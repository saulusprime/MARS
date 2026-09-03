# La pagina di M.A.R.S. Beacon per lymphatechnologies.com

**Non è un sito a sé: è il corpo di una pagina del sito**, nella stessa
forma di [/it/ia-agenti-e-rag](https://www.lymphatechnologies.com/it/ia-agenti-e-rag).
Testata, piede, menu, cookie e font li mette il sito.

| File | Cosa fa |
|---|---|
| `pagina-mars-beacon.html` | **Il frammento da incollare.** Uno `<style>`, una `<section class="lt-hero">`, una `<section class="section">` e uno `<script>` |
| `anteprima.html` | Involucro di sola anteprima: carica il frammento con i CSS veri del sito. **Non si pubblica** |

---

## Come si incorpora

Il contenuto di `pagina-mars-beacon.html` va **dentro `#main-container`**,
esattamente come nella pagina di riferimento. Nient'altro: niente
`<html>`, niente `<head>`, nessun foglio di stile aggiuntivo.

Da rivedere prima di pubblicare, perché dipendono da dove archiviate la
pagina:

- il **breadcrumb** dice `Home / Sviluppo / M.A.R.S. Beacon`;
- l'**occhiello** sopra il titolo dice `Sviluppo`;
- l'`action` del modulo punta a `/it/mars-beacon-accesso`;
- i link a `/it/termini-di-servizio` e `/it/privacy`.

## Che cosa prende dal sito e che cosa porta con sé

**Dal sito**: Bootstrap Italia (`container`, `row`, `col-*`, `g-*`,
`btn btn-primary`, `btn btn-outline-primary`, `btn-sm`, `breadcrumb`),
`lympha-brand.css` (`.lt-hero`, `.lt-hero__wave`, `.lt-hero__content`,
`.lt-check`, `.eyebrow`, `.lead`) e i font.

**Con sé**: il proprio `<style>` e il proprio `<script>`. Nessuna origine
esterna — nessun CDN, nessun font remoto, nessuna immagine — quindi non
tocca la CSP né il consenso Cookiebot.

**Non dipende da jQuery.** Il sito lo carica, ma legarcisi renderebbe
questa pagina fragile a un suo aggiornamento.

## Le due regole che tengono il frammento dentro i suoi confini

1. **Tutto il CSS è ancorato a una classe `.mars`**, che sta su entrambe
   le sezioni. Un selettore di elemento nudo — `h2`, `label`, `pre` —
   uscirebbe da qui e arriverebbe su ogni altra pagina del sito. Un
   controllo statico lo verifica: vedi sotto.
2. **Ogni classe e ogni id nostri cominciano per `mars-`.** I prefissi
   corti (`mb-`, `ms-`, `mt-`) sono utilità di Bootstrap: riusarli
   significherebbe sovrascriverle in tutto il sito.

Lo script cerca i propri nodi **dentro** `.section.mars` e non nel
documento: se un domani questa pagina convivesse con un altro frammento,
non si ruberebbero i nodi a vicenda.

## Vedere il risultato prima di pubblicare

`fetch()` su `file://` è vietato dal browser, quindi serve un server:

```bash
python3 -m http.server -d landing 8080
# poi http://127.0.0.1:8080/anteprima.html
```

L'anteprima **carica** il frammento invece di copiarlo: due copie
divergerebbero, e quella sbagliata sarebbe proprio la copia che si
guarda.

## L'anteprima del referto

I numeri e il dominio sono **inventati**, e la pagina lo dichiara due
volte. Il dominio è `acme-manifatture.example`: `.example` è riservato
dalla RFC 2606, quindi non può esistere.

La **resa** invece è quella vera, presa da un referto reale: stessa
scala (critico sotto 50, da migliorare 50-89, buono da 90), stesso
vocabolario, e la stessa geometria dei quadranti — `r=56`, circonferenza
`351,86`, offset `351,86 × (1 − voto/100)`. Un 77 dà
`stroke-dashoffset="80.93"` nel referto e qui.

Il referto vero da cui viene lo spunto è di un sito reale con punteggi
reali: non finisce in una pagina commerciale.

## Accessibilità

Una pagina che vende un audit di accessibilità non può fallire i propri
criteri.

- I tre colori di gravità sono quelli del referto e vengono da Bootstrap
  Italia, che il sito già usa. Quelli di Lighthouse — `#0cce6b`,
  `#ffa400` — stanno a 2,09:1 e 1,99:1 su bianco.
- **Quindici contrasti calcolati**: il più basso fra i testi è 4,62:1
  contro una soglia di 4,5:1. Il bordo dei campi è `#748891` e non un
  grigio più chiaro perché WCAG 1.4.11 chiede 3:1 per il contorno di un
  componente: sta a 3,70:1, e la prima stesura stava a 2,24:1 —
  misurato, non supposto.
- Ogni tinta del foglio o è misurata o è **dichiarata esente con la sua
  ragione**: una tinta nuova fa fallire la verifica finché qualcuno non
  dice a quale delle due categorie appartiene.
- Il colore non viaggia mai da solo: la parola lo accompagna sempre, e
  gli errori del modulo portano un simbolo oltre al colore (1.4.1).
- Il movimento sta dietro `prefers-reduced-motion`.
- Il riassunto degli errori riceve il fuoco e ogni voce porta al proprio
  campo: un `role="alert"` fuori dallo schermo viene letto e poi perso.

## Il modulo

Raccoglie ragione sociale, sito da analizzare, nome, ruolo, email
aziendale, telefono e tre spunte obbligatorie — termini, privacy,
responsabilità.

L'email aziendale è verificata contro un **elenco dichiarato** di 28
provider personali, corto per scelta: dedurre «personale» da una regola
generale produce falsi rifiuti, e un rifiuto sbagliato costa più di un
lead in più da guardare. L'URL si valida col parser del browser e non
con una regex — gli URL sono dato ostile anche qui.

La spunta di responsabilità non è una formula legale: **è
`--i-own-this-domain`**. Senza, la scansione attiva resta disattivata, e
la dichiarazione finisce registrata nel referto.

Il modulo ha `action` e `method`: senza JavaScript si invia lo stesso e
lo valida il server. Lo script **migliora, non abilita** — e quando i
campi sono validi non chiama `preventDefault()`, quindi l'invio prosegue.

## Verifica

Fatta staticamente, con `landing/verifica.py`:

```bash
.venv/bin/python landing/verifica.py
```

Controlla che ogni selettore CSS sia ancorato a `.mars`, che ogni id
cercato dallo script esista, che ogni `<label for>` e ogni
`aria-describedby` puntino a qualcosa, che non ci siano origini esterne,
che ci sia un solo `<h1>` senza salti di gerarchia e che nessuna lista
abbia figli che non siano `<li>`.

**Non verificato**: il frammento non è mai stato aperto in un browser —
su questa macchina non c'è né Node né un Chromium fuori dall'immagine —
quindi la resa dentro Bootstrap Italia, il comportamento dei bottoni e
la validazione live restano da guardare con `anteprima.html`.
