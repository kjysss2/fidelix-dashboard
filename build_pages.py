금요일 오후 9:01
어제 오후 8:15
오늘 오전 7:10
지금되고있는거지?
저기 느낌표 표시는 괜찮은거야?

네, 저 회색 느낌표는 크게 문제 있는 표시가 아닙니다.

지금 화면에서는 Update build_pages.py 실행이 진행되던 중 새 pages.yml 커밋이 올라오면서 이전 실행이 취소된 상태로 보입니다. 현재 워크플로에 아래 설정이 있어서 그렇습니다.

concurrency:
  group: github-pages
  cancel-in-progress: true

즉, 새 실행이 시작되면 이전 실행을 자동으로 중단합니다.

확인할 것은 맨 위 Update pages.yml 실행입니다.

초록색 체크 → 정상 완료
빨간색 X → 오류 발생
회색 느낌표 → 이전 실행 취소·중단 가능성
노란색 회전 표시 → 현재 실행 중

따라서 맨 위 실행만 초록색 체크로 끝나면 괜찮습니다.

난야 26.2Q업데이트안되는데?
4m 25s 동안 처리함

맞습니다. 자동화는 실행됐지만 난야 2026년 2분기 분기실적은 수집되지 않았습니다.

현재 저장된 데이터는 7월 12일 07:17에 전체 갱신됐고 오류도 없는 것으로 기록됐지만, 난야는 6월 월매출까지만 갱신됐으며 분기실적은 여전히 2026Q1에서 끝납니다.

원인

기존 수정본은 난야 2분기 자료를 MOPS 정식 분기재무제표 페이지에서 찾도록 만들었습니다.

그런데 난야가 7월 10일 발표한 것은 미감사 잠정실적입니다. 난야 공식 재무보고서 페이지에도 현재 2026년 자료는 1분기 보고서만 올라와 있습니다.

발표된 잠정 수치는:

매출: NT$825.5억
순이익: NT$501.9억
매출총이익률: 79.5%

입니다.

즉, 워크플로 오류가 아니라 정식 재무제표만 찾는 데이터 소스 선택이 잘못된 것입니다.

수정본

다음 파일로 현재 build_pages.py를 전체 교체하세요.

build_pages_nanya_fix.py

다운로드 후 파일 이름을 반드시:

build_pages.py

로 해서 저장소 루트의 기존 파일을 교체하면 됩니다.

pages.yml은 다시 수정할 필요 없습니다.

이번 수정본의 작동 방식
기존 MOPS 정식 분기재무제표를 먼저 확인
정식 보고서가 없으면 TWSE 일일 중요공시에서 自結, 損益, 財務 잠정실적을 확인
이번에 이미 지나간 난야 2026Q2는 별도 보완값으로 즉시 입력
나중에 정식 MOPS 재무제표가 올라오면 잠정값을 정식값으로 자동 교체

이번 Q2에는 다음 값이 들어갑니다.

매출: NT$ 825.49억
순이익: NT$ 501.90억
순이익률: 약 60.8%
영업이익: 정식 공시 확인 전까지 미표시

영업이익은 현재 확인 가능한 잠정 발표 자료에 명확한 숫자가 없어 임의 계산하지 않았습니다.

적용 후 실행
GitHub 저장소
→ build_pages.py
→ 연필 아이콘
→ 기존 내용 전체 삭제
→ 수정본 전체 붙여넣기
→ Commit changes

그다음:

Actions
→ Build and deploy GitHub Pages
→ Run workflow
→ Run workflow

정상 완료되면 Actions가 Update dashboard data [skip ci] 커밋을 새로 만들고, 난야 그래프의 마지막 분기가 2026Q2로 표시됩니다. 

이거 자동으로 업데이트는 안되?
19s 동안 처리함

현재 상태에서는 난야 잠정실적은 자동 업데이트되지 않습니다.

저장소의 build_pages.py를 확인해보면 아직 MOPS 정식 재무제표만 조회하고 있습니다.

period, item = service._fetch_mops_quarter(code, year, quarter)

정식 자료가 없으면 그대로 건너뛰기 때문에, 워크플로가 2시간마다 실행돼도 난야 2026Q2는 계속 안 나옵니다.

다만 잠정실적 대응 수정본을 한 번만 커밋하면 그다음부터는 자동입니다.

작동 순서는 다음과 같습니다.

2시간마다 GitHub Actions 실행
MOPS 정식 분기실적 확인
정식 자료가 없으면 TWSE 중요공시의 잠정실적 확인
잠정실적을 분기 그래프에 반영
나중에 정식 재무제표가 올라오면 정식 수치로 교체

현재 pages.yml은 이미 2시간마다 전체 빌드하도록 설정돼 있습니다.

따라서 필요한 수동 작업은 딱 한 번입니다.

build_pages_nanya_fix.py 다운로드
→ 파일 이름을 build_pages.py로 변경
→ 저장소의 기존 build_pages.py 전체 교체
→ Commit changes

build_pages_nanya_fix.py

커밋하면 새 Actions가 자동으로 실행되므로 별도로 Run workflow를 누르지 않아도 됩니다. 그 실행이 끝나면 난야 2026Q2가 반영되고, 이후부터는 2시간 주기로 자동 확인합니다.

단, 향후 TWSE가 잠정실적 공시 문구 형식을 크게 바꾸면 파서 수정이 다시 필요할 수 있습니다.

그냥 니가 준 소스코드를 build_pages.py에 덮어쓰기 해도되지?

네. 기존 build_pages.py 내용을 전부 지우고, 제가 준 build_pages_nanya_fix.py의 내용을 그대로 붙여넣으면 됩니다.

주의할 점은 파일명을 새로 만들지 말고 기존 경로의 파일을 그대로 수정하는 것입니다.

fidelix-dashboard/build_pages.py

순서는:

build_pages.py 열기
→ 연필 아이콘
→ 기존 내용 전체 삭제
→ 제가 준 코드 전체 붙여넣기
→ Commit changes

pages.yml은 건드리지 않아도 됩니다. 커밋하면 push 이벤트로 Actions가 자동 실행됩니다. 최신 실행이 초록색 체크로 끝나면 적용 완료입니다.

build_pages_nanya_fix.py
#!/usr/bin/env python3
"""Build a static GitHub Pages version of the dashboard."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"
TWSE_MATERIAL_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"

# 2026Q2 was announced as unaudited preliminary results before the formal
# MOPS quarterly financial statement became available. This one-time fallback
# fills the missed historical announcement. A later formal MOPS filing will
# automatically overwrite the same period.
NANYA_PRELIMINARY_FALLBACKS = {
    "2026Q2": {
        "revenue": 82549.073,  # TWD million; Apr + May + Jun monthly revenue
        "operatingIncome": None,
        "netIncome": 50190.0,  # TWD million; unaudited preliminary result
        "source": "Nanya unaudited preliminary results",
        "sourceUrl": "https://www.reuters.com/world/asia-pacific/taiwanese-chipmaker-nanya-plans-6-billion-spending-2027-riding-ai-boom-2026-07-10/",
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
    targets = {"2337": "macronix", "2344": "winbond", "2408": "nanya"}

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

        # Nanya often announces unaudited earnings before the formal MOPS
        # financial statement is posted. Check TWSE material disclosures first.
        if item is None and company_id == "nanya":
            try:
                item = preliminary_nanya_from_twse(service, working, year, quarter)
            except Exception as exc:
                errors.append(f"Nanya 잠정실적 공시 조회: {exc}")

            # One-time historical fallback for 2026Q2, which was already
            # announced before this collector was enabled.
            if item is None:
                item = preliminary_nanya_fallback(service, working, year, quarter)

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

        if company_id == "nanya" and "잠정" in str(item.get("basis", "")):
            add_preliminary_feed(working, item)

    if updated_companies:
        service._source_status(
            working,
            "twse",
            "live",
            f"대만 3사 월매출·분기실적 갱신 완료 ({target_period})",
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

인사이트 얻기
build_pages_nanya_fix.py
#!/usr/bin/env python3
"""Build a static GitHub Pages version of the dashboard."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"
TWSE_MATERIAL_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"

# 2026Q2 was announced as unaudited preliminary results before the formal
# MOPS quarterly financial statement became available. This one-time fallback
# fills the missed historical announcement. A later formal MOPS filing will
# automatically overwrite the same period.
NANYA_PRELIMINARY_FALLBACKS = {
    "2026Q2": {
        "revenue": 82549.073,  # TWD million; Apr + May + Jun monthly revenue
        "operatingIncome": None,
        "netIncome": 50190.0,  # TWD million; unaudited preliminary result
        "source": "Nanya unaudited preliminary results",
        "sourceUrl": "https://www.reuters.com/world/asia-pacific/taiwanese-chipmaker-nanya-plans-6-billion-spending-2027-riding-ai-boom-2026-07-10/",
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
    targets = {"2337": "macronix", "2344": "winbond", "2408": "nanya"}

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

        # Nanya often announces unaudited earnings before the formal MOPS
        # financial statement is posted. Check TWSE material disclosures first.
        if item is None and company_id == "nanya":
            try:
                item = preliminary_nanya_from_twse(service, working, year, quarter)
            except Exception as exc:
                errors.append(f"Nanya 잠정실적 공시 조회: {exc}")

            # One-time historical fallback for 2026Q2, which was already
            # announced before this collector was enabled.
            if item is None:
                item = preliminary_nanya_fallback(service, working, year, quarter)

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

        if company_id == "nanya" and "잠정" in str(item.get("basis", "")):
            add_preliminary_feed(working, item)

    if updated_companies:
        service._source_status(
            working,
            "twse",
            "live",
            f"대만 3사 월매출·분기실적 갱신 완료 ({target_period})",
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
