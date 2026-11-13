import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/restockos"
    owner_token: str = ""
    automation_token: str = ""
    web_origin: str = "http://localhost:3000"
    near_rpc_url: str = "https://test.rpc.fastnear.com"
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


def session():
    with Session(engine(), expire_on_commit=False) as db:
        yield db
