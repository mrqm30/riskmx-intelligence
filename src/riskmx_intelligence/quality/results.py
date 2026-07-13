from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class QualityCheckResult:
    check_name: str
    status: str
    severity: str
    message: str
    metrics: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pass_check(
    check_name: str,
    message: str,
    metrics: dict[str, Any] | None = None,
    severity: str = "HIGH",
) -> QualityCheckResult:
    return QualityCheckResult(
        check_name=check_name,
        status="PASS",
        severity=severity,
        message=message,
        metrics=metrics or {},
    )


def fail_check(
    check_name: str,
    message: str,
    metrics: dict[str, Any] | None = None,
    severity: str = "HIGH",
) -> QualityCheckResult:
    return QualityCheckResult(
        check_name=check_name,
        status="FAIL",
        severity=severity,
        message=message,
        metrics=metrics or {},
    )