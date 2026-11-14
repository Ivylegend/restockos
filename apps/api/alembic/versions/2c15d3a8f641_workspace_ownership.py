"""Add wallet-owned workspaces and scope business records by workspace.

Revision ID: 2c15d3a8f641
Revises: 69979f29be0a
"""
from alembic import op
import sqlalchemy as sa

revision = "2c15d3a8f641"
down_revision = "69979f29be0a"
branch_labels = None
depends_on = None

TABLES = (
    "products", "suppliers", "agent_policy", "agent_runs", "supplier_quotes",
    "purchase_orders", "purchase_order_items", "inventory_movements",
    "blockchain_transactions", "audit_events",
)


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("owner_account", sa.String(64), nullable=False, unique=True),
        sa.Column("contract_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_challenges",
        sa.Column("nonce", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("INSERT INTO workspaces (id, name, owner_account, created_at) "
               "VALUES ('admin-demo', 'Northline Electronics', 'admin-demo.testnet', CURRENT_TIMESTAMP)")

    for table in TABLES:
        op.add_column(table, sa.Column("workspace_id", sa.String(64), nullable=True))
        op.execute(sa.text(f"UPDATE {table} SET workspace_id = 'admin-demo'"))
        op.alter_column(table, "workspace_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_workspace", table, "workspaces", ["workspace_id"], ["id"])
        if table != "agent_policy":
            op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])

    op.drop_constraint("products_sku_key", "products", type_="unique")
    op.create_unique_constraint("uq_products_workspace_sku", "products", ["workspace_id", "sku"])
    op.drop_constraint("suppliers_name_key", "suppliers", type_="unique")
    op.drop_constraint("suppliers_account_key", "suppliers", type_="unique")
    op.create_unique_constraint("uq_suppliers_workspace_name", "suppliers", ["workspace_id", "name"])
    op.create_unique_constraint("uq_suppliers_workspace_account", "suppliers", ["workspace_id", "account"])
    op.create_unique_constraint("uq_agent_policy_workspace", "agent_policy", ["workspace_id"])


def downgrade() -> None:
    op.drop_constraint("uq_agent_policy_workspace", "agent_policy", type_="unique")
    op.drop_constraint("uq_suppliers_workspace_account", "suppliers", type_="unique")
    op.drop_constraint("uq_suppliers_workspace_name", "suppliers", type_="unique")
    op.create_unique_constraint("suppliers_account_key", "suppliers", ["account"])
    op.create_unique_constraint("suppliers_name_key", "suppliers", ["name"])
    op.drop_constraint("uq_products_workspace_sku", "products", type_="unique")
    op.create_unique_constraint("products_sku_key", "products", ["sku"])
    for table in reversed(TABLES):
        if table != "agent_policy":
            op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        op.drop_constraint(f"fk_{table}_workspace", table, type_="foreignkey")
        op.drop_column(table, "workspace_id")
    op.drop_table("auth_challenges")
    op.drop_table("workspaces")
