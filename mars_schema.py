#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

import json
from bs4 import BeautifulSoup

def audit(context):
    issues = []
    score = 100
    found = 0
    for url, data in context["pages"].items():
        soup = BeautifulSoup(data['html'], 'lxml')
        json_ld = soup.find_all('script', type='application/ld+json')
        if json_ld:
            found += 1
            for script in json_ld:
                try:
                    json.loads(script.string)
                except Exception:
                    issues.append(f"JSON-LD malformato su {url}")
                    score -= 10
    if found == 0:
        issues.append("Nessun JSON-LD / Schema.org trovato")
        score -= 50
    return {"score": max(0, score), "issues": issues}