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
        raise FileNotFoundError(f"No silver files found under {base_path}")

    return files[-1]


def latest_dv_dir() -> Path:
    base_path = settings.dv_path / "sesnsp" / DATASET_NAME
    dirs = sorted(base_path.glob("ingestion_date=*"))

    if not dirs:
        raise FileNotFoundError(
            f"No Data Vault directories found under {base_path}. "
            "Run scripts/09_build_data_vault_sesnsp.py first."
        )

    return dirs[-1]


def scalar(con: duckdb.DuckDBPyConnection, query: str) -> int:
    return con.execute(query).fetchone()[0]


def check(condition: bool, message: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"{status} | {message}")

    if not condition:
        raise ValueError(message)


def main() -> None:
    silver_file = latest_silver_file()
    dv_dir = latest_dv_dir()

    files = {
        "hub_entidad": dv_dir / "hub_entidad.parquet",
        "hub_municipio": dv_dir / "hub_municipio.parquet",
        "hub_delito": dv_dir / "hub_delito.parquet",
        "hub_periodo": dv_dir / "hub_periodo.parquet",
        "link_municipio_delito_periodo": dv_dir / "link_municipio_delito_periodo.parquet",
        "sat_incidencia_mensual": dv_dir / "sat_incidencia_mensual.parquet",
    }

    print("Validating Data Vault 2.0 objects")
    print("=" * 100)
    print(f"Silver file: {silver_file}")
    print(f"DV dir: {dv_dir}")
    print("=" * 100)

    for name, path in files.items():
        check(path.exists(), f"{name} exists: {path}")

    con = duckdb.connect(database=":memory:")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW silver AS
        SELECT *
        FROM read_parquet('{sql_path(silver_file)}');
        """
    )

    for name, path in files.items():
        con.execute(
            f"""
            CREATE OR REPLACE VIEW {name} AS
            SELECT *
            FROM read_parquet('{sql_path(path)}');
            """
        )

    print("=" * 100)
    print("Row counts")

    row_counts = {
        name: scalar(con, f"SELECT count(*) FROM {name}")
        for name in files
    }
    silver_rows = scalar(con, "SELECT count(*) FROM silver")

    for name, count in row_counts.items():
        print(f"{name}: {count:,}")
    print(f"silver: {silver_rows:,}")

    check(row_counts["hub_entidad"] == 32, "hub_entidad has 32 entities")
    check(row_counts["hub_periodo"] == 132, "hub_periodo has 132 monthly periods")
    check(row_counts["link_municipio_delito_periodo"] == silver_rows, "link row count matches silver")
    check(row_counts["sat_incidencia_mensual"] == silver_rows, "satellite row count matches silver")

    print("=" * 100)
    print("Null hashkey checks")

    null_checks = {
        "hub_entidad.entidad_hashkey": "SELECT count(*) FROM hub_entidad WHERE entidad_hashkey IS NULL",
        "hub_municipio.municipio_hashkey": "SELECT count(*) FROM hub_municipio WHERE municipio_hashkey IS NULL",
        "hub_delito.delito_hashkey": "SELECT count(*) FROM hub_delito WHERE delito_hashkey IS NULL",
        "hub_periodo.periodo_hashkey": "SELECT count(*) FROM hub_periodo WHERE periodo_hashkey IS NULL",
        "link_municipio_delito_periodo.municipio_delito_periodo_lnk_hashkey": (
            "SELECT count(*) FROM link_municipio_delito_periodo "
            "WHERE municipio_delito_periodo_lnk_hashkey IS NULL"
        ),
        "sat_incidencia_mensual.hashdiff": (
            "SELECT count(*) FROM sat_incidencia_mensual WHERE hashdiff IS NULL"
        ),
    }

    for label, query in null_checks.items():
        count = scalar(con, query)
        check(count == 0, f"{label} has no nulls")

    print("=" * 100)
    print("Duplicate hashkey checks")

    duplicate_queries = {
        "hub_entidad": """
            SELECT count(*)
            FROM (
                SELECT entidad_hashkey, count(*) c
                FROM hub_entidad
                GROUP BY entidad_hashkey
                HAVING count(*) > 1
            )
        """,
        "hub_municipio": """
            SELECT count(*)
            FROM (
                SELECT municipio_hashkey, count(*) c
                FROM hub_municipio
                GROUP BY municipio_hashkey
                HAVING count(*) > 1
            )
        """,
        "hub_delito": """
            SELECT count(*)
            FROM (
                SELECT delito_hashkey, count(*) c
                FROM hub_delito
                GROUP BY delito_hashkey
                HAVING count(*) > 1
            )
        """,
        "hub_periodo": """
            SELECT count(*)
            FROM (
                SELECT periodo_hashkey, count(*) c
                FROM hub_periodo
                GROUP BY periodo_hashkey
                HAVING count(*) > 1
            )
        """,
        "link_municipio_delito_periodo": """
            SELECT count(*)
            FROM (
                SELECT municipio_delito_periodo_lnk_hashkey, count(*) c
                FROM link_municipio_delito_periodo
                GROUP BY municipio_delito_periodo_lnk_hashkey
                HAVING count(*) > 1
            )
        """,
    }

    for label, query in duplicate_queries.items():
        count = scalar(con, query)
        check(count == 0, f"{label} has no duplicated hashkeys")

    print("=" * 100)
    print("Referential integrity checks")

    orphan_municipio = scalar(
        con,
        """
        SELECT count(*)
        FROM link_municipio_delito_periodo l
        LEFT JOIN hub_municipio h
            ON l.municipio_hashkey = h.municipio_hashkey
        WHERE h.municipio_hashkey IS NULL
        """,
    )

    orphan_delito = scalar(
        con,
        """
        SELECT count(*)
        FROM link_municipio_delito_periodo l
        LEFT JOIN hub_delito h
            ON l.delito_hashkey = h.delito_hashkey
        WHERE h.delito_hashkey IS NULL
        """,
    )

    orphan_periodo = scalar(
        con,
        """
        SELECT count(*)
        FROM link_municipio_delito_periodo l
        LEFT JOIN hub_periodo h
            ON l.periodo_hashkey = h.periodo_hashkey
        WHERE h.periodo_hashkey IS NULL
        """,
    )

    orphan_satellite = scalar(
        con,
        """
        SELECT count(*)
        FROM sat_incidencia_mensual s
        LEFT JOIN link_municipio_delito_periodo l
            ON s.municipio_delito_periodo_lnk_hashkey = l.municipio_delito_periodo_lnk_hashkey
        WHERE l.municipio_delito_periodo_lnk_hashkey IS NULL
        """,
    )

    check(orphan_municipio == 0, "link has no orphan municipio_hashkey")
    check(orphan_delito == 0, "link has no orphan delito_hashkey")
    check(orphan_periodo == 0, "link has no orphan periodo_hashkey")
    check(orphan_satellite == 0, "satellite has no orphan link hashkey")

    print("=" * 100)
    print("Quantity reconciliation")

    silver_total = scalar(con, "SELECT sum(cantidad) FROM silver")
    sat_total = scalar(con, "SELECT sum(cantidad) FROM sat_incidencia_mensual")

    print(f"Silver total cantidad: {silver_total:,}")
    print(f"Satellite total cantidad: {sat_total:,}")

    check(silver_total == sat_total, "satellite total cantidad matches silver")

    print("=" * 100)
    print("DATA VAULT VALIDATION OK")


if __name__ == "__main__":
    main()
