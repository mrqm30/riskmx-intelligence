from pathlib import Path
import polars as pl
from riskmx_intelligence.settings import settings

print(settings.raw_path)

DATASET_NAME = "incidencia_delictiva_municipal"
RAW_FILENAME = "Municipal-Delitos-2015-2025_may-2026.csv"


def get_latest_raw_file() -> Path:
    base_path = settings.raw_path / "sesnsp" / DATASET_NAME

    # Primero busca en subcarpetas ingestion_date=*/
    files = sorted(base_path.glob("ingestion_date=*/{RAW_FILENAME}"))

    # Si no hay, busca suelto en la raíz
    if not files:
        files = sorted(base_path.glob("Municipal-Delitos*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No raw files found under {base_path}. "
            "Run scripts/01_download_raw_sesnsp.py first."
        )
    return files[-1]


def main() -> None:
    raw_file = get_latest_raw_file()

    print("Profiling raw SESNSP file")
    print("=" * 100)
    print(f"File: {raw_file}")
    print("=" * 100)

    df = pl.read_csv(
        raw_file,
        infer_schema_length=10000,
        ignore_errors=True,
        encoding="latin1"
    )

    print(f"Rows: {df.height:,}")
    print(f"Columns: {df.width:,}")
    print("=" * 100)

    print("Schema:")
    for column, dtype in df.schema.items():
        print(f"- {column}: {dtype}")

    print("=" * 100)
    print("First 5 rows:")
    print(df.head())

    print("=" * 100)
    print("Null counts:")
    print(df.null_count())

    print("=" * 100)
    print("Column names:")
    for idx, column in enumerate(df.columns, start=1):
        print(f"{idx:02d}.{column}")


if __name__ == "__main__":
    main()
