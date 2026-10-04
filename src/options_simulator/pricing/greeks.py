"""Single entry point: picks Black-Scholes or the binomial tree.

It acts as a dispatcher. Callers pricing an option do not need to know whether
the closed formula or the tree is required: they call ``price_option`` and this
module routes by exercise style.

It also holds the CACHE (so the same thing is never computed twice) and the
aggregation of Greeks across all the legs of a position.
"""

from __future__ import annotations

from functools import lru_cache

from .binomial import binomial_price, binomial_price_and_greeks
from .black_scholes import black_scholes
from .merton import JumpParams, merton_price, merton_price_and_greeks
from .types import (
    STEPS_BY_RESOLUTION,
    ExerciseStyle,
    Greeks,
    MarketParams,
    OptionLeg,
    OptionSpec,
    PricedOption,
    Resolution,
    ResolvedLeg,
    spec_for_leg,
)

_CACHE_SIZE = 50_000


@lru_cache(maxsize=_CACHE_SIZE)
def _cached_binomial_price(spec: OptionSpec, exercise: ExerciseStyle, steps: int) -> float:
    return binomial_price(spec, exercise, steps)


def clear_price_cache() -> None:
    """Empty the cache. Used by tests and memory monitoring."""
    _cached_binomial_price.cache_clear()


def price_cache_info() -> dict[str, int]:
    """Cache statistics: hits, misses, size, capacity."""
    info = _cached_binomial_price.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize or 0,
    }


def price_option(
    spec: OptionSpec,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
    jumps: JumpParams | None = None,
) -> float:
    """Price of a single option. No Greeks computed.

    With ``jumps`` (European options only) the Merton jump-diffusion is used.
    """
    if jumps is not None and jumps.intensity > 0.0 and exercise == "european":
        return merton_price(spec, jumps)
    if exercise == "european":
        return black_scholes(spec).price
    return _cached_binomial_price(spec, exercise, STEPS_BY_RESOLUTION[resolution])


def price_and_greeks(
    spec: OptionSpec,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
    jumps: JumpParams | None = None,
) -> PricedOption:
    """Price and Greeks of a single option."""
    if jumps is not None and jumps.intensity > 0.0 and exercise == "european":
        return merton_price_and_greeks(spec, jumps)
    if exercise == "european":
        return black_scholes(spec)
    return binomial_price_and_greeks(spec, exercise, STEPS_BY_RESOLUTION[resolution])


STOCK_GREEKS = Greeks(
    delta=1.0, gamma=0.0, theta_per_day=0.0, vega_per_point=0.0, rho_per_point=0.0
)


def leg_greeks(
    resolved: ResolvedLeg,
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
    jumps: JumpParams | None = None,
) -> Greeks:
    """Greeks of a single leg, without sign or quantity."""
    leg = resolved.leg
    if isinstance(leg, OptionLeg):
        return price_and_greeks(spec_for_leg(leg, market), exercise, resolution, jumps).greeks()
    return STOCK_GREEKS


def position_greeks(
    legs: list[ResolvedLeg],
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
    jumps: JumpParams | None = None,
) -> Greeks:
    """Sum of the Greeks of all legs, with sign and quantity applied."""
    delta = gamma = theta = vega = rho = 0.0

    for resolved in legs:
        g = leg_greeks(resolved, market, exercise, resolution, jumps)
        n = resolved.signed_qty
        delta += g.delta * n
        gamma += g.gamma * n
        theta += g.theta_per_day * n
        vega += g.vega_per_point * n
        rho += g.rho_per_point * n

    return Greeks(
        delta=delta,
        gamma=gamma,
        theta_per_day=theta,
        vega_per_point=vega,
        rho_per_point=rho,
    )
