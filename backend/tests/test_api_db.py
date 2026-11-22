"""
Database-backed API tests: check-in validation, scoring, the Edit flow and
safety-flag retention, run end to end against the Postgres test database.
"""
from __future__ import annotations

import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

API = "/api/v1"
PASSWORD = "TestPass123!"


# ── helpers ───────────────────────────────────────────────────────────────────

def make_user(client, role="patient"):
    email = f"{role}.{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "role": role, "full_name": f"Test {role}"})
    assert r.status_code == 201, r.text
    token = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"email": email, "headers": {"Authorization": f"Bearer {token}"},
            "id": client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]}


def start(client, user):
    r = client.post(f"{API}/patient/session/start", headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, user, sid, key, value, rt=1800):
    return client.post(f"{API}/patient/session/{sid}/respond", headers=user["headers"],
                       json={"question_key": key, "raw_value": value, "response_time_ms": rt})


def default_value(q):
    return {"likert": 0, "numeric": 8 if q["key"] == "sleep_hours" else 3, "text": ""}[q["type"]]


def answer_all(client, user, session, overrides=None):
    overrides = overrides or {}
    for q in session["questions"]:
        r = answer(client, user, session["session_id"], q["key"], overrides.get(q["key"], default_value(q)))
        assert r.status_code == 200, (q["key"], r.text)


def submit(client, user, sid):
    return client.post(f"{API}/patient/session/{sid}/complete", headers=user["headers"])


def edit(client, user, sid):
    r = client.post(f"{API}/patient/session/{sid}/reset", headers=user["headers"])
    assert r.status_code == 200, r.text


def status_of(client, user, sid):
    return client.get(f"{API}/patient/session/{sid}/status", headers=user["headers"]).json()["status"]


def flags(db, sid):
    db.expire_all()
    rows = db.execute(text("SELECT flag_type, self_report_val FROM dissonance_flags WHERE session_id = :s ORDER BY flag_type"),
                      {"s": sid}).all()
    return {r.flag_type: r.self_report_val for r in rows}


def patient_type(db, user):
    from app.engine.profiles import classify_latest
    db.expire_all()
    return classify_latest(db, uuid.UUID(user["id"]))


def move_to_yesterday(db, sid):
    db.execute(text("UPDATE sessions SET started_at = started_at - interval '1 day', "
                    "completed_at = completed_at - interval '1 day' WHERE id = :s"), {"s": sid})
    db.commit()


def full_checkin(client, user, overrides=None):
    s = start(client, user)
    answer_all(client, user, s, overrides)
    r = submit(client, user, s["session_id"])
    assert r.status_code == 200, r.text
    return s


# ── Edit (reset) keeps answers; safety flags are retained ────────────────────

class TestEditFlow:
    def test_edit_keeps_answers_and_reopens_same_checkin(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_flashbacks": 3, "subj_mind": "kept text"})
        assert status_of(client, p, s["session_id"]) == "scored"

        edit(client, p, s["session_id"])
        s2 = start(client, p)
        assert s2["session_id"] == s["session_id"]
        assert len(s2["answers"]) == len(s2["questions"])
        assert s2["answers"]["ref_flashbacks"] == 3
        assert s2["answers"]["subj_mind"] == "kept text"
        assert status_of(client, p, s["session_id"]) == "in_progress"

    def test_edit_then_change_answer_rescores(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_flashbacks": 3, "ref_thoughts_scary": 3})
        assert patient_type(db_session, p)["primary"] == "trauma"

        edit(client, p, s["session_id"])
        t = patient_type(db_session, p)  # last submitted result stays visible while editing
        assert t["primary"] == "trauma" and t["being_edited"]
        answer(client, p, s["session_id"], "ref_flashbacks", 0)
        answer(client, p, s["session_id"], "ref_thoughts_scary", 0)
        assert submit(client, p, s["session_id"]).status_code == 200
        t = patient_type(db_session, p)
        assert t["primary"] == "low_concern" and not t["being_edited"]
        n = db_session.execute(text("SELECT count(*) FROM domain_scores WHERE session_id = :s"), {"s": s["session_id"]}).scalar()
        assert n == 5  # replaced, not duplicated

    def test_safety_flag_kept_and_annotated_when_edited_away(self, client, db_session):
        from app.engine.scoring import EDITED_NOTE
        p = make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 1})
        sid = s["session_id"]
        assert "self_reported_safety_concern" in flags(db_session, sid)

        edit(client, p, sid)
        assert "self_reported_safety_concern" in flags(db_session, sid)  # survives the Edit itself
        answer(client, p, sid, "ref_self_harm", 0)
        submit(client, p, sid)

        f = flags(db_session, sid)
        assert list(f) == ["self_reported_safety_concern"]
        assert EDITED_NOTE in f["self_reported_safety_concern"]
        t = patient_type(db_session, p)
        assert t["at_risk"] and "edited_safety_answer" in t["safety_items"]

        # Editing again doesn't repeat the note
        edit(client, p, sid)
        submit(client, p, sid)
        assert flags(db_session, sid)["self_reported_safety_concern"].count(EDITED_NOTE) == 1

        # And the next day is still the crisis set
        move_to_yesterday(db_session, sid)
        assert start(client, p)["stage"] == "crisis"

    def test_edit_without_changes_does_not_duplicate_or_annotate(self, client, db_session):
        from app.engine.scoring import EDITED_NOTE
        p = make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 2, "meals_per_day": 1})
        before = flags(db_session, s["session_id"])
        edit(client, p, s["session_id"])
        submit(client, p, s["session_id"])
        after = flags(db_session, s["session_id"])
        assert after == before
        assert EDITED_NOTE not in after["self_reported_safety_concern"]
        n = db_session.execute(text("SELECT count(*) FROM dissonance_flags WHERE session_id = :s"), {"s": s["session_id"]}).scalar()
        assert n == len(before)

    def test_non_safety_flags_are_recalculated(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"meals_per_day": 1})
        assert "low_meal_intake" in flags(db_session, s["session_id"])
        edit(client, p, s["session_id"])
        assert "low_meal_intake" in flags(db_session, s["session_id"])  # last result kept while editing
        answer(client, p, s["session_id"], "meals_per_day", 3)
        submit(client, p, s["session_id"])
        assert "low_meal_intake" not in flags(db_session, s["session_id"])

    def test_free_text_risk_flag_survives_edit(self, client, db_session):
        from app.engine.scoring import EDITED_NOTE
        p = make_user(client)
        s = full_checkin(client, p, {"subj_mind": "I want to end my life"})
        sid = s["session_id"]
        assert "free_text_risk_language" in flags(db_session, sid)
        assert patient_type(db_session, p)["at_risk"]

        edit(client, p, sid)
        answer(client, p, sid, "subj_mind", "Actually I'm fine")
        submit(client, p, sid)
        f = flags(db_session, sid)
        assert EDITED_NOTE in f["free_text_risk_language"]
        assert patient_type(db_session, p)["at_risk"]


# ── Answer validation ─────────────────────────────────────────────────────────

class TestValidation:
    @pytest.mark.parametrize("key,value", [
        ("ref_thoughts_anxious", 5), ("ref_self_harm", -1), ("ref_self_harm", True), ("ref_numb", None),
        ("ref_loneliness", "two"), ("ref_flashbacks", "Nearly every day"), ("ref_numb", 1.5),
        ("sleep_hours", 1_000_000), ("sleep_hours", -1), ("meals_per_day", 7), ("subj_mind", 42),
    ])
    def test_bad_answers_rejected(self, client, db_session, key, value):
        p = make_user(client)
        s = start(client, p)
        r = answer(client, p, s["session_id"], key, value)
        assert r.status_code == 422, r.text
        n = db_session.execute(text("SELECT count(*) FROM questionnaire_responses WHERE session_id = :s"), {"s": s["session_id"]}).scalar()
        assert n == 0

    def test_nan_rejected(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        r = client.post(f"{API}/patient/session/{s['session_id']}/respond", headers={**p["headers"], "Content-Type": "application/json"},
                        content='{"question_key": "sleep_hours", "raw_value": NaN, "response_time_ms": 1800}')
        assert r.status_code == 422

    @pytest.mark.parametrize("rt", [-1, 10**12])
    def test_bad_response_time_rejected(self, client, db_session, rt):
        p = make_user(client)
        s = start(client, p)
        assert answer(client, p, s["session_id"], "ref_numb", 0, rt=rt).status_code == 422

    def test_free_text_trimmed_and_encrypted(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        assert answer(client, p, s["session_id"], "subj_mind", "<b>x</b>" * 1000).status_code == 200
        stored = db_session.execute(text("SELECT raw_value FROM questionnaire_responses WHERE question_key = 'subj_mind'")).scalar()
        from app.services.encryption import decrypt
        assert "<b>" not in str(stored) and len(decrypt(stored)) == 2000

    def test_question_outside_this_checkin_rejected(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p)
        move_to_yesterday(db_session, s["session_id"])
        s2 = start(client, p)
        assert s2["stage"] == "stable"
        asked = {q["key"] for q in s2["questions"]}
        assert "ref_numb" not in asked
        assert answer(client, p, s2["session_id"], "ref_numb", 3).status_code == 422

    def test_retired_and_unknown_keys_rejected(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        assert answer(client, p, s["session_id"], "phq_9", 3).status_code == 422
        assert answer(client, p, s["session_id"], "nonexistent", 1).status_code == 422


# ── Submitting, concurrency, refresh ─────────────────────────────────────────

class TestCheckinLifecycle:
    def test_cannot_submit_incomplete(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        assert submit(client, p, s["session_id"]).status_code == 422
        answer(client, p, s["session_id"], "ref_self_harm", 3)
        r = submit(client, p, s["session_id"])
        assert r.status_code == 422 and "missing" in r.json()["detail"]
        assert status_of(client, p, s["session_id"]) == "in_progress"

    def test_free_text_is_optional(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        for q in s["questions"]:
            if q["type"] != "text":
                answer(client, p, s["session_id"], q["key"], default_value(q))
        assert submit(client, p, s["session_id"]).status_code == 200
        assert status_of(client, p, s["session_id"]) == "scored"

    def test_refresh_restores_saved_answers(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        answer(client, p, s["session_id"], "ref_numb", 2)
        answer(client, p, s["session_id"], "sleep_hours", 7.5)
        answer(client, p, s["session_id"], "subj_mind", "half way")
        s2 = start(client, p)
        assert s2["session_id"] == s["session_id"]
        assert [q["key"] for q in s2["questions"]] == [q["key"] for q in s["questions"]]
        assert s2["answers"] == {"ref_numb": 2, "sleep_hours": 7.5, "subj_mind": "half way"}

    def test_simultaneous_starts_create_one_checkin(self, client, db_session):
        from fastapi.testclient import TestClient
        from app.main import app
        p = make_user(client)
        ids, errors = [], []

        def go():
            try:
                ids.append(TestClient(app).post(f"{API}/patient/session/start", headers=p["headers"]).json()["session_id"])
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=go) for _ in range(5)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert not errors
        assert len(set(ids)) == 1
        n = db_session.execute(text("SELECT count(*) FROM sessions WHERE patient_id = :p"), {"p": p["id"]}).scalar()
        assert n == 1

    def test_one_checkin_per_day(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p)
        r = client.post(f"{API}/patient/session/start", headers=p["headers"])
        assert r.status_code == 409 and r.json()["detail"] == "already_completed_today"

    def test_scoring_failure_marks_not_scored(self, client, db_session, monkeypatch):
        p = make_user(client)
        s = start(client, p)
        answer_all(client, p, s)
        import app.engine.scoring as scoring

        def boom(*a, **k):
            raise RuntimeError("simulated scoring failure")
        monkeypatch.setattr(scoring, "compute_all_domains", boom)
        db_session.execute(text("UPDATE sessions SET completed_at = now() WHERE id = :s"), {"s": s["session_id"]})
        db_session.commit()
        with pytest.raises(RuntimeError):
            scoring.run_scoring_pipeline(s["session_id"])
        assert status_of(client, p, s["session_id"]) == "abstained"

    def test_malformed_stored_answer_is_skipped_not_fatal(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        answer_all(client, p, s, {"ref_loneliness": 3})
        # Simulate a bad value that got into the database some other way
        db_session.execute(text("UPDATE questionnaire_responses SET raw_value = '\"two\"' "
                                "WHERE session_id = :s AND question_key = 'ref_numb'"), {"s": s["session_id"]})
        db_session.commit()
        assert submit(client, p, s["session_id"]).status_code == 200
        assert status_of(client, p, s["session_id"]) == "scored"


# ── Stages and patient type through the API ─────────────────────────────────

class TestStagesAndTypes:
    def test_first_checkin_is_initial_then_stable(self, client, db_session):
        p = make_user(client)
        s = start(client, p)
        assert s["stage"] == "initial" and len(s["questions"]) == 22
        answer_all(client, p, s)
        submit(client, p, s["session_id"])
        move_to_yesterday(db_session, s["session_id"])
        s2 = start(client, p)
        assert s2["stage"] == "stable" and len(s2["questions"]) == 11

    def test_legacy_phq9_item9_gives_crisis(self, client, db_session):
        p = make_user(client)
        sid = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO sessions (id, patient_id, started_at, completed_at, abstained) "
            "VALUES (:s, :p, now() - interval '2 days', now() - interval '2 days', false)"), {"s": sid, "p": p["id"]})
        db_session.execute(text(
            "INSERT INTO questionnaire_responses (id, session_id, question_key, question_type, raw_value, answered_at) "
            "VALUES (:i, :s, 'phq_9', 'phq9', '3', now() - interval '2 days')"), {"i": uuid.uuid4(), "s": sid})
        db_session.commit()
        assert start(client, p)["stage"] == "crisis"

    def test_clinician_sees_joint_type_and_at_risk(self, client, db_session):
        doc = make_user(client, "clinician")
        joint = make_user(client)
        full_checkin(client, joint, {"ref_thoughts_anxious": 3, "ref_thoughts_scary": 3, "ref_flashbacks": 3})
        risky = make_user(client)
        full_checkin(client, risky, {"ref_thoughts_harm_others": 2})
        for pt in (joint, risky):
            assert client.post(f"{API}/clinician/link", headers=doc["headers"], json={"patient_email": pt["email"]}).status_code == 201

        listing = {p["email"]: p["patient_type"] for p in client.get(f"{API}/clinician/patients", headers=doc["headers"]).json()}
        assert listing[joint["email"]]["primary_label"] == "Anxious + Trauma-related"
        assert not listing[joint["email"]]["at_risk"]
        assert listing[risky["email"]]["at_risk"] and listing[risky["email"]]["primary"] == "low_concern"

        summary = client.get(f"{API}/clinician/patient/{risky['id']}/summary", headers=doc["headers"]).json()
        assert summary["patient_type"]["safety_items"] == ["ref_thoughts_harm_others"]

    def test_patient_cannot_touch_another_patients_checkin(self, client, db_session):
        a, b = make_user(client), make_user(client)
        sb = start(client, b)
        assert answer(client, a, sb["session_id"], "ref_numb", 3).status_code == 404
        assert client.post(f"{API}/patient/session/{sb['session_id']}/reset", headers=a["headers"]).status_code == 404

    def test_clinician_cannot_use_patient_checkin(self, client, db_session):
        doc = make_user(client, "clinician")
        assert client.post(f"{API}/patient/session/start", headers=doc["headers"]).status_code == 403


# ── Patient badge and at-risk visibility ─────────────────────────────────────

def wellbeing(client, user):
    r = client.get(f"{API}/patient/wellbeing", headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def clinician_view(client, doc, patient):
    client.post(f"{API}/clinician/link", headers=doc["headers"], json={"patient_email": patient["email"]})
    listing = {p["email"]: p["patient_type"] for p in client.get(f"{API}/clinician/patients", headers=doc["headers"]).json()}
    return listing[patient["email"]]


class TestBadgeAndAtRisk:
    def test_new_patient_is_not_checked_in_not_normality(self, client, db_session):
        p = make_user(client)
        w = wellbeing(client, p)
        assert (w["badge"], w["at_risk"], w["checked_in"]) == ("NONE", False, False)
        assert w["risk"] == {"pct": None, "label": "No data", "reason": None}
        start(client, p)  # an unsubmitted check-in doesn't change that
        assert wellbeing(client, p)["badge"] == "NONE"

    def test_calm_checkin_is_s1(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p)
        w = wellbeing(client, p)
        assert (w["badge"], w["at_risk"], w["checked_in"]) == ("S1", False, True)
        assert w["risk"]["label"] == "Low" and w["risk"]["pct"] == 0

    def test_reported_self_harm_and_harm_to_others_is_s2_at_risk(self, client, db_session):
        # The case reported: self-harm "More than half the days", harming others "Several days"
        doc, p = make_user(client, "clinician"), make_user(client)
        full_checkin(client, p, {"ref_self_harm": 2, "ref_thoughts_harm_others": 1})
        w = wellbeing(client, p)
        assert (w["badge"], w["at_risk"], w["checked_in"]) == ("S2", True, True)
        assert w["risk"] == {"pct": None, "label": "High", "reason": "safety"}
        t = clinician_view(client, doc, p)
        assert t["at_risk"] and set(t["safety_items"]) == {"ref_self_harm", "ref_thoughts_harm_others"}

    def test_still_at_risk_while_reopened_with_edit(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 2, "ref_thoughts_harm_others": 1})
        edit(client, p, s["session_id"])

        w = wellbeing(client, p)
        assert w["badge"] == "S2" and w["risk"]["label"] == "High"  # not a placeholder "Low"
        t = clinician_view(client, doc, p)
        assert t["at_risk"] and t["being_edited"] and not t["scores_pending"]
        assert set(t["scores"]) == {"depressive", "anxious", "obsessive", "trauma", "interpersonal"}
        summary = client.get(f"{API}/clinician/patient/{p['id']}/summary", headers=doc["headers"]).json()
        assert summary["patient_type"]["at_risk"]
        assert start(client, p)["stage"] == "crisis"

    def test_yesterdays_risk_still_shows_while_todays_checkin_is_in_progress(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_hopelessness": 1})
        move_to_yesterday(db_session, s["session_id"])
        s2 = start(client, p)
        assert s2["stage"] == "crisis"
        assert wellbeing(client, p)["badge"] == "S2"

    def test_clinician_resolving_the_flag_clears_at_risk(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 1})
        assert clinician_view(client, doc, p)["at_risk"]
        flag_id = db_session.execute(text("SELECT id FROM dissonance_flags WHERE session_id = :s AND flag_type = 'self_reported_safety_concern'"),
                                     {"s": s["session_id"]}).scalar()
        assert client.patch(f"{API}/clinician/flag/{flag_id}/resolve", headers=doc["headers"]).status_code == 200
        assert not clinician_view(client, doc, p)["at_risk"]
        assert wellbeing(client, p)["at_risk"] is False

    def test_high_scores_without_safety_items_are_not_at_risk(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p, {"ref_numb": 3, "ref_no_excitement": 3, "ref_not_worthy": 3, "ref_start_finish": 3})
        w = wellbeing(client, p)
        assert w["at_risk"] is False and w["badge"] == "S2"  # depressive > 0.5 is still the S2 badge, but not "at risk"


class TestRiskRate:
    def test_one_strong_type_is_not_averaged_away(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p, {"ref_flashbacks": 3, "ref_thoughts_scary": 2, "ref_thoughts_unwanted": 2})
        r = wellbeing(client, p)["risk"]
        assert r["reason"] == "scores" and r["pct"] >= 60 and r["label"] == "High"

    def test_moderate(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p, {"ref_loneliness": 2, "ref_no_one_to_rely_on": 1, "ref_disapproval": 1, "ref_harmful_relationships": 1})
        r = wellbeing(client, p)["risk"]
        assert r["label"] == "Moderate" and 33 <= r["pct"] < 60


class TestHomeTilesDuringEdit:
    def test_tiles_keep_last_submitted_scores_while_editing(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_loneliness": 3, "ref_no_one_to_rely_on": 3})
        before = client.get(f"{API}/patient/history", headers=p["headers"]).json()
        assert {r["domain"] for r in before} == {"depressive", "anxious", "obsessive", "trauma", "interpersonal"}

        edit(client, p, s["session_id"])
        during = client.get(f"{API}/patient/history", headers=p["headers"]).json()
        assert sorted((r["domain"], r["score"]) for r in during) == sorted((r["domain"], r["score"]) for r in before)
        assert wellbeing(client, p)["risk"]["reason"] == "scores"

        answer(client, p, s["session_id"], "ref_loneliness", 0)
        answer(client, p, s["session_id"], "ref_no_one_to_rely_on", 0)
        submit(client, p, s["session_id"])
        after = {r["domain"]: r["score"] for r in client.get(f"{API}/patient/history", headers=p["headers"]).json()}
        assert len(after) == 5 and after["interpersonal"] < dict((r["domain"], r["score"]) for r in before)["interpersonal"]

    def test_resubmit_that_cannot_be_scored_clears_old_scores(self, client, db_session, monkeypatch):
        p = make_user(client)
        s = full_checkin(client, p)
        edit(client, p, s["session_id"])
        import app.engine.scoring as scoring
        monkeypatch.setattr(scoring, "should_abstain", lambda u: True)
        submit(client, p, s["session_id"])
        assert status_of(client, p, s["session_id"]) == "abstained"
        n = db_session.execute(text("SELECT count(*) FROM domain_scores WHERE session_id = :s"), {"s": s["session_id"]}).scalar()
        assert n == 0


class TestSafetyReasons:
    @pytest.mark.parametrize("answers,expected", [
        ({"ref_self_harm": 2}, ["self"]),
        ({"ref_thoughts_harm_others": 1}, ["others"]),
        ({"ref_self_harm": 2, "ref_thoughts_harm_others": 1}, ["self", "others"]),
        ({"ref_hopelessness": 1}, ["hopeless"]),
        ({"subj_mind": "I want to kill myself"}, ["self"]),
        ({"subj_mind": "I could hurt someone"}, ["others"]),
    ])
    def test_reasons_match_what_was_reported(self, client, db_session, answers, expected):
        p = make_user(client)
        full_checkin(client, p, answers)
        assert wellbeing(client, p)["safety_reasons"] == expected

    def test_reason_kept_after_edited_away(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_thoughts_harm_others": 2})
        edit(client, p, s["session_id"])
        answer(client, p, s["session_id"], "ref_thoughts_harm_others", 0)
        submit(client, p, s["session_id"])
        assert wellbeing(client, p)["safety_reasons"] == ["others"]

    def test_insights_chat_names_only_the_reported_reason(self, client, db_session):
        p = make_user(client)
        full_checkin(client, p, {"ref_thoughts_harm_others": 1})
        reply = client.post(f"{API}/patient/insights", headers=p["headers"], json={"keyword": "overall"}).json()["response"]
        assert "harming someone else" in reply and "yourself" not in reply


# ── Deleting a check-in ─────────────────────────────────────────────────────

def delete_checkin(client, user, sid):
    return client.delete(f"{API}/patient/session/{sid}", headers=user["headers"])


class TestDeleteKeepsSafety:
    def test_delete_without_safety_flags_removes_everything(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"meals_per_day": 1})
        assert delete_checkin(client, p, s["session_id"]).status_code == 204
        n = db_session.execute(text("SELECT count(*) FROM sessions WHERE id = :s"), {"s": s["session_id"]}).scalar()
        assert n == 0
        assert start(client, p)["stage"] == "initial"  # can redo today

    def test_delete_with_safety_flag_is_hidden_from_patient_but_kept(self, client, db_session):
        from app.engine.scoring import DELETED_NOTE
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 2, "meals_per_day": 1})
        sid = s["session_id"]
        assert delete_checkin(client, p, sid).status_code == 204

        # Patient side: gone
        assert client.get(f"{API}/patient/sessions", headers=p["headers"]).json() == []
        assert client.get(f"{API}/patient/history", headers=p["headers"]).json() == []
        assert client.get(f"{API}/patient/session/{sid}/status", headers=p["headers"]).status_code == 404
        assert client.post(f"{API}/patient/session/{sid}/reset", headers=p["headers"]).status_code == 404

        # Kept for the clinician: safety flag (annotated) and answers; other flags and scores removed
        f = flags(db_session, sid)
        assert list(f) == ["self_reported_safety_concern"] and DELETED_NOTE in f["self_reported_safety_concern"]
        n = db_session.execute(text("SELECT count(*) FROM questionnaire_responses WHERE session_id = :s"), {"s": sid}).scalar()
        assert n == len(s["questions"])
        t = clinician_view(client, doc, p)
        assert t["at_risk"] and t["safety_items"] == ["ref_self_harm"]
        sessions = client.get(f"{API}/clinician/patient/{p['id']}/sessions", headers=doc["headers"]).json()
        assert sessions[0]["status"] == "deleted_by_patient" and sessions[0]["deleted_at"]

        # Still treated as at risk; patient may do a new check-in today, which gets the crisis set
        assert wellbeing(client, p)["badge"] == "S2"
        s2 = start(client, p)
        assert s2["session_id"] != sid and s2["stage"] == "crisis"

    def test_deleting_twice_does_not_repeat_note(self, client, db_session):
        from app.engine.scoring import DELETED_NOTE
        p = make_user(client)
        s = full_checkin(client, p, {"ref_hopelessness": 1})
        delete_checkin(client, p, s["session_id"])
        assert delete_checkin(client, p, s["session_id"]).status_code == 404
        assert flags(db_session, s["session_id"])["self_reported_safety_concern"].count(DELETED_NOTE) == 1

    def test_resolved_flag_on_deleted_checkin_no_longer_counts(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 1})
        delete_checkin(client, p, s["session_id"])
        assert clinician_view(client, doc, p)["at_risk"]
        fid = db_session.execute(text("SELECT id FROM dissonance_flags WHERE session_id = :s"), {"s": s["session_id"]}).scalar()
        client.patch(f"{API}/clinician/flag/{fid}/resolve", headers=doc["headers"])
        assert wellbeing(client, p)["badge"] == "NONE"
        assert start(client, p)["stage"] == "initial"

    def test_reopened_checkin_with_safety_flag_can_be_deleted_and_is_kept(self, client, db_session):
        p = make_user(client)
        s = full_checkin(client, p, {"ref_thoughts_harm_others": 1})
        edit(client, p, s["session_id"])
        assert delete_checkin(client, p, s["session_id"]).status_code == 204
        assert "self_reported_safety_concern" in flags(db_session, s["session_id"])
        assert wellbeing(client, p)["safety_reasons"] == ["others"]


class TestSpecificSafetyWording:
    def test_flag_and_banner_name_question_and_answer(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_thoughts_harm_others": 1, "ref_hopelessness": 1})
        f = flags(db_session, s["session_id"])["self_reported_safety_concern"]
        assert f == "Thoughts of hurting someone else: Several days; Feelings of hopelessness: Several days"
        assert "ref_" not in f
        t = clinician_view(client, doc, p)
        assert t["safety_details"] == [
            {"item": "ref_thoughts_harm_others", "label": "Thoughts of hurting someone else", "answer": "Several days"},
            {"item": "ref_hopelessness", "label": "Feelings of hopelessness", "answer": "Several days"},
        ]
        signal = db_session.execute(text("SELECT signal_val FROM dissonance_flags WHERE session_id = :s AND flag_type = 'self_reported_safety_concern'"),
                                    {"s": s["session_id"]}).scalar()
        assert signal == "Patient self-reported thoughts of harming others and hopelessness"

    def test_self_harm_only_does_not_mention_others(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_self_harm": 2})
        f = flags(db_session, s["session_id"])["self_reported_safety_concern"]
        assert f == "Feelings of wanting to harm themself: More than half the days"
        details = clinician_view(client, doc, p)["safety_details"]
        assert [d["label"] for d in details] == ["Feelings of wanting to harm themself"]

    def test_edited_away_shows_what_was_originally_reported(self, client, db_session):
        doc, p = make_user(client, "clinician"), make_user(client)
        s = full_checkin(client, p, {"ref_thoughts_harm_others": 2})
        edit(client, p, s["session_id"])
        answer(client, p, s["session_id"], "ref_thoughts_harm_others", 0)
        submit(client, p, s["session_id"])
        d = clinician_view(client, doc, p)["safety_details"]
        assert len(d) == 1 and d[0]["item"] == "edited_safety_answer"
        assert d[0]["answer"] == "Thoughts of hurting someone else: More than half the days"
