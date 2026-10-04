"""P&L multi-gamba: payoff a scadenza, valore corrente, break-even, estremi.

--- COSA FA QUESTO FILE ---
Fin qui si è prezzata UNA opzione alla volta. Qui si passa alla POSIZIONE
intera: più gambe insieme, con i loro segni e le loro quantità.

Risponde a quattro domande:
  - quanto guadagno o perdo se a scadenza il titolo vale X?  (`pl_at_expiry`)
  - a che prezzo vado in pari?                                (`break_evens`)
  - qual è il massimo che posso guadagnare o perdere?         (`payoff_bounds`)
  - quanti soldi veri mi servono per aprirla?                 (`trade_cost`)

SCELTA STRUTTURALE — il premio d'ingresso è un INPUT, mai un ricalcolo.

Nel prototipo originale il premio veniva riprezzato ai parametri correnti a
ogni accesso: spostando lo slider dello spot cambiava anche il costo "già
pagato", quindi la curva "valore oggi" passava sempre per lo zero al prezzo
spot e i break-even scivolavano insieme allo slider. Qui ``resolve_legs()``
risolve i premi UNA volta contro un ``MarketParams`` esplicito. Passando lo
snapshot d'ingresso si ottiene il comportamento corretto; passando i parametri
correnti si riproduce il prototipo. La decisione sta fuori dal motore.

BREAK-EVEN ANALITICI — il payoff a scadenza è lineare a tratti, con nodi solo
sugli strike. I break-even si risolvono in forma chiusa segmento per segmento,
non per campionamento: il P&L al break-even è esattamente 0, non "0 entro
l'errore di griglia".
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Literal

from .greeks import price_option
from .normal import norm_cdf
from .types import (
    ExerciseStyle,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    Resolution,
    ResolvedLeg,
    Sizing,
    StockLeg,
    spec_for_leg,
    years_from_days,
)

_TOL = 1e-9
_DEDUPE_TOL = 1e-7


# ---------------------------------------------------------------------------
# Risoluzione dei premi d'ingresso
# ---------------------------------------------------------------------------


def leg_entry_premium(leg: Leg, entry_market: MarketParams, exercise: ExerciseStyle) -> float:
    """Premio d'ingresso di una gamba, per unità di sottostante."""
    match leg:
        case StockLeg(entry_price=price):
            return price
        case OptionLeg(premium=ManualPremium(value=value)):
            return value
        case OptionLeg():
            return price_option(spec_for_leg(leg, entry_market), exercise, "full")


def resolve_legs(
    legs: list[Leg], entry_market: MarketParams, exercise: ExerciseStyle
) -> list[ResolvedLeg]:
    """Congela i premi d'ingresso e applica il segno della posizione.

    Da qui in poi il motore non riprezza mai il costo di carico.
    """
    return [
        ResolvedLeg(
            leg=leg,
            entry_premium=leg_entry_premium(leg, entry_market, exercise),
            signed_qty=leg.qty if leg.side == "long" else -leg.qty,
        )
        for leg in legs
    ]


# ---------------------------------------------------------------------------
# Payoff a scadenza
# ---------------------------------------------------------------------------


def intrinsic_at_expiry(leg: Leg, final_spot: float) -> float:
    """Valore lordo di una gamba a scadenza, per unità di sottostante.

    Per un'opzione è il valore intrinseco; per l'azione è il prezzo stesso.
    """
    match leg:
        case StockLeg():
            return final_spot
        case OptionLeg(right="call", strike=strike):
            return max(final_spot - strike, 0.0)
        case OptionLeg(strike=strike):
            return max(strike - final_spot, 0.0)


def pl_at_expiry(legs: list[ResolvedLeg], final_spot: float) -> float:
    """P&L complessivo a scadenza per un prezzo finale del sottostante."""
    return sum(
        r.signed_qty * (intrinsic_at_expiry(r.leg, final_spot) - r.entry_premium) for r in legs
    )


def pl_at_market(
    legs: list[ResolvedLeg],
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
) -> float:
    """P&L al mercato indicato: valore corrente meno costo d'ingresso.

    È la curva "valore oggi" del diagramma di payoff.
    """
    total = 0.0
    for r in legs:
        match r.leg:
            case StockLeg():
                value = market.spot
            case OptionLeg() as opt:
                value = price_option(spec_for_leg(opt, market), exercise, resolution)
        total += r.signed_qty * (value - r.entry_premium)
    return total


def _slope_at_expiry(legs: list[ResolvedLeg], final_spot: float) -> float:
    """Derivata destra del P&L a scadenza rispetto al prezzo del sottostante.

    È costante su ogni segmento fra strike consecutivi, quindi valutarla
    nell'estremo sinistro dà la pendenza dell'intero segmento.
    """
    slope = 0.0
    for r in legs:
        match r.leg:
            case StockLeg():
                slope += r.signed_qty
            case OptionLeg(right="call", strike=strike):
                if final_spot >= strike:
                    slope += r.signed_qty
            case OptionLeg(strike=strike):
                if final_spot < strike:
                    slope -= r.signed_qty
    return slope


def _sorted_strikes(legs: list[ResolvedLeg]) -> list[float]:
    """Strike distinti e ordinati delle sole gambe opzione."""
    strikes = {
        r.leg.strike
        for r in legs
        if isinstance(r.leg, OptionLeg) and math.isfinite(r.leg.strike) and r.leg.strike > 0.0
    }
    return sorted(strikes)


def _dedupe(values: list[float]) -> list[float]:
    """Toglie i doppioni da una lista ordinata, a meno della tolleranza."""
    out: list[float] = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > _DEDUPE_TOL:
            out.append(v)
    return out


def break_evens(legs: list[ResolvedLeg]) -> list[float]:
    """Break-even esatti: i prezzi a cui il P&L a scadenza vale zero.

    Il dominio [0, +inf) viene spezzato sugli strike. Su ogni segmento il P&L
    è una retta: se la pendenza è non nulla la radice è ``a - P(a)/m``, e si
    accetta solo se cade dentro il segmento. Un segmento a pendenza nulla e
    valore nullo è un intero tratto di break-even: se ne riportano gli estremi.
    """
    edges = [0.0, *_sorted_strikes(legs)]
    roots: list[float] = []

    for i, a in enumerate(edges):
        b = edges[i + 1] if i + 1 < len(edges) else math.inf
        pa = pl_at_expiry(legs, a)
        slope = _slope_at_expiry(legs, a)

        if abs(slope) > _TOL:
            root = a - pa / slope
            inside = root >= a - _TOL and (math.isinf(b) or root <= b + _TOL)
            if inside and math.isfinite(root):
                roots.append(max(root, 0.0))
        elif abs(pa) <= _TOL:
            roots.append(a)
            if math.isfinite(b):
                roots.append(b)

    return _dedupe([r for r in roots if r >= 0.0])


def _prob_below(price: float, market: MarketParams) -> float:
    """P(S_T < price) sotto la distribuzione lognormale neutrale al rischio."""
    if price <= 0.0:
        return 0.0
    if math.isinf(price):
        return 1.0
    t = years_from_days(market.days_to_expiry)
    sigma = market.iv
    if t <= 0.0 or sigma <= 0.0:
        return 1.0 if market.spot < price else 0.0
    drift = (market.risk_free_rate - market.dividend_yield - 0.5 * sigma * sigma) * t
    z = (math.log(price / market.spot) - drift) / (sigma * math.sqrt(t))
    return float(norm_cdf(z))


def probability_of_profit(legs: list[ResolvedLeg], market: MarketParams) -> float:
    """Probabilità che a scadenza la posizione chiuda in profitto.

    Il prezzo finale del sottostante segue la lognormale di Black-Scholes
    (neutrale al rischio, IV globale). I break-even dividono l'asse dei prezzi
    in intervalli; su ognuno il segno del P&L è costante, quindi basta
    guardarlo in un punto interno e sommare la probabilità degli intervalli
    in guadagno. Nessuna simulazione: il risultato è esatto per il modello.
    """
    edges = [0.0, *break_evens(legs), math.inf]
    total = 0.0
    for a, b in itertools.pairwise(edges):
        if b - a <= _DEDUPE_TOL:
            continue
        probe = a * 2.0 + 1.0 if math.isinf(b) else (a + b) / 2.0
        if pl_at_expiry(legs, probe) > _TOL:
            total += _prob_below(b, market) - _prob_below(a, market)
    return min(max(total, 0.0), 1.0)


@dataclass(frozen=True, slots=True)
class PayoffBounds:
    """Estremi del payoff. ``math.inf`` significa illimitato."""

    max_profit: float
    max_loss: float
    profit_unbounded: bool
    loss_unbounded: bool


def payoff_bounds(legs: list[ResolvedLeg]) -> PayoffBounds:
    """Estremi VERI del payoff, non "sul range del grafico".

    Il payoff a tratti raggiunge i suoi estremi finiti solo nei vertici (S = 0
    e gli strike); la pendenza del raggio destro dice se profitto o perdita
    sono illimitati. Il prototipo riportava il massimo campionato sul range
    visibile, facendo apparire finita la perdita di una call venduta nuda.
    """
    strikes = _sorted_strikes(legs)
    vertices = [0.0, *strikes]
    values = [pl_at_expiry(legs, s) for s in vertices]

    right_ray_from = strikes[-1] if strikes else 0.0
    right_slope = _slope_at_expiry(legs, right_ray_from)

    profit_unbounded = right_slope > _TOL
    loss_unbounded = right_slope < -_TOL

    return PayoffBounds(
        max_profit=math.inf if profit_unbounded else max(values),
        max_loss=-math.inf if loss_unbounded else min(values),
        profit_unbounded=profit_unbounded,
        loss_unbounded=loss_unbounded,
    )


# ---------------------------------------------------------------------------
# Costo dell'operazione
# ---------------------------------------------------------------------------


def net_cost(legs: list[ResolvedLeg]) -> float:
    """Costo netto per unità di sottostante.

    Positivo = debito (esborso), negativo = credito (incasso).
    """
    return sum(r.signed_qty * r.entry_premium for r in legs)


@dataclass(frozen=True, slots=True)
class LegCost:
    """Il costo di una singola gamba, scomposto."""

    resolved: ResolvedLeg
    unit_price: float
    per_contract: float
    units: float
    outflow: float
    inflow: float
    gross: float


@dataclass(frozen=True, slots=True)
class TradeCost:
    """Il costo dell'intera operazione."""

    legs: list[LegCost]
    total_outflow: float
    total_inflow: float
    net: float


def trade_cost(legs: list[ResolvedLeg], sizing: Sizing) -> TradeCost:
    """Traduce i prezzi per unità in esborso reale.

    È l'unico punto del motore dove moltiplicatore di contratto e pacchetti
    entrano nel calcolo.
    """
    detail: list[LegCost] = []
    for r in legs:
        qty = abs(r.signed_qty)
        units = sizing.contract_multiplier * qty * sizing.packages
        gross = r.entry_premium * units
        is_long = r.signed_qty >= 0
        detail.append(
            LegCost(
                resolved=r,
                unit_price=r.entry_premium,
                per_contract=r.entry_premium * sizing.contract_multiplier,
                units=units,
                outflow=gross if is_long else 0.0,
                inflow=0.0 if is_long else gross,
                gross=gross,
            )
        )

    total_outflow = sum(c.outflow for c in detail)
    total_inflow = sum(c.inflow for c in detail)
    return TradeCost(
        legs=detail,
        total_outflow=total_outflow,
        total_inflow=total_inflow,
        net=total_outflow - total_inflow,
    )


# ---------------------------------------------------------------------------
# Moneyness
# ---------------------------------------------------------------------------

MoneynessCode = Literal["ITM", "ATM", "OTM", "STOCK"]

_ATM_BAND = 0.015


def moneyness(leg: Leg, spot: float) -> MoneynessCode:
    """Classificazione della gamba rispetto al prezzo corrente."""
    match leg:
        case StockLeg():
            return "STOCK"
        case OptionLeg(strike=strike, right=right):
            if abs(spot - strike) / strike < _ATM_BAND:
                return "ATM"
            itm = spot > strike if right == "call" else spot < strike
            return "ITM" if itm else "OTM"
