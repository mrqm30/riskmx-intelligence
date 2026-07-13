from pathlib import Path

import polars as pl

from riskmx_intelligence.settings import settings

DATASET_NAME = "incidencia_delictiva_municipal"
RAW_FILENAME = "Municipal-Delitos-2015-2025_may-2026.csv"


def get_latest_bronze_file() -> Path:
    base_path = settings.bronze_path / "sesnsp" / DATASET_NAME
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No bronze files found under {base_path}. "
            "Run scripts/03_raw_to_bronze_sesnsp.py first."
        )

    return files[-1]

def main() -> None:
    bronze_file = get_latest_bronze_file()

    print("Validating BRONZE file")
    print("=" * 100)
    print(f"File: {bronze_file}")
    print("=" * 100)

    df = pl.read_parquet(bronze_file)

    print(f"Rows: {df.height:,}")
    print(f"Columns: {df.width:,}")

    required_metadata_columns = [
        "_record_source",
        "_load_datetime_utc",
        "_source_file",
        "_source_file_sha256",
        "_ingestion_date",
    ]

    missing_columns = [
        column for column in required_metadata_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing metadata columns: {missing_columns}")

    if df.height == 0:
        raise ValueError("Bronze dataframe is empty")

    print("=" * 100)
    print("Schema:")
    for column, dtype in df.schema.items():
        print(f"- {column}: {dtype}")

    print("=" * 100)
    print("Sample:")
    print(df.head(5))
    print(df.columns)
    print("=" * 100)
    print("BRONZE validation OK")


if __name__ == "__main__":
    main()
