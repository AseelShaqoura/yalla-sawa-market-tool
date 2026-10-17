import pandas as pd
import plotly.express as px
import streamlit as st
from html import escape

from src.config import settings
from src.ai_analysis import generate_market_recommendations
from src.analysis import (
    classify_sentiment,
    competitor_swot,
    statistical_summary,
    sentiment_summary,
    split_recommendations,
)
from src.db import (
    init_db,
    list_competitors,
    list_reviews,
    list_reviews_for_competitors,
    review_count,
    save_competitor,
    save_reviews,
)
from src.scraper import ARAB_COUNTRIES, fetch_reviews, search_apps, search_curated_arab_apps
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
    .ai-header { background: linear-gradient(135deg, #073b3a, #0b6b66); color: white;
            padding: 1.2rem 1.4rem; border-radius: 16px 16px 0 0; }
    .ai-header h3 { margin: 0; color: white; font-size: 1.35rem; }
    .ai-header p { margin: .35rem 0 0; color: #d8f3eb; }
    .ai-card { background: #ffffff; border: 1px solid #dcebe6; border-right: 5px solid #10B981;
            border-radius: 12px; padding: 1rem 1.15rem; min-height: 135px; margin-bottom: .8rem; }
    .ai-card h4 { color: #073b3a; margin: 0 0 .55rem; font-size: 1.05rem; }
    .ai-card p { color: #425b56; line-height: 1.75; margin: 0; white-space: pre-line; }
    .ai-note { background: #f3faf7; border: 1px solid #d8eee6; padding: .8rem 1rem;
            color: #42615c; border-radius: 10px; margin-top: .8rem; }
    .swot-card { background: #fff; border: 1px solid #dcebe6; border-radius: 12px;
            padding: 1rem 1.15rem; margin-bottom: 1rem; }
    .swot-card h4 { color: #073b3a; margin: 0 0 .7rem; font-size: 1.1rem; }
    .swot-col { padding: .75rem; border-radius: 9px; min-height: 120px; }
    .swot-strength { background: #effaf5; border-right: 4px solid #10B981; }
    .swot-weakness { background: #fff7ed; border-right: 4px solid #f59e0b; }
    .swot-col h5 { margin: 0 0 .45rem; font-size: 1rem; }
    .swot-col ul { margin: 0; padding-right: 1.1rem; color: #425b56; line-height: 1.7; }
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

search_tab, local_tab, selected_tab, market_tab = st.tabs(
    ["البحث عن المنافسين", "إضافة منافس محلي", "المنافسون المحفوظون", "دراسة السوق"]
)

with search_tab:
    st.subheader("ابحثي عن تطبيقات منافسة")
    query = st.text_input(
        "بحث اختياري",
        placeholder="اتركيه فارغًا لعرض 10 تطبيقات عربية مقترحة، أو اكتبي اسمًا محددًا",
    )
    if st.button("بحث", type="primary", use_container_width=True):
        with st.spinner("جاري تجهيز قائمة التطبيقات العربية..."):
            if query.strip():
                results = search_apps(query.strip(), limit=10)
                st.session_state["search_heading"] = "نتائج البحث المخصصة"
            else:
                results = search_curated_arab_apps(limit=10)
                st.session_state["search_heading"] = "10 تطبيقات عربية منافسة مقترحة"
        st.session_state["search_results"] = results
        if not results:
            st.info("لم تظهر نتائج من Google Play. جربي الضغط مرة أخرى أو اكتبي اسم تطبيق محدد.")

    results = st.session_state.get("search_results", [])
    if results:
        st.subheader(f"{st.session_state.get('search_heading', 'قائمة المرشحين')} — {min(len(results), 10)} تطبيقات")
        st.caption("اختاري المنافسين الذين تريدين حفظهم، ثم اضغطي زر الحفظ مرة واحدة.")
        selected_result_ids = []
        for app in results:
            app_id = app.get("app_id")
            if not app_id:
                continue
            country_code = app.get("country")
            country_name = next(
                (name for name, code in ARAB_COUNTRIES.items() if code == country_code),
                "دولة عربية",
            )
            cols = st.columns([0.7, 1, 4.2, 1.8, 1.5])
            checked = cols[0].checkbox("اختيار", key=f"select-{app_id}", label_visibility="collapsed")
            if checked:
                selected_result_ids.append(app_id)
            cols[1].write("📱")
            cols[2].markdown(f"**{app['title']}**  \n{app.get('developer', 'غير معروف')}")
            cols[3].caption(f"التقييم: {app.get('score', '—')}")
            cols[4].caption(country_name)

        if st.button("حفظ المنافسين المحددين", type="primary", use_container_width=True):
            if not selected_result_ids:
                st.warning("اختاري منافسًا واحدًا على الأقل من القائمة.")
            else:
                selected_apps = [app for app in results if app.get("app_id") in selected_result_ids]
                saved = 0
                for app in selected_apps:
                    try:
                        save_competitor(app)
                        saved += 1
                    except ValueError:
                        pass
                st.success(f"تم حفظ {saved} منافس. انتقلي إلى تبويب دراسة السوق لاختيار حتى 4 للتحليل.")

with local_tab:
    st.subheader("إضافة منافس محلي")
    st.caption("أضيفي مكاتب التاكسيات، مجموعات واتساب وفيسبوك، السرفيس، أو أي بديل محلي لا يظهر في Google Play.")
    with st.form("local_competitor_form", clear_on_submit=True):
        local_title = st.text_input("اسم المنافس أو المجموعة", placeholder="مثال: مكتب تاكسي الجامعة أو جروب واتساب مواصلات غزة")
        local_type = st.selectbox(
            "نوع المنافس",
            ["مكتب تاكسي", "مجموعة واتساب", "مجموعة فيسبوك", "سرفيس / تاكسي مشترك", "نقل جامعي", "سائقون مستقلون", "أخرى"],
        )
        local_region = st.selectbox(
            "المنطقة",
            ["قطاع غزة", "شمال غزة", "مدينة غزة", "دير البلح", "خانيونس", "رفح", "الضفة الغربية", "رام الله", "نابلس", "الخليل", "جنين", "كل فلسطين", "أخرى"],
        )
        local_booking = st.text_input("طريقة الحجز أو التواصل", placeholder="هاتف، واتساب، فيسبوك، حضور مباشر...")
        local_price = st.text_input("السعر أو طريقة التسعير", placeholder="مثال: حسب المسافة / سعر المقعد / تفاوض")
        local_strengths = st.text_area("نقاط القوة", placeholder="انتشار واسع، معرفة محلية، سرعة الرد...")
        local_weaknesses = st.text_area("نقاط الضعف", placeholder="لا يوجد تتبع، لا يوجد توثيق، تفاوت السعر...")
        local_source = st.text_input("رابط أو مصدر المعلومة (اختياري)")
        local_notes = st.text_area("ملاحظات إضافية (اختياري)")
        submitted = st.form_submit_button("حفظ المنافس المحلي", type="primary", use_container_width=True)
        if submitted:
            if not local_title.strip():
                st.error("اكتبي اسم المنافس أولًا.")
            else:
                from src.db import save_local_competitor
                save_local_competitor({
                    "title": local_title.strip(),
                    "competitor_type": local_type,
                    "region": local_region,
                    "booking_method": local_booking.strip(),
                    "price_info": local_price.strip(),
                    "strengths": local_strengths.strip(),
                    "weaknesses": local_weaknesses.strip(),
                    "source_url": local_source.strip(),
                    "notes": local_notes.strip(),
                })
                st.success("تم حفظ المنافس المحلي. ستجدينه في تبويب المنافسون المحفوظون.")

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

        selected_review_ids = [competitor["id"] for competitor in selected_competitors]
        statistical_reviews = list_reviews_for_competitors(selected_review_ids)
        if statistical_reviews:
            st.subheader("التحليل الإحصائي للمنافسين المختارين")
            st.caption("النتائج محسوبة من تقييمات النجوم للمراجعات المجموعة، مع فاصل ثقة 95% للمتوسط.")
            competitor_names = {item["id"]: item.get("title", "غير معروف") for item in selected_competitors}
            statistical_rows = []
            for competitor_id in selected_review_ids:
                competitor_reviews = [
                    review for review in statistical_reviews
                    if review.get("competitor_id") == competitor_id
                ]
                summary = statistical_summary(competitor_reviews)
                sentiments = sentiment_summary(competitor_reviews)
                total = max(summary["n"], 1)
                statistical_rows.append({
                    "المنافس": competitor_names.get(competitor_id, "غير معروف"),
                    "عدد التقييمات": summary["n"],
                    "المتوسط": round(summary["mean"], 2) if summary["mean"] is not None else "—",
                    "الوسيط": round(summary["median"], 2) if summary["median"] is not None else "—",
                    "الانحراف المعياري": round(summary["stdev"], 2) if summary["stdev"] is not None else "—",
                    "فاصل الثقة 95%": (
                        f"{summary['ci_low']:.2f} – {summary['ci_high']:.2f}"
                        if summary["ci_low"] is not None else "—"
                    ),
                    "سلبي %": round(sentiments["سلبي"] / total * 100, 1),
                })
            st.dataframe(pd.DataFrame(statistical_rows), use_container_width=True, hide_index=True)

            chart_col1, chart_col2 = st.columns(2)
            stats_frame = pd.DataFrame(statistical_rows)
            with chart_col1:
                st.markdown("#### مقارنة متوسط التقييم")
                if not stats_frame.empty:
                    mean_chart = px.bar(
                        stats_frame, x="المنافس", y="المتوسط", range_y=[0, 5],
                        color="المتوسط", color_continuous_scale=["#D1FAE5", "#047857"],
                        labels={"المتوسط": "المتوسط من 5", "المنافس": "المنافس"},
                    )
                    mean_chart.update_layout(showlegend=False, height=330, margin=dict(l=20, r=20, t=20, b=80))
                    st.plotly_chart(mean_chart, use_container_width=True)
            with chart_col2:
                st.markdown("#### توزيع تقييمات النجوم")
                star_rows = []
                for competitor_id in selected_review_ids:
                    title = competitor_names.get(competitor_id, "غير معروف")
                    for score in range(1, 6):
                        count = sum(
                            1 for review in statistical_reviews
                            if review.get("competitor_id") == competitor_id and review.get("score") == score
                        )
                        star_rows.append({"المنافس": title, "النجوم": f"{score} نجوم", "العدد": count})
                star_frame = pd.DataFrame(star_rows)
                if not star_frame.empty:
                    star_chart = px.bar(
                        star_frame, x="النجوم", y="العدد", color="المنافس", barmode="group",
                        labels={"النجوم": "التقييم", "العدد": "عدد المراجعات"},
                        color_discrete_sequence=["#047857", "#10B981", "#6EE7B7", "#6B7280"],
                    )
                    star_chart.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=60))
                    st.plotly_chart(star_chart, use_container_width=True)

            sentiment_rows = []
            for competitor_id in selected_review_ids:
                title = competitor_names.get(competitor_id, "غير معروف")
                counts = sentiment_summary([
                    review for review in statistical_reviews
                    if review.get("competitor_id") == competitor_id
                ])
                for sentiment, count in counts.items():
                    sentiment_rows.append({"المنافس": title, "المشاعر": sentiment, "العدد": count})
            if sentiment_rows:
                st.markdown("#### مقارنة المشاعر بين المنافسين")
                sentiment_frame = pd.DataFrame(sentiment_rows)
                sentiment_chart = px.bar(
                    sentiment_frame, x="المنافس", y="العدد", color="المشاعر", barmode="stack",
                    labels={"المنافس": "المنافس", "العدد": "عدد المراجعات", "المشاعر": "التصنيف"},
                    color_discrete_map={"إيجابي": "#10B981", "محايد": "#9CA3AF", "سلبي": "#047857"},
                )
                sentiment_chart.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=80))
                st.plotly_chart(sentiment_chart, use_container_width=True)

            overall = statistical_summary(statistical_reviews)
            overall_a, overall_b, overall_c = st.columns(3)
            overall_a.metric("متوسط التقييم العام", f"{overall['mean']:.2f}/5" if overall["mean"] is not None else "—")
            overall_b.metric("الوسيط العام", f"{overall['median']:.2f}/5" if overall["median"] is not None else "—")
            overall_c.metric("الانحراف المعياري", f"{overall['stdev']:.2f}" if overall["stdev"] is not None else "—")

        st.subheader("تحليل نقاط القوة والضعف")
        st.caption("يجمع هذا القسم بين البيانات اليدوية للمنافسين المحليين ومؤشرات المراجعات للمنافسين الرقميين.")
        swot_reviews = list_reviews_for_competitors([item["id"] for item in selected_competitors])
        for competitor in selected_competitors:
            competitor_reviews = [
                review for review in swot_reviews
                if review.get("competitor_id") == competitor["id"]
            ]
            swot = competitor_swot(competitor, competitor_reviews)
            strength_items = "".join(f"<li>{escape(item)}</li>" for item in swot["strengths"])
            weakness_items = "".join(f"<li>{escape(item)}</li>" for item in swot["weaknesses"])
            st.markdown(
                f"<div class='swot-card'><h4>{escape(str(competitor.get('title', 'غير معروف')))}</h4>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:.8rem'>"
                f"<div class='swot-col swot-strength'><h5>نقاط القوة</h5><ul>{strength_items}</ul></div>"
                f"<div class='swot-col swot-weakness'><h5>نقاط الضعف</h5><ul>{weakness_items}</ul></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

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
        st.subheader("التوصيات")
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
                recommendation_text = st.session_state["recommendations"]
                sections = split_recommendations(recommendation_text)
                st.markdown(
                    "<div class='ai-header'><h3>التوصيات</h3>"
                    "<p>خلاصة منظمة من مراجعات المنافسين لمساعدة فريق يلا سوا على ترتيب الأولويات.</p></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='ai-note'>التوصيات مبنية على النصوص المجموعة وتحتاج إلى تحقق ميداني قبل اعتماد أي قرار استثماري.</div>", unsafe_allow_html=True)
                for start in range(0, len(sections), 2):
                    card_cols = st.columns(2)
                    for card_col, section in zip(card_cols, sections[start:start + 2]):
                        with card_col:
                            card_title = escape(section["title"])
                            card_body = escape(section["body"])
                            st.markdown(
                                f"<div class='ai-card'><h4>{card_title}</h4>"
                                f"<p>{card_body}</p></div>",
                                unsafe_allow_html=True,
                            )
    else:
        st.warning("بعد جمع المراجعات ستظهر هنا العينة والإحصاءات الأولية.")

st.divider()
st.caption("يلا سوا — أداة بحث لاتخاذ قرار مبني على البيانات، وليست بديلًا عن التحقق الميداني.")
