"""Prebuilt strategies.

The strategies in the menu (bull call spread, iron condor, collar…). Each one is
a RECIPE: given the underlying price, it builds the matching legs.

They are only a starting point: once loaded, every leg can be edited freely.
Names and descriptions are in Italian and go through tr() when displayed.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass

from ..pricing import Leg, OptionLeg, Right, Side, StockLeg

_ids = itertools.count(1)


def new_leg_id() -> str:
    """Unique identifier for a newly created leg."""
    return f"leg-{next(_ids)}"


def _opt(right: Right, side: Side, strike: float, qty: float = 1.0) -> OptionLeg:
    return OptionLeg(leg_id=new_leg_id(), side=side, qty=qty, right=right, strike=strike)


def _shares(side: Side, entry_price: float, qty: float = 1.0) -> StockLeg:
    return StockLeg(leg_id=new_leg_id(), side=side, qty=qty, entry_price=entry_price)


@dataclass(frozen=True, slots=True)
class Strategy:
    name: str
    description: str
    build: Callable[[float], list[Leg]]


# Position built by hand or from the real chain: it matches no recipe, so it
# is not in STRATEGIES.
CUSTOM_STRATEGY = "custom"
CUSTOM_STRATEGY_NAME = "Personalizzata"
CUSTOM_STRATEGY_DESCRIPTION = (
    "Gambe scelte da te (o caricate dalle opzioni reali). Scegli una strategia "
    "dall'elenco per ripartire da una ricetta."
)

STRATEGIES: dict[str, Strategy] = {
    "single": Strategy(
        name="Singola opzione",
        description="Una sola gamba. Il punto di partenza per capire le greche.",
        build=lambda s: [_opt("call", "long", round(s))],
    ),
    "bull_call_spread": Strategy(
        name="Bull Call Spread",
        description=(
            "Compri una call ATM e ne vendi una OTM più alta. Rialzista, "
            "rischio e profitto limitati."
        ),
        build=lambda s: [_opt("call", "long", round(s)), _opt("call", "short", round(s * 1.1))],
    ),
    "bear_put_spread": Strategy(
        name="Bear Put Spread",
        description=(
            "Compri una put ATM e ne vendi una OTM più bassa. Ribassista, "
            "rischio e profitto limitati."
        ),
        build=lambda s: [_opt("put", "long", round(s)), _opt("put", "short", round(s * 0.9))],
    ),
    "long_straddle": Strategy(
        name="Long Straddle",
        description=(
            "Compri call e put sullo stesso strike. Scommetti su un grande "
            "movimento, in qualsiasi direzione."
        ),
        build=lambda s: [_opt("call", "long", round(s)), _opt("put", "long", round(s))],
    ),
    "long_strangle": Strategy(
        name="Long Strangle",
        description=(
            "Compri call OTM e put OTM. Come lo straddle ma più economico; "
            "serve un movimento più ampio."
        ),
        build=lambda s: [
            _opt("call", "long", round(s * 1.1)),
            _opt("put", "long", round(s * 0.9)),
        ],
    ),
    "iron_condor": Strategy(
        name="Iron Condor",
        description=(
            "Vendi uno strangle interno e compri ali esterne. Guadagni se il "
            "sottostante resta nel range."
        ),
        build=lambda s: [
            _opt("put", "long", round(s * 0.85)),
            _opt("put", "short", round(s * 0.95)),
            _opt("call", "short", round(s * 1.05)),
            _opt("call", "long", round(s * 1.15)),
        ],
    ),
    "covered_call": Strategy(
        name="Covered Call (con azione)",
        description=(
            "Possiedi 100 azioni e vendi una call OTM: incassi il premio in "
            "cambio di un tetto al guadagno. Reddito su una posizione che già detieni."
        ),
        build=lambda s: [_shares("long", round(s)), _opt("call", "short", round(s * 1.1))],
    ),
    "protective_put": Strategy(
        name="Protective Put (con azione)",
        description=(
            "Possiedi 100 azioni e compri una put: assicuri la posizione contro "
            "i ribassi pagando un premio. È un'assicurazione."
        ),
        build=lambda s: [_shares("long", round(s)), _opt("put", "long", round(s * 0.9))],
    ),
    "collar": Strategy(
        name="Collar (con azione)",
        description=(
            "Possiedi 100 azioni, compri una put protettiva e finanzi la "
            "protezione vendendo una call OTM. Limiti sia perdite sia guadagni."
        ),
        build=lambda s: [
            _shares("long", round(s)),
            _opt("put", "long", round(s * 0.9)),
            _opt("call", "short", round(s * 1.1)),
        ],
    ),
    "risk_reversal": Strategy(
        name="Risk Reversal",
        description=(
            "Vendi una put OTM e compri una call OTM, senza azione: esposizione "
            "rialzista sintetica a basso costo."
        ),
        build=lambda s: [
            _opt("put", "short", round(s * 0.9)),
            _opt("call", "long", round(s * 1.1)),
        ],
    ),
    "synthetic_covered_call": Strategy(
        name="Covered Call (sintetica)",
        description=(
            "Short put singola: stesso profilo di rischio del possedere l'azione "
            "e vendere una call, ma senza detenere il titolo."
        ),
        build=lambda s: [_opt("put", "short", round(s))],
    ),
}
