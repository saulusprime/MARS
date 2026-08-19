#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

import requests
from urllib.parse import urljoin


def audit(context):
    issues = []
    url = context["url"]
    try:
        r = requests.get(urljoin(url, "/robots.txt"), timeout=5)
        if r.status_code != 200:
            issues.append("robots.txt mancante")
        else:
            content = r.text.lower()
            if "gptbot" not in content and "ccbot" not in content and "claudebot" not in content:
                issues.append("Nessuna regola esplicita per crawler IA (GPTBot/ClaudeBot)")
    except Exception:
        issues.append("Errore rete robots.txt")
    return {"score": max(0, 100 - len(issues)*15), "issues": issues}
