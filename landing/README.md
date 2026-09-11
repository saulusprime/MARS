# landing/ — la pagina di presentazione di M.A.R.S.

HTML, CSS e JavaScript vanilla. Nessuna dipendenza, nessuna compilazione:
si apre `index.html` e funziona.

| File | Che cos'è |
|---|---|
| `index.html` | La pagina. Una sola. |
| `styles.css` | Tema unico e chiaro, con le fasce scure come fasce e non come secondo tema. |
| `app.js` | Menu, rivelazione allo scorrimento, simulazione RRF, profili di citabilità. |
| `logo.png` | Il logo a 288 px (75 KB), ridotto dai 744 px dell'originale in radice. |
| `favicon.ico` | Copia di quella di M.A.R.S. |

Per vederla in locale, da questa cartella:

```bash
python3 -m http.server 8080
```

## I dati non sono inventati

I numeri della pagina vengono dal programma, non da una brochure:

- le **dieci aree** sono `MODULES_REGISTRY` di `mars_core.py`, nello stesso ordine;
- la **matrice dei pesi** e i **pesi di mercato** dei profili di citabilità sono
  quelli di `mars_citability.py`, moltiplicatore dell'accessibilità per il
  mercato UE compreso;
- la **formula RRF** e il valore predefinito `k = 60` sono quelli veri; i ranghi
  delle due liste sono d'esempio, e la pagina lo dichiara;
- **colori, forme e scala tipografica** vengono dagli stili *calcolati* di
  `www.lymphatechnologies.com/it`, letti col browser e non dedotti a occhio:
  le variabili Bootstrap Italia del sito (`--bs-primary` `#186078`,
  `--bs-link-color` `#0f4a5b`, `--bs-secondary` `#5d7083`, `--bs-body-color`
  `#14272b`), i due gradienti radiali dell'eroe e della fascia scura copiati
  alla lettera, le card a **20px** con bordo `rgba(8,49,58,.12)` e padding
  **28px**, i pulsanti a **4px** di raggio e peso 600, il piede `#0c3540` con
  testo `#cdd8e4`, Titillium Web per il testo e Roboto Mono per il codice.

**L'arancio `#d86010` è quello del sito, e si comporta come lì**: un filetto
di 28×2 px prima dell'occhiello e una velatura al 18% nell'eroe. Sul sito non
è mai testo, e qui non lo diventa — su bianco starebbe a 4,0:1.

Se uno di quei moduli cambia, questa pagina non se ne accorge: i valori sono
copiati, non letti. È una copia dichiarata, non un collegamento.

**E la copia è doppia.** Lo stato iniziale — le tre classifiche a `k = 60`, i
quattro assistenti sul mercato globale, le sette righe della matrice — sta
*sia* nel markup di `index.html` *sia* in `app.js`, che lo ridisegna al primo
giro. Serve a chi non ha JavaScript, e il prezzo è che i due possono divergere
senza che nulla lo segnali. Chi tocca l'uno tocchi l'altro, e verifichi che il
testo delle sette zone (`#list-lex`, `#list-vec`, `#list-rrf`, `#assistants`,
`#matrix-body`, `#market-note`, `#k-consensus`) sia identico con e senza
script.

## Il modulo «Richiedi un check-up preliminare»

È la ricostruzione del blocco `i07ziu` di
`www.lymphatechnologies.com/it/mars`, preso col browser dalla pagina viva. I
`name` dei campi sono quelli veri — `CustomForms[ragione_sociale]`,
`CustomForms[sito]`, `CustomForms[name]`, `CustomForms[ruolo]`,
`CustomForms[email]`, `CustomForms[telephone]`, e le tre caselle
`termini_servizio`, `ricontatta`, `dichiaro` — perché è su quelli che il
backend riconosce i dati. Ogni casella conserva il suo `input` nascosto
omonimo a `0`: è l'idioma CakePHP per la casella non spuntata, e toglierlo
cambierebbe ciò che arriva al server.

**Tre valori li genera il server a ogni render, e qui sono vuoti**:
`_csrfToken`, `_Token[fields]` e il token ALTCHA. Non sono dimenticanze e non
vanno riempiti a mano: sono legati alla sessione e scadono. Perché il modulo
funzioni, **questa pagina deve essere resa dallo stesso CMS** che li inietta.

**Se non lo è, il modulo non invia e lo dice.** `app.js` controlla
`_csrfToken` prima di lasciar partire la POST: se è vuoto blocca l'invio,
mostra un avviso e rimanda al modulo sul sito. Senza quel controllo la
richiesta partirebbe, il server la rifiuterebbe e il contatto sparirebbe
**senza che nessuno se ne accorga**.

**Il captcha non è finto.** Dove il sito monta il widget ALTCHA c'è un
contenitore vuoto, `#altcha-slot`: una casella «I'm not a robot» che non
verifica nulla ingannerebbe chi la spunta.

**Tre scostamenti dall'originale, dichiarati.** I tipi dei campi sono `email`
e `tel` invece di `text` — cambia la tastiera sul telefono e la validazione
del browser, non ciò che viene inviato. Le etichette delle due caselle di
consenso rimandano ai documenti (`../docs/TOS.md`, `../docs/PRIVACY.md`), che
sull'originale sono testo senza collegamento: un consenso privo del documento
da leggere è un consenso zoppo. E il rosso di errore compare con
`:user-invalid`, cioè dopo che l'utente ha scritto, non al caricamento.

## Verifiche eseguite

- **axe-core 4.13 su Chromium**, regole WCAG 2.1 A e AA, a 1280×900 e 390×844:
  **zero violazioni**, 32 e 33 controlli superati.
- **Il modulo, provato davvero**: a campi vuoti lo ferma la validazione nativa
  e l'avviso NON compare; a campi pieni senza `_csrfToken` l'avviso compare, la
  messa a fuoco ci si sposta e **l'URL non cambia**; con un token presente la
  POST parte verso `process-form` e il ripiego si toglie di mezzo.
- I nodi che axe lascia «da verificare a mano» — testo sopra un gradiente o una
  trasparenza — sono stati calcolati a parte: il peggiore è l'occhiello del
  titolo a **4,83:1** sul punto più chiaro del gradiente.
- **Tre token del sito non reggevano dove li avrei messi, e sono scesi di un
  gradino — misurato, non a gusto**: il grigio `#5d7083` sta a **3,46:1** sopra
  la velatura verde-azzurra dell'eroe, quindi lì e solo lì diventa `#455566`;
  l'azzurro d'accento `#8ecfe3` sta a **4,08:1** sul punto più chiaro del
  radiale scuro, e diventa `#a5daeb`; i pannelli della fascia scura erano
  velature bianche che *schiarivano* il fondo e portavano il testo secondario a
  **3,52:1**, e ora sono opachi (`#0e3f4f`, 7,89:1). È lo stesso genere di
  scostamento che U11.1 dovette fare sul referto, e per la stessa ragione: un
  token va bene finché non guardi il fondo su cui finisce.
- **Senza JavaScript**: 25 blocchi su 25 visibili e **10.832 caratteri di
  testo, esattamente quanti con lo script a animazione conclusa** — la classe
  che nasconde le sezioni la aggiunge lo script, non il markup, e le zone di
  dati stanno già in `index.html`. Misurato col browser a
  `java_script_enabled=False`, e le **nove zone** confrontate carattere per
  carattere fra le due modalità: **zero divergenze**. Restano inerti, e solo
  quelle, il cursore di `k`, il selettore di mercato, l'evidenziazione dei
  connettori, l'animazione del referto d'esempio e il menu a telefono.
- **Il referto d'esempio si compila da solo**: barre e punteggi partono da
  zero, restano fermi **un secondo** e poi salgono insieme — la card si legge
  prima com'è fatta, e solo dopo si riempie. Con `prefers-reduced-motion` non
  si aspetta nessun secondo e tutto è già al valore finale.
- **Lo zero delle barre sta nel CSS, non in `app.js`, ed è una correzione di
  un difetto vero**: `app.js` è `defer`, quindi gira dopo l'analisi del
  documento, e fra l'analisi e la sua esecuzione il browser può avere già
  disegnato un fotogramma. Azzerare le larghezze da JavaScript era una corsa
  con quel fotogramma, e a perderla le barre si vedevano **già piene** —
  peggio, l'azzeramento tardivo diventava una transizione all'indietro.
  Misurato con Chromium: su cinque caricamenti identici **uno la perdeva**.
  Con `@keyframes` e `animation-delay:1s` lo zero è nello stile dal primo
  fotogramma: 8 caricamenti su 8, e 9 su 9 con la CPU rallentata fino a 8×,
  partono da zero; regge anche con `app.js` fatto arrivare 1,5 s in ritardo,
  su Chromium e su Firefox. In più l'animazione ora funziona **anche senza
  JavaScript**, perché a farla è il foglio di stile.
- **I numeri, che solo JavaScript può toccare**, si agganciano ad
  `animationstart` della prima barra: l'evento scocca a ritardo scaduto, così
  cifre e barre salgono insieme senza che lo script debba indovinare
  l'orologio del CSS. Se l'animazione non scocca, una rete di sicurezza li fa
  salire lo stesso.
- **In stampa la barra esce piena** anche se si stampa dentro il secondo di
  attesa: `@media print` annulla l'animazione invece di lasciarla congelata a
  zero.
- **La gravità è a dieci gradini da 10 punti l'uno**: `none` (0-10),
  `verybad`, `bad`, `notsobad`, `hotwarn`, `verywarn`, `warn`, `semiok`,
  `quasiok`, `ok` (90-100). Ogni gradino sfuma dal colore del gradino sotto al
  proprio, così due barre vicine sono due tratti della stessa rampa e non due
  tinte piatte. Le tre tinte del referto non si sono mosse — `--bad` sta al
  gradino 20-30, `--warn` al 60-70, `--ok` al 90-100 — e le sei nuove in mezzo
  le interpolano: la più debole, `--g-verywarn`, dà **4,93:1 su bianco e
  4,02:1 sul `--track`** su cui la barra poggia davvero, contro i 3:1 che le
  chiederebbe una superficie non testuale. La classe sta nel markup, per chi
  non ha JavaScript, e lo script la **riallinea al punteggio** all'avvio:
  cambiare un valore senza cambiare la classe non lascia una barra del colore
  sbagliato.
- In stampa le sezioni non restano bianche: `@media print` annulla la
  rivelazione allo scorrimento, che nessun `IntersectionObserver` farebbe
  scattare su carta.
- Ogni animazione è subordinata a `prefers-reduced-motion`.

## Da cambiare prima di pubblicare

**I due link ai documenti nel piede puntano a `../docs/TOS.md` e
`../docs/PRIVACY.md`**: funzionano aprendo la cartella in locale, non su un
sito, dove quei file non sono serviti né resi in HTML. Vanno sostituiti con
gli indirizzi veri.

Il carattere Titillium Web arriva da Google Fonts, come sul sito. Se il
dominio deve restare senza chiamate a terzi, si toglie il `<link>` e la pila
di ripiego già dichiarata in `--sans` fa il resto.
