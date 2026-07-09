#!/usr/bin/env python3
"""Build a static GitHub Pages version of the dashboard."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"


def copy_static_assets() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    shutil.copytree(STATIC_DIR, DIST_DIR)
    (DIST_DIR / "data").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / ".nojekyll").write_text("", encoding="utf-8")


def write_static_index() -> None:
    index_path = DIST_DIR / "index.html"
    html = index_path.read_text(encoding="utf-8")
    marker = '<script src="app.js" defer></script>'
    config = (
        '<script>'
        'window.DASHBOARD_STATIC_MODE=true;'
        'window.DASHBOARD_DATA_URL="data/dashboard.json";'
        '</script>\n  '
        + marker
    )
    if marker in html:
        html = html.replace(marker, config)
    index_path.write_text(html, encoding="utf-8")


def write_dashboard_data(snapshot: dict) -> None:
    snapshot["system"]["refreshing"] = False
    (DIST_DIR / "data" / "dashboard.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-refresh", action="store_true", help="Build from existing seed/cache only.")
    args = parser.parse_args()

    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8765")
    os.environ.setdefault("REFRESH_AT", "08:00")
    os.environ.setdefault("REFRESH_ON_STARTUP", "0")
    os.environ.setdefault("ENABLE_CHINA_IDC", "0")

    from server import SERVICE

    if not args.no_refresh:
        result = SERVICE.refresh("github-pages")
        print(json.dumps({
            "ok": result.get("ok"),
            "updatedSources": result.get("updatedSources", []),
            "errors": result.get("errors", []),
        }, ensure_ascii=False))

    copy_static_assets()
    write_static_index()
    write_dashboard_data(SERVICE.snapshot())
    print(f"Built static dashboard: {DIST_DIR}")


if __name__ == "__main__":
    main()
