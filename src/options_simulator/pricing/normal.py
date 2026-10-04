"""Standard normal distribution.

Two mathematical functions, nothing else. The "standard normal" is the Gaussian
bell curve: ``norm_pdf`` returns the height of the bell at a point, ``norm_cdf``
the area under the bell up to that point (the probability of a smaller value).
Black-Scholes uses both.

It uses Hart's algorithm (1968) as popularised by Graeme West, accurate to
double precision (~1e-15). The original prototype used Abramowitz-Stegun
26.2.17, with an absolute error of ~7.5e-8: invisible on a four-decimal price,
but multiplied by 500 units of underlying it exceeds a cent.

INVARIANT — the reason put-call parity holds to 1e-15.
``norm_cdf`` always computes the tail ``N(-|x|)`` and then mirrors it::

    N(x) = 1 - tail   if x > 0
    N(x) = tail       otherwise

This guarantees ``N(x) + N(-x) == 1`` by construction, whatever the accuracy of
the approximation. Black-Scholes parity is exactly that sum, so it holds to
machine precision even if the absolute value of N were imprecise. Anyone
touching this function must preserve the symmetry, not just the accuracy.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

_INV_SQRT_2PI = 0.3989422804014327
_SQRT_2PI = 2.506628274631

_HART_SPLIT = 7.07106781186547

type FloatArray = NDArray[np.float64]


def norm_pdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Standard normal density: the height of the bell curve at x."""
    return _INV_SQRT_2PI * np.exp(-(np.asarray(x) ** 2) / 2.0)


def norm_cdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Cumulative distribution: the area under the bell curve up to x."""
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
