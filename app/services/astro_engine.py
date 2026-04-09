import swisseph as swe
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData

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

# Essential Dignities Table
DIGNITIES_TABLE = {
    "Sun": {"rulership": ["Leo"], "exaltation": "Aries", "detriment": ["Aquarius"], "fall": "Libra"},
    "Moon": {"rulership": ["Cancer"], "exaltation": "Taurus", "detriment": ["Capricorn"], "fall": "Scorpio"},
    "Mercury": {"rulership": ["Gemini", "Virgo"], "exaltation": "Virgo", "detriment": ["Sagittarius", "Pisces"], "fall": "Pisces"},
    "Venus": {"rulership": ["Taurus", "Libra"], "exaltation": "Pisces", "detriment": ["Scorpio", "Aries"], "fall": "Virgo"},
    "Mars": {"rulership": ["Aries", "Scorpio"], "exaltation": "Capricorn", "detriment": ["Libra", "Taurus"], "fall": "Cancer"},
    "Jupiter": {"rulership": ["Sagittarius", "Pisces"], "exaltation": "Cancer", "detriment": ["Gemini", "Virgo"], "fall": "Capricorn"},
    "Saturn": {"rulership": ["Capricorn", "Aquarius"], "exaltation": "Libra", "detriment": ["Cancer", "Leo"], "fall": "Aries"},
}

class AstroEngine:
    def __init__(self, ephe_path: str = "ephe"):
        self.ephe_path = ephe_path
        abs_path = os.path.abspath(ephe_path)
        swe.set_ephe_path(abs_path)

    def get_julian_day(self, dt: datetime) -> float:
        """Convert datetime to Julian Day (ET)."""
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
            res, status = swe.calc_ut(jd, swe_id)
            long = res[0]
            speed = res[3]
            house_num = self._get_house_for_long(long, cusps)
            sign = self.get_sign(long)

            dignity = self.get_essential_dignity(name, sign)

            planets_data.append(PlanetData(
                name=name,
                sign=sign,
                degree=round(self.get_degree_in_sign(long), 2),
                house=house_num,
                is_retrograde=speed < 0,
                dignity=dignity
            ))

        midpoints = self.calculate_midpoints(planets_data)
        aspects = self._calculate_aspects(planets_data)

        return {
            "ascendant": ascendant,
            "midheaven": mc,
            "planets": planets_data,
            "aspects": aspects,
            "midpoints": midpoints
        }

    def get_essential_dignity(self, planet_name: str, sign: str) -> Optional[DignityData]:
        if planet_name not in DIGNITIES_TABLE:
            return None

        dig = DIGNITIES_TABLE[planet_name]
        is_ruler = sign in dig["rulership"]
        is_exalted = sign == dig["exaltation"]
        is_detriment = sign in dig["detriment"]
        is_fall = sign == dig["fall"]

        score = 0
        if is_ruler: score += 5
        if is_exalted: score += 4
        if is_detriment: score -= 5
        if is_fall: score -= 4

        return DignityData(
            rulership=is_ruler,
            exaltation=is_exalted,
            detriment=is_detriment,
            fall=is_fall,
            score=score
        )

    def calculate_midpoints(self, planets: List[PlanetData]) -> List[Dict[str, Any]]:
        midpoints = []
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                p1 = planets[i]
                p2 = planets[j]
                
                d1 = self._to_full_degree(p1.sign, p1.degree)
                d2 = self._to_full_degree(p2.sign, p2.degree)
                
                diff = abs(d1 - d2)
                mid_degree = (d1 + d2) / 2.0
                if diff > 180:
                    mid_degree = (mid_degree + 180.0) % 360.0
                
                midpoints.append({
                    "planets": [p1.name, p2.name],
                    "sign": self.get_sign(mid_degree),
                    "degree": round(self.get_degree_in_sign(mid_degree), 2)
                })
        return midpoints

    def calculate_synastry(self, natal1: Dict[str, Any], natal2: Dict[str, Any]) -> List[AspectData]:
        return self._calculate_aspects(natal1["planets"], natal2["planets"])

    def calculate_transits(self, natal_dt: datetime, lat: float, lon: float, transit_dt: datetime, house_system: str = 'P') -> List[PlanetData]:
        natal_jd = self.get_julian_day(natal_dt)
        transit_jd = self.get_julian_day(transit_dt)
        
        hsys_code = house_system[0].upper().encode('utf-8')
        cusps, _ = swe.houses_ex(natal_jd, lat, lon, hsys_code)
        
        transit_planets = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(transit_jd, swe_id)
            long = res[0]
            speed = res[3]
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
        for i in range(1, 12):
            c1 = cusps[i]
            c2 = cusps[i+1]
            if c1 < c2:
                if c1 <= long < c2: return i
            else:
                if long >= c1 or long < c2: return i
        return 12

    def _calculate_aspects(self, planets_a: List[PlanetData], planets_b: Optional[List[PlanetData]] = None) -> List[AspectData]:
        results = []
        if planets_b is None:
            for i in range(len(planets_a)):
                for j in range(i + 1, len(planets_a)):
                    self._add_aspect_if_exists(planets_a[i], planets_a[j], results)
        else:
            for p1 in planets_a:
                for p2 in planets_b:
                    self._add_aspect_if_exists(p1, p2, results)
        return results

    def _add_aspect_if_exists(self, p1: PlanetData, p2: PlanetData, results: List[AspectData]):
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
