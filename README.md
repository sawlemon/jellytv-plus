# Jelly TV+

A custom-CSS theme that makes the Jellyfin web client look and behave like the Apple TV app
(macOS / iPadOS 26): a floating Liquid Glass tab bar, smoked-glass controls, full-bleed heroes
with title art, frosted metadata inside landscape tiles, Mac-style episode rows, and the iPad
player layout. The header wordmark reads **Jelly TV+** in Apple's system font.

Built and tested against **Jellyfin 12.2** (web client with the MUI "experimental" layout on
desktop/phone and the legacy layout on TVs).

| Home | Movie |
| --- | --- |
| ![Home](screenshots/after/home.jpg) | ![Movie](screenshots/after/movie-detail.jpg) |
| **Season / episodes** | **Library** |
| ![Season](screenshots/after/season-episodes.jpg) | ![Library](screenshots/after/library.jpg) |
| **Player** | **Sign in** |
| ![Player](screenshots/after/player.jpg) | ![Sign in](screenshots/after/sign-in.jpg) |
| **TV layout (focus)** | **Phone sidebar** |
| ![TV](screenshots/after/tv-layout.jpg) | ![Phone](screenshots/after/phone-sidebar.jpg) |
| **iPhone home (tab bar)** | **iPhone season** |
| ![iPhone home](screenshots/after/iphone-home.jpg) | ![iPhone season](screenshots/after/iphone-season.jpg) |
| **iPad (mobile layout)** | **iPad portrait / iPhone movie** |
| ![iPad show](screenshots/after/ipad-show.jpg) | ![iPad portrait](screenshots/after/ipad-portrait-movie.jpg) ![iPhone movie](screenshots/after/iphone-movie.jpg) |

## What it changes

- **Header** – "Jelly TV+" wordmark; library links become a centered glass tab pill with the
  active tab in blue on a darker capsule (iPad Apple TV); SyncPlay/Cast/Search grouped in a glass
  capsule; avatar in a glass circle; progressive scroll-edge blur behind it.
- **Glass** – one smoked tint (`--jtv-glass`) with blur, saturation, a specular rim and soft
  shadow, used for every floating control. Tuned to ~#262626 over black (Apple's measures ~#292929)
  while staying legible over bright video.
- **Cards** – 12 px radius with a hairline rim; landscape tiles carry title/subtitle inside the
  artwork over a frosted fade, with Apple's `▶ ━━ 1982` resume row; posters get left-aligned
  captions; hover lift on desktop, tvOS-style focus lift on TVs.
- **Detail pages** – full-bleed backdrop hero, logo art bottom-left (plain title hidden when a
  logo exists), `·`-separated metadata with outlined rating badge, white **Play** pill + glass
  circle actions; black hero flowing into the Mac's `#1d1d1e` content canvas; circular cast
  portraits.
- **Seasons** – the episode list becomes a horizontal row of 16:9 cards with title, two-line
  synopsis and `▶ 28m` over a frosted fade (Mac "Season 1" row).
- **Player** – glass back circle, SyncPlay/Cast capsule and volume capsule up top, centered
  rewind / play / fast-forward glass cluster, bold title bottom-left above a thin white-on-gray
  scrubber, remaining controls as glass circles.
- **Sidebar, menus, dialogs, sign-in** – glass panels with blue icons and macOS menu highlighting.
- **iPhone (≤600 px)** – the navigation drawer becomes the iOS 26 floating glass tab bar (icons
  over labels, selected tab blue on a darker capsule); "Jelly TV+" large title on Home with the
  avatar top-right; centered detail hero (logo, metadata, Play pill + ✓ on one row, other actions
  centered below); taller episode cards; Continue Watching tiles with the next one peeking in;
  portrait player with a volume circle and Apple's control spacing.
- **Backdrops on iPhone/iPad** – Jellyfin's mobile layout puts the backdrop on the page's own
  banner (`#itemBackdrop`) instead of the global backdrop layer; the theme styles that banner as
  the hero. When Jellyfin loads no backdrop at all (desktop layout narrower than 1000 px) a blurred
  poster stands in.

## Install

**Paste:** Dashboard → General → Custom CSS, paste the contents of `jellytv-plus.css`, save,
reload clients.

**Script (keeps a backup, verifies the write):**

```sh
# dry run first
JELLYFIN_TOKEN=<admin api key> python3 scripts/deploy.py --server http://<host>:8096 --dry-run
# deploy, appending any server-specific overrides
python3 scripts/deploy.py --server http://<host>:8096 --token-file ~/.jellyfin-token \
    --override overrides/hplaptop.css
```

`deploy.py` uses only the Python standard library. It reads the current branding config, writes
a timestamped backup to `backups/` (git-ignored), replaces only `CustomCss`, and reads it back to
confirm. Restore by POSTing a backup JSON to `/System/Configuration/branding`.

## Fonts

Apple devices render the real **SF Pro** through the `-apple-system` stack. SF Pro can't be
redistributed, so other platforms (Windows, Android, Tizen, webOS) fall back to **Inter**, which
is loaded from Google Fonts and is the closest freely licensed match.

## Compatibility notes

- TVs (`html.layout-tv`) get the same look without `backdrop-filter` (too expensive on Tizen/webOS)
  and with denser fills instead.
- Rules that must work on Tizen 6 (Chromium 76) avoid `:is()`, `:where()`, `aspect-ratio`,
  `inset` and flex `gap`; every `max()`/`min()` has a plain fallback declared first.
- `:has()` is used only for desktop refinements (hiding the duplicate title under logo art,
  the Home tab highlight, hiding header chrome when signed out). Browsers without it skip those.
- The theme targets stable `Mui*` component classes and legacy Jellyfin classes, never the
  hashed `css-*` ones, so it should survive minor web-client updates.

## Limitations

- CSS can't add content, so there is no auto-rotating hero carousel on Home (that needs a
  featured-content/media-bar plugin), and the browser tab title still says "Jellyfin".
- Material icons stay Material icons (no SF Symbols); they are recolored and resized to sit
  naturally in the glass controls.
