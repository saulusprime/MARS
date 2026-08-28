#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from mars_config import SOGLIA_DEBOLE
from mars_core import SEV_INFO, Finding

# ======================================================================
# AVVERTENZA
# ----------------------------------------------------------------------
# I pesi di questo file sono STIME EURISTICHE DICHIARATE, non
# comportamento documentato dai vendor. Nessun fornitore di assistenti
# IA pubblica come seleziona le fonti da citare: quello che segue e' un
# modello esplicito e discutibile, messo qui in chiaro proprio perche'
# sia discusso e corretto. Un profilo alto non garantisce una citazione,
# e uno basso non la esclude.
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
    #                            tec seo rec ans dat acc sic
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

# Da quali aree viene ogni segnale. Serve ai rilievi: un rilievo
# derivato senza indirizzo e' una lamentela, e con l'indirizzo la Fase 4
# puo' agganciarlo ai rilievi veri che lo spiegano.
#
# E' una SECONDA dichiarazione della corrispondenza che `raccogli_segnali`
# esprime leggendo i moduli — due implementazioni della stessa cosa, che
# e' esattamente cio' che diverge in silenzio. A tenerle insieme non c'e'
# un accorgimento ma un test: costruisce i `results` a partire da questa
# tabella e verifica che il segnale corrispondente diventi misurato.
# Riscrivere `raccogli_segnali` per leggerla e' possibile, ma sarebbe un
# refactor a comportamento invariato dentro un commit che cambia il
# comportamento, e l'ordine del suo dict letterale e' dato osservabile.
ORIGINE: Dict[str, Tuple[str, ...]] = {
    "tecnica": ("mars_tech",),
    "seo": ("mars_seo",),
    "dati_strutturati": ("mars_schema",),
    "accessibilita": ("mars_wcag",),
    "sicurezza": ("mars_wapt",),
    "recuperabilita": ("mars_lexical", "mars_semantic"),
    "answer_shaped": ("mars_semantic",),
}


def _derivato(chiave: str, testo: str, **params: object) -> dict:
    """Un rilievo di quest'area: descrive, non quantifica.

    `params["derived"] = True` su OGNI rilievo, ed e' un invariante
    d'area, non un giudizio caso per caso: mars_citability non guarda
    il sito, rilegge i punteggi delle altre aree. Chi consuma i rilievi
    per SOMMARLI — piano di interventi, conteggi per gravita', confronto
    fra due esecuzioni — deve saltare i derivati, altrimenti conta due
    volte lo stesso difetto. E' la decisione D3 portata dentro il dato.

    Nessun rilievo porta mai `penalty`, e l'assenza e' il significato:
    un segnale debole E' un difetto del sito, ma quantificarlo tocca
    all'area che l'ha misurato, che lo fa con molto piu' dettaglio.
    Sarebbe calcolabile — il composito e' una media pesata, quindi
    lineare come quella di Lighthouse — e proprio per questo non va
    messo: sarebbe lo stesso deficit espresso in una seconda unita', e
    un numero che somiglia a una penalita', dentro un elenco di rilievi,
    prima o poi verrebbe sommato alle penalita'.

    Tutti `info`, peso 1.0. La severita' e' l'asse su cui la Fase 4
    ordinera' il piano, e su quell'asse una sintesi non deve MAI
    scavalcare la misura che sintetizza: "Segnale debole: Sicurezza
    (50/100)" e "[ZAP:High] SQL injection (3 URL)" descrivono lo stesso
    difetto, e il secondo porta regola, URL e soluzione. Tenere i
    derivati al gradino piu' basso rende l'ordinamento per gravita'
    monotono rispetto alla derivazione.

    `source_severity` resta vuoto ovunque: nessun altro modulo ha
    espresso un giudizio su QUESTO rilievo.
    """
    return Finding(area="mars_citability", severity=SEV_INFO,
                   key=chiave, title=testo,
                   params=dict(params, derived=True)).as_dict()


def _rilievo_segnale(segnale: str, esito: str, testo: str,
                     **params: object) -> dict:
    """Un rilievo su un segnale, con l'indirizzo di chi l'ha misurato.

    La chiave e' `cit.<segnale>.<esito>` e NON passa da
    `chiave_esterna()`: quella funzione difende la profondita' fissa da
    un id ostile — axe, ZAP, Lighthouse — al prezzo dell'iniettivita'
    (R39). Qui il vocabolario e' scritto in questo file, e un refuso
    deve far fallire un test, non essere ripulito in silenzio.

    Famiglia = soggetto, esito = verdetto, come `sd.jsonld.block_empty`
    e `sec.headers.hsts_missing`: cosi' lo stesso segnale puo' avere due
    esiti — `weak` e `unmeasured` — sotto la stessa famiglia.
    """
    return _derivato(
        "cit.%s.%s" % (segnale, esito), testo,
        signal=segnale, label=SEGNALI[segnale],
        # Sempre una LISTA, anche di un elemento: `recuperabilita` ne ha
        # due, e un campo a volte stringa e a volte lista rompe un
        # consumatore in silenzio. E lista, non tupla: `as_dict()` non
        # converte, e il dato avrebbe tipo diverso in Python e in JSON.
        sources=list(ORIGINE[segnale]), **params)


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
                           "completo (CLI o POST /audit/full)"],
                "findings": [_derivato(
                    "cit.status.no_results",
                    "Richiede le altre aree: eseguire l'audit completo "
                    "(CLI o POST /audit/full)")]}

    nome_mercato = (context.get("market") or "global").lower()
    mercato = MERCATI.get(nome_mercato)
    issues = []
    rilievi: List[dict] = []
    if mercato is None:
        issues.append("Mercato '%s' sconosciuto: uso 'global' (noti: %s)"
                      % (nome_mercato, ", ".join(sorted(MERCATI))))
        # Il rilievo si costruisce PRIMA della riassegnazione: due righe
        # piu' sotto `nome_mercato` vale gia' "global", e `requested`
        # direbbe che l'utente ha chiesto proprio cio' che ha ottenuto.
        rilievi.append(_derivato(
            "cit.status.unknown_market",
            "Mercato '%s' sconosciuto: uso 'global'" % nome_mercato,
            requested=nome_mercato, used="global",
            known=sorted(MERCATI)))
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
    # Una issue sola che li elenca tutti, un rilievo per segnale: la
    # cardinalita' delle due viste puo' divergere, il contenuto e
    # l'ordine no. Aggregarli in un rilievo unico toglierebbe l'unica
    # informazione azionabile del caso — QUALE strumento manca — e
    # renderebbe la chiave incomparabile fra due esecuzioni.
    rilievi += [_rilievo_segnale(s, "unmeasured",
                                 "Segnale non misurato: %s" % SEGNALI[s])
                for s, v in segnali.items() if v is None]
    # Il nome interno del segnale entra come TERZO elemento, non come
    # secondo: l'ordinamento pareggia sull'etichetta italiana, e le
    # etichette sono uniche, quindi il terzo non viene mai confrontato.
    # Metterlo al posto dell'etichetta cambierebbe quale segnale
    # sopravvive al taglio `deboli[:2]`, cioe' il testo delle issues.
    deboli = sorted((v, SEGNALI[s], s) for s, v in segnali.items()
                    if v is not None and v < SOGLIA_DEBOLE)
    for valore, etichetta, _ in deboli[:2]:
        issues.append("Segnale debole: %s (%.0f/100)" % (etichetta, valore))
    # Le issues ne mostrano due, il dato li porta tutti: e' la stessa
    # asimmetria dei cinque alert ZAP e delle cinque violazioni axe.
    rilievi += [_rilievo_segnale(
        s, "weak", "Segnale debole: %s (%.0f/100)" % (etichetta, valore),
        value=valore, threshold=SOGLIA_DEBOLE)
        for valore, etichetta, s in deboli]

    if composito is None:
        # In coda, ed e' una CONCLUSIONE, non una premessa: i segnali non
        # misurati che lo precedono ne sono la causa. Non ha una issue
        # corrispondente — quel ramo e' muto da sempre — ed e' la seconda
        # volta nella fase che il dato dice qualcosa che la vista compatta
        # tace. Non e' deducibile dai sette `unmeasured`: `profilo()`
        # restituisce None anche quando i pesi si annullano, e dedurlo
        # significherebbe reimplementarla nel consumatore.
        rilievi.append(_derivato("cit.status.no_composite",
                                 "Indice composito non calcolabile"))

    return {
        "score": composito,
        # Senza un solo segnale misurabile il composito non esiste, e
        # va DICHIARATO: score None senza status era un terzo stato che
        # il vocabolario del referto non contempla, e che le viste
        # collassavano su "non misurato" senza distinguerlo da un'area
        # mai eseguita.
        "status": None if composito is not None else "unavailable",
        "issues": issues,
        # Nell'ordine in cui le issues raccontano lo stesso audit, e
        # proseguendo dove le issues si fermano. Nessun `sorted` per
        # gravita': sono tutti `info` a peso 1.0, quindi riordinarli
        # sarebbe un no-op che nasconde il criterio vero.
        "findings": rilievi,
        "market": nome_mercato,
        "profiles": profili,
        "signals": {SEGNALI[s]: v for s, v in segnali.items()},
        "disclaimer": DISCLAIMER,
    }
