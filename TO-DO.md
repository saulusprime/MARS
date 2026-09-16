# MARS Beacon — TO-DO

> **Questo file è la coda di lavoro, e contiene solo ciò che deve essere
> fatto.** Il lavoro concluso si sposta in [AS-IS.md](AS-IS.md), con difetto,
> soluzione e prove, nello stesso commit che lo chiude.
>
> **Che cosa merita una casella**, deciso il 2026-08-26: un difetto aperto
> (`R##`), una fase del programma UPGRADE non dichiarata opzionale (`U##`), o
> una **prova che manca** a ciò che il codice già dichiara (`C##`). Non una
> proposta, per buona che sia: le proposte stanno in fondo, come indice, e non
> hanno una casella finché qualcuno non le decide.
>
> **Frontiera della numerazione**: correzioni fino a **R73**, idee fino a
> **I29**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Nessuna casella aperta.** Il 2026-09-15 ne sono state aperte tre e
> chiuse tutte e tre — R71, R72 e R73 — e realizzate le idee I23 e I24.
> Ognuna delle tre è nata dalla misura che chiudeva la precedente.
> Il programma UPGRADE è chiuso, salvo la fase
> che il piano stesso dichiara opzionale. Da R55 a R63 sono
> tutte aperte e chiuse il 2026-08-27, nate da osservazioni dell'utente sul
> campo e non da una revisione — due da un sospetto su `--max-pages`, tre da un
> giudizio LLM che annunciava un invio mai partito, R60 da un referto vero
> guardato da chi lo riceve, e R61 dal chiudere R60. **Il 2026-08-28 si è
> chiuso il resto**: C4/C2 verificata sul campo con una chiave vera e una
> chiamata vera, e la chiamata ha trovato **R63**; l'ultima prova mancante —
> `evaluate_answer` — chiusa lo stesso giorno, e la misura che l'ha aperta è
> che **sei mutazioni su sei** su quella funzione lasciavano la suite verde;
> **U10.1**, **U10** e **U11**, cioè le ultime fasi del programma. **I2**,
> **I8**, **I4+I9** e **I15** sono le prime idee decise dopo la chiusura del
> programma, e **I18** e' la prima voce NUOVA aperta dopo di essa — la
> correzione con esempio per l'area SEO, chiesta e chiusa lo stesso giorno: non avevano
> una casella, e l'hanno avuta quando l'utente ha detto di farle. I8 è stata
> realizzata **in forma ridotta e dichiarata**: un modulo `mars_config.py`, non
> il file di configurazione che l'idea chiedeva — la ragione sta in
> [AS-IS.md](AS-IS.md), e chi volesse il file esterno riapra una voce invece di
> credere che I8 lo abbia già fatto.
>
> `__version__` è salita a **2.10.0** con R63, perché da lì i punteggi si
> muovono a sito invariato; a **2.11.0** con U10.1, che non muove alcun
> punteggio ma aggiunge una famiglia di rilievi; a **2.12.0** con U10, a
> **2.13.0** con U11, a **2.14.0** con I2, a **2.15.0** con I4+I9, che
> aggiunge contenuto al referto, a **2.16.0** con I15, da cui i punteggi
> lessicali si muovono a sito invariato, e a **2.17.0** con I18. I8 non l'ha mossa: nessun punteggio
> cambia e nessuna interfaccia con lei. **I10** (2026-08-31) l'ha portata a
> **2.18.0**: nasce l'area «3. Prestazioni» e le aree 3-9 diventano 4-10 —
> le chiavi dei rilievi e lo storico non si muovono, il complessivo nemmeno,
> perché l'area ne resta fuori per decisione dichiarata. Il primo confronto
> del committente col PSI (2026-08-31) ha aperto e chiuso **R64** — la
> diffusione axe partiva dal massimo sul campione di una pagina, e da lì i
> punteggi WCAG si muovono a sito invariato — e ha deciso **I16**, che con
> `--form-factor` porta la versione a **2.19.0**. Lo stesso giorno si è
> decisa **I17** — il segnale «Recuperabilità» del complessivo e dei profili
> di citabilità è la media per query, che da k non dipende, e l'aggregato
> resta come diagnostica — e la versione è **2.20.0**, perché complessivo e
> profili si muovono a sito invariato. La revisione di I17 ha aperto **R65**
> — le code a punteggio zero regalavano consenso sulle query a riscontro
> parziale — chiusa lo stesso giorno: da lì le classifiche si fermano dove
> finiscono i riscontri, e la versione è **2.21.0**. Lo stesso giorno il
> committente ha chiesto di riprogettare l'hero, «poco dinamico»: **I19**
> lo ricompone — la variazione rispetto al giro precedente sale in testa,
> le tre tessere di uguale peso e il donut diventano due barre
> proporzionali, e il movimento sta dietro `prefers-reduced-motion` —
> e la versione è **2.22.0**. Il 2026-09-01 un audit eseguito dentro il
> container ha aperto e chiuso **R66**: il referto leggeva «Lighthouse non
> riuscito: CalledProcessError», cioè aveva la diagnosi dello strumento —
> `CalledProcessError` porta lo stderr — e la buttava via; quella non ha
> mosso la versione, perché nessun punteggio cambia e nessuna interfaccia.
> **Il pilota di I20** sì, a **2.23.0**: il referto guadagna contenuto —
> gli esempi delle aree SEO e Prestazioni, che nell'HTML non comparivano
> affatto, e il frammento VERO del sito dove Lighthouse lo fornisce —
> senza che alcun punteggio si muova, come per I18. **I20** è arrivata
> a **2.25.0** in tre giri — i controlli SEO, poi axe e ZAP, poi i
> controlli statici — e per la stessa ragione: il referto guadagna
> contenuto e nessun punteggio si muove — poi a **2.26.0** col giro che
> ha reso parlanti i tetti e ha portato il «quale elemento» nel piano,
> e a **2.27.0** con la prima delle tre letture di «completa»: il piano
> copre anche gli `info`.
>
> **Il 2026-09-02 il montaggio di un `.venv` a 3.10 su questa macchina ha
> aperto e chiuso R67 e R68**, tutte e due nate dall'ambiente e non da una
> revisione: la suite era verde altrove e rossa qui. **R67** — `_iso`
> passava a `fromisoformat` una `Z` che solo la 3.11 legge, e sotto un
> `unavailable_after` scaduto spariva dal referto **senza un errore**;
> **R68** — `conftest` prendeva `mars_wcag` da un `import` invece che dal
> caricatore, quindi la fixture `autouse` del locale axe rattoppava un
> oggetto morto e la suite tornava a dipendere da `npm install`. Nessuna
> delle due muove `__version__`: sugli interpreti su cui MARS gira davvero
> l'esito è identico, e la seconda è banco di prova soltanto.
>
> **Il 2026-09-03 nasce e si chiude I21**, dalla stessa via: un audit con
> `--i-own-this-domain` ha saturato la CPU per quattordici minuti ed è
> stato ucciso 72 secondi prima che MARS lo fermasse da solo. La proposta
> del committente — «un core e dieci secondi, quello che rileva rileva» —
> è stata **rovesciata da una misura**: `score_from_alerts([])` vale 100,
> quindi un budget corto non abbassa il punteggio ma lo alza. Il contratto
> dell'area 8 resta quindi intatto per sua decisione, e si costruiscono le
> due leve: `cpus: "1.0"` su ZAP in compose e `--zap-timeout` come scelta
> **dichiarata nel referto**. `__version__` sale a **2.28.0**: nessun
> punteggio si muove, ma nascono un flag, un campo API e una chiave.
> **Resta possibile e non scelta** la terza via — rendere `unavailable`
> una scansione troncata invece di lasciarle un numero: chi la volesse
> riapra una voce.
>
> **Lo stesso giorno, R69**, aperta da un «Auth error» di Swagger: la
> chiave di `FAKE_USERS_DB` e il campo `username` erano due scritture
> dello stesso nome, e cambiarne una restituiva un token valido che non
> apriva nulla — la forma di R1, tornata perche' il presidio mancava
> dove il difetto nasce. Accanto, la password in chiaro nel sorgente:
> ora l'hash si legge dal file indicato da `MARS_API_PASSWORD_HASH_FILE`,
> e il **percorso** invece del valore perche' compose divora i `$` di un
> hash bcrypt senza un errore. `__version__` a **2.29.0**: cambia il
> contratto di configurazione dell'API — non ci sono piu' credenziali
> predefinite — e non un punteggio.
>
> **Il 2026-09-04, R70**, aperta da una richiesta che chiedeva altro:
> «riavviare i container dopo ogni audit». Non serve — il riavvio era la
> cura del sintomo. `core/view/alerts` restituisce gli alert dell'intera
> SESSIONE ZAP, e MARS non ne apriva mai una nuova: il secondo audit
> dello stesso sito sommava i rilievi del primo, e il punteggio scendeva
> a sito fermo. Nello storico del committente si vede: 76 con sessione
> vergine, 30 al giro dopo, e otto audit consecutivi a 400 istanze fisse.
> `__version__` a **2.30.0**, perche' da qui i punteggi di sicurezza si
> muovono a sito invariato.
>
> **I22**, lo stesso giorno, e' la richiesta da cui R70 e' nata: «una
> chiamata API che riavvii i container». La premessa era falsa — i
> container non vanno riavviati — e l'endpoint e' stato costruito lo
> stesso, per decisione del committente, ma non serve piu' a quello. Il
> socket di Docker nel container e' stato **rifiutato**: equivale a root
> sull'host per chi raggiunge l'API. Passa un file, e a eseguirlo e' un
> sorvegliante sull'host con un proprio elenco di nomi permessi — due
> porte, e la seconda non si fida della prima. `__version__` a
> **2.31.0**: nasce un endpoint, nessun punteggio si muove.
>
> **Il 2026-09-15 una revisione della sola area 7** apre **R71** e sette
> idee, da **I23** a **I29**. Nate da una lettura del sorgente e
> **verificate lo stesso giorno sul codice in esecuzione**, mano a mano
> che l'ambiente veniva completato: **tutte e otto sono misurate**, e i
> numeri stanno in ciascuna voce. Le ultime tre — la metà axe di R71,
> I23 e I24 — hanno dovuto aspettare `npm install`, e sono cadute
> insieme appena axe-core 4.13.0 è stato disponibile. Perché proprio
> quest'area: per
> `market: eu` l'accessibilità è l'unico segnale che `mars_citability`
> moltiplica, e lo moltiplica per due
> ([mars_citability.py:93](mars_citability.py#L93)), quindi qui un difetto
> costa il doppio nel complessivo di un sito europeo. La stessa revisione
> non ha trovato traccia, in nessuno dei tre documenti, della rimozione di
> `landing/` dal repository: se quella decisione va registrata, il posto è
> [AS-IS.md](AS-IS.md), non questo file.
>
> **R71 è chiusa lo stesso giorno** e sta in [AS-IS.md](AS-IS.md):
> `estrai_immagini()` porta al modulo le marcature che esentano, e
> `_senza_alternativa()` decide quali, concordando con axe perché è lo
> stesso strumento del ramo forte. Undici mutazioni, nessuna sfuggita.
> `__version__` a **2.32.0**: da lì i punteggi WCAG si muovono a sito
> invariato, verso l'alto — 88 → 100 dove il sito aveva marcato bene le
> proprie immagini decorative. La misura che l'ha chiusa ha aperto
> **R72**, il difetto opposto — `alt=" "` vale come alternativa
> testuale e non lo è — chiusa a sua volta lo stesso giorno, in un commit
> suo perché muove i punteggi **verso il basso**: sotto una versione sola
> i due movimenti non si sarebbero più letti. `__version__` a **2.33.0**.
>
> **Da I15 si sa una cosa sui golden**: colgono un tokenizzatore morto, non
> uno sbagliato — il ritorno a `.lower().split()`, cioè la regressione di R18,
> li lascia verdi. Misurato, e scritto in [AS-IS.md](AS-IS.md): il presidio di
> `tokenize` sono i test unitari.
>
> **I principi** stanno in [.claude/principi.md](.claude/principi.md), che
> CLAUDE.md monta in ogni sessione, e valgono anche qui: una voce che per
> essere realizzata chiede di sostituire un algoritmo core con una libreria, o
> di rendere obbligatoria una dipendenza oggi opzionale, è una voce da
> riscrivere, non da eseguire.

---

## Correzioni

**Nessuna aperta.**

---

## Completamento

**Nessuna aperta**

---

## Idee

- **I7** — `--compare a.com b.com c.com` con tabella affiancata.
- **I11** — verificare gli `@type` del JSON-LD contro i tipi che gli
  assistenti usano davvero, non solo la sintassi (lo dice
  [mars_schema.py:67](mars_schema.py#L67)).
- **I14** — tetto alla dimensione della risposta HTTP: `_get` scarica il corpo
  intero senza `stream` né limite, e il `timeout` copre solo l'attesa fra i
  byte.

- **I20** — **resta una decisione, ed è tua.** Il committente ha scelto
  il 2026-09-01 la prima delle tre letture di «completa»: il piano copre
  ogni rilievo che descriva un difetto del sito, `info` compresi. Sta in
  [AS-IS.md](AS-IS.md), insieme al difetto che quella scelta ha scoperto
  — tre controlli Lighthouse **non falliti** erano entrati nel piano, e
  ora ne restano fuori per la penalità dichiarata.

  - **Privacy.** Il referto incorpora contenuto del sito: uno `src`, il
    testo di un titolo, il valore di un header.
    [CLAUDE.md](CLAUDE.md) impone di oscurare i dati personali, e oggi
    il contenuto entra intero. Il presidio contro l'**esecuzione** c'è
    ed è provato con un payload vero; l'**oscuramento** no, perché è
    una scelta e non una misura.

  *Le altre due letture di «completa» restano possibili e non sono
  state scelte*: colmare i 12 esempi mancanti a catalogo, e l'ordine di
  lavoro per istanza — che ora è quasi solo resa, perché gli elementi
  ci sono.

  *Una cosa che il piano non dice ancora*: la vista testo si ferma a
  cinque voci e dichiara il troncamento, quella HTML le stampa tutte.
  Con 27 voci la differenza si vede.

### Area 7 — accessibilità

Sette voci aperte dalla revisione del 2026-09-15, **tutte verificate in
esecuzione**: il numero sta in ciascuna. **I23, I24 e I25 sono realizzate** e stanno in
[AS-IS.md](AS-IS.md); restano quattro. Suite e presidio nello stesso giro:
`flake8 .` a zero, `pytest` **1433 passati e nessuno saltato** — con
`node_modules` installato il test axe non si salta più, e la suite resta
ferma a 22 secondi, cioè la neutralizzazione di R20 regge e Chromium non
parte. Misurate prima su Python 3.14.4 e **rimisurate sulla 3.10.12** dopo
la ricostruzione della venv: stesso esito sui due interpreti.

- **I26** — **il tabindex non sa dire quale elemento.** È l'unico dei sette
  controlli statici senza `cita()` ([mars_wcag.py:277](mars_wcag.py#L277)),
  perché `estrai_struttura` porta i valori e non gli elementi che li hanno
  ([mars_core.py:1301](mars_core.py#L1301)). «3 elementi con tabindex positivo»
  si corregge cercandoli a mano: è la domanda di I20, rimasta senza risposta in
  un punto solo dei sette. **Misurato**: su una pagina con `tabindex="3"` su un
  `div#menu` e `tabindex="5"` su un link, il crawler consegna `['3', '5']` e il
  rilievo esce con `cited` **assente**.

- **I27** — **il campione axe è una costante, non una scelta.**
  `MAX_PAGINE_AXE = 5` ([mars_wcag.py:58](mars_wcag.py#L58)) non è un flag né
  un campo API, mentre ogni altro confine del perimetro — `--max-pages`,
  `--max-children`, `--zap-timeout` — è una scelta dichiarata. Prima di farne
  una leva, misurare: la diffusione normalizza sulle pagine **analizzate**
  ([mars_wcag.py:515](mars_wcag.py#L515)). **Misurato il 2026-09-15** su
  `score_from_violations`, che è pura: allargare il campione da 5 a 10 pagine
  **non muove il punteggio** a violazioni invariate — 50 e 50 con una regola
  presente ovunque, 75 e 75 con una regola sulla sola home — ma lo abbassa
  appena il campione più largo trova **una regola in più**: 50 → 38. Vale
  quindi la stessa asimmetria di I21, e per la stessa ragione: zero
  violazioni valgono 100, quindi un campione corto non può che alzare il
  punteggio. Due referti con campioni diversi non si confrontano alla pari,
  ed è questo — non la taratura — che rende la costante una scelta da
  dichiarare.

- **I28** — **1.2.x non lo guarda nessuno dei due rami.** Sottotitoli e
  trascrizioni sono criteri di livello A: axe non li controlla e il markup non
  li contiene. Una cosa però il markup la dice — se esistano `<video>` o
  `<audio>`, e se abbiano un `<track kind="captions">`. Un `info` che dice dove
  guardare, non un punteggio: è la forma che I20 ha già scelto per gli `info`,
  e costa un campo in `estrai_struttura`. **Misurato**: su una pagina con un
  `<video>` e un `<audio>`, le chiavi che arrivano al modulo sono otto —
  `form_fields`, `heading_levels`, `heading_texts`, `images`, `lang`, `links`,
  `tables`, `tabindex` — e nessuna riguarda i media.

- **I29** — **«WCAG 2.1 A + AA» si legge come conformità.** Nel ramo axe il
  referto stampa strumento, livello e «5 pagine esaminate»
  ([mars_report.py:1295](mars_report.py#L1295)), e tace due cose che sa: quanta
  parte dei criteri un controllo automatico non può vedere, e che quelle cinque
  pagine stanno dentro un `pages_total` che il risultato porta e la riga non
  stampa. Il ramo di ripiego è onesto — «parziale: solo criteri statici» — il
  ramo forte no, ed è il ramo forte quello che finisce davanti al committente.
  Col peso doppio dell'EAA sull'area, la distanza fra «misura automatica» e
  «conformità» è quella fra un referto e una dichiarazione. **Misurato** su
  un'area con `pages_tested: 5` e `pages_total: 40`, `_qualificatori` rende
  `['axe-core', 'WCAG 2.1 A + AA', '5 pagine esaminate', 'Lighthouse 97/100
  (1 pagina, scala diversa: la nostra è più severa)']`: il 40 il risultato ce
  l'ha e la riga non lo stampa.
