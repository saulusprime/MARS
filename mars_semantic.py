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
    # Un titolo e' una domanda quando e' PUNTEGGIATO come tale.
    #
    # Bastava che aprisse con un interrogativo, e su questo cadeva una
    # classe intera di intestazioni standard: "Chi siamo", "Dove
    # siamo", "Come funziona", "Cosa facciamo", "How it works" — nomi
    # di sezione, non domande. Misurato su 209 heading di un sito
    # reale: la vecchia regola ne accendeva 31, la nuova 5, e nessuno
    # dei 26 in piu' era una domanda. Fra questi anche i titoli con i
    # due punti, perche' _INIZIO_FRASE li tratta come inizio di frase:
    # "AI Act: cosa scatta davvero" si accendeva a meta' titolo.
    #
    # Costo dichiarato: le FAQ scritte senza "?" non vengono piu'
    # riconosciute dal titolo. Restano riconoscibili dal corpo, se la
    # domanda vi compare.
    titolo_domanda = bool(heading) and "?" in heading

    # Il titolo entra nel passaggio SOLO se e' una domanda. E' la
    # stessa regola di sopra, applicata una volta sola, e concilia due
    # voci che sembravano in conflitto: per R9 "Come funziona?" come
    # titolo vale quanto la stessa frase nel corpo — quindi accende
    # anche i segnali testuali — mentre per R34 "Chi siamo" non deve
    # accendere nulla.
    #
    # Senza questa riga la correzione non servirebbe a niente, ed e'
    # la meta' che R34 non aveva visto: il rapporto conta un chunk se
    # UN QUALUNQUE segnale e' acceso, quindi restringere il solo
    # "titolo interrogativo" lasciava "Chi siamo" acceso lo stesso
    # attraverso "interrogativo a inizio frase", che leggeva heading e
    # testo uniti. Verificato prima di correggere: answer_shaped_ratio
    # sarebbe rimasto identico.
    intero = " ".join(x for x in (heading if titolo_domanda else "", testo)
                      if x)

    segnali = []
    if "?" in intero:
        segnali.append("punto interrogativo")
    if _interrogativo(intero, lingua):
        segnali.append("interrogativo a inizio frase")
    if titolo_domanda:
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
    # `testi` e `corpus` sono due cose diverse, e la differenza e' R35.
    #
    # Il CORPUS e' cio' che il recuperatore indicizza, e deve essere lo
    # stesso di `mars_lexical` — heading + testo. R10 aveva lavorato
    # perche' i due ranghi si riferissero alle stesse UNITA'; nessuno
    # aveva controllato che leggessero lo stesso CONTENUTO di quelle
    # unita'. Con la parola solo nell'heading il lessicale trovava e il
    # vettoriale no: su un sito con le FAQ nei titoli i due erano in
    # disaccordo per costruzione, e il consenso RRF usciva depresso per
    # una ragione che non riguarda il sito.
    #
    # I TESTI restano il solo testo: `question_signals` riceve gia'
    # l'heading a parte, e `MIN_PAROLE` conta le parole del passaggio.
    # Unirli anche li' conterebbe l'heading due volte.
    testi = [c.get("text") or "" for c in chunks]
    corpus = [" ".join(p for p in ((c.get("heading") or ""),
                                   (c.get("text") or "")) if p)
              for c in chunks]
    vec = VectorRetriever(
        corpus, context["embeddings_model"], context["force_proxy"],
        hf_token=(context.get("credentials") or {}).get("hf_token"))
    queries = context.get("queries") or []
    per_query = []
    for query in queries:
        punteggi = vec.get_scores(query)
        # Come in mars_lexical: senza alcun riscontro i punteggi sono
        # tutti zero e l'ordinamento restituisce l'ordine di scansione,
        # non una classifica. Va distinto, altrimenti due ordini
        # naturali identici vengono letti come consenso perfetto.
        trovato = any(p > 0 for p in punteggi)
        classifica = [i for i, _ in sorted(enumerate(punteggi),
                                           key=lambda x: x[1], reverse=True)]
        per_query.append({
            "query": query,
            "rank": classifica,
            "matched": trovato,
            "top_chunk": (describe_chunk(chunks[classifica[0]])
                          if classifica and trovato else None),
        })
    # Stesso criterio di mars_lexical: le classifiche per query si
    # fondono con l'RRF per ottenere il rango aggregato, e solo quelle
    # che hanno trovato qualcosa vi partecipano.
    rank = [indice for indice, _
            in reciprocal_rank_fusion([p["rank"] for p in per_query
                                       if p["matched"]])]

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
        # Vedi mars_lexical: e' una classifica, e lo dice il dato.
        "status": "ranking",
        # Dei due recuperatori vettoriali il referto non diceva quale
        # avesse girato, benche' cambi il senso di ogni rango: il
        # modello multilingue e il proxy char-TFIDF non misurano la
        # stessa cosa. VectorRetriever lo sa gia'.
        "tool": ("vettoriale %s" % context["embeddings_model"]
                 if vec.use_real else "proxy char-TFIDF"),
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
