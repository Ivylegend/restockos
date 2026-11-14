from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("workspace_id", "sku", name="uq_products_workspace_sku"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    sku: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    stock: Mapped[int]
    reorder_point: Mapped[int]
    daily_sales: Mapped[float]
    unit_price: Mapped[str] = mapped_column(String(39))


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_suppliers_workspace_name"),
        UniqueConstraint("workspace_id", "account", name="uq_suppliers_workspace_account"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    account: Mapped[str] = mapped_column(String(64))
    lead_days: Mapped[int]
    reliability: Mapped[int]
    price_bps: Mapped[int]


class AgentPolicy(Base):
    __tablename__ = "agent_policy"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_agent_policy_workspace"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), unique=True)
    paused: Mapped[bool]
    auto_execute: Mapped[bool]
    approved_accounts: Mapped[list[str]] = mapped_column(JSON)
    max_order: Mapped[str] = mapped_column(String(39))
    budget: Mapped[str] = mapped_column(String(39))


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    scenario: Mapped[str]
    status: Mapped[str]
    mode: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
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
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
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
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    delta: Mapped[int]
    reason: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
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
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    kind: Mapped[str]
    message: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_account: Mapped[str] = mapped_column(String(64), unique=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
