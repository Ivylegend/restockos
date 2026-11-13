from alembic import context

from restock.db import Base, engine
from restock import models  # noqa: F401

with engine().connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
