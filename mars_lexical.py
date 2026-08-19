#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from __future__ import annotations

from mars_core import LexicalRetriever, describe_chunk


def audit(context: dict) -> dict:
    """BM25 sui chunk del sito.

    Indicizza i CHUNK, non le pagine: prima questo modulo lavorava su
    pagine e mars_semantic su chunk, e i due ranking venivano poi fusi
    dall'RRF come se si riferissero alle stesse unita'. Non era cosi',
    e il "consenso" che ne usciva non aveva il significato dichiarato.
    """
    chunks = context["chunks"]
    corpus = []
    for chunk in chunks:
        # L'heading pesa: e' il segnale piu' forte di cosa tratti il
        # passaggio, ed e' spesso la forma in cui la domanda e' posta.
        parti = [chunk.get("heading") or "", chunk.get("text") or ""]
        corpus.append(" ".join(p for p in parti if p))

    bm25 = LexicalRetriever([c.lower().split() for c in corpus])
    query = "cos'è questo sito"
    scores = bm25.get_scores(query.lower().split())
    rank = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    return {
        "scores": scores,
        "rank": rank,
        "top_chunk": describe_chunk(chunks[rank[0]]) if rank else "N/A",
        "top_url": chunks[rank[0]]["url"] if rank else "N/A",
    }
