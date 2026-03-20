from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import Medicine, PurchaseOrder, PurchaseOrderStatus, Sale, SaleItem


def summarize_medicine_names(names: list[str]) -> str:
    if not names:
        return "No medicines"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return ", ".join(names)
    return f"{names[0]}, {names[1]} +{len(names) - 2} more"


def seed_sale(
    session: Session,
    *,
    invoice_number: str,
    customer_name: str,
    payment_method: str,
    cashier_name: str,
    sold_at: datetime,
    line_items: list[dict],
) -> Sale:
    medicine_names = [item["medicine"].name for item in line_items]
    units_sold = sum(item["quantity"] for item in line_items)
    total_amount = round(
        sum(item["quantity"] * item["medicine"].unit_price for item in line_items),
        2,
    )

    sale = Sale(
        invoice_number=invoice_number,
        medicine_id=line_items[0]["medicine"].id if len(line_items) == 1 else None,
        medicine_name=summarize_medicine_names(medicine_names),
        customer_name=customer_name,
        payment_method=payment_method,
        item_count=len(line_items),
        units_sold=units_sold,
        total_amount=total_amount,
        sold_at=sold_at,
        cashier_name=cashier_name,
    )
    session.add(sale)
    session.flush()

    for item in line_items:
        medicine = item["medicine"]
        quantity = item["quantity"]
        session.add(
            SaleItem(
                sale_id=sale.id,
                medicine_id=medicine.id,
                medicine_name=medicine.name,
                quantity=quantity,
                unit_price=medicine.unit_price,
                line_total=round(quantity * medicine.unit_price, 2),
            )
        )

    return sale


def seed_database(session: Session) -> None:
    if session.query(Medicine).count() > 0:
        return

    today = date.today()
    now = datetime.now()

    medicines = [
        Medicine(
            name="Paracetamol",
            generic_name="Acetaminophen",
            manufacturer="Cipla",
            supplier_name="Medline Traders",
            category="Pain Relief",
            dosage_form="Tablet",
            strength="500 mg",
            batch_number="PARA-2401",
            quantity=120,
            unit_price=2.5,
            reorder_level=20,
            expiry_date=today + timedelta(days=220),
            location="Rack A1",
        ),
        Medicine(
            name="Azithromycin",
            generic_name="Azithromycin",
            manufacturer="Sun Pharma",
            supplier_name="Apollo Wholesale",
            category="Antibiotic",
            dosage_form="Tablet",
            strength="250 mg",
            batch_number="AZI-2402",
            quantity=14,
            unit_price=9.75,
            reorder_level=15,
            expiry_date=today + timedelta(days=160),
            location="Rack B1",
        ),
        Medicine(
            name="Cetirizine",
            generic_name="Cetirizine Hydrochloride",
            manufacturer="Dr. Reddy's",
            supplier_name="CarePoint Supply",
            category="Allergy",
            dosage_form="Tablet",
            strength="10 mg",
            batch_number="CET-2403",
            quantity=0,
            unit_price=3.2,
            reorder_level=12,
            expiry_date=today + timedelta(days=190),
            location="Rack A3",
        ),
        Medicine(
            name="Omeprazole",
            generic_name="Omeprazole",
            manufacturer="Mankind",
            supplier_name="Prime Pharma Link",
            category="Gastro",
            dosage_form="Capsule",
            strength="20 mg",
            batch_number="OME-2404",
            quantity=36,
            unit_price=6.5,
            reorder_level=10,
            expiry_date=today - timedelta(days=12),
            location="Rack C2",
            manual_expired=True,
        ),
        Medicine(
            name="Amoxicillin",
            generic_name="Amoxicillin",
            manufacturer="Lupin",
            supplier_name="Wellness Wholesale",
            category="Antibiotic",
            dosage_form="Capsule",
            strength="500 mg",
            batch_number="AMOX-2405",
            quantity=42,
            unit_price=8.4,
            reorder_level=18,
            expiry_date=today + timedelta(days=145),
            location="Rack B2",
        ),
        Medicine(
            name="Vitamin D3",
            generic_name="Cholecalciferol",
            manufacturer="Abbott",
            supplier_name="Abbott Trade",
            category="Supplements",
            dosage_form="Softgel",
            strength="60000 IU",
            batch_number="VD3-2406",
            quantity=8,
            unit_price=14.0,
            reorder_level=10,
            expiry_date=today + timedelta(days=260),
            location="Rack D1",
        ),
        Medicine(
            name="Metformin",
            generic_name="Metformin Hydrochloride",
            manufacturer="Torrent",
            supplier_name="HealthKart Distributors",
            category="Diabetes",
            dosage_form="Tablet",
            strength="500 mg",
            batch_number="MET-2407",
            quantity=74,
            unit_price=4.3,
            reorder_level=20,
            expiry_date=today + timedelta(days=310),
            location="Rack C1",
        ),
    ]

    session.add_all(medicines)
    session.flush()

    seed_sale(
        session,
        invoice_number="INV-2026-201",
        customer_name="Rajesh Kumar",
        payment_method="Card",
        cashier_name="Neha",
        sold_at=now.replace(hour=9, minute=15, second=0, microsecond=0),
        line_items=[
            {"medicine": medicines[0], "quantity": 6},
            {"medicine": medicines[4], "quantity": 1},
            {"medicine": medicines[6], "quantity": 3},
        ],
    )
    seed_sale(
        session,
        invoice_number="INV-2026-202",
        customer_name="Sarah Smith",
        payment_method="Cash",
        cashier_name="Karan",
        sold_at=now.replace(hour=11, minute=5, second=0, microsecond=0),
        line_items=[
            {"medicine": medicines[1], "quantity": 2},
            {"medicine": medicines[5], "quantity": 2},
        ],
    )
    seed_sale(
        session,
        invoice_number="INV-2026-203",
        customer_name="Michael Johnson",
        payment_method="UPI",
        cashier_name="Anika",
        sold_at=now.replace(hour=13, minute=40, second=0, microsecond=0),
        line_items=[
            {"medicine": medicines[6], "quantity": 5},
            {"medicine": medicines[0], "quantity": 8},
            {"medicine": medicines[4], "quantity": 2},
        ],
    )
    seed_sale(
        session,
        invoice_number="INV-2026-198",
        customer_name="Ananya Rao",
        payment_method="UPI",
        cashier_name="Neha",
        sold_at=now - timedelta(days=1, hours=2),
        line_items=[
            {"medicine": medicines[1], "quantity": 4},
            {"medicine": medicines[0], "quantity": 3},
        ],
    )
    seed_sale(
        session,
        invoice_number="INV-2026-197",
        customer_name="Vikram Shah",
        payment_method="Card",
        cashier_name="Karan",
        sold_at=now - timedelta(days=1, hours=4),
        line_items=[
            {"medicine": medicines[5], "quantity": 1},
            {"medicine": medicines[6], "quantity": 2},
        ],
    )

    purchase_orders = [
        PurchaseOrder(
            medicine_id=medicines[1].id,
            medicine_name=medicines[1].name,
            supplier_name="Apollo Wholesale",
            quantity=100,
            total_amount=975.0,
            status=PurchaseOrderStatus.PENDING.value,
            ordered_at=now - timedelta(days=1),
            expected_delivery=today + timedelta(days=3),
        ),
        PurchaseOrder(
            medicine_id=medicines[2].id,
            medicine_name=medicines[2].name,
            supplier_name="MedPlus Supply",
            quantity=80,
            total_amount=256.0,
            status=PurchaseOrderStatus.IN_TRANSIT.value,
            ordered_at=now - timedelta(days=2),
            expected_delivery=today + timedelta(days=1),
        ),
        PurchaseOrder(
            medicine_id=medicines[5].id,
            medicine_name=medicines[5].name,
            supplier_name="Abbott Trade",
            quantity=50,
            total_amount=700.0,
            status=PurchaseOrderStatus.COMPLETED.value,
            ordered_at=now - timedelta(days=5),
            expected_delivery=today - timedelta(days=1),
        ),
    ]

    session.add_all(purchase_orders)
    session.commit()
