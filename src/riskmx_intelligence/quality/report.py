import json
from datetime import datetime, timezone
from pathlib import Path

from riskmx_intelligence.quality.results import QualityCheckResult


def write_quality_report(
    results: list[QualityCheckResult],
    output_dir: Path,
    dataset_name: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    total_checks = len(results)
    passed_checks = sum(result.passed for result in results)
    failed_checks = total_checks - passed_checks

    report = {
        "dataset_name": dataset_name,
        "generated_at_utc": generated_at,
        "summary": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "status": "PASS" if failed_checks == 0 else "FAIL",
        },
        "checks": [result.to_dict() for result in results],
    }

    json_path = output_dir / "data_quality_report.json"
    md_path = output_dir / "data_quality_report.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_lines = [
        f"# Data Quality Report — {dataset_name}",
        "",
        f"Generated at UTC: `{generated_at}`",
        "",
        "## Summary",
        "",
        f"- Total checks: **{total_checks}**",
        f"- Passed checks: **{passed_checks}**",
        f"- Failed checks: **{failed_checks}**",
        f"- Status: **{report['summary']['status']}**",
        "",
        "## Checks",
        "",
        "| Check | Status | Severity | Message |",
        "|---|---:|---:|---|",
    ]

    for result in results:
        markdown_lines.append(
            f"| `{result.check_name}` | **{result.status}** | {result.severity} | {result.message} |"
        )

    markdown_lines.extend(
        [
            "",
            "## Metrics",
            "",
        ]
    )

    for result in results:
        markdown_lines.append(f"### {result.check_name}")
        markdown_lines.append("")
        markdown_lines.append("```json")
        markdown_lines.append(json.dumps(result.metrics, indent=2, ensure_ascii=False))
        markdown_lines.append("```")
        markdown_lines.append("")

    md_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    return json_path, md_path