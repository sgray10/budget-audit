from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReconciliationResult:
    label: str
    expected: Decimal
    actual: Decimal
    difference: Decimal
    passed: bool


def reconcile_total(label: str, expected: Decimal, values: list[Decimal], tolerance: Decimal = Decimal("0.00")) -> ReconciliationResult:
    """Compare a stated total to the sum of extracted values."""
    actual = sum(values, Decimal("0"))
    difference = actual - expected
    return ReconciliationResult(
        label=label,
        expected=expected,
        actual=actual,
        difference=difference,
        passed=abs(difference) <= tolerance,
    )


def material_delta(old: Decimal | None, new: Decimal | None) -> tuple[Decimal | None, Decimal | None]:
    """Return absolute and percent delta.

    Percent delta is returned as a percentage, e.g. 12.5 means +12.5%.
    """
    if old is None or new is None:
        return None, None
    absolute = new - old
    if old == 0:
        return absolute, None
    return absolute, (absolute / abs(old)) * Decimal("100")
