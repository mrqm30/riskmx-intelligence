import re
import unicodedata


def normalize_column_name(column_name: str) -> str:
    """
    Normalize a column name to snake_case ASCII.

    Exemple:
    'Bien jurídico afectado' -> 'bien_juridico_afectado'
    """

    normalized = unicodedata.normalize("NFKD", column_name)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")

    return normalized


def normalize_column_names(column_names: list[str]) -> list[str]:
    return [normalize_column_name(column_name) for column_name in column_names]
