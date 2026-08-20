#!/usr/bin/env python3
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Dict, List, Optional

LIGHTHOUSE_TIMEOUT = 120  # secondi: Lighthouse puo' bloccarsi a lungo
CATEGORIA = "seo"

# I titoli li traduce Lighthouse, non noi: --locale=it li restituisce
# gia' in italiano, quindi restano allineati allo strumento invece di
# essere una nostra traduzione destinata a invecchiare.
LOCALE = "it"

# Quanti elementi incriminati riportare per audit fallito. Lighthouse
# ne elenca anche decine: bastano i primi per capire dove guardare.
MAX_ELEMENTI = 5


def _descrivi_item(item: object) -> str:
    """Un elemento incriminato in forma leggibile.

    Lighthouse li restituisce in forme diverse a seconda dell'audit:
    una sorgente testuale per is-crawlable, un nodo del DOM per
    image-alt. Si prende cio' che identifica l'elemento e si scarta il
    resto (coordinate, percorsi interni), che non aiuta chi legge.
    """
    if not isinstance(item, dict):
        return str(item)
    sorgente = item.get("source")
    if isinstance(sorgente, str):
        return sorgente
    if isinstance(sorgente, dict):
        return str(sorgente.get("url") or sorgente.get("value") or "")
    nodo = item.get("node")
    if isinstance(nodo, dict):
        return str(nodo.get("selector") or nodo.get("snippet") or "")
    for chiave in ("href", "text", "url", "value"):
        if isinstance(item.get(chiave), str):
            return item[chiave]
    return ""


def estrai_audit(lhr: dict) -> List[Dict[str, object]]:
    """I singoli controlli della categoria SEO, come li elenca Lighthouse.

    Il referto conteneva finora il solo punteggio complessivo: 92/100
    non dice quale controllo sia fallito, mentre e' esattamente quello
    che serve per correggere. Si riportano tutti gli audit della
    categoria — superati, falliti e manuali — perche' un elenco di soli
    fallimenti non permette di sapere che cosa sia stato guardato.

    Funzione pura: si verifica su un LHR salvato, senza avviare nulla.
    """
    categoria = (lhr.get("categories") or {}).get(CATEGORIA) or {}
    audits = lhr.get("audits") or {}
    esito: List[Dict[str, object]] = []
    for ref in categoria.get("auditRefs") or []:
        voce = audits.get(ref.get("id")) or {}
        punteggio = voce.get("score")
        manuale = voce.get("scoreDisplayMode") in ("manual", "notApplicable")
        dettagli = voce.get("details") or {}
        elementi = [d for d in
                    (_descrivi_item(i) for i in
                     (dettagli.get("items") or [])[:MAX_ELEMENTI]) if d]
        esito.append({
            "id": ref.get("id"),
            "title": voce.get("title") or ref.get("id"),
            # Il titolo di Lighthouse cambia gia' fra superato e
            # fallito ("Il documento ha / non ha un elemento <title>"),
            # quindi non serve aggiungerci nulla.
            # "and not manuale" e' una guardia, non una differenza:
            # misurato su tre referti reali, gli audit manuali e non
            # applicabili hanno SEMPRE score None. Serve a rendere la
            # classificazione inequivocabile — superato, fallito e
            # manuale devono partizionare l'elenco — se un giorno
            # Lighthouse cambiasse forma.
            "passed": bool(punteggio) and not manuale,
            "manual": manuale,
            "items": elementi,
        })
    return esito


def riassumi(lhr: dict) -> dict:
    """Il risultato d'area a partire dal referto Lighthouse.

    Separata da audit() perche' e' la parte che contiene le decisioni,
    e va potuta verificare senza Lighthouse installato.
    """
    punteggio = ((lhr.get("categories") or {}).get(CATEGORIA) or {}).get(
        "score")
    if punteggio is None:
        # Lo schema LHR ammette score null: il run e' riuscito, il JSON
        # e' valido, ma la categoria non e' calcolabile. E' un "non
        # misurato", non un errore di Lighthouse — e dirlo giusto vale
        # piu' che dirlo genericamente (lezione di R6).
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non ha calcolato la categoria SEO "
                           "per questa pagina"]}

    controlli = estrai_audit(lhr)
    falliti = [c for c in controlli if not c["passed"] and not c["manual"]]
    superati = [c for c in controlli if c["passed"]]
    manuali = [c for c in controlli if c["manual"]]

    issues = []
    for c in falliti:
        elementi = c["items"]
        issues.append("[Lighthouse] %s%s"
                      % (c["title"],
                         " (%s)" % ", ".join(elementi) if elementi else ""))
    for c in manuali:
        issues.append("[Lighthouse] da verificare a mano: %s" % c["title"])

    impostazioni = lhr.get("configSettings") or {}
    return {
        "score": punteggio * 100,
        "issues": issues,
        "tool": "Lighthouse %s" % (lhr.get("lighthouseVersion") or "?"),
        # Il tipo di dispositivo cambia i risultati e va dichiarato:
        # un referto mobile e uno desktop non sono confrontabili.
        "form_factor": impostazioni.get("formFactor"),
        "audited_url": lhr.get("finalDisplayedUrl") or lhr.get("finalUrl"),
        "audits": controlli,
        "passed": len(superati),
        "failed": len(falliti),
        "manual": len(manuali),
    }


def esegui_lighthouse(url: str, lighthouse: str) -> Optional[dict]:
    """L'unica parte con I/O. None se non e' stato possibile misurare.

    L'URL arriva dall'utente (via CLI o dal corpo di una richiesta API):
    va passato come argomento di una lista con shell=False, MAI
    interpolato in una stringa di shell. Con shell=True un URL come
    'https://x/; rm -rf ~ #' verrebbe eseguito dalla shell.
    """
    result = subprocess.run(
        [lighthouse, url, "--output=json", "--quiet",
         "--chrome-flags=--headless", "--locale=%s" % LOCALE],
        capture_output=True, text=True, check=True,
        timeout=LIGHTHOUSE_TIMEOUT,
    )
    return json.loads(result.stdout)


def audit(context: dict) -> dict:
    """Area 2: SEO via Lighthouse, se disponibile nel PATH.

    Riporta gli stessi controlli che Lighthouse mostra nella sua
    sezione SEO, non il solo punteggio: e' cio' che permette di sapere
    che cosa correggere invece che soltanto quanto si e' preso.
    """
    lighthouse = shutil.which("lighthouse")
    if not lighthouse:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non trovato nel PATH"]}
    try:
        return riassumi(esegui_lighthouse(context["url"], lighthouse))
    except subprocess.TimeoutExpired:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse: timeout dopo %ds"
                           % LIGHTHOUSE_TIMEOUT]}
    except (subprocess.CalledProcessError, json.JSONDecodeError,
            KeyError, TypeError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non riuscito: %s"
                           % type(exc).__name__]}
