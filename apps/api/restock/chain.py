import base64
import json
import os
import subprocess
from pathlib import Path

import httpx

from .db import settings

SIGNER = Path(__file__).resolve().parents[3] / "scripts" / "sign-purchase.mjs"
VIOLATIONS = {
    "UNAUTHORIZED_AGENT": "Signer is outside the authorized agent role.",
    "SUPPLIER_NOT_ALLOWED": "Supplier account is outside the on-chain allowlist.",
    "PER_ORDER_CAP": "Payment exceeds the on-chain per-order cap.",
    "BUDGET_CAP": "Payment exceeds the remaining on-chain budget.",
    "INSUFFICIENT_TREASURY": "On-chain treasury has insufficient funds.",
    "AGENT_PAUSED": "The on-chain agent is paused.",
    "ORDER_ALREADY_USED": "The contract has already reserved this order ID.",
}


class ChainError(Exception):
    pass


def rpc(method: str, params: dict):
    try:
        result = httpx.post(settings.near_rpc_url, timeout=10, json={
            "jsonrpc": "2.0", "id": "restockos", "method": method, "params": params,
        })
        result.raise_for_status()
        payload = result.json()
        if "error" in payload:
            raise ChainError("NEAR RPC could not confirm this request.")
        return payload["result"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise ChainError("NEAR RPC is unavailable.") from exc


def require_testnet():
    status = rpc("status", [])
    if status.get("chain_id") != "testnet":
        raise ChainError("RestockOS only supports NEAR Testnet transactions.")


def view(method: str, args: dict, contract: str | None = None):
    contract = contract or settings.near_contract_id
    if contract and not contract.endswith(".testnet"):
        raise ChainError("RestockOS only supports NEAR Testnet contracts.")
    require_testnet()
    result = rpc("query", {
        "request_type": "call_function", "finality": "final",
        "account_id": contract, "method_name": method,
        "args_base64": base64.b64encode(json.dumps(args).encode()).decode(),
    })
    return json.loads(bytes(result["result"]))


def prepare(order_id: str, supplier: str, amount: str) -> dict[str, str]:
    if not (settings.near_contract_id and settings.near_agent_id and settings.near_agent_private_key):
        raise ChainError("Connect a Testnet contract and a scoped agent key before requesting payment.")
    args = dict(near_rpc_url=settings.near_rpc_url, contract=settings.near_contract_id,
                agent=settings.near_agent_id, order_id=order_id, supplier=supplier, amount=amount)
    try:
        result = subprocess.run(
            ["node", str(SIGNER), json.dumps(args)], capture_output=True, text=True, timeout=20,
            env={**os.environ, "NEAR_AGENT_PRIVATE_KEY": settings.near_agent_private_key},
        )
        if result.returncode:
            raise ChainError(result.stderr.strip() or "The NEAR signer could not prepare the payment.")
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise ChainError("The NEAR signing service is unavailable.") from exc


def broadcast(payload: str):
    rpc("send_tx", {"signed_tx_base64": payload, "wait_until": "NONE"})


def verify(tx_hash: str, signer: str, contract: str, order_id: str, account: str, amount: str):
    if not signer.endswith(".testnet") or not contract.endswith(".testnet"):
        raise ChainError("RestockOS only supports NEAR Testnet transactions.")
    require_testnet()
    result = rpc("tx", {"tx_hash": tx_hash, "sender_account_id": signer, "wait_until": "FINAL"})
    if result.get("final_execution_status") != "FINAL":
        return None
    tx = result.get("transaction", {})
    if (tx.get("hash"), tx.get("signer_id"), tx.get("receiver_id")) != (tx_hash, signer, contract):
        raise ChainError("RPC returned an unrelated transaction.")
    # A caller-supplied hash must refer to this exact purchase call even when
    # execution failed. Otherwise an unrelated failed transaction could mark
    # a purchase order as rejected in the application.
    actions = tx.get("actions", [])
    calls = [action.get("FunctionCall") for action in actions if action.get("FunctionCall")]
    if len(actions) != 1 or len(calls) != 1 or calls[0].get("method_name") != "execute_purchase":
        raise ChainError("Transaction does not contain the expected purchase call.")
    try:
        call_args = json.loads(base64.b64decode(calls[0]["args"], validate=True))
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ChainError("Purchase transaction arguments could not be verified.") from exc
    if call_args != {"order_id": order_id, "supplier": account, "amount": amount}:
        raise ChainError("Transaction purchase details do not match the order.")
    status = result.get("status", {})
    if "Failure" in status:
        details = json.dumps(status["Failure"])
        reason = next((message for code, message in VIOLATIONS.items() if code in details),
                      "NEAR rejected execution. See the transaction for details.")
        rejection_receipt = next((
            outcome["id"] for outcome in result.get("receipts_outcome", [])
            if outcome["outcome"]["executor_id"] == contract and "Failure" in outcome["outcome"]["status"]
        ), None)
        return "rejected", rejection_receipt, reason
    purchase = view("get_purchase", {"order_id": order_id}, contract)
    if not purchase or purchase["status"] == "pending":
        return None
    if (purchase["supplier"], purchase["amount"]) != (account, amount):
        raise ChainError("On-chain purchase details differ from the order.")
    if "SuccessValue" not in status:
        return None
    callback_id = next((
        outcome["id"] for outcome in result.get("receipts_outcome", [])
        if outcome["outcome"]["executor_id"] == contract
        and outcome["outcome"]["status"].get("SuccessValue") == status["SuccessValue"]
    ), None)
    if not callback_id:
        return None
    if purchase["status"] == "success":
        return "paid", callback_id, "Testnet transfer verified at finality."
    return "failed", callback_id, "Supplier transfer failed. Reserved funds returned to the treasury."
