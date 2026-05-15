from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/bronze/sesnsp/Municipal-Delitos-2015-2025_mar2026.csv")
OUTPUT_PATH = Path("data/silver/crime_monthly/sesnsp_crime_monthly_2025.parquet")


MONTH_MAP = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


ID_COLUMNS = [
    "Año",
    "Clave_Ent",
    "Entidad",
    "Cve. Municipio",
    "Municipio",
    "Bien jurídico afectado",
    "Tipo de delito",
    "Subtipo de delito",
    "Modalidad",
]


def read_sesnsp_csv(input_path: Path, year: int = 2025) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {input_path}")

    df = pd.read_csv(input_path, encoding="latin-1")
    df = df[df["Año"] == year]
    return df


def transform_to_long_format(df: pd.DataFrame) -> pd.DataFrame:
    month_columns = list(MONTH_MAP.keys())

    required_columns = ID_COLUMNS + month_columns
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Faltan columnas en el archivo: {missing_columns}")

    df_long = df.melt(
        id_vars=ID_COLUMNS,
        value_vars=month_columns,
        var_name="mes_nombre",
        value_name="incidencia",
    )

    df_long["mes"] = df_long["mes_nombre"].map(MONTH_MAP)

    df_long["fecha"] = pd.to_datetime(
        df_long["Año"].astype(str)
        + "-"
        + df_long["mes"].astype(str).str.zfill(2)
        + "-01"
    )

    df_long["clave_entidad"] = df_long["Clave_Ent"].astype(str).str.zfill(2)
    df_long["cvegeo"] = df_long["Cve. Municipio"].astype(str).str.zfill(5)

    df_long = df_long.rename(
        columns={
            "Año": "anio",
            "Entidad": "entidad",
            "Municipio": "municipio",
            "Bien jurídico afectado": "bien_juridico",
            "Tipo de delito": "tipo_delito",
            "Subtipo de delito": "subtipo_delito",
            "Modalidad": "modalidad",
        }
    )

    df_long["incidencia"] = df_long["incidencia"].fillna(0).astype(int)
    df_long["record_source"] = "SESNSP"
    df_long["load_date"] = pd.Timestamp.utcnow()

    final_columns = [
        "anio",
        "fecha",
        "mes",
        "mes_nombre",
        "clave_entidad",
        "cvegeo",
        "entidad",
        "municipio",
        "bien_juridico",
        "tipo_delito",
        "subtipo_delito",
        "modalidad",
        "incidencia",
        "record_source",
        "load_date",
    ]

    return df_long[final_columns]


def save_parquet(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)


def main() -> None:
    print("Leyendo archivo SESNSP...")
    df = read_sesnsp_csv(INPUT_PATH)

    print(f"Filas originales: {len(df):,}")
    print(f"Columnas originales: {len(df.columns):,}")

    print("Transformando de formato wide a formato long...")
    df_long = transform_to_long_format(df)

    print(f"Filas transformadas: {len(df_long):,}")

    print("Guardando archivo Parquet...")
    save_parquet(df_long, OUTPUT_PATH)

    print(f"Archivo generado correctamente en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()