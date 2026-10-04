"""Merton jump-diffusion: European prices with sudden price jumps, and calibration.

Black-Scholes assumes the price moves continuously. Merton (1976) adds JUMPS: at
random moments (a Poisson process with ``intensity`` jumps per year) the price is
multiplied by a lognormal factor whose log has mean ``mean`` and standard
deviation ``vol``. Negative mean jumps are crashes; they are what makes deep
out-of-the-money puts more expensive than Black-Scholes says — the volatility
smile, or skew.

THE CLOSED FORM. Given that exactly n jumps happen before expiry, the price is
still lognormal, so the option is worth a Black-Scholes price with an adjusted
volatility and rate. The Merton price is the Poisson-weighted sum::

    price = Σ_n  e^(−λ'T) (λ'T)^n / n!  ·  BS(S, K, T, r_n, σ_n)

    k    = e^(mean + vol²/2) − 1       expected relative jump size
    λ'   = λ (1 + k)
    σ_n² = σ² + n·vol² / T
    r_n  = r − λk + n·ln(1 + k) / T

With ``intensity = 0`` only the n = 0 term is left and the formula is exactly
Black-Scholes: Merton extends the model rather than replacing it.

CALIBRATION. The jump parameters cannot be observed: they are inferred from the
option prices of one expiry by minimising the pricing error, measured in
implied-volatility points. The optimiser is a small Nelder-Mead (no SciPy
dependency) started from a few points, and the whole chain is priced at once
with NumPy.

SCOPE. The formula is for European options. On American stock options it is used
only with out-of-the-money quotes, where early exercise is worth little.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from .black_scholes import black_scholes
from .normal import norm_cdf, norm_pdf
from .types import OptionSpec, PricedOption, Right, years_from_days

FloatArray = NDArray[np.float64]

MAX_TERMS = 200

# Calibration bounds: wide enough for any listed chain, narrow enough to keep
# the optimiser away from meaningless corners.
SIGMA_BOUNDS = (0.01, 2.0)
INTENSITY_BOUNDS = (0.0, 20.0)
MEAN_BOUNDS = (-1.0, 0.5)
JUMP_VOL_BOUNDS = (0.005, 1.0)


@dataclass(frozen=True, slots=True)
class JumpParams:
    """The jump part of the model."""

    intensity: float  # λ: expected number of jumps per year
    mean: float  # mean of the log jump size (negative = crashes)
    vol: float  # standard deviation of the log jump size

    @property
    def expected_jump(self) -> float:
        """Expected relative jump size k = E[J] − 1 (e.g. −0.08 = an 8% drop)."""
        return math.exp(self.mean + 0.5 * self.vol * self.vol) - 1.0


NO_JUMPS = JumpParams(intensity=0.0, mean=0.0, vol=0.0)
# A typical S&P 500 calibration: about one 10% crash every three years.
TYPICAL_CRASHES = JumpParams(intensity=0.3, mean=-0.11, vol=0.10)


def _terms(x: float) -> int:
    """Number of Poisson terms to keep for an expected count of ``x`` jumps."""
    return min(MAX_TERMS, int(x + 10.0 * math.sqrt(x) + 12.0))


def merton_prices(
    spot: float,
    strikes: FloatArray,
    is_call: NDArray[np.bool_],
    days_to_expiry: float,
    rate: float,
    dividend: float,
    sigma: float,
    jumps: JumpParams,
) -> FloatArray:
    """Merton prices for a whole set of strikes at once (vectorised).

    Rows are Poisson terms, columns are strikes: one NumPy pass prices the whole
    chain, which is what makes calibration fast.
    """
    t = years_from_days(days_to_expiry)
    k_arr = np.asarray(strikes, dtype=np.float64)
    calls = np.asarray(is_call, dtype=bool)
    if t <= 0.0:
        intrinsic = np.where(calls, spot - k_arr, k_arr - spot)
        return np.maximum(intrinsic, 0.0)

    k = jumps.expected_jump if jumps.intensity > 0.0 else 0.0
    lam_prime = jumps.intensity * (1.0 + k)
    x = lam_prime * t
    count = _terms(x) if jumps.intensity > 0.0 else 1
    n = np.arange(count, dtype=np.float64)
    if x > 0.0:
        log_weights = -x + n * math.log(x) - np.array([math.lgamma(i + 1.0) for i in n])
        weights = np.exp(log_weights)
    else:
        weights = np.zeros(count)
        weights[0] = 1.0

    variance = sigma * sigma + n * jumps.vol * jumps.vol / t
    vol_t = np.sqrt(np.maximum(variance * t, 1e-24))[:, None]
    log_growth = math.log1p(k)
    r_n = (rate - jumps.intensity * k + n * log_growth / t)[:, None]

    forward = spot * np.exp((r_n - dividend) * t)
    d1 = (np.log(forward / k_arr[None, :]) + 0.5 * vol_t * vol_t) / vol_t
    d2 = d1 - vol_t
    discount = np.exp(-r_n * t)
    call = discount * (forward * norm_cdf(d1) - k_arr[None, :] * norm_cdf(d2))
    put = discount * (k_arr[None, :] * norm_cdf(-d2) - forward * norm_cdf(-d1))
    terms = np.where(calls[None, :], call, put)
    return np.asarray(weights @ terms, dtype=np.float64)


def merton_price(spec: OptionSpec, jumps: JumpParams) -> float:
    """Merton price of a single European option; ``spec.iv`` is the diffusion volatility."""
    if jumps.intensity <= 0.0:
        return black_scholes(spec).price
    prices = merton_prices(
        spec.spot,
        np.array([spec.strike]),
        np.array([spec.right == "call"]),
        spec.days_to_expiry,
        spec.risk_free_rate,
        spec.dividend_yield,
        spec.iv,
        jumps,
    )
    return float(prices[0])


def merton_price_and_greeks(spec: OptionSpec, jumps: JumpParams) -> PricedOption:
    """Price and Greeks under Merton, by central differences on the closed form.

    The closed form is smooth, so small bumps give accurate Greeks: unlike the
    binomial tree there is no sawtooth to amplify.
    """
    if jumps.intensity <= 0.0:
        return black_scholes(spec)
    price = merton_price(spec, jumps)
    h = spec.spot * 1e-3
    up = merton_price(replace(spec, spot=spec.spot + h), jumps)
    down = merton_price(replace(spec, spot=spec.spot - h), jumps)
    if spec.days_to_expiry > 1.0:
        tomorrow = merton_price(replace(spec, days_to_expiry=spec.days_to_expiry - 1.0), jumps)
        theta = tomorrow - price
    else:
        theta = 0.0
    vol_up = merton_price(replace(spec, iv=spec.iv + 0.01), jumps)
    vol_down = merton_price(replace(spec, iv=max(spec.iv - 0.01, 1e-4)), jumps)
    rate_up = merton_price(replace(spec, risk_free_rate=spec.risk_free_rate + 0.01), jumps)
    rate_down = merton_price(replace(spec, risk_free_rate=spec.risk_free_rate - 0.01), jumps)
    return PricedOption(
        price=price,
        delta=(up - down) / (2.0 * h),
        gamma=(up - 2.0 * price + down) / (h * h),
        theta_per_day=theta,
        vega_per_point=(vol_up - vol_down) / 2.0,
        rho_per_point=(rate_up - rate_down) / 2.0,
    )


def merton_probability_below(
    price: float,
    spot: float,
    days_to_expiry: float,
    rate: float,
    dividend: float,
    sigma: float,
    jumps: JumpParams,
) -> float:
    """Risk-neutral P(S_T < price) under Merton: a Poisson mixture of lognormals.

    Given n jumps, ln S_T is normal with mean ln S + (r − q − λk − σ²/2)T + n·mean
    and variance σ²T + n·vol².
    """
    if price <= 0.0:
        return 0.0
    if math.isinf(price):
        return 1.0
    t = years_from_days(days_to_expiry)
    if t <= 0.0:
        return 1.0 if spot < price else 0.0
    k = jumps.expected_jump if jumps.intensity > 0.0 else 0.0
    x = jumps.intensity * t
    count = _terms(x) if jumps.intensity > 0.0 else 1
    total = 0.0
    for n in range(count):
        weight = math.exp(-x + n * math.log(x) - math.lgamma(n + 1.0)) if x > 0.0 else 1.0
        mean = (
            math.log(spot)
            + (rate - dividend - jumps.intensity * k - 0.5 * sigma * sigma) * t
            + n * jumps.mean
        )
        std = math.sqrt(max(sigma * sigma * t + n * jumps.vol * jumps.vol, 1e-24))
        total += weight * float(norm_cdf((math.log(price) - mean) / std))
    return min(max(total, 0.0), 1.0)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FitQuote:
    """One market quote used for calibration."""

    strike: float
    right: Right
    price: float
    iv: float  # the quote's Black-Scholes implied volatility


@dataclass(frozen=True, slots=True)
class MertonFit:
    """Result of a calibration on one expiry."""

    sigma: float  # diffusion volatility, i.e. volatility without jumps
    jumps: JumpParams
    rmse: float  # Merton error, in implied-volatility points
    bsm_iv: float  # the best single volatility (what Black-Scholes can do)
    bsm_rmse: float  # Black-Scholes error, in implied-volatility points
    strikes: list[float]
    market_iv: list[float]
    model_iv: list[float]  # Merton prices expressed as Black-Scholes IVs


def _clip(value: float, bounds: tuple[float, float]) -> float:
    return min(max(value, bounds[0]), bounds[1])


def _unpack(x: FloatArray) -> tuple[float, JumpParams]:
    sigma = _clip(math.exp(x[0]), SIGMA_BOUNDS)
    intensity = _clip(math.exp(x[1]), INTENSITY_BOUNDS)
    mean = _clip(float(x[2]), MEAN_BOUNDS)
    vol = _clip(math.exp(x[3]), JUMP_VOL_BOUNDS)
    return sigma, JumpParams(intensity=intensity, mean=mean, vol=vol)


def _nelder_mead(
    f: Callable[[FloatArray], float],
    x0: FloatArray,
    step: FloatArray,
    iterations: int = 600,
    tolerance: float = 1e-10,
) -> tuple[FloatArray, float]:
    """Plain Nelder-Mead minimisation: no derivatives, robust on small problems."""
    dim = len(x0)
    simplex = [x0] + [x0 + np.eye(dim)[i] * step[i] for i in range(dim)]
    values = [f(p) for p in simplex]
    for _ in range(iterations):
        order = np.argsort(values)
        simplex = [simplex[i] for i in order]
        values = [values[i] for i in order]
        if abs(values[-1] - values[0]) < tolerance:
            break
        centroid = np.mean(simplex[:-1], axis=0)
        worst = simplex[-1]
        reflected = centroid + (centroid - worst)
        f_reflected = f(reflected)
        if f_reflected < values[0]:
            expanded = centroid + 2.0 * (centroid - worst)
            f_expanded = f(expanded)
            if f_expanded < f_reflected:
                simplex[-1], values[-1] = expanded, f_expanded
            else:
                simplex[-1], values[-1] = reflected, f_reflected
        elif f_reflected < values[-2]:
            simplex[-1], values[-1] = reflected, f_reflected
        else:
            contracted = centroid + 0.5 * (worst - centroid)
            f_contracted = f(contracted)
            if f_contracted < values[-1]:
                simplex[-1], values[-1] = contracted, f_contracted
            else:
                best = simplex[0]
                simplex = [best + 0.5 * (p - best) for p in simplex]
                values = [values[0]] + [f(p) for p in simplex[1:]]
    best_index = int(np.argmin(values))
    return simplex[best_index], values[best_index]


def calibrate_merton(
    spot: float,
    days_to_expiry: float,
    rate: float,
    dividend: float,
    quotes: Sequence[FitQuote],
) -> MertonFit | None:
    """Find the volatility and jump parameters that best match ``quotes``.

    The error of each quote is its price error divided by its Black-Scholes vega,
    which is (to first order) the error in implied-volatility points: cheap to
    compute and comparable across strikes. Return ``None`` with too few quotes.
    """
    if len(quotes) < 5 or days_to_expiry <= 0:
        return None
    from .implied import implied_volatility  # local: implied -> greeks -> merton

    t = years_from_days(days_to_expiry)
    strikes = np.array([q.strike for q in quotes], dtype=np.float64)
    is_call = np.array([q.right == "call" for q in quotes])
    prices = np.array([q.price for q in quotes], dtype=np.float64)
    ivs = np.array([q.iv for q in quotes], dtype=np.float64)

    forward = spot * math.exp((rate - dividend) * t)
    vol_t = ivs * math.sqrt(t)
    d1 = (np.log(forward / strikes) + 0.5 * vol_t * vol_t) / vol_t
    vega = spot * math.exp(-dividend * t) * norm_pdf(d1) * math.sqrt(t)
    vega = np.maximum(vega, 1e-4 * spot * math.sqrt(t))

    def objective(x: FloatArray) -> float:
        sigma, jumps = _unpack(x)
        model = merton_prices(spot, strikes, is_call, days_to_expiry, rate, dividend, sigma, jumps)
        error = (model - prices) / vega
        return float(np.mean(error * error))

    base = float(np.min(ivs))
    starts = [
        (base * 0.9, 0.3, -0.15, 0.10),
        (base * 0.9, 1.5, -0.05, 0.05),
        (base * 0.7, 0.5, -0.25, 0.20),
        (base * 0.95, 3.0, -0.02, 0.03),
    ]
    step = np.array([0.2, 0.7, 0.05, 0.4])
    best_x, best_value = None, math.inf
    for sigma0, lam0, mean0, vol0 in starts:
        x0 = np.array([math.log(max(sigma0, 0.02)), math.log(lam0), mean0, math.log(vol0)])
        x, value = _nelder_mead(objective, x0, step)
        if value < best_value:
            best_x, best_value = x, value
    assert best_x is not None
    best_x, best_value = _nelder_mead(objective, best_x, step * 0.25)
    sigma, jumps = _unpack(best_x)

    model_prices = merton_prices(
        spot, strikes, is_call, days_to_expiry, rate, dividend, sigma, jumps
    )
    model_iv: list[float] = []
    market_iv: list[float] = []
    kept: list[float] = []
    for quote, price in zip(quotes, model_prices, strict=True):
        spec = OptionSpec(
            spot=spot,
            strike=quote.strike,
            days_to_expiry=days_to_expiry,
            risk_free_rate=rate,
            iv=0.2,
            right=quote.right,
            dividend_yield=dividend,
        )
        iv = implied_volatility(float(price), spec, "european", "full")
        if iv is not None:
            kept.append(quote.strike)
            model_iv.append(iv)
            market_iv.append(quote.iv)

    market = np.array(market_iv) if market_iv else ivs
    bsm_iv = float(np.mean(ivs))
    bsm_rmse = float(np.sqrt(np.mean((ivs - bsm_iv) ** 2))) * 100
    rmse = (
        float(np.sqrt(np.mean((np.array(model_iv) - market) ** 2))) * 100
        if model_iv
        else math.sqrt(best_value) * 100
    )
    return MertonFit(
        sigma=sigma,
        jumps=jumps,
        rmse=rmse,
        bsm_iv=bsm_iv,
        bsm_rmse=bsm_rmse,
        strikes=kept,
        market_iv=market_iv,
        model_iv=model_iv,
    )
