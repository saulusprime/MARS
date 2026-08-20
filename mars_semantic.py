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


def question_signals(testo: str, heading: str = "",
                     lingua: str = "") -> List[str]:
    """Segnali che QUESTO passaggio sia in forma di risposta.

    Piu' segnali indipendenti invece di un solo elenco di parole: il
    punto interrogativo e il titolo sono molto piu' affidabili della
    presenza di un termine nel corpo del testo.

    Tutti e tre riguardano il passaggio e nient'altro. Prima il
    "titolo interrogativo" si accendeva se una QUALUNQUE intestazione
    della pagina era una domanda, quindi una sola FAQ marcava
    answer-shaped ogni chunk della pagina e il rapporto arrivava al
    100% su un sito generico: una proprieta' della pagina non puo'
    dire nulla su un suo singolo pezzo (R19).
    """
    segnali = []
    intero = " ".join(x for x in (heading, testo) if x)
    if "?" in intero:
        segnali.append("punto interrogativo")
    if _interrogativo(intero, lingua):
        segnali.append("interrogativo a inizio frase")
    if heading and ("?" in heading or _interrogativo(heading, lingua)):
        # L'heading del chunk, non quelli della pagina: e' il titolo
        # sotto cui questo passaggio vive.
        segnali.append("titolo interrogativo")
    return segnali


def page_signals(pagina: Optional[dict], lingua: str = "") -> List[str]:
    """Segnali che riguardano la PAGINA, non il singolo passaggio.

    Restano nel referto perche' dicono qualcosa di vero — una pagina
    che si dichiara FAQPage sta dichiarando la propria forma — ma non
    entrano in answer_shaped_ratio, che e' una frazione di CHUNK.
    Contarli li' significava moltiplicare un fatto di pagina per il
    numero dei suoi pezzi.
    """
    if not pagina:
        return []
    segnali = []
    # Controllo volutamente grezzo: mars_schema legge gia' il JSON-LD,
    # ma i moduli non si scambiano ancora i risultati.
    if "faqpage" in (pagina.get("html") or "").lower():
        segnali.append("FAQPage JSON-LD")
    return segnali


def audit(context: dict) -> dict:
    chunks = context["chunks"]
    testi = [c.get("text") or "" for c in chunks]
    vec = VectorRetriever(
        testi, context["embeddings_model"], context["force_proxy"],
        hf_token=(context.get("credentials") or {}).get("hf_token"))
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

    # I segnali di pagina si calcolano una volta per PAGINA, e sono
    # contati in pagine. Farlo dentro il ciclo dei chunk non era solo
    # sbagliato nel merito: rifaceva un .lower() sull'intero HTML per
    # ogni chunk della stessa pagina.
    segnali_pagina: dict = defaultdict(int)
    for pag in pagine.values():
        for s in page_signals(pag, lingua_pagina(pag)):
            segnali_pagina[s] += 1

    for chunk, testo in zip(chunks, testi):
        # Ogni chunk porta con se' il proprio URL: niente piu'
        # corrispondenza posizionale con l'elenco delle pagine, che
        # reggeva solo finche' i chunk erano uno per pagina.
        pagina = pagine.get(chunk.get("url"))
        lingua = lingua_pagina(pagina)
        lingue[lingua or "n/d"] += 1
        # L'heading del chunk fa parte del passaggio: "Come funziona?"
        # come titolo e' un segnale forte quanto la stessa frase nel
        # corpo. Quelli delle ALTRE sezioni no: vedi R19.
        segnali = question_signals(testo, chunk.get("heading") or "", lingua)
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
        # Contati in PAGINE, non in chunk, e tenuti separati proprio
        # per non poter rientrare dalla finestra nel rapporto.
        "page_signals": dict(segnali_pagina),
        "n_pages": len(pagine),
        "languages": dict(lingue),
    }
