"""Strategie precostruite.

--- COSA FA QUESTO FILE ---
Contiene l'elenco delle strategie del menu (bull call spread, iron condor,
collar…). Ognuna è una RICETTA: dato un prezzo del sottostante, costruisce le
gambe corrispondenti.

Sono solo un punto di partenza: una volta caricata, ogni gamba resta
liberamente modificabile.
"""

from __future__ import annotations

import itertools

# `collections.abc` contiene i tipi "astratti": descrivono un COMPORTAMENTO
# invece di una classe concreta. `Callable` significa "qualcosa che si può
# chiamare come una funzione".
from collections.abc import Callable
from dataclasses import dataclass

# `..pricing` sale di una cartella (da `app` alla radice del pacchetto) e poi
# entra in `pricing`. È la direzione consentita: app dipende da pricing.
from ..pricing import Leg, OptionLeg, Right, Side, StockLeg

_ids = itertools.count(1)


def new_leg_id() -> str:
    """Identificatore univoco per una gamba appena creata."""
    return f"leg-{next(_ids)}"


def _opt(right: Right, side: Side, strike: float, qty: float = 1.0) -> OptionLeg:
    return OptionLeg(leg_id=new_leg_id(), side=side, qty=qty, right=right, strike=strike)


def _shares(side: Side, entry_price: float, qty: float = 1.0) -> StockLeg:
    return StockLeg(leg_id=new_leg_id(), side=side, qty=qty, entry_price=entry_price)


# --- UNA FUNZIONE COME VALORE ----------------------------------------------
# In Python le funzioni sono valori come i numeri: si possono mettere in una
# variabile, in una lista, o — come qui — in un campo di una dataclass.
#
# `Callable[[float], list[Leg]]` si legge: "una funzione che prende un float e
# restituisce una lista di Leg". La prima parentesi quadra elenca i parametri,
# quello dopo la virgola è il tipo restituito.
#
# È ciò che rende questo file un ELENCO DI RICETTE invece di una catena di
# `if`: ogni strategia porta con sé le proprie istruzioni.
@dataclass(frozen=True, slots=True)
class Strategy:
    name: str
    description: str
    build: Callable[[float], list[Leg]]


# --- `lambda`: una funzione senza nome, scritta in una riga ----------------
# `lambda s: [...]` crea una funzione che prende un parametro `s` e
# restituisce quello che segue i due punti. Equivale a:
#
#     def costruisci(s):
#         return [_opt("call", "long", round(s))]
#
# Si usa quando la funzione è così breve che darle un nome sarebbe rumore.
# Limite: può contenere UNA SOLA espressione — niente `if` su più righe,
# niente cicli. Se serve di più, si scrive una `def` vera.
#
# `round(x)` arrotonda all'intero più vicino: gli strike sono numeri tondi.
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
