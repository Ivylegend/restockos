import logging
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, with_loader_criteria


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/restockos"
    owner_token: str = ""
    session_secret: str = ""
    automation_token: str = ""
    admin_account_ids: list[str] = []
    auth_recipient: str = "localhost"
    web_origin: str = "http://localhost:3000"
    near_rpc_url: str = "https://rpc.testnet.near.org"
    near_contract_id: str = ""
    near_agent_id: str = ""
    near_agent_private_key: str = ""
    demo_supplier_accounts: str = ""
    demo_enabled: bool = False
    public_demo: bool = False
    scan_interval_seconds: int = 0
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"


settings = Settings()
logger = logging.getLogger("uvicorn.error")


@lru_cache
def engine():
    url = settings.database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


def session(request: Request):
    from .auth import resolve_principal

    authorization = request.headers.get("authorization") if request else None
    principal = resolve_principal(authorization, settings,
                                  public=bool(settings.demo_enabled and settings.public_demo))
    workspace_id = principal.workspace_id if principal else "admin-demo"
    with Session(engine(), expire_on_commit=False) as db:
        db.info["workspace_id"] = workspace_id
        yield db


@event.listens_for(Session, "do_orm_execute")
def _scope_queries(execute_state):
    workspace_id = execute_state.session.info.get("workspace_id")
    if not workspace_id or not execute_state.is_orm_statement:
        return
    from .models import (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction,
                         InventoryMovement, Product, PurchaseOrder, PurchaseOrderItem,
                         Supplier, SupplierQuote)

    scoped = (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction, InventoryMovement,
              Product, PurchaseOrder, PurchaseOrderItem, Supplier, SupplierQuote)
    statement = execute_state.statement
    for model in scoped:
        statement = statement.options(with_loader_criteria(
            model, lambda cls: cls.workspace_id == workspace_id, include_aliases=True,
        ))
    execute_state.statement = statement


@event.listens_for(Session, "before_flush")
def _assign_workspace_id(db, _flush_context, _instances):
    workspace_id = db.info.get("workspace_id")
    if not workspace_id:
        return
    from .models import (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction,
                         InventoryMovement, Product, PurchaseOrder, PurchaseOrderItem,
                         Supplier, SupplierQuote)

    scoped = (AgentPolicy, AgentRun, AuditEvent, BlockchainTransaction, InventoryMovement,
              Product, PurchaseOrder, PurchaseOrderItem, Supplier, SupplierQuote)
    for obj in db.new:
        if isinstance(obj, scoped):
            if not obj.workspace_id:
                obj.workspace_id = workspace_id
            elif obj.workspace_id != workspace_id:
                raise ValueError("Cannot write a record outside the authenticated workspace.")
