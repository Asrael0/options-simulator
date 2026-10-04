"""Tipi del motore di pricing.

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

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["long", "short"]
Right = Literal["call", "put"]
ExerciseStyle = Literal["european", "american"]
Resolution = Literal["full", "curve"]

STEPS_BY_RESOLUTION: dict[Resolution, int] = {"full": 140, "curve": 70}


# ---------------------------------------------------------------------------
# Origine del premio d'ingresso
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TheoreticalPremium:
    """Il premio lo calcola il motore dai parametri di mercato."""


@dataclass(frozen=True, slots=True)
class ManualPremium:
    """Il premio lo ha imposto l'utente."""

    value: float


PremiumSource = TheoreticalPremium | ManualPremium


# ---------------------------------------------------------------------------
# Gambe della posizione
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OptionLeg:
    """Una gamba opzione."""

    leg_id: str
    side: Side
    qty: float
    right: Right
    strike: float

    premium: PremiumSource = TheoreticalPremium()

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


Leg = OptionLeg | StockLeg


# ---------------------------------------------------------------------------
# Mercato, greche, specifica di pricing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarketParams:
    """Parametri di mercato osservabili a un dato istante."""

    spot: float
    days_to_expiry: float
    risk_free_rate: float
    iv: float
    dividend_yield: float = 0.0


@dataclass(frozen=True, slots=True)
class Greeks:
    """Sensibilità di un'opzione o di una posizione."""

    delta: float
    gamma: float
    theta_per_day: float
    vega_per_point: float
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

    def greeks(self) -> Greeks:
        """Estrae le sole greche, scartando il prezzo."""
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

    contract_multiplier: float = 100.0
    packages: int = 1


@dataclass(frozen=True, slots=True)
class ResolvedLeg:
    """Una gamba con il premio d'ingresso già risolto in un numero."""

    leg: Leg
    entry_premium: float
    signed_qty: float


# ---------------------------------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------------------------------

DAYS_PER_YEAR = 365.0


def years_from_days(days: float) -> float:
    """Giorni -> anni. Le scadenze negative valgono zero, non un tempo negativo."""
    return max(days, 0.0) / DAYS_PER_YEAR


def effective_iv(leg: OptionLeg, market: MarketParams) -> float:
    """IV della gamba: override se presente, altrimenti quella globale."""
    return leg.iv_override if leg.iv_override is not None else market.iv


def spec_for_leg(leg: OptionLeg, market: MarketParams) -> OptionSpec:
    """Costruisce lo ``OptionSpec`` di una gamba dai parametri di mercato."""
    return OptionSpec(
        spot=market.spot,
        strike=leg.strike,
        days_to_expiry=market.days_to_expiry,
        risk_free_rate=market.risk_free_rate,
        iv=effective_iv(leg, market),
        dividend_yield=market.dividend_yield,
        right=leg.right,
    )
