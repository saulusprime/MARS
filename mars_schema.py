#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
from typing import List

from mars_core import SEV_INFO, Finding, normalizza_severita

# Quest'area non ha una scala di gravita' propria: nel modulo esiste
# solo l'ordinamento implicito delle penalita', 50/10/5. La gravita'
# canonica e' quindi una SCELTA EDITORIALE, dichiarata qui invece che
# sparsa fra i punti in cui nasce un rilievo.
#
# `missing` resta "grave" e non "critico" benche' costi meta' del
# punteggio: in MARS "critico" vuol dire che il sito e' INVISIBILE agli
# assistenti — e' l'uso che ne fa mars_tech con i crawler IA bloccati e
# con le pagine noindex. Un sito senza JSON-LD e' meno leggibile, non
# invisibile, e appiattire la differenza toglierebbe senso al livello
# piu' alto.
GRAVITA = {"missing": "grave", "malformed": "medio", "empty": "lieve"}

# Penalita' per OCCORRENZA. Sono quelle di sempre: il punteggio non
# cambia con l'adeguamento, e i test lo verificano.
PENALITA = {"missing": 50, "malformed": 10, "empty": 5}


def _rilievo(caso: str, testo: str, chiave: str, quante: int = 1,
             **params: object) -> Finding:
    """Un rilievo dell'area, aggregato per CONTROLLO.

    Un controllo emette un solo Finding anche quando i blocchi difettosi
    sono molti: le occorrenze stanno nei params, non nella cardinalita'
    della lista. La cardinalita' e' accoppiata al punteggio in tutta
    MARS — qui `score -= 5` sta accanto a ogni append — e spezzare un
    controllo in N rilievi farebbe crollare i punteggi di chi li conta.

    `source_severity` resta VUOTO: nessuno strumento ha espresso questa
    gravita', l'abbiamo scelta noi. Le `issues` di quest'area non
    portano alcun prefisso di severita', quindi dichiararne una
    significherebbe attribuire al modulo una scala che non pubblica.
    """
    severita, peso = normalizza_severita("mars", GRAVITA[caso])
    return Finding(
        area="mars_schema", severity=severita, weight=peso,
        title=testo, key=chiave,
        params=dict(params, n=quante,
                    penalty=float(PENALITA[caso] * quante)))


def audit(context: dict) -> dict:
    """Area 5: presenza e validita' sintattica del JSON-LD.

    Controlla che i blocchi si analizzino, non che i tipi Schema.org
    siano quelli giusti: la verifica dei tipi e' I11 in TO-DO.md.
    """
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"],
                "findings": [Finding(
                    area="mars_schema", severity=SEV_INFO,
                    key="sd.status.no_pages",
                    title="Nessuna pagina da analizzare").as_dict()]}

    issues = []
    score = 100
    found = 0
    # Gli URL dei blocchi difettosi, per aggregarli in un rilievo solo.
    vuoti: List[str] = []
    malformati: List[str] = []
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
                score -= PENALITA["empty"]
                vuoti.append(url)
                continue
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                issues.append(f"JSON-LD malformato su {url}")
                score -= PENALITA["malformed"]
                malformati.append(url)

    rilievi: List[Finding] = []
    if found == 0:
        issues.append("Nessun JSON-LD / Schema.org trovato")
        score -= PENALITA["missing"]
        rilievi.append(_rilievo(
            "missing", "Nessun JSON-LD / Schema.org trovato",
            "sd.jsonld.missing", pagine=len(pages)))
    if malformati:
        rilievi.append(_rilievo(
            "malformed", "%d blocchi JSON-LD malformati" % len(malformati),
            "sd.jsonld.block_malformed", len(malformati),
            urls=sorted(set(malformati))))
    if vuoti:
        rilievi.append(_rilievo(
            "empty", "%d blocchi JSON-LD vuoti" % len(vuoti),
            "sd.jsonld.block_empty", len(vuoti), urls=sorted(set(vuoti))))

    ordinati = sorted(rilievi, key=lambda f: -f.params["penalty"])
    return {"score": max(0, score),
            # La vista compatta resta una riga per BLOCCO, com'era: e'
            # sotto test e dice su quale URL sta il difetto.
            "issues": issues,
            "findings": [f.as_dict() for f in ordinati]}
