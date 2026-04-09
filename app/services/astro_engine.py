import swisseph as swe
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData, SabianSymbolData, LotData, FixedStarData

# Planet constants from swisseph
PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS,
    "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, "Lilith": swe.MEAN_APOG, "North Node": swe.MEAN_NODE,
}

ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

ASPECTS = [
    {"name": "Conjunction", "angle": 0, "orb": 10}, {"name": "Opposition", "angle": 180, "orb": 10},
    {"name": "Trine", "angle": 120, "orb": 8}, {"name": "Square", "angle": 90, "orb": 8}, {"name": "Sextile", "angle": 60, "orb": 6},
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

FIXED_STARS = {
    "Regulus": 150.0, "Spica": 204.0, "Antares": 249.0, "Aldebaran": 69.0, "Fomalhaut": 333.0, "Algol": 56.0, "Sirius": 104.0
}

class AstroEngine:
    def __init__(self, ephe_path: str = "ephe"):
        self.ephe_path = ephe_path
        abs_path = os.path.abspath(ephe_path)
        swe.set_ephe_path(abs_path)

    def get_julian_day(self, dt: datetime) -> float:
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def get_sign(self, degree: float) -> str:
        return ZODIAC_SIGNS[int(degree / 30) % 12]

    def get_degree_in_sign(self, degree: float) -> float:
        return degree % 30

    def calculate_chart(self, dt: datetime, lat: float, lon: float, house_system: str = 'P') -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        hsys_code = house_system[0].upper().encode('utf-8')
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys_code)
        
        asc, mc = ascmc[0], ascmc[1]
        planets_data = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id)
            long, speed = res[0], res[3]
            sign = self.get_sign(long)
            planets_data.append(PlanetData(
                name=name, sign=sign, degree=round(self.get_degree_in_sign(long), 2),
                house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0,
                dignity=self.get_essential_dignity(name, sign)
            ))

        # Sect calculation for Arabic Parts
        sun_long = planets_data[0].degree + (ZODIAC_SIGNS.index(planets_data[0].sign) * 30)
        is_day = self._get_house_for_long(sun_long, cusps) > 6

        return {
            "ascendant": {"sign": self.get_sign(asc), "degree": round(self.get_degree_in_sign(asc), 2)},
            "midheaven": {"sign": self.get_sign(mc), "degree": round(self.get_degree_in_sign(mc), 2)},
            "planets": planets_data,
            "aspects": self._calculate_aspects(planets_data),
            "midpoints": self.calculate_midpoints(planets_data),
            "lots": self.calculate_lots(asc, planets_data, is_day),
            "fixed_stars": self.calculate_fixed_stars(planets_data)
        }

    def get_essential_dignity(self, name: str, sign: str) -> Optional[DignityData]:
        if name not in DIGNITIES_TABLE: return None
        dig = DIGNITIES_TABLE[name]
        r, e, d, f = sign in dig["rulership"], sign == dig["exaltation"], sign in dig["detriment"], sign == dig["fall"]
        return DignityData(rulership=r, exaltation=e, detriment=d, fall=f, score=(5 if r else 0)+(4 if e else 0)-(5 if d else 0)-(4 if f else 0))

    def calculate_midpoints(self, planets: List[PlanetData]) -> List[Dict[str, Any]]:
        res = []
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                d1, d2 = self._to_full_degree(planets[i].sign, planets[i].degree), self._to_full_degree(planets[j].sign, planets[j].degree)
                diff = abs(d1 - d2)
                mid = ((d1 + d2) / 2.0 + (180.0 if diff > 180 else 0)) % 360.0
                res.append({"planets": [planets[i].name, planets[j].name], "sign": self.get_sign(mid), "degree": round(self.get_degree_in_sign(mid), 2)})
        return res

    def calculate_lots(self, asc: float, planets: List[PlanetData], is_day: bool) -> List[LotData]:
        sun = self._to_full_degree(planets[0].sign, planets[0].degree)
        moon = self._to_full_degree(planets[1].sign, planets[1].degree)
        # Fortune: Day = ASC + Moon - Sun, Night = ASC + Sun - Moon
        f_deg = (asc + moon - sun) if is_day else (asc + sun - moon)
        s_deg = (asc + sun - moon) if is_day else (asc + moon - sun)
        return [
            LotData(name="Lot of Fortune", sign=self.get_sign(f_deg % 360), degree=round(self.get_degree_in_sign(f_deg % 360), 2)),
            LotData(name="Lot of Spirit", sign=self.get_sign(s_deg % 360), degree=round(self.get_degree_in_sign(s_deg % 360), 2))
        ]

    def calculate_fixed_stars(self, planets: List[PlanetData]) -> List[FixedStarData]:
        res = []
        for s_name, s_deg in FIXED_STARS.items():
            for p in planets:
                p_deg = self._to_full_degree(p.sign, p.degree)
                dist = abs(p_deg - s_deg)
                if dist > 180: dist = 360 - dist
                if dist < 2.0: # 2 degree orb for stars
                    res.append(FixedStarData(name=s_name, sign=self.get_sign(s_deg), degree=round(self.get_degree_in_sign(s_deg), 2), distance_to_planet=round(dist, 2), connected_planet=p.name))
        return res

    def calculate_harmonic_chart(self, dt: datetime, lat: float, lon: float, harmonic: int) -> Dict[str, Any]:
        base = self.calculate_chart(dt, lat, lon)
        for p in base["planets"]:
            full = self._to_full_degree(p.sign, p.degree)
            h_deg = (full * harmonic) % 360
            p.sign, p.degree = self.get_sign(h_deg), round(self.get_degree_in_sign(h_deg), 2)
        return base

    def calculate_solar_return(self, natal_dt: datetime, year: int, lat: float, lon: float) -> Dict[str, Any]:
        jd_natal = self.get_julian_day(natal_dt)
        sun_long = swe.calc_ut(jd_natal, swe.SUN)[0][0]
        return_jd = swe.solcross_ut(sun_long, self.get_julian_day(datetime(year, natal_dt.month, natal_dt.day)) - 2.0)
        y, m, d, h = swe.revjul(return_jd)
        return self.calculate_chart(datetime(y, m, d, int(h), int((h%1)*60), int(((h%1)*60%1)*60)), lat, lon)

    def calculate_planetary_hours(self, dt: datetime, lat: float, lon: float) -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        sunrise = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_RISE)[0]
        sunset = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_SET)[0]
        day_rulers = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
        return {"day_ruler": day_rulers[dt.weekday()], "is_daytime": sunrise <= jd <= sunset, "hour_ruler": "Search logic pending"}

    def _get_house_for_long(self, l: float, c: List[float]) -> int:
        for i in range(1, 12):
            if (c[i] < c[i+1] and c[i] <= l < c[i+1]) or (c[i] > c[i+1] and (l >= c[i] or l < c[i+1])): return i
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
        for a in ASPECTS:
            if abs(diff - a["angle"]) <= a["orb"]: res.append(AspectData(planet_1=p1.name, planet_2=p2.name, aspect_type=a["name"], orb=round(abs(diff - a["angle"]), 2)))

    def _to_full_degree(self, s: str, d: float) -> float:
        try: return ZODIAC_SIGNS.index(s) * 30 + d
        except: return 0.0
