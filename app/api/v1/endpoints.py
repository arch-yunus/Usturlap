from fastapi import APIRouter, HTTPException, Query
from app.models.chart import (
    ChartRequest, ChartResponse, MetaData, Location, 
    SynastryRequest, SynastryResponse, TransitRequest, TransitResponse,
    AIInterpretationRequest, AIInterpretationResponse,
    ProgressionRequest, SolarReturnRequest, PlanetaryHourResponse
)
from app.services.astro_engine import AstroEngine
from app.services.ai_service import AIService
from app.services.symbol_service import SabianSymbolService
from datetime import datetime

router = APIRouter()
engine = AstroEngine()
ai_service = AIService()
symbol_service = SabianSymbolService()

HOUSE_SYSTEMS = {
    "placidus": "P", "koch": "K", "campanus": "C", 
    "regiomontanus": "R", "whole_sign": "W", "equal": "E", "porphyry": "O"
}

def _enhance_with_symbols(chart: ChartResponse) -> ChartResponse:
    for planet in chart.planets:
        planet.sabian_symbol = symbol_service.get_symbol(planet.sign, planet.degree)
    return chart

@router.get("/chart", response_model=ChartResponse)
async def get_chart(
    datetime_str: str = Query(..., alias="datetime", example="2002-04-10T14:30:00Z"),
    lat: float = Query(..., example=41.0082),
    lon: float = Query(..., example=28.9784),
    system: str = Query("placidus", example="placidus")
):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        results = engine.calculate_chart(dt, lat, lon, house_system=HOUSE_SYSTEMS.get(system.lower(), "P"))
        response = ChartResponse(
            meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system),
            ascendant=results["ascendant"], planets=results["planets"],
            aspects=results["aspects"], midpoints=results["midpoints"]
        )
        return _enhance_with_symbols(response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/synastry", response_model=SynastryResponse)
async def get_synastry(request: SynastryRequest):
    try:
        c1 = engine.calculate_chart(request.person_1.datetime, request.person_1.lat, request.person_1.lon, HOUSE_SYSTEMS.get(request.person_1.house_system.lower(), "P"))
        c2 = engine.calculate_chart(request.person_2.datetime, request.person_2.lat, request.person_2.lon, HOUSE_SYSTEMS.get(request.person_2.house_system.lower(), "P"))
        comp = engine.calculate_synastry(c1, c2)
        return SynastryResponse(
            person_1_chart=_enhance_with_symbols(ChartResponse(meta=MetaData(datetime=request.person_1.datetime, location=Location(lat=request.person_1.lat, lon=request.person_1.lon), house_system=request.person_1.house_system), ascendant=c1["ascendant"], planets=c1["planets"], aspects=c1["aspects"], midpoints=c1["midpoints"])),
            person_2_chart=_enhance_with_symbols(ChartResponse(meta=MetaData(datetime=request.person_2.datetime, location=Location(lat=request.person_2.lat, lon=request.person_2.lon), house_system=request.person_2.house_system), ascendant=c2["ascendant"], planets=c2["planets"], aspects=c2["aspects"], midpoints=c2["midpoints"])),
            compatibility_aspects=comp
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/transits", response_model=TransitResponse)
async def get_transits(request: TransitRequest):
    try:
        natal = engine.calculate_chart(request.natal.datetime, request.natal.lat, request.natal.lon, HOUSE_SYSTEMS.get(request.natal.house_system.lower(), "P"))
        transits = engine.calculate_transits(request.natal.datetime, request.natal.lat, request.natal.lon, request.transit_datetime)
        return TransitResponse(
            natal_chart=_enhance_with_symbols(ChartResponse(meta=MetaData(datetime=request.natal.datetime, location=Location(lat=request.natal.lat, lon=request.natal.lon), house_system=request.natal.house_system), ascendant=natal["ascendant"], planets=natal["planets"], aspects=natal["aspects"], midpoints=natal["midpoints"])),
            transit_planets=transits
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/progressions", response_model=ChartResponse)
async def get_progressions(request: ProgressionRequest):
    try:
        res = engine.calculate_secondary_progressions(request.natal.datetime, request.target_date, request.natal.lat, request.natal.lon)
        response = ChartResponse(
            meta=MetaData(datetime=request.target_date, location=Location(lat=request.natal.lat, lon=request.natal.lon), house_system=request.natal.house_system),
            ascendant=res["ascendant"], planets=res["planets"], aspects=res["aspects"], midpoints=res["midpoints"]
        )
        return _enhance_with_symbols(response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/solar-return", response_model=ChartResponse)
async def get_solar_return(request: SolarReturnRequest):
    try:
        res = engine.calculate_solar_return(request.natal.datetime, request.return_year, request.natal.lat, request.natal.lon)
        response = ChartResponse(
            meta=MetaData(datetime=request.natal.datetime, location=Location(lat=request.natal.lat, lon=request.natal.lon), house_system=request.natal.house_system),
            ascendant=res["ascendant"], planets=res["planets"], aspects=res["aspects"], midpoints=res["midpoints"]
        )
        return _enhance_with_symbols(response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/planetary-hours", response_model=PlanetaryHourResponse)
async def get_hours(lat: float, lon: float):
    try:
        res = engine.calculate_planetary_hours(datetime.utcnow(), lat, lon)
        return PlanetaryHourResponse(hour_ruler=res["hour_ruler"], day_ruler=res["day_ruler"], is_daytime=res["is_daytime"])
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/interpret", response_model=AIInterpretationResponse)
async def interpret_chart(request: AIInterpretationRequest):
    try: return await ai_service.get_interpretation(request.chart_data, request.interpretation_type)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
