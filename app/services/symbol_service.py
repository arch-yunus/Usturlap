from typing import Dict, Optional
from app.models.chart import SabianSymbolData

class SabianSymbolService:
    def __init__(self):
        # In a real production app, this would be a full 360-degree DB
        self.symbols_map = {
            "Aries-1": "A Woman Has Just Risen From The Sea, A Seal Is Embracing Her.",
            "Aries-2": "A Comedian Entertaining A Group.",
            "Leo-1": "Blood Rushes To A Man's Head As His Vital Energies Are Mobilized Under The Spur Of Ambition.",
            "Scorpio-1": "A Sight-Seeing Bus Filled With Tourists.",
            # ... 360 symbols would go here
        }

    def get_symbol(self, sign: str, degree: float) -> SabianSymbolData:
        """
        Sabian symbols are associated with each degree (1-30).
        0.0 to 0.99 is the 1st degree.
        """
        rounded_degree = int(degree) + 1
        key = f"{sign}-{rounded_degree}"
        
        symbol_text = self.symbols_map.get(key, "Symbol description pending high-density database integration.")
        
        return SabianSymbolData(
            degree_label=f"{rounded_degree}° {sign}",
            symbol=symbol_text
        )
