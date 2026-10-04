"""Tests of the standard normal distribution."""

from __future__ import annotations

import math

import numpy as np
import pytest

from options_simulator.pricing import norm_cdf, norm_pdf


def norm_cdf_reference(x: float) -> float:
    """Independent reference: erf via its Taylor series.

    It shares nothing with the rational approximations it validates, so
    agreement between the two is real evidence rather than a tautology.
    """
    z = x / math.sqrt(2.0)
    term = z
    total = z
    for n in range(1, 200):
        term *= -(z * z) / n
        total += term / (2 * n + 1)
    return 0.5 * (1.0 + (2.0 / math.sqrt(math.pi)) * total)


class TestNormCdf:
    def test_symmetric_to_machine_precision(self) -> None:
        for i in range(-60, 61):
            x = i / 10.0
            assert abs(float(norm_cdf(x)) + float(norm_cdf(-x)) - 1.0) < 1e-15

    def test_is_half_at_zero(self) -> None:
        assert float(norm_cdf(0.0)) == 0.5

    def test_known_table_values(self) -> None:
        assert float(norm_cdf(1.96)) == pytest.approx(0.9750021048518, abs=1e-12)
        assert float(norm_cdf(1.0)) == pytest.approx(0.8413447460685429, abs=1e-13)
        assert float(norm_cdf(-1.0)) == pytest.approx(0.15865525393145707, abs=1e-13)
        assert float(norm_cdf(2.5)) == pytest.approx(0.9937903346742, abs=1e-12)

    def test_agrees_with_independent_reference(self) -> None:
        for i in range(-12, 13):
            x = i / 4.0
            assert abs(float(norm_cdf(x)) - norm_cdf_reference(x)) < 1e-14

    def test_saturates_in_extreme_tails(self) -> None:
        assert float(norm_cdf(40.0)) == 1.0
        assert float(norm_cdf(-40.0)) == 0.0
        assert float(norm_cdf(8.0)) > 0.9999999999999
        assert 0.0 < float(norm_cdf(-8.0)) < 1e-14

    def test_is_monotonically_increasing(self) -> None:
        previous = float(norm_cdf(-10.0))
        for i in range(-200, 201):
            current = float(norm_cdf(i / 20.0))
            assert current >= previous
            previous = current

    def test_vectorises_over_arrays(self) -> None:
        xs = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        result = np.asarray(norm_cdf(xs))
        assert result.shape == (5,)
        for x, value in zip(xs, result, strict=True):
            assert value == pytest.approx(float(norm_cdf(float(x))), abs=1e-15)


class TestNormPdf:
    def test_is_one_over_sqrt_two_pi_at_zero(self) -> None:
        assert float(norm_pdf(0.0)) == pytest.approx(0.3989422804014327, abs=1e-15)

    def test_is_even(self) -> None:
        for i in range(0, 51):
            x = i / 10.0
            assert float(norm_pdf(x)) == float(norm_pdf(-x))
