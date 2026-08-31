import math
import pandas as pd


class BIEngine:
    """
    Business Intelligence calculation layer.

    This class performs deterministic calculations on cleaned data.
    It does not call the LLM and does not modify the source DataFrames.

    Important:
    - Pipeline and Work Order records are analyzed independently.
    - No deal-to-work-order relationship is assumed.
    - Rankings and risk signals are calculated from verified metrics.
    """

    # Status values are matched case-insensitively.
    WON_STATUS_VALUES = {"won"}
    LOST_STATUS_VALUES = {"lost", "dead"}

    def __init__(
        self,
        deals_df: pd.DataFrame,
        wo_df: pd.DataFrame
    ):
        self.deals_df = deals_df
        self.wo_df = wo_df

    # ==================================================
    # SAFE HELPERS
    # ==================================================

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

        return round(
            (numerator / denominator) * 100,
            2
        )

    @staticmethod
    def _safe_distribution(
        series: pd.Series
    ) -> dict:
        """
        Convert a pandas Series into a JSON-safe distribution.

        Missing values are represented as 'Unknown'.
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

        counts = cleaned.value_counts(
            dropna=False
        )

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

    # ==================================================
    # EXISTING PIPELINE ANALYSIS
    # ==================================================

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

        if val_col in df.columns:

            numeric_values = pd.to_numeric(
                df[val_col],
                errors="coerce"
            )

            known_values = numeric_values.dropna()

            total_recorded_deal_value = (
                self._safe_number(
                    known_values.sum()
                )
            )

            missing_value_count = int(
                numeric_values.isna().sum()
            )

        else:

            total_recorded_deal_value = 0.0
            missing_value_count = total_deals

        if "Deal Stage" in df.columns:

            stage_distribution = (
                self._safe_distribution(
                    df["Deal Stage"]
                )
            )

        else:

            stage_distribution = {}

        if "Deal Status" in df.columns:

            status_distribution = (
                self._safe_distribution(
                    df["Deal Status"]
                )
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
                status.isin(
                    self.WON_STATUS_VALUES
                ).sum()
            )

            lost_deals = int(
                status.isin(
                    self.LOST_STATUS_VALUES
                ).sum()
            )

        caveats = []

        if missing_value_count > 0:

            caveats.append(
                f"{missing_value_count} out of "
                f"{total_deals} deals have missing "
                "deal values."
            )

        if "Deal Stage" not in df.columns:

            caveats.append(
                "Deal Stage is unavailable "
                "in the source data."
            )

        if "Deal Status" not in df.columns:

            caveats.append(
                "Deal Status is unavailable "
                "in the source data."
            )

        return {
            "sector": sector or "All Sectors",
            "total_deals": int(total_deals),
            "total_recorded_deal_value_inr": (
                total_recorded_deal_value
            ),
            "won_deals": int(won_deals),
            "lost_deals": int(lost_deals),
            "status_distribution": (
                status_distribution
            ),
            "stage_distribution": (
                stage_distribution
            ),
            "data_caveats": caveats,
        }

    # ==================================================
    # EXISTING FINANCIAL ANALYSIS
    # ==================================================

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
            "Billed Value in Rupees "
            "(Incl of GST.) (Masked)"
        )

        collected_col = (
            "Collected Amount in Rupees "
            "(Incl of GST.) (Masked)"
        )

        def safe_sum(column: str) -> float:

            if column not in df.columns:
                return 0.0

            values=df[column].astype('string')

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            total = numeric_values.sum(
                skipna=True
            )

            return self._safe_number(total)

        total_contracted = safe_sum(
            contract_col
        )

        total_billed = safe_sum(
            billed_col
        )

        total_collected = safe_sum(
            collected_col
        )

        outstanding = self._safe_number(
            total_billed - total_collected
        )

        billing_percentage = (
            self._safe_percentage(
                total_billed,
                total_contracted
            )
        )

        collection_percentage = (
            self._safe_percentage(
                total_collected,
                total_billed
            )
        )

        missing_contract = (
            int(
                pd.to_numeric(
                    df[contract_col].astype('string'),
                    errors="coerce"
                ).isna().sum()
            )
            if contract_col in df.columns
            else total_orders
        )

        missing_billed = (
            int(
                pd.to_numeric(
                    df[billed_col].astype('string'),
                    errors="coerce"
                ).isna().sum()
            )
            if billed_col in df.columns
            else total_orders
        )

        missing_collected = (
            int(
                pd.to_numeric(
                    df[collected_col].astype('string'),
                    errors="coerce"
                ).isna().sum()
            )
            if collected_col in df.columns
            else total_orders
        )

        if "Execution Status" in df.columns:

            execution_statuses = (
                self._safe_distribution(
                    df["Execution Status"]
                )
            )

        else:

            execution_statuses = {}

        caveats = []

        if missing_contract > 0:

            caveats.append(
                f"{missing_contract} work orders "
                "have missing contracted amounts."
            )

        if missing_billed > 0:

            caveats.append(
                f"{missing_billed} work orders "
                "have missing billed amounts."
            )

        if missing_collected > 0:

            caveats.append(
                f"{missing_collected} work orders "
                "have missing collected amounts."
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

        return {
            "sector": sector or "All Sectors",
            "total_work_orders": int(total_orders),
            "total_contracted_value_inr": (
                total_contracted
            ),
            "total_billed_value_inr": (
                total_billed
            ),
            "total_collected_value_inr": (
                total_collected
            ),
            "outstanding_billed_value_inr": (
                outstanding
            ),
            "billing_percentage": (
                billing_percentage
            ),
            "collection_percentage": (
                collection_percentage
            ),
            "execution_statuses": (
                execution_statuses
            ),
            "data_caveats": caveats,
        }

    # ==================================================
    # NEW: CROSS-BOARD SECTOR ANALYSIS
    # ==================================================

    def get_cross_board_sector_analysis(self) -> dict:
        """
        Compare Deal Funnel and Work Order Tracker
        metrics independently for every sector.

        This method does NOT assume that a deal corresponds
        to a work order.

        It also calculates deterministic sector rankings
        and evidence-backed comparison signals.
        """

        deal_sector_column = "Sector/service"
        work_order_sector_column = "Sector"

        # --------------------------------------------------
        # Discover sectors
        # --------------------------------------------------

        deal_sectors = set()

        if deal_sector_column in self.deals_df.columns:

            deal_sectors = set(
                self.deals_df[
                    deal_sector_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .unique()
                .tolist()
            )

        work_order_sectors = set()

        if work_order_sector_column in self.wo_df.columns:

            work_order_sectors = set(
                self.wo_df[
                    work_order_sector_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .unique()
                .tolist()
            )

        all_sectors = sorted(
            deal_sectors.union(
                work_order_sectors
            ),
            key=lambda value: value.casefold()
        )

        # --------------------------------------------------
        # Build sector-level metrics
        # --------------------------------------------------

        sector_analysis = []

        for sector in all_sectors:

            pipeline = (
                self.get_pipeline_health(
                    sector=sector
                )
            )

            financial = (
                self.get_financial_execution_summary(
                    sector=sector
                )
            )

            sector_analysis.append(
                {
                    "sector": sector,

                    "pipeline": {
                        "total_deals": pipeline[
                            "total_deals"
                        ],
                        "recorded_deal_value_inr": pipeline[
                            "total_recorded_deal_value_inr"
                        ],
                        "won_deals": pipeline[
                            "won_deals"
                        ],
                        "lost_deals": pipeline[
                            "lost_deals"
                        ],
                        "status_distribution": pipeline[
                            "status_distribution"
                        ],
                        "stage_distribution": pipeline[
                            "stage_distribution"
                        ],
                    },

                    "work_orders": {
                        "total_work_orders": financial[
                            "total_work_orders"
                        ],
                        "contracted_value_inr": financial[
                            "total_contracted_value_inr"
                        ],
                        "billed_value_inr": financial[
                            "total_billed_value_inr"
                        ],
                        "collected_value_inr": financial[
                            "total_collected_value_inr"
                        ],
                        "outstanding_billed_value_inr": financial[
                            "outstanding_billed_value_inr"
                        ],
                        "billing_percentage": financial[
                            "billing_percentage"
                        ],
                        "collection_percentage": financial[
                            "collection_percentage"
                        ],
                        "execution_statuses": financial[
                            "execution_statuses"
                        ],
                    },

                    "data_caveats": (
                        pipeline["data_caveats"]
                        + financial["data_caveats"]
                    )
                }
            )

        # --------------------------------------------------
        # Sector membership gaps
        # --------------------------------------------------

        only_in_deals = sorted(
            deal_sectors - work_order_sectors,
            key=lambda value: value.casefold()
        )

        only_in_work_orders = sorted(
            work_order_sectors - deal_sectors,
            key=lambda value: value.casefold()
        )

        # --------------------------------------------------
        # Build numeric ranking helpers
        # --------------------------------------------------

        def valid_metric(
            item,
            category,
            metric
        ):
            value = (
                item
                .get(category, {})
                .get(metric)
            )

            if value is None:
                return False

            try:
                value = float(value)
                return math.isfinite(value)
            except (TypeError, ValueError):
                return False

        # --------------------------------------------------
        # Ranking utility
        # --------------------------------------------------

        def rank_sectors(
            category,
            metric,
            descending=True
        ):
            valid_items = [
                item
                for item in sector_analysis
                if valid_metric(
                    item,
                    category,
                    metric
                )
            ]

            valid_items.sort(
                key=lambda item: float(
                    item[category][metric]
                ),
                reverse=descending
            )

            return [
                {
                    "sector": item["sector"],
                    "value": item[
                        category
                    ][metric]
                }
                for item in valid_items
            ]

        pipeline_value_ranking = rank_sectors(
            "pipeline",
            "recorded_deal_value_inr",
            descending=True
        )

        deal_count_ranking = rank_sectors(
            "pipeline",
            "total_deals",
            descending=True
        )

        billing_ranking = rank_sectors(
            "work_orders",
            "billing_percentage",
            descending=True
        )

        collection_ranking = rank_sectors(
            "work_orders",
            "collection_percentage",
            descending=True
        )

        outstanding_ranking = rank_sectors(
            "work_orders",
            "outstanding_billed_value_inr",
            descending=True
        )

        work_order_count_ranking = rank_sectors(
            "work_orders",
            "total_work_orders",
            descending=True
        )

        # --------------------------------------------------
        # Helper for first / last ranking item
        # --------------------------------------------------

        def first_item(ranking):
            return ranking[0] if ranking else None

        def last_item(ranking):
            return ranking[-1] if ranking else None

        # --------------------------------------------------
        # Evidence-backed sector signals
        # --------------------------------------------------
        #
        # IMPORTANT:
        # These are descriptive signals.
        # They do NOT claim causality or conversion.
        #

        high_pipeline_low_billing = []

        high_billed_low_collection = []

        pipeline_without_work_orders = []

        work_orders_without_pipeline = []

        # Determine median values where possible.
        # Median is used instead of arbitrary hard-coded
        # thresholds so the logic adapts to changing data.

        pipeline_values = [
            float(
                item["pipeline"][
                    "recorded_deal_value_inr"
                ]
            )
            for item in sector_analysis
            if valid_metric(
                item,
                "pipeline",
                "recorded_deal_value_inr"
            )
        ]

        billing_values = [
            float(
                item["work_orders"][
                    "billing_percentage"
                ]
            )
            for item in sector_analysis
            if valid_metric(
                item,
                "work_orders",
                "billing_percentage"
            )
        ]

        billed_values = [
            float(
                item["work_orders"][
                    "billed_value_inr"
                ]
            )
            for item in sector_analysis
            if valid_metric(
                item,
                "work_orders",
                "billed_value_inr"
            )
        ]

        collection_values = [
            float(
                item["work_orders"][
                    "collection_percentage"
                ]
            )
            for item in sector_analysis
            if valid_metric(
                item,
                "work_orders",
                "collection_percentage"
            )
        ]

        pipeline_median = (
            float(
                pd.Series(
                    pipeline_values
                ).median()
            )
            if pipeline_values
            else None
        )

        billing_median = (
            float(
                pd.Series(
                    billing_values
                ).median()
            )
            if billing_values
            else None
        )

        billed_median = (
            float(
                pd.Series(
                    billed_values
                ).median()
            )
            if billed_values
            else None
        )

        collection_median = (
            float(
                pd.Series(
                    collection_values
                ).median()
            )
            if collection_values
            else None
        )

        # --------------------------------------------------
        # High pipeline + low billing
        # --------------------------------------------------

        if (
            pipeline_median is not None
            and billing_median is not None
        ):

            for item in sector_analysis:

                pipeline_value = item[
                    "pipeline"
                ].get(
                    "recorded_deal_value_inr"
                )

                billing_percentage = item[
                    "work_orders"
                ].get(
                    "billing_percentage"
                )

                if (
                    pipeline_value is not None
                    and billing_percentage is not None
                    and float(pipeline_value)
                    > pipeline_median
                    and float(billing_percentage)
                    < billing_median
                ):

                    high_pipeline_low_billing.append(
                        {
                            "sector": item[
                                "sector"
                            ],
                            "pipeline_value_inr": (
                                pipeline_value
                            ),
                            "billing_percentage": (
                                billing_percentage
                            ),
                            "signal": (
                                "Pipeline value is above "
                                "the sector median while "
                                "billing percentage is "
                                "below the sector median."
                            )
                        }
                    )

        # --------------------------------------------------
        # High billed + low collection
        # --------------------------------------------------

        if (
            billed_median is not None
            and collection_median is not None
        ):

            for item in sector_analysis:

                billed_value = item[
                    "work_orders"
                ].get(
                    "billed_value_inr"
                )

                collection_percentage = item[
                    "work_orders"
                ].get(
                    "collection_percentage"
                )

                if (
                    billed_value is not None
                    and collection_percentage is not None
                    and float(billed_value)
                    > billed_median
                    and float(collection_percentage)
                    < collection_median
                ):

                    high_billed_low_collection.append(
                        {
                            "sector": item[
                                "sector"
                            ],
                            "billed_value_inr": (
                                billed_value
                            ),
                            "collection_percentage": (
                                collection_percentage
                            ),
                            "outstanding_billed_value_inr": (
                                item["work_orders"][
                                    "outstanding_billed_value_inr"
                                ]
                            ),
                            "signal": (
                                "Billed value is above "
                                "the sector median while "
                                "collection percentage "
                                "is below the sector median."
                            )
                        }
                    )

        # --------------------------------------------------
        # Sector exists in pipeline but not WO
        # --------------------------------------------------

        for sector in only_in_deals:

            pipeline = next(
                (
                    item["pipeline"]
                    for item in sector_analysis
                    if item["sector"] == sector
                ),
                {}
            )

            pipeline_without_work_orders.append(
                {
                    "sector": sector,
                    "pipeline_deal_count": pipeline.get(
                        "total_deals",
                        0
                    ),
                    "pipeline_value_inr": pipeline.get(
                        "recorded_deal_value_inr",
                        0.0
                    ),
                    "signal": (
                        "Sector appears in the Deal "
                        "Funnel but not in the Work "
                        "Order Tracker."
                    )
                }
            )

        # --------------------------------------------------
        # Sector exists in WO but not pipeline
        # --------------------------------------------------

        for sector in only_in_work_orders:

            work_orders = next(
                (
                    item["work_orders"]
                    for item in sector_analysis
                    if item["sector"] == sector
                ),
                {}
            )

            work_orders_without_pipeline.append(
                {
                    "sector": sector,
                    "work_order_count": work_orders.get(
                        "total_work_orders",
                        0
                    ),
                    "contracted_value_inr": (
                        work_orders.get(
                            "contracted_value_inr",
                            0.0
                        )
                    ),
                    "signal": (
                        "Sector appears in the Work "
                        "Order Tracker but not in the "
                        "Deal Funnel."
                    )
                }
            )

        # --------------------------------------------------
        # Verified rankings
        # --------------------------------------------------

        rankings = {
            "pipeline_value": pipeline_value_ranking,
            "deal_count": deal_count_ranking,
            "billing_percentage": billing_ranking,
            "collection_percentage": collection_ranking,
            "outstanding_billed_value": outstanding_ranking,
            "work_order_count": work_order_count_ranking,
        }

        # --------------------------------------------------
        # Key extremes
        # --------------------------------------------------

        key_extremes = {
            "largest_pipeline_value": first_item(
                pipeline_value_ranking
            ),
            "smallest_pipeline_value": last_item(
                pipeline_value_ranking
            ),
            "most_deals": first_item(
                deal_count_ranking
            ),
            "fewest_deals": last_item(
                deal_count_ranking
            ),
            "highest_billing_percentage": first_item(
                billing_ranking
            ),
            "lowest_billing_percentage": last_item(
                billing_ranking
            ),
            "highest_collection_percentage": first_item(
                collection_ranking
            ),
            "lowest_collection_percentage": last_item(
                collection_ranking
            ),
            "largest_outstanding_billed_value": first_item(
                outstanding_ranking
            ),
            "most_work_orders": first_item(
                work_order_count_ranking
            ),
        }

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        return {
            "comparison_type": (
                "Independent sector-level comparison. "
                "No deal-to-work-order mapping is assumed."
            ),

            "sector_count": len(
                all_sectors
            ),

            "sectors": sector_analysis,

            "rankings": rankings,

            "key_extremes": key_extremes,

            "verified_signals": {
                "high_pipeline_low_billing": (
                    high_pipeline_low_billing
                ),
                "high_billed_low_collection": (
                    high_billed_low_collection
                ),
                "pipeline_without_work_orders": (
                    pipeline_without_work_orders
                ),
                "work_orders_without_pipeline": (
                    work_orders_without_pipeline
                ),
            },

            "sector_medians": {
                "pipeline_value_inr": (
                    pipeline_median
                ),
                "billing_percentage": (
                    billing_median
                ),
                "billed_value_inr": (
                    billed_median
                ),
                "collection_percentage": (
                    collection_median
                ),
            },

            "sectors_only_in_deal_funnel": (
                only_in_deals
            ),

            "sectors_only_in_work_order_tracker": (
                only_in_work_orders
            ),

            "data_caveats": [
                "Pipeline and work-order records are "
                "aggregated by sector independently.",
                "A deal cannot be assumed to correspond "
                "to a specific work order unless an explicit "
                "mapping exists in the source data.",
                "Verified signals are descriptive patterns "
                "based on the available metrics and do not "
                "establish causation."
            ]
        }