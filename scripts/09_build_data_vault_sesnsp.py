from pathlib import Path

import duckdb

from riskmx_intelligence.settings import settings


DATASET_NAME = "incidencia_delictiva_municipal"


def sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def latest_silver_file() -> Path:
    base_path = settings.silver_path / "sesnsp" / DATASET_NAME
    files = sorted(base_path.glob("ingestion_date=*/data.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No silver files found under {base_path}. "
            "Run scripts/05_bronze_to_silver_sesnsp.py first."
        )

    return files[-1]


def copy_to_parquet(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con.execute(
        f"""
        COPY (
            {query}
        )
        TO '{sql_path(output_path)}'
        (FORMAT PARQUET, COMPRESSION ZSTD);
        """
    )


def main() -> None:
    silver_file = latest_silver_file()
    ingestion_date = silver_file.parent.name.replace("ingestion_date=", "")

    dv_dir = (
        settings.dv_path
        / "sesnsp"
        / DATASET_NAME
        / f"ingestion_date={ingestion_date}"
    )

    dv_dir.mkdir(parents=True, exist_ok=True)

    print("Building Data Vault 2.0 objects")
    print("=" * 100)
    print(f"Silver file: {silver_file}")
    print(f"DV dir: {dv_dir}")
    print("=" * 100)

    con = duckdb.connect(database=":memory:")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW silver AS
        SELECT *
        FROM read_parquet('{sql_path(silver_file)}');
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW silver_hashed AS
        SELECT
            *,
            sha256('ENTIDAD|' || clave_entidad_str) AS entidad_hashkey,

            sha256('MUNICIPIO|' || clave_municipio_str) AS municipio_hashkey,

            sha256(
                'DELITO|'
                || upper(trim(bien_juridico)) || '|'
                || upper(trim(tipo_delito)) || '|'
                || upper(trim(subtipo_delito)) || '|'
                || upper(trim(modalidad))
            ) AS delito_hashkey,

            sha256('PERIODO|' || anio_mes) AS periodo_hashkey
        FROM silver;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW silver_linked AS
        SELECT
            *,
            sha256(
                'L_MDP|'
                || municipio_hashkey || '|'
                || delito_hashkey || '|'
                || periodo_hashkey
            ) AS municipio_delito_periodo_lnk_hashkey
        FROM silver_hashed;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW silver_vault_ready AS
        SELECT
            *,
            sha256(
                'SAT_INCIDENCIA|'
                || cast(cantidad AS VARCHAR)
            ) AS hashdiff
        FROM silver_linked;
        """
    )

    print("Writing hubs...")

    copy_to_parquet(
        con,
        """
        SELECT
            entidad_hashkey,
            clave_entidad,
            clave_entidad_str,
            entidad,
            min(_load_datetime_utc) AS load_datetime_utc,
            min(_record_source) AS record_source
        FROM silver_vault_ready
        GROUP BY
            entidad_hashkey,
            clave_entidad,
            clave_entidad_str,
            entidad
        ORDER BY clave_entidad
        """,
        dv_dir / "hub_entidad.parquet",
    )

    copy_to_parquet(
        con,
        """
        SELECT
            municipio_hashkey,
            clave_municipio,
            clave_municipio_str,
            municipio,
            clave_entidad,
            clave_entidad_str,
            entidad,
            min(_load_datetime_utc) AS load_datetime_utc,
            min(_record_source) AS record_source
        FROM silver_vault_ready
        GROUP BY
            municipio_hashkey,
            clave_municipio,
            clave_municipio_str,
            municipio,
            clave_entidad,
            clave_entidad_str,
            entidad
        ORDER BY clave_municipio
        """,
        dv_dir / "hub_municipio.parquet",
    )

    copy_to_parquet(
        con,
        """
        SELECT
            delito_hashkey,
            bien_juridico,
            tipo_delito,
            subtipo_delito,
            modalidad,
            min(_load_datetime_utc) AS load_datetime_utc,
            min(_record_source) AS record_source
        FROM silver_vault_ready
        GROUP BY
            delito_hashkey,
            bien_juridico,
            tipo_delito,
            subtipo_delito,
            modalidad
        ORDER BY
            bien_juridico,
            tipo_delito,
            subtipo_delito,
            modalidad
        """,
        dv_dir / "hub_delito.parquet",
    )

    copy_to_parquet(
        con,
        """
        SELECT
            periodo_hashkey,
            anio,
            mes,
            anio_mes,
            fecha_periodo,
            min(_load_datetime_utc) AS load_datetime_utc,
            min(_record_source) AS record_source
        FROM silver_vault_ready
        GROUP BY
            periodo_hashkey,
            anio,
            mes,
            anio_mes,
            fecha_periodo
        ORDER BY anio, mes
        """,
        dv_dir / "hub_periodo.parquet",
    )

    print("Writing link...")

    copy_to_parquet(
        con,
        """
        SELECT
            municipio_delito_periodo_lnk_hashkey,
            municipio_hashkey,
            delito_hashkey,
            periodo_hashkey,
            min(_load_datetime_utc) AS load_datetime_utc,
            min(_record_source) AS record_source
        FROM silver_vault_ready
        GROUP BY
            municipio_delito_periodo_lnk_hashkey,
            municipio_hashkey,
            delito_hashkey,
            periodo_hashkey
        """,
        dv_dir / "link_municipio_delito_periodo.parquet",
    )

    print("Writing satellite...")

    copy_to_parquet(
        con,
        """
        SELECT
            municipio_delito_periodo_lnk_hashkey,
            _load_datetime_utc AS load_datetime_utc,
            _record_source AS record_source,
            hashdiff,
            fecha_periodo AS effective_from_date,
            cantidad,
            _source_file AS source_file,
            _source_file_sha256 AS source_file_sha256,
            _ingestion_date AS ingestion_date
        FROM silver_vault_ready
        """,
        dv_dir / "sat_incidencia_mensual.parquet",
    )

    print("=" * 100)
    print("Data Vault write completed")
    print(f"Output: {dv_dir}")

    for file_path in sorted(dv_dir.glob("*.parquet")):
        count = con.execute(
            f"SELECT count(*) FROM read_parquet('{sql_path(file_path)}')"
        ).fetchone()[0]

        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"{file_path.name}: {count:,} rows | {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
