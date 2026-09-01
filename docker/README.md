# MARS Beacon in un container

Un'immagine sola per le due interfacce: CLI (`mars_audit.py`) e API REST
(`mars_api.py`). Sono due facce dello stesso motore (principio 4), e
separarle vorrebbe dire mantenere due volte gli stessi strumenti
esterni — Node, Lighthouse, axe-core, Chromium.

| File | Cosa fa |
|---|---|
| `Dockerfile` | L'immagine. Contesto di build: la **radice** del repository |
| `entrypoint.sh` | Smista fra API, CLI, `pytest` e shell |
| `docker-compose.yml` | API in piedi con un comando; ZAP dietro un profilo |
| `mars.env.example` | Modello di `.env` — chiavi e porta |
| `../.dockerignore` | Sta nella radice **perché è lì che Docker lo legge**: senza, il contesto sarebbe di 5,6 GB |

---

## Avvio rapido

```bash
cd docker
mkdir -p work                 # PRIMA di `up`: se la crea Docker è di root
cp mars.env.example .env      # `.env` è già ignorato da git
chmod 600 .env
docker compose up -d --build
```

L'API risponde su `http://127.0.0.1:8000`, la documentazione interattiva
su `http://127.0.0.1:8000/docs`.

```bash
# Token (credenziali predefinite: mars_api.py:370)
curl -s -X POST http://127.0.0.1:8000/token \
     -d 'username=admin&password=mars2026' | python3 -m json.tool
```

**Cambiare quella password prima di esporre l'API**: sta in chiaro in
`FAKE_USERS_DB` ([mars_api.py:66](../mars_api.py#L66)), che è un dizionario
in memoria e non un database.

## La CLI

Lo stesso container, un comando diverso. La directory di lavoro dentro
l'immagine è `/work`: è lì che atterrano `--output`, `--history` e il
`.mars-history.jsonl` predefinito, ed è la sola da montare.

```bash
# Con compose già in piedi
docker compose run --rm mars audit https://www.example.com \
    --max-pages 20 --format html --output referto.html

# Oppure senza compose
docker build -f docker/Dockerfile -t mars-beacon:latest .
docker run --rm -v "$PWD/docker/work:/work" mars-beacon \
    audit https://www.example.com --format html --output referto.html
```

`audit` si può omettere se il primo argomento è un URL:
`docker run --rm mars-beacon https://www.example.com`.

Le altre forme che l'entrypoint riconosce:

| Comando | Effetto |
|---|---|
| *(nessuno)* o `api` | `uvicorn mars_api:app` su `0.0.0.0:8000` |
| `audit …` | `python mars_audit.py …` |
| `citations …` | `python mars_citations.py …` |
| `pytest` / `flake8` | Da `/app`, dove sta `setup.cfg` |
| `sh`, `bash`, altro | Eseguito così com'è |

## Le chiavi

Due strade, come fuori dal container.

**Variabili d'ambiente** — `.env`, letto da compose. MARS ne legge
quattro: `MARS_SECRET_KEY`, `ANTHROPIC_API_KEY`, `ZAP_API_KEY`,
`ZAP_PROXY` (più `HF_TOKEN`, che legge `huggingface_hub`).

**File di credenziali** — l'unica strada per i giudici non-Anthropic
(`openai`, `qwen`, `kimi`), che dall'ambiente non si leggono:

```bash
cp examples/credentials.json docker/work/chiavi.local.json
chmod 600 docker/work/chiavi.local.json
docker compose run --rm mars audit https://www.example.com \
    --credentials /work/chiavi.local.json --llm on
```

Il modello è `examples/credentials.json` e **non** `audit_request.json`,
che è il corpo di una richiesta API: passato a `--credentials` consegna
quattro segnaposto come se fossero chiavi (R62).

## ZAP (area 8)

Sta dietro un profilo perché l'immagine è grande e l'area senza daemon
non fallisce: ripiega sul controllo di superficie e lo dichiara.

```bash
docker compose --profile zap up -d
```

Spider e active scan girano **solo** con `--i-own-this-domain`: lo
spider di ZAP non rispetta robots.txt (R55), quindi sta dietro la
dichiarazione di proprietà come l'active scan. Senza dichiarazione ZAP
vede le sole pagine che il crawler di MARS ha già scaricato.

## Che cosa c'è dentro, e che cosa manca

| Area | Strumento | Nell'immagine |
|---|---|---|
| 2 SEO, 3 Prestazioni | Lighthouse 13.x su Chromium | ✅ |
| 7 Accessibilità | axe-core 4.x via Playwright | ✅ |
| 10 Giudizio LLM | `anthropic` | ✅ (serve la chiave) |
| 5 Semantica | `sentence-transformers` | ❌ per scelta — vedi sotto |
| 8 Sicurezza | daemon ZAP | Profilo `zap` di compose |

**Gli embedding reali sono fuori dal default.** `sentence-transformers`
trascina torch: alcuni GB per un'area che senza di lui non fallisce —
ripiega sul proxy char-TFIDF scritto a mano e lo dichiara nel referto
(principio 2). Chi li vuole:

```bash
docker build -f docker/Dockerfile --build-arg MARS_EMBEDDINGS=on \
    -t mars-beacon:embeddings .
```

o `MARS_EMBEDDINGS: "on"` sotto `build.args` in `docker-compose.yml`.

## Verificare l'immagine dall'interno

`pytest` e `flake8` sono installati apposta: la suite non tocca la rete
(fixture `niente_rete`) e non dipende da un database, quindi risponde
alla domanda «questa immagine ha tutto ciò che serve».

```bash
docker run --rm mars-beacon pytest
docker run --rm mars-beacon flake8 .
```

Che gli strumenti esterni siano davvero raggiungibili lo dicono loro:

```bash
docker run --rm mars-beacon sh -c \
    'node --version && lighthouse --version && echo "CHROME_PATH=$CHROME_PATH" && "$CHROME_PATH" --version'
```

## Chromium e il sandbox

`mars_seo.py` passa a Lighthouse `--chrome-flags=--headless` e nient'altro,
e `mars_wcag.py` chiama `launch(headless=True)`: **nessuno dei due può
aggiungere `--no-sandbox`**, e non è il container a doverli cambiare.
L'immagine risolve la cosa dove va risolta, cioè in sé:

- un browser solo per due consumatori — Playwright installa Chromium,
  Lighthouse lo raggiunge via `CHROME_PATH`, che è la prima variabile
  che `chrome-launcher` guarda;
- il **sandbox SUID** abilitato in build (`chmod 4755` su
  `chrome-sandbox`), perché il profilo seccomp predefinito di Docker
  vieta a un processo non privilegiato di creare user namespace e il
  sandbox a namespace non partirebbe.

Se su un host particolare Chromium si rifiutasse comunque di partire, il
ripiego è un flag di runtime e non una modifica all'immagine:

```bash
docker run --rm --security-opt seccomp=unconfined ... mars-beacon ...
```

In compose: `security_opt: ["seccomp=unconfined"]` sotto il servizio
`mars`. Riduce l'isolamento del container: usarlo solo se serve.

## Perché queste scelte

- **Node dall'immagine ufficiale**, non da uno script scaricato ed
  eseguito: Lighthouse 13.4.1 dichiara `engines.node >= 22.19`, e
  bookworm porta la 18.
- **`npm install` in immagine, non `node_modules` copiato**: i moduli
  della macchina di sviluppo possono venire da un'altra piattaforma.
  La build non è riproducibile alla patch perché `package-lock.json` è
  ignorato da git — è la posizione che il progetto ha già scelto.
- **`npm` deve installare dentro `/app`**: `mars_seo.py` e `mars_wcag.py`
  risolvono `node_modules` da `__file__`, non dal `PATH`. Tre `test` in
  build lo verificano, altrimenti un'area ripiegherebbe in silenzio.
- **Utente non privilegiato, uid 1000**: i referti nel volume montato
  appartengono a chi li ha chiesti, non a root.
- **Un solo worker uvicorn**: gli endpoint di audit sono `def` e non
  `async def` apposta (R29), quindi FastAPI li esegue nel threadpool e
  un audit lungo non blocca gli altri.
