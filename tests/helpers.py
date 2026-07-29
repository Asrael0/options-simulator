"""Costruttori compatti per i test del motore.

--- COSA FA QUESTO FILE ---
Non è un test: è una cassetta degli attrezzi PER i test. Creare un `OptionSpec`
richiede sette argomenti; nei test se ne cambia uno solo alla volta. Queste
funzioni permettono di scrivere `spec(strike=110)` intendendo "tutto come al
solito, ma con strike 110".

Il file NON si chiama `test_qualcosa.py`, quindi pytest non prova a eseguirlo
come suite: lo tratta come un normale modulo da importare.

I parametri base sono quelli della tabella di riferimento:
S = 100, K = 100, T = 30 giorni, r = 4%, IV = 30%, nessun dividendo.
"""

from __future__ import annotations

# `itertools` contiene strumenti per lavorare con le sequenze.
import itertools
from dataclasses import replace

# `Any` significa "un tipo qualsiasi": disattiva il controllo su quel valore.
# Va usato con parsimonia — qui è inevitabile, perché `**overrides` può
# ricevere campi di tipi diversi.
from typing import Any

from simulatore_opzioni_python.pricing import (
    ManualPremium,
    MarketParams,
    OptionLeg,
    OptionSpec,
    Right,
    Side,
    StockLeg,
)

BASE_MARKET = MarketParams(
    spot=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    dividend_yield=0.0,
)

BASE_SPEC = OptionSpec(
    spot=100.0,
    strike=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    right="call",
    dividend_yield=0.0,
)

# --- `itertools.count`: un contatore infinito ------------------------------
# Produce 1, 2, 3, ... senza fine. Non calcola tutti i numeri: ne genera uno
# alla volta, su richiesta. È un "iteratore pigro".
_ids = itertools.count(1)


# --- `**overrides`: accettare un numero variabile di argomenti a nome -------
# Nella FIRMA di una funzione, `**nome` raccoglie in un dizionario tutti gli
# argomenti passati per nome che non corrispondono a parametri dichiarati.
#
#   market(spot=120, iv=0.5)  ->  overrides = {"spot": 120, "iv": 0.5}
#
# Nella CHIAMATA, lo stesso `**` fa l'opposto: srotola un dizionario in
# argomenti a nome. `replace(BASE_MARKET, **overrides)` equivale a scrivere
# `replace(BASE_MARKET, spot=120, iv=0.5)`.
#
# Stessa sintassi, due direzioni opposte a seconda di dove si trova. Esiste
# anche `*args` con un asterisco solo, che fa lo stesso con gli argomenti
# posizionali raccogliendoli in una tupla.
def market(**overrides: Any) -> MarketParams:
    """Parametri di mercato standard, con le modifiche richieste."""
    # `replace` è la funzione vista in binomial.py: copia l'oggetto immutabile
    # cambiando solo i campi indicati.
    return replace(BASE_MARKET, **overrides)


def spec(**overrides: Any) -> OptionSpec:
    """Specifica standard di un'opzione, con le modifiche richieste."""
    return replace(BASE_SPEC, **overrides)


def _next_id() -> str:
    """Identificatore progressivo per una gamba di test."""
    # `next(iteratore)` chiede il prossimo valore. Su `itertools.count` non
    # finisce mai. La f-string (vedi formatting.py) costruisce "leg-1", "leg-2"…
    return f"leg-{next(_ids)}"


def option(
    right: Right,
    side: Side,
    strike: float,
    qty: float = 1.0,
    iv_override: float | None = None,
) -> OptionLeg:
    """Una gamba opzione col premio calcolato dal modello."""
    return OptionLeg(
        leg_id=_next_id(),
        side=side,
        qty=qty,
        right=right,
        strike=strike,
        iv_override=iv_override,
    )


def option_at_premium(
    right: Right, side: Side, strike: float, premium: float, qty: float = 1.0
) -> OptionLeg:
    """Una gamba opzione con premio imposto a mano."""
    return OptionLeg(
        leg_id=_next_id(),
        side=side,
        qty=qty,
        right=right,
        strike=strike,
        premium=ManualPremium(premium),
    )


def stock(side: Side, entry_price: float, qty: float = 1.0) -> StockLeg:
    """Una gamba azionaria."""
    return StockLeg(leg_id=_next_id(), side=side, qty=qty, entry_price=entry_price)
