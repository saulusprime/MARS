# La pagina di M.A.R.S. per lymphatech.it

**Una pagina intera e autoconsistente**, nella stessa forma delle altre
pagine del sito: si apre da sola in un browser, con testata, menu, piede
e fogli di stile suoi.

| File | Cosa fa |
|---|---|
| `mars-beacon.html` | **La pagina.** Si apre così com'è: `xdg-open landing/mars-beacon.html` |
| `ia-agenti-rag.html` | La pagina del sito da cui viene il telaio. Sta qui per il diff: se il telaio del sito cambia, la differenza si vede invece di doverla cercare |
| `logo.png` | Il marchio del prodotto, 744×752. **Nostro**, quindi versionato: `assets/` non lo e' |
| `verifica.py` | I controlli statici, descritti in fondo |
| `assets/` | Bootstrap Italia, `lympha.css`, `lympha.js`, font e immagini del sito. **Non versionata** — vedi sotto |

---

## `assets/` non sta in questo repository

Sono 11 MB e 254 file, e sono **del sito**: Bootstrap Italia, il foglio e
lo script di lymphatech.it, i suoi font, le sue immagini. Duplicarli
nella storia di MARS non serve a nessuno, e la pagina li ritrova da sé
quando viene messa accanto al sito.

Su un clone appena fatto la cartella manca, la pagina si apre nuda e
`verifica.py` **lo dichiara** invece di fallire: un controllo verde qui e
rosso altrove renderebbe la verifica dipendente dalla macchina, che è la
trappola già pagata con `node_modules`.

Per rivederla come sarà: copiare `assets/` dal sito accanto a
`mars-beacon.html`.

## Che cosa è nostro e che cosa è del sito

**Del sito**, copiato da `ia-agenti-rag.html` **senza ritocchi**: il
`<head>` (a meno di titolo, descrizione, canonical, OG e breadcrumb
JSON-LD), la testata col menu, il piede. L'unica modifica è la voce di
questa pagina aggiunta al menu **Sviluppo** — che va aggiunta anche alle
altre pagine del sito, altrimenti il menu di M.A.R.S. elenca una
voce che le sorelle non hanno.

**Nostro**: tutto ciò che sta dentro `<main>`, più lo `<style>` nel
`<head>` e lo `<script>` in fondo. Nessuna origine esterna: nessun CDN,
nessun font remoto, nessuna immagine di terzi, quindi la nostra parte non
tocca né la CSP né il consenso Cookiebot. Il piede del sito un badge
esterno ce l'ha — è suo, ed è rimasto com'era.

**Non dipende da jQuery**, e non dipende nemmeno da `lympha.js`: senza
quello l'indice laterale perde solo l'evidenziazione della sezione
corrente.

## Le due regole che tengono il nostro CSS dentro i suoi confini

1. **Tutto il CSS nostro è annidato sotto `.mars`**, che sta su entrambe
   le sezioni. Un selettore di elemento nudo — `h2`, `label`, `pre` — non
   farebbe danno finché la pagina è sola, ma il giorno in cui il file
   entra nel sito arriverebbe su ogni altra pagina. `verifica.py` lo
   controlla.
2. **Ogni classe e ogni id nostri cominciano per `mars-`.** I prefissi
   corti (`mb-`, `ms-`, `mt-`) sono utilità di Bootstrap: riusarli
   significherebbe sovrascriverle in tutto il sito.

Lo script cerca i propri nodi **dentro** `.section.mars` e non nel
documento.

## Che cosa riusa del sito, invece di rifarlo

L'indice laterale è un `<nav class="lt-toc" data-toc>` e l'articolo porta
`data-article`: sono i due agganci che `lympha.js` cerca per evidenziare
la sezione corrente durante lo scorrimento. Prima quell'indice aveva il
proprio CSS e nessuna evidenziazione; ora ha quella del sito e cinque
righe di foglio in meno.

Sopra l'indice ci sono le pagine della sezione **Sviluppo**, come in
`ia-agenti-rag.html`, con questa marcata `aria-current="page"`.

## I link da rivedere prima di pubblicare

Dipendono da dove archiviate la pagina, e oggi puntano a:

- `index.html`, `sviluppo.html` — breadcrumb e colonna laterale;
- `mars-beacon-accesso.html` — l'`action` del modulo, **pagina che non
  esiste ancora**;
- `termini-di-servizio.html` — **non esiste ancora**;
- `privacy-cookie.html` — questa c'è, è quella del piede.

L'occhiello sopra il titolo e il breadcrumb dicono `Sviluppo`.

## Il marchio

`logo.png` sta accanto al sommario, non nell'hero: il titolo il nome lo
dice gia', e li' l'immagine sarebbe stata una ripetizione. L'`alt` e'
**vuoto di proposito** per la stessa ragione — un lettore di schermo
direbbe «M.A.R.S.» due volte a due dita di distanza.

`width` e `height` ci sono: senza, la riga di testo salta quando
l'immagine arriva, ed e' il CLS che il prodotto misura sui siti dei
clienti.

**Pesa 352 KB per mostrarsi a 96 pixel**, ed e' un difetto vero: su
questa macchina non c'e' nulla per ridimensionare un PNG — niente PIL,
niente ImageMagick — quindi la riduzione la fa il browser a ogni
visita. Prima di pubblicare va rifatto a misura (192 px per gli schermi
a densita' doppia), o convertito in SVG.

Quando la pagina va sul sito il file la segue: sta accanto a
`mars-beacon.html`, non in `assets/img/`, perche' e' nostro e
`assets/` non entra in git.

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

Undici controlli: ogni selettore CSS ancorato a `.mars`; ogni id cercato
dallo script esistente; ogni `<label for>` e ogni `aria-describedby` che
puntano a qualcosa; nessuna origine esterna **dentro `<main>`**; un solo
`<h1>` senza salti di gerarchia; nessuna lista con figli che non siano
`<li>`; i quindici contrasti; ogni tinta misurata o esente con la sua
ragione; ogni immagine e ogni file di `assets/` citati che esistono
davvero, e ogni immagine con `width` e `height`; il telaio del sito
arrivato tutto, agganci allo scrollspy compresi; ogni ancora interna che
porta a un id che c'e'.

Dodici mutazioni provate una per una e **dodici colte**: `data-article`
tolto, un percorso di `assets/` sbagliato, lo script del sito rimosso, un
CDN dentro `<main>`, una `<label for>` rotta, un `h2` nudo nel foglio, un
colore non dichiarato, un secondo `<h1>`, il logo che non c'e', il logo
senza `width`/`height`, il logo preso da un CDN, un'ancora dell'indice
che non porta a nessun id.

**Non verificato**: la pagina non è mai stata aperta in un browser — su
questa macchina non c'è né Node né un Chromium fuori dall'immagine —
quindi la resa dentro Bootstrap Italia, i menu a tendina, l'onda animata
dell'hero, il comportamento dei bottoni e la validazione live restano da
guardare.
