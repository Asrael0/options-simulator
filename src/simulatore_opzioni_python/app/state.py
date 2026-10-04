"""Stato della posizione e valori derivati.

--- COSA FA QUESTO FILE ---
È il ponte fra interfaccia e motore. Contiene due cose:

  `PositionState` — tutto ciò che l'utente può modificare: ticker, parametri di
  mercato, gambe, dimensionamento. Solo dati e metodi per cambiarli.

  `compute()`     — prende quello stato e produce `Analytics`, cioè tutti i
  numeri derivati (costo, greche, break-even, curva del payoff…) in un colpo
  solo, chiamando il motore.

Lo stato è DELIBERATAMENTE STUPIDO: nessun calcolo finanziario nei metodi. Se
il pricing finisse dentro i setter, ogni movimento di uno slider ricalcolerebbe
l'albero binomiale in mezzo alla gestione di un evento dell'interfaccia, e non
si capirebbe più quante volte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ..pricing import (
    ExerciseStyle,
    Greeks,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    Resolution,
    ResolvedLeg,
    Right,
    Side,
    Sizing,
    StockLeg,
    TheoreticalPremium,
    TradeCost,
    break_evens,
    net_cost,
    payoff_bounds,
    pl_at_expiry,
    pl_at_market,
    position_greeks,
    price_option,
    probability_of_profit,
    resolve_legs,
    spec_for_leg,
    trade_cost,
)
from .strategies import STRATEGIES, new_leg_id

INITIAL_MARKET = MarketParams(
    spot=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    dividend_yield=0.0,
)

LegType = Right | str


@dataclass(slots=True)
class PositionState:
    """Tutto ciò che l'utente può modificare."""

    ticker: str = "AAPL"
    name: str = "Apple Inc."
    market: MarketParams = INITIAL_MARKET
    entry_market: MarketParams = INITIAL_MARKET
    pin_premiums: bool = True
    exercise: ExerciseStyle = "european"
    compare_exercise: bool = False
    legs: list[Leg] = field(default_factory=lambda: STRATEGIES["single"].build(100.0))
    strategy_key: str = "single"
    target: float = 100.0
    iv_sim: float = 0.30
    sizing: Sizing = field(default_factory=Sizing)
    currency: str = "$"

    # Solo per il grafico, non vengono salvati con la posizione.
    days_forward: float = 0.0
    comparison: PositionState | None = None
    comparison_name: str = ""

    # -- mercato ----------------------------------------------------------

    def set_market(self, **changes: float) -> None:
        # Lo scenario segue il prezzo finché l'utente non lo sposta altrove.
        if "spot" in changes and abs(self.target - self.market.spot) < 1e-9:
            self.target = changes["spot"]
        self.market = replace(self.market, **changes)
        if "iv" in changes:
            self.iv_sim = changes["iv"]
        if not self.pin_premiums:
            self.entry_market = self.market

    def set_pin_premiums(self, pinned: bool) -> None:
        self.pin_premiums = pinned
        if pinned:
            self.entry_market = self.market

    def reprice_entry(self) -> None:
        """Rifissa i premi teorici ai parametri di mercato correnti."""
        self.entry_market = self.market

    # -- gambe ------------------------------------------------------------

    def apply_strategy(self, key: str) -> None:
        strategy = STRATEGIES.get(key)
        if strategy is None:
            return
        self.strategy_key = key
        self.legs = strategy.build(self.market.spot)
        self.entry_market = self.market

    def add_leg(self) -> None:
        self.legs.append(
            OptionLeg(
                leg_id=new_leg_id(),
                side="long",
                qty=1.0,
                right="call",
                strike=round(self.market.spot),
            )
        )

    def remove_leg(self, leg_id: str) -> None:
        if len(self.legs) > 1:
            self.legs = [leg for leg in self.legs if leg.leg_id != leg_id]

    def _replace_leg(self, leg_id: str, new_leg: Leg) -> None:
        self.legs = [new_leg if leg.leg_id == leg_id else leg for leg in self.legs]

    def _find(self, leg_id: str) -> Leg | None:
        return next((leg for leg in self.legs if leg.leg_id == leg_id), None)

    def set_leg_type(self, leg_id: str, leg_type: str) -> None:
        leg = self._find(leg_id)
        if leg is None:
            return
        if leg_type == "stock":
            if isinstance(leg, StockLeg):
                return
            self._replace_leg(
                leg_id,
                StockLeg(leg_id=leg.leg_id, side=leg.side, qty=leg.qty, entry_price=leg.strike),
            )
            return
        right: Right = "call" if leg_type == "call" else "put"
        if isinstance(leg, StockLeg):
            self._replace_leg(
                leg_id,
                OptionLeg(
                    leg_id=leg.leg_id,
                    side=leg.side,
                    qty=leg.qty,
                    right=right,
                    strike=leg.entry_price,
                ),
            )
            return
        self._replace_leg(leg_id, replace(leg, right=right, premium=TheoreticalPremium()))

    def set_leg_side(self, leg_id: str, side: Side) -> None:
        leg = self._find(leg_id)
        if leg is not None:
            self._replace_leg(leg_id, replace(leg, side=side))

    def set_leg_strike(self, leg_id: str, value: float) -> None:
        leg = self._find(leg_id)
        if leg is None or value is None:
            return
        if isinstance(leg, StockLeg):
            self._replace_leg(leg_id, replace(leg, entry_price=float(value)))
        else:
            self._replace_leg(leg_id, replace(leg, strike=float(value)))

    def set_leg_qty(self, leg_id: str, value: float) -> None:
        leg = self._find(leg_id)
        if leg is None or value is None:
            return
        self._replace_leg(leg_id, replace(leg, qty=max(1.0, round(float(value)))))

    def set_leg_premium(self, leg_id: str, value: float | None) -> None:
        leg = self._find(leg_id)
        if not isinstance(leg, OptionLeg):
            return
        premium = TheoreticalPremium() if value is None else ManualPremium(float(value))
        self._replace_leg(leg_id, replace(leg, premium=premium))

    def reset_premiums(self) -> None:
        self.legs = [
            replace(leg, premium=TheoreticalPremium()) if isinstance(leg, OptionLeg) else leg
            for leg in self.legs
        ]

    def has_manual_premiums(self) -> bool:
        return any(
            isinstance(leg, OptionLeg) and isinstance(leg.premium, ManualPremium)
            for leg in self.legs
        )


@dataclass(frozen=True, slots=True)
class PayoffPoint:
    spot: float
    expiry: float
    today: float
    today_other: float | None
    scenario: float | None
    compare: float | None


@dataclass(frozen=True, slots=True)
class Analytics:
    """Tutti i valori derivati, calcolati in blocco."""

    net_cost: float
    greeks: Greeks
    break_evens: list[float]
    max_profit: float
    max_loss: float
    profit_unbounded: bool
    loss_unbounded: bool
    cost: TradeCost
    payoff: list[PayoffPoint]
    chart_low: float
    chart_high: float
    entry_premiums: dict[str, float]
    other_exercise: ExerciseStyle | None
    scenario: Scenario
    scenario_curve: bool
    prob_profit: float
    comparison_name: str | None


# ---------------------------------------------------------------------------
# Scenario: prezzo, data e volatilità scelti dall'utente
# ---------------------------------------------------------------------------

# Matrice degli scenari: variazioni del prezzo e della IV rispetto a oggi.
MATRIX_PRICE_MOVES = (-0.10, -0.05, -0.025, 0.0, 0.025, 0.05, 0.10)
MATRIX_IV_MOVES = (-0.50, -0.25, 0.0, 0.25, 0.50)


@dataclass(frozen=True, slots=True)
class ScenarioLeg:
    leg_id: str
    entry: float
    value: float
    pl: float


@dataclass(frozen=True, slots=True)
class Scenario:
    """Il P&L in uno scenario, e da dove viene.

    ``pl_today`` è il P&L se si chiudesse ora. Gli effetti sono calcolati in
    sequenza — prima si muove il prezzo, poi passa il tempo, poi cambia la
    volatilità — quindi si sommano esattamente:
    ``pl = pl_today + effect_price + effect_time + effect_vol``.
    """

    price: float
    days: float
    iv: float
    pl_today: float
    pl: float
    effect_price: float
    effect_time: float
    effect_vol: float
    legs: list[ScenarioLeg]
    matrix: list[list[float]]  # matrix[riga IV][colonna prezzo]


def scenario_market_of(state: PositionState) -> MarketParams:
    """Mercato dello scenario: prezzo scelto, giorni avanzati, IV scelta."""
    dte = state.market.days_to_expiry
    return replace(
        state.market,
        spot=state.target,
        days_to_expiry=max(dte - min(state.days_forward, dte), 0.0),
        iv=state.iv_sim,
    )


def compute_scenario(state: PositionState, resolved: list[ResolvedLeg]) -> Scenario:
    now = state.market
    target = scenario_market_of(state)

    def pl(market: MarketParams) -> float:
        return pl_at_market(resolved, market, state.exercise)

    pl_today = pl(now)
    moved = replace(now, spot=target.spot)
    aged = replace(moved, days_to_expiry=target.days_to_expiry)
    pl_moved, pl_aged, pl_final = pl(moved), pl(aged), pl(target)

    legs: list[ScenarioLeg] = []
    for r in resolved:
        value = (
            target.spot
            if isinstance(r.leg, StockLeg)
            else price_option(spec_for_leg(r.leg, target), state.exercise)
        )
        legs.append(
            ScenarioLeg(
                leg_id=r.leg.leg_id,
                entry=r.entry_premium,
                value=value,
                pl=r.signed_qty * (value - r.entry_premium),
            )
        )

    matrix = [
        [
            pl_at_market(
                resolved,
                replace(
                    target,
                    spot=now.spot * (1 + dp),
                    iv=max(now.iv * (1 + dv), 0.01),
                ),
                state.exercise,
                "curve",
            )
            for dp in MATRIX_PRICE_MOVES
        ]
        for dv in MATRIX_IV_MOVES
    ]

    return Scenario(
        price=target.spot,
        days=now.days_to_expiry - target.days_to_expiry,
        iv=target.iv,
        pl_today=pl_today,
        pl=pl_final,
        effect_price=pl_moved - pl_today,
        effect_time=pl_aged - pl_moved,
        effect_vol=pl_final - pl_aged,
        legs=legs,
        matrix=matrix,
    )


def compute(state: PositionState) -> Analytics:
    """Ricalcola tutto ciò che dipende dallo stato.

    Un'unica funzione invece di tante proprietà sparse: così è ovvio quanto
    costa un aggiornamento, e si vede subito se qualcosa viene ricalcolato
    più volte del necessario.
    """
    premium_market = state.entry_market if state.pin_premiums else state.market
    resolved = resolve_legs(state.legs, premium_market, state.exercise)

    bounds = payoff_bounds(resolved)
    bes = break_evens(resolved)

    references = [
        leg.entry_price if isinstance(leg, StockLeg) else leg.strike for leg in state.legs
    ]
    # Ampiezza del grafico: circa tre deviazioni standard del prezzo a
    # scadenza, fra il 10% e il 45% dello spot. Così una scadenza a 9 giorni
    # non viene schiacciata in una striscia, e una a un anno ha spazio.
    spot = state.market.spot
    spread = state.market.iv * math.sqrt(max(state.market.days_to_expiry, 1.0) / 365.0)
    width = min(max(3.0 * spread, 0.10), 0.45)
    low = max(min(spot * (1 - width), min(references) * 0.97), 0.0)
    high = max(spot * (1 + width), max(references) * 1.03)

    # Curva di confronto con lo stile opposto. Usa gli STESSI premi pagati:
    # la distanza fra le due curve è quindi il solo valore dell'esercizio
    # anticipato, non una differenza di costo.
    other_exercise: ExerciseStyle | None = None
    if state.compare_exercise and any(isinstance(leg, OptionLeg) for leg in state.legs):
        other_exercise = "european" if state.exercise == "american" else "american"

    uses_tree = state.exercise == "american" or other_exercise is not None
    steps = 70 if uses_tree else 140
    xs = {low + (high - low) * i / steps for i in range(steps + 1)}
    xs.update(x for x in (*references, *bes, state.market.spot, state.target) if low < x < high)

    # Curva dello scenario: fra N giorni e con la IV dello scenario. Si
    # disegna solo se differisce da «oggi» in almeno una delle due cose.
    scenario_market = scenario_market_of(state)
    scenario_curve = (
        scenario_market.days_to_expiry != state.market.days_to_expiry
        or abs(scenario_market.iv - state.market.iv) > 1e-12
    )

    # Confronto con un'altra posizione: solo il P&L a scadenza, per unità.
    compared: list[ResolvedLeg] | None = None
    if state.comparison is not None:
        other = state.comparison
        compared = resolve_legs(
            other.legs,
            other.entry_market if other.pin_premiums else other.market,
            other.exercise,
        )

    resolution: Resolution = "curve"

    payoff: list[PayoffPoint] = []
    for spot in sorted(xs):
        at_spot = replace(state.market, spot=spot)
        today = pl_at_market(resolved, at_spot, state.exercise, resolution)
        payoff.append(
            PayoffPoint(
                spot=spot,
                expiry=pl_at_expiry(resolved, spot),
                today=today,
                today_other=(
                    pl_at_market(resolved, at_spot, other_exercise, resolution)
                    if other_exercise is not None
                    else None
                ),
                scenario=(
                    pl_at_market(
                        resolved, replace(scenario_market, spot=spot), state.exercise, resolution
                    )
                    if scenario_curve
                    else None
                ),
                compare=pl_at_expiry(compared, spot) if compared is not None else None,
            )
        )

    return Analytics(
        net_cost=net_cost(resolved),
        greeks=position_greeks(resolved, state.market, state.exercise),
        break_evens=bes,
        max_profit=bounds.max_profit,
        max_loss=bounds.max_loss,
        profit_unbounded=bounds.profit_unbounded,
        loss_unbounded=bounds.loss_unbounded,
        cost=trade_cost(resolved, state.sizing),
        payoff=payoff,
        chart_low=low,
        chart_high=high,
        entry_premiums={r.leg.leg_id: r.entry_premium for r in resolved},
        other_exercise=other_exercise,
        scenario=compute_scenario(state, resolved),
        scenario_curve=scenario_curve,
        prob_profit=probability_of_profit(resolved, state.market),
        comparison_name=state.comparison_name if compared is not None else None,
    )


# ---------------------------------------------------------------------------
# Mappa di calore prezzo x tempo
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Heatmap:
    """P&L su una griglia: righe = giorni da oggi, colonne = prezzi."""

    prices: list[float]
    days: list[float]
    values: list[list[float]]  # values[riga][colonna]


HEATMAP_PRICES = 25
HEATMAP_ROWS = 11


def compute_heatmap(state: PositionState, analytics: Analytics) -> Heatmap:
    """P&L della posizione al variare di prezzo e giorni trascorsi.

    Separata da ``compute`` perché costa molto di più (centinaia di prezzi,
    alberi binomiali con le americane): la pagina la chiama solo quando la
    scheda della mappa è aperta.
    """
    premium_market = state.entry_market if state.pin_premiums else state.market
    resolved = resolve_legs(state.legs, premium_market, state.exercise)
    low, high = analytics.chart_low, analytics.chart_high
    prices = [low + (high - low) * i / (HEATMAP_PRICES - 1) for i in range(HEATMAP_PRICES)]
    dte = state.market.days_to_expiry
    days = [dte * j / (HEATMAP_ROWS - 1) for j in range(HEATMAP_ROWS)]
    values = [
        [
            pl_at_expiry(resolved, price)
            if elapsed >= dte
            else pl_at_market(
                resolved,
                replace(state.market, spot=price, days_to_expiry=dte - elapsed),
                state.exercise,
                "curve",
            )
            for price in prices
        ]
        for elapsed in days
    ]
    return Heatmap(prices=prices, days=days, values=values)
