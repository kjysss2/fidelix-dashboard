(function () {
  const FIDELIX_REPORT_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000003";
  const FIDELIX_UPDATED_AT = "2026-08-12T09:13:17+09:00";
  const FIDELIX_CUMULATIVE = {
    period: "2026 반기 누적",
    periodType: "정기보고서",
    revenue: 54923791090,
    revenueDisplay: "549.2억원",
    revenueYoY: null,
    revenueQoQ: null,
    operatingIncome: 13944282996,
    operatingIncomeDisplay: "139.4억원",
    netIncome: 14783021861,
    netIncomeDisplay: "147.8억원",
    currency: "KRW",
    basis: "별도, 반기 누적",
  };
  const FIDELIX_QUARTER = {
    period: "2026Q2",
    revenue: 33434.395547,
    operatingIncome: 9612.33947,
    netIncome: 9528.789884,
    currency: "KRW",
    basis: "별도 단일분기",
    source: "DART",
    sourceUrl: FIDELIX_REPORT_URL,
    announcementDate: "2026-08-12",
    operatingMargin: 28.749852697314566,
    netMargin: 28.499961575812005,
  };
  const FIDELIX_FEED_ITEM = {
    id: "dart-20260812000003",
    companyId: "fidelix",
    company: "피델릭스",
    date: "20260812",
    title: "반기보고서 (2026.06)",
    type: "공시",
    url: FIDELIX_REPORT_URL,
    source: "DART",
    isNew: true,
  };

  const JEJU_REPORT_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260813001713";
  const JEJU_UPDATED_AT = "2026-08-14T12:56:27+09:00";
  const JEJU_CUMULATIVE = {
    period: "2026 반기 누적",
    periodType: "정기보고서",
    revenue: 289938012131,
    revenueDisplay: "2,899.4억원",
    revenueYoY: null,
    revenueQoQ: null,
    operatingIncome: 121871077131,
    operatingIncomeDisplay: "1,218.7억원",
    netIncome: 145019505408,
    netIncomeDisplay: "1,450.2억원",
    currency: "KRW",
    basis: "연결, 반기 누적",
  };
  const JEJU_QUARTER = {
    period: "2026Q2",
    revenue: 109466.043778,
    operatingIncome: 54757.630204,
    netIncome: 66953.257538,
    currency: "KRW",
    basis: "연결 단일분기",
    source: "DART",
    sourceUrl: JEJU_REPORT_URL,
    announcementDate: "2026-08-13",
    operatingMargin: 50.022480318234486,
    netMargin: 61.163494383503036,
  };
  const JEJU_FEED_ITEM = {
    id: "dart-20260813001713",
    companyId: "jeju",
    company: "제주반도체",
    date: "20260813",
    title: "반기보고서 (2026.06)",
    type: "공시",
    url: JEJU_REPORT_URL,
    source: "DART",
    isNew: true,
  };

  function shouldPatchH1(company) {
    const period = String(company?.metrics?.period || "");
    return period.includes("2026") && period.includes("반기");
  }

  function upsertQuarter(company, quarter) {
    const history = (company.quarterlyHistory || []).filter((item) => item.period !== quarter.period);
    history.push({ ...quarter });
    company.quarterlyHistory = history.sort((a, b) => String(a.period).localeCompare(String(b.period))).slice(-12);
  }

  function upsertFeed(data, item) {
    const feed = (data.feed || []).filter((entry) => entry.id !== item.id);
    data.feed = [item, ...feed].sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 18);
  }

  function applyFidelix2026H1(data) {
    const company = (data?.companies || []).find((item) => item.id === "fidelix");
    if (!company || !shouldPatchH1(company)) return data;

    company.metrics = { ...(company.metrics || {}), ...FIDELIX_CUMULATIVE };
    company.updatedAt = FIDELIX_UPDATED_AT;
    company.verification = "official";
    company.sourceLabel = "DART 반기보고서";
    company.sourceUrl = FIDELIX_REPORT_URL;
    company.note = "2026년 반기보고서 원문 기준 수동 갱신";
    upsertQuarter(company, FIDELIX_QUARTER);
    upsertFeed(data, FIDELIX_FEED_ITEM);
    return data;
  }

  function applyJeju2026H1(data) {
    const company = (data?.companies || []).find((item) => item.id === "jeju");
    if (!company || !shouldPatchH1(company)) return data;

    company.metrics = { ...(company.metrics || {}), ...JEJU_CUMULATIVE };
    company.updatedAt = JEJU_UPDATED_AT;
    company.verification = "official";
    company.sourceLabel = "DART 반기보고서";
    company.sourceUrl = JEJU_REPORT_URL;
    company.note = "2026년 반기보고서 원문 기준 수동 갱신";
    upsertQuarter(company, JEJU_QUARTER);
    upsertFeed(data, JEJU_FEED_ITEM);
    return data;
  }

  function applyManual2026H1(data) {
    applyFidelix2026H1(data);
    applyJeju2026H1(data);

    const dart = (data.sources || []).find((source) => source.id === "dart");
    if (dart) {
      dart.status = "live";
      dart.message = "피델릭스·제주반도체 2026년 반기보고서 반영 완료";
      dart.checkedAt = JEJU_UPDATED_AT;
      dart.url = "https://dart.fss.or.kr/";
    }

    if (data.system) {
      data.system.lastRefresh = JEJU_UPDATED_AT;
      data.system.lastRefreshReason = "manual-2026h1-fidelix-jeju";
      data.system.lastRefreshErrors = [];
      data.system.refreshing = false;
    }
    return data;
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async function patchedFetch(input, init) {
    const response = await originalFetch(input, init);
    const url = typeof input === "string" ? input : input?.url;
    const pathname = (() => {
      try {
        return new URL(url, window.location.href).pathname;
      } catch {
        return "";
      }
    })();
    if (!pathname.endsWith("/data/dashboard.json") && !pathname.endsWith("/api/dashboard")) {
      return response;
    }

    try {
      const payload = await response.clone().json();
      applyManual2026H1(payload);
      const headers = new Headers(response.headers);
      headers.set("content-type", "application/json; charset=utf-8");
      return new Response(JSON.stringify(payload), {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    } catch {
      return response;
    }
  };

  window.applyFidelix2026H1 = applyFidelix2026H1;
  window.applyJeju2026H1 = applyJeju2026H1;
  window.applyManual2026H1 = applyManual2026H1;
})();
