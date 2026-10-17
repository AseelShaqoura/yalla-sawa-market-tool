from pathlib import Path
from typing import Iterable
from html import escape
from io import BytesIO

import pandas as pd

from .config import settings


def export_excel(
    competitors: Iterable[dict],
    reviews: Iterable[dict] | None = None,
    insights: Iterable[dict] | None = None,
    filename: str = "market-study.xlsx",
) -> Path:
    output = settings.exports_dir / filename
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(list(competitors)).to_excel(writer, sheet_name="Competitors", index=False)
        pd.DataFrame(list(reviews or [])).to_excel(writer, sheet_name="Reviews", index=False)
        pd.DataFrame(list(insights or [])).to_excel(writer, sheet_name="Insights", index=False)
    return output


def excel_bytes(
    competitors: Iterable[dict],
    reviews: Iterable[dict] | None = None,
    insights: Iterable[dict] | None = None,
) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(list(competitors)).to_excel(writer, sheet_name="Competitors", index=False)
        pd.DataFrame(list(reviews or [])).to_excel(writer, sheet_name="Reviews", index=False)
        pd.DataFrame(list(insights or [])).to_excel(writer, sheet_name="Insights", index=False)
    return buffer.getvalue()


def html_report(
    competitors: Iterable[dict],
    reviews: Iterable[dict],
    recommendations: str = "",
) -> str:
    competitor_rows = "".join(
        f"<tr><td>{escape(str(item.get('title', '')))}</td>"
        f"<td>{escape(str(item.get('developer', '')))}</td>"
        f"<td>{escape(str(item.get('score', '—')))}</td></tr>"
        for item in competitors
    )
    review_rows = "".join(
        f"<tr><td>{escape(str(item.get('score', '—')))}</td>"
        f"<td>{escape(str(item.get('sentiment', '')))}</td>"
        f"<td>{escape(str(item.get('content', '')))}</td></tr>"
        for item in list(reviews)[:200]
    )
    recommendation_html = escape(recommendations).replace("\n", "<br>")
    return f"""<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>
<title>تقرير دراسة المنافسين — يلا سوا</title><style>
body{{font-family:Arial,sans-serif;color:#173b37;line-height:1.8;margin:40px}}
h1{{color:#073b3a;border-bottom:3px solid #0b6b66;padding-bottom:12px}}
h2{{color:#0b6b66;margin-top:28px}} table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}
th,td{{border:1px solid #cdded9;padding:8px;text-align:right;vertical-align:top}}
th{{background:#eaf5f1}} .recommendations{{background:#f2faf8;border-right:5px solid #0b6b66;padding:16px}}
@media print{{body{{margin:18mm}} h1{{page-break-before:avoid}}}}
</style></head><body><h1>تقرير دراسة المنافسين — يلا سوا</h1>
<p>تقرير مولد من أداة Market Gap Lab.</p><h2>المنافسون المختارون</h2>
<table><tr><th>المنافس</th><th>المطور</th><th>التقييم</th></tr>{competitor_rows}</table>
<h2>المراجعات والتحليل</h2><table><tr><th>التقييم</th><th>المشاعر</th><th>نص المراجعة</th></tr>{review_rows}</table>
<h2>توصيات الذكاء الاصطناعي</h2><div class='recommendations'>{recommendation_html or 'لم يتم توليد التوصيات بعد.'}</div>
</body></html>"""
