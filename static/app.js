const state = { data: null, filter: "all", polling: null };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value = "") => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const isStaticDashboard = () => Boolean(window.DASHBOARD_STATIC_MODE);
const dashboardDataUrl = () => window.DASHBOARD_DATA_URL || "/api/dashboard";

function fmtDate(value) {
  if (!value) return "\u2014";
  const normalized = /^\d{8}$/.test(value) ? `${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}` : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return normalized;
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric" }).format(date);
}

function fmtUpdated(value) {
  if (!value) return "\uac31\uc2e0 \uae30\ub85d \uc5c6\uc74c";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${new Intl.DateTimeFormat("ko-KR", {month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit"}).format(date)} \uc5c5\ub370\uc774\ud2b8`;
}

function pct(value, compareLabel = "YoY") {
  if (value === null || value === undefined) return "";
  const tone = value >= 0 ? "positive-text" : "negative-text";
  return `<small class="${tone}">${compareLabel} ${value >= 0 ? "+" : ""}${Number(value).toFixed(1)}%</small>`;
}

function freshness(value) {
  if (!value) return "\uae30\uc900\uc77c \uc5c6\uc74c";
  const days = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 86400000));
  return days === 0 ? "\uc624\ub298 \ud655\uc778" : `${days}\uc77c \uc804 \ud655\uc778`;
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
  $("#topStatus").textContent = `${live}/${data.sources.length}\uac1c \ub370\uc774\ud130 \uc18c\uc2a4 \uc815\uc0c1`;
  $("#lastUpdated").textContent = fmtUpdated(data.system.lastRefresh);
  const future = [...data.calendar].filter(e => new Date(e.date) >= new Date(new Date().toDateString())).sort((a,b) => a.date.localeCompare(b.date))[0] || data.calendar[0];
  if (future) {
    $("#nextEventDate").textContent = fmtDate(future.date);
    $("#nextEventTitle").textContent = `${future.company} \u00b7 ${future.event}`;
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
    <div><span class="company-name">${esc(company.name)}</span><span class="company-ticker">${esc(company.market)} \u00b7 ${esc(company.ticker)}</span></div>
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
      <div class="metric"><label>${esc(fidelix.metrics.period)} \ub9e4\ucd9c</label><strong>${esc(fidelix.metrics.revenueDisplay)}</strong>${pct(fidelix.metrics.revenueYoY)}</div>
      <div class="metric"><label>\uc601\uc5c5\uc774\uc775</label><strong>${esc(fidelix.metrics.operatingIncomeDisplay)}</strong></div>
      <div class="metric"><label>\uc21c\uc774\uc775</label><strong>${esc(fidelix.metrics.netIncomeDisplay)}</strong></div>
    </div>
    <div class="feature-note"><span>KEY READ</span><strong>${esc(fidelix.note)}</strong><a href="${esc(fidelix.sourceUrl)}" target="_blank" rel="noreferrer">${esc(fidelix.sourceLabel)} \u2197</a></div>
  </article>`;

  const peers = companies.filter(c => c.id !== "fidelix");
  $("#peerGrid").innerHTML = peers.map(company => `<article class="company-card peer-card ${state.filter !== "all" && state.filter !== company.country ? "hidden-card" : ""}" data-country="${company.country}">
    ${identity(company)}
    <span class="role-tag">${esc(company.role)}</span>
    <p class="focus">${esc(company.focus)}</p>
    <div class="peer-primary"><label>${esc(company.metrics.period)} ${esc(company.metrics.periodType)}</label><strong>${esc(company.metrics.revenueDisplay)}</strong></div>
    <div class="peer-change ${company.metrics.revenueYoY >= 0 ? "positive-text" : "negative-text"}">${company.metrics.revenueYoY == null ? "YoY \u2014" : `YoY ${company.metrics.revenueYoY >= 0 ? "+" : ""}${Number(company.metrics.revenueYoY).toFixed(1)}%`}</div>
    <div class="peer-footer"><span>${esc(freshness(company.updatedAt))}</span><a class="verify" href="${esc(company.sourceUrl)}" target="_blank" rel="noreferrer">\uc6d0\ubb38 \u2197</a></div>
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
    return `<rect class="revenue-bar" x="${x(index).toFixed(1)}" y="${barY.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}" rx="1.8" fill="${color}" data-period="${item.period}" data-value="${values[index].toFixed(1)}" tabindex="0" role="graphics-symbol" aria-label="${item.period} \uc6d4\ub9e4\ucd9c NT$ ${values[index].toFixed(1)}\uc5b5"><title>${item.period} \u00b7 NT$ ${values[index].toFixed(1)}\uc5b5</title></rect>`;
  }).join("");
  const latest = history[history.length - 1];
  const latestValue = values[values.length - 1];
  const low = Math.min(...values), high = Math.max(...values);
  return `<article class="trend-card">
    <div class="trend-head">
      <div><span class="trend-company">${esc(company.name)}</span><small>${esc(company.market)} \u00b7 ${esc(company.ticker)}</small></div>
      <div class="trend-latest"><strong>NT$ ${latestValue.toFixed(1)}\uc5b5</strong><span class="${latest.yoy >= 0 ? "positive-text" : "negative-text"}">YoY ${latest.yoy >= 0 ? "+" : ""}${Number(latest.yoy).toFixed(1)}%</span></div>
    </div>
    <svg class="monthly-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(company.name)} \ucd5c\uadfc ${history.length}\uac1c\uc6d4 \uc6d4\ub9e4\ucd9c \uadf8\ub798\ud504">
      ${grid}${bars}${labels}
      <g class="chart-tooltip" aria-hidden="true"><rect x="-58" y="-29" width="116" height="23" rx="5"></rect><text x="0" y="-14" text-anchor="middle"></text></g>
    </svg>
    <div class="trend-foot"><span>${history[0].period}\u2013${latest.period}</span><span>3\ub144 \ubc94\uc704 ${low.toFixed(1)}\u2013${high.toFixed(1)}\uc5b5</span></div>
  </article>`;
}

function renderMonthlyCharts(companies) {
  const colors = { winbond: "#0d6b4d", nanya: "#b87419", macronix: "#2e7a8f" };
  const html = ["winbond", "nanya", "macronix"].map(id => {
    const company = companies.find(item => item.id === id);
    return company ? chartMarkup(company, colors[id]) : "";
  }).filter(Boolean).join("");
  $("#monthlyChartGrid").innerHTML = html || `<div class="chart-empty">\uc6d4\ub9e4\ucd9c \uc774\ub825\uc744 \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4. \ub2e4\uc74c \uac31\uc2e0 \ud6c4 \ud45c\uc2dc\ub429\ub2c8\ub2e4.</div>`;
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
      label.textContent = `${bar.dataset.period} \u00b7 NT$ ${bar.dataset.value}\uc5b5`;
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
  if (value === null || value === undefined) return "\u2014";
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
  const dots = history.map((item,index) => `<circle cx="${x(index).toFixed(1)}" cy="${y(Number(item.average)).toFixed(1)}" r="3.2" fill="#fff" stroke="${color}" stroke-width="2"><title>${item.date} \u00b7 ${spotNumber(item.average)} \u00b7 ${item.change == null ? "\u2014" : `${Number(item.change).toFixed(2)}%`}</title></circle>`).join("");
  const polyline = history.length > 1 ? `<polyline points="${points}" class="spot-line" style="stroke:${color}"></polyline>` : "";
  return `<svg class="spot-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(product.name)} \ud604\ubb3c\uac00 \ucd94\uc774">
    ${grid}${polyline}${dots}${labels}
  </svg>`;
}

function renderSpotPrices(payload) {
  const container = $("#spotPriceGrid");
  if (!container) return;
  const products = payload?.products || [];
  if (!products.length) {
    container.innerHTML = `<div class="chart-empty">DRAMeXchange \ud604\ubb3c\uac00 \ub370\uc774\ud130\ub97c \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</div>`;
    return;
  }
  container.innerHTML = products.map(product => {
    const history = [...(product.history || [])].filter(item => item.average != null).sort((a,b) => String(a.date).localeCompare(String(b.date)));
    const latest = product.latest || history[history.length - 1] || {};
    const change = latest.change == null ? "\u2014" : `${Number(latest.change) >= 0 ? "+" : ""}${Number(latest.change).toFixed(2)}%`;
    const tone = Number(latest.change) >= 0 ? "positive-text" : "negative-text";
    return `<article class="spot-card">
      <div class="spot-head">
        <div><span>${esc(product.name)}</span><small>${esc(product.label)}</small></div>
        <a href="${esc(payload.sourceUrl || "https://www.dramexchange.com/")}" target="_blank" rel="noreferrer">${esc(payload.sourceLabel || "DRAMeXchange")} \u2197</a>
      </div>
      <div class="spot-kpis">
        <div><label>Session Average</label><strong>${esc(spotNumber(latest.average))}</strong></div>
        <div><label>Session Change</label><strong class="${tone}">${esc(change)}</strong></div>
        <div><label>\ucd5c\uadfc \uae30\uc900</label><strong>${esc(latest.date || "\u2014")}</strong></div>
      </div>
      ${spotChartMarkup(product)}
      <div class="spot-foot">
        <span>${history.length ? `${history[0].date}\u2013${history[history.length-1].date}` : "\uc774\ub825 \uc218\uc9d1 \uc804"}</span>
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
  if (value === null || value === undefined) return "\u2014";
  const amount = Number(value) / 100000;
  return `${amount.toLocaleString("ko-KR", {minimumFractionDigits: amount < 10 ? 1 : 0, maximumFractionDigits: 1})}\uc5b5\uc6d0`;
}

function tradeUsd(value) {
  if (value === null || value === undefined) return "\u2014";
  return `$${(Number(value) / 1000000).toLocaleString("ko-KR", {maximumFractionDigits: 1})}M`;
}

function tradeUnit(value) {
  if (value === null || value === undefined) return "\u2014";
  return `$${Number(value).toLocaleString("ko-KR", {maximumFractionDigits: 0})}`;
}

function signedPercent(value) {
  if (value === null || value === undefined) return "\u2014";
  return `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(1)}%`;
}

function percentTone(value) {
  return Number(value) >= 0 ? "positive-text" : "negative-text";
}

function tradeMonthLabel(period) {
  const [year = "", month = ""] = String(period || "").split("-");
  return year && month ? `${year.slice(2)}.${month}` : "\u2014";
}

function tradeQuarterLabel(period) {
  period = String(period || "");
  return period.length >= 6 ? `${period.slice(2, 4)}Q${period.slice(-1)}` : period || "\u2014";
}

function latestWith(rows, key) {
  return [...rows].reverse().find(item => item?.[key] !== null && item?.[key] !== undefined) || rows[rows.length - 1] || {};
}

function jejuTradeMonthlyMarkup(payload) {
  const monthly = normalizeTradeRows(payload?.monthly, payload?.monthlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period))).slice(-24);
  const quarterly = normalizeTradeRows(payload?.quarterly, payload?.quarterlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period)));
  if (monthly.length < 2) return `<div class="chart-empty">\uc81c\uc8fc\ubc18\ub3c4\uccb4 \uc6d4\ubcc4 \uc218\ucd9c\uc785 \ub370\uc774\ud130\ub97c \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</div>`;

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
    const title = `${item.period} \u00b7 \uc218\ucd9c\uc561 ${tradeEok(item.exportKrwThousand)} (${tradeUsd(item.exportUsd)}) \u00b7 \ub2e8\uac00 ${tradeUnit(item.unitUsd)} \u00b7 YoY ${signedPercent(item.exportYoY)} \u00b7 MoM ${signedPercent(item.exportMoM)}`;
    const hot = Number(item.exportYoY) >= 100 ? " hot" : "";
    return `<rect class="trade-bar export${hot}" x="${barX(index).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(1, baseline-y).toFixed(1)}" rx="1.5"><title>${esc(title)}</title></rect>`;
  }).join("");
  const unitPoints = monthly.map((item,index) => `${x(index).toFixed(1)},${unitY(Number(item.unitUsd)).toFixed(1)}`).join(" ");
  const unitDots = monthly.map((item,index) => index % 3 === 0 || index === monthly.length - 1 ? `<circle cx="${x(index).toFixed(1)}" cy="${unitY(Number(item.unitUsd)).toFixed(1)}" r="2.2" class="trade-dot unit"><title>${esc(`${item.period} \u00b7 \ub2e8\uac00 ${tradeUnit(item.unitUsd)} \u00b7 \ub2e8\uac00 MoM ${signedPercent(item.unitMoM)}`)}</title></circle>` : "").join("");

  return `<article class="trade-card">
    <div class="trade-card-head">
      <div><span>\uc6d4\ubcc4 \uc218\ucd9c\uc785 \ub370\uc774\ud130</span><small>${esc(payload?.basis || "\uc81c\uc8fc\ubc18\ub3c4\uccb4 \uc218\ucd9c\uc785 \ub370\uc774\ud130")}</small></div>
      <strong>${tradeMonthLabel(latest.period)} ${latest.period === "2026-07" ? "(20D)" : ""}</strong>
    </div>
    <div class="trade-kpis">
      <div><label>\ucd5c\uadfc \uc6d4 \uc218\ucd9c\uc561</label><strong>${tradeEok(latest.exportKrwThousand)}</strong><span class="${percentTone(latest.exportYoY)}">YoY ${signedPercent(latest.exportYoY)}</span></div>
      <div><label>\uc6d4\uac04 \uc99d\uac10</label><strong class="${percentTone(latest.exportMoM)}">${signedPercent(latest.exportMoM)}</strong><span>\uc218\ucd9c\uae08\uc561 MoM</span></div>
      <div><label>\ub2e8\uac00</label><strong>${tradeUnit(latest.unitUsd)}</strong><span class="${percentTone(latest.unitMoM)}">MoM ${signedPercent(latest.unitMoM)}</span></div>
      <div><label>\ucd5c\uadfc \ubd84\uae30\ud569</label><strong>${tradeEok(latestQuarter.exportKrwThousand)}</strong><span class="${percentTone(latestQuarter.exportQoQ)}">QoQ ${signedPercent(latestQuarter.exportQoQ)}</span></div>
    </div>
    <div class="trade-legend"><span><i class="trade-swatch export"></i>\uc218\ucd9c\uc561</span><span><i class="trade-swatch hot"></i>YoY +100% \uc774\uc0c1</span><span><i class="trade-line unit"></i>\ub2e8\uac00</span></div>
    <svg class="trade-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="\uc81c\uc8fc\ubc18\ub3c4\uccb4 \uc6d4\ubcc4 \uc218\ucd9c\uc561\uacfc \ub2e8\uac00 \ucd94\uc774">
      ${grid}${rightLabels}${bars}<polyline points="${unitPoints}" class="trade-unit-line"></polyline>${unitDots}${labels}
    </svg>
    <div class="trade-foot"><span>${tradeMonthLabel(monthly[0].period)}\u2013${tradeMonthLabel(latest.period)}</span><span>${esc(payload?.note || "")}</span></div>
  </article>`;
}

function jejuTradeQuarterMarkup(payload) {
  const quarterly = normalizeTradeRows(payload?.quarterly, payload?.quarterlyColumns).sort((a,b) => String(a.period).localeCompare(String(b.period))).slice(-12);
  if (quarterly.length < 2) return `<div class="chart-empty">\uc81c\uc8fc\ubc18\ub3c4\uccb4 \ubd84\uae30 \uc218\ucd9c\uc785 \ub370\uc774\ud130\ub97c \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</div>`;

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
    [["revenueKrwThousand", "revenue", -0.58, "\ub9e4\ucd9c\uc561"], ["exportKrwThousand", "export", 0.58, "\uc218\ucd9c\uc561"]].forEach(([key, cls, offset, label]) => {
      if (item[key] === null || item[key] === undefined) return;
      const value = Number(item[key]) / 100000;
      const y = moneyY(value);
      const qoq = key === "exportKrwThousand" ? ` \u00b7 QoQ ${signedPercent(item.exportQoQ)} \u00b7 YoY ${signedPercent(item.exportYoY)}` : "";
      rendered.push(`<rect class="trade-bar ${cls}" x="${(x(index) + offset * barWidth - barWidth / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(1, baseline-y).toFixed(1)}" rx="1.5"><title>${esc(`${item.period} \u00b7 ${label} ${tradeEok(item[key])}${qoq}`)}</title></rect>`);
    });
    return rendered.join("");
  }).join("");
  const opmPoints = quarterly.map((item,index) => item.opm == null ? null : `${x(index).toFixed(1)},${opmY(Number(item.opm)).toFixed(1)}`).filter(Boolean).join(" ");
  const opmDots = quarterly.map((item,index) => item.opm == null ? "" : `<circle cx="${x(index).toFixed(1)}" cy="${opmY(Number(item.opm)).toFixed(1)}" r="2.7" class="trade-dot opm"><title>${esc(`${item.period} \u00b7 OPM ${signedPercent(item.opm)}`)}</title></circle>`).join("");
  const labels = quarterly.map((item,index) => index % 4 === 0 || index === quarterly.length - 1 ? `<text x="${x(index)}" y="${height-12}" text-anchor="middle" class="chart-xlabel">${tradeQuarterLabel(item.period)}</text>` : "").join("");

  return `<article class="trade-card">
    <div class="trade-card-head">
      <div><span>\ubd84\uae30\ud569 + \ub9e4\ucd9c\uc561 + OPM</span><small>\uc218\ucd9c\uc561\uacfc \uc81c\uc8fc\ubc18\ub3c4\uccb4 \ubd84\uae30 \ub9e4\ucd9c\uc561\uc744 \uac19\uc740 \ucd95\uc73c\ub85c \ube44\uad50</small></div>
      <strong>${tradeQuarterLabel(latestExport.period)} ${latestExport.period === "2026Q3" ? "(20D)" : ""}</strong>
    </div>
    <div class="trade-kpis">
      <div><label>\ucd5c\uadfc \uc218\ucd9c\uc561</label><strong>${tradeEok(latestExport.exportKrwThousand)}</strong><span class="${percentTone(latestExport.exportYoY)}">YoY ${signedPercent(latestExport.exportYoY)}</span></div>
      <div><label>\uc218\ucd9c\uc561 QoQ</label><strong class="${percentTone(latestExport.exportQoQ)}">${signedPercent(latestExport.exportQoQ)}</strong><span>${tradeQuarterLabel(latestExport.period)}</span></div>
      <div><label>\ucd5c\uadfc \ub9e4\ucd9c\uc561</label><strong>${tradeEok(latestRevenue.revenueKrwThousand)}</strong><span>${tradeQuarterLabel(latestRevenue.period)} \u00b7 \uc218\ucd9c\ube44\uc911 ${signedPercent(latestRevenue.exportToRevenuePct).replace("+", "")}</span></div>
      <div><label>OPM</label><strong>${signedPercent(latestOpm.opm).replace("+", "")}</strong><span>${tradeQuarterLabel(latestOpm.period)}</span></div>
    </div>
    <div class="trade-legend"><span><i class="trade-swatch revenue"></i>\ub9e4\ucd9c\uc561</span><span><i class="trade-swatch export"></i>\uc218\ucd9c\uc561</span><span><i class="trade-line opm"></i>OPM</span></div>
    <svg class="trade-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="\uc81c\uc8fc\ubc18\ub3c4\uccb4 \ubd84\uae30 \ub9e4\ucd9c\uc561 \uc218\ucd9c\uc561 OPM \uadf8\ub798\ud504">
      ${grid}${rightLabels}${bars}${opmPoints ? `<polyline points="${opmPoints}" class="trade-opm-line"></polyline>${opmDots}` : ""}${labels}
    </svg>
    <div class="trade-foot"><span>${tradeQuarterLabel(quarterly[0].period)}\u2013${tradeQuarterLabel(latestExport.period)}</span><span>\ub2e8\uc704: \uc5b5\uc6d0, %</span></div>
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
  if (value === null || value === undefined) return "\u2014";
  const amount = Number(value) / 100;
  const prefix = currency === "KRW" ? "" : currency === "TWD" ? "NT$ " : "CNY ";
  const suffix = currency === "KRW" ? "\uc5b5\uc6d0" : "\uc5b5";
  return `${prefix}${amount.toLocaleString("ko-KR", {maximumFractionDigits: 1})}${suffix}`;
}

function quarterRangeValue(range, currency) {
  if (!Array.isArray(range) || range.length < 2) return null;
  return `${quarterValue(range[0], currency)}~${quarterValue(range[1], currency)}`;
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
    {key:"revenue", label:"\ub9e4\ucd9c", color:"#a9bbb3"},
    {key:"operatingIncome", label:"\uc601\uc5c5\uc774\uc775", color:"#2e7a8f"},
    {key:"netIncome", label:"\uc21c\uc774\uc775", color:"#c69b51"}
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
  const hits = history.map((item,index) => `<rect class="quarter-hit" x="${(pad.left+index*slot).toFixed(1)}" y="${pad.top}" width="${slot.toFixed(1)}" height="${plotHeight}" fill="transparent" tabindex="0" data-index="${index}" aria-label="${item.period} \uc2e4\uc801${item.isPreliminary ? " \uc608\ube44" : ""}"></rect>`).join("");
  const latest = history[history.length-1];
  const latestLabel = `${esc(latest.period)}${latest.isPreliminary ? " \uc608\ube44" : ""}`;
  const currencyLabel = latest.currency === "KRW" ? "KRW \uc5b5\uc6d0" : latest.currency === "TWD" ? "NT$ \uc5b5" : "CNY \uc5b5";
  return `<article class="quarter-card">
    <div class="quarter-head"><div><span>${esc(company.name)}</span><small>${esc(company.market)} \u00b7 ${esc(company.ticker)} \u00b7 ${currencyLabel}</small></div><strong>${latestLabel}</strong></div>
    <div class="quarter-legend">
      ${barSeries.map(series => `<span><i style="background:${series.color}"></i>${series.label}</span>`).join("")}
      <span><i class="dash op"></i>\uc601\uc5c5\uc774\uc775\ub960</span><span><i class="dash net"></i>\uc21c\uc774\uc775\ub960</span>
    </div>
    <div class="quarter-chart-wrap">
      <svg class="quarter-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(company.name)} \ucd5c\uadfc 12\uac1c \ubd84\uae30 \uc2e4\uc801\uacfc \uc774\uc775\ub960">
        ${leftGrid}<line x1="${pad.left}" y1="${zeroY}" x2="${width-pad.right}" y2="${zeroY}" class="zero-line"/>
        ${bars}
        ${opPoints ? `<polyline points="${opPoints}" class="margin-line op"></polyline>${lineDots("operatingMargin","#0d6b4d")}` : ""}
        ${netPoints ? `<polyline points="${netPoints}" class="margin-line net"></polyline>${lineDots("netMargin","#b24c44")}` : ""}
        ${rightLabels}${xLabels}${hits}
      </svg>
      <div class="quarter-tooltip"></div>
    </div>
    <div class="quarter-source"><span>${history[0].period}\u2013${latest.period}</span><span>${esc(latest.source || "\uacf5\uc2dc")}${latest.isPreliminary ? " \u00b7 \uc911\uac04\uac12" : ""}</span></div>
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
      const revenueRange = quarterRangeValue(item.revenueRange, item.currency);
      const netIncomeRange = quarterRangeValue(item.netIncomeRange, item.currency);
      const preliminaryLines = item.isPreliminary ? `${revenueRange ? `<span>\uc608\ube44 \ub9e4\ucd9c \ubc94\uc704 ${esc(revenueRange)}</span>` : ""}${netIncomeRange ? `<span>\uc608\ube44 \uc21c\uc774\uc775 \ubc94\uc704 ${esc(netIncomeRange)}</span>` : ""}` : "";
      tooltip.innerHTML = `<strong>${esc(item.period)}${item.isPreliminary ? " \uc608\ube44" : ""}</strong><div><span>\ub9e4\ucd9c ${quarterValue(item.revenue,item.currency)}</span><span>\uc601\uc5c5\uc774\uc775 ${quarterValue(item.operatingIncome,item.currency)}</span><span>\uc21c\uc774\uc775 ${quarterValue(item.netIncome,item.currency)}</span><span>OPM ${item.operatingMargin == null ? "\u2014" : `${Number(item.operatingMargin).toFixed(1)}%`} \u00b7 NPM ${item.netMargin == null ? "\u2014" : `${Number(item.netMargin).toFixed(1)}%`}</span>${preliminaryLines}</div>`;
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
  $("#quarterlyChartGrid").innerHTML = html || `<div class="chart-empty">\ubd84\uae30 \uc2e4\uc801 \uc774\ub825\uc744 \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</div>`;
  bindQuarterTooltips(ordered.filter(company => (company.quarterlyHistory || []).length >= 2));
}

function orderDisplay(value, unit = "MW") {
  if (value === null || value === undefined || value === "") return "\u2014";
  const formatted = Number(value).toLocaleString("ko-KR", {maximumFractionDigits: unit === "%" ? 0 : 1});
  return unit === "%" ? `${formatted}%` : `${formatted} ${unit}`;
}

function renderChinaOrders(payload) {
  const container = $("#chinaOrderGrid");
  if (!container) return;
  const companies = payload?.companies || [];
  if (!companies.length) {
    container.innerHTML = `<div class="chart-empty">\uc911\uad6d IDC \uc2e0\uaddc\uc218\uc8fc \ub370\uc774\ud130\ub97c \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</div>`;
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
      const tooltip = `${item.period} \u00b7 ${orderDisplay(item.value, item.unit)} \u00b7 ${item.basis || item.category || ""}`;
      return `<div class="order-row" title="${esc(tooltip)}">
        <span class="order-period">${esc(item.period)}</span>
        <div class="order-track"><i style="width:${width.toFixed(1)}%"></i></div>
        <span class="order-value">${esc(orderDisplay(item.value, item.unit))}</span>
        <small>${esc(item.category || item.basis || "")}</small>
      </div>`;
    }).join("");
    const backlogItems = backlog.map(item => `<div class="backlog-chip" title="${esc(item.basis || "")}">
      <span>${esc(item.label)}${item.derived ? " \u00b7 \uacc4\uc0b0\uac12" : ""}</span>
      <strong>${esc(orderDisplay(item.value, item.unit))}</strong>
    </div>`).join("");
    return `<article class="china-order-card">
      <div class="china-order-head">
        <div><span class="china-company">${esc(company.name)}</span><small>${esc(company.note || "")}</small></div>
        <a href="${esc(company.sourceUrl)}" target="_blank" rel="noreferrer">${esc(company.sourceLabel || "\uacf5\uc2dd IR")} \u2197</a>
      </div>
      <div class="order-kpis">
        <div><label>\ucd5c\uadfc \uc2e0\uaddc\uc218\uc8fc</label><strong>${esc(orderDisplay(latest.value, latest.unit))}</strong><span>${esc(latest.label || "\ucd5c\uadfc")}</span></div>
        <div><label>\uc5c5\ub370\uc774\ud2b8</label><strong>${esc(fmtDate(company.updatedAt))}</strong><span>${esc(freshness(company.updatedAt))}</span></div>
        <div><label>\uae30\uc900</label><strong>${esc(latest.unit || "MW")}</strong><span>${esc(latest.basis || "\uacf5\uc2dd IR")}</span></div>
      </div>
      <div class="order-bars">${bars || `<p class="order-empty">\uc2e0\uaddc\uc218\uc8fc \ub9c9\ub300 \ub370\uc774\ud130\ub97c \uc218\uc9d1 \uc911\uc785\ub2c8\ub2e4.</p>`}</div>
      <div class="backlog-title">\ubc31\ub85c\uadf8\u00b7\ud655\uc57d/\ud65c\uc6a9 \uc6a9\ub7c9</div>
      <div class="backlog-grid">${backlogItems || `<div class="backlog-chip"><span>\uc6d0\ubb38 \ud655\uc778 \ub300\uae30</span><strong>\u2014</strong></div>`}</div>
    </article>`;
  }).join("");
}

function renderCalendar(events) {
  const today = new Date();
  $("#timeline").innerHTML = [...events].sort((a,b) => a.date.localeCompare(b.date)).map(event => {
    const days = Math.ceil((new Date(event.date) - today) / 86400000);
    const dayLabel = days < 0 ? "\uc644\ub8cc" : days === 0 ? "D-day" : `D-${days}`;
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
    $("#feedList").innerHTML = `<div class="feed-item"><span>\ucd5c\uadfc \uacf5\uc2dc\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.</span></div>`;
    return;
  }
  const dateKey = item => String(item.date || "").replace(/\D/g, "").padEnd(14, "0");
  const newestFirst = [...items].sort((a,b) => dateKey(b).localeCompare(dateKey(a)));
  $("#feedList").innerHTML = newestFirst.slice(0, 12).map(item => `<a class="feed-item" href="${esc(item.url)}" target="_blank" rel="noreferrer">
    <span class="feed-date">${esc(fmtDate(item.date))}</span>
    <span class="feed-company">${esc(item.company)}</span>
    <span class="feed-title">${esc(item.title)}</span>
    <span class="feed-source">${esc(item.source)}</span>
    <span class="feed-arrow">\u2197</span>
  </a>`).join("");
}

function renderSources(sources, system) {
  $("#sourceGrid").innerHTML = sources.map(source => `<a class="source-card" href="${esc(source.url)}" target="_blank" rel="noreferrer">
    <div class="source-head"><strong>${esc(source.name)}</strong><span class="status-pill ${esc(source.status)}">${esc(source.status)}</span></div>
    <p>${esc(source.message)}</p>
    <small>${source.checkedAt ? fmtUpdated(source.checkedAt) : "\uc5f0\uacb0 \ub300\uae30"}</small>
  </a>`).join("");
  if (system.lastRefreshErrors?.length) showToast(`\uc77c\ubd80 \uc18c\uc2a4 \ud655\uc778 \ud544\uc694: ${system.lastRefreshErrors[0]}`);
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
    showToast(`\ub300\uc2dc\ubcf4\ub4dc\ub97c \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4: ${error.message}`);
  }
}

async function refreshDashboard() {
  if (isStaticDashboard()) {
    showToast("GitHub Actions\uac00 \ub9e4\uc77c 08\uc2dc\uacbd \uc790\ub3d9 \uac31\uc2e0\ud569\ub2c8\ub2e4. GitHub\uc5d0\uc11c \uc218\ub3d9 \uc2e4\ud589\ub3c4 \uac00\ub2a5\ud569\ub2c8\ub2e4.");
    return;
  }
  const button = $("#refreshButton");
  button.classList.add("loading");
  button.disabled = true;
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const result = await response.json();
    showToast(result.message || "\uac31\uc2e0\uc744 \uc2dc\uc791\ud588\uc2b5\ub2c8\ub2e4.");
    let attempts = 0;
    clearInterval(state.polling);
    state.polling = setInterval(async () => {
      attempts += 1;
      await loadDashboard();
      if (!state.data?.system?.refreshing || attempts > 20) {
        clearInterval(state.polling);
        button.classList.remove("loading");
        button.disabled = false;
        showToast("\ucd5c\uc2e0 \ub370\uc774\ud130 \ud655\uc778\uc744 \ub9c8\ucce4\uc2b5\ub2c8\ub2e4.");
      }
    }, 1500);
  } catch (error) {
    button.classList.remove("loading");
    button.disabled = false;
    showToast(`\uac31\uc2e0 \uc2e4\ud328: ${error.message}`);
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

