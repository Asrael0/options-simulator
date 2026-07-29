"""Guida: la spiegazione di ogni aspetto dello strumento.

Il contenuto è dati, non codice: una lista di sezioni con ancora, titolo e
testo in Markdown. Aggiungerne una significa aggiungere una voce alla lista,
e l'indice si aggiorna da solo.
"""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from .. import auth
from ..layout import page_frame
from ..widgets import CARD, FAINT, MUTED


@dataclass(frozen=True, slots=True)
class Section:
    anchor: str
    title: str
    body: str


SECTIONS: list[Section] = [
    Section(
        "opzione",
        "Che cos'è un'opzione",
        """
Un'opzione è un **contratto che dà un diritto, non un obbligo**. Chi la compra
paga una somma — il **premio** — e in cambio ottiene la facoltà di comprare o
vendere un titolo a un prezzo prefissato entro una certa data.

Chi la vende incassa il premio e assume l'obbligo speculare: se il compratore
decide di esercitare, il venditore *deve* stare al patto.

Questa asimmetria è tutto. Il compratore ha perdita limitata al premio pagato
e guadagno potenzialmente grande. Il venditore ha guadagno limitato al premio
incassato e perdita potenzialmente molto grande. Non esiste un lato "migliore":
il premio è esattamente il prezzo che il mercato attribuisce a quello squilibrio.

Nel simulatore ogni riga della tabella «Gambe della posizione» è un contratto.
Una posizione può averne quante ne vuoi, e il grafico mostra sempre il risultato
**combinato**.
""",
    ),
    Section(
        "call-put",
        "Call e put, long e short: le quattro combinazioni",
        """
Ci sono due tipi di opzione e due lati da cui starci. Quattro combinazioni, ed è
utile impararle come quattro scommesse diverse.

| | Comprata (**long**) | Venduta (**short**) |
|---|---|---|
| **Call** | Scommetti che salga. Paghi il premio, guadagno illimitato. | Scommetti che *non* salga. Incassi il premio, **perdita illimitata**. |
| **Put** | Scommetti che scenda. Paghi il premio, guadagno grande ma limitato (il prezzo non va sotto zero). | Scommetti che *non* scenda. Incassi il premio, perdita grande ma limitata. |

Le due caselle a destra vanno lette con attenzione. Vendere opzioni significa
incassare subito una somma certa e piccola, assumendosi un rischio raro e
grande. È una strategia legittima e diffusa, ma il profilo di rischio è
l'opposto di quello che l'incasso immediato suggerisce.

Il simulatore te lo dice esplicitamente: quando una posizione ha perdita
illimitata, il riepilogo mostra «ILLIMITATA» e un avviso in rosso, invece di un
numero rassicurante.
""",
    ),
    Section(
        "strike-premio",
        "Strike, premio, scadenza",
        """
**Strike** (o prezzo d'esercizio) è il prezzo prefissato nel contratto. Una call
con strike 100 dà il diritto di comprare a 100, qualunque cosa faccia il mercato.

**Premio** è quanto costa il contratto. Nel simulatore viene calcolato dal
modello, ma puoi sovrascriverlo digitando un valore tuo: serve quando vuoi
usare il prezzo reale visto sul book invece di quello teorico.

**Giorni alla scadenza** è quanto tempo resta. Più tempo resta, più l'opzione
vale: c'è più spazio perché succeda qualcosa. Il valore del tempo non decade in
modo lineare — accelera avvicinandosi alla scadenza, ed è la ragione per cui il
theta cresce negli ultimi giorni.

Attenzione a una convenzione: nel motore i prezzi sono sempre **per unità di
sottostante**. Un premio di 3,59 significa 3,59 per azione. Un contratto
americano standard ne controlla 100, quindi l'esborso reale è 359 — ed è quello
che mostra la pagina «Costi».
""",
    ),
    Section(
        "moneyness",
        "Moneyness: ITM, ATM, OTM",
        """
La *moneyness* dice se l'opzione avrebbe valore se scadesse adesso.

- **ITM** (*in the money*) — ha valore intrinseco. Una call è ITM se lo spot è
  sopra lo strike; una put se è sotto.
- **ATM** (*at the money*) — spot e strike quasi coincidono. Il simulatore usa
  una banda dell'1,5%.
- **OTM** (*out of the money*) — non ha valore intrinseco. Vale solo per la
  possibilità che le cose cambino prima della scadenza.

Un'opzione OTM non è "senza valore": ha un premio, e quel premio è tutto valore
temporale. È anche il motivo per cui le OTM perdono valore più rapidamente
avvicinandosi alla scadenza — non hanno nient'altro da perdere.

Nella tabella delle gambe l'etichetta colorata a destra mostra la moneyness di
ogni contratto, aggiornata mentre muovi lo spot.
""",
    ),
    Section(
        "intrinseco-temporale",
        "Valore intrinseco e valore temporale",
        """
Il premio di un'opzione si scompone sempre in due parti:

**Valore intrinseco** — quanto varrebbe se scadesse adesso. Per una call è
`max(spot − strike, 0)`, per una put `max(strike − spot, 0)`. Non può essere
negativo: nel caso peggiore non eserciti.

**Valore temporale** — tutto il resto. È quello che paghi per la possibilità che
le cose migliorino prima della scadenza. Dipende da quanto tempo resta e da
quanto il titolo si muove (la volatilità).

A scadenza il valore temporale è **zero** per definizione: non resta tempo. Ecco
perché nel grafico la curva «valore oggi» sta sempre sopra la spezzata «a
scadenza» quando sei long, e vi scende sopra man mano che i giorni passano. La
distanza fra le due curve *è* il valore temporale.
""",
    ),
    Section(
        "payoff",
        "Il diagramma di payoff",
        """
È lo strumento centrale. Sull'asse orizzontale c'è il prezzo del sottostante,
su quello verticale il profitto o la perdita della posizione.

**La linea bianca** è il risultato a scadenza. È una spezzata, con un vertice su
ogni strike, e rappresenta il P&L definitivo. È la linea che conta.

**La linea viola tratteggiata** è il valore oggi, alla volatilità corrente. È più
liscia e sta più in alto (se sei long) perché include ancora valore temporale.
Riduci i giorni alla scadenza e la vedrai piegarsi progressivamente verso la
bianca: è il decadimento temporale reso visibile.

**Le aree colorate** — verde sopra lo zero, rossa sotto — si riferiscono al
risultato a scadenza, e i loro confini cadono esattamente sui break-even.

**Le linee verticali**: arancione tratteggiata per gli strike, blu continua per
lo spot attuale, verde tratteggiata per i break-even.

Un consiglio pratico: carica una strategia, poi muovi lo slider dei giorni da
365 verso 0 e guarda solo la curva viola. È la lezione più densa che questo
strumento sa dare.
""",
    ),
    Section(
        "break-even",
        "Break-even",
        """
Il break-even è il prezzo a cui la posizione va in pari a scadenza: non guadagni
e non perdi. Per una call comprata è semplicemente `strike + premio`, perché
devi recuperare quello che hai pagato.

Con più gambe i break-even possono essere più di uno. Un iron condor, per
esempio, ne ha due: la zona di profitto sta in mezzo.

Nel simulatore i break-even non sono cercati per tentativi: il payoff a scadenza
è **lineare a tratti**, con vertici solo sugli strike, quindi si risolvono in
forma chiusa segmento per segmento. Il P&L al break-even vale esattamente zero,
non "zero entro l'errore di campionamento".
""",
    ),
    Section(
        "estremi",
        "Profitto e perdita massimi",
        """
Non tutti gli estremi sono numeri. Una call comprata ha profitto **illimitato**:
il titolo può salire senza tetto. Una call venduta nuda ha, specularmente,
perdita **illimitata**.

Il simulatore distingue i due casi guardando la pendenza del payoff nel tratto
finale a destra: se sale, il profitto è illimitato; se scende, lo è la perdita.
Non campiona il grafico visibile — un massimo letto "sul range mostrato" sarebbe
un numero finito e falsamente rassicurante.

Nota una asimmetria vera: la put comprata ha profitto **limitato**, perché il
prezzo di un titolo non può scendere sotto zero. Il massimo è `strike − premio`.
""",
    ),
    Section(
        "greche",
        "Le greche, una per una",
        """
Le greche misurano quanto il valore della posizione reagisce al cambiare di una
variabile. Sono derivate: dicono la reazione *istantanea*, non quella su grandi
movimenti.

**Δ Delta** — di quanto cambia il valore per +1 $ del sottostante. È
l'esposizione direzionale: un delta di 0,53 si comporta come 53 azioni. Una call
ha delta fra 0 e 1, una put fra −1 e 0, un'azione esattamente 1.

**Γ Gamma** — di quanto cambia il *delta* per +1 $ del sottostante. È la
curvatura. Gamma alto significa che l'esposizione direzionale cambia in fretta:
massimo vicino allo strike e a ridosso della scadenza. Chi è long di opzioni ha
gamma positivo, ed è la ragione per cui guadagna dai movimenti bruschi.

**Θ Theta** — quanto perde la posizione per ogni giorno che passa, a parità di
tutto il resto. Negativo per chi è net long: il tempo erode il premio. Positivo
per chi è net short — è precisamente il suo modello di business.

**ν Vega** — quanto cambia il valore per +1 punto di volatilità implicita.
Sempre positivo per chi è long di opzioni. Il vega non è una greca "greca": la
lettera ν non esiste nell'alfabeto greco con quel nome, è un'invenzione degli
operatori.

**ρ Rho** — quanto cambia il valore per +1 punto di tasso risk-free. La meno
rilevante su scadenze brevi, e la più rilevante su quelle lunghe.

Nel simulatore le greche sono **aggregate**: sommate su tutte le gambe, con
segno e quantità già applicati. È il numero che descrive la posizione nel suo
insieme.
""",
    ),
    Section(
        "volatilita",
        "Volatilità implicita e vol crush",
        """
La **volatilità implicita** non è una previsione: è il numero che, messo dentro
il modello, restituisce il prezzo che il mercato sta effettivamente facendo. In
pratica è il prezzo dell'incertezza, espresso in percentuale annua.

Sale quando il mercato si aspetta movimento — prima di una trimestrale, di una
decisione di banca centrale, di un evento societario. E crolla subito dopo,
quando l'incertezza si risolve. Questo crollo si chiama **vol crush**.

È una trappola classica: compri opzioni prima degli earnings, il titolo si muove
nella direzione giusta, e perdi comunque, perché il calo della IV toglie più di
quanto il movimento del prezzo abbia dato.

La pagina «Scenari» ha uno slider di IV **indipendente** proprio per isolare
questo effetto: tiene fermi spot, giorni e tasso, e muove solo la volatilità.
Quello che vedi cambiare è vega allo stato puro.
""",
    ),
    Section(
        "europee-americane",
        "Europee, americane ed esercizio anticipato",
        """
Un'opzione **europea** si può esercitare solo a scadenza. Una **americana** in
qualunque momento fino alla scadenza.

Quel diritto in più vale qualcosa, quindi un'americana non può costare meno
della corrispondente europea. Ma quanto vale dipende dal caso:

- **Call senza dividendi**: l'esercizio anticipato non è *mai* ottimale.
  Esercitare significa pagare lo strike prima del necessario, rinunciando agli
  interessi su quei soldi, e buttare via il valore temporale residuo. Meglio
  vendere l'opzione. Risultato: call americana ed europea valgono **identico**.
- **Put ITM**: qui l'esercizio anticipato può convenire. Incassi subito lo strike
  e cominci a percepirci interessi. Il simulatore lo mostra bene con
  `S=80, K=100, 90 giorni, r=6%`: l'americana vale ≈ 20,00 contro ≈ 19,02
  dell'europea.
- **Call con dividendi alti**: può convenire esercitare appena prima dello
  stacco, per incassare il dividendo. Alza il campo «Dividend yield» e lo vedi.

Cambiare stile di esercizio nel simulatore cambia anche il *modello* usato:
formula chiusa per le europee, albero binomiale per le americane.
""",
    ),
    Section(
        "modelli",
        "I due modelli di pricing",
        """
**Black-Scholes-Merton** è una formula chiusa: dai i parametri, ottieni il
prezzo in un calcolo diretto. Vale solo per le europee, perché assume che non si
possa esercitare prima. È istantaneo e dà anche le greche in forma esatta.

**L'albero binomiale (Cox-Ross-Rubinstein)** costruisce tutti i percorsi
possibili del prezzo su N passi discreti, poi torna indietro dalla scadenza
verso oggi. A ogni nodo confronta «tenere l'opzione» con «esercitarla adesso» e
prende il massimo: è così che il valore dell'esercizio anticipato *emerge* dal
calcolo, invece di doverlo aggiungere a mano.

L'albero converge a Black-Scholes al crescere dei passi, ma in modo oscillante:
a 500 passi dà 3,5894 contro i 3,5911 analitici. Non è un errore — è la
discretizzazione, e il simulatore ha un test che la verifica.

Un dettaglio che si vede: l'albero è O(N²) come costo. Per questo le curve del
grafico usano meno passi dei numeri che leggi a schermo. La forma è identica a
occhio, i numeri restano a precisione piena.
""",
    ),
    Section(
        "strategie",
        "Le strategie precostruite",
        """
Il menu «Strategie» è solo un punto di partenza: caricata una strategia, ogni
gamba resta modificabile.

- **Bull call spread** — compri una call ATM, ne vendi una più alta. Rialzista,
  ma sia il guadagno sia la perdita sono limitati. Costa meno di una call secca.
- **Bear put spread** — lo specchio ribassista.
- **Long straddle** — call e put sullo stesso strike. Scommetti sul *movimento*,
  non sulla direzione. Serve che si muova parecchio: paghi due premi.
- **Long strangle** — come lo straddle ma con strike diversi e più esterni. Costa
  meno, richiede un movimento più ampio.
- **Iron condor** — vendi uno strangle interno e compri le ali esterne. Guadagni
  se il titolo *non* si muove. Le ali comprate sono ciò che rende la perdita
  limitata.
- **Covered call** — possiedi 100 azioni e vendi una call. Incassi il premio in
  cambio di un tetto al guadagno.
- **Protective put** — possiedi le azioni e compri una put. È un'assicurazione:
  paghi un premio per limitare il ribasso.
- **Collar** — le due precedenti insieme: la call venduta finanzia la put
  comprata. Spesso a costo quasi nullo, in cambio di un guadagno limitato.
- **Risk reversal** — vendi una put OTM e compri una call OTM. Esposizione
  rialzista a basso costo, ma col rischio della put venduta.

Le tre che includono l'azione usano una gamba di tipo «Azione», il cui prezzo di
carico non è uno strike: è il prezzo a cui hai comprato il titolo.
""",
    ),
    Section(
        "costi",
        "Il costo reale dell'operazione",
        """
Il motore lavora per **unità di sottostante**. La pagina «Costi» traduce quei
numeri in denaro vero, con due parametri:

**Moltiplicatore contratto** — quante unità controlla un contratto. Lo standard
americano è 100.

**Pacchetti** — quante volte replichi l'intera strategia.

Il costo di una gamba è quindi `premio × moltiplicatore × contratti × pacchetti`.
Un bull call spread che "costa 2,94" per unità, con moltiplicatore 100 e 5
pacchetti, richiede 1.468 $ reali.

Un avvertimento che il simulatore non può darti in cifre: le posizioni a
**credito** (quelle che incassano premio netto) richiedono un margine presso il
broker, che può essere molto maggiore del credito incassato e non è mostrato qui.
""",
    ),
    Section(
        "premi-congelati",
        "Premi congelati: perché, e cosa cambia",
        """
Questa è una scelta di progetto che vale la pena capire, perché è la differenza
più importante rispetto a molti simulatori.

Quando apri una posizione paghi un certo premio. Quel costo è **storia**: non
cambia più. Se domani il titolo sale, cambia il *valore* della tua posizione,
non quello che hai speso per aprirla.

Molti simulatori ricalcolano il premio ogni volta che muovi uno slider. Il
risultato è fuorviante: muovendo lo spot per vedere «cosa succede se sale»,
cambia anche il costo di ingresso, e i break-even scivolano insieme al cursore.
La curva «valore oggi» finisce per passare *sempre* per lo zero al prezzo spot,
il che non insegna nulla.

Qui, con l'interruttore attivo (il default), i premi restano fissati a quando hai
aperto la posizione. Muovi lo spot e vedi il costo netto e i break-even **restare
fermi**: è il comportamento corretto.

Quando il mercato corrente si allontana dallo snapshot, compare un avviso con i
valori a cui i premi sono fissati. Serve, perché altrimenti un premio calcolato a
spot 100 mentre gli slider mostrano 115 sembrerebbe semplicemente sbagliato.

Se vuoi il comportamento tradizionale, disattiva l'interruttore.
""",
    ),
    Section(
        "limiti",
        "I limiti: cosa questo strumento non fa",
        """
Vale la pena essere espliciti, perché i modelli hanno assunzioni forti che nella
realtà non valgono.

**Volatilità costante.** Il modello assume che la volatilità sia un numero fisso.
Nella realtà cambia continuamente, ed è diversa per strike diversi (il cosiddetto
*skew* o *smile*). Qui la IV è una sola per tutta la posizione.

**Nessun salto di prezzo.** Il modello assume che il prezzo si muova con
continuità. I gap di apertura e le notizie improvvise esistono, e sono
esattamente i momenti in cui chi ha venduto opzioni scopre quanto valeva davvero
il premio incassato.

**Nessun costo di transazione.** Commissioni e spread denaro-lettera non sono
modellati. Penalizzano soprattutto le strategie a quattro gambe, dove paghi lo
spread quattro volte.

**Nessun margine.** Le posizioni a credito richiedono capitale immobilizzato che
qui non compare.

**Esercizio razionale.** L'albero assume che l'esercizio anticipato avvenga solo
quando è ottimale. Le controparti reali non sempre si comportano così.

Per questo i prezzi qui sono **teorici** e divergono da quelli di mercato. Lo
strumento serve a capire *come le variabili si legano fra loro* — cosa fa il
theta quando la scadenza si avvicina, perché il gamma esplode vicino allo
strike, quanto pesa un vol crush. Per quello è accurato e utile. Per stimare il
prezzo a cui eseguirai un ordine, no.
""",
    ),
]


@ui.page("/guida")
def guide_page() -> None:
    if not auth.require_login():
        return

    with page_frame("/guida", subtitle="Ogni aspetto dello strumento, spiegato"):
        with ui.card().classes(CARD):
            ui.label("Indice").classes("text-sm font-semibold text-[#c9cfdd] mb-1")
            ui.label(
                "Una pagina sola, in ordine di lettura. Se è la prima volta, "
                "leggila dall'inizio; altrimenti salta alla voce che ti serve."
            ).classes(FAINT)
            with ui.column().classes("gap-0 mt-2"):
                for index, section in enumerate(SECTIONS, start=1):
                    ui.link(f"{index}. {section.title}", f"#{section.anchor}").classes(
                        "text-xs text-[#5b8def] no-underline hover:underline py-0.5"
                    )

        for index, section in enumerate(SECTIONS, start=1):
            ui.link_target(section.anchor).style("position: relative; top: -70px")
            with ui.card().classes(CARD):
                ui.label(f"{index}. {section.title}").classes(
                    "text-base font-bold text-[#e6e9f0] mb-1"
                )
                ui.markdown(section.body).classes(
                    "text-sm leading-relaxed text-[#c9cfdd] "
                    "[&_table]:w-full [&_table]:text-xs [&_th]:text-left "
                    "[&_th]:py-1 [&_td]:py-1 [&_td]:pr-3 [&_th]:pr-3 "
                    "[&_code]:text-[#5b8def] [&_strong]:text-[#e6e9f0] "
                    "[&_li]:my-1"
                )

        with ui.card().classes(CARD):
            ui.label("Torna su").classes(MUTED)
            ui.link("↑ Indice", "#indice-top").classes("text-xs text-[#5b8def]")
