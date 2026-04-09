from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class Location(BaseModel):
    lat: float = Field(..., example=41.0082)
    lon: float = Field(..., example=28.9784)

class PlanetData(BaseModel):
    name: str
    sign: str
    degree: float
    house: int
    is_retrograde: bool

class AspectData(BaseModel):
    planet_1: str
    planet_2: str
    aspect_type: str
    orb: float

class MetaData(BaseModel):
    datetime: datetime
    location: Location
    house_system: str

class ChartResponse(BaseModel):
    meta: MetaData
    ascendant: Dict[str, any]
    planets: List[PlanetData]
    aspects: List[AspectData]

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
    transit_planets: List[PlanetData] # Current positions relative to natal chart
