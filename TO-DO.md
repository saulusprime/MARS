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
> **Frontiera della numerazione**: correzioni fino a **R61**, idee fino a
> **I16**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Cinque caselle aperte, e nessuna è una correzione**: da R55 a R61 sono
> tutte aperte e chiuse il 2026-08-27, nate da osservazioni dell'utente sul
> campo e non da una revisione — due da un sospetto su `--max-pages`, tre da un
> giudizio LLM che annunciava un invio mai partito, R60 da un referto vero
> guardato da chi lo riceve, e R61 dal chiudere R60. Restano il programma
> UPGRADE e due prove mancanti.
>
> **I principi** stanno in [.claude/principi.md](.claude/principi.md), che
> CLAUDE.md monta in ogni sessione, e valgono anche qui: una voce che per
> essere realizzata chiede di sostituire un algoritmo core con una libreria, o
> di rendere obbligatoria una dipendenza oggi opzionale, è una voce da
> riscrivere, non da eseguire.

---

## Correzioni

**Nessuna aperta.** Le quattro del 2026-08-27 sono chiuse lo stesso giorno e
stanno in [AS-IS.md](AS-IS.md): **R57** (la CLI non aveva **alcun** modo di
passare una credenziale — `--credentials FILE`), **R58** (l'annuncio della
spesa si
stampava anche quando nulla sarebbe partito) e **R59** (diagnostica e referto
sullo stesso canale). Chiudendo R59 si è misurato che la seconda voce che
quella lasciava intravedere — le stampe di `mars_citations.py` — **non
esisteva**: là i due canali erano già separati. **R60** — gli esempi di
correzione si leggevano come contenuto misurato del sito — ne ha aperta e
chiusa una sesta, **R61**: l'etichetta «Correzione:» stava nel CSS, e un
referto inglese la diceva in italiano.

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
      ([README.md:246](README.md#L246)). Il referto JSON conserva per intero
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
  `k` (oggi `RRF_K = 60`, [mars_core.py:1810](mars_core.py#L1810)). Didattica,
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
