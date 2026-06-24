"""
Bake a static, openable snapshot of the dashboard with embedded results for all three ideas.

Runs the Lab, Genome, and Fund once, embeds the JSON into the dashboard, and overrides the fetch
layer so the page renders fully **with no server** — open the HTML directly in a browser to click
through all three tabs. For the live, re-runnable app use `astroquant serve` or deploy to Render.

Run:  PYTHONPATH=python python3 scripts/build_preview.py out.html [source]
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "python")

from fastapi.testclient import TestClient   # noqa: E402

from astroquant.api.app import app          # noqa: E402
from astroquant.api.dashboard import DASHBOARD_HTML  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "dashboard_preview.html"
    src = sys.argv[2] if len(sys.argv) > 2 else "synthetic"
    c = TestClient(app)
    print(f"building preview from {src} data …")
    lab = c.post("/lab/run", params={"symbols": "NIFTY,BANKNIFTY", "source": src,
                                      "start": "2021-01-01", "end": "2024-12-31", "permutations": 8}).json()
    gen = c.post("/genome/run", params={"symbol": "NIFTY", "source": src,
                                        "start": "2018-01-01", "end": "2024-12-31"}).json()
    fund = c.post("/fund/evolve", params={"symbol": "NIFTY", "source": src, "start": "2018-01-01",
                                          "end": "2024-12-31", "generations": 5, "pop": 8}).json()
    data = json.dumps({"lab": lab, "genome": gen, "fund": fund})
    inject = (
        "<script>window.__D=" + data + ";"
        "call=async function(u){if(u.indexOf('/lab')>=0)return window.__D.lab;"
        "if(u.indexOf('/genome')>=0)return window.__D.genome;return window.__D.fund;};"
        "window.addEventListener('load',function(){try{runLab();runGenome();runFund();}catch(e){}});"
        "</script>"
    )
    html = DASHBOARD_HTML.replace("</body>", inject + "\n</body>")
    html = html.replace("research only — no live trading",
                        "static preview (" + src + ") · run `astroquant serve` for the live app")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out}  (lab survivors={lab['n_survivors']}, "
          f"genome relationships={gen['n_relationships']}, fund verdict={fund['risk']['research_verdict']})")


if __name__ == "__main__":
    main()
