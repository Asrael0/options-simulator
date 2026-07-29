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

import math
from dataclasses import dataclass
from typing import Literal

from .greeks import price_option
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
)

# Tolleranze: due numeri decimali non sono quasi mai esattamente uguali, per
# via degli arrotondamenti binari. Si confrontano "a meno di" una soglia.
_TOL = 1e-9  # notazione scientifica: 1e-9 = 0.000000001
_DEDUPE_TOL = 1e-7


# ---------------------------------------------------------------------------
# Risoluzione dei premi d'ingresso
# ---------------------------------------------------------------------------


def leg_entry_premium(leg: Leg, entry_market: MarketParams, exercise: ExerciseStyle) -> float:
    """Premio d'ingresso di una gamba, per unità di sottostante."""
    # --- `match` / `case`: il pattern matching strutturale ------------------
    # Introdotto in Python 3.10. Somiglia allo `switch` di altri linguaggi, ma
    # fa molto di più: non confronta solo valori, riconosce la FORMA dei dati.
    #
    # Si legge: "guarda `leg`; se ha la forma del primo caso, esegui quel ramo".
    # I casi si provano dall'alto in basso e si ferma al primo che combacia,
    # quindi l'ORDINE conta: dal più specifico al più generico.
    #
    # `case StockLeg(entry_price=price):` fa due cose insieme: verifica che sia
    # una `StockLeg` E cattura il campo `entry_price` in una nuova variabile
    # `price`. Questa è la "destrutturazione", ed è ciò che rende `match`
    # superiore a una catena di `isinstance`.
    #
    # Bonus: mypy capisce il match e restringe i tipi ramo per ramo, quindi sa
    # che nel terzo caso `leg` è certamente una OptionLeg.
    match leg:
        case StockLeg(entry_price=price):
            return price
        # I pattern si annidano: qui si chiede una OptionLeg il cui campo
        # `premium` sia a sua volta un ManualPremium, catturandone il valore.
        case OptionLeg(premium=ManualPremium(value=value)):
            return value
        # Caso generico: una OptionLeg qualsiasi (premio teorico).
        case OptionLeg():
            return price_option(spec_for_leg(leg, entry_market), exercise, "full")


def resolve_legs(
    legs: list[Leg], entry_market: MarketParams, exercise: ExerciseStyle
) -> list[ResolvedLeg]:
    """Congela i premi d'ingresso e applica il segno della posizione.

    Da qui in poi il motore non riprezza mai il costo di carico.
    """
    # --- LIST COMPREHENSION ------------------------------------------------
    # È il modo idiomatico di costruire una lista trasformandone un'altra.
    # Si legge da dentro a fuori:  [ COSA_PRODURRE for OGNI_ELEMENTO in DOVE ]
    #
    # Equivale a:
    #     risultato = []
    #     for leg in legs:
    #         risultato.append(ResolvedLeg(...))
    #     return risultato
    #
    # Più corta, più veloce, e dichiara subito che si sta costruendo una lista.
    # Si può aggiungere un filtro in fondo: [x for x in lista if x > 0].
    return [
        ResolvedLeg(
            leg=leg,
            entry_premium=leg_entry_premium(leg, entry_market, exercise),
            # Operatore ternario: il segno dipende dal lato della posizione.
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
        # `StockLeg()` senza argomenti: verifica solo il tipo, non cattura nulla.
        case StockLeg():
            return final_spot
        # `right="call"` verifica che quel campo valga esattamente "call".
        case OptionLeg(right="call", strike=strike):
            return max(final_spot - strike, 0.0)
        # Se non è una call, è per forza una put: `Right` ammette solo due
        # valori, quindi questo caso è esaustivo e non serve un `case _`.
        case OptionLeg(strike=strike):
            return max(strike - final_spot, 0.0)


def pl_at_expiry(legs: list[ResolvedLeg], final_spot: float) -> float:
    """P&L complessivo a scadenza per un prezzo finale del sottostante."""
    # --- `sum()` CON UN GENERATORE -----------------------------------------
    # `sum(...)` somma una sequenza di numeri.
    # Quello che c'è dentro somiglia a una list comprehension ma SENZA le
    # parentesi quadre: è un GENERATORE. Differenza pratica: la comprehension
    # costruisce l'intera lista in memoria, il generatore produce un valore alla
    # volta. Sommando non serve tenerli tutti, quindi il generatore è la scelta
    # giusta — soprattutto perché questa funzione viene chiamata centinaia di
    # volte per disegnare una curva.
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
            # `as opt` dà un nome al valore che ha combaciato: serve perché
            # dopo lo si passa a una funzione che vuole una OptionLeg, e mypy
            # deve sapere che è di quel tipo.
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
                # Un `if` senza `else`: se la condizione è falsa non succede
                # nulla e si passa all'elemento successivo.
                if final_spot >= strike:
                    slope += r.signed_qty
            case OptionLeg(strike=strike):
                if final_spot < strike:
                    slope -= r.signed_qty
    return slope


def _sorted_strikes(legs: list[ResolvedLeg]) -> list[float]:
    """Strike distinti e ordinati delle sole gambe opzione."""
    # --- SET COMPREHENSION -------------------------------------------------
    # Come la list comprehension, ma con le graffe: costruisce un SET.
    # Un set è una collezione SENZA duplicati e senza ordine. Perfetto qui:
    # due gambe sullo stesso strike devono contare per un vertice solo.
    #
    # L'`if` in fondo filtra: entrano solo gli elementi per cui è vero.
    # `math.isfinite(x)` esclude infinito e NaN ("not a number"), che possono
    # nascere da input malformati.
    strikes = {
        r.leg.strike
        for r in legs
        if isinstance(r.leg, OptionLeg) and math.isfinite(r.leg.strike) and r.leg.strike > 0.0
    }
    # `sorted()` prende qualunque collezione e restituisce una LISTA ordinata.
    # Diverso da `.sort()`, che ordina sul posto e funziona solo sulle liste.
    return sorted(strikes)


def _dedupe(values: list[float]) -> list[float]:
    """Toglie i doppioni da una lista ordinata, a meno della tolleranza."""
    # `out: list[float] = []` crea una lista vuota, annotata col tipo che
    # conterrà. L'annotazione qui serve a mypy: da una lista vuota non potrebbe
    # indovinare cosa ci finirà dentro.
    out: list[float] = []
    for v in sorted(values):
        # `not out` è vero quando la lista è VUOTA: in Python una collezione
        # vuota conta come "falso", una piena come "vero". Idiomatico, e
        # preferito a `len(out) == 0`.
        # `out[-1]` è l'ultimo elemento: gli indici negativi contano dalla fine.
        if not out or abs(v - out[-1]) > _DEDUPE_TOL:
            # `.append(x)` aggiunge in fondo alla lista.
            out.append(v)
    return out


def break_evens(legs: list[ResolvedLeg]) -> list[float]:
    """Break-even esatti: i prezzi a cui il P&L a scadenza vale zero.

    Il dominio [0, +inf) viene spezzato sugli strike. Su ogni segmento il P&L
    è una retta: se la pendenza è non nulla la radice è ``a - P(a)/m``, e si
    accetta solo se cade dentro il segmento. Un segmento a pendenza nulla e
    valore nullo è un intero tratto di break-even: se ne riportano gli estremi.
    """
    # --- SPACCHETTAMENTO CON `*` -------------------------------------------
    # `[0.0, *lista]` crea una nuova lista che comincia con 0.0 e prosegue con
    # tutti gli elementi di `lista`. L'asterisco "srotola" la sequenza dentro
    # la nuova. Senza, si otterrebbe una lista con dentro una lista.
    edges = [0.0, *_sorted_strikes(legs)]
    roots: list[float] = []

    # --- `enumerate`: scorrere avendo anche l'indice ------------------------
    # `for i, a in enumerate(lista)` dà a ogni giro la posizione e il valore.
    # L'alternativa `for i in range(len(lista))` con `lista[i]` funziona ma è
    # considerata poco pythonica.
    for i, a in enumerate(edges):
        # `math.inf` è l'infinito positivo: un vero valore numerico con cui si
        # può fare aritmetica e confronti. L'ultimo segmento non ha fine.
        b = edges[i + 1] if i + 1 < len(edges) else math.inf
        pa = pl_at_expiry(legs, a)
        slope = _slope_at_expiry(legs, a)

        if abs(slope) > _TOL:
            # Radice di una retta: x tale che P(x) = 0.
            root = a - pa / slope
            # `math.isinf(b)` è vero se b è infinito: in quel caso il segmento
            # si estende all'infinito e il limite destro non va controllato.
            inside = root >= a - _TOL and (math.isinf(b) or root <= b + _TOL)
            if inside and math.isfinite(root):
                roots.append(max(root, 0.0))
        elif abs(pa) <= _TOL:
            # Segmento piatto esattamente sullo zero: tutto il tratto è
            # break-even, quindi se ne riportano gli estremi.
            roots.append(a)
            if math.isfinite(b):
                roots.append(b)

    # Filtro con comprehension: si tengono solo i valori non negativi, perché
    # il prezzo di un titolo non scende sotto zero.
    return _dedupe([r for r in roots if r >= 0.0])


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

    # `strikes[-1] if strikes else 0.0`: se la lista è vuota (nessuna opzione,
    # solo azioni) si usa 0.0. Anche qui una lista vuota vale "falso".
    right_ray_from = strikes[-1] if strikes else 0.0
    right_slope = _slope_at_expiry(legs, right_ray_from)

    profit_unbounded = right_slope > _TOL
    loss_unbounded = right_slope < -_TOL

    return PayoffBounds(
        # `max(lista)` e `min(lista)` funzionano anche su una collezione, non
        # solo su due valori come visto in black_scholes.py.
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
    #: Premio dell'opzione o prezzo di carico dell'azione.
    unit_price: float
    #: Costo di un singolo contratto o lotto.
    per_contract: float
    #: Unità di sottostante totali mosse dalla gamba.
    units: float
    outflow: float
    inflow: float
    #: Valore assoluto del flusso, senza segno.
    gross: float


@dataclass(frozen=True, slots=True)
class TradeCost:
    """Il costo dell'intera operazione."""

    legs: list[LegCost]
    total_outflow: float
    total_inflow: float
    #: Positivo = debito netto, negativo = credito netto.
    net: float


def trade_cost(legs: list[ResolvedLeg], sizing: Sizing) -> TradeCost:
    """Traduce i prezzi per unità in esborso reale.

    È l'unico punto del motore dove moltiplicatore di contratto e pacchetti
    entrano nel calcolo.
    """
    detail: list[LegCost] = []
    for r in legs:
        # `abs()` toglie il segno: qui serve la quantità, non la direzione.
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
                # Una gamba comprata è un'uscita, una venduta un'incasso: solo
                # uno dei due campi è diverso da zero.
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

# Un alias di tipo può essere definito ovunque nel file, non solo in types.py:
# questo vive qui perché lo usa solo la funzione qui sotto.
MoneynessCode = Literal["ITM", "ATM", "OTM", "STOCK"]

_ATM_BAND = 0.015


def moneyness(leg: Leg, spot: float) -> MoneynessCode:
    """Classificazione della gamba rispetto al prezzo corrente."""
    match leg:
        case StockLeg():
            return "STOCK"
        case OptionLeg(strike=strike, right=right):
            # Distanza RELATIVA: `|spot - strike| / strike`. Usare la distanza
            # assoluta non andrebbe bene, perché 2 $ su un titolo da 20 $ è
            # tutt'altra cosa che 2 $ su un titolo da 2000 $.
            if abs(spot - strike) / strike < _ATM_BAND:
                return "ATM"
            itm = spot > strike if right == "call" else spot < strike
            return "ITM" if itm else "OTM"
