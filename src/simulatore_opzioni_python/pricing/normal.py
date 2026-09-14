"""Distribuzione normale standard.

--- COSA FA QUESTO FILE ---
Due funzioni matematiche, niente altro. La "normale standard" è la campana di
Gauss: `norm_pdf` restituisce l'altezza della campana in un punto, `norm_cdf`
l'area sotto la campana fino a quel punto (cioè la probabilità di ottenere un
valore minore). Black-Scholes le usa entrambe.

Si usa l'algoritmo di Hart (1968) nella formulazione divulgata da Graeme West,
accurato alla doppia precisione (~1e-15). Il prototipo originale usava
Abramowitz-Stegun 26.2.17, con errore assoluto ~7.5e-8: invisibile su un
prezzo a quattro decimali, ma moltiplicato per 500 unità di sottostante supera
il centesimo.

PROPRIETÀ INVARIANTE — la ragione per cui la put-call parity passa a 1e-15.
``norm_cdf`` calcola sempre la coda ``N(-|x|)`` e poi rispecchia::

    N(x) = 1 - coda   se x > 0
    N(x) = coda       altrimenti

Questo garantisce ``N(x) + N(-x) == 1`` per costruzione, indipendentemente
dalla precisione dell'approssimazione. La parity di Black-Scholes è
esattamente quella somma, quindi vale a precisione macchina anche se il valore
assoluto di N fosse impreciso. Chi tocca questa funzione deve preservare la
simmetria, non solo l'accuratezza.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

_INV_SQRT_2PI = 0.3989422804014327
_SQRT_2PI = 2.506628274631

_HART_SPLIT = 7.07106781186547

type FloatArray = NDArray[np.float64]


def norm_pdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Densità della normale standard: l'altezza della campana nel punto x."""
    return _INV_SQRT_2PI * np.exp(-(np.asarray(x) ** 2) / 2.0)


def norm_cdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Funzione di ripartizione: l'area sotto la campana fino al punto x."""
    xv = np.asarray(x, dtype=np.float64)
    xa = np.abs(xv)
    e = np.exp(-xa * xa / 2.0)

    num = 3.52624965998911e-2 * xa + 0.700383064443688
    num = num * xa + 6.37396220353165
    num = num * xa + 33.912866078383
    num = num * xa + 112.079291497871
    num = num * xa + 221.213596169931
    num = num * xa + 220.206867912376

    den = 8.83883476483184e-2 * xa + 1.75566716318264
    den = den * xa + 16.064177579207
    den = den * xa + 86.7807322029461
    den = den * xa + 296.564248779674
    den = den * xa + 637.333633378831
    den = den * xa + 793.826512519948
    den = den * xa + 440.413735824752

    polynomial_tail = e * num / den

    cf = xa + 0.65
    cf = xa + 4.0 / cf
    cf = xa + 3.0 / cf
    cf = xa + 2.0 / cf
    cf = xa + 1.0 / cf
    continued_tail = e / (cf * _SQRT_2PI)

    tail = np.where(xa < _HART_SPLIT, polynomial_tail, continued_tail)
    tail = np.where(xa > 37.0, 0.0, tail)

    result = np.where(xv > 0.0, 1.0 - tail, tail)
    return result if result.ndim else np.float64(result)
