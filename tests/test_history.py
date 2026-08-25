#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — storico e confronto fra due esecuzioni (U7).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os

import mars_history as st
from mars_core import SEV_CRITICAL, SEV_INFO, SEV_WARNING


def _rilievo(**kw) -> dict:
    base = {"area": "mars_tech", "severity": SEV_CRITICAL, "title": "Titolo",
            "key": "tech.robots.ai_blocked", "detail": "", "fix": "",
            "example": "", "url": "", "weight": 2.0, "source_severity": "",
            "params": {}}
    base.update(kw)
    return base


def _referto(aree=None, **kw) -> dict:
    base = {"generated_at": "2026-01-01T00:00:00+0000",
            "url": "https://esempio.test/", "version": "9.9.9",
            "schema_version": 1, "areas": aree or [],
            "overall": {"score": 70.0, "components": []}}
    base.update(kw)
    return base


def _area(modulo="mars_tech", score=57, rilievi=None) -> dict:
    return {"module": modulo, "label": "1. Tecnica", "score": score,
            "issues": [], "findings": rilievi or []}


# ----------------------------------------------------------------------
# La riga di storico
# ----------------------------------------------------------------------

def test_la_riga_tiene_solo_cio_che_serve_al_confronto():
    riga = st.riga_storico(_referto([_area(rilievi=[_rilievo()])]))
    assert set(riga) == {"generated_at", "url", "version", "schema_version",
                         "scores", "overall", "findings"}
    assert riga["scores"] == {"mars_tech": 57}
    assert riga["overall"] == 70.0
    assert riga["findings"] == [{"area": "mars_tech",
                                 "key": "tech.robots.ai_blocked",
                                 "title": "Titolo",
                                 "severity": SEV_CRITICAL}]


def test_la_riga_lascia_fuori_gli_info():
    """Un elenco di risolti pieno di note informative nasconderebbe le
    due righe che contano."""
    riga = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(severity=SEV_INFO, key="tech.canonical.missing")])]))
    assert riga["findings"] == []


def test_la_riga_lascia_fuori_i_derivati():
    """R41: il confronto fra due esecuzioni AGGREGA. Un `cit.seo.weak`
    che sparisce perche' l'area SEO e' migliorata comparirebbe fra i
    risolti accanto al rilievo che l'ha davvero risolto — due righe per
    un intervento solo."""
    riga = st.riga_storico(_referto([_area("mars_citability", rilievi=[
        _rilievo(area="mars_citability", key="cit.seo.weak",
                 severity=SEV_CRITICAL, params={"derived": True})])]))
    assert riga["findings"] == []


def test_la_riga_e_serializzabile():
    """Finisce in JSONL: un valore non serializzabile romperebbe
    l'append DOPO che l'audit e' riuscito."""
    json.dumps(st.riga_storico(_referto([_area(rilievi=[_rilievo()])])))


# ----------------------------------------------------------------------
# Il delta
# ----------------------------------------------------------------------

def test_alla_prima_esecuzione_non_c_e_delta():
    """None e non un delta a zero: le viste devono poter tacere invece
    di dire «non e' cambiato nulla», che sarebbe falso."""
    assert st.compute_delta(None, st.riga_storico(_referto())) is None
    assert st.compute_delta({}, st.riga_storico(_referto())) is None


def test_il_delta_riconosce_risolti_e_nuovi():
    prima = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="tech.robots.ai_blocked"),
        _rilievo(key="tech.sitemap.missing", severity=SEV_WARNING)])]))
    dopo = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="tech.sitemap.missing", severity=SEV_WARNING),
        _rilievo(key="tech.index.noindex")])]))
    delta = st.compute_delta(prima, dopo)
    assert [f["key"] for f in delta["resolved"]] == ["tech.robots.ai_blocked"]
    assert [f["key"] for f in delta["new"]] == ["tech.index.noindex"]


def test_il_confronto_e_per_chiave_e_non_per_titolo():
    """La proprieta' che rende utile la `key` della Fase 1: se il
    confronto guardasse il titolo, un conteggio che cambia direbbe un
    rilievo risolto e uno nuovo — cioe' il contrario del vero."""
    prima = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="tech.canonical.missing",
                 title="2/3 pagine senza canonical")])]))
    dopo = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="tech.canonical.missing",
                 title="117/400 pagine senza canonical")])]))
    delta = st.compute_delta(prima, dopo)
    assert delta["resolved"] == [] and delta["new"] == []
    assert delta["by_title_fallback"] is False


def test_senza_chiave_si_ripiega_sul_titolo_e_lo_dichiara():
    """Nessuno dei nove moduli produce rilievi senza chiave; un plugin
    di terzi puo'. Il ripiego funziona e il delta lo dice, perche' e'
    un confronto piu' debole."""
    prima = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="", title="2 pagine rotte")])]))
    dopo = st.riga_storico(_referto([_area(rilievi=[
        _rilievo(key="", title="9 pagine rotte")])]))
    delta = st.compute_delta(prima, dopo)
    assert delta["resolved"] == [] and delta["new"] == []
    assert delta["by_title_fallback"] is True


def test_il_delta_confronta_i_punteggi_e_ordina_per_movimento():
    prima = st.riga_storico(_referto([_area("mars_tech", 50),
                                      _area("mars_wcag", 90)]))
    dopo = st.riga_storico(_referto([_area("mars_tech", 80),
                                     _area("mars_wcag", 85)]))
    delta = st.compute_delta(prima, dopo)
    assert delta["scores"] == [
        {"area": "mars_tech", "before": 50, "after": 80, "change": 30},
        {"area": "mars_wcag", "before": 90, "after": 85, "change": -5}]


def test_un_area_non_piu_misurata_non_e_un_peggioramento():
    """La bugia piu' facile della fase: un'area misurata ieri e non oggi
    non e' scesa a zero, non e' stata guardata. E' la stessa distinzione
    fra «non misurato» e «zero» che il referto fa dappertutto."""
    prima = st.riga_storico(_referto([_area("mars_seo", 80)]))
    dopo = st.riga_storico(_referto([_area("mars_seo", None)]))
    assert st.compute_delta(prima, dopo)["scores"] == []


def test_il_delta_confronta_il_complessivo():
    prima = st.riga_storico(_referto(overall={"score": 60.0,
                                              "components": []}))
    dopo = st.riga_storico(_referto(overall={"score": 66.3,
                                             "components": []}))
    assert st.compute_delta(prima, dopo)["overall"] == {
        "before": 60.0, "after": 66.3, "change": 6.3}


def test_senza_complessivo_da_entrambe_le_parti_non_si_confronta():
    prima = st.riga_storico(_referto(overall=None))
    dopo = st.riga_storico(_referto(overall={"score": 66.3,
                                             "components": []}))
    assert st.compute_delta(prima, dopo)["overall"] is None


def test_il_delta_dice_con_quale_esecuzione_si_confronta():
    """Senza, «+30 sulla tecnica» non dice rispetto a quando — e due
    esecuzioni a un'ora di distanza non valgono come due a sei mesi."""
    prima = st.riga_storico(_referto(generated_at="2026-01-01T00:00:00+0000",
                                     version="1.0.0"))
    delta = st.compute_delta(prima, st.riga_storico(_referto()))
    assert delta["previous_run"] == "2026-01-01T00:00:00+0000"
    assert delta["previous_version"] == "1.0.0"


# ----------------------------------------------------------------------
# Il file
# ----------------------------------------------------------------------

def test_lo_storico_e_append_only(tmp_path):
    """Nessuna riga viene mai riscritta: il file resta leggibile anche
    se un'esecuzione si interrompe a meta'."""
    percorso = str(tmp_path / "storico.jsonl")
    assert st.appendi_storico(percorso, {"url": "https://a/", "n": 1})
    assert st.appendi_storico(percorso, {"url": "https://a/", "n": 2})
    righe = open(percorso, encoding="utf-8").read().strip().split("\n")
    assert [json.loads(r)["n"] for r in righe] == [1, 2]


def test_si_rilegge_l_ultima_esecuzione_di_quel_sito(tmp_path):
    """Un solo file puo' raccogliere piu' siti: confrontarne due
    darebbe un delta pieno di rilievi «risolti» che nessuno ha
    toccato."""
    percorso = str(tmp_path / "storico.jsonl")
    for voce in ({"url": "https://a/", "n": 1}, {"url": "https://b/", "n": 2},
                 {"url": "https://a/", "n": 3}):
        st.appendi_storico(percorso, voce)
    assert st.leggi_ultima_esecuzione(percorso, "https://a/")["n"] == 3
    assert st.leggi_ultima_esecuzione(percorso, "https://b/")["n"] == 2
    assert st.leggi_ultima_esecuzione(percorso, "https://c/") is None


def test_una_riga_corrotta_non_invalida_le_altre(tmp_path):
    """E' il vantaggio del JSONL sul JSON, ed e' la ragione per cui lo
    storico ha questo formato."""
    percorso = str(tmp_path / "storico.jsonl")
    st.appendi_storico(percorso, {"url": "https://a/", "n": 1})
    with open(percorso, "a", encoding="utf-8") as fh:
        fh.write("{non e' json\n\n")
    st.appendi_storico(percorso, {"url": "https://a/", "n": 2})
    assert st.leggi_ultima_esecuzione(percorso, "https://a/")["n"] == 2
    assert len(st.leggi_storico(percorso)) == 2


def test_uno_storico_che_non_c_e_non_e_un_errore(tmp_path):
    """Lo storico e' un archivio di comodo: un file assente o
    illeggibile non deve far fallire un audit gia' fatto."""
    assente = str(tmp_path / "mai-scritto.jsonl")
    assert st.leggi_ultima_esecuzione(assente, "https://a/") is None
    assert st.leggi_storico(assente) == []


def test_scrivere_dove_non_si_puo_non_solleva(tmp_path):
    """Il referto e' gia' prodotto: perdere una riga di archivio non
    vale il codice di uscita. Chi chiama lo dichiara all'utente."""
    cartella = tmp_path / "inesistente" / "ancora"
    assert st.appendi_storico(str(cartella / "s.jsonl"), {"n": 1}) is False


def test_lo_storico_sta_accanto_al_referto(tmp_path):
    fuori = str(tmp_path / "referto.json")
    assert st.percorso_storico(fuori) == os.path.join(
        str(tmp_path), st.STORICO_PREDEFINITO)
    assert st.percorso_storico(None) == st.STORICO_PREDEFINITO
