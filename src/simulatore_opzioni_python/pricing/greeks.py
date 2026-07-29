"""Punto d'ingresso unificato: sceglie Black-Scholes o l'albero binomiale.

--- COSA FA QUESTO FILE ---
Fa da centralino. Chi vuole prezzare un'opzione non deve sapere se serve la
formula chiusa o l'albero: chiama `price_option` e ci pensa questo file a
smistare in base allo stile di esercizio.

Contiene anche la CACHE (per non ricalcolare due volte la stessa cosa) e
l'aggregazione delle greche su tutte le gambe di una posizione.
"""

from __future__ import annotations

# `functools` contiene strumenti che lavorano SULLE funzioni.
from functools import lru_cache

from .binomial import binomial_price, binomial_price_and_greeks
from .black_scholes import black_scholes
from .types import (
    STEPS_BY_RESOLUTION,
    ExerciseStyle,
    Greeks,
    MarketParams,
    OptionLeg,
    OptionSpec,
    PricedOption,
    Resolution,
    ResolvedLeg,
    spec_for_leg,
)

#: Cache dei prezzi binomiali.
#:
#: ``lru_cache`` funziona perché ``OptionSpec`` è un dataclass ``frozen``,
#: quindi hashabile: i parametri SONO la chiave, senza doverla costruire a
#: mano. Nessuno svuota la cache "quando cambiano i parametri", perché
#: parametri diversi sono già voci diverse.
_CACHE_SIZE = 50_000


# --- I DECORATORI ----------------------------------------------------------
# Un decoratore è una riga che comincia con `@` sopra una funzione. Prende la
# funzione scritta sotto, la avvolge in altro codice, e sostituisce l'originale
# con la versione avvolta. Il nome resta lo stesso; il comportamento cambia.
#
# `@lru_cache` avvolge la funzione in un dizionario: la prima volta che la
# chiami con certi argomenti esegue davvero e ricorda il risultato; le volte
# successive con gli STESSI argomenti restituisce quello memorizzato senza
# ricalcolare. Si chiama "memoizzazione". LRU = Least Recently Used: quando la
# cache è piena, butta via le voci usate meno di recente.
#
# Requisito: gli argomenti devono essere "hashabili", cioè immutabili. Una
# lista non lo è (può cambiare, quindi non sarebbe una chiave affidabile), una
# dataclass `frozen` sì. È il motivo per cui in types.py tutto è `frozen`.
#
# Nota: `maxsize=` usa il segno `=` perché è un ARGOMENTO A NOME. Il numero
# 50_000 usa l'underscore come separatore delle migliaia: Python lo ignora,
# serve solo a rendere leggibile il numero.
@lru_cache(maxsize=_CACHE_SIZE)
def _cached_binomial_price(spec: OptionSpec, exercise: ExerciseStyle, steps: int) -> float:
    return binomial_price(spec, exercise, steps)


def clear_price_cache() -> None:
    """Svuota la cache. Serve ai test e al monitoraggio della memoria."""
    # `-> None` significa che la funzione non restituisce niente di utile:
    # esiste solo per l'effetto che produce.
    # `.cache_clear()` è un metodo che `@lru_cache` ha attaccato alla funzione.
    _cached_binomial_price.cache_clear()


def price_cache_info() -> dict[str, int]:
    """Statistiche della cache: hit, miss, dimensione, capacità."""
    info = _cached_binomial_price.cache_info()
    # Un dizionario si scrive `{chiave: valore, ...}`. Le chiavi qui sono
    # stringhe, i valori numeri interi — coerente con `dict[str, int]`.
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        # `or 0` è un idioma: se `info.maxsize` fosse `None`, usa 0 al suo
        # posto. Funziona perché `None` è considerato "falso" da `or`.
        "maxsize": info.maxsize or 0,
    }


# --- ARGOMENTI CON VALORE DI DEFAULT ---------------------------------------
# `resolution: Resolution = "full"` significa: se chi chiama non specifica
# questo argomento, vale "full". Rende la funzione comoda nel caso normale
# senza togliere la possibilità di scegliere.
#
# ATTENZIONE a una trappola classica: mai usare una LISTA o un DIZIONARIO come
# valore di default (`def f(x=[])`). Quel valore viene creato UNA VOLTA SOLA,
# alla definizione, e condiviso da tutte le chiamate. Con valori immutabili
# (numeri, stringhe, None) non c'è problema.
def price_option(
    spec: OptionSpec, exercise: ExerciseStyle, resolution: Resolution = "full"
) -> float:
    """Prezzo di una singola opzione. Nessuna greca calcolata."""
    if exercise == "european":
        return black_scholes(spec).price
    # Le parentesi quadre su un dizionario ne leggono il valore per quella
    # chiave: qui traduce "full"/"curve" nel numero di passi.
    return _cached_binomial_price(spec, exercise, STEPS_BY_RESOLUTION[resolution])


def price_and_greeks(
    spec: OptionSpec, exercise: ExerciseStyle, resolution: Resolution = "full"
) -> PricedOption:
    """Prezzo e greche di una singola opzione."""
    if exercise == "european":
        return black_scholes(spec)
    return binomial_price_and_greeks(spec, exercise, STEPS_BY_RESOLUTION[resolution])


#: Greche di una gamba azionaria.
#:
#: Delta 1 per unità di sottostante, tutto il resto nullo: l'azione non ha
#: convessità né decadimento temporale.
# Creato una volta sola a livello di modulo e riusato: è immutabile, quindi
# condividerlo è sicuro (a differenza di una lista, che andrebbe copiata).
STOCK_GREEKS = Greeks(
    delta=1.0, gamma=0.0, theta_per_day=0.0, vega_per_point=0.0, rho_per_point=0.0
)


def leg_greeks(
    resolved: ResolvedLeg,
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
) -> Greeks:
    """Greche di una singola gamba, senza segno né quantità."""
    leg = resolved.leg
    # `isinstance(oggetto, Classe)` chiede: "questo oggetto è di questo tipo?"
    # Serve a distinguere i due casi della union `Leg`. Nel file payoff.py si
    # vedrà `match`, che fa la stessa cosa in modo più leggibile quando i casi
    # sono più di due.
    if isinstance(leg, OptionLeg):
        return price_and_greeks(spec_for_leg(leg, market), exercise, resolution).greeks()
    return STOCK_GREEKS


def position_greeks(
    legs: list[ResolvedLeg],
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
) -> Greeks:
    """Somma delle greche di tutte le gambe, con segno e quantità applicati."""
    # Accumulatori azzerati prima del ciclo: si sommano man mano.
    delta = gamma = theta = vega = rho = 0.0

    # `for x in lista:` scorre gli elementi di una lista uno per uno. Nota che
    # non serve un indice: in Python si itera direttamente sui valori.
    for resolved in legs:
        g = leg_greeks(resolved, market, exercise, resolution)
        n = resolved.signed_qty
        # `+=` è la forma breve di `delta = delta + ...`. Esistono anche
        # `-=`, `*=`, `/=` e compagnia.
        delta += g.delta * n
        gamma += g.gamma * n
        theta += g.theta_per_day * n
        vega += g.vega_per_point * n
        rho += g.rho_per_point * n

    return Greeks(
        delta=delta,
        gamma=gamma,
        theta_per_day=theta,
        vega_per_point=vega,
        rho_per_point=rho,
    )
