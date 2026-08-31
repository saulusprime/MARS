#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — interfaccia da riga di comando.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import ast
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
    # I due canali interi, non il solo stdout: da R59 dicono cose
    # diverse — il referto e la diagnostica — e un test deve dire quale
    # dei due sta guardando.
    return codice, capsys.readouterr()


def test_la_cli_scrive_lo_storico(monkeypatch, capsys, contesto, tmp_path):
    percorso = str(tmp_path / "storico.jsonl")
    codice, uscita = _audit_con_storico(monkeypatch, capsys, contesto,
                                        percorso)
    assert codice == 0
    assert "Storico aggiornato" in uscita.err
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
    # `json.loads` sul canale INTERO, senza piu' ritagliare fra la
    # prima graffa e l'ultima: era il rattoppo che il difetto R59
    # imponeva a chiunque rileggesse il referto da stdout.
    referto = json.loads(uscita.out)
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
    assert "Impossibile scrivere lo storico" in uscita.err


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
    altrettanto silenziosa: l'audit gira, l'area 10 dice «nessuna
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
    assert "assente.json" in capsys.readouterr().err


def test_cli_main_senza_flag_non_inventa_credenziali(monkeypatch):
    """Senza `--credentials` il contesto non porta chiavi, e valgono le
    variabili d'ambiente come prima: il flag aggiunge una strada."""
    visti = {}
    monkeypatch.setattr(mars_audit, "run_audit",
                        lambda *a, **k: visti.update(k) or 0)
    mars_audit.main(["https://x/"])
    assert visti["credentials"] is None


def test_cli_il_flag_rrf_k_esiste_e_ha_il_default_del_paper():
    parser = mars_audit.costruisci_parser()
    assert parser.parse_args(["https://x/"]).rrf_k == 60
    assert parser.parse_args(["https://x/", "--rrf-k", "10"]).rrf_k == 10


def test_cli_un_k_negativo_e_un_errore_d_uso(capsys):
    """`1/(k + rank + 1)` con k=-1 e il primo posto divide per zero:
    l'audit morirebbe dentro la fusione, a scansione fatta."""
    with pytest.raises(SystemExit):
        mars_audit.costruisci_parser().parse_args(["https://x/",
                                                   "--rrf-k", "-1"])
    assert "rrf-k" in capsys.readouterr().err


def test_cli_rrf_k_arriva_al_contesto(monkeypatch):
    """L'anello che a `--max-children` era sfuggito due volte: un flag
    che si ferma prima di `build_context` e' indistinguibile da uno che
    funziona, e nessun test lo attraversava."""
    visti = {}
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: visti.update(k) or None)
    mars_audit.run_audit("https://x/", 1, "none", "global", rrf_k=7)
    assert visti.get("rrf_k") == 7
    mars_audit.main(["https://x/", "--rrf-k", "11"])
    assert visti.get("rrf_k") == 11, "e anche dalla riga di comando"


def test_cli_il_form_factor_esiste_e_arriva_al_contesto(monkeypatch):
    """I16: come per `--rrf-k`, un flag che si ferma prima di
    `build_context` e' indistinguibile da uno che funziona."""
    parser = mars_audit.costruisci_parser()
    assert parser.parse_args(["https://x/"]).form_factor == "mobile"
    assert parser.parse_args(
        ["https://x/", "--form-factor", "desktop"]).form_factor == "desktop"
    visti = {}
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: visti.update(k) or None)
    mars_audit.main(["https://x/", "--form-factor", "desktop"])
    assert visti.get("form_factor") == "desktop"
    mars_audit.main(["https://x/"])
    assert visti.get("form_factor") == "mobile"


def test_cli_un_form_factor_ignoto_e_un_errore_d_uso(capsys):
    """`choices` ferma il valore prima della scansione: Lighthouse non
    ha un preset `tablet`, e scoprirlo a crawl finito costerebbe
    l'intero giro di richieste al sito."""
    with pytest.raises(SystemExit):
        mars_audit.costruisci_parser().parse_args(
            ["https://x/", "--form-factor", "tablet"])
    assert "form-factor" in capsys.readouterr().err

# ----------------------------------------------------------------------
# R59: diagnostica su stderr, referto su stdout
# ----------------------------------------------------------------------


def _print_non_su_stderr(percorso: str) -> list:
    """Le righe dei `print()` che non dichiarano `file=sys.stderr`."""
    with open(percorso, encoding="utf-8") as handle:
        albero = ast.parse(handle.read())
    fuori = []
    for nodo in ast.walk(albero):
        if not (isinstance(nodo, ast.Call)
                and getattr(nodo.func, "id", "") == "print"):
            continue
        canale = next((k.value for k in nodo.keywords if k.arg == "file"),
                      None)
        if not (isinstance(canale, ast.Attribute)
                and canale.attr == "stderr"):
            fuori.append(nodo.lineno)
    return sorted(fuori)


@pytest.mark.parametrize("formato, apertura", [
    ("json", "{"),
    ("csv", "﻿"),
    ("markdown", "#"),
])
def test_il_referto_su_stdout_non_porta_diagnostica(monkeypatch, capsys,
                                                    contesto, formato,
                                                    apertura):
    """R59: `mars_audit.py URL --format json > f.json` non si rileggeva.

    Il file cominciava con «Avvio scansione MARS Beacon su: …» e
    `json.loads` moriva sulla prima colonna. La convenzione Unix e'
    l'unica che tenga: il DATO su stdout, la DIAGNOSTICA su stderr.
    Vale per tutti e tre i formati che qualcuno redirige."""
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica")])
    monkeypatch.setattr(mars_audit, "load_external_module",
                        lambda nome: _ModuloConPunteggio)
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: contesto)
    codice = mars_audit.run_audit("https://x/", 1, "none", "global",
                                  formato=formato)
    uscita = capsys.readouterr()

    assert codice == 0
    assert uscita.out.startswith(apertura), "su stdout c'e' altro"
    assert "Avvio scansione" not in uscita.out
    assert "Rilevamento Moduli" not in uscita.out
    assert "Avvio scansione" in uscita.err, "e la diagnostica non si perde"
    if formato == "json":
        json.loads(uscita.out)      # e' il gesto che il difetto rompeva


def test_su_stdout_va_solo_il_referto(monkeypatch, capsys, contesto):
    """Il presidio dell'invariante, e non del solo percorso di sopra.

    `mars_audit.py` e i moduli che stampano durante un audit scrivono
    su stdout una cosa sola — il referto — e lo fanno con
    `sys.stdout.write`, che il DATO lo dichiara. Ogni `print()` di quei
    file e' diagnostica e va su `stderr`: cosi' non c'e' un'eccezione
    da ricordare, e una stampa aggiunta domani nel posto sbagliato fa
    rosso qui invece che nel referto di qualcuno.

    `mars_api.py` non e' nell'elenco e non e' una dimenticanza: non
    scrive mai un referto su stdout — il dato esce dalla risposta HTTP
    — quindi le sue tre stampe non possono mescolarsi ad alcun dato.
    """
    for nome in ("mars_audit.py", "mars_core.py", "mars_wapt.py",
                 "mars_llm_judge.py"):
        percorso = os.path.join(RADICE, nome)
        assert _print_non_su_stderr(percorso) == [], \
            "%s stampa su stdout" % nome


def test_mars_citations_separava_gia_i_due_canali():
    """La misura che ha sciolto la decisione lasciata aperta nel TO-DO.

    La voce chiedeva se `mars_citations.py` fosse una seconda voce,
    dicendo che aveva «altre 8 stampe con lo stesso problema». Sono
    otto, ma sette dichiarano gia' `file=sys.stderr` e l'ottava e' il
    referto: il difetto li' non c'era. Il test lo tiene vero, perche'
    una stampa aggiunta senza `file=` lo ricreerebbe."""
    percorso = os.path.join(RADICE, "mars_citations.py")
    with open(percorso, encoding="utf-8") as handle:
        sorgente = handle.read()
    righe = sorgente.split("\n")
    fuori = _print_non_su_stderr(percorso)
    assert len(fuori) == 1, "solo il referto va su stdout"
    assert righe[fuori[0] - 1].strip() == "print(report)"


def test_l_aiuto_mostra_come_si_scrive_il_file_delle_chiavi(aiuto):
    """R62: «file JSON con le chiavi» non dice come si scrive.

    L'aiuto rimandava a `examples/audit_request.json`, che e' il corpo
    di una richiesta API: chi lo apriva trovava url, max_pages e
    queries e non capiva quale parte servisse. Ora l'epilogo mostra il
    file per intero, che e' l'unica forma che non si puo' fraintendere.
    """
    assert '"anthropic_api_key"' in aiuto, "il nome della chiave, in JSON"
    assert "examples/credentials.json" in aiuto
    assert "--credentials" in aiuto


# ----------------------------------------------------------------------
# I2: --fail-under, la soglia che decide il codice di uscita
# ----------------------------------------------------------------------

class _ModuloNonMisurato:
    """Un'area che non e' stata guardata: `score` None, non zero."""

    @staticmethod
    def audit(context):
        return {"score": None, "status": "unavailable",
                "issues": ["strumento assente"], "findings": []}


def _audit_con_soglia(monkeypatch, capsys, contesto, soglia,
                      modulo=_ModuloConPunteggio, output=None):
    monkeypatch.setattr(mars_audit, "MODULES_REGISTRY",
                        [("mars_tech", "1. Tecnica")])
    monkeypatch.setattr(mars_audit, "load_external_module",
                        lambda nome: modulo)
    monkeypatch.setattr(mars_audit, "build_context",
                        lambda *a, **k: contesto)
    codice = mars_audit.run_audit("https://x/", 1, "none", "global",
                                  fail_under=soglia, output=output)
    return codice, capsys.readouterr()


def test_cli_il_complessivo_dell_area_sola_e_il_suo_punteggio(monkeypatch,
                                                              capsys,
                                                              contesto):
    """L'ancora dei test della soglia: con un'area sola e nessun
    segnale derivato il complessivo E' 57, quindi 56, 57 e 58 sono
    davvero sotto, alla pari e sopra. Senza questa misura le tre
    asserzioni qui sotto proverebbero solo se stesse."""
    codice, uscita = _audit_con_soglia(monkeypatch, capsys, contesto, None)
    assert codice == mars_audit.EXIT_OK
    assert "57" in uscita.out


def test_cli_fail_under_esce_uno_sotto_la_soglia(monkeypatch, capsys,
                                                 contesto):
    codice, _ = _audit_con_soglia(monkeypatch, capsys, contesto, 58.0)
    assert codice == mars_audit.EXIT_SOTTO_SOGLIA


def test_cli_fail_under_esce_zero_sopra_la_soglia(monkeypatch, capsys,
                                                  contesto):
    codice, _ = _audit_con_soglia(monkeypatch, capsys, contesto, 56.0)
    assert codice == mars_audit.EXIT_OK


def test_cli_fail_under_alla_pari_non_fallisce(monkeypatch, capsys, contesto):
    """`<` e non `<=`: «sotto la soglia» esclude la soglia, come in
    `mars_citations`. Una soglia di 57 su un sito da 57 e' rispettata,
    e le due CLI non possono rispondere diversamente alla stessa
    domanda."""
    codice, _ = _audit_con_soglia(monkeypatch, capsys, contesto, 57.0)
    assert codice == mars_audit.EXIT_OK


def test_cli_senza_soglia_un_punteggio_basso_esce_zero(monkeypatch, capsys,
                                                       contesto):
    """Il comportamento di prima resta il predefinito: chi non chiede
    la soglia non deve vedere cambiare il codice di uscita."""
    codice, _ = _audit_con_soglia(monkeypatch, capsys, contesto, None)
    assert codice == mars_audit.EXIT_OK


def test_cli_fail_under_non_giudica_un_complessivo_non_misurato(monkeypatch,
                                                                capsys,
                                                                contesto):
    """Principio 5: «non misurato» non e' uno zero, e una soglia non lo
    puo' giudicare. Uscire con 1 direbbe alla pipeline che il sito e'
    sotto la soglia; uscirne con 0 in silenzio le farebbe credere che
    la soglia sia stata verificata. Si esce con 0 e LO SI DICHIARA."""
    codice, uscita = _audit_con_soglia(monkeypatch, capsys, contesto, 90.0,
                                       modulo=_ModuloNonMisurato)
    assert codice == mars_audit.EXIT_OK
    assert "--fail-under" in uscita.err


def test_cli_la_scrittura_fallita_vince_sulla_soglia(monkeypatch, capsys,
                                                     contesto, tmp_path):
    """R28 al contrario: un disco pieno non deve uscire con il codice
    della soglia, o la pipeline leggerebbe un guasto della macchina
    come un giudizio sul sito. Il 3 viene prima."""
    codice, _ = _audit_con_soglia(
        monkeypatch, capsys, contesto, 90.0,
        output=str(tmp_path / "assente" / "referto.txt"))
    assert codice == mars_audit.EXIT_SCRITTURA


def test_cli_il_flag_fail_under_esiste_e_non_ha_un_default():
    parser = mars_audit.costruisci_parser()
    assert parser.parse_args(["https://x/"]).fail_under is None
    assert parser.parse_args(["https://x/",
                              "--fail-under", "70"]).fail_under == 70.0


@pytest.mark.parametrize("valore", ["-1", "101", "molte", ""])
def test_cli_fail_under_rifiuta_una_soglia_impossibile(valore):
    """Come `--rrf-k`: il valore si valida PRIMA della scansione. Una
    soglia di 150 uscirebbe con 1 su qualunque sito, ma solo dopo aver
    fatto lavorare il sito per dieci minuti."""
    with pytest.raises(SystemExit):
        mars_audit.costruisci_parser().parse_args(
            ["https://x/", "--fail-under", valore])


def test_cli_main_propaga_fail_under_fino_a_run_audit(monkeypatch):
    """La tubatura argparse -> run_audit, che senza un test si rompe in
    silenzio: l'audit gira, il flag e' accettato, e il codice di uscita
    resta 0 comunque."""
    visti = {}
    monkeypatch.setattr(mars_audit, "run_audit",
                        lambda *a, **k: visti.update(k) or 0)
    mars_audit.main(["https://x/", "--fail-under", "70"])
    assert visti.get("fail_under") == 70.0


def test_aiuto_dichiara_il_codice_uno(aiuto):
    """L'epilogo elencava tre codici e diceva che «1 resta libero».
    Ora non lo e' piu': un elenco che ne tace uno e' peggio di nessun
    elenco, perche' chi lo legge lo crede completo.

    Si guarda dentro il BLOCCO dei codici, non l'aiuto intero: la sola
    presenza di `--fail-under` non basta, e una mutazione che toglieva
    la riga dall'elenco lasciando il flag e' sfuggita per questo.
    """
    assert "resta libero" not in aiuto
    blocco = aiuto.split("codici di uscita:")[1].split("\n\n")[0]
    codici = {riga.split()[0] for riga in blocco.splitlines() if riga.strip()}
    assert codici == {"0", "1", "2", "3"}, blocco
    assert "--fail-under" in blocco
