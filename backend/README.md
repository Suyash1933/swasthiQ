# Backend Setup

This backend uses FastAPI with a local SQLite database and seeds demo pharmacy data on first run.

## Install

```powershell
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

API docs will be available at `http://127.0.0.1:8000/docs`.

## Main Endpoints

- `GET /api/health`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/sales-summary`
- `GET /api/dashboard/items-sold`
- `GET /api/dashboard/low-stock`
- `GET /api/dashboard/purchase-orders/summary`
- `GET /api/dashboard/recent-sales`
- `GET /api/inventory/summary`
- `GET /api/medicines`
- `GET /api/medicines/{medicine_id}`
- `POST /api/medicines`
- `PUT /api/medicines/{medicine_id}`
- `PATCH /api/medicines/{medicine_id}/status`
