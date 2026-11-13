from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(24), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    stock: Mapped[int]
    reorder_point: Mapped[int]
    daily_sales: Mapped[float]
    unit_price: Mapped[str] = mapped_column(String(39))


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    account: Mapped[str] = mapped_column(String(64), unique=True)
    lead_days: Mapped[int]
    reliability: Mapped[int]
    price_bps: Mapped[int]


class AgentPolicy(Base):
    __tablename__ = "agent_policy"
    id: Mapped[int] = mapped_column(primary_key=True)
    paused: Mapped[bool]
    auto_execute: Mapped[bool]
    approved_accounts: Mapped[list[str]] = mapped_column(JSON)
    max_order: Mapped[str] = mapped_column(String(39))
    budget: Mapped[str] = mapped_column(String(39))


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario: Mapped[str]
    status: Mapped[str]
    mode: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    account: Mapped[str]
    amount: Mapped[str] = mapped_column(String(39))
    quantity: Mapped[int]
    lead_days: Mapped[int]
    reliability: Mapped[int]
    status: Mapped[str]
    negotiated_amount: Mapped[str | None] = mapped_column(String(39), default=None)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    account: Mapped[str]
    amount: Mapped[str] = mapped_column(String(39))
    status: Mapped[str]
    reason: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    delta: Mapped[int]
    reason: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), unique=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True)
    signer: Mapped[str]
    contract: Mapped[str]
    signed_payload: Mapped[str | None]
    status: Mapped[str]
    receipt_id: Mapped[str | None] = mapped_column(default=None)
    reason: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    kind: Mapped[str]
    message: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
