from typing import Dict, List, Any
from app.models.chart import ChartResponse

class BuiltinInterpretationService:
    def __init__(self):
        # A subset of archetypal interpretations for the Sovereign Engine
        self.placements_tr = {
            "Sun-Aries": "Güneş Koç'ta: Liderlik, cesaret ve yeni başlangıçlar için güçlü bir enerji.",
            "Moon-Taurus": "Ay Boğa'da: Duygusal denge, huzur ve maddi güvenlik ihtiyacı.",
            "Mars-Scorpio": "Mars Akrep'te: Derin tutku, dayanıklılık ve stratejik güç.",
            # ... can be expanded to 120+ combinations
        }
        self.aspects_tr = {
            "Sun-Conjunction-Jupiter": "Güneş Jüpiter Kavuşumu: Büyük şans, iyimserlik ve genişleme fırsatları.",
            "Saturn-Square-Mars": "Satürn Mars Karesi: Engellenmiş aksiyonlar, disiplin gerektiren zorlu mücadeleler.",
        }

    def get_base_interpretation(self, chart: ChartResponse, lang: str = "tr") -> str:
        intro = "### Usturlap Temel Analiz Raporu\n\n" if lang == "tr" else "### Usturlap Base Analysis Report\n\n"
        
        sections = []
        # Analyze Important Placements
        for p in chart.planets[:3]: # Sun, Moon, Mercury
            key = f"{p.name}-{p.sign}"
            desc = self.placements_tr.get(key, f"{p.name} {p.sign} burcunda konumlanmış.")
            sections.append(f"- **{p.name} {p.sign}**: {desc}")
            
        # Analyze Major Aspects
        for a in chart.aspects[:5]:
            key = f"{a.planet_1}-{a.aspect_type}-{a.planet_2}"
            desc = self.aspects_tr.get(key, f"{a.planet_1} ile {a.planet_2} arasında {a.aspect_type} mevcut.")
            sections.append(f"- **{a.planet_1} {a.aspect_type} {a.planet_2}**: {desc}")

        return intro + "\n".join(sections)
