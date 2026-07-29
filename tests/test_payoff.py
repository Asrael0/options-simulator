"""Verifica del P&L multi-gamba contro la tabella di riferimento."""

from __future__ import annotations

import math

import pytest

from simulatore_opzioni_python.pricing import (
    ExerciseStyle,
    Leg,
    ResolvedLeg,
    Sizing,
    break_evens,
    moneyness,
    net_cost,
    payoff_bounds,
    pl_at_expiry,
    pl_at_market,
    resolve_legs,
    trade_cost,
)

from .helpers import market, option, option_at_premium, stock

# L'annotazione non è decorativa: senza, mypy inferisce `str` e la costante
# non è più accettata dove serve un Literal["european", "american"].
EUROPEAN: ExerciseStyle = "european"


def build(legs: list[Leg], days: float = 30.0) -> list[ResolvedLeg]:
    return resolve_legs(legs, market(days_to_expiry=days), EUROPEAN)


class TestBearPutSpread:
    """Long put 100 / short put 90."""

    # --- `@pytest.fixture`: preparare i dati per più test ------------------
    # Un metodo decorato con `@pytest.fixture` non è un test: è una FABBRICA di
    # dati. Qualunque test di questa classe che dichiari un parametro chiamato
    # `position` lo riceve automaticamente, già costruito.
    #
    # È l'iniezione di dipendenze di pytest: il collegamento avviene per NOME
    # del parametro, non per import. Vantaggio: la posizione viene ricostruita
    # da zero per ogni test, quindi un test non può sporcare i dati di un altro.
    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build([option("put", "long", 100.0), option("put", "short", 90.0)])

    def test_costa_2_862(self, position: list[ResolvedLeg]) -> None:
        assert net_cost(position) == pytest.approx(2.862, abs=5e-4)

    def test_profitto_massimo_e_spread_meno_costo(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(7.138, abs=5e-4)
        assert bounds.max_profit == pytest.approx(10.0 - net_cost(position), abs=1e-9)
        assert bounds.profit_unbounded is False

    def test_perdita_massima_e_il_costo_netto(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-2.862, abs=5e-4)
        assert bounds.max_loss == pytest.approx(-net_cost(position), abs=1e-9)
        assert bounds.loss_unbounded is False

    def test_unico_break_even_con_pl_esattamente_zero(self, position: list[ResolvedLeg]) -> None:
        bes = break_evens(position)
        assert len(bes) == 1
        assert bes[0] == pytest.approx(97.138, abs=5e-4)
        # Break-even risolto analiticamente, non per campionamento: il residuo
        # è errore di arrotondamento in virgola mobile, non errore di griglia.
        assert abs(pl_at_expiry(position, bes[0])) < 1e-9

    def test_piatto_fuori_dagli_strike(self, position: list[ResolvedLeg]) -> None:
        assert pl_at_expiry(position, 80.0) == pytest.approx(pl_at_expiry(position, 90.0), abs=1e-9)
        assert pl_at_expiry(position, 0.0) == pytest.approx(7.138, abs=5e-4)
        assert pl_at_expiry(position, 110.0) == pytest.approx(
            pl_at_expiry(position, 100.0), abs=1e-9
        )
        assert pl_at_expiry(position, 200.0) == pytest.approx(-2.862, abs=5e-4)


class TestIronCondor:
    """85 / 95 / 105 / 115."""

    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build(
            [
                option("put", "long", 85.0),
                option("put", "short", 95.0),
                option("call", "short", 105.0),
                option("call", "long", 115.0),
            ]
        )

    def test_incassa_un_credito_di_2_693(self, position: list[ResolvedLeg]) -> None:
        # net_cost negativo = credito.
        assert net_cost(position) == pytest.approx(-2.693, abs=5e-4)

    def test_profitto_massimo_uguale_al_credito(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(2.693, abs=5e-4)
        assert bounds.max_profit == pytest.approx(-net_cost(position), abs=1e-9)

    def test_perdita_simmetrica_su_entrambe_le_ali(self, position: list[ResolvedLeg]) -> None:
        assert pl_at_expiry(position, 85.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 115.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 85.0) == pytest.approx(
            pl_at_expiry(position, 115.0), abs=1e-9
        )

        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-7.307, abs=5e-4)
        assert bounds.profit_unbounded is False
        assert bounds.loss_unbounded is False

    def test_piatto_oltre_le_ali(self, position: list[ResolvedLeg]) -> None:
        # Le gambe comprate chiudono il rischio.
        assert pl_at_expiry(position, 0.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 500.0) == pytest.approx(-7.307, abs=5e-4)

    def test_due_break_even(self, position: list[ResolvedLeg]) -> None:
        bes = break_evens(position)
        assert len(bes) == 2
        assert 85.0 < bes[0] < 95.0
        assert 105.0 < bes[1] < 115.0
        for be in bes:
            assert abs(pl_at_expiry(position, be)) < 1e-9


class TestCollar:
    """Azione @100 + long put 90 + short call 110, T = 60gg."""

    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build(
            [
                stock("long", 100.0),
                option("put", "long", 90.0),
                option("call", "short", 110.0),
            ],
            days=60.0,
        )

    def test_floor_costante_sotto_lo_strike_della_put(self, position: list[ResolvedLeg]) -> None:
        for spot in (0.0, 30.0, 60.0, 89.99, 90.0):
            assert pl_at_expiry(position, spot) == pytest.approx(-9.386, abs=5e-4)
        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-9.386, abs=5e-4)
        assert bounds.loss_unbounded is False

    def test_cap_costante_sopra_lo_strike_della_call(self, position: list[ResolvedLeg]) -> None:
        for spot in (110.0, 130.0, 400.0):
            assert pl_at_expiry(position, spot) == pytest.approx(10.614, abs=5e-4)
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(10.614, abs=5e-4)
        assert bounds.profit_unbounded is False

    def test_lineare_uno_a_uno_fra_gli_strike(self, position: list[ResolvedLeg]) -> None:
        # Il tratto lineare è [90, 110]: l'ultima differenza utile è 110 - 109.
        for spot in range(90, 110):
            delta = pl_at_expiry(position, spot + 1) - pl_at_expiry(position, spot)
            assert delta == pytest.approx(1.0, abs=1e-9)
        assert pl_at_expiry(position, 110.0) - pl_at_expiry(position, 90.0) == pytest.approx(
            20.0, abs=1e-9
        )

    def test_ampiezza_pari_alla_distanza_fra_gli_strike(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit - bounds.max_loss == pytest.approx(20.0, abs=1e-9)


class TestEstremiIllimitati:
    def test_profitto_illimitato_di_una_call_comprata(self) -> None:
        position = build([option("call", "long", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.profit_unbounded is True
        assert bounds.max_profit == math.inf
        assert bounds.loss_unbounded is False
        assert bounds.max_loss == pytest.approx(-net_cost(position), abs=1e-9)

    def test_perdita_illimitata_di_una_call_venduta_nuda(self) -> None:
        # Il prototipo riportava qui una perdita massima FINITA, perché
        # campionava solo il range visibile del grafico. Su uno strumento
        # didattico è esattamente l'informazione che non deve mancare.
        position = build([option("call", "short", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.loss_unbounded is True
        assert bounds.max_loss == -math.inf
        assert bounds.profit_unbounded is False
        assert bounds.max_profit == pytest.approx(-net_cost(position), abs=1e-9)

    def test_put_comprata_limitata_dal_prezzo_zero(self) -> None:
        position = build([option("put", "long", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.profit_unbounded is False
        assert bounds.max_profit == pytest.approx(100.0 - net_cost(position), abs=1e-9)

    def test_esposizione_lineare_dell_azione(self) -> None:
        assert payoff_bounds(build([stock("long", 100.0)])).profit_unbounded is True
        assert payoff_bounds(build([stock("short", 100.0)])).loss_unbounded is True


class TestBreakEven:
    def test_call_singola_a_strike_piu_premio(self) -> None:
        position = build([option("call", "long", 100.0)])
        bes = break_evens(position)
        assert len(bes) == 1
        assert bes[0] == pytest.approx(100.0 + net_cost(position), abs=1e-9)
        assert abs(pl_at_expiry(position, bes[0])) < 1e-9

    def test_entrambi_i_break_even_di_uno_straddle(self) -> None:
        position = build([option("call", "long", 100.0), option("put", "long", 100.0)])
        bes = break_evens(position)
        assert len(bes) == 2
        cost = net_cost(position)
        assert bes[0] == pytest.approx(100.0 - cost, abs=1e-9)
        assert bes[1] == pytest.approx(100.0 + cost, abs=1e-9)

    def test_posizione_azionaria_pura(self) -> None:
        assert break_evens(build([stock("long", 100.0)])) == [100.0]

    def test_nessun_break_even_se_sempre_in_profitto(self) -> None:
        position = build(
            [
                option_at_premium("call", "short", 100.0, 5.0),
                option_at_premium("call", "long", 100.0, 2.0),
            ]
        )
        assert break_evens(position) == []
        assert pl_at_expiry(position, 100.0) == pytest.approx(3.0, abs=1e-9)

    def test_non_duplica_un_break_even_su_uno_strike(self) -> None:
        # Long call 100 a premio zero: il P&L è nullo per tutto il tratto
        # sotto 100 e attraversa lo zero proprio nel vertice.
        position = build([option_at_premium("call", "long", 100.0, 0.0)])
        assert break_evens(position) == [0.0, 100.0]


class TestCostoOperazione:
    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build([option("call", "long", 100.0), option("call", "short", 110.0)])

    def test_bull_call_spread_5_pacchetti_per_100(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))

        # DIVERGENZA NOTA rispetto ai valori del prototipo: 1795.57 / 327.60 /
        # 1467.97 contro 1795.56 / 327.60 / 1467.96.
        #
        # La causa è la funzione di ripartizione normale, non il port. Il
        # prototipo usava Abramowitz-Stegun 26.2.17, con errore assoluto ~8e-6
        # sul prezzo della call ATM; qui si usa Hart, verificato contro una
        # serie di Taylor su erf con residuo 7e-15. Moltiplicato per 500 unità
        # di sottostante, l'errore del prototipo supera il centesimo.
        #
        #   prezzo call ATM   A-S  3.591131034  -> x500 = 1795.5655 -> 1795.57
        #                     Hart 3.591123032  -> x500 = 1795.5615 -> 1795.56
        assert cost.total_outflow == pytest.approx(1795.56, abs=5e-3)
        assert cost.total_inflow == pytest.approx(327.60, abs=5e-3)
        assert cost.net == pytest.approx(1467.96, abs=5e-3)

    def test_scala_linearmente(self, position: list[ResolvedLeg]) -> None:
        single = trade_cost(position, Sizing(contract_multiplier=100.0, packages=1))
        five = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))
        assert five.net == pytest.approx(single.net * 5.0, abs=1e-9)

        mini = trade_cost(position, Sizing(contract_multiplier=10.0, packages=5))
        assert mini.net == pytest.approx(five.net / 10.0, abs=1e-9)

    def test_netto_negativo_per_una_posizione_a_credito(self) -> None:
        credit = build([option("put", "short", 95.0), option("put", "long", 85.0)])
        cost = trade_cost(credit, Sizing(contract_multiplier=100.0, packages=1))
        assert cost.net < 0.0
        assert cost.total_inflow > cost.total_outflow

    def test_coincide_con_net_cost_per_unita(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=1.0, packages=1))
        assert cost.net == pytest.approx(net_cost(position), abs=1e-9)

    def test_conta_le_unita_gamba_per_gamba(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))
        for leg_cost in cost.legs:
            assert leg_cost.units == 500.0
            assert leg_cost.per_contract == pytest.approx(leg_cost.unit_price * 100.0, abs=1e-9)


class TestQuantitaElevate:
    def test_scala_linearmente_e_resta_finito(self) -> None:
        one = build([option("call", "long", 100.0)])
        many = build([option("call", "long", 100.0, qty=10_000.0)])

        assert net_cost(many) == pytest.approx(net_cost(one) * 10_000.0, abs=1e-6)
        assert pl_at_expiry(many, 150.0) == pytest.approx(
            pl_at_expiry(one, 150.0) * 10_000.0, abs=1e-6
        )
        assert break_evens(many)[0] == pytest.approx(break_evens(one)[0], abs=1e-9)

        cost = trade_cost(many, Sizing(contract_multiplier=100.0, packages=1000))
        assert math.isfinite(cost.net)


class TestPremioCongelato:
    def test_non_cambia_quando_il_mercato_si_muove(self) -> None:
        # Regressione sul comportamento del prototipo: là il premio veniva
        # riprezzato ai parametri correnti a ogni accesso, quindi muovendo lo
        # spot cambiava anche il costo "già pagato" e i break-even scivolavano.
        entry = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        premium = entry[0].entry_premium

        before = break_evens(entry)[0]
        assert pl_at_expiry(entry, 120.0) == pytest.approx(20.0 - premium, abs=1e-9)
        assert break_evens(entry)[0] == before

    def test_rispetta_un_premio_manuale(self) -> None:
        position = resolve_legs([option_at_premium("call", "long", 100.0, 5.0)], market(), EUROPEAN)
        assert position[0].entry_premium == 5.0
        assert net_cost(position) == 5.0
        assert break_evens(position)[0] == pytest.approx(105.0, abs=1e-9)

    def test_usa_l_override_di_iv_della_gamba(self) -> None:
        base = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        skewed = resolve_legs([option("call", "long", 100.0, iv_override=0.5)], market(), EUROPEAN)
        assert skewed[0].entry_premium > base[0].entry_premium

    def test_prezzo_di_carico_per_la_gamba_azionaria(self) -> None:
        position = resolve_legs([stock("long", 87.5)], market(), EUROPEAN)
        assert position[0].entry_premium == 87.5
        assert pl_at_expiry(position, 100.0) == pytest.approx(12.5, abs=1e-9)


class TestValoreCorrente:
    def test_nullo_se_il_mercato_non_si_e_mosso(self) -> None:
        entry_market = market()
        position = resolve_legs([option("call", "long", 100.0)], entry_market, EUROPEAN)
        assert pl_at_market(position, entry_market, EUROPEAN) == pytest.approx(0.0, abs=1e-12)

    def test_isola_l_effetto_vega(self) -> None:
        position = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        assert pl_at_market(position, market(iv=0.20), EUROPEAN) < 0.0
        assert pl_at_market(position, market(iv=0.40), EUROPEAN) > 0.0

    def test_valuta_la_gamba_azionaria_allo_spot_corrente(self) -> None:
        position = resolve_legs([stock("long", 100.0)], market(), EUROPEAN)
        assert pl_at_market(position, market(spot=115.0), EUROPEAN) == pytest.approx(15.0, abs=1e-9)


class TestMoneyness:
    def test_classifica_call_e_put(self) -> None:
        assert moneyness(option("call", "long", 90.0), 100.0) == "ITM"
        assert moneyness(option("call", "long", 110.0), 100.0) == "OTM"
        assert moneyness(option("put", "long", 110.0), 100.0) == "ITM"
        assert moneyness(option("put", "long", 90.0), 100.0) == "OTM"

    def test_banda_atm_dell_uno_e_mezzo_percento(self) -> None:
        assert moneyness(option("call", "long", 100.0), 100.0) == "ATM"
        assert moneyness(option("call", "long", 100.0), 101.0) == "ATM"
        assert moneyness(option("call", "long", 100.0), 102.0) == "ITM"

    def test_non_classifica_l_azione(self) -> None:
        assert moneyness(stock("long", 100.0), 100.0) == "STOCK"
