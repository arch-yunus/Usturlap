from fastapi import APIRouter, HTTPException, Query, Response
from app.models.chart import (
    ChartRequest, ChartResponse, MetaData, Location, 
    SynastryRequest, SynastryResponse, TransitRequest, TransitResponse,
    AIInterpretationRequest, AIInterpretationResponse,
    ProgressionRequest, SolarReturnRequest, PlanetaryHourResponse,
    HarmonicRequest, SolarArcRequest, LocalityRequest
)
from app.services.astro_engine import AstroEngine
from app.services.ai_service import AIService
from app.services.symbol_service import SabianSymbolService
from app.services.chart_drawing import SVGChartService
from datetime import datetime

router = APIRouter()
engine = AstroEngine()
ai_service = AIService()
symbol_service = SabianSymbolService()
drawing_service = SVGChartService()

HOUSE_SYSTEMS = {"placidus": "P", "koch": "K", "campanus": "C", "regiomontanus": "R", "whole_sign": "W", "equal": "E", "porphyry": "O"}

def _enhance(chart: ChartResponse) -> ChartResponse:
    for p in chart.planets: p.sabian_symbol = symbol_service.get_symbol(p.sign, p.degree)
    return chart

@router.get("/chart", response_model=ChartResponse)
async def get_chart(
    datetime_str: str = Query(..., alias="datetime"), 
    lat: float = Query(...), lon: float = Query(...), 
    system: str = Query("placidus"), 
    heliocentric: bool = Query(False)
):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"), is_heliocentric=heliocentric)
        return _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/chart/draw")
async def draw_chart(
    datetime_str: str = Query(..., alias="datetime"), 
    lat: float = Query(...), lon: float = Query(...), 
    system: str = Query("placidus")
):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"))
        chart_data = _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
        svg_content = drawing_service.draw_chart(chart_data)
        return Response(content=svg_content, media_type="image/svg+xml")
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/synastry", response_model=SynastryResponse)
async def synastry(req: SynastryRequest):
    try:
        c1 = engine.calculate_chart(req.person_1.datetime, req.person_1.lat, req.person_1.lon, HOUSE_SYSTEMS.get(req.person_1.house_system.lower(), "P"), req.person_1.is_heliocentric)
        c2 = engine.calculate_chart(req.person_2.datetime, req.person_2.lat, req.person_2.lon, HOUSE_SYSTEMS.get(req.person_2.house_system.lower(), "P"), req.person_2.is_heliocentric)
        return SynastryResponse(
            person_1_chart=_enhance(ChartResponse(meta=MetaData(datetime=req.person_1.datetime, location=Location(lat=req.person_1.lat, lon=req.person_1.lon), house_system=req.person_1.house_system), **c1)),
            person_2_chart=_enhance(ChartResponse(meta=MetaData(datetime=req.person_2.datetime, location=Location(lat=req.person_2.lat, lon=req.person_2.lon), house_system=req.person_2.house_system), **c2)),
            compatibility_aspects=engine.calculate_synastry(c1, c2)
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/transits", response_model=TransitResponse)
async def transits(req: TransitRequest):
    try:
        natal = engine.calculate_chart(req.natal.datetime, req.natal.lat, req.natal.lon, HOUSE_SYSTEMS.get(req.natal.house_system.lower(), "P"), req.natal.is_heliocentric)
        return TransitResponse(
            natal_chart=_enhance(ChartResponse(meta=MetaData(datetime=req.natal.datetime, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system), **natal)),
            transit_planets=engine.calculate_transits(req.natal.datetime, req.natal.lat, req.natal.lon, req.transit_datetime)
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/harmonic", response_model=ChartResponse)
async def harmonic(req: HarmonicRequest):
    try:
        res = engine.calculate_harmonic_chart(req.natal.datetime, req.natal.lat, req.natal.lon, req.harmonic_number)
        return _enhance(ChartResponse(meta=MetaData(datetime=req.natal.datetime, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/solar-arcs", response_model=ChartResponse)
async def solar_arcs(req: SolarArcRequest):
    try:
        res = engine.calculate_solar_arc_directions(req.natal.datetime, req.target_date, req.natal.lat, req.natal.lon)
        return _enhance(ChartResponse(meta=MetaData(datetime=req.target_date, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/progressions", response_model=ChartResponse)
async def progressions(req: ProgressionRequest):
    try:
        res = engine.calculate_secondary_progressions(req.natal.datetime, req.target_date, req.natal.lat, req.natal.lon)
        return _enhance(ChartResponse(meta=MetaData(datetime=req.target_date, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/solar-return", response_model=ChartResponse)
async def solar_return(req: SolarReturnRequest):
    try:
        res = engine.calculate_solar_return(req.natal.datetime, req.return_year, req.natal.lat, req.natal.lon)
        return _enhance(ChartResponse(meta=MetaData(datetime=req.natal.datetime, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/locality", response_model=list)
async def locality(lat: float, lon: float, datetime_str: str = Query(..., alias="datetime"), planet: str = "Sun"):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return engine.calculate_locality_lines(dt, planet)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/planetary-hours", response_model=PlanetaryHourResponse)
async def hours(lat: float, lon: float):
    try:
        res = engine.calculate_planetary_hours(datetime.utcnow(), lat, lon)
        return PlanetaryHourResponse(**res)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/interpret", response_model=AIInterpretationResponse)
async def interpret(req: AIInterpretationRequest):
    try: return await ai_service.get_interpretation(req.chart_data, req.interpretation_type)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
