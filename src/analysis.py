import re
from collections import Counter

POSITIVE_WORDS = {"ممتاز", "رائع", "جيد", "سهل", "سريع", "مفيد", "excellent", "great", "good", "easy"}
NEGATIVE_WORDS = {"سيئ", "بطء", "بطيء", "مشكلة", "غالي", "فشل", "bad", "slow", "expensive", "crash", "problem"}


def clean_text(value: str | None) -> str:
    text = (value or "").strip()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def classify_sentiment(text: str, score: int | None = None) -> str:
    cleaned = clean_text(text).lower()
    if score is not None:
        if score <= 2:
            return "سلبي"
        if score >= 4:
            return "إيجابي"
    positive = sum(word in cleaned for word in POSITIVE_WORDS)
    negative = sum(word in cleaned for word in NEGATIVE_WORDS)
    if positive > negative:
        return "إيجابي"
    if negative > positive:
        return "سلبي"
    return "محايد"


def summarize_themes(texts: list[str], top_n: int = 10) -> list[tuple[str, int]]:
    tokens: list[str] = []
    for text in texts:
        tokens.extend(re.findall(r"[\wء-ي]{3,}", clean_text(text).lower()))
    ignored = {"هذا", "هذه", "على", "من", "الى", "عن", "the", "and", "for", "with"}
    counts = Counter(token for token in tokens if token not in ignored)
    return counts.most_common(top_n)
