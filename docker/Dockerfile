# syntax=docker/dockerfile:1
#
# MARS Beacon — l'immagine e' lo STACK, non MARS.
#
# Dentro ci sono l'interprete, il runtime e gli strumenti esterni:
# Python, Node, Chromium, Lighthouse, axe-core, e le dipendenze pip.
# Il codice di MARS NON viene copiato: sta sull'host e si monta su
# /app. Cosi' una modifica a un modulo si esegue subito, senza
# ricostruire nulla, e l'immagine si rifa' solo quando cambia lo stack.
#
# Cosa fa ricostruire l'immagine: requirements*.txt, package.json,
# la versione di Python o di Node. Nient'altro.
#
#     docker build -f docker/Dockerfile -t mars-stack:latest .
#
# ---------------------------------------------------------------------
# Node non e' un accessorio: Lighthouse porta le aree 2 (SEO) e 3
# (Prestazioni), axe-core porta l'area 7 (Accessibilita'). Lighthouse
# 13.4.1 dichiara `engines.node >= 22.19` e bookworm porta la 18,
# quindi il binario si prende dall'immagine ufficiale invece che da uno
# script scaricato ed eseguito dalla shell.
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
# copertura di wheel piu' larga per lxml, bcrypt e torch.
#
# PIP_ROOT_USER_ACTION=ignore silenzia l'avviso «Running pip as the
# 'root' user»: fuori da un container mette in guardia dal rompere il
# Python di sistema, ma qui il Python di sistema E' lo stack, non c'e'
# altro che possa rompersi e non esiste un gestore di pacchetti in
# conflitto. Non ha mai fermato una build: si toglie perche' in un log
# lungo somiglia a un errore.
#
# PLAYWRIGHT_BROWSERS_PATH sta fuori da $HOME: i browser li installa
# root e devono restare leggibili all'utente che esegue il container.
#
# PATH: `node_modules/.bin` dell'immagine. `trova_lighthouse()` guarda
# PRIMA il PATH (mars_seo.py:754), quindi Lighthouse si trova anche se
# nulla e' montato su /app.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PATH=/app/node_modules/.bin:$PATH

# --- Node dall'immagine ufficiale ------------------------------------
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version

WORKDIR /app

# --- Dipendenze Python ------------------------------------------------
# Dei file del repository entrano nell'immagine SOLO i manifest: sono
# la definizione dello stack, non il codice che gira.
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
# pytest e flake8 (requirements-dev.txt) ci sono perche' il codice e'
# montato: `docker compose run --rm mars pytest` esegue la suite VERA
# dell'host dentro lo stack, ed e' la prova che lo stack e' completo.

# --- Chromium ---------------------------------------------------------
# Un browser solo per due consumatori: Playwright lo usa per axe-core
# (area 7), Lighthouse lo raggiunge via CHROME_PATH (aree 2 e 3).
RUN apt-get update \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

# Il percorso di Chromium contiene il numero di build, che cambia a ogni
# versione di Playwright: lo si chiede a Playwright invece di scriverlo,
# e il collegamento assorbe la differenza. CHROME_PATH e' la variabile
# che chrome-launcher legge per prima (chrome-finder.js:75), ed e'
# l'unica leva che Lighthouse offra: mars_seo.py passa
# `--chrome-flags=--headless` e nient'altro.
RUN ln -s "$(python -c 'from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path); p.stop()')" \
        /usr/local/bin/chromium \
 && test -x /usr/local/bin/chromium
ENV CHROME_PATH=/usr/local/bin/chromium

# Il sandbox SUID di Chromium. Il profilo seccomp predefinito di Docker
# vieta a un processo non privilegiato di creare user namespace, quindi
# il sandbox a namespace non parte; quello SUID e' il ripiego che
# Chromium prevede, e non chiede alcun flag al `docker run`.
#
# Tre cose misurate su un'installazione Playwright vera, e nessuna
# indovinata:
#
#   1. l'helper si chiama `chrome_sandbox`, con il TRATTINO BASSO.
#      Cercare `chrome-sandbox` — il nome che Chromium usa quando lo
#      trova accanto a se' — non ne incontra nessuno, ed e' cosi' che
#      questa build e' fallita la prima volta. Si cercano entrambi i
#      nomi, perche' quale dei due Playwright spedisca e' una sua
#      scelta e puo' cambiare.
#   2. l'helper sta nel solo pacchetto `chromium`. Il pacchetto
#      `chromium_headless_shell` non ne ha alcuno.
#   3. `launch(headless=True)` esegue proprio `chrome-headless-shell`,
#      non il browser pieno — verificato leggendo la riga di comando
#      del processo. E' mars_wcag a lanciarlo.
#
# Da (2) e (3): l'helper NON puo' stare accanto al binario, perche' i
# binari sono due e uno solo ce l'ha. Si copia in un percorso stabile e
# lo si dichiara con CHROME_DEVEL_SANDBOX, che il binario chrome porta
# fra i propri letterali e che i processi figli ereditano — sia quelli
# di Playwright sia quelli che Lighthouse lancia.
#
# Copiato e non collegato: il bit setuid su un collegamento simbolico e'
# ignorato dal kernel, e qui il bit e' tutto.
RUN set -eu; \
    trovati="$(find /opt/ms-playwright \
        \( -name chrome_sandbox -o -name chrome-sandbox \) -type f)"; \
    if [ -z "$trovati" ]; then \
        echo "nessun helper di sandbox sotto /opt/ms-playwright" >&2; \
        exit 1; \
    fi; \
    origine="$(echo "$trovati" | head -n 1)"; \
    echo "helper di sandbox: $origine"; \
    cp "$origine" /usr/local/sbin/chrome-devel-sandbox; \
    chown root:root /usr/local/sbin/chrome-devel-sandbox; \
    chmod 4755 /usr/local/sbin/chrome-devel-sandbox; \
    modo="$(stat -c '%a %U' /usr/local/sbin/chrome-devel-sandbox)"; \
    if [ "$modo" != "4755 root" ]; then \
        echo "sandbox mal configurato: $modo (atteso 4755 root)" >&2; \
        exit 1; \
    fi
ENV CHROME_DEVEL_SANDBOX=/usr/local/sbin/chrome-devel-sandbox

# --- Dipendenze Node --------------------------------------------------
# Installate in /app/node_modules, che e' il percorso da cui il volume
# nominato di docker-compose.yml si semina. NON e' un dettaglio: i due
# strumenti Node si raggiungono in due modi diversi, e uno solo passa
# dal PATH.
#
#   Lighthouse  -> PATH, e `trova_lighthouse()` guarda li' per primo.
#   axe-core    -> mars_wcag.py:27 compone il percorso da __file__ e
#                  NON ha un ripiego sul PATH: `axe.min.js` deve
#                  trovarsi accanto ai moduli montati, cioe' dentro
#                  /app/node_modules.
#
# `npm install` e non `npm ci`: package-lock.json e' ignorato da git
# (.gitignore), quindi su un clone pulito non c'e'. La build non e'
# riproducibile alla patch — package.json usa intervalli `^` — ed e' la
# posizione che il progetto ha gia' scelto, non una decisione presa qui.
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# Verificato QUI: se l'appiattimento di npm cambiasse e axe-core
# finisse annidato, senza questo controllo l'area 7 ripiegherebbe in
# silenzio su un'euristica, con l'immagine costruita «bene».
RUN test -x node_modules/.bin/lighthouse \
 && test -f node_modules/axe-core/axe.min.js \
 && test -f node_modules/axe-core/locales/it.json \
 && lighthouse --version

# --- Entrypoint -------------------------------------------------------
# L'unico file non-manifest che entra nell'immagine: e' parte dello
# stack, non di MARS.
COPY docker/entrypoint.sh /usr/local/bin/mars-entrypoint
RUN chmod 755 /usr/local/bin/mars-entrypoint

# --- Utente -----------------------------------------------------------
# uid 1000: e' il primo utente della maggior parte degli host, e con il
# repository montato ogni file scritto — referti, storico, __pycache__ —
# deve appartenere a chi lo ha chiesto e non a root. Se sull'host l'uid
# e' un altro, si passa `--user "$(id -u):$(id -g)"`.
# Niente `chown -R /app`: duplicherebbe il layer di node_modules,
# duecento megabyte, per un permesso che non serve — MARS quei file li
# LEGGE soltanto, e npm li lascia gia' leggibili a tutti.
RUN useradd --create-home --uid 1000 --shell /bin/bash mars
USER mars

EXPOSE 8000

# `/` esiste e non chiede autenticazione (mars_api.py:361).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"

ENTRYPOINT ["mars-entrypoint"]
CMD ["api"]
