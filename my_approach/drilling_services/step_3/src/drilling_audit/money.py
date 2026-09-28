"""Money helpers. Every amount is a ``Decimal`` read from text; binary floats never touch money."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal(0)
MONEY_TEXT = re.compile(r"^-?\d+\.\d{2}$")


def r2(x: Decimal, half_up: bool = False) -> Decimal:
    """Clause 17 (p.6): each step to the cent, a half cent to the even cent."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP if half_up else ROUND_HALF_EVEN)


def money(text: str) -> Decimal:
    """Parse a CSV money field; it must carry exactly two decimals."""
    if not MONEY_TEXT.match(text):
        raise ValueError(f"not a two-decimal amount: {text!r}")
    return Decimal(text)


def to_cents(x: Decimal) -> int:
    cents = x * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"{x} is not a whole number of cents")
    return int(cents)
