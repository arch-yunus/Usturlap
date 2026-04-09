from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1 import endpoints
import os

app = FastAPI(
    title="Usturlap (Astrolabe) API",
    description="Modern and high-performance astrological calculation engine.",
    version="1.0.0"
)

# Serve static files for the premium interface
# We ensure the static directory exists before mounting
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include v1 routes
app.include_router(endpoints.router, prefix="/api/v1", tags=["Astrology"])

@app.get("/")
async def root():
    # Serve the Sovereign Interface as the landing page
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "message": "Welcome to Usturlap API. Visit /docs for documentation.",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
