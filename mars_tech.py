#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import re
from typing import Dict, List, Set
from urllib.robotparser import RobotFileParser

from mars_core import (USER_AGENT, Finding, norm_host,
                       normalizza_severita)

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

# Direttive che escludono la pagina dagli indici, e direttive che
# impediscono di seguirne i link. `none` sta in entrambe: per Google e
# Bing equivale a `noindex, nofollow`.
#
# `all` — il default esplicito — non compare di proposito: non e' un
# rilievo, e non annulla nulla. Quando le direttive si contraddicono
# (`all, noindex`) vince la piu' restrittiva, ed e' esattamente cio'
# che fa l'intersezione con questi insiemi.
DIRETTIVE_NOINDEX = frozenset({"noindex", "none"})
DIRETTIVE_NOFOLLOW = frozenset({"nofollow", "none"})

# Le direttive sono una lista separata da virgole, con spazi liberi.
_SEPARATORI = re.compile(r"[,\s]+")

# Penalita' per gravita'. Sostituiscono il vecchio 100 - len(issues)*15,
# che dava lo stesso peso a un noindex sull'intero sito e a un lastmod
# mancante. Scelta editoriale dichiarata.
PESI = {"critico": 40, "grave": 20, "medio": 8, "lieve": 3}
# Penalita' di una gravita' che non conosciamo. Non e' teorica: se
# un giorno si aggiungesse un livello e si dimenticasse questa
# tabella, il rilievo peserebbe 5 invece di sparire.
PENALITA_IGNOTA = 5


def _rilievo(gravita: str, testo: str, chiave: str,
             **params: object) -> Finding:
    """Un rilievo dell'area, come dato strutturato.

    Imbuto unico del modulo: ogni rilievo passa di qui, quindi e' qui
    che nasce il Finding e non in tredici punti.

    `source_severity` conserva la parola italiana grezza — "critico",
    "grave" — che e' quella che l'utente vede da sempre nelle issues e
    in `findings_by_severity`. La severita' canonica ci sta accanto,
    non al suo posto: le quattro severita' collassano `grave` e
    `medio` entrambe in `warning`, e chi conosce la scala di MARS
    perderebbe l'informazione.

    `params["penalty"]` porta la penalita' EFFETTIVAMENTE applicata al
    punteggio. Non e' `weight`, che vale 2.0/1.0 ed e' importanza
    relativa: senza il numero vero, la Fase 4 non potrebbe calcolare
    quanto risalirebbe il punteggio d'area se il rilievo fosse risolto.
    """
    severita, peso = normalizza_severita("mars", gravita)
    return Finding(
        area="mars_tech", severity=severita, weight=peso,
        source_severity=gravita, title=testo, key=chiave,
        params=dict(params, penalty=float(PESI.get(gravita, PENALITA_IGNOTA))))


def controlla_robots(context: dict) -> List[Finding]:
    """robots.txt: esistenza e regole per i crawler IA.

    Distingue tre casi che il codice precedente confondeva: nessuna
    regola (i crawler passano, ma per silenzio), permesso esplicito, e
    blocco esplicito. Solo il terzo e' un difetto per la citabilita' —
    ed e' un difetto grave, perche' nessun'altra area puo' compensarlo.
    """
    robots = context.get("robots") or {}
    if not robots.get("found"):
        return [_rilievo("medio", "robots.txt assente: i crawler non "
                                  "hanno indicazioni",
                         "tech.robots.missing")]

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
        # L'elenco troncato viaggia nei params accanto a quello intero
        # perche' il titolo e' prosa, e la prosa si traduce: senza,
        # ogni lingua rifarebbe il troncamento per conto suo e due
        # viste dello stesso rilievo elencherebbero un numero diverso
        # di crawler. Vedi mars_i18n.finding_texts().
        elenco = ", ".join(sorted(bloccati)[:5])
        rilievi.append(_rilievo(
            "critico", "robots.txt BLOCCA %d crawler IA: %s"
                       % (len(bloccati), elenco),
            "tech.robots.ai_blocked",
            # L'elenco COMPLETO: la stringa ne mostra cinque ma il
            # conteggio non e' troncato, quindi con sei crawler bloccati
            # il testo dice un numero ed elenca meno. Il dato canonico
            # non tronca — a troncare e' la vista compatta.
            bloccati=sorted(bloccati), n=len(bloccati), elenco=elenco))
    if not citati:
        rilievi.append(_rilievo(
            "lieve", "Nessuna regola esplicita per i crawler IA: passano "
                     "per silenzio, non per scelta",
            "tech.robots.ai_unmentioned", controllati=len(CRAWLER_IA)))
    if not parser.can_fetch(USER_AGENT, url):
        rilievi.append(_rilievo("grave", "robots.txt esclude anche questo "
                                         "audit dalla home",
                                "tech.robots.self_blocked",
                                agente=USER_AGENT))
    return rilievi


def controlla_sitemap(context: dict) -> List[Finding]:
    """Sitemap: esistenza, leggibilita', ampiezza, lastmod."""
    info = context.get("sitemap") or {}
    rilievi = []
    if not info.get("found"):
        rilievi.append(_rilievo("grave", "Nessuna sitemap utilizzabile: le "
                                         "pagine sono state trovate seguendo "
                                         "i link",
                                "tech.sitemap.missing"))
        return rilievi
    if not info.get("from_robots"):
        rilievi.append(_rilievo("lieve", "La sitemap non e' dichiarata in "
                                         "robots.txt (trovata su "
                                         "/sitemap.xml)",
                                "tech.sitemap.not_in_robots"))
    if info.get("unreadable"):
        rilievi.append(_rilievo("medio", "%d file di sitemap illeggibili o "
                                         "non validi" % info["unreadable"],
                                "tech.sitemap.unreadable",
                                n=info["unreadable"]))
    urls = info.get("urls") or 0
    if urls and not info.get("with_lastmod"):
        rilievi.append(_rilievo("lieve", "Nessun <lastmod> nella sitemap: i "
                                         "crawler non sanno cosa e' "
                                         "cambiato",
                                "tech.sitemap.no_lastmod", urls=urls))
    return rilievi


def direttive_robots(pagina: dict) -> Set[str]:
    """Direttive robots di una pagina — meta e header insieme, come token.

    Il meta `robots` e l'header `X-Robots-Tag` condividono la stessa
    grammatica, quindi si leggono insieme. Si tokenizza invece di
    cercare sottostringhe perche' cosi' l'elenco delle direttive
    riconosciute e' esplicito ed elencabile: `none` significa
    `noindex, nofollow` senza contenere "noindex", e cercare quella
    sottostringa bastava a mancare un sito interamente de-indicizzato.

    L'eventuale prefisso per agente dell'X-Robots-Tag
    (`googlebot: noindex`) resta fra i token e non nasconde la
    direttiva, che viene contata come prima.
    """
    grezzo = "%s,%s" % (pagina.get("meta_robots") or "",
                        pagina.get("x_robots_tag") or "")
    return {t for t in _SEPARATORI.split(grezzo.lower()) if t}


def controlla_indicizzabilita(context: dict) -> List[Finding]:
    """meta robots, X-Robots-Tag e canonical, pagina per pagina.

    X-Robots-Tag va guardato accanto al meta: agisce allo stesso modo
    ma viaggia negli header, quindi non compare nel DOM ed e' il modo
    piu' facile per escludersi dagli indici senza accorgersene.
    """
    pages = context.get("pages") or {}
    if not pages:
        return []
    noindex, nofollow, senza_canonical, canonical_altrove = [], [], [], []
    for url, dati in pages.items():
        direttive = direttive_robots(dati)
        if direttive & DIRETTIVE_NOINDEX:
            noindex.append(url)
        if direttive & DIRETTIVE_NOFOLLOW:
            nofollow.append(url)
        canonical = (dati.get("canonical") or "").strip()
        if not canonical:
            senza_canonical.append(url)
        elif norm_host(canonical) and norm_host(canonical) != norm_host(url):
            canonical_altrove.append(url)

    rilievi = []
    if noindex:
        gravita = "critico" if len(noindex) == len(pages) else "grave"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine escluse dagli indici (noindex o none, "
                     "in meta robots o X-Robots-Tag)"
                     % (len(noindex), len(pages)),
            "tech.index.noindex",
            pagine=len(noindex), totale=len(pages), urls=sorted(noindex)))
    if canonical_altrove:
        rilievi.append(_rilievo(
            "grave", "%d pagine con canonical verso un altro host: il "
                     "contenuto viene attribuito altrove"
                     % len(canonical_altrove),
            "tech.canonical.cross_host",
            pagine=len(canonical_altrove), totale=len(pages),
            urls=sorted(canonical_altrove)))
    if nofollow:
        # Un 'nofollow' non nasconde la pagina: impedisce di raggiungere
        # le altre partendo da li'. Su una pagina sola e' una scelta
        # legittima e frequente; quando e' la regola del sito, la
        # scoperta dipende interamente dalla sitemap. Da qui le due
        # gravita'.
        gravita = "medio" if len(nofollow) == len(pages) else "lieve"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine non fanno seguire i propri link "
                     "(nofollow o none)" % (len(nofollow), len(pages)),
            "tech.index.nofollow",
            pagine=len(nofollow), totale=len(pages), urls=sorted(nofollow)))
    if senza_canonical:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine senza <link rel=\"canonical\">"
                     % (len(senza_canonical), len(pages)),
            "tech.canonical.missing",
            pagine=len(senza_canonical), totale=len(pages)))
    return rilievi


def audit(context: dict) -> dict:
    """Area 1: indicizzabilità, robots.txt, sitemap, crawler IA.

    Copre le quattro cose che il nome dell'area promette. Il punteggio
    e' pesato per gravita': un 'noindex' su tutto il sito e un
    <lastmod> mancante non possono valere uguale, come invece
    accadeva con la penalita' fissa di prima.
    """
    rilievi: List[Finding] = []
    rilievi += controlla_robots(context)
    rilievi += controlla_sitemap(context)
    rilievi += controlla_indicizzabilita(context)

    # Punteggio, ordinamento e conteggio restano sulla scala GREZZA,
    # non su quella canonica. Non e' pigrizia: le quattro severita'
    # collassano "grave" e "medio" entrambe in warning, distinte solo
    # da 2.0 contro 1.0 — un rapporto di 2:1 — mentre PESI le tiene a
    # 20:8, cioe' 2.5:1. Ricalcolare da li' cambierebbe i punteggi in
    # silenzio, e con essi mars_citability e l'indice composito.
    penalita = sum(f.params["penalty"] for f in rilievi)
    conteggio: Dict[str, int] = {}
    for f in rilievi:
        conteggio[f.source_severity] = conteggio.get(f.source_severity, 0) + 1

    ordinati = sorted(rilievi, key=lambda f: -f.params["penalty"])
    return {
        # round() e non il solo max(): le penalita' sono float perche'
        # altre aree le scalano per diffusione, e senza arrotondare il
        # punteggio uscirebbe 9.0 dove prima usciva 9. La vista non
        # cambierebbe (stampa %.0f), ma il JSON si', e sarebbe un
        # cambio di contratto silenzioso — per giunta invisibile ai
        # test, perche' 9 == 9.0.
        "score": max(0, round(100 - penalita)),
        # La vista compatta di sempre, parola per parola: e' sotto test
        # come sottostringa in una decina di punti, ed e' cio' che
        # l'utente legge da C10 in poi.
        "issues": ["[%s] %s" % (f.source_severity, f.title)
                   for f in ordinati],
        # Il dato canonico. La dataclass NON attraversa il confine dei
        # plugin: as_dict() la serializza (principio 3 di CLAUDE.md).
        "findings": [f.as_dict() for f in ordinati],
        "findings_by_severity": conteggio,
        "ai_crawlers_checked": len(CRAWLER_IA),
    }
