"""
FastAPI service for the Autonomous Alpha Discovery Lab.

Endpoints
  GET  /healthz            liveness probe (Render health check)
  GET  /                   live HTML dashboard (run the lab, see the leaderboard)
  POST /lab/run            run a discovery round -> LabReport JSON
  GET  /discoveries        the discoveries ledger from the DB (JSON)
  GET  /astro/{date}       sidereal planetary positions for a date (engine demo)

Run locally:  PYTHONPATH=python uvicorn astroquant.api.app:app --reload
Run on Render: uvicorn astroquant.api.app:app --host 0.0.0.0 --port $PORT   (after pip install -e .)

NOTE ON SECRETS: this service reads all configuration from environment variables
(AQ_DB_URL, AQ_BROKER, …). Never hard-code API keys/tokens; set them as Render env vars.
"""
from __future__ import annotations

from datetime import date

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from astroquant.agents.base import get_logger
from astroquant.lab import DiscoveryLab

log = get_logger("api")
app = FastAPI(title="AstroQuant OS — Autonomous Alpha Discovery Lab", version="0.2.0")

_STATE: dict = {"last_report": None}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "astroquant-os", "version": "0.2.0"}


@app.get("/astro/{d}")
def astro(d: str) -> dict:
    from astroquant.collectors.astronomy import AstronomyCollector

    rows = AstronomyCollector().planets_for_date(date.fromisoformat(d))
    return {"date": d, "planets": [r.__dict__ for r in rows]}


@app.post("/lab/run")
def lab_run(
    symbols: str = Query("NIFTY,BANKNIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    start: str = Query("2019-01-01"),
    end: str = Query("2024-12-31"),
    rounds: int = Query(1, ge=1, le=3),
    permutations: int = Query(10, ge=4, le=40),
) -> JSONResponse:
    """Run the Collect→Hypotheses→Backtest→Validate→Rank→Learn loop and return the leaderboard."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:5]
    lab = DiscoveryLab(
        syms, source=source, start=date.fromisoformat(start), end=date.fromisoformat(end),
        persist=True, k_folds=4, n_permutations=permutations,
    )
    report = lab.run(rounds=rounds, learn=(rounds > 1))
    _STATE["last_report"] = report
    log.info("api: lab run complete — %d tested, %d survivors", report.total_tested, report.n_survivors)
    return JSONResponse(report.to_dict())


@app.get("/discoveries")
def discoveries(limit: int = Query(50, ge=1, le=500)) -> dict:
    try:
        from astroquant.db import repo
        from astroquant.db.session import get_engine, init_db, session_scope

        eng = get_engine()
        init_db(eng)
        with session_scope(eng) as s:
            return {"discoveries": repo.list_signals(s, limit=limit)}
    except Exception as e:  # noqa: BLE001
        return {"discoveries": [], "error": str(e)}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return DASHBOARD_HTML


# --- the live dashboard (self-contained: inline CSS + JS, no CDN) ---
DASHBOARD_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AstroQuant OS — Autonomous Alpha Discovery Lab</title>
<style>
 :root{--ink:#1f2733;--muted:#5a6472;--line:#e6eaf0;--bg:#f1f4f8;--card:#fff;--accent:#3b5bdb;}
 *{box-sizing:border-box} body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
 .wrap{max-width:1000px;margin:0 auto;padding:26px 20px 70px}
 h1{margin:0 0 2px;font-size:23px} .sub{color:var(--muted);font-size:14px;margin-bottom:18px}
 .panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:18px}
 .row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
 label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
 input,select{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff}
 button{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:10px 18px;font-weight:600;cursor:pointer;font-size:14px}
 button:disabled{opacity:.5;cursor:wait}
 .pipe{font-size:12px;color:var(--muted);margin:10px 0 0;letter-spacing:.3px}
 .kpis{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 0}
 .kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:150px}
 .kpi b{display:block;font-size:22px} .kpi span{color:var(--muted);font-size:12px}
 table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
 th{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);text-align:left;padding:8px 6px;border-bottom:1px solid var(--line)}
 td{padding:8px 6px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
 .badge{padding:3px 9px;border-radius:999px;color:#fff;font-size:11px;font-weight:700}
 .b-edge{background:#0b8457}.b-cond{background:#b8860b}.b-no{background:#5a6472}
 .pos{color:#0b8457}.neg{color:#c0392b}
 .note{font-size:12px;color:#6b5b1f;background:#fff8e6;border:1px solid #f0e2bb;border-radius:10px;padding:10px 12px;margin-top:16px}
 .spin{display:none;color:var(--muted);font-size:13px;margin-left:8px}
</style></head><body><div class="wrap">
 <h1>🔭 AstroQuant OS — Autonomous Alpha Discovery Lab</h1>
 <div class="sub">Continuously tests whether astrology, Gann, technical & market signals have real,
   out-of-sample, <b>post-cost</b> predictive edge in Indian markets — and reports honest nulls.</div>

 <div class="panel">
   <div class="row">
     <div><label>Symbols (comma-sep)</label><input id="symbols" value="NIFTY,BANKNIFTY" size="22"/></div>
     <div><label>Source</label><select id="source">
       <option value="nse">NSE (live, free)</option>
       <option value="bse">BSE (live, free)</option>
       <option value="synthetic">Synthetic (offline)</option>
     </select></div>
     <div><label>Start</label><input id="start" value="2019-01-01" size="10"/></div>
     <div><label>End</label><input id="end" value="2024-12-31" size="10"/></div>
     <div><label>Rounds</label><input id="rounds" type="number" value="1" min="1" max="3" style="width:64px"/></div>
     <div><button id="run" onclick="runLab()">Run discovery ▶</button><span class="spin" id="spin">collecting data, generating &amp; testing hypotheses… (can take ~20–40s on live data)</span></div>
   </div>
   <div class="pipe">Collect → Generate Hypotheses → Backtest → Validate → Rank → Learn → Repeat</div>
 </div>

 <div id="results" style="display:none">
   <div class="kpis">
     <div class="kpi"><b id="k-tested">–</b><span>hypotheses tested (denominator)</span></div>
     <div class="kpi"><b id="k-surv">–</b><span>validated survivors</span></div>
     <div class="kpi"><b id="k-syms">–</b><span>symbols · source</span></div>
   </div>
   <div class="panel" style="margin-top:14px">
     <h3 style="margin:0 0 6px;font-size:14px">Leaderboard</h3>
     <table><thead><tr><th>#</th><th>Hypothesis</th><th>Symbol</th><th>Family on trial</th>
       <th>Verdict</th><th>Lift</th><th>q (FDR)</th><th>DSR</th><th>Return</th></tr></thead>
       <tbody id="lb"></tbody></table>
   </div>
   <div class="note"><b>Reading the board:</b> a row only “survives” if its incremental lift is positive,
     out-of-sample, post-cost, and its <b>batch-corrected q-value &lt; 0.05</b> with Deflated Sharpe &gt; 0.5.
     On noise (or on signals that don’t clear the multiple-testing bar), the honest answer is
     <b>no edge</b> — which is the lab working correctly, not failing.</div>
 </div>

<script>
function badge(v){const m={edge:['b-edge','EDGE'],conditional_edge:['b-cond','CONDITIONAL'],no_edge_found:['b-no','NO EDGE']};
  const x=m[v]||['b-no',v]; return '<span class="badge '+x[0]+'">'+x[1]+'</span>';}
function sgn(x){const c=x>=0?'pos':'neg';return '<span class="'+c+'">'+(x>=0?'+':'')+x.toFixed(3)+'</span>';}
async function runLab(){
  const b=document.getElementById('run'),sp=document.getElementById('spin');
  b.disabled=true; sp.style.display='inline';
  const q=new URLSearchParams({symbols:symbols.value,source:source.value,start:start.value,end:end.value,rounds:rounds.value});
  try{
    const r=await fetch('/lab/run?'+q.toString(),{method:'POST'});
    const d=await r.json();
    document.getElementById('results').style.display='block';
    document.getElementById('k-tested').textContent=d.total_tested;
    document.getElementById('k-surv').textContent=d.n_survivors;
    document.getElementById('k-syms').textContent=d.symbols.join(', ')+' · '+d.source;
    const tb=document.getElementById('lb'); tb.innerHTML='';
    d.leaderboard.forEach(x=>{tb.insertAdjacentHTML('beforeend',
      '<tr><td>'+x.rank+'</td><td>'+x.hypothesis_id+'</td><td>'+x.symbol+'</td><td>'+x.trial_families.join('+')+'</td><td>'+badge(x.verdict)+'</td><td>'+sgn(x.incremental_lift)+'</td><td>'+x.q_value.toFixed(3)+'</td><td>'+x.dsr.toFixed(2)+'</td><td>'+sgn(x.total_return)+'</td></tr>');});
  }catch(e){alert('Run failed: '+e);}finally{b.disabled=false; sp.style.display='none';}
}
</script>
</div></body></html>"""
