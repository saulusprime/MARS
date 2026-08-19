#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from __future__ import annotations

import json


def audit(context: dict) -> dict:
    """Area 5: presenza e validita' sintattica del JSON-LD.

    Controlla che i blocchi si analizzino, non che i tipi Schema.org
    siano quelli giusti: la verifica dei tipi e' I11 in TO-DO.md.
    """
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"]}

    issues = []
    score = 100
    found = 0
    for url, data in pages.items():
        # Il JSON-LD grezzo arriva dal crawler: nessuna riparsificazione.
        blocchi = data.get("json_ld") or []
        if not blocchi:
            continue
        found += 1
        for raw in blocchi:
            # Vuoto e malformato sono difetti diversi: prima
            # json.loads(None) dava TypeError, l'except generico lo
            # catturava e riportava "malformato" su un blocco vuoto.
            if not raw:
                issues.append(f"JSON-LD vuoto su {url}")
                score -= 5
                continue
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                issues.append(f"JSON-LD malformato su {url}")
                score -= 10

    if found == 0:
        issues.append("Nessun JSON-LD / Schema.org trovato")
        score -= 50
    return {"score": max(0, score), "issues": issues}
