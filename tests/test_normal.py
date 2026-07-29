"""Verifica della normale standard.

--- COME FUNZIONA UN TEST ---
Un test è una funzione che verifica un'affermazione sul codice. Se
l'affermazione è falsa, il test "fallisce" e lo strumento lo segnala.

Le regole di pytest (lo strumento che li esegue) sono tre convenzioni:
  1. i file si chiamano `test_*.py`;
  2. le funzioni si chiamano `test_*`;
  3. dentro si usa la parola chiave `assert`.

`assert CONDIZIONE` significa: "a questo punto la condizione DEVE essere vera".
Se lo è, non succede nulla e si prosegue. Se non lo è, il test si ferma e
pytest stampa cosa valeva davvero. Non serve altro: niente `expect(...)`,
niente confronti da dichiarare.

Perché scrivere test? Perché permettono di cambiare il codice senza paura. Se
domani ottimizzi `norm_cdf` e rompi qualcosa, questi test te lo dicono in un
secondo invece che dopo settimane, davanti a un prezzo sbagliato.
"""

from __future__ import annotations

import math

import numpy as np

# `pytest` è l'unica libreria di test che serve. Va installata (sta fra le
# dipendenze di sviluppo in pyproject.toml), a differenza di `math`.
import pytest

from simulatore_opzioni_python.pricing import norm_cdf, norm_pdf


def norm_cdf_reference(x: float) -> float:
    """Riferimento indipendente: erf per serie di Taylor.

    Non condivide nulla con le approssimazioni razionali che deve validare,
    quindi un accordo fra i due è evidenza reale e non una tautologia.
    """
    z = x / math.sqrt(2.0)
    term = z
    total = z
    for n in range(1, 200):
        term *= -(z * z) / n
        total += term / (2 * n + 1)
    return 0.5 * (1.0 + (2.0 / math.sqrt(math.pi)) * total)


# --- CLASSI COME RAGGRUPPAMENTO -------------------------------------------
# Una `class` il cui nome comincia con `Test` è, per pytest, un contenitore di
# test. Qui NON serve a creare oggetti: serve solo a raggruppare i test che
# riguardano la stessa cosa, così l'output è leggibile e si può eseguire un
# solo gruppo alla volta.
#
# Ogni metodo riceve `self` come primo argomento (vedi types.py), anche se qui
# non lo usa: è la firma che Python richiede per i metodi.
class TestNormCdf:
    def test_simmetria_a_precisione_macchina(self) -> None:
        # Questa proprietà, non l'accuratezza, è ciò che rende esatta la
        # put-call parity. Chi modifica norm_cdf deve preservarla.
        for i in range(-60, 61):
            x = i / 10.0
            assert abs(float(norm_cdf(x)) + float(norm_cdf(-x)) - 1.0) < 1e-15

    def test_vale_mezzo_in_zero(self) -> None:
        assert float(norm_cdf(0.0)) == 0.5

    def test_valori_tabulati_noti(self) -> None:
        # --- `pytest.approx`: confrontare numeri decimali ------------------
        # I numeri con la virgola sono memorizzati in binario, e quasi mai in
        # modo esatto. Il caso classico: in Python `0.1 + 0.2 == 0.3` è FALSO,
        # perché il risultato vale 0.30000000000000004.
        #
        # Quindi non si usa mai `==` fra risultati di calcoli decimali. Si usa
        # `pytest.approx(atteso, abs=tolleranza)`, che significa "uguale a meno
        # di quella differenza". Esiste anche `rel=` per una tolleranza
        # relativa, in percentuale del valore.
        assert float(norm_cdf(1.96)) == pytest.approx(0.9750021048518, abs=1e-12)
        assert float(norm_cdf(1.0)) == pytest.approx(0.8413447460685429, abs=1e-13)
        assert float(norm_cdf(-1.0)) == pytest.approx(0.15865525393145707, abs=1e-13)
        assert float(norm_cdf(2.5)) == pytest.approx(0.9937903346742, abs=1e-12)

    def test_accordo_col_riferimento_indipendente(self) -> None:
        # Il confronto si ferma a |x| = 3 per un limite del RIFERIMENTO, non
        # di norm_cdf: la serie di Taylor è alternante e il termine di modulo
        # massimo vale circa e^(x²/2), quindi la cancellazione catastrofica
        # distrugge circa x²/2 * log10(e) cifre significative. Le code oltre
        # |x| = 3 sono coperte dai valori tabulati e dal test di saturazione.
        for i in range(-12, 13):
            x = i / 4.0
            assert abs(float(norm_cdf(x)) - norm_cdf_reference(x)) < 1e-14

    def test_satura_nelle_code_estreme(self) -> None:
        assert float(norm_cdf(40.0)) == 1.0
        assert float(norm_cdf(-40.0)) == 0.0
        assert float(norm_cdf(8.0)) > 0.9999999999999
        assert 0.0 < float(norm_cdf(-8.0)) < 1e-14

    def test_e_monotona_crescente(self) -> None:
        previous = float(norm_cdf(-10.0))
        for i in range(-200, 201):
            current = float(norm_cdf(i / 20.0))
            assert current >= previous
            previous = current

    def test_vettorizza_sugli_array(self) -> None:
        # Il motore prezza intere curve di payoff in una chiamata sola: la
        # funzione deve accettare array senza doverla riscrivere.
        xs = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        result = np.asarray(norm_cdf(xs))
        # `.shape` è la forma dell'array. `(5,)` è una TUPLA di un solo
        # elemento: una sequenza immutabile. La virgola finale non è un refuso,
        # serve a distinguerla da una semplice parentesi.
        assert result.shape == (5,)
        # --- `zip`: scorrere due sequenze in parallelo ---------------------
        # Accoppia il primo di `xs` col primo di `result`, il secondo col
        # secondo, e così via. A ogni giro si ricevono due valori insieme.
        #
        # `strict=True` fa fallire se le due sequenze hanno lunghezze diverse.
        # Senza, `zip` si fermerebbe alla più corta IN SILENZIO, e metà del
        # test non verrebbe eseguita senza che nessuno se ne accorga.
        for x, value in zip(xs, result, strict=True):
            assert value == pytest.approx(float(norm_cdf(float(x))), abs=1e-15)


class TestNormPdf:
    def test_vale_uno_su_radice_di_due_pi_in_zero(self) -> None:
        assert float(norm_pdf(0.0)) == pytest.approx(0.3989422804014327, abs=1e-15)

    def test_e_pari(self) -> None:
        for i in range(0, 51):
            x = i / 10.0
            assert float(norm_pdf(x)) == float(norm_pdf(-x))
