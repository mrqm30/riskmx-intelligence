from pathlib import Path

import polars as pl

from riskmx_intelligence.quality.checks import (
    check_catalog_cardinality,
    check_month_range,
    check_no_nulls,
    check_non_negative,
    check_not_empty,
    check_required_columns,
    check_row_count_reconciliation,
    check_total_quantity_consistency,
    check_unique_grain,
    check_year_range,
)
from riskmx_intelligence.quality.report import write_quality_report
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

SILVER_GRAIN_COLUMNS = [
    "anio",
    "mes",
    "clave_municipio",
    "bien_juridico",
    "tipo_delito",
    "subtipo_delito",
    "modalidad",
]


def get_latest_file(base_path: Path, pattern: str) -> Path:
    files = sorted(base_path.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No files found under {base_path} with pattern {pattern}")

    return files[-1]


def main() -> None:
    bronze_base_path = settings.bronze_path / "sesnsp" / DATASET_NAME
    silver_base_path = settings.silver_path / "sesnsp" / DATASET_NAME

    bronze_file = get_latest_file(bronze_base_path, "ingestion_date=*/data.parquet")
    silver_file = get_latest_file(silver_base_path, "ingestion_date=*/data.parquet")

    ingestion_date = silver_file.parent.name.replace("ingestion_date=", "")

    report_dir = (
        settings.reports_root
        / "data_quality"
        / "sesnsp"
        / DATASET_NAME
        / f"ingestion_date={ingestion_date}"
    )

    print("Running formal data quality checks")
    print("=" * 100)
    print(f"Bronze file: {bronze_file}")
    print(f"Silver file: {silver_file}")
    print(f"Report dir: {report_dir}")
    print("=" * 100)

    bronze_df = pl.read_parquet(bronze_file)
    silver_df = pl.read_parquet(silver_file)

    results = [
        check_not_empty(silver_df),
        check_required_columns(silver_df, SILVER_REQUIRED_COLUMNS),
        check_no_nulls(silver_df, SILVER_REQUIRED_COLUMNS),
        check_non_negative(silver_df, "cantidad"),
        check_month_range(silver_df, "mes"),
        check_year_range(silver_df, "anio", min_year=2015),
        check_unique_grain(silver_df, SILVER_GRAIN_COLUMNS),
        check_catalog_cardinality(silver_df),
        check_row_count_reconciliation(bronze_df, silver_df, expected_multiplier=12),
        check_total_quantity_consistency(bronze_df, silver_df, MONTH_COLUMNS),
    ]

    json_path, md_path = write_quality_report(
        results=results,
        output_dir=report_dir,
        dataset_name=DATASET_NAME,
    )

    failed_results = [result for result in results if not result.passed]

    print("Quality checks completed")
    print("=" * 100)

    for result in results:
        print(f"{result.status} | {result.severity} | {result.check_name} | {result.message}")

    print("=" * 100)
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")

    if failed_results:
        raise SystemExit("Data quality failed. Review report.")

    print("DATA QUALITY OK")


if __name__ == "__main__":
    main()