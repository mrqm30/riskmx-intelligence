from pathlib import Path

import polars as pl

from riskmx_intelligence.settings import settings

DATA_SETNAME  = "incidencia_delictiva_municipal"

MONTH_MAP = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12
}

MONTH_COLUMNS = list(MONTH_MAP.keys())


def get_latest_bronze_file() -> Path:
    base_path = settings.bronze_path / "sesnsp" / DATA_SETNAME
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No bronze files found under {base_path}"
            "Run scripts/03_raw_to_bronze_sesnsp.py first"
        )

    return files[-1]


def clean_string_expr(column: str) -> pl.Expr:
    return(
        pl.col(column)
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.replace_all(r"\s+", " ")
        .alias(column)
    )


def main() -> None:
    bronze_file = get_latest_bronze_file()
    ingestion_date = bronze_file.parent.name.replace("ingestion_date=", "")

    silver_dir = (
        settings.silver_path
        / "sesnsp"
        / DATA_SETNAME
        / f"ingestion_date={ingestion_date}"
    )

    silver_dir.mkdir(parents=True, exist_ok=True)
    silver_file = silver_dir / "data.parquet"
    print("Transforming BRONZE to SILVER")
    print("=" * 100)
    print(f"Bronze file: {bronze_file}")
    print(f"Silver file: {silver_file}")
    print("=" * 100)


    print(bronze_file)
    df = pl.read_parquet(bronze_file)

    required_columns = [
        "ano",
        "clave_ent",
        "entidad",
        "cve_municipio",
        "municipio",
        "bien_juridico_afectado",
        "tipo_de_delito",
        "subtipo_de_delito",
        "modalidad",
        *MONTH_COLUMNS,
        "_record_source",
        "_load_datetime_utc",
        "_source_file",
        "_source_file_sha256",
        "_ingestion_date"
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing Required columns in bronze: {missing_columns}")


    index_columns = [
        "ano",
        "clave_ent",
        "entidad",
        "cve_municipio",
        "municipio",
        "bien_juridico_afectado",
        "tipo_de_delito",
        "subtipo_de_delito",
        "modalidad",
        "_record_source",
        "_load_datetime_utc",
        "_source_file",
        "_source_file_sha256",
        "_ingestion_date",
    ]


    # Unpivot months from wide to long format.
    silver_df = df.melt(
        id_vars=index_columns,
        value_vars=MONTH_COLUMNS,
        variable_name="mes_nombre",
        value_name="cantidad",
    )

    silver_df = silver_df.rename(
        {
            "ano": "anio",
            "clave_ent": "clave_entidad",
            "cve_municipio": "clave_municipio",
            "bien_juridico_afectado": "bien_juridico",
            "tipo_de_delito": "tipo_delito",
            "subtipo_de_delito": "subtipo_delito",
        }
    )

    string_columns = [
        "entidad",
        "municipio",
        "bien_juridico",
        "tipo_delito",
        "subtipo_delito",
        "modalidad",
        "mes_nombre",
    ]

    silver_df = silver_df.with_columns(
        [
            clean_string_expr(column) for column in string_columns
        ]
    )

    silver_df = silver_df.with_columns(
        [
            pl.col("anio").cast(pl.Int32),
            pl.col("clave_entidad").cast(pl.Int32),
            pl.col("clave_municipio").cast(pl.Int32),
            pl.col("cantidad").cast(pl.Int64),
            pl.col("mes_nombre").replace(MONTH_MAP).cast(pl.Int8).alias("mes"),
            pl.col("clave_entidad").cast(pl.Utf8).str.zfill(2).alias("clave_entidad_str"),
            pl.col("clave_municipio").cast(pl.Utf8).str.zfill(5).alias("clave_municipio_str"),
        ]
    )

    # SESNSP usa valores negativos (típicamente -1) como centinela de
    # "no disponible / no reportado". Se confirmó contra el CSV original
    # (IDM_NM_dic25.csv) que estos valores son error de captura de la
    # fuente. No representan una cantidad de delitos válida y se excluyen
    # del análisis (no se imputan a 0, para no inflar artificialmente los
    # totales de "sin incidencia"). Bronze permanece intacto; los
    # registros excluidos se preservan en cuarentena para auditoría.
    is_invalid = (pl.col("cantidad") < 0) | pl.col("cantidad").is_null()
    invalid_count = silver_df.filter(is_invalid).height

    if invalid_count > 0:
        quarantine_dir = (
            settings.quarantine_path
            / "sesnsp"
            / DATA_SETNAME
            / f"ingestion_date={ingestion_date}"
        )
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_file = quarantine_dir / "invalid_cantidad_rows.parquet"

        silver_df.filter(is_invalid).with_columns(
            pl.lit("negative_or_null_cantidad_source_error").alias(
                "exclusion_reason"
            )
        ).write_parquet(quarantine_file)

        print(
            f"Excluding {invalid_count:,} rows with invalid cantidad "
            "(negative sentinel or null, confirmed source data entry error). "
            f"Quarantined to: {quarantine_file}"
        )

        silver_df = silver_df.filter(~is_invalid)

    silver_df = silver_df.with_columns(
        [
            (
                pl.col("anio").cast(pl.Utf8)
                + "-"
                + pl.col("mes").cast(pl.Utf8).str.zfill(2)
            ).alias("anio_mes"),
            (
                pl.col("anio").cast(pl.Utf8)
                + "-"
                + pl.col("mes").cast(pl.Utf8).str.zfill(2)
                + "-01"
            )
            .str.strptime(pl.Date, "%Y-%m-%d")
            .alias("fecha_periodo"),
        ]
    )

    silver_df = silver_df.select(
        [
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
    )

    silver_df.write_parquet(
        silver_file,
        compression="zstd",
        statistics=True,
    )

    print("Silver write completed")
    print(f"Rows: {silver_df.height:,}")
    print(f"Columns: {silver_df.width:,}")
    print(f"Output: {silver_file}")


if __name__ == "__main__":
    main()