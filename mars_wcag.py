#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from bs4 import BeautifulSoup

def audit(context: dict) -> dict:
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"]}

    issues = []
    score = 100
    # lang e' gia' estratto dal crawler: evita una riparsificazione
    # dell'HTML. Piu' severo del vecchio has_attr(): un lang="" vuoto
    # non e' una dichiarazione di lingua valida (WCAG 3.1.1).
    first_page = next(iter(pages.values()))
    if not first_page.get("lang"):
        issues.append("Attributo 'lang' mancante nel tag <html>")
        score -= 20


    total_imgs = 0
    missing_alt = 0
    for url, data in pages.items():
        soup = BeautifulSoup(data['html'], 'lxml')
        imgs = soup.find_all('img')
        total_imgs += len(imgs)
        missing_alt += len([i for i in imgs if not i.has_attr('alt') and not i.has_attr('aria-label')])
        
    if total_imgs > 0 and missing_alt > 0:
        ratio = missing_alt / total_imgs
        issues.append(f"{missing_alt}/{total_imgs} immagini prive di attributo 'alt'")
        score -= int(ratio * 30)
        
    return {"score": max(0, score), "issues": issues}