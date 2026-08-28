#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import base64
import csv
import html
import json
import math
import io
import os
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import mars_history
import mars_remediation
from mars_config import (PESO_AREA, PESO_SEGNALE_DERIVATO,
                         SOGLIA_BUONO, SOGLIA_MEDIO)
from mars_i18n import (LINGUA_CANONICA, finding_texts, normalizza_lingua,
                       t)
from mars_core import (AREA_PREFIX, JSON_SCHEMA_VERSION, MODULES_REGISTRY,
                       RRF_FORMULA, RRF_K, SEV_CRITICAL, SEV_INFO, SEV_OK,
                       SEV_WARNING, SEVERITA, Finding, __version__,
                       describe_chunk, normalizza_risultato,
                       pagine_del_rilievo, reciprocal_rank_fusion)

FAVICON = "favicon.ico"


# ======================================================================
# Il dato: struttura canonica del referto
# ======================================================================

def _finding_errore(module_name: str, errore: object) -> dict:
    """Il fallimento di un'area, come rilievo strutturato.

    Un'area in errore non puo' restare senza `findings`: e' proprio
    quella che ha piu' bisogno di comparire negli elenchi che da qui in
    avanti si costruiranno sui rilievi — piano di interventi, conteggi
    per gravita', confronto fra due esecuzioni. Il modulo non puo'
    produrlo da se', perche' e' fallito: lo sintetizza il referto.

    La gravita' e' `info` e non `critical`: il difetto non e' del sito
    ma dello strumento, e gonfiare la gravita' del sito per un guasto
    nostro sarebbe una misura falsa a suo danno.
    """
    return Finding(
        area=module_name,
        severity=SEV_INFO,
        key="%s.status.error" % AREA_PREFIX.get(module_name, "area"),
        title="Area non calcolata: il modulo e' fallito",
        detail=str(errore),
    ).as_dict()


def build_report(results: dict, context: Optional[dict] = None) -> dict:
    """Referto come DATO, indipendente da come verra' mostrato.

    E' la struttura canonica: il JSON la serializza tal quale, testo e
    HTML ne sono viste. Prima la logica del referto viveva dentro le
    print, quindi esisteva un solo formato possibile e l'API dovevaripetere
    gli stessi calcoli per conto proprio.
    """
    context = context or {}
    chunks = context.get("chunks") or []
    # Il k EFFETTIVO, non la costante: da I3 e' una scelta di chi lancia
    # l'audit, e `rrf.k` esiste apposta per dire con quale ha girato.
    k_fusione = int(context.get("rrf_k", RRF_K))

    aree = []
    for nome, descrizione in MODULES_REGISTRY:
        if nome not in results:
            continue
        # Un plugin che non rispetta il contratto non deve far cadere
        # il referto DOPO che tutti i moduli sono girati: diventa
        # un'area fallita e dichiarata.
        res = normalizza_risultato(nome, results[nome])
        errore = res.get("error")
        aree.append({
            "module": nome,
            "label": descrizione,
            "score": res.get("score"),
            "status": "error" if errore else res.get("status"),
            # Il motivo del fallimento E' il rilievo dell'area: senza,
            # il referto direbbe solo "non misurato" senza dire perche'.
            "issues": ([str(errore)] if errore
                       else list(res.get("issues") or [])),
            # I rilievi come DATO (U1: dataclass Finding serializzata).
            # Convivono con "issues", che resta la vista compatta: su
            # di esse poggiano test, ordinamenti e l'API, e romperle
            # per un adeguamento di forma non varrebbe il prezzo.
            #
            # `or []` non e' difensivo per abitudine: normalizza_risultato
            # garantisce un dict, non le sue chiavi, e diversi test
            # scrivono risultati a mano senza questa chiave.
            "findings": ([_finding_errore(nome, errore)] if errore
                         else list(res.get("findings") or [])),
            # Con quale strumento e a quale livello: un punteggio di
            # accessibilita' senza il livello WCAG non significa nulla.
            "tool": res.get("tool"),
            # Il punteggio di un ALTRO strumento sulla stessa area,
            # quando esiste: due numeri diversi sulla stessa cosa si
            # spiegano, uno solo si subisce. Chiavi generiche e non
            # "lighthouse_*" perche' il confronto non e' una proprieta'
            # di quello strumento.
            "reference_score": res.get("reference_score"),
            "reference_tool": res.get("reference_tool"),
            # Tutti i punteggi di categoria di Lighthouse, dove
            # l'area li ha. Non si rendono nelle viste umane, ma
            # rendono TRACCIABILE il numero di riferimento qui sopra:
            # senza, il 97 dell'accessibilita' comparirebbe nel
            # referto senza che nulla dica da dove viene.
            "lighthouse_scores": res.get("lighthouse_scores"),
            "wcag_level": res.get("wcag_level"),
            "pages_tested": res.get("pages_tested"),
            # Elenco dei singoli controlli, quando lo strumento lo
            # fornisce: e' cio' che Lighthouse mostra nella sua
            # sezione, e senza non si sa QUALE controllo sia fallito.
            "audits": list(res.get("audits") or []) or None,
            "form_factor": res.get("form_factor"),
            # False quando lo strumento non e' arrivato in fondo (ZAP
            # interrotto dal timeout, axe che non ha caricato tutte le
            # pagine): un punteggio parziale non e' un punteggio pieno.
            "complete": res.get("complete"),
        })

    referto: Dict[str, object] = {
        "tool": "mars_audit.py",
        "version": __version__,
        # Lo schema del DATO, non del programma: chi consuma il JSON
        # legge questo. Sale solo su un cambiamento incompatibile.
        "schema_version": JSON_SCHEMA_VERSION,
        # I parametri che rendono il referto riproducibile. Il k della
        # fusione era il default di una funzione: due esecuzioni con k
        # diversi non sono confrontabili alla pari, e senza scriverlo
        # qui bisognerebbe aprire il codice di quella versione.
        "rrf": {"k": k_fusione, "formula": RRF_FORMULA},
        # `null` finche' le soglie non sono configurabili, e dichiararlo
        # e' il punto: due referti con soglie diverse non si confrontano
        # alla pari, quindi la chiave esiste da subito — quando le
        # soglie arriveranno, chi legge il JSON non dovra' distinguere
        # "assente perche' vecchio" da "assente perche' di serie".
        "thresholds": None,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "url": context.get("url"),
        "market": context.get("market"),
        "pages_crawled": len(context.get("pages") or {}),
        "discovery": context.get("discovery"),
        "chunks": len(chunks),
        "robots_ignored": bool(context.get("robots_ignored")),
        # Le query stanno anche qui, non solo dentro rrf_simulation:
        # se un retriever cade, quella lista e' vuota e
        # `mars_citations --from-audit` non trovava piu' nulla da
        # riusare, benche' load_queries sappia gia' leggere questa
        # chiave.
        "queries": list(context.get("queries") or []),
        "skipped": list(context.get("skipped") or []),
        # La superficie come dato: che cosa c'e' su ogni URL e quanto e'
        # profondo. Serve alle integrazioni, e nessuna delle nove aree
        # lo espone — ognuna guarda la propria misura.
        "pages": pagine_scansionate(context),
        "surface_math": surface_math(context),
        "areas": aree,
        # Chiave del contratto con mars_citations.py --from-audit:
        # lista di voci ciascuna con la propria "query".
        "rrf_simulation": rrf_simulation(results, chunks, k_fusione),
        "rrf_aggregate": rrf_aggregate(results, chunks, k_fusione),
        # Additivo, quindi `schema_version` non si muove: chi non lo
        # legge non se ne accorge.
        "rrf_sensitivity": rrf_sensitivity(results, chunks, k_fusione),
        "citability": results.get("mars_citability"),
        "llm_judgement": results.get("mars_llm_judge"),
        # Tutti i giudici, in cima e non sepolti dentro `llm_judgement`
        # (U10): un consumatore che vuole confrontare i modelli non deve
        # sapere che il primo di loro sta anche in cima. Additivo,
        # quindi `schema_version` non si muove — `llm_judgement` resta
        # dov'era e significa quello che significava.
        "llm_judgements": ((results.get("mars_llm_judge") or {})
                           .get("judgements") or []),
        "lexical": {"top_chunk":
                    (results.get("mars_lexical") or {}).get("top_chunk")},
        "semantic": {
            k: (results.get("mars_semantic") or {}).get(k)
            for k in ("answer_shaped_ratio", "n_chunks",
                      "answer_shaped_signals", "page_signals", "languages")
        },
    }
    # Il complessivo prima del piano: nessuno dei due dipende
    # dall'altro, ma entrambi rileggono le aree gia' composte.
    referto["overall"] = overall_score(referto)
    # Il piano si costruisce per ULTIMO, e da questa stessa struttura:
    # rilegge le aree e la citabilita' gia' composte, quindi non puo'
    # stare dentro il letterale che le definisce.
    #
    # L'import di `mars_remediation` e' DURO, a differenza di quello di
    # `mars_fixes` in `normalizza_risultato`: quello e' un catalogo di
    # prosa, e la sua assenza degrada un referto che resta vero;
    # questo e' dato canonico, e la sua assenza deve rompere invece di
    # produrre un referto silenziosamente senza piano.
    referto["remediation"] = mars_remediation.build_remediation(referto)
    # Il confronto con l'esecuzione precedente, se il chiamante ne ha
    # trovata una. `None` alla prima, e le viste tacciono: una sezione
    # «rispetto a prima» con tutto a zero direbbe che non e' cambiato
    # nulla, invece che «non c'e' un prima».
    referto["delta"] = mars_history.compute_delta(
        context.get("previous"), mars_history.riga_storico(referto))
    return referto


# D3: chi entra nel punteggio complessivo, e con quale peso.
#
# Le aree escluse lo sono per NOME e non per una proprieta' del dato,
# ed e' deliberato. `mars_citability` e' una sintesi dei punteggi
# altrui: contarla sarebbe contare due volte le stesse misure.
# `mars_llm_judge` e' opzionale e a pagamento, quindi lo stesso sito
# darebbe due complessivi diversi a seconda che si sia speso o no.
# Escluderle per nome le tiene fuori anche quando FALLISCONO, che e'
# proprio il caso in cui una regola basata sul dato le lascerebbe
# rientrare.
#
# `mars_lexical` e `mars_semantic` sono entrate in questo elenco con
# U13, che ha dato loro un punteggio: e' la stessa ragione della
# citabilita', misurata invece che assunta. Quelle due aree ci entrano
# gia' dai SEGNALI DERIVATI, a peso 1.5 ciascuno; contarle anche come
# aree porterebbe il totale da 8.0 a 10.0 con 5.0 che vengono da loro,
# cioe' meta' del complessivo a due aree su nove. La strada opposta —
# togliere i segnali e tenere le aree — costa di piu': il consenso RRF
# e' la domanda del progetto e nessun controllo di U13 lo misura,
# quindi sparirebbe dal complessivo per non tornare.
AREE_FUORI_DAL_COMPLESSIVO = ("mars_citability", "mars_llm_judge",
                              "mars_lexical", "mars_semantic")


def segnali_derivati(referto: dict, lang: str = LINGUA_CANONICA
                     ) -> List[Dict[str, object]]:
    """I due segnali che non vengono da un'area ma dal confronto fra due.

    `mars_lexical` e `mars_semantic` un punteggio da U13 ce l'hanno, ma
    resta fuori dalla media (`AREE_FUORI_DAL_COMPLESSIVO`): al loro
    posto valgono il consenso RRF aggregato e la quota di contenuto in
    forma di risposta, che sono MISURE dei due recuperatori invece che
    somme di penalita' editoriali.

    Scritta una volta sola perche' la leggono in due — la fascia dei
    quadranti e il punteggio complessivo — e due implementazioni dello
    stesso numero divergerebbero senza che nulla si rompa. E' lo stesso
    argomento del `tokenize()` condiviso fra corpus e query (R18).

    `lang` governa la sola `note`, che e' prosa e non esce nel JSON —
    `overall_score` prende `name`, `value` e `weight` e la ignora. La
    nota si compone QUI e non si traduce a valle, perche' «consenso
    2/3» e' gia' una frase montata: cercarla in un catalogo vorrebbe
    dire una voce per ogni coppia di numeri possibile.
    """
    esito: List[Dict[str, object]] = []
    aggregato = referto.get("rrf_aggregate")
    if aggregato and aggregato.get("consensus_out_of"):
        esito.append({
            "name": "Recuperabilità",
            "value": (100.0 * aggregato["consensus_top3"]
                      / aggregato["consensus_out_of"]),
            "note": t("consenso %d/%d", lang)
                    % (aggregato["consensus_top3"],
                       aggregato["consensus_out_of"]),
        })
    sem = referto.get("semantic") or {}
    if sem.get("n_chunks"):
        esito.append({
            "name": "In forma di risposta",
            "value": 100.0 * (sem.get("answer_shaped_ratio") or 0),
            "note": t("su %d chunk", lang) % sem["n_chunks"],
        })
    return esito


def overall_score(referto: dict) -> Optional[Dict[str, object]]:
    """Il punteggio complessivo, con gli ingredienti accanto.

    Media pesata delle sole aree MISURATE, rinormalizzata su quelle
    presenti: un'area senza strumento non abbassa il complessivo, lo
    rende meno informato — la stessa regola che `mars_citability`
    applica ai suoi segnali.

    Restituisce anche `components` ed `excluded`, e non e' ornamento:
    un numero che riassume nove aree in uno vale quanto la possibilita'
    di rifarne il conto. Senza, «68» sarebbe l'unica cifra del referto
    che nessuno puo' verificare.

    None quando non c'e' nulla da mediare: e' un "non misurato", non
    uno zero.
    """
    componenti: List[Dict[str, object]] = []
    escluse: List[str] = []
    for area in referto.get("areas") or []:
        nome = area.get("module") or ""
        if nome in AREE_FUORI_DAL_COMPLESSIVO:
            escluse.append(nome)
            continue
        if not isinstance(area.get("score"), (int, float)):
            continue
        componenti.append({"name": area.get("label") or nome,
                           "value": float(area["score"]),
                           "weight": PESO_AREA})
    for segnale in segnali_derivati(referto):
        componenti.append({"name": segnale["name"],
                           "value": float(segnale["value"]),
                           "weight": PESO_SEGNALE_DERIVATO})
    if not componenti:
        return None
    totale = sum(c["weight"] for c in componenti)
    somma = sum(c["value"] * c["weight"] for c in componenti)
    return {"score": round(somma / totale, 1),
            "components": componenti,
            "excluded": escluse,
            "weight_total": totale}


# I secchielli della profondità di crawl. Tre e non uno per livello:
# oltre il terzo click la differenza fra quattro e sette non cambia
# quel che si fa, e un istogramma con dodici colonne da una pagina
# ciascuna non si legge.
SECCHIELLI_PROFONDITA = (
    (0, 0, "home"),
    (1, 1, "1 click"),
    (2, 2, "2 click"),
    (3, 3, "3 click"),
    (4, None, "4+ click"),
)


def _tipi_json_ld(blocchi: List[str]) -> List[str]:
    """I tipi Schema.org dichiarati da una pagina.

    Legge il `@type`, che nel JSON-LD puo' essere una stringa o una
    lista, e puo' stare dentro un `@graph`. Un blocco che non si
    analizza non da' niente e **non e' un giudizio**: che sia malformato
    lo dice gia' `mars_schema` con un rilievo suo, e ripeterlo qui
    sarebbe la seconda voce sullo stesso difetto.
    """
    tipi: List[str] = []

    def raccogli(nodo: object) -> None:
        if isinstance(nodo, list):
            for voce in nodo:
                raccogli(voce)
            return
        if not isinstance(nodo, dict):
            return
        valore = nodo.get("@type")
        if isinstance(valore, str):
            tipi.append(valore)
        elif isinstance(valore, list):
            tipi.extend(v for v in valore if isinstance(v, str))
        raccogli(nodo.get("@graph"))

    for blocco in blocchi or []:
        try:
            raccogli(json.loads(blocco or ""))
        except ValueError:
            continue
    # Ordinati e senza doppioni: il referto e' un dato che si
    # confronta fra due esecuzioni, e l'ordine di apparizione nel DOM
    # non e' un'informazione.
    return sorted(set(tipi))


def pagine_scansionate(context: dict) -> List[Dict[str, object]]:
    """Le pagine come dato, senza il loro contenuto.

    `context["pages"]` porta anche `html` e `text` — centinaia di
    kilobyte per pagina — che nel referto non hanno posto: qui esce il
    sottoinsieme che serve a un'integrazione, cioe' che cosa c'e' su
    ogni URL e quanto e' profondo.

    **Lo status HTTP non c'e', e non si inventa**: nel dict pagina non
    esiste, perche' solo le 200 entrano in `pages` e tutto il resto
    finisce in `skipped`. Metterci un 200 fisso vorrebbe dire scrivere
    una misura che nessuno ha fatto.
    """
    scansionate = set(context.get("pages") or {})
    esito = []
    for url, pagina in (context.get("pages") or {}).items():
        uscenti = list(pagina.get("link_targets") or [])
        esito.append({
            "url": url,
            "title": pagina.get("title") or "",
            "lang": pagina.get("lang") or "",
            # None quando la pagina viene dalla sitemap: dichiarata dal
            # sito, ma nessuno l'ha raggiunta seguendo i link.
            "depth": pagina.get("depth"),
            "headings": len(pagina.get("headings") or []),
            "chunks": len(pagina.get("chunks") or []),
            # Le parole si contano sui CHUNK, non sul testo di pagina:
            # sono quelle che i due recuperatori possono pescare, ed e'
            # lo stesso conto che fa `surface_math` sull'intero sito.
            # Contarle sul testo darebbe due numeri sulla stessa cosa
            # che non tornano — la somma delle pagine diversa dal
            # totale — e chi legge non saprebbe quale credere.
            "words": sum(len((c.get("text") or "").split())
                         for c in (pagina.get("chunks") or [])),
            # Due numeri diversi, e non e' una ridondanza: `links_to`
            # sono gli archi che si possono DISEGNARE, cioe' quelli
            # verso pagine che l'audit ha guardato; `links_internal` e'
            # quanti link interni la pagina ha davvero. Il secondo dice
            # quanto del sito resta fuori dal campione, e senza di lui
            # un grafo con tre archi sembrerebbe un sito con tre link.
            "links_to": sorted(u for u in uscenti if u in scansionate),
            "links_internal": len(uscenti),
            "json_ld_types": _tipi_json_ld(pagina.get("json_ld") or []),
        })
    return esito


def depth_distribution(pagine: List[dict]) -> List[Dict[str, object]]:
    """Quante pagine a ciascuna distanza dalla home.

    Il secchiello «profondita' ignota» non e' un residuo: raccoglie le
    pagine che il crawler ha preso dalla sitemap senza mai raggiungerle
    per link, e sono la scoperta piu' utile della sezione — un
    contenuto che sta nella sitemap e in nessun percorso di
    navigazione e' un contenuto che un assistente trova solo se sa gia'
    che esiste.
    """
    profondita = [p.get("depth") for p in pagine]
    esito: List[Dict[str, object]] = []
    for minimo, massimo, etichetta in SECCHIELLI_PROFONDITA:
        quante = sum(1 for d in profondita
                     if isinstance(d, int)
                     and d >= minimo and (massimo is None or d <= massimo))
        if quante:
            esito.append({"label": etichetta, "pages": quante,
                          "unknown": False})
    ignote = sum(1 for d in profondita if not isinstance(d, int))
    if ignote:
        esito.append({"label": "profondità ignota", "pages": ignote,
                      "unknown": True})
    return esito


# L'obiettivo contro cui si misura la superficie attuale. E' una
# ASSUNZIONE, non una misura, e viaggia dentro il dato perche' ogni
# vista la ripeta: una pagina di contenuto sostanziale sta intorno alle
# 900 parole e il chunker ne ricava quattro passaggi. Chi non e'
# d'accordo col numero deve poterlo vedere invece di dedurlo dal
# risultato.
PAROLE_PER_PAGINA_OBIETTIVO = 900
CHUNK_PER_PAGINA_OBIETTIVO = 4
ASSUNZIONE_SUPERFICIE = (
    "proiezione, non misura: si assume una pagina di contenuto "
    "sostanziale intorno alle %d parole, da cui il chunker ricava circa "
    "%d passaggi" % (PAROLE_PER_PAGINA_OBIETTIVO,
                     CHUNK_PER_PAGINA_OBIETTIVO))


def surface_math(context: dict) -> Optional[Dict[str, object]]:
    """Quanta superficie recuperabile c'e', e quanta ce ne potrebbe essere.

    Ogni chunk e' un'occasione di essere recuperato: due recuperatori
    che pescano fra dodici passaggi e due che pescano fra quaranta non
    fanno lo stesso lavoro. Questa sezione dice di quanto si
    moltiplicherebbero le occasioni se le pagine avessero il contenuto
    che si dara' per obiettivo.

    E' una **proiezione dichiarata**, non una misura, e l'assunzione
    viaggia dentro il dato: e' la differenza fra dire «potresti avere
    40 passaggi» e dire «se ogni pagina arrivasse a 900 parole».

    None senza pagine: non c'e' superficie di cui parlare.
    """
    pagine = context.get("pages") or {}
    chunks = context.get("chunks") or []
    if not pagine:
        return None
    parole = sum(len((c.get("text") or "").split()) for c in chunks)
    potenziali = len(pagine) * CHUNK_PER_PAGINA_OBIETTIVO
    return {
        "pages": len(pagine),
        "chunks": len(chunks),
        "words": parole,
        "words_per_page": round(parole / len(pagine), 1),
        "chunks_per_page": round(len(chunks) / len(pagine), 2),
        "target_words_per_page": PAROLE_PER_PAGINA_OBIETTIVO,
        "target_chunks_per_page": CHUNK_PER_PAGINA_OBIETTIVO,
        "potential_chunks": potenziali,
        # None e non 1.0 quando non c'e' nulla da moltiplicare: dire
        # «x1» su zero chunk suonerebbe come «sei gia' a posto».
        "multiplier": (round(potenziali / len(chunks), 1)
                       if chunks else None),
        "assumption": ASSUNZIONE_SUPERFICIE,
    }


# La treemap: quanto e' grande ciascuna pagina, viste tutte insieme.
# 760x420 e' lo spazio di disegno, non un dato del sito: la geometria
# NON entra nel referto canonico, e non e' una svista — un consumatore
# del JSON ha `pages[]` con le parole, che e' l'ingrediente, mentre
# delle coordinate calcolate per una larghezza che lui non usa non
# saprebbe che farsene. Il tetto esiste perche' quaranta rettangoli
# sono gia' piu' di quanti se ne distinguano a occhio, ed e' DICHIARATO
# dai conteggi che escono accanto alle voci.
TREEMAP_W = 760.0
TREEMAP_H = 420.0
TREEMAP_MAX = 40


def _coda(testo: str, quanti: int) -> str:
    """Il testo, o la sua CODA quando non ci sta.

    Si taglia dalla testa e non dalla fine perche' e' la testa che le
    pagine hanno in comune: su un sito vero i percorsi condividono le
    sezioni — `/servizi/consulenza/x` e `/servizi/formazione/y` — e
    troncare a destra darebbe dieci etichette identiche. Misurato su un
    sito sintetico di cinquanta pagine: `/sezione-molto-l` per tutte e
    quaranta i rettangoli.
    """
    if quanti <= 1:
        return ""
    if len(testo) <= quanti:
        return testo
    return "…" + testo[-(quanti - 1):]


def _squarify(valori: List[float], x: float, y: float, w: float,
              h: float) -> List[Dict[str, float]]:
    """Layout squarified deterministico: rettangoli (x, y, w, h).

    Algoritmo di Bruls-Huizing-van Wijk. Si riempie lo spazio a righe
    lungo il lato **corto** di cio' che resta, allungando la riga
    finche' il rapporto d'aspetto peggiore migliora: fermarsi quando
    peggiora e' tutto il metodo, ed e' cio' che distingue una treemap
    leggibile da una fila di schegge.

    L'ordine d'ingresso si conserva, e i rettangoli riempiono
    esattamente l'area data: la somma delle aree e' `w * h`, quindi
    l'area di ciascuno e' davvero proporzionale al suo valore.

    Deterministico, e deve restarlo: i golden congelano l'SVG.
    """
    totale = sum(valori)
    if not valori or totale <= 0 or w <= 0 or h <= 0:
        return []
    scala = w * h / totale
    aree = [v * scala for v in valori]
    rettangoli: List[Dict[str, float]] = []
    i = 0
    while i < len(aree):
        # Spazio piu' alto che largo: la riga corre in orizzontale.
        lungo_x = w <= h
        lato = w if lungo_x else h

        def peggiore(riga: List[float]) -> float:
            somma = sum(riga)
            if somma <= 0:
                return float("inf")
            spessore2 = (somma / lato) ** 2
            return max(spessore2 / min(riga), max(riga) / spessore2)

        riga = [aree[i]]
        j = i + 1
        while j < len(aree) and peggiore(riga + [aree[j]]) <= peggiore(riga):
            riga.append(aree[j])
            j += 1
        spessore = sum(riga) / lato
        scorrimento = 0.0
        for area in riga:
            estensione = area / spessore
            if lungo_x:
                rettangoli.append({"x": x + scorrimento, "y": y,
                                   "w": estensione, "h": spessore})
            else:
                rettangoli.append({"x": x, "y": y + scorrimento,
                                   "w": spessore, "h": estensione})
            scorrimento += estensione
        if lungo_x:
            y += spessore
            h -= spessore
        else:
            x += spessore
            w -= spessore
        i = j
    return rettangoli


def disposizione_ad_anelli(livelli: List[Optional[int]],
                           larghezza: float,
                           altezza: float) -> List[Tuple[float, float]]:
    """Un anello per distanza dalla home, con gli orfani fuori da tutti.

    Era ventisei righe di JavaScript, e nessun test le eseguiva: quattro
    ne guardavano la *stringa*. E' aritmetica pura, quindi qui e'
    verificabile con la suite di sempre, senza allargare l'ambiente a
    node e jsdom (R48). Al JavaScript resta il gesto — eventi, classi,
    zoom — che il banco `tools/banco_grafo.py` continua a presidiare.

    `None` e' una pagina che dalla home non si raggiunge seguendo i
    link: va **fuori** da tutti gli anelli, non «prima» della home.
    Non sta a una distanza minore: sta fuori dal percorso.
    """
    if not livelli:
        return []
    cx, cy = larghezza / 2.0, altezza / 2.0
    massimo = max((liv for liv in livelli if liv is not None), default=0)
    # Gli orfani prendono la corsia subito oltre l'ultimo livello vero.
    quote = [massimo + 1 if liv is None else liv for liv in livelli]

    gruppi: Dict[int, List[int]] = {}
    for i, quota in enumerate(quote):
        gruppi.setdefault(quota, []).append(i)

    esterno = min(cx, cy) - 24.0
    punti: List[Tuple[float, float]] = [(cx, cy)] * len(livelli)
    for quota, gruppo in gruppi.items():
        # Un grafo di soli orfani, o di sola home, non ha livelli veri:
        # senza questo ramo il raggio sarebbe una divisione per uno e
        # gli orfani finirebbero al centro insieme alla home.
        if massimo <= 0:
            raggio = esterno if quota > 0 else 0.0
        else:
            raggio = esterno * quota / (massimo + 1.0)
        for k, i in enumerate(gruppo):
            if not raggio:
                punti[i] = (cx, cy)
                continue
            angolo = 2.0 * math.pi * k / len(gruppo) - math.pi / 2.0
            punti[i] = (cx + raggio * math.cos(angolo),
                        cy + raggio * math.sin(angolo))
    return punti


def geometria_arco(partenza: Tuple[float, float],
                   arrivo: Tuple[float, float],
                   raggio: float) -> Tuple[float, float, float, float]:
    """Le due estremita' di un arco, dato dove stanno i due nodi.

    L'arco si ferma sul **bordo** del nodo d'arrivo e non al centro,
    altrimenti la freccia finisce nascosta sotto il cerchio.

    Sta in una funzione perche' la chiamano due volte per arco — una
    per il layout a forze, una per quello ad anelli — e prima la stessa
    aritmetica viveva in due linguaggi: qui e dentro `ridisegna()` del
    JavaScript, dove nessun test la eseguiva (R48).
    """
    dx = arrivo[0] - partenza[0]
    dy = arrivo[1] - partenza[1]
    lunghezza = (dx * dx + dy * dy) ** 0.5 or 1.0
    arretra = (raggio + 3.0) / lunghezza
    return (partenza[0], partenza[1],
            arrivo[0] - dx * arretra, arrivo[1] - dy * arretra)


def vicinato(archi: List[Dict[str, object]], quanti: int
             ) -> Tuple[List[List[int]], List[List[int]]]:
    """Per ogni nodo: i suoi vicini, e gli archi che lo toccano.

    `evidenzia()` scandiva tutti gli archi a ogni passaggio del
    puntatore per ricavarli. La risposta non dipende dal gesto — e' una
    proprieta' del grafo — quindi si calcola una volta qui e il
    JavaScript la legge (R48).

    Un nodo e' vicino di se stesso: e' il modo in cui l'evidenziazione
    lo tiene acceso senza un caso speciale.
    """
    vicini: List[List[int]] = [[i] for i in range(quanti)]
    incidenti: List[List[int]] = [[] for _ in range(quanti)]
    for k, arco in enumerate(archi):
        s, t = int(arco["source"]), int(arco["target"])
        for uno, altro in ((s, t), (t, s)):
            if altro not in vicini[uno]:
                vicini[uno].append(altro)
            if k not in incidenti[uno]:
                incidenti[uno].append(k)
    return ([sorted(v) for v in vicini], incidenti)


def ripartizione_pagine(referto: dict) -> Dict[str, int]:
    """I tre numeri del donut dell'hero: quanti URL, e in che stato.

    Il totale e' cio' che il crawler ha **incontrato**, non le sole
    pagine: gli URL scartati fanno parte del giro e sparirebbero da
    una ripartizione delle sole pagine.

    I nomi dei settori portano il caveat dentro il disegno, e non in una
    nota accanto:

    - **`non_citate` non significa «pulite».** Nessuna area registra
      QUALI pagine ha guardato — Lighthouse ne misura una, axe le prime
      del campione — quindi un settore chiamato «senza rilievi»
      affermerebbe cio' che nessuno ha misurato, per giunta su un
      disegno che si legge come esaustivo. E' la stessa ragione per cui
      la treemap non colora di verde (R21, R47);
    - **`scartati` non sono pagine.** `skipped` contiene MOTIVI, e fra
      quelli ci sono un altro host e un URL non analizzabile: chiamarli
      «pagine scartate» direbbe che sono pagine del sito.

    Non entra nel dato canonico: e' derivabile per intero da `pages`,
    `skipped` e `areas[].findings[].params["urls"]`, e scriverlo accanto
    sarebbe una seconda copia che diverge da sola — come la geometria
    della treemap.
    """
    scansionate = {str(p.get("url") or "") for p in (referto.get("pages") or [])}
    # L'intersezione, non il conteggio dei citati: un rilievo puo'
    # nominare un URL che non e' fra le pagine — gli strumenti esterni
    # seguono i propri redirect — e contarlo qui gonfierebbe un settore
    # oltre il totale.
    con_rilievi = len(set(gravita_per_pagina(referto)) & scansionate)
    return {"con_rilievi": con_rilievi,
            "non_citate": len(scansionate) - con_rilievi,
            "scartati": len(referto.get("skipped") or [])}


def gravita_per_pagina(referto: dict) -> Dict[str, Dict[str, object]]:
    """Per ogni pagina citata da un rilievo, la gravita' PEGGIORE e quanti.

    Si legge dai rilievi e non si conserva nel referto canonico: e'
    interamente derivabile da `areas[].findings[].params["urls"]`, e
    scriverla accanto sarebbe una seconda copia che diverge da sola —
    la stessa ragione per cui la geometria della treemap non entra nel
    dato.

    **Una pagina assente dalla mappa non e' una pagina pulita.** Puo'
    essere una pagina che nessun modulo ha guardato: Lighthouse ne
    misura una sola, axe le prime del campione. Chi legge questa mappa
    deve distinguere «nessun rilievo la cita» da «nessun problema», ed
    e' il motivo per cui la treemap in quel caso non colora invece di
    colorare di verde (R21, R47).
    """
    peggiore: Dict[str, Dict[str, object]] = {}
    for area in referto.get("areas") or []:
        for rilievo in area.get("findings") or []:
            gravita = str(rilievo.get("severity") or "")
            if gravita not in SEVERITA:
                continue
            for url in pagine_del_rilievo(rilievo):
                voce = peggiore.setdefault(url, {"severity": gravita,
                                                 "findings": 0})
                voce["findings"] = int(voce["findings"]) + 1
                if (SEVERITA.index(gravita)
                        < SEVERITA.index(str(voce["severity"]))):
                    voce["severity"] = gravita
    return peggiore


def treemap_data(pagine: List[dict], width: float = TREEMAP_W,
                 height: float = TREEMAP_H,
                 max_items: int = TREEMAP_MAX,
                 gravita: Optional[Dict[str, Dict[str, object]]] = None
                 ) -> Optional[Dict[str, object]]:
    """La superficie pagina per pagina, come rettangoli.

    Ogni rettangolo e' una pagina, l'area e' proporzionale alle parole
    recuperabili. La distribuzione di profondita' dice DOVE sta il
    contenuto, questa dice quanto ce n'e' su ciascuna pagina — e la
    forma che si legge a colpo d'occhio e' quella di un sito che ha
    tutto il testo in una pagina sola.

    **Il colore e' la gravita' peggiore dei rilievi che citano la
    pagina**, da `gravita_per_pagina`. Era il passo 3 della Fase 8 di
    UPGRADE.md, ed e' rimasto in sospeso fino a R47 perche' nessun
    rilievo dichiarava una pagina: applicata allora, quella regola non
    avrebbe trovato una corrispondenza e avrebbe dipinto **tutte** le
    pagine di "nessun problema" — un via libera che nessuno ha
    misurato.

    Le pagine che **nessun rilievo cita** restano senza colore, e non
    diventano verdi: potrebbero essere pulite come potrebbero non
    essere state guardate — Lighthouse ne misura una sola, axe le
    prime del campione. La distinzione e' la stessa di `score: None`
    contro `score: 0`, e la vista la scrive a parole accanto al
    disegno, perche' il colore da solo non la porta.

    None sotto le due pagine con testo: un rettangolo solo non e' una
    distribuzione, e' un quadrato che riempie lo spazio qualunque sia
    il sito.
    """
    con_testo = [p for p in pagine if int(p.get("words") or 0) > 0]
    if len(con_testo) < 2:
        return None
    # Decrescente e, a parita' di parole, per URL: due esecuzioni sullo
    # stesso sito devono dare lo stesso disegno.
    ordinate = sorted(con_testo,
                      key=lambda p: (-int(p.get("words") or 0),
                                     str(p.get("url") or "")))
    mostrate = ordinate[:max_items]
    rettangoli = _squarify([float(p["words"]) for p in mostrate],
                           0.0, 0.0, width, height)
    gravita = gravita or {}
    voci: List[Dict[str, object]] = []
    for pagina, rettangolo in zip(mostrate, rettangoli):
        url = str(pagina.get("url") or "")
        percorso = urlsplit(url).path or "/"
        citata = gravita.get(url) or {}
        voci.append({
            "url": pagina.get("url"),
            "label": _coda(percorso, 30),
            "words": int(pagina.get("words") or 0),
            "chunks": int(pagina.get("chunks") or 0),
            # Vuoto quando nessun rilievo la cita: e' un'assenza di
            # informazione, non un "ok", e le due non vanno confuse.
            "severity": str(citata.get("severity") or ""),
            "findings": int(citata.get("findings") or 0),
            "x": round(rettangolo["x"], 1), "y": round(rettangolo["y"], 1),
            "w": round(rettangolo["w"], 1), "h": round(rettangolo["h"], 1),
        })
    return {
        "width": width, "height": height,
        "total": len(pagine),
        "shown": len(voci),
        # Le pagine senza una parola indicizzabile non hanno superficie
        # da disegnare, ma sono proprio quelle che interessano di piu':
        # sparire in silenzio le farebbe sembrare inesistenti invece
        # che vuote, quindi il conteggio esce e la vista lo dice.
        "empty": len(pagine) - len(con_testo),
        "items": voci,
    }


# Il grafo dei link: spazio di disegno e tetto ai nodi. Come per la
# treemap, la geometria non entra nel referto canonico. Sessanta nodi
# sono gia' oltre quanti se ne seguano a occhio, e il tetto e'
# dichiarato accanto al disegno.
GRAFO_W = 780.0
GRAFO_H = 540.0
GRAFO_MAX = 60
GRAFO_ITERAZIONI = 150


def _force_layout(quanti: int, archi: List[Tuple[int, int]],
                  width: float = GRAFO_W, height: float = GRAFO_H,
                  iterazioni: int = GRAFO_ITERAZIONI
                  ) -> List[Tuple[float, float]]:
    """Layout a forze deterministico (Fruchterman-Reingold, 1991).

    Repulsione `k^2/d` fra tutte le coppie, attrazione `d^2/k` lungo
    gli archi, raffreddamento geometrico. Il nodo 0 — la home — resta
    ancorato al centro, cosi' il disegno ha sempre lo stesso fuoco.

    **Nessuna casualita'**: l'inizializzazione e' su un cerchio invece
    che a caso, quindi lo stesso sito da' lo stesso disegno. E' cio'
    che permette di congelarlo in un golden e di confrontare due
    esecuzioni; un layout seminato a caso sarebbe piu' vario e
    inverificabile.

    Scritto a mano come gli altri algoritmi del progetto: e' una
    ventina di righe, e networkx trascinerebbe numpy per questo solo
    uso.
    """
    if quanti <= 0:
        return []
    cx, cy = width / 2.0, height / 2.0
    if quanti == 1:
        return [(round(cx, 1), round(cy, 1))]
    raggio = min(width, height) / 3.0
    pos = [[cx + raggio * math.cos(2 * math.pi * i / quanti),
            cy + raggio * math.sin(2 * math.pi * i / quanti)]
           for i in range(quanti)]
    pos[0] = [cx, cy]
    k = (width * height / quanti) ** 0.5
    temperatura = width / 8.0
    for _ in range(iterazioni):
        spostamento = [[0.0, 0.0] for _ in range(quanti)]
        for i in range(quanti):
            for j in range(i + 1, quanti):
                dx = pos[i][0] - pos[j][0]
                dy = pos[i][1] - pos[j][1]
                dist = max(0.01, (dx * dx + dy * dy) ** 0.5)
                forza = k * k / dist
                spostamento[i][0] += dx / dist * forza
                spostamento[i][1] += dy / dist * forza
                spostamento[j][0] -= dx / dist * forza
                spostamento[j][1] -= dy / dist * forza
        for a, b in archi:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            dist = max(0.01, (dx * dx + dy * dy) ** 0.5)
            forza = dist * dist / k
            spostamento[a][0] -= dx / dist * forza
            spostamento[a][1] -= dy / dist * forza
            spostamento[b][0] += dx / dist * forza
            spostamento[b][1] += dy / dist * forza
        # Dal nodo 1: la home resta dove sta.
        for i in range(1, quanti):
            dx, dy = spostamento[i]
            dist = max(0.01, (dx * dx + dy * dy) ** 0.5)
            passo = min(dist, temperatura)
            pos[i][0] = min(width - 20.0,
                            max(20.0, pos[i][0] + dx / dist * passo))
            pos[i][1] = min(height - 16.0,
                            max(16.0, pos[i][1] + dy / dist * passo))
        temperatura *= 0.95
    return [(round(x, 1), round(y, 1)) for x, y in pos]


def _distanze_in_click(archi: Dict[str, List[str]],
                       home: str) -> Dict[str, int]:
    """Quanti click dalla home, seguendo i soli link osservati.

    **Non e' `pages[].depth`**, ed e' importante che i due non si
    confondano: quello dice come il crawler ci e' arrivato ed e'
    ignoto per le pagine che vengono dalla sitemap; questo e' il
    cammino piu' breve dentro il CAMPIONE di pagine scaricate.
    Un sito con sitemap ha `depth` ignota ovunque e distanze qui
    misurabili, e le due cose restano vere insieme.

    Chi non compare nel risultato non e' raggiungibile dalla home
    seguendo i link visti: e' l'informazione piu' utile del grafo.
    """
    if home not in archi:
        return {}
    distanza = {home: 0}
    coda = [home]
    while coda:
        nodo = coda.pop(0)
        for arrivo in archi.get(nodo, ()):
            if arrivo not in distanza:
                distanza[arrivo] = distanza[nodo] + 1
                coda.append(arrivo)
    return distanza


def link_graph_data(pagine: List[dict], base: str,
                    max_nodes: int = GRAFO_MAX
                    ) -> Optional[Dict[str, object]]:
    """L'architettura del sito: chi linka chi, fra le pagine viste.

    La treemap dice quanto contenuto c'e' su ogni pagina, questa dice
    come ci si arriva. Il nodo e' grande quanto i link che riceve, e
    quelli che dalla home non si raggiungono per link sono **orfani**:
    un assistente che segue i collegamenti non li incontra mai.

    Gli archi sono solo quelli fra pagine **scansionate**: un link
    verso una pagina fuori dal campione non e' un arco che si possa
    disegnare, e inventarne il capo dall'altra parte direbbe che quella
    pagina e' stata guardata. Quanti link restino fuori lo dice
    `links_internal` di ciascuna pagina, che il referto porta.

    None senza archi: un grafo di punti senza linee non e'
    un'architettura, e disegnarlo suggerirebbe che il sito non ha link
    invece che «non ne abbiamo visti fra queste pagine».
    """
    if len(pagine) < 2:
        return None
    archi_per_url = {str(p.get("url") or ""): list(p.get("links_to") or [])
                     for p in pagine}
    entranti: Dict[str, int] = {u: 0 for u in archi_per_url}
    for uscenti in archi_per_url.values():
        for arrivo in uscenti:
            if arrivo in entranti:
                entranti[arrivo] += 1
    home = base if base in archi_per_url else ""
    # Home per prima, poi i piu' linkati: se il tetto taglia, taglia
    # le pagine che il sito stesso richiama di meno.
    urls = sorted(archi_per_url,
                  key=lambda u: (u != home, -entranti[u], u))[:max_nodes]
    indice = {u: i for i, u in enumerate(urls)}
    collegamenti = sorted(
        {(indice[u], indice[a]) for u in urls
         for a in archi_per_url[u] if a in indice})
    if not collegamenti:
        return None
    distanze = _distanze_in_click(
        {u: archi_per_url[u] for u in urls}, home)
    posizioni = _force_layout(len(urls), collegamenti)
    uscenti_per_indice = [0] * len(urls)
    for partenza, _arrivo in collegamenti:
        uscenti_per_indice[partenza] += 1
    nodi = []
    for i, url in enumerate(urls):
        nodi.append({
            "url": url,
            "label": _coda(urlsplit(url).path or "/", 30),
            "incoming": entranti[url],
            "outgoing": uscenti_per_indice[i],
            # None = non raggiungibile dalla home seguendo i link.
            "clicks": distanze.get(url),
            "home": url == home,
            "x": posizioni[i][0], "y": posizioni[i][1],
            # Il raggio cresce con la RADICE dei link entranti: una
            # pagina linkata cento volte non puo' essere dieci volte
            # piu' larga di una linkata dieci, o coprirebbe il resto.
            "r": round(min(15.0, 5.0 + 1.8 * entranti[url] ** 0.5), 1),
        })
    return {
        "width": GRAFO_W, "height": GRAFO_H,
        "total": len(pagine),
        "shown": len(nodi),
        "edges": len(collegamenti),
        # Le pagine che dalla home non si raggiungono per link.
        # `None` — non zero — senza un punto di partenza nel campione:
        # li' ogni pagina risulterebbe irraggiungibile, ma il numero
        # direbbe qualcosa sul sito quando invece dice solo che non
        # sappiamo da dove si parte. La home, quando c'e', ha sempre
        # distanza 0 perche' e' la radice del BFS: escluderla di nuovo
        # qui sarebbe un ramo che non puo' scattare.
        "orphans": (sum(1 for n in nodi if n["clicks"] is None)
                    if home else None),
        # `False` quando l'URL di partenza non e' fra le pagine
        # scansionate: senza un punto di partenza «raggiungibile» non
        # significa nulla, e il referto deve dirlo invece di mostrare
        # tutte le pagine come orfane.
        "has_home": bool(home),
        # `True` quando NESSUN link interno esce dal campione: allora
        # «orfana» e' una misura chiusa. Quando invece il campione e'
        # parziale — dieci pagine di un sito da cinquecento — una
        # pagina puo' risultare orfana solo perche' chi la linka non e'
        # stato scaricato, e il referto deve dirlo prima che qualcuno
        # ci lavori sopra.
        "closed": all(int(p.get("links_internal") or 0)
                      == len(p.get("links_to") or []) for p in pagine),
        "nodes": nodi,
        "links": [{"source": a, "target": b} for a, b in collegamenti],
    }


def _divergenti(propri: List[int], altrui: List[int],
                chunks: List[dict]) -> List[Dict[str, object]]:
    """I primi tre di `propri` che non stanno nei primi tre di `altrui`.

    **Nell'ordine di `propri`**, non dell'indice del chunk: un `set` di
    interi si itera per valore, quindi ordinare per indice sarebbe
    deterministico e privo di significato. Chi legge vuole sapere qual
    e' il PRIMO dei passaggi che solo quel recuperatore ha trovato.

    Gli indici arrivano dai moduli, che sono plugin: uno oltre il
    corpus e' dato ostile e si scarta, come gia' fa il passaggio in
    testa.
    """
    esclusi = set(altrui[:3])
    return [{"label": describe_chunk(chunks[i]), "url": chunks[i]["url"]}
            for i in propri[:3]
            if i not in esclusi and 0 <= i < len(chunks)]


def _consenso(rank_a: List[int], rank_b: List[int], chunks: List[dict],
              query: str, k: int, misurabile: bool = True) -> dict:
    """Consenso fra due classifiche sui primi tre chunk.

    `misurabile` distingue "i due recuperatori non concordano" da "non
    c'e' nulla su cui concordare": quando una query non trova alcun
    riscontro entrambi restituiscono l'ordine di scansione, che coincide
    con se stesso e produrrebbe un consenso 3/3 — il risultato migliore
    possibile proprio dove l'informazione e' zero. Si riporta None,
    come per un'area non misurata.
    """
    if not misurabile:
        return {"query": query, "consensus_top3": None,
                "consensus_out_of": None, "top_chunk": None,
                "top_chunk_url": None, "matched": False,
                # Liste VUOTE e non `None`: il conteggio non c'e'
                # perche' non c'e' nulla su cui concordare, e per la
                # stessa ragione non c'e' nulla su cui divergere.
                "only_lexical": [], "only_semantic": []}
    attesi = min(3, len(rank_a), len(rank_b))
    # `k` obbligatorio e senza default: e' il passaggio in cui il
    # referto puo' cominciare a dire il falso — dichiarare un k e
    # fondere con un altro — e un default lo renderebbe possibile per
    # dimenticanza. Il consenso in se' non dipende da k (e' l'incrocio
    # dei primi tre), ma il passaggio in testa si'.
    fusi = reciprocal_rank_fusion([rank_a, rank_b], k)
    top = fusi[0][0] if fusi and fusi[0][0] < len(chunks) else None
    return {
        "query": query,
        "consensus_top3": len(set(rank_a[:3]) & set(rank_b[:3])),
        "consensus_out_of": attesi,
        "top_chunk": describe_chunk(chunks[top]) if top is not None else None,
        "top_chunk_url": chunks[top]["url"] if top is not None else None,
        "matched": True,
        # QUALI passaggi stanno fuori dall'intersezione, non quanti
        # (I4 + I9). Sono due difetti editoriali opposti: un passaggio
        # nei primi tre del solo lessicale e' trovato dalle PAROLE e
        # non dal significato — spesso perche' ripete i termini della
        # domanda senza rispondere — mentre uno del solo semantico
        # risponde ma non usa le parole con cui la domanda si scrive.
        # Il conteggio "1/3" non permette di distinguerli.
        "only_lexical": _divergenti(rank_a, rank_b, chunks),
        "only_semantic": _divergenti(rank_b, rank_a, chunks),
    }


def divergenze_leggibili(voce: dict, lang: str = LINGUA_CANONICA
                         ) -> List[Tuple[str, List[dict]]]:
    """Le due direzioni della divergenza, con la loro diagnosi (I4+I9).

    Scritta una volta perche' la leggono in tre — testo, HTML e
    markdown — e tre formulazioni dello stesso fatto divergerebbero
    senza che nulla si rompa. E' l'argomento di `segnali_derivati`.

    La direzione E' la diagnosi: elencare sei passaggi senza dire da
    che parte stanno sarebbe peggio del conteggio che sostituisce.
    """
    esito: List[Tuple[str, List[dict]]] = []
    for chiave, diagnosi in (
            ("only_lexical",
             t("trovato solo dalle parole, non dal significato", lang)),
            ("only_semantic",
             t("trovato solo dal significato, non dalle parole", lang))):
        divergenti = voce.get(chiave) or []
        if divergenti:
            esito.append((diagnosi, divergenti))
    return esito


def rrf_simulation(results: dict, chunks: List[dict],
                   k: int) -> List[dict]:
    """Esito della fusione, una voce per query interrogata.

    E' la chiave che mars_citations.py --from-audit legge per riusare
    le stesse query: cosi' la stima della citabilita' e la misura delle
    citazioni reali guardano le stesse domande.
    """
    lex = results.get("mars_lexical") or {}
    sem = results.get("mars_semantic") or {}
    voci_lex = {v["query"]: v for v in lex.get("per_query") or []}
    voci_sem = {v["query"]: v for v in sem.get("per_query") or []}
    comuni = [q for q in voci_lex if q in voci_sem]
    # Basta che UNO dei due non abbia trovato nulla perche' il
    # confronto non abbia oggetto.
    return [_consenso(voci_lex[q]["rank"], voci_sem[q]["rank"], chunks, q, k,
                      misurabile=(voci_lex[q].get("matched", True)
                                  and voci_sem[q].get("matched", True)))
            for q in comuni]


# I k del sondaggio. Zero e' l'estremo in cui conta solo la POSIZIONE
# (1/(rank+1)); 300 quello in cui conta quasi solo la PRESENZA, perche'
# 1/(300+r) e' quasi lo stesso numero per ogni r. In mezzo il 10 e il 60
# del paper, che e' il predefinito. Quattro colonne: una in piu' non
# aggiunge intuizione, una in meno toglie un estremo.
SCALA_K = (0, 10, 60, 300)


def rrf_sensitivity(results: dict, chunks: List[dict],
                    k_in_uso: int) -> List[Dict[str, object]]:
    """Come cambia il consenso AGGREGATO al variare di k (I3).

    Il consenso di una singola query non dipende da k e non puo'
    dipenderne: e' l'incrocio dei primi tre di due classifiche, e la
    fusione non entra nel conto. Sondarlo darebbe una riga piatta che
    sembra una misura di robustezza e non lo e'. Il consenso aggregato
    invece dai ranghi fusi viene, e con k cambia davvero — misurato su
    un sito reale da 128 chunk: 3/3 a k=10 e 0/3 a k=60, cioe' il
    segnale «Recuperabilita'» che entra nel complessivo passa da 100 a
    0. E' la ragione per cui questo sondaggio sta nel referto e non in
    una nota didattica: quel numero il lettore lo vede altrove.

    Si rifondono le classifiche PER QUERY gia' calcolate: non si
    interroga di nuovo nulla, e il costo e' quello di qualche divisione.
    """
    lex = (results.get("mars_lexical") or {}).get("per_query") or []
    sem = (results.get("mars_semantic") or {}).get("per_query") or []
    liste_lex = [p["rank"] for p in lex if p.get("matched")]
    liste_sem = [p["rank"] for p in sem if p.get("matched")]
    if not liste_lex or not liste_sem:
        return []
    voci = []
    for k in sorted(set(SCALA_K) | {int(k_in_uso)}):
        rank_lex = [i for i, _ in reciprocal_rank_fusion(liste_lex, k)]
        rank_sem = [i for i, _ in reciprocal_rank_fusion(liste_sem, k)]
        misura = _consenso(rank_lex, rank_sem, chunks, str(k), k)
        voci.append({"k": k,
                     "consensus_top3": misura["consensus_top3"],
                     "consensus_out_of": misura["consensus_out_of"],
                     "in_use": k == int(k_in_uso)})
    return voci


def rrf_aggregate(results: dict, chunks: List[dict],
                  k: int) -> Optional[dict]:
    """Consenso sui ranghi aggregati, cioe' su tutte le query insieme.

    E' la misura piu' solida delle due: un chunk che sale in alto per
    entrambi i recuperatori su piu' domande e' recuperabile davvero,
    mentre un consenso su una sola query puo' essere un caso.
    """
    lex = results.get("mars_lexical") or {}
    sem = results.get("mars_semantic") or {}
    if "rank" not in lex or "rank" not in sem:
        return None
    aggregato = _consenso(lex["rank"], sem["rank"], chunks,
                          "(aggregato su tutte le query)", k,
                          misurabile=bool(lex["rank"] and sem["rank"]))
    aggregato["queries"] = lex.get("queries") or []
    return aggregato


# ======================================================================
# Le viste
# ======================================================================

def render_json(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """Il dato canonico, che resta **italiano in ogni lingua**.

    `lang` c'e' per uniformita' di firma e non si usa: il JSON e' cio'
    da cui le altre viste derivano, e due JSON diversi per lingua
    sarebbero due dati canonici. Chi lo consuma da un programma ha
    `key` e `params` su ogni rilievo e traduce da se' — che e' il
    motivo per cui U1 li ha messi li'.
    """
    return json.dumps(referto, indent=2, ensure_ascii=False)


# Come si legge lo "status" di un'area nelle viste umane. "surface" e'
# l'unico che convive con un punteggio, ed e' quello che R21 ha trovato
# invisibile: 100/100 dai soli header HTTP e 100/100 da una scansione
# ZAP completa sono lo stesso numero e due fatti diversi.
STATO_LEGGIBILE = {
    "surface": "controllo di superficie",
    # Un'area che ordina OLTRE a giudicare. Prima il fatto non stava
    # nel dato e le viste lo cablavano per nome del modulo: da li'
    # nasceva "Analizzato", stampato anche su un'area andata in errore.
    #
    # Diceva "classifica, non un voto", ed era vero finche' il voto non
    # c'era: U13 lo ha dato, e la frase sarebbe comparsa fra i
    # qualificatori a due centimetri dal numero che nega. Il fatto
    # resta detto, cambia cio' che afferma.
    "ranking": "con una classifica dei passaggi",
    "unavailable": "non misurato",
    "disabled": "disattivato",
    "error": "errore del modulo",
}


def _qualificatori(area: dict, lang: str = LINGUA_CANONICA) -> List[str]:
    """Con che cosa e' stato ottenuto il punteggio, e quanto vale.

    Un numero senza strumento, profondita' e campione non e' una misura
    ma un'impressione. La funzione e' condivisa fra le due viste umane
    perche' testo e HTML non possano tornare a dire cose diverse:
    prima queste informazioni comparivano solo dove esisteva un
    wcag_level, cioe' per la sola accessibilita'.

    Lo stato si annota solo se convive con un punteggio: quando il
    punteggio manca, "non misurato" e "disattivato" prendono gia' il
    posto del numero e ripeterli sarebbe rumore.

    Il nome dello strumento passa da `t()` per i modi che una parola
    italiana ce l'hanno — «ZAP (attiva)», «markup» — ma quelli che il
    modulo COMPONE, come «vettoriale <modello>» o «BM25 (k1=1.5,
    b=0.75)», nessun catalogo puo' contenerli e restano come lo
    strumento si e' nominato. `wcag_level` e `form_factor` non ci
    passano affatto: «WCAG 2.1 AA» e «mobile» sono gli stessi in ogni
    lingua.
    """
    pezzi: List[str] = []
    if area.get("tool"):
        pezzi.append(t(str(area["tool"]), lang))
    if area.get("wcag_level"):
        pezzi.append(str(area["wcag_level"]))
    if area.get("score") is not None and area.get("status") in STATO_LEGGIBILE:
        pezzi.append(t(STATO_LEGGIBILE[area["status"]], lang))
    if area.get("complete") is False:
        pezzi.append(t("scansione parziale", lang))
    if area.get("pages_tested"):
        pezzi.append(t("%d pagine esaminate", lang) % area["pages_tested"])
    if area.get("form_factor"):
        # Un referto mobile e uno desktop non sono confrontabili.
        pezzi.append(str(area["form_factor"]))
    if area.get("reference_score") is not None:
        # Il numero dell'altro strumento, con la ragione per cui
        # differisce. Senza quella ragione sarebbero due voti in
        # contraddizione; con essa sono due misure con scale diverse,
        # ed e' un'informazione in piu' invece che un dubbio.
        pezzi.append(t("%s %.0f/100 (1 pagina, scala diversa: la nostra è "
                       "più severa)", lang)
                     % (area.get("reference_tool")
                        or t("altro strumento", lang),
                        area["reference_score"]))
    controlli = area.get("audits") or []
    if controlli:
        superati = sum(1 for c in controlli if c.get("passed"))
        falliti = sum(1 for c in controlli
                      if not c.get("passed") and not c.get("manual"))
        pezzi.append(t("%d controlli superati, %d falliti", lang)
                     % (superati, falliti))
    return pezzi


def _quota_consenso(voce: dict) -> Optional[float]:
    """Il consenso in percentuale, o None se non era misurabile."""
    if voce.get("consensus_top3") is None or not voce.get("consensus_out_of"):
        return None
    return 100.0 * voce["consensus_top3"] / voce["consensus_out_of"]


def sensibilita_leggibile(voci: List[dict],
                          lang: str = LINGUA_CANONICA) -> str:
    """Il sondaggio su k come una riga sola, per tutte e tre le viste.

    Una riga e non una tabella: sono quattro numeri, e il lettore deve
    poterli confrontare con un colpo d'occhio. Il k in uso e' marcato,
    altrimenti sono quattro valori e nessuno che sia il suo.
    """
    if not voci:
        return ""
    pezzi = []
    for v in voci:
        etichetta = "k=%d" % v["k"]
        if v.get("in_use"):
            etichetta += " (%s)" % t("in uso", lang)
        pezzi.append("%s %s" % (etichetta, _consenso_leggibile(v, lang)))
    return " · ".join(pezzi)


def _consenso_leggibile(voce: dict,
                        lang: str = LINGUA_CANONICA) -> str:
    """Il consenso come lo legge una persona.

    "nessun riscontro" e "0/3" sono cose diverse: la prima dice che la
    domanda non ha trovato nulla nel sito, la seconda che i due
    recuperatori hanno trovato cose diverse. Confonderle nascondeva il
    caso peggiore — una query a vuoto riportata come consenso pieno.
    """
    if voce.get("consensus_top3") is None:
        return t("nessun riscontro", lang)
    return "%d/%d" % (voce["consensus_top3"], voce["consensus_out_of"])


# Le tre parole della scala, agganciate alle stesse soglie del colore:
# se un giorno si ritarano, verdetto e pallino non possono divergere.
def _verdetto(valore: Optional[float],
              lang: str = LINGUA_CANONICA) -> str:
    if valore is None:
        return t("non misurato", lang)
    return t("buono" if valore >= SOGLIA_BUONO
             else "da migliorare" if valore >= SOGLIA_MEDIO
             else "critico", lang)


def _ha_blocco_dedicato(area: dict, referto: dict) -> bool:
    """Vero se quest'area ha gia' una sezione tutta sua, piu' sotto.

    Una sola area ce l'ha, la citabilita', e **solo quando ha prodotto i
    profili**: e' la stessa condizione che protegge quel blocco, letta
    in un posto solo perche' le due non possano divergere. Se
    divergessero, l'area comparirebbe due volte o nessuna — e il secondo
    caso e' esattamente il difetto R42.
    """
    if area.get("module") != "mars_citability":
        return False
    return bool((referto.get("citability") or {}).get("profiles"))


def aree_escluse_leggibili(referto: dict,
                           lang: str = LINGUA_CANONICA) -> str:
    """Le aree tenute fuori dal complessivo, per etichetta.

    Si legge da `overall["excluded"]` invece di scriverle a mano nelle
    tre viste. La frase diceva «citabilità e giudizio LLM esclusi», ed
    e' rimasta vera finche' le escluse erano due: U13 ne ha aggiunte
    due, e nessun test poteva accorgersene perche' quella riga era
    prosa, non dato. Da qui in poi una decisione su
    `AREE_FUORI_DAL_COMPLESSIVO` si propaga da sola.
    """
    etichette = {area.get("module"): area.get("label") or area.get("module")
                 for area in referto.get("areas") or []}
    escluse = (referto.get("overall") or {}).get("excluded") or []
    return ", ".join(t(str(etichette.get(nome, nome)), lang)
                     for nome in escluse)


def _riga_complessivo(referto: dict,
                      lang: str = LINGUA_CANONICA) -> List[str]:
    """Il complessivo in testa, con che cosa lo compone.

    Un numero solo per nove aree e' utile quanto e' verificabile: la
    riga sotto dice quante misure ci sono dentro e quali non ci sono
    per decisione, cosi' chi legge 68 sa che non e' la media di tutto.
    """
    complessivo = referto.get("overall")
    if not complessivo:
        return []
    righe = ["%-20s : %3.0f/100  (%s)"
             % (t("COMPLESSIVO", lang), complessivo["score"],
                _verdetto(complessivo["score"], lang))]
    righe.append(t("  media pesata di %d misure; escluse %s", lang)
                 % (len(complessivo["components"]),
                    aree_escluse_leggibili(referto, lang)))
    righe.append("-" * 55)
    return righe


def _riga_area(area: dict, lang: str = LINGUA_CANONICA) -> str:
    etichetta = t(area["label"], lang)
    if area["score"] is None:
        stato = t(STATO_LEGGIBILE.get(area["status"], "non misurato"), lang)
        return f"{etichetta:<20} : {stato}"
    return f"{etichetta:<20} : {area['score']:>3.0f}/100"


def _correzioni_testo(findings: List[dict],
                      nel_piano: frozenset = frozenset(),
                      quante: int = 2,
                      lang: str = LINGUA_CANONICA) -> List[str]:
    """Le correzioni d'area che il piano NON prende in carico.

    Titolo e poi prescrizione, come nel referto HTML, e per la stessa
    ragione: fra `issues` e `findings` non esiste una chiave — per
    posizione si disallineano appena axe o ZAP superano le cinque
    regole — quindi un `-> fix` appeso sotto le due issues lascerebbe
    il lettore a indovinare a quale delle due si riferisce. Col titolo
    non c'e' niente da indovinare, al prezzo di una riga ripetuta.

    `nel_piano` e' arrivato con U4.3, e toglie una duplicazione che si
    vedeva a occhio nudo: la sezione del piano stampa gli stessi titoli
    e gli stessi fix, ordinati per valore, quaranta righe piu' sotto.
    Restano qui le correzioni che il piano non elenca — i rilievi
    `info`, che il suo filtro esclude — e che altrimenti sparirebbero
    dalla vista testo pur avendo una prescrizione.

    Due, come le issues: questa e' la vista che sta in un terminale.
    L'`example` resta fuori — sono blocchi nginx e JSON-LD di cinque o
    sette righe, e due per area triplicherebbero il referto. Chi li
    vuole ha l'HTML e il JSON, dove ci sono per intero.
    """
    righe: List[str] = []
    fuori = [x for x in findings
             if x.get("fix") and x.get("key") not in nel_piano]
    for f in fuori[:quante]:
        testi = finding_texts(f, lang)
        righe.append("  → %s" % testi["title"])
        righe.append("    %s" % testi["fix"])
    return righe


# Quanti interventi mostra la vista compatta. Cinque, come i cinque
# alert ZAP e le cinque violazioni axe: e' la stessa asimmetria di
# sempre fra la vista che sta in un terminale e il dato che li porta
# tutti.
PIANO_IN_TESTO = 5

_GRAVITA_TESTO = {SEV_CRITICAL: "CRITICO", SEV_WARNING: "AVVERTENZA"}


def _voce_piano_testo(voce: dict,
                      lang: str = LINGUA_CANONICA) -> List[str]:
    """Una voce del piano: intestazione, numeri, prescrizione."""
    testi = finding_texts(voce, lang)
    righe = ["  %d. [%s · %s · %s] %s"
             % (voce["priority"],
                t(_GRAVITA_TESTO.get(voce["severity"], voce["severity"]),
                  lang),
                t(voce["area_label"], lang).split(". ", 1)[-1],
                t(voce["effort"], lang) if voce["effort"]
                else t("sforzo non dichiarato", lang),
                testi["title"])]

    numeri = []
    if voce["recovery"]:
        # Punteggio di partenza e di arrivo accanto alla differenza: e'
        # cio' che permette di rifare il conto leggendo il referto, e in
        # un'area satura e' anche l'unica spiegazione del perche' una
        # penalita' di 40 ne renda 32.
        numeri.append(t("+%d punti d'area (%d → %d)", lang)
                      % (voce["recovery"], voce["score_before"],
                         voce["score_after"]))
    if voce["index_gain"]:
        numeri.append(t("indice +%.2f", lang) % voce["index_gain"])
    if not numeri:
        # Mai un silenzio al posto di un numero: la corsia dice perche'
        # non c'e', e sono tre ragioni diverse.
        numeri.append(t(voce["lane_reason"], lang) if voce["lane_reason"]
                      else t("recupero non dichiarato", lang))
    if voce["quick_win"]:
        numeri.insert(0, t("** QUICK WIN", lang))
    righe.append("     %s" % " · ".join(numeri))

    if testi["fix"]:
        righe.append("     %s" % testi["fix"])
    return righe


# Quanti rilievi risolti o nuovi mostra la vista compatta.
DELTA_IN_TESTO = 3


def _segno(valore: float, lang: str = LINGUA_CANONICA) -> str:
    """Un numero con il segno sempre visibile: «+3» e «-3», mai «3»."""
    return "%+.0f" % valore if valore else t("invariato", lang)


def _superficie_testo(referto: dict,
                      lang: str = LINGUA_CANONICA) -> List[str]:
    """La superficie: quanto e' profondo il sito e quanto contenuto ha."""
    profondita = depth_distribution(referto.get("pages") or [])
    matematica = referto.get("surface_math")
    if not profondita and not matematica:
        return []
    righe = ["-" * 55, t("SUPERFICIE", lang)]
    for voce in profondita:
        # Barra e conteggio, come i profili di citabilita': la forma
        # della distribuzione si legge prima dei numeri.
        righe.append("  %-20s %3d  %s" % (t(voce["label"], lang),
                                          voce["pages"],
                                          "█" * min(voce["pages"], 30)))
    if matematica:
        righe.append(t("  %d pagine, %d passaggi (%.2f per pagina, %.0f "
                       "parole per pagina)", lang)
                     % (matematica["pages"], matematica["chunks"],
                        matematica["chunks_per_page"],
                        matematica["words_per_page"]))
        if matematica["multiplier"]:
            righe.append(t("  Con %d parole per pagina i passaggi "
                           "sarebbero %d, cioe' x%.1f", lang)
                         % (matematica["target_words_per_page"],
                            matematica["potential_chunks"],
                            matematica["multiplier"]))
        righe.append("  (%s)" % t(matematica["assumption"], lang))
    return righe


def _delta_testo(referto: dict,
                 lang: str = LINGUA_CANONICA) -> List[str]:
    """Il confronto con l'esecuzione precedente, se c'e'.

    Assente alla prima, e la sezione **non compare**: una sezione
    «rispetto a prima» con tutto invariato direbbe che non e' cambiato
    nulla, che e' un'altra cosa da «non c'e' un prima». E' l'opposto
    della scelta fatta per il piano, dove la sezione resta anche vuota
    — li' il vuoto e' un risultato, qui e' un'assenza.
    """
    delta = referto.get("delta")
    if not delta:
        return []
    righe = ["-" * 55,
             t("RISPETTO A PRIMA     : %s", lang)
             % (delta.get("previous_run") or "?")]
    if delta.get("overall"):
        righe.append(t("  Complessivo          %s  (%.0f → %.0f)", lang)
                     % (_segno(delta["overall"]["change"], lang),
                        delta["overall"]["before"],
                        delta["overall"]["after"]))
    for voce in delta["scores"]:
        if not voce["change"]:
            continue
        righe.append("  %-20s %s  (%.0f → %.0f)"
                     % (voce["area"].replace("mars_", ""),
                        _segno(voce["change"], lang), voce["before"],
                        voce["after"]))
    for etichetta, elenco in ((t("risolti", lang), delta["resolved"]),
                              (t("nuovi", lang), delta["new"])):
        if not elenco:
            continue
        righe.append("  %d %s:" % (len(elenco), etichetta))
        for rilievo in elenco[:DELTA_IN_TESTO]:
            righe.append("    · %s" % finding_texts(rilievo, lang)["title"])
        if len(elenco) > DELTA_IN_TESTO:
            righe.append(t("    · ... e altri %d", lang)
                         % (len(elenco) - DELTA_IN_TESTO))
    cambio_k = delta.get("rrf_k_changed")
    if cambio_k:
        righe.append(t("  (il k della fusione è cambiato, da %d a %d: il "
                       "consenso aggregato non è la stessa misura)", lang)
                     % (cambio_k["before"], cambio_k["after"]))
    if delta.get("by_title_fallback"):
        righe.append(t("  (qualche rilievo non ha una chiave stabile: "
                       "confrontato sul titolo)", lang))
    for migrazione in delta.get("key_migrations") or []:
        righe.append(t("  (le chiavi %s hanno cambiato forma: li' "
                       "«risolto» e «comparso» non sono fatti del sito)",
                       lang) % migrazione["prefix"])
    for cambio in delta.get("measure_changes") or []:
        # Senza il numero di versione: e' un campo volatile, e il
        # presidio dei golden lo vieta nelle rese. Sta nel JSON, in
        # `since`, per chi deve sapere da quando.
        righe.append(t("  (e' cambiato che cosa si misura: i numeri si "
                       "muovono anche a sito invariato)", lang))
    return righe


def _piano_testo(referto: dict,
                 lang: str = LINGUA_CANONICA) -> List[str]:
    """La sezione del piano, per la vista compatta.

    **Sempre stampata**, anche vuota, e non e' una svista: le altre tre
    sezioni spariscono quando manca il dato, e qui sarebbe un errore —
    un piano che sparisce non si distingue da un piano non calcolato.
    E' il principio 5 applicato alla sezione invece che al numero.

    Le condizioni guardano il DATO e mai il nome di un modulo: e' il
    difetto R42, dove `mars_citability` spariva dalla vista testo
    perche' la si saltava per nome anche quando falliva.
    """
    piano = referto.get("remediation") or []
    riepilogo = mars_remediation.riepilogo(piano, referto)
    righe = ["-" * 55]
    if not piano:
        righe.append(t("PIANO DI INTERVENTI  : nessun rilievo critico o "
                       "di avvertenza", lang))
        return righe

    righe.append(t("PIANO DI INTERVENTI  : %d interventi (%d critici, "
                   "%d avvertenze)", lang)
                 % (riepilogo["total"], riepilogo["critical"],
                    riepilogo["warning"]))
    conteggi = [t("%d quick win", lang) % riepilogo["quick_wins"]]
    senza = riepilogo["total"] - riepilogo["by_lane"]["misurato"]
    if senza:
        conteggi.append(t("%d senza recupero", lang) % senza)
    if riepilogo["no_effort"]:
        conteggi.append(t("%d senza sforzo dichiarato", lang)
                        % riepilogo["no_effort"])
    righe.append("  %s" % " · ".join(conteggi))
    # Quante aree lo alimentano, CONTATE e non cablate: al massimo
    # cinque delle nove, perche' due non producono rilievi e due li
    # producono tutti `info`. Un numero fisso qui sarebbe falso in una
    # riga scritta per essere onesta.
    righe.append(t("  %d aree su %d; ordinato per gravita', poi per "
                   "guadagno dell'indice", lang)
                 % (riepilogo["areas_covered"], riepilogo["areas_total"]))

    for voce in piano[:PIANO_IN_TESTO]:
        righe.extend(_voce_piano_testo(voce, lang))
    if len(piano) > PIANO_IN_TESTO:
        righe.append(t("  · ... e altri %d interventi (per intero nel JSON "
                       "e nell'HTML)", lang)
                     % (len(piano) - PIANO_IN_TESTO))
    return righe


def _area_di(referto: dict, modulo: str) -> dict:
    """L'area di un modulo, o un guscio vuoto se non c'e'.

    Guarda il DATO e non l'indice: le aree possono mancare — un modulo
    non sul filesystem non produce una voce — e indicizzare per
    posizione e' il difetto che R42 ha chiuso in questa stessa vista.
    """
    for area in referto.get("areas") or []:
        if area.get("module") == modulo:
            return area
    return {}


def giudizi_del_referto(referto: dict) -> List[dict]:
    """I giudici dell'area 9, dal piu' recente dei due campi.

    `llm_judgements` esiste da U10 e li porta tutti; `llm_judgement`
    e' il primo che ha risposto, ed e' quello che i consumatori
    scritti prima di U10 leggono. Il ripiego serve a un referto
    JSON archiviato prima di U10 e riaperto oggi: senza, quella
    sezione sparirebbe dalla resa invece di mostrare cio' che c'e'.
    """
    giudizi = referto.get("llm_judgements") or []
    if giudizi:
        return [g for g in giudizi if isinstance(g, dict)]
    legacy = referto.get("llm_judgement") or {}
    if legacy.get("motivazione"):
        return [dict(legacy, answered=True)]
    return []


def scarti_leggibili(giudizio: dict,
                     lang: str = LINGUA_CANONICA) -> List[Tuple[str, str]]:
    """Gli scarti di onesta' di un giudice, come coppie gia' rese.

    Una funzione sola per le tre viste: la stessa aritmetica scritta
    tre volte diverge, e qui non c'e' aritmetica ma una convenzione di
    segno — giudizio meno euristica — che tre rese diverse
    presenterebbero in tre modi.

    Il segno si stampa SEMPRE, `+` compreso: uno scarto senza segno si
    legge come un punteggio.
    """
    scarti = giudizio.get("scarti") or {}
    righe: List[Tuple[str, str]] = []
    composito = scarti.get("delta_composite")
    if isinstance(composito, (int, float)):
        righe.append((t("scarto vs indice composito:", lang),
                      "%+.1f" % composito))
    profilo = scarti.get("delta_profile")
    if isinstance(profilo, (int, float)):
        righe.append((t("scarto vs profilo %s:", lang)
                      % scarti.get("profile", ""), "%+.1f" % profilo))
    return righe


def strumenti_in_altra_lingua(referto: dict,
                              lang: str = LINGUA_CANONICA) -> List[str]:
    """Gli strumenti i cui testi NON sono nella lingua del referto.

    Non si deduce dal testo — nessuno qui riconosce una lingua — ma si
    legge da `params["text_lang"]`, che le tre aree con testi di terzi
    dichiarano rilievo per rilievo. Per REGOLA e non per area: un
    locale axe copre quasi tutte le regole ma non quelle aggiunte a
    mano con `axe.configure`, e dire «l'area e' in italiano» con dentro
    due regole inglesi sarebbe una mezza verita'.

    Vale in OGNI lingua, italiano compreso: ZAP scrive solo in inglese,
    e un referto italiano che non lo dicesse lascerebbe credere a una
    dimenticanza cio' che e' un limite dello strumento.
    """
    per_strumento: Dict[str, str] = {}
    for area in referto.get("areas") or []:
        for rilievo in area.get("findings") or []:
            altra = str((rilievo.get("params") or {}).get("text_lang") or "")
            if not altra or altra == lang:
                continue
            nome = str(area.get("tool") or area.get("module") or "")
            if nome:
                per_strumento.setdefault(nome, altra)
    return ["%s (%s)" % (nome, lingua)
            for nome, lingua in sorted(per_strumento.items())]


def _nota_lingua(referto: dict,
                 lang: str = LINGUA_CANONICA) -> List[str]:
    """Le note di onesta' sulla lingua, in testa alle viste di prosa.

    Tre cose che il lettore non puo' dedurre: che le evidenze citate
    dal sito restano nella lingua del sito — un titolo mancante o un
    testo di link generico si citano com'erano — QUALI aree non sono
    state tradotte, per nome invece che genericamente, e quali
    STRUMENTI hanno scritto in un'altra lingua.

    L'ultima compare anche in italiano, le prime due no: fuori
    dall'italiano il ripiego e' sulla lingua canonica e va detto,
    mentre in italiano non c'e' alcun ripiego da dichiarare — ma ZAP
    resta inglese comunque.
    """
    righe: List[str] = []
    if lang != LINGUA_CANONICA:
        righe += ["", t("Nota: le evidenze citate dal sito analizzato "
                        "restano nella lingua del sito.", lang)]
        rimaste = aree_non_tradotte(referto, lang)
        if rimaste:
            righe.append(t("Queste aree si esprimono solo in italiano: %s.",
                           lang) % ", ".join(rimaste))
    strumenti = strumenti_in_altra_lingua(referto, lang)
    if strumenti:
        if not righe:
            righe.append("")
        righe.append(t("I testi di questi strumenti restano nella loro "
                       "lingua: %s.", lang) % ", ".join(strumenti))
    return righe


def _righe_compatte(area: dict,
                    lang: str = LINGUA_CANONICA) -> List[str]:
    """La vista compatta di un'area: le `issues`, o i titoli dei rilievi.

    Le `issues` sono la vista storica, e sono **prosa italiana senza
    chiave**: U1 le ha lasciate intatte di proposito, quindi non c'e'
    nulla su cui indicizzare una traduzione. I `findings` dicono le
    stesse cose e una chiave ce l'hanno, cosi' in una lingua diversa
    dalla canonica si stampano quelli.

    Non e' un ripiego nascosto: le due viste possono avere cardinalita'
    diversa — `mars_schema` emette una issue per blocco e un rilievo per
    controllo — ed e' scritto qui invece che in tre renderer perche'
    testo, HTML e Markdown non possano divergere.

    Dove i rilievi non ci sono restano le issues italiane, e il referto
    lo dichiara in testa. Da U10.1 nessuna area del progetto e' piu' in
    quel caso — il giudizio LLM, che era l'ultima, etichetta i propri
    punti deboli — ma il ramo resta: un modulo di terzi non e' tenuto a
    emettere rilievi.
    """
    if lang == LINGUA_CANONICA:
        return list(area.get("issues") or [])
    rilievi = area.get("findings") or []
    if not rilievi:
        return list(area.get("issues") or [])
    return [finding_texts(f, lang)["title"] for f in rilievi]


def aree_non_tradotte(referto: dict,
                      lang: str = LINGUA_CANONICA) -> List[str]:
    """Le aree che in questa lingua restano italiane, per nome.

    Serve alla nota di onesta' in testa alle viste di prosa: dire «le
    evidenze citate restano nella lingua del sito» e' vero ma generico,
    dire QUALI aree non sono state tradotte e' verificabile.
    """
    if lang == LINGUA_CANONICA:
        return []
    rimaste = []
    for area in referto.get("areas") or []:
        if area.get("issues") and not area.get("findings"):
            rimaste.append(t(area["label"], lang))
    return rimaste


def render_text(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    lang = normalizza_lingua(lang)
    righe = ["", "=" * 55,
             t("           MARS BEACON - REPORT FINALE           ", lang),
             "=" * 55]
    righe.extend(_nota_lingua(referto, lang))

    righe.extend(_riga_complessivo(referto, lang))

    # Le chiavi che il piano gia' elenca: sotto l'area si stampano solo
    # le correzioni che lui non prende in carico.
    nel_piano = frozenset(v["key"] for v in referto.get("remediation") or [])
    for area in referto["areas"]:
        # La citabilita' ha un blocco tutto suo in fondo — ma solo
        # quando i profili ci sono. Si salta quindi sul DATO e non sul
        # nome del modulo (R42): quando i profili non ci sono, e cioe'
        # proprio quando qualcosa e' andato storto, la vista testo
        # taceva del tutto — ne' il nome dell'area ne' il motivo,
        # mentre l'HTML la mostrava. Era R38 rimasta aperta per una
        # sola area su nove, e l'ultimo punto di `render_text` che
        # decideva su un nome di modulo.
        if _ha_blocco_dedicato(area, referto):
            continue
        righe.append(_riga_area(area, lang))
        # Con che cosa e' stato misurato, per OGNI area e non piu' per
        # la sola accessibilita': senza, 100/100 dai soli header HTTP
        # e 100/100 da un WAPT completo erano due righe identiche.
        qualifiche = _qualificatori(area, lang)
        if qualifiche:
            righe.append("  " + " · ".join(qualifiche))
        for problema in _righe_compatte(area, lang)[:2]:
            righe.append(f"  ⚠ {problema}")
        righe.extend(_correzioni_testo(area.get("findings") or [],
                                       nel_piano, lang=lang))

    righe.extend(_superficie_testo(referto, lang))
    righe.extend(_delta_testo(referto, lang))
    righe.extend(_piano_testo(referto, lang))

    aggregato = referto.get("rrf_aggregate")
    if aggregato:
        righe.append("-" * 55)
        righe.append(t("Simulazione RRF      : Consenso Top-3 = %s su %d "
                       "chunk", lang)
                     % (_consenso_leggibile(aggregato, lang),
                        referto["chunks"]))
        righe.append(t("  aggregato su %d query", lang)
                     % len(referto["rrf_simulation"]))
        sensibilita = sensibilita_leggibile(
            referto.get("rrf_sensitivity") or [], lang)
        if sensibilita:
            righe.append("  %s %s" % (t("al variare di k:", lang),
                                      sensibilita))
        if aggregato["top_chunk"]:
            righe.append("%s %s" % (t("Top Chunk Ibrido     :", lang),
                                    aggregato["top_chunk"]))
        for voce in referto["rrf_simulation"]:
            righe.append("  %-34s %s" % (voce["query"][:34],
                                         _consenso_leggibile(voce, lang)))
        # DOPO l'elenco per query, non prima: l'elenco non ha
        # un'intestazione propria, e un blocco rientrato infilato sopra
        # se lo prendeva — le tre query sembravano una terza direzione
        # della divergenza. Qui il titolo a colonna zero chiude la
        # sezione invece di aprirne una che ingloba cio' che segue.
        divergenze = divergenze_leggibili(aggregato, lang)
        if divergenze:
            righe.append(t("Fuori dall'intersezione:", lang))
            for diagnosi, divergenti in divergenze:
                righe.append("  %s" % diagnosi)
                for passaggio in divergenti:
                    righe.append("    %s" % passaggio["label"])

    cit = referto.get("citability")
    if cit and cit.get("profiles"):
        righe.append("-" * 55)
        righe.append(t("Profili di citabilità IA  (mercato: %s)", lang)
                     % cit.get("market"))
        for assistente, valore in cit["profiles"].items():
            barra = "█" * int((valore or 0) / 5)
            testo = f"{valore:>5.1f}" if valore is not None else "  n/d"
            righe.append(f"  {assistente:<20} {testo}  {barra}")
        if cit.get("score") is not None:
            composito = t("INDICE COMPOSITO", lang)
            righe.append(f"  {composito:<20} {cit['score']:>5.1f}")
        # Il disclaimer sta QUI e non in fondo: chi legge il numero
        # deve leggere anche cosa non è.
        righe.append("  (%s)" % t(cit.get("disclaimer", ""), lang))
        for nota in _righe_compatte(_area_di(referto, "mars_citability"),
                                    lang)[:3]:
            righe.append(f"  · {nota}")

    giudizi = giudizi_del_referto(referto)
    if giudizi:
        righe.append("-" * 55)
        for giudizio in giudizi:
            righe.append(t("Giudizio LLM (%s)  su %s passaggi", lang)
                         % (giudizio.get("model"),
                            giudizio.get("chunk_valutati")))
            if not giudizio.get("answered"):
                # Un giudice che non ha risposto si DICHIARA, non
                # sparisce: il motivo e' nelle sue issues, e senza
                # questa riga il referto mostrerebbe tre giudici dove
                # se ne sono pagati quattro.
                for motivo in giudizio.get("issues") or []:
                    righe.append("  · %s" % motivo)
                continue
            if giudizio.get("score") is not None:
                righe.append("%s %s/100"
                             % (t("  Citabilità stimata   :", lang),
                                giudizio["score"]))
            righe.append("  %s" % giudizio.get("motivazione", ""))
            for etichetta, valore in scarti_leggibili(giudizio, lang):
                righe.append("  %-21s %s" % (etichetta, valore))
            if giudizio.get("passaggio_migliore"):
                righe.append("%s %s"
                             % (t("  Passaggio migliore   :", lang),
                                giudizio["passaggio_migliore"]))
            for punto in (giudizio.get("punti_deboli") or [])[:2]:
                righe.append("  · %s: %s"
                             % (t("da migliorare", lang, "llm"), punto))
        if any(scarti_leggibili(g, lang) for g in giudizi):
            righe.append("  (%s)" % t("gli scarti confrontano un giudizio "
                                      "con una stima euristica", lang))

    if referto["robots_ignored"]:
        righe.append("-" * 55)
        righe.append(t("⚠ robots.txt IGNORATO per dichiarazione "
                       "di proprieta'", lang))
    saltati = referto["skipped"]
    if saltati:
        righe.append("-" * 55)
        righe.append("%s %d" % (t("URL saltati          :", lang),
                                len(saltati)))
        for motivo in saltati[:3]:
            righe.append(f"  · {motivo}")
        if len(saltati) > 3:
            righe.append(t("  · ... e altri %d", lang) % (len(saltati) - 3))

    righe.append("-" * 55)
    righe.append(t("Pagine trovate via   : %s  (%d pagine, %d chunk)", lang)
                 % (t(referto.get("discovery") or "", lang),
                    referto["pages_crawled"], referto["chunks"]))
    righe.append("=" * 55)
    righe.append("")
    return "\n".join(righe)


#: Firma dei formati che l'icona puo' avere -> tipo MIME. Si guardano i
#: BYTE e non l'estensione, ed e' R43: il file si chiama `favicon.ico`
#: ma `file(1)` dice «PNG image data, 32 x 32», mentre il referto lo
#: dichiarava `image/x-icon`. I browser lo digeriscono, ma la
#: dichiarazione era falsa — e cablare `image/png` al suo posto
#: sposterebbe soltanto la bugia al giorno in cui l'icona cambia.
FIRME_ICONA = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\x00\x00\x01\x00", "image/x-icon"),
    (b"GIF8", "image/gif"),
    (b"<svg", "image/svg+xml"),
    (b"<?xml", "image/svg+xml"),
)

#: Quando i byte non dicono nulla. Un data URI senza tipo vale
#: `text/plain`, che nessun browser disegnerebbe: meglio dichiarare
#: un'immagine generica e lasciar decidere a lui.
MIME_ICONA_IGNOTO = "application/octet-stream"


def tipo_icona(dati: bytes) -> str:
    """Il MIME dell'icona, letto dai suoi byte.

    Funzione pura: si prova senza toccare il filesystem.
    """
    for firma, mime in FIRME_ICONA:
        if dati.startswith(firma):
            return mime
    return MIME_ICONA_IGNOTO


def _favicon_data_uri() -> str:
    """L'icona del referto incorporata come data URI.

    Si usa il file da 2,8 KB e non il PNG da 344 KB: il referto deve
    restare un file solo, ma non a costo di mezzo megabyte di icona.

    Il tipo si legge dai byte (`tipo_icona`), non dall'estensione.

    Stringa vuota se il file non c'e' o non si legge — e a differenza di
    prima **chi rende lo dichiara**: il degrado era silenzioso, e su un
    checkout parziale il referto perdeva l'icona senza che nessuno lo
    sapesse (R43).
    """
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            FAVICON)
    try:
        with open(percorso, "rb") as handle:
            grezzi = handle.read()
    except OSError:
        return ""
    return "data:%s;base64,%s" % (tipo_icona(grezzi),
                                  base64.b64encode(grezzi).decode("ascii"))


def _e(valore: object) -> str:
    """Escape: il referto contiene testo preso dal sito analizzato."""
    return html.escape(str(valore if valore is not None else ""))


def _plurale(quante: int, singolare: str, plurale: str,
             lang: str = LINGUA_CANONICA) -> str:
    """«1 pagina» e «3 pagine», mai «1 pagine».

    Un referto si consegna, e un accordo sbagliato e' la prima cosa che
    si nota: costa meno scriverlo giusto che spiegare perche' non lo e'.
    """
    # Il contesto e' obbligatorio qui e non opzionale: in italiano
    # «click» non cambia al plurale, quindi le due parole arrivano
    # identiche e senza contesto il catalogo non potrebbe distinguerle.
    return "%d %s" % (quante,
                      t(singolare if quante == 1 else plurale, lang,
                        "singolare" if quante == 1 else "plurale"))


CSS = """
/* La palette e' quella di lymphatechnologies.com, misurata sugli stili
   calcolati del sito (U11.1). Un tema solo, il chiaro: l'identita' del
   sito e' pensata per il chiaro, e una variante scura inventata da noi
   non sarebbe la sua.
   I tre colori di gravita' vengono da Bootstrap Italia, che il sito
   usa, e non sono una scelta estetica: quelli di Lighthouse — #0cce6b
   e #ffa400 — stanno a 2,09:1 e 1,99:1 su bianco, sotto perfino la
   soglia 3:1 dei componenti, e sono i colori con cui questo referto
   scrive i punteggi. Un referto che misura l'accessibilita' non puo'
   fallire i propri criteri. La scala resta 90/50 e il simbolo
   accompagna sempre il colore: cambiano le tinte, non il significato. */
/* Due tinte sono state scostate da quelle del sito, e la ragione e'
   misurata su questo referto e non dedotta: `--muted` e' il grigio del
   sito (#5d7083) sceso di un gradino, perche' a quella tinta il
   `<code>` dentro `.meta` sta a 4,19:1 e axe lo rileva; `--track` e'
   salito di un gradino da #e3eaec, perche' l'etichetta del `fix`
   dentro un rilievo raggiunto da un'ancora (`li:target`) ci finisce
   sopra e stava a 4,44:1. Sono i due fondi su cui il referto scrive
   davvero. (La parola italiana di quell'etichetta non si scrive qui:
   il presidio di R61 la cerca in tutta la pagina.) */
:root { --ok:#008055; --warn:#995c00; --bad:#cc334d; --bg:#fff;
        --fg:#14272b; --muted:#556879; --line:#dde5e7; --card:#f4f7f8;
        --track:#e6edee; --brand:#0c3540; --link:#1e4c5a;
        --ombra:0 1px 3px rgba(12,53,64,.08); }
* { box-sizing:border-box; }
body { margin:0; padding:0 0 3rem; background:var(--bg); color:var(--fg);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:64rem; margin:0 auto; padding:0 1rem; }
header.testata { border-bottom:1px solid var(--line); margin-bottom:1.5rem;
                 padding:1.75rem 0 1.25rem; }
h1 { font-size:1.35rem; margin:0 0 .3rem; letter-spacing:-.01em;
     color:var(--brand); }
h2 { font-size:1.05rem; margin:2.25rem 0 .85rem;
     border-bottom:1px solid var(--line); padding-bottom:.4rem;
     color:var(--brand); }
h3 { font-size:.95rem; margin:0; color:var(--brand); }
a { color:var(--link); }
.meta { color:var(--muted); font-size:.87rem; margin:.15rem 0; }
.meta code { word-break:break-all; }

/* --- fascia dei quadranti, la firma visiva di Lighthouse --- */
.quadranti { display:flex; flex-wrap:wrap; gap:.5rem 1.5rem;
             justify-content:center; padding:1.25rem 0 .5rem; }
.quadrante { width:8.5rem; text-align:center; }
.quadrante svg { display:block; margin:0 auto; width:5.5rem; height:5.5rem; }
.quadrante .nome { font-size:.82rem; margin-top:.35rem; line-height:1.3;
                   color:var(--fg); }
.quadrante .nota { font-size:.72rem; color:var(--muted); }
.quadrante .nota.parziale, .strumento.parziale { color:var(--warn); }
.anello-fondo { stroke:var(--track); }
.valore { font:600 30px/1 system-ui,sans-serif; }
.valore.piccolo { font-size:22px; }

/* --- legenda della scala --- */
.legenda { display:flex; flex-wrap:wrap; gap:1rem; justify-content:center;
           font-size:.78rem; color:var(--muted); padding:.5rem 0 .25rem; }
.legenda span { white-space:nowrap; }
.pallino { display:inline-block; width:.62rem; height:.62rem;
           border-radius:50%; vertical-align:-1px; margin-right:.3rem; }
.pallino.vuoto { background:none; border:1.5px dashed var(--muted); }

/* --- schede d'area --- */
.area { background:var(--card); border:1px solid var(--line);
        border-radius:.6rem; padding:.9rem 1rem; margin:.6rem 0;
        box-shadow:var(--ombra); }
.area .riga, .intervento .riga { display:flex; align-items:baseline;
              gap:.6rem; justify-content:space-between; }
.punteggio { font-variant-numeric:tabular-nums; font-weight:600;
             white-space:nowrap; }
.strumento { font-size:.78rem; color:var(--muted); margin:.3rem 0 0; }
ul.rilievi { margin:.55rem 0 0; padding-left:1.15rem; }
ul.controlli { list-style:none; margin:.6rem 0 0; padding:0; }
ul.controlli li { font-size:.88rem; margin:.22rem 0; display:flex;
                  gap:.5rem; align-items:baseline; }
ul.controlli .segno { font-weight:700; flex:0 0 1rem; text-align:center; }
ul.controlli li.fallito .segno { color:var(--bad); }
ul.controlli li.superato .segno { color:var(--ok); }
ul.controlli li.manuale .segno, ul.controlli li.manuale { color:var(--muted); }
ul.controlli .dettaglio { color:var(--muted); font-size:.82rem;
                          word-break:break-all; }
ul.rilievi li { font-size:.88rem; margin:.15rem 0; }
.nessun-rilievo { font-size:.85rem; color:var(--muted); margin:.4rem 0 0; }

/* --- hero: il complessivo in testa (Fase 5) --- */
.hero { display:flex; flex-wrap:wrap; gap:1.5rem; align-items:center;
        justify-content:center; padding:1.5rem 0 .5rem;
        border-bottom:1px solid var(--line); }
.hero-voto { text-align:center; }
.hero .quadrante { width:12rem; }
.hero .quadrante svg { width:8.5rem; height:8.5rem; }
.hero .valore { font-size:38px; }
.verdetto { font-size:1.05rem; font-weight:600; margin:.2rem 0 .35rem;
            text-transform:uppercase; letter-spacing:.03em; }
.tessere { display:flex; flex-wrap:wrap; gap:.6rem; justify-content:center; }
.tessera { background:var(--card); border:1px solid var(--line);
           border-radius:.6rem; padding:.6rem .9rem; min-width:7rem;
           text-align:center; box-shadow:var(--ombra); }
.tessera .grande { display:block; font-size:1.5rem; }
.tessera .meta { display:block; margin:0; }

/* --- ancore stabili (Fase 5) --- */
.ancora { color:var(--muted); text-decoration:none; margin-left:.35rem;
          opacity:0; transition:opacity .1s; }
li:hover > .ancora, li:hover .ancora, .ancora:focus { opacity:1; }
li:target { background:var(--track); border-radius:.35rem;
            box-shadow:0 0 0 .35rem var(--track); }
.primi { max-width:64rem; margin:0 auto; padding:.25rem 1rem 0; }
ol.primi-rilievi { margin:.2rem 0 0; padding-left:1.4rem; font-size:.88rem; }
ol.primi-rilievi li { margin:.12rem 0; }
ol.primi-rilievi a { color:inherit; }

/* --- piano di interventi (Fase 4) --- */
.intervento { background:var(--card); border:1px solid var(--line);
              border-radius:.6rem; padding:.75rem 1rem; margin:.5rem 0;
              box-shadow:var(--ombra); }
.intervento h3 { font-size:.92rem; font-weight:600; }
.priorita { display:inline-block; min-width:1.5rem; margin-right:.35rem;
            color:var(--muted); font-variant-numeric:tabular-nums; }
.badge { font-size:.7rem; font-weight:700; letter-spacing:.04em;
         border:1px solid currentColor; border-radius:.75rem;
         padding:.05rem .5rem; white-space:nowrap; }
.qw { color:var(--ok); font-weight:600; }
.guadagno { font-size:.83rem; margin:.3rem 0 0;
            font-variant-numeric:tabular-nums; }

/* --- come si aggiusta: i testi di correzione (Fase 3) --- */
.titolo-correzioni { font-size:.72rem; text-transform:uppercase;
                     letter-spacing:.05em; color:var(--muted);
                     margin:.8rem 0 .25rem; }
ul.correzioni { list-style:none; margin:0; padding:0; }
ul.correzioni li { font-size:.88rem; margin:.5rem 0; padding-left:.7rem;
                   border-left:2px solid var(--line); }
.spiegazione { display:block; margin-top:.15rem; font-size:.83rem;
               color:var(--muted); }
.fix { display:block; margin-top:.2rem; font-size:.85rem; }
/* L'etichetta sta nel markup e non qui: `content` non passa dal
   catalogo, e in inglese usciva in italiano (R61). Il commento non
   la nomina apposta: e' il referto stesso, e il presidio cerca quella
   parola in tutta la pagina. */
.fix-eti { color:var(--warn); font-weight:600; }
.ex-nota { display:block; margin:.45rem 0 .15rem; font-size:.72rem;
           text-transform:uppercase; letter-spacing:.05em;
           color:var(--muted); }
pre.ex { margin:.4rem 0 0; padding:.55rem .65rem; background:var(--track);
         border-radius:.35rem; font-size:.78rem; line-height:1.45;
         overflow-x:auto; white-space:pre; }

table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:.5rem .6rem;
        border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:.75rem; text-transform:uppercase; color:var(--muted);
     letter-spacing:.04em; }
td.num { text-align:right; font-variant-numeric:tabular-nums;
         white-space:nowrap; }
.ok{color:var(--ok)} .warn{color:var(--warn)} .bad{color:var(--bad)}
.muted{color:var(--muted)}
.bar { display:inline-block; height:.5rem; border-radius:.25rem;
       background:currentColor; vertical-align:middle; min-width:2px; }
.card { background:var(--card); border:1px solid var(--line);
        border-radius:.6rem; padding:1rem; margin:.6rem 0;
        box-shadow:var(--ombra); }
/* La treemap. Il colore e' la gravita' PEGGIORE dei rilievi che citano
   la pagina; il grigio pallido di serie e' «nessun rilievo la cita»,
   che non e' «nessun problema» — vedi treemap_data. Il colore non e'
   mai solo: il titolo del rettangolo e la tabella lo dicono a parole.
   Il bordo e' il fondo pagina, cosi' i rettangoli si separano anche
   quando due pagine hanno la stessa estensione. Il testo si stampa
   sopra un contorno del fondo per restare leggibile su qualunque
   rettangolo, chiaro o scuro che sia il tema. */
svg.treemap { width:100%; max-width:760px; height:auto; margin:.6rem 0;
              display:block; }
svg.donut { width:100%; max-width:8.5rem; height:auto; }
svg.donut circle.settore { stroke:var(--muted); }
svg.donut circle.settore.con-rilievi { stroke:var(--bad); }
/* Grigio del binario e non verde: «nessun rilievo le cita» non vuol
   dire «a posto» — nessuna area registra quali pagine ha guardato.
   Stessa scelta per cui la treemap lascia neutro cio' che non sa. */
svg.donut circle.settore.non-citate { stroke:var(--track); }
svg.donut circle.settore.scartati { stroke:var(--muted); }
svg.treemap rect { fill:var(--muted); fill-opacity:.2;
                   stroke:var(--bg); stroke-width:2; }
svg.treemap rect.bad { fill:var(--bad); fill-opacity:.55; }
svg.treemap rect.warn { fill:var(--warn); fill-opacity:.55; }
svg.treemap rect.muted { fill:var(--muted); fill-opacity:.5; }
svg.treemap text { font-size:11px; fill:var(--fg); stroke:var(--bg);
                   stroke-width:3; paint-order:stroke;
                   pointer-events:none; }
details > summary { cursor:pointer; color:var(--muted);
                    font-size:.85rem; margin:.4rem 0; }
/* Il grafo dei link. Il colore dice una cosa misurata: la home, le
   pagine raggiunte seguendo i link, e quelle che non lo sono — giallo
   come il secchiello «profondita' ignota», perche' e' un livello che
   non sappiamo e non un livello peggiore. */
svg.grafo { width:100%; max-width:780px; height:auto; margin:.6rem 0;
            display:block; }
svg.grafo marker path { fill:var(--line); }
svg.grafo .grafo-arco { stroke:var(--line); stroke-width:.8; }
svg.grafo .grafo-nodo { fill-opacity:.75; fill:var(--muted);
                        stroke:var(--muted); }
svg.grafo .grafo-nodo.casa { fill:var(--fg); stroke:var(--fg); }
svg.grafo .grafo-nodo.orfana { fill:var(--warn); stroke:var(--warn); }
svg.grafo .grafo-nodo:focus { outline:2px solid var(--fg);
                              outline-offset:2px; }
svg.grafo .grafo-etichetta { font-size:11px; fill:var(--fg);
                             stroke:var(--bg); stroke-width:3;
                             paint-order:stroke; pointer-events:none; }
/* Le due classi che lo script accende. Senza script non compaiono
   mai, e il disegno resta quello di partenza. */
svg.grafo .spento { opacity:.15; }
svg.grafo .grafo-arco.acceso { stroke:var(--fg); stroke-width:1.6; }
.grafo-comandi button { font:inherit; font-size:.8rem; cursor:pointer;
                        color:var(--fg); background:var(--card);
                        border:1px solid var(--line); border-radius:.4rem;
                        padding:.25rem .6rem; }
.grafo-comandi button[aria-pressed="true"] { border-color:var(--fg); }
@media (prefers-reduced-motion: no-preference) {
  svg.grafo .grafo-nodo, svg.grafo .grafo-arco,
  svg.grafo .grafo-etichetta { transition:opacity .15s, cx .3s, cy .3s,
                               x1 .3s, y1 .3s, x2 .3s, y2 .3s,
                               x .3s, y .3s; } }
.disclaimer { font-size:.83rem; color:var(--muted); font-style:italic; }
code { background:var(--track); padding:.1rem .3rem; border-radius:.25rem;
       font-size:.85em; }
.grande { font-size:1.6rem; font-weight:600;
          font-variant-numeric:tabular-nums; }
@media (max-width:40rem){
  .quadrante { width:6.5rem; }
  .quadrante svg { width:4.5rem; height:4.5rem; }
  th,td { padding:.4rem .35rem; font-size:.9rem; }
}
.piede { border-top:1px solid var(--line); margin:2.5rem auto 0;
         padding:1.25rem 1rem 0; max-width:64rem; }
.piede ul { margin:.3rem 0 0; }
.piede li { color:var(--muted); font-size:.83rem; }
/* La stampa. Un referto di consulenza finisce in PDF, e senza queste
   regole ci finiva con i quadranti in bianco e nero, le schede spezzate
   a meta' pagina e i link ridotti a parole sottolineate senza indirizzo.
   La palette NON cambia: e' gia' a contrasto pieno su bianco (U11.1), e
   una seconda palette per la stampa sarebbe una seconda cosa da tenere
   allineata. */
@media print {
  @page { margin:1.5cm; }
  /* I punteggi sono colore E simbolo insieme: senza questa riga i
     browser scartano i fondi in stampa, e i quadranti — che il colore
     ce l'hanno nel riempimento SVG — uscirebbero vuoti. */
  * { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  body { padding:0; font-size:10.5pt; }
  main { max-width:none; padding:0; }
  /* Una scheda spezzata fra due pagine si legge due volte e male. */
  .area, .card, .quadrante, table, figure { break-inside:avoid;
                                            page-break-inside:avoid; }
  h2, h3 { break-after:avoid; page-break-after:avoid; }
  /* Le ancore servono a copiare un link a video: su carta sono
     cancelletti muti. Lo script del grafo non gira in stampa, quindi
     i suoi comandi non hanno nulla da comandare. */
  .ancora, .grafo-comandi, script { display:none; }
  /* Il piano chiedeva anche l'indirizzo dei link esterni stampato via
     `::after`. Non c'e' nulla su cui agirebbe: il referto non contiene
     alcun `href` esterno — invariante presidiato — e i soli `<a>` sono
     le ancore interne, che qui sono nascoste. Una regola che non
     seleziona nulla non si scrive. */
}
"""

# Geometria del quadrante: raggio 56 in un viewBox 120x120.
_RAGGIO = 56
_CIRCONFERENZA = 2 * math.pi * _RAGGIO


def _classe(valore: Optional[float]) -> str:
    if valore is None:
        return "muted"
    return ("ok" if valore >= SOGLIA_BUONO
            else "warn" if valore >= SOGLIA_MEDIO else "bad")


def _quadrante(valore: Optional[float], nome: str, nota: str = "",
               parziale: bool = False,
               lang: str = LINGUA_CANONICA) -> str:
    """Un quadrante circolare, come quelli in testa a un referto Lighthouse.

    E' SVG inline calcolato qui: l'arco si ottiene con stroke-dasharray
    sulla circonferenza, quindi non serve alcuno script — e il referto
    resta un file solo, apribile senza rete (principio del referto
    autoconsistente).

    Un valore assente NON diventa uno zero: si disegna un anello
    tratteggiato con un trattino al centro, perche' "non misurato" e
    "misurato zero" sono cose diverse e il referto le distingue.
    """
    classe = _classe(valore)
    if valore is None:
        arco = ("<circle class='anello-fondo' cx='60' cy='60' r='%d' "
                "fill='none' stroke-width='9' stroke-dasharray='4 6'/>"
                % _RAGGIO)
        testo = ("<text class='valore muted' x='60' y='60' "
                 "text-anchor='middle' dominant-baseline='central' "
                 "fill='currentColor'>—</text>")
    else:
        pieno = _CIRCONFERENZA * max(0.0, min(valore, 100.0)) / 100.0
        arco = ("<circle class='anello-fondo' cx='60' cy='60' r='%d' "
                "fill='none' stroke-width='9'/>" % _RAGGIO)
        if pieno > 0.5:
            # Sotto mezzo pixel l'arco non si disegna: con
            # stroke-linecap arrotondato un valore di zero lascerebbe
            # comunque un puntino colorato, che si legge come "poco"
            # invece che come "niente".
            arco += (
                "<circle cx='60' cy='60' r='%d' fill='none' "
                "stroke='currentColor' stroke-width='9' "
                "stroke-linecap='round' stroke-dasharray='%.2f %.2f' "
                "transform='rotate(-90 60 60)'/>"
                % (_RAGGIO, pieno, _CIRCONFERENZA - pieno))
        testo = ("<text class='valore' x='60' y='60' text-anchor='middle' "
                 "dominant-baseline='central' fill='currentColor'>%.0f</text>"
                 % valore)
    return (
        "<div class='quadrante %s'>"
        "<svg viewBox='0 0 120 120' role='img' aria-label='%s: %s'>%s%s</svg>"
        "<div class='nome'>%s</div>%s</div>"
        # L'aria-label descrive il solo quadrante: la qualifica sta
        # nella nota qui sotto, che e' un fratello nel DOM e viene letta
        # subito dopo. Ripeterla qui la duplicherebbe, e sbagliarla —
        # "superficie" su una scansione soltanto interrotta — sarebbe
        # peggio che ometterla.
        % (classe, _e(nome),
           t("non misurato", lang) if valore is None
           else t("%.0f su 100", lang) % valore,
           arco, testo, _e(nome),
           "<div class='nota%s'>%s</div>"
           % (" parziale" if parziale else "", _e(nota)) if nota else ""))


def _etichetta_area(area: dict, lang: str = LINGUA_CANONICA) -> str:
    """Nome dell'area senza il numero d'ordine: nel quadrante lo spazio
    e' poco e "1. Tecnica" non aggiunge nulla a "Tecnica"."""
    etichetta = area.get("label") or area.get("module") or "?"
    return t(etichetta, lang).split(". ", 1)[-1]


def _stato_area(area: dict, lang: str = LINGUA_CANONICA) -> str:
    return t(STATO_LEGGIBILE.get(area.get("status"), "non misurato"), lang)


def conteggi_per_gravita(referto: dict) -> Dict[str, int]:
    """Quanti rilievi per gravita', in tutto il referto.

    **Esclude i derivati** (R41): i rilievi di `mars_citability`
    ridicono difetti che le aree d'origine hanno gia' misurato, e
    contarli qui riaprirebbe sui CONTEGGI il doppio conteggio che D3
    chiude sul punteggio — sette `unmeasured` e i `weak` gonfierebbero
    la casella «Info» accanto ai rilievi che ripetono.

    Non basterebbe filtrare per gravita': oggi quei rilievi sono tutti
    `info`, ma e' una protezione incidentale, e il giorno che uno
    nascesse `warning` il conteggio si gonfierebbe in silenzio.

    I rilievi di stato restano dentro: dicono qualcosa di vero su
    questa esecuzione, e la casella «Info» non e' una coda di lavoro —
    quella e' il piano, che li esclude.
    """
    conteggi: Dict[str, int] = {}
    for area in referto.get("areas") or []:
        for rilievo in area.get("findings") or []:
            if (rilievo.get("params") or {}).get("derived"):
                continue
            gravita = str(rilievo.get("severity") or "")
            conteggi[gravita] = conteggi.get(gravita, 0) + 1
    return conteggi


# Le tre caselle, nell'ordine in cui si leggono. `SEV_OK` non c'e'
# perche' nessun modulo lo emette: il giorno che qualcuno lo facesse,
# un test lo direbbe invece di lasciarlo sparire da qui.
TESSERE_GRAVITA = ((SEV_CRITICAL, "critici", "bad"),
                   (SEV_WARNING, "avvertenze", "warn"),
                   (SEV_INFO, "informativi", "muted"))


def _hero(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """Il riquadro in testa: un numero, un verdetto, quattro caselle.

    Il quadrante e' lo STESSO `_quadrante` della fascia sotto, solo
    piu' grande per CSS: disegnarne un secondo, anche identico,
    vorrebbe dire avere due archi da tenere allineati.

    La riga delle soglie e' obbligatoria quanto il numero. Un 66 senza
    la scala e' un voto di cui non si conosce il metro, e questo
    referto la scala la dichiara gia' nella legenda dei quadranti: qui
    si ripete perche' l'hero puo' essere l'unica cosa che qualcuno
    legge.
    """
    complessivo = referto.get("overall")
    if not complessivo:
        return ""
    conteggi = conteggi_per_gravita(referto)
    voto = complessivo["score"]

    caselle = []
    for gravita, etichetta, classe in TESSERE_GRAVITA:
        caselle.append("<div class='tessera'><span class='grande %s'>%d"
                       "</span><span class='meta'>%s</span></div>"
                       % (classe, conteggi.get(gravita, 0),
                          t(etichetta, lang)))
    caselle.append(_donut_pagine(referto, lang))

    return (
        "<section class='hero'>"
        "<div class='hero-voto'>%s"
        "<p class='verdetto %s'>%s</p>"
        "<p class='meta'>%s</p>"
        "<p class='meta'>%s</p></div>"
        "<div class='tessere'>%s</div></section>"
        % (_quadrante(voto, t("Complessivo", lang), lang=lang),
           _classe(voto), _verdetto(voto, lang),
           t("media pesata di %d misure · escluse %s", lang)
           % (len(complessivo["components"]),
              aree_escluse_leggibili(referto, lang)),
           t("scala dichiarata: critico sotto %d · da migliorare "
             "%d-%d · buono da %d", lang)
           % (SOGLIA_MEDIO, SOGLIA_MEDIO, SOGLIA_BUONO - 1, SOGLIA_BUONO),
           "".join(caselle)))


# I tre settori del donut delle pagine, nell'ordine in cui si leggono.
# I nomi NON sono «senza rilievi / con rilievi / scartate» come il piano
# prevedeva: portano il caveat dentro il disegno — vedi
# `ripartizione_pagine()` per il perche'. «nessun rilievo le cita» e' la
# stessa frase che usa la treemap: una sola voce per un solo concetto.
SETTORI_PAGINE = (
    ("con_rilievi", "con rilievi", "con-rilievi"),
    ("non_citate", "nessun rilievo le cita", "non-citate"),
    ("scartati", "URL scartati", "scartati"),
)


def _donut_pagine(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """L'anello degli URL incontrati, in tre settori.

    Stessa tecnica dei quadranti — `stroke-dasharray` su una
    circonferenza, nessuno script — quindi il referto resta un file
    solo. Gli archi si concatenano tenendo l'offset di quello prima.

    Con zero URL non si disegna nulla: un anello vuoto si leggerebbe
    come una ripartizione, e non c'e' niente da ripartire.
    """
    quote = ripartizione_pagine(referto)
    totale = sum(quote.values())
    if not totale:
        return ""

    archi, voci, scorso = [], [], 0.0
    for chiave, etichetta, classe in SETTORI_PAGINE:
        quanti = quote[chiave]
        voci.append("<span class='meta'><b>%d</b> %s</span>"
                    % (quanti, t(etichetta, lang)))
        if not quanti:
            continue
        pieno = _CIRCONFERENZA * quanti / totale
        archi.append(
            "<circle class='settore %s' cx='60' cy='60' r='%d' fill='none' "
            "stroke-width='9' stroke-dasharray='%.2f %.2f' "
            "stroke-dashoffset='%.2f' transform='rotate(-90 60 60)'/>"
            % (classe, _RAGGIO, pieno, _CIRCONFERENZA - pieno, -scorso))
        scorso += pieno

    return ("<div class='tessera'>"
            "<svg class='donut' viewBox='0 0 120 120' role='img' "
            "aria-label='%s'>%s"
            "<text class='valore' x='60' y='60' text-anchor='middle' "
            "dominant-baseline='central' fill='currentColor'>%d</text>"
            "</svg><span class='meta'>%s</span>%s</div>"
            % (_e(t("URL incontrati: %d", lang) % totale),
               "".join(archi), totale, t("URL incontrati", lang),
               "".join(voci)))


# Quanti rilievi mostra il riquadro in testa. Cinque, come ogni altra
# vista compatta del referto.
PRIMI_RILIEVI = 5


def _primi_rilievi(referto: dict, ancore: Dict[str, str],
                   lang: str = LINGUA_CANONICA) -> str:
    """I primi interventi del piano, in testa e cliccabili.

    E' la scorciatoia per chi apre il referto e vuole sapere subito da
    dove cominciare, senza scorrere fino al piano. Legge la lista
    canonica — nessun secondo ordinamento — e mostra le prime cinque
    voci nell'ordine che il piano ha gia' deciso.

    Ogni voce e' un link solo se la sua ancora esiste: dove il rilievo
    non ha ne' `fix` ne' `example` la scheda d'area non emette alcun
    id, e un link a vuoto sarebbe peggio di nessun link.
    """
    piano = referto.get("remediation") or []
    if not piano:
        return ""
    voci = []
    for voce in piano[:PRIMI_RILIEVI]:
        ancora = ancore.get(voce.get("key") or "")
        titolo = _e(finding_texts(voce, lang)["title"])
        voci.append("<li class='%s'>%s</li>"
                    % (_BADGE_GRAVITA.get(voce["severity"], ("muted", ""))[0],
                       "<a href='#%s'>%s</a>" % (ancora, titolo)
                       if ancora else titolo))
    return ("<div class='primi'><p class='meta'>%s</p>"
            "<ol class='primi-rilievi'>%s</ol></div>"
            % (t("Da dove cominciare", lang), "".join(voci)))


def _fascia_quadranti(referto: dict,
                      lang: str = LINGUA_CANONICA) -> str:
    """La fascia in testa, come in Lighthouse: un quadrante per area.

    Le aree lessicale e semantica non producono un voto ma una
    classifica, e mettere loro uno zero sarebbe una bugia: al loro
    posto la fascia mostra i due segnali DERIVATI che C1 gia' calcola —
    consenso RRF e contenuto in forma di risposta — dichiarati come
    tali nella riga sotto il quadrante.
    """
    pezzi = []
    for area in referto["areas"]:
        if area["score"] is None:
            nota, parziale = _stato_area(area, lang), False
        else:
            # Sotto il quadrante lo spazio e' poco: strumento, e la
            # parola che cambia il senso del numero. Un 100 verde
            # ottenuto guardando tre header non deve poter passare
            # per un WAPT completo.
            breve = [area["tool"]] if area.get("tool") else []
            parziale = (area.get("status") == "surface"
                        or area.get("complete") is False)
            if area.get("status") == "surface":
                breve.append(t("superficie", lang))
            if area.get("complete") is False:
                breve.append(t("parziale", lang))
            nota = " · ".join(breve)
        pezzi.append(_quadrante(area["score"], _etichetta_area(area, lang),
                                nota, parziale, lang))

    for segnale in segnali_derivati(referto, lang):
        pezzi.append(_quadrante(segnale["value"], t(segnale["name"], lang),
                                str(segnale["note"]), lang=lang))
    if not pezzi:
        return ""
    return "<div class='quadranti'>%s</div>" % "".join(pezzi)


def _legenda(lang: str = LINGUA_CANONICA) -> str:
    """La scala e' una convenzione: dichiararla evita che il colore
    venga letto come una misura."""
    return (
        "<div class='legenda'>"
        "<span><i class='pallino bad'></i>0-49</span>"
        "<span><i class='pallino warn'></i>50-89</span>"
        "<span><i class='pallino ok'></i>90-100</span>"
        "<span><i class='pallino vuoto'></i>%s</span>"
        "</div>" % t("non misurato", lang) +
        "<style>.pallino.bad{background:var(--bad)}"
        ".pallino.warn{background:var(--warn)}"
        ".pallino.ok{background:var(--ok)}</style>")


def _ancora(chiave: str) -> str:
    """L'id stabile di un rilievo, dalla sua chiave.

    UPGRADE.md prevedeva uno slug ricavato dal TITOLO, coi numeri
    normalizzati a `n` perche' «2/3 pagine senza canonical» e «1/3
    pagine senza canonical» non producessero due ancore diverse. Qui
    non serve: dalla Fase 1 ogni rilievo ha gia' una `key` stabile per
    costruzione — tre segmenti, mai un valore variabile dentro — ed e'
    esattamente il problema che quello slug cercava di risolvere a
    valle. Il riferimento non aveva chiavi, noi si.

    Il punto diventa trattino: un id con i punti e' legale in HTML5,
    ma `#tech.robots.ai_blocked` in un selettore CSS si legge come un
    id piu' due classi. Oggi nessuno lo interroga — nel referto non c'e'
    JavaScript — e proprio per questo conviene non lasciare la mina.
    """
    pulita = re.sub(r"[^a-z0-9]+", "-", (chiave or "").lower()).strip("-")
    return "r-%s" % pulita if pulita else ""


def ancore_dei_rilievi(referto: dict) -> Dict[str, str]:
    """chiave -> ancora, per i soli rilievi che una scheda d'area rende.

    Calcolata **una volta** e passata a chi la usa — le schede, il
    piano, il riquadro dei primi rilievi — invece di ricalcolare la
    condizione in tre posti. Un link a un'ancora che nessuno emette e'
    un link rotto, e nessun test sul contenuto lo vedrebbe: la pagina
    resterebbe valida e il salto non succederebbe.

    Riceve l'ancora chi la scheda d'area mostra come elemento proprio:
    un rilievo del blocco «Come si aggiusta», o una voce dell'elenco
    dei controlli agganciata al suo rilievo.
    """
    ancore: Dict[str, str] = {}
    for area in referto.get("areas") or []:
        rilievi = area.get("findings") or []
        if area.get("audits"):
            regole = {r["params"]["rule"] for r in rilievi
                      if isinstance(r.get("params"), dict)
                      and r["params"].get("rule")}
            for rilievo in rilievi:
                regola = (rilievo.get("params") or {}).get("rule")
                if regola in regole and any(c.get("id") == regola
                                            for c in area["audits"]):
                    ancore[rilievo["key"]] = _ancora(rilievo["key"])
            continue
        for rilievo in rilievi:
            if rilievo.get("fix") or rilievo.get("example"):
                ancore[rilievo["key"]] = _ancora(rilievo["key"])
    return {k: v for k, v in ancore.items() if k and v}


def _permalink(ancora: str, lang: str = LINGUA_CANONICA) -> str:
    """Il cancelletto che rende citabile un rilievo."""
    return ("<a class='ancora' href='#%s' aria-label='%s'>#</a>"
            % (ancora, t("Link a questo rilievo", lang)))


def _elenco_controlli(controlli: List[dict],
                      rilievi: Optional[List[dict]] = None,
                      ancore: Optional[Dict[str, str]] = None,
                      lang: str = LINGUA_CANONICA) -> str:
    """I singoli controlli, nell'ordine in cui Lighthouse li mostra.

    Prima i falliti — sono quelli su cui si interviene — poi quelli da
    verificare a mano, infine i superati. Elencare anche i superati non
    e' ridondanza: senza, non si sa CHE COSA sia stato guardato, e un
    punteggio pieno resta indistinguibile da un controllo che non e'
    stato eseguito affatto.

    I testi del rilievo — la `description` di Lighthouse, che U3.2 ha
    messo in `detail` — si agganciano al controllo tramite
    `params["rule"]`, che e' l'id dell'audit. E' una CHIAVE, non una
    somiglianza fra stringhe: e' l'unico posto del referto dove i due
    elenchi si possono unire senza indovinare, ed e' il motivo per cui
    qui la spiegazione sta sotto la voce e altrove ha un blocco suo.
    """
    def chiave(c: dict) -> int:
        if c.get("manual"):
            return 1
        return 0 if not c.get("passed") else 2

    per_regola = {r["params"]["rule"]: r for r in (rilievi or [])
                  if isinstance(r.get("params"), dict)
                  and r["params"].get("rule")}
    righe = []
    for c in sorted(controlli, key=chiave):
        if c.get("manual"):
            classe, segno = "manuale", "?"
        elif c.get("passed"):
            # NON "ok": e' gia' una classe globale del CSS e
            # colorerebbe di verde l'intera riga invece del solo segno.
            classe, segno = "superato", "\u2713"
        else:
            classe, segno = "fallito", "\u2717"
        # Che cosa Lighthouse ha da dire su QUESTO controllo, nei tre
        # campi che R53 ha portato nel dato: il riassunto quantificato,
        # la ragione dell'esito, gli elementi incriminati, gli avvisi.
        # Nell'ordine in cui servono a chi legge — prima quanto, poi
        # perche', infine dove.
        #
        # `warnings` e' l'unico che compare anche su un controllo
        # SUPERATO — `is-crawlable` passa se almeno un bot e' ammesso e
        # avverte quali sono bloccati — ed e' la ragione per cui questi
        # testi stanno nella voce e non solo nel rilievo: un superato
        # un rilievo non lo produce.
        dettaglio = " — ".join(
            [p for p in (c.get("displayValue"), c.get("explanation")) if p]
            + [", ".join(c.get("items") or [])] * bool(c.get("items"))
            + list(c.get("warnings") or []))
        rilievo = per_regola.get(c.get("id")) or {}
        ancora = (ancore or {}).get(rilievo.get("key") or "")
        righe.append(
            "<li%s class='%s'><span class='segno'>%s</span>"
            "<span>%s%s%s%s</span></li>"
            % (" id='%s'" % ancora if ancora else "",
               classe, segno, _e(c.get("title")),
               _permalink(ancora, lang) if ancora else "",
               "<br><span class='dettaglio'>%s</span>" % _e(dettaglio)
               if dettaglio else "",
               # Nessun <br>: `.spiegazione` e' gia' display:block,
               # e il <br> aggiungerebbe una riga vuota.
               "<span class='spiegazione'>%s</span>"
               % _e(finding_texts(rilievo, lang)["detail"])
               if rilievo.get("detail") else ""))
    return "<ul class='controlli'>%s</ul>" % "".join(righe)


def _correzioni(findings: List[dict],
                ancore: Optional[Dict[str, str]] = None,
                lang: str = LINGUA_CANONICA) -> str:
    """Il blocco «Come si aggiusta», dai rilievi che hanno qualcosa da dire.

    Sta SOTTO l'elenco dei rilievi invece che dentro, e ne ripete i
    titoli. La ripetizione e' il prezzo di una scelta, non una
    distrazione: le `issues` sono la vista compatta che ogni modulo
    compone per se', e portano cose che il rilievo tiene nei params —
    «(2 elementi su 1 pagine)», «[1.1.1]», l'URL del blocco JSON-LD
    malformato. Toglierle per mettere al loro posto i `findings`
    perderebbe quelle informazioni; ricostruirle qui dai params
    significherebbe riscrivere nel referto la presentazione che sta nei
    moduli, cioe' la solita coppia di implementazioni che divergono in
    silenzio.

    E unire i due elenchi non si puo': **non esiste una chiave**. Per
    posizione si disallineano appena axe o ZAP superano le cinque
    regole, perche' le issues si fermano a cinque e i rilievi no; per
    somiglianza del testo fallisce mars_schema, dove la issue dice
    «JSON-LD malformato su <url>» e il titolo «1 blocchi JSON-LD
    malformati». L'unica area con una chiave vera e' mars_seo, che
    infatti la spiegazione ce l'ha in linea.
    """
    # Serve un `fix` o un `example`: il blocco si intitola «Come si
    # aggiusta», e un rilievo che ha solo `detail` non aggiusta nulla.
    # Sono due i casi, e vanno tenuti fuori tutt'e due: l'area in
    # ERRORE, il cui detail e' il messaggio dell'eccezione, e
    # `wcag.status.no_fixes`, che dice dove manca il locale di axe —
    # istruzioni per chi fa girare MARS, non per chi possiede il sito,
    # cioe' la stessa esclusione che regge il catalogo di U3.1.
    voci = [f for f in findings if f.get("fix") or f.get("example")]
    if not voci:
        return ""
    righe = []
    for f in voci:
        ancora = (ancore or {}).get(f.get("key") or "")
        testi = finding_texts(f, lang)
        pezzi = ["<b>%s</b>%s" % (_e(testi["title"]),
                                  _permalink(ancora, lang) if ancora else "")]
        # `source_severity` NON si stampa: dove c'e' — "[critico]",
        # "[axe:critical]", "[ZAP:High]" — sta gia' nella riga della
        # vista compatta, due centimetri piu' su.
        if f.get("detail"):
            pezzi.append("<span class='spiegazione'>%s</span>"
                         % _e(testi["detail"]))
        if f.get("fix"):
            # L'etichetta viaggia col testo, e con lo stesso letterale
            # che usa il Markdown: era un `content` nel CSS, che nessun
            # catalogo puo' tradurre (R61).
            pezzi.append("<span class='fix'><span class='fix-eti'>%s</span> "
                         "%s</span>"
                         % (_e(t("Correzione:", lang)), _e(testi["fix"])))
        # L'esempio e' codice: <pre> perche' gli a-capo e
        # l'indentazione di un blocco nginx o JSON-LD sono il suo
        # contenuto, non la sua impaginazione.
        #
        # E porta la sua didascalia, sempre (R60): un blocco nginx si
        # riconosce da solo, un esempio scritto in prosa italiana
        # plausibile no — e `sem.answer_shaped.low` deve mostrare
        # proprio quello, perche' il rilievo parla della forma della
        # prosa. Senza etichetta il lettore di un referto vero l'ha
        # letto come contenuto di un altro sito finito nel suo.
        if f.get("example"):
            # Il letterale e non una costante condivisa col Markdown:
            # `test_ogni_letterale_della_cornice_e_a_catalogo` legge
            # l'AST e indicizza sul testo italiano, quindi un nome
            # scollegherebbe la traduzione senza rompere nulla — che e'
            # esattamente il difetto che quel presidio esiste per
            # impedire.
            pezzi.append(
                "<span class='ex-nota'>%s</span>"
                % _e(t("Esempio — non è contenuto del tuo sito", lang)))
            pezzi.append("<pre class='ex'>%s</pre>" % _e(testi["example"]))
        righe.append("<li%s>%s</li>"
                     % (" id='%s'" % ancora if ancora else "",
                        "".join(pezzi)))
    return ("<p class='titolo-correzioni'>%s</p>"
            "<ul class='correzioni'>%s</ul>"
            % (t("Come si aggiusta", lang), "".join(righe)))


def _scheda_area(area: dict, referto: dict,
                 ancore: Optional[Dict[str, str]] = None,
                 lang: str = LINGUA_CANONICA) -> str:
    """Una scheda per area, con i rilievi sotto — come le categorie di
    Lighthouse elencano i propri audit."""
    if area["score"] is None:
        voto = "<span class='muted'>%s</span>" % _stato_area(area, lang)
    else:
        voto = ("<span class='%s'>%.0f<span class='muted'>/100</span></span>"
                % (_classe(area["score"]), area["score"]))

    corpo = []
    # I paragrafi descrittivi valgono solo se la classifica c'e'
    # davvero: su un'area in errore "Passaggio in testa: —" descrive
    # un risultato inesistente. La condizione guarda lo STATO, non il
    # nome del modulo — che e' il difetto da cui nasceva "Analizzato".
    ordina = area.get("status") == "ranking"
    if ordina and area["module"] == "mars_lexical":
        # Il paragrafo descrittivo resta; il VERDETTO no. Prima
        # veniva sovrascritto con "classifica" anche quando l'area era
        # in errore, nascondendo il fallimento dietro un'etichetta
        # normale. Ora lo stato arriva dal dato, come per le altre.
        corpo.append("<p class='strumento'>%s <code>%s</code></p>"
                     % (t("Passaggio in testa:", lang),
                        _e((referto.get("lexical") or {}).get("top_chunk")
                           or "—")))
    elif ordina and area["module"] == "mars_semantic":
        sem = referto.get("semantic") or {}
        corpo.append("<p class='strumento'>%s</p>"
                     % (t("%.0f%% di %s chunk in forma di risposta.", lang)
                        % (100 * (sem.get("answer_shaped_ratio") or 0),
                           sem.get("n_chunks") or 0)))
        # Segnali di PAGINA, tenuti fuori dal rapporto ma non nascosti:
        # dicono qualcosa di vero sul sito (vedi R19).
        for nome, quante in (sem.get("page_signals") or {}).items():
            corpo.append("<p class='strumento'>%s</p>"
                         % (t("%s: %d pagine su %d.", lang)
                            % (_e(t(nome, lang)), quante,
                               referto["pages_crawled"])))

    qualifiche = _qualificatori(area, lang)
    if qualifiche:
        # Marcato quando il punteggio non e' una misura piena: e' la
        # differenza fra "sicuro" e "non abbiamo guardato a fondo".
        parziale = (area.get("status") == "surface"
                    or area.get("complete") is False)
        corpo.append("<p class='strumento%s'>%s</p>"
                     % (" parziale" if parziale else "",
                        _e(" · ".join(qualifiche))))
    rilievi = area.get("findings") or []
    if area.get("audits"):
        # L'elenco dei controlli sostituisce quello dei rilievi: li
        # contiene gia' tutti, e in piu' dice che cosa e' stato
        # guardato e superato — che e' l'informazione che mancava.
        corpo.append(_elenco_controlli(area["audits"], rilievi, ancore,
                                       lang))
    else:
        compatte = _righe_compatte(area, lang)
        if compatte:
            corpo.append("<ul class='rilievi'>%s</ul>"
                         % "".join("<li>%s</li>" % _e(i) for i in compatte))
        corpo.append(_correzioni(rilievi, ancore, lang))
        # "Nessun rilievo." vale solo quando l'area non ha NE' issues
        # NE' findings. Guardare i soli findings direbbe che il
        # giudizio LLM riuscito non ha rilevato nulla — ne elenca tre,
        # e findings non ne produce per scelta di U1.9 — e guardare le
        # sole issues farebbe lo stesso con un'area che avesse solo
        # rilievi strutturati.
        if not area["issues"] and not rilievi and area["score"] is not None:
            corpo.append("<p class='nessun-rilievo'>%s</p>"
                         % t("Nessun rilievo.", lang))

    return ("<div class='area'><div class='riga'><h3>%s</h3>"
            "<span class='punteggio'>%s</span></div>%s</div>"
            % (_e(t(area["label"], lang)), voto, "".join(corpo)))


_BADGE_GRAVITA = {SEV_CRITICAL: ("bad", "CRITICO"),
                  SEV_WARNING: ("warn", "AVVERTENZA")}


def _voce_piano_html(voce: dict, ancore: Optional[Dict[str, str]] = None,
                     lang: str = LINGUA_CANONICA) -> str:
    """Un intervento come scheda.

    Porta cio' che la scheda d'area non ha — priorita', sforzo,
    recupero, guadagno d'indice — e ripete il `fix`, che invece la
    scheda ce l'ha. La ripetizione qui e' voluta, mentre nella vista
    testo e' stata tolta: la' il referto e' largo 55 colonne e il
    lettore aveva le due righe sott'occhio insieme, qui sono due
    sezioni di un documento lungo, e un intervento che non dicesse che
    cosa fare manderebbe a cercarlo — senza nemmeno un'ancora, che
    arriva con la Fase 5.

    L'`example` invece resta alla scheda d'area, e non e' una
    dimenticanza: sedici blocchi di codice dentro un elenco di
    priorita' lo renderebbero illeggibile proprio come elenco.
    """
    classe, etichetta = _BADGE_GRAVITA.get(voce["severity"], ("muted", "?"))
    etichetta = t(etichetta, lang)
    testi = finding_texts(voce, lang)
    ancora = (ancore or {}).get(voce.get("key") or "")
    # Il titolo diventa un link SOLO se l'ancora esiste davvero: un
    # href verso un id che nessuno emette e' un salto che non succede,
    # e la pagina resta valida — cioe' un difetto invisibile.
    titolo = ("<a href='#%s'>%s</a>" % (ancora, _e(testi["title"]))
              if ancora else _e(testi["title"]))
    parti = ["<div class='intervento'><div class='riga'>",
             "<h3><span class='priorita'>%d</span> %s</h3>"
             % (voce["priority"], titolo),
             "<span class='badge %s'>%s</span></div>" % (classe, etichetta)]

    contesto = [_e(t(voce["area_label"], lang).split(". ", 1)[-1])]
    contesto.append(t("sforzo: %s", lang)
                    % _e(t(voce["effort"], lang) if voce["effort"]
                         else t("non dichiarato", lang)))
    if voce["quick_win"]:
        contesto.append("<span class='qw'>%s</span>"
                        % t("QUICK WIN", lang))
    parti.append("<p class='meta'>%s</p>" % " · ".join(contesto))

    if voce["recovery"]:
        numeri = [t("+%d punti d'area (%d → %d)", lang)
                  % (voce["recovery"], voce["score_before"],
                     voce["score_after"])]
        if voce["index_gain"]:
            # Il mercato viaggia col numero: i coefficienti si
            # rinormalizzano sui segnali misurati, quindi lo stesso
            # rilievo vale diversamente in due esecuzioni diverse.
            numeri.append(
                t("indice di citabilità +%.2f (mercato %s, stima)", lang)
                % (voce["index_gain"], _e(voce["market"] or "?")))
        parti.append("<p class='guadagno'>%s</p>" % " · ".join(numeri))
    else:
        # Mai un silenzio al posto di un numero: la corsia dice perche'.
        parti.append("<p class='meta'>%s</p>"
                     % _e(t(voce["lane_reason"], lang)
                          if voce["lane_reason"]
                          else t("recupero non dichiarato", lang)))

    if testi["fix"]:
        # Stessa etichetta della scheda d'area, e per la stessa ragione
        # (R61): il piano usa la classe `fix`, quindi prendeva il suo
        # «Correzione: » dal `content` del CSS — cioe' in italiano
        # dentro un referto inglese.
        parti.append("<span class='fix'><span class='fix-eti'>%s</span> "
                     "%s</span>"
                     % (_e(t("Correzione:", lang)), _e(testi["fix"])))
    parti.append("</div>")
    return "".join(parti)


# Sotto queste misure l'etichetta non ci sta e uscirebbe dal
# rettangolo, sovrapposta a quella accanto. Il `<title>` e la tabella
# di ripiego dicono comunque tutto: e' l'etichetta a essere un di piu',
# non il dato.
TREEMAP_MIN_W = 90.0
TREEMAP_MIN_H = 26.0


# Gravita' peggiore di una pagina -> (classe CSS, parola). Non e'
# `_BADGE_GRAVITA`, che di proposito non ha `info`: li' un rilievo
# informativo non merita un'etichetta accanto al titolo, qui invece la
# casella e' colorata comunque e tacere che cosa sia il colore
# lascerebbe indovinare. Non e' nemmeno `TESSERE_GRAVITA`, le cui
# etichette sono plurali che contano ("3 critici").
TREEMAP_GRAVITA = {SEV_CRITICAL: ("bad", "rilievo critico"),
                   SEV_WARNING: ("warn", "avvertenza"),
                   SEV_INFO: ("muted", "rilievo informativo")}


def _rilievi_della_pagina(voce: dict, lang: str = LINGUA_CANONICA) -> str:
    """Che cosa dice il colore di un rettangolo, a parole.

    Esiste perche' il colore non basta: e' l'invariante che il referto
    tiene dovunque (il simbolo accompagna sempre il colore), e qui vale
    doppio, perche' il grigio non e' un giudizio lieve — e' l'assenza
    di un giudizio.
    """
    if not voce["severity"]:
        return t("nessun rilievo la cita", lang)
    _, parola = TREEMAP_GRAVITA[str(voce["severity"])]
    quanti = int(voce["findings"])
    if quanti > 1:
        return t("%d rilievi, il peggiore: %s", lang) % (quanti,
                                                         t(parola, lang))
    return t(parola, lang)


def _treemap_html(referto: dict, p: List[str],
                  lang: str = LINGUA_CANONICA) -> None:
    """La treemap della superficie: SVG statico, e la sua tabella.

    L'SVG e' **una sola immagine** per chi usa un lettore di schermo
    (`role="img"` con la sua etichetta), e i `<title>` per rettangolo
    servono il passaggio del mouse. La lettura accessibile e' la
    tabella in `<details>`, che porta gli stessi numeri: e' per questo
    che i rettangoli **non** sono focalizzabili: quaranta fermate di
    tabulazione che al fuoco non mostrano nulla — senza JavaScript il
    `<title>` non compare — sarebbero un ostacolo travestito da
    accessibilita'.
    """
    mappa = treemap_data(referto.get("pages") or [],
                         gravita=gravita_per_pagina(referto))
    if not mappa:
        return
    voci = mappa["items"]
    note = [t("Ogni rettangolo è una pagina, l'area è proporzionale alle "
              "parole recuperabili.", lang)]
    con_testo = int(mappa["total"]) - int(mappa["empty"])
    if mappa["shown"] < con_testo:
        note.append(t("Le %d più estese di %s.", lang)
                    % (mappa["shown"],
                       _plurale(con_testo, "pagina", "pagine", lang)))
    if mappa["empty"]:
        note.append(t("%s senza testo indicizzabile non %s superficie da "
                      "disegnare.", lang)
                    % (_plurale(int(mappa["empty"]), "pagina", "pagine",
                                lang),
                       t("ha" if mappa["empty"] == 1 else "hanno", lang)))
    # Che cosa sia il colore va detto, e va detto soprattutto che cosa
    # NON sia il grigio: una pagina che nessun rilievo cita puo' essere
    # pulita come puo' non essere stata guardata — Lighthouse ne misura
    # una sola, axe le prime del campione. Leggerlo come «tutto a
    # posto» e' la confusione che il referto evita ovunque.
    citate = sum(1 for v in voci if v["severity"])
    note.append(t("Il colore è la gravità peggiore dei rilievi che citano "
                  "la pagina.", lang))
    if citate < len(voci):
        note.append(t("%s in grigio: nessun rilievo le cita, che non vuol "
                      "dire che siano a posto — non tutte le aree guardano "
                      "tutte le pagine.", lang)
                    % _plurale(len(voci) - citate, "pagina", "pagine", lang))
    p.append("<p class='meta'>%s</p>" % _e(" ".join(note)))
    p.append("<svg class='treemap' viewBox='0 0 %d %d' role='img' "
             "aria-label='%s'>"
             % (int(mappa["width"]), int(mappa["height"]),
                t("Treemap della superficie: %s, la più estesa è %s con "
                  "%s. I dati sono nella tabella qui sotto.", lang)
                % (_plurale(int(mappa["shown"]), "pagina", "pagine", lang),
                   _e(voci[0]["label"]),
                   _plurale(int(voci[0]["words"]), "parola", "parole",
                            lang))))
    for voce in voci:
        classe, _ = TREEMAP_GRAVITA.get(str(voce["severity"]), ("", ""))
        p.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f'%s>"
                 # Il colore non viaggia mai da solo: al passaggio del
                 # mouse il titolo dice a parole che cosa significa, e
                 # la tabella qui sotto lo dice a chi il mouse non lo
                 # usa.
                 "<title>%s — %s, %s, %s</title></rect>"
                 % (voce["x"], voce["y"], voce["w"], voce["h"],
                    " class='%s'" % classe if classe else "",
                    _e(voce["label"]),
                    _plurale(int(voce["words"]), "parola", "parole", lang),
                    _plurale(int(voce["chunks"]), "passaggio", "passaggi",
                             lang),
                    _e(_rilievi_della_pagina(voce, lang))))
        if voce["w"] >= TREEMAP_MIN_W and voce["h"] >= TREEMAP_MIN_H:
            p.append("<text x='%.1f' y='%.1f'>%s</text>"
                     % (voce["x"] + 6, voce["y"] + 17,
                        _e(_coda(str(voce["label"]),
                                 int((voce["w"] - 12) // 6)))))
    p.append("</svg>")
    p.append("<details><summary>%s</summary>"
             "<table><thead><tr><th scope='col'>%s</th>"
             "<th scope='col'>%s</th><th scope='col'>%s</th>"
             "<th scope='col'>%s</th></tr></thead>"
             % (t("La superficie in tabella", lang), t("Pagina", lang),
                t("Parole", lang), t("Passaggi", lang),
                t("Rilievi", lang)))
    for voce in voci:
        p.append("<tr><td>%s</td><td class='num'>%d</td>"
                 "<td class='num'>%d</td><td>%s</td></tr>"
                 % (_e(voce["url"]), voce["words"], voce["chunks"],
                    _e(_rilievi_della_pagina(voce, lang))))
    p.append("</table></details>")


# Oltre questo numero di nodi si etichettano solo i piu' linkati:
# sessanta etichette sovrapposte non si leggono, e l'etichetta di un
# nodo periferico vale meno di quella dell'hub accanto.
GRAFO_ETICHETTA_TUTTI = 20
GRAFO_ETICHETTA_QUANTI = 12


def _grafo_html(referto: dict, p: List[str],
                lang: str = LINGUA_CANONICA) -> None:
    """Il grafo dei link interni: SVG statico, e i comandi che il JS accende.

    Il disegno **e' completo senza JavaScript**: nodi, archi, frecce,
    etichette e titoli sono nell'HTML, posizionati dal layout a forze
    calcolato in Python. Lo script aggiunge la lettura — evidenziare
    un nodo, disporre per distanza, ingrandire — e per questo i
    comandi nascono `hidden`: un bottone che non fa nulla e' peggio di
    un bottone assente, perche' promette qualcosa.

    Per la stessa ragione i nodi **non** hanno `tabindex` nell'HTML:
    glielo mette lo script, che al fuoco ha qualcosa da mostrare. E'
    la stessa scelta della treemap, applicata al contrario — li' il JS
    non c'e' e le fermate non si creano mai.
    """
    grafo = link_graph_data(referto.get("pages") or [],
                            str(referto.get("url") or ""))
    if not grafo:
        return
    nodi = grafo["nodes"]
    p.append("<h3>%s</h3>" % t("Architettura dei link", lang))
    note = [t("%s e %s fra le pagine scansionate.", lang)
            % (_plurale(int(grafo["shown"]), "nodo", "nodi", lang),
               _plurale(int(grafo["edges"]), "collegamento",
                        "collegamenti", lang))]
    if grafo["shown"] < grafo["total"]:
        note.append(t("I %d più linkati di %d.", lang)
                    % (grafo["shown"], grafo["total"]))
    if not grafo["has_home"]:
        note.append(t("L'URL di partenza non è fra le pagine scansionate, "
                      "quindi «raggiungibile» qui non vuol dire nulla.",
                      lang))
    elif grafo["orphans"]:
        note.append(t("%s non si raggiunge dalla home seguendo i link.",
                      lang)
                    % _plurale(int(grafo["orphans"]), "pagina", "pagine",
                               lang))
    # La riserva che rende onesto il giallo: dentro un campione di
    # dieci pagine «orfana» puo' voler dire solo che chi la linka non
    # e' stato scaricato. Quando invece nessun link esce dal campione
    # il conto e' chiuso, e lo si puo' dire senza riserve.
    if not grafo["closed"]:
        note.append(t("Il campione è parziale: una pagina può risultare "
                      "orfana solo perché chi la linka non è stato "
                      "scansionato.", lang))
    p.append("<p class='meta'>%s</p>" % _e(" ".join(note)))
    p.append("<svg id='grafo' class='grafo' viewBox='0 0 %d %d' role='img' "
             "aria-label='%s'>"
             % (int(grafo["width"]), int(grafo["height"]),
                t("Grafo dei link interni: %s e %s. I dati sono nella "
                  "tabella qui sotto.", lang)
                % (_plurale(int(grafo["shown"]), "nodo", "nodi", lang),
                   _plurale(int(grafo["edges"]), "collegamento",
                            "collegamenti", lang))))
    p.append("<defs><marker id='grafo-freccia' viewBox='0 0 8 8' refX='7' "
             "refY='4' markerWidth='5' markerHeight='5' "
             "orient='auto-start-reverse'>"
             "<path d='M0 0L8 4L0 8z'/></marker></defs>")
    # La vista ad anelli, calcolata qui: il JavaScript la applica e non
    # la ricalcola (R48). Serve prima degli archi, perche' ogni arco
    # pubblica ENTRAMBE le geometrie — le due viste sono due e note.
    anelli = disposizione_ad_anelli(
        [nodo["clicks"] for nodo in nodi],
        float(grafo["width"]), float(grafo["height"]))
    for arco in grafo["links"]:
        partenza, arrivo = nodi[arco["source"]], nodi[arco["target"]]
        forze = geometria_arco((partenza["x"], partenza["y"]),
                               (arrivo["x"], arrivo["y"]), arrivo["r"])
        ad_anelli = geometria_arco(anelli[arco["source"]],
                                   anelli[arco["target"]], arrivo["r"])
        # Le quattro coordinate della vista ad anelli in UN attributo,
        # separate da spazi come un `viewBox`: quattro attributi
        # costavano 76 caratteri per arco contro 32, e su un grafo al
        # massimo della sua dimensione — 60 nodi, 180 archi — la
        # differenza misurata e' 7,9 KB. Il JavaScript le separa, e
        # separare non e' calcolare.
        p.append("<line class='grafo-arco' data-s='%d' data-t='%d' "
                 "x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' "
                 "data-a='%.1f %.1f %.1f %.1f' "
                 "marker-end='url(#grafo-freccia)'/>"
                 % ((arco["source"], arco["target"]) + forze + ad_anelli))
    vicini, incidenti = vicinato(grafo["links"], len(nodi))
    if len(nodi) <= GRAFO_ETICHETTA_TUTTI:
        etichettati = set(range(len(nodi)))
    else:
        etichettati = {i for i, _ in sorted(
            enumerate(nodi),
            key=lambda v: (not v[1]["home"], -v[1]["incoming"]))
            [:GRAFO_ETICHETTA_QUANTI]}
    for i, nodo in enumerate(nodi):
        if nodo["home"]:
            classe, dove = "casa", t("punto di partenza", lang)
        elif nodo["clicks"] is None:
            classe = "orfana"
            dove = t("non raggiunta dalla home per link", lang)
        else:
            classe = "raggiunta"
            dove = t("%s dalla home", lang) % _plurale(
                int(nodo["clicks"]), "click", "click", lang)
        p.append("<circle class='grafo-nodo %s' data-i='%d' data-r='%.1f' "
                 "data-c='%s' data-ax='%.1f' data-ay='%.1f' "
                 "data-v='%s' data-e='%s' "
                 "cx='%.1f' cy='%.1f' r='%.1f'>"
                 "<title>%s — %s, %s, %s</title>"
                 "</circle>"
                 % (classe, i, nodo["r"],
                    "" if nodo["clicks"] is None else nodo["clicks"],
                    anelli[i][0], anelli[i][1],
                    ",".join(str(v) for v in vicini[i]),
                    ",".join(str(k) for k in incidenti[i]),
                    nodo["x"], nodo["y"], nodo["r"], _e(nodo["label"]),
                    t("%s in entrata", lang) % _plurale(
                        int(nodo["incoming"]), "link", "link", lang),
                    t("%s in uscita", lang) % _plurale(
                        int(nodo["outgoing"]), "link", "link", lang),
                    _e(dove)))
        if i in etichettati:
            p.append("<text class='grafo-etichetta' data-i='%d' x='%.1f' "
                     "y='%.1f' data-ax='%.1f' data-ay='%.1f'>%s</text>"
                     % (i, nodo["x"] + nodo["r"] + 3, nodo["y"] + 4,
                        anelli[i][0] + nodo["r"] + 3, anelli[i][1] + 4,
                        _e(nodo["label"])))
    p.append("</svg>")
    p.append("<p class='grafo-comandi' id='grafo-comandi' hidden>"
             "<button type='button' id='grafo-forze' aria-pressed='true'>"
             "%s</button> "
             "<button type='button' id='grafo-anelli' aria-pressed='false'>"
             "%s</button> · "
             "<button type='button' id='grafo-piu'>%s</button> "
             "<button type='button' id='grafo-meno'>%s</button> "
             "<button type='button' id='grafo-zero'>%s</button></p>"
             % (t("Per collegamenti", lang), t("Per distanza", lang),
                t("Ingrandisci", lang), t("Riduci", lang),
                t("Reimposta", lang)))
    p.append("<p id='grafo-stato' class='meta' role='status'></p>")
    p.append("<details><summary>%s</summary>"
             "<table><thead><tr><th scope='col'>%s</th>"
             "<th scope='col'>%s</th><th scope='col'>%s</th>"
             "<th scope='col'>%s</th></tr></thead>"
             % (t("L'architettura in tabella", lang), t("Pagina", lang),
                t("Link in entrata", lang), t("Link in uscita", lang),
                t("Distanza dalla home", lang)))
    for nodo in nodi:
        p.append("<tr><td>%s</td><td class='num'>%d</td>"
                 "<td class='num'>%d</td><td class='num'>%s</td></tr>"
                 % (_e(nodo["url"]), nodo["incoming"], nodo["outgoing"],
                    t("non raggiunta", lang) if nodo["clicks"] is None
                    else t("%d click", lang) % nodo["clicks"]))
    p.append("</table></details>")


def _sezione_superficie(referto: dict, p: List[str],
                        lang: str = LINGUA_CANONICA) -> None:
    """Profondita' di crawl e matematica della superficie."""
    profondita = depth_distribution(referto.get("pages") or [])
    matematica = referto.get("surface_math")
    if not profondita and not matematica:
        return
    p.append("<h2>%s</h2>" % t("Superficie", lang))
    if profondita:
        massimo = max(v["pages"] for v in profondita) or 1
        # La terza colonna porta la barra, che e' la stessa misura
        # della seconda resa in grafica: l'intestazione lo DICE invece
        # di restare vuota. Un `th` vuoto e' un difetto che axe rileva,
        # e questo referto misura l'accessibilita' altrui.
        p.append("<table><thead><tr><th scope='col'>%s</th>"
                 "<th scope='col'>%s</th>"
                 "<th scope='col'>%s</th></tr></thead>"
                 % (t("Distanza dalla home", lang), t("Pagine", lang),
                    t("Proporzione", lang)))
        for voce in profondita:
            # Il secchiello delle ignote e' giallo: non e' un livello
            # peggiore degli altri, e' un livello che non sappiamo.
            classe = "warn" if voce["unknown"] else "muted"
            p.append("<tr><td>%s</td><td class='num'>%d</td>"
                     "<td style='width:60%%'><span class='bar %s' "
                     "aria-hidden='true' "
                     "style='width:%.0f%%'></span></td></tr>"
                     % (_e(t(voce["label"], lang)), voce["pages"], classe,
                        100.0 * voce["pages"] / massimo))
        p.append("</table>")
    _treemap_html(referto, p, lang)
    _grafo_html(referto, p, lang)
    if matematica:
        p.append("<div class='card'><p>%s</p>"
                 % (t("%d pagine, %d passaggi — %.2f per pagina, %.0f "
                      "parole per pagina.", lang)
                    % (matematica["pages"], matematica["chunks"],
                       matematica["chunks_per_page"],
                       matematica["words_per_page"])))
        if matematica["multiplier"]:
            p.append("<p class='grande'>x%.1f</p>"
                     "<p class='meta'>%s</p>"
                     % (matematica["multiplier"],
                        t("passaggi recuperabili con %d parole per "
                          "pagina: %d invece di %d. Ogni passaggio è "
                          "un'occasione in più di essere recuperato.",
                          lang)
                        % (matematica["target_words_per_page"],
                           matematica["potential_chunks"],
                           matematica["chunks"])))
        p.append("<p class='disclaimer'>%s</p></div>"
                 % _e(t(matematica["assumption"], lang)))


def _sezione_delta(referto: dict, p: List[str],
                   lang: str = LINGUA_CANONICA) -> None:
    """«Rispetto all'esecuzione precedente», con risolti e nuovi."""
    delta = referto.get("delta")
    if not delta:
        return
    p.append("<h2>%s</h2>" % t("Rispetto all'esecuzione precedente", lang))
    p.append("<p class='meta'>%s</p>"
             % (t("Confronto con il %s (v%s).", lang)
                % (_e(delta.get("previous_run")),
                   _e(delta.get("previous_version")))))
    righe = []
    if delta.get("overall"):
        righe.append((t("Complessivo", lang), delta["overall"]))
    righe += [(v["area"].replace("mars_", ""), v)
              for v in delta["scores"] if v["change"]]
    if righe:
        p.append("<table><thead><tr><th scope='col'>%s</th>"
                 "<th scope='col'>%s</th><th scope='col'>%s</th>"
                 "<th scope='col'>%s</th></tr></thead>"
                 % (t("Area", lang), t("Prima", lang), t("Dopo", lang),
                    t("Variazione", lang)))
        for nome, voce in righe:
            # Il colore segue il SEGNO e non la scala dei punteggi: qui
            # non si giudica quanto vale l'area, si dice se e' salita.
            classe = "ok" if voce["change"] > 0 else "bad"
            p.append("<tr><td>%s</td><td class='num'>%.0f</td>"
                     "<td class='num'>%.0f</td>"
                     "<td class='num %s'>%s</td></tr>"
                     % (_e(nome), voce["before"], voce["after"], classe,
                        _segno(voce["change"], lang)))
        p.append("</table>")
    for titolo, elenco, classe in (
            (t("Risolti", lang), delta["resolved"], "ok"),
            (t("Nuovi", lang), delta["new"], "bad")):
        if not elenco:
            continue
        p.append("<h3 class='%s'>%s (%d)</h3>" % (classe, titolo,
                                                  len(elenco)))
        p.append("<ul class='rilievi'>%s</ul>"
                 % "".join("<li>%s</li>"
                           % _e(finding_texts(r, lang)["title"])
                           for r in elenco))
    cambio_k = delta.get("rrf_k_changed")
    if cambio_k:
        p.append("<p class='meta'>%s</p>"
                 % (t("Il k della fusione è cambiato, da %d a %d: il "
                      "consenso aggregato delle due esecuzioni non è la "
                      "stessa misura.", lang)
                    % (cambio_k["before"], cambio_k["after"])))
    if delta.get("by_title_fallback"):
        p.append("<p class='meta'>%s</p>"
                 % t("Qualche rilievo non ha una chiave stabile: il "
                     "confronto usa il titolo, ed è più debole.", lang))
    for cambio in delta.get("measure_changes") or []:
        p.append("<p class='meta'>%s</p>"
                 % (_e(t("È cambiato che cosa si misura — %s: i numeri si "
                         "muovono anche a sito invariato.", lang)
                       % t(cambio["reason"], lang))))
    for migrazione in delta.get("key_migrations") or []:
        # Il MOTIVO per esteso, qui e nel Markdown: la vista compatta
        # ha una riga sola e si ferma al prefisso, ma chi legge il
        # referto consegnato deve poter capire perché un'area intera
        # risulta risolta e ricomparsa.
        #
        # La VERSIONE della migrazione resta nel dato (`since`) e non
        # nella prosa: al cliente non dice nulla di azionabile, e a chi
        # legge il JSON serve com'è. Stamparla renderebbe inoltre
        # indistinguibile una costante dichiarata dalla versione di
        # questa esecuzione, che il golden vieta di far comparire.
        p.append("<p class='meta'>%s</p>"
                 % _e(t("Le chiavi %s hanno cambiato forma — %s: in "
                        "quest'area «risolto» e «comparso» non sono "
                        "fatti del sito.", lang)
                      % (migrazione["prefix"],
                         t(migrazione["reason"], lang))))


def _sezione_piano(referto: dict, p: List[str],
                   ancore: Optional[Dict[str, str]] = None,
                   lang: str = LINGUA_CANONICA) -> None:
    """Il piano di interventi, ordinato.

    **Sempre presente**, anche vuoto, a differenza delle tre sezioni
    che seguono: un piano che sparisce non si distingue da un piano non
    calcolato.

    Qui non c'e' il tetto di cinque della vista testo: e' il documento
    che si consegna, e li porta tutti.
    """
    piano = referto.get("remediation") or []
    riepilogo = mars_remediation.riepilogo(piano, referto)
    p.append("<h2>%s</h2>" % t("Piano di interventi", lang))
    if not piano:
        p.append("<p class='meta'>%s</p>"
                 % t("Nessun rilievo critico o di avvertenza: non c'è "
                     "nulla da mettere in ordine di priorità.", lang))
        return

    conteggi = [t("%d interventi (%d critici, %d avvertenze)", lang)
                % (riepilogo["total"], riepilogo["critical"],
                   riepilogo["warning"]),
                t("%d quick win", lang) % riepilogo["quick_wins"]]
    senza = riepilogo["total"] - riepilogo["by_lane"]["misurato"]
    if senza:
        conteggi.append(t("%d senza recupero dichiarato", lang) % senza)
    if riepilogo["no_effort"]:
        conteggi.append(t("%d senza sforzo dichiarato", lang)
                        % riepilogo["no_effort"])
    p.append("<p class='meta'>%s</p>" % _e(" · ".join(conteggi)))
    # Le aree si CONTANO: al massimo cinque delle nove alimentano il
    # piano, perche' due non producono rilievi e due li producono tutti
    # `info`. Un numero fisso qui sarebbe falso.
    p.append("<p class='meta'>%s</p>"
             % (t("Ordinato per gravità, poi per guadagno dell'indice di "
                  "citabilità. Lo alimentano %d aree su %d; i punti "
                  "d'area sono la stessa aritmetica che ha prodotto i "
                  "punteggi, il guadagno d'indice è una stima derivata "
                  "dai pesi per assistente.", lang)
                % (riepilogo["areas_covered"], riepilogo["areas_total"])))
    for voce in piano:
        p.append(_voce_piano_html(voce, ancore, lang))


def _sezione_rrf(referto: dict, p: List[str],
                 lang: str = LINGUA_CANONICA) -> None:
    aggregato = referto.get("rrf_aggregate")
    simulazione = referto.get("rrf_simulation") or []
    if not aggregato and not simulazione:
        return
    p.append("<h2>%s</h2>" % t("Simulazione RRF", lang))
    if aggregato:
        p.append("<div class='card'><p class='meta'>%s</p>"
                 "<p class='grande %s'>%s</p>"
                 % (t("Consenso fra il recuperatore lessicale e quello "
                      "vettoriale, aggregato su %d query — la misura più "
                      "solida, perché un accordo su una sola domanda può "
                      "essere un caso.", lang) % len(simulazione),
                    _classe(_quota_consenso(aggregato)),
                    _e(_consenso_leggibile(aggregato, lang))))
        if aggregato.get("top_chunk"):
            p.append("<p class='meta'>%s<br><code>%s</code></p>"
                     % (t("Passaggio più recuperabile:", lang),
                        _e(aggregato["top_chunk"])))
        sensibilita = sensibilita_leggibile(
            referto.get("rrf_sensitivity") or [], lang)
        if sensibilita:
            p.append("<p class='meta'>%s <b>%s</b></p>"
                     % (t("al variare di k:", lang), _e(sensibilita)))
        for diagnosi, divergenti in divergenze_leggibili(aggregato, lang):
            p.append("<p class='meta'>%s</p><ul>%s</ul>"
                     % (_e(diagnosi),
                        "".join("<li><code>%s</code></li>"
                                % _e(v["label"]) for v in divergenti)))
        p.append("</div>")
    if simulazione:
        p.append("<table><thead><tr><th scope='col'>%s</th>"
                 "<th scope='col'>%s</th>"
                 "<th scope='col'>%s</th></tr></thead>"
                 % (t("Query", lang), t("Consenso", lang),
                    t("Passaggio migliore", lang)))
        for voce in simulazione:
            p.append("<tr><td><code>%s</code></td>"
                     "<td class='num %s'>%s</td><td>%s</td></tr>"
                     % (_e(voce["query"]), _classe(_quota_consenso(voce)),
                        _e(_consenso_leggibile(voce, lang)),
                        _e(voce["top_chunk"] or "—")))
        p.append("</table>")


def _sezione_citabilita(referto: dict, p: List[str],
                        lang: str = LINGUA_CANONICA) -> None:
    cit = referto.get("citability")
    if not cit or not cit.get("profiles"):
        return
    p.append("<h2>%s</h2>" % t("Profili di citabilità IA", lang))
    # L'unica tabella del referto che non aveva alcuna intestazione:
    # tre colonne di numeri senza dire di che cosa fossero.
    p.append("<p class='meta'>%s</p><table><thead><tr>"
             "<th scope='col'>%s</th><th scope='col'>%s</th>"
             "<th scope='col'>%s</th></tr></thead>"
             % (t("Mercato: %s", lang) % _e(cit.get("market")),
                t("Assistente", lang), t("Profilo", lang),
                t("Proporzione", lang)))
    for assistente, valore in cit["profiles"].items():
        # `aria-hidden`: la barra e' il numero della colonna accanto
        # ridisegnato, e un lettore di schermo che la annunciasse
        # leggerebbe due volte lo stesso dato.
        barra = ("<span class='bar %s' aria-hidden='true' "
                 "style='width:%.0f%%'></span>"
                 % (_classe(valore), (valore or 0)))
        testo = ("%.1f" % valore) if valore is not None \
            else t("n/d", lang)
        p.append("<tr><td>%s</td><td class='num %s'>%s</td>"
                 "<td style='width:55%%'>%s</td></tr>"
                 % (_e(assistente), _classe(valore), testo, barra))
    if cit.get("score") is not None:
        p.append("<tr><td><strong>%s</strong></td>"
                 "<td class='num %s'><strong>%.1f</strong></td><td></td></tr>"
                 % (t("Indice composito", lang), _classe(cit["score"]),
                    cit["score"]))
    p.append("</table>")
    # Il disclaimer sta subito sotto i numeri, non in fondo alla pagina:
    # chi legge il punteggio deve leggere anche cosa non è.
    p.append("<p class='disclaimer'>%s</p>"
             % _e(t(cit.get("disclaimer") or "", lang)))
    compatte = _righe_compatte(_area_di(referto, "mars_citability"), lang)
    if compatte:
        p.append("<ul class='rilievi'>%s</ul>"
                 % "".join("<li>%s</li>" % _e(i) for i in compatte))
    _azioni_di_profilo(referto, p, lang)


# Quante azioni mostrare sotto i profili di citabilita'. Tre: e' una
# nota dentro un'altra sezione, non un secondo piano.
AZIONI_DI_PROFILO = 3


def _azioni_di_profilo(referto: dict, p: List[str],
                       lang: str = LINGUA_CANONICA) -> None:
    """Gli interventi che spostano di piu' l'indice di citabilita'.

    Legge il piano canonico e lo riordina per solo guadagno: non e' lo
    stesso elenco dei primi interventi, perche' li' la gravita' domina
    — un rilievo critico che muove poco sta comunque davanti a
    un'avvertenza che muove molto. Qui la domanda e' un'altra: fra
    tutti, quali pesano di piu' su QUESTI profili.

    Nessuna chiave nuova nel dato: il piano e' gia' pubblicato, e una
    `top_actions` accanto ai profili sarebbe una seconda copia che
    diverge in silenzio dalla prima. E' la stessa ragione per cui il
    referto non ricalcola il piano dentro le viste.

    Ogni voce nomina l'assistente che guadagna di piu': i pesi per
    assistente sono diversi, quindi la stessa correzione non vale
    uguale per tutti, ed e' l'unica cosa che questa sezione dice e il
    piano no.
    """
    con_guadagno = [v for v in referto.get("remediation") or []
                    if v.get("index_gain")]
    if not con_guadagno:
        return
    ordinate = sorted(con_guadagno, key=lambda v: -v["index_gain"])
    p.append("<p class='meta'>%s</p>"
             % t("Azioni con maggior guadagno di profilo:", lang))
    p.append("<ul class='rilievi'>")
    for voce in ordinate[:AZIONI_DI_PROFILO]:
        profili = voce.get("profile_gains") or {}
        migliore = ""
        if profili:
            nome, guadagno = max(profili.items(), key=lambda c: c[1])
            migliore = (t(" — soprattutto %s (+%.2f)", lang)
                        % (_e(nome), guadagno))
        p.append("<li>%s <strong>+%.2f</strong>%s%s</li>"
                 % (_e(finding_texts(voce, lang)["title"]),
                    voce["index_gain"], t(" sull'indice", lang), migliore))
    p.append("</ul>")


def _sezione_llm(referto: dict, p: List[str],
                 lang: str = LINGUA_CANONICA) -> None:
    giudizi = giudizi_del_referto(referto)
    if not giudizi:
        return
    p.append("<h2>%s</h2>" % t("Giudizio LLM", lang))
    scarti_visti = False
    for llm in giudizi:
        p.append("<div class='card'>")
        p.append("<p class='meta'>%s · %s · %s</p>"
                 % (_e(llm.get("provider") or ""), _e(llm.get("model")),
                    t("%s passaggi valutati", lang)
                    % _e(llm.get("chunk_valutati"))))
        if not llm.get("answered"):
            # Il giudice che non ha risposto resta nella pagina col suo
            # motivo: e' stato chiesto, e chi legge deve sapere che
            # manca e perche'.
            p.append("<ul class='rilievi'>%s</ul></div>"
                     % "".join("<li>%s</li>" % _e(m)
                               for m in llm.get("issues") or []))
            continue
        if llm.get("score") is not None:
            p.append("<p class='grande %s'>%s"
                     "<span class='muted'>/100</span></p>"
                     % (_classe(llm["score"]), _e(llm["score"])))
        p.append("<p>%s</p>" % _e(llm.get("motivazione") or ""))
        righe = scarti_leggibili(llm, lang)
        scarti_visti = scarti_visti or bool(righe)
        for etichetta, valore in righe:
            p.append("<p class='meta'>%s <strong>%s</strong></p>"
                     % (_e(etichetta), _e(valore)))
        if llm.get("passaggio_migliore"):
            p.append("<p class='meta'>%s <code>%s</code></p>"
                     % (t("Passaggio migliore:", lang),
                        _e(llm["passaggio_migliore"])))
        for titolo, chiave in ((t("Punti di forza", lang), "punti_forti"),
                               (t("Da migliorare", lang), "punti_deboli")):
            voci = llm.get(chiave) or []
            if voci:
                p.append("<p class='strumento'><strong>%s</strong></p>"
                         "<ul class='rilievi'>%s</ul>"
                         % (titolo,
                            "".join("<li>%s</li>" % _e(v) for v in voci)))
        p.append("</div>")
    if scarti_visti:
        # Una volta sola, sotto tutti i giudici: ripeterla per ciascuno
        # la trasformerebbe in rumore, e chi legge la salterebbe.
        p.append("<p class='meta'>%s</p>"
                 % _e(t("gli scarti confrontano un giudizio "
                        "con una stima euristica", lang)))


# ======================================================================
# Il solo JavaScript del referto (D1, Fase 8)
# ======================================================================
#
# Ratificato con D1 il 2026-08-21, e adottato qui per la prima volta.
# Tre vincoli, che i test presidiano:
#
# 1. **Inline e senza origini esterne.** Nessun `src`, nessuna CDN,
#    nessuna `fetch`: il referto resta un file solo, apribile fra due
#    anni da un archivio senza rete. Il vincolo che cambia rispetto a
#    prima non e' «niente script», e' «niente che venga da fuori».
# 2. **Progressive enhancement.** Il disegno e' completo nell'HTML: lo
#    script non crea nodi, ne' archi, ne' etichette. Se non gira — un
#    lettore che lo disabilita, un PDF di stampa — resta il grafo
#    statico, che e' la stessa informazione senza i comandi.
# 3. **Nessun dato dentro il codice.** Posizioni, raggi e distanze si
#    leggono dagli attributi `data-*` del DOM. Interpolare il referto
#    dentro una stringa JavaScript significherebbe un secondo percorso
#    di escaping accanto a `_e()`, ed e' esattamente il modo in cui
#    nasce una XSS in un file che contiene testo preso dal sito
#    analizzato.
#
# `prefers-reduced-motion` non ha bisogno di essere letto qui: le sole
# transizioni stanno nel CSS, e li' la media query le spegne.
REFERTO_JS = """
(function () {
  "use strict";
  var svg = document.getElementById("grafo");
  if (!svg) { return; }
  var nodi = [].slice.call(svg.querySelectorAll(".grafo-nodo"));
  var archi = [].slice.call(svg.querySelectorAll(".grafo-arco"));
  if (!nodi.length) { return; }
  var comandi = document.getElementById("grafo-comandi");
  var stato = document.getElementById("grafo-stato");
  /* Le etichette non sono una per nodo: oltre una certa dimensione il
     grafo ne mostra solo le piu' linkate. Si tengono come ELENCO,
     perche' ciascuna porta gia' le proprie due posizioni e non serve
     piu' risalire al nodo che la possiede. */
  var etichetteVive = [].slice.call(
    svg.querySelectorAll(".grafo-etichetta"));
  var vbase = svg.getAttribute("viewBox").split(" ").map(Number);
  /* Le DUE viste sono entrambe calcolate in Python: quella a forze sta
     negli attributi di partenza, quella ad anelli nei `data-a*`. Il
     layout di partenza si fotografa al caricamento perche' e' cio' a
     cui "Reimposta" riporta: fotografare non e' calcolare. */
  function istantanea(elementi, attributi) {
    return elementi.map(function (el) {
      return attributi.map(function (a) { return el.getAttribute(a); });
    });
  }
  var nodiForze = istantanea(nodi, ["cx", "cy"]);
  var archiForze = istantanea(archi, ["x1", "y1", "x2", "y2"]);
  var testiForze = etichetteVive.map(function (e) {
    return [e.getAttribute("x"), e.getAttribute("y")];
  });

  /* Applicare, non ricalcolare: l'aritmetica della geometria e' uscita
     di qui perche' nessun test la eseguiva -- quattro ne guardavano la
     stringa -- e in Python la suite di sempre la verifica (R48). Al
     JavaScript restano gli eventi, le classi e lo zoom, che dipendono
     dal gesto e non si possono precalcolare. */
  function applica(elementi, attributi, valori) {
    elementi.forEach(function (el, i) {
      attributi.forEach(function (a, k) {
        if (valori[i][k] !== null) { el.setAttribute(a, valori[i][k]); }
      });
    });
  }

  /* Vista per distanza: un anello per click dalla home, gli orfani
     sul cerchio piu' esterno. Dice a colpo d'occhio quanto e'
     profondo il sito, che il layout a forze non mostra. */
  function anelli() {
    applica(nodi, ["cx", "cy"], istantanea(nodi, ["data-ax", "data-ay"]));
    /* Le quattro coordinate dell'arco viaggiano in un attributo solo,
       come un `viewBox`: qui si separano, e separare non e' calcolare. */
    applica(archi, ["x1", "y1", "x2", "y2"], archi.map(function (a) {
      return (a.getAttribute("data-a") || "").split(" ");
    }));
    applica(etichetteVive, ["x", "y"],
            istantanea(etichetteVive, ["data-ax", "data-ay"]));
  }

  function forze() {
    applica(nodi, ["cx", "cy"], nodiForze);
    applica(archi, ["x1", "y1", "x2", "y2"], archiForze);
    applica(etichetteVive, ["x", "y"], testiForze);
  }

  /* Evidenziazione: il nodo, i suoi archi e i suoi vicini restano
     accesi, il resto si spegne. Su un grafo di sessanta nodi e' la
     sola cosa che rende leggibile un groviglio. */
  /* Vicini e archi incidenti li dichiara il nodo (`data-v`, `data-e`):
     non dipendono dal gesto, sono una proprieta' del grafo, e Python
     la conosce. Prima si scandivano TUTTI gli archi a ogni passaggio
     del puntatore. */
  function insieme(el, attributo) {
    var dentro = {};
    (el.getAttribute(attributo) || "").split(",").forEach(function (x) {
      if (x !== "") { dentro[x] = true; }
    });
    return dentro;
  }

  function evidenzia(i) {
    var vicini = insieme(nodi[i], "data-v");
    var incidenti = insieme(nodi[i], "data-e");
    archi.forEach(function (a, k) {
      var acceso = incidenti[String(k)] === true;
      a.classList.toggle("acceso", acceso);
      a.classList.toggle("spento", !acceso);
    });
    nodi.forEach(function (n, k) {
      n.classList.toggle("spento", vicini[String(k)] !== true);
    });
    if (stato) {
      var t = nodi[i].querySelector("title");
      stato.textContent = t ? t.textContent : "";
    }
  }

  function pulisci() {
    nodi.forEach(function (n) { n.classList.remove("spento"); });
    archi.forEach(function (a) {
      a.classList.remove("spento");
      a.classList.remove("acceso");
    });
    if (stato) { stato.textContent = ""; }
  }

  /* I nodi diventano raggiungibili da tastiera SOLO ora che il fuoco
     ha qualcosa da mostrare: nell'HTML statico sarebbero fermate di
     tabulazione vuote. */
  nodi.forEach(function (n, i) {
    n.setAttribute("tabindex", "0");
    n.addEventListener("pointerenter", function () { evidenzia(i); });
    n.addEventListener("focus", function () { evidenzia(i); });
    n.addEventListener("pointerleave", pulisci);
    n.addEventListener("blur", pulisci);
  });
  svg.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { pulisci(); }
  });

  function zoom(fattore) {
    var cx = vista[0] + vista[2] / 2, cy = vista[1] + vista[3] / 2;
    vista[2] *= fattore;
    vista[3] *= fattore;
    vista[0] = cx - vista[2] / 2;
    vista[1] = cy - vista[3] / 2;
    svg.setAttribute("viewBox", vista.join(" "));
  }
  var vista = vbase.slice();

  function bottone(id, azione) {
    var b = document.getElementById(id);
    if (b) { b.addEventListener("click", azione); }
    return b;
  }
  var bForze = bottone("grafo-forze", function () { premuto(true); });
  var bAnelli = bottone("grafo-anelli", function () { premuto(false); });
  function premuto(perForze) {
    if (bForze) { bForze.setAttribute("aria-pressed", String(perForze)); }
    if (bAnelli) { bAnelli.setAttribute("aria-pressed", String(!perForze)); }
    pulisci();
    if (perForze) { forze(); } else { anelli(); }
  }
  bottone("grafo-piu", function () { zoom(0.8); });
  bottone("grafo-meno", function () { zoom(1.25); });
  bottone("grafo-zero", function () {
    vista = vbase.slice();
    svg.setAttribute("viewBox", vista.join(" "));
    premuto(true);
  });
  /* I comandi si accendono per ultimi: se qualcosa qui sopra fosse
     esploso, resterebbero nascosti invece che inerti. */
  if (comandi) { comandi.removeAttribute("hidden"); }
}());
"""


# Le fonti del metodo, nel piede del referto HTML (U11).
# ----------------------------------------------------------------------
# Chi riceve un referto di consulenza deve poter risalire a COME i
# numeri sono stati fatti senza chiederlo a chi glielo ha consegnato.
# Sono le stesse che il README elenca, e un test lo verifica: due
# elenchi della stessa cosa divergono, e qui divergerebbero in silenzio
# — e' la deriva che R32 ha gia' chiuso una volta.
RIFERIMENTI: Tuple[Tuple[str, str], ...] = (
    ("Cormack, Clarke, Buettcher (2009), «Reciprocal Rank Fusion»,"
     " SIGIR '09", ""),
    ("Robertson & Zaragoza (2009), «The Probabilistic Relevance"
     " Framework: BM25 and Beyond»", ""),
    ("Schema.org", "https://schema.org/"),
    ("Web Content Accessibility Guidelines (WCAG) 2.1",
     "https://www.w3.org/TR/WCAG21/"),
)


def _footer_html(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """Il piede: chi ha generato il referto, con che formula, su che basi.

    Firma testuale e non logo: il perimetro di U11.1 lo dice — «la
    testata senza logo e la favicon di MARS», e incorporare il caratere
    del sito costava 72 KB di base64 su un referto di 57. Non e' una
    casella rimasta aperta.

    La `k` viene dal REFERTO e non dalla costante: `--rrf-k` la cambia,
    e un piede che dichiarasse 60 su un referto girato con 10
    mentirebbe proprio dove promette di dire come si e' misurato.
    """
    rrf = referto.get("rrf") or {}
    # Gli URL come TESTO e non come `<a href>`: il referto non contiene
    # alcun riferimento esterno, ed e' un invariante presidiato
    # (`riferimenti_esterni` in tests/test_report.py). Un link non
    # scarica nulla, ma la guardia e' volutamente larga e allargarla
    # per un piede sarebbe scambiare una promessa per una comodita' —
    # l'indirizzo si copia lo stesso.
    voci = ["<li>%s%s</li>" % (_e(testo), (" — %s" % _e(url)) if url else "")
            for testo, url in RIFERIMENTI]
    return ("<footer class='piede'>"
            "<p class='meta'><strong>MARS Beacon</strong> — %s</p>"
            "<p class='meta'>%s</p>"
            "<p class='meta'>%s</p><ul class='rilievi'>%s</ul>"
            "</footer>"
            % (_e(t("audit di citabilità per assistenti IA", lang)),
               _e(t("Generato da mars_audit.py v%s · fusione RRF con "
                    "k=%s", lang)
                  % (referto.get("version"), rrf.get("k"))),
               _e(t("Fonti del metodo:", lang)), "".join(voci)))


def render_html(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """Referto HTML nello stile di Lighthouse, esteso alle nostre aree.

    Autoconsistente per costruzione: CSS incorporato, favicon come data
    URI, quadranti in SVG calcolato qui. **Nessuna origine esterna** —
    niente CDN, niente `src`, niente richieste di rete: un referto deve
    potersi aprire fra due anni, da un archivio, senza rete.

    Fino alla Fase 8 il vincolo era piu' stretto, «nessuno script», e
    D1 lo ha ristretto a cio' che davvero lo garantisce. Un `<script>`
    inline non fa uscire il referto dal file: e' `src` che lo farebbe.
    Lo script c'e' solo dove il grafo dei link c'e', e cio' che
    aggiunge — evidenziare, disporre per distanza, ingrandire — e' in
    piu' rispetto a un disegno gia' completo: vedi `REFERTO_JS`.
    """
    lang = normalizza_lingua(lang)
    p: List[str] = []
    icona = _favicon_data_uri()
    # L'attributo `lang` NON e' cosmesi: e' il criterio WCAG 3.1.1 che
    # quest'referto stesso misura sulle pagine altrui (`wcag.lang.missing`).
    # Cablarlo a "it" su un referto inglese sarebbe il difetto che il
    # documento rileva, commesso dal documento.
    p.append("<!doctype html><html lang='%s'><head><meta charset='utf-8'>"
             % lang)
    p.append("<meta name='viewport' content='width=device-width,"
             "initial-scale=1'>")
    p.append("<title>MARS Beacon — %s</title>" % _e(referto["url"]))
    if icona:
        p.append("<link rel='icon' href='%s'>" % icona)
    p.append("<style>%s</style></head><body><main>" % CSS)

    p.append("<header class='testata'><h1>MARS Beacon</h1>")
    p.append("<p class='meta'><code>%s</code></p>" % _e(referto["url"]))
    p.append("<p class='meta'>%s</p></header>"
             % (t("%s · %s pagine trovate via %s · %s chunk · "
                  "mercato %s · v%s", lang)
                % (_e(referto["generated_at"]), referto["pages_crawled"],
                   _e(t(referto.get("discovery") or "", lang)),
                   referto["chunks"], _e(referto["market"]),
                   _e(referto["version"]))))
    for nota in _nota_lingua(referto, lang):
        if nota:
            p.append("<p class='disclaimer'>%s</p>" % _e(nota))
    if not icona:
        # Il degrado non e' piu' silenzioso (R43). Compare SOLO quando
        # succede — un checkout parziale, un file illeggibile — quindi
        # un referto sano non guadagna una riga di rumore. E' la stessa
        # regola di `wcag.status.no_fixes`: si dichiara la degradazione
        # dove costa qualcosa, non ovunque per simmetria.
        p.append("<p class='disclaimer'>%s</p>"
                 % _e(t("Icona non incorporata: il file non è stato "
                        "letto. Il referto resta valido e "
                        "autoconsistente.", lang)))

    # Le ancore si calcolano UNA volta e si passano a chi le usa: la
    # scheda che le emette, il piano e il riquadro in testa che le
    # linkano. Ricalcolare la condizione in tre posti significherebbe
    # tre occasioni di divergere, e un link rotto in un referto HTML
    # non fa alcun rumore.
    ancore = ancore_dei_rilievi(referto)

    p.append(_hero(referto, lang))
    p.append(_primi_rilievi(referto, ancore, lang))
    p.append(_fascia_quadranti(referto, lang))
    p.append(_legenda(lang))

    p.append("<h2>%s</h2>" % t("Aree", lang))
    for area in referto["areas"]:
        p.append(_scheda_area(area, referto, ancore, lang))

    _sezione_superficie(referto, p, lang)
    _sezione_delta(referto, p, lang)
    _sezione_piano(referto, p, ancore, lang)
    _sezione_rrf(referto, p, lang)
    _sezione_citabilita(referto, p, lang)
    _sezione_llm(referto, p, lang)

    if referto["robots_ignored"] or referto["skipped"]:
        p.append("<h2>%s</h2>" % t("Cosa non è stato guardato", lang))
        if referto["robots_ignored"]:
            p.append("<p class='bad'>%s</p>"
                     % t("robots.txt ignorato per dichiarazione di "
                         "proprietà del dominio.", lang))
        if referto["skipped"]:
            p.append("<div class='card'><p class='meta'>%s</p>"
                     "<ul class='rilievi'>%s</ul></div>"
                     % (t("%d URL saltati:", lang)
                        % len(referto["skipped"]),
                        "".join("<li>%s</li>" % _e(m)
                                for m in referto["skipped"])))

    # Lo script SOLO se il grafo c'e': un referto senza architettura da
    # mostrare non porta codice che non ha nulla da fare.
    if "id='grafo'" in "".join(p):
        p.append("<script>%s</script>" % REFERTO_JS)
    # FUORI da `<main>`: un `<footer>` che gli sta dentro e' il piede
    # di quella sezione, non del documento, e non diventa un punto di
    # riferimento `contentinfo` per chi naviga con un lettore di
    # schermo. E' la stessa semantica che questo referto misura sulle
    # pagine altrui.
    p.append("</main>")
    p.append(_footer_html(referto, lang))
    p.append("</body></html>")
    return "".join(p)


# ======================================================================
# Vista Markdown: il referto che si incolla in una issue (Fase 6)
# ======================================================================
#
# Serve dove l'HTML non arriva: una issue di GitHub, una pagina di wiki,
# un messaggio. Ed e' l'unico formato in cui il piano diventa
# **operativo** invece che leggibile — una task list GFM si spunta.
#
# La gravita' e' un MARCATORE testuale e non un colore. In HTML il
# badge rosso porta gia' la parola; qui non c'e' un badge, e affidare
# la gravita' alla sola posizione nell'elenco significherebbe perderla
# appena qualcuno riordina o copia una riga.

_MARCATORE = {SEV_CRITICAL: "**[CRITICO]**", SEV_WARNING: "[AVVISO]",
              SEV_INFO: "[INFO]", SEV_OK: "[OK]"}


def _md_cella(valore: object) -> str:
    """Un valore dentro una cella di tabella Markdown.

    Due caratteri rompono una tabella GFM e vanno neutralizzati: la
    pipe, che aprirebbe una colonna in piu', e l'a-capo, che chiuderebbe
    la riga. Arrivano da fuori — titoli di pagina, `solution` di ZAP,
    testi del sito — quindi non e' un'ipotesi.
    """
    testo = "" if valore is None else str(valore)
    return testo.replace("|", "\\|").replace("\n", " ").strip()


def _md_rilievo(rilievo: dict,
                lang: str = LINGUA_CANONICA) -> List[str]:
    """Un rilievo come voce di elenco, con la correzione sotto."""
    testi = finding_texts(rilievo, lang)
    righe = ["- %s %s" % (t(_MARCATORE.get(rilievo.get("severity"), "[?]"),
                            lang), testi["title"])]
    if testi["detail"]:
        righe.append("  %s" % testi["detail"])
    if testi["fix"]:
        righe.append("  *%s* %s" % (t("Correzione:", lang), testi["fix"]))
    if testi["example"]:
        # Recintato: un esempio nginx o JSON-LD dentro un elenco
        # perderebbe indentazione e a-capo, che sono il suo contenuto.
        # La didascalia sopra e' la stessa dell'HTML, e per la stessa
        # ragione (R60): il recinto dice «codice», non «inventato».
        righe.append("")
        righe.append("  *%s*"
                     % t("Esempio — non è contenuto del tuo sito",
                         lang))
        righe.append("  ```")
        righe.extend("  %s" % r for r in testi["example"].split("\n"))
        righe.append("  ```")
    return righe


def render_markdown(referto: dict,
                    lang: str = LINGUA_CANONICA) -> str:
    """Il referto in Markdown, con il piano come task list.

    Non e' una traduzione dell'HTML: e' la stessa struttura resa dove
    non c'e' CSS. Legge gli stessi dati canonici — `overall`,
    `remediation`, `findings` — quindi non puo' raccontare un referto
    diverso dalle altre viste.
    """
    lang = normalizza_lingua(lang)
    r: List[str] = ["# MARS Beacon — %s" % (referto.get("url") or "")]
    r.append("")
    r.append(t("*%s · v%s · %s pagine trovate via %s · %s chunk · "
               "mercato %s*", lang)
             % (referto.get("generated_at"), referto.get("version"),
                referto.get("pages_crawled"),
                t(referto.get("discovery") or "", lang),
                referto.get("chunks"), referto.get("market")))
    for nota in _nota_lingua(referto, lang):
        if nota:
            r += ["", "*%s*" % _md_cella(nota)]

    complessivo = referto.get("overall")
    if complessivo:
        r += ["", "## %s" % t("Complessivo", lang), "",
              "**%.0f/100** — %s" % (complessivo["score"],
                                     _verdetto(complessivo["score"], lang)),
              "",
              t("Media pesata di %d misure; escluse %s. Scala "
                "dichiarata: critico sotto %d, da migliorare %d-%d, "
                "buono da %d.", lang)
              % (len(complessivo["components"]),
                 aree_escluse_leggibili(referto, lang),
                 SOGLIA_MEDIO, SOGLIA_MEDIO,
                 SOGLIA_BUONO - 1, SOGLIA_BUONO)]

    r += ["", "## %s" % t("Punteggi per area", lang), "",
          "| %s | %s | %s |" % (t("Area", lang), t("Punteggio", lang),
                                t("Con che cosa", lang)),
          "|---|---|---|"]
    for area in referto.get("areas") or []:
        voto = ("%.0f/100" % area["score"] if area["score"] is not None
                else t(STATO_LEGGIBILE.get(area.get("status"),
                                           "non misurato"), lang))
        r.append("| %s | %s | %s |"
                 % (_md_cella(t(area.get("label") or "", lang)), voto,
                    _md_cella(" · ".join(_qualificatori(area, lang)))))

    profondita = depth_distribution(referto.get("pages") or [])
    matematica = referto.get("surface_math")
    if profondita or matematica:
        r += ["", "## %s" % t("Superficie", lang), ""]
        if profondita:
            r += ["| %s | %s |" % (t("Distanza dalla home", lang),
                                   t("Pagine", lang)), "|---|---|"]
            r += ["| %s | %d |" % (_md_cella(t(v["label"], lang)),
                                   v["pages"])
                  for v in profondita]
        if matematica:
            r += ["", t("%d pagine, %d passaggi — %.2f per pagina, %.0f "
                        "parole per pagina.", lang)
                  % (matematica["pages"], matematica["chunks"],
                     matematica["chunks_per_page"],
                     matematica["words_per_page"])]
            if matematica["multiplier"]:
                r.append(t("Con %d parole per pagina i passaggi sarebbero "
                           "**%d**, cioè **x%.1f**.", lang)
                         % (matematica["target_words_per_page"],
                            matematica["potential_chunks"],
                            matematica["multiplier"]))
            r += ["", "*%s*" % _md_cella(t(matematica["assumption"], lang))]

    delta = referto.get("delta")
    if delta:
        r += ["", "## %s" % t("Rispetto all'esecuzione precedente", lang),
              "", t("Confronto con il %s (v%s).", lang)
              % (delta.get("previous_run"), delta.get("previous_version"))]
        movimenti = ([(t("Complessivo", lang), delta["overall"])]
                     if delta.get("overall") else [])
        movimenti += [(v["area"].replace("mars_", ""), v)
                      for v in delta["scores"] if v["change"]]
        if movimenti:
            r += ["", "| %s | %s | %s | %s |"
                  % (t("Area", lang), t("Prima", lang), t("Dopo", lang),
                     t("Variazione", lang)), "|---|---|---|---|"]
            for nome, voce in movimenti:
                r.append("| %s | %.0f | %.0f | %s |"
                         % (_md_cella(nome), voce["before"], voce["after"],
                            _segno(voce["change"], lang)))
        for titolo, elenco in ((t("Risolti", lang), delta["resolved"]),
                               (t("Nuovi", lang), delta["new"])):
            if not elenco:
                continue
            r += ["", "**%s (%d)**" % (titolo, len(elenco)), ""]
            r += ["- %s" % _md_cella(finding_texts(x, lang)["title"])
                  for x in elenco]
        cambio_k = delta.get("rrf_k_changed")
        if cambio_k:
            r += ["", "*%s*"
                  % (t("Il k della fusione è cambiato, da %d a %d: il "
                       "consenso aggregato delle due esecuzioni non è la "
                       "stessa misura.", lang)
                     % (cambio_k["before"], cambio_k["after"]))]
        if delta.get("by_title_fallback"):
            r += ["", "*%s*"
                  % t("Qualche rilievo non ha una chiave stabile: il "
                      "confronto usa il titolo, ed è più debole.", lang)]
        for cambio in delta.get("measure_changes") or []:
            r += ["", "*%s*"
                  % _md_cella(
                      t("È cambiato che cosa si misura — %s: i numeri si "
                        "muovono anche a sito invariato.", lang)
                      % t(cambio["reason"], lang))]
        for migrazione in delta.get("key_migrations") or []:
            r += ["", "*%s*"
                  % _md_cella(
                      t("Le chiavi %s hanno cambiato forma — %s: in "
                        "quest'area «risolto» e «comparso» non sono "
                        "fatti del sito.", lang)
                      % (migrazione["prefix"],
                         t(migrazione["reason"], lang)))]

    piano = referto.get("remediation") or []
    riepilogo = mars_remediation.riepilogo(piano, referto)
    r += ["", "## %s" % t("Piano di interventi", lang), ""]
    if not piano:
        r.append(t("Nessun rilievo critico o di avvertenza.", lang))
    else:
        r.append(t("%d interventi (%d critici, %d avvertenze) · "
                   "%d quick win.", lang)
                 % (riepilogo["total"], riepilogo["critical"],
                    riepilogo["warning"], riepilogo["quick_wins"]))
        r.append("")
        for voce in piano:
            # Task list GFM: incollata in una issue diventa una
            # checklist spuntabile, ed e' il motivo per cui questo
            # formato esiste.
            testi = finding_texts(voce, lang)
            note = [t(voce["area_label"], lang).split(". ", 1)[-1],
                    t("sforzo: %s", lang)
                    % (t(voce["effort"], lang) if voce["effort"]
                       else t("non dichiarato", lang))]
            if voce["recovery"]:
                note.append(t("+%d punti d'area", lang) % voce["recovery"])
            if voce["index_gain"]:
                note.append(t("indice +%.2f", lang) % voce["index_gain"])
            # Il grassetto del quick win sta FUORI dal corsivo delle
            # note: annidati darebbero `**QUICK WIN***`, e la terza
            # asterisco chiude il corsivo invece del grassetto.
            r.append("- [ ] %s %s — *%s*%s"
                     % (t(_MARCATORE.get(voce["severity"], "[?]"), lang),
                        testi["title"], " · ".join(note),
                        t(" · **QUICK WIN**", lang) if voce["quick_win"]
                        else ""))
            if testi["fix"]:
                r.append("      %s" % testi["fix"])

    r += ["", "## %s" % t("Rilievi per area", lang)]
    for area in referto.get("areas") or []:
        r += ["", "### %s" % t(area.get("label") or area.get("module") or "",
                               lang), ""]
        rilievi = area.get("findings") or []
        if rilievi:
            for rilievo in rilievi:
                r += _md_rilievo(rilievo, lang)
        elif area.get("issues"):
            r += ["- %s" % i for i in _righe_compatte(area, lang)]
        else:
            r.append(t("Nessun rilievo.", lang))

    cit = referto.get("citability") or {}
    if cit.get("profiles"):
        r += ["", "## %s" % t("Profili di citabilità IA", lang), "",
              t("Mercato: %s", lang) % _md_cella(cit.get("market")), "",
              "| %s | %s |" % (t("Assistente", lang), t("Indice", lang)),
              "|---|---|"]
        for assistente, valore in cit["profiles"].items():
            r.append("| %s | %s |"
                     % (_md_cella(assistente),
                        "%.1f" % valore if valore is not None
                        else t("n/d", lang)))
        if cit.get("score") is not None:
            r.append("| **%s** | **%.1f** |" % (t("Indice composito", lang),
                                                cit["score"]))
        r += ["", "*%s*" % _md_cella(t(cit.get("disclaimer") or "", lang))]

    giudizi = giudizi_del_referto(referto)
    if giudizi:
        r += ["", "## %s" % t("Giudizio LLM", lang)]
        for llm in giudizi:
            r += ["", "### %s" % _md_cella(llm.get("provider") or ""), "",
                  t("Modello: %s, su %s passaggi.", lang)
                  % (_md_cella(llm.get("model")),
                     llm.get("chunk_valutati"))]
            if not llm.get("answered"):
                r += [""] + ["- %s" % _md_cella(m)
                             for m in llm.get("issues") or []]
                continue
            if llm.get("score") is not None:
                r += ["", t("Citabilità stimata: **%s/100**", lang)
                      % llm["score"]]
            r += ["", llm.get("motivazione") or ""]
            righe = scarti_leggibili(llm, lang)
            if righe:
                r += [""] + ["- %s **%s**" % (_md_cella(e), v)
                             for e, v in righe]
        if any(scarti_leggibili(g, lang) for g in giudizi):
            r += ["", "*%s*" % _md_cella(
                t("gli scarti confrontano un giudizio con una stima "
                  "euristica", lang))]

    simulazione = referto.get("rrf_simulation") or []
    if simulazione:
        r += ["", "## %s" % t("Simulazione RRF", lang), "",
              "| %s | %s | %s |" % (t("Query", lang), t("Consenso", lang),
                                    t("Passaggio migliore", lang)),
              "|---|---|---|"]
        for voce in simulazione:
            r.append("| %s | %s | %s |"
                     % (_md_cella(voce["query"]),
                        _md_cella(_consenso_leggibile(voce, lang)),
                        _md_cella(voce.get("top_chunk") or "—")))
        sensibilita = sensibilita_leggibile(
            referto.get("rrf_sensitivity") or [], lang)
        if sensibilita:
            r += ["", "%s %s" % (t("al variare di k:", lang),
                                 _md_cella(sensibilita))]
        for diagnosi, divergenti in divergenze_leggibili(
                referto.get("rrf_aggregate") or {}, lang):
            r += ["", "%s" % _md_cella(diagnosi), ""]
            r += ["- `%s`" % _md_cella(v["label"]) for v in divergenti]

    if referto.get("skipped"):
        r += ["", "## %s" % t("Cosa non è stato guardato", lang), ""]
        r += ["- %s" % _md_cella(m) for m in referto["skipped"]]

    r.append("")
    return "\n".join(r)


# ======================================================================
# Vista CSV: i rilievi come righe, per chi li lavora altrove (Fase 6)
# ======================================================================

# `pagine` e `riferimento` erano una colonna sola, `url`, e portava il
# link alla documentazione della regola axe: nel referto completo era
# l'unica valorizzata, con dentro dequeuniversity.com accanto a una
# colonna `sito` che diceva un altro indirizzo. Sono due cose diverse e
# ora sono due colonne (R47).
COLONNE_CSV = ("sito", "area", "gravita", "peso", "titolo", "dettaglio",
               "correzione", "pagine", "riferimento", "sforzo", "quick_win")

# Con che cosa si separano piu' pagine dentro una cella. Uno spazio e
# non il punto e virgola, che e' il DELIMITATORE del file: `csv` la
# cella la quoterebbe correttamente, ma chi apre il CSV in un foglio si
# troverebbe il separatore dentro il testo e crederebbe a un errore.
SEPARATORE_PAGINE = " "

# L'intestazione e il «sì» si traducono come tutto il resto: passano da
# `t()`, quindi stanno nel catalogo della cornice e non in una tabella
# loro. Il resto della riga sono dati del rilievo, che li traduce
# `finding_texts`.

# Il BOM non e' un vezzo: senza, Excel apre un CSV UTF-8 leggendolo
# nella codepage di sistema, e "Accessibilità" diventa "AccessibilitÃ ".
# E' il motivo per cui questa resa esiste — chi vuole i byte puliti ha
# il JSON.
BOM_UTF8 = "\ufeff"

# Il punto e virgola, non la virgola, per la stessa ragione: nelle
# impostazioni italiane di Excel il separatore di lista e' quello, e un
# file con le virgole finisce tutto in una colonna sola.
DELIMITATORE_CSV = ";"


def render_csv(referto: dict, lang: str = LINGUA_CANONICA) -> str:
    """Una riga per rilievo, con lo sforzo dove il piano lo dichiara.

    Comprende i rilievi **derivati** di `mars_citability`: R41 esclude
    i derivati da chi AGGREGA — piano, conteggi, confronti — e li tiene
    per chi li mostra uno per uno, che e' esattamente questo. Il loro
    `params["sources"]` dice a quali aree agganciarli.

    `sforzo` e `quick_win` restano vuoti dove il rilievo non e'
    azionabile: sono proprieta' di una voce del piano, e riportarle su
    un rilievo che il piano non prende in carico direbbe il falso.
    Vuoto, non «no»: un `quick_win` a «no» su un rilievo informativo
    sembrerebbe una valutazione che nessuno ha fatto.
    """
    lang = normalizza_lingua(lang)
    per_chiave = {v["key"]: v for v in referto.get("remediation") or []}
    buffer = io.StringIO()
    # `QUOTE_MINIMAL` e le regole di `csv` fanno il resto: una cella
    # con un punto e virgola, un a-capo o una virgoletta viene quotata
    # e le virgolette raddoppiate. Scriverlo a mano e' il classico
    # punto in cui un fix di ZAP pieno di `"` spezza il file.
    scrittore = csv.writer(buffer, delimiter=DELIMITATORE_CSV,
                           quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    scrittore.writerow([t(c, lang) for c in COLONNE_CSV])
    for area in referto.get("areas") or []:
        for rilievo in area.get("findings") or []:
            voce = per_chiave.get(rilievo.get("key") or "")
            testi = finding_texts(rilievo, lang)
            sforzo = (voce or {}).get("effort") or ""
            scrittore.writerow([
                referto.get("url") or "",
                t(area.get("label") or area.get("module") or "", lang),
                rilievo.get("severity") or "",
                rilievo.get("weight") if rilievo.get("weight") is not None
                else "",
                testi["title"],
                testi["detail"],
                testi["fix"],
                SEPARATORE_PAGINE.join(pagine_del_rilievo(rilievo)),
                rilievo.get("doc_url") or "",
                t(sforzo, lang) if sforzo else "",
                t("sì", lang) if voce and voce.get("quick_win") else "",
            ])
    return BOM_UTF8 + buffer.getvalue()


RENDERERS = {"text": render_text, "json": render_json, "html": render_html,
             "markdown": render_markdown, "csv": render_csv}
