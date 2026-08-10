#!/usr/bin/env python3
"""Build a static GitHub Pages version of the dashboard."""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import re
import shutil
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"
TWSE_MATERIAL_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
NANYA_PRESS_RELEASES_API = (
    "https://www.nanya.com/en/Activity?Action=IR_PressCenter_year_Item"
    "&year={year}&En_Pagetype=0"
)
NANYA_PRESS_RELEASE_BASE_URL = "https://www.nanya.com/en/IR/16/"

# 2026Q2 was announced as unaudited preliminary results before the formal
# MOPS quarterly financial statement became available. This one-time fallback
# fills the missed historical announcement. A later formal MOPS filing will
# automatically overwrite the same period.
NANYA_PRELIMINARY_FALLBACKS = {
    "2026Q2": {
        "revenue": 82549.0,
        "operatingIncome": 60826.0,
        "netIncome": 50192.0,
        "source": "Nanya official IR",
        "sourceUrl": "https://www.nanya.com/en/IR/16/?IRId=13150",
    },
}


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


def latest_completed_quarter(now: datetime) -> tuple[int, int]:
    """Return the most recently completed calendar quarter."""
    current_quarter = (now.month - 1) // 3 + 1
    if current_quarter == 1:
        return now.year - 1, 4
    return now.year, current_quarter - 1


def roc_date_to_iso(value: str) -> str | None:
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 7:
        return None
    try:
        year = int(digits[:3]) + 1911
        month = int(digits[3:5])
        day = int(digits[5:7])
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return None


def period_is_in_text(text: str, year: int, quarter: int) -> bool:
    roc_year = year - 1911
    quarter_zh = {1: "一", 2: "二", 3: "三", 4: "四"}[quarter]
    candidates = (
        f"{year}年第{quarter}季",
        f"{year}年{quarter_zh}季",
        f"{roc_year}年第{quarter}季",
        f"{roc_year}年{quarter_zh}季",
        f"{year}Q{quarter}",
        f"{quarter}Q{str(year)[-2:]}",
    )
    compact = re.sub(r"\s+", "", text).upper()
    return any(candidate.upper() in compact for candidate in candidates)


def amount_to_twd_million(number: str, unit: str) -> float | None:
    try:
        value = float(number.replace(",", "").strip())
    except ValueError:
        return None
    if unit == "億元":
        return value * 100
    if unit == "百萬元":
        return value
    if unit in {"千元", "仟元"}:
        return value / 1000
    if unit == "元":
        return value / 1_000_000
    return None


def extract_twd_million(text: str, labels: list[str]) -> float | None:
    normalized = (
        text.replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("－", "-")
    )
    label_pattern = "(?:" + "|".join(labels) + ")"
    patterns = [
        rf"{label_pattern}[^\d\-]{{0,40}}(?:新台幣|NT\$|NTD)?\s*([\-]?\d[\d,]*(?:\.\d+)?)\s*(億元|百萬元|千元|仟元|元)",
        rf"(?:新台幣|NT\$|NTD)?\s*([\-]?\d[\d,]*(?:\.\d+)?)\s*(億元|百萬元|千元|仟元|元)[^。\n]{{0,30}}{label_pattern}",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.I | re.S)
        if match:
            value = amount_to_twd_million(match.group(1), match.group(2))
            if value is not None:
                return value
    return None


def quarterly_months(year: int, quarter: int) -> list[str]:
    first_month = (quarter - 1) * 3 + 1
    return [f"{year}-{month:02d}" for month in range(first_month, first_month + 3)]


def sum_monthly_revenue(company: dict, year: int, quarter: int) -> float | None:
    required = quarterly_months(year, quarter)
    history = {
        item.get("period"): item.get("revenue")
        for item in company.get("monthlyHistory", [])
    }
    if not all(history.get(period) is not None for period in required):
        return None
    return sum(float(history[period]) for period in required)


def html_to_text(source: str) -> str:
    """Collapse an HTML fragment into normalized visible text."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", source)).split())


class AnchorTextParser(HTMLParser):
    """Collect anchor destinations and their visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a" or self._href is not None:
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._href is None:
            return
        self.links.append((self._href, " ".join("".join(self._text).split())))
        self._href = None
        self._text = []


def find_nanya_results_release_url(source: str, year: int, quarter: int) -> str | None:
    """Find a quarter's earnings release from Nanya's official IR listing."""
    quarter_name = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}[quarter]
    expected = f"Nanya Technology Reports Results for the {quarter_name} Quarter {year}".casefold()
    parser = AnchorTextParser()
    parser.feed(source)
    for href, text in parser.links:
        if expected not in text.casefold():
            continue
        return urllib.parse.urljoin(NANYA_PRESS_RELEASE_BASE_URL, html.unescape(href))
    return None


def parse_nanya_results_release(
    source: str,
    year: int,
    quarter: int,
    source_url: str,
) -> dict | None:
    """Parse Nanya's official English quarterly earnings release."""
    from server import with_margins

    text = html_to_text(source)
    quarter_name = {1: "first", 2: "second", 3: "third", 4: "fourth"}[quarter]
    if f"{quarter_name} quarter {year}" not in text.casefold():
        return None

    def amount(label: str) -> float | None:
        match = re.search(
            rf"{label}[^.]*?NT\$\s*([\d,]+(?:\.\d+)?)\s*million",
            text,
            flags=re.I,
        )
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    revenue = amount(r"quarterly sales revenue")
    operating_income = amount(r"operating income of the quarter")
    net_income = amount(r"\bnet income")
    if revenue is None or operating_income is None or net_income is None:
        return None

    date_match = re.search(r"\b(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\b", text)
    announcement_date = None
    if date_match:
        announcement_date = "-".join(
            (date_match.group(1), date_match.group(2).zfill(2), date_match.group(3).zfill(2))
        )

    return with_margins({
        "period": f"{year}Q{quarter}",
        "revenue": revenue,
        "operatingIncome": operating_income,
        "netIncome": net_income,
        "currency": "TWD",
        "basis": "연결 단일분기·미감사 실적발표",
        "source": "Nanya official IR",
        "sourceUrl": source_url,
        "announcementDate": announcement_date,
        "isPreliminary": True,
    })


def preliminary_nanya_from_official_ir(year: int, quarter: int) -> dict | None:
    """Discover and parse Nanya's latest official quarterly press release."""
    from server import fetch_bytes, fetch_json

    response = fetch_json(NANYA_PRESS_RELEASES_API.format(year=year))
    listing = response.get("msg", "") if isinstance(response, dict) else ""
    release_url = find_nanya_results_release_url(listing, year, quarter)
    if not release_url:
        return None
    release = fetch_bytes(release_url, timeout=35).decode("utf-8", "replace")
    return parse_nanya_results_release(release, year, quarter, release_url)


def preliminary_nanya_from_twse(service, data: dict, year: int, quarter: int) -> dict | None:
    """Read Nanya preliminary quarterly earnings from TWSE material disclosures."""
    from server import fetch_json, with_margins

    rows = fetch_json(TWSE_MATERIAL_URL)
    if not isinstance(rows, list):
        return None

    nanya = service._company(data, "nanya")
    for row in rows:
        if str(row.get("公司代號", "")).strip() != "2408":
            continue

        subject = str(row.get("主旨 ") or row.get("主旨") or "")
        explanation = str(row.get("說明") or "")
        text = f"{subject}\n{explanation}"

        if not period_is_in_text(text, year, quarter):
            continue
        if not any(keyword in text for keyword in ("自結", "損益", "財務", "營運結果", "獲利")):
            continue

        revenue = extract_twd_million(text, [r"合併營業收入", r"營業收入", r"合併營收", r"營收"])
        operating_income = extract_twd_million(
            text,
            [r"營業利益(?:\(損失\))?", r"營業淨利", r"營業損益"],
        )
        net_income = extract_twd_million(
            text,
            [
                r"歸屬(?:於)?母公司業主(?:之)?淨利",
                r"本期淨利(?:\(淨損\))?",
                r"稅後淨利",
                r"合併淨利",
                r"淨利",
            ],
        )

        revenue = revenue if revenue is not None else sum_monthly_revenue(nanya, year, quarter)
        if revenue is None or (operating_income is None and net_income is None):
            continue

        item = {
            "period": f"{year}Q{quarter}",
            "revenue": revenue,
            "operatingIncome": operating_income,
            "netIncome": net_income,
            "currency": "TWD",
            "basis": "연결 단일분기·미감사 잠정실적",
            "source": "TWSE重大訊息·自結",
            "sourceUrl": TWSE_MATERIAL_URL,
            "announcementDate": roc_date_to_iso(row.get("發言日期", "")),
        }
        return with_margins(item)

    return None


def preliminary_nanya_fallback(service, data: dict, year: int, quarter: int) -> dict | None:
    """Use a verified one-time fallback for a missed historical announcement."""
    from server import with_margins

    period = f"{year}Q{quarter}"
    fallback = NANYA_PRELIMINARY_FALLBACKS.get(period)
    if not fallback:
        return None

    nanya = service._company(data, "nanya")
    revenue = sum_monthly_revenue(nanya, year, quarter)
    if revenue is None:
        revenue = fallback["revenue"]

    return with_margins({
        "period": period,
        "revenue": revenue,
        "operatingIncome": fallback.get("operatingIncome"),
        "netIncome": fallback.get("netIncome"),
        "currency": "TWD",
        "basis": "연결 단일분기·미감사 잠정실적",
        "source": fallback["source"],
        "sourceUrl": fallback["sourceUrl"],
        "announcementDate": "2026-07-10",
        "isPreliminary": True,
    })


def upsert_quarter(company: dict, item: dict) -> None:
    history = {
        entry["period"]: entry
        for entry in company.get("quarterlyHistory", [])
        if entry.get("period")
    }
    history[item["period"]] = item
    periods = sorted(history)[-12:]
    company["quarterlyHistory"] = [history[period] for period in periods]


def add_preliminary_feed(data: dict, item: dict) -> None:
    period = item["period"]
    feed_id = f"nanya-preliminary-{period.lower()}"
    existing = [entry for entry in data.get("feed", []) if entry.get("id") != feed_id]
    existing.append({
        "id": feed_id,
        "companyId": "nanya",
        "company": "Nanya",
        "date": item.get("announcementDate") or f"{period[:4]}-01-01",
        "title": f"{period} 미감사 잠정실적",
        "type": "실적",
        "url": item.get("sourceUrl") or TWSE_MATERIAL_URL,
        "source": item.get("source", "잠정실적"),
        "isNew": True,
    })
    data["feed"] = sorted(
        existing,
        key=lambda entry: re.sub(r"\D", "", str(entry.get("date", ""))),
        reverse=True,
    )[:18]


def refresh_latest_completed_twse_quarter(service) -> dict:
    """Refresh the latest completed TWSE quarter with preliminary fallback."""
    from server import CACHE_FILE, KST, atomic_write_json, now_iso, with_margins

    year, quarter = latest_completed_quarter(datetime.now(KST))
    target_period = f"{year}Q{quarter}"
    targets = {
        "2337": "macronix",
        "2344": "winbond",
        "2408": "nanya",
        "3006": "esmt",
    }

    with service.lock:
        working = copy.deepcopy(service.dashboard)

    errors: list[str] = []
    updated_companies: list[str] = []

    for code, company_id in targets.items():
        company = service._company(working, company_id)
        item = None

        try:
            period, formal_item = service._fetch_mops_quarter(code, year, quarter)
            if period == target_period and formal_item.get("revenue") is not None:
                item = formal_item
        except Exception as exc:
            if company_id != "nanya":
                errors.append(f"{company.get('name', company_id)} {target_period}: {exc}")

        # Nanya announces unaudited earnings before the formal MOPS statement.
        # Prefer its official IR release, then fall back to TWSE material news.
        if item is None and company_id == "nanya":
            lookup_errors: list[str] = []
            try:
                item = preliminary_nanya_from_official_ir(year, quarter)
            except Exception as exc:
                lookup_errors.append(f"Nanya 공식 IR 조회: {exc}")

            if item is None:
                try:
                    item = preliminary_nanya_from_twse(service, working, year, quarter)
                except Exception as exc:
                    lookup_errors.append(f"Nanya 잠정실적 공시 조회: {exc}")

            # Verified fallback keeps a completed release from disappearing
            # during a temporary Nanya/TWSE outage.
            if item is None:
                item = preliminary_nanya_fallback(service, working, year, quarter)
            if item is None:
                errors.extend(lookup_errors)

        if item is None:
            continue

        if quarter == 4 and "잠정" not in str(item.get("basis", "")):
            history = {
                entry["period"]: entry
                for entry in company.get("quarterlyHistory", [])
                if entry.get("period")
            }
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

        upsert_quarter(company, item)
        company["updatedAt"] = now_iso()
        updated_companies.append(company.get("name", company_id))

        if company_id == "nanya" and (
            item.get("isPreliminary") or "잠정" in str(item.get("basis", ""))
        ):
            add_preliminary_feed(working, item)

    if updated_companies:
        service._source_status(
            working,
            "twse",
            "live",
            f"대만 4사 월매출·분기실적 갱신 완료 ({target_period})",
        )

    existing_errors = list(working.get("system", {}).get("lastRefreshErrors", []))
    working["system"]["lastRefreshErrors"] = existing_errors + errors

    with service.lock:
        service.dashboard = working
        atomic_write_json(CACHE_FILE, working)

    return {
        "ok": bool(updated_companies),
        "updatedSources": [f"MOPS/TWSE {target_period}"] if updated_companies else [],
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
