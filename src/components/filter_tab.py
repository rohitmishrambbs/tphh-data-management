"""
TPHH Data Management System - Multi-Level Filter & Search Component
High-performance multi-criteria filtering and instant search powered by Polars.
"""
import streamlit as st
import polars as pl
from pathlib import Path
from typing import List

from src.config import (
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_NAME,
    COL_FATHER,
    COL_MOBILE,
    COL_BLOCK,
    COL_GP,
    COL_DISTRICT,
    COL_RURAL_URBAN,
    COL_CARD_STATUS_FAMILY,
    COL_CARD_STATUS_MEMBER,
    COL_FPS_OWNER,
    SEARCH_COLUMNS,
    EXPORTS_DIR,
)
from src.utils.data_engine import (
    get_unique_options,
    filter_dataset,
    export_to_excel,
    export_to_csv,
)


def render_filter_tab(df: pl.DataFrame):
    """Renders the advanced search and multi-level filtering dashboard."""
    st.markdown("### 🔍 Advanced Multi-Level Filter & Search")
    st.write(
        f"Drill down across {df.height:,} records using administrative hierarchies, card statuses, and instant multi-column search."
    )

    # 1. Filter Selection Section
    with st.expander("⚙️ Filter Criteria & Search Panel", expanded=True):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)

        # Available Blocks
        all_blocks = get_unique_options(df, COL_BLOCK)
        with fcol1:
            selected_blocks = st.multiselect(
                "🏢 Select Block(s):",
                options=all_blocks,
                default=[],
                help="Filter beneficiaries belonging to specific administrative blocks."
            )

        # Dynamic Panchayats (filtered by selected blocks if any)
        if selected_blocks:
            available_gps = (
                df.filter(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars().is_in(selected_blocks))
                .select(pl.col(COL_GP).drop_nulls().unique())
                .to_series()
                .to_list()
            )
            available_gps = sorted([str(gp).strip() for gp in available_gps if gp and str(gp).strip()])
        else:
            available_gps = get_unique_options(df, COL_GP)

        with fcol2:
            selected_gps = st.multiselect(
                "🏡 Select Gram Panchayat / Village:",
                options=available_gps[:300],
                default=[],
                help="Hierarchically filtered based on selected Block(s)."
            )

        with fcol3:
            raw_member_statuses = get_unique_options(df, COL_CARD_STATUS_MEMBER)
            # Prioritize "Approved" and "Not Applied" at the top of the filter options
            priority_opts = [s for s in ["Approved", "Not Applied"] if s in raw_member_statuses]
            other_opts = [s for s in raw_member_statuses if s not in priority_opts]
            member_card_statuses = priority_opts + other_opts

            selected_member_card_status = st.multiselect(
                "🪪 Member Card Status (Approved / Not Applied):",
                options=member_card_statuses,
                default=[],
                help="Filter by individual Member Card Status. Blank entries are categorized as 'Not Applied'."
            )

        with fcol4:
            card_statuses = get_unique_options(df, COL_CARD_STATUS_FAMILY)
            selected_card_status = st.multiselect(
                "💳 Family Card Status:",
                options=card_statuses,
                default=[],
                help="Filter by family-level Ayushman / scheme card status."
            )

        fcol5, fcol6, fcol7 = st.columns([1, 1, 2])
        with fcol5:
            rural_urban_opts = get_unique_options(df, COL_RURAL_URBAN)
            selected_rural_urban = st.multiselect(
                "🏙️ Area Type:",
                options=rural_urban_opts,
                default=[],
                help="R = Rural, U = Urban."
            )

        with fcol6:
            # Check if mobile_validity_status exists (from cleaning tab)
            if "mobile_validity_status" in df.columns:
                phone_statuses = get_unique_options(df, "mobile_validity_status")
                selected_phone_status = st.multiselect(
                    "📱 Mobile Status:",
                    options=phone_statuses,
                    default=[],
                    help="Filter by mobile number validity (10-digit vs dummy/missing)."
                )
            else:
                selected_phone_status = []
                st.caption("ℹ️ *Mobile validation status available after running Cleaning tab.*")

        with fcol7:
            search_query = st.text_input(
                "🔎 Free-Text Search (Name, Family ID, Member ID, Mobile, Dealer):",
                value="",
                placeholder="Type name, ID number, or phone...",
                help="Instantly matches across all primary identifier columns."
            )

    # 2. Apply Filters using Polars Engine
    active_filters = {}
    if selected_blocks:
        active_filters[COL_BLOCK] = selected_blocks
    if selected_gps:
        active_filters[COL_GP] = selected_gps
    if selected_member_card_status:
        active_filters[COL_CARD_STATUS_MEMBER] = selected_member_card_status
    if selected_card_status:
        active_filters[COL_CARD_STATUS_FAMILY] = selected_card_status
    if selected_rural_urban:
        active_filters[COL_RURAL_URBAN] = selected_rural_urban
    if selected_phone_status and "mobile_validity_status" in df.columns:
        active_filters["mobile_validity_status"] = selected_phone_status

    filtered_df = filter_dataset(
        df=df,
        active_filters=active_filters,
        search_query=search_query,
    )

    # 3. Dynamic Filter KPI Metrics Bar
    total_records = df.height
    filtered_records = filtered_df.height
    pct_remaining = round((filtered_records / total_records) * 100, 2) if total_records > 0 else 0

    not_applied_count = (
        filtered_df.filter(pl.col(COL_CARD_STATUS_MEMBER) == "Not Applied").height
        if COL_CARD_STATUS_MEMBER in filtered_df.columns and filtered_records > 0
        else 0
    )
    pending_count = (
        filtered_df.filter(pl.col(COL_CARD_STATUS_MEMBER).is_in(["P", "S", "Disable", "D"])).height
        if COL_CARD_STATUS_MEMBER in filtered_df.columns and filtered_records > 0
        else 0
    )
    unique_families = filtered_df[COL_FAMILY_ID].n_unique() if COL_FAMILY_ID in filtered_df.columns and filtered_records > 0 else 0
    unique_dealers = filtered_df[COL_FPS_OWNER].n_unique() if COL_FPS_OWNER in filtered_df.columns and filtered_records > 0 else 0

    st.markdown("#### 📊 Filter Results Summary")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(
            "Matching Beneficiaries",
            f"{filtered_records:,}",
            delta=f"{pct_remaining}% of database",
            help="Total individuals matching your search and filter criteria."
        )
    with k2:
        st.metric(
            "Not Applied",
            f"{not_applied_count:,}",
            help="Beneficiaries with 'Not Applied' status in the filtered view."
        )
    with k3:
        st.metric(
            "Other Pending / Status",
            f"{pending_count:,}",
            help="Beneficiaries with other pending/special status (P, S, Disable, D)."
        )
    with k4:
        st.metric(
            "Distinct Families",
            f"{unique_families:,}",
            help="Total distinct family units in the filtered subset."
        )
    with k5:
        st.metric(
            "Ration Dealers / Shops",
            f"{unique_dealers:,}",
            help="Distinct Fair Price Shop dealers servicing these records."
        )

    st.markdown("---")

    # 4. Filtered Table View & Export Controls
    if filtered_records == 0:
        st.warning("⚠️ No records matched your current filter criteria. Try broadening your search or resetting filters.")
    else:
        table_col1, table_col2 = st.columns([3, 1])
        with table_col1:
            st.subheader(f"📋 Filtered Records ({filtered_records:,} rows)")
        with table_col2:
            row_limit_opt = st.selectbox(
                "Display Limit:",
                options=[100, 500, 1000, 5000, "All"],
                index=1,
                key="filter_row_limit",
                help="Limits browser rendering for smooth scrolling while retaining full export capability."
            )

        # Ensure card_status_member and card_status_family are included in default columns
        default_cols = list(filtered_df.columns[:10])
        for c in [COL_CARD_STATUS_MEMBER, COL_CARD_STATUS_FAMILY, COL_MOBILE]:
            if c in filtered_df.columns and c not in default_cols:
                default_cols.append(c)

        display_columns = st.multiselect(
            "Customize Table Columns:",
            options=filtered_df.columns,
            default=default_cols,
            key="filter_col_select"
        )
        if not display_columns:
            display_columns = filtered_df.columns

        display_df = filtered_df.select(display_columns)
        if row_limit_opt != "All":
            display_df = display_df.head(int(row_limit_opt))

        st.dataframe(
            display_df.to_pandas(),
            use_container_width=True,
            height=420,
        )

        # 5. One-Click Export of Filtered Results
        st.markdown("#### 💾 Export Filtered Records")
        exp_c1, exp_c2, _ = st.columns([1.5, 1.5, 2])

        with exp_c1:
            if st.button("📥 Download Filtered as CSV", key="btn_filter_csv", use_container_width=True):
                csv_path = EXPORTS_DIR / f"tphh_filtered_{filtered_records}_rows.csv"
                export_to_csv(filtered_df, csv_path)
                st.success(f"Saved `{csv_path.name}` in `data/exports/`")

        with exp_c2:
            if st.button("📥 Download Filtered as Excel", key="btn_filter_xlsx", use_container_width=True):
                with st.spinner("Generating memory-optimized Excel file..."):
                    xlsx_path = EXPORTS_DIR / f"tphh_filtered_{filtered_records}_rows.xlsx"
                    export_to_excel(filtered_df, xlsx_path)
                    st.success(f"Saved `{xlsx_path.name}` in `data/exports/`")
