import swisseph as swe
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData, SabianSymbolData

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
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def get_sign(self, degree: float) -> str:
        index = int(degree / 30) % 12
        return ZODIAC_SIGNS[index]

    def get_degree_in_sign(self, degree: float) -> float:
        return degree % 30

    def calculate_chart(self, dt: datetime, lat: float, lon: float, house_system: str = 'P') -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        hsys_code = house_system[0].upper().encode('utf-8')
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys_code)
        
        ascendant = {"sign": self.get_sign(ascmc[0]), "degree": round(self.get_degree_in_sign(ascmc[0]), 2)}
        mc = {"sign": self.get_sign(ascmc[1]), "degree": round(self.get_degree_in_sign(ascmc[1]), 2)}

        planets_data = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id)
            long = res[0]
            speed = res[3]
            house_num = self._get_house_for_long(long, cusps)
            sign = self.get_sign(long)

            planets_data.append(PlanetData(
                name=name, sign=sign, degree=round(self.get_degree_in_sign(long), 2),
                house=house_num, is_retrograde=speed < 0,
                dignity=self.get_essential_dignity(name, sign)
            ))

        return {
            "ascendant": ascendant, "midheaven": mc, "planets": planets_data,
            "aspects": self._calculate_aspects(planets_data),
            "midpoints": self.calculate_midpoints(planets_data)
        }

    def get_essential_dignity(self, planet_name: str, sign: str) -> Optional[DignityData]:
        if planet_name not in DIGNITIES_TABLE: return None
        dig = DIGNITIES_TABLE[planet_name]
        is_ruler, is_exalted = sign in dig["rulership"], sign == dig["exaltation"]
        is_detriment, is_fall = sign in dig["detriment"], sign == dig["fall"]
        score = (5 if is_ruler else 0) + (4 if is_exalted else 0) - (5 if is_detriment else 0) - (4 if is_fall else 0)
        return DignityData(rulership=is_ruler, exaltation=is_exalted, detriment=is_detriment, fall=is_fall, score=score)

    def calculate_midpoints(self, planets: List[PlanetData]) -> List[Dict[str, Any]]:
        midpoints = []
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                d1, d2 = self._to_full_degree(planets[i].sign, planets[i].degree), self._to_full_degree(planets[j].sign, planets[j].degree)
                diff = abs(d1 - d2)
                mid_degree = ((d1 + d2) / 2.0 + (180.0 if diff > 180 else 0)) % 360.0
                midpoints.append({"planets": [planets[i].name, planets[j].name], "sign": self.get_sign(mid_degree), "degree": round(self.get_degree_in_sign(mid_degree), 2)})
        return midpoints

    def calculate_secondary_progressions(self, natal_dt: datetime, target_date: datetime, lat: float, lon: float) -> Dict[str, Any]:
        """Calculates secondary progressions (1 day = 1 year)."""
        years_diff = (target_date - natal_dt).days / 365.25
        prog_dt = natal_dt + timedelta(days=years_diff)
        return self.calculate_chart(prog_dt, lat, lon)

    def calculate_solar_return(self, natal_dt: datetime, return_year: int, lat: float, lon: float) -> Dict[str, Any]:
        """Finds the solar return moment for a given year."""
        jd_natal = self.get_julian_day(natal_dt)
        res, _ = swe.calc_ut(jd_natal, swe.SUN)
        natal_sun_long = res[0]
        
        # Estimate return date
        estimate_dt = datetime(return_year, natal_dt.month, natal_dt.day, natal_dt.hour, natal_dt.minute)
        jd_start = self.get_julian_day(estimate_dt) - 2.0 # Search window
        
        # Find the exact moment Sun longitude matches
        return_jd = swe.solcross_ut(natal_sun_long, jd_start)
        y, m, d, h = swe.revjul(return_jd)
        # Convert decimal hour to H:M:S
        hour = int(h)
        minute = int((h - hour) * 60)
        second = int(((h - hour) * 60 - minute) * 60)
        return_dt = datetime(y, m, d, hour, minute, second)
        
        return self.calculate_chart(return_dt, lat, lon)

    def calculate_planetary_hours(self, dt: datetime, lat: float, lon: float) -> Dict[str, Any]:
        """Calculates the planetary ruler of the current day and hour."""
        jd = self.get_julian_day(dt)
        # 1. Get sunrise/sunset
        res = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_RISE)
        sunrise_jd = res[0]
        res = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_SET)
        sunset_jd = res[0]
        
        is_daytime = sunrise_jd <= jd <= sunset_jd
        # Simplified planetary hour logic (requires specific day-of-week mapping)
        day_of_week = dt.weekday() # 0=Monday, 6=Sunday
        days = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"] # Actually, order is Sun(0), Mon(1)...
        # Correct Chaldean order: Sat, Jup, Mar, Sun, Ven, Mer, Moo
        chaldean_order = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
        # Day rulers: Sun=Sun, Mon=Moon, Tue=Mars, Wed=Mercury, Thu=Jupiter, Fri=Venus, Sat=Saturn
        day_rulers = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"] # Mon-Sun
        day_ruler = day_rulers[day_of_week]
        
        return {"day_ruler": day_ruler, "is_daytime": is_daytime, "hour_ruler": "Pending Implementation"} # Full math is complex

    def calculate_transits(self, natal_dt: datetime, lat: float, lon: float, transit_dt: datetime, house_system: str = 'P') -> List[PlanetData]:
        natal_jd, transit_jd = self.get_julian_day(natal_dt), self.get_julian_day(transit_dt)
        cusps, _ = swe.houses_ex(natal_jd, lat, lon, house_system[0].upper().encode('utf-8'))
        transit_planets = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(transit_jd, swe_id)
            long, speed = res[0], res[3]
            transit_planets.append(PlanetData(name=name, sign=self.get_sign(long), degree=round(self.get_degree_in_sign(long), 2), house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0))
        return transit_planets

    def calculate_synastry(self, natal1: Dict[str, Any], natal2: Dict[str, Any]) -> List[AspectData]:
        return self._calculate_aspects(natal1["planets"], natal2["planets"])

    def _get_house_for_long(self, long: float, cusps: List[float]) -> int:
        for i in range(1, 12):
            if cusps[i] < cusps[i+1]:
                if cusps[i] <= long < cusps[i+1]: return i
            elif long >= cusps[i] or long < cusps[i+1]: return i
        return 12

    def _calculate_aspects(self, pA: List[PlanetData], pB: Optional[List[PlanetData]] = None) -> List[AspectData]:
        res = []
        if pB is None:
            for i in range(len(pA)):
                for j in range(i + 1, len(pA)): self._add_aspect_if_exists(pA[i], pA[j], res)
        else:
            for p1 in pA:
                for p2 in pB: self._add_aspect_if_exists(p1, p2, res)
        return res

    def _add_aspect_if_exists(self, p1: PlanetData, p2: PlanetData, res: List[AspectData]):
        d1, d2 = self._to_full_degree(p1.sign, p1.degree), self._to_full_degree(p2.sign, p2.degree)
        diff = abs(d1 - d2)
        if diff > 180: diff = 360 - diff
        for aspect in ASPECTS:
            orb_val = abs(diff - aspect["angle"])
            if orb_val <= aspect["orb"]: res.append(AspectData(planet_1=p1.name, planet_2=p2.name, aspect_type=aspect["name"], orb=round(orb_val, 2)))

    def _to_full_degree(self, sign: str, degree: float) -> float:
        try: return ZODIAC_SIGNS.index(sign) * 30 + degree
        except ValueError: return 0.0
