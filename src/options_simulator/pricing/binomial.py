"""Albero binomiale Cox-Ross-Rubinstein: prezza europee e americane.

--- COSA FA QUESTO FILE ---
L'idea: invece di una formula, si SIMULA. Si divide il tempo fino alla scadenza
in N passi. A ogni passo il prezzo può solo salire di un fattore `u` o scendere
di un fattore `d`. Si ottiene un albero di prezzi possibili.

Poi si va AL CONTRARIO: si parte dalla scadenza, dove il valore dell'opzione è
noto (è il payoff), e si torna indietro passo per passo calcolando quanto vale
ogni nodo. Al nodo di partenza c'è il prezzo di oggi.

Per le AMERICANE, a ogni nodo si confronta "tenere l'opzione" con "esercitarla
adesso" e si prende il massimo. È così che il valore dell'esercizio anticipato
*emerge* dal calcolo, invece di doverlo aggiungere a mano.

PERCHÉ NUMPY NON È UN OPZIONALE QUI.

Un albero a N passi ha O(N²) nodi. Con N = 140 sono circa diecimila
valutazioni: in JavaScript un doppio ciclo le esegue in frazioni di
millisecondo, in Python puro sarebbe cento volte più lento e l'interfaccia
diventerebbe inusabile. La soluzione non è "scrivere Python più veloce" ma
cambiare la forma del calcolo: un intero LIVELLO dell'albero è un array, e
l'induzione all'indietro diventa UNA operazione vettoriale per livello. Si
passa da O(N²) iterazioni interpretate a O(N) chiamate NumPy, ognuna eseguita
in C.

La riga che fa tutto il lavoro è::

    val = discount * (p_up * val[:-1] + p_down * val[1:])

``val[:-1]`` sono i figli "su", ``val[1:]`` i figli "giù". Uno slittamento di
un indice esprime l'intera struttura ad albero.

ALTRE OTTIMIZZAZIONI, ereditate dalla versione TypeScript.

1. Zero potenze nei cicli. Una tabella ``u^k`` per k in [-steps, steps] viene
   costruita una volta sola; il prezzo di ogni nodo è una lettura indicizzata.
2. Delta, gamma e theta si LEGGONO dall'albero (livelli 1 e 2, metodo standard
   di Hull) invece di ricostruire alberi bumpati. Sono gratis e, soprattutto,
   sono lisci: le differenze finite dividono per h², amplificando di 1e4 il
   sawtooth di convergenza del CRR. Restano bumpati solo vega e rho, che
   dividono per 2*0.01 e quindi non soffrono del problema.

NOTA sulla convergenza: il CRR puro converge a Black-Scholes in modo
oscillante, O(1/n). Esistono tecniche di smoothing (Broadie-Detemple) che la
rendono più regolare, ma cambierebbero i valori attesi del test di
convergenza. Non sono attive.
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
    """Risultato interno dell'albero."""

    price: float
    delta: float
    gamma: float
    theta_per_day: float


def _run_tree(spec: OptionSpec, exercise: ExerciseStyle, requested_steps: int) -> _TreeResult:
    """Costruisce l'albero e restituisce prezzo, delta, gamma e theta.

    Delta e gamma sono letti ai livelli 1 e 2, quindi valgono tecnicamente a
    t = dt e t = 2*dt anziché a t = 0. Con 140 passi su 30 giorni lo
    sfasamento è di circa 0.4 giorni: produce un bias sotto l'1%, e in cambio
    le curve sono lisce, che su uno slider conta di più.
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
        """Prezzi del sottostante a un livello, dal nodo più alto al più basso.

        Gli esponenti sono ``level, level-2, ..., -level``: uno slicing con
        passo -2 li estrae come vista, senza allocare.
        """
        return s0 * pow_u[steps + level :: -2][: level + 1]

    def intrinsic(prices: np.ndarray) -> np.ndarray:
        """Valore d'esercizio immediato per un intero livello."""
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
    """Prezzo di un'opzione con l'albero binomiale."""
    return _run_tree(spec, exercise, steps).price


def binomial_price_and_greeks(
    spec: OptionSpec, exercise: ExerciseStyle, steps: int
) -> PricedOption:
    """Prezzo e greche complete. Vega e rho richiedono alberi aggiuntivi."""
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
