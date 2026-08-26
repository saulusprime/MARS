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
    "tech.index.unavailable_after": {
        "title": "%(pagine)d/%(totale)d pages whose unavailable_after "
                 "has already passed: excluded from indexes as by a "
                 "noindex",
        "fix": "Remove `unavailable_after` or move the date forward: "
               "the one declared has passed, and since then the page "
               "is excluded from indexes as by a noindex.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.index.agent_only": {
        "title": "%(pagine)d/%(totale)d pages with directives restricted "
                 "to an agent that is not an AI assistant (%(agents)s): "
                 "%(directives)s",
        "fix": "Remove the per-agent prefix if the directive must apply "
               "to every crawler. If the restriction is deliberate, note "
               "that the AI assistants are not affected by it.",
    },
    "tech.index.nosnippet": {
        "title": "%(pagine)d/%(totale)d pages indexed but not citable: "
                 "no fragment of their text may appear in an answer "
                 "(nosnippet or max-snippet:0)",
        "fix": "Remove `nosnippet` and `max-snippet:0` from the pages "
               "that must be cited: they stay in the indexes, but no "
               "assistant may quote a single line of them.",
        "example": '<meta name="robots" content="index, follow, '
                   'max-snippet:-1">',
    },
    "tech.index.noarchive": {
        "title": "%(pagine)d/%(totale)d pages forbid the cached copy "
                 "(noarchive): the text stays citable, the archived "
                 "version does not",
        "fix": "Remove `noarchive` unless there is a legal or "
               "contractual reason: it forbids the archived copy that "
               "is used when the original is slow or unreachable.",
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

    # --- Area 3: lessicale (U13) ----------------------------------------
    "lex.status.no_pages": {
        "title": "No pages to analyse",
    },
    "lex.words.thin": {
        "title": "%(pagine)d of %(totale)d pages under %(soglia)d words",
        "fix": "Take the key pages past the threshold with informative "
               "content, not promotional: BM25 normalises term "
               "frequency by document length, and two paragraphs never "
               "reach the frequency the formula rewards.",
    },
    "lex.title.dup": {
        "title": "%(pagine)d of %(totale)d pages share a <title>",
        "fix": "Give every page a distinct <title>: two pages with the "
               "same title compete for the same queries and neither "
               "stands out in the index.",
        "example": '// before \u2014 two pages, one title\n'
                   '<title>Services</title>\n'
                   '<title>Services</title>\n'
                   '// after\n'
                   '<title>Manual lymphatic drainage | Example '
                   'Centre</title>\n'
                   '<title>Post-operative care | Example Centre</title>',
    },
    "lex.query.no_match": {
        "title": "%(senza_riscontro)d of %(totale)d queries with no "
                 "lexical match",
        "fix": "Not one term of the question appears on the site: write "
               "a passage using the words the question is asked with, "
               "not the company's internal synonyms.",
    },

    # --- Area 4: semantica (U13) ----------------------------------------
    "sem.status.no_pages": {
        "title": "No pages to analyse",
    },
    "sem.chunks.none": {
        "title": "No passage extractable from the %(pagine)d pages",
        "fix": "The pages offer no text that can be split into "
               "passages: write flowing paragraphs under headings, "
               "because the passage is the unit a hybrid engine cites.",
    },
    "sem.chunks.few": {
        "title": "%(chunk)d indexable passages across %(pagine)d pages, "
                 "below the %(soglia)d expected",
        "fix": "Increase the number of self-contained thematic "
               "passages: each passage is a separate chance to appear "
               "in a result list.",
    },
    "sem.answer_shaped.low": {
        "title": "%(quota).0f%% of passages in answer form, below the "
                 "%(soglia)d%% expected",
        "fix": "Shape the passages as answers: the heading asks the "
               "question, the opening lines close it. It is the format "
               "assistants quote most readily, because it is already "
               "extractable on its own.",
        "example": "<h2>How long does a session last?</h2>\n"
                   "<p>A session lasts about fifty minutes, initial "
                   "assessment included.</p>",
    },
    "sem.query.no_match": {
        "title": "%(senza_riscontro)d of %(totale)d queries with no "
                 "semantic match",
        "fix": "The vector retriever finds nothing close to the "
               "question: a passage on that topic is missing, not a "
               "keyword to add.",
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
    "sec.status.zap_failed": {
        "title": "ZAP was reachable but the scan did not complete: what "
                 "follows are the HTTP headers alone",
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
    "llm.status.refused": {
        "title": "Request declined by the model's classifiers",
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


# ======================================================================
# La cornice del referto
# ----------------------------------------------------------------------
# Le etichette, i titoli di sezione e le note che il referto scrive di
# suo — tutto cio' che non e' un rilievo. Il catalogo e' indicizzato
# **sul testo italiano** e non su una chiave simbolica, per due ragioni
# che si tengono:
#
# 1. l'italiano resta scritto per esteso nel renderer, dove lo si legge
#    in mezzo al codice che lo usa. Con chiavi simboliche servirebbe un
#    catalogo `it` accanto a questo, e la vista italiana — che e' la
#    canonica, quella congelata nei golden — dipenderebbe da una
#    ricerca che puo' mancare il bersaglio;
# 2. la stessa funzione traduce cosi' anche i testi che arrivano dal
#    DATO e non dal renderer: l'etichetta di un'area, il secchiello di
#    profondita', l'assunzione della superficie. Con chiavi simboliche
#    quelli sarebbero rimasti italiani, perche' nel dato una chiave non
#    c'e'.
#
# Il prezzo e' doppio, e si paga con lo stesso strumento in due modi.
#
# Il primo: cambiare una parola italiana scollega la traduzione in
# silenzio. Lo presidia un test che rilegge i sorgenti — ogni letterale
# passato a `t()` dev'essere a catalogo.
#
# Il secondo: **due significati possono condividere una stringa**, e
# allora una chiave sola non basta. E' successo subito, e per due volte:
# «da migliorare» e' il verdetto di un punteggio fra 50 e 89 («needs
# work») ed e' anche l'etichetta dei punti deboli del giudizio LLM («to
# improve»); e «click» in italiano non cambia al plurale, quindi
# `_plurale(3, "click", "click")` chiederebbe due volte la stessa parola
# e in inglese uscirebbe «3 click». Da qui il `contesto` di `t()`, che e'
# il `msgctxt` di gettext: si aggiunge SOLO dove la collisione c'e', e in
# mancanza si ripiega sulla chiave nuda.
# ======================================================================

_CORNICE_EN: Dict[str, str] = {

    # --- Testata e cornice generale ------------------------------------
    "           MARS BEACON - REPORT FINALE           ":
        "            MARS BEACON - FINAL REPORT           ",
    "%s · %s pagine trovate via %s · %s chunk · mercato %s · v%s":
        "%s · %s pages found via %s · %s chunks · market %s · v%s",
    "*%s · v%s · %s pagine trovate via %s · %s chunk · mercato %s*":
        "*%s · v%s · %s pages found via %s · %s chunks · market %s*",
    "Pagine trovate via   : %s  (%d pagine, %d chunk)":
        "Pages found via      : %s  (%d pages, %d chunks)",
    "Nota: le evidenze citate dal sito analizzato restano nella lingua "
    "del sito.":
        "Note: evidence quoted from the audited site stays in the "
        "language of the site.",
    "Queste aree si esprimono solo in italiano: %s.":
        "These areas speak Italian only: %s.",
    "I testi di questi strumenti restano nella loro lingua: %s.":
        "The texts of these tools stay in their own language: %s.",
    "sitemap": "sitemap",
    "link interni": "internal links",

    # --- Complessivo e verdetti ----------------------------------------
    "COMPLESSIVO": "OVERALL",
    "Complessivo": "Overall",
    "  media pesata di %d misure; escluse %s":
        "  weighted mean of %d measures; %s excluded",
    "media pesata di %d misure · escluse %s":
        "weighted mean of %d measures · %s excluded",
    "Media pesata di %d misure; escluse %s. "
    "Scala dichiarata: critico sotto %d, da migliorare %d-%d, buono "
    "da %d.":
        "Weighted mean of %d measures; %s excluded. Declared scale: "
        "critical below %d, needs work %d-%d, good from %d.",
    "scala dichiarata: critico sotto %d · da migliorare %d-%d · buono "
    "da %d":
        "declared scale: critical below %d · needs work %d-%d · good "
        "from %d",
    "buono": "good",
    "da migliorare": "needs work",
    "critico": "critical",
    "non misurato": "not measured",
    "%.0f su 100": "%.0f out of 100",

    # --- Aree e qualificatori ------------------------------------------
    "Aree": "Areas",
    "Area": "Area",
    "1. Tecnica": "1. Technical",
    "2. SEO": "2. SEO",
    "3. Lessicale": "3. Lexical",
    "4. Semantica": "4. Semantic",
    "5. Dati Strutturati": "5. Structured Data",
    "6. Accessibilità": "6. Accessibility",
    "7. Sicurezza": "7. Security",
    "8. Citabilità IA": "8. AI Citability",
    "9. Giudizio LLM": "9. LLM Judgement",
    "controllo di superficie": "surface check",
    "con una classifica dei passaggi": "with a ranking of passages",
    "disattivato": "disabled",
    "errore del modulo": "module error",
    "scansione parziale": "partial scan",
    "parziale": "partial",
    "superficie": "surface",
    "%d pagine esaminate": "%d pages examined",
    "%d controlli superati, %d falliti": "%d checks passed, %d failed",
    "%s %.0f/100 (1 pagina, scala diversa: la nostra è più severa)":
        "%s %.0f/100 (1 page, different scale: ours is stricter)",
    "altro strumento": "other tool",
    "Nessun rilievo.": "No findings.",
    "Come si aggiusta": "How to fix it",
    "Link a questo rilievo": "Link to this finding",
    "Punteggi per area": "Scores by area",
    "Punteggio": "Score",
    "Con che cosa": "Measured with",
    "Rilievi per area": "Findings by area",
    "Passaggio in testa:": "Top passage:",
    "%.0f%% di %s chunk in forma di risposta.":
        "%.0f%% of %s chunks are answer-shaped.",
    "%s: %d pagine su %d.": "%s: %d pages out of %d.",
    "FAQPage JSON-LD": "FAQPage JSON-LD",

    # --- Nomi degli strumenti che portano una parola italiana ----------
    "HTTP-Headers": "HTTP-Headers",
    "ZAP (attiva)": "ZAP (active)",
    "ZAP (passiva)": "ZAP (passive)",
    "axe-core": "axe-core",
    "markup": "markup",

    # --- Gravità e conteggi --------------------------------------------
    "CRITICO": "CRITICAL",
    "AVVERTENZA": "WARNING",
    "critici": "critical",
    "avvertenze": "warnings",
    "informativi": "informational",
    "**[CRITICO]**": "**[CRITICAL]**",
    "[AVVISO]": "[WARNING]",
    "[INFO]": "[INFO]",
    "[OK]": "[OK]",
    "URL incontrati": "URLs encountered",
    "URL incontrati: %d": "URLs encountered: %d",
    # I tre settori del donut delle pagine. «nessun rilievo le cita» e
    # non «senza rilievi»: il referto non sa quali pagine ogni area
    # abbia guardato, e il nome porta il caveat dentro il disegno (R49).
    "con rilievi": "with findings",
    "nessun rilievo le cita": "no finding cites them",
    "URL scartati": "URLs skipped",
    "Da dove cominciare": "Where to start",

    # --- Superficie -----------------------------------------------------
    "SUPERFICIE": "SURFACE",
    "Superficie": "Surface",
    "Distanza dalla home": "Distance from the home page",
    "home": "home",
    "1 click": "1 click",
    "2 click": "2 clicks",
    "3 click": "3 clicks",
    "4+ click": "4+ clicks",
    "profondità ignota": "unknown depth",
    "Pagine": "Pages",
    "Pagina": "Page",
    "Parole": "Words",
    "Passaggi": "Passages",
    "  %d pagine, %d passaggi (%.2f per pagina, %.0f parole per pagina)":
        "  %d pages, %d passages (%.2f per page, %.0f words per page)",
    "%d pagine, %d passaggi — %.2f per pagina, %.0f parole per pagina.":
        "%d pages, %d passages — %.2f per page, %.0f words per page.",
    "  Con %d parole per pagina i passaggi sarebbero %d, cioe' x%.1f":
        "  With %d words per page there would be %d passages, i.e. x%.1f",
    "Con %d parole per pagina i passaggi sarebbero **%d**, cioè "
    "**x%.1f**.":
        "With %d words per page there would be **%d** passages, i.e. "
        "**x%.1f**.",
    "passaggi recuperabili con %d parole per pagina: %d invece di %d. "
    "Ogni passaggio è un'occasione in più di essere recuperato.":
        "retrievable passages with %d words per page: %d instead of %d. "
        "Every passage is one more chance of being retrieved.",
    "proiezione, non misura: si assume una pagina di contenuto "
    "sostanziale intorno alle 900 parole, da cui il chunker ricava "
    "circa 4 passaggi":
        "a projection, not a measurement: it assumes a page of "
        "substantial content of around 900 words, from which the "
        "chunker gets about 4 passages",

    # --- Treemap --------------------------------------------------------
    "Ogni rettangolo è una pagina, l'area è proporzionale alle parole "
    "recuperabili.":
        "Each rectangle is a page; its area is proportional to the "
        "retrievable words.",
    "Le %d più estese di %s.": "The %d largest out of %s.",
    "%s senza testo indicizzabile non %s superficie da disegnare.":
        "%s with no indexable text %s no surface to draw.",
    "ha": "has",
    "hanno": "have",
    "Il colore è la gravità peggiore dei rilievi che citano la pagina.":
        "Colour is the worst severity among the findings that cite the "
        "page.",
    "%s in grigio: nessun rilievo le cita, che non vuol dire che siano a "
    "posto — non tutte le aree guardano tutte le pagine.":
        "%s in grey: no finding cites them, which does not mean they are "
        "fine — not every area looks at every page.",
    "nessun rilievo la cita": "no finding cites it",
    "%d rilievi, il peggiore: %s": "%d findings, the worst: %s",
    "rilievo critico": "critical finding",
    "avvertenza": "warning",
    "rilievo informativo": "informational finding",
    "Treemap della superficie: %s, la più estesa è %s con %s. I dati "
    "sono nella tabella qui sotto.":
        "Surface treemap: %s, the largest is %s with %s. The figures "
        "are in the table below.",
    "Icona non incorporata: il file non è stato letto. Il referto resta "
    "valido e autoconsistente.":
        "Icon not embedded: the file could not be read. The report is still "
        "valid and self-contained.",
    "La superficie in tabella": "The surface as a table",
    "Rilievi": "Findings",
    "pagina": "page",
    "pagine": "pages",
    "parola": "word",
    "parole": "words",
    "passaggio": "passage",
    "passaggi": "passages",

    # --- Grafo dei link -------------------------------------------------
    "Architettura dei link": "Link architecture",
    "%s e %s fra le pagine scansionate.":
        "%s and %s among the crawled pages.",
    "I %d più linkati di %d.": "The %d most linked out of %d.",
    "L'URL di partenza non è fra le pagine scansionate, quindi "
    "«raggiungibile» qui non vuol dire nulla.":
        "The starting URL is not among the crawled pages, so "
        "“reachable” means nothing here.",
    "%s non si raggiunge dalla home seguendo i link.":
        "%s cannot be reached from the home page by following links.",
    "Il campione è parziale: una pagina può risultare orfana solo "
    "perché chi la linka non è stato scansionato.":
        "The sample is partial: a page may look orphaned only because "
        "whatever links to it was not crawled.",
    "Grafo dei link interni: %s e %s. I dati sono nella tabella qui "
    "sotto.":
        "Internal link graph: %s and %s. The figures are in the table "
        "below.",
    "nodo": "node",
    "nodi": "nodes",
    "collegamento": "link",
    "collegamenti": "links",
    "link": "link",
    "%s in entrata": "%s inbound",
    "%s in uscita": "%s outbound",
    "punto di partenza": "starting point",
    "non raggiunta dalla home per link":
        "not reached from the home page by links",
    "%s dalla home": "%s from the home page",
    "click": "click",
    "plurale|click": "clicks",
    "plurale|link": "links",
    "%d click": "%d clicks",
    "non raggiunta": "not reached",
    "Per collegamenti": "By links",
    "Per distanza": "By distance",
    "Ingrandisci": "Zoom in",
    "Riduci": "Zoom out",
    "Reimposta": "Reset",
    "L'architettura in tabella": "The architecture as a table",
    "Link in entrata": "Inbound links",
    "Link in uscita": "Outbound links",

    # --- Confronto con l'esecuzione precedente --------------------------
    "RISPETTO A PRIMA     : %s": "SINCE LAST RUN       : %s",
    "Rispetto all'esecuzione precedente": "Since the previous run",
    "Confronto con il %s (v%s).": "Compared with %s (v%s).",
    "  Complessivo          %s  (%.0f → %.0f)":
        "  Overall              %s  (%.0f → %.0f)",
    "Prima": "Before",
    "Dopo": "After",
    "Variazione": "Change",
    "invariato": "unchanged",
    "Risolti": "Resolved",
    "Nuovi": "New",
    "risolti": "resolved",
    "nuovi": "new",
    "    · ... e altri %d": "    · ... and %d more",
    "  · ... e altri %d": "  · ... and %d more",
    "  (qualche rilievo non ha una chiave stabile: confrontato sul "
    "titolo)":
        "  (some findings have no stable key: compared by title)",
    "Qualche rilievo non ha una chiave stabile: il confronto usa il "
    "titolo, ed è più debole.":
        "Some findings have no stable key: the comparison falls back on "
        "the title, and is weaker.",

    # --- Piano di interventi --------------------------------------------
    "Piano di interventi": "Remediation plan",
    "PIANO DI INTERVENTI  : nessun rilievo critico o di avvertenza":
        "REMEDIATION PLAN     : no critical or warning findings",
    "PIANO DI INTERVENTI  : %d interventi (%d critici, %d avvertenze)":
        "REMEDIATION PLAN     : %d actions (%d critical, %d warnings)",
    "Nessun rilievo critico o di avvertenza.":
        "No critical or warning findings.",
    "Nessun rilievo critico o di avvertenza: non c'è nulla da mettere "
    "in ordine di priorità.":
        "No critical or warning findings: there is nothing to put in "
        "priority order.",
    "%d interventi (%d critici, %d avvertenze)":
        "%d actions (%d critical, %d warnings)",
    "%d interventi (%d critici, %d avvertenze) · %d quick win.":
        "%d actions (%d critical, %d warnings) · %d quick wins.",
    "%d quick win": "%d quick wins",
    "%d senza recupero": "%d with no recovery",
    "%d senza recupero dichiarato": "%d with no declared recovery",
    "%d senza sforzo dichiarato": "%d with no declared effort",
    "  %d aree su %d; ordinato per gravita', poi per guadagno "
    "dell'indice":
        "  %d areas out of %d; ordered by severity, then by index gain",
    "Ordinato per gravità, poi per guadagno dell'indice di citabilità. "
    "Lo alimentano %d aree su %d; i punti d'area sono la stessa "
    "aritmetica che ha prodotto i punteggi, il guadagno d'indice è una "
    "stima derivata dai pesi per assistente.":
        "Ordered by severity, then by citability index gain. It is fed "
        "by %d areas out of %d; the area points are the same arithmetic "
        "that produced the scores, the index gain is an estimate "
        "derived from the per-assistant weights.",
    "  · ... e altri %d interventi (per intero nel JSON e nell'HTML)":
        "  · ... and %d more actions (in full in the JSON and the HTML)",
    "sforzo: %s": "effort: %s",
    "sforzo non dichiarato": "effort not declared",
    "non dichiarato": "not declared",
    "minuti": "minutes",
    "ore": "hours",
    "giorni": "days",
    "** QUICK WIN": "** QUICK WIN",
    "QUICK WIN": "QUICK WIN",
    " · **QUICK WIN**": " · **QUICK WIN**",
    "+%d punti d'area (%d → %d)": "+%d area points (%d → %d)",
    "+%d punti d'area": "+%d area points",
    "indice +%.2f": "index +%.2f",
    "indice di citabilità +%.2f (mercato %s, stima)":
        "citability index +%.2f (market %s, estimate)",
    "recupero non dichiarato": "recovery not declared",
    "recupero non dichiarato: la penalita' non e' calcolabile per "
    "questo controllo":
        "recovery not declared: the penalty cannot be computed for "
        "this check",
    "recupero non dichiarato: il punteggio dell'area non si "
    "ricostruisce":
        "recovery not declared: the area score cannot be reconstructed",
    "in questa esecuzione il controllo non entra nel punteggio "
    "dell'area":
        "in this run the check does not enter the area score",
    "il punteggio dell'area e' gia' a zero: questa penalita' non lo "
    "muove":
        "the area score is already zero: this penalty does not move it",
    "Correzione:": "Fix:",

    # --- Simulazione RRF ------------------------------------------------
    "Simulazione RRF": "RRF simulation",
    "Simulazione RRF      : Consenso Top-3 = %s su %d chunk":
        "RRF simulation       : Top-3 consensus = %s over %d chunks",
    "  aggregato su %d query": "  aggregated over %d queries",
    "Consenso fra il recuperatore lessicale e quello vettoriale, "
    "aggregato su %d query — la misura più solida, perché un accordo "
    "su una sola domanda può essere un caso.":
        "Consensus between the lexical and the vector retriever, "
        "aggregated over %d queries — the most solid measure, because "
        "agreement on a single question can be chance.",
    "Top Chunk Ibrido     :": "Top hybrid chunk     :",
    "Passaggio più recuperabile:": "Most retrievable passage:",
    "Query": "Query",
    "Consenso": "Consensus",
    "Passaggio migliore": "Best passage",
    "nessun riscontro": "no match",
    "consenso %d/%d": "consensus %d/%d",
    "su %d chunk": "over %d chunks",
    "Recuperabilità": "Retrievability",
    "In forma di risposta": "Answer-shaped",

    # --- Citabilità -----------------------------------------------------
    "Profili di citabilità IA": "AI citability profiles",
    "Profili di citabilità IA  (mercato: %s)":
        "AI citability profiles  (market: %s)",
    "Mercato: %s": "Market: %s",
    "Assistente": "Assistant",
    "Indice": "Index",
    "Indice composito": "Composite index",
    "INDICE COMPOSITO": "COMPOSITE INDEX",
    "n/d": "n/a",
    "stime euristiche dichiarate, non comportamento documentato dai "
    "vendor":
        "declared heuristic estimates, not behaviour documented by the "
        "vendors",
    "Azioni con maggior guadagno di profilo:":
        "Actions with the largest profile gain:",
    " sull'indice": " on the index",
    " — soprattutto %s (+%.2f)": " — above all %s (+%.2f)",

    # --- Giudizio LLM ---------------------------------------------------
    "Giudizio LLM": "LLM judgement",
    "Giudizio LLM (%s)  su %s passaggi":
        "LLM judgement (%s)  on %s passages",
    "%s passaggi valutati": "%s passages evaluated",
    "Modello: %s, su %s passaggi.": "Model: %s, on %s passages.",
    "  Citabilità stimata   :": "  Estimated citability :",
    "Citabilità stimata: **%s/100**": "Estimated citability: **%s/100**",
    "  Passaggio migliore   :": "  Best passage         :",
    "Passaggio migliore:": "Best passage:",
    "Punti di forza": "Strengths",
    "Da migliorare": "To improve",
    "llm|da migliorare": "to improve",

    # --- Cosa non è stato guardato --------------------------------------
    "Cosa non è stato guardato": "What was not looked at",
    "⚠ robots.txt IGNORATO per dichiarazione di proprieta'":
        "⚠ robots.txt IGNORED under a declaration of ownership",
    "robots.txt ignorato per dichiarazione di proprietà del dominio.":
        "robots.txt ignored under a declaration of domain ownership.",
    "URL saltati          :": "Skipped URLs         :",
    "%d URL saltati:": "%d skipped URLs:",

    # --- Intestazioni del CSV -------------------------------------------
    "sito": "site",
    "area": "area",
    "gravita": "severity",
    "peso": "weight",
    "titolo": "title",
    "dettaglio": "detail",
    "correzione": "fix",
    "pagine": "pages",
    "riferimento": "reference",
    "sforzo": "effort",
    "quick_win": "quick_win",
    "sì": "yes",
}

CORNICE: Dict[str, Dict[str, str]] = {"en": _CORNICE_EN}


#: Separatore fra contesto e testo dentro una chiave di cornice. Una
#: barra verticale non compare in nessuna stringa dell'interfaccia, e a
#: differenza di uno `\x00` resta leggibile in un diff.
SEPARATORE_CONTESTO = "|"


def t(testo: str, lang: str = LINGUA_CANONICA, contesto: str = "") -> str:
    """Un testo di cornice nella lingua del referto.

    In mancanza torna l'italiano: e' la stessa regola dei rilievi, e
    vale anche per i testi che vengono dal dato canonico invece che dal
    renderer.

    `contesto` disambigua due significati che in italiano condividono la
    stessa stringa. Si cerca prima la voce con contesto e poi quella
    nuda, cosi' aggiungere un contesto in un punto non obbliga a
    riscrivere il catalogo per tutti gli altri.
    """
    if lang == LINGUA_CANONICA:
        return testo
    catalogo = CORNICE.get(lang, {})
    if contesto:
        con_contesto = catalogo.get(contesto + SEPARATORE_CONTESTO + testo)
        if con_contesto is not None:
            return con_contesto
    return catalogo.get(testo, testo)


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
