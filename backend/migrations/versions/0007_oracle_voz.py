"""ORACLE-Voz: what the pipeline stores (no audio is ever stored, only the transcript).

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE voice_reports
          ADD COLUMN input_mode       text  NOT NULL DEFAULT 'audio' CHECK (input_mode IN ('audio','text','demo_text')),
          ADD COLUMN classifier_label text  CHECK (classifier_label IN ('emergency','urgent','routine')),
          ADD COLUMN classifier_probs jsonb,
          ADD COLUMN no_speech_prob   numeric(4,3),
          ADD COLUMN report_status    text  NOT NULL DEFAULT 'pending'
                                     CHECK (report_status IN ('pending','ready','invalid','failed')),
          ADD COLUMN report_problem   text,
          ADD COLUMN timings          jsonb NOT NULL DEFAULT '{}'""")
    # "No hablo español / Pedir que alguien me llame" (docs/spec/05) is a request to coordination
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute("""ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN
                  ('emergency','risk','contingency','anomaly','queue_delay','call_back'))""")


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
