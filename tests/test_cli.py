#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — interfaccia da riga di comando.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

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
