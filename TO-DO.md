# MARS Beacon — TO-DO

> **Questo file contiene solo ciò che resta da fare.** Il lavoro completato e
> verificato si sposta in [AS-IS.md](AS-IS.md), con difetto, soluzione e prove,
> nello stesso commit che lo chiude.
>
> **Frontiera della numerazione**: correzioni fino a **R53**, idee fino a
> **I16**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Ripulito il 2026-08-26**, secondo giro: il primo, il 2026-08-25, aveva
> tolto centoquattro righe di lavoro concluso e rinfrescato quarantasei
> riferimenti di riga. Come allora, ogni voce aperta è stata **riverificata sul
> codice**, non riletta, e **nove affermazioni non hanno retto**: tre premesse
> false — due dichiaravano aperto un lavoro già fatto — tre riferimenti di riga
> che non atterrano più dove dicono, due numeri invecchiati e un prerequisito
> soddisfatto dal 2026-08-19. Ogni correzione è nella sua voce, e dice **che
> cosa** diceva prima: è l'unica parte di questa pulizia che cambia una
> decisione, e cancellarla senza traccia lascerebbe credere che la voce sia
> sempre stata così.
>
> Sono uscite **trentasette righe di annunci di chiusura**, riaccumulate in una
> sola sessione dopo la potatura precedente, e le **cinquantadue righe della
> filosofia**. Un cappello che annuncia le chiusure diventa un secondo AS-IS,
> più corto e senza le prove, che invecchia per conto suo: le chiusure si
> leggono là.

---

## Filosofia di sviluppo da preservare

I principi stanno in [.claude/principi.md](.claude/principi.md), che CLAUDE.md
monta nel contesto di ogni sessione: qui ne restava una seconda copia, più
lunga e non divergente — cioè il caso peggiore, perché nulla segnala quando le
due smettono di dirsi la stessa cosa. Delle cinquantadue righe una sola non
stava nell'altro file, la convenzione su `__version__`, `--version` e i codici
di uscita espliciti, ed è andata dove serve davvero: dentro **I2**, la voce
che la deve applicare.

Resta la riga che parla di **questo elenco** e non del codice, e che il file
dei principi quindi non può contenere: **nessuna voce di questo TO-DO deve
violarli.** Una voce che per essere realizzata chiede di sostituire un
algoritmo core con una libreria, o di rendere obbligatoria una dipendenza
oggi opzionale, è una voce da riscrivere, non da eseguire.

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
La suite esiste — vedi [AS-IS.md](AS-IS.md). Restano rifiniture. Il numero dei
test non sta qui: cambia a ogni commit, e un numero che invecchia da solo dice
meno del comando che lo produce.

- [ ] Misurare la copertura (`pytest --cov`) per trovare i rami mai eseguiti:
      oggi si sa quali difetti sono protetti, non quanto codice è toccato.
- [ ] `evaluate_answer` di `mars_citations.py` non è chiamata da alcun test.
      *(La voce diceva «`mars_citations.py` non ha test propri»: falso dal
      2026-08-26, quando R28 ha portato `tests/test_citations.py` — codici di
      uscita, storico JSONL, `overall_rate`, il tasso non misurato. Delle tre
      funzioni pure che nominava ne resta scoperta una, ed è quella che decide
      se una risposta cita il sito: è una funzione pura, quindi verificabile
      senza rete né chiavi.)*
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

**Nessuna voce GRAVE resta aperta**, e resta una voce sola. Viene
dall'**adeguamento dei moduli alle fasi UPGRADE**, non dalla revisione
sistematica del 2026-08-20, che è esaurita: leggere un modulo riga per riga
per cambiarne la forma ne ha rivelato i difetti, e nessuno è stato corretto lì
dentro perché tutti spostano punteggi o testi — cioè esattamente ciò che un
adeguamento di forma non deve fare. Va riprodotta prima di correggerla (regola
*verificare, non dedurre*).

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
  ([mars_core.py:388](mars_core.py#L388)): la funzione decide su modo e peso.
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

### I2 — Modalità CI con exit code e soglie
`--fail-under 70` → exit code ≠ 0. Rende MARS utilizzabile come gate in una
pipeline. Costo: una decina di righe.

**Metà è già fatta, ed è la metà che serviva a scoprire il costo vero.**
`mars_citations.py` ha `--fail-under` e i codici di uscita espliciti; il posto
per quello dell'audit è **riservato nel codice**, non da inventare:
[mars_audit.py:27](mars_audit.py#L27) tiene libero il valore `1` proprio per
questa idea, perché una pipeline non deve poter confondere «punteggio sotto
la soglia» con «l'audit non è riuscito». Resta quindi solo `mars_audit`, e la
convenzione da seguire è quella già scritta accanto.

### I3 — Sensibilità del parametro `k` dell'RRF
`k=60` è la predefinita di `reciprocal_rank_fusion`, dichiarata come `RRF_K`
([mars_core.py:1684](mars_core.py#L1684)) — è il valore del paper Cormack
2009, ma il progetto è *anche* didattico: esporre `--rrf-k` e mostrare come
cambia il consenso al variare di `k` è esattamente il tipo di intuizione che
il README vuole trasmettere. Quasi gratis da implementare. *(La voce lo diceva
«hardcoded», e rimandava a una riga che oggi è dentro il caricamento delle
query: la costante c'è, il flag no.)*

### I4 — Ablation lessicale vs. vettoriale
Riportare, accanto al risultato fuso, quanto ciascun retriever contribuisce al
Top-N: quanti chunk vengono solo da BM25, quanti solo dal vettoriale, quanti dal
consenso. È la dimostrazione empirica del perché l'ibrido batte i singoli —
la tesi centrale del paper citato in bibliografia.

*Verificato il 2026-08-26:* **il terzo numero c'è già.** `_consenso`
([mars_report.py:1015](mars_report.py#L1015)) pubblica `consensus_top3`, che è
la cardinalità dell'intersezione dei primi tre — e i due «solo» sono il
complemento, quindi non è nemmeno una misura nuova: è una sottrazione che
oggi il referto non fa. Ciò che manca davvero è **quali** chunk stiano fuori
dall'intersezione, ed è la stessa cosa che manca a **I9**: le due idee sono
una domanda sola vista da due lati, e chi ne apre una apra l'altra.

### I5 — Crawling concorrente
`ThreadPoolExecutor` sul fetch delle pagine (stdlib, nessuna dipendenza nuova).
Con `--max-pages 40` e timeout di 10s il crawl seriale può richiedere minuti.
Il rate limiting c'è già — R7, chiusa il 2026-08-19 — ed è **il vincolo, non
il prerequisito**: `_get` serializza le richieste su `self._last_request`
([mars_core.py:700](mars_core.py#L700)), quindi un pool che non passasse di lì
violerebbe `Crawl-delay`, e uno che ci passa non guadagna niente. La voce va
riscritta come «parallelizzare *ciò che sta attorno* al fetch» — parsing,
estrazione — oppure chiusa: la sua formulazione attuale non è realizzabile
senza rompere un principio.

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
([mars_seo.py:22](mars_seo.py#L22)) e nella stessa risposta JSON restituisce
anche `performance`, `accessibility` e `best-practices`.

*Corretta il 2026-08-26, perché la premessa non regge più.* Diceva che quei
dati erano «**già scaricati e buttati via**»: **falso da R45**, che li pubblica
tutti (`punteggi_categorie`, `lighthouse_scores`) e che ha già realizzato la
seconda metà dell'idea — la controprova fra l'`accessibility` di Lighthouse e
`mars_wcag`, con la spiegazione del perché i due numeri differiscono. Restava
dichiarata aperta un'idea per metà eseguita.

Resta il **modulo**: oggi si pubblica il *punteggio* di categoria, non i
controlli che lo compongono — LCP, CLS, INP e le loro soglie, che sono l'unica
parte azionabile. Un `mars_perf.py` li leggerebbe dallo stesso LHR, senza un
secondo Lighthouse, come `mars_wcag` già fa per l'accessibilità.

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

### I16 — Scegliere il dispositivo di Lighthouse (`--form-factor`)
*(proposta il 2026-08-20, portando i controlli SEO nel referto)*
Lighthouse misura per `mobile` come predefinito, e MARS lo dichiara nel
referto. PageSpeed Insights espone invece entrambe le viste, e un referto
`desktop` puo' dare punteggi diversi sugli stessi contenuti. Un flag
`--form-factor {mobile,desktop}` — passato a Lighthouse come
`--preset=desktop` — permetterebbe di confrontare like-for-like con il
referto che il committente ha sotto gli occhi. Costo: un flag, un campo
nel corpo API, e la propagazione fino a `mars_seo`.
