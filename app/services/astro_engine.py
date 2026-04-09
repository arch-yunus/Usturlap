import swisseph as swe
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData, SabianSymbolData, LotData, FixedStarData, AlmutenData, LunarMansionData

# Localized Mappings
LANG_DATA = {
    "tr": {
        "signs": ["Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık"],
        "planets": {"Sun": "Güneş", "Moon": "Ay", "Mercury": "Merkür", "Venus": "Venüs", "Mars": "Mars", "Jupiter": "Jüpiter", "Saturn": "Satürn", "Uranus": "Uranüs", "Neptune": "Neptün", "Pluto": "Plüton", "Chiron": "Şiron", "Lilith": "Lilith", "North Node": "Kuzey Düğüm"},
        "aspects": {"Conjunction": "Kavuşum", "Opposition": "Karşıt", "Trine": "Üçgen", "Square": "Kare", "Sextile": "Sekstil"}
    },
    "en": {
        "signs": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
        "planets": {"Sun": "Sun", "Moon": "Moon", "Mercury": "Mercury", "Venus": "Venus", "Mars": "Mars", "Jupiter": "Jupiter", "Saturn": "Saturn", "Uranus": "Uranus", "Neptune": "Neptune", "Pluto": "Pluto", "Chiron": "Chiron", "Lilith": "Lilith", "North Node": "North Node"},
        "aspects": {"Conjunction": "Conjunction", "Opposition": "Opposition", "Trine": "Trine", "Square": "Square", "Sextile": "Sextile"}
    }
}

PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, "Lilith": swe.MEAN_APOG, "North Node": swe.MEAN_NODE}
ASPECT_CONFIG = [{"name": "Conjunction", "angle": 0, "orb": 10}, {"name": "Opposition", "angle": 180, "orb": 10}, {"name": "Trine", "angle": 120, "orb": 8}, {"name": "Square", "angle": 90, "orb": 8}, {"name": "Sextile", "angle": 60, "orb": 6}]
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
        swe.set_ephe_path(os.path.abspath(ephe_path))

    def get_julian_day(self, dt: datetime) -> float:
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def translate(self, key: str, value: str, lang: str = "en") -> str:
        data = LANG_DATA.get(lang, LANG_DATA["en"])
        if key == "sign":
            try: return data["signs"][LANG_DATA["en"]["signs"].index(value)]
            except: return value
        elif key == "planet": return data["planets"].get(value, value)
        elif key == "aspect": return data["aspects"].get(value, value)
        return value

    def calculate_chart(self, dt: datetime, lat: float, lon: float, hsys: str = 'P', is_hel: bool = False, lang: str = "en") -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        flag = swe.FLG_HELCTR if is_hel else swe.FLG_SWIEPH
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys[0].upper().encode('utf-8'))
        
        planets_data = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id, flag)
            long, speed = res[0], res[3]
            sign_en = LANG_DATA["en"]["signs"][int(long / 30) % 12]
            planets_data.append(PlanetData(
                name=self.translate("planet", name, lang), sign=self.translate("sign", sign_en, lang),
                degree=round(long % 30, 2), house=self._get_house_for_long(long, cusps),
                is_retrograde=speed < 0, dignity=self.get_essential_dignity(name, sign_en, lang)
            ))

        moon_long = (LANG_DATA["en"]["signs"].index(self.translate("sign", planets_data[1].sign, "en")) * 30) + planets_data[1].degree
        return {
            "ascendant": {"sign": self.translate("sign", LANG_DATA["en"]["signs"][int(ascmc[0] / 30) % 12], lang), "degree": round(ascmc[0] % 30, 2)},
            "planets": planets_data, "aspects": self._calculate_aspects(planets_data, lang=lang),
            "almuten": self.calculate_almuten(planets_data), "lunar_mansion": self.calculate_lunar_mansion(moon_long, lang)
        }

    def get_essential_dignity(self, name: str, sign_en: str, lang: str = "en") -> Optional[DignityData]:
        if name not in DIGNITIES_TABLE: return None
        dig = DIGNITIES_TABLE[name]
        r, e, d, f = sign_en in dig["rulership"], sign_en == dig["exaltation"], sign_en in dig["detriment"], sign_en == dig["fall"]
        return DignityData(rulership=r, exaltation=e, detriment=d, fall=f, score=(5 if r else 0)+(4 if e else 0)-(5 if d else 0)-(4 if f else 0))

    def calculate_almuten(self, planets: List[PlanetData]) -> AlmutenData:
        scores = {p.name: p.dignity.score if p.dignity else 0.0 for p in planets}
        winner = max(scores, key=scores.get)
        return AlmutenData(planet=winner, total_score=scores[winner], breakdown=scores)

    def calculate_lunar_mansion(self, long: float, lang: str = "en") -> LunarMansionData:
        idx = int(long / (360.0 / 28.0)) % 28
        return LunarMansionData(number=idx+1, name=f"Station {idx+1}", meaning="Archetypal Station")

    def calculate_secondary_progressions(self, natal_dt: datetime, target_date: datetime, lat: float, lon: float, lang: str = "en") -> Dict[str, Any]:
        years = (target_date - natal_dt).days / 365.25
        return self.calculate_chart(natal_dt + timedelta(days=years), lat, lon, lang=lang)

    def calculate_transits(self, natal_dt: datetime, lat: float, lon: float, transit_dt: datetime, lang: str = "en") -> List[PlanetData]:
        natal_jd, transit_jd = self.get_julian_day(natal_dt), self.get_julian_day(transit_dt)
        cusps, _ = swe.houses_ex(natal_jd, lat, lon, b'P')
        transit_planets = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(transit_jd, swe_id)
            long, speed = res[0], res[3]
            sign_en = LANG_DATA["en"]["signs"][int(long / 30) % 12]
            transit_planets.append(PlanetData(name=self.translate("planet", name, lang), sign=self.translate("sign", sign_en, lang), degree=round(long % 30, 2), house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0))
        return transit_planets

    def _get_house_for_long(self, l: float, c: List[float]) -> int:
        for i in range(1, 12):
            if (c[i] < c[i+1] and c[i] <= l < c[i+1]) or (c[i] > c[i+1] and (l >= c[i] or l < c[i+1])): return i
        return 12

    def _calculate_aspects(self, p1_list: List[PlanetData], p2_list: Optional[List[PlanetData]] = None, lang: str = "en") -> List[AspectData]:
        res = []
        if p2_list is None:
            for i in range(len(p1_list)):
                for j in range(i + 1, len(p1_list)): self._add_aspect(p1_list[i], p1_list[j], res, lang)
        else:
            for p1 in p1_list:
                for p2 in p2_list: self._add_aspect(p1, p2, res, lang)
        return res

    def _add_aspect(self, p1: PlanetData, p2: PlanetData, res: List[AspectData], lang: str):
        d1 = (LANG_DATA["en"]["signs"].index(self.translate("sign", p1.sign, "en")) * 30) + p1.degree
        d2 = (LANG_DATA["en"]["signs"].index(self.translate("sign", p2.sign, "en")) * 30) + p2.degree
        diff = abs(d1 - d2)
        if diff > 180: diff = 360 - diff
        for a in ASPECT_CONFIG:
            if abs(diff - a["angle"]) <= a["orb"]:
                res.append(AspectData(planet_1=p1.name, planet_2=p2.name, aspect_type=self.translate("aspect", a["name"], lang), orb=round(abs(diff - a["angle"]), 2)))
