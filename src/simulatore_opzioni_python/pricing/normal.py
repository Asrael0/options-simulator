"""Distribuzione normale standard.

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

NOTA DI PYTHON — le funzioni accettano sia scalari sia array NumPy senza
scriverle due volte: ``np.exp`` e compagnia funzionano su entrambi, e
``np.where`` sostituisce l'``if`` quando la condizione è un array. È il modo
idiomatico di scrivere codice numerico che vettorizza.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# 1 / sqrt(2*pi) e sqrt(2*pi), scritti a mano per non ricalcolarli.
_INV_SQRT_2PI = 0.3989422804014327
_SQRT_2PI = 2.506628274631

# Soglia fra il ramo polinomiale e la frazione continua per la coda estrema.
_HART_SPLIT = 7.07106781186547

type FloatArray = NDArray[np.float64]


def norm_pdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Densità della normale standard."""
    return _INV_SQRT_2PI * np.exp(-(np.asarray(x) ** 2) / 2.0)


def norm_cdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Funzione di ripartizione della normale standard."""
    xv = np.asarray(x, dtype=np.float64)
    xa = np.abs(xv)
    e = np.exp(-xa * xa / 2.0)

    # Ramo polinomiale: rapporto di due polinomi valutati con Horner.
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

    # Frazione continua per la coda estrema.
    cf = xa + 0.65
    cf = xa + 4.0 / cf
    cf = xa + 3.0 / cf
    cf = xa + 2.0 / cf
    cf = xa + 1.0 / cf
    continued_tail = e / (cf * _SQRT_2PI)

    tail = np.where(xa < _HART_SPLIT, polynomial_tail, continued_tail)
    # Oltre 37 deviazioni standard la coda è sotto il minimo denormale.
    tail = np.where(xa > 37.0, 0.0, tail)

    result = np.where(xv > 0.0, 1.0 - tail, tail)
    # Uno scalare in ingresso deve dare uno scalare in uscita, non un array 0-d.
    return result if result.ndim else np.float64(result)
