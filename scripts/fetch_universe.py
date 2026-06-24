"""
Refresh the bundled exchange masters under python/astroquant/universe/data/.

Pulls the official NSE equity master + the BSE active-equity scrip master (free, public) and writes
compact CSVs the universe loads offline. MCX commodity futures are a small curated list with Yahoo
global-commodity proxies. Run periodically to keep the universe current (membership changes over time).

Run:  PYTHONPATH=python python3 scripts/fetch_universe.py
"""
from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "python" / "astroquant" / "universe" / "data"
H = {"User-Agent": "Mozilla/5.0 (AstroQuant-OS)", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}

MCX = [
    ("GOLD", "Gold", "GC=F"), ("SILVER", "Silver", "SI=F"), ("CRUDEOIL", "Crude Oil", "CL=F"),
    ("NATURALGAS", "Natural Gas", "NG=F"), ("COPPER", "Copper", "HG=F"), ("ZINC", "Zinc", ""),
    ("ALUMINIUM", "Aluminium", "ALI=F"), ("LEAD", "Lead", ""), ("NICKEL", "Nickel", ""),
    ("COTTON", "Cotton", "CT=F"), ("MENTHAOIL", "Mentha Oil", ""), ("GOLDM", "Gold Mini", "GC=F"),
    ("SILVERM", "Silver Mini", "SI=F"), ("CRUDEOILM", "Crude Oil Mini", "CL=F"),
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    base = "https://www.nseindia.com"
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    op.open(urllib.request.Request(base, headers={**H, "Referer": base}), timeout=12)
    raw = op.open(urllib.request.Request(
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        headers={**H, "Referer": base}), timeout=25).read().decode("utf-8", "replace")
    rows = list(csv.reader(raw.splitlines()))
    nse = [(r[0].strip(), r[1].strip()) for r in rows[1:]
           if len(r) > 2 and r[2].strip() in ("EQ", "BE", "BZ", "SM", "ST")]
    with (DATA / "nse_equity.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["symbol", "name"]); w.writerows(nse)
    print("NSE:", len(nse))

    hb = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
          "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
    u = ("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
         "?Group=&Scripcode=&industry=&segment=Equity&status=Active")
    j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=hb), timeout=30)
                   .read().decode("utf-8", "replace"))
    bse = [(str(r.get("SCRIP_CD", "")).strip(), (r.get("scrip_id") or "").strip(),
            (r.get("Scrip_Name") or "").strip(), (r.get("INDUSTRY") or "").strip())
           for r in j if r.get("SCRIP_CD") and r.get("Scrip_Name")]
    with (DATA / "bse_equity.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "symbol", "name", "industry"]); w.writerows(bse)
    print("BSE:", len(bse))

    with (DATA / "mcx.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["symbol", "name", "yahoo"]); w.writerows(MCX)
    print("MCX:", len(MCX))
    print("TOTAL:", len(nse) + len(bse) + len(MCX))


if __name__ == "__main__":
    main()
