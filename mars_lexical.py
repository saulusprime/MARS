#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from mars_core import LexicalRetriever

def audit(context):
    pages = context["pages"]
    corpus_texts = []
    for url, data in pages.items():
        parts = [data.get("title", "")] + data.get("headings", []) + [data.get("text", "")[:1000]]
        corpus_texts.append(" ".join(parts))
        
    tokenized_corpus = [c.lower().split() for c in corpus_texts]
    bm25 = LexicalRetriever(tokenized_corpus)
    query = "cos'è questo sito"
    scores = bm25.get_scores(query.lower().split())
    rank = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]
    return {"scores": scores, "rank": rank, "top_url": context["urls"][rank[0]] if rank else "N/A"}