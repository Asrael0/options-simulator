"""Punto d'ingresso unificato: sceglie Black-Scholes o l'albero binomiale.

--- COSA FA QUESTO FILE ---
Fa da centralino. Chi vuole prezzare un'opzione non deve sapere se serve la
formula chiusa o l'albero: chiama `price_option` e ci pensa questo file a
smistare in base allo stile di esercizio.

Contiene anche la CACHE (per non ricalcolare due volte la stessa cosa) e
l'aggregazione delle greche su tutte le gambe di una posizione.
"""

from __future__ import annotations

from functools import lru_cache

from .binomial import binomial_price, binomial_price_and_greeks
from .black_scholes import black_scholes
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
    """Svuota la cache. Serve ai test e al monitoraggio della memoria."""
    _cached_binomial_price.cache_clear()


def price_cache_info() -> dict[str, int]:
    """Statistiche della cache: hit, miss, dimensione, capacità."""
    info = _cached_binomial_price.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize or 0,
    }


def price_option(
    spec: OptionSpec, exercise: ExerciseStyle, resolution: Resolution = "full"
) -> float:
    """Prezzo di una singola opzione. Nessuna greca calcolata."""
    if exercise == "european":
        return black_scholes(spec).price
    return _cached_binomial_price(spec, exercise, STEPS_BY_RESOLUTION[resolution])


def price_and_greeks(
    spec: OptionSpec, exercise: ExerciseStyle, resolution: Resolution = "full"
) -> PricedOption:
    """Prezzo e greche di una singola opzione."""
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
) -> Greeks:
    """Greche di una singola gamba, senza segno né quantità."""
    leg = resolved.leg
    if isinstance(leg, OptionLeg):
        return price_and_greeks(spec_for_leg(leg, market), exercise, resolution).greeks()
    return STOCK_GREEKS


def position_greeks(
    legs: list[ResolvedLeg],
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
) -> Greeks:
    """Somma delle greche di tutte le gambe, con segno e quantità applicati."""
    delta = gamma = theta = vega = rho = 0.0

    for resolved in legs:
        g = leg_greeks(resolved, market, exercise, resolution)
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
