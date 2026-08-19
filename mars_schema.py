#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

import json
from bs4 import BeautifulSoup

def audit(context: dict) -> dict:
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"]}

    issues = []
    score = 100
    found = 0
    for url, data in pages.items():
        soup = BeautifulSoup(data['html'], 'lxml')
        json_ld = soup.find_all('script', type='application/ld+json')
        if json_ld:
            found += 1
            for script in json_ld:
                # get_text() invece di .string, che su uno script vuoto
                # e' None: dava TypeError, catturato dall'except generico
                # e riportato come "malformato". Vuoto e malformato sono
                # difetti diversi e ora vengono distinti.
                raw = script.get_text(strip=True)
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