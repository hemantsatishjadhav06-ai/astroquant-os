"""The unified single-page dashboard (served at GET /). Self-contained: inline CSS + JS, no CDN."""

DASHBOARD_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AstroQuant OS — Research Lab</title>
<style>
 :root{
   --bg:#0b1020; --panel:#121a30; --card:#16203a; --line:#26314f;
   --ink:#eaf0ff; --muted:#9aa8c7; --accent:#7c5cff; --accent2:#34d399;
   --edge:#3b82f6; --good:#34d399; --warn:#fbbf24; --bad:#f87171;
 }
 *{box-sizing:border-box}
 body{margin:0;background:radial-gradient(1200px 600px at 50% -200px,#1b2547 0,#0b1020 60%);
   color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
 a{color:var(--accent)}
 .wrap{max-width:1080px;margin:0 auto;padding:22px 18px 80px}
 header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:8px}
 .brand{display:flex;align-items:center;gap:12px}
 .logo{width:42px;height:42px;border-radius:12px;background:conic-gradient(from 210deg,#7c5cff,#34d399,#3b82f6,#7c5cff);
   box-shadow:0 6px 24px rgba(124,92,255,.4)}
 h1{font-size:20px;margin:0;letter-spacing:.2px}
 .tag{color:var(--muted);font-size:12.5px;margin:2px 0 0}
 .pill{font-size:11px;color:#cbd5ff;border:1px solid #2e3a63;border-radius:999px;padding:5px 11px;background:#101831}
 .tabs{display:flex;gap:6px;margin:18px 0 14px;background:#0e1730;border:1px solid #233056;border-radius:14px;padding:6px;flex-wrap:wrap}
 .tab{flex:1;min-width:150px;border:0;background:transparent;color:var(--muted);padding:11px 12px;border-radius:10px;
   font-weight:600;font-size:14px;cursor:pointer;transition:.15s;display:flex;gap:8px;align-items:center;justify-content:center}
 .tab:hover{color:var(--ink)}
 .tab.active{background:#1c2748;color:#fff;box-shadow:inset 0 0 0 1px #34406e}
 .panel{display:none;animation:fade .25s ease}
 .panel.active{display:block}
 @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
 .card{background:var(--card);border:1px solid #233056;border-radius:16px;padding:18px;margin-bottom:16px;box-shadow:0 8px 30px rgba(0,0,0,.25)}
 .controls{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
 label{display:block;font-size:11.5px;color:var(--muted);margin-bottom:5px}
 input,select{background:#0d1530;border:1px solid #2b375d;color:var(--ink);border-radius:10px;padding:9px 11px;font-size:13.5px}
 input:focus,select:focus{outline:2px solid #3a4a82;border-color:#3a4a82}
 .btn{background:linear-gradient(180deg,#8a6cff,#6d4bff);color:#fff;border:0;border-radius:11px;padding:11px 20px;
   font-weight:700;font-size:14px;cursor:pointer;box-shadow:0 6px 18px rgba(109,75,255,.4)}
 .btn:disabled{opacity:.55;cursor:wait}
 .hint{font-size:12px;color:var(--muted);margin-top:10px}
 .flow{font-size:12px;color:#aab6da;letter-spacing:.3px;margin-top:10px}
 .spin{display:none;align-items:center;gap:10px;color:var(--muted);font-size:13px;margin-top:6px}
 .spin.on{display:flex}
 .dot{width:14px;height:14px;border-radius:50%;border:2px solid #4658a0;border-top-color:#8a6cff;animation:rot .8s linear infinite}
 @keyframes rot{to{transform:rotate(360deg)}}
 .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:4px}
 .kpi{background:#0f1830;border:1px solid #233056;border-radius:13px;padding:14px 16px}
 .kpi b{display:block;font-size:23px;line-height:1.1} .kpi span{color:var(--muted);font-size:11.5px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);text-align:left;padding:9px 7px;border-bottom:1px solid #243056}
 td{padding:9px 7px;border-bottom:1px solid #1c2643;font-variant-numeric:tabular-nums}
 .badge{padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap}
 .b-edge{background:rgba(52,211,153,.16);color:#34d399;border:1px solid #2f7a5f}
 .b-cond{background:rgba(251,191,36,.14);color:#fbbf24;border:1px solid #7a6326}
 .b-no{background:rgba(154,168,199,.12);color:#aab6da;border:1px solid #34406e}
 .pos{color:#34d399}.neg{color:#f87171}.muted{color:var(--muted)}
 .bar{height:8px;border-radius:6px;background:#0d1530;overflow:hidden;min-width:60px}
 .bar>span{display:block;height:100%}
 .note{font-size:12.5px;color:#dfe7ff;background:rgba(124,92,255,.10);border:1px solid #34406e;border-radius:12px;padding:12px 14px;margin-top:14px}
 .chart{width:100%;height:auto;background:#0c1430;border:1px solid #233056;border-radius:12px}
 .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
 @media(max-width:760px){.grid2{grid-template-columns:1fr}}
 .stratcard{display:flex;align-items:center;gap:14px;background:#16203a;
   border:1px solid #34406e;border-radius:14px;padding:14px 16px;margin-bottom:14px}
 .gate{font-size:12px;font-weight:700;color:#0b1020;background:#fbbf24;border-radius:8px;padding:5px 10px}
 footer{color:#6f7ba5;font-size:12px;text-align:center;margin-top:26px}
 h3{font-size:13.5px;margin:2px 0 12px;color:#cdd7f5;text-transform:uppercase;letter-spacing:.5px}
</style></head><body><div class="wrap">
 <header>
   <div class="brand"><div class="logo"></div>
     <div><h1>AstroQuant&nbsp;OS</h1><div class="tag">Scientifically testing astro · Gann · technical signals in Indian markets</div></div>
   </div>
   <span class="pill">● research only — no live trading</span>
 </header>

 <div class="tabs">
   <button class="tab active" data-t="lab" onclick="tab('lab')">🔭 Discovery Lab</button>
   <button class="tab" data-t="genome" onclick="tab('genome')">🧬 Market Genome</button>
   <button class="tab" data-t="fund" onclick="tab('fund')">🤖 Evolving Fund</button>
   <button class="tab" data-t="stock" onclick="tab('stock')">📈 Stock Deep Dive</button>
   <button class="tab" data-t="options" onclick="tab('options')">⚡ Options Greeks</button>
 </div>

 <!-- ===================== LAB ===================== -->
 <section class="panel active" id="p-lab">
   <div class="card">
     <div class="controls">
       <div><label>Symbols</label><input id="lab-symbols" value="NIFTY,BANKNIFTY" size="20"/></div>
       <div><label>Source</label><select id="lab-source">
         <option value="synthetic">Synthetic · instant</option>
         <option value="nse">NSE · live</option><option value="bse">BSE · live</option></select></div>
       <div><label>Start</label><input id="lab-start" value="2019-01-01" size="10"/></div>
       <div><label>End</label><input id="lab-end" value="2023-12-31" size="10"/></div>
       <div><label>Rounds</label><input id="lab-rounds" type="number" value="1" min="1" max="3" style="width:62px"/></div>
       <button class="btn" id="lab-btn" onclick="runLab()">Run discovery ▶</button>
     </div>
     <div class="flow">Collect → Generate Hypotheses → Backtest → Validate → Rank → Learn → Repeat</div>
     <div class="spin" id="lab-spin"><div class="dot"></div><span>Searching for edges across hypotheses…</span></div>
   </div>
   <div id="lab-out" style="display:none">
     <div class="card"><div class="kpis">
       <div class="kpi"><b id="lab-k1">–</b><span>hypotheses tested (denominator)</span></div>
       <div class="kpi"><b id="lab-k2">–</b><span>validated survivors</span></div>
       <div class="kpi"><b id="lab-k3">–</b><span>scope</span></div>
     </div></div>
     <div class="card"><h3>Leaderboard</h3>
       <table><thead><tr><th>#</th><th>Hyp</th><th>Symbol</th><th>Family</th><th>Verdict</th>
         <th>Incremental lift</th><th>q (FDR)</th><th>DSR</th><th>Return</th></tr></thead>
         <tbody id="lab-tb"></tbody></table>
       <div class="note" id="lab-note"></div>
     </div>
   </div>
 </section>

 <!-- ===================== GENOME ===================== -->
 <section class="panel" id="p-genome">
   <div class="card">
     <div class="controls">
       <div><label>Symbol</label><input id="g-symbol" value="NIFTY" size="12"/></div>
       <div><label>Source</label><select id="g-source">
         <option value="synthetic">Synthetic · instant</option>
         <option value="nse">NSE · live</option><option value="bse">BSE · live</option></select></div>
       <div><label>Start</label><input id="g-start" value="2017-01-01" size="10"/></div>
       <div><label>End</label><input id="g-end" value="2023-12-31" size="10"/></div>
       <button class="btn" id="g-btn" onclick="runGenome()">Map the genome ▶</button>
     </div>
     <div class="flow">Tests condition → outcome relationships (permutation test + FDR) and graphs what survives.</div>
     <div class="spin" id="g-spin"><div class="dot"></div><span>Testing relationships across the market genome…</span></div>
   </div>
   <div id="g-out" style="display:none">
     <div class="card"><div class="kpis">
       <div class="kpi"><b id="g-k1">–</b><span>relationships found</span></div>
       <div class="kpi"><b id="g-k2">–</b><span>studies run</span></div>
       <div class="kpi"><b id="g-k3">–</b><span>scope</span></div>
     </div></div>
     <div class="grid2">
       <div class="card"><h3>Knowledge graph</h3><div id="g-graph"></div></div>
       <div class="card"><h3>Effect sizes |r|</h3><div id="g-bars"></div></div>
     </div>
     <div class="card"><h3>All studies</h3>
       <table><thead><tr><th>Study</th><th>Condition</th><th>Outcome</th><th>r</th><th>q (FDR)</th><th>Verdict</th></tr></thead>
         <tbody id="g-tb"></tbody></table>
       <div class="note" id="g-note"></div>
     </div>
   </div>
 </section>

 <!-- ===================== FUND ===================== -->
 <section class="panel" id="p-fund">
   <div class="card">
     <div class="controls">
       <div><label>Symbol</label><input id="f-symbol" value="NIFTY" size="12"/></div>
       <div><label>Source</label><select id="f-source">
         <option value="synthetic">Synthetic · instant</option>
         <option value="nse">NSE · live</option><option value="bse">BSE · live</option></select></div>
       <div><label>Start</label><input id="f-start" value="2017-01-01" size="10"/></div>
       <div><label>End</label><input id="f-end" value="2023-12-31" size="10"/></div>
       <div><label>Generations</label><input id="f-gen" type="number" value="4" min="1" max="8" style="width:74px"/></div>
       <button class="btn" id="f-btn" onclick="runFund()">Evolve strategies ▶</button>
     </div>
     <div class="flow">create → backtest → improve → re-validate → paper-trade &nbsp;·&nbsp; deploy = PAPER ONLY</div>
     <div class="spin" id="f-spin"><div class="dot"></div><span>Breeding & validating strategies…</span></div>
   </div>
   <div id="f-out" style="display:none">
     <div class="card">
       <div class="stratcard">
         <div style="font-size:30px">🏆</div>
         <div style="flex:1"><div class="muted" style="font-size:11px">best evolved strategy</div>
           <div id="f-best" style="font-size:18px;font-weight:700"></div></div>
         <div id="f-verdict"></div>
         <div class="gate">PAPER ONLY · G5</div>
       </div>
       <div class="kpis">
         <div class="kpi"><b id="f-ret">–</b><span>post-cost return</span></div>
         <div class="kpi"><b id="f-sharpe">–</b><span>Sharpe</span></div>
         <div class="kpi"><b id="f-dsr">–</b><span>Deflated Sharpe</span></div>
         <div class="kpi"><b id="f-dd">–</b><span>max drawdown</span></div>
         <div class="kpi"><b id="f-var">–</b><span>VaR 95%</span></div>
         <div class="kpi"><b id="f-exp">–</b><span>exposure</span></div>
       </div>
     </div>
     <div class="grid2">
       <div class="card"><h3>Evolution — best fitness / generation</h3><div id="f-evo"></div></div>
       <div class="card"><h3>Paper equity curve (post-cost)</h3><div id="f-eq"></div></div>
     </div>
     <div class="note" id="f-note"></div>
   </div>
 </section>

 <!-- ===================== STOCK DEEP DIVE ===================== -->
 <section class="panel" id="p-stock">
   <div class="card">
     <div class="controls">
       <div><label>Symbol</label><input id="s-symbol" list="s-list" value="RELIANCE" size="14"/>
         <datalist id="s-list"></datalist></div>
       <div><label>Source</label><select id="s-source">
         <option value="nse">NSE · live</option><option value="bse">BSE · live</option>
         <option value="synthetic">Synthetic</option></select></div>
       <div><label>History (years)</label><input id="s-years" type="number" value="6" min="2" max="12" style="width:74px"/></div>
       <button class="btn" id="s-btn" onclick="runStock()">Deep dive ▶</button>
     </div>
     <div class="flow">Technical + Gann + Astrology + Backtest, fused into one analyst view (LLM-narrated when a key is set).</div>
     <div class="spin" id="s-spin"><div class="dot"></div><span>Collecting data, computing transits, levels & backtest…</span></div>
   </div>
   <div id="s-out" style="display:none">
     <div class="card">
       <div class="stratcard">
         <div id="s-stance-emoji" style="font-size:30px">📊</div>
         <div style="flex:1"><div id="s-title" style="font-size:18px;font-weight:700"></div>
           <div class="muted" id="s-sub" style="font-size:12px"></div></div>
         <div id="s-stance"></div>
       </div>
       <div class="kpis">
         <div class="kpi"><b id="s-price">–</b><span>last close</span></div>
         <div class="kpi"><b id="s-chg">–</b><span>20-day change</span></div>
         <div class="kpi"><b id="s-trend">–</b><span>trend · RSI</span></div>
         <div class="kpi"><b id="s-verdict">–</b><span>astro+gann backtest</span></div>
       </div>
     </div>
     <div class="grid2">
       <div class="card"><h3>Technical</h3><div id="s-tech"></div></div>
       <div class="card"><h3>Gann geometry</h3><div id="s-gann"></div></div>
       <div class="card"><h3>Astrological backdrop</h3><div id="s-astro"></div></div>
       <div class="card"><h3>Backtest equity (paper, post-cost)</h3><div id="s-eq"></div></div>
     </div>
     <div class="card"><h3>Analyst narrative <span class="muted" id="s-nsrc" style="font-size:10px"></span></h3>
       <div id="s-narr" style="font-size:13.5px;line-height:1.6"></div></div>
   </div>
 </section>

 <!-- ===================== OPTIONS GREEKS ===================== -->
 <section class="panel" id="p-options">
   <div class="card">
     <div class="controls">
       <div><label>Symbol</label><input id="o-symbol" value="NIFTY" size="12"/></div>
       <div><label>Source</label><select id="o-source">
         <option value="synthetic">Synthetic · instant</option>
         <option value="nse">NSE · live</option><option value="bse">BSE · live</option></select></div>
       <div><label>Capital ₹</label><input id="o-capital" type="number" value="1000000" style="width:120px"/></div>
       <div><label>Risk %/trade</label><input id="o-risk" type="number" step="0.5" value="1.5" style="width:90px"/></div>
       <div><label>Expiry final hr</label><select id="o-final"><option value="false">No</option><option value="true">Yes (Γ-cliff)</option></select></div>
       <button class="btn" id="o-btn" onclick="runOptions()">Generate signal ▶</button>
       <button class="btn" id="o-bt" style="background:#1c2748" onclick="runOptBacktest()">Backtest</button>
     </div>
     <div class="flow">signal (dir+conviction) + IV-rank → vol regime → structure → worst-case-gap sizing → order intents. <b>You cannot be long Gamma AND long Theta.</b></div>
     <div class="spin" id="o-spin"><div class="dot"></div><span>Reading vol regime, picking structure, sizing risk…</span></div>
   </div>
   <div id="o-out" style="display:none">
     <div class="card">
       <div class="stratcard">
         <div id="o-side-emoji" style="font-size:30px">⚡</div>
         <div style="flex:1"><div id="o-action" style="font-size:18px;font-weight:700"></div>
           <div class="muted" id="o-trigger" style="font-size:12px"></div></div>
         <div id="o-regime"></div>
         <div class="gate">PAPER ONLY</div>
       </div>
       <div class="kpis">
         <div class="kpi"><b id="o-d">–</b><span>net Δ (delta)</span></div>
         <div class="kpi"><b id="o-g">–</b><span>net Γ (gamma)</span></div>
         <div class="kpi"><b id="o-t">–</b><span>net Θ/day (theta)</span></div>
         <div class="kpi"><b id="o-v">–</b><span>net Vega</span></div>
         <div class="kpi"><b id="o-lots">–</b><span>lots (worst-case sized)</span></div>
       </div>
     </div>
     <div class="grid2">
       <div class="card"><h3>Order intents</h3><table><thead><tr><th>Action</th><th>Instrument</th><th>Lots</th><th>Est. premium</th></tr></thead><tbody id="o-intents"></tbody></table></div>
       <div class="card"><h3>Risk &amp; exits</h3><div id="o-risk-tbl"></div></div>
     </div>
     <div class="note" id="o-note"></div>
   </div>
   <div id="o-bt-out" style="display:none">
     <div class="card"><div class="kpis">
       <div class="kpi"><b id="ob-ret">–</b><span>net return (post-cost)</span></div>
       <div class="kpi"><b id="ob-trades">–</b><span>trades</span></div>
       <div class="kpi"><b id="ob-win">–</b><span>win rate</span></div>
       <div class="kpi"><b id="ob-dd">–</b><span>max drawdown</span></div>
       <div class="kpi"><b id="ob-tail">–</b><span>tail loss (worst 1%)</span></div>
       <div class="kpi"><b id="ob-cap">–</b><span>realized-vs-implied capture</span></div>
     </div></div>
     <div class="grid2">
       <div class="card"><h3>Equity curve (post-cost)</h3><div id="ob-eq"></div></div>
       <div class="card"><h3>P&amp;L by vol regime</h3><div id="ob-regime"></div></div>
     </div>
     <div class="note">Synthetic-IV backtest with the India options cost stack and no look-ahead. A losing NEUTRAL bucket is the expected truth: directional debit-spreads bleed Theta in chop. Validate on real per-strike IV before any capital.</div>
   </div>
 </section>

 <footer>AstroQuant OS · research platform only · Swiss Ephemeris isolated behind the astronomy collector · nothing is assumed true, everything is tested.</footer>
</div>
<script>
function tab(n){document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.t===n));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id==='p-'+n));}
function $(id){return document.getElementById(id)}
function pct(x){return (x>=0?'+':'')+(x*100).toFixed(1)+'%'}
function sgn(x,d){d=d===undefined?3:d;return '<span class="'+(x>=0?'pos':'neg')+'">'+(x>=0?'+':'')+x.toFixed(d)+'</span>'}
function vbadge(v){var m={edge:['b-edge','EDGE'],conditional_edge:['b-cond','CONDITIONAL'],no_edge_found:['b-no','NO EDGE'],
  relationship:['b-edge','RELATIONSHIP'],no_relationship:['b-no','NONE'],not_validated:['b-no','—']};
  var x=m[v]||['b-no',(v||'').toUpperCase()];return '<span class="badge '+x[0]+'">'+x[1]+'</span>'}
async function call(url){const r=await fetch(url,{method:'POST'}); if(!r.ok) throw new Error(r.status); return r.json();}
function busy(b,btn,sp){$(btn).disabled=b;$(sp).classList.toggle('on',b);}

function lineSVG(vals,opt){opt=opt||{};var w=opt.w||560,h=opt.h||190,p=26;
  if(!vals||vals.length<2)return '<div class="muted">no data</div>';
  var lo=Math.min.apply(0,vals),hi=Math.max.apply(0,vals),rg=(hi-lo)||1;
  var pts=vals.map(function(v,i){var x=p+(w-2*p)*i/(vals.length-1);var y=p+(h-2*p)*(1-(v-lo)/rg);return x.toFixed(1)+','+y.toFixed(1)}).join(' ');
  var up=vals[vals.length-1]>=vals[0];var c=opt.color||(up?'#34d399':'#f87171');
  var y0=p+(h-2*p)*(1-(((opt.base!==undefined?opt.base:vals[0])-lo)/rg));
  return '<svg viewBox="0 0 '+w+' '+h+'" class="chart"><line x1="'+p+'" y1="'+y0.toFixed(1)+'" x2="'+(w-p)+'" y2="'+y0.toFixed(1)+'" stroke="#2a3658" stroke-dasharray="4 4"/>'+
    '<polyline points="'+pts+'" fill="none" stroke="'+c+'" stroke-width="2.2"/></svg>';}

function graphSVG(graph){var w=520,h=300,p=18;
  var conds=[],outs=[];graph.edges.forEach(function(e){if(conds.indexOf(e.from)<0)conds.push(e.from);if(outs.indexOf(e.to)<0)outs.push(e.to)});
  function ypos(i,n){return p+18+(h-2*p-36)*(n<2?0.5:i/(n-1))}
  var lx=130,rx=w-130,svg='<svg viewBox="0 0 '+w+' '+h+'" class="chart">';
  graph.edges.forEach(function(e){var yi=ypos(conds.indexOf(e.from),conds.length),yo=ypos(outs.indexOf(e.to),outs.length);
    var rel=e.verdict==='relationship';var col=rel?'#34d399':'#33406e';var wdt=1+Math.min(6,Math.abs(e.effect)*30);
    svg+='<line x1="'+lx+'" y1="'+yi.toFixed(1)+'" x2="'+rx+'" y2="'+yo.toFixed(1)+'" stroke="'+col+'" stroke-width="'+wdt.toFixed(1)+'" opacity="'+(rel?0.95:0.5)+'"/>';});
  conds.forEach(function(c,i){var y=ypos(i,conds.length);svg+='<circle cx="'+lx+'" cy="'+y.toFixed(1)+'" r="5" fill="#7c5cff"/>'+
    '<text x="'+(lx-10)+'" y="'+(y+4).toFixed(1)+'" fill="#cdd7f5" font-size="11" text-anchor="end">'+c+'</text>';});
  outs.forEach(function(o,i){var y=ypos(i,outs.length);svg+='<circle cx="'+rx+'" cy="'+y.toFixed(1)+'" r="6" fill="#3b82f6"/>'+
    '<text x="'+(rx+10)+'" y="'+(y+4).toFixed(1)+'" fill="#cdd7f5" font-size="11">'+o+'</text>';});
  return svg+'</svg>';}

function barRows(items){ // items: {label,value,max,verdict}
  var max=Math.max.apply(0,items.map(function(i){return i.max}))||1;
  return items.map(function(it){var pctw=Math.min(100,100*it.value/max);var c=it.verdict==='relationship'?'#34d399':'#5b6aa8';
    return '<div style="display:flex;align-items:center;gap:10px;margin:7px 0"><div class="muted" style="width:120px;font-size:12px">'+it.label+'</div>'+
    '<div class="bar" style="flex:1"><span style="width:'+pctw.toFixed(0)+'%;background:'+c+'"></span></div>'+
    '<div style="width:54px;text-align:right;font-size:12px">'+it.value.toFixed(3)+'</div></div>';}).join('');}

async function runLab(){busy(true,'lab-btn','lab-spin');try{
  var q=new URLSearchParams({symbols:$('lab-symbols').value,source:$('lab-source').value,start:$('lab-start').value,end:$('lab-end').value,rounds:$('lab-rounds').value});
  var d=await call('/lab/run?'+q);$('lab-out').style.display='block';
  $('lab-k1').textContent=d.total_tested;$('lab-k2').textContent=d.n_survivors;$('lab-k3').textContent=d.symbols.join(', ')+' · '+d.source;
  $('lab-tb').innerHTML=d.leaderboard.map(function(x){var lift=Math.min(100,Math.abs(x.incremental_lift)*900);
    return '<tr><td>'+x.rank+'</td><td>'+x.hypothesis_id+'</td><td>'+x.symbol+'</td><td>'+x.trial_families.join('+')+'</td><td>'+vbadge(x.verdict)+'</td>'+
    '<td><div style="display:flex;align-items:center;gap:8px"><div class="bar" style="width:70px"><span style="width:'+lift.toFixed(0)+'%;background:'+(x.incremental_lift>=0?'#34d399':'#f87171')+'"></span></div>'+sgn(x.incremental_lift)+'</div></td>'+
    '<td>'+x.q_value.toFixed(3)+'</td><td>'+x.dsr.toFixed(2)+'</td><td>'+sgn(x.total_return,3)+'</td></tr>';}).join('');
  $('lab-note').innerHTML=d.n_survivors>0?('<b>'+d.n_survivors+' strategy(ies) cleared every hurdle.</b> Re-validate before trusting — the bar rises with the number tried.')
    :'<b>No validated edge — and that is the platform working.</b> A row only survives if its lift is positive, out-of-sample, post-cost, with batch-corrected q&lt;0.05 and Deflated Sharpe&gt;0.5. On noise the honest answer is "no edge".';
}catch(e){alert('Lab run failed: '+e)}finally{busy(false,'lab-btn','lab-spin')}}

async function runGenome(){busy(true,'g-btn','g-spin');try{
  var q=new URLSearchParams({symbol:$('g-symbol').value,source:$('g-source').value,start:$('g-start').value,end:$('g-end').value});
  var d=await call('/genome/run?'+q);$('g-out').style.display='block';
  $('g-k1').textContent=d.n_relationships;$('g-k2').textContent=d.n_studies;$('g-k3').textContent=d.symbol+' · '+d.source;
  $('g-graph').innerHTML=graphSVG(d.graph);
  $('g-bars').innerHTML=barRows(d.findings.map(function(f){return {label:f.predictor+'→'+f.outcome,value:f.abs_effect,max:f.abs_effect,verdict:f.verdict}}));
  $('g-tb').innerHTML=d.findings.map(function(f){return '<tr><td>'+f.id+'</td><td>'+f.predictor+'</td><td>'+f.outcome+'</td><td>'+sgn(f.effect)+'</td><td>'+f.q_value.toFixed(3)+'</td><td>'+vbadge(f.verdict)+'</td></tr>'}).join('');
  $('g-note').innerHTML=d.n_relationships>0?('<b>'+d.n_relationships+' relationship(s) survived FDR correction.</b> Knowledge, not a trade — confirm out-of-sample before acting.')
    :'<b>No relationship survived correction — a genuine knowledge result (an honest null).</b> Method-control studies (RSI, weekday, momentum) are included so you can see the battery is sensitive.';
}catch(e){alert('Genome run failed: '+e)}finally{busy(false,'g-btn','g-spin')}}

async function runFund(){busy(true,'f-btn','f-spin');try{
  var q=new URLSearchParams({symbol:$('f-symbol').value,source:$('f-source').value,start:$('f-start').value,end:$('f-end').value,generations:$('f-gen').value});
  var d=await call('/fund/evolve?'+q);var e=d.evolution,r=d.risk;$('f-out').style.display='block';
  $('f-best').textContent='['+e.best_label+']  band '+e.best_prob_band+' · L2 '+e.best_l2+'  ·  '+e.n_evaluated+' strategies tried';
  $('f-verdict').innerHTML='validated: '+vbadge(r.research_verdict);
  $('f-ret').innerHTML=sgn(r.total_return,3);$('f-ret').className='';$('f-ret').innerHTML=pct(r.total_return);
  $('f-sharpe').textContent=r.sharpe.toFixed(2);$('f-dsr').textContent=r.deflated_sharpe.toFixed(2);
  $('f-dd').textContent=(r.max_drawdown*100).toFixed(1)+'%';$('f-var').textContent=(r.var_95*100).toFixed(2)+'%';
  $('f-exp').textContent=(r.exposure*100).toFixed(0)+'%';
  $('f-evo').innerHTML=lineSVG(e.history.map(function(h){return h.best_fitness}),{color:'#7c5cff'});
  $('f-eq').innerHTML=lineSVG(r.equity_curve,{base:r.equity_curve[0]});
  $('f-note').innerHTML=(r.research_verdict==='no_edge_found')
    ?'<b>The evolved winner looked good on its own slice but was graded NO-EDGE by the rigorous engine.</b> That is the anti-overfitting gate: a backtest Sharpe selected from many trials is deflated and walk-forward tested before it can be believed. Deploy stays paper-only.'
    :'<b>This strategy cleared the rigorous gate.</b> Still paper-only (G5) — forward-validate for months before any live discussion.';
}catch(e){alert('Fund run failed: '+e)}finally{busy(false,'f-btn','f-spin')}}

function kv(rows){return '<table>'+rows.map(function(r){return '<tr><td class="muted" style="width:44%">'+r[0]+'</td><td>'+r[1]+'</td></tr>'}).join('')+'</table>';}
function md(t){return (t||'').split('\n').map(function(l){
  if(/^#\s/.test(l))return '<h2 style="font-size:17px;margin:14px 0 6px;color:#fff">'+l.replace(/^#\s/,'')+'</h2>';
  if(/^##\s/.test(l))return '<h3 style="margin:14px 0 6px">'+l.replace(/^##\s/,'')+'</h3>';
  if(/^>\s/.test(l))return '<blockquote style="border-left:3px solid #34406e;margin:8px 0;padding:6px 12px;color:#aab6da">'+l.replace(/^>\s/,'')+'</blockquote>';
  if(/^\s*$/.test(l))return '';return '<p style="margin:6px 0">'+l+'</p>';}).join('').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');}

async function runStock(){busy(true,'s-btn','s-spin');try{
  var q=new URLSearchParams({symbol:$('s-symbol').value,source:$('s-source').value,years:$('s-years').value});
  var d=await call('/stock/analyze?'+q);$('s-out').style.display='block';
  var m=d.market,t=d.technical,g=d.gann,a=d.astro,b=d.backtest,s=d.scores;
  $('s-title').textContent=d.name+' ('+d.symbol+')';
  $('s-sub').textContent=d.sector+' · as of '+d.as_of+' · '+d.n_bars+' sessions · '+((d.meta&&d.meta.data_source_stamp)||d.source);
  $('s-stance').innerHTML='<span class="badge '+(s.stance==='Constructive'?'b-edge':(s.stance==='Cautious'?'b-cond':'b-no'))+'">'+s.stance.toUpperCase()+' '+(s.composite>=0?'+':'')+s.composite+'</span>';
  $('s-stance-emoji').textContent=s.stance==='Constructive'?'🟢':(s.stance==='Cautious'?'🔴':'🟡');
  $('s-price').textContent='₹'+m.last_close.toLocaleString('en-IN');
  $('s-chg').innerHTML=pct(m.change_20d);
  $('s-trend').textContent=t.trend+' · RSI '+t.rsi14;
  $('s-verdict').innerHTML=vbadge(b.verdict||'not_validated');
  $('s-tech').innerHTML=kv([['Trend',t.trend],['RSI(14)',t.rsi14+' ('+t.rsi_state+')'],['Price vs 20D SMA',pct(t.price_vs_sma20)+' · ₹'+t.sma20],['Price vs 50D SMA',pct(t.price_vs_sma50)+' · ₹'+t.sma50],['20D momentum',pct(t.momentum_20d)],['Ann. volatility',(t.volatility_annual*100).toFixed(0)+'%'],['Volume vs 20D avg',t.volume_vs_avg20+'×']]);
  var cyc=(g.upcoming_cycles||[]).slice(0,4).map(function(c){return c.date+' ('+c.days+'d/'+c.from+')'}).join(', ')||'—';
  $('s-gann').innerHTML=kv([['Nearest resistance','₹'+g.nearest_resistance],['Nearest support','₹'+g.nearest_support],['Resistances','₹'+(g.resistances||[]).join(', ₹')],['Supports','₹'+(g.supports||[]).join(', ₹')],['Swing high','₹'+g.pivot_high+' · '+g.pivot_high_date],['Swing low','₹'+g.pivot_low+' · '+g.pivot_low_date],['Time-cycle windows',cyc]]);
  $('s-astro').innerHTML=kv([['Moon',a.moon_sign+' / '+a.moon_nakshatra+' ('+a.paksha+', '+(a.moon_illum*100).toFixed(0)+'%)'],['Sun',a.sun_sign],['Retrograde',(a.retrogrades||[]).join(', ')||'none'],['Tight aspects',(a.aspects||[]).slice(0,4).map(function(x){return x.a+'–'+x.b+' '+x.type}).join('; ')||'none']]);
  $('s-eq').innerHTML=(b.equity_curve&&b.equity_curve.length>1)?lineSVG(b.equity_curve,{base:b.equity_curve[0]}):'<div class="muted">backtest equity unavailable</div>';
  $('s-nsrc').textContent='· '+(d.narrative_source||'built-in');
  $('s-narr').innerHTML=md(d.narrative);
}catch(e){alert('Stock analysis failed: '+e)}finally{busy(false,'s-btn','s-spin')}}

async function runOptions(){busy(true,'o-btn','o-spin');try{
  var q=new URLSearchParams({symbol:$('o-symbol').value,source:$('o-source').value,capital:$('o-capital').value,risk_pct:($('o-risk').value/100),final_hour:$('o-final').value});
  var d=await call('/options/signal?'+q);$('o-out').style.display='block';
  var seller=d.action.indexOf('SELL')===0, none=d.action.indexOf('NO TRADE')>=0;
  $('o-side-emoji').textContent=none?'⛔':(seller?'🔻':'🟢');
  $('o-action').textContent=d.action; $('o-trigger').textContent=d.trigger;
  var rb={CHEAP:'b-edge',RICH:'b-cond',NEUTRAL:'b-no'}[d.regime]||'b-no';
  $('o-regime').innerHTML='<span class="badge '+rb+'">'+d.regime+' · IVrank '+(d.iv_rank*100).toFixed(0)+'%</span>';
  var g=d.position_greeks;
  $('o-d').textContent=g.delta;$('o-g').textContent=g.gamma;$('o-t').textContent=g.theta_day;$('o-v').textContent=g.vega_pt;$('o-lots').textContent=d.sizing.lots;
  $('o-intents').innerHTML=d.order_intents.map(function(it){return '<tr><td><span class="badge '+(it.action==='BUY'?'b-edge':'b-cond')+'">'+it.action+'</span></td><td>'+it.instrument+'</td><td>'+it.lots+'</td><td>₹'+it.est_premium+'</td></tr>'}).join('')||'<tr><td colspan="4" class="muted">no legs — risk cap too small for one lot</td></tr>';
  $('o-risk-tbl').innerHTML=kv([['Worst-case loss / lot','₹'+d.sizing.worst_case_per_lot.toLocaleString('en-IN')],['Risk cap (per trade)','₹'+d.sizing.risk_cap.toLocaleString('en-IN')],['Total worst-case','₹'+d.sizing.total_worst_case.toLocaleString('en-IN')],['Overnight gap assumed',(d.sizing.gap_pct*100)+'%'],['Net debit/credit','₹'+d.decision.structure.net_debit],['Structure max loss','₹'+d.decision.structure.max_loss.toLocaleString('en-IN')],['Gates',(d.decision.gate_failures||[]).join('; ')||'✓ all passed']]);
  var ex=Object.keys(d.exits).map(function(k){return '<b>'+k+'</b>: '+d.exits[k]}).join('<br>');
  $('o-note').innerHTML='<b>Exit logic (Greek-based, not P&L):</b><br>'+ex+'<br><br><span class="muted">'+d.note+'</span>';
}catch(e){alert('Options signal failed: '+e)}finally{busy(false,'o-btn','o-spin')}}

async function runOptBacktest(){busy(true,'o-bt','o-spin');try{
  var q=new URLSearchParams({symbol:$('o-symbol').value,source:($('o-source').value==='nse'?'synthetic':$('o-source').value),years:6});
  var d=await call('/options/backtest?'+q);$('o-bt-out').style.display='block';
  $('ob-ret').innerHTML=pct(d.total_return);$('ob-trades').textContent=d.n_trades;
  $('ob-win').textContent=(d.win_rate*100).toFixed(0)+'%';$('ob-dd').textContent=(d.max_drawdown*100).toFixed(1)+'%';
  $('ob-tail').textContent='₹'+d.tail_loss_1pct.toLocaleString('en-IN');$('ob-cap').textContent=(d.realized_vs_implied_capture*100).toFixed(0)+'%';
  $('ob-eq').innerHTML=lineSVG(d.equity_curve,{base:d.equity_curve[0]});
  $('ob-regime').innerHTML=kv(Object.keys(d.by_regime).map(function(k){return [k,d.by_regime[k].trades+' trades · ₹'+d.by_regime[k].pnl.toLocaleString('en-IN')]}));
}catch(e){alert('Options backtest failed: '+e)}finally{busy(false,'o-bt','o-spin')}}

async function loadUniverse(){try{var r=await fetch('/universe');var d=await r.json();
  $('s-list').innerHTML=d.stocks.map(function(x){return '<option value="'+x.symbol+'">'+x.name+' · '+x.sector+'</option>'}).join('');}catch(e){}}
window.addEventListener('load',loadUniverse);
</script>
</body></html>"""
