# Gurucul ThreatIntel Platform

A reusable, actor-scoped Threat Intelligence dashboard for ransomware/extortion groups.

## What this build contains

- Threat-actor profile dashboard for every registered actor.
- Actor-scoped victim, country and industry analytics.
- ISO country normalization and controlled industry taxonomy.
- Evidence/provenance and confidence for enrichment.
- Country coverage, industry coverage and overall data-quality metrics.
- Attack velocity, monthly victims and cumulative victims.
- Country exposure map-style grid, top countries and top industries.
- Country × industry targeting matrix.
- Recent victims with analyst detail drawer.
- Collection health and crawl metrics.
- Manual threat-group registration with group-specific extractors.
- Optional Ransomware.live API enrichment/import adapter.
- SQLite by default; PostgreSQL supported via `DATABASE_URL`.
- Synthetic demo data so the dashboard can be opened immediately.
- No Ransomware.live API key is required for demo mode.

## Important intelligence rule

Country and industry counts are calculated only from normalized records belonging to the selected actor.

Unknown metadata stays unknown. The application never turns missing country/industry data into a fabricated value.

Each enrichment value carries:
- source
- confidence
- evidence URL when available

## Quick start — Windows PowerShell

1. Extract this ZIP.
2. Open PowerShell in the extracted folder.
3. Run:

```powershell
.\RUN-WINDOWS.ps1
```

4. Open:

http://localhost:5173

Default local login:

```text
Email:    admin@example.com
Password: ChangeMe123!
```

The first startup seeds clearly labelled synthetic demo data for DragonForce, Qilin and Black Basta.

## Quick start — manual

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
cd ..
python scripts\seed_demo.py
uvicorn backend.app.main:app --reload --port 8001
```

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Live data

Set these in `backend/.env`:

```env
DEMO_MODE=false
SEED_DEMO_DATA=false
RANSOMWARE_LIVE_API_KEY=your_key_here
RANSOMWARE_LIVE_GROUP_ENDPOINT=https://api-pro.ransomware.live/REPLACE_WITH_DOCUMENTED_GROUP_ENDPOINT
```

The adapter is deliberately endpoint-configurable because the exact API route can vary by API plan/version. The application does not guess a live endpoint and silently import the wrong data.

The import endpoint is:

```text
POST /api/v1/integrations/ransomware-live/groups/{group_id}/sync
```

It accepts a flexible JSON response containing a list of victim objects. The adapter recognizes common keys such as:

- victim / name / company
- country
- activity / industry / sector
- published / published_at / date
- discovered / discovered_at
- description
- website / source_page / post_url

After import, run the enrichment endpoint if required.

## Production database

For PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/gurucul_threatintel
```

Then install:

```powershell
pip install -r requirements.txt
```

The included requirements contain `psycopg[binary]`.

## What to do after download

1. Run `RUN-WINDOWS.ps1`.
2. Verify the dashboard in demo mode.
3. Open Threat Actors and inspect DragonForce, Qilin and Black Basta.
4. Set `DEMO_MODE=false` and `SEED_DEMO_DATA=false`.
5. Add your Ransomware.live API key in `backend/.env`.
6. Set the exact API endpoint from your API documentation.
7. Register/configure the actors you want to monitor.
8. Sync live data.
9. Review Country/Industry coverage and unknown records.
10. Only then treat the analytics as production intelligence.

## Tests

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Frontend:

```powershell
cd frontend
npm install
npm run build
```

## Design references used

This implementation follows the concepts reviewed from the supplied RansomLook 2.0 and ransomware.live source packages:

- independent actor/group parsers
- actor-level statistics
- country exposure
- sector/industry statistics
- collection/source health
- victim-level records

The implementation is an independent codebase and does not bundle third-party project source.


## Optional Docker

```powershell
docker compose up --build
```

Open:

http://localhost:5173

The compose file uses PostgreSQL. Change the database password and JWT secret before any non-demo deployment.
