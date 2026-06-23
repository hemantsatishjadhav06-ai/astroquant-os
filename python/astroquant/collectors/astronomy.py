"""
Agent 4 — Astronomy / Ephemeris Collector  (docs/004 §Agent 4, docs/005 §3)

Computes geocentric SIDEREAL (Lahiri ayanamsa) longitudes for the classical Vedic bodies,
plus derived constructs: rasi (sign), nakshatra+pada, retrograde flag, moon phase/tithi,
and pairwise aspect angles. Deterministic function of time => no data-collection look-ahead.

Uses the built-in Moshier model when no .se1 ephemeris files are configured (still ~0.1"
precision for planets), so this runs anywhere with just `pip install pyswisseph`.

LICENSE: Swiss Ephemeris is AGPL (or commercial). See docs/VERIFICATION_ADDENDUM.md.
This engine is intentionally isolated behind this module so it can be swapped if the project
ever becomes a distributed/SaaS product.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone

import swisseph as swe

from astroquant.agents.base import Agent, Health, RunContext, RunResult, content_hash, get_logger

log = get_logger("collector.astronomy")

# Bodies we track (name -> Swiss Ephemeris body id). Rahu = mean lunar node; Ketu = +180°.
BODIES: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# 27 nakshatras, each 13°20' (= 800') of the sidereal zodiac.
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]


@dataclass
class PlanetRow:
    obs_date: str
    body: str
    longitude_sidereal: float
    longitude_tropical: float
    speed: float
    is_retrograde: bool
    sign: int           # 1..12
    sign_name: str
    nakshatra: int      # 1..27
    nakshatra_name: str
    pada: int           # 1..4


@dataclass
class MoonPhaseRow:
    obs_date: str
    phase_angle: float      # Sun-Moon elongation, 0..360
    illumination: float     # 0..1
    tithi: int              # 1..30
    paksha: str             # Shukla (waxing) / Krishna (waning)


@dataclass
class AspectRow:
    obs_date: str
    body_a: str
    body_b: str
    angle_deg: float        # 0..180 separation


def _julday(d: date) -> float:
    """Julian day at 00:00 UTC for the given date."""
    dt = datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc)
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)


def _nakshatra_pada(longitude_sidereal: float) -> tuple[int, int]:
    """Map a sidereal longitude to nakshatra (1..27) and pada (1..4)."""
    seg = 360.0 / 27.0          # 13°20'
    idx = int(longitude_sidereal // seg)          # 0..26
    within = longitude_sidereal - idx * seg
    pada = int(within // (seg / 4.0)) + 1         # 1..4
    return idx + 1, pada


class AstronomyCollector:
    name = "astronomy_collector"
    version = "0.1.0"

    def __init__(self, ephe_path: str = "", ayanamsa: str = "lahiri") -> None:
        if ephe_path:
            swe.set_ephe_path(ephe_path)
        # Sidereal mode with Lahiri ayanamsa for Vedic longitudes.
        if ayanamsa.lower() == "lahiri":
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        self._flags_sidereal = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
        self._flags_tropical = swe.FLG_SWIEPH | swe.FLG_SPEED

    # --- core computations (pure; unit-testable without a DB) ---

    def planets_for_date(self, d: date) -> list[PlanetRow]:
        jd = _julday(d)
        rows: list[PlanetRow] = []
        for name, body_id in BODIES.items():
            sid, _ = swe.calc_ut(jd, body_id, self._flags_sidereal)
            trop, _ = swe.calc_ut(jd, body_id, self._flags_tropical)
            lon_sid, speed = sid[0] % 360.0, sid[3]
            lon_trop = trop[0] % 360.0
            sign_idx = int(lon_sid // 30)                 # 0..11
            nak, pada = _nakshatra_pada(lon_sid)
            rows.append(PlanetRow(
                obs_date=d.isoformat(), body=name,
                longitude_sidereal=round(lon_sid, 6),
                longitude_tropical=round(lon_trop, 6),
                speed=round(speed, 6),
                is_retrograde=speed < 0,                  # Sun/Moon never retrograde
                sign=sign_idx + 1, sign_name=SIGNS[sign_idx],
                nakshatra=nak, nakshatra_name=NAKSHATRAS[nak - 1], pada=pada,
            ))
            # Ketu = Rahu + 180°
            if name == "Rahu":
                lon_k = (lon_sid + 180.0) % 360.0
                trop_k = (lon_trop + 180.0) % 360.0
                sgn = int(lon_k // 30)
                nk, pk = _nakshatra_pada(lon_k)
                rows.append(PlanetRow(
                    obs_date=d.isoformat(), body="Ketu",
                    longitude_sidereal=round(lon_k, 6),
                    longitude_tropical=round(trop_k, 6),
                    speed=round(speed, 6), is_retrograde=True,
                    sign=sgn + 1, sign_name=SIGNS[sgn],
                    nakshatra=nk, nakshatra_name=NAKSHATRAS[nk - 1], pada=pk,
                ))
        return rows

    def moon_phase_for_date(self, d: date) -> MoonPhaseRow:
        jd = _julday(d)
        sun, _ = swe.calc_ut(jd, swe.SUN, self._flags_tropical)
        moon, _ = swe.calc_ut(jd, swe.MOON, self._flags_tropical)
        elong = (moon[0] - sun[0]) % 360.0               # 0..360
        illum = (1 - __import__("math").cos(__import__("math").radians(elong))) / 2
        tithi = int(elong // 12.0) + 1                   # 30 tithis of 12° each
        paksha = "Shukla" if elong < 180 else "Krishna"
        return MoonPhaseRow(
            obs_date=d.isoformat(), phase_angle=round(elong, 4),
            illumination=round(illum, 4), tithi=tithi, paksha=paksha,
        )

    def aspects_for_date(self, d: date) -> list[AspectRow]:
        planets = {p.body: p.longitude_sidereal for p in self.planets_for_date(d)}
        names = list(planets)
        out: list[AspectRow] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                diff = abs(planets[a] - planets[b]) % 360.0
                sep = min(diff, 360.0 - diff)            # 0..180
                out.append(AspectRow(d.isoformat(), a, b, round(sep, 4)))
        return out

    # --- agent entrypoint ---

    def run(self, ctx: RunContext) -> RunResult:
        start = ctx.start or date.today()
        end = ctx.end or start
        n_rows = 0
        sample_hashes: dict[str, str] = {}
        d = start
        while d <= end:
            planets = self.planets_for_date(d)
            self.moon_phase_for_date(d)
            self.aspects_for_date(d)
            n_rows += len(planets)
            if d == start:
                sample_hashes["first_day_planets"] = content_hash([asdict(p) for p in planets])
            # NOTE: persistence to planetary_data/moon_phase/planetary_aspects via the db layer
            # is wired in scripts/run_astronomy.py; kept out of the pure core for testability.
            d += timedelta(days=1)
        res = RunResult(agent=self.name, status="ok", rows_written=n_rows,
                        metrics={"days": (end - start).days + 1}, output_hashes=sample_hashes)
        res.write_manifest(ctx)
        log.info("astronomy: computed %d planet-rows over %s..%s", n_rows, start, end)
        return res

    def healthcheck(self) -> Health:
        try:
            self.planets_for_date(date(2024, 1, 1))
            return Health(ok=True, detail=f"swisseph {swe.version}")
        except Exception as e:  # pragma: no cover
            return Health(ok=False, detail=str(e))


# Sanity check: make this Agent-protocol-compatible at import time.
_: Agent = AstronomyCollector()  # type: ignore[assignment]
