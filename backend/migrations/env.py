"""Alembic environment. Baseline = database/sql/001-005 (loaded by infra/db-init.sh);
migrations here only add changes on top of that baseline. Plain SQL migrations, no autogenerate."""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

url = os.environ["OWNER_DATABASE_URL"]  # table owner: only the migrate service has it

with create_engine(url).connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
