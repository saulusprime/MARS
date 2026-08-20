#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from mars_core import (LexicalRetriever, describe_chunk,
                       reciprocal_rank_fusion)


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
    queries = context.get("queries") or []
    per_query = []
    for query in queries:
        scores = bm25.get_scores(query.lower().split())
        rank = sorted(range(len(scores)),
                      key=lambda i: scores[i], reverse=True)
        per_query.append({
            "query": query,
            "rank": rank,
            "top_chunk": describe_chunk(chunks[rank[0]]) if rank else None,
        })

    # Rango aggregato: le classifiche per query si fondono con lo
    # stesso RRF che il progetto usa fra recuperatori. Un chunk in alto
    # su piu' domande e' piu' citabile di uno che vince una sola volta.
    fusi = reciprocal_rank_fusion([p["rank"] for p in per_query])
    rank = [indice for indice, _ in fusi]

    return {
        "rank": rank,
        "per_query": per_query,
        "queries": queries,
        "top_chunk": describe_chunk(chunks[rank[0]]) if rank else "N/A",
        "top_url": chunks[rank[0]]["url"] if rank else "N/A",
    }
