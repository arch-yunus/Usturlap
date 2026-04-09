from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Location(BaseModel):
    lat: float = Field(..., example=41.0082)
    lon: float = Field(..., example=28.9784)

class DignityData(BaseModel):
    rulership: bool = False
    exaltation: bool = False
    detriment: bool = False
    fall: bool = False
    score: int = 0  # Essential dignity score

class SabianSymbolData(BaseModel):
    degree_label: str
    symbol: str

class PlanetData(BaseModel):
    name: str
    sign: str
    degree: float
    house: int
    is_retrograde: bool
    dignity: Optional[DignityData] = None
    sabian_symbol: Optional[SabianSymbolData] = None

class AspectData(BaseModel):
    planet_1: str
    planet_2: str
    aspect_type: str
    orb: float

class MetaData(BaseModel):
    datetime: datetime
    location: Location
    house_system: str

class LotData(BaseModel):
    name: str # Lot of Fortune, Spirit, etc.
    sign: str
    degree: float

class FixedStarData(BaseModel):
    name: str # Regulus, Aldebaran, etc.
    sign: str
    degree: float
    distance_to_planet: Optional[float] = None
    connected_planet: Optional[str] = None

class ChartResponse(BaseModel):
    meta: MetaData
    ascendant: Dict[str, Any]
    planets: List[PlanetData]
    aspects: List[AspectData]
    midpoints: Optional[List[Dict[str, Any]]] = None
    lots: Optional[List[LotData]] = None
    fixed_stars: Optional[List[FixedStarData]] = None

class ChartRequest(BaseModel):
    datetime: datetime
    lat: float
    lon: float
    house_system: str = "placidus"
    zodiac_type: str = "tropical"

class SynastryRequest(BaseModel):
    person_1: ChartRequest
    person_2: ChartRequest

class SynastryResponse(BaseModel):
    person_1_chart: ChartResponse
    person_2_chart: ChartResponse
    compatibility_aspects: List[AspectData]

class TransitRequest(BaseModel):
    natal: ChartRequest
    transit_datetime: datetime

class TransitResponse(BaseModel):
    natal_chart: ChartResponse
    transit_planets: List[PlanetData] 

class ProgressionRequest(BaseModel):
    natal: ChartRequest
    target_date: datetime 

class SolarReturnRequest(BaseModel):
    natal: ChartRequest
    return_year: int 

class HarmonicRequest(BaseModel):
    natal: ChartRequest
    harmonic_number: int # 9 for Navamsa, etc.

class LocalityRequest(BaseModel):
    natal: ChartRequest
    planet: str # The planet we want to map lines for

class PlanetaryHourResponse(BaseModel):
    hour_ruler: str
    day_ruler: str
    is_daytime: bool

class AIInterpretationRequest(BaseModel):
    chart_data: ChartResponse
    interpretation_type: str = "professional"  # professional, archetypal, psychological

class AIInterpretationResponse(BaseModel):
    interpretation: str
    model_used: str
    structured_insights: Dict[str, Any]
