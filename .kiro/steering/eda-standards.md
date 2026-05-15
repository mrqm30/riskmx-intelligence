# EDA & Notebook Standards

## Notebook Structure
Every EDA notebook must follow this layout:
1. **Title cell** (H1 markdown) — descriptive name, dataset reference, and a numbered table of contents.
2. **Imports cell** — all imports and shared constants (e.g., `MONTH_LABELS`, `MONTH_ORDER`) in a single cell at the top.
3. **Data load & overview** — row/column counts, unique key counts, date range covered, `df.head()`.
4. **Data quality** — nulls, duplicates, zero-value percentage.
5. **Analysis sections** — one H2 heading per topic, each with its own code cell(s).
6. **Insights / conclusions** — final markdown cell summarizing findings in business terms.

## Visualization Conventions
- Default library: **Plotly** (`plotly.express` for simple charts, `plotly.graph_objects` for composites).
- Use `make_subplots` when combining related views side by side.
- Always set explicit `title`, `labels`, and `height` on every figure.
- Format large numbers with thousands separator: `texttemplate="%{text:,.0f}"`.
- Preferred color scales: `YlOrRd`, `Viridis`, `Reds`, `RdYlGn_r`, `Set2`.
- Hide color scale bar when color is redundant with axis: `coloraxis_showscale=False`.
- Horizontal bar charts for ranked lists (sorted ascending so highest is at top visually).

## Data Paths
- Notebooks live in `notebooks/` and reference data with relative paths (`../data/silver/...`).
- Always read from **silver** or **gold** layers, never directly from bronze.

## Language
- Markdown narrative, chart titles, and axis labels in **Spanish**.
- Variable names in code cells follow Python conventions (English or snake_case Spanish).
