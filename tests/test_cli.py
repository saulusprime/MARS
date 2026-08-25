#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — interfaccia da riga di comando.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys

import pytest

import mars_audit
from mars_citability import MERCATI


def _aiuto() -> str:
    esito = subprocess.run([sys.executable, "mars_audit.py", "--help"],
                           capture_output=True, text=True, timeout=60)
    assert esito.returncode == 0
    return esito.stdout


def _comandi_negli_esempi() -> list:
    """I comandi dell'epilogo, con le continuazioni riunite."""
    testo = mars_audit.ESEMPI.replace("\\\n", " ")
    return [riga.strip() for riga in testo.splitlines()
            if riga.strip().startswith("mars_audit.py")]


@pytest.fixture(scope="module")
def aiuto():
    return _aiuto()


# ----------------------------------------------------------------------
# L'esecutore dei moduli (R22)
# ----------------------------------------------------------------------

def _run_audit_con(modulo_finto, monkeypatch, capsys, contesto):
    """Esegue run_audit con un solo modulo, quello dato."""
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica")])
    monkeypatch.setattr(mars_audit, "load_external_module",
                        lambda nome: modulo_finto)
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: contesto)
    codice = mars_audit.run_audit("https://x/", 1, "none", "global")
    return codice, capsys.readouterr().out


class _ModuloCheSolleva:
    @staticmethod
    def audit(context):
        raise ValueError("divisione per zero")


class _ModuloSenzaAudit:
    pass


class _ModuloCheRestituisceNulla:
    @staticmethod
    def audit(context):
        return None      # il `return` dimenticato


@pytest.mark.parametrize("modulo, atteso", [
    (_ModuloCheSolleva, "divisione per zero"),
    (_ModuloSenzaAudit, "manca la funzione audit()"),
    (_ModuloCheRestituisceNulla, "invece di un dict"),
])
def test_area_fallita_finisce_nel_referto(modulo, atteso, monkeypatch,
                                          capsys, contesto):
    """Regressione R22: un modulo che rompe spariva dal referto.

    L'errore veniva soltanto stampato, quindi l'area non entrava in
    results e build_report non la nominava affatto: con --output il
    file consegnato non portava traccia dell'area persa. L'API
    registrava gia' l'errore; la CLI no.
    """
    codice, uscita = _run_audit_con(modulo, monkeypatch, capsys, contesto)
    assert codice == 0, "il referto viene comunque prodotto"
    assert "1. Tecnica" in uscita
    assert "errore del modulo" in uscita
    assert atteso in uscita


def test_un_modulo_rotto_non_ferma_gli_altri(monkeypatch, capsys, contesto):
    """Il gestore per-modulo esiste proprio perche' un plugin guasto
    non debba far perdere il resto dell'audit."""
    class Buono:
        @staticmethod
        def audit(context):
            return {"score": 80, "issues": []}

    moduli = {"mars_tech": _ModuloCheSolleva, "mars_seo": Buono}
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica"), ("mars_seo", "2. SEO")])
    monkeypatch.setattr(mars_audit, "load_external_module", moduli.get)
    monkeypatch.setattr(mars_audit, "build_context", lambda *a, **k: contesto)
    mars_audit.run_audit("https://x/", 1, "none", "global")
    uscita = capsys.readouterr().out
    assert "errore del modulo" in uscita
    assert "80/100" in uscita


def test_ogni_parametro_e_documentato(aiuto):
    for flag in ("--max-pages", "--queries", "--embeddings", "--market",
                 "--delay", "--timeout", "--format", "--output", "--llm",
                 "--i-own-this-domain", "--version"):
        assert flag in aiuto, "manca %s" % flag


def test_ogni_parametro_mostra_valori_o_esempio():
    """Un help che dice solo "numero massimo di pagine" non aiuta:
    servono i valori ammessi o un esempio.

    Si interroga il parser invece di elencare eccezioni a mano: un
    interruttore senza argomento non ha valori da esemplificare, e la
    distinzione la conosce argparse.
    """
    for azione in mars_audit.costruisci_parser()._actions:
        if azione.nargs == 0 or not azione.option_strings:
            continue  # interruttore, --help o --version
        if azione.dest in ("help", "version"):
            continue
        testo = azione.help or ""
        assert ("Esempi:" in testo or "Esempio:" in testo
                or "Valori:" in testo or azione.choices), \
            "%s non mostra ne' valori ammessi ne' un esempio" % (
                azione.option_strings[0])


def test_gli_esempi_documentati_sono_validi():
    """Regressione R12: il README documentava comandi che fallivano.

    Ogni esempio dell'epilogo viene dato in pasto al parser reale: se
    un flag cambia nome o sparisce, il test se ne accorge prima di chi
    legge l'aiuto.
    """
    comandi = _comandi_negli_esempi()
    assert len(comandi) >= 5, "l'aiuto deve mostrare piu' di un esempio"
    parser = mars_audit.costruisci_parser()
    for comando in comandi:
        argomenti = shlex.split(comando)[1:]
        parser.parse_args(argomenti)


def test_i_mercati_nell_aiuto_non_divergono(aiuto):
    """I valori riconosciuti si leggono da MERCATI, non si riscrivono."""
    for mercato in MERCATI:
        assert mercato in aiuto


def test_aiuto_dichiara_codici_di_uscita_e_ambiente(aiuto):
    assert "codici di uscita" in aiuto
    for variabile in ("ANTHROPIC_API_KEY", "HF_TOKEN", "ZAP_PROXY"):
        assert variabile in aiuto


def test_aiuto_avverte_su_spesa_e_attacco(aiuto):
    assert "SPESA" in aiuto
    assert "payload d'attacco" in aiuto


def test_version():
    esito = subprocess.run([sys.executable, "mars_audit.py", "--version"],
                           capture_output=True, text=True, timeout=60)
    assert esito.returncode == 0
    assert mars_audit.__version__ in esito.stdout


def test_url_obbligatorio():
    esito = subprocess.run([sys.executable, "mars_audit.py"],
                           capture_output=True, text=True, timeout=60)
    assert esito.returncode == 2


@pytest.mark.parametrize("argomenti", [
    ["https://x.it", "--format", "inventato"],
    ["https://x.it", "--llm", "forse"],
    ["https://x.it", "--max-pages", "molte"],
])
def test_valori_non_ammessi_rifiutati(argomenti):
    with pytest.raises(SystemExit):
        mars_audit.costruisci_parser().parse_args(argomenti)


# ----------------------------------------------------------------------
# U7: lo storico, dalla riga di comando
# ----------------------------------------------------------------------

class _ModuloConPunteggio:
    @staticmethod
    def audit(context):
        return {"score": 57, "issues": [], "findings": []}


def _audit_con_storico(monkeypatch, capsys, contesto, percorso):
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica")])
    monkeypatch.setattr(mars_audit, "load_external_module",
                        lambda nome: _ModuloConPunteggio)
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: contesto)
    codice = mars_audit.run_audit("https://x/", 1, "none", "global",
                                  formato="json", storico=percorso)
    return codice, capsys.readouterr().out


def test_la_cli_scrive_lo_storico(monkeypatch, capsys, contesto, tmp_path):
    percorso = str(tmp_path / "storico.jsonl")
    codice, uscita = _audit_con_storico(monkeypatch, capsys, contesto,
                                        percorso)
    assert codice == 0
    assert "Storico aggiornato" in uscita
    righe = open(percorso, encoding="utf-8").read().strip().split("\n")
    assert len(righe) == 1
    assert json.loads(righe[0])["scores"] == {"mars_tech": 57}


def test_la_cli_rilegge_lo_storico_e_produce_il_delta(monkeypatch, capsys,
                                                      contesto, tmp_path):
    """Il giro completo: la prima esecuzione scrive, la seconda
    confronta. E' l'unico posto dove le due meta' si toccano."""
    percorso = str(tmp_path / "storico.jsonl")
    _audit_con_storico(monkeypatch, capsys, contesto, percorso)
    _, uscita = _audit_con_storico(monkeypatch, capsys, contesto, percorso)
    referto = json.loads(uscita[uscita.index("{"):uscita.rindex("}") + 1])
    assert referto["delta"] is not None
    assert referto["delta"]["previous_run"] is not None
    assert len(open(percorso, encoding="utf-8").read().strip().split("\n")) == 2


def test_senza_storico_la_cli_non_lo_tocca(monkeypatch, capsys, contesto,
                                           tmp_path):
    """`--no-history` passa None: nessuna lettura, nessuna scrittura."""
    percorso = str(tmp_path / "storico.jsonl")
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica")])
    monkeypatch.setattr(mars_audit, "load_external_module",
                        lambda nome: _ModuloConPunteggio)
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: contesto)
    mars_audit.run_audit("https://x/", 1, "none", "global", formato="json",
                         storico=None)
    assert not os.path.exists(percorso)


def test_uno_storico_non_scrivibile_non_fa_fallire_l_audit(monkeypatch,
                                                           capsys, contesto,
                                                           tmp_path):
    """Il referto e' gia' prodotto: perdere una riga di archivio non
    vale il codice di uscita. Lo si dichiara e si va avanti."""
    cartella = tmp_path / "non" / "esiste"
    codice, uscita = _audit_con_storico(monkeypatch, capsys, contesto,
                                        str(cartella / "s.jsonl"))
    assert codice == 0
    assert "Impossibile scrivere lo storico" in uscita
