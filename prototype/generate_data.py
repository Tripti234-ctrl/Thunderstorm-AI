"""
ThunderGuard AI - synthetic forecast generator
================================================
Generates a believable 0-60 min thunderstorm/lightning nowcast for a demo
grid, without needing real radar/satellite/lightning feeds.

WHY THIS EXISTS
For a one-day hackathon prototype you don't have time to source and align
real MOSDAC/IMD data. This script fakes four physically-motivated input
"proxy" layers (radar, satellite, lightning, atmospheric instability),
moves a storm cell across an 8x8 grid over 5 time steps, and fuses the
layers with a simple weighted rule (your Stage-1 baseline model). Swap this
script's internals for a trained model later without touching the
backend or frontend - they only depend on the JSON shape below.

RUN
    pip install numpy --break-system-packages   # only dependency
    python generate_data.py

OUTPUT
    data/forecast.json  (read by backend/main.py)
"""

import json
import math
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Config - tweak these to change the demo story
# ---------------------------------------------------------------------------
GRID_SIZE = 8                                   # 8x8 cells
TIME_STEPS = ["now", "+15", "+30", "+45", "+60"]  # forecast horizon labels
REGION_NAME = "Dehradun"
SEED = 42                                       # change for a different run

# storm path: where the cell starts and where it drifts to, over the 5 steps
START = (2.0, 2.0)
END = (5.5, 5.5)

# fusion weights - must sum to ~1.0. This IS your "Stage 1" rule-based model.
WEIGHTS = {"radar": 0.35, "satellite": 0.25, "lightning": 0.25, "instability": 0.15}

# risk category thresholds (0-100 scale)
THRESHOLDS = [(65, "RED"), (40, "ORANGE"), (20, "YELLOW"), (0, "GREEN")]

REASON_TEXT = {
    "radar": "Rapid increase in radar reflectivity",
    "satellite": "Cloud-top cooling detected in satellite IR imagery",
    "lightning": "Lightning strike density increasing",
    "instability": "High atmospheric instability (CAPE/wind shear)",
}

random.seed(SEED)


def gaussian(dx, dy, spread):
    return math.exp(-(dx ** 2 + dy ** 2) / (2 * spread ** 2))


def category(score):
    for cutoff, label in THRESHOLDS:
        if score >= cutoff:
            return label
    return "GREEN"


def build_frame(t_index, n_steps):
    """Build one time-step's grid of proxy values + fused risk."""
    progress = t_index / (n_steps - 1)  # 0..1 across the forecast horizon
    cx = START[0] + (END[0] - START[0]) * progress
    cy = START[1] + (END[1] - START[1]) * progress

    # storm intensifies then decays - peaks around the middle of the horizon
    intensity = 0.55 + 0.45 * math.sin(math.pi * progress)

    # each proxy leads/lags the others slightly, mimicking real physics:
    # satellite cooling shows up first, lightning ramps up last
    proxies_cfg = {
        "radar": {"spread": 1.6, "lag": 0.0},
        "satellite": {"spread": 2.1, "lag": -0.15},
        "lightning": {"spread": 1.3, "lag": 0.15},
        "instability": {"spread": 2.6, "lag": -0.05},
    }

    cells = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            proxy_vals = {}
            for name, cfg in proxies_cfg.items():
                p = min(max(progress + cfg["lag"], 0), 1)
                px = START[0] + (END[0] - START[0]) * p
                py = START[1] + (END[1] - START[1]) * p
                base = gaussian(c - px, r - py, cfg["spread"]) * intensity
                noise = random.uniform(-0.04, 0.04)
                proxy_vals[name] = round(max(0.0, min(1.0, base + noise)), 3)

            fused = sum(WEIGHTS[k] * v for k, v in proxy_vals.items())
            risk_pct = round(fused * 100, 1)

            # explainability: which proxies are actually driving this cell
            triggered = sorted(proxy_vals.items(), key=lambda kv: kv[1], reverse=True)
            reasons = [REASON_TEXT[name] for name, val in triggered if val > 0.5][:3]

            cells.append({
                "row": r, "col": c,
                "risk": risk_pct,
                "category": category(risk_pct),
                "proxies": proxy_vals,
                "reasons": reasons,
            })

    # region-level summary metrics for the side panel
    max_cell = max(cells, key=lambda x: x["risk"])
    thunderstorm_pct = round(max_cell["risk"], 1)
    lightning_pct = round(max(c["proxies"]["lightning"] for c in cells) * 100, 1)
    rainfall_pct = round(max(c["proxies"]["radar"] for c in cells) * 100, 1)

    return {
        "label": TIME_STEPS[t_index],
        "cells": cells,
        "summary": {
            "thunderstorm_risk": thunderstorm_pct,
            "lightning_risk": lightning_pct,
            "rainfall_probability": rainfall_pct,
            "peak_cell": {"row": max_cell["row"], "col": max_cell["col"]},
            "top_reasons": max_cell["reasons"],
        },
    }


def confidence_for(frames):
    peak = max(f["summary"]["thunderstorm_risk"] for f in frames)
    if peak >= 70:
        return "HIGH"
    if peak >= 45:
        return "MEDIUM"
    return "LOW"


def main():
    frames = [build_frame(i, len(TIME_STEPS)) for i in range(len(TIME_STEPS))]
    peak_frame = max(frames, key=lambda f: f["summary"]["thunderstorm_risk"])

    forecast = {
        "region": REGION_NAME,
        "grid_size": GRID_SIZE,
        "time_steps": TIME_STEPS,
        "generated_with": "rule-based fusion baseline (Stage 1) - swap in a trained model later",
        "weights": WEIGHTS,
        "frames": frames,
        "headline": {
            "confidence": confidence_for(frames),
            "expected_peak_step": peak_frame["label"],
            "peak_thunderstorm_risk": peak_frame["summary"]["thunderstorm_risk"],
        },
    }

    out_path = Path(__file__).parent / "data" / "forecast.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(forecast, indent=2))
    print(f"Wrote {out_path} ({len(frames)} time steps, {GRID_SIZE}x{GRID_SIZE} grid)")


if __name__ == "__main__":
    main()
