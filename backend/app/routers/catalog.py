"""Services that the user's institution offers (for the request forms)."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, current_user, tenant_db

router = APIRouter(prefix="/api/services", tags=["catalog"])


@router.get("")
def list_services(user: CurrentUser = Depends(current_user), db: Session = Depends(tenant_db)) -> list[dict]:
    rows = db.execute(text("""
        SELECT s.service_id, s.name, s.required_skill, ins.duration_min
        FROM institution_services ins JOIN services s USING (service_id)
        WHERE ins.active ORDER BY s.service_id""")).mappings().all()
    return [dict(r) for r in rows]
