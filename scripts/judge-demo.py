"""Run both demo paths against an existing RestockOS API and print public evidence."""
import json
import os
import time
import urllib.request

BASE = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ["OWNER_TOKEN"]


def request(path, method="GET", body=None):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=80) as result:
        return json.load(result)


def settlement(order_id, expected):
    for _ in range(25):
        tx = next((t for t in request("/transactions") if t["order_id"] == order_id), None)
        if tx and tx["status"] != "pending":
            assert tx["status"] == expected, tx
            return tx
        time.sleep(3)
    raise RuntimeError(f"Order {order_id} did not settle. Inspect the API logs and RPC.")


def main():
    assert request("/health")["status"] == "ok"
    assert len(request("/products")) >= 15
    assert len(request("/suppliers")) == 3
    treasury = request("/treasury")
    assert treasury["policy"] and not treasury["policy"]["paused"], treasury
    run = request("/agent/run", "POST", {"scenario": "normal"})
    order = run["order"]
    assert order, "No eligible shortage. Receive existing orders and reset demo stock first."
    assert len([q for q in request("/quotes") if q["run_id"] == run["id"]]) == 3
    if order["status"] == "ready":
        order = request(f"/purchase-orders/{order['id']}/execute", "POST")
    assert order["status"] in ("submitting", "paid"), order
    paid = settlement(order["id"], "paid")
    assert paid["receipt_id"], paid
    after_paid = request("/treasury")["policy"]
    amount = int(order["amount"])
    assert int(after_paid["spent"]) - int(treasury["policy"]["spent"]) == amount
    assert int(treasury["policy"]["available"]) - int(after_paid["available"]) == amount
    bad = request("/agent/run", "POST", {"scenario": "redirect"})["order"]
    assert bad and bad["status"] == "submitting", bad
    rejected = settlement(bad["id"], "rejected")
    assert "allowlist" in rejected["reason"], rejected
    after_bad = request("/treasury")["policy"]
    assert {k: after_paid[k] for k in ("available", "reserved", "spent")} == {
        k: after_bad[k] for k in ("available", "reserved", "spent")
    }
    print(json.dumps({"contract": treasury["contract"], "paid": paid, "rejected": rejected,
                      "treasury_after_payment": after_paid}, indent=2))


if __name__ == "__main__":
    main()
