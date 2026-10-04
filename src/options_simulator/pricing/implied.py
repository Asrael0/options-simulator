"""Implied volatility: from price to IV.

The reverse of pricing. Given a volatility, the model gives a price; here, given
a price observed in the market, we look for the volatility that reproduces it.
That is where "implied volatility" comes from.

METHOD — bisection. An option's price always increases with volatility (vega is
positive), so at most one IV gives that price, and it is found by halving the
interval [0.1%, 500%] until it is narrow enough. Slower than Newton-Raphson but
it never diverges, and it works the same for the European model and for the
American tree, which has no closed-form vega.
"""

from __future__ import annotations

from dataclasses import replace

from .greeks import price_option
from .types import ExerciseStyle, OptionSpec, Resolution

IV_LOW = 0.001
IV_HIGH = 5.0
TOLERANCE = 1e-5
MAX_ITERATIONS = 60


def implied_volatility(
    price: float,
    spec: OptionSpec,
    exercise: ExerciseStyle,
    resolution: Resolution = "curve",
) -> float | None:
    """IV that makes option ``spec`` worth ``price`` (``spec.iv`` is ignored).

    Return ``None`` if the price is outside what the model can produce: below
    the value at near-zero volatility (it happens with stale prices or a wrong
    rate and dividend) or above the value at 500% IV.
    """
    if price <= 0.0:
        return None

    def value(iv: float) -> float:
        return price_option(replace(spec, iv=iv), exercise, resolution)

    low, high = IV_LOW, IV_HIGH
    if not value(low) <= price <= value(high):
        return None
    for _ in range(MAX_ITERATIONS):
        mid = (low + high) / 2
        if value(mid) < price:
            low = mid
        else:
            high = mid
        if high - low < TOLERANCE:
            break
    return (low + high) / 2
