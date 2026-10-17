import os
from collections import defaultdict
from typing import Any


def generate_market_recommendations(
    competitors: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> str:
    """Send a bounded review sample to Gemini and return Arabic recommendations."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("لم يتم العثور على GEMINI_API_KEY داخل ملف .env")

    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError("ثبّتي مكتبة google-genai أولًا عبر pip install google-genai") from error

    grouped: dict[int, list[str]] = defaultdict(list)
    for review in reviews:
        content = (review.get("content") or "").strip()
        if content and len(grouped[review["competitor_id"]]) < 80:
            grouped[review["competitor_id"]].append(content[:500])

    sections: list[str] = []
    for competitor in competitors:
        items = grouped.get(competitor["id"], [])
        sections.append(
            f"المنافس: {competitor.get('title', 'غير معروف')}\n"
            + "\n".join(f"- {item}" for item in items)
        )

    prompt = """أنت محلل سوق ومنتج متخصص في النقل التشاركي في فلسطين.
حلل مراجعات المستخدمين التالية لمشروع «يلا سوا»، وهو تطبيق لحجز مقعد ومشاركة التوصيل في غزة والضفة.
اكتب بالعربية وبشكل عملي، ولا تخترع أرقامًا أو حقائق غير موجودة في المراجعات.

أخرج النتيجة بهذه العناوين:
1. أكثر الشكاوى تكرارًا
2. المشكلات المتعلقة بالسعر والتوفر والموثوقية
3. فرص يلا سوا غير المستغلة
4. ميزات MVP ذات الأولوية
5. توصيات الثقة والأمان
6. مخاطر أو افتراضات تحتاج تحققًا ميدانيًا
7. خطة اختبار خلال 14 يومًا

بيانات المنافسين والمراجعات:
""" + "\n\n".join(sections)

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("لم يُرجع Gemini نصًا صالحًا للتحليل")
    return text
