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

### C4 — voce residua
Il referto JSON e HTML è fatto — vedi [AS-IS.md](AS-IS.md). Resta un punto che
non dipende dal codice.

- [ ] **Verificare sul campo il giudizio LLM (C2)** con una credenziale
      Anthropic reale: la chiamata non è mai stata eseguita, solo simulata.
      Il referto JSON ora conserva per intero motivazione, punti forti e
      deboli, quindi è il formato giusto per controllarne l'esito.

### C9 — WAPT via ZAP: voci residue
Client ufficiale, orchestrazione eseguita contro un daemon simulato,
raggruppamento per regola — vedi [AS-IS.md](AS-IS.md). Restano i due punti che
richiedono ZAP vero.

- [ ] **Verifica contro un daemon ZAP reale.** Qui Java non è installato e il
      collaudo è avvenuto contro un finto daemon che risponde all'API. La
      sequenza e le chiavi sono confermate; resta da vedere se ZAP reale si
      comporta come il suo contratto documentato.
- [ ] Tarare `ZAP_PENALTIES` su scansioni vere: oggi sono un ordinamento
      dichiarato, non una misura calibrata.

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
