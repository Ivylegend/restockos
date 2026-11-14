from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import engine, settings
from .models import AgentPolicy, Product, Supplier, Workspace

NEAR = 10**24
CATALOG = [
    ("EL-101", "USB-C 65W Charger", "Charging", 3, 20, 6.2, 4),
    ("EL-102", "HDMI 2.1 Cable", "Cables", 8, 15, 3.6, 2),
    ("EL-103", "Portable SSD 1 TB", "Storage", 11, 16, 2.8, 8),
    ("EL-104", "Wireless Mouse", "Peripherals", 31, 18, 3.1, 4),
    ("EL-105", "Mechanical Keyboard", "Peripherals", 24, 12, 1.8, 7),
    ("EL-106", "USB-C Hub 7-in-1", "Adapters", 48, 20, 3.8, 6),
    ("EL-107", "Braided USB-C Cable", "Cables", 70, 25, 5.7, 2),
    ("EL-108", "MagSafe Charging Pad", "Charging", 39, 16, 2.9, 4),
    ("EL-109", "Webcam 1080p", "Video", 18, 10, 1.9, 5),
    ("EL-110", "Bluetooth Headset", "Audio", 26, 12, 2.4, 6),
    ("EL-111", "SD Card 128 GB", "Storage", 56, 24, 4.1, 3),
    ("EL-112", "USB-A Wall Charger", "Charging", 33, 18, 3.2, 2),
    ("EL-113", "DisplayPort Adapter", "Adapters", 25, 10, 1.3, 3),
    ("EL-114", "Desktop Microphone", "Audio", 22, 12, 1.7, 6),
    ("EL-115", "Laptop Stand", "Peripherals", 34, 15, 2.0, 5),
    ("EL-116", "Ethernet Cat6 Cable", "Cables", 90, 25, 4.4, 2),
]


def seed(db: Session, workspace_id: str = "admin-demo", owner_account: str = "admin-demo.testnet",
         name: str = "Northline Electronics"):
    if db.get(Workspace, workspace_id) is None:
        db.add(Workspace(id=workspace_id, name=name, owner_account=owner_account))
        db.flush()
    if db.scalar(select(AgentPolicy.id).where(AgentPolicy.workspace_id == workspace_id)):
        return
    accounts = settings.demo_supplier_accounts.split(",") if settings.demo_supplier_accounts else [
        "restock-northstar.testnet", "restock-circuit.testnet", "restock-volt.testnet",
    ]
    if len(accounts) != 3 or len(set(accounts)) != 3:
        raise ValueError("DEMO_SUPPLIER_ACCOUNTS must contain three distinct accounts")
    for (name, lead, reliability, price), account in zip(
        [("Northstar Supply", 2, 98, 10000), ("Circuit Wholesale", 5, 94, 8800),
         ("Volt Distribution", 1, 91, 11700)], accounts,
    ):
        db.add(Supplier(workspace_id=workspace_id, name=name, account=account, lead_days=lead,
                        reliability=reliability, price_bps=price))
    for sku, name, category, stock, threshold, sales, price in CATALOG:
        db.add(Product(workspace_id=workspace_id, sku=sku, name=name, category=category, stock=stock, reorder_point=threshold,
                       daily_sales=sales, unit_price=str(price * NEAR // 1000)))
    policy_id = int(db.connection().execute(select(func.max(AgentPolicy.id))).scalar() or 0) + 1
    db.add(AgentPolicy(id=policy_id, workspace_id=workspace_id, paused=False, auto_execute=False, approved_accounts=accounts,
                       max_order=str(NEAR // 2), budget=str(2 * NEAR)))


if __name__ == "__main__":
    with Session(engine()) as db, db.begin():
        seed(db)
