# Sharp Operations Center

A full-stack trucking operations dashboard built to turn operational records
into useful decisions, reviewable billing, and polished report artifacts.

> **Portfolio-safe demo:** every person, customer, route, load, tractor count,
> and financial value in this repository is synthetic. Production credentials,
> SQL queries, customer records, and deployment details are intentionally excluded.

## What it demonstrates

- An owner-facing morning brief with fleet capacity, utilization, service,
  deadhead, revenue, manager scorecards, configurable goals, and alerts.
- Lane-profitability PDFs with separate outbound/inbound analysis and visual
  round-trip performance bands.
- A multi-stop customer invoice workflow with selectable bill dates, editable
  order charges, expected-total variance warnings, and formatted XLSX output.
- Fleet-cost versus revenue analysis grouped by day, Sunday–Saturday week, or
  month, with interactive charts plus CSV and PNG exports.
- A live load-pricing calculator for deadhead, fuel surcharge, CPM, target
  margin, and required inbound/outbound rates.
- Request IDs, structured logs, health/readiness endpoints, tests, containers,
  and automated dependency/build checks.

## Architecture

```text
Browser
  └── nginx reverse proxy
      ├── React + Vinext frontend
      └── FastAPI backend
          ├── reporting services
          ├── PDF / XLSX / CSV / PNG generators
          └── repository interface
              └── seeded SQLite demo database
```

The public repository is intentionally locked to `DATA_MODE=demo`. SQLite is
seeded on first use with deterministic records covering 2025–2027. The private
application swaps the repository implementation for a read-only enterprise data
adapter; that implementation is not part of this project.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). The SQLite database is
created automatically in the `demo-data` Docker volume.

## Run for development

Backend:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Useful demo dates are
preselected in the interface; invoice billing dates are loaded from SQLite.

## Quality checks

```bash
uv run pytest
uv run ruff check app tests
cd frontend && npm run lint && npm run build
```

GitHub Actions runs the backend and frontend checks for every push and pull
request. Dependabot watches both Python and npm dependencies.

## Data-safety boundary

The public database schema models only what the UI and report generators need.
It is not a copy of the production schema. The repository contains no live
database hostname, username, password, internal network address, employee name,
customer identifier, general-ledger account, or production report output.

## Tech stack

Python 3.12 · FastAPI · SQLite · pandas · Matplotlib · ReportLab · openpyxl ·
React 19 · TypeScript · Vinext · nginx · Docker Compose · GitHub Actions

## License

MIT — see [LICENSE](LICENSE).

The Sharp Transportation logo is displayed for portfolio context and is not
licensed for reuse under the MIT License.
