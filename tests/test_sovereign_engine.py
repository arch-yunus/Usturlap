import pytest
from datetime import datetime
from app.services.astro_engine import AstroEngine

@pytest.fixture
def engine():
    return AstroEngine(ephe_path="ephe")

def test_natal_chart_accuracy(engine):
    # Testing for a known date: April 10, 2002
    dt = datetime(2002, 4, 10, 14, 30)
    lat, lon = 41.0082, 28.9784
    res = engine.calculate_chart(dt, lat, lon)
    
    # Sun should be in Aries
    sun = next(p for p in res["planets"] if p.name in ["Sun", "Güneş"])
    assert "Aries" in sun.sign or "Koç" in sun.sign

def test_essential_dignity_leo_sun(engine):
    dt = datetime(2024, 8, 1, 12, 0) # Sun in Leo
    res = engine.calculate_chart(dt, 0, 0)
    sun = next(p for p in res["planets"] if p.name in ["Sun", "Güneş"])
    assert sun.dignity.rulership == True
    assert sun.dignity.score == 5

def test_lots_calculation(engine):
    dt = datetime(2002, 4, 10, 14, 30)
    res = engine.calculate_chart(dt, 41, 28)
    assert len(res["lots"]) >= 2
    assert "Lot of Fortune" in [l.name for l in res["lots"]]

def test_i18n_support(engine):
    dt = datetime(2024, 1, 1, 12, 0)
    res_tr = engine.calculate_chart(dt, 0, 0, lang="tr")
    res_en = engine.calculate_chart(dt, 0, 0, lang="en")
    
    # Checking if sign name changed
    sign_tr = res_tr["planets"][0].sign
    sign_en = res_en["planets"][0].sign
    assert sign_tr != sign_en
