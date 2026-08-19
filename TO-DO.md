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
> R10 ha rimosso il presupposto mancante: i due retriever lavorano ora sugli
> stessi chunk, quindi far ciclare più query produce ranghi fondibili.
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

### C13 — File di progetto: voci residue
Il grosso è chiuso — vedi [AS-IS.md](AS-IS.md). Restano due punti aperti.

- [ ] **Titolarità del copyright.** `LICENSE` è l'Apache 2.0 autentico, ma
      l'appendice conserva il segnaposto `Copyright [yyyy] [name of copyright
      owner]` e nessun file sorgente porta una riga di copyright: dichiarano
      solo *"Licenza: Apache 2.0"*. Senza un titolare indicato la licenza è
      difficile da far valere. Non l'ho compilato di mia iniziativa: attribuire
      la titolarità è una decisione, non una formattazione.
- [ ] **Recapito nel `CODE_OF_CONDUCT.md`**, lasciato in bianco di proposito:
      pubblicare un indirizzo nel repository spetta al responsabile.
- [ ] La cartella `versions/` (`mars_audit_1/2/3.py`, `mars_api_1.py`) **non è
      più presente** ed è assente dal repository. Se serve come riferimento
      storico va recuperata ora; altrimenti la voce si chiude togliendola.

---

## Correzioni

**Capitolo vuoto: le correzioni R1-R14 sono tutte risolte.**
Difetto, soluzione e verifiche di ciascuna sono in [AS-IS.md](AS-IS.md).

Le nuove correzioni si aprono qui, con la numerazione che riprende da R15.

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
