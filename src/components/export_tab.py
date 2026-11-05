"""
TPHH Data Management System - Export Center Component
Custom column filtering, multi-format exports (Excel, CSV, Parquet), and export file history.
"""
import streamlit as st
import polars as pl
from pathlib import Path
from datetime import datetime
import os
import subprocess

from src.config import (
    EXPORTS_DIR,
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_NAME,
    COL_FATHER,
    COL_MOBILE,
    COL_BLOCK,
    COL_GP,
    COL_DISTRICT,
    COL_CARD_STATUS_FAMILY,
    COL_CARD_STATUS_MEMBER,
    COL_ZERO_POVERTY,
    COL_SHOP_ID,
    COL_FPS_OWNER,
    COL_RATION_AREA,
)
from src.utils.data_engine import export_to_excel, export_to_csv


# Presets for quick column selection
COLUMN_PRESETS = {
    "Full Database (All Columns)": None,
    "Beneficiary Contact Directory": [
        COL_NAME,
        COL_FATHER,
        COL_MOBILE,
        COL_DISTRICT,
        COL_BLOCK,
        COL_GP,
        "address",
        "source_address",
        "addressasperrationcard",
    ],
    "Scheme & Card Audit List": [
        COL_FAMILY_ID,
        COL_MEMBER_ID,
        COL_NAME,
        COL_CARD_STATUS_FAMILY,
        COL_CARD_STATUS_MEMBER,
        COL_ZERO_POVERTY,
        COL_RATION_AREA,
    ],
    "Dealer & Ration Distribution": [
        COL_SHOP_ID,
        COL_FPS_OWNER,
        "block_town_name",
        COL_FAMILY_ID,
        COL_NAME,
        COL_MOBILE,
    ],
    "Custom Column Selection": [],
}


def render_export_tab(raw_df: pl.DataFrame):
    """Renders the comprehensive Export Center tab."""
    st.markdown("### 💾 Export Center & Data Publishing")
    st.write(
        "Generate custom-tailored spreadsheets, select required columns, choose your preferred format, "
        "and download securely to your computer."
    )

    # 1. Source Dataset Selection
    st.subheader("1️⃣ Select Dataset to Export")
    has_cleaned = "cleaned_df" in st.session_state
    
    source_options = ["Original Raw Dataset"]
    if has_cleaned:
        source_options.insert(0, "Cleaned Dataset (from Cleaning Tab)")

    selected_source = st.radio(
        "Choose Data Source:",
        options=source_options,
        index=0,
        horizontal=True,
        help="Select whether to export your original data or the cleaned version."
    )

    if selected_source.startswith("Cleaned"):
        export_base_df = st.session_state["cleaned_df"]
        st.caption(f"✨ Exporting **Cleaned Dataset** with {export_base_df.height:,} rows.")
    else:
        export_base_df = raw_df
        st.caption(f"📄 Exporting **Original Raw Dataset** with {export_base_df.height:,} rows.")

    st.markdown("---")

    # 2. Column Selection & Presets
    st.subheader("2️⃣ Choose Columns to Include")
    preset_col, _ = st.columns([2, 1])
    with preset_col:
        preset_choice = st.selectbox(
            "Quick Column Presets:",
            options=list(COLUMN_PRESETS.keys()),
            index=0,
            help="Choose a pre-defined set of columns or build a custom list."
        )

    all_cols = export_base_df.columns
    if preset_choice == "Full Database (All Columns)":
        chosen_columns = all_cols
    elif preset_choice == "Custom Column Selection":
        chosen_columns = st.multiselect(
            "Select specific columns:",
            options=all_cols,
            default=all_cols[:8],
        )
    else:
        preset_target = [c for c in COLUMN_PRESETS[preset_choice] if c in all_cols]
        chosen_columns = st.multiselect(
            "Selected Columns (edit if desired):",
            options=all_cols,
            default=preset_target,
        )

    if not chosen_columns:
        st.warning("Please select at least one column to export.")
        chosen_columns = all_cols

    st.caption(f"Will export **{len(chosen_columns)}** columns across **{export_base_df.height:,}** rows.")

    st.markdown("---")

    # 3. Format and Output Settings
    st.subheader("3️⃣ Format & File Name")
    cfg_col1, cfg_col2 = st.columns([1.5, 2])
    
    with cfg_col1:
        export_format = st.radio(
            "Export Format:",
            options=["Excel (.xlsx)", "CSV (.csv)", "Parquet (.parquet)"],
            index=0,
            help="Excel is formatted for spreadsheet viewers; CSV is universal; Parquet is ultra-fast and compact."
        )

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".xlsx" if "Excel" in export_format else (".csv" if "CSV" in export_format else ".parquet")
    default_filename = f"tphh_export_{timestamp_str}{ext}"

    with cfg_col2:
        custom_filename = st.text_input(
            "Export File Name:",
            value=default_filename,
            help="Name of the file to save in data/exports/ folder."
        )
        if not custom_filename.endswith(ext):
            custom_filename += ext

    # 4. Generate Export File
    st.markdown("<br>", unsafe_allow_html=True)
    exp_btn_col, folder_btn_col, _ = st.columns([1.5, 1.5, 2])

    target_path = EXPORTS_DIR / custom_filename

    with exp_btn_col:
        run_export = st.button("🚀 Generate & Export File", type="primary", use_container_width=True)

    with folder_btn_col:
        if st.button("📂 Open Exports Folder in Explorer", use_container_width=True):
            try:
                os.startfile(str(EXPORTS_DIR))
                st.success("Opened `data/exports` in Windows Explorer!")
            except Exception:
                try:
                    subprocess.Popen(["explorer.exe", str(EXPORTS_DIR)])
                except Exception as ex:
                    st.info(f"Exports are stored at: `{EXPORTS_DIR}`")

    if run_export:
        subset_df = export_base_df.select(chosen_columns)
        with st.spinner(f"Writing {subset_df.height:,} rows to {custom_filename}..."):
            if "Excel" in export_format:
                export_to_excel(subset_df, target_path)
            elif "CSV" in export_format:
                export_to_csv(subset_df, target_path)
            else:
                subset_df.write_parquet(target_path, compression="zstd")

        file_size_mb = round(target_path.stat().st_size / (1024 * 1024), 2)
        st.success(f"✅ Successfully exported **{subset_df.height:,}** records to `{custom_filename}` ({file_size_mb} MB)!")
        
        # Download button for direct in-browser download
        with open(target_path, "rb") as f:
            file_bytes = f.read()
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if "Excel" in export_format else "text/csv"
        st.download_button(
            label=f"📥 Click Here to Download `{custom_filename}` to Your PC",
            data=file_bytes,
            file_name=custom_filename,
            mime=mime_type,
            use_container_width=True,
        )

    st.markdown("---")

    # 5. Export History and File Library
    st.subheader("📁 Export History & Generated Files")
    existing_files = sorted(
        list(EXPORTS_DIR.glob("*.*")),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if existing_files:
        st.write(f"Found **{len(existing_files)}** previously exported file(s) in `data/exports/`:")
        file_records = []
        for f in existing_files:
            file_records.append({
                "File Name": f.name,
                "Format": f.suffix.upper(),
                "Size (MB)": round(f.stat().st_size / (1024 * 1024), 2),
                "Last Modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d-%m-%Y %H:%M:%S"),
            })
        st.dataframe(file_records, use_container_width=True, height=220)
    else:
        st.info("No exported files yet. Click 'Generate & Export File' above to create your first export.")

