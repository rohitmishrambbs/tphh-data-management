"""
TPHH Data Management System - Configuration
"""
from pathlib import Path
from typing import List

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

# Ensure runtime directories exist
for folder in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Default raw data file (uses raw CSV if present; automatically falls back to cached Parquet for cloud deployment)
DEFAULT_CSV_FILE = PROJECT_ROOT / "Azamgarh TPHH 02_NOV_2026.csv"
DEFAULT_PARQUET_FILE = PROCESSED_DATA_DIR / "Azamgarh_TPHH_02_NOV_2026_cache.parquet"

if DEFAULT_CSV_FILE.exists():
    DEFAULT_RAW_FILE = DEFAULT_CSV_FILE
elif DEFAULT_PARQUET_FILE.exists():
    DEFAULT_RAW_FILE = DEFAULT_PARQUET_FILE
else:
    DEFAULT_RAW_FILE = DEFAULT_CSV_FILE

# Security & Access Control for Online Deployment
DEFAULT_APP_PIN = "2026"


def get_available_data_files() -> List[Path]:
    """Discover all valid dataset files (.csv, .xlsx, .xls, .parquet) in the project root, data/raw, and data/processed."""
    valid_exts = {".csv", ".xlsx", ".xls", ".xlsm", ".parquet"}
    found = []
    # Check default file first
    if DEFAULT_RAW_FILE.exists():
        found.append(DEFAULT_RAW_FILE)
    for folder in [PROJECT_ROOT, RAW_DATA_DIR, PROCESSED_DATA_DIR]:
        if folder.exists():
            for p in sorted(folder.iterdir()):
                if p.is_file() and p.suffix.lower() in valid_exts and p not in found:
                    found.append(p)
    return found


# App Branding
APP_TITLE = "TPHH Data Management System"
APP_SUBTITLE = "Targeted Household & Leftover Beneficiary Portal (260k+ Records)"

# Important Columns in the TPHH Dataset
COL_FAMILY_ID = "src_family_id"
COL_MEMBER_ID = "src_member_id"
COL_NAME = "name"
COL_RELATION = "relation"
COL_FATHER = "father_guardian_name"
COL_RURAL_URBAN = "rural_urban_flag"
COL_DISTRICT = "district_name"
COL_BLOCK = "blockname"
COL_GP = "village_gpname"
COL_CARD_STATUS_MEMBER = "card_status_member"
COL_CARD_STATUS_FAMILY = "card_status_family"
COL_ZERO_POVERTY = "memberbelongtozeropovery"
COL_MOBILE = "mobileno"
COL_RATION_CARD_ADDRESS = "addressasperrationcard"
COL_SHOP_ID = "shopid"
COL_FPS_OWNER = "fps_ownername"
COL_RATION_AREA = "ration_area"

# Columns to prioritize in filtering dropdowns
FILTER_COLUMNS = [
    COL_DISTRICT,
    COL_BLOCK,
    COL_RURAL_URBAN,
    COL_CARD_STATUS_FAMILY,
    COL_CARD_STATUS_MEMBER,
    COL_ZERO_POVERTY,
]

# Columns to include in free-text search
SEARCH_COLUMNS = [
    COL_NAME,
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_MOBILE,
    COL_FATHER,
    COL_FPS_OWNER,
]
