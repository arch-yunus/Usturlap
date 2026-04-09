from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
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
from app.services.report_service import PDFReportService
from app.services.database_manager import DatabaseManager
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
engine = AstroEngine()
ai_service = AIService()
symbol_service = SabianSymbolService()
drawing_service = SVGChartService()
builtin_interpret = BuiltinInterpretationService()
report_service = PDFReportService()
db = DatabaseManager()

class SaveChartRequest(BaseModel):
    name: str
    datetime: datetime
    lat: float
    lon: float
    house_system: str = "placidus"
    notes: Optional[str] = ""

@router.on_event("startup")
async def startup():
    await db.initialize()

@router.post("/charts")
async def save_chart(req: SaveChartRequest):
    try:
        return await db.save_chart(req.name, req.datetime, req.lat, req.lon, req.house_system, req.notes)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/charts")
async def get_charts():
    try: return await db.get_charts()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.delete("/charts/{chart_id}")
async def delete_chart(chart_id: int):
    try: return await db.delete_chart(chart_id)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# ... Previous Calculation Endpoints ...
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

@router.get("/chart/report/pdf")
async def get_pdf_report(datetime_str: str = Query(...), lat: float = Query(...), lon: float = Query(...), system: str = Query("placidus"), lang: str = Query("tr")):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"), lang=lang)
        chart_data = _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
        pdf_buffer = report_service.generate_report(chart_data, builtin_interpret.get_base_interpretation(chart_data, lang=lang))
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=usturlap_report.pdf"})
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get("/chart/draw")
async def draw_chart(datetime_str: str = Query(...), lat: float = Query(...), lon: float = Query(...), system: str = Query("placidus"), lang: str = Query("tr")):
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        res = engine.calculate_chart(dt, lat, lon, HOUSE_SYSTEMS.get(system.lower(), "P"), lang=lang)
        chart_data = _enhance(ChartResponse(meta=MetaData(datetime=dt, location=Location(lat=lat, lon=lon), house_system=system), **res))
        return Response(content=drawing_service.draw_chart(chart_data), media_type="image/svg+xml")
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/interpret", response_model=AIInterpretationResponse)
async def interpret(req: AIInterpretationRequest, lang: str = Query("tr")):
    try:
        base = builtin_interpret.get_base_interpretation(req.chart_data, lang=lang)
        ai_res = await ai_service.get_interpretation(req.chart_data, req.interpretation_type)
        return AIInterpretationResponse(interpretation=f"{base}\n\n{ai_res.interpretation}", model_used=ai_res.model_used, structured_insights=ai_res.structured_insights)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
