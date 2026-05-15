# Tech Stack & Build System

## Runtime
- Python **3.12**
- Package manager: **uv** (lockfile: `uv.lock`, config: `pyproject.toml`)

## Key Libraries
| Category | Libraries |
|---|---|
| DataFrames | pandas, polars, openpyxl |
| File formats | pyarrow (Parquet) |
| Validation | pandera, pydantic |
| Visualization | plotly, matplotlib, seaborn, kaleido (static export) |
| Dashboard | dash |
| Analytical DB | duckdb |
| Notebooks | jupyterlab, ipykernel, nbformat |
|Test| Pytest|

## Dev Dependencies
- **pytest** — test runner
- **ruff** — linter and formatter

## Common Commands
```bash
# Install / sync dependencies
uv sync

# Run the main entry point
uv run python main.py

# Run a specific pipeline step
uv run python src/transformation/transform_sesnsp.py

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Run tests
uv run pytest
```

## Architecture:
- Bronze/Silver/Gold data layers
- Data quality validation
- Modular Python scripts
- Exploratory notebooks
- Dashboard with Dash and Plotly

Avoid:
- Hardcoded absolute paths
- Unvalidated transformations
- Unstructured notebooks without reusable scripts
- Committing large raw files if they exceed GitHub limits

## Conventions
- All CLI invocations go through `uv run` to use the project virtualenv.
- No `requirements.txt`; dependencies live exclusively in `pyproject.toml`.
- Parquet is the standard interchange format between pipeline layers.