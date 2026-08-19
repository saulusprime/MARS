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

