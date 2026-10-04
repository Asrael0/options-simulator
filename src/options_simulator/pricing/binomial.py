"""Cox-Ross-Rubinstein binomial tree: prices European and American options.

The idea: instead of a formula, SIMULATE. Split the time to expiry into N steps.
At each step the price can only go up by a factor ``u`` or down by a factor
``d``. The result is a tree of possible prices.

Then go BACKWARDS: start at expiry, where the option value is known (it is the
payoff), and walk back step by step working out what each node is worth. The
root node holds today's price.

For AMERICAN options every node compares "keep the option" with "exercise it
now" and takes the larger. That is how the value of early exercise *emerges*
from the calculation instead of being added by hand.

WHY NUMPY IS NOT OPTIONAL HERE.

A tree with N steps has O(N²) nodes. With N = 140 that is about ten thousand
evaluations: a double loop in JavaScript runs them in a fraction of a
millisecond, in pure Python it would be a hundred times slower and the
interface would become unusable. The fix is not "writing faster Python" but
changing the shape of the calculation: a whole LEVEL of the tree is an array,
and backward induction becomes ONE vector operation per level. That goes from
O(N²) interpreted iterations to O(N) NumPy calls, each one executed in C.

The line doing all the work is::

    val = discount * (p_up * val[:-1] + p_down * val[1:])

``val[:-1]`` are the "up" children, ``val[1:]`` the "down" children. A one-index
shift expresses the whole tree structure.

OTHER OPTIMISATIONS, inherited from the TypeScript version.

1. No powers inside the loops. A ``u^k`` table for k in [-steps, steps] is built
   once; each node price is an indexed read.
2. Delta, gamma and theta are READ from the tree (levels 1 and 2, Hull's
   standard method) instead of rebuilding bumped trees. They come for free and,
   above all, they are smooth: finite differences divide by h², amplifying the
   CRR convergence sawtooth by 1e4. Only vega and rho are still bumped; they
   divide by 2*0.01 and do not suffer from the problem.

NOTE on convergence: plain CRR converges to Black-Scholes in an oscillating
way, O(1/n). Smoothing techniques exist (Broadie-Detemple) that make it more
regular, but they would change the expected values of the convergence test.
They are not enabled.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .black_scholes import _deterministic_limit
from .types import (
    DAYS_PER_YEAR,
    ExerciseStyle,
    OptionSpec,
    PricedOption,
    years_from_days,
)

MIN_STEPS = 2

_VOL_BUMP = 0.01
_RATE_BUMP = 0.01


@dataclass(frozen=True, slots=True)
class _TreeResult:
    """Internal result of the tree."""

    price: float
    delta: float
    gamma: float
    theta_per_day: float


def _run_tree(spec: OptionSpec, exercise: ExerciseStyle, requested_steps: int) -> _TreeResult:
    """Build the tree and return price, delta, gamma and theta.

    Delta and gamma are read at levels 1 and 2, so technically they hold at
    t = dt and t = 2*dt rather than t = 0. With 140 steps over 30 days the shift
    is about 0.4 days: it causes a bias below 1%, and in exchange the curves are
    smooth, which matters more on a slider.
    """
    s0 = spec.spot
    k = spec.strike
    r = spec.risk_free_rate
    sigma = spec.iv
    q = spec.dividend_yield
    t = years_from_days(spec.days_to_expiry)

    if t <= 0.0 or sigma <= 0.0 or s0 <= 0.0 or k <= 0.0:
        limit = _deterministic_limit(spec)
        return _TreeResult(limit.price, limit.delta, limit.gamma, limit.theta_per_day)

    steps = max(MIN_STEPS, int(requested_steps))
    dt = t / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    drift = math.exp((r - q) * dt)
    p_up = (drift - d) / (u - d)

    if not 0.0 < p_up < 1.0:
        limit = _deterministic_limit(spec)
        return _TreeResult(limit.price, limit.delta, limit.gamma, limit.theta_per_day)

    p_down = 1.0 - p_up
    discount = math.exp(-r * dt)
    is_call = spec.right == "call"
    is_american = exercise == "american"

    pow_u = u ** np.arange(-steps, steps + 1, dtype=np.int64)

    def level_prices(level: int) -> np.ndarray:
        """Underlying prices at a level, from the highest node to the lowest.

        The exponents are ``level, level-2, ..., -level``: a slice with step -2
        extracts them as a view, without allocating.
        """
        return s0 * pow_u[steps + level :: -2][: level + 1]

    def intrinsic(prices: np.ndarray) -> np.ndarray:
        """Immediate exercise value for a whole level."""
        return np.maximum(prices - k, 0.0) if is_call else np.maximum(k - prices, 0.0)

    val = intrinsic(level_prices(steps))

    v20 = v21 = v22 = 0.0
    v10 = v11 = 0.0

    for level in range(steps - 1, -1, -1):
        val = discount * (p_up * val[:-1] + p_down * val[1:])
        if is_american:
            np.maximum(val, intrinsic(level_prices(level)), out=val)
        if level == 2:
            v20, v21, v22 = float(val[0]), float(val[1]), float(val[2])
        elif level == 1:
            v10, v11 = float(val[0]), float(val[1])

    price = float(val[0])

    upper_gap = s0 * u * u - s0
    lower_gap = s0 - s0 * d * d
    gamma = ((v20 - v21) / upper_gap - (v21 - v22) / lower_gap) / ((upper_gap + lower_gap) / 2.0)

    return _TreeResult(
        price=price,
        delta=(v10 - v11) / (s0 * u - s0 * d),
        gamma=gamma,
        theta_per_day=(v21 - price) / (2.0 * dt) / DAYS_PER_YEAR,
    )


def binomial_price(spec: OptionSpec, exercise: ExerciseStyle, steps: int) -> float:
    """Option price with the binomial tree."""
    return _run_tree(spec, exercise, steps).price


def binomial_price_and_greeks(
    spec: OptionSpec, exercise: ExerciseStyle, steps: int
) -> PricedOption:
    """Price and full Greeks. Vega and rho need extra trees."""
    base = _run_tree(spec, exercise, steps)

    vol_up = binomial_price(replace(spec, iv=spec.iv + _VOL_BUMP), exercise, steps)
    if spec.iv > _VOL_BUMP:
        vol_down = binomial_price(replace(spec, iv=spec.iv - _VOL_BUMP), exercise, steps)
        vega_per_point = (vol_up - vol_down) / 2.0
    else:
        vega_per_point = vol_up - base.price

    rate_up = binomial_price(
        replace(spec, risk_free_rate=spec.risk_free_rate + _RATE_BUMP), exercise, steps
    )
    rate_down = binomial_price(
        replace(spec, risk_free_rate=spec.risk_free_rate - _RATE_BUMP), exercise, steps
    )

    return PricedOption(
        price=base.price,
        delta=base.delta,
        gamma=base.gamma,
        theta_per_day=base.theta_per_day,
        vega_per_point=vega_per_point,
        rho_per_point=(rate_up - rate_down) / 2.0,
    )
