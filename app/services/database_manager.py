from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
from app.models.database import Base, SavedChart
from datetime import datetime
import os

DB_URL = "sqlite+aiosqlite:///./usturlap.db"

class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(DB_URL, echo=False)
        self.SessionLocal = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save_chart(self, name: str, dt: datetime, lat: float, lon: float, hsys: str, notes: str = ""):
        async with self.SessionLocal() as session:
            new_chart = SavedChart(
                name=name, chart_date=dt, lat=lat, lon=lon, 
                house_system=hsys, notes=notes
            )
            session.add(new_chart)
            await session.commit()
            await session.refresh(new_chart)
            return new_chart.to_dict()

    async def get_charts(self):
        async with self.SessionLocal() as session:
            result = await session.execute(select(SavedChart).order_by(SavedChart.created_at.desc()))
            charts = result.scalars().all()
            return [c.to_dict() for c in charts]

    async def delete_chart(self, chart_id: int):
        async with self.SessionLocal() as session:
            await session.execute(delete(SavedChart).where(SavedChart.id == chart_id))
            await session.commit()
            return True
