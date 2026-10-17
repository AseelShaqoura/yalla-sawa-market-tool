import re
from math import sqrt
from collections import Counter
from statistics import mean, median, stdev

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


def statistical_summary(reviews: list[dict]) -> dict:
    """Calculate transparent descriptive statistics for review star scores."""
    scores = [float(item["score"]) for item in reviews if item.get("score") is not None]
    summary = {
        "n": len(scores), "mean": None, "median": None, "stdev": None,
        "min": None, "max": None, "ci_low": None, "ci_high": None,
    }
    if not scores:
        return summary
    average = mean(scores)
    deviation = stdev(scores) if len(scores) > 1 else 0.0
    margin = 1.96 * deviation / sqrt(len(scores)) if len(scores) > 1 else 0.0
    summary.update({
        "mean": average, "median": median(scores), "stdev": deviation,
        "min": min(scores), "max": max(scores),
        "ci_low": max(1.0, average - margin), "ci_high": min(5.0, average + margin),
    })
    return summary


def sentiment_summary(reviews: list[dict]) -> dict[str, int]:
    counts = {"إيجابي": 0, "محايد": 0, "سلبي": 0}
    for review in reviews:
        counts[classify_sentiment(review.get("content", ""), review.get("score"))] += 1
    return counts


def split_recommendations(text: str) -> list[dict[str, str]]:
    """Convert Gemini's numbered Arabic sections into structured UI blocks."""
    sections: list[dict[str, str]] = []
    current_title = "ملخص التوصيات"
    current_lines: list[str] = []
    heading_pattern = re.compile(r"^\s*(?:#{1,3}\s*)?(?:\d+[.)-]\s*)?(.{3,})\s*$")
    known_titles = ("أكثر الشكاوى", "المشكلات", "فرص", "ميزات", "توصيات الثقة", "مخاطر", "خطة اختبار")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = heading_pattern.match(line)
        is_heading = bool(match and (line.startswith("#") or re.match(r"^\d+[.)-]", line) or any(t in line for t in known_titles)))
        if is_heading:
            if current_lines:
                sections.append({"title": current_title, "body": "\n".join(current_lines)})
            current_title = match.group(1).strip(" *#:")
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"title": current_title, "body": "\n".join(current_lines)})
    return sections or [{"title": "التوصيات", "body": text.strip()}]


def competitor_swot(competitor: dict, reviews: list[dict]) -> dict[str, list[str]]:
    """Produce transparent, evidence-based strengths and weaknesses for one competitor."""
    strengths: list[str] = []
    weaknesses: list[str] = []
    score = competitor.get("score")
    sentiments = sentiment_summary(reviews)
    total = sum(sentiments.values())
    positive_ratio = sentiments["إيجابي"] / total if total else 0
    negative_ratio = sentiments["سلبي"] / total if total else 0

    if competitor.get("strengths"):
        strengths.extend([part.strip() for part in str(competitor["strengths"]).split("\n") if part.strip()])
    if competitor.get("weaknesses"):
        weaknesses.extend([part.strip() for part in str(competitor["weaknesses"]).split("\n") if part.strip()])
    if score is not None and float(score) >= 4.2:
        strengths.append(f"تقييم مرتفع على المتجر: {float(score):.1f}/5")
    if positive_ratio >= 0.6:
        strengths.append(f"غالبية المراجعات إيجابية ({positive_ratio * 100:.1f}%)")
    if score is not None and float(score) < 3.5:
        weaknesses.append(f"التقييم العام منخفض نسبيًا: {float(score):.1f}/5")
    if negative_ratio >= 0.25:
        weaknesses.append(f"نسبة ملحوظة من المراجعات سلبية ({negative_ratio * 100:.1f}%)")
    if not strengths:
        strengths.append("لا توجد بيانات كافية؛ يلزم تحقق ميداني أو مراجعات إضافية")
    if not weaknesses:
        weaknesses.append("لم تظهر نقطة ضعف واضحة من العينة الحالية؛ لا يعني ذلك عدم وجودها")
    return {"strengths": strengths[:5], "weaknesses": weaknesses[:5]}
