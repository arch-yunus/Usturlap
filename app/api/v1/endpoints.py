from fastapi import APIRouter, HTTPException, Query
from app.models.chart import (
    ChartRequest, ChartResponse, MetaData, Location, 
    SynastryRequest, SynastryResponse, TransitRequest, TransitResponse
)
from app.services.astro_engine import AstroEngine
from datetime import datetime

router = APIRouter()
engine = AstroEngine()

HOUSE_SYSTEMS = {
    "placidus": "P",
    "koch": "K",
    "campanus": "C",
    "regiomontanus": "R",
    "whole_sign": "W",
    "equal": "E",
    "porphyry": "O"
}

@router.get("/chart", response_model=ChartResponse)
async def get_chart(
    datetime_str: str = Query(..., alias="datetime", example="2002-04-10T14:30:00Z"),
    lat: float = Query(..., example=41.0082),
    lon: float = Query(..., example=28.9784),
    system: str = Query("placidus", example="placidus")
):
    """
    Calculate a natal chart for a given date, time, and location.
    """
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        hsys = HOUSE_SYSTEMS.get(system.lower(), "P")
        
        results = engine.calculate_chart(dt, lat, lon, house_system=hsys)
        
        return ChartResponse(
            meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system),
            ascendant=results["ascendant"],
            planets=results["planets"],
            aspects=results["aspects"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/synastry", response_model=SynastryResponse)
async def get_synastry(request: SynastryRequest):
    """
    Calculate compatibility aspects between two charts.
    """
    try:
        hsys1 = HOUSE_SYSTEMS.get(request.person_1.house_system.lower(), "P")
        hsys2 = HOUSE_SYSTEMS.get(request.person_2.house_system.lower(), "P")
        
        chart1 = engine.calculate_chart(request.person_1.datetime, request.person_1.lat, request.person_1.lon, hsys1)
        chart2 = engine.calculate_chart(request.person_2.datetime, request.person_2.lat, request.person_2.lon, hsys2)
        
        compatibility = engine.calculate_synastry(chart1, chart2)
        
        return SynastryResponse(
            person_1_chart=ChartResponse(
                meta=MetaData(datetime=request.person_1.datetime, location=Location(lat=request.person_1.lat, lon=request.person_1.lon), house_system=request.person_1.house_system),
                ascendant=chart1["ascendant"], planets=chart1["planets"], aspects=chart1["aspects"]
            ),
            person_2_chart=ChartResponse(
                meta=MetaData(datetime=request.person_2.datetime, location=Location(lat=request.person_2.lat, lon=request.person_2.lon), house_system=request.person_2.house_system),
                ascendant=chart2["ascendant"], planets=chart2["planets"], aspects=chart2["aspects"]
            ),
            compatibility_aspects=compatibility
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transits", response_model=TransitResponse)
async def get_transits(request: TransitRequest):
    """
    Calculate current planet positions relative to a natal chart.
    """
    try:
        hsys = HOUSE_SYSTEMS.get(request.natal.house_system.lower(), "P")
        
        natal_chart = engine.calculate_chart(request.natal.datetime, request.natal.lat, request.natal.lon, hsys)
        transit_planets = engine.calculate_transits(
            request.natal.datetime, request.natal.lat, request.natal.lon, 
            request.transit_datetime, hsys
        )
        
        return TransitResponse(
            natal_chart=ChartResponse(
                meta=MetaData(datetime=request.natal.datetime, location=Location(lat=request.natal.lat, lon=request.natal.lon), house_system=request.natal.house_system),
                ascendant=natal_chart["ascendant"], planets=natal_chart["planets"], aspects=natal_chart["aspects"]
            ),
            transit_planets=transit_planets
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
