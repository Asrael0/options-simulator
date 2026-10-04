"""Motore di pricing: Python puro, nessuna dipendenza dall'interfaccia.

--- COSA FA QUESTO FILE ---
Raccoglie in un solo posto i nomi pubblici del motore, così chi lo usa può
scrivere `from options_simulator.pricing import black_scholes`.

--- IL VINCOLO ARCHITETTURALE ---
Questo pacchetto non importa nulla dal layer di presentazione. È testabile in
isolamento, usabile da un notebook e riutilizzabile da qualunque interfaccia.
Se un giorno vedi un `from ..app import ...` qui dentro, è un errore.
"""

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
from .implied import implied_volatility
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
    probability_of_profit,
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
    "implied_volatility",
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
    "probability_of_profit",
    "resolve_legs",
    "spec_for_leg",
    "trade_cost",
    "years_from_days",
]
