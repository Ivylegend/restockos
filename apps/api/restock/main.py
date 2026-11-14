import asyncio
import time
import subprocess
import json
import os
import re
from threading import Lock
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager, suppress
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import chain, procurement
from .auth import DEMO_WORKSPACE, Principal, create_session, nonce, require_principal
from .db import engine, logger, session, settings
from .models import (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction, InventoryMovement,
                     AuthChallenge, Product, PurchaseOrder, PurchaseOrderItem, Supplier,
                     SupplierQuote, Workspace)
from .schemas import (PolicyInput, ProductInput, RunInput, StockUpdate, TransactionVerifyInput,
                      WalletVerifyInput, WorkspaceContractInput)
from .seed import CATALOG, seed as seed_workspace


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
RATE_LIMITS: dict[str, list[float]] = {}
RATE_LIMIT_LOCK = Lock()


def rate_limit(request: Request, bucket: str, limit: int, period: int = 60):
    with RATE_LIMIT_LOCK:
        now = time.monotonic()
        ip = request.client.host if request.client else "unknown"
        key = f"{bucket}:{ip}"
        hits = [stamp for stamp in RATE_LIMITS.get(key, []) if now - stamp < period]
        if len(hits) >= limit:
            RATE_LIMITS[key] = hits
            raise HTTPException(429, "Too many requests. Please wait and try again.")
        hits.append(now)
        RATE_LIMITS[key] = hits
        if len(RATE_LIMITS) > 5000:
            for stale in [key for key, stamps in RATE_LIMITS.items() if not stamps or now - stamps[-1] >= period]:
                RATE_LIMITS.pop(stale, None)


def bind_principal(db: Session, principal: Principal):
    db.info["workspace_id"] = principal.workspace_id
    return principal


def owner(db: DB, authorization: Annotated[str | None, Header()] = None):
    principal = require_principal(authorization, settings)
    if principal.role not in ("owner", "admin"):
        raise HTTPException(403, "Owner authorization is required.")
    return bind_principal(db, principal)


def viewer(db: DB, authorization: Annotated[str | None, Header()] = None):
    return bind_principal(db, require_principal(authorization, settings, public=True))


@app.get("/demo/access")
def demo_access():
    public_access = settings.demo_enabled and settings.public_demo
    return {"public_access": public_access, "public_read_only": public_access,
            "sandbox_enabled": public_access}


@app.get("/auth/challenge")
def auth_challenge(account_id: str, request: Request, db: DB):
    rate_limit(request, "auth-challenge", 8)
    if not settings.demo_enabled:
        raise HTTPException(403, "Wallet workspace creation is disabled.")
    if not account_id or len(account_id) > 64 or not re.fullmatch(r"(?:[a-z0-9]+[-_.])*[a-z0-9]+", account_id):
        raise HTTPException(422, "Enter a valid NEAR Testnet account ID.")
    now = datetime.now(timezone.utc)
    db.execute(delete(AuthChallenge).where(AuthChallenge.expires_at < now))
    value = nonce()
    message = f"Sign in to RestockOS. One-time nonce: {value}"
    db.add(AuthChallenge(nonce=value, account_id=account_id, message=message,
                         expires_at=now + timedelta(minutes=5)))
    db.commit()
    return {"nonce": value, "message": message, "recipient": settings.auth_recipient}


@app.post("/auth/verify")
def auth_verify(payload: WalletVerifyInput, request: Request, db: DB):
    rate_limit(request, "auth-verify", 8)
    challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.nonce == payload.nonce).with_for_update())
    if not challenge or challenge.account_id != payload.account_id or challenge.consumed_at:
        raise HTTPException(401, "Wallet sign-in challenge is invalid or already used.")
    expiry = challenge.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(401, "Wallet sign-in challenge expired. Connect again.")
    args = json.dumps({"rpc": settings.near_rpc_url, "account_id": payload.account_id,
                       "public_key": payload.public_key, "signature": payload.signature,
                       "message": challenge.message, "nonce": payload.nonce,
                       "recipient": settings.auth_recipient})
    verifier = Path(__file__).resolve().parents[3] / "scripts" / "verify-nep413.mjs"
    try:
        checked = subprocess.run(["node", str(verifier), args], capture_output=True, text=True,
                                 timeout=15, env=os.environ.copy())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, "Wallet signature verification is unavailable.") from exc
    if checked.returncode:
        raise HTTPException(401, "NEAR Testnet could not verify this wallet signature.")
    challenge.consumed_at = datetime.now(timezone.utc)
    admin_accounts = set(settings.admin_account_ids)
    if payload.account_id in admin_accounts:
        workspace_id, role = DEMO_WORKSPACE, "admin"
        workspace = db.get(Workspace, workspace_id)
    else:
        workspace = db.scalar(select(Workspace).where(Workspace.owner_account == payload.account_id))
        if workspace is None:
            workspace_id = "ws-" + uuid4().hex
            label = payload.account_id.split(".", 1)[0].replace("-", " ").title()
            workspace = Workspace(id=workspace_id, name=(label[:100] + " Workspace"), owner_account=payload.account_id)
            db.add(workspace)
            db.flush()
            role = "owner"
            db.info["workspace_id"] = workspace_id
            seed_workspace(db, workspace_id, payload.account_id, workspace.name)
        else:
            workspace_id, role = workspace.id, "owner"
    db.commit()
    token = create_session(settings, workspace_id, payload.account_id, role)
    return {"access_token": token, "token_type": "bearer", "role": role,
            "workspace": {"id": workspace_id, "name": workspace.name if workspace else "Admin workspace",
                          "owner_account": workspace.owner_account if workspace else payload.account_id,
                          "contract_id": workspace.contract_id if workspace else settings.near_contract_id}}


def operator(db: DB, authorization: Annotated[str | None, Header()] = None):
    principal = require_principal(authorization, settings)
    if principal.role not in ("owner", "admin", "automation"):
        raise HTTPException(403, "Agent execution is not authorized.")
    return bind_principal(db, principal)


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


@app.get("/dashboard/summary", dependencies=[Depends(viewer)])
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


@app.get("/products", dependencies=[Depends(viewer)])
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


@app.get("/suppliers", dependencies=[Depends(viewer)])
def suppliers(db: DB):
    return [row(s) for s in db.scalars(select(Supplier).order_by(Supplier.id))]


@app.get("/quotes", dependencies=[Depends(viewer)])
def quotes(db: DB):
    return [row(q) for q in db.scalars(select(SupplierQuote).order_by(SupplierQuote.id.desc()).limit(150))]


@app.get("/purchase-orders", dependencies=[Depends(viewer)])
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
    policy = db.scalar(select(AgentPolicy).where(AgentPolicy.workspace_id == db.info.get("workspace_id", DEMO_WORKSPACE)))
    if not policy:
        raise HTTPException(503, "Seed the workspace before using the agent.")
    return row(policy, omit=("id",))


@app.put("/agent/policy", dependencies=[Depends(owner)])
def put_policy(payload: PolicyInput, db: DB):
    policy = procurement.lock_policy(db, db.info.get("workspace_id"))
    accounts = set(db.scalars(select(Supplier.account)))
    if not set(payload.approved_accounts) <= accounts:
        raise HTTPException(422, "Select suppliers from the workspace directory.")
    for key, value in payload.model_dump().items():
        setattr(policy, key, value)
    procurement.audit(db, None, "policy", "Owner updated workspace permissions.")
    db.commit()
    return row(policy, omit=("id",))


@app.post("/agent/run")
def run_agent(db: DB, request: Request, payload: RunInput = RunInput(),
              principal: Principal = Depends(operator)):
    rate_limit(request, "agent-run", 10)
    if payload.scenario == "redirect":
        if principal.role != "admin":
            raise HTTPException(403, "Only the admin may run the controlled rejection scenario.")
        if not settings.demo_enabled:
            raise HTTPException(403, "The controlled rejection demo is disabled.")
    run, order = procurement.run_agent(db, payload.scenario,
                                       allow_server_signing=principal.role in ("admin", "automation"))
    return {**row(run), "order": row(order) if order else None}


@app.post("/demo/run")
def run_sandbox(db: DB, request: Request):
    if not (settings.demo_enabled and settings.public_demo):
        raise HTTPException(403, "The public sandbox is disabled.")
    rate_limit(request, "sandbox-run", 5)
    db.info["workspace_id"] = DEMO_WORKSPACE
    run, order = procurement.run_agent(db, "normal", sandbox=True, workspace_id=DEMO_WORKSPACE,
                                       allow_server_signing=False)
    return {**row(run), "order": row(order) if order else None,
            "simulation": True, "notice": "Sandbox only. No wallet was asked to sign and no NEAR transaction was sent."}


@app.get("/agent/runs", dependencies=[Depends(viewer)])
def runs(db: DB):
    records = db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(30)).all()
    events = db.scalars(select(AuditEvent).where(AuditEvent.run_id.in_([r.id for r in records])).order_by(AuditEvent.id))
    grouped = {run.id: [] for run in records}
    for event in events:
        grouped[event.run_id].append(row(event))
    return [{**row(run), "events": grouped[run.id]} for run in records]


@app.post("/purchase-orders/{order_id}/execute")
def execute(order_id: str, db: DB, request: Request, principal: Principal = Depends(owner)):
    rate_limit(request, "purchase-execute", 10)
    if principal.role != "admin":
        raise HTTPException(403, "Workspace owners must confirm purchases in their connected NEAR wallet.")
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


@app.get("/transactions", dependencies=[Depends(viewer)])
def transactions(db: DB):
    records = db.scalars(select(BlockchainTransaction).order_by(BlockchainTransaction.created_at.desc()).limit(100))
    return [row(tx, omit=("signed_payload",)) for tx in records]


@app.get("/treasury", dependencies=[Depends(viewer)])
def treasury(db: DB):
    workspace = db.get(Workspace, db.info.get("workspace_id", DEMO_WORKSPACE))
    contract_id = workspace.contract_id if workspace else None
    if db.info.get("workspace_id") == DEMO_WORKSPACE:
        contract_id = contract_id or settings.near_contract_id
    if not contract_id:
        return {"contract": None, "policy": None, "error": "Set a NEAR Testnet contract to connect treasury."}
    try:
        policy = chain.view("get_policy", {}, contract_id)
        return {"contract": contract_id, "policy": policy, "error": None}
    except chain.ChainError as exc:
        return {"contract": contract_id, "policy": None, "error": str(exc)}


@app.get("/workspace", dependencies=[Depends(owner)])
def workspace(db: DB, principal: Principal = Depends(owner)):
    record = db.get(Workspace, db.info.get("workspace_id", DEMO_WORKSPACE))
    contract = record.contract_id if record else None
    if db.info.get("workspace_id") == DEMO_WORKSPACE:
        contract = contract or settings.near_contract_id
    owner_account = record.owner_account if record else None
    return {"id": record.id if record else DEMO_WORKSPACE,
            "name": record.name if record else "Admin workspace",
            "owner_account": owner_account,
            "contract_id": contract,
            "expected_contract_id": ("policy." + owner_account) if owner_account else None,
            "role": principal.role,
            "demo_enabled": settings.demo_enabled, "chain_configured": bool(contract)}


@app.put("/workspace/contract")
def set_workspace_contract(payload: WorkspaceContractInput, db: DB,
                           principal: Principal = Depends(owner)):
    workspace = db.get(Workspace, principal.workspace_id)
    if not workspace or not principal.account_id or workspace.owner_account != principal.account_id:
        raise HTTPException(403, "The connected wallet must own this workspace.")
    expected = "policy." + workspace.owner_account
    if payload.contract_id != expected:
        raise HTTPException(422, f"This workspace contract must be deployed at {expected}.")
    try:
        policy = chain.view("get_policy", {}, payload.contract_id)
    except chain.ChainError as exc:
        raise HTTPException(422, "The Testnet contract is not deployed or could not be verified.") from exc
    if policy.get("owner") != workspace.owner_account:
        raise HTTPException(422, "The contract owner does not match the workspace wallet.")
    workspace.contract_id = payload.contract_id
    db.commit()
    return {"contract_id": workspace.contract_id, "owner": policy["owner"]}


@app.post("/purchase-orders/{order_id}/authorize")
def authorize_wallet_purchase(order_id: str, db: DB, principal: Principal = Depends(owner)):
    workspace = db.get(Workspace, principal.workspace_id)
    order = db.get(PurchaseOrder, order_id, with_for_update=True)
    if not workspace or not principal.account_id or workspace.owner_account != principal.account_id:
        raise HTTPException(403, "The connected workspace owner must confirm this payment.")
    if not workspace.contract_id:
        raise HTTPException(409, "Deploy and verify this workspace's Testnet policy contract first.")
    if not order or order.status != "ready":
        raise HTTPException(409, "Only a ready purchase order can be authorized.")
    policy = procurement.lock_policy(db, principal.workspace_id)
    quote = db.scalar(select(SupplierQuote).where(SupplierQuote.run_id == order.run_id,
                                                  SupplierQuote.account == order.account))
    if not quote:
        raise HTTPException(409, "The selected supplier quote could not be verified.")
    reason = procurement.check_policy(policy, quote, order.amount, "normal")
    if reason:
        raise HTTPException(409, reason)
    return {"network": "testnet", "contract_id": workspace.contract_id,
            "order_id": order.id, "supplier": order.account, "amount": order.amount,
            "method_name": "execute_purchase", "args": {"order_id": order.id,
                "supplier": order.account, "amount": order.amount}}


@app.post("/transactions/verify")
def verify_wallet_transaction(payload: TransactionVerifyInput, db: DB, request: Request,
                              principal: Principal = Depends(owner)):
    rate_limit(request, "transaction-verify", 12)
    workspace = db.get(Workspace, principal.workspace_id)
    order = db.get(PurchaseOrder, payload.order_id, with_for_update=True)
    if not workspace or not principal.account_id or workspace.owner_account != principal.account_id:
        raise HTTPException(403, "The connected wallet does not own this workspace.")
    if not workspace.contract_id or not order or order.status not in ("ready", "submitting"):
        raise HTTPException(404, "The pending Testnet purchase was not found.")
    existing = db.scalar(select(BlockchainTransaction).where(BlockchainTransaction.order_id == order.id))
    if existing and existing.hash != payload.hash:
        raise HTTPException(409, "This order already has a different transaction hash.")
    if existing:
        tx = existing
    else:
        tx = BlockchainTransaction(workspace_id=workspace.id, order_id=order.id, hash=payload.hash,
                                   signer=principal.account_id, contract=workspace.contract_id,
                                   signed_payload=None, status="pending")
        db.add(tx)
        order.status = "submitting"
        db.get(AgentRun, order.run_id).status = "submitting"
    try:
        outcome = chain.verify(tx.hash, principal.account_id, workspace.contract_id,
                               order.id, order.account, order.amount)
    except chain.ChainError as exc:
        db.commit()
        raise HTTPException(422, str(exc)) from exc
    if outcome:
        tx.status, tx.receipt_id, tx.reason = outcome
        order.status, order.reason = outcome[0], outcome[2]
        db.get(AgentRun, order.run_id).status = outcome[0]
        procurement.audit(db, order.run_id, "settlement", outcome[2])
    db.commit()
    return row(tx, omit=("signed_payload",))


@app.post("/demo/reset", status_code=204)
def reset(db: DB, request: Request, principal: Principal = Depends(owner)):
    rate_limit(request, "demo-reset", 2)
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
