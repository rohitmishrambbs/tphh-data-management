"""
TPHH Data Management System - Panchayat Summary Component
Renders a clear village-by-village summary for Block Operators and Officers.
"""
import streamlit as st
import polars as pl
from pathlib import Path

from src.config import (
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_BLOCK,
    COL_GP,
    COL_SHOP_ID,
    COL_FPS_OWNER,
    EXPORTS_DIR,
)
from src.utils.data_engine import get_unique_options, export_to_excel


def render_panchayat_summary_tab(df: pl.DataFrame):
    """Renders the Panchayat-level summary table for Block operators."""
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 20px; margin-bottom: 20px;">
            <h3 style="color: #0F172A; margin: 0; font-size: 20px;">
                📋 ग्राम पंचायतवार प्रगति एवं रैंकिंग रिपोर्ट (Panchayat Ranking Report)
            </h3>
            <p style="color: #64748B; margin: 4px 0 0 0; font-size: 14px;">
                देखें कि आपके ब्लॉक में किस ग्राम पंचायत में सबसे अधिक लाभार्थी छूटे हुए हैं ताकि वहां पहले शिविर लगाया जा सके।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_blocks = get_unique_options(df, COL_BLOCK)

    b_col1, _ = st.columns([2, 2])
    with b_col1:
        chosen_block = st.selectbox(
            "🏢 अपना ब्लॉक चुनें (Select Your Block):",
            options=["-- सभी ब्लॉक (All Blocks) --"] + all_blocks,
            index=1 if all_blocks else 0,
            key="panchayat_sum_block"
        )

    block_data = df
    if chosen_block != "-- सभी ब्लॉक (All Blocks) --":
        block_data = block_data.filter(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars() == chosen_block)

    if COL_GP in block_data.columns:
        summary_report = (
            block_data.filter(pl.col(COL_GP).is_not_null())
            .with_columns(pl.col(COL_GP).cast(pl.String).str.strip_chars().alias("PanchayatName"))
            .group_by("PanchayatName")
            .agg([
                pl.len().alias("छूटे हुए लाभार्थी (Leftover Persons)"),
                pl.col(COL_FAMILY_ID).n_unique().alias("कुल परिवार (Families)"),
                pl.col(COL_FPS_OWNER).n_unique().alias("कोटेदार संख्या (Dealers)"),
            ])
            .sort("छूटे हुए लाभार्थी (Leftover Persons)", descending=True)
        )

        total_gps = summary_report.height
        total_people = block_data.height

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("कुल ग्राम पंचायतें (Total Panchayats)", f"{total_gps}")
        with m2:
            st.metric("ब्लॉक में कुल छूटे हुए लाभार्थी", f"{total_people:,}")
        with m3:
            top_gp = summary_report["PanchayatName"][0] if total_gps > 0 else "N/A"
            top_gp_count = summary_report["छूटे हुए लाभार्थी (Leftover Persons)"][0] if total_gps > 0 else 0
            st.metric("सर्वाधिक छूटा गाँव (Highest Need)", f"{top_gp} ({top_gp_count:,})")

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(summary_report.to_pandas(), use_container_width=True, height=450)

        # 1-Click Excel Download of the summary
        clean_name = chosen_block.replace("-- सभी ब्लॉक (All Blocks) --", "All_Blocks").replace(" ", "_")
        target_summary_path = EXPORTS_DIR / f"{clean_name}_Panchayat_Summary.xlsx"

        btn_c, _ = st.columns([1.5, 2])
        with btn_c:
            if st.button("📥 पूरी पंचायत रिपोर्ट डाउनलोड करें (Excel)", type="primary", use_container_width=True):
                export_to_excel(summary_report, target_summary_path)
                with open(target_summary_path, "rb") as f:
                    st.download_button(
                        label="⬇️ पंचायत रिपोर्ट सेव करें (Click to Save)",
                        data=f.read(),
                        file_name=target_summary_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
