# MARS Beacon — TO-DO

> Stato rilevato: 2026-08-19; revisione sistematica il 2026-08-20 (voci
> R15-R37, I13-I16); **ripulito il 2026-08-25**, chiudendo le Fasi 4-9.
>
> **Questo file contiene solo ciò che resta da fare.** Il lavoro completato e
> verificato si sposta in [AS-IS.md](AS-IS.md), con difetto, soluzione e prove.
>
> Nella pulizia del 2026-08-25 **ogni voce aperta è stata riverificata sul
> codice**, non riletta: sono uscite **I1** e **I13**, realizzate; **R46** ha
> avuto la sezione che non aveva mai avuto — era dichiarata aperta e non c'era
> nulla da leggere; e **quarantasei riferimenti di riga** sono stati
> rinfrescati, perché dopo sei fasi puntavano quasi tutti altrove. Un puntatore
> che atterra sulla riga sbagliata è peggio di nessun puntatore.
>
> Nella stessa pulizia sono uscite **centoquattro righe che descrivevano
> lavoro concluso**: il riassunto delle nove fasi, le decisioni D1-D4 e la
> recita delle correzioni chiuse. Stanno in [AS-IS.md](AS-IS.md), dove c'era
> già il dettaglio — qui erano una seconda copia, e una seconda copia invecchia
> per conto suo.
>
> **Correzioni chiuse**: R1-R27, R34, R38, R41, R44, R45, R47. **Aperte**:
> R28-R33, R35-R37, R39-R40, R42-R43, R46, R48 e R49 — trovate *adeguando* i
> moduli alle Fasi 1-5, e non corrette lì dentro perché avrebbero spostato
> punteggi o testi dentro un commit che cambiava la forma. **R47 è chiusa il
> 2026-08-26**: ha portato lo schema JSON a `schema_version: 2` e chiuso il
> passo 3 della Fase 8, e ha sbloccato **R49**.
>
> **Programma UPGRADE** (U1-U12), che porta il referto al livello di
> `marsbeacon/`: il piano sta in [UPGRADE.md](UPGRADE.md), il lavoro sul ramo
> `upgrade`, la versione è **2.8.0**. **Le prime nove fasi sono chiuse** —
> le loro voci stanno in [AS-IS.md](AS-IS.md). Con U9 **D4 è ratificata**
> (it/en, livello inferiore dichiarato) e **R44 è chiusa**. La prossima è
> U10, il giudizio LLM multi-modello.
>
> Da U3 in poi vale un vincolo: ogni cambiamento di resa fa fallire i golden
> di `tests/golden/`, e la rigenerazione va sempre seguita dalla **revisione
> del diff**.

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
   L'allineamento dei moduli esistenti era previsto graduale ed è invece
   **completato** (R13, in [AS-IS.md](AS-IS.md)): vale quindi per il codice
   nuovo, non c'è un arretrato da smaltire.

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
La suite esiste — 908 test, vedi [AS-IS.md](AS-IS.md). Restano rifiniture.

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
**Undici sono colmati**, e il documento dichiara in testa quali fasi sono
eseguite: resta il piano, non diventa un registro — è il termine di paragone
rispetto a cui si legge una divergenza.

Le **decisioni D1-D4**, il **quadro delle nove fasi chiuse** — che cosa ha
fatto ciascuna, con quale versione, e che cosa ha lasciato aperto — e le
convenzioni della lavorazione stanno in [AS-IS.md](AS-IS.md). Qui restano solo
le fasi che non sono state fatte.

### Fasi aperte

- [ ] **U10 — Giudizio LLM multi-modello** (G08, Fase 10): ChatGPT, Qwen e
      Kimi accanto a Claude.
- [ ] **U10.1 — I `punti_deboli` del giudizio come rilievi strutturati.**
      U1.9 li ha lasciati fuori di proposito: sono prosa libera, senza chiave
      stabile, diversi a ogni esecuzione (`thinking: adaptive`) e a ogni
      modello, quindi né confrontabili (U7) né traducibili (U9) — e
      `Finding.key` è proprio ciò su cui quelle due fasi poggiano. Il prezzo è
      che l'**unica prosa orientata al miglioramento** dell'intero referto
      (UPGRADE.md: «unica prosa orientata al miglioramento è quella libera del
      giudice LLM») resta fuori dal piano U4 e da ogni esportazione basata sui
      findings. Riaprirla richiede prima **una** delle due cose che oggi
      mancano: *(a)* far etichettare al modello ogni punto debole con una
      delle chiavi che le altre otto aree già producono — allora il rilievo è
      un derivato di quella chiave, con la prosa in `detail` e
      `params["derived"] = True` come in `mars_citability`, e la chiave resta
      stabile perché il modello la sceglie da un vocabolario chiuso invece di
      scriverla; *(b)* il giudizio multi-modello, dove la **concordanza** fra
      modelli è la misura che oggi manca e che renderebbe il rilievo una
      misura invece di un'opinione. Senza (a) o (b) resta prosa, e va lasciata
      dov'è.
- [ ] **U11 — Deliverable rifinito** (G14, G15, Fase 11): CSS di stampa,
      accessibilità delle tabelle, brand nel footer.
- [ ] **U12 — Ancore esterne alla simulazione** (G13, Fase 12) — *opzionale*:
      Brave Search e confronto competitivo.

### U13 — `mars_lexical` e `mars_semantic` non hanno controlli

> **Aggiornamento 2026-08-21.** La metà di *resa* è chiusa da **R38**: il
> referto copre ora tutti e nove gli ambiti, ciascuno con uno stato
> dichiarato, e non afferma più «Analizzato» su aree che non hanno giudicato.
> Resta la metà di *sostanza*, qui sotto: quelle due aree non emettono
> controlli.

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

Le voci chiuse — R1-R27, R34, R38, R41, R44, R45, R47 — stanno in
[AS-IS.md](AS-IS.md) con difetto, soluzione e verifiche, e non si riassumono
qui: **nessuna voce GRAVE resta aperta.**

Le voci **R28-R33** qui sotto vengono da una **revisione sistematica del
2026-08-20** (lettura integrale di codice e documentazione, con verifica
avversariale dei rilievi). Dove scritto *«riprodotto»* il difetto è stato
osservato in esecuzione con la suite/venv; le altre voci sono uscite dalla
verifica e vanno riprodotte prima di correggerle (regola *verificare, non
dedurre*). Ordinate per gravità.

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
`time.sleep()` per il rate-limit ([mars_core.py:626](mars_core.py#L626)),
`subprocess.run(timeout=120)` ([mars_seo.py:467](mars_seo.py#L467)), il polling
ZAP fino a 900 s ([mars_wapt.py:471](mars_wapt.py#L471)). In FastAPI un handler
`async` gira **sull'event loop**: un audit blocca l'intero server per tutti gli
altri client fino a fine scansione.

- [ ] Rendere `def` (non `async def`) gli handler bloccanti — FastAPI li sposta
      su un threadpool — oppure delegare l'esecuzione a `run_in_threadpool`.

### R30 — 🟡 MEDIO: `VectorRetriever` con corpus vuoto
> La prima metà della voce — `httpx` non dichiarato — è **chiusa con U1.9**:
> `requirements-dev.txt` lo dichiara, e la fixture `nessuna_spesa` lo importa
> esplicitamente per bloccare il transport HTTP, quindi non è più una
> dipendenza transitiva. Resta la seconda.

Nel ramo embeddings reali ([mars_core.py:1188](mars_core.py#L1188))
`model.encode([])` seguito da `cosine_similarity`
([:1245](mars_core.py#L1245)) solleva `ValueError`, mentre il proxy
restituisce `[]`: la promessa che «il chiamante non deve sapere quale dei due
sia attivo» si rompe con chunk vuoti, e `mars_semantic` muore invece di
risultare non misurato.

- [ ] Guardia sul corpus vuoto anche nel ramo embeddings reali.

### R31 — ⚪ LIEVE: casi limite e diagnosi imprecise
- **`load_queries` con file vuoto = successo silenzioso.**
  ([mars_core.py:1367](mars_core.py#L1367)) restituisce `([], "")`; l'audit
  ripiega sulle query generiche ([:1527](mars_core.py#L1527)) **senza dirlo**, e
  l'utente crede di aver misurato le proprie. Il ramo `report_path` invece un
  errore lo dà.
- **Rifiuto dei classificatori mal riportato.** `interroga()`
  ([mars_llm_judge.py:174](mars_llm_judge.py#L174)) solleva `RuntimeError` con un
  messaggio chiaro, ma `audit()` lo cattura nel gruppo generico
  ([:323](mars_llm_judge.py#L323)) e stampa solo *«Giudizio non interpretabile:
  RuntimeError»*, perdendo la spiegazione.
- **Nessun tetto alla dimensione della risposta** (vedi anche I14):
  `_get` ([mars_core.py:614](mars_core.py#L614)) scarica l'intero corpo senza
  `stream` né limite; una pagina enorme a 200 viene letta tutta.

- [ ] Errore anche per il file `--queries` senza righe utili.
- [ ] Distinguere il `refusal` nel `mars_llm_judge`. *(Chiuso a metà da U1.9:
      il messaggio arriva nel dato — `llm.status.unreadable` porta in `detail`
      «RuntimeError: richiesta declinata dai classificatori». Le `issues` non
      cambiano, quindi la vista compatta continua a dire «Giudizio non
      interpretabile: RuntimeError», che resta impreciso. Resta da fare: un
      ramo e uno `status` propri per il rifiuto.)*

### R32 — ⚪ LIEVE: deriva fra documentazione e codice
Divergenze verificate (documento → codice). **I riferimenti di riga sono
stati rinfrescati il 2026-08-25**: puntavano tutti altrove dopo le Fasi 4-9, e
un puntatore che atterra sulla riga sbagliata è peggio di nessun puntatore.

- [README.md:177-190](README.md#L177): il paragrafo `zap-cli`
  (`pip install zapcli`, `pip uninstall urllib3/requests/six`) è **stantio** — il
  codice parla direttamente l'API JSON di ZAP dal 2026-08-20 (AS-IS, C9). Contraddice
  [README.md:147](README.md#L147) e `requirements-optional.txt`. Correggere anche la
  docstring di `/audit/wapt` ([mars_api.py:379](mars_api.py#L379): «ZAP CLI»).
- [README.md:330-347](README.md#L330): l'elenco di `AuditRequest` **omette
  `queries`** (e `llm`), aggiunti da C5/C2 dopo la stesura della sezione.
- [README.md:509](README.md#L509): i codici di uscita omettono che `2` copre anche
  l'errore d'uso (l'help della CLI è già corretto).
- [README.md:423](README.md#L423) e help `--queries`: non dichiarano il **tetto di
  15 query** (`DEFAULT_MAX_QUERIES`), applicato in silenzio e non regolabile da CLI
  audit; l'API non lo applica affatto.
- [CLAUDE.md:36](CLAUDE.md#L36): `market` descritto «non ancora usato», ma
  `mars_citability` lo legge da C1.
- [I8](#i8--estrarre-le-euristiche-in-un-file-di-configurazione): «tomli già in
  requirements.txt» è falso — rimosso con R11; usare `tomllib` (stdlib ≥ 3.11).
- [package.json](package.json): dichiara `lighthouse` e `corepack`, ma `mars_seo`
  cerca `lighthouse` solo nel PATH (ignora `node_modules/.bin`); dopo `npm install`
  il referto dice comunque «non trovato».
- [requirements-optional.txt:20](requirements-optional.txt#L20): il commento su
  `playwright` dice «non ancora integrato: vedi C8», ma C8 è chiuso e axe-core è
  integrato — afferma il contrario del vero.
- [mars_wapt.py:218](mars_wapt.py#L218): la docstring promette diffusione
  «da 1x», ma la formula ([:290](mars_wapt.py#L290)) su un URL solo dà 1.1x (un
  `High` singolo → score 72, non 75). Poiché la taratura di C9 è stata misurata sul
  codice attuale, allineare la docstring.
- **«ZAP scrive la confidenza accanto al rischio»: la frase non regge alla
  lettura del sorgente**, ed è in tre posti. In `core/view/alerts` il campo
  `risk` vale sempre uno dei quattro `MSG_RISK`, perché `AlertAPI.alertToSet`
  lo costruisce come `MSG_RISK[alert.getRisk()]`, senza concatenazioni; la
  confidenza sta in un campo suo, `confidence`, e `"High (Medium)"` è
  `riskdesc`, che i referti tradizionali compongono e l'endpoint non emette.
  Il commento in `mars_wapt` è già riscritto da U1.6; restano la docstring di
  `test_zap_la_confidenza_non_e_una_gravita`
  ([tests/test_core.py:1129](tests/test_core.py#L1129)) e
  [AS-IS.md:221](AS-IS.md#L221), che dà il caso per **osservato** sul daemon
  reale. Prima di correggere quella riga va ricontrollato da dove venisse
  l'osservazione — un referto, `riskdesc`, un campo diverso: è un fatto
  registrato, e si annota, non si riscrive. Il comportamento in ogni caso non
  cambia: lo `split(" ")[0]` resta come difesa verso gli alert che non nascono
  dalle regole di serie (script utente, add-on di terzi,
  `alert/action/addAlert`).

- [ ] Correggere ciascuna riga sopra (il testo, non il comportamento, tranne
      dove indicato un'opzione di codice).

### R33 — ⚪ LIEVE: rifiniture dei test
- **Seconda fixture di controlli scritta a mano.**
  [tests/test_report.py:489](tests/test_report.py#L489) (`CONTROLLI`) ricalca
  a mano le voci di `audits` che `mars_seo.estrai_audit` produce, e da U1.7 è
  ferma a cinque campi su otto: invecchia da sola, senza che nulla diventi
  rosso. Candidata a sparire dentro **U2**, che congela la resa con i golden.
- **Dipendenza dalla cwd.** [tests/test_cli.py](tests/test_cli.py) (righe 22, 100,
  107) e [tests/test_api.py:320](tests/test_api.py#L320) usano percorsi relativi:
  eseguendo `pytest` da un'altra directory si hanno 1 failure e 4 errori, e
  `test_url_obbligatorio` **passa vacuamente** (attende rc 2 da argparse, ma da cwd
  sbagliata rc 2 arriva dal file non trovato).
- **`test_html_autoconsistente` troppo debole.**
  [tests/test_report.py:164](tests/test_report.py#L164) cerca riferimenti esterni
  solo negli attributi `src`/`href` quotati: un `url(https://…)` nel `<style>`,
  `@import` o `srcset` sfuggirebbero, lasciando verde una regressione che rompe
  l'autoconsistenza.

- [ ] Fissare la cwd al repo (fixture/`chdir`) e rendere non-vacuo il test URL.
- [ ] Estendere il controllo a `url(`, `@import`, `srcset` (escludendo `data:`).

### R35 — 🟡 MEDIO: i due recuperatori indicizzano contenuti diversi
*(trovata misurando, chiudendo R23 il 2026-08-20)*

`mars_lexical` costruisce il corpus con **heading + testo** del chunk
([mars_lexical.py:29](mars_lexical.py#L29)); `mars_semantic` indicizza il
**solo testo** ([mars_semantic.py:149](mars_semantic.py#L149)). I due
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

`direttive_robots()` ([mars_tech.py:171](mars_tech.py#L171)) legge ora tutte le
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

### R39 — 🟡 MEDIO: quattro difetti di `mars_wapt` trovati adeguandolo a U1.6
*(trovati leggendo il modulo riga per riga per U1.6, il 2026-08-24. Nessuno è
stato corretto lì: tutti cambierebbero punteggi o testi, cioè
esattamente ciò che un adeguamento di forma non deve fare.)*

- **`alertRef` non viene mai raggiunto, e tre difetti diversi si fondono in
  uno.** La catena di raggruppamento è
  `pluginId or alertRef or name or alert or "?"`
  ([mars_wapt.py:229](mars_wapt.py#L229)), ma `pluginId` è **sempre** presente
  e non vuoto nel JSON di ZAP (`AlertAPI.alertToSet` lo mette con
  `String.valueOf`): `alertRef` è codice morto. Conseguenza reale: la regola
  CSP 10038 emette `10038-1`, `10038-2` e `10038-3` — alert distinti, con
  testi e soluzioni proprie — che oggi diventano **una** voce e **una**
  penalità. Correggerlo è una **ritaratura di C9**, non un adeguamento: la
  cardinalità dei gruppi *è* il punteggio, e ogni sito che viola quella regola
  ne perderebbe il triplo. Porta con sé anche una **migrazione di chiavi**
  (`sec.zap.10038` → `sec.zap.10038_1/_2/_3`), che per il confronto fra due
  esecuzioni (U7) è una sparizione di massa seguita da una comparsa di massa.
  U1.6 conserva già il dato che serve a farlo: `params["alert_refs"]`.
- **`chiave_esterna()` non è iniettiva, e su ZAP il caso è reale.**
  `chiave_esterna("-1") == chiave_esterna("1") == "1"`: gli alert manuali, da
  script e da `alert/action/addAlert` hanno `pluginId = -1` e finiscono tutti
  su `sec.zap.1`, indistinguibili da un plugin `1`. Il dato fedele resta in
  `params["rule"]`, e `params["key_source"]` dice da quale campo la chiave sia
  nata — solo `pluginId` la rende stabile, perché un `name` viene dai
  `Messages.properties`, cambia fra due release ed è **localizzato**.
- **ZAP raggiunto e fallito non lascia traccia nel referto.** Se `run_zap`
  restituisce `None` ([mars_wapt.py:574](mars_wapt.py#L574)) c'è solo un
  `print`, e il referto dichiara «HTTP-Headers, superficie» senza mai dire che
  un daemon c'era e non ha portato a termine la scansione. È lo stesso difetto
  di onestà che R38 ha chiuso altrove.
- **`audit_headers` perde il primo errore.** Se HEAD solleva e GET risponde
  ≥400, `errore` viene riassegnato a `None`
  ([mars_wapt.py:523](mars_wapt.py#L523)) e la diagnosi diventa `HTTP 500`,
  perdendo il `ConnectionError` che spiegava il primo tentativo.

- [ ] Raggruppare per `alertRef`, ritarando le penalità e dichiarando la
      migrazione di chiavi.
- [ ] Dire nel referto che ZAP era raggiungibile e ha fallito, invece di
      ripiegare in silenzio.
- [ ] Conservare entrambe le diagnosi in `audit_headers`.

### R40 — 🟡 MEDIO: sei difetti di `mars_seo` trovati adeguandolo a U1.7
*(trovati leggendo il modulo e il sorgente di Lighthouse 13.4.1 per U1.7, il
2026-08-24. Nessuno corretto lì: tutti sposterebbero punteggi, conteggi o
testi.)*

- **Un solo audit in errore fa buttare via gli altri dieci.** Lighthouse
  azzera il peso degli audit non applicabili, informativi e manuali prima di
  scriverlo nel LHR, ma **non** quello di un audit andato in `error`
  (`core/scoring.js`): il suo `score: null` sopravvive al filtro e annulla il
  punteggio dell'intera categoria. `riassumi` esce allora al primo `if`
  ([mars_seo.py:390](mars_seo.py#L390)) con «Lighthouse non ha calcolato la
  categoria SEO», **senza mai chiamare `estrai_audit`** — mentre nel LHR ci
  sono dieci controlli perfettamente misurati. Vanno distinti i due casi: non
  calcolabile *e* nulla di leggibile, contro non calcolabile *ma* dieci audit
  su undici validi. Attenzione: aggiungere `audits` a quel ramo cambia anche
  la resa, perché l'HTML mostra l'elenco dei controlli **al posto** dei rilievi
  ([mars_report.py:2201](mars_report.py#L2201)).
- **«da verificare a mano» detto a un `notApplicable`.** Lighthouse usa
  `failureTitle` solo quando `score < 0.9`, quindi un controllo non misurato
  porta il titolo del **successo**: la issue di una pagina senza canonical
  recita «da verificare a mano: Il documento ha un elemento `rel=canonical`
  valido», che afferma il contrario del vero due volte. U1.7 ha corretto il
  **titolo del rilievo** (prefissi «Non applicabile a questa pagina» / «Da
  verificare a mano» / «Controllo non eseguito da Lighthouse»); le `issues`
  sono rimaste com'erano perché cambiarle è una regressione di testo.
- **`MODI_NON_MISURATI_VOCE` e `LH_MODI_NON_MISURATI` divergono di
  proposito**, e la divergenza va tolta con una misura, non per simmetria.
  La voce si ferma a `("manual", "notApplicable")`
  ([mars_seo.py:44](mars_seo.py#L44)); `mars_core` comprende anche
  `informative` ed `error`. Un `informative` ha `score: 1` per costruzione,
  quindi oggi è contato fra i **superati**; un `error` fra i **falliti**.
  Allargare la tupla della voce sposterebbe `passed`/`failed`/`manual`, la
  riga «N superati, M falliti» del referto e la ripartizione delle issues.
- **Tre buchi in `_descrivi_item`** ([mars_seo.py:236](mars_seo.py#L236)): il
  `source` che è un `NodeValue` invece di una stringa — è il caso più pesante
  della categoria, `is-crawlable` bloccato da un `<meta robots noindex>`,
  dove [:250](mars_seo.py#L250) cerca `url`/`value` e non `selector`; gli item
  `{index, line, message}` di `robots-txt`; i `subItems` di `hreflang`.
  Correggerli cambia il testo delle issues.
- **`explanation`, `displayValue` e `warnings` di Lighthouse sono ignorati.**
  *(Aggiornato il 2026-08-25: `description` **non** lo è più — U3.2 la porta in
  `detail` e `_senza_link_markdown` la ripulisce dai link Markdown, che è la
  funzione che questa voce dava per mancante. Restano gli altri tre, verificato:
  zero occorrenze in `mars_seo.py`.)* Sono i testi che dicono *perché* un
  controllo è fallito. Da notare `warnings` di `is-crawlable`: un audit che
  **passa** pur avendo qualcosa da dire.
- **Il parametro `score` di `severita_lighthouse` non viene mai letto**
  ([mars_core.py:381](mars_core.py#L381)): la funzione decide su modo e peso.
  Non è morto per svista — è il chiamante che deve filtrare i superati, e
  senza quel filtro un sito perfetto produrrebbe nove `warning` — ma un
  parametro inerte in una firma pubblica invita a crederlo significativo.
  Renderlo significativo vuol dire introdurre `SEV_OK`, che oggi nessun
  modulo usa: è una decisione della fase che renderà i controlli superati.

- [ ] Distinguere «categoria non calcolabile» da «categoria non calcolabile ma
      dieci audit su undici misurati».
- [ ] Allineare il testo delle issues dei non applicabili a quello dei
      rilievi, rigenerando i golden.
- [ ] Chiudere i tre buchi di `_descrivi_item`.

### R42 — 🟢 LIEVE: la citabilità sparisce dalla vista testo quando fallisce
*(trovato censendo i consumatori per U1.8, il 2026-08-24)*

[mars_report.py:1391](mars_report.py#L1391) salta `mars_citability` nel ciclo
delle aree, perché ha un blocco tutto suo in fondo — ma quel blocco è protetto
da `if cit and cit.get("profiles")`. Quando i profili non ci sono, e cioè
proprio quando qualcosa è andato storto, **la vista testo non stampa nulla**:
né il nome dell'area, né il motivo. Misurato: con l'area in errore,
`'plugin rotto' in testo` → `False` e `'Citabilit' in testo` → `False`.
L'HTML invece la mostra (quadrante, scheda d'area, sezione dedicata).

Sono i due rami dell'uscita anticipata («Richiede le altre aree») e dell'area
fallita. È **R38 ancora aperto per una sola area su nove**, ed è anche
l'ultimo punto di `render_text` che decide sul **nome del modulo** invece che
sul dato — l'anti-pattern che R38 ha tolto per `mars_lexical`/`mars_semantic`.

Da U1.8 il dato canonico dice la verità (`cit.status.no_results`,
`cit.status.error`) mentre la vista testo continua a tacerla.

- [ ] Far decidere la vista sul dato, non sul nome: stampare la riga d'area
      quando il blocco dedicato non può girare. Rigenerando i golden (U2).

### R43 — ⚪ LIEVE: due cose che U2 ha visto e non ha corretto
*(trovate costruendo i golden, il 2026-08-24)*

- **La favicon dichiara un MIME che non e' il suo.** `file favicon.ico` dice
  `PNG image data, 32 x 32`, mentre `_favicon_data_uri`
  ([mars_report.py:1482](mars_report.py#L1482)) la incorpora come
  `data:image/x-icon;base64,…` e la docstring parla di «.ico (2,8 KB)». I
  browser lo digeriscono, ma la dichiarazione è falsa. Correggerla cambia il
  golden HTML, quindi va fatta con la sua rigenerazione.
- **Il degrado della favicon è silenzioso.** `except OSError: return ""` fa
  sparire la riga `<link rel='icon'>` senza traccia: su un checkout parziale
  il referto perde l'icona e nessuno lo saprebbe. Nel golden il fatto è
  rilevato (il digest sparisce, il diff lo mostra), ma in produzione no.

- [ ] Dichiarare il MIME vero, o convertire davvero l'icona in .ico.
- [ ] Dire nel referto quando l'icona non è stata incorporata.

### R46 — ⚪ LIEVE: lo sforzo è editoriale e non scala col difetto
*(lasciata aperta da U4, il 2026-08-24; la sezione è stata scritta il
2026-08-25 — fino ad allora la voce era **dichiarata aperta e non c'era nulla
da leggere**, citata solo di sfuggita in [AS-IS.md](AS-IS.md))*

`SFORZO` ([mars_remediation.py:135](mars_remediation.py#L135)) è una mappa
`chiave -> minuti|ore|giorni` scritta a mano: dipende dal **tipo** di
controllo e non da quante volte il difetto ricorre. «1 immagine senza `alt`» e
«400 immagini senza `alt`» hanno la stessa chiave, quindi lo stesso sforzo —
`giorni` in entrambi i casi, che sul primo è una sopravvalutazione e sul
secondo forse una sottovalutazione.

Il dato per fare meglio **c'è già**: ogni rilievo porta nei `params` il proprio
conteggio di istanze (`immagini`, `campi`, `pagine`, `nodes`, `n`), ma i nomi
sono **diversi per area**, scelti da chi ha scritto il modulo. Renderli
canonici è il prerequisito, e non è gratis: significa o un nome comune in più
accanto a quelli parlanti, o una mappa chiave → nome del conteggio, cioè un
secondo catalogo da tenere allineato ai moduli.

Finché quel conteggio non è canonico lo sforzo **resta editoriale, ed è
dichiarato tale**: il referto scrive `sforzo: giorni` e non «3 giorni», e la
differenza è voluta — un ordine di grandezza è una stima, un numero sembra una
misura.

- [ ] Decidere se il conteggio delle istanze diventa canonico, e con quale
      nome. È il prerequisito, non un dettaglio dell'implementazione.
- [ ] Solo dopo: far scalare lo sforzo col conteggio, e continuare a
      dichiararlo come stima.

### R48 — ⚪ LIEVE: del JavaScript la suite verifica il testo, non il gesto
*(trovata chiudendo U8.4, il 2026-08-25)*

`REFERTO_JS` è presidiato da quattro test, e tutti guardano la **stringa**:
che non contenga origini esterne, che non contenga dati del sito, che
compaia solo dove c'è un grafo, che chiami `removeAttribute("hidden")` e
`setAttribute("tabindex", "0")`. Nessuno lo **esegue**. Una mutazione che
sposti i nodi nel punto sbagliato, o che evidenzi i vicini di un altro nodo,
passerebbe tutti e quattro.

Il comportamento si verifica con `tools/banco_grafo.py`, che fa girare lo
script su un DOM finto in `node` — sul vero SVG prodotto da `mars_report`,
non su uno scritto a mano — e controlla nove comportamenti. È un presidio
reale (quattro mutazioni del JavaScript su quattro lo fanno diventare rosso)
ma **non automatico**: nessuno lo lancia al posto di chi modifica il codice.

Perché non è già nella suite: servirebbe `node` — e con esso, per farlo
bene, `jsdom`. È la trappola di `node_modules/axe-core` in un'altra forma:
un test che gira qui e non su un clone appena fatto rende la suite
**dipendente dalla macchina**, e la regola del progetto è che `pytest` non
esca dal proprio ambiente. Un `pytest.mark.skipif` su `node` assente sarebbe
onesto, ma un test che sulla macchina di chi non ha node è sempre verde
perché sempre saltato è un presidio che non presidia.

Tre strade, in ordine di costo:

- ~~conservare il banco di prova nel repo e documentarlo in CONTRIBUTING~~
  — **fatto** con `tools/banco_grafo.py`: non è automatico, ma non è più
  un'esecuzione persa. È il minimo, non la soluzione;
- **portare le funzioni pure in Python** — la disposizione ad anelli è
  aritmetica, e calcolarla in `mars_report` la renderebbe testabile con la
  suite di sempre, lasciando al JS il solo compito di applicarla;
- **`jsdom` in `requirements-dev`** e un test marcato, accettando che la
  suite dipenda da npm.

La seconda è la sola che porti il comportamento dentro `pytest` senza
allargare l'ambiente, ed è anche quella che riduce il JavaScript.

- [ ] Scegliere fra le due rimaste, e nel frattempo non toccare
      `REFERTO_JS` senza rilanciare `tools/banco_grafo.py`.

### R49 — ⚪ LIEVE: il donut delle pagine è rimasto al taglio di ripiego
*(sbloccata chiudendo R47, il 2026-08-26)*

La Fase 5 di UPGRADE.md prevedeva un donut dello stato pagine col taglio
**senza rilievi / con rilievi / scartate**, e ha ripiegato su *scansionate vs
scartate* dichiarando il motivo: «finché i Finding non portano `url`
valorizzati dai moduli» ([UPGRADE.md:489](UPGRADE.md#L489)). Ora quel dato
c'è — `params["urls"]`, letto da `pagine_del_rilievo()` — e la stessa mappa
che colora la treemap (`gravita_per_pagina`, [mars_report.py:573](mars_report.py#L573))
darebbe il taglio previsto senza calcolare nulla di nuovo.

Resta il caveat che R47 ha reso esplicito, e che qui pesa più che sulla
treemap: **«senza rilievi» non vuol dire «a posto»**. Lighthouse misura una
pagina sola, axe le prime del campione, e un donut che mettesse quelle pagine
in un settore chiamato «senza rilievi» affermerebbe ciò che nessuno ha
misurato — su un disegno che si legge come una ripartizione esaustiva, cosa
che la treemap non è. O il settore si chiama diversamente, o servono tre
settori invece di due.

- [ ] Decidere il taglio e come si chiamano i settori, poi renderlo.
      Rigenerando i golden.

---

## Idee

Proposte di sviluppo, non promesse dal README. Da valutare, **non** da eseguire
senza conferma: alcune allargano il perimetro del progetto.

> **I1** (audit differenziale) e **I13** (test diretti del `Crawler`) sono state
> **realizzate** e sono uscite di qui il 2026-08-25 — la prima da U7, in una
> forma diversa da quella proposta, la seconda dalle regressioni scritte per
> R15-R24. Le due voci stanno in [AS-IS.md](AS-IS.md) con la differenza fra ciò
> che era stato proposto e ciò che è stato fatto.

### I2 — Modalità CI con exit code e soglie
`--fail-under 70` → exit code ≠ 0. Rende MARS utilizzabile come gate in una
pipeline. Costo: una decina di righe.

### I3 — Sensibilità del parametro `k` dell'RRF
`k=60` è hardcoded ([mars_core.py:1536](mars_core.py#L1536)) — è il valore del
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
([mars_seo.py:21](mars_seo.py#L21)) e nella stessa risposta JSON restituisce
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
