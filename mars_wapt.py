#!/usr/bin/env python3
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Optional

import requests

ZAP_START_TIMEOUT = 180
ZAP_SCAN_TIMEOUT = 900
ZAP_ALERT_LEVEL = "Informational"

# Penalita' per livello di rischio ZAP. Sono una scelta editoriale, non una
# misura: stanno qui in chiaro perche' siano ispezionabili e discutibili.
ZAP_PENALTIES = {"High": 25, "Medium": 10, "Low": 3, "Informational": 0}

# Header di sicurezza controllati nel ripiego: (penalita', messaggio).
SECURITY_HEADERS = {
    "Strict-Transport-Security": (15, "HSTS mancante"),
    "Content-Security-Policy": (15, "CSP mancante"),
    "X-Frame-Options": (10, "X-Frame-Options mancante"),
}


def score_from_alerts(alerts: list) -> dict:
    """Punteggio derivato dagli alert reali di ZAP.

    Funzione pura: prende la lista di alert gia' letta e non tocca ne'
    rete ne' processi, cosi' e' verificabile con payload sintetici.
    Il difetto che sostituisce assegnava 95 o 60 in base al solo exit
    code, due numeri che non corrispondevano ad alcuna vulnerabilita'.
    """
    penalita = 0
    conteggio: dict[str, int] = {}
    for alert in alerts:
        # ZAP usa "risk": "High"; alcune versioni "High (Medium)",
        # dove il secondo valore e' la confidenza.
        livello = str(alert.get("risk") or "Informational").split(" ")[0]
        conteggio[livello] = conteggio.get(livello, 0) + 1
        penalita += ZAP_PENALTIES.get(livello, 0)

    issues = []
    for livello in ("High", "Medium", "Low"):
        numero = conteggio.get(livello, 0)
        if numero:
            issues.append("ZAP: %d alert di rischio %s" % (numero, livello))
    nomi = sorted({str(a.get("alert") or a.get("name") or "?") for a in alerts
                   if str(a.get("risk") or "").startswith(("High", "Medium"))})
    issues.extend(nomi[:5])

    return {"score": max(0, 100 - penalita), "tool": "ZAP",
            "issues": issues, "alerts_by_risk": conteggio}


def run_zap(url: str, zap_cli: str) -> Optional[list]:
    """Avvia ZAP, scansiona, legge gli alert, spegne. None se fallisce.

    Non si usa --self-contained: spegnerebbe il daemon a fine scansione
    e gli alert non sarebbero piu' interrogabili.
    """
    avviato = False
    try:
        subprocess.run(
            [zap_cli, "start", "--start-options",
             "-config api.disablekey=true"],
            capture_output=True, text=True, check=True,
            timeout=ZAP_START_TIMEOUT)
        avviato = True
        # quick-scan esce con 1 quando TROVA alert: e' il suo modo di
        # segnalare i risultati, non un errore. Niente check=True qui.
        subprocess.run([zap_cli, "quick-scan", "--spider", url],
                       capture_output=True, text=True,
                       timeout=ZAP_SCAN_TIMEOUT)
        res = subprocess.run(
            [zap_cli, "alerts", "-f", "json", "-l", ZAP_ALERT_LEVEL,
             "--exit-code", "False"],
            capture_output=True, text=True, check=True,
            timeout=ZAP_SCAN_TIMEOUT)
        return json.loads(res.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    finally:
        if avviato:
            subprocess.run([zap_cli, "shutdown"], capture_output=True,
                           text=True, timeout=60)


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
    url = context["url"]
    zap_cli = shutil.which("zap-cli")
    if zap_cli:
        print("  Esecuzione ZAP (puo' richiedere diversi minuti)...")
        alerts = run_zap(url, zap_cli)
        if alerts is not None:
            return score_from_alerts(alerts)
        print("  ZAP non ha completato: ripiego sui soli header HTTP.")
    return audit_headers(url)
