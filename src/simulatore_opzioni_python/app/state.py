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

--- MUTABILE CONTRO IMMUTABILE ---
Attenzione a una differenza importante rispetto al motore. Là tutte le
dataclass erano `frozen=True`, immutabili. `PositionState` invece è
`@dataclass(slots=True)` SENZA `frozen`: è MUTABILE, cioè `state.ticker = "X"`
funziona.

Perché la differenza? Perché questo oggetto rappresenta qualcosa che per sua
natura cambia — l'utente muove uno slider e lo stato deve seguirlo. Gli oggetti
del motore invece descrivono un calcolo, e congelarli garantisce che nessuno
li alteri a metà.

Regola pratica: immutabile per default, mutabile solo dove il cambiamento è
il senso stesso dell'oggetto.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..pricing import (
    ExerciseStyle,
    Greeks,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    Resolution,
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
    resolve_legs,
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

LegType = Right | str  # "call" | "put" | "stock"


@dataclass(slots=True)
class PositionState:
    """Tutto ciò che l'utente può modificare."""

    ticker: str = "AAPL"
    name: str = "Apple Inc."
    market: MarketParams = INITIAL_MARKET
    entry_market: MarketParams = INITIAL_MARKET
    #: Se True il premio d'ingresso resta congelato allo snapshot.
    pin_premiums: bool = True
    exercise: ExerciseStyle = "european"
    # --- `field(default_factory=...)`: default che vanno costruiti ---------
    # Per numeri e stringhe basta `campo: int = 0`. Per LISTE e DIZIONARI no:
    # scrivendo `legs: list = []` quella singola lista verrebbe creata una
    # volta sola, alla definizione della classe, e CONDIVISA da tutte le
    # istanze. Due posizioni diverse finirebbero per modificarsi a vicenda.
    #
    # È un errore così comune che Python lo vieta esplicitamente nelle
    # dataclass. La soluzione è `default_factory`: si passa una FUNZIONE, che
    # viene chiamata a ogni creazione per produrre un valore nuovo e separato.
    legs: list[Leg] = field(default_factory=lambda: STRATEGIES["single"].build(100.0))
    strategy_key: str = "single"
    #: Prezzo-target per lo scenario a scadenza.
    target: float = 110.0
    #: IV indipendente del simulatore di vol crush (decimale).
    iv_sim: float = 0.30
    # default_factory anche se Sizing è immutabile: un'istanza creata nella
    # definizione della classe sarebbe condivisa da tutte le posizioni.
    sizing: Sizing = field(default_factory=Sizing)
    currency: str = "$"

    # -- mercato ----------------------------------------------------------

    # --- METODI CHE MODIFICANO L'OGGETTO -----------------------------------
    # `self` è l'oggetto su cui il metodo è stato chiamato (vedi types.py).
    # Qui, a differenza del motore, `self.market = ...` è LECITO perché la
    # classe non è `frozen`.
    #
    # Nota però che `self.market` È un oggetto frozen: per cambiarlo si usa
    # comunque `replace`. Si sostituisce l'intero oggetto, non un suo campo.
    def set_market(self, **changes: float) -> None:
        self.market = replace(self.market, **changes)
        if "iv" in changes:
            # La IV simulata segue quella principale finché l'utente non la
            # muove per conto suo.
            self.iv_sim = changes["iv"]
        if not self.pin_premiums:
            # Senza pin, il mercato d'ingresso insegue quello corrente.
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
        # Caricare una strategia equivale ad aprire la posizione adesso.
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
            # Lo strike diventa prezzo di carico: conservare il numero che
            # l'utente ha già digitato è meno sorprendente che azzerarlo.
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
        # --- `any()` e `all()` -------------------------------------------
        # `any(sequenza)` è vero se ALMENO UN elemento è vero.
        # `all(sequenza)` è vero se lo sono TUTTI.
        # Entrambe si fermano appena la risposta è certa: `any` al primo vero,
        # `all` al primo falso. Con un generatore (senza parentesi quadre)
        # questo significa che il resto non viene nemmeno calcolato.
        return any(
            isinstance(leg, OptionLeg) and isinstance(leg.premium, ManualPremium)
            for leg in self.legs
        )


@dataclass(frozen=True, slots=True)
class PayoffPoint:
    spot: float
    expiry: float
    today: float
    today_sim: float


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
    scenario_pl: float
    value_now_current_iv: float
    value_now_sim_iv: float
    vol_crush_effect: float
    entry_premiums: dict[str, float]
    sim_iv_differs: bool


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
    low = max(min(state.market.spot, *references) * 0.55, 0.0)
    high = max(state.market.spot, *references) * 1.45

    # Meno punti per le americane: ogni punto costa un albero. La forma resta
    # liscia perché i punti notevoli sono aggiunti esplicitamente alla griglia.
    steps = 70 if state.exercise == "american" else 140
    xs = {low + (high - low) * i / steps for i in range(steps + 1)}
    xs.update(x for x in (*references, *bes, state.market.spot, state.target) if low < x < high)

    sim_iv_differs = abs(state.iv_sim - state.market.iv) > 1e-12
    # L'annotazione serve: senza, mypy inferisce `str` e la costante non è più
    # accettata dove il motore vuole un Literal["full", "curve"].
    resolution: Resolution = "curve"

    payoff: list[PayoffPoint] = []
    for spot in sorted(xs):
        at_spot = replace(state.market, spot=spot)
        today = pl_at_market(resolved, at_spot, state.exercise, resolution)
        if sim_iv_differs:
            at_sim_iv = replace(at_spot, iv=state.iv_sim)
            today_sim = pl_at_market(resolved, at_sim_iv, state.exercise, resolution)
        else:
            today_sim = today
        payoff.append(
            PayoffPoint(
                spot=spot,
                expiry=pl_at_expiry(resolved, spot),
                today=today,
                today_sim=today_sim,
            )
        )

    value_now = pl_at_market(resolved, state.market, state.exercise)
    value_now_sim = pl_at_market(resolved, replace(state.market, iv=state.iv_sim), state.exercise)

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
        scenario_pl=pl_at_expiry(resolved, state.target),
        value_now_current_iv=value_now,
        value_now_sim_iv=value_now_sim,
        vol_crush_effect=value_now_sim - value_now,
        entry_premiums={r.leg.leg_id: r.entry_premium for r in resolved},
        sim_iv_differs=sim_iv_differs,
    )
