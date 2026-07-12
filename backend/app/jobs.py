from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def _weekly_narrative_job() -> None:
    from app.database import SessionLocal
    from app.models.user import User, ROLE_PATIENT
    from app.models.link import ClinicianPatient
    from app.models.narrative import Narrative
    from app.services.narrative import build_narrative_context, generate_narrative

    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week

    db = SessionLocal()
    try:
        # Only run for patients who have at least one active clinician link
        linked_patient_ids = (
            db.query(ClinicianPatient.patient_id)
            .filter(ClinicianPatient.active == True)
            .distinct()
            .all()
        )
        patient_ids = [row[0] for row in linked_patient_ids]

        for patient_id in patient_ids:
            # Skip if narrative already generated for this week
            exists = (
                db.query(Narrative)
                .filter(Narrative.patient_id == patient_id, Narrative.week_start == week_start)
                .first()
            )
            if exists:
                continue

            ctx = build_narrative_context(db, patient_id, week_start)
            if not ctx:
                continue

            bullets, raw_output = generate_narrative(ctx)
            db.add(Narrative(
                patient_id=patient_id,
                week_start=week_start,
                bullets=bullets,
                raw_llm_output=raw_output,
            ))
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start_scheduler() -> None:
    # Monday 06:00 UTC — narratives ready before clinic sessions
    scheduler.add_job(_weekly_narrative_job, "cron", day_of_week="mon", hour=6, minute=0)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
