from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from collections import defaultdict
import os

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.orm import Session

from .database import Base, DATABASE_LABEL, USING_SQLITE, engine, get_db
from .models import Medicine, PurchaseOrder, Sale, SaleItem
from .schemas import (
    DashboardOverview,
    DashboardOverviewResponse,
    HealthResponse,
    InventorySummary,
    InventorySummaryResponse,
    ItemsSoldResponse,
    ItemsSoldSummary,
    LowStockItem,
    LowStockResponse,
    MedicineCreate,
    MedicineListMeta,
    MedicineListResponse,
    MedicineResponse,
    MedicineResponseData,
    MedicineStatus,
    MedicineStatusUpdate,
    MedicineUpdate,
    PurchaseOrderSummary,
    PurchaseOrderSummaryResponse,
    RecentSaleItem,
    RecentSalesResponse,
    SaleBillRequest,
    SaleBillResponse,
    SalesSummary,
    SalesSummaryResponse,
    StatusUpdateAction,
)
from .seed import seed_database


def resolve_status(medicine: Medicine, today: date | None = None) -> MedicineStatus:
    today = today or date.today()
    if medicine.manual_expired or medicine.expiry_date < today:
        return MedicineStatus.EXPIRED
    if medicine.quantity <= 0:
        return MedicineStatus.OUT_OF_STOCK
    if medicine.quantity <= medicine.reorder_level:
        return MedicineStatus.LOW_STOCK
    return MedicineStatus.ACTIVE


def serialize_medicine(medicine: Medicine) -> MedicineResponseData:
    return MedicineResponseData.model_validate(
        {
            "id": medicine.id,
            "name": medicine.name,
            "generic_name": medicine.generic_name,
            "manufacturer": medicine.manufacturer,
            "supplier_name": medicine.supplier_name,
            "category": medicine.category,
            "dosage_form": medicine.dosage_form,
            "strength": medicine.strength,
            "batch_number": medicine.batch_number,
            "quantity": medicine.quantity,
            "unit_price": round(medicine.unit_price, 2),
            "reorder_level": medicine.reorder_level,
            "expiry_date": medicine.expiry_date,
            "location": medicine.location,
            "manual_expired": medicine.manual_expired,
            "status": resolve_status(medicine),
            "stock_value": round(medicine.quantity * medicine.unit_price, 2),
            "created_at": medicine.created_at,
            "updated_at": medicine.updated_at,
        }
    )


def summarize_medicine_names(names: list[str]) -> str:
    unique_names = []
    for name in names:
        if name not in unique_names:
            unique_names.append(name)

    if not unique_names:
        return "No medicines"
    if len(unique_names) == 1:
        return unique_names[0]
    if len(unique_names) == 2:
        return ", ".join(unique_names)
    return f"{unique_names[0]}, {unique_names[1]} +{len(unique_names) - 2} more"


def serialize_recent_sale(sale: Sale) -> RecentSaleItem:
    return RecentSaleItem(
        id=sale.id,
        invoice_number=sale.invoice_number,
        medicine_name=sale.medicine_name,
        customer_name=sale.customer_name,
        payment_method=sale.payment_method,
        item_count=sale.item_count,
        units_sold=sale.units_sold,
        total_amount=round(sale.total_amount, 2),
        sold_at=sale.sold_at,
        cashier_name=sale.cashier_name,
    )


def build_invoice_number(session: Session, sold_at: datetime) -> str:
    day_code = sold_at.strftime("%Y%m%d")
    start = datetime.combine(sold_at.date(), time.min)
    end = start + timedelta(days=1)
    today_count = session.query(Sale).filter(Sale.sold_at >= start, Sale.sold_at < end).count()
    return f"INV-{day_code}-{today_count + 1:03d}"


def build_sales_summary(session: Session) -> SalesSummary:
    today = date.today()
    start = datetime.combine(today, time.min)
    end = start + timedelta(days=1)

    sales = session.scalars(
        select(Sale).where(Sale.sold_at >= start, Sale.sold_at < end).order_by(Sale.sold_at.desc())
    ).all()

    return SalesSummary(
        date=today,
        total_sales_amount=round(sum(sale.total_amount for sale in sales), 2),
        transaction_count=len(sales),
    )


def build_items_sold_summary(session: Session) -> ItemsSoldSummary:
    today = date.today()
    start = datetime.combine(today, time.min)
    end = start + timedelta(days=1)

    sale_items = session.scalars(
        select(SaleItem).join(Sale).where(Sale.sold_at >= start, Sale.sold_at < end)
    ).all()

    return ItemsSoldSummary(
        date=today,
        total_units_sold=sum(item.quantity for item in sale_items),
        unique_medicines_sold=len({item.medicine_name for item in sale_items}),
    )


def build_low_stock_items(session: Session) -> list[LowStockItem]:
    medicines = session.scalars(select(Medicine).order_by(Medicine.name.asc())).all()
    low_stock_items: list[LowStockItem] = []

    for medicine in medicines:
        status_value = resolve_status(medicine)
        if status_value in {MedicineStatus.LOW_STOCK, MedicineStatus.OUT_OF_STOCK}:
            low_stock_items.append(
                LowStockItem(
                    id=medicine.id,
                    name=medicine.name,
                    batch_number=medicine.batch_number,
                    quantity=medicine.quantity,
                    reorder_level=medicine.reorder_level,
                    status=status_value,
                )
            )

    return low_stock_items


def build_purchase_order_summary(session: Session) -> PurchaseOrderSummary:
    orders = session.scalars(select(PurchaseOrder)).all()

    pending_orders = [order for order in orders if order.status == "pending"]
    in_transit_orders = [order for order in orders if order.status == "in_transit"]
    completed_orders = [order for order in orders if order.status == "completed"]

    return PurchaseOrderSummary(
        pending_count=len(pending_orders),
        in_transit_count=len(in_transit_orders),
        completed_count=len(completed_orders),
        pending_value=round(sum(order.total_amount for order in pending_orders), 2),
    )


def build_recent_sales(session: Session, limit: int = 5) -> list[RecentSaleItem]:
    sales = session.scalars(select(Sale).order_by(Sale.sold_at.desc()).limit(limit)).all()
    return [serialize_recent_sale(sale) for sale in sales]


def build_inventory_summary(session: Session) -> InventorySummary:
    medicines = session.scalars(select(Medicine)).all()
    counts = {
        MedicineStatus.ACTIVE: 0,
        MedicineStatus.LOW_STOCK: 0,
        MedicineStatus.EXPIRED: 0,
        MedicineStatus.OUT_OF_STOCK: 0,
    }

    total_inventory_value = 0.0
    for medicine in medicines:
        status_value = resolve_status(medicine)
        counts[status_value] += 1
        total_inventory_value += medicine.quantity * medicine.unit_price

    return InventorySummary(
        total_medicines=len(medicines),
        active=counts[MedicineStatus.ACTIVE],
        low_stock=counts[MedicineStatus.LOW_STOCK],
        expired=counts[MedicineStatus.EXPIRED],
        out_of_stock=counts[MedicineStatus.OUT_OF_STOCK],
        total_inventory_value=round(total_inventory_value, 2),
    )


def create_sale_bill(session: Session, payload: SaleBillRequest) -> Sale:
    normalized_quantities: dict[int, int] = defaultdict(int)
    for item in payload.items:
        normalized_quantities[item.medicine_id] += item.quantity

    medicine_ids = list(normalized_quantities.keys())
    medicines = session.scalars(
        select(Medicine).where(Medicine.id.in_(medicine_ids)).order_by(Medicine.name.asc())
    ).all()
    medicines_by_id = {medicine.id: medicine for medicine in medicines}

    missing_ids = [medicine_id for medicine_id in medicine_ids if medicine_id not in medicines_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine not found for ids: {', '.join(str(item) for item in missing_ids)}.",
        )

    sold_at = datetime.now()
    sale = Sale(
        invoice_number=build_invoice_number(session, sold_at),
        medicine_id=medicine_ids[0] if len(medicine_ids) == 1 else None,
        medicine_name="",
        customer_name=payload.patient_id,
        payment_method=payload.payment_method,
        item_count=0,
        units_sold=0,
        total_amount=0.0,
        sold_at=sold_at,
        cashier_name=payload.cashier_name,
    )
    session.add(sale)
    session.flush()

    total_amount = 0.0
    total_units_sold = 0
    sold_names: list[str] = []

    for medicine_id, quantity in normalized_quantities.items():
        medicine = medicines_by_id[medicine_id]
        medicine_status = resolve_status(medicine)

        if medicine_status == MedicineStatus.EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{medicine.name} is expired and cannot be billed.",
            )
        if medicine_status == MedicineStatus.OUT_OF_STOCK:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{medicine.name} is out of stock and cannot be billed.",
            )
        if quantity > medicine.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Only {medicine.quantity} units of {medicine.name} are available.",
            )

        line_total = round(quantity * medicine.unit_price, 2)
        medicine.quantity -= quantity
        total_amount += line_total
        total_units_sold += quantity
        sold_names.append(medicine.name)

        session.add(
            SaleItem(
                sale_id=sale.id,
                medicine_id=medicine.id,
                medicine_name=medicine.name,
                quantity=quantity,
                unit_price=medicine.unit_price,
                line_total=line_total,
            )
        )

    sale.medicine_name = summarize_medicine_names(sold_names)
    sale.item_count = len(normalized_quantities)
    sale.units_sold = total_units_sold
    sale.total_amount = round(total_amount, 2)

    session.commit()
    session.refresh(sale)
    return sale


def get_medicine_or_404(session: Session, medicine_id: int) -> Medicine:
    medicine = session.get(Medicine, medicine_id)
    if medicine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found.")
    return medicine


def ensure_unique_batch_number(session: Session, batch_number: str, current_id: int | None = None) -> None:
    existing = session.scalar(select(Medicine).where(Medicine.batch_number == batch_number))
    if existing and existing.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A medicine with this batch number already exists.",
        )


def ensure_demo_schema() -> None:
    if not USING_SQLITE:
        Base.metadata.create_all(bind=engine)
        return

    inspector = inspect(engine)
    expected_columns = {
        "medicines": {"generic_name", "supplier_name"},
        "sales": {"invoice_number", "customer_name", "payment_method", "item_count"},
        "sale_items": {"sale_id", "medicine_name", "quantity", "line_total"},
    }

    try:
        tables = set(inspector.get_table_names())
    except Exception:
        tables = set()

    needs_reset = False
    for table_name, required_columns in expected_columns.items():
        if table_name not in tables:
            if tables:
                needs_reset = True
                break
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if not required_columns.issubset(existing_columns):
            needs_reset = True
            break

    if not needs_reset and {"sales", "sale_items"}.issubset(tables):
        with Session(engine) as session:
            sales_count = session.query(Sale).count()
            sale_items_count = session.query(SaleItem).count()
            if sales_count > 0 and sale_items_count < sales_count:
                needs_reset = True

    if needs_reset:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_demo_schema()
    with Session(engine) as session:
        seed_database(session)
    yield


app = FastAPI(
    title="SwasthiQ Pharmacy Backend",
    version="1.0.0",
    description="REST APIs for the SwasthiQ pharmacy dashboard and inventory assignment.",
    lifespan=lifespan,
)

default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://swasthi-q-two.vercel.app",
]
configured_cors_origins = os.getenv("CORS_ORIGINS", "")
allowed_origins: list[str] = []

for origin in [*default_cors_origins, *configured_cors_origins.split(",")]:
    normalized_origin = origin.strip().rstrip("/")
    if normalized_origin and normalized_origin not in allowed_origins:
        allowed_origins.append(normalized_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", database=DATABASE_LABEL)


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "SwasthiQ backend is running.",
        "frontend_url": "https://swasthi-q-two.vercel.app",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "database": DATABASE_LABEL,
    }


@app.get("/favicon.ico", include_in_schema=False, status_code=status.HTTP_204_NO_CONTENT)
def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(db: Session = Depends(get_db)):
    return DashboardOverviewResponse(
        data=DashboardOverview(
            sales_summary=build_sales_summary(db),
            items_sold=build_items_sold_summary(db),
            low_stock_items=build_low_stock_items(db),
            purchase_order_summary=build_purchase_order_summary(db),
            recent_sales=build_recent_sales(db),
        )
    )


@app.get("/api/dashboard/sales-summary", response_model=SalesSummaryResponse)
def get_sales_summary(db: Session = Depends(get_db)):
    return SalesSummaryResponse(data=build_sales_summary(db))


@app.get("/api/dashboard/items-sold", response_model=ItemsSoldResponse)
def get_items_sold(db: Session = Depends(get_db)):
    return ItemsSoldResponse(data=build_items_sold_summary(db))


@app.get("/api/dashboard/low-stock", response_model=LowStockResponse)
def get_low_stock_items(db: Session = Depends(get_db)):
    return LowStockResponse(data=build_low_stock_items(db))


@app.get("/api/dashboard/purchase-orders/summary", response_model=PurchaseOrderSummaryResponse)
def get_purchase_order_summary(db: Session = Depends(get_db)):
    return PurchaseOrderSummaryResponse(data=build_purchase_order_summary(db))


@app.get("/api/dashboard/recent-sales", response_model=RecentSalesResponse)
def get_recent_sales(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return RecentSalesResponse(data=build_recent_sales(db, limit=limit))


@app.post("/api/sales/bill", response_model=SaleBillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(payload: SaleBillRequest, db: Session = Depends(get_db)):
    sale = create_sale_bill(db, payload)
    return SaleBillResponse(
        message="Bill created successfully.",
        data=serialize_recent_sale(sale),
    )


@app.get("/api/inventory/summary", response_model=InventorySummaryResponse)
def get_inventory_summary(db: Session = Depends(get_db)):
    return InventorySummaryResponse(data=build_inventory_summary(db))


@app.get("/api/medicines", response_model=MedicineListResponse)
def list_medicines(
    search: str | None = Query(default=None, max_length=120),
    status_filter: MedicineStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
):
    query = select(Medicine).order_by(Medicine.name.asc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Medicine.name.ilike(term),
                Medicine.generic_name.ilike(term),
                Medicine.manufacturer.ilike(term),
                Medicine.supplier_name.ilike(term),
                Medicine.category.ilike(term),
                Medicine.batch_number.ilike(term),
            )
        )

    if category:
        query = query.where(func.lower(Medicine.category) == category.strip().lower())

    medicines = db.scalars(query).all()
    serialized = [serialize_medicine(medicine) for medicine in medicines]

    if status_filter:
        serialized = [medicine for medicine in serialized if medicine.status == status_filter]

    return MedicineListResponse(
        data=serialized,
        meta=MedicineListMeta(
            total=len(serialized),
            returned=len(serialized),
            search=search,
            status=status_filter,
            category=category,
        ),
    )


@app.get("/api/medicines/{medicine_id}", response_model=MedicineResponse)
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    medicine = get_medicine_or_404(db, medicine_id)
    return MedicineResponse(message="Medicine fetched successfully.", data=serialize_medicine(medicine))


@app.post("/api/medicines", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
def create_medicine(payload: MedicineCreate, db: Session = Depends(get_db)):
    ensure_unique_batch_number(db, payload.batch_number)

    medicine = Medicine(**payload.model_dump())
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    return MedicineResponse(message="Medicine created successfully.", data=serialize_medicine(medicine))


@app.put("/api/medicines/{medicine_id}", response_model=MedicineResponse)
def update_medicine(medicine_id: int, payload: MedicineUpdate, db: Session = Depends(get_db)):
    medicine = get_medicine_or_404(db, medicine_id)
    updates = payload.model_dump(exclude_unset=True)

    if "batch_number" in updates:
        ensure_unique_batch_number(db, updates["batch_number"], current_id=medicine.id)

    for field_name, value in updates.items():
        setattr(medicine, field_name, value)

    db.commit()
    db.refresh(medicine)

    return MedicineResponse(message="Medicine updated successfully.", data=serialize_medicine(medicine))


@app.patch("/api/medicines/{medicine_id}/status", response_model=MedicineResponse)
def update_medicine_status(medicine_id: int, payload: MedicineStatusUpdate, db: Session = Depends(get_db)):
    medicine = get_medicine_or_404(db, medicine_id)

    if payload.status == StatusUpdateAction.EXPIRED:
        medicine.manual_expired = True
    elif payload.status == StatusUpdateAction.OUT_OF_STOCK:
        medicine.manual_expired = False
        medicine.quantity = 0
    elif payload.status == StatusUpdateAction.ACTIVE:
        medicine.manual_expired = False
        if medicine.expiry_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expired medicines need a new expiry date before they can be reactivated.",
            )
        if payload.quantity is not None:
            medicine.quantity = payload.quantity
        if medicine.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide a positive quantity to reactivate an out-of-stock medicine.",
            )

    db.commit()
    db.refresh(medicine)

    return MedicineResponse(message="Medicine status updated successfully.", data=serialize_medicine(medicine))
