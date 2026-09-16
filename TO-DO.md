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
> **I30**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
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

- **I30** — **il piano dice cosa fare, non in che ordine lavorare.** Aperta
  il 2026-09-16 su richiesta del committente: «la remediation è poco più di
  un consiglio». **Resta una decisione, ed è tua**: qui sotto ci sono quattro
  letture, misurate sul referto sintetico, e non si sceglie da sé.

  **Cosa il piano fa già**, perché la voce non finga che non ci sia nulla:
  ordina 27 interventi per gravità e guadagno, dichiara per ognuno il
  recupero di punti d'area col prima e il dopo, la corsia (misurato,
  bloccato, ignoto, nullo), lo sforzo su tre livelli, i quick win, e il
  guadagno sull'indice di citabilità col mercato che lo rende
  confrontabile. Da I20 porta anche i frammenti veri del sito e le pagine.

  **Cosa un lettore non ci trova**, misurato sulle 27 voci del golden:

  | Domanda | Oggi |
  |---|---|
  | quanto vale chiudere le prime N **insieme** | non c'è |
  | quali voci si chiudono con la **stessa** modifica | non c'è |
  | come **verifico** che una voce sia chiusa | non c'è |
  | la forma corretta da scrivere (`example`) | 16 voci su 27 |
  | dove intervenire (`params.urls`) | 24 su 27 |
  | quanto costa (`effort`) | 20 su 27 |

  - **A. Il pacchetto.** Il piano dà il guadagno di **una voce alla volta** e
    dichiara che i recuperi non sono additivi, ma non dice quanto valga
    chiudere le prime cinque insieme, né di quanto salga il **complessivo**.
    È l'unica delle quattro che non chiede prosa nuova: la stessa `R()` che
    il modulo già usa. *Misurato*: sulle prime 3, 5 e 10 voci il pacchetto
    coincide con la somma (102, 130, 170), ma dentro `mars_perf` chiudere le
    quattro voci insieme vale **42 invece di 43** — la non-additività esiste
    e morde dove un'area è vicina alla saturazione. **Se devo consigliarne
    una, è questa**: risponde a «quanto vale la giornata di lavoro», e il
    numero esiste già.

  - **B. Il raggruppamento.** L'ordine è per valore, non per come si lavora:
    *misurato*, **19 voci su 27 toccano la home** e 6 la pagina servizi, e
    chi lavora per pagina o per template se lo riordina a mano. Una vista
    per pagina userebbe `params["urls"]`, che c'è già in 24 voci su 27.
    Attenzione al confine: **raggruppare non è ri-ordinare**, e la gravità
    deve restare quella che domina — un `info` non scavalca un'avvertenza
    perché sta sulla stessa pagina.

  - **C. La verifica.** Nessuna voce dice come si controlla di averla
    chiusa. Per i controlli che MARS misura da sé la verifica **è il
    controllo stesso**, quindi la voce potrebbe dirlo invece di lasciarlo
    dedurre; per axe, Lighthouse e ZAP è lo strumento a dirlo, e per
    `wcag.media.captions_undeclared` non esiste affatto — quella voce
    dichiara già di essere un puntatore.

  - **D. Gli esempi che mancano.** `example` è valorizzato in 16 voci su 27.
    È la lettura di «completa» che I20 lasciò non scelta, e qui torna
    perché è ciò che separa «Collega ogni campo a una `<label>`» da una
    forma che si copia.

  *Un limite che vale per tutte e quattro*: quello che il piano pubblica
  sono **stime dichiarate**, e la loro onestà sta nel dirlo. Una vista che
  sommasse guadagni per farne una promessa — «chiudi questi cinque e passi
  a 80» — sarebbe un numero più bello e meno vero: la somma vale finché il
  certificato dell'area regge, e il piano lo dichiara voce per voce.
