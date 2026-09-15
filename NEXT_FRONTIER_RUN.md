# Next Frontier — run checklist

Branch: `feature/next-frontier-architecture`

## 1. Backend (required once)

```bash
cd backend
python apply_next_frontier_patch.py   # wires enrich_payload into main.py
export NASA_API_KEY=DEMO_KEY         # or your real key
export GEMINI_API_KEY=...            # optional; falls back to rule-based analyst
uvicorn main:app --reload --port 8000
```

Verify:

```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/api/neos | head
```

## 2. Frontend

If App.jsx looks minimal or broken, restore the full UI from main then patch:

```bash
git checkout main -- frontend/src/App.jsx
python frontend/apply_frontend_patch.py
```

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL. Select an asteroid → set lat/lon → **Run simulation**.

You should see:
- physics / consequences (existing)
- **Location engine** (terrain)
- **Tsunami screening** (ocean impacts)
- **AI Analyst** (Gemini if `GEMINI_API_KEY` set, else rule-based)

## Architecture

Asteroid → Entry model → Atmospheric solver → Location engine → Land/Ocean → Crater / Tsunami → Consequences → AI Analyst → Confidence + report

## Files

| Path | Role |
|------|------|
| `backend/physics/location_engine.py` | surface / material |
| `backend/physics/tsunami.py` | ocean screening |
| `backend/physics/ai_analyst.py` | Gemini + fallback |
| `backend/physics/enrichment.py` | attaches terrain/tsunami/analyst |
| `backend/apply_next_frontier_patch.py` | patches `main.py` |
| `frontend/src/components/AnalystPanel.jsx` | UI card |
| `frontend/src/analyst.css` | styles |
| `frontend/apply_frontend_patch.py` | wires panel into App.jsx |
