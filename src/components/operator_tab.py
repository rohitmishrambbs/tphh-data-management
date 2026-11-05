"""
TPHH Data Management System - Block Level Operator Component
Ultra-simplified, bilingual interface tailored for Block & Panchayat Level Data Entry Operators.
"""
import streamlit as st
import polars as pl
from pathlib import Path
from typing import List
from datetime import datetime

from src.config import (
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_NAME,
    COL_FATHER,
    COL_MOBILE,
    COL_BLOCK,
    COL_GP,
    COL_CARD_STATUS_MEMBER,
    COL_FPS_OWNER,
    COL_RELATION,
    EXPORTS_DIR,
)
from src.utils.data_engine import (
    get_unique_options,
    filter_dataset,
    export_to_excel,
    export_to_csv,
)

# Friendly bilingual column mapping for operators
FRIENDLY_COLUMNS = {
    "name": "लाभार्थी का नाम (Beneficiary Name)",
    "father_guardian_name": "पिता / पति का नाम (Father/Husband Name)",
    "src_family_id": "राशन कार्ड / परिवार संख्या (Family ID)",
    "src_member_id": "सदस्य संख्या (Member ID)",
    "village_gpname": "ग्राम पंचायत (Gram Panchayat)",
    "blockname": "ब्लॉक (Block)",
    "mobileno": "मोबाइल नंबर (Mobile)",
    "card_status_member": "कार्ड स्थिति (Status)",
    "fps_ownername": "कोटेदार का नाम (Ration Dealer)",
    "relation": "संबंध (Relation)",
    "address": "पता (Address)",
}


def render_operator_tab(df: pl.DataFrame):
    """Renders the simplified Block Operator daily working interface."""
    st.markdown(
        """
        <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 14px 20px; margin-bottom: 20px;">
            <h3 style="color: #1E40AF; margin: 0; font-size: 20px;">
                🏢 ब्लॉक एवं ग्राम पंचायत ऑपरेटर पोर्टल (Operator Portal)
            </h3>
            <p style="color: #3B82F6; margin: 4px 0 0 0; font-size: 14px;">
                छूटे हुए लाभार्थियों को खोजने, सत्यापन करने एवं शिविर (Camp) सूची डाउनलोड करने हेतु सरल पोर्टल
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # STEP 1: Big Selection Bar (Block -> Panchayat -> Dealer)
    with st.container(border=True):
        st.markdown("#### 1️⃣ अपना क्षेत्र चुनें (Select Area)")
        c1, c2, c3 = st.columns(3)

        # 1. Block Selector
        all_blocks = get_unique_options(df, COL_BLOCK)
        with c1:
            selected_block = st.selectbox(
                "🏢 1. ब्लॉक चुनें (Select Block):",
                options=["-- सभी ब्लॉक (All Blocks) --"] + all_blocks,
                index=0,
                help="जिस ब्लॉक का काम करना है उसे चुनें।"
            )

        # 2. Dynamic Panchayat Selector based on Block
        if selected_block != "-- सभी ब्लॉक (All Blocks) --":
            block_filtered = df.filter(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars() == selected_block)
            available_gps = (
                block_filtered.select(pl.col(COL_GP).drop_nulls().unique())
                .to_series()
                .to_list()
            )
            available_gps = sorted([str(gp).strip() for gp in available_gps if gp and str(gp).strip()])
        else:
            block_filtered = df
            available_gps = get_unique_options(df, COL_GP)

        with c2:
            selected_gp = st.selectbox(
                "🏡 2. ग्राम पंचायत / गाँव चुनें (Select Panchayat):",
                options=["-- सभी ग्राम पंचायतें (All Panchayats) --"] + available_gps,
                index=0,
                help="गाँव या ग्राम पंचायत का चयन करें।"
            )

        # 3. Dynamic Dealer Selector
        if selected_gp != "-- सभी ग्राम पंचायतें (All Panchayats) --":
            gp_filtered = block_filtered.filter(pl.col(COL_GP).cast(pl.String).str.strip_chars() == selected_gp)
        else:
            gp_filtered = block_filtered

        dealers = (
            gp_filtered.select(pl.col(COL_FPS_OWNER).drop_nulls().unique())
            .to_series()
            .to_list()
        )
        dealers = sorted([str(d).strip() for d in dealers if d and str(d).strip()])

        with c3:
            selected_dealer = st.selectbox(
                "🏪 3. कोटेदार / डीलर (Ration Dealer - Optional):",
                options=["-- सभी कोटेदार (All Dealers) --"] + dealers,
                index=0,
            )

    # STEP 2: Quick Search Bar
    with st.container(border=True):
        st.markdown("#### 2️⃣ त्वरित खोज (Quick Beneficiary Search)")
        search_query = st.text_input(
            "लाभार्थी का नाम, पिता का नाम, मोबाइल नंबर या राशन कार्ड नंबर लिखें:",
            placeholder="उदाहरण: Ramesh, 9876543210, या परिवार आईडी...",
            help="यहाँ टाइप करते ही नीचे सूची तुरंत फ़िल्टर हो जाएगी।"
        )

    # Apply Filters
    filtered = df
    if selected_block != "-- सभी ब्लॉक (All Blocks) --":
        filtered = filtered.filter(pl.col(COL_BLOCK).cast(pl.String).str.strip_chars() == selected_block)

    if selected_gp != "-- सभी ग्राम पंचायतें (All Panchayats) --":
        filtered = filtered.filter(pl.col(COL_GP).cast(pl.String).str.strip_chars() == selected_gp)

    if selected_dealer != "-- सभी कोटेदार (All Dealers) --":
        filtered = filtered.filter(pl.col(COL_FPS_OWNER).cast(pl.String).str.strip_chars() == selected_dealer)

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        search_cols = [c for c in [COL_NAME, COL_FATHER, COL_FAMILY_ID, COL_MEMBER_ID, COL_MOBILE, COL_FPS_OWNER] if c in filtered.columns]
        exprs = [
            pl.col(c).cast(pl.String).str.to_lowercase().str.contains(q, literal=True)
            for c in search_cols
        ]
        if exprs:
            combined = exprs[0]
            for e in exprs[1:]:
                combined = combined | e
            filtered = filtered.filter(combined)

    # KPI Summary Cards for Operator
    total_count = filtered.height
    families_count = filtered[COL_FAMILY_ID].n_unique() if COL_FAMILY_ID in filtered.columns and total_count > 0 else 0
    mobiles_valid = (
        filtered.filter(
            pl.col(COL_MOBILE).is_not_null() & (pl.col(COL_MOBILE).str.len_chars() >= 10)
        ).height
        if COL_MOBILE in filtered.columns and total_count > 0
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("👥 कुल छूटे हुए लाभार्थी", f"{total_count:,}", help="इस चयन में कुल छूटे हुए व्यक्ति")
    with k2:
        st.metric("🏠 कुल परिवार", f"{families_count:,}", help="कुल राशन कार्ड / परिवार इकाइयां")
    with k3:
        st.metric("📱 मोबाइल नंबर उपलब्ध", f"{mobiles_valid:,}", help="जिनके पास 10 अंकों का वैध फोन नंबर है")
    with k4:
        st.metric("🏢 सक्रिय ब्लॉक", selected_block.replace("-- सभी ब्लॉक (All Blocks) --", "सभी ब्लॉक"))

    st.markdown("---")

    # STEP 3: Action Buttons (Download Lists)
    st.markdown("#### 3️⃣ सूची डाउनलोड करें (Download & Print)")
    
    down_col1, down_col2, _ = st.columns([1.5, 1.5, 1])

    clean_block_tag = selected_block.replace("-- सभी ब्लॉक (All Blocks) --", "All_Blocks").replace(" ", "_")
    clean_gp_tag = selected_gp.replace("-- सभी ग्राम पंचायतें (All Panchayats) --", "All_GPs").replace(" ", "_")
    filename_base = f"TPHH_{clean_block_tag}_{clean_gp_tag}"

    with down_col1:
        # Standard Excel Download
        if st.button("📥 पूरी सूची डाउनलोड करें (Excel)", type="primary", use_container_width=True):
            with st.spinner("एक्सेल फ़ाइल तैयार हो रही है..."):
                target_file = EXPORTS_DIR / f"{filename_base}.xlsx"
                # Select clean friendly columns
                active_cols = [c for c in FRIENDLY_COLUMNS.keys() if c in filtered.columns]
                out_df = filtered.select(active_cols).rename({c: FRIENDLY_COLUMNS[c] for c in active_cols})
                export_to_excel(out_df, target_file)
                st.success(f"✅ फ़ाइल तैयार हो गई: `{target_file.name}`")
                with open(target_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {target_file.name} सेव करें (Click to Save)",
                        data=f.read(),
                        file_name=target_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

    with down_col2:
        # Camp Verification Sheet Download (with extra blank signature & remark columns!)
        if st.button("📋 शिविर सत्यापन फॉर्म (Field Camp Sheet)", use_container_width=True):
            with st.spinner("शिविर फॉर्म तैयार हो रहा है..."):
                target_camp_file = EXPORTS_DIR / f"{filename_base}_Camp_Sheet.xlsx"
                camp_cols = [c for c in ["name", "father_guardian_name", "src_family_id", "village_gpname", "mobileno", "fps_ownername"] if c in filtered.columns]
                camp_df = filtered.select(camp_cols).rename({c: FRIENDLY_COLUMNS[c] for c in camp_cols})
                # Add blank columns for field worker verification
                camp_df = camp_df.with_columns([
                    pl.lit("").alias("सत्यापन स्थिति (Verified?)"),
                    pl.lit("").alias("हस्ताक्षर / अंगूठा (Sign/Thumb)"),
                    pl.lit("").alias("टिप्पणी (Remark)"),
                ])
                export_to_excel(camp_df, target_camp_file)
                st.success(f"✅ शिविर सत्यापन फ़ाइल तैयार: `{target_camp_file.name}`")
                with open(target_camp_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {target_camp_file.name} सेव करें (Click to Save)",
                        data=f.read(),
                        file_name=target_camp_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

    st.markdown("<br>", unsafe_allow_html=True)

    # STEP 4: Table View
    st.markdown(f"#### 4️⃣ लाभार्थी विवरण तालिका ({total_count:,} रिकॉर्ड)")
    
    # Table column customizer (pre-selected with friendly names)
    preview_cols = [c for c in ["name", "father_guardian_name", "src_family_id", "src_member_id", "village_gpname", "mobileno", "card_status_member", "fps_ownername"] if c in filtered.columns]
    
    display_df = filtered.select(preview_cols).rename({c: FRIENDLY_COLUMNS[c] for c in preview_cols})
    
    st.dataframe(
        display_df.head(1000).to_pandas(),
        use_container_width=True,
        height=450,
    )
    if total_count > 1000:
        st.caption(f"ℹ️ पहले 1,000 रिकॉर्ड दिखाए जा रहे हैं। पूरी {total_count:,} रिकॉर्ड की सूची ऊपर दिए गए बटन से एक्सेल में डाउनलोड करें।")
