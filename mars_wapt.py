#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

import requests

# ZAP si raggiunge come daemon GIA' in esecuzione, non lo si avvia.
# Avviarlo e spegnerlo dal codice significava orchestrare un processo
# Java, con il rischio di lasciarlo orfano dopo un timeout; delegarlo a
# chi lancia l'audit e' piu' semplice e piu' onesto:
#
#   docker run -u zap -p 8080:8080 zaproxy/zap-stable zap.sh -daemon \
#       -host 0.0.0.0 -port 8080 -config api.disablekey=true
ZAP_PROXY = os.environ.get("ZAP_PROXY", "http://127.0.0.1:8080")
ZAP_API_KEY = os.environ.get("ZAP_API_KEY", "")

ZAP_TIMEOUT_SCAN = 900   # secondi per spider + active scan
ZAP_ATTESA = 3           # secondi fra due controlli di avanzamento

# Penalita' per livello di rischio. Scelta editoriale dichiarata: non
# sono calibrate su un corpus di scansioni reali, e finche' non lo
# saranno vanno lette come un ordinamento, non come una misura.
ZAP_PENALTIES = {"High": 25, "Medium": 10, "Low": 3, "Informational": 0}

SECURITY_HEADERS = {
    "Strict-Transport-Security": (15, "HSTS mancante"),
    "Content-Security-Policy": (15, "CSP mancante"),
    "X-Frame-Options": (10, "X-Frame-Options mancante"),
}


def score_from_alerts(alerts: List[dict]) -> dict:
    """Punteggio dagli alert ZAP, raggruppati per REGOLA.

    Raggruppare non e' un dettaglio: ZAP segnala un alert per ogni URL
    interessato, quindi un solo difetto presente su venti pagine
    arriverebbe venti volte e affonderebbe il punteggio da solo. Si
    penalizza la regola violata, con un fattore di diffusione da 1x
    (un URL) a 2x (molti). E' la stessa correzione applicata ad
    axe-core in C8.

    Funzione pura: verificabile senza un daemon ZAP.
    """
    per_regola: Dict[str, dict] = {}
    for alert in alerts:
        chiave = str(alert.get("pluginId") or alert.get("alertRef")
                     or alert.get("name") or alert.get("alert") or "?")
        # ZAP usa "risk": "High"; alcune versioni "High (Medium)",
        # dove il secondo valore e' la confidenza.
        livello = str(alert.get("risk") or "Informational").split(" ")[0]
        voce = per_regola.setdefault(chiave, {
            "risk": livello,
            "name": alert.get("alert") or alert.get("name") or chiave,
            "urls": set(),
        })
        if alert.get("url"):
            voce["urls"].add(alert["url"])

    penalita = 0.0
    conteggio: Dict[str, int] = {}
    for voce in per_regola.values():
        quanti = max(len(voce["urls"]), 1)
        diffusione = 1.0 + min(quanti, 10) / 10.0
        penalita += ZAP_PENALTIES.get(voce["risk"], 2) * diffusione
        conteggio[voce["risk"]] = conteggio.get(voce["risk"], 0) + 1

    ordinate = sorted(per_regola.values(),
                      key=lambda v: -ZAP_PENALTIES.get(v["risk"], 2))
    issues = ["[ZAP:%s] %s (%d URL)"
              % (v["risk"], v["name"], max(len(v["urls"]), 1))
              for v in ordinate[:5]]
    return {"score": max(0, round(100 - penalita)),
            "alerts_by_risk": conteggio,
            "rules_violated": len(per_regola),
            "issues": issues}


def connect_zap():
    """Client ZAP se un daemon risponde, altrimenti None."""
    try:
        from zapv2 import ZAPv2
    except ImportError:
        return None
    try:
        client = ZAPv2(apikey=ZAP_API_KEY or None,
                       proxies={"http": ZAP_PROXY, "https": ZAP_PROXY})
        # version e' una PROPRIETA', non un metodo: con le
        # parentesi si ottiene un TypeError, non un errore di
        # connessione, e la diagnosi sarebbe fuorviante.
        client.core.version
        return client
    except Exception:
        # Qualunque cosa vada storta qui significa "niente ZAP": non
        # deve mai interrompere l'audit.
        return None


def _attendi(stato, scan_id: str, scadenza: float) -> bool:
    """Attende il completamento di una scansione. False se scade."""
    while time.time() < scadenza:
        try:
            if int(stato(scan_id)) >= 100:
                return True
        except (ValueError, TypeError, requests.RequestException):
            return False
        time.sleep(ZAP_ATTESA)
    return False


def run_zap(url: str, client=None) -> Optional[tuple]:
    """Spider, active scan e alert: (alerts, completata). None se fallisce."""
    client = client or connect_zap()
    if client is None:
        return None
    scadenza = time.time() + ZAP_TIMEOUT_SCAN
    try:
        scan_id = client.spider.scan(url)
        spider_ok = _attendi(client.spider.status, scan_id, scadenza)
        scan_id = client.ascan.scan(url)
        ascan_ok = _attendi(client.ascan.status, scan_id, scadenza)
        alerts = list(client.core.alerts(baseurl=url) or [])
        # Gli alert parziali di una scansione interrotta valgono piu'
        # di niente, ma spacciarli per completi no: il chiamante deve
        # poterlo dire nel referto.
        return alerts, (spider_ok and ascan_ok)
    except Exception:
        return None


def audit_headers(url: str) -> dict:
    """Ripiego: controllo di superficie sui soli header HTTP.

    Non e' un WAPT. Lo status "surface" lo dichiara a chi legge il
    referto, cosi' che 100/100 qui non venga scambiato per un sito
    scansionato e trovato pulito.
    """
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
    except requests.RequestException as exc:
        return {"score": None, "status": "unavailable", "tool": "HTTP-Headers",
                "issues": ["Sito irraggiungibile: %s" % type(exc).__name__]}

    score = 100
    issues = []
    for header, (penalita, messaggio) in SECURITY_HEADERS.items():
        if header not in resp.headers:
            issues.append(messaggio)
            score -= penalita
    return {"score": max(0, score), "status": "surface",
            "tool": "HTTP-Headers", "issues": issues}


def audit(context: dict) -> dict:
    """Area 7: sicurezza, con ZAP quando un daemon e' raggiungibile."""
    url = context["url"]
    client = context.get("_zap_client") or connect_zap()
    if client is not None:
        print("  ZAP raggiunto su %s: scansione in corso "
              "(puo' richiedere diversi minuti)..." % ZAP_PROXY)
        esito_zap = run_zap(url, client)
        if esito_zap is not None:
            alerts, completa = esito_zap
            esito = score_from_alerts(alerts)
            issues = list(esito["issues"])
            if not completa:
                issues.insert(0, "Scansione ZAP interrotta dal timeout: "
                                 "i rilievi sono parziali")
            return {"score": esito["score"], "tool": "ZAP",
                    "complete": completa,
                    "alerts_by_risk": esito["alerts_by_risk"],
                    "rules_violated": esito["rules_violated"],
                    "issues": issues}
        print("  ZAP non ha completato: ripiego sui soli header HTTP.")
    return audit_headers(url)
