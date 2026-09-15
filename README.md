# Meteor Madness

**NASA Space Apps 2026 — The Next Frontier**

Atmospheric-entry physics engine driven by real NASA Near-Earth Object (NeoWs) data, with explicit land/ocean consequence branching and a transparent AI Analyst layer.

## Architecture (implemented)

```
☄️ ASTEROID (NASA NeoWs)
         │
         ▼
   ENTRY MODEL + ATMOSPHERIC SOLVER   ← RK4, drag, ablation, fragmentation
         │
         ▼
┌─────────────────────┐
│   LOCATION ENGINE   │  ← coordinates + surface_hint / heuristic
└──────────┬──────────┘
           │
  ┌────────┼────────┐
  ▼        ▼        ▼
LOCATION  TERRAIN  MATERIAL
  │        │        │
  └────────┼────────┘
           ▼
   IMPACT ENVIRONMENT
      /          \
   LAND          OCEAN
    │              │
    ▼              ▼
CRATER MODEL   TSUNAMI MODEL
    │              │
    └──────┬───────┘
           ▼
     CONSEQUENCES
           │
           ▼
     🤖 AI ANALYST
           │
           ▼
  CONFIDENCE + REPORT
```

## Quick start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export NASA_API_KEY=DEMO_KEY   # or your real key from api.nasa.gov
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173  (Vite proxies `/api` → backend)

## Key endpoints

- `GET  /api/neos` — live Near-Earth Objects
- `POST /api/simulation/entry` — direct physics simulation
- `POST /api/simulation/from-neo` — NeoWs → full pipeline (terrain → land/ocean → consequences → AI report)

## Design principles

- SI units only inside the physics engine
- Explicit energy bookkeeping (no “impact energy = initial KE”)
- All screening models carry clear limitation statements
- AI Analyst is rule-based and fully offline for reproducibility
- Existing atmospheric solver and land-crater path remain unchanged

## Status

Branch: `feature/next-frontier-architecture`  
Core physics: production-ready for educational / screening use  
New layers: Location Engine, Tsunami screening, AI Analyst — implemented and wired
