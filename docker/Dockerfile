# syntax=docker/dockerfile:1
#
# MARS Beacon — un'immagine sola per la CLI e per l'API.
#
# CLI e API sono due interfacce sopra lo stesso motore (principio 4):
# due immagini vorrebbero dire mantenere due volte le stesse dipendenze
# e gli stessi strumenti esterni. Quale delle due parte lo decide il
# comando — vedi entrypoint.sh.
#
# Il contesto di build e' la RADICE del repository, non questa cartella:
#
#     docker build -f docker/Dockerfile -t mars-beacon:latest .
#
# ---------------------------------------------------------------------
# Node non e' un accessorio: Lighthouse porta le aree 2 (SEO) e 3
# (Prestazioni), axe-core porta l'area 7 (Accessibilita'). Lighthouse
# 13.4.1 dichiara `engines.node >= 22.19` e bookworm porta la 18, quindi
# il binario si prende dall'immagine ufficiale invece che da uno script
# scaricato ed eseguito dalla shell.
# ---------------------------------------------------------------------
FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm

# `on` aggiunge sentence-transformers, e con lui torch: alcuni GB.
# Il default e' `off` perche' senza embedding reali MARS non fallisce —
# ripiega sul proxy char-TFIDF scritto a mano e LO DICHIARA nel referto
# (principio 2). Chi li vuole:
#     docker build --build-arg MARS_EMBEDDINGS=on ...
ARG MARS_EMBEDDINGS=off

# Python 3.12 e non la 3.14 del .venv di sviluppo: il codice non usa
# sintassi oltre la 3.10 (CLAUDE.md) e la 3.12 e' la versione con la
# copertura di wheel piu' larga per lxml, bcrypt e torch. Se il progetto
# dichiarasse un minimo, questa riga lo seguirebbe.

# PLAYWRIGHT_BROWSERS_PATH sta fuori da $HOME: i browser vengono
# installati da root e devono restare leggibili all'utente non
# privilegiato che esegue il container.
# PYTHONPATH serve perche' i moduli stanno in /app mentre la directory
# di lavoro e' /work: senza, `uvicorn mars_api:app` non troverebbe nulla.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PYTHONPATH=/app

# --- Node dall'immagine ufficiale ------------------------------------
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version

WORKDIR /app

# --- Dipendenze Python ------------------------------------------------
# Copiate da sole e prima dei sorgenti: cambiare un modulo non invalida
# questo layer, che e' il piu' caro da ricostruire.
COPY requirements.txt requirements-optional.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir "anthropic>=0.120" "playwright>=1.40" \
 && if [ "$MARS_EMBEDDINGS" = "on" ]; then \
        pip install --no-cache-dir -r requirements-optional.txt; \
    fi \
 && pip install --no-cache-dir -r requirements-dev.txt
# La riga di mezzo e' il sottoinsieme di requirements-optional.txt che
# NON trascina torch: senza anthropic l'area 10 non parte, senza
# playwright l'area 7 ripiega sull'euristica di superficie.
# pytest e flake8 (requirements-dev.txt) restano perche' sono pochi MB e
# rendono l'immagine verificabile dall'interno: `docker run mars pytest`.

# --- Chromium ---------------------------------------------------------
# Un browser solo per due consumatori: Playwright lo usa per axe-core
# (area 7), Lighthouse lo raggiunge via CHROME_PATH (aree 2 e 3).
RUN apt-get update \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

# Il percorso di Chromium contiene il numero di build, che cambia a ogni
# versione di Playwright: lo si chiede a Playwright invece di scriverlo,
# e il collegamento assorbe la differenza. CHROME_PATH e' la variabile
# che chrome-launcher legge per prima (node_modules/chrome-launcher/
# dist/chrome-finder.js:75), ed e' l'unica leva che Lighthouse offre:
# mars_seo.py passa `--chrome-flags=--headless` e nient'altro.
RUN ln -s "$(python -c 'from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path); p.stop()')" \
        /usr/local/bin/chromium \
 && test -x /usr/local/bin/chromium
ENV CHROME_PATH=/usr/local/bin/chromium

# Il sandbox SUID di Chromium. Il profilo seccomp predefinito di Docker
# vieta a un processo non privilegiato di creare user namespace, quindi
# il sandbox a namespace non parte; quello SUID e' il ripiego che
# Chromium prevede, e non chiede alcun flag al `docker run`.
# I file si CERCANO invece di scriverne il percorso: i pacchetti sono
# due, `chromium` e `chromium_headless_shell`, e i loro nomi portano il
# numero di build. Zero file trovati fa fallire la build, altrimenti
# l'immagine nascerebbe senza sandbox e senza un errore.
RUN set -eu; \
    trovati="$(find /opt/ms-playwright -name chrome-sandbox)"; \
    if [ -z "$trovati" ]; then \
        echo "chrome-sandbox non trovato sotto /opt/ms-playwright" >&2; \
        exit 1; \
    fi; \
    echo "$trovati" | while IFS= read -r f; do \
        echo "sandbox SUID: $f"; chown root:root "$f"; chmod 4755 "$f"; \
    done

# --- Dipendenze Node --------------------------------------------------
# `npm install` e non `npm ci`: package-lock.json e' ignorato da git
# (.gitignore), quindi su un clone pulito non c'e'. La build non e'
# riproducibile alla patch — package.json usa intervalli `^` — ed e' la
# posizione che il progetto ha gia' scelto, non una decisione presa qui.
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# I percorsi che i moduli risolvono da __file__ (mars_seo.py:31,
# mars_wcag.py:28 e :40). Verificati QUI: se l'appiattimento di npm
# cambiasse e axe-core finisse annidato, senza questo controllo l'area 7
# ripiegherebbe in silenzio su un'euristica e l'immagine risulterebbe
# costruita «bene».
RUN test -x node_modules/.bin/lighthouse \
 && test -f node_modules/axe-core/axe.min.js \
 && test -f node_modules/axe-core/locales/it.json

# --- Sorgenti ---------------------------------------------------------
COPY mars_*.py setup.cfg README.md LICENSE ./
COPY examples ./examples
COPY tests ./tests
COPY tools ./tools
COPY docker/entrypoint.sh /usr/local/bin/mars-entrypoint
RUN chmod 755 /usr/local/bin/mars-entrypoint

# --- Utente e directory di lavoro -------------------------------------
# uid 1000: coincide con il primo utente della maggior parte degli host,
# cosi' i referti scritti nel volume montato appartengono a chi li ha
# chiesti e non a root.
RUN useradd --create-home --uid 1000 --shell /bin/bash mars \
 && mkdir -p /work && chown mars:mars /work

# /work e non /app: qui atterrano `--output`, `--history` e il
# `.mars-history.jsonl` predefinito, ed e' la directory da montare.
# I moduli restano in /app, dove sta node_modules.
WORKDIR /work
USER mars

EXPOSE 8000

# `/` esiste e non chiede autenticazione (mars_api.py:361).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"

ENTRYPOINT ["mars-entrypoint"]
CMD ["api"]
