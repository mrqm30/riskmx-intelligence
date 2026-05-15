# Data Quality Standards

## Validation Libraries
- Use **pandera** for DataFrame schema validation (column types, value ranges, nullability).
- Use **pydantic** for config objects and non-tabular data structures.

## Required Checks per Pipeline Layer

### Bronze → Silver
- Verify expected columns exist before transformation; raise `ValueError` with the list of missing columns.
- Validate encoding (SESNSP files use `latin-1`).
- Filter by target year early to reduce memory footprint.
- Fill NaN incidence values with `0` and cast to `int`.

### Silver → Gold
- Assert no null values in key columns: `cvegeo`, `clave_entidad`, `tipo_delito`, `incidencia`.
- Validate geographic codes: `clave_entidad` must be 2-digit zero-padded, `cvegeo` must be 5-digit zero-padded.
- Check for exact duplicate rows and log count.
- Validate `incidencia >= 0` (no negative counts).

## Audit Columns
Every Silver and Gold table must include:
- `record_source` — origin identifier (e.g., `"SESNSP"`).
- `load_date` — UTC timestamp of when the record was created (`pd.Timestamp.utcnow()`).

## Quality Reporting
- Print summary stats during transformation: row counts, null counts, duplicate counts, zero-incidence percentage.
- When building new pipeline steps, include a quality section that logs these metrics to stdout.

## File Format Rules
- Intermediate and output data is always **Parquet** (`index=False`).
- Raw source files in bronze are kept as-is (CSV). Never modify bronze files.
