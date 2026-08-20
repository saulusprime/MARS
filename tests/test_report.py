#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — referto: dato canonico e sue viste.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json

import pytest

from mars_core import load_queries
from mars_report import (RENDERERS, build_report, render_html, render_json,
                         render_text)


@pytest.fixture
def referto(contesto):
    contesto["results"] = {
        "mars_tech": {"score": 85, "issues": ["[lieve] robots.txt muto"]},
        "mars_seo": {"score": None, "status": "unavailable",
                     "issues": ["Lighthouse assente"]},
        "mars_lexical": {"rank": [0, 1], "top_chunk": "https://x/ § H",
                         "queries": ["alfa", "beta"],
                         "per_query": [{"query": "alfa", "rank": [0, 1]},
                                       {"query": "beta", "rank": [1, 0]}]},
        "mars_semantic": {"rank": [0, 1], "answer_shaped_ratio": 0.5,
                          "n_chunks": 2,
                          "per_query": [{"query": "alfa", "rank": [0, 1]},
                                        {"query": "beta", "rank": [0, 1]}]},
        "mars_wcag": {"score": 70, "tool": "axe-core",
                      "wcag_level": "WCAG 2.1 A + AA", "pages_tested": 2,
                      "issues": ["[axe:critical] Images must have alt"]},
        "mars_citability": {"score": 66.0, "market": "eu",
                            "profiles": {"Claude": 70.0, "Kimi": None},
                            "disclaimer": "stime euristiche dichiarate",
                            "issues": ["Segnale debole: X"]},
        "mars_llm_judge": {"score": 72, "model": "claude-opus-5",
                           "chunk_valutati": 3, "motivazione": "Motivo.",
                           "punti_forti": ["A"], "punti_deboli": ["B"],
                           "passaggio_migliore": "https://x/ § H"},
    }
    contesto["skipped"] = ["vietato da robots.txt: https://x/privato"]
    return build_report(contesto["results"], contesto)


# ----------------------------------------------------------------------
# Il dato canonico
# ----------------------------------------------------------------------

def test_referto_ha_i_campi_attesi(referto):
    for chiave in ("tool", "version", "generated_at", "url", "market",
                   "pages_crawled", "discovery", "chunks", "areas",
                   "rrf_simulation", "rrf_aggregate", "citability",
                   "llm_judgement", "skipped"):
        assert chiave in referto, "manca %s" % chiave


def test_referto_e_serializzabile(referto):
    assert json.loads(render_json(referto))["url"] == referto["url"]


def test_referto_non_contiene_credenziali(contesto):
    contesto["credentials"] = {"anthropic_api_key": "SEGRETO-42"}
    testo = render_json(build_report({}, contesto))
    assert "SEGRETO-42" not in testo


def test_aree_dichiarano_strumento_e_livello(referto):
    wcag = [a for a in referto["areas"] if a["module"] == "mars_wcag"][0]
    assert wcag["tool"] == "axe-core"
    assert "WCAG 2.1" in wcag["wcag_level"]
    assert wcag["pages_tested"] == 2


def test_area_non_misurata_ha_score_none(referto):
    seo = [a for a in referto["areas"] if a["module"] == "mars_seo"][0]
    assert seo["score"] is None and seo["status"] == "unavailable"


# ----------------------------------------------------------------------
# Il contratto con mars_citations --from-audit
# ----------------------------------------------------------------------

def test_rrf_simulation_una_voce_per_query(referto):
    assert [v["query"] for v in referto["rrf_simulation"]] == ["alfa", "beta"]


def test_il_referto_alimenta_from_audit(referto, tmp_path):
    """Contratto C3/C4: le stesse query che guidano la simulazione RRF
    devono poter guidare il monitoraggio delle citazioni."""
    f = tmp_path / "r.json"
    f.write_text(render_json(referto), encoding="utf-8")
    query, errore = load_queries(report_path=str(f))
    assert errore == ""
    assert query == ["alfa", "beta"]


def test_aggregato_distinto_dalle_singole(referto):
    assert referto["rrf_aggregate"]["query"].startswith("(aggregato")
    assert referto["rrf_aggregate"]["consensus_out_of"] >= 1


# ----------------------------------------------------------------------
# Le viste
# ----------------------------------------------------------------------

@pytest.mark.parametrize("nome", sorted(RENDERERS))
def test_ogni_renderer_produce_testo(referto, nome):
    uscita = RENDERERS[nome](referto)
    assert isinstance(uscita, str) and len(uscita) > 100


def test_testo_dichiara_cio_che_non_ha_guardato(referto):
    uscita = render_text(referto)
    assert "non misurato" in uscita
    assert "URL saltati" in uscita
    assert "Pagine trovate via" in uscita


def test_testo_mostra_il_disclaimer_sotto_i_numeri(referto):
    uscita = render_text(referto)
    posizione_indice = uscita.index("INDICE COMPOSITO")
    posizione_nota = uscita.index("stime euristiche")
    assert posizione_nota > posizione_indice, \
        "il disclaimer deve stare accanto al numero, non in fondo"


def test_html_autoconsistente(referto):
    """Nessuna CDN, nessuno script: il referto deve restare un file
    solo, apribile senza rete."""
    import re
    uscita = render_html(referto)
    esterni = re.findall(r'(?:src|href)\s*=\s*[\'"](?!data:)([^\'"]+)', uscita)
    assert esterni == []
    assert "<script" not in uscita
    assert "data:image/x-icon;base64," in uscita


def test_html_supporta_il_tema_scuro(referto):
    assert "prefers-color-scheme: dark" in render_html(referto)


def test_html_neutralizza_il_markup_del_sito():
    """Il referto contiene testo preso dal sito analizzato: un sito
    ostile potrebbe iniettare markup."""
    ostile = {
        "tool": "t", "version": "1", "generated_at": "x",
        "url": "<script>alert(1)</script>", "market": "global",
        "pages_crawled": 1, "discovery": "sitemap", "chunks": 1,
        "robots_ignored": False,
        "skipped": ["<img src=x onerror=alert(2)>"],
        "areas": [{"module": "mars_tech", "label": "<b>1</b>", "score": 50,
                   "status": None, "issues": ["<i>iniettato</i>"],
                   "tool": None, "wcag_level": None, "pages_tested": None}],
        "rrf_simulation": [], "rrf_aggregate": None, "citability": None,
        "llm_judgement": None, "lexical": {"top_chunk": None},
        "semantic": {"answer_shaped_ratio": 0, "n_chunks": 0},
    }
    uscita = render_html(ostile)
    assert "<script>alert" not in uscita
    assert "<img src=x" not in uscita
    assert "<b>1</b>" not in uscita
    assert "&lt;script&gt;" in uscita


def test_referto_vuoto_non_esplode(contesto):
    for renderer in RENDERERS.values():
        assert renderer(build_report({}, contesto))
