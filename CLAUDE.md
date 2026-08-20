# MARS Beacon — istruzioni per il lavoro assistito

Contesto essenziale per chi (persona o modello) mette mano al codice.
Il quadro completo sta in [README.md](README.md), il lavoro aperto in
[TO-DO.md](TO-DO.md), quello concluso in [AS-IS.md](AS-IS.md).

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
| `llm` | `auto` / `on` / `off`: governa il solo modulo che comporta una spesa |
| `embeddings_model`, `force_proxy` | scelta del recuperatore vettoriale |
| `market` | mercato per la citabilità (previsto da C1, non ancora usato) |
| `robots_ignored` | `True` se è stata dichiarata la proprietà del dominio |
| `owner_declaration` | dichiarazione di proprietà: abilita anche l'active scan WAPT |
| `credentials` | chiavi fornite dal chiamante API (`anthropic_api_key`, `hf_token`, `zap_api_key`, `zap_proxy`); i moduli le preferiscono all'ambiente |
| `skipped` | motivo di ogni URL scartato dal crawler |

Ogni **pagina** contiene `title`, `text`, `headings`, `html`, `lang`,
`chunks`, `json_ld`, `images`, `meta_robots`, `canonical`,
`x_robots_tag`. Sono già estratti dal crawler: **non
riparsare l'HTML** in un modulo, il DOM è già stato attraversato una
volta.

### Cosa restituire

`score` (0-100) e `issues` (lista di stringhe) sono opzionali ma
riconosciuti dal referto. Chiavi aggiuntive sono libere.

**`score: None` più `status: "unavailable"` quando l'area non è stata
misurata** — strumento assente, sito irraggiungibile. Non è la stessa
cosa di `score: 0`, che è un giudizio. Il referto le distingue e stampa
`non misurato`.

## Principi da non violare

1. **Gli algoritmi core sono scritti a mano** — crawler, BM25, proxy
   char-TFIDF, RRF, chunker. Non sostituirli con librerie: sono il
   valore del progetto, non un dettaglio implementativo.
2. **Degradazione graduale.** Lighthouse, ZAP, sentence-transformers,
   Anthropic sono tutti opzionali. Se mancano si ripiega e **lo si
   dichiara**; non si solleva e non si inventa un punteggio.
3. **Moduli plugin, contratto sopra.** Il `context` e ciò che contiene
   restano **dict**: attraversano il confine dei plugin, e imporre
   classi di `mars_core` costringerebbe ogni modulo esterno a
   importarle. I `@dataclass` valgono per le strutture interne a un
   modulo.
4. **CLI e API sono due interfacce sopra lo stesso motore.**
   `build_context()`, `MODULES_REGISTRY` e `load_external_module()`
   stanno in `mars_core`: se ti trovi a copiare qualcosa fra
   `mars_audit.py` e `mars_api.py`, appartiene a `mars_core`.
5. **Onestà metodologica.** Ogni punteggio deve derivare da una misura.
   Se è una stima euristica, il referto lo dice. Se un'area non è stata
   guardata, il referto lo dice. Vale anche per le docstring: diverse
   dichiarano quanto della propria area *non* coprono ancora.
6. **Interfaccia in italiano**, identificatori in inglese.
7. **Stile di riferimento: `mars_citations.py`.** Type hints,
   `from __future__ import annotations`, I/O separato dalla logica, il
   dato prima della presentazione, docstring che spiegano il *perché*.

## Come si lavora

- **`pytest` deve restare verde**, e la suite non deve toccare la rete:
  la fixture `niente_rete` lo impedisce, ed e' `autouse` perche' nessuno
  possa dimenticarla.
- **Reintrodurre il difetto per fidarsi del test.** Un test verde non
  dimostra nulla finche' non lo si e' visto fallire.
- **`flake8` deve restare a zero.** `setup.cfg` è già configurato:
  basta `flake8 .`. È il controllo che ha rivelato il difetto più grave
  del progetto (login rotto da una funzione definita due volte).
- **Verificare, non dedurre.** Prima di correggere, riprodurre il
  difetto; dopo, dimostrare che è chiuso. Diverse voci di
  [AS-IS.md](AS-IS.md) documentano previsioni smentite dalla misura:
  registrarle vale più che cancellarle.
- **Un commit per voce del TO-DO**, e **la riformattazione in un commit
  separato** da ciò che cambia il comportamento.
- **Chiuso ≠ cancellato.** Una voce risolta si sposta dal TO-DO ad
  AS-IS con difetto, soluzione e verifiche, così nessuno rifà la stessa
  indagine.

## Trappole già pagate

Costano ore se le si reincontra senza saperlo.

- **`bcrypt` è pinnato a 4.0.1.** passlib 1.7.4 non sa leggere la
  versione di bcrypt ≥ 4.1 e solleva `AttributeError`: ogni login si
  rompe. Non alzare il vincolo senza aver aggiornato passlib.
- **`load_external_module` registra in `sys.modules` prima di eseguire
  il modulo.** Senza, ogni modulo che usi `@dataclass` insieme a
  `from __future__ import annotations` fallisce con un errore
  incomprensibile.
- **Il caricatore compila la sorgente invece di usare `exec_module()`.**
  Il bytecode cache di Python valida su *(mtime in secondi interi,
  dimensione)*: un file modificato nello stesso secondo e della stessa
  lunghezza — cambiare una cifra, invertire un booleano — verrebbe
  eseguito nella versione vecchia, senza un solo errore.
- **`RobotFileParser` senza `parse()` nega ogni URL.** Va chiamato
  `parse([])` anche quando robots.txt manca. E `crawl_delay()` per un
  agente specifico **non eredita** da `*`.
- **`soup.title.string` è `None` su `<title></title>`**, non `""`. Usare
  `get_text(strip=True)`.
- **`sentence-transformers` si importa pigramente.** L'import trascina
  torch e costa ~3 secondi: non riportarlo a livello di modulo.
- **Il `context` si costruisce una volta per audit.** `/audit/full`
  scansionava il sito otto volte.

## Sicurezza

- `MARS_SECRET_KEY` firma i JWT. Senza, il server genera una chiave
  effimera e lo dichiara: i token scadono a ogni riavvio.
- **Mai interpolare un URL in una stringa di shell.** Gli URL arrivano
  dall'utente, anche dal corpo di una richiesta API: lista di argomenti
  e `shell=False`.
- Il crawler rispetta robots.txt. L'unico modo per ignorarlo è la
  dichiarazione di proprietà del dominio (`--i-own-this-domain`,
  `i_own_this_domain`), che viene registrata nel referto.
