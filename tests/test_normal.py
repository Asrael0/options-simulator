"""Verifica della normale standard."""

from __future__ import annotations

import math

import numpy as np
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


class TestNormCdf:
    def test_simmetria_a_precisione_macchina(self) -> None:
        for i in range(-60, 61):
            x = i / 10.0
            assert abs(float(norm_cdf(x)) + float(norm_cdf(-x)) - 1.0) < 1e-15

    def test_vale_mezzo_in_zero(self) -> None:
        assert float(norm_cdf(0.0)) == 0.5

    def test_valori_tabulati_noti(self) -> None:
        assert float(norm_cdf(1.96)) == pytest.approx(0.9750021048518, abs=1e-12)
        assert float(norm_cdf(1.0)) == pytest.approx(0.8413447460685429, abs=1e-13)
        assert float(norm_cdf(-1.0)) == pytest.approx(0.15865525393145707, abs=1e-13)
        assert float(norm_cdf(2.5)) == pytest.approx(0.9937903346742, abs=1e-12)

    def test_accordo_col_riferimento_indipendente(self) -> None:
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
        xs = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        result = np.asarray(norm_cdf(xs))
        assert result.shape == (5,)
        for x, value in zip(xs, result, strict=True):
            assert value == pytest.approx(float(norm_cdf(float(x))), abs=1e-15)


class TestNormPdf:
    def test_vale_uno_su_radice_di_due_pi_in_zero(self) -> None:
        assert float(norm_pdf(0.0)) == pytest.approx(0.3989422804014327, abs=1e-15)

    def test_e_pari(self) -> None:
        for i in range(0, 51):
            x = i / 10.0
            assert float(norm_pdf(x)) == float(norm_pdf(-x))
