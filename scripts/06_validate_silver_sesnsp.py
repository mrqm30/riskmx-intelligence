from pathlib import Path

import polars as pl

from riskmx_intelligence.settings import settings


DATASET_NAME = "incidencia_delictiva_municipal"


def get_latest_bronze_file() -> Path:
    base_path = settings.bronze_path / "sesnsp" / DATASET_NAME
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))

    if not files:
        raise FileNotFoundError(f"No bronze files found under {base_path}")

    return files[-1]


def get_latest_silver_file() -> Path:
    base_path = settings.silver_path / "sesnsp" / DATASET_NAME
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No silver files found under {base_path}. "
            "Run scripts/05_bronze_to_silver_sesnsp.py first."
        )

    return files[-1]


def main() -> None:
    bronze_file = get_latest_bronze_file()
    silver_file = get_latest_silver_file()

    print("Validating SILVER file")
    print("=" * 100)
    print(f"Bronze file: {bronze_file}")
    print(f"Silver file: {silver_file}")
    print("=" * 100)

    bronze_df = pl.read_parquet(bronze_file)
    silver_df = pl.read_parquet(silver_file)

    expected_rows = bronze_df.height * 12
    actual_rows = silver_df.height

    print(f"Bronze rows: {bronze_df.height:,}")
    print(f"Expected silver rows: {expected_rows:,}")
    print(f"Actual silver rows: {actual_rows:,}")

    if actual_rows != expected_rows:
        raise ValueError(
            f"Unexpected silver row count. Expected {expected_rows:,}, got {actual_rows:,}"
        )

    required_columns = [
        "anio",
        "mes",
        "anio_mes",
        "fecha_periodo",
        "clave_entidad",
        "clave_entidad_str",
        "entidad",
        "clave_municipio",
        "clave_municipio_str",
        "municipio",
        "bien_juridico",
        "tipo_delito",
        "subtipo_delito",
        "modalidad",
        "cantidad",
        "_record_source",
        "_load_datetime_utc",
        "_source_file",
        "_source_file_sha256",
        "_ingestion_date",
    ]

    missing_columns = [column for column in required_columns if column not in silver_df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns in silver: {missing_columns}")

    negative_rows = silver_df.filter(pl.col("cantidad") < 0).height

    if negative_rows > 0:
        raise ValueError(f"Found negative cantidad rows: {negative_rows:,}")

    invalid_months = silver_df.filter(~pl.col("mes").is_between(1, 12)).height

    if invalid_months > 0:
        raise ValueError(f"Found invalid month rows: {invalid_months:,}")

    null_counts = silver_df.select(
        [
            pl.col(column).null_count().alias(column)
            for column in required_columns
        ]
    )

    print("=" * 100)
    print("Null counts:")
    print(null_counts)

    key_columns = [
        "anio",
        "mes",
        "clave_municipio",
        "bien_juridico",
        "tipo_delito",
        "subtipo_delito",
        "modalidad",
    ]

    duplicate_grain_rows = (
        silver_df
        .group_by(key_columns)
        .len()
        .filter(pl.col("len") > 1)
        .height
    )

    print("=" * 100)
    print(f"Duplicate grain combinations: {duplicate_grain_rows:,}")

    if duplicate_grain_rows > 0:
        raise ValueError(
            "Found duplicated grain combinations. "
            "Review municipality + crime + period granularity."
        )

    print("=" * 100)
    print("Basic profile:")
    print(f"Years: {silver_df.select(pl.col('anio').min()).item()} - {silver_df.select(pl.col('anio').max()).item()}")
    print(f"Entities: {silver_df.select(pl.col('clave_entidad').n_unique()).item():,}")
    print(f"Municipalities: {silver_df.select(pl.col('clave_municipio').n_unique()).item():,}")
    print(f"Crime types: {silver_df.select(pl.col('tipo_delito').n_unique()).item():,}")
    print(f"Total cantidad: {silver_df.select(pl.col('cantidad').sum()).item():,}")

    print("=" * 100)
    print("Sample:")
    print(silver_df.head(10))

    print("=" * 100)
    print("SILVER validation OK")


if __name__ == "__main__":
    main()