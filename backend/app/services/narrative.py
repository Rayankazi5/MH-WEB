import json
import re
from datetime import date, timedelta
from typing import Optional

SYSTEM_PROMPT = """You are a clinical documentation assistant supporting a licensed mental health clinician.
Your role is to summarise one week of a patient's behavioral and self-report data into a structured History of Present Illness (HPI) format.

STRICT RULES:
1. Output ONLY a JSON object with a single key "bullets" containing an array of 5-6 strings.
2. Each bullet must begin with a clinical domain label in brackets: [Sleep], [Mood], [Anxiety], [Cognition], [Social], [Behaviour].
3. Write in neutral, third-person clinical language. No diagnosis. No prediction. Use phrases like "Patient reported...", "Data indicates...", "Clinician attention advised..."
4. Do NOT reproduce any raw journal text verbatim.
5. Do NOT include any disclaimers, preambles, or keys other than "bullets".
6. If data for a domain is insufficient, write: "[Domain] Insufficient data this week."
7. Flag abstained sessions explicitly: "Scoring withheld for N sessions due to data quality."

OUTPUT FORMAT (strict JSON, no markdown):
{"bullets": ["[Sleep] ...", "[Mood] ...", "[Anxiety] ...", "[Cognition] ...", "[Social] ...", "[Behaviour] ..."]}"""


def _build_user_prompt(ctx: dict) -> str:
    domain_lines = json.dumps(ctx["domain_scores"], indent=2)
    theme_lines = "\n".join(
        f'  - {k.replace("journal_", "").replace("_", " ").title()} cluster: {v:.2f} frequency'
        for k, v in ctx["journal_themes"].items()
    ) or "  None"
    flag_lines = "\n".join(
        f'  - [{f["severity"].upper()}] {f["flag_type"]}: {f["self_report_val"]} / {f["signal_val"]}'
        for f in ctx["dissonance_flags"]
    ) or "  None"
    avg_rt = ctx.get("avg_rt_ms")
    rt_note = f"{avg_rt:,}ms" if avg_rt else "N/A"

    return f"""Generate an HPI summary for the following patient data.

WEEK: {ctx["week_start"]} to {ctx["week_end"]}
SESSIONS COMPLETED: {ctx["completed"]} of {ctx["expected"]}
SESSIONS ABSTAINED: {ctx["abstained"]}

DOMAIN SCORES (0.0 = low concern, 1.0 = high concern):
{domain_lines}

JOURNAL THEMES (keyword clusters — not verbatim text):
{theme_lines}

DISSONANCE FLAGS THIS WEEK:
{flag_lines}

AVERAGE RESPONSE TIME: {rt_note}"""


def parse_narrative(raw: str) -> list[str]:
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        parsed = json.loads(cleaned)
        bullets = parsed.get("bullets", [])
        assert isinstance(bullets, list)
        assert 5 <= len(bullets) <= 6
        assert all(isinstance(b, str) and b.startswith("[") for b in bullets)
        return bullets
    except (json.JSONDecodeError, AssertionError):
        return ["[System] Narrative generation failed. Manual review required."]


def generate_narrative(ctx: dict) -> tuple[list[str], str]:
    try:
        import anthropic  # type: ignore
        from app.config import get_settings
        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(ctx)}],
        )
        raw = message.content[0].text
        return parse_narrative(raw), raw
    except ImportError:
        raw = '{"bullets": ["[System] Narrative service unavailable — anthropic package not installed."]}'
        return parse_narrative(raw), raw


def build_narrative_context(db, patient_id, week_start: date) -> Optional[dict]:
    from app.models.session import Session, QuestionnaireResponse
    from app.models.journal import JournalEntry
    from app.models.score import DomainScore
    from app.models.flag import DissonanceFlag

    week_end = week_start + timedelta(days=6)

    sessions = (
        db.query(Session)
        .filter(
            Session.patient_id == patient_id,
            Session.started_at >= week_start,
            Session.started_at <= week_end,
            Session.completed_at.isnot(None),
        )
        .all()
    )

    if not sessions:
        return None

    session_ids = [s.id for s in sessions]
    completed = sum(1 for s in sessions if not s.abstained)
    abstained = sum(1 for s in sessions if s.abstained)

    scores_rows = (
        db.query(DomainScore)
        .filter(DomainScore.session_id.in_(session_ids))
        .all()
    )

    domain_accumulator: dict[str, list[float]] = {}
    for row in scores_rows:
        domain_accumulator.setdefault(row.domain, []).append(row.score)

    from statistics import mean, stdev
    domain_scores = {}
    for domain, vals in domain_accumulator.items():
        prev_week_start = week_start - timedelta(days=7)
        prev_scores = (
            db.query(DomainScore)
            .filter(
                DomainScore.patient_id == patient_id,
                DomainScore.domain == domain,
                DomainScore.computed_at >= prev_week_start,
                DomainScore.computed_at < week_start,
            )
            .all()
        )
        prev_mean = mean(s.score for s in prev_scores) if prev_scores else None
        curr_mean = mean(vals)
        if prev_mean is None:
            trend = "insufficient data"
        elif curr_mean > prev_mean + 0.05:
            trend = "worsening"
        elif curr_mean < prev_mean - 0.05:
            trend = "improving"
        else:
            trend = "stable"
        domain_scores[domain] = {"mean": round(curr_mean, 3), "trend": trend}

    journals = (
        db.query(JournalEntry)
        .filter(JournalEntry.session_id.in_(session_ids))
        .all()
    )
    merged_keywords: dict[str, list[float]] = {}
    rt_values: list[int] = []
    for j in journals:
        if j.keyword_vector:
            for k, v in j.keyword_vector.items():
                merged_keywords.setdefault(k, []).append(v)
    journal_themes = {k: round(mean(v), 3) for k, v in merged_keywords.items()}

    flags = (
        db.query(DissonanceFlag)
        .filter(
            DissonanceFlag.session_id.in_(session_ids),
            DissonanceFlag.resolved.is_(None),
        )
        .all()
    )
    flag_list = [
        {"flag_type": f.flag_type, "self_report_val": f.self_report_val,
         "signal_val": f.signal_val, "severity": f.severity}
        for f in flags
    ]

    responses = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.session_id.in_(session_ids),
                QuestionnaireResponse.response_time_ms.isnot(None))
        .all()
    )
    avg_rt = int(mean(r.response_time_ms for r in responses)) if responses else None

    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "completed": completed,
        "expected": 7,
        "abstained": abstained,
        "domain_scores": domain_scores,
        "journal_themes": journal_themes,
        "dissonance_flags": flag_list,
        "avg_rt_ms": avg_rt,
    }
