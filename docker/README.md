# Lo stack di MARS in un container

**L'immagine è lo stack, non MARS.** Dentro ci sono Python, Node,
Chromium, Lighthouse, axe-core e le dipendenze pip; il codice resta sul
tuo disco e viene montato su `/app`. Modifichi un modulo e la modifica
è già viva: non c'è nulla da ricostruire.

L'immagine si rifà solo quando cambia lo **stack** — `requirements*.txt`,
`package.json`, la versione di Python o di Node.

| File | Cosa fa |
|---|---|
| `Dockerfile` | Lo stack. Contesto di build: la **radice** del repository |
| `entrypoint.sh` | Verifica il montaggio e smista fra API, CLI, `pytest`, shell |
| `docker-compose.yml` | Monta il repository, semina lo stack Node, ZAP dietro un profilo |
| `mars.env.example` | Modello di `.env` — chiavi e porta |
| `../.dockerignore` | Sta nella radice **perché è lì che Docker lo legge**: senza, il contesto sarebbe di 5,6 GB |

Del repository nell'immagine entrano **solo i manifest**
(`requirements*.txt`, `package.json`) e `docker/entrypoint.sh`. Nessun
`mars_*.py`.

---

## Avvio

```bash
cd docker
cp mars.env.example .env && chmod 600 .env
docker compose up -d --build
```

L'API risponde su `http://127.0.0.1:8000`, la documentazione
interattiva su `http://127.0.0.1:8000/docs`.

```bash
# Token (credenziali predefinite: mars_api.py:370)
curl -s -X POST http://127.0.0.1:8000/token \
     -d 'username=admin&password=mars2026' | python3 -m json.tool
```

**Cambiare quella password prima di esporre l'API**: sta in chiaro in
`FAKE_USERS_DB` ([mars_api.py:66](../mars_api.py#L66)), che è un dizionario
in memoria e non un database.

## La CLI

Stesso container, comando diverso. La directory di lavoro è `/app`,
cioè il repository montato: `--output referto.html` scrive nel tuo
albero, esattamente come sull'host.

```bash
docker compose run --rm mars audit https://www.example.com \
    --max-pages 20 --format html --output referto.html
```

`audit` si può omettere se il primo argomento è un URL.

| Comando | Effetto |
|---|---|
| *(nessuno)* o `api` | `uvicorn mars_api:app` su `0.0.0.0:8000` |
| `audit …` | `python mars_audit.py …` |
| `citations …` | `python mars_citations.py …` |
| `pytest` / `flake8` | Da `/app`, dove sta `setup.cfg` |
| `sh`, `bash`, altro | Eseguito così com'è |

Senza compose serve montare a mano — ed è dove si sbaglia:

```bash
docker build -f docker/Dockerfile -t mars-stack:latest .
docker run --rm \
    -v "$PWD:/app" \
    -v mars_node_modules:/app/node_modules \
    mars-stack audit https://www.example.com
```

Senza il montaggio di `/app` l'entrypoint si ferma subito con il codice
**78** (`EX_CONFIG`) e dice cosa manca, invece di lasciare un traceback.
Non usa 1, 2 o 3: quelli sono di `mars_audit.py` — soglia `--fail-under`,
argomento non valido, scrittura fallita — e riusarli qui farebbe leggere
a una pipeline «il sito è sotto soglia» dove manca un montaggio.

## I due strumenti Node non si raggiungono allo stesso modo

È il vincolo che dà forma a tutto il resto.

- **Lighthouse passa dal PATH.** `trova_lighthouse()`
  ([mars_seo.py:754](../mars_seo.py#L754)) prova `shutil.which("lighthouse")`
  per primo, quindi basta che l'immagine ce l'abbia. Funziona sempre.
- **axe-core no.** [mars_wcag.py:27](../mars_wcag.py#L27) compone il percorso
  da `__file__` — `<cartella dei moduli>/node_modules/axe-core/axe.min.js` —
  e non ha alcun ripiego. Con i moduli montati su `/app`, axe-core deve
  trovarsi in `/app/node_modules`.

Per questo `docker-compose.yml` monta un **volume nominato** su
`/app/node_modules`: Docker semina un volume vuoto con il contenuto che
l'immagine ha in quel percorso, così lo stack Node resta dello stack
anche se sull'host `node_modules` manca. Il montaggio del repository non
lo copre, perché il volume è più specifico.

Dopo aver cambiato `package.json` il volume va rifatto — altrimenti
resta quello vecchio:

```bash
docker compose down -v && docker compose up -d --build
```

Se axe-core non è raggiungibile l'entrypoint lo dice su `stderr` e
l'area 7 ripiega sull'euristica dichiarandolo nel referto (principio 2).

## Le chiavi

**Variabili d'ambiente** — `.env`, letto da compose. MARS ne legge
quattro: `MARS_SECRET_KEY`, `ANTHROPIC_API_KEY`, `ZAP_API_KEY`,
`ZAP_PROXY` (più `HF_TOKEN`, che legge `huggingface_hub`).

**File di credenziali** — l'unica strada per i giudici non-Anthropic
(`openai`, `qwen`, `kimi`), che dall'ambiente non si leggono. Il file sta
nel repository montato, quindi il percorso è quello di sempre:

```bash
cp examples/credentials.json chiavi.local.json   # *.local.json è ignorato
chmod 600 chiavi.local.json
docker compose run --rm mars audit https://www.example.com \
    --credentials chiavi.local.json --llm on
```

Il modello è `examples/credentials.json` e **non** `audit_request.json`,
che è il corpo di una richiesta API: passato a `--credentials` consegna
quattro segnaposto come se fossero chiavi (R62).

## ZAP (area 8)

Dietro un profilo, perché l'immagine è grande e l'area senza daemon non
fallisce: ripiega sul controllo di superficie e lo dichiara.

```bash
docker compose --profile zap up -d
```

Spider e active scan girano **solo** con `--i-own-this-domain`: lo
spider di ZAP non rispetta robots.txt (R55), quindi sta dietro la
dichiarazione di proprietà come l'active scan.

## Che cosa porta lo stack

| Area | Strumento | Nello stack |
|---|---|---|
| 2 SEO, 3 Prestazioni | Lighthouse 13.x su Chromium | ✅ via PATH |
| 7 Accessibilità | axe-core 4.x via Playwright | ✅ via volume nominato |
| 10 Giudizio LLM | `anthropic` | ✅ (serve la chiave) |
| 5 Semantica | `sentence-transformers` | ❌ per scelta — vedi sotto |
| 8 Sicurezza | daemon ZAP | Profilo `zap` di compose |

**Gli embedding reali sono fuori dal default.** `sentence-transformers`
trascina torch: alcuni GB per un'area che senza di lui non fallisce —
ripiega sul proxy char-TFIDF scritto a mano e lo dichiara nel referto
(principio 2). Chi li vuole: `MARS_EMBEDDINGS: "on"` sotto `build.args`
in `docker-compose.yml`, oppure

```bash
docker build -f docker/Dockerfile --build-arg MARS_EMBEDDINGS=on \
    -t mars-stack:embeddings .
```

## Verificare che lo stack sia completo

Il codice è montato, quindi `pytest` esegue **la suite vera dell'host**
dentro lo stack: se passa, lo stack ha ciò che MARS si aspetta. La suite
non tocca la rete (fixture `niente_rete`) e non vuole un database.

```bash
docker compose run --rm mars pytest
docker compose run --rm mars flake8 .
docker compose run --rm mars sh -c \
    'node --version && lighthouse --version && "$CHROME_PATH" --version'
```

E che Chromium parta **davvero**, sandbox compreso — è il controllo che
nessuna build può fare al posto tuo, perché in build il container gira
con un profilo diverso:

```bash
docker compose run --rm mars python -c \
    "from playwright.sync_api import sync_playwright as s; p=s().start(); \
     b=p.chromium.launch(); print('chromium OK'); b.close(); p.stop()"
```

## Chromium e il sandbox

`mars_seo.py` passa a Lighthouse `--chrome-flags=--headless` e nient'altro,
e `mars_wcag.py` chiama `launch(headless=True)`: **nessuno dei due può
aggiungere `--no-sandbox`**, e non è il container a dover cambiare il
codice. L'immagine risolve la cosa in sé, e le tre cose che decidono come
sono state misurate su un'installazione Playwright vera:

1. l'helper del sandbox si chiama **`chrome_sandbox`, con il trattino
   basso** — non `chrome-sandbox`, che è il nome che Chromium cerca
   quando lo trova accanto a sé. È così che la prima build è fallita;
2. l'helper sta nel **solo** pacchetto `chromium`. Il pacchetto
   `chromium_headless_shell` non ne ha alcuno;
3. `launch(headless=True)` esegue proprio **`chrome-headless-shell`**,
   non il browser pieno — letto sulla riga di comando del processo.

Da (2) e (3) segue che l'helper non può stare accanto al binario: i
binari sono due e uno solo ce l'ha. Quindi viene copiato in
`/usr/local/sbin/chrome-devel-sandbox`, reso `4755 root`, e dichiarato
con `CHROME_DEVEL_SANDBOX` — la variabile che il binario `chrome` porta
fra i propri letterali e che i processi figli ereditano, sia quelli di
Playwright sia quelli che Lighthouse lancia. Copiato e non collegato:
il bit setuid su un symlink il kernel lo ignora, e qui il bit è tutto.

Lighthouse trova il browser per un'altra strada ancora, `CHROME_PATH`,
che è la prima variabile che `chrome-launcher` guarda.

**Se Chromium non partisse comunque**, il ripiego è un flag di runtime e
non una modifica all'immagine:

```yaml
    security_opt: ["seccomp=unconfined"]     # sotto il servizio mars
```

Restituisce al container gli user namespace, così Chromium usa il
proprio sandbox a namespace e non ha bisogno dell'helper. Riduce
l'isolamento del container: usarlo solo se serve, e saperlo.

## Altre scelte, in breve

- **Node dall'immagine ufficiale**, non da uno script scaricato ed
  eseguito: `lighthouse@13.4.1` dichiara `engines.node >= 22.19`, e
  bookworm porta la 18.
- **uid 1000**: con il repository montato, ogni file scritto — referti,
  storico, `__pycache__` — deve appartenere a te e non a root. Se sul
  tuo host l'uid è diverso: `--user "$(id -u):$(id -g)"`.
- **Un solo worker uvicorn**: gli endpoint di audit sono `def` e non
  `async def` apposta (R29), quindi FastAPI li esegue nel threadpool e
  un audit lungo non blocca gli altri.
- **`npm install` e non `npm ci`**: `package-lock.json` è ignorato da
  git, quindi su un clone pulito non c'è. La build non è riproducibile
  alla patch — è la posizione che il progetto ha già scelto.
