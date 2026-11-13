import asyncio
import time
import secrets
from contextlib import asynccontextmanager, suppress
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import chain, procurement
from .db import engine, logger, session, settings
from .models import (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction, InventoryMovement,
                     Product, PurchaseOrder, PurchaseOrderItem, Supplier, SupplierQuote)
from .schemas import PolicyInput, ProductInput, RunInput, StockUpdate
from .seed import CATALOG


def maintain_payments(scan: bool):
    with Session(engine()) as db:
        procurement.reconcile(db)
        if scan:
            procurement.run_agent(db, "normal", scheduled=True)


async def reconcile_loop():
    interval = max(0, settings.scan_interval_seconds)
    next_scan = time.monotonic() + interval
    while True:
        await asyncio.sleep(4)
        scan = interval > 0 and time.monotonic() >= next_scan
        if scan:
            next_scan = time.monotonic() + interval
        try:
            await asyncio.to_thread(maintain_payments, scan)
        except SQLAlchemyError:
            logger.warning('{"event":"reconciliation_database_unavailable"}')
        except procurement.WorkflowError:
            logger.info('{"event":"scheduled_scan_deferred"}')


@asynccontextmanager
async def lifespan(_app):
    worker = asyncio.create_task(reconcile_loop())
    yield
    worker.cancel()
    with suppress(asyncio.CancelledError):
        await worker


app = FastAPI(title="RestockOS API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_methods=["GET", "POST", "PUT", "PATCH"],
                   allow_headers=["Authorization", "Content-Type"])
DB = Annotated[Session, Depends(session)]


def authorized(authorization: str | None, *tokens: str):
    supplied = (authorization or "").removeprefix("Bearer ").encode()
    if not authorization or not authorization.startswith("Bearer ") or not any(
        token and secrets.compare_digest(supplied, token.encode()) for token in tokens
    ):
        raise HTTPException(401, "A valid workspace access token is required.")


def owner(authorization: Annotated[str | None, Header()] = None):
    authorized(authorization, settings.owner_token)


def operator(authorization: Annotated[str | None, Header()] = None):
    authorized(authorization, settings.owner_token, settings.automation_token)


def row(obj, *, omit=()):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns if column.name not in omit}


@app.exception_handler(procurement.WorkflowError)
async def workflow_error(_request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health")
def health(db: DB):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database is unavailable.") from exc
    return {"status": "ok", "network": "testnet"}


@app.get("/dashboard/summary", dependencies=[Depends(owner)])
def dashboard(db: DB):
    products = db.scalars(select(Product).order_by(Product.id)).all()
    orders = db.scalars(select(PurchaseOrder)).all()
    shortages = sorted((p for p in products if p.stock < p.reorder_point),
                       key=lambda p: (p.stock / max(p.daily_sales, .01), p.id))
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(12))
    return {
        "products": len(products), "shortages": len(shortages),
        "open_orders": sum(o.status in ("ready", "submitting", "paid") for o in orders),
        "settled_yocto": str(sum(int(o.amount) for o in orders if o.status in ("paid", "received"))),
        "low_stock": [row(p) for p in shortages[:6]], "activity": [row(event) for event in events],
        "categories": [{"name": name, "count": sum(p.category == name for p in products)}
                       for name in sorted({p.category for p in products})],
    }


@app.get("/products", dependencies=[Depends(owner)])
def products(db: DB):
    return [row(p) for p in db.scalars(select(Product).order_by(Product.id))]


@app.post("/products", status_code=201, dependencies=[Depends(owner)])
def add_product(payload: ProductInput, db: DB):
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.flush()
        db.add(InventoryMovement(product_id=product.id, delta=product.stock, reason="Opening stock"))
        procurement.audit(db, None, "inventory", f"Added {product.sku} to inventory.")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A product with this SKU already exists.") from exc
    return row(product)


@app.patch("/products/{product_id}", dependencies=[Depends(owner)])
def update_product(product_id: int, payload: StockUpdate, db: DB):
    product = db.get(Product, product_id, with_for_update=True)
    if not product:
        raise HTTPException(404, "Product not found.")
    values = payload.model_dump(exclude_none=True)
    if "stock" in values and product.stock != values["stock"]:
        db.add(InventoryMovement(product_id=product.id, delta=values["stock"] - product.stock, reason="Stock adjustment"))
    for key, value in values.items():
        setattr(product, key, value)
    procurement.audit(db, None, "inventory", f"Updated {product.sku}.")
    db.commit()
    return row(product)


@app.get("/suppliers", dependencies=[Depends(owner)])
def suppliers(db: DB):
    return [row(s) for s in db.scalars(select(Supplier).order_by(Supplier.id))]


@app.get("/quotes", dependencies=[Depends(owner)])
def quotes(db: DB):
    return [row(q) for q in db.scalars(select(SupplierQuote).order_by(SupplierQuote.id.desc()).limit(150))]


@app.get("/purchase-orders", dependencies=[Depends(owner)])
def orders(db: DB):
    query = (select(PurchaseOrder, PurchaseOrderItem, Product.name, Supplier.name, BlockchainTransaction.hash)
             .select_from(PurchaseOrder)
             .join(PurchaseOrderItem, PurchaseOrderItem.order_id == PurchaseOrder.id)
             .join(Product, Product.id == PurchaseOrderItem.product_id)
             .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
             .outerjoin(BlockchainTransaction, BlockchainTransaction.order_id == PurchaseOrder.id)
             .order_by(PurchaseOrder.created_at.desc()))
    return [{**row(order), "quantity": item.quantity, "product": name, "supplier": supplier, "hash": tx_hash}
            for order, item, name, supplier, tx_hash in db.execute(query)]


@app.get("/agent/policy", dependencies=[Depends(owner)])
def get_policy(db: DB):
    policy = db.get(AgentPolicy, 1)
    if not policy:
        raise HTTPException(503, "Seed the workspace before using the agent.")
    return row(policy, omit=("id",))


@app.put("/agent/policy", dependencies=[Depends(owner)])
def put_policy(payload: PolicyInput, db: DB):
    policy = procurement.lock_policy(db)
    accounts = set(db.scalars(select(Supplier.account)))
    if not set(payload.approved_accounts) <= accounts:
        raise HTTPException(422, "Select suppliers from the workspace directory.")
    for key, value in payload.model_dump().items():
        setattr(policy, key, value)
    procurement.audit(db, None, "policy", "Owner updated workspace permissions.")
    db.commit()
    return row(policy, omit=("id",))


@app.post("/agent/run", dependencies=[Depends(operator)])
def run_agent(db: DB, payload: RunInput = RunInput(), authorization: Annotated[str | None, Header()] = None):
    if payload.scenario == "redirect":
        owner(authorization)
        if not settings.demo_enabled:
            raise HTTPException(403, "The controlled rejection demo is disabled.")
    run, order = procurement.run_agent(db, payload.scenario)
    return {**row(run), "order": row(order) if order else None}


@app.get("/agent/runs", dependencies=[Depends(owner)])
def runs(db: DB):
    records = db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(30)).all()
    events = db.scalars(select(AuditEvent).where(AuditEvent.run_id.in_([r.id for r in records])).order_by(AuditEvent.id))
    grouped = {run.id: [] for run in records}
    for event in events:
        grouped[event.run_id].append(row(event))
    return [{**row(run), "events": grouped[run.id]} for run in records]


@app.post("/purchase-orders/{order_id}/execute", dependencies=[Depends(owner)])
def execute(order_id: str, db: DB):
    return row(procurement.request_onchain_purchase(db, order_id))


@app.post("/purchase-orders/{order_id}/receive", dependencies=[Depends(owner)])
def receive(order_id: str, db: DB):
    order = db.get(PurchaseOrder, order_id, with_for_update=True)
    if not order or order.status != "paid":
        raise HTTPException(409, "Only a paid purchase order can be received.")
    for item in db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order.id)):
        product = db.get(Product, item.product_id, with_for_update=True)
        product.stock += item.quantity
        db.add(InventoryMovement(product_id=product.id, delta=item.quantity, reason=f"Received {order.id}"))
    order.status = "received"
    procurement.audit(db, order.run_id, "inventory", "Owner confirmed delivery and inventory was updated.")
    db.commit()
    return row(order)


@app.get("/transactions", dependencies=[Depends(owner)])
def transactions(db: DB):
    records = db.scalars(select(BlockchainTransaction).order_by(BlockchainTransaction.created_at.desc()).limit(100))
    return [row(tx, omit=("signed_payload",)) for tx in records]


@app.get("/treasury", dependencies=[Depends(owner)])
def treasury():
    if not settings.near_contract_id:
        return {"contract": None, "policy": None, "error": "Set a NEAR Testnet contract to connect treasury."}
    try:
        policy = chain.view("get_policy", {})
        return {"contract": settings.near_contract_id, "policy": policy, "error": None}
    except chain.ChainError as exc:
        return {"contract": settings.near_contract_id, "policy": None, "error": str(exc)}


@app.get("/workspace", dependencies=[Depends(owner)])
def workspace():
    return {"demo_enabled": settings.demo_enabled, "chain_configured": bool(settings.near_contract_id)}


@app.post("/demo/reset", status_code=204, dependencies=[Depends(owner)])
def reset(db: DB):
    if not settings.demo_enabled:
        raise HTTPException(403, "Demo reset is disabled.")
    procurement.lock_policy(db)
    if db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status.in_(("submitting", "paid")))):
        raise HTTPException(409, "Finalize pending payments and receive paid orders before resetting stock.")
    demo = {entry[0]: entry[3] for entry in CATALOG}
    for product in db.scalars(select(Product).where(Product.sku.in_(demo)).with_for_update()):
        delta = demo[product.sku] - product.stock
        if delta:
            product.stock += delta
            db.add(InventoryMovement(product_id=product.id, delta=delta, reason="Demo inventory reset"))
    for order in db.scalars(select(PurchaseOrder).where(PurchaseOrder.status == "ready").with_for_update()):
        order.status = "cancelled"
        order.reason = "Cancelled by demo reset."
        db.get(AgentRun, order.run_id).status = "cancelled"
    procurement.audit(db, None, "demo", "Reset demo inventory and cancelled unsigned orders.")
    db.commit()
    return Response(status_code=204)
