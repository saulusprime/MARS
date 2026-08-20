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
from mars_report import (RENDERERS, _classe, _quadrante, build_report,
                         render_html, render_json, render_text)


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


# ----------------------------------------------------------------------
# La vista HTML in stile Lighthouse
# ----------------------------------------------------------------------

def test_html_ha_un_quadrante_per_area_con_punteggio(referto):
    """La fascia di quadranti e' la firma visiva di Lighthouse: deve
    esserci, e i quadranti si disegnano in SVG perche' il referto non
    puo' contenere script."""
    uscita = render_html(referto)
    assert uscita.count("<svg viewBox='0 0 120 120'") >= 5
    assert "<script" not in uscita


@pytest.mark.parametrize("valore, arco, tratteggio, centro", [
    (None, 0, True, "—"),     # non misurato: anello vuoto, nessun numero
    (0, 0, False, "0"),       # misurato zero: anello pieno, numero
    (55, 1, False, "55"),
    (100, 1, False, "100"),
])
def test_quadrante_distingue_zero_da_non_misurato(valore, arco, tratteggio,
                                                  centro):
    """Il cuore dell'onestà del referto, in forma grafica.

    Un'area non misurata non deve somigliare a un'area che ha preso
    zero: la prima ha l'anello tratteggiato e un trattino, la seconda
    un anello pieno e lo zero scritto. E lo zero non deve disegnare
    alcun arco — con stroke-linecap arrotondato lascerebbe un puntino
    colorato che si legge come "poco" invece che come "niente".
    """
    disegno = _quadrante(valore, "Area")
    assert disegno.count("stroke='currentColor'") == arco
    assert ("stroke-dasharray='4 6'" in disegno) is tratteggio
    assert ">%s</text>" % centro in disegno


@pytest.mark.parametrize("valore, classe", [
    (100, "ok"), (90, "ok"), (89, "warn"), (50, "warn"),
    (49, "bad"), (0, "bad"), (None, "muted"),
])
def test_scala_dei_colori_e_quella_di_lighthouse(valore, classe):
    """0-49 rosso, 50-89 arancio, 90-100 verde: si adotta la scala di
    Lighthouse perche' chi legge i due referti non debba tradurre."""
    assert _classe(valore) == classe


def test_html_non_finge_un_voto_per_lessicale_e_semantica(referto):
    """Quelle due aree producono classifiche, non voti: mettere loro
    uno zero — o un quadrante qualunque — sarebbe inventare una misura."""
    uscita = render_html(referto)
    assert uscita.count(">classifica<") == 2
    for atteso in ("Classifica BM25, non un voto",
                   "Classifica vettoriale, non un voto"):
        assert atteso in uscita


def test_html_dichiara_lo_stato_di_cio_che_non_ha_misurato(referto):
    uscita = render_html(referto)
    assert "non misurato" in uscita        # mars_seo, unavailable
    assert "Cosa non è stato guardato" in uscita
    assert "vietato da robots.txt" in uscita


# ----------------------------------------------------------------------
# L'elenco dei controlli, come lo mostra Lighthouse
# ----------------------------------------------------------------------

# Titoli senza apostrofi: in HTML escono come &#x27;, ed è giusto così
# — l'escape ha il suo test a parte. Ci sono già cascato in R22.
# Il superato sta per PRIMO di proposito: se il dato fosse gia'
# ordinato, il test sull'ordinamento passerebbe anche senza ordinare.
CONTROLLI = [
    {"id": "http-status-code", "title": "Codice di stato HTTP valido",
     "passed": True, "manual": False, "items": []},
    {"id": "structured-data", "title": "Dati strutturati validi",
     "passed": False, "manual": True, "items": []},
    {"id": "is-crawlable", "title": "Pagina bloccata dallo indicizzatore",
     "passed": False, "manual": False, "items": ["X-Robots-Tag: noindex"]},
]


def _referto_seo():
    return build_report(
        {"mars_seo": {"score": 42.0, "issues": ["[Lighthouse] bloccata"],
                      "tool": "Lighthouse 13.4.1", "form_factor": "mobile",
                      "audits": CONTROLLI}},
        {"url": "https://x/", "market": "global", "pages": {"a": {}},
         "chunks": [], "discovery": "sitemap", "skipped": []})


def test_i_controlli_arrivano_nel_dato_canonico():
    area = _referto_seo()["areas"][0]
    assert [c["id"] for c in area["audits"]] == [c["id"] for c in CONTROLLI]
    assert area["form_factor"] == "mobile"


def test_html_elenca_anche_i_controlli_superati():
    """Elencare i superati non e' ridondanza: senza, non si sa CHE COSA
    sia stato guardato, e un punteggio pieno resta indistinguibile da
    un controllo che non e' stato eseguito affatto."""
    uscita = render_html(_referto_seo())
    for controllo in CONTROLLI:
        assert controllo["title"] in uscita
    assert "class='superato'" in uscita
    assert "class='fallito'" in uscita
    assert "class='manuale'" in uscita


def test_html_mette_i_falliti_per_primi():
    """Sono quelli su cui si interviene, e nel dato stanno per ultimi."""
    uscita = render_html(_referto_seo())
    assert (uscita.index("Pagina bloccata dallo indicizzatore")
            < uscita.index("Dati strutturati validi")
            < uscita.index("Codice di stato HTTP valido"))


def test_html_mostra_gli_elementi_incriminati():
    assert "X-Robots-Tag: noindex" in render_html(_referto_seo())


def test_il_conteggio_dei_controlli_compare_in_entrambe_le_viste():
    for vista in (render_text, render_html):
        uscita = vista(_referto_seo())
        assert "1 controlli superati, 1 falliti" in uscita
        assert "mobile" in uscita, "il dispositivo cambia i risultati"


def test_superato_non_usa_la_classe_globale_ok():
    """La classe .ok esiste gia' nel CSS e colora l'intera riga:
    riusarla per i controlli superati li rendeva tutti verdi, invece
    del solo segno di spunta."""
    assert "<li class='ok'>" not in render_html(_referto_seo())


# ----------------------------------------------------------------------
# Plugin che rompono (R22)
# ----------------------------------------------------------------------

def _referto_con(risultato_tech):
    return build_report({"mars_tech": risultato_tech},
                        {"url": "https://x/", "market": "global",
                         "pages": {"a": {}}, "chunks": [],
                         "discovery": "sitemap", "skipped": []})


@pytest.mark.parametrize("ritorno", [None, "oops", 42, []])
def test_plugin_non_dict_non_fa_crollare_il_referto(ritorno):
    """Regressione R22: res.get() su un non-dict sollevava
    AttributeError DOPO che tutti i moduli erano girati.

    L'audit intero andava perso per la distrazione di un plugin — un
    `return` dimenticato — con un errore incomprensibile e fuori dai
    codici di uscita documentati.
    """
    area = _referto_con(ritorno)["areas"][0]
    assert area["status"] == "error"
    assert "invece di un dict" in area["issues"][0]
    assert type(ritorno).__name__ in area["issues"][0]


def test_area_fallita_compare_nel_referto(referto):
    """Regressione R22: un'area fallita spariva senza lasciare traccia.

    Peggio di una dichiarata fallita: con --output il file consegnato
    non ne diceva nulla, e chi legge non sapeva di aver perso un'area.
    """
    # Messaggio senza apostrofi: in HTML verrebbero resi come &#x27;,
    # ed e' giusto cosi' — l'escape ha il suo test a parte.
    r = _referto_con({"error": "ValueError: divisione per zero"})
    assert [a["module"] for a in r["areas"]] == ["mars_tech"]
    for vista in (render_text, render_html):
        uscita = vista(r)
        assert "1. Tecnica" in uscita
        assert "errore del modulo" in uscita
        assert "divisione per zero" in uscita


def test_errore_di_modulo_non_e_uno_zero():
    """Un modulo fallito non ha preso zero: non ha preso nulla."""
    area = _referto_con({"error": "boom"})["areas"][0]
    assert area["score"] is None


# ----------------------------------------------------------------------
# «di superficie» non è «misurato a fondo» (R21)
# ----------------------------------------------------------------------

def _referto_sicurezza(**extra):
    res = {"mars_wapt": dict({"score": 100, "issues": []}, **extra)}
    return build_report(res, {"url": "https://x/", "market": "global",
                              "pages": {"a": {}}, "chunks": [],
                              "discovery": "sitemap", "skipped": []})


SUPERFICIE = {"status": "surface", "tool": "HTTP-Headers"}
COMPLETA = {"tool": "ZAP (attiva)", "complete": True}
INTERROTTA = {"tool": "ZAP (passiva)", "complete": False}


@pytest.mark.parametrize("vista", [render_text, render_html],
                         ids=["testo", "html"])
def test_superficie_distinguibile_da_una_misura_piena(vista):
    """Regressione R21: due fatti diversi, lo stesso numero.

    Un sito con i tre header presenti e nessun daemon ZAP prendeva
    100/100 esattamente come un WAPT completo e pulito. In vista testo
    le due righe erano stringhe IDENTICHE.
    """
    superficie = vista(_referto_sicurezza(**SUPERFICIE))
    completa = vista(_referto_sicurezza(**COMPLETA))
    assert superficie != completa, \
        "un controllo di superficie non puo' rendersi identico a un WAPT"
    assert "superficie" in superficie.lower()
    assert "superficie" not in completa.lower().replace("class='nota", "")


@pytest.mark.parametrize("vista", [render_text, render_html],
                         ids=["testo", "html"])
def test_scansione_interrotta_dichiarata(vista):
    """Un punteggio parziale non e' un punteggio pieno: vale per il
    timeout di ZAP come per le pagine che axe non ha caricato."""
    assert "parziale" in vista(_referto_sicurezza(**INTERROTTA)).lower()


@pytest.mark.parametrize("chiave, extra", [
    ("status", SUPERFICIE), ("complete", INTERROTTA),
])
def test_il_dato_canonico_porta_lo_stato(chiave, extra):
    """Le viste possono dirlo perche' il dato lo contiene: se sparisce
    da build_report, sparisce da entrambe insieme."""
    area = _referto_sicurezza(**extra)["areas"][0]
    assert area[chiave] == extra[chiave]


def test_lo_strumento_e_dichiarato_per_ogni_area_non_solo_wcag(referto):
    """Prima strumento e campione comparivano solo dove esisteva un
    wcag_level, cioe' per la sola accessibilita'."""
    testo = render_text(referto)
    assert "axe-core" in testo and "WCAG 2.1" in testo


def test_quadrante_di_superficie_e_marcato(referto):
    """Il numero resta, ma il quadrante non deve leggersi come un
    successo pieno: la nota sotto lo qualifica ed e' colorata."""
    html_superficie = render_html(_referto_sicurezza(**SUPERFICIE))
    assert "class='nota parziale'" in html_superficie
    assert "class='nota parziale'" not in render_html(
        _referto_sicurezza(**COMPLETA))


def test_html_mostra_la_legenda_della_scala(referto):
    """La scala è una convenzione, non una misura: va dichiarata."""
    uscita = render_html(referto)
    for fascia in ("0-49", "50-89", "90-100", "non misurato"):
        assert fascia in uscita
