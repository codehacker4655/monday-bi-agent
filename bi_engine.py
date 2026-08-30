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
    def _safe_percentage(numerator: float, denominator: float):
        """
        Calculate a percentage safely.

        Returns None when the denominator is zero or unavailable,
        rather than incorrectly returning 0%.
        """
        if denominator is None or denominator <= 0:
            return None

        return round((numerator / denominator) * 100, 2)

    def get_pipeline_health(self, sector: str = None) -> dict:
        """
        Calculate sales pipeline metrics with explicit data-quality caveats.
        """
        df = self._filter_by_sector(
            self.deals_df,
            sector,
            "Sector/service"
        )

        total_deals = len(df)
        val_col = "Masked Deal value"

        # Recorded deal values only.
        if val_col in df.columns:
            known_values = df[val_col].dropna()
            total_recorded_deal_value = float(known_values.sum())
            missing_value_count = int(df[val_col].isna().sum())
        else:
            total_recorded_deal_value = 0.0
            missing_value_count = total_deals

        # Stage distribution.
        if "Deal Stage" in df.columns:
            stage_distribution = (
                df["Deal Stage"]
                .value_counts(dropna=False)
                .to_dict()
            )
        else:
            stage_distribution = {}

        # Status distribution.
        if "Deal Status" in df.columns:
            status_distribution = (
                df["Deal Status"]
                .value_counts(dropna=False)
                .to_dict()
            )
        else:
            status_distribution = {}

        # Useful high-level status counts.
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

            won_deals = int((status == "won").sum())
            lost_deals = int((status == "lost").sum())

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

        return {
            "sector": sector or "All Sectors",
            "total_deals": total_deals,
            "total_recorded_deal_value_inr": total_recorded_deal_value,
            "won_deals": won_deals,
            "lost_deals": lost_deals,
            "status_distribution": status_distribution,
            "stage_distribution": stage_distribution,
            "data_caveats": caveats,
        }

    def get_financial_execution_summary(
        self,
        sector: str = None
    ) -> dict:
        """
        Calculate contracted, billed, collected and outstanding values
        from Work Orders.
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

        def safe_sum(column: str) -> float:
            if column not in df.columns:
                return 0.0

            return float(df[column].sum(skipna=True))

        total_contracted = safe_sum(contract_col)
        total_billed = safe_sum(billed_col)
        total_collected = safe_sum(collected_col)

        # Outstanding amount based on recorded billed and collected values.
        outstanding = total_billed - total_collected

        billing_percentage = self._safe_percentage(
            total_billed,
            total_contracted
        )

        collection_percentage = self._safe_percentage(
            total_collected,
            total_billed
        )

        # Missing-value counts.
        missing_contract = (
            int(df[contract_col].isna().sum())
            if contract_col in df.columns
            else total_orders
        )

        missing_billed = (
            int(df[billed_col].isna().sum())
            if billed_col in df.columns
            else total_orders
        )

        missing_collected = (
            int(df[collected_col].isna().sum())
            if collected_col in df.columns
            else total_orders
        )

        # Execution status distribution.
        if "Execution Status" in df.columns:
            execution_statuses = (
                df["Execution Status"]
                .value_counts(dropna=False)
                .to_dict()
            )
        else:
            execution_statuses = {}

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
                "Contracted amount is unavailable in the source data."
            )

        if billed_col not in df.columns:
            caveats.append(
                "Billed amount is unavailable in the source data."
            )

        if collected_col not in df.columns:
            caveats.append(
                "Collected amount is unavailable in the source data."
            )

        return {
            "sector": sector or "All Sectors",
            "total_work_orders": total_orders,
            "total_contracted_value_inr": total_contracted,
            "total_billed_value_inr": total_billed,
            "total_collected_value_inr": total_collected,
            "outstanding_billed_value_inr": float(outstanding),
            "billing_percentage": billing_percentage,
            "collection_percentage": collection_percentage,
            "execution_statuses": execution_statuses,
            "data_caveats": caveats,
        }