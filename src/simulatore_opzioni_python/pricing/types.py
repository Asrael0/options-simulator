"""Tipi del motore di pricing.

--- COS'È QUESTO TESTO FRA TRIPLE VIRGOLETTE ---
Si chiama "docstring". È una stringa messa in cima a un file, a una funzione o a
una classe, e Python la conserva: chiedendo `help(nome)` te la ristampa. Serve a
spiegare COSA fa la cosa; i commenti con `#` servono invece a spiegare COME o
PERCHÉ. Convenzione: la docstring sta sempre come primissima riga del blocco.

--- COSA FA QUESTO FILE ---
Non calcola niente. Definisce soltanto il *vocabolario* del progetto: cos'è una
gamba, cosa sono i parametri di mercato, cosa sono le greche. Tutti gli altri
file importano da qui, così parlano la stessa lingua.

CONVENZIONI DI UNITÀ — leggere prima di toccare qualunque formula.

1. Tassi e volatilità sono SEMPRE decimali, mai percentuali.
   IV del 30% => 0.30. Tasso del 4% => 0.04. La conversione da e verso la
   percentuale è responsabilità esclusiva del layer di presentazione.

2. Il motore lavora PER UNITÀ DI SOTTOSTANTE. ``qty`` è un moltiplicatore
   puro. Il moltiplicatore di contratto (100 azioni) e il numero di pacchetti
   vivono solo in ``trade_cost()``, nel layer monetario.

3. Le greche portano l'unità nel nome. ``theta_per_day`` è in valuta al
   giorno, non all'anno; ``vega_per_point`` è per +1 punto di IV (cioè +0.01
   decimale), non per +1.00.
"""

# --- `from __future__ import annotations` ---------------------------------
# Riga tecnica da mettere in cima a ogni file. Dice a Python: "le annotazioni
# di tipo trattale come semplice testo, non provare a eseguirle subito".
# Serve a due cose: permette di usare tipi moderni anche su versioni vecchie di
# Python, e permette a una classe di riferirsi a se stessa nei propri tipi.
# Non cambia il comportamento del programma.
from __future__ import annotations

# --- `import` -------------------------------------------------------------
# `import` porta dentro questo file codice scritto altrove.
# Esistono due forme:
#   import math          -> poi si scrive math.sqrt(...)
#   from math import sqrt -> poi si scrive sqrt(...)
# Qui si usa la seconda: si prendono solo i due nomi che servono.
# `dataclasses` e `typing` fanno parte della "libreria standard": arrivano già
# con Python, non vanno installate.
from dataclasses import dataclass
from typing import Literal

# --- ALIAS DI TIPO --------------------------------------------------------
# Un alias di tipo è un soprannome per un tipo. `Side` non è un valore: è
# un'etichetta che significa "una stringa che può valere solo 'long' o 'short'".
#
# `Literal[...]` è la parte interessante: invece di dire "una stringa
# qualsiasi", elenca esattamente i valori ammessi. Scrivendo per sbaglio
# side="longg", il controllore di tipi (mypy) lo segnala PRIMA di eseguire il
# programma. Senza `Literal` te ne accorgeresti solo a run-time, forse.
#
# I nomi dei tipi si scrivono in MaiuscoloCammello per convenzione.
Side = Literal["long", "short"]
Right = Literal["call", "put"]
ExerciseStyle = Literal["european", "american"]
Resolution = Literal["full", "curve"]

# --- COSTANTI E IL COMMENTO `#:` ------------------------------------------
# Per convenzione i nomi TUTTI_MAIUSCOLI indicano valori che non vanno mai
# modificati durante l'esecuzione. Python non lo impone: è un patto fra
# programmatori.
#
# Il commento che inizia con `#:` (invece del solo `#`) è una convenzione degli
# strumenti di documentazione: significa "questa è la descrizione dell'elemento
# che segue", ed è per questo che lo trovi sopra molti campi in questo file.
#
# `dict[Resolution, int]` significa: un dizionario le cui chiavi sono valori di
# tipo Resolution e i cui valori sono numeri interi. Un dizionario associa
# chiavi a valori, e si scrive fra graffe con i due punti.
#: Passi dell'albero binomiale per risoluzione.
#:
#: ``curve`` ne usa meno: serve a disegnare le curve del payoff, dove la forma
#: è visivamente identica ma i punti da valutare sono centinaia. ``full`` è la
#: precisione piena, usata per ogni numero che l'utente legge a schermo.
STEPS_BY_RESOLUTION: dict[Resolution, int] = {"full": 140, "curve": 70}


# ---------------------------------------------------------------------------
# Origine del premio d'ingresso
# ---------------------------------------------------------------------------


# --- `@dataclass`: il decoratore che scrive codice al posto tuo -------------
# La riga che comincia con `@` sopra una classe si chiama "decoratore": prende
# la classe scritta sotto e la restituisce modificata.
#
# `@dataclass` guarda i campi dichiarati e scrive automaticamente il costruttore
# (il codice che crea l'oggetto), il confronto con `==`, e la rappresentazione
# testuale. Senza, dovresti scrivere venti righe a mano per ogni classe.
#
# Le due opzioni usate qui:
#
#   frozen=True  -> l'oggetto è IMMUTABILE: una volta creato non si può più
#                   modificare (`x.campo = 5` diventa un errore). Sembra
#                   scomodo, ma elimina un'intera famiglia di bug: nessuno può
#                   cambiarti un oggetto sotto i piedi mentre lo stai usando.
#                   Per "modificarlo" si usa `dataclasses.replace()`, che ne
#                   restituisce una COPIA con i campi cambiati.
#
#   slots=True   -> ottimizzazione: l'oggetto occupa meno memoria e i suoi campi
#                   si leggono più in fretta. In cambio non si possono
#                   aggiungere campi non dichiarati. Utile quando se ne creano
#                   tanti, come qui.
@dataclass(frozen=True, slots=True)
class TheoreticalPremium:
    """Il premio lo calcola il motore dai parametri di mercato."""

    # Questa classe non ha campi: la sua sola esistenza è l'informazione.
    # Il corpo è la sola docstring, che basta a rendere la classe valida —
    # in Python un blocco non può essere vuoto.


@dataclass(frozen=True, slots=True)
class ManualPremium:
    """Il premio lo ha imposto l'utente."""

    # `value: float` dichiara un campo di nome `value` che contiene un numero
    # decimale. `float` sta per "floating point", il tipo dei numeri con la
    # virgola; `int` è quello dei numeri interi.
    value: float


# --- UNIONE DI TIPI: la barra verticale ------------------------------------
# `A | B` si legge "o A o B". Qui: un premio è o teorico o manuale, mai altro.
#
# Perché non un singolo campo `float | None`, con None che significa "teorico"?
# Perché `None` non spiega niente, e soprattutto perché con l'unione il valore
# ESISTE SOLO nel caso manuale: non può capitare uno stato "manuale ma senza
# valore", che sarebbe rappresentabile e privo di senso.
PremiumSource = TheoreticalPremium | ManualPremium


# ---------------------------------------------------------------------------
# Gambe della posizione
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OptionLeg:
    """Una gamba opzione."""

    # Campi SENZA valore di default: vanno forniti obbligatoriamente quando si
    # crea l'oggetto.
    leg_id: str  # `str` = testo
    side: Side  # può valere solo "long" o "short"
    qty: float
    right: Right  # solo "call" o "put"
    strike: float

    # Campi CON valore di default: se non li passi, prendono questo valore.
    # Regola di Python: tutti i campi con default devono stare DOPO quelli
    # senza, altrimenti sarebbe ambiguo quale argomento è quale.
    premium: PremiumSource = TheoreticalPremium()

    #: Override della IV per questa gamba (decimale). ``None`` = IV globale.
    # `float | None` significa "un numero decimale, oppure niente".
    # `None` è il valore speciale di Python che rappresenta l'assenza di valore
    # (in altri linguaggi si chiama null o nil).
    iv_override: float | None = None


@dataclass(frozen=True, slots=True)
class StockLeg:
    """Una gamba azionaria.

    ``entry_price`` è il prezzo di carico, NON uno strike: non entra in
    nessuna formula di pricing, serve solo come base di costo per il P&L.
    """

    leg_id: str
    side: Side
    qty: float
    entry_price: float


#: Unione discriminata sul TIPO, non su un campo stringa. Il vantaggio si vede
#: con ``match``: ``right`` esiste solo dove significa qualcosa, e chiederlo a
#: una ``StockLeg`` è un errore che mypy intercetta prima dell'esecuzione.
Leg = OptionLeg | StockLeg


# ---------------------------------------------------------------------------
# Mercato, greche, specifica di pricing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarketParams:
    """Parametri di mercato osservabili a un dato istante."""

    spot: float
    days_to_expiry: float
    #: Tasso risk-free continuo, decimale.
    risk_free_rate: float
    #: Volatilità implicita di riferimento, decimale.
    iv: float
    #: Dividend yield continuo, decimale. 0 = nessun dividendo.
    dividend_yield: float = 0.0


@dataclass(frozen=True, slots=True)
class Greeks:
    """Sensibilità di un'opzione o di una posizione."""

    #: Variazione di valore per +1 unità di valuta sul sottostante.
    delta: float
    #: Variazione del delta per +1 unità di valuta sul sottostante.
    gamma: float
    #: Variazione di valore per il passare di 1 giorno.
    theta_per_day: float
    #: Variazione di valore per +1 punto di IV (+0.01 decimale).
    vega_per_point: float
    #: Variazione di valore per +1 punto di tasso (+0.01 decimale).
    rho_per_point: float


@dataclass(frozen=True, slots=True)
class PricedOption:
    """Prezzo e greche di una singola opzione."""

    price: float
    delta: float
    gamma: float
    theta_per_day: float
    vega_per_point: float
    rho_per_point: float

    # --- METODO: una funzione che appartiene a una classe ------------------
    # Si definisce dentro la classe e riceve sempre come primo argomento
    # `self`, cioè l'oggetto su cui è stata chiamata. Scrivendo `x.greeks()`,
    # Python passa `x` come `self` automaticamente.
    #
    # `-> Greeks` dopo la parentesi è l'annotazione del valore restituito.
    def greeks(self) -> Greeks:
        """Estrae le sole greche, scartando il prezzo."""
        # Chiamata con "argomenti a nome": `delta=self.delta`. È più lungo di
        # passarli in ordine, ma impossibile da sbagliare — e con cinque numeri
        # dello stesso tipo, sbagliare l'ordine sarebbe fin troppo facile.
        return Greeks(
            delta=self.delta,
            gamma=self.gamma,
            theta_per_day=self.theta_per_day,
            vega_per_point=self.vega_per_point,
            rho_per_point=self.rho_per_point,
        )


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """Descrizione completa e autosufficiente di un'opzione da prezzare."""

    spot: float
    strike: float
    days_to_expiry: float
    risk_free_rate: float
    iv: float
    right: Right
    dividend_yield: float = 0.0


@dataclass(frozen=True, slots=True)
class Sizing:
    """Dimensionamento monetario dell'operazione."""

    #: Unità di sottostante controllate da un contratto o lotto (100 = USA).
    contract_multiplier: float = 100.0
    #: Quante volte la strategia viene replicata.
    packages: int = 1


@dataclass(frozen=True, slots=True)
class ResolvedLeg:
    """Una gamba con il premio d'ingresso già risolto in un numero."""

    leg: Leg
    #: Premio (opzione) o prezzo di carico (azione), per unità di sottostante.
    entry_premium: float
    #: ``qty`` col segno della posizione: +qty se long, -qty se short.
    signed_qty: float


# ---------------------------------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------------------------------

DAYS_PER_YEAR = 365.0


# --- DEFINIRE UNA FUNZIONE -------------------------------------------------
# `def nome(parametri) -> tipo_restituito:` seguito da un blocco INDENTATO.
# In Python l'indentazione non è estetica: è la sintassi. Le righe rientrate
# di quattro spazi appartengono alla funzione; quando il rientro finisce,
# finisce la funzione. Non ci sono parentesi graffe.
#
# `days: float` dichiara che il parametro è un numero decimale.
# `-> float` dichiara che la funzione restituisce un numero decimale.
def years_from_days(days: float) -> float:
    """Giorni -> anni. Le scadenze negative valgono zero, non un tempo negativo."""
    # `max(a, b)` restituisce il più grande fra due valori. Qui serve a
    # trasformare un numero di giorni negativo in zero.
    # `return` termina la funzione restituendo il valore calcolato.
    return max(days, 0.0) / DAYS_PER_YEAR


def effective_iv(leg: OptionLeg, market: MarketParams) -> float:
    """IV della gamba: override se presente, altrimenti quella globale."""
    # Questo è un "operatore ternario": una scelta scritta su una riga sola.
    # Si legge nell'ordine: VALORE_SE_VERO if CONDIZIONE else VALORE_SE_FALSO.
    # Equivale a:
    #     if leg.iv_override is not None:
    #         return leg.iv_override
    #     else:
    #         return market.iv
    #
    # `is not None` invece di `!= None`: con `None` si usa sempre `is`, perché
    # controlla l'identità dell'oggetto e non può essere ridefinito.
    return leg.iv_override if leg.iv_override is not None else market.iv


def spec_for_leg(leg: OptionLeg, market: MarketParams) -> OptionSpec:
    """Costruisce lo ``OptionSpec`` di una gamba dai parametri di mercato."""
    # Creare un oggetto significa "chiamare" la classe come fosse una funzione.
    # Il punto (`market.spot`) accede a un campo di un oggetto.
    return OptionSpec(
        spot=market.spot,
        strike=leg.strike,
        days_to_expiry=market.days_to_expiry,
        risk_free_rate=market.risk_free_rate,
        iv=effective_iv(leg, market),  # una funzione può chiamarne un'altra
        dividend_yield=market.dividend_yield,
        right=leg.right,
    )
