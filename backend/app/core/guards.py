"""Who may see what, beyond tenant isolation (minimisation, docs/spec/11):

  coordinator → the whole institution          owner  → everything ('*')
  physician   → only patients that have (or had) an assignment with them
  caregiver   → only their own assignments
  family      → only their own patient

Every denial answers 403 and is written to audit_log in its own transaction.
"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit_now
from app.core.deps import CurrentUser
from app.core.roles import CAREGIVER, FAMILY, PHYSICIAN


def deny(user: CurrentUser, action: str, entity: str, entity_id: str, message: str, **detail) -> HTTPException:
    """Record the blocked attempt and return the 403 to raise."""
    audit_now(user_id=user.user_id, institution_id=user.institution_id, action=action, entity=entity,
              entity_id=entity_id, allowed=False, detail=detail or None)
    return HTTPException(status.HTTP_403_FORBIDDEN, message)


def not_found_or_cross_tenant(db: Session, user: CurrentUser, entity: str, entity_id: str) -> HTTPException:
    """RLS hid the row: tell apart "belongs to another institution" (403 + audit) from "does not exist"
    (404) with entity_institution() (see docs/dev/decisiones_paso_1_2.md)."""
    owner_inst = db.scalar(text("SELECT entity_institution(:e, :i)"), {"e": entity, "i": entity_id})
    if owner_inst is not None and owner_inst != user.institution_id:
        return deny(user, "blocked_cross_tenant", entity, entity_id,
                    "Este registro pertenece a otra institución. El intento quedó registrado.",
                    target_institution=owner_inst)
    return HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado.")


def family_patient_id(db: Session, user: CurrentUser) -> str:
    return db.scalar(text("SELECT patient_id FROM family_members WHERE family_member_id = :f"),
                     {"f": user.family_member_id})


def can_see_patient(db: Session, user: CurrentUser, patient_id: str) -> bool:
    """Role scope inside the institution (RLS already limited the institution)."""
    if user.role == PHYSICIAN:
        return bool(db.scalar(text("""
            SELECT EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                           WHERE a.caregiver_id = :c AND r.patient_id = :p)"""),
            {"c": user.caregiver_id, "p": patient_id}))
    if user.role == FAMILY:
        return family_patient_id(db, user) == patient_id
    if user.role == CAREGIVER:
        return False   # caregivers see visits, not patient records
    return True        # coordinator, owner


def ensure_patient_scope(db: Session, user: CurrentUser, patient_id: str) -> None:
    if not can_see_patient(db, user, patient_id):
        raise deny(user, "blocked_out_of_scope", "patient", patient_id,
                   "Esta persona no está a tu cargo. El intento quedó registrado.")


def ensure_own_assignment(db: Session, user: CurrentUser, assignment_id: str) -> None:
    """Caregiver/physician acting on a visit: it must exist and be theirs."""
    caregiver = db.scalar(text("SELECT caregiver_id FROM assignments WHERE assignment_id = :a AND status = 'active'"),
                          {"a": assignment_id})
    if caregiver is None:
        raise not_found_or_cross_tenant(db, user, "assignment", assignment_id)
    if caregiver != user.caregiver_id:
        raise deny(user, "blocked_out_of_scope", "assignment", assignment_id,
                   "Esta visita no está asignada a ti. El intento quedó registrado.")
