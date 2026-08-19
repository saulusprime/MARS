#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from mars_core import LexicalRetriever


def audit(context: dict) -> dict:
    pages = context["pages"]
    corpus_texts = []
    for url, data in pages.items():
        # I moduli non devono fidarsi ciecamente del context: un titolo
        # o un testo a None arriverebbe fino a " ".join() e farebbe
        # cadere l'intero modulo lessicale, e con esso la fusione RRF.
        parts = [data.get("title") or ""]
        parts.extend(str(h) for h in data.get("headings") or [] if h)
        parts.append((data.get("text") or "")[:1000])
        corpus_texts.append(" ".join(p for p in parts if p))
        
    tokenized_corpus = [c.lower().split() for c in corpus_texts]
    bm25 = LexicalRetriever(tokenized_corpus)
    query = "cos'è questo sito"
    scores = bm25.get_scores(query.lower().split())
    rank = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]
    return {"scores": scores, "rank": rank, "top_url": context["urls"][rank[0]] if rank else "N/A"}