# WOEnv Dashboard

Well Operating Envelope Dashboard — a web application for managing and visualising
petroleum well operating envelopes across the UGHE, UTOR and UGWest fields.

## Features

- **Fleet overview** — well counts, oil/water/gas rates and water cut across all fields
- **Envelope alerts** — wells producing above their erosional limit or flowing sub-critically
- **Per-well detail** — operating envelope, production, water-cut and gas-ratio trends
- **Workbook ingestion** — imports Historical Data, Erosional Rates and Envelope Data sheets
- **Bean models** — Gilbert, Ros, Baxendell and Achong choke correlations
- **Role-based access** — admin, engineer and viewer roles
- **Light and dark themes**

## Tech stack

- **Frontend** — React 18, TypeScript, Vite, Tailwind CSS, Recharts, TanStack Query
- **Backend** — FastAPI, SQLAlchemy 2
- **Data** — PostgreSQL 15
- **Deployment** — Docker Compose behind nginx locally; Render, Vercel and Neon
  in production, see [DEPLOY.md](DEPLOY.md)

## Quick start

### Docker

```bash
cp .env.example .env
```

Generate a signing key and put it in `.env` as `SECRET_KEY` — the stack refuses to
start without one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then bring everything up:

```bash
docker compose up -d --build
```

The backend container migrates the schema on every start, so there is no
separate migration step under Docker.

Create the first admin user:

```bash
docker compose exec backend python -m scripts.seed_admin
```

The generated password is printed once. Alternatively set `ADMIN_PASSWORD` in
`.env` and the container creates the user on startup — this is the path the
Render deployment uses, since its free plan has no shell.

The app is then at http://localhost:3000,
the API at http://localhost:8000 and its docs at http://localhost:8000/docs.

### Manual setup

Backend:

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.migrate_schema
python -m scripts.seed_admin
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to port 8000, so no `VITE_API_URL` is needed locally.

## Maintenance scripts

Run from `backend/`:

| Command | Purpose |
| --- | --- |
| `python -m scripts.migrate_schema` | Add any missing columns and indexes. Idempotent. |
| `python -m scripts.seed_admin` | Create or reset the admin user. |
| `python -m scripts.reingest_uploads` | Re-run ingestion over every workbook in `uploads/`. Idempotent. |
| `python -m scripts.normalize_data --dry-run` | Report data repairs without writing. |
| `python -m scripts.normalize_data` | Apply them. Safe to re-run. |
| `python -m scripts.remove_field CODE [CODE...]` | Delete a field and all its wells, tests and envelopes. Supports `--dry-run`. |

### Managed fields

The app manages **UGHE**, **UTOR** and **UGWest**. Workbooks belonging to any
other field are rejected on upload and skipped by `reingest_uploads`.

OGIN and YOKRI were retired on 2026-08-07. To bring a field back, move its
patterns into `FIELD_CODE_MAP` and add a display name to `FIELD_NAMES` in
[`app/services/data_ingestion.py`](backend/app/services/data_ingestion.py) —
see `RETIRED_FIELD_CODES` — then re-run `python -m scripts.reingest_uploads`.

## Tests

```bash
cd backend && python -m pytest tests/ -q
```

## Data model notes

Several columns in the source workbooks are named misleadingly. Ingestion
reconciles them; these notes explain what is stored.

- **BSW** is stored as a **percentage** (0–100). The workbook's `Raw BSW (%)`
  column is a true percentage while `BSW (%)` is a fraction of the same value.
- **Gas rate** is derived as `oil rate × GOR`. The workbook's
  `Calculated Gas (Mscf/d)` column actually carries MMscf/d, so deriving the
  value sidesteps the mislabelling.
- **GOR and GLR are distinct.** GOR is gas per barrel of *oil*; GLR is gas per
  barrel of *gross liquid*, computed as `GOR × (1 − BSW)`. At 86% water cut they
  differ by roughly a factor of seven.
- **Well status** is normalised to `Flowing`, `Closed-in`, `Suspended` or
  `Unknown`. The raw data contains nine spellings of these four states.
- **Test rows are deduplicated** on `(well, test date)`, so re-uploading the same
  workbook is a no-op.

## Calculations

### Bean (choke) correlations

All four follow the Gilbert family form, in psig / scf·stb⁻¹ / stb·d⁻¹ / 64ths:

```
P_wh = A × GLR^B × Q / S^C
```

| Model | A | B | C |
| --- | --- | --- | --- |
| Gilbert | 10.00 | 0.546 | 1.89 |
| Ros | 17.40 | 0.500 | 2.00 |
| Baxendell | 9.56 | 0.546 | 1.93 |
| Achong | 3.82 | 0.650 | 1.88 |

Validated against 86 critical-flow, natural-flow tests from the field workbooks,
driven by measured GOR. Median absolute error: **Achong 20%**, Baxendell 27%,
Ros 34%, Gilbert 39%. Achong is therefore the default when a well has no model
assigned.

The workbooks also reference an in-house **SW Ampa** model. Its constants are not
published, so wells assigned to it fall back to Achong and the UI says so.

These correlations are only valid in critical (sonic) flow. The workbooks treat
flow as critical when FTHP ≥ 1.7 × flowline pressure, and the app reports when a
well falls below that.

### Erosional limits

The governing erosional rate limit comes from the workbook's `Qerosion` column,
computed by the asset engineers in Prosper. Where it is absent, the app falls
back to API RP 14E:

```
ρ_m = (12409·SG_l·P + 2.7·R·SG_g·P) / (198.7·P + R·T·Z)
V_e = C / √ρ_m
```

with C = 100 for continuous non-corrosive service. The velocity limit is then
converted to a liquid rate using the completion bore and in-situ gas volume.

## Project structure

```
woenv-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/          # Routes: auth, fields, wells, envelopes, upload, stats
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # calculations, workbook parsing, ingestion, envelopes
│   │   └── tasks/        # Celery tasks
│   ├── scripts/          # Migration, seeding and data-repair utilities
│   └── tests/            # pytest suite
├── frontend/
│   └── src/
│       ├── components/   # ui primitives, charts, layout
│       ├── pages/        # Dashboard, Fields, Wells, WellDetail, Upload, Login
│       ├── services/     # API client and types
│       └── stores/       # Auth and theme state
└── docker-compose.yml
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Obtain a bearer token |
| `GET` | `/api/v1/auth/me` | Current user and role |
| `GET` | `/api/v1/stats/overview` | Fleet totals, optionally by field |
| `GET` | `/api/v1/stats/fields` | Per-field breakdown |
| `GET` | `/api/v1/stats/envelope-alerts` | Wells breaching an envelope bound |
| `GET` | `/api/v1/fields` | List fields |
| `GET` | `/api/v1/wells` | List wells, filterable by field and status |
| `GET` | `/api/v1/wells/{id}/history` | Test history |
| `GET` | `/api/v1/envelopes/{well_id}` | Operating envelope (read-only) |
| `POST` | `/api/v1/envelopes/compute/{well_id}` | Recompute and persist the envelope |
| `POST` | `/api/v1/upload/excel` | Upload a field workbook |

CSV upload is not supported: ingestion depends on the workbook's multiple sheets.

## License

Proprietary — all rights reserved.
