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

# I sottoprocessi vanno lanciati dalla radice del repo, non dalla cwd di
# chi invoca pytest: `mars_audit.py` e' un percorso relativo, e da
# un'altra directory Python esce con rc 2 per «can't open file» — lo
# stesso codice che argparse usa per un argomento mancante. Il test
# dell'URL obbligatorio passava cosi' per la ragione sbagliata (R33).
# Percorsi assoluti e non una fixture `chdir`: e' l'idioma gia' in casa
# (test_i18n, test_core, test_report), e una chdir globale
# colliderebbe con chi la cwd la cambia di proposito.
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _aiuto() -> str:
    esito = subprocess.run([sys.executable, "mars_audit.py", "--help"],
                           capture_output=True, text=True, timeout=60,
                           cwd=RADICE)
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
                           capture_output=True, text=True, timeout=60,
                           cwd=RADICE)
    assert esito.returncode == 0
    assert mars_audit.__version__ in esito.stdout


def test_url_obbligatorio():
    """R33: il solo `rc == 2` non distingue due cause diverse.

    Argparse esce con 2 per un argomento mancante, e Python esce con 2
    anche per «can't open file»: da un'altra directory questo test
    passava senza aver mai raggiunto il parser. Le due asserzioni sullo
    stderr ancorano la causa, e restano rosse se qualcuno rimette il
    percorso relativo.

    Si asserisce sul metavar `URL`, che e' nostro, e non sulla prosa di
    argparse, che passa da gettext e cambia con il locale.
    """
    esito = subprocess.run([sys.executable, "mars_audit.py"],
                           capture_output=True, text=True, timeout=60,
                           cwd=RADICE)
    assert esito.returncode == 2
    assert "URL" in esito.stderr
    assert "can't open file" not in esito.stderr


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


def test_cli_max_children_arriva_al_contesto(monkeypatch):
    """R56: sfuggita a due mutazioni — togliere `max_children` dalla
    catena della CLI lasciava verde tutto, perche' nessun test
    attraversava la tubatura fra il flag e il modulo.

    Il valore ha una strada sola e lunga: argparse -> run_audit ->
    build_context -> context -> mars_wapt -> ZapClient. Ogni anello
    rotto e' silenzioso: lo spider gira lo stesso, senza tetto.
    """
    visti = {}

    def finto(url, max_pages=10, *a, **k):
        visti.update(k)
        return None

    monkeypatch.setattr(mars_audit, "build_context", finto)
    mars_audit.run_audit("https://x/", 1, "none", "global", max_children=37)
    assert visti.get("max_children") == 37


def test_cli_ogni_parametro_del_parser_e_letto_al_punto_di_ingresso():
    """Guardia statica: un `args.<qualcosa>` mai letto in `main()` e'
    un flag che si accetta dalla riga di comando, non fa nulla, e non
    da' errore.

    Vale per ogni parametro insieme e non per uno solo: e' lo stesso
    ragionamento del test che verifica con `ast` che nessun modulo
    passi un `k` suo alla fusione RRF. Guarda il CODICE, non il dato.

    Non basta pero' da sola — le mutazioni di R57 lo hanno dimostrato:
    dice che il valore e' LETTO, non che sia usato per qualcosa. Per
    quello servono i test che eseguono `main()`, possibili da quando
    non e' piu' un blocco `if __name__`.
    """
    import inspect
    import re

    ingresso = inspect.getsource(mars_audit.main)
    letti = set(re.findall(r"args\.([a-z_]+)", ingresso))
    dichiarati = {a.dest for a in mars_audit.costruisci_parser()._actions}
    dichiarati -= {"help", "version"}   # argparse li gestisce da se'
    assert dichiarati <= letti, \
        "parametri accettati e mai letti: %s" % sorted(dichiarati - letti)


def test_cli_il_flag_max_children_esiste_e_ha_un_default(monkeypatch):
    """L'anello prima: che argparse lo legga davvero, e che il
    predefinito sia quello di ZAP — 0, nessun tetto — perche' un
    default nostro cambierebbe in silenzio il comportamento di chi
    dichiara il dominio."""
    parser = mars_audit.costruisci_parser()
    assert parser.parse_args(["https://x/"]).max_children == 0
    assert parser.parse_args(["https://x/",
                              "--max-children", "12"]).max_children == 12


def test_cli_le_credenziali_del_file_arrivano_al_contesto(monkeypatch, tmp_path):
    """R57: la CLI non aveva ALCUN modo di passare una chiave — solo
    variabili d'ambiente — mentre l'API le accetta dal corpo. La
    tubatura e' la stessa di `--max-children`, e la sua rottura sarebbe
    altrettanto silenziosa: l'audit gira, l'area 9 dice «nessuna
    credenziale», e nessuno sa perche'."""
    visti = {}

    def finto(url, max_pages=10, *a, **k):
        visti.update(k)
        return None

    monkeypatch.setattr(mars_audit, "build_context", finto)
    mars_audit.run_audit("https://x/", 1, "none", "global",
                         credentials={"anthropic_api_key": "sk-ant-finta"})
    assert visti.get("credentials") == {"anthropic_api_key": "sk-ant-finta"}


def test_cli_il_flag_credentials_esiste_e_non_ha_un_default(tmp_path):
    """Senza il flag valgono le variabili d'ambiente, come prima: il
    flag aggiunge una strada, non ne toglie una."""
    parser = mars_audit.costruisci_parser()
    assert parser.parse_args(["https://x/"]).credentials is None
    assert parser.parse_args(
        ["https://x/", "--credentials", "chiavi.json"]).credentials \
        == "chiavi.json"


def test_cli_main_propaga_le_credenziali_fino_a_run_audit(monkeypatch,
                                                          tmp_path, capsys):
    """`main()` esiste come funzione proprio per questo: due mutazioni
    di R57 sono sopravvissute perche' il codice fra argparse e
    `run_audit` non era eseguibile da un test."""
    visti = {}
    monkeypatch.setattr(mars_audit, "run_audit",
                        lambda *a, **k: visti.update(k) or 0)
    percorso = tmp_path / "chiavi.json"
    percorso.write_text('{"hf_token": "hf-finto"}', encoding="utf-8")
    percorso.chmod(0o600)
    assert mars_audit.main(["https://x/", "--credentials", str(percorso)]) == 0
    assert visti["credentials"] == {"hf_token": "hf-finto"}


def test_cli_main_si_ferma_su_un_file_di_chiavi_illeggibile(monkeypatch,
                                                            tmp_path, capsys):
    """E NON ripiega sulle variabili d'ambiente: chi passa
    `--credentials` ha detto quali chiavi vuole usare, e usarne altre
    in silenzio e' la stessa classe di difetto che ha aperto la voce —
    un audit che gira e dichiara «nessuna credenziale» senza che si
    capisca perche'."""
    partito = []
    monkeypatch.setattr(mars_audit, "run_audit",
                        lambda *a, **k: partito.append(1) or 0)
    codice = mars_audit.main(["https://x/", "--credentials",
                              str(tmp_path / "assente.json")])
    assert codice == mars_audit.EXIT_USO
    assert not partito, "l'audit non deve nemmeno cominciare"
    assert "assente.json" in capsys.readouterr().out


def test_cli_main_senza_flag_non_inventa_credenziali(monkeypatch):
    """Senza `--credentials` il contesto non porta chiavi, e valgono le
    variabili d'ambiente come prima: il flag aggiunge una strada."""
    visti = {}
    monkeypatch.setattr(mars_audit, "run_audit",
                        lambda *a, **k: visti.update(k) or 0)
    mars_audit.main(["https://x/"])
    assert visti["credentials"] is None
