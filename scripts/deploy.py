#!/usr/bin/env python3
"""Push jellytv-plus.css (plus optional local overrides) into a Jellyfin server's
Custom CSS via the branding configuration API.

The current branding config is backed up before anything is written, and the
result is read back and compared. Only CustomCss changes; LoginDisclaimer and
SplashscreenEnabled are preserved.

Usage:
  JELLYFIN_TOKEN=... python3 scripts/deploy.py --server http://host:8096 --dry-run
  python3 scripts/deploy.py --server http://host:8096 --token-file ~/.jellyfin-token \
      --override overrides/hplaptop.css

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
    ap.add_argument("--backup-dir", default=str(ROOT / "backups"))
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    args = ap.parse_args()

    token = pathlib.Path(args.token_file).expanduser().read_text().strip() if args.token_file else os.environ.get("JELLYFIN_TOKEN", "")
    if not token:
        sys.exit("No token: pass --token-file or set JELLYFIN_TOKEN")

    try:
        current = request(args.server, token, "GET", "/System/Configuration/branding")
    except urllib.error.HTTPError as e:
        sys.exit(f"GET branding failed: HTTP {e.code} (is the token an administrator's?)")

    new_css = build_css(args.css, args.override)
    old_css = current.get("CustomCss") or ""
    print(f"server:        {args.server}")
    print(f"current CSS:   {len(old_css):>6} chars, first line: {old_css.splitlines()[0][:80] if old_css else '(empty)'}")
    print(f"new CSS:       {len(new_css):>6} chars from {pathlib.Path(args.css).name} + {len(args.override)} override file(s)")
    print(f"unchanged:     LoginDisclaimer={current.get('LoginDisclaimer')!r}, SplashscreenEnabled={current.get('SplashscreenEnabled')}")
    if old_css == new_css:
        print("Nothing to do: server already has this CSS.")
        return
    if args.dry_run:
        print("Dry run: no changes written.")
        return

    backup_dir = pathlib.Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"branding-{stamp}.json"
    backup.write_text(json.dumps(current, indent=2))
    print(f"backup:        {backup}")

    updated = dict(current, CustomCss=new_css)
    request(args.server, token, "POST", "/System/Configuration/branding", updated)

    check = request(args.server, token, "GET", "/System/Configuration/branding")
    if (check.get("CustomCss") or "") != new_css:
        sys.exit("Verification FAILED: server CustomCss differs from what was sent. Restore from the backup above.")
    print("deployed and verified: server CustomCss matches.")


if __name__ == "__main__":
    main()
