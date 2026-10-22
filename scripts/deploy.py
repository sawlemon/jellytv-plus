#!/usr/bin/env python3
"""Push jellytv-plus.css (plus optional local overrides) into a Jellyfin server's
Custom CSS via the branding configuration API, and jellytv-plus.js (the home hero
carousel) into the JavaScript Injector plugin's script list.

Each config is backed up before anything is written, and the result is read back
and compared. Only CustomCss changes in branding; in the injector only the script
entry named "Jelly TV+" is created or replaced (other scripts are left alone).

Usage:
  JELLYFIN_TOKEN=... python3 scripts/deploy.py --server http://host:8096 --dry-run
  python3 scripts/deploy.py --server http://host:8096 --token-file ~/.jellyfin-token \
      --override overrides/samsung-tv.css

The token must belong to an administrator (an API key from Dashboard → API Keys works).
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent


def request(server, token, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(server.rstrip("/") + path, data=data, method=method)
    req.add_header("Authorization", f'MediaBrowser Client="jellytv-plus-deploy", Token="{token}"')
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def build_css(theme_path, overrides):
    parts = [pathlib.Path(theme_path).read_text()]
    for path in overrides:
        parts.append(f"\n/* ── local overrides: {pathlib.Path(path).name} ── */\n")
        parts.append(pathlib.Path(path).read_text())
    return "".join(parts).strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", required=True, help="Jellyfin base URL, e.g. http://192.168.1.10:8096")
    ap.add_argument("--token-file", help="file containing an admin access token (else $JELLYFIN_TOKEN)")
    ap.add_argument("--css", default=str(ROOT / "jellytv-plus.css"))
    ap.add_argument("--override", action="append", default=[], help="extra CSS appended after the theme (repeatable)")
    ap.add_argument("--js", default=str(ROOT / "jellytv-plus.js"), help="hero script for JavaScript Injector")
    ap.add_argument("--skip-js", action="store_true", help="only deploy the CSS")
    ap.add_argument("--backup-dir", default=str(ROOT / "backups"))
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    args = ap.parse_args()

    token = pathlib.Path(args.token_file).expanduser().read_text().strip() if args.token_file else os.environ.get("JELLYFIN_TOKEN", "")
    if not token:
        sys.exit("No token: pass --token-file or set JELLYFIN_TOKEN")

    print(f"server:        {args.server}")
    deploy_css(args, token)
    if not args.skip_js:
        deploy_js(args, token)


def backup(args, name, data):
    backup_dir = pathlib.Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = backup_dir / f"{name}-{stamp}.json"
    path.write_text(json.dumps(data, indent=2))
    print(f"  backup:      {path}")


def deploy_css(args, token):
    try:
        current = request(args.server, token, "GET", "/System/Configuration/branding")
    except urllib.error.HTTPError as e:
        sys.exit(f"GET branding failed: HTTP {e.code} (is the token an administrator's?)")

    new_css = build_css(args.css, args.override)
    old_css = current.get("CustomCss") or ""
    print("CSS (branding):")
    print(f"  current:     {len(old_css):>6} chars, first line: {old_css.splitlines()[0][:80] if old_css else '(empty)'}")
    print(f"  new:         {len(new_css):>6} chars from {pathlib.Path(args.css).name} + {len(args.override)} override file(s)")
    print(f"  unchanged:   LoginDisclaimer={current.get('LoginDisclaimer')!r}, SplashscreenEnabled={current.get('SplashscreenEnabled')}")
    if old_css == new_css:
        print("  nothing to do: server already has this CSS.")
        return
    if args.dry_run:
        print("  dry run: no changes written.")
        return
    backup(args, "branding", current)
    request(args.server, token, "POST", "/System/Configuration/branding", dict(current, CustomCss=new_css))
    check = request(args.server, token, "GET", "/System/Configuration/branding")
    if (check.get("CustomCss") or "") != new_css:
        sys.exit("Verification FAILED: server CustomCss differs from what was sent. Restore from the backup above.")
    print("  deployed and verified: server CustomCss matches.")


SCRIPT_NAME = "Jelly TV+"


def deploy_js(args, token):
    plugins = request(args.server, token, "GET", "/Plugins")
    injector = next((p for p in plugins if p.get("Name") == "JavaScript Injector"), None)
    print("JS (JavaScript Injector):")
    if not injector:
        print("  plugin not installed; skipping the hero script (CSS-only look).")
        return
    path = f"/Plugins/{injector['Id']}/Configuration"
    config = request(args.server, token, "GET", path)
    scripts = config.get("CustomJavaScripts") or []
    new_js = pathlib.Path(args.js).read_text()
    existing = next((s for s in scripts if s.get("Name") == SCRIPT_NAME), None)
    print(f"  plugin:      {injector.get('Version')} ({injector.get('Status')}), {len(scripts)} custom script(s)")
    print(f"  entry:       {'replace' if existing else 'create'} '{SCRIPT_NAME}', {len(new_js)} chars")
    if existing and existing.get("Script") == new_js and existing.get("Enabled"):
        print("  nothing to do: server already has this script.")
        return
    if args.dry_run:
        print("  dry run: no changes written.")
        return
    backup(args, "javascript-injector", config)
    entry = dict(existing or {}, Name=SCRIPT_NAME, Script=new_js, Enabled=True, RequiresAuthentication=True)
    others = [s for s in scripts if s.get("Name") != SCRIPT_NAME]
    request(args.server, token, "POST", path, dict(config, CustomJavaScripts=others + [entry]))
    check = request(args.server, token, "GET", path)
    got = next((s for s in check.get("CustomJavaScripts") or [] if s.get("Name") == SCRIPT_NAME), None)
    if not got or got.get("Script") != new_js:
        sys.exit("Verification FAILED: injector script differs from what was sent. Restore from the backup above.")
    print("  deployed and verified: injector script matches.")

if __name__ == "__main__":
    main()
