import swisseph as swe
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData, SabianSymbolData, LotData, FixedStarData, AlmutenData, LunarMansionData

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

MANAZIL = [
    {"num": 1, "name": "Al-Natih", "meaning": "The Horns"},
    {"num": 2, "name": "Al-Butayn", "meaning": "The Belly"},
    # ... placeholder for all 28 mansional names for architectural integrity
]

FIXED_STARS = {
    "Regulus": 150.0, "Spica": 204.0, "Antares": 249.0, "Aldebaran": 69.0, "Fomalhaut": 333.0, "Algol": 56.0, "Sirius": 104.0,
    "Procyon": 115.0, "Betelgeuse": 88.0, "Rigel": 76.0, "Vega": 285.0, "Arcturus": 204.0, "Altair": 301.0, "Pollux": 113.0
}

class AstroEngine:
    def __init__(self, ephe_path: str = "ephe"):
        self.ephe_path = ephe_path
        swe.set_ephe_path(os.path.abspath(ephe_path))

    def get_julian_day(self, dt: datetime) -> float:
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def get_sign(self, degree: float) -> str:
        return ZODIAC_SIGNS[int(degree / 30) % 12]

    def get_degree_in_sign(self, degree: float) -> float:
        return degree % 30

    def calculate_chart(self, dt: datetime, lat: float, lon: float, house_system: str = 'P', is_heliocentric: bool = False) -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        flag = swe.FLG_HELCTR if is_heliocentric else swe.FLG_SWIEPH
        
        cusps, ascmc = swe.houses_ex(jd, lat, lon, house_system[0].upper().encode('utf-8'))
        
        planets_data = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id, flag)
            long, speed = res[0], res[3]
            sign = self.get_sign(long)
            planets_data.append(PlanetData(
                name=name, sign=sign, degree=round(self.get_degree_in_sign(long), 2),
                house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0,
                dignity=self.get_essential_dignity(name, sign)
            ))

        moon_long = planets_data[1].degree + (ZODIAC_SIGNS.index(planets_data[1].sign) * 30)
        sun_long = planets_data[0].degree + (ZODIAC_SIGNS.index(planets_data[0].sign) * 30)
        is_day = self._get_house_for_long(sun_long, cusps) > 6

        return {
            "ascendant": {"sign": self.get_sign(ascmc[0]), "degree": round(self.get_degree_in_sign(ascmc[0]), 2)},
            "midheaven": {"sign": self.get_sign(ascmc[1]), "degree": round(self.get_degree_in_sign(ascmc[1]), 2)},
            "planets": planets_data,
            "aspects": self._calculate_aspects(planets_data),
            "midpoints": self.calculate_midpoints(planets_data),
            "lots": self.calculate_lots(ascmc[0], planets_data, is_day),
            "fixed_stars": self.calculate_fixed_stars(planets_data),
            "almuten": self.calculate_almuten_figuris(planets_data),
            "lunar_mansion": self.calculate_lunar_mansion(moon_long)
        }

    def get_essential_dignity(self, name: str, sign: str) -> Optional[DignityData]:
        if name not in DIGNITIES_TABLE: return None
        dig = DIGNITIES_TABLE[name]
        r, e, d, f = sign in dig["rulership"], sign == dig["exaltation"], sign in dig["detriment"], sign == dig["fall"]
        return DignityData(rulership=r, exaltation=e, detriment=d, fall=f, score=(5 if r else 0)+(4 if e else 0)-(5 if d else 0)-(4 if f else 0))

    def calculate_almuten_figuris(self, planets: List[PlanetData]) -> AlmutenData:
        scores = {p.name: 0.0 for p in planets if p.name in DIGNITIES_TABLE}
        for p in planets:
            if p.name in DIGNITIES_TABLE and p.dignity: scores[p.name] += p.dignity.score
        winner = max(scores, key=scores.get)
        return AlmutenData(planet=winner, total_score=scores[winner], breakdown=scores)

    def calculate_lunar_mansion(self, moon_long: float) -> LunarMansionData:
        # 28 Mansions, each 360/28 = 12.857 degrees
        idx = int(moon_long / (360.0 / 28.0)) % 28
        m = MANAZIL[idx] if idx < len(MANAZIL) else {"num": idx+1, "name": "Al-Manzil", "meaning": "Moon Station"}
        return LunarMansionData(number=m["num"], name=m["name"], meaning=m["meaning"])

    def calculate_lots(self, asc: float, planets: List[PlanetData], is_day: bool) -> List[LotData]:
        sun, moon = self._to_full_degree(planets[0].sign, planets[0].degree), self._to_full_degree(planets[1].sign, planets[1].degree)
        pars = [
            ("Lot of Fortune", (asc + moon - sun) if is_day else (asc + sun - moon)),
            ("Lot of Spirit", (asc + sun - moon) if is_day else (asc + moon - sun)),
            ("Lot of Assets", (asc + (ZODIAC_SIGNS.index("Leo")*30) - planets[0].degree) % 360) # Example complex lot
        ]
        return [LotData(name=n, sign=self.get_sign(d % 360), degree=round(self.get_degree_in_sign(d % 360), 2)) for n, d in pars]

    def calculate_fixed_stars(self, planets: List[PlanetData]) -> List[FixedStarData]:
        res = []
        for s_name, s_deg in FIXED_STARS.items():
            for p in planets:
                p_deg = self._to_full_degree(p.sign, p.degree)
                dist = abs(p_deg - s_deg)
                if dist > 180: dist = 360 - dist
                if dist < 2.0: res.append(FixedStarData(name=s_name, sign=self.get_sign(s_deg), degree=round(self.get_degree_in_sign(s_deg), 2), distance_to_planet=round(dist, 2), connected_planet=p.name))
        return res

    def calculate_midpoints(self, planets: List[PlanetData]) -> List[Dict[str, Any]]:
        res = []
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                d1, d2 = self._to_full_degree(planets[i].sign, planets[i].degree), self._to_full_degree(planets[j].sign, planets[j].degree)
                diff = abs(d1 - d2)
                mid = ((d1 + d2) / 2.0 + (180.0 if diff > 180 else 0)) % 360.0
                res.append({"planets": [planets[i].name, planets[j].name], "sign": self.get_sign(mid), "degree": round(self.get_degree_in_sign(mid), 2)})
        return res

    def calculate_secondary_progressions(self, natal_dt: datetime, target_date: datetime, lat: float, lon: float) -> Dict[str, Any]:
        years = (target_date - natal_dt).days / 365.25
        return self.calculate_chart(natal_dt + timedelta(days=years), lat, lon)

    def calculate_solar_arc_directions(self, natal_dt: datetime, target_date: datetime, lat: float, lon: float) -> Dict[str, Any]:
        years = (target_date - natal_dt).days / 365.25
        natal = self.calculate_chart(natal_dt, lat, lon)
        sun_arc = (swe.calc_ut(self.get_julian_day(natal_dt + timedelta(days=years)), swe.SUN)[0][0] - swe.calc_ut(self.get_julian_day(natal_dt), swe.SUN)[0][0]) % 360
        for p in natal["planets"]:
            full = (self._to_full_degree(p.sign, p.degree) + sun_arc) % 360
            p.sign, p.degree = self.get_sign(full), round(self.get_degree_in_sign(full), 2)
        return natal

    def calculate_harmonic_chart(self, dt: datetime, lat: float, lon: float, harmonic: int) -> Dict[str, Any]:
        base = self.calculate_chart(dt, lat, lon)
        for p in base["planets"]:
            h_deg = (self._to_full_degree(p.sign, p.degree) * harmonic) % 360
            p.sign, p.degree = self.get_sign(h_deg), round(self.get_degree_in_sign(h_deg), 2)
        return base

    def calculate_locality_lines(self, natal_dt: datetime, planet: str) -> List[Dict[str, Any]]:
        res, _ = swe.calc_ut(self.get_julian_day(natal_dt), PLANETS[planet])
        return [{"line_type": "MC", "longitude": (res[0] - 90) % 360}]

    def calculate_solar_return(self, natal_dt: datetime, year: int, lat: float, lon: float) -> Dict[str, Any]:
        sun_long = swe.calc_ut(self.get_julian_day(natal_dt), swe.SUN)[0][0]
        jd = swe.solcross_ut(sun_long, self.get_julian_day(datetime(year, natal_dt.month, natal_dt.day)) - 2.0)
        y, m, d, h = swe.revjul(jd)
        return self.calculate_chart(datetime(y, m, d, int(h), int((h%1)*60), int(((h%1)*60%1)*60)), lat, lon)

    def calculate_planetary_hours(self, dt: datetime, lat: float, lon: float) -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        rise = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_RISE)[0]
        set = swe.rise_trans(jd, swe.SUN, lat, lon, 0, 0, 0, swe.BIT_SET_SET)[0]
        return {"day_ruler": ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"][dt.weekday()], "is_daytime": rise <= jd <= set, "hour_ruler": "Search logic pending"}

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
