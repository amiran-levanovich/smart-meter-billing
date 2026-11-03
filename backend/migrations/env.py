from alembic import context
from sqlalchemy import create_engine

from app.config import database_url
from app.db import Base

url = context.config.get_main_option("sqlalchemy.url") or database_url()

with create_engine(url).connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
