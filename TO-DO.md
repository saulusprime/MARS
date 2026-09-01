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
> **Frontiera della numerazione**: correzioni fino a **R66**, idee fino a
> **I20**, fasi UPGRADE fino a **U13**. Una voce nuova prende il numero
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
> cambia e nessuna interfaccia con lei. **I10** (2026-08-31) l'ha portata a
> **2.18.0**: nasce l'area «3. Prestazioni» e le aree 3-9 diventano 4-10 —
> le chiavi dei rilievi e lo storico non si muovono, il complessivo nemmeno,
> perché l'area ne resta fuori per decisione dichiarata. Il primo confronto
> del committente col PSI (2026-08-31) ha aperto e chiuso **R64** — la
> diffusione axe partiva dal massimo sul campione di una pagina, e da lì i
> punteggi WCAG si muovono a sito invariato — e ha deciso **I16**, che con
> `--form-factor` porta la versione a **2.19.0**. Lo stesso giorno si è
> decisa **I17** — il segnale «Recuperabilità» del complessivo e dei profili
> di citabilità è la media per query, che da k non dipende, e l'aggregato
> resta come diagnostica — e la versione è **2.20.0**, perché complessivo e
> profili si muovono a sito invariato. La revisione di I17 ha aperto **R65**
> — le code a punteggio zero regalavano consenso sulle query a riscontro
> parziale — chiusa lo stesso giorno: da lì le classifiche si fermano dove
> finiscono i riscontri, e la versione è **2.21.0**. Lo stesso giorno il
> committente ha chiesto di riprogettare l'hero, «poco dinamico»: **I19**
> lo ricompone — la variazione rispetto al giro precedente sale in testa,
> le tre tessere di uguale peso e il donut diventano due barre
> proporzionali, e il movimento sta dietro `prefers-reduced-motion` —
> e la versione è **2.22.0**. Il 2026-09-01 un audit eseguito dentro il
> container ha aperto e chiuso **R66**: il referto leggeva «Lighthouse non
> riuscito: CalledProcessError», cioè aveva la diagnosi dello strumento —
> `CalledProcessError` porta lo stderr — e la buttava via; quella non ha
> mosso la versione, perché nessun punteggio cambia e nessuna interfaccia.
> **Il pilota di I20** sì, a **2.23.0**: il referto guadagna contenuto —
> gli esempi delle aree SEO e Prestazioni, che nell'HTML non comparivano
> affatto, e il frammento VERO del sito dove Lighthouse lo fornisce —
> senza che alcun punteggio si muova, come per I18. **I20** è arrivata
> a **2.25.0** in tre giri — i controlli SEO, poi axe e ZAP, poi i
> controlli statici — e per la stessa ragione: il referto guadagna
> contenuto e nessun punteggio si muove — poi a **2.26.0** col giro che
> ha reso parlanti i tetti e ha portato il «quale elemento» nel piano.
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
- **I11** — verificare gli `@type` del JSON-LD contro i tipi che gli
  assistenti usano davvero, non solo la sintassi (lo dice
  [mars_schema.py:67](mars_schema.py#L67)).
- **I14** — tetto alla dimensione della risposta HTTP: `_get` scarica il corpo
  intero senza `stream` né limite, e il `timeout` copre solo l'attesa fra i
  byte.

- **I20** — **restano due decisioni, e sono tue.** Tutto il tecnico è
  fatto il 2026-09-01 e sta in [AS-IS.md](AS-IS.md): accanto
  all'esempio il referto elenca gli elementi del sito su cui il rilievo
  è scattato — per i controlli SEO, per axe, per ZAP e per i controlli
  statici — il tetto dei cinque elementi dichiara quanti ne restano
  fuori, e il piano di interventi dice quale elemento su una riga.

  - **Privacy.** Il referto ora incorpora contenuto del sito: uno
    `src`, il testo di un titolo, il valore di un header.
    [CLAUDE.md](CLAUDE.md) impone di oscurare i dati personali, e oggi
    il contenuto entra intero. Il presidio contro l'**esecuzione** c'è
    ed è provato con un payload vero; l'**oscuramento** no, perché è
    una scelta e non una misura.
  - **«Completa» ha tre letture**, e nessuna è stata scelta: (1) piano
    su tutti i rilievi, cioè includere i 19 `info` — codice minimo ma
    **ribalta una decisione dichiarata** in `_e_candidato`; (2) colmare
    i 12 esempi mancanti a catalogo; (3) ordine di lavoro per istanza,
    che ora è quasi solo resa, perché gli elementi ci sono.

  *Una previsione di questo file era sbagliata, e vale registrarla*: «il
  piano rende `fix` e non `example`» era annotato come difetto. Non lo
  era — `test_il_piano_html_non_ripete_gli_esempi` lo fissa come
  decisione, con la ragione. Quello che mancava era il «quale elemento»,
  ed è stato aggiunto senza toccare la decisione.
