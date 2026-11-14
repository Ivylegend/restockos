from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

Yocto = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]{0,38})$")]
Account = Annotated[str, StringConstraints(min_length=2, max_length=64, pattern=r"^(?:[a-z0-9]+[-_.])*[a-z0-9]+$")]
MAX_AMOUNT = 2**128 - 1


class ProductInput(BaseModel, extra="forbid"):
    sku: str = Field(min_length=2, max_length=24, pattern=r"^[A-Z0-9-]+$")
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    stock: int = Field(ge=0, le=1_000_000)
    reorder_point: int = Field(ge=1, le=100_000)
    daily_sales: float = Field(ge=0, le=10_000)
    unit_price: Yocto

    @field_validator("unit_price")
    @classmethod
    def validate_price(cls, value):
        if not 0 < int(value) <= 10**30:
            raise ValueError("Unit price must be positive and within the catalog limit")
        return value


class StockUpdate(BaseModel, extra="forbid"):
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    reorder_point: int | None = Field(default=None, ge=1, le=100_000)
    daily_sales: float | None = Field(default=None, ge=0, le=10_000)


class PolicyInput(BaseModel, extra="forbid"):
    paused: bool
    auto_execute: bool
    approved_accounts: list[Account] = Field(max_length=50)
    max_order: Yocto
    budget: Yocto

    @model_validator(mode="after")
    def caps(self):
        if not 0 <= int(self.max_order) <= int(self.budget) <= MAX_AMOUNT:
            raise ValueError("Order cap must be within the total budget and u128 range")
        if len(set(self.approved_accounts)) != len(self.approved_accounts):
            raise ValueError("Supplier accounts must be unique")
        return self


class RunInput(BaseModel, extra="forbid"):
    scenario: Literal["normal", "redirect"] = "normal"


class WalletVerifyInput(BaseModel, extra="forbid"):
    account_id: Account
    public_key: str = Field(min_length=8, max_length=100)
    signature: str = Field(min_length=32, max_length=200)
    nonce: str = Field(min_length=32, max_length=64)


class WorkspaceContractInput(BaseModel, extra="forbid"):
    contract_id: Account


class TransactionVerifyInput(BaseModel, extra="forbid"):
    order_id: str = Field(min_length=8, max_length=36)
    hash: str = Field(min_length=32, max_length=64, pattern=r"^[1-9A-HJ-NP-Za-km-z]+$")
