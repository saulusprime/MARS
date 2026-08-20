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
from collections import defaultdict
from typing import List, Optional

from mars_core import (VectorRetriever, describe_chunk,
                       reciprocal_rank_fusion)

MIN_PAROLE = 40

# Termini interrogativi per lingua. Il modello di embedding di default
# e' multilingue: limitarsi all'italiano rendeva la metrica cieca su
# meta' dei siti che lo strumento sa gia' analizzare.
INTERROGATIVI = {
    "it": ("chi", "cosa", "come", "quando", "dove", "perché", "perche",
           "quale", "quali", "quanto", "quanta", "quanti", "quante"),
    "en": ("what", "who", "whom", "whose", "when", "where", "why",
           "how", "which"),
    "es": ("qué", "que", "quién", "cómo", "cuándo", "dónde", "por qué",
           "cuál", "cuánto"),
    "fr": ("qui", "quoi", "comment", "quand", "où", "pourquoi",
           "quel", "quelle", "combien"),
    "de": ("wer", "was", "wie", "wann", "wo", "warum", "welche",
           "wieviel"),
}

# Un interrogativo conta solo a INIZIO FRASE. Misurato: i confini di
# parola eliminano i falsi positivi da sottostringa ("chi" dentro
# chiave, archivio, macchina) ma non quelli grammaticali, perche' in
# italiano "come", "dove" e "quando" sono anche congiunzioni:
# "comodo come la neve", "il luogo dove abbiamo aperto".
_INIZIO_FRASE = r"(?:\A|[.!?;:\n]\s*)"

_REGEX = {
    lingua: re.compile(
        _INIZIO_FRASE + r"(?:" + "|".join(map(re.escape, termini)) + r")\b",
        re.IGNORECASE)
    for lingua, termini in INTERROGATIVI.items()
}


def lingua_pagina(pagina: Optional[dict]) -> str:
    """Codice lingua a due lettere, se fra quelle che sappiamo trattare."""
    codice = ((pagina or {}).get("lang") or "").lower()[:2]
    return codice if codice in _REGEX else ""


def _interrogativo(testo: str, lingua: str = "") -> bool:
    """True se il testo apre una frase con un interrogativo.

    Senza lingua nota si provano tutte: meglio un falso positivo che
    una metrica sistematicamente a zero su ogni sito non italiano.
    """
    lingue = [lingua] if lingua else list(_REGEX)
    return any(_REGEX[cod].search(testo) for cod in lingue)


def question_signals(testo: str, pagina: Optional[dict] = None,
                     lingua: str = "") -> List[str]:
    """Segnali che il contenuto sia in forma di risposta a una domanda.

    Piu' segnali indipendenti invece di un solo elenco di parole: il
    punto interrogativo e i titoli sono molto piu' affidabili della
    presenza di un termine nel corpo del testo.
    """
    segnali = []
    if "?" in testo:
        segnali.append("punto interrogativo")
    if _interrogativo(testo, lingua):
        segnali.append("interrogativo a inizio frase")
    if pagina:
        titoli = pagina.get("headings") or []
        if any("?" in t or _interrogativo(t, lingua) for t in titoli):
            segnali.append("titolo interrogativo")
        # Controllo volutamente grezzo: mars_schema legge gia' il
        # JSON-LD, ma i moduli non si scambiano ancora i risultati.
        if "faqpage" in (pagina.get("html") or "").lower():
            segnali.append("FAQPage JSON-LD")
    return segnali


def audit(context: dict) -> dict:
    chunks = context["chunks"]
    testi = [c.get("text") or "" for c in chunks]
    vec = VectorRetriever(testi, context["embeddings_model"],
                          context["force_proxy"])
    queries = context.get("queries") or []
    per_query = []
    for query in queries:
        punteggi = vec.get_scores(query)
        classifica = [i for i, _ in sorted(enumerate(punteggi),
                                           key=lambda x: x[1], reverse=True)]
        per_query.append({
            "query": query,
            "rank": classifica,
            "top_chunk": (describe_chunk(chunks[classifica[0]])
                          if classifica else None),
        })
    # Stesso criterio di mars_lexical: le classifiche per query si
    # fondono con l'RRF per ottenere il rango aggregato.
    rank = [indice for indice, _
            in reciprocal_rank_fusion([p["rank"] for p in per_query])]

    pagine = context.get("pages") or {}
    conteggio: dict = defaultdict(int)
    lingue: dict = defaultdict(int)
    answer_shaped = 0

    for chunk, testo in zip(chunks, testi):
        # Ogni chunk porta con se' il proprio URL: niente piu'
        # corrispondenza posizionale con l'elenco delle pagine, che
        # reggeva solo finche' i chunk erano uno per pagina.
        pagina = pagine.get(chunk.get("url"))
        lingua = lingua_pagina(pagina)
        lingue[lingua or "n/d"] += 1
        # L'heading fa parte del passaggio: "Come funziona?" come
        # titolo e' un segnale forte quanto la stessa frase nel corpo.
        segnali = question_signals(
            " ".join(x for x in (chunk.get("heading"), testo) if x),
            pagina, lingua)
        for s in segnali:
            conteggio[s] += 1
        if segnali and len(testo.split()) > MIN_PAROLE:
            answer_shaped += 1

    return {
        "rank": rank,
        "per_query": per_query,
        "queries": queries,
        "answer_shaped_ratio": answer_shaped / len(chunks) if chunks else 0,
        "n_chunks": len(chunks),
        "answer_shaped_signals": dict(conteggio),
        "languages": dict(lingue),
    }
