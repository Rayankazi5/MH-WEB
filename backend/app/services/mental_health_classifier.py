"""
Remote Hugging Face Inference API client for a fine-tuned mental-health
risk classifier.

Model:  SajjadIslam/multiMentalRoBERTA-6-class (Apache-2.0, RoBERTa-based)
Labels: stress, anxiety, depression, ptsd, suicidal, none
Paper:  "multiMentalRoBERTa: A Fine-tuned Multiclass Classifier for Mental
        Health Disorder" (IEEE BigData 2025) — https://arxiv.org/abs/2511.04698

This is a community research model, not clinically validated for this
application. Its scores are treated as a soft, informational signal only:
merged into the journal entry's keyword_vector (prefixed "mh_") for
clinician visibility, and used to raise a safety flag when the
"suicidal" label is high-confidence (see app/engine/dissonance.py). They
are intentionally NOT wired into the validated PHQ-9-based domain-score
weights in app/engine/weights.json — recalibrating those is a clinical
decision, not an engineering one.

Runs via the HF Inference API rather than a local download, so it needs
HF_API_TOKEN set and network access at call time. A cold start on a
low-traffic community model can take tens of seconds, so this must only
ever be called from the async internal scoring job — never from a
patient-facing request path (see its one call site in app/engine/scoring.py).
"""
import time
from typing import Optional

import httpx

from app.config import get_settings

MODEL_ID = "SajjadIslam/multiMentalRoBERTA-6-class"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
MAX_CHARS = 2000  # payload cap; the model itself truncates at 512 tokens
REQUEST_TIMEOUT_SECONDS = 30.0
COLD_START_RETRIES = 3
COLD_START_BACKOFF_SECONDS = 5

SUICIDAL_RISK_THRESHOLD = 0.5


def classify_mental_health_risk(text: str) -> Optional[dict[str, float]]:
    """
    Returns {label: probability} for all six classes, or None if the
    token is missing, the text is empty, the call fails, or the model
    never finished loading within the retry budget. Never raises —
    callers should treat this as a best-effort signal.
    """
    settings = get_settings()
    token = settings.hf_api_token
    if not token or not text or not text.strip():
        return None

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": text[:MAX_CHARS], "options": {"wait_for_model": True}}

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            for _ in range(COLD_START_RETRIES):
                resp = client.post(API_URL, headers=headers, json=payload)
                if resp.status_code == 503:
                    # Serverless model is still cold-starting — back off and retry.
                    time.sleep(COLD_START_BACKOFF_SECONDS)
                    continue
                resp.raise_for_status()
                data = resp.json()
                # Expected shape: [[{"label": "Stress", "score": 0.1}, ...]]
                rows = data[0] if data and isinstance(data[0], list) else data
                return {row["label"].lower(): round(float(row["score"]), 4) for row in rows}
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None

    return None
