import math
from typing import Dict, Any, List
from app.models.chart import ChartResponse

class SVGChartService:
    def __init__(self, size: int = 800):
        self.size = size
        self.center = size / 2
        self.radius = (size / 2) - 40
        self.colors = {
            "trine": "#3498db", "square": "#e74c3c", "conjunction": "#f1c40f",
            "sextile": "#2ecc71", "opposition": "#9b59b6", "wheel": "#2c3e50",
            "planet": "#ecf0f1", "label": "#bdc3c7"
        }

    def _degree_to_rad(self, degree: float) -> float:
        # 0 Aries is at 90 degrees (top) or 180 (left)? 
        # Traditionally ASC is at 180 (left).
        return math.radians(degree - 180)

    def draw_chart(self, chart: ChartResponse) -> str:
        asc_deg = chart.ascendant["degree"] + (90) # Placeholder offset
        
        svg = [f'<svg width="{self.size}" height="{self.size}" viewBox="0 0 {self.size} {self.size}" xmlns="http://www.w3.org/2000/svg" style="background:#1a1a1a">']
        
        # 1. Background Circles
        svg.append(f'<circle cx="{self.center}" cy="{self.center}" r="{self.radius}" fill="none" stroke="{self.colors["wheel"]}" stroke-width="2"/>')
        svg.append(f'<circle cx="{self.center}" cy="{self.center}" r="{self.radius - 60}" fill="none" stroke="{self.colors["wheel"]}" stroke-width="1"/>')

        # 2. Draw Aspect Lines
        for aspect in chart.aspects:
            p1 = next((p for p in chart.planets if p.name == aspect.planet_1), None)
            p2 = next((p for p in chart.planets if p.name == aspect.planet_2), None)
            if p1 and p2:
                # Convert sign+degree to absolute 360
                d1 = (self._sign_to_long(p1.sign) + p1.degree)
                d2 = (self._sign_to_long(p2.sign) + p2.degree)
                x1, y1 = self._get_coords(d1, self.radius - 80)
                x2, y2 = self._get_coords(d2, self.radius - 80)
                color = self.colors.get(aspect.aspect_type.lower(), self.colors["label"])
                svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-opacity="0.4" stroke-width="1"/>')

        # 3. Draw Planets
        for p in chart.planets:
            long = self._sign_to_long(p.sign) + p.degree
            x, y = self._get_coords(long, self.radius - 40)
            svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{self.colors["planet"]}"/>')
            svg.append(f'<text x="{x+8}" y="{y+4}" font-family="Arial" font-size="12" fill="{self.colors["planet"]}">{p.name[:2]}</text>')

        # 4. Draw Zodiac Labels (Simplified)
        signs = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
        for i, sign in enumerate(signs):
            angle = i * 30 + 15
            x, y = self._get_coords(angle, self.radius + 20)
            svg.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="14" fill="{self.colors["label"]}" text-anchor="middle">{sign}</text>')

        svg.append('</svg>')
        return "\n".join(svg)

    def _get_coords(self, degree: float, radius: float) -> (float, float):
        # Rotate so 0 Aries is at 180 degrees (Left)
        rad = math.radians(180 - degree)
        x = self.center + radius * math.cos(rad)
        y = self.center + radius * math.sin(rad)
        return x, y

    def _sign_to_long(self, sign: str) -> float:
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        try: return signs.index(sign) * 30
        except: return 0.0
