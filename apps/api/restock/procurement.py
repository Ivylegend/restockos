import json
from decimal import Decimal
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import chain
from .db import logger, settings
from .models import (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction, Product, PurchaseOrder,
                     PurchaseOrderItem, Supplier, SupplierQuote)


class WorkflowError(Exception):
    pass


def audit(db: Session, run_id: str | None, kind: str, message: str):
    logger.info(json.dumps({"event": kind, "run_id": run_id, "message": message}))
    db.add(AuditEvent(run_id=run_id, kind=kind, message=message))


def lock_policy(db: Session) -> AgentPolicy:
    policy = db.get(AgentPolicy, 1, with_for_update=True, populate_existing=True)
    if policy is None:
        raise WorkflowError("Seed the workspace before running procurement.")
    return policy


def analyze_inventory(db: Session, scenario: str) -> Product | None:
    ordered = select(PurchaseOrderItem.product_id).join(PurchaseOrder).where(
        PurchaseOrder.status.in_(("ready", "submitting", "paid"))
    )
    shortages = select(Product).where(Product.stock < Product.reorder_point)
    if scenario == "normal":
        shortages = shortages.where(Product.id.not_in(ordered))
    return min(db.scalars(shortages), key=lambda p: (p.stock / max(p.daily_sales, .01), p.id), default=None)


def request_supplier_quotes(db: Session, run: AgentRun, product: Product) -> list[SupplierQuote]:
    quantity = max(1, product.reorder_point * 2 - product.stock)
    quotes = []
    for supplier in db.scalars(select(Supplier).order_by(Supplier.id).limit(3)):
        redirect = settings.near_contract_id or "unapproved-restock-recipient.testnet"
        account = redirect if run.scenario == "redirect" and not quotes else supplier.account
        quotes.append(SupplierQuote(
            run_id=run.id, supplier_id=supplier.id, product_id=product.id, account=account,
            amount=str((int(product.unit_price) * quantity * supplier.price_bps + 9999) // 10000),
            quantity=quantity, lead_days=supplier.lead_days, reliability=supplier.reliability,
            status="received" if account == supplier.account else "flagged",
        ))
    db.add_all(quotes)
    db.flush()
    return quotes


def score(quote: SupplierQuote, cheapest: int) -> int:
    return (int(quote.amount) * 60_000 // cheapest +
            quote.lead_days * 4_000 + (100 - quote.reliability) * 1_000)


def evaluate_quotes(quotes: list[SupplierQuote], policy: AgentPolicy) -> list[SupplierQuote]:
    allowed = [q for q in quotes if q.status == "received" and q.account in policy.approved_accounts]
    if not allowed:
        return []
    cheapest = min(int(q.amount) for q in allowed)
    return sorted(allowed, key=lambda q: (score(q, cheapest), q.id))


def recommend_quote(quotes: list[SupplierQuote]) -> tuple[SupplierQuote, str]:
    if not settings.llm_api_key:
        return quotes[0], "deterministic"
    choices = [{"quote_id": q.id, "amount_yocto": q.amount, "lead_days": q.lead_days,
                "reliability": q.reliability} for q in quotes]
    tool = {"type": "function", "function": {
        "name": "evaluate_quotes", "description": "Recommend one of the approved quotes.",
        "parameters": {"type": "object", "properties": {"quote_id": {"type": "integer"}},
                       "required": ["quote_id"], "additionalProperties": False},
    }}
    try:
        result = httpx.post(
            settings.llm_base_url.rstrip("/") + "/chat/completions", timeout=8,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "tools": [tool],
                  "tool_choice": {"type": "function", "function": {"name": "evaluate_quotes"}},
                  "messages": [{"role": "system", "content": "Balance price, shipping speed and reliability. Use the quote tool."},
                               {"role": "user", "content": json.dumps(choices)}]},
        )
        result.raise_for_status()
        call = result.json()["choices"][0]["message"]["tool_calls"][0]["function"]
        quote_id = json.loads(call["arguments"])["quote_id"]
        if call["name"] == "evaluate_quotes" and type(quote_id) is int:
            selected = next((q for q in quotes if q.id == quote_id), None)
            if selected:
                return selected, "llm"
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        pass
    return quotes[0], "deterministic fallback"


def negotiate_quote(quote: SupplierQuote) -> str:
    # The demo supplier adapter accepts a 4% counteroffer at ten units or more.
    price = int(quote.amount)
    return str((price * 96 + 99) // 100 if quote.quantity >= 10 else price)


def check_policy(policy: AgentPolicy, quote: SupplierQuote, amount: str, scenario: str) -> str | None:
    if policy.paused:
        return "Workspace agent is paused."
    if scenario == "normal" and quote.account not in policy.approved_accounts:
        return "Supplier is outside the workspace allowlist."
    if int(amount) > min(int(policy.max_order), int(policy.budget)):
        return "Offer exceeds the workspace spending limits."
    return None


def create_purchase_order(db: Session, run: AgentRun, quote: SupplierQuote, amount: str, reason: str | None):
    order = PurchaseOrder(id=str(uuid4()), run_id=run.id, supplier_id=quote.supplier_id,
                          account=quote.account, amount=amount, status="rejected" if reason else "ready", reason=reason)
    db.add(order)
    db.flush()
    db.add(PurchaseOrderItem(order_id=order.id, product_id=quote.product_id, quantity=quote.quantity))
    return order


def run_agent(db: Session, scenario: str, *, scheduled: bool = False):
    policy = lock_policy(db)
    if scheduled and (
        policy.paused or not policy.auto_execute or
        db.scalar(select(BlockchainTransaction.id).where(BlockchainTransaction.status == "pending").limit(1))
    ):
        return None, None
    product = analyze_inventory(db, scenario)
    if scheduled and product is None:
        return None, None
    run = AgentRun(id=str(uuid4()), scenario=scenario, mode="deterministic", status="scanning")
    db.add(run)
    db.flush()
    if not product or policy.paused:
        run.status = "paused" if policy.paused else "clear"
        audit(db, run.id, "inventory", "Agent is paused." if policy.paused else "No shortage without an open order.")
        db.commit()
        return run, None
    audit(db, run.id, "inventory", f"{product.name} has {product.stock} units against a reorder point of {product.reorder_point}.")
    quotes = request_supplier_quotes(db, run, product)
    audit(db, run.id, "quotes", f"Received {len(quotes)} supplier quotes for {quotes[0].quantity if quotes else 0} units.")
    candidates = evaluate_quotes(quotes, policy)
    if scenario == "redirect":
        quote = next((q for q in quotes if q.status == "flagged"), None)
        audit(db, run.id, "policy", "Supplier proposed an alternate account. The controlled demo submits it for on-chain rejection.")
    else:
        quote, run.mode = recommend_quote(candidates) if candidates else (None, run.mode)
    if not quote:
        run.status = "rejected"
        audit(db, run.id, "policy", "No approved supplier quote is available.")
        db.commit()
        return run, None
    amount = negotiate_quote(quote)
    quote.negotiated_amount = amount
    if quote.status != "flagged":
        quote.status = "selected"
    savings = Decimal(int(quote.amount) - int(amount)) / Decimal(10**24)
    supplier_name = db.get(Supplier, quote.supplier_id).name
    audit(db, run.id, "negotiation",
          f"Compared price, delivery and reliability. {supplier_name} accepted a counteroffer saving {savings:f} NEAR.")
    reason = check_policy(policy, quote, amount, scenario)
    order = create_purchase_order(db, run, quote, amount, reason)
    run.status = order.status
    audit(db, run.id, "order", reason or "Purchase order created and ready for the Testnet policy contract.")
    db.commit()
    if (policy.auto_execute or scenario == "redirect") and order.status == "ready":
        try:
            request_onchain_purchase(db, order.id)
        except WorkflowError as exc:
            order.reason = str(exc)
            audit(db, run.id, "policy", order.reason)
            db.commit()
    return run, order


def verify_transaction(db: Session, order: PurchaseOrder, tx: BlockchainTransaction):
    try:
        outcome = chain.verify(tx.hash, tx.signer, tx.contract, order.id, order.account, order.amount)
    except chain.ChainError:
        return
    if not outcome:
        return
    tx.status, tx.receipt_id, tx.reason = outcome
    tx.signed_payload = None
    order.status, order.reason = tx.status, tx.reason
    db.get(AgentRun, order.run_id).status = tx.status
    audit(db, order.run_id, "settlement", tx.reason)


def reconcile(db: Session):
    pending = db.scalars(select(BlockchainTransaction).where(BlockchainTransaction.status == "pending")
                         .with_for_update(skip_locked=True)).all()
    for tx in pending:
        order = db.get(PurchaseOrder, tx.order_id)
        if tx.signed_payload:
            try:
                chain.broadcast(tx.signed_payload)
            except chain.ChainError:
                pass
        verify_transaction(db, order, tx)
    db.commit()


def request_onchain_purchase(db: Session, order_id: str):
    policy = lock_policy(db)
    order = db.get(PurchaseOrder, order_id, with_for_update=True, populate_existing=True)
    if not order:
        raise WorkflowError("Purchase order not found.")
    if order.status not in ("ready", "submitting"):
        return order
    tx = db.scalar(select(BlockchainTransaction).where(BlockchainTransaction.order_id == order.id))
    if not tx:
        run = db.get(AgentRun, order.run_id)
        if policy.paused or (run.scenario == "normal" and order.account not in policy.approved_accounts):
            raise WorkflowError("The current workspace policy blocks this purchase.")
        used = sum(int(o.amount) for o in db.scalars(select(PurchaseOrder).where(PurchaseOrder.status.in_(("paid", "received")))))
        if int(order.amount) > int(policy.max_order) or used + int(order.amount) > int(policy.budget):
            raise WorkflowError("The current workspace spending limit blocks this purchase.")
        if db.scalar(select(BlockchainTransaction.id).where(BlockchainTransaction.status == "pending").limit(1)):
            raise WorkflowError("Another payment is awaiting finality. Refresh Treasury before retrying.")
        try:
            signed = chain.prepare(order.id, order.account, order.amount)
        except chain.ChainError as exc:
            order.reason = str(exc)
            audit(db, order.run_id, "chain", order.reason)
            db.commit()
            return order
        tx = BlockchainTransaction(order_id=order.id, hash=signed["hash"], signer=settings.near_agent_id,
                                   contract=settings.near_contract_id, signed_payload=signed["payload"], status="pending")
        db.add(tx)
        order.status = "submitting"
        order.reason = None
        run.status = order.status
        audit(db, order.run_id, "chain", "Signed purchase recorded. Waiting for Testnet finality.")
        db.commit()
    if tx.signed_payload:
        try:
            chain.broadcast(tx.signed_payload)
        except chain.ChainError:
            pass  # An unknown RPC outcome is reconciled by the persisted transaction hash.
    db.commit()
    return order
