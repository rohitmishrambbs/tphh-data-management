"""
TPHH Data Management System - Overview Component
Renders dataset KPIs, health checks, schema inspection, and interactive table preview.
"""
import streamlit as st
import polars as pl
from typing import Dict, Any

from src.utils.data_engine import get_dataset_summary


def render_overview_tab(df: pl.DataFrame, load_time: float, from_cache: bool, source_name: str):
    """Renders the comprehensive overview tab for the loaded dataset."""
    summary = get_dataset_summary(df)

    # 1. Performance and Ingestion Status Banner
    cache_badge = "⚡ Loaded from High-Speed Cache" if from_cache else "💾 Parsed from Raw Excel & Cached"
    st.markdown(
        f"""
        <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <strong style="color: #166534; font-size: 15px;">Active Dataset:</strong> 
                    <span style="color: #15803D; font-weight: 600;">{source_name}</span>
                </div>
                <div style="font-size: 13px; color: #166534;">
                    <span style="background: #DCFCE7; padding: 4px 10px; border-radius: 12px; font-weight: 500;">{cache_badge} ({load_time:.3f} seconds)</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Executive KPI Summary Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Total Records",
            value=f"{summary['total_rows']:,}",
            help="Total number of beneficiary records in this database."
        )
    with col2:
        st.metric(
            label="Unique Families",
            value=f"{summary['unique_families']:,}",
            help="Count of distinct Family IDs (src_family_id)."
        )
    with col3:
        st.metric(
            label="Blocks Covered",
            value=f"{summary['unique_blocks']}",
            help="Total administrative blocks identified in the data."
        )
    with col4:
        st.metric(
            label="FPS Shops",
            value=f"{summary['unique_shops']:,}",
            help="Total distinct Fair Price Shops (Ration Dealers)."
        )
    with col5:
        st.metric(
            label="Memory Footprint",
            value=f"{summary['memory_mb']} MB",
            help="RAM used by Polars for this entire dataset in memory."
        )

    st.markdown("---")

    # 3. Interactive Data Table Preview & Column Customizer
    st.subheader("📋 Dataset Table Preview")
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
    with ctrl_col1:
        all_columns = df.columns
        default_overview_cols = list(all_columns[:10]) if len(all_columns) > 10 else list(all_columns)
        for extra_col in ["card_status_member", "card_status_family"]:
            if extra_col in all_columns and extra_col not in default_overview_cols:
                default_overview_cols.append(extra_col)
        selected_columns = st.multiselect(
            "Visible Columns:",
            options=all_columns,
            default=default_overview_cols,
            help="Pick which columns you want to inspect in the preview table."
        )
        if not selected_columns:
            selected_columns = all_columns

    with ctrl_col2:
        quick_search = st.text_input(
            "🔎 Quick Search Preview:",
            placeholder="Type any name, ID, or phone number...",
            help="Quickly search records in this preview table."
        )

    with ctrl_col3:
        preview_limit = st.selectbox(
            "Preview Rows:",
            options=[100, 500, 1000, 5000, "All Records"],
            index=1,
            help="Limiting preview rows keeps browser scrolling ultra-smooth."
        )

    # Filter dataframe for preview
    preview_df = df.select(selected_columns)
    if quick_search and quick_search.strip():
        q = quick_search.strip().lower()
        search_exprs = [
            pl.col(c).cast(pl.String).str.to_lowercase().str.contains(q, literal=True)
            for c in selected_columns
        ]
        if search_exprs:
            combined = search_exprs[0]
            for expr in search_exprs[1:]:
                combined = combined | expr
            preview_df = preview_df.filter(combined)

    total_preview_matching = preview_df.height
    if preview_limit != "All Records":
        preview_df = preview_df.head(int(preview_limit))

    st.caption(f"Displaying **{preview_df.height:,}** of **{total_preview_matching:,}** matching records (from {summary['total_rows']:,} total).")
    
    # Display Streamlit DataFrame with interactive column sorting and resizing
    st.dataframe(
        preview_df.to_pandas(),
        use_container_width=True,
        height=450,
    )

    st.markdown("---")

    # 4. Schema & Data Quality Inspection (Expandable)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.expander("🔍 Column Schema & Data Types", expanded=False):
            schema_data = []
            for col_name, dtype in zip(df.columns, df.dtypes):
                null_count = df[col_name].null_count()
                null_pct = round((null_count / summary["total_rows"]) * 100, 1)
                schema_data.append({
                    "Column Name": col_name,
                    "Type": str(dtype),
                    "Missing Values": f"{null_count:,} ({null_pct}%)",
                })
            st.dataframe(schema_data, use_container_width=True, height=300)

    with col_right:
        with st.expander("⚠️ Missing Values & Data Health", expanded=False):
            null_counts = summary["null_counts"]
            if null_counts:
                st.write("**Columns with missing entries:**")
                missing_list = []
                for col_name, count in sorted(null_counts.items(), key=lambda x: x[1], reverse=True):
                    pct = round((count / summary["total_rows"]) * 100, 1)
                    missing_list.append({
                        "Column": col_name,
                        "Missing Rows": f"{count:,}",
                        "Missing %": f"{pct}%"
                    })
                st.dataframe(missing_list, use_container_width=True, height=300)
            else:
                st.success("✅ Excellent! No missing values detected in this dataset.")

