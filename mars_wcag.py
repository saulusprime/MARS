#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from bs4 import BeautifulSoup

def audit(context):
    issues = []
    score = 100
    first_page = list(context["pages"].values())[0]
    soup = BeautifulSoup(first_page['html'], 'lxml')
    
    if not soup.html or not soup.html.has_attr('lang'):
        issues.append("Attributo 'lang' mancante nel tag <html>")
        score -= 20
        
    total_imgs = 0
    missing_alt = 0
    for url, data in context["pages"].items():
        soup = BeautifulSoup(data['html'], 'lxml')
        imgs = soup.find_all('img')
        total_imgs += len(imgs)
        missing_alt += len([i for i in imgs if not i.has_attr('alt') and not i.has_attr('aria-label')])
        
    if total_imgs > 0 and missing_alt > 0:
        ratio = missing_alt / total_imgs
        issues.append(f"{missing_alt}/{total_imgs} immagini prive di attributo 'alt'")
        score -= int(ratio * 30)
        
    return {"score": max(0, score), "issues": issues}