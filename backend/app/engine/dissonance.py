from typing import List, Dict, Any, Callable

from app.engine.questionnaire_reference import (
    MEALS_LOW, SAFETY_KEYS, SLEEP_HIGH_HOURS, SLEEP_LOW_HOURS,
)
from app.services.mental_health_classifier import SUICIDAL_RISK_THRESHOLD

_SELF_REPORT_SAFETY_KEYS = list(SAFETY_KEYS)


def _endorsed_safety_items(ind: dict) -> list[str]:
    # Normalised 0–1; > 0 means anything above "Not at all".
    return [k for k in _SELF_REPORT_SAFETY_KEYS if ind.get(k, 0) > 0]

_Rule = dict[str, Any]

DISSONANCE_RULES: list[_Rule] = [
    {
        "flag_type": "sleep_late_activity",
        "condition": lambda ind: (
            7 <= ind.get("sleep_hours_raw", 0) <= 9      # reports a healthy amount of sleep
            and ind.get("late_phone_activity_nights", 0) > 0.5
        ),
        "self_report_val": "User reports adequate sleep",
        "signal_val": lambda ind: (
            f'{int(ind.get("late_phone_activity_nights", 0) * 7)} nights of late device activity detected'
        ),
        "severity": "medium",
    },
    {
        "flag_type": "mood_movement",
        # Only when movement data actually exists — a missing signal is not "sedentary".
        "condition": lambda ind: (
            "daily_step_variance" in ind
            and ind.get("ref_no_excitement", 1.0) < 0.3     # reports interest / no low mood
            and ind.get("ref_hopelessness", 1.0) < 0.3
            and ind["daily_step_variance"] < 0.2
        ),
        "self_report_val": "Patient reports good mood and interest",
        "signal_val": "Consistent sedentary pattern — minimal movement variance",
        "severity": "high",
    },
    {
        "flag_type": "social_report_vs_withdrawal",
        "condition": lambda ind: (
            ind.get("ref_loneliness", 1.0) < 0.34       # reports little or no loneliness
            and ind.get("journal_isolation", 0) > 0.6
        ),
        "self_report_val": "Patient reports little or no loneliness",
        "signal_val": "High isolation keyword frequency in journal entries",
        "severity": "medium",
    },
    {
        "flag_type": "ml_suicidal_risk_signal",
        "condition": lambda ind: ind.get("mh_suicidal", 0) > SUICIDAL_RISK_THRESHOLD,
        "self_report_val": "N/A — model-derived signal, not a self-report comparison",
        "signal_val": lambda ind: (
            f'Mental-health classifier flagged suicidal-risk language in journal '
            f'(p={ind.get("mh_suicidal", 0):.2f})'
        ),
        "severity": "high",
    },
    {
        "flag_type": "self_reported_safety_concern",
        "condition": lambda ind: bool(_endorsed_safety_items(ind)),
        "self_report_val": lambda ind: "Endorsed: " + ", ".join(_endorsed_safety_items(ind)),
        "signal_val": "Patient self-reported self-harm, harm to others, or hopelessness",
        "severity": "high",
    },
    {
        "flag_type": "sleep_out_of_range",
        "condition": lambda ind: (
            "sleep_hours_raw" in ind
            and (ind["sleep_hours_raw"] < SLEEP_LOW_HOURS or ind["sleep_hours_raw"] > SLEEP_HIGH_HOURS)
        ),
        "self_report_val": lambda ind: f'{ind["sleep_hours_raw"]:g} hours of sleep per night',
        "signal_val": f"Outside {SLEEP_LOW_HOURS}–{SLEEP_HIGH_HOURS} hour range",
        "severity": "medium",
    },
    {
        "flag_type": "low_meal_intake",
        "condition": lambda ind: ind.get("meals_per_day_raw", MEALS_LOW) < MEALS_LOW,
        "self_report_val": lambda ind: f'{ind["meals_per_day_raw"]:g} meals per day',
        "signal_val": f"Below {MEALS_LOW} meals per day",
        "severity": "medium",
    },
]


def detect_dissonance(indicators: dict) -> list[dict]:
    flags = []
    for rule in DISSONANCE_RULES:
        try:
            if rule["condition"](indicators):
                signal_val = rule["signal_val"]
                if callable(signal_val):
                    signal_val = signal_val(indicators)
                self_report_val = rule["self_report_val"]
                if callable(self_report_val):
                    self_report_val = self_report_val(indicators)
                flags.append({
                    "flag_type": rule["flag_type"],
                    "self_report_val": self_report_val,
                    "signal_val": signal_val,
                    "severity": rule["severity"],
                })
        except (KeyError, TypeError, ZeroDivisionError):
            continue
    return flags
