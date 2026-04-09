from fastapi import APIRouter, HTTPException, Query, Response
from app.models.chart import (
    ChartRequest, ChartResponse, MetaData, Location, 
    SynastryRequest, SynastryResponse, TransitRequest, TransitResponse,
    AIInterpretationRequest, AIInterpretationResponse,
    ProgressionRequest, SolarReturnRequest, PlanetaryHourResponse,
    HarmonicRequest, SolarArcRequest, LocalityRequest,
    TransitTimelineRequest, TransitTimelineResponse
)
from app.services.astro_engine import AstroEngine
from app.services.ai_service import AIService
from app.services.symbol_service import SabianSymbolService
from app.services.chart_drawing import SVGChartService
from app.services.interpretation_engine import BuiltinInterpretationService
from datetime import datetime

router = APIRouter()
engine = AstroEngine()
ai_service = AIService()
symbol_service = SabianSymbolService()
drawing_service = SVGChartService()
builtin_interpret = BuiltinInterpretationService()

HOUSE_SYSTEMS = {"placidus": "P", "koch": "K", "campanus": "C", "regiomontanus": "R", "whole_sign": "W", "equal": "E", "porphyry": "O"}

def _enhance(chart: ChartResponse) -> ChartResponse:
    for p in chart.planets: p.sabian_symbol = symbol_service.get_symbol(p.sign, p.degree)
    return chart

@router.get("/chart", response_model=ChartResponse)
async def get_chart(
    datetime_str: str = Query(..., alias="datetime"), 
    lat: float = Query(...), lon: float = Query(...), 
    system: str = Query("placidus"), 
    heliocentric: bool = Query(False),
    lang: str = Query("tr")
):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"), is_hel=heliocentric, lang=lang)
        return _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/interpret", response_model=AIInterpretationResponse)
async def interpret(req: AIInterpretationRequest, lang: str = Query("tr")):
    """
    Generate an interpretation for the provided chart data.
    Uses a hybrid approach: Built-in rule engine + AI scaffolding.
    """
    try:
        base_text = builtin_interpret.get_base_interpretation(req.chart_data, lang=lang)
        ai_res = await ai_service.get_interpretation(req.chart_data, req.interpretation_type)
        
        return AIInterpretationResponse(
            interpretation=f"{base_text}\n\n---\n\n{ai_res.interpretation}",
            model_used=ai_res.model_used,
            structured_insights=ai_res.structured_insights
        )
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart/draw")
async def draw_chart(
    datetime_str: str = Query(..., alias="datetime"), 
    lat: float = Query(...), lon: float = Query(...), 
    system: str = Query("placidus"),
    lang: str = Query("tr")
):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"), lang=lang)
        chart_data = _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
        return Response(content=drawing_service.draw_chart(chart_data), media_type="image/svg+xml")
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/transits/timeline", response_model=TransitTimelineResponse)
async def transit_timeline(req: TransitTimelineRequest):
    try:
        timeline = engine.calculate_transit_timeline(req.natal.datetime, req.natal.lat, req.natal.lon, req.days, lang=req.lang)
        return TransitTimelineResponse(
            natal_meta=MetaData(datetime=req.natal.datetime, location=Location(lat=req.natal.lat, lon=req.natal.lon), house_system=req.natal.house_system),
            timeline=timeline
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/synastry", response_model=SynastryResponse)
async def synastry(req: SynastryRequest, lang: str = Query("tr")):
    try:
        c1 = engine.calculate_chart(req.person_1.datetime, req.person_1.lat, req.person_1.lon, HOUSE_SYSTEMS.get(req.person_1.house_system.lower(), "P"), req.person_1.is_heliocentric, lang=lang)
        c2 = engine.calculate_chart(req.person_2.datetime, req.person_2.lat, req.person_2.lon, HOUSE_SYSTEMS.get(req.person_2.house_system.lower(), "P"), req.person_2.is_heliocentric, lang=lang)
        return SynastryResponse(
            person_1_chart=_enhance(ChartResponse(meta=MetaData(datetime=req.person_1.datetime, location=Location(lat=req.person_1.lat, lon=req.person_1.lon), house_system=req.person_1.house_system), **c1)),
            person_2_chart=_enhance(ChartResponse(meta=MetaData(datetime=req.person_2.datetime, location=Location(lat=req.person_2.lat, lon=req.person_2.lon), house_system=req.person_2.house_system), **c2)),
            compatibility_aspects=engine._calculate_aspects(c1["planets"], c2["planets"], lang=lang)
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))
