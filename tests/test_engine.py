"""
tests/test_engine.py
Automated validation of MetricEngine, PVM variance reconciliation,
regional calculations, and Pydantic schema integrity.
"""

import pytest
from src.engine import MetricEngine
from src.schema import RootCauseReport


@pytest.fixture(scope="module")
def engine():
    return MetricEngine("./data/olist_analytics_fact.parquet")


def test_available_periods(engine):
    periods = engine.get_available_periods()
    assert len(periods) > 10
    assert "2017-10" in periods
    assert "2017-11" in periods
    assert periods == sorted(periods)


def test_compute_kpis(engine):
    kpi_oct = engine.compute_period_kpis("2017-10")
    assert kpi_oct.period == "2017-10"
    assert kpi_oct.total_revenue > 0
    assert kpi_oct.total_orders > 0
    assert kpi_oct.total_units >= kpi_oct.total_orders
    assert kpi_oct.aov > 0
    assert kpi_oct.avg_item_price > 0
    assert kpi_oct.total_freight > 0
    assert abs(kpi_oct.net_margin_proxy - (kpi_oct.total_revenue - kpi_oct.total_freight)) < 0.05


def test_pvm_reconciliation(engine):
    period_a = "2017-10"
    period_b = "2017-11"
    kpi_a = engine.compute_period_kpis(period_a)
    kpi_b = engine.compute_period_kpis(period_b)
    bridge = engine.compute_pvm_bridge(period_a, period_b, kpi_a, kpi_b)

    # 1. Volume + Price == Revenue Delta
    rev_reconciliation = bridge.volume_effect + bridge.price_effect
    assert abs(rev_reconciliation - bridge.revenue_delta) < 1.0, (
        f"Revenue mismatch: Volume({bridge.volume_effect}) + Price({bridge.price_effect}) "
        f"= {rev_reconciliation} != {bridge.revenue_delta}"
    )

    # 2. Volume + Price + Freight == Net Margin Delta
    margin_reconciliation = bridge.volume_effect + bridge.price_effect + bridge.freight_effect
    assert abs(margin_reconciliation - bridge.net_margin_delta) < 1.0, (
        f"Margin mismatch: Volume({bridge.volume_effect}) + Price({bridge.price_effect}) + "
        f"Freight({bridge.freight_effect}) = {margin_reconciliation} != {bridge.net_margin_delta}"
    )


def test_dimensional_slices(engine):
    period_a = "2017-10"
    period_b = "2017-11"
    drivers, detractors = engine.compute_category_movers(period_a, period_b, top_n=3)
    assert len(drivers) <= 3
    assert len(detractors) <= 3
    for d in drivers:
        assert d.delta_val >= 0

    growers, decliners = engine.compute_state_growers_decliners(period_a, period_b, top_n=3)
    assert len(growers) <= 3
    assert len(decliners) <= 3


def test_regional_performance(engine):
    period_a = "2017-10"
    period_b = "2017-11"
    regions = engine.compute_regional_performance(period_a, period_b)
    assert len(regions) == 5
    region_names = {r.region for r in regions}
    expected_regions = {"Southeast", "South", "Northeast", "Central-West", "North"}
    assert region_names == expected_regions

    # Total regional shares in period B should sum to ~100%
    total_share = sum(r.comparison_share_pct for r in regions)
    assert abs(total_share - 100.0) < 1.0


def test_full_report_generation(engine):
    report = engine.generate_report("2017-10", "2017-11", top_n=3)
    assert isinstance(report, RootCauseReport)
    assert report.baseline_period == "2017-10"
    assert report.comparison_period == "2017-11"
    assert len(report.regional_performance) == 5


def test_query_fact_table(engine):
    # 1. Test South region category turnover query
    south_res = engine.query_fact_table(
        group_by=["category"],
        metrics=["turnover", "units"],
        filters={"region": "South"},
        limit=5,
    )
    assert len(south_res) == 5
    assert "product_category_name_english" in south_res[0]
    assert "gross_revenue" in south_res[0]
    assert "units" in south_res[0]
    assert south_res[0]["gross_revenue"] >= south_res[1]["gross_revenue"]

    # 2. Test multi-filter with period and state
    sp_res = engine.query_fact_table(
        group_by=["city"],
        metrics=["gross_revenue", "orders"],
        filters={"state": "SP", "year_month": "2017-11"},
        limit=3,
    )
    assert len(sp_res) == 3
    assert "customer_city" in sp_res[0]
    assert "gross_revenue" in sp_res[0]
    assert "orders" in sp_res[0]
    assert sp_res[0]["gross_revenue"] >= sp_res[1]["gross_revenue"]

