# MARS Beacon — TO-DO

> Stato rilevato: 2026-08-19
> Riferimento: `README.md` (premesse di progetto) vs. codice presente in root.
>
> **Questo file contiene solo ciò che resta da fare.** Il lavoro completato e
> verificato si sposta in [AS-IS.md](AS-IS.md), con difetto, soluzione e prove.

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
   - `@dataclass` per le strutture dati, invece di dizionari anonimi;
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

### C1 — Profili di citabilità IA e indice composito per mercato — *mancante al 100%*
Il README promette: *"Dai punteggi di area deriva i profili di citabilita' per
assistente IA (Claude, ChatGPT/Perplexity, Qwen, Kimi) con indice composito
pesato per mercato (`--market`)"*.

Nel codice `market` viene passato lungo tutta la catena
([mars_audit.py:84](mars_audit.py#L84), [mars_api.py:179](mars_api.py#L179))
ma **non è mai letto da nessun modulo**. Nessun profilo viene calcolato.

> Da non confondere con `mars_citations.py` (**C3**, già scritto): quello
> *misura* le citazioni reali interrogando gli assistenti; questo le *stima*
> dai punteggi d'area, senza rete e senza chiavi API.

- [ ] Creare `mars_citability.py` che rispetti il contratto `audit(context)`.
- [ ] Definire una matrice di pesi per assistente × area (7 aree) e per mercato
      (`global`, `eu`, `us`, `cn`, …), come tabella dichiarativa in testa al file.
- [ ] Ricevere i punteggi di area già calcolati: serve che `run_audit()` passi
      i `results` parziali nel `context` (vedi **C7**).
- [ ] Stampare nel report finale un blocco `Profili di citabilità` con il
      composito per assistente.
- [ ] Marcare esplicitamente in output che sono stime euristiche (principio 6).

### C2 — Giudizio LLM sulla citabilità ("modalità auto" con `ANTHROPIC_API_KEY`) — *mancante al 100%*
Il README: *"per il giudizio LLM sulla citabilità (attivo di default in modalità
'auto' quando la chiave `ANTHROPIC_API_KEY` è presente)"*.

`anthropic>=0.120` è in `requirements.txt` ed è installato nel venv, ma la
stringa `anthropic` non compare in nessun file `.py` del progetto.

- [ ] Creare `mars_llm_judge.py`, attivo solo se `os.environ.get("ANTHROPIC_API_KEY")`
      e se `import anthropic` riesce; altrimenti no-op silenzioso (principio 2).
- [ ] Aggiungere il flag `--llm {auto,on,off}` con default `auto`, come da README.
- [ ] Sottoporre al modello i top-N chunk selezionati dall'RRF (non tutto il
      sito: costo e latenza) e chiedere un giudizio strutturato di citabilità.
- [ ] Consultare la skill `claude-api` per model id e parametri correnti prima
      di scrivere la chiamata.
- [ ] Rendere il costo prevedibile: cap sui token, e stampare a video quanti
      chunk verranno inviati prima di inviarli.

### C3 — Monitoraggio citazioni IA: voci residue
Il modulo `mars_citations.py` è scritto, verificato e in uso —
vedi [AS-IS.md](AS-IS.md). Restano aperti tre punti.

- [ ] `--from-audit` è dormiente: legge `report["rrf_simulation"]`, chiave che
      nessun modulo produce ancora. Non è un difetto ma un **contratto in
      anticipo**: il referto JSON di **C4** dovrà esporre
      `rrf_simulation: [{"query": ...}, ...]`, e le query vengono da **C5**.
- [ ] Verificare `OPENAI_MODEL = "gpt-5.6"`: è un altro fornitore, non
      verificabile con la documentazione Anthropic.
- [ ] Riusare `load_queries()` anche in `mars_audit.py` quando si farà **C5**,
      invece di riscriverne una seconda copia.

### C4 — Output HTML e JSON (`--format`, `--output`) — *mancante al 100%*
Il README mostra nell'`Uso:` la riga
`python3 mars_audit.py https://example.com --max-pages 40 --format html --output report.html`.
`argparse` in [mars_audit.py:107-114](mars_audit.py#L107-L114) espone solo
`url`, `--max-pages`, `--embeddings`, `--market`. I due flag **non esistono**:
il comando documentato termina con un errore.

- [ ] Aggiungere `--format {text,json,html}` (default `text`) e `--output PATH`
      (default stdout).
- [ ] Estrarre da `print_report()` una funzione `build_report(results, urls) -> dict`
      pura, e tre renderer che la consumano. Così il JSON è la struttura
      canonica e HTML/testo ne sono viste — e l'API può riusare lo stesso dict.
- [ ] Il renderer HTML deve essere self-contained (CSS inline, nessuna CDN),
      coerente con il principio "nessuna dipendenza aggiuntiva".
- [ ] `favicon.ico` / `favicon.png` sono già in root e presumibilmente destinati
      a questo report: agganciarli (inline base64) o rimuoverli.

### C5 — Query personalizzate (`--queries q.txt`) — *mancante al 100%*
Il README mostra `--queries q.txt`. Oggi la query è **una sola, hardcoded**, e
per giunta duplicata in due file:
`"cos'è questo sito"` in [mars_lexical.py:19](mars_lexical.py#L19) e
[mars_semantic.py:13](mars_semantic.py#L13).

Questo è il limite più serio della simulazione RRF: fondere due ranking prodotti
da **una** query dice pochissimo sul consenso reale del sito. Il README stesso
descrive l'RRF come `somma su ogni lista di 1/(k + rank_i(d))`, formula che ha
senso su un set di query.

- [ ] Aggiungere `--queries PATH` (una query per riga, UTF-8).
- [ ] Mettere le query nel `context` (`context["queries"]`), con default a una
      lista di query generiche multilingue se il flag non è passato.
- [ ] Far ciclare `mars_lexical` e `mars_semantic` sulle query, restituendo
      `rank` *per query*.
- [ ] Calcolare consenso e RRF aggregati su tutte le query, non sulla prima.

### C6 — Crawling interno (fallback quando manca la sitemap) — *mancante*
> R7 ha reso il crawler rispettoso (robots.txt, User-Agent, rate limit,
> filtro same-host, normalizzazione URL): la BFS sui link interni va
> innestata su quelle regole, non aggiunta a fianco.
Il README: *"esegue una scansione di un sito (**via sitemap o crawling
interno**)"*. In [mars_core.py:40-44](mars_core.py#L40-L44), se
`fetch_sitemap()` non restituisce nulla il fallback è
`urls = [self.base_url]`: **una sola pagina**. Non esiste alcun crawling
interno; `--max-pages 40` su un sito senza sitemap produce 1 pagina.

- [ ] Implementare la BFS sui link interni in `Crawler.crawl()`: coda,
      `visited` set, estrazione `<a href>`, `urljoin`, filtro same-host,
      normalizzazione (drop di fragment e query di tracking), stop a `max_pages`.
- [ ] Rimanere no-dipendenze: `urllib.parse` + BeautifulSoup, già presenti.
- [ ] Vedi anche **R7** (robots.txt, User-Agent, rate limit) — vanno insieme.

### C7 — Riuso dei risultati fra moduli
`run_audit()` passa a ogni modulo lo stesso `context` immutabile e raccoglie i
`results` fuori dal loop ([mars_audit.py:90-103](mars_audit.py#L90-L103)).
Un modulo di sintesi (C1, C2) non può quindi vedere i punteggi delle aree
precedenti.

- [ ] Aggiungere `context["results"] = results` **prima** del loop (stesso dict,
      popolato incrementalmente). È una riga, non rompe nessun modulo esistente
      e mantiene il contratto `audit(context)` intatto (principio 3).
- [ ] Documentare nel README che i moduli sono eseguiti nell'ordine di
      `MODULES_REGISTRY` e possono leggere `context["results"]`.

### C8 — WCAG reale via axe-core / Playwright
Il README lo indica come raccomandazione: *"Per un audit WCAG reale ti consiglio
di integrare librerie come axe-core (tramite Selenium o Playwright)"*.
`playwright>=1.40` è **già in `requirements.txt`** ma non è importato da nessun
file. `mars_wcag.py` controlla oggi solo `lang` e `alt` — due criteri su decine.

- [ ] Estendere `mars_wcag.py` con un percorso axe-core opzionale, attivo solo se
      Playwright e un browser sono disponibili; altrimenti resta l'euristica
      attuale (principio 2).
- [ ] Nel frattempo, allargare comunque l'euristica statica a costo zero:
      gerarchia degli heading, `<label>` per input, `<table>` senza `<th>`,
      link con testo generico ("clicca qui"), `tabindex` positivi,
      attributo `lang` su tutte le pagine e non solo sulla prima.
- [ ] Dichiarare nel report **quale** livello WCAG (A / AA) si sta misurando.

### C9 — WAPT reale via ZAP *(orchestrazione scritta, mai eseguita)*
`mars_wapt.py` ora legge gli alert reali e ne deriva il punteggio — vedi
**R4** in [AS-IS.md](AS-IS.md). Resta che **il daemon ZAP (Java) non è
installato** su questa macchina: `zap-cli` c'è (solo dentro `.venv/bin/`,
nemmeno nel PATH di sistema), ma senza daemon non scansiona nulla, quindi
oggi il ramo ZAP ripiega sempre sugli header.

- [ ] Installare ZAP e **verificare il percorso completo** `start` →
      `quick-scan` → `alerts -f json` → `shutdown`: è scritto
      sull'interfaccia documentata della CLI ma mai eseguito fino in fondo.
- [ ] Controllare che il JSON di `alerts` abbia davvero le chiavi `risk` e
      `alert` attese da `score_from_alerts()` (parsing già difensivo, ma da
      confermare sul campo).
- [ ] Verificare che lo `shutdown` in `finally` non lasci daemon orfani dopo
      un timeout.
- [ ] Valutare se `zapcli` 0.10.0 (2018) regga le versioni recenti di ZAP, o
      se convenga passare a `python-owasp-zap-v2.4`, già installato.
- [ ] Tarare i pesi di `ZAP_PENALTIES` su scansioni vere: oggi sono una
      stima dichiarata, non calibrata.

### C10 — `mars_tech`: coprire tutto ciò che il README dichiara
Il README assegna a `mars_tech` *"indicizzabilita', robots.txt, sitemap,
crawler IA"*. Il file implementa **solo robots.txt** (24 righe totali).

- [ ] Verifica sitemap: esistenza, validità XML, `<sitemapindex>` annidati,
      numero di URL, `lastmod` presente.
- [ ] Verifica indicizzabilità: `<meta name="robots" content="noindex">`,
      header `X-Robots-Tag`, `<link rel="canonical">` presente e coerente.
- [ ] Elenco crawler IA più completo e per-agente (GPTBot, ClaudeBot,
      Claude-Web, CCBot, PerplexityBot, Google-Extended, Bytespider, Amazonbot),
      distinguendo *assente* da *esplicitamente bloccato*.
- [ ] Sostituire `100 - len(issues)*15` con una scala pesata per gravità.

### C11 — Documentare l'API REST nel README
`mars_api.py` (300 righe, 10 endpoint, JWT) è metà del progetto, ma il README lo
menziona solo come elenco di pacchetti da installare. La sezione `Uso:` copre
esclusivamente la CLI.

- [ ] Sezione README con: avvio (`uvicorn mars_api:app`), flusso di
      autenticazione, tabella degli endpoint, esempio `curl` completo.
- [ ] Documentare che `/` reindirizza a `/docs` (Swagger UI).

### C12 — Test
`pytest>=7` e `flake8>=6` sono in `requirements.txt`; **nel progetto non esiste
un solo test**.

- [ ] `tests/test_core.py`: RRF su ranking noti (verifica contro la formula del
      paper Cormack 2009), BM25 su un corpus giocattolo, char-TFIDF, e i casi
      limite di **R6** (corpus vuoto, documenti vuoti).
- [ ] `tests/test_modules.py`: ogni `audit()` su HTML fixture offline —
      nessun test deve toccare la rete.
- [ ] `tests/test_api.py`: `TestClient` FastAPI, login + un endpoint protetto
      (fallirebbe **oggi**, vedi **R1**).
- [ ] Configurare flake8 (`setup.cfg`, `max-line-length = 120`) — vedi **R11**.

### C13 — File di progetto mancanti
- [x] `.gitignore` — creato. Esclude `.venv/` (5,4 GB) e `node_modules/`
      (162 MB), le cache, i referti rigenerabili e lo storico JSONL delle
      citazioni (che è dato dell'utente, non codice).
- [x] **Repository git inizializzato** (branch `main`) — vedi
      [AS-IS.md](AS-IS.md).
- [ ] `LICENSE` — ogni file sorgente dichiara "Licenza: Apache 2.0" ma il testo
      della licenza non è nel repo.
- [ ] `CLAUDE.md` con il contratto dei moduli, utile per il lavoro assistito.
- [ ] La cartella `versions/` (versionamento manuale: `mars_audit_1/2/3.py`,
      `mars_api_1.py`) **non è più presente** ed è quindi assente dal commit
      iniziale. Se quei file servono come riferimento storico, vanno
      recuperati e committati prima che si perdano del tutto.

---

## Correzioni

Difetti nel codice esistente. **R1-R8 sono tutti risolti** — vedi
[AS-IS.md](AS-IS.md). R13 è una direzione di lavoro, non un difetto.

### R9 — L'euristica "answer-shaped" è imprecisa e monolingue
[mars_semantic.py:20](mars_semantic.py#L20):
```python
has_question = any(w in chunk.lower() for w in ["?", "come", "cosa", "perché", "chi", "dove", "quando"])
```
È un test di **sottostringa**, non di parola: `"chi"` matcha *chiave*,
*macchina*, *architettura*; `"come"` matcha *comodo*. In pratica quasi ogni
chunk italiano risulta "answer-shaped" e la metrica perde significato.

Inoltre il termini sono solo italiani, mentre il modello di embedding di default
(`paraphrase-multilingual-MiniLM-L12-v2`) è **multilingue**: su un sito inglese
la metrica è sistematicamente vicina a zero.

- [ ] Usare confini di parola (`re.search(r'\b(...)\b')`).
- [ ] Estendere ad almeno IT/EN, o derivare la lingua dall'attributo `lang`
      già letto da `mars_wcag.py`.
- [ ] Aggiungere segnali strutturali più robusti dell'elenco di parole:
      presenza di liste, definizioni, `<h2>` in forma interrogativa, FAQPage
      JSON-LD (dato che `mars_schema.py` lo sta già leggendo).

### R10 — I "chunk" non sono chunk
[mars_audit.py:81](mars_audit.py#L81) e [mars_api.py:176](mars_api.py#L176):
```python
"chunks": [p['text'][:500] for p in pages.values()]
```
Un chunk = i **primi 500 caratteri** di una pagina — cioè, tipicamente, il menu
di navigazione. Tutto il contenuto oltre il carattere 500 è invisibile all'audit
semantico. Il README promette invece *"chunk autoconsistenti"*.

Conseguenza a catena: `mars_lexical` indicizza le **pagine**
([mars_lexical.py:14](mars_lexical.py#L14), primi 1000 caratteri) mentre
`mars_semantic` indicizza i **chunk** — ma gli indici delle due liste vengono
poi fusi insieme come se si riferissero alle stesse unità
([mars_audit.py:58-61](mars_audit.py#L58-L61)). **L'RRF sta fondendo due
ranking su granularità diverse**: il "consenso Top-3" che ne esce non ha il
significato dichiarato nel README.

- [ ] Costruire un vero chunker in `mars_core.py`: segmentazione per heading
      o per finestre di ~1000 caratteri con overlap, ciascun chunk con
      `{"url", "heading", "text"}`.
- [ ] Far lavorare **entrambi** i retriever sulla stessa lista di chunk. È la
      correzione singola più importante per la validità della simulazione RRF.
- [ ] Nel report, mappare l'indice del chunk sul suo URL *e* sul suo heading.

### R11 — Igiene del codice
- [ ] `requirements.txt:13` — `bcrypt=4.0.1` non è una specifica PEP 508 valida
      (serve `==`). **`pip install -r requirements.txt` fallisce**: verificato.
- [ ] `requirements.txt` **non elenca** dipendenze che il codice importa
      davvero: `fastapi`, `uvicorn`, `pydantic`, `python-jose[cryptography]`,
      `passlib[bcrypt]`, `python-multipart` (tutte usate da `mars_api.py`),
      più le opzionali `sentence-transformers`, `torch`, `scikit-learn`,
      `numpy`, `zapcli`. Sono installate nel venv ma non dichiarate.
      Valutare `requirements.txt` (core) + `requirements-optional.txt`,
      coerentemente col principio 2.
- [ ] `requirements.txt` include `tomli`, `jsonschema`, `PyYAML`, `idna`, `click`:
      **nessuno è importato** da alcun file del progetto. Rimuovere o motivare.
- [ ] `openapi.json` **non è una specifica OpenAPI**: contiene un payload di
      esempio di `AuditRequest` (con un URL reale, `lymphatechnologies.com`).
      Rinominare in `examples/audit_request.json`; la vera spec è generata da
      FastAPI su `/openapi.json`.
- [ ] `SECRET_KEY` in chiaro in [mars_api.py:26](mars_api.py#L26). Leggerla da
      `os.environ` e rifiutare l'avvio in assenza (o generarne una effimera con
      un warning esplicito).
- [ ] `datetime.utcnow()` ([mars_api.py:124-126](mars_api.py#L124-L126)) è
      deprecata da Python 3.12 e il progetto gira su **3.14**. Sostituire con
      `datetime.now(timezone.utc)`.
> Due voci di questo capitolo sono state chiuse — caricatore di moduli e
> import pigro di sentence-transformers: vedi [AS-IS.md](AS-IS.md).

- [ ] `load_external_module()` usa il percorso relativo `f"{module_name}.py"`
      ([mars_audit.py:24](mars_audit.py#L24), [mars_api.py:156](mars_api.py#L156)):
      **dipende dalla directory di lavoro**. Lanciato da un'altra cartella, il
      programma non trova nessun modulo e stampa serenamente `[ ] ... ignorato`
      per tutte e 7 le aree, producendo un report vuoto senza errori.
      Usare `Path(__file__).parent`. *(Distinto dal difetto `sys.modules` qui
      sopra: quello è risolto, questo no.)*
- [ ] `MODULES_REGISTRY` e `load_external_module()` sono **duplicati** verbatim
      in `mars_audit.py` e `mars_api.py`. Spostarli in `mars_core.py`
      (o `mars_registry.py`), unica fonte di verità. *(R5 ha già spostato lì
      `build_context()`: resta questa seconda metà della duplicazione, ed è
      la stessa che ha costretto a correggere il difetto `sys.modules` in due
      file invece che in uno.)*
- [ ] `mars_schema.py` e `mars_wcag.py` ri-parsano l'HTML con BeautifulSoup a
      ogni modulo. Parsare una volta nel `Crawler` e mettere il `soup` (o il
      DOM già estratto) nel `context`.
- [ ] Eseguire `flake8 --select=F` dopo ogni modifica: è il controllo che ha
      rivelato **R1**. Oggi riporta un solo errore logico; deve restare a zero.
- [ ] ~200 avvisi di stile (E302, E501, W291, W293) su `flake8 --max-line-length=120`.
      Aggiungere `setup.cfg` e normalizzare in un unico commit separato, per non
      mescolare formattazione e correzioni sostanziali.
- [ ] `__pycache__/` e `node_modules/` sono versionati nella cartella di lavoro
      (vedi **C13**).

### R12 — Incoerenze nel README
- [ ] *"valuta **quattro** aree"* seguito da un elenco di **sette** voci
      numerate 1-7. Correggere in "sette aree".
- [ ] L'`Uso:` documenta `--format`, `--output` e `--queries`, che non esistono
      (**C4**, **C5**). O si implementano, o si toglie la riga: un README che
      documenta comandi che falliscono è peggio di uno incompleto.
- [ ] Il README dice che WCAG/WAPT sono *"stub euristici"*: onesto per WCAG, ma
      per WAPT sottostima il problema, perché i punteggi sono **inventati**
      (**R4**), non euristici.
- [ ] Il blocco di comandi per i prerequisiti `zap-cli` disinstalla
      `urllib3`/`requests`/`six` a livello globale: aggiungere l'avvertenza di
      eseguirlo **dentro un virtualenv**.
- [ ] Manca del tutto la documentazione dell'API REST (**C11**).

### R13 — Allineamento graduale allo stile di riferimento
Decisione del 2026-08-19 (principio 8): `mars_citations.py` è il modello.
L'allineamento è **graduale e opportunistico** — si adegua un modulo quando lo
si tocca per altri motivi, non in un rifacimento di massa che
mescolerebbe riformattazione e correzioni sostanziali.

Ordine suggerito, dal ritorno più alto al più basso:

- [ ] `mars_core.py` — è la base di tutto. `Crawler` e i due retriever
      diventerebbero molto più chiari con dataclass e type hints, e la cosa si
      combina naturalmente con **R7** (crawler) e **R8** (proxy quadratico).
      Le funzioni aggiunte oggi (`load_sentence_transformers`, `norm_host`,
      `host_matches`) sono già nel nuovo stile: il file è misto.
- [ ] `mars_audit.py` — la separazione dato/presentazione di **C4** è
      esattamente il rifacimento di `print_report()`. Farli insieme.
- [ ] `mars_api.py` — ha già i type hints (via Pydantic); mancano la
      separazione I/O e la deduplicazione con `mars_audit.py`. Si combina
      con **R5**.
- [ ] I 7 moduli d'area — sono corti; conviene adeguarli quando si estendono
      (**C8**, **C9**, **C10**).

Regola pratica: **un commit di sola riformattazione, separato** da quello che
cambia il comportamento. Altrimenti la revisione diventa impossibile.

### R14 — 🔴 Il campo `disabled` non è mai applicato
Emerso verificando R2. `User` dichiara `disabled: bool | None` e `FAKE_USERS_DB`
valorizza `"disabled": False`, ma **nessuna funzione lo legge mai**: né
`authenticate_user()` né `get_current_user()`.

Verificato in esecuzione con un utente `disabled: True`:

```
POST /token      -> 200  (token rilasciato)
GET  /users/me   -> 200
POST /audit/tech -> 404  (auth superata, si ferma solo sul sito irraggiungibile)
```

Un account sospeso continua quindi ad accedere a tutta l'API. Il campo dà
l'impressione che esista una revoca degli accessi che in realtà non c'è — è
peggio della sua assenza, perché induce a fidarsene.

- [ ] Rifiutare l'autenticazione degli utenti disabilitati in
      `authenticate_user()`, e ricontrollare in `get_current_user()` così che
      un token già emesso smetta di funzionare quando l'utente viene sospeso
      (altrimenti resta valido fino alla scadenza, 30 minuti).
- [ ] Test dedicato: è esattamente il tipo di regressione silenziosa che
      **C12** deve intercettare.

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
Se si fa **C4**, il grafico più espressivo è il *rank shift*: due colonne
(BM25, vettoriale) collegate da linee ai rispettivi ranghi post-fusione.
Mostra a colpo d'occhio il consenso. Da fare in SVG inline, senza librerie.

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
