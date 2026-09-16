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
> **Frontiera della numerazione**: correzioni fino a **R73**, idee fino a
> **I29**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
> successivo; i numeri che qui mancano sono voci chiuse e stanno in
> [AS-IS.md](AS-IS.md), che le indicizza tutte.
>
> **Vincolo permanente** (da U3 in poi): ogni cambiamento di resa fa fallire i
> golden di `tests/golden/`, e la rigenerazione va sempre seguita dalla
> **revisione del diff** — non si rigenera per far tornare il verde.
>
> **Nessuna casella aperta.** Il programma UPGRADE è chiuso, salvo la fase
> che il piano stesso dichiara opzionale. La cronologia di ciò che è stato
> chiuso — difetto, soluzione e prove, voce per voce — sta in
> [AS-IS.md](AS-IS.md), che la indicizza tutta: qui resta solo ciò che deve
> ancora essere fatto, e ripetere là il racconto lo farebbe divergere.
>
> **Lo stato del sistema** — versioni, strumenti presenti, limitazioni
> dichiarate — sta in testa ad [AS-IS.md](AS-IS.md), e si legge prima di
> aprire una voce nuova: diverse proposte plausibili sono già chiuse o già
> dichiarate come limite.
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
- **I11** — verificare gli `@type` del JSON-LD contro i tipi che gli
  assistenti usano davvero, non solo la sintassi (lo dice
  [mars_schema.py:67](mars_schema.py#L67)).
- **I14** — tetto alla dimensione della risposta HTTP: `_get` scarica il corpo
  intero senza `stream` né limite, e il `timeout` copre solo l'attesa fra i
  byte.

- **I20** — **resta una decisione, ed è tua.** Il committente ha scelto
  il 2026-09-01 la prima delle tre letture di «completa»: il piano copre
  ogni rilievo che descriva un difetto del sito, `info` compresi. Sta in
  [AS-IS.md](AS-IS.md), insieme al difetto che quella scelta ha scoperto
  — tre controlli Lighthouse **non falliti** erano entrati nel piano, e
  ora ne restano fuori per la penalità dichiarata.

  - **Privacy.** Il referto incorpora contenuto del sito: uno `src`, il
    testo di un titolo, il valore di un header.
    [CLAUDE.md](CLAUDE.md) impone di oscurare i dati personali, e oggi
    il contenuto entra intero. Il presidio contro l'**esecuzione** c'è
    ed è provato con un payload vero; l'**oscuramento** no, perché è
    una scelta e non una misura.

  *Le altre due letture di «completa» restano possibili e non sono
  state scelte*: colmare i 12 esempi mancanti a catalogo, e l'ordine di
  lavoro per istanza — che ora è quasi solo resa, perché gli elementi
  ci sono.

  *Una cosa che il piano non dice ancora*: la vista testo si ferma a
  cinque voci e dichiara il troncamento, quella HTML le stampa tutte.
  Con 27 voci la differenza si vede.
