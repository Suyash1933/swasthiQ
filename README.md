# SwasthiQ Pharmacy Assignment

This repository now includes a working backend setup for the SwasthiQ pharmacy hiring assignment:

- `frontend/` contains the React app.
- `backend/` contains a FastAPI REST API backed by SQLite.

## Backend Stack

- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

## Backend Features

- Auto-seeded pharmacy data on first run
- Dashboard APIs for sales, items sold, low stock, purchase orders, and recent sales
- Inventory APIs for listing, searching, filtering, creating, updating, and status changes
- Validation and proper HTTP status codes
- Interactive Swagger docs at `/docs`

## Run The Project

### 1. Start the backend

```powershell
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend

```powershell
cd frontend
npm run dev
```

The Vite dev server is configured to proxy `/api` calls to `http://127.0.0.1:8000`.

## REST API Contracts

### Dashboard

- `GET /api/dashboard/overview`
- `GET /api/dashboard/sales-summary`
- `GET /api/dashboard/items-sold`
- `GET /api/dashboard/low-stock`
- `GET /api/dashboard/purchase-orders/summary`
- `GET /api/dashboard/recent-sales?limit=5`
- `POST /api/sales/bill`

### Inventory

- `GET /api/inventory/summary`
- `GET /api/medicines?search=para&status=low_stock&category=Antibiotic`
- `GET /api/medicines/{medicine_id}`
- `POST /api/medicines`
- `PUT /api/medicines/{medicine_id}`
- `PATCH /api/medicines/{medicine_id}/status`

Example request body for `POST /api/medicines`:

```json
{
  "name": "Ibuprofen",
  "generic_name": "Ibuprofen",
  "manufacturer": "Sun Pharma",
  "supplier_name": "Medline Traders",
  "category": "Pain Relief",
  "dosage_form": "Tablet",
  "strength": "400 mg",
  "batch_number": "IBU-2408",
  "quantity": 55,
  "unit_price": 5.6,
  "reorder_level": 15,
  "expiry_date": "2026-12-31",
  "location": "Rack A2",
  "manual_expired": false
}
```

Example request body for `PATCH /api/medicines/{medicine_id}/status`:

```json
{
  "status": "out_of_stock"
}
```

Example request body for `POST /api/sales/bill`:

```json
{
  "patient_id": "PT-2045",
  "payment_method": "Cash",
  "cashier_name": "Counter Desk",
  "items": [
    {
      "medicine_id": 1,
      "quantity": 2
    },
    {
      "medicine_id": 5,
      "quantity": 1
    }
  ]
}
```

To reactivate an out-of-stock item:

```json
{
  "status": "active",
  "quantity": 25
}
```

## Consistency Rules

- Inventory status is derived consistently from expiry and stock quantity.
- Expired items remain expired until updated with a valid expiry date and reactivated.
- Out-of-stock items are set by quantity reaching `0`.
- Low-stock items are derived when `quantity <= reorder_level`.
