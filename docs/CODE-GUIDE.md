# Code guide

A map of the project: **what each file does** and **in which order to read them**.

---

## Architecture in one sentence

The project has two halves that never mix: a **pricing engine** (`pricing/`) that is pure
mathematics, and an **interface** (`app/`) that draws web pages. `app` imports `pricing`;
`pricing` does not even know `app` exists.

```
pricing/  →  mathematics. Not a single line of interface code.
app/      →  interface. No financial maths of its own.
tests/    →  checks for the engine and the app logic (no internet needed).
```

The split is not cosmetic: it is what makes the engine testable on its own, usable from a
Jupyter notebook, and replaceable without touching the maths.

---

## Reading order

### Part 1 — The engine (`src/options_simulator/pricing/`)

| # | File | What it does |
|---|------|--------------|
| 1 | `types.py` | Every **data type** of the project: what a leg is, what market parameters are, what the Greeks are. No calculations: it is the vocabulary all other modules use. Also holds the unit conventions. |
| 2 | `normal.py` | The **density** and **cumulative distribution** of the standard normal, used by Black-Scholes. Built so that `N(x) + N(−x) = 1` holds exactly. |
| 3 | `black_scholes.py` | The **closed formula** pricing a European option and its Greeks. One direct calculation, no loops. |
| 4 | `binomial.py` | The **binomial tree**: prices American options by walking every possible price path. The heaviest computation, vectorised with NumPy. |
| 5 | `implied.py` | **Implied volatility**: pricing in reverse. Given an observed price, bisection finds the IV that reproduces it, with either model. |
| 5b | `merton.py` | **Merton jump-diffusion**: European prices with sudden jumps (a Poisson-weighted sum of Black-Scholes prices, vectorised over the chain) and the calibration that fits the jump parameters to market prices. |
| 6 | `greeks.py` | The **dispatcher**: picks Black-Scholes or the tree, caches results, and sums the Greeks over all legs. |
| 7 | `payoff.py` | The position's **profit and loss**: value at expiry, break-evens, extremes, probability of profit, real trade cost. |
| 8 | `pricing/__init__.py` | The package's **public surface**: lists what can be used from outside. No logic. |

### Part 2 — The tests (`tests/`)

| # | File | What it checks |
|---|------|----------------|
| 9 | `helpers.py` | **Shortcuts** for writing tests: compact builders for legs, markets and specs. Not a test itself. |
| 10 | `test_normal.py` | The normal distribution is accurate and **symmetric**. |
| 11 | `test_black_scholes.py` | Prices, Greeks and structural relations of the closed formula, plus edge cases. |
| 12 | `test_binomial.py` | The tree **converges** to Black-Scholes and early exercise behaves. |
| 13 | `test_payoff.py` | Whole strategies: bear put spread, iron condor, collar, trade cost, probability of profit. |
| 14 | the other `test_*.py` | Merton (against Black-Scholes, parity and Monte Carlo), app logic: carry, market data parsing, portfolio, saved positions, scenarios, theme, tickers, volatility, translations. |

### Part 3 — The interface (`src/options_simulator/app/`)

| # | File | What it does |
|---|------|--------------|
| 15 | `i18n.py`, `lang_en.py` | The **language**: `tr()` returns every sentence in Italian or English; the English dictionary lives in `lang_en.py`, keyed by the Italian sentence. |
| 16 | `formatting.py` | Turns numbers and dates into **readable text** in the chosen language: `1.234,50` in Italian, `1,234.50` in English. |
| 17 | `strategies.py` | The **prebuilt strategies** (bull call spread, iron condor…). Each is a recipe that builds the legs from a price. |
| 18 | `state.py` | The **position state**: everything the user can change, plus `compute()`, which derives every number in one go. The bridge between interface and engine. |
| 19 | `context.py` | The **refresh mechanism**: moving a slider recomputes once, not once per panel. |
| 20 | `widgets.py` | **Reusable UI pieces**: throttled slider, figure tiles, card headers, stock search box, price notice. |
| 21 | `theme.py` | The **visual theme**: dark and light colours as CSS variables, the six accent colours, fonts, component tweaks, chart colours. |
| 22 | `chart.py` | The **chart configuration** for the payoff diagram and the P&L map. Produces a dictionary only. |
| 23 | `panels/` | The simulator **panels**, one per file: `market.py`, `strategy.py`, `legs.py`, `summary.py`, `chart_controls.py`, `positions.py`, `greeks.py`, `scenario.py`, `heatmap.py`, `costs.py`. Each reads ready-made numbers. |
| 24 | `auth.py` | **Accounts and passwords**: creation, verification, secure hashing, browser session, permissions, migration of old data files. |
| 25 | `session.py` | Each user's **position**, kept between pages, and the server counters. |
| 26 | `saved.py` | **Saved positions**: position ↔ JSON, stored in `~/.options-simulator/positions.json`, plus file export and import. |
| 27 | `tickers.py` | The **stock catalogue** used by the search box, and the single rule for spelling symbols (`_SPX` / `SPX`). |
| 28 | `market_data.py` | **Real options**: downloads a US stock's chain from CBOE, parses it, compares market and model prices, and builds a simulator position from picked options. |
| 29 | `carry.py` | **Rate and dividend from prices** via put-call parity, and the call/put check. |
| 29b | `jumps.py` | Picks the out-of-the-money quotes of one expiry and calibrates Merton on them, for the «Model vs market» tab. |
| 30 | `volatility.py` | **Historical against implied volatility**: price history from CBOE, realised volatility, the expensive/cheap verdict. |
| 31 | `portfolio.py` | The **virtual portfolio**: positions at real prices, the model's forecast, daily revaluation, closing at bid/ask, forecasts against outcomes. |
| 32 | `layout.py` | The **shared frame**: sidebar, page title, notices, login page frame. |
| 33 | `pages/simulator.py` | The **simulator page** (`/`). |
| 34 | `pages/market/` | The **real options page** (`/market`), one module per tab plus `page.py`, `basket.py` and `view.py`. |
| 35 | `pages/portfolio_page.py` | The **portfolio page** (`/portfolio`). |
| 36 | `pages/guide.py`, `pages/guide_en.py` | The **user guide** (`/guide`), in Italian and English. The text is data, not code. |
| 37 | `pages/access.py` | **Login, sign-up and settings** (`/login`, `/signup`, `/settings`). |
| 38 | `pages/report.py` | The **printable summary** (`/print`), saved as PDF through the browser. |
| 39 | `pages/admin.py` | The **administration page** (`/admin`): server, users, sessions, cache. |
| 40 | `pages/__init__.py` | **Registers the routes**: importing the page modules is what makes the URLs exist. |
| 41 | `app/main.py` | **Starts the server**. |

### Part 4 — Configuration

| File | What it does |
|------|--------------|
| `pyproject.toml` | Project metadata, dependencies, and the pytest, mypy and ruff configuration. |
| `uv.lock` | The **exact versions** of every installed library. Generated, never edited by hand. |
| `.github/workflows/ci.yml` | The checks GitHub runs on every push: lint, formatting, types, tests. |
| `start-simulator.bat` | Windows launcher: starts the server without a window, or just opens the browser if it is already running. |
| `.gitignore`, `.gitattributes` | What git ignores, and line-ending rules. |

---

## Python features worth noticing, and where

| Feature | Where to see it |
|---------|-----------------|
| Frozen dataclasses with `slots` | `pricing/types.py` |
| `Literal` types instead of enums | `pricing/types.py` |
| Structural pattern matching (`match` / `case`) | `pricing/payoff.py` |
| NumPy vectorisation and slicing tricks | `pricing/binomial.py`, `pricing/normal.py` |
| `functools.lru_cache` on a frozen dataclass | `pricing/greeks.py` |
| `itertools.pairwise` | `pricing/payoff.py`, `app/volatility.py` |
| PEP 695 generics (`def f[E: ...]`) | `app/widgets.py` |
| `@contextmanager` for page frames | `app/layout.py` |
| `@ui.refreshable` panels and a single recompute | `app/context.py` |
| `asyncio` work off the UI loop (`run.io_bound`) | `app/pages/market/page.py` |
| Constant-time password comparison (`hmac.compare_digest`) | `app/auth.py` |
| AST-based test over the source code | `tests/test_i18n.py` |

---

## Where to change things

- change a formula → `pricing/black_scholes.py` or `pricing/binomial.py`
- add a strategy → `app/strategies.py` (and its English name in `app/lang_en.py`)
- change how a panel looks → its file in `app/panels/`
- add a page → a module in `app/pages/` plus an entry in `app/layout.py`
- change the user guide → `app/pages/guide.py` and `app/pages/guide_en.py`
- add a new interface sentence → write it as `tr("...")` and add the English version to
  `app/lang_en.py` (`tests/test_i18n.py` reports any that are missing)
