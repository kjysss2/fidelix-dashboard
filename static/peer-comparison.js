(function () {
  "use strict";

  function company(data, id) {
    return (data.companies || []).find(function (item) {
      return item.id === id;
    });
  }

  function history(item) {
    return (item && item.quarterlyHistory || [])
      .filter(function (row) {
        return row.revenue != null;
      })
      .sort(function (a, b) {
        return String(a.period).localeCompare(String(b.period));
      })
      .slice(-12);
  }

  function at(rows, period) {
    return rows.find(function (row) {
      return row.period === period;
    }) || {};
  }

  function validNumber(value) {
    return value !== null && value !== undefined && value !== "" && isFinite(Number(value));
  }

  function money(value, id) {
    if (value == null) return "-";
    var amount = Number(value) / 100;
    return id === "f"
      ? amount.toLocaleString("ko-KR", {maximumFractionDigits: 1}) + " KRW 100M"
      : amount.toLocaleString("ko-KR", {maximumFractionDigits: 2}) + " CNY 100M";
  }

  function profitMoney(value, id) {
    if (value == null) return "\u2014";
    var amount = Number(value) / 100;
    return id === "f"
      ? amount.toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "\uc5b5\uc6d0"
      : "CNY " + amount.toLocaleString("ko-KR", {minimumFractionDigits: 2, maximumFractionDigits: 2}) + "\uc5b5";
  }

  function pairedValues(leftRows, rightRows, key) {
    return leftRows.reduce(function (pairs, left) {
      var right = at(rightRows, left.period);
      if (validNumber(left[key]) && validNumber(right[key])) {
        pairs.push({
          period: left.period,
          left: Number(left[key]),
          right: Number(right[key])
        });
      }
      return pairs;
    }, []);
  }

  function pearson(pairs) {
    if (pairs.length < 2) return null;

    var leftMean = pairs.reduce(function (sum, pair) {
      return sum + pair.left;
    }, 0) / pairs.length;
    var rightMean = pairs.reduce(function (sum, pair) {
      return sum + pair.right;
    }, 0) / pairs.length;

    var numerator = 0;
    var leftSquares = 0;
    var rightSquares = 0;

    pairs.forEach(function (pair) {
      var leftDelta = pair.left - leftMean;
      var rightDelta = pair.right - rightMean;
      numerator += leftDelta * rightDelta;
      leftSquares += leftDelta * leftDelta;
      rightSquares += rightDelta * rightDelta;
    });

    var denominator = Math.sqrt(leftSquares * rightSquares);
    return denominator ? numerator / denominator : null;
  }

  function correlationLabel(value) {
    if (value == null) return "계산 불가";

    var strength = Math.abs(value);
    var level = strength >= 0.85
      ? "매우 강한"
      : strength >= 0.7
        ? "강한"
        : strength >= 0.4
          ? "중간 수준의"
          : strength >= 0.2
            ? "약한"
            : "매우 약한";
    var direction = value >= 0 ? "양의" : "음의";
    return level + " " + direction + " 상관";
  }

  function correlationTone(value) {
    if (value == null) return "unavailable";
    var strength = Math.abs(value);
    var level = strength >= 0.85
      ? "very-strong"
      : strength >= 0.7
        ? "strong"
        : strength >= 0.4
          ? "moderate"
          : strength >= 0.2
            ? "weak"
            : "very-weak";
    return level + (value < 0 ? " negative" : " positive");
  }

  function correlationMarkup(leftRows, rightRows) {
    var definitions = [
      {key: "revenue", label: "매출액"},
      {key: "operatingIncome", label: "영업이익"},
      {key: "operatingMargin", label: "영업이익률"},
      {key: "netIncome", label: "순이익"}
    ];

    var results = definitions.map(function (definition) {
      var pairs = pairedValues(leftRows, rightRows, definition.key);
      return {
        label: definition.label,
        value: pearson(pairs),
        periods: pairs.map(function (pair) {
          return pair.period;
        })
      };
    });

    var sharedPeriods = results.length
      ? results[0].periods.filter(function (period) {
          return results.every(function (result) {
            return result.periods.indexOf(period) !== -1;
          });
        })
      : [];
    var range = sharedPeriods.length
      ? sharedPeriods[0] + "\u2013" + sharedPeriods[sharedPeriods.length - 1]
      : "\u2014";

    var cards = results.map(function (result) {
      var value = result.value == null ? "\u2014" : result.value.toFixed(3);
      return '<div class="peer-correlation-item ' + correlationTone(result.value) + '">' +
        '<span>' + result.label + '</span>' +
        '<strong>' + value + '</strong>' +
        '<small>n=' + result.periods.length + ' \u00b7 ' + correlationLabel(result.value) + '</small>' +
      '</div>';
    }).join("");

    return '<section class="peer-correlation" aria-label="\ud53c\ub378\ub9ad\uc2a4\uc640 Dosilicon \uc2e4\uc801 \uc0c1\uad00\uacc4\uc218">' +
      '<div class="peer-correlation-head">' +
        '<div><span>PEARSON CORRELATION</span><strong>\uc2e4\uc801 \ub3d9\ud589\uc131</strong></div>' +
        '<p>\uacf5\ud1b5 ' + sharedPeriods.length + '\uac1c \ubd84\uae30 \u00b7 ' + range + '</p>' +
      '</div>' +
      '<div class="peer-correlation-grid">' + cards + '</div>' +
      '<p class="peer-correlation-note">\ub3d9\uc77c \ubd84\uae30\uc758 \uc6d0\uc790\ub8cc\ub97c \ud1b5\ud654 \ubcc0\ud658 \uc5c6\uc774 \ube44\uad50\ud55c \ud53c\uc5b4\uc2a8 \uc0c1\uad00\uacc4\uc218(r) \u00b7 2026Q2 Dosilicon \uc608\ube44\uce58\ub294 \uacf5\ud1b5 \ubd84\uae30\uc5d0\uc11c \uc81c\uc678</p>' +
    '</section>';
  }

  function latestProfitMarkup(leftRows, rightRows) {
    function latest(rows) {
      return rows.filter(function (row) {
        return validNumber(row.netIncome) && validNumber(row.netMargin);
      }).slice(-1)[0] || {};
    }

    function item(row, id, name) {
      var preliminary = row.isPreliminary ? " \uc608\ube44" : "";
      return '<div class="peer-profit-item ' + (id === "d" ? "dosi" : "fidelix") + '">' +
        '<span>' + name + " \u00b7 " + (row.period || "\u2014") + preliminary + '</span>' +
        '<strong>\uc21c\uc774\uc775 ' + profitMoney(row.netIncome, id) + '</strong>' +
        '<small>NPM ' + (validNumber(row.netMargin) ? Number(row.netMargin).toFixed(1) + "%" : "\u2014") + '</small>' +
      '</div>';
    }

    return '<div class="peer-profit-snapshot" aria-label="\uc591\uc0ac \ucd5c\uadfc \uc21c\uc774\uc775\uacfc \uc21c\uc774\uc775\ub960">' +
      item(latest(leftRows), "f", "Fidelix") +
      item(latest(rightRows), "d", "Dosilicon") +
    '</div>';
  }

  function render(data) {
    var root = document.getElementById("fidelixDosiliconChart");
    if (!root) return;

    var fr = history(company(data, "fidelix"));
    var dr = history(company(data, "dosilicon"));
    var periods = Array.from(new Set(fr.concat(dr).map(function (row) {
      return row.period;
    }))).sort().slice(-12);

    if (periods.length < 2) {
      root.innerHTML = '<div class="chart-empty">Quarterly comparison data is not available yet.</div>';
      return;
    }

    var W = 1000;
    var H = 410;
    var L = 68;
    var R = 72;
    var T = 36;
    var B = 62;
    var PW = W - L - R;
    var PH = H - T - B;
    var S = PW / periods.length;

    var fVals = fr.reduce(function (values, row) {
      return values.concat([row.revenue, row.operatingIncome, row.netIncome]
        .filter(function (value) {
          return value != null;
        })
        .map(function (value) {
          return Number(value) / 100;
        }));
    }, []);
    var dVals = dr.reduce(function (values, row) {
      return values.concat([row.revenue, row.operatingIncome, row.netIncome]
        .filter(function (value) {
          return value != null;
        })
        .map(function (value) {
          return Number(value) / 100;
        }));
    }, []);

    function range(values) {
      var low = Math.min.apply(null, [0].concat(values));
      var high = Math.max.apply(null, [1].concat(values));
      return {
        lo: low < 0 ? low * 1.18 : 0,
        hi: high * 1.12
      };
    }

    var F = range(fVals);
    var D = range(dVals);
    var negRatio = Math.max(
      Math.abs(F.lo) / (F.hi - F.lo),
      Math.abs(D.lo) / (D.hi - D.lo)
    );

    if (negRatio > 0) {
      F.lo = -F.hi * negRatio / (1 - negRatio);
      D.lo = -D.hi * negRatio / (1 - negRatio);
    }

    var x = function (index) {
      return L + (index + 0.5) * S;
    };
    var fy = function (value) {
      return T + (F.hi - value) * PH / (F.hi - F.lo);
    };
    var dy = function (value) {
      return T + (D.hi - value) * PH / (D.hi - D.lo);
    };
    var marginValues = fr.concat(dr).reduce(function (values, row) {
      return values.concat([row.operatingMargin, row.netMargin].filter(validNumber).map(Number));
    }, []);
    var marginMin = Math.floor(Math.min.apply(null, [-20].concat(marginValues)) * 1.05 / 10) * 10;
    var marginMax = Math.ceil(Math.max.apply(null, [40].concat(marginValues)) * 1.05 / 10) * 10;
    var my = function (value) {
      var clipped = Math.max(marginMin, Math.min(marginMax, value));
      return T + (marginMax - clipped) * PH / (marginMax - marginMin);
    };
    var zero = fy(0);
    var barWidth = Math.max(4, S * 0.13);

    var bars = periods.map(function (period, index) {
      var f = at(fr, period);
      var d = at(dr, period);
      var output = "";
      [
        [f, "revenue", "#0d6b4d", -2.5, fy, "f", "Revenue"],
        [f, "operatingIncome", "#80b7b0", -1.5, fy, "f", "Operating income"],
        [f, "netIncome", "#4f7f70", -0.5, fy, "f", "Net income"],
        [d, "revenue", "#b87419", 0.5, dy, "d", "Revenue"],
        [d, "operatingIncome", "#e3b66a", 1.5, dy, "d", "Operating income"],
        [d, "netIncome", "#c58f38", 2.5, dy, "d", "Net income"]
      ].forEach(function (series) {
        if (series[0][series[1]] == null) return;
        var raw = Number(series[0][series[1]]) / 100;
        var y = series[4](raw);
        var height = Math.max(1, Math.abs(zero - y));
        output += '<rect x="' + (x(index) + series[3] * barWidth - barWidth / 2).toFixed(1) +
          '" y="' + Math.min(zero, y).toFixed(1) +
          '" width="' + barWidth.toFixed(1) +
          '" height="' + height.toFixed(1) +
          '" rx="2" fill="' + series[2] + '"><title>' +
          period + " / " + (series[5] === "f" ? "Fidelix" : "Dosilicon") +
          " / " + series[6] + " / " + money(series[0][series[1]], series[5]) +
          '</title></rect>';
      });
      return output;
    }).join("");

    function line(rows, metric, color, name, label, dashArray) {
      var points = periods.map(function (period, index) {
        var row = at(rows, period);
        return row[metric] == null
          ? null
          : x(index).toFixed(1) + "," + my(Number(row[metric])).toFixed(1);
      }).filter(Boolean).join(" ");
      var dots = periods.map(function (period, index) {
        var row = at(rows, period);
        return row[metric] == null
          ? ""
          : '<circle cx="' + x(index).toFixed(1) +
            '" cy="' + my(Number(row[metric])).toFixed(1) +
            '" r="2.7" fill="#fff" stroke="' + color +
            '" stroke-width="1.8"><title>' + period + " / " + name +
            " " + label + " / " + Number(row[metric]).toFixed(1) +
            '%</title></circle>';
      }).join("");
      return points
        ? '<polyline points="' + points + '" fill="none" stroke="' + color +
          '" stroke-width="2.5"' + (dashArray ? ' stroke-dasharray="' + dashArray + '"' : "") + '/>' + dots
        : "";
    }

    var grid = [0, 0.25, 0.5, 0.75, 1].map(function (ratio) {
      var y = T + ratio * PH;
      var fValue = F.hi - ratio * (F.hi - F.lo);
      var dValue = D.hi - ratio * (D.hi - D.lo);
      return '<line x1="' + L + '" y1="' + y + '" x2="' + (W - R) +
        '" y2="' + y + '" stroke="#e1e5df"/><text x="' + (L - 7) +
        '" y="' + (y + 3) + '" text-anchor="end" class="peer-axis">' +
        fValue.toFixed(0) + '</text><text x="' + (W - R + 7) +
        '" y="' + (y + 3) + '" class="peer-axis">' + dValue.toFixed(1) + '</text>';
    }).join("");
    var labels = periods.map(function (period, index) {
      return '<text x="' + x(index) + '" y="' + (H - 20) +
        '" text-anchor="middle" class="peer-axis">' +
        String(period).replace(/^20/, "") + '</text>';
    }).join("");

    root.innerHTML = '<article class="peer-compare-card">' +
      correlationMarkup(fr, dr) +
      latestProfitMarkup(fr, dr) +
      '<div class="peer-axis-titles"><strong>LEFT - Fidelix (KRW 100M)</strong><strong>RIGHT - Dosilicon (CNY 100M)</strong></div>' +
      '<div class="peer-compare-legend">' +
        '<span><i style="background:#0d6b4d"></i>Fidelix Revenue</span>' +
        '<span><i style="background:#80b7b0"></i>Fidelix Operating income</span>' +
        '<span><i style="background:#4f7f70"></i>Fidelix Net income</span>' +
        '<span><i style="background:#b87419"></i>Dosilicon Revenue</span>' +
        '<span><i style="background:#e3b66a"></i>Dosilicon Operating income</span>' +
        '<span><i style="background:#c58f38"></i>Dosilicon Net income</span>' +
        '<span><i class="peer-line f-opm"></i>Fidelix OPM</span>' +
        '<span><i class="peer-line f-npm"></i>Fidelix NPM</span>' +
        '<span><i class="peer-line d-opm"></i>Dosilicon OPM</span>' +
        '<span><i class="peer-line d-npm"></i>Dosilicon NPM</span>' +
      '</div>' +
      '<svg viewBox="0 0 ' + W + " " + H +
        '" role="img" aria-label="Fidelix left axis and Dosilicon right axis financial comparison">' +
        grid +
        '<line x1="' + L + '" y1="' + zero + '" x2="' + (W - R) +
          '" y2="' + zero + '" stroke="#aab1ad"/>' +
        bars +
        line(fr, "operatingMargin", "#064d38", "Fidelix", "OPM", "7 4") +
        line(fr, "netMargin", "#397c70", "Fidelix", "NPM", "") +
        line(dr, "operatingMargin", "#9a5d0b", "Dosilicon", "OPM", "7 4") +
        line(dr, "netMargin", "#cf8f2f", "Dosilicon", "NPM", "") +
        labels +
      '</svg>' +
      '<p>Money bars use separate company axes. Dashed lines are OPM; solid lines are NPM. Margin scale: ' +
        marginMin.toFixed(0) + "% to " + marginMax.toFixed(0) + '%.</p>' +
    '</article>';
  }

  async function load() {
    var root = document.getElementById("fidelixDosiliconChart");
    try {
      var response = await fetch(window.DASHBOARD_DATA_URL || "/api/dashboard", {cache: "no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      render(await response.json());
    } catch (error) {
      if (root) {
        root.innerHTML = '<div class="chart-empty">Unable to load comparison data.</div>';
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
