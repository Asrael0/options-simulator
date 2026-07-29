"""Albero binomiale Cox-Ross-Rubinstein: prezza europee e americane.

--- COSA FA QUESTO FILE ---
L'idea: invece di una formula, si SIMULA. Si divide il tempo fino alla scadenza
in N passi. A ogni passo il prezzo può solo salire di un fattore `u` o scendere
di un fattore `d`. Si ottiene un albero di prezzi possibili.

Poi si va AL CONTRARIO: si parte dalla scadenza, dove il valore dell'opzione è
noto (è il payoff), e si torna indietro passo per passo calcolando quanto vale
ogni nodo. Al nodo di partenza c'è il prezzo di oggi.

Per le AMERICANE, a ogni nodo si confronta "tenere l'opzione" con "esercitarla
adesso" e si prende il massimo. È così che il valore dell'esercizio anticipato
*emerge* dal calcolo, invece di doverlo aggiungere a mano.

PERCHÉ NUMPY NON È UN OPZIONALE QUI.

Un albero a N passi ha O(N²) nodi. Con N = 140 sono circa diecimila
valutazioni: in JavaScript un doppio ciclo le esegue in frazioni di
millisecondo, in Python puro sarebbe cento volte più lento e l'interfaccia
diventerebbe inusabile. La soluzione non è "scrivere Python più veloce" ma
cambiare la forma del calcolo: un intero LIVELLO dell'albero è un array, e
l'induzione all'indietro diventa UNA operazione vettoriale per livello. Si
passa da O(N²) iterazioni interpretate a O(N) chiamate NumPy, ognuna eseguita
in C.

La riga che fa tutto il lavoro è::

    val = discount * (p_up * val[:-1] + p_down * val[1:])

``val[:-1]`` sono i figli "su", ``val[1:]`` i figli "giù". Uno slittamento di
un indice esprime l'intera struttura ad albero.

ALTRE OTTIMIZZAZIONI, ereditate dalla versione TypeScript.

1. Zero potenze nei cicli. Una tabella ``u^k`` per k in [-steps, steps] viene
   costruita una volta sola; il prezzo di ogni nodo è una lettura indicizzata.
2. Delta, gamma e theta si LEGGONO dall'albero (livelli 1 e 2, metodo standard
   di Hull) invece di ricostruire alberi bumpati. Sono gratis e, soprattutto,
   sono lisci: le differenze finite dividono per h², amplificando di 1e4 il
   sawtooth di convergenza del CRR. Restano bumpati solo vega e rho, che
   dividono per 2*0.01 e quindi non soffrono del problema.

NOTA sulla convergenza: il CRR puro converge a Black-Scholes in modo
oscillante, O(1/n). Esistono tecniche di smoothing (Broadie-Detemple) che la
rendono più regolare, ma cambierebbero i valori attesi del test di
convergenza. Non sono attive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .black_scholes import _deterministic_limit
from .types import (
    DAYS_PER_YEAR,
    ExerciseStyle,
    OptionSpec,
    PricedOption,
    years_from_days,
)

#: Servono almeno due livelli per leggere gamma dall'albero.
MIN_STEPS = 2

_VOL_BUMP = 0.01
_RATE_BUMP = 0.01


@dataclass(frozen=True, slots=True)
class _TreeResult:
    """Risultato interno dell'albero. L'underscore dice: non usarlo da fuori."""

    price: float
    delta: float
    gamma: float
    theta_per_day: float


def _run_tree(spec: OptionSpec, exercise: ExerciseStyle, requested_steps: int) -> _TreeResult:
    """Costruisce l'albero e restituisce prezzo, delta, gamma e theta.

    Delta e gamma sono letti ai livelli 1 e 2, quindi valgono tecnicamente a
    t = dt e t = 2*dt anziché a t = 0. Con 140 passi su 30 giorni lo
    sfasamento è di circa 0.4 giorni: produce un bias sotto l'1%, e in cambio
    le curve sono lisce, che su uno slider conta di più.
    """
    s0 = spec.spot
    k = spec.strike
    r = spec.risk_free_rate
    sigma = spec.iv
    q = spec.dividend_yield
    t = years_from_days(spec.days_to_expiry)

    if t <= 0.0 or sigma <= 0.0 or s0 <= 0.0 or k <= 0.0:
        limit = _deterministic_limit(spec)
        return _TreeResult(limit.price, limit.delta, limit.gamma, limit.theta_per_day)

    # `int(...)` tronca un decimale a intero. Il numero di passi deve essere
    # intero perché conta quante volte si ripete il ciclo.
    steps = max(MIN_STEPS, int(requested_steps))
    dt = t / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    drift = math.exp((r - q) * dt)
    p_up = (drift - d) / (u - d)

    # Condizione di non-arbitraggio del CRR: d < e^((r-q)dt) < u, cioè
    # sigma > |r - q| * sqrt(dt). Con IV molto bassa o scadenze lunghe la
    # condizione cade e p_up esce da [0, 1]: l'albero produrrebbe prezzi
    # arbitraggiabili senza segnalare nulla. In quel regime la volatilità è
    # talmente piccola che il limite deterministico è la risposta corretta.
    #
    # `0.0 < p_up < 1.0` è il "confronto a catena": Python permette di scrivere
    # le disuguaglianze come in matematica, invece di `p_up > 0 and p_up < 1`.
    # `not` davanti nega il risultato.
    if not 0.0 < p_up < 1.0:
        limit = _deterministic_limit(spec)
        return _TreeResult(limit.price, limit.delta, limit.gamma, limit.theta_per_day)

    p_down = 1.0 - p_up
    discount = math.exp(-r * dt)
    is_call = spec.right == "call"
    is_american = exercise == "american"

    # --- COSTRUIRE UNA TABELLA CON UNA SOLA OPERAZIONE ---------------------
    # `np.arange(a, b)` crea l'array [a, a+1, ..., b-1]: come `range` ma array.
    # `u ** array` eleva `u` a ciascun esponente in un colpo solo.
    # Risultato: pow_u[steps + e] contiene u elevato alla e, con e che va da
    # -steps a +steps. Costruita una volta, si legge migliaia di volte.
    pow_u = u ** np.arange(-steps, steps + 1, dtype=np.int64)

    # --- FUNZIONE DENTRO UNA FUNZIONE (closure) ----------------------------
    # `level_prices` è definita dentro `_run_tree` e "vede" le variabili di
    # `_run_tree` (`s0`, `pow_u`, `steps`) senza doverle ricevere come
    # argomenti. Questo legame si chiama CHIUSURA (closure).
    # Vantaggi: nomi che non inquinano il resto del file, e nessun parametro da
    # ripassare a ogni chiamata.
    def level_prices(level: int) -> np.ndarray:
        """Prezzi del sottostante a un livello, dal nodo più alto al più basso.

        Gli esponenti sono ``level, level-2, ..., -level``: uno slicing con
        passo -2 li estrae come vista, senza allocare.
        """
        # --- SLICING: prendere una fetta di sequenza -----------------------
        # La sintassi è `array[inizio:fine:passo]`.
        #   array[2:5]    -> dall'indice 2 al 4 (il 5 è escluso)
        #   array[:3]     -> dall'inizio al 2
        #   array[3:]     -> dal 3 alla fine
        #   array[:-1]    -> tutto tranne l'ultimo (indici negativi contano
        #                    dalla fine: -1 è l'ultimo)
        #   array[::-1]   -> tutto, al contrario
        #   array[a::-2]  -> da `a` all'indietro saltando di due
        #
        # Qui: si parte dall'indice `steps + level` e si torna indietro di due
        # in due, poi si tengono i primi `level + 1` elementi.
        # Nota: uno slice di un array NumPy è una VISTA, non una copia — non
        # occupa nuova memoria.
        return s0 * pow_u[steps + level :: -2][: level + 1]

    def intrinsic(prices: np.ndarray) -> np.ndarray:
        """Valore d'esercizio immediato per un intero livello."""
        # `np.maximum(a, b)` confronta elemento per elemento, a differenza di
        # `max(a, b)` che confronta due valori singoli.
        return np.maximum(prices - k, 0.0) if is_call else np.maximum(k - prices, 0.0)

    # Livello di partenza: la scadenza, dove il valore è noto.
    val = intrinsic(level_prices(steps))

    # --- ASSEGNAZIONE MULTIPLA ---------------------------------------------
    # `a = b = c = 0.0` assegna lo stesso valore a tre variabili.
    # Servono inizializzate qui perché più sotto vengono riempite dentro un
    # `if`: senza, se l'`if` non scattasse mai, il nome non esisterebbe.
    v20 = v21 = v22 = 0.0
    v10 = v11 = 0.0

    # --- CICLO `for` E `range` ---------------------------------------------
    # `for x in sequenza:` ripete il blocco una volta per ogni elemento.
    # `range(inizio, fine, passo)` genera numeri; `fine` è sempre ESCLUSO.
    # Qui: `range(steps-1, -1, -1)` conta ALL'INDIETRO da steps-1 fino a 0
    # incluso (si ferma prima di -1). Serve perché l'induzione va dalla
    # scadenza verso oggi.
    for level in range(steps - 1, -1, -1):
        # LA RIGA CHIAVE. `val` contiene i valori del livello successivo.
        # `val[:-1]` = tutti tranne l'ultimo = i figli "su".
        # `val[1:]`  = tutti tranne il primo  = i figli "giù".
        # Sommandoli pesati e scontando si ottengono i valori di QUESTO livello,
        # che ha un elemento in meno. Un intero strato dell'albero in una riga.
        val = discount * (p_up * val[:-1] + p_down * val[1:])
        if is_american:
            # `out=val` dice a NumPy di scrivere il risultato dentro `val`
            # invece di creare un nuovo array: evita un'allocazione per livello.
            np.maximum(val, intrinsic(level_prices(level)), out=val)
        if level == 2:
            # Assegnazione multipla in parallelo: la parte a destra viene
            # valutata tutta, poi distribuita ai nomi a sinistra in ordine.
            v20, v21, v22 = float(val[0]), float(val[1]), float(val[2])
        # `elif` = "else if": si controlla solo se l'`if` sopra era falso.
        elif level == 1:
            v10, v11 = float(val[0]), float(val[1])

    # Alla fine del ciclo `val` ha un solo elemento: la radice, cioè oggi.
    price = float(val[0])

    upper_gap = s0 * u * u - s0
    lower_gap = s0 - s0 * d * d
    gamma = ((v20 - v21) / upper_gap - (v21 - v22) / lower_gap) / ((upper_gap + lower_gap) / 2.0)

    return _TreeResult(
        price=price,
        delta=(v10 - v11) / (s0 * u - s0 * d),
        gamma=gamma,
        # v21 è il nodo centrale a t = 2*dt: u * d = 1, quindi ha lo stesso
        # prezzo del sottostante di partenza e la differenza col nodo radice
        # isola il solo passare del tempo.
        theta_per_day=(v21 - price) / (2.0 * dt) / DAYS_PER_YEAR,
    )


def binomial_price(spec: OptionSpec, exercise: ExerciseStyle, steps: int) -> float:
    """Prezzo di un'opzione con l'albero binomiale."""
    return _run_tree(spec, exercise, steps).price


def binomial_price_and_greeks(
    spec: OptionSpec, exercise: ExerciseStyle, steps: int
) -> PricedOption:
    """Prezzo e greche complete. Vega e rho richiedono alberi aggiuntivi."""
    base = _run_tree(spec, exercise, steps)

    # --- `replace()`: modificare un oggetto immutabile ---------------------
    # `spec` è una dataclass `frozen`: `spec.iv = 0.31` sarebbe un errore.
    # `replace(spec, iv=...)` non tocca l'originale: restituisce una COPIA con
    # quel solo campo diverso. È il modo idiomatico di "cambiare" un oggetto
    # immutabile, e garantisce che nessun altro veda la modifica.
    #
    # Qui serve a "bumpare" un parametro: si riprezza con volatilità un filo
    # più alta e un filo più bassa, e la differenza dice quanto il prezzo è
    # sensibile alla volatilità. È la definizione pratica di derivata.
    vol_up = binomial_price(replace(spec, iv=spec.iv + _VOL_BUMP), exercise, steps)
    if spec.iv > _VOL_BUMP:
        vol_down = binomial_price(replace(spec, iv=spec.iv - _VOL_BUMP), exercise, steps)
        # Differenza centrale: più accurata, perché gli errori dei due lati si
        # cancellano a vicenda.
        vega_per_point = (vol_up - vol_down) / 2.0
    else:
        # Differenza in avanti: si usa quando non c'è margine sotto, perché una
        # volatilità negativa non ha senso.
        vega_per_point = vol_up - base.price

    rate_up = binomial_price(
        replace(spec, risk_free_rate=spec.risk_free_rate + _RATE_BUMP), exercise, steps
    )
    rate_down = binomial_price(
        replace(spec, risk_free_rate=spec.risk_free_rate - _RATE_BUMP), exercise, steps
    )

    return PricedOption(
        price=base.price,
        delta=base.delta,
        gamma=base.gamma,
        theta_per_day=base.theta_per_day,
        vega_per_point=vega_per_point,
        rho_per_point=(rate_up - rate_down) / 2.0,
    )
