"""Volatilità implicita: dal prezzo alla IV.

--- COSA FA QUESTO FILE ---
Fa il percorso inverso del pricing. Il modello, data una volatilità, dà un
prezzo; qui, dato un prezzo osservato sul mercato, si cerca la volatilità che
lo riproduce. È così che nasce la "volatilità implicita".

METODO — bisezione. Il prezzo di un'opzione cresce sempre con la volatilità
(la vega è positiva), quindi esiste al più una IV che dà quel prezzo, e la si
trova dimezzando l'intervallo [0,1%, 500%] finché è abbastanza stretto. È più
lento di Newton-Raphson ma non diverge mai, e funziona identico per il modello
europeo e per l'albero americano, che non ha una vega in forma chiusa.
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
    """IV che fa valere ``price`` all'opzione ``spec`` (la cui ``iv`` è ignorata).

    Restituisce ``None`` se il prezzo è fuori da ciò che il modello può
    produrre: sotto il valore con volatilità quasi nulla (succede con prezzi
    vecchi o con tasso e dividendo sbagliati) o sopra quello con IV del 500%.
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
