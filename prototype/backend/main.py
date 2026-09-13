"""
ThunderGuard AI - backend
==========================
Minimal FastAPI service that serves the precomputed forecast (see
../generate_data.py) to the dashboard. Deliberately simple: no live model
inference during the demo, so nothing can crash on stage. Swap the
`load_forecast()` function for a real model call once you have one trained.

RUN
    pip install fastapi uvicorn --break-system-packages
    uvicorn main:main_app --reload --port 8000 --app-dir backend

Then open frontend/index.html in a browser (it calls http://localhost:8000).
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DATA_PATH = Path(__file__).parent.parent / "data" / "forecast.json"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

main_app = FastAPI(title="ThunderGuard AI API")

# CORS left open in case you serve the frontend separately during development
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_forecast():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "data/forecast.json not found - run `python generate_data.py` first"
        )
    return json.loads(DATA_PATH.read_text())


@main_app.get("/api/health")
def health():
    return {"status": "ok", "service": "thunderguard-ai-backend"}


@main_app.get("/api/forecast")
def get_forecast():
    """Full forecast: all time steps, grid cells, proxy values and reasons."""
    return load_forecast()


@main_app.get("/api/forecast/{step_label}")
def get_forecast_step(step_label: str):
    """A single time step, e.g. /api/forecast/+30"""
    data = load_forecast()
    for frame in data["frames"]:
        if frame["label"] == step_label:
            return frame
    return {"error": f"Unknown time step '{step_label}'", "available": data["time_steps"]}


# Serve the dashboard itself at http://localhost:8000/ so the whole demo
# runs from one command - no separate frontend server, no CORS headaches.
main_app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
