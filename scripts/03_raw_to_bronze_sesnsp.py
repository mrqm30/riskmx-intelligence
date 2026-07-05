import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from riskmx_intelligence.settings import settings
from riskmx_intelligence.transform.columns import normalize_column_names

DATASET_NAME = "incidencia_delictiva_municipal"
RAW_FILENAME = "Municipal-Delitos-2015-2025_may2026.csv"


def get_latest_raw_dir() -> Path:
    base_path = settings.raw_path / "sesnsp" / DATASET_NAME
    dirs = sorted(base_path.glob("ingestion_date=*"))

    if not dirs:
        raise FileExistsError(
            f"No raw ingestion directories found under {base_path}. "
            "Run scripts/01_download_raw_sesnsp.py first."
        )

    return dirs[-1]


raw_dir = get_latest_raw_dir()
print(raw_dir)


def main() -> None:
    raw_dir = get_latest_raw_dir()
    raw_file = raw_dir / RAW_FILENAME
    metadata_file = raw_dir / "metadata.json"

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw file does not exist: {raw_file}")

    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file does not exist: {metadata_file}")


    metadata = json.loads(metadata_file.read_text(encoding="latin1"))

    ingestion_date = metadata["ingestion_date"]
    source_file_sha256 = metadata["file_sha256"]
    source_file = str(raw_file)
    load_datetime_utc = datetime.now(timezone.utc).isoformat()

    bronze_dir = (
        settings.bronze_path
        / "sesnsp"
        / DATASET_NAME
        / f"ingestion_date={ingestion_date}"
    )

    bronze_dir.mkdir(parents=True, exist_ok=True)
    bronze_file = bronze_dir / "data.parquet"

    print("Transforming RAW to BRONZE")
    print("=" * 100)
    print(f"Raw file: {raw_file}")
    print(f"Bronze file: {bronze_file}")
    print("=" * 100)

    df = pl.read_csv(
        raw_file,
        infer_schema_length=10000,
        ignore_errors=True,
        encoding="latin1",
    )
    print("="*100)
    print(df)
    original_columns = df.columns
    print("="*100)
    print(original_columns)
    normalized_columns = normalize_column_names(original_columns)

    df = df.rename(dict(zip(original_columns, normalized_columns)))

    df = df.with_columns(
        [
            pl.lit(metadata["record_source"]).alias("_record_source"),
            pl.lit(load_datetime_utc).alias("_load_datetime_utc"),
            pl.lit(source_file).alias("_source_file"),
            pl.lit(source_file_sha256).alias("_source_file_sha256"),
            pl.lit(ingestion_date).alias("_ingestion_date"),
        ]
    )

    df.write_parquet(
        bronze_file,
        compression="zstd",
        statistics=True,
    )

    print("Bronze write completed")
    print(f"Rows: {df.height:,}")
    print(f"Columns: {df.width:,}")
    print(f"Output: {bronze_file}")


if __name__ == "__main__":
    main()