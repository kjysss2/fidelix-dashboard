const state = { data: null, filter: "all", polling: null };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value = "") => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const isStaticDashboard = () => Boolean(window.DASHBOARD_STATIC_MODE);
const dashboardDataUrl = () => window.DASHBOARD_DATA_URL || "/api/dashboard";

function fmtDate(value) {
  if (!value) return "—";
  const normalized = /^\d{8}$/.test(value) ? `${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}` : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return normalized;
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric" }).format(date);
}

function fmtUpdated(value) {
  if (!value) return "갱신 기록 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${new Intl.DateTimeFormat("ko-KR", {month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit"}).format(date)} 업데이트`;
}

function pct(value, compareLabel = "YoY") {
  if (value === null || value === undefined) return "";
  const tone = value >= 0 ? "positive-text" : "negative-text";
  return `<small class="${tone}">${compareLabel} ${value >= 0 ? "+" : ""}${Number(value).toFixed(1)}%</small>`;
}

function freshness(value) {
  if (!value) return "기준일 없음";
  const days = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 86400000));
  return days === 0 ? "오늘 확인" : `${days}일 전 확인`;
}

function render(data) {
  state.data = data;
  renderTop(data);
  renderThesis(data.thesisChecks);
  renderCompanies(data.companies);
  renderMonthlyCharts(data.companies);
  renderSpotPrices(data.spotPrices);
  renderJejuTrade(data.jejuTrade);
  renderQuarterlyCharts(data.companies);
  renderChinaOrders(data.chinaServerOrders);
  renderCalendar(data.calendar);
  renderQuestions(data.companies);
  renderFeed(data.feed);
  renderSources(data.sources, data.system);
}

function renderTop(data) {
  const live = data.sources.filter(s => s.status === "live").length;
  $("#topStatus").textContent = `${live}/${data.sources.length}개 데이터 소스 정상`;
  $("#lastUpdated").textContent = fmtUpdated(data.system.lastRefresh);
  const future = [...data.calendar].filter(e => new Date(e.date) >= new Date(new Date().toDateString())).sort((a,b) => a.date.localeCompare(b.date))[0] || data.calendar[0];
  if (future) {
    $("#nextEventDate").textContent = fmtDate(future.date);
    $("#nextEventTitle").textContent = `${future.company} · ${future.event}`;
  }
  $("#refreshButton").classList.toggle("loading", Boolean(data.system.refreshing));
}

function renderThesis(items) {
  $("#thesisGrid").innerHTML = items.map(item => `
    <article class="thesis-card ${esc(item.tone)}">
      <span class="label">${esc(item.label)}</span>
      <div class="value">${esc(item.value)}</div>
      <p>${esc(item.detail)}</p>
    </article>`).join("");
}

function identity(company) {
  return `<div class="identity-top">
    <span class="flag">${esc(company.country)}</span>
    <div><span class="company-name">${esc(company.name)}</span><span class="company-ticker">${esc(company.market)} · ${esc(company.ticker)}</span></div>
  </div>`;
}

function renderCompanies(companies) {
  const fidelix = companies.find(c => c.id === "fidelix");
  $("#fidelixFeature").innerHTML = `<article class="company-card feature-card" data-country="${fidelix.country}">
    <div class="company-identity">
      ${identity(fidelix)}
      <span class="role-tag">${esc(fidelix.role)}</span>
      <p class="focus">${esc(fidelix.focus)}</p>
    </div>
    <div class="feature-metrics">
      <div class="metric"><label>${esc(fidelix.metrics.period)} 매출</label><strong>${esc(fidelix.metrics.revenueDisplay)}</strong>${pct(fidelix.metrics.revenueYoY)}</div>
      <div class="metric"><label>영업이익</label><strong>${esc(fidelix.metrics.operatingIncomeDisplay)}</strong></div>
      <div class="metric"><label>순이익</label><strong>${esc(fidelix.metrics.netIncomeDisplay)}</strong></div>
    </div>
    <div class="feature-note"><span>KEY READ</span><strong>${esc(fidelix.note)}</strong><a href="${esc(fidelix.sourceUrl)}" target="_blank" rel="noreferrer">${esc(fidelix.sourceLabel)} ↗</a></div>
  </article>`;

  const peers = companies.filter(c => c.id !== "fidelix");
  $("#peerGrid").innerHTML = peers.map(company => `<article class="company-card peer-card ${state.filter !== "all" && state.filter !== company.country ? "hidden-card" : ""}" data-country="${company.country}">
    ${identity(company)}
    <span class="role-tag">${esc(company.role)}</span>
    <p class="focus">${esc(company.focus)}</p>
    <div class="peer-primary"><label>${esc(company.metrics.period)} ${esc(company.metrics.periodType)}</label><strong>${esc(company.metrics.revenueDisplay)}</strong></div>
    <div class="peer-change ${company.metrics.revenueYoY >= 0 ? "positive-text" : "negative-text"}">${company.metrics.revenueYoY == null ? "YoY —" : `YoY ${company.metrics.revenueYoY >= 0 ? "+" : ""}${Number(company.metrics.revenueYoY).toFixed(1)}%`}</div>
    <div class="peer-footer"><span>${esc(freshness(company.updatedAt))}</span><a class="verify" href="${esc(company.sourceUrl)}" target="_blank" rel="noreferrer">원문 ↗</a></div>
  </article>`).join("");

  const featureVisible = state.filter === "all" || state.filter === "KR";
  $("#fidelixFeature").classList.toggle("hidden-card", !featureVisible);
}

function chartMarkup(company, color) {
  const history = [...(company.monthlyHistory || [])].sort((a, b) => a.period.localeCompare(b.period));
  if (history.length < 2) return "";
  const width = 420, height = 188;
  const pad = { left: 10, right: 10, top: 18, bottom: 30 };
  const values = history.map(item => Number(item.revenue) / 100);
  const rawMin = Math.min(...values), rawMax = Math.max(...values);
  const min = 0, max = Math.max(rawMax * 1.12, 1);
  const plotWidth = width - pad.left - pad.right;
  const baseline = height - pad.bottom;
  const slot = plotWidth / history.length;
  const barWidth = Math.max(3, slot * .7);
  const x = index => pad.left + index * slot + (slot - barWidth) / 2;
  const y = value => pad.top + (max - value) * (height - pad.top - pad.bottom) / max;
  const labelIndexes = [...new Set([0, Math.round((history.length - 1) / 3), Math.round((history.length - 1) * 2 / 3), history.length - 1])];
  const grid = [0, .5, 1].map(ratio => {
    const gy = pad.top + ratio * (height - pad.top - pad.bottom);
    const value = max - ratio * (max - min);
    return `<line x1="${pad.left}" y1="${gy}" x2="${width-pad.right}" y2="${gy}" class="chart-gridline"/><text x="${width-pad.right}" y="${gy-4}" class="chart-ylabel">${value.toFixed(0)}</text>`;
  }).join("");
  const labels = labelIndexes.map(index => `<text x="${x(index) + barWidth / 2}" y="${height - 8}" text-anchor="middle" class="chart-xlabel">${history[index].period.slice(2).replace("-", ".")}</text>`).join("");
  const bars = history.map((item, index) => {
    const barY = y(values[index]);
    const barHeight = Math.max(1, baseline - barY);
    return `<rect class="revenue-bar" x="${x(index).toFixed(1)}" y="${barY.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}" rx="1.8" fill="${color}" data-period="${item.period}" data-value="${values[index].toFixed(1)}" tabindex="0" role="graphics-symbol" aria-label="${item.period} 월매출 NT$ ${values[index].toFixed(1)}억"><title>${item.period} · NT$ ${values[index].toFixed(1)}억</title></rect>`;
  }).join("");
  const latest = history[history.length - 1];
  const latestValue = values[values.length - 1];
  const low = Math.min(...values), high = Math.max(...values);
  return `<article class="trend-card">
    <div class="trend-head">
      <div><span class="trend-company">${esc(company.name)}</span><small>${esc(company.market)} · ${esc(company.ticker)}</small></div>
      <div class="trend-latest"><strong>NT$ ${latestValue.toFixed(1)}억</strong><span class="${latest.yoy >= 0 ? "positive-text" : "negative-text"}">YoY ${latest.yoy >= 0 ? "+" : ""}${Number(latest.yoy).toFixed(1)}%</span></div>
    </div>
    <svg class="monthly-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(company.name)} 최근 ${history.length}개월 월매출 그래프">
      ${grid}${bars}${labels}
      <g class="chart-tooltip" aria-hidden="true"><rect x="-58" y="-29" width="116" height="23" rx="5"></rect><text x="0" y="-14" text-anchor="middle"></text></g>
    </svg>
    <div class="trend-foot"><span>${history[0].period}–${latest.period}</span><span>3년 범위 ${low.toFixed(1)}–${high.toFixed(1)}억</span></div>
  </article>`;
}

function renderMonthlyCharts(companies) {
  const colors = { winbond: "#0d6b4d", nanya: "#b87419", macronix: "#2e7a8f" };
  const html = ["winbond", "nanya", "macronix"].map(id => {
    const company = companies.find(item => item.id === id);
    return company ? chartMarkup(company, colors[id]) : "";
  }).filter(Boolean).join("");
  $("#monthlyChartGrid").innerHTML = html || `<div class="chart-empty">월매출 이력을 수집 중입니다. 다음 갱신 후 표시됩니다.</div>`;
  bindChartTooltips();
}

function bindChartTooltips() {
  $$(".monthly-chart").forEach(chart => {
    const tooltip = chart.querySelector(".chart-tooltip");
    const label = tooltip?.querySelector("text");
    if (!tooltip || !label) return;
    const show = bar => {
      const center = Number(bar.getAttribute("x")) + Number(bar.getAttribute("width")) / 2;
      const top = Number(bar.getAttribute("y"));
      const tx = Math.max(62, Math.min(358, center));
      const ty = Math.max(38, top);
      label.textContent = `${bar.dataset.period} · NT$ ${bar.dataset.value}억`;
      tooltip.setAttribute("transform", `translate(${tx} ${ty})`);
      tooltip.classList.add("show");
    };
    const hide = () => tooltip.classList.remove("show");
    chart.querySelectorAll(".revenue-bar").forEach(bar => {
      bar.addEventListener("mouseenter", () => show(bar));
      bar.addEventListener("focus", () => show(bar));
      bar.addEventListener("mouseleave", hide);
      bar.addEventListener("blur", hide);
      bar.addEventListener("click", () => show(bar));
    });
  });
}

function spotNumber(value) {
  if (value === null || value === undefined) return "—";
  return `$${Number(value).toLocaleString("ko-KR", {minimumFractionDigits: 3, maximumFractionDigits: 3})}`;
}

function spotChartMarkup(product) {
  const history = [...(product.history || [])].filter(item => item.average != null).sort((a,b) => String(a.date).localeCompare(String(b.date)));
  if (!history.length) return "";
  const width = 520, height = 210;
  const pad = {left: 38, right: 16, top: 22, bottom: 33};
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const values = history.map(item => Number(item.average));
  let min = Math.min(...values), max = Math.max(...values);
  if (min === max) {
    min = Math.max(0, min * .94);
    max = max * 1.06 || 1;
  } else {
    const span = max - min;
    min = Math.max(0, min - span * .12);
    max = max + span * .12;
  }
  const x = index => history.length === 1 ? pad.left + plotWidth / 2 : pad.left + index * plotWidth / (history.length - 1);
  const y = value => pad.top + (max - value) * plotHeight / (max - min);
  const color = product.color || "#2e7a8f";
  const points = history.map((item,index) => `${x(index).toFixed(1)},${y(Number(item.average)).toFixed(1)}`).join(" ");
  const grid = [0,.5,1].map(ratio => {
    const gy = pad.top + ratio * plotHeight;
    const value = max - ratio * (max - min);
    return `<line x1="${pad.left}" y1="${gy}" x2="${width-pad.right}" y2="${gy}" class="chart-gridline"/><text x="${pad.left-6}" y="${gy+3}" text-anchor="end" class="quarter-axis-label">${value.toFixed(1)}</text>`;
  }).join("");
  const labelIndexes = history.length === 1 ? [0] : [...new Set([0, Math.floor((history.length-1)/2), history.length-1])];
  const labels = labelIndexes.map(index => `<text x="${x(index)}" y="${height-10}" text-anchor="middle" class="chart-xlabel">${String(history[index].date).slice(5).replace("-",".")}</text>`).join("");
  const dots = history.map((item,index) => `<circle cx="${x(index).toFixed(1)}" cy="${y(Number(item.average)).toFixed(1)}" r="3.2" fill="#fff" stroke="${color}" stroke-width="2"><title>${item.date} · ${spotNumber(item.average)} · ${item.change == null ? "—" : `${Number(item.change).toFixed(2)}%`}</title></circle>`).join("");
  const polyline = history.length > 1 ? `<polyline points="${points}" class="spot-line" style="stroke:${color}"></polyline>` : "";
  return `<svg class="spot-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(product.name)} 현물가 추이">
    ${grid}${polyline}${dots}${labels}
  </svg>`;
}

function renderSpotPrices(payload) {
  const container = $("#spotPriceGrid");
  if (!container) return;
  const products = payload?.products || [];
  if (!products.length) {
    container.innerHTML = `<div class="chart-empty">DRAMeXchange 현물가 데이터를 수집 중입니다.</div>`;
    return;
  }
  container.innerHTML = products.map(product => {
    const history = [...(product.history || [])].filter(item => item.average != null).sort((a,b) => String(a.date).localeCompare(String(b.date)));
    const latest = product.latest || history[history.length - 1] || {};
    const change = latest.change == null ? "—" : `${Number(latest.change) >= 0 ? "+" : ""}${Number(latest.change).toFixed(2)}%`;
    const tone = Number(latest.change) >= 0 ? "positive-text" : "negative-text";
    return `<article class="spot-card">
      <div class="spot-head">
        <div><span>${esc(product.name)}</span><small>${esc(product.label)}</small></div>
        <a href="${esc(payload.sourceUrl || "https://www.dramexchange.com/")}" target="_blank" rel="noreferrer">${esc(payload.sourceLabel || "DRAMeXchange")} ↗</a>
      </div>
      <div class="spot-kpis">
        <div><label>Session Average</label><strong>${esc(spotNumber(latest.average))}</strong></div>
        <div><label>Session Change</label><strong class="${tone}">${esc(change)}</strong></div>
        <div><label>최근 기준</label><strong>${esc(latest.date || "—")}</strong></div>
      </div>
      ${spotChartMarkup(product)}
      <div class="spot-foot">
        <span>${history.length ? `${history[0].date}–${history[history.length-1].date}` : "이력 수집 전"}</span>
        <span>${esc(latest.sourceTime || payload.updatedAt || "")}</span>
      </div>
    </article>`;
  }).join("");
}


function normalizeTradeRows(rows = [], columns = []) {
  if (!Array.isArray(rows)) return [];
  if (!rows.length || (!Array.isArray(rows[0]) && typeof rows[0] === "object")) return rows;
  return rows.map(row => columns.reduce((item, key, index) => {
    item[key] = row[index];
    return item;
  }, {}));
}

function tradeEok(value) {
  if (value === null || value === undefined) return "—";
  const amount = Number(value) / 100000;
  return `${amount.toLocaleString("ko-KR", {minimumFractionDigits: amount < 10 ? 1 : 0, maximumFractionDigits: 1})}억원`;
}

function tradeUsd(value) {
  if (value === null || value === undefined) return "—";
  return `$${(Number(value) / 1000000).toLocaleString("ko-KR", {maximumFractionDigits: 1})}M`;
}

function tradeUnit(value) {
  if (value === null || value === undefined) return "—";
  return `$${Number(value).toLocaleString("ko-KR", {maximumFractionDigits: 0})}`;
}

function signedPercent(value) {
  if (value === null || value === undefined) return "—";
  return `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(1)}%`;
}

function percentTone(value) {
  return Number(value) >= 0 ? "positive-text" : "negative-text";
}

function tradeMonthLabel(period) {
  const [year = "", month = ""] = String(period || "").split("-");
  return year && month ? `${year.slice(2)}.${month}` : "—";
}

function tradeQuarterLabel(period) {
  period = String(period || "");
  return period.length >= 6 ? `${period.slice(2, 4)}Q${period.slice(-1)}` : period || "—";
}

function latestWith(rows, key) {
  return [...rows].reverse().find(item => item?.[key] !== null && item?.[key] !== undefined) || rows[rows.length - 1] || {};
}

function jejuTradeMonthlyMarkup(payload) {
  const monthly = normalizeTradeRows(payload?.monthly, payload?.monthlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period)));
  const quarterly = normalizeTradeRows(payload?.quarterly, payload?.quarterlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period)));
  if (monthly.length < 2) return `<div class="chart-empty">제주반도체 월별 수출입 데이터를 수집 중입니다.</div>`;

  const latest = latestWith(monthly, "exportKrwThousand");
  const latestQuarter = latestWith(quarterly, "exportKrwThousand");
  const width = 940, height = 330;
  const pad = {left: 58, right: 72, top: 28, bottom: 56};
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const exports = monthly.map(item => Number(item.exportKrwThousand) / 100000);
  const units = monthly.map(item => Number(item.unitUsd)).filter(value => Number.isFinite(value));
  const exportMax = Math.max(1, ...exports) * 1.12;
  const unitMax = Math.max(1, ...units) * 1.12;
  const slot = plotWidth / monthly.length;
  const barWidth = Math.max(3, slot * .66);
  const x = index => pad.left + index * slot + slot / 2;
  const barX = index => x(index) - barWidth / 2;
  const exportY = value => pad.top + (exportMax - value) * plotHeight / exportMax;
  const unitY = value => pad.top + (unitMax - value) * plotHeight / unitMax;
  const baseline = pad.top + plotHeight;
  const grid = [0, .25, .5, .75, 1].map(ratio => {
    const gy = pad.top + ratio * plotHeight;
    const value = exportMax - ratio * exportMax;
    return `<line x1="${pad.left}" y1="${gy}" x2="${width-pad.right}" y2="${gy}" class="chart-gridline"/><text x="${pad.left-7}" y="${gy+3}" text-anchor="end" class="quarter-axis-label">${value.toFixed(0)}</text>`;
  }).join("");
  const rightLabels = [unitMax, unitMax / 2, 0].map((value,index) => `<text x="${width-pad.right+7}" y="${pad.top + index*plotHeight/2 + 3}" class="quarter-axis-label">$${value.toFixed(0)}</text>`).join("");
  const labelIndexes = monthly.map((_, index) => index).filter(index => index % 6 === 0 || index === monthly.length - 1);
  const labels = labelIndexes.map(index => `<text x="${x(index)}" y="${height-12}" text-anchor="middle" class="chart-xlabel">${tradeMonthLabel(monthly[index].period)}</text>`).join("");
  const bars = monthly.map((item,index) => {
    const value = Number(item.exportKrwThousand) / 100000;
    const y = exportY(value);
    const title = `${item.period} · 수출액 ${tradeEok(item.exportKrwThousand)} (${tradeUsd(item.exportUsd)}) · 단가 ${tradeUnit(item.unitUsd)} · YoY ${signedPercent(item.exportYoY)} · MoM ${signedPercent(item.exportMoM)}`;
    const hot = Number(item.exportYoY) >= 100 ? " hot" : "";
    return `<rect class="trade-bar export${hot}" x="${barX(index).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(1, baseline-y).toFixed(1)}" rx="1.5"><title>${esc(title)}</title></rect>`;
  }).join("");
  const unitPoints = monthly.map((item,index) => `${x(index).toFixed(1)},${unitY(Number(item.unitUsd)).toFixed(1)}`).join(" ");
  const unitDots = monthly.map((item,index) => index % 3 === 0 || index === monthly.length - 1 ? `<circle cx="${x(index).toFixed(1)}" cy="${unitY(Number(item.unitUsd)).toFixed(1)}" r="2.2" class="trade-dot unit"><title>${esc(`${item.period} · 단가 ${tradeUnit(item.unitUsd)} · 단가 MoM ${signedPercent(item.unitMoM)}`)}</title></circle>` : "").join("");

  return `<article class="trade-card">
    <div class="trade-card-head">
      <div><span>월별 수출입 데이터</span><small>${esc(payload?.basis || "제주반도체 수출입 데이터")}</small></div>
      <strong>${tradeMonthLabel(latest.period)}</strong>
    </div>
    <div class="trade-kpis">
      <div><label>최근 월 수출액</label><strong>${tradeEok(latest.exportKrwThousand)}</strong><span class="${percentTone(latest.exportYoY)}">YoY ${signedPercent(latest.exportYoY)}</span></div>
      <div><label>월간 증감</label><strong class="${percentTone(latest.exportMoM)}">${signedPercent(latest.exportMoM)}</strong><span>수출금액 MoM</span></div>
      <div><label>단가</label><strong>${tradeUnit(latest.unitUsd)}</strong><span class="${percentTone(latest.unitMoM)}">MoM ${signedPercent(latest.unitMoM)}</span></div>
      <div><label>최근 분기합</label><strong>${tradeEok(latestQuarter.exportKrwThousand)}</strong><span class="${percentTone(latestQuarter.exportQoQ)}">QoQ ${signedPercent(latestQuarter.exportQoQ)}</span></div>
    </div>
    <div class="trade-legend"><span><i class="trade-swatch export"></i>수출액</span><span><i class="trade-swatch hot"></i>YoY +100% 이상</span><span><i class="trade-line unit"></i>단가</span></div>
    <svg class="trade-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="제주반도체 월별 수출액과 단가 추이">
      ${grid}${rightLabels}${bars}<polyline points="${unitPoints}" class="trade-unit-line"></polyline>${unitDots}${labels}
    </svg>
    <div class="trade-foot"><span>${tradeMonthLabel(monthly[0].period)}–${tradeMonthLabel(latest.period)}</span><span>${esc(payload?.note || "")}</span></div>
  </article>`;
}

function jejuTradeQuarterMarkup(payload) {
  const quarterly = normalizeTradeRows(payload?.quarterly, payload?.quarterlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period)));
  if (quarterly.length < 2) return `<div class="chart-empty">제주반도체 분기 수출입 데이터를 수집 중입니다.</div>`;

  const latestExport = latestWith(quarterly, "exportKrwThousand");
  const latestRevenue = latestWith(quarterly, "revenueKrwThousand");
  const latestOpm = latestWith(quarterly, "opm");
  const width = 940, height = 344;
  const pad = {left: 58, right: 64, top: 28, bottom: 56};
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const moneyValues = quarterly.flatMap(item => [item.revenueKrwThousand, item.exportKrwThousand].filter(value => value !== null && value !== undefined).map(value => Number(value) / 100000));
  const moneyMax = Math.max(1, ...moneyValues) * 1.12;
  const opmValues = quarterly.map(item => item.opm).filter(value => value !== null && value !== undefined).map(Number);
  let opmMin = Math.min(0, ...opmValues), opmMax = Math.max(0, ...opmValues);
  const opmSpan = Math.max(opmMax - opmMin, 10);
  opmMin -= opmSpan * .12;
  opmMax += opmSpan * .12;
  const slot = plotWidth / quarterly.length;
  const barWidth = Math.max(3, slot * .27);
  const x = index => pad.left + index * slot + slot / 2;
  const moneyY = value => pad.top + (moneyMax - value) * plotHeight / moneyMax;
  const opmY = value => pad.top + (opmMax - value) * plotHeight / (opmMax - opmMin);
  const baseline = pad.top + plotHeight;
  const grid = [0, .25, .5, .75, 1].map(ratio => {
    const gy = pad.top + ratio * plotHeight;
    const value = moneyMax - ratio * moneyMax;
    return `<line x1="${pad.left}" y1="${gy}" x2="${width-pad.right}" y2="${gy}" class="chart-gridline"/><text x="${pad.left-7}" y="${gy+3}" text-anchor="end" class="quarter-axis-label">${value.toFixed(0)}</text>`;
  }).join("");
  const rightLabels = [opmMax, (opmMax+opmMin)/2, opmMin].map((value,index) => `<text x="${width-pad.right+7}" y="${pad.top + index*plotHeight/2 + 3}" class="quarter-axis-label">${value.toFixed(0)}%</text>`).join("");
  const bars = quarterly.map((item,index) => {
    const rendered = [];
    [["revenueKrwThousand", "revenue", -0.58, "매출액"], ["exportKrwThousand", "export", 0.58, "수출액"]].forEach(([key, cls, offset, label]) => {
      if (item[key] === null || item[key] === undefined) return;
      const value = Number(item[key]) / 100000;
      const y = moneyY(value);
      const qoq = key === "exportKrwThousand" ? ` · QoQ ${signedPercent(item.exportQoQ)} · YoY ${signedPercent(item.exportYoY)}` : "";
      rendered.push(`<rect class="trade-bar ${cls}" x="${(x(index) + offset * barWidth - barWidth / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(1, baseline-y).toFixed(1)}" rx="1.5"><title>${esc(`${item.period} · ${label} ${tradeEok(item[key])}${qoq}`)}</title></rect>`);
    });
    return rendered.join("");
  }).join("");
  const opmPoints = quarterly.map((item,index) => item.opm == null ? null : `${x(index).toFixed(1)},${opmY(Number(item.opm)).toFixed(1)}`).filter(Boolean).join(" ");
  const opmDots = quarterly.map((item,index) => item.opm == null ? "" : `<circle cx="${x(index).toFixed(1)}" cy="${opmY(Number(item.opm)).toFixed(1)}" r="2.7" class="trade-dot opm"><title>${esc(`${item.period} · OPM ${signedPercent(item.opm)}`)}</title></circle>`).join("");
  const labels = quarterly.map((item,index) => index % 4 === 0 || index === quarterly.length - 1 ? `<text x="${x(index)}" y="${height-12}" text-anchor="middle" class="chart-xlabel">${tradeQuarterLabel(item.period)}</text>` : "").join("");

  return `<article class="trade-card">
    <div class="trade-card-head">
      <div><span>분기합 + 매출액 + OPM</span><small>수출액과 제주반도체 분기 매출액을 같은 축으로 비교</small></div>
      <strong>${tradeQuarterLabel(latestExport.period)}</strong>
    </div>
    <div class="trade-kpis">
      <div><label>최근 수출액</label><strong>${tradeEok(latestExport.exportKrwThousand)}</strong><span class="${percentTone(latestExport.exportYoY)}">YoY ${signedPercent(latestExport.exportYoY)}</span></div>
      <div><label>수출액 QoQ</label><strong class="${percentTone(latestExport.exportQoQ)}">${signedPercent(latestExport.exportQoQ)}</strong><span>${tradeQuarterLabel(latestExport.period)}</span></div>
      <div><label>최근 매출액</label><strong>${tradeEok(latestRevenue.revenueKrwThousand)}</strong><span>${tradeQuarterLabel(latestRevenue.period)} · 수출비중 ${signedPercent(latestRevenue.exportToRevenuePct).replace("+", "")}</span></div>
      <div><label>OPM</label><strong>${signedPercent(latestOpm.opm).replace("+", "")}</strong><span>${tradeQuarterLabel(latestOpm.period)}</span></div>
    </div>
    <div class="trade-legend"><span><i class="trade-swatch revenue"></i>매출액</span><span><i class="trade-swatch export"></i>수출액</span><span><i class="trade-line opm"></i>OPM</span></div>
    <svg class="trade-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="제주반도체 분기 매출액 수출액 OPM 그래프">
      ${grid}${rightLabels}${bars}${opmPoints ? `<polyline points="${opmPoints}" class="trade-opm-line"></polyline>${opmDots}` : ""}${labels}
    </svg>
    <div class="trade-foot"><span>${tradeQuarterLabel(quarterly[0].period)}–${tradeQuarterLabel(latestExport.period)}</span><span>단위: 억원, %</span></div>
  </article>`;
}

function renderJejuTrade(payload) {
  const monthly = $("#jejuTradeMonthly");
  const quarterly = $("#jejuTradeQuarterly");
  if (!monthly || !quarterly) return;
  monthly.innerHTML = jejuTradeMonthlyMarkup(payload);
  quarterly.innerHTML = jejuTradeQuarterMarkup(payload);
}

function quarterValue(value, currency) {
  if (value === null || value === undefined) return "—";
  const amount = Number(value) / 100;
  const prefix = currency === "KRW" ? "" : currency === "TWD" ? "NT$ " : "CNY ";
  const suffix = currency === "KRW" ? "억원" : "억";
  return `${prefix}${amount.toLocaleString("ko-KR", {maximumFractionDigits: 1})}${suffix}`;
}

function quarterlyChartMarkup(company) {
  const history = [...(company.quarterlyHistory || [])].sort((a,b) => a.period.localeCompare(b.period)).slice(-12);
  if (history.length < 2) return "";
  const width = 620, height = 292;
  const pad = {left: 38, right: 40, top: 25, bottom: 36};
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const slot = plotWidth / history.length;
  const barWidth = Math.max(4, slot * .19);
  const toEok = value => value == null ? null : Number(value) / 100;
  const barSeries = [
    {key:"revenue", label:"매출", color:"#a9bbb3"},
    {key:"operatingIncome", label:"영업이익", color:"#2e7a8f"},
    {key:"netIncome", label:"순이익", color:"#c69b51"}
  ];
  const barValues = history.flatMap(item => barSeries.map(series => toEok(item[series.key])).filter(value => value != null));
  let barMin = Math.min(0, ...barValues), barMax = Math.max(0, ...barValues);
  const barSpan = Math.max(barMax - barMin, 1);
  barMin -= barSpan * .08; barMax += barSpan * .1;
  const barY = value => pad.top + (barMax - value) * plotHeight / (barMax - barMin);
  const zeroY = barY(0);

  const marginValues = history.flatMap(item => [item.operatingMargin, item.netMargin].filter(value => value != null).map(Number));
  let marginMin = Math.min(0, ...marginValues), marginMax = Math.max(0, ...marginValues);
  const marginSpan = Math.max(marginMax - marginMin, 10);
  marginMin -= marginSpan * .12; marginMax += marginSpan * .12;
  const marginY = value => pad.top + (marginMax - value) * plotHeight / (marginMax - marginMin);
  const centerX = index => pad.left + slot * index + slot / 2;

  const bars = history.map((item,index) => barSeries.map((series,seriesIndex) => {
    const value = toEok(item[series.key]);
    if (value == null) return "";
    const y = barY(value);
    const x = centerX(index) + (seriesIndex - 1) * (barWidth + 1) - barWidth / 2;
    return `<rect x="${x.toFixed(1)}" y="${Math.min(y,zeroY).toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(1,Math.abs(zeroY-y)).toFixed(1)}" rx="1.3" fill="${series.color}" opacity=".88"></rect>`;
  }).join("")).join("");

  const linePath = key => history.map((item,index) => item[key] == null ? null : `${centerX(index).toFixed(1)},${marginY(Number(item[key])).toFixed(1)}`).filter(Boolean).join(" ");
  const opPoints = linePath("operatingMargin"), netPoints = linePath("netMargin");
  const lineDots = (key,color) => history.map((item,index) => item[key] == null ? "" : `<circle cx="${centerX(index)}" cy="${marginY(Number(item[key]))}" r="2.5" fill="#fff" stroke="${color}" stroke-width="1.7"></circle>`).join("");
  const xLabels = history.map((item,index) => index % 2 === 0 || index === history.length-1 ? `<text x="${centerX(index)}" y="${height-10}" text-anchor="middle" class="chart-xlabel">${item.period.slice(2)}</text>` : "").join("");
  const leftGrid = [0,.5,1].map(ratio => {
    const gy = pad.top + ratio * plotHeight;
    const value = barMax - ratio * (barMax-barMin);
    return `<line x1="${pad.left}" y1="${gy}" x2="${width-pad.right}" y2="${gy}" class="chart-gridline"/><text x="${pad.left-5}" y="${gy+3}" text-anchor="end" class="quarter-axis-label">${value.toFixed(0)}</text>`;
  }).join("");
  const rightLabels = [marginMax,(marginMax+marginMin)/2,marginMin].map((value,index) => `<text x="${width-pad.right+5}" y="${pad.top + index*plotHeight/2 + 3}" class="quarter-axis-label">${value.toFixed(0)}%</text>`).join("");
  const hits = history.map((item,index) => `<rect class="quarter-hit" x="${(pad.left+index*slot).toFixed(1)}" y="${pad.top}" width="${slot.toFixed(1)}" height="${plotHeight}" fill="transparent" tabindex="0" data-index="${index}" aria-label="${item.period} 실적"></rect>`).join("");
  const latest = history[history.length-1];
  const currencyLabel = latest.currency === "KRW" ? "KRW 억원" : latest.currency === "TWD" ? "NT$ 억" : "CNY 억";
  return `<article class="quarter-card">
    <div class="quarter-head"><div><span>${esc(company.name)}</span><small>${esc(company.market)} · ${esc(company.ticker)} · ${currencyLabel}</small></div><strong>${esc(latest.period)}</strong></div>
    <div class="quarter-legend">
      ${barSeries.map(series => `<span><i style="background:${series.color}"></i>${series.label}</span>`).join("")}
      <span><i class="dash op"></i>영업이익률</span><span><i class="dash net"></i>순이익률</span>
    </div>
    <div class="quarter-chart-wrap">
      <svg class="quarter-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(company.name)} 최근 12개 분기 실적과 이익률">
        ${leftGrid}<line x1="${pad.left}" y1="${zeroY}" x2="${width-pad.right}" y2="${zeroY}" class="zero-line"/>
        ${bars}
        ${opPoints ? `<polyline points="${opPoints}" class="margin-line op"></polyline>${lineDots("operatingMargin","#0d6b4d")}` : ""}
        ${netPoints ? `<polyline points="${netPoints}" class="margin-line net"></polyline>${lineDots("netMargin","#b24c44")}` : ""}
        ${rightLabels}${xLabels}${hits}
      </svg>
      <div class="quarter-tooltip"></div>
    </div>
    <div class="quarter-source"><span>${history[0].period}–${latest.period}</span><span>${esc(latest.source || "공시")}</span></div>
  </article>`;
}

function bindQuarterTooltips(companies) {
  $$(".quarter-card").forEach((card, cardIndex) => {
    const company = companies[cardIndex];
    const history = [...(company.quarterlyHistory || [])].sort((a,b) => a.period.localeCompare(b.period)).slice(-12);
    const tooltip = card.querySelector(".quarter-tooltip");
    const show = hit => {
      const item = history[Number(hit.dataset.index)];
      if (!item) return;
      tooltip.innerHTML = `<strong>${esc(item.period)}</strong><div><span>매출 ${quarterValue(item.revenue,item.currency)}</span><span>영업이익 ${quarterValue(item.operatingIncome,item.currency)}</span><span>순이익 ${quarterValue(item.netIncome,item.currency)}</span><span>OPM ${item.operatingMargin == null ? "—" : `${Number(item.operatingMargin).toFixed(1)}%`} · NPM ${item.netMargin == null ? "—" : `${Number(item.netMargin).toFixed(1)}%`}</span></div>`;
      const index = Number(hit.dataset.index);
      tooltip.style.left = `${Math.max(18,Math.min(82,(index+.5)/history.length*100))}%`;
      tooltip.classList.add("show");
    };
    const hide = () => tooltip.classList.remove("show");
    card.querySelectorAll(".quarter-hit").forEach(hit => {
      hit.addEventListener("mouseenter", () => show(hit));
      hit.addEventListener("focus", () => show(hit));
      hit.addEventListener("click", () => show(hit));
      hit.addEventListener("mouseleave", hide);
      hit.addEventListener("blur", hide);
    });
  });
}

function renderQuarterlyCharts(companies) {
  const ordered = ["fidelix","jeju","winbond","nanya","macronix","dosilicon"].map(id => companies.find(company => company.id === id)).filter(Boolean);
  const html = ordered.map(quarterlyChartMarkup).filter(Boolean).join("");
  $("#quarterlyChartGrid").innerHTML = html || `<div class="chart-empty">분기 실적 이력을 수집 중입니다.</div>`;
  bindQuarterTooltips(ordered.filter(company => (company.quarterlyHistory || []).length >= 2));
}

function orderDisplay(value, unit = "MW") {
  if (value === null || value === undefined || value === "") return "—";
  const formatted = Number(value).toLocaleString("ko-KR", {maximumFractionDigits: unit === "%" ? 0 : 1});
  return unit === "%" ? `${formatted}%` : `${formatted} ${unit}`;
}

function renderChinaOrders(payload) {
  const container = $("#chinaOrderGrid");
  if (!container) return;
  const companies = payload?.companies || [];
  if (!companies.length) {
    container.innerHTML = `<div class="chart-empty">중국 IDC 신규수주 데이터를 수집 중입니다.</div>`;
    return;
  }
  container.innerHTML = companies.map(company => {
    const series = company.series || [];
    const backlog = company.backlog || [];
    const max = Math.max(1, ...series.map(item => Number(item.value) || 0));
    const latest = company.latest || series[series.length - 1] || {};
    const bars = series.map(item => {
      const value = Number(item.value) || 0;
      const width = Math.max(2, value / max * 100);
      const tooltip = `${item.period} · ${orderDisplay(item.value, item.unit)} · ${item.basis || item.category || ""}`;
      return `<div class="order-row" title="${esc(tooltip)}">
        <span class="order-period">${esc(item.period)}</span>
        <div class="order-track"><i style="width:${width.toFixed(1)}%"></i></div>
        <span class="order-value">${esc(orderDisplay(item.value, item.unit))}</span>
        <small>${esc(item.category || item.basis || "")}</small>
      </div>`;
    }).join("");
    const backlogItems = backlog.map(item => `<div class="backlog-chip" title="${esc(item.basis || "")}">
      <span>${esc(item.label)}${item.derived ? " · 계산값" : ""}</span>
      <strong>${esc(orderDisplay(item.value, item.unit))}</strong>
    </div>`).join("");
    return `<article class="china-order-card">
      <div class="china-order-head">
        <div><span class="china-company">${esc(company.name)}</span><small>${esc(company.note || "")}</small></div>
        <a href="${esc(company.sourceUrl)}" target="_blank" rel="noreferrer">${esc(company.sourceLabel || "공식 IR")} ↗</a>
      </div>
      <div class="order-kpis">
        <div><label>최근 신규수주</label><strong>${esc(orderDisplay(latest.value, latest.unit))}</strong><span>${esc(latest.label || "최근")}</span></div>
        <div><label>업데이트</label><strong>${esc(fmtDate(company.updatedAt))}</strong><span>${esc(freshness(company.updatedAt))}</span></div>
        <div><label>기준</label><strong>${esc(latest.unit || "MW")}</strong><span>${esc(latest.basis || "공식 IR")}</span></div>
      </div>
      <div class="order-bars">${bars || `<p class="order-empty">신규수주 막대 데이터를 수집 중입니다.</p>`}</div>
      <div class="backlog-title">백로그·확약/활용 용량</div>
      <div class="backlog-grid">${backlogItems || `<div class="backlog-chip"><span>원문 확인 대기</span><strong>—</strong></div>`}</div>
    </article>`;
  }).join("");
}

function renderCalendar(events) {
  const today = new Date();
  $("#timeline").innerHTML = [...events].sort((a,b) => a.date.localeCompare(b.date)).map(event => {
    const days = Math.ceil((new Date(event.date) - today) / 86400000);
    const dayLabel = days < 0 ? "완료" : days === 0 ? "D-day" : `D-${days}`;
    return `<div class="timeline-item ${esc(event.importance)}">
      <span class="timeline-date">${esc(fmtDate(event.date))}</span>
      <div class="timeline-copy"><strong>${esc(event.event)}</strong><p>${esc(event.company)}</p></div>
      <span class="days-left">${dayLabel}</span>
    </div>`;
  }).join("");
}

function renderQuestions(companies) {
  const ordered = ["fidelix", "jeju", "dosilicon", "nanya", "winbond", "macronix"];
  const questions = ordered.flatMap(id => {
    const company = companies.find(c => c.id === id);
    return (company?.questions || []).slice(0, 1).map(text => ({company: company.name, text}));
  });
  $("#questionCount").textContent = questions.length;
  $("#questionList").innerHTML = questions.map((q, index) => `<div class="question-item">
    <span class="question-index">${String(index + 1).padStart(2,"0")}</span>
    <div><strong>${esc(q.company)}</strong><p>${esc(q.text)}</p></div>
  </div>`).join("");
}

function renderFeed(items) {
  if (!items.length) {
    $("#feedList").innerHTML = `<div class="feed-item"><span>최근 공시가 없습니다.</span></div>`;
    return;
  }
  const dateKey = item => String(item.date || "").replace(/\D/g, "").padEnd(14, "0");
  const newestFirst = [...items].sort((a,b) => dateKey(b).localeCompare(dateKey(a)));
  $("#feedList").innerHTML = newestFirst.slice(0, 12).map(item => `<a class="feed-item" href="${esc(item.url)}" target="_blank" rel="noreferrer">
    <span class="feed-date">${esc(fmtDate(item.date))}</span>
    <span class="feed-company">${esc(item.company)}</span>
    <span class="feed-title">${esc(item.title)}</span>
    <span class="feed-source">${esc(item.source)}</span>
    <span class="feed-arrow">↗</span>
  </a>`).join("");
}

function renderSources(sources, system) {
  $("#sourceGrid").innerHTML = sources.map(source => `<a class="source-card" href="${esc(source.url)}" target="_blank" rel="noreferrer">
    <div class="source-head"><strong>${esc(source.name)}</strong><span class="status-pill ${esc(source.status)}">${esc(source.status)}</span></div>
    <p>${esc(source.message)}</p>
    <small>${source.checkedAt ? fmtUpdated(source.checkedAt) : "연결 대기"}</small>
  </a>`).join("");
  if (system.lastRefreshErrors?.length) showToast(`일부 소스 확인 필요: ${system.lastRefreshErrors[0]}`);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3500);
}

async function loadDashboard() {
  try {
    const response = await fetch(dashboardDataUrl(), { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    showToast(`대시보드를 불러오지 못했습니다: ${error.message}`);
  }
}

async function refreshDashboard() {
  if (isStaticDashboard()) {
    showToast("GitHub Actions가 매일 08시경 자동 갱신합니다. GitHub에서 수동 실행도 가능합니다.");
    return;
  }
  const button = $("#refreshButton");
  button.classList.add("loading");
  button.disabled = true;
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const result = await response.json();
    showToast(result.message || "갱신을 시작했습니다.");
    let attempts = 0;
    clearInterval(state.polling);
    state.polling = setInterval(async () => {
      attempts += 1;
      await loadDashboard();
      if (!state.data?.system?.refreshing || attempts > 20) {
        clearInterval(state.polling);
        button.classList.remove("loading");
        button.disabled = false;
        showToast("최신 데이터 확인을 마쳤습니다.");
      }
    }, 1500);
  } catch (error) {
    button.classList.remove("loading");
    button.disabled = false;
    showToast(`갱신 실패: ${error.message}`);
  }
}

function bindEvents() {
  $("#refreshButton").addEventListener("click", refreshDashboard);
  $("#menuButton").addEventListener("click", () => document.body.classList.toggle("menu-open"));
  $$(".nav a").forEach(link => link.addEventListener("click", () => document.body.classList.remove("menu-open")));
  $$(".segmented button").forEach(button => button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    $$(".segmented button").forEach(item => item.classList.toggle("active", item === button));
    renderCompanies(state.data.companies);
  }));
  $("#setupButton").addEventListener("click", () => $("#setupGuide").hidden = false);
  $("#setupClose").addEventListener("click", () => $("#setupGuide").hidden = true);
}

bindEvents();
loadDashboard();
