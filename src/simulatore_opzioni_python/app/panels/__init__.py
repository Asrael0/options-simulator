"""Pannelli dell'interfaccia, uno per file.

--- COSA FA QUESTO PACCHETTO ---
Contiene i blocchi visivi dell'applicazione: mercato, strategie, gambe,
riepilogo, greche, simulatore di scenari, costi. Ogni pannello è una funzione che
riceve il contesto di pagina e disegna se stessa.

Nessun pannello calcola niente di finanziario: i numeri arrivano già pronti da
`ctx.analytics`. Così le pagine si compongono scegliendo quali pannelli
mostrare, senza duplicare logica.

Qui si raccolgono tutti, così le pagine scrivono `from ..panels import ...`
senza sapere in quale file stia ciascuno.
"""

from __future__ import annotations

from .chart_controls import chart_controls_panel
from .costs import cost_panel
from .greeks import greeks_panel
from .heatmap import heatmap_intro_panel
from .legs import legs_panel
from .market import market_panel
from .positions import load_saved_into, saved_panel
from .scenario import scenario_panel
from .strategy import strategy_panel
from .summary import summary_panel

__all__ = [
    "chart_controls_panel",
    "cost_panel",
    "greeks_panel",
    "heatmap_intro_panel",
    "legs_panel",
    "load_saved_into",
    "market_panel",
    "saved_panel",
    "scenario_panel",
    "strategy_panel",
    "summary_panel",
]
