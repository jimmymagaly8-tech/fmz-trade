from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers.strategies import router as strategies_router
from backend.routers.backtest import router as backtest_router, ws_router

app = FastAPI(title="FMZ Backtest Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategies_router)
app.include_router(backtest_router)
app.include_router(ws_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Production: serve frontend static files from frontend/dist/
_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: serve index.html for all non-API routes."""
        file = _DIST_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
