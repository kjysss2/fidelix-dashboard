#!/usr/bin/env python3
"""Build a static GitHub Pages version of the dashboard."""

from __future__ import annotations

import argparse
import copy
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


def refresh_spot_prices_only(service) -> dict:
    """Refresh only the DRAMeXchange spot price slice for GitHub Pages builds."""
    from server import CACHE_FILE, atomic_write_json, now_iso

    with service.lock:
        working = copy.deepcopy(service.dashboard)

    errors: list[str] = []
    updated_sources: list[str] = []
    try:
        service._refresh_dramexchange_spot(working)
        updated_sources.append("DRAMeXchange")
    except Exception as exc:
        errors.append(f"DRAMeXchange: {exc}")
        service._source_error(working, "dramexchange", str(exc))

    working["system"].update({
        "lastRefresh": now_iso(),
        "lastRefreshReason": "github-pages-spot-only",
        "lastRefreshErrors": errors,
    })

    with service.lock:
        service.dashboard = working
        atomic_write_json(CACHE_FILE, working)

    return {"ok": bool(updated_sources), "updatedSources": updated_sources, "errors": errors}


def refresh_spot_and_china_only(service) -> dict:
    """Refresh DRAM spot prices plus China IDC order/backlog data for Pages builds."""
    from server import CACHE_FILE, atomic_write_json, now_iso

    with service.lock:
        working = copy.deepcopy(service.dashboard)

    errors: list[str] = []
    updated_sources: list[str] = []
    refreshers = [
        ("DRAMeXchange", lambda: service._refresh_dramexchange_spot(working), "dramexchange"),
        ("GDS IR", lambda: service._refresh_gds_orders(working), "gds_ir"),
        ("VNET IR", lambda: service._refresh_vnet_orders(working), "vnet_ir"),
    ]
    for label, refresh, source_id in refreshers:
        try:
            refresh()
            updated_sources.append(label)
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            service._source_error(working, source_id, str(exc))

    working["system"].update({
        "lastRefresh": now_iso(),
        "lastRefreshReason": "github-pages-spot-china-only",
        "lastRefreshErrors": errors,
    })

    with service.lock:
        service.dashboard = working
        atomic_write_json(CACHE_FILE, working)

    return {"ok": bool(updated_sources), "updatedSources": updated_sources, "errors": errors}


def latest_completed_quarter(now) -> tuple[int, int]:
    """Return the most recently completed calendar quarter."""
    current_quarter = (now.month - 1) // 3 + 1
    if current_quarter == 1:
        return now.year - 1, 4
    return now.year, current_quarter - 1


def refresh_latest_completed_twse_quarter(service) -> dict:
    """Backfill the latest completed TWSE quarter directly from MOPS.

    TWSE's aggregated income-statement OpenAPI can lag company announcements.
    This check lets Nanya, Winbond, and Macronix appear as soon as their
    individual MOPS financial statement becomes available.
    """
    from server import CACHE_FILE, KST, atomic_write_json, datetime, now_iso, with_margins

    year, quarter = latest_completed_quarter(datetime.now(KST))
    target_period = f"{year}Q{quarter}"
    targets = {"2337": "macronix", "2344": "winbond", "2408": "nanya"}

    with service.lock:
        working = copy.deepcopy(service.dashboard)

    errors: list[str] = []
    updated_companies: list[str] = []

    for code, company_id in targets.items():
        company = service._company(working, company_id)
        try:
            period, item = service._fetch_mops_quarter(code, year, quarter)
        except Exception as exc:
            errors.append(f"{company.get('name', company_id)} {target_period}: {exc}")
            continue

        if period != target_period or item.get("revenue") is None:
            errors.append(f"{company.get('name', company_id)} {target_period}: 재무자료 미공시")
            continue

        history = {
            entry["period"]: entry
            for entry in company.get("quarterlyHistory", [])
            if entry.get("period")
        }

        if quarter == 4:
            previous = [history.get(f"{year}Q{value}") for value in (1, 2, 3)]
            if all(previous):
                for key in ("revenue", "operatingIncome", "netIncome"):
                    if (
                        item.get(key) is not None
                        and all(entry.get(key) is not None for entry in previous)
                    ):
                        item[key] -= sum(entry[key] for entry in previous)
                item["basis"] = "연결 단일분기(연간-1~3Q)"
                with_margins(item)

        history[target_period] = item
        periods = sorted(history)[-12:]
        company["quarterlyHistory"] = [history[value] for value in periods]
        company["updatedAt"] = now_iso()
        updated_companies.append(company.get("name", company_id))

    if updated_companies:
        service._source_status(
            working,
            "twse",
            "live",
            f"대만 3사 월매출·분기실적 갱신 완료 ({target_period})",
        )
        with service.lock:
            service.dashboard = working
            atomic_write_json(CACHE_FILE, working)

    return {
        "ok": bool(updated_companies),
        "updatedSources": [f"MOPS {target_period}"] if updated_companies else [],
        "updatedCompanies": updated_companies,
        "errors": errors,
    }


def merge_results(*results: dict) -> dict:
    """Merge refresh results without failing the build on a single source."""
    updated_sources: list[str] = []
    errors: list[str] = []
    for result in results:
        for source in result.get("updatedSources", []):
            if source not in updated_sources:
                updated_sources.append(source)
        errors.extend(result.get("errors", []))
    return {
        "ok": bool(updated_sources),
        "updatedSources": updated_sources,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-refresh", action="store_true", help="Build from existing seed/cache only.")
    parser.add_argument(
        "--spot-only",
        action="store_true",
        help="Refresh only public DRAMeXchange spot prices before building.",
    )
    parser.add_argument(
        "--spot-china-only",
        action="store_true",
        help="Refresh DRAM spot prices plus GDS/VNET China IDC data before building.",
    )
    args = parser.parse_args()

    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8765")
    os.environ.setdefault("REFRESH_AT", "12:30")
    os.environ.setdefault("REFRESH_ON_STARTUP", "0")
    os.environ.setdefault("ENABLE_CHINA_IDC", "0")

    from server import SERVICE

    if not args.no_refresh:
        if args.spot_china_only:
            result = refresh_spot_and_china_only(SERVICE)
        elif args.spot_only:
            result = refresh_spot_prices_only(SERVICE)
        else:
            full_result = SERVICE.refresh("github-pages")
            twse_backfill_result = refresh_latest_completed_twse_quarter(SERVICE)
            result = merge_results(full_result, twse_backfill_result)

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
