# Sharp Operations Center

[![CI](https://github.com/jadogg22/sharp-operations-center/actions/workflows/ci.yml/badge.svg)](https://github.com/jadogg22/sharp-operations-center/actions/workflows/ci.yml)

I built this to replace a pile of one-off spreadsheets and reports with one
place where our team can check the operation, review billing, and work through
pricing decisions.

This repository is the public version of that work. It runs on made-up data and
does not include the production database adapter, company records, customer
names, contract details, or internal deployment information.

## What is in it

The owner overview answers the questions that usually come up first thing in
the morning: How many trucks are working? How much deadhead are we running? Are
we hitting service goals? Where does somebody need to take a closer look?

![Owner overview running with synthetic fleet data](docs/images/owner-overview.png)

The rest of the app covers a few jobs that used to take more manual work:

- comparing outbound and inbound lane performance in a PDF;
- reviewing a recurring multi-stop customer's charges before creating an XLSX
  invoice;
- comparing fleet cost with revenue by day, week, or month;
- exporting the numbers as CSV or a chart; and
- testing load rates against miles, deadhead, fuel surcharge, cost per mile,
  and a target margin.

The pricing builder turns those inputs into a return-load target while keeping
the assumptions visible to the person quoting the load.

![Load pricing builder with fictional rates and mileage](docs/images/load-pricing-builder.png)

The billing workflow is deliberately anonymous. The demo shows why it exists—
one bill date can contain several loads, and each load may visit several
delivery locations—without identifying the customer or exposing its freight.

![Anonymous invoice review using fictional orders](docs/images/invoice-review.png)

## A note about the demo data

The SQLite database is seeded the first time the backend starts. The names,
routes, orders, equipment counts, and dollar amounts are fictional. They are
there so every screen and export works after a fresh clone.

In the private application, the repository layer points at a read-only
operational data source. That adapter and its queries are intentionally not in
this repo.

## Run it

The easiest route is Docker:

```bash
cp .env.example .env
docker compose up --build
```

Then open [http://localhost:8080](http://localhost:8080).

For local development, start the API:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Then start the frontend in another terminal:

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

The frontend will be available at [http://localhost:3000](http://localhost:3000).

## How it is put together

```text
Browser
  └── nginx
      ├── React + TypeScript frontend
      └── FastAPI backend
          ├── overview and report services
          ├── PDF, XLSX, CSV, and PNG exporters
          └── repository layer
              └── SQLite demo database
```

The backend is Python 3.12 with FastAPI, pandas, Matplotlib, ReportLab, and
openpyxl. The frontend uses React, TypeScript, and Vinext. GitHub Actions runs
the tests, lint, frontend build, and Docker build on every pull request.

## Checks

```bash
uv run ruff check app tests
uv run pytest
cd frontend && npm run lint && npm run build
```

## License

The code is available under the [MIT License](LICENSE). The Sharp
Transportation logo is included for project context and is not licensed for
reuse.
