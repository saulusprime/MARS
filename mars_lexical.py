#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from mars_config import PENALITA, SOGLIA_PAROLE
from mars_core import (SEV_INFO, Finding, LexicalRetriever, describe_chunk,
                       normalizza_severita, reciprocal_rank_fusion,
                       RRF_K, tokenize)


def _rilievo(gravita: str, testo: str, chiave: str,
             istanze: Optional[Tuple[str, int]] = None,
             **params: object) -> Finding:
    """Imbuto unico dei rilievi dell'area.

    `source_severity` conserva la parola italiana grezza, perche' e'
    quella che compare fra parentesi quadre nella vista compatta: la
    scala canonica collassa "grave" e "medio" entrambe in `warning`, e
    chi conosce la scala di MARS perderebbe la differenza.
    """
    if istanze is not None:
        nome, quante = istanze
        params[nome] = quante
        params["instances"] = quante
    severita, peso = normalizza_severita("mars", gravita)
    return Finding(
        area="mars_lexical", severity=severita, weight=peso,
        source_severity=gravita, title=testo, key=chiave,
        params=dict(params, penalty=float(PENALITA[gravita])))


def controlla_lunghezza(pages: dict) -> List[Finding]:
    """Le pagine troppo corte perche' l'indice lessicale le valorizzi."""
    parole = {url: len(((pagina or {}).get("text") or "").split())
              for url, pagina in pages.items()}
    sottili = sorted(url for url, quante in parole.items()
                     if quante < SOGLIA_PAROLE)
    if not sottili:
        return []
    return [_rilievo(
        "grave",
        "%d/%d pagine sotto le %d parole" % (len(sottili), len(parole),
                                             SOGLIA_PAROLE),
        "lex.words.thin", istanze=("pagine", len(sottili)),
        totale=len(parole),
        soglia=SOGLIA_PAROLE,
        media=sum(parole.values()) // len(parole),
        urls=sottili)]


def controlla_titoli(pages: dict) -> List[Finding]:
    """I `<title>` ripetuti fra pagine diverse.

    E' un fatto FRA pagine, e nessun'altra area di MARS puo' vederlo:
    Lighthouse misura `document-title` su una pagina sola. Il titolo
    **assente** invece resta suo, e contarlo qui darebbe due rilievi
    sullo stesso difetto.
    """
    per_titolo: Dict[str, List[str]] = defaultdict(list)
    for url, pagina in pages.items():
        titolo = ((pagina or {}).get("title") or "").strip()
        if titolo:
            per_titolo[titolo].append(url)
    ripetuti = {titolo: urls for titolo, urls in per_titolo.items()
                if len(urls) > 1}
    if not ripetuti:
        return []
    coinvolte = sorted(url for urls in ripetuti.values() for url in urls)
    return [_rilievo(
        "medio",
        "%d/%d pagine con un <title> ripetuto" % (len(coinvolte), len(pages)),
        "lex.title.dup", titoli=len(ripetuti),
        istanze=("pagine", len(coinvolte)), totale=len(pages),
        esempi=" | ".join(sorted(ripetuti)[:3]),
        urls=coinvolte)]


def controlla_query(per_query: List[dict]) -> List[Finding]:
    """Le query su cui il corpus non offre un solo riscontro.

    R23 ha insegnato a non spacciare l'ordine di scansione per una
    classifica; il fatto restava pero' dentro `per_query`, e nessuno
    ne faceva un controllo. **Nessun `urls`**: la domanda senza
    risposta non e' un difetto di una pagina, e sceglierne una per
    colorare la treemap sarebbe inventare l'indirizzo.
    """
    vuote = [voce["query"] for voce in per_query if not voce["matched"]]
    if not vuote:
        return []
    return [_rilievo(
        "grave",
        "%d/%d query senza un riscontro lessicale" % (len(vuote),
                                                      len(per_query)),
        "lex.query.no_match", istanze=("senza_riscontro", len(vuote)),
        totale=len(per_query), esempi=" | ".join(vuote[:3]))]


def _giudizio(pages: dict, per_query: List[dict]) -> dict:
    """Punteggio e rilievi, separati dalla classifica (U13).

    Senza pagine non c'e' nulla da giudicare: un punteggio calcolato
    sulle sole query direbbe 100 su un sito da cui non e' stata letta
    una riga. `score: None` piu' `unavailable` e' il contratto, e non
    e' la stessa cosa di uno zero.
    """
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"],
                "findings": [Finding(
                    area="mars_lexical", severity=SEV_INFO,
                    key="lex.status.no_pages",
                    title="Nessuna pagina da analizzare").as_dict()]}
    rilievi = (controlla_lunghezza(pages) + controlla_titoli(pages)
               + controlla_query(per_query))
    ordinati = sorted(rilievi, key=lambda f: -f.params["penalty"])
    penalita = sum(f.params["penalty"] for f in rilievi)
    return {
        # round() e non il solo max(): le penalita' sono float, e senza
        # arrotondare il JSON porterebbe 80.0 dove le altre aree
        # portano 80 — un cambio di contratto invisibile ai test,
        # perche' 80 == 80.0.
        "score": max(0, round(100 - penalita)),
        "issues": ["[%s] %s" % (f.source_severity, f.title)
                   for f in ordinati],
        "findings": [f.as_dict() for f in ordinati],
    }


def audit(context: dict) -> dict:
    """Area 3: BM25 sui chunk del sito, e i segnali che lo alimentano.

    Indicizza i CHUNK, non le pagine: prima questo modulo lavorava su
    pagine e mars_semantic su chunk, e i due ranking venivano poi fusi
    dall'RRF come se si riferissero alle stesse unita'. Non era cosi',
    e il "consenso" che ne usciva non aveva il significato dichiarato.

    Da U13 l'area produce **anche un punteggio**: la classifica dice
    quale passaggio vincerebbe, i tre controlli dicono se il sito
    offre a BM25 qualcosa da valorizzare. Il punteggio resta fuori dal
    complessivo — vedi `AREE_FUORI_DAL_COMPLESSIVO` in mars_report —
    perche' quest'area ci entra gia' dai segnali derivati.

    Copertura dichiarata: i controlli riguardano la LUNGHEZZA e la
    DISTINGUIBILITA' dei documenti, cioe' le due grandezze su cui BM25
    normalizza. La qualita' dei termini — sigle senza forma estesa,
    sinonimi, riformulazioni — non e' misurata.
    """
    chunks = context["chunks"]
    corpus = []
    for chunk in chunks:
        # L'heading pesa: e' il segnale piu' forte di cosa tratti il
        # passaggio, ed e' spesso la forma in cui la domanda e' posta.
        parti = [chunk.get("heading") or "", chunk.get("text") or ""]
        corpus.append(" ".join(p for p in parti if p))

    # tokenize() e non .lower().split(): corpus e query devono passare
    # per la stessa funzione, altrimenti "funziona?" nell'indice non
    # incontra mai "funziona" nella query. Vive in mars_core proprio
    # perche' i due punti non possano divergere.
    bm25 = LexicalRetriever([tokenize(c) for c in corpus])
    queries = context.get("queries") or []
    per_query = []
    for query in queries:
        scores = bm25.get_scores(tokenize(query))
        # Nessun termine della query compare nel corpus: i punteggi
        # sono tutti zero e sorted() restituisce l'ORDINE NATURALE dei
        # chunk. Quella non e' una classifica, e' l'ordine di
        # scansione — e presentarla come tale faceva riportare un
        # consenso 3/3, il risultato migliore possibile, proprio dove
        # non c'era un solo riscontro.
        trovato = any(s > 0 for s in scores)
        rank = sorted(range(len(scores)),
                      key=lambda i: scores[i], reverse=True)
        per_query.append({
            "query": query,
            "rank": rank,
            "matched": trovato,
            "top_chunk": (describe_chunk(chunks[rank[0]])
                          if rank and trovato else None),
        })

    # Rango aggregato: le classifiche per query si fondono con lo
    # stesso RRF che il progetto usa fra recuperatori. Un chunk in alto
    # su piu' domande e' piu' citabile di uno che vince una sola volta.
    # Entrano solo le classifiche che portano informazione: fondere un
    # ordine di scansione con una classifica vera sposta il risultato
    # senza dire nulla sul sito.
    fusi = reciprocal_rank_fusion([p["rank"] for p in per_query
                                   if p["matched"]],
                                  context.get("rrf_k", RRF_K))
    rank = [indice for indice, _ in fusi]

    esito = {
        # Quest'area produce una CLASSIFICA oltre al voto: e' un fatto
        # del dato, non una particolarita' della vista. Finche' stava
        # solo nelle viste, queste intercettavano il modulo per NOME e
        # stampavano "Analizzato" — anche quando il modulo era andato
        # in errore, ingoiandone il motivo.
        "status": "ranking",
        # Quale recuperatore ha prodotto la classifica. Un rango senza
        # il nome di chi l'ha calcolato non e' verificabile.
        "tool": "BM25 (k1=%.1f, b=%.2f)" % (bm25.k1, bm25.b),
        "rank": rank,
        "per_query": per_query,
        "queries": queries,
        "top_chunk": describe_chunk(chunks[rank[0]]) if rank else "N/A",
        "top_url": chunks[rank[0]]["url"] if rank else "N/A",
    }
    # La classifica resta anche quando non c'e' nulla da giudicare: e'
    # l'uscita primaria dell'area, e il giudizio le si aggiunge sopra.
    esito.update(_giudizio(context.get("pages") or {}, per_query))
    return esito
