"""Black-Scholes-Merton per opzioni EUROPEE: prezzo e greche in forma chiusa.

Il dividend yield ``q`` è presente fin dall'inizio con default 0. Con q = 0
tutte le formule si riducono esattamente a Black-Scholes puro, quindi non
servirà riscrivere il motore quando i dividendi entreranno nell'interfaccia.
"""

from __future__ import annotations

import math

from .normal import norm_cdf, norm_pdf
from .types import DAYS_PER_YEAR, OptionSpec, PricedOption, years_from_days


def _deterministic_limit(spec: OptionSpec) -> PricedOption:
    """Caso senza incertezza residua: T = 0, oppure IV = 0, oppure spot nullo.

    Il sottostante vale con certezza il suo forward, quindi l'opzione vale il
    payoff sul forward, scontato.

    Il prototipo restituiva qui il valore intrinseco sullo SPOT. Coincide con
    questo risultato per T = 0, ma per IV -> 0 con T > 0 il valore corretto è
    quello sul forward: è il limite matematico di Black-Scholes per sigma -> 0.
    """
    t = years_from_days(spec.days_to_expiry)
    discount = math.exp(-spec.risk_free_rate * t)
    carry = math.exp(-spec.dividend_yield * t)
    forward = spec.spot * math.exp((spec.risk_free_rate - spec.dividend_yield) * t)
    is_call = spec.right == "call"

    if is_call:
        in_the_money = forward > spec.strike
        payoff = max(forward - spec.strike, 0.0)
        delta = carry if in_the_money else 0.0
    else:
        in_the_money = forward < spec.strike
        payoff = max(spec.strike - forward, 0.0)
        delta = -carry if in_the_money else 0.0

    return PricedOption(
        price=discount * payoff,
        delta=delta,
        gamma=0.0,
        theta_per_day=0.0,
        vega_per_point=0.0,
        rho_per_point=0.0,
    )


def black_scholes(spec: OptionSpec) -> PricedOption:
    """Prezzo e greche analitiche di un'opzione europea."""
    s = spec.spot
    k = spec.strike
    r = spec.risk_free_rate
    sigma = spec.iv
    q = spec.dividend_yield
    t = years_from_days(spec.days_to_expiry)

    if t <= 0.0 or sigma <= 0.0 or s <= 0.0 or k <= 0.0:
        return _deterministic_limit(spec)

    sqrt_t = math.sqrt(t)
    vol_t = sigma * sqrt_t
    discount = math.exp(-r * t)
    carry = math.exp(-q * t)

    d1 = (math.log(s / k) + (r - q + sigma * sigma / 2.0) * t) / vol_t
    d2 = d1 - vol_t
    pdf1 = float(norm_pdf(d1))

    # Identiche fra call e put: non dipendono dal segno del payoff.
    gamma = carry * pdf1 / (s * vol_t)
    vega_per_point = s * carry * pdf1 * sqrt_t / 100.0

    # Termine di decadimento della volatilità, comune a call e put.
    vol_decay = -(s * carry * pdf1 * sigma) / (2.0 * sqrt_t)

    if spec.right == "call":
        nd1 = float(norm_cdf(d1))
        nd2 = float(norm_cdf(d2))
        theta_per_year = vol_decay - r * k * discount * nd2 + q * s * carry * nd1
        return PricedOption(
            price=s * carry * nd1 - k * discount * nd2,
            delta=carry * nd1,
            gamma=gamma,
            theta_per_day=theta_per_year / DAYS_PER_YEAR,
            vega_per_point=vega_per_point,
            rho_per_point=k * t * discount * nd2 / 100.0,
        )

    n_minus_d1 = float(norm_cdf(-d1))
    n_minus_d2 = float(norm_cdf(-d2))
    theta_per_year = vol_decay + r * k * discount * n_minus_d2 - q * s * carry * n_minus_d1
    return PricedOption(
        price=k * discount * n_minus_d2 - s * carry * n_minus_d1,
        delta=-carry * n_minus_d1,
        gamma=gamma,
        theta_per_day=theta_per_year / DAYS_PER_YEAR,
        vega_per_point=vega_per_point,
        rho_per_point=-(k * t * discount * n_minus_d2) / 100.0,
    )


def black_scholes_price(spec: OptionSpec) -> float:
    """Prezzo soltanto. Evita di costruire l'oggetto greche dove non serve."""
    return black_scholes(spec).price


def probability_itm(spec: OptionSpec) -> float:
    """Probabilità risk-neutral che l'opzione scada in-the-money.

    È ``N(d2)`` per una call e ``N(-d2)`` per una put.

    NON è una previsione: è la probabilità sotto la misura risk-neutral, che
    incorpora il prezzo del rischio e non la vera distribuzione attesa dei
    rendimenti.
    """
    s = spec.spot
    k = spec.strike
    r = spec.risk_free_rate
    sigma = spec.iv
    q = spec.dividend_yield
    t = years_from_days(spec.days_to_expiry)

    if t <= 0.0 or sigma <= 0.0 or s <= 0.0 or k <= 0.0:
        forward = s * math.exp((r - q) * t)
        itm = forward > k if spec.right == "call" else forward < k
        return 1.0 if itm else 0.0

    vol_t = sigma * math.sqrt(t)
    d2 = (math.log(s / k) + (r - q - sigma * sigma / 2.0) * t) / vol_t
    return float(norm_cdf(d2)) if spec.right == "call" else float(norm_cdf(-d2))
