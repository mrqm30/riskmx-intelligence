from riskmx_intelligence.settings import settings


def main() -> None:
    print("RiskMX Intelligence - Project Check")
    print("=" * 50)

    print(f"ENV: {settings.env}")
    print(f"PROJECT_NAME: {settings.project_name}")
    print(f"RECORD_SOURCE: {settings.record_source}")
    print(f"DATA_ROOT: {settings.data_root}")
    print(f"MLFLOW_TRACKING_URI: {settings.mlflow_tracking_uri}")
    print("=" * 50)

    required_paths = [
        settings.data_root,
        settings.datasets_root,
        settings.reports_root,
        settings.models_root,
        settings.artifacts_root,
        settings.logs_root,
        settings.raw_path,
        settings.bronze_path,
        settings.silver_path,
        settings.gold_path,
        settings.dv_path,
        settings.features_path,
        settings.tmp_path,
        settings.spark_warehouse_dir,
    ]

    for path in required_paths:
        path.mkdir(parents=True, exist_ok=True)
        print(f"OK: {path}")


if __name__ == "__main__":
    main()
