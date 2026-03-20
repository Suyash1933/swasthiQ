from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicineStatus(str, Enum):
    ACTIVE = "active"
    LOW_STOCK = "low_stock"
    EXPIRED = "expired"
    OUT_OF_STOCK = "out_of_stock"


class StatusUpdateAction(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    OUT_OF_STOCK = "out_of_stock"


class MedicineBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    generic_name: str = Field(min_length=2, max_length=120)
    manufacturer: str = Field(min_length=2, max_length=120)
    supplier_name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    dosage_form: str = Field(min_length=2, max_length=50)
    strength: str = Field(min_length=1, max_length=50)
    batch_number: str = Field(min_length=2, max_length=60)
    quantity: int = Field(ge=0)
    unit_price: float = Field(gt=0)
    reorder_level: int = Field(ge=0)
    expiry_date: date
    location: str = Field(min_length=2, max_length=80)
    manual_expired: bool = False

    @field_validator(
        "name",
        "generic_name",
        "manufacturer",
        "supplier_name",
        "category",
        "dosage_form",
        "strength",
        "batch_number",
        "location",
    )
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    generic_name: str | None = Field(default=None, min_length=2, max_length=120)
    manufacturer: str | None = Field(default=None, min_length=2, max_length=120)
    supplier_name: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    dosage_form: str | None = Field(default=None, min_length=2, max_length=50)
    strength: str | None = Field(default=None, min_length=1, max_length=50)
    batch_number: str | None = Field(default=None, min_length=2, max_length=60)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, gt=0)
    reorder_level: int | None = Field(default=None, ge=0)
    expiry_date: date | None = None
    location: str | None = Field(default=None, min_length=2, max_length=80)
    manual_expired: bool | None = None

    @field_validator(
        "name",
        "generic_name",
        "manufacturer",
        "supplier_name",
        "category",
        "dosage_form",
        "strength",
        "batch_number",
        "location",
    )
    @classmethod
    def strip_optional_whitespace(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class MedicineStatusUpdate(BaseModel):
    status: StatusUpdateAction
    quantity: int | None = Field(default=None, ge=1)


class MedicineResponseData(MedicineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MedicineStatus
    stock_value: float
    created_at: datetime
    updated_at: datetime | None = None


class MedicineResponse(BaseModel):
    message: str
    data: MedicineResponseData


class MedicineListMeta(BaseModel):
    total: int
    returned: int
    search: str | None = None
    status: MedicineStatus | None = None
    category: str | None = None


class MedicineListResponse(BaseModel):
    data: list[MedicineResponseData]
    meta: MedicineListMeta


class InventorySummary(BaseModel):
    total_medicines: int
    active: int
    low_stock: int
    expired: int
    out_of_stock: int
    total_inventory_value: float


class InventorySummaryResponse(BaseModel):
    data: InventorySummary


class SalesSummary(BaseModel):
    date: date
    total_sales_amount: float
    transaction_count: int


class SalesSummaryResponse(BaseModel):
    data: SalesSummary


class ItemsSoldSummary(BaseModel):
    date: date
    total_units_sold: int
    unique_medicines_sold: int


class ItemsSoldResponse(BaseModel):
    data: ItemsSoldSummary


class LowStockItem(BaseModel):
    id: int
    name: str
    batch_number: str
    quantity: int
    reorder_level: int
    status: MedicineStatus


class LowStockResponse(BaseModel):
    data: list[LowStockItem]


class PurchaseOrderSummary(BaseModel):
    pending_count: int
    in_transit_count: int
    completed_count: int
    pending_value: float


class PurchaseOrderSummaryResponse(BaseModel):
    data: PurchaseOrderSummary


class RecentSaleItem(BaseModel):
    id: int
    invoice_number: str
    medicine_name: str
    customer_name: str
    payment_method: str
    item_count: int
    units_sold: int
    total_amount: float
    sold_at: datetime
    cashier_name: str


class RecentSalesResponse(BaseModel):
    data: list[RecentSaleItem]


class SaleBillLineItem(BaseModel):
    medicine_id: int
    quantity: int = Field(ge=1)


class SaleBillRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    payment_method: str = Field(default="Cash", min_length=2, max_length=40)
    cashier_name: str = Field(default="Counter Desk", min_length=2, max_length=80)
    items: list[SaleBillLineItem] = Field(min_length=1)

    @field_validator("patient_id", "payment_method", "cashier_name")
    @classmethod
    def strip_sale_text(cls, value: str) -> str:
        return value.strip()


class SaleBillResponse(BaseModel):
    message: str
    data: RecentSaleItem


class DashboardOverview(BaseModel):
    sales_summary: SalesSummary
    items_sold: ItemsSoldSummary
    low_stock_items: list[LowStockItem]
    purchase_order_summary: PurchaseOrderSummary
    recent_sales: list[RecentSaleItem]


class DashboardOverviewResponse(BaseModel):
    data: DashboardOverview


class HealthResponse(BaseModel):
    status: str
    database: str
