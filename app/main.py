from fastapi import FastAPI
from app.api.v1 import endpoints

app = FastAPI(
    title="Usturlap (Astrolabe) API",
    description="Modern and high-performance astrological calculation engine.",
    version="1.0.0"
)

# Include v1 routes
app.include_router(endpoints.router, prefix="/api/v1", tags=["Astrology"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Usturlap API. Visit /docs for documentation.",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
