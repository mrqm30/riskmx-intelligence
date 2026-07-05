import json
from datetime import datetime, timezone
from pathlib import Path

from riskmx_intelligence.ingestion.download import download_file
from riskmx_intelligence.settings import settings
from riskmx_intelligence.utils.hashing import calculate_sha256


SESNSP_MUNICIPAL_URL = (
    "https://repodatos.atdt.gob.mx/api_update/sesnsp/"
    "incidencia_delictiva/IDM_NM_dic25.csv"
)

SOURCE_SYSTEM = "SESNSP"
DATASET_NAME = "incidencia_delictiva_municipal"
RAW_FILENAME = "Municipal-Delitos-2015-2025_may-2026.csv"


def main() -> None:
    ingestion_datetime = datetime.now(timezone.utc)
    ingestion_date = ingestion_datetime.strftime("%Y-%m-%d")

    output_dir = (
        settings.raw_path / "sesnsp" / DATASET_NAME / f"ingestion_date={ingestion_date}"
    )

    output_path = output_dir / RAW_FILENAME
    metadata_path = output_dir / "metadata.json"

    print("Downloading SESNSP municipal crime incidence dataset")
    print("=" * 80)
    print(f"URL: {SESNSP_MUNICIPAL_URL}")
    print(f"Output: {output_path}")
    print("=" * 80)

    downloaded_path = download_file(
        url=SESNSP_MUNICIPAL_URL,
        output_path=output_path,
    )

    file_size_bytes = downloaded_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_sha256 = calculate_sha256(downloaded_path)

    metadata = {
        "source_system": SOURCE_SYSTEM,
        "dataset_name": DATASET_NAME,
        "source_url": SESNSP_MUNICIPAL_URL,
        "raw_filename": RAW_FILENAME,
        "ingestion_datetime_utc": ingestion_datetime.isoformat(),
        "ingestion_date": ingestion_date,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_mb, 4),
        "file_sha256": file_sha256,
        "record_source": settings.record_source,
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Download completed")
    print(f"File: {downloaded_path}")
    print(f"SHA256: {file_sha256}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
