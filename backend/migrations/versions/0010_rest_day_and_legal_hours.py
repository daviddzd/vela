"""Weekly rest day and legal working hours (LFT arts. 60, 61 and 69; app/services/labor.py).

- caregivers.rest_day: ISO weekday (1 Monday ... 7 Sunday), assigned in rotation with labor.assign_rest_days (the same
  function SIRAG-D uses), editable in /personal.
- Diurna / mixta shifts above the art. 61 maximum are shortened with labor.legal_shift (the seed's evening shift
  14:00-22:00 is mixta -> 14:00-21:30). Nocturna shifts are NOT changed; /personal flags them and coordination gets
  an alert (alerts.type 'labor').
- The seed CSVs are not touched: they remain the "before Vela" baseline (staff assigned 7 days a week).

Revision ID: 0010
Revises: 0009
"""
import sys
from pathlib import Path

from alembic import op
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # backend/ -> import app.services.labor
from app.services import labor  # noqa: E402

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    op.execute("ALTER TABLE caregivers ADD COLUMN rest_day smallint CHECK (rest_day BETWEEN 1 AND 7)")
    rows = conn.execute(text("""
        SELECT c.caregiver_id, c.institution_id, c.shift_start, c.shift_end, array_agg(k.skill) AS skills
        FROM caregivers c JOIN caregiver_skills k USING (caregiver_id) GROUP BY c.caregiver_id""")).mappings().all()
    for r in rows:
        legal = labor.legal_shift(r["shift_start"], r["shift_end"])
        if legal["adjusted"]:
            conn.execute(text("UPDATE caregivers SET shift_end = :e WHERE caregiver_id = :c"),
                         {"e": legal["end"], "c": r["caregiver_id"]})
    people = [{"caregiver_id": r["caregiver_id"], "institution_id": r["institution_id"], "shift_start": r["shift_start"],
               "shift_end": labor.legal_shift(r["shift_start"], r["shift_end"])["end"], "skill": labor.main_skill(r["skills"])}
              for r in rows]
    for cid, day in labor.assign_rest_days(people).items():
        conn.execute(text("UPDATE caregivers SET rest_day = :d WHERE caregiver_id = :c"), {"d": day, "c": cid})
    op.execute("ALTER TABLE caregivers ALTER COLUMN rest_day SET NOT NULL")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute("""ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN
                  ('emergency','risk','contingency','anomaly','queue_delay','call_back','consent','care_plan','labor'))""")


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
