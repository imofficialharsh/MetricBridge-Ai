"""
src/preprocess.py
ETL & Parquet Materialization pipeline using Polars LazyFrames.
Transforms 5 raw Olist CSV tables into a high-performance,
Snappy-compressed columnar analytical fact table.
"""

import os
import sys
import time
from pathlib import Path
import polars as pl

# 5 Brazilian Macro-Regions mapping (IBGE official classification)
STATE_TO_REGION = {
    # Southeast (Sudeste)
    "SP": "Southeast",
    "RJ": "Southeast",
    "MG": "Southeast",
    "ES": "Southeast",
    # South (Sul)
    "PR": "South",
    "SC": "South",
    "RS": "South",
    # Northeast (Nordeste)
    "BA": "Northeast",
    "PE": "Northeast",
    "CE": "Northeast",
    "MA": "Northeast",
    "PB": "Northeast",
    "RN": "Northeast",
    "AL": "Northeast",
    "PI": "Northeast",
    "SE": "Northeast",
    # Central-West (Centro-Oeste)
    "DF": "Central-West",
    "GO": "Central-West",
    "MT": "Central-West",
    "MS": "Central-West",
    # North (Norte)
    "AM": "North",
    "PA": "North",
    "RO": "North",
    "TO": "North",
    "AC": "North",
    "AP": "North",
    "RR": "North",
}


def run_etl(raw_data_dir: str = "./data/raw", output_parquet_path: str = "./data/olist_analytics_fact.parquet") -> pl.DataFrame:
    """
    Executes the lazy ETL pipeline:
    1. Ingests 5 CSVs via pl.scan_csv().
    2. Filters delivered orders and parses purchase timestamps.
    3. Joins items, products, English category translations, and customer geography.
    4. Computes customer_region from customer_state.
    5. Casts and projects columns to target fact schema.
    6. Materializes to Snappy-compressed Parquet.
    """
    start_time = time.time()
    raw_path = Path(raw_data_dir)
    out_path = Path(output_parquet_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    orders_file = raw_path / "olist_orders_dataset.csv"
    order_items_file = raw_path / "olist_order_items_dataset.csv"
    products_file = raw_path / "olist_products_dataset.csv"
    translations_file = raw_path / "product_category_name_translation.csv"
    customers_file = raw_path / "olist_customers_dataset.csv"

    # Verify input files exist
    for f in [orders_file, order_items_file, products_file, translations_file, customers_file]:
        if not f.exists():
            raise FileNotFoundError(f"Required raw dataset not found: {f.resolve()}")

    print("[INFO] Starting Polars Lazy ETL Pipeline...")
    print(f"   Raw directory: {raw_path.resolve()}")
    print(f"   Destination:   {out_path.resolve()}")

    # 1. Orders: Lazy scan, filter delivered, parse timestamps
    orders_lf = (
        pl.scan_csv(str(orders_file))
        .filter(pl.col("order_status") == "delivered")
        .with_columns(
            pl.col("order_purchase_timestamp").str.to_datetime("%Y-%m-%d %H:%M:%S")
        )
        .with_columns([
            pl.col("order_purchase_timestamp").dt.year().cast(pl.Int32).alias("year"),
            pl.col("order_purchase_timestamp").dt.strftime("%Y-%m").alias("year_month"),
        ])
        .select([
            "order_id",
            "customer_id",
            "order_purchase_timestamp",
            "year",
            "year_month",
        ])
    )

    # 2. Order Items: Lazy scan
    items_lf = pl.scan_csv(str(order_items_file)).select([
        "order_id",
        "order_item_id",
        "product_id",
        "price",
        "freight_value",
    ])

    # 3. Products: Lazy scan
    products_lf = pl.scan_csv(str(products_file)).select([
        "product_id",
        "product_category_name",
    ])

    # 4. Translations: Lazy scan
    trans_lf = pl.scan_csv(str(translations_file)).select([
        "product_category_name",
        "product_category_name_english",
    ])

    # 5. Customers: Lazy scan
    customers_lf = pl.scan_csv(str(customers_file)).select([
        "customer_id",
        "customer_city",
        "customer_state",
    ])

    # Relational Joins & Transformations
    # Orders -> Items -> Products -> Translations -> Customers
    fact_lf = (
        orders_lf
        .join(items_lf, on="order_id", how="inner")
        .join(products_lf, on="product_id", how="left")
        .join(trans_lf, on="product_category_name", how="left")
        .join(customers_lf, on="customer_id", how="left")
        .with_columns([
            # Fill missing category translations with 'others'
            pl.col("product_category_name_english").fill_null("others").alias("product_category_name_english"),
            # Map Brazilian states to macro-regions
            pl.col("customer_state")
            .replace(STATE_TO_REGION)
            .fill_null("Other")
            .alias("customer_region"),
            # Alias price -> gross_revenue, freight_value -> freight_cost
            pl.col("price").cast(pl.Float64).alias("gross_revenue"),
            pl.col("freight_value").cast(pl.Float64).alias("freight_cost"),
        ])
        .select([
            "order_id",
            "order_item_id",
            "order_purchase_timestamp",
            "year",
            "year_month",
            "customer_state",
            "customer_city",
            "customer_region",
            "product_category_name_english",
            "gross_revenue",
            "freight_cost",
        ])
    )

    print("[INFO] Collecting optimized plan and materializing to Parquet...")
    fact_df = fact_lf.collect()

    # Materialize to Snappy-compressed Parquet
    fact_df.write_parquet(str(out_path), compression="snappy")

    elapsed = time.time() - start_time
    file_size_mb = out_path.stat().st_size / (1024 * 1024)

    print(f"[SUCCESS] Materialization completed in {elapsed:.2f}s!")
    print(f"   Output rows:        {len(fact_df):,}")
    print(f"   Distinct orders:    {fact_df['order_id'].n_unique():,}")
    print(f"   Distinct periods:   {fact_df['year_month'].n_unique()} months")
    print(f"   File size:          {file_size_mb:.2f} MB")
    print(f"   Schema:\n{fact_df.schema}")

    return fact_df


if __name__ == "__main__":
    raw_dir = sys.argv[1] if len(sys.argv) > 1 else "./data/raw"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "./data/olist_analytics_fact.parquet"
    run_etl(raw_data_dir=raw_dir, output_parquet_path=out_file)
