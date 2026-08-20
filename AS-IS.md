# MARS Beacon — AS-IS

> Registro del lavoro **completato e verificato**. Le voci escono da
> [TO-DO.md](TO-DO.md) e arrivano qui solo dopo che la correzione è stata
> eseguita e provata: ogni voce riporta il difetto, la soluzione adottata e
> le verifiche fatte, così che nessuno debba rifare la stessa indagine.
>
> Gli identificativi (R1, C3, …) restano quelli del TO-DO.

## Indice

| ID | Voce | Data |
|---|---|---|
| R1 | Login dell'API completamente rotto | 2026-08-19 |
| R2 | `/users/me` restituiva l'hash della password | 2026-08-19 |
| R3 | Command injection remota in `mars_seo.py` | 2026-08-19 |
| R4 | Punteggi inventati in `mars_wapt.py` e `mars_seo.py` | 2026-08-19 |
| R5 | `/audit/full` ricrawlava il sito 8 volte | 2026-08-19 |
| R6 | Crash su `<title>` vuoto e tre casi limite vicini | 2026-08-19 |
| R7 | Il crawler non era un buon cittadino della rete | 2026-08-19 |
| R8 | Il proxy char-TFIDF era quadratico | 2026-08-19 |
| R9 | Euristica "answer-shaped" imprecisa e monolingue | 2026-08-19 |
| R10 | I "chunk" non erano chunk; l'RRF fondeva granularità diverse | 2026-08-19 |
| R11 | Igiene del codice (11 voci, 2 commit) | 2026-08-19 |
| R12 | Incoerenze nel README; documentata l'API REST (con C11) | 2026-08-19 |
| R13 | Allineamento allo stile di riferimento (2 commit) | 2026-08-19 |
| R14 | Il campo `disabled` non era mai applicato | 2026-08-19 |
| C13 | File di progetto: git, CLAUDE.md, CONTRIBUTING, CoC | 2026-08-19 |
| C1+C7 | Profili di citabilità IA; riuso dei risultati fra moduli | 2026-08-19 |
| C2 | Giudizio LLM sulla citabilità (`mars_llm_judge.py`) | 2026-08-19 |
| — | Verifica sistematica dei parametri API; `max_pages` corretto | 2026-08-20 |
| — | Credenziali nella richiesta API; esempio completo | 2026-08-20 |
| C13 (residue) | Titolarità del copyright e recapito del codice di condotta | 2026-08-20 |
| C9 (residue) | Verificato contro ZAP 2.17 reale; active scan autorizzato | 2026-08-20 |
| C9 | WAPT via ZAP: client ufficiale, orchestrazione eseguita | 2026-08-20 |
| C8 | WCAG reale via axe-core su Chromium | 2026-08-20 |
| C6 | Crawling interno quando manca la sitemap | 2026-08-20 |
| C5 | Query personalizzate e consenso RRF aggregato | 2026-08-20 |
| C4 | Referto JSON e HTML; l'API riusa la struttura canonica | 2026-08-20 |
| C3 (residue) | Modello OpenAI, `include` delle fonti, caricatore query | 2026-08-20 |
| C3 | Monitoraggio delle citazioni IA (`mars_citations.py`) | 2026-08-19 |
| — | Manutenzione: caricatore di moduli e import pigro | 2026-08-19 |
| — | Decisione: stile di riferimento del progetto | 2026-08-19 |

---

### R1 — ✅ RISOLTO (2026-08-19): il login dell'API era completamente rotto
`verify_password` è **definita due volte** in `mars_api.py`:
[riga 44](mars_api.py#L44) (confronto SHA256 timing-safe) e
[riga 101](mars_api.py#L101) (`pwd_context.verify`, bcrypt). La seconda
sovrascrive la prima. Ma `FAKE_USERS_DB` popola `hashed_password` con
`hash_password("mars2026")` ([riga 54](mars_api.py#L54)), cioè uno **SHA256 esadecimale**,
che passlib non sa interpretare.

Verificato in esecuzione:
```
>>> authenticate_user(FAKE_USERS_DB, 'admin', 'mars2026')
UnknownHashError: hash could not be identified
```

`POST /token` risponde **500** con le credenziali documentate nel docstring.
Di conseguenza **tutti e 8 gli endpoint protetti sono irraggiungibili**:
l'intera superficie API è inutilizzabile. `flake8 --select=F` lo segnala come
`F811`.

**Risoluzione applicata:** tenuta la versione passlib/bcrypt, con la coppia
`get_password_hash` / `verify_password` spostata sopra `FAKE_USERS_DB` (che la
invoca all'import) e le definizioni SHA256 e duplicate commentate.
`hashed_password` è ora un hash bcrypt `$2b$12$`.

Verificato: `flake8 --select=F` pulito (F811 sparito); `POST /token` → 200 con
JWT valido a 3 segmenti e claim `exp`; credenziali errate → 401; tutti e 8 gli
endpoint protetti raggiungibili col token e 401 senza.

- [x] Eliminare una delle due implementazioni.
- [ ] Aggiungere il test di **C12** che copre questo percorso — finora la
      verifica è stata manuale e non è registrata da nessuna parte.
- [x] Ripulire il codice commentato in `mars_api.py` (righe 8-9, 40-46, 62,
      101-105) quando il progetto sarà sotto git (**C13**): con lo storico
      versionato non serve più tenerlo a vista.

### R2 — ✅ RISOLTO (2026-08-19): `/users/me` restituiva l'hash della password
`User` includeva `hashed_password: str` ed era il `response_model` di
`GET /users/me`: l'hash bcrypt finiva nel corpo della risposta HTTP e nello
schema OpenAPI pubblicato su `/docs`.

Il codice mostrava l'intenzione originale — `# return UserInDB(**user_dict)` —
ma `UserInDB` non era mai stato scritto.

**Risoluzione applicata:** `User` è ora il modello pubblico (senza hash) e
`UserInDB(User)` quello interno che aggiunge `hashed_password`. `get_user()`
restituisce `UserInDB | None`; `authenticate_user()` restituisce `None` invece
di `False` in caso di fallimento.

`get_current_user()` proietta esplicitamente su `User` invece di restituire
l'oggetto interno: è **difesa in profondità**, perché così anche un endpoint
che dimenticasse `response_model` non potrebbe far uscire le credenziali —
l'oggetto non le contiene proprio. Affidarsi al solo filtro di `response_model`
avrebbe funzionato, ma sarebbe stata una protezione a un livello solo.

Verificato: `/users/me` restituisce 4 campi e nessun `hashed_password` (né nel
JSON né nel testo grezzo); lo schema `User` in `/openapi.json` non lo espone
più; login, password errata e accesso senza token invariati; `get_user`
interno conserva l'hash.

- [x] Separare `User` (pubblico) da `UserInDB` (interno).

### R3 — ✅ RISOLTO (2026-08-19): command injection remota in `mars_seo.py`
`mars_seo.py` interpolava l'URL in una stringa di shell:

```python
cmd = f"lighthouse {context['url']} --output=json --quiet --chrome-flags='--headless'"
subprocess.run(cmd, shell=True, ...)
```

L'URL arriva dall'utente: da riga di comando, e — da quando R1 ha reso l'API
raggiungibile — dal **corpo della richiesta** di `POST /audit/seo`.

**Sfruttabilità dimostrata** (comando innocuo, su codice nostro):

```
url = "https://esempio.it/; touch <file> #"   ->  file creato
```

Nota sull'API: `pydantic.HttpUrl` percent-codifica gli spazi (`%20`), il che
smorza i payload più banali. **Non è una difesa**: è un effetto collaterale
della normalizzazione dell'URL, `;` e backtick restano letterali, e un comando
senza spazi passa. Non va considerata una mitigazione.

**Risoluzione applicata:** argomenti passati come **lista** con `shell=False`,
quindi l'URL è un singolo argomento e la shell non lo interpreta mai.
Aggiunti `shutil.which("lighthouse")` per la diagnosi esplicita (come già
promesso dal README: *"cerca il comando lighthouse nel PATH"*) e un
`timeout` di 120 s, perché Lighthouse può bloccarsi a tempo indeterminato.

Attenzione a un dettaglio nella conversione: le virgolette in
`--chrome-flags='--headless'` erano **sintassi di shell**. In una lista di
argomenti vanno tolte (`--chrome-flags=--headless`), altrimenti Lighthouse
riceve gli apici come parte del valore.

L'`except Exception` generico è stato sostituito da eccezioni specifiche
(`TimeoutExpired`, `CalledProcessError`, `JSONDecodeError`, `KeyError`):
prima mascherava anche gli errori di programmazione.

Verificato: il payload di iniezione non esegue più nulla; con Lighthouse
assente si ottiene il fallback; con Lighthouse reale (13.4.1 + Chrome)
`https://example.com` restituisce 80/100.

- [x] Passare una lista di argomenti e `shell=False`.
- [x] Aggiungere un `timeout`.

**Contestualmente è stata chiusa la parte SEO di R4** (punteggi disonesti):
il fallback non restituisce più `score: 0` — che è il peggior giudizio
possibile e inquinerebbe qualunque aggregato — ma `score: None` con
`status: "unavailable"`. Questo ha richiesto di adeguare `print_report()`,
che andava in `TypeError` formattando `None` con `:>3.0f`: ora stampa
`non misurato`. La parte WAPT di R4 resta aperta.

### R4 — ✅ RISOLTO (2026-08-19): punteggi inventati in `mars_wapt.py` e `mars_seo.py`
`mars_wapt.py` restituiva `95` se `zap-cli quick-scan` usciva con 0 e `60`
altrimenti: due numeri che non corrispondevano ad alcuna vulnerabilità.
`mars_seo.py` restituiva `score: 0` quando Lighthouse mancava — il peggior
giudizio possibile al posto del "fallback" promesso dal README.

**L'exit code era letto al contrario.** `zap-cli quick-scan` documenta:
*"If any alerts are found for the given alert level, this command will exit
with a status code of 1"*. Quindi il ramo che assegnava 60 con la nota *"ZAP
ha rilevato potenziali vulnerabilità"* scattava sui **risultati**, non su un
errore — e il ramo da 95 scattava quando ZAP **non trovava nulla**, cioè
proprio quando il sito era pulito. Il difetto non era solo "numeri finti":
era una lettura invertita dello strumento.

**Due errori nel TO-DO stesso, corretti leggendo la CLI installata (zapcli
0.10.0):**

- `zap-cli report` produce solo **xml/html/md**, non JSON. Il comando giusto
  è `zap-cli alerts -f json`.
- `quick-scan --self-contained` **spegne il daemon a fine scansione**, quindi
  dopo non si possono più leggere gli alert. Serve un
  `start` → `quick-scan` → `alerts` → `shutdown` esplicito, con lo shutdown
  in `finally` per non lasciare processi orfani.

**Risoluzione applicata.** Logica separata dall'I/O, secondo il principio 8:

- `score_from_alerts(alerts)` — **funzione pura**: 100 meno le penalità per
  livello di rischio (`High` 25, `Medium` 10, `Low` 3, `Informational` 0),
  con i nomi degli alert reali in `issues` e il conteggio per rischio in
  `alerts_by_risk`. I pesi sono costanti dichiarate in testa al file, perché
  sono una scelta editoriale e non una misura (principio 6).
- `run_zap(url, zap_cli)` — la sola parte con I/O, isolata; restituisce
  `None` invece di sollevare.
- `audit_headers(url)` — ripiego, ora con `status: "surface"` per dichiarare
  che 100/100 sui tre header **non** è un sito scansionato e trovato pulito;
  e `score: None` + `status: "unavailable"` se il sito è irraggiungibile,
  invece del vecchio `score = 0`.

Chiusi contestualmente due difetti di **R11**: `shutil.which("zap-cli")` al
posto di uno `subprocess.run(["zap-cli", "--help"])` speso solo per sapere se
il comando esiste, e la cattura di `subprocess.SubprocessError` (che copre
`TimeoutExpired`) oltre a `OSError` — prima un timeout propagava e
interrompeva l'audit.

**Verificato.** `score_from_alerts` con payload sintetici: sito pulito 100;
1 High 75; 2 Medium 80; 1 High + 1 Medium + 3 Low 56; `"High (Medium)"`
(rischio con confidenza fra parentesi) 75; 10 alert informativi 100; alert
con campi mancanti nessun crash. Ripiego header su siti reali:
`example.com` 60, `github.com` 100. Percorso completo con `zap-cli` nel PATH
ma daemon ZAP assente: ripiego pulito, nessuna eccezione. `POST /audit/wapt`
risponde 200 con gli header. `flake8` pulito.

**Limite dichiarato:** il daemon ZAP (Java) non è installato su questa
macchina, quindi `run_zap()` è scritto sull'interfaccia documentata della CLI
ma **non è mai stato eseguito fino in fondo**. La logica di punteggio sì, ed
è la parte che conteneva il difetto. Il primo ambiente con ZAP installato
deve verificare il percorso completo.

- [x] Derivare lo score dagli alert reali, pesati per rischio.
- [x] Popolare `issues` con gli alert veri.
- [x] `score: None` + `status: "unavailable"` quando lo strumento non c'è.
- [ ] Escludere i moduli non misurati dal calcolo del composito (**C1**),
      quando C1 esisterà.

### R5 — ✅ RISOLTO (2026-08-19): `/audit/full` ricrawlava il sito 8 volte
`run_single_audit(module_name, req)` chiamava `build_context()` — e quindi
`Crawler.crawl()` — **a ogni modulo**. Con 7 moduli erano 7 scansioni complete;
poi una riga recuperava `urls` con un'ottava, accompagnata dal commento onesto
`# Ricalcolo veloce, in prod cacheare`.

Misurato prima della correzione, con un crawler strumentato: **8 crawl per una
sola richiesta**. Su `max_pages=25` significa 200 richieste HTTP invece di 25 —
e, cosa peggiore, i moduli potevano osservare **stati diversi del sito**,
rendendo i loro punteggi non confrontabili fra loro.

**Risoluzione applicata.** `build_context()` è stato spostato in
`mars_core.py`, dove diventa l'unica fonte di verità: prima CLI e API
costruivano ciascuna il proprio dizionario, con lo stesso contenuto scritto
due volte. La funzione restituisce `None` se il sito è irraggiungibile —
tradurre l'assenza in un errore HTTP spetta al chiamante, non al modulo core,
che non deve conoscere FastAPI.

`run_single_audit(module_name, context)` ora riceve il **contesto già
costruito** invece della richiesta: è ciò che permette a `/audit/full` di
scansionare una volta e riusare il risultato per tutti i moduli. Gli endpoint
singoli chiamano `build_context(req)` una volta ciascuno.

Nella CLI, `run_audit()` ha perso il parametro `force_proxy`: era ricalcolato
in due punti da `embeddings == "none"`, ora lo deriva `build_context()`.

**Risolto di conseguenza un difetto trovato durante i test di R1.** Il
`try/except Exception` attorno a ogni modulo inghiottiva anche l'`HTTPException`
sollevata da `build_context`: con un sito irraggiungibile `/audit/full`
rispondeva **200** con `{"error": "Modulo fallito"}` sette volte, mentre i
sette endpoint singoli rispondevano correttamente 404. Ora il contesto si
costruisce **fuori** dal ciclo e il 404 propaga. Il gestore per-modulo, che
resta necessario perché un modulo mancante non deve far fallire l'intero
referto, registra ora l'errore reale (`tipo: messaggio`) invece della stringa
generica.

**Verificato.** Con crawler strumentato: `/audit/full` **1 crawl** (era 8), i
quattro endpoint singoli provati 1 ciascuno, `rrf_analysis` presente nel
referto. Sito irraggiungibile: `/audit/tech` e `/audit/full` entrambi **404**
con lo stesso messaggio. CLI end-to-end su `example.com`: tutti e 7 i moduli
eseguiti, Lighthouse reale 80/100, header 60/100, RRF con consenso Top-3 1/3.
R1 e R2 non regrediti, `flake8` pulito.

- [x] Costruire il `context` una volta sola in `/audit/full`.
- [x] Rifattorizzare `run_single_audit` per ricevere il contesto.
- [x] Eliminare la duplicazione CLI/API della costruzione del contesto.

### R6 — ✅ RISOLTO (2026-08-19): crash su `<title>` vuoto, e tre casi limite vicini
`title = soup.title.string if soup.title else ""`: su `<title></title>` il tag
esiste ma `.string` è **`None`**, non `""`. Quel `None` finiva in
`pages[url]["title"]` e poi dentro `" ".join(parts)` in `mars_lexical.py`:

```
TypeError: sequence item 0: expected str instance, NoneType found
```

Un solo `<title></title>` in tutto il sito faceva cadere l'intero modulo
lessicale, e con esso la simulazione RRF — il cuore del progetto.

**Risoluzione applicata**, su quattro punti:

1. **`mars_core.Crawler`** usa `soup.title.get_text(strip=True)`, che
   restituisce `""` dove `.string` dava `None`. Verificato su `<title></title>`
   → `''`, `<title>  Spazi  </title>` → `'Spazi'`, titolo assente → `''`.
   Su `<title><b>x</b></title>` restituisce `'<b>x</b>'`: **corretto**, perché
   `<title>` è un elemento a testo grezzo e un browser mostrerebbe proprio
   quella stringa.
2. **`mars_lexical`** si difende comunque a valle: i moduli non devono fidarsi
   ciecamente del `context`. Verificato con `title` **e** `headings` a `None`.
3. **`LexicalRetriever.get_scores`** ha ora una guardia esplicita su
   `avgdl == 0`. Non era un crash reale: `avgdl` è 0 solo se *tutti* i
   documenti sono vuoti, e allora `idf` è vuoto e il ciclo interno non entra.
   Era una protezione **accidentale**, che un refactor avrebbe potuto togliere
   senza accorgersene.
4. **`mars_wcag`** andava in `IndexError` con `pages` vuoto
   (`list(...values())[0]`). Ora restituisce `score: None` +
   `status: "unavailable"`, come lo schema introdotto da R4. Stessa guardia
   aggiunta a `mars_schema`.

**`mars_schema`: vuoto ≠ malformato.** `json.loads(script.string)` con
`.string` a `None` sollevava `TypeError`, che l'`except Exception` catturava
riportandolo come *"JSON-LD malformato"* — **diagnosi sbagliata**: il blocco
non era malformato, era vuoto. Ora si usa `get_text(strip=True)`, si distingue
`JSON-LD vuoto` (−5) da `JSON-LD malformato` (−10), e si cattura
`json.JSONDecodeError` invece di `Exception`.

Verificato: script vuoto → 95 con "vuoto"; JSON malformato → 90 con
"malformato"; JSON-LD valido → 100 senza rilievi; script con testo estraneo al
JSON → 90 "malformato", ora per la ragione giusta.

**Una precisazione emersa durante il lavoro.** Avevo scritto, sia nel TO-DO che
in un primo commento nel codice, che `.string` è `None` anche quando il tag ha
più di un figlio. Con lxml **non vale** per `<title>` e `<script>`, che sono
elementi a testo grezzo: lì `.string` è `None` solo se l'elemento è vuoto.
I commenti sono stati corretti per non lasciare in giro una spiegazione falsa.

**Prova decisiva.** Audit completo su un sito con una pagina a `<title>` vuoto
e `title` forzato a `None` nel contesto: `mars_lexical` e `mars_semantic`
completano entrambi, l'RRF viene calcolato. Prima il modulo lessicale sarebbe
caduto e la fusione non sarebbe avvenuta affatto. CLI end-to-end su
`example.com` invariata.

- [x] `title` robusto nel crawler.
- [x] Difesa a valle in `mars_lexical.py`.
- [x] Guardia esplicita su `avgdl`.
- [x] `mars_wcag` e `mars_schema` con `pages` vuoto.
- [x] `mars_schema`: vuoto distinto da malformato, eccezione specifica.

### R7 — ✅ RISOLTO (2026-08-19): il crawler è ora un buon cittadino della rete
`Crawler` era un ciclo di `requests.get` su `/sitemap.xml`. Nove difetti,
tutti chiusi.

**robots.txt, con dichiarazione di proprietà.** Era il difetto più
imbarazzante: uno strumento che *valuta* robots.txt in `mars_tech.py` non lo
rispettava. Ora si usa `urllib.robotparser`, e l'unico modo per ignorarlo è
una **dichiarazione esplicita di proprietà del dominio e di responsabilità** —
`--i-own-this-domain` da CLI, `i_own_this_domain: bool` nel corpo della
richiesta API. Non è un interruttore di comodo: il nome del flag *è* la
dichiarazione, l'uso stampa un avviso, e il fatto viene registrato in
`context["robots_ignored"]` e dichiarato in fondo al referto. Via API la
dichiarazione è per di più attribuibile all'utente autenticato.

Due trappole di `robotparser`, verificate prima di scrivere il codice:

- un `RobotFileParser` su cui non si è mai chiamato `parse()` risponde
  **`False` a ogni `can_fetch()`**. Va quindi chiamato `parse([])` anche
  quando robots.txt manca, altrimenti il crawler non scaricherebbe nulla
  senza spiegare perché.
- `crawl_delay()` per un agente specifico **non eredita** da `*`. Si
  interrogano entrambi e si prende il valore più prudente fra quello del sito
  e il nostro.

**Gli altri otto.** User-Agent `MARSBeacon/2.0` invece di
`python-requests/2.x`; pausa fra le richieste (`--delay`, default 0,5 s, che
cede al `Crawl-delay` del sito se più alto); scarto delle risposte non-200,
che prima finivano nel corpus BM25 come pagine d'errore falsando i ranking;
controllo del `Content-Type`, che prima faceva parsare i PDF come HTML;
normalizzazione degli URL (`normalize_url()`: via il frammento, host
minuscolo, porta implicita) così che `/a` e `/a#top` non siano due pagine;
filtro same-host sugli URL della sitemap; sitemap lette dalle direttive
`Sitemap:` di robots.txt prima che da `/sitemap.xml`, con `<sitemapindex>`
annidati (fino a 3 livelli) e `.xml.gz` decompressi; timeout configurabile
(`--timeout`).

**Il referto dichiara cosa non ha guardato.** Il crawler raccoglie in
`skipped` il motivo di ogni URL scartato e `print_report()` lo mostra: dodici
pagine saltate cambiano il significato di ogni punteggio del referto, e
tacerlo sarebbe una bugia per omissione (principio 6).

**Verificato** con un server HTTP locale costruito apposta, che riproduce
robots.txt con `Disallow` e `Crawl-delay`, un `<sitemapindex>` che punta a una
sitemap normale e a una `.xml.gz`, un URL con frammento, un host esterno, un
404 e un PDF:

```
pagine scaricate : ok1, ok2
URL saltati      : vietato da robots.txt: /privato/segreto
                   host esterno: http://esterno.test/pagina
                   HTTP 404: /mancante
                   non HTML (application/pdf): /documento.pdf
User-Agent       : MARSBeacon/2.0
delay applicato  : 1.0s  (il nostro era 0,5; robots.txt chiedeva 1)
```

`/ok1` e `/ok1#top` producono una sola pagina; `ok2` arriva dalla sitemap
compressa, quindi indice annidato e gzip funzionano. Con
`owner_declaration=True` compare anche `/privato/segreto`. Referto CLI e
schema OpenAPI mostrano entrambi la dichiarazione. Regressione su
`example.com` invariata.

- [x] Rispettare robots.txt, con bypass solo su dichiarazione di proprietà.
- [x] User-Agent, rate limit, status code, Content-Type.
- [x] Normalizzazione/deduplicazione URL e filtro same-host.
- [x] Sitemap: direttive in robots.txt, indici annidati, `.xml.gz`.
- [x] Timeout configurabile.

### R8 — ✅ RISOLTO (2026-08-19): il proxy char-TFIDF era quadratico
Dentro `get_scores()`, per **ogni n-gramma della query** si ri-tokenizzava
**l'intero corpus**:

```python
idf = math.log((len(self.corpus)+1) /
               (sum(1 for d in self.corpus if ng in self._get_ngrams(d)) + 1)) + 1
```

Le document frequency erano già state calcolate in `_build_proxy()` e buttate
via. In più il prodotto scalare iterava l'intero vocabolario per ogni
documento, e la norma di ogni documento veniva ricalcolata a ogni query.

**Risoluzione applicata:** `self.df` conservato e letto da un `_idf()`
condiviso; vettori sparsi (`dict` per documento) al posto di
`[0.0] * len(vocab)`; `self.doc_norms` precalcolate; prodotto scalare che
itera **la query** (poche decine di n-grammi) cercando nel documento, invece
del vocabolario intero. Introdotta anche `DEFAULT_EMBEDDINGS`, che era
ripetuta come stringa letterale in tre file.

**Misurato**, corpus sintetico ad alta diversità lessicale (vocabolario ~17.000
trigrammi), 5 query:

| N documenti | query prima | query dopo | build prima | build dopo |
|---|---|---|---|---|
| 20 | 0,087 s | 0,0001 s | 0,194 s | 0,119 s |
| 40 | 0,190 s | 0,0002 s | 0,388 s | 0,241 s |
| 80 | 0,395 s | 0,0004 s | 0,791 s | 0,485 s |

Circa **1000× più veloce** per query, e la costruzione dell'indice scende a
~0,6×. Prima il tempo per query cresceva **linearmente col numero di
documenti** — il sintomo del difetto; ora è piatto.

**Verifica di equivalenza:** su tutte le combinazioni misurate lo scarto
massimo fra i punteggi prima e dopo è **0.00e+00** — non "entro tolleranza",
esattamente identici. Il refactor non cambia i risultati, solo il costo.

**Una previsione del TO-DO non si è avverata, e va detto.** Avevo scritto che
i vettori densi sprecavano memoria e che lo sparso avrebbe risolto. Misurato:
5,8 → 5,6 MB, 10,0 → 10,1 MB, 18,3 → 19,0 MB. **Nessun guadagno.** La ragione,
misurata anziché ipotizzata: ogni documento contiene in media 2.490 n-grammi
distinti su un vocabolario di 17.303, cioè una **densità del 14%**. Un `dict`
Python costa circa 100 byte per voce contro gli 8 byte per cella di una lista;
sotto l'8% circa di densità lo sparso vince, sopra pareggia. A 14% è un
pareggio. Il guadagno reale di R8 è la velocità, non la memoria.

- [x] Conservare `self.df` e leggerlo in `get_scores()`.
- [x] Vettori sparsi (utile per la struttura, **non** per la memoria: vedi
      sopra).
- [x] Norme dei documenti precalcolate.

### R9 — ✅ RISOLTO (2026-08-19): l'euristica "answer-shaped" era imprecisa e monolingue
```python
has_question = any(w in chunk.lower() for w in ["?", "come", "cosa", "perché", "chi", "dove", "quando"])
```
Test di **sottostringa**, non di parola. Misurato quali termini causano
davvero falsi positivi: `chi` (dentro *chiave, chiaro, chiesa, macchina,
architettura, archivio*), `cosa` (*qualcosa*), `dove` (*dovere, doveroso*).

**Due affermazioni del TO-DO erano sbagliate e sono state corrette:**
`"come"` **non** matcha *comodo* (che contiene "como", non "come"); e la
metrica **non** era "vicina a zero" sull'inglese, perché `"?"` è nell'elenco
e le domande inglesi con punto interrogativo passavano. Restava cieca solo
sulle domande senza punto interrogativo in lingue diverse dall'italiano.

**I confini di parola da soli non bastavano.** Misurato: eliminano tutti i
falsi positivi da sottostringa, ma non quelli grammaticali, perché in italiano
gli interrogativi sono anche congiunzioni — *"comodo **come** la neve"*,
*"il luogo **dove** abbiamo aperto"*, *"ricordiamo **quando** abbiamo
iniziato"*. Da qui la scelta di un segnale **posizionale**.

**Risoluzione applicata.** Quattro segnali indipendenti al posto di un elenco
di parole:

1. **punto interrogativo** nel testo;
2. **interrogativo a inizio frase** (dopo `. ! ? ; :` o a inizio testo), che è
   ciò che distingue una domanda da una congiunzione;
3. **titolo interrogativo** fra gli `headings` della pagina — segnale molto
   più forte di un termine nel corpo del testo;
4. **FAQPage JSON-LD** nella pagina (controllo volutamente grezzo: `mars_schema`
   legge già il JSON-LD, ma i moduli non si scambiano ancora i risultati —
   vedi **C7**).

Cinque lingue coperte (it, en, es, fr, de), scelte in base all'attributo
`lang`; senza lingua nota si provano tutte, perché un falso positivo è
preferibile a una metrica sistematicamente a zero.

`Crawler` conserva ora `lang` nel dizionario di pagina: letto una volta sola,
serve sia qui sia a `mars_wcag`, che è stato collegato e non riparsifica più
l'HTML per quel controllo. Effetto collaterale desiderabile: `lang=""` ora
conta come mancante, dove `has_attr('lang')` lo accettava — una stringa vuota
non è una dichiarazione di lingua valida (WCAG 3.1.1).

Il modulo restituisce anche `answer_shaped_signals` e `languages`, e
`/audit/semantic` li espone (continuando a escludere `scores`/`rank`, che sono
array lunghi quanto il corpus).

**Verificato** su 10 casi costruiti — 4 falsi positivi noti e 6 vere domande in
5 lingue: la vecchia euristica sbagliava 7 volte, la nuova **10/10**. Su un
sito sintetico con vere FAQ: 67% di chunk answer-shaped, con i quattro segnali
distinti nel referto; il chunk pieno di *chiavi/archivio/comodo come* non
produce alcun segnale.

- [x] Confini di parola — e oltre: posizione a inizio frase.
- [x] Multilingue (it, en, es, fr, de) guidato da `lang`.
- [x] Segnali strutturali: titoli interrogativi e FAQPage JSON-LD.

### R10 — ✅ RISOLTO (2026-08-19): i "chunk" non erano chunk
```python
"chunks": [p['text'][:500] for p in pages.values()]
```
Un chunk erano i **primi 500 caratteri** di una pagina — tipicamente il menu di
navigazione. Tutto il resto era invisibile all'audit semantico, mentre il
README prometteva *"chunk autoconsistenti"*.

Il danno peggiore era però a valle: `mars_lexical` indicizzava le **pagine**
(primi 1000 caratteri) e `mars_semantic` i **chunk**, ma i due ranghi venivano
fusi dall'RRF **come se si riferissero alle stesse unità**. Il "consenso Top-3"
non aveva il significato dichiarato nel README, che presenta l'RRF come il
cuore del progetto.

**Risoluzione applicata.**

`chunk_page()` in `mars_core.py` segmenta una pagina in passaggi
autoconsistenti: un chunk = un heading più il testo che lo segue fino
all'heading successivo, con `{"url", "heading", "text"}`. Le sezioni troppo
lunghe passano per `split_windows()`, che le divide in finestre da 1000
caratteri con 150 di sovrapposizione, tagliando su confine di parola — la
sovrapposizione serve a non spezzare a metà un'affermazione, perché un
passaggio citabile deve reggersi da solo.

Scelta implementativa che vale la pena spiegare: si cammina sui **nodi di
testo** (`descendants`) invece che sugli elementi di blocco, perché ogni nodo
viene visitato una volta sola. Con `find_all(["p", "li", ...])` il testo di un
`<p>` dentro un `<li>` verrebbe contato due volte, gonfiando il chunk.
`script`, `style`, `noscript` e `template` sono esclusi.

La segmentazione avviene **dentro il crawler**, dove il DOM è già in memoria:
farlo a valle avrebbe richiesto di riparsare l'HTML.

**Entrambi i retriever lavorano ora sulla stessa lista.** `mars_lexical`
indicizza i chunk (heading + testo: l'heading pesa, ed è spesso la forma in cui
la domanda è posta) e `mars_semantic` gli stessi chunk. Gli indici dei due
ranghi si riferiscono finalmente alle stesse unità, ed è la condizione perché
l'RRF significhi quello che il README dice.

Effetto collaterale che risolve una fragilità introdotta da **R9**: ogni chunk
porta con sé il proprio URL, quindi `mars_semantic` risale alla pagina per
chiave invece che per posizione nell'elenco — corrispondenza che reggeva solo
finché i chunk erano uno per pagina.

**Il referto identifica il passaggio, non un numero.** `describe_chunk()`
produce `URL § heading`, e sia la CLI sia `rrf_analysis` dell'API lo usano.
Prima si stampava `urls[rrf[0][0]]`, cioè l'URL di una pagina indicizzata con
l'indice di un chunk.

**Prova decisiva.** Pagina di 1051 caratteri con la risposta utile che inizia
al carattere **841**:

```
PRIMA (primi 500 caratteri) : 'preventivo' presente? False
DOPO  (segmentato)          : [0] 'Chi siamo'                       759 car.  False
                              [1] 'Come si richiede un preventivo?' 198 car.  True
query "come richiedere un preventivo"
  rango lessicale : [1, 0]      rango vettoriale: [1, 0]      vincitore RRF: chunk 1
```

Contenuto prima invisibile, ora trovato da entrambi i recuperatori, che
concordano perché finalmente ordinano le stesse cose.

Su sito di prova con due pagine strutturate: 6 chunk, consenso Top-3 2/3,
top chunk `.../ok1 § Quando conviene adottarla`. Regressione su `example.com`
e su tutti gli endpoint invariata.

- [x] Chunker in `mars_core.py` con `{"url", "heading", "text"}`.
- [x] Entrambi i retriever sulla stessa lista di chunk.
- [x] Referto che mappa l'indice sul suo URL e heading.

### R11 — ✅ RISOLTO (2026-08-19): igiene del codice
Undici voci, chiuse in **due commit separati** — sostanza e formattazione —
perché mescolarle rende la revisione impossibile (regola fissata in **R13**).

**`pip install -r requirements.txt` falliva.** `bcrypt=4.0.1` non è una
specifica PEP 508 valida: serve `==`. Il file è ora diviso in tre —
`requirements.txt` (core: CLI e API), `requirements-optional.txt`,
`requirements-dev.txt` — con le dipendenze che il codice importa davvero e non
erano dichiarate (`fastapi`, `uvicorn`, `pydantic`, `python-jose`, `passlib`,
`python-multipart`) e senza `tomli`, `jsonschema`, `PyYAML`, `idna`, `click`,
che nessun file importa. Il pin di bcrypt porta ora scritta la ragione:
passlib 1.7.4 non sa leggere la versione di bcrypt ≥ 4.1 e solleva
`AttributeError` — è ciò che ha reso possibile la correzione di **R1**, e
alzarlo distrattamente la romperebbe.

**`SECRET_KEY` non è più nel sorgente.** Si legge da `MARS_SECRET_KEY`; in sua
assenza se ne genera una effimera con un avviso esplicito. I token scadono a
ogni riavvio, il che rende il ripiego inutilizzabile in produzione: è
esattamente il punto, e il messaggio lo dice.

**`datetime.utcnow()`**, deprecata da Python 3.12 su un progetto che gira su
**3.14**, sostituita con `datetime.now(timezone.utc)`.

**Il difetto della directory di lavoro.** `load_external_module()` risolveva
`f"{module_name}.py"` rispetto alla CWD: lanciato da un'altra cartella il
programma non trovava nessun modulo e stampava serenamente `[ ] ... ignorato`
per tutte e sette le aree, producendo un referto vuoto **senza un solo
errore** — il tipo di guasto peggiore, perché sembra un risultato. Ora il
percorso si risolve da `__file__`. Verificato lanciando l'audit da `/tmp`:
tutti e 7 i moduli caricati.

**Duplicazione eliminata.** `MODULES_REGISTRY` e `load_external_module()` erano
copiati verbatim in `mars_audit.py` e `mars_api.py` — la stessa duplicazione
che aveva costretto a correggere il difetto `sys.modules` in due file invece
che in uno. Ora stanno in `mars_core.py`, insieme a `build_context()` che ci
era arrivato con **R5**.

**Un parse invece di tre.** Il crawler estrae `json_ld` e `images` mentre ha il
DOM in memoria; `mars_schema` e `mars_wcag` non riparsano più l'HTML. Si
estraggono **dati grezzi, non giudizi**: decidere cosa sia un difetto resta
compito dei moduli, e il layering regge.

**`openapi.json` rinominato** in `examples/audit_request.json`: non era una
specifica OpenAPI ma un payload di esempio con dentro un URL reale. La spec
vera la genera FastAPI su `/openapi.json`.

**Stile:** aggiunto `setup.cfg` (`max-line-length = 100`), così `flake8` gira
senza flag. Da **49 avvisi a zero**, in un commit di sola formattazione.
Verificato che il comportamento non cambia: BM25 su corpus noto
`[0.444974, 0.0, 0.645499]`, audit end-to-end e login API identici. Nel
riformattare, il denominatore della formula BM25 è stato estratto in una
variabile `norm`, che la rende anche più leggibile.

- [x] `requirements.txt` valido, completo e diviso per ruolo.
- [x] `SECRET_KEY` da ambiente.
- [x] `datetime.now(timezone.utc)`.
- [x] Percorso dei moduli da `__file__`.
- [x] Registro moduli deduplicato in `mars_core`.
- [x] HTML parsato una volta sola.
- [x] `openapi.json` rinominato.
- [x] `setup.cfg` e stile a zero avvisi.

### R12 — ✅ RISOLTO (2026-08-19): incoerenze nel README
Delle voci originali ne restavano due (le altre erano già state sistemate
dall'autore, incluso *"valuta quattro aree"* seguito da un elenco di sette).

**Avvertenza sul virtualenv.** Il blocco di comandi suggerito per i
prerequisiti di `zap-cli` contiene
`pip uninstall -y urllib3 requests six`: eseguito sul Python di sistema può
rompere altri programmi e, su alcune distribuzioni, strumenti del sistema
operativo. Aggiunta un'avvertenza esplicita, con il controllo da fare prima
(`which python` deve puntare dentro il virtualenv).

**Documentazione dell'API REST** (chiude anche **C11**). `mars_api.py` è metà
del progetto e il README lo citava solo come elenco di pacchetti da
installare. Aggiunta una sezione con avvio, `MARS_SECRET_KEY`, flusso di
autenticazione, tabella dei dieci endpoint, campi di `AuditRequest` — inclusa
la dichiarazione `i_own_this_domain` — e codici di risposta.

L'elenco degli endpoint **non è stato scritto a memoria**: è stato estratto
dalla specifica OpenAPI che FastAPI genera, così non può divergere dal codice.

**Ogni comando documentato è stato eseguito**, non solo scritto. È così che è
emerso un problema reale: sulla macchina di sviluppo la porta 8000 è occupata
da un'altra applicazione dell'utente (`LymphaGest`). Uvicorn non riusciva ad
agganciarsi ed **usciva**, ma le richieste continuavano a ricevere risposta —
dall'altra applicazione. I 404 sembravano provenire da MARS. Rifatta la prova
su porta libera:

```
GET  /docs            -> 200      senza token          -> 401
GET  /                -> 307      url non valido       -> 422
POST /token           -> JWT a 3 segmenti, 124 caratteri
POST /audit/wcag      -> 200      sito irraggiungibile -> 404
```

Il README avverte ora di questo caso: un server che non si è agganciato lascia
rispondere qualunque altra cosa stia su quella porta.

**Installazione per ruolo.** Documentati i tre file di requirements introdotti
da **R11** e il pin di `bcrypt==4.0.1` con la sua ragione.

- [x] Avvertenza virtualenv sul blocco `zap-cli`.
- [x] Documentazione dell'API REST (chiude **C11**).

### R13 — ✅ RISOLTO (2026-08-19): allineamento allo stile di riferimento
L'allineamento era previsto graduale; su richiesta è stato completato in una
sola sessione, ma rispettandone la regola: **due commit separati**, uno di
sole annotazioni e uno di sostanza.

Buona parte del lavoro era già stata fatta *opportunisticamente*, come R13
prescriveva: i sette moduli d'area erano stati riscritti nel nuovo stile
mentre si correggevano R3, R4, R9, R10 e R11. Restavano scoperti
`mars_audit.py`, `mars_tech.py`, parte di `mars_api.py` e i due retriever di
`mars_core.py`.

**Annotazioni.** `from __future__ import annotations` ora in tutti e undici i
moduli; annotate le firme rimaste scoperte. Le docstring aggiunte spiegano il
*perché*, non il cosa: `reciprocal_rank_fusion` documenta che usa la
posizione e non il punteggio — che non è confrontabile fra recuperatori
diversi — e che le classifiche in ingresso devono riferirsi alle stesse unità.
`mars_tech`, `mars_schema` e `mars_wcag` **dichiarano quanto del proprio nome
non coprono ancora**, con il rimando alla voce di TO-DO che completerebbe
l'area: una docstring onesta vale più di una che promette l'area intera.

**Sostanza.** `__version__` vive in `mars_core` ed è l'unica fonte: alimenta
User-Agent, `--version` e la versione dell'API, che erano tre stringhe
indipendenti destinate a divergere. Aggiunto `--version` alla CLI.

**Codici di uscita.** Un audit su sito irraggiungibile usciva con **0**, cioè
"successo": nessuna pipeline poteva distinguerlo da un audit riuscito. Ora
`0` = referto prodotto, `2` = nessuna pagina indicizzata, allineati a
`mars_citations.py`; il valore `1` resta libero per una futura soglia
`--fail-under` (idea **I2**).

**Un punto di R13 è stato deliberatamente NON applicato.** Il principio 8
chiedeva `@dataclass` al posto dei dizionari anonimi. Applicato al `context`
e a ciò che contiene — pagine, chunk — avrebbe violato il **principio 3**:
quelle strutture attraversano il confine dei plugin, e imporre classi di
`mars_core` costringerebbe ogni modulo esterno a importarle per rispettare il
contratto `audit(context) -> dict`. I dataclass restano per le strutture
interne a un modulo (`ProviderAnswer` in `mars_citations` ne è l'esempio).
Il principio 8 nel TO-DO è stato riscritto per dirlo.

Verificato che nulla cambia: BM25 `[0.470004, 0.0, 0.578466]`, RRF
`[(0, 0.032266458), (2, 0.032266458), (1, 0.032258065)]`, proxy `[0.548, 0.0]`,
audit end-to-end e login API invariati. Il cambio di User-Agent da
`MARSBeacon/2.0` a `MARSBeacon/2.0.0` non altera il rispetto di robots.txt:
`robotparser` confronta la parte prima della barra. `flake8` a zero avvisi.

- [x] `mars_core.py` allineato.
- [x] `mars_audit.py` allineato.
- [x] `mars_api.py` allineato.
- [x] I sette moduli d'area (fatti lungo il percorso, come previsto).

### R14 — ✅ RISOLTO (2026-08-19): il campo `disabled` non era mai applicato
`User` dichiarava `disabled: bool | None` e `FAKE_USERS_DB` lo valorizzava, ma
**nessuna funzione lo leggeva**.

**La classificazione iniziale era sbagliata, e va detto.** L'avevo marcato
🔴 CRITICO. Verificando su domanda dell'autore: non esiste alcun endpoint che
crei o modifichi utenti, `FAKE_USERS_DB` contiene un solo utente hardcoded, e
per portare `disabled` a `True` bisogna **editare il sorgente** — chi può farlo
ha già vinto. La "dimostrazione" che avevo prodotto creava l'utente sospeso da
Python: uno scenario artificiale, non un attacco. Come difetto di sicurezza
sfruttabile, R14 non lo era.

**Il difetto reale era nel contratto OpenAPI.** Lo schema `User` pubblicato su
`/docs` espone `disabled` a chiunque integri l'API, e chi lo legge conclude
ragionevolmente che esista una sospensione degli account. Non esisteva. Dato
che l'applicazione è consumata **esclusivamente via OpenAPI**, lo schema è la
superficie del prodotto: la promessa non mantenuta viveva esattamente dove
vive l'applicazione.

**Risoluzione applicata** (scelta dell'autore fra applicare, rimuovere il campo
o documentarlo come riservato):

- `authenticate_user()` rifiuta gli utenti sospesi: niente token.
- `get_current_user()` **ricontrolla a ogni richiesta**. È la parte che conta:
  i JWT non si revocano e durano 30 minuti, quindi senza questo un account
  sospeso resterebbe operativo fino alla scadenza. È l'unico meccanismo di
  revoca che l'API possiede.
- Il campo porta ora una `description` che finisce nello schema OpenAPI, così
  la promessa è esplicita oltre che mantenuta.

Vale anche in prospettiva: il codice dichiara `# Fake DB Utenti (in produzione
usa un DB reale)`, e quando quel DB arriverà `disabled` sarà l'unico modo per
revocare un accesso. Due righe ora, invece di ricordarsene dopo.

**Verificato:** utente attivo 200; utente sospeso `/token` → 401; token emesso
**prima** della sospensione → 200 prima, **401 dopo**, sia su `/users/me` sia
su `/audit/tech`; admin non toccato; descrizione presente nello schema
pubblicato.

- [x] Rifiutare l'autenticazione degli utenti sospesi.
- [x] Ricontrollare in `get_current_user()` perché i token già emessi decadano.
- [ ] Test dedicato (**C12**): la verifica è stata manuale.

### C13 — ✅ RISOLTO (2026-08-19): file di progetto mancanti
Il repository non era sotto controllo di versione e mancavano i file che
rendono un progetto utilizzabile da qualcuno che non l'ha scritto.

**Git.** Repository inizializzato su `main`, con `.gitignore` scritto **prima**
dell'`init`: `.venv/` pesa 5,4 GB e `node_modules/` 162 MB, quindi l'ordine non
era un dettaglio. Il repository sta in 708 KB. Esclusi anche i referti
rigenerabili e lo storico JSONL delle citazioni, che è dato dell'utente e non
codice.

**LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md** aggiunti dall'autore. I
primo è l'Apache 2.0 autentico; gli altri due erano però **file vuoti**, e un
file vuoto è peggio di uno assente perché chi lo apre non trova nulla. Sono
stati scritti.

`CONTRIBUTING.md` codifica le regole emerse lavorando: `flake8` a zero,
riprodurre il difetto prima e dimostrarlo chiuso dopo, riformattazione in un
commit separato, una voce del TO-DO per commit, e lo spostamento in AS-IS
quando è chiusa. Più cosa non cambiare senza discuterne: sostituire gli
algoritmi scritti a mano, rendere obbligatoria una dipendenza opzionale,
trasformare il `context` in classi.

`CODE_OF_CONDUCT.md` adatta il Contributor Covenant 2.1 in italiano. Il
recapito per le segnalazioni è **deliberatamente lasciato in bianco**, con una
nota che lo dice: pubblicare un indirizzo in un file del repository è una
scelta del responsabile, non un dettaglio da dare per scontato.

**`CLAUDE.md`** documenta il contratto dei moduli — `audit(context) -> dict` —
con la tabella di ciò che arriva nel `context`, la struttura di pagine e
chunk, cosa restituire, e la distinzione fra `score: None` (non misurato) e
`score: 0` (giudizio). Poi i sette principi, le regole di lavoro, e una
sezione **"trappole già pagate"**: il pin di `bcrypt`, `sys.modules` nel
caricatore, `RobotFileParser` che nega tutto senza `parse()`,
`soup.title.string` a `None`, l'import pigro di sentence-transformers, il
`context` da costruire una volta sola. Sono le ore spese in questa sessione,
messe dove servono la prossima volta.

**Il contratto documentato è stato verificato contro il codice**, non scritto a
memoria: chiavi del `context`, chiavi di pagina e di chunk confrontate a
runtime. Zero divergenze in entrambe le direzioni — nulla di documentato che
non esista, nulla di esistente non documentato.

- [x] `.gitignore` e repository git.
- [x] `LICENSE` (dall'autore).
- [x] `CLAUDE.md` con il contratto dei moduli.
- [x] `CONTRIBUTING.md` e `CODE_OF_CONDUCT.md` scritti (erano vuoti).

### C1 + C7 — ✅ FATTI (2026-08-19): profili di citabilità IA e riuso dei risultati
Il README prometteva i profili di citabilità per assistente con indice
composito pesato per mercato. `market` veniva passato lungo tutta la catena ma
**non era letto da nessun modulo**: nessun profilo veniva calcolato.

**C7 era il prerequisito** ed era davvero una riga: `context["results"] =
results` **prima** del ciclo, stesso dict popolato mentre il ciclo avanza. Un
modulo di sintesi può così leggere i punteggi delle aree già eseguite senza
che il contratto `audit(context) -> dict` cambi di una virgola.

**Solo 5 aree su 7 producono un punteggio.** `mars_lexical` e `mars_semantic`
restituiscono classifiche, non voti. C1 ne deriva quindi due segnali:

- *Contenuto in forma di risposta* = `answer_shaped_ratio × 100`;
- *Recuperabilità ibrida* = consenso RRF fra i primi tre chunk dei due
  recuperatori. È la misura più vicina a "questo passaggio verrebbe davvero
  selezionato da una ricerca ibrida", ed è possibile solo perché **R10** ha
  reso i due ranghi commensurabili.

**Il modello è esplicito e discutibile, per scelta.** Pesi 0-3 per assistente ×
segnale, con la motivazione di ogni riga scritta accanto; il mercato agisce su
due piani — quanto conta ciascun assistente, e moltiplicatori sui segnali dove
esiste una ragione concreta. L'unico attivo è l'accessibilità per `eu`, per
l'European Accessibility Act: una ragione **normativa verificabile**, non una
stima.

Due scelte di onestà metodologica (principio 6):

- **Qwen e Kimi hanno pesi identici**, ed è dichiarato: non ci sono basi
  pubbliche per differenziarli, e inventare una differenza per far sembrare la
  tabella più informata sarebbe esattamente la falsa precisione che il
  principio vieta.
- **La scala è volutamente grossolana** (0-3). Una scala fine suggerirebbe una
  precisione che non abbiamo.

I segnali non misurati sono **esclusi** dalla media e i pesi si rinormalizzano:
un'area senza strumento non abbassa il profilo, lo rende solo meno informato —
ed è dichiarato nel referto quali segnali mancano. È il seguito naturale della
distinzione `score: None` vs `score: 0` introdotta da **R4**.

Il disclaimer è stampato **dentro il blocco**, subito sotto i numeri: chi legge
il punteggio deve leggere anche cosa non è.

**Verificato:** mercati `global`/`eu`/`us`/`cn` producono compositi diversi
(l'`eu` sale per il moltiplicatore accessibilità, il `cn` per lo spostamento
verso Qwen e Kimi); un mercato inesistente ricade su `global` dichiarandolo;
Lighthouse assente compare fra i "segnali non misurati" invece di contare zero;
`/audit/full` restituisce profili, composito e disclaimer.

- [x] `mars_citability.py` col contratto `audit(context)`.
- [x] Matrice pesi assistente × segnale e per mercato, dichiarativa.
- [x] `context["results"]` popolato incrementalmente (**C7**).
- [x] Blocco `Profili di citabilità` nel referto.
- [x] Natura euristica marcata in output.

### C2 — ✅ FATTO (2026-08-19): giudizio LLM sulla citabilità
Il README prometteva un giudizio LLM *"attivo di default in modalità auto
quando la chiave ANTHROPIC_API_KEY è presente"*. La libreria `anthropic` era
fra le dipendenze e installata, ma la stringa non compariva in nessun file.

**`mars_llm_judge.py`** sottopone al modello i passaggi più recuperabili
**secondo la fusione RRF** — non le prime pagine del sito. È la differenza che
rende il giudizio pertinente: si chiede al modello di valutare ciò che una
ricerca ibrida selezionerebbe davvero, ed è possibile solo perché **R10** ha
reso i due ranghi commensurabili e **C7** dà al modulo accesso ai risultati.

**Le API sono state usate secondo documentazione, non a memoria.** Modello
`claude-opus-5`; output strutturato con `output_config={"effort", "format"}` e
uno schema `json_schema`, così il parsing non dipende da come il modello
formatta la prosa; `thinking={"type": "adaptive"}`; fallback lato server
(`betas=["server-side-fallback-2026-07-01"]` con `fallbacks="default"`) perché
una richiesta declinata dai classificatori venga rieseguita sul modello di
ripiego invece di andare persa. Lo schema esatto di `output_config.format` è
stato letto dalla documentazione dell'SDK, non dedotto.

**È l'unico modulo che spende denaro**, e il controllo è esplicito: `--llm
auto` (predefinito) esegue solo con credenziale presente; `on` tenta comunque,
così da usare anche un profilo `ant auth login` che la variabile d'ambiente
non mostra; `off` non esegue mai. Via API il campo è `llm`, validato con
`pattern`. Prima di inviare, il modulo dichiara quanti passaggi e quanti token
partiranno — con la stima marcata come grossolana, un token ogni quattro
caratteri: serve a dare un ordine di grandezza, non a prevedere la fattura.
Tetto a 8 passaggi da 1200 caratteri e `max_tokens` a 4000.

**Due difetti trovati collaudando**, entrambi invisibili leggendo il codice:

1. Con `--llm on` e nessuna credenziale, `anthropic.Anthropic()` fa passare la
   costruzione e solleva **`TypeError` al momento della richiesta**. Non era
   catturato: l'intero audit sarebbe **crashato**.
2. Catturandolo genericamente, un problema di credenziali veniva riportato
   come *"giudizio non interpretabile"* — diagnosi sbagliata sul difetto
   sbagliato. Ora il `TypeError` viene distinto guardando il messaggio, e
   riporta *"Nessuna credenziale Anthropic utilizzabile"*.

**Limite dichiarato.** Su questa macchina non esiste alcuna credenziale
Anthropic, quindi **la chiamata reale non è mai stata eseguita**. È stato però
collaudato tutto il resto tramite `context["_anthropic_client"]`, un punto di
iniezione documentato nella docstring: selezione RRF dei passaggi, costruzione
del prompt, forma esatta della richiesta (modello, betas, fallback, thinking,
effort, schema JSON, system), parsing della risposta, mappatura dell'indice sul
passaggio, e i tre percorsi di `--llm`. Resta da verificare sul campo solo che
il servizio accetti la richiesta così composta.

- [x] `mars_llm_judge.py` attivo solo con credenziale, altrimenti no-op dichiarato.
- [x] `--llm {auto,on,off}` con default `auto`.
- [x] Top-N passaggi selezionati dall'RRF, non tutto il sito.
- [x] API consultate sulla documentazione corrente.
- [x] Costo prevedibile: tetto sui token e dichiarazione prima dell'invio.

### Verifica sistematica dei parametri API (2026-08-20)
Controllo completo che ogni parametro dell'API sia passabile da
`examples/audit_request.json` **e abbia effetto**, perché un campo accettato e
poi ignorato è peggio di uno mancante.

**Struttura: completa.** Tutti e 10 i campi di `AuditRequest` e tutti e 4 di
`Credentials` sono nell'esempio; nessun campo estraneo; tutti e 8 gli endpoint
di audit accettano lo stesso corpo.

**Comportamento: verificato uno per uno.** Con una spia sul `Crawler`,
`max_pages`, `delay`, `timeout` e `i_own_this_domain` arrivano con i valori
inviati; nel contesto arrivano `market`, `force_proxy`, `queries`, `llm` e le
quattro credenziali. Via HTTP l'effetto è osservabile nel referto: `market`
cambia l'indice composito (cn 68,7 / eu 71,1), `queries` produce una voce per
query, `llm=off` disattiva il modulo, `i_own_this_domain` accende
`robots_ignored`, e una chiave riconoscibile non compare in risposta.

**Parità CLI/API:** ogni flag della CLI ha il suo campo. `--format` e
`--output` restano solo CLI perché riguardano la resa del referto, non l'audit;
`credentials` resta solo API perché da riga di comando si usano le variabili
d'ambiente.

**Un difetto trovato dalla verifica: `max_pages` non limitava le pagine.**
`max_pages=2` restituiva **1 pagina**. `fetch_sitemap()` limitava gli URL
**candidati** a `max_pages`, ma i candidati vengono scartati a valle —
duplicati dopo la normalizzazione, host esterni, vietati da robots.txt, 404,
risorse non HTML. Sul sito di prova con `max_pages=2` la sitemap restituiva
`/ok1` e `/ok1#top`, che sono la stessa pagina: il budget se ne andava in URL
che non diventavano mai pagine.

Ora i candidati si raccolgono con un margine dichiarato
(`CANDIDATI_PER_PAGINA = 5`, minimo 50, tetto `MAX_CODA`) ed è il ciclo di
`crawl()` a fermarsi a `max_pages`, come dovrebbe. Verificato:
`max_pages=1` → 1 pagina, `max_pages=2` → 2 pagine.

Il difetto era invisibile finora perché tutte le prove precedenti usavano
`max_pages` generoso rispetto al sito di prova: chiedere **poco** era il caso
che nessuno aveva provato.

### Credenziali nella richiesta API (2026-08-20)
`examples/audit_request.json` era fermo a quattro campi su nove ed era stato
scritto prima di R7, C2, C5 e C6. Serviva inoltre poter passare le chiavi degli
strumenti opzionali dalla richiesta, perché un'unica istanza dell'API possa
servire chiamanti che portano le proprie.

**Il campo `credentials`** accetta `anthropic_api_key`, `hf_token`,
`zap_api_key` e `zap_proxy`. `hf_token` serve **solo** per i modelli di
embedding Hugging Face ad accesso limitato o privati: per quelli pubblici,
incluso il predefinito, è ininfluente, e da riga di comando basta la variabile
`HF_TOKEN` che `huggingface_hub` legge da sé. Viene passato a
`SentenceTransformer(token=...)` solo quando è presente, così il percorso
pubblico resta identico a prima. Sono `SecretStr`: pydantic li maschera in log, `repr` e messaggi
d'errore, così una chiave non finisce in un traceback per distrazione. Nello
schema OpenAPI risultano `format: password` e **`writeOnly: true`**, quindi
Swagger li maschera e li dichiara solo-input.

`get_secret_value()` viene chiamato in un punto solo, all'ingresso: i moduli
ricevono stringhe e non devono conoscere pydantic. `mars_llm_judge` e
`mars_wapt` preferiscono la credenziale della richiesta all'ambiente; senza,
tutto funziona come prima.

**Verificato che le chiavi non tornano indietro.** Inviata una chiave
riconoscibile a `/audit/full` e ai singoli endpoint: non compare in nessuna
risposta, e la parola `credentials` nemmeno. `build_report()` legge chiavi
nominate e non l'intero contesto, quindi il referto non può contenerle per
costruzione.

**Il file di esempio contiene segnaposto, e deve restare così**: è versionato
in git. Il primo campo del file è un `_commento` che lo dice a chi lo apre, e
il README ripete l'avvertenza insieme a quella sull'uso solo su HTTPS — nel
corpo di una richiesta le chiavi viaggiano fino al server.

Le chiavi di `mars_citations.py` restano solo su variabili d'ambiente: è uno
strumento da riga di comando, non esposto via API.

**Una deriva della documentazione, trovata verificando.** Il confronto fra il
contratto scritto in `CLAUDE.md` e le chiavi reali del `context` ha rivelato
che `discovery`, `llm` e `queries` — aggiunte da C6, C2 e C5 — non erano mai
state documentate. Allineate. È il secondo controllo automatico dello stesso
tipo, e il primo che trova qualcosa: vale la pena rifarlo ogni volta che il
contesto cambia.

### C13 (residue) — ✅ CHIUSE (2026-08-20): titolarità e recapito
Le due voci erano state lasciate aperte di proposito: pubblicare un nome e un
indirizzo in un repository è una decisione del titolare, non una formattazione,
e non l'ho presa io.

**Titolarità del copyright.** `LICENSE` conservava il segnaposto
`Copyright [yyyy] [name of copyright owner]` dell'appendice Apache, e nessun
sorgente portava una riga di copyright: dichiaravano solo la licenza. Senza un
titolare indicato una licenza è difficile da far valere. Compilata come
`Copyright 2026 Paolo Pierno`, nel LICENSE e negli header di tutti e **14** i
file sorgente.

**Recapito nel codice di condotta.** Il segnaposto è stato sostituito con
l'indirizzo indicato dall'autore, `p.pierno@lymphatech.it`. Un codice di
condotta senza un canale di segnalazione non è applicabile.

La terza voce — il recupero della cartella `versions/` — era già stata chiusa
dall'autore, che ha deciso di non recuperarla: git ne ha preso il posto.

Verificato: `flake8` a zero, tutti e 9 i moduli si caricano, CLI e API
invariate.

- [x] Titolarità del copyright nel LICENSE e nei sorgenti.
- [x] Recapito nel `CODE_OF_CONDUCT.md`.

### C9 (residue) — ✅ CHIUSE (2026-08-20): verificato contro ZAP 2.17 reale
L'autore ha installato ZAP. Le due voci che richiedevano il daemon sono chiuse,
e la verifica sul campo ha rovesciato una delle scelte fatte a tavolino.

**Il client ufficiale non funziona con ZAP 2.17.**
`python-owasp-zap-v2.4` 0.0.14 cabla l'indirizzo `http://zap/` e **rifiuta ogni
altro URL** — c'è un controllo esplicito nel suo codice, per non far trapelare
la chiave API. Ma ZAP 2.17 non serve più quell'alias attraverso il proxy.
Misurato: il proxy inoltra regolarmente `example.com` (200), mentre
`http://zap/` chiude la connessione; nessun alias alternativo (`zap.local`,
`localhost`, `127.0.0.1`) funziona. L'API diretta invece risponde.

Il finto daemon costruito in precedenza non poteva rivelarlo: rispondeva a
qualunque percorso, mentre quello vero è selettivo. **Un banco di prova troppo
accomodante conferma anche ciò che è sbagliato.**

**Sostituito con un client scritto a mano**, una trentina di righe su
`requests`, che era già una dipendenza. L'API di ZAP è un GET che restituisce
JSON: farlo a mano costa meno che dipendere da un wrapper fermo al 2018.
`zapcli` e il client ufficiale sono usciti da `requirements-optional.txt`, con
la ragione scritta accanto: per ZAP **non serve alcun pacchetto pip**.

**Un problema di sicurezza sollevato dal collaudo.** Per verificare ho dovuto
lanciare scansioni, e questo ha reso evidente che `ascan` **invia payload
d'attacco** — XSS, SQL injection, path traversal. `mars_wapt` lo lanciava
contro qualunque URL ricevesse: contro un sito che non si possiede è un
attacco, e a seconda della giurisdizione un reato.

L'active scan richiede ora la **stessa dichiarazione di proprietà** introdotta
da **R7** per ignorare robots.txt. Senza, gira solo lo spider e si raccolgono
gli alert **passivi** — header mancanti, informazioni divulgate — che sono utili
e innocui. Il referto dichiara quale delle due ha girato (`ZAP (attiva)` /
`ZAP (passiva)`). Per distinguere i due significati, `context` porta ora
`owner_declaration` accanto a `robots_ignored`.

**Verificato su ZAP 2.17.0 reale**, contro server locali di nostra proprietà:
sequenza `version` → `spider/action/scan` → `spider/view/status` →
`ascan/action/scan` → `ascan/view/status` → `core/view/alerts`; chiavi
`pluginId`, `alert`, `risk`, `url` tutte presenti.

**Il raggruppamento per regola confermato sul campo:** 27 alert grezzi da una
scansione reale → **4 regole distinte**, con *Missing Anti-clickjacking Header*
su 6 URL contata una volta. Senza raggruppamento quella sola regola sarebbe
costata 60 punti.

**Taratura dei pesi, due punti reali** (entrambi su server locali nostri):

| sito | score | regole |
|---|---|---|
| mal configurato | 58 | 2 Medium + 2 Low |
| ben configurato | 76 | 2 Medium (residui: CSP fallback, sito solo HTTP) |

La scala ordina correttamente e lascia spazio sotto per un rilievo *High*.
Due punti non sono una calibrazione su corpus, e resta scritto così.

**Un difetto del prodotto trovato mentre si tarava.** Il server di prova
blindato risultava privo di HSTS e CSP che invece impostava: `audit_headers`
usava `requests.head()` **senza controllare lo status code**, e leggeva gli
header di una risposta `501 Unsupported method`. Esistono server reali che
rifiutano HEAD: avrebbero ricevuto un *"mancano tutti gli header di
sicurezza"*, falso e dato con sicurezza. Ora si controlla lo status e si
ripiega su GET. Verificato: il server blindato passa da 60 a **100/100**.

Il daemon ZAP avviato per il collaudo è stato spento.

- [x] Verifica contro un daemon ZAP reale (2.17.0).
- [x] Pesi tarati su scansioni reali — due punti, dichiarati come tali.

### C9 — ✅ IN GRAN PARTE FATTO (2026-08-20): WAPT via ZAP, orchestrazione eseguita
Dopo **R4** il modulo derivava il punteggio dagli alert reali, ma il percorso
ZAP non era **mai stato eseguito**: il daemon Java non è installato, e non lo
è tuttora. Quattro delle sei voci non lo richiedevano.

**Migrato da `zapcli` al client ufficiale.** `zapcli` 0.10.0 è del 2018 e
costringeva a orchestrare la CLI e a interpretarne l'output;
`python-owasp-zap-v2.4`, già installato, parla direttamente l'API di ZAP e
restituisce dati strutturati.

**MARS non avvia più il daemon: si collega a uno già in esecuzione**
(`ZAP_PROXY`, `ZAP_API_KEY`). Questo risolve per costruzione la voce sui
*daemon orfani dopo un timeout*: non c'è più un processo Java da spegnere.
Il README documenta il comando Docker che lo mette in piedi.

**Un finto daemon ZAP per collaudare davvero.** Il client `ZAPv2` parla
*attraverso* ZAP come proxy HTTP, quindi un server locale può rispondere alle
sue chiamate API. È lo stesso schema del finto client Anthropic in C2, e ha
trovato lo stesso tipo di difetto — invisibile leggendo il codice.

**`core.version` è una `@property`, non un metodo.** Il codice scriveva
`client.core.version()`, che con un daemon reale avrebbe sollevato
`TypeError: 'str' object is not callable`. Senza daemon l'errore non appariva:
l'eccezione di connessione arrivava prima e mascherava il difetto. Verificato
che `scan`, `status` e `alerts` restano invece metodi.

**Sequenza eseguita e chiavi confermate.** `core/view/version` →
`spider/action/scan` → `spider/view/status` → `ascan/action/scan` →
`ascan/view/status` → `core/view/alerts`. Gli alert contengono davvero
`pluginId`, `alert`, `risk` e `url`, che è ciò che `score_from_alerts()`
attende, incluso il caso `"Medium (High)"` con la confidenza fra parentesi.

**Applicata la lezione di C8.** Gli alert si raggruppano per **regola**, non
per occorrenza: ZAP ne emette uno per ogni URL interessato, quindi un solo
difetto su venti pagine affondava il punteggio da solo. Verificato con il finto
daemon: 6 alert grezzi → **4 regole distinte**, con il CSP che compare su 3 URL
e conta una volta, pesato per diffusione.

**Le scansioni parziali sono dichiarate.** Se spider o active scan vanno in
timeout, gli alert raccolti valgono più di niente — ma spacciarli per completi
no. Il risultato porta `complete: False` e un rilievo in testa che lo dice.
Verificato forzando il timeout a zero.

- [x] Percorso completo eseguito (contro un daemon simulato).
- [x] Chiavi del JSON confermate.
- [x] Nessun daemon orfano: non lo avviamo più.
- [x] `zapcli` sostituito dal client ufficiale.
- [x] Alert raggruppati per regola.
- [ ] Verifica contro un daemon ZAP **reale**: Java non è installato qui.
- [ ] Taratura di `ZAP_PENALTIES` su scansioni vere.

### C8 — ✅ FATTO (2026-08-20): WCAG reale via axe-core su Chromium
`mars_wcag.py` controllava **due criteri**: `lang` sulla sola prima pagina e i
testi alternativi. Il README raccomandava axe-core, e `playwright` era già fra
le dipendenze senza essere importato da nessun file.

**Stavolta lo strumento c'era davvero**, a differenza di ZAP in R4: Playwright
1.62, Chromium installato e `axe-core` 4.13 in `node_modules`. Il percorso è
quindi stato **eseguito**, non solo scritto.

**Si naviga alle pagine reali, non si inietta l'HTML salvato.** È la scelta di
progetto che conta: senza CSS e JavaScript i criteri su contrasto, focus e
contenuto generato darebbero risultati sbagliati, che è peggio che non darli.
La prova lo conferma — su una pagina costruita apposta, axe rileva
`color-contrast`, che dall'HTML grezzo sarebbe invisibile. Il browser è lento,
quindi axe gira sulle prime pagine e il referto **dichiara quante ne ha viste**.

**Il punteggio raggruppa per regola, non per occorrenza.** Un difetto trovato
collaudando: axe restituisce le violazioni pagina per pagina, quindi un solo
problema ricorrente su cinque pagine arrivava cinque volte e affondava il
punteggio da solo. Ora si penalizza la **regola violata**, con un fattore di
diffusione che va da 1× (una pagina) a 2× (tutte). Verificato: la stessa
violazione su 1 pagina di 5 dà 86, su tutte e 5 dà 76 — un fattore due, non
cinque.

**L'euristica statica è stata comunque allargata** da due criteri a sette, e
copre *tutte* le pagine mentre axe ne vede le prime: `lang` su ogni pagina,
testi alternativi, salti nella gerarchia degli heading, campi di modulo senza
etichetta, tabelle dati senza `<th>`, link con testo generico, `tabindex`
positivi. Ogni rilievo **cita il criterio WCAG** a cui si riferisce, perché un
rilievo senza riferimento non è verificabile da chi lo riceve. I rilievi statici
restano nel referto anche quando axe è attivo.

Verificati i casi che distinguono un controllo utile da uno rumoroso: una
tabella `role="presentation"` non conta, un link generico con `aria-label` non
conta, `tabindex="0"` non conta, un campo avvolto da `<label>` è etichettato.

**Il livello è dichiarato**: `WCAG 2.1 A + AA`, sia come filtro passato ad axe
(`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`) sia come etichetta nel referto —
in tutti e tre i formati e nell'API. Il ripiego statico si dichiara come
*"parziale: solo criteri statici"*, perché "accessibile" senza un livello non
significa nulla.

**Verificato end-to-end:** sito costruito rotto → **0/100** con quattro regole
violate; sito pulito → **100/100**; ripiego statico simulato → 64/100 con lo
strumento `markup` dichiarato; `tool`, `wcag_level` e `pages_tested` presenti
in JSON e HTML.

- [x] Percorso axe-core opzionale, attivo solo se browser e libreria ci sono.
- [x] Euristica statica allargata da 2 a 7 criteri, su tutte le pagine.
- [x] Livello WCAG dichiarato nel referto.

### C6 — ✅ FATTO (2026-08-20): crawling interno quando manca la sitemap
Il README diceva *"via sitemap o crawling interno"*, ma il crawling interno non
esisteva: senza sitemap il fallback era `urls = [self.base_url]`, cioè **una
sola pagina**. `--max-pages 40` su un sito senza sitemap ne produceva **1**, e
tutte le sette aree giudicavano quell'unica pagina come se fosse il sito.

**Innestata, non affiancata.** Il ciclo di `crawl()` è diventato una coda FIFO
— ampiezza, non profondità — e la scoperta per link condivide le *stesse*
regole introdotte da **R7**: robots.txt rispettato, filtro same-host,
normalizzazione degli URL, controllo di status e `Content-Type`, pausa fra le
richieste, tetto a `--max-pages`. La scoperta per link non è una seconda strada
che aggira i controlli: è la stessa strada con una sorgente diversa. `estrai_link()`
riusa `normalize_url()` e `host_matches()`, gli stessi applicati alla sitemap.

Due dettagli che sarebbe stato facile sbagliare:

- `urljoin` si applica all'URL **finale** della risposta (`resp.url`), non a
  quello richiesto: dopo un redirect i link relativi vanno risolti rispetto a
  dove si è arrivati.
- `mailto:`, `tel:`, `javascript:`, `data:` e i frammenti puri sono scartati in
  fase di estrazione, e la coda ha un tetto (`MAX_CODA`) perché su un sito
  grande la scoperta cresce anche quando le pagine scaricate non crescono più.

**La sitemap resta autoritativa quando c'è.** È la dichiarazione del sito su
cosa vuole far indicizzare: si rispetta e non si va a caccia d'altro. Il
crawling per link è il ripiego, non un'aggiunta.

**Il referto dichiara come ha trovato le pagine** — `sitemap` o `link
interni` — in tutti e tre i formati e nell'API. Cambia il significato del
campione: due pagine dichiarate dal sito non sono la stessa cosa di cinque
raggiunte seguendo la navigazione.

**Verificato** con un secondo server di prova, senza sitemap e con link
interni, che include di proposito i casi ostili:

```
prima : 1 pagina  (urls = [self.base_url])
dopo  : 5 pagine  ['/', '/a', '/b', '/c', '/d']
scarti: vietato da robots.txt: /privato/p
        HTTP 404: /rotta
```

`a#sezione` non produce un doppione di `/a`; `https://esterno.test/x` e
`mailto:` non entrano mai in coda; `--max-pages 3` restituisce 3 pagine. Il
sito **con** sitemap resta invariato: 2 pagine, modalità `sitemap`. API e
referto HTML verificati, quest'ultimo ancora senza alcun riferimento esterno.

- [x] BFS sui link interni con coda, visitati, `urljoin`, same-host,
      normalizzazione e stop a `max_pages`.
- [x] Nessuna dipendenza nuova: `urllib.parse` e BeautifulSoup.
- [x] Innestata sulle regole di **R7**.

### C5 — ✅ FATTO (2026-08-20): query personalizzate e consenso aggregato
Il README mostrava `--queries q.txt`, ma la query era **una sola e cablata** —
`"cos'è questo sito"` — per giunta duplicata in due file. Era il limite più
serio della simulazione RRF: fondere due classifiche prodotte da **una** query
dice pochissimo, mentre la formula del paper ha senso su un insieme di
interrogazioni.

**`--queries FILE`** (e il campo `queries` via API) alimenta
`context["queries"]`. Il caricatore è quello già estratto da **C3**, quindi non
è stata scritta una seconda copia.

**Le query di default sono nella lingua del sito.** Quattro intenti generici,
scelti in base all'attributo `lang` prevalente fra le pagine — il campo che
**R9** aveva fatto conservare al crawler. Interrogare un sito inglese in
italiano produrrebbe un consenso basso che non dice nulla sul sito, ma solo che
le domande erano nella lingua sbagliata. Lingua ignota: italiano più inglese.
Sono dichiarate come punto di partenza, non come riferimento.

**Entrambi i retriever ciclano sulle query** e restituiscono `per_query` più un
**rango aggregato**, ottenuto fondendo le classifiche per query **con l'RRF
stesso**: un chunk in alto su più domande è più citabile di uno che vince una
volta sola. I quattro moduli che leggono `rank` — citabilità, giudizio LLM,
referto — continuano a funzionare senza modifiche, e ricevono ora un dato
migliore: il rango aggregato invece di quello di una singola query.

Il referto espone `rrf_simulation` (una voce per query, la chiave che
`--from-audit` legge) e `rrf_aggregate`, dichiarato come la misura più solida.

**La metrica ora discrimina davvero.** Sul sito di prova, che documenta l'RRF:

```
come funziona la fusione reciproca dei ranghi   3/3
cos'è la costante k dell'RRF                    3/3
quando conviene usare una ricerca ibrida        2/3
--- contro le generiche ---
come funziona                                   1/3
chi siamo                                       2/3
```

È la differenza fra misurare il sito e misurare la genericità della domanda.

**Catena completa verificata:** `--queries` → audit → `--format json` → le tre
query personalizzate compaiono in `rrf_simulation` → `mars_citations
--from-audit` le rilegge tutte e tre. Stima e misura della citabilità guardano
ora le stesse domande.

Verificato anche: file di query inesistente → uscita 2; API con e senza
`queries`; tabella per query nel referto HTML, che resta autoconsistente
(9,3 KB, zero riferimenti esterni); regressione su `example.com`.

- [x] `--queries PATH`, una query per riga.
- [x] `context["queries"]` con default generico multilingue.
- [x] Entrambi i retriever ciclano, con `rank` per query.
- [x] Consenso e RRF aggregati su tutte le query.

### C4 — ✅ FATTO (2026-08-20): referto JSON e HTML
Il README mostrava nell'`Uso:` il comando
`--format html --output report.html`, ma `argparse` non conosceva né l'uno né
l'altro flag: **il comando documentato terminava con un errore**.

**Il dato prima della presentazione.** `mars_report.build_report()` produce la
struttura canonica; `render_text`, `render_json` e `render_html` ne sono tre
viste. Prima la logica del referto viveva dentro le `print`, quindi esisteva un
solo formato possibile e l'API doveva ripetere gli stessi calcoli per conto
proprio. È il principio 8 applicato a ciò che il progetto produce, non solo a
come è scritto.

**`/audit/full` restituisce ora la stessa struttura**, con i risultati grezzi
per modulo sotto `modules`. Il calcolo dell'RRF che l'endpoint faceva da sé è
sparito: era la stessa logica scritta due volte. *Attenzione: la forma della
risposta è cambiata* — `rrf_analysis` è diventato `rrf_simulation`, con la
stessa informazione più la query.

**Il referto HTML è autoconsistente**, verificato: **zero** riferimenti
esterni, **zero** tag `<script>`, CSS incorporato, favicon `.ico` inclusa come
data URI. Si usa il `.ico` da 2,8 KB e non il `.png` da 344 KB: il referto deve
restare un file solo, ma non a costo di mezzo megabyte di icona. 8,8 KB in
tutto, con tema chiaro e scuro.

**Escape verificato con input ostile.** Il referto contiene testo preso dal
sito analizzato — titoli, heading, motivi di scarto — quindi un sito potrebbe
iniettare markup. Provato con `<script>alert(1)</script>` nell'URL e
`<img src=x onerror=...>` fra gli URL saltati: tutto esce come entità, nessun
tag viene aperto.

**Chiude anche l'ultima voce di C3.** `--from-audit` di `mars_citations.py`
era dormiente perché nessuno produceva `rrf_simulation`. Ora il referto JSON la
espone — una voce per query, con `query`, consenso e passaggio migliore — e la
catena funziona: `mars_audit --format json --output r.json` seguito da
`mars_citations --from-audit r.json` legge la query e prosegue, fermandosi solo
sulla credenziale mancante. La forma è già quella definitiva, così **C5** potrà
aggiungere query senza toccare il contratto.

**Nuovo codice di uscita 3** per `--output` non scrivibile: prima un percorso
non valido sarebbe passato inosservato.

Verificato: il referto testuale è **identico** a prima del rifacimento; JSON
valido con quindici campi di primo livello; HTML autoconsistente; catena
audit → citations funzionante; exit 0 / 2 / 3 corretti.

- [x] `--format {text,json,html}` e `--output PATH`.
- [x] `build_report()` puro più tre renderer; l'API riusa lo stesso dict.
- [x] HTML self-contained, nessuna CDN.
- [x] `favicon.ico` agganciata come data URI.

### C3 (residue) — ✅ CHIUSE (2026-08-20): verifiche e caricatore condiviso
Delle tre voci rimaste dopo la stesura di `mars_citations.py`, due sono chiuse
e una resta legata a **C4**.

**Il modello OpenAI era corretto.** `gpt-5.6` è un alias valido di
`gpt-5.6-sol`, il modello di punta della famiglia; verificato sulla
documentazione OpenAI, non dedotto. La docstring porta ora la data di
riverifica.

**Ma la stessa verifica ha trovato un difetto.** Le fonti consultate sono
esposte sull'item `web_search_call` **solo se la richiesta le chiede**, con
`include: ["web_search_call.action.sources"]`. Il codice le leggeva senza
chiederle: `searched_urls` sarebbe rimasto sempre vuoto e `site_consulted`
sempre falso — una metà della metrica silenziosamente morta. Aggiunto
l'`include`.

**Il caricatore di query è ora condiviso.** `load_queries()` vive in
`mars_core.py` e prende parametri semplici invece di un `argparse.Namespace`;
`mars_citations.py` ne è un adattatore di due righe. Le stesse query che
guidano la simulazione RRF devono poter guidare il monitoraggio delle
citazioni, altrimenti i due strumenti misurano cose diverse e confrontarli non
significa nulla. **C5** lo troverà già pronto invece di riscriverlo.

Legge sia `rrf_simulation` (voci come dizionari con chiave `query`, o come
stringhe) sia un `queries` di primo livello: accettare entrambe le forme evita
di dover riscrivere il caricatore quando C4 fisserà il formato. Provato su
nove casi, inclusi file mancante, referto non JSON e referto senza query.

**Un difetto grave trovato collaudando.** Senza credenziali,
`mars_citations.py` **terminava con un traceback** invece del codice di uscita
`2` che il README documenta per "provider non configurato". La causa è la
stessa di **C2**: l'SDK Anthropic costruisce il client senza protestare e
solleva `TypeError` alla prima *richiesta*. Non era un caso isolato ma una
classe di difetto, ed è stata corretta in entrambi i punti.

`AnthropicProvider` verifica ora alla costruzione che `api_key` o `auth_token`
siano risolti — restano `None` quando non c'è né variabile d'ambiente né
profilo `ant auth login` — e solleva `RuntimeError`, che `main()` traduce nel
codice 2. Più una rete di sicurezza in `ask()`, perché una query fallita non
faccia cadere l'intero monitoraggio. Verificati tutti i codici documentati:
2 per provider non configurato, query mancanti e troppi concorrenti; 0 per
`--version`. Zero righe di traceback.

- [x] Verificare `OPENAI_MODEL = "gpt-5.6"` — valido, ed è emerso il difetto
      dell'`include`.
- [x] Riusare `load_queries()` fra i due strumenti.
- [ ] `--from-audit` resta dormiente finché **C4** non produce il referto JSON.

### C3 — ✅ IN GRAN PARTE FATTO (2026-08-19): monitoraggio delle citazioni IA
Il requisito, prima non deducibile, è ora specificato nel README (provider,
flag, codici di uscita) e implementato in `mars_citations.py` (585 righe).

Verificato contro la documentazione Anthropic corrente: `claude-opus-5`,
`web_search_20260209`, e l'accoppiamento `betas=["server-side-fallback-2026-07-01"]`
con `fallbacks="default"` (la forma ad array vuole `-06-01`: scambiarle dà 400).
Gestisce correttamente `pause_turn`, `refusal`, e il caso in cui `content` di
`web_search_tool_result` sia un oggetto d'errore invece di una lista.
`flake8` pulito su tutto il file.

**Adattamenti applicati:** rinominato da `mars_citability.py` (due stringhe
interne già dicevano `mars_citations.py`); `norm_host`/`host_matches` spostati
in `mars_core.py`; corretta la ripresa dopo `pause_turn`, che dalla seconda
pausa sostituiva il turno assistente invece di accodarlo, facendo perdere al
modello le ricerche già svolte; newline finale.

Deliberatamente **fuori** da `MODULES_REGISTRY` e **senza** `audit(context)`:
non è un'area di audit, è uno strumento periodico da cron, come da README.

- [x] Definire il requisito e implementare `mars_citations.py`.
- [ ] `--from-audit` è dormiente: legge `report["rrf_simulation"]`, chiave che
      nessun modulo produce ancora. Non è un difetto ma un **contratto in
      anticipo**: il referto JSON di **C4** dovrà esporre
      `rrf_simulation: [{"query": ...}, ...]`, e le query vengono da **C5**.
- [ ] Verificare `OPENAI_MODEL = "gpt-5.6"`: è un altro fornitore, non
      verificabile con la documentazione Anthropic.
- [ ] Riusare `load_queries()` anche in `mars_audit.py` quando si farà C5,
      invece di riscriverne una seconda copia.

### Manutenzione (2026-08-19): caricatore di moduli e import pigro
Due difetti di `mars_core.py` / `load_external_module()` emersi mentre si
integrava `mars_citations.py`. Entrambi erano voci di **R11**.

**`load_external_module()` non registrava il modulo in `sys.modules`.**
Qualunque modulo che usi `@dataclass` insieme a
`from __future__ import annotations` falliva il caricamento con
`'NoneType' object has no attribute '__dict__'`, perché `dataclasses` risolve
le annotazioni passando da `sys.modules[cls.__module__]`. L'eccezione veniva
inghiottita e l'utente leggeva `[ ] ... ignorato (file non trovato)` — con il
file presente sul disco. Corretto in `mars_audit.py` e `mars_api.py`
(registrazione prima di `exec_module`, rimozione in caso di errore).
È il prerequisito della decisione sullo stile: senza, ogni modulo scritto
nel nuovo stile sarebbe sparito silenziosamente dall'audit.

**Import di `sentence-transformers` reso pigro.** Era eseguito all'import di
`mars_core` e trascinava torch: **3,01 s pagati da chiunque**, compreso
`--embeddings none` che il modello non lo carica mai, e `mars_citations.py`
che non lo usa affatto. Ora la funzione `load_sentence_transformers()` lo
importa alla prima richiesta reale: `import mars_core` costa **0,10 s**.
Entrambe le modalità di `VectorRetriever` verificate — sul parafrasi
*"un felino riposa sul sofà"* il proxy char-tfidf dà 0.0, gli embedding
reali 0.748.

**`norm_host()` / `host_matches()` spostati in `mars_core.py`**, dove
serviranno identici al filtro same-host del crawler (**R7**).

### Decisione (2026-08-19): stile di riferimento del progetto
`mars_citations.py` è stato adottato come modello per il codice nuovo:
type hints, `@dataclass`, I/O separato dalla logica, il dato (`payload` dict)
prima della presentazione (`render_text` / `render_json`), `__version__`,
codici di uscita espliciti, docstring che spiegano il perché.

La decisione è registrata come **principio 8** in [TO-DO.md](TO-DO.md), e
l'allineamento graduale dei moduli esistenti è **R13**, ancora aperto.
Lo stile cambia, la filosofia (principi 1-7) no.

