"""Motore di pricing: Python puro, nessuna dipendenza dall'interfaccia.

--- COS'È UN PACCHETTO E A COSA SERVE QUESTO FILE ---
Una cartella che contiene un file chiamato `__init__.py` è un PACCHETTO: Python
la tratta come un contenitore di moduli importabili. Il nome fra doppi
underscore (si legge "dunder init") è una convenzione riservata al linguaggio.

`__init__.py` viene eseguito la prima volta che qualcuno scrive
`import simulatore_opzioni_python.pricing`. Serve a due cose:
  1. dichiarare che la cartella è un pacchetto;
  2. fare da VETRINA — raccogliere in un solo posto i nomi che si vogliono
     rendere disponibili all'esterno.

Grazie a questo file, chi usa il motore può scrivere:
    from simulatore_opzioni_python.pricing import black_scholes
invece del più lungo e fragile:
    from simulatore_opzioni_python.pricing.black_scholes import black_scholes

Il vantaggio non è solo la brevità: se domani si spostasse `black_scholes` in
un altro file, basterebbe cambiare una riga QUI e nessun altro codice si
accorgerebbe di niente.

--- IL VINCOLO ARCHITETTURALE ---
Questo pacchetto non importa nulla dal layer di presentazione. È testabile in
isolamento, usabile da un notebook e riutilizzabile da qualunque interfaccia.
Se un giorno vedi un `from ..app import ...` qui dentro, è un errore.
"""

# --- IMPORT RELATIVI -------------------------------------------------------
# Il punto iniziale significa "a partire da dove mi trovo io".
#   .binomial   -> il file binomial.py in QUESTA stessa cartella
#   ..pricing   -> risali di una cartella, poi entra in pricing
#   ...qualcosa -> risali di due, e così via
#
# L'alternativa sono gli import ASSOLUTI, che scrivono il percorso completo
# dalla radice del progetto. I relativi sono più corti e sopravvivono a un
# eventuale rinominamento del pacchetto.
#
# Le parentesi tonde permettono di spezzare l'import su più righe: senza,
# servirebbe una barra rovesciata a fine riga, molto più fragile.
from .binomial import binomial_price, binomial_price_and_greeks
from .black_scholes import black_scholes, black_scholes_price, probability_itm
from .greeks import (
    clear_price_cache,
    leg_greeks,
    position_greeks,
    price_and_greeks,
    price_cache_info,
    price_option,
)
from .normal import norm_cdf, norm_pdf
from .payoff import (
    LegCost,
    MoneynessCode,
    PayoffBounds,
    TradeCost,
    break_evens,
    intrinsic_at_expiry,
    leg_entry_premium,
    moneyness,
    net_cost,
    payoff_bounds,
    pl_at_expiry,
    pl_at_market,
    resolve_legs,
    trade_cost,
)
from .types import (
    STEPS_BY_RESOLUTION,
    ExerciseStyle,
    Greeks,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    OptionSpec,
    PremiumSource,
    PricedOption,
    Resolution,
    ResolvedLeg,
    Right,
    Side,
    Sizing,
    StockLeg,
    TheoreticalPremium,
    effective_iv,
    spec_for_leg,
    years_from_days,
)

# --- `__all__`: l'elenco ufficiale di ciò che è pubblico --------------------
# È una lista di stringhe coi nomi che il pacchetto espone. Fa due cose:
#
#   1. Definisce cosa succede con `from ... import *` (la forma che importa
#      tutto in blocco — sconsigliata, ma esiste).
#   2. Molto più importante: dice agli strumenti (linter, editor, chi legge)
#      "questa è l'interfaccia ufficiale, il resto è dettaglio interno".
#
# Senza `__all__`, ruff segnalerebbe ogni import qui sopra come "importato ma
# mai usato" — perché tecnicamente è vero: sono importati solo per essere
# ri-esportati. Elencarli qui è la dichiarazione che è voluto.
#
# L'ordine è alfabetico, con le MAIUSCOLE prima delle minuscole: è l'ordine
# che ruff impone automaticamente, per evitare discussioni.
__all__ = [
    "STEPS_BY_RESOLUTION",
    "ExerciseStyle",
    "Greeks",
    "Leg",
    "LegCost",
    "ManualPremium",
    "MarketParams",
    "MoneynessCode",
    "OptionLeg",
    "OptionSpec",
    "PayoffBounds",
    "PremiumSource",
    "PricedOption",
    "Resolution",
    "ResolvedLeg",
    "Right",
    "Side",
    "Sizing",
    "StockLeg",
    "TheoreticalPremium",
    "TradeCost",
    "binomial_price",
    "binomial_price_and_greeks",
    "black_scholes",
    "black_scholes_price",
    "break_evens",
    "clear_price_cache",
    "effective_iv",
    "intrinsic_at_expiry",
    "leg_entry_premium",
    "leg_greeks",
    "moneyness",
    "net_cost",
    "norm_cdf",
    "norm_pdf",
    "payoff_bounds",
    "pl_at_expiry",
    "pl_at_market",
    "position_greeks",
    "price_and_greeks",
    "price_cache_info",
    "price_option",
    "probability_itm",
    "resolve_legs",
    "spec_for_leg",
    "trade_cost",
    "years_from_days",
]
