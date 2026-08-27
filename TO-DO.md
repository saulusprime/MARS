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
> **Frontiera della numerazione**: correzioni fino a **R56**, idee fino a
> **I16**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Nove caselle aperte**, e da oggi **una voce GRAVE**: R55, la prima da
> quando la revisione del 2026-08-20 le aveva chiuse tutte. Non viene da una
> revisione ma da un sospetto dell'utente su `--max-pages`, verificato e
> fondato — e la stessa indagine ha trovato la cosa peggiore accanto.
>
> **I principi** stanno in [.claude/principi.md](.claude/principi.md), che
> CLAUDE.md monta in ogni sessione, e valgono anche qui: una voce che per
> essere realizzata chiede di sostituire un algoritmo core con una libreria, o
> di rendere obbligatoria una dipendenza oggi opzionale, è una voce da
> riscrivere, non da eseguire.

---

## Correzioni

Due, aperte il 2026-08-27 da un controllo chiesto dall'utente: «credo che ZAP
ignori `--max-pages`». Vero, e la stessa indagine ne ha trovata una seconda,
più grave. **Entrambe riguardano `mars_wapt`, l'unica delle nove aree che
scopre le pagine da sé** invece di lavorare sul campione già costruito — le
altre otto leggono `context["pages"]` e sono per questo già vincolate.

Ordinate per gravità. Riprodotte prima di essere scritte: i numeri qui sotto
sono misure su un sito locale di tredici pagine in catena, ZAP 2.17.0.

### R55 — 🔴 GRAVE: lo spider di ZAP non rispetta robots.txt, e MARS lo lancia da sé

[.claude/sicurezza.md](.claude/sicurezza.md) dichiara: «Il crawler rispetta
robots.txt. L'unico modo per ignorarlo è la dichiarazione di proprietà del
dominio (`--i-own-this-domain`), che viene registrata nel referto.» Vale per il
crawler di `mars_core`. **Non vale per lo spider che `mars_wapt` avvia** a ogni
audit in cui un daemon ZAP risponde — senza flag, senza dichiarazione, e senza
che il referto lo dica.

**Misurato, non dedotto.** Con un `robots.txt` che vieta `/p02.html` e
`/p03.html`, ZAP le ha richieste entrambe. E il meccanismo è isolato: una
pagina `/segreta.html` **collegata da nessuna pagina**, presente solo come
`Disallow` in robots.txt, **è stata richiesta lo stesso**. Lo spider usa le voci
`Disallow` come *semi* da cui partire, quindi robots.txt lo fa scansionare **di
più**, non di meno — e proprio i percorsi che il sito chiede di non toccare.

**Non è configurabile.** Verificato sul daemon: delle ventiquattro opzioni dello
spider l'unica che nomina robots è `optionParseRobotsTxt`, che governa il
*leggerlo per trovare URL*, non l'obbedirgli. **Un'opzione per obbedire non
esiste**, quindi la correzione non è una riga di configurazione.

Con `--i-own-this-domain` sarebbe una scelta dichiarata, come l'active scan.
Senza, è una promessa del progetto che una delle nove aree non mantiene, su
traffico diretto a siti di terzi. È per questo GRAVE e non MEDIO: non produce un
numero sbagliato nel referto, fa fare a MARS qualcosa che MARS dichiara di non
fare.

Le tre strade, con ciò che è già verificato di ciascuna:

| Strada | Che cosa comporta |
|---|---|
| **Niente spider**: dare a ZAP gli URL che il crawler ha già scelto — sono per costruzione conformi a robots.txt — con `core/action/accessUrl`, e tenere la sola scansione **passiva** | Chiude anche R56, perché il perimetro diventa esattamente il campione. Costo: gli alert attivi resterebbero legati allo spider, e va misurato quanto si perde |
| **Spider solo con `--i-own-this-domain`**, come l'active scan | Coerente con una regola che esiste già; ma senza dichiarazione l'area 7 diventa il solo ripiego sugli header, ed è un passo indietro per l'uso normale |
| **Filtrare a mano** i `Disallow` in `optionSkipURLString` | Riscrive in MARS la logica di robots.txt che `mars_core` ha già, e le due copie divergerebbero in silenzio — vedi il principio contro le implementazioni doppie |

- [ ] Decidere fra le tre, misurando quanti alert si perdono senza spider.
- [ ] Qualunque sia la scelta, il referto deve **dichiarare il perimetro
      dell'area 7**: oggi `mars_wapt` non pubblica `pages_tested`, quindi tace,
      mentre il referto in testa dichiara `pages_crawled` e chi legge lo
      riferisce a tutte le aree.

### R56 — 🟡 MEDIO: `--max-pages` non vincola l'area 7

`--max-pages` si ferma al costruttore del `Crawler` e **non entra nel
`context`**: le chiavi sono `url, pages, urls, chunks, queries, discovery,
robots, sitemap, delay, llm, lang, market, …` e `max_pages` non c'è. Per le otto
aree che leggono `context["pages"]` non è un problema — il campione è già
tagliato. Per `mars_wapt` sì: legge il solo `context["url"]` e chiama
`client.spider_scan(url)`, che manda a ZAP **il solo `url`**
([mars_wapt.py:445](mars_wapt.py#L445)).

**Misurato**, stesso sito locale:

| | |
|---|---|
| MARS con `--max-pages 2` | **2** pagine: `index`, `p01.html` |
| Lo spider di ZAP, stessa esecuzione | **6** pagine più `robots.txt` e `sitemap.xml` |

Si è fermato a `p05` perché è il `MaxDepth` di default di ZAP, **5** — non per
un limite di MARS. `MaxChildren` e `MaxDuration` sono a **0**, cioè illimitati.
L'aiuto del flag promette «più pagine significa più tempo e più richieste al
sito» ([mars_audit.py:191](mars_audit.py#L191)): per l'area 7 quella frase non
descrive nulla.

**Un tetto esatto non è ottenibile dall'API**, ed è verificato:
`spider/action/scan` accetta `url maxChildren recurse contextName subtreeOnly`,
e `maxChildren` limita i figli **per nodo**, non il totale. Chi lavora R56 lo
sappia prima di provarci: la strada che dà un perimetro esatto è la prima di
R55, cioè non usare lo spider.

- [ ] Portare il limite nel `context` come chiave, così che un modulo che
      scopre da sé possa onorarlo invece di doverlo indovinare.
- [ ] Vincolare l'area 7 al campione, coordinandosi con la decisione di R55:
      se si sceglie «niente spider», questa casella si chiude con quella.

---

## Programma UPGRADE

Il piano sta in [UPGRADE.md](UPGRADE.md), il quadro delle nove fasi chiuse e le
decisioni D1-D4 in [AS-IS.md](AS-IS.md). Dove piano e realizzazione divergono
ha ragione AS-IS. Restano tre fasi, più **U12** (ancore esterne, Brave Search e
confronto competitivo) che il piano dichiara **opzionale** e che per questo non
ha una casella: se si decide di farla, la casella si aggiunge.

- [ ] **U10 — Giudizio LLM multi-modello** (G08, Fase 10): ChatGPT, Qwen e
      Kimi accanto a Claude.
- [ ] **U10.1 — I `punti_deboli` del giudizio come rilievi strutturati.**
      U1.9 li ha lasciati fuori di proposito: sono prosa libera, senza chiave
      stabile, diversi a ogni esecuzione (`thinking: adaptive`) e a ogni
      modello, quindi né confrontabili (U7) né traducibili (U9) — e
      `Finding.key` è proprio ciò su cui quelle due fasi poggiano. Il prezzo è
      che l'**unica prosa orientata al miglioramento** dell'intero referto
      resta fuori dal piano U4 e da ogni esportazione basata sui findings.
      Riaprirla richiede prima **una** delle due cose che oggi mancano:
      *(a)* far etichettare al modello ogni punto debole con una delle chiavi
      che le altre otto aree già producono — allora il rilievo è un derivato di
      quella chiave, con la prosa in `detail` e `params["derived"] = True` come
      in `mars_citability`, e la chiave resta stabile perché il modello la
      sceglie da un vocabolario chiuso invece di scriverla; *(b)* il giudizio
      multi-modello, dove la **concordanza** fra modelli è la misura che oggi
      manca e che renderebbe il rilievo una misura invece di un'opinione.
      Senza (a) o (b) resta prosa, e va lasciata dov'è. Dipende quindi da U10,
      o da una decisione che non richiede U10.
- [ ] **U11 — Deliverable rifinito** (G14, G15, Fase 11): CSS di stampa,
      accessibilità delle tabelle, brand nel footer.

---

## Completamento

Le due voci `C##` rimaste non sono funzioni mancanti: sono **prove mancanti**.
In entrambe il codice c'è, e nessuno ha verificato che faccia ciò che dichiara
— è la regola 2, niente «funziona» senza prova. Il resto della famiglia è
chiuso e sta in [AS-IS.md](AS-IS.md).

- [ ] **Verificare sul campo il giudizio LLM (C4/C2)** con una credenziale
      Anthropic reale: la chiamata non è mai stata eseguita, solo simulata, ed
      è l'unica area del referto in questa condizione. Il README la promette
      ([README.md:220](README.md#L220)). Il referto JSON conserva per intero
      motivazione, punti forti e deboli, quindi è il formato giusto per
      controllarne l'esito. **Bloccata su una chiave**, non sul codice.
- [ ] **`evaluate_answer` di `mars_citations.py` non è chiamata da alcun
      test.** È la funzione che decide se una risposta cita il sito — la
      misura centrale dello strumento — ed è pura, quindi verificabile senza
      rete né chiavi. Le altre due funzioni pure che la voce C12 nominava sono
      coperte da `tests/test_citations.py` dal 2026-08-26 (R28).

---

## Idee

**Proposte, non lavoro deciso: nessuna ha una casella, e nessuna si esegue
senza conferma.** Una riga a testa; il ragionamento completo di ciascuna è
nella storia di git, `git show 8e80211:TO-DO.md`. Quando una si decide,
diventa una voce con la sua analisi e la sua casella.

Due portano qui una **misura**, e non una proposta, perché rifarla costerebbe:
sono I5 e I15, ed è l'unica ragione per cui sono più lunghe di una riga.

- **I2** — `--fail-under` per `mars_audit`, con exit code ≠ 0 sotto la soglia.
  Fatto in `mars_citations`; il codice di uscita `1` è già **riservato** per
  questo in [mars_audit.py:27](mars_audit.py#L27).
- **I3** — esporre `--rrf-k` e mostrare come cambia il consenso al variare di
  `k` (oggi `RRF_K = 60`, [mars_core.py:1706](mars_core.py#L1706)). Didattica,
  quasi gratis.
- **I4 + I9** — **quali** chunk stiano fuori dall'intersezione fra i due
  recuperatori, non quanti: `consensus_top3` già dice quanti. Le due idee sono
  una domanda sola vista da due lati, e chi ne apre una apra l'altra.
- **I5** — crawling concorrente. *Misurato il 2026-08-26:* **non realizzabile
  com'è scritta.** `_get` serializza le richieste su `self._last_request`
  ([mars_core.py:722](mars_core.py#L722)) per rispettare `Crawl-delay`, quindi
  un pool che non passa di lì viola robots.txt e uno che ci passa non guadagna
  niente. Da riscrivere su ciò che sta *attorno* al fetch — parsing,
  estrazione — oppure da chiudere.
- **I6** — cache HTTP su disco (URL + ETag/Last-Modified): rende iterabile lo
  sviluppo dei moduli senza martellare il sito bersaglio.
- **I7** — `--compare a.com b.com c.com` con tabella affiancata.
- **I8** — pesi, soglie ed elenchi (crawler IA, termini answer-shaped) in un
  file di configurazione invece che costanti sparse nel codice.
- **I10** — un `mars_perf.py` con i **controlli** dei Core Web Vitals, letti
  dallo stesso LHR senza un secondo Lighthouse. I punteggi di categoria li
  pubblica già R45: manca la parte azionabile, LCP, CLS, INP e le loro soglie.
- **I11** — verificare gli `@type` del JSON-LD contro i tipi che gli
  assistenti usano davvero, non solo la sintassi (lo dice
  [mars_schema.py:67](mars_schema.py#L67)).
- **I12** — un Dockerfile con Node, Lighthouse, Chrome, ZAP, Playwright e
  torch preinstallati: il README dedica un paragrafo a risolverne a mano i
  conflitti.
- **I14** — tetto alla dimensione della risposta HTTP: `_get` scarica il corpo
  intero senza `stream` né limite, e il `timeout` copre solo l'attesa fra i
  byte.
- **I15** — elisione italiana nella tokenizzazione: `l'azienda` resta un token
  solo. *Misurato chiudendo R18:* la correzione ovvia, `re.findall(r"\w+")`,
  è **scartata** — manda in pezzi `info@esempio.it`, `3,14` e `COVID-19`, e
  riempie l'indice di frammenti che gonfiano la lunghezza su cui BM25
  normalizza. Serve un elenco dichiarato di articoli e preposizioni elidibili,
  non una regola generale.
- **I16** — `--form-factor {mobile,desktop}` per confrontare like-for-like con
  il referto PageSpeed che il committente ha sotto gli occhi.
