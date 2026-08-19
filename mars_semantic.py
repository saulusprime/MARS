#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from mars_core import VectorRetriever

def audit(context):
    chunks = context["chunks"]
    vec = VectorRetriever(chunks, context["embeddings_model"], context["force_proxy"])
    query = "cos'è questo sito"
    scores = vec.get_scores(query)
    rank = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]
    
    answer_shaped_count = 0
    for chunk in chunks:
        words = chunk.split()
        has_question = any(w in chunk.lower() for w in ["?", "come", "cosa", "perché", "chi", "dove", "quando"])
        is_long_enough = len(words) > 40
        if has_question and is_long_enough:
            answer_shaped_count += 1
            
    return {
        "scores": scores, 
        "rank": rank, 
        "answer_shaped_ratio": answer_shaped_count / len(chunks) if chunks else 0
    }