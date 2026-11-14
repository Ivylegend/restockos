"""Wallet-backed workspace sessions and the preserved local admin token."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException

DEMO_WORKSPACE = "admin-demo"


@dataclass(frozen=True)
class Principal:
    workspace_id: str
    account_id: str | None
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _secret(settings) -> bytes:
    value = settings.session_secret or settings.owner_token
    if not value:
        raise HTTPException(503, "Set SESSION_SECRET before enabling wallet workspaces.")
    return value.encode()


def create_session(settings, workspace_id: str, account_id: str, role: str = "owner") -> str:
    payload = {"sub": account_id, "wid": workspace_id, "role": role, "exp": int(time.time()) + 43200}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_secret(settings), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def resolve_principal(authorization: str | None, settings, *, public: bool = False) -> Principal | None:
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization[7:].encode()
        for token, role in ((settings.owner_token, "admin"), (settings.automation_token, "automation")):
            if token and hmac.compare_digest(supplied, token.encode()):
                return Principal(DEMO_WORKSPACE, None, role)
        raw = authorization[7:]
        try:
            body, signature = raw.split(".", 1)
            expected = _b64(hmac.new(_secret(settings), body.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if int(payload["exp"]) < int(time.time()):
                return None
            workspace_id, account_id = payload["wid"], payload["sub"]
            role = payload["role"]
            if not isinstance(workspace_id, str) or not isinstance(account_id, str) or role not in ("owner", "admin"):
                return None
            if role == "admin" and account_id not in settings.admin_account_ids:
                return None
            return Principal(workspace_id, account_id, role)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, HTTPException):
            return None
    if public and settings.demo_enabled and settings.public_demo:
        return Principal(DEMO_WORKSPACE, None, "viewer")
    return None


def require_principal(authorization: str | None, settings, *, public: bool = False) -> Principal:
    principal = resolve_principal(authorization, settings, public=public)
    if principal is None:
        raise HTTPException(401, "Connect a NEAR Testnet wallet or provide the admin access token.")
    return principal


def nonce() -> str:
    return _b64(secrets.token_bytes(32))
