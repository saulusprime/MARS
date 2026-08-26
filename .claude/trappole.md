## Trappole già pagate

Costano ore se le si reincontra senza saperlo.

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
- **Un IPv6 letterale non si taglia sui due punti.** `[2001:db8::1]`
  ne è pieno: `split(":")[0]` dà `[2001`, e due indirizzi diversi
  diventano lo stesso host — il filtro same-host salta senza un
  errore. `parts.hostname` toglie invece le quadre, e l'URL ricomposto
  non è più un indirizzo valido. Vedi R24.
- **Normalizzare un URL può sollevare `ValueError`**, e non solo dentro
  `normalize_url`: su un IPv6 malformato solleva **`urljoin` stesso**,
  prima. Gli URL vengono dal sito analizzato, quindi sono dato ostile:
  usare `safe_normalize_url()`, che restituisce `None`, e dichiarare lo
  scarto in `skipped`. Vedi R15.
- **Corpus e query si tokenizzano con la stessa funzione.**
  `tokenize()` sta in `mars_core` proprio per questo: se i due lati
  divergono, la query smette di trovare ciò che l'indice contiene, e
  non c'è alcun errore — solo punteggi sbagliati. Con
  `.lower().split()` bastava un `?` a escludere una parola. Vedi R18.
- **Un redirect è un URL nuovo, e va ricontrollato prima di seguirlo.**
  `requests` li segue da solo e l'arrivo non viene più esaminato: basta
  un `302` perché il sito faccia scaricare al crawler un percorso
  `Disallow` o il contenuto di un altro host. Le pagine passano da
  `_scarica_pagina()`, che controlla ogni salto **prima** di farlo;
  robots.txt e sitemap li seguono ancora da sé (RFC 9309). Vedi R17.
- **`resp.text` decodifica in ISO-8859-1 ogni `text/*` senza charset.**
  È il default legacy di RFC 2616 che `requests` applica ancora: su un
  sito UTF-8 restituisce mojibake, e il corpus si corrompe in silenzio.
  Usare `decode_html()` per le pagine e `resp.content` per il resto.
  Vedi R16.
- **Vietare la rete non basta a fermare un browser.** Playwright non
  passa da `requests`: prima che `conftest.py` rendesse
  `playwright.sync_api` non importabile, la sola parte WCAG della suite
  lanciava **15 volte** chrome-headless-shell, mentre fixture e README
  dichiaravano il contrario. Si neutralizza la **libreria**, non
  `mars_wcag`, così non dipende da quale oggetto-modulo sia vivo.
  Vedi R20.
- **`node_modules` non è nell'ambiente di test, ma i moduli lo leggono.**
  `mars_wcag` prende da `node_modules/axe-core/locales/it.json` i testi di
  correzione delle regole axe. Un file che c'è su questa macchina e non su
  un clone appena fatto rende la suite **dipendente dalla macchina**:
  misurato, cinque test verdi qui e rossi là. Lo si fissa in `conftest.py`
  (`locale_axe_fisso`), come `force_proxy` fa con sentence-transformers.
  E la fixture va **presidiata da un test**, perché dove il file c'è la
  sua assenza è invisibile.
- **La fixture `niente_rete` copre `requests.get`, non `Session.get`.**
  Il `Crawler` usa una `Session`: per esercitarlo nei test si monta un
  `requests.adapters.BaseAdapter` finto sulla sua `session`
  (`tests/test_core.py`), non si conta sulla fixture. Quell'adattatore
  deve restare **fedele** a `HTTPAdapter.build_response`: quando
  fissava `resp.encoding = "utf-8"` tre mutazioni di R16 su cinque
  passavano inosservate, e finché non impostava `resp.request` il
  difetto R17 non si manifestava affatto nei test.
- **`sentence-transformers` si importa pigramente.** L'import trascina
  torch e costa ~3 secondi: non riportarlo a livello di modulo.

Tre trappole sono uscite di qui perché **non possono più mordere in
silenzio**: qualcosa le presidia nel punto in cui si sbaglierebbe.
Il pin di `bcrypt` a 4.0.1 porta la sua ragione scritta accanto a sé in
`requirements.txt`, dove guarda chi lo alza (R11); `soup.title.string`
che è `None` su `<title></title>` è R6, e il crawler usa
`get_text(strip=True)` con i test che lo coprono; «il `context` si
costruisce una volta per audit» è R5, presidiato da un test che conta
le scansioni. Il criterio per restare qui è questo: una trappola vale
una riga di CLAUDE.md finché può ancora mordere **codice non ancora
scritto**.
