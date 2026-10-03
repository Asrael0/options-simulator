# Guida al codice

Questo documento è la mappa del progetto. Dice **cosa fa esattamente ogni file** e in **che
ordine leggerli** per imparare Python partendo da zero.

## Come usare questa guida

Il codice è commentato secondo una regola precisa: **ogni concetto di Python è spiegato una
volta sola**, nel primo file in cui compare seguendo l'ordine di lettura qui sotto. Quando lo
stesso costrutto ricompare altrove, il commento non si ripete — al massimo c'è un rimando.

Quindi: **leggi i file nell'ordine indicato**. Se salti al file 12 senza aver letto il 3,
troverai costrutti già dati per acquisiti.

Alla fine c'è l'**indice dei concetti**: se ti imbatti in qualcosa che non capisci, cerca lì in
quale file è spiegato.

---

## Architettura in una frase

Il progetto ha due metà che non si mescolano mai: un **motore di calcolo** (`pricing/`) che è
matematica pura, e un'**interfaccia** (`app/`) che disegna pagine web. `app` importa `pricing`;
`pricing` non sa nemmeno che `app` esista.

```
pricing/  →  matematica. Nessuna riga di interfaccia.
app/      →  interfaccia. Nessuna riga di matematica.
tests/    →  verifica del motore.
```

Questa separazione non è estetica: è ciò che rende il motore testabile da solo, usabile da un
notebook Jupyter, e sostituibile senza toccare la matematica.

---

## Ordine di lettura

### Parte 1 — Il motore (`src/simulatore_opzioni_python/pricing/`)

| # | File | Cosa fa esattamente |
|---|------|---------------------|
| 1 | `types.py` | Definisce **tutti i tipi di dato** del progetto: cos'è una gamba, cosa sono i parametri di mercato, cosa sono le greche. Non calcola nulla. È il vocabolario che tutti gli altri file usano. |
| 2 | `normal.py` | Due funzioni matematiche: la **densità** e la **funzione di ripartizione** della distribuzione normale. Servono a Black-Scholes. Sono l'unico posto dove si approssima qualcosa. |
| 3 | `black_scholes.py` | La **formula chiusa** che prezza un'opzione europea e ne calcola le greche. Un calcolo diretto, senza cicli. |
| 4 | `binomial.py` | L'**albero binomiale**: prezza opzioni americane simulando tutti i percorsi possibili del prezzo. È il file computazionalmente più pesante e quello dove NumPy conta davvero. |
| 5 | `greeks.py` | Il **selettore**: decide se usare Black-Scholes o l'albero, tiene una cache dei risultati, e somma le greche di tutte le gambe. |
| 6 | `payoff.py` | Il **profitto e perdita** della posizione: quanto vale a scadenza, dove sono i break-even, quali sono gli estremi, quanto costa davvero l'operazione. |
| 7 | `pricing/__init__.py` | La **vetrina** del pacchetto: elenca cosa è utilizzabile dall'esterno. Non contiene logica. |

### Parte 2 — I test (`tests/`)

| # | File | Cosa fa esattamente |
|---|------|---------------------|
| 8 | `helpers.py` | **Scorciatoie** per scrivere i test: costruttori compatti di gambe, mercati e specifiche. Non è un test. |
| 9 | `test_normal.py` | Verifica che la funzione normale sia accurata e **simmetrica**. La simmetria è la proprietà che rende esatta la put-call parity. |
| 10 | `test_black_scholes.py` | Verifica prezzi, greche e relazioni strutturali della formula chiusa, più i casi limite. |
| 11 | `test_binomial.py` | Verifica che l'albero **converga** a Black-Scholes e che l'esercizio anticipato funzioni. |
| 12 | `test_payoff.py` | Verifica le strategie complete: bear put spread, iron condor, collar, costo dell'operazione. |

### Parte 3 — L'interfaccia (`src/simulatore_opzioni_python/app/`)

| # | File | Cosa fa esattamente |
|---|------|---------------------|
| 13 | `formatting.py` | Trasforma numeri in **testo leggibile all'italiana**: `1234.5` diventa `1.234,50`. Nient'altro. |
| 14 | `strategies.py` | L'elenco delle **strategie precostruite** (bull call spread, iron condor…). Ognuna è una ricetta che, dato un prezzo, costruisce le gambe. |
| 15 | `state.py` | Lo **stato della posizione**: tutto ciò che l'utente può modificare, più la funzione che ricalcola i valori derivati. È il ponte fra interfaccia e motore. |
| 16 | `context.py` | Il **meccanismo di aggiornamento**: garantisce che muovendo uno slider il calcolo avvenga una volta sola, non una per pannello. |
| 17 | `widgets.py` | **Pezzetti visivi riutilizzabili**: uno slider che non intasa il server, un riquadro con una cifra, l'intestazione delle card con icona. |
| 18 | `theme.py` | Il **tema grafico**: i colori del tema scuro e di quello chiaro (come variabili CSS), i caratteri, i ritocchi ai componenti e i colori del grafico. Per cambiare l'aspetto del sito si parte da qui. |
| 19 | `chart.py` | Costruisce la **configurazione del grafico** di payoff. Produce solo un dizionario: non disegna nulla e non calcola nulla. |
| 20 | `panels.py` | I **pannelli** dell'interfaccia: mercato, strategie, gambe, riepilogo, greche, vol crush, scenario, costi. Ognuno legge i numeri già pronti. |
| 21 | `auth.py` | **Account e password**: creazione, verifica, hashing sicuro, sessione del browser, controllo dei permessi. |
| 22 | `session.py` | La **posizione di ogni utente**, conservata fra una pagina e l'altra. Senza questo file, cambiando pagina si ripartirebbe da zero. |
| 23 | `saved.py` | Le **posizioni salvate**: trasforma una posizione in testo (JSON) e ritorno, e la conserva in `~/.simulatore-opzioni/posizioni.json`, separata per utente. |
| 24 | `layout.py` | La **cornice comune**: barra laterale con la navigazione e il pulsante del tema, titolo della pagina, avvisi. Garantisce che ogni pagina abbia lo stesso contorno. |
| 25 | `pages/simulator.py` | La **pagina del simulatore**: la posizione sempre in vista e, sotto il grafico, le schede Greche, Scenari, Costi e Come si legge. |
| 26 | `pages/access.py` | Le pagine di **accesso, registrazione e cambio password**. |
| 27 | `pages/guide.py` | La **guida per l'utente** (non per il programmatore): 16 sezioni che spiegano le opzioni. Il testo è dati, non codice. |
| 28 | `pages/report.py` | Il **riepilogo stampabile** (`/stampa`): pagina in tema chiaro con mercato, gambe, numeri chiave, grafico e greche, da salvare in PDF con la stampa del browser. |
| 29 | `pages/admin.py` | Il **pannello di amministrazione**: stato del server, utenti, sessioni, cache. |
| 30 | `pages/__init__.py` | **Registra le rotte**. Importare questi moduli è ciò che fa esistere gli indirizzi web. |
| 31 | `app/main.py` | **Avvia il server**. Poche righe, ma è il punto d'ingresso. |
| 32 | `app/__init__.py` | Espone `main`, il punto d'ingresso usato da `uv run simulatore-opzioni`. |
| 33 | `simulatore_opzioni_python/__init__.py` | Radice del pacchetto: contiene solo il numero di versione e l'avviso didattico. |

### Parte 4 — Configurazione

| File | Cosa fa esattamente |
|------|---------------------|
| `pyproject.toml` | **Carta d'identità del progetto**: nome, dipendenze, e configurazione di pytest, mypy e ruff. Non è Python: è un formato di configurazione. |
| `uv.lock` | Le **versioni esatte** di ogni libreria installata. Generato automaticamente, non si modifica a mano. |
| `.gitignore` | Elenco di ciò che git deve **ignorare** (l'ambiente virtuale, i file temporanei). |
| `README.md` | Presentazione del progetto e istruzioni d'uso. |
| `docs/GUIDA-AL-CODICE.md` | Questo documento. |

---

## Indice dei concetti di Python

Se incontri un costrutto che non riconosci, qui trovi dov'è spiegato.

### Fondamenta

| Concetto | Spiegato in |
|----------|-------------|
| Docstring (il testo fra `"""` a inizio file o funzione) | `types.py` |
| `import` e `from … import …` | `types.py` |
| `from __future__ import annotations` | `types.py` |
| Annotazioni di tipo (`x: float`, `-> str`) | `types.py` |
| Alias di tipo (`Side = Literal[...]`) | `types.py` |
| `Literal["call", "put"]` | `types.py` |
| Union con `\|` e `None` | `types.py` |
| `@dataclass`, `frozen`, `slots` | `types.py` |
| Valori di default nei campi | `types.py` |
| Costanti in MAIUSCOLO | `types.py` |
| Il commento `#:` per documentare | `types.py` |
| Definire una funzione (`def`) | `types.py` |
| `dict`, `list`, `set` | `types.py` |

### Calcolo e strutture di controllo

| Concetto | Spiegato in |
|----------|-------------|
| `import numpy as np` e cos'è un array | `normal.py` |
| Operazioni su interi array in un colpo solo | `normal.py` |
| `np.where` (l'`if` per gli array) | `normal.py` |
| `import math` e la libreria standard | `black_scholes.py` |
| `if` / `elif` / `else` | `black_scholes.py` |
| Uscita anticipata (`return` presto) | `black_scholes.py` |
| Operatori booleani `or`, `and`, `not` | `black_scholes.py` |
| `max()` e `min()` | `black_scholes.py` |
| Underscore iniziale (`_funzione_privata`) | `black_scholes.py` |
| `for` e `range()` | `binomial.py` |
| `range` all'indietro | `binomial.py` |
| Funzione dentro una funzione (closure) | `binomial.py` |
| Slicing di liste e array (`[1:]`, `[:-1]`, `[::-2]`) | `binomial.py` |
| Assegnazione multipla (`a = b = 0`, `a, b = 1, 2`) | `binomial.py` |
| Decoratori (`@qualcosa`) | `greeks.py` |
| `@lru_cache` e la memoizzazione | `greeks.py` |
| Argomenti con valore di default | `greeks.py` |
| `match` / `case` (pattern matching) | `payoff.py` |
| List comprehension (`[x for x in …]`) | `payoff.py` |
| Set comprehension e `sorted()` | `payoff.py` |
| `sum()` con un generatore | `payoff.py` |
| `enumerate()` | `payoff.py` |
| `math.inf` (infinito) | `payoff.py` |
| Spacchettamento con `*` in una lista | `payoff.py` |

### Pacchetti e test

| Concetto | Spiegato in |
|----------|-------------|
| Cos'è un pacchetto e a cosa serve `__init__.py` | `pricing/__init__.py` |
| Import relativi (`.types`, `..pricing`) | `pricing/__init__.py` |
| `__all__` | `pricing/__init__.py` |
| `itertools.count` e `next()` | `tests/helpers.py` |
| `**overrides` (argomenti a nome variabile) | `tests/helpers.py` |
| `dataclasses.replace()` | `tests/helpers.py` |
| Come si scrive un test (`assert`) | `test_normal.py` |
| Classi come raggruppamento (`class TestQualcosa`) | `test_normal.py` |
| `pytest.approx` e i confronti fra numeri decimali | `test_normal.py` |
| `zip(..., strict=True)` | `test_normal.py` |
| `@pytest.fixture` | `test_payoff.py` |
| `itertools.pairwise` | `test_binomial.py` |

### Testo, oggetti e funzioni avanzate

| Concetto | Spiegato in |
|----------|-------------|
| Stringhe, f-string e mini-formati (`:,.2f`) | `formatting.py` |
| `str.replace()` e le catene di metodi | `formatting.py` |
| `lambda` (funzione senza nome) | `strategies.py` |
| `Callable` (una funzione come valore) | `strategies.py` |
| Dataclass **mutabile** e metodi | `state.py` |
| `self` | `state.py` |
| `field(default_factory=…)` | `state.py` |
| `isinstance()` | `state.py` |
| `**kwargs` in una firma | `state.py` |
| `any()` e `all()` | `state.py` |
| `class` scritta a mano, `__init__` | `context.py` |
| `functools.partial` | `context.py` |
| Riferimento in avanti nei tipi (`"PageContext"`) | `context.py` |
| Parametri solo-per-nome (`*` nella firma) | `widgets.py` |
| `dict.get()` con valore di ripiego | `widgets.py` |
| Operatore ternario (`a if cond else b`) | `chart.py` |
| Dizionari annidati | `chart.py` |
| Il trucco `lambda e, i=valore:` per catturare una variabile | `panels.py` |
| `try` / `except` e le eccezioni | `auth.py` |
| `pathlib.Path` | `auth.py` |
| `json.loads` / `json.dumps` | `auth.py` |
| `hashlib`, `secrets`, `hmac` | `auth.py` |
| `**data` per costruire un oggetto da un dizionario | `auth.py` |
| `datetime` e i fusi orari | `auth.py` |
| Stato a livello di modulo | `session.py` |
| `sorted(key=lambda …)` | `session.py` |
| `@contextmanager` e `yield` | `layout.py` |
| `with` con più oggetti | `layout.py` |
| Decoratore con argomenti (`@ui.page("/")`) | `pages/simulator.py` |
| Import eseguito per il suo effetto | `pages/__init__.py` |
| `# noqa` (zittire il linter) | `pages/__init__.py` |
| `if __name__ == "__main__"` | `app/main.py` |

---

## Da dove comincio, in pratica

Se vuoi solo **usare** l'applicazione: leggi il `README.md` e basta.

Se vuoi **capire il codice**: parti da `types.py` e vai in ordine. I primi sette file sono
matematica e strutture dati — è la parte dove si impara Python "puro", senza framework. La parte
sull'interfaccia (dal 13 in poi) richiede di accettare che NiceGUI faccia delle cose per magia;
è normale, e il file `context.py` spiega dov'è la magia.

Se vuoi **modificare qualcosa**:

- cambiare una formula → `black_scholes.py` o `binomial.py`
- aggiungere una strategia → `strategies.py`
- cambiare l'aspetto di un pannello → `panels.py`
- aggiungere una pagina → un file in `pages/` più una voce in `layout.py`
- cambiare il testo della guida per l'utente → `pages/guide.py`
