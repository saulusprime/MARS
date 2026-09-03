# `landing/` — la pagina di presentazione

Materiale **commerciale**, non parte del motore: nessun file qui viene
importato da `mars_*.py`, e la suite non lo esercita. Sono quattro file
statici, senza build e senza dipendenze — si aprono con un doppio clic.

| File | Cosa contiene |
|---|---|
| `index.html` | La presentazione, l'anteprima del referto, il modulo di registrazione |
| `servizio.html` | Dove il modulo porta: lo spazio del cliente, con i parametri dell'esecuzione |
| `style.css` | Un solo foglio, un solo tema |
| `app.js` / `servizio.js` | JavaScript vanilla, nessuna libreria |

```bash
python3 -m http.server -d landing 8080   # http://127.0.0.1:8080
```

Serve un server locale e non `file://` per un motivo solo: `sessionStorage`
su `file://` si comporta in modo diverso da browser a browser, e il
passaggio dei dati fra le due pagine è proprio quello.

---

## Tre cose che qui non sono decorative

**I tre colori di gravità sono quelli del referto** — `#008055`,
`#995c00`, `#cc334d` — e non sono una scelta estetica: quelli di
Lighthouse (`#0cce6b`, `#ffa400`) stanno a 2,09:1 e 1,99:1 su bianco,
sotto perfino la soglia 3:1 dei componenti. Una pagina che vende un audit
di accessibilità non può fallire i propri criteri. **Tutti** i contrasti
di testo sono stati calcolati: il più basso è 4,65:1, sopra il 4,5
richiesto. Il colore non viaggia mai da solo — accanto c'è sempre la
parola o il simbolo.

**La geometria dei quadranti è quella vera.** `r=56`, quindi
circonferenza `351,86`, e l'offset è `351,86 × (1 − voto/100)`. Verificato
contro `report.html`: un punteggio di 77 dà `stroke-dashoffset="80.93"` là
e qui. L'anteprima non somiglia al prodotto, usa il prodotto.

**I numeri dell'anteprima sono inventati, e la pagina lo dichiara** in
due punti. Il dominio è `acme-manifatture.example` — `.example` è
riservato dalla RFC 2606, quindi non può esistere. Il referto vero da cui
è preso lo spunto riguarda un sito reale con punteggi reali, e quelli non
finiscono in una pagina commerciale.

## La spunta di responsabilità non è una formula

Le tre spunte sono termini di servizio, privacy e **responsabilità**, e la
terza corrisponde a una cosa che esiste nel motore: `--i-own-this-domain`.
Senza quella dichiarazione lo spider e la scansione attiva di ZAP non
partono — lo spider di ZAP non rispetta `robots.txt` — e la dichiarazione
finisce registrata nel referto. Il testo della spunta lo dice invece di
essere un vincolo legale generico.

## L'email deve essere aziendale

`app.js` rifiuta un elenco **dichiarato** di 28 provider personali
(`gmail.com`, `libero.it`, …). È corto per scelta: dedurre da una regola
generale che un dominio sia «personale» produce falsi rifiuti, e un
rifiuto sbagliato costa più di un lead in più da guardare.

## Che cosa non è stato verificato

**Il JavaScript non è mai stato eseguito in un browser.** Su questa
macchina non c'è Node e Chromium sta solo nell'immagine del container,
quindi la validazione statica è tutto ciò che è stato fatto: HTML che
passa il parser, ogni `getElementById` che trova il suo `id`, ogni
`<label for>` che trova il suo campo, zero origini esterne, contrasti
calcolati. Prima di pubblicare, va aperta e cliccata.

**Nessun dato lascia la pagina.** Il modulo non fa una richiesta: scrive
in `sessionStorage` e cambia pagina. Per raccogliere lead davvero serve un
endpoint, e allora servono anche il consenso registrato con data e ora, la
protezione anti-bot e un posto dove i dati atterrano — nessuna delle tre
esiste qui.
