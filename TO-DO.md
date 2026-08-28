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
> **I18**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
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
> guardato da chi lo riceve, e R61 dal chiudere R60. **Il 2026-08-28 si è
> chiuso il resto**: C4/C2 verificata sul campo con una chiave vera e una
> chiamata vera, e la chiamata ha trovato **R63**; l'ultima prova mancante —
> `evaluate_answer` — chiusa lo stesso giorno, e la misura che l'ha aperta è
> che **sei mutazioni su sei** su quella funzione lasciavano la suite verde;
> **U10.1**, **U10** e **U11**, cioè le ultime fasi del programma. **I2**,
> **I8**, **I4+I9** e **I15** sono le prime idee decise dopo la chiusura del
> programma, e **I18** e' la prima voce NUOVA aperta dopo di essa — la
> correzione con esempio per l'area SEO, chiesta e chiusa lo stesso giorno: non avevano
> una casella, e l'hanno avuta quando l'utente ha detto di farle. I8 è stata
> realizzata **in forma ridotta e dichiarata**: un modulo `mars_config.py`, non
> il file di configurazione che l'idea chiedeva — la ragione sta in
> [AS-IS.md](AS-IS.md), e chi volesse il file esterno riapra una voce invece di
> credere che I8 lo abbia già fatto.
>
> `__version__` è salita a **2.10.0** con R63, perché da lì i punteggi si
> muovono a sito invariato; a **2.11.0** con U10.1, che non muove alcun
> punteggio ma aggiunge una famiglia di rilievi; a **2.12.0** con U10, a
> **2.13.0** con U11, a **2.14.0** con I2, a **2.15.0** con I4+I9, che
> aggiunge contenuto al referto, a **2.16.0** con I15, da cui i punteggi
> lessicali si muovono a sito invariato, e a **2.17.0** con I18. I8 non l'ha mossa: nessun punteggio
> cambia e nessuna interfaccia con lei.
>
> **Da I15 si sa una cosa sui golden**: colgono un tokenizzatore morto, non
> uno sbagliato — il ritorno a `.lower().split()`, cioè la regressione di R18,
> li lascia verdi. Misurato, e scritto in [AS-IS.md](AS-IS.md): il presidio di
> `tokenize` sono i test unitari.
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

## Completamento

**Nessuna aperta**

---

## Idee

- **I7** — `--compare a.com b.com c.com` con tabella affiancata.
- **I10** — un `mars_perf.py` con i **controlli** dei Core Web Vitals, letti
  dallo stesso LHR senza un secondo Lighthouse. I punteggi di categoria li
  pubblica già R45: manca la parte azionabile, LCP, CLS, INP e le loro soglie.
- **I11** — verificare gli `@type` del JSON-LD contro i tipi che gli
  assistenti usano davvero, non solo la sintassi (lo dice
  [mars_schema.py:67](mars_schema.py#L67)).
- **I14** — tetto alla dimensione della risposta HTTP: `_get` scarica il corpo
  intero senza `stream` né limite, e il `timeout` copre solo l'attesa fra i
  byte.
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
