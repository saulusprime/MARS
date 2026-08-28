#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — i pesi e le soglie in un posto solo (I8).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import ast
import glob
import os
import re

import mars_citability
import mars_config
import mars_lexical
import mars_semantic
import mars_tech

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _costanti_dichiarate() -> set:
    return {n for n in dir(mars_config)
            if n.isupper() and not n.startswith("_")}


def _sorgenti() -> list:
    """Ogni modulo del progetto tranne `mars_config` stesso."""
    return [p for p in sorted(glob.glob(os.path.join(RADICE, "mars_*.py")))
            if os.path.basename(p) != "mars_config.py"]


def test_nessun_modulo_riscrive_una_costante_di_mars_config():
    """IL presidio di I8, e l'unico che possa mordere.

    Prima, la scala editoriale era scritta tre volte identica — in
    `mars_tech`, `mars_lexical` e `mars_semantic` — con un commento che
    la dichiarava ripetuta di proposito. Nessun test le legava: se una
    delle tre fosse cambiata, i punteggi di quell'area si sarebbero
    mossi e nulla si sarebbe rotto.

    Riunirle non basta, perche' la stessa divergenza si riottiene
    riscrivendo il nome in un modulo. Questa guardia guarda il CODICE:
    un `PENALITA = {...}` a livello di modulo dove il nome viene da
    `mars_config` e' esattamente il difetto che I8 ha chiuso.

    Non impedisce di usare quei nomi come variabili LOCALI: si guardano
    le sole assegnazioni al livello del modulo, che sono quelle che
    ridefiniscono la costante per tutti i lettori del file.
    """
    dichiarate = _costanti_dichiarate()
    assert len(dichiarate) >= 15, "il file e' quasi vuoto: %d" % len(dichiarate)
    for percorso in _sorgenti():
        with open(percorso, encoding="utf-8") as handle:
            albero = ast.parse(handle.read())
        for nodo in albero.body:
            if isinstance(nodo, ast.AnnAssign):
                bersagli = [nodo.target]
            elif isinstance(nodo, ast.Assign):
                bersagli = nodo.targets
            else:
                continue
            for bersaglio in bersagli:
                nome = getattr(bersaglio, "id", None)
                assert nome not in dichiarate, (
                    "%s:%d: %s e' di mars_config e qui viene riscritta"
                    % (os.path.basename(percorso), nodo.lineno, nome))


def test_la_scala_editoriale_e_un_oggetto_solo():
    """L'altra meta' del presidio: che le tre aree leggano davvero la
    stessa tabella, non tre copie uguali oggi.

    L'identita' e non l'uguaglianza, perche' e' l'identita' che
    distingue «una tabella condivisa» da «tre tabelle che per ora
    coincidono» — ed e' la seconda che il progetto aveva.
    """
    assert (mars_tech.PENALITA
            is mars_lexical.PENALITA
            is mars_semantic.PENALITA
            is mars_config.PENALITA)
    assert mars_config.PENALITA == {"critico": 40, "grave": 20,
                                    "medio": 8, "lieve": 3}, \
        "il valore, non la costante"


def test_la_soglia_delle_risposte_e_quella_della_citabilita():
    """Due soglie sullo stesso numero: sotto 60 `mars_citability`
    dichiara il segnale debole. Se quella semantica fosse 10, il
    referto direbbe «segnale debole» accanto a un'area che non ha nulla
    da segnalare, e nessun errore lo rivelerebbe.

    Fino a I8 stavano in due file e questo test era tutto cio' che le
    teneva insieme. Ora sono un valore solo, e a mordere e' la guardia
    qui sopra: questo resta per il VALORE, che nessuna guardia
    strutturale controlla.
    """
    assert (mars_semantic.SOGLIA_ANSWER_SHAPED
            == mars_citability.SOGLIA_DEBOLE
            == 60), "il valore, non la costante"


def test_ogni_costante_porta_la_sua_ragione():
    """La promessa del file: le ragioni si sono spostate con i valori.

    Un `mars_config` che diventasse un elenco di numeri nudi sarebbe
    peggio della dispersione che ha sostituito — il commento era
    accanto al codice che lo usava, e li' almeno si trovava.
    """
    percorso = os.path.join(RADICE, "mars_config.py")
    with open(percorso, encoding="utf-8") as handle:
        righe = handle.read().split("\n")
    albero = ast.parse("\n".join(righe))
    for nodo in albero.body:
        if isinstance(nodo, ast.AnnAssign):
            nome = getattr(nodo.target, "id", "")
        elif isinstance(nodo, ast.Assign):
            nome = getattr(nodo.targets[0], "id", "")
        else:
            continue
        if not nome.isupper():
            continue
        # Si risale saltando le altre costanti: una COPPIA spiegata da
        # un commento solo — SOGLIA_BUONO e SOGLIA_MEDIO — e' legittima,
        # e pretendere un commento per riga produrrebbe ripetizioni.
        riga = nodo.lineno - 2
        while riga >= 0 and re.match(r"[A-Z_]+[ :]", righe[riga]):
            riga -= 1
        assert riga >= 0 and righe[riga].strip().startswith("#"), \
            "%s non ha una ragione scritta sopra di se'" % nome


def test_mars_config_non_importa_nulla_del_progetto():
    """E' una foglia, e deve restarlo: `mars_core` la legge, quindi un
    import all'indietro sarebbe un ciclo."""
    percorso = os.path.join(RADICE, "mars_config.py")
    with open(percorso, encoding="utf-8") as handle:
        albero = ast.parse(handle.read())
    for nodo in ast.walk(albero):
        moduli = []
        if isinstance(nodo, ast.ImportFrom):
            moduli = [nodo.module or ""]
        elif isinstance(nodo, ast.Import):
            moduli = [alias.name for alias in nodo.names]
        for modulo in moduli:
            assert not modulo.startswith("mars_"), \
                "mars_config importa %s: e' un ciclo" % modulo
