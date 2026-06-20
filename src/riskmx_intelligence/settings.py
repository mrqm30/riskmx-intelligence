from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "local"
    project_name: str = "riskmx-intelligence"
    record_source: str = "SESNSP"

    data_root: Path = Path("/data/lakehouse/riskmx-intelligence")
    datasets_root: Path = Path("/data/datasets/riskmx-intelligence")
    reports_root: Path = Path("/data/reports/risk-intelligence")
    models_root: Path = Path("/data/models/risk-intelligence")
    artifacts_root: Path = Path("/data/artifacts/risk-intelligence")
    logs_root: Path = Path("/data/logs/risk-intelligence")
    mlflow_tracking_uri: str = "file:///data/mlruns/risk-intelligence"
    spark_warehouse_dir: Path = Path("/data/spark-warehouse")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def raw_path(self) -> Path:
        return self.data_root / "raw"

    @property
    def bronze_path(self) -> Path:
        return self.data_root / "bronze"

    @property
    def silver_path(self) -> Path:
        return self.data_root / "silver"

    @property
    def gold_path(self) -> Path:
        return self.data_root / "gold"

    @property
    def dv_path(self) -> Path:
        return self.data_root / "dv"

    @property
    def features_path(self) -> Path:
        return self.data_root / "features"

    @property
    def tmp_path(self) -> Path:
        return self.data_root / "tmp"


settings = Settings()
