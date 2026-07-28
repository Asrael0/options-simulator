# Simulatore di Opzioni — versione Python

Motore di pricing per opzioni: Black-Scholes-Merton, albero binomiale CRR, greche e payoff
multi-gamba. Python puro, verificato da 84 test.

> **Nota didattica.** I prezzi sono _teorici_: i modelli assumono volatilità costante e assenza
> di salti di prezzo (gap), quindi divergono dai prezzi reali di mercato. Lo strumento serve a
> capire le relazioni tra le variabili, non a stimare prezzi di trading, e **non costituisce
> consulenza finanziaria**.

---

## Comandi

Non serve installare Python né creare ambienti a mano: `uv` fa tutto da solo la prima volta.

```bash
uv run pytest
```

| Comando                 | Cosa fa                                            |
| ----------------------- | -------------------------------------------------- |
| `uv run pytest`         | Esegue gli 84 test                                 |
| `uv run pytest -v`      | Come sopra, elencando ogni test per nome           |
| `uv run mypy src tests` | Controlla i tipi in modalità strict                |
| `uv run ruff check .`   | Lint                                               |
| `uv run ruff format .`  | Formatta il codice                                 |
| `uv run python`         | Apre l'interprete col pacchetto già importabile    |

---

## Struttura

```
src/simulatore_opzioni_python/
  pricing/
    types.py           Dataclass, Literal, convenzioni di unità
    normal.py          N(x) e phi(x) ad alta precisione, vettorizzate
    black_scholes.py   Formule chiuse per le europee
    binomial.py        Albero CRR vettorizzato con NumPy
    greeks.py          Dispatch, cache, greche di posizione
    payoff.py          P&L multi-gamba, break-even, estremi, costo
tests/
    test_normal.py  test_black_scholes.py  test_binomial.py  test_payoff.py
```

Il pacchetto `pricing` **non importa nulla dall'interfaccia**. È testabile in isolamento,
usabile da un notebook Jupyter e riutilizzabile da qualunque frontend.

---

## Convenzioni di unità

Sono la fonte più probabile di errori, quindi vivono nei **nomi**, non nei commenti:

- Tassi e volatilità sono **sempre decimali**. IV 30% ⇒ `0.30`. La percentuale esiste solo dove
  si mostrano i numeri all'utente.
- Il motore lavora **per unità di sottostante**. `qty` è un moltiplicatore puro; il
  moltiplicatore di contratto e il numero di pacchetti entrano soltanto in `trade_cost()`.
- `theta_per_day` è in valuta **al giorno**; `vega_per_point` e `rho_per_point` sono per **+1
  punto** (cioè +0.01 decimale). Non per anno e non per +1.00.

---

## Scelte di Python che vale la pena riconoscere

Il codice è commentato anche dal punto di vista del linguaggio, non solo della finanza. I punti
principali:

**`@dataclass(frozen=True, slots=True)`** — `frozen` rende gli oggetti immutabili: una gamba non
può cambiare sotto i piedi a chi la sta usando, e per modificarla si usa `dataclasses.replace()`,
che ne restituisce una copia. `slots` elimina il dizionario di istanza: meno memoria e accessi
più rapidi.

**Union discriminata con `match`** — `Leg = OptionLeg | StockLeg`, e il codice la distingue con
il pattern matching strutturale di Python 3.10+:

```python
match leg:
    case StockLeg():
        return final_spot
    case OptionLeg(right="call", strike=strike):
        return max(final_spot - strike, 0.0)
    case OptionLeg(strike=strike):
        return max(strike - final_spot, 0.0)
```

Rispetto a una catena di `isinstance` legge meglio, permette di destrutturare i campi dentro il
pattern, e mypy restringe i tipi ramo per ramo. Il prezzo di carico dell'azione si chiama
`entry_price`, non `strike`: non è uno strike travestito e non entra in nessuna formula.

**`Literal["call", "put"]` invece di `Enum`** — i valori sono già stringhe parlanti, e mypy
verifica comunque che non se ne usino altre. Attenzione a una trappola: `EUROPEAN = "european"`
viene inferito come `str` generico e non è più accettato dove serve un `Literal`. Serve
l'annotazione esplicita: `EUROPEAN: ExerciseStyle = "european"`.

**`functools.lru_cache` sulla dataclass** — funziona perché `OptionSpec` è `frozen`, quindi
hashabile: i parametri **sono** la chiave, senza doverla costruire a mano concatenando stringhe.

**`itertools.pairwise`** — per confrontare ogni elemento col precedente. `zip(xs, xs[1:])` fa lo
stesso ma è più rumoroso, e con `strict=True` è addirittura un errore, perché le due sequenze
hanno lunghezze diverse per costruzione.

**mypy in modalità strict** — è l'equivalente Python di `"strict": true` in TypeScript. Non è
obbligatorio in Python, ma su codice numerico dove `theta` per anno e `theta` per giorno sono
entrambi `float`, i tipi sono l'unica rete di sicurezza che resta.

---

## Perché NumPy non è un opzionale

Un albero binomiale a N passi ha O(N²) nodi. Con N = 140 sono circa diecimila valutazioni: in
JavaScript un doppio ciclo le esegue in frazioni di millisecondo, **in Python puro sarebbe circa
cento volte più lento**.

La soluzione non è "scrivere Python più veloce" ma cambiare la forma del calcolo: un intero
_livello_ dell'albero diventa un array, e l'induzione all'indietro diventa **una** operazione
vettoriale per livello. Si passa da O(N²) iterazioni interpretate a O(N) chiamate NumPy, ognuna
eseguita in C.

La riga che fa tutto il lavoro è questa:

```python
val = discount * (p_up * val[:-1] + p_down * val[1:])
```

`val[:-1]` sono i figli "su", `val[1:]` i figli "giù". Uno slittamento di un indice esprime
l'intera struttura ad albero. È il modo di pensare che NumPy richiede, e vale la pena
interiorizzarlo: quasi tutto il calcolo numerico in Python funziona così.

---

## Verifica

84 test su quattro file, che coprono la tabella di riferimento — prezzi ATM, greche, put-call
parity, convergenza binomiale, premio di esercizio anticipato, bear put spread, iron condor,
collar, costo dell'operazione — più robustezza su `T = 0`, `IV → 0`, strike lontani dallo spot,
quantità elevate, spot nullo, scadenze decennali.

Alcuni test valgono più di un controllo numerico:

- **Simmetria di `norm_cdf`.** `N(x) + N(−x) = 1` a precisione macchina _per costruzione_: è
  questa proprietà, non l'accuratezza, a rendere esatta la put-call parity.
- **Call americana ≡ europea.** Il confronto è binomiale contro binomiale ed è bit per bit:
  senza dividendi il `max(continuazione, esercizio)` non morde in nessun nodo. Contro
  Black-Scholes resterebbe la discretizzazione e il test fallirebbe a torto.
- **Gamma liscio.** Delta, gamma e theta si leggono dai livelli 1 e 2 dell'albero invece che per
  differenze finite, che dividendo per `h²` amplificano il sawtooth del CRR in un jitter del ~2%.
- **Premio congelato.** `resolve_legs()` risolve i premi **una volta** contro un `MarketParams`
  esplicito: il costo già pagato non cambia quando il mercato si muove.

### Concordanza con la versione TypeScript

Esiste una seconda implementazione dello stesso motore in TypeScript, in
`../simulatore-opzioni/`. Concordano su ogni valore fino a 1e-6:

| Valore                       | TypeScript            | Python                |
| ---------------------------- | --------------------- | --------------------- |
| Call ATM                     | 3.591123              | 3.591123              |
| Put ATM                      | 3.262896              | 3.262896              |
| Delta / Gamma                | 0.532370 / 0.046232   | 0.532370 / 0.046232   |
| Vega / Theta                 | 0.113996 / −0.062439  | 0.113996 / −0.062439  |
| Binomiale europeo, 500 passi | 3.589410              | 3.589410              |
| Put americana ITM            | 20.000000             | 20.000000             |
| Bear put spread: costo / BE  | 2.862338 / 97.137662  | 2.862338 / 97.137662  |
| Iron condor: credito / ala   | 2.693222 / −7.306778  | 2.693222 / −7.306778  |
| Collar: floor / cap          | −9.385751 / 10.614249 | −9.385751 / 10.614249 |
| Costo operazione, netto      | 1467.9620             | 1467.9620             |

Due implementazioni indipendenti in linguaggi diversi che concordano è l'evidenza più forte
disponibile su un motore finanziario: un errore avrebbe dovuto essere commesso due volte allo
stesso modo.

---

## Stato

Il motore è completo e verificato. **L'interfaccia grafica non c'è ancora.**

I browser eseguono JavaScript e WebAssembly, non Python, quindi un'interfaccia web in Python
richiede una scelta esplicita fra un framework con server (NiceGUI, Reflex) e l'esecuzione di
Python nel browser via WebAssembly (Pyodide), che costa alcuni megabyte di download. È la
prossima decisione da prendere.

---

## Se il progetto vive su OneDrive

`.venv` e la sincronizzazione continua non vanno d'accordo: durante `uv run` può capitare un
`Accesso negato (os error 5)` perché OneDrive tiene aperto un file. Di solito basta ripetere il
comando. Per eliminarlo del tutto, escludi `.venv` dalla sincronizzazione dalle impostazioni di
OneDrive.
