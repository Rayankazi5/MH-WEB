"""
On-demand clinical report generator — assembles 4-week patient data and
calls Claude to produce a structured report for the clinician portal.
Falls back to rule-based generation when no API key is configured.
"""
from __future__ import annotations

import json
import re
from typing import Optional

REPORT_SYSTEM_PROMPT = """You are a clinical documentation assistant supporting a licensed mental health clinician.
Generate a structured clinical report based on a patient's behavioral tracking data.

STRICT RULES:
1. Output ONLY valid JSON with the exact keys specified below.
2. Write in neutral, third-person clinical language. No diagnosis. No prediction.
3. Use phrases like "Patient reported...", "Data indicates...", "Clinician attention recommended..."
4. Do NOT reproduce any raw journal text verbatim.
5. Do NOT include disclaimers, preambles, or extra keys.
6. Never name DSM diagnoses. Describe observable patterns only.
7. Session focus recommendations must be concrete, actionable, and tied directly to the data.

OUTPUT FORMAT (strict JSON, no markdown fences):
{
  "executive_summary": "2-3 sentence overview of patient status this period.",
  "domain_notes": {
    "sleep_quality": "One clinical sentence.",
    "mood_stability": "One clinical sentence.",
    "anxiety": "One clinical sentence.",
    "cognitive_fatigue": "One clinical sentence.",
    "social_withdrawal": "One clinical sentence."
  },
  "behavioral_highlights": ["Observation 1.", "Observation 2.", "Observation 3."],
  "journal_summary": "One sentence on journal theme patterns, or omit if no data.",
  "flags_summary": "One sentence on dissonance flags, or 'No active flags this period.'",
  "session_focus_recommendations": ["Recommendation 1.", "Recommendation 2.", "Recommendation 3."]
}"""

DOMAIN_LABELS = {
    "cognitive_fatigue": "Cognitive Fatigue / Energy",
    "social_withdrawal": "Social Withdrawal",
    "anxiety": "Anxiety",
    "mood_stability": "Mood Stability",
    "sleep_quality": "Sleep Quality",
}

_DOMAIN_THRESHOLDS = {
    "sleep_quality": ("adequate sleep patterns", "disrupted sleep patterns", "significantly disrupted sleep"),
    "mood_stability": ("relatively stable mood", "some mood variability", "notable mood instability"),
    "anxiety": ("manageable anxiety levels", "moderate anxiety indicators", "elevated anxiety indicators"),
    "cognitive_fatigue": ("good cognitive functioning", "moderate cognitive fatigue", "significant cognitive fatigue"),
    "social_withdrawal": ("healthy social engagement", "reduced social engagement", "marked social withdrawal"),
}


def _build_report_prompt(ctx: dict) -> str:
    domain_lines = json.dumps(ctx["domain_scores"], indent=2)

    theme_lines = "\n".join(
        f'  - {k.replace("journal_", "").replace("_", " ").title()}: {v:.2f} frequency'
        for k, v in ctx.get("journal_themes", {}).items()
    ) or "  No journal data available"

    flag_lines = "\n".join(
        f'  - [{f["severity"].upper()}] {f["flag_type"]}: self-report={f["self_report_val"]} / signal={f["signal_val"]}'
        for f in ctx.get("open_flags", [])
    ) or "  No active flags"

    protective_lines = "\n".join(
        f'  - {f["label"]}: {f["value"]} (strength: {f["strength"]})'
        for f in ctx.get("protective_factors", [])
    ) or "  No data"

    questionnaire_lines = "\n".join(
        f'  - {r["question_text"]}: {r["answer_label"]}'
        for r in ctx.get("notable_responses", [])
    ) or "  No non-zero PHQ responses"

    avg_rt = ctx.get("avg_rt_ms")
    rt_note = f"{avg_rt:,}ms" if avg_rt else "N/A"
    adherence = ctx.get("adherence", {})

    return f"""Generate a clinical report for the following patient data.

REPORT PERIOD: {ctx["period_start"]} to {ctx["period_end"]}
SESSIONS COMPLETED: {adherence.get("completed", 0)} (abstained: {adherence.get("abstained", 0)})
AVERAGE RESPONSE TIME: {rt_note}

DOMAIN SCORES (0.0 = low concern, 1.0 = high concern, includes trend vs previous period):
{domain_lines}

PROTECTIVE FACTORS (from most recent session):
{protective_lines}

JOURNAL THEMES (keyword clusters — not verbatim text):
{theme_lines}
JOURNAL SENTIMENT (avg, 0=positive 1=negative): {ctx.get("avg_sentiment", "N/A")}

OPEN DISSONANCE FLAGS:
{flag_lines}

NOTABLE QUESTIONNAIRE RESPONSES (non-zero PHQ items, most recent scored session):
{questionnaire_lines}"""


def _rule_based_report(ctx: dict) -> dict:
    domain_scores = ctx.get("domain_scores", {})

    def score_note(domain: str) -> str:
        info = domain_scores.get(domain, {})
        score = info.get("mean", 0.0)
        trend = info.get("trend", "insufficient data")
        labels = _DOMAIN_THRESHOLDS.get(domain, ("within normal range", "some concern", "significant concern"))
        desc = labels[0] if score < 0.35 else (labels[1] if score < 0.6 else labels[2])
        return f"Patient demonstrates {desc} (score {score:.2f}, trend: {trend})."

    domains_present = [d for d in DOMAIN_LABELS if d in domain_scores]
    high_concern = [(d, domain_scores[d]["mean"]) for d in domains_present if domain_scores[d]["mean"] >= 0.55]
    high_concern.sort(key=lambda x: -x[1])

    if not domains_present:
        summary = (
            "Insufficient data is available for this reporting period. "
            "The patient has not completed enough check-ins to generate meaningful trends."
        )
    elif high_concern:
        areas = ", ".join(DOMAIN_LABELS.get(d, d) for d, _ in high_concern[:2])
        summary = (
            f"Patient data over the reporting period indicates elevated concern in {areas}. "
            "Clinician review of these domains is recommended. "
            "Overall check-in adherence and engagement should also be assessed."
        )
    else:
        summary = (
            "Patient data over the reporting period reflects generally manageable levels "
            "across all tracked domains. Continued monitoring is recommended to confirm stability."
        )

    open_flags = ctx.get("open_flags", [])
    flags_summary = (
        f"{len(open_flags)} active dissonance flag(s) require clinician review: "
        + ", ".join(f["flag_type"] for f in open_flags[:3]) + "."
        if open_flags
        else "No active dissonance flags recorded during this period."
    )

    themes = ctx.get("journal_themes", {})
    journal_summary = (
        "Journal entries reflect themes of "
        + ", ".join(k.replace("journal_", "").replace("_", " ") for k in list(themes.keys())[:3])
        + "."
        if themes
        else "No journal entries recorded during this period."
    )

    recs = []
    for domain, _ in high_concern[:2]:
        label = DOMAIN_LABELS.get(domain, domain)
        recs.append(f"Explore {label.lower()} patterns in session; data indicates elevated concern in this area.")
    if len(recs) < 2:
        recs.append("Continue monitoring current patterns and reinforce adaptive behaviours identified to date.")
    recs.append(
        "Review any open dissonance flags and explore discrepancies between self-report and behavioural signals."
    )
    recs.append(
        "Encourage consistent daily check-in completion to improve data resolution for future reporting periods."
    )

    protective = ctx.get("protective_factors", [])
    behavioral_highlights = [
        f"{f['label']}: {f['value']} ({f['strength']} indicator)."
        for f in protective[:4]
    ]
    if not behavioral_highlights:
        behavioral_highlights = ["No protective factor data available from recent sessions."]

    return {
        "executive_summary": summary,
        "domain_notes": {d: score_note(d) for d in DOMAIN_LABELS},
        "behavioral_highlights": behavioral_highlights,
        "journal_summary": journal_summary,
        "flags_summary": flags_summary,
        "session_focus_recommendations": recs[:4],
    }


def generate_report(ctx: dict) -> dict:
    try:
        from app.config import get_settings
        settings = get_settings()
        if not settings.anthropic_api_key:
            return _rule_based_report(ctx)

        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0.2,
            system=REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_report_prompt(ctx)}],
        )
        raw = message.content[0].text.strip()
        cleaned = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(cleaned)
        required = {
            "executive_summary", "domain_notes", "behavioral_highlights",
            "journal_summary", "flags_summary", "session_focus_recommendations",
        }
        if not required.issubset(parsed.keys()):
            return _rule_based_report(ctx)
        return parsed
    except Exception:
        return _rule_based_report(ctx)


def build_report_context(db, patient_id, weeks: int = 4) -> dict:
    from datetime import datetime, timedelta
    from statistics import mean
    from app.models.session import Session as CheckInSession, QuestionnaireResponse
    from app.models.journal import JournalEntry
    from app.models.score import DomainScore
    from app.models.flag import DissonanceFlag
    from app.engine.questions import QUESTION_BANK

    now = datetime.utcnow()
    cutoff = now - timedelta(weeks=weeks)
    prev_cutoff = cutoff - timedelta(weeks=weeks)

    sessions = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == patient_id,
            CheckInSession.started_at >= cutoff,
            CheckInSession.completed_at.isnot(None),
        )
        .all()
    )
    completed = sum(1 for s in sessions if not s.abstained)
    abstained = sum(1 for s in sessions if s.abstained)

    score_rows = (
        db.query(DomainScore)
        .filter(DomainScore.patient_id == patient_id, DomainScore.computed_at >= cutoff)
        .all()
    )
    domain_accumulator: dict = {}
    for row in score_rows:
        domain_accumulator.setdefault(row.domain, []).append(row.score)

    domain_scores: dict = {}
    for domain, vals in domain_accumulator.items():
        prev_rows = (
            db.query(DomainScore)
            .filter(
                DomainScore.patient_id == patient_id,
                DomainScore.domain == domain,
                DomainScore.computed_at >= prev_cutoff,
                DomainScore.computed_at < cutoff,
            )
            .all()
        )
        prev_mean = mean(r.score for r in prev_rows) if prev_rows else None
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
        .filter(JournalEntry.patient_id == patient_id, JournalEntry.created_at >= cutoff)
        .all()
    )
    merged_keywords: dict = {}
    sentiments = []
    for j in journals:
        if j.keyword_vector:
            for k, v in j.keyword_vector.items():
                merged_keywords.setdefault(k, []).append(v)
        if j.sentiment_score is not None:
            sentiments.append(j.sentiment_score)
    journal_themes = {k: round(mean(v), 3) for k, v in merged_keywords.items()}
    avg_sentiment = round(mean(sentiments), 3) if sentiments else None

    open_flags_rows = (
        db.query(DissonanceFlag)
        .filter(DissonanceFlag.patient_id == patient_id, DissonanceFlag.resolved.is_(None))
        .order_by(DissonanceFlag.created_at.desc())
        .all()
    )
    open_flags = [
        {
            "flag_type": f.flag_type,
            "self_report_val": f.self_report_val,
            "signal_val": f.signal_val,
            "severity": f.severity,
        }
        for f in open_flags_rows
    ]

    latest_session = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == patient_id,
            CheckInSession.completed_at.isnot(None),
            CheckInSession.abstained == False,
        )
        .order_by(CheckInSession.completed_at.desc())
        .first()
    )

    protective_factors = []
    notable_responses = []
    avg_rt = None

    if latest_session:
        responses = (
            db.query(QuestionnaireResponse)
            .filter(QuestionnaireResponse.session_id == latest_session.id)
            .all()
        )
        response_map = {r.question_key: r.raw_value for r in responses}

        def cal_count(key: str):
            val = response_map.get(key)
            if val is None:
                return None
            return len(val) if isinstance(val, list) else int(val)

        sleep_days = cal_count("indirect_sleep_days")
        social_days = cal_count("indirect_social_days")
        productive_days = cal_count("indirect_productive_days")
        sleep_hours_raw = response_map.get("sleep_hours")
        sleep_hours = float(sleep_hours_raw) if sleep_hours_raw is not None else None

        if sleep_days is not None:
            strength = "strong" if sleep_days >= 5 else "moderate" if sleep_days >= 3 else "low"
            protective_factors.append({"label": "Good sleep nights", "value": f"{sleep_days}/7", "strength": strength})
        if sleep_hours is not None:
            strength = "strong" if sleep_hours >= 7 else "moderate" if sleep_hours >= 5.5 else "low"
            protective_factors.append({"label": "Avg. sleep duration", "value": f"{sleep_hours:.1f} hrs/night", "strength": strength})
        if social_days is not None:
            strength = "strong" if social_days >= 4 else "moderate" if social_days >= 2 else "low"
            protective_factors.append({"label": "Social engagement", "value": f"{social_days}/7 days", "strength": strength})
        if productive_days is not None:
            strength = "strong" if productive_days >= 4 else "moderate" if productive_days >= 2 else "low"
            protective_factors.append({"label": "Productive days", "value": f"{productive_days}/7 days", "strength": strength})

        PHQ_LABELS = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        question_map = {q["key"]: q for q in QUESTION_BANK}

        for r in responses:
            if r.question_type == "phq9":
                try:
                    idx = int(r.raw_value)
                    if idx >= 1:
                        q_info = question_map.get(r.question_key, {})
                        notable_responses.append({
                            "question_text": q_info.get("text", r.question_key),
                            "answer_label": PHQ_LABELS[idx],
                        })
                except (ValueError, TypeError, IndexError):
                    pass

        rt_vals = [r.response_time_ms for r in responses if r.response_time_ms is not None]
        if rt_vals:
            avg_rt = int(mean(rt_vals))

    return {
        "period_start": cutoff.strftime("%Y-%m-%d"),
        "period_end": now.strftime("%Y-%m-%d"),
        "adherence": {"completed": completed, "abstained": abstained},
        "domain_scores": domain_scores,
        "journal_themes": journal_themes,
        "avg_sentiment": avg_sentiment,
        "open_flags": open_flags,
        "protective_factors": protective_factors,
        "notable_responses": notable_responses,
        "avg_rt_ms": avg_rt,
    }
