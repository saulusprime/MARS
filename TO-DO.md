# MARS Beacon — TO-DO

> Stato rilevato: 2026-08-19; **rivisto il 2026-08-20** (revisione sistematica
> di codice e documentazione: nuove voci R15-R35, I13-I16). R15-R26 sono
> già chiuse — con esse tutte le voci GRAVI; restano aperte R27-R37.
> Riferimento: `README.md` (premesse di progetto) vs. codice presente in root.
>
> **Questo file contiene solo ciò che resta da fare.** Il lavoro completato e
> verificato si sposta in [AS-IS.md](AS-IS.md), con difetto, soluzione e prove.
>
> Dal 2026-08-21 è aperto il **programma UPGRADE** (U1-U12), che porta il
> referto al livello di `marsbeacon/`: il piano sta in [UPGRADE.md](UPGRADE.md),
> le voci aperte qui sotto, il lavoro sul ramo `upgrade`.

---

## Filosofia di sviluppo da preservare

Prima di ogni intervento, questi sono i principi che il codice attuale esprime.
**Nessuna voce di questo TO-DO deve violarli.**

1. **Algoritmi core implementati nativamente, senza dipendenze pesanti.**
   Crawler, BM25 (`LexicalRetriever`), proxy vettoriale char-TFIDF
   (`VectorRetriever`) e la fusione RRF sono scritti a mano in `mars_core.py`.
   Non sostituirli con `rank_bm25`, `scikit-learn` o simili: sono il valore
   didattico e il cuore del progetto.
2. **Degradazione graduale, mai fallimento.** Ogni dipendenza esterna
   (Lighthouse, ZAP, sentence-transformers, Anthropic) è *opzionale*: se manca,
   si usa un fallback e l'audit prosegue. Non introdurre dipendenze obbligatorie.
3. **Moduli plugin auto-rilevati a runtime.** `load_external_module()` carica
   `mars_<area>.py` dal filesystem. Il contratto è uno solo:
   `audit(context: dict) -> dict`, con `score` / `issues` opzionali.
   Aggiungere un'area = aggiungere un file + una riga in `MODULES_REGISTRY`.
4. **Un file per area, header e licenza identici.** Moduli piccoli, leggibili,
   auto-contenuti.
5. **CLI-first; l'API è un secondo consumatore degli stessi moduli.**
   `mars_audit.py` e `mars_api.py` condividono `MODULES_REGISTRY`,
   `load_external_module()` e la costruzione del `context`.
6. **Onestà metodologica.** Il README dichiara esplicitamente che i profili di
   citabilità IA sono "stime euristiche dichiarate, non comportamento
   documentato dai vendor". Ogni punteggio nuovo deve dichiarare la sua natura.
7. **Interfaccia utente in italiano**, codice e identificatori in inglese.
8. **Stile di riferimento: `mars_citations.py`** *(deciso il 2026-08-19)*.
   Il modulo più recente è anche il meglio costruito, e da qui in avanti è il
   modello da seguire per il codice nuovo:
   - `from __future__ import annotations` e **type hints** sulle firme
     pubbliche;
   - `@dataclass` per le strutture dati **interne** a un modulo. Il
     `context` e i dizionari che vi stanno dentro (pagine, chunk) restano
     invece **dict**: attraversano il confine dei plugin, e imporre classi
     di `mars_core` costringerebbe ogni modulo esterno a importarle,
     contro il principio 3. Deciso applicando R13 il 2026-08-19;
   - **I/O separato dalla logica**: le funzioni pure (`evaluate_answer`,
     `overall_rate`, `norm_host`) sono testabili senza rete né chiavi API —
     è ciò che ha permesso di verificarne il comportamento in pochi secondi;
   - **il dato prima della presentazione**: si costruisce un `payload` dict e
     i renderer (`render_text`, `render_json`) lo consumano. È esattamente
     l'architettura richiesta da **C4**, qui già funzionante;
   - **`__version__`, `--version`, codici di uscita espliciti** (0/1/2) e
     `--fail-under` per l'uso in pipeline (l'idea **I2**, già realizzata);
   - docstring che spiegano **il perché**, non il cosa.

   Questo **non** annulla i principi 1-7: `mars_citations.py` li rispetta
   tutti (nessuna dipendenza nuova, provider opzionali che degradano con un
   messaggio chiaro, messaggi in italiano). Lo stile cambia, la filosofia no.
   L'allineamento dei moduli esistenti è graduale — vedi **R13**.

---

## Completamento

Funzionalità **promesse dal README ma assenti nel codice**, in ordine di
distanza tra promessa e realtà.

### C4 — voce residua
Il referto JSON e HTML è fatto — vedi [AS-IS.md](AS-IS.md). Resta un punto che
non dipende dal codice.

- [ ] **Verificare sul campo il giudizio LLM (C2)** con una credenziale
      Anthropic reale: la chiamata non è mai stata eseguita, solo simulata.
      Il referto JSON ora conserva per intero motivazione, punti forti e
      deboli, quindi è il formato giusto per controllarne l'esito.

### C12 — voci residue
La suite esiste — 146 test, vedi [AS-IS.md](AS-IS.md). Restano rifiniture.

- [ ] Misurare la copertura (`pytest --cov`) per trovare i rami mai eseguiti:
      oggi si sa quali difetti sono protetti, non quanto codice è toccato.
- [ ] `mars_citations.py` non ha test propri: è uno strumento a sé, e le sue
      funzioni pure (`evaluate_answer`, `overall_rate`, lo storico JSONL) sono
      facilmente verificabili.
- [ ] Eseguire la suite in una pipeline, non solo a mano.

---

## Programma UPGRADE — il referto al livello di marsbeacon

Il piano completo sta in [UPGRADE.md](UPGRADE.md): 15 divari individuati
confrontando sul codice `MARS/` (la versione definitiva) e `marsbeacon/` (il
riferimento per la reportistica), ciascuno verificato in modo avversariale.
Qui restano solo le **voci aperte**, una per fase; il dettaglio non si duplica.

Convenzioni della lavorazione, dal documento: un commit per fase, bump di
`__version__` (minor per fase), `pytest` verde senza rete e `flake8 .` a zero
prima del commit, golden rigenerati **intenzionalmente** dalla Fase 2 in poi.
Il lavoro sta sul ramo **`upgrade`**.

### Decisioni ratificate (2026-08-21)

Registrate qui perché non vengano prese "di fatto" scrivendo codice.

| | decisione | esito |
|---|---|---|
| **D1** | JavaScript nel referto | **Sì**, vanilla inline, progressive enhancement: l'SVG statico resta la base, nessuna origine esterna, `prefers-reduced-motion` spegne le animazioni. Adottata **solo dalla Fase 8**; fino ad allora ogni sezione nuova è statica. Ribalta il vincolo "NESSUNO SCRIPT" di `mars_report.py` e il test che lo presidia |
| **D2** | Scala di severità canonica | **Sì**, quattro livelli `critical`/`warning`/`info`/`ok`. La granularità in più delle tre scale esistenti si conserva nel **peso**, non in livelli extra |
| **D3** | Pesi del punteggio complessivo | **Sì**: aree misurate a peso 1.0, Recuperabilità-RRF e "In forma di risposta" a 1.5; **esclusi** Citabilità (sintesi derivata: conterebbe due volte) e Giudizio LLM (opzionale e a pagamento). Rinormalizzazione sulle aree presenti |
| **D4** | Lingue | **Rinviata**: la i18n esce dal piano delle fasi e diventa la voce U9 qui sotto. Il referto resta in italiano finché non la si affronta |

### Fasi

### U1 — Modello dati dei rilievi (G01) — prerequisito di U2, U3, U4, U5, U7

Dataclass `Finding` e scala di severità unificata. La dataclass **non**
attraversa il confine dei plugin: i moduli restituiscono `findings` come lista
di dict, accanto alle `issues` attuali, che restano (vista compatta legacy).

Nove commit, non uno: così ogni passo chiude una voce con le sue verifiche e
AS-IS conserva nove misure invece di un riassunto.

- [x] **U1.1** — `mars_core`: `SEV_*`, `WEIGHTS`, `AREA_PREFIX`, `Finding`,
      `normalizza_severita`, `severita_lighthouse`, `chiave_esterna`.
- [ ] **U1.2** — `build_report`: `findings` nell'area, sintesi di
      `<prefisso>.status.error`, test di contratto esteso a **tutti e nove** i
      moduli. Il consumatore **prima** dei produttori: `build_report` copia una
      lista chiusa di chiavi, quindi senza questo passo i commit successivi
      consegnerebbero una chiave che nessuno legge e nessun test vede.
- [ ] **U1.3** — `mars_tech`. È il banco di prova del modello: unica scala
      propria, due gravità calcolate a runtime, punteggio accoppiato alla
      scala, e la rete di test più fitta del progetto.
- [ ] **U1.4** — `mars_schema`. Prima area senza gravità propria, primo caso di
      aggregazione per chiave.
- [ ] **U1.5** — `mars_wcag`. Due origini nello stesso modulo (axe +
      editoriale), il marcatore `surface`, l'impact assente.
- [ ] **U1.6** — `mars_wapt`. Scala ZAP + header editoriali, tre rami d'uscita,
      **nessuna rete di test esistente**: il commit si porta i propri. Qui si
      raccoglie anche `solution` di ZAP, che oggi viene scartata e serve a U3.
- [ ] **U1.7** — `mars_seo`. L'unico che richiede di arricchire il dato a
      monte: `estrai_audit` deve conservare `score`, `scoreDisplayMode` e il
      `weight` di `auditRefs`, che oggi **non viene mai letto**.
- [ ] **U1.8** — `mars_citability`. Modulo di sintesi: dipende da come emettono
      gli altri sei. Ogni suo rilievo porta `params["derived"] = True`.
- [ ] **U1.9** — `mars_llm_judge`: solo `llm.status.*`. Fuori dai sei di
      UPGRADE.md, ma senza l'area 9 resta muta in ogni vista basata sui
      findings.
- [ ] Bump `__version__` a **2.1.0** e badge nel README a fine fase.
### Altre fasi

- [ ] **U2 — Golden test dei formati** (G10, Fase 2). Rete di sicurezza per
      tutte le fasi successive: ogni cambiamento di resa passa da una
      rigenerazione intenzionale con revisione del diff.
- [ ] **U3 — Testi `fix` ed `example` per ogni controllo** (G03, Fase 3).
- [ ] **U4 — Piano di remediation ordinato** (G02, Fase 4) — il cuore
      dell'adeguamento.
- [ ] **U5 — Punteggio complessivo, hero, ancore stabili** (G07, G11, Fase 5).
- [ ] **U6 — Formati Markdown e CSV** (G04, Fase 6).
- [ ] **U7 — Riproducibilità e storia** (G09, G06, Fase 7):
      `schema_version`, parametri RRF e soglie nel referto; delta fra due
      esecuzioni e storico.
- [ ] **U8 — Analisi della superficie** (G12, Fase 8): profondità, treemap,
      grafo dei link (qui entra D1), matematica dell'RRF, `pages[]`.
- [ ] **U9 — i18n del referto** (G05, Fase 9) — *rinviata da D4*. Cataloghi e
      `--lang` per it/en/fr/de/es, riusando i cataloghi già scritti in
      marsbeacon dove i controlli coincidono. Ridurre a it/en è legittimo ma
      va **dichiarato** come livello inferiore rispetto al riferimento.
      Prerequisito implicito: `key` e `params` dei `Finding` (U1).
- [ ] **U10 — Giudizio LLM multi-modello** (G08, Fase 10): ChatGPT, Qwen e
      Kimi accanto a Claude.
- [ ] **U11 — Deliverable rifinito** (G14, G15, Fase 11): CSS di stampa,
      accessibilità delle tabelle, brand nel footer.
- [ ] **U12 — Ancore esterne alla simulazione** (G13, Fase 12) — *opzionale*:
      Brave Search e confronto competitivo.

### U13 — `mars_lexical` e `mars_semantic` non hanno controlli

*(trovata mappando i moduli per U1, il 2026-08-21)*

Le due aree **non emettono un solo rilievo**: producono metriche
(`answer_shaped_ratio`, ranghi, consenso) ma nessun controllo con un esito.
Nel riferimento `lex.` e `sem.` sono **47 chiavi su 122** — titoli duplicati,
contenuti sottili, freschezza, fonti citate.

Il divario non è di formato ed **U1 non lo chiude**: adeguare il modello dati
non fa comparire rilievi che non esistono. Conseguenza da conoscere prima di
U5, non da scoprire dopo: hero, tile per gravità, CSV, piano di remediation e
delta descriveranno **sette aree su nove**, e le due che alimentano i quadranti
derivati non contribuiranno un solo `Finding`.

- [ ] Decidere se colmarlo, e con quali controlli. Candidati dal riferimento:
      `lex.title.dup`, `lex.words.thin`, `sem.fresh.very_stale`,
      `sem.refs.missing`. È materia di una fase a sé, non di una riga.

---

## Correzioni

Le R1-R14 sono chiuse, e con esse **R15** (URL malformato che faceva cadere
l'audit), **R16** (mojibake sui siti UTF-8 senza charset), **R17** (redirect
mai rivalidati), **R18** (punteggiatura che escludeva le parole da BM25) e
**R19** (segnali di pagina che gonfiavano `answer_shaped_ratio`), **R20** (axe
che fabbricava un 100/100) e **R21** (referto che non distingueva un controllo
di superficie da una misura piena) e **R22** (esecutore di moduli non robusto
ai plugin che rompono) e **R23** (query che non sopravvivevano a un retriever
caduto, e ranghi a informazione zero) e **R24** (casi limite del crawler sugli
URL) e **R25** (la direttiva robots `none` mai vista) e **R26** (`alt=""`
contato come violazione, `delay` mai passato ad axe, riparsing dell'HTML),
tutte il 2026-08-20: difetto, soluzione e verifiche in
[AS-IS.md](AS-IS.md). **Nessuna voce GRAVE resta aperta.**

Le voci **R27-R33** qui sotto vengono da una **revisione sistematica del
2026-08-20** (lettura integrale di codice e documentazione, con verifica
avversariale dei rilievi). Dove scritto *«riprodotto»* il difetto è stato
osservato in esecuzione con la suite/venv; le altre voci sono uscite dalla
verifica e vanno riprodotte prima di correggerle (regola *verificare, non
dedurre*). Ordinate per gravità.

### R27 — 🟡 MEDIO: il timeout ZAP non ferma la scansione
Allo scadere di `ZAP_TIMEOUT_SCAN`, `_attendi()`
([mars_wapt.py:160](mars_wapt.py#L160)) esce dal ciclo senza fermare nulla, e
`run_zap` non chiama mai `spider/action/stop` né `ascan/action/stop` —
`ZapClient` non li espone nemmeno. La scansione (anche l'**active scan**, che
invia payload d'attacco) prosegue nel daemon, mentre il referto
([:261](mars_wapt.py#L261)) dichiara *«scansione interrotta dal timeout»*:
l'interruzione riguarda solo l'attesa di MARS, non ZAP.

- [ ] Esporre e chiamare gli endpoint di stop nel ramo di timeout, così il
      messaggio del referto corrisponda al fatto.

### R28 — 🟡 MEDIO: `mars_citations`, scritture e monitoraggio non misurato
- **`OSError` non gestita su `--output`/`--history`.** L'`open` di `--output`
  ([mars_citations.py:564](mars_citations.py#L564)) e `append_history`
  ([:404](mars_citations.py#L404), invocata a [:559](mars_citations.py#L559)) non
  gestiscono `OSError`: un percorso non scrivibile termina con traceback ed
  **exit 1** — lo stesso codice di `--fail-under`, quindi una pipeline scambia il
  crash per «sotto soglia». Con `--history` il crash avviene **prima** di
  stampare il referto: i risultati (pagati in chiamate API) vanno persi.
- **Monitoraggio non misurato = `rate 0.0`.** Se tutte le query di un provider
  falliscono, `run_monitor` scrive `"rate": 0.0`
  ([mars_citations.py:348](mars_citations.py#L348)) — un *«0% di citazioni»* per
  un dato mai misurato — indistinguibile da uno 0% reale nel referto e nello
  storico JSONL.

- [ ] Gestire `OSError` con un codice di uscita distinto da `--fail-under`, e
      scrivere il referto prima dello storico.
- [ ] Distinguere «0 su 0» (non misurato) da uno 0% reale, come già fa `overall_rate`.

### R29 — 🟡 MEDIO: gli endpoint `async` bloccano l'event loop
Tutti gli handler REST sono `async def` (12 in [mars_api.py](mars_api.py)) ma
fanno lavoro **sincrono bloccante**: `crawler.crawl()` con `session.get()` e
`time.sleep()` per il rate-limit ([mars_core.py:227](mars_core.py#L227)),
`subprocess.run(timeout=120)` ([mars_seo.py:32](mars_seo.py#L32)), il polling ZAP
fino a 900 s ([mars_wapt.py:168](mars_wapt.py#L168)). In FastAPI un handler
`async` gira **sull'event loop**: un audit blocca l'intero server per tutti gli
altri client fino a fine scansione.

- [ ] Rendere `def` (non `async def`) gli handler bloccanti — FastAPI li sposta
      su un threadpool — oppure delegare l'esecuzione a `run_in_threadpool`.

### R30 — 🟡 MEDIO: dipendenze non dichiarate e un caso limite del retriever
- **`httpx` non dichiarato.** [tests/test_api.py](tests/test_api.py) usa
  `TestClient`, che richiede `httpx`/`httpx2`: nessun `requirements*.txt` lo
  dichiara (verificato). Oggi la suite passa solo perché `httpx` arriva come
  dipendenza transitiva di `anthropic`/`sentence-transformers`
  (requirements-optional): chi installa solo core+dev non può far girare i test.
- **`VectorRetriever` con corpus vuoto.** Nel ramo embeddings reali
  ([mars_core.py:575](mars_core.py#L575)) `model.encode([])` + `cosine_similarity`
  sollevano `ValueError`, mentre il proxy restituisce `[]`: la promessa che «il
  chiamante non deve sapere quale dei due sia attivo» si rompe con chunk vuoti, e
  `mars_semantic` muore invece di risultare non misurato.

- [ ] Dichiarare `httpx` in `requirements-dev.txt`.
- [ ] Guardia sul corpus vuoto anche nel ramo embeddings reali.

### R31 — ⚪ LIEVE: casi limite e diagnosi imprecise
- **`load_queries` con file vuoto = successo silenzioso.**
  ([mars_core.py:698](mars_core.py#L698)) restituisce `([], "")`; l'audit ripiega
  sulle query generiche ([:842](mars_core.py#L842)) **senza dirlo**, e l'utente
  crede di aver misurato le proprie. Il ramo `report_path` invece un errore lo dà.
- **Rifiuto dei classificatori mal riportato.** `interroga()`
  ([mars_llm_judge.py:143](mars_llm_judge.py#L143)) solleva `RuntimeError` con un
  messaggio chiaro, ma `audit()` lo cattura nel gruppo generico
  ([:214](mars_llm_judge.py#L214)) e stampa solo *«Giudizio non interpretabile:
  RuntimeError»*, perdendo la spiegazione.
- **Nessun tetto alla dimensione della risposta** (vedi anche I14):
  `_get` scarica l'intero corpo senza `stream` né limite; una pagina enorme a 200
  viene letta tutta.

- [ ] Errore anche per il file `--queries` senza righe utili.
- [ ] Distinguere il `refusal` nel `mars_llm_judge`.

### R32 — ⚪ LIEVE: deriva fra documentazione e codice
Divergenze verificate (documento → codice):
- [README.md:123-143](README.md#L123): il paragrafo `zap-cli`
  (`pip install zapcli`, `pip uninstall urllib3/requests/six`) è **stantio** — il
  codice parla direttamente l'API JSON di ZAP dal 2026-08-20 (AS-IS, C9). Contraddice
  [README.md:96](README.md#L96) e `requirements-optional.txt`. Correggere anche la
  docstring di `/audit/wapt` ([mars_api.py:383](mars_api.py#L383): «ZAP CLI»).
- [README.md:252-268](README.md#L252): l'elenco di `AuditRequest` **omette
  `queries`** (e `llm`), aggiunti da C5/C2 dopo la stesura della sezione.
- [README.md:369](README.md#L369): i codici di uscita omettono che `2` copre anche
  l'errore d'uso (l'help della CLI è già corretto).
- [README.md:337](README.md#L337) e help `--queries`: non dichiarano il **tetto di
  15 query** (`DEFAULT_MAX_QUERIES`), applicato in silenzio e non regolabile da CLI
  audit; l'API non lo applica affatto.
- [CLAUDE.md:34](CLAUDE.md#L34): `market` descritto «non ancora usato», ma
  `mars_citability` lo legge da C1.
- [TO-DO.md:143](TO-DO.md#L143) (I8): «tomli già in requirements.txt» è falso —
  rimosso con R11; usare `tomllib` (stdlib ≥ 3.11).
- [package.json](package.json): dichiara `lighthouse` e `corepack`, ma `mars_seo`
  cerca `lighthouse` solo nel PATH (ignora `node_modules/.bin`); dopo `npm install`
  il referto dice comunque «non trovato».
- [requirements-optional.txt:20](requirements-optional.txt#L20): il commento su
  `playwright` dice «non ancora integrato: vedi C8», ma C8 è chiuso e axe-core è
  integrato — afferma il contrario del vero.
- [mars_wapt.py:49-50](mars_wapt.py#L49): la docstring promette diffusione «1x per
  un URL», ma la formula ([:74](mars_wapt.py#L74)) dà 1.1x (un `High` singolo →
  score 72, non 75). Poiché la taratura di C9 è stata misurata sul codice attuale,
  allineare la docstring.

- [ ] Correggere ciascuna riga sopra (il testo, non il comportamento, tranne
      dove indicato un'opzione di codice).

### R33 — ⚪ LIEVE: rifiniture dei test
- **Dipendenza dalla cwd.** [tests/test_cli.py](tests/test_cli.py) (righe 22, 100,
  107) e [tests/test_api.py:278](tests/test_api.py#L278) usano percorsi relativi:
  eseguendo `pytest` da un'altra directory si hanno 1 failure e 4 errori, e
  `test_url_obbligatorio` **passa vacuamente** (attende rc 2 da argparse, ma da cwd
  sbagliata rc 2 arriva dal file non trovato).
- **`test_html_autoconsistente` troppo debole.**
  [tests/test_report.py:137](tests/test_report.py#L137) cerca riferimenti esterni
  solo negli attributi `src`/`href` quotati: un `url(https://…)` nel `<style>`,
  `@import` o `srcset` sfuggirebbero, lasciando verde una regressione che rompe
  l'autoconsistenza.

- [ ] Fissare la cwd al repo (fixture/`chdir`) e rendere non-vacuo il test URL.
- [ ] Estendere il controllo a `url(`, `@import`, `srcset` (escludendo `data:`).

### R34 — 🟡 MEDIO: i titoli di sezione italiani scambiati per domande
*(trovata misurando, chiudendo R19 il 2026-08-20)*

`_interrogativo()` ([mars_semantic.py:58](mars_semantic.py#L58)) accende il
segnale quando un termine interrogativo apre il testo. Su un **titolo di
sezione** questo produce falsi positivi su tutta una classe di intestazioni
standard, che sono nomi e non domande. Misurato:

| titolo | segnale acceso | è una domanda? |
|---|---|---|
| `Chi siamo` | sì | no |
| `Dove siamo` | sì | no |
| `Come raggiungerci` | sì | no |
| `Cosa facciamo` | sì | no |
| `Quali servizi offriamo` | sì | no |
| `How it works` | sì | no |
| `What we do` | sì | no |
| `Come funziona il servizio?` | sì | **sì** |

Non è il difetto di R19 — quello era l'attribuzione dei segnali di pagina ai
chunk, ed è chiuso — ma la stessa metrica ne resta gonfiata: su una pagina con
`Chi siamo` e una vera FAQ, `answer_shaped_ratio` dà 0,50 dove l'onesto è 0,25.
`Chi siamo` sta su quasi ogni sito italiano, quindi la classe non è marginale.

L'ipotesi da verificare (non da applicare a intuito): **un titolo è una domanda
quando è punteggiato come tale**. Le intestazioni che iniziano con un
interrogativo senza `?` sono etichette di sezione; le FAQ vere il punto
interrogativo ce l'hanno quasi sempre. Costo: qualche falso negativo sulle FAQ
scritte senza `?`. Da misurare su contenuto reale prima di decidere, ed
eventualmente da applicare **solo** al segnale «titolo interrogativo», non a
quello sul corpo del testo.

### R35 — 🟡 MEDIO: i due recuperatori indicizzano contenuti diversi
*(trovata misurando, chiudendo R23 il 2026-08-20)*

`mars_lexical` costruisce il corpus con **heading + testo** del chunk
([mars_lexical.py:29](mars_lexical.py#L29)); `mars_semantic` indicizza il
**solo testo** ([mars_semantic.py:117](mars_semantic.py#L117)). I due
recuperatori ordinano quindi le stesse unità partendo da contenuti diversi.

**R10** aveva lavorato perché i due ranghi si riferissero alle **stesse
unità** — è la condizione perché l'RRF significhi quello che il README dice.
Nessuno ha poi controllato che leggessero lo **stesso contenuto** di quelle
unità. Misurato, con `servizi` presente solo nell'heading:

```
lessicale  -> matched = True    (indicizza heading + testo)
vettoriale -> matched = False   (indicizza il solo testo)
```

L'heading è spesso la forma in cui la domanda è posta — è la ragione per cui
`mars_lexical` lo include, scritta nel suo stesso commento. Il recuperatore
vettoriale ne è cieco, quindi su un sito con FAQ nei titoli i due sono in
disaccordo per costruzione, e il consenso RRF ne esce depresso per una ragione
che non riguarda il sito.

La correzione probabile è una riga (indicizzare `heading + testo` anche nel
vettoriale), ma **cambia tutti i punteggi vettoriali**: va misurata prima e
dopo su un sito reale, non applicata a intuito.

### R36 — 🟡 MEDIO: `nosnippet` è invisibile, ed è la direttiva che conta di più
*(trovata misurando, chiudendo R25 il 2026-08-20)*

`direttive_robots()` ([mars_tech.py:123](mars_tech.py#L123)) legge ora tutte le
direttive, ma `controlla_indicizzabilita` ne giudica due: `noindex` e
`nofollow`. Restano mute proprio quelle che governano **l'estrazione del
testo**, cioè il meccanismo con cui un assistente cita una pagina. Misurato,
contro un riferimento senza direttive che vale 94:

| direttiva | punteggio | rilievo |
|---|---|---|
| `nosnippet` | 94 | nessuno |
| `max-snippet:0` | 94 | nessuno |
| `noarchive` | 94 | nessuno |
| `unavailable_after: 2020-01-01` | 94 | nessuno |

Una pagina con `nosnippet` è regolarmente indicizzata e **non può essere
citata**: nessun frammento del suo testo può comparire in una risposta. Per uno
strumento che misura la citabilità è la direttiva più rilevante delle tre, e
oggi non produce nulla. `unavailable_after` scaduto equivale a `noindex`, ma
richiede di confrontare una data.

- [ ] Rilievo per `nosnippet` / `max-snippet:0` (gravità alta: colpisce
      direttamente la citabilità, che è l'oggetto del progetto).
- [ ] Valutare `noarchive` (lieve) e `unavailable_after` scaduto (come
      `noindex`, previo confronto di date).

### R37 — 🟢 LIEVE: il prefisso per agente dell'X-Robots-Tag viene ignorato
*(trovata misurando, chiudendo R25 il 2026-08-20)*

`X-Robots-Tag` ammette un prefisso che limita la direttiva a un solo crawler:
`X-Robots-Tag: googlebot: noindex`. `direttive_robots()` lascia il prefisso fra
i token e la direttiva viene contata come se valesse per tutti — comportamento
ereditato dalla ricerca per sottostringa, non introdotto da R25. Misurato:

```
X-Robots-Tag: noindex             -> 54  [critico] 1/1 pagine escluse dagli indici
X-Robots-Tag: googlebot: noindex  -> 54  [critico] 1/1 pagine escluse dagli indici
X-Robots-Tag: gptbot: noindex     -> 54  [critico] 1/1 pagine escluse dagli indici
```

I tre casi sono diversi e ricevono lo stesso giudizio. Il secondo esclude
Google ma **non** GPTBot, ClaudeBot o PerplexityBot: per la citabilità IA è
molto meno grave del primo. Il terzo è invece mirato esattamente ai crawler
che l'area 1 già enumera in `CRAWLER_IA`, e meriterebbe di essere segnalato
per nome.

- [ ] Separare il prefisso per agente e graduare la gravità: tutti i crawler,
      solo i motori tradizionali, o proprio quelli IA.

---

## Idee

Proposte di sviluppo, non promesse dal README. Da valutare, **non** da eseguire
senza conferma: alcune allargano il perimetro del progetto.

### I1 — `--baseline` e audit differenziale
Salvare il report JSON (**C4**) e confrontare due esecuzioni:
`python3 mars_audit.py <url> --baseline report-precedente.json`, con output
"+12 SEO, −5 WCAG, 2 nuovi problemi". Trasforma MARS da fotografia in
strumento di monitoraggio, riusando ciò che C4 costruisce già.

### I2 — Modalità CI con exit code e soglie
`--fail-under 70` → exit code ≠ 0. Rende MARS utilizzabile come gate in una
pipeline. Costo: una decina di righe.

### I3 — Sensibilità del parametro `k` dell'RRF
`k=60` è hardcoded ([mars_core.py:171](mars_core.py#L171)) — è il valore del
paper Cormack 2009, ma il progetto è *anche* didattico: esporre `--rrf-k` e
mostrare come cambia il consenso al variare di `k` è esattamente il tipo di
intuizione che il README vuole trasmettere. Quasi gratis da implementare.

### I4 — Ablation lessicale vs. vettoriale
Riportare, accanto al risultato fuso, quanto ciascun retriever contribuisce al
Top-N: quanti chunk vengono solo da BM25, quanti solo dal vettoriale, quanti dal
consenso. È la dimostrazione empirica del perché l'ibrido batte i singoli —
la tesi centrale del paper citato in bibliografia.

### I5 — Crawling concorrente
`ThreadPoolExecutor` sul fetch delle pagine (stdlib, nessuna dipendenza nuova).
Con `--max-pages 40` e timeout di 10s il crawl seriale può richiedere minuti.
Da fare **dopo** R7, perché il rate limiting va rispettato anche in concorrenza.

### I6 — Cache HTTP su disco
Cache dei fetch (chiave: URL + ETag/Last-Modified) sotto `.mars-cache/`.
Rende iterabile lo sviluppo dei moduli senza martellare il sito bersaglio — e
rende i test di **C12** riproducibili.

### I7 — Vista comparativa multi-sito
`python3 mars_audit.py --compare a.com b.com c.com` con tabella affiancata.
Utile per benchmark competitivo, ed è il caso d'uso naturale dei profili di
citabilità (**C1**).

### I8 — Estrarre le euristiche in un file di configurazione
Pesi degli score, soglie, elenchi di crawler IA e termini "answer-shaped" sono
oggi costanti sparse nel codice. Un `mars_weights.yaml` (o `.toml`, con `tomli`
già in `requirements.txt`) li renderebbe ispezionabili e regolabili senza
toccare il codice — rafforzando il principio 6.

### I9 — Report HTML con visualizzazione RRF
Il grafico più espressivo è il *rank shift*: due colonne (BM25, vettoriale)
collegate da linee ai rispettivi ranghi post-fusione. Mostra a colpo d'occhio
il consenso. Da fare in SVG inline, senza librerie.

*Aggiornata il 2026-08-20:* il rifacimento in stile Lighthouse ha portato nel
referto una sezione **Simulazione RRF** con il consenso aggregato, la tabella
per query e il passaggio più recuperabile, più un quadrante *Recuperabilità* —
e ha dimostrato che l'SVG inline calcolato in Python basta, senza script né
librerie. Il *rank shift* vero e proprio resta però da fare: oggi si legge
**quanto** i due recuperatori concordano, non **su cosa** divergono.

### I10 — Modulo performance (Core Web Vitals)
Lighthouse viene già invocato per la categoria `seo`
([mars_seo.py:16](mars_seo.py#L16)) e nella stessa risposta JSON restituisce
`performance`, `accessibility` e `best-practices`: sono dati **già scaricati e
buttati via**. Un `mars_perf.py` costerebbe pochissimo e la categoria
`accessibility` di Lighthouse darebbe una controprova a `mars_wcag.py`.

### I11 — Verifica dei tipi Schema.org
`mars_schema.py` oggi controlla solo che il JSON-LD sia sintatticamente valido.
Verificare `@type` contro i tipi che gli assistenti IA usano davvero
(`FAQPage`, `HowTo`, `Article`, `Organization`, `BreadcrumbList`) e la presenza
delle proprietà richieste. Legame diretto con la citabilità (**C1**).

### I12 — Dockerfile
Il progetto ha prerequisiti pesanti e conflittuali: Node + Lighthouse + Chrome,
ZAP, Playwright, torch. Il README dedica un intero paragrafo a risolvere
conflitti di pacchetti a mano. Un'immagine con tutto preinstallato
eliminerebbe la classe di problemi — a costo di un file, senza toccare il
codice.

### I13 — Test diretti del `Crawler`
*(proposta dalla revisione del 2026-08-20)* Nessun test esercita `robots()`,
`can_fetch()`, `fetch_sitemap()`, `estrai_link()` o `crawl()`: `conftest.py`
azzera `Crawler` e `test_api` usa doppi. Le trappole documentate in
[CLAUDE.md](CLAUDE.md) (`parse([])` sul ramo robots-mancante, `crawl_delay` che
non eredita da `*`) e diverse voci R15-R24 qui sopra sono **senza regressione**.
Sono testabili offline montando un adapter `requests` finto sulla `session` del
crawler (pattern verificato funzionante durante la revisione) o con un server
HTTP locale, senza toccare la rete. È il complemento naturale delle voci
residue di **C12**.

### I14 — Tetto alla dimensione della risposta HTTP
*(proposta dalla revisione del 2026-08-20)* `_get` scarica l'intero corpo senza
`stream` né limite, e `crawl()` conserva la pagina sia parsata sia grezza in
`pages[url]["html"]`: un endpoint che serve a 200 un file enorme o uno stream
senza fine viene letto per intero (il `timeout` di `requests` copre solo
l'attesa fra i byte). Un tetto su `Content-Length` o la lettura a chunk con
limite (5-10 MB), oltre il quale la pagina va in `skipped` con motivo
dichiarato, chiude la classe. Legata a **R15-R17** (robustezza del crawler).

### I16 — Scegliere il dispositivo di Lighthouse (`--form-factor`)
*(proposta il 2026-08-20, portando i controlli SEO nel referto)*
Lighthouse misura per `mobile` come predefinito, e MARS lo dichiara nel
referto. PageSpeed Insights espone invece entrambe le viste, e un referto
`desktop` puo' dare punteggi diversi sugli stessi contenuti. Un flag
`--form-factor {mobile,desktop}` — passato a Lighthouse come
`--preset=desktop` — permetterebbe di confrontare like-for-like con il
referto che il committente ha sotto gli occhi. Costo: un flag, un campo
nel corpo API, e la propagazione fino a `mars_seo`.

### I15 — Elisione italiana nella tokenizzazione
*(proposta dalla revisione del 2026-08-20, misurata chiudendo R18)*
`tokenize()` toglie la punteggiatura di **confine**, quindi `l'azienda` resta
un token solo e una query per `azienda` non lo incontra. In italiano
l'elisione è ovunque (`dell'anno`, `un'idea`, `all'inizio`), quindi la perdita
non è marginale.

La correzione ovvia — spezzare su ogni non-parola, `re.findall(r"\w+", …)` —
è stata **misurata e scartata** chiudendo R18: manda in pezzi
`info@esempio.it` (tre token), `3,14` (due) e `COVID-19`, e riempie l'indice
di frammenti (`l`, `dell`, `un`, `s`) che gonfiano la lunghezza dei documenti,
cioè la grandezza su cui BM25 normalizza. Serve qualcosa di più mirato:
spezzare **solo** sull'apostrofo, e solo quando la parte a sinistra è un
articolo o una preposizione elidibile — cioè un piccolo elenco dichiarato,
non una regola generale. Da valutare con una misura, non a intuito.
