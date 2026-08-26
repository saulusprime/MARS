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
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set
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

# Il divieto di frammento. E' la direttiva che pesa di piu' sull'oggetto
# di questo progetto: la pagina resta regolarmente indicizzata e non
# puo' essere CITATA, perche' nessuna riga del suo testo puo' comparire
# in una risposta. `max-snippet:0` e' `nosnippet` scritto diversamente.
# `max-snippet:-1` e' l'opposto — nessun limite — e non sta qui.
DIRETTIVE_NOSNIPPET = frozenset({"nosnippet", "max-snippet:0"})
# `noarchive` vieta la copia in cache, non il frammento: il testo resta
# citabile, quindi non e' la stessa cosa e non ha la stessa gravita'.
DIRETTIVE_NOARCHIVE = frozenset({"noarchive"})

# Le direttive sono una lista separata da virgole, con spazi liberi.
_SEPARATORI = re.compile(r"[,\s]+")

# Alcune direttive portano un valore dopo i due punti, e lo spazio
# intorno ai due punti e' legale: `max-snippet: 0` si spezzerebbe nei
# due token `max-snippet:` e `0`, che non corrispondono a nulla. Si
# ricuciono per NOME, non su ogni `:`, perche' ricucire tutto
# incollerebbe il prefisso per agente alla sua direttiva
# (`googlebot:noindex`) e nasconderebbe un noindex — l'opposto di cio'
# che serve. Le quattro con valore sono elencate per intero anche se
# oggi il modulo ne giudica due: e' la stessa riga, e ometterle
# lascerebbe il difetto in agguato per la prossima che si aggiunge.
_DIRETTIVE_CON_VALORE = re.compile(
    r"\b(max-snippet|max-image-preview|max-video-preview"
    r"|unavailable_after)\s*:\s*")

# La scadenza si legge dal GREZZO, non dai token: il suo valore e' una
# data, e una data puo' contenere spazi e virgole — cioe' esattamente i
# separatori delle direttive. Si cattura tutta la coda e si decide dopo
# dove finisce, in `scadenza_dichiarata()`.
_SCADENZA = re.compile(r"\bunavailable_after\s*:\s*(.*)", re.IGNORECASE)

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


def _direttive_grezze(pagina: dict) -> str:
    """Meta `robots` e `X-Robots-Tag` in una stringa sola.

    Due funzioni leggono le direttive e devono guardare le **stesse**
    fonti: se un giorno se ne aggiungesse una terza qui, una sola delle
    due la vedrebbe, e la differenza non produrrebbe alcun errore.
    """
    return "%s,%s" % (pagina.get("meta_robots") or "",
                      pagina.get("x_robots_tag") or "")


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

    Le direttive con valore (`max-snippet: 0`) arrivano come UN token,
    valore compreso: vedi `_DIRETTIVE_CON_VALORE`.
    """
    grezzo = _DIRETTIVE_CON_VALORE.sub(
        r"\1:", _direttive_grezze(pagina).lower())
    return {t for t in _SEPARATORI.split(grezzo) if t}


def scadenza_dichiarata(pagina: dict) -> Optional[datetime]:
    """La data di `unavailable_after`, o `None` se assente o illeggibile.

    Google ne documenta due formati, e vanno letti entrambi: ISO 8601
    (`2020-09-21`) e RFC 850 (`Saturday, 21-Sep-2020 12:00:00 GMT`).
    Il secondo contiene una virgola, che e' anche il separatore delle
    direttive: tagliare sempre alla prima virgola lascerebbe
    `Saturday`, e la data non si leggerebbe mai. Quindi si prova prima
    la coda intera — il caso normale, la direttiva e' l'ultima — e solo
    se non si legge si taglia alla virgola, che e' il caso di una ISO
    seguita da altre direttive.

    Il valore viene dal sito analizzato: e' dato ostile. Una data che
    non si legge restituisce `None` e non produce alcun giudizio —
    dedurne 'scaduta' sarebbe un rilievo critico su una misura che non
    c'e'.

    Una data senza fuso orario e' letta come UTC: la specifica non lo
    dice, ma il confronto deve avvenire fra istanti confrontabili, e
    l'alternativa e' l'ora locale della macchina che esegue l'audit.
    """
    trovato = _SCADENZA.search(_direttive_grezze(pagina))
    if not trovato:
        return None
    coda = trovato.group(1).strip()
    for candidato in (coda, coda.split(",")[0]):
        for leggi in (datetime.fromisoformat, parsedate_to_datetime):
            try:
                quando = leggi(candidato.strip())
            except (TypeError, ValueError):
                continue
            return (quando if quando.tzinfo
                    else quando.replace(tzinfo=timezone.utc))
    return None


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
    nosnippet, noarchive, scadute = [], [], []
    # Un solo istante per tutte le pagine: leggendo l'orologio dentro il
    # ciclo, due pagine con la stessa data ai due lati di un secondo
    # riceverebbero giudizi diversi, e l'audit non sarebbe riproducibile
    # su se stesso.
    adesso = datetime.now(timezone.utc)
    for url, dati in pages.items():
        direttive = direttive_robots(dati)
        escluso = bool(direttive & DIRETTIVE_NOINDEX)
        if escluso:
            noindex.append(url)
        else:
            # Una data passata e un `noindex` dicono lo stesso fatto:
            # si conta il primo che c'e', non tutti e due.
            scadenza = scadenza_dichiarata(dati)
            if scadenza is not None and scadenza <= adesso:
                scadute.append(url)
                escluso = True
        if direttive & DIRETTIVE_NOFOLLOW:
            nofollow.append(url)
        # Su una pagina gia' fuori dagli indici il divieto di frammento
        # non toglie nulla che non fosse gia' tolto: contarlo anche li'
        # farebbe pagare due volte lo stesso fatto — 80 punti su 100
        # per un difetto solo, e `noindex, nosnippet` e' una scrittura
        # reale, non un caso di laboratorio.
        if not escluso and direttive & DIRETTIVE_NOSNIPPET:
            nosnippet.append(url)
        if direttive & DIRETTIVE_NOARCHIVE:
            noarchive.append(url)
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
    if scadute:
        # Stesso denominatore del divieto di frammento: le pagine non
        # gia' dichiarate fuori dagli indici per altra via.
        gravita = ("critico" if len(scadute) == len(pages) - len(noindex)
                   else "grave")
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine con unavailable_after gia' passato: "
                     "escluse dagli indici come da un noindex"
                     % (len(scadute), len(pages)),
            "tech.index.unavailable_after",
            pagine=len(scadute), totale=len(pages), urls=sorted(scadute)))
    if nosnippet:
        # Il denominatore della gravita' sono le pagine ancora
        # CITABILI, non tutte: se le altre sono gia' escluse dagli
        # indici il sito resta muto lo stesso, e chiamarlo `grave`
        # direbbe che qualcosa si salva. `citabili` non e' mai zero
        # qui, perche' le pagine escluse non entrano in `nosnippet`.
        citabili = len(pages) - len(noindex)
        gravita = "critico" if len(nosnippet) == citabili else "grave"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine indicizzate ma non citabili: nessun "
                     "frammento del loro testo puo' comparire in una "
                     "risposta (nosnippet o max-snippet:0)"
                     % (len(nosnippet), len(pages)),
            "tech.index.nosnippet",
            pagine=len(nosnippet), totale=len(pages),
            urls=sorted(nosnippet)))
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
    if noarchive:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine vietano la copia in cache "
                     "(noarchive): il testo resta citabile, la versione "
                     "archiviata no" % (len(noarchive), len(pages)),
            "tech.index.noarchive",
            pagine=len(noarchive), totale=len(pages),
            urls=sorted(noarchive)))
    if senza_canonical:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine senza <link rel=\"canonical\">"
                     % (len(senza_canonical), len(pages)),
            "tech.canonical.missing",
            pagine=len(senza_canonical), totale=len(pages),
            # L'unico controllo dell'area che sapeva su quali pagine
            # aveva guardato e non lo diceva: gli altri tre dichiarano
            # `urls` da sempre (R47).
            urls=sorted(senza_canonical)))
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
