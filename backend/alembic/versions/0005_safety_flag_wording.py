"""Rewrite older safety flags ("Endorsed: ref_self_harm, ...") into clinician wording.

New flags read e.g. "Thoughts of hurting someone else: Several days". Older ones listed raw
question keys. The answer is filled in from the saved response when it still endorses the
item; any "(answer later changed …)" / "(check-in deleted …)" note is preserved.

Revision ID: 0005
Revises: 0004
"""
import re

import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

LABELS = {
    "ref_self_harm": "Feelings of wanting to harm themself",
    "ref_thoughts_harm_others": "Thoughts of hurting someone else",
    "ref_hopelessness": "Feelings of hopelessness",
    "phq_9": "Thoughts of being better off dead or of self-harm (retired PHQ-9 item 9)",
}
ANSWERS = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
SIGNAL = {"ref_self_harm": "thoughts of self-harm", "ref_thoughts_harm_others": "thoughts of harming others",
          "ref_hopelessness": "hopelessness", "phq_9": "thoughts of self-harm (PHQ-9 item 9)"}


def upgrade() -> None:
    conn = op.get_bind()
    flags = conn.execute(sa.text(
        "SELECT id, session_id, self_report_val FROM dissonance_flags "
        "WHERE flag_type = 'self_reported_safety_concern' AND self_report_val LIKE 'Endorsed:%'"
    )).all()
    for flag_id, session_id, text in flags:
        m = re.match(r"Endorsed:\s*([a-z0-9_,\s]+?)(\s*\(.*\))?$", text or "")
        if not m:
            continue
        keys = [k.strip() for k in m.group(1).split(",") if k.strip() in LABELS]
        if not keys:
            continue
        note = (m.group(2) or "").strip()
        answers = dict(conn.execute(sa.text(
            "SELECT question_key, raw_value FROM questionnaire_responses WHERE session_id = :s AND question_key = ANY(:k)"
        ), {"s": session_id, "k": keys}).all())
        parts = []
        for k in keys:
            try:
                v = int(answers.get(k) or 0)
            except (TypeError, ValueError):
                v = 0
            parts.append(f"{LABELS[k]}: {ANSWERS[min(v, 3)]}" if v > 0 else LABELS[k])
        new = "; ".join(parts) + (f" {note}" if note else "")
        signal = "Patient self-reported " + " and ".join(SIGNAL[k] for k in keys)
        conn.execute(sa.text("UPDATE dissonance_flags SET self_report_val = :t, signal_val = :g WHERE id = :i"),
                     {"t": new, "g": signal, "i": flag_id})


def downgrade() -> None:
    pass  # wording-only change
