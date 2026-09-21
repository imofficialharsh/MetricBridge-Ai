"""
src/engine.py
Analytical Engine & Mathematical Variance Decomposition Core.
Executes high-performance aggregations over Parquet using Polars,
computes Price-Volume-Mix (PVM) variance trees, and generates dimensional
diagnostics (Category, State, and Macro-Region).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import polars as pl

from src.schema import (
    DimensionItem,
    KPISnapshot,
    RegionPerformance,
    RootCauseReport,
    VarianceBridge,
)


class MetricEngine:
    """
    Core analytical engine operating on the columnar analytics fact table.
    Provides sub-second querying, KPI calculation, Price-Volume-Mix variance
    reconciliation, and multi-dimensional slicing.
    """

    def __init__(self, parquet_path: str = "./data/olist_analytics_fact.parquet"):
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(
                f"Analytics fact table not found at {self.parquet_path.resolve()}. "
                "Please run `python src/preprocess.py` first."
            )

    def _scan(self) -> pl.LazyFrame:
        """Returns a lazy scan over the analytical fact parquet."""
        return pl.scan_parquet(str(self.parquet_path))

    def get_available_periods(self) -> List[str]:
        """Returns a sorted list of unique year_month periods available in the dataset."""
        df = (
            self._scan()
            .select("year_month")
            .unique()
            .sort("year_month")
            .collect()
        )
        return df["year_month"].to_list()

    def compute_period_kpis(self, period_str: str) -> KPISnapshot:
        """
        Calculates foundational commercial KPIs for a single period:
        - Gross Revenue
        - Total Orders
        - Total Units
        - Average Order Value (AOV)
        - Average Realized Item Price
        - Total Freight Cost
        - Net Margin Proxy (Gross Revenue - Total Freight)
        """
        agg = (
            self._scan()
            .filter(pl.col("year_month") == period_str)
            .select([
                pl.col("gross_revenue").sum().alias("total_revenue"),
                pl.col("order_id").n_unique().alias("total_orders"),
                pl.len().alias("total_units"),
                pl.col("freight_cost").sum().alias("total_freight"),
            ])
            .collect()
        )

        if len(agg) == 0 or agg["total_orders"][0] == 0:
            return KPISnapshot(
                period=period_str,
                total_revenue=0.0,
                total_orders=0,
                total_units=0,
                aov=0.0,
                avg_item_price=0.0,
                total_freight=0.0,
                net_margin_proxy=0.0,
            )

        total_rev = float(agg["total_revenue"][0] or 0.0)
        total_orders = int(agg["total_orders"][0] or 0)
        total_units = int(agg["total_units"][0] or 0)
        total_freight = float(agg["total_freight"][0] or 0.0)

        aov = (total_rev / total_orders) if total_orders > 0 else 0.0
        avg_item_price = (total_rev / total_units) if total_units > 0 else 0.0
        net_margin_proxy = total_rev - total_freight

        return KPISnapshot(
            period=period_str,
            total_revenue=round(total_rev, 2),
            total_orders=total_orders,
            total_units=total_units,
            aov=round(aov, 2),
            avg_item_price=round(avg_item_price, 2),
            total_freight=round(total_freight, 2),
            net_margin_proxy=round(net_margin_proxy, 2),
        )

    def compute_pvm_bridge(
        self,
        period_a: str,
        period_b: str,
        kpi_a: Optional[KPISnapshot] = None,
        kpi_b: Optional[KPISnapshot] = None,
    ) -> VarianceBridge:
        """
        Performs mathematical Price-Volume-Mix (PVM) and Freight cost decomposition
        between Period A (Baseline) and Period B (Comparison).

        Mathematical formulas:
          Volume Effect      = (Units_B - Units_A) * Avg_Price_A
          Price Effect       = (Avg_Price_B - Avg_Price_A) * Units_B
          Freight Effect     = Total_Freight_A - Total_Freight_B
          Net Margin Delta   = Comparison_Margin - Baseline_Margin

        Identity Checks:
          Volume Effect + Price Effect = Revenue Delta
          Volume Effect + Price Effect + Freight Effect = Net Margin Delta
        """
        if kpi_a is None:
            kpi_a = self.compute_period_kpis(period_a)
        if kpi_b is None:
            kpi_b = self.compute_period_kpis(period_b)

        # Use exact unrounded prices derived from total revenue and units to eliminate rounding drift
        exact_price_a = (kpi_a.total_revenue / kpi_a.total_units) if kpi_a.total_units > 0 else 0.0
        exact_price_b = (kpi_b.total_revenue / kpi_b.total_units) if kpi_b.total_units > 0 else 0.0

        # Standard PVM decomposition
        volume_effect = (kpi_b.total_units - kpi_a.total_units) * exact_price_a
        price_effect = (exact_price_b - exact_price_a) * kpi_b.total_units
        freight_effect = kpi_a.total_freight - kpi_b.total_freight

        net_margin_delta = kpi_b.net_margin_proxy - kpi_a.net_margin_proxy
        revenue_delta = kpi_b.total_revenue - kpi_a.total_revenue
        freight_delta = kpi_b.total_freight - kpi_a.total_freight

        # Ensure penny-perfect accounting identity after rounding
        rounded_vol = round(volume_effect, 2)
        rounded_rev_delta = round(revenue_delta, 2)
        rounded_price = round(rounded_rev_delta - rounded_vol, 2)
        rounded_freight_eff = round(freight_effect, 2)
        rounded_margin_delta = round(rounded_rev_delta + rounded_freight_eff, 2)

        return VarianceBridge(
            baseline_margin=round(kpi_a.net_margin_proxy, 2),
            comparison_margin=round(kpi_b.net_margin_proxy, 2),
            volume_effect=rounded_vol,
            price_effect=rounded_price,
            freight_effect=rounded_freight_eff,
            net_margin_delta=rounded_margin_delta,
            revenue_delta=rounded_rev_delta,
            freight_delta=round(freight_delta, 2),
        )

    def compute_category_movers(
        self, period_a: str, period_b: str, top_n: int = 3
    ) -> Tuple[List[DimensionItem], List[DimensionItem]]:
        """
        Identifies top positive margin contributing categories and top negative margin detractors.
        Margin Proxy = gross_revenue - freight_cost for each category.
        """
        cat_lf = (
            self._scan()
            .filter(pl.col("year_month").is_in([period_a, period_b]))
            .group_by(["year_month", "product_category_name_english"])
            .agg([
                pl.col("gross_revenue").sum().alias("revenue"),
                pl.col("freight_cost").sum().alias("freight"),
                pl.len().alias("units"),
            ])
            .with_columns(
                (pl.col("revenue") - pl.col("freight")).alias("margin")
            )
        )

        cat_df = cat_lf.collect()

        # Pivot or split into period A and period B DataFrames
        df_a = (
            cat_df.filter(pl.col("year_month") == period_a)
            .select([
                pl.col("product_category_name_english").alias("category"),
                pl.col("margin").alias("margin_a"),
                pl.col("revenue").alias("revenue_a"),
                pl.col("units").alias("units_a"),
            ])
        )

        df_b = (
            cat_df.filter(pl.col("year_month") == period_b)
            .select([
                pl.col("product_category_name_english").alias("category"),
                pl.col("margin").alias("margin_b"),
                pl.col("revenue").alias("revenue_b"),
                pl.col("units").alias("units_b"),
            ])
        )

        joined = (
            df_a.join(df_b, on="category", how="full")
            .with_columns([
                pl.col("category").fill_null(pl.col("category_right")),
                pl.col("margin_a").fill_null(0.0),
                pl.col("margin_b").fill_null(0.0),
                pl.col("revenue_a").fill_null(0.0),
                pl.col("revenue_b").fill_null(0.0),
                pl.col("units_a").fill_null(0),
                pl.col("units_b").fill_null(0),
            ])
            .with_columns([
                (pl.col("margin_b") - pl.col("margin_a")).alias("margin_delta"),
                (pl.col("revenue_b") - pl.col("revenue_a")).alias("revenue_delta"),
                (pl.col("units_b") - pl.col("units_a")).alias("units_delta"),
            ])
            .with_columns(
                pl.when(pl.col("margin_a") != 0)
                .then((pl.col("margin_delta") / pl.col("margin_a").abs()) * 100.0)
                .otherwise(
                    pl.when(pl.col("margin_b") > 0).then(100.0).otherwise(0.0)
                )
                .alias("pct_change")
            )
        )

        # Top positive contributors (drivers)
        drivers_df = (
            joined.filter(pl.col("margin_delta") > 0)
            .sort("margin_delta", descending=True)
            .head(top_n)
        )

        # Top negative detractors
        detractors_df = (
            joined.filter(pl.col("margin_delta") < 0)
            .sort("margin_delta", descending=False)
            .head(top_n)
        )

        drivers = [
            DimensionItem(
                name=row["category"],
                baseline_val=round(row["margin_a"], 2),
                comparison_val=round(row["margin_b"], 2),
                delta_val=round(row["margin_delta"], 2),
                pct_change=round(row["pct_change"], 1),
                extra_info={
                    "revenue_delta": round(row["revenue_delta"], 2),
                    "units_delta": int(row["units_delta"]),
                    "units_comparison": int(row["units_b"]),
                },
            )
            for row in drivers_df.to_dicts()
        ]

        detractors = [
            DimensionItem(
                name=row["category"],
                baseline_val=round(row["margin_a"], 2),
                comparison_val=round(row["margin_b"], 2),
                delta_val=round(row["margin_delta"], 2),
                pct_change=round(row["pct_change"], 1),
                extra_info={
                    "revenue_delta": round(row["revenue_delta"], 2),
                    "units_delta": int(row["units_delta"]),
                    "units_comparison": int(row["units_b"]),
                },
            )
            for row in detractors_df.to_dicts()
        ]

        return drivers, detractors

    def compute_state_growers_decliners(
        self, period_a: str, period_b: str, top_n: int = 3
    ) -> Tuple[List[DimensionItem], List[DimensionItem]]:
        """
        Identifies top growing and declining Brazilian states by gross merchandise sales.
        """
        state_lf = (
            self._scan()
            .filter(pl.col("year_month").is_in([period_a, period_b]))
            .group_by(["year_month", "customer_state"])
            .agg([
                pl.col("gross_revenue").sum().alias("revenue"),
                pl.col("order_id").n_unique().alias("orders"),
            ])
        )

        state_df = state_lf.collect()

        df_a = (
            state_df.filter(pl.col("year_month") == period_a)
            .select([
                pl.col("customer_state").alias("state"),
                pl.col("revenue").alias("revenue_a"),
                pl.col("orders").alias("orders_a"),
            ])
        )

        df_b = (
            state_df.filter(pl.col("year_month") == period_b)
            .select([
                pl.col("customer_state").alias("state"),
                pl.col("revenue").alias("revenue_b"),
                pl.col("orders").alias("orders_b"),
            ])
        )

        joined = (
            df_a.join(df_b, on="state", how="full")
            .with_columns([
                pl.col("state").fill_null(pl.col("state_right")),
                pl.col("revenue_a").fill_null(0.0),
                pl.col("revenue_b").fill_null(0.0),
                pl.col("orders_a").fill_null(0),
                pl.col("orders_b").fill_null(0),
            ])
            .with_columns([
                (pl.col("revenue_b") - pl.col("revenue_a")).alias("revenue_delta"),
            ])
            .with_columns(
                pl.when(pl.col("revenue_a") > 0)
                .then((pl.col("revenue_delta") / pl.col("revenue_a")) * 100.0)
                .otherwise(
                    pl.when(pl.col("revenue_b") > 0).then(100.0).otherwise(0.0)
                )
                .alias("pct_change")
            )
        )

        growers_df = (
            joined.filter(pl.col("revenue_delta") > 0)
            .sort("revenue_delta", descending=True)
            .head(top_n)
        )

        decliners_df = (
            joined.filter(pl.col("revenue_delta") < 0)
            .sort("revenue_delta", descending=False)
            .head(top_n)
        )

        growers = [
            DimensionItem(
                name=row["state"],
                baseline_val=round(row["revenue_a"], 2),
                comparison_val=round(row["revenue_b"], 2),
                delta_val=round(row["revenue_delta"], 2),
                pct_change=round(row["pct_change"], 1),
                extra_info={"orders_comparison": int(row["orders_b"])},
            )
            for row in growers_df.to_dicts()
        ]

        decliners = [
            DimensionItem(
                name=row["state"],
                baseline_val=round(row["revenue_a"], 2),
                comparison_val=round(row["revenue_b"], 2),
                delta_val=round(row["revenue_delta"], 2),
                pct_change=round(row["pct_change"], 1),
                extra_info={"orders_comparison": int(row["orders_b"])},
            )
            for row in decliners_df.to_dicts()
        ]

        return growers, decliners

    def compute_regional_performance(
        self, period_a: str, period_b: str
    ) -> List[RegionPerformance]:
        """
        Computes commercial metrics across the 5 Brazilian macro-regions:
        - Revenue Period A vs Period B
        - Share of Company Sales (%)
        - Revenue Growth (%)
        - Freight Burden (Freight / Revenue %)
        - Focus Signal: 'Expansion Driver', 'Focus Required (High Freight Drag)', or 'Contraction Zone'
        """
        reg_lf = (
            self._scan()
            .filter(pl.col("year_month").is_in([period_a, period_b]))
            .group_by(["year_month", "customer_region"])
            .agg([
                pl.col("gross_revenue").sum().alias("revenue"),
                pl.col("freight_cost").sum().alias("freight"),
                pl.col("order_id").n_unique().alias("orders"),
            ])
        )

        reg_df = reg_lf.collect()

        df_a = (
            reg_df.filter(pl.col("year_month") == period_a)
            .select([
                pl.col("customer_region").alias("region"),
                pl.col("revenue").alias("revenue_a"),
                pl.col("orders").alias("orders_a"),
                pl.col("freight").alias("freight_a"),
            ])
        )

        df_b = (
            reg_df.filter(pl.col("year_month") == period_b)
            .select([
                pl.col("customer_region").alias("region"),
                pl.col("revenue").alias("revenue_b"),
                pl.col("orders").alias("orders_b"),
                pl.col("freight").alias("freight_b"),
            ])
        )

        total_rev_a = float(df_a["revenue_a"].sum() or 0.0)
        total_rev_b = float(df_b["revenue_b"].sum() or 0.0)

        joined = (
            df_a.join(df_b, on="region", how="full")
            .with_columns([
                pl.col("region").fill_null(pl.col("region_right")),
                pl.col("revenue_a").fill_null(0.0),
                pl.col("revenue_b").fill_null(0.0),
                pl.col("orders_a").fill_null(0),
                pl.col("orders_b").fill_null(0),
                pl.col("freight_a").fill_null(0.0),
                pl.col("freight_b").fill_null(0.0),
            ])
            .with_columns([
                (pl.col("revenue_b") - pl.col("revenue_a")).alias("revenue_delta"),
            ])
            .with_columns(
                pl.when(pl.col("revenue_a") > 0)
                .then((pl.col("revenue_delta") / pl.col("revenue_a")) * 100.0)
                .otherwise(
                    pl.when(pl.col("revenue_b") > 0).then(100.0).otherwise(0.0)
                )
                .alias("growth_pct")
            )
            .sort("revenue_b", descending=True)
        )

        regions: List[RegionPerformance] = []
        for row in joined.to_dicts():
            rev_a = float(row["revenue_a"])
            rev_b = float(row["revenue_b"])
            orders_b = int(row["orders_b"])
            freight_b = float(row["freight_b"])
            rev_delta = float(row["revenue_delta"])
            growth_pct = float(row["growth_pct"])

            share_a = (rev_a / total_rev_a * 100.0) if total_rev_a > 0 else 0.0
            share_b = (rev_b / total_rev_b * 100.0) if total_rev_b > 0 else 0.0
            freight_burden = (freight_b / rev_b * 100.0) if rev_b > 0 else 0.0

            # Operational Focus categorization
            if growth_pct > 15.0 and freight_burden < 20.0:
                status_signal = "Expansion Driver"
            elif growth_pct > 0 and freight_burden >= 20.0:
                status_signal = "Focus Required (High Freight Drag)"
            elif growth_pct < 0:
                status_signal = "Contraction Zone"
            else:
                status_signal = "Stable Core"

            regions.append(
                RegionPerformance(
                    region=row["region"],
                    baseline_revenue=round(rev_a, 2),
                    comparison_revenue=round(rev_b, 2),
                    revenue_delta=round(rev_delta, 2),
                    revenue_growth_pct=round(growth_pct, 1),
                    baseline_share_pct=round(share_a, 1),
                    comparison_share_pct=round(share_b, 1),
                    comparison_orders=orders_b,
                    freight_cost=round(freight_b, 2),
                    freight_burden_pct=round(freight_burden, 1),
                    status_signal=status_signal,
                )
            )

        return regions

    def generate_report(
        self, period_a: str, period_b: str, top_n: int = 3
    ) -> RootCauseReport:
        """
        Orchestrates full analysis between Period A and Period B, assembling
        and validating the complete RootCauseReport data contract.
        """
        kpi_a = self.compute_period_kpis(period_a)
        kpi_b = self.compute_period_kpis(period_b)
        bridge = self.compute_pvm_bridge(period_a, period_b, kpi_a=kpi_a, kpi_b=kpi_b)
        drivers, detractors = self.compute_category_movers(period_a, period_b, top_n=top_n)
        growers, decliners = self.compute_state_growers_decliners(period_a, period_b, top_n=top_n)
        regional = self.compute_regional_performance(period_a, period_b)

        return RootCauseReport(
            baseline_period=period_a,
            comparison_period=period_b,
            baseline_kpi=kpi_a,
            comparison_kpi=kpi_b,
            variance_bridge=bridge,
            top_category_drivers=drivers,
            top_category_detractors=detractors,
            top_state_growers=growers,
            top_state_decliners=decliners,
            regional_performance=regional,
        )

    def query_fact_table(
        self,
        group_by: List[str],
        metrics: List[str],
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Dynamically executes multi-dimensional aggregations and filters on the fact table.
        Used by the AI Copilot to answer ad-hoc questions about products, turnover, regions, and states.

        Supported dimensions:
          - 'customer_region' (South, Southeast, Northeast, Central-West, North)
          - 'customer_state' (SP, RJ, MG, RS, PR, SC, BA, etc.)
          - 'customer_city'
          - 'product_category_name_english'
          - 'year_month' (e.g. '2017-10')
          - 'year'

        Supported metrics:
          - 'gross_revenue' (total sales turnover)
          - 'freight_cost' (total logistics charge)
          - 'units' (item unit volume)
          - 'orders' (distinct order count)
          - 'avg_item_price' (average price per item)
          - 'aov' (average order value)
          - 'net_margin_proxy' (gross revenue - freight cost)
        """
        synonyms = {
            "region": "customer_region",
            "customer_region": "customer_region",
            "state": "customer_state",
            "customer_state": "customer_state",
            "city": "customer_city",
            "customer_city": "customer_city",
            "category": "product_category_name_english",
            "product_category": "product_category_name_english",
            "product_category_name": "product_category_name_english",
            "product": "product_category_name_english",
            "products": "product_category_name_english",
            "product_category_name_english": "product_category_name_english",
            "period": "year_month",
            "year_month": "year_month",
            "month": "year_month",
            "year": "year",
        }

        # Resolve group_by columns
        resolved_gb: List[str] = []
        for g in group_by:
            clean_g = synonyms.get(str(g).strip().lower())
            if clean_g and clean_g not in resolved_gb:
                resolved_gb.append(clean_g)

        if not resolved_gb:
            resolved_gb = ["product_category_name_english"]

        lf = self._scan()

        # Apply filters
        if filters:
            for k, v in filters.items():
                col = synonyms.get(str(k).strip().lower())
                if not col:
                    continue
                if isinstance(v, list):
                    clean_vals = [str(x).strip().lower() for x in v]
                    lf = lf.filter(pl.col(col).cast(pl.String).str.to_lowercase().is_in(clean_vals))
                elif isinstance(v, (str, int, float)):
                    val_str = str(v).strip().lower()
                    lf = lf.filter(pl.col(col).cast(pl.String).str.to_lowercase() == val_str)

        # Build metric expressions
        metric_aliases = {
            "gross_revenue": "gross_revenue",
            "gross_revenue_sum": "gross_revenue",
            "turnover": "gross_revenue",
            "revenue": "gross_revenue",
            "sales": "gross_revenue",
            "freight_cost": "freight_cost",
            "freight_cost_sum": "freight_cost",
            "freight": "freight_cost",
            "shipping": "freight_cost",
            "units": "units",
            "units_count": "units",
            "volume": "units",
            "quantity": "units",
            "orders": "orders",
            "orders_count": "orders",
            "total_orders": "orders",
            "avg_item_price": "avg_item_price",
            "price": "avg_item_price",
            "aov": "aov",
            "net_margin_proxy": "net_margin_proxy",
            "net_margin": "net_margin_proxy",
            "margin": "net_margin_proxy",
        }

        norm_metrics = set()
        for m in metrics:
            target = metric_aliases.get(str(m).strip().lower())
            if target:
                norm_metrics.add(target)

        if not norm_metrics:
            norm_metrics = {"gross_revenue", "units"}

        agg_exprs = []
        if "gross_revenue" in norm_metrics:
            agg_exprs.append(pl.col("gross_revenue").sum().round(2).alias("gross_revenue"))
        if "freight_cost" in norm_metrics:
            agg_exprs.append(pl.col("freight_cost").sum().round(2).alias("freight_cost"))
        if "units" in norm_metrics:
            agg_exprs.append(pl.len().alias("units"))
        if "orders" in norm_metrics:
            agg_exprs.append(pl.col("order_id").n_unique().alias("orders"))
        if "avg_item_price" in norm_metrics:
            agg_exprs.append(
                (pl.col("gross_revenue").sum() / pl.len()).round(2).alias("avg_item_price")
            )
        if "aov" in norm_metrics:
            agg_exprs.append(
                (pl.col("gross_revenue").sum() / pl.col("order_id").n_unique()).round(2).alias("aov")
            )
        if "net_margin_proxy" in norm_metrics:
            agg_exprs.append(
                (pl.col("gross_revenue").sum() - pl.col("freight_cost").sum()).round(2).alias("net_margin_proxy")
            )

        # Execute aggregation
        grouped = lf.group_by(resolved_gb).agg(agg_exprs)

        # Sorting
        sort_col = "gross_revenue" if "gross_revenue" in norm_metrics else (agg_exprs[0].meta.output_name() if agg_exprs else resolved_gb[0])
        if order_by:
            candidate = metric_aliases.get(str(order_by).strip().lower(), order_by)
            if candidate in norm_metrics or candidate in resolved_gb:
                sort_col = candidate

        max_limit = min(max(int(limit), 1), 25)
        res_df = grouped.sort(sort_col, descending=True).head(max_limit).collect()
        return res_df.to_dicts()

