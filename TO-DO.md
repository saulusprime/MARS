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
> **Frontiera della numerazione**: correzioni fino a **R63**, idee fino a
> **I17**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Nessuna casella aperta.** Il programma UPGRADE è chiuso, salvo la fase
> che il piano stesso dichiara opzionale. Da R55 a R63 sono
> tutte aperte e chiuse il 2026-08-27, nate da osservazioni dell'utente sul
> campo e non da una revisione — due da un sospetto su `--max-pages`, tre da un
> giudizio LLM che annunciava un invio mai partito, R60 da un referto vero
> guardato da chi lo riceve, e R61 dal chiudere R60. Resta il solo programma
> UPGRADE: **C4/C2 è stata verificata sul campo** il 2026-08-28, con una chiave
> vera e una chiamata vera, e la chiamata ha trovato **R63**, chiusa lo stesso
> giorno; l'ultima prova mancante — `evaluate_answer` — è chiusa lo stesso
> giorno, e la misura che l'ha aperta è che **sei mutazioni su sei** su quella
> funzione lasciavano la suite verde. `__version__` è a **2.10.0**,
> perché da R63 i punteggi si muovono a sito invariato — a **2.11.0** da
> U10.1, che non muove alcun punteggio ma aggiunge una famiglia di rilievi, a
> **2.12.0** da U10 e a **2.13.0** da U11.
>
> **I principi** stanno in [.claude/principi.md](.claude/principi.md), che
> CLAUDE.md monta in ogni sessione, e valgono anche qui: una voce che per
> essere realizzata chiede di sostituire un algoritmo core con una libreria, o
> di rendere obbligatoria una dipendenza oggi opzionale, è una voce da
> riscrivere, non da eseguire.

---

## Correzioni

**Nessuna aperta.**

---

## Programma UPGRADE

Il piano sta in [UPGRADE.md](UPGRADE.md), il quadro delle nove fasi chiuse e le
decisioni D1-D4 in [AS-IS.md](AS-IS.md). Dove piano e realizzazione divergono
ha ragione AS-IS. **Nessuna fase resta aperta**: U10 e U11 sono chiuse il
2026-08-28 e stanno in [AS-IS.md](AS-IS.md). Resta la sola **U12** (ancore
esterne, Brave Search e confronto competitivo), che il piano dichiara
**opzionale** e che per questo non ha una casella: se si decide di farla, la
casella si aggiunge.

Due cose che la Fase 11 chiedeva **non sono state fatte**, e sono decisioni,
non caselle: il logo e il carattere del sito incorporati nel referto — li
esclude il perimetro che hai fissato in U11.1, col costo misurato — e il
white-label da TOML, che il piano stesso rimanda a quando MARS avrà una GUI.


---

## Completamento

**Nessuna aperta**

---

## Idee

- **I2** — `--fail-under` per `mars_audit`, con exit code ≠ 0 sotto la soglia.
  Fatto in `mars_citations`; il codice di uscita `1` è già **riservato** per
  questo in [mars_audit.py:27](mars_audit.py#L27).
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
- **I17** — il consenso aggregato regge il segnale «Recuperabilità», che entra
  nel complessivo, ed è **fragile rispetto a k**. *Misurato il 2026-08-27
  chiudendo I3, sullo stesso sito e nello stesso minuto:* 3/3 e complessivo
  77.9 con `--rrf-k 10`, 0/3 e complessivo 59.2 con il predefinito 60. Le
  strade sono tre e vanno decise, non dedotte: lasciare tutto com'è ora che il
  referto lo dichiara e lo sonda; togliere quel segnale dal complessivo, come
  già si fa per le due aree di classifica; oppure sostituirlo con una misura
  che da k non dipenda — per esempio la sovrapposizione media fra i primi N
  delle due liste per query, che è il consenso per query e infatti non si
  muove. Frontiera: **I17**.
- **I16** — `--form-factor {mobile,desktop}` per confrontare like-for-like con
  il referto PageSpeed che il committente ha sotto gli occhi.
