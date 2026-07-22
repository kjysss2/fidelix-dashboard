#!/usr/bin/env python3
"""Fidelix peer follow-up dashboard."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import io
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
SEED_FILE = DATA_DIR / "seed.json"
CACHE_FILE = DATA_DIR / "cache.json"
SPOT_HISTORY_FILE = DATA_DIR / "spot_history.json"
JEJU_TRADE_FILE = DATA_DIR / "jeju_trade.json"
KST = timezone(timedelta(hours=9))
DRAMEXCHANGE_URL = "https://www.dramexchange.com/"
STOCKEASY_MEMORY_URL = "https://stockeasy.intellio.kr/market-analysis?tab=memory-prices"
TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
MOPS_HISTORY_URL = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{roc_year}_{month}_0.html"
MOPS_FINANCIAL_URL = "https://mopsov.twse.com.tw/server-java/t164sb01?step=1&CO_ID={code}&SYEAR={year}&SSEASON={quarter}&REPORT_ID=C"
TWSE_INCOME_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci"
EASTMONEY_INCOME_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SSE_QUERY_URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"
DOSILICON_H1_2026_PRELIMINARY = {
    "announcementDate": "2026-07-21",
    "source": "SSE 2026H1 예비실적",
    "sourceUrl": "https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-07-21/688110_20260721_8A63.pdf",
    "h1RevenueRange": [1490.0, 1530.0],
    "h1NetIncomeRange": [640.0, 680.0],
    "q2NetIncomeQoQRange": [262.81, 291.74],
}
DART_BASE = "https://opendart.fss.or.kr/api"
GDS_IR_URL = "https://investors.gds-services.com/financial-information/quarterly-results/"
VNET_IR_URL = "https://ir.vnet.com/financial-information/quarterly-results/"
GDS_FALLBACK_PRESENTATION_URL = "https://investors.gds-services.com/system/files-encrypted/nasdaq_kms/assets/2026/05/20/6-54-39/GDS%201Q26%20Earnings%20Presentation%200520%201700.pdf"
VNET_FALLBACK_PRESENTATION_URL = "https://ir.vnet.com/static-files/2b16e7ee-2d06-4379-9035-266b7a27d52d"
VNET_FALLBACK_RELEASE_URL = "https://ir.vnet.com/news-releases/news-release-details/vnet-reports-unaudited-first-quarter-2026-financial-results"


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def load_local_env() -> None:
    """Load simple KEY=VALUE settings without exposing them to the browser."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def fetch_bytes(url: str, *, headers: dict | None = None, timeout: int = 25, attempts: int = 3) -> bytes:
    request_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FidelixFollowUp/1.0)",
        "Accept": "application/json,text/plain,*/*",
    }
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # network boundaries are intentionally resilient
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.2 * (attempt + 1))
    if os.name == "nt":
        try:
            command = ["curl.exe", "-L", "--max-time", str(timeout), "-sS", url]
            completed = subprocess.run(command, capture_output=True, timeout=timeout + 6, check=True)
            if completed.stdout:
                return completed.stdout
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"데이터 요청 실패: {last_error}")


def fetch_json(url: str, *, headers: dict | None = None) -> dict | list:
    payload = fetch_bytes(url, headers=headers)
    return json.loads(payload.decode("utf-8-sig"))


def clean_number(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def disclosure_sort_key(item: dict) -> str:
    """Normalize YYYYMMDD and YYYY-MM-DD dates to one sortable key."""
    digits = re.sub(r"\D", "", str(item.get("date", "")))
    return digits[:14].ljust(14, "0")


def format_krw_eok(value_won: float | None) -> str:
    if value_won is None:
        return "—"
    return f"{value_won / 100_000_000:,.1f}억원"


def roc_period(value: str) -> str:
    if len(value) != 5:
        return value
    return f"{int(value[:3]) + 1911}-{value[3:]}"


class CellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.buffer: list[str] = []
        self.cells: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "td":
            self.in_cell = True
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "td" and self.in_cell:
            self.cells.append(" ".join("".join(self.buffer).split()))
            self.in_cell = False
            self.buffer = []


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            self.current_href = href
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href:
            self.links.append({
                "href": self.current_href,
                "text": " ".join("".join(self.current_text).split()),
            })
            self.current_href = None
            self.current_text = []


def month_range(end_period: str, count: int) -> list[str]:
    year, month = (int(part) for part in end_period.split("-", 1))
    result: list[str] = []
    for offset in range(count - 1, -1, -1):
        absolute = year * 12 + (month - 1) - offset
        result.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
    return result


def quarter_range(end_period: str, count: int) -> list[str]:
    match = re.fullmatch(r"(\d{4})Q([1-4])", end_period)
    if not match:
        return []
    year, quarter = int(match.group(1)), int(match.group(2))
    absolute_end = year * 4 + quarter - 1
    return [f"{absolute // 4:04d}Q{absolute % 4 + 1}" for absolute in range(absolute_end - count + 1, absolute_end + 1)]


def with_margins(item: dict) -> dict:
    revenue = item.get("revenue")
    item["operatingMargin"] = (item.get("operatingIncome") / revenue * 100) if revenue not in (None, 0) and item.get("operatingIncome") is not None else None
    item["netMargin"] = (item.get("netIncome") / revenue * 100) if revenue not in (None, 0) and item.get("netIncome") is not None else None
    return item


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def plain_text_from_html(value: str) -> str:
    return normalize_spaces(html.unescape(re.sub(r"<[^>]+>", " ", value)))


def extract_pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("PDF 텍스트 추출 모듈(pypdf)을 찾지 못했습니다") from exc
    reader = PdfReader(io.BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def first_number(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_number(match.group(1))
    return None


def first_int(patterns: list[str], text: str) -> int | None:
    value = first_number(patterns, text)
    return int(value) if value is not None else None


class DashboardService:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.refreshing = False
        self.seed = read_json(SEED_FILE)
        self.dashboard = copy.deepcopy(self.seed)
        if CACHE_FILE.exists():
            try:
                cached = read_json(CACHE_FILE)
                if cached.get("schemaVersion") == self.dashboard.get("schemaVersion"):
                    self.dashboard = cached
            except Exception:
                pass
        self._ensure_defaults(self.dashboard)
        self._merge_spot_history_file(self.dashboard)
        self._merge_jeju_trade_file(self.dashboard)

    def _ensure_defaults(self, data: dict) -> None:
        """Add new dashboard sections to older cache files without discarding live data."""
        seed_sources = {source["id"]: source for source in self.seed.get("sources", [])}
        existing_sources = {source["id"]: source for source in data.get("sources", [])}
        merged_sources = []
        for source_id, seed_source in seed_sources.items():
            current = existing_sources.get(source_id)
            merged_sources.append(current if current else copy.deepcopy(seed_source))
        for source in data.get("sources", []):
            if source.get("id") not in seed_sources:
                merged_sources.append(source)
        data["sources"] = merged_sources

        if "chinaServerOrders" not in data:
            data["chinaServerOrders"] = copy.deepcopy(self.seed.get("chinaServerOrders", {
                "updatedAt": None,
                "note": "공식 IR 원문에서 확인되는 중국 IDC 신규수주와 백로그만 표시합니다.",
                "companies": [],
            }))

        if "spotPrices" not in data:
            data["spotPrices"] = copy.deepcopy(self.seed.get("spotPrices", {
                "updatedAt": None,
                "sourceLabel": "DRAMeXchange 공개 현물가",
                "sourceUrl": DRAMEXCHANGE_URL,
                "note": "공개 홈의 Session Average를 매일 저장해 자체 추이를 만듭니다.",
                "products": [],
            }))

        if "jejuTrade" not in data:
            data["jejuTrade"] = copy.deepcopy(self.seed.get("jejuTrade", {
                "updatedAt": None,
                "sourceLabel": "User-provided trade table",
                "basis": "Jeju Semiconductor trade data",
                "monthlyColumns": [],
                "monthly": [],
                "quarterlyColumns": [],
                "quarterly": [],
            }))

    @staticmethod
    def _merge_jeju_trade_file(data: dict) -> None:
        if not JEJU_TRADE_FILE.exists():
            return
        try:
            data["jejuTrade"] = read_json(JEJU_TRADE_FILE)
        except Exception:
            data.setdefault("jejuTrade", {
                "updatedAt": None,
                "sourceLabel": "User-provided trade table",
                "basis": "Jeju Semiconductor trade data",
                "monthlyColumns": [],
                "monthly": [],
                "quarterlyColumns": [],
                "quarterly": [],
            })

    @staticmethod
    def _spot_products(data: dict) -> dict[str, dict]:
        spot = data.setdefault("spotPrices", {
            "updatedAt": None,
            "sourceLabel": "DRAMeXchange 공개 현물가",
            "sourceUrl": DRAMEXCHANGE_URL,
            "note": "공개 홈의 Session Average를 매일 저장해 자체 추이를 만듭니다.",
            "products": [],
        })
        legacy_ids = {"ddr4_16gb_3200"}
        spot["products"] = [
            product for product in spot.setdefault("products", [])
            if product.get("id") not in legacy_ids
        ]
        return {product.get("id"): product for product in spot.setdefault("products", [])}

    def _merge_spot_history_file(self, data: dict) -> None:
        if not SPOT_HISTORY_FILE.exists():
            return
        try:
            stored = read_json(SPOT_HISTORY_FILE)
        except Exception:
            return
        stored_products = {product.get("id"): product for product in stored.get("products", [])}
        products = self._spot_products(data)
        for product_id, stored_product in stored_products.items():
            current = products.get(product_id)
            if not current:
                current = copy.deepcopy(stored_product)
                current.setdefault("unit", "USD")
                current.setdefault("color", {
                    "ddr5_16gb_4800_5600": "#2e7a8f",
                    "ddr4_8gb_3200": "#9a6f2e",
                }.get(product_id, "#6b6258"))
                data["spotPrices"].setdefault("products", []).append(current)
                products[product_id] = current
            history = sorted(stored_product.get("history", []), key=lambda item: item.get("date", ""))
            if history:
                current["history"] = history
                current["latest"] = history[-1]
        if stored.get("updatedAt"):
            data["spotPrices"]["updatedAt"] = stored["updatedAt"]
        for key in ("sourceLabel", "sourceUrl", "note"):
            if stored.get(key):
                data["spotPrices"][key] = stored[key]

    @staticmethod
    def _write_spot_history_file(data: dict) -> None:
        spot = data.get("spotPrices", {})
        payload = {
            "updatedAt": spot.get("updatedAt"),
            "sourceLabel": spot.get("sourceLabel"),
            "sourceUrl": spot.get("sourceUrl"),
            "products": [
                {
                    "id": product.get("id"),
                    "name": product.get("name"),
                    "label": product.get("label"),
                    "unit": product.get("unit"),
                    "color": product.get("color"),
                    "history": product.get("history", []),
                }
                for product in spot.get("products", [])
            ],
        }
        atomic_write_json(SPOT_HISTORY_FILE, payload)

    def snapshot(self) -> dict:
        with self.lock:
            result = copy.deepcopy(self.dashboard)
            result["system"]["refreshing"] = self.refreshing
            result["system"]["dartConfigured"] = bool(os.getenv("DART_API_KEY"))
            result["system"]["refreshAt"] = os.getenv("REFRESH_AT", "08:00")
            result["feed"] = sorted(result.get("feed", []), key=disclosure_sort_key, reverse=True)
            return result

    def refresh(self, reason: str = "manual") -> dict:
        with self.lock:
            if self.refreshing:
                return {"ok": True, "message": "이미 갱신 중입니다.", "dashboard": self.snapshot()}
            self.refreshing = True

        errors: list[str] = []
        updated_sources: list[str] = []
        try:
            with self.lock:
                working = copy.deepcopy(self.dashboard)
            try:
                self._refresh_twse(working)
                self._refresh_mops_history(working)
                self._refresh_twse_quarterly(working)
                updated_sources.append("TWSE")
            except Exception as exc:
                errors.append(f"TWSE: {exc}")
                self._source_error(working, "twse", str(exc))

            try:
                self._refresh_sse(working)
                self._refresh_dosilicon_quarterly(working)
                updated_sources.append("SSE")
            except Exception as exc:
                errors.append(f"SSE: {exc}")
                self._source_error(working, "sse", str(exc))

            try:
                self._refresh_dramexchange_spot(working)
                updated_sources.append("DRAMeXchange")
            except Exception as exc:
                errors.append(f"DRAMeXchange: {exc}")
                self._source_error(working, "dramexchange", str(exc))

            if os.getenv("ENABLE_CHINA_IDC", "0").strip().lower() in {"1", "true", "yes", "y"}:
                try:
                    self._refresh_gds_orders(working)
                    updated_sources.append("GDS IR")
                except Exception as exc:
                    errors.append(f"GDS IR: {exc}")
                    self._source_error(working, "gds_ir", str(exc))

                try:
                    self._refresh_vnet_orders(working)
                    updated_sources.append("VNET IR")
                except Exception as exc:
                    errors.append(f"VNET IR: {exc}")
                    self._source_error(working, "vnet_ir", str(exc))
            else:
                self._source_status(working, "gds_ir", "setup", "나중에 연결 예정")
                self._source_status(working, "vnet_ir", "setup", "나중에 연결 예정")

            if os.getenv("DART_API_KEY"):
                try:
                    self._refresh_dart(working, os.environ["DART_API_KEY"])
                    self._refresh_dart_quarterly(working, os.environ["DART_API_KEY"])
                    updated_sources.append("OpenDART")
                except Exception as exc:
                    errors.append(f"OpenDART: {exc}")
                    self._source_error(working, "dart", str(exc))
            else:
                self._source_status(working, "dart", "setup", "API 키 연결 필요")

            working["system"].update({
                "lastRefresh": now_iso(),
                "lastRefreshReason": reason,
                "lastRefreshErrors": errors,
            })
            with self.lock:
                self.dashboard = working
                atomic_write_json(CACHE_FILE, working)
            return {
                "ok": bool(updated_sources),
                "updatedSources": updated_sources,
                "errors": errors,
                "dashboard": self.snapshot(),
            }
        finally:
            with self.lock:
                self.refreshing = False

    @staticmethod
    def _company(data: dict, company_id: str) -> dict:
        return next(company for company in data["companies"] if company["id"] == company_id)

    @staticmethod
    def _source(data: dict, source_id: str) -> dict:
        return next(source for source in data["sources"] if source["id"] == source_id)

    def _source_status(self, data: dict, source_id: str, status: str, message: str) -> None:
        source = self._source(data, source_id)
        source.update({"status": status, "message": message, "checkedAt": now_iso()})

    def _source_error(self, data: dict, source_id: str, message: str) -> None:
        self._source_status(data, source_id, "error", message[:140])

    def _refresh_twse(self, data: dict) -> None:
        rows = fetch_json(TWSE_URL)
        if not isinstance(rows, list):
            raise RuntimeError("예상하지 못한 응답 형식")
        code_map = {"2344": "winbond", "2408": "nanya", "2337": "macronix"}
        found = 0
        for row in rows:
            company_id = code_map.get(row.get("公司代號"))
            if not company_id:
                continue
            found += 1
            company = self._company(data, company_id)
            revenue_thousand = clean_number(row.get("營業收入-當月營收"))
            revenue_million = revenue_thousand / 1000 if revenue_thousand is not None else None
            company["metrics"].update({
                "period": roc_period(row.get("資料年月", "")),
                "periodType": "월매출",
                "revenue": revenue_million,
                "revenueDisplay": f"NT$ {revenue_million / 100:,.1f}억" if revenue_million is not None else "—",
                "revenueYoY": clean_number(row.get("營業收入-去年同月增減(%)")),
                "revenueQoQ": clean_number(row.get("營業收入-上月比較增減(%)")),
                "operatingIncome": None,
                "operatingIncomeDisplay": "월매출 공시 미제공",
                "netIncome": None,
                "netIncomeDisplay": "월매출 공시 미제공",
                "currency": "TWD",
                "basis": "당월, NT$ million",
            })
            company.update({
                "updatedAt": now_iso(),
                "verification": "official",
                "sourceLabel": "대만거래소 월매출",
                "sourceUrl": TWSE_URL,
                "note": row.get("備註") or "대만거래소 월매출 공시",
            })
        if found != 3:
            raise RuntimeError(f"대상 3개사 중 {found}개사만 확인")
        self._source_status(data, "twse", "live", "3개사 월매출 갱신 완료")

    @staticmethod
    def _parse_mops_month(payload: bytes, period: str) -> dict[str, dict]:
        parser = CellParser()
        parser.feed(payload.decode("big5", "replace"))
        result: dict[str, dict] = {}
        for code in ("2337", "2344", "2408"):
            try:
                index = parser.cells.index(code)
                revenue_thousand = clean_number(parser.cells[index + 2])
                mom = clean_number(parser.cells[index + 5])
                yoy = clean_number(parser.cells[index + 6])
            except (ValueError, IndexError):
                continue
            if revenue_thousand is None:
                continue
            result[code] = {
                "period": period,
                "revenue": revenue_thousand / 1000,
                "mom": mom,
                "yoy": yoy,
            }
        return result

    def _fetch_mops_period(self, period: str) -> tuple[str, dict[str, dict]]:
        year, month = (int(part) for part in period.split("-", 1))
        url = MOPS_HISTORY_URL.format(roc_year=year - 1911, month=month)
        payload = fetch_bytes(url, headers={"Referer": "https://mops.twse.com.tw/"}, timeout=30)
        return period, self._parse_mops_month(payload, period)

    def _refresh_mops_history(self, data: dict) -> None:
        code_map = {"2344": "winbond", "2408": "nanya", "2337": "macronix"}
        end_period = self._company(data, "winbond")["metrics"]["period"]
        required_periods = month_range(end_period, 36)
        existing: dict[str, dict[str, dict]] = {code: {} for code in code_map}
        for code, company_id in code_map.items():
            for item in self._company(data, company_id).get("monthlyHistory", []):
                if item.get("period") in required_periods:
                    existing[code][item["period"]] = item

        missing = [period for period in required_periods if not all(period in existing[code] for code in code_map)]
        errors: list[str] = []
        if missing:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self._fetch_mops_period, period): period for period in missing}
                for future in as_completed(futures):
                    period = futures[future]
                    try:
                        _, rows = future.result()
                        for code, item in rows.items():
                            existing[code][period] = item
                    except Exception as exc:
                        errors.append(f"{period}: {exc}")

        for code, company_id in code_map.items():
            company = self._company(data, company_id)
            company["monthlyHistory"] = [existing[code][period] for period in required_periods if period in existing[code]]

        complete = min(len(existing[code]) for code in code_map)
        message = f"3개사 월매출·{complete}개월 이력 갱신 완료"
        if errors:
            message += f" (일부 {len(errors)}개월 재시도 예정)"
        self._source_status(data, "twse", "live", message)

    @staticmethod
    def _mops_row_value(source: str, labels: list[str], year: int, quarter: int) -> float | None:
        starts = {1: f"{year}0101", 2: f"{year}0401", 3: f"{year}0701", 4: f"{year}0101"}
        ends = {1: f"{year}0331", 2: f"{year}0630", 3: f"{year}0930", 4: f"{year}1231"}
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", source, flags=re.I | re.S):
            plain = html.unescape(re.sub(r"<[^>]+>", "", row)).replace("\u3000", "").strip()
            if not any(label in plain for label in labels):
                continue
            for match in re.finditer(r"<ix:nonFraction\s+([^>]*)>(.*?)</ix:nonFraction>", row, flags=re.I | re.S):
                attrs = dict(re.findall(r"([\w:.-]+)=[\"']([^\"']*)[\"']", match.group(1)))
                context = attrs.get("contextRef", "")
                if starts[quarter] not in context or ends[quarter] not in context:
                    continue
                raw = re.sub(r"<[^>]+>", "", match.group(2)).replace(",", "").strip()
                value = clean_number(raw)
                if value is None:
                    continue
                if attrs.get("sign") == "-":
                    value = -value
                return value / 1000  # published in TWD thousands -> TWD millions
        return None

    def _fetch_mops_quarter(self, code: str, year: int, quarter: int) -> tuple[str, dict]:
        url = MOPS_FINANCIAL_URL.format(code=code, year=year, quarter=quarter)
        payload = fetch_bytes(url, headers={"Referer": "https://mops.twse.com.tw/"}, timeout=35)
        source = payload.decode("big5", "replace")
        period = f"{year}Q{quarter}"
        item = {
            "period": period,
            "revenue": self._mops_row_value(source, ["營業收入合計", "營業收入"], year, quarter),
            "operatingIncome": self._mops_row_value(source, ["營業利益（損失）", "營業利益(損失)", "營業利益"], year, quarter),
            "netIncome": self._mops_row_value(source, ["本期淨利（淨損）", "本期淨利(淨損)"], year, quarter),
            "currency": "TWD",
            "basis": "연결 단일분기",
            "source": "MOPS",
        }
        return period, with_margins(item)

    def _refresh_twse_quarterly(self, data: dict) -> None:
        latest_rows = fetch_json(TWSE_INCOME_URL)
        targets = {"2337": "macronix", "2344": "winbond", "2408": "nanya"}
        latest_period = ""
        for row in latest_rows if isinstance(latest_rows, list) else []:
            if row.get("公司代號") in targets:
                period = f"{int(row.get('年度', 0)) + 1911}Q{row.get('季別')}"
                latest_period = max(latest_period, period)
        if not latest_period:
            latest_period = "2026Q1"
        required = quarter_range(latest_period, 12)
        first_year = int(required[0][:4])
        last_year = int(required[-1][:4])

        for code, company_id in targets.items():
            company = self._company(data, company_id)
            existing = {item["period"]: item for item in company.get("quarterlyHistory", []) if item.get("period") in required}
            if len(existing) < len(required):
                fetched: dict[str, dict] = {}
                jobs = []
                for year in range(first_year, last_year + 1):
                    for quarter in range(1, 5):
                        if f"{year}Q{quarter}" <= latest_period:
                            jobs.append((year, quarter))
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {executor.submit(self._fetch_mops_quarter, code, year, quarter): (year, quarter) for year, quarter in jobs}
                    for future in as_completed(futures):
                        try:
                            period, item = future.result()
                            if item.get("revenue") is not None:
                                fetched[period] = item
                        except Exception:
                            continue
                for year in range(first_year, last_year + 1):
                    annual = fetched.get(f"{year}Q4")
                    if not annual:
                        continue
                    previous = [fetched.get(f"{year}Q{quarter}") for quarter in (1, 2, 3)]
                    if all(previous):
                        for key in ("revenue", "operatingIncome", "netIncome"):
                            if annual.get(key) is not None and all(item.get(key) is not None for item in previous):
                                annual[key] = annual[key] - sum(item[key] for item in previous)
                        annual["basis"] = "연결 단일분기(연간-1~3Q)"
                        with_margins(annual)
                existing.update({period: item for period, item in fetched.items() if period in required})
            company["quarterlyHistory"] = [existing[period] for period in required if period in existing]

    def _refresh_sse(self, data: dict) -> None:
        params = {
            "isPagination": "true",
            "productId": "688110",
            "keyWord": "",
            "securityType": "0101,120100,020100,020200,120200",
            "pageHelp.pageSize": "12",
            "pageHelp.pageNo": "1",
            "pageHelp.beginPage": "1",
            "pageHelp.cacheSize": "1",
        }
        url = SSE_QUERY_URL + "?" + urllib.parse.urlencode(params)
        result = fetch_json(url, headers={"Referer": "https://www.sse.com.cn/"})
        rows = result.get("pageHelp", {}).get("data", [])
        if not rows:
            raise RuntimeError("최근 공시를 찾지 못함")
        company = self._company(data, "dosilicon")
        company.update({"updatedAt": now_iso(), "verification": "official-monitor"})
        existing = [item for item in data["feed"] if item.get("companyId") != "dosilicon"]
        sse_feed = []
        for row in rows[:6]:
            pdf_path = row.get("URL", "")
            sse_feed.append({
                "id": f"sse-{row.get('SSEDATE')}-{abs(hash(pdf_path))}",
                "companyId": "dosilicon",
                "company": "Dosilicon",
                "date": row.get("SSEDATE"),
                "title": row.get("TITLE", "상하이거래소 공시"),
                "type": "공시",
                "url": "https://www.sse.com.cn" + pdf_path if pdf_path.startswith("/") else pdf_path,
                "source": "SSE",
                "isNew": True,
            })
        data["feed"] = sorted(existing + sse_feed, key=disclosure_sort_key, reverse=True)[:18]
        self._source_status(data, "sse", "live", f"Dosilicon 최근 공시 {len(sse_feed)}건 확인")

    @staticmethod
    def _apply_dosilicon_preliminary(standalone: dict[str, dict]) -> None:
        forecast = DOSILICON_H1_2026_PRELIMINARY
        if "2026Q2" in standalone and not standalone["2026Q2"].get("isPreliminary"):
            return

        q1 = standalone.get("2026Q1")
        if not q1 or q1.get("revenue") in (None, 0):
            return

        h1_net_low, h1_net_high = forecast["h1NetIncomeRange"]
        q2_growth_low, q2_growth_high = forecast["q2NetIncomeQoQRange"]
        q1_net_values = [
            h1_net_low / (2 + q2_growth_low / 100),
            h1_net_high / (2 + q2_growth_high / 100),
        ]
        q1_net = sum(q1_net_values) / len(q1_net_values)
        q1["netIncome"] = q1_net
        q1["netIncomeBasis"] = "SSE 2026H1 예비실적 역산 귀속순이익"
        with_margins(q1)

        h1_revenue_low, h1_revenue_high = forecast["h1RevenueRange"]
        revenue_range = [h1_revenue_low - q1["revenue"], h1_revenue_high - q1["revenue"]]
        net_income_range = [h1_net_low - q1_net, h1_net_high - q1_net]
        q2 = {
            "period": "2026Q2",
            "revenue": sum(revenue_range) / len(revenue_range),
            "operatingIncome": None,
            "netIncome": sum(net_income_range) / len(net_income_range),
            "currency": "CNY",
            "basis": "2026H1 예비실적 중간값(누적-1Q)",
            "source": forecast["source"],
            "sourceUrl": forecast["sourceUrl"],
            "isPreliminary": True,
            "announcementDate": forecast["announcementDate"],
            "revenueRange": revenue_range,
            "netIncomeRange": net_income_range,
            "h1RevenueRange": forecast["h1RevenueRange"],
            "h1NetIncomeRange": forecast["h1NetIncomeRange"],
        }
        standalone["2026Q2"] = with_margins(q2)

    def _refresh_dosilicon_quarterly(self, data: dict) -> None:
        params = {
            "reportName": "RPT_F10_FINANCE_GINCOME",
            "columns": "ALL",
            "filter": '(SECUCODE="688110.SH")',
            "pageNumber": "1",
            "pageSize": "24",
            "sortTypes": "-1",
            "sortColumns": "REPORT_DATE",
        }
        result = fetch_json(EASTMONEY_INCOME_URL + "?" + urllib.parse.urlencode(params), headers={"Referer": "https://data.eastmoney.com/"})
        rows = result.get("result", {}).get("data", []) if isinstance(result, dict) else []
        cumulative: dict[str, dict] = {}
        for row in rows:
            report_date = str(row.get("REPORT_DATE", ""))[:10]
            if not report_date:
                continue
            year, month = int(report_date[:4]), int(report_date[5:7])
            quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(month)
            if not quarter:
                continue
            cumulative[f"{year}Q{quarter}"] = {
                "period": f"{year}Q{quarter}",
                "revenue": clean_number(row.get("TOTAL_OPERATE_INCOME")) / 1_000_000 if row.get("TOTAL_OPERATE_INCOME") is not None else None,
                "operatingIncome": clean_number(row.get("OPERATE_PROFIT")) / 1_000_000 if row.get("OPERATE_PROFIT") is not None else None,
                "netIncome": clean_number(row.get("NETPROFIT")) / 1_000_000 if row.get("NETPROFIT") is not None else None,
                "currency": "CNY",
                "basis": "연결 누적",
                "source": "Eastmoney/SSE filing",
            }
        standalone: dict[str, dict] = {}
        for period in sorted(cumulative):
            item = copy.deepcopy(cumulative[period])
            year, quarter = int(period[:4]), int(period[-1])
            if quarter > 1:
                prior = cumulative.get(f"{year}Q{quarter - 1}")
                if prior:
                    for key in ("revenue", "operatingIncome", "netIncome"):
                        if item.get(key) is not None and prior.get(key) is not None:
                            item[key] -= prior[key]
                    item["basis"] = "연결 단일분기(누적 차감)"
            else:
                item["basis"] = "연결 단일분기"
            standalone[period] = with_margins(item)
        self._apply_dosilicon_preliminary(standalone)
        periods = sorted(standalone)[-12:]
        self._company(data, "dosilicon")["quarterlyHistory"] = [standalone[period] for period in periods]

    @staticmethod
    def _dramexchange_date(text: str) -> tuple[str, str]:
        match = re.search(
            r"DRAM\s+Spot\s+Price\s+Last\s+Update:\s*([A-Za-z]{3})\.?\s*(\d{1,2})\s+(\d{4})\s+(\d{1,2}:\d{2})\s*\(GMT\+8\)",
            text,
            flags=re.I,
        )
        if not match:
            today = datetime.now(KST).strftime("%Y-%m-%d")
            return today, f"{today} (KST)"
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = months.get(match.group(1).lower()[:3], datetime.now(KST).month)
        day = int(match.group(2))
        year = int(match.group(3))
        time_label = match.group(4)
        return f"{year:04d}-{month:02d}-{day:02d}", f"{year:04d}-{month:02d}-{day:02d} {time_label} GMT+8"

    @staticmethod
    def _dramexchange_product(text: str, label: str) -> dict:
        pattern = (
            re.escape(label)
            + r"\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([+-]?\d+(?:\.\d+)?)\s*%"
        )
        match = re.search(pattern, text, flags=re.I)
        if not match:
            raise RuntimeError(f"{label} 가격 행을 찾지 못함")
        daily_high, daily_low, session_high, session_low, average, change = (clean_number(value) for value in match.groups())
        return {
            "dailyHigh": daily_high,
            "dailyLow": daily_low,
            "sessionHigh": session_high,
            "sessionLow": session_low,
            "average": average,
            "change": change,
        }

    @staticmethod
    def _append_spot_history(product: dict, item: dict) -> None:
        history = {entry.get("date"): entry for entry in product.get("history", []) if entry.get("date")}
        existing = history.get(item["date"])
        if existing and existing.get("source") == "StockEasy":
            item = existing
        history[item["date"]] = item
        product["history"] = sorted(history.values(), key=lambda entry: entry.get("date", ""))[-730:]
        product["latest"] = product["history"][-1]

    def _refresh_dramexchange_spot(self, data: dict) -> None:
        payload = fetch_bytes(DRAMEXCHANGE_URL, timeout=25, attempts=2)
        text = plain_text_from_html(payload.decode("utf-8", "replace"))
        date, source_time = self._dramexchange_date(text)
        targets = [
            ("ddr5_16gb_4800_5600", "DDR5", "DDR5 16Gb (2Gx8) 4800/5600", "#2e7a8f"),
            ("ddr4_8gb_3200", "DDR4", "DDR4 8Gb (1Gx8) 3200", "#9a6f2e"),
        ]
        spot = data.setdefault("spotPrices", {
            "updatedAt": None,
            "sourceLabel": "DRAMeXchange 공개 현물가",
            "sourceUrl": DRAMEXCHANGE_URL,
            "note": "공개 홈의 Session Average를 매일 저장해 자체 추이를 만듭니다.",
            "products": [],
        })
        products = self._spot_products(data)
        for product_id, name, label, color in targets:
            product = products.get(product_id)
            if not product:
                product = {"id": product_id, "name": name, "label": label, "unit": "USD", "color": color, "history": []}
                spot["products"].append(product)
                products[product_id] = product
            parsed = self._dramexchange_product(text, label)
            item = {
                "date": date,
                "sourceTime": source_time,
                "average": parsed["average"],
                "change": parsed["change"],
                "dailyHigh": parsed["dailyHigh"],
                "dailyLow": parsed["dailyLow"],
                "sessionHigh": parsed["sessionHigh"],
                "sessionLow": parsed["sessionLow"],
                "source": "DRAMeXchange",
            }
            product.update({"name": name, "label": label, "unit": "USD", "color": color})
            self._append_spot_history(product, item)
        spot.update({
            "updatedAt": now_iso(),
            "sourceLabel": "StockEasy / DRAMeXchange",
            "sourceUrl": STOCKEASY_MEMORY_URL,
            "note": "과거 90일은 StockEasy 메모리 화면 툴팁에서 수집했고, 이후 같은 DDR4 8Gb·DDR5 16Gb 품목의 공개 DRAMeXchange Session Average를 자동 누적합니다.",
        })
        self._write_spot_history_file(data)
        self._source_status(data, "dramexchange", "live", f"DDR4/DDR5 현물가 {date} 갱신 완료")

    @staticmethod
    def _latest_ir_link(page_url: str, predicate) -> tuple[str, str]:
        payload = fetch_bytes(page_url, timeout=12, attempts=1)
        source = payload.decode("utf-8", "replace")
        parser = LinkParser()
        parser.feed(source)
        for link in parser.links:
            label = normalize_spaces(link.get("text", ""))
            href = link.get("href", "")
            if predicate(label, href):
                return urllib.parse.urljoin(page_url, href), label
        raise RuntimeError("최신 IR 링크를 찾지 못했습니다")

    @staticmethod
    def _quarter_short_label(value: str) -> str:
        text = normalize_spaces(value)
        patterns = [
            r"([1-4])Q\s*(20\d{2}|\d{2})",
            r"Q([1-4])\s*(20\d{2}|\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                quarter, year = match.group(1), match.group(2)
                return f"{quarter}Q{year[-2:]}"
        quarter_words = {"First": "1", "Second": "2", "Third": "3", "Fourth": "4"}
        match = re.search(r"(First|Second|Third|Fourth)\s+Quarter\s+(20\d{2})", text, flags=re.I)
        if match:
            return f"{quarter_words[match.group(1).title()]}Q{match.group(2)[-2:]}"
        return "최근"

    @staticmethod
    def _section_after(text: str, start_pattern: str, end_patterns: list[str]) -> str:
        match = re.search(start_pattern, text, flags=re.I)
        if not match:
            return ""
        start = match.end()
        end = len(text)
        for pattern in end_patterns:
            end_match = re.search(pattern, text[start:], flags=re.I)
            if end_match:
                end = min(end, start + end_match.start())
        return text[start:end]

    @staticmethod
    def _sum_mw(section: str, *, fallback: int | None = None, max_items: int | None = None) -> int | None:
        numbers = [clean_number(match) for match in re.findall(r"\b(\d+(?:\.\d+)?)\s*MW\b", section, flags=re.I)]
        values = [value for value in numbers if value is not None]
        if max_items:
            values = values[:max_items]
        if values:
            return int(round(sum(values)))
        return fallback

    @staticmethod
    def _sum_gds_power_table(section: str, *, fallback: int | None = None, max_items: int | None = None) -> int | None:
        values = []
        for match in re.finditer(
            r"(?:Hebei|Jiangsu|Guangdong|Inner Mongolia)\s+(?:[\d,]+\s+)?(\d{1,4})\s+(?:Inventory|New Build|Expansion)",
            section,
            flags=re.I,
        ):
            value = clean_number(match.group(1))
            if value is not None:
                values.append(value)
        if max_items:
            values = values[:max_items]
        if values:
            return int(round(sum(values)))
        return DashboardService._sum_mw(section, fallback=fallback, max_items=max_items)

    @staticmethod
    def _text_from_ir_payload(payload: bytes) -> str:
        if payload[:5] == b"%PDF-" or payload.lstrip().startswith(b"%PDF-"):
            return normalize_spaces(extract_pdf_text(payload))
        return normalize_spaces(plain_text_from_html(payload.decode("utf-8", "replace")))

    @staticmethod
    def _china_order_company(data: dict, company_id: str) -> dict:
        orders = data.setdefault("chinaServerOrders", {
            "updatedAt": None,
            "note": "공식 IR 원문에서 확인되는 중국 IDC 신규수주와 백로그만 표시합니다.",
            "companies": [],
        })
        for company in orders.setdefault("companies", []):
            if company.get("id") == company_id:
                return company
        company = {"id": company_id, "name": company_id.upper(), "series": [], "backlog": []}
        orders["companies"].append(company)
        return company

    def _refresh_gds_orders(self, data: dict) -> None:
        company = self._china_order_company(data, "gds")
        try:
            presentation_url, presentation_label = self._latest_ir_link(
                GDS_IR_URL,
                lambda text, href: "earnings presentation" in text.lower() and "gds" in (text + href).lower(),
            )
        except Exception:
            presentation_url, presentation_label = GDS_FALLBACK_PRESENTATION_URL, "GDS 1Q26 Earnings Presentation"
        presentation_text = normalize_spaces(extract_pdf_text(fetch_bytes(presentation_url, timeout=25, attempts=1)))
        annual_values = None
        annual_match = re.search(
            r"Gross Additional Power Committed By Year.*?FY22\s+FY23\s+FY24\s+FY25\s+YTD26\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
            presentation_text,
            flags=re.I,
        )
        if annual_match:
            annual_values = [int(value) for value in annual_match.groups()]

        existing_series = {item.get("period"): item for item in company.get("series", [])}
        annual_periods = ["FY22", "FY23", "FY24", "FY25", "YTD26"]
        if annual_values:
            for period, value in zip(annual_periods, annual_values):
                existing_series[period] = {
                    "period": period,
                    "value": value,
                    "unit": "MW",
                    "category": "연간 확약전력",
                    "basis": "Gross Additional Power Committed By Year",
                }

        q1_section = self._section_after(
            presentation_text,
            r"Bookings\s+1Q26",
            [r"Bookings\s+Current\s+Quarter", r"Hyperscale\s+Orders\s+2Q26", r"Backlog\s+Build-Up"],
        )
        q2_section = self._section_after(
            presentation_text,
            r"Hyperscale\s+Orders\s+2Q26\s+To\s+Date",
            [r"Backlog\s+Build-Up", r"Resource\s+Supply", r"Financial\s+Performance"],
        )
        q1_value = self._sum_gds_power_table(q1_section, fallback=existing_series.get("1Q26", {}).get("value"), max_items=4)
        q2_value = self._sum_gds_power_table(q2_section, fallback=138, max_items=2)
        if q1_value:
            existing_series["1Q26"] = {
                "period": "1Q26",
                "value": q1_value,
                "unit": "MW",
                "category": "분기 신규수주",
                "basis": "Hyperscale orders in 1Q26",
            }
        if q2_value:
            existing_series["2Q26TD"] = {
                "period": "2Q26TD",
                "value": q2_value,
                "unit": "MW",
                "category": "분기 신규수주",
                "basis": "Hyperscale orders to date",
            }

        total_backlog = first_int([
            r"Total\s+Backlog(?:\s+of)?\s+([\d,]+)(?:\s*sqm)?",
            r"Total Backlog of\s+([\d,]+)\s*sqm",
            r"Total Backlog\s+([\d,]+)\s*sqm",
        ], presentation_text)
        effective_backlog = first_int([r"([\d,]+)\s+Effective Backlog"], presentation_text)
        total_area_committed = first_int([r"Total Area Committed of\s+([\d,]+)\s*sqm"], presentation_text)
        if effective_backlog is None and total_backlog is not None and total_area_committed is not None:
            effective_backlog = int(round(total_backlog - total_area_committed * 0.05))
        backlog = []
        if total_backlog:
            backlog.append({"label": "Total backlog", "value": total_backlog, "unit": "sqm", "basis": "GDS IR"})
        if effective_backlog:
            backlog.append({"label": "Effective backlog", "value": effective_backlog, "unit": "sqm", "basis": "GDS IR"})
        delivery_section = self._section_after(presentation_text, r"Effective Backlog", [r"Financial\s+&\s+Operating\s+Review", r"1Q26\s+P&L"])
        delivery_values = [int(value) for value in re.findall(r"~?(\d+)%", delivery_section)[:3]]
        for label, value in zip(("2Q-4Q26 delivery", "FY27 delivery", "Thereafter"), delivery_values):
            backlog.append({"label": label, "value": value, "unit": "%", "basis": "Backlog delivery split"})
        if not backlog:
            backlog = company.get("backlog", [])

        ordered_periods = ["FY22", "FY23", "FY24", "FY25", "YTD26", "1Q26", "2Q26TD"]
        series = [existing_series[period] for period in ordered_periods if period in existing_series]
        latest_item = existing_series.get("2Q26TD") or existing_series.get("1Q26") or (series[-1] if series else None)
        company.update({
            "name": "GDS",
            "sourceLabel": f"GDS 공식 IR · {presentation_label}",
            "sourceUrl": presentation_url,
            "updatedAt": now_iso(),
            "latest": {
                "label": f"{latest_item['period']} 신규수주" if latest_item else "최근 신규수주",
                "value": latest_item.get("value") if latest_item else None,
                "unit": latest_item.get("unit", "MW") if latest_item else "MW",
                "basis": latest_item.get("basis", "GDS IR") if latest_item else "GDS IR",
            },
            "series": series,
            "backlog": backlog,
            "note": "중국 IDC 신규수주는 MW, 백로그는 sqm 기준으로 구분 표시합니다.",
        })
        data["chinaServerOrders"]["updatedAt"] = now_iso()
        self._source_status(data, "gds_ir", "live", "GDS 신규수주·백로그 갱신 완료")

    def _refresh_vnet_orders(self, data: dict) -> None:
        company = self._china_order_company(data, "vnet")
        try:
            release_url, release_label = self._latest_ir_link(
                VNET_IR_URL,
                lambda text, href: text.strip().lower() == "press release" or "financial results" in text.lower(),
            )
        except Exception:
            release_url, release_label = VNET_FALLBACK_RELEASE_URL, "VNET Reports Unaudited First Quarter 2026 Financial Results"
        try:
            presentation_url, presentation_label = self._latest_ir_link(
                VNET_IR_URL,
                lambda text, href: "earnings presentation" in text.lower() and "english" in text.lower(),
            )
        except Exception:
            presentation_url, presentation_label = VNET_FALLBACK_PRESENTATION_URL, "VNET 1Q26 Earnings Presentation"

        release_text = ""
        presentation_text = ""
        try:
            release_text = self._text_from_ir_payload(fetch_bytes(release_url, timeout=25, attempts=1))
        except Exception:
            if release_url != VNET_FALLBACK_RELEASE_URL:
                release_text = self._text_from_ir_payload(fetch_bytes(VNET_FALLBACK_RELEASE_URL, timeout=25, attempts=1))
                release_url, release_label = VNET_FALLBACK_RELEASE_URL, "VNET Reports Unaudited First Quarter 2026 Financial Results"
            else:
                raise
        try:
            presentation_text = self._text_from_ir_payload(fetch_bytes(presentation_url, timeout=25, attempts=1))
        except Exception:
            presentation_text = ""
        combined_text = normalize_spaces(f"{release_text} {presentation_text}")

        latest_period = self._quarter_short_label(combined_text) or self._quarter_short_label(release_label)
        ytd_orders = first_int([
            r"secured\s+\d+\s+wholesale\s+orders\s+totaling\s+([\d,]+)\s*MW",
            r"total\s+of\s+([\d,]+)\s*MW\s+of\s+new\s+orders",
            r"securing\s+a\s+total\s+of\s+([\d,]+)\s*MW",
            r"totaling\s+([\d,]+)\s*MW\s+year-to-date",
            r"secured.*?total(?:ing)?\s+(?:of\s+)?([\d,]+)\s*MW",
            r"new\s+orders\s+year-to-date\s+20\d{2}.*?([\d,]+)\s*MW",
        ], combined_text)
        committed = first_int([
            r"Wholesale Capacity Committed\s*\(?([\d,]+)\s*MW\)?",
            r"Committed Wholesale Capacity\s*\(?([\d,]+)\s*MW\)?",
            r"total capacity committed(?:\[\d+\])?\s+(?:was\s+)?([\d,]+)\s*MW",
            r"Total capacity committed\s+([\d,]+)\s*MW",
        ], combined_text)
        utilized = first_int([
            r"capacity utilized by customers(?:\s+reached|\s+was)?\s+([\d,]+)\s*MW",
            r"capacity utilized by customers reached\s+([\d,]+)\s*MW",
            r"capacity utilized\s+(?:was\s+)?([\d,]+)\s*MW",
            r"Capacity utilized\s+([\d,]+)\s*MW",
        ], combined_text)
        construction = first_int([
            r"Wholesale Capacity under Construction\s*\(?([\d,]+)\s*MW\)?",
            r"capacity under construction(?:\[\d+\])?\s+(?:was\s+)?([\d,]+)\s*MW",
            r"under construction\s+([\d,]+)\s*MW",
        ], combined_text)
        held = first_int([
            r"Wholesale Capacity Held for Future Development\s*\(?([\d,]+)\s*MW\)?",
            r"held for future development\s+(?:was\s+)?([\d,]+)\s*MW",
            r"Held for future development\s+([\d,]+)\s*MW",
        ], combined_text)
        unutilized_direct = first_int([
            r"Unutilized(?:\s+Wholesale)?\s+Capacity\s*\(?([\d,]+)\s*MW\)?",
            r"Unutilized\s+committed\s+capacity\s*\(?([\d,]+)\s*MW\)?",
        ], combined_text)

        existing_series = {
            item.get("period"): item
            for item in company.get("series", [])
            if item.get("period") not in {f"{latest_period} YTD", latest_period}
        }
        for period, item in existing_series.items():
            if period in {"3Q25", "4Q25TD"}:
                item["category"] = "분기 신규수주"
        if ytd_orders:
            existing_series[f"{latest_period} YTD"] = {
                "period": f"{latest_period} YTD",
                "value": ytd_orders,
                "unit": "MW",
                "category": "YTD 신규수주",
                "basis": "Wholesale IDC orders",
            }
        ordered_periods = ["3Q25", "4Q25TD", f"{latest_period} YTD", latest_period]
        series = [existing_series[period] for period in ordered_periods if period in existing_series]
        series.extend(
            item
            for period, item in sorted(existing_series.items(), key=lambda entry: str(entry[0]))
            if period not in ordered_periods
        )

        backlog = []
        if committed is not None:
            backlog.append({"label": "Committed capacity", "value": committed, "unit": "MW", "basis": "VNET operating metrics"})
        if utilized is not None:
            backlog.append({"label": "Utilized capacity", "value": utilized, "unit": "MW", "basis": "VNET operating metrics"})
        if unutilized_direct is not None:
            backlog.append({"label": "Unutilized committed", "value": unutilized_direct, "unit": "MW", "basis": "VNET operating metrics"})
        elif committed is not None and utilized is not None:
            backlog.append({"label": "Unutilized committed", "value": committed - utilized, "unit": "MW", "basis": "Committed - utilized", "derived": True})
        if construction is not None:
            backlog.append({"label": "Under construction", "value": construction, "unit": "MW", "basis": "VNET operating metrics"})
        if held is not None:
            backlog.append({"label": "Held for future development", "value": held, "unit": "MW", "basis": "VNET operating metrics"})
        if not backlog:
            backlog = company.get("backlog", [])

        latest_item = existing_series.get(f"{latest_period} YTD") or (series[-1] if series else None)
        company.update({
            "name": "VNET",
            "sourceLabel": f"VNET 공식 IR · {release_label}",
            "sourceUrl": release_url,
            "updatedAt": now_iso(),
            "latest": {
                "label": f"{latest_item['period']} 신규수주" if latest_item else "최근 신규수주",
                "value": latest_item.get("value") if latest_item else None,
                "unit": latest_item.get("unit", "MW") if latest_item else "MW",
                "basis": latest_item.get("basis", "VNET IR") if latest_item else "VNET IR",
            },
            "series": series,
            "backlog": backlog,
            "note": "Wholesale IDC 신규수주와 확약·활용 용량을 구분 표시합니다.",
        })
        data["chinaServerOrders"]["updatedAt"] = now_iso()
        self._source_status(data, "vnet_ir", "live", "VNET 신규수주·확약용량 갱신 완료")

    def _dart_request(self, endpoint: str, params: dict) -> dict:
        url = f"{DART_BASE}/{endpoint}?" + urllib.parse.urlencode(params)
        result = fetch_json(url)
        if result.get("status") not in (None, "000"):
            raise RuntimeError(result.get("message", "OpenDART 오류"))
        return result

    def _dart_corp_map(self, api_key: str) -> dict[str, str]:
        url = f"{DART_BASE}/corpCode.xml?" + urllib.parse.urlencode({"crtfc_key": api_key})
        payload = fetch_bytes(url)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            xml_data = archive.read("CORPCODE.xml")
        root = ElementTree.fromstring(xml_data)
        result: dict[str, str] = {}
        for item in root.findall("list"):
            stock_code = (item.findtext("stock_code") or "").strip()
            corp_code = (item.findtext("corp_code") or "").strip()
            if stock_code:
                result[stock_code] = corp_code
        return result

    @staticmethod
    def _dart_metric(rows: list[dict], patterns: list[str]) -> tuple[float | None, str | None]:
        for pattern in patterns:
            for row in rows:
                account = row.get("account_nm", "")
                section = row.get("sj_nm", "")
                if re.search(pattern, account) and section in ("손익계산서", "포괄손익계산서"):
                    value = clean_number(row.get("thstrm_amount"))
                    if value is not None:
                        return value, account
        return None, None

    def _dart_financials(self, api_key: str, corp_code: str) -> tuple[dict, list[dict]]:
        current_year = datetime.now(KST).year
        candidates = [
            (current_year, "11014", "3Q 누적"),
            (current_year, "11012", "반기 누적"),
            (current_year, "11013", "1Q"),
            (current_year - 1, "11011", "연간"),
            (current_year - 1, "11014", "3Q 누적"),
            (current_year - 1, "11012", "반기 누적"),
            (current_year - 1, "11013", "1Q"),
        ]
        last_error = "재무제표 없음"
        for year, report_code, period_name in candidates:
            for fs_div, basis_name in (("CFS", "연결"), ("OFS", "별도")):
                params = {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": report_code,
                    "fs_div": fs_div,
                }
                try:
                    result = self._dart_request("fnlttSinglAcntAll.json", params)
                    rows = result.get("list", [])
                    if not rows:
                        continue
                    revenue, _ = self._dart_metric(rows, [r"^매출액$", r"^수익\(매출액\)$", r"^영업수익$"])
                    op_income, _ = self._dart_metric(rows, [r"^영업이익", r"영업손익"])
                    net_income, _ = self._dart_metric(rows, [r"지배기업.*순이익", r"당기순이익", r"분기순이익"])
                    return ({
                        "period": f"{year} {period_name}",
                        "periodType": "정기보고서",
                        "revenue": revenue,
                        "revenueDisplay": format_krw_eok(revenue),
                        "revenueYoY": None,
                        "revenueQoQ": None,
                        "operatingIncome": op_income,
                        "operatingIncomeDisplay": format_krw_eok(op_income),
                        "netIncome": net_income,
                        "netIncomeDisplay": format_krw_eok(net_income),
                        "currency": "KRW",
                        "basis": f"{basis_name}, 누적 기준일 수 있음",
                    }, rows)
                except Exception as exc:
                    last_error = str(exc)
        raise RuntimeError(last_error)

    def _dart_quarter_report(self, api_key: str, corp_code: str, year: int, quarter: int) -> dict | None:
        report_code = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}[quarter]
        for fs_div, basis_name in (("CFS", "연결"), ("OFS", "별도")):
            try:
                result = self._dart_request("fnlttSinglAcntAll.json", {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": report_code,
                    "fs_div": fs_div,
                })
            except Exception:
                continue
            rows = result.get("list", [])
            if not rows:
                continue
            revenue, _ = self._dart_metric(rows, [r"^매출액$", r"^수익\(매출액\)$", r"^영업수익$"])
            op_income, _ = self._dart_metric(rows, [r"^영업이익", r"영업손익"])
            net_income, _ = self._dart_metric(rows, [r"지배기업.*순이익", r"당기순이익", r"분기순이익"])
            return with_margins({
                "period": f"{year}Q{quarter}",
                "revenue": revenue / 1_000_000 if revenue is not None else None,
                "operatingIncome": op_income / 1_000_000 if op_income is not None else None,
                "netIncome": net_income / 1_000_000 if net_income is not None else None,
                "currency": "KRW",
                "basis": f"{basis_name} {'연간 누적' if quarter == 4 else '단일분기'}",
                "source": "OpenDART",
            })
        return None

    def _refresh_dart_quarterly(self, data: dict, api_key: str) -> None:
        corp_map = self._dart_corp_map(api_key)
        targets = [("fidelix", "032580"), ("jeju", "080220")]
        current_year = datetime.now(KST).year
        for company_id, stock_code in targets:
            corp_code = corp_map.get(stock_code)
            if not corp_code:
                continue
            fetched: dict[str, dict] = {}
            for year in range(current_year - 3, current_year + 1):
                for quarter in range(1, 5):
                    item = self._dart_quarter_report(api_key, corp_code, year, quarter)
                    if item and item.get("revenue") is not None:
                        fetched[item["period"]] = item
            for year in range(current_year - 3, current_year + 1):
                annual = fetched.get(f"{year}Q4")
                previous = [fetched.get(f"{year}Q{quarter}") for quarter in (1, 2, 3)]
                if annual and all(previous):
                    for key in ("revenue", "operatingIncome", "netIncome"):
                        if annual.get(key) is not None and all(item.get(key) is not None for item in previous):
                            annual[key] = annual[key] - sum(item[key] for item in previous)
                    annual["basis"] = annual["basis"].replace("연간 누적", "단일분기(연간-1~3Q)")
                    with_margins(annual)
            periods = sorted(fetched)[-12:]
            self._company(data, company_id)["quarterlyHistory"] = [fetched[period] for period in periods]

    def _refresh_dart(self, data: dict, api_key: str) -> None:
        corp_map = self._dart_corp_map(api_key)
        targets = [("fidelix", "032580"), ("jeju", "080220")]
        feed = [item for item in data["feed"] if item.get("source") != "OpenDART"]
        for company_id, stock_code in targets:
            corp_code = corp_map.get(stock_code)
            if not corp_code:
                raise RuntimeError(f"{stock_code} DART 고유번호 없음")
            company = self._company(data, company_id)
            financials, _ = self._dart_financials(api_key, corp_code)
            company["metrics"] = financials
            company.update({
                "updatedAt": now_iso(),
                "verification": "official",
                "sourceLabel": "OpenDART 연결재무제표",
                "sourceUrl": "https://opendart.fss.or.kr/",
                "note": "OpenDART 원문 기준 자동 갱신",
            })
            start_date = (datetime.now(KST) - timedelta(days=240)).strftime("%Y%m%d")
            filings = self._dart_request("list.json", {
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": start_date,
                "page_count": "12",
                "sort": "date",
                "sort_mth": "desc",
            }).get("list", [])
            for item in filings[:5]:
                feed.append({
                    "id": f"dart-{item.get('rcept_no')}",
                    "companyId": company_id,
                    "company": company["name"],
                    "date": item.get("rcept_dt"),
                    "title": item.get("report_nm"),
                    "type": "공시",
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
                    "source": "OpenDART",
                    "isNew": True,
                })
        data["feed"] = sorted(feed, key=disclosure_sort_key, reverse=True)[:18]
        self._source_status(data, "dart", "live", "국내 2개사 재무·공시 갱신 완료")


load_local_env()
SERVICE = DashboardService()


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/dashboard":
            self._json(SERVICE.snapshot())
            return
        if path == "/api/health":
            self._json({"ok": True, "time": now_iso()})
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/refresh":
            self._json({"ok": False, "message": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        if SERVICE.refreshing:
            self._json({"ok": True, "message": "이미 갱신 중입니다."}, HTTPStatus.ACCEPTED)
            return

        def refresh_job() -> None:
            SERVICE.refresh("manual")

        threading.Thread(target=refresh_job, daemon=True).start()
        self._json({"ok": True, "message": "갱신을 시작했습니다."}, HTTPStatus.ACCEPTED)


def seconds_until_refresh(refresh_at: str) -> float:
    try:
        hour, minute = (int(part) for part in refresh_at.split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError as exc:
        raise ValueError("REFRESH_AT은 HH:MM 형식이어야 합니다.") from exc
    current = datetime.now(KST)
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return (target - current).total_seconds()


def scheduler(refresh_at: str) -> None:
    time.sleep(3)
    if os.getenv("REFRESH_ON_STARTUP", "0").strip().lower() in {"1", "true", "yes", "y"}:
        SERVICE.refresh("startup")
    while True:
        time.sleep(seconds_until_refresh(refresh_at))
        SERVICE.refresh("scheduled")


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    refresh_at = os.getenv("REFRESH_AT", "08:00")
    threading.Thread(target=scheduler, args=(refresh_at,), daemon=True).start()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Fidelix dashboard: http://{host}:{port}")
    print(f"Daily refresh: {refresh_at} KST")
    print("Ctrl+C로 종료")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
