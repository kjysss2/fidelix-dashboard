(function () {
  "use strict";
  const esc = (v="") => String(v).replace(/[&<>']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;"}[c]));
  const fmt = (value,currency) => value == null ? "—" : `${currency === "KRW" ? "₩" : "CNY "}${Number(value).toLocaleString("ko-KR",{maximumFractionDigits:1})}`;
  function normalize(history) {
    return [...(history||[])].filter(x=>x.revenue!=null).sort((a,b)=>a.period.localeCompare(b.period)).slice(-12);
  }
  function render(data) {
    const root=document.getElementById("fidelixDosiliconChart"); if(!root) return;
    const f=data.companies?.find(x=>x.id==="fidelix"), d=data.companies?.find(x=>x.id==="dosilicon");
    const fh=normalize(f?.quarterlyHistory), dh=normalize(d?.quarterlyHistory);
    const periods=[...new Set([...fh.map(x=>x.period),...dh.map(x=>x.period)])].sort().slice(-12);
    if(periods.length<2){root.innerHTML='<div class="chart-empty">비교 가능한 분기 실적을 수집 중입니다.</div>';return;}
    const by=(rows,p)=>rows.find(x=>x.period===p)||{};
    const base=(rows,key)=>{const x=rows.find(v=>v[key]!=null&&Number(v[key])!==0);return x?Math.abs(Number(x[key])):1;};
    const fb={revenue:base(fh,"revenue"),operatingIncome:base(fh,"operatingIncome")},db={revenue:base(dh,"revenue"),operatingIncome:base(dh,"operatingIncome")};
    const width=980,height=390,pad={l:54,r:58,t:34,b:58},pw=width-pad.l-pad.r,ph=height-pad.t-pad.b,slot=pw/periods.length;
    const indexed=[]; periods.forEach(p=>{const a=by(fh,p),b=by(dh,p);[[a,fb,"f"],[b,db,"d"]].forEach(([x,z,id])=>["revenue","operatingIncome"].forEach(k=>{if(x[k]!=null)indexed.push(Math.abs(Number(x[k]))/z[k]*100)}))});
    const ymax=Math.max(120,...indexed)*1.12, y=v=>pad.t+(ymax-v)*ph/ymax, my=v=>pad.t+(60-Math.max(-20,Math.min(60,v)))*ph/80, x=i=>pad.l+(i+.5)*slot, zero=pad.t+ph;
    const defs=[{id:"f",key:"revenue",color:"#0d6b4d",off:-1.5},{id:"f",key:"operatingIncome",color:"#80b7b0",off:-.5},{id:"d",key:"revenue",color:"#b87419",off:.5},{id:"d",key:"operatingIncome",color:"#e3b66a",off:1.5}],bw=Math.max(4,slot*.16);
    const bars=periods.map((p,i)=>defs.map(s=>{const rows=s.id==="f"?fh:dh,obj=by(rows,p),b=s.id==="f"?fb:db;if(obj[s.key]==null)return"";const idx=Math.abs(Number(obj[s.key]))/b[s.key]*100,yy=y(idx),cur=s.id==="f"?"KRW":"CNY";return `<rect x="${(x(i)+s.off*bw-bw/2).toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,zero-yy).toFixed(1)}" rx="2" fill="${s.color}"><title>${esc(p)} · ${s.id==="f"?"피델릭스":"Dosilicon"} ${s.key==="revenue"?"매출액":"영업이익"} ${fmt(obj[s.key],cur)} · 지수 ${idx.toFixed(1)}</title></rect>`}).join("")).join("");
    const line=(rows,color)=>{const pts=periods.map((p,i)=>{const o=by(rows,p);if(o.operatingMargin==null)return null;return `${x(i).toFixed(1)},${my(Number(o.operatingMargin)).toFixed(1)}`}).filter(Boolean).join(" ");return pts?`<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2.5" stroke-dasharray="7 4"><title>영업이익률</title></polyline>`:""};
    const grid=[0,.25,.5,.75,1].map(r=>`<line x1="${pad.l}" y1="${pad.t+r*ph}" x2="${width-pad.r}" y2="${pad.t+r*ph}" stroke="#e1e5df"/><text x="${pad.l-7}" y="${pad.t+r*ph+3}" text-anchor="end" class="peer-axis">${(ymax*(1-r)).toFixed(0)}</text>`).join("");
    const labels=periods.map((p,i)=>`<text x="${x(i)}" y="${height-20}" text-anchor="middle" class="peer-axis">${esc(p.replace(/^20/,""))}</text>`).join("");
    root.innerHTML=`<article class="peer-compare-card"><div class="peer-compare-legend"><span><i style="background:#0d6b4d"></i>피델릭스 매출</span><span><i style="background:#80b7b0"></i>피델릭스 영업이익</span><span><i style="background:#b87419"></i>Dosilicon 매출</span><span><i style="background:#e3b66a"></i>Dosilicon 영업이익</span><span><i class="peer-dash f"></i>피델릭스 OPM</span><span><i class="peer-dash d"></i>Dosilicon OPM</span></div><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="피델릭스와 Dosilicon 매출액 영업이익 영업이익률 비교">${grid}${bars}${line(fh,"#064d38")}${line(dh,"#9a5d0b")}${labels}</svg><p>왼쪽 축: 시작 분기=100 지수 · 오른쪽 개념축: 영업이익률 -20~60% · 막대와 선에 마우스를 올리면 원금액을 확인할 수 있습니다.</p></article>`;
  }
  async function load(){try{const url=window.DASHBOARD_DATA_URL||"/api/dashboard",r=await fetch(url,{cache:"no-store"});if(r.ok)render(await r.json());}catch(e){const root=document.getElementById("fidelixDosiliconChart");if(root)root.innerHTML='<div class="chart-empty">비교 데이터를 불러오지 못했습니다.</div>';}}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);else load();
})();
