# Project Structure

Use this structure:

data/
  bronze/
  silver/
  gold/

src/
  ingestion/
  transformation/
  quality/
  scoring/
  visualization/

notebooks/
docs/
dashboard/
tests/

Rules:
- Notebooks are for exploration only.
- Production transformations must live in src/.
- All generated silver and gold datasets must be Parquet.
- Every transformation script must have a main() function.
- All paths must use pathlib.
- Every important dataset must have a documented schema.

## Architecture Pattern — Medallion (Bronze → Silver → Gold)
- **Bronze**: Raw files as received from external sources. No transformations.
- **Silver**: Cleaned, validated, long-format Parquet files. One record per observation.
- **Gold**: Aggregated, scored, or joined datasets ready for consumption by dashboards or APIs.

## Code Conventions
- Each pipeline stage lives in its own `src/` subpackage (`ingestion`, `transformation`, `quality`, `scoring`).
- Modules define `INPUT_PATH` / `OUTPUT_PATH` constants at the top and expose a `main()` function as the entry point.
- Path handling uses `pathlib.Path`.
- Column renaming normalizes Spanish source headers to lowercase snake_case.
- Audit columns (`record_source`, `load_date`) are appended during transformation.