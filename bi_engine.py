import math
import pandas as pd


class BIEngine:
    """
    Business Intelligence calculation layer.

    This class performs deterministic calculations on cleaned data.
    It does not call the LLM and does not modify the source DataFrames.
    """

    def __init__(self, deals_df: pd.DataFrame, wo_df: pd.DataFrame):
        self.deals_df = deals_df
        self.wo_df = wo_df

    @staticmethod
    def _filter_by_sector(
        df: pd.DataFrame,
        sector: str,
        column: str
    ) -> pd.DataFrame:
        """Filter a DataFrame by sector without changing the original data."""

        if not sector or column not in df.columns:
            return df.copy()

        sector_value = str(sector).strip().casefold()

        return df[
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
            == sector_value
        ].copy()

    @staticmethod
    def _safe_percentage(
        numerator: float,
        denominator: float
    ):
        """
        Calculate a percentage safely.

        Returns None when the denominator is zero,
        missing, NaN or infinite.
        """

        if numerator is None or denominator is None:
            return None

        try:
            numerator = float(numerator)
            denominator = float(denominator)
        except (TypeError, ValueError):
            return None

        if (
            not math.isfinite(numerator)
            or not math.isfinite(denominator)
            or denominator <= 0
        ):
            return None

        return round((numerator / denominator) * 100, 2)

    @staticmethod
    def _safe_distribution(
        series: pd.Series
    ) -> dict:
        """
        Convert a pandas Series into a JSON-safe distribution.

        Missing values are represented as 'Unknown'.
        Counts are converted to normal Python integers.
        """

        if series is None:
            return {}

        cleaned = series.copy()

        cleaned = cleaned.astype(object).where(
            cleaned.notna(),
            "Unknown"
        )

        cleaned = cleaned.astype(str).str.strip()

        cleaned = cleaned.replace(
            {
                "": "Unknown",
                "nan": "Unknown",
                "NaN": "Unknown",
                "None": "Unknown",
            }
        )

        counts = cleaned.value_counts(dropna=False)

        return {
            str(key): int(value)
            for key, value in counts.items()
        }

    @staticmethod
    def _safe_number(value) -> float:
        """
        Convert a value into a JSON-safe float.

        NaN and infinity become 0.0.
        """

        try:
            value = float(value)

            if not math.isfinite(value):
                return 0.0

            return value

        except (TypeError, ValueError):
            return 0.0

    def get_pipeline_health(
        self,
        sector: str = None
    ) -> dict:
        """
        Calculate sales pipeline metrics with explicit
        data-quality caveats.
        """

        df = self._filter_by_sector(
            self.deals_df,
            sector,
            "Sector/service"
        )

        total_deals = len(df)

        val_col = "Masked Deal value"

        # --------------------------------------------------
        # Deal values
        # --------------------------------------------------

        if val_col in df.columns:

            numeric_values = pd.to_numeric(
                df[val_col],
                errors="coerce"
            )

            known_values = numeric_values.dropna()

            total_recorded_deal_value = self._safe_number(
                known_values.sum()
            )

            missing_value_count = int(
                numeric_values.isna().sum()
            )

        else:

            total_recorded_deal_value = 0.0
            missing_value_count = total_deals

        # --------------------------------------------------
        # Stage distribution
        # --------------------------------------------------

        if "Deal Stage" in df.columns:

            stage_distribution = self._safe_distribution(
                df["Deal Stage"]
            )

        else:

            stage_distribution = {}

        # --------------------------------------------------
        # Status distribution
        # --------------------------------------------------

        if "Deal Status" in df.columns:

            status_distribution = self._safe_distribution(
                df["Deal Status"]
            )

        else:

            status_distribution = {}

        # --------------------------------------------------
        # Won / Lost counts
        # --------------------------------------------------

        won_deals = 0
        lost_deals = 0

        if "Deal Status" in df.columns:

            status = (
                df["Deal Status"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.casefold()
            )

            won_deals = int(
                (status == "won").sum()
            )

            lost_deals = int(
                (status == "lost").sum()
            )

        # --------------------------------------------------
        # Data quality caveats
        # --------------------------------------------------

        caveats = []

        if missing_value_count > 0:

            caveats.append(
                f"{missing_value_count} out of {total_deals} "
                "deals have missing deal values."
            )

        if "Deal Stage" not in df.columns:

            caveats.append(
                "Deal Stage is unavailable in the source data."
            )

        if "Deal Status" not in df.columns:

            caveats.append(
                "Deal Status is unavailable in the source data."
            )

        # --------------------------------------------------
        # Final pipeline result
        # --------------------------------------------------

        return {
            "sector": sector or "All Sectors",
            "total_deals": int(total_deals),
            "total_recorded_deal_value_inr": (
                total_recorded_deal_value
            ),
            "won_deals": int(won_deals),
            "lost_deals": int(lost_deals),
            "status_distribution": status_distribution,
            "stage_distribution": stage_distribution,
            "data_caveats": caveats,
        }

    def get_financial_execution_summary(
        self,
        sector: str = None
    ) -> dict:
        """
        Calculate contracted, billed, collected and
        outstanding values from Work Orders.
        """

        df = self._filter_by_sector(
            self.wo_df,
            sector,
            "Sector"
        )

        total_orders = len(df)

        contract_col = (
            "Amount in Rupees (Incl of GST) (Masked)"
        )

        billed_col = (
            "Billed Value in Rupees (Incl of GST.) (Masked)"
        )

        collected_col = (
            "Collected Amount in Rupees (Incl of GST.) (Masked)"
        )

        # --------------------------------------------------
        # Safe numeric sum
        # --------------------------------------------------

        def safe_sum(column: str) -> float:

            if column not in df.columns:
                return 0.0

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            total = numeric_values.sum(
                skipna=True
            )

            return self._safe_number(total)

        # --------------------------------------------------
        # Financial totals
        # --------------------------------------------------

        total_contracted = safe_sum(
            contract_col
        )

        total_billed = safe_sum(
            billed_col
        )

        total_collected = safe_sum(
            collected_col
        )

        # Outstanding amount based on
        # recorded billed and collected values.
        outstanding = self._safe_number(
            total_billed - total_collected
        )

        # --------------------------------------------------
        # Percentages
        # --------------------------------------------------

        billing_percentage = self._safe_percentage(
            total_billed,
            total_contracted
        )

        collection_percentage = self._safe_percentage(
            total_collected,
            total_billed
        )

        # --------------------------------------------------
        # Missing-value counts
        # --------------------------------------------------

        missing_contract = (
            int(
                pd.to_numeric(
                    df[contract_col],
                    errors="coerce"
                ).isna().sum()
            )
            if contract_col in df.columns
            else total_orders
        )

        missing_billed = (
            int(
                pd.to_numeric(
                    df[billed_col],
                    errors="coerce"
                ).isna().sum()
            )
            if billed_col in df.columns
            else total_orders
        )

        missing_collected = (
            int(
                pd.to_numeric(
                    df[collected_col],
                    errors="coerce"
                ).isna().sum()
            )
            if collected_col in df.columns
            else total_orders
        )

        # --------------------------------------------------
        # Execution status distribution
        # --------------------------------------------------

        if "Execution Status" in df.columns:

            execution_statuses = self._safe_distribution(
                df["Execution Status"]
            )

        else:

            execution_statuses = {}

        # --------------------------------------------------
        # Data quality caveats
        # --------------------------------------------------

        caveats = []

        if missing_contract > 0:

            caveats.append(
                f"{missing_contract} work orders have missing "
                "contracted amounts."
            )

        if missing_billed > 0:

            caveats.append(
                f"{missing_billed} work orders have missing "
                "billed amounts."
            )

        if missing_collected > 0:

            caveats.append(
                f"{missing_collected} work orders have missing "
                "collected amounts."
            )

        if contract_col not in df.columns:

            caveats.append(
                "Contracted amount is unavailable "
                "in the source data."
            )

        if billed_col not in df.columns:

            caveats.append(
                "Billed amount is unavailable "
                "in the source data."
            )

        if collected_col not in df.columns:

            caveats.append(
                "Collected amount is unavailable "
                "in the source data."
            )

        # --------------------------------------------------
        # Final financial result
        # --------------------------------------------------

        return {
            "sector": sector or "All Sectors",
            "total_work_orders": int(total_orders),
            "total_contracted_value_inr": total_contracted,
            "total_billed_value_inr": total_billed,
            "total_collected_value_inr": total_collected,
            "outstanding_billed_value_inr": outstanding,
            "billing_percentage": billing_percentage,
            "collection_percentage": collection_percentage,
            "execution_statuses": execution_statuses,
            "data_caveats": caveats,
        }