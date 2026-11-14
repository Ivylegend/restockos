import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from types import SimpleNamespace

from restock import chain
from restock.auth import create_session
from restock.db import Base, session, settings
from restock.main import app
from restock import main as main_module
from restock.models import (AgentRun, BlockchainTransaction, Product, PurchaseOrder, SupplierQuote,
                            Workspace)
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
    main_module.RATE_LIMITS.clear()
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
    assert client.post("/demo/reset", headers=AUTOMATION).status_code == 403
    assert client.post("/agent/run", headers=AUTOMATION, json={"scenario": "redirect"}).status_code == 403
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


def test_public_demo_allows_reads_and_sandbox_but_protects_live_actions(workspace, monkeypatch):
    client, _ = workspace
    monkeypatch.setattr(settings, "public_demo", True)
    assert client.get("/demo/access").json()["public_access"]
    for path in ("/dashboard/summary", "/products", "/suppliers", "/quotes", "/purchase-orders",
                 "/agent/runs", "/transactions", "/treasury"):
        assert client.get(path).status_code == 200, path
    simulated = client.post("/demo/run")
    assert simulated.status_code == 200
    assert simulated.json()["simulation"] is True
    assert simulated.json()["order"]["status"] == "simulated"
    assert "NEAR transaction was sent" in simulated.json()["notice"]
    assert client.get("/transactions").json() == []
    assert all(client.post("/demo/run").status_code == 200 for _ in range(4))
    assert client.post("/demo/run").status_code == 429
    for method, path in (
        ("GET", "/agent/policy"), ("GET", "/workspace"), ("PUT", "/agent/policy"),
        ("POST", "/products"), ("PATCH", "/products/1"), ("POST", "/agent/run"),
        ("POST", "/purchase-orders/missing/execute"), ("POST", "/purchase-orders/missing/receive"),
        ("POST", "/purchase-orders/missing/authorize"), ("POST", "/transactions/verify"),
        ("PUT", "/workspace/contract"), ("POST", "/demo/reset"),
    ):
        body = {} if method != "GET" else None
        if path == "/transactions/verify":
            body = {"order_id": "00000000-0000-0000-0000-000000000000", "hash": "1" * 44}
        if path == "/workspace/contract":
            body = {"contract_id": "policy.alice.testnet"}
        assert client.request(method, path, json=body).status_code == 401, path
    monkeypatch.setattr(settings, "demo_enabled", False)
    assert not client.get("/demo/access").json()["public_access"]
    assert client.get("/products").status_code == 401
    assert client.post("/demo/run").status_code == 403


def test_wallet_challenge_creates_one_workspace_and_cannot_be_replayed(workspace, monkeypatch):
    client, _ = workspace
    from restock import main

    monkeypatch.setattr(main.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="verified", stderr=""))
    challenge = client.get("/auth/challenge", params={"account_id": "alice.testnet"})
    assert challenge.status_code == 200
    message = challenge.json()
    verified = client.post("/auth/verify", json={
        "account_id": "alice.testnet", "public_key": "ed25519:" + "1" * 40,
        "signature": "A" * 88, "nonce": message["nonce"],
    })
    assert verified.status_code == 200
    assert verified.json()["workspace"]["owner_account"] == "alice.testnet"
    headers = {"Authorization": "Bearer " + verified.json()["access_token"]}
    assert len(client.get("/products", headers=headers).json()) == 16
    assert client.post("/auth/verify", json={
        "account_id": "alice.testnet", "public_key": "ed25519:" + "1" * 40,
        "signature": "A" * 88, "nonce": message["nonce"],
    }).status_code == 401


def test_allowlisted_wallet_receives_admin_role_without_replacing_admin_token(workspace, monkeypatch):
    client, _ = workspace
    monkeypatch.setattr(settings, "admin_account_ids", ["ops.testnet"])
    monkeypatch.setattr(main_module.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="verified", stderr=""))
    challenge = client.get("/auth/challenge", params={"account_id": "ops.testnet"}).json()
    result = client.post("/auth/verify", json={
        "account_id": "ops.testnet", "public_key": "ed25519:" + "1" * 40,
        "signature": "A" * 88, "nonce": challenge["nonce"],
    })
    assert result.status_code == 200
    assert result.json()["role"] == "admin"
    wallet_headers = {"Authorization": "Bearer " + result.json()["access_token"]}
    assert client.get("/workspace", headers=wallet_headers).json()["role"] == "admin"
    assert client.get("/agent/policy", headers=OWNER).status_code == 200


def test_workspace_records_are_isolated_for_wallet_owners(workspace):
    client, engine = workspace
    with Session(engine) as db, db.begin():
        db.add(Workspace(id="ws-bob", name="Bob Workspace", owner_account="bob.testnet"))
        db.info["workspace_id"] = "ws-bob"
        seed(db, "ws-bob", "bob.testnet", "Bob Workspace")
    alice = create_session(settings, "admin-demo", "alice.testnet")
    bob = create_session(settings, "ws-bob", "bob.testnet")
    alice_headers = {"Authorization": "Bearer " + alice}
    bob_headers = {"Authorization": "Bearer " + bob}
    run = client.post("/agent/run", headers=bob_headers, json={}).json()
    order_id = run["order"]["id"]
    with Session(engine) as db:
        order = db.get(PurchaseOrder, order_id)
        order.status = "paid"
        db.add(BlockchainTransaction(workspace_id="ws-bob", order_id=order_id, hash="bob-testnet-hash",
                                     signer="bob.testnet", contract="policy.bob.testnet", signed_payload=None,
                                     status="paid", receipt_id="bob-receipt"))
        db.commit()
    alice_catalog = client.get("/products", headers=alice_headers).json()
    bob_catalog = client.get("/products", headers=bob_headers).json()
    assert len(alice_catalog) == len(bob_catalog) == 16
    assert alice_catalog[0]["id"] != bob_catalog[0]["id"]
    changed = client.patch(f"/products/{bob_catalog[0]['id']}", headers=alice_headers, json={"stock": 1})
    assert changed.status_code == 404
    own = client.patch(f"/products/{bob_catalog[0]['id']}", headers=bob_headers, json={"stock": 1})
    assert own.status_code == 200
    assert client.get("/products", headers=alice_headers).json()[0]["stock"] != 1
    assert client.get("/quotes", headers=alice_headers).json() == []
    assert len(client.get("/quotes", headers=bob_headers).json()) == 3
    assert client.get("/purchase-orders", headers=alice_headers).json() == []
    assert len(client.get("/purchase-orders", headers=bob_headers).json()) == 1
    assert client.get("/transactions", headers=alice_headers).json() == []
    assert len(client.get("/transactions", headers=bob_headers).json()) == 1
    assert client.get("/agent/runs", headers=alice_headers).json() == []
    assert len(client.get("/agent/runs", headers=bob_headers).json()) == 1
    assert client.post(f"/purchase-orders/{order_id}/receive", headers=alice_headers).status_code == 409
    assert client.post(f"/purchase-orders/{order_id}/receive", headers=bob_headers).status_code == 200
