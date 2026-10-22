# Jelly TV+

Make your Jellyfin server look and feel like the Apple TV app.

Jelly TV+ is a free theme for [Jellyfin](https://jellyfin.org). It changes how Jellyfin looks
in a web browser, on iPhone and iPad, and on TV apps that use Jellyfin's web interface (like the
Samsung TV app). Your movies and shows stay exactly the same; only the look changes.

Made for **Jellyfin 12.2**. It may need small fixes on other versions.

| Home | iPhone |
| --- | --- |
| ![Home screen with a large rotating banner](screenshots/after/home-hero.jpg) | ![iPhone home screen](screenshots/after/iphone-home-hero.jpg) |
| **Movie page** | **Episodes** |
| ![Movie page](screenshots/after/movie-detail.jpg) | ![Episode row](screenshots/after/season-episodes.jpg) |
| **Library** | **Video player** |
| ![Movie library](screenshots/after/library.jpg) | ![Video player](screenshots/after/player.jpg) |
| **iPad** | **Sign in** |
| ![iPad show page](screenshots/after/ipad-show.jpg) | ![Sign-in page](screenshots/after/sign-in.jpg) |
| **TV** | **iPhone menu bar** |
| ![TV layout](screenshots/after/tv-layout.jpg) | ![iPhone bottom menu](screenshots/after/iphone-home.jpg) |

## What you get

- **A big rotating banner on the Home screen** showing your newest movies and shows, with the
  title logo, a short description and a white **Play** button. It changes every few seconds;
  you can also tap the dots or swipe. Under it: *Continue Watching*, then *Recently Added*.
- **"Jelly TV+" at the top** instead of the Jellyfin logo, in Apple's own font on Apple devices.
- **See-through "glass" buttons and menus**, like the newest Apple designs.
- **A floating menu bar** (Home, Favorites, Movies, Shows…) at the top on computers and iPads,
  and at the bottom on iPhones.
- **Movie and show pages** with full-screen artwork, the title logo, and a white Play button.
- **Episodes shown as a row of picture cards**, like the Apple TV app.
- **A cleaner video player** with big round buttons in the middle of the screen.
- **Round cast photos**, rounded posters, and smooth hover and focus effects.

## How to install

There are two parts:

1. **The look** (colors, buttons, layout). This is the file `jellytv-plus.css`.
2. **The Home screen banner**. This is the file `jellytv-plus.js`. It needs one free plugin.

You can install just part 1 if you like. Everything works without part 2; the Home screen
simply starts with *Continue Watching* instead of the banner.

### Part 1: the look (2 minutes)

1. Open Jellyfin and sign in as an administrator.
2. Go to **Dashboard → General**.
3. Find the box called **Custom CSS**.
4. Open `jellytv-plus.css` from this project, copy everything in it, and paste it into that box.
5. Click **Save**, then refresh the page.

### Part 2: the Home screen banner

1. In Jellyfin, go to **Dashboard → Plugins → Repositories** and add the plugin address for
   your Jellyfin version, from the
   [JavaScript Injector page](https://github.com/n00bcodr/Jellyfin-JavaScript-Injector).
   For Jellyfin 12 it is:
   `https://raw.githubusercontent.com/n00bcodr/jellyfin-plugins/main/12/manifest.json`
2. Go to **Dashboard → Plugins → Catalog**, install **JavaScript Injector**, then restart Jellyfin.
3. Open the plugin's settings, add a new script named **Jelly TV+**, paste in everything from
   `jellytv-plus.js`, and save.
4. Refresh the Jellyfin page. If the banner does not appear, see *Troubleshooting* below.

### Optional: install or update with one command

If you are comfortable with a terminal, `scripts/deploy.py` does both parts for you. It saves a
backup of your current settings first and checks that everything was saved correctly. It only
needs Python 3, nothing else.

1. In Jellyfin, go to **Dashboard → API Keys** and create a new key.
2. Save that key in a file on your computer, for example `~/.jellyfin-token`. Keep this file
   private and never share it or commit it to Git.
3. Run (replace the address with your server's address):

```sh
# Preview what would change. Nothing is saved.
python3 scripts/deploy.py --server http://YOUR-SERVER:8096 --token-file ~/.jellyfin-token --dry-run

# Install or update
python3 scripts/deploy.py --server http://YOUR-SERVER:8096 --token-file ~/.jellyfin-token
```

Backups go into a `backups` folder, which Git ignores.

## Samsung TVs

The theme also works in the Samsung (Tizen) Jellyfin app, with a few differences:

- **Fully close and reopen the app** after installing or updating the theme. TVs often keep
  apps paused in the background, so the old look can stay until the app really restarts.
- **Turn on artwork:** in the TV app, go to **Settings → Display → Backdrops**. Without it, movie
  pages have no background picture.
- **No Home screen banner on TVs.** The TV app has its own built-in copy of Jellyfin's interface,
  so it never loads the banner script. TVs show the normal rows instead.
- If you see gray bars around videos on a Samsung TV, add the small fix in
  `overrides/samsung-tv.css` to the end of your Custom CSS. With the command above, add
  `--override overrides/samsung-tv.css`.

## Troubleshooting

**The Home banner does not show up after installing the plugin.**
Your browser may still be using an old copy of Jellyfin's start page. If Jellyfin runs in
Docker, run this once on the server and then refresh the page:

```sh
docker exec jellyfin touch /jellyfin/jellyfin-web/index.html
```

You may need to run it again after updating Jellyfin.

**I changed the theme but my device still shows the old look.**
Refresh the page. On phones, tablets and TVs, close the app completely and open it again.

**I want my old look back.**
Delete everything in **Dashboard → General → Custom CSS**, and turn off or delete the
**Jelly TV+** script in the JavaScript Injector settings.

## Good to know

- **Fonts:** Apple devices show Apple's own font (SF Pro). Other devices use **Inter**, a very
  similar free font, loaded from Google Fonts.
- **Icons:** the icons are Jellyfin's own, recolored to match. Apple's icons cannot be used here.
- **Browser tab:** the browser tab title still says "Jellyfin".
- **Updates:** a big Jellyfin update can move things around. If something looks wrong after an
  update, please open an issue.

## Disclaimer

Jelly TV+ is a fan-made theme. It is not made by, supported by, or connected to Apple or the
Jellyfin project. "Apple TV" is a trademark of Apple Inc. Movie posters and pictures in the
screenshots belong to their owners and are shown only to demonstrate the theme.
