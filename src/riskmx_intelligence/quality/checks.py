import polars as pl

from riskmx_intelligence.quality.results import (
    QualityCheckResult,
    fail_check,
    pass_check,
)


def check_not_empty(df: pl.DataFrame) -> QualityCheckResult:
    rows = df.height

    if rows == 0:
        return fail_check(
            check_name="not_empty",
            message="Dataset is empty.",
            metrics={"rows": rows},
        )

    return pass_check(
        check_name="not_empty",
        message="Dataset is not empty.",
        metrics={"rows": rows},
    )


def check_required_columns(
    df: pl.DataFrame,
    required_columns: list[str],
) -> QualityCheckResult:
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return fail_check(
            check_name="required_columns",
            message="Dataset is missing required columns.",
            metrics={"missing_columns": missing_columns},
        )

    return pass_check(
        check_name="required_columns",
        message="All required columns are present.",
        metrics={
            "required_columns": required_columns,
            "column_count": len(df.columns),
        },
    )


def check_no_nulls(
    df: pl.DataFrame,
    columns: list[str],
) -> QualityCheckResult:
    null_counts_df = df.select(
        [pl.col(column).null_count().alias(column) for column in columns]
    )

    null_counts = null_counts_df.to_dicts()[0]
    columns_with_nulls = {
        column: count
        for column, count in null_counts.items()
        if count > 0
    }

    if columns_with_nulls:
        return fail_check(
            check_name="no_nulls_required_columns",
            message="Required columns contain null values.",
            metrics={"columns_with_nulls": columns_with_nulls},
        )

    return pass_check(
        check_name="no_nulls_required_columns",
        message="Required columns have no null values.",
        metrics={"checked_columns": columns},
    )


def check_non_negative(
    df: pl.DataFrame,
    column: str,
) -> QualityCheckResult:
    negative_rows = df.filter(pl.col(column) < 0).height

    if negative_rows > 0:
        return fail_check(
            check_name=f"non_negative_{column}",
            message=f"Column {column} contains negative values.",
            metrics={"negative_rows": negative_rows},
        )

    return pass_check(
        check_name=f"non_negative_{column}",
        message=f"Column {column} has no negative values.",
        metrics={"negative_rows": negative_rows},
    )


def check_month_range(df: pl.DataFrame, column: str = "mes") -> QualityCheckResult:
    invalid_rows = df.filter(~pl.col(column).is_between(1, 12)).height

    if invalid_rows > 0:
        return fail_check(
            check_name="month_range",
            message="Month column contains values outside 1..12.",
            metrics={"invalid_rows": invalid_rows},
        )

    month_min = df.select(pl.col(column).min()).item()
    month_max = df.select(pl.col(column).max()).item()

    return pass_check(
        check_name="month_range",
        message="Month column is within valid range 1..12.",
        metrics={"min_month": month_min, "max_month": month_max},
    )


def check_year_range(
    df: pl.DataFrame,
    column: str = "anio",
    min_year: int = 2015,
) -> QualityCheckResult:
    year_min = df.select(pl.col(column).min()).item()
    year_max = df.select(pl.col(column).max()).item()

    if year_min < min_year:
        return fail_check(
            check_name="year_range",
            message=f"Dataset contains years lower than {min_year}.",
            metrics={"min_year": year_min, "max_year": year_max},
        )

    return pass_check(
        check_name="year_range",
        message="Year range is valid.",
        metrics={"min_year": year_min, "max_year": year_max},
    )


def check_unique_grain(
    df: pl.DataFrame,
    grain_columns: list[str],
) -> QualityCheckResult:
    duplicate_combinations = (
        df
        .group_by(grain_columns)
        .len()
        .filter(pl.col("len") > 1)
        .height
    )

    if duplicate_combinations > 0:
        return fail_check(
            check_name="unique_grain",
            message="Dataset contains duplicated grain combinations.",
            metrics={
                "grain_columns": grain_columns,
                "duplicate_combinations": duplicate_combinations,
            },
        )

    return pass_check(
        check_name="unique_grain",
        message="Dataset grain is unique.",
        metrics={
            "grain_columns": grain_columns,
            "duplicate_combinations": duplicate_combinations,
        },
    )


def check_catalog_cardinality(
    df: pl.DataFrame,
) -> QualityCheckResult:
    metrics = {
        "entities": df.select(pl.col("clave_entidad").n_unique()).item(),
        "municipalities": df.select(pl.col("clave_municipio").n_unique()).item(),
        "crime_types": df.select(pl.col("tipo_delito").n_unique()).item(),
        "legal_goods": df.select(pl.col("bien_juridico").n_unique()).item(),
        "subcrime_types": df.select(pl.col("subtipo_delito").n_unique()).item(),
        "modalities": df.select(pl.col("modalidad").n_unique()).item(),
    }

    if metrics["entities"] != 32:
        return fail_check(
            check_name="catalog_cardinality",
            message="Unexpected number of entities.",
            metrics=metrics,
            severity="MEDIUM",
        )

    if metrics["municipalities"] < 2400:
        return fail_check(
            check_name="catalog_cardinality",
            message="Unexpectedly low number of municipalities.",
            metrics=metrics,
            severity="MEDIUM",
        )

    return pass_check(
        check_name="catalog_cardinality",
        message="Catalog cardinalities are within expected ranges.",
        metrics=metrics,
        severity="MEDIUM",
    )


def check_total_quantity_consistency(
    bronze_df: pl.DataFrame,
    silver_df: pl.DataFrame,
    month_columns: list[str],
) -> QualityCheckResult:
    bronze_total = bronze_df.select(
        sum(pl.col(column).sum() for column in month_columns)
    ).item()

    silver_total = silver_df.select(pl.col("cantidad").sum()).item()

    if bronze_total != silver_total:
        return fail_check(
            check_name="total_quantity_consistency",
            message="Total quantity mismatch between bronze and silver.",
            metrics={
                "bronze_total": bronze_total,
                "silver_total": silver_total,
                "difference": silver_total - bronze_total,
            },
        )

    return pass_check(
        check_name="total_quantity_consistency",
        message="Total quantity matches between bronze and silver.",
        metrics={
            "bronze_total": bronze_total,
            "silver_total": silver_total,
            "difference": 0,
        },
    )


def check_row_count_reconciliation(
    bronze_df: pl.DataFrame,
    silver_df: pl.DataFrame,
    expected_multiplier: int = 12,
) -> QualityCheckResult:
    expected_rows = bronze_df.height * expected_multiplier
    actual_rows = silver_df.height

    if actual_rows != expected_rows:
        return fail_check(
            check_name="row_count_reconciliation",
            message="Silver row count does not match expected bronze expansion.",
            metrics={
                "bronze_rows": bronze_df.height,
                "expected_silver_rows": expected_rows,
                "actual_silver_rows": actual_rows,
            },
        )

    return pass_check(
        check_name="row_count_reconciliation",
        message="Silver row count matches expected bronze expansion.",
        metrics={
            "bronze_rows": bronze_df.height,
            "expected_silver_rows": expected_rows,
            "actual_silver_rows": actual_rows,
        },
    )