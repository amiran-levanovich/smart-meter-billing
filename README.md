# WattWunder: smart-meter billing

This app computes a bakery's monthly electricity bill from 15-minute smart-meter readings on a day/night tariff and shows it to the customer on a screen in German. The original task is in [TASK.md](TASK.md). The computed total and the decisions behind it are in [NOTES.md](NOTES.md).

## Prerequisites

You need [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 by itself), Node.js 24 (`.nvmrc`) and make. If `uv --version`, `node --version` or `make --version` already works, skip that step.

```sh
# 1. make and curl
xcode-select --install                                   # macOS
sudo apt-get update && sudo apt-get install -y make curl # Linux / WSL (Debian, Ubuntu)

# 2. uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

# 3. Node.js 24 via nvm (run from the repo root, nvm reads .nvmrc)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install
```

## Run

```sh
make install   # backend deps via uv, frontend deps via npm ci
make dev       # API on :8000, screen on :5173
```

Open <http://localhost:5173>. On first start the backend creates `backend/billing.db`, runs the migrations and imports `readings.csv` and `tariff.json`. The screen opens on the latest month with readings: October 2026, total **2.295,99 €**.

## Test

```sh
make test        # pytest (billing core, HTTP API on a temp DB) + vitest (screen)
make crosscheck  # independent pandas recomputation of the October total
make lint        # ruff, oxlint, tsc
```

## Post a reading

The seeded meter has the public ID `3f6c1a52-8e0b-4b7e-9a51-2d4f7c9e0b18`. Sending the real value for the one missing interval (13 Oct, 14:30) replaces the estimate:

```sh
curl -X POST http://localhost:8000/api/meters/3f6c1a52-8e0b-4b7e-9a51-2d4f7c9e0b18/readings \
  -H 'content-type: application/json' \
  -d '[{"timestamp": "2026-10-13T14:30:00+02:00", "energy_wh": 2300}]'
# {"inserted":1,"corrected":0,"unchanged":0}
```

Reload the screen: the "geschätzt" notice is gone and the total is 2.296,00 €. If you send a different value for an interval that already has one, the screen marks it "korrigiert".

## More months

```sh
make demo   # adds 5 synthetic months before October (one left empty) and the current month up to now
```

The demo months are placed relative to today, so the screen opens on the current month, billed up to the latest reading ("laufender Monat"). Switch months with ‹ › next to the title or with `?month=YYYY-MM`. The empty month shows a fee-only bill. To start over, delete `backend/billing.db`.

## API

- `GET /api/bill/{YYYY-MM}`: the bill for the logged-in customer (login is stubbed: it is always the seeded customer)
- `GET /api/months`: first and last month with readings (bills outside that range are 404)
- `POST /api/meters/{public_id}/readings`: batch of `{timestamp, energy_wh}`

Interactive docs at <http://localhost:8000/docs>. After you change an API schema, run `make types` to regenerate the frontend types. `make test` fails if you forget.

## Layout

- `backend/app/billing.py`: pure billing core (pricing, DST, gaps, rounding, VAT)
- `backend/app/ingest.py`, `seed.py`, `bills.py`, `main.py`: storage, CSV import, API
- `backend/scripts/crosscheck.py`: independent check, imports nothing from the app
- `frontend/src/BillScreen.tsx`, `DailyChart.tsx`: the customer screen
