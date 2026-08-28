# MARS Beacon — AS-IS

> Registro del lavoro **completato e verificato**. Le voci escono da
> [TO-DO.md](TO-DO.md) e arrivano qui solo dopo che la correzione è stata
> eseguita e provata, così che nessuno debba rifare la stessa indagine.
>
> Gli identificativi (R1, C3, U4.2, …) restano quelli del TO-DO, e **il codice
> li cita**: ogni identificativo nominato da un sorgente o da un altro
> documento atterra qui: le sotto-voci delle fasi UPGRADE hanno una
> [mappa](#mappa-delle-sotto-voci) dentro la voce di fase.
>
> **Potato il 2026-08-26**, da 6001 righe a circa un quarto. Il criterio: ogni
> voce conserva **il difetto**, **la misura che ha smentito una previsione** e
> **la decisione col suo perché**; è uscito il racconto della lavorazione —
> conteggi di mutazioni voce per voce, confronti con `git show`, «la suite
> passa da N a M test», le ricopiature del codice e gli elenchi di spunta di
> ciò che il commit toccava. Quelle cose avevano un lettore mentre il lavoro si
> faceva; il presidio, adesso, sono i test e i golden.
>
> Le mutazioni **sfuggite alla prima esecuzione** restano tutte, perché sono
> l'unica parte del racconto di verifica che dice qualcosa di nuovo: ciascuna
> ha rivelato un test che sembrava corretto e non lo era.
>
> Il testo integrale è nella storia di git: `git show 0753405:AS-IS.md`.

## Indice

| ID | Voce | Data |
|---|---|---|
| R1 | Login dell'API completamente rotto | 2026-08-19 |
| R2 | `/users/me` restituiva l'hash della password | 2026-08-19 |
| R3 | Command injection remota in `mars_seo.py` | 2026-08-19 |
| R4 | Punteggi inventati in `mars_wapt.py` e `mars_seo.py` | 2026-08-19 |
| R5 | `/audit/full` ricrawlava il sito 8 volte | 2026-08-19 |
| R6 | Crash su `<title>` vuoto e tre casi limite vicini | 2026-08-19 |
| R7 | Il crawler non era un buon cittadino della rete | 2026-08-19 |
| R8 | Il proxy char-TFIDF era quadratico | 2026-08-19 |
| R9 | Euristica "answer-shaped" imprecisa e monolingue | 2026-08-19 |
| R10 | I "chunk" non erano chunk; l'RRF fondeva granularità diverse | 2026-08-19 |
| R11 | Igiene del codice (11 voci, 2 commit) | 2026-08-19 |
| R12 | Incoerenze nel README; documentata l'API REST (con C11) | 2026-08-19 |
| R13 | Allineamento allo stile di riferimento | 2026-08-19 |
| R14 | Il campo `disabled` non era mai applicato | 2026-08-19 |
| R15 | Un solo URL malformato faceva cadere l'intero audit | 2026-08-20 |
| R16 | Mojibake silenzioso sui siti UTF-8 senza charset | 2026-08-20 |
| R17 | I redirect non venivano rivalidati | 2026-08-20 |
| R18 | La punteggiatura escludeva le parole da BM25 | 2026-08-20 |
| — | Referto HTML nello stile di Lighthouse | 2026-08-20 |
| R19 | I segnali di pagina gonfiavano `answer_shaped_ratio` | 2026-08-20 |
| R20 | axe fabbricava un 100/100; la suite lanciava Chromium | 2026-08-20 |
| R21 | «Di superficie» era indistinguibile da una misura piena | 2026-08-20 |
| R22 | L'esecutore di moduli non reggeva i plugin che rompono | 2026-08-20 |
| — | La sezione SEO riporta i controlli di Lighthouse | 2026-08-20 |
| R23 | Query perse con un retriever caduto; ranghi a informazione zero | 2026-08-20 |
| R24 | Casi limite del crawler sugli URL (IPv6, loc relativi, robots vuoto) | 2026-08-20 |
| R25 | La direttiva robots `none` non veniva vista | 2026-08-20 |
| R26 | Tre difetti di `mars_wcag` (alt vuoto, delay morto, riparsing) | 2026-08-20 |
| R34 | I titoli di sezione non sono domande | 2026-08-21 |
| R27 | Il timeout ZAP non fermava la scansione | 2026-08-21 |
| R38 | Il referto copre tutti e nove gli ambiti | 2026-08-21 |
| U1 | Modello dati dei rilievi (`Finding`); `__version__` a 2.1.0 | 2026-08-24 |
| U2 | Golden del referto: tre formati, due referti sintetici | 2026-08-24 |
| U3 | Testi `fix` ed `example`; `__version__` a 2.2.0 | 2026-08-24 |
| U4 | Piano di interventi; `__version__` a 2.3.0 | 2026-08-25 |
| R45 | Due numeri sulla stessa area, e perché differiscono | 2026-08-25 |
| U5 | Complessivo, hero e ancore; `__version__` a 2.4.0 | 2026-08-25 |
| R41 | `derived` ha finalmente dei lettori | 2026-08-25 |
| U6 | Markdown e CSV; `__version__` a 2.5.0 | 2026-08-25 |
| U7 | Riproducibilità e storia; `__version__` a 2.6.0 | 2026-08-25 |
| U8 | Analisi della superficie; `__version__` a 2.7.0 | 2026-08-25 |
| U9 | i18n del referto (it/en); `__version__` a 2.8.0 | 2026-08-25 |
| R44 | Nel ramo axe il referto parlava inglese | 2026-08-25 |
| I1 | Audit differenziale — realizzata da U7, in altra forma | 2026-08-25 |
| I13 | Test diretti del `Crawler` — realizzata da R15-R24 | 2026-08-25 |
| — | Programma UPGRADE: le decisioni D1-D4 e il quadro delle fasi | 2026-08-25 |
| R63 | Il menu di navigazione non entra più nel corpus | 2026-08-28 |
| C4/C2 | Il giudizio LLM eseguito contro il servizio reale | 2026-08-28 |
| I3 | Il k della fusione esposto, e la sua sensibilità misurata | 2026-08-27 |
| U11.1 | Il referto HTML prende la palette del sito, e un tema solo | 2026-08-27 |
| R62 | Non si capiva che cosa scrivere nel file di `--credentials` | 2026-08-27 |
| R61 | «Correzione:» nel CSS: un referto inglese lo diceva in italiano | 2026-08-27 |
| R60 | Gli esempi di correzione si leggevano come contenuto misurato | 2026-08-27 |
| R59 | Diagnostica e referto sullo stesso canale: il JSON non si rileggeva | 2026-08-27 |
| R58 | L'annuncio della spesa si stampava anche quando nulla partiva | 2026-08-27 |
| R57 | Le chiavi dalla riga di comando, e un `main()` che si esegue | 2026-08-27 |
| R56 | `--max-children`, e un perimetro dichiarato inesatto | 2026-08-27 |
| R55 | Lo spider di ZAP non rispettava robots.txt | 2026-08-27 |
| R54 | Il parametro inerte nascondeva un audit assente | 2026-08-27 |
| R53 | I conteggi di `mars_seo` e i tre testi di Lighthouse | 2026-08-27 |
| R48 | Dal JavaScript del grafo esce anche la geometria | 2026-08-26 |
| R46 | Il conteggio delle istanze è canonico; lo sforzo ci scala | 2026-08-26 |
| R40 | Tre difetti di `mars_seo` (categoria, testi, item) | 2026-08-26 |
| R39 | `alertRef` non veniva mai raggiunto; migrazione di chiavi | 2026-08-26 |
| R51 | Il `<meta name="googlebot">` non aveva un agente | 2026-08-26 |
| U13 | Le due aree di classifica non avevano un solo controllo | 2026-08-26 |
| R47 | Nessun rilievo dichiarava la pagina che lo aveva prodotto | 2026-08-26 |
| R32 | Deriva fra documentazione e codice, dieci righe | 2026-08-26 |
| R30 | `VectorRetriever` moriva sul corpus vuoto, in un ramo su due | 2026-08-26 |
| R31 | Un file di query vuoto era un successo muto; il rifiuto LLM non aveva un ramo | 2026-08-26 |
| R29 | Un audit bloccava l'API per tutti gli altri client | 2026-08-26 |
| R43 | La favicon dichiarava un MIME che non era il suo, e spariva in silenzio | 2026-08-26 |
| R42 | La citabilità spariva dalla vista testo proprio quando falliva | 2026-08-26 |
| C13 | File di progetto: git, CLAUDE.md, CONTRIBUTING, CoC | 2026-08-19 |
| C1+C7 | Profili di citabilità IA; riuso dei risultati fra moduli | 2026-08-19 |
| C2 | Giudizio LLM sulla citabilità (`mars_llm_judge.py`) | 2026-08-19 |
| — | Caricatore di moduli: cache, e bytecode stantio corretto | 2026-08-20 |
| — | Aiuto della CLI: valori, esempi, avvertenze | 2026-08-20 |
| C12 | Suite di test, verificata reintroducendo i difetti | 2026-08-20 |
| C10 | `mars_tech` copre indicizzabilità, sitemap e 13 crawler IA | 2026-08-20 |
| — | Verifica sistematica dei parametri API; `max_pages` corretto | 2026-08-20 |
| — | Credenziali nella richiesta API | 2026-08-20 |
| C9 | WAPT via ZAP, verificato contro il daemon 2.17 reale | 2026-08-20 |
| C8 | WCAG reale via axe-core su Chromium | 2026-08-20 |
| C6 | Crawling interno quando manca la sitemap | 2026-08-20 |
| C5 | Query personalizzate e consenso RRF aggregato | 2026-08-20 |
| C4 | Referto JSON e HTML; l'API riusa la struttura canonica | 2026-08-20 |
| C3 | Monitoraggio delle citazioni IA (`mars_citations.py`) | 2026-08-19 |
| — | Manutenzione: caricatore di moduli e import pigro | 2026-08-19 |
| — | Decisione: stile di riferimento del progetto | 2026-08-19 |

---
### R1 — ✅ RISOLTO (2026-08-19): il login dell'API era completamente rotto
**Il difetto.** `verify_password` era definita **due volte** in `mars_api.py`:
la seconda (passlib/bcrypt) sovrascriveva la prima (SHA256 timing-safe), ma
`FAKE_USERS_DB` era popolato con uno SHA256 esadecimale, che passlib non sa
identificare (`UnknownHashError`). `POST /token` rispondeva **500** con le
credenziali documentate nella propria docstring, e **tutti e otto gli endpoint
protetti erano irraggiungibili**: l'intera superficie API inutilizzabile.

**Come è stato trovato.** `flake8 --select=F` lo segnalava come `F811`. È il
motivo per cui la regola «flake8 a zero» sta in CLAUDE.md: il difetto più
grave del progetto era un avviso di lint che nessuno leggeva.

**La soluzione.** Tenuta la versione passlib/bcrypt, con la coppia
`get_password_hash` / `verify_password` spostata **sopra** `FAKE_USERS_DB`,
che la invoca all'import.

### R2 — ✅ RISOLTO (2026-08-19): `/users/me` restituiva l'hash della password
**Il difetto.** `User` includeva `hashed_password` ed era il `response_model`
di `GET /users/me`: l'hash bcrypt finiva nel corpo della risposta **e nello
schema OpenAPI pubblicato su `/docs`**. Il codice mostrava l'intenzione
originale — `# return UserInDB(**user_dict)` — ma `UserInDB` non era mai stato
scritto.

**La soluzione, e perché a due livelli.** `User` è il modello pubblico,
`UserInDB(User)` quello interno. `get_current_user()` proietta esplicitamente
su `User` invece di restituire l'oggetto interno: così un endpoint che
dimenticasse `response_model` **non potrebbe** far uscire le credenziali,
perché l'oggetto non le contiene. Il solo filtro di `response_model` avrebbe
funzionato, ma sarebbe stato una protezione a un livello solo.

### R3 — ✅ RISOLTO (2026-08-19): command injection remota in `mars_seo.py`
**Il difetto.** L'URL veniva interpolato in una stringa di shell passata a
`subprocess.run(..., shell=True)`. L'URL arriva dall'utente: da riga di
comando e — da quando R1 ha reso l'API raggiungibile — dal **corpo della
richiesta** di `POST /audit/seo`. Sfruttabilità dimostrata con un comando
innocuo su codice nostro: `https://esempio.it/; touch <file> #` creava il file.

**La mitigazione che non era una mitigazione.** `pydantic.HttpUrl`
percent-codifica gli spazi, il che smorza i payload più banali. Non è una
difesa: è un effetto collaterale della normalizzazione, `;` e i backtick
restano letterali, e un comando senza spazi passa.

**La soluzione.** Lista di argomenti e `shell=False`, così l'URL è un solo
argomento e la shell non lo interpreta mai. Più `shutil.which("lighthouse")`
per la diagnosi e un `timeout` di 120 s, perché Lighthouse può bloccarsi a
tempo indeterminato. L'`except Exception` generico è diventato specifico:
prima mascherava anche gli errori di programmazione.

**Il dettaglio che costa un'ora se sfugge.** In `--chrome-flags='--headless'`
le virgolette erano **sintassi di shell**. In una lista di argomenti vanno
tolte, altrimenti Lighthouse riceve gli apici dentro il valore.

Contestualmente la parte SEO di **R4**: il ripiego non restituisce più
`score: 0` — il peggior giudizio possibile — ma `score: None` con
`status: "unavailable"`.

### R4 — ✅ RISOLTO (2026-08-19): punteggi inventati in `mars_wapt.py` e `mars_seo.py`
**Il difetto.** `mars_wapt` restituiva `95` se `zap-cli quick-scan` usciva con
0 e `60` altrimenti: due numeri che non corrispondevano ad alcuna
vulnerabilità.

**E l'exit code era letto al contrario.** La CLI documenta: *«If any alerts
are found for the given alert level, this command will exit with a status code
of 1»*. Il ramo che assegnava 60 con la nota «ZAP ha rilevato potenziali
vulnerabilità» scattava quindi sui **risultati**, e quello da 95 quando ZAP
**non trovava nulla** — cioè proprio quando il sito era pulito. Non erano solo
numeri finti: era una lettura invertita dello strumento.

**Due errori del TO-DO stesso, corretti leggendo la CLI installata** invece
che la memoria: `zap-cli report` produce xml/html/md e **non** JSON (serve
`alerts -f json`), e `quick-scan --self-contained` **spegne il daemon a fine
scansione**, quindi dopo non si possono più leggere gli alert.

**La soluzione.** Logica separata dall'I/O: `score_from_alerts(alerts)` pura
(100 meno le penalità per rischio, i pesi costanti dichiarate in testa perché
sono una scelta editoriale e non una misura), `run_zap()` come sola parte con
I/O che restituisce `None` invece di sollevare, `audit_headers()` come ripiego
con `status: "surface"`.

**Verificato** con payload sintetici: sito pulito 100; 1 High 75; 2 Medium 80;
1 High + 1 Medium + 3 Low 56; **`"High (Medium)"`** — rischio con la confidenza
fra parentesi — 75; 10 alert informativi 100; alert con campi mancanti nessun
crash.

> Quella riga è citata da **R32**, ancora aperta, che chiede di ricontrollare
> **da dove venisse** l'osservazione del `"High (Medium)"`: la lettura del
> sorgente di ZAP dice che `core/view/alerts` non compone mai rischio e
> confidenza in un campo solo — `"High (Medium)"` è `riskdesc`, che
> quell'endpoint non emette. È un fatto registrato, e si annota invece di
> riscriverlo. Lo `split(" ")[0]` resta comunque come difesa verso gli alert
> che non nascono dalle regole di serie.

**Il limite dichiarato allora**, e chiuso poi da C9: il daemon ZAP non era
installato, quindi `run_zap()` era scritto sull'interfaccia documentata ma mai
eseguito fino in fondo.

### R5 — ✅ RISOLTO (2026-08-19): `/audit/full` ricrawlava il sito 8 volte
**Il difetto, misurato con un crawler strumentato: 8 crawl per una sola
richiesta.** `run_single_audit` chiamava `build_context()` a ogni modulo; una
riga in più recuperava `urls` con un'ottava scansione, accompagnata dal
commento onesto `# Ricalcolo veloce, in prod cacheare`. Su `max_pages=25` sono
200 richieste HTTP invece di 25 — e, peggio, i moduli potevano osservare
**stati diversi del sito**, rendendo i loro punteggi non confrontabili.

**La soluzione.** `build_context()` spostata in `mars_core`, dove diventa
l'unica fonte di verità (prima CLI e API scrivevano lo stesso dizionario due
volte), e `run_single_audit` riceve il **contesto già costruito**. Restituisce
`None` se il sito è irraggiungibile: tradurlo in un errore HTTP spetta al
chiamante, non al core, che non deve conoscere FastAPI.

**Un secondo difetto emerso qui.** Il `try/except Exception` attorno a ogni
modulo inghiottiva anche l'`HTTPException` di `build_context`: con un sito
irraggiungibile `/audit/full` rispondeva **200** con «Modulo fallito» sette
volte, mentre i sette endpoint singoli rispondevano 404. Ora il contesto si
costruisce fuori dal ciclo e il 404 propaga.

Verificato dopo: 1 crawl. Sito irraggiungibile: 404 da tutti.

### R6 — ✅ RISOLTO (2026-08-19): crash su `<title>` vuoto, e tre casi limite vicini
**Il difetto.** `soup.title.string` su `<title></title>` è **`None`**, non
`""`. Quel `None` finiva in `pages[url]["title"]` e poi dentro `" ".join()` in
`mars_lexical`: `TypeError`. Un solo `<title></title>` in tutto il sito faceva
cadere il modulo lessicale e con esso la simulazione RRF — il cuore del
progetto.

**La soluzione, su quattro punti.** `get_text(strip=True)` nel crawler; difesa
a valle in `mars_lexical`, perché un modulo non deve fidarsi ciecamente del
`context`; guardia esplicita su `avgdl == 0` in `LexicalRetriever`, che era una
protezione **accidentale** che un refactor avrebbe potuto togliere senza
accorgersene; `score: None` + `status: "unavailable"` in `mars_wcag` e
`mars_schema` con `pages` vuoto (prima `IndexError`).

**Vuoto ≠ malformato.** `json.loads(None)` sollevava `TypeError`, che
l'`except Exception` riportava come «JSON-LD malformato»: **diagnosi
sbagliata**, il blocco era vuoto. Ora si distingue `vuoto` (−5) da
`malformato` (−10) e si cattura `json.JSONDecodeError`.

**Una previsione smentita, e corretta nei commenti.** Era scritto — nel TO-DO
e in un primo commento — che `.string` è `None` anche quando il tag ha più di
un figlio. Con lxml **non vale** per `<title>` e `<script>`, che sono elementi
a testo grezzo: lì `.string` è `None` solo se l'elemento è vuoto.

### R7 — ✅ RISOLTO (2026-08-19): il crawler è ora un buon cittadino della rete
**Il difetto.** `Crawler` era un ciclo di `requests.get` su `/sitemap.xml`.
Nove difetti, il più imbarazzante dei quali: uno strumento che *valuta*
robots.txt in `mars_tech` non lo rispettava.

**robots.txt, con dichiarazione di proprietà.** L'unico modo per ignorarlo è
una dichiarazione esplicita — `--i-own-this-domain`, `i_own_this_domain` via
API. Non è un interruttore di comodo: il nome del flag *è* la dichiarazione,
l'uso stampa un avviso, e il fatto è registrato in `context["robots_ignored"]`
e dichiarato nel referto. Via API è per di più attribuibile all'utente
autenticato.

**Due trappole di `robotparser`, verificate prima di scrivere il codice** (e
oggi in CLAUDE.md): un parser su cui non si è mai chiamato `parse()` risponde
**`False` a ogni `can_fetch()`**, quindi va chiamato `parse([])` anche quando
robots.txt manca; e `crawl_delay()` per un agente specifico **non eredita**
da `*`.

**Gli altri otto.** User-Agent proprio; pausa fra le richieste che cede al
`Crawl-delay` del sito se più alto; scarto delle risposte non-200, che prima
finivano nel corpus BM25 come pagine d'errore falsando i ranking; controllo
del `Content-Type`, che prima faceva parsare i PDF come HTML; normalizzazione
degli URL; filtro same-host; sitemap dalle direttive di robots.txt prima che
da `/sitemap.xml`, con indici annidati e `.xml.gz`; timeout configurabile.

**Il referto dichiara cosa non ha guardato**: `skipped` porta il motivo di
ogni URL scartato. Dodici pagine saltate cambiano il significato di ogni
punteggio, e tacerlo sarebbe una bugia per omissione.

Verificato con un server HTTP locale costruito apposta, che riproduce
robots.txt con `Disallow` e `Crawl-delay`, un `<sitemapindex>` che punta a una
sitemap compressa, un URL con frammento, un host esterno, un 404 e un PDF.

### R8 — ✅ RISOLTO (2026-08-19): il proxy char-TFIDF era quadratico
**Il difetto.** Per **ogni n-gramma della query** si ri-tokenizzava l'intero
corpus, benché le document frequency fossero già state calcolate in
`_build_proxy()` e buttate via. Il prodotto scalare iterava poi il vocabolario
intero per ogni documento, e la norma di ogni documento veniva ricalcolata a
ogni query.

**La soluzione.** `self.df` conservato e letto da un `_idf()` condiviso;
vettori sparsi; `doc_norms` precalcolate; il prodotto scalare itera **la
query** (poche decine di n-grammi) cercando nel documento.

**Misurato**, corpus sintetico, vocabolario ~17.000 trigrammi:

| N documenti | query prima | query dopo |
|---|---|---|
| 20 | 0,087 s | 0,0001 s |
| 80 | 0,395 s | 0,0004 s |

Circa **1000× per query**. Prima il tempo cresceva linearmente col numero di
documenti — il sintomo del difetto; ora è piatto. Scarto fra i punteggi prima
e dopo: **0.00e+00**, non «entro tolleranza» — identici.

**Una previsione del TO-DO non si è avverata.** Era scritto che i vettori
densi sprecavano memoria e che lo sparso avrebbe risolto. Misurato: 5,8 → 5,6
MB, 18,3 → **19,0** MB. Nessun guadagno. La ragione, misurata: ogni documento
contiene in media 2.490 n-grammi distinti su 17.303, cioè una **densità del
14%**; un `dict` costa ~100 byte per voce contro gli 8 di una cella di lista,
e sotto l'8% circa lo sparso vince, sopra pareggia. Il guadagno di R8 è la
velocità, non la memoria.

### R9 — ✅ RISOLTO (2026-08-19): l'euristica "answer-shaped" era imprecisa e monolingue
**Il difetto.** `any(w in chunk.lower() for w in [...])` era un test di
**sottostringa**: `chi` dentro *chiave, chiaro, macchina, archivio*, `cosa`
dentro *qualcosa*, `dove` dentro *dovere*.

**Due affermazioni del TO-DO erano sbagliate**, corrette misurando: `"come"`
**non** matcha *comodo* (che contiene «como»), e la metrica **non** era vicina
a zero sull'inglese, perché `"?"` era nell'elenco. Restava cieca solo sulle
domande senza punto interrogativo in lingue diverse dall'italiano.

**I confini di parola da soli non bastavano**, ed è la misura che ha
determinato la soluzione: eliminano i falsi positivi da sottostringa ma non
quelli grammaticali, perché in italiano gli interrogativi sono anche
congiunzioni — *«comodo **come** la neve»*, *«il luogo **dove** abbiamo
aperto»*. Da qui un segnale **posizionale**.

**La soluzione.** Quattro segnali indipendenti: punto interrogativo;
interrogativo **a inizio frase** (ciò che distingue una domanda da una
congiunzione); titolo interrogativo fra gli `headings`, segnale molto più
forte di un termine nel corpo; `FAQPage` JSON-LD. Cinque lingue scelte da
`lang`; senza lingua nota si provano tutte, perché un falso positivo è
preferibile a una metrica sistematicamente a zero.

Effetto collaterale voluto: `lang=""` conta ora come mancante, dove
`has_attr('lang')` lo accettava — una stringa vuota non è una dichiarazione di
lingua valida (WCAG 3.1.1).

**Verificato** su 10 casi costruiti (4 falsi positivi noti, 6 vere domande in
5 lingue): la vecchia euristica sbagliava 7 volte, la nuova **10 su 10**.

### R10 — ✅ RISOLTO (2026-08-19): i "chunk" non erano chunk
**Il difetto.** Un chunk erano i **primi 500 caratteri** di una pagina —
tipicamente il menu di navigazione. Ma il danno peggiore era a valle:
`mars_lexical` indicizzava le **pagine** (primi 1000 caratteri) e
`mars_semantic` i **chunk**, e i due ranghi venivano fusi dall'RRF **come se
si riferissero alle stesse unità**. Il «consenso Top-3» non aveva il
significato dichiarato nel README, che presenta l'RRF come il cuore del
progetto.

**La soluzione.** `chunk_page()` segmenta una pagina in passaggi
autoconsistenti — un heading più il testo che lo segue — con le sezioni lunghe
divise in finestre da 1000 caratteri e **150 di sovrapposizione**, tagliate su
confine di parola: la sovrapposizione serve a non spezzare a metà
un'affermazione, perché un passaggio citabile deve reggersi da solo.

**Perché si cammina sui nodi di testo e non sugli elementi di blocco.** Con
`find_all(["p", "li", ...])` il testo di un `<p>` dentro un `<li>` verrebbe
contato due volte, gonfiando il chunk. Con `descendants` ogni nodo è visitato
una volta sola.

La segmentazione avviene **dentro il crawler**, dove il DOM è già in memoria.

**Prova decisiva.** Pagina di 1051 caratteri con la risposta utile che comincia
al carattere **841**:

```
PRIMA (primi 500 caratteri) : 'preventivo' presente? False
DOPO  (segmentato)          : [1] 'Come si richiede un preventivo?'  True
query "come richiedere un preventivo"
  rango lessicale [1, 0]   rango vettoriale [1, 0]   vincitore RRF: chunk 1
```

Contenuto prima invisibile, ora trovato da entrambi i recuperatori, che
concordano perché finalmente ordinano le stesse cose.

**Ciò che R10 NON ha controllato**, e che è costato R35: che i due
recuperatori leggessero lo stesso *contenuto* di quelle unità.

### R11 — ✅ RISOLTO (2026-08-19): igiene del codice
Undici voci, in **due commit separati** — sostanza e formattazione — perché
mescolarle rende la revisione impossibile. È la regola fissata poi in R13.

**`pip install -r requirements.txt` falliva**: `bcrypt=4.0.1` non è una
specifica PEP 508 valida. Il file è ora diviso per ruolo, con le dipendenze
che il codice importa davvero e senza quelle che nessuno importa. Il pin di
bcrypt porta scritta la ragione: passlib 1.7.4 non sa leggere bcrypt ≥ 4.1 e
solleva `AttributeError`.

**`SECRET_KEY` non è più nel sorgente**: si legge da `MARS_SECRET_KEY`, e in
sua assenza se ne genera una effimera con un avviso. I token scadono a ogni
riavvio, il che rende il ripiego inutilizzabile in produzione — è il punto.

**Il difetto della directory di lavoro**, il peggiore del gruppo perché
sembrava un risultato: `load_external_module()` risolveva il percorso rispetto
alla CWD, quindi lanciato da un'altra cartella il programma non trovava un
solo modulo e stampava serenamente «ignorato» per tutte e sette le aree,
producendo un referto vuoto **senza un errore**. Ora si risolve da `__file__`.

**Un parse invece di tre.** Il crawler estrae `json_ld` e `images` mentre ha il
DOM in memoria; `mars_schema` e `mars_wcag` non riparsano più. Si estraggono
**dati grezzi, non giudizi**: decidere che cosa sia un difetto resta dei
moduli.

Più: `MODULES_REGISTRY` e `load_external_module()` deduplicati in `mars_core`;
`datetime.utcnow()` (deprecata) sostituita; `openapi.json` rinominato in
`examples/audit_request.json`, perché non era una specifica ma un payload con
dentro un URL reale; `setup.cfg` e flake8 **da 49 avvisi a zero**.

### R12 — ✅ RISOLTO (2026-08-19): incoerenze nel README
Documentata l'API REST (chiude **C11**): `mars_api.py` è metà del progetto e il
README lo citava solo come elenco di pacchetti. L'elenco degli endpoint **non
è stato scritto a memoria**, ma estratto dalla specifica che FastAPI genera,
così non può divergere dal codice.

**Ogni comando documentato è stato eseguito, non solo scritto** — ed è così che
è emerso il caso che il README ora avverte: sulla macchina di sviluppo la porta
8000 è occupata da un'altra applicazione, uvicorn non si agganciava ed
**usciva**, ma le richieste continuavano a ricevere risposta da quell'altra
applicazione. I 404 sembravano venire da MARS.

Aggiunta l'avvertenza sul virtualenv per il blocco `zap-cli`, che contiene
`pip uninstall -y urllib3 requests six`: sul Python di sistema può rompere
strumenti del sistema operativo.

### R13 — ✅ RISOLTO (2026-08-19): allineamento allo stile di riferimento
Previsto graduale, completato in una sessione ma rispettandone la regola: **due
commit separati**, uno di sole annotazioni e uno di sostanza. Buona parte era
già stata fatta opportunisticamente correggendo R3, R4, R9, R10 e R11.

**`__version__` vive in `mars_core` ed è l'unica fonte**: alimenta User-Agent,
`--version` e la versione dell'API, che erano tre stringhe indipendenti
destinate a divergere.

**Codici di uscita.** Un audit su sito irraggiungibile usciva con **0**, cioè
«successo»: nessuna pipeline poteva distinguerlo da un audit riuscito.

**Un punto è stato deliberatamente NON applicato**, ed è la decisione che
regge ancora il progetto. Il principio 8 chiedeva `@dataclass` al posto dei
dizionari anonimi; applicato al `context` e a ciò che contiene avrebbe violato
il **principio 3**, perché quelle strutture attraversano il confine dei plugin
e imporre classi di `mars_core` costringerebbe ogni modulo esterno a
importarle. I dataclass restano per le strutture interne a un modulo.

Verificato che nulla cambia, numeri alla mano: BM25 `[0.470004, 0.0,
0.578466]`, RRF `[(0, 0.032266458), (2, 0.032266458), (1, 0.032258065)]`. Il
cambio di User-Agent da `MARSBeacon/2.0` a `2.0.0` non altera il rispetto di
robots.txt: `robotparser` confronta la parte prima della barra.

### R14 — ✅ RISOLTO (2026-08-19): il campo `disabled` non era mai applicato
**Una classificazione sbagliata, e va detto.** Era marcato 🔴 CRITICO.
Verificando su domanda dell'autore: nessun endpoint crea o modifica utenti,
`FAKE_USERS_DB` ha un solo utente cablato, e per portare `disabled` a `True`
bisogna **editare il sorgente** — chi può farlo ha già vinto. La
«dimostrazione» prodotta creava l'utente sospeso da Python: uno scenario
artificiale, non un attacco.

**Il difetto reale era nel contratto OpenAPI.** Lo schema `User` pubblicato su
`/docs` espone `disabled`, e chi lo legge conclude ragionevolmente che esista
una sospensione degli account. Non esisteva. Dato che l'applicazione è
consumata **esclusivamente via OpenAPI**, lo schema è la superficie del
prodotto: la promessa non mantenuta viveva esattamente dove vive
l'applicazione.

**La soluzione, e la parte che conta.** `get_current_user()` ricontrolla a
**ogni richiesta**: i JWT non si revocano e durano 30 minuti, quindi senza
questo un account sospeso resterebbe operativo fino alla scadenza. È l'unico
meccanismo di revoca che l'API possiede.

### R15 — ✅ RISOLTO (2026-08-20): un solo URL malformato faceva cadere l'intero audit
**Il difetto.** `normalize_url()` solleva `ValueError` su porta non numerica,
porta fuori range e IPv6 malformato. Nessun chiamante la catturava, e
`build_context()` sta **fuori dal `try`** di `run_audit()`: un solo `href`
rotto in una pagina — o un solo `<loc>` in una sitemap — uccideva l'audit
intero. Riprodotto ai tre livelli prima di toccare il codice: crawler in
`ValueError` con le pagine già raccolte **perse**, CLI in traceback con
**exit 1**, API in 500.

L'exit 1 è il dettaglio peggiore: è fuori dal contratto documentato ed è
proprio il valore riservato alla futura soglia `--fail-under`. Una pipeline
leggerebbe il crash come «sito sotto soglia» — un guasto travestito da
giudizio.

**Una trappola trovata misurando, non leggendo.** Su un IPv6 malformato è
**`urljoin` stesso** a sollevare, prima ancora che `normalize_url` venga
chiamata: proteggere solo la seconda avrebbe lasciato aperta metà del difetto.

**La soluzione, e dove va la tolleranza.** `safe_normalize_url()` restituisce
`None`, con **l'urljoin dentro la guardia**. `normalize_url()` resta intatta e
continua a sollevare: è una funzione pura con un contratto chiaro, e il posto
giusto per la tolleranza è il confine dove entra il dato non fidato. Gli URL
vengono dal sito analizzato: sono **dato ostile, non un errore di
programmazione**. Lo scarto si dichiara in `skipped` — un `href` rotto è anche
un rilievo sul sito.

**Gli scarti sono deduplicati**, e non è estetica: lo stesso `href` rotto in un
template compare su *ogni* pagina e riempirebbe il referto della stessa riga.

**Quattro mutazioni; la seconda non veniva rilevata.** I test coprivano
`estrai_link` ma nessuno esercitava `crawl()`, cioè proprio il percorso del
`<loc>` di cui avevo riprodotto il crash: la suite sarebbe rimasta verde con
metà del difetto rimessa dentro. Colmarla ha richiesto il primo test che
esercita `Crawler` direttamente, con un `BaseAdapter` finto montato sulla
`session` — perché la fixture `niente_rete` copre `requests.get` e **non**
`Session.get`.

### R16 — ✅ RISOLTO (2026-08-20): mojibake silenzioso sui siti UTF-8 senza charset
**Il difetto.** `requests` applica a ogni `text/*` privo di `charset` il
default legacy di RFC 2616, cioè ISO-8859-1 — regola che HTML5 ha abbandonato
proprio perché sbaglia su ogni sito UTF-8. Su un sito UTF-8 servito senza
charset — configurazione comunissima — titolo, testo, chunk e HTML grezzo
entravano **corrotti nel corpus senza un solo errore**. Non è estetica: sono
gli ingressi di BM25, del proxy e dell'RRF.

```
prima : Top Chunk Ibrido : .../ § PerchÃ© Ã¨ giÃ  cosÃ¬ caro?
dopo  : Top Chunk Ibrido : .../ § Perché è già così caro?
```

**La soluzione.** `decode_html()` applica l'ordine dello standard — BOM,
charset dell'header, `<meta charset>` o rilevamento — con `UnicodeDammit`, che
BeautifulSoup porta già: nessuna dipendenza nuova. Si decodifica **una volta
sola** e si parsa quella stringa, così DOM e HTML grezzo non possono divergere.

**Il BOM va guardato a mano, scoperto misurando.** `UnicodeDammit` accetta
`known_definite_encodings` per l'header ma **non gli fa cedere il passo al
BOM**: con byte UTF-8 con BOM e header latin-1 sceglieva latin-1. È la pagina
scritta su Windows e servita da un server mai riconfigurato — tutt'altro che
teorico.

**Una scoperta contraria all'attesa.** `user_encodings=["utf-8"]` era stato
aggiunto **solo per velocità** (175 ms di rilevamento statistico su 80 KB
contro 0,06). Il confronto sistematico dei due percorsi ha mostrato anche una
**differenza di risultato, in meglio**: una pagina con `<meta charset>` stantio
— dice latin-1, i byte sono UTF-8, il residuo di una migrazione — smette di
produrre mojibake. Anticiparlo è lecito perché il tentativo UTF-8 è
**autoverificante**: i byte accentati di una pagina davvero latin-1 non sono
UTF-8 valido, quindi fallisce e gli altri candidati vengono provati.

**robots.txt subiva lo stesso** (viaggia come `text/plain`), e RFC 9309 impone
UTF-8: una direttiva `Sitemap:` con un IDN ne usciva storpiata. Le sitemap
erano già a posto, perché `_read_sitemap` usa `resp.content`.

**Cinque mutazioni; tre non venivano rilevate**, ed è il risultato più utile
della voce. La colpa non era dei test ma del banco: l'adattatore finto di R15
impostava `resp.encoding = "utf-8"`, quindi `resp.text` funzionava sempre e il
mojibake non poteva manifestarsi. **Un banco di prova troppo accomodante
conferma anche ciò che è sbagliato.** L'adattatore deriva ora l'encoding dagli
header con la stessa funzione di `HTTPAdapter.build_response`.

### R17 — ✅ RISOLTO (2026-08-20): i redirect non venivano rivalidati
**Il difetto.** `requests` seguiva i redirect da solo e nessuno guardava dove
si era finiti: `host_matches()` e `can_fetch()` giravano sull'URL
**richiesto**. Un redirect bastava al sito per decidere che cosa il crawler
scaricasse. Quattro effetti, tutti riprodotti: robots.txt aggirato, host
esterno indicizzato, stessa pagina due volte nel corpus, e **la richiesta
vietata partita davvero**.

Grave su due piani: una **promessa rotta** (README e CLAUDE.md dichiarano che
il crawler rispetta robots.txt, e l'unico bypass dovrebbe essere la
dichiarazione di proprietà) e la **contaminazione del corpus**, con il
contenuto di un altro host dentro BM25 e l'RRF senza che `skipped` ne dicesse
nulla.

**È il quarto effetto a decidere la forma della correzione.** Ricontrollare
`resp.url` a cose fatte avrebbe evitato di *indicizzare* la pagina, ma la
richiesta vietata sarebbe comunque partita: il crawler avrebbe disobbedito e
poi nascosto la prova. Quindi `_scarica_pagina()` segue i redirect **uno a
uno** con `allow_redirects=False` e controlla host e robots **prima** di ogni
salto. `_get()` continua a seguirli da sé per robots.txt e sitemap, che non
sono pagine da indicizzare — e per robots.txt **RFC 9309 chiede esplicitamente
di seguirli**.

**La pagina si registra sotto l'URL di ARRIVO**: è lì che il contenuto vive, ed
è quello che `mars_tech` confronta col `canonical`. Questo da solo chiude il
terzo effetto, perché la chiave del dizionario diventa la stessa.

**Una correzione nata da una misura.** Il controllo del duplicato stava a valle
di `_scarica_pagina`: contando le richieste è emerso che nell'ordine «prima
`/nuova`, poi `/vecchia`» la pagina veniva scaricata **due volte** — il
duplicato veniva dichiarato dopo aver già sprecato la richiesta.

**Diagnosi precise sui casi degeneri**, applicando la lezione di R6 (vuoto ≠
malformato): una `Location` vuota veniva risolta da `urljoin` nell'URL di
partenza e riportata come «più di 5 redirect» — difetto sbagliato, e cinque
richieste sprecate per scoprirlo. Ora sono cinque diagnosi distinte, ciascuna
con il proprio costo in richieste (1, 1, 2, 1, 6).

**Sette mutazioni; la quarta non veniva rilevata**: il test guardava solo le
chiavi di `pages`, che ormai deduplicano da sole. Il controllo esplicito compra
altro — **non richiedere la pagina due volte** — e finché il test non misurava
quello era vacuo.

**Il banco reso fedele una seconda volta.** L'adattatore non impostava
`resp.request`, e senza quello `requests` non sa risolvere i redirect: il
difetto non si manifestava affatto nei test. Dopo `resp.encoding` di R16, è il
secondo pezzo di `HTTPAdapter.build_response` che mancava.

### R18 — ✅ RISOLTO (2026-08-20): la punteggiatura escludeva le parole da BM25
**Il difetto.** `mars_lexical` tokenizzava con `.lower().split()`, quindi
`"funziona?"` era un token **diverso** da `"funziona"`.

**Un'affermazione del TO-DO era sbagliata.** Diceva che anche `mars_semantic`
tokenizza con `split()`: lì `split()` conta le parole per una soglia, mentre il
recupero passa da `VectorRetriever`, che lavora su **trigrammi di caratteri**,
per i quali le due forme condividono quasi tutto. Il difetto era confinato a
`mars_lexical`.

**Ed è l'asimmetria a fare il danno peggiore**: il recuperatore vettoriale
vedeva la corrispondenza, quello lessicale no, e i due si trovavano in
disaccordo per una ragione che **non riguarda il sito**. Misurato su tre chunk:

```
BM25       : [0.4700, 0.4869, 0.0]    -> primo il chunk 1
vettoriale : [0.4221, 0.0966, 0.0161] -> primo il chunk 0
```

Il chunk 0 è quello che contiene la frase cercata. Per BM25 finiva **sotto** un
chunk più corto che `"funziona"` non lo conteneva affatto: la normalizzazione
sulla lunghezza premiava il più breve.

**La soluzione, e perché `tokenize()` sta in `mars_core`.** Corpus e query
**devono** passare per la stessa funzione: se divergono, la query smette di
trovare ciò che l'indice contiene, e non c'è alcun errore — solo punteggi
sbagliati. Si guarda la **categoria Unicode** e non un elenco di caratteri,
perché un elenco ASCII dimentica `«» “” ‘’ — … ¿`; i simboli (categoria `S`)
restano, così `C++` non diventa `c`.

**Perché non spezzare su ogni non-parola.** `re.findall(r"\w+", …)`, misurata
su testo reale, manda in pezzi `info@esempio.it` (tre token), `3,14` (due) e
`COVID-19`, e riempie l'indice di frammenti — `l`, `dell`, `un` — che
**gonfiano la lunghezza dei documenti**, cioè la grandezza su cui BM25
normalizza. L'elisione italiana resta aperta come **I15**, con la misura fatta.

**Un limite noto, registrato invece che nascosto.** `tokenize("C#")` dà
`["c"]`, perché `#` è categoria `Po`. Nessuna eccezione a mano — la prima ne
chiama altre — perché il danno è di **precisione, non di recall**: corpus e
query passano per la stessa funzione, quindi `C#` continua a trovare `C#`.

**L'effetto misurato, e il suo limite dichiarato.** Il punteggio del chunk che
risponde sale sempre (+140%, +19%, +50% su tre query; l'11% dei token
dell'indice portava punteggiatura attaccata), ma **se il vincitore cambi
dipende dal corpus**: sui chunk reali del sito di prova il primo posto non
cambia, perché i concorrenti sono più lunghi e BM25 li penalizza già. La
correzione è certa, la sua visibilità nel referto no, e prometterla sarebbe
falsa precisione.

**Sette mutazioni; due non venivano rilevate.** Una era mal costruita da parte
mia — toccava un solo ciclo — e serve a ricordare che **anche le mutazioni
vanno verificate**. L'altra è più istruttiva: il test sul lato query **passava
vacuamente**, perché con la query non tokenizzata tutti i punteggi sono zero e
`sorted()` restituisce l'ordine naturale, che per caso metteva primo il chunk
atteso. È il difetto di R23 incontrato dal vivo; il test mette ora il bersaglio
in **seconda** posizione.

### Referto HTML nello stile di Lighthouse (2026-08-20)
Richiesta dell'autore. **Testo e JSON non sono stati toccati**, e la struttura
canonica di `build_report()` nemmeno: è il principio di C4 — il dato prima
della presentazione — che qui si paga da solo, perché cambiare l'aspetto ha
significato riscrivere **un solo renderer**.

I quadranti sono **SVG calcolato in Python**, con l'arco da `stroke-dasharray`
sulla circonferenza: nessuno script, nessuna libreria, il referto resta un file
solo apribile fra due anni da un archivio senza rete. È anche la prova che
l'SVG inline basta, che **I9** dava per assunto.

**Tre scelte di onestà, che sono la ragione per cui non basta copiare
Lighthouse.**

1. Un'area **non misurata** disegna un anello tratteggiato con un trattino, non
   un quadrante a zero.
2. **Zero non disegna alcun arco.** Con `stroke-linecap` arrotondato lo zero
   lasciava un **puntino colorato** che si legge come «poco» invece che come
   «niente». Trovato guardando lo screenshot, non leggendo il codice.
3. **Lessicale e Semantica non ricevono un voto finto**: producono classifiche,
   non punteggi, e al loro posto la fascia mostra i due segnali derivati.

**La scala cambia significato, e va detto**: MARS usava 80/50, Lighthouse usa
90/50. Il numero non cambia, la convenzione sì, ed è dichiarata nella legenda
proprio perché il colore non venga letto come una misura.

**Verificato guardando, non deducendo**: il referto è stato generato su un sito
reale, **fotografato con Playwright** in tema chiaro e scuro e ispezionato — è
così che sono emersi il puntino dello zero e i testi rimasti con gli apostrofi
ASCII. Fotografato anche il caso **degradato**, perché è lì che si vede se la
distinzione «non misurato» regge.

I test preesistenti su autoconsistenza, tema scuro ed escape del markup ostile
sono rimasti verdi senza modifiche: erano scritti sul comportamento e non
sull'aspetto, e hanno retto a un rifacimento completo della vista.

### R19 — ✅ RISOLTO (2026-08-20): i segnali di pagina gonfiavano `answer_shaped_ratio`
**Il difetto.** `question_signals()` riceveva l'intera **pagina** ed era
chiamata per **ogni chunk**. Due dei quattro segnali erano però proprietà della
pagina: «titolo interrogativo» si accendeva se una *qualunque* intestazione era
una domanda, «FAQPage JSON-LD» se il marcatore compariva *ovunque* nell'HTML.
Una sola FAQ marcava answer-shaped ogni chunk della pagina.

Non è un dettaglio interno: `answer_shaped_ratio` alimenta il segnale
*Contenuto in forma di risposta* di C1, che pesa 3 su 3 per ogni assistente.

**Misurato** su una pagina con quattro sezioni di cui **una sola** è una
domanda: `answer_shaped_ratio` 1.00 contro l'onesto 0.25, e un composito di
85,5 che scende a **70,0** una volta corretto. Quindici punti e mezzo di
gonfiaggio.

**La soluzione: i segnali si dividono per ambito.** `question_signals` guarda
solo il passaggio, e il titolo che considera è quello del **chunk**;
`page_signals` raccoglie ciò che riguarda la pagina e **non entra nel
rapporto**, che è una frazione di chunk — contarli lì significava moltiplicare
un fatto di pagina per il numero dei suoi pezzi. Restano nel referto, contati
in pagine, perché dicono qualcosa di vero.

**Una scelta di R9 conservata deliberatamente**: l'heading del chunk continua a
far parte del testo su cui si calcolano gli altri due segnali — «Come
funziona?» come titolo vale quanto la stessa frase nel corpo. Senza, un chunk
la cui unica domanda sta nel titolo perderebbe due segnali su tre.

**Un test di R9 codificava il difetto**, ed è stato riscritto: verificava che
l'heading di *un'altra* sezione accendesse il segnale, cioè esattamente R19
scritto come se fosse la funzione voluta. I segnali strutturali di R9 restano
giusti come **segnali**; era sbagliata la loro **attribuzione**.

**Una seconda causa di gonfiaggio, trovata misurando e NON corretta qui.** Con
R19 chiusa la pagina di prova dava 0,50 invece di 0,25: `Chi siamo` accende
«titolo interrogativo» pur non essendo una domanda, e vale per un'intera classe
di intestazioni standard. È **R34**, tenuta separata perché mescolarla avrebbe
reso illeggibile la batteria di mutazioni.

### R20 — ✅ RISOLTO (2026-08-20): axe fabbricava un 100/100, e la suite lanciava Chromium
Due difetti che si tenevano in piedi a vicenda: il prodotto produceva un
punteggio inventato, e il banco di prova era costruito in modo da non poterlo
vedere.

**Il prodotto.** `run_axe()` inghiottiva ogni fallimento per-URL **senza
contare le pagine analizzate**: con tutte le pagine irraggiungibili restituiva
una lista **vuota**, che `audit()` leggeva come «nessuna violazione». Un sito
mai caricato veniva pubblicato come **accessibile al 100%, misurato con
axe-core**, e `pages_tested` riportava gli URL *tentati*. È il difetto peggiore
della famiglia aperta da R4: non un'assenza dichiarata, ma una misura inventata
che si presenta come la migliore possibile.

**Il banco.** `conftest.py` e il README dichiaravano entrambi che nessun test
avvia un browser. **Erano affermazioni false**, misurate con `strace` sulla
sola porzione WCAG: **15 browser lanciati**. La fixture `niente_rete` copre
`requests`, ma **Playwright non passa da requests**. E poiché nei test le
navigazioni fallivano tutte, la suite esercitava proprio il 100/100 fabbricato,
passando verde. Nessun test fissava quale ramo girasse, quindi il risultato
dipendeva dalla macchina.

**La soluzione.** `run_axe()` conta le pagine riuscite e restituisce `None` se
sono zero; `pages_tested` riporta le esaminate, con `pages_attempted` e
`complete` accanto; la scansione parziale è dichiarata; la **diffusione** si
calcola sulle pagine viste. E `conftest.py` rende `playwright.sync_api` non
importabile: si agisce sulla **libreria** e non su `mars_wcag`, così la
neutralizzazione non dipende da quale oggetto-modulo sia vivo e copre entrambe
le porte d'ingresso.

Dopo: **0 browser** dalla suite intera, durata da 8,1 a 6,4 s. Le due
dichiarazioni di `conftest.py` e del README sono tornate vere senza riscriverle.

**Il percorso axe reale non è stato rotto**, ed è la verifica che contava di
più: su un sito locale costruito inaccessibile, `tool=axe-core`, `score=0`,
`color-contrast` fra i rilievi — un criterio che solo un browser vero può
vedere.

**Sei mutazioni; le prime due — il cuore di R20 — non venivano rilevate.** I
test iniettavano `run_axe` dall'esterno, quindi provavano `audit()` ma
lasciavano il **corpo** di `run_axe` mai eseguito: il conteggio delle pagine,
che *è* il difetto, non era sotto test. Colmato con un **finto Playwright** che
fa fallire davvero la navigazione sugli URL indicati.

### R21 — ✅ RISOLTO (2026-08-20): «di superficie» era indistinguibile da una misura piena
**Il difetto.** Le viste umane mostravano `tool` — e mai `status` — **solo**
dove esisteva un `wcag_level`, cioè per la sola accessibilità. Il dato canonico
lo conteneva già: il JSON era onesto, e le due viste che le persone leggono no.

```
vista TESTO
  solo header HTTP      -> 7. Sicurezza : 100/100
  scansione ZAP attiva  -> 7. Sicurezza : 100/100
```

Stringhe **identiche**. Chi non sa che *HTTP-Headers* significa «abbiamo
guardato tre intestazioni» leggeva un sito perfettamente sicuro. È il difetto
più grave della famiglia aperta da R4, perché non riguarda un modulo ma il
punto in cui tutto il lavoro di onestà arriva al lettore: `mars_wapt`
distingueva già `surface`, `mars_wcag` pure, C9 aveva introdotto `complete:
False` — e le viste buttavano via tutto.

**La soluzione.** `_qualificatori(area)` produce per **ogni** area con un
punteggio con che cosa è stato ottenuto: strumento, livello, profondità,
completezza, campione. È **condivisa fra le due viste**, così testo e HTML non
possono tornare a dire cose diverse — che è esattamente com'era nato il
difetto. Nel referto HTML la qualifica è anche visiva, in arancio.

**Un'imprecisione trovata rileggendo l'output.** La qualifica era stata
aggiunta anche all'`aria-label` del quadrante, ma su una scansione soltanto
*interrotta* diceva «controllo di superficie», che è un'altra cosa. Tolta: la
nota è un fratello nel DOM e viene letta subito dopo, quindi ripeterla la
duplicava e sbagliarla era peggio che ometterla.

Due affermazioni del README sono tornate vere senza riscriverle. **Con R21 si
chiude l'ultima voce GRAVE** della revisione del 2026-08-20.

### R22 — ✅ RISOLTO (2026-08-20): l'esecutore di moduli non reggeva i plugin che rompono
Tre difetti della stessa famiglia: il contratto `audit(context) -> dict` era
scritto ma non difeso.

1. **Un modulo che solleva spariva dal referto CLI.** L'eccezione veniva solo
   stampata, l'area non entrava in `results`, e `build_report` non la nominava
   affatto — exit code **0**. Con `--output` il file consegnato non portava
   traccia dell'area persa. L'API faceva già la cosa giusta: le due interfacce
   si comportavano diversamente davanti allo stesso guasto.
2. **Un plugin che non restituisce un `dict` faceva crollare il referto.**
   `res.get("score")` su `None` — il `return` dimenticato, l'errore più comune
   scrivendo un plugin — sollevava `AttributeError` **dopo che tutti i moduli
   erano girati**: audit intero perso, e 500 sugli endpoint singoli.
3. **`mars_seo` non reggeva uno score SEO `null`**, che lo schema LHR ammette.

**La soluzione.** `normalizza_risultato()` ed `errore_modulo()` vivono in
`mars_core`, perché CLI e API caricano gli stessi plugin e la difesa del
contratto appartiene lì. Un risultato non conforme diventa `status: "error"`
con **il motivo fra i rilievi**: «non misurato» senza il perché è
un'informazione dimezzata.

Per `mars_seo` la diagnosi è **specifica** (lezione di R6): non «Lighthouse non
riuscito» — che sarebbe falso, Lighthouse ha funzionato — ma «non ha calcolato
la categoria SEO per questa pagina».

**Sette mutazioni; la terza e la sesta non venivano rilevate**, ed è sempre lo
stesso punto cieco in forma nuova: avevo testato `build_report`, cioè il
*consumatore*, ma nessun test esercitava i due **punti d'integrazione** —
`run_audit()` della CLI e `run_single_audit()` dell'API.

**Un fallimento di test utile.** L'asserzione sul referto HTML cercava
`il plugin e' rotto` e falliva: in HTML l'apostrofo esce come `&#x27;`, cioè
l'escape funziona. Era il test a essere ingenuo, non il codice.

### La sezione SEO riporta i controlli di Lighthouse (2026-08-20)
Richiesta dell'autore, con un referto PageSpeed reale come riferimento.

**La fonte è stata verificata, non ricostruita a memoria.** La pagina di
PageSpeed è un'applicazione JavaScript e restituisce solo il guscio a chi la
scarica; al suo posto è stato eseguito **Lighthouse in locale sullo stesso
URL**, che è la fonte migliore perché è lo stesso strumento e la stessa
versione che `mars_seo` invoca. Da lì la struttura esatta: **11 audit**, dieci
binari e uno manuale. La forma di un audit *fallito* — che quella pagina non
offriva, perché li supera tutti — è stata ottenuta eseguendo Lighthouse contro
una pagina locale costruita carente, così i test usano forme **osservate** e
non immaginate.

**I superati si elencano, e non è ridondanza**: senza, non si sa *che cosa* sia
stato guardato, e un punteggio pieno resta indistinguibile da un controllo mai
eseguito. È R21 applicato al dettaglio invece che all'area.

**I titoli li traduce Lighthouse** (`--locale=it`), così restano allineati allo
strumento invece di essere una nostra traduzione destinata a invecchiare. E il
**tipo di dispositivo è dichiarato**, perché mobile e desktop non sono
confrontabili.

**Un difetto invisibile nel codice, trovato nello screenshot**: la classe CSS
`ok` dei controlli superati **collideva con la classe globale `.ok`**, che
colora l'intera riga — tutte le voci superate risultavano verdi invece del solo
segno di spunta. Rinominate in `superato` / `fallito`.

**Una guardia dichiarata come tale.** `passed` esclude gli audit manuali;
misurato su tre referti reali, manuali e non applicabili hanno **sempre**
`score: None`, quindi oggi la clausola non cambia nulla. Resta perché superato,
fallito e manuale devono partizionare l'elenco, e il commento dice che è una
difesa, non una differenza.

**Sette mutazioni; tre non venivano rilevate, per due ragioni diverse.** Due
erano **mal costruite da me** — una era un no-op (`[] or [...]` vale `[...]`),
l'altra non discriminava perché i manuali hanno score `None`. La terza ha
scoperto un test **vacuo**: i falliti stavano già per primi nel dato di prova,
quindi l'ordinamento non veniva esercitato.

### R23 — ✅ RISOLTO (2026-08-20): query perse, e ranghi a informazione zero
**1. Un rango a informazione zero veniva presentato come la classifica
migliore possibile.** Quando nessun termine della query trova riscontro i
punteggi sono tutti zero e `sorted()` restituisce l'**ordine naturale**, cioè
quello di scansione: i due recuperatori davano quindi lo stesso ordine, che
coincide con se stesso.

```
rango lessicale [0, 1, 2]   rango vettoriale [0, 1, 2]
CONSENSO riportato: 3/3     <- su una domanda senza un solo riscontro
```

E si propagava: il segnale *Recuperabilità ibrida* di C1 leggeva **100.0**.

**2. Le query non sopravvivevano alla caduta di un retriever**: vivevano solo
dentro `rrf_simulation`, e `mars_citations --from-audit` usciva con «Nessuna
query nel referto».

**La soluzione.** I due retriever dichiarano `matched` per ogni query, e senza
riscontro non nominano alcun `top_chunk`. Le classifiche a vuoto sono
**escluse dalla fusione aggregata**, perché fondere un ordine di scansione con
una classifica vera sposta il risultato senza dire nulla sul sito. Nel referto
il consenso di una query senza riscontro **non è zero: è non misurabile** —
«nessun riscontro» e «0/3» dicono cose diverse, e confonderle nascondeva
proprio il caso peggiore.

Misurato: tre consensi fabbricati su quattro spariti, e l'indice composito
**non cambia** (62,1), perché il rango aggregato conserva la query che ha
funzionato. La correzione toglie le invenzioni senza impoverire ciò che era
misurato.

**Un'ipotesi mia, smentita dalla misura.** Vedendo tre query su quattro
dichiarare «nessun riscontro» avevo supposto la colpa del recuperatore
**vettoriale**. È il **lessicale** a non trovare nulla, mentre il vettoriale
matcha tutto: `matched` significa cose diverse per i due — per BM25 «un termine
della query compare nel corpus», un segnale forte; per il proxy char-TFIDF
«qualche trigramma si sovrappone», che fra due testi nella stessa lingua è
quasi sempre vero. La guardia coglie quindi il caso patologico ma sul lato
vettoriale scatterà di rado, e va detto invece di lasciar credere il contrario.

**Un difetto nuovo, trovato indagando quell'ipotesi**: `mars_lexical` indicizza
heading + testo, `mars_semantic` il solo testo. R10 aveva lavorato perché i
ranghi si riferissero alle stesse **unità**; nessuno aveva controllato che
leggessero lo stesso **contenuto**. È **R35**.

C'è anche un test che fissa la **lettura compatibile**: una voce `per_query`
senza `matched` viene considerata misurata, così un modulo esterno scritto
prima continua a funzionare.

### R24 — ✅ RISOLTO (2026-08-20): tre casi limite del crawler sugli URL
**1. Gli host IPv6 letterali venivano corrotti, e il filtro same-host con
loro.** `norm_host()` tagliava sul primo `:`, che in un IPv6 non è il
separatore della porta ma parte dell'indirizzo; `normalize_url()` usava
`parts.hostname`, che toglie le parentesi quadre:

```
normalize_url("http://[2001:db8::1]/x") = 'http://2001:db8::1/x'   <- non e' un URL
norm_host    ("http://[2001:db8::1]/x") = '[2001'
host_matches fra due IPv6 DIVERSI       = True                     <- !
```

L'ultima riga è la più seria: due indirizzi diversi si riducevano alla stessa
stringa, quindi il filtro same-host lasciava passare un altro server. E un sito
servito su IPv6 falliva ogni richiesta, diagnosticato *irraggiungibile* pur
rispondendo.

**2. Le sitemap con `<loc>` relativi producevano zero pagine, col motivo
sbagliato.** Lo standard li vuole assoluti, ma le sitemap reali ne hanno di
relativi, e `host_matches` li bocciava come «host esterno» — che è falso, è
esattamente lo stesso host.

**3. Un robots.txt vuoto veniva riportato come assente**, perché `found` si
deduceva dal contenuto e non dallo status. Un file servito a 200 ma vuoto
significa *«tutto permesso»*, ed è una scelta esplicita del sito: `mars_tech`
ne faceva un rilievo di gravità media per un difetto che non c'era.

**Verificato con una prova end-to-end** su un server in ascolto su `[::1]:8861`:
prima «NESSUNA PAGINA: il sito risulta irraggiungibile», dopo la pagina
indicizzata. Su un sito senza questi casi limite il referto è **invariato**,
area per area.

### R25 — ✅ RISOLTO (2026-08-20): la direttiva robots `none` non veniva vista
**Il difetto.** Si cercava la sottostringa `noindex`. La direttiva standard
`none` — che per Google e Bing significa **esattamente** `noindex, nofollow` —
non la contiene. Riprodotto su un sito di una pagina, tutto uguale tranne la
direttiva:

```
meta robots: noindex               57  [critico] 1/1 pagine con 'noindex'
meta robots: none                  97  NESSUNO
meta robots: noindex,nofollow      57  [critico] 1/1 pagine con 'noindex'
meta robots: (nessuno)             97  NESSUNO
```

Non è che il rilievo fosse più mite: **non c'era**. `none` e «nessuna
direttiva» ricevevano lo stesso identico giudizio, mentre `none` e
`noindex, nofollow` — la stessa direttiva in due scritture — ne ricevevano due
distanti 40 punti.

**La soluzione, e perché non è «aggiungere una parola».** Il difetto non era
l'assenza di `none` dalla stringa cercata: era **cercare sottostringhe**. Le
direttive sono una lista separata da virgole e ora vengono lette come tale, con
il giudizio ridotto a un'intersezione fra insiemi dichiarati. Il guadagno è che
l'elenco delle direttive riconosciute è **esplicito ed elencabile**: aggiungerne
una è una domanda sull'insieme, non una scommessa su una sottostringa.

**`all` non compare in nessuno dei due insiemi, di proposito**, ed è annotato
perché nessuno lo «corregga»: è il default esplicito, non un rilievo. Quando le
direttive si contraddicono (`all, noindex`) vince la più restrittiva — che è
precisamente ciò che fa un'intersezione.

**`nofollow` riceve un rilievo proprio, graduato**: su una pagina sola è una
scelta legittima (`lieve`), quando è la regola del sito la scoperta dipende
interamente dalla sitemap (`medio`).

**Dieci mutazioni, e due lezioni che valgono oltre questa voce.**

- **Il `.lower()` non era coperto da nulla**, e me ne sono accorto
  *progettando* la mutazione, non eseguendola: tutti i dati di prova erano già
  minuscoli. `direttive_robots` riceve un dict che attraversa il confine dei
  plugin e non può contare sul crawler, e le direttive robots sono insensibili
  al maiuscolo per specifica.
- **La batteria ha dichiarato dieci mutazioni su dieci «non rilevate», con la
  suite rossa.** Cercava la parola `failed` nell'output di pytest, ma
  `setup.cfg` ha già `addopts = -q`: il `-q` sulla riga di comando faceva
  `-qq`, che **sopprime la riga di riepilogo finale**. Il verdetto viene ora dal
  codice di uscita. Un banco che non sa distinguere verde da rosso avrebbe
  promosso qualunque cosa.

**Due rilievi nuovi dalla misura, aperti come R36 e R37**: `nosnippet` e
`max-snippet:0` non producono nulla, e sono le direttive che governano
l'**estrazione del testo**, cioè il meccanismo con cui un assistente cita una
pagina — per questo progetto più rilevanti di `noindex`.

### R26 — ✅ RISOLTO (2026-08-20): tre difetti di `mars_wcag`
**1. `alt=""` contato come violazione 1.1.1.** Il filtro `not i.get("alt")` è
falso tanto per l'attributo assente quanto per quello presente e vuoto. Ma
`alt=""` su un'immagine decorativa è la tecnica **H67**: la marcatura
*corretta*, quella che dice allo screen reader di saltarla. Contarla come
difetto penalizzava proprio chi aveva fatto la cosa giusta. Il crawler la
distinzione la conserva già: era il filtro a buttarla via.

**2. `context.get("delay")` era sempre `None`.** `audit()` leggeva una chiave
che `build_context` non ha mai inserito: il ramo `if delay:` di `run_axe` era
codice morto e Chromium apriva le pagine di fila. E il valore giusto non è
nemmeno quello chiesto dalla CLI, perché **robots.txt può alzarlo**: misurato,
1,0 s chiesto contro 7,0 s effettivi dopo un `Crawl-delay: 7`. Il crawler
rispettava i sette secondi e poi il browser visitava cinque pagine senza pausa
alcuna, sullo stesso sito.

**3. Il riparsing dell'HTML**, contro il principio dichiarato e contro R11, che
annunciava «un parse invece di tre» — vera quando fu scritta, resa falsa da C8.
La scelta era fra estrarre i dati nel crawler e correggere le due
dichiarazioni. Estrarli, per una ragione che pesa più della velocità:
`controlli_statici` dipendeva da `pagina["html"]`, quindi il giorno in cui il
crawler smettesse di conservarlo — un'ottimizzazione plausibile — i controlli
tornerebbero **vuoti senza un errore**.

`estrai_struttura(soup)` estrae **dati, non giudizi**: il `role="presentation"`
di una tabella arriva grezzo. Sono già risolte solo le due cose che richiedono
il documento intero e a valle non sarebbero più ricostruibili: la
`<label for>` che punta a un campo e la `<label>` che lo avvolge.

**Verificato per confronto, non per asserzione.** La versione precedente,
estratta da `git show`, eseguita accanto alla nuova sullo stesso markup: **una
sola differenza**, quella voluta (`2/4` → `1/4` immagini senza alt). Gli altri
sei rilievi identici parola per parola.

**Una previsione smentita dalla misura.** Davo per scontato che spostare
l'estrazione nel crawler facesse risparmiare il parse:

```
parse completo (cio' che mars_wcag faceva)  :  5,7 ms/pagina
estrai_struttura sul DOM gia' aperto        : 18,6 ms/pagina   <- PEGGIO
```

Il costo non era il parse: era `soup.find("label", for=...)` **dentro il ciclo
sui campi**, cioè O(campi × documento) — un difetto che il codice vecchio aveva
già e che avrei trasportato di peso. Raccogliendo gli `for` una volta sola si
scende a 2,7 ms, cioè **+3 ms netti a pagina**, non gli «885×» che il solo
`controlli_statici` mostrerebbe: quel confronto tace che il crawler ora fa il
lavoro al posto suo. Il guadagno vero della voce non è la velocità — è che il
modulo non dipende più dall'HTML grezzo.

**Sedici mutazioni; una non veniva rilevata**: nessun test aveva un
`<input type="submit">` senza etichetta, quindi togliere i tipi non
interattivi dalle esclusioni non faceva fallire nulla. Punto cieco
preesistente, ora coperto.

**Due finti resi fedeli**: il `Crawler` di `tests/test_api.py` accettava
`delay` e lo scartava, e la pagina Playwright finta ignorava
`wait_for_timeout`. Un finto che scarta ciò che il vero conserva non può
accorgersi di nulla.

### R34 — ✅ RISOLTO (2026-08-21): i titoli di sezione non sono domande
**Il difetto.** Il segnale «titolo interrogativo» si accendeva quando
l'intestazione **apriva** con un termine interrogativo, il che colpisce
un'intera classe di intestazioni standard: `Chi siamo`, `Dove siamo`, `Come
funziona`, `How it works`. Sono nomi, non domande.

**Misurato su contenuto reale**, non su un corpus costruito — 209 intestazioni
distinte di un sito vero: la regola di allora ne accendeva **31 su 209**, la
proposta **5**. I 26 di differenza, verificati uno per uno, **non contengono
una sola domanda**: sono titoli di articolo.

**Una classe che il TO-DO non aveva previsto: i due punti.** `_INIZIO_FRASE`
tratta `:` come confine di frase, quindi il segnale si accendeva **a metà
titolo** su una forma editoriale comunissima — *«AI Act: cosa scatta davvero
il 2 agosto»*.

**La correzione proposta dal TO-DO non avrebbe corretto nulla**, ed è la
ragione per cui è stata provata prima di adottarla: R34 suggeriva di applicare
la regola del `?` «solo al segnale titolo interrogativo, non a quello sul corpo
del testo», e i tre casi tipici restavano **invariati**. Il motivo sta in due
righe distanti fra loro: `answer_shaped` conta un chunk se *un qualunque*
segnale è acceso, e `intero` univa heading e testo prima di cercarvi
l'interrogativo — l'heading aveva **due possibilità** di accendere, e
restringerne una lasciava l'altra intatta. Senza la misura preventiva sarebbe
stata scritta una correzione verde e inefficace.

**La soluzione: una regola sola, applicata una volta.** *Un titolo è una
domanda quando è punteggiato come tale*, ed entra nel passaggio **solo se lo
è**. Questo concilia due voci che sembravano in conflitto: R9 aveva deciso che
l'heading fa parte del passaggio, R34 vuole che «Chi siamo» non accenda nulla,
e il discrimine fra i due casi è esattamente il `?`. Il test di R9 è rimasto
verde senza modifiche.

**Verificato sul dato che il referto pubblica**, sugli stessi 453 chunk reali:

| | prima | dopo |
|---|---|---|
| `answer_shaped_ratio` | 0,243 | **0,201** |
| segnale `titolo interrogativo` | **49** | **6** |
| `punto interrogativo` | 38 | 38 |

Il segnale sul titolo era falso **43 volte su 49**. `punto interrogativo` non
si muove di uno: era già corretto, e la correzione non lo ha toccato.

**Il costo, dichiarato e non misurato.** Le FAQ scritte senza `?` nel titolo
non sono più riconosciute *dal titolo*; restano riconoscibili dal corpo.
**Questo costo non è stato misurato su contenuto reale**: il sito usato per la
verifica non ha una pagina FAQ (267 URL in sitemap, nessuno).

**Otto mutazioni, e la seconda è la correzione letterale di R34**, messa in
batteria apposta: un test scritto sul solo segnale «titolo interrogativo»
l'avrebbe promossa. Le asserzioni sono infatti sull'**elenco intero** dei
segnali e sul rapporto finale.

### R27 — ✅ RISOLTO (2026-08-21): il timeout ZAP adesso ferma la scansione
**Il difetto.** Allo scadere del timeout `_attendi()` usciva dal ciclo e
`run_zap` proseguiva; `ZapClient` non esponeva nemmeno gli endpoint di stop.
**MARS smetteva di aspettare, il daemon no** — mentre il referto dichiarava
«Scansione ZAP interrotta dal timeout».

**Il secondo caso è peggiore di come la voce lo descriveva.** Il budget è unico
per spider e active scan: se lo spider lo esaurisce, `run_zap` lanciava
comunque `ascan/action/scan` — payload d'attacco: XSS, SQL injection, path
traversal — e poi **non attendeva neanche un controllo di avanzamento**, né lo
fermava. Un attacco avviato e abbandonato.

**Verificato sul daemon vero prima di scrivere il codice**, perché il progetto
si era già scottato dando per buono il client ufficiale (C9). Su ZAP 2.17.0
`spider/action/stop?scanId=999` risponde **HTTP 400 `does_not_exist`**, e non è
un dettaglio: `_get()` chiama `raise_for_status()`, quindi fermare una
scansione **conclusasi da sola** solleverebbe — e fra l'ultimo controllo di
avanzamento e la fermata può passare abbastanza perché finisca proprio lì.

**La soluzione.** `_ferma()` chiama gli stop senza mai sollevare e
**restituisce se il daemon ha accettato**: `does_not_exist` vale come fermata
riuscita, ogni altro errore no. Il referto distingue i due casi — «interrotta e
fermata» contro «scaduta e NON fermata: prosegue nel daemon ZAP». Il secondo
messaggio è il caso che prima era **l'unico**, dichiarato come se fosse il
primo. E non si avvia più un attacco che non si potrebbe sorvegliare.

**La prova end-to-end viene dal daemon, non dal codice**: bersaglio locale
deliberatamente lento e timeout di 3 s. Mai un sito reale — l'active scan è un
attacco.

| | `run_zap` restituisce | ZAP, 4 secondi dopo |
|---|---|---|
| **prima** | `completa=False` | scansione **`RUNNING` al 35%** |
| **dopo** | `completa=False, fermate=True` | scansione **`FINISHED`** |

**Nove mutazioni; una non era rilevata**: `_ferma` che dichiara riuscita *ogni*
`HTTPError`. I test coprivano `does_not_exist` e il daemon irraggiungibile, ma
non un errore HTTP diverso — il caso in cui non sappiamo se la scansione si sia
fermata, e il dubbio va dichiarato invece di risolverlo a nostro favore.

Il daemon finto **registra gli ordini ricevuti** invece di accettarli in
silenzio: è il punto, perché R27 non riguarda cosa `run_zap` restituisce ma
che cosa MARS dice al daemon.

### R38 — ✅ RISOLTO (2026-08-21): il referto copre tutti e nove gli ambiti
**Il difetto apparente**: il referto dichiarava «Analizzato» per Lessicale e
Semantica, che non producono né punteggio né rilievi.

**Il difetto vero sta nel meccanismo**: `render_text` decideva **sul nome del
modulo** e non sul dato, con un `continue` che scavalcava sia la riga di stato
sia i rilievi. Quindi se uno di quei due plugin **rompeva**, il referto lo
dichiarava analizzato e ne ingoiava il motivo:

```
1. Tecnica    : errore del modulo
  ⚠ RuntimeError: il plugin tecnico e' rotto      <- R22 funziona
3. Lessicale  : Analizzato (Top: N/A)             <- l'errore SPARISCE
```

È **R22 riaperta per due aree su nove**. Il caso speciale era nato prima della
macchina dell'onestà e non era mai stato ricondotto a essa.

**Un terzo stato non dichiarato.** `score: None` **senza** `status` non è nel
vocabolario di `STATO_LEGGIBILE`, e le viste lo collassavano su «non
misurato». Due casi veri oltre alle aree di classifica: `mars_citability`
quando nessun segnale è misurabile, e `mars_llm_judge` quando il modello
risponde ma omette il punteggio — che è una risposta, non una misura.

**La soluzione: il fatto entra nel dato e il caso speciale sparisce.** I due
moduli dichiarano `status: "ranking"`; le viste perdono **tutti** i
`if area["module"] == …`. Da nove punti cablati sul nome a uno stato nel dato.

**Un guadagno fuori ambito**: il referto non diceva **quale recuperatore avesse
girato**, benché cambi il senso di ogni rango — il modello multilingue e il
proxy char-TFIDF non misurano la stessa cosa.

**Perché questa forma non andrà rifatta dopo U13.** `_qualificatori` ha già la
regola: *lo stato si annota solo se convive con un punteggio*. Quando U13 darà
un voto alle due aree, `ranking` migrerà da solo dal posto del verdetto a
quello dei qualificatori, come fa `surface`.

**Undici mutazioni; cinque non erano rilevate alla prima esecuzione**, ed è la
misura di quanto la suite non proteggesse — nessun test guardava che la fascia
dei quadranti contenesse tutte le aree. Ora l'elenco atteso **viene dal referto
stesso**, così non invecchia.

Due errori miei, registrati perché ricorrenti: una mutazione con un pattern non
univoco, e **un test vacuo** — l'asserzione stava dentro un `if` che la
eseguiva solo quando era già vera.

### U1 — ✅ FASE CHIUSA (2026-08-24): il modello dati dei rilievi
*(9 sotto-voci. Il piano sta in [UPGRADE.md](UPGRADE.md).)*

Fino a qui un rilievo era una stringa con la gravità in un prefisso, e i
prefissi erano **tre**, diversi per modulo: `[critico]`, `[axe:serious]`,
`[ZAP:High]`. Tre scale mai messe in relazione, nessun peso, nessuna chiave
stabile — e su stringhe così non si costruiscono un piano di interventi
ordinato, un confronto fra due esecuzioni o una traduzione, cioè le fasi da U4
a U9.

**Le decisioni, area per area.**

**U1.1, il modello.** La scala editoriale si chiama `"mars"` e non
`"mars_tech"`, perché la usano più moduli. **Scala ignota e valore ignoto non
sono la stessa cosa**, e il piano li trattava insieme: un *valore* ignoto è
dato esterno — uno strumento che aggiorna la propria scala non deve far cadere
un audit, quindi degrada a `(info, 1.0)`; una *scala* ignota è un refuso di
programmazione, e degradarla appiattirebbe un intero modulo su un livello con
i punteggi intatti e i test verdi, cioè **invisibilmente**: solleva
`ValueError`.

La **soglia di Lighthouse non è arbitraria, ed è misurata**: nel
`default-config.js` di Lighthouse 13.4.1 ogni audit SEO pesa 1 tranne
`is-crawlable`, che pesa 93/23 ≈ 4,04 — calibrato, dice il loro commento,
perché quel solo fallimento faccia fallire l'intera categoria. Una soglia a 3
separa esattamente ciò che Lighthouse considera rompi-categoria.

**`weight` non è la penalità**, e UPGRADE.md proponeva di calcolare il recupero
dall'uno *o* dall'altra. Sono cose diverse — 2.0/1.0 è importanza relativa,
40/20/8/3 è punteggio — e per axe e ZAP la penalità dipende dalla diffusione,
quindi è calcolabile **solo dentro il ciclo che la applica**: non registrarla
subito l'avrebbe resa irricostruibile alla Fase 4.

**U1.2: l'ordine dei passi del piano è stato invertito di proposito.**
`build_report` copia una **lista chiusa** di chiavi, quindi finché non conosce
`findings` un modulo può produrli perfetti e il referto li butta via, con i
test di modulo tutti verdi. Adeguare i sei moduli prima del referto avrebbe
consegnato cinque commit di lavoro invisibile.

Qui è emerso che **due moduli su nove erano fuori dal contratto**: la lista
`MODULI` dei test era scritta a mano e non conteneva `mars_seo` né
`mars_wapt`, mai verificati contro `audit(context) -> dict`. Ora si deriva da
`MODULES_REGISTRY` — ma la derivazione **da sola non basta**, perché una suite
non può accorgersi di *quanti* casi ha girato: troncare la lista non faceva
fallire nulla finché l'invariante non è stato asserito.

**U1.3, `mars_tech`**, scelto apposta come banco di prova perché ha il
punteggio **accoppiato** alla scala. Il punteggio continua a derivare dalla
scala grezza: le quattro severità canoniche collassano `grave` e `medio`
entrambe in `warning`, distinte solo da 2.0 contro 1.0 (2:1), mentre `PESI` le
tiene a 20:8 (2.5:1) — ricalcolare da lì avrebbe cambiato i punteggi **in
silenzio**, e con essi l'indice composito.

**Una differenza involontaria, colta e tolta**: con le penalità in `float` lo
score usciva `94.0` dove usciva `94`. La vista non sarebbe cambiata (stampa
`%.0f`) ma il JSON sì — un cambio di contratto silenzioso e **invisibile ai
test**, perché `94 == 94.0`.

**U1.4, `mars_schema`**, la prima area **senza una scala propria**: la gravità
è quindi una scelta editoriale, e va dichiarata invece di lasciarla dedurre
dai numeri. `source_severity` resta **vuoto**, all'opposto di `mars_tech`: là
`[critico]` è la parola che l'utente legge, qui le issues non portano alcun
prefisso, e dichiararne uno attribuirebbe al modulo una scala che non pubblica.

JSON-LD assente resta `warning` **benché costi metà del punteggio**: in MARS
`critical` significa che il sito è **invisibile** agli assistenti, e senza
JSON-LD un sito è meno leggibile, non invisibile.

**Primo caso di aggregazione per chiave**, e non è estetica: in quest'area
`score -= 5` sta accanto a ogni `append`, quindi la cardinalità della lista
**è** il punteggio, e spezzare un controllo in N rilievi farebbe crollare i
punteggi di chiunque li conti.

**U1.5, `mars_wcag`**, il primo modulo con **due sorgenti di gravità**. Il
criterio WCAG non è una gravità: `[1.3.1]` è il *riferimento* che rende il
rilievo verificabile, e va nei params. **La penalità di un controllo statico
dipende dal ramo**: nel ripiego valgono 12 ciascuno, nel ramo axe il punteggio
viene dalle violazioni e la loro penalità è **zero** — attribuirgliene 12
prometterebbe alla Fase 4 un miglioramento che non arriverebbe.

**`impact` assente non diventa un giudizio di axe**: MARS lo appiattisce a
`minor` per poter pesare la violazione, ma è una *nostra* assunzione, e
`source_severity` resta vuoto.

**U1.6, `mars_wapt`**, il modulo con la superficie più larga: tre rami
d'uscita, due origini di gravità e **nessuna rete di test** su ciò che
l'adeguamento tocca — `audit_headers()` non aveva un solo test proprio, e
`audit()` non aveva **mai visto un alert non vuoto**. I test propri dell'area
passano da 15 a 61.

La gravità dei tre header è nostra ma **ancorata**: ZAP classifica gli stessi
tre fatti Medium e Low, mai High. Fra `grave` e `medio` decide la monotonia con
le penalità già tarate — è la decisione **D2**. Conseguenza scritta nel codice
perché non la si scopra dopo: un `grave` dedotto da un solo HEAD pesa **più**
di un Medium di ZAP, ed è innocuo soltanto perché i due rami si escludono.

**La `solution` di ZAP entra in `fix` e non si ripulisce.** Verificato sul
sorgente e sul daemon: `core/view/alerts` restituisce **testo semplice**; i
`<p>` dei referti tradizionali li aggiunge il generatore. Cercati tag HTML in
tutti i `.soln`/`.desc`/`.refs` di 79 add-on: **zero**. Uno strip sarebbe il
rimedio a un problema che lo strumento non ha, e mangerebbe in silenzio i
`<meta http-equiv=…>` di cui un testo di sicurezza è pieno.

**Interrotta e abbandonata restano due chiavi distinte** — sono due fatti
diversi, ed è esattamente ciò che R27 esiste per non confondere.

**U1.7, `mars_seo`**, l'unica voce che chiede di arricchire il dato a monte, e
la prima penalità del progetto che **non è una stima**.

**Il peso va letto dal referto, mai dalla configurazione**, ed è il fatto su
cui poggia tutto il resto: `core/scoring.js` **azzera** il peso degli audit non
applicabili, informativi e manuali prima di scriverlo nel LHR, quindi un
`is-crawlable` non applicabile pesa **0** nel referto e **4,04** nel
`default-config.js`. Una tabella cablata lo farebbe uscire `critical`.

**Il peso di `error` invece non viene azzerato**, e la costante di U1.1 non lo
contemplava: un audit che lo strumento **non è riuscito a eseguire** usciva
`critical`, presentato come difetto grave del sito — cioè R21.

La formula di Lighthouse è una media pesata, quindi **lineare**: il contributo
di ogni audit è esatto, additivo e invertibile, e la somma ricostruisce
`100 − score` a meno dell'arrotondamento a due decimali. Misurato sul referto
reale: **63,78 contro 64,00**, e `is-crawlable` fallito vale **36,6 punti**
contro i 9,1 di ciascun altro — il 31% che il commento di Lighthouse dichiara
di aver calibrato, ritrovato per calcolo.

**Il titolo di un controllo non misurato era una frase falsa**: Lighthouse usa
`failureTitle` solo quando `score < 0.9`, quindi un `notApplicable` porta il
titolo del **successo** — «da verificare a mano: Il documento ha un elemento
`rel=canonical` valido» sbaglia due volte. I `Finding` prefissano ora la
condizione; le `issues` restano com'erano, ed è **l'unico punto della fase in
cui il dato nuovo si discosta dalla vista compatta**, perché quella riga è nota
per falsa.

**La fixture di test è stata rifatta fedele**, ed era la condizione per poter
provare qualunque cosa: aveva sei audit e **nessun peso**, quindi ogni rilievo
sarebbe uscito `info` e un test sulla gravità sarebbe passato per il motivo
sbagliato.

**U1.8, `mars_citability`**, l'area che **rilegge** invece di misurare. Il
rischio non era perdere informazione — era **produrne di finta**, cioè un
secondo elenco di difetti che sembra indipendente dal primo e che a valle
verrebbe sommato al primo.

`params["derived"] = True` su **ogni** rilievo, come invariante d'area invece
che come giudizio caso per caso: la lettura che vince è «questo rilievo non
nasce da una misura di quest'area: descrive, non quantifica», perché dà al
consumatore una regola sola invece di tre classi.

**Nessun rilievo porta `penalty`, e l'assenza è il significato del
marcatore.** Sarebbe calcolabile — il composito è lineare come quello di
Lighthouse — e proprio per questo non va messo: sarebbe lo stesso deficit in
una seconda unità di misura, mentre l'area d'origine lo dichiara già con molto
più dettaglio. È **D3** portata dentro il dato.

**Tutti `info`, e non è prudenza**: la severità è l'asse su cui la Fase 4
ordina il piano, e su quell'asse una sintesi non deve **mai** scavalcare la
misura che sintetizza. «Segnale debole: Sicurezza (50/100)» e «[ZAP:High] SQL
injection (3 URL)» descrivono lo stesso difetto, e il secondo porta regola, URL
e soluzione.

**Un pareggio che decide quale segnale l'utente legge.** `deboli` si ordina per
valore e, a parità, per **etichetta italiana**; mettere il nome interno al posto
dell'etichetta invertiva sei coppie su ventuno, e il pareggio attraversa il
taglio `deboli[:2]` — cambiava *quale* segnale diventa issue. Il nome è entrato
come terzo elemento della tupla, dove non viene mai confrontato.

**Il doppio canale, accettato e non filtrato.** I findings della citabilità
escono nel JSON due volte (tre contando `modules` dell'API). Filtrarlo
significherebbe far decidere a `build_report` sul **nome del modulo**, che è
l'anti-pattern appena tolto da R38: si chiuderebbe un doppione
reintroducendone la causa.

**U1.9, `mars_llm_judge`**, la più piccola per ambito — e la cosa più
importante non è nel modulo, è in `conftest.py`. Scrivendo test sull'unica area
che **spende denaro**, la prima domanda era se la suite potesse spendere.
Misurato, non dedotto: un test con `ANTHROPIC_API_KEY` nell'ambiente faceva
partire **tre POST veri verso `api.anthropic.com`**. `niente_rete` copre
`requests`; l'SDK Anthropic passa da **httpx** e non lo vede — è **R20 nella
stessa forma**, sull'unico modulo che, se sfugge, presenta un conto.

La fixture `nessuna_spesa` intercetta `httpx.HTTPTransport.handle_request` e
**non** `httpx.Client.send`: il `TestClient` di FastAPI è *esso stesso* un
client httpx e verrebbe bloccato anche lui. E l'asserzione sta **dopo lo
`yield`**, perché sollevare non basta: l'SDK incapsula qualunque eccezione del
transport in un `APIConnectionError` che il modulo gestisce e dichiara, quindi
senza il controllo in coda un test che sfugge finirebbe **verde**, esercitando
il ramo sbagliato.

**Una chiave sbagliata non è una chiave assente**, e va saputo:
`AuthenticationError` **è** un `APIError`, quindi una chiave scaduta o revocata
— il caso reale più frequente — esce come `api_failed` e non come
`no_credentials`. Sono due fatti con riparazioni diverse: l'SDK non ha
**risolto** una credenziale contro l'API ha **rifiutato** quella risolta.

**Perché i `punti_deboli` non diventano rilievi.** `Finding.key` è ciò su cui
poggiano il confronto fra esecuzioni e i cataloghi di traduzione: una chiave
ricavata da prosa libera sarebbe o **variabile** — vietato — o **ripetuta**,
che distrugge l'identità e impedisce a un delta di distinguere «lo stesso punto
debole persiste» da «ne è comparso un altro». Registrato in **U10.1** con le
due condizioni che permetterebbero di riaprirla.

#### Che cosa ha insegnato la Fase 1

Le `issues` **non sono cambiate di una parola** in nessuna delle nove voci:
ogni adeguamento è stato verificato per confronto col codice precedente preso
da `git show` — 43 casi in U1.6, 52 in U1.7, 58 in U1.8, tutti e nove i rami in
U1.9 — sempre con zero divergenze.

Le mutazioni provate sono **162**. Una sola non è riproducibile (il default
mutabile che la dataclass rifiuta all'import) e resta contata come tale, non
fra i successi. Ma il valore non sta nel numero: sta nelle **tredici mutazioni
sfuggite alla prima esecuzione**, ciascuna delle quali ha rivelato un test
debole. Le classi, perché si ripresentano:

- **una costante confrontata con se stessa.** `len(items) == MAX_ELEMENTI`
  resta verde per qualunque valore della costante. Comparsa in U1.4 (le
  penalità di `mars_schema`, di cui era fissata solo la *relazione*) e di nuovo
  in U1.7;
- **un ordinamento mai asserito**, perché il dato di prova era già ordinato
  bene, o perché due criteri sembravano equivalenti e non lo erano;
- **il banco di prova che eseguiva bytecode vecchio.** In U1.7 le due mutazioni
  di un carattere — `3.0` → `5.0`, `5` → `3` — venivano applicate e
  ripristinate dentro lo stesso secondo, e pytest eseguiva la versione vecchia.
  Il difetto si è manifestato al rovescio: dopo il giro il sorgente diceva
  `3.0` e il runtime rispondeva `5.0`. **`PYTHONDONTWRITEBYTECODE=1`**, e da
  U1.8 in poi è stato applicato dall'inizio;
- **un guardiano che nessuno presidiava**: la fixture contro la spesa è
  rilevabile solo se qualcosa prova a passarle davanti. Il test verifica il
  **meccanismo** — che il transport sia sostituito — perché verificarne
  l'effetto richiederebbe di tentare una richiesta;
- **`Finding.area` non era asserito da nessun test di modulo**: sostituirlo col
  prefisso passava inosservato, a un carattere di distanza dall'errore;
- **mutazioni mal costruite da me**, tre volte: un `[] or [...]` che vale
  `[...]`, cioè un no-op travestito da mutazione, e due che rompevano la
  sintassi — un modulo che non si importa fa fallire tutto e non dimostra che
  il test cogliesse *quel* difetto.

`__version__` a **2.1.0**. Difetti trovati e non corretti qui, perché
avrebbero spostato punteggi o testi dentro un commit di sola forma: **R39**
(`mars_wapt`), **R40** (`mars_seo`), **R41** e **R42** (`mars_citability`),
più la chiusura parziale di **R31**.

### U2 — ✅ FASE CHIUSA (2026-08-24): i golden del referto
**Il problema.** `tests/test_report.py` fa asserzioni puntuali: colgono ciò che
qualcuno ha pensato di guardare, e una modifica di resa che non tocca quei
punti passa inosservata. Con **otto fasi di lavoro sul renderer davanti**,
quella rete andava montata prima. Sei file, tre formati × due referti
sintetici; nessuna riga di codice di produzione cambiata.

**Il dataset dichiara il proprio ambiente, non lo eredita**, ed è la decisione
che regge tutto il resto. Su questa macchina Lighthouse, ZAP, Playwright e
sentence-transformers sono *tutti* installati; su un runner nudo nessuno.
Misurato: lasciando decidere all'ambiente, l'area sicurezza scrive nel referto
la issue «Header non leggibili: **NienteRete**» — cioè **il nome di una fixture
del banco di prova finisce dentro il golden**. Un golden così misurerebbe quali
strumenti mancano su una macchina, non come si rende un referto.

**E non si costruisce a mano**, che sarebbe R33 ripetuto: si usano i moduli
**veri**, con l'uscita dello strumento iniettata **alla sua cucitura di I/O**.

**I moduli si prendono da `load_external_module`, non da un `import`**, ed è
una trappola che sarebbe costata caro: il caricatore **sostituisce** l'oggetto
in `sys.modules`, quindi `import mars_wcag` e il modulo che gira **non sono lo
stesso oggetto** (verificato: `m is mars_wcag` → `False`). Una patch
sull'oggetto importato non arriverebbe e il golden congelerebbe **il ramo di
ripiego** senza che nulla sollevi. È R20 in abito nuovo.

**Due referti e non uno**, perché ci sono rami che nessun singolo referto può
contenere insieme: un'area misurata e la stessa senza strumento, il giudizio
LLM reso e disattivato, robots rispettato e ignorato. I due insieme coprono
**tutte e nove le aree e tutte e cinque le voci di `STATO_LEGGIBILE`**, e
questo è **asserito**, non sperato: un'area nuova o uno stato nuovo diventano
rossi invece che invisibili.

**Iniezione dei campi volatili, non sostituzione a valle.** Il `_normalizza`
del progetto di riferimento sostituisce la forma JSON `"generated_at": "…"`; in
MARS il timestamp esce **nudo** dentro un `<p class='meta'>`, quindi copiarlo
avrebbe lasciato l'HTML volatile fino al primo cambio di fuso. Il valore è
plausibile e non un segnaposto: un renderer futuro che formattasse la data
cadrebbe su di esso.

**Due normalizzazioni per rendere il diff leggibile, ed è il punto della
fase.** `render_html` è un `"".join()`: tutto ciò che segue `</style>` era
**una riga sola da 13 KB**. Si spezza fra un tag e l'altro **prima di scrivere
il golden**, non solo prima di mostrare il diff, perché il mezzo della
revisione è `git diff tests/golden/` e su una riga da 13 KB la revisione non è
possibile — il presidio diventerebbe un rito. Misurato: 88 righe con la più
lunga da 12 958 caratteri diventano **515 righe con la più lunga da 182**.
La favicon, 3.773 caratteri di base64 sulla stessa riga, diventa un **digest**:
un cambio d'icona resta rilevato, il diff resta leggibile. Limite dichiarato:
il file non è più byte per byte ciò che `render_html` emette, e un a-capo
*letterale* fra due tag sarebbe invisibile.

**`.gitignore` ignorava il golden JSON.** Senza l'eccezione il golden si
sarebbe rigenerato in locale, il test sarebbe passato sulla macchina di chi
l'ha scritto, e **il file non sarebbe mai arrivato in CI**. Trappola da
conoscere: `git check-ignore` **con `-v` esce 0 anche su una regola di
negazione** — la prova è senza `-v`, o `git add -n`.

**Che cosa il golden NON è**, scritto perché non lo si scopra rigenerando: è un
golden **della pipeline**, non dei soli formati. I risultati d'area vengono dai
moduli veri, quindi un punteggio che cambia fa fallire tutti e sei i file. È il
prezzo della fedeltà: la rigenerazione non è il rimedio, è il primo di due
passi — il secondo è `git diff tests/golden/`, ed è lì che si distingue una
resa cambiata da una misura cambiata.

### U3 — ✅ FASE CHIUSA (2026-08-24): i testi di correzione, `__version__` a 2.2.0
*(tre sotto-voci: il catalogo, i testi degli strumenti, la resa.)*

**Il problema.** I moduli dicevano *che cosa* è rotto e mai *come* si aggiusta:
i campi `fix` ed `example` esistevano dalla Fase 1 ed erano vuoti in tutti
tranne `mars_wapt`, che la `solution` la prende da ZAP.

#### U3.1 — il catalogo

**Sta in un file suo, `mars_fixes.py`, e non dentro i moduli.** Tre ragioni: la
Fase 9 tradurrà **per chiave** da un catalogo, e coi testi sparsi in sei moduli
l'italiano vivrebbe in due forme che divergono senza che nulla si rompa; un
catalogo si legge *come catalogo*, che è l'unico modo di accorgersi che due
controlli vicini dicono la stessa cosa in due modi; e i moduli restano plugin —
**non importano il catalogo**, che si applica fuori.

**In Python e non in JSON**: un file di dati assente o illeggibile darebbe un
referto con tutti i `fix` vuoti e **nessun errore**, cioè la degradazione non
dichiarata che il principio 2 vieta. E gli esempi sono multiriga: in JSON
diventerebbero stringhe con `\n` letterali, irrivedibili in un `git diff`, cioè
fuori dal presidio che U2 aveva appena montato.

**Il modulo vince, il catalogo colma**: si scrive solo dove il campo è vuoto, e
questo permette a un plugin di terzi di portare i propri testi senza sapere che
il catalogo esista.

**Chi riceve un fix, e perché non tutti.** *Riceve un `fix` soltanto il rilievo
che descrive uno stato del sito che chi lo possiede può cambiare.* I
`*.status.*` sono fatti sulla **scansione**: «Lighthouse non trovato nel PATH»
ha un'azione ovvia, ma è un'istruzione per chi fa girare MARS, e un piano
consegnato a un cliente che dica «installa Lighthouse» ha sbagliato
destinatario.

**Due fix del progetto di riferimento sono stati bocciati**, non riusati: uno
era una *domanda* sotto un `warning` dove in MARS lo stesso rilievo è
**critico**; l'altro elencava i tipi Schema.org da aggiungere, ma `mars_schema`
**non guarda i tipi** — prescrivere più di quanto si misuri è falsa precisione.

**L'esempio di robots.txt non correggeva il difetto**, ed è il caso in cui per
poco non cascavo: mostrava tre blocchi permissivi, e chi lo incollasse **in
coda** al proprio robots.txt — la lettura naturale — resterebbe bloccato,
perché `RobotFileParser` tiene il **primo** gruppo che nomina quell'agente. Il
proprietario crederebbe di aver corretto e la scansione successiva direbbe di
no, senza modo di capire perché. Ora l'esempio mostra la **sostituzione**, e
c'è un test di andata e ritorno che lo dà in pasto a `controlla_robots` e
verifica che il rilievo si chiuda.

**Due esempi portano un'avvertenza dentro il fix**, e non è formalità:
`Content-Security-Policy-Report-Only` **non chiude** il rilievo, e HSTS è
**irrevocabile** per tutta la durata di `max-age`.

#### U3.2 — i testi che vengono dagli strumenti

**Una regola sola, misurata su tre strumenti: la spiegazione va in `detail`, la
prescrizione in `fix`.** Non è una convenzione decisa a tavolino, è ciò che i
testi dicono quando li si legge:

- **Lighthouse**: dei suoi undici audit SEO, **nove spiegano perché il
  controllo conta** e solo due prescrivono qualcosa. Quel testo dentro `fix`
  sarebbe il piano della Fase 4 che, alla voce *come si aggiusta*, spiega il
  problema;
- **axe**: delle 103 regole del locale italiano, **100 cominciano con
  "Assicurati"** — un imperativo, e più specifico del titolo, che degli
  elementi e delle vie d'uscita non dice nulla;
- **ZAP**: i due campi li tiene già separati lui.

**Il locale di axe si legge in Python, non nel browser.** axe accetta un
`axe.configure({locale})`, che tradurrebbe anche i titoli. Non si è fatto
perché così `score_from_violations` resta una funzione pura, e perché un locale
illeggibile costa **i testi e non la misura** — dentro la pagina farebbe
fallire `axe.run` e con lui l'intera area.

**La misura che ha cambiato il progetto: la suite era diventata dipendente
dalla macchina.** Spostando `AXE_LOCALE` su un file inesistente — cioè
simulando un clone appena fatto, senza `npm install` — **cinque test
diventavano rossi**. Verdi qui, rossi altrove, e nessuno se ne sarebbe accorto
fino alla prima CI. La cura è `locale_axe_fisso` in `conftest.py`, che fissa un
locale **presente** e non assente come fanno le altre fixture, perché i casi
non si somigliano: quelli sono strumenti che si installano a parte, questo è un
file dentro lo stesso pacchetto npm che `axe_disponibile()` già pretende.

E la fixture è **presidiata**, perché su questa macchina la sua assenza è
invisibile: un test asserisce che durante la suite `testi_axe()` valga
esattamente i due testi fissati, 2 regole e non 103.

**Le fixture sono diventate più fedeli, non solo più ricche**: gli undici
`description` di `_lhr()` sono **verbatim** dal locale italiano di Lighthouse
13.4.1, coi link Markdown dentro — riscriverli a mano vorrebbe dire inventare
il Markdown che si dice di saper ripulire — e un test li confronta col file
vero.

**Trovato e non chiuso**: nel ramo axe i titoli del referto sono **in inglese**,
e la fixture del golden lo nascondeva perché i suoi `help` erano già italiani.
È **R44**.

#### U3.3 — la resa

**Non esiste una chiave fra `issues` e `findings`, ed è la scoperta che ha
deciso la forma.** Sembrano due viste della stessa cosa e non lo sono:
**per posizione** si disallineano appena axe o ZAP superano le cinque regole,
perché le issues si fermano a cinque e i rilievi no — non è un caso di
laboratorio, è quasi ogni sito reale, e il guasto sarebbe *silenzioso*; **per
somiglianza del testo** fallisce su `mars_schema`, dove nessuna delle due
contiene l'altra. L'unica area con una chiave vera è `mars_seo`, ed è infatti
l'unica in cui la spiegazione sta **in linea**.

**Dove non c'è chiave, il blocco è separato**, e la ripetizione dei titoli è il
prezzo di una scelta dichiarata: le `issues` portano cose che il rilievo tiene
nei `params`, e **ricostruirle nel referto dai params significherebbe
riscrivere lì la presentazione che sta nei moduli**.

**Due difetti visti nel diff del golden, non nel codice** — ed è esattamente
ciò per cui U2 esiste: il blocco stampava `source_severity` accanto al titolo,
dove sta **già** due centimetri più su; e l'area **in errore** finiva sotto
«Come si aggiusta», perché il blocco accettava chi avesse un `detail`
qualunque, e «MemoryError: corpus troppo grande» non aggiusta niente.

**Anche la vista testo, e con la stessa forma.** La prima stesura si era
fermata all'HTML con l'argomento che le righe compatte portano già i conteggi:
l'argomento era buono per *sostituire* le issues, non per non aggiungere nulla,
e chi usa la CLI non avrebbe mai visto una prescrizione. L'`example` resta
fuori dal solo testo — blocchi nginx e JSON-LD di cinque o sette righe
triplicherebbero un referto che sta in un terminale.

#### Numeri della fase

Cinquantadue mutazioni nei tre commit, tutte rilevate; la suite da 559 a 612
test. I golden si sono mossi **una volta ciascuno**: i `.json` in U3.1, il solo
`referto.json` in U3.2, i `.html` e i `.txt` in U3.3. È la divisione in tre che
rende leggibile ciò che sarebbe stato un unico diff di settecento righe.

### U4 — ✅ FASE CHIUSA (2026-08-25): il piano di interventi, `__version__` a 2.3.0
*(cinque sotto-voci: la funzione pura, il dato, la vista testo, la vista HTML,
le azioni di profilo.)*

**Il problema.** Fra «elenco dei difetti» e «che cosa faccio lunedì mattina»
non c'era nulla.

**Il numero che il piano pubblica è il RECUPERO, non la penalità**, ed è il
difetto più facile dell'intera fase:

    recupero = R(base − penalità) − R(base),  R(P) = max(0, round(100 − P))

`base` è la somma delle penalità di **tutti** i rilievi dell'area, `info`
compresi: sommando i soli candidati la ricostruzione si romperebbe in silenzio.
Due conseguenze misurate: **un'area satura vale meno di quel che sembra** (con
base 108 e score 0, un rilievo da 40 ne recupera 32 e uno da 8 non muove
niente), e **i recuperi non sono additivi** — su `mars_wcag` del golden, 37 +
18 + 7 uno alla volta fanno 62, chiudendoli insieme si guadagnano 63. Ogni voce
porta `additive: False` **nel dato** e non solo nella resa, perché il CSV della
Fase 6 e il confronto della Fase 7 sommeranno ciò che trovano.

**Il certificato d'area.** U4 è il **primo consumatore** di
`params["penalty"]`: fino a qui quel campo lo leggevano solo i test, e la
coerenza fra penalità e punteggio non l'aveva mai verificata nessuno. Un'area
non certificata **tiene le sue voci e perde i numeri**, dichiarandolo. Il gate
ha un ramo apposta per le aree sature, perché con score già a 0 il confronto è
falso per costruzione e senza quel ramo un'area satura perderebbe i numeri
proprio dove servono di più.

**Il guadagno di citabilità è una derivata**, e i suoi `k` **non sono
costanti**: dipendono dal mercato e da quanti segnali sono stati misurati in
quella esecuzione — misurato, `tecnica` vale 0,1885 nel referto completo
(mercato `eu`, 7 segnali) e 0,4045 in quello degradato (`global`, 4). Per
questo ogni voce porta con sé il mercato, e **confrontare due `index_gain` di
referti diversi non significa niente**.

**Quattro corsie, perché «non lo so» e «so che vale zero» sono opposti** per
chi decide lunedì mattina: `misurato`, `bloccato`, `ignoto`, `nullo`. La corsia
viene **prima dei numeri** nella chiave d'ordinamento, così nessun confronto
numerico incontra un `None` — senza, due voci in corsia `ignoto` solleverebbero
`TypeError` dopo che tutte le aree hanno girato.

**Il quick win vuole tre condizioni**, non due: critico, da minuti, **e con un
recupero che esiste davvero**. Il terzo termine non è pignoleria — nel golden
completo due rilievi sono critici con penalità 0,0 perché in quel ramo il
punteggio lo fa axe, e senza il piano aprirebbe con due vittorie rapide che
lasciano l'area dov'era.

**Lo sforzo è un catalogo chiuso** sulle 25 chiavi di `mars_fixes`, e un test
pretende che i due insiemi coincidano: un controllo con un `fix` e senza sforzo
non potrebbe mai essere un quick win, uno con lo sforzo e senza `fix`
prometterebbe un intervento che il referto non sa descrivere.

**La duplicazione che si vedeva a occhio nudo.** Rigenerando i golden per la
prima volta, ogni correzione compariva **due volte in quaranta righe** — in un
referto largo 55 colonne è insostenibile. Ora sotto l'area restano solo le
correzioni che il piano **non** prende in carico. Non è un ripensamento su
U3.3: quelle righe erano la risposta giusta finché il piano non esisteva.

**Il `fix` si ripete nell'HTML e non nel testo**, ed è una scelta opposta presa
poche ore dopo: là il lettore aveva le due righe sott'occhio insieme, qui sono
due sezioni di un documento lungo e un intervento che non dicesse *che cosa
fare* manderebbe a cercarlo.

**Nessuna chiave nuova nel dato.** UPGRADE.md prevedeva una `top_actions`
accanto alla citabilità: non si fa, perché sarebbe una seconda copia del piano
che diverge in silenzio dalla prima. La sezione legge la lista canonica e la
riordina.

**Una trappola dei selettori annidati, colta prima di consegnarla.** La scheda
riusa la classe `riga` delle schede d'area, ma il CSS la definiva come
`.area .riga`, cioè **ristretta**: dentro `.intervento` titolo e badge
sarebbero rimasti impilati. **Nessun test sul contenuto lo avrebbe visto**,
perché l'HTML sarebbe stato identico.

**Un aggancio fragile, dichiarato**: il referto pubblica
`citability["signals"]` indicizzato per **etichetta italiana**, e
`mars_remediation` inverte `SEGNALI` per tornare ai nomi. La Fase 9,
traducendo le etichette, lo romperebbe — non in silenzio: i coefficienti
diventano `None` e i guadagni spariscono.

**Il bump a 2.3.0, e una rete che mancava.** Il numero di versione vive in due
posti — `__version__` e la riga in testa al README — e alzarne uno solo non
rompeva niente: è la deriva di R32. Ora un test li lega, e nasce da una
**mutazione sfuggita** che nessun test presidiava. Il banco ha mostrato un suo
limite: valida con `ast.parse` ogni file mutato, quindi una mutazione su un
`.md` viene scartata come «sintassi rotta» — quella sul README è stata
verificata a mano.

#### Che cosa la fase ha dimostrato sul metodo

Il progetto è stato preceduto da **dodici agenti in sola lettura** — sei
letture parallele, tre proposte indipendenti, una sintesi, due critici
avversariali. I due critici hanno prodotto **18 obiezioni, tutte verificate sul
codice**, e due erano bloccanti:

- la sintesi proponeva una chiave pubblica nuova giustificandola con
  «`import mars_citability` non funzionerebbe, perché `load_external_module`
  sostituisce l'oggetto in `sys.modules`». **Falso**, e riverificato di
  persona: gli oggetti-modulo sono due, ma le costanti sono uguali. Sono caduti
  **due commit su otto**;
- gli `index_gain` erano dichiarati additivi. Non lo sono.

Senza quella verifica sarebbero nati due commit inutili e una chiave pubblica
in più nel dato canonico.

Cinque commit, la suite da 659 a 698 test, **sessantotto mutazioni** tutte
rilevate, golden mossi una volta per commit. Lasciate aperte: **R46** e il
widget «Top rilievi», che UPGRADE.md lega all'hero della Fase 5.

### R45 — ✅ (2026-08-25): due numeri sulla stessa area, e perché differiscono
**Il difetto, trovato sul campo.** Confrontando il referto con PageSpeed
Insights su un sito vero, la differenza era enorme e inspiegabile a chi legge:
**Lighthouse 97 all'accessibilità, MARS 59**. Non è un disaccordo sui fatti.
Verificato eseguendo il Lighthouse 13.4.1 locale, lo stesso che MARS invoca:

- usano **lo stesso strumento**, axe-core, e hanno trovato **lo stesso
  difetto**, `color-contrast`;
- Lighthouse fa una **media pesata** su 76 controlli, peso totale 226, dove
  `color-contrast` pesa 7 — il 3%. Da lì il 97;
- MARS **sottrae penalità**: `color-contrast` è `serious`, 12 punti, per la
  diffusione (tutte e 5 le pagine, quindi 2×) fa 24; più
  `scrollable-region-focusable`, 16,8. Totale 40,8, da cui il 59.

Due differenze strutturali oltre alla scala: MARS guarda **5 pagine**,
Lighthouse **una**; e `scrollable-region-focusable` **non è nella categoria
accessibility di Lighthouse** — verificato sul LHR — quindi non ci sarebbe
entrato nemmeno guardando lo stesso campione. Sull'unico numero che è la
**stessa misura**, il SEO, non c'era alcuna differenza: 100 per entrambi.

**La decisione, presa dall'utente fra tre alternative**: pubblicare entrambi i
numeri con la nota che il nostro è più restrittivo. È la risposta che non tocca
la misura e non nasconde niente — chi apre PageSpeed accanto al referto i due
numeri li vede comunque, e tacerne uno non li rende uguali, li rende
inspiegabili.

**Costo zero, e una cosa che si buttava via.** `esegui_lighthouse` non passa
`--only-categories`, quindi Lighthouse calcola **tutte e cinque** le categorie
a ogni run, e `mars_seo` ne teneva una. Ora le pubblica tutte, e `mars_wcag`
legge da lì: **nessun secondo Lighthouse**, perché gira dopo `mars_seo` nel
registro.

**Le chiavi sono generiche**, `reference_score` e `reference_tool`: il
confronto non è una proprietà di quello strumento.

Due dettagli che sarebbero passati: il confronto vale **anche nel ramo di
ripiego**, dove serve di più; e la condizione è `is not None` e non la verità
del valore, altrimenti **uno zero dell'altro strumento sparirebbe** — cioè
proprio il caso peggiore.

**Non chiude la questione della scala**, e va detto: MARS resta molto più
severo, e un solo controllo violato su tutte le pagine costa un quarto del
punteggio. Ora però il referto lo dichiara.

### U5 — ✅ FASE CHIUSA (2026-08-25): complessivo, hero e ancore, `__version__` a 2.4.0
**Il punteggio complessivo** è la media pesata delle sole aree **misurate**,
rinormalizzata su quelle presenti: un'area senza strumento non abbassa il
complessivo, lo rende **meno informato**. I due segnali derivati pesano **1,5**
contro l'1,0 di un'area, perché non vengono da uno strumento esterno ma dal
confronto fra i due recuperatori, che è la domanda del progetto.

Citabilità e giudizio LLM sono esclusi **per nome** e non per una proprietà del
dato (D3), ed è deliberato: la prima è una sintesi dei punteggi altrui, il
secondo è opzionale e **a pagamento** — con dentro, lo stesso sito darebbe due
complessivi a seconda che si sia speso o no. Per nome restano fuori **anche
quando falliscono**, che è proprio il caso in cui una regola basata sul dato li
lascerebbe rientrare.

La chiave `overall` porta i **componenti e i pesi**: un numero che riassume
nove aree vale quanto la possibilità di rifarne il conto, e senza sarebbe
l'unica cifra del referto che nessuno può verificare.

**L'hero riusa lo stesso `_quadrante`** della fascia sotto, solo più grande per
CSS: disegnarne un secondo, anche identico, vorrebbe dire avere due archi da
tenere allineati.

I conteggi per gravità **escludono i derivati** — è la seconda casella di R41,
e con essa la voce si chiude. Il test costruisce un derivato **critico**
apposta, perché oggi li terrebbe fuori anche la sola gravità: è la protezione
incidentale che R41 denuncia.

**Il donut previsto dal piano diventa due numeri.** La quota di URL scartati
non è un voto — un PDF o un altro host sono scarti legittimi — e un anello la
colorerebbe con la scala dei punteggi. Il taglio giusto (senza rilievi / con
rilievi / scartate) richiede le pagine sui rilievi, che allora non c'erano: è
**R49**, sbloccata da R47.

**Le ancore, e una prescrizione che non serviva.** UPGRADE.md prevedeva uno
slug ricavato dal **titolo**, coi numeri normalizzati perché «2/3 pagine» e
«117/400 pagine» non producessero due ancore diverse. Non serve: dalla Fase 1
ogni rilievo ha già una `key` stabile per costruzione, ed è esattamente il
problema che quello slug risolveva a valle. Il progetto di riferimento non
aveva chiavi, noi sì.

Il punto diventa trattino: un id coi punti è legale in HTML5, ma
`#tech.robots.ai_blocked` in un selettore CSS si legge come un id più due
classi. Oggi nessuno lo interroga, e proprio per questo conviene non lasciare
la mina.

**Le ancore si calcolano una volta sola** e si passano a chi le usa, perché
**un link rotto in un referto HTML non fa alcun rumore**: la pagina resta
valida, il browser non protesta, il salto semplicemente non succede. Per questo
l'invariante è un test: 20 ancore emesse e 20 link, zero rotti.

Scrivendo quel test è emerso un fatto dato per scontato al contrario: un
rilievo *senza* `fix` non esiste quasi mai, perché `vesti_findings` glielo
riempie dal catalogo. Il caso va costruito su una famiglia **dinamica**.

Trentadue mutazioni, nessuna sfuggita.

### R41 — ✅ CHIUSA (2026-08-25): `derived` ha finalmente dei lettori
**Il difetto.** Da U1.8 ogni rilievo di `mars_citability` porta
`params["derived"] = True`, ma il marcatore **non aveva un lettore** —
`grep -rn '"derived"' *.py` trovava solo il modulo che lo scriveva — e le tre
guardie contro il doppio conteggio non erano equivalenti: l'assenza di
`penalty` protegge le *somme*, non l'*elenco*, e `severity: info` è ciò che li
escludeva davvero, ma è una protezione **incidentale**.

**Chiusa in due tempi**, dai due consumatori nati nel frattempo: U4.1 li
esclude dal piano, U5.2 dai conteggi per gravità dell'hero — senza, i
`cit.*.unmeasured` avrebbero gonfiato la casella «Info» accanto ai rilievi che
ripetono, riaprendo sui *conteggi* il doppio conteggio che D3 chiude sul
*punteggio*.

Entrambi i test costruiscono un derivato **critico** apposta, cioè uno stato
che oggi nessun modulo produce: senza, verificherebbero la protezione
incidentale invece di quella vera.

Resta valida l'eccezione: `cit.status.error` **non** porta `derived` — non è
una sintesi ma un guasto del nostro strumento, e nessun'altra area lo sta già
dicendo.

### U6 — ✅ FASE CHIUSA (2026-08-25): Markdown e CSV, `__version__` a 2.5.0
**Markdown** è l'unico formato in cui il piano diventa **operativo** invece che
leggibile: una task list GFM si spunta. Un test pretende che le caselle si
consegnino **vuote**, perché `- [x]` in un referto direbbe che l'intervento è
già fatto. La gravità è un **marcatore testuale** e non un colore: senza badge,
affidarla alla sola posizione nell'elenco la perderebbe appena qualcuno
riordina o copia una riga.

`_md_cella` neutralizza i due caratteri che rompono una tabella GFM e arrivano
da fuori: la **pipe** e l'**a-capo**. Gli `example` vanno invece in blocchi
recintati, perché indentazione e a-capo di un blocco nginx *sono* il contenuto.

**CSV**: `;` come delimitatore e **BOM UTF-8** in testa, e non sono vezzi —
senza BOM Excel legge un file UTF-8 nella codepage di sistema e
«Accessibilità» diventa «AccessibilitÃ»; con la virgola, nelle impostazioni
italiane finisce tutto in una colonna sola. Chi vuole i byte puliti ha il JSON,
ed è il motivo per cui questa resa esiste separata.

Le celle passano dal modulo `csv` della stdlib e non da una concatenazione a
mano: un `fix` di ZAP pieno di virgolette spezzerebbe il file, e sono dati che
vengono da fuori. `sforzo` e `quick_win` restano **vuoti** dove il rilievo non
è azionabile — vuoto e non «no», che sembrerebbe una valutazione che nessuno ha
fatto. E il CSV **tiene i derivati**: R41 li esclude da chi *aggrega* e li
tiene per chi li mostra uno per uno.

**Nessuna riga di codice nella CLI né nei golden.** `RENDERERS` è la sola
registrazione: la CLI legge `choices=tuple(RENDERERS)` e la Fase 2 itera già
sul registro, quindi i quattro golden nuovi sono nati da soli. È il ritorno di
due decisioni prese fasi fa.

Una cosa scoperta scrivendo i test: la fixture del referto non aveva
`findings`, e il CSV ne usciva con la sola intestazione — esercitava una forma
che in produzione non esiste.

### U7 — ✅ FASE CHIUSA (2026-08-25): riproducibilità e storia, `__version__` a 2.6.0
**I metadati.** `schema_version` sale **solo** su un cambiamento incompatibile:
senza quella distinzione servirebbe una versione nuova a ogni fase del
programma UPGRADE, e il numero smetterebbe di dire qualcosa. Accanto, i
parametri che rendono il referto rileggibile fra sei mesi: `rrf` col k della
fusione — che viveva come **default di una funzione**, e due esecuzioni con k
diversi non sono confrontabili — e `thresholds`, oggi `null`. Null e non chiave
mancante: quando le soglie diventeranno configurabili, nessuno dovrà
distinguere «assente perché vecchio» da «assente perché di serie».

Un test guarda il **codice** e non il dato: il referto dichiara `RRF_K`, ma la
fusione la chiamano quattro moduli, e se uno passasse un `k` suo il referto
direbbe il falso senza che nessun test sul contenuto se ne accorga. Verificato
con `ast` su tutti i `mars_*.py`.

**Lo storico è JSONL append-only**, una riga compatta per esecuzione: il
referto intero pesa 1.500 righe di JSON, e conservarne uno per esecuzione
trasformerebbe lo storico in un archivio che nessuno rilegge. Una riga corrotta
non invalida le altre — è il vantaggio del JSONL sul JSON, ed è la ragione del
formato.

**Il confronto è per chiave**, ed è il ritorno della Fase 1: una `key` non
contiene mai un valore variabile, quindi resta la stessa quando le pagine senza
canonical passano da 2 a 117 — confrontare i *titoli* direbbe un rilievo
risolto e uno nuovo, cioè il contrario del vero. Per i rilievi senza chiave si
ripiega sul titolo coi numeri normalizzati **e il delta lo dichiara**: è un
confronto più debole, e chi legge deve saperlo.

**Tre decisioni che sarebbero potute andare storte:**

- **un'area misurata ieri e non oggi non è peggiorata**: non è stata guardata.
  Sarebbe stata la bugia più facile della fase;
- **il colore del delta segue il segno, non la scala dei punteggi**: qui non si
  giudica quanto vale l'area, si dice se è salita, e un 59 che sale da 40 è una
  buona notizia che la scala dipingerebbe di rosso;
- **la sezione non compare alla prima esecuzione**, all'opposto del piano, dove
  resta anche vuota: lì il vuoto è un risultato, qui è un'assenza — «tutto
  invariato» e «non c'è un prima» sono cose diverse.

**Lo storico non può far fallire un audit**: un file assente, illeggibile o non
scrivibile viene dichiarato, perché il referto è già prodotto e perdere una riga
di archivio non vale il codice di uscita.

**Il golden completo ha ora un'esecuzione precedente**, congelata a mano e non
prodotta da un secondo giro dei moduli: se la generasse il codice, il delta
uscirebbe vuoto e il golden congelerebbe una sezione che non dice niente.

Ventisei mutazioni; due sfuggite al primo giro erano un buco vero — il
cablaggio nella CLI, leggere prima e appendere dopo, non era presidiato da
nulla.

### U8 — ✅ FASE CHIUSA (2026-08-25): le analisi della superficie, `__version__` a 2.7.0
*(quattro sotto-voci: `pages[]` e la profondità, la matematica, la treemap, il
grafo.)*

**U8.1 — la superficie come dato.** `pages[]` porta per ogni URL il titolo, la
lingua, la profondità, gli heading, i chunk e i tipi Schema.org — nessuna delle
nove aree lo espone, e per un'integrazione è il dato più utile dopo i rilievi.
Esce **senza il contenuto**: `html` e `text` sono centinaia di kilobyte per
pagina.

**Lo status HTTP non c'è, e non si inventa**: nel dict pagina non esiste,
perché solo le 200 entrano in `pages`. Scriverci un 200 fisso vorrebbe dire
pubblicare una misura che nessuno ha fatto.

Le pagine che vengono dalla **sola sitemap** hanno profondità `None` —
dichiarate dal sito, ma nessuno le ha raggiunte seguendo i link, e chiamarle
«profondità 0» direbbe che stanno in home. Quel secchiello non è un residuo: un
contenuto che sta nella sitemap e in nessun percorso di navigazione è un
contenuto che un assistente trova **solo se sa già che esiste**, ed è la
scoperta più utile della sezione.

I **tipi Schema.org** si leggono nelle tre forme che i siti veri usano
(`@type` stringa, lista, dentro un `@graph`). Un blocco che non si analizza
**non diventa un giudizio**: lo dice già `mars_schema`.

**U8.2 — la matematica.** Due recuperatori che pescano fra dodici passaggi e
due che pescano fra quaranta non fanno lo stesso lavoro. **È una proiezione, e
lo dice il dato**: `assumption` viaggia dentro `surface_math` e ogni vista la
ripete — è la differenza fra «potresti avere 12 passaggi» e «*se* ogni pagina
arrivasse a 900 parole», e chi non è d'accordo col numero deve poterlo vedere
invece di dedurlo dal risultato.

Due dettagli che sarebbero passati: il moltiplicatore è `None` e non `1.0`
quando non ci sono passaggi, perché «x1» su zero suonerebbe come «sei già a
posto»; e il secchiello delle profondità ignote è **giallo, non rosso** —
non è un livello peggiore, è un livello che non sappiamo.

**Una collisione, e la spia che ne è uscita più forte.** La sezione si chiama
«Superficie», e un test di regressione di R21 cercava la parola `superficie`
come spia. Ora cerca la frase intera, «controllo di superficie», che è la
stringa vera di `STATO_LEGGIBILE`: restringere la spia rende il presidio più
forte. Rinominare la sezione sarebbe stato più comodo e avrebbe lasciato in
piedi una spia ambigua.

**U8.3 — la treemap.** Il colore di gravità previsto dal piano **non c'era**,
e non era una rinuncia estetica: misurato prima di scrivere, `Finding.url` era
vuoto in otto aree su nove e nella nona portava il link alla documentazione
axe — **zero corrispondenze possibili**. Applicata alla lettera, quella regola
avrebbe dipinto **ogni** pagina di «nessun problema»: la forma esatta di R21,
e invisibile, perché un verde uniforme non ha l'aria di un errore. Aperta come
**R47**, chiusa il 2026-08-26.

**Le pagine senza testo si contano invece di sparire**: non hanno superficie da
disegnare, ma sono quelle che interessano di più, ed escluderle in silenzio le
farebbe sembrare inesistenti invece che vuote.

**I rettangoli non sono focalizzabili, e il riferimento lo faceva.**
`marsbeacon` mette `tabindex="0"` su ogni `<rect>`, ma lì c'è il JavaScript che
al fuoco scrive nel riquadro di stato. Qui no, e senza JS il `<title>` al fuoco
**non compare**: sarebbero quaranta fermate di tabulazione che non mostrano
nulla, cioè un ostacolo travestito da accessibilità. Copiare il riferimento
senza la sua metà dinamica avrebbe peggiorato la pagina.

**Il giro di mutazioni ha cambiato due test, e la lezione vale oltre la voce.**
Sedici mutazioni tutte colte **sull'intera suite**, dove il golden HTML fa da
rete; rieseguite contro il **solo** `test_report.py`, quattro sfuggivano — i
test mirati non dicevano nulla su ciò che rende una treemap *squarified*.
Misurato: il layout corretto tiene il rapporto d'aspetto peggiore a **2.0**,
mentre due varianti sbagliate arrivano a **327** e **72** — schegge che non si
confrontano più a occhio, con le aree ancora perfettamente proporzionali.
**Una mutazione colta dal golden non dimostra che il test mirato serva**: è
l'ordine alfabetico dei file a decidere chi fallisce per primo.

**Le etichette si troncano dalla testa, e il golden non poteva dirlo.** Reso su
un sito sintetico di cinquanta pagine sotto lo stesso percorso, tutti e
quaranta i rettangoli portavano `/sezione-molto-l`: il troncamento a destra
taglia via proprio la parte che distingue le pagine. Il referto sintetico ha
tre pagine con percorsi corti, quindi non ne mostrava traccia — è un difetto
che si vede solo rendendo un caso realistico.

**U8.4 — il grafo dei link.** **Il dato non c'era, e UPGRADE.md diceva di sì**:
il piano dava per fatto che «il crawler estrae già `links` per pagina», ma
`links` porta il **testo** delle ancore e non un solo href. Gli href esistevano
in `estrai_link` ma erano **consumati e buttati**, e per di più solo nel ramo
che segue i link — un sito con sitemap, cioè quasi tutti, sarebbe rimasto senza
architettura da mostrare.

**La fixture usa la stessa funzione del crawler**, e non è pignoleria: una
fixture che riscrivesse l'estrazione dei link congelerebbe nei golden un grafo
che in produzione non esiste — è il difetto che R44 ha pagato sui titoli axe.

**Due misure di profondità che convivono, e non si confondono.**
`pages[].depth` dice come il crawler è arrivato a una pagina ed è ignota per
quelle da sitemap; `clicks` del grafo è il cammino più breve dalla home
**dentro il campione**. Sono vere insieme, hanno nomi diversi, e riusarne uno
solo avrebbe fatto sembrare risolto un problema che resta.

**«Orfana» ha una riserva, e il referto la dichiara.** Dentro un campione di
dieci pagine, una pagina può risultare orfana solo perché chi la linka non è
stato scaricato: `closed` misura se **nessun** link interno esce dal campione.
Senza quel confronto il giallo sarebbe stato un'accusa fondata su un artefatto
di `--max-pages`. E senza un punto di partenza `orphans` è **`None`, non zero**.

**D1 applicata: il vincolo passa da «nessuno script» a «nessuna origine
esterna».** È il vincolo vero, e lo era da sempre: uno `<script src>` fa uscire
il referto dal file, uno inline no. I due test che dicevano `"<script" not in
uscita` erano **verdi per caso** — la loro fixture ha una pagina sola, quindi
nessun grafo e nessuno script, e avrebbero continuato a passare mentre il
vincolo si allentava sotto.

Tre proprietà dello script, ciascuna col suo test: nessuna origine esterna;
**nessun dato del referto dentro il codice**, perché interpolarlo sarebbe un
secondo percorso di escaping accanto a `_e()` ed è così che nasce una XSS in un
file che contiene testo preso dal sito analizzato — verificato con un URL che
contiene `</script>`; e lo script **non c'è** dove non c'è un grafo.

**Progressive enhancement fino in fondo.** I **comandi nascono `hidden`** e li
accende lo script per ultimo, perché un bottone che non fa nulla è peggio di un
bottone assente; i nodi **non hanno `tabindex` nell'HTML**, glielo mette lo
script, che al fuoco ha qualcosa da mostrare — la regola di U8.3 al contrario.

**Della simulazione a forze viva del riferimento non si è portato nulla**:
~400 righe di JavaScript con fisica dal vivo, contro un layout già calcolato e
fermo. Meno codice da presidiare in un file che si consegna. È una **riduzione
consapevole**, non una dimenticanza.

**Diciotto mutazioni, due sfuggite, e nessuna delle due era un test debole**:
il tetto ai sessanta nodi non aveva **alcun** test, e l'altra ha rivelato
**codice irraggiungibile** — `orphans` escludeva la home con
`and not n["home"]`, ma la home è la radice del BFS e ha sempre distanza 0.
Sembrava una garanzia ed era decorazione. **Una mutazione che non fa fallire
nulla non è sempre un test mancante: a volte è codice che non fa nulla.**

#### Il filo della fase

Non è il disegno: è che **tre volte su quattro la fase ha dovuto dire *non lo
sappiamo* invece di riempire un buco** — lo status HTTP che non si inventa, il
moltiplicatore `None` invece di «x1», il colore della treemap che sarebbe stato
un via libera mai misurato, la riserva sul campione parziale. Il piano
prevedeva quattro disegni; quello che è costato di più è stato decidere che
cosa **non** potevano dire.

Aperte da qui: **R47** (chiusa il 2026-08-26) e **R48**.

### U9 — ✅ FASE CHIUSA (2026-08-25): i18n del referto, `__version__` a 2.8.0
*(tre sotto-voci: l'impianto e il catalogo dei rilievi, la cornice, la lingua
chiesta agli strumenti.)*

**La premessa del piano non reggeva, ed è stata misurata prima di
cominciare.** UPGRADE.md prevedeva cinque lingue riusando i cataloghi «già
scritti in marsbeacon dove i controlli coincidono». Sulle chiavi vere: il
riferimento ne ha **145**, MARS ne emette **49**, e **ne coincidono quattro**.
Non è una questione di nomi da riallineare: il riferimento **non ha una sola
chiave `wcag.`, `sec.` o `seo.`**, che sono tre delle nove aree di MARS. Le
traduzioni si scrivono, non si copiano.

**D4 ratificata: due lingue, dichiarate come livello inferiore.** Quattro
lingue scritte da zero senza che nessuno qui possa verificarle sarebbero
quattro lingue di qualità **non misurata**, cioè il contrario del principio 5.
L'impianto non assume che le lingue siano due: aggiungerne una costa un
catalogo e una voce in `LINGUE`.

**L'italiano non entra nel catalogo**: vive dove il rilievo nasce, e qui c'è
solo ciò che l'italiano non è. È la stessa ragione per cui `mars_fixes.py` era
stato scritto come catalogo — se l'italiano vivesse in due forme, le due
divergerebbero senza che nulla si rompa.

**`finding_texts()` non solleva mai**, e ripiega **campo per campo**: un
referto con una riga nella lingua sbagliata si legge, uno interrotto a metà no.

**Tre famiglie non si traducono qui** — `wcag.axe.*`, `sec.zap.*`, `seo.lh.*`
prendono il testo dallo strumento che ha fatto la misura. Riscriverle
significherebbe due errori insieme: dire peggio di axe, ZAP e Lighthouse ciò
che loro dicono, e invecchiare accanto a loro a ogni release.

**`lang` si passa a mano, e non è pigrizia.** L'alternativa era un
`ContextVar`, che avrebbe risparmiato un parametro in quarantatré funzioni. Non
attraversa il threadpool: FastAPI esegue gli handler sincroni su thread di un
pool, e un `ContextVar` in un thread nuovo parte dal proprio default — il
referto sarebbe uscito in italiano via API e in inglese via CLI, **senza un
errore**.

**Il catalogo è indicizzato sul testo italiano**, non su chiavi simboliche: così
l'italiano resta scritto per esteso nel renderer, dove lo si legge accanto al
codice che lo usa, e la stessa funzione traduce anche i testi che arrivano dal
**dato**, che con chiavi simboliche sarebbero rimasti italiani.

**Il prezzo si è presentato subito, due volte.** «Da migliorare» è il verdetto
di un punteggio fra 50 e 89 (*needs work*) ed è l'etichetta dei punti deboli
del giudizio LLM (*to improve*); e «click» in italiano non cambia al plurale,
quindi `_plurale(3, "click", "click")` chiede due volte la stessa parola e
l'inglese sarebbe uscito «3 click». Da qui il `contesto` di `t()`, che è il
`msgctxt` di gettext. La prima l'ha colta `flake8` (`F601`); **la seconda no**,
e sarebbe passata — le due parole sono identiche, quindi per il dizionario non
c'era nessun duplicato.

**Due difetti veri, trovati misurando invece che leggendo.** Reso il referto in
inglese e cercate le righe rimaste italiane, sono comparse voci che il catalogo
*conteneva*: le **voci del piano non portavano i `params`**, quindi
`finding_texts` non trovava i valori del template e ripiegava sull'italiano —
un referto con le schede d'area tradotte e il piano, cioè la parte che si
consegna, in italiano; e **lo storico non li portava**, quindi la sezione
«rispetto a prima» non sarebbe stata traducibile in nessun momento futuro,
nemmeno per i rilievi **risolti**, che in quella esecuzione non esistono più e
vivono solo lì. Misurato prima di decidere: la riga passa da 2,4 a 4,8 KB.

**Le `issues` non si possono tradurre, e il referto lo dice**: sono prosa
italiana senza chiave, quindi non c'è nulla su cui indicizzare una traduzione.
Fuori dall'italiano le viste compatte mostrano i **titoli dei rilievi**; dove i
rilievi non ci sono, `_nota_lingua` nomina le aree **per nome** invece di dirlo
genericamente.

**L'API non prende `lang`, ed è una constatazione e non una dimenticanza**:
tutti gli handler restituiscono il dato canonico e nessuno rende prosa, quindi
il campo sarebbe stato inerte — configurazione che non configura nulla.

**Il presidio è a tre versi**, perché il ripiego non fa rumore: ogni letterale
passato a `t()` dev'essere a catalogo — letto dall'**AST** e non con una regex,
perché `t()` compare dentro `%`, concatenazioni e condizionali, e una stringa
spezzata su quattro righe una regex non la ricompone; ogni testo che arriva dal
dato dev'essere a catalogo, enumerato **dalle costanti** e non dai due referti
sintetici, che delle quattro corsie del piano ne accendono una; e nessuna voce
dev'essere **orfana**. Quest'ultimo ha fatto il suo mestiere subito: ha mostrato
che l'estrattore AST era troppo stretto, e le venticinque voci che segnalava
erano vive.

**Il buco che i golden non potevano coprire.** Il primo test sui segnaposto
girava sui due referti sintetici, che di `tech.` accendono **due chiavi su
dodici**: una mutazione `%(pagine)d` → `%(pages)d` è passata **verde**, perché
il ripiego non fa rumore. Ora `_params_del_banco()` fa girare i moduli **veri**
su contesti costruiti apposta, e il test **pretende** che ogni template con un
segnaposto abbia un caso che lo accenda: 25 su 25. Una chiave nuova con un
segnaposto e senza caso è rossa il giorno in cui nasce.

#### U9.3, e R44 chiusa

**La lingua entra nel `context`, accanto a `market` e `llm`**, e non resta un
parametro di resa: axe, ZAP e Lighthouse producono i propri testi **al momento
della misura**, quindi glieli si deve chiedere allora — a valle non c'è più
nulla da tradurre.

**R44**: `wcag.axe.*` portava come titolo il `help` **inglese** di axe, dentro
un'interfaccia italiana e accanto a un `fix` che italiano lo era, perché quello
veniva dal locale. Si è presa la strada di leggere il locale in Python e non
`axe.configure({locale})`, perché dentro la pagina un locale illeggibile
farebbe fallire `axe.run` e costerebbe **la misura** invece dei soli testi.

Ne discende una cosa non ovvia: **per l'inglese un file di locale non esiste, e
non serve** — cercarne uno inesistente e dichiararne l'assenza segnalerebbe un
difetto dove non ce n'è uno. E `wcag.status.no_fixes` cambia significato: non è
più «manca il `fix`» ma «manca la **lingua**».

**La riga compatta divergeva dal rilievo, e nessuno lo vedeva**: le issues
leggevano `voce["help"]` grezzo mentre il `Finding` portava il titolo tradotto
— due implementazioni dello stesso testo.

**La fixture del golden congelava un'illusione.** `_violazioni_axe()` scriveva
`help` in italiano — testi che axe non ha mai prodotto, né in inglese né in
italiano: erano **inventati**. Ora porta i testi inglesi verbatim di axe-core
4.13.0.

**Il referto dichiara quali strumenti hanno scritto in un'altra lingua**, e non
lo indovina: nessuno qui riconosce una lingua leggendo un testo. Le tre aree lo
scrivono nel dato **per rilievo e non per area**, perché un locale axe copre
quasi tutte le regole ma non quelle aggiunte con `axe.configure`, e dire
«l'area è in italiano» con dentro due regole inglesi sarebbe una mezza verità.
Per Lighthouse la lingua si legge da `configSettings.locale`, cioè da ciò che
**ha fatto** e non da ciò che gli abbiamo chiesto.

**La nota compare anche in italiano**, ed è la parte che vale di più: ZAP
scrive solo in inglese, e un referto italiano che non lo dicesse lascerebbe
credere a una dimenticanza ciò che è un limite dello strumento.

**Un secondo test vacuo, trovato guardando l'esito e non il verde**: la prova
che «le aree non tradotte sono nominate per esteso» cercava «3. Lexical» nel
referto intero, dove compare comunque nella riga d'area.

**Tredici mutazioni, una sfuggita, e non era di poco conto**: togliendo
`context.get("lang")` dalla chiamata a `score_from_violations` la suite
restava **verde**, perché il predefinito è l'italiano e ogni test del ramo axe
gira in italiano — la cucitura fra il contesto e lo strumento non era
esercitata da nessuno, e un audit in inglese avrebbe prodotto testi italiani
senza che nulla lo dicesse.

#### Il filo della fase

Il ripiego di una traduzione è **silenzioso per costruzione** — esce
l'italiano, che è un esito valido — quindi ogni difetto di questa fase era
invisibile e nessuno si è trovato leggendo il codice. Li ha trovati tutti la
stessa mossa: **rendere il referto in inglese e misurare che cosa restava
italiano**. Così è emerso che il residuo finale era esattamente il perimetro
degli strumenti, cioè U9.3.

**Due limiti restano, dichiarati**: le `issues` sono prosa senza chiave e non
si traducono; e ZAP parla inglese e basta. Il referto dice l'una e l'altra cosa
in testa.

### R44 — ✅ RISOLTO (2026-08-25, da U9.3): nel ramo axe il referto parlava inglese
*(la voce è stata scritta verificando che ogni correzione dichiarata chiusa
avesse una sezione qui: R44 era stata chiusa **dentro** U9.3 e non ne aveva una
propria — chi l'avesse cercata non avrebbe trovato nulla.)*

Il difetto, la soluzione e la fixture resa fedele stanno in **U9.3** qui sopra.

### I1 — ✅ REALIZZATA (2026-08-25, da U7): audit differenziale
**Che cosa chiedeva**: `--baseline report-precedente.json`, con output «+12
SEO, −5 WCAG, 2 nuovi problemi».

**La forma proposta non è stata adottata, e la differenza conta:**

- **JSONL append-only invece di `--baseline <file>`.** Un file per esecuzione
  richiede a chi lo lancia di ricordarsi quale sia il precedente; uno storico
  lo sa da sé, e filtra per URL perché un solo file possa raccogliere più siti
  — confrontarne due diversi darebbe un delta pieno di «risolti» che nessuno ha
  toccato;
- **il confronto è per `key` stabile, non per titolo**, e senza sarebbe stata
  una funzione che mente: «1 blocchi malformati» → «2 blocchi malformati»
  avrebbe mostrato un difetto risolto e uno nuovo, quando è lo stesso difetto
  peggiorato;
- **la riga dello storico non porta il referto intero**, solo ciò che serve a
  confrontarlo col prossimo.

### I13 — ✅ REALIZZATA (2026-08-25): test diretti del `Crawler`
**La premessa era falsa**, e verificato con un conteggio invece che a occhio:
in `tests/test_core.py` `crawl()` è chiamato **17** volte, `estrai_link()` 3,
`robots()` 3, `can_fetch()` 2.

**Il modo è esattamente quello che l'idea proponeva**, ed è la ragione per cui
si chiude senza aver fatto nulla apposta: un `BaseAdapter` finto montato sulla
`session`. L'adattatore deve restare **fedele** a
`HTTPAdapter.build_response`, perché quando fissava `resp.encoding` tre
mutazioni di R16 su cinque passavano inosservate, e finché non impostava
`resp.request` il difetto R17 non si manifestava affatto.

**Non è stata chiusa da un commit suo**: si è chiusa da sé, chiudendo R15-R24 e
U8.1. È il motivo per cui è rimasta aperta nel TO-DO per cinque giorni dopo
essere diventata vera — nessuno l'ha riletta finché non si è riverificata ogni
voce sul codice.

### Programma UPGRADE — le quattro decisioni e il quadro delle fasi

| | decisione | esito | applicata da |
|---|---|---|---|
| **D1** | JavaScript nel referto | **Sì**, vanilla inline, progressive enhancement: l'SVG statico resta la base, nessuna origine esterna | **U8.4**. Il vincolo «NESSUNO SCRIPT» è diventato «nessuna origine esterna» — che è il vincolo vero — e i due test che lo presidiavano, **verdi per caso**, sono stati riscritti |
| **D2** | Scala di severità canonica | **Sì**, quattro livelli. La granularità in più delle tre scale esistenti si conserva nel **peso**, non in livelli extra | **U1**, in tutte e nove le aree |
| **D3** | Pesi del complessivo | **Sì**: aree misurate a 1.0, i due segnali derivati a 1.5; **esclusi** Citabilità (conterebbe due volte) e Giudizio LLM (opzionale e a pagamento) | **U5**, `overall_score()` |
| **D4** | Lingue | **it ed en**, livello **inferiore** al riferimento a cinque lingue e dichiarato tale. Il riuso previsto dal piano è stato **misurato prima di decidere**: 4 chiavi su 49 | **U9.1** |

| fase | che cosa | versione | ha lasciato aperto |
|---|---|---|---|
| **U1** | il modello dati dei rilievi (`Finding`), nove sotto-voci | 2.1.0 | **R39**, **R40**, **R42**, **U13** — adeguare la *forma* ha fatto leggere sei moduli riga per riga, e ogni difetto trovato lì è stato lasciato aperto invece che corretto dentro un commit che non doveva spostare punteggi né testi |
| **U2** | i golden: sei file, tre formati su due referti sintetici | — | **R43** |
| **U3** | i testi `fix` ed `example`, e la regola «spiegazione in `detail`, prescrizione in `fix`» | 2.2.0 | **R44** (chiusa da U9.3) |
| **U4** | il piano di interventi: il **recupero**, non la penalità | 2.3.0 | **R46** |
| **U5** | complessivo, hero e ancore dalla `key` | 2.4.0 | chiude **R41** |
| **U6** | Markdown e CSV, registrati in `RENDERERS` | 2.5.0 | — |
| **U7** | riproducibilità e storia, confronto per **chiave stabile** | 2.6.0 | realizza **I1** |
| **U8** | l'analisi della superficie: profondità, `surface_math`, treemap, grafo | 2.7.0 | **R47** (chiusa il 2026-08-26), **R48** |
| **U9** | i18n del referto (it/en), fino alla lingua **chiesta agli strumenti** | 2.8.0 | chiude **R44** |

**Le convenzioni della lavorazione**: un commit per fase, bump di
`__version__` (minor per fase), `pytest` verde senza rete e `flake8 .` a zero
prima del commit, golden rigenerati **intenzionalmente** dalla Fase 2 in poi.
Le nove fasi chiuse sono state lavorate sul ramo `upgrade`, rifuso in
`main` e cancellato il 2026-08-27: da lì in avanti il programma prosegue
su `main`.

#### Mappa delle sotto-voci

Ogni fase è stata lavorata in più commit, e **il codice e i test citano quei
numeri**. La potatura del 2026-08-26 ha fuso le sotto-voci dentro la voce di
fase: questa tabella dice dove atterrare.

| sotto-voce | che cosa ha fatto | sta in |
|---|---|---|
| U1.1-U1.9 | il modello, il consumatore prima dei produttori, poi le sei aree, `mars_citability` e `mars_llm_judge` | **U1** |
| U3.1 | il catalogo `mars_fixes.py` | **U3** |
| U3.2 | i testi che vengono dagli strumenti (axe, ZAP, Lighthouse) | **U3** |
| U3.3 | la resa dei testi di correzione | **U3** |
| U4.1 | il piano come funzione pura, `mars_remediation.py` | **U4** |
| U4.2 | il piano entra nel dato canonico (`remediation`) | **U4** |
| U4.3 | il piano nella vista testo, e la duplicazione tolta | **U4** |
| U4.4 | il piano nella vista HTML | **U4** |
| U4.5 | «Azioni con maggior guadagno di profilo», bump a 2.3.0 | **U4** |
| U5.1 | `overall_score()`, il punteggio complessivo | **U5** |
| U5.2 | l'hero e i conteggi per gravità (chiude R41) | **U5** |
| U5.3 | le ancore stabili ricavate dalla `key` | **U5** |
| U7.1-U7.2 | metadati di riproducibilità, storico e delta | **U7** |
| U8.1-U8.4 | `pages[]` e profondità, `surface_math`, treemap, grafo | **U8** |
| U9.1 | l'impianto i18n e il catalogo dei rilievi | **U9** |
| U9.2 | la cornice, e `lang` attraverso i renderer | **U9** |
| U9.3 | la lingua chiesta agli strumenti (chiude R44) | **U9** |

### R63 — ✅ (2026-08-28): il menu di navigazione non è contenuto

*(l'ha trovato **il giudizio LLM alla sua prima esecuzione vera** — C4/C2 —
non una revisione: «sei passaggi su otto sono solo menu di navigazione».)*

**Il difetto.** `chunk_page` segmenta per heading, e tutto ciò che sta prima
del primo `<h*>` diventa un passaggio con `heading` vuoto. Su un sito con un
megamenu quella è la navigazione. Misurato sul corpus reale, 8 pagine:

| | prima | dopo |
|---|---|---|
| chunk del corpus | 128 | **94** |
| chunk senza alcun heading | 23 (18%) | **0** |
| chunk identici su più pagine | 37 | **9** |
| parole nel corpus | 13 969 | 9 959 |

I nove rimasti non sono navigazione: sono il blocco «Potrebbe interessarti
anche», che sta dentro `<article>`, e due elenchi di prerequisiti identici fra
due tutorial. Contenuto vero, e resta.

**La regola, e perché non le altre due.** Escono `nav` sempre — è navigazione
per definizione, briciole di pane e indici di pagina compresi — e `header` /
`footer` **solo quando stanno fuori da `main` e `article`**. Le altre due
strade che il TO-DO elencava sono state misurate e scartate:

- *scartare i chunk senza heading* butta via contenuto vero: su questo sito
  l'attacco di ogni articolo — data, firma, prima frase — sta dentro un
  `<header>` **di sezione**, ed è esattamente il caso che la condizione
  «fuori da main/article» protegge;
- *scartare i chunk ripetuti su più pagine* funziona solo con abbastanza
  pagine, e cancellerebbe un claim o un disclaimer legittimamente ripetuto.

**Non si decompone nulla**: si cammina e si salta. Il DOM resta intero perché
il grafo dei link ha bisogno proprio dei link del menu, e `links_internal`
pure. Il testo di pagina (`pagina["text"]`) segue la stessa regola: regge il
controllo «sotto le N parole» di `mars_lexical`, e contarci dentro un megamenu
fa passare per piena una pagina vuota — sul sito misurato il menu vale fra il
**19% e il 36%** delle parole.

**Effetto end-to-end, stesso sito e stesso HTML:**

| | prima | dopo |
|---|---|---|
| quota in forma di risposta | 19,5% | **28,7%** |
| consenso aggregato | 0/3 | 1/3 |
| citabilità IA | 63,8 | 71,0 |
| **complessivo** | **59,2** | **67,1** |
| passaggio più recuperabile | un URL senza heading | l'articolo sul server proxy |

Il sito non è migliorato: MARS ha smesso di misurare la propria navigazione.

**Perché la versione sale a 2.10.0.** I numeri si muovono a sito invariato,
quindi un archivio scritto prima non è confrontabile alla pari. Il delta lo
dichiara con `measure_changes`, un elenco gemello di `MIGRAZIONI_CHIAVE`: là
cambia il NOME di un controllo, qui cambia che cosa si misura. Il confronto
non si butta via, si dichiara indebolito — la stessa scelta di
`by_title_fallback` e di `rrf_k_changed`. `schema_version` resta **3**:
nessuna chiave cambia forma.

**Prove.**

- Sei mutazioni. **Due sono sopravvissute al primo giro**, e sono la parte che
  vale la pena registrare:
  1. togliere `nav` dall'elenco lasciava tutto verde, perché nel primo HTML di
     prova il `<nav>` di pagina stava dentro `<header>` — già escluso — e
     quello dentro `main` era troppo corto per diventare un chunk. La prova
     passava per la ragione sbagliata;
  2. rimettere `soup.get_text()` dentro il crawler lasciava tutto verde,
     perché `conftest.pagina()` chiama `testo_contenuto` per conto suo: il
     banco di prova provava la funzione e **non la cucitura**. È R56 in un
     altro punto — un anello che nessun test attraversava.

  Chiuse tutt'e due: un `<nav>` di pagina lungo abbastanza da fare un chunk, e
  un test che passa dal `Crawler` vero con l'adattatore finto montato. Al
  secondo giro le sei mutazioni sono tutte colte.
- Golden rigenerati e diff riveduto. Le pagine sintetiche non hanno
  `nav`/`header`/`footer`, quindi **il corpus dei golden non si è mosso di un
  carattere**: l'unica differenza è la nuova nota del delta.
- Nel farlo è emerso un difetto del banco di prova: il golden congelava la
  versione **dopo** aver composto il referto, quindi le dichiarazioni che
  dipendono dalla versione entravano con quella viva. La guardia dei campi
  volatili lo ha rilevato, e la si è estesa a `MISURE_CAMBIATE` come già
  faceva per le migrazioni di chiave.
- `pytest` **1176 passed**, `flake8 .` a zero.

### C4/C2 — ✅ VERIFICATA SUL CAMPO (2026-08-28): il giudizio LLM contro il servizio reale

*(era l'unica area del referto mai eseguita davvero: **bloccata su una chiave**,
non sul codice. L'utente ne ha messa una in un file `--credentials`.)*

**Che cosa è stato eseguito.** Un audit completo di `lymphatechnologies.com`
(8 pagine, cinque query di dominio, `--embeddings none`) con `--llm on` e la
chiave vera. Non una simulazione: **la richiesta è partita**, il modello ha
risposto, e il referto porta l'esito.

| | |
|---|---|
| modello | `claude-opus-5` |
| passaggi inviati | 8 |
| costo dichiarato prima dell'invio | ~2187 token stimati (8750 caratteri) |
| citabilità stimata | **18/100** |
| rilievi prodotti | nessuno, ed è previsto (U1.9: un giudizio riuscito non ne produce) |

**Che cosa la verifica ha provato**, e che nessun test poteva provare:

- il percorso reale dell'SDK funziona — costruzione del client dalla chiave del
  file, richiesta beta con `output_config` in JSON schema, `thinking:
  adaptive`, e la risposta **si analizza**: `citabilita`, `motivazione`,
  `punti_forti`, `punti_deboli`, `passaggio_migliore` arrivano tutti;
- l'annuncio della spesa compare **una volta sola e prima dell'invio**, che è
  ciò che R58 ha corretto ieri: «Giudizio LLM: invio 8 passaggi (~2187 token
  stimati) a claude-opus-5…»;
- il referto conserva la prosa per intero in JSON e la rende leggibile nella
  vista testo, motivazione compresa;
- **la chiave non compare nel referto**, né intera né in un frammento di venti
  caratteri: verificato cercandola nel file prodotto.

**Il giudizio ha trovato un difetto di MARS, non del sito.** La motivazione
dice: «la maggior parte dei passaggi recuperati è puro boilerplate di
navigazione (menu del sito)», e il primo punto debole è «6 passaggi su 8 sono
solo menu di navigazione». È vero, ed è misurato: vedi **R63** nel TO-DO. Il
primo uso reale dell'area 9 ha quindi fatto esattamente ciò per cui esiste —
guardare i passaggi che una ricerca ibrida selezionerebbe davvero — e ha
segnalato che quei passaggi, su questo sito, sono in buona parte il menu.

**Nessuna riga di codice è cambiata**: la voce chiedeva una prova, e la prova è
questa. `pytest` **1167 passed**, `flake8 .` a zero, invariati.

### I3 — ✅ REALIZZATA (2026-08-27): `--rrf-k`, e che cosa cambia davvero

*(idea decisa dall'utente. La voce la dava «didattica, quasi gratis»: la misura
ha detto un'altra cosa.)*

**Che cosa c'era.** `k=60` era il default di `reciprocal_rank_fusion()`, e un
presidio di U7 vietava a chiunque di passarne uno: il referto dichiarava
`rrf.k = RRF_K`, e chi lo avesse passato avrebbe fatto girare la fusione con un
numero diverso da quello dichiarato.

**La misura, prima di scrivere.** L'idea chiedeva di «mostrare come cambia il
consenso al variare di k». Misurato su due corpora:

| | k=0 | k=10 | k=60 | k=300 | k=1000 |
|---|---|---|---|---|---|
| consenso **per query** (5 query, sito reale) | 0,0,2,0,2 | *identico* | *identico* | *identico* | *identico* |
| consenso **aggregato** (128 chunk, sito reale) | 1/3 | **3/3** | **0/3** | 0/3 | 0/3 |

Il consenso di una singola query **non può** dipendere da k: è l'incrocio dei
primi tre di due classifiche, e la fusione non entra nel conto. Sondarlo
darebbe una riga piatta che sembra una misura di robustezza e non lo è.

Il consenso **aggregato** invece dai ranghi fusi viene, e si muove moltissimo —
e non è un numero qualsiasi: `segnali_derivati()` lo trasforma nel segnale
**«Recuperabilità»**, che entra nel punteggio complessivo. Sullo stesso sito,
lo stesso giorno, con lo stesso corpus: **100 a k=10, 0 a k=60**. Cioè il
parametro che l'idea chiamava didattico sposta un voto pubblicato.

**Che cosa è stato fatto.**

- `--rrf-k N` (CLI) e `rrf_k` (API), default 60, con `k >= 0` validato ai due
  bordi: la formula divide per `k + posizione + 1`, e k=-1 sul primo posto è
  una divisione per zero che arriverebbe **a scansione fatta**.
- `context["rrf_k"]`, letto dai tre moduli che fondono (`mars_lexical`,
  `mars_semantic`, `mars_llm_judge`) e dalle tre fusioni del referto.
- **Il presidio di U7 è stato rovesciato, non tolto**: diceva «nessuno passa un
  k esplicito», ed era giusto finché il k era una costante. Ora la stessa
  divergenza si ottiene **non** passandolo, quindi il test pretende che ogni
  chiamata lo passi e che non sia un letterale — un `60` scritto a mano in un
  modulo è il k inventato che il presidio esiste per impedire.
- `rrf_sensitivity` nel dato e una riga nelle tre viste che lo rendono:
  `al variare di k: k=0 3/3 · k=10 3/3 · k=60 (in uso) 0/3 · k=300 0/3`.
  Si rifondono le classifiche **già calcolate**: nessuna interrogazione in più.
- La riga di storico archivia il k, e il delta dichiara `rrf_k_changed`: un
  consenso che scende da 3/3 a 0/3 perché è cambiato il k **non è un fatto del
  sito**, ed è esattamente ciò che la sezione «rispetto a prima» sembrerebbe
  dire. È la stessa scelta di `by_title_fallback` e `key_migrations` — il
  confronto non si butta via, si dichiara indebolito.

**Additivo**: `schema_version` resta **3**. Nessuna chiave rimossa o
rinominata; `rrf.k` cambia valore solo se l'utente lo chiede.

**Prove.**

- **End-to-end sul sito reale, due audit identici salvo il k** — stesso
  crawl, stesse cinque query, `--embeddings none`:

  | | `--rrf-k 10` | `--rrf-k 60` |
  |---|---|---|
  | `rrf.k` dichiarato | 10 | 60 |
  | consenso aggregato | **3/3** | **0/3** |
  | segnale «Recuperabilità» | 100.0 | 0.0 |
  | **punteggio complessivo** | **77.9** | **59.2** |

  Diciotto punti e sette decimi di differenza fra due referti dello stesso
  sito, prodotti nello stesso minuto, per un parametro che fino a ieri non si
  vedeva. È la ragione per cui il sondaggio sta nel referto e il k
  nell'archivio.
- Sette mutazioni, tutte colte: contesto che ignora il k; referto che dichiara
  la costante invece del k in uso; CLI che non propaga il flag; validatore che
  accetta un k negativo; sondaggio senza il k in uso; storico che non registra
  il k; delta che tace il k cambiato.
- Un test che non dipende dal corpus: si guarda il k che la fusione **riceve**,
  non l'ordine che ne esce. Sul corpus della fixture l'ordine è lo stesso per
  ogni k — provato: il confronto fra ranghi passava anche senza il parametro
  collegato.
- Golden rigenerati e diff riveduto: due chiavi additive nel JSON e una riga
  nelle tre viste, nient'altro.
- `pytest` **1167 passed**, `flake8 .` a zero.

### U11.1 — ✅ (2026-08-27): la palette del referto è quella del sito

*(chiesta dall'utente, con il perimetro ristretto da lui: «il look & feel può
limitarsi SOLO ai colori; stile solo chiaro e favicon resta quella di MARS».)*

**Perimetro, e cosa NON è stato fatto.** Solo colori. Restano com'erano i
caratteri (stack di sistema: incorporare Titillium Web sarebbe costato ~72 KB
di base64 su un referto di 57, misurato sui woff2 del sito), le forme (raggi,
spaziature, la card a 20px del sito), la testata senza logo e la favicon di
MARS. Non sono caselle rimaste aperte: sono decisioni prese.

**La palette, misurata sugli stili calcolati di `lymphatechnologies.com`** —
Bootstrap Italia 2.16, cioè il design system della PA:

| token | prima | ora | dove |
|---|---|---|---|
| `--fg` | `#1f2328` | `#14272b` | testo del corpo |
| `--brand` | *non esisteva* | `#0c3540` | h1, h2, h3 |
| `--link` | *non esisteva* | `#1e4c5a` | link |
| `--ok` | `#0cce6b` | `#008055` | punteggi buoni, controlli superati |
| `--warn` | `#ffa400` | `#995c00` | avvertenze, etichetta del `fix` |
| `--bad` | `#ff4e42` | `#cc334d` | critici, controlli falliti |
| `--muted` | `#5f6771` | `#556879` | testo secondario |
| `--track` | `#e8ebee` | `#e6edee` | fondo di `code`, `pre`, `li:target` |

**I colori di gravità non sono un vezzo estetico, ed è la scoperta della
voce.** Quelli di Lighthouse, che il referto usa **come testo**, stanno su
bianco a **2,09:1** (`--ok`) e **1,99:1** (`--warn`): sotto perfino la soglia
3:1 dei componenti, cioè il referto che misura l'accessibilità falliva i
propri criteri. I tre di Bootstrap Italia stanno tutti sopra 4,5:1.

**Due tinte sono state scostate da quelle del sito, e la ragione è misurata,
non estetica**: `--muted` è il grigio del sito (`#5d7083`) sceso di un
gradino, perché a quella tinta il `<code>` dentro `.meta` sta a **4,19:1** sul
proprio fondo; `--track` è salito di un gradino perché l'etichetta del `fix`
dentro un rilievo raggiunto da un'ancora (`li:target`) ci finisce sopra e
stava a **4,44:1**. Nessuna delle due l'ha trovata una lettura del CSS: le ha
trovate **axe, eseguito sul referto stesso**.

**Divergenza dal piano, dichiarata**: [UPGRADE.md](UPGRADE.md) §6.2 elenca
«chiaro/scuro via `prefers-color-scheme`» fra le caratteristiche del referto
definitivo. Non è più vero, per decisione del proprietario: il tema è uno solo.
Il piano resta il piano e non si riscrive — qui sta la realizzazione, e vince
questa.

**Prove.**

- **axe-core sul referto stesso**, con Chromium, regole WCAG 2.1 A e AA:
  **prima 87 nodi in violazione** (tutti `color-contrast`, gravità *serious*),
  **dopo zero**, su entrambi i referti sintetici e anche con un rilievo
  raggiunto da un'ancora, che cambia il fondo. 25 controlli superati.
- Un test in suite che non ha bisogno del browser: ogni colore di testo contro
  **i fondi su cui finisce davvero**. La prima versione guardava il solo
  `--bg`, passava, e axe trovava lo stesso i quattro `<code>` a 4,19:1 — la
  lezione è nel commento del test, insieme al perché `--track` non prende
  `ok` e `bad`.
- Cinque mutazioni, tutte colte: ognuno dei tre colori riportato a quello di
  prima → il test dei contrasti; il tema scuro rimesso → il test del tema
  unico; i titoli riportati al colore del corpo → i golden, che è esattamente
  ciò per cui esistono.
- Golden HTML rigenerati e **diff riveduto**: il cambiamento è tutto dentro
  `<style>`; nel corpo non si è mosso un carattere.
- `pytest` **1149 passed**, `flake8 .` a zero.

### R62 — ✅ (2026-08-27): il file delle chiavi non si capiva come si scrive

*(segnalata dall'utente: «non si comprende come da mars_audit.py si possa
passare il json con le API keys». R57 aveva dato la strada e non il modello.)*

**Il difetto.** `--credentials FILE` diceva *quali* chiavi accetta e mai *che
forma* ha il file. L'unica istruzione concreta, nell'aiuto e nel README, era
«copia `examples/audit_request.json`» — che è **il corpo di una richiesta
API**: chi lo apriva trovava `url`, `max_pages`, `queries` e non poteva sapere
quale parte servisse alla CLI.

**E la strada indicata aveva un secondo difetto, misurato.**
`load_credentials("examples/audit_request.json")` restituisce **quattro
credenziali** — i quattro segnaposto — e nessun avviso su di essi:

    anthropic_api_key  "SEGNAPOSTO-sostituire-fuori-dal-repository"
    hf_token           "SEGNAPOSTO-solo-per-modelli-Hugging-Face-…"
    zap_api_key        "SEGNAPOSTO-oppure-omettere-se-api.disablekey=true"
    zap_proxy          "http://127.0.0.1:8080"

Chi copia quel file e riempie la sola chiave Anthropic consegna a
`huggingface_hub` e a ZAP due segnaposto come se fossero chiavi vere: gli
strumenti li rifiutano, e l'area si degrada senza che nessuno abbia sbagliato
a scrivere una chiave. Il file è severo sui *tipi* (R57) e muto sui
**contenuti**, che non può giudicare.

**Soluzione.** Un modello suo, `examples/credentials.json`, con **una sola
chiave da riempire** e le altre tre nominate dal commento; l'aiuto della CLI
mostra il contenuto del file per intero nell'epilogo, che è l'unica forma che
non si può fraintendere:

    {"credentials": {"anthropic_api_key": "sk-ant-..."}}

Il valore è **vuoto** apposta: `""` non è utilizzabile, quindi il modello
copiato e non modificato **ferma l'audit con codice 2 nominando la chiave**,
invece di girare consegnando segnaposto. Nessun cambiamento al codice del
lettore: la severità che serviva c'era già, mancava un modello che ci
andasse d'accordo.

**Prove.**

- Misurato prima: `examples/audit_request.json` passato a `--credentials`
  consegna quattro segnaposto con l'unico avviso «leggibile da altri utenti».
- End-to-end sul modello nuovo: copiato e **non** modificato → uscita **2**,
  «valore non utilizzabile per anthropic_api_key» su `stderr`, `stdout` vuoto,
  nessuna richiesta al sito; riempito → esce esattamente
  `{"anthropic_api_key": …}` e nessun messaggio, perché il commento in testa
  sta fuori da `credentials` e non conta come chiave ignota.
- Quattro test nuovi: il modello esiste e **non versiona alcuna chiave**; non
  si usa per sbaglio così com'è; riempito dà esattamente ciò che ci si è
  scritto; l'aiuto mostra il JSON e nomina `examples/credentials.json`.
- Il presidio già in casa ha fatto il suo: togliendo la parola «Esempio:»
  dall'aiuto, `test_ogni_parametro_mostra_valori_o_esempio` è diventato rosso.
- `pytest` **1147 passed**, `flake8 .` a zero.

### R61 — ✅ (2026-08-27): l'etichetta «Correzione:» stava nel CSS

*(trovata chiudendo **R60**, due righe più in su nello stesso foglio di stile.
Non è passata dal TO-DO: aperta e chiusa nello stesso commit.)*

**Il difetto.** Il prefisso di ogni correzione era una regola CSS —
`.fix::before { content:"Correzione: " }` — e `content` non passa da alcun
catalogo. In un referto `--lang en` il blocco si intitolava «How to fix it» e
ogni voce dentro cominciava con «Correzione:». Il Markdown la traduceva già,
con `t("Correzione:", lang)`: due viste dello stesso dato, due lingue diverse.
È R44 in un altro punto — «nel ramo axe il referto parlava inglese» — col verso
invertito.

**Soluzione.** L'etichetta scende nel markup, `<span class='fix-eti'>`, con lo
**stesso letterale** che il Markdown già usa, quindi la traduzione esisteva
di suo. Il CSS conserva il solo colore.

**Quello che la correzione ha scoperto**: `<span class='fix'>` lo emettono
**due** punti — la scheda d'area e il piano di interventi — e il secondo
prendeva l'etichetta dal CSS come il primo. Corretto il solo primo, il piano
sarebbe rimasto **senza alcun prefisso**, in tutte e due le lingue: un difetto
nuovo introdotto correggendone uno. L'ha visto il conteggio del test — 17
«Fix:» contro 32 `<span class='fix'>` — e non una lettura del codice.

**Prove.**

- Un test che guarda il referto **intero, CSS compreso**: in inglese la parola
  «Correzione» non compare da nessuna parte, e le etichette sono tante quante
  le correzioni (32 = 32, in entrambe le lingue).
- Tre mutazioni, tutte colte: etichetta rimessa nel CSS → 3 rossi; **piano
  senza etichetta** → 3, ed è la metà che sfuggiva; etichetta cablata invece
  che tradotta → 1.
- Golden rigenerati e diff riveduto: due soli file, i due HTML; nessun testo
  italiano cambiato, nessun punteggio.
- `pytest` **1143 passed**, `flake8 .` a zero.

### R60 — ✅ (2026-08-27): un esempio senza didascalia si legge come una misura

*(aperta da un referto vero, letto da chi lo riceve — non da una revisione.)*

**Il fatto.** Nella scheda «4. Semantica» di un audit su
`lymphatechnologies.com` compariva, sotto il rilievo, questo blocco:

    <h2>Quanto dura una seduta?</h2>
    <p>Una seduta dura circa cinquanta minuti, prima valutazione compresa.</p>

Il destinatario del referto lo ha letto come **contenuto di un altro sito
finito nel suo**, e ha chiesto conto del perimetro.

**Che cos'era davvero.** L'`example` di `sem.answer_shaped.low`, cablato in
[mars_fixes.py:268](mars_fixes.py#L268): un esempio inventato di come si scrive
un passaggio in forma di risposta. Riprodotto rilanciando l'audit per intero (8
pagine, `--llm on`, `--i-own-this-domain`, embedding reali).

**Il perimetro non c'entrava, ed è stato misurato invece che affermato**: nel
referto compare **un solo host**, `https://www.lymphatechnologies.com`. Nessuna
pagina estranea scaricata, nessun link fuori host seguito. Il difetto è di
resa.

**Causa radice.** `_correzioni_html()` rendeva l'`example` come `<pre
class='ex'>` senza didascalia, e **nell'intero referto la parola «esempio» non
compariva nemmeno una volta**. Un blocco nginx o un JSON-LD si riconoscono da
soli; un esempio scritto in prosa italiana plausibile no — ed è esattamente
quello che `sem.answer_shaped.low` deve mostrare, perché il rilievo parla della
forma della prosa. La classe è «esempio in prosa», non «questo esempio»:
`wcag.alt.missing` porta `alt="La sala trattamenti"`, dallo stesso sito
immaginario.

**Soluzione** (opzione scelta dall'utente fra tre): una didascalia sopra ogni
blocco — «Esempio — non è contenuto del tuo sito» — in HTML e in Markdown, a
catalogo i18n. Gli esempi restano realistici: è ciò che li rende utili, e
renderli finti avrebbe tolto valore senza chiudere la classe.

**Il letterale sta nel renderer e non in una costante condivisa**, e non è
sciatteria: `test_ogni_letterale_della_cornice_e_a_catalogo` legge l'AST e
indicizza sul **testo italiano** passato a `t()`. Una costante scollega la
traduzione senza rompere nulla — il primo tentativo l'ha fatto, e il presidio
è diventato rosso subito («voce di cornice orfana»).

**Prove.**

- Riprodotto e verificato **sul sito vero**, prima e dopo: la didascalia ora
  precede il blocco nel referto reale, e i due conteggi coincidono (2 esempi,
  2 didascalie).
- Quattro test nuovi in `tests/test_report.py`: la didascalia c'è ed è **sopra**
  il blocco; l'invariante sui due referti sintetici in entrambe le lingue —
  contando `<span class='ex-nota'>` e non la stringa nuda, che compare anche
  nella regola CSS; la traduzione inglese; il Markdown che dice la stessa cosa.
- Quattro mutazioni, tutte colte: didascalia HTML tolta → 5 rossi; didascalia
  **sotto** il blocco → 3; didascalia Markdown tolta → 3; **una parola cambiata
  nel letterale** → 5, fra cui la guardia del catalogo i18n, che è la prova che
  la traduzione resta agganciata.
- Golden rigenerati e **diff riveduto**: 38 righe aggiunte in quattro file, e
  sono la regola CSS più una didascalia per blocco. Nessun punteggio, nessun
  testo, nessuna riga del JSON, del CSV o della vista testo si è mossa.
- `pytest` **1142 passed**, `flake8 .` a zero.

### R59 — ✅ (2026-08-27): diagnostica su `stderr`, referto su `stdout`

*(ultima delle quattro voci nate dall'esecuzione reale dell'utente sul giudizio
LLM, con **R57** e **R58**.)*

**Il difetto.** Ogni stampa di avanzamento usava `print()`, e `run_audit`
scriveva il referto sullo stesso canale quando mancava `--output`: dato e
diagnostica su `stdout`. Riprodotto contro un sito servito in locale —
`mars_audit.py URL --format json > referto.json` esce con **0**, e il file
comincia con «Avvio scansione MARS Beacon su: …»: `json.loads` muore su
`Expecting value: line 1 column 1`, e `stderr` è vuoto.

**La decisione che il TO-DO lasciava aperta non esisteva.** La voce chiedeva se
`mars_citations.py` fosse una seconda voce, «altre 8 stampe con lo stesso
problema». Misurato sull'AST dei sorgenti: sono otto, ma **sette dichiarano già
`file=sys.stderr`** e l'ottava è il referto. Lì il difetto non c'era — ed è lo
stesso file che il principio 7 indica come stile di riferimento. Un test lo
tiene vero, perché una stampa aggiunta senza `file=` lo ricreerebbe.

Il censimento vero, sempre dall'AST:

| File | `print()` | su `stdout` prima | dopo |
|---|---|---|---|
| `mars_audit.py` | 14 | 14 | 0 (più il referto, con `sys.stdout.write`) |
| `mars_core.py` | 5 | 5 | 0 |
| `mars_wapt.py` | 2 | 2 | 0 |
| `mars_llm_judge.py` | 1 | 1 | 0 |
| `mars_citations.py` | 8 | 1, ed è il referto | invariato |
| `mars_api.py` | 3 | 3 | invariato |

**`mars_api.py` è fuori di proposito**, e non per dimenticanza: non scrive mai
un referto su `stdout` — il dato esce dalla risposta HTTP — quindi le sue tre
stampe non possono mescolarsi ad alcun dato. Il difetto è la **convivenza** dei
due sul canale, non il canale in sé.

**Soluzione.** Ogni `print()` dei quattro file porta `file=sys.stderr`; il
referto esce con `sys.stdout.write(testo + "\n")`. Non è cosmesi: dichiarare il
dato con un gesto diverso dalla diagnostica lascia l'invariante «ogni `print()`
di questi file va su `stderr`» **senza un'eccezione da ricordare**, ed era
proprio l'eccezione dimenticata a produrre il difetto. La sostituzione è stata
fatta sulle posizioni dell'AST e non a mano — con le colonne lette in **byte**
UTF-8, che è ciò che l'AST usa: tagliare per caratteri sposta il punto di
innesto su ogni riga con un accento o una ⚠.

**Effetto collaterale dichiarato:** con `--output`, `stdout` è ora **vuoto** —
«Referto scritto in …» è diagnostica. Chi rediriga `stdout` di un audit con
`--output` trova un file vuoto dove prima trovava quella riga. È la stessa
convenzione che `mars_citations.py` applica dal principio.

**Prove.**

- End-to-end contro un sito servito in locale, tre formati: `stdout` comincia
  con `{`, con il BOM del CSV e con `#`; `stderr` porta «Avvio scansione…»; il
  JSON si rilegge (9 aree, complessivo 58.6). Prima: uscita 0 e
  `JSONDecodeError` sulla prima colonna.
- Cinque test nuovi in `tests/test_cli.py`: i tre formati che non portano
  diagnostica su `stdout` (per `json`, `json.loads` sul canale intero), un
  **invariante sull'AST** dei quattro file, e la misura su `mars_citations.py`.
- Quattro test esistenti ora leggono `stderr` invece di `stdout`, ed è la
  prova visibile del cambiamento. Uno di essi —
  `test_la_cli_rilegge_lo_storico_e_produce_il_delta` — ha smesso di
  **ritagliare il JSON fra la prima graffa e l'ultima**: era il rattoppo che il
  difetto imponeva. I tre test di R22 continuano invece a leggere `stdout` e
  restano verdi: l'errore del modulo è nel referto, non solo nella stampa.
- Quattro mutazioni, tutte colte: una stampa di `mars_audit` su `stdout` → 5
  rossi; una stampa di `mars_wapt` su `stdout` → 1, **e solo l'invariante**,
  che è la ragione per cui esiste (nessun test esercita quel ripiego); il
  referto su `stderr` → 8; il rilevatore dei `print` neutralizzato → 1, quindi
  non è un controllo morto.
- `pytest` **1138 passed**, `flake8 .` a zero.

### R58 — ✅ (2026-08-27): l'annuncio della spesa, e un presidio che non presidiava

*(nata dalla stessa indagine di **R57**: l'utente ha visto annunciare un invio
che non è mai partito.)*

**Il difetto.** `mars_llm_judge` stampava «Giudizio LLM: invio N passaggi (~M
token stimati) a claude-opus-5…» anche quando nessuna credenziale esisteva, e
la richiesta moriva subito dopo. Il referto diceva poi «non misurato», ma chi
guardava il terminale aveva già letto un invio.

**Causa radice.** Il presidio era il `try` intorno alla costruzione del client,
col commento «senza credenziali risolvibili l'SDK solleva TypeError». Falso
sull'SDK **0.122.0**: `anthropic.Anthropic()` **non valida alla costruzione** —
riesce sempre — e risolve la credenziale al momento della richiesta, dentro
`_validate_headers`. Quel `try` non intercettava nulla, e il ramo
`no_credentials` con `stage="client"` era **irraggiungibile con l'SDK vero**:
lo raggiungeva solo un test che faceva sollevare `Anthropic` a mano.

**La misura che ha dettato la soluzione.** Non basta `bool(client.api_key)`,
che il TO-DO proponeva: la docstring di `Anthropic.__init__` elenca cinque vie
di risoluzione, e il profilo `ant auth login` finisce in `client.credentials`,
non in `api_key`. Con la sola `api_key` un utente autenticato per profilo — il
caso che il README promette a `--llm on` — si sarebbe visto rifiutare l'invio.
Le fonti che l'SDK stesso guarda prima di firmare sono **tre**, e la condizione
è copiata da lì:

| Fonte | Da dove viene | Dove finisce sul client |
|---|---|---|
| `api_key` | `--credentials`, corpo API, `ANTHROPIC_API_KEY` | `client.api_key` |
| `auth_token` | `ANTHROPIC_AUTH_TOKEN` | `client.auth_token` |
| fornitore di token | `ANTHROPIC_PROFILE`, profilo attivo su disco (`ant auth login`), federazione | `client.credentials` |

**Soluzione.** `credenziale_risolta(client)` in
[mars_llm_judge.py](mars_llm_judge.py), chiamata **dopo** la costruzione e
**prima** dell'annuncio: se le tre fonti sono tutte vuote si esce con
`llm.status.no_credentials`, `stage="client"`, `attempted: False`. Il `try`
resta — un'altra versione dell'SDK, o argomenti incoerenti, possono ancora
sollevare — ed è lo stesso fatto visto in un altro momento, con la stessa
chiave. Un oggetto che non espone **nessuna** delle tre non è un client
dell'SDK: è quello iniettato dai test, su cui non si può affermare nulla, e
vale usabile — senza questa clausola ogni test col client finto direbbe
«nessuna credenziale».

**Prove.**

- Confronto end-to-end con l'SDK reale e nessuna credenziale nel processo,
  stesso contesto sulle due versioni: prima `stdout` = «Giudizio LLM: invio 1
  passaggi (~42 token stimati)…» con `stage=request` e `attempted=True`; dopo
  `stdout` vuoto, `stage=client`, `attempted=False`. Nessuna richiesta di rete
  in entrambi i casi: l'SDK solleva prima di aprire il socket.
- Tre test nuovi in `tests/test_modules.py`: l'annuncio che non si stampa e il
  ramo `stage="client"` finalmente raggiungibile; il contratto dell'SDK fissato
  con `anthropic.Anthropic(api_key="")` — argomento esplicito **apposta**, così
  l'SDK non consulta né ambiente né disco e il test dice la stessa cosa su un
  clone appena fatto; il profilo `ant auth login` che non va scambiato per
  assenza.
- Cinque mutazioni, tutte colte, nessuna sfuggita: controllo assente (il
  difetto tale e quale) → 1 rosso; controllo sempre «usabile» → 2; client senza
  le tre fonti dichiarato inutilizzabile → 19; **la correzione ingenua alla
  sola `api_key`** → 1, ed è il test del profilo; controllo dopo l'annuncio
  invece che prima → 1.
- `pytest` **1133 passed**, `flake8 .` a zero. Golden invariati: il client
  iniettato non espone le tre fonti, quindi il percorso del golden non cambia.

### R57 — ✅ (2026-08-27): le chiavi dalla riga di comando, e un `main()` che si esegue
*(nata da un'esecuzione reale dell'utente sul giudizio LLM. Apre **R58** e
**R59**, trovate nella stessa indagine.)*

**Il fatto che ha aperto la voce.** L'utente ha lanciato un audit convinto che
`ANTHROPIC_API_KEY` fosse nell'ambiente; la CLI ha annunciato «invio 8 passaggi
(~2121 token stimati) a claude-opus-5…» e il referto ha poi detto **«9. Giudizio
LLM — non misurato — Nessuna credenziale Anthropic utilizzabile»**. Nulla è
partito, nulla è stato speso, e **C4 resta non verificata**.

**La diagnosi si regge su una distinzione verificabile**, che il codice già
faceva e che nessuno aveva mai letto in coppia:

| Cosa succede | Eccezione | Che cosa scrive il referto |
|---|---|---|
| Nessuna credenziale **risolta** | `TypeError: Could not resolve authentication method` | «Nessuna credenziale Anthropic utilizzabile» |
| Credenziale risolta e **rifiutata** | `AuthenticationError` (401) | «Errore API Anthropic: AuthenticationError» |

Il referto diceva la prima, quindi in quel processo non c'era **nessun** valore
— non un valore cattivo. Verificato su SDK 0.122.0: un valore non vuoto ma
insensato non produce `TypeError`, va in rete e fallisce là.

**E `python-dotenv` non c'entra**: l'utente l'aveva installato (1.2.3 nel
`.venv`), ma **nessun file del progetto chiama `load_dotenv()`** — zero
occorrenze. Installare il pacchetto non fa leggere `.env` a nessuno, e la
libreria non sta in alcun `requirements*.txt`.

**La decisione dell'utente:** niente `.env`, le chiavi si passano
esplicitamente — via API, che già le accetta, o da riga di comando, che **non
aveva alcun parametro**. L'unica via era l'ambiente, ed è la fragilità che ha
prodotto l'incidente.

**La forma, scelta fra quattro con una misura davanti.** `--credentials FILE`,
JSON, con le stesse chiavi del corpo API — accetta sia il solo blocco sia il
corpo intero, così chi copia `examples/audit_request.json` non riscrive nulla.
È il principio 4. **Un file e non un valore sul flag**, e la ragione è misurata
su questa macchina: `/proc` è montato **senza `hidepid`** e
`/proc/<pid>/cmdline` è `-r--r--r--`, quindi una chiave passata come argomento è
leggibile da **ogni utente locale** per tutta la durata dell'audit, e finisce
integra in `~/.bash_history`.

**Lettura severa, per la stessa ragione che ha aperto la voce.** Un file
passato e ignorato in silenzio fa credere di aver misurato con la propria
chiave — è la lezione di R31 sulle query. Fermano l'audit con codice 2: file
assente, JSON non valido, nessuna credenziale nota, valore che non è una
stringa. Non lo fermano ma si dichiarano: una chiave scritta male, nominata per
nome — `antropic_api_key` senza la h disabiliterebbe l'area 9 senza un errore —
e un file leggibile da altri utenti. **Un valore rotto annulla anche le altre
chiavi**: proseguire con metà delle credenziali, senza dire quale metà, è
peggio che fermarsi. Nessun messaggio contiene mai il valore di una chiave.

**Una motivazione mia, scritta e poi smentita.** Avevo commentato che si usa
`exc.msg` e non `exc` perché il testo di `JSONDecodeError` «cita la riga del
documento, e quella riga può essere la chiave». **Falso**, verificato:
`str(JSONDecodeError)` dà «Expecting value: line 1 column 23 (char 22)» e non
riporta il documento. Il commento ora dice la cosa vera — non c'è nulla da
oscurare, si scompone solo per comporre la frase in italiano — ed è per questo
che la mutazione su quella riga **resta verde a ragione**: non c'è niente da
presidiare.

**`main()` è ora una funzione.** Il punto d'ingresso stava in un blocco
`if __name__ == "__main__"`, che nessun test può eseguire: due mutazioni ci
sono sopravvissute — togliere la propagazione delle credenziali, e togliere
l'uscita su un file illeggibile — perché il codice fra argparse e `run_audit`
era fuori portata. La guardia statica di R56 non bastava: dice che un
parametro è **letto**, non che serva a qualcosa. Ora `main(argv)` restituisce
il codice di uscita e tre test lo eseguono davvero.

**Verifiche.** `flake8` 0, `pytest` **1130** (erano 1115). Tredici mutazioni,
tutte rosse **senza** `tests/test_golden.py` tranne quella cosmetica di cui
sopra. **Cinque erano passate al primo giro**, e quattro appartengono alla
stessa famiglia già vista in R56: il codice che nessun test esegue.

**End-to-end contro l'API vera**, con una chiave **finta** in un file e
`ANTHROPIC_API_KEY` tolta dall'ambiente: `--llm auto` è passato — quindi la
chiave del file è stata vista — la richiesta è arrivata ad Anthropic, ed è
tornata `AuthenticationError`. Il referto dice «Errore API Anthropic:
AuthenticationError», cioè **l'altro** messaggio della tabella qui sopra, e la
chiave finta non compare in nessun punto del referto. La catena
`--credentials` → `context` → `mars_llm_judge` → SDK è quindi provata per
intero. Verificati anche i codici di uscita: **2** su file assente e su file
senza chiavi note.

### R56 — ✅ (2026-08-27): `--max-children`, e un perimetro dichiarato inesatto
*(chiude la catena R40 → R53 → R54, e la coppia R55 → R56 nata dal controllo
su `--max-pages`. **Nessuna correzione resta aperta.**)*

**Metà del problema era sparita da sé.** R55 ha reso il perimetro dell'area 7
uguale al campione del crawler quando la proprietà non è dichiarata: lì
`--max-pages` vincola l'area 7 come le altre otto. Restava la via del
proprietario, dove lo spider percorre il sito per conto suo — misurato, con
`--max-pages 2` ha toccato **nove** URL, fermandosi al `MaxDepth` di ZAP e non
a un limite nostro.

**La decisione dell'utente, e la sua ragione:** dichiarare il limite invece di
fingerlo esatto — «se è il proprietario a lanciarlo non è importante avere un
limite rigoroso». È la stessa scelta di onestà metodologica del principio 5: un
tetto approssimato spacciato per tetto sarebbe un numero inventato.

**`--max-children`**, nuovo, dalla CLI all'API fino al `context`. È **l'unico**
tetto che l'API dello spider accetta — `spider/action/scan` prende
`url maxChildren recurse contextName subtreeOnly`, verificato sul daemon — e
**non è un numero di pagine**. Misurato su un indice con otto figli:

| `--max-children` | pagine percorse |
|---|---|
| 0 (predefinito, il default di ZAP) | **8**, tutte |
| 2 | **1** |

Con 2 se ne percorre **una**, non due, perché `robots.txt` e `sitemap.xml`
contano anch'essi come figli. È esattamente il motivo per cui il referto non
può chiamarlo tetto di pagine, e la misura vale più della spiegazione.

**Il perimetro si dichiara.** Sulla via dello spider `pages_tested` resta
`None` — MARS il numero non lo conosce — ma tacere lascerebbe credere che valga
`--max-pages` come per le altre otto aree. Il rilievo `sec.status.spider_scope`
dice i due limiti che agiscono davvero: il nostro per **nodo** e il `MaxDepth`
del daemon, **letto** e non supposto. Cablare il 5 predefinito direbbe il falso
a chi il proprio ZAP l'ha configurato, e una mutazione lo dimostra.

**Verifiche.** `flake8` 0, `pytest` **1115** (erano 1105). Nove mutazioni,
tutte rosse **senza** `tests/test_golden.py` — ma **quattro erano passate al
primo giro**, e sono tutte della stessa famiglia: **la tubatura**. Il valore ha
una strada sola e lunga — argparse → `run_audit` → `build_context` → `context`
→ `mars_wapt` → `ZapClient` → richiesta HTTP — e ogni anello rotto è
silenzioso: lo spider gira lo stesso, senza tetto, e non c'è alcun errore.
Erano scoperti l'anello del `context`, quello dell'API, quello della richiesta
HTTP (i finti registrano la chiamata Python, non i parametri che partono) e
quello del punto d'ingresso.

**L'ultimo ha prodotto la guardia più utile.** Il blocco
`if __name__ == "__main__"` **non è una funzione**, quindi nessun test lo
esegue: un `args.<qualcosa>` dimenticato lì è invisibile per **ogni** flag, non
solo per questo — il parametro si accetta dalla riga di comando, non fa nulla, e
non c'è errore. Ora un test statico confronta i `dest` del parser con ciò che il
blocco legge davvero, come già si fa con `ast` per il `k` della fusione RRF:
guarda il **codice**, non il dato, e copre tutti i parametri insieme.

I golden **non si muovono**: vi si gira senza dichiarazione di proprietà, quindi
la via dello spider non è esercitata. Per la stessa ragione il caso è stato
aggiunto al banco dell'i18n — una chiave nuova con un segnaposto e senza un caso
che lo accenda diventa rossa il giorno in cui nasce, ed è successo.

### R55 — ✅ (2026-08-27): lo spider di ZAP non rispettava robots.txt
*(nata da un sospetto dell'utente — «credo che ZAP ignori `--max-pages`» — che
era fondato, e la cui indagine ha trovato accanto questa, più grave.)*

**La promessa rotta.** [.claude/sicurezza.md](.claude/sicurezza.md) dichiara che
il crawler rispetta robots.txt e che l'unico modo per ignorarlo è la
dichiarazione di proprietà del dominio. Valeva per il crawler di `mars_core`.
**Non valeva per lo spider che `mars_wapt` avviava** a ogni audit in cui un
daemon ZAP rispondeva — senza flag, senza dichiarazione, senza che il referto lo
dicesse. È GRAVE non perché sbagli un numero, ma perché faceva fare a MARS,
verso siti di terzi, esattamente ciò che MARS dichiara di non fare.

**Misurato su ZAP 2.17.0, e il meccanismo isolato.** Con un `robots.txt` che
vietava `/p02.html` e `/p03.html`, ZAP le ha richieste entrambe. Poi il caso
decisivo: una pagina `/segreta.html` **collegata da nessuna pagina**, presente
solo come `Disallow`, **è stata richiesta lo stesso**. Lo spider usa le voci
`Disallow` come **semi** da cui partire — robots.txt lo fa quindi scansionare
*di più*, e proprio dove il sito chiede di non andare.

**Non è una riga di configurazione.** Delle ventiquattro opzioni dello spider
l'unica che nomina robots è `optionParseRobotsTxt`, che governa il *leggerlo per
trovare URL*, non l'obbedirgli. Un'opzione per obbedire **non esiste**.

**La decisione, e la misura che ha corretto la mia proposta.** L'utente ha
scelto fra tre strade: *lo spider solo con `--i-own-this-domain`*. Nella tabella
del TO-DO avevo però scritto che senza dichiarazione l'area 7 sarebbe diventata
il solo ripiego sugli header — un'assunzione **mia**, non una misura, e la
misura l'ha smentita. Confronto su sito locale:

| | Alert | **Regole distinte** | URL toccati | Tocca la vietata | Punteggio |
|---|---|---|---|---|---|
| Spider, com'era | 34 | **5** | 9 | **sì** | 54 |
| Solo il campione del crawler | 8 | **4** | 2 | no | 69 |
| Niente spider e nient'altro | 0 | 0 | 0 | no | **100** |

Le regole sono il numero che conta, non gli alert: in MARS **un rilievo è un
controllo, non un'occorrenza**. E l'ultima riga è la trappola:
`score_from_alerts([])` vale **100**, quindi togliere lo spider e non mettere
nulla al suo posto avrebbe fatto dire al referto «ZAP passiva, 100/100» di un
sito mai guardato — esattamente ciò contro cui la docstring di `audit_headers`
mette in guardia. Rimessa la scelta all'utente con i numeri, ha scelto la
seconda riga.

**La soluzione.** `run_zap` ha due perimetri. Senza dichiarazione nessuno spider
parte: ZAP riceve le pagine che il crawler ha già scaricato — conformi a
robots.txt per costruzione — con `core/action/accessUrl`, e se ne ricavano i
soli alert passivi. **Non una sola richiesta in più** verso il sito rispetto a
quelle già fatte. Con dichiarazione tornano spider e active scan: sono due cose
che il sito non ha autorizzato, e la dichiarazione è ciò che le rende lecite —
da qui in avanti il gate è **lo stesso** per entrambe.

**Una cosa che si sarebbe persa in silenzio:** gli alert passivi non sono pronti
quando l'ultima richiesta è finita, perché ZAP li produce leggendo una coda.
Senza attenderla (`pscan/view/recordsToScan`) se ne perde una parte, e **quanta
dipende dalla velocità della macchina** — cioè un referto che cambia da
un'esecuzione all'altra senza che nulla lo dichiari. Il timeout vale anche qui,
e `fermate` resta True: non c'è nulla da fermare, la passiva legge traffico già
avvenuto.

**Seconda casella: il perimetro si dichiara.** `mars_wapt` non pubblicava
`pages_tested`, quindi taceva sul proprio campione mentre il referto in testa
scrive `pages_crawled` e chi legge lo riferisce a tutte le aree. Ora lo
pubblica sulla via senza spider, dove il numero è **esatto**, e resta `None` su
quella con lo spider, dove MARS non lo conosce: dichiarare un campione sbagliato
è peggio che tacerlo. La issue e il rilievo `sec.status.passive_only` dicono ora
il perimetro e portano gli URL in `params`.

**Verifica end-to-end su ZAP vero**, non sui finti — che qui non basterebbero,
perché la domanda è che cosa MARS dice al daemon:

- **senza** dichiarazione, `mars_audit.py` su un sito con `/p02.html` vietata:
  ZAP ha toccato **due** URL, il campione esatto, e **non** la pagina vietata.
  Area 7 a 69 con `pages_tested: 2`. Prima della correzione, stessa esecuzione:
  **nove** URL, vietata compresa;
- **con** dichiarazione: spider di nuovo a nove URL, `tool: "ZAP (attiva)"`,
  `pages_tested: None`.

**Verifiche.** `flake8` 0, `pytest` **1105** (erano 1096). Otto mutazioni, tutte
rosse **senza** `tests/test_golden.py` — ma **tre erano passate al primo giro**,
e sono l'unica parte del controllo che ha insegnato qualcosa:

1. invertire il confronto dell'attesa (`<= 0` in `>= 0`) non si vedeva, perché
   il daemon finto rispondeva sempre `0` e le due forme coincidevano: il finto
   ora svuota la coda a poco a poco, come ZAP;
2. togliere il ripiego `or [url]` dal perimetro faceva dichiarare «**0** pagine
   scansionate» mentre ZAP l'URL di partenza l'aveva comunque guardato — zero è
   un numero, e un numero sbagliato è peggio di nessun numero;
3. togliere `%(pages)d` dal titolo inglese lasciava verde tutto: i test di
   parità i18n controllano che una chiave sia **tradotta**, non che la
   traduzione dica la stessa cosa.

Golden rigenerati e diff riletto: i punteggi **non si muovono** — nel golden
`run_zap` è sostituito, quindi gli alert sono gli stessi — e cambiano solo il
testo della issue, i suoi `params` e `pages_tested`.

### R54 — ✅ (2026-08-27): il parametro inerte nascondeva un audit assente
*(l'ultima delle tre osservazioni di R40, e la catena R40 → R53 → R54 si chiude
qui. **Nessuna correzione resta aperta.**)*

**Il difetto era più grande della voce, e il parametro inerte era il sintomo.**
`severita_lighthouse(score, mode, weight)` non leggeva `score`: decideva su modo
e peso. Il TO-DO offriva due strade — introdurre `SEV_OK`, oppure togliere il
parametro dalla firma dichiarando che la gravita' dal punteggio non dipende — e
**nessuna delle due era giusta**, perché entrambe partivano dal presupposto che
`score` non avesse nulla da dire.

**Che cosa nasconde l'inerzia, misurato prima di toccare il codice.** Un
`auditRef` che la categoria elenca e il cui `id` **non compare** fra gli
`audits` produce una voce vuota: `score: None`, `scoreDisplayMode: None`, ma il
`weight` viene dal ref ed è intero. Quel modo non entra in
`LH_MODI_NON_MISURATI`, quindi decideva il solo peso, e `is-crawlable` — 93/23,
l'unico audit SEO sopra la soglia, calibrato da Lighthouse perché il suo solo
fallimento faccia fallire la categoria — usciva:

- `severity: "critical"`, il grado più alto di MARS;
- `title: "is-crawlable"`, lo slug grezzo, perché il titolo ripiega su
  `ref.get("id")`;
- contato fra i **falliti**.

Un difetto grave del sito, annunciato da un identificatore, su un controllo che
Lighthouse non ha mai riportato. È la stessa classe che R53 aveva chiuso per
`error`, sopravvissuta in un ramo che nessun modo copre. Non è teorico: è lo
stesso caso che la docstring di `_penalita` dichiara reale, ed è il motivo per
cui **li'** lo score si controlla già con `isinstance`. La classificazione non
lo faceva.

**La decisione: il punteggio è la guardia più forte del modo**, e per
costruzione. `_normalizeAuditScore` (`core/audits/audit.js`) restituisce `null`
per ogni modo non misurato e un numero finito per ogni modo misurato — o
solleva, e allora l'audit finisce in `error`, che è di nuovo `null`. Quindi
«score non numerico» equivale a «non misurato», **sempre**, e vale anche dove il
modo manca o non si riconosce. Il parametro diventa significativo senza
`SEV_OK`: la fase che rendera' i controlli superati parte del referto resta da
fare, ma non era questa a bloccare.

**Servono entrambe le metà**, e l'`informative` è la ragione: ha `score: 1`,
quindi numerico, e lo riconosce solo il modo. Una mutazione che lascia la sola
guardia sullo score lo rimanda fra i superati.

**Il titolo.** Con la voce classificata non misurata, `PREFISSO_NON_MISURATO`
non aveva una riga per il modo assente e il rilievo si presentava ancora col
solo slug. Una riga in più — «Controllo assente dal referto di Lighthouse» — e
la tabella copre ora i quattro modi **più** il caso senza modo; il test che
teneva allineate tupla e tabella dice adesso questo.

**Verifiche.** `flake8` 0, `pytest` 1096 (erano 1094). Sei mutazioni, tutte
rosse **senza** `tests/test_golden.py`. Una era passata al primo giro:
sostituire `isinstance(score, (int, float))` con `score is None`. La differenza
si misura — il LHR arriva da un sottoprocesso, quindi è dato esterno, e un
`"score": "0"` non è un punteggio — e ora due asserzioni la fissano.

**I golden non si sono mossi di una riga, ed è il risultato atteso:** nessun
LHR ben formato ha un audit assente, quindi la correzione è inerte su ogni
referto vero. Per la stessa ragione **non è stata rieseguita end-to-end**: il
caso che cambia non si può produrre con un Lighthouse reale, e su input valido
i golden — che congelano la pipeline intera — dimostrano già che nulla si
muove.

### R53 — ✅ (2026-08-27): i conteggi di `mars_seo`, e i tre testi che si buttavano via
*(due caselle su tre. La terza — il parametro `score` inerte di
`severita_lighthouse` — prosegue in **R54**: non è un difetto da correggere ma
una decisione che aspetta `SEV_OK`.)*

**Casella 1 — la metà che R40 aveva lasciato aperta.** `mars_seo` aveva una
tupla sua, `MODI_NON_MISURATI_VOCE = ("manual", "notApplicable")`, contro i
quattro modi di `LH_MODI_NON_MISURATI` in `mars_core`. Due risposte alla stessa
domanda — «Lighthouse ha misurato?» — che si erano già separate. I due modi che
restavano fuori finivano nelle classi sbagliate:

- **`informative` fra i superati.** `_normalizeAuditScore`
  (`core/audits/audit.js`) esce con **1** su `informative`, e lo fa nel **primo
  ramo**, prima del controllo su binary/numeric/metricSavings. Il commento di
  `estrai_audit` citava quel controllo e ometteva il ramo che lo precede,
  quindi documentava il contrario di ciò che il codice faceva.
- **`error` fra i falliti.** Un guasto dello strumento contato come difetto del
  sito, cioè la stessa affermazione falsa che R40 aveva tolto dal **testo** e
  lasciato nei **conteggi**.

**La misura che ha ridimensionato la voce.** Il TO-DO dichiarava a rischio i
conteggi `passed`/`failed`/`manual` restituiti da `riassumi`: **non li legge
nessuno.** La serializzazione d'area di `mars_report` è una whitelist e non li
comprende, quindi non arrivano nel JSON; la riga «N superati, M falliti» se li
ricalcola da `audits`. Li leggevano tre test. Metà del rischio dichiarato non
esisteva.

E l'altra metà è più piccola di quanto sembrasse: **`informative` non può
capitare nella categoria SEO.** Verificato audit per audit sui sorgenti di
Lighthouse 13.4.1 — nessuno degli undici lo produce, né nel `meta` né a
runtime. Quel ramo è una guardia, non una correzione, e il test lo dichiara.
Resta `error`, che capita a qualunque audit il cui gatherer sollevi. Sui due
golden lo spostamento è **zero**: nessuno dei due dataset ha un audit in
errore, e l'unica riga che si muove è `schema_version`.

**Perché il bump si pagava comunque.** `audits[].manual` è nel JSON pubblico, e
il README dice che `schema_version` sale anche quando **il significato di una
chiave cambia** — non solo quando è rinominata. Allargare `manual` è
precisamente questo. Decisione presa dall'utente fra tre alternative:
**allargare la chiave, non rinominarla**. Il nome resta imperfetto — `manual`
non ha mai significato «da fare a mano», perché `notApplicable` c'è sempre
stato — ma rinominare avrebbe aggiunto un secondo cambiamento incompatibile per
un guadagno di sola lettura, mentre il referto il modo lo dice già in parole
(`PREFISSO_NON_MISURATO`). `JSON_SCHEMA_VERSION` a **3**; `__version__` resta
2.9.0, come in R47: sono due versioni indipendenti, e il README lo dichiara.

**Una cosa che sarebbe passata:** le due strutture usavano maiuscole diverse.
`mars_core` tiene la tupla in minuscolo e abbassa prima di confrontare;
`mars_seo` confrontava la forma grezza e aveva le chiavi dei prefissi in
camelCase. Unificando senza abbassare, `notApplicable` sarebbe uscito
**misurato** — cioè un difetto nuovo introdotto dalla correzione. Un test copre
il caso, e un altro verifica che tupla e tabella dei prefissi coprano gli
stessi modi: un modo ammesso dall'una e assente dall'altra tornerebbe a portare
il titolo del **successo**, che è il difetto che R40 aveva corretto.

**Casella 2 — `explanation`, `displayValue` e `warnings`.** Verificato che
erano ignorati: zero occorrenze. Sono i testi che dicono perché **quel**
controllo è andato così, mentre la `description` — già il `detail` — dice
perché il controllo conta. Due cose diverse, quindi params separati e non
`detail`.

**Vanno nella VOCE, non solo nel rilievo**, ed è la decisione che conta: un
audit **superato** non produce alcun rilievo (scelta di R40, altrimenti un sito
perfetto mostrerebbe nove voci da fare), e `warnings` è proprio di un audit che
passa — `is-crawlable` passa quando almeno un bot è ammesso, e nel `warnings`
elenca **quali sono bloccati**. Per un progetto che misura i crawler IA è
l'avviso più rilevante dei tre, e se quei testi fossero vissuti solo nei
rilievi non avrebbe avuto dove andare.

Sei degli undici audit ne portano almeno uno. Il caso che pesa è
`meta-description`: fallisce **senza** `details.items`, quindi il suo rilievo
era il solo titolo generico e la sua riga di dettaglio nell'HTML **non esisteva
affatto**. Ora dice «Il testo della descrizione è vuoto.»

**Verificato contro Lighthouse vero, non contro la fixture.** Alla prima
esecuzione su un sito locale l'`explanation` non compariva: quel testo esce
solo quando la meta descrizione **c'è ed è vuota** (`content=""`), non quando
manca. Rifatta la pagina, Lighthouse 13.4.1 ha prodotto esattamente la
combinazione della fixture — score 0, titolo «Il documento non ha una meta
descrizione», explanation «Il testo della descrizione è vuoto.» — e il referto
end-to-end la porta fino all'HTML. Un limite misurato e dichiarato: il
`warnings` di `is-crawlable` **non è nel locale italiano** di Lighthouse 13.4.1
e arriva in inglese anche con `--locale it`; `params["text_lang"]` lo dichiara
già.

**Un effetto collaterale utile:** `displayValue` rende visibile il troncamento
di R46. La riga di `link-text` diceva cinque elementi; ora dice «8 link trovati
— /p0, /p1, /p2, /p3, /p4».

**Verifiche.** `flake8` 0, `pytest` 1094. Dodici mutazioni, tutte rosse. Ma il
giro rifatto **senza** `tests/test_golden.py` ne ha lasciate passare due, ed è
l'unica parte del controllo che ha insegnato qualcosa: togliere `displayValue`
ed `explanation` dalla resa HTML lasciava verde tutto tranne i golden — un
guardiano che vive solo nei golden si perde alla prima rigenerazione fatta per
far tornare il verde, e ora c'è un test suo. L'altra è `JSON_SCHEMA_VERSION`
stessa, e lì il golden è il guardiano giusto: un test che asserisse «3»
ripeterebbe la costante.

### R48 — ✅ CHIUSA (2026-08-26): dal JavaScript esce anche la geometria
*(la seconda metà. La prima — la disposizione ad anelli — è nella voce
«R48 — RIDOTTO» più sotto, e resta il racconto di come la voce si era
rimpicciolita)*

**Che cosa restava.** Dopo il primo passo il JavaScript non calcolava più il
layout ad anelli, ma `ridisegna()` ricalcolava a ogni cambio di vista le due
estremità di **ogni arco** — radice quadrata compresa — e la posizione di ogni
etichetta; `evidenzia()` scandiva **tutti** gli archi a ogni passaggio del
puntatore per trovare i vicini di un nodo. Aritmetica che nessun test eseguiva.

**Perché era precalcolabile, e non un'ottimizzazione.** Le viste sono **due e
note**: il layout a forze, che sta già negli attributi `x1..y2`, e quello ad
anelli, che Python calcola dal primo passo. Il vicinato non dipende dal gesto:
è una proprietà del grafo. Nessuna delle tre cose dipende da che cosa
l'utente fa, quindi nessuna ha ragione di stare in uno script.

Ora ogni arco porta anche `data-a` — quattro coordinate in un attributo solo —
ogni etichetta `data-ax`/`data-ay`, e ogni nodo `data-v` (i vicini, sé stesso
compreso) e `data-e` (gli archi che lo toccano). `anelli()`, `forze()` ed
`evidenzia()` applicano attributi; `Math.sqrt` è uscito dallo script, e un test
lo presidia.

**Tre funzioni nuove in `mars_report`, tutte pure**: `geometria_arco()` — che
la chiamano due volte per arco, una per vista, dove prima la stessa aritmetica
viveva in due linguaggi — e `vicinato()`. Le verifica `pytest` come qualunque
altra funzione.

**Il prezzo misurato smentisce la ricognizione.** Il TO-DO prevedeva 4-5 KB su
un grafo da 60 nodi. Misurato sulla prima stesura: **15,3 KB**, perché la
previsione contava i nodi (60) e non gli archi (180, con quattro numeri
ciascuno). Comprimendo le quattro coordinate in un attributo solo — 32
caratteri per arco invece di 76, come un `viewBox` — il costo scende a **9,2
KB**: 5,8 per gli archi, 3,4 per il vicinato. Resta il doppio del previsto, ed
è dichiarato in [CONTRIBUTING.md](CONTRIBUTING.md) invece di essere lasciato
scoprire.

**Un test asseriva l'opposto, e lo diceva.**
`test_i_nodi_del_grafo_portano_la_posizione_ad_anelli` conteneva
`assert "Math.sqrt" in REFERTO_JS` con la spiegazione «resta: è la lunghezza
dell'arco in `ridisegna`, cioè il gesto, che R48 non porta via». Il gesto non
era: era geometria, e questa metà la porta via.

**Verifiche.** 1083 test verdi (erano 1077), `flake8` a zero, golden HTML
rigenerati e diff riletto. **`tools/banco_grafo.py` rilanciato**: nove
controlli su nove verdi in un browser vero, compresi i due che questa metà
riscrive — «gli archi seguono i nodi» e «si torna esattamente al layout
calcolato in Python». **Otto mutazioni su otto** fanno rosso; **una sfuggiva
alla prima esecuzione**: un vicino elencato due volte, che il golden non può
rivelare perché non ha due pagine che si linkano a vicenda. È il caso vero — un
menu reciproco — e ora ha un test suo.

### R46 — ✅ RISOLTO (2026-08-26): il conteggio delle istanze è canonico, e lo sforzo ci scala

**Il difetto.** `SFORZO` è una mappa `chiave -> minuti|ore|giorni`: dipendeva
dal **tipo** di controllo e non da quante volte il difetto ricorre. «1 immagine
senza `alt`» e «400 immagini senza `alt`» hanno la stessa chiave, quindi lo
stesso sforzo — `giorni` in entrambi i casi, che sul primo è una
sopravvalutazione. Il dato per fare meglio c'era già, ma con un nome **diverso
per area**: `immagini`, `campi`, `pagine`, `nodes`, `n`, scelti da chi ha
scritto il modulo.

**La decisione: un nome canonico accanto a quelli parlanti.** `instances` viene
scritto da ogni modulo insieme al nome parlante, che resta perché lo usano i
template di traduzione. L'alternativa — una mappa chiave → nome del conteggio
in `mars_remediation` — sarebbe stata un secondo catalogo da tenere allineato a
sei moduli, cioè la forma di divergenza silenziosa che questo progetto ha già
pagato più volte.

**Il numero si scrive una volta sola.** Gli imbuti dei moduli prendono una
**coppia** `istanze=(nome parlante, conteggio)` e scrivono entrambi i nomi:
`_rilievo(..., istanze=("pagine", len(noindex)))`. Due argomenti separati
avrebbero significato assegnare lo stesso valore due volte allo stesso punto di
chiamata, e due assegnazioni dello stesso valore prima o poi divergono.

**L'assenza è un significato**, come per `params["urls"]` di R47: dice che il
difetto **non ricorre**. `robots.txt` manca una volta sola; «nessun JSON-LD sul
sito» è un fatto unico, non un'occorrenza — dichiarargli `instances: 1` lo
farebbe scendere di un gradino insieme alle immagini singole, che è il
contrario del vero. `mars_schema` lo omette esplicitamente con `ricorre=False`.

**Che cosa conta come istanza, area per area**, e non è ovvio:

- **axe**: i **nodi**, non le pagine. Sono gli elementi da correggere;
- **Lighthouse**: il conteggio **vero** degli item, letto prima del troncamento
  a `MAX_ELEMENTI`. `items` è la vista — cinque su otto — e far scalare una
  stima su una scelta di impaginazione sarebbe assurdo;
- **ZAP**: gli URL della **variante**, cioè le pagine su cui quell'alert va
  chiuso;
- **`sem.chunks.few` non lo dichiara**: «pochi passaggi» è un difetto che
  cresce quando il numero **scende**, quindi scalarci sopra lo sforzo lo
  invertirebbe.

**Lo sforzo resta una stima, e lo dichiara.** `SFORZO` è ora il livello della
**ricorrenza tipica**, e `GRADINI_ISTANZE` lo muove di un gradino per volta:
una sola occorrenza scende, dieci salgono, cento salgono di due, e la scala si
ferma agli estremi invece di girare. Il referto continua a scrivere `giorni` e
non «3 giorni»: un ordine di grandezza è una stima, un numero sembra una
misura. Le soglie stanno nel piano e non nei sei moduli, perché la scala è una
proprietà del piano e non dell'area che ha misurato.

Le famiglie dinamiche — axe, ZAP, Lighthouse — restano **senza** sforzo anche
con mille occorrenze: un gradino sopra il nulla è ancora il nulla, e inventare
lì un livello che il catalogo non dichiara sarebbe un'assenza travestita da
stima.

**Un lettore solo**: `istanze_del_rilievo()` in `mars_core`, accanto a
`pagine_del_rilievo` e per la stessa ragione. Rifiuta zero, i negativi e i
booleani — `True` in Python **è** un `int` che vale 1, e un booleano scritto
per sbaglio farebbe scendere di un gradino lo sforzo di quel rilievo.

**Verifiche.** 1077 test verdi (erano 1060), `flake8` a zero, golden rigenerati
e diff riletto: cambiano **solo** le righe di sforzo dei difetti a una sola
occorrenza — `1 campi di modulo senza etichetta` passa da `giorni` a `ore`, `1
blocchi JSON-LD malformati` da `ore` a `minuti` — e nessun punteggio si muove.
Il conteggio dei quick win resta invariato. **Dodici mutazioni su dodici** fanno
rosso; **due sfuggivano alla prima esecuzione**, ed entrambe stavano su rami che
i due referti sintetici non accendono: un conteggio a zero o booleano, che da
`_sforzo` si comporta come un conteggio assente, e `sd.jsonld.missing` che
dichiarasse un'istanza — un caso che i golden non hanno, perché entrambi i siti
sintetici il JSON-LD ce l'hanno.

### R40 — ✅ RISOLTO (2026-08-26): tre difetti di `mars_seo`, e uno trovato chiudendoli
*(le tre caselle della voce. I tre rilievi che caselle non erano — la divergenza
fra le due tuple dei modi, i testi `explanation`/`displayValue`/`warnings`, il
parametro inerte di `severita_lighthouse` — proseguono in **R53**)*

**Un solo audit in errore faceva buttare via gli altri dieci.** Lighthouse
azzera il peso degli audit non applicabili, informativi e manuali prima di
scriverlo nel LHR, ma **non** quello di un audit andato in `error`
(`core/scoring.js`): il suo `score: null` sopravvive al filtro e annulla il
punteggio dell'intera categoria. `riassumi` usciva allora al primo `if` **senza
mai chiamare `estrai_audit`**, mentre nel LHR c'erano dieci controlli misurati
perfettamente — dati già pagati col tempo del run.

I due casi ora sono due: non calcolabile *e* nulla da leggere, contro non
calcolabile *ma* dieci audit su undici validi. **Il punteggio resta `None` in
entrambi**: ricavarne uno dagli audit leggibili sarebbe inventare la categoria
che Lighthouse si è rifiutata di calcolare. `audits` è `None` e non una lista
vuota quando non c'è nulla da leggere, perché la scheda d'area mostra l'elenco
dei controlli **al posto** dei rilievi e i due casi si rendono diversamente.

La conseguenza da conoscere: in quel ramo i rilievi portano una `penalty` ma
l'area non ha un punteggio, quindi `certificato_area` dichiara «l'area non ha
un punteggio» e il piano li mette in corsia `ignoto`. È la catena giusta, ed
esisteva già.

**«Da verificare a mano» detto a un `notApplicable` — e a un `error`.**
Lighthouse usa `failureTitle` solo quando `score < 0.9`, quindi un controllo
non misurato porta il titolo del **successo**: la issue di una pagina senza
canonical recitava «da verificare a mano: Il documento ha un elemento
`rel=canonical` valido», che afferma il contrario del vero due volte. U1.7
aveva corretto il titolo del *rilievo* e lasciato la issue, perché cambiarla
era una regressione di testo dentro un commit di sola forma.

Chiudendola è emerso che il difetto era **più largo della voce**: il prefisso
va scelto sul **modo**, non sul flag `manual`, altrimenti un audit in `error` —
che `manual` non è, sta fra i falliti — continua ad annunciarsi col titolo del
successo. Misurato: «[Lighthouse] Il documento ha un `hreflang` valido» per un
gatherer che non era partito.

Cambia **solo il testo**: `MODI_NON_MISURATI_VOCE` resta `("manual",
"notApplicable")` e i conteggi `passed`/`failed`/`manual` non si muovono.
Allargare quella tupla è la decisione che prosegue in R53, e le due metà
vanno tenute distinte — un test le separa esplicitamente.

**Tre buchi in `_descrivi_item`**, tutti verificati sui sorgenti di Lighthouse
13.4.1 in `node_modules` invece che dedotti:

- il `source` che è un **NodeValue** invece di una stringa. È il caso più
  pesante della categoria — `is-crawlable` bloccato da un
  `<meta robots noindex>` — e il ramo cercava `url` e `value`: usciva la
  **stringa vuota** sul difetto più grave che quest'area sappia rilevare. Il
  campo giusto è `snippet`, che `handleMetaElement` sovrascrive proprio col tag
  incriminato; `selector` viene dopo, perché dice dove sta nel DOM e non che
  cosa sia;
- gli item `{index, line, message}` di `robots-txt`, senza né `source` né
  `node`: uscivano tutti vuoti, cioè l'audit diceva «ci sono errori» e nessuno
  di quali. Ora danno riga, contenuto e motivo;
- i `subItems` di `hreflang`, dove sta il **motivo**: senza, restava il tag e
  non si sapeva che cosa avesse di sbagliato — l'unica cosa che serve per
  correggerlo.

**Un imbuto invece di due copie.** Le issues e i rilievi dei controlli si
costruivano dentro `riassumi`, e servivano ora a due rami: sono usciti in
`_issues_dei_controlli` e `_rilievi_dei_controlli`. Due implementazioni della
stessa cosa nello stesso file sono la forma di divergenza che questo progetto
ha già pagato con `direttive_efficaci` (R37).

**Due test riscritti con intenzione.**
`test_seo_un_non_applicabile_non_e_un_manuale` asseriva la riga sbagliata
dichiarando che le issues «restano com'erano — sono la vista congelata»: è la
metà che questa voce chiude. `test_seo_un_audit_in_errore_non_e_un_difetto_del_sito`
fissava la divergenza «perché non la si chiuda per distrazione», e infatti non
si chiude per distrazione: si chiude **metà**, quella del testo, e il test ora
separa le due metà invece di tenerle insieme.

**Verifiche.** 1060 test verdi (erano 1052), `flake8` a zero, golden rigenerati
e diff riletto: **tre righe**, i tre prefissi delle issues non misurate, e
nessun punteggio mosso. **Nove mutazioni su nove** fanno rosso alla prima
esecuzione, fra cui `snippet` scambiato con `selector` — che dà comunque una
stringa non vuota, quindi sarebbe passata a un test che guardasse solo la
lunghezza.

### R39 — ✅ RISOLTO (2026-08-26): `alertRef` non veniva mai raggiunto
*(le caselle 2, 3 e 4 erano già chiuse; questa è la prima, quella che tocca i
punteggi. `__version__` a 2.9.0)*

**Il difetto.** La catena di raggruppamento era
`pluginId or alertRef or name or alert`, ma `pluginId` è **sempre** presente e
non vuoto nel JSON di ZAP (`AlertAPI.alertToSet` lo scrive con
`String.valueOf`): `alertRef` era codice morto. Conseguenza reale: la regola
CSP 10038 emette `10038-1`, `-2` e `-3` — alert distinti, con nome,
spiegazione e **soluzione** propri — che diventavano *una* voce sola, con la
soluzione del primo e le altre perdute. Il campo `params["soluzioni"]` esisteva
proprio per dichiarare quella perdita.

**La decisione: ripartire, non moltiplicare.** Dare a ogni variante il costo
pieno della regola avrebbe fatto perdere il triplo a ogni sito che la viola,
senza che nulla fosse cambiato sul sito: la cardinalità dei gruppi *è* il
punteggio in tutta MARS. La ritaratura è quindi sulla **regola** — penalità
calcolata sull'unione dei suoi URL, con la diffusione di sempre — e la quota è
divisa in parti uguali fra le varianti. Misurato sui golden, con una variante
in più nel dataset apposta per esercitarlo: **`mars_wapt` resta 57 e
`overall` resta 60,1**, identici a prima.

La quota è una **ripartizione, non un recupero misurato**: chiudere una
variante su tre non fa necessariamente risalire il punteggio di un terzo,
perché la diffusione si ricalcolerebbe sull'unione rimasta. È lo stesso motivo
per cui il piano di interventi dichiara `additive: False`, e sta scritto nella
docstring invece di essere lasciato dedurre.

**La ripartizione è auditabile.** `params` porta `variants`, `rule_penalty` e
`rule_n`: `penalty * variants == rule_penalty`, e `rule_penalty` si ricalcola
dalla formula sull'unione degli URL. Un numero del referto vale quanto la
possibilità di rifarne il conto.

**Due rischi convivono, e il dato lo dice.** La gravità del rilievo è quella
che ZAP ha dato a *quella* variante; la penalità viene dalla regola, che ne ha
una sola — il rischio del suo primo alert, criterio di sempre, perché
cambiarlo sposterebbe i punteggi. Quando i due differiscono, `params["risk"]` e
`params["rule_risk"]` stanno accanto: senza, un rilievo `info` che porta una
quota di penalità `High` sarebbe inspiegabile.

**`alertRef` uguale al `pluginId` non è una variante.** ZAP lo valorizza così
per le regole che varianti non ne hanno: lì la chiave **non migra**, e
`params["alert_ref"]` resta vuoto. È ciò che limita la migrazione alle sole
regole che si sono davvero spezzate.

**La migrazione di chiavi si dichiara, perché non si può annullare.**
`sec.zap.10038` → `sec.zap.10038_1`: contro un archivio scritto prima,
`compute_delta` vede una sparizione di massa seguita da una comparsa di massa,
e nessuna delle due è successa sul sito. Tradurre le vecchie chiavi nelle nuove
vorrebbe dire indovinare quale sotto-variante fosse quella archiviata. Il
confronto non si salva, ma si dichiara indebolito: `mars_history` ha ora una
tabella `MIGRAZIONI_CHIAVE` con prefisso, versione e motivo, e `compute_delta`
pubblica `key_migrations` — la stessa scelta di `by_title_fallback` per i
rilievi senza chiave. Le tre viste di prosa lo scrivono.

Tre decisioni piccole dentro quella:

- **una versione precedente illeggibile fa dichiarare la migrazione.** Viene da
  un file scritto da un'altra esecuzione, quindi è dato esterno: non si può
  concludere che l'archivio sia recente guardando una stringa che non si
  capisce. Un caveat di troppo si legge, uno mancante no;
- **`_semver` restituisce `None` e non `(0, 0, 0)`** su ciò che non legge:
  «non l'abbiamo capita» e «è la prima di tutte» sono due fatti diversi, e chi
  confronta sceglie il caso peggiore *sapendolo*. La differenza è osservabile
  solo dal lato della versione corrente, quindi è fissata da un test suo;
- **la versione della migrazione resta nel dato, non nella prosa.** Al
  destinatario del referto non dice nulla di azionabile, e stamparla renderebbe
  indistinguibile una costante dichiarata dalla versione dell'esecuzione — che
  è esattamente ciò che il golden vieta di far comparire.

**Un finto reso fedele.** Il costruttore di alert dei test cablava
`alertRef: "10038-1"` accanto a `pluginId: "10038"`, quindi
`_alert(pluginId="40012")` produceva un alert che ZAP non emetterebbe mai —
l'`alertRef` comincia sempre col `pluginId`. Finché il raggruppamento era per
`pluginId` non si vedeva; da R39 metteva due regole diverse nello stesso gruppo.
Ora l'`alertRef` si deriva dal `pluginId`, ed è la stessa lezione
dell'adattatore HTTP dei test di R16/R17.

**Due test riscritti.** `test_wapt_un_gruppo_con_piu_soluzioni_lo_dichiara`
misurava due `alertRef` dello stesso `pluginId` con soluzioni diverse: è
esattamente il caso che questa voce **chiude**, e il test ora copre quello che
resta vero — lo stesso alert su due URL con soluzioni diverse.
`test_wapt_gli_alert_refs_del_gruppo_non_si_perdono` guardava
`params["alert_refs"]`, l'insieme del gruppo che U1.6 conservava come «il dato
che permetterà di spezzarlo quando lo si vorrà»: il gruppo *è* la variante, il
campo diventa singolare.

**Verifiche.** 1052 test verdi (erano 1039), `flake8` a zero, golden rigenerati
e diff riletto — **nessun punteggio si muove**, cambiano le chiavi, compare un
rilievo e compare il caveat della migrazione. **Dieci mutazioni su dieci** fanno
rosso; **due sfuggivano alla prima esecuzione**, entrambe sul confronto fra
versioni: la migrazione dichiarata anche a due archivi entrambi vecchi, e
`_semver` che restituisse `(0, 0, 0)` invece di `None`. Sono i due rami che in
produzione non si raggiungono, perché la versione corrente è sempre quella del
codice — e `compute_delta` è una funzione pura che chiunque può chiamare con
due righe di storico.

### R51 — ✅ RISOLTO (2026-08-26): il `<meta name="googlebot">` non aveva un agente
*(la metà di R37 che era rimasta aperta)*

**Il difetto.** R37 aveva separato il prefisso per agente dell'`X-Robots-Tag`:
`googlebot: noindex` esclude il solo Google, non gli assistenti, e i due casi
non possono ricevere lo stesso giudizio. Il DOM ha l'equivalente —
`<meta name="googlebot" content="noindex">` — e lì la distinzione non c'era: il
crawler univa i `content` di `robots` e `googlebot` in **una stringa sola**, e
quale meta li portasse era perduto prima di arrivare al modulo.
`direttive_per_agente()` non poteva separarli, e lo dichiarava nella propria
docstring.

Conseguenza misurata su un sito servito in locale: una pagina col solo
`<meta name="googlebot" content="noindex">` produceva `tech.index.noindex`,
gravità **critica**, cioè «il sito è invisibile agli assistenti» — su una
direttiva che agli assistenti non si rivolge affatto.

**Perché non si era chiusa con R37.** Chiuderla vuol dire una chiave nuova
nella pagina prodotta dal crawler, cioè il contratto documentato in
[.claude/contratto-moduli.md](.claude/contratto-moduli.md): sarebbe finita in
un commit che cambiava anche il crawler.

**La soluzione.** `mars_core.estrai_meta_robots(soup)` restituisce
`(globali, {agente: direttive})`; la pagina porta `meta_robots` — d'ora in poi
**solo** i `<meta name="robots">` — e `meta_robots_by_agent`. `mars_tech` legge
la chiave nuova in `direttive_per_agente()` e la tratta come il prefisso
dell'header: `googlebot` non è in `CRAWLER_IA`, quindi il rilievo diventa
`tech.index.agent_only`, di gravità media. Verificato end-to-end: la stessa
pagina passa da un critico inventato a «1/2 pagine con direttive riservate a un
agente che non è un assistente IA (googlebot): noindex».

**Le decisioni, con il loro perché.**

**Il meta non passa dal parser posizionale dell'header, ed è deliberato.**
Nell'`X-Robots-Tag` il prefisso vale *fino al prossimo* perché `requests`
concatena più header in una stringa; nel DOM ogni meta è un elemento a sé,
quindi il suo agente è **noto**, non dedotto. Unire i meta in una stringa
prefissata per riusare quel parser rimetterebbe in gioco proprio la confusione
che la chiave nuova toglie: due meta consecutivi si contaminerebbero, e nella
grammatica non esiste un token che riporti a «globale».

**I blocchi per agente vanno in coda a `_direttive_grezze()`.** Quella stringa
*è* posizionale — la legge `_grezzo_efficace()` per far rispettare il prefisso
anche alla scadenza (R37) — quindi un blocco per agente messo in mezzo
colorerebbe di quell'agente tutto ciò che segue, e una `unavailable_after`
globale sparirebbe. In coda ogni blocco apre col proprio nome e nessuno eredita.
È presidiato da un test suo.

**`META_ROBOTS_AGENTI` è corto per scelta.** Contiene `googlebot` e basta, cioè
esattamente i nomi che il crawler già raccoglieva. Allargarlo ai crawler degli
assistenti — un `<meta name="gptbot">` — vorrebbe dire prima **verificare** che
quei crawler leggano davvero il meta, e non è verificato: si dichiara il limite
invece di assumerlo. È un rilievo in meno, non uno sbagliato in più.

**Una seconda copia dell'estrazione è sparita per strada.**
`tests/conftest.py::pagina()` riscriveva a mano la lettura dei meta, mentre due
righe più sotto due commenti spiegavano perché `link_targets` ed
`estrai_struttura` vengono invece *dalla funzione del crawler* — «se le due
divergessero i controlli girerebbero nei test su una struttura che in
produzione non esiste». Ora anche i meta passano di lì.

**Un test riscritto e uno corretto.**
`test_tech_il_meta_per_agente_resta_fuori_e_lo_si_dichiara` fissava il
comportamento di allora **dichiarando** che sarebbe diventato rosso il giorno
in cui la voce si fosse chiusa: è quel giorno, e ora asserisce l'opposto.
`test_tech_direttive_da_piu_meta_tag` misurava l'unione con lo spazio fra un
meta `robots` e uno `googlebot`; l'invariante che gli appartiene davvero è **lo
spazio come separatore**, che due meta `robots` sulla stessa pagina producono
ancora, e il test ora usa quelli.

**Verifiche.** 1039 test verdi (erano 1032), `flake8` a zero, golden **non
toccati** — nessuna pagina dei due referti sintetici porta un meta per agente,
e questo è il modo in cui il dataset dichiara di non coprire il caso. Referto
end-to-end su un sito locale con `<meta name="googlebot" content="noindex">` e
`<meta name="robots" content="nofollow">` insieme: il primo diventa
`agent_only`, il secondo resta globale. **Nove mutazioni su nove** fanno rosso
alla prima esecuzione, fra cui le tre che distinguono le decisioni qui sopra:
il meta per agente contato anche come globale (cioè il difetto stesso), il
prefisso tolto al blocco nel grezzo, e i blocchi messi in testa invece che in
coda.

### U13 — ✅ RISOLTO (2026-08-26): le due aree di classifica non avevano un solo controllo

**Il difetto.** `mars_lexical` e `mars_semantic` producevano metriche —
`answer_shaped_ratio`, ranghi, consenso — e **nessun controllo con un esito**.
Sette aree su nove alimentavano il piano di interventi, il CSV, il confronto
fra due esecuzioni e i conteggi per gravità; le due che nutrono i quadranti
derivati non contribuivano un solo `Finding`. Il caso più visibile:
`cit.answer_shaped.weak` è un rilievo **derivato**, e per D3 un derivato
rimanda all'area che ha misurato — che non aveva nulla da indicare.

**Che cosa NON si è fatto, e perché.** Il riferimento `marsbeacon/` ha 47
chiavi `lex.`/`sem.`. Portarle tutte era la strada sbagliata, per tre ragioni
misurate prima di scegliere:

- **metà sono già coperte altrove.** `lex.title.*` e `lex.desc.*` sono
  `seo.lh.document-title` e `seo.lh.meta-description`; `lex.alt.*` è
  `wcag.img.alt_missing`. Due rilievi sullo stesso difetto sono due penalità;
- **22 delle 47 sono chiavi `.ok`**, e nessun modulo di MARS emette `SEV_OK`.
  Renderli significativi è la decisione che **R40** rimanda esplicitamente a
  una fase sua: portarli qui l'avrebbe presa di straforo;
- **due controlli non sono realizzabili** senza toccare il contratto del
  crawler: la pagina prodotta da `crawl()` non ha `description` (verificato
  sull'elenco delle chiavi). È lo stesso costo che tiene aperta R51.

Restano fuori anche freschezza, fonti citate e autoconsistenza dei passaggi —
il riferimento le misura, MARS non estrae i dati che servirebbero. Le docstring
dei due moduli lo **dichiarano**, invece di lasciarlo dedurre.

**La soluzione: sette controlli, sei dei quali su misure già fatte.** Il
criterio è uno solo — *spiega un esito di recupero, usa dati che MARS ha già,
non duplica un'altra area*.

| chiave | quando scatta | gravità | penalità |
|---|---|---|---|
| `lex.words.thin` | pagine sotto le 300 parole | grave | 20 |
| `lex.title.dup` | `<title>` ripetuto fra pagine | medio | 8 |
| `lex.query.no_match` | query senza un riscontro lessicale | grave | 20 |
| `sem.chunks.none` | pagine che non producono un passaggio | critico | 40 |
| `sem.chunks.few` | meno di 20 passaggi | medio | 8 |
| `sem.answer_shaped.low` | quota in forma di risposta sotto il 60% | grave | 20 |
| `sem.query.no_match` | query senza un riscontro semantico | grave | 20 |

`lex.title.dup` è l'unico controllo del riferimento che **nessun'altra area di
MARS può vedere**: Lighthouse misura `document-title` su una pagina sola, e il
titolo ripetuto è un fatto *fra* pagine. Le due `query.no_match` non stanno nel
riferimento affatto: MARS i due recuperatori li **esegue**, quindi `matched:
False` è una misura che c'era già e si buttava via (era il dato di R23).

**Le decisioni, con il loro perché.**

**Il punteggio c'è, e resta fuori dal complessivo.** Le due aree avevano
`score: None` per costruzione; ora hanno un voto, e con esso `certificato_area`
le certifica e il piano di interventi ne quantifica il recupero. Ma **entrano
in `AREE_FUORI_DAL_COMPLESSIVO`**, ed è aritmetica, non gusto: quelle due aree
nel complessivo ci sono già come *segnali derivati* a peso 1.5 ciascuno.
Contarle anche come aree porterebbe il totale da 8.0 a 10.0 con **5.0 che
vengono da loro** — metà del referto a due aree su nove. La strada opposta —
togliere i segnali e tenere le aree — costa di più: il consenso RRF è la
domanda del progetto e **nessuno dei sette controlli lo misura**, quindi
sparirebbe dal complessivo per non tornare. Misurato sui golden: `overall`
resta 60.1 e 65.5, identici a prima.

**La soglia in forma di risposta è 60, la stessa di `mars_citability`.** Con
due numeri diversi il referto avrebbe detto «segnale debole» accanto a un'area
senza nulla da segnalare. I moduli sono plugin e non si importano fra loro: a
tenerle insieme non c'è un accorgimento ma **un test**, come per `ORIGINE`.

**Penalità per controllo, non per occorrenza.** Su un sito da cinquanta pagine
`lex.words.thin` da solo saturerebbe il punteggio. Quante volte il difetto
ricorra lo dicono i `params`, dove sta anche `urls` (R47): la treemap si colora
sulle pagine sottili e su quelle senza una risposta, **non** su quelle che una
risposta ce l'hanno.

**Nessun `urls` sulle due `query.no_match`.** Una domanda senza risposta non è
il difetto di una pagina, e sceglierne una per colorare la treemap sarebbe
inventare l'indirizzo. Omettere è diverso da una lista vuota, ed è documentato.

**`status: "ranking"` è migrato dal posto del verdetto a quello dei
qualificatori**, esattamente come U1.9 aveva previsto. La frase però diceva
«classifica, **non un voto**», e con il voto accanto negava il numero a due
centimetri di distanza: ora è «con una classifica dei passaggi».

**Una riga di prosa era diventata falsa senza che nulla se ne accorgesse.**
«media pesata di N misure; citabilità e giudizio LLM esclusi» era scritta a
mano in **tre** viste, ed era una seconda copia di
`AREE_FUORI_DAL_COMPLESSIVO`. Ora la compone `aree_escluse_leggibili()`
leggendo `overall["excluded"]`: una decisione su quell'elenco si propaga da
sola. È la stessa classe di R32 — deriva fra ciò che il codice fa e ciò che il
testo afferma — colta qui perché la modifica l'ha resa visibile.

**Due test riscritti con intenzione, e va detto.**
`test_html_non_finge_un_voto_per_lessicale_e_semantica` asseriva
`"/100" not in scheda`: era **giusto** finché quelle aree un voto non
l'avevano, ed è la decisione a superarlo, non un aggiustamento per far tornare
il verde. Il suo meccanismo — la parola arriva dallo *stato* dichiarato dal
modulo, mai dal nome cablato nella vista (R38) — resta asserito.
`test_l_icona_mancante_e_dichiarata` invece era **sbagliato**: la sua regex
contava anche le ancore interne `href='#r-...'` fra i «riferimenti esterni», e
restava verde solo perché la fixture non aveva rilievi con un `fix`. Misurava
la fixture, non R43.

**Verifiche.** 1032 test verdi (erano 1011), `flake8` a zero, golden
rigenerati e diff riletto: `overall` invariato, il piano passa da 5 aree su 9 a
7, il delta da 15 a 18 comparsi. Referto end-to-end su un sito locale servito
da `http.server`, con sentence-transformers reale e con il proxy: i tre rilievi
lessicali e i due semantici escono con gli `urls` giusti e il complessivo non
si muove. **Sedici mutazioni su sedici** fanno rosso; **tre sfuggivano alla
prima esecuzione**, e sono quelle che hanno insegnato qualcosa:

- `max(0, round(100 - penalita))` → `round(...)`: le penalità di oggi non
  arrivano a 100 (48 sul lessicale, 80 sul semantico), quindi il pavimento è
  **irraggiungibile con un sito**. Ora un test lo raggiunge alzando `PENALITA`,
  così il presidio c'è già il giorno in cui un controllo nuovo saturerà;
- `if quota >= SOGLIA` → `>`: mancava il caso di confine, l'unico che
  distingue i due operatori. Tre passaggi su cinque fanno esattamente il 60%;
- `con_risposta.add(url)` → `pass`: il test aveva quota 0.0, dove l'insieme è
  vuoto in entrambi i casi. Serviva una pagina **con** una risposta accanto a
  una senza, cioè proprio ciò che `urls` deve saper distinguere.

### R48 — ✅ RIDOTTO (2026-08-26): l'aritmetica del grafo è uscita dal JavaScript
*(la voce non si chiude: si rimpicciolisce, e il perimetro rimasto è scritto in
[CONTRIBUTING.md](CONTRIBUTING.md))*

**Il difetto.** `REFERTO_JS` era presidiato da quattro test, e tutti guardavano la
**stringa**: che non contenga origini esterne, che non contenga dati del sito,
che compaia solo dove c'è un grafo, che chiami `removeAttribute("hidden")`.
Nessuno lo **eseguiva**. Ventisei righe di aritmetica — la disposizione ad anelli
— vivevano lì dentro senza che nulla le verificasse.

**Delle tre strade, la seconda.** `jsdom` in `requirements-dev` avrebbe allargato
la suite a npm, e su un clone senza `node` un test marcato `skipif` è sempre
verde perché sempre saltato: il TO-DO stesso lo chiamava «un presidio che non
presidia». Il porting in Python porta il comportamento dentro `pytest` **senza**
allargare l'ambiente, e per giunta riduce il JavaScript: `anelli()` scende da 26
righe a 5, e la funzione non calcola più nulla — legge `data-ax`/`data-ay`.

**Il costo, misurato.** Circa 24 caratteri per nodo nell'HTML. Il diff dei due
golden è di 16 righe aggiunte e 48 tolte: il JavaScript si è accorciato più di
quanto gli attributi abbiano allungato.

**Quel che resta al JavaScript, e va detto.** Il **gesto**: il fuoco,
l'evidenziazione dei vicini, lo zoom, il ritorno al layout di partenza. Il banco
`tools/banco_grafo.py` resta l'unico a provarlo, e va rilanciato da chi tocca
`REFERTO_JS` — il porting toglie il calcolo, non il gesto. Rilanciato dopo la
modifica: **nove controlli su nove**, coi raggi `[0 123 123 246]` identici a
quelli che `disposizione_ad_anelli()` produce in Python.

**Una mutazione sfuggita al primo giro**, e vale registrarla: «tutti i nodi di un
anello allo stesso angolo» passava. Il test verificava i **raggi**, che restano
quelli giusti mentre i nodi finiscono uno sopra l'altro. Aggiunte due asserzioni
— i punti dello stesso anello sono diversi, e il primo sta in alto — la mutazione
diventa rossa.

**Verifiche.** 1011 test verdi, `flake8` a zero, i due golden HTML rigenerati e
il diff **riletto**. **Sei mutazioni su sei** fanno rosso, e il banco passa.

### R52 — ✅ RISOLTO (2026-08-26): tre difetti dell'incontro fra R36 e R37
*(trovati lo stesso giorno in cui sono nati, correggendo un test che passava per
la ragione sbagliata. Nessuno era nel TO-DO)*

R36 legge la scadenza dal **testo grezzo**, con una regex, perché una data
contiene spazi e virgole — i separatori delle direttive. R37 separa i prefissi
per agente lavorando **sui pezzi**. Le due letture non si conoscevano, e nel
punto in cui si toccano c'erano tre difetti. Misurati:

| `X-Robots-Tag` | prima | dopo |
|---|---|---|
| `unavailable_after: 2020-09-21t12:00:00z` | **94**, nessun rilievo | 54, scaduta |
| `unavailable_after: saturday, 21-sep-2020 12:00:00 gmt` | 46, **+ agente `21-sep-2020 12`** | 54, scaduta |
| `googlebot: unavailable_after: 2020-01-01` | **46** | 86, `agent_only` |
| `gptbot: unavailable_after: 2020-01-01` | 54 | 54 |

**1. La Zulu minuscola non si leggeva, ed è la sola che arriva.** Il crawler
scrive `meta_robots` e `x_robots_tag` con `.strip().lower()` (`mars_core`),
quindi una `Z` maiuscola **non arriva mai** al modulo — e
`datetime.fromisoformat` rifiuta la minuscola con `ValueError`. Il formato ISO
con fuso, che Google documenta, non veniva letto affatto.

Il difetto era **mascherato da un mio test**: `test_tech_i_formati_di_data_
ammessi_si_leggono_tutti` parametrizzava `"2020-09-21T12:00:00Z"`, cioè
presidiava un percorso che il crawler ha già chiuso un livello più su, mentre il
solo caso reale restava scoperto. I parametri sono ora tutti minuscoli, e il
difetto è emerso appena il test è diventato fedele.

**2. Una data diventava un agente.** Un'ora contiene i due punti e una data RFC
850 le virgole: `unavailable_after: saturday, 21-sep-2020 12:00:00 gmt` si spezza
in due pezzi, e il secondo ha i due punti dell'ora. Letto come prefisso creava
l'agente `21-sep-2020 12` e con esso un rilievo `agent_only` **inventato**. Un
nome di crawler non contiene spazi: è il criterio che distingue le due cose, e
ora sta in `_agente_del_pezzo()`, un punto solo per entrambi i lettori.

**3. La scadenza ignorava il prefisso.** `googlebot: unavailable_after:
<passato>` produceva il rilievo pieno **più** `agent_only`, e il punteggio
scendeva a 46 — cioè **peggio** di una scadenza che vale per tutti, che ne fa 54.
Una restrizione a un solo agente non può pesare più di quella che vale per
chiunque. `_grezzo_efficace()` ricompone ora il testo delle sole direttive che
valgono per gli assistenti, e la regex della data legge quello.

**Ricomporre il testo, non i token.** Il primo tentativo ricostruiva il grezzo
unendo i token: una data ne occupa quattro, e un insieme ne perde l'ordine — due
test delle date sono diventati rossi subito. Si ricompone il testo, con `", "`:
senza lo spazio la data si legge ancora, ma **solo** per un dettaglio
implementativo di `email._parseaddr`, che cerca l'ultima virgola dentro il primo
token. Appoggiarsi a quello vorrebbe dire smettere di leggere le date il giorno
in cui CPython lo cambia, senza che nulla diventi rosso. Un test fissa la
ricomposizione — la mutazione che toglie lo spazio era l'unica sfuggita al primo
giro.

**Verifiche.** 1011 test verdi, `flake8` a zero, golden fermi. **Sette mutazioni
su sette** fanno rosso.

### R49 — ✅ RISOLTO (2026-08-26): il donut delle pagine, coi nomi che non affermano
**Il ripiego che c'era.** La Fase 5 di UPGRADE.md prevedeva un donut «senza
rilievi / con rilievi / scartate» e aveva ripiegato su due numeri — *pagine
scansionate* e *URL scartati* — dichiarando il motivo: mancavano gli `url` sui
rilievi. R47 li ha portati (`params["urls"]`, `pagine_del_rilievo()`), quindi il
dato c'era.

**Due vincoli misurati hanno cambiato i nomi del piano, non il taglio.**

- **Nessuna area registra QUALI pagine ha guardato.** `mars_wcag` scrive
  `pages_tested` come conteggio e axe si ferma alle prime del campione;
  Lighthouse ne misura una. «Pulita» e «non guardata» non sono distinguibili dal
  dato, quindi un settore chiamato «senza rilievi» affermerebbe ciò che nessuno
  ha misurato — per giunta su un disegno che si legge come una ripartizione
  esaustiva, cosa che la treemap non è. Il settore si chiama **«nessun rilievo le
  cita»**, che è la frase già usata dalla treemap: una sola voce per un concetto.
- **`skipped` non contiene pagine, contiene motivi**, e fra quelli ci sono un
  altro host e un URL non analizzabile. Il terzo settore si chiama **«URL
  scartati»**, non «pagine scartate», e il totale è **«URL incontrati»**: è ciò
  che il crawler ha visto, non le sole pagine del sito.

Il caveat sta così **dentro il disegno** invece che in una nota accanto — che era
l'opzione che il TO-DO stesso sconsigliava, perché una nota non toglie
l'affermazione dal grafico.

**Il colore dice la stessa cosa dei nomi.** Il settore «nessun rilievo le cita»
prende il grigio del binario e **non il verde**: è la stessa scelta per cui la
treemap lascia neutro ciò che non sa (R21, R47). Le classi sono proprie
(`con-rilievi`, `non-citate`, `scartati`) e non le `.bad`/`.muted` generiche, che
altrove impostano `color` e non `stroke`: riusarle qui avrebbe legato due regole
con significati diversi.

**Un URL citato da un rilievo può non essere fra le pagine.** Gli strumenti
esterni seguono i propri redirect, quindi il conteggio è l'**intersezione** con
le pagine scansionate: contare i citati e basta gonfierebbe un settore oltre il
totale. Un test lo presidia.

**Non entra nel dato canonico**, quindi `schema_version` resta **2** e json, txt,
md e csv non si muovono: la ripartizione è derivabile per intero da `pages`,
`skipped` e `params["urls"]`, come la geometria della treemap. Verificato — il
diff tocca i due soli `referto*.html`.

**Verifiche.** 1004 test verdi (erano 1001), `flake8` a zero. I due golden HTML
rigenerati e il diff **riletto**: esce la tessera a due numeri, entra il donut
con i suoi tre conteggi (3 con rilievi, 0 non citate, 4 URL scartati, totale 7) e
le quattro regole CSS. **Otto mutazioni su otto** fanno rosso, comprese quelle
che rimettono i nomi del piano e quella che colora di verde le non citate.

### R35 — ✅ RISOLTO (2026-08-26): i due recuperatori leggevano contenuti diversi
**Il difetto.** R10 aveva lavorato perché i due ranghi si riferissero alle stesse
**unità**. Nessuno aveva poi controllato che leggessero lo stesso **contenuto** di
quelle unità: `mars_lexical` indicizzava heading + testo, `mars_semantic` il solo
testo. Riprodotto con la parola cercata presente solo nell'heading:

```
lessicale  -> matched = True    (indicizza heading + testo)
vettoriale -> matched = False   (indicizza il solo testo)
```

Su un sito con le FAQ nei titoli i due erano in disaccordo **per costruzione**, e
il consenso RRF ne usciva depresso per una ragione che non riguarda il sito.

**Il punteggio SCENDE, e non perché il sito sia peggiorato.** È il fatto che
conta, e va letto due volte prima di allarmarsi:

| | prima | dopo |
|---|---|---|
| Recuperabilità ibrida (consenso RRF) | 100,0 | 66,7 |
| Complessivo | 66,3 | 60,1 |
| Citabilità IA | 65,6 | 60,7 |
| query «quanto costa una seduta…» | 2/3 | **3/3** |
| aggregato su tutte le query | 3/3 | 2/3 |

La **singola query migliora** — il vettoriale ora trova il chunk giusto, «Quanto
dura una seduta?», che l'heading rendeva riconoscibile — mentre **l'aggregato
peggiora**. Il 100 di prima era un consenso perfetto ottenuto confrontando due
indici **diversi**: sembrava ottimo e non significava quello che diceva. Il 66,7
di adesso è un consenso vero fra due recuperatori che guardano lo stesso testo.
Nel referto il quadrante «Recuperabilità» passa da `ok` a `warn` per la stessa
ragione.

**Chi legge lo storico va avvisato.** Il riquadro «RISPETTO A PRIMA» mostra
`Complessivo -1 (61 → 60)` e `citability +1 (60 → 61)`: su un archivio già
scritto, il confronto fra un'esecuzione di prima e una di dopo misura un
**cambio di strumento**, non un cambio del sito. Chi guarda una serie storica a
cavallo di questo commit deve saperlo.

**`testi` e `corpus` restano due cose diverse.** Il corpus è ciò che il
recuperatore indicizza; i testi sono ciò su cui girano i segnali answer-shaped, e
lì l'heading arriva già a parte a `question_signals` — unirli anche lì lo
conterebbe due volte e sposterebbe `MIN_PAROLE`, che con R35 non c'entra. Un test
lo presidia.

**Quel che il TO-DO chiedeva e non è stato fatto.** La voce diceva «va misurata
prima e dopo su un sito reale, non applicata a intuito». La misura su un sito
reale **non è stata fatta**: la suite non può darla, perché `force_proxy` esclude
il modello vero e la rete è vietata. Quanto sopra è misurato sui due referti
sintetici col proxy char-TFIDF, che pesa un heading corto pochissimo — quindi
**sottostima** l'effetto, non lo sovrastima. Resta da verificare su un sito con
le FAQ nei titoli e `sentence-transformers` attivo.

**Verifiche.** 1001 test verdi (erano 998), `flake8` a zero. I quattro golden non
degradati rigenerati e il diff **riletto**: solo valori numerici e le classi CSS
che ne dipendono, nessuna chiave nuova o rimossa, nessun testo tradotto toccato.
Tre mutazioni su tre fanno rosso.

### R37 — ✅ RISOLTO A METÀ (2026-08-26): tre casi diversi, un giudizio solo
*(la metà che resta — il `<meta name="googlebot">` — è una voce nuova, R51)*

**Il difetto, misurato prima e dopo.** `X-Robots-Tag` ammette un prefisso che
limita la direttiva a un solo crawler, e i tre casi ricevevano lo stesso identico
giudizio:

| `X-Robots-Tag` | prima | dopo | rilievo |
|---|---|---|---|
| `noindex` | 54 | 54 | `tech.index.noindex` critico |
| `googlebot: noindex` | 54 | **86** | `tech.index.agent_only` medio |
| `gptbot: noindex` | 54 | 54 | `tech.index.noindex` critico, `agents: [gptbot]` |

**La contropartita è dichiarata, non nascosta.** Questa correzione **abbassa** la
gravità di un'esclusione reale da Google. È una scelta editoriale coerente con
l'oggetto del progetto — MARS misura la citabilità IA, e una direttiva mirata al
solo Google non toglie il sito agli assistenti — e sta scritta nella docstring
del modulo, non solo qui.

**Il prefisso si legge per posizione, non per token.** Più header `X-Robots-Tag`
arrivano uniti da **una virgola sola**: è `requests` che li concatena
(`resp.headers.get`). Quindi un prefisso vale fino al prossimo che compare, ed è
il caso documentato da Google:

```
X-Robots-Tag: googlebot: nofollow
X-Robots-Tag: otherbot: noindex, nofollow
```

**I due punti significano due cose, e confonderle rompe l'altra.**
`max-snippet: 0` è una direttiva col suo valore, e i due pezzi si **ricuciono**
(R36); `googlebot: noindex` è un prefisso, e i due pezzi si **separano**. Un
parser che trattasse ogni `:` allo stesso modo romperebbe l'altro caso in
silenzio: ricucendo tutto sparirebbe il noindex, separando tutto sparirebbe il
divieto di frammento. Il confine è presidiato da un test che li esercita insieme.

**Tre mutazioni sfuggite alla prima esecuzione**, e la ragione era un difetto
vero: `direttive_robots` e `controlla_indicizzabilita` calcolavano **entrambe**
quali direttive valgono per gli assistenti. Con la regola scritta in due punti,
mutarne uno non si vedeva — `direttive_robots` era diventata di fatto codice
morto per il modulo, viva solo nei test. Estratta `direttive_efficaci()`, unica
definizione, le tre mutazioni diventano rosse. Una quarta sfuggiva perché il test
non asseriva `params["urls"]` sul rilievo nuovo, che senza uscirebbe dalla
treemap (R47).

**Il test che fissava il comportamento vecchio è stato riscritto, non piegato.**
`test_tech_la_normalizzazione_del_valore_non_ingoia_il_prefisso` asseriva che
`googlebot:` restasse fra i token: era il comportamento di allora, e R37 lo cambia
di proposito. Al suo posto un test che fissa il **confine fra le due ricuciture**,
che è ciò che deve restare vero comunque.

**Verifiche.** 998 test verdi (erano 989), `flake8` a zero, golden fermi — i due
referti sintetici non portano prefissi per agente. **Dieci mutazioni su dieci**
fanno rosso, dopo la rimozione della duplicazione.

### R39 (caselle 2 e 3) — ✅ RISOLTE (2026-08-26): un WAPT tentato e fallito taceva
*(la casella 1 — raggruppare per `alertRef` — resta aperta per decisione: sposta i
punteggi di ogni sito e migra le chiavi pubbliche, quindi vuole un commit suo)*

**Il ripiego silenzioso.** Se `run_zap` restituiva `None` c'era **solo un
`print`**, e il referto dichiarava «HTTP-Headers, superficie» senza mai dire che
un daemon c'era e non aveva portato a termine la scansione. Chi legge il referto
non ha la console davanti: vedeva un'area di sicurezza fatta di soli header e non
poteva sapere che il WAPT era stato tentato. È lo stesso difetto di onestà che
R38 ha chiuso altrove, e il principio 2 lo vieta.

Ora il ripiego passa da `_ripiego_dopo_zap()`, che aggiunge `sec.status.zap_failed`
**in testa** ai rilievi — come gli altri stati: è la premessa per leggere il
punteggio, non una nota in fondo. Il punteggio degli header non si tocca, perché
è la misura che è stata fatta davvero.

**L'altra metà è presidiata:** senza daemon raggiungibile non c'è nulla da
dichiarare, e un rilievo «ZAP ha fallito» sarebbe falso. Un test lo verifica,
altrimenti la correzione avrebbe potuto aggiungere l'avviso sempre.

**Le due diagnosi degli header.** Se HEAD sollevava e GET rispondeva ≥ 400,
`errore` veniva riassegnato a `None` dal secondo giro e la diagnosi diventava il
solo «HTTP 500»: il `ConnectionError` che spiegava il primo tentativo spariva. I
due tentativi possono fallire per ragioni **diverse** — HEAD rifiutato dalla
rete, GET accolto e andato in errore — e saperlo dice qualcosa che nessuna delle
due dice da sola. Ora si conservano entrambe, deduplicate con `dict.fromkeys`
perché due tentativi falliti allo stesso modo restino una diagnosi sola.

**Una mutazione sfuggita alla prima esecuzione**, e vale la pena registrarla:
«l'avviso finisce in coda invece che in testa» passava. Il ripiego finto del test
restituiva `findings: []`, quindi la lista aveva **un elemento solo** e
l'asserzione sulla posizione era vuota — verde per costruzione, non per merito.
Corretto il test dando un rilievo proprio al ripiego finto, la mutazione diventa
rossa.

**Verifiche.** 989 test verdi (erano 985), `flake8` a zero, golden fermi: nessun
punteggio si muove. **Otto mutazioni su otto** fanno rosso, dopo la correzione di
cui sopra. La chiave nuova è tradotta in inglese; `sec.status.*` resta fuori da
`mars_fixes` e `mars_remediation`, che escludono le chiavi di stato per
costruzione — uno stato non è un difetto da riparare.

### R50 — ✅ RISOLTO (2026-08-26): metà dei test i18n erano rossi a caso, e nessuno lo sapeva
*(trovata chiudendo R28, non era nel TO-DO)*

**Come è saltata fuori.** Durante R28 la suite è uscita rossa **una volta** su
`test_una_lingua_sconosciuta_rende_come_l_italiano[html]`, e le cinque
esecuzioni successive sono state verdi. Il primo sospetto — la trappola del
bytecode, perché avevo appena sostituito `1.2.0` con `1.2.1`, **stessa
lunghezza** — non ha retto: tre tentativi mirati di riprodurla non hanno
prodotto nulla. Registrato come non spiegato invece che archiviato, e cercato
nel codice.

**La causa, dimostrata.** `generated_at` nasce da `time.strftime` **al secondo**
(`mars_report.py`) e arriva fino alla resa: nell'HTML sta nella testata. Il
`_resa()` di `tests/test_i18n.py` costruisce il referto **due volte** e
confronta le due rese — «pt rende come it», «il JSON resta italiano in ogni
lingua». Se le due costruzioni cadono su due secondi diversi, i due documenti
differiscono di due righe e il test è rosso. Misurato: cambiando il solo
`generated_at`, la resa cambia.

Non è raro per caso: la probabilità è il rapporto fra la durata di una
costruzione e un secondo. Ecco perché usciva una volta ogni tanto e non si
riproduceva a comando.

**La correzione era già scritta cinquanta righe più in là.**
`tests/test_golden.py` fissa `referto["generated_at"] = GENERATED_AT` prima di
rendere, **per la stessa ragione**, da sempre — e `test_i18n` importa già da
quel file. Mancava solo la stessa riga in `_resa`.

**Perché vale una voce e non una riga silenziosa.** Un rosso casuale non è
rumore: insegna a rilanciare la suite invece di leggerla, ed è il modo in cui un
difetto vero passa inosservato. Il presidio è un test che fa avanzare l'orologio
di proposito a ogni lettura: senza il campo fissato è rosso **sempre**, invece
che a caso — verificato togliendo la riga.

**Verifiche.** 985 test verdi, `flake8` a zero, nessun `mars_*.py` toccato
quindi golden fermi.

### R28 — ✅ RISOLTO (2026-08-26): un disco pieno valeva come un giudizio sul sito
**Il difetto, riprodotto prima di toccare il codice** — con un provider finto,
senza rete e senza spesa:

| caso | prima | dopo |
|---|---|---|
| `--output` su percorso non scrivibile | traceback, **exit 1** | exit **3**, motivo su stderr |
| `--history` non scrivibile | traceback, exit 1, **referto perduto** | referto stampato, exit 0, guasto dichiarato |
| tutte le query fallite | `"rate": 0.0` | `"rate": null` |
| `overall_rate` nello stesso file | `null` | `null` |

Exit 1 è il codice di `--fail-under`: una pipeline che distingue «sotto soglia»
da «rotto» leggeva un guasto di scrittura come un **giudizio sul sito**. E con
`--history` il crash arrivava prima del rendering, quindi buttava via un referto
già pagato in chiamate API.

**«0 su 0» non è «0%».** Le due misure dello stesso non-dato si contraddicevano
nella stessa riga JSONL: `rate: 0.0` accanto a `overall_rate: null`. Ora dicono
la stessa cosa. L'altra metà è presidiata da un test apposta: uno 0% **misurato**
deve restare `0.0`, o la correzione avrebbe solo spostato la bugia.

**Le due modifiche del tasso stanno nello stesso commit, e devono.** `render_text`
formattava `rate` con `%.1f`: da sola, la prima avrebbe fatto sollevare
`TypeError` alla vista testo. La parola per il non misurato — `n/d` — è quella
che il totale usava già.

**Il commento di `mars_audit` era una promessa senza controparte.** Diceva da
sempre «Codici di uscita, allineati a quelli di `mars_citations.py`», mentre qui
i valori erano `return 1/2/0` nudi e il 3 non esisteva. Ora ci sono le costanti,
e un test è la controparte: se le due scale divergono, diventa rosso.

**Una divergenza dalla lettera della casella, dichiarata.** Il TO-DO chiedeva
«gestire `OSError` […] **e scrivere il referto prima dello storico**». Il
riordino non è stato fatto, e la misura dice perché: con `append_history` che
restituisce `False` invece di sollevare, il referto arriva comunque — è ciò che
il test asserisce. Spostare la chiamata avrebbe inoltre **rotto il parallelo con
`mars_audit`**, dove l'ordine è già dato → storico → render → output, e avrebbe
cambiato l'ordine osservabile su stdout/stderr per chi ne fa parsing. La
sostanza della richiesta — il referto non si perde — è soddisfatta; la lettera
no, e non serviva.

**Il modo di forzare l'errore è una directory, non un `chmod`.** `open()` su una
directory solleva `IsADirectoryError` — sottoclasse di `OSError` — a prescindere
dai permessi e anche da root, mentre un `chmod 0o500` sarebbe verde per caso in
un container che gira da root: un test che non esercita nulla.

**Verifiche.** `mars_citations` non aveva **un solo test**: ora ne ha undici, in
`tests/test_citations.py`, tutti visti fallire sul codice di prima. 984 verdi in
totale (erano 973), `flake8` a zero, golden non toccati. **Sette mutazioni su
sette** fanno rosso, fra cui il codice di scrittura riportato a 1, lo storico che
torna a sollevare, e quello che fallisce in silenzio. `__version__` a **1.2.1**:
`rate` nullable e il codice 3 sono comportamento osservabile, e il README
dichiara entrambi — comprese le righe di storico scritte prima, che portano
ancora `0.0`.

### R33 — ✅ RISOLTO (2026-08-26): due presìdi che passavano per la ragione sbagliata
**Il difetto, misurato prima di toccare il codice.** Lanciando `pytest` da una
directory diversa dalla radice: **2 failure e 4 errori** — uno in più di quanti
la voce ne dichiarasse, perché `test_api.py::test_esempio_valido_e_completo` si
era aggiunto nel frattempo. E `test_url_obbligatorio` **passava a vuoto**: si
limitava ad asserire `rc == 2`, ma da un'altra cwd quel 2 arrivava da Python
(«can't open file .../mars_audit.py»), non da argparse. Un test verde che non
aveva mai raggiunto il parser.

**L'autoconsistenza dell'HTML era controllata su un quinto delle superfici.**
La regex cercava solo `src`/`href` quotati. Iniettando nel referto le quattro
forme che quella regex non vede, il conteggio dei riferimenti esterni **non
cambiava**:

| forma iniettata | vista prima | vista dopo |
|---|---|---|
| `@font-face{src:url(https://…)}` | no | sì |
| `background:url('https://…')` | no | sì |
| `@import "https://…"` | no | sì |
| `srcset='https://… 1x'` | no | sì |
| `<script src="https://…">` | sì | sì |

**Percorsi assoluti, non una fixture `chdir`.** È l'idioma già in casa
(`test_i18n`, `test_core`, `test_report`), e una `chdir` globale avrebbe
nascosto la dipendenza invece di toglierla — oltre a collidere con
`test_core.py`, che la cwd la cambia di proposito.

**La trappola dello split, che è costata l'unico giro rosso.** Spezzare i
candidati sulle virgole per gestire `srcset` **scavalca il filtro `data:`**: un
data URI contiene una virgola per costruzione, e a pezzi non comincia più per
`data:`. Misurato: sui golden sarebbe uscito `DIGEST`, sulla fixture l'intero
base64 della favicon. Si spezza quindi il **solo** `srcset`, dove la stessa
ambiguità non esiste — le virgole di un URL vanno percent-encoded, o
l'attributo è invalido.

**Un caso di test scritto male, corretto invece di piegare il codice.** Avevo
asserito che `srcset="data:image/png;base64,AA,BB 1x"` non producesse
riferimenti: è un input che l'HTML non ammette, quindi l'asserzione pretendeva
una proprietà inesistente. È stato tolto il caso, non allargato il codice.

**Il controllo gira anche sui due golden, non solo sulla fixture.** La fixture
ha una pagina, un rilievo e un solo `href` in tutto l'HTML: non attraversa il
grafo, la treemap, le tabelle — cioè i rami dove una regressione ha più
probabilità di nascere. Serve un'esenzione per i frammenti `#…`, che non escono
dal file: `url(#grafo-freccia)` è il marcatore delle frecce del grafo, e gli
`href="#…"` sono le ancore dei rilievi (42 nel golden pieno).

**Il terzo bullet non andava chiuso, e la misura lo dimostra.** La voce
segnalava la fixture `CONTROLLI` «ferma a cinque campi su otto». Verificato sul
sorgente: `_elenco_controlli` legge esattamente `id`, `title`, `passed`,
`manual`, `items` — i cinque che la fixture ha. `score`, `weight`,
`scoreDisplayMode` e `description` sono consumati **solo dentro `mars_seo`**,
mai dal referto. Il ramo davvero delicato è un altro — il join fra controlli e
rilievi via `params["rule"]`, che porta il `detail` sotto la voce — e i golden
lo esercitano: in `referto.json`, 8 rilievi su 11 audit si agganciano, tutti
con `detail`. La fixture resta minima perché è ciò che deve essere: esercita i
tre stati della resa, il join lo copre U2 — esattamente come la voce prevedeva
scrivendo «candidata a sparire dentro U2».

**Verifiche.** 973 test verdi (erano 970), `flake8` a zero, golden non toccati:
nessun file `mars_*.py` è stato modificato. **Sei mutazioni su sei** fanno
rosso — le quattro forme di riferimento esterno nel CSS del referto, un `url()`
iniettato dentro un golden congelato, e il `cwd=RADICE` tolto al sottoprocesso
(quest'ultima verificata lanciando la suite da un'altra directory, che è
l'unico posto dove quel difetto si manifesta).

### R36 — ✅ RISOLTO (2026-08-26): `nosnippet` era invisibile, ed è la direttiva che conta di più
**Il difetto, misurato prima di toccare il codice.** `direttive_robots()` leggeva
tutte le direttive, ma `controlla_indicizzabilita` ne giudicava due — `noindex` e
`nofollow`. Restavano mute proprio quelle che governano l'**estrazione del
testo**, cioè il meccanismo con cui un assistente cita una pagina. Contro un
riferimento senza direttive che vale 94:

| direttiva | prima | dopo |
|---|---|---|
| `nosnippet` | 94 | 54 |
| `max-snippet:0` | 94 | 54 |
| `max-snippet: 0` (con spazio) | 94 | 54 |
| `noarchive` | 94 | 91 |
| `unavailable_after: 2020-01-01` | 94 | 54 |

Una pagina con `nosnippet` è regolarmente indicizzata e **non può essere
citata**: nessun frammento del suo testo può comparire in una risposta. Per uno
strumento che misura la citabilità era la lacuna più grande dell'area 1.

**La tokenizzazione nascondeva metà del difetto.** `_SEPARATORI` divide su
virgole e spazi, e lo spazio dopo i due punti è legale: `max-snippet: 0`
arrivava come i **due** token `max-snippet:` e `0`, che non corrispondono a
nulla. Un `frozenset({"nosnippet", "max-snippet:0"})` avrebbe colto la forma
compatta e mancato quella spaziata — cioè avrebbe funzionato sui test scritti a
mano e non su metà dei siti veri. Il valore si ricuce al proprio nome
(`_DIRETTIVE_CON_VALORE`), e si ricuce **per nome, non su ogni `:`**: ricucire
tutto incollerebbe il prefisso per agente alla sua direttiva
(`googlebot:noindex`) e nasconderebbe un `noindex` — l'opposto di ciò che serve.
Le quattro direttive con valore sono elencate per intero benché il modulo ne
giudichi due: è la stessa riga, e ometterle lascerebbe il difetto in agguato per
la prossima che si aggiunge.

**`unavailable_after` ha preso una chiave propria, non l'elenco del `noindex`.**
Il TO-DO proponeva «come `noindex`». Rileggendo il codice prima di scegliere: il
titolo di quel rilievo — `«…(noindex o none, in meta robots o X-Robots-Tag)»` —
è sotto test come sottostringa in una decina di punti, è tradotto in inglese ed
è congelato nei golden. Nominarvi una terza direttiva muoveva tutto quel
materiale per un guadagno nullo, mentre `tech.index.unavailable_after` è
puramente additiva: nessun testo esistente cambia, nessun golden si muove.

**Tre decisioni che il codice porta scritte accanto a sé.**

- **Il denominatore della gravità sono le pagine ancora *citabili*, non tutte.**
  Se le altre sono già escluse dagli indici il sito resta muto lo stesso, e
  chiamarlo `grave` direbbe che qualcosa si salva.
- **Lo stesso fatto non si paga due volte.** `noindex, nosnippet` è una
  scrittura reale: sommare le due penalità toglierebbe 80 punti su 100 per un
  difetto solo. Una pagina già esclusa non entra nel conteggio del divieto di
  frammento, e nemmeno in quello della scadenza — che dichiara lo stesso fatto
  del `noindex` con altre parole.
- **Una data illeggibile non è una data scaduta.** Il valore viene dal sito
  analizzato, quindi è dato ostile: `scadenza_dichiarata()` restituisce `None` e
  non produce alcun giudizio. Dedurne «scaduta» sarebbe un rilievo *critico*
  fondato su una misura che non c'è.

**Due formati di data, e la virgola che è anche un separatore.** Google
documenta ISO 8601 (`2020-09-21`) e RFC 850
(`Saturday, 21-Sep-2020 12:00:00 GMT`). Il secondo contiene una virgola, che è
il separatore delle direttive: tagliare sempre lì lascerebbe `Saturday`, e la
data non si leggerebbe mai. Si prova prima la coda intera — il caso normale,
la direttiva è l'ultima — e solo se non si legge si taglia alla virgola, che è
il caso di una ISO seguita da altre direttive. Verificato che
`datetime.fromisoformat` e `email.utils.parsedate_to_datetime` coprano insieme
entrambi i formati, RFC 850 con i trattini compreso e insensibile al maiuscolo.

**L'orologio si legge una volta per audit.** Dentro il ciclo, due pagine con la
stessa data ai due lati di un secondo riceverebbero giudizi diversi e l'audit
non sarebbe riproducibile su se stesso. È presidiato da un test che **conta le
letture**: spostare quella riga dentro il ciclo lascia verde ogni altra
asserzione.

**Verifiche.** 970 test verdi, `flake8` a zero, golden non toccati (i due
referti sintetici non portano queste direttive). **Diciannove mutazioni su
diciannove** fanno rosso, fra cui le quattro che distinguono le decisioni qui
sopra: il valore tagliato sempre alla virgola, il valore mai tagliato, la
gravità misurata su tutte le pagine, l'orologio letto nel ciclo. Un presidio in
più sugli esempi: applicare l'`example` del catalogo — italiano e inglese — deve
**chiudere** il rilievo che promette di correggere, e il caso che lo rende utile
è `max-snippet:-1`, che sembra un limite ed è il suo contrario.

**Che cosa resta fuori.** R37 — il prefisso per agente dell'X-Robots-Tag
(`googlebot: noindex`) è ancora contato come se valesse per tutti — resta
aperta: la ricucitura per nome è stata scritta in modo da non peggiorarla, e un
test lo presidia.

### R47 — ✅ RISOLTO (2026-08-26): nessun rilievo dichiarava la pagina che lo aveva prodotto
**Il difetto, misurato prima di toccare il codice.** `Finding.url` esisteva dal
modello dati di U1 ed era vuoto quasi ovunque: sui due referti sintetici, 2
rilievi su 28 e 0 su 19. I due valorizzati puntavano a `dequeuniversity.com`
mentre le pagine scansionate stavano su `esempio.test`. Il campo aveva due
significati possibili — la pagina colpita e il riferimento allo strumento — ne
esercitava uno solo, e la docstring di `Finding` non diceva quale: era l'unico
campo del modello dati che non spiegava.

**Che cosa costava.** Il passo 3 della Fase 8 doveva colorare la treemap con la
gravità peggiore dei rilievi che citano ciascuna pagina. Applicata alla
lettera, quella regola non trovava **mai** una corrispondenza e avrebbe dipinto
ogni pagina di «nessun problema» — il difetto che R21 ha chiuso altrove. Lo
pagava anche il CSV, con una colonna `url` che diceva `dequeuniversity.com`
accanto a una colonna `sito` che diceva un altro indirizzo.

**Le due strade del TO-DO erano tre, e la terza è quella presa.** La voce
proponeva di separare i due campi oppure di lasciarne uno solo rinunciando alla
treemap. Rileggendo il codice prima di scegliere sono usciti due fatti che
cambiano la domanda:

- **`params["urls"]` era già la convenzione di fatto**, in quattro moduli su
  nove: `mars_tech` (4 rilievi), `mars_schema` (2), `mars_wapt` (tutti gli
  alert ZAP), `mars_wcag` (il controllo `lang`). La seconda strada avrebbe
  rinunciato a un dato che c'era;
- **un campo scalare è vuoto per costruzione.** `mars_schema` lo dichiarava già
  nel proprio codice: *un rilievo per CONTROLLO, anche quando gli URL sono
  molti; la cardinalità è accoppiata al punteggio in tutta MARS*. Un `url`
  singolo su un rilievo che aggrega venti pagine è vuoto, o è una seconda copia
  di `urls[0]` che diverge da sola.

Da qui: **`params["urls"]` diventa il canone**, `url` viene rinominato
`doc_url` — che è ciò che ha sempre contenuto — e la treemap si colora
sull'unico dato che dice davvero dove.

**Due affermazioni della voce non hanno retto alla lettura del sorgente**, e si
annotano invece di riscriverle: *«axe riporta i nodi per pagina in
`voce["pages"]`, quindi il dato c'è»* — `voce["pages"]` è un **contatore**, e
l'URL veniva buttato prima, in `run_axe`, dove `violazioni.extend()` appiattiva
in una lista sola violazioni che axe restituisce pagina per pagina; e
*«`mars_seo` sa su quale pagina ha guardato»* — lo sapeva e lo dichiarava, ma
**solo a livello d'area**.

**La soluzione.** `Finding.url` → `doc_url`, documentato come il link alla
documentazione della regola e mai una pagina del sito; **`JSON_SCHEMA_VERSION`
1 → 2**, primo scatto da quando la chiave esiste ed esattamente il caso per cui
esiste; `pagine_del_rilievo()` in `mars_core` come **unico lettore** della
convenzione, accanto a chi la documenta, perché due letture separate
divergerebbero in silenzio.

I moduli colmano i buchi dove la pagina la sanno: `run_axe` etichetta ogni
violazione con la sua (il contatore `pages` resta quello che decide il
punteggio — quanto e dove sono due domande diverse e convivono); i **sei
controlli statici** di `mars_wcag`; `mars_seo` dall'URL che **Lighthouse**
dichiara di aver misurato, cioè l'arrivo dopo i redirect e non quello che gli
avevamo chiesto; `tech.canonical.missing`; gli header di `mars_wapt`.

**La treemap si colora**, e le pagine che **nessun rilievo cita restano senza
colore e non diventano verdi**: non tutte le aree guardano tutte le pagine, e
la nota accanto al disegno lo scrive a parole. Il colore non viaggia mai da
solo (invariante 4): il `<title>` del rettangolo e una colonna nuova della
tabella dicono quanti rilievi sono e qual è il peggiore. Nel CSV `url` diventa
`pagine` e `riferimento`.

**Le verifiche.**

- **Nessun punteggio si è mosso**, ed è la prova che la voce ha cambiato ciò
  che il referto *dichiara* e non ciò che *misura*: nel diff dei sei golden non
  compare una sola riga `score` o `penalty` modificata.
- **Il confronto fra due esecuzioni non si rompe**, ed era la domanda da farsi
  prima di alzare `schema_version`: R39 avverte che una migrazione di chiavi è,
  per U7, una sparizione di massa seguita da una comparsa di massa. Qui non lo
  è, perché lo storico registra `key`, `title`, `severity` e `params` e **non
  ha mai registrato `url`**. Verificato eseguendo `compute_delta` fra una riga
  `schema_version: 1` e una `2`.
- **Dodici mutazioni, dodici rosse**, dalla mancata etichetta di pagina in
  `run_axe` alla mappa che tiene la gravità *migliore* invece della peggiore,
  fino alle due colonne CSV scambiate di posto.

**Tre finti non erano fedeli, e la voce li ha scoperti.** `_Risposta` e il
finto `requests.head` dei golden non avevano `.url`, che una
`requests.Response` vera ha **sempre**: sono saliti come `AttributeError`,
cioè esattamente il servizio che un finto fedele rende. E `_violazioni_axe()`
è dichiaratamente «le violazioni come le manda axe», ma sostituisce `run_axe`,
non axe: senza l'etichetta di pagina il golden avrebbe congelato un referto in
cui i rilievi axe non sanno dove stanno mentre in produzione lo sanno.
Corretta tenendo **una regola per pagina** e non la stessa due volte, perché
axe le riporta pagina per pagina e due voci avrebbero spostato la diffusione,
cioè il punteggio.

**Che cosa si sblocca**: il donut della Fase 5 — «senza rilievi / con rilievi /
scartate» — che UPGRADE.md aveva rimandato in attesa di questo dato. È
**R49**, non un di più di R47.

**Le voci anteriori a questa nominano il campo `url`** (U1.5, U1.6, U1.9,
U8.3): erano corrette quando sono state scritte, e si leggono con la rinomina
in mente. Non si riscrivono — un fatto registrato si annota.

---

### R30 — ✅ RISOLTO (2026-08-26): `VectorRetriever` con corpus vuoto
**Il difetto.** `get_scores` promette nella propria docstring che «il
chiamante non deve sapere quale dei due sia attivo». Con un corpus vuoto quella
promessa si rompeva, ed era l'unico punto in cui succedeva. Riprodotto sul
modello vero, non dedotto:

```
proxy char-TFIDF       corpus vuoto -> []
embeddings reali       corpus vuoto -> ValueError: Expected 2D array,
                                       got 1D array instead
```

`mars_semantic` moriva quindi invece di risultare **non misurato**, e un sito
di sole pagine senza testo indicizzabile non è un caso di laboratorio.

**La soluzione.** Una guardia in testa a `get_scores`, che è la funzione che
pubblica la promessa — non nel chiamante — e prima di `model.encode`, così non
si paga nemmeno la codifica della query.

**La guardia copre anche il proxy, che non ne aveva bisogno**, e la ragione è
un precedente di questo stesso progetto. Misurato: sul proxy con corpus vuoto
ogni query restituisce già `[]`, per qualunque testo. Ma quel `[]` è
**emergente** — nasce da tre accidenti indipendenti: `q_norm` che risulta zero
perché nessun n-gramma è in `df`, lo `zip` su due liste vuote, e la
moltiplicazione `[0.0] * 0`. È esattamente la «protezione accidentale» che R6
aveva trovato su `avgdl`, e che un refactor può togliere senza accorgersene.
La guardia rende il contratto esplicito in un punto solo.

**Tre mutazioni, due rosse.** La terza — far valere la guardia per il solo ramo
reale — **non è colta, e non è un test mancante**: non cambia il comportamento
di nessun ingresso, perché il proxy quel `[]` lo produce da sé. È la lezione di
U8.4 in forma affine, e il contratto del proxy resta comunque pinnato da
un'asserzione sua.

**Il finto non era fedele, e il secondo test l'ha scoperto.** Il primo finto di
`cosine_similarity` restituiva liste nude, ma il codice scrive
`self._cosine(...)[0].tolist()`: `AttributeError`. Il test sul corpus vuoto
**passava lo stesso**, perché la guardia corto-circuita prima di arrivarci —
quindi senza il secondo test, quello che verifica che il ramo reale funzioni
ancora *con* documenti, l'infedeltà sarebbe restata invisibile. Il finto imita
ora la forma che il codice usa (`[0]` e poi `.tolist()`) invece di importare
numpy, che non è una dipendenza della suite.

### R42 — ✅ RISOLTO (2026-08-26): la citabilità spariva dalla vista testo
**Il difetto.** `render_text` saltava `mars_citability` nel ciclo delle aree
perché ha un blocco tutto suo in fondo — ma quel blocco è protetto da
`if cit and cit.get("profiles")`. Quando i profili non c'erano, e cioè
**proprio quando qualcosa era andato storto**, la vista testo non stampava
nulla: né il nome dell'area né il motivo. L'HTML invece la mostrava.

Riprodotto sui due rami che lo producono:

```
                     'Citabilità' nel testo    motivo nel testo
area in ERRORE              False                   False
uscita anticipata           False                   False
```

Era **R38 rimasta aperta per una sola area su nove**, e l'ultimo punto di
`render_text` che decideva sul **nome del modulo** invece che sul dato — cioè
l'anti-pattern che R38 aveva tolto per `mars_lexical` e `mars_semantic`.

**La soluzione.** `_ha_blocco_dedicato(area, referto)` legge la **stessa
condizione** che protegge il blocco, in un posto solo: se le due divergessero,
l'area comparirebbe due volte o nessuna — e il secondo caso è esattamente R42.
C'è un test per ciascuno dei due esiti sbagliati.

**I golden non si sono mossi**, ed è corretto: in entrambi i dataset la
citabilità produce i profili, quindi il ramo cambiato non è esercitato da
nessuno dei due. È il caso in cui il golden non può fare da rete e il test
mirato è l'unico presidio.

**Tre mutazioni, tre rosse.**

**Il primo test era troppo largo e ha pescato la cosa sbagliata**: cercava
«Citabilit» in una riga con i due punti, e ha trovato «Citabilità stimata», che
è il **giudizio LLM**. La riga d'area la produce `_riga_area` dall'etichetta
del registro, che comincia col numero d'ordine: è quello a distinguerle.

### R43 — ✅ RISOLTO (2026-08-26): due cose che U2 aveva visto e non corretto
**Il primo difetto: l'icona dichiarava un MIME che non era il suo.** Il file si
chiama `favicon.ico`, ma `file(1)` dice «PNG image data, 32 x 32» — verificato
anche sui byte, che cominciano con `89 50 4e 47` — mentre il referto lo
incorporava come `data:image/x-icon`. I browser lo digeriscono, ma la
dichiarazione era falsa, e in un progetto che misura l'onestà dei referti altrui
è un difetto a casa propria.

**Non si è cablato `image/png`**, che avrebbe soltanto spostato la bugia al
giorno in cui l'icona cambia: il tipo si **legge dai byte**, con una tabella di
firme dichiarata. Byte che non dicono nulla danno
`application/octet-stream` e non un tipo inventato — un data URI *senza* tipo
varrebbe `text/plain`, che nessun browser disegnerebbe.

**Il secondo: il degrado era silenzioso.** `except OSError: return ""` faceva
sparire la riga `<link rel='icon'>` senza traccia: su un checkout parziale il
referto perdeva l'icona e nessuno lo sapeva. Ora chi rende lo dichiara, e la
riga **compare solo quando succede** — un referto sano non guadagna rumore. È la
regola di `wcag.status.no_fixes`: la degradazione si dichiara dove costa
qualcosa, non ovunque per simmetria. C'è un'asserzione anche sul verso opposto,
altrimenti il vincolo si leggerebbe come «la riga c'è sempre».

**Il banco di prova portava la stessa bugia**, e andava tolta da lì per prima:
il golden normalizzava l'icona con `data:image/x-icon;base64,DIGEST` **cablato**
e un test cercava quella stringa. Cablarlo lì avrebbe congelato `x-icon` nel
presidio dopo averlo tolto dal prodotto. Ora il golden normalizza il tipo
qualunque esso sia — il digest resta ciò che rileva un cambio d'icona — e il
test chiede il tipo alla stessa funzione, più un'asserzione che oggi valga
`image/png`: se l'icona cambia, cambia il referto e si deve vedere.

**Cinque mutazioni, cinque rosse**, comprese le due che accendono e spengono
l'avviso nel verso sbagliato.

Il golden si è mosso di **due righe**, i due segnaposto.

### R29 — ✅ RISOLTO (2026-08-26): un audit bloccava l'API per tutti gli altri
**Il difetto.** Tutti e dodici gli handler REST erano `async def`, ma fanno
lavoro **sincrono bloccante**: `crawler.crawl()` con `session.get()` e
`time.sleep()` per il rate limit, `subprocess.run(timeout=120)` per Lighthouse,
il polling di ZAP fino a 900 secondi. In FastAPI un handler `async` gira
**sull'event loop**, quindi un audit fermava l'intero server.

**Riprodotto sull'applicazione vera**, non su un esempio: uvicorn, un
`build_context` sostituito da una pausa di due secondi — interessa il modello
di concorrenza, non la scansione — e due richieste in parallelo, l'audit lento
e una `/users/me` che non fa nulla.

```
                       attesa di /users/me durante l'audit
prima  (async def)     1,71 s   su 2 di audit
dopo   (def)           0,01 s
```

**La soluzione.** Gli otto endpoint d'audit diventano `def`: FastAPI li sposta
da sé su un threadpool. Con loro `/token`, che non fa I/O ma verifica una
password bcrypt — **179 ms di CPU misurati** su questa macchina, tenuti fuori
dall'event loop per la stessa ragione.

**`root` e `/users/me` restano `async`**, e l'asimmetria è deliberata: non
bloccano, e spostarle sul threadpool costerebbe un cambio di contesto per
niente. C'è un'asserzione anche su questo verso, altrimenti il vincolo si
leggerebbe come «mai `async`», che non è.

**Il presidio serve perché il difetto non fa rumore.** Rimettere un `async def`
lascia le risposte **corrette**: cambia solo che il server smette di servire
chiunque altro mentre lavora, e nessun test sul contenuto se ne accorgerebbe.
Un test parametrizzato pretende quindi che gli handler bloccanti non siano
corutine, e un terzo confronta l'elenco scritto a mano con le **rotte che
l'applicazione dichiara**: un endpoint d'audit nuovo che non entrasse
nell'elenco fa fallire, invece di ereditare il vincolo da un'euristica.

**Quattro mutazioni, quattro rosse.**

**Il banco resta nel repository**, come `tools/banco_grafo.py` e per la stessa
ragione: apre una porta e fa girare uvicorn, cioè esce dall'ambiente che la
suite si è data. Dentro `pytest` il vincolo è statico; `tools/banco_concorrenza_api.py`
è ciò che dimostra **perché** conti, ed è documentato in CONTRIBUTING.

### R31 — ✅ RISOLTO (2026-08-26): due diagnosi che dicevano la cosa sbagliata
**Il primo difetto: un file di query senza righe utili era un successo
muto.** `load_queries` restituiva `([], "")`, e `build_context` legge
`list(queries) if queries else default_queries(pages)` — quindi l'audit
ripiegava sulle **query generiche senza dirlo**, e chi aveva passato
`--queries` credeva di aver misurato le proprie. Riprodotto su un file di zero
byte e su uno di sole righe bianche: entrambi `([], '')`.

Il ramo `report_path` della **stessa funzione** un errore lo dava già: erano le
due metà a comportarsi in modo diverso davanti alla stessa condizione. Ora
anche il ramo `path` lo dà, e la CLI esce con il codice d'uso. Una riga utile
in mezzo a righe bianche resta un successo — è la differenza fra «file vuoto» e
«file con dentro poco», e c'è un'asserzione per ciascuno dei tre casi.

**Il secondo: il rifiuto dei classificatori non aveva un ramo suo.**
`interroga()` sollevava un `RuntimeError` con un messaggio chiaro, che
`audit()` catturava nel gruppo generico: la vista compatta diceva «Giudizio non
interpretabile: RuntimeError», impreciso **due volte** — non c'è alcun giudizio
da interpretare, e il nome di un'eccezione Python non dice niente a chi legge
un referto. U1.9 aveva già portato il messaggio nel `detail`; la metà che
mancava è questa.

**Si distingue per tipo e non guardando il messaggio**, ed è la differenza con
C2: là il `TypeError` viene dall'SDK e non lascia altra scelta, qui
l'eccezione è **nostra**. `RichiestaDeclinata` resta sottoclasse di
`RuntimeError` — chi catturava la vecchia continua a catturarla, e il ramo
generico resta una rete — e nasce la chiave `llm.status.refused`, `info` come
gli altri `llm.status.*` perché è un fatto sulla scansione e non si ripara
cambiando il sito. La richiesta è comunque partita, quindi il conto dei
passaggi e la stima dei token viaggiano col rilievo: sono proprio i rami che
falliscono *dopo* l'invio quelli in cui la traccia della spesa non deve
sparire.

**Il ramo generico ha ora un caso suo**, un JSON che non si analizza — senza,
`unreadable` sarebbe uscito dall'elenco dei rami provati e nessuno lo avrebbe
più esercitato.

**E qui il finto ha mostrato un limite.** Il primo tentativo passava la stringa
`"non è JSON"` a `_risposta_llm`, che fa `json.dumps`: il risultato è `"non è
JSON"` fra virgolette, cioè **JSON validissimo** — il modello avrebbe risposto
con una stringa invece che con un oggetto, e `json.loads` non avrebbe
protestato. Serve un secondo aiuto che metta il testo **verbatim**.

**Cinque mutazioni, cinque rosse.**

**Il terzo punto della voce resta fuori**, ed era già fuori dalla lista di
spunta: il tetto alla dimensione della risposta HTTP è l'idea **I14**, non una
correzione.

### R32 — ✅ RISOLTO (2026-08-26): deriva fra documentazione e codice
**Il difetto.** Dieci punti in cui un documento affermava una cosa e il codice
ne faceva un'altra. Nessuno rompeva nulla, ed è il motivo per cui erano
sopravvissuti: **una documentazione sbagliata non fa fallire un test**.

Tutti e dieci sono stati **riverificati sul codice prima di correggerli**, e
tutti e dieci erano reali.

**Otto correzioni di solo testo.**

- Il paragrafo `zap-cli` del README era stantio dal 2026-08-20: prescriveva
  `pip install zapcli` e un `pip uninstall urllib3 requests six` come suo
  prerequisito, mentre dal C9 MARS parla direttamente l'API JSON di ZAP e
  **non serve alcun pacchetto pip**. Contraddiceva un'altra riga del README
  stesso e `requirements-optional.txt`. Riscritto dicendo anche *perché* il
  client ufficiale non si usa — cabla `http://zap/`, che ZAP 2.17 non serve
  più attraverso il proxy — così nessuno lo reintroduca. Con lui è caduto il
  blocco di comandi pericoloso, che ora è nominato solo per avvertire di non
  eseguirlo.
- L'elenco di `AuditRequest` **ometteva `queries` e `llm`**, aggiunti da C5 e
  C2 dopo la stesura della sezione.
- I codici di uscita tacevano che **`2` copre anche l'errore d'uso** —
  l'help della CLI era già corretto, il README no.
- Il **tetto di 15 query** (`DEFAULT_MAX_QUERIES`) era applicato in silenzio e
  non dichiarato da nessuna parte. Ora lo dicono il README e l'help, e l'help
  lo legge **dalla costante** invece di riscriverlo. Il README dichiara anche
  l'asimmetria: via API il tetto non si applica, perché chi chiama l'API sa
  quante query sta mandando.
- `CLAUDE.md` descriveva `market` come «previsto da C1, non ancora usato»,
  mentre `mars_citability` lo legge da C1: ora la riga dice i valori
  riconosciuti e i due piani su cui agisce.
- L'idea **I8** diceva «`tomli` già in `requirements.txt`»: falso, rimosso con
  R11 perché nessun file lo importava — e non serve, `tomllib` è nella stdlib
  da Python 3.11.
- Il commento su `playwright` in `requirements-optional.txt` diceva «non ancora
  integrato: vedi C8», cioè **il contrario del vero** da quando C8 è chiusa.
- La docstring di `/audit/wapt` diceva «ZAP CLI».

**Una docstring che prometteva un numero sbagliato**, e va detto in che verso.
`score_from_alerts` dichiarava una diffusione «da 1x (un URL) a 2x (molti)», ma
la formula è `1 + min(URL, 10)/10`, che su un URL solo dà **1,1x**. Misurato:
un `High` isolato costa 27,5 punti, cioè score **72 e non 75**. La taratura di
C9 è stata misurata su questa formula, quindi **il numero è quello giusto ed è
la docstring a dire il falso**: si allinea il testo, non il comportamento.

**Un'affermazione su ZAP che non regge alla lettura del sorgente**, ed era in
tre posti. «ZAP scrive la confidenza accanto al rischio» — cioè `"High
(Medium)"` — è falso per l'endpoint che MARS usa: in `core/view/alerts` il
campo `risk` vale sempre uno dei quattro `MSG_RISK`, perché `alertToSet` lo
costruisce come `MSG_RISK[getRisk()]`, senza concatenazioni; la confidenza sta
in un campo suo, e `"High (Medium)"` è `riskdesc`, che quell'endpoint non
emette.

Il commento nel modulo era già stato riscritto da U1.6; restavano la docstring
del test e due righe di AS-IS, che davano il caso per **osservato sul daemon
reale**. Quelle due si annotano e non si riscrivono — è un fatto registrato — e
la nota sta ora dentro R4. La docstring del test dice invece la ragione vera
per cui il caso resta coperto: gli alert che **non** nascono dalle regole di
serie — script utente, add-on di terzi, `alert/action/addAlert` — portano il
testo che ne ha scritto l'autore, e lo `split(" ")[0]` è una difesa verso
quelli. Il comportamento non cambia.

**Una sola riga di codice, e non era un'opzione fra le due.** `package.json`
dichiara `lighthouse` fra le dipendenze del progetto, ma `mars_seo` lo cercava
**solo nel PATH**: chi seguiva il `package.json` e lanciava `npm install` senza
`-g` si vedeva dire «Lighthouse non trovato». Delle due strade — correggere il
testo o il codice — si è presa la seconda, perché la stessa cucitura esiste già
per axe (`mars_wcag` legge `node_modules/axe-core`) e perché il ripiego è
gratis.

**E qui la correzione ha prodotto un difetto peggiore di quello che
chiudeva.** La prima stesura cercava il comando con `os.access` sul percorso
composto. Misurato subito dopo:

```
suite: 15 s -> 263 s     Lighthouse lanciato per davvero
golden del referto degradato: 4 rossi   l'area SEO risultava MISURATA
```

La fixture `strumenti_esterni_assenti` neutralizza `shutil.which`, e un secondo
meccanismo le sfuggiva. Su questa macchina `node_modules/.bin/lighthouse` c'è;
su un clone appena fatto no — quindi il verde sarebbe dipeso dalla macchina in
**entrambi i versi**. È la trappola di `node_modules/axe-core` in forma nuova,
e la più insidiosa finora, perché la neutralizzazione esisteva e sembrava
bastare.

La forma giusta è che **anche il ripiego passi da `shutil.which`**, con
`path=`: un solo meccanismo, già presidiato, e per giunta `which` fa il lavoro
migliore — verifica l'eseguibilità e su Windows conosce le estensioni. C'è un
test che presidia il vincolo contando le chiamate, e uno che pinna il valore di
`LIGHTHOUSE_BIN`.

**Quattro mutazioni; la quarta non era colta**: cambiare `node_modules/.bin` in
`node_modules/bin` — la directory che npm **non** usa — passava verde, perché
tutti i test sostituivano la costante con una directory finta e nessuno ne
guardava il valore. È la lezione di U1.4, una costante mai confrontata con sé
stessa, alla terza occorrenza.

**Sei finti di `shutil.which` non erano fedeli alla firma vera**, che ha anche
`path`: sono saliti come `TypeError` appena il codice ha cominciato a usarlo.
Corretti; e il `which` autentico è ora esposto dal `conftest` come
`WHICH_VERO`, perché la fixture è `autouse` e un test che voglia esercitare la
ricerca vera non ha altro modo di riprenderselo — ricostruirla a mano sarebbe
un finto che verifica se stesso.

### C13 — ✅ RISOLTO (2026-08-19 e 2026-08-20): file di progetto mancanti
Repository inizializzato su `main`, con `.gitignore` scritto **prima**
dell'`init`: `.venv/` pesa 5,4 GB e `node_modules/` 162 MB, quindi l'ordine non
era un dettaglio — il repository sta in 708 KB.

`CONTRIBUTING.md` e `CODE_OF_CONDUCT.md` erano **file vuoti**, e un file vuoto
è peggio di uno assente perché chi lo apre non trova nulla. Sono stati scritti;
il primo codifica le regole emerse lavorando, il secondo adatta il Contributor
Covenant 2.1.

`CLAUDE.md` documenta il contratto dei moduli, i principi e le **trappole già
pagate**. **Il contratto documentato è stato verificato contro il codice**, non
scritto a memoria: chiavi del `context`, di pagina e di chunk confrontate a
runtime, zero divergenze in entrambe le direzioni — nulla di documentato che
non esista, nulla di esistente non documentato.

**Diviso il 2026-08-26** in cinque file sotto `.claude/`, uno per argomento,
che `CLAUDE.md` importa con le righe `@`: il testo che arriva nel contesto è lo
stesso, la divisione è stata verificata ricomponendo i pezzi e confrontandoli
con l'originale, byte per byte. Nello stesso passaggio sono uscite dalle
trappole le **tre già presidiate nel punto in cui si sbaglierebbe** — il pin di
`bcrypt` porta la sua ragione accanto a sé in `requirements.txt` (R11);
`soup.title.string` è R6, con `test_crawler_estrae_titoli_difficili` che prova proprio
`<title></title>`; «il `context` una volta sola» è R5, con
`test_audit_full_scansiona_una_volta_sola` che **conta le scansioni** e pretende
1. Il criterio: una trappola resta in CLAUDE.md finché può ancora mordere
codice non ancora scritto; quando un test la coglie, il presidio è il test.

**Le due voci residue erano state lasciate aperte di proposito**: pubblicare un
nome e un indirizzo in un repository è una decisione del titolare, non una
formattazione. `LICENSE` conservava il segnaposto `Copyright [yyyy] [name of
copyright owner]` e nessun sorgente portava una riga di copyright — senza un
titolare indicato una licenza è difficile da far valere.

### C1 + C7 — ✅ FATTI (2026-08-19): profili di citabilità IA e riuso dei risultati
**Il difetto.** `market` veniva passato lungo tutta la catena ma **non era
letto da nessun modulo**: nessun profilo veniva calcolato.

**C7 era il prerequisito ed era davvero una riga**: `context["results"] =
results` **prima** del ciclo, stesso dict popolato mentre il ciclo avanza. Un
modulo di sintesi può così leggere i punteggi delle aree già eseguite senza che
il contratto cambi di una virgola. È la cucitura su cui poggiano poi anche
`mars_llm_judge` e R45.

**Solo 5 aree su 7 producono un punteggio**, quindi C1 deriva due segnali da
`mars_lexical` e `mars_semantic`: *Contenuto in forma di risposta* e
*Recuperabilità ibrida*, cioè il consenso RRF — la misura più vicina a «questo
passaggio verrebbe davvero selezionato da una ricerca ibrida», ed è possibile
solo perché **R10** ha reso i due ranghi commensurabili.

**Il modello è esplicito e discutibile, per scelta**, con la motivazione di
ogni riga scritta accanto. Due scelte di onestà: **Qwen e Kimi hanno pesi
identici**, ed è dichiarato — non ci sono basi pubbliche per differenziarli, e
inventare una differenza per far sembrare la tabella più informata sarebbe
falsa precisione; e **la scala è volutamente grossolana** (0-3), perché una
scala fine suggerirebbe una precisione che non abbiamo.

L'unico moltiplicatore di mercato attivo è l'accessibilità per `eu`, per
l'European Accessibility Act: una ragione **normativa verificabile**, non una
stima.

I segnali non misurati sono **esclusi** dalla media e i pesi si
rinormalizzano: un'area senza strumento non abbassa il profilo, lo rende solo
meno informato. Il disclaimer è stampato **dentro il blocco**, subito sotto i
numeri.

### C2 — ✅ FATTO (2026-08-19): giudizio LLM sulla citabilità
**Il difetto.** Il README prometteva il giudizio LLM, la libreria `anthropic`
era installata, ma la stringa non compariva in nessun file.

Il modulo sottopone al modello i passaggi più recuperabili **secondo la fusione
RRF** — non le prime pagine del sito. È la differenza che rende il giudizio
pertinente: si chiede di valutare ciò che una ricerca ibrida selezionerebbe
davvero.

**Le API sono state usate secondo documentazione, non a memoria**: output
strutturato con uno schema `json_schema`, così il parsing non dipende da come
il modello formatta la prosa; fallback lato server, perché una richiesta
declinata dai classificatori venga rieseguita invece di andare persa.

**È l'unico modulo che spende denaro**, e il controllo è esplicito
(`--llm auto|on|off`). Prima di inviare, il modulo dichiara quanti passaggi e
quanti token partiranno, con la stima marcata come **grossolana**: serve a dare
un ordine di grandezza, non a prevedere la fattura.

**Due difetti trovati collaudando**, entrambi invisibili leggendo il codice:
con `--llm on` e nessuna credenziale, `anthropic.Anthropic()` fa passare la
costruzione e solleva `TypeError` **al momento della richiesta** — non
catturato, l'intero audit sarebbe crashato; e catturandolo genericamente, un
problema di credenziali veniva riportato come «giudizio non interpretabile»,
cioè diagnosi sbagliata sul difetto sbagliato.

**Limite dichiarato, e ancora aperto**: su questa macchina non esiste alcuna
credenziale Anthropic, quindi **la chiamata reale non è mai stata eseguita**.
Tutto il resto è collaudato tramite `context["_anthropic_client"]`, un punto di
iniezione documentato.

### Caricatore di moduli: cache e bytecode stantio (2026-08-20)
**La ragione per intervenire non era la velocità, e va detto.** Misurato: 0,8
ms per audit, nulla accanto a una scansione che dura secondi. Il problema era
che **due chiamate restituivano oggetti diversi**, quindi un `isinstance`
contro una classe del modulo falliva e lo stato di modulo si azzerava a ogni
richiesta.

La cache si invalida sulla firma del file *(mtime in nanosecondi, dimensione)*,
così modificare un plugin continua ad avere effetto **senza riavviare l'API** —
che è la ragione per cui il caricamento a runtime esiste.

**Un difetto più insidioso, trovato dal test di ricaricamento**, che falliva
pur avendo la cache corretta: l'oggetto era nuovo ma **il codice eseguito era
vecchio**. Il bytecode cache di Python valida su *(mtime in **secondi
interi**, dimensione del sorgente)*, quindi un file modificato nello stesso
secondo e della stessa lunghezza — cambiare una cifra, invertire un booleano —
veniva eseguito nella versione precedente, **senza un solo errore**.

Il difetto **precedeva** questa modifica ed era una proprietà di
`exec_module()`, non della cache; ma prometterne l'invalidazione senza
sistemarlo sarebbe stata una promessa falsa. Il caricatore compila ora la
sorgente e la esegue nel namespace del modulo, saltando del tutto il `.pyc`.

### Aiuto della CLI (2026-08-20)
Ogni parametro mostra valori ammessi o un esempio, col default e l'effetto
pratico; i valori di `--market` si **leggono da `MERCATI`**, non si riscrivono,
così non possono divergere. Due avvertenze sono in maiuscolo: `--llm` è
l'unico modulo che comporta una spesa, e `--i-own-this-domain` abilita una
scansione che **invia payload d'attacco**.

**Gli esempi sono verificati da un test**, ed è la lezione di R12 dove il
README documentava comandi che terminavano con un errore: ogni comando
dell'epilogo viene dato in pasto al parser reale, quindi se un flag cambia nome
il test se ne accorge prima di chi legge l'aiuto. Tutti e cinque sono stati
anche **eseguiti**.

### C12 — ✅ FATTO (2026-08-20): la suite di test
**Il difetto.** `pytest` era fra le dipendenze dal primo giorno e **non
esisteva un solo test**: decine di verifiche fatte a mano vivevano solo nello
scrollback della sessione.

**La suite è ermetica per costruzione.** Una fixture `autouse` sostituisce ogni
richiesta di rete con un'eccezione che eredita **sia** da `AssertionError`
**sia** da `requests.RequestException`: un modulo che gestisce correttamente
gli errori di rete la cattura e ripiega — e il percorso di ripiego viene così
esercitato davvero — mentre un modulo che non la gestisce la lascia passare e
il test fallisce rumorosamente. Un solo meccanismo verifica due cose opposte.

Una seconda fixture neutralizza gli strumenti esterni: senza, `mars_seo`
**lanciava Lighthouse per davvero** e la suite passava da 8 secondi a **85**.

**La prova che conta: reintrodurre i difetti.** Sei difetti reali rimessi nel
codice uno per uno — e **tre su sei non venivano rilevati**, che è il risultato
più utile dell'esercizio. I tre test erano vacui e sembravano corretti:

- quello su **R2** misurava la seconda difesa invece della prima:
  `response_model=User` filtra comunque, quindi sarebbe passato anche con la
  dipendenza che restituisce l'oggetto interno. Riscritto sul livello che
  protegge i prossimi endpoint, quelli che qualcuno scriverà dimenticando
  `response_model`;
- quello su **R6** metteva il `None` nelle *pagine*, ma da R10
  `mars_lexical` legge i **chunk**: toccava un campo che il modulo non guarda
  più;
- quello su **R10** verificava separatamente la segmentazione per heading e
  `split_windows`, senza mai provarne **l'innesto** — ed è lì che stava il
  difetto.

Un settimo tentativo non ha fatto fallire nulla, e non era un test debole: la
mutazione toglieva una delle due difese indipendenti del codice, e l'altra
reggeva. Verificato togliendole entrambe.

### C10 — ✅ FATTO (2026-08-20): `mars_tech` copre le quattro aree che promette
**Il difetto.** Il README assegnava all'area 1 «indicizzabilità, robots.txt,
sitemap, crawler IA». Il file ne implementava **una**, in 24 righe: una GET su
robots.txt e un controllo di **sottostringa**.

**I dati vengono dal crawler, non da nuove richieste**: robots.txt e sitemap
erano già stati letti durante la scansione. È lo stesso principio applicato a
`json_ld` e `images` in R11 — si estraggono **dati grezzi**, e il giudizio
resta al modulo.

**robots.txt, tre casi invece di uno.** Il controllo precedente non distingueva
*nessuna regola*, *permesso esplicito* e *blocco esplicito*, che sono cose
opposte. Un blocco è `critico`: nessun'altra area può compensarlo, perché un
crawler escluso non legge nulla.

**`X-Robots-Tag`** agisce come `meta robots` ma viaggia negli header, quindi
non compare nel DOM ed è il modo più facile per escludersi dagli indici senza
accorgersene. Verificato su una pagina dove è l'unica fonte.

**Scala pesata**: `100 - len(issues)*15` dava lo stesso peso a un `noindex`
sull'intero sito e a un `<lastmod>` mancante. Ora quattro gravità, dichiarate
come scelta editoriale.

Misurato su un terzo server di prova, ostile agli assistenti: **tecnica 91/100
→ 17/100**, con la citabilità composita da 70,2 a 50,0.

> *Verbale del 2026-08-19, conservato com'è.* La riga «2/3 pagine con
> 'noindex'» oggi direbbe «escluse dagli indici (noindex o none…)»: la
> formulazione è cambiata con **R25**. Chi confronta il comportamento attuale
> con questo blocco non stia cercando una regressione che non c'è.

### Verifica sistematica dei parametri API (2026-08-20)
Controllo completo che ogni parametro sia passabile **e abbia effetto**, perché
un campo accettato e poi ignorato è peggio di uno mancante. Struttura completa,
comportamento verificato uno per uno con una spia sul `Crawler`, ed effetto
osservabile nel referto via HTTP.

**Un difetto trovato dalla verifica: `max_pages` non limitava le pagine.**
`max_pages=2` restituiva **1 pagina**. `fetch_sitemap()` limitava gli URL
**candidati** a `max_pages`, ma i candidati vengono scartati a valle —
duplicati dopo la normalizzazione, host esterni, vietati da robots.txt, 404,
risorse non HTML: sul sito di prova la sitemap restituiva `/ok1` e `/ok1#top`,
che sono la stessa pagina, e il budget se ne andava in URL che non diventavano
mai pagine. Ora i candidati si raccolgono con un margine dichiarato ed è il
ciclo di `crawl()` a fermarsi.

**Il difetto era invisibile finora perché tutte le prove precedenti usavano
`max_pages` generoso**: chiedere **poco** era il caso che nessuno aveva
provato.

**Parità CLI/API**: ogni flag della CLI ha il suo campo. `--format` e
`--output` restano solo CLI perché riguardano la resa, non l'audit.

### Credenziali nella richiesta API (2026-08-20)
Il campo `credentials` accetta le chiavi degli strumenti opzionali, perché
un'unica istanza dell'API possa servire chiamanti che portano le proprie. Sono
`SecretStr`: pydantic li maschera in log, `repr` e messaggi d'errore, così una
chiave non finisce in un traceback per distrazione; nello schema OpenAPI
risultano `format: password` e **`writeOnly: true`**.

`get_secret_value()` viene chiamato **in un punto solo**, all'ingresso: i
moduli ricevono stringhe e non devono conoscere pydantic.

`hf_token` serve **solo** per i modelli di embedding ad accesso limitato: per
quelli pubblici, incluso il predefinito, è ininfluente.

**Verificato che le chiavi non tornano indietro**: inviata una chiave
riconoscibile, non compare in nessuna risposta. `build_report()` legge chiavi
nominate e non l'intero contesto, quindi il referto non può contenerle **per
costruzione**.

**Il file di esempio contiene segnaposto, e deve restare così**: è versionato
in git, e il suo primo campo è un `_commento` che lo dice a chi lo apre.

**Una deriva della documentazione, trovata verificando.** Il confronto fra il
contratto scritto in `CLAUDE.md` e le chiavi reali del `context` ha rivelato
che `discovery`, `llm` e `queries` non erano mai state documentate. È il
secondo controllo automatico dello stesso tipo, e il primo che trova qualcosa:
vale la pena rifarlo ogni volta che il contesto cambia.

### C9 — ✅ FATTO (2026-08-20): WAPT via ZAP, e la verifica sul daemon reale
**Il difetto.** Dopo R4 il punteggio derivava dagli alert reali, ma il percorso
ZAP non era **mai stato eseguito**.

**Il client ufficiale non funziona con ZAP 2.17**, ed è la verifica sul campo
che ha rovesciato una scelta fatta a tavolino. `python-owasp-zap-v2.4` cabla
l'indirizzo `http://zap/` e **rifiuta ogni altro URL** — c'è un controllo
esplicito nel suo codice, per non far trapelare la chiave API — ma ZAP 2.17
non serve più quell'alias attraverso il proxy. Misurato: il proxy inoltra
regolarmente `example.com`, mentre `http://zap/` chiude la connessione;
nessun alias alternativo funziona.

**Il finto daemon costruito in precedenza non poteva rivelarlo**: rispondeva a
qualunque percorso, mentre quello vero è selettivo. **Un banco di prova troppo
accomodante conferma anche ciò che è sbagliato** — è la frase che il progetto
si è portato dietro da qui in avanti.

Sostituito con un client scritto a mano, una trentina di righe su `requests`:
l'API di ZAP è un GET che restituisce JSON, e farlo a mano costa meno che
dipendere da un wrapper fermo al 2018. Per ZAP **non serve alcun pacchetto
pip**.

**Sequenza eseguita e chiavi confermate** — `pluginId`, `alert`, `risk`, `url`
sono quelle che `score_from_alerts()` attende, «incluso il caso
`"Medium (High)"` con la confidenza fra parentesi». *(Anche questa riga è nel
mirino di R32: vedi la nota in R4.)*

**Un difetto trovato dal finto daemon, prima ancora del vero**: il codice
scriveva `client.core.version()`, ma `core.version` è una **`@property`**, non
un metodo. Con un daemon reale avrebbe sollevato `TypeError`; senza daemon
l'eccezione di connessione arrivava prima e mascherava il difetto.

**Un problema di sicurezza sollevato dal collaudo.** Per verificare ho dovuto
lanciare scansioni, e questo ha reso evidente che `ascan` **invia payload
d'attacco** — XSS, SQL injection, path traversal — contro qualunque URL
ricevesse: contro un sito che non si possiede è un attacco, e a seconda della
giurisdizione un reato. L'active scan richiede ora la **stessa dichiarazione di
proprietà** introdotta da R7 per ignorare robots.txt.

**Il raggruppamento per regola, confermato sul campo**: 27 alert grezzi da una
scansione reale → **4 regole distinte**, con *Missing Anti-clickjacking Header*
su 6 URL contata una volta. Senza raggruppamento quella sola regola sarebbe
costata 60 punti.

**Taratura dei pesi, due punti reali** (entrambi su server locali nostri): sito
mal configurato 58, sito ben configurato 76. La scala ordina correttamente e
lascia spazio sotto per un rilievo *High*. **Due punti non sono una
calibrazione su corpus, e resta scritto così.**

**Un difetto del prodotto trovato mentre si tarava.** Il server di prova
blindato risultava privo di HSTS e CSP che invece impostava: `audit_headers`
usava `requests.head()` **senza controllare lo status code**, e leggeva gli
header di una risposta `501 Unsupported method`. Esistono server reali che
rifiutano HEAD: avrebbero ricevuto un «mancano tutti gli header di sicurezza»,
falso e dato con sicurezza. Il server blindato passa da 60 a **100/100**.

**MARS non avvia il daemon: si collega a uno già in esecuzione.** Questo
risolve per costruzione la voce sui *daemon orfani dopo un timeout*: non c'è
più un processo Java da spegnere.

### C8 — ✅ FATTO (2026-08-20): WCAG reale via axe-core su Chromium
**Il difetto.** `mars_wcag` controllava **due criteri**, e `playwright` era fra
le dipendenze senza essere importato da nessun file.

**Si naviga alle pagine reali, non si inietta l'HTML salvato**, ed è la scelta
di progetto che conta: senza CSS e JavaScript i criteri su contrasto, focus e
contenuto generato darebbero risultati sbagliati, che è peggio che non darli.
La prova lo conferma — su una pagina costruita apposta axe rileva
`color-contrast`, che dall'HTML grezzo sarebbe invisibile.

**Il punteggio raggruppa per regola, non per occorrenza**, ed è un difetto
trovato collaudando: axe restituisce le violazioni pagina per pagina, quindi un
solo problema ricorrente su cinque pagine arrivava cinque volte e affondava il
punteggio da solo. Misurato: la stessa violazione su 1 pagina di 5 dà 86, su
tutte e 5 dà 76 — un fattore due, non cinque.

**L'euristica statica è stata comunque allargata** da due criteri a sette, e
copre *tutte* le pagine mentre axe ne vede le prime. Ogni rilievo **cita il
criterio WCAG** a cui si riferisce, perché un rilievo senza riferimento non è
verificabile da chi lo riceve.

Verificati i casi che distinguono un controllo utile da uno rumoroso: una
tabella `role="presentation"` non conta, un link generico con `aria-label` non
conta, `tabindex="0"` non conta, un campo avvolto da `<label>` è etichettato.

**Il livello è dichiarato** — `WCAG 2.1 A + AA` — perché «accessibile» senza un
livello non significa nulla.

### C6 — ✅ FATTO (2026-08-20): crawling interno quando manca la sitemap
**Il difetto.** Il README diceva «via sitemap o crawling interno», ma senza
sitemap il ripiego era `urls = [self.base_url]`: **una sola pagina**.
`--max-pages 40` su un sito senza sitemap ne produceva **1**, e tutte e sette
le aree giudicavano quell'unica pagina come se fosse il sito.

**Innestata, non affiancata.** La scoperta per link condivide le *stesse*
regole di R7 — robots.txt, filtro same-host, normalizzazione, status e
`Content-Type`, pausa, tetto. Non è una seconda strada che aggira i controlli:
è la stessa strada con una sorgente diversa.

Due dettagli che sarebbe stato facile sbagliare: `urljoin` si applica all'URL
**finale** della risposta e non a quello richiesto, perché dopo un redirect i
link relativi vanno risolti rispetto a dove si è arrivati; e la coda ha un
tetto, perché su un sito grande la scoperta cresce anche quando le pagine
scaricate non crescono più.

**La sitemap resta autoritativa quando c'è**: è la dichiarazione del sito su
cosa vuole far indicizzare. Il crawling per link è il ripiego, non un'aggiunta.

**Il referto dichiara come ha trovato le pagine**, perché cambia il significato
del campione: due pagine dichiarate dal sito non sono la stessa cosa di cinque
raggiunte seguendo la navigazione.

### C5 — ✅ FATTO (2026-08-20): query personalizzate e consenso aggregato
**Il difetto.** La query era **una sola e cablata**, per giunta duplicata in
due file. Era il limite più serio della simulazione RRF: fondere due
classifiche prodotte da **una** query dice pochissimo, mentre la formula del
paper ha senso su un insieme di interrogazioni.

**Le query di default sono nella lingua del sito**, scelte in base
all'attributo `lang` che R9 aveva fatto conservare al crawler: interrogare un
sito inglese in italiano produrrebbe un consenso basso che non dice nulla sul
sito, ma solo che le domande erano nella lingua sbagliata.

**Il rango aggregato si ottiene fondendo le classifiche per query con l'RRF
stesso**: un chunk in alto su più domande è più citabile di uno che vince una
volta sola. I quattro moduli che leggono `rank` continuano a funzionare senza
modifiche e ricevono un dato migliore.

**La metrica ora discrimina davvero.** Sul sito di prova, che documenta l'RRF:

```
come funziona la fusione reciproca dei ranghi   3/3
quando conviene usare una ricerca ibrida        2/3
--- contro le generiche ---
come funziona                                   1/3
chi siamo                                       2/3
```

È la differenza fra misurare il sito e misurare la genericità della domanda.

### C4 — ✅ FATTO (2026-08-20): referto JSON e HTML
**Il difetto.** Il README mostrava `--format html --output report.html`, ma
`argparse` non conosceva né l'uno né l'altro flag: **il comando documentato
terminava con un errore**.

**Il dato prima della presentazione.** `build_report()` produce la struttura
canonica, i renderer ne sono viste. Prima la logica del referto viveva dentro
le `print`, quindi esisteva un solo formato possibile e l'API doveva ripetere
gli stessi calcoli per conto proprio. È il principio 8 applicato a ciò che il
progetto **produce**, non solo a come è scritto — ed è la decisione che ha reso
possibili tutte le fasi UPGRADE.

**Il referto HTML è autoconsistente**, verificato: zero riferimenti esterni,
CSS incorporato, favicon come data URI. Si usa il `.ico` da 2,8 KB e non il
`.png` da 344 KB: il referto deve restare un file solo, ma non a costo di mezzo
megabyte di icona.

**Escape verificato con input ostile**, perché il referto contiene testo preso
dal sito analizzato: provato con `<script>alert(1)</script>` nell'URL e
`<img src=x onerror=...>` fra gli URL saltati.

### C3 — ✅ FATTO (2026-08-19 e 2026-08-20): monitoraggio delle citazioni IA
`mars_citations.py`, deliberatamente **fuori** da `MODULES_REGISTRY` e senza
`audit(context)`: non è un'area di audit, è uno strumento periodico da cron.

Verificato contro la documentazione Anthropic corrente, non a memoria; corretta
la ripresa dopo `pause_turn`, che dalla seconda pausa **sostituiva** il turno
assistente invece di accodarlo, facendo perdere al modello le ricerche già
svolte.

**Il modello OpenAI era corretto, ma la stessa verifica ha trovato un
difetto**: le fonti consultate sono esposte sull'item `web_search_call` **solo
se la richiesta le chiede**, con `include: [...]`. Il codice le leggeva senza
chiederle: `searched_urls` sarebbe rimasto sempre vuoto e `site_consulted`
sempre falso — **una metà della metrica silenziosamente morta**.

**Un difetto grave trovato collaudando.** Senza credenziali lo strumento
**terminava con un traceback** invece del codice di uscita 2 che il README
documenta. La causa è la stessa di C2 — l'SDK Anthropic costruisce il client
senza protestare e solleva `TypeError` alla prima *richiesta* — quindi non era
un caso isolato ma **una classe di difetto**, corretta in entrambi i punti.

**Il caricatore di query è condiviso** (`load_queries` in `mars_core`): le
stesse query che guidano la simulazione RRF devono poter guidare il
monitoraggio delle citazioni, altrimenti i due strumenti misurano cose diverse
e confrontarli non significa nulla.

### Manutenzione (2026-08-19): caricatore di moduli e import pigro
**`load_external_module()` non registrava il modulo in `sys.modules`.**
Qualunque modulo che usi `@dataclass` insieme a `from __future__ import
annotations` falliva il caricamento con `'NoneType' object has no attribute
'__dict__'`, perché `dataclasses` risolve le annotazioni passando da
`sys.modules[cls.__module__]`. L'eccezione veniva inghiottita e l'utente
leggeva «ignorato (file non trovato)» — **con il file presente sul disco**.

È il prerequisito della decisione sullo stile: senza, ogni modulo scritto nel
nuovo stile sarebbe sparito silenziosamente dall'audit.

**Import di `sentence-transformers` reso pigro.** Era eseguito all'import di
`mars_core` e trascinava torch: **3,01 s pagati da chiunque**, compreso
`--embeddings none` che il modello non lo carica mai. Ora costa **0,10 s**.
Entrambe le modalità di `VectorRetriever` verificate — sul parafrasi «un felino
riposa sul sofà» il proxy char-tfidf dà 0.0, gli embedding reali 0.748.

### Decisione (2026-08-19): stile di riferimento del progetto
`mars_citations.py` adottato come modello per il codice nuovo: type hints,
`@dataclass`, I/O separato dalla logica, il dato prima della presentazione,
`__version__`, codici di uscita espliciti, docstring che spiegano il perché.
Registrata come **principio 8**; l'allineamento dei moduli esistenti è **R13**.
Lo stile cambia, la filosofia (principi 1-7) no.
