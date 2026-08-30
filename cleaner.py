import pandas as pd
import numpy as np


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

    # Remove accidental duplicate header rows
    if "Deal Stage" in cleaned.columns:
        cleaned = cleaned[
            cleaned["Deal Stage"].astype("string").str.strip()
            != "Deal Stage"
        ]

    # Clean text columns
    cleaned = clean_text_columns(cleaned)

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

    # Clean text columns
    cleaned = clean_text_columns(cleaned)

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