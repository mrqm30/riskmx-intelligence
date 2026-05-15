# GitHub & Version Control Standards

## Branching
- Default branch: `main`.
- Feature branches: `feature/<short-description>` (e.g., `feature/add-scoring-model`).
- Fix branches: `fix/<short-description>`.
- Always push to a new branch; never commit directly to `main`.

## Commits
- Write commit messages in **Spanish** to match the project language.
- Use conventional-style prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `data:`, `chore:`.
- Keep the subject line under 72 characters.
- Reference related issue numbers when applicable.

## Pull Requests
- PR title: concise summary under 70 characters.
- PR description: brief summary of changes, what was tested, and any caveats.
- Ensure `ruff check` and `ruff format --check` pass before opening a PR.
- Run `uv run pytest` and confirm tests pass.

## What to Commit
- Source code (`src/`, `notebooks/`, `dashboard/`, `main.py`).
- Config files (`pyproject.toml`, `.gitignore`, `.python-version`).
- Documentation (`docs/`, `README.md`, `.kiro/steering/`).

## What NOT to Commit
- `data/` directory — raw and processed data stays local (already in `.gitignore` or should be).
- `.venv/` — virtual environment.
- `__pycache__/`, `*.pyc` — bytecode.
- Notebook outputs — clear outputs before committing (or use a pre-commit hook).
- Secrets, API keys, credentials.

## Pre-Push Checklist
1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run pytest`
4. Verify no data files or secrets are staged.
