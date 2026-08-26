#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from mars_core import JSON_SCHEMA_VERSION, SEV_CRITICAL, SEV_WARNING

# ======================================================================
# Storico e confronto fra due esecuzioni (U7 / Fase 7 di UPGRADE.md)
# ----------------------------------------------------------------------
# Un referto dice com'e' il sito oggi. Due dicono se sta migliorando, ed
# e' l'unica delle due cose che si puo' portare a una riunione.
#
# Il modello interno c'era gia': `mars_citations.py` tiene lo storico
# del tasso di citazione in JSONL e ne calcola la differenza. Stesso
# stile e stesso schema di file, perche' due modi di fare la stessa cosa
# nello stesso progetto sono uno di troppo.
#
# ----------------------------------------------------------------------
# Perche' una riga compatta e non il referto intero
#
#   Il referto completo pesa centinaia di kilobyte — nel golden sono
#   1.500 righe di JSON — e conservarne uno per esecuzione trasforma lo
#   storico in un archivio che nessuno rilegge. La riga tiene cio' che
#   serve al confronto: i punteggi, il complessivo e l'identita' dei
#   rilievi. Il resto e' gia' nel referto di quel giorno, se lo si e'
#   salvato.
#
# ----------------------------------------------------------------------
# Perche' il confronto e' per CHIAVE
#
#   Dalla Fase 1 ogni rilievo ha una `key` stabile per costruzione, che
#   non contiene mai un valore variabile: `tech.canonical.missing` resta
#   la stessa quando le pagine senza canonical passano da 2 a 117. Il
#   titolo no — e infatti confrontare i titoli direbbe che il rilievo e'
#   stato risolto e uno nuovo e' comparso.
#
#   Per i rilievi SENZA chiave — che nessuno dei nove moduli produce, ma
#   un plugin di terzi puo' — si ripiega sul titolo coi numeri
#   normalizzati, e il delta lo DICHIARA: e' un confronto piu' debole, e
#   chi legge deve saperlo.
# ======================================================================

# Solo cio' su cui si interviene entra nello storico: gli `info`
# descrivono, e un elenco di risolti pieno di note informative
# nasconderebbe le due righe che contano.
GRAVITA_STORICO = (SEV_CRITICAL, SEV_WARNING)

# Il file di default. Punto davanti perche' e' un archivio di lavoro,
# non un deliverable: chi consegna un referto non consegna anche la
# propria storia.
STORICO_PREDEFINITO = ".mars-history.jsonl"

_NUMERI = re.compile(r"\d+")


def _identita(rilievo: dict) -> str:
    """Che cosa rende «lo stesso rilievo» due rilievi di due giorni.

    La chiave, quando c'e'. Altrimenti il titolo coi numeri portati a
    `n`, che e' esattamente cio' che la chiave garantisce per
    costruzione: «2/3 pagine senza canonical» e «117/400 pagine senza
    canonical» sono lo stesso difetto, non uno risolto e uno nuovo.
    """
    chiave = (rilievo.get("key") or "").strip()
    if chiave:
        return chiave
    return "titolo:" + _NUMERI.sub("n", rilievo.get("title") or "")


def riga_storico(referto: dict) -> dict:
    """Il referto ridotto a cio' che serve per confrontarlo col prossimo.

    Esclude i rilievi **derivati** (R41): il confronto fra due
    esecuzioni aggrega, e un `cit.seo.weak` che sparisce perche' l'area
    SEO e' migliorata comparirebbe fra i risolti accanto al rilievo che
    l'ha davvero risolto — due righe per un intervento solo.
    """
    rilievi = []
    for area in referto.get("areas") or []:
        for rilievo in area.get("findings") or []:
            if rilievo.get("severity") not in GRAVITA_STORICO:
                continue
            if (rilievo.get("params") or {}).get("derived"):
                continue
            rilievi.append({"area": area.get("module") or "",
                            "key": rilievo.get("key") or "",
                            "title": rilievo.get("title") or "",
                            "severity": rilievo.get("severity"),
                            # I `params` stanno qui per la stessa
                            # ragione del `title`: il delta si RENDE, e
                            # un rilievo si rende da chiave e params.
                            # Senza, la sezione «rispetto a prima» non
                            # sarebbe traducibile in nessuna lingua e in
                            # nessun momento futuro — nemmeno per i
                            # rilievi risolti, che in questa esecuzione
                            # non esistono piu' e vivono solo qui.
                            # Misurato: la riga raddoppia, da 2,4 a 4,8
                            # KB sul referto sintetico completo. Le
                            # righe scritte prima di U9.2 non li hanno,
                            # e ripiegano sul titolo registrato.
                            "params": dict(rilievo.get("params") or {})})
    complessivo = referto.get("overall") or {}
    return {
        "generated_at": referto.get("generated_at"),
        "url": referto.get("url"),
        "version": referto.get("version"),
        "schema_version": referto.get("schema_version",
                                      JSON_SCHEMA_VERSION),
        "scores": {area.get("module"): area.get("score")
                   for area in referto.get("areas") or []},
        "overall": complessivo.get("score"),
        "findings": rilievi,
    }


# Le migrazioni di chiave, dichiarate.
#
# Una `key` e' l'identita' di un controllo, e il confronto fra due
# esecuzioni ci poggia sopra per intero. Quando la FORMA di una chiave
# cambia, un archivio scritto prima produce una sparizione di massa
# seguita da una comparsa di massa: `compute_delta` le vede come
# «risolti» e «comparsi», e nessuno dei due e' successo sul sito.
#
# Non si puo' salvare il confronto — tradurre le vecchie chiavi nelle
# nuove vorrebbe dire indovinare quale sotto-variante fosse quella
# archiviata — ma si puo' dichiararlo indebolito, che e' la stessa
# scelta di `by_title_fallback` per i rilievi senza chiave.
#
# `since` e' la versione a partire dalla quale vale la forma NUOVA: un
# archivio scritto prima non e' confrontabile su quel prefisso.
MIGRAZIONI_CHIAVE = (
    {"prefix": "sec.zap.",
     "since": "2.9.0",
     "reason": "gli alert ZAP si raggruppano per sotto-variante e non "
               "piu' per sola regola: sec.zap.10038 e' diventato "
               "sec.zap.10038_1, _2, _3 (R39)"},
)

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _semver(versione: object) -> Optional[tuple]:
    """La versione come tupla confrontabile, o None se non si legge.

    None e non `(0, 0, 0)`: la versione arriva da un file scritto da
    un'altra esecuzione, quindi e' dato esterno, e «non si legge» deve
    restare distinguibile da «e' antichissima». Chi chiama sceglie il
    caso peggiore, ma lo sceglie sapendolo.
    """
    trovato = _SEMVER.match(str(versione or "").strip())
    if not trovato:
        return None
    return tuple(int(p) for p in trovato.groups())


def migrazioni_fra(precedente: object, corrente: object) -> List[dict]:
    """Le migrazioni di chiave avvenute fra due versioni.

    Una versione precedente **illeggibile** fa dichiarare tutte le
    migrazioni: non si puo' concludere che l'archivio sia recente
    guardando una stringa che non si capisce, e un caveat di troppo si
    legge, uno mancante no.
    """
    prima = _semver(precedente)
    dopo = _semver(corrente)
    esito = []
    for voce in MIGRAZIONI_CHIAVE:
        soglia = _semver(voce["since"])
        if soglia is None:
            continue
        # La migrazione riguarda questo confronto solo se l'esecuzione
        # CORRENTE la ha gia' applicata: due archivi entrambi vecchi si
        # confrontano fra loro senza problemi.
        if dopo is not None and dopo < soglia:
            continue
        if prima is None or prima < soglia:
            esito.append(dict(voce))
    return esito


def compute_delta(precedente: Optional[dict],
                  corrente: dict) -> Optional[dict]:
    """Che cosa e' cambiato fra due esecuzioni.

    None alla prima: un delta con tutto a zero non e' un delta, e le
    viste devono poter tacere invece di mostrare una sezione vuota.

    I punteggi si confrontano solo dove **entrambe** le esecuzioni
    hanno un numero: un'area misurata ieri e non oggi non e' peggiorata
    di quanto valeva: non e' stata guardata. La differenza sarebbe la
    bugia piu' facile di tutta la fase, ed e' la stessa distinzione
    fra «non misurato» e «zero» che il referto fa dappertutto.
    """
    if not precedente:
        return None

    prima = {a: s for a, s in (precedente.get("scores") or {}).items()
             if isinstance(s, (int, float))}
    dopo = {a: s for a, s in (corrente.get("scores") or {}).items()
            if isinstance(s, (int, float))}
    punteggi = []
    for area in dopo:
        if area not in prima:
            continue
        punteggi.append({"area": area, "before": prima[area],
                         "after": dopo[area],
                         "change": round(dopo[area] - prima[area], 1)})
    punteggi.sort(key=lambda v: (-abs(v["change"]), v["area"]))

    vecchi = {_identita(f): f for f in precedente.get("findings") or []}
    nuovi = {_identita(f): f for f in corrente.get("findings") or []}
    risolti = [f for i, f in vecchi.items() if i not in nuovi]
    comparsi = [f for i, f in nuovi.items() if i not in vecchi]

    complessivo = None
    if isinstance(precedente.get("overall"), (int, float)) and \
            isinstance(corrente.get("overall"), (int, float)):
        complessivo = {"before": precedente["overall"],
                       "after": corrente["overall"],
                       "change": round(corrente["overall"]
                                       - precedente["overall"], 1)}

    # Il confronto e' piu' debole se qualche rilievo non aveva chiave:
    # si dichiara invece di lasciarlo intuire.
    senza_chiave = [i for i in list(vecchi) + list(nuovi)
                    if i.startswith("titolo:")]
    return {
        "previous_run": precedente.get("generated_at"),
        "previous_version": precedente.get("version"),
        "scores": punteggi,
        "overall": complessivo,
        "resolved": risolti,
        "new": comparsi,
        # `False` e non assente: chi legge il delta deve poter
        # distinguere «confronto pieno» da «non lo sappiamo».
        "by_title_fallback": bool(senza_chiave),
        # Le famiglie di chiavi che hanno cambiato forma fra le due
        # esecuzioni: li' «risolto» e «comparso» non sono fatti del
        # sito. Lista vuota e non assente, per la stessa ragione.
        "key_migrations": migrazioni_fra(precedente.get("version"),
                                         corrente.get("version")),
    }


# ----------------------------------------------------------------------
# L'unica parte con I/O
# ----------------------------------------------------------------------

def percorso_storico(output: Optional[str] = None) -> str:
    """Dove sta lo storico: accanto al referto, o nella cartella corrente."""
    if output:
        return os.path.join(os.path.dirname(os.path.abspath(output)),
                            STORICO_PREDEFINITO)
    return STORICO_PREDEFINITO


def leggi_ultima_esecuzione(percorso: str, url: str) -> Optional[dict]:
    """L'ultima riga dello storico per QUEL sito, o None.

    Filtra per URL perche' un solo file puo' raccogliere piu' siti — e
    confrontare due siti diversi darebbe un delta pieno di rilievi
    «risolti» che nessuno ha toccato.

    Non solleva mai: lo storico e' un archivio di comodo, e un file
    illeggibile o una riga corrotta non devono far fallire un audit
    che e' gia' stato fatto. Restituisce None e chi lo riceve mostra la
    prima esecuzione.
    """
    ultima = None
    try:
        with open(percorso, encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    voce = json.loads(riga)
                except ValueError:
                    # Una riga corrotta non invalida le altre: e' il
                    # vantaggio del JSONL sul JSON, ed e' la ragione
                    # per cui lo storico ha questo formato.
                    continue
                if isinstance(voce, dict) and voce.get("url") == url:
                    ultima = voce
    except OSError:
        return None
    return ultima


def appendi_storico(percorso: str, riga: dict) -> bool:
    """Aggiunge una riga allo storico. Vero se ci e' riuscito.

    **Append-only**: nessuna riga viene mai riscritta, e il file resta
    leggibile anche se un'esecuzione si interrompe a meta'.

    Un fallimento non e' un errore dell'audit: il referto e' gia'
    prodotto, e perdere una riga di archivio non vale il codice di
    uscita. Chi chiama lo dichiara all'utente.
    """
    try:
        with open(percorso, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(riga, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def leggi_storico(percorso: str, url: Optional[str] = None) -> List[dict]:
    """Tutte le righe, eventualmente di un solo sito. Mai un'eccezione."""
    righe: List[Dict[str, object]] = []
    try:
        with open(percorso, encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    voce = json.loads(riga)
                except ValueError:
                    continue
                if isinstance(voce, dict) and (url is None
                                               or voce.get("url") == url):
                    righe.append(voce)
    except OSError:
        return []
    return righe
