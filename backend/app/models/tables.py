"""SQLAlchemy models for the tables used so far. The schema itself is created by
database/sql/001_schema.sql (baseline) and later by Alembic migrations; these classes only map it."""
from datetime import date, datetime

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """Demo accounts. Not under RLS: login has to find the user before knowing the institution."""
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str]
    institution_id: Mapped[str | None]
    caregiver_id: Mapped[str | None]
    family_member_id: Mapped[str | None]
    display_name: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    active: Mapped[bool]


class Person(Base):
    """Synthetic 60+ population (master person index). Only the name columns are mapped here."""
    __tablename__ = "persons"
    person_id: Mapped[str] = mapped_column(Text, primary_key=True)
    first_name: Mapped[str]
    paternal_surname: Mapped[str]
    maternal_surname: Mapped[str]


class Patient(Base):
    """Patients of an institution. Under RLS (tenant_isolation policy)."""
    __tablename__ = "patients"
    patient_id: Mapped[str] = mapped_column(Text, primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.person_id"))
    institution_id: Mapped[str]
    admission_date: Mapped[date]
    base_priority: Mapped[str]
    active: Mapped[bool]


class AuditLog(Base):
    """Append-only trail: vela_api can INSERT and SELECT, never UPDATE or DELETE."""
    __tablename__ = "audit_log"
    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(server_default="now()")
    user_id: Mapped[str | None]
    institution_id: Mapped[str | None]
    action: Mapped[str]
    entity: Mapped[str]
    entity_id: Mapped[str | None]
    allowed: Mapped[bool]
    detail: Mapped[dict | None] = mapped_column(JSONB)
