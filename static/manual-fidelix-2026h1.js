(function () {
  const REPORT_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000003";
  const UPDATED_AT = "2026-08-12T09:13:17+09:00";
  const CUMULATIVE = {
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
  const QUARTER = {
    period: "2026Q2",
    revenue: 33434.395547,
    operatingIncome: 9612.33947,
    netIncome: 9528.789884,
    currency: "KRW",
    basis: "별도 단일분기",
    source: "DART",
    sourceUrl: REPORT_URL,
    announcementDate: "2026-08-12",
    operatingMargin: 28.749852697314566,
    netMargin: 28.499961575812005,
  };
  const FEED_ITEM = {
    id: "dart-20260812000003",
    companyId: "fidelix",
    company: "피델릭스",
    date: "20260812",
    title: "반기보고서 (2026.06)",
    type: "공시",
    url: REPORT_URL,
    source: "DART",
    isNew: true,
  };

  function shouldPatch(company) {
    const period = String(company?.metrics?.period || "");
    return period.includes("2026") && period.includes("반기");
  }

  function applyFidelix2026H1(data) {
    const company = (data?.companies || []).find((item) => item.id === "fidelix");
    if (!company || !shouldPatch(company)) return data;

    company.metrics = { ...(company.metrics || {}), ...CUMULATIVE };
    company.updatedAt = UPDATED_AT;
    company.verification = "official";
    company.sourceLabel = "DART 반기보고서";
    company.sourceUrl = REPORT_URL;
    company.note = "2026년 반기보고서 원문 기준 수동 갱신";

    const history = (company.quarterlyHistory || []).filter((item) => item.period !== "2026Q2");
    history.push({ ...QUARTER });
    company.quarterlyHistory = history.sort((a, b) => String(a.period).localeCompare(String(b.period))).slice(-12);

    const feed = (data.feed || []).filter((item) => item.id !== FEED_ITEM.id);
    data.feed = [FEED_ITEM, ...feed].sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 18);

    const dart = (data.sources || []).find((source) => source.id === "dart");
    if (dart) {
      dart.status = "live";
      dart.message = "피델릭스 2026년 반기보고서 반영 완료";
      dart.checkedAt = UPDATED_AT;
      dart.url = "https://dart.fss.or.kr/";
    }

    if (data.system) {
      data.system.lastRefresh = UPDATED_AT;
      data.system.lastRefreshReason = "manual-fidelix-2026h1";
      data.system.lastRefreshErrors = [];
      data.system.refreshing = false;
    }
    return data;
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async function patchedFetch(input, init) {
    const response = await originalFetch(input, init);
    const url = typeof input === "string" ? input : input?.url;
    if (!url || (!url.endsWith("data/dashboard.json") && !url.endsWith("/api/dashboard"))) {
      return response;
    }

    try {
      const payload = await response.clone().json();
      applyFidelix2026H1(payload);
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
})();
