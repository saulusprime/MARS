## Il contratto dei moduli

Un'area di audit è **un file** che espone **una funzione**:

```python
def audit(context: dict) -> dict:
    ...
```

`mars_core.load_external_module()` carica i moduli dal filesystem a
runtime; `MODULES_REGISTRY` (in `mars_core.py`) elenca quali e in quale
ordine. Aggiungere un'area = un file più una riga nel registro.

### Cosa arriva in `context`

| chiave | contenuto |
|---|---|
| `url` | URL di partenza |
| `pages` | dict `url -> pagina` (vedi sotto) |
| `urls` | elenco degli URL scansionati |
| `chunks` | lista di `{"url", "heading", "text"}` — **le unità su cui lavorano i retriever** |
| `queries` | query su cui gira la simulazione RRF; default generico nella lingua del sito |
| `discovery` | come sono state trovate le pagine: `sitemap` o `link interni` |
| `robots` | robots.txt grezzo: `found`, `text`, `sitemaps` |
| `sitemap` | statistiche della sitemap: `urls`, `with_lastmod`, `index_files`, `unreadable`… |
| `delay` | ritardo **effettivo** fra due richieste, in secondi: robots.txt può averlo alzato con `Crawl-delay`. Chi rivisita le pagine (il browser di `mars_wcag`) deve rispettarlo |
| `llm` | `auto` / `on` / `off`: governa il solo modulo che comporta una spesa |
| `lang` | lingua del referto, `it` (predefinita) o `en`. **Non e' solo resa**: e' anche la lingua che si chiede agli strumenti esterni, i cui testi nascono al momento della misura — `--locale` di Lighthouse, il file di locale di axe. Un modulo che porta testi di terzi dichiara in `params["text_lang"]` la lingua in cui sono davvero, cosi' il referto puo' dirlo |
| `embeddings_model`, `force_proxy` | scelta del recuperatore vettoriale |
| `market` | mercato per la citabilità: `global` (predefinito), `eu`, `us`, `cn`. Lo legge `mars_citability` — pesa gli assistenti e, dove c'è una ragione concreta, moltiplica un segnale (oggi solo l'accessibilità per `eu`, European Accessibility Act) |
| `robots_ignored` | `True` se è stata dichiarata la proprietà del dominio |
| `owner_declaration` | dichiarazione di proprietà: abilita anche l'active scan WAPT |
| `credentials` | chiavi fornite dal chiamante API (`anthropic_api_key`, `hf_token`, `zap_api_key`, `zap_proxy`); i moduli le preferiscono all'ambiente |
| `skipped` | motivo di ogni URL scartato dal crawler |

Ogni **pagina** contiene `title`, `text`, `headings`, `html`, `lang`,
`chunks`, `json_ld`, `images`, `meta_robots`, `meta_robots_by_agent`,
`canonical`, `x_robots_tag`, più la struttura che `estrai_struttura()`
legge sullo stesso DOM: `heading_levels`, `form_fields`, `tables`,
`links`, `tabindex`. Sono già estratti dal crawler: **non riparsare
l'HTML** in un modulo, il DOM è già stato attraversato una volta.

`meta_robots` porta **solo** i `<meta name="robots">`, quelli che
valgono per ogni crawler. Le direttive rivolte a un agente solo —
`<meta name="googlebot">` — stanno in `meta_robots_by_agent`, un dict
`agente -> direttive`, e valgono come il prefisso dell'`X-Robots-Tag`:
escludere Google non è escludere gli assistenti. Finché stavano nella
stessa stringa i due casi ricevevano lo stesso giudizio, e quale meta
portasse che cosa era perduto prima di arrivare al modulo — R51. Quali
nomi di meta contino come agente lo dichiara `META_ROBOTS_AGENTI` in
`mars_core`, ed è un elenco corto per scelta: che un `<meta
name="gptbot">` sia letto da GPTBot non è verificato, e il limite si
dichiara invece di assumerlo.

Il crawler estrae **dati grezzi, non giudizi**: `role="presentation"` su
una tabella arriva com'è, decidere che esenti dal criterio tocca al
modulo. Le uniche cose già risolte sono quelle che richiedono il
documento intero e a valle non sarebbero più ricostruibili — la
`<label for>` che punta a un campo e la `<label>` che lo avvolge.
Servono altri dati? Si aggiungono lì, non si riapre l'HTML: legarsi a
`pagina["html"]` significa che smettere di conservarlo svuoterebbe i
controlli **senza un errore**.

### Cosa restituire

`score` (0-100) e `issues` (lista di stringhe) sono opzionali ma
riconosciuti dal referto. Chiavi aggiuntive sono libere.

Se `audit()` solleva o non restituisce un `dict`, l'area **non
sparisce**: il referto la mostra con `status: "error"` e il motivo fra i
rilievi (`normalizza_risultato()` / `errore_modulo()` in `mars_core`).
Un'area persa in silenzio è peggio di una dichiarata fallita — vedi R22.

**`score: None` più `status: "unavailable"` quando l'area non è stata
misurata** — strumento assente, sito irraggiungibile. Non è la stessa
cosa di `score: 0`, che è un giudizio. Il referto le distingue e stampa
`non misurato`.

**Un rilievo è un CONTROLLO, non un'occorrenza**, e dichiara le pagine
su cui è scattato in `params["urls"]`. Lo stesso difetto su venti
pagine resta **un** rilievo: la cardinalità dei rilievi è accoppiata al
punteggio in tutta MARS, e spezzarlo per pagina moltiplicherebbe la
penalità per venti. Il conteggio (`pagine`, `immagini`, `nodes`…) dice
quanto, `urls` dice dove — sono due domande diverse e convivono. Chi
legge quella lista è `pagine_del_rilievo()` in `mars_core`, e la
treemap del referto vi si colora sopra. Un modulo che la pagina la sa e
non la dichiara toglie il rilievo dalla treemap **senza un errore** —
vedi R47. Il campo `doc_url` è un'altra cosa: il link alla
documentazione della regola dello strumento, mai una pagina del sito.
