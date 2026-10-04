"""Black-Scholes-Merton for EUROPEAN options: closed-form price and Greeks.

"Closed form" means a formula that gives the result in one direct calculation,
with no loops or successive approximations. Put in spot, strike, time, rate and
volatility, and the price comes out. It is the fastest part of the engine.

It applies only to EUROPEAN options, exercisable at expiry only: the formula
assumes no early exercise. American options need the binomial tree in
``binomial.py``.

The dividend yield ``q`` is supported throughout, defaulting to 0. With q = 0
every formula reduces exactly to plain Black-Scholes.
"""

from __future__ import annotations

import math

from .normal import norm_cdf, norm_pdf
from .types import DAYS_PER_YEAR, OptionSpec, PricedOption, years_from_days


def _deterministic_limit(spec: OptionSpec) -> PricedOption:
    """Case with no remaining uncertainty: T = 0, or IV = 0, or zero spot.

    The underlying is certain to be worth its forward, so the option is worth
    the discounted payoff on the forward.

    The original prototype returned the intrinsic value on SPOT here. That
    matches for T = 0, but for IV -> 0 with T > 0 the correct value is the one on
    the forward: it is the mathematical limit of Black-Scholes as sigma -> 0.
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
    """Price and analytical Greeks of a European option."""
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

    gamma = carry * pdf1 / (s * vol_t)
    vega_per_point = s * carry * pdf1 * sqrt_t / 100.0

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
    """Price only, for call sites that do not need the Greeks."""
    return black_scholes(spec).price


def probability_itm(spec: OptionSpec) -> float:
    """Risk-neutral probability that the option expires in the money.

    It is ``N(d2)`` for a call and ``N(-d2)`` for a put.

    It is NOT a forecast: it is the probability under the risk-neutral measure,
    which embeds the price of risk rather than the real expected distribution of
    returns.
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
