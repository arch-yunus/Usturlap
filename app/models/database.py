from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class SavedChart(Base):
    __tablename__ = "saved_charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    chart_date = Column(DateTime, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    house_system = Column(String(20), default="placidus")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "datetime": self.chart_date.isoformat(),
            "lat": self.lat,
            "lon": self.lon,
            "house_system": self.house_system,
            "notes": self.notes,
            "created_at": self.created_at.isoformat()
        }
