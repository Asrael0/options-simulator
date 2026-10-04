"""English translations: Italian text (the key used in the code) -> English text.

Placeholders such as ``{n}`` or ``{symbol}`` must stay the same on both sides:
``tests/test_i18n.py`` checks it, and checks that every ``tr()`` key is here.
"""

from __future__ import annotations

EN: dict[str, str] = {
    # --- Navigation and layout ---
    "Simulatore": "Simulator",
    "Opzioni reali": "Real options",
    "Portafoglio": "Portfolio",
    "Portafoglio virtuale": "Virtual portfolio",
    "Guida": "Guide",
    "Amministrazione": "Administration",
    "Impostazioni": "Settings",
    "Strumenti": "Tools",
    "Gestione": "Management",
    "Esci": "Log out",
    "Spegni simulatore": "Shut down simulator",
    "Spegnere il simulatore?": "Shut down the simulator?",
    "Spegni": "Shut down",
    "Annulla": "Cancel",
    "Simulatore spento. Puoi chiudere questa scheda.": (
        "Simulator shut down. You can close this tab."
    ),
    "Il sito smette di funzionare finché non lo riavvii dal collegamento sul desktop. "
    "Le posizioni salvate restano; quella aperta, se non l'hai salvata, si perde.": (
        "The site stops working until you restart it from the desktop shortcut. "
        "Saved positions are kept; the open one is lost if you have not saved it."
    ),
    "Prezzi teorici · dati reali da CBOE": "Theoretical prices · real data from CBOE",
    "Password admin predefinita: va bene in locale, cambiala prima di rendere il sito "
    "raggiungibile da altri.": (
        "Default admin password: fine locally, change it before making the site "
        "reachable by others."
    ),
    "Cambiala": "Change it",
    "amministratore": "administrator",
    "utente": "user",
    "Capire le opzioni, una variabile alla volta.": (
        "Understanding options, one variable at a time."
    ),
    "Black-Scholes e albero binomiale": "Black-Scholes and binomial tree",
    "Europee e americane, a confronto.": "European and American, side by side.",
    "Greche e scenari": "Greeks and scenarios",
    "Delta, gamma, theta, vega e vol crush.": "Delta, gamma, theta, vega and vol crush.",
    "Pensato per imparare": "Built for learning",
    "Ogni numero ha la sua spiegazione.": "Every number comes with an explanation.",
    # --- Formatting and common terms ---
    "illimitato": "unlimited",
    "illimitata": "unlimited",
    "g": "d",
    "Long": "Long",
    "Short": "Short",
    "Call": "Call",
    "Put": "Put",
    "call": "call",
    "put": "put",
    "Azione": "Stock",
    "europea": "European",
    "americana": "American",
    "europee": "European",
    "americane": "American",
    "europeo": "European",
    "americano": "American",
    "Europea": "European",
    "Americana": "American",
    # --- Theme, colours, language ---
    "Automatico": "Automatic",
    "Chiaro": "Light",
    "Scuro": "Dark",
    "Terracotta": "Terracotta",
    "Blu": "Blue",
    "Viola": "Purple",
    "Verde": "Green",
    "Rosso": "Red",
    "Ambra": "Amber",
    # --- Login and settings ---
    "Accedi": "Log in",
    "Registrati": "Sign up",
    "Serve un account per usare il simulatore.": "You need an account to use the simulator.",
    "Crea un account": "Create an account",
    "Crea account": "Create account",
    "Non hai un account?": "Don't have an account?",
    "Hai già un account?": "Already have an account?",
    "Account creato: ora puoi accedere": "Account created: you can now log in",
    "Nome utente": "Username",
    "Password": "Password",
    "Ripeti la password": "Repeat the password",
    "Nome utente o password non corretti.": "Wrong username or password.",
    "Primo avvio: esiste già un account amministratore con nome utente «admin» e password "
    "«admin». Cambiala dalla pagina Impostazioni.": (
        "First start: there is already an administrator account with username «admin» "
        "and password «admin». Change it from the Settings page."
    ),
    "Aspetto e lingua": "Appearance and language",
    "Lingua": "Language",
    "Tema": "Theme",
    "Colore": "Colour",
    "«Automatico» segue il tema di Windows.": "«Automatic» follows the Windows theme.",
    "Le scelte restano salvate in questo browser.": "Your choices stay saved in this browser.",
    "Lingua, aspetto, posizioni salvate e dati del tuo accesso": (
        "Language, appearance, saved positions and your account details"
    ),
    "Posizioni salvate": "Saved positions",
    "Eliminata «{name}»": "Deleted «{name}»",
    "Questa posizione salvata è danneggiata": "This saved position is damaged",
    "{len} su {max_per_user} disponibili": "{len} of {max_per_user} available",
    "Non hai ancora salvato nessuna posizione. Nel simulatore, il riquadro «Le mie "
    "posizioni» ha il pulsante «Salva».": (
        "You have not saved any position yet. In the simulator, the «My positions» box "
        "has the «Save» button."
    ),
    "Nome": "Name",
    "Sottostante": "Underlying",
    "Stile": "Style",
    "Salvata il": "Saved on",
    "Apri nel simulatore": "Open in the simulator",
    "Elimina": "Delete",
    "Cambia password": "Change password",
    "Password attuale": "Current password",
    "Nuova password": "New password",
    "Ripeti la nuova password": "Repeat the new password",
    "Aggiorna password": "Update password",
    "Password aggiornata": "Password updated",
    "Dati dell'account": "Account details",
    "Ruolo": "Role",
    "Creato il": "Created on",
    "Questo account usa ancora la password predefinita.": (
        "This account still uses the default password."
    ),
    "Le password non vengono mai salvate in chiaro: il file contiene solo un hash pbkdf2 "
    "con 600.000 iterazioni e un sale casuale diverso per ogni utente.": (
        "Passwords are never stored in plain text: the file only holds a pbkdf2 hash with "
        "600,000 iterations and a different random salt for each user."
    ),
    "Vai al simulatore": "Go to the simulator",
    "{n} gamba": "{n} leg",
    "{n} gambe": "{n} legs",
    # --- Auth messages ---
    "Il nome utente deve avere almeno {n} caratteri.": (
        "The username must be at least {n} characters long."
    ),
    "Il nome utente può contenere solo lettere, numeri, trattini e underscore.": (
        "The username can contain only letters, numbers, hyphens and underscores."
    ),
    "La password deve avere almeno {n} caratteri.": (
        "The password must be at least {n} characters long."
    ),
    "Le due password non coincidono.": "The two passwords do not match.",
    "Questo nome utente è già in uso.": "This username is already taken.",
    "La password attuale non è corretta.": "The current password is wrong.",
    "La nuova password deve avere almeno {n} caratteri.": (
        "The new password must be at least {n} characters long."
    ),
    "Utente non trovato.": "User not found.",
    # --- Administration ---
    "Stato del server, utenti e sessioni": "Server status, users and sessions",
    "Cache svuotata": "Cache cleared",
    "⚠ Un account amministratore usa ancora la password predefinita «admin». Cambiala dalla "
    "pagina «Impostazioni» prima di rendere raggiungibile questa applicazione da altri "
    "computer.": (
        "⚠ An administrator account still uses the default password «admin». Change it "
        "from the «Settings» page before making this application reachable from other "
        "computers."
    ),
    "Server": "Server",
    "Cache del motore di pricing": "Pricing engine cache",
    "Ambiente": "Environment",
    "Utenti registrati ({len})": "Registered users ({len})",
    "Sessioni attive ({len})": "Active sessions ({len})",
    "Aggiorna": "Refresh",
    "I contatori si azzerano a ogni riavvio del server: vivono in memoria, non su disco.": (
        "Counters reset at every server restart: they live in memory, not on disk."
    ),
    "Riguarda solo l'albero binomiale: le europee usano una formula chiusa e non hanno "
    "bisogno di cache.": (
        "Only the binomial tree uses it: European options use a closed formula and need no cache."
    ),
    "Creato": "Created",
    "Nessuna sessione registrata.": "No sessions recorded.",
    "Svuota la cache": "Clear the cache",
    "Password predefinita mai cambiata": "Default password never changed",
    "{symbol} · {legs} ({stock_legs} azionarie) · {style} · spot {spot} · IV {iv} · "
    "{days_to_expiry} gg": (
        "{symbol} · {legs} ({stock_legs} stock) · {style} · spot {spot} · IV {iv} · "
        "{days_to_expiry} d"
    ),
    "sessione {key}… · {page_views} pagine viste": "session {key}… · {page_views} pages viewed",
    "inattivo da {humanize}": "idle for {humanize}",
    "non autenticato": "not logged in",
    "Attivo da": "Up for",
    "Avviato il": "Started on",
    "Pagine servite": "Pages served",
    "Accessi riusciti": "Successful logins",
    "Accessi falliti": "Failed logins",
    "Registrazioni": "Sign-ups",
    "Richieste servite dalla cache": "Requests served from cache",
    "Calcoli eseguiti": "Calculations run",
    "Tasso di riuso": "Reuse rate",
    "Voci in cache": "Cache entries",
    "Versione applicazione": "Application version",
    "Python": "Python",
    "NumPy": "NumPy",
    "NiceGUI": "NiceGUI",
    "Sistema": "System",
    "File degli utenti": "Users file",
    # --- Guide ---
    "Ogni aspetto del simulatore, spiegato": "Every part of the simulator, explained",
    "Una pagina sola, in ordine di lettura. Se è la prima volta, leggila dall'inizio; "
    "altrimenti salta alla voce che ti serve.": (
        "A single page, in reading order. If it is your first time, read it from the "
        "start; otherwise jump to the topic you need."
    ),
    "↑ Torna all'indice": "↑ Back to contents",
    "Indice": "Contents",
    # --- Chart ---
    "Scenario: {parts}": "Scenario: {parts}",
    "fra {days} gg": "in {days} d",
    "Profitto": "Profit",
    "Perdita": "Loss",
    "Valore oggi": "Value today",
    "A scadenza": "At expiry",
    "Oggi se fossero americane": "Today if they were American",
    "Oggi se fossero europee": "Today if they were European",
    "Prezzo del sottostante": "Underlying price",
    "Profitto / Perdita": "Profit / Loss",
    "oggi": "today",
    "scenario {price}": "scenario {price}",
    "Confronto: {name}": "Compare: {name}",
    "scadenza": "expiry",
    "+{days} gg": "+{days} d",
    "profitto max {value}": "max profit {value}",
    "perdita max {value}": "max loss {value}",
    "Prezzo": "Price",
    # --- Simulator page and tabs ---
    "Gambe": "Legs",
    "Greche": "Greeks",
    "Scenari": "Scenarios",
    "Mappa P&L": "P&L map",
    "Costi": "Costs",
    "Legenda": "Legend",
    "Come si legge il grafico": "How to read the chart",
    "Costruisci una posizione e guarda come reagisce a prezzo, tempo e IV.": (
        "Build a position and watch how it reacts to price, time and IV."
    ),
    "La linea bianca è il risultato a scadenza: è la spezzata che conta davvero, perché è il "
    "P&L che realizzi se tieni la posizione fino alla fine. La linea viola tratteggiata è il "
    "valore oggi, alla volatilità corrente: è più liscia perché al valore intrinseco si somma "
    "ancora del valore temporale. Man mano che i giorni passano, la viola scende verso la "
    "bianca.": (
        "The white line is the result at expiry: it is the broken line that really "
        "matters, because it is the P&L you make if you hold the position to the end. The "
        "dashed purple line is the value today, at the current volatility: it is smoother "
        "because some time value is still added to the intrinsic value. As the days go "
        "by, the purple line sinks towards the white one."
    ),
    "L'area verde è profitto, la rossa è perdita, e i confini cadono esattamente sui "
    "break-even. Le linee verticali tratteggiate in arancione sono gli strike, quella blu "
    "continua è il prezzo spot attuale, quelle verdi sono i break-even.": (
        "The green area is profit, the red one is loss, and the borders fall exactly on "
        "the break-evens. The dashed orange vertical lines are the strikes, the solid "
        "blue one is the current spot price, the green ones are the break-evens."
    ),
    "Se sposti lo slider del tempo sopra il grafico, o imposti nella scheda «Scenari» una "
    "data o una IV diverse da oggi, compare la curva terracotta «Scenario»: il valore della "
    "posizione in quel giorno e con quella volatilità. La linea verticale terracotta è il "
    "prezzo dello scenario.": (
        "If you move the time slider above the chart, or set a date or an IV different "
        "from today in the «Scenarios» tab, the terracotta «Scenario» curve appears: the "
        "value of the position on that day and with that volatility. The terracotta "
        "vertical line is the scenario price."
    ),
    # --- Panels: chart controls ---
    "Nessun confronto": "No comparison",
    "Scarica il grafico come immagine": "Download the chart as an image",
    "Riepilogo stampabile / salvabile in PDF": "Printable summary / save as PDF",
    "Ferma": "Stop",
    "Fai scorrere il tempo fino alla scadenza": "Run time forward to expiry",
    "Oggi": "Today",
    "Fra {forward} gg · {strftime}": "In {forward} d · {strftime}",
    "Confronta con": "Compare with",
    # --- Panels: costs ---
    "Costo dell'operazione": "Cost of the trade",
    "{side} azione @ {price}": "{side} stock @ {price}",
    "Esborso (premi/azioni pagati)": "Outlay (premiums/shares paid)",
    "Incasso (premi venduti)": "Income (premiums sold)",
    "Traduce i prezzi teorici in esborso reale. Ogni contratto controlla "
    "{contract_multiplier} unità di sottostante: il costo di una gamba è premio × "
    "moltiplicatore × contratti × pacchetti.": (
        "Turns theoretical prices into real outlay. Each contract controls "
        "{contract_multiplier} units of underlying: the cost of a leg is premium × "
        "multiplier × contracts × packages."
    ),
    "Costo netto totale": "Total net cost",
    "Credito netto totale": "Total net credit",
    "Gamba": "Leg",
    "Prezzo unit.": "Unit price",
    "Unità tot.": "Total units",
    "Flusso": "Cash flow",
    "Le posizioni a credito richiedono in genere un margine presso il broker, non mostrato "
    "qui.": "Credit positions usually require margin at the broker, not shown here.",
    "az.": "sh.",
    "{label} ×{qty}": "{label} ×{qty}",
    "Pacchetti (repliche)": "Packages (replicas)",
    "Moltiplicatore contratto": "Contract multiplier",
    "per {n} pacchetto": "for {n} package",
    "per {n} pacchetti": "for {n} packages",
    # --- Panels: Greeks ---
    "Greche aggregate della posizione": "Aggregate Greeks of the position",
    "Somma delle greche di tutte le gambe, con segno e quantità.": (
        "Sum of the Greeks of all legs, with sign and quantity."
    ),
    "Delta": "Delta",
    "Gamma": "Gamma",
    "Theta": "Theta",
    "Vega": "Vega",
    "Rho": "Rho",
    "$/gg": "$/d",
    "$/1% IV": "$/1% IV",
    "$/1% tasso": "$/1% rate",
    "Variazione del valore della posizione per +1 $ del sottostante. È l'esposizione "
    "direzionale netta.": (
        "Change in the position's value for +$1 in the underlying. It is the net "
        "directional exposure."
    ),
    "Variazione del delta per +1 $ del sottostante. Misura quanto rapidamente cambia "
    "l'esposizione direzionale.": (
        "Change in delta for +$1 in the underlying. It measures how quickly the "
        "directional exposure changes."
    ),
    "Variazione del valore per ogni giorno che passa. Negativo per chi è net long di "
    "opzioni: il tempo erode il premio.": (
        "Change in value for each day that passes. Negative for net option buyers: time "
        "erodes the premium."
    ),
    "Variazione del valore per +1 punto di volatilità implicita. Net short vega guadagna da "
    "un vol crush.": (
        "Change in value for +1 point of implied volatility. Net short vega gains from a vol crush."
    ),
    "Variazione del valore per +1 punto di tasso risk-free. La greca meno rilevante per "
    "scadenze brevi.": (
        "Change in value for +1 point of the risk-free rate. The least relevant Greek "
        "for short expiries."
    ),
    # --- Panels: P&L map ---
    "Mappa del P&L: prezzo × tempo": "P&L map: price × time",
    "Ogni casella è il guadagno o la perdita per unità, se il titolo valesse quel prezzo in "
    "quel giorno (IV e tasso fermi).": (
        "Each cell is the gain or loss per unit if the stock were at that price on that "
        "day (IV and rate unchanged)."
    ),
    # --- Panels: legs ---
    "Gambe della posizione": "Position legs",
    "Ogni riga è un contratto o un'azione": "Each row is a contract or a stock",
    "Costo netto (debito)": "Net cost (debit)",
    "Credito netto incassato": "Net credit received",
    "Aggiungi gamba": "Add leg",
    "Tipo": "Type",
    "Q.tà": "Qty",
    "Premio": "Premium",
    "Per l'azione il costo è il prezzo di carico": "For the stock the cost is the entry price",
    "Rimuovi gamba": "Remove leg",
    "Prezzo di carico dell'azione": "Stock entry price",
    "Premio teorico. Modificalo per imporre un valore manuale.": (
        "Theoretical premium. Edit it to set a manual value."
    ),
    "{title}: {signed_money}": "{title}: {signed_money}",
    "Riporta tutti i premi al teorico": "Reset all premiums to theoretical",
    # --- Panels: market ---
    "Sottostante e mercato": "Underlying and market",
    "Ticker": "Ticker",
    "Stile di esercizio": "Exercise style",
    "gg · scade {date}": "d · expires {date}",
    "Esercitabile solo a scadenza. Prezzata con Black-Scholes-Merton (formula chiusa).": (
        "Exercisable only at expiry. Priced with Black-Scholes-Merton (closed formula)."
    ),
    "Esercitabile in qualsiasi momento. Prezzata con albero binomiale CRR: include il valore "
    "dell'esercizio anticipato, visibile soprattutto sulle put ITM.": (
        "Exercisable at any time. Priced with a CRR binomial tree: it includes the value "
        "of early exercise, visible mostly on ITM puts."
    ),
    "La curva verde acqua usa gli stessi premi pagati: la distanza dalla viola è solo il "
    "valore dell'esercizio anticipato. Per una call senza dividendi le due curve "
    "coincidono.": (
        "The teal curve uses the same premiums paid: its distance from the purple one is "
        "only the value of early exercise. For a call without dividends the two curves "
        "coincide."
    ),
    "Confronta sul grafico: se fossero {other}": "Compare on the chart: if they were {other}",
    "Prezzo spot": "Spot price",
    "Esercitabile solo a scadenza. Prezzata con Merton: Black-Scholes più salti improvvisi.": (
        "Exercisable only at expiry. Priced with Merton: Black-Scholes plus sudden jumps."
    ),
    "Modello di prezzo": "Pricing model",
    "Merton (con salti)": "Merton (with jumps)",
    "Merton vale solo per le opzioni europee: scegli «Europea» per usarlo.": (
        "Merton applies to European options only: choose «European» to use it."
    ),
    "Salti/anno": "Jumps/yr",
    "Variabilità": "Variability",
    "Con Merton la IV qui sopra è la volatilità senza salti: i salti si aggiungono, quindi "
    "le opzioni costano di più, soprattutto le put lontane. Salto medio negativo = crollo.": (
        "With Merton the IV above is the volatility without jumps: jumps come on top, so "
        "options cost more, especially far out-of-the-money puts. Negative average jump = "
        "crash."
    ),
    "Valori tipici dell'S&P 500": "Typical S&P 500 values",
    "Merton: {count} salti/anno di {size}": "Merton: {count} jumps/year of {size}",
    "Volatilità implicita (IV)": "Implied volatility (IV)",
    # --- Panels: saved positions ---
    "Aperta «{name}»": "Opened «{name}»",
    "Posizione non trovata": "Position not found",
    "Salva la posizione": "Save the position",
    "Importata «{imported_name}». Premi «Salva» per tenerla.": (
        "Imported «{imported_name}». Press «Save» to keep it."
    ),
    "Importa una posizione": "Import a position",
    "Le mie posizioni": "My positions",
    "Posizione salvata": "Position saved",
    "{n} salvata": "{n} saved",
    "{n} salvate": "{n} saved",
    "Se usi un nome già salvato, la posizione con quel nome viene aggiornata.": (
        "If you use a name already saved, the position with that name is updated."
    ),
    "Scegli un file .json esportato dal simulatore (anche da un altro computer).": (
        "Choose a .json file exported from the simulator (even from another computer)."
    ),
    "Salva": "Save",
    "Nessuna posizione salvata. Costruisci una strategia e premi «Salva» per ritrovarla in "
    "seguito, anche dopo aver spento il simulatore.": (
        "No saved positions. Build a strategy and press «Save» to find it later, even "
        "after shutting the simulator down."
    ),
    "Apri": "Open",
    "Gestiscile tutte nelle Impostazioni →": "Manage them all in Settings →",
    "Gestisci nelle Impostazioni →": "Manage in Settings →",
    "Esporta file": "Export file",
    "Importa file": "Import file",
    # --- Panels: scenarios ---
    "{side} {qty}× azione": "{side} {qty}× stock",
    "Simulatore di scenari": "Scenario simulator",
    "Scegli dove sarà il titolo, fra quanti giorni e con quale volatilità: vedi il P&L e da "
    "dove viene.": (
        "Choose where the stock will be, in how many days and with which volatility: see "
        "the P&L and where it comes from."
    ),
    "P&L nello scenario": "P&L in the scenario",
    "Matrice degli scenari · P&L {when}": "Scenario matrix · P&L {when}",
    "Ogni casella combina una variazione del prezzo (colonne) e della IV (righe). Utile per "
    "vedere a colpo d'occhio se la posizione teme di più il prezzo o la volatilità.": (
        "Each cell combines a price change (columns) and an IV change (rows). Useful to "
        "see at a glance whether the position fears price or volatility more."
    ),
    "per azione · {signed_money} sulla posizione reale ({units} azioni)": (
        "per share · {signed_money} on the real position ({units} shares)"
    ),
    "Da dove viene": "Where it comes from",
    "IV \\ prezzo": "IV \\ price",
    "Prezzo del titolo: {price} ({x}{move} da oggi)": "Stock price: {price} ({x}{move} from today)",
    "Il «vol crush» è il crollo della IV dopo un evento atteso, tipicamente gli utili "
    "trimestrali: chi ha comprato opzioni perde anche se il prezzo si muove nella direzione "
    "giusta.": (
        "«Vol crush» is the collapse of IV after an expected event, typically quarterly "
        "earnings: option buyers lose even if the price moves in the right direction."
    ),
    "Varrà": "Will be worth",
    "P&L": "P&L",
    "Quando: oggi": "When: today",
    "Volatilità implicita: {iv}": "Implied volatility: {iv}",
    "Azzera scenario": "Reset scenario",
    "= P&L nello scenario": "= P&L in the scenario",
    "Quando: fra {days} gg ({strftime})": "When: in {days} d ({strftime})",
    " ({x}{change} rispetto a oggi)": " ({x}{change} versus today)",
    " (come oggi)": " (same as today)",
    "IV attuale": "Current IV",
    "IV {x}{iv_move}": "IV {x}{iv_move}",
    " · a scadenza": " · at expiry",
    "Crollo −50%": "Crash −50%",
    "Attuale": "Current",
    "Se chiudessi oggi": "If you closed today",
    "Movimento del prezzo": "Price move",
    "Tempo che passa (theta)": "Time passing (theta)",
    "Cambio di volatilità (vega)": "Volatility change (vega)",
    "1 settimana": "1 week",
    "Metà": "Halfway",
    "Scadenza": "Expiry",
    # --- Panels: strategy ---
    "Premi rifissati ai prezzi correnti": "Premiums reset to current prices",
    "Strategie precostruite": "Prebuilt strategies",
    "Premi d'ingresso": "Entry premiums",
    "Congelati all'apertura della posizione": "Frozen when the position is opened",
    "Il costo già pagato non cambia quando muovi lo spot: è il comportamento corretto. "
    "Disattivandolo, i premi vengono riprezzati ai parametri correnti e la curva «valore "
    "oggi» passerà sempre per lo zero al prezzo spot.": (
        "The cost already paid does not change when you move spot: that is the correct "
        "behaviour. Turning it off reprices the premiums at the current parameters and "
        "the «value today» curve will always cross zero at the spot price."
    ),
    "I premi seguono i parametri correnti: muovendo lo spot cambia anche il costo «già "
    "pagato», e i break-even scivolano con lo slider.": (
        "Premiums follow the current parameters: moving spot also changes the cost "
        "«already paid», and the break-evens slide with the slider."
    ),
    "Premi fissati a: spot {spot} $ · IV {iv} · {days_to_expiry} gg. Anche le gambe "
    "aggiunte ora usano questi valori.": (
        "Premiums fixed at: spot ${spot} · IV {iv} · {days_to_expiry} d. Legs added now "
        "use these values too."
    ),
    "Rifissa i premi ai prezzi correnti": "Reset premiums to current prices",
    # --- Strategies ---
    "Personalizzata": "Custom",
    "Gambe scelte da te (o caricate dalle opzioni reali). Scegli una strategia dall'elenco "
    "per ripartire da una ricetta.": (
        "Legs chosen by you (or loaded from real options). Pick a strategy from the list "
        "to start again from a recipe."
    ),
    "Singola opzione": "Single option",
    "Una sola gamba. Il punto di partenza per capire le greche.": (
        "A single leg. The starting point for understanding the Greeks."
    ),
    "Bull Call Spread": "Bull Call Spread",
    "Compri una call ATM e ne vendi una OTM più alta. Rialzista, rischio e profitto limitati.": (
        "Buy an ATM call and sell a higher OTM one. Bullish, limited risk and profit."
    ),
    "Bear Put Spread": "Bear Put Spread",
    "Compri una put ATM e ne vendi una OTM più bassa. Ribassista, rischio e profitto limitati.": (
        "Buy an ATM put and sell a lower OTM one. Bearish, limited risk and profit."
    ),
    "Long Straddle": "Long Straddle",
    "Compri call e put sullo stesso strike. Scommetti su un grande movimento, in qualsiasi "
    "direzione.": (
        "Buy a call and a put on the same strike. You bet on a big move, in either direction."
    ),
    "Long Strangle": "Long Strangle",
    "Compri call OTM e put OTM. Come lo straddle ma più economico; serve un movimento più ampio.": (
        "Buy an OTM call and an OTM put. Like the straddle but cheaper; it needs a bigger move."
    ),
    "Iron Condor": "Iron Condor",
    "Vendi uno strangle interno e compri ali esterne. Guadagni se il sottostante resta nel "
    "range.": (
        "Sell an inner strangle and buy outer wings. You gain if the underlying stays in the range."
    ),
    "Covered Call (con azione)": "Covered Call (with stock)",
    "Possiedi 100 azioni e vendi una call OTM: incassi il premio in cambio di un tetto al "
    "guadagno. Reddito su una posizione che già detieni.": (
        "Own 100 shares and sell an OTM call: you collect the premium in exchange for a "
        "cap on the gain. Income on a position you already hold."
    ),
    "Protective Put (con azione)": "Protective Put (with stock)",
    "Possiedi 100 azioni e compri una put: assicuri la posizione contro i ribassi pagando "
    "un premio. È un'assicurazione.": (
        "Own 100 shares and buy a put: you insure the position against drops by paying a "
        "premium. It is insurance."
    ),
    "Collar (con azione)": "Collar (with stock)",
    "Possiedi 100 azioni, compri una put protettiva e finanzi la protezione vendendo una "
    "call OTM. Limiti sia perdite sia guadagni.": (
        "Own 100 shares, buy a protective put and fund the protection by selling an OTM "
        "call. You limit both losses and gains."
    ),
    "Risk Reversal": "Risk Reversal",
    "Vendi una put OTM e compri una call OTM, senza azione: esposizione rialzista "
    "sintetica a basso costo.": (
        "Sell an OTM put and buy an OTM call, without stock: cheap synthetic bullish exposure."
    ),
    "Covered Call (sintetica)": "Covered Call (synthetic)",
    "Short put singola: stesso profilo di rischio del possedere l'azione e vendere una "
    "call, ma senza detenere il titolo.": (
        "Single short put: same risk profile as owning the stock and selling a call, but "
        "without holding the shares."
    ),
    # --- Panels: summary ---
    "Riepilogo della posizione": "Position summary",
    "{ticker} · {name} · scade {expiry}": "{ticker} · {name} · expires {expiry}",
    "Costo / credito netto": "Net cost / credit",
    "Probabilità di profitto": "Probability of profit",
    "a scadenza, secondo il modello": "at expiry, according to the model",
    "esborso iniziale": "initial outlay",
    "premio incassato": "premium received",
    "illimitato verso l'alto": "unlimited to the upside",
    "a scadenza": "at expiry",
    "ILLIMITATA — rischio non coperto": "UNLIMITED — uncovered risk",
    "Questa posizione ha perdita potenzialmente illimitata: una gamba venduta non è coperta "
    "da una comprata più esterna.": (
        "This position has potentially unlimited loss: a sold leg is not covered by a "
        "bought one further out."
    ),
    "<strong>Nota sui prezzi.</strong> I prezzi sono <em>teorici</em>: i modelli assumono "
    "volatilità costante e assenza di salti di prezzo (gap), quindi divergono dai prezzi "
    "reali di mercato. Il simulatore serve a capire le relazioni tra le variabili, non a "
    "stimare prezzi di trading, e non costituisce consulenza finanziaria.": (
        "<strong>A note on prices.</strong> Prices are <em>theoretical</em>: the models "
        "assume constant volatility and no price jumps (gaps), so they differ from real "
        "market prices. The simulator is for understanding how the variables relate, not "
        "for estimating trading prices, and it is not financial advice."
    ),
    # --- Printable summary ---
    "Mercato": "Market",
    "Costo / credito": "Cost / credit",
    "Profitto massimo": "Maximum profit",
    "Prob. di profitto": "Prob. of profit",
    "Greche aggregate": "Aggregate Greeks",
    "Spot": "Spot",
    "Giorni alla scadenza": "Days to expiry",
    "Volatilità implicita": "Implied volatility",
    "Tasso risk-free": "Risk-free rate",
    "Dividend yield": "Dividend yield",
    "Esercizio": "Exercise",
    "{side} azione": "{side} stock",
    "Δ Delta": "Δ Delta",
    "Γ Gamma": "Γ Gamma",
    "Θ Theta $/gg": "Θ Theta $/d",
    "ν Vega $/1% IV": "ν Vega $/1% IV",
    "ρ Rho $/1% tasso": "ρ Rho $/1% rate",
    "Generato con il simulatore di opzioni, versione {app_version}.": (
        "Generated with the options simulator, version {app_version}."
    ),
    "Stampa / Salva PDF": "Print / Save PDF",
    "Nella finestra di stampa scegli «Salva come PDF».": (
        "In the print window choose «Save as PDF»."
    ),
    "Costo reale: {signed_money} {packages} (moltiplicatore {contract_multiplier}).": (
        "Real cost: {signed_money} {packages} (multiplier {contract_multiplier})."
    ),
    "Simulatore di opzioni · riepilogo": "Options simulator · summary",
    "Simulatore di opzioni": "Options simulator",
    "{ticker} · {name}": "{ticker} · {name}",
    "Strike / carico": "Strike / entry",
    # --- Real options: page ---
    "Tasso implicito": "Implied rate",
    "Rendimento implicito": "Implied yield",
    "Stile delle opzioni": "Option style",
    "annuo: dividendi + costo di prestito": "annual: dividends + borrow cost",
    "annuo: dividendi + costo di prestito · questa scadenza: {value}": (
        "annual: dividends + borrow cost · this expiry: {value}"
    ),
    "Scadenza breve: il rendimento di questa scadenza ({value}) è una stima rumorosa, "
    "perché pochi centesimi di errore sul forward vengono divisi per pochi giorni. Quello "
    "annuo è {annual}. Nei calcoli resta quello della scadenza, che fa combaciare call e "
    "put.": (
        "Short expiry: this expiry's yield ({value}) is a noisy estimate, because a few "
        "cents of error on the forward are divided by a few days. The annual one is "
        "{annual}. Calculations keep the expiry's value, which makes calls and puts agree."
    ),
    "Verifica call/put": "Call/put check",
    "{after} punti": "{after} points",
    "Selezione svuotata: le gambe devono avere la stessa scadenza.": (
        "Selection cleared: legs must have the same expiry."
    ),
    "Questa opzione non ha un prezzo utilizzabile.": "This option has no usable price.",
    "{title} {strike}": "{title} {strike}",
    "Le opzioni quotate davvero: guardale, scegline alcune e studiale nel simulatore, o "
    "confronta il mercato con il modello.": (
        "The options actually listed: look at them, pick a few and study them in the "
        "simulator, or compare the market with the model."
    ),
    "indice: solo a scadenza": "index: at expiry only",
    "esercitabili sempre": "exercisable any time",
    "differenza di IV fra call e put (con 4% e 0%: {before})": (
        "IV gap between calls and puts (with 4% and 0%: {before})"
    ),
    "Carica un titolo": "Load a stock",
    "calcolo in corso": "calculating",
    "Chi compra paga il prezzo lettera, chi vende incassa il denaro: la differenza (lo "
    "spread) è il costo nascosto di ogni operazione.": (
        "Buyers pay the ask, sellers receive the bid: the difference (the spread) is the "
        "hidden cost of every trade."
    ),
    "Titoli, ETF e indici USA · fonte: {source_name}": (
        "US stocks, ETFs and indices · source: {source_name}"
    ),
    "{display_symbol} · {name}": "{display_symbol} · {name}",
    "prezzo": "price",
    "Variazione del giorno": "Day change",
    "IV a 30 giorni": "30-day IV",
    "Dati aggiornati al": "Data as of",
    "indice di volatilità del titolo": "the stock's volatility index",
    "ora USA, ritardo ~15 min": "US time, ~15 min delay",
    "Strike mostrati, in percentuale dal prezzo attuale": (
        "Strikes shown, as a percentage from the current price"
    ),
    "es. Apple, AAPL, Ferrari…": "e.g. Apple, AAPL, Ferrari…",
    "Cerca un titolo o scrivi un simbolo USA": "Search a stock or type a US symbol",
    "Catena": "Chain",
    "Modello vs mercato": "Model vs market",
    "Volatilità": "Volatility",
    "Sfoglia per categoria": "Browse by category",
    "Scrivi il nome o il simbolo di un titolo e scegli fra i suggerimenti, oppure usa i "
    "titoli rapidi. Qualunque simbolo USA con opzioni funziona, anche se non è nell'elenco: "
    "scrivilo e premi Invio. Serve internet.": (
        "Type a stock's name or symbol and pick from the suggestions, or use the quick "
        "picks. Any US symbol with options works, even if it is not in the list: type it "
        "and press Enter. Needs internet."
    ),
    "Compra a {price_text}": "Buy at {price_text}",
    "Vendi a {price_text}": "Sell at {price_text}",
    "{date} · {days} gg": "{date} · {days} d",
    "Tutti": "All",
    "Denaro": "Bid",
    "Lettera": "Ask",
    "IV": "IV",
    "OI": "OI",
    "ricavato dalle opzioni sull'S&P 500": "derived from S&P 500 options",
    "valore predefinito (S&P 500 non disponibile)": "default value (S&P 500 unavailable)",
    # --- Real options: your picks ---
    "Le tue scelte": "Your picks",
    "Registra la posizione ai prezzi veri e seguila nei prossimi giorni": (
        "Record the position at real prices and follow it over the next days"
    ),
    "Apri nel portafoglio virtuale": "Open in the virtual portfolio",
    "{display_symbol} · scadenza {strftime}": "{display_symbol} · expiry {strftime}",
    "Posizione aperta nel portafoglio virtuale": "Position opened in the virtual portfolio",
    "Clicca un'opzione nella catena": "Click an option in the chain",
    "Per azione. Un contratto vale {contract_multiplier} azioni: {signed_money} per contratto.": (
        "Per share. One contract covers {contract_multiplier} shares: {signed_money} per contract."
    ),
    "Nel simulatore spot, giorni, IV, tasso e dividendo vengono dal mercato e i premi "
    "pagati sono quelli reali. Sostituisce la posizione aperta: salvala prima, se ti "
    "serve.": (
        "In the simulator spot, days, IV, rate and dividend come from the market and the "
        "premiums paid are the real ones. It replaces the open position: save it first if "
        "you need it."
    ),
    "Pagheresti {money} (prezzi reali, {contract_multiplier} azioni per contratto). Nessun "
    "soldo vero: il simulatore ricorda solo i prezzi e la previsione del modello, per "
    "confrontarli poi con quello che succede.": (
        "You would pay {money} (real prices, {contract_multiplier} shares per contract). "
        "No real money: the simulator only records the prices and the model's forecast, "
        "to compare them later with what happens."
    ),
    "Incasseresti {money} (prezzi reali, {contract_multiplier} azioni per contratto). "
    "Nessun soldo vero: il simulatore ricorda solo i prezzi e la previsione del modello, "
    "per confrontarli poi con quello che succede.": (
        "You would receive {money} (real prices, {contract_multiplier} shares per "
        "contract). No real money: the simulator only records the prices and the model's "
        "forecast, to compare them later with what happens."
    ),
    "Qui si raccolgono le opzioni che compri o vendi dalla catena. Tutte devono avere la "
    "stessa scadenza: cambiando scadenza la selezione riparte da capo.": (
        "The options you buy or sell from the chain gather here. They must all have the "
        "same expiry: changing expiry starts the selection over."
    ),
    "Apri la posizione": "Open the position",
    "Credito netto": "Net credit",
    "Studia nel simulatore": "Study in the simulator",
    "Svuota": "Clear",
    "La tua previsione (facoltativa)": "Your forecast (optional)",
    "{x} {right} {strike}": "{x} {right} {strike}",
    "es. credo che salga sopra 340 prima della scadenza": (
        "e.g. I think it goes above 340 before expiry"
    ),
    "a {premium}": "at {premium}",
    "Apri nel portafoglio": "Open in the portfolio",
    " · IV {iv}": " · IV {iv}",
    "L": "L",
    "S": "S",
    # --- Real options: chain ---
    "Le righe colorate sono in the money. Clicca il lato call o put di una riga per "
    "comprare o vendere quell'opzione.": (
        "Coloured rows are in the money. Click the call or put side of a row to buy or "
        "sell that option."
    ),
    "CALL": "CALL",
    "PUT": "PUT",
    "Strike": "Strike",
    "prezzo {spot}": "price {spot}",
    # --- Real options: model vs market ---
    "Il modello con una sola volatilità, contro il mercato": (
        "The single-volatility model against the market"
    ),
    "Il modello prezza ogni strike con la stessa IV; il mercato no. Lo scarto, strike per "
    "strike, è il sorriso della volatilità.": (
        "The model prices every strike with the same IV; the market does not. The gap, "
        "strike by strike, is the volatility smile."
    ),
    "Rendimento implicito per questa scadenza, ricavato dalla catena": (
        "Implied yield for this expiry, derived from the chain"
    ),
    "* Scarto = prezzo di mercato meno prezzo del modello. Rosso: il mercato chiede di più; "
    "verde: di meno. OI = interesse aperto, cioè quanti contratti esistono su "
    "quell'opzione.": (
        "* Gap = market price minus model price. Red: the market asks more; green: less. "
        "OI = open interest, i.e. how many contracts exist on that option."
    ),
    "Tasso e dividendo non sono inventati: vengono dalla put-call parity. Una call comprata "
    "e una put venduta allo stesso strike equivalgono a possedere il titolo a termine, "
    "quindi C − P rivela il forward. Dall'S&P 500, che ha opzioni europee, si ricava il "
    "tasso; dal forward di ogni titolo il suo rendimento implicito. Con valori giusti, call "
    "e put allo stesso strike hanno la stessa IV: la casella «Verifica call/put» misura "
    "quanto ci si avvicina.": (
        "Rate and dividend are not made up: they come from put-call parity. A bought call "
        "and a sold put on the same strike are equivalent to owning the stock forward, so "
        "C − P reveals the forward. The rate is derived from the S&P 500, which has "
        "European options; each stock's implied yield from its forward. With the right "
        "values, calls and puts on the same strike have the same IV: the «Call/put check» "
        "box measures how close it gets."
    ),
    "Come leggerlo. Se il modello avesse ragione, la IV di mercato sarebbe una linea piatta "
    "e le barre sarebbero tutte a zero. Sulle azioni di solito le put molto fuori dal "
    "denaro (strike bassi) costano più del modello: il mercato paga una protezione contro i "
    "crolli che la lognormale considera quasi impossibili. Barre positive = il mercato "
    "chiede più del modello.": (
        "How to read it. If the model were right, the market IV would be a flat line and "
        "the bars would all be at zero. On stocks, deep out-of-the-money puts (low "
        "strikes) usually cost more than the model: the market pays for protection "
        "against crashes the lognormal considers almost impossible. Positive bars = the "
        "market asks more than the model."
    ),
    "IV call": "Call IV",
    "IV put": "Put IV",
    "Modello": "Model",
    "IV del modello: {iv} (ATM di mercato: {atm})": "Model IV: {iv} (market ATM: {atm})",
    "Volatilità implicita per strike": "Implied volatility by strike",
    "Mercato meno modello ($ per azione)": "Market minus model ($ per share)",
    "IV ATM": "ATM IV",
    "Tasso": "Rate",
    "Valori del mercato": "Market values",
    "Dividendo": "Dividend",
    "Call merc.": "Call mkt",
    "Call mod.": "Call model",
    "Scarto*": "Gap*",
    "Put merc.": "Put mkt",
    "Put mod.": "Put model",
    # --- Real options: Merton jumps ---
    "Salti di Merton": "Merton jumps",
    "Un modello con crolli improvvisi: spiega le put care che Black-Scholes non riesce a "
    "spiegare.": (
        "A model with sudden crashes: it explains the expensive puts that Black-Scholes "
        "cannot explain."
    ),
    "Cerca quanti salti all'anno, e di che grandezza, rendono i prezzi del modello uguali a "
    "quelli di mercato su questa scadenza. Usa le opzioni fuori dal denaro, le più "
    "scambiate.": (
        "It looks for how many jumps a year, and how large, make the model prices match the "
        "market on this expiry. It uses out-of-the-money options, the most traded ones."
    ),
    "Calibra i salti": "Calibrate the jumps",
    "Calibrazione in corso…": "Calibrating…",
    "Ricalibra": "Recalibrate",
    "Troppo poche opzioni quotate su questa scadenza per calibrare i salti.": (
        "Too few quoted options on this expiry to calibrate the jumps."
    ),
    "Salti attesi all'anno": "Expected jumps per year",
    "quanti ne prezza il mercato": "how many the market prices in",
    "Salto medio": "Average jump",
    "negativo = crollo": "negative = crash",
    "Variabilità dei salti": "Jump variability",
    "quanto cambiano da un salto all'altro": "how much they differ from one jump to the next",
    "Volatilità senza salti": "Volatility without jumps",
    "il movimento continuo di tutti i giorni": "the continuous everyday movement",
    "Errore Black-Scholes": "Black-Scholes error",
    "con la migliore volatilità unica": "with the best single volatility",
    "Errore Merton": "Merton error",
    "scarto medio dalla IV di mercato": "average gap from the market IV",
    "{value} punti": "{value} points",
    "Merton": "Merton",
    "Come leggerlo: su questa scadenza il mercato prezza in media {count} salti all'anno, di "
    "circa {size} ciascuno. Con i salti l'errore sulla volatilità implicita scende da {bsm} a "
    "{merton} punti: la curva «Merton» nel grafico segue il sorriso, la linea del modello a "
    "volatilità unica no.": (
        "How to read it: on this expiry the market prices in an average of {count} jumps a "
        "year, of about {size} each. With jumps the implied volatility error drops from "
        "{bsm} to {merton} points: the «Merton» curve on the chart follows the smile, the "
        "single-volatility model line does not."
    ),
    "Le opzioni su azioni sono americane: la formula di Merton è per le europee, quindi qui "
    "usa solo le opzioni fuori dal denaro, dove l'esercizio anticipato vale poco.": (
        "Stock options are American: Merton's formula is for European options, so here it "
        "uses only out-of-the-money options, where early exercise is worth little."
    ),
    # --- Real options: volatility ---
    "Volatilità implicita contro storica": "Implied against historical volatility",
    "La IV è quanto il mercato si aspetta che il titolo si muova; la storica è quanto si è "
    "mosso davvero. Confrontarle dice se le opzioni sono care o economiche.": (
        "IV is how much the market expects the stock to move; historical is how much it "
        "really moved. Comparing them tells whether options are expensive or cheap."
    ),
    "Implicita a 30 giorni": "30-day implied",
    "Storica 1 mese": "Historical 1 month",
    "Storica 3 mesi": "Historical 3 months",
    "Storica 1 anno": "Historical 1 year",
    "Implicita / storica": "Implied / historical",
    "Posizione nell'anno": "Position in the year",
    "Storica a 30 giorni": "30-day historical",
    "Prezzo {symbol}": "{symbol} price",
    "quanto il mercato si aspetta": "what the market expects",
    "20 giorni di borsa": "20 trading days",
    "60 giorni di borsa": "60 trading days",
    "252 giorni di borsa": "252 trading days",
    "{ratio}×": "{ratio}×",
    "sopra 1 = il mercato prevede più movimento": "above 1 = the market expects more movement",
    "giorni dell'ultimo anno con storica più bassa della IV di oggi": (
        "days of the last year with historical below today's IV"
    ),
    "Implicita di oggi": "Today's implied",
    "Volatilità storica nell'ultimo anno, contro la implicita di oggi": (
        "Historical volatility over the last year, against today's implied"
    ),
    "Carica un titolo per vedere la sua volatilità.": "Load a stock to see its volatility.",
    "Storica = deviazione standard dei rendimenti giornalieri, annualizzata (×√252). La IV "
    "sta di solito un po' sopra la storica anche in tempi normali: chi vende opzioni chiede "
    "un premio per il rischio di movimenti improvvisi. Per questo «care» scatta solo quando "
    "la IV supera la storica di oltre il 25%.": (
        "Historical = standard deviation of daily returns, annualised (×√252). IV usually "
        "sits a little above historical even in normal times: option sellers ask for a "
        "premium for the risk of sudden moves. That is why «expensive» triggers only when "
        "IV exceeds historical by more than 25%."
    ),
    "Scarico lo storico dei prezzi…": "Downloading price history…",
    "La IV a 30 giorni ({iv}) è {ratio} volte la volatilità realizzata nell'ultimo mese "
    "({hv20}). {text}": (
        "The 30-day IV ({iv}) is {ratio} times the volatility realised over the last "
        "month ({hv20}). {text}"
    ),
    " Per gli indici CBOE non fornisce lo storico: si usa {display_symbol}, l'ETF che li "
    "replica.": (
        " CBOE provides no history for indices: {display_symbol}, the ETF that tracks "
        "them, is used instead."
    ),
    "Opzioni care": "Expensive options",
    "Il mercato si aspetta più movimento di quello che il titolo ha fatto nell'ultimo mese, "
    "oppure c'è un evento in arrivo (per esempio gli utili trimestrali). Chi vende opzioni "
    "incassa premi alti; chi le compra paga caro e rischia il vol crush quando l'evento "
    "passa.": (
        "The market expects more movement than the stock showed over the last month, or "
        "an event is coming (quarterly earnings, for example). Option sellers collect high "
        "premiums; buyers pay a lot and risk the vol crush once the event has passed."
    ),
    "Opzioni nella media": "Average options",
    "La volatilità implicita è in linea con quella realizzata, con il piccolo sovrapprezzo "
    "che il mercato chiede di solito. Nessun vantaggio evidente né per chi compra né per chi "
    "vende.": (
        "Implied volatility is in line with realised volatility, with the small markup the "
        "market usually asks. No clear edge for either buyers or sellers."
    ),
    "Opzioni economiche": "Cheap options",
    "Il mercato prezza meno movimento di quello che il titolo sta facendo davvero. Comprare "
    "opzioni costa poco rispetto all'agitazione recente; vendere opzioni incassa poco per "
    "il rischio che si prende.": (
        "The market prices in less movement than the stock is really making. Buying "
        "options is cheap compared with the recent turbulence; selling them collects "
        "little for the risk taken."
    ),
    # --- Portfolio ---
    "Eliminata {display_ticker}": "Deleted {display_ticker}",
    "Il tuo portafoglio virtuale": "Your virtual portfolio",
    "Le tue previsioni contro la realtà": "Your forecasts against reality",
    "Posizioni chiuse": "Closed positions",
    "Prezzi aggiornati per {count} posizioni": "Prices updated for {count} positions",
    "Chiusa {display_ticker}: {signed_money}": "Closed {display_ticker}: {signed_money}",
    "Chiudere {display_ticker}?": "Close {display_ticker}?",
    "Posizioni aperte per finta ai prezzi veri: torna nei prossimi giorni e scopri se il "
    "modello aveva ragione.": (
        "Make-believe positions at real prices: come back in the next days and find out "
        "whether the model was right."
    ),
    "Posizioni aperte": "Open positions",
    "Valore attuale": "Current value",
    "Guadagno / perdita aperti": "Open gain / loss",
    "Realizzato": "Realised",
    "Quanto spesso il modello ci prende: la probabilità che ti dava all'apertura contro "
    "come sono finite davvero le posizioni chiuse.": (
        "How often the model gets it right: the probability it gave you at opening "
        "against how the closed positions really ended."
    ),
    "Il modello prevedeva": "The model expected",
    "È successo": "What happened",
    "Risultato complessivo": "Overall result",
    "Vale ora": "Worth now",
    "Prezzo del titolo": "Stock price",
    "Volatilità ATM": "ATM volatility",
    "Il modello dava": "The model gave",
    "{prob_profit} di profitto": "{prob_profit} chance of profit",
    "Break-even": "Break-even",
    "Guadagno massimo": "Maximum gain",
    "Perdita massima": "Maximum loss",
    "Prezzi aggiornati al {timestamp} · dati CBOE in ritardo di 15 minuti": (
        "Prices as of {timestamp} · CBOE data delayed by 15 minutes"
    ),
    "Nessuna posizione aperta": "No open positions",
    "al prezzo medio fra denaro e lettera": "at the mid price between bid and ask",
    "non ancora realizzati": "not yet realised",
    "{n} posizione chiusa": "{n} closed position",
    "{n} posizioni chiuse": "{n} closed positions",
    "probabilità media di profitto all'apertura": "average probability of profit at opening",
    "{wins} in guadagno su {closed}": "{wins} in profit out of {closed}",
    "Il grafico dell'andamento compare dal secondo giorno: torna domani.": (
        "The progress chart appears from the second day: come back tomorrow."
    ),
    "Pagato": "Paid",
    "Incassato": "Received",
    "nessuno": "none",
    "Si chiude ai prezzi reali di adesso: le opzioni comprate si vendono al prezzo denaro, "
    "quelle vendute si ricomprano al prezzo lettera. È il costo vero dell'uscita, di solito "
    "un po' peggiore del valore «a metà».": (
        "It closes at the real prices of right now: bought options are sold at the bid, "
        "sold ones are bought back at the ask. It is the true cost of exiting, usually a "
        "bit worse than the «mid» value."
    ),
    "Il portafoglio è vuoto": "The portfolio is empty",
    "Aggiorna prezzi": "Refresh prices",
    "Appare quando avrai chiuso almeno una posizione (o una sarà scaduta). Più posizioni "
    "chiudi, più il confronto diventa significativo.": (
        "It appears once you have closed at least one position (or one has expired). The "
        "more positions you close, the more meaningful the comparison."
    ),
    "Con poche posizioni il caso pesa molto: servono decine di operazioni prima che la "
    "percentuale reale si avvicini a quella prevista. E una probabilità di profitto alta "
    "non basta: conta anche quanto si guadagna quando va bene e quanto si perde quando va "
    "male.": (
        "With few positions luck weighs a lot: it takes dozens of trades before the real "
        "percentage gets close to the expected one. And a high probability of profit is "
        "not enough: what you gain when it goes well and lose when it goes badly matters "
        "too."
    ),
    "Se la percentuale reale resta lontana da quella prevista, il modello (volatilità "
    "costante, nessun salto di prezzo) non descrive bene i titoli che scegli: è il sorriso "
    "di volatilità che lavora.": (
        "If the real percentage stays far from the expected one, the model (constant "
        "volatility, no price jumps) does not describe the stocks you pick well: it is the "
        "volatility smile at work."
    ),
    "La tua previsione: «{note}»": "Your forecast: «{note}»",
    "Appena aperta, la posizione vale già un po' meno di quanto pagato: il valore si misura "
    "«a metà» fra denaro e lettera, mentre tu hai comprato alla lettera e venduto al "
    "denaro. È lo spread, il costo nascosto di ogni operazione.": (
        "Right after opening, the position is already worth a bit less than you paid: "
        "value is measured «mid» between bid and ask, while you bought at the ask and sold "
        "at the bid. It is the spread, the hidden cost of every trade."
    ),
    "Probabilità di profitto che dava il modello all'apertura": (
        "Probability of profit the model gave at opening"
    ),
    "Chiudi la posizione": "Close the position",
    "Scarico i prezzi, un titolo alla volta…": "Downloading prices, one stock at a time…",
    "Guadagno / perdita $": "Gain / loss $",
    "Aperta il {timestamp} · scade il {strftime} ({days_left} gg)": (
        "Opened on {timestamp} · expires on {strftime} ({days_left} d)"
    ),
    "Titolo": "Stock",
    "Posizione": "Position",
    "Chiusa il": "Closed on",
    "Prevista": "Expected",
    "Risultato": "Result",
    "Vai su «Opzioni reali», scegli un titolo e una o più opzioni, poi premi «Apri nel "
    "portafoglio». Il simulatore ricorda i prezzi che avresti pagato davvero e la "
    "previsione del modello in quel momento.": (
        "Go to «Real options», pick a stock and one or more options, then press «Open in "
        "the portfolio». The simulator records the prices you would really have paid and "
        "the model's forecast at that moment."
    ),
    "{sign}{pct} sul premio": "{sign}{pct} on the premium",
    "Chiudi": "Close",
    "Vai alle opzioni reali": "Go to real options",
    "regolata a scadenza al valore intrinseco (prezzo del giorno dell'aggiornamento)": (
        "settled at expiry at intrinsic value (price on the day of the refresh)"
    ),
    # --- Data, saving and portfolio errors ---
    "CBOE non ha restituito un prezzo valido per questo titolo.": (
        "CBOE did not return a valid price for this stock."
    ),
    "Nessuna opzione con scadenza futura per questo titolo.": (
        "No options with a future expiry for this stock."
    ),
    "Scrivi un simbolo valido, per esempio AAPL o SPY.": (
        "Type a valid symbol, for example AAPL or SPY."
    ),
    "Il formato dei dati CBOE non è quello atteso.": "The CBOE data is not in the expected format.",
    "CBOE ha risposto con un errore ({code}).": "CBOE replied with an error ({code}).",
    "Impossibile raggiungere CBOE: controlla la connessione a internet.": (
        "Cannot reach CBOE: check your internet connection."
    ),
    "CBOE ha restituito dati illeggibili.": "CBOE returned unreadable data.",
    "CBOE non ha opzioni per «{symbol}»: funziona solo con titoli, ETF e indici USA.": (
        "CBOE has no options for «{symbol}»: it only works with US stocks, ETFs and indices."
    ),
    "CBOE ha ricevuto troppe richieste e ci ha messo in pausa: riprova fra qualche minuto.": (
        "CBOE received too many requests and paused us: try again in a few minutes."
    ),
    "CBOE (dati in ritardo di 15 minuti)": "CBOE (data delayed by 15 minutes)",
    "Storico troppo corto per calcolare la volatilità.": (
        "History too short to compute volatility."
    ),
    "CBOE non fornisce lo storico di {symbol}.": "CBOE provides no history for {symbol}.",
    "Il VIX è già una volatilità implicita: il confronto con la storica non si applica.": (
        "The VIX already is an implied volatility: the comparison with historical does not apply."
    ),
    "Lo storico di CBOE non ha il formato atteso.": (
        "The CBOE history is not in the expected format."
    ),
    "Storico non disponibile per {symbol}.": "History not available for {symbol}.",
    "Impossibile raggiungere CBOE per lo storico.": "Cannot reach CBOE for the history.",
    "Lo storico di CBOE è illeggibile.": "The CBOE history is unreadable.",
    "CBOE ha ricevuto troppe richieste: riprova fra qualche minuto.": (
        "CBOE received too many requests: try again in a few minutes."
    ),
    "Nessuna opzione scelta.": "No option selected.",
    "Hai già {n} posizioni aperte: chiudine qualcuna.": (
        "You already have {n} open positions: close some."
    ),
    "Dai un nome alla posizione.": "Give the position a name.",
    "Il nome può avere al massimo {n} caratteri.": "The name can be at most {n} characters.",
    "Hai già {n} posizioni salvate: eliminane qualcuna.": (
        "You already have {n} saved positions: delete some."
    ),
    "Il file non è una posizione esportata dal simulatore.": (
        "The file is not a position exported from the simulator."
    ),
    "Il file viene da una versione più recente del simulatore.": (
        "The file comes from a newer version of the simulator."
    ),
    "Il file non è un JSON valido.": "The file is not valid JSON.",
    # --- Stock catalogue: categories ---
    "Indici": "Indices",
    "ETF di mercato": "Market ETFs",
    "ETF di settore": "Sector ETFs",
    "Materie prime e obbligazioni": "Commodities and bonds",
    "Tecnologia": "Technology",
    "Finanza": "Finance",
    "Cripto (azioni ed ETF)": "Crypto (stocks and ETFs)",
    "Consumi e industria": "Consumer and industrial",
    "Sanità": "Healthcare",
    "Energia": "Energy",
    "Estero e Italia (quotate in USA)": "International and Italy (US-listed)",
    "ETF a leva e volatilità": "Leveraged and volatility ETFs",
    "Spazio e nuove tecnologie": "Space and frontier tech",
    # --- Stock catalogue: Italian names ---
    "S&P 500 (indice)": "S&P 500 (index)",
    "Mini S&P 500 (1/10 di SPX)": "Mini S&P 500 (1/10 of SPX)",
    "Nasdaq 100 (indice)": "Nasdaq 100 (index)",
    "Russell 2000 (indice)": "Russell 2000 (index)",
    "VIX, indice della volatilità": "VIX, volatility index",
    "iShares mercati emergenti": "iShares emerging markets",
    "iShares mercati sviluppati ex USA": "iShares developed markets ex US",
    "iShares Cina large cap": "iShares China large cap",
    "iShares Brasile": "iShares Brazil",
    "iShares Giappone": "iShares Japan",
    "iShares Italia": "iShares Italy",
    "iShares Germania": "iShares Germany",
    "Finanziari": "Financials",
    "Industriali": "Industrials",
    "Consumi discrezionali": "Consumer discretionary",
    "Beni di prima necessità": "Consumer staples",
    "Utility": "Utilities",
    "Biotecnologie": "Biotech",
    "Semiconduttori": "Semiconductors",
    "Banche regionali": "Regional banks",
    "Oro": "Gold",
    "Argento": "Silver",
    "Petrolio": "Oil",
    "Gas naturale": "Natural gas",
    "Minatori d'oro": "Gold miners",
    "Treasury USA 20+ anni": "US Treasury 20+ years",
    "Obbligazioni high yield": "High-yield bonds",
    "Obbligazioni societarie": "Corporate bonds",
    "iShares Regno Unito": "iShares United Kingdom",
    "iShares Corea del Sud": "iShares South Korea",
    "iShares Cina": "iShares China",
    "Direxion Semiconduttori Bull (3x)": "Direxion Semiconductor Bull (3x)",
    "ProShares Ultra VIX a breve": "ProShares Ultra VIX Short-Term",
    "iPath VIX a breve": "iPath VIX Short-Term",
    "Servizi di comunicazione": "Communication services",
    "Materiali": "Materials",
    "Immobiliare": "Real estate",
    "Petrolio e gas, esplorazione": "Oil & gas exploration",
    "Commercio al dettaglio": "Retail",
    "Costruttori di case": "Homebuilders",
    "iShares Costruzioni residenziali": "iShares Home Construction",
    "iShares Biotecnologie": "iShares Biotechnology",
    "iShares Semiconduttori": "iShares Semiconductor",
    "Compagnie aeree": "Airlines",
    "Energia solare": "Solar energy",
    "Uranio": "Uranium",
    "iShares Oro": "iShares Gold",
    "Minatori d'oro junior": "Junior gold miners",
    "Minatori d'argento": "Silver miners",
    "Minatori di rame": "Copper miners",
    "Agricoltura": "Agriculture",
    "Treasury USA 1-3 anni": "US Treasury 1-3 years",
}
