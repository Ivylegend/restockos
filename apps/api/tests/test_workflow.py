import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from restock import chain
from restock.db import Base, session, settings
from restock.main import app
from restock.models import BlockchainTransaction
from restock.procurement import reconcile
from restock.seed import seed


@pytest.fixture
def workspace(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "owner_token", "test-owner")
    monkeypatch.setattr(settings, "automation_token", "test-scheduler")
    monkeypatch.setattr(settings, "demo_enabled", True)
    monkeypatch.setattr(settings, "near_contract_id", "")
    monkeypatch.setattr(settings, "near_agent_id", "agent.testnet")
    monkeypatch.setattr(settings, "demo_supplier_accounts", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    with Session(engine) as db, db.begin():
        seed(db)

    def override():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[session] = override
    try:
        yield TestClient(app), engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


OWNER = {"Authorization": "Bearer test-owner"}
AUTOMATION = {"Authorization": "Bearer test-scheduler"}


def test_authorization_and_inventory(workspace):
    client, _ = workspace
    assert client.get("/health").status_code == 200
    assert client.get("/products").status_code == 401
    assert client.post("/purchase-orders/missing/execute").status_code == 401
    assert client.post("/demo/reset", headers=AUTOMATION).status_code == 401
    assert client.post("/agent/run", headers=AUTOMATION, json={"scenario": "redirect"}).status_code == 401
    catalog = client.get("/products", headers=OWNER).json()
    assert len(catalog) == 16
    assert client.patch("/products/1", headers=OWNER, json={"stock": -1}).status_code == 422
    assert client.patch("/products/1", headers=OWNER, json={"stock": 4}).json()["stock"] == 4
    assert client.get("/dashboard/summary", headers=OWNER).json()["shortages"] == 3
    assert client.post("/demo/reset", headers=OWNER).status_code == 204
    assert client.get("/products", headers=OWNER).json()[0]["stock"] == 3


def test_procurement_requires_chain_evidence_and_receives_once(workspace, monkeypatch):
    client, engine = workspace
    run = client.post("/agent/run", headers=AUTOMATION, json={}).json()
    order_id = run["order"]["id"]
    assert run["status"] == "ready"
    assert len(client.get("/quotes", headers=OWNER).json()) == 3
    orders = client.get("/purchase-orders", headers=OWNER).json()
    assert orders[0]["product"] == "USB-C 65W Charger"
    assert orders[0]["quantity"] == 37
    endpoint = f"/purchase-orders/{order_id}"
    assert client.post(endpoint + "/execute", headers=OWNER).json()["status"] == "ready"
    assert client.get("/transactions", headers=OWNER).json() == []

    signed = []
    monkeypatch.setattr(chain, "prepare", lambda *args: signed.append(args) or {"hash": "test-tx", "payload": "test-payload"})
    monkeypatch.setattr(chain, "broadcast", lambda _payload: None)
    monkeypatch.setattr(chain, "verify", lambda *_args: None)
    assert client.post(endpoint + "/execute", headers=OWNER).json()["status"] == "submitting"
    assert client.post(endpoint + "/execute", headers=OWNER).json()["status"] == "submitting"
    assert len(signed) == 1
    assert client.post(endpoint + "/receive", headers=OWNER).status_code == 409
    assert "signed_payload" not in client.get("/transactions", headers=OWNER).json()[0]
    with Session(engine) as db:
        reconcile(db)
        assert db.scalar(select(BlockchainTransaction.status)) == "pending"
        monkeypatch.setattr(chain, "verify", lambda *_args: ("paid", "test-receipt", "Test outcome"))
        reconcile(db)
    assert client.get("/transactions", headers=OWNER).json()[0]["receipt_id"] == "test-receipt"
    assert client.post(endpoint + "/receive", headers=OWNER).json()["status"] == "received"
    assert client.post(endpoint + "/receive", headers=OWNER).status_code == 409
    assert client.get("/products", headers=OWNER).json()[0]["stock"] == 40


def test_public_demo_allows_reads_only(workspace, monkeypatch):
    client, _ = workspace
    monkeypatch.setattr(settings, "public_demo", True)
    assert client.get("/demo/access").json()["public_read_only"]
    for path in ("/dashboard/summary", "/products", "/suppliers", "/quotes", "/purchase-orders",
                 "/agent/runs", "/transactions", "/treasury"):
        assert client.get(path).status_code == 200, path
    for method, path in (
        ("GET", "/agent/policy"), ("GET", "/workspace"), ("PUT", "/agent/policy"),
        ("POST", "/products"), ("PATCH", "/products/1"), ("POST", "/agent/run"),
        ("POST", "/purchase-orders/missing/execute"), ("POST", "/purchase-orders/missing/receive"),
        ("POST", "/demo/reset"),
    ):
        assert client.request(method, path, json={} if method != "GET" else None).status_code == 401, path
    monkeypatch.setattr(settings, "demo_enabled", False)
    assert not client.get("/demo/access").json()["public_read_only"]
    assert client.get("/products").status_code == 401
