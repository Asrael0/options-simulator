"""Elementi visivi riutilizzabili e costanti di stile.

--- COSA FA QUESTO FILE ---
Piccoli pezzi di interfaccia usati ovunque: uno slider che non intasa il
server, il riquadro con una cifra in evidenza, l'avviso didattico, e le
costanti dei colori e delle classi CSS.

Sta tutto qui per una ragione sola: se domani i riquadri devono cambiare
aspetto, si modifica un punto invece di quindici.

--- LE STRINGHE DI CLASSI CSS ---
Le costanti come `CARD` sono elenchi di classi Tailwind, un sistema in cui ogni
classe fa una cosa sola: `p-4` = padding, `rounded-xl` = angoli arrotondati,
`bg-[#11141c]` = colore di sfondo. Non è Python: è testo che finisce
nell'attributo `class` dell'HTML.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

CARD = "w-full bg-[#11141c] border border-[#1e222d] rounded-xl p-4"
TITLE = "text-sm font-semibold text-[#c9cfdd] mb-2"
MUTED = "text-xs text-[#8b93a7]"
FAINT = "text-[11px] text-[#7c8497] leading-relaxed"
NOTICE = (
    "w-full text-xs leading-relaxed rounded-xl px-4 py-3 "
    "bg-[rgba(240,165,0,0.08)] border border-[rgba(240,165,0,0.3)] text-[#d9c08a]"
)
DANGER = (
    "w-full text-xs leading-relaxed rounded-xl px-4 py-3 "
    "bg-[rgba(255,93,108,0.08)] border border-[rgba(255,93,108,0.35)] text-[#ffb3ba]"
)

COLOR_PROFIT = "#3ddc97"
COLOR_LOSS = "#ff5d6c"
COLOR_NEUTRAL = "#e6e9f0"

MONEYNESS_COLOR = {
    "ITM": COLOR_PROFIT,
    "OTM": COLOR_LOSS,
    "ATM": "#f0a500",
    "STOCK": "#8b93a7",
}


# --- L'ASTERISCO SOLITARIO NELLA FIRMA -------------------------------------
# Un `*` da solo fra i parametri significa: "tutto quello che viene dopo si può
# passare SOLO per nome".
#
#   throttled_slider(minimum=0, maximum=100, ...)   -> corretto
#   throttled_slider(0, 100, ...)                   -> errore
#
# Sembra una scomodità, ed è invece una difesa. Questa funzione ha sei
# parametri numerici: chiamandola per posizione, invertire `minimum` e `step`
# darebbe uno slider rotto senza nessun errore. Costringendo a scrivere il nome,
# l'errore diventa impossibile.
def throttled_slider(
    *,
    minimum: float,
    maximum: float,
    step: float,
    value: float,
    on_value: Callable[[float], None],
    throttle: float = 0.08,
) -> ui.slider:
    """Slider che non inonda il server di eventi durante il trascinamento.

    Senza throttle un trascinamento produce decine di eventi al secondo, e in
    modalità americana ognuno costruisce alberi binomiali. ``trailing_events``
    garantisce che l'ultimo valore arrivi comunque, quindi non si perde la
    posizione finale del cursore.
    """
    slider = ui.slider(min=minimum, max=maximum, step=step, value=value).props("dense")
    slider.on(
        "update:model-value",
        lambda e: on_value(float(e.args)),
        throttle=throttle,
        trailing_events=True,
    )
    return slider


def stat(label: str, value: str, *, tone: str = "neutral", sub: str = "") -> None:
    """Riquadro con una cifra in evidenza."""
    # --- `dict.get()` con valore di ripiego -------------------------------
    # `dizionario[chiave]` va in errore se la chiave non c'è.
    # `dizionario.get(chiave, ripiego)` restituisce il ripiego invece di
    # fallire. Qui: se `tone` non è né "profit" né "loss", si usa il colore
    # neutro. Un piccolo dizionario creato al volo fa da tabella di
    # traduzione, al posto di una catena di `if`.
    color = {"profit": COLOR_PROFIT, "loss": COLOR_LOSS}.get(tone, COLOR_NEUTRAL)
    # --- `with` PER COSTRUIRE L'INTERFACCIA -------------------------------
    # In NiceGUI il `with` non apre file: dice "tutto ciò che creo qui dentro
    # va messo DENTRO questo contenitore". L'indentazione del codice riflette
    # l'annidamento degli elementi sulla pagina.
    # Il funzionamento del `with` è spiegato in layout.py.
    with ui.column().classes("gap-0 bg-[#0a0c11] rounded-lg px-3 py-2 grow min-w-[150px]"):
        ui.label(label).classes("text-[11px] text-[#8b93a7]")
        ui.label(value).classes("text-base font-bold").style(f"color: {color}")
        if sub:
            ui.label(sub).classes("text-[10px] text-[#6b7280]")


def didactic_notice() -> None:
    """Avviso che deve restare visibile in ogni pagina dell'applicazione."""
    ui.html(
        "<strong>Nota didattica.</strong> I prezzi sono <em>teorici</em>: i modelli "
        "assumono volatilità costante e assenza di salti di prezzo (gap), quindi "
        "divergono dai prezzi reali di mercato. Lo strumento serve a capire le "
        "relazioni tra le variabili, non a stimare prezzi di trading, e non "
        "costituisce consulenza finanziaria."
    ).classes(NOTICE)
