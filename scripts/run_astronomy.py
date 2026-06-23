"""
Demo / smoke test for the Astronomy Collector.
Run:  PYTHONPATH=python python3 scripts/run_astronomy.py
Computes sidereal (Lahiri) positions and prints a readable table — no DB or API keys needed.
"""
from __future__ import annotations

import sys
from datetime import date

sys.path.insert(0, "python")

from astroquant.collectors.astronomy import AstronomyCollector  # noqa: E402


def main() -> None:
    col = AstronomyCollector(ayanamsa="lahiri")
    h = col.healthcheck()
    print(f"healthcheck: ok={h.ok}  ({h.detail})\n")

    d = date(2024, 1, 1)
    print(f"=== Sidereal (Lahiri) planetary positions for {d} ===")
    print(f"{'Body':<9}{'Sid.Long':>10}{'Sign':<13}{'Nakshatra':<18}{'Pada':>5}{'Retro':>7}")
    for p in col.planets_for_date(d):
        print(f"{p.body:<9}{p.longitude_sidereal:>10.4f}  {p.sign_name:<11}"
              f"{p.nakshatra_name:<18}{p.pada:>5}{'  R' if p.is_retrograde else '   ':>7}")

    mp = col.moon_phase_for_date(d)
    print(f"\nMoon phase: elongation={mp.phase_angle}°  illumination={mp.illumination*100:.1f}%  "
          f"tithi={mp.tithi}  paksha={mp.paksha}")

    print("\n=== A few aspect separations (sidereal) ===")
    for a in col.aspects_for_date(d):
        if a.body_a in ("Jupiter", "Saturn") and a.body_b in ("Jupiter", "Saturn", "Sun", "Mars"):
            print(f"{a.body_a:<9}–{a.body_b:<9} {a.angle_deg:>8.4f}°")


if __name__ == "__main__":
    main()
