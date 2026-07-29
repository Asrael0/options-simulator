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

# --- NUMPY: la libreria per calcolare su tanti numeri insieme --------------
# `import numpy as np` importa la libreria dandole il soprannome `np`. È una
# convenzione universale: in qualunque codice Python scientifico, `np` è NumPy.
#
# L'idea centrale di NumPy è l'ARRAY: una sequenza di numeri su cui si opera
# TUTTA IN UNA VOLTA. In Python normale, per raddoppiare mille numeri servirebbe
# un ciclo che gira mille volte, interpretato riga per riga. Con NumPy si scrive
# `array * 2` e il lavoro viene eseguito in C, cento volte più in fretta.
#
# È la ragione per cui `np.exp(x)` funziona sia se `x` è un singolo numero sia
# se è un array di diecimila: nel secondo caso calcola l'esponenziale di tutti.
import numpy as np

# `numpy.typing` contiene i tipi per annotare gli array.
from numpy.typing import NDArray

# 1 / sqrt(2*pi) e sqrt(2*pi), scritti a mano per non ricalcolarli.
_INV_SQRT_2PI = 0.3989422804014327
_SQRT_2PI = 2.506628274631

# Soglia fra il ramo polinomiale e la frazione continua per la coda estrema.
_HART_SPLIT = 7.07106781186547

# --- `type`: dichiarare un alias di tipo in modo esplicito -----------------
# Equivale a `FloatArray = NDArray[np.float64]` ma dice a chi legge (e a mypy)
# che è un alias intenzionale e non una variabile.
# `NDArray[np.float64]` significa: un array NumPy di numeri decimali a 64 bit.
type FloatArray = NDArray[np.float64]


# I due tipi separati da `|` nella firma dicono: questa funzione accetta sia un
# singolo numero sia un array, e restituisce di conseguenza. È possibile
# proprio perché le operazioni NumPy funzionano su entrambi.
def norm_pdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Densità della normale standard: l'altezza della campana nel punto x."""
    # `np.asarray(x)` converte l'ingresso in array. Se è già un array non fa
    # nulla; se è un numero singolo lo incarta. Serve a garantire che le
    # operazioni successive si comportino allo stesso modo nei due casi.
    #
    # `**` è l'elevamento a potenza: `x ** 2` è x al quadrato.
    # `np.exp(y)` è l'esponenziale e^y.
    return _INV_SQRT_2PI * np.exp(-(np.asarray(x) ** 2) / 2.0)


def norm_cdf(x: float | FloatArray) -> np.float64 | FloatArray:
    """Funzione di ripartizione: l'area sotto la campana fino al punto x."""
    # `dtype=np.float64` forza il tipo dei numeri: anche se arriva un intero,
    # da qui in poi si lavora in virgola mobile a doppia precisione.
    xv = np.asarray(x, dtype=np.float64)
    # `np.abs` è il valore assoluto: toglie il segno.
    xa = np.abs(xv)
    e = np.exp(-xa * xa / 2.0)

    # --- VALUTAZIONE DI UN POLINOMIO CON LO SCHEMA DI HORNER ---------------
    # Invece di calcolare a*x^5 + b*x^4 + ... (che richiede tante potenze), si
    # riscrive come (((a*x + b)*x + c)*x + d)... — solo moltiplicazioni e
    # addizioni. Meno operazioni e meno errore di arrotondamento.
    #
    # Nota che `num` viene RIASSEGNATA a ogni riga: in Python una variabile può
    # essere sovrascritta con un nuovo valore quante volte si vuole.
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

    # --- `np.where`: l'`if` che funziona sugli array -----------------------
    # Un `if` normale decide una volta sola, su un singolo valore. Ma qui `xa`
    # può essere un array di mille numeri, ognuno dei quali vorrebbe una
    # decisione diversa.
    #
    # `np.where(condizione, se_vero, se_falso)` sceglie ELEMENTO PER ELEMENTO.
    # Nota il prezzo da pagare: entrambi i rami vengono calcolati per intero, e
    # poi si tiene solo la metà che serve. Su array è comunque più veloce che
    # scorrere con un ciclo Python.
    tail = np.where(xa < _HART_SPLIT, polynomial_tail, continued_tail)
    # Oltre 37 deviazioni standard la coda è sotto il minimo denormale.
    tail = np.where(xa > 37.0, 0.0, tail)

    result = np.where(xv > 0.0, 1.0 - tail, tail)
    # `.ndim` è il numero di dimensioni di un array: 0 per uno scalare, 1 per
    # una sequenza, 2 per una matrice. Uno scalare in ingresso deve dare uno
    # scalare in uscita, non un array a zero dimensioni, che si comporterebbe
    # in modo sottilmente diverso.
    return result if result.ndim else np.float64(result)
