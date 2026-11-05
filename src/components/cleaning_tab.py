"""
TPHH Data Management System - Data Cleaning & Validation Component
Interactive tools for duplicate detection, smart imputation, text normalization, and phone validation.
"""
import streamlit as st
import polars as pl
from pathlib import Path
from typing import Tuple

from src.config import (
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_NAME,
    COL_FATHER,
    COL_MOBILE,
    COL_BLOCK,
    COL_GP,
    EXPORTS_DIR,
)
from src.utils.data_engine import export_to_excel, export_to_csv


def apply_data_cleaning(
    df: pl.DataFrame,
    fix_blocks: bool = True,
    fix_panchayats: bool = True,
    standardize_names: bool = True,
    clean_phones: bool = True,
    drop_exact_dupes: bool = True,
) -> Tuple[pl.DataFrame, dict]:
    """Applies selected cleaning operations and returns cleaned dataframe with audit stats."""
    cleaned = df
    audit = {}

    initial_rows = df.height
    audit["initial_rows"] = initial_rows

    # 1. Exact Duplicates Removal
    if drop_exact_dupes:
        cleaned = cleaned.unique()
        audit["duplicates_removed"] = initial_rows - cleaned.height
    else:
        audit["duplicates_removed"] = 0

    # 2. Smart Block Imputation (coalesce blockname with block_town_name)
    if fix_blocks and "blockname" in cleaned.columns and "block_town_name" in cleaned.columns:
        orig_null_blocks = cleaned["blockname"].null_count()
        cleaned = cleaned.with_columns(
            pl.coalesce(["blockname", "block_town_name"]).alias("blockname")
        )
        new_null_blocks = cleaned["blockname"].null_count()
        audit["blocks_resolved"] = orig_null_blocks - new_null_blocks

    # 3. Smart Panchayat/Village Imputation
    if fix_panchayats and "village_gpname" in cleaned.columns and "panchayat_tahsil_name" in cleaned.columns:
        orig_null_gp = cleaned["village_gpname"].null_count()
        cleaned = cleaned.with_columns(
            pl.coalesce(["village_gpname", "panchayat_tahsil_name"]).alias("village_gpname")
        )
        new_null_gp = cleaned["village_gpname"].null_count()
        audit["panchayats_resolved"] = orig_null_gp - new_null_gp

    # 4. Text Normalization: Strip spaces and Title Case / Upper Case
    if standardize_names:
        text_cols = [c for c in [COL_NAME, COL_FATHER, "address", "source_address", "addressasperrationcard"] if c in cleaned.columns]
        exprs = []
        for col in text_cols:
            exprs.append(
                pl.col(col)
                .cast(pl.String)
                .str.strip_chars()
                .str.to_titlecase()
                .replace("", None)
                .alias(col)
            )
        cleaned = cleaned.with_columns(exprs)
        audit["text_standardized"] = len(text_cols)

    # 5. Mobile Number Standardization & Validation
    if clean_phones and COL_MOBILE in cleaned.columns:
        orig_null_mobiles = cleaned[COL_MOBILE].null_count()
        # Strip '.0', spaces, non-digits
        cleaned = cleaned.with_columns(
            pl.col(COL_MOBILE)
            .cast(pl.String)
            .str.replace(r"\.0$", "")
            .str.strip_chars()
            .alias(COL_MOBILE)
        )
        # Flag valid 10-digit mobile numbers vs dummy / incomplete
        cleaned = cleaned.with_columns(
            pl.when(pl.col(COL_MOBILE).is_null() | (pl.col(COL_MOBILE).str.len_chars() < 10))
            .then(pl.lit("Missing/Invalid"))
            .otherwise(pl.lit("Valid 10-Digit"))
            .alias("mobile_validity_status")
        )
        audit["phones_validated"] = cleaned.height

    return cleaned, audit


def render_cleaning_tab(df: pl.DataFrame):
    """Renders the interactive Data Cleaning & Validation interface."""
    st.markdown("### 🧹 Data Quality & Automated Cleaning Center")
    st.write(
        "Standardize messy records, eliminate duplicate entries, and resolve missing administrative names "
        "across hundreds of thousands of rows locally without altering your original files."
    )

    # Overview Cards of Potential Quality Issues
    block_nulls = df["blockname"].null_count() if "blockname" in df.columns else 0
    gp_nulls = df["village_gpname"].null_count() if "village_gpname" in df.columns else 0
    mobile_nulls = df[COL_MOBILE].null_count() if COL_MOBILE in df.columns else 0
    
    # Calculate dummy mobile numbers (length < 10)
    dummy_mobiles = 0
    if COL_MOBILE in df.columns:
        dummy_mobiles = df.filter(
            pl.col(COL_MOBILE).is_not_null() & (pl.col(COL_MOBILE).str.len_chars() < 10)
        ).height

    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        st.metric("Missing Blocks", f"{block_nulls:,}", help="Rows where blockname is blank.")
    with qcol2:
        st.metric("Missing Gram Panchayats", f"{gp_nulls:,}", help="Rows where village_gpname is blank.")
    with qcol3:
        st.metric("Missing Mobiles", f"{mobile_nulls:,}", help="Rows with completely blank phone numbers.")
    with qcol4:
        st.metric("Dummy/Short Mobiles", f"{dummy_mobiles:,}", help="Phone numbers with fewer than 10 digits (e.g. 0, 1234).")

    st.markdown("---")

    # Cleaning Options Configuration
    st.subheader("⚙️ Select Cleaning Operations")
    
    c1, c2 = st.columns(2)
    with c1:
        opt_fix_blocks = st.checkbox(
            "Fix Missing Blocks (Impute from Block Town Column)",
            value=True,
            help="Fills missing blockname values using available block_town_name entries."
        )
        opt_fix_panchayats = st.checkbox(
            "Fix Missing Gram Panchayats (Impute from Tahsil Column)",
            value=True,
            help="Fills missing village_gpname values using available panchayat_tahsil_name entries."
        )
        opt_drop_dupes = st.checkbox(
            "Remove Exact Duplicate Rows",
            value=True,
            help="Deletes duplicate rows where every single column is identical."
        )

    with c2:
        opt_standardize_names = st.checkbox(
            "Standardize Text Formatting (Title Case & Trim Spaces)",
            value=True,
            help="Converts names to neat Title Case (e.g. 'ramesh kumar' -> 'Ramesh Kumar') and strips extra whitespace."
        )
        opt_clean_phones = st.checkbox(
            "Validate & Categorize Phone Numbers",
            value=True,
            help="Creates a 'mobile_validity_status' column flagging valid 10-digit numbers vs dummy/missing."
        )

    st.markdown("<br>", unsafe_allow_html=True)
    btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 3])
    
    with btn_col1:
        run_cleaning = st.button("🚀 Apply Cleaning Operations", type="primary", use_container_width=True)

    with btn_col2:
        reset_cleaning = st.button("🔄 Reset to Original Data", use_container_width=True)

    if reset_cleaning:
        if "cleaned_df" in st.session_state:
            del st.session_state["cleaned_df"]
        st.success("✅ Reset back to original uncleaned dataset.")
        st.rerun()

    # Apply Cleaning
    if run_cleaning:
        with st.spinner(f"Processing cleaning pipeline across {df.height:,} records..."):
            cleaned_df, audit = apply_data_cleaning(
                df=df,
                fix_blocks=opt_fix_blocks,
                fix_panchayats=opt_fix_panchayats,
                standardize_names=opt_standardize_names,
                clean_phones=opt_clean_phones,
                drop_exact_dupes=opt_drop_dupes,
            )
            st.session_state["cleaned_df"] = cleaned_df
            st.session_state["last_cleaning_audit"] = audit

    # Display Results if Cleaned Data is in Session State
    if "cleaned_df" in st.session_state:
        cleaned_df = st.session_state["cleaned_df"]
        audit = st.session_state.get("last_cleaning_audit", {})
        
        st.success("🎉 Cleaning pipeline completed successfully! Details below:")

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.metric("Duplicates Removed", f"{audit.get('duplicates_removed', 0):,}")
        with r2:
            st.metric("Blocks Recovered", f"{audit.get('blocks_resolved', 0):,}")
        with r3:
            st.metric("Panchayats Recovered", f"{audit.get('panchayats_resolved', 0):,}")
        with r4:
            st.metric("Total Cleaned Rows", f"{cleaned_df.height:,}")

        st.subheader("📋 Cleaned Data Preview")
        st.dataframe(cleaned_df.head(500).to_pandas(), use_container_width=True, height=400)

        # One-Click Export Options for Cleaned Data
        st.markdown("#### 💾 Quick Export Cleaned Data")
        exp_col1, exp_col2 = st.columns(2)
        
        with exp_col1:
            if st.button("📥 Export Cleaned Dataset to CSV", key="export_clean_csv"):
                out_path = EXPORTS_DIR / "tphh_cleaned_data.csv"
                export_to_csv(cleaned_df, out_path)
                st.success(f"Cleaned dataset saved to: `{out_path.name}` in `data/exports/`")

        with exp_col2:
            if st.button("📥 Export Cleaned Dataset to Excel (.xlsx)", key="export_clean_excel"):
                with st.spinner("Writing memory-optimized Excel file..."):
                    out_path = EXPORTS_DIR / "tphh_cleaned_data.xlsx"
                    export_to_excel(cleaned_df, out_path)
                    st.success(f"Cleaned Excel file saved to: `{out_path.name}` in `data/exports/`")

