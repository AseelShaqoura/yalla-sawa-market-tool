import pandas as pd
import streamlit as st

from src.config import settings
from src.ai_analysis import generate_market_recommendations
from src.analysis import classify_sentiment
from src.db import (
    init_db,
    list_competitors,
    list_reviews,
    list_reviews_for_competitors,
    review_count,
    save_competitor,
    save_reviews,
)
from src.scraper import fetch_reviews, search_apps
from src.reports import excel_bytes, html_report

st.set_page_config(
    page_title="Market Gap Lab | يلا سوا",
    page_icon="🚗",
    layout="wide",
)
init_db()

st.markdown(
    """
    <style>
    html, body, [class*="css"] { direction: rtl; text-align: right; }
    .stApp, .stAppViewContainer, .main, section.main, .block-container,
    [data-testid="stSidebar"], [data-testid="stSidebarContent"],
    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stMarkdownContainer"], [data-testid="stAlert"],
    [data-testid="stMetric"], [data-testid="stTextInput"],
    [data-testid="stSlider"], [data-testid="stSelectbox"] {
        direction: rtl;
        text-align: right;
    }
    input, textarea, select, [role="combobox"] {
        direction: rtl !important;
        text-align: right !important;
    }
    button, [data-baseweb="tab"] {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stSidebar"] {
        border-left: 1px solid #e7eceb;
        border-right: 0;
    }
    [data-testid="stDataFrame"] { direction: ltr; }
    .block-container { max-width: 1250px; padding-top: 2rem; }
    .hero { background: linear-gradient(135deg, #073b3a, #0b6b66); color: white;
            padding: 2rem; border-radius: 22px; margin-bottom: 1.5rem; }
    .analysis-panel { background: linear-gradient(135deg, #f2faf8, #ffffff);
            border: 1px solid #d5e9e3; border-right: 5px solid #0b6b66;
            border-radius: 16px; padding: 1rem 1.25rem; margin: 1rem 0; }
    .analysis-panel h3 { color: #073b3a; margin: 0 0 .35rem 0; }
    .analysis-panel p { color: #42615c; margin: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>Market Gap Lab</h1>'
    '<p>أداة دراسة المنافسين واكتشاف فجوات السوق لمشروع «يلا سوا»</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("إعدادات الدراسة")
    review_limit = st.selectbox(
        "عدد المراجعات لكل تطبيق",
        options=[300, 250, 200, 150, 100, 50],
        index=3,
        format_func=lambda value: f"{value} مراجعة",
        help="اختاري العدد بوضوح؛ القائمة مرتبة من 300 إلى 50 لتجنب انعكاس اتجاه شريط RTL.",
    )
    st.caption(f"قاعدة البيانات: {settings.db_path}")
    st.info("هذه النسخة هي الهيكل الأولي. سيتم تفعيل جمع المراجعات والتحليل في الخطوات التالية.")

search_tab, selected_tab, market_tab = st.tabs(
    ["البحث عن المنافسين", "المنافسون المحفوظون", "دراسة السوق"]
)

with search_tab:
    st.subheader("ابحثي عن تطبيقات منافسة")
    query = st.text_input(
        "اسم تطبيق أو كلمة مفتاحية",
        placeholder="مثال: taxi Gaza أو shared transportation Palestine",
    )
    if st.button("بحث", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("اكتبي اسمًا أو كلمة مفتاحية أولًا.")
        else:
            with st.spinner("جاري البحث..."):
                results = search_apps(query.strip(), limit=10)
            st.session_state["search_results"] = results
            if not results:
                st.info("لا توجد نتائج. تأكدي من تثبيت الاعتمادات أو جرّبي كلمة مفتاحية أخرى.")

    results = st.session_state.get("search_results", [])
    if results:
        st.subheader("نتائج البحث")
        for app in results:
            cols = st.columns([1, 4, 2, 1])
            cols[0].write("📱")
            cols[1].markdown(f"**{app['title']}**  \n{app.get('developer', 'غير معروف')}")
            cols[2].caption(f"التقييم: {app.get('score', '—')}")
            app_id = app.get("app_id")
            if app_id and cols[3].button("إضافة", key=f"add-{app_id}"):
                try:
                    save_competitor(app)
                    st.success("تم حفظ المنافس.")
                except ValueError as error:
                    st.error(str(error))

with selected_tab:
    st.subheader("قائمة المنافسين للدراسة")
    competitors = list_competitors()
    if competitors:
        st.dataframe(pd.DataFrame(competitors), use_container_width=True, hide_index=True)
        st.caption(
            f"سيتم لاحقًا اختيار 2–4 منافسين لجمع وتحليل {review_limit} مراجعة لكل منافس."
        )
    else:
        st.info("لم تتم إضافة منافسين بعد. ابدئي من تبويب البحث.")

with market_tab:
    st.subheader("لوحة دراسة السوق")
    competitors = list_competitors()
    st.markdown("تظهر هنا المنافسون الذين حفظتِهم. اختاري حتى 4 منافسين للعمل عليهم.")

    competitor_options = {
        f"{competitor.get('title', 'غير معروف')} — {competitor.get('developer') or 'مطور غير معروف'}": competitor["id"]
        for competitor in competitors
    }
    selected_labels = st.multiselect(
        "اختاري المنافسين للتحليل",
        options=list(competitor_options.keys()),
        max_selections=4,
        placeholder="اضغطي هنا لعرض المنافسين واختيارهم",
        help="يمكن اختيار منافس واحد إلى أربعة منافسين.",
    )
    selected_ids = {competitor_options[label] for label in selected_labels}
    selected_competitors = [competitor for competitor in competitors if competitor["id"] in selected_ids]

    if selected_competitors:
        st.success(f"تم اختيار {len(selected_competitors)} منافس للتحليل.")
        st.dataframe(
            pd.DataFrame(selected_competitors)[["title", "developer", "score", "ratings_count"]],
            use_container_width=True,
            hide_index=True,
        )

    if not selected_competitors:
        if competitors:
            st.info("اختاري منافسًا واحدًا على الأقل من القائمة أعلاه.")
        else:
            st.info("أضيفي منافسين أولًا من تبويب البحث عن المنافسين.")
    elif st.button("بدء تحليل المنافسين الأربعة", type="primary", use_container_width=True):
        progress = st.progress(0, text="بدء جمع المراجعات...")
        status = st.empty()
        total = len(selected_competitors)
        for index, competitor in enumerate(selected_competitors, start=1):
            title = competitor.get("title", "المنافس")
            status.info(f"جاري جمع المراجعات من: {title}")
            reviews = fetch_reviews(competitor["app_id"], count=review_limit)
            inserted = save_reviews(competitor["id"], reviews)
            progress.progress(index / total, text=f"تمت معالجة {index} من {total}")
            status.success(f"{title}: تم العثور على {len(reviews)} مراجعة، أضيف منها {inserted} جديدة.")
        st.session_state["analysis_completed"] = True
        st.success("اكتمل جمع المراجعات للمنافسين المحددين.")

    c1, c2, c3 = st.columns(3)
    c1.metric("عدد المنافسين", len(competitors))
    c2.metric("المراجعات المجموعة", review_count())
    all_reviews = list_reviews()
    sentiment_counts = {"إيجابي": 0, "محايد": 0, "سلبي": 0}
    for review in all_reviews:
        sentiment = classify_sentiment(review.get("content", ""), review.get("score"))
        sentiment_counts[sentiment] += 1
    c3.metric("المراجعات السلبية", sentiment_counts["سلبي"])
    if review_count():
        st.subheader("ملخص تنفيذي سريع")
        metric_a, metric_b, metric_c, metric_d = st.columns(4)
        total_reviews = len(all_reviews)
        negative_ratio = (sentiment_counts["سلبي"] / total_reviews * 100) if total_reviews else 0
        metric_a.metric("إجمالي المراجعات", total_reviews)
        metric_b.metric("إيجابي", sentiment_counts["إيجابي"])
        metric_c.metric("محايد", sentiment_counts["محايد"])
        metric_d.metric("نسبة السلبي", f"{negative_ratio:.1f}%")

        st.markdown(
            "<div class='analysis-panel'><h3>قراءة أولية للسوق</h3>"
            "<p>هذه المؤشرات وصفية من المراجعات المجموعة. التوصيات النهائية تظهر بعد تشغيل تحليل Gemini.</p></div>",
            unsafe_allow_html=True,
        )
        selected_ids_for_report = [competitor["id"] for competitor in selected_competitors]
        report_reviews = list_reviews_for_competitors(selected_ids_for_report)
        for report_review in report_reviews:
            report_review["sentiment"] = classify_sentiment(
                report_review.get("content", ""), report_review.get("score")
            )
        report_recommendations = st.session_state.get("recommendations", "")
        excel_data = excel_bytes(selected_competitors, report_reviews, [])
        html_data = html_report(selected_competitors, report_reviews, report_recommendations)
        download_col1, download_col2 = st.columns(2)
        download_col1.download_button(
            "تحميل تقرير Excel",
            data=excel_data,
            file_name="yalla-sawa-market-study.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        download_col2.download_button(
            "تحميل تقرير HTML / PDF",
            data=html_data.encode("utf-8"),
            file_name="yalla-sawa-market-study.html",
            mime="text/html",
            use_container_width=True,
            help="افتحي الملف ثم اضغطي Ctrl+P واختاري Microsoft Print to PDF.",
        )
        st.subheader("عينة من المراجعات المجموعة")
        sample_df = pd.DataFrame(all_reviews[:20])
        if not sample_df.empty:
            sample_df["sentiment"] = sample_df.apply(
                lambda row: classify_sentiment(row.get("content", ""), row.get("score")), axis=1
            )
        st.dataframe(sample_df, use_container_width=True, hide_index=True)
        st.subheader("التوصيات بالذكاء الاصطناعي")
        st.caption("سيتم إرسال نصوص المراجعات إلى Google Gemini. لا ترسلي بيانات شخصية أو أرقام هواتف.")
        if st.button("توليد توصيات الذكاء الاصطناعي", use_container_width=True):
            try:
                competitor_ids = [competitor["id"] for competitor in selected_competitors]
                ai_reviews = list_reviews_for_competitors(competitor_ids)
                with st.spinner("جاري تحليل المراجعات وتوليد التوصيات..."):
                    recommendations = generate_market_recommendations(selected_competitors, ai_reviews)
                st.session_state["recommendations"] = recommendations
            except Exception as error:
                st.error(str(error))
        if st.session_state.get("recommendations"):
            with st.container(border=True):
                st.markdown("### توصيات Gemini لمشروع يلا سوا")
                st.markdown(st.session_state["recommendations"])
    else:
        st.warning("بعد جمع المراجعات ستظهر هنا العينة والإحصاءات الأولية.")

st.divider()
st.caption("يلا سوا — أداة بحث لاتخاذ قرار مبني على البيانات، وليست بديلًا عن التحقق الميداني.")
