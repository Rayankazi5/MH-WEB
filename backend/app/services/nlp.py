import math
import re
from typing import Optional

# Semantic keyword clusters used to build the journal_vector sent to the LLM.
# Only cluster frequencies — not verbatim text — ever leave the NLP layer.
CLUSTERS: dict[str, list[str]] = {
    "journal_isolation": [
        "alone", "lonely", "isolated", "withdrawn", "disconnected",
        "solitude", "antisocial", "nobody", "invisible", "avoided",
    ],
    "journal_work_stress": [
        "stressed", "overwhelmed", "deadline", "pressure", "burnout",
        "overworked", "exhausted", "frustrated", "demanding", "falling behind",
    ],
    "journal_sleep_disruption": [
        "insomnia", "awake", "restless", "fatigue", "tired",
        "couldn't sleep", "nightmares", "tossing", "groggy", "woke up",
    ],
    "journal_anxiety": [
        "anxious", "worried", "panic", "fear", "nervous",
        "dread", "overthinking", "racing thoughts", "on edge", "uneasy",
    ],
    "journal_low_mood": [
        "sad", "hopeless", "depressed", "miserable", "empty",
        "numb", "worthless", "pointless", "crying", "despair",
    ],
}


def _tokenise(text: str) -> list[str]:
    return re.sub(r"[^a-z\s]", "", text.lower()).split()


def extract_keyword_vector(text: str) -> dict[str, float]:
    tokens = _tokenise(text)
    total_words = max(len(tokens), 1)
    joined = " ".join(tokens)
    vector: dict[str, float] = {}

    for cluster_key, keywords in CLUSTERS.items():
        hits = sum(joined.count(kw) for kw in keywords)
        if hits > 0:
            tf = hits / total_words
            # Log-normalise so a single strong keyword doesn't dominate
            vector[cluster_key] = round(math.log1p(tf * 100) / math.log1p(100), 4)

    return vector


def score_sentiment(text: str) -> Optional[float]:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        analyser = SentimentIntensityAnalyzer()
        compound = analyser.polarity_scores(text)["compound"]
        # Map [-1, 1] → [0, 1]; 1 = very negative (high concern)
        return round(1.0 - (compound + 1.0) / 2.0, 4)
    except ImportError:
        # VADER not installed yet — return neutral until package is added
        return None


def process_journal(body: str) -> tuple[dict, Optional[float], int]:
    keyword_vector = extract_keyword_vector(body)
    sentiment_score = score_sentiment(body)
    word_count = len(body.split())
    return keyword_vector, sentiment_score, word_count
