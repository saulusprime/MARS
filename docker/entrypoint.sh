#!/bin/sh
# MARS Beacon — smistamento fra le due interfacce dello stesso motore.
#
#   docker run ... mars-beacon                      -> API su 0.0.0.0:8000
#   docker run ... mars-beacon audit https://x.it   -> CLI
#   docker run ... mars-beacon https://x.it         -> CLI (scorciatoia)
#   docker run ... mars-beacon citations https://x.it
#   docker run ... mars-beacon pytest               -> verifica l'immagine
#   docker run ... mars-beacon sh                   -> shell
#
# Qualunque altro primo argomento viene eseguito cosi' com'e', che e' il
# comportamento che ci si aspetta da un entrypoint.
set -eu

APP=/app

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
        # Dalla radice dei sorgenti: setup.cfg configura entrambi, e da
        # /work non verrebbe letto. pytest si invoca senza `-q`, che
        # setup.cfg ha gia' in addopts (.claude/metodo.md).
        cd "$APP"
        exec "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
