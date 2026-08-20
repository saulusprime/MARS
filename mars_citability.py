#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ======================================================================
# AVVERTENZA
# ----------------------------------------------------------------------
# I pesi di questo file sono STIME EURISTICHE DICHIARATE, non
# comportamento documentato dai vendor. Nessun fornitore di assistenti
# IA pubblica come seleziona le fonti da citare: quello che segue e' un
# modello esplicito e discutibile, messo qui in chiaro proprio perche'
# sia discusso e corretto. Un profilo alto non garantisce una citazione,
# e uno basso non la esclude.
#
# Cambiare questi numeri e' previsto. Cambiarli senza scrivere il
# perche' nella colonna delle motivazioni, no.
# ======================================================================

DISCLAIMER = ("stime euristiche dichiarate, non comportamento "
              "documentato dai vendor")

# I sette segnali. Cinque vengono dai punteggi d'area; due sono derivati,
# perche' mars_lexical e mars_semantic producono classifiche e non voti.
SEGNALI = {
    "tecnica": "Accesso e indicizzabilità",
    "seo": "Qualità SEO",
    "recuperabilita": "Recuperabilità ibrida (consenso RRF)",
    "answer_shaped": "Contenuto in forma di risposta",
    "dati_strutturati": "Dati strutturati",
    "accessibilita": "Accessibilità",
    "sicurezza": "Sicurezza",
}

# Peso di ogni segnale per assistente, da 0 (irrilevante) a 3
# (determinante). Scala volutamente grossolana: una scala fine
# suggerirebbe una precisione che non abbiamo.
#
# Le motivazioni, segnale per segnale:
#
# - "tecnica" pesa 3 ovunque: se robots.txt esclude il crawler
#   dell'assistente, tutto il resto e' irrilevante. E' l'unico segnale
#   che puo' azzerare gli altri.
# - "seo" pesa piu' per gli assistenti che si appoggiano a un indice di
#   ricerca generalista; Lighthouse misura per giunta criteri
#   Google-centrici, poco pertinenti fuori da quell'ecosistema.
# - "recuperabilita" e "answer_shaped" pesano molto per chi cita
#   passaggi: sono la misura di quanto il sito somigli a cio' che una
#   pipeline RAG seleziona.
# - "accessibilita" pesa poco ma non zero: markup semantico e testi
#   alternativi rendono il contenuto piu' estraibile, non solo piu'
#   accessibile.
# - "sicurezza" pesa poco: incide sulla reputazione della fonte, non
#   sulla sua recuperabilita'.
PESI_ASSISTENTE: Dict[str, Dict[str, int]] = {
    #                       tec seo rec ans dat acc sic
    "Claude": dict(zip(SEGNALI, (3, 1, 3, 3, 2, 1, 1))),
    "ChatGPT/Perplexity": dict(zip(SEGNALI, (3, 3, 2, 3, 3, 1, 1))),
    "Qwen": dict(zip(SEGNALI, (3, 1, 2, 3, 2, 1, 1))),
    "Kimi": dict(zip(SEGNALI, (3, 1, 2, 3, 2, 1, 1))),
}

# Qwen e Kimi hanno pesi IDENTICI ed e' deliberato: non abbiamo basi
# pubbliche per differenziarli. Inventare una differenza per far
# sembrare la tabella piu' informata sarebbe esattamente il tipo di
# falsa precisione che il principio 6 vieta.

# Il mercato agisce su due piani distinti:
#  - "assistenti": quanto ciascun assistente conta in quel mercato;
#  - "aree": moltiplicatori sui segnali, quando esiste una ragione
#    concreta e non un'impressione.
MERCATI: Dict[str, Dict[str, Dict[str, float]]] = {
    "global": {
        "assistenti": {"Claude": 5, "ChatGPT/Perplexity": 9,
                       "Qwen": 3, "Kimi": 3},
        "aree": {},
    },
    "eu": {
        "assistenti": {"Claude": 6, "ChatGPT/Perplexity": 10,
                       "Qwen": 1, "Kimi": 1},
        # L'European Accessibility Act (direttiva UE 2019/882, in
        # applicazione dal giugno 2025) rende l'accessibilita' un
        # obbligo per molti servizi digitali rivolti al mercato UE:
        # e' una ragione normativa verificabile, non una stima.
        "aree": {"accessibilita": 2.0},
    },
    "us": {
        "assistenti": {"Claude": 6, "ChatGPT/Perplexity": 10,
                       "Qwen": 1, "Kimi": 1},
        "aree": {},
    },
    "cn": {
        "assistenti": {"Claude": 1, "ChatGPT/Perplexity": 1,
                       "Qwen": 9, "Kimi": 9},
        "aree": {},
    },
}


def raccogli_segnali(results: dict) -> Dict[str, Optional[float]]:
    """Riduce i risultati delle aree ai sette segnali, in scala 0-100.

    Un segnale a None significa "non misurato" e viene ESCLUSO dalla
    media, non contato come zero: uno strumento assente non e' un sito
    che ha preso zero.
    """
    def punteggio(modulo: str) -> Optional[float]:
        valore = (results.get(modulo) or {}).get("score")
        return float(valore) if isinstance(valore, (int, float)) else None

    segnali: Dict[str, Optional[float]] = {
        "tecnica": punteggio("mars_tech"),
        "seo": punteggio("mars_seo"),
        "dati_strutturati": punteggio("mars_schema"),
        "accessibilita": punteggio("mars_wcag"),
        "sicurezza": punteggio("mars_wapt"),
        "recuperabilita": None,
        "answer_shaped": None,
    }

    semantico = results.get("mars_semantic") or {}
    if "answer_shaped_ratio" in semantico:
        segnali["answer_shaped"] = 100.0 * semantico["answer_shaped_ratio"]

    # Recuperabilita' ibrida: quanti dei primi tre chunk coincidono fra
    # il recuperatore lessicale e quello vettoriale. E' il consenso RRF,
    # cioe' la misura piu' vicina a "questo passaggio verrebbe davvero
    # selezionato da una ricerca ibrida".
    lessicale = results.get("mars_lexical") or {}
    if "rank" in lessicale and "rank" in semantico:
        primi_lex = set(lessicale["rank"][:3])
        primi_sem = set(semantico["rank"][:3])
        attesi = min(3, len(lessicale["rank"]), len(semantico["rank"]))
        if attesi:
            consenso = len(primi_lex & primi_sem)
            segnali["recuperabilita"] = 100.0 * consenso / attesi
    return segnali


def profilo(assistente: str, segnali: Dict[str, Optional[float]],
            moltiplicatori: Dict[str, float]) -> Optional[float]:
    """Indice 0-100 per un assistente: media pesata dei segnali noti.

    I pesi si rinormalizzano sui soli segnali disponibili, cosi' un'area
    non misurata non abbassa il profilo — lo rende solo meno informato.
    """
    pesi = PESI_ASSISTENTE[assistente]
    totale = somma = 0.0
    for segnale, valore in segnali.items():
        if valore is None:
            continue
        peso = pesi.get(segnale, 0) * moltiplicatori.get(segnale, 1.0)
        somma += peso * valore
        totale += peso
    return round(somma / totale, 1) if totale else None


def audit(context: dict) -> dict:
    """Area 8: profili di citabilità IA stimati dai punteggi d'area.

    Modulo di SINTESI: legge context["results"], quindi deve girare per
    ultimo in MODULES_REGISTRY. Non tocca la rete e non usa chiavi API —
    per misurare le citazioni reali c'e' mars_citations.py.
    """
    results = context.get("results") or {}
    if not any(k.startswith("mars_") for k in results):
        return {"score": None, "status": "unavailable",
                "issues": ["Richiede le altre aree: eseguire l'audit "
                           "completo (CLI o POST /audit/full)"]}

    nome_mercato = (context.get("market") or "global").lower()
    mercato = MERCATI.get(nome_mercato)
    issues = []
    if mercato is None:
        issues.append("Mercato '%s' sconosciuto: uso 'global' (noti: %s)"
                      % (nome_mercato, ", ".join(sorted(MERCATI))))
        nome_mercato, mercato = "global", MERCATI["global"]

    segnali = raccogli_segnali(results)
    moltiplicatori = mercato["aree"]
    profili = {a: profilo(a, segnali, moltiplicatori)
               for a in PESI_ASSISTENTE}

    # Indice composito: media dei profili pesata per quanto ciascun
    # assistente conta nel mercato scelto.
    pesi_mercato = mercato["assistenti"]
    somma = totale = 0.0
    for assistente, valore in profili.items():
        if valore is None:
            continue
        peso = pesi_mercato.get(assistente, 0)
        somma += peso * valore
        totale += peso
    composito = round(somma / totale, 1) if totale else None

    non_misurati: List[str] = [SEGNALI[s] for s, v in segnali.items()
                               if v is None]
    if non_misurati:
        issues.append("Segnali non misurati, esclusi dal calcolo: %s"
                      % ", ".join(non_misurati))
    deboli = sorted((v, SEGNALI[s]) for s, v in segnali.items()
                    if v is not None and v < 60)
    for valore, etichetta in deboli[:2]:
        issues.append("Segnale debole: %s (%.0f/100)" % (etichetta, valore))

    return {
        "score": composito,
        "issues": issues,
        "market": nome_mercato,
        "profiles": profili,
        "signals": {SEGNALI[s]: v for s, v in segnali.items()},
        "disclaimer": DISCLAIMER,
    }
