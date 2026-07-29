"""Verifica di Black-Scholes-Merton contro la tabella di riferimento.

Parametri base: S=100, K=100, T=30gg, r=4%, IV=30%.

I test sono divisi in tre gruppi con scopi diversi:
  - VALORI DI RIFERIMENTO: numeri esatti, presi dal prototipo originale.
  - RELAZIONI STRUTTURALI: proprietà che devono valere sempre (la put-call
    parity, la monotonia nel volatilità). Non dipendono da numeri specifici.
  - ROBUSTEZZA: i casi limite. T = 0, volatilità nulla, strike assurdi. È dove
    il codice normalmente si rompe, quindi è dove i test servono di più.
"""

from __future__ import annotations

import math

import pytest

from simulatore_opzioni_python.pricing import (
    black_scholes,
    probability_itm,
    years_from_days,
)

from .helpers import spec


class TestValoriDiRiferimento:
    def test_call_atm_europea(self) -> None:
        assert black_scholes(spec(right="call")).price == pytest.approx(3.5911, abs=5e-5)

    def test_put_atm_europea(self) -> None:
        assert black_scholes(spec(right="put")).price == pytest.approx(3.2629, abs=5e-5)

    def test_greche_call_atm(self) -> None:
        g = black_scholes(spec(right="call"))
        assert g.delta == pytest.approx(0.5324, abs=5e-5)
        assert g.gamma == pytest.approx(0.0462, abs=5e-5)
        assert g.vega_per_point == pytest.approx(0.1140, abs=5e-5)
        assert g.theta_per_day == pytest.approx(-0.0624, abs=5e-5)


class TestRelazioniStrutturali:
    def test_put_call_parity(self) -> None:
        # C - P = S - K*e^(-rT)
        for strike in (70.0, 90.0, 100.0, 110.0, 140.0):
            for days in (1.0, 30.0, 180.0, 730.0):
                call = black_scholes(spec(strike=strike, days_to_expiry=days, right="call"))
                put = black_scholes(spec(strike=strike, days_to_expiry=days, right="put"))
                t = years_from_days(days)
                expected = 100.0 - strike * math.exp(-0.04 * t)
                assert abs(call.price - put.price - expected) < 1e-9

    def test_parity_con_dividend_yield(self) -> None:
        # C - P = S*e^(-qT) - K*e^(-rT)
        q = 0.03
        t = years_from_days(90.0)
        call = black_scholes(spec(days_to_expiry=90.0, dividend_yield=q, right="call"))
        put = black_scholes(spec(days_to_expiry=90.0, dividend_yield=q, right="put"))
        expected = 100.0 * math.exp(-q * t) - 100.0 * math.exp(-0.04 * t)
        assert abs(call.price - put.price - expected) < 1e-9

    def test_gamma_e_vega_identici_fra_call_e_put(self) -> None:
        for strike in (80.0, 95.0, 100.0, 105.0, 130.0):
            call = black_scholes(spec(strike=strike, right="call"))
            put = black_scholes(spec(strike=strike, right="put"))
            assert call.gamma == put.gamma
            assert call.vega_per_point == put.vega_per_point

    def test_delta_call_meno_delta_put_vale_e_meno_qt(self) -> None:
        call = black_scholes(spec(right="call"))
        put = black_scholes(spec(right="put"))
        assert call.delta - put.delta == pytest.approx(1.0, abs=1e-12)

    def test_prezzo_monotono_crescente_nella_volatilita(self) -> None:
        previous = -math.inf
        for i in range(1, 31):
            price = black_scholes(spec(iv=i * 0.05)).price
            assert price > previous
            previous = price

    def test_prezzo_sopra_il_valore_intrinseco(self) -> None:
        for strike in (60.0, 80.0, 100.0, 120.0, 150.0):
            call = black_scholes(spec(strike=strike, right="call")).price
            assert call >= max(100.0 - strike, 0.0) - 1e-12
            assert black_scholes(spec(strike=strike, right="put")).price >= 0.0


class TestRobustezza:
    def test_a_scadenza_restituisce_il_valore_intrinseco(self) -> None:
        assert black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="call")).price == 10.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="call")).price == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="put")).price == 10.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="put")).price == 0.0

        # Le greche di sensibilità sono nulle: non c'è più incertezza.
        itm_call = black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="call"))
        assert itm_call.delta == 1.0
        assert itm_call.gamma == 0.0
        assert itm_call.vega_per_point == 0.0
        assert itm_call.theta_per_day == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="call")).delta == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="put")).delta == -1.0

    def test_scadenze_negative_trattate_come_scadute(self) -> None:
        assert black_scholes(spec(days_to_expiry=-10.0, strike=90.0)).price == 10.0

    def test_iv_verso_zero_converge_al_payoff_sul_forward(self) -> None:
        # Limite deterministico di Black-Scholes per sigma -> 0: il
        # sottostante vale con certezza il suo forward. Il prototipo
        # restituiva l'intrinseco sullo SPOT, corretto solo per T = 0.
        t = years_from_days(30.0)
        forward = 100.0 * math.exp(0.04 * t)
        expected = math.exp(-0.04 * t) * max(forward - 100.0, 0.0)

        assert black_scholes(spec(iv=0.0)).price == pytest.approx(expected, abs=1e-12)
        for iv in (1e-4, 1e-5, 1e-6):
            assert black_scholes(spec(iv=iv)).price == pytest.approx(expected, abs=1e-6)

    def test_strike_molto_lontani_dallo_spot(self) -> None:
        far_otm_call = black_scholes(spec(strike=100_000.0, right="call"))
        assert math.isfinite(far_otm_call.price)
        assert 0.0 <= far_otm_call.price < 1e-9
        assert far_otm_call.delta == pytest.approx(0.0, abs=1e-9)

        deep_itm_call = black_scholes(spec(strike=0.01, right="call"))
        assert math.isfinite(deep_itm_call.price)
        assert deep_itm_call.delta == pytest.approx(1.0, abs=1e-6)

        far_otm_put = black_scholes(spec(strike=0.01, right="put"))
        assert 0.0 <= far_otm_put.price < 1e-9

        for g in (far_otm_call, deep_itm_call, far_otm_put):
            assert math.isfinite(g.gamma)
            assert math.isfinite(g.vega_per_point)
            assert math.isfinite(g.theta_per_day)
            assert math.isfinite(g.rho_per_point)

    def test_spot_o_strike_nulli(self) -> None:
        zero_spot = black_scholes(spec(spot=0.0, right="put"))
        assert math.isfinite(zero_spot.price)
        expected = 100.0 * math.exp(-0.04 * years_from_days(30.0))
        assert zero_spot.price == pytest.approx(expected, abs=1e-12)
        assert math.isfinite(black_scholes(spec(strike=0.0)).price)

    def test_scadenze_lunghe_e_iv_estreme(self) -> None:
        long_dated = black_scholes(spec(days_to_expiry=3650.0, iv=2.5))
        assert math.isfinite(long_dated.price)
        assert 0.0 < long_dated.price < 100.0


class TestProbabilitaItm:
    def test_appena_sotto_meta_per_una_call_atm(self) -> None:
        # N(d2), con d2 < d1.
        p = probability_itm(spec(right="call"))
        assert 0.4 < p < 0.5

    def test_complementare_fra_call_e_put(self) -> None:
        for strike in (85.0, 100.0, 120.0):
            call = probability_itm(spec(strike=strike, right="call"))
            put = probability_itm(spec(strike=strike, right="put"))
            assert call + put == pytest.approx(1.0, abs=1e-12)

    def test_decresce_al_crescere_dello_strike(self) -> None:
        previous = math.inf
        for strike in (80.0, 90.0, 100.0, 110.0, 120.0):
            p = probability_itm(spec(strike=strike, right="call"))
            assert p < previous
            previous = p

    def test_degenera_a_scadenza(self) -> None:
        assert probability_itm(spec(days_to_expiry=0.0, strike=90.0, right="call")) == 1.0
        assert probability_itm(spec(days_to_expiry=0.0, strike=110.0, right="call")) == 0.0
