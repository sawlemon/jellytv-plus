/*
 * Jelly TV+ — Apple TV-style hero carousel for the Jellyfin home screen.
 * https://github.com/sawlemon/jellytv-plus
 *
 * Loaded by the JavaScript Injector plugin. Styling lives in jellytv-plus.css (.jtv-hero*).
 * Shows the most recently added movies/shows that have backdrop art, then Jellyfin's own
 * rows follow (Continue Watching, Recently Added …). The "My Media" library tiles are hidden.
 * Written without optional chaining / nullish coalescing so older TV browsers can parse it.
 */
(function () {
  'use strict';
  if (window.__jellyTvPlusHero) return;
  window.__jellyTvPlusHero = true;

  var LIMIT = 8;
  var INTERVAL_MS = 8000;
  var NEW_DAYS = 21;

  var state = { items: null, loading: false, index: 0, timer: null, root: null, userId: null };

  function api() { return window.ApiClient; }
  function isTv() { return document.documentElement.classList.contains('layout-tv'); }

  function homePage() {
    var page = document.getElementById('indexPage');
    if (!page || page.classList.contains('hide')) return null;
    var tab = page.querySelector('#homeTab');
    if (!tab || !tab.classList.contains('is-active')) return null;
    return tab;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function img(item, type, maxWidth) {
    var client = api();
    if (type === 'Backdrop') {
      if (item.BackdropImageTags && item.BackdropImageTags.length) {
        return client.getScaledImageUrl(item.Id, { type: 'Backdrop', index: 0, tag: item.BackdropImageTags[0], maxWidth: maxWidth, quality: 90 });
      }
      return null;
    }
    if (item.ImageTags && item.ImageTags[type]) {
      return client.getScaledImageUrl(item.Id, { type: type, tag: item.ImageTags[type], maxWidth: maxWidth, quality: 90 });
    }
    return null;
  }

  var ICON_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.6v14.8c0 .8.9 1.3 1.6.9l11.8-7.4c.6-.4.6-1.4 0-1.8L8.6 3.7C7.9 3.3 7 3.8 7 4.6z"/></svg>';
  var ICON_PLUS = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.5v15M4.5 12h15" stroke-width="2.4" stroke-linecap="round" fill="none"/></svg>';
  var ICON_CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';

  function metaLine(item) {
    var parts = [item.Type === 'Series' ? 'TV Show' : 'Movie'];
    (item.Genres || []).slice(0, 2).forEach(function (g) { parts.push(g); });
    var html = parts.map(esc).join(' · ');
    if (item.OfficialRating) html += ' <span class="jtv-hero-rating">' + esc(item.OfficialRating) + '</span>';
    return html;
  }

  function caption(item) {
    var bits = [];
    if (item.ProductionYear) bits.push(item.ProductionYear);
    if (item.Type === 'Series' && item.ChildCount) bits.push(item.ChildCount + (item.ChildCount === 1 ? ' Season' : ' Seasons'));
    if (item.Type !== 'Series' && item.RunTimeTicks) {
      var mins = Math.round(item.RunTimeTicks / 600000000);
      bits.push(mins >= 60 ? Math.floor(mins / 60) + 'h ' + (mins % 60) + 'm' : mins + 'm');
    }
    return bits.join(' · ');
  }

  function isNew(item) {
    var d = Date.parse(item.DateCreated);
    return d && (Date.now() - d) < NEW_DAYS * 86400000;
  }

  function playLabel(item) {
    var ud = item.UserData || {};
    return ud.PlaybackPositionTicks > 0 ? 'Resume' : 'Play';
  }

  function slideHtml(item, i) {
    var logo = img(item, 'Logo', 900);
    var fav = item.UserData && item.UserData.IsFavorite;
    return '' +
      '<article class="jtv-hero-slide' + (i === 0 ? ' is-active' : '') + '" data-index="' + i + '" data-id="' + esc(item.Id) + '" aria-hidden="' + (i === 0 ? 'false' : 'true') + '">' +
        '<div class="jtv-hero-bg" style="background-image:url(\'' + esc(img(item, 'Backdrop', 2560)) + '\')"></div>' +
        '<div class="jtv-hero-scrim"></div>' +
        '<div class="jtv-hero-info">' +
          (isNew(item) ? '<span class="jtv-hero-badge">New</span>' : '') +
          (logo
            ? '<img class="jtv-hero-logo" src="' + esc(logo) + '" alt="' + esc(item.Name) + '">'
            : '<h2 class="jtv-hero-title">' + esc(item.Name) + '</h2>') +
          '<div class="jtv-hero-meta">' + metaLine(item) + '</div>' +
          (item.Overview ? '<p class="jtv-hero-overview">' + esc(item.Overview) + '</p>' : '') +
          '<p class="jtv-hero-caption">' + (isNew(item) ? '<span class="jtv-hero-caption-new">New · </span>' : '') + esc(caption(item)) + '</p>' +
          '<div class="jtv-hero-actions">' +
            '<button type="button" class="jtv-hero-play" data-action="play">' + ICON_PLAY + '<span>' + playLabel(item) + '</span></button>' +
            '<button type="button" class="jtv-hero-fav' + (fav ? ' is-fav' : '') + '" data-action="fav" aria-label="' + (fav ? 'Remove from Favorites' : 'Add to Favorites') + '">' + (fav ? ICON_CHECK : ICON_PLUS) + '</button>' +
          '</div>' +
        '</div>' +
      '</article>';
  }

  function render(tab) {
    var items = state.items;
    var root = document.createElement('section');
    root.className = 'jtv-hero';
    root.setAttribute('aria-roledescription', 'carousel');
    root.setAttribute('aria-label', 'Recently added');
    root.style.setProperty('--jtv-hero-interval', INTERVAL_MS + 'ms');
    root.innerHTML =
      '<div class="jtv-hero-slides">' + items.map(slideHtml).join('') + '</div>' +
      (items.length > 1
        ? '<div class="jtv-hero-dots" role="tablist">' + items.map(function (it, i) {
            return '<button type="button" class="jtv-hero-dot' + (i === 0 ? ' is-active' : '') + '" data-index="' + i + '" aria-label="' + esc(it.Name) + '"><i></i></button>';
          }).join('') + '</div>'
        : '');
    tab.insertBefore(root, tab.firstChild);
    state.root = root;
    state.index = 0;
    bind(root);
    offset();
    enrichSeriesLabels();
    restart();
  }

  function offset() {
    var root = state.root;
    if (!root) return;
    // measure the page box (absolutely positioned, so the hero's negative margin can't collapse into it)
    var page = root.closest('.page') || root.parentNode;
    var top = page.getBoundingClientRect().top + window.pageYOffset;
    root.style.marginTop = (-top) + 'px';
  }

  function go(i) {
    var root = state.root;
    if (!root || !state.items) return;
    var n = state.items.length;
    state.index = (i + n) % n;
    var slides = root.querySelectorAll('.jtv-hero-slide');
    var dots = root.querySelectorAll('.jtv-hero-dot');
    for (var k = 0; k < slides.length; k++) {
      var on = k === state.index;
      slides[k].classList.toggle('is-active', on);
      slides[k].setAttribute('aria-hidden', on ? 'false' : 'true');
    }
    for (var d = 0; d < dots.length; d++) {
      dots[d].classList.remove('is-active');
      // restart the progress animation
      void dots[d].offsetWidth;
      dots[d].classList.toggle('is-active', d === state.index);
    }
    restart();
  }

  function restart() {
    clearTimeout(state.timer);
    if (!state.items || state.items.length < 2) return;
    state.timer = setTimeout(function () {
      if (document.hidden || !homePage()) { restart(); return; }
      go(state.index + 1);
    }, INTERVAL_MS);
  }

  function currentItem(el) {
    var slide = el.closest('.jtv-hero-slide');
    return slide ? state.items[Number(slide.getAttribute('data-index'))] : null;
  }

  function openDetails(item) {
    window.location.hash = '#/details?id=' + item.Id + '&serverId=' + api().serverId();
  }

  // open the item page and press Jellyfin's own Play button (resume, next-up, versions all handled)
  function playViaDetails(item) {
    openDetails(item);
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      var page = document.querySelector('.itemDetailPage:not(.hide)');
      var btn = page && page.querySelector('.mainDetailButtons .btnPlay:not(.hide)');
      if (btn && location.hash.indexOf(item.Id) !== -1) { clearInterval(t); btn.click(); }
      else if (tries > 40) clearInterval(t);
    }, 150);
  }

  function play(item) {
    var client = api();
    if (!(client.isWebSocketOpen && client.isWebSocketOpen())) { playViaDetails(item); return; }
    var userId = client.getCurrentUserId();
    var target = Promise.resolve({ id: item.Id, ticks: (item.UserData && item.UserData.PlaybackPositionTicks) || 0 });
    if (item.Type === 'Series') {
      target = client.getNextUpEpisodes({ SeriesId: item.Id, UserId: userId, Limit: 1, Fields: 'UserData' }).then(function (r) {
        var ep = r.Items && r.Items[0];
        if (ep) return { id: ep.Id, ticks: (ep.UserData && ep.UserData.PlaybackPositionTicks) || 0 };
        return client.getEpisodes(item.Id, { UserId: userId, Limit: 1 }).then(function (e) {
          return e.Items && e.Items[0] ? { id: e.Items[0].Id, ticks: 0 } : null;
        });
      });
    }
    target.then(function (t) {
      if (!t) { openDetails(item); return; }
      // ask the server to start playback on this very browser session
      return client.getSessions({ DeviceId: client.deviceId() }).then(function (sessions) {
        var app = client.appName ? decodeURIComponent(client.appName()) : '';
        var me = (sessions || []).filter(function (s) { return s.SupportsRemoteControl && (!app || s.Client === app); })[0] ||
          (sessions || []).filter(function (s) { return s.SupportsRemoteControl; })[0];
        if (!me) throw new Error('no session');
        return client.sendPlayCommand(me.Id, { ItemIds: t.id, PlayCommand: 'PlayNow', StartPositionTicks: t.ticks });
      });
    }).catch(function () { playViaDetails(item); });
  }

  function toggleFav(btn, item) {
    var client = api();
    var next = !(item.UserData && item.UserData.IsFavorite);
    client.updateFavoriteStatus(client.getCurrentUserId(), item.Id, next).then(function () {
      item.UserData = item.UserData || {};
      item.UserData.IsFavorite = next;
      btn.classList.toggle('is-fav', next);
      btn.innerHTML = next ? ICON_CHECK : ICON_PLUS;
      btn.setAttribute('aria-label', next ? 'Remove from Favorites' : 'Add to Favorites');
    });
  }

  function bind(root) {
    root.addEventListener('click', function (e) {
      var dot = e.target.closest('.jtv-hero-dot');
      if (dot) { go(Number(dot.getAttribute('data-index'))); return; }
      var item = currentItem(e.target);
      if (!item) return;
      var btn = e.target.closest('button[data-action]');
      if (btn && btn.getAttribute('data-action') === 'play') { e.preventDefault(); play(item); return; }
      if (btn && btn.getAttribute('data-action') === 'fav') { e.preventDefault(); toggleFav(btn, item); return; }
      if (e.target.closest('.jtv-hero-logo, .jtv-hero-title, .jtv-hero-bg, .jtv-hero-scrim, .jtv-hero-overview')) openDetails(item);
    });
    var x0 = null;
    root.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    root.addEventListener('touchend', function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 50) go(state.index + (dx < 0 ? 1 : -1));
    }, { passive: true });
  }

  // "Play S1, E3" / "Resume S1, E3" like Apple's hero buttons
  function enrichSeriesLabels() {
    var client = api();
    state.items.forEach(function (item, i) {
      if (item.Type !== 'Series') return;
      client.getNextUpEpisodes({ SeriesId: item.Id, UserId: client.getCurrentUserId(), Limit: 1, Fields: 'UserData' }).then(function (r) {
        var ep = r.Items && r.Items[0];
        if (!ep || !state.root) return;
        var label = state.root.querySelector('.jtv-hero-slide[data-index="' + i + '"] .jtv-hero-play span');
        var resume = ep.UserData && ep.UserData.PlaybackPositionTicks > 0;
        if (label) label.textContent = (resume ? 'Resume' : 'Play') + ' S' + (ep.ParentIndexNumber || 1) + ', E' + (ep.IndexNumber || 1);
      }).catch(function () {});
    });
  }

  function load() {
    var client = api();
    state.loading = true;
    state.userId = client.getCurrentUserId();
    return client.getItems(state.userId, {
      SortBy: 'DateCreated',
      SortOrder: 'Descending',
      IncludeItemTypes: 'Movie,Series',
      Recursive: true,
      Limit: 24,
      ImageTypes: 'Backdrop',
      EnableImageTypes: 'Backdrop,Logo,Primary',
      Fields: 'Overview,Genres,DateCreated,ProductionYear,OfficialRating,RunTimeTicks,ChildCount',
      EnableUserData: true
    }).then(function (r) {
      state.items = (r.Items || []).filter(function (it) { return it.BackdropImageTags && it.BackdropImageTags.length; }).slice(0, LIMIT);
      state.loading = false;
      return state.items;
    }, function () { state.loading = false; state.items = []; });
  }

  function hideLibraryTiles(tab) {
    var cards = tab.querySelectorAll('.card[data-type="CollectionFolder"]');
    for (var i = 0; i < cards.length; i++) {
      var sec = cards[i].closest('.verticalSection');
      if (sec) sec.classList.add('jtv-hidden-section');
    }
  }

  function tick() {
    var client = api();
    var tab = homePage();
    document.documentElement.classList.toggle('jtv-home', !!tab);
    if (!tab || !client || isTv()) return;
    hideLibraryTiles(tab);
    if (client.getCurrentUserId() !== state.userId && !state.loading) {
      state.items = null;
      if (state.root) { state.root.remove(); state.root = null; }
    }
    if (state.items === null) {
      if (!state.loading) load().then(function () { tick(); });
      return;
    }
    if (!state.items.length) return;
    if (!state.root || !tab.contains(state.root)) {
      if (state.root) state.root.remove();
      render(tab);
    }
  }

  function onScroll() {
    var root = state.root;
    var past = !!root && document.documentElement.classList.contains('jtv-home') &&
      window.pageYOffset > root.offsetHeight - 140;
    document.documentElement.classList.toggle('jtv-hero-scrolled', past);
  }

  window.addEventListener('hashchange', function () { setTimeout(tick, 50); });
  window.addEventListener('resize', offset);
  window.addEventListener('scroll', onScroll, { passive: true });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) restart(); });
  new MutationObserver(function () { tick(); }).observe(document.body, { childList: true, subtree: false });
  setInterval(tick, 1000);
  tick();
})();
