# Requirements Document

## Introduction

RiskMX Intelligence v1 implements a complete exploratory data analysis pipeline over SESNSP municipal crime incidence data. The pipeline follows the Bronze → Silver → Gold medallion architecture: it ingests the raw CSV file (latin-1 encoded, wide format with 12 monthly columns), transforms it into a clean long-format Silver Parquet dataset, validates data quality with pandera, produces Gold-layer analytical datasets (municipal monthly metrics, state-month aggregations, crime type summaries, and a Pareto concentration table), generates EDA visualizations with Plotly, and prepares all outputs for consumption by a Dash dashboard and GitHub portfolio documentation. The tech stack uses Python 3.12, uv, pandas, pyarrow, duckdb, plotly, pandera, and pydantic.

## Glossary

- **Pipeline**: The orchestrated sequence of scripts that ingests Bronze data, transforms it to Silver, validates quality, produces Gold datasets, generates EDA outputs, and prepares dashboard-ready artifacts.
- **Bronze_CSV**: The raw SESNSP CSV file at `data/bronze/sesnsp/Municipal-Delitos-2015-2025_mar2026.csv`, encoded in latin-1, with Spanish column headers and 12 monthly columns in wide format.
- **Ingester**: The module in `src/ingestion/` that reads the Bronze_CSV, filters by year, and validates the expected column structure.
- **Transformer**: The module in `src/transformation/` that melts the wide-format DataFrame into long format, constructs geographic keys, normalizes column names, and appends audit columns.
- **Silver_Dataset**: The cleaned, long-format Parquet file at `data/silver/crime_monthly/sesnsp_crime_monthly_{year}.parquet` containing one row per municipality-month-crime combination with 15 columns.
- **Validator**: The pandera-based schema validation module in `src/quality/` that checks Silver and Gold data against defined schemas.
- **Aggregator**: The module in `src/scoring/` that reads validated Silver data and produces Gold-layer aggregated datasets.
- **Gold_Dataset**: An aggregated Parquet file in `data/gold/municipal_risk/` ready for consumption by dashboards, scoring models, or external consumers.
- **DuckDB_Analyzer**: The component that uses duckdb to execute analytical SQL queries over Gold Parquet datasets for EDA and dashboard preparation.
- **Report_Generator**: The module in `src/visualization/` that reads Gold datasets and produces Plotly-based HTML charts and a summary insights file.
- **Orchestrator**: The `main.py` entry point that runs the full pipeline end-to-end: ingest → transform → validate Silver → aggregate Gold → validate Gold → generate EDA → prepare dashboard outputs.
- **cvegeo**: The 5-digit zero-padded INEGI municipal geographic code that uniquely identifies a municipality, constructed by zero-padding `Cve. Municipio` from the source CSV.
- **clave_entidad**: The 2-digit zero-padded state code derived from `Clave_Ent` in the source CSV.
- **incidencia**: The integer count of crime incidents for a given municipality-month-crime combination.
- **bien_juridico**: The legal category of the crime (e.g., patrimonio, vida e integridad corporal).
- **tipo_delito**: The crime type classification (e.g., Robo, Homicidio, Violencia familiar).
- **Pareto_Table**: A Gold dataset ranking municipalities by cumulative share of total incidence.
- **Municipal_Monthly_Table**: A Gold dataset at municipality-month granularity with aggregated crime metrics.
- **Dash_App**: The Dash-based interactive dashboard in `dashboard/` that consumes Gold datasets and EDA outputs.
- **MONTH_MAP**: A dictionary mapping Spanish month names (Enero through Diciembre) to integer values 1 through 12.

## Requirements

### Requirement 1: Ingest Bronze CSV File

**User Story:** As a data engineer, I want to read the raw SESNSP CSV file with correct encoding and filter by year, so that downstream transformations receive a clean, year-scoped DataFrame.

#### Acceptance Criteria

1. WHEN the Ingester receives the Bronze_CSV path, THE Ingester SHALL read the file using `latin-1` encoding.
2. WHEN the Ingester reads the Bronze_CSV, THE Ingester SHALL verify that all 21 expected columns exist: the 9 ID columns (`Año`, `Clave_Ent`, `Entidad`, `Cve. Municipio`, `Municipio`, `Bien jurídico afectado`, `Tipo de delito`, `Subtipo de delito`, `Modalidad`) and the 12 month columns (`Enero` through `Diciembre`).
3. IF any expected column is missing from the Bronze_CSV, THEN THE Ingester SHALL raise a `ValueError` listing all missing column names.
4. WHEN the Ingester receives a `year` parameter, THE Ingester SHALL filter the DataFrame to rows where `Año` equals the specified year.
5. IF the Bronze_CSV file does not exist at the specified path, THEN THE Ingester SHALL raise a `FileNotFoundError` with a message identifying the missing path.
6. WHEN the Ingester completes reading, THE Ingester SHALL print to stdout the number of rows loaded and the number of rows after year filtering.

### Requirement 2: Transform Wide Format to Long Format

**User Story:** As a data engineer, I want to melt the 12 monthly columns into a single long-format DataFrame, so that each row represents one municipality-month-crime observation.

#### Acceptance Criteria

1. WHEN the Transformer receives the year-filtered DataFrame, THE Transformer SHALL melt the 12 month columns (`Enero` through `Diciembre`) into two new columns: `mes_nombre` (the Spanish month name) and `incidencia` (the crime count value).
2. THE Transformer SHALL map each `mes_nombre` value to an integer `mes` column using the MONTH_MAP (Enero=1, Febrero=2, ..., Diciembre=12).
3. THE Transformer SHALL construct a `fecha` column as a `datetime64` value representing the first day of the corresponding month and year (format: `YYYY-MM-01`).
4. THE Transformer SHALL fill null `incidencia` values with `0` and cast the column to `int64`.
5. FOR ALL input DataFrames with N rows, the Transformer output SHALL contain exactly N × 12 rows (one row per original row per month).

### Requirement 3: Construct CVEGEO Municipal Key

**User Story:** As a data engineer, I want to build a standardized 5-digit zero-padded municipal code from the source data, so that geographic joins and lookups are consistent across the pipeline.

#### Acceptance Criteria

1. THE Transformer SHALL construct the `cvegeo` column by converting `Cve. Municipio` to a string and zero-padding to exactly 5 characters.
2. THE Transformer SHALL construct the `clave_entidad` column by converting `Clave_Ent` to a string and zero-padding to exactly 2 characters.
3. FOR ALL rows in the output, `cvegeo` values SHALL match the regex pattern `^\d{5}$`.
4. FOR ALL rows in the output, `clave_entidad` values SHALL match the regex pattern `^\d{2}$`.

### Requirement 4: Normalize Columns and Save Silver Parquet

**User Story:** As a data engineer, I want to rename Spanish source headers to snake_case, append audit columns, and save the result as a Parquet file, so that the Silver layer is clean, documented, and efficient to read.

#### Acceptance Criteria

1. THE Transformer SHALL rename source columns to snake_case: `Año` → `anio`, `Entidad` → `entidad`, `Municipio` → `municipio`, `Bien jurídico afectado` → `bien_juridico`, `Tipo de delito` → `tipo_delito`, `Subtipo de delito` → `subtipo_delito`, `Modalidad` → `modalidad`.
2. THE Transformer SHALL append a `record_source` column with the value `"SESNSP"` for all rows.
3. THE Transformer SHALL append a `load_date` column with the current UTC timestamp at the time of execution.
4. THE Transformer SHALL output the Silver_Dataset with exactly 15 columns in order: `anio`, `fecha`, `mes`, `mes_nombre`, `clave_entidad`, `cvegeo`, `entidad`, `municipio`, `bien_juridico`, `tipo_delito`, `subtipo_delito`, `modalidad`, `incidencia`, `record_source`, `load_date`.
5. THE Transformer SHALL save the Silver_Dataset as a Parquet file at `data/silver/crime_monthly/sesnsp_crime_monthly_{year}.parquet` with `index=False`.
6. THE Transformer SHALL create parent directories if they do not exist before writing the Parquet file.

### Requirement 5: Validate Silver Dataset Schema

**User Story:** As a data engineer, I want to validate the Silver dataset schema before any aggregation, so that downstream Gold datasets are built on verified, clean data.

#### Acceptance Criteria

1. WHEN the Validator receives the Silver_Dataset path, THE Validator SHALL load the Parquet file and check all 15 columns against a pandera DataFrameSchema.
2. THE Validator SHALL verify that `cvegeo` values are 5-character zero-padded strings matching the pattern `^\d{5}$`.
3. THE Validator SHALL verify that `clave_entidad` values are 2-character zero-padded strings matching the pattern `^\d{2}$`.
4. THE Validator SHALL verify that `incidencia` values are integers greater than or equal to zero.
5. THE Validator SHALL verify that `mes` values are integers in the range 1 to 12 inclusive.
6. THE Validator SHALL verify that no null values exist in columns `cvegeo`, `clave_entidad`, `tipo_delito`, `subtipo_delito`, `modalidad`, and `incidencia`.
7. IF the Silver_Dataset fails any schema check, THEN THE Validator SHALL raise a `pandera.errors.SchemaError` with a message identifying the failing column and constraint.
8. WHEN the Silver_Dataset passes all schema checks, THE Validator SHALL print a summary to stdout containing row count, column count, number of unique municipalities, and number of unique crime types.

### Requirement 6: Aggregate Municipal Monthly Crime Metrics (Gold)

**User Story:** As a risk analyst, I want a Gold dataset at municipality-month granularity with aggregated crime metrics, so that I can analyze monthly crime trends per municipality.

#### Acceptance Criteria

1. WHEN the Aggregator reads the validated Silver_Dataset, THE Aggregator SHALL produce a Municipal_Monthly_Table at `data/gold/municipal_risk/crime_municipal_monthly.parquet` with one row per municipality-month combination.
2. THE Municipal_Monthly_Table SHALL contain columns: `cvegeo`, `clave_entidad`, `entidad`, `municipio`, `anio`, `mes`, `mes_nombre`, `fecha`, `total_incidencia`, `num_crime_types`, `num_subtypes`, `record_source`, and `load_date`.
3. THE Aggregator SHALL compute `total_incidencia` as the sum of `incidencia` grouped by `cvegeo` and `mes`.
4. THE Aggregator SHALL compute `num_crime_types` as the count of distinct `tipo_delito` values with `incidencia > 0` for each municipality-month pair.
5. THE Aggregator SHALL compute `num_subtypes` as the count of distinct `subtipo_delito` values with `incidencia > 0` for each municipality-month pair.
6. THE Municipal_Monthly_Table SHALL be sorted by `cvegeo` ascending, then by `mes` ascending.
7. THE Aggregator SHALL append `record_source` with value `"SESNSP"` and `load_date` with the current UTC timestamp.

### Requirement 7: Aggregate Crime Incidence by Municipality (Gold)

**User Story:** As a risk analyst, I want a Gold dataset aggregating total crime incidence per municipality across all months and crime types, so that I can rank municipalities by overall crime volume.

#### Acceptance Criteria

1. WHEN the Aggregator reads the validated Silver_Dataset, THE Aggregator SHALL produce a Gold_Dataset at `data/gold/municipal_risk/crime_by_municipality.parquet` with one row per municipality.
2. THE Gold_Dataset SHALL contain columns: `cvegeo`, `clave_entidad`, `entidad`, `municipio`, `total_incidencia`, `num_crime_types`, `num_months_with_crime`, `record_source`, and `load_date`.
3. THE Aggregator SHALL compute `total_incidencia` as the sum of `incidencia` grouped by `cvegeo`.
4. THE Aggregator SHALL compute `num_crime_types` as the count of distinct `tipo_delito` values with `incidencia > 0` for each municipality.
5. THE Aggregator SHALL compute `num_months_with_crime` as the count of distinct `mes` values where the municipality has at least one record with `incidencia > 0`.
6. THE Gold_Dataset SHALL be sorted in descending order by `total_incidencia`.
7. THE Aggregator SHALL append `record_source` with value `"SESNSP"` and `load_date` with the current UTC timestamp.

### Requirement 8: Aggregate Crime Incidence by State and Month (Gold)

**User Story:** As a risk analyst, I want a Gold dataset with monthly crime totals per state, so that I can analyze temporal trends and seasonality at the state level.

#### Acceptance Criteria

1. WHEN the Aggregator reads the validated Silver_Dataset, THE Aggregator SHALL produce a Gold_Dataset at `data/gold/municipal_risk/crime_by_state_month.parquet` with one row per state-month combination.
2. THE Gold_Dataset SHALL contain columns: `clave_entidad`, `entidad`, `anio`, `mes`, `mes_nombre`, `total_incidencia`, `num_municipalities_with_crime`, `record_source`, and `load_date`.
3. THE Aggregator SHALL compute `total_incidencia` as the sum of `incidencia` grouped by `clave_entidad` and `mes`.
4. THE Aggregator SHALL compute `num_municipalities_with_crime` as the count of distinct `cvegeo` values with `incidencia > 0` for each state-month pair.
5. THE Gold_Dataset SHALL be sorted by `clave_entidad` ascending, then by `mes` ascending.

### Requirement 9: Aggregate Crime Incidence by Crime Type (Gold)

**User Story:** As a risk analyst, I want a Gold dataset summarizing incidence by crime type and legal category, so that I can identify the dominant crime types and their distribution.

#### Acceptance Criteria

1. WHEN the Aggregator reads the validated Silver_Dataset, THE Aggregator SHALL produce a Gold_Dataset at `data/gold/municipal_risk/crime_by_type.parquet` with one row per `bien_juridico`-`tipo_delito` combination.
2. THE Gold_Dataset SHALL contain columns: `bien_juridico`, `tipo_delito`, `total_incidencia`, `num_municipalities_affected`, `pct_of_total`, `record_source`, and `load_date`.
3. THE Aggregator SHALL compute `total_incidencia` as the sum of `incidencia` grouped by `bien_juridico` and `tipo_delito`.
4. THE Aggregator SHALL compute `num_municipalities_affected` as the count of distinct `cvegeo` values with `incidencia > 0` for each crime type.
5. THE Aggregator SHALL compute `pct_of_total` as `total_incidencia` divided by the grand total of all incidence, expressed as a float between 0.0 and 1.0.
6. THE Gold_Dataset SHALL be sorted in descending order by `total_incidencia`.

### Requirement 10: Generate Pareto Concentration Table (Gold)

**User Story:** As a risk analyst, I want a Pareto table ranking municipalities by cumulative share of total incidence, so that I can identify the geographic concentration of crime.

#### Acceptance Criteria

1. WHEN the Aggregator reads the crime-by-municipality Gold_Dataset, THE Aggregator SHALL produce a Pareto_Table at `data/gold/municipal_risk/pareto_municipalities.parquet`.
2. THE Pareto_Table SHALL contain columns: `rank`, `cvegeo`, `clave_entidad`, `entidad`, `municipio`, `total_incidencia`, `pct_of_total`, `cumulative_pct`, `record_source`, and `load_date`.
3. THE Aggregator SHALL assign `rank` as a sequential integer starting at 1, ordered by `total_incidencia` descending.
4. THE Aggregator SHALL compute `pct_of_total` as the municipality's `total_incidencia` divided by the grand total.
5. THE Aggregator SHALL compute `cumulative_pct` as the running sum of `pct_of_total` from rank 1 onward.
6. FOR ALL rows in the Pareto_Table, `cumulative_pct` at the last row SHALL equal 1.0 (within floating-point tolerance of 1e-9).

### Requirement 11: Execute Analytical Queries with DuckDB

**User Story:** As a data engineer, I want to use duckdb to run analytical SQL queries over Gold Parquet datasets, so that complex aggregations and ad-hoc analysis are fast and expressive.

#### Acceptance Criteria

1. THE DuckDB_Analyzer SHALL read Gold Parquet files directly using `duckdb.sql()` or `duckdb.read_parquet()` without requiring a persistent database file.
2. WHEN the DuckDB_Analyzer executes a query, THE DuckDB_Analyzer SHALL return results as a pandas DataFrame for compatibility with downstream Plotly and Dash components.
3. THE DuckDB_Analyzer SHALL provide at minimum the following pre-built queries: top N municipalities by total incidence, monthly trend by state, crime type distribution, and Pareto cumulative percentages.
4. THE DuckDB_Analyzer SHALL accept parameterized inputs (year, top N count, state filter) to support flexible dashboard filtering.
5. IF a Gold Parquet file referenced by a query does not exist, THEN THE DuckDB_Analyzer SHALL raise a `FileNotFoundError` with a message identifying the missing file.

### Requirement 12: Validate Gold Dataset Schemas

**User Story:** As a data engineer, I want pandera schemas for each Gold dataset, so that I can catch schema regressions automatically.

#### Acceptance Criteria

1. THE Validator SHALL define a pandera DataFrameSchema for each Gold_Dataset: `crime_municipal_monthly`, `crime_by_municipality`, `crime_by_state_month`, `crime_by_type`, and `pareto_municipalities`.
2. WHEN a Gold_Dataset is produced, THE Aggregator SHALL validate the output DataFrame against its corresponding pandera schema before writing to Parquet.
3. IF a Gold_Dataset fails schema validation, THEN THE Aggregator SHALL raise a `pandera.errors.SchemaError` with a message identifying the dataset name, failing column, and constraint.
4. THE Validator SHALL verify that `pct_of_total` values in `crime_by_type` and `pareto_municipalities` are floats in the range 0.0 to 1.0 inclusive.
5. THE Validator SHALL verify that `cumulative_pct` values in `pareto_municipalities` are monotonically non-decreasing.

### Requirement 13: Generate EDA Visualizations

**User Story:** As a stakeholder, I want a set of Plotly HTML charts generated from the Gold datasets, so that I can review crime insights without running a notebook.

#### Acceptance Criteria

1. WHEN the Report_Generator reads the Gold datasets, THE Report_Generator SHALL produce HTML chart files in `data/gold/municipal_risk/charts/`.
2. THE Report_Generator SHALL generate a horizontal bar chart of the top 20 municipalities by total incidence, saved as `top20_municipalities.html`.
3. THE Report_Generator SHALL generate a heatmap of state × month total incidence, saved as `heatmap_state_month.html`.
4. THE Report_Generator SHALL generate a horizontal bar chart of crime types by total incidence, saved as `crime_types.html`.
5. THE Report_Generator SHALL generate a Pareto curve (line chart with cumulative percentage on the y-axis and municipality rank on the x-axis), saved as `pareto_curve.html`.
6. THE Report_Generator SHALL generate a line chart showing monthly crime trends for the top 5 crime types, saved as `top5_crime_trends.html`.
7. THE Report_Generator SHALL set explicit `title`, `labels`, and `height` on every generated figure.
8. THE Report_Generator SHALL use Spanish for chart titles and axis labels.
9. THE Report_Generator SHALL format large numbers with thousands separator using `texttemplate="%{text:,.0f}"` where applicable.

### Requirement 14: Generate Summary Insights File

**User Story:** As a stakeholder, I want a machine-readable JSON summary of key EDA findings, so that downstream systems and dashboards can consume the insights programmatically.

#### Acceptance Criteria

1. WHEN the Report_Generator completes chart generation, THE Report_Generator SHALL produce a JSON file at `data/gold/municipal_risk/eda_summary.json`.
2. THE JSON file SHALL contain a top-level object with keys: `dataset_overview`, `geographic_concentration`, `crime_type_distribution`, `temporal_patterns`, and `metadata`.
3. THE `dataset_overview` object SHALL include: `total_rows`, `total_incidencia`, `num_states`, `num_municipalities`, `num_crime_types`, `pct_zero_incidence`.
4. THE `geographic_concentration` object SHALL include: `top_10_states_pct` (percentage of total incidence from the top 10 states), `top_20_municipalities_pct` (percentage from the top 20 municipalities), and `top_20_municipalities` (list of municipality names).
5. THE `crime_type_distribution` object SHALL include: `top_5_crime_types` (list of objects with `tipo_delito` and `total_incidencia`).
6. THE `temporal_patterns` object SHALL include: `highest_month` (month name with highest total incidence) and `lowest_month` (month name with lowest total incidence).
7. THE `metadata` object SHALL include: `generated_at` (ISO 8601 UTC timestamp), `source_file` (path to the Silver_Dataset), and `pipeline_version` (string).

### Requirement 15: Prepare Outputs for Dash Dashboard

**User Story:** As a frontend developer, I want Gold datasets and EDA outputs structured for consumption by a Dash application, so that the dashboard can load data efficiently without re-running the pipeline.

#### Acceptance Criteria

1. THE Pipeline SHALL produce all Gold Parquet files in `data/gold/municipal_risk/` in a layout that the Dash_App can read directly using `pd.read_parquet()` or `duckdb.read_parquet()`.
2. THE Pipeline SHALL produce the `eda_summary.json` file that the Dash_App can load for displaying key metrics and overview cards.
3. THE Pipeline SHALL produce all HTML chart files in `data/gold/municipal_risk/charts/` that the Dash_App can embed as iframe components or serve as static assets.
4. THE Report_Generator SHALL export static PNG versions of each chart to `data/gold/municipal_risk/charts/` using kaleido, with filenames matching the HTML versions but with `.png` extension, for use in GitHub documentation.
5. WHEN all outputs are generated, THE Pipeline SHALL print a manifest to stdout listing every output file path and its type (parquet, html, png, json).

### Requirement 16: Generate GitHub Documentation Artifacts

**User Story:** As a portfolio owner, I want documentation artifacts (markdown summaries and static chart images) generated by the pipeline, so that the GitHub repository showcases the analysis professionally.

#### Acceptance Criteria

1. THE Report_Generator SHALL produce a markdown file at `docs/eda_report.md` containing a structured EDA summary with embedded chart images (referencing the PNG files).
2. THE markdown file SHALL include sections: Dataset Overview, Data Quality Summary, Geographic Concentration, Crime Type Distribution, Temporal Patterns, and Key Insights.
3. THE markdown file SHALL use Spanish for section titles and narrative text.
4. THE markdown file SHALL reference chart images using relative paths from the `docs/` directory (e.g., `../data/gold/municipal_risk/charts/top20_municipalities.png`).
5. THE Report_Generator SHALL include a table in the markdown file listing all Gold datasets with their file paths, row counts, and column counts.

### Requirement 17: Orchestrate Full Pipeline Execution

**User Story:** As a data engineer, I want a single command to run the entire pipeline end-to-end from Bronze ingestion through EDA output generation, so that the process is reproducible and scriptable.

#### Acceptance Criteria

1. WHEN a user executes `uv run python main.py`, THE Orchestrator SHALL run the pipeline steps in order: ingest Bronze CSV, transform to long format, save Silver Parquet, validate Silver data, produce Gold aggregations, validate Gold schemas, generate EDA charts and summary JSON, export static PNGs, and generate the documentation markdown.
2. THE Orchestrator SHALL print a progress message to stdout before each pipeline step, identifying the step name and input/output paths.
3. IF any pipeline step fails, THEN THE Orchestrator SHALL print the error message to stderr and exit with a non-zero exit code without running subsequent steps.
4. WHEN all pipeline steps complete successfully, THE Orchestrator SHALL print a final summary to stdout listing all generated output files and their row counts (for Parquet files) or file sizes (for HTML/JSON/PNG files).

### Requirement 18: Support Configurable Pipeline Parameters

**User Story:** As a data engineer, I want to configure the pipeline year, input path, and output paths via a pydantic settings model, so that the pipeline can be reused for different years without code changes.

#### Acceptance Criteria

1. THE Pipeline SHALL define a pydantic `BaseModel` named `PipelineConfig` with fields: `year` (int, default 2025), `bronze_input_path` (Path, default `data/bronze/sesnsp/Municipal-Delitos-2015-2025_mar2026.csv`), `silver_output_dir` (Path, default `data/silver/crime_monthly/`), `gold_output_dir` (Path, default `data/gold/municipal_risk/`), and `charts_output_dir` (Path, default `data/gold/municipal_risk/charts/`).
2. WHEN the Orchestrator starts, THE Orchestrator SHALL instantiate `PipelineConfig` with default values and pass the configuration to each pipeline step.
3. THE PipelineConfig SHALL validate that `year` is an integer between 2015 and 2030 inclusive.
4. THE PipelineConfig SHALL validate that `bronze_input_path` points to an existing file.
5. IF `PipelineConfig` validation fails, THEN THE Orchestrator SHALL print the validation error and exit with a non-zero exit code before running any pipeline step.
