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
| R15 | Un solo URL malformato faceva cadere l'intero audit | 2026-08-20 |
| R16 | Mojibake silenzioso sui siti UTF-8 senza charset | 2026-08-20 |
| R17 | I redirect non venivano rivalidati | 2026-08-20 |
| R18 | La punteggiatura escludeva le parole da BM25 | 2026-08-20 |
| — | Referto HTML nello stile di Lighthouse, esteso alle nostre aree | 2026-08-20 |
| R19 | I segnali di pagina gonfiavano `answer_shaped_ratio` | 2026-08-20 |
| R20 | axe fabbricava un 100/100; la suite lanciava Chromium | 2026-08-20 |
| R21 | «Di superficie» era indistinguibile da una misura piena | 2026-08-20 |
| R22 | L'esecutore di moduli non reggeva i plugin che rompono | 2026-08-20 |
| — | La sezione SEO riporta i controlli di Lighthouse, non il solo voto | 2026-08-20 |
| R23 | Query perse con un retriever caduto; ranghi a informazione zero | 2026-08-20 |
| R24 | Casi limite del crawler sugli URL (IPv6, loc relativi, robots vuoto) | 2026-08-20 |
| C13 | File di progetto: git, CLAUDE.md, CONTRIBUTING, CoC | 2026-08-19 |
| C1+C7 | Profili di citabilità IA; riuso dei risultati fra moduli | 2026-08-19 |
| C2 | Giudizio LLM sulla citabilità (`mars_llm_judge.py`) | 2026-08-19 |
| — | Caricatore di moduli: cache, e bytecode stantio corretto | 2026-08-20 |
| — | Aiuto della CLI: valori, esempi, avvertenze | 2026-08-20 |
| C12 | Suite di test: 146 test, verificati reintroducendo i difetti | 2026-08-20 |
| C10 | `mars_tech` copre indicizzabilità, sitemap e 13 crawler IA | 2026-08-20 |
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

### R15 — ✅ RISOLTO (2026-08-20): un solo URL malformato faceva cadere l'intero audit
`normalize_url()` chiama `urlsplit()` e legge `parts.port`, che sollevano
`ValueError` su porta non numerica, porta fuori range e IPv6 malformato.
Nessuno dei due chiamanti la catturava, e in `run_audit()` `build_context()` sta
**fuori dal `try`**: un solo `href` rotto in una pagina — o un solo `<loc>` rotto
in una sitemap — uccideva l'audit intero.

**Riprodotto ai tre livelli**, con server HTTP locali, prima di toccare il
codice:

```
crawler : ValueError: Port could not be cast to integer value as 'port'
          pagine raccolte e PERSE: ['http://127.0.0.1:8771/']   skipped: []
CLI     : traceback, exit 1
API     : POST /audit/tech -> 500,  POST /audit/full -> 500
```

Il dettaglio peggiore è l'**exit 1** della CLI: non solo è fuori dal contratto
documentato (0 referto, 2 nessuna pagina, 3 scrittura), ma è proprio il valore
che [TO-DO.md](TO-DO.md) tiene riservato alla futura soglia `--fail-under`
(idea **I2**). Una pipeline che un domani usasse quella soglia leggerebbe il
crash come "sito sotto soglia": un guasto travestito da giudizio.

**Due punti d'ingresso, non uno.** `estrai_link()` normalizza gli `href` della
pagina, `crawl()` normalizza ciò che esce dalla coda — dove arrivano i `<loc>`
della sitemap. Entrambi sono stati riprodotti separatamente, ed è stato giusto
farlo: il difetto vive in due posti indipendenti.

**Una trappola trovata misurando, non leggendo.** In `estrai_link` la riga era
`normalize_url(urljoin(base, href))`, e su un IPv6 malformato è **`urljoin`
stesso** a sollevare, prima ancora che `normalize_url` venga chiamata:

```
urljoin('http://sito.test/base/', 'http://[::1/pagina') -> ValueError: Invalid IPv6 URL
```

Proteggere solo `normalize_url` avrebbe lasciato aperta metà del difetto.

**Risoluzione applicata.** `safe_normalize_url(url, base=None)` in `mars_core.py`
restituisce `None` invece di sollevare, con **l'urljoin dentro la guardia**.
`normalize_url()` resta intatta e continua a sollevare: è una funzione pura con
un contratto chiaro, e il posto giusto per la tolleranza è il confine dove entra
il dato non fidato, non la funzione che lo elabora. Gli URL da normalizzare
arrivano dal sito analizzato: sono **dato ostile, non un errore di
programmazione**.

I due chiamanti scartano l'URL e lo dichiarano in `skipped`, che il referto
mostra già sotto "cosa non è stato guardato" (principio 6): un `href` rotto è
anche un rilievo sul sito, non solo un fastidio per noi.

**Gli scarti sono deduplicati**, e non è un dettaglio estetico: lo stesso `href`
rotto in un template compare su *ogni* pagina del sito, e senza deduplicazione
riempirebbe il referto HTML — che li stampa tutti — con la stessa riga ripetuta.
Verificato con un `<loc>` malformato presente due volte nella sitemap: una sola
riga nel referto.

**Verificato.** Le tre riproduzioni ripetute dopo la correzione:

```
crawler : 2 pagine indicizzate (era: crash dopo la prima)
          skipped: ['URL non analizzabile: http://sito.test:port/rotto']
CLI     : referto prodotto, exit 0, "URL saltati: 1" nel referto
API     : POST /audit/tech -> 200,  POST /audit/full -> 200
```

Il link **buono** presente sulla stessa pagina del link rotto viene comunque
seguito: la correzione scarta l'URL, non la pagina.

**Regressione sul percorso normale: nessuna differenza.** Audit completo su un
sito locale pulito, referto confrontato fra `HEAD` e la versione corretta —
**identico** a meno della data di generazione.

**La prova che conta: reintrodurre il difetto.** Quattro mutazioni, una per
ciascuna parte della correzione:

```
1. estrai_link senza guardia                 -> 2 falliti
2. crawl senza guardia (percorso sitemap)    -> 1 fallito
3. funzione tollerante senza try/except      -> 8 falliti
4. deduplicazione degli scarti rimossa       -> 1 fallito
```

**Alla prima esecuzione la mutazione 2 NON veniva rilevata**, e va detto: i test
coprivano `estrai_link` ma nessuno esercitava `crawl()`, cioè proprio il
percorso del `<loc>` di sitemap di cui avevo riprodotto il crash. La suite
sarebbe rimasta verde con metà del difetto rimessa dentro. È la stessa lezione
di **C12** — tre test vacui su sei — ed è arrivata di nuovo dalla stessa
verifica, il che è un buon argomento per non saltarla mai.

Colmarla ha richiesto di far girare `crawl()` senza rete: un
`requests.adapters.BaseAdapter` finto montato sulla `session` del crawler serve
le risposte da un dizionario e intercetta ogni richiesta. Serviva un adattatore
perché la fixture `niente_rete` copre `requests.get`, **non** `Session.get`.
È anche il primo test che esercita `Crawler` direttamente, e il pattern resta
disponibile per **I13**, che propone di coprire il resto della classe.

- [x] Catturare `ValueError` (inclusa quella di `urljoin`) al confine.
- [x] Scartare il singolo URL e dichiararlo in `skipped`.
- [x] Deduplicare gli scarti, perché un template rotto non allaghi il referto.
- [x] Test su entrambi i punti d'ingresso, validati per mutazione.

### R16 — ✅ RISOLTO (2026-08-20): mojibake silenzioso sui siti UTF-8 senza charset
Il crawler leggeva `resp.text`. Ma `requests` applica a **ogni** `text/*` privo
del parametro `charset` il default legacy di RFC 2616, cioè ISO-8859-1 — regola
che HTML5 ha abbandonato proprio perché sbaglia su ogni sito UTF-8:

```
get_encoding_from_headers({"content-type": "text/html"})  ->  'ISO-8859-1'
```

Su un sito UTF-8 servito senza `charset` nell'header — configurazione
comunissima — `title`, `headings`, `text`, `chunks`, `json_ld` e l'HTML grezzo
entravano **corrotti** nel corpus, senza un solo errore. Non è un difetto
estetico: sono gli ingressi di BM25, del proxy char-TFIDF e dell'RRF, quindi
ogni punteggio a valle era calcolato su mojibake.

**Visibile nel referto**, sullo stesso sito prima e dopo:

```
prima : Top Chunk Ibrido : .../ § PerchÃ© Ã¨ giÃ  cosÃ¬ caro?
dopo  : Top Chunk Ibrido : .../ § Perché è già così caro?
```

**Risoluzione applicata.** `decode_html(content, content_type)` in
`mars_core.py` — funzione pura, verificabile senza rete — applica l'ordine
dello standard: **BOM**, poi il **charset dell'header**, poi `<meta charset>` o
rilevamento statistico. Gli ultimi due li fa `UnicodeDammit`, che BeautifulSoup
porta già con sé: nessuna dipendenza nuova (principio 1).

Si decodifica **una volta sola** e si parsa quella stringa, invece di chiamare
`resp.text` due volte: così il DOM e l'`html` grezzo conservato per gli altri
moduli non possono divergere.

**Il BOM va guardato a mano, e l'ho scoperto misurando.** `UnicodeDammit`
accetta `known_definite_encodings` per l'header, ma **non gli fa cedere il
passo al BOM**: con byte UTF-8 con BOM e un header che dichiara latin-1
sceglieva latin-1. È il caso classico della pagina scritta su Windows e servita
da un server mai riconfigurato, quindi tutt'altro che teorico.

**Una scoperta contraria all'attesa, e va detta.** `user_encodings=["utf-8"]`
era stato aggiunto **solo per velocità**: il rilevamento statistico su una
pagina da 80 KB costa **175 ms** contro 0,06 quando non parte affatto. Il
confronto sistematico dei due percorsi su dieci combinazioni ha però mostrato
**una differenza di risultato**, in meglio: una pagina con `<meta charset>`
*stantio* — dice latin-1, i byte sono UTF-8, il residuo tipico di una
migrazione — smette di produrre mojibake. Cercavo la velocità e ho trovato
anche una correzione.

Il tentativo UTF-8 è **autoverificante**, ed è la ragione per cui anticiparlo è
lecito: i byte accentati di una pagina davvero latin-1 non sono UTF-8 valido,
quindi fallisce e gli altri candidati vengono provati comunque. Verificato: una
pagina genuinamente latin-1 resta letta come latin-1.

**Chiuso contestualmente anche robots.txt.** Viaggia come `text/plain`, quindi
subiva lo stesso ISO-8859-1. RFC 9309 impone UTF-8, e una direttiva `Sitemap:`
con un IDN ne usciva storpiata. Ora si decodifica in UTF-8 con sostituzione.
Le sitemap invece erano già a posto: `_read_sitemap` usa `resp.content` e
lascia decidere al parser XML, come deve.

**Verificato.** Undici test nuovi coprono la matrice delle precedenze — meta
sola, header solo, entrambi, nessuno dei due, `application/xhtml+xml`, pagina
davvero latin-1, header contro meta stantio, BOM contro header sbagliato,
charset inventato, byte indecodificabili — più i due punti d'ingresso del
crawler. Sul sito pulito di regressione il referto è **identico** a quello di
`HEAD`.

**La prova che conta: reintrodurre il difetto.**

```
1. pagina di nuovo da resp.text (il difetto)  -> 1 fallito
2. robots.txt di nuovo da resp.text           -> 1 fallito
3. BOM non piu' guardato                      -> 1 fallito
4. charset dell'header ignorato               -> 1 fallito
5. html grezzo scollegato dal DOM             -> 1 fallito
```

**Alla prima esecuzione tre mutazioni su cinque NON venivano rilevate**, ed è
il risultato più utile di tutta la voce. La colpa non era dei test ma del banco
di prova: l'adattatore finto introdotto da **R15** impostava
`resp.encoding = "utf-8"`, quindi `resp.text` funzionava sempre e il mojibake
non poteva manifestarsi. È **esattamente la lezione di C9** — *un banco di
prova troppo accomodante conferma anche ciò che è sbagliato* — ripresentatasi
in un punto diverso. L'adattatore deriva ora l'encoding dagli header con la
**stessa** funzione di `HTTPAdapter.build_response`, e le tre mutazioni
falliscono.

La quarta mutazione ha richiesto di cercare un caso in cui l'header è davvero
decisivo: pagina cirillica in `windows-1251` senza `<meta>`, dove il solo
rilevamento sceglie `maccyrillic` e sbaglia il primo carattere.

- [x] `decode_html()` con l'ordine di precedenza dello standard.
- [x] Una sola decodifica: DOM e HTML grezzo non possono divergere.
- [x] robots.txt in UTF-8 per RFC 9309.
- [x] Banco di prova reso fedele a `requests`.

### R17 — ✅ RISOLTO (2026-08-20): i redirect non venivano rivalidati
`crawl()` lasciava che `requests` seguisse i redirect da solo, poi non
guardava mai dov'era finito: `host_matches()` e `can_fetch()` giravano
esclusivamente sull'URL **richiesto**. Un redirect bastava quindi al sito per
decidere cosa il crawler scaricasse.

**Quattro effetti, tutti riprodotti** con l'adattatore finto:

```
(a) robots.txt aggirato via redirect  : True   /porta -> /privato/segreto (Disallow)
(b) host esterno indicizzato          : True   /fuori -> esterno.test, title "CONTENUTO ESTERNO"
(c) stessa pagina due volte nel corpus: True   /vecchia e /nuova, testo identico
(d) richiesta VIETATA partita davvero : True
skipped: (vuoto)
```

Il difetto è grave su due piani distinti. Il primo è una **promessa rotta**:
`README.md` e `CLAUDE.md` dichiarano che il crawler rispetta robots.txt, e
l'unico modo per ignorarlo dovrebbe essere la dichiarazione di proprietà
introdotta da **R7**. Il secondo è la **contaminazione del corpus**: il
contenuto di un altro host entrava in BM25, nel proxy char-TFIDF e nell'RRF
come se fosse del sito analizzato, e `skipped` non ne diceva nulla.

**Il punto (d) è quello che decide la forma della correzione.** Ricontrollare
`resp.url` a cose fatte avrebbe evitato di *indicizzare* la pagina, ma la
richiesta vietata sarebbe comunque partita: il crawler avrebbe disobbedito e
poi nascosto la prova. Per questo `_scarica_pagina()` segue i redirect **uno a
uno**, con `allow_redirects=False`, e controlla host e robots.txt **prima** di
ogni salto — così la richiesta vietata non parte affatto. Verificato
ispezionando gli URL realmente chiesti dall'adattatore.

`_get()` continua invece a seguirli da sé per robots.txt e le sitemap, che non
sono pagine da indicizzare — e per robots.txt **RFC 9309 chiede esplicitamente
di seguirli**, oltre al fatto che `/robots.txt` che redirige (http→https, www)
è comunissimo. C'è un test apposta perché quel comportamento non regredisca.

**La pagina si registra sotto l'URL di ARRIVO**, non più sotto quello
richiesto: è lì che il contenuto vive davvero, ed è quello che finisce nei
chunk e che `mars_tech` confronta con il `canonical`. Questo da solo chiude
(c), perché la chiave del dizionario diventa la stessa.

**Un tetto di 5 salti** (quanti ne segue Googlebot), più il riconoscimento dei
cicli.

**Una correzione nata da una misura, non da una lettura.** Il controllo del
duplicato stava all'inizio *a valle* di `_scarica_pagina`. Contando le
richieste è emerso che nell'ordine "prima `/nuova`, poi `/vecchia`" la pagina
veniva scaricata **due volte**: il controllo dichiarava il duplicato dopo aver
già sprecato la richiesta. Spostato dentro `_scarica_pagina`, prima del salto —
il che ha richiesto di promuovere `visti` da variabile locale di `crawl()` ad
attributo del crawler. Misurato dopo: **una sola richiesta in entrambi gli
ordini**.

**Diagnosi precise sui casi degeneri**, applicando la lezione di **R6** (vuoto
≠ malformato). Una `Location` vuota veniva risolta da `urljoin` nell'URL di
partenza e riportata come *«più di 5 redirect»*: difetto sbagliato, e cinque
richieste sprecate per scoprirlo. Ora:

| caso | diagnosi | richieste |
|---|---|---|
| `Location` vuota | redirect senza destinazione | 1 |
| redirect su se stesso | redirect circolare | 1 |
| ciclo a due | redirect circolare | 2 |
| `Location` malformata | redirect verso URL non analizzabile | 1 |
| catena lunga | più di 5 redirect | 6 |

**Verificato.** I quattro effetti ripetuti dopo la correzione danno tutti
`False`, con `skipped` che dichiara i due scarti; la pagina compare una volta
sola, sotto `/nuova`. In CLI il referto lo dice a chi legge:

```
URL saltati          : 2
  · redirect verso URL vietato da robots.txt: .../porta -> .../privato/segreto
  · redirect verso host esterno: .../fuori -> http://esterno.invalid/x
```

Sul sito pulito di regressione, senza redirect, il referto è **identico** a
quello di `HEAD`.

**La prova che conta: reintrodurre il difetto.** Sette mutazioni, tutte
rilevate:

```
1. redirect di nuovo seguiti da requests    -> 11 falliti
2. robots non ricontrollato sul salto       ->  1 fallito
3. host non ricontrollato sul salto         ->  1 fallito
4. duplicato dopo redirect non riconosciuto ->  2 falliti
5. pagina registrata sotto URL richiesto    ->  2 falliti
6. redirect circolare non riconosciuto      ->  2 falliti
7. Location vuota non riconosciuta          ->  1 fallito
```

**La mutazione 4 alla prima esecuzione non veniva rilevata**, e la ragione è
istruttiva: il test verificava solo le chiavi di `pages`, che ormai
deduplicano da sole grazie alla registrazione sotto l'URL di arrivo. Il
controllo esplicito compra altro — **non richiedere la pagina due volte** e
dichiarare il duplicato — e finché il test non ha misurato *quelle* due cose
era vacuo. È la terza volta in tre voci che la batteria di mutazioni trova un
test che sembrava corretto.

**L'adattatore di prova è stato reso più fedele una seconda volta.** Non
impostava `resp.request`, e senza quello `requests` non sa risolvere i
redirect: il difetto non si manifestava affatto nei test. Dopo `resp.encoding`
di **R16**, è il secondo pezzo di `HTTPAdapter.build_response` che mancava.

- [x] Redirect seguiti un salto per volta, con i controlli **prima**.
- [x] robots.txt e sitemap continuano a seguirli (RFC 9309).
- [x] Pagina registrata sotto l'URL di arrivo.
- [x] Duplicati riconosciuti senza sprecare una richiesta.
- [x] Cicli, tetto sui salti e `Location` degeneri diagnosticati.

### R18 — ✅ RISOLTO (2026-08-20): la punteggiatura escludeva le parole da BM25
`mars_lexical` tokenizzava con `.lower().split()`, quindi `"funziona?"` restava
un token **diverso** da `"funziona"`: un chunk che conteneva davvero la frase
cercata non prendeva alcun credito per quella parola.

**Un'affermazione del TO-DO era sbagliata, e va detta.** La voce diceva che
anche `mars_semantic` tokenizza con `split()`. Non è vero: lì `split()` conta
le parole per la soglia `MIN_PAROLE`, mentre il recupero passa da
`VectorRetriever`, che lavora su **trigrammi di caratteri** — per i quali
`"funziona?"` e `"funziona"` condividono quasi tutti i trigrammi. Il difetto
era confinato a `mars_lexical`.

**Ed è proprio questa asimmetria a fare il danno peggiore.** Il recuperatore
vettoriale vedeva la corrispondenza, quello lessicale no: i due si trovavano in
disaccordo per una ragione che **non ha nulla a che fare col sito**, e il
consenso RRF — che il README presenta come il cuore del progetto — ne usciva
falsato. Misurato su un corpus di tre chunk:

```
BM25       : [0.4700, 0.4869, 0.0]   -> primo il chunk 1
vettoriale : [0.4221, 0.0966, 0.0161] -> primo il chunk 0
```

Il chunk 0 è quello che contiene la frase cercata. Per BM25 finiva **sotto** un
chunk più corto che la parola `"funziona"` non la conteneva affatto: la
normalizzazione sulla lunghezza premiava il più breve, e il più pertinente non
aveva modo di recuperare. L'RRF andava dietro all'errore.

**Risoluzione applicata.** `tokenize()` in `mars_core.py` toglie la
punteggiatura di **confine** e lascia intatto l'interno. Vive lì e non in
`mars_lexical` perché corpus e query **devono** passare per la stessa funzione:
se divergono, la query smette di trovare ciò che l'indice contiene, ed è un
difetto invisibile — nessun errore, solo punteggi sbagliati.

**Si guarda la categoria Unicode, non un elenco di caratteri.** Un elenco ASCII
dimentica `«» “” ‘’ — … ¿`, che nei testi reali ci sono eccome; le categorie
`P*` li coprono tutte per costruzione. I **simboli** (categoria `S`) restano,
così `C++` non diventa `c`.

**Perché non spezzare su ogni non-parola.** L'alternativa era
`re.findall(r"\w+", …)`. Misurata su testo reale, fa anche altro: manda in
pezzi `info@esempio.it` (tre token), `3,14` (due) e `COVID-19`, e riempie
l'indice di frammenti — `l`, `dell`, `un`, `s` — che **gonfiano la lunghezza
dei documenti**, cioè proprio la grandezza su cui BM25 normalizza. Una
correzione mirata al difetto dichiarato è meno rischiosa di una che ne cambia
altri quattro senza averli analizzati. L'elisione italiana (`l'azienda` che non
incontra `azienda`) resta aperta come **I15**, con la misura già fatta.

**Un limite noto, trovato misurando e non ipotizzando.** Avevo scritto un test
che dava `tokenize("C#") == ["c#"]`. Sbagliato: `#` è categoria `Po`, quindi
diventa `["c"]`. Non è stata aggiunta un'eccezione a mano — la prima ne chiama
altre — perché il danno è di **precisione, non di recall**: corpus e query
passano per la stessa funzione, quindi `C#` continua a trovare `C#`. Il test
registra il fatto invece di nasconderlo.

**Verificato, e con una precisazione sull'entità dell'effetto.** Sui chunk di
un sito di prova con titoli in forma di domanda, il punteggio del chunk che
risponde alla domanda sale sempre:

| query | chunk | prima | dopo |
|---|---|---|---|
| come funziona | *Come funziona?* | 1,2842 | 3,0805 (+140%) |
| chi siamo | *Chi siamo?* | 2,8482 | 3,3932 (+19%) |
| quali servizi offre | *Quali servizi offre?* | 3,9117 | 5,8676 (+50%) |

Su quel sito l'11% dei token dell'indice portava punteggiatura attaccata.

**Se il vincitore cambi dipende però dal corpus, e va detto invece di
generalizzare.** L'inversione di classifica è stata riprodotta su un corpus
plausibile (con un chunk *Dove siamo* breve che conteneva `"come"`), mentre sui
chunk reali del sito di prova il primo posto non cambia: lì i chunk concorrenti
sono più lunghi e la normalizzazione BM25 li penalizza già. Il referto finale
di quel sito è quindi **identico**, anche perché il consenso Top-3 confronta
*insiemi* e non ordini. La correzione è certa; la sua visibilità nel referto
no, e prometterla sarebbe falsa precisione.

**La prova che conta: reintrodurre il difetto.** Sette mutazioni, tutte
rilevate:

```
1. corpus di nuovo con split() nudo      ->  1 fallito
2. query di nuovo con split() nudo       ->  1 fallito
3. tokenize non toglie piu' nulla        -> 13 falliti
4. si spoglia solo la coda, non la testa ->  4 falliti
5. si spoglia solo la testa, non la coda -> 11 falliti
6. token vuoti non filtrati              ->  3 falliti
7. si spogliano anche i simboli          ->  1 fallito
```

**Due mutazioni alla prima esecuzione non venivano rilevate.** La settima era
una mutazione mal costruita da parte mia — toccava solo uno dei due cicli — ed
è servita a ricordare che anche le mutazioni vanno verificate. La seconda è più
istruttiva: il test sul lato query **passava vacuamente**. Con la query non
tokenizzata nessun termine matcha, tutti i punteggi sono zero e `sorted()`
restituisce l'ordine naturale — che per caso metteva primo proprio il chunk
atteso. È esattamente il difetto annotato in **R23**, incontrato dal vivo. Il
test mette ora il bersaglio in **seconda** posizione, così un rango a
informazione zero non può passare per una classifica.

È la quarta voce di fila in cui la batteria di mutazioni scopre un test che
sembrava corretto.

- [x] `tokenize()` in `mars_core`, condivisa fra corpus e query.
- [x] Punteggiatura per categoria Unicode, simboli preservati.
- [x] Scelta della granularità motivata da una misura, non da un'impressione.
- [x] Limite su `#` registrato invece che nascosto.

### Referto HTML nello stile di Lighthouse (2026-08-20)
Richiesta dell'autore: rendere il referto simile a quello di Lighthouse,
estendendolo alle aree di MARS. La vista HTML è stata rifatta; **testo e JSON
non sono stati toccati**, e la struttura canonica di `build_report()` nemmeno —
è il principio di **C4**, il dato prima della presentazione, che qui si paga da
solo: cambiare l'aspetto ha significato riscrivere un solo renderer.

**Cosa c'è ora.** Una fascia di **quadranti circolari** in testa, la firma
visiva di Lighthouse, uno per area; la sua **scala di colori** (0-49 rosso,
50-89 arancio, 90-100 verde) con la legenda dichiarata; una scheda per area con
i rilievi elencati sotto; poi le sezioni che Lighthouse non ha — **Simulazione
RRF** con consenso aggregato e tabella per query, **Profili di citabilità IA**
col disclaimer sotto i numeri, **Giudizio LLM**, e **Cosa non è stato
guardato**.

**I quadranti sono SVG calcolato in Python**, con l'arco ottenuto da
`stroke-dasharray` sulla circonferenza. Nessuno script, nessuna libreria:
il referto resta un file solo, apribile fra due anni da un archivio senza rete.
È anche la prova che l'SVG inline basta, che **I9** dava per assunto.

**Tre scelte di onestà, che sono la ragione per cui non basta copiare
Lighthouse.**

1. **Un'area non misurata non è un'area che ha preso zero.** Un valore assente
   disegna un anello **tratteggiato** con un trattino al centro, non un
   quadrante a zero. È la distinzione introdotta da **R4** portata in forma
   grafica.
2. **Zero non disegna alcun arco.** Con `stroke-linecap` arrotondato un valore
   di zero lasciava comunque un **puntino colorato** — visibile nella prima
   resa fotografata — che si legge come «poco» invece che come «niente».
   Trovato guardando lo screenshot, non leggendo il codice.
3. **Lessicale e Semantica non ricevono un voto finto.** Producono classifiche,
   non punteggi: le loro schede dicono *«classifica BM25, non un voto»* e al
   loro posto la fascia mostra i due segnali **derivati** che C1 già calcola —
   consenso RRF e contenuto in forma di risposta — etichettati come tali.

**La scala cambia significato, e va detto.** MARS usava 80/50, Lighthouse usa
90/50: lo stesso punteggio può ora avere un colore diverso rispetto a un
referto generato prima. Il numero non cambia, la convenzione sì, ed è
dichiarata nella legenda proprio perché il colore non venga letto come una
misura.

**Verificato guardando, non deducendo.** Il referto è stato generato su un
sito di prova reale — con Lighthouse davvero eseguito, axe-core davvero
eseguito — e **fotografato con Playwright** in tema chiaro e scuro, poi
ispezionato. È così che sono emersi il puntino dello zero e alcuni testi
rimasti con gli apostrofi ASCII (`piu'`, `perche'`) dove il resto della pagina
usa gli accenti veri. Fotografato anche il caso **degradato** — Lighthouse
assente, nessuna pagina per axe, ZAP assente — perché è lì che si vede se la
distinzione «non misurato» regge.

**Le invarianti di onestà sono protette da test, verificati per mutazione:**

```
1. "non misurato" disegnato come uno zero          -> 8 falliti
2. soglie riportate a quelle vecchie (80/50)       -> 1 fallito
3. zero disegna comunque un arco (puntino spurio)  -> 1 fallito
4. lessicale e semantica con un voto finto (0/100) -> 1 fallito
```

I test preesistenti su autoconsistenza, tema scuro ed escape del markup ostile
sono rimasti verdi senza modifiche: erano scritti sul comportamento e non
sull'aspetto, e hanno retto a un rifacimento completo della vista.

**Chiude metà di R21.** La vista HTML mostra ora `tool` per **ogni** area, non
più solo per la WCAG, quindi la sicurezza dichiara `HTTP-Headers` o
`ZAP (attiva)`. Ma `status` continua a non comparire: un `surface` a 100/100 si
legge ancora come un WAPT completo. R21 resta aperta, ridotta a metà, e lo dice.

### R19 — ✅ RISOLTO (2026-08-20): i segnali di pagina gonfiavano `answer_shaped_ratio`
`question_signals()` riceveva l'intera **pagina** e veniva chiamata per **ogni
chunk**. Due dei quattro segnali erano però proprietà della pagina, non del
passaggio: *«titolo interrogativo»* si accendeva se una **qualunque**
intestazione della pagina era una domanda, e *«FAQPage JSON-LD»* se il marcatore
compariva **ovunque** nell'HTML. Una sola FAQ marcava quindi answer-shaped ogni
chunk della pagina.

Non è un dettaglio interno: `answer_shaped_ratio` alimenta il segnale
*Contenuto in forma di risposta* di **C1**, che pesa 3 su 3 per ogni assistente.
Un numero gonfiato lì si propaga fino all'indice composito.

**Riprodotto** su una pagina con quattro sezioni di cui **una sola** è una
domanda:

```
answer_shaped_ratio : 1.00        (l'onesto e' 0.25)
segnali             : {'titolo interrogativo': 4, ...}
C1 "Contenuto in forma di risposta" : 100.0
indice composito                    :  85.7
```

Quattro chunk su quattro con il segnale del titolo, quando i titoli
interrogativi erano uno.

**Risoluzione applicata: i segnali si dividono per ambito.**

- `question_signals(testo, heading, lingua)` guarda **solo questo passaggio**, e
  il titolo che considera è quello del **chunk** — non quelli delle altre
  sezioni.
- `page_signals(pagina, lingua)` raccoglie ciò che riguarda la pagina. Restano
  nel referto perché dicono qualcosa di vero — una pagina che si dichiara
  FAQPage sta dichiarando la propria forma — ma **non entrano nel rapporto**,
  che è una frazione di chunk. Contarli lì significava moltiplicare un fatto di
  pagina per il numero dei suoi pezzi.

I segnali di pagina si contano ora **in pagine** (`page_signals`, `n_pages`) e
si calcolano **una volta per pagina**. Effetto collaterale gradito: prima
`"faqpage" in html.lower()` girava per ogni chunk, cioè una copia in minuscolo
dell'intero HTML per ciascun pezzo della stessa pagina.

Il fatto non si perde di vista: `/audit/semantic` espone `page_signals`, e la
scheda Semantica del referto lo dichiara come *«FAQPage JSON-LD: 1 pagine su
1»*, separato dal rapporto.

**Una scelta di R9 conservata deliberatamente.** L'heading del chunk continua a
far parte del testo su cui si calcolano gli altri due segnali: *«Come
funziona?»* come titolo vale quanto la stessa frase nel corpo. Senza, un chunk
la cui unica domanda sta nel titolo perderebbe due segnali su tre — e la
mutazione che lo toglie oggi fa fallire un test apposta.

**Verificato end-to-end** su un sito con quattro sezioni, una sola domanda e uno
schema FAQPage:

```
prima : 4. Semantica : Analizzato (100% di 4 chunk answer-shaped)   composito 85,5
dopo  : 4. Semantica : Analizzato ( 25% di 4 chunk answer-shaped)   composito 70,0
```

Quindici punti e mezzo di gonfiaggio tolti dall'indice composito.

**La prova che conta: reintrodurre il difetto.** Quattro mutazioni, tutte
rilevate:

```
1. il titolo di QUALUNQUE sezione riaccende il segnale -> 4 falliti
2. FAQPage torna a contare come segnale di chunk       -> 1 fallito
3. segnali di pagina contati per chunk                 -> 1 fallito
4. l'heading del chunk non entra nei segnali testuali  -> 1 fallito
```

La quarta alla prima esecuzione **non veniva rilevata**: nessun test verificava
che l'heading del chunk alimentasse anche i segnali testuali, quindi la scelta
di R9 sarebbe potuta sparire senza rumore. Aggiunto il test che la fissa.

**Un test di R9 codificava il difetto, ed è stato riscritto.**
`test_semantic_segnali_strutturali` verificava che l'heading di *un'altra*
sezione accendesse il segnale: era esattamente R19, scritto come se fosse la
funzione voluta. I segnali strutturali di R9 restano giusti come **segnali**;
era sbagliata la loro **attribuzione**.

**Una seconda causa di gonfiaggio, trovata misurando e NON corretta qui.** Con
R19 chiusa, la pagina di prova originale dava 0,50 invece dell'atteso 0,25: il
titolo `Chi siamo` accende «titolo interrogativo» pur non essendo una domanda.
Vale per un'intera classe di intestazioni standard — `Dove siamo`, `Come
raggiungerci`, `Cosa facciamo`, `How it works`. È un difetto **diverso** da
R19, aperto come **R34** con la misura già fatta: mescolarlo qui avrebbe
confuso due cose e reso la batteria di mutazioni illeggibile.

- [x] Segnali di chunk separati da quelli di pagina.
- [x] «titolo interrogativo» dal titolo del chunk, non della pagina.
- [x] FAQPage contato in pagine, esposto nell'API e nel referto.
- [x] Segnali di pagina calcolati una volta per pagina.

### R20 — ✅ RISOLTO (2026-08-20): axe fabbricava un 100/100, e la suite lanciava Chromium
Due difetti che si tenevano in piedi a vicenda: il prodotto produceva un
punteggio inventato, e il banco di prova era costruito in modo da non poterlo
vedere.

**Il prodotto.** `run_axe()` inghiottiva ogni fallimento per-URL con
`except Exception: continue` **senza contare le pagine davvero analizzate**. Con
tutte le pagine irraggiungibili restituiva quindi una lista **vuota**, che
`audit()` — guardando solo `if violazioni is not None` — leggeva come «nessuna
violazione trovata». Riprodotto:

```
pagine irraggiungibili -> tool=axe-core  score=100  pages_tested=1
run_axe(...)           -> []
```

Un sito mai caricato veniva pubblicato come **accessibile al 100%, misurato con
axe-core**, con `pages_tested` pari agli URL **tentati**. È il difetto peggiore
della famiglia che R4 aveva aperto: non un'assenza dichiarata, ma una misura
inventata che si presenta come la migliore possibile.

**Il banco di prova.** `conftest.py` dichiarava *«Nessun test avvia Lighthouse,
ZAP o un browser»*, e il README ripeteva che i test *«non avviano Lighthouse,
ZAP o un browser»*. **Erano affermazioni false.** Misurato con `strace` sulla
sola porzione WCAG della suite:

```
browser lanciati: 15   (~/.cache/ms-playwright/.../chrome-headless-shell)
```

La fixture `niente_rete` copre `requests`, ma **Playwright non passa da
requests**. E poiché nei test le navigazioni fallivano tutte, la suite
esercitava proprio il 100/100 fabbricato — passando verde. Nessun test fissava
quale dei due rami di `audit()` venisse eseguito, quindi il risultato dipendeva
dalla macchina: con Playwright installato girava axe, senza girava il markup.

**Risoluzione applicata.**

- `run_axe()` conta le pagine riuscite e restituisce `(violazioni, analizzate)`,
  oppure **`None`** se non ne ha analizzata nemmeno una — così `audit()` ripiega
  sull'euristica statica e lo dichiara (`tool: markup`, `status: surface`),
  invece di spacciare il vuoto per un sito perfetto.
- `pages_tested` riporta ora le pagine **esaminate**, non quelle tentate, e
  accanto compaiono `pages_attempted` e `complete`.
- Una scansione **parziale è dichiarata** in testa ai rilievi, con la stessa
  regola applicata alle scansioni ZAP interrotte in **C9**.
- La **diffusione** di una regola si calcola sulle pagine viste: una regola
  presente su tutte le pagine esaminate è diffusa al 100%, anche se il campione
  tentato era più grande.
- `conftest.py` rende `playwright.sync_api` non importabile. Si agisce sulla
  libreria e non su `mars_wcag` perché così la neutralizzazione **non dipende da
  quale oggetto-modulo sia vivo** — import diretto nei test o
  `load_external_module` — e copre entrambe le porte d'ingresso:
  `axe_disponibile()` e `run_axe()` degradano tutte e due.

**Verificato.**

```
browser lanciati dalla suite intera : 0      (erano 15 nella sola parte WCAG)
durata della suite                  : 6,4 s  (erano 8,1)
pagine irraggiungibili              : tool=markup, status=surface
```

Le due dichiarazioni di `conftest.py` e del README sono tornate vere senza
doverle riscrivere.

**Il percorso axe reale non è stato rotto**, ed è la verifica che contava di
più: audit su un sito locale costruito inaccessibile → `tool=axe-core`,
`score=0`, `complete=True`, con `color-contrast` fra i rilievi — un criterio che
solo un browser vero può vedere. Con una pagina irraggiungibile mescolata a una
buona: **1 pagina analizzata su 2 tentate**, contata giusta.

**La prova che conta: reintrodurre il difetto.** Sei mutazioni, tutte rilevate:

```
1. zero pagine analizzate torna a valere []      -> 1 fallito
2. i successi non vengono contati                -> 1 fallito
3. pages_tested torna a essere le pagine TENTATE -> 1 fallito
4. scansione parziale non dichiarata             -> 1 fallito
5. diffusione calcolata sulle pagine tentate     -> 1 fallito
6. il browser torna a non essere neutralizzato   -> 1 fallito
```

**Alla prima esecuzione le prime due — cioè il cuore di R20 — non venivano
rilevate**, e la ragione è la stessa di sempre in forma nuova: i test iniettavano
`run_axe` dall'esterno, quindi provavano `audit()` ma lasciavano il **corpo** di
`run_axe` mai eseguito. Il conteggio delle pagine, che *è* il difetto, non era
sotto test.

Colmato con un **finto Playwright** — pagina, browser e context manager — che
fa fallire davvero la navigazione sugli URL indicati. È lo stesso schema del
finto daemon ZAP di **C9**, con la stessa avvertenza incisa sopra: un banco di
prova troppo accomodante conferma anche ciò che è sbagliato. La quinta mutazione
è sfuggita per un motivo diverso ma affine: avevo scritto in un commento che la
diffusione si misura sulle pagine viste, senza un test che lo difendesse.

- [x] Contare le pagine analizzate; `None` se sono zero.
- [x] `pages_tested` veritiero, parzialità dichiarata.
- [x] Browser neutralizzato nella suite, sulla libreria e non sul modulo.
- [x] Un test per **ciascun** ramo, reso deterministico.
- [x] Corpo di `run_axe` sotto test con un finto Playwright.

### R21 — ✅ RISOLTO (2026-08-20): «di superficie» era indistinguibile da una misura piena
Le viste umane mostravano `tool` — e mai `status` — **solo** dove esisteva un
`wcag_level`, cioè per la sola accessibilità. Il dato canonico lo conteneva già,
quindi il JSON era onesto e le due viste che le persone leggono no.

**Riprodotto.** Due sicurezze con lo stesso numero e due significati opposti:

```
vista TESTO
  solo header HTTP      -> 7. Sicurezza         : 100/100
  scansione ZAP attiva  -> 7. Sicurezza         : 100/100
```

Stringhe **identiche**. In HTML cambiava il solo nome dello strumento, e la
parola «superficie» non compariva da nessuna parte: il quadrante era verde in
entrambi i casi. Chi non sa che *HTTP-Headers* significa «abbiamo guardato tre
intestazioni» leggeva un sito perfettamente sicuro.

È il difetto più grave della famiglia aperta da **R4**, perché non riguarda un
modulo ma il punto in cui tutto il lavoro di onestà metodologica arriva al
lettore. `mars_wapt` distingueva già `surface` dal resto, `mars_wcag` pure, C9
aveva introdotto `complete: False` per le scansioni interrotte — e le viste
buttavano via tutto.

**Risoluzione applicata.** `_qualificatori(area)` produce, per **ogni** area con
un punteggio, con che cosa è stato ottenuto: strumento, livello, profondità
(`controllo di superficie`), completezza (`scansione parziale`) e campione
(`N pagine esaminate`). È **condivisa fra le due viste**, così testo e HTML non
possono tornare a dire cose diverse — che è esattamente com'era nato il difetto.

`build_report()` porta ora anche `complete` nel dato d'area: le viste possono
dirlo perché il dato lo contiene, e se sparisce da lì sparisce da entrambe
insieme (c'è una mutazione che lo verifica).

**Nel referto HTML la qualifica è anche visiva.** La nota sotto il quadrante
diventa `HTTP-Headers · superficie` **in arancio**, contro il grigio di
`axe-core`: un 100 verde ottenuto guardando tre header non può più leggersi come
un successo pieno. Verificato guardando lo screenshot della fascia.

**Un'imprecisione trovata rileggendo l'output.** Avevo aggiunto la qualifica
anche all'`aria-label` del quadrante, ma su una scansione soltanto *interrotta*
diceva «controllo di superficie» — che è un'altra cosa. Tolta: la nota è un
fratello nel DOM e viene letta subito dopo, quindi ripeterla la duplicava e
sbagliarla era peggio che ometterla.

**Verificato end-to-end**, su un sito reale senza daemon ZAP:

```
6. Accessibilità     :  50/100
  axe-core · WCAG 2.1 A + AA · 2 pagine esaminate
7. Sicurezza         :  60/100
  HTTP-Headers · controllo di superficie
```

Due affermazioni del README sono tornate vere senza riscriverle: *«viene
dichiarato come controllo di superficie»* e *«se la scansione va in timeout, i
rilievi parziali vengono riportati come tali»* valevano finora solo nel JSON.

**La prova che conta: reintrodurre il difetto.** Cinque mutazioni, tutte
rilevate:

```
1. "surface" non piu' annotato                  -> 1 fallito
2. scansione parziale non piu' annotata         -> 1 fallito
3. la vista testo torna a tacere lo strumento   -> 3 falliti
4. "complete" non entra nel dato canonico       -> 2 falliti
5. il quadrante di superficie non piu' marcato  -> 1 fallito
```

I test girano **su entrambe le viste** con lo stesso `parametrize`: la prova
centrale è che il referto di un controllo di superficie e quello di un WAPT
completo non possano essere la stessa stringa.

**Con R21 si chiude l'ultima voce GRAVE** della revisione del 2026-08-20: delle
sette aperte quella mattina (R15-R21) non ne resta nessuna.

- [x] `status` e `tool` dichiarati in entrambe le viste, per ogni area.
- [x] `complete` nel dato canonico e nelle viste.
- [x] Qualifica visiva nel quadrante, non solo testuale.
- [x] Un solo `_qualificatori()` per testo e HTML.

### R22 — ✅ RISOLTO (2026-08-20): l'esecutore di moduli non reggeva i plugin che rompono
Tre difetti della stessa famiglia: il contratto `audit(context) -> dict` era
scritto ma non difeso, e chi lo violava faceva danni sproporzionati.

**1. Un modulo che solleva spariva dal referto CLI.** L'eccezione veniva solo
stampata; l'area non entrava in `results`, e `build_report` — che salta ciò che
non trova — non la nominava affatto. Riprodotto:

```
[✓] 1. Tecnica (mars_tech.py)
  Errore esecuzione audit: il plugin e' rotto
           MARS BEACON - REPORT FINALE
  (nessuna riga "1. Tecnica" nel referto)   exit code: 0
```

Con `--output` il file consegnato non portava alcuna traccia dell'area persa, e
chi lo legge non poteva sapere di averla persa. L'API faceva già la cosa giusta
— registra `{"error": ...}` in `results` — quindi le due interfacce si
comportavano in modo diverso davanti allo stesso guasto.

**2. Un plugin che non restituisce un `dict` faceva crollare il referto.**
`res.get("score")` su un `None` — il `return` dimenticato, l'errore più comune
che si possa fare scrivendo un plugin — sollevava `AttributeError` **dopo che
tutti i moduli erano girati**: l'audit intero perso, con un messaggio
incomprensibile e un codice di uscita fuori dal contratto documentato. Via API
gli endpoint singoli, che non hanno il `try/except` di `/audit/full`,
rispondevano **500**.

**3. `mars_seo` non reggeva uno score SEO `null`.** Lo schema LHR lo ammette: il
run riesce, il JSON è valido, ma la categoria non è calcolabile. `None * 100`
sollevava `TypeError`, che non era nella tupla dell'`except` e propagava fuori
da `audit()`.

**Risoluzione applicata.** `normalizza_risultato()` e `errore_modulo()` vivono
in `mars_core` — CLI e API caricano gli stessi plugin, quindi la difesa del
contratto appartiene lì (principio 4). Un risultato non conforme diventa
`{"error": ...}`; `build_report()` lo traduce in un'area con
`status: "error"` e **il motivo fra i rilievi**, perché «non misurato» senza il
perché è un'informazione dimezzata.

La CLI registra ora l'esito **sempre**, fallimento incluso, allineandosi
all'API; `run_single_audit` normalizza a sua volta, così un plugin distratto non
produce più un 500.

Per `mars_seo` la diagnosi è **specifica**, applicando la lezione di **R6**
(vuoto ≠ malformato): non *«Lighthouse non riuscito»* — che sarebbe falso,
Lighthouse ha funzionato — ma *«Lighthouse non ha calcolato la categoria SEO per
questa pagina»*, con `score: None` e `status: "unavailable"`. `TypeError` è
comunque entrato nell'`except` come rete.

**Verificato.** Le tre riproduzioni ripetute:

```
modulo che solleva   -> 1. Tecnica : errore del modulo
                        ⚠ ValueError: il plugin e' rotto
ritorno None         -> status=error, "mars_tech ha restituito NoneType invece di un dict"
Lighthouse score null-> {'score': None, 'status': 'unavailable',
                         'issues': ['Lighthouse non ha calcolato la categoria SEO...']}
POST /audit/tech     -> 200 (era 500)
```

Un modulo rotto **non ferma gli altri**: c'è un test che lo prova con un plugin
guasto accanto a uno sano. E l'audit reale su un sito di prova è invariato.

**La prova che conta: reintrodurre il difetto.** Sette mutazioni, tutte
rilevate:

```
1. non-dict non normalizzato nel referto      -> 4 falliti
2. il normalizzatore accetta qualunque cosa   -> 6 falliti
3. la CLI torna a non registrare l'errore     -> 2 falliti
4. l'errore non diventa status/issue          -> 9 falliti
5. mars_seo non guarda lo score null          -> 1 fallito
6. API: run_single_audit non normalizza       -> 1 fallito
7. la CLI non registra il modulo senza audit()-> 1 fallito
```

**Le mutazioni 3 e 6 alla prima esecuzione non venivano rilevate**, ed è sempre
lo stesso punto cieco in forma nuova: avevo testato `build_report`, cioè il
*consumatore*, ma nessun test esercitava i due **punti d'integrazione** —
`run_audit()` della CLI e `run_single_audit()` dell'API. Colmato con test
diretti su entrambi, che è anche il primo test di `run_audit` esistente.

**Un fallimento di test utile.** L'asserzione sul referto HTML cercava `il
plugin e' rotto` e falliva: in HTML l'apostrofo esce come `&#x27;`, cioè
l'escape funziona. Era il test a essere ingenuo, non il codice.

- [x] La CLI registra l'esito sempre, come l'API.
- [x] Contratto difeso in `mars_core`, per entrambe le interfacce.
- [x] L'area fallita compare nel referto, col motivo.
- [x] `mars_seo` distingue «non calcolato» da «non riuscito».

### La sezione SEO riporta i controlli di Lighthouse (2026-08-20)
Richiesta dell'autore, con un referto PageSpeed Insights reale come
riferimento: *«facciamo in modo che la nostra sezione del referto contenga gli
stessi dati»*.

**La fonte è stata verificata, non ricostruita a memoria.** La pagina di
PageSpeed è un'applicazione JavaScript e restituisce solo il guscio a chi la
scarica, quindi non serviva. Al suo posto è stato eseguito **Lighthouse in
locale sullo stesso URL** — che è la fonte migliore, perché è lo stesso
strumento e la stessa versione (13.4.1) che `mars_seo` invoca. Da lì la
struttura esatta: la categoria SEO ha **11 audit**, dieci binari e uno manuale
(`structured-data`).

Serviva anche la forma di un audit **fallito**, che quella pagina non offre
perché li supera tutti: ottenuta eseguendo Lighthouse contro una pagina locale
costruita carente. I dettagli arrivano in forme diverse a seconda dell'audit —
`is-crawlable` porta una `source` testuale, `image-alt` un `node` del DOM,
`meta-description` nessun dettaglio — e i test usano **quelle** forme, osservate,
non forme immaginate.

**Cosa c'è ora.** `mars_seo` non restituisce più il solo punteggio: riporta
tutti gli audit della categoria con esito, titolo e **elementi incriminati**
(selettore o sorgente). Il referto li mostra come li mostra Lighthouse —
falliti per primi, poi i manuali, infine i superati — con la versione dello
strumento e il tipo di dispositivo.

**I superati si elencano, e non è ridondanza.** Senza, non si sa *che cosa* sia
stato guardato, e un punteggio pieno resta indistinguibile da un controllo mai
eseguito: è la stessa distinzione di **R21**, applicata al dettaglio invece che
all'area.

**I titoli li traduce Lighthouse.** `--locale=it` li restituisce già in
italiano, quindi restano allineati allo strumento invece di essere una nostra
traduzione destinata a invecchiare. Rispetta il principio 6 senza inventare
nulla.

**Il tipo di dispositivo è dichiarato.** Lighthouse misura `mobile` di
predefinito, mentre il referto PageSpeed di riferimento era `desktop`: sono
due misure non confrontabili, e il referto lo dice invece di tacerlo. Sceglierlo
è l'idea **I16**.

**Verificato sul sito indicato**, con un audit MARS reale:

```
2. SEO               : 100/100
  Lighthouse 13.4.1 · mobile · 10 controlli superati, 0 falliti
  ⚠ [Lighthouse] da verificare a mano: Dati strutturati validi
```

Nel referto HTML compaiono tutti e undici i controlli, in italiano, con lo
stesso punteggio della sezione SEO di PageSpeed. Verificato anche guardando lo
screenshot, dove è emerso un difetto invisibile nel codice: la classe CSS `ok`
usata per i controlli superati **collide con la classe globale `.ok`**, che
colora l'intera riga — tutte le voci superate risultavano verdi invece del solo
segno di spunta. Rinominate in `superato` / `fallito`.

**Una guardia dichiarata come tale.** `passed` esclude gli audit manuali
(`bool(punteggio) and not manuale`). Misurato su tre referti reali: gli audit
manuali e non applicabili hanno **sempre** `score: None`, quindi oggi la
clausola non cambia nulla. Resta perché superato, fallito e manuale devono
partizionare l'elenco, e c'è un test che lo fissa — con il commento che dice
che è una difesa, non una differenza.

**La prova che conta: reintrodurre il difetto.** Sette mutazioni, tutte
rilevate:

```
1. si estraggono solo i falliti          -> 3 falliti
2. gli elementi incriminati non riportati -> 4 falliti
3. i manuali contati come superati       -> 3 falliti
4. niente --locale=it                    -> 1 fallito
5. il form factor non si dichiara        -> 1 fallito
6. i controlli non arrivano al referto   -> 5 falliti
7. i falliti non stanno per primi        -> 1 fallito
```

**Tre non venivano rilevate alla prima esecuzione, per due ragioni diverse.**
Due mutazioni erano **mal costruite da me** — una era un no-op (`[] or [...]`
vale `[...]`), l'altra non discriminava perché gli audit manuali hanno score
`None`. La terza ha scoperto un test **vacuo**: i falliti stavano già per primi
nel dato di prova, quindi l'ordinamento non veniva esercitato. Ora il dato di
prova è deliberatamente in ordine sbagliato.

E, per la seconda volta, un'asserzione è caduta su un apostrofo reso come
`&#x27;`: l'escape funziona, era il test a essere ingenuo.

### R23 — ✅ RISOLTO (2026-08-20): query perse, e ranghi a informazione zero
Due difetti attorno alla simulazione RRF, il cuore dichiarato del progetto.

**1. Un rango a informazione zero veniva presentato come una classifica — anzi,
come la classifica migliore possibile.** Quando nessun termine della query
trova riscontro, i punteggi sono tutti zero e `sorted()` restituisce l'**ordine
naturale** dei chunk, cioè l'ordine di scansione. I due recuperatori
restituivano quindi lo stesso ordine, che coincide con se stesso:

```
rango lessicale  : [0, 1, 2]      rango vettoriale : [0, 1, 2]
CONSENSO riportato: 3/3           <- su una domanda senza un solo riscontro
```

**3/3 è il risultato migliore possibile.** E si propagava: il rango entrava
nella fusione aggregata, e il segnale *Recuperabilità ibrida* di **C1** —
che pesa 2 o 3 su 3 per ogni assistente — leggeva **100.0**. È lo stesso
difetto incontrato dal vivo chiudendo **R18**, dove un test passava
vacuamente proprio perché l'ordine naturale metteva per caso il chunk atteso
in testa.

**2. Le query non sopravvivevano alla caduta di un retriever.** Vivevano solo
dentro `rrf_simulation`, che è vuota se anche uno solo dei due non ha prodotto
`per_query`. In quel caso `mars_citations --from-audit` usciva con *«Nessuna
query nel referto»* — benché `load_queries` sapesse già leggere una chiave
`queries` di primo livello, che però nessuno scriveva.

**Risoluzione applicata.** I due retriever dichiarano ora, per ogni query, se
hanno trovato **qualcosa** (`matched`), e senza riscontro non dichiarano alcun
`top_chunk`: non c'è un vincitore da nominare. Le classifiche a vuoto sono
**escluse dalla fusione aggregata**, perché fondere un ordine di scansione con
una classifica vera sposta il risultato senza dire nulla sul sito.

Nel referto, il consenso di una query senza riscontro **non è zero: è non
misurabile**, e vale la stessa distinzione di R4 e R21. *«nessun riscontro»* e
*«0/3»* dicono cose diverse — la prima che la domanda non ha trovato nulla, la
seconda che i due recuperatori hanno trovato cose diverse — e confonderle
nascondeva proprio il caso peggiore. Le query stanno ora anche al primo livello
del referto, così il contratto con `--from-audit` non dipende più
dall'essere sopravvissuti entrambi i recuperatori.

**Verificato**, su un sito di prova con le query generiche:

```
prima : cos'è questo sito 2/3 · come funziona 2/3 · chi siamo 3/3 · quali servizi 3/3
dopo  : cos'è questo sito nessun riscontro · come funziona nessun riscontro
        chi siamo 3/3 · quali servizi nessun riscontro
```

Tre numeri fabbricati spariti; l'unico che restava era l'unico misurato.
L'indice composito non cambia (62,1), perché il rango aggregato conserva la
query che ha funzionato: la correzione toglie le invenzioni senza impoverire
ciò che era misurato. E la catena `--format json` → `--from-audit` funziona
ora anche con un retriever caduto.

**Un'ipotesi mia, smentita dalla misura.** Vedendo tre query su quattro
dichiarare «nessun riscontro» ho supposto che la colpa fosse del recuperatore
**vettoriale**. Misurato: è il **lessicale** a non trovare nulla, mentre il
vettoriale matcha tutto. La ragione è che `matched` significa cose diverse per
i due: per BM25 vuol dire *«un termine della query compare nel corpus»*, un
segnale forte; per il proxy char-TFIDF vuol dire *«qualche trigramma si
sovrappone»*, che fra due testi nella stessa lingua è quasi sempre vero. La
guardia coglie quindi il caso patologico — quello che produceva il 3/3 finto —
ma sul lato vettoriale scatterà di rado, e va detto invece di lasciar credere
il contrario.

**Un difetto nuovo, trovato mentre si indagava quell'ipotesi.** `mars_lexical`
indicizza **heading + testo**, `mars_semantic` il **solo testo**: i due
recuperatori ordinano le stesse unità partendo da contenuti diversi. R10 aveva
lavorato perché i ranghi si riferissero alle stesse **unità**; nessuno aveva
controllato che leggessero lo stesso **contenuto**. Aperto come **R35** con la
misura già fatta, non corretto qui.

**La prova che conta: reintrodurre il difetto.** Sette mutazioni, tutte
rilevate al primo tentativo:

```
1. lessicale: tutto considerato trovato           -> 2 falliti
2. vettoriale: tutto considerato trovato          -> 2 falliti
3. le query a vuoto rientrano nel rango aggregato -> 1 fallito
4. il consenso torna a essere sempre misurabile   -> 4 falliti
5. il flag matched non viene letto dal referto    -> 4 falliti
6. le query non stanno piu' al primo livello      -> 1 fallito
7. top_chunk dichiarato anche senza riscontro     -> 1 fallito
```

C'è anche un test che fissa la **lettura compatibile**: una voce `per_query`
senza il flag `matched` viene considerata misurata, così un modulo esterno
scritto prima di questa modifica continua a funzionare.

- [x] `matched` dichiarato da entrambi i retriever.
- [x] Classifiche a vuoto fuori dalla fusione aggregata.
- [x] Consenso non misurabile distinto da consenso zero.
- [x] `queries` al primo livello del referto.

### R24 — ✅ RISOLTO (2026-08-20): tre casi limite del crawler sugli URL
Tre difetti indipendenti, tutti nella gestione degli URL, tutti silenziosi.

**1. Gli host IPv6 letterali venivano corrotti — e il filtro same-host con
loro.** `norm_host()` tagliava sul primo `:`, che in un IPv6 non è il
separatore della porta ma parte dell'indirizzo; `normalize_url()` usava
`parts.hostname`, che toglie le parentesi quadre:

```
normalize_url("http://[2001:db8::1]/x") = 'http://2001:db8::1/x'   <- non e' un URL
norm_host    ("http://[2001:db8::1]/x") = '[2001'
host_matches fra due IPv6 DIVERSI       = True                     <- !
```

L'ultima riga è la più seria: due indirizzi diversi si riducevano alla stessa
stringa, quindi il filtro same-host costruito da **R7** e rafforzato da **R17**
lasciava passare un altro server. E un sito servito su IPv6 falliva ogni
richiesta, venendo diagnosticato *irraggiungibile* pur rispondendo.

**2. Le sitemap con `<loc>` relativi producevano zero pagine, con il motivo
sbagliato.** Lo standard li vuole assoluti, ma le sitemap reali ne hanno di
relativi. Presi alla lettera, `host_matches` li bocciava:

```
skipped: ['host esterno: /pagina1.html', 'host esterno: pagina2.html']
```

*«Host esterno»* è falso — è esattamente lo stesso host — e l'audit restava
senza una pagina.

**3. Un robots.txt vuoto veniva riportato come assente.** `found` si deduceva
dal **contenuto** (`bool(righe)`), non dallo status: un file servito a 200 ma
vuoto significa *«tutto permesso»*, ed è una scelta esplicita del sito.
`mars_tech` ne faceva un rilievo di gravità **media** (*«robots.txt assente»*),
cioè un difetto che non c'era.

**Risoluzione applicata.** `norm_host()` riconosce il letterale fra parentesi
quadre **prima** di tagliare sui due punti; `normalize_url()` le rimette
quando l'host ne contiene; i `<loc>` si risolvono con `urljoin` rispetto alla
sitemap che li contiene; `found` deriva dallo **status 200**, non dal
contenuto.

**Verificato, e per l'IPv6 con una prova end-to-end** — un server HTTP
in ascolto su `[::1]:8861`:

```
prima (HEAD) : NESSUNA PAGINA: il sito risulta irraggiungibile
dopo         : pagine ['http://[::1]:8861/']   titolo "IPv6"
```

Gli altri due, ripetuti:

```
sitemap relativa -> pagine ['.../pagina1.html', '.../pagina2.html'], skipped []
robots vuoto     -> found True; mars_tech passa da "assente" (medio)
                    a "nessuna regola esplicita" (lieve)
```

Su un sito senza questi casi limite il referto è **invariato**, area per area.

**La prova che conta: reintrodurre il difetto.** Cinque mutazioni, tutte
rilevate al primo tentativo:

```
1. norm_host taglia di nuovo sui due punti      -> 3 falliti
2. normalize_url perde le quadre IPv6           -> 4 falliti
3. i <loc> non sono piu' risolti sulla sitemap  -> 1 fallito
4. found torna a dedursi dal contenuto          -> 1 fallito
5. trovato non viene mai impostato              -> 3 falliti
```

C'è anche un test che fissa il **caso normale**: `urljoin` su un `<loc>` già
assoluto lo restituisce identico, così la correzione non tocca ciò che
funzionava.

- [x] IPv6 letterali preservati in `norm_host` e `normalize_url`.
- [x] Filtro same-host che distingue due IPv6 diversi.
- [x] `<loc>` relativi risolti sulla sitemap che li contiene.
- [x] `found` dallo status, non dal contenuto.

### R25 — ✅ RISOLTO (2026-08-20): la direttiva robots `none` non veniva vista
`controlla_indicizzabilita` cercava la sottostringa `noindex` dentro la
concatenazione di `meta_robots` e `x_robots_tag`. La direttiva standard `none`
— che per Google e Bing significa **esattamente** `noindex, nofollow` — non la
contiene, quindi passava inosservata.

**Riprodotto.** Un sito di una pagina, tutto uguale tranne la direttiva:

```
direttiva                       score  rilievi sull'indicizzabilita'
------------------------------------------------------------------------
meta robots: noindex               57  [critico] 1/1 pagine con 'noindex'
meta robots: none                  97  NESSUNO
meta robots: noindex,nofollow      57  [critico] 1/1 pagine con 'noindex'
meta robots: (nessuno)             97  NESSUNO
X-Robots-Tag: none                 97  NESSUNO
```

Non è che il rilievo fosse più mite: **non c'era**. `none` e "nessuna
direttiva" ricevevano lo stesso identico giudizio, 97 su 100, mentre `none` e
`noindex, nofollow` — la stessa direttiva in due scritture — ne ricevevano due
distanti 40 punti. Un sito interamente escluso dagli indici usciva dall'area 1
senza un rilievo.

**Risoluzione applicata.** Il difetto non era l'assenza di `none` dalla
stringa cercata: era cercare sottostringhe. Le direttive robots sono una lista
separata da virgole, e ora vengono lette come tale.

`direttive_robots(pagina)` unisce meta e header — hanno la stessa grammatica —
e restituisce un **insieme di token**, separando su virgole *e* spazi (il
crawler unisce con uno spazio i `content` di più `<meta>`, per esempio
`robots` e `googlebot`). Il giudizio diventa un'intersezione con due insiemi
dichiarati:

```python
DIRETTIVE_NOINDEX  = frozenset({"noindex", "none"})
DIRETTIVE_NOFOLLOW = frozenset({"nofollow", "none"})
```

Il guadagno non è aver aggiunto una parola, è che l'elenco delle direttive
riconosciute ora è **esplicito ed elencabile**: aggiungerne una è una domanda
sull'insieme, non una scommessa su una sottostringa. Ed è la forma in cui R36
si innesterà senza toccare il parser.

**`all` non compare in nessuno dei due insiemi, di proposito**, ed è annotato
nel codice perché nessuno lo "corregga": è il default esplicito, non un
rilievo, e non deve annullare nulla. Quando le direttive si contraddicono
(`all, noindex`) vince la più restrittiva — che è precisamente ciò che fa
un'intersezione.

**`nofollow` riceve un rilievo proprio, graduato.** Il TO-DO chiedeva di
valutarlo. Non nasconde la pagina: impedisce di raggiungere le altre partendo
da lì. Su una pagina sola è una scelta legittima e frequente, quindi `lieve`;
quando è la regola del sito la scoperta dipende interamente dalla sitemap,
quindi `medio`. Le due gravità sono una scelta editoriale, dichiarata nel
codice accanto alla riga che le assegna.

**Verificato.** Dopo la correzione, con lo stesso banco:

```
meta robots: noindex               57  [critico] escluse dagli indici
meta robots: none                  49  [critico] escluse dagli indici
                                       [medio]   non fanno seguire i link
meta robots: noindex,nofollow      49  [critico] + [medio]      <- identico
meta robots: nofollow              89  [medio]   non fanno seguire i link
meta robots: all                   97  NESSUNO
meta robots: (nessuno)             97  NESSUNO
X-Robots-Tag: none                 49  [critico] + [medio]
```

Le due scritture della stessa direttiva ora coincidono riga per riga. `all` e
"nessuna direttiva" restano a 97: nessun falso positivo introdotto.

**La prova che conta: reintrodurre il difetto.** Dieci mutazioni, tutte
rilevate — `none` tolto da ciascuno dei due insiemi, il separatore ridotto
alle sole virgole e ai soli spazi, l'intersezione trasformata in
sottoinsieme, la gravità del `nofollow` resa fissa, l'X-Robots-Tag ignorato,
il `.lower()` rimosso, il blocco `nofollow` zittito, e il ritorno al vecchio
confronto per sottostringa.

Due cose che la batteria ha insegnato, e che valgono oltre questa voce:

- **Il `.lower()` non era coperto da nulla.** Me ne sono accorto *progettando*
  la mutazione, non eseguendola: tutti i dati di prova erano già minuscoli.
  Il crawler abbassa già le direttive, ma `direttive_robots` riceve un dict
  che attraversa il confine dei plugin e non può contarci — e le direttive
  robots sono insensibili al maiuscolo per specifica. È ora fissato da
  un'asserzione con `NONE` maiuscolo, l'unica che quella mutazione fa cadere.
- **La batteria ha dichiarato dieci mutazioni su dieci "non rilevate", con la
  suite rossa.** Cercava la parola `failed` nell'output di pytest, ma
  `setup.cfg` ha già `addopts = -q`: il mio `-q` sulla riga di comando faceva
  `-qq`, che **sopprime la riga di riepilogo finale**. Il verdetto viene ora
  dal codice di uscita. Un banco di prova che non sa distinguere verde da
  rosso avrebbe promosso qualunque cosa.

**Due rilievi nuovi, dalla misura, aperti nel TO-DO come R36 e R37.**
Guardando le direttive rimaste fuori: `nosnippet` e `max-snippet:0` non
producono nulla, e sono le direttive che governano l'**estrazione del testo**
— cioè il meccanismo stesso con cui un assistente cita una pagina. Una pagina
con `nosnippet` è regolarmente indicizzata e non può essere citata: per
questo progetto è più rilevante di `noindex`, e vale la voce a sé. Il prefisso
per agente dell'X-Robots-Tag (`googlebot: noindex`) resta invece contato come
se valesse per tutti — comportamento ereditato, non introdotto qui.

- [x] `none` trattata come `noindex` **e** come `nofollow`.
- [x] Direttive lette come token, non cercate come sottostringhe.
- [x] `all` riconosciuta come default: nessun rilievo, nessun annullamento.
- [x] `nofollow` con rilievo proprio, graduato fra pagina singola e sito.

### R26 — ✅ RISOLTO (2026-08-20): tre difetti di `mars_wcag`
Indipendenti fra loro, tutti nell'area 6.

**1. `alt=""` contato come violazione 1.1.1.** Il filtro era
`not i.get("alt")`, che è falso tanto per l'attributo assente quanto per
quello presente e vuoto. Ma `alt=""` su un'immagine decorativa è la tecnica
**H67**: è la marcatura *corretta*, quella che dice allo screen reader di
saltare l'immagine. Contarla come difetto penalizzava proprio chi aveva fatto
la cosa giusta. Riprodotto su quattro immagini:

```
crawler:  alt=''  alt='Logo Acme'  alt=None  aria-label='Con aria'
rilievo:  [1.1.1] 2/4 immagini prive di testo alternativo   <- l'onesto e' 1/4
```

Il crawler la distinzione `None`/`""` la conserva già: era questo filtro a
buttarla via. Ora `i.get("alt") is None`.

**2. `context.get("delay")` era sempre `None`.** `audit()` leggeva una chiave
che `build_context` **non ha mai inserito** — verificato sul sorgente. Il ramo
`if delay:` di `run_axe` non veniva quindi mai preso: il parametro era codice
morto e Chromium apriva le pagine di fila.

Non è solo una pausa mancata. Il valore giusto non è nemmeno quello chiesto
dalla CLI, perché **robots.txt può alzarlo**:

```
crawler.delay richiesto dalla CLI                    : 1.0 s
crawler.delay dopo un robots.txt con Crawl-delay: 7  : 7.0 s   <- l'effettivo
```

Il crawler rispettava i sette secondi e poi il browser visitava cinque pagine
senza pausa alcuna, sullo stesso sito. `build_context` pubblica ora
`crawler.delay` **dopo** la scansione, cioè il ritardo effettivo, ed è
documentato in [CLAUDE.md](CLAUDE.md) come il valore che deve rispettare
chiunque rivisiti le pagine.

**3. Il riparsing dell'HTML.** `controlli_statici` riapriva l'HTML di ogni
pagina con BeautifulSoup, contro il principio dichiarato in
[CLAUDE.md](CLAUDE.md) e contro la voce **R11** qui sopra, che annunciava «un
parse invece di tre» — vera quando fu scritta, resa falsa da **C8**, che
aggiunse i cinque controlli strutturali. Era l'**unico** modulo a farlo:
`mars_schema` no.

La scelta era fra estrarre i dati nel crawler e correggere le due
dichiarazioni. Estrarli, per una ragione che pesa più della velocità:
`controlli_statici` dipendeva da `pagina["html"]`, quindi il giorno in cui il
crawler smettesse di conservare l'HTML intero — un'ottimizzazione di memoria
plausibile — i controlli statici tornerebbero **vuoti senza un errore**, che è
la classe di guasto peggiore e la stessa contro cui R20 aveva lavorato.

`estrai_struttura(soup)` in `mars_core` legge `heading_levels`,
`form_fields`, `tables`, `links` e `tabindex` mentre il DOM è aperto. Estrae
**dati, non giudizi**: il `role="presentation"` di una tabella arriva grezzo,
decidere che esenti dal criterio resta di `mars_wcag`, con la soglia, la
gravità e il testo del rilievo. Sono già risolte solo le due cose che
richiedono il documento intero e a valle non sarebbero più ricostruibili: la
`<label for>` che punta a un campo e la `<label>` che lo avvolge.

**Verificato per confronto, non per asserzione.** La versione precedente è
stata estratta da `git show HEAD:mars_wcag.py` ed eseguita accanto alla nuova
sullo stesso markup, costruito per accendere tutti e sette i controlli:

```
differenze:
   - [1.1.1] 2/4 immagini prive di testo alternativo
   + [1.1.1] 1/4 immagini prive di testo alternativo
```

Una sola differenza, ed è quella voluta. Gli altri sei rilievi — lang,
salti di heading, campi senza etichetta, tabelle senza `<th>`, link generici,
tabindex positivi — identici parola per parola.

**Una previsione smentita dalla misura.** Davo per scontato che spostare
l'estrazione nel crawler facesse risparmiare il parse. Misurato su una pagina
da 36 KB:

```
parse completo (cio' che mars_wcag faceva)   :  5,7 ms/pagina
estrai_struttura sul DOM gia' aperto         : 18,6 ms/pagina   <- PEGGIO
```

Il costo non era il parse: era `soup.find("label", for=...)` **dentro il ciclo
sui campi**, cioè O(campi × documento) — un difetto che il codice vecchio
aveva già, e che avrei trasportato di peso. Raccogliendo gli `for` una volta
sola:

```
estrai_struttura                             :  2,7 ms/pagina
guadagno netto per pagina                    :  +3,0 ms
```

Il numero onesto è **~3 ms a pagina**, non gli «885x» che il solo
`controlli_statici` mostra: quel confronto tace che il crawler ora fa il
lavoro al posto suo. Il guadagno vero della voce non è la velocità — è che il
modulo non dipende più dall'HTML grezzo.

**La prova che conta: reintrodurre il difetto.** Sedici mutazioni sui due
file, tutte rilevate: il filtro `alt` riportato a `not alt`, il `delay` tolto
dal contesto, il `delay` chiesto al posto dell'effettivo, `audit()` che non lo
passa, `run_axe` che lo ignora, il crawler che non chiama `estrai_struttura`,
i livelli di heading ridotti a h1-h3, le due risoluzioni della `<label>`
disattivate una per volta, gli `for` raccolti come `id`, `has_th` sempre vero,
`role` e `aria-label` non estratti, il `tabindex` convertito nel crawler, e le
due esclusioni di `mars_wcag`.

Una sola non veniva rilevata alla prima esecuzione: **nessun test aveva un
`<input type="submit">` senza etichetta**, quindi togliere `submit`, `reset` e
`button` dalle esclusioni non faceva fallire nulla. È un punto cieco
preesistente, non introdotto qui; `HTML_INACCESSIBILE` ora contiene tutti e
quattro i tipi non interattivi e il conteggio è fissato.

Sono stati resi fedeli anche due finti: il `Crawler` di `tests/test_api.py`
accettava `delay` e lo scartava, e la pagina Playwright finta ignorava
`wait_for_timeout`. Un finto che scarta ciò che il vero conserva non può
accorgersi di nulla — è la stessa lezione dell'adattatore di R16 e R17.

- [x] `alt is None` per il criterio 1.1.1.
- [x] `delay` effettivo nel contesto, e rispettato fino al browser.
- [x] Struttura estratta nel crawler: `mars_wcag` non riparsa più l'HTML, e la
      dichiarazione di R11 torna vera.
- [x] `soup.find` per etichetta tolto dal ciclo: O(campi × documento) eliminato.

### R34 — ✅ RISOLTO (2026-08-21): i titoli di sezione non sono domande
`question_signals` accendeva il segnale «titolo interrogativo» quando
l'intestazione **apriva** con un termine interrogativo. Su un titolo di
sezione questo colpisce una classe intera di intestazioni standard: `Chi
siamo`, `Dove siamo`, `Come funziona`, `Cosa facciamo`, `How it works`. Sono
nomi, non domande, e `Chi siamo` sta su quasi ogni sito italiano.

**Misurato su contenuto reale**, non su un corpus costruito: 40 pagine e 209
intestazioni distinte di un sito vero, scaricate con il crawler di MARS.

```
regola ATTUALE  accende 31 heading su 209  (15%)
regola PROPOSTA accende  5 heading su 209  ( 2%)
```

I 26 di differenza — verificati uno per uno — **non contengono una sola
domanda**. Sono titoli di articolo: `Come mettere in sicurezza un VPS con
Rocky Linux`, `Cosa propone EuroStack`, `Quanto consuma il mondo`, `Perché la
ricerca sbaglia`.

**Una classe che il TO-DO non aveva previsto: i due punti.** `_INIZIO_FRASE`
tratta `:` come confine di frase, quindi il segnale si accendeva **a metà
titolo** su una forma editoriale comunissima:

```
AI Act: cosa scatta davvero il 2 agosto 2026
Il backup non basta: perché c'è chi riparte in ore e chi resta fermo giorni
Un data center in Europa non basta: cosa significa davvero sovranità digitale
Come funziona: le tecnologie integrate
```

**La correzione proposta dal TO-DO non avrebbe corretto nulla.** R34
suggeriva di applicare la regola del `?` «**solo** al segnale "titolo
interrogativo", non a quello sul corpo del testo». Provata prima di
adottarla:

```
heading                        atteso   con la correzione letterale
Chi siamo                      no       SI  <- INVARIATO
Come funziona                  no       SI  <- INVARIATO
AI Act: cosa scatta davvero    no       SI  <- INVARIATO
```

Il motivo sta in due righe distanti fra loro: `answer_shaped` conta un chunk
se **un qualunque** segnale è acceso, e `intero` univa heading e testo prima
di cercarvi l'interrogativo. Quindi l'heading aveva **due possibilità** di
accendere, e restringerne una lasciava l'altra intatta. È la metà del difetto
che R34 non aveva visto, e senza la misura preventiva sarebbe stata scritta
una correzione verde e inefficace.

**Risoluzione: una regola sola, applicata una volta.** *Un titolo è una
domanda quando è punteggiato come tale*, e **entra nel passaggio solo se lo
è**:

```python
titolo_domanda = bool(heading) and "?" in heading
intero = " ".join(x for x in (heading if titolo_domanda else "", testo) if x)
```

Questo concilia due voci che sembravano in conflitto. **R9** aveva deciso che
l'heading fa parte del passaggio — «Come funziona?» come titolo vale quanto la
stessa frase nel corpo — e ha un test che lo difende. **R34** vuole che «Chi
siamo» non accenda nulla. Il discrimine fra i due casi è esattamente il `?`,
quindi una regola sola li serve entrambi, e il test di R9 è rimasto verde
senza modifiche.

**Verificato sul dato che il referto pubblica**, sugli stessi 453 chunk reali:

| | prima | dopo |
|---|---|---|
| `answer_shaped_ratio` | 0,243 | **0,201** |
| segnale `titolo interrogativo` | **49** | **6** |
| `interrogativo a inizio frase` | 98 | 69 |
| `punto interrogativo` | 38 | 38 |

Il segnale sul titolo era falso **43 volte su 49**. Il rapporto scende di 4,2
punti percentuali, il 17% del suo valore — meno del segnale perché molti chunk
ne avevano anche altri. `punto interrogativo` non si muove di uno: era già
corretto, e la correzione non lo ha toccato.

**Il costo, dichiarato.** Le FAQ scritte senza `?` nel titolo non vengono più
riconosciute *dal titolo*; restano riconoscibili dal corpo, se la domanda vi
compare. **Questo costo non è stato misurato su contenuto reale**: il sito
usato per la verifica non ha una pagina FAQ (267 URL in sitemap, nessuno). Su
un corpus costruito a mano il passaggio era da 1 a 2 falsi negativi su 10
domande — e uno dei due sfuggiva anche alla regola vecchia.

**La prova che conta: reintrodurre il difetto.** Otto mutazioni, tutte
rilevate. La seconda è **la correzione letterale di R34**, messa in batteria
apposta: un test scritto sul solo segnale «titolo interrogativo» l'avrebbe
promossa. Le asserzioni sono infatti sull'**elenco intero** dei segnali e sul
rapporto finale, non sul singolo segnale.

Una mutazione non era rilevata alla prima esecuzione: togliere `:` da
`_INIZIO_FRASE`. Dopo la correzione i due punti contano solo per il **corpo**,
dove una frase dopo i due punti è una frase davvero, e lì nessun test li
copriva. Ora c'è.

- [x] Il `?` come discrimine, applicato al solo titolo.
- [x] Il titolo entra nel passaggio solo se è una domanda — la metà mancante.
- [x] R9 preservata senza toccarne il test.
- [x] Misurato su 209 intestazioni e 453 chunk di un sito reale.

### R27 — ✅ RISOLTO (2026-08-21): il timeout ZAP adesso ferma la scansione
Allo scadere di `ZAP_TIMEOUT_SCAN`, `_attendi()` usciva dal ciclo e `run_zap`
proseguiva. `ZapClient` non esponeva nemmeno gli endpoint di stop, quindi non
veniva fermato nulla: **MARS smetteva di aspettare, il daemon no.** Il referto
dichiarava intanto *«Scansione ZAP interrotta dal timeout»* — l'interruzione
riguardava solo l'attesa.

**Riprodotto, e il secondo caso è peggiore di come la voce lo descriveva.**

```
1. scansione ATTIVA in timeout
   chiamate al daemon: spider/action/scan, spider/view/status,
                       ascan/action/scan  <- PAYLOAD D'ATTACCO
                       core/view/alerts
   chiamate di STOP:   NESSUNA

2. la scadenza e' UNA per spider+ascan e non si rinnova
   active scan AVVIATO: True
   active scan ATTESO:  False
```

Il budget è unico per spider e active scan. Se lo spider lo esaurisce, `run_zap`
lanciava comunque `ascan/action/scan` — payload d'attacco: XSS, SQL injection,
path traversal — e poi **non attendeva neanche un controllo di avanzamento**,
né lo fermava. Un attacco avviato e abbandonato.

**Verificato sul daemon vero prima di scrivere il codice**, perché il progetto
si era già scottato dando per buono il client ufficiale ZAP (C9). Su ZAP
2.17.0:

```
spider/action/stop?scanId=999   -> HTTP 400 {"code":"does_not_exist"}
ascan/action/stop?scanId=999    -> HTTP 400 {"code":"does_not_exist"}
spider/action/stopAllScans      -> {"Result":"OK"}
```

Il 400 non è un dettaglio: `_get()` chiama `raise_for_status()`, quindi
fermare una scansione **conclusasi da sola** solleverebbe. Non è un guasto —
fra l'ultimo controllo di avanzamento e la fermata passano fino a
`ZAP_ATTESA` secondi, e la scansione può finire proprio lì.

**Risoluzione.** `ZapClient` espone `spider_stop` e `ascan_stop`. `_ferma()`
li chiama senza mai sollevare, e **restituisce se il daemon ha accettato**:
`does_not_exist` vale come fermata riuscita (quella scansione non sta
girando), ogni altro errore no. `run_zap` restituisce ora una terna
`(alerts, completa, fermate)`, e il referto distingue:

```
Scansione ZAP interrotta dal timeout e fermata: i rilievi sono parziali
Scansione ZAP scaduta e NON fermata: prosegue nel daemon ZAP, e i rilievi
qui sono parziali
```

Il secondo messaggio è il caso che prima era **l'unico**, dichiarato come se
fosse il primo. La chiave `stopped` porta il fatto anche nel dato.

**E non si avvia più un attacco che non si potrebbe sorvegliare**: se la
scadenza è già passata, l'active scan non parte. Con la fermata funzionante,
avviarlo quando resta poco tempo è di nuovo sicuro — verrà fermato.

**La prova end-to-end viene dal daemon, non dal codice.** Un bersaglio locale
deliberatamente lento (60 pagine, 0,4 s a richiesta) e un timeout di 3 s. Mai
un sito reale: l'active scan è un attacco.

| | `run_zap` restituisce | ZAP, 4 secondi dopo |
|---|---|---|
| **prima** | `completa=False` | scansione **`RUNNING` al 35%** |
| **dopo** | `completa=False, fermate=True` | scansione **`FINISHED`** |

**La prova che conta: reintrodurre il difetto.** Nove mutazioni, tutte
rilevate — le due fermate tolte una per volta, l'attacco riavviato senza
tempo, l'esito della fermata ignorato, `does_not_exist` trattato come guasto,
un daemon muto dichiarato fermato, il referto che non distingue più i due
casi, e la fermata chiesta sullo scanId sbagliato.

Una non era rilevata alla prima esecuzione: `_ferma` che dichiara riuscita
**ogni** `HTTPError`. I test coprivano `does_not_exist` e il daemon
irraggiungibile, ma non un errore HTTP *diverso* — un 500, o un codice
inatteso. È il caso in cui non sappiamo se la scansione si sia fermata, e il
dubbio va dichiarato invece di risolverlo a nostro favore. Ora c'è.

`mars_wapt` non aveva rete di test sui propri rami d'uscita: il commit se la
porta, con un daemon finto che **registra gli ordini ricevuti** invece di
accettarli in silenzio. È il punto: R27 non riguarda cosa `run_zap`
restituisce, ma che cosa MARS dice al daemon.

- [x] `spider_stop` e `ascan_stop` esposti e chiamati nel ramo di timeout.
- [x] Il messaggio del referto corrisponde al fatto, nei due casi.
- [x] Nessun active scan avviato senza tempo per sorvegliarlo.
- [x] Verificato end-to-end su ZAP 2.17.0, bersaglio locale.

### R38 — ✅ RISOLTO (2026-08-21): il referto copre tutti e nove gli ambiti
*(aperta e chiusa lo stesso giorno, trovata progettando U13)*

Il referto dichiarava **«Analizzato»** per le aree 3 (Lessicale) e 4
(Semantica), che non producono né punteggio né rilievi. Due ambiti su nove
affermavano un'analisi che non c'era stata.

**Ma il difetto vero è peggiore, e sta nel meccanismo.** `render_text`
decideva **sul nome del modulo**, non sul dato:

```python
if area["module"] == "mars_lexical":
    righe.append("%-20s : Analizzato (Top: %s)" % ...)
    continue          # salta _riga_area E il ciclo dei rilievi
```

Quel `continue` scavalcava sia la riga di stato sia i rilievi. Quindi se uno
di quei due plugin **rompeva**, il referto lo dichiarava analizzato e ne
ingoiava il motivo. Riprodotto:

```
1. Tecnica           : errore del modulo
  ⚠ RuntimeError: il plugin tecnico e' rotto      <- R22 funziona
3. Lessicale         : Analizzato (Top: N/A)      <- l'errore SPARISCE
```

È **R22 riaperta per due aree su nove** — «un'area persa in silenzio è peggio
di una dichiarata fallita», dice [CLAUDE.md](CLAUDE.md). Il caso speciale era
nato prima della macchina dell'onestà e non era mai stato ricondotto a essa.

**Un terzo stato non dichiarato.** `score: None` **senza** `status` non è nel
vocabolario di `STATO_LEGGIBILE`, e le viste lo collassavano su *«non
misurato»*. Due casi veri, oltre alle aree di classifica:

- `mars_citability`, quando **nessun segnale** è misurabile: il composito non
  esiste (`totale` zero) e usciva un None muto;
- `mars_llm_judge`, quando il modello **risponde ma omette il punteggio**: è
  una risposta, non una misura.

**Risoluzione: il fatto entra nel dato, e il caso speciale sparisce.**

I due moduli dichiarano `status: "ranking"` e `tool`; `STATO_LEGGIBILE`
guadagna `"ranking": "classifica, non un voto"`; le viste perdono **tutti** i
`if area["module"] == …`, in `render_text`, in `_scheda_area` e in
`_fascia_quadranti`. Da nove punti cablati sul nome a uno stato nel dato.

```
3. Lessicale         : classifica, non un voto
  BM25 (k1=1.5, b=0.75)
4. Semantica         : classifica, non un voto
  proxy char-TFIDF
```

**Un guadagno che non era nell'ambito della voce.** Il referto non diceva
**quale recuperatore avesse girato**, benché cambi il senso di ogni rango: il
modello multilingue e il proxy char-TFIDF non misurano la stessa cosa.
`VectorRetriever.use_real` lo sapeva già; ora esce.

**Guardato, non dedotto.** Con l'area lessicale forzata in errore, lo scatto
del referto HTML mostrava ancora *«Passaggio in testa: —»*: un paragrafo che
descrive una classifica inesistente. Legato allo **stato** — non al nome del
modulo, che è il difetto da cui si veniva.

**Perché questa forma non andrà rifatta dopo U13.** `_qualificatori` ha già la
regola: *lo stato si annota solo se convive con un punteggio*. Quando U13 darà
un voto alle due aree, `ranking` migrerà da solo dal posto del verdetto a
quello dei qualificatori, come fa `surface`. Un solo vocabolario.

**La prova che conta: reintrodurre il difetto.** Undici mutazioni, tutte
rilevate. Cinque **non** lo erano alla prima esecuzione, e sono la misura di
quanto la suite non proteggesse:

- la fascia dei quadranti che torna a saltare le due aree — nessun test
  guardava che ci fossero tutte. Ora l'elenco atteso **viene dal referto
  stesso**, così non invecchia e non può passare elencandone meno;
- gli stati mancanti di `mars_citability` e `mars_llm_judge`;
- lo strumento non dichiarato dai due moduli di classifica;
- `mars_semantic` che finge il modello vero mentre gira il proxy.

Due errori miei, registrati perché sono ricorrenti: una mutazione con un
pattern non univoco (cinque occorrenze), e **un test vacuo** — l'asserzione
stava dentro un `if` che la eseguiva solo quando era già vera. Riscritto sul
punto d'iniezione documentato (`context["_anthropic_client"]`), senza rami.

Il test riscritto è `test_html_non_finge_un_voto_per_lessicale_e_semantica`:
l'intento era giusto e resta, il meccanismo no. Asseriva la stringa cablata
che è stata rimossa; ora verifica, **per scheda**, che il verdetto sia lo
stato dichiarato e che non compaia alcun `/100`.

- [x] Nessun `if` sul nome del modulo nelle viste.
- [x] R22 vale di nuovo per tutte e nove le aree.
- [x] Nessuno `score: None` senza `status` — ed è un contratto sotto test per
      ogni modulo, non una correzione puntuale.
- [x] Il referto dichiara quale recuperatore ha prodotto la classifica.

### U1 — Fase 1 del programma UPGRADE: il modello dati dei rilievi
*(9 sotto-voci su 9. Il piano sta in [UPGRADE.md](UPGRADE.md), le voci
aperte in [TO-DO.md](TO-DO.md).)*

Fino a qui un rilievo è una stringa con la gravità in un prefisso, e i
prefissi sono **tre**, diversi per modulo: `[critico]`, `[axe:serious]`,
`[ZAP:High]`. Tre scale mai messe in relazione, nessun peso, nessuna chiave
stabile. Su stringhe così non si costruiscono un piano di interventi ordinato,
un confronto fra due esecuzioni o una traduzione — cioè le fasi da U4 a U9.

#### U1.1 — il modello (2026-08-21)

`SEV_*`, `WEIGHTS`, `AREA_PREFIX`, `Finding` + `as_dict()`,
`normalizza_severita`, `severita_lighthouse`, `chiave_esterna` in
`mars_core.py`. Tre decisioni che UPGRADE.md lasciava aperte:

**La scala editoriale si chiama `"mars"`, non `"mars_tech"`.** La usano cinque
moduli — tech, gli header di wapt, gli statici di wcag, schema, citability —
non uno solo.

**Scala ignota e valore ignoto non sono la stessa cosa**, e il piano li
trattava insieme. Un *valore* ignoto è dato esterno: uno strumento che
aggiorna la propria scala non deve far cadere un audit, quindi degrada a
`(info, 1.0)`. Una *scala* ignota è un refuso di programmazione: degradarla
appiattirebbe un intero modulo su un livello, con i punteggi intatti e i test
verdi — **invisibile**. Solleva `ValueError`.

**La soglia di Lighthouse non è arbitraria, ed è misurata.** Nel
`default-config.js` di Lighthouse 13.4.1 la categoria SEO dà peso 1 a ogni
audit tranne `is-crawlable`, che pesa 93/23 (~4,04); il commento nel loro
codice dice perché — è calibrato affinché quel solo fallimento faccia fallire
l'intera categoria (≥31% del punteggio). Gli audit manuali pesano 0. Una
soglia a 3 separa esattamente ciò che Lighthouse considera rompi-categoria.

**`weight` non è la penalità**, e UPGRADE.md (Fase 4) proponeva di calcolare
il recupero «dal campo `weight` **o** da `params["penalty"]`». Sono cose
diverse — 2.0/1.0 è importanza relativa, 40/20/8/3 è punteggio — e per axe e
ZAP la penalità dipende dalla diffusione, quindi è calcolabile **solo dentro
il ciclo che la applica**. Se non la si registra adesso, alla Fase 4 non sarà
più ricostruibile.

Sedici mutazioni, quindici rilevate. La sedicesima **non è riproducibile**: il
default mutabile condiviso su `params` lo rifiuta la dataclass stessa con
`ValueError` all'import. Quell'asserzione resta come documento del contratto,
non come rete di regressione — ed è detto così invece di contarla fra i
successi.

#### U1.2 — il consumatore, prima dei produttori (2026-08-21)

**L'ordine dei passi di UPGRADE.md è stato invertito di proposito.**
`build_report` copia una **lista chiusa** di chiavi: finché non conosce
`findings`, un modulo può produrli perfetti e il referto li butta via — con i
test di modulo tutti verdi. Adeguare i sei moduli prima del referto avrebbe
consegnato cinque commit di lavoro invisibile.

Ogni area porta ora `findings`, e un'area **fallita** riceve un rilievo
sintetizzato dal referto (`<prefisso>.status.error`): il modulo non può
produrlo, perché è fallito, ma è proprio quella che ha più bisogno di comparire
negli elenchi che le fasi successive costruiranno sui rilievi. La gravità è
`info` e non `critical`: il difetto è del nostro strumento, non del sito, e
gonfiarla sarebbe una misura falsa a danno di chi viene analizzato.

**Due moduli su nove erano fuori dal contratto.** `MODULI`, in
`tests/test_modules.py`, era scritta a mano e non conteneva `mars_seo` né
`mars_wapt`: mai verificati contro `audit(context) -> dict`. Ora la lista si
**deriva da `MODULES_REGISTRY`**, così un'area entra nel contratto il giorno
in cui entra nel registro. Non è un dettaglio di igiene: il `ValueError` su
scala ignota deciso in U1.1 serve a poco se un modulo non viene mai eseguito
nei test.

Sette mutazioni, tutte rilevate. Una non lo era alla prima esecuzione:
**troncare la lista `MODULI`**. Una suite non può accorgersi da sé di *quanti*
casi ha girato, quindi l'invariante «il contratto copre ogni area del
registro» va **asserito**, non dedotto dalla derivazione. Ora c'è.

#### U1.3 — `mars_tech`, il banco di prova del modello (2026-08-21)

Primo modulo adeguato, e scelto apposta: unica scala propria, due gravità
calcolate a runtime, punteggio **accoppiato** alla scala e la rete di test più
fitta del progetto. Se il modello fosse sbagliato, si vedrebbe qui.

`_rilievo()` è l'imbuto unico — tredici chiamate — quindi il `Finding` nasce
lì e non in tredici punti. Dodici chiavi stabili, da `tech.robots.ai_blocked`
a `tech.canonical.missing`, tre segmenti ciascuna.

**Il punteggio continua a derivare dalla scala grezza, di proposito.** Le
quattro severità canoniche collassano `grave` e `medio` entrambe in `warning`,
distinte solo da 2.0 contro 1.0 — un rapporto di 2:1 — mentre `PESI` le tiene
a 20:8, cioè 2.5:1. Ricalcolare da lì avrebbe cambiato i punteggi **in
silenzio**, e con essi `mars_citability` e l'indice composito.

Per la stessa ragione `source_severity` conserva la parola italiana: `[critico]`
è ciò che l'utente legge da C10, e `findings_by_severity` la usa come chiave in
otto asserzioni.

**Verificato per confronto con il codice precedente**, preso da `git show`:
punteggi, `issues` e `findings_by_severity` **identici** su un sito pulito e su
uno pieno di difetti. La conversione non doveva cambiare nulla di visibile, e
non l'ha fatto.

**Il dato canonico non tronca.** La issue dice «robots.txt BLOCCA 6 crawler
IA» ed elenca i primi cinque — il conteggio non era troncato, l'elenco sì. Ora
`params["bloccati"]` li porta tutti e sei: a troncare è la vista compatta, non
il dato.

**Una differenza involontaria, colta e tolta.** Con le penalità in `float` lo
score usciva `94.0` dove usciva `94`. La vista non sarebbe cambiata (stampa
`%.0f`) ma il JSON sì — un cambio di contratto silenzioso, e **invisibile ai
test**, perché `94 == 94.0`. Ora c'è `round()`, e un test sul **tipo**.

Dodici mutazioni, tutte rilevate. Tre non lo erano alla prima esecuzione, e
sono tutte cose che si davano per ovvie:

- **il prefisso `[critico]` nelle issues non era sotto test.** Le uguaglianze
  fra due esecuzioni introdotte da R25 non discriminano: cambierebbero
  insieme;
- **il tipo dello score** — proprio la differenza appena descritta;
- **l'ordinamento per penalità invece che per peso.** Sembrano equivalenti e
  non lo sono: `critico` e `grave` pesano entrambi 2.0, quindi pareggerebbero,
  e un ordinamento stabile lascerebbe l'ordine d'inserimento. Il test è
  costruito perché i due ordini divergano.

- [x] `mars_core`: costanti, `Finding`, conversione delle scale.
- [x] `build_report`: `findings` su ogni area, errore sintetizzato.
- [x] Contratto di test derivato dal registro, e l'invariante asserito.
#### U1.4 — `mars_schema`, la prima area senza una scala propria (2026-08-21)

Qui la gravità **non esiste nel modulo**: c'è solo l'ordinamento implicito
delle penalità, 50/10/5. Renderla canonica è quindi una **scelta editoriale**,
e va dichiarata come tale invece di lasciarla dedurre dai numeri.

`source_severity` resta **vuoto**, ed è l'opposto di `mars_tech`. Là
`[critico]` è la parola che l'utente legge; qui le `issues` non portano alcun
prefisso di severità, quindi dichiararne una attribuirebbe al modulo una scala
che non pubblica.

**JSON-LD assente resta `warning`, non `critical`, benché costi metà del
punteggio.** In MARS `critical` significa che il sito è **invisibile** agli
assistenti — è l'uso che ne fa `mars_tech` con i crawler bloccati e le pagine
noindex. Senza JSON-LD un sito è meno leggibile, non invisibile: appiattire la
differenza toglierebbe senso al livello più alto.

**Primo caso di aggregazione per chiave.** Le `issues` restano una per blocco —
dicono su quale URL sta il difetto, e sono sotto test — mentre i `findings`
aggregano per controllo, con le occorrenze in `params["n"]` e gli URL in
`params["urls"]`. Su tre blocchi difettosi: **tre issues, due rilievi**.

Non è estetica. In quest'area `score -= 5` sta accanto a ogni `append`, quindi
la cardinalità della lista **è accoppiata al punteggio**: spezzare un controllo
in N rilievi farebbe crollare i punteggi di chiunque li conti. È il difetto
C10 già pagato in `mars_tech`. La penalità di un rilievo aggregato è quindi
quella **totale** del controllo, `n × per-occorrenza`, così la somma ricostruisce
lo score.

Verificato per confronto col codice precedente: punteggi e `issues` identici su
quattro casi, compreso quello senza pagine.

Dieci mutazioni, tutte rilevate. Una non lo era alla prima esecuzione, e la
lezione vale oltre questa voce: **i valori delle penalità non erano fissati,
solo la loro relazione.** Un test che verifica «la somma ricostruisce lo score»
resta verde anche cambiando una penalità, perché i due lati cambiano insieme.
Ora ci sono cinque casi con il punteggio atteso, e pinnano anche l'ordine che
ha un significato: un blocco malformato costa il **doppio** di uno vuoto, perché
un JSON rotto è un errore e un blocco vuoto una dimenticanza.

- [x] `mars_core`: costanti, `Finding`, conversione delle scale.
- [x] `build_report`: `findings` su ogni area, errore sintetizzato.
- [x] Contratto di test derivato dal registro, e l'invariante asserito.
- [x] `mars_tech`: dodici chiavi, penalità nei params, comportamento identico.
#### U1.5 — `mars_wcag`, due origini nello stesso modulo (2026-08-21)

Il primo modulo con **due sorgenti di gravità**: axe, che una scala ce l'ha, e
sette controlli statici che non ce l'hanno. Convivono nello stesso elenco.

**Il criterio WCAG non è una gravità.** `[1.3.1/3.3.2]` è il *riferimento* che
rende il rilievo verificabile da chi lo riceve. Va in `params["criterio"]` e
resta nel testo della issue; la gravità è un'altra cosa, ed è nostra — quindi
`source_severity` dei sette statici è vuoto. `critico` va a ciò che **blocca**
uno screen reader (niente alternativa testuale, niente etichetta, niente lingua
dichiarata); tabelle senza `<th>` e tabindex positivi rendono la navigazione
peggiore, non impossibile.

**La penalità di un controllo statico dipende dal ramo, e va detto.** Nel
ripiego pagano 12 ciascuno — è il `100 - len(statici) * 12` di sempre. Nel ramo
axe il punteggio viene dalle violazioni e i controlli statici **non lo toccano**:
la loro penalità lì è **zero**. Attribuirgliene 12 prometterebbe alla Fase 4 un
miglioramento che non arriverebbe.

Nel ripiego ogni rilievo porta inoltre `params["surface"] = True`: senza, un
elenco di soli findings mostrerebbe un `critical` come se venisse da una misura
che non c'è stata. È R21 portato dentro il dato.

**`impact` assente non diventa un giudizio di axe.** axe può ometterlo, e MARS
lo appiattisce a `minor` per poter comunque pesare la violazione — ma è una
**nostra** assunzione. `source_severity` resta vuoto: scrivere `axe:minor`
attribuirebbe ad axe un giudizio che non ha espresso. Il punteggio si calcola
lo stesso, che è a cosa serve l'assunzione.

**Due cose raccolte perché il ciclo era già aperto.** `helpUrl` di axe — il
link alla spiegazione della regola, cioè metà del lavoro della Fase 3 — veniva
scartato; ora finisce in `Finding.url`. E gli id di axe passano da
`chiave_esterna()`: `color.contrast` diventa `color_contrast`, perché quel
punto romperebbe la profondità fissa a tre segmenti e con essa le ancore del
referto.

Verificato per confronto col codice precedente: punteggi e `issues` identici
su sito difettoso, sito pulito, area senza pagine e ramo axe.

Undici mutazioni, tutte rilevate. Tre non lo erano alla prima esecuzione: la
**penalità axe che ignora la diffusione** (il peso scalato da 1x a 2x è
calcolabile solo dentro il ciclo che lo applica, e nessun test lo ricostruiva),
e i **due rilievi di stato** — scansione parziale e area senza pagine — che
esistevano nei campi strutturati ma non fra i findings.

Un errore mio, già registrato e ripetuto: la mutazione sul rilievo di scansione
parziale era `[] or [Finding(...)]`, che **vale** `[Finding(...)]` — un no-op
travestito da mutazione. Rifatta come si deve, il test la coglie.

- [x] `mars_core`: costanti, `Finding`, conversione delle scale.
- [x] `build_report`: `findings` su ogni area, errore sintetizzato.
- [x] Contratto di test derivato dal registro, e l'invariante asserito.
- [x] `mars_tech`: dodici chiavi, penalità nei params, comportamento identico.
- [x] `mars_schema`: gravità editoriale dichiarata, aggregazione per controllo.
- [x] `mars_wcag`: due origini, penalità per ramo, `impact` assente onesto.
- [ ] I tre moduli restanti (U1.6-U1.8), più `mars_llm_judge` (U1.9).

#### U1.6 — `mars_wapt`, tre rami e un solo elenco di rilievi (2026-08-24)

Il modulo con la superficie più larga della fase: **tre rami d'uscita** — ZAP,
ripiego sugli header, area non misurata — **due origini di gravità** e, come
diceva la voce, **nessuna rete di test** su ciò che l'adeguamento tocca.
`audit_headers()` non aveva un solo test proprio: il ramo `surface` non era mai
stato raggiunto, le penalità 15/15/10 non erano protette da nulla, e `audit()`
non aveva **mai visto un alert non vuoto** — `run_zap` veniva sostituito con un
ritorno `([], False, fermate)`. Il commit si porta quella rete, ed è la ragione
per cui i test propri dell'area passano da **15 a 61**.

**La gravità dei tre header è nostra, ma non è arbitraria.** In quest'area
`critico` è riservato a una vulnerabilità **sfruttabile constatata**; un header
mancante è una difesa in profondità assente, che rende sfruttabile *un altro*
difetto senza esserlo di per sé. E questo ramo non ha scansionato nulla: ha
letto tre header di una risposta, quindi dichiarare `critical` di lì sarebbe
R21 — vendere per misura ciò che non lo è. Lo conferma l'unico strumento con
una scala tarata: ZAP classifica gli stessi tre fatti **Medium** (10038 CSP,
10020 anti-clickjacking) e **Low** (10035 HSTS), mai High.

Fra `grave` e `medio` decide la **monotonia con le penalità**, che sono già
tarate e non si toccano: 15 → grave, 10 → medio, così la granularità che le
quattro severità perdono si ritrova nel peso (2.0 contro 1.0) — è la decisione
**D2** del programma. Conseguenza scritta nel codice perché non la si scopra
dopo: un `grave` dedotto da un solo HEAD pesa **più** di un Medium di ZAP. È
innocuo soltanto perché i due rami si escludono a vicenda.

**`source_severity` resta vuoto quando ZAP tace.** Il modulo assume
`Informational` se `risk` manca, per poter comunque pesare l'alert; ma è una
*nostra* assunzione, e scrivere `ZAP:Informational` gli attribuirebbe un
giudizio mai espresso. Qui però si chiude anche il buco lasciato in U1.5: il
livello **usato per il calcolo** finisce in `params["risk"]`, così l'assunzione
è auditabile invece che invisibile.

**La `solution` di ZAP entra in `Finding.fix`, e non si ripulisce.** Verificato
sul sorgente di ZAP e sul daemon installato: `core/view/alerts` restituisce
**testo semplice**; i `<p>` che si vedono nei referti tradizionali li aggiunge
`legacyEscapeParagraph` del generatore, e il progetto lo dichiara come scelta
(issue zaproxy#5685). Cercati tag HTML in tutti i `.soln`/`.desc`/`.refs` di 79
add-on: **zero**. Uno strip sarebbe il rimedio a un problema che lo strumento
non ha, e mangerebbe in silenzio i `<meta http-equiv=…>` di cui un testo di
sicurezza è pieno. Nessun campo di un `Finding` è HTML: chi lo renderà lo
escapa, ed è già ciò che `_e()` fa con le issues.

**`reference` va in `params["references"]`, non in `Finding.url`.** È **una**
stringa con dentro più URL separati da a-capo: `url` è un link solo, e
collassarla ne mostrerebbe uno nascondendo gli altri. In quest'area `url`
sarebbe per giunta ambiguo fra «la pagina colpita» — che sono N, e stanno in
`params["urls"]` — e «la documentazione della regola». Resta vuoto.

**L'ordine dei findings rispecchia esattamente quello delle `issues`**: in
testa i rilievi di timeout, in coda la nota sulla scansione passiva. Le due
viste sono la stessa informazione per due lettori, e raccontare la stessa
scansione in due ordini diversi ne impedirebbe il confronto. Per la stessa
ragione l'ordinamento degli alert resta per **classe di rischio** e non passa
alla «penalità decrescente» di U1.3: ordinare per penalità scavalcherebbe i
pari-classe — un High su 10 URL davanti a un High su 1 — cambiando il testo che
l'utente legge.

**Interrotta e abbandonata restano due chiavi distinte**, `sec.status.partial`
e `sec.status.not_stopped`: sono due fatti diversi — una scansione conclusa in
anticipo e del traffico ancora in corso — ed è esattamente ciò che R27 esiste
per non confondere. `not_stopped` è inoltre la negazione del campo `stopped`
che il dict già pubblica, così chiave e campo non possono raccontare due
storie. Entrambe sono `info`: la severità è la gravità del difetto **del
sito**, e un daemon che non si ferma non si ripara cambiando il sito. L'urgenza
la portano la posizione e il testo.

**Verificato per confronto con il codice precedente**, preso da `git show`:
punteggi, `issues` e ogni altra chiave del dict **identici** su 43 casi —
diciannove per `score_from_alerts` (compresi risk assente, risk ignoto, alert
senza URL, clamp a zero, gruppo con due `alertRef` e due soluzioni), tredici
per `audit_headers` (gli otto sottoinsiemi dei tre header più i ripieghi
HEAD→GET e i tre modi di non leggerli) e undici per `audit()`. Zero
divergenze.

**Ventotto mutazioni, tutte rilevate.** Una non lo era alla prima esecuzione:
`quanti = len(urls)` senza il minimo di 1. Un alert **senza URL** — ne esistono,
sono quelli manuali e da script — avrebbe visto la penalità della sua regola
azzerarsi e la issue dire «(0 URL)», e nessun test se ne sarebbe accorto, perché
tutti i casi provati un URL ce l'avevano. Il `n` finito nei params ha reso il
buco visibile.

Due mutazioni sono state **riscritte perché mal costruite**, ed è la stessa
lezione di U1.5 sotto altra forma: la prima versione della «senza la chiave
`findings`» rompeva la sintassi del file, e un modulo che non si importa fa
fallire tutto — non dimostra che il test cogliesse *quel* difetto. Una
mutazione vale solo se il codice resta valido.

**Quattro difetti trovati e non corretti qui**, registrati in R39 perché
correggerli sposterebbe punteggi o testi: `alertRef` è codice morto nella
catena di raggruppamento (i tre alert CSP `10038-1/-2/-3` si fondono in uno);
`chiave_esterna()` non è iniettiva e un `pluginId` `-1` collide con `1`; ZAP
raggiunto e fallito non lascia traccia nel referto; `audit_headers` perde il
primo errore quando ripiega. Il dato per chiudere il primo — `alert_refs` — il
commit lo conserva già.

- [x] `mars_core`: costanti, `Finding`, conversione delle scale.
- [x] `build_report`: `findings` su ogni area, errore sintetizzato.
- [x] Contratto di test derivato dal registro, e l'invariante asserito.
- [x] `mars_tech`: dodici chiavi, penalità nei params, comportamento identico.
- [x] `mars_schema`: gravità editoriale dichiarata, aggregazione per controllo.
- [x] `mars_wcag`: due origini, penalità per ramo, `impact` assente onesto.
- [x] `mars_wapt`: tre rami, gravità ancorata a ZAP, `solution` raccolta.
- [ ] I due moduli restanti (U1.7-U1.8), più `mars_llm_judge` (U1.9).

#### U1.7 — `mars_seo`, la prima penalità che non è una stima (2026-08-24)

L'unica voce che chiede di **arricchire il dato a monte**: `score`,
`scoreDisplayMode` e il `weight` di `auditRefs` venivano letti e buttati via,
e senza di essi un rilievo Lighthouse non ha né gravità né peso.

**Il peso va letto dal referto, mai dalla configurazione**, ed è il fatto su
cui poggia tutto il resto. `core/scoring.js` di Lighthouse **azzera** il peso
degli audit non applicabili, informativi e manuali prima di scriverlo nel LHR:
un `is-crawlable` che Lighthouse non ha potuto applicare pesa **0** nel
referto e **4,04** nel `default-config.js`. Una tabella cablata lo farebbe
uscire `critical`.

**Il peso di `error` invece non viene azzerato**, e la costante di U1.1 non lo
contemplava: `severita_lighthouse(None, "error", 93/23)` restituiva
`(critical, 2.0)` — un audit che lo strumento **non è riuscito a eseguire**
presentato come difetto grave del sito, cioè R21. `"error"` è ora nella tupla
`LH_MODI_NON_MISURATI`. È l'unica riga di `mars_core` toccata dalla voce, ed è
la correzione di un fatto verificabile nel sorgente, non un cambio di
progetto: nessun chiamante attuale ne cambia l'uscita.

**La penalità qui si calcola, ed è esatta.** In tutte le altre aree è una
scelta editoriale (40/20/8/3, 15/15/10, 25/10/3); qui il punteggio arriva già
fatto da Lighthouse, e non c'è nessuna penalità *applicata* da registrare. Ma
la sua formula — `clampTo2Decimals(Σ(score×peso)/Σpeso)`, `core/scoring.js` —
è una media pesata, quindi **lineare**: il contributo di ogni audit è esatto,
additivo e invertibile. `params["penalty"] = peso/Σpeso × 100 × (1 − score)` è
di quanti punti risalirebbe l'area se quel controllo passasse, e la somma dei
contributi ricostruisce `100 − score` a meno del solo arrotondamento a due
decimali di Lighthouse, cioè mezzo punto. Misurato sul referto reale: 63,78
contro 64,00. Resta una **ricostruzione**, non una misura — Lighthouse quel
numero non lo pubblica — ma è la prima penalità del progetto che non è una
stima, e la Fase 4 avrà qui un recupero vero.

Sul referto reale: `is-crawlable` fallito vale **36,6 punti**, ciascuno degli
altri **9,1**. È il 31% che il commento di `default-config.js` dichiara di
aver risolto, ritrovato per calcolo.

**Il titolo di un controllo non misurato era una frase falsa.** Lighthouse usa
`failureTitle` solo quando `score < 0.9`, quindi un `notApplicable` porta il
titolo del **successo**: su una pagina senza canonical la issue recita «da
verificare a mano: Il documento ha un elemento `rel=canonical` valido», che
sbaglia due volte. I `Finding` prefissano ora «Non applicabile a questa
pagina», «Da verificare a mano», «Controllo non eseguito da Lighthouse»; le
`issues` restano com'erano, perché sono la vista congelata. È **l'unico punto
di tutta la fase in cui il dato nuovo si discosta dalla vista compatta**, e si
discosta perché quella riga è nota per falsa.

**I controlli superati non diventano rilievi**, e il filtro non è
un'ottimizzazione: `severita_lighthouse` decide su modo e peso e **non guarda
lo score**, quindi un superato a peso 1 uscirebbe `warning`. Un sito perfetto
mostrerebbe nove voci da fare. `SEV_OK` resta perciò senza usi dopo U1.7, e
non è una dimenticanza: usarla vorrebbe dire scavalcare l'unica funzione
scritta per quest'area.

**Un `1 − None` che avrebbe fatto sparire l'area.** Un `auditRef` il cui `id`
non compare fra gli `audits` dà `score: None` e non è né superato né manuale:
il calcolo della penalità sarebbe finito in `TypeError`, che l'`except` di
`audit()` cattura — «Lighthouse non riuscito», area intera persa. È R22 sotto
altra forma, ed è chiuso da una guardia e da un test suo.

**La fixture di test è stata rifatta fedele**, ed era la condizione per
poter provare qualunque cosa: aveva sei audit e **nessun peso**, quindi ogni
rilievo sarebbe uscito `info` e un test sulla gravità sarebbe passato per il
motivo sbagliato. Ora sono gli undici reali, coi pesi reali, il peso azzerato
sui non applicabili, e un punteggio (0,27) che è il risultato aritmetico della
formula di Lighthouse su quegli esiti. Quattro asserzioni esistenti sono
cambiate di conseguenza, tutte visibili nel diff.

Verificato per confronto col codice precedente su **52 casi**: LHR reale
prodotto dalla Lighthouse 13.4.1 di `node_modules` contro una pagina servita
in locale, la fixture di HEAD, pesi assenti/nulli/illeggibili/negativi, LHR
degeneri, `error` a peso pieno e a peso zero, i sei rami di `audit()`. Zero
divergenze: punteggi, `issues` e voci di `audits` identici, meno i tre campi
nuovi.

Ventotto mutazioni, tutte rilevate — ma **solo al secondo giro**, e la
ragione vale più delle mutazioni:

**Il banco di prova mentiva, ed era la trappola già scritta in CLAUDE.md.** Il
bytecode cache di Python valida su *(mtime in secondi interi, dimensione)*: le
due mutazioni che cambiavano una cifra senza cambiare la lunghezza —
`LH_PESO_CRITICO` da `3.0` a `5.0`, `MAX_ELEMENTI` da `5` a `3` — venivano
applicate e ripristinate dentro lo stesso secondo, e **pytest eseguiva la
versione vecchia**. Il difetto si è manifestato al rovescio: dopo il giro, il
sorgente diceva `3.0` e il runtime rispondeva `5.0`, facendo fallire un test
che era corretto. Un giro di mutazioni deve girare con
`PYTHONDONTWRITEBYTECODE=1`, altrimenti misura il codice sbagliato proprio
sulle mutazioni più insidiose — quelle di un carattere.

Due mutazioni erano davvero sfuggite, e tutte e due per lo stesso vizio:
**il test confrontava una costante con se stessa.** `len(items) ==
MAX_ELEMENTI` resta verde per qualunque valore della costante — è la lezione
di U1.4 ripetuta — e il test sull'audit in errore non asseriva i conteggi,
quindi non vedeva la tupla della voce allargarsi. Ora il primo pinna i cinque
elementi per nome, il secondo pinna `(3, 6, 2)` e il testo della issue.

- [x] `mars_seo`: peso dal referto, penalità esatta, titoli non più falsi.
- [ ] `mars_citability` (U1.8) e `mars_llm_judge` (U1.9).

#### U1.8 — `mars_citability`, l'area che ridice invece di misurare (2026-08-24)

Le sei voci precedenti hanno adeguato aree che **misurano**. Questa adegua
un'area che **rilegge**: `mars_citability` non guarda il sito, riduce i
punteggi altrui a sette segnali, quattro profili e un indice. Il rischio non
era perdere informazione — era **produrne di finta**, cioè un secondo elenco di
difetti che sembra indipendente dal primo e che a valle verrebbe sommato al
primo.

**`params["derived"] = True` su ogni rilievo, senza eccezioni**, ed è un
invariante d'area invece che un giudizio caso per caso. Le due letture
possibili erano «questo rilievo ridice un difetto già misurato altrove» (vera
per i segnali, falsa per il mercato sconosciuto) e «questo rilievo non nasce da
una misura di quest'area: **descrive, non quantifica**» (vera per tutti). Vince
la seconda: dà al consumatore una regola sola invece di tre classi, e un test
su un invariante regge dove una tabella di casi deriva.

**Nessun rilievo porta `penalty`, e l'assenza è il significato del
marcatore.** Sarebbe calcolabile — il composito è una media pesata, quindi
lineare come quella di Lighthouse, e il contributo di un segnale è esatto:
proprio per questo non va messo. Sarebbe lo stesso deficit espresso in una
seconda unità di misura, mentre l'area d'origine lo dichiara già riga per riga
e con molto più dettaglio. È **D3 portata dentro il dato**: la citabilità è
esclusa dal punteggio complessivo perché conterebbe due volte, e per la stessa
ragione è esclusa dalle somme di recupero.

**Tutti `info`, peso 1.0, e non è prudenza.** La severità è l'asse su cui la
Fase 4 ordinerà il piano di interventi, e su quell'asse una sintesi non deve
**mai** scavalcare la misura che sintetizza: «Segnale debole: Sicurezza
(50/100)» e «[ZAP:High] SQL injection (3 URL)» descrivono lo stesso difetto, e
il secondo porta regola, URL e soluzione. Tenerli al gradino più basso rende
l'ordinamento per gravità **monotono rispetto alla derivazione**.

Per la stessa ragione il modulo **non usa** la scala editoriale `"mars"`, e il
commento di `_SCALE_SEVERITA` che da U1.1 contava «cinque moduli» è stato
corretto a quattro, nel codice e nel test. L'alternativa — dichiarare `lieve`
sette volte per tenere vera quella frase — attribuirebbe al modulo una scala
che non pubblica.

**Le chiavi si compongono col nome del segnale e NON passano da
`chiave_esterna()`.** Quella funzione difende la profondità fissa da un id
ostile — axe, ZAP, Lighthouse — al prezzo dell'iniettività (R39). Qui il
vocabolario è scritto nel file: un refuso deve far fallire un test, non essere
ripulito in silenzio. Famiglia = soggetto, esito = verdetto
(`cit.seo.weak`, `cit.seo.unmeasured`), come `sd.jsonld.*` e `sec.headers.*`:
così lo stesso segnale porta due esiti sotto la stessa famiglia.

**Una issue che elenca sette segnali diventa sette rilievi**, e l'argomento di
`mars_schema` per aggregare qui non vale: là la cardinalità era accoppiata al
punteggio, qui non c'è punteggio da ricostruire. Ogni segnale non misurato
punta invece a un'**area diversa** — che è l'unica informazione azionabile del
caso — e `params["sources"]` la porta. Il rapporto fra le due viste è quindi
uno-a-molti in un verso e molti-a-uno nell'altro (i deboli: tutti nel dato, due
nelle issues): **non sono tenute alla stessa cardinalità, sono tenute allo
stesso contenuto e allo stesso ordine**.

**Un pareggio che decide quale segnale l'utente legge.** `deboli` si ordina per
valore e, a parità, per **etichetta italiana**; per emettere la chiave serviva
il nome interno, e metterlo al posto dell'etichetta avrebbe cambiato il
tie-break — sei coppie su ventuno si invertono, e il pareggio attraversa il
taglio `deboli[:2]`, quindi cambia *quale* segnale diventa issue. Il nome è
entrato come **terzo** elemento della tupla, dove non viene mai confrontato
perché le etichette sono uniche. Quel criterio non aveva una sola asserzione
dietro: ora ne ha una, costruita su un pareggio vero.

**`ORIGINE` è una seconda dichiarazione, e lo dice.** La corrispondenza
segnale → area vive già dentro `raccogli_segnali`, che legge i moduli per nome.
Riscriverla per leggere la tabella sarebbe un refactor a comportamento
invariato dentro un commit che cambia il comportamento, e l'ordine del suo dict
letterale è dato osservabile (decide l'ordine di `signals` nel JSON e dei nomi
dentro la issue). A tenere insieme le due dichiarazioni non c'è un accorgimento
ma **un test**, parametrizzato su tutti e sette i segnali: costruisce i
`results` a partire da `ORIGINE` e verifica che il segnale corrispondente
risulti misurato.

**Il doppio canale, accettato e non filtrato.** I findings della citabilità
escono nel JSON due volte: `referto["citability"]["findings"]` (copia integrale
del dict) e la voce d'area (copia selettiva) — tre, contando `modules`
dell'API. È l'unica area con questo doppio canale. Filtrarlo significherebbe
far decidere a `build_report` sul **nome del modulo**, che è l'anti-pattern che
R38 ha appena tolto da `render_text`: si chiuderebbe un doppione
reintroducendone la causa. Chi renderà i findings in HTML dovrà agganciarsi a
**uno solo** dei tre punti in cui la citabilità compare.

Verificato per confronto col codice precedente su **58 casi**, con uguaglianza
**totale** del dict (non chiave per chiave, così una chiave scomparsa non
passa) più l'ordine delle chiavi di `signals`: zero divergenze. E le viste sono
identiche **byte a byte**, testo e HTML.

Ventisette mutazioni, tutte rilevate al primo giro — con
`PYTHONDONTWRITEBYTECODE=1` fin dall'inizio, che è la lezione di U1.7 applicata
invece che ripagata.

Due difetti trovati e non corretti, in **R41** e **R42**: il marcatore
`derived` non ha ancora un lettore, e le tre guardie contro il doppio conteggio
non sono equivalenti — la Fase 5 conterebbe i derivati fra gli «Info»; e la
vista testo, quando la citabilità fallisce, **non stampa nulla**, perché il suo
blocco dedicato è protetto da `profiles` e il ciclo delle aree la salta per
nome.

- [x] `mars_citability`: derivati senza penalità, `sources`, chiavi per segnale.
- [ ] `mars_llm_judge` (U1.9), poi il bump a 2.1.0.

#### U1.9 — `mars_llm_judge`, e una fixture che mancava da sempre (2026-08-24)

L'ultima delle nove, e la più piccola per ambito: **solo `llm.status.*`**.
Nove chiavi per nove rami d'uscita, tutte `info` a peso 1.0, nessuna
`penalty` — nessuno di questi esiti si ripara cambiando il sito.

**La cosa più importante di questa voce non è nel modulo: è in
`tests/conftest.py`.** Scrivendo nove test su l'unica area che *spende
denaro*, la prima domanda era se la suite potesse spendere. Misurato, non
dedotto: un test con `ANTHROPIC_API_KEY` nell'ambiente e `llm: "auto"` faceva
partire **tre POST veri verso `api.anthropic.com`**. `niente_rete` copre
`requests`; l'SDK Anthropic passa da **httpx** e non lo vede — è **R20 nella
stessa forma**, sull'unico modulo che, se sfugge, presenta un conto.

La fixture `nessuna_spesa` intercetta `httpx.HTTPTransport.handle_request` e
non `httpx.Client.send`: il `TestClient` di FastAPI è *esso stesso* un client
httpx, con un transport suo che parla all'applicazione in memoria — bloccare
`send` fermerebbe anche quello, mentre `HTTPTransport` è esattamente e
soltanto la rete vera. E l'asserzione sta **dopo lo `yield`**, perché
sollevare non basta: l'SDK incapsula qualunque eccezione del transport in un
`APIConnectionError`, che `mars_llm_judge` gestisce e dichiara. Senza il
controllo in coda un test che sfugge finirebbe **verde**, esercitando il ramo
sbagliato. Verificato dopo: la sonda che tenta la chiamata ora fallisce in
teardown, con l'elenco degli URL tentati.

**Un ramo, un fatto, una chiave.** Le due regole già fissate si applicano in
direzioni opposte nello stesso modulo:

- il `TypeError` con `"authentication"` nel messaggio e l'eccezione della
  **costruzione** del client sono **lo stesso fatto in due momenti** — quale
  dei due scatti dipende dalla versione dell'SDK, non da un fatto sull'audit:
  una chiave sola, `llm.status.no_credentials`, con `params["stage"]` a
  distinguere `client` da `request`. Senza, un aggiornamento dell'SDK
  sposterebbe il fatto da un ramo all'altro senza lasciare traccia;
- le **quattro eccezioni** catturate insieme sono già indistinte nella issue:
  una chiave sola, `llm.status.unreadable`, e `detail` dice quale. È la regola
  di `seo.status.failed`;
- il `TypeError` **senza** `"authentication"` è invece un fatto diverso — la
  chiamata è malformata, kwarg ignoto o SDK incompatibile — ed è un difetto
  *nostro*: `llm.status.bad_call`. Fonderlo con l'altro rifarebbe il difetto
  che C2 ha già chiuso.

**Una chiave sbagliata non è una chiave assente**, e va saputo:
`anthropic.AuthenticationError` **è** un `APIError`, quindi una chiave scaduta
o revocata — il caso reale più frequente — esce come `api_failed`, non come
`no_credentials`. Sono due fatti con riparazioni diverse: l'SDK non ha
**risolto** una credenziale contro l'API ha **rifiutato** quella risolta. Il
`detail` porta il nome dell'eccezione, che si autonomina.

`api_failed` e non `api_error` proprio per questo genere di vicinanza:
`llm.status.error` è già la chiave che il referto sintetizza quando il
*modulo* solleva, e due chiavi che differiscono per una parola e significano
cose diverse si confondono a mano.

**La traccia della spesa non spariva quando serviva.** `costo_stimato` esce
solo dal ramo di successo: nei rami che falliscono *dopo* l'invio, cioè quelli
che possono essere stati fatturati, il numero non c'era. Ora i rilievi di quei
rami portano `model`, `chunks_sent` e `estimated_input_tokens`. `attempted`
dice se si è arrivati a chiamare il modello — e la docstring dice che **non**
significa «speso»: un 429 non si paga, e nessun ramo può saperlo.

**Perché i `punti_deboli` non diventano rilievi.** `Finding.key` è ciò su cui
poggeranno il confronto fra due esecuzioni e i cataloghi di traduzione: una
chiave ricavata da prosa libera sarebbe o **variabile** — vietato — o
**ripetuta**, che distrugge l'identità e impedisce a un delta di distinguere
«lo stesso punto debole persiste» da «ne è comparso un altro». Quella prosa
cambia per giunta a ogni esecuzione (`thinking: adaptive`) e a ogni modello.
Registrato in U10.1, con le due condizioni che permetterebbero di riaprirla.

**Conseguenza dichiarata**: quando il giudizio **riesce**, l'area restituisce
`findings: []` mentre le sue `issues` portano fino a tre punti deboli. È
l'unico punto della Fase 1 in cui la vista compatta dice **più** del dato
canonico — in `mars_seo` (titoli dei non misurati) e in `mars_citability`
(`cit.status.no_composite`) la divergenza va nella direzione opposta. Non è
un'anomalia: due delle nove aree, `mars_lexical` e `mars_semantic`, non
producono né `issues` né `findings` **mai**.

Chiusura parziale di **R31**: il `RuntimeError("richiesta declinata dai
classificatori")` era l'unica diagnosi del rifiuto e si perdeva interamente —
la issue pubblica il solo tipo. Ora arriva in `detail`. Le `issues` non
cambiano, quindi la vista compatta resta imprecisa: resta da fare un ramo e
uno `status` propri.

Verificato per confronto col codice precedente su **tutti e nove i rami** più
le funzioni pure, con uguaglianza totale del dict meno `findings`: zero
divergenze.

Ventitré mutazioni, tutte rilevate. Due sfuggite alla prima esecuzione, ed
erano buchi veri:

- **`Finding.area` non era asserito da nessun test di modulo** — in tutto il
  progetto una sola asserzione, in `tests/test_report.py`. Sostituire
  `area="mars_llm_judge"` col prefisso `"llm"` passava inosservato, a un
  carattere di distanza dall'errore;
- **la fixture contro la spesa non era presidiata da nulla**: un guardiano è
  rilevabile solo se qualcosa prova a passargli davanti. Ora un test verifica
  il **meccanismo** — che il transport sia sostituito, via un marcatore
  sull'oggetto — perché verificarne l'effetto richiederebbe di tentare una
  richiesta, e la fixture fa fallire in teardown proprio i test che ci provano.

Una terza mutazione era mal costruita — rompeva la sintassi — ed è stata
rifatta: un modulo che non si importa fa fallire tutto, e non dimostra che il
test cogliesse *quel* difetto. È la stessa lezione di U1.6, alla terza
occorrenza.

- [x] `mars_llm_judge`: nove rami, nove chiavi di stato, la spesa tracciata.
- [x] La suite non può più spendere: `nessuna_spesa` in `conftest.py`.
- [x] `__version__` a **2.1.0**, versione dichiarata in testa al README.

**La Fase 1 è chiusa.** Tutte e nove le aree emettono `findings` accanto alle
`issues`, che non sono cambiate di una parola in nessuna delle nove voci: ogni
adeguamento è stato verificato per confronto col codice precedente, sempre con
zero divergenze — 43 casi in U1.6, 52 in U1.7, 58 in U1.8, tutti e nove i rami
in U1.9.

Le mutazioni provate nelle nove sotto-voci sono **162**, di cui 116 nei sei
moduli che UPGRADE.md elenca; una sola non è riproducibile (U1.1, il default
mutabile che la dataclass rifiuta all'import) e resta contata come tale, non
fra i successi. La suite arriva a **548 test**: 118 li hanno aggiunti le
ultime quattro voci, misurati da 430 a 548.

Il valore non sta nel numero: sta nelle **tredici mutazioni sfuggite alla
prima esecuzione**, che le voci qui sopra conservano una per una perché
ciascuna ha rivelato un test debole — un ordinamento mai asserito, una
costante confrontata con sé stessa, un banco di prova che eseguiva bytecode
vecchio, un guardiano che nessuno presidiava.

### U2 — ✅ CHIUSA (2026-08-24): i golden del referto

**Il problema.** `tests/test_report.py` fa asserzioni puntuali: colgono ciò
che qualcuno ha pensato di guardare, e una modifica di resa che non tocca
quei punti passa inosservata. Con **otto fasi di lavoro sul renderer davanti**,
quella rete andava montata prima, non dopo.

Sei file in `tests/golden/` — tre formati × due referti sintetici — più sette
test in `tests/test_golden.py`. Nessuna riga di codice di produzione è
cambiata.

**Il dataset dichiara il proprio ambiente, non lo eredita.** È la decisione
che regge tutto il resto. Su questa macchina Lighthouse, ZAP, Playwright e
sentence-transformers sono *tutti installati*; su un runner nudo nessuno.
Misurato: lasciando decidere all'ambiente, l'area sicurezza scrive nel referto
la issue «Header non leggibili: **NienteRete**» — cioè **il nome di una
fixture del banco di prova finisce dentro il golden**. Un golden costruito
così misurerebbe quali strumenti mancano su una macchina, non come si rende un
referto.

**E non si costruisce a mano.** La strada opposta — scrivere `results` a
mano, come fa la fixture di `test_report.py` — congelerebbe una forma che i
moduli non producono più: è R33, già registrato per la costante `CONTROLLI`
di quel file, ferma a cinque campi su otto. La via presa è la terza: i moduli
**veri**, con l'uscita dello strumento iniettata **alla sua cucitura di I/O** —
`run_axe`, `run_zap`, `context["_zap_client"]`, `context["_anthropic_client"]`,
tutte cuciture già usate dai test di modulo. `mars_seo` passa da
`riassumi(_lhr())`, che è ciò che `audit()` restituisce verbatim.

**I moduli si prendono da `load_external_module`, non da un `import`**, ed è
una trappola che sarebbe costata caro: il caricatore **sostituisce** l'oggetto
in `sys.modules`, quindi `import mars_wcag` e il modulo che gira **non sono lo
stesso oggetto** (verificato: `m is mars_wcag` → `False`). Una patch applicata
all'oggetto importato non arriverebbe, `axe_disponibile()` resterebbe `False`
per via della fixture, e il golden congelerebbe **il ramo di ripiego** senza
che nulla sollevi. È R20 in abito nuovo.

**Anche l'ultima area passa dal codice di produzione.** `mars_llm_judge`
importa `anthropic` *dentro* il percorso di successo: scriverne a mano il
risultato avrebbe reintrodotto R33 sull'unica area rimasta — e infatti un
prototipo scritto a mano sbagliava su quattro punti, fra cui il nome del
modello e la chiave `status`. Si stubba invece **la libreria** in `sys.modules`,
con lo stesso schema con cui `conftest.py` rende non importabile
`playwright.sync_api`, e il giudizio entra nel golden per la sua strada vera.

**Due referti e non uno.** Ci sono rami che nessun singolo referto può
contenere insieme: un'area misurata e la stessa senza strumento, il giudizio
LLM reso e disattivato, robots rispettato e ignorato, la sezione RRF presente
e assente. Il degradato accende **tre rami con un fatto solo** — `mars_semantic`
che solleva dà l'area in `error`, la sezione RRF che sparisce e il quadrante
«In forma di risposta» non misurato. I due insieme coprono **tutte e nove le
aree del registro e tutte e cinque le voci di `STATO_LEGGIBILE`**, e questo è
**asserito**, non sperato: un'area nuova o uno stato nuovo diventano rossi
invece che invisibili.

**Iniezione dei campi volatili, non sostituzione a valle.** `generated_at` e
`version` si scrivono nel referto *prima* di renderlo. Il `_normalizza` del
progetto di riferimento sostituisce la forma JSON `"generated_at": "…"` — in
MARS il timestamp esce **nudo** dentro un `<p class='meta'>`, quindi copiarlo
avrebbe lasciato l'HTML volatile senza che nessuno se ne accorgesse fino al
primo cambio di fuso. E l'iniezione congela anche **il punto** in cui il campo
compare: spostare la data nel piè di pagina — cosa che la Fase 11 prevede —
è un diff di due righe invece che nulla. Il valore è plausibile
(`2026-01-01T00:00:00+0000`, `0.0.0`) e non un segnaposto: un renderer futuro
che formattasse la data cadrebbe su `GENERATED_AT`.

**Due normalizzazioni per rendere il diff leggibile, ed è il punto della
fase.** `render_html` è un `"".join()`: tutto ciò che segue `</style>` era
**una riga sola da 13 KB**, e il criterio di accettazione — «un carattere di
CSS fa fallire con diff leggibile» — sarebbe stato soddisfatto per il solo
CSS, che porta gli a-capo suoi. Si spezza fra un tag e l'altro **prima di
scrivere il golden**, non solo prima di mostrare il diff: il mezzo della
revisione è `git diff tests/golden/`, e su una riga da 13 KB la revisione non
è possibile — il presidio diventerebbe un rito. Misurato: 88 righe con la più
lunga da 12 958 caratteri diventano **515 righe con la più lunga da 182**.
La favicon, 3 773 caratteri di base64 sulla stessa riga, diventa un digest:
un cambio d'icona resta rilevato, il diff resta leggibile.

Limite dichiarato: il file su disco non è più byte per byte ciò che
`render_html` emette, e un a-capo *letterale* fra due tag sarebbe invisibile.
È l'unico angolo cieco e non riguarda nulla che il renderer faccia oggi.

**`.gitignore` ignorava il golden JSON.** Verificato:
`git check-ignore -v tests/golden/referto.json` → `.gitignore:16:referto.json`.
Quella riga non ha `/`, quindi vale a ogni livello. Senza l'eccezione il
golden si sarebbe rigenerato in locale, il test sarebbe passato sulla macchina
di chi l'ha scritto, e **il file non sarebbe mai arrivato in CI**. Trappola da
conoscere: `git check-ignore` **con `-v` esce 0 anche su una regola di
negazione** — la prova è senza `-v` (deve uscire 1), o `git add -n`.

**Il criterio di accettazione è un test, non una nota.** Un carattere di CSS
cambiato con `monkeypatch` — non con un `sed` sul file, così il repo resta
pulito anche se il test fallisce a metà — deve produrre un diff, e un diff
**leggibile**: 11 righe, la più lunga da 74 caratteri.

Otto mutazioni sulla resa, tutte colte: il carattere di CSS, il taglio delle
issues nel testo, una parola del vocabolario degli stati, la precisione dei
quadranti SVG, la larghezza della colonna dei nomi d'area, il separatore fra i
qualificatori, una chiave sparita da `Finding.as_dict()`, un peso della scala
canonica. Due erano mal costruite alla prima stesura — cercavano stringhe che
nel file non esistono — e sono state rifatte sul testo vero.

**Che cosa il golden NON è**, scritto qui perché non lo si scopra rigenerando:
è un golden **della pipeline**, non dei soli formati. I risultati d'area
vengono dai moduli veri, quindi un punteggio che cambia fa fallire tutti e sei
i file. È il prezzo della fedeltà, ed è dichiarato nel README: la
rigenerazione non è il rimedio, è il primo di due passi — il secondo è
`git diff tests/golden/`, ed è lì che si distingue una resa cambiata da una
misura cambiata.

- [x] `tests/test_golden.py`, sei golden, `.gitignore`, README e CLAUDE.md.

### U3.1 — ✅ (2026-08-24): il catalogo dei testi di correzione

**Il problema.** I moduli dicevano *che cosa* è rotto e mai *come* si
aggiusta. I `Finding` hanno i campi `fix` ed `example` dalla Fase 1, e sono
rimasti vuoti in tutti tranne uno: `mars_wapt`, che la `solution` la prende
da ZAP. Venticinque controlli senza una riga di prescrizione.

**Il catalogo sta in un file suo**, `mars_fixes.py`, e non dentro i moduli.
Tre ragioni: la Fase 9 tradurrà **per chiave** da un catalogo, e con i testi
sparsi in sei moduli l'italiano vivrebbe in due forme che divergono senza che
nulla si rompa; un catalogo si legge *come catalogo*, che è l'unico modo di
accorgersi che due controlli vicini dicono la stessa cosa in due modi; e i
moduli restano plugin — **non importano il catalogo**, che si applica fuori,
nell'imbuto di `normalizza_risultato`, quindi il contratto
`audit(context) -> dict` non cambia (principio 3).

In Python e non in JSON: un file di dati assente o illeggibile darebbe un
referto con tutti i `fix` vuoti e **nessun errore**, che è la degradazione non
dichiarata che il principio 2 vieta. E gli esempi sono multiriga: in JSON
diventerebbero stringhe con `\n` letterali, irrivedibili in un `git diff` —
cioè fuori dal presidio che U2 ha appena montato.

**Il modulo vince, il catalogo colma.** Si scrive solo dove il rilievo ha il
campo vuoto: è ciò che permette a `mars_wapt` di conservare la `solution` di
ZAP (verificato nel golden: «Convalida l'input e codifica l'output.» resta
quella dello strumento) e a un plugin di terzi di portare i propri testi senza
sapere che il catalogo esista.

**Chi riceve un fix, e perché non tutti.** La regola è una: *riceve un `fix`
soltanto il rilievo che descrive uno stato del sito che chi lo possiede può
cambiare*. Ne discendono tre esclusioni, ed è un test a farle rispettare:

- i `*.status.*` sono fatti sulla **scansione**. «Lighthouse non trovato nel
  PATH» ha un'azione ovvia, ma è un'istruzione per chi fa girare MARS: il
  `fix` finisce nel piano di interventi e nel CSV, che si consegnano a un
  cliente, e un piano che dica «installa Lighthouse» ha sbagliato
  destinatario;
- i rilievi di `mars_citability` portano `derived`: ridicono un difetto già
  quantificato dall'area d'origine, e prescriverlo due volte gonfierebbe il
  piano;
- le tre famiglie dinamiche prendono il testo **dallo strumento**.

**Due fix del progetto di riferimento sono stati bocciati**, non riusati:

- «Verifica che l'esclusione sia voluta» per `tech.index.noindex` è una
  *domanda*, e là sta sotto un `warning` mentre in MARS lo stesso rilievo è
  **critico** quando tutto il sito è deindicizzato. Riscritto all'imperativo;
- il fix di `sd.jsonld.missing` elencava i tipi Schema.org da aggiungere, ma
  `mars_schema` **non guarda i tipi**: verifica che i blocchi si analizzino
  (I11 è ancora aperta). Prescrivere più di quanto si misuri è la falsa
  precisione che il principio 5 vieta.

**L'esempio di robots.txt non correggeva il difetto**, ed è il caso in cui per
poco non cascavo. L'esempio riusato mostra tre blocchi permissivi; chi lo
incollasse **in coda** al proprio robots.txt — la lettura naturale, ed è
quella che l'esempio gemello della sitemap prescrive esplicitamente —
resterebbe bloccato, perché `RobotFileParser` tiene il **primo** gruppo che
nomina quell'agente. Il proprietario crederebbe di aver corretto e la
scansione successiva direbbe di no, senza modo di capire perché. Ora l'esempio
mostra la **sostituzione**, e c'è un test di andata e ritorno che lo dà in
pasto a `controlla_robots` e verifica che il rilievo si chiuda. Stessa prova
per l'esempio di robots.txt completo e per il blocco JSON-LD.

**Due esempi portano un'avvertenza dentro il fix**, e non è formalità:
`Content-Security-Policy-Report-Only` **non chiude** il rilievo — il controllo
cerca la chiave esatta — e il fix lo dice; HSTS è **irrevocabile** per tutta
la durata di `max-age`, quindi l'esempio parte da un giorno e il fix dice di
aggiungere `includeSubDomains` solo dopo aver verificato i sottodomini.

**Nessuna interpolazione, e una formulazione per chiave.** Il catalogo si
applica dove i moduli non ci sono più: un fix che nominasse GPTBot dovrebbe
leggere i params. Il fix dice *che cosa fare*, il titolo e i params dicono *a
chi* e *quanto*. E `tech.index.noindex` è critico o grave a seconda di quante
pagine sono escluse: il testo è scritto per reggere entrambi i casi, perché un
catalogo `chiave → {gravità → testo}` raddoppierebbe le voci da tradurre nella
Fase 9 per una sfumatura che la prescrizione non cambia.

**La prova che la divisione in tre serviva**: dei sei golden ne cambiano
**due**, i `.json`, e il loro diff è di 34 righe modificate e 34 aggiunte —
tutte e sole `"fix"` ed `"example"`. Testo e HTML sono **byte per byte
identici**: nessuna resa è cambiata, quindi in questo commit si rivede la
prosa e basta.

Nove mutazioni, tutte rilevate. Due erano mal costruite alla prima stesura —
una era il doppione di un'altra (il codice sta in `mars_fixes`, non in
`mars_core`) e una cercava una stringa con l'indentazione sbagliata: rifatte.

I due dataset dei golden esercitano **dieci** delle venticinque voci: le altre
quindici non le vedrebbe nessuno finché un sito reale non le accende, e per
questo un test le guarda tutte — lunghezza, imperativo, nessuna domanda.

- [x] `mars_fixes.py`, `vesti_findings()`, quindici test, i due golden JSON.

### U3.2 — ✅ (2026-08-24): i testi che vengono dagli strumenti

**Il problema.** U3.1 ha escluso dal catalogo le tre famiglie dinamiche —
`wcag.axe.*`, `sec.zap.*`, `seo.lh.*` — perché il testo lo conosce lo
strumento, non noi: le regole di axe sono oltre cento e la regola violata la
sa lui. Ma di quei testi ne veniva raccolto **uno solo**, la `solution` di
ZAP. L'italiano di axe stava dentro `node_modules` senza che nessuno lo
aprisse, e la `description` di Lighthouse veniva letta e buttata via da
`estrai_audit`.

**Una regola sola, misurata su tre strumenti: la spiegazione va in `detail`,
la prescrizione in `fix`.** Non è una convenzione decisa a tavolino, è ciò che
i testi dicono quando li si legge:

- **Lighthouse** — dei suoi undici audit SEO, **nove spiegano perché il
  controllo conta** («I motori di ricerca non sono in grado di includere le
  pagine nei risultati di ricerca se non dispongono dell'autorizzazione…») e
  solo `crawlable-anchors` e `structured-data` prescrivono qualcosa. Quel
  testo dentro `fix` sarebbe il piano di interventi della Fase 4 che, alla
  voce *come si aggiusta*, spiega il problema. Va in `detail`;
- **axe** — delle 103 regole del locale italiano 4.13.0, **100 cominciano con
  "Assicurati"**. È un imperativo, ed è anche più specifico del titolo, che
  degli elementi e delle vie d'uscita non dice nulla: «Assicurati che gli
  elementi `<img>` abbiano un testo alternativo **o un ruolo none o
  presentation**». Va in `fix`;
- **ZAP** — i due campi li tiene già separati lui, `description` e
  `solution`, e restano separati nel rilievo.

**Il Markdown di Lighthouse.** Le `description` arrivano da `--locale=it`, e
l'unica sintassi che usano davvero è il link: misurati, dieci degli undici
audit ne hanno **uno**, `structured-data` ne ha **due**, di cui il primo a
metà frase. Si tiene l'etichetta e si toglie l'URL — buttare via anche
l'etichetta lascerebbe una frase monca proprio in quei due — e gli URL
finiscono in `params["references"]`, **lista e non `Finding.url`**, che è la
stessa decisione presa in U1.6 per i `reference` di ZAP e per lo stesso
motivo: i link possono essere più d'uno, e sceglierne uno nasconde gli altri.

Un limite è dichiarato e verificato da un test: l'URL si ferma alla prima
parentesi, quindi un link a una voce di Wikipedia con le parentesi nel titolo
**resta nel testo com'è**. L'alternativa — un `[^)]+` avido — lo
riconoscerebbe e ne troncherebbe l'URL, lasciando `)` appeso in mezzo alla
frase e un riferimento che non si apre.

**Il locale di axe si legge in Python, non nel browser.** axe accetta un
`axe.configure({locale})`, che tradurrebbe anche i titoli. Non si è fatto per
due ragioni: `score_from_violations` resta una funzione pura, verificabile
senza avviare nulla; e un locale illeggibile costa **i testi e non la
misura**, mentre dentro la pagina farebbe fallire `axe.run` e con lui l'intera
area. È il principio 2 applicato al posto giusto.

**La degradazione è dichiarata**, con lo stesso argomento per cui `mars_fixes`
è un file Python e non un JSON: senza il locale i rilievi axe resterebbero
senza `fix`, e **un campo vuoto sembra un campo che non serviva**. Nasce
`wcag.status.no_fixes`, che si accende solo quando costa qualcosa — cioè
quando ci sono violazioni da vestire — ed è un **rilievo e non una issue**, a
differenza di `wcag.status.partial`: la riga compatta elenca ciò che non va
nel *sito*, e una scansione parziale ci sta perché cambia come si legge il
punteggio; questa no, il punteggio è lo stesso e mancano le istruzioni.

Il suo `detail` porta il percorso **relativo** e non `AXE_LOCALE`, che è
assoluto: un referto si consegna a un cliente, e la struttura delle directory
della macchina che ha fatto girare la scansione non è un suo problema. È la
stessa regola per cui `detail` non porta mai il proxy o la chiave di ZAP.

**La misura che ha cambiato il progetto: la suite era diventata dipendente
dalla macchina.** Spostando `AXE_LOCALE` su un file inesistente — cioè
simulando un clone appena fatto, senza `npm install` — **cinque test di
mars_wcag diventavano rossi**: il rilievo di stato in più spostava indici e
conteggi. Verdi qui, rossi altrove, e nessuno se ne sarebbe accorto fino alla
prima CI.

La cura è `locale_axe_fisso` in `conftest.py`, autouse, che fissa due testi
veri di axe-core. Fissa un locale **presente** e non assente come fanno
Lighthouse, ZAP e il browser, perché i casi non si somigliano: quelli sono
strumenti che si installano a parte, questo è un file dentro lo stesso
pacchetto npm di `axe.min.js`, che `axe_disponibile()` già pretende. In
produzione, se ci sono violazioni axe c'è quasi sempre anche il locale, e una
suite che desse per normale il contrario proverebbe ogni volta il ramo
eccezionale. Il ramo del locale assente si prova dove va provato: chiedendolo.

E la fixture è **presidiata**, perché su questa macchina la sua assenza è
invisibile — i testi arriverebbero dal file vero e i test resterebbero verdi
lo stesso. Un test asserisce che durante la suite `testi_axe()` valga
esattamente i due testi fissati, 2 regole e non 103: è la regola del guardiano
rilevabile solo se qualcosa prova a passargli davanti. `testi_axe` è
memoizzata; per poterla verificare la lettura vera è stata separata in
`_leggi_locale_axe(percorso)`, che una cache non ce l'ha e si può quindi
interrogare due volte su due file diversi.

**Il golden.** Dei sei ne cambia **uno solo**, `referto.json`: 62 righe
aggiunte e 26 modificate, tutte e sole `detail`, `fix` e `references`. Testo e
HTML **byte per byte identici**, come U3.2 prometteva — la resa tocca a U3.3.
Nel diff si vede anche la scelta di lasciare `label` fuori dal locale fissato:
è la regola che il locale non conosce, e nel referto congelato si legge come
`fix` vuoto invece che come niente.

Le fixture sono diventate più fedeli, non solo più ricche: gli undici
`description` di `_lhr()` sono **verbatim** dal locale italiano di Lighthouse
13.4.1, coi link Markdown dentro — riscriverli a mano vorrebbe dire inventare
il Markdown che si dice di saper ripulire — e un test ricompone i letterali e
li confronta col file vero. Lo stesso per i due testi axe di `conftest`.

**Ventidue mutazioni, nessuna sfuggita**, compresa quella sulla fixture nuova.

**Una scelta consapevole nel dato**: `audits` continua a portare la
`description` **grezza**, col Markdown, mentre i `findings` portano quella
ripulita. È l'estrazione verbatim del LHR, la stessa regola per cui `score`,
`scoreDisplayMode` e `weight` compaiono in tutt'e due i posti.

**Trovato e non chiuso**: nel ramo axe i titoli del referto sono **in
inglese**. Verificato caricando `axe-core` in node: `getRules()` restituisce
«Active `<area>` elements must have alternative text». La fixture del golden
lo nasconde, perché i suoi `help` sono già in italiano. Tradurli sposterebbe i
golden di testo e HTML, quindi non è materia di U3.2: è **R44**.

- [x] `mars_wcag.py` (locale + `no_fixes`), `mars_seo.py` (Markdown +
      `detail`), `mars_wapt.py` (`detail`), `conftest.py`, 23 test nuovi,
      un golden.

### U3.3 — ✅ (2026-08-24): la resa dei testi di correzione

**Il problema.** Dopo U3.1 e U3.2 i `fix`, gli `example` e i `detail` erano nel
dato e in nessuna vista: solo il JSON li mostrava, perché li mostra tutti per
costruzione. Il referto HTML — quello che si consegna — continuava a dire
*che cosa* è rotto e mai *come* si aggiusta.

**Non esiste una chiave fra `issues` e `findings`, ed è questa la scoperta che
ha deciso la forma.** Sembrano due viste della stessa cosa e non lo sono:

- **per posizione** si disallineano appena axe o ZAP superano le cinque
  regole, perché le issues si fermano a cinque e i rilievi no. Non è un caso
  di laboratorio: è quasi ogni sito reale, e il guasto sarebbe *silenzioso*;
- **per somiglianza del testo** fallisce su `mars_schema`, dove la issue dice
  «JSON-LD malformato su `<url>`» e il titolo «1 blocchi JSON-LD malformati»:
  nessuna delle due contiene l'altra;
- `mars_citability` ne ha 2 contro 4, `mars_llm_judge` riuscito 3 contro 0.

L'unica area con una chiave vera è `mars_seo`: `params["rule"]` **è** l'id
dell'audit Lighthouse. E infatti è l'unica in cui la spiegazione sta **in
linea**, sotto la voce del controllo — non per estetica, ma perché lì unire i
due elenchi non richiede di indovinare.

**Dove non c'è chiave, il blocco è separato.** «Come si aggiusta» sta sotto
l'elenco dei rilievi e ne ripete i titoli. La ripetizione è il prezzo di una
scelta dichiarata: le `issues` sono la vista compatta che ogni modulo compone
per sé, e portano cose che il rilievo tiene nei `params` — «(2 elementi su 1
pagine)», «[1.1.1]», l'URL del blocco malformato. Sostituirle coi titoli dei
findings le perderebbe; **ricostruirle nel referto dai params significherebbe
riscrivere lì la presentazione che sta nei moduli**, cioè la solita coppia di
implementazioni che divergono in silenzio.

**Due difetti visti nel diff del golden, non nel codice.** È esattamente ciò
per cui U2 esiste:

- il blocco stampava `source_severity` come etichetta accanto al titolo —
  «critico», «axe:critical» — che sta **già** nella riga della vista compatta
  due centimetri più su. Terza volta che la stessa scheda dice la stessa cosa:
  tolto;
- l'area **in errore** finiva sotto «Come si aggiusta»: `_finding_errore`
  mette il messaggio dell'eccezione in `detail`, e il blocco accettava chi
  avesse un `detail` qualunque. «MemoryError: corpus troppo grande» non
  aggiusta niente. Ora serve un `fix` o un `example`, e la stessa condizione
  tiene fuori `wcag.status.no_fixes`, che è un'istruzione per chi fa girare
  MARS — la stessa esclusione che regge il catalogo di U3.1.

**Il vincolo di «Nessun rilievo.», rispettato.** Il ramo si accende solo quando
l'area non ha **né** issues **né** findings. Guardare i soli findings farebbe
dire «Nessun rilievo.» al giudizio LLM riuscito, che ne elenca tre e findings
non ne produce per scelta di U1.9. Nei due golden quel ramo non compare mai —
lo provano due test, e due mutazioni lo confermano.

**Anche la vista testo, e con la stessa forma.** Qui la prima stesura si era
fermata all'HTML, con l'argomento che le righe compatte portano i conteggi di
diffusione e il criterio WCAG e che il «come si aggiusta» nel terminale poteva
aspettare U4. UPGRADE.md, Fase 3, chiede però esplicitamente una riga
`-> Fix: …` sotto il rilievo: l'argomento era buono per *sostituire* le
issues, non per non aggiungere nulla, e chi usa la CLI non avrebbe mai visto
una prescrizione. Ora ogni area mostra fino a **due** correzioni — titolo e
poi prescrizione, come nell'HTML e per la stessa ragione: senza il titolo, un
`->` appeso sotto due issues lascerebbe indovinare a quale si riferisca.

L'`example` resta fuori dal solo testo: sono blocchi nginx e JSON-LD di
cinque o sette righe, e due per area triplicherebbero un referto che sta in un
terminale. Nell'HTML e nel JSON ci sono per intero.

**Si muovono quattro golden su sei**: i due `.html` e i due `.txt`, +14 righe
ciascuno. Il JSON non si muove — il dato era già tutto lì dalla Fase 1, ed è
la conferma che questo commit contiene soltanto resa.

**Ventuno mutazioni, nessuna sfuggita** — comprese le due che riportano
«Nessun rilievo.» a guardare un elenco solo, quella che aggancia la
spiegazione dei controlli per posizione invece che per id, e quella che toglie
il tetto di due alla vista testo.

- [x] `_correzioni()`, `_correzioni_testo()`,
      `_elenco_controlli(controlli, rilievi)`, il CSS (`.correzioni`,
      `.spiegazione`, `.fix`, `pre.ex`), quindici test, quattro golden.

### U3 — ✅ CHIUSA (2026-08-24): `__version__` a 2.2.0

Ultima voce della fase, come per la Fase 1: il bump minore, e la riga di
versione del README che dice che cosa la 2.2.0 porta. `USER_AGENT` segue —
il crawler si presenta ora come `MARSBeacon/2.2.0`.

**Numeri della fase, misurati e non stimati.** Cinquantadue mutazioni nei tre
commit — 9 in U3.1, 22 in U3.2, 21 in U3.3 — tutte rilevate. La suite passa
da 559 a 612 test. I golden si sono mossi **una
volta ciascuno**: i `.json` in U3.1 (i testi del catalogo), il solo
`referto.json` in U3.2 (i testi degli strumenti), i `.html` e i `.txt` in
U3.3 (la resa). È la divisione in tre che rende leggibile ciò che altrimenti
sarebbe stato un unico diff di settecento righe per metà golden.

**Che cosa la fase ha aggiunto al referto.** Venticinque controlli hanno un
`fix` scritto a mano e diciannove un `example` incollabile; le tre famiglie
dinamiche prendono il testo dallo strumento, con una regola sola — la
spiegazione in `detail`, la prescrizione in `fix` — misurata su tutti e tre.

**Che cosa la fase ha lasciato aperto**, e sta scritto dove si trova:
**R44** (i titoli axe in inglese) e la scelta, deliberata, che
`mars_citability` non prescriva nulla perché ridirebbe ciò che l'area
d'origine ha già quantificato.

### U4.1 — ✅ (2026-08-25): il piano di interventi, come funzione pura

**Il problema.** Fra «elenco dei difetti» e «che cosa faccio lunedì mattina»
non c'era nulla. Le prime tre fasi hanno reso i rilievi un dato con gravità,
penalità e prescrizione: qui diventano un elenco **ordinato**, e ogni voce
dichiara quanto si guadagna a chiuderla.

**Il numero che il piano pubblica è il RECUPERO, non la penalità**, ed è il
difetto più facile dell'intera fase:

    recupero = R(base − penalità) − R(base),  R(P) = max(0, round(100 − P))

`base` è la somma delle penalità dichiarate da **tutti** i rilievi dell'area,
`info` compresi — nel golden `mars_tech` fa 40 (critico) + 3 (un `info`) = 43,
e R(43) = 57 = il punteggio pubblicato; sommando i soli candidati verrebbe 60 e
la ricostruzione si romperebbe in silenzio. Due conseguenze misurate:

- **un'area satura vale meno di quel che sembra**: con base 108 e score 0 un
  rilievo da 40 ne recupera 32, e uno da 8 non muove niente;
- **i recuperi non sono additivi**: su `mars_wcag` del golden, 37 + 18 + 7 uno
  alla volta fanno 62, chiudendoli insieme si guadagnano 63. Ogni voce porta
  `additive: False` **nel dato** e non solo nella resa, perché il CSV della
  Fase 6 e il confronto della Fase 7 sommeranno ciò che trovano.

**Il certificato d'area.** U4 è il **primo consumatore** di
`params["penalty"]`: fino a qui quel campo lo leggevano solo i test, e la
coerenza fra penalità e punteggio non l'aveva mai verificata nessuno. Ora un
gate per area lo pretende, e un test lo esercita su tutte e nove le aree con
penalità dei due golden. Un'area non certificata **tiene le sue voci e perde i
numeri**: recupero e guadagno spariscono dichiarandolo.

Il gate ha un ramo apposta per le aree sature, e non è un dettaglio: con score
già a 0 il confronto `round(100 − base) == round(score)` è falso per
costruzione — 100 − 154 fa −54 — e senza quel ramo un'area satura perderebbe
tutti i suoi numeri proprio dove servono di più. L'eccedenza si pubblica,
perché è ciò che spiega perché un rilievo da 40 ne recuperi 32.

**Il guadagno di citabilità è una derivata.** L'indice composito è una media
pesata di medie pesate, lineare nei segnali: la derivata rispetto al punteggio
di un'area è un numero solo, e il guadagno è `recupero × k[segnale]`. I `k`
**non sono costanti** — dipendono dal mercato e da quanti segnali sono stati
misurati in quella esecuzione: misurato, `tecnica` vale 0,1885 nel referto
completo (mercato `eu`, 7 segnali) e 0,4045 in quello degradato (`global`, 4).
Per questo ogni voce porta con sé il mercato, e confrontare due `index_gain` di
referti diversi non significa niente. Verificato contro il modulo vero: la
derivata ricostruisce il movimento dell'indice a meno dell'arrotondamento, che
può valere **due passi** (0,2) perché il modulo arrotonda i profili a 0,1 e poi
di nuovo l'indice.

**Quattro corsie, perché «non lo so» e «so che vale zero» sono opposti** per
chi decide lunedì mattina: `misurato`, `bloccato` (area satura), `ignoto`
(penalità assente), `nullo` (penalità 0,0 dichiarata). La corsia viene **prima
dei numeri** nella chiave d'ordinamento, così nessun confronto numerico
incontra un `None` — e senza, due voci in corsia `ignoto` solleverebbero
`TypeError` su `-None`, cioè dopo che tutte le aree hanno girato.

**Lo sforzo è un catalogo chiuso** sulle 25 chiavi di `mars_fixes`, e un test
pretende che i due insiemi coincidano: un controllo con un `fix` e senza sforzo
non potrebbe mai essere un quick win, uno con lo sforzo e senza `fix`
prometterebbe un intervento che il referto non sa descrivere. Le tre famiglie
dinamiche restano fuori tutte e tre — un default «ore» sarebbe un'assenza
travestita da stima, e le loro chiavi non sono nostre.

**Il quick win vuole tre condizioni**, non due: critico, da minuti, **e con un
recupero che esiste davvero**. Il terzo termine non è pignoleria — nel golden
completo `wcag.img.alt_missing` e `wcag.form.label_missing` sono critici con
penalità 0,0, perché in quel ramo il punteggio lo fa axe: senza, il piano
aprirebbe con due vittorie rapide che lasciano l'area dov'era.

**La ricognizione, e che cosa ha smentito.** Il progetto è stato preceduto da
dodici agenti in sola lettura — sei letture parallele, tre proposte
indipendenti, una sintesi, due critici avversariali — per circa 50 minuti e
1,4 milioni di token. I due critici hanno prodotto **18 obiezioni, tutte
verificate sul codice**, e due erano bloccanti:

- la sintesi proponeva una chiave pubblica nuova, `citability["sensibilita"]`,
  giustificandola con «`import mars_citability` non funzionerebbe, perché
  `load_external_module` sostituisce l'oggetto in `sys.modules`». **Falso**, e
  riverificato di persona: gli oggetti-modulo sono due, ma `PESI_ASSISTENTE`,
  `MERCATI` e `SEGNALI` sono uguali. Sono caduti due commit su otto;
- gli `index_gain` erano dichiarati additivi. Non lo sono: sono `recupero × k`,
  e se il fattore non è additivo non lo è il prodotto.

**Una cosa che nessun agente aveva visto**, trovata verificando: il referto
pubblica `citability["signals"]` indicizzato per **etichetta italiana**, non
per nome interno. `mars_remediation` inverte `SEGNALI` per tornare ai nomi, ed
è l'unico aggancio fragile del modulo: la Fase 9, traducendo le etichette, lo
romperebbe. Non in silenzio — su un'etichetta non riconosciuta i coefficienti
diventano `None`, i guadagni spariscono e l'ordinamento degrada sul recupero.

**Il modulo non è un'area** e non sta in `MODULES_REGISTRY`: non espone
`audit()`, non misura niente, rilegge il referto quando tutte le aree hanno
parlato. Il precedente è `mars_fixes`, con una differenza: lì l'import è
tollerante perché il catalogo è prosa editoriale e la sua assenza degrada un
referto che resta vero; qui sarà **duro**, perché il piano è dato canonico e la
sua assenza deve rompere invece di produrre un referto silenziosamente monco.

Quarantasette test, **ventitré mutazioni, nessuna sfuggita**. Due erano
sfuggite al primo giro, ed erano difetti del banco di prova: la prova
sull'etichetta ignota le passava *tutte* ignote, dove il codice restituisce
`None` per un'altra strada, e nessun caso metteva due voci pari-gravità in
corsie diverse.

- [x] `mars_remediation.py`, `tests/test_remediation.py`. In questo commit il
      piano non è ancora nel referto: si prova la funzione.

### U4.2 — ✅ (2026-08-25): il piano entra nel dato canonico

`build_report` guadagna la chiave `remediation`, e la costruisce **per
ultima**: il piano rilegge il referto — gli servono le aree, per le penalità e
i punteggi, e la citabilità, per i coefficienti — quindi non può stare dentro
il letterale che le definisce. Costruito lì dentro le troverebbe assenti e
uscirebbe senza guadagni, **senza un solo errore**: due mutazioni lo
verificano, una che gli toglie le aree e una che gli toglie la citabilità.

**L'import di `mars_remediation` è duro**, a differenza di quello di
`mars_fixes` in `normalizza_risultato`. La differenza è il tipo di dato: quello
è un catalogo di prosa editoriale, e la sua assenza degrada un referto che
resta vero; questo è dato canonico, e la sua assenza deve rompere invece di
produrre un referto silenziosamente senza piano.

**La chiave c'è sempre**, anche vuota, per la stessa ragione di `findings` in
U1.2: una lista vuota si consuma, una chiave assente fa cadere chi la legge —
e chi la leggerà sono il CSV della Fase 6 e il confronto della Fase 7, che
nascono dopo e non possono verificarla.

**Nessuna seconda copia.** Un test pretende che `referto["remediation"]` sia
esattamente ciò che `build_remediation` produce rileggendo quel referto: se un
giorno una vista lo ricostruisse per conto suo, le due copie divergerebbero
senza che nulla si rompa. È lo stesso argomento per cui la sezione citabilità
non avrà una `top_actions` duplicata.

**L'API non ha lavoro suo da fare** — `response_model=dict` lascia passare la
chiave intera — ma il test c'è lo stesso: `/audit/full` è l'unica delle tre
interfacce che non passa da `render_*`, quindi un piano costruito dentro una
vista invece che nel dato canonico sparirebbe proprio lì.

I due golden `.json` si sono mossi **solo** per la chiave nuova: 447 e 235
righe aggiunte, una sola riga tolta — la parentesi che chiudeva il documento.
Testo e HTML fermi, come previsto: la resa è U4.3 e U4.4.

Cinque mutazioni, nessuna sfuggita. Una era mal costruita alla prima stesura —
aggiungeva una chiamata senza spostare l'assegnamento, cioè un no-op
travestito da mutazione — e va registrata perché è la terza volta che quel
tipo di errore compare in un giro.

- [x] `mars_report.py`, cinque test in `test_report.py`, uno in `test_api.py`,
      i due golden JSON.

### U4.3 — ✅ (2026-08-25): il piano nella vista testo

La sezione sta fra il ciclo delle aree e quella dell'RRF, ed è **sempre
stampata, anche vuota**. Le altre tre spariscono quando manca il dato; qui
sarebbe un errore, perché un piano che sparisce non si distingue da un piano
non calcolato — è il principio 5 applicato alla sezione invece che al numero.

Mostra **cinque** interventi, come i cinque alert ZAP e le cinque violazioni
axe: è la stessa asimmetria di sempre fra la vista che sta in un terminale e il
dato che li porta tutti, e la riga di troncamento la dichiara. Ogni voce porta
gravità, area, sforzo, il recupero con i punteggi di partenza e arrivo — che
sono ciò che permette di rifare il conto leggendo il referto — il guadagno
d'indice, e la prescrizione.

Dove un numero non c'è, **al suo posto va il motivo**: «in questa esecuzione il
controllo non entra nel punteggio dell'area» invece di una riga vuota. Sono tre
motivi diversi, e la corsia sa quale.

**La duplicazione che si vedeva a occhio nudo.** Rigenerando i golden per la
prima volta, ogni correzione compariva **due volte in quaranta righe**: una
sotto la sua area, dalle righe `→` di U3.3, e una dentro il piano. In un
referto largo 55 colonne è insostenibile. Ora sotto l'area restano solo le
correzioni che il piano **non prende in carico** — i rilievi `info`, che il suo
filtro esclude — e che altrimenti sparirebbero dalla vista testo pur avendo una
prescrizione. Nessuna informazione persa, nessuna ripetuta: nel golden completo
sono `tech.canonical.missing` e `wcag.link.generic`.

Non è un ripensamento su U3.3: quelle righe erano la risposta giusta finché il
piano non esisteva. Ora esiste, ed è ordinato per valore.

**R42 rispettato in partenza**: la sezione si condiziona sul dato e mai sul
nome di un modulo, e un test lo verifica costruendo un rilievo che dichiara
`area: "un_plugin_di_terzi"`. È il difetto per cui `mars_citability` spariva
dalla vista testo — la si saltava per nome anche quando falliva.

Sedici mutazioni, nessuna sfuggita. Due erano mal costruite alla prima
stesura: toglievano il corpo di un `if` lasciando l'intestazione, quindi
rompevano la sintassi e non dimostravano nulla. Rifatte cambiando la
**condizione** invece del corpo.

- [x] `_piano_testo()`, `_voce_piano_testo()`, `_correzioni_testo(…,
      nel_piano)`, otto test, i due golden `.txt`.

### U4.4 — ✅ (2026-08-25): il piano nella vista HTML

Una scheda per intervento, nella stessa posizione della vista testo — dopo le
aree, prima dell'RRF — perché le due rese raccontino il referto nello stesso
ordine. Ogni scheda porta priorità, badge di gravità, area, sforzo, il quick
win, il recupero coi punteggi di partenza e arrivo, il guadagno d'indice e la
prescrizione.

**Qui non c'è il tetto di cinque della vista testo**: è il documento che si
consegna, e li porta tutti.

**Che cosa NON si ripete, e perché.** L'`example` resta alla scheda d'area:
sedici blocchi di codice dentro un elenco di priorità lo renderebbero
illeggibile proprio come elenco. Il `fix` invece si ripete, ed è una scelta
opposta a quella presa nella vista testo poche ore prima — là il referto è
largo 55 colonne e il lettore aveva le due righe sott'occhio insieme, qui sono
due sezioni di un documento lungo, e un intervento che non dicesse *che cosa
fare* manderebbe a cercarlo. Senza nemmeno un'ancora: quelle arrivano con la
Fase 5.

**I due numeri hanno statuto diverso, e il referto lo dice.** I punti d'area
sono la stessa aritmetica che ha prodotto i punteggi pubblicati; il guadagno
d'indice esce da una matrice di pesi editoriali, quindi è dichiarato *stima* e
porta con sé il mercato — lo stesso rilievo vale diversamente in due esecuzioni
con segnali misurati diversi.

**Una trappola dei selettori annidati, colta prima di consegnarla.** La scheda
riusa la classe `riga` delle schede d'area, ma il CSS la definiva come
`.area .riga`, cioè **ristretta**: dentro `.intervento` titolo e badge sarebbero
rimasti impilati invece che affiancati. Nessun test sul contenuto lo avrebbe
visto, perché l'HTML sarebbe stato identico. Il selettore ora copre entrambe, e
un test lo pretende.

Tredici mutazioni, nessuna sfuggita — compresa quella che restringe di nuovo il
selettore e quella che toglie la parola «stima».

Due test esistenti sono stati adeguati, e vale la pena dire perché: uno
costruiva un rilievo `critical` per provare il ramo «Nessun rilievo.», e da
oggi quel rilievo entra nel piano, cioè il test misurava due cose. Ora è
`info`, e ne misura una.

- [x] `_sezione_piano()`, `_voce_piano_html()`, il CSS (`.intervento`,
      `.priorita`, `.badge`, `.qw`, `.guadagno`), otto test, i due golden
      `.html`.

### R45 — ✅ (2026-08-25): due numeri sulla stessa area, e perché differiscono

**Il difetto, trovato sul campo.** Confrontando il referto di MARS con
PageSpeed Insights su un sito vero — `lymphatechnologies.com` — la differenza
era enorme e inspiegabile a chi legge: **Lighthouse 97 all'accessibilità,
MARS 59**. Non è un disaccordo sui fatti. Verificato eseguendo il Lighthouse
13.4.1 locale, lo stesso che MARS invoca:

- usano **lo stesso strumento**, axe-core, e hanno trovato **lo stesso
  difetto**, `color-contrast`;
- Lighthouse fa una **media pesata** su 76 controlli, 30 dei quali con peso,
  per un peso totale di 226: `color-contrast` pesa 7, cioè il 3%. Da lì il 97;
- MARS **sottrae penalità**: `color-contrast` è `serious`, 12 punti,
  moltiplicati per la diffusione — presente su tutte e 5 le pagine esaminate,
  quindi 2× — fa 24. Più `scrollable-region-focusable`, 12 × 1,4 = 16,8.
  Totale 40,8, da cui il 59.

Due differenze strutturali oltre alla scala: MARS guarda **5 pagine**,
Lighthouse **una**; e `scrollable-region-focusable` **non è nella categoria
accessibility di Lighthouse** — verificato sul LHR — quindi non ci sarebbe
entrato nemmeno guardando lo stesso campione.

Sull'unico numero che è la **stessa misura**, invece, non c'era alcuna
differenza: il SEO di MARS *è* il punteggio di Lighthouse, e valeva 100 per
entrambi.

**La decisione, presa dall'utente fra tre alternative** (lasciare e dichiarare;
ritarare `PESI_AXE`; pubblicare entrambi): **pubblicare entrambi i numeri con
la nota che il nostro è più restrittivo**. È la risposta che non tocca la
misura e non nasconde niente — chi apre PageSpeed accanto al referto i due
numeri li vede comunque, e tacerne uno non li rende uguali, li rende
inspiegabili.

**Costo zero, e una cosa che si buttava via.** `esegui_lighthouse` non passa
`--only-categories`, quindi Lighthouse calcola **tutte e cinque** le categorie
a ogni run — performance, accessibilità, best practices, SEO, agentic
browsing — e `mars_seo` ne teneva una, buttando le altre insieme al resto del
LHR. Ora le pubblica tutte in `lighthouse_scores`, e `mars_wcag` legge da lì
il numero che gli serve: **nessun secondo Lighthouse**, perché il modulo gira
dopo `mars_seo` in `MODULES_REGISTRY` — la stessa cucitura su cui poggia
`mars_citability`.

**Le chiavi sono generiche**, `reference_score` e `reference_tool`, non
`lighthouse_*`: il confronto non è una proprietà di quello strumento, e la
stessa forma servirà il giorno che un'altra area avrà un termine di paragone.

**Tracciabilità.** Il 97 compare nell'area accessibilità, ma è stato misurato
dal run pagato dall'area SEO: senza `lighthouse_scores` nel dato canonico non
ci sarebbe modo di risalire a chi l'ha prodotto. `build_report` copia una
lista chiusa di chiavi, quindi la prima stesura lo perdeva — è la lezione di
U1.2, ripresentatasi identica.

**La resa sta in `_qualificatori`**, condivisa fra testo e HTML, quindi le due
viste non possono divergere: «axe-core · WCAG 2.1 A + AA · 5 pagine
esaminate · Lighthouse 97/100 (1 pagina, scala diversa: la nostra è più
severa)».

Due dettagli che sarebbero passati: il confronto vale **anche nel ramo di
ripiego**, dove serve di più — lì il nostro numero è un controllo di
superficie e quello di Lighthouse no — e la condizione è `is not None` e non
la verità del valore, altrimenti **uno zero dell'altro strumento sparirebbe**,
cioè proprio il caso peggiore. Entrambi presidiati da un test e da una
mutazione.

La fixture `_lhr()` ora dichiara tutte e cinque le categorie, coi punteggi del
run vero: senza, `punteggi_categorie` sarebbe stata provata su un LHR che ne
dichiara una sola, cioè su una forma che non esiste.

Undici mutazioni, nessuna sfuggita. Golden mossi: quattro — i due `.json` e il
`.txt`/`.html` del referto completo.

**Non chiude la questione della scala**, e va detto: MARS resta molto più
severo, e un solo controllo violato su tutte le pagine costa un quarto del
punteggio. Ora però il referto lo dichiara, invece di lasciarlo scoprire a chi
confronta.

- [x] `punteggi_categorie()` in `mars_seo`, `punteggio_riferimento()` in
      `mars_wcag`, tre chiavi nel referto, `_qualificatori`, undici test,
      quattro golden.

### U4.5 — ✅ (2026-08-25) e chiusura della Fase 4: `__version__` a 2.3.0

**L'ultimo pezzo che la Fase 4 prometteva**: «Azioni con maggior guadagno di
profilo», sotto i profili di citabilità. Riordina il piano canonico per **solo
guadagno**, e non è lo stesso elenco dei primi interventi — là la gravità
domina, e un rilievo critico che muove poco sta comunque davanti a
un'avvertenza che muove molto. Qui la domanda è un'altra: fra tutti, quali
pesano di più su *questi* profili.

Ogni voce nomina **l'assistente che guadagna di più**, ed è l'unica cosa che
questa sezione dice e il piano no: i pesi per assistente sono diversi, quindi
la stessa correzione non vale uguale per tutti. Nel golden, togliere il blocco
a GPTBot vale +7,54 sull'indice ma +8,57 su Qwen.

**Nessuna chiave nuova nel dato.** UPGRADE.md prevedeva una `top_actions`
derivata accanto alla citabilità: non si fa, perché sarebbe una seconda copia
del piano che diverge in silenzio dalla prima. La sezione legge la lista
canonica e la riordina, come le viste fanno già con tutto il resto.

**Il vincolo R41 è ora scritto dove serve**: in UPGRADE.md, accanto alle Fasi
4, 5 e 7, cioè le tre che aggregano rilievi. Prima viveva solo in una voce del
TO-DO, che è il posto sbagliato per un vincolo che vale sul lavoro futuro.

**Il bump a 2.3.0, e una rete che mancava.** Il numero di versione vive in due
posti — `__version__`, che governa referto e `User-Agent` del crawler, e la
riga in testa al README — e alzarne uno solo non rompeva niente. È esattamente
la deriva fra documentazione e codice di R32. Ora un test li lega, e uno
verifica che lo `User-Agent` continui a portare il numero: entrambi nati da una
**mutazione sfuggita** al giro di U4.5, che nessun test presidiava.

Il banco di prova ha mostrato un suo limite: valida con `ast.parse` ogni file
mutato, quindi una mutazione su un `.md` viene scartata come «sintassi rotta».
Quella sul README è stata verificata **a mano** — applicata, test rosso,
ripristinata — invece di darla per buona.

Sette mutazioni più una a mano, nessuna sfuggita.

---

**La Fase 4 è chiusa.** Numeri misurati, non stimati: **cinque commit**
(U4.1-U4.5), la suite da 659 a 698 test, **sessantotto mutazioni** in tutto,
tutte rilevate. I golden si sono mossi una volta per commit — i `.json` in
U4.2, i `.txt` in U4.3, gli `.html` in U4.4 e U4.5 — che è la divisione che
rende rivedibile un diff altrimenti illeggibile.

**Che cosa la fase ha aggiunto al referto.** Un elenco ordinato di interventi
che, per ognuno, dichiara di quanto risale il punteggio dell'area se lo si
chiude, quanto ne guadagna l'indice di citabilità e su quale assistente, e
quanto costa in ordine di grandezza. In tutte e tre le viste, con una copia
sola del dato.

**Che cosa la fase ha lasciato aperto**, e sta scritto dove si trova: **R46**
(lo sforzo resta editoriale finché il conteggio delle istanze non è canonico),
la seconda casella di **R41** (i conteggi per gravità, che nascono nella Fase
5), e il widget «Top rilievi» in testa alla pagina, che UPGRADE.md lega
esplicitamente all'hero della Fase 5.

**Che cosa la fase ha dimostrato sul metodo.** Il progetto è stato preceduto da
una ricognizione di dodici agenti in sola lettura, e i due critici avversariali
hanno demolito due decisioni su undici — una delle quali poggiava su
un'affermazione **verificata falsa**. Senza quella verifica sarebbero nati due
commit inutili e una chiave pubblica in più nel dato canonico.

- [x] `_azioni_di_profilo()`, il vincolo su UPGRADE.md, `__version__` 2.3.0,
      il README, sette test, due golden `.html`.

### U5.1-U5.3 — ✅ (2026-08-25): complessivo, hero e ancore stabili

**U5.1 — il punteggio complessivo.** Media pesata delle sole aree **misurate**,
rinormalizzata su quelle presenti: un'area senza strumento non abbassa il
complessivo, lo rende meno informato — la stessa regola che `mars_citability`
applica ai suoi segnali. I due segnali derivati — consenso RRF e contenuto in
forma di risposta — pesano **1,5** contro l'1,0 di un'area, perché non vengono
da uno strumento esterno ma dal confronto fra i due recuperatori, che è la
domanda del progetto.

Citabilità e giudizio LLM sono esclusi **per nome** e non per una proprietà del
dato (D3), ed è deliberato: la prima è una sintesi dei punteggi altrui, il
secondo è opzionale e a pagamento — con dentro, lo stesso sito darebbe due
complessivi a seconda che si sia speso o no. Per nome restano fuori **anche
quando falliscono**, che è proprio il caso in cui una regola basata sul dato li
lascerebbe rientrare.

La chiave `overall` porta i **componenti e i pesi**: un numero che riassume
nove aree vale quanto la possibilità di rifarne il conto, e senza sarebbe
l'unica cifra del referto che nessuno può verificare. Nel golden completo:
(57 + 27 + 90 + 37 + 57 + 1,5·100 + 1,5·75) / 8 = **66,3**.

I due segnali derivati erano calcolati *dentro* la fascia dei quadranti:
estratti in `segnali_derivati()` e letti da entrambi. La prova che il refactor
è invariante è che l'HTML dei golden **non si è mosso**.

**U5.2 — l'hero, e i conteggi che chiudono R41.** Un numero, un verdetto, la
scala dichiarata e quattro caselle. Il quadrante è lo **stesso** `_quadrante`
della fascia sotto, solo più grande per CSS: disegnarne un secondo, anche
identico, vorrebbe dire avere due archi da tenere allineati.

I conteggi per gravità **escludono i derivati**: è la seconda casella di R41, e
con essa la voce si chiude. Contarli qui riaprirebbe sui *conteggi* il doppio
conteggio che D3 chiude sul *punteggio* — nel golden sono quattro rilievi su
dodici informativi. Il test costruisce un derivato **critico** apposta, perché
oggi li terrebbe fuori anche la sola gravità: è la protezione incidentale che
R41 denuncia.

I rilievi di **stato** restano dentro: dicono qualcosa di vero su questa
esecuzione, e la casella «informativi» non è una coda di lavoro — quella è il
piano, che li esclude.

Il **donut** previsto da UPGRADE.md diventa due numeri. La quota di URL
scartati non è un voto — un PDF o un altro host sono scarti legittimi — e un
anello la colorerebbe con la scala dei punteggi. Il taglio giusto (senza
rilievi / con rilievi / scartate) richiede i `url` valorizzati sui Finding, che
UPGRADE.md stesso dichiara assenti.

**U5.3 — le ancore, e una prescrizione che non serviva.** UPGRADE.md prevedeva
uno slug ricavato dal **titolo**, coi numeri normalizzati a `n` perché «2/3
pagine senza canonical» e «117/400 pagine senza canonical» non producessero due
ancore diverse. Qui non serve: dalla Fase 1 ogni rilievo ha già una `key`
stabile per costruzione — tre segmenti, mai un valore variabile dentro — ed è
esattamente il problema che quello slug cercava di risolvere a valle. Il
progetto di riferimento non aveva chiavi, noi sì. Un test verifica comunque la
proprietà che conta: cambiando solo i numeri del titolo, l'ancora non si muove.

Il punto diventa trattino: un id coi punti è legale in HTML5, ma
`#tech.robots.ai_blocked` in un selettore CSS si legge come un id più due
classi. Oggi nessuno lo interroga — nel referto non c'è JavaScript — e proprio
per questo conviene non lasciare la mina.

**Le ancore si calcolano una volta sola** e si passano a chi le usa: la scheda
che le emette, il piano e il riquadro «Da dove cominciare» che le linkano.
Ricalcolare la condizione in tre posti significherebbe tre occasioni di
divergere, e **un link rotto in un referto HTML non fa alcun rumore**: la
pagina resta valida, il browser non protesta, il salto semplicemente non
succede. Per questo l'invariante è un test: nel referto completo, 20 ancore
emesse e 20 link, zero rotti.

Riceve l'ancora solo il rilievo che la scheda d'area mostra come **elemento
proprio** — una voce di «Come si aggiusta», o una riga dell'elenco dei
controlli agganciata al suo rilievo. Dove non c'è, il piano stampa il titolo
senza link invece di promettere un salto verso il nulla.

Scrivendo quel test è emerso un fatto che avevo dato per scontato al contrario:
un rilievo *senza* `fix` non esiste quasi mai, perché `vesti_findings` glielo
riempie dal catalogo di U3.1. Il caso va costruito su una famiglia **dinamica**
— `wcag.axe.*` — che dal catalogo non prende nulla.

Trentadue mutazioni nelle tre voci, nessuna sfuggita.

- [x] `overall_score()`, `segnali_derivati()`, `conteggi_per_gravita()`,
      `_hero()`, `_ancora()`, `ancore_dei_rilievi()`, `_primi_rilievi()`, il
      CSS, ventotto test, i golden.

### R41 — ✅ CHIUSA (2026-08-25): `derived` ha finalmente dei lettori

**Il difetto.** Da U1.8 ogni rilievo di `mars_citability` porta
`params["derived"] = True` e nessuna `penalty`: sono sintesi, ridicono difetti
che altre aree hanno già misurato con più dettaglio. Il marcatore però **non
aveva un lettore** — `grep -rn '"derived"' *.py` trovava solo il modulo che lo
scriveva — e le tre guardie contro il doppio conteggio non erano equivalenti:
l'assenza di `penalty` protegge le *somme*, non l'*elenco*; e `severity: info`
è ciò che li escludeva davvero, ma è una protezione **incidentale**.

**Chiusa in due tempi, dai due consumatori che sono nati nel frattempo:**

- **U4.1** li esclude dal piano di interventi (`_e_candidato`);
- **U5.2** li esclude dai conteggi per gravità dell'hero
  (`conteggi_per_gravita`), che è il caso che la voce prevedeva: i sette
  `cit.*.unmeasured` e i `cit.*.weak` avrebbero gonfiato la casella «Info»
  accanto ai rilievi che ripetono, riaprendo sui *conteggi* il doppio
  conteggio che D3 chiude sul *punteggio*. Nel golden completo sono quattro
  rilievi su dodici informativi.

Entrambi i test costruiscono un derivato **critico** apposta, cioè uno stato
che oggi nessun modulo produce: senza, verificherebbero la protezione
incidentale invece di quella vera, e il giorno che un derivato nascesse
`warning` il conteggio si gonfierebbe in silenzio.

**Il vincolo è ora scritto dove serve** (U4.5): in UPGRADE.md, accanto alle
Fasi 4, 5 e 7 — le tre che aggregano rilievi — invece che in una voce del
TO-DO, che è il posto sbagliato per un vincolo sul lavoro futuro. Chi mostra i
rilievi uno per uno (elenco d'area, JSON, CSV) li tiene: dicono qualcosa di
vero, e `params["sources"]` dice a quali aree agganciarli.

Resta valida l'eccezione: `cit.status.error`, che `build_report` sintetizza
quando il modulo fallisce, **non** porta `derived` — non è una sintesi ma un
guasto del nostro strumento, e nessun'altra area lo sta già dicendo.

### U6 — ✅ (2026-08-25): Markdown e CSV, e `__version__` a 2.5.0

**Markdown.** Serve dove l'HTML non arriva — una issue, un wiki, un messaggio —
ed è l'unico formato in cui il piano diventa **operativo** invece che
leggibile: una task list GFM si spunta. Un test pretende che le caselle si
consegnino **vuote**, perché `- [x]` in un referto direbbe che l'intervento è
già fatto.

La gravità è un **marcatore testuale** e non un colore: `**[CRITICO]**`,
`[AVVISO]`, `[INFO]`. In HTML il badge rosso porta già la parola; qui non c'è
badge, e affidare la gravità alla sola posizione nell'elenco la perderebbe
appena qualcuno riordina o copia una riga.

`_md_cella` neutralizza due caratteri che rompono una tabella GFM e arrivano da
fuori: la **pipe**, che aprirebbe una colonna in più, e l'**a-capo**, che
chiuderebbe la riga. Gli `example` vanno invece in blocchi recintati:
indentazione e a-capo di un blocco nginx *sono* il suo contenuto.

**CSV.** Una riga per rilievo, `;` come delimitatore e **BOM UTF-8** in testa.
Non sono vezzi: senza BOM, Excel legge un file UTF-8 nella codepage di sistema
e «Accessibilità» diventa «AccessibilitÃ»; con la virgola, nelle impostazioni
italiane finisce tutto in una colonna sola. Chi vuole i byte puliti ha il JSON,
ed è il motivo per cui questa resa esiste separata.

Le celle passano dal modulo `csv` della libreria standard invece che da una
concatenazione a mano: un `fix` di ZAP pieno di virgolette o un titolo con un
punto e virgola spezzerebbero il file, e sono dati che vengono da fuori.

`sforzo` e `quick_win` restano **vuoti** dove il rilievo non è azionabile —
vuoto e non «no»: un `quick_win` a «no» su un rilievo informativo sembrerebbe
una valutazione che nessuno ha fatto. E il CSV **tiene i derivati**: R41 li
esclude da chi *aggrega* e li tiene per chi li mostra uno per uno, che è
esattamente questo caso.

**Nessuna riga di codice nella CLI né nei golden.** `RENDERERS` è la sola
registrazione: la CLI legge `choices=tuple(RENDERERS)` e la Fase 2 itera già
sul registro, quindi i quattro golden nuovi sono nati da soli. È il ritorno di
due decisioni prese fasi fa.

Una cosa scoperta scrivendo i test: la fixture del referto di `test_report.py`
non aveva `findings`, e il CSV ne usciva con la sola intestazione. Dalla Fase 1
ogni area ne emette: la fixture ne esercitava una forma che in produzione non
esiste, e ora ne ha uno.

Quattordici mutazioni, nessuna sfuggita.

- [x] `render_markdown()`, `render_csv()`, `_md_cella()`, gli esempi della
      CLI, il README, quattordici test, quattro golden nuovi.

### U7 — ✅ (2026-08-25): riproducibilità e storia, e `__version__` a 2.6.0

**I metadati (G09).** Il referto dichiara `schema_version`, che è cosa diversa
dalla versione del programma: sale **solo** su un cambiamento incompatibile,
mentre le aggiunte sono additive. Senza quella distinzione servirebbe una
versione di schema nuova a ogni fase del programma UPGRADE, e il numero
smetterebbe di dire qualcosa.

Accanto ci sono i parametri che rendono il referto rileggibile fra sei mesi:
`rrf` con il k della fusione e la formula — viveva come **default di una
funzione**, e due esecuzioni con k diversi non sono confrontabili alla pari —
e `thresholds`, oggi `null`. Null e non chiave mancante: quando le soglie
diventeranno configurabili, nessuno dovrà distinguere «assente perché vecchio»
da «assente perché di serie».

Un test guarda il **codice** e non il dato: il referto dichiara `RRF_K`, ma la
fusione la chiamano quattro moduli, e se uno passasse un `k` suo il referto
direbbe il falso senza che nessun test sul contenuto se ne accorga. Verificato
con `ast` su tutti i `mars_*.py`: quattro chiamate, nessuna col `k` esplicito.

**Lo storico e il delta (G06).** `mars_history.py`, modulo suo perché
`mars_report` ha già 1.800 righe e perché l'I/O va separato dalla logica. Una
riga compatta per esecuzione in JSONL **append-only**: il referto intero pesa
1.500 righe di JSON, e conservarne uno per esecuzione trasforma lo storico in
un archivio che nessuno rilegge.

**Il confronto è per chiave**, ed è il ritorno della Fase 1. Una `key` non
contiene mai un valore variabile, quindi `tech.canonical.missing` resta la
stessa quando le pagine senza canonical passano da 2 a 117 — confrontare i
*titoli* direbbe un rilievo risolto e uno nuovo, cioè il contrario del vero.
Per i rilievi senza chiave, che nessuno dei nove moduli produce ma un plugin
di terzi può, si ripiega sul titolo coi numeri normalizzati **e il delta lo
dichiara**: è un confronto più debole, e chi legge deve saperlo.

**Tre decisioni che sarebbero potute andare storte:**

- **un'area misurata ieri e non oggi non è peggiorata**: non è stata guardata.
  I punteggi si confrontano solo dove entrambe le esecuzioni hanno un numero,
  ed è la stessa distinzione fra «non misurato» e «zero» che il referto fa
  dappertutto. Sarebbe stata la bugia più facile della fase;
- **il colore del delta segue il segno, non la scala dei punteggi**: qui non si
  giudica quanto vale l'area, si dice se è salita, e un 59 che sale da 40 è una
  buona notizia che la scala dipingerebbe di rosso;
- **la sezione non compare alla prima esecuzione**. È l'opposto della scelta
  fatta per il piano, dove la sezione resta anche vuota: lì il vuoto è un
  risultato, qui è un'assenza — «tutto invariato» e «non c'è un prima» sono
  cose diverse.

**Lo storico non può far fallire un audit.** Un file assente, illeggibile o non
scrivibile restituisce `None`/`False` e viene dichiarato: il referto è già
prodotto, e perdere una riga di archivio non vale il codice di uscita. Una
riga corrotta non invalida le altre — è il vantaggio del JSONL sul JSON, ed è
la ragione per cui lo storico ha questo formato.

**Il golden completo ha ora un'esecuzione precedente**, congelata a mano e non
prodotta da un secondo giro dei moduli: se la generasse il codice, il delta
uscirebbe vuoto e il golden congelerebbe una sezione che non dice niente. Il
degradato resta alla prima esecuzione, così i due dataset coprono entrambi i
casi. Il presidio sui campi volatili ammette ora due letterali, e nient'altro:
una data *viva* che sfuggisse resta rossa.

Ventisei mutazioni, nessuna sfuggita. Due erano sfuggite al primo giro, ed
erano un buco vero: il cablaggio nella CLI — leggere prima, appendere dopo —
non era presidiato da nulla. Ora un test fa il giro completo, prima esecuzione
e seconda.

- [x] `mars_core` (`JSON_SCHEMA_VERSION`, `RRF_K`, `RRF_FORMULA`),
      `mars_history.py`, tre chiavi nel referto più `delta`, `--history` e
      `--no-history`, la resa in testo/HTML/Markdown, trenta test, i golden.

### U8.1 — ✅ (2026-08-25): la superficie come dato

**`pages[]` nel referto**: per ogni URL scansionato il titolo, la lingua, la
profondità, quanti heading e quanti chunk, e i tipi Schema.org dichiarati.
Nessuna delle nove aree lo espone — ognuna guarda la propria misura — e per
un'integrazione è il dato più utile del referto dopo i rilievi.

Esce **senza il contenuto**: `context["pages"]` porta anche `html` e `text`,
centinaia di kilobyte per pagina, che nel referto non hanno posto.

**Lo status HTTP non c'è, e non si inventa.** Nel dict pagina non esiste,
perché solo le 200 entrano in `pages` e tutto il resto finisce in `skipped`:
scriverci un 200 fisso vorrebbe dire pubblicare una misura che nessuno ha
fatto. È l'avvertenza che UPGRADE.md stesso segnalava.

**La profondità di crawl**, registrata dal crawler: la coda BFS porta ora la
distanza in click dalla home. Le pagine che vengono dalla **sola sitemap**
hanno profondità `None` — dichiarate dal sito, ma nessuno le ha raggiunte
seguendo i link, e chiamarle «profondità 0» direbbe che stanno in home. Ne
segue che la profondità si misura **solo** quando il crawler segue i link,
cioè quando la sitemap manca: è per costruzione, e il secchiello «profondità
ignota» esiste apposta.

Quel secchiello non è un residuo: un contenuto che sta nella sitemap e in
nessun percorso di navigazione è un contenuto che un assistente trova solo se
sa già che esiste — ed è la scoperta più utile della sezione.

**I tipi Schema.org** si leggono nelle tre forme che i siti veri usano:
`@type` stringa, `@type` lista, e dentro un `@graph`. Un blocco che non si
analizza non dà niente e **non diventa un giudizio**: che sia malformato lo
dice già `mars_schema` con un rilievo suo, e ripeterlo qui sarebbe la seconda
voce sullo stesso difetto.

I due golden restano a profondità ignota su tutte le pagine, ed è fedele:
entrambi i dataset dichiarano `discovery: sitemap`. I secchielli veri li
esercitano i test, e due test nuovi sul `Crawler` verificano il giro completo
— tre pagine in fila danno 0, 1, 2, e la stessa scansione da sitemap dà
`None`.

- [x] `Crawler.crawl()` (la coda porta la profondità), `pagine_scansionate()`,
      `depth_distribution()`, `_tipi_json_ld()`, nove test, i due golden JSON.

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

### Caricatore di moduli: cache e bytecode stantio (2026-08-20)
`load_external_module()` rieseguiva il modulo a ogni chiamata: nove per
richiesta API.

**La ragione per intervenire non era la velocità, e va detto.** Misurato: 0,8 ms
per audit, nulla accanto a una scansione che dura secondi. Il problema era che
**due chiamate restituivano oggetti diversi**, quindi un `isinstance` contro
una classe del modulo falliva e lo stato di modulo si azzerava a ogni
richiesta. Con la cache: 0,024 ms, ma è un effetto collaterale, non lo scopo.

La cache si invalida sulla firma del file *(mtime in nanosecondi, dimensione)*,
così modificare un plugin continua ad avere effetto **senza riavviare l'API** —
che è la ragione per cui il caricamento a runtime esiste.

**Un difetto più insidioso, trovato dal test di ricaricamento.** Il test
falliva pur avendo la cache corretta: l'oggetto era nuovo ma **il codice
eseguito era vecchio**. Indagando: il bytecode cache di Python valida su
*(mtime in **secondi interi**, dimensione del sorgente)*. Un file modificato
nello stesso secondo e della stessa lunghezza — cambiare una cifra, invertire
un booleano — veniva eseguito nella versione precedente, **senza un solo
errore**.

Verificato in isolamento: stessa dimensione → valore vecchio; dimensione
diversa → valore nuovo. Il difetto **precedeva** questa modifica ed era una
proprietà di `exec_module()`, non della cache; ma prometterne l'invalidazione
senza sistemarlo sarebbe stata una promessa falsa.

Il caricatore compila ora la sorgente e la esegue nel namespace del modulo,
saltando del tutto il `.pyc`. Costa nulla e toglie un'intera classe di
sorprese — il tipo che fa perdere un'ora a chiedersi perché una modifica non
si veda.

Quattro test nuovi, e la mutazione che toglie l'invalidazione li fa fallire.

### Aiuto della CLI (2026-08-20)
`mars_audit.py --help` elencava i parametri senza dire cosa accettassero:
*"Numero massimo di pagine"*, *"Modello ST o 'none'"*, *"Target market per
citabilità IA"*. Nessun default mostrato per metà dei flag, e **nessun
esempio**.

**Ogni parametro mostra ora valori ammessi o un esempio**, con il default e
l'effetto pratico: `--max-pages` suggerisce 10/40/100 e avverte che più pagine
significano più richieste al sito; `--delay` spiega quando usare 0 e quando 2,
e che un `Crawl-delay` più alto in robots.txt vince comunque; `--embeddings`
distingue `none` da un nome di modello dell'Hub. I valori di `--market` si
leggono da `MERCATI`, non si riscrivono: non possono divergere.

**Un epilogo con cinque esempi eseguibili**, i codici di uscita e le quattro
variabili d'ambiente. Due avvertenze sono in maiuscolo perché non passino
inosservate: `--llm` è l'unico modulo che comporta una spesa, e
`--i-own-this-domain` abilita una scansione che **invia payload d'attacco**.

**Gli esempi sono verificati da un test.** È la lezione di **R12**, dove il
README documentava comandi che terminavano con un errore: ogni comando
dell'epilogo viene dato in pasto al parser reale, quindi se un flag cambia
nome il test se ne accorge prima di chi legge l'aiuto. Tutti e cinque sono
stati anche **eseguiti**, inclusa la catena `--format json` →
`mars_citations --from-audit`.

Il parser è stato estratto in `costruisci_parser()` per renderlo verificabile
fuori dal blocco `__main__`.

**Un'incoerenza trovata dal test:** `--market` diceva *"Valori riconosciuti"*
dove gli altri dicono *"Valori"*. Uniformato il linguaggio invece di allentare
il controllo — 11 test nuovi, 157 in tutto.

### C12 — ✅ FATTO (2026-08-20): la suite di test
`pytest` era fra le dipendenze dal primo giorno e **non esisteva un solo
test**. Decine di verifiche fatte a mano lungo tutto il percorso vivevano solo
nello scrollback della sessione.

**146 test in meno di 8 secondi**, in quattro file: `test_core.py` (algoritmi,
URL, chunker, query, caricatore di moduli), `test_modules.py` (le nove aree su
fixture offline), `test_api.py` (autenticazione, endpoint, parametri,
credenziali), `test_report.py` (dato canonico e tre viste).

**La suite è ermetica per costruzione.** Una fixture `autouse` sostituisce ogni
richiesta di rete con un'eccezione che eredita **sia** da `AssertionError`
**sia** da `requests.RequestException`: un modulo che gestisce correttamente
gli errori di rete la cattura e ripiega — e il percorso di ripiego viene così
esercitato davvero — mentre un modulo che non la gestisce la lascia passare e
il test fallisce rumorosamente. Un solo meccanismo verifica due cose opposte.

Una seconda fixture neutralizza gli strumenti esterni. Senza, `mars_seo`
**lanciava Lighthouse per davvero** durante i test: la suite passava da 8
secondi a **85**.

**Ogni test cita la regressione che protegge.** R1 (login rotto), R2 (hash
esposto), R3 (nessuna shell), R4 (score 0 ≠ non misurato), R5 (una scansione
sola), R6 (campi `None`), R7 (normalizzazione URL), R8 (df conservate,
vettori sparsi), R9 (falsi positivi answer-shaped), R10 (segmentazione), R11
(`sys.modules`, percorso da `__file__`), R14 (`disabled`), C1, C2, C3, C5, C8,
C9, C10.

**La prova che conta: reintrodurre i difetti.** Una suite verde non dimostra
nulla finché non la si vede fallire. Sei difetti reali sono stati rimessi nel
codice uno per uno:

```
R1  login rotto                  -> 2 falliti, 20 errori
R2  /users/me con l'hash         -> 1 fallito
R6  campi None senza difese      -> 1 fallito
R10 chunk senza segmentazione    -> 1 fallito
R14 disabled non applicato       -> 2 falliti
C10 robots.txt per sottostringa  -> 1 fallito
```

**Alla prima esecuzione tre su sei NON venivano rilevati**, ed è il risultato
più utile dell'intero esercizio. I tre test erano vacui e sembravano corretti:

- quello su **R2** misurava la seconda difesa invece della prima —
  `response_model=User` filtra comunque, quindi sarebbe passato anche con la
  dipendenza che restituisce l'oggetto interno. Riscritto per verificare
  `get_current_user` direttamente, cioè il livello che protegge i prossimi
  endpoint, quelli che qualcuno scriverà dimenticando `response_model`;
- quello su **R6** metteva il `None` nelle *pagine*, ma da **R10**
  `mars_lexical` legge i **chunk**: toccava un campo che il modulo non guarda
  più;
- quello su **R10** verificava separatamente la segmentazione per heading e
  `split_windows`, senza mai provarne **l'innesto** — ed è lì che stava il
  difetto.

Un settimo tentativo, su R6, non ha fatto fallire nulla: la mutazione toglieva
una delle due difese indipendenti del codice, e l'altra reggeva. Non un test
debole ma una ridondanza reale, ed è stato verificato togliendole entrambe.

`setup.cfg` configura ora anche pytest, così `pytest` da solo funziona dalla
radice.

**Un difetto minore emerso:** `load_external_module()` **riesegue** il modulo a
ogni chiamata, quindi nove riesecuzioni per audit, e le patch applicate
all'oggetto importato non sopravvivono. Non è un problema di correttezza —
annotato in TO-DO.

- [x] `tests/test_core.py`: RRF, BM25, char-TFIDF, casi limite.
- [x] `tests/test_modules.py`: ogni `audit()` offline.
- [x] `tests/test_api.py`: autenticazione ed endpoint.
- [x] `setup.cfg` con la configurazione di flake8 e pytest.

### C10 — ✅ FATTO (2026-08-20): `mars_tech` copre le quattro aree che promette
Il README assegnava all'area 1 *"indicizzabilita', robots.txt, sitemap, crawler
IA"*. Il file ne implementava **una**, in 24 righe: una GET su robots.txt e un
controllo che il testo contenesse `gptbot`, `ccbot` o `claudebot` come
sottostringa.

**I dati vengono dal crawler, non da nuove richieste.** `robots.txt` e le
sitemap erano già stati letti durante la scansione: ora `Crawler` conserva
`robots_info` (esistenza, testo, direttive `Sitemap:`) e `sitemap_info` (file
letti, indici annidati, URL, quanti con `<lastmod>`, quanti illeggibili), e
ogni pagina porta `meta_robots`, `canonical` e `x_robots_tag`. È lo stesso
principio applicato a `json_ld` e `images` in R11: si estraggono **dati
grezzi**, e il giudizio resta al modulo.

**robots.txt, tre casi invece di uno.** Il controllo precedente cercava una
sottostringa e non distingueva *nessuna regola*, *permesso esplicito* e
*blocco esplicito* — che sono cose opposte. Ora si usa `RobotFileParser` per
agente su **13 crawler IA** (OpenAI ×3, Anthropic ×3, Perplexity, Common Crawl,
Google-Extended, Applebot-Extended, ByteDance, Amazon, Meta). Un blocco è
`critico`: nessun'altra area può compensarlo, perché un crawler escluso non
legge nulla.

**Indicizzabilità.** `noindex` da `meta robots` **e** da `X-Robots-Tag`:
quest'ultimo agisce allo stesso modo ma viaggia negli header, quindi non
compare nel DOM ed è il modo più facile per escludersi dagli indici senza
accorgersene. Più `canonical` mancante, e `canonical` che punta a un altro
host — il caso in cui il contenuto viene attribuito altrove.

**Sitemap.** Esistenza, se è dichiarata in robots.txt o solo trovata su
`/sitemap.xml`, file illeggibili, e `<lastmod>` assente.

**Scala pesata.** `100 - len(issues)*15` dava lo stesso peso a un `noindex`
sull'intero sito e a un `<lastmod>` mancante. Ora quattro gravità
(`critico` 40, `grave` 20, `medio` 8, `lieve` 3), dichiarate come scelta
editoriale, e i rilievi escono ordinati per gravità.

**Verificato** con un terzo server di prova, ostile agli assistenti:
robots.txt che blocca GPTBot, ClaudeBot e CCBot; una pagina con
`meta robots noindex`; una con `X-Robots-Tag: noindex` **solo** negli header;
una con canonical verso un altro host.

```
sito aperto  : tecnica 91/100  -> citabilità composita 70,2
sito ostile  : tecnica 17/100  -> citabilità composita 50,0
   [critico] robots.txt BLOCCA 3 crawler IA: CCBot, ClaudeBot, GPTBot
   [grave]   2/3 pagine con 'noindex' (meta robots o X-Robots-Tag)
   [grave]   1 pagine con canonical verso un altro host
```

> *Verbale del 2026-08-19, conservato com'è.* La seconda riga oggi direbbe
> «2/3 pagine escluse dagli indici (noindex o none, in meta robots o
> X-Robots-Tag)»: la formulazione è cambiata con **R25**. Chi confronta il
> comportamento attuale con questo blocco non stia cercando una regressione
> che non c'è.

Il `noindex` da header è stato rilevato su una pagina dove è l'unica fonte, il
che prova che il controllo non si limita al DOM. E l'effetto si propaga:
"Accesso e indicizzabilità" compare fra i segnali deboli del profilo di
citabilità, che è esattamente il collegamento che C1 aveva predisposto.

Nel rifattorizzare, una `replace` distratta aveva colpito due volte e rotto
l'assegnazione di `discovery` dentro `crawl()`. Trovata subito perché i dati
attesi nel contesto risultavano vuoti — e corretta prima di proseguire.

- [x] Sitemap: esistenza, validità, indici annidati, URL, `lastmod`.
- [x] Indicizzabilità: `meta robots`, `X-Robots-Tag`, `canonical`.
- [x] 13 crawler IA per agente, distinguendo assente da bloccato.
- [x] Scala pesata per gravità.

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

