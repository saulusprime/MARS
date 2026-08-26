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
> **U13 è chiusa il 2026-08-26** e sta in [AS-IS.md](AS-IS.md): le due aree
> di classifica emettono sette controlli, hanno un punteggio, e quel punteggio
> resta **fuori dal complessivo** perché le stesse due aree ci entrano già dai
> segnali derivati. Il piano di interventi copre ora sette aree su nove.
>
> **Correzioni chiuse**: R1-R52. **R51 è chiusa il
> 2026-08-26**, e con essa **R37 per intero**: il `<meta name="googlebot">`
> arriva ora separato dal meta globale (`meta_robots_by_agent`, una chiave
> nuova nel contratto) e vale come il prefisso dell'`X-Robots-Tag`. R52 è
> l'ultima nata e chiusa il 2026-08-26, trovata chiudendo R28: meta' dei test
> i18n confrontavano due rese e potevano cadere a cavallo di un secondo.
> **R39 è chiusa il 2026-08-26**: gli alert ZAP si raggruppano per
> sotto-variante, la penalità resta della regola e si ripartisce, i punteggi
> non si muovono e la migrazione di chiavi è dichiarata nel referto
> (`key_migrations`). `__version__` a **2.9.0**.
> **R40 è chiusa il 2026-08-26** — le sue tre caselle; i tre rilievi che
> caselle non erano proseguono in **R53**.
> **R46 è chiusa il 2026-08-26**: `instances` è il nome canonico del conteggio
> accanto a quelli parlanti, e lo sforzo scala di un gradino per volta restando
> una stima dichiarata.
> **R48 è chiusa il 2026-08-26**: dal JavaScript del grafo è uscita anche la
> geometria — archi, etichette e vicinato — e allo script resta il solo gesto,
> che `tools/banco_grafo.py` presidia come prima. Il costo in attributi è
> misurato e dichiarato in [CONTRIBUTING.md](CONTRIBUTING.md).
> **Aperta**: R53 —
> trovate *adeguando* i moduli alle Fasi 1-5, e non corrette lì dentro perché
> avrebbero spostato punteggi o testi dentro un commit che cambiava la forma.
> **R47 è chiusa il 2026-08-26** — schema JSON a `schema_version: 2`, passo 3
> della Fase 8 chiuso, **R49** sbloccata — e **R32** lo stesso giorno. **R36**
> è chiusa il 2026-08-26: `nosnippet`, `noarchive` e `unavailable_after` scaduto
> sono tre rilievi nuovi dell'area 1, e la direttiva che pesa di più sulla
> citabilità non è più muta. **R33** lo stesso giorno: la suite non dipende più
> dalla directory da cui la si lancia, e l'autoconsistenza dell'HTML è
> controllata su quattro forme in più — `url()`, `@import`, `srcset` — anche sui
> due golden. **R28** lo stesso giorno: `mars_citations` esce con 3 e non con 1
> quando non riesce a scrivere, non perde piu' il referto se lo storico e'
> illeggibile, e dice `null` invece di `0.0` quando non ha misurato nulla.
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
La suite esiste — 1032 test, vedi [AS-IS.md](AS-IS.md). Restano rifiniture.

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

---

## Correzioni

Le voci chiuse — R1-R52 — stanno in
[AS-IS.md](AS-IS.md) con difetto, soluzione e verifiche, e non si riassumono
qui: **nessuna voce GRAVE resta aperta.**

Le voci qui sotto vengono tutte dall'**adeguamento dei moduli alle
fasi UPGRADE**, non dalla revisione sistematica del 2026-08-20, che è
esaurita: leggere un modulo riga per riga per cambiarne la forma ne ha
rivelato i difetti, e nessuno è stato corretto lì dentro perché tutti
spostano punteggi o testi — cioè esattamente ciò che un adeguamento di forma
non deve fare. Vanno riprodotte prima di correggerle (regola *verificare, non
dedurre*). Ordinate per gravità.

### R53 — ⚪ LIEVE: i tre residui di `mars_seo` che caselle non erano
*(R40 aveva sei rilievi e tre caselle. Le caselle sono chiuse il 2026-08-26 e
stanno in [AS-IS.md](AS-IS.md); questi tre non erano azioni ma osservazioni, e
ciascuno apre una decisione)*

- **`MODI_NON_MISURATI_VOCE` e `LH_MODI_NON_MISURATI` divergono di proposito**,
  e la divergenza va tolta con una misura, non per simmetria. La voce si ferma
  a `("manual", "notApplicable")` ([mars_seo.py:55](mars_seo.py#L55));
  `mars_core` comprende anche `informative` ed `error`. Un `informative` ha
  `score: 1` per costruzione, quindi oggi è contato fra i **superati**; un
  `error` fra i **falliti**. R40 ha chiuso la metà del **testo** — il prefisso
  della issue ora si sceglie sul modo, quindi un `error` non si annuncia più
  col titolo del successo — e ha lasciato aperta quella dei **conteggi**:
  allargare la tupla sposterebbe `passed`/`failed`/`manual` e la riga «N
  superati, M falliti» del referto. Un test tiene le due metà separate.
- **`explanation`, `displayValue` e `warnings` di Lighthouse sono ignorati.**
  Sono i testi che dicono *perché* un controllo è fallito; verificato: zero
  occorrenze in `mars_seo.py`. Da notare `warnings` di `is-crawlable`, che è un
  audit che **passa** pur avendo qualcosa da dire — e oggi quel qualcosa non
  arriva da nessuna parte.
- **Il parametro `score` di `severita_lighthouse` non viene mai letto**
  ([mars_core.py:381](mars_core.py#L381)): la funzione decide su modo e peso.
  Non è morto per svista — è il chiamante che deve filtrare i superati, e senza
  quel filtro un sito perfetto produrrebbe nove `warning` — ma un parametro
  inerte in una firma pubblica invita a crederlo significativo. Renderlo
  significativo vuol dire introdurre `SEV_OK`, che oggi nessun modulo usa: è la
  decisione della fase che renderà i controlli superati, la stessa che **U13**
  ha lasciato fuori dal proprio perimetro.

- [ ] Decidere se i conteggi seguono i quattro modi di `mars_core`, misurando
      quanto si sposta la riga «N superati, M falliti».
- [ ] Portare `explanation`, `displayValue` e `warnings` nel rilievo, decidendo
      in quale campo: `detail` è già occupato dalla `description`.
- [ ] Solo con `SEV_OK`: rendere significativo il parametro `score`.

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
oggi costanti sparse nel codice. Un `mars_weights.yaml` (o `.toml`, letto con
`tomllib`, che è nella stdlib da Python 3.11 — `tomli` era in
`requirements.txt` ed è stato rimosso con R11, perché nessun file lo importava)
li renderebbe ispezionabili e regolabili senza toccare il codice — rafforzando
il principio 6.

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
