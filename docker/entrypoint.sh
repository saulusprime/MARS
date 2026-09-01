#!/bin/sh
# MARS Beacon — avvio dentro lo stack.
#
# L'immagine porta lo stack; MARS arriva montato su /app. Questo script
# controlla che ci sia e smista fra le due interfacce dello stesso
# motore:
#
#   docker compose run --rm mars                      -> API su 0.0.0.0:8000
#   docker compose run --rm mars audit https://x.it   -> CLI
#   docker compose run --rm mars https://x.it         -> CLI (scorciatoia)
#   docker compose run --rm mars citations https://x.it
#   docker compose run --rm mars pytest               -> la suite dell'host
#   docker compose run --rm mars sh                   -> shell
#
# Qualunque altro primo argomento viene eseguito cosi' com'e', che e' il
# comportamento che ci si aspetta da un entrypoint.
set -eu

APP=/app

# 78 e' EX_CONFIG di sysexits.h — errore di configurazione. NON 1, 2 o
# 3: quelli sono di mars_audit.py (soglia --fail-under, argomento non
# valido, scrittura fallita) e riusarli qui farebbe leggere a una
# pipeline «il sito e' sotto soglia» dove il montaggio manca.
if [ ! -f "$APP/mars_audit.py" ]; then
    echo "MARS non e' montato su $APP: l'immagine e' lo STACK e non" >&2
    echo "contiene il codice. Montare il repository:" >&2
    echo "    docker run -v \"\$PWD:/app\" ...     (o docker compose)" >&2
    exit 78
fi

# axe-core NON ha un ripiego sul PATH: mars_wcag.py:27 compone il
# percorso da __file__, quindi `axe.min.js` deve stare dentro il volume
# montato su /app. Se manca, l'area 7 ripiega sull'euristica e lo
# dichiara nel referto (principio 2) — ma chi guarda il terminale merita
# di saperlo prima di leggere il referto.
# Lighthouse invece passa dal PATH, che l'immagine porta con se'.
if [ ! -f "$APP/node_modules/axe-core/axe.min.js" ]; then
    echo "avviso: axe-core assente da $APP/node_modules — l'area 7" >&2
    echo "        (Accessibilita') ripieghera' sull'euristica." >&2
    echo "        Con docker compose il volume mars_node_modules lo" >&2
    echo "        porta; a mano:  -v mars_node_modules:/app/node_modules" >&2
fi

case "${1:-api}" in
    api)
        # `shift` con zero argomenti e' un errore del builtin e sotto
        # `set -e` fermerebbe lo script: `|| true` non lo salva. Il caso
        # esiste perche' ${1:-api} accetta la lista vuota.
        if [ "$#" -gt 0 ]; then shift; fi
        # `--host 0.0.0.0` e non il `127.0.0.1` di mars_api.py:530: quel
        # binding e' giusto fuori da un container e irraggiungibile
        # dentro. Si passa da uvicorn invece di modificare il modulo.
        #
        # Un solo worker: gli endpoint di audit sono `def` e non `async
        # def` apposta (R29), quindi FastAPI li esegue nel threadpool e
        # un audit lungo non blocca gli altri. Piu' worker moltiplicano
        # la memoria — con gli embedding reali, alcuni GB ciascuno.
        cd "$APP"
        exec uvicorn mars_api:app \
            --host "${MARS_HOST:-0.0.0.0}" \
            --port "${MARS_PORT:-8000}" \
            --workers "${MARS_WORKERS:-1}" \
            "$@"
        ;;
    audit)
        shift
        exec python "$APP/mars_audit.py" "$@"
        ;;
    citations)
        shift
        exec python "$APP/mars_citations.py" "$@"
        ;;
    http://*|https://*)
        exec python "$APP/mars_audit.py" "$@"
        ;;
    pytest|flake8)
        # Dalla radice dei sorgenti: setup.cfg configura entrambi. E'
        # la suite dell'host, non una copia congelata nell'immagine:
        # se passa, lo stack ha tutto quello che MARS si aspetta.
        # pytest si invoca senza `-q`, che setup.cfg ha gia' in addopts
        # (.claude/metodo.md).
        cd "$APP"
        exec "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
