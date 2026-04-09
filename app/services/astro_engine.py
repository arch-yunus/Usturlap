import swisseph as swe
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse

# Planet constants from swisseph
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON,
    "Lilith": swe.MEAN_APOG,
    "North Node": swe.MEAN_NODE,
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ASPECTS = [
    {"name": "Conjunction", "angle": 0, "orb": 10},
    {"name": "Opposition", "angle": 180, "orb": 10},
    {"name": "Trine", "angle": 120, "orb": 8},
    {"name": "Square", "angle": 90, "orb": 8},
    {"name": "Sextile", "angle": 60, "orb": 6},
]

class AstroEngine:
    def __init__(self, ephe_path: str = "ephe"):
        self.ephe_path = ephe_path
        # Ensure path is absolute for swisseph
        abs_path = os.path.abspath(ephe_path)
        swe.set_ephe_path(abs_path)

    def get_julian_day(self, dt: datetime) -> float:
        """Convert datetime to Julian Day (ET)."""
        # Swiss Ephemeris uses UTC by default if not specified otherwise
        # Input datetime should be UTC
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def get_sign(self, degree: float) -> str:
        """Get zodiac sign name from degree (0-360)."""
        index = int(degree / 30) % 12
        return ZODIAC_SIGNS[index]

    def get_degree_in_sign(self, degree: float) -> float:
        """Get degree within the 30-degree sign (0-30)."""
        return degree % 30

    def calculate_chart(self, dt: datetime, lat: float, lon: float, house_system: str = 'P') -> Dict[str, Any]:
        """Core calculation for a natal chart."""
        jd = self.get_julian_day(dt)
        
        # House calculation
        # house_system: 'P' for Placidus, 'K' for Koch, etc.
        # swe.houses_ex returns (cusps, ascmc)
        # cusps is array of 13 (index 0 is unused)
        # ascmc is (asc, mc, armc, vertex, ...)
        hsys_code = house_system[0].upper().encode('utf-8')
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys_code)
        
        ascendant = {
            "sign": self.get_sign(ascmc[0]),
            "degree": round(self.get_degree_in_sign(ascmc[0]), 2)
        }
        
        mc = {
            "sign": self.get_sign(ascmc[1]),
            "degree": round(self.get_degree_in_sign(ascmc[1]), 2)
        }

        planets_data = []
        for name, swe_id in PLANETS.items():
            # swe.calc_ut returns (data, status) 
            # data is (long, lat, dist, speed_long, ...)
            res, status = swe.calc_ut(jd, swe_id)
            long = res[0]
            speed = res[3]
            
            # Find which house the planet is in
            # Basically compare long with cusps
            # Minimal implementation of house detection
            house_num = self._get_house_for_long(long, cusps)

            planets_data.append(PlanetData(
                name=name,
                sign=self.get_sign(long),
                degree=round(self.get_degree_in_sign(long), 2),
                house=house_num,
                is_retrograde=speed < 0
            ))

        # Calculate Aspects
        aspects = self._calculate_aspects(planets_data)

        return {
            "ascendant": ascendant,
            "midheaven": mc,
            "planets": planets_data,
            "aspects": aspects
        }

    def calculate_synastry(self, chart1_data: Dict[str, Any], chart2_data: Dict[str, Any]) -> List[AspectData]:
        """Calculate aspects between two different charts."""
        return self._calculate_aspects(chart1_data["planets"], chart2_data["planets"])

    def calculate_transits(self, natal_dt: datetime, lat: float, lon: float, transit_dt: datetime, house_system: str = 'P') -> List[PlanetData]:
        """Calculate current (transit) planet positions within natal houses."""
        natal_jd = self.get_julian_day(natal_dt)
        transit_jd = self.get_julian_day(transit_dt)
        
        # Get natal houses
        hsys_code = house_system[0].upper().encode('utf-8')
        cusps, _ = swe.houses_ex(natal_jd, lat, lon, hsys_code)
        
        transit_planets = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(transit_jd, swe_id)
            long = res[0]
            speed = res[3]
            
            # Find which NATAL house the TRANSIT planet is in
            house_num = self._get_house_for_long(long, cusps)

            transit_planets.append(PlanetData(
                name=name,
                sign=self.get_sign(long),
                degree=round(self.get_degree_in_sign(long), 2),
                house=house_num,
                is_retrograde=speed < 0
            ))
        return transit_planets

    def _get_house_for_long(self, long: float, cusps: List[float]) -> int:
        """Helper to find the house number (1-12) for a given longitude."""
        for i in range(1, 12):
            c1 = cusps[i]
            c2 = cusps[i+1]
            if c1 < c2:
                if c1 <= long < c2: return i
            else: # House cross 0 degrees
                if long >= c1 or long < c2: return i
        return 12

    def _calculate_aspects(self, planets_a: List[PlanetData], planets_b: Optional[List[PlanetData]] = None) -> List[AspectData]:
        """
        Aspect engine that supports both natal (single list) and synastry (two lists).
        """
        results = []
        
        # If planets_b is None, we calculate aspects within planets_a (Natal)
        if planets_b is None:
            # Natal aspects
            for i in range(len(planets_a)):
                for j in range(i + 1, len(planets_a)):
                    self._add_aspect_if_exists(planets_a[i], planets_a[j], results)
        else:
            # Synastry aspects (pA vs pB)
            for p1 in planets_a:
                for p2 in planets_b:
                    self._add_aspect_if_exists(p1, p2, results)
        return results

    def _add_aspect_if_exists(self, p1: PlanetData, p2: PlanetData, results: List[AspectData]):
        # Full degrees (0-360)
        d1 = self._to_full_degree(p1.sign, p1.degree)
        d2 = self._to_full_degree(p2.sign, p2.degree)
        
        diff = abs(d1 - d2)
        if diff > 180: diff = 360 - diff
        
        for aspect in ASPECTS:
            orb_val = abs(diff - aspect["angle"])
            if orb_val <= aspect["orb"]:
                results.append(AspectData(
                    planet_1=p1.name,
                    planet_2=p2.name,
                    aspect_type=aspect["name"],
                    orb=round(orb_val, 2)
                ))

    def _to_full_degree(self, sign: str, degree: float) -> float:
        try:
            index = ZODIAC_SIGNS.index(sign)
            return index * 30 + degree
        except ValueError:
            return 0.0
