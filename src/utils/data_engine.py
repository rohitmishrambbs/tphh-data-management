"""
TPHH Data Management System - Core Data Engine
High-performance ingestion, caching, filtering, and export powered by Polars.
"""
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
import polars as pl

from src.config import (
    PROCESSED_DATA_DIR,
    SEARCH_COLUMNS,
    COL_FAMILY_ID,
    COL_MEMBER_ID,
    COL_MOBILE,
    COL_DISTRICT,
    COL_BLOCK,
    COL_SHOP_ID,
    COL_CARD_STATUS_MEMBER,
)


def get_cache_path(source_file_path: Path) -> Path:
    """Return the designated Parquet cache file path for a given source spreadsheet."""
    stem = source_file_path.stem.replace(" ", "_")
    return PROCESSED_DATA_DIR / f"{stem}_cache.parquet"


def is_cache_valid(raw_path: Path, cache_path: Path) -> bool:
    """Check if a cached parquet file exists and is up-to-date with the raw spreadsheet."""
    if not cache_path.exists():
        return False
    try:
        raw_mtime = raw_path.stat().st_mtime
        cache_mtime = cache_path.stat().st_mtime
        return cache_mtime >= raw_mtime
    except Exception:
        return False


def load_dataset(file_path: Path, force_reload: bool = False) -> tuple[pl.DataFrame, float, bool]:
    """
    Loads dataset efficiently:
    1. If cached parquet exists and is up to date, loads instantly.
    2. Otherwise, parses raw CSV or Excel via Polars, normalizes strings, and caches to parquet.

    Returns:
        (DataFrame, load_time_in_seconds, is_from_cache)
    """
    t0 = time.time()
    cache_path = get_cache_path(file_path)

    # 1. Load from fast cache if valid
    if not force_reload and is_cache_valid(file_path, cache_path):
        df = pl.read_parquet(cache_path)
        if COL_CARD_STATUS_MEMBER in df.columns:
            df = df.with_columns(
                pl.col(COL_CARD_STATUS_MEMBER)
                .cast(pl.String)
                .str.strip_chars()
                .replace({"": "Not Applied", "NULL": "Not Applied", "null": "Not Applied", "None": "Not Applied"})
                .fill_null("Not Applied")
                .alias(COL_CARD_STATUS_MEMBER)
            ).filter(pl.col(COL_CARD_STATUS_MEMBER) != "Approved")
        load_time = time.time() - t0
        return df, load_time, True

    # 2. Ingest raw file using Polars
    suffix = file_path.suffix.lower()
    if suffix in [".xlsx", ".xls", ".xlsm"]:
        df = pl.read_excel(file_path, engine="calamine")
    elif suffix == ".parquet":
        df = pl.read_parquet(file_path)
    elif suffix == ".csv":
        # infer_schema_length=0 preserves leading zeros (e.g. "034368") and 24-digit IDs as String
        df = pl.read_csv(
            file_path,
            infer_schema_length=0,
            null_values=["NULL", "null", "None", "NA", ""],
            ignore_errors=True,
        )
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Standardize column names (strip whitespace)
    cleaned_col_names = [col.strip() for col in df.columns]
    df = df.rename(dict(zip(df.columns, cleaned_col_names)))

    # Clean text columns: strip spaces and convert empty or "NULL" strings to null
    string_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.String]
    if string_cols:
        strip_exprs = [
            pl.col(c)
            .str.strip_chars()
            .replace({"": None, "NULL": None, "null": None, "None": None, "NA": None})
            .alias(c)
            for c in string_cols
        ]
        df = df.with_columns(strip_exprs)

    # Clean phone numbers if present: strip '.0' from float conversions
    if COL_MOBILE in df.columns:
        df = df.with_columns(
            pl.col(COL_MOBILE)
            .cast(pl.String)
            .str.replace(r"\.0$", "")
            .str.strip_chars()
            .replace({"": None, "NULL": None, "null": None, "None": None})
            .alias(COL_MOBILE)
        )

    # Treat blank card_status_member entries as "Not Applied" and filter out Approved
    if COL_CARD_STATUS_MEMBER in df.columns:
        df = df.with_columns(
            pl.col(COL_CARD_STATUS_MEMBER)
            .cast(pl.String)
            .str.strip_chars()
            .replace({"": "Not Applied", "NULL": "Not Applied", "null": "Not Applied", "None": "Not Applied"})
            .fill_null("Not Applied")
            .alias(COL_CARD_STATUS_MEMBER)
        ).filter(pl.col(COL_CARD_STATUS_MEMBER) != "Approved")

    # Save to high-speed parquet cache
    df.write_parquet(cache_path, compression="zstd")
    load_time = time.time() - t0
    return df, load_time, False


def get_dataset_summary(df: pl.DataFrame) -> Dict[str, Any]:
    """Calculate key statistics and overview metrics for the dataset."""
    total_rows = df.height
    total_cols = df.width

    unique_families = df[COL_FAMILY_ID].n_unique() if COL_FAMILY_ID in df.columns else 0
    unique_members = df[COL_MEMBER_ID].n_unique() if COL_MEMBER_ID in df.columns else 0
    unique_districts = df[COL_DISTRICT].n_unique() if COL_DISTRICT in df.columns else 0
    unique_blocks = df[COL_BLOCK].n_unique() if COL_BLOCK in df.columns else 0
    unique_shops = df[COL_SHOP_ID].n_unique() if COL_SHOP_ID in df.columns else 0

    # Memory footprint in MB
    memory_mb = round(df.estimated_size() / (1024 * 1024), 2)

    # Null value summary per column
    null_counts = {
        col: df[col].null_count()
        for col in df.columns
        if df[col].null_count() > 0
    }

    return {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "unique_families": unique_families,
        "unique_members": unique_members,
        "unique_districts": unique_districts,
        "unique_blocks": unique_blocks,
        "unique_shops": unique_shops,
        "memory_mb": memory_mb,
        "null_counts": null_counts,
    }


def get_unique_options(df: pl.DataFrame, column: str, max_items: int = 500) -> List[str]:
    """Return sorted unique non-null values of a column for dropdowns."""
    if column not in df.columns:
        return []
    unique_vals = (
        df.select(pl.col(column).drop_nulls().unique())
        .to_series()
        .to_list()
    )
    # Convert all items to clean strings and sort alphabetically
    clean_vals = sorted([str(v).strip() for v in unique_vals if v is not None and str(v).strip()])
    return clean_vals[:max_items]


def filter_dataset(
    df: pl.DataFrame,
    active_filters: Dict[str, List[str]],
    search_query: str = "",
) -> pl.DataFrame:
    """
    High-speed multi-threaded filtering and free-text search.
    """
    filtered_df = df

    # Apply categorical filters (District, Block, Card Status, etc.)
    for col, selected_values in active_filters.items():
        if col in filtered_df.columns and selected_values:
            filtered_df = filtered_df.filter(
                pl.col(col).cast(pl.String).is_in(selected_values)
            )

    # Apply free-text search across multiple key columns
    if search_query and search_query.strip():
        query = search_query.strip().lower()
        search_exprs = []
        for col in SEARCH_COLUMNS:
            if col in filtered_df.columns:
                search_exprs.append(
                    pl.col(col).cast(pl.String).str.to_lowercase().str.contains(query, literal=True)
                )
        if search_exprs:
            combined_search = search_exprs[0]
            for expr in search_exprs[1:]:
                combined_search = combined_search | expr
            filtered_df = filtered_df.filter(combined_search)

    return filtered_df


def export_to_excel(df: pl.DataFrame, target_path: Path) -> Path:
    """
    Exports a Polars DataFrame to Excel using XlsxWriter in memory-optimized mode.
    Automatically splits across sheets if the dataset exceeds Excel's 1,000,000 row per-sheet limit.
    """
    import xlsxwriter

    MAX_EXCEL_ROWS = 1_000_000
    workbook = xlsxwriter.Workbook(
        str(target_path),
        {"constant_memory": True, "strings_to_numbers": False}
    )

    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#1E3A8A",
        "font_color": "#FFFFFF",
        "border": 1,
    })

    headers = df.columns
    total_rows = df.height

    if total_rows == 0:
        worksheet = workbook.add_worksheet("TPHH_Data")
        worksheet.write_row(0, 0, headers, header_format)
    else:
        for sheet_idx, start_row in enumerate(range(0, total_rows, MAX_EXCEL_ROWS), start=1):
            sheet_name = "TPHH_Data" if total_rows <= MAX_EXCEL_ROWS else f"TPHH_Data_Part{sheet_idx}"
            worksheet = workbook.add_worksheet(sheet_name)
            worksheet.write_row(0, 0, headers, header_format)
            chunk = df.slice(start_row, MAX_EXCEL_ROWS)
            for row_idx, row in enumerate(chunk.iter_rows(), start=1):
                worksheet.write_row(row_idx, 0, [val if val is not None else "" for val in row])

    workbook.close()
    return target_path


def export_to_csv(df: pl.DataFrame, target_path: Path) -> Path:
    """Exports a Polars DataFrame to CSV at ultra-high speed."""
    df.write_csv(target_path)
    return target_path
