import pandas as pd
import numpy as np



SECTOR_ALIASES = {
    "renewable energy": "Renewables",
    "renewables": "Renewables",
    
}


def drop_duplicate_header_rows(
    df: pd.DataFrame,
    min_matches: int = 2
) -> pd.DataFrame:
    """
    Remove rows that are accidental re-imported header rows, i.e. rows
    where a cell's value equals its own column name.

    Checks every column instead of just one, so it still catches the
    row even if a future re-import doesn't duplicate every column
    identically (min_matches lets you require the header text to
    reappear in at least N columns before treating it as a real
    duplicate-header row, rather than a coincidental single match).
    """
    if df.empty:
        return df.copy()

    match_counts = pd.Series(0, index=df.index)
    for col in df.columns:
        match_counts += (
            df[col].astype("string").str.strip() == col
        ).fillna(False)

    return df[match_counts < min_matches].copy()


def normalize_sector_column(
    df: pd.DataFrame,
    column: str
) -> pd.DataFrame:
    """Map known near-duplicate sector spellings to a single canonical name."""
    if column not in df.columns:
        return df

    cleaned = df.copy()
    cleaned[column] = (
        cleaned[column]
        .astype("string")
        .str.strip()
        .apply(
            lambda v: SECTOR_ALIASES.get(v.casefold(), v)
            if pd.notna(v) else v
        )
    )
    return cleaned


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from text columns while preserving missing values."""
    cleaned = df.copy()
    for col in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[col] = cleaned[col].apply(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        cleaned[col] = cleaned[col].replace("", np.nan)
    return cleaned


def clean_numeric_columns(
    df: pd.DataFrame,
    columns: list[str]
) -> pd.DataFrame:
    """Convert specified columns to numeric while preserving missing values."""
    cleaned = df.copy()
    for col in columns:
        if col in cleaned.columns:
            cleaned[col] = (
                cleaned[col]
                .astype("string")
                .str.replace(",", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.strip()
            )
            cleaned[col] = pd.to_numeric(
                cleaned[col],
                errors="coerce"
            )
    return cleaned


def clean_date_columns(
    df: pd.DataFrame,
    columns: list[str]
) -> pd.DataFrame:
    """Convert specified columns to datetime while preserving invalid/missing values."""
    cleaned = df.copy()
    for col in columns:
        if col in cleaned.columns:
            cleaned[col] = pd.to_datetime(
                cleaned[col],
                errors="coerce"
            )
    return cleaned


def clean_deals_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize Deal Funnel data for BI analysis."""
    if df.empty:
        return df.copy()

    cleaned = df.copy()

    # Remove accidental duplicate header rows (checks all columns now)
    cleaned = drop_duplicate_header_rows(cleaned)

    # Clean text columns
    cleaned = clean_text_columns(cleaned)

    # Normalize near-duplicate sector spellings
    cleaned = normalize_sector_column(cleaned, "Sector/service")

    # Convert monetary values
    cleaned = clean_numeric_columns(
        cleaned,
        ["Masked Deal value"]
    )

    # Convert dates
    cleaned = clean_date_columns(
        cleaned,
        [
            "Close Date (A)",
            "Tentative Close Date",
            "Created Date"
        ]
    )

    return cleaned


def clean_work_orders_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize Work Order Tracker data for BI analysis."""
    if df.empty:
        return df.copy()

    cleaned = df.copy()

    # Remove accidental duplicate header rows (checks all columns now)
    cleaned = drop_duplicate_header_rows(cleaned)

    # Clean text columns
    cleaned = clean_text_columns(cleaned)

    # Normalize near-duplicate sector spellings
    cleaned = normalize_sector_column(cleaned, "Sector")

    # Convert financial columns
    money_cols = [
        "Amount in Rupees (Excl of GST) (Masked)",
        "Amount in Rupees (Incl of GST) (Masked)",
        "Billed Value in Rupees (Excl of GST.) (Masked)",
        "Billed Value in Rupees (Incl of GST.) (Masked)",
        "Collected Amount in Rupees (Incl of GST.) (Masked)",
        "Amount to be billed in Rs. (Exl. of GST) (Masked)",
        "Amount to be billed in Rs. (Incl. of GST) (Masked)",
        "Amount Receivable (Masked)"
    ]
    cleaned = clean_numeric_columns(
        cleaned,
        money_cols
    )

    # Convert dates
    date_cols = [
        "Data Delivery Date",
        "Date of PO/LOI",
        "Probable Start Date",
        "Probable End Date",
        "Last invoice date"
    ]
    cleaned = clean_date_columns(
        cleaned,
        date_cols
    )

    return cleaned