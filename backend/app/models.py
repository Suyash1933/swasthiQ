from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PurchaseOrderStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    generic_name: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str] = mapped_column(String(120))
    supplier_name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80), index=True)
    dosage_form: Mapped[str] = mapped_column(String(50))
    strength: Mapped[str] = mapped_column(String(50))
    batch_number: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float] = mapped_column(Float)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)
    expiry_date: Mapped[date] = mapped_column(Date)
    location: Mapped[str] = mapped_column(String(80))
    manual_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    sales: Mapped[list["Sale"]] = relationship(back_populates="medicine")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="medicine")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), index=True)
    medicine_id: Mapped[int | None] = mapped_column(ForeignKey("medicines.id"), nullable=True)
    medicine_name: Mapped[str] = mapped_column(String(120))
    customer_name: Mapped[str] = mapped_column(String(120))
    payment_method: Mapped[str] = mapped_column(String(40))
    item_count: Mapped[int] = mapped_column(Integer)
    units_sold: Mapped[int] = mapped_column(Integer)
    total_amount: Mapped[float] = mapped_column(Float)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cashier_name: Mapped[str] = mapped_column(String(80))

    medicine: Mapped["Medicine | None"] = relationship(back_populates="sales")
    sale_items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), index=True)
    medicine_id: Mapped[int | None] = mapped_column(ForeignKey("medicines.id"), nullable=True)
    medicine_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    line_total: Mapped[float] = mapped_column(Float)

    sale: Mapped["Sale"] = relationship(back_populates="sale_items")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    medicine_id: Mapped[int | None] = mapped_column(ForeignKey("medicines.id"), nullable=True)
    medicine_name: Mapped[str] = mapped_column(String(120))
    supplier_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer)
    total_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default=PurchaseOrderStatus.PENDING.value)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expected_delivery: Mapped[date] = mapped_column(Date)

    medicine: Mapped["Medicine | None"] = relationship(back_populates="purchase_orders")
