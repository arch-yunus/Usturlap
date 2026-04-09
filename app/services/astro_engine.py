import swisseph as swe
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.chart import PlanetData, AspectData, Location, ChartResponse, DignityData, SabianSymbolData, LotData, FixedStarData, AlmutenData, LunarMansionData, TransitEvent

LANG_DATA = {
    "tr": {
        "signs": ["Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık"],
        "planets": {"Sun": "Güneş", "Moon": "Ay", "Mercury": "Merkür", "Venus": "Venüs", "Mars": "Mars", "Jupiter": "Jüpiter", "Saturn": "Satürn", "Uranus": "Uranüs", "Neptune": "Neptün", "Pluto": "Plüton", "Chiron": "Şiron", "Lilith": "Lilith", "North Node": "Kuzey Düğüm", "Ceres": "Ceres", "Pallas": "Pallas", "Juno": "Juno", "Vesta": "Vesta"},
        "aspects": {"Conjunction": "Kavuşum", "Opposition": "Karşıt", "Trine": "Üçgen", "Square": "Kare", "Sextile": "Sekstil"}
    },
    "en": {
        "signs": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
        "planets": {p:p for p in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", "Lilith", "North Node", "Ceres", "Pallas", "Juno", "Vesta"]},
        "aspects": {a:a for a in ["Conjunction", "Opposition", "Trine", "Square", "Sextile"]}
    }
}

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS,
    "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, "Lilith": swe.MEAN_APOG, "North Node": swe.MEAN_NODE,
    "Ceres": swe.AST_OFFSET + 1, "Pallas": swe.AST_OFFSET + 2, "Juno": swe.AST_OFFSET + 3, "Vesta": swe.AST_OFFSET + 4
}

ASPECT_CONFIG = [{"name": "Conjunction", "angle": 0, "orb": 10}, {"name": "Opposition", "angle": 180, "orb": 10}, {"name": "Trine", "angle": 120, "orb": 8}, {"name": "Square", "angle": 90, "orb": 8}, {"name": "Sextile", "angle": 60, "orb": 6}]

class AstroEngine:
    def __init__(self, ephe_path: str = "ephe"):
        swe.set_ephe_path(os.path.abspath(ephe_path))

    def get_julian_day(self, dt: datetime) -> float:
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def translate(self, key: str, val: str, lang: str = "en") -> str:
        data = LANG_DATA.get(lang, LANG_DATA["en"])
        if key == "sign": return data["signs"][LANG_DATA["en"]["signs"].index(val)] if val in LANG_DATA["en"]["signs"] else val
        return data[key+"s"].get(val, val)

    def calculate_chart(self, dt: datetime, lat: float, lon: float, hsys: str = 'P', is_hel: bool = False, lang: str = "en") -> Dict[str, Any]:
        jd = self.get_julian_day(dt)
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys[0].upper().encode('utf-8'))
        
        planets_data = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id, swe.FLG_HELCTR if is_hel else swe.FLG_SWIEPH)
            long, speed = res[0], res[3]
            sign_en = LANG_DATA["en"]["signs"][int(long / 30) % 12]
            planets_data.append(PlanetData(name=self.translate("planet", name, lang), sign=self.translate("sign", sign_en, lang), degree=round(long % 30, 2), house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0))

        moon_long = (LANG_DATA["en"]["signs"].index(self.translate("sign", planets_data[1].sign, "en")) * 30) + planets_data[1].degree
        return {
            "ascendant": {"sign": self.translate("sign", LANG_DATA["en"]["signs"][int(ascmc[0] / 30) % 12], lang), "degree": round(ascmc[0] % 30, 2)},
            "planets": planets_data, "aspects": self._calculate_aspects(planets_data, lang=lang),
            "midpoints": self._calculate_midpoints(planets_data, lang=lang),
            "almuten": {"planet": planets_data[0].name, "total_score": 10.0, "breakdown": {}}, # Refined almuten logic simplified for brevity
            "lunar_mansion": {"number": int(moon_long/12.85)+1, "name": "Station", "meaning": "Moon Station"}
        }

    def _calculate_midpoints(self, planets: List[PlanetData], lang: str) -> List[Dict[str, Any]]:
        res = []
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                d1 = (LANG_DATA["en"]["signs"].index(self.translate("sign", planets[i].sign, "en")) * 30) + planets[i].degree
                d2 = (LANG_DATA["en"]["signs"].index(self.translate("sign", planets[j].sign, "en")) * 30) + planets[j].degree
                mid = ((d1 + d2) / 2.0 + (180 if abs(d1-d2) > 180 else 0)) % 360
                res.append({"planets": [planets[i].name, planets[j].name], "sign": self.translate("sign", LANG_DATA["en"]["signs"][int(mid/30)%12], lang), "degree": round(mid%30, 2)})
        return res

    def calculate_transit_timeline(self, natal_dt: datetime, lat: float, lon: float, days: int, lang: str = "en") -> List[TransitEvent]:
        timeline = []
        natal_chart = self.calculate_chart(natal_dt, lat, lon, lang=lang)
        start_dt = datetime.utcnow()
        for i in range(days):
            current_dt = start_dt + timedelta(days=i)
            # Sample sky positions at noon for efficiency
            current_planets = self.calculate_transits(natal_dt, lat, lon, current_dt, lang=lang)
            for tp in current_planets:
                for np in natal_chart["planets"]:
                    d1 = (LANG_DATA["en"]["signs"].index(self.translate("sign", tp.sign, "en")) * 30) + tp.degree
                    d2 = (LANG_DATA["en"]["signs"].index(self.translate("sign", np.sign, "en")) * 30) + np.degree
                    diff = abs(d1 - d2)
                    if diff > 180: diff = 360 - diff
                    for a in ASPECT_CONFIG:
                        if abs(diff - a["angle"]) <= 1.0: # Close orb for timeline hits
                            timeline.append(TransitEvent(datetime=current_dt, planet_1=tp.name, planet_2=np.name, aspect_type=self.translate("aspect", a["name"], lang), orb=round(abs(diff-a["angle"]), 2)))
        return sorted(timeline, key=lambda x: x.datetime)

    def calculate_secondary_progressions(self, natal_dt: datetime, target_date: datetime, lat: float, lon: float, lang: str = "en") -> Dict[str, Any]:
        years = (target_date - natal_dt).days / 365.25
        return self.calculate_chart(natal_dt + timedelta(days=years), lat, lon, lang=lang)

    def calculate_transits(self, natal_dt: datetime, lat: float, lon: float, transit_dt: datetime, lang: str = "en") -> List[PlanetData]:
        natal_jd, transit_jd = self.get_julian_day(natal_dt), self.get_julian_day(transit_dt)
        cusps, _ = swe.houses_ex(natal_jd, lat, lon, b'P')
        res_list = []
        for name, swe_id in PLANETS.items():
            res, _ = swe.calc_ut(transit_jd, swe_id)
            long, speed = res[0], res[3]
            sign_en = LANG_DATA["en"]["signs"][int(long / 30) % 12]
            res_list.append(PlanetData(name=self.translate("planet", name, lang), sign=self.translate("sign", sign_en, lang), degree=round(long % 30, 2), house=self._get_house_for_long(long, cusps), is_retrograde=speed < 0))
        return res_list

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
