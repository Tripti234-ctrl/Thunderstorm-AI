// ThunderGuard AI — prototype dashboard logic
// Talks to the FastAPI backend at /api/forecast (same origin, served by main.py).

const CATEGORY_COLOR = {
  GREEN: "#2e8b57",
  YELLOW: "#f2a93b",
  ORANGE: "#c97e12",
  RED: "#d64545",
};

const CATEGORY_ACTION = {
  GREEN: "Low risk — no action needed",
  YELLOW: "Elevated risk — stay alert, monitor updates",
  ORANGE: "High risk — move indoors, avoid open areas",
  RED: "Severe risk — seek shelter immediately",
};

// Static impact-zone labels mapped to fixed grid positions (for demo purposes).
// In a real system these would come from a GIS layer of schools/airports/etc.
const IMPACT_ZONES = [
  { name: "School Zone", row: 3, col: 3, radius: 1.5 },
  { name: "Airport", row: 5, col: 6, radius: 1.5 },
  { name: "Highway", row: 6, col: 2, radius: 1.5 },
  { name: "Power Substation", row: 2, col: 5, radius: 1.5 },
];

let forecast = null;
let currentStep = 0;
let selectedCell = null;

async function loadForecast() {
  const res = await fetch("/api/forecast");
  if (!res.ok) throw new Error("Failed to load forecast from backend");
  forecast = await res.json();
}

function frame() {
  return forecast.frames[currentStep];
}

function cellAt(row, col) {
  return frame().cells.find((c) => c.row === row && c.col === col);
}

function renderStepLabels() {
  const wrap = document.getElementById("step-labels");
  wrap.innerHTML = "";
  forecast.time_steps.forEach((label, i) => {
    const span = document.createElement("span");
    span.textContent = label.toUpperCase();
    if (i === currentStep) span.classList.add("active");
    span.onclick = () => {
      currentStep = i;
      document.getElementById("time-slider").value = i;
      renderAll();
    };
    wrap.appendChild(span);
  });
}

function renderGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  const size = forecast.grid_size;
  const f = frame();

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const cellData = cellAt(r, c);
      const div = document.createElement("div");
      div.className = "cell";
      div.style.background = CATEGORY_COLOR[cellData.category];
      if (selectedCell && selectedCell.row === r && selectedCell.col === c) {
        div.classList.add("selected");
      }
      div.title = `Row ${r}, Col ${c} — ${cellData.risk}% (${cellData.category})`;
      div.onclick = () => {
        selectedCell = { row: r, col: c };
        renderAll();
      };
      grid.appendChild(div);
    }
  }
}

function renderBars() {
  const s = frame().summary;
  document.getElementById("ts-label").textContent = `Thunderstorm Risk — ${s.thunderstorm_risk}%`;
  document.getElementById("bar-ts").style.width = `${s.thunderstorm_risk}%`;
  document.getElementById("lt-label").textContent = `Lightning Risk — ${s.lightning_risk}%`;
  document.getElementById("bar-lt").style.width = `${s.lightning_risk}%`;
  document.getElementById("rf-label").textContent = `Rainfall Probability — ${s.rainfall_probability}%`;
  document.getElementById("bar-rf").style.width = `${s.rainfall_probability}%`;
}

function activeCellForExplainability() {
  // if the user picked a cell, explain that one; otherwise explain the region's peak cell
  if (selectedCell) return cellAt(selectedCell.row, selectedCell.col);
  const s = frame().summary;
  return cellAt(s.peak_cell.row, s.peak_cell.col);
}

function renderAlertBanner() {
  const cell = activeCellForExplainability();
  const banner = document.getElementById("alert-banner");
  banner.textContent = `RISK LEVEL: ${cell.category} — ${CATEGORY_ACTION[cell.category]}`;
  banner.style.background = CATEGORY_COLOR[cell.category];
}

function renderReasons() {
  const cell = activeCellForExplainability();
  const list = document.getElementById("reason-list");
  list.innerHTML = "";

  const reasons = cell.reasons.length ? cell.reasons : ["No dominant driver — conditions are quiet at this cell"];
  reasons.forEach((text) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dot">✓</span><span>${text}</span>`;
    list.appendChild(li);
  });

  document.getElementById("meta-cell").textContent = selectedCell
    ? `Row ${selectedCell.row}, Col ${selectedCell.col} (${cell.risk}%)`
    : `Auto — region peak (${cell.risk}%)`;
  document.getElementById("meta-peak").textContent =
    `${forecast.headline.expected_peak_step} (${forecast.headline.peak_thunderstorm_risk}%)`;
  document.getElementById("meta-conf").textContent = forecast.headline.confidence;
}

function renderImpactZones() {
  const cell = activeCellForExplainability();
  const wrap = document.getElementById("impact-zones");
  wrap.innerHTML = "";
  IMPACT_ZONES.forEach((zone) => {
    const dist = Math.hypot(zone.row - cell.row, zone.col - cell.col);
    const hot = dist <= zone.radius && (cell.category === "RED" || cell.category === "ORANGE");
    const chip = document.createElement("span");
    chip.className = "impact-chip" + (hot ? " hot" : "");
    chip.textContent = hot ? `⚠ ${zone.name} — at risk` : zone.name;
    wrap.appendChild(chip);
  });
}

function renderAll() {
  renderStepLabels();
  renderGrid();
  renderBars();
  renderAlertBanner();
  renderReasons();
  renderImpactZones();
}

function wireControls() {
  document.getElementById("time-slider").addEventListener("input", (e) => {
    currentStep = parseInt(e.target.value, 10);
    renderAll();
  });

  document.getElementById("why-btn").addEventListener("click", () => {
    selectedCell = null; // reset to region peak cell
    renderAll();
    document.getElementById("reason-list").scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

async function init() {
  try {
    await loadForecast();
    document.getElementById("region-title").textContent =
      `Thunderstorm & Lightning Nowcast — ${forecast.region}`;
    wireControls();
    renderAll();
  } catch (err) {
    document.body.innerHTML = `<p style="padding:40px;font-family:sans-serif;color:#d64545;">
      Could not load forecast data: ${err.message}.<br/>
      Make sure you ran <code>python generate_data.py</code> and started the backend with
      <code>uvicorn main:main_app --reload --app-dir backend</code>, then open
      <code>http://localhost:8000</code> (not the HTML file directly).
    </p>`;
  }
}

init();
