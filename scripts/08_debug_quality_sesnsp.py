from pathlib import Path

import polars as pl

from riskmx_intelligence.settings import settings


DATASET_NAME = "incidencia_delictiva_municipal"

MONTH_COLUMNS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

SILVER_REQUIRED_COLUMNS = [
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


def latest_file(base_path: Path) -> Path:
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))
    if not files:
        raise FileNotFoundError(base_path)
    return files[-1]


def main() -> None:
    bronze_file = latest_file(settings.bronze_path / "sesnsp" / DATASET_NAME)
    silver_file = latest_file(settings.silver_path / "sesnsp" / DATASET_NAME)

    print(f"Bronze: {bronze_file}")
    print(f"Silver: {silver_file}")
    print("=" * 100)

    bronze_df = pl.read_parquet(bronze_file)
    silver_df = pl.read_parquet(silver_file)

    print("Silver null columns:")
    nulls = silver_df.select(
        [pl.col(c).null_count().alias(c) for c in SILVER_REQUIRED_COLUMNS]
    ).to_dicts()[0]

    for column, count in nulls.items():
        if count > 0:
            print(f"- {column}: {count:,}")

    if all(count == 0 for count in nulls.values()):
        print("- No nulls found in required silver columns")

    print("=" * 100)

    print("Bronze month totals:")
    bronze_month_totals = bronze_df.select(
        [pl.col(c).sum().alias(c) for c in MONTH_COLUMNS]
    ).to_dicts()[0]

    for column, total in bronze_month_totals.items():
        print(f"- {column}: {total:,}")

    bronze_total_safe = sum(value or 0 for value in bronze_month_totals.values())
    silver_total = silver_df.select(pl.col("cantidad").sum()).item()

    print("=" * 100)
    print(f"Bronze total safe: {bronze_total_safe:,}")
    print(f"Silver total:       {silver_total:,}")
    print(f"Difference:         {silver_total - bronze_total_safe:,}")

    print("=" * 100)
    print("Silver cantidad nulls:")
    print(silver_df.select(pl.col("cantidad").null_count()).item())

    print("=" * 100)
    print("Silver total by month:")
    print(
        silver_df
        .group_by("mes")
        .agg(pl.col("cantidad").sum().alias("total"))
        .sort("mes")
    )


if __name__ == "__main__":
    main()
