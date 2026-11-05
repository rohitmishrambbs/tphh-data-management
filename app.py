"""
TPHH Data Management System
Main Streamlit Application Entrypoint
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
from src.components.overview_tab import render_overview_tab
from src.components.cleaning_tab import render_cleaning_tab
from src.components.filter_tab import render_filter_tab
from src.components.analytics_tab import render_analytics_tab
from src.components.export_tab import render_export_tab
from src.components.auth import check_authentication, render_logout_button

# 1. Page Configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Custom CSS for Enterprise Styling
st.markdown(
    """
    <style>
    /* Main container styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    /* Header typography */
    h1 {
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    /* Metric Card Customization */
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #1E3A8A !important;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #F1F5F9;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
        color: #334155;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. Access Security & PIN Verification
if not check_authentication():
    st.stop()

# 3. Sidebar - Dataset Management
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/database.png",
        width=64,
    )
    st.title("TPHH System")
    st.caption("Local Household Database Portal")
    st.markdown("---")

    st.subheader("📁 Data Source")
    data_source_mode = st.radio(
        "Select Data Mode:",
        options=["Project Dataset", "Upload New File"],
        index=0,
        help="Choose whether to load a dataset file from your project folder or upload a new one."
    )

    force_refresh = False
    active_file_path = None

    if data_source_mode == "Project Dataset":
        available_files = get_available_data_files()
        if available_files:
            file_map = {f.name: f for f in available_files}
            selected_name = st.selectbox(
                "Available Files:",
                options=list(file_map.keys()),
                index=0,
                help="Select any CSV or Excel dataset in your project folder."
            )
            active_file_path = file_map[selected_name]
            st.info(f"📄 **File:** `{active_file_path.name}`")
            file_size_mb = round(active_file_path.stat().st_size / (1024 * 1024), 2)
            st.caption(f"Original size: {file_size_mb} MB")
            force_refresh = st.button("🔄 Force Rebuild Cache", help="Re-read raw file and regenerate high-speed Parquet cache.")
        else:
            st.error("No CSV or Excel dataset files found in the project directory.")
    else:
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel:",
            type=["csv", "xlsx", "xls", "parquet"],
            help="Upload a CSV, Excel, or Parquet file."
        )
        if uploaded_file is not None:
            # Save uploaded file to data/raw/
            save_path = RAW_DATA_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            active_file_path = save_path
            st.success(f"Uploaded: `{uploaded_file.name}`")

    st.markdown("---")
    st.markdown(
        """
        ### 💡 Quick Guide
        - **High-Speed Engine**: 260k+ leftover records cached in Parquet for sub-second reload.
        - **Navigation**: Switch between tabs above to explore, clean, filter, and export.
        """
    )
    st.markdown("---")
    render_logout_button()


# 4. Header Section
st.title("🏛️ " + APP_TITLE)
st.caption(APP_SUBTITLE)


# 5. Load Active Dataset
if active_file_path and active_file_path.exists():
    try:
        # Reset cleaned_df if the user switched to a different source file or forced refresh
        if st.session_state.get("active_file_name") != active_file_path.name or force_refresh:
            st.session_state.pop("cleaned_df", None)
            st.session_state.pop("last_cleaning_audit", None)

        with st.spinner("Loading dataset into high-speed memory..."):
            df, load_time, from_cache = load_dataset(active_file_path, force_reload=force_refresh)

        # Store in session state
        st.session_state["raw_df"] = df
        st.session_state["active_file_name"] = active_file_path.name

        # Determine working dataset (original or cleaned)
        is_using_cleaned = "cleaned_df" in st.session_state
        working_df = st.session_state["cleaned_df"] if is_using_cleaned else df

        if is_using_cleaned:
            st.info("✨ **Active View:** Currently working with the **Cleaned Dataset** (cleaned in Tab 2).")

        # 6. Navigation Tabs
        tab_overview, tab_clean, tab_filter, tab_analytics, tab_export = st.tabs([
            "📊 Overview & Explorer",
            "🧹 Data Cleaning & Quality",
            "🔍 Multi-Level Search & Filter",
            "📈 Visual Analytics",
            "💾 Export Center",
        ])

        # Tab 1: Overview
        with tab_overview:
            render_overview_tab(
                df=working_df,
                load_time=load_time,
                from_cache=from_cache,
                source_name=f"{active_file_path.name} {'(Cleaned)' if is_using_cleaned else ''}",
            )

        # Tab 2: Cleaning
        with tab_clean:
            render_cleaning_tab(df=df)

        # Tab 3: Filtering
        with tab_filter:
            render_filter_tab(df=working_df)

        # Tab 4: Analytics
        with tab_analytics:
            render_analytics_tab(df=working_df)

        # Tab 5: Export
        with tab_export:
            render_export_tab(raw_df=st.session_state["raw_df"])

    except Exception as e:
        st.error(f"Error loading dataset: {str(e)}")
        st.exception(e)
else:
    st.warning("Please select or upload a dataset in the sidebar to begin.")
