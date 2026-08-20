#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from urllib.robotparser import RobotFileParser

from mars_core import USER_AGENT, norm_host

# Crawler degli assistenti IA e di chi li alimenta. Un sito che li
# esclude non verra' citato: e' il primo fattore di citabilita', prima
# di qualunque considerazione sul contenuto.
CRAWLER_IA = {
    "GPTBot": "OpenAI, addestramento e ricerca di ChatGPT",
    "OAI-SearchBot": "OpenAI, indice di ricerca di ChatGPT",
    "ChatGPT-User": "OpenAI, navigazione su richiesta dell'utente",
    "ClaudeBot": "Anthropic, addestramento",
    "Claude-Web": "Anthropic, navigazione",
    "anthropic-ai": "Anthropic, agente storico",
    "PerplexityBot": "Perplexity",
    "CCBot": "Common Crawl, alimenta molti modelli",
    "Google-Extended": "Google, Gemini e Vertex",
    "Applebot-Extended": "Apple Intelligence",
    "Bytespider": "ByteDance",
    "Amazonbot": "Amazon",
    "meta-externalagent": "Meta",
}

# Penalita' per gravita'. Sostituiscono il vecchio 100 - len(issues)*15,
# che dava lo stesso peso a un noindex sull'intero sito e a un lastmod
# mancante. Scelta editoriale dichiarata.
PESI = {"critico": 40, "grave": 20, "medio": 8, "lieve": 3}


def _rilievo(gravita: str, testo: str) -> Tuple[str, str]:
    return (gravita, testo)


def controlla_robots(context: dict) -> List[Tuple[str, str]]:
    """robots.txt: esistenza e regole per i crawler IA.

    Distingue tre casi che il codice precedente confondeva: nessuna
    regola (i crawler passano, ma per silenzio), permesso esplicito, e
    blocco esplicito. Solo il terzo e' un difetto per la citabilita' —
    ed e' un difetto grave, perche' nessun'altra area puo' compensarlo.
    """
    robots = context.get("robots") or {}
    if not robots.get("found"):
        return [_rilievo("medio", "robots.txt assente: i crawler non "
                                  "hanno indicazioni")]

    parser = RobotFileParser()
    parser.parse((robots.get("text") or "").splitlines())
    url = context["url"]
    bloccati, citati = [], []
    for agente in CRAWLER_IA:
        if not parser.can_fetch(agente, url):
            bloccati.append(agente)
        if agente.lower() in (robots.get("text") or "").lower():
            citati.append(agente)

    rilievi = []
    if bloccati:
        rilievi.append(_rilievo(
            "critico", "robots.txt BLOCCA %d crawler IA: %s"
                       % (len(bloccati), ", ".join(sorted(bloccati)[:5]))))
    if not citati:
        rilievi.append(_rilievo(
            "lieve", "Nessuna regola esplicita per i crawler IA: passano "
                     "per silenzio, non per scelta"))
    if not parser.can_fetch(USER_AGENT, url):
        rilievi.append(_rilievo("grave", "robots.txt esclude anche questo "
                                         "audit dalla home"))
    return rilievi


def controlla_sitemap(context: dict) -> List[Tuple[str, str]]:
    """Sitemap: esistenza, leggibilita', ampiezza, lastmod."""
    info = context.get("sitemap") or {}
    rilievi = []
    if not info.get("found"):
        rilievi.append(_rilievo("grave", "Nessuna sitemap utilizzabile: le "
                                         "pagine sono state trovate seguendo "
                                         "i link"))
        return rilievi
    if not info.get("from_robots"):
        rilievi.append(_rilievo("lieve", "La sitemap non e' dichiarata in "
                                         "robots.txt (trovata su "
                                         "/sitemap.xml)"))
    if info.get("unreadable"):
        rilievi.append(_rilievo("medio", "%d file di sitemap illeggibili o "
                                         "non validi" % info["unreadable"]))
    urls = info.get("urls") or 0
    if urls and not info.get("with_lastmod"):
        rilievi.append(_rilievo("lieve", "Nessun <lastmod> nella sitemap: i "
                                         "crawler non sanno cosa e' "
                                         "cambiato"))
    return rilievi


def controlla_indicizzabilita(context: dict) -> List[Tuple[str, str]]:
    """meta robots, X-Robots-Tag e canonical, pagina per pagina.

    X-Robots-Tag va guardato accanto al meta: agisce allo stesso modo
    ma viaggia negli header, quindi non compare nel DOM ed e' il modo
    piu' facile per escludersi dagli indici senza accorgersene.
    """
    pages = context.get("pages") or {}
    if not pages:
        return []
    noindex, senza_canonical, canonical_altrove = [], [], []
    for url, dati in pages.items():
        direttive = "%s %s" % (dati.get("meta_robots") or "",
                               dati.get("x_robots_tag") or "")
        if "noindex" in direttive:
            noindex.append(url)
        canonical = (dati.get("canonical") or "").strip()
        if not canonical:
            senza_canonical.append(url)
        elif norm_host(canonical) and norm_host(canonical) != norm_host(url):
            canonical_altrove.append(url)

    rilievi = []
    if noindex:
        gravita = "critico" if len(noindex) == len(pages) else "grave"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine con 'noindex' (meta robots o "
                     "X-Robots-Tag)" % (len(noindex), len(pages))))
    if canonical_altrove:
        rilievi.append(_rilievo(
            "grave", "%d pagine con canonical verso un altro host: il "
                     "contenuto viene attribuito altrove"
                     % len(canonical_altrove)))
    if senza_canonical:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine senza <link rel=\"canonical\">"
                     % (len(senza_canonical), len(pages))))
    return rilievi


def audit(context: dict) -> dict:
    """Area 1: indicizzabilità, robots.txt, sitemap, crawler IA.

    Copre le quattro cose che il nome dell'area promette. Il punteggio
    e' pesato per gravita': un 'noindex' su tutto il sito e un
    <lastmod> mancante non possono valere uguale, come invece
    accadeva con la penalita' fissa di prima.
    """
    rilievi: List[Tuple[str, str]] = []
    rilievi += controlla_robots(context)
    rilievi += controlla_sitemap(context)
    rilievi += controlla_indicizzabilita(context)

    penalita = sum(PESI.get(g, 5) for g, _ in rilievi)
    conteggio: Dict[str, int] = {}
    for gravita, _ in rilievi:
        conteggio[gravita] = conteggio.get(gravita, 0) + 1

    ordinati = sorted(rilievi, key=lambda r: -PESI.get(r[0], 5))
    return {
        "score": max(0, 100 - penalita),
        "issues": ["[%s] %s" % (g, t) for g, t in ordinati],
        "findings_by_severity": conteggio,
        "ai_crawlers_checked": len(CRAWLER_IA),
    }
