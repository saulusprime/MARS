#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Tuple

from mars_core import AREA_PREFIX

# ======================================================================
# Le lingue del referto (U9.1 / Fase 9 di UPGRADE.md)
# ----------------------------------------------------------------------
# L'italiano e' la lingua CANONICA e non sta in questo file: vive nei
# moduli, dove il rilievo nasce, e in mars_fixes.py per `fix` ed
# `example`. Qui c'e' solo cio' che l'italiano non e', e la ragione e'
# la stessa per cui mars_fixes.py e' un catalogo e non sei manciate di
# stringhe sparse: se l'italiano vivesse in due forme — letterale nel
# modulo e riga di catalogo — le due divergerebbero senza che nulla si
# rompa.
#
# Ne discende la regola di questo modulo: **si traduce PER CHIAVE, e in
# mancanza si ripiega sull'italiano campo per campo, mai sollevando**.
# Un referto in inglese con tre righe italiane e' un referto; un referto
# che si interrompe su un template sbagliato non lo e'.
#
# ----------------------------------------------------------------------
# Perche' due lingue e non cinque (decisione D4, ratificata il
# 2026-08-25)
#
# UPGRADE.md prevede it/en/fr/de/es sul modello di marsbeacon, e
# prevede di riusarne i cataloghi «dove i controlli coincidono».
# Misurato prima di cominciare: il catalogo del riferimento ha 145
# chiavi, MARS ne emette 49, e **ne coincidono quattro**
# (`tech.canonical.missing`, `tech.robots.ai_blocked`,
# `tech.robots.missing`, `tech.sitemap.missing`). Il motivo e'
# strutturale e non si chiude con una rinomina: il riferimento copre
# `tech`/`sem`/`lex`/`sd`/`rrf` e non ha una sola chiave `wcag.`,
# `sec.` o `seo.`, che sono tre delle nove aree di MARS.
#
# Le traduzioni quindi si scrivono, non si copiano — e quattro lingue
# scritte senza che nessuno qui dentro possa verificarle sarebbero
# quattro lingue di qualita' NON MISURATA, cioe' il contrario del
# principio 5. Due lingue verificabili valgono piu' di cinque
# dichiarate.
#
# **E' un livello inferiore al riferimento, ed e' dichiarato**: qui,
# in UPGRADE.md e nel referto stesso. Aggiungere una lingua costa un
# catalogo in piu' in questo file e una voce in LINGUE: l'impianto non
# assume che le lingue siano due.
# ======================================================================

LINGUA_CANONICA = "it"

#: Le lingue in cui il referto sa uscire. L'ordine e' quello dell'aiuto
#: della CLI; la canonica sta per prima perche' e' il predefinito.
LINGUE: Tuple[str, ...] = ("it", "en")


def normalizza_lingua(lang: Optional[str]) -> str:
    """La lingua richiesta, o quella canonica se non la conosciamo.

    Non solleva e non indovina: `pt` non diventa `es` per vicinanza.
    Chi deve DICHIARARE il ripiego — il referto lo fa, come gia' fa
    `mars_citability` con un mercato sconosciuto — confronta il
    risultato con la richiesta, che qui non si perde.
    """
    scelta = (lang or "").strip().lower()
    return scelta if scelta in LINGUE else LINGUA_CANONICA


# ======================================================================
# I rilievi che NON si traducono qui
# ----------------------------------------------------------------------
# Tre famiglie prendono i testi dallo strumento che ha fatto la misura,
# non da noi: e' la stessa regola che U3.2 ha scritto per i `fix`.
# Tradurle a mano significherebbe due cose sbagliate insieme —
# riscrivere in italiano cio' che axe, ZAP e Lighthouse dicono meglio
# di noi, e farlo invecchiare accanto a loro a ogni release.
#
# La lingua di quelle tre si chiede allo strumento (U9.3): Lighthouse
# ha `--locale`, axe ha `axe.configure({locale})`, ZAP parla inglese e
# basta. Cio' che lo strumento non sa dire nella lingua del referto ci
# resta, e il referto lo dichiara invece di far finta.
# ======================================================================

FAMIGLIE_DALLO_STRUMENTO: Tuple[str, ...] = ("wcag.axe.", "sec.zap.",
                                             "seo.lh.")


def dallo_strumento(key: str) -> bool:
    """Vero se il testo del rilievo viene da axe, ZAP o Lighthouse."""
    return key.startswith(FAMIGLIE_DALLO_STRUMENTO)


# ======================================================================
# Il catalogo dei rilievi, per lingua e per chiave
# ----------------------------------------------------------------------
# Un campo assente qui NON e' una dimenticanza da riempire con una
# stringa vuota: significa "resta l'italiano", ed e' il ripiego
# dichiarato. Le chiavi senza `fix` sono le stesse che non ce l'hanno in
# mars_fixes.py, per le tre esclusioni scritte li' (i `*.status.*` sono
# rilievi sulla SCANSIONE, non sul sito; i derivati di `mars_citability`
# ridicono un difetto gia' prescritto altrove; le famiglie dinamiche
# vengono dallo strumento).
# ======================================================================

_RILIEVI_EN: Dict[str, Dict[str, str]] = {

    # --- Area 1: tecnica -----------------------------------------------
    "tech.robots.missing": {
        "title": "robots.txt missing: crawlers have no instructions",
        "fix": "Publish a robots.txt that declares the sitemap: without "
               "one, crawlers proceed by trial and error.",
        "example": "# /robots.txt\n"
                   "User-agent: *\n"
                   "Disallow:\n"
                   "\n"
                   "Sitemap: https://example.com/sitemap.xml",
    },
    "tech.robots.ai_blocked": {
        # `elenco` e non `bloccati`: il titolo italiano ne mostra
        # cinque e il dato canonico li porta tutti, quindi la lista
        # gia' troncata viaggia nei params. Senza, l'inglese li
        # elencherebbe tutti e le due viste direbbero cose diverse.
        "title": "robots.txt BLOCKS %(n)d AI crawlers: %(elenco)s",
        "fix": "Remove the Disallow that blocks the agents you want to "
               "be cited by. Adding a permissive group at the end is "
               "not enough: for each agent the FIRST group that names "
               "it wins, so the rule must be fixed where it is.",
        "example": "# robots.txt — the group must be FIXED, not appended\n"
                   "# before:\n"
                   "#   User-agent: GPTBot\n"
                   "#   Disallow: /\n"
                   "# after:\n"
                   "User-agent: GPTBot\n"
                   "Disallow:",
    },
    "tech.robots.ai_unmentioned": {
        "title": "No explicit rule for AI crawlers: they pass by "
                 "silence, not by choice",
        "fix": "Name the AI agents explicitly in robots.txt: today they "
               "pass by silence, and tomorrow a generic rule could "
               "exclude them without anyone noticing.",
        "example": "# robots.txt — explicit permission\n"
                   "User-agent: GPTBot\n"
                   "Disallow:\n"
                   "\n"
                   "User-agent: ClaudeBot\n"
                   "Disallow:",
    },
    "tech.robots.self_blocked": {
        "title": "robots.txt excludes this audit from the home page too",
        "fix": "robots.txt excludes the URL the audit starts from: fix "
               "the rule, or declare ownership of the domain if the "
               "exclusion is deliberate and you want to analyse it "
               "anyway.",
    },
    "tech.sitemap.missing": {
        "title": "No usable sitemap: the pages were found by following "
                 "links",
        "fix": "Publish an XML sitemap and declare it in robots.txt.",
        "example": '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/'
                   'sitemap/0.9">\n'
                   '  <url>\n'
                   '    <loc>https://example.com/</loc>\n'
                   '    <lastmod>2026-08-24</lastmod>\n'
                   '  </url>\n'
                   '</urlset>',
    },
    "tech.sitemap.not_in_robots": {
        "title": "The sitemap is not declared in robots.txt (found at "
                 "/sitemap.xml)",
        "fix": "Declare the sitemap in robots.txt: it is the first "
               "place a crawler looks for it.",
        "example": "# at the end of robots.txt\n"
                   "Sitemap: https://example.com/sitemap.xml",
    },
    "tech.sitemap.unreadable": {
        "title": "%(n)d sitemap files unreadable or invalid",
        "fix": "Check that the sitemap files answer 200 and are valid "
               "XML: an unreadable sitemap counts as a missing one.",
    },
    "tech.sitemap.no_lastmod": {
        "title": "No <lastmod> in the sitemap: crawlers cannot tell "
                 "what changed",
        "fix": "Add <lastmod> to every <url>: it is what tells a "
               "crawler which pages to revisit.",
        "example": "<url>\n"
                   "  <loc>https://example.com/services/</loc>\n"
                   "  <lastmod>2026-08-24</lastmod>\n"
                   "</url>",
    },
    "tech.index.noindex": {
        "title": "%(pagine)d/%(totale)d pages excluded from indexes "
                 "(noindex or none, in meta robots or X-Robots-Tag)",
        "fix": "Remove `noindex` from the meta robots tag and from the "
               "X-Robots-Tag on the pages that must be found. If the "
               "exclusion is deliberate, those pages will never be "
               "cited.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.canonical.cross_host": {
        "title": "%(pagine)d pages with a canonical pointing to another "
                 "host: the content is credited elsewhere",
        "fix": "The canonical points to another host: unless that is "
               "deliberate, fix it — you are declaring that the good "
               "version of this page lives somewhere else.",
    },
    "tech.index.nofollow": {
        "title": "%(pagine)d/%(totale)d pages do not let their own "
                 "links be followed (nofollow or none)",
        "fix": "Remove `nofollow`: it prevents internal links from "
               "being followed, so the rest of the site stays "
               "unreachable from that page.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.canonical.missing": {
        "title": '%(pagine)d/%(totale)d pages without '
                 '<link rel="canonical">',
        "fix": 'Declare <link rel="canonical"> on every page: without '
               'it, two URLs serving the same content compete with '
               'each other.',
        "example": '<link rel="canonical" '
                   'href="https://example.com/services/">',
    },

    # --- Area 2: SEO (stato; i controlli vengono da Lighthouse) --------
    "seo.status.no_tool": {
        "title": "Lighthouse not found in PATH",
    },
    "seo.status.not_scored": {
        "title": "Lighthouse did not compute the SEO category for this "
                 "page",
    },
    "seo.status.timeout": {
        "title": "Lighthouse: timeout after %(timeout)ds",
    },
    "seo.status.failed": {
        "title": "Lighthouse failed",
    },

    # --- Area 5: dati strutturati --------------------------------------
    "sd.status.no_pages": {
        "title": "No pages to analyse",
    },
    "sd.jsonld.missing": {
        "title": "No JSON-LD / Schema.org found",
        "fix": "Add a JSON-LD block describing the organisation or the "
               "service: it is the form assistants read without having "
               "to infer it from the prose.",
        "example": '<script type="application/ld+json">\n'
                   '{"@context": "https://schema.org",\n'
                   ' "@type": "LocalBusiness",\n'
                   ' "name": "Example Centre",\n'
                   ' "url": "https://example.com/",\n'
                   ' "telephone": "+39 0521 123456",\n'
                   ' "address": {"@type": "PostalAddress",\n'
                   '  "streetAddress": "Via Roma 1",\n'
                   '  "addressLocality": "Parma",\n'
                   '  "postalCode": "43121",\n'
                   '  "addressCountry": "IT"}}\n'
                   '</script>',
    },
    "sd.jsonld.block_malformed": {
        "title": "%(n)d malformed JSON-LD blocks",
        "fix": "Fix the syntax of the block: a JSON-LD that does not "
               "parse is ignored entirely, not in part.",
        "example": '// before — the trailing comma makes the block '
                   'invalid\n'
                   '{"@type": "Service",}\n'
                   '// after\n'
                   '{"@type": "Service"}',
    },
    "sd.jsonld.block_empty": {
        "title": "%(n)d empty JSON-LD blocks",
        "fix": 'Remove the empty <script type="application/ld+json"> '
               'blocks, or fill them in: an empty block is noise for '
               'whoever reads the page and for whoever analyses it.',
    },

    # --- Area 6: accessibilita' (i controlli statici e lo stato) -------
    "wcag.status.no_pages": {
        "title": "No pages to analyse",
    },
    "wcag.status.partial": {
        "title": "axe did not examine %(mancate)d of the %(tentate)d "
                 "pages in the sample",
    },
    "wcag.status.no_fixes": {
        "title": "axe correction texts unavailable: the Italian "
                 "axe-core locale is missing",
        "detail": "expected at node_modules/axe-core/locales/it.json",
    },
    "wcag.lang.missing": {
        "title": "%(pagine)d pages out of %(totale)d without a 'lang' "
                 "attribute",
        "fix": "Declare the language on the <html> element: without "
               "it, a screen reader reads the text with the wrong "
               "pronunciation and a search engine cannot tell which "
               "language to index it under.",
        "example": '<html lang="en">',
    },
    "wcag.img.alt_missing": {
        "title": "%(immagini)d/%(totale)d images with no alternative "
                 "text",
        "fix": 'Give alternative text to every image that carries '
               'information, and alt="" to decorative ones: the two are '
               'different things, and omitting the attribute is '
               'neither.',
        "example": '<img src="/room.jpg" alt="The treatment room">\n'
                   '<img src="/wave.svg" alt="">',
    },
    "wcag.heading.skip": {
        "title": "%(salti)d skips in the heading hierarchy (e.g. h2 "
                 "followed by h4)",
        "fix": "Do not skip heading levels: the hierarchy is the "
               "outline people navigate a page by without seeing it. "
               "To make a heading smaller, use CSS.",
    },
    "wcag.form.label_missing": {
        "title": "%(campi)d form fields with no label",
        "fix": "Tie every field to a <label>: a `placeholder` does not "
               "replace one, because it disappears as soon as you type.",
        "example": '<label for="name">Name</label>\n'
                   '<input id="name" name="name" type="text">',
    },
    "wcag.table.th_missing": {
        "title": "%(tabelle)d data tables with no <th> headers",
        "fix": "Use <th> for the headers of data tables, with `scope`: "
               "without it, every cell is read out without saying which "
               "column it belongs to.",
        "example": '<table>\n'
                   '  <tr><th scope="col">Treatment</th>'
                   '<th scope="col">Duration</th></tr>\n'
                   '  <tr><td>Drainage</td><td>50 minutes</td></tr>\n'
                   '</table>',
    },
    "wcag.tabindex.positive": {
        "title": "%(elementi)d elements with a positive tabindex: they "
                 "alter the navigation order",
        "fix": 'Remove positive tabindex values: they force a '
               'navigation order different from the visual one. To make '
               'an element reachable, `tabindex="0"` is enough.',
    },
    "wcag.link.generic": {
        "title": '%(link)d links with generic text ("click here", '
                 '"read more")',
        "fix": "Put the destination in the link, not the action: people "
               "who navigate by list of links read that text alone, "
               "outside the sentence that contained it.",
        "example": '<!-- instead of: <a href="/prices/">click here</a> '
                   '-->\n'
                   '<a href="/prices/">The treatment price list</a>',
    },

    # --- Area 7: sicurezza ---------------------------------------------
    "sec.headers.hsts_missing": {
        "title": "HSTS missing",
        "fix": "Add Strict-Transport-Security. Start with a short "
               "max-age and ADD includeSubDomains only after checking "
               "that every subdomain answers over HTTPS: the commitment "
               "cannot be revoked before it expires.",
        "example": "# nginx — one day, to begin with\n"
                   "add_header Strict-Transport-Security "
                   "\"max-age=86400\" always;",
    },
    "sec.headers.csp_missing": {
        "title": "CSP missing",
        "fix": "Add Content-Security-Policy. It is worth starting in "
               "observation only with -Report-Only and reading the "
               "violations before enforcing it — but the finding stands "
               "until you move to the real header.",
        "example": "# nginx — observe first\n"
                   "add_header Content-Security-Policy-Report-Only "
                   "\"default-src 'self'\" always;\n"
                   "# then, once the violations are at zero\n"
                   "add_header Content-Security-Policy "
                   "\"default-src 'self'\" always;",
    },
    "sec.headers.xframe_missing": {
        "title": "X-Frame-Options missing",
        "fix": "Stop third parties from framing the site: "
               "X-Frame-Options DENY if it must never be framed, "
               "SAMEORIGIN if you frame it yourself.",
        "example": "# nginx\n"
                   "add_header X-Frame-Options \"SAMEORIGIN\" always;",
    },
    "sec.status.unreadable": {
        "title": "Headers unreadable",
    },
    "sec.status.passive_only": {
        "title": "Passive scan only: the active scan requires "
                 "--i-own-this-domain",
    },
    "sec.status.partial": {
        "title": "ZAP scan interrupted by the timeout and stopped: the "
                 "findings are partial",
    },
    "sec.status.not_stopped": {
        "title": "ZAP scan timed out and was NOT stopped: it carries on "
                 "in the ZAP daemon, and the findings here are partial",
    },

    # --- Area 8: citabilita' -------------------------------------------
    # I sette segnali per due esiti. Le voci sono scritte una per una,
    # e non generate da `mars_citability.SEGNALI`, perche' quel modulo
    # e' un PLUGIN: si carica dal filesystem a runtime, e importarlo qui
    # lo renderebbe obbligatorio per tradurre un referto che magari non
    # lo contiene. La deriva la coglie un test, che il plugin puo'
    # importarlo.
    "cit.tecnica.weak": {
        "title": "Weak signal: Access and indexability (%(value).0f/100)",
    },
    "cit.tecnica.unmeasured": {
        "title": "Signal not measured: Access and indexability",
    },
    "cit.seo.weak": {
        "title": "Weak signal: SEO quality (%(value).0f/100)",
    },
    "cit.seo.unmeasured": {
        "title": "Signal not measured: SEO quality",
    },
    "cit.recuperabilita.weak": {
        "title": "Weak signal: Hybrid retrievability (RRF consensus) "
                 "(%(value).0f/100)",
    },
    "cit.recuperabilita.unmeasured": {
        "title": "Signal not measured: Hybrid retrievability (RRF "
                 "consensus)",
    },
    "cit.answer_shaped.weak": {
        "title": "Weak signal: Answer-shaped content (%(value).0f/100)",
    },
    "cit.answer_shaped.unmeasured": {
        "title": "Signal not measured: Answer-shaped content",
    },
    "cit.dati_strutturati.weak": {
        "title": "Weak signal: Structured data (%(value).0f/100)",
    },
    "cit.dati_strutturati.unmeasured": {
        "title": "Signal not measured: Structured data",
    },
    "cit.accessibilita.weak": {
        "title": "Weak signal: Accessibility (%(value).0f/100)",
    },
    "cit.accessibilita.unmeasured": {
        "title": "Signal not measured: Accessibility",
    },
    "cit.sicurezza.weak": {
        "title": "Weak signal: Security (%(value).0f/100)",
    },
    "cit.sicurezza.unmeasured": {
        "title": "Signal not measured: Security",
    },
    "cit.status.no_results": {
        "title": "Requires the other areas: run the full audit (CLI or "
                 "POST /audit/full)",
    },
    "cit.status.unknown_market": {
        "title": "Market '%(requested)s' unknown: using '%(used)s'",
    },
    "cit.status.no_composite": {
        "title": "Composite index not computable",
    },

    # --- Area 9: giudizio LLM ------------------------------------------
    "llm.status.disabled": {
        "title": "LLM judgement disabled (--llm off)",
    },
    "llm.status.not_attempted": {
        "title": "ANTHROPIC_API_KEY not present: LLM judgement not run "
                 "(--llm on to try anyway)",
    },
    "llm.status.no_library": {
        "title": "anthropic library not installed (pip install -r "
                 "requirements-optional.txt)",
    },
    "llm.status.no_chunks": {
        "title": "No passage to evaluate",
    },
    "llm.status.no_credentials": {
        "title": "No usable Anthropic credentials",
    },
    "llm.status.api_failed": {
        "title": "Anthropic API error",
    },
    "llm.status.bad_call": {
        "title": "Invalid call",
    },
    "llm.status.unreadable": {
        "title": "Judgement not interpretable",
    },
    "llm.status.no_score": {
        "title": "The model answered without giving a citability score",
    },
}

# Il fallimento di un'area indossa nove chiavi — una per prefisso —
# perche' e' il referto a sintetizzarlo quando il modulo e' caduto e non
# puo' parlare per se'. Il controllo pero' e' UNO, quindi la voce e' una
# sola e le nove chiavi si derivano da `AREA_PREFIX`: un'area nuova
# porta con se' la propria traduzione, invece di ripiegare in silenzio.
_ERRORE_EN = {"title": "Area not computed: the module failed"}
for _prefisso in sorted(set(AREA_PREFIX.values())) + ["area"]:
    _RILIEVI_EN.setdefault("%s.status.error" % _prefisso, dict(_ERRORE_EN))

RILIEVI: Dict[str, Dict[str, Dict[str, str]]] = {"en": _RILIEVI_EN}

#: I campi di un rilievo che questo modulo sa tradurre. Gli altri —
#: `url`, `params`, `weight`, `severity` — sono dati, non prosa.
CAMPI_TRADOTTI: Tuple[str, ...] = ("title", "detail", "fix", "example")


def _params_leggibili(params: Mapping[str, object]) -> Dict[str, object]:
    """I params come li vuole un template: le liste gia' unite.

    `%(urls)s` su una lista Python stamperebbe `['a', 'b']`, apici
    quadre e virgolette comprese. Unire qui invece che in ogni template
    e' anche l'unico modo perche' la regola sia una sola.
    """
    leggibili: Dict[str, object] = {}
    for nome, valore in params.items():
        if isinstance(valore, (list, tuple)):
            leggibili[nome] = ", ".join(str(v) for v in valore)
        else:
            leggibili[nome] = valore
    return leggibili


def finding_texts(source: object, lang: str = LINGUA_CANONICA
                  ) -> Dict[str, str]:
    """I quattro testi di un rilievo nella lingua del referto.

    `source` e' un rilievo gia' serializzato — un dict, che e' la forma
    in cui attraversa il referto — oppure qualunque oggetto con gli
    stessi attributi (un `Finding`). Torna sempre tutti e quattro i
    campi, anche vuoti, cosi' che il chiamante non debba distinguere
    "campo assente" da "campo non tradotto".

    **Non solleva mai.** Un template incoerente coi params — un
    `%(pagine)d` dove il modulo passa `pagine` come stringa, una chiave
    rinominata in un modulo e non qui — lascia in piedi l'italiano di
    quel campo e non tocca gli altri. E' la degradazione dichiarata del
    principio 2 applicata alla prosa: un referto con una riga nella
    lingua sbagliata si legge, uno interrotto a meta' no.
    """
    if isinstance(source, Mapping):
        dati = {campo: str(source.get(campo) or "")
                for campo in CAMPI_TRADOTTI}
        key = str(source.get("key") or "")
        params = dict(source.get("params") or {})  # type: ignore[arg-type]
    else:
        dati = {campo: str(getattr(source, campo, "") or "")
                for campo in CAMPI_TRADOTTI}
        key = str(getattr(source, "key", "") or "")
        params = dict(getattr(source, "params", None) or {})

    lingua = normalizza_lingua(lang)
    if lingua == LINGUA_CANONICA or not key:
        return dati

    voce = RILIEVI.get(lingua, {}).get(key) or {}
    if not voce:
        return dati

    leggibili = _params_leggibili(params)
    for campo, template in voce.items():
        if campo not in dati:
            continue
        try:
            dati[campo] = template % leggibili
        except (KeyError, TypeError, ValueError):
            # Params incoerenti col template: resta l'italiano di
            # QUESTO campo, e gli altri tre si traducono lo stesso.
            continue
    return dati
