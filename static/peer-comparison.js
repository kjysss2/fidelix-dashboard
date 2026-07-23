(function () {
  "use strict";
  function company(data,id){return(data.companies||[]).find(function(x){return x.id===id;});}
  function history(c){return(c&&c.quarterlyHistory||[]).filter(function(x){return x.revenue!=null;}).sort(function(a,b){return String(a.period).localeCompare(String(b.period));}).slice(-12);}
  function at(rows,p){return rows.find(function(x){return x.period===p;})||{};}
  function money(value,id){if(value==null)return"-";var n=Number(value)/100;return id==="f"?n.toLocaleString("ko-KR",{maximumFractionDigits:1})+" KRW 100M":n.toLocaleString("ko-KR",{maximumFractionDigits:2})+" CNY 100M";}
  function render(data){
    var root=document.getElementById("fidelixDosiliconChart");if(!root)return;
    var fr=history(company(data,"fidelix")),dr=history(company(data,"dosilicon"));
    var periods=Array.from(new Set(fr.concat(dr).map(function(x){return x.period;}))).sort().slice(-12);
    if(periods.length<2){root.innerHTML='<div class="chart-empty">Quarterly comparison data is not available yet.</div>';return;}
    var W=1000,H=410,L=68,R=72,T=36,B=62,PW=W-L-R,PH=H-T-B,S=PW/periods.length;
    var fVals=fr.reduce(function(a,x){return a.concat([x.revenue,x.operatingIncome].filter(function(v){return v!=null;}).map(function(v){return Number(v)/100;}));},[]);
    var dVals=dr.reduce(function(a,x){return a.concat([x.revenue,x.operatingIncome].filter(function(v){return v!=null;}).map(function(v){return Number(v)/100;}));},[]);
    function range(vals){var lo=Math.min.apply(null,[0].concat(vals)),hi=Math.max.apply(null,[1].concat(vals));return{lo:lo<0?lo*1.18:0,hi:hi*1.12};}
    var F=range(fVals),D=range(dVals);
    var negRatio=Math.max(Math.abs(F.lo)/(F.hi-F.lo),Math.abs(D.lo)/(D.hi-D.lo));
    if(negRatio>0){F.lo=-F.hi*negRatio/(1-negRatio);D.lo=-D.hi*negRatio/(1-negRatio);}
    var x=function(i){return L+(i+.5)*S;},fy=function(v){return T+(F.hi-v)*PH/(F.hi-F.lo);},dy=function(v){return T+(D.hi-v)*PH/(D.hi-D.lo);};
    var opmMin=-20,opmMax=40,oy=function(v){return T+(opmMax-Math.max(opmMin,Math.min(opmMax,v)))*PH/(opmMax-opmMin);};
    var zero=fy(0),bw=Math.max(5,S*.18);
    var bars=periods.map(function(p,i){var f=at(fr,p),d=at(dr,p),out="";
      [[f,"revenue","#0d6b4d",-1.5,fy,"f","Revenue"],[f,"operatingIncome","#80b7b0",-.5,fy,"f","Operating income"],[d,"revenue","#b87419",.5,dy,"d","Revenue"],[d,"operatingIncome","#e3b66a",1.5,dy,"d","Operating income"]].forEach(function(s){if(s[0][s[1]]==null)return;var raw=Number(s[0][s[1]])/100,yy=s[4](raw),h=Math.max(1,Math.abs(zero-yy));out+='<rect x="'+(x(i)+s[3]*bw-bw/2).toFixed(1)+'" y="'+Math.min(zero,yy).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" rx="2" fill="'+s[2]+'"><title>'+p+' / '+(s[5]==="f"?"Fidelix":"Dosilicon")+' / '+s[6]+' / '+money(s[0][s[1]],s[5])+'</title></rect>';});return out;
    }).join("");
    function line(rows,color,name){var pts=periods.map(function(p,i){var z=at(rows,p);return z.operatingMargin==null?null:x(i).toFixed(1)+","+oy(Number(z.operatingMargin)).toFixed(1);}).filter(Boolean).join(" ");var dots=periods.map(function(p,i){var z=at(rows,p);return z.operatingMargin==null?"":'<circle cx="'+x(i).toFixed(1)+'" cy="'+oy(Number(z.operatingMargin)).toFixed(1)+'" r="2.7" fill="#fff" stroke="'+color+'" stroke-width="1.8"><title>'+p+' / '+name+' OPM / '+Number(z.operatingMargin).toFixed(1)+'%</title></circle>';}).join("");return pts?'<polyline points="'+pts+'" fill="none" stroke="'+color+'" stroke-width="2.5" stroke-dasharray="7 4"/>'+dots:"";}
    var grid=[0,.25,.5,.75,1].map(function(q){var gy=T+q*PH,fv=F.hi-q*(F.hi-F.lo),dv=D.hi-q*(D.hi-D.lo);return'<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" stroke="#e1e5df"/><text x="'+(L-7)+'" y="'+(gy+3)+'" text-anchor="end" class="peer-axis">'+fv.toFixed(0)+'</text><text x="'+(W-R+7)+'" y="'+(gy+3)+'" class="peer-axis">'+dv.toFixed(1)+'</text>';}).join("");
    var labels=periods.map(function(p,i){return'<text x="'+x(i)+'" y="'+(H-20)+'" text-anchor="middle" class="peer-axis">'+String(p).replace(/^20/,"")+'</text>';}).join("");
    root.innerHTML='<article class="peer-compare-card"><div class="peer-axis-titles"><strong>LEFT - Fidelix (KRW 100M)</strong><strong>RIGHT - Dosilicon (CNY 100M)</strong></div><div class="peer-compare-legend"><span><i style="background:#0d6b4d"></i>Fidelix Revenue</span><span><i style="background:#80b7b0"></i>Fidelix Operating income</span><span><i style="background:#b87419"></i>Dosilicon Revenue</span><span><i style="background:#e3b66a"></i>Dosilicon Operating income</span><span><i class="peer-dash f"></i>Fidelix OPM</span><span><i class="peer-dash d"></i>Dosilicon OPM</span></div><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Fidelix left axis and Dosilicon right axis financial comparison">'+grid+'<line x1="'+L+'" y1="'+zero+'" x2="'+(W-R)+'" y2="'+zero+'" stroke="#aab1ad"/>'+bars+line(fr,"#064d38","Fidelix")+line(dr,"#9a5d0b","Dosilicon")+labels+'</svg><p>Money bars use separate company axes. Dashed OPM lines share a fixed -20% to 40% scale.</p></article>';
  }
  async function load(){var root=document.getElementById("fidelixDosiliconChart");try{var r=await fetch(window.DASHBOARD_DATA_URL||"/api/dashboard",{cache:"no-store"});if(!r.ok)throw new Error("HTTP "+r.status);render(await r.json());}catch(e){if(root)root.innerHTML='<div class="chart-empty">Unable to load comparison data.</div>';}}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);else load();
})();
