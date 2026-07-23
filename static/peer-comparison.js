(function () {
  "use strict";

  function findCompany(data, id) {
    return (data.companies || []).find(function (item) { return item.id === id; });
  }

  function rows(company) {
    return (company && company.quarterlyHistory ? company.quarterlyHistory : [])
      .filter(function (item) { return item.revenue != null; })
      .sort(function (a, b) { return String(a.period).localeCompare(String(b.period)); })
      .slice(-12);
  }

  function render(data) {
    var root = document.getElementById("fidelixDosiliconChart");
    if (!root) return;
    var fidelix = findCompany(data, "fidelix");
    var dosilicon = findCompany(data, "dosilicon");
    var fRows = rows(fidelix);
    var dRows = rows(dosilicon);
    var periods = Array.from(new Set(fRows.concat(dRows).map(function (item) { return item.period; }))).sort().slice(-12);

    if (periods.length < 2) {
      root.innerHTML = '<div class="chart-empty">Quarterly comparison data is not available yet.</div>';
      return;
    }

    function itemAt(list, period) { return list.find(function (item) { return item.period === period; }) || {}; }
    function firstValue(list, key) {
      var item = list.find(function (row) { return row[key] != null && Number(row[key]) !== 0; });
      return item ? Math.abs(Number(item[key])) : 1;
    }

    var bases = {
      f: { revenue: firstValue(fRows, "revenue"), operatingIncome: firstValue(fRows, "operatingIncome") },
      d: { revenue: firstValue(dRows, "revenue"), operatingIncome: firstValue(dRows, "operatingIncome") }
    };
    var width = 980, height = 390, left = 54, right = 58, top = 34, bottom = 58;
    var plotWidth = width - left - right, plotHeight = height - top - bottom, slot = plotWidth / periods.length;
    var values = [];
    periods.forEach(function (period) {
      [[itemAt(fRows, period), bases.f], [itemAt(dRows, period), bases.d]].forEach(function (pair) {
        ["revenue", "operatingIncome"].forEach(function (key) {
          if (pair[0][key] != null) values.push(Math.abs(Number(pair[0][key])) / pair[1][key] * 100);
        });
      });
    });
    var maxValue = Math.max.apply(null, [120].concat(values)) * 1.12;
    var x = function (index) { return left + (index + 0.5) * slot; };
    var y = function (value) { return top + (maxValue - value) * plotHeight / maxValue; };
    var marginY = function (value) { return top + (60 - Math.max(-20, Math.min(60, value))) * plotHeight / 80; };
    var baseline = top + plotHeight, barWidth = Math.max(4, slot * 0.16);
    var series = [
      { id: "f", list: fRows, key: "revenue", color: "#0d6b4d", offset: -1.5 },
      { id: "f", list: fRows, key: "operatingIncome", color: "#80b7b0", offset: -0.5 },
      { id: "d", list: dRows, key: "revenue", color: "#b87419", offset: 0.5 },
      { id: "d", list: dRows, key: "operatingIncome", color: "#e3b66a", offset: 1.5 }
    ];
    var bars = periods.map(function (period, index) {
      return series.map(function (s) {
        var item = itemAt(s.list, period);
        if (item[s.key] == null) return "";
        var indexed = Math.abs(Number(item[s.key])) / bases[s.id][s.key] * 100;
        var barY = y(indexed);
        var companyName = s.id === "f" ? "Fidelix" : "Dosilicon";
        var metric = s.key === "revenue" ? "Revenue" : "Operating income";
        return '<rect x="' + (x(index) + s.offset * barWidth - barWidth / 2).toFixed(1) + '" y="' + barY.toFixed(1) + '" width="' + barWidth.toFixed(1) + '" height="' + Math.max(1, baseline - barY).toFixed(1) + '" rx="2" fill="' + s.color + '"><title>' + period + ' / ' + companyName + ' / ' + metric + ' index ' + indexed.toFixed(1) + '</title></rect>';
      }).join("");
    }).join("");

    function line(list, color) {
      var points = periods.map(function (period, index) {
        var item = itemAt(list, period);
        return item.operatingMargin == null ? null : x(index).toFixed(1) + "," + marginY(Number(item.operatingMargin)).toFixed(1);
      }).filter(Boolean).join(" ");
      return points ? '<polyline points="' + points + '" fill="none" stroke="' + color + '" stroke-width="2.5" stroke-dasharray="7 4" />' : "";
    }

    var grid = [0, 0.25, 0.5, 0.75, 1].map(function (ratio) {
      var gy = top + ratio * plotHeight;
      return '<line x1="' + left + '" y1="' + gy + '" x2="' + (width - right) + '" y2="' + gy + '" stroke="#e1e5df"/><text x="' + (left - 7) + '" y="' + (gy + 3) + '" text-anchor="end" class="peer-axis">' + (maxValue * (1 - ratio)).toFixed(0) + '</text>';
    }).join("");
    var labels = periods.map(function (period, index) {
      return '<text x="' + x(index) + '" y="' + (height - 20) + '" text-anchor="middle" class="peer-axis">' + String(period).replace(/^20/, "") + '</text>';
    }).join("");

    root.innerHTML = '<article class="peer-compare-card"><div class="peer-compare-legend"><span><i style="background:#0d6b4d"></i>Fidelix Revenue</span><span><i style="background:#80b7b0"></i>Fidelix Operating income</span><span><i style="background:#b87419"></i>Dosilicon Revenue</span><span><i style="background:#e3b66a"></i>Dosilicon Operating income</span><span><i class="peer-dash f"></i>Fidelix OPM</span><span><i class="peer-dash d"></i>Dosilicon OPM</span></div><svg viewBox="0 0 ' + width + ' ' + height + '" role="img" aria-label="Fidelix and Dosilicon financial comparison">' + grid + bars + line(fRows, "#064d38") + line(dRows, "#9a5d0b") + labels + '</svg><p>Bars: first available quarter = 100 index. Dashed lines: operating margin from -20% to 60%.</p></article>';
  }

  async function load() {
    var root = document.getElementById("fidelixDosiliconChart");
    try {
      var response = await fetch(window.DASHBOARD_DATA_URL || "/api/dashboard", { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      render(await response.json());
    } catch (error) {
      if (root) root.innerHTML = '<div class="chart-empty">Unable to load comparison data.</div>';
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
