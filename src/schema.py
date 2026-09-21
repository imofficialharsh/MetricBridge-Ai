"""
src/schema.py
Strict Pydantic v2 data contracts for Metric Trees, PVM Variance Decomposition,
Regional Intelligence, and Root Cause Analysis reporting.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class KPISnapshot(BaseModel):
    """Snapshot of foundational e-commerce KPIs for a specific time period."""

    period: str = Field(description="Period identifier, formatted as YYYY-MM")
    total_revenue: float = Field(description="Gross merchandise sales (sum of product prices)")
    total_orders: int = Field(description="Distinct count of delivered orders")
    total_units: int = Field(description="Total count of item units purchased")
    aov: float = Field(description="Average Order Value: total_revenue / total_orders")
    avg_item_price: float = Field(description="Average Realized Unit Price: total_revenue / total_units")
    total_freight: float = Field(description="Total shipping and logistics charges paid by customers")
    net_margin_proxy: float = Field(
        description="Net margin proxy before non-freight operating costs: total_revenue - total_freight"
    )


class VarianceBridge(BaseModel):
    """
    Mathematical Price-Volume-Mix (PVM) and Freight cost variance decomposition
    between Period A (Baseline) and Period B (Comparison).
    """

    baseline_margin: float = Field(description="Period A Net Margin Proxy")
    comparison_margin: float = Field(description="Period B Net Margin Proxy")
    volume_effect: float = Field(
        description="(Units_B - Units_A) * Avg_Price_A. Revenue delta driven purely by unit sales volume."
    )
    price_effect: float = Field(
        description="(Avg_Price_B - Avg_Price_A) * Units_B. Revenue delta driven purely by unit pricing adjustments."
    )
    freight_effect: float = Field(
        description="Total_Freight_A - Total_Freight_B. Direct impact of shipping cost fluctuations on margin."
    )
    net_margin_delta: float = Field(
        description="Comparison_Margin - Baseline_Margin (Reconciles: Volume + Price + Freight Effects)"
    )
    revenue_delta: float = Field(
        description="Comparison_Revenue - Baseline_Revenue (Reconciles: Volume + Price Effects)"
    )
    freight_delta: float = Field(description="Comparison_Freight - Baseline_Freight")


class DimensionItem(BaseModel):
    """Diagnostic data point representing a specific slice (category or state)."""

    name: str = Field(description="Dimension value name (e.g., product category or state abbreviation)")
    baseline_val: float = Field(description="Value in Period A")
    comparison_val: float = Field(description="Value in Period B")
    delta_val: float = Field(description="Absolute delta: comparison_val - baseline_val")
    pct_change: float = Field(description="Percentage change from Period A to Period B")
    extra_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional supporting metrics (e.g. units sold, margin delta)"
    )


class RegionPerformance(BaseModel):
    """
    Regional commercial breakdown across Brazilian macro-regions
    (Southeast, South, Northeast, Central-West, North).
    """

    region: str = Field(description="Brazilian macro-region name")
    baseline_revenue: float = Field(description="Gross revenue in Period A")
    comparison_revenue: float = Field(description="Gross revenue in Period B")
    revenue_delta: float = Field(description="Revenue change: comparison - baseline")
    revenue_growth_pct: float = Field(description="Revenue growth percentage")
    baseline_share_pct: float = Field(description="Region's share of total company revenue in Period A (%)")
    comparison_share_pct: float = Field(description="Region's share of total company revenue in Period B (%)")
    comparison_orders: int = Field(description="Total orders in Period B")
    freight_cost: float = Field(description="Total freight cost in Period B")
    freight_burden_pct: float = Field(description="Freight cost as a percentage of gross revenue in Period B (%)")
    status_signal: str = Field(
        description="Operational focus label: 'Expansion Driver', 'Focus Required', or 'Contraction Zone'"
    )


class RootCauseReport(BaseModel):
    """
    Type-safe master container carrying complete financial variance,
    dimensional diagnostics, and regional performance.
    """

    baseline_period: str = Field(description="Baseline period (Period A)")
    comparison_period: str = Field(description="Comparison period (Period B)")
    baseline_kpi: KPISnapshot = Field(description="Baseline period KPI snapshot")
    comparison_kpi: KPISnapshot = Field(description="Comparison period KPI snapshot")
    variance_bridge: VarianceBridge = Field(description="PVM and Freight variance breakdown")
    top_category_drivers: List[DimensionItem] = Field(
        description="Top positive margin contributing categories"
    )
    top_category_detractors: List[DimensionItem] = Field(
        description="Top negative margin detracting categories"
    )
    top_state_growers: List[DimensionItem] = Field(
        description="Top growing states by gross revenue"
    )
    top_state_decliners: List[DimensionItem] = Field(
        description="Top declining states by gross revenue"
    )
    regional_performance: List[RegionPerformance] = Field(
        description="Macro-regional commercial performance breakdown"
    )
