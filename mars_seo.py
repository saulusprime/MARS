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

LIGHTHOUSE_TIMEOUT = 120  # secondi: Lighthouse puo' bloccarsi a lungo


def audit(context: dict) -> dict:
    """Punteggio SEO via Lighthouse, se disponibile nel PATH.

    L'URL arriva dall'utente (via CLI o dal corpo di una richiesta API):
    va passato come argomento di una lista con shell=False, MAI interpolato
    in una stringa di shell. Con shell=True un URL come
    'https://x/; rm -rf ~ #' verrebbe eseguito dalla shell.
    """
    url = context["url"]
    lighthouse = shutil.which("lighthouse")
    if not lighthouse:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non trovato nel PATH"]}
    try:
        result = subprocess.run(
            [lighthouse, url, "--output=json", "--quiet",
             "--chrome-flags=--headless"],
            capture_output=True, text=True, check=True,
            timeout=LIGHTHOUSE_TIMEOUT,
        )
        data = json.loads(result.stdout)
        return {"score": data["categories"]["seo"]["score"] * 100}
    except subprocess.TimeoutExpired:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse: timeout dopo %ds"
                           % LIGHTHOUSE_TIMEOUT]}
    except (subprocess.CalledProcessError, json.JSONDecodeError,
            KeyError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non riuscito: %s"
                           % type(exc).__name__]}
