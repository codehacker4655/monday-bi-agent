import math
import pandas as pd


class BIEngine:
    """
    Business Intelligence calculation layer.

    Performs deterministic calculations on cleaned data.
    Does not call the LLM and does not modify source DataFrames.
    """

    def __init__(self, deals_df: pd.DataFrame, wo_df: pd.DataFrame):
        self.deals_df = deals_df
        self.wo_df = wo_df

    # ==========================================================
    # Generic helpers
    # ==========================================================

    @staticmethod
    def _filter_by_sector(
        df: pd.DataFrame,
        sector: str,
        column: str
    ) -> pd.DataFrame:
        """Filter a DataFrame by sector without changing the original."""

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
        """Return a safe percentage or None."""

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
    def _safe_distribution(series: pd.Series) -> dict:
        """
        Convert a pandas Series into a JSON-safe distribution.
        Missing values become 'Unknown'.
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
        """Convert a value into a JSON-safe float."""

        try:
            value = float(value)

            if not math.isfinite(value):
                return 0.0

            return value

        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_sector_series(series: pd.Series) -> pd.Series:
        """
        Normalize sector names for grouping while preserving
        a readable 'Unknown' bucket.
        """

        return (
            series
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )

    # ==========================================================
    # Existing pipeline analysis
    # ==========================================================

    def get_pipeline_health(
        self,
        sector: str = None
    ) -> dict:
        """Calculate sales pipeline metrics."""

        df = self._filter_by_sector(
            self.deals_df,
            sector,
            "Sector/service"
        )

        total_deals = len(df)

        val_col = "Masked Deal value"

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

        if "Deal Stage" in df.columns:
            stage_distribution = self._safe_distribution(
                df["Deal Stage"]
            )
        else:
            stage_distribution = {}

        if "Deal Status" in df.columns:
            status_distribution = self._safe_distribution(
                df["Deal Status"]
            )
        else:
            status_distribution = {}

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

    # ==========================================================
    # Existing financial / execution analysis
    # ==========================================================

    def get_financial_execution_summary(
        self,
        sector: str = None
    ) -> dict:
        """Calculate contracted, billed, collected and outstanding."""

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

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            return self._safe_number(
                numeric_values.sum(skipna=True)
            )

        total_contracted = safe_sum(contract_col)
        total_billed = safe_sum(billed_col)
        total_collected = safe_sum(collected_col)

        outstanding = self._safe_number(
            total_billed - total_collected
        )

        billing_percentage = self._safe_percentage(
            total_billed,
            total_contracted
        )

        collection_percentage = self._safe_percentage(
            total_collected,
            total_billed
        )

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

        if "Execution Status" in df.columns:
            execution_statuses = self._safe_distribution(
                df["Execution Status"]
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

        if "Execution Status" not in df.columns:
            caveats.append(
                "Execution Status is unavailable "
                "in the source data."
            )

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

    # ==========================================================
    # NEW: Pipeline by sector
    # ==========================================================

    def get_pipeline_by_sector(self) -> dict:
        """
        Calculate pipeline metrics for every sector.

        Used for sector comparison, ranking and opportunity analysis.
        """

        if "Sector/service" not in self.deals_df.columns:

            return {
                "sectors": {},
                "ranking_by_deal_value": [],
                "ranking_by_deal_count": [],
                "data_caveats": [
                    "Sector/service is unavailable in the source data."
                ]
            }

        df = self.deals_df.copy()

        df["_sector"] = self._normalize_sector_series(
            df["Sector/service"]
        )

        value_col = "Masked Deal value"

        if value_col in df.columns:
            df["_deal_value"] = pd.to_numeric(
                df[value_col],
                errors="coerce"
            )
        else:
            df["_deal_value"] = pd.NA

        sectors = {}

        for sector_name, group in df.groupby(
            "_sector",
            dropna=False
        ):

            values = group["_deal_value"]

            sectors[str(sector_name)] = {
                "total_deals": int(len(group)),
                "total_recorded_deal_value_inr": self._safe_number(
                    values.sum(skipna=True)
                ),
                "missing_deal_value_count": int(
                    values.isna().sum()
                ),
                "won_deals": (
                    int(
                        group["Deal Status"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.casefold()
                        .eq("won")
                        .sum()
                    )
                    if "Deal Status" in group.columns
                    else 0
                ),
                "lost_deals": (
                    int(
                        group["Deal Status"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.casefold()
                        .eq("lost")
                        .sum()
                    )
                    if "Deal Status" in group.columns
                    else 0
                ),
                "stage_distribution": (
                    self._safe_distribution(
                        group["Deal Stage"]
                    )
                    if "Deal Stage" in group.columns
                    else {}
                ),
                "status_distribution": (
                    self._safe_distribution(
                        group["Deal Status"]
                    )
                    if "Deal Status" in group.columns
                    else {}
                ),
            }

        ranking_by_deal_value = sorted(
            sectors.items(),
            key=lambda item: item[1][
                "total_recorded_deal_value_inr"
            ],
            reverse=True
        )

        ranking_by_deal_count = sorted(
            sectors.items(),
            key=lambda item: item[1]["total_deals"],
            reverse=True
        )

        return {
            "sectors": sectors,
            "ranking_by_deal_value": [
                {
                    "sector": sector,
                    **metrics
                }
                for sector, metrics in ranking_by_deal_value
            ],
            "ranking_by_deal_count": [
                {
                    "sector": sector,
                    **metrics
                }
                for sector, metrics in ranking_by_deal_count
            ],
            "data_caveats": [],
        }

    # ==========================================================
    # NEW: Financial / execution by sector
    # ==========================================================

    def get_financial_by_sector(self) -> dict:
        """
        Calculate financial and execution metrics for every sector.
        """

        if "Sector" not in self.wo_df.columns:

            return {
                "sectors": {},
                "ranking_by_contracted_value": [],
                "ranking_by_collection_percentage": [],
                "data_caveats": [
                    "Sector is unavailable in the source data."
                ]
            }

        df = self.wo_df.copy()

        df["_sector"] = self._normalize_sector_series(
            df["Sector"]
        )

        contract_col = (
            "Amount in Rupees (Incl of GST) (Masked)"
        )

        billed_col = (
            "Billed Value in Rupees (Incl of GST.) (Masked)"
        )

        collected_col = (
            "Collected Amount in Rupees (Incl of GST.) (Masked)"
        )

        for col in [
            contract_col,
            billed_col,
            collected_col
        ]:

            if col in df.columns:

                df[f"_{col}"] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

            else:

                df[f"_{col}"] = pd.Series(
                    pd.NA,
                    index=df.index
                )

        sectors = {}

        for sector_name, group in df.groupby(
            "_sector",
            dropna=False
        ):

            contracted = self._safe_number(
                group[f"_{contract_col}"].sum(
                    skipna=True
                )
            )

            billed = self._safe_number(
                group[f"_{billed_col}"].sum(
                    skipna=True
                )
            )

            collected = self._safe_number(
                group[f"_{collected_col}"].sum(
                    skipna=True
                )
            )

            outstanding = self._safe_number(
                billed - collected
            )

            sectors[str(sector_name)] = {
                "total_work_orders": int(len(group)),
                "total_contracted_value_inr": contracted,
                "total_billed_value_inr": billed,
                "total_collected_value_inr": collected,
                "outstanding_billed_value_inr": outstanding,
                "billing_percentage": self._safe_percentage(
                    billed,
                    contracted
                ),
                "collection_percentage": self._safe_percentage(
                    collected,
                    billed
                ),
                "execution_statuses": (
                    self._safe_distribution(
                        group["Execution Status"]
                    )
                    if "Execution Status" in group.columns
                    else {}
                ),
                "missing_contract_count": int(
                    group[f"_{contract_col}"].isna().sum()
                ),
                "missing_billed_count": int(
                    group[f"_{billed_col}"].isna().sum()
                ),
                "missing_collected_count": int(
                    group[f"_{collected_col}"].isna().sum()
                ),
            }

        ranking_by_contracted = sorted(
            sectors.items(),
            key=lambda item: item[1][
                "total_contracted_value_inr"
            ],
            reverse=True
        )

        collection_candidates = [
            item
            for item in sectors.items()
            if item[1]["collection_percentage"] is not None
        ]

        ranking_by_collection = sorted(
            collection_candidates,
            key=lambda item: item[1][
                "collection_percentage"
            ],
            reverse=True
        )

        return {
            "sectors": sectors,
            "ranking_by_contracted_value": [
                {
                    "sector": sector,
                    **metrics
                }
                for sector, metrics in ranking_by_contracted
            ],
            "ranking_by_collection_percentage": [
                {
                    "sector": sector,
                    **metrics
                }
                for sector, metrics in ranking_by_collection
            ],
            "data_caveats": [],
        }

    # ==========================================================
    # NEW: Cross-board sector analysis
    # ==========================================================

    def get_cross_board_sector_analysis(self) -> dict:
        """
        Combine Deal Funnel and Work Order metrics by sector.

        This is the evidence layer for:
        - sector comparison
        - pipeline vs execution
        - collection risk
        - opportunity identification
        """

        pipeline = self.get_pipeline_by_sector()
        financial = self.get_financial_by_sector()

        pipeline_sectors = pipeline.get(
            "sectors",
            {}
        )

        financial_sectors = financial.get(
            "sectors",
            {}
        )

        all_sectors = sorted(
            set(pipeline_sectors.keys())
            |
            set(financial_sectors.keys())
        )

        combined = {}

        for sector in all_sectors:

            pipeline_data = pipeline_sectors.get(
                sector,
                {}
            )

            financial_data = financial_sectors.get(
                sector,
                {}
            )

            pipeline_value = self._safe_number(
                pipeline_data.get(
                    "total_recorded_deal_value_inr",
                    0
                )
            )

            contracted_value = self._safe_number(
                financial_data.get(
                    "total_contracted_value_inr",
                    0
                )
            )

            billed_value = self._safe_number(
                financial_data.get(
                    "total_billed_value_inr",
                    0
                )
            )

            collected_value = self._safe_number(
                financial_data.get(
                    "total_collected_value_inr",
                    0
                )
            )

            combined[sector] = {
                "pipeline": pipeline_data,
                "work_orders": financial_data,

                # Explicit cross-board indicators.
                "pipeline_to_contracted_value_ratio": (
                    self._safe_percentage(
                        contracted_value,
                        pipeline_value
                    )
                ),

                "pipeline_value_inr": pipeline_value,

                "contracted_value_inr": contracted_value,

                "billed_value_inr": billed_value,

                "collected_value_inr": collected_value,

                "outstanding_billed_value_inr": (
                    self._safe_number(
                        billed_value - collected_value
                    )
                ),

                "collection_percentage": (
                    financial_data.get(
                        "collection_percentage"
                    )
                ),

                "billing_percentage": (
                    financial_data.get(
                        "billing_percentage"
                    )
                ),
            }

        return {
            "sectors": combined,
            "sector_count": len(combined),
            "data_caveats": (
                pipeline.get("data_caveats", [])
                +
                financial.get("data_caveats", [])
            ),
        }