"""Database engine and the tenant-scoped session.

Every request that touches tenant data opens ONE transaction and runs
    SELECT set_config('app.institution_id', <id>, true)
which is the parameterised form of `SET LOCAL app.institution_id = '<id>'`: the value lives only
until the transaction ends, so it can never leak to the next request that reuses the connection.
Without the setting, the RLS policies in database/sql/004_row_level_security.sql return zero rows.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Value that the RLS policies understand as "all institutions" (only for the owner role).
ALL_INSTITUTIONS = "*"


def set_tenant(session: Session, institution_id: str) -> None:
    """Scope the current transaction to one institution (or '*' for the owner)."""
    session.execute(text("SELECT set_config('app.institution_id', :v, true)"), {"v": institution_id})


@contextmanager
def tenant_session(institution_id: str | None) -> Iterator[Session]:
    """Open a transaction scoped to a tenant. None = no setting = zero rows (fail closed)."""
    with SessionLocal() as session, session.begin():
        if institution_id is not None:
            set_tenant(session, institution_id)
        yield session
