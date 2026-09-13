# ThunderGuard AI — One-Day Prototype

A working, demoable 0–60 min thunderstorm/lightning nowcast dashboard, built to
run in a single day with **no real radar/satellite feeds required**. It uses a
synthetic-but-physically-shaped dataset and a transparent rule-based fusion
"model" so the whole pipeline — data → model → map → explainable alert — is
real and clickable, even though the data underneath is simulated for the demo.

## What's actually real vs. simulated

| Piece | Status |
|---|---|
| Data (radar/satellite/lightning/instability proxies) | **Simulated** — a moving Gaussian "storm cell" per `generate_data.py` |
| Fusion model | **Real, but simple** — a weighted-sum rule (your Stage-1 baseline) |
| Backend API | **Real** — FastAPI, serves the forecast as JSON |
| Dashboard (map, time slider, explainability, impact zones) | **Real** — fully interactive, HTML/CSS/JS |

This is intentionally honest scoping for a one-day build. Swap
`generate_data.py`'s internals for a trained ConvLSTM/fusion model reading
real MOSDAC/IMD data later — nothing else needs to change.

## Quick start (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate the synthetic forecast
python generate_data.py

# 3. Run the app (backend + dashboard, one server)
uvicorn main:main_app --reload --port 8000 --app-dir backend
```

Then open **http://localhost:8000** in a browser. Do not open `index.html`
directly by double-clicking it — it needs to be served by the backend so its
`fetch("/api/forecast")` call works.

## What you can click during the demo

- **Time slider / NOW +15 +30 +45 +60 labels** — moves through the forecast horizon; the grid, risk bars and alert banner update live.
- **Any grid cell** — click it to see that specific cell's risk and the reasons driving it.
- **"Why this alert?"** — resets to the region's single highest-risk cell and scrolls to its reasons. This is your explainable-AI moment for judges.
- **Impact zones** — chips light up red when the currently-explained cell is near a hardcoded school/airport/highway/substation position.

## Re-running with a different storm

Edit the `START`, `END`, or `SEED` constants at the top of `generate_data.py`
and re-run it — e.g. move the storm further, make it more intense, or change
which corner it starts in — to get a different-looking demo run without
touching any other file.

## Project layout

```
prototype/
├── generate_data.py     # synthetic data + rule-based fusion "model"
├── requirements.txt
├── data/
│   └── forecast.json    # generated output, read by the backend
├── backend/
│   └── main.py           # FastAPI: /api/forecast, /api/forecast/{step}, serves frontend
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

## Next steps after the hackathon's first round

1. Replace `generate_data.py` with real ingestion from MOSDAC/IMD (radar,
   INSAT satellite, LLDN lightning, AWS, NWP) on a common grid.
2. Train the Stage-1 ConvLSTM/U-Net baseline on radar alone, then the
   Stage-2 multi-branch fusion model — see the architecture slide in the deck.
3. Replace the weighted-sum rule in `build_frame()` with a call to your
   trained model's inference function; keep the JSON shape identical so the
   frontend needs zero changes.
4. Add real evaluation (CSI, precision/recall, Brier score, lead time) instead
   of the illustrative numbers used for the pitch deck.
