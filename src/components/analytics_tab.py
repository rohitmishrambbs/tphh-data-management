"""
TPHH Data Management System - Visual Analytics & Reports Component
Interactive Plotly charts and administrative distribution reports.
"""
import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from src.config import (
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_BLOCK,
    COL_CARD_STATUS_FAMILY,
    COL_CARD_STATUS_MEMBER,
    COL_RURAL_URBAN,
    COL_FPS_OWNER,
    COL_SHOP_ID,
    EXPORTS_DIR,
)
from src.utils.data_engine import export_to_excel, export_to_csv


def render_analytics_tab(df: pl.DataFrame):
    """Renders visual charts, distribution graphs, and aggregated reports."""
    st.markdown("### 📈 Visual Analytics & Administrative Reports")
    st.write(
        "Interactive graphical breakdowns of beneficiary counts, family sizes, card coverage, and dealer volumes."
    )

    # 1. High-Level Aggregation Metrics
    total_beneficiaries = df.height
    total_families = df[COL_FAMILY_ID].n_unique() if COL_FAMILY_ID in df.columns else 0
    avg_family_size = round(total_beneficiaries / total_families, 2) if total_families > 0 else 0
    total_blocks = df[COL_BLOCK].n_unique() if COL_BLOCK in df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Beneficiaries", f"{total_beneficiaries:,}")
    with m2:
        st.metric("Total Families", f"{total_families:,}")
    with m3:
        st.metric("Avg Family Size", f"{avg_family_size} members")
    with m4:
        st.metric("Blocks Analyzed", f"{total_blocks}")

    st.markdown("---")

    # 2. Row 1: Block Distribution & Ayushman Card Coverage
    col_chart1, col_chart2 = st.columns([1.6, 1.4])

    with col_chart1:
        st.markdown("#### 🏢 Beneficiaries by Administrative Block")
        if COL_BLOCK in df.columns:
            block_agg = (
                df.filter(pl.col(COL_BLOCK).is_not_null())
                .with_columns(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars().alias("CleanBlock"))
                .group_by("CleanBlock")
                .agg([
                    pl.len().alias("Beneficiaries"),
                    pl.col(COL_FAMILY_ID).n_unique().alias("Families")
                ])
                .sort("Beneficiaries", descending=True)
                .head(20)
            )

            fig_block = px.bar(
                block_agg.to_pandas(),
                x="Beneficiaries",
                y="CleanBlock",
                orientation="h",
                color="Beneficiaries",
                color_continuous_scale="Blues",
                labels={"CleanBlock": "Block Name", "Beneficiaries": "Beneficiaries"},
                hover_data=["Families"],
            )
            fig_block.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=10, r=10, t=10, b=10),
                height=420,
            )
            st.plotly_chart(fig_block, use_container_width=True)
        else:
            st.info("Block column not found.")

    with col_chart2:
        st.markdown("#### 💳 Ayushman / Scheme Card Coverage")
        if COL_CARD_STATUS_FAMILY in df.columns:
            card_agg = (
                df.with_columns(
                    pl.col(COL_CARD_STATUS_FAMILY).fill_null("Not Specified").alias("CardStatus")
                )
                .group_by("CardStatus")
                .len()
                .sort("len", descending=True)
            )

            fig_card = px.pie(
                card_agg.to_pandas(),
                names="CardStatus",
                values="len",
                hole=0.45,
                color_discrete_sequence=["#1E3A8A", "#0D9488", "#E2E8F0", "#F59E0B"],
            )
            fig_card.update_traces(textinfo="percent+label", pull=[0.05, 0, 0])
            fig_card.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=420,
                showlegend=False,
            )
            st.plotly_chart(fig_card, use_container_width=True)
        else:
            st.info("Card status column not found.")

    st.markdown("---")

    # 3. Row 2: Family Size Distribution & Rural vs Urban Split
    col_chart3, col_chart4 = st.columns([1.5, 1.5])

    with col_chart3:
        st.markdown("#### 👨‍👩‍👧‍👦 Family Size Distribution")
        if COL_FAMILY_ID in df.columns:
            fam_sizes = (
                df.group_by(COL_FAMILY_ID)
                .len()
                .select(
                    pl.when(pl.col("len") >= 7)
                    .then(pl.lit("7+ Members"))
                    .otherwise(pl.col("len").cast(pl.String) + " Member(s)")
                    .alias("Family_Size_Category")
                )
                .group_by("Family_Size_Category")
                .len()
                .sort("len", descending=True)
            )

            fig_fam = px.bar(
                fam_sizes.to_pandas(),
                x="Family_Size_Category",
                y="len",
                labels={"Family_Size_Category": "Family Size", "len": "Count of Families"},
                color="len",
                color_continuous_scale="Teal",
            )
            fig_fam.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=350,
            )
            st.plotly_chart(fig_fam, use_container_width=True)

    with col_chart4:
        st.markdown("#### 🏙️ Rural vs. Urban Distribution")
        if COL_RURAL_URBAN in df.columns:
            area_agg = (
                df.with_columns(
                    pl.when(pl.col(COL_RURAL_URBAN) == "R")
                    .then(pl.lit("Rural"))
                    .when(pl.col(COL_RURAL_URBAN) == "U")
                    .then(pl.lit("Urban"))
                    .otherwise(pl.lit("Unspecified"))
                    .alias("AreaLabel")
                )
                .group_by("AreaLabel")
                .len()
                .sort("len", descending=True)
            )

            fig_area = px.pie(
                area_agg.to_pandas(),
                names="AreaLabel",
                values="len",
                hole=0.4,
                color="AreaLabel",
                color_discrete_map={"Rural": "#10B981", "Urban": "#3B82F6", "Unspecified": "#94A3B8"},
            )
            fig_area.update_traces(textinfo="percent+label")
            fig_area.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=350,
                showlegend=True,
            )
            st.plotly_chart(fig_area, use_container_width=True)

    st.markdown("---")

    # 4. Top Fair Price Shops (Ration Dealers)
    st.markdown("#### 🏪 Top 15 Fair Price Shops by Beneficiary Volume")
    if COL_FPS_OWNER in df.columns:
        fps_agg = (
            df.filter(pl.col(COL_FPS_OWNER).is_not_null())
            .with_columns(pl.col(COL_FPS_OWNER).cast(pl.String).str.strip_chars().alias("DealerName"))
            .group_by("DealerName")
            .agg([
                pl.len().alias("Beneficiaries"),
                pl.col(COL_FAMILY_ID).n_unique().alias("Families"),
            ])
            .sort("Beneficiaries", descending=True)
            .head(15)
        )

        fig_fps = px.bar(
            fps_agg.to_pandas(),
            x="DealerName",
            y="Beneficiaries",
            color="Beneficiaries",
            color_continuous_scale="Purples",
            hover_data=["Families"],
            labels={"DealerName": "Dealer / FPS Owner", "Beneficiaries": "Beneficiaries Serviced"},
        )
        fig_fps.update_layout(
            xaxis={"tickangle": -45},
            margin=dict(l=10, r=10, t=10, b=50),
            height=400,
        )
        st.plotly_chart(fig_fps, use_container_width=True)

    st.markdown("---")

    # 5. Block-Level Administrative Summary Table & Report Export
    st.markdown("#### 📑 Block-Level Administrative Summary Report")
    st.write("Aggregated breakdown by block with family counts and average household density:")

    if COL_BLOCK in df.columns:
        agg_exprs = [
            pl.len().alias("Total Beneficiaries"),
            pl.col(COL_FAMILY_ID).n_unique().alias("Total Families"),
        ]
        if COL_CARD_STATUS_MEMBER in df.columns:
            agg_exprs.extend([
                (pl.col(COL_CARD_STATUS_MEMBER) == "Approved").sum().alias("Approved Cards"),
                (pl.col(COL_CARD_STATUS_MEMBER) == "Not Applied").sum().alias("Not Applied"),
            ])
        agg_exprs.append(pl.col(COL_SHOP_ID).n_unique().alias("Active FPS Shops"))

        block_report = (
            df.filter(pl.col(COL_BLOCK).is_not_null())
            .with_columns(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars().alias("Block"))
            .group_by("Block")
            .agg(agg_exprs)
            .with_columns(
                (pl.col("Total Beneficiaries") / pl.col("Total Families")).round(2).alias("Avg Family Size")
            )
            .sort("Total Beneficiaries", descending=True)
        )

        st.dataframe(block_report.to_pandas(), use_container_width=True, height=350)

        r_btn1, r_btn2, _ = st.columns([1.5, 1.5, 2])
        with r_btn1:
            if st.button("📥 Download Block Report as Excel", key="btn_rep_xlsx", use_container_width=True):
                rep_path = EXPORTS_DIR / "block_administrative_summary.xlsx"
                export_to_excel(block_report, rep_path)
                st.success(f"Report saved to `{rep_path.name}` in `data/exports/`")

        with r_btn2:
            if st.button("📥 Download Block Report as CSV", key="btn_rep_csv", use_container_width=True):
                rep_csv = EXPORTS_DIR / "block_administrative_summary.csv"
                export_to_csv(block_report, rep_csv)
                st.success(f"Report saved to `{rep_csv.name}` in `data/exports/`")

