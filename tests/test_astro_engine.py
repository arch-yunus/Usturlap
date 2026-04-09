import pytest
from datetime import datetime
from app.services.astro_engine import AstroEngine

def test_julian_day_conversion():
    engine = AstroEngine()
    # Test for J2000 epoch: 2000-01-01 12:00:00 UTC -> JD 2451545.0
    dt = datetime(2000, 1, 1, 12, 0, 0)
    jd = engine.get_julian_day(dt)
    assert jd == pytest.approx(2451545.0, rel=1e-7)

def test_sign_calculation():
    engine = AstroEngine()
    assert engine.get_sign(0) == "Aries"
    assert engine.get_sign(30) == "Taurus"
    assert engine.get_sign(359) == "Pisces"

def test_degree_in_sign():
    engine = AstroEngine()
    assert engine.get_degree_in_sign(35.5) == pytest.approx(5.5)
    assert engine.get_degree_in_sign(0) == 0
    assert engine.get_degree_in_sign(360) == 0
