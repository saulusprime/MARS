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
> **Correzioni chiuse**: R1-R38, R41-R45, R47, R49-R50, R52 — R37 a
> metà: la metà aperta è **R51**. L'ultima
> nata e chiusa il 2026-08-26, trovata chiudendo R28: meta' dei test i18n
> confrontavano due rese e potevano cadere a cavallo di un secondo.
> **Aperte**: R39 (una casella), R40, R46, R48 e R51 —
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

Le voci chiuse — R1-R27, R29-R32, R34, R38, R41-R45, R47 — stanno in
[AS-IS.md](AS-IS.md) con difetto, soluzione e verifiche, e non si riassumono
qui: **nessuna voce GRAVE resta aperta.**

Le voci **R28-R33** qui sotto vengono da una **revisione sistematica del
2026-08-20** (lettura integrale di codice e documentazione, con verifica
avversariale dei rilievi). Dove scritto *«riprodotto»* il difetto è stato
osservato in esecuzione con la suite/venv; le altre voci sono uscite dalla
verifica e vanno riprodotte prima di correggerle (regola *verificare, non
dedurre*). Ordinate per gravità.

### R51 — ⚪ LIEVE: il `<meta name="googlebot">` non ha un agente
*(la metà di R37 che non si è chiusa il 2026-08-26)*

R37 ha separato il prefisso per agente dell'`X-Robots-Tag`, e il DOM ha
l'equivalente: `<meta name="googlebot" content="noindex">` vale per il solo
Google, mentre `<meta name="robots">` vale per tutti. Oggi ricevono lo stesso
giudizio, perché il crawler unisce i `content` di più meta in **una stringa
sola** (`mars_core`) e quale meta li portasse è perduto prima di arrivare al
modulo — `direttive_per_agente()` non può separarli, e lo dichiara nella propria
docstring.

Chiuderla vuol dire una chiave nuova nella pagina prodotta dal crawler, cioè il
contratto documentato in [.claude/contratto-moduli.md](.claude/contratto-moduli.md):
è la ragione per cui non è stata fatta insieme a R37, dove sarebbe finita in un
commit che cambiava anche il crawler.

Il comportamento di oggi è **fissato da un test**
(`test_tech_il_meta_per_agente_resta_fuori_e_lo_si_dichiara`), che diventerà
rosso quando questa voce si chiuderà: è esattamente quando va riscritto.

- [ ] Conservare l'agente del meta nella pagina, e trattarlo come il prefisso
      dell'header.

### R39 — 🟡 MEDIO: `alertRef` non viene mai raggiunto
*(le caselle 2 e 3 sono chiuse il 2026-08-26 e stanno in [AS-IS.md](AS-IS.md):
il ripiego dopo un fallimento di ZAP ora si dichiara, e `audit_headers`
conserva entrambe le diagnosi. Resta la prima casella, che sposta i punteggi)*
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
      migrazione di chiavi. **Deciso il 2026-08-26**: si ritara sulla REGOLA —
      penalità calcolata sull'unione degli URL e ripartita fra le sotto-varianti,
      così i tre rilievi CSP diventano distinti, ciascuno con la propria
      `solution`, e la somma resta quella di oggi. Migrano solo le chiavi
      (`sec.zap.10038` → `sec.zap.10038_1`), e la migrazione va dichiarata in
      AS-IS e nel referto: per `compute_delta` è un «risolto» più un «comparso»
      per ogni regola con sotto-varianti, contro gli archivi già scritti.

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

### R48 — ⚪ LIEVE: del JavaScript resta da verificare il GESTO
*(l'aritmetica e' uscita di qui il 2026-08-26: vedi [AS-IS.md](AS-IS.md))*

La disposizione ad anelli e' ora `disposizione_ad_anelli()` in
`mars_report.py`, e `pytest` la verifica. Restano al JavaScript gli **eventi** —
fuoco, evidenziazione dei vicini, zoom, ritorno al layout di partenza — che solo
`tools/banco_grafo.py` prova, e non automaticamente: chi tocca `REFERTO_JS` deve
lanciarlo a mano.

Le due strade per chiudere restano quelle di prima, ma su una superficie molto
piu' piccola:

- **portare in Python anche archi, etichette e vicini** (`data-ax1..ay2`,
  `data-v`): `ridisegna()` ed `evidenzia()` diventerebbero applicazione di
  attributi, e sparirebbe la geometria oggi scritta due volte. Costo misurato in
  ricognizione: 4-5 KB in piu' su un grafo da 60 nodi;
- **`jsdom` in `requirements-dev`** con un test marcato: copre il gesto per
  intero, ma allarga la suite a npm, e su un clone senza `node` e' sempre verde
  perche' sempre saltato.

- [ ] Scegliere fra le due, e nel frattempo non toccare `REFERTO_JS` senza
      rilanciare `tools/banco_grafo.py`.

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
