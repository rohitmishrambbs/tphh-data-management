"""
TPHH Data Management System
Operator-Friendly Web Application for Block Level Data Entry Operators
"""
from pathlib import Path
import streamlit as st
import polars as pl

from src.config import (
    APP_TITLE,
    APP_SUBTITLE,
    DEFAULT_RAW_FILE,
    RAW_DATA_DIR,
    get_available_data_files,
)
from src.utils.data_engine import load_dataset
from src.components.operator_tab import render_operator_tab
from src.components.panchayat_summary_tab import render_panchayat_summary_tab
from src.components.analytics_tab import render_analytics_tab
from src.components.filter_tab import render_filter_tab
from src.components.cleaning_tab import render_cleaning_tab
from src.components.export_tab import render_export_tab
from src.components.overview_tab import render_overview_tab
from src.components.auth import check_authentication, render_logout_button

# 1. Page Configuration
st.set_page_config(
    page_title="TPHH Block Operator Portal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Custom CSS for High-Contrast, Operator-Friendly Design
st.markdown(
    """
    <style>
    /* Main container styling */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 98% !important;
    }
    /* Header typography */
    h1 {
        color: #1E3A8A;
        font-weight: 800;
        font-size: 26px !important;
        margin-bottom: 0.2rem;
    }
    /* Metric Card Customization */
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 2px solid #CBD5E1;
        padding: 12px 16px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #334155 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #1E3A8A !important;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 15px !important;
        font-weight: 700;
        background-color: #F1F5F9;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 22px;
        color: #1E293B;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
    }
    /* Big readable buttons */
    button[data-testid="baseButton-primary"] {
        background-color: #059669 !important;
        border-color: #059669 !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
    button[data-testid="baseButton-secondary"] {
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    /* Input and Selectbox borders */
    .stSelectbox > div > div {
        border: 2px solid #94A3B8 !important;
        border-radius: 8px !important;
    }
    .stTextInput > div > div > input {
        border: 2px solid #94A3B8 !important;
        border-radius: 8px !important;
        font-size: 15px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. Access Security & PIN Verification
if not check_authentication():
    st.stop()

# 3. Sidebar - Simplified for Block Operators
with st.sidebar:
    st.markdown("### 🏛️ टी.पी.एच.एच. पोर्टल")
    st.caption("ब्लॉक एवं पंचायत ऑपरेटर प्रणाली (Azamgarh)")
    st.markdown("---")

    # Simple operator instructions
    st.markdown(
        """
        #### 📌 ऑपरेटर मार्गदर्शिका:
        1. **1. ब्लॉक चुनें:** पहले टैब में अपने ब्लॉक का नाम चुनें।
        2. **2. गाँव चुनें:** अपनी ग्राम पंचायत चुनें।
        3. **3. एक्सेल डाउनलोड:** **"पूरी सूची डाउनलोड करें"** बटन दबाएं।
        """
    )
    st.markdown("---")

    force_refresh = False
    active_file_path = DEFAULT_RAW_FILE

    # Collapsible Admin Settings (so ordinary operators are not distracted)
    with st.expander("⚙️ डेटाबेस सेटिंग्स (Admin)", expanded=False):
        available_files = get_available_data_files()
        if available_files:
            file_map = {f.name: f for f in available_files}
            selected_name = st.selectbox(
                "डेटा फ़ाइल:",
                options=list(file_map.keys()),
                index=0,
            )
            active_file_path = file_map[selected_name]
            file_size_mb = round(active_file_path.stat().st_size / (1024 * 1024), 2)
            st.caption(f"आकार: {file_size_mb} MB")
            force_refresh = st.button("🔄 डेटा रिफ्रेश करें", help="Re-read raw file and regenerate cache.")

        uploaded_file = st.file_uploader(
            "नई एक्सेल/CSV जोड़ें:",
            type=["csv", "xlsx", "parquet"],
        )
        if uploaded_file is not None:
            save_path = RAW_DATA_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            active_file_path = save_path
            st.success(f"फ़ाइल लोड हो गई: `{uploaded_file.name}`")

    st.markdown("<br>", unsafe_allow_html=True)
    render_logout_button()


# 4. Header Section
st.title("🏛️ आजमगढ़ टी.पी.एच.एच. प्रबंधन पोर्टल")
st.caption("लक्ष्यित सार्वजनिक परिवार (TPHH) - छूटे हुए लाभार्थियों की सूची एवं ब्लॉक सत्यापन पोर्टल")


# 5. Load Active Dataset
if active_file_path and active_file_path.exists():
    try:
        if st.session_state.get("active_file_name") != active_file_path.name or force_refresh:
            st.session_state.pop("cleaned_df", None)
            st.session_state.pop("last_cleaning_audit", None)

        with st.spinner("डेटा लोड हो रहा है, कृपया प्रतीक्षा करें..."):
            df, load_time, from_cache = load_dataset(active_file_path, force_reload=force_refresh)

        st.session_state["raw_df"] = df
        st.session_state["active_file_name"] = active_file_path.name

        is_using_cleaned = "cleaned_df" in st.session_state
        working_df = st.session_state["cleaned_df"] if is_using_cleaned else df

        # 6. Primary Operator-Friendly Navigation Tabs
        tab_op, tab_panchayat, tab_charts, tab_advanced = st.tabs([
            "🔍 1. लाभार्थी खोज एवं सूची (Beneficiary Search)",
            "📋 2. ग्राम पंचायत रैंकिंग (Panchayat Ranking)",
            "📈 3. ब्लॉक प्रगति चार्ट (Visual Charts)",
            "⚙️ 4. अतिरिक्त उपकरण (Advanced Tools)",
        ])

        # Tab 1: Primary Working Screen for Block Operators
        with tab_op:
            render_operator_tab(df=working_df)

        # Tab 2: Village-by-Village Summary for Camp Planning
        with tab_panchayat:
            render_panchayat_summary_tab(df=working_df)

        # Tab 3: Visual Progress Charts
        with tab_charts:
            render_analytics_tab(df=working_df)

        # Tab 4: Advanced Tools (Clean, Detailed Filter, Full Export, Health Check)
        with tab_advanced:
            st.markdown("### ⚙️ अतिरिक्त व्यवस्थापक उपकरण (Advanced Administrative Tools)")
            st.caption("विस्तृत फ़िल्टरिंग, डेटा सफाई, एवं संपूर्ण डेटाबेस एक्सपोर्ट उपकरण")

            adv_sub1, adv_sub2, adv_sub3, adv_sub4 = st.tabs([
                "🔍 विस्तृत फ़िल्टर (Deep Filter)",
                "🧹 डेटा सफाई (Cleaning)",
                "💾 संपूर्ण एक्सपोर्ट (Full Export)",
                "📊 डेटाबेस स्वास्थ्य (Health & Schema)",
            ])

            with adv_sub1:
                render_filter_tab(df=working_df)

            with adv_sub2:
                render_cleaning_tab(df=df)

            with adv_sub3:
                render_export_tab(raw_df=st.session_state["raw_df"])

            with adv_sub4:
                render_overview_tab(
                    df=working_df,
                    load_time=load_time,
                    from_cache=from_cache,
                    source_name=active_file_path.name,
                )

    except Exception as e:
        st.error(f"डेटा लोड करने में त्रुटि: {str(e)}")
        st.exception(e)
else:
    st.warning("कृपया डेटा लोड करने हेतु फ़ाइल का चयन करें।")
