"""Tema grafico: colori, caratteri e ritocchi ai componenti.

--- COSA FA QUESTO FILE ---
Tutti i colori del sito vivono qui, come *variabili CSS* (``--accent``,
``--profit``…). Le pagine non scrivono mai un colore a mano: usano le classi
(``t-muted``, ``sim-card``…) o ``var(--nome)``. Così il tema chiaro e quello
scuro sono solo due elenchi di valori, e passare dall'uno all'altro non tocca
nessun pannello.

La palette prende spunto dall'estetica di Claude: fondo caldo (antracite o
avorio), accento terracotta, titoli in serif.

Il grafico è l'unica eccezione: ECharts vuole colori veri, non variabili CSS,
quindi ``chart_palette`` restituisce gli stessi valori come testo.
"""

from __future__ import annotations

from typing import Literal

from nicegui import app, ui

Theme = Literal["dark", "light"]
ThemeMode = Literal["auto", "dark", "light"]
THEME_MODES = ("auto", "dark", "light")
THEME_STORAGE_KEY = "theme"
SYSTEM_THEME_KEY = "system_theme"
DEFAULT_THEME: Theme = "dark"
DEFAULT_MODE: ThemeMode = "auto"

PALETTES: dict[Theme, dict[str, str]] = {
    "dark": {
        "bg": "#1b1a17",
        "sidebar": "#151412",
        "surface": "#24231f",
        "surface-2": "#1e1d1a",
        "hover": "rgba(255,255,255,0.045)",
        "line": "#33312c",
        "line-strong": "#47443d",
        "text": "#ede9e0",
        "text-2": "#cbc6ba",
        "muted": "#9e998d",
        "faint": "#7f7a70",
        "accent": "#d97757",
        "accent-soft": "rgba(217,119,87,0.14)",
        "accent-ink": "#ffffff",
        "profit": "#6cc495",
        "profit-soft": "rgba(108,196,149,0.12)",
        "loss": "#ea7b70",
        "loss-soft": "rgba(234,123,112,0.12)",
        "warn": "#e3ab4f",
        "warn-soft": "rgba(227,171,79,0.12)",
        "info": "#7ea6dc",
        "violet": "#ad90e0",
        "teal": "#55b9aa",
        "shadow": "0 1px 2px rgba(0,0,0,0.25)",
    },
    "light": {
        "bg": "#f5f3ec",
        "sidebar": "#eeebe2",
        "surface": "#fffefa",
        "surface-2": "#f8f6ef",
        "hover": "rgba(0,0,0,0.04)",
        "line": "#e5e1d5",
        "line-strong": "#d3cdbd",
        "text": "#22211d",
        "text-2": "#47453e",
        "muted": "#6f6b61",
        "faint": "#8e897d",
        "accent": "#c4613f",
        "accent-soft": "rgba(196,97,63,0.10)",
        "accent-ink": "#ffffff",
        "profit": "#2e8a58",
        "profit-soft": "rgba(46,138,88,0.10)",
        "loss": "#c6463e",
        "loss-soft": "rgba(198,70,62,0.09)",
        "warn": "#a8730f",
        "warn-soft": "rgba(168,115,15,0.10)",
        "info": "#3a6db3",
        "violet": "#7652be",
        "teal": "#21857a",
        "shadow": "0 1px 2px rgba(60,50,30,0.06), 0 2px 8px rgba(60,50,30,0.04)",
    },
}

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Inter:wght@400;500;600;700&"
    'family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap">'
)

SANS = "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
SERIF = "'Source Serif 4', Georgia, 'Times New Roman', serif"


def _variables(theme: Theme) -> str:
    return "".join(f"--{name}:{value};" for name, value in PALETTES[theme].items())


CSS = (
    """
body.body--dark, :root { __DARK__ }
body.body--light { __LIGHT__ }

body {
  background: var(--bg) !important;
  color: var(--text);
  font-family: __SANS__;
  -webkit-font-smoothing: antialiased;
}
.nicegui-content { padding: 0 !important; }

/* --- Testo ------------------------------------------------------------ */
.t-text   { color: var(--text) !important; }
.t-text2  { color: var(--text-2) !important; }
.t-muted  { color: var(--muted) !important; }
.t-faint  { color: var(--faint) !important; }
.t-accent { color: var(--accent) !important; }
.t-profit { color: var(--profit) !important; }
.t-loss   { color: var(--loss) !important; }
.t-num    { font-variant-numeric: tabular-nums; }
.t-serif  { font-family: __SERIF__; }
.sim-h1 {
  font-family: __SERIF__; font-weight: 500; font-size: 30px;
  line-height: 1.15; letter-spacing: -0.01em; color: var(--text);
}
.sim-eyebrow {
  font-size: 11px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent);
}

/* --- Barra laterale ------------------------------------------------- */
.q-drawer { background: var(--sidebar) !important; border-right: 1px solid var(--line); }
.sim-topbar {
  background: var(--sidebar) !important; color: var(--text) !important;
  border-bottom: 1px solid var(--line);
}
.sim-logo {
  width: 34px; height: 34px; border-radius: 10px; display: flex;
  align-items: center; justify-content: center;
  background: var(--accent); color: var(--accent-ink);
}
.sim-nav-item {
  display: flex; align-items: center; gap: 12px; width: 100%;
  padding: 9px 12px; border-radius: 10px; font-size: 14px;
  color: var(--text-2); text-decoration: none !important;
  transition: background .12s, color .12s;
}
.sim-nav-item:hover { background: var(--hover); color: var(--text); }
.sim-nav-item .q-icon { font-size: 20px; color: var(--muted); }
.sim-nav-item.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.sim-nav-item.active .q-icon { color: var(--accent); }
.sim-nav-section {
  font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  color: var(--faint); padding: 14px 12px 6px;
}
.sim-avatar {
  width: 34px; height: 34px; border-radius: 999px; display: flex; flex-shrink: 0;
  align-items: center; justify-content: center; font-weight: 600; font-size: 14px;
  background: var(--accent-soft); color: var(--accent);
}
.sim-user {
  border: 1px solid var(--line); background: var(--surface); border-radius: 12px;
  padding: 10px;
}

/* --- Card e blocchi ------------------------------------------------- */
.sim-card.q-card, .sim-card {
  background: var(--surface) !important; color: var(--text);
  border: 1px solid var(--line); border-radius: 16px; padding: 18px 20px;
  box-shadow: var(--shadow) !important;
}
.sim-card-icon {
  width: 30px; height: 30px; border-radius: 9px; display: flex; flex-shrink: 0;
  align-items: center; justify-content: center;
  background: var(--accent-soft); color: var(--accent);
}
.sim-card-title { font-size: 15px; font-weight: 600; color: var(--text); }
.sim-stat {
  background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 14px; flex: 1 1 160px; min-width: 150px;
}
.sim-stat-label {
  font-size: 11px; font-weight: 500; letter-spacing: .05em;
  text-transform: uppercase; color: var(--muted);
}
.sim-stat-value {
  font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em; line-height: 1.25;
}
.sim-divider { border-top: 1px solid var(--line); }
.sim-thead {
  font-size: 11px; font-weight: 500; letter-spacing: .04em;
  text-transform: uppercase; color: var(--faint);
}
.sim-chip {
  font-size: 10px; font-weight: 700; letter-spacing: .03em; padding: 1px 6px;
  border-radius: 999px; border: 1px solid currentColor;
}
.sim-badge {
  font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 999px;
  background: var(--accent-soft); color: var(--accent);
}
.sim-badge-muted {
  font-size: 11px; font-weight: 500; padding: 2px 9px; border-radius: 999px;
  background: var(--surface-2); color: var(--muted); border: 1px solid var(--line);
}
.sim-danger {
  background: var(--loss-soft); color: var(--loss);
  border: 1px solid color-mix(in srgb, var(--loss) 35%, transparent);
  border-radius: 12px;
}
.sim-warn {
  background: var(--warn-soft); color: var(--warn); border-radius: 8px;
}
.sim-notice {
  color: var(--faint); border-top: 1px solid var(--line);
}
.sim-chart {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 16px; box-shadow: var(--shadow);
}

/* Riquadro con schede: i pannelli dentro perdono la propria cornice. */
.sim-tabgroup .sim-card.q-card, .sim-tabgroup .sim-card {
  background: transparent !important; border: none; box-shadow: none !important;
  padding: 0;
}
.sim-tabgroup .q-tab-panels { background: transparent; }

/* --- Componenti Quasar --------------------------------------------- */
.q-btn { text-transform: none; border-radius: 10px; font-weight: 500; letter-spacing: 0; }
.q-btn.q-btn--round { border-radius: 999px; }
.q-field--outlined .q-field__control {
  border-radius: 10px; background: var(--surface-2);
}
.q-field--outlined .q-field__control:before { border-color: var(--line-strong) !important; }
.q-field--outlined:hover .q-field__control:before { border-color: var(--muted) !important; }
.q-field__native, .q-field__input, .q-field__prefix, .q-field__suffix,
.q-field__marginal, .q-select__dropdown-icon { color: var(--text) !important; }
.q-field__suffix { color: var(--muted) !important; }
.q-field__label { color: var(--muted) !important; }
.q-field--readonly .q-field__control { opacity: .75; }
.q-menu {
  background: var(--surface) !important; color: var(--text) !important;
  border: 1px solid var(--line); border-radius: 12px !important;
  box-shadow: 0 8px 28px rgba(0,0,0,.18) !important;
}
.q-item { color: var(--text-2); }
.q-item--active, .q-manual-focusable--focused { color: var(--accent) !important; }
.q-tooltip {
  background: var(--text) !important; color: var(--bg) !important;
  font-size: 11px; border-radius: 7px; padding: 5px 8px;
}
.q-separator { background: var(--line) !important; }
.q-slider__track { background: var(--line-strong) !important; }
.q-toggle__label { color: var(--text-2); }

.sim-seg.q-btn-toggle {
  background: var(--surface-2); border: 1px solid var(--line);
  border-radius: 10px; padding: 3px; box-shadow: none;
}
.sim-seg .q-btn { border-radius: 8px !important; color: var(--muted); min-height: 30px; }
.sim-seg .q-btn.bg-primary { color: var(--accent-ink) !important; }

.sim-tabs {
  background: var(--surface-2); border: 1px solid var(--line);
  border-radius: 12px; padding: 4px;
}
.sim-tabs .q-tab {
  border-radius: 9px; min-height: 38px; padding: 0 14px;
  color: var(--muted); text-transform: none;
}
.sim-tabs .q-tab__label { font-weight: 500; font-size: 13px; }
.sim-tabs .q-tab__icon { font-size: 18px; margin-right: 6px; }
.sim-tabs .q-tab__content { flex-direction: row; }
.sim-tabs .q-tab--active {
  background: var(--surface); color: var(--text); box-shadow: var(--shadow);
}
.sim-tabs .q-tab--active .q-tab__icon { color: var(--accent); }
.sim-tabs .q-tab__indicator { display: none; }
.sim-tabs .q-focus-helper { display: none; }

/* --- Guida ---------------------------------------------------------- */
.sim-prose { color: var(--text-2); font-size: 14.5px; line-height: 1.7; }
.sim-prose strong { color: var(--text); }
.sim-prose code {
  color: var(--accent); background: var(--accent-soft);
  padding: 1px 5px; border-radius: 5px; font-size: .9em;
}
.sim-prose table { width: 100%; font-size: 13px; border-collapse: collapse; margin: 8px 0; }
.sim-prose th {
  text-align: left; color: var(--muted); font-weight: 600;
  border-bottom: 1px solid var(--line-strong); padding: 6px 12px 6px 0;
}
.sim-prose td { border-bottom: 1px solid var(--line); padding: 6px 12px 6px 0; }
.sim-prose li { margin: 4px 0; }
.sim-toc a {
  display: block; padding: 6px 10px; border-radius: 8px; font-size: 13px;
  color: var(--text-2); text-decoration: none; border-left: 2px solid transparent;
}
.sim-toc a:hover {
  background: var(--hover); color: var(--accent); border-left-color: var(--accent);
}

/* --- Accesso -------------------------------------------------------- */
.sim-hero {
  background:
    radial-gradient(120% 80% at 0% 0%,
      color-mix(in srgb, var(--accent) 38%, transparent), transparent 60%),
    radial-gradient(90% 70% at 100% 100%,
      color-mix(in srgb, var(--violet) 22%, transparent), transparent 60%),
    var(--sidebar);
  border-right: 1px solid var(--line);
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
  background: var(--line-strong); border-radius: 999px;
  border: 3px solid var(--bg);
}
::-webkit-scrollbar-track { background: transparent; }
""".replace("__DARK__", _variables("dark"))
    .replace("__LIGHT__", _variables("light"))
    .replace("__SANS__", SANS)
    .replace("__SERIF__", SERIF)
)


def theme_mode() -> ThemeMode:
    """Scelta del visitatore: automatico (segue il sistema), scuro o chiaro."""
    try:
        stored = app.storage.user.get(THEME_STORAGE_KEY)
    except RuntimeError:
        return DEFAULT_MODE
    return stored if stored in THEME_MODES else DEFAULT_MODE


def current_theme() -> Theme:
    """Tema effettivo. In automatico usa l'ultimo tema letto dal sistema."""
    mode = theme_mode()
    if mode != "auto":
        return mode
    try:
        system = app.storage.user.get(SYSTEM_THEME_KEY)
    except RuntimeError:
        return DEFAULT_THEME
    return system if system in PALETTES else DEFAULT_THEME


async def _sync_with_system() -> None:
    """Legge dal browser se Windows usa il tema scuro e, se è cambiato, ricarica.

    Il server non può saperlo da solo: lo chiede alla pagina appena è aperta.
    La ricarica avviene solo quando il tema del sistema è davvero cambiato,
    quindi di solito non succede nulla.
    """
    try:
        dark = await ui.run_javascript(
            "window.matchMedia('(prefers-color-scheme: dark)').matches", timeout=3.0
        )
    except TimeoutError:
        return
    system: Theme = "dark" if dark else "light"
    if app.storage.user.get(SYSTEM_THEME_KEY) != system:
        app.storage.user[SYSTEM_THEME_KEY] = system
        ui.navigate.reload()


def apply_theme(force: Theme | None = None) -> Theme:
    """Carica caratteri e stili e attiva il tema del visitatore."""
    theme = force or current_theme()
    palette = PALETTES[theme]
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1">')
    ui.add_head_html(FONTS)
    ui.add_css(CSS)
    ui.dark_mode(theme == "dark")
    ui.colors(
        primary=palette["accent"],
        positive=palette["profit"],
        negative=palette["loss"],
        warning=palette["warn"],
    )
    if force is None and theme_mode() == "auto":
        ui.timer(0.1, _sync_with_system, once=True)
    return theme


# Ordine del pulsante nella barra laterale: automatico -> chiaro -> scuro.
_NEXT_MODE: dict[str, ThemeMode] = {"auto": "light", "light": "dark", "dark": "auto"}
MODE_LABELS: dict[str, tuple[str, str]] = {
    "auto": ("Tema: automatico", "brightness_auto"),
    "light": ("Tema: chiaro", "light_mode"),
    "dark": ("Tema: scuro", "dark_mode"),
}


def toggle_theme() -> None:
    """Passa al tema successivo e ricarica la pagina."""
    app.storage.user[THEME_STORAGE_KEY] = _NEXT_MODE[theme_mode()]
    ui.navigate.reload()


def chart_palette(theme: Theme | None = None) -> dict[str, str]:
    """Colori del grafico per il tema indicato (o quello corrente)."""
    p = PALETTES[theme or current_theme()]
    return {
        "expiry": p["text"],
        "today": p["violet"],
        "sim": p["warn"],
        "other": p["teal"],
        "forward": p["accent"],
        "compare": p["info"],
        "neutral": p["surface-2"],
        "surface": p["surface"],
        "profit": p["profit"],
        "loss": p["loss"],
        "spot": p["info"],
        "strike": p["warn"],
        "axis": p["muted"],
        "grid": p["line"],
        "tooltip_bg": p["surface"],
        "tooltip_border": p["line-strong"],
        "font": SANS,
    }
