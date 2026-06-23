"""Tests for the Astronomy Collector — verify against known Vedic positions for 2024-01-01."""
from datetime import date

from astroquant.collectors.astronomy import AstronomyCollector


def test_healthcheck():
    assert AstronomyCollector().healthcheck().ok


def test_planet_count_includes_ketu():
    col = AstronomyCollector()
    rows = col.planets_for_date(date(2024, 1, 1))
    bodies = {r.body for r in rows}
    # 8 base bodies + Ketu derived
    assert "Ketu" in bodies
    assert {"Sun", "Moon", "Jupiter", "Saturn", "Rahu", "Ketu"} <= bodies
    assert len(rows) == 9


def test_longitudes_in_range():
    col = AstronomyCollector()
    for r in col.planets_for_date(date(2024, 1, 1)):
        assert 0.0 <= r.longitude_sidereal < 360.0
        assert 1 <= r.sign <= 12
        assert 1 <= r.nakshatra <= 27
        assert 1 <= r.pada <= 4


def test_known_positions_2024():
    """Sanity vs published Vedic ephemeris (Lahiri) for 1 Jan 2024."""
    col = AstronomyCollector()
    by = {r.body: r for r in col.planets_for_date(date(2024, 1, 1))}
    assert by["Jupiter"].sign_name == "Aries"        # Jupiter in Mesha in early 2024
    assert by["Saturn"].sign_name == "Aquarius"      # Saturn in Kumbha through 2024
    assert by["Sun"].sign_name == "Sagittarius"      # Sun sidereal Sag late Dec–mid Jan
    assert by["Rahu"].sign_name == "Pisces"          # Rahu in Meena early 2024
    # Rahu and Ketu always 180 deg apart
    assert abs(((by["Rahu"].longitude_sidereal - by["Ketu"].longitude_sidereal) % 360) - 180) < 1e-6


def test_sun_never_retrograde():
    col = AstronomyCollector()
    by = {r.body: r for r in col.planets_for_date(date(2024, 6, 15))}
    assert by["Sun"].is_retrograde is False
    assert by["Rahu"].is_retrograde is True          # nodes are always retrograde


def test_moon_phase_consistency():
    col = AstronomyCollector()
    mp = col.moon_phase_for_date(date(2024, 1, 1))
    assert 0.0 <= mp.phase_angle < 360.0
    assert 0.0 <= mp.illumination <= 1.0
    assert 1 <= mp.tithi <= 30
    assert mp.paksha in ("Shukla", "Krishna")


def test_aspects_symmetric_range():
    col = AstronomyCollector()
    for a in col.aspects_for_date(date(2024, 1, 1)):
        assert 0.0 <= a.angle_deg <= 180.0
