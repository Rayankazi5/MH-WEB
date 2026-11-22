import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_patient
from app.database import get_db
from app.engine.questions import ANSWERABLE, generate_questions, validate_answer
from app.engine.scoring import run_scoring_pipeline
from app.engine.stages import determine_stage
from app.engine.profiles import PROFILE_KEYS
from app.models.flag import DissonanceFlag
from app.models.journal import JournalEntry
from app.models.score import DomainScore
from app.models.session import Session as CheckInSession, QuestionnaireResponse
from app.models.user import User
from app.schemas.patient import InsightRequest, JournalEditRequest, JournalSubmitRequest
from app.schemas.session import RespondRequest, SessionStartResponse, SessionStatusResponse
from app.services.encryption import encrypt
from app.services.insight_chat import KEYWORD_CONFIG, run_insight_chat
from app.services.nlp import process_journal

router = APIRouter(prefix="/patient", tags=["patient"])


@router.post("/session/start", response_model=SessionStartResponse)
def start_session(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    # Lock this patient's row so simultaneous "start" requests can't each create a check-in;
    # the lock is held until this request's transaction ends.
    db.query(User).filter(User.id == current_user.id).with_for_update().one()

    # Consult the reference questionnaire for this patient's stage before generating questions.
    # The stage comes from the last completed check-in, so it is stable while a session is open.
    stage = determine_stage(db, current_user.id)

    # Return existing active (uncompleted) session if present, with the questions it was started
    # with and any answers already saved
    active = (
        db.query(CheckInSession)
        .filter(CheckInSession.patient_id == current_user.id, CheckInSession.completed_at.is_(None),
                CheckInSession.deleted_at.is_(None))
        .order_by(CheckInSession.started_at)
        .first()
    )
    if active:
        if not active.question_keys:  # started before question_keys existed
            active.question_keys = [q["key"] for q in generate_questions(stage)]
            db.commit()
        return SessionStartResponse(
            session_id=active.id, stage=stage,
            questions=_session_questions(active), answers=_saved_answers(db, active.id),
        )

    # Block a second completed session on the same calendar day (UTC)
    today_start = datetime.combine(date.today(), datetime.min.time())
    done_today = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == current_user.id,
            CheckInSession.completed_at >= today_start,
            CheckInSession.deleted_at.is_(None),
        )
        .first()
    )
    if done_today:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_completed_today")

    questions = generate_questions(stage)
    session = CheckInSession(
        patient_id=current_user.id, device_type="web", question_keys=[q["key"] for q in questions],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionStartResponse(session_id=session.id, stage=stage, questions=questions)


def _session_questions(session: CheckInSession) -> list[dict]:
    return [
        {f: ANSWERABLE[k][f] for f in ("key", "type", "text", "scale")}
        for k in (session.question_keys or []) if k in ANSWERABLE
    ]


def _saved_answers(db: Session, session_id) -> dict:
    from app.services.encryption import decrypt
    out = {}
    for r in db.query(QuestionnaireResponse).filter(QuestionnaireResponse.session_id == session_id).all():
        if r.question_type == "text":
            try:
                out[r.question_key] = decrypt(r.raw_value)
            except Exception:
                out[r.question_key] = ""
        else:
            out[r.question_key] = r.raw_value
    return out


@router.post("/session/{session_id}/reset", status_code=status.HTTP_200_OK)
def reset_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """Re-open a completed session so the patient can review and change their answers.

    The check-in reopens on the review screen with its answers. Its scores and flags stay in
    place (shown as the last submitted result) until it is submitted again.
    """
    session = (
        db.query(CheckInSession)
        .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Clear completion state
    session.completed_at = None
    session.abstained = False

    # Answers, scores and flags are all kept: until the patient resubmits, every screen keeps
    # showing the last submitted result. Resubmitting replaces the scores and non-safety flags;
    # safety flags are never removed by an edit (see run_scoring_pipeline).

    db.commit()
    return {"session_id": str(session_id), "status": "reset"}


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    session = (
        db.query(CheckInSession)
        .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # A check-in with a safety flag is hidden from the patient but kept, with its answers and
    # safety flags, so the clinician still sees what was reported. Anything else is deleted.
    from app.engine.profiles import SAFETY_FLAG_TYPES
    from app.engine.scoring import DELETED_NOTE
    safety_flags = (
        db.query(DissonanceFlag)
        .filter(DissonanceFlag.session_id == session_id, DissonanceFlag.flag_type.in_(SAFETY_FLAG_TYPES))
        .all()
    )
    if not safety_flags:
        db.delete(session)
        db.commit()
        return

    session.deleted_at = datetime.utcnow()
    db.query(DomainScore).filter(DomainScore.session_id == session_id).delete(synchronize_session=False)
    db.query(DissonanceFlag).filter(
        DissonanceFlag.session_id == session_id, DissonanceFlag.flag_type.notin_(SAFETY_FLAG_TYPES),
    ).delete(synchronize_session=False)
    for f in safety_flags:
        if DELETED_NOTE not in (f.self_report_val or ""):
            f.self_report_val = f"{f.self_report_val} {DELETED_NOTE}"
    db.commit()


@router.post("/session/{session_id}/respond", status_code=status.HTTP_200_OK)
def respond(
    session_id: uuid.UUID,
    payload: RespondRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    session = (
        db.query(CheckInSession)
        .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.completed_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already completed")

    # Validate question key — must be one of the questions this check-in asked
    if payload.question_key not in ANSWERABLE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown question key")
    if session.question_keys and payload.question_key not in session.question_keys:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Question not part of this check-in")

    # Upsert — allow re-answering before completion
    existing = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.session_id == session_id,
            QuestionnaireResponse.question_key == payload.question_key,
        )
        .first()
    )
    question_meta = ANSWERABLE[payload.question_key]

    raw_value, problem = validate_answer(question_meta, payload.raw_value)
    if problem:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problem)
    if question_meta["type"] == "text":
        # Free-text answers are as sensitive as journals — store encrypted.
        raw_value = encrypt(raw_value)

    if existing:
        existing.raw_value = raw_value
        existing.response_time_ms = payload.response_time_ms
        existing.answered_at = datetime.utcnow()
    else:
        db.add(QuestionnaireResponse(
            session_id=session_id,
            question_key=payload.question_key,
            question_type=question_meta["type"],
            raw_value=raw_value,
            response_time_ms=payload.response_time_ms,
        ))

    db.commit()
    return {"status": "recorded"}


@router.post("/session/{session_id}/complete")
def complete_session(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    session = (
        db.query(CheckInSession)
        .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.completed_at:
        return {"status": "abstained" if session.abstained else "scored"}

    # Every question except the optional free-text ones must be answered before submitting
    if session.question_keys:
        answered = {
            k for (k,) in db.query(QuestionnaireResponse.question_key)
            .filter(QuestionnaireResponse.session_id == session_id).all()
        }
        missing = [
            k for k in session.question_keys
            if k in ANSWERABLE and ANSWERABLE[k]["type"] != "text" and k not in answered
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Please answer every question before submitting", "missing": missing},
            )

    session.completed_at = datetime.utcnow()
    db.commit()

    background_tasks.add_task(run_scoring_pipeline, str(session_id))
    return {"status": "scoring"}


@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(JournalEntry)
        .filter(JournalEntry.id == entry_id, JournalEntry.patient_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    db.delete(entry)
    db.commit()


@router.patch("/journal/{entry_id}", status_code=status.HTTP_200_OK)
def edit_journal(
    entry_id: uuid.UUID,
    payload: JournalEditRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    from app.services.encryption import encrypt
    entry = (
        db.query(JournalEntry)
        .filter(JournalEntry.id == entry_id, JournalEntry.patient_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    keyword_vector, sentiment_score, word_count = process_journal(payload.body)
    entry.body_encrypted = encrypt(payload.body)
    entry.keyword_vector = keyword_vector or None
    entry.sentiment_score = sentiment_score
    entry.word_count = word_count
    db.commit()
    return {"status": "updated", "word_count": word_count}


@router.get("/journals")
def list_journals(
    limit: int = Query(20, ge=1, le=100),
    source: str = Query(None),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    from app.services.encryption import decrypt
    from typing import Optional
    q = db.query(JournalEntry).filter(JournalEntry.patient_id == current_user.id)
    if source in ("chat", "solo"):
        q = q.filter(JournalEntry.source == source)
    entries = q.order_by(JournalEntry.created_at.desc()).limit(limit).all()
    result = []
    for e in entries:
        try:
            body = decrypt(e.body_encrypted)
        except Exception:
            body = ""
        result.append({
            "id": str(e.id),
            "body": body,
            "word_count": e.word_count,
            "sentiment_score": e.sentiment_score,
            "source": e.source,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return result


@router.post("/journal", status_code=status.HTTP_201_CREATED)
def submit_journal(
    payload: JournalSubmitRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    session_id = payload.session_id
    if session_id is not None:
        session = (
            db.query(CheckInSession)
            .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
            .first()
        )
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    keyword_vector, sentiment_score, word_count = process_journal(payload.body)
    body_encrypted = encrypt(payload.body)

    entry = JournalEntry(
        session_id=session_id,
        patient_id=current_user.id,
        body_encrypted=body_encrypted,
        keyword_vector=keyword_vector or None,
        sentiment_score=sentiment_score,
        word_count=word_count,
        source=payload.source,
    )
    db.add(entry)
    db.commit()
    return {"status": "saved", "word_count": word_count}


@router.get("/sessions")
def list_sessions(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(CheckInSession)
        .filter(CheckInSession.patient_id == current_user.id, CheckInSession.deleted_at.is_(None))
        .order_by(CheckInSession.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "session_id": str(s.id),
            "started_at": s.started_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "status": "abstained" if s.abstained else ("done" if s.completed_at else "in_progress"),
        }
        for s in sessions
    ]


@router.get("/wellbeing")
def wellbeing(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """The patient's S1–S4 badge. At risk (any unresolved safety flag) is always S2."""
    from app.engine.profiles import patient_badge
    return patient_badge(db, current_user.id)


@router.get("/history")
def history(
    weeks: int = Query(2, ge=1, le=52),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(weeks=weeks)
    scores = (
        db.query(DomainScore)
        .filter(DomainScore.patient_id == current_user.id, DomainScore.computed_at >= cutoff,
                DomainScore.domain.in_(PROFILE_KEYS))
        .order_by(DomainScore.computed_at)
        .all()
    )
    return [
        {"domain": s.domain, "score": s.score, "confidence": s.confidence, "date": s.computed_at.isoformat()}
        for s in scores
    ]


@router.post("/insights")
def patient_insights(
    payload: InsightRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """Guardrailed insight chat — returns a data-grounded 3-4 sentence response."""
    from app.engine.scoring import extract_indicators, compute_all_domains, load_weights
    from datetime import timedelta

    # Validate keyword
    valid_keywords = set(KEYWORD_CONFIG.keys())
    keyword = payload.keyword
    if keyword and keyword not in valid_keywords:
        raise HTTPException(status_code=422, detail=f"keyword must be one of: {', '.join(valid_keywords)}")
    if not keyword and not payload.free_text:
        raise HTTPException(status_code=422, detail="Provide keyword or free_text")

    # Pull latest completed session's responses for live indicators
    latest_session = (
        db.query(CheckInSession)
        .filter(
            CheckInSession.patient_id == current_user.id,
            CheckInSession.completed_at.isnot(None),
            CheckInSession.abstained == False,
            CheckInSession.deleted_at.is_(None),
        )
        .order_by(CheckInSession.completed_at.desc())
        .first()
    )

    raw_indicators: dict = {}
    if latest_session:
        responses = (
            db.query(QuestionnaireResponse)
            .filter(QuestionnaireResponse.session_id == latest_session.id)
            .all()
        )
        # Pass raw values to insight chat so descriptions show real hours/days, not normalised scores
        for r in responses:
            raw_indicators[r.question_key] = r.raw_value

    # Pull recent domain scores (last 4 weeks)
    cutoff = datetime.utcnow() - timedelta(weeks=4)
    score_rows = (
        db.query(DomainScore)
        .filter(
            DomainScore.patient_id == current_user.id,
            DomainScore.computed_at >= cutoff,
            DomainScore.domain.in_(PROFILE_KEYS),
        )
        .order_by(DomainScore.computed_at.desc())
        .all()
    )

    # Average per domain
    domain_accumulator: dict = {}
    for row in score_rows:
        domain_accumulator.setdefault(row.domain, []).append(row.score)
    domain_scores = {d: sum(v) / len(v) for d, v in domain_accumulator.items()}

    # Compute trend vs previous 4-week window
    trend = None
    if domain_scores and keyword and keyword != "overall":
        from app.services.insight_chat import KEYWORD_CONFIG as KC
        target_domains = KC.get(keyword, {}).get("domains", [])
        if target_domains:
            prev_cutoff = cutoff - timedelta(weeks=4)
            prev_rows = (
                db.query(DomainScore)
                .filter(
                    DomainScore.patient_id == current_user.id,
                    DomainScore.domain.in_(target_domains),
                    DomainScore.computed_at >= prev_cutoff,
                    DomainScore.computed_at < cutoff,
                )
                .all()
            )
            if prev_rows:
                prev_mean = sum(r.score for r in prev_rows) / len(prev_rows)
                curr_mean = sum(domain_scores.get(d, 0) for d in target_domains) / len(target_domains)
                if curr_mean > prev_mean + 0.05:
                    trend = "showing more strain than last period"
                elif curr_mean < prev_mean - 0.05:
                    trend = "improving compared to last period"
                else:
                    trend = "staying fairly stable"

    from app.engine.profiles import latest_checkin, safety_reasons
    latest_any = latest_checkin(db, current_user.id)
    reasons = safety_reasons(db, latest_any) if latest_any is not None else []
    response_text = run_insight_chat(keyword, payload.free_text, domain_scores, raw_indicators, trend,
                                     safety_reasons=reasons)
    return {"response": response_text, "keyword": keyword}


@router.get("/session/{session_id}/status", response_model=SessionStatusResponse)
def session_status(
    session_id: uuid.UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    session = (
        db.query(CheckInSession)
        .filter(CheckInSession.id == session_id, CheckInSession.patient_id == current_user.id,
                CheckInSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if not session.completed_at:
        return SessionStatusResponse(status="in_progress")
    if session.abstained:
        return SessionStatusResponse(status="abstained")

    domain_scores = (
        db.query(DomainScore)
        .filter(DomainScore.session_id == session_id)
        .all()
    )
    if not domain_scores:
        return SessionStatusResponse(status="scoring")

    return SessionStatusResponse(
        status="scored",
        domains=[
            {"domain": s.domain, "score": s.score, "confidence": s.confidence}
            for s in domain_scores
        ],
    )
