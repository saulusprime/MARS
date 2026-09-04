#!/bin/sh
# MARS Beacon — il sorvegliante degli ordini di riavvio (I22).
#
# GIRA SULL'HOST, non dentro un container, ed e' l'unico pezzo che parla
# con Docker. L'API si limita a scrivere un file in una cartella
# condivisa; qui si decide se quel file significa qualcosa.
#
# PERCHE' COSI' E NON COL SOCKET. Montare /var/run/docker.sock dentro il
# container dell'API equivale a dare root sull'host a chiunque riesca a
# parlarle: con l'accesso al demone si avvia un container privilegiato
# che monta la radice. L'API di MARS sta dietro una credenziale sola, su
# un indirizzo raggiungibile, senza limite ai tentativi di login. Il
# socket la' dentro trasformerebbe una password trapelata in root.
#
# L'ELENCO DEI NOMI PERMESSI STA QUI, e non solo nell'API: il container
# e' il lato NON FIDATO. Se venisse compromesso potrebbe scrivere file,
# non decidere che cosa riavviare. Sono due porte, e la seconda e'
# questa.
#
#   uso:  mars-restart-watcher.sh <cartella-ordini> [nome ...]
#   es.:  mars-restart-watcher.sh /srv/mars/restart zap
#
# Con systemd, invece del ciclo:
#
#   [Unit]
#   Description=MARS: esegue gli ordini di riavvio
#   [Service]
#   Type=oneshot
#   ExecStart=/opt/mars/tools/mars-restart-watcher.sh --una-volta \
#             /srv/mars/restart zap
#   [Install]
#   WantedBy=multi-user.target
#
# piu' un .timer, oppure un .path con PathExistsGlob.

set -eu

UNA_VOLTA=0
if [ "${1:-}" = "--una-volta" ]; then
    UNA_VOLTA=1
    shift
fi

CARTELLA="${1:-}"
if [ -z "$CARTELLA" ]; then
    echo "uso: $0 [--una-volta] <cartella-ordini> [nome ...]" >&2
    exit 64                      # EX_USAGE
fi
shift

# Il default e' `zap` e non `*`: un elenco vuoto che significasse "tutti"
# sarebbe la porta aperta di cui sopra, e per giunta silenziosa.
PERMESSI="${*:-zap}"

if [ ! -d "$CARTELLA" ]; then
    echo "cartella degli ordini assente: $CARTELLA" >&2
    exit 66                      # EX_NOINPUT
fi

INTERVALLO="${MARS_RESTART_INTERVALLO:-5}"

esegui_giro() {
    for ordine in "$CARTELLA"/*.restart; do
        # Con `nullglob` assente in sh, un glob che non trova nulla resta
        # letterale: senza questo controllo si proverebbe a riavviare un
        # container chiamato '*'.
        [ -e "$ordine" ] || continue

        base="$(basename "$ordine")"
        nome="${base%.restart}"

        # Il nome si CONFRONTA, uno per uno. Non si costruisce da una
        # stringa e non si passa a una shell: `docker` viene invocato con
        # una lista di argomenti, e $nome e' gia' stato riconosciuto
        # uguale a un elemento dell'elenco.
        permesso=0
        for consentito in $PERMESSI; do
            if [ "$nome" = "$consentito" ]; then
                permesso=1
                break
            fi
        done

        # L'ordine si toglie SEMPRE, permesso o no: lasciarlo li'
        # significherebbe ritentare in eterno un nome rifiutato, e
        # riempire il log di una riga ogni cinque secondi.
        chi="$(cat "$ordine" 2>/dev/null || echo '(illeggibile)')"
        rm -f "$ordine"

        if [ "$permesso" -eq 0 ]; then
            echo "$(date -Is) RIFIUTATO $nome — non e' fra: $PERMESSI" >&2
            continue
        fi

        echo "$(date -Is) riavvio $nome (chiesto da: $chi)"
        if docker restart "$nome" >/dev/null; then
            echo "$(date -Is) $nome riavviato"
        else
            # Non si esce: un container che non riparte e' un guaio, ma
            # un sorvegliante che muore al primo guaio smette di
            # sorvegliare anche tutto il resto.
            echo "$(date -Is) ERRORE nel riavvio di $nome" >&2
        fi
    done
}

if [ "$UNA_VOLTA" -eq 1 ]; then
    esegui_giro
    exit 0
fi

echo "$(date -Is) sorveglio $CARTELLA ogni ${INTERVALLO}s — permessi: $PERMESSI"
while true; do
    esegui_giro
    sleep "$INTERVALLO"
done
