#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — algoritmi e utilita' di mars_core.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup

from conftest import HTML_BASE
from mars_core import (Crawler, LexicalRetriever, VectorRetriever, chunk_page,
                       default_queries, describe_chunk, host_matches,
                       load_external_module, load_queries, norm_host,
                       normalize_url, reciprocal_rank_fusion,
                       safe_normalize_url, split_windows)


# ----------------------------------------------------------------------
# RRF — la formula del paper, non una sua approssimazione
# ----------------------------------------------------------------------

def test_rrf_valori_esatti_dal_paper():
    """score(d) = somma di 1/(k + rank + 1), con k=60.

    Su due classifiche invertite gli estremi pareggiano SOPRA il
    centro: e' la proprieta' caratteristica dell'RRF, e blinda il "+1"
    dell'indicizzazione, che un refactor perderebbe senza accorgersene.
    """
    esito = dict(reciprocal_rank_fusion([[0, 1, 2], [2, 1, 0]]))
    assert esito[0] == pytest.approx(1 / 61 + 1 / 63)
    assert esito[2] == pytest.approx(1 / 61 + 1 / 63)
    assert esito[1] == pytest.approx(2 / 62)
    assert esito[0] > esito[1]


def test_rrf_premia_chi_sale_su_piu_liste():
    fusi = reciprocal_rank_fusion([[5, 1, 2], [5, 3, 4], [5, 0, 9]])
    assert fusi[0][0] == 5


def test_rrf_k_configurabile():
    stretto = dict(reciprocal_rank_fusion([[0, 1]], k=1))
    largo = dict(reciprocal_rank_fusion([[0, 1]], k=1000))
    assert stretto[0] / stretto[1] > largo[0] / largo[1]


def test_rrf_liste_vuote():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


# ----------------------------------------------------------------------
# BM25
# ----------------------------------------------------------------------

def test_bm25_ordina_per_pertinenza():
    corpus = [["gatto", "dorme", "divano"], ["macchina", "parcheggiata"],
              ["gatto", "gatto", "felino"]]
    punteggi = LexicalRetriever(corpus).get_scores(["gatto"])
    assert punteggi[2] > punteggi[0] > punteggi[1] == 0


def test_bm25_idf_penalizza_i_termini_ovunque():
    ovunque = LexicalRetriever([["a", "x"], ["a", "y"], ["a", "z"]])
    raro = LexicalRetriever([["a", "x"], ["b", "y"], ["c", "z"]])
    assert max(ovunque.get_scores(["a"])) < max(raro.get_scores(["a"]))


@pytest.mark.parametrize("corpus", [[], [[]], [[], []]])
def test_bm25_corpus_degenere_non_esplode(corpus):
    """Regressione R6: la guardia su avgdl == 0 era accidentale."""
    punteggi = LexicalRetriever(corpus).get_scores(["qualsiasi"])
    assert punteggi == [0.0] * len(corpus)


# ----------------------------------------------------------------------
# Proxy char-TFIDF
# ----------------------------------------------------------------------

def test_proxy_riconosce_la_somiglianza():
    corpus = ["il gatto dorme sul divano", "la macchina e' parcheggiata"]
    punteggi = VectorRetriever(corpus, force_proxy=True).get_scores("gatto")
    assert punteggi[0] > punteggi[1]


def test_proxy_conserva_le_document_frequency():
    """Regressione R8: get_scores() ricalcolava df ri-tokenizzando
    l'intero corpus per ogni n-gramma della query."""
    vec = VectorRetriever(["alfa beta", "beta gamma"], force_proxy=True)
    assert vec.df, "le df devono restare in memoria, non essere buttate"
    assert vec.doc_norms and len(vec.doc_norms) == 2
    assert all(isinstance(v, dict) for v in vec.doc_vecs), "vettori sparsi"


def test_proxy_query_vuota_o_ignota():
    vec = VectorRetriever(["alfa beta"], force_proxy=True)
    assert vec.get_scores("") == [0.0]
    assert vec.get_scores("zzzzzzzz") == [0.0]


# ----------------------------------------------------------------------
# URL
# ----------------------------------------------------------------------

@pytest.mark.parametrize("grezzo, atteso", [
    ("https://ESEMPIO.test/a#top", "https://esempio.test/a"),
    ("https://esempio.test:443/a", "https://esempio.test/a"),
    ("http://esempio.test:80/", "http://esempio.test/"),
    ("https://esempio.test", "https://esempio.test/"),
    ("https://esempio.test:8443/a", "https://esempio.test:8443/a"),
    ("https://esempio.test/a?b=1", "https://esempio.test/a?b=1"),
])
def test_normalize_url(grezzo, atteso):
    """Regressione R7: /a e /a#top erano due pagine distinte."""
    assert normalize_url(grezzo) == atteso


@pytest.mark.parametrize("url, host, atteso", [
    ("https://blog.esempio.it/a", "esempio.it", True),
    ("https://esempio.it/a", "esempio.it", True),
    ("https://nonesempio.it/a", "esempio.it", False),
    ("https://esempio.it.altro.com/", "esempio.it", False),
])
def test_host_matches(url, host, atteso):
    assert host_matches(url, host) is atteso


def test_norm_host_toglie_www_e_porta():
    assert norm_host("https://WWW.Esempio.IT:8080/x") == "esempio.it"


@pytest.mark.parametrize("malformato", [
    "http://esempio.test:port/x",    # porta non numerica
    "http://esempio.test:99999/x",   # porta fuori range
    "http://esempio.test:8x/x",      # porta quasi numerica
    "http://[::1/pagina",            # IPv6 senza chiusura
])
def test_safe_normalize_url_non_solleva(malformato):
    """Regressione R15: normalize_url propagava ValueError.

    Questi quattro casi facevano cadere l'audit INTERO — non l'URL.
    """
    with pytest.raises(ValueError):
        normalize_url(malformato)          # il difetto, ancora presente
    assert safe_normalize_url(malformato) is None   # la difesa


def test_safe_normalize_url_concorda_con_normalize_url():
    """Sugli URL validi la versione tollerante non cambia nulla."""
    for buono in ("https://ESEMPIO.test/a#top", "https://esempio.test:443/a",
                  "https://esempio.test", "https://esempio.test/a?b=1"):
        assert safe_normalize_url(buono) == normalize_url(buono)


def test_safe_normalize_url_risolve_i_relativi():
    """base= risolve i relativi, e l'urljoin sta dentro la guardia.

    Regressione R15: su un IPv6 malformato solleva urljoin STESSO,
    prima che normalize_url venga chiamata. Proteggere solo
    normalize_url avrebbe lasciato aperta meta' del difetto.
    """
    assert safe_normalize_url("/a", "http://x.test/b/") == "http://x.test/a"
    with pytest.raises(ValueError):
        urljoin("http://x.test/b/", "http://[::1/")     # il difetto
    assert safe_normalize_url("http://[::1/", "http://x.test/b/") is None


def test_estrai_link_scarta_href_malformato_e_lo_dichiara():
    """Regressione R15, dal lato del crawler.

    Un solo href rotto in una pagina uccideva l'audit. Ora l'URL
    viene scartato, i link buoni della stessa pagina sopravvivono, e
    il referto dichiara cosa non ha guardato (principio 6).
    """
    html = ("<html><body>"
            "<a href='/buona'>ok</a>"
            "<a href='http://esempio.test:port/rotto'>rotto</a>"
            "</body></html>")
    crawler = Crawler("http://esempio.test/", delay=0)
    trovati = crawler.estrai_link(BeautifulSoup(html, "lxml"),
                                  "http://esempio.test/")
    assert trovati == ["http://esempio.test/buona"]
    assert crawler.skipped == [
        "URL non analizzabile: http://esempio.test:port/rotto"]


class _AdattatoreFinto(requests.adapters.BaseAdapter):
    """Serve risposte da un dizionario invece che dalla rete.

    Montato sulla session del Crawler intercetta OGNI richiesta, cosi'
    crawl() puo' essere esercitata per intero restando ermetica: la
    fixture niente_rete copre requests.get, non Session.get.
    """

    def __init__(self, risposte: dict) -> None:
        super().__init__()
        self.risposte = risposte

    def send(self, request, **kwargs):        # noqa: D102
        corpo, tipo = self.risposte.get(request.url, (None, None))
        resp = requests.Response()
        resp.url = request.url
        resp.encoding = "utf-8"
        if corpo is None:
            resp.status_code = 404
            resp._content = b""
            resp.headers["Content-Type"] = "text/plain"
        else:
            resp.status_code = 200
            resp._content = corpo.encode("utf-8")
            resp.headers["Content-Type"] = tipo
        return resp

    def close(self) -> None:
        pass


def _crawler_finto(risposte: dict) -> Crawler:
    crawler = Crawler("http://esempio.test/", max_pages=10, delay=0)
    crawler.session.mount("http://", _AdattatoreFinto(risposte))
    return crawler


PAGINA_UTILE = ("<html lang='it'><head><title>Buona</title></head><body>"
                "<h1>Pagina raggiungibile</h1><p>Testo abbastanza lungo da "
                "superare la soglia minima del chunker e diventare un "
                "passaggio autoconsistente per i due recuperatori.</p>"
                "</body></html>")


def test_crawl_sopravvive_a_un_loc_malformato():
    """Regressione R15, dal percorso sitemap.

    E' il punto d'ingresso che estrai_link NON copre: un <loc>
    malformato entrava in coda e faceva sollevare normalize_url dentro
    crawl(), uccidendo l'audit e portandosi via le pagine gia'
    scaricate. Qui la pagina buona deve sopravvivere allo stesso
    crawl in cui il <loc> rotto viene scartato.
    """
    sitemap = ("<?xml version='1.0'?><urlset>"
               "<url><loc>http://esempio.test/buona</loc></url>"
               "<url><loc>http://esempio.test:port/rotto</loc></url>"
               "</urlset>")
    crawler = _crawler_finto({
        "http://esempio.test/sitemap.xml": (sitemap, "application/xml"),
        "http://esempio.test/buona": (PAGINA_UTILE, "text/html"),
    })
    pagine = crawler.crawl()
    assert list(pagine) == ["http://esempio.test/buona"]
    assert crawler.skipped == [
        "URL non analizzabile: http://esempio.test:port/rotto"]


def test_url_illeggibile_dichiarato_una_volta_sola():
    """Lo stesso href rotto in un template sta su OGNI pagina: senza
    deduplicazione riempirebbe il referto con la stessa riga."""
    html = ("<html><body>"
            "<a href='http://esempio.test:port/rotto'>a</a>"
            "<a href='http://esempio.test:port/rotto'>b</a>"
            "</body></html>")
    crawler = Crawler("http://esempio.test/", delay=0)
    soup = BeautifulSoup(html, "lxml")
    crawler.estrai_link(soup, "http://esempio.test/")
    crawler.estrai_link(soup, "http://esempio.test/")   # seconda pagina
    assert len(crawler.skipped) == 1


# ----------------------------------------------------------------------
# Chunker
# ----------------------------------------------------------------------

def test_chunk_page_segmenta_per_heading():
    """Regressione R10: i chunk erano i primi 500 caratteri."""
    chunks = chunk_page(BeautifulSoup(HTML_BASE, "lxml"),
                        "https://esempio.test/", "Titolo")
    assert len(chunks) == 2
    assert chunks[0]["heading"] == "Intestazione principale"
    assert chunks[1]["heading"] == "Come funziona?"
    assert all(c["url"] == "https://esempio.test/" for c in chunks)


def test_chunk_page_spezza_le_sezioni_lunghe():
    """Regressione R10: una sezione piu' lunga della finestra deve
    produrre piu' chunk. Verificare separatamente la segmentazione per
    heading e split_windows non basta: il difetto sta nel loro
    innesto, ed e' sopravvissuto alla prima versione di questi test."""
    lungo = " ".join("parola%04d" % i for i in range(900))
    html = "<html><body><h1>Una sola sezione</h1><p>%s</p></body></html>"
    chunks = chunk_page(BeautifulSoup(html % lungo, "lxml"), "u", "t")
    assert len(chunks) > 1, "la sezione lunga non e' stata spezzata"
    assert all(c["heading"] == "Una sola sezione" for c in chunks)
    ricomposto = " ".join(c["text"] for c in chunks)
    assert "parola0899" in ricomposto, "la coda del testo e' andata persa"


def test_chunk_page_esclude_script_e_style():
    html = ("<html><body><script>var segreto = 'non deve comparire';"
            "</script><h1>T</h1><p>%s</p></body></html>" % ("testo " * 40))
    testo = " ".join(c["text"] for c in
                     chunk_page(BeautifulSoup(html, "lxml"), "u", "t"))
    assert "segreto" not in testo


def test_chunk_page_non_duplica_il_testo_annidato():
    """Camminare sui nodi di testo, non sugli elementi di blocco:
    con find_all un <p> dentro un <li> verrebbe contato due volte."""
    html = "<html><body><h1>T</h1><ul><li><p>%s</p></li></ul></body></html>"
    chunks = chunk_page(BeautifulSoup(html % ("unico " * 40), "lxml"), "u", "t")
    assert chunks[0]["text"].count("unico") == 40


def test_chunk_page_pagina_corta_produce_comunque_un_chunk():
    chunks = chunk_page(BeautifulSoup("<html><body>ciao</body></html>",
                                      "lxml"), "u", "Titolo")
    assert len(chunks) == 1


def test_split_windows_sovrappone():
    testo = " ".join("parola%03d" % i for i in range(400))
    finestre = split_windows(testo, size=500, overlap=100)
    assert len(finestre) > 1
    assert all(len(f) <= 500 for f in finestre)
    assert finestre[0][-40:].split()[-1] in finestre[1]


def test_split_windows_testo_corto():
    assert split_windows("breve") == ["breve"]


def test_describe_chunk():
    assert describe_chunk({"url": "https://x/a", "heading": "H"}) \
        == "https://x/a § H"
    assert describe_chunk({"url": "https://x/a", "heading": ""}) \
        == "https://x/a"


# ----------------------------------------------------------------------
# Query
# ----------------------------------------------------------------------

def test_default_queries_segue_la_lingua():
    """Regressione C5: interrogare un sito inglese in italiano misura
    la lingua della domanda, non il sito."""
    ita = default_queries({"a": {"lang": "it"}, "b": {"lang": "it"}})
    eng = default_queries({"a": {"lang": "en"}})
    assert "cos'è questo sito" in ita
    assert "what is this site about" in eng
    ignota = default_queries({"a": {"lang": ""}})
    assert "cos'è questo sito" in ignota and "what is this site about" in ignota


def test_load_queries_da_file(tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("prima\n\nseconda\n", encoding="utf-8")
    assert load_queries(path=str(f)) == (["prima", "seconda"], "")


def test_load_queries_rispetta_il_tetto(tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("\n".join("q%d" % i for i in range(30)), encoding="utf-8")
    query, _ = load_queries(path=str(f), max_queries=3)
    assert len(query) == 3


@pytest.mark.parametrize("contenuto, atteso", [
    ({"rrf_simulation": [{"query": "a"}, {"query": "b"}]}, ["a", "b"]),
    ({"rrf_simulation": ["a", "b"]}, ["a", "b"]),
    ({"queries": ["c"]}, ["c"]),
])
def test_load_queries_dal_referto(tmp_path, contenuto, atteso):
    """Contratto C4/C3: e' cio' che sblocca --from-audit."""
    f = tmp_path / "r.json"
    f.write_text(json.dumps(contenuto), encoding="utf-8")
    assert load_queries(report_path=str(f)) == (atteso, "")


def test_load_queries_errori(tmp_path):
    assert load_queries()[1]
    assert load_queries(path=str(tmp_path / "manca.txt"))[1]
    rotto = tmp_path / "rotto.json"
    rotto.write_text("non json", encoding="utf-8")
    assert load_queries(report_path=str(rotto))[1]


# ----------------------------------------------------------------------
# Caricatore di moduli
# ----------------------------------------------------------------------

def test_load_external_module_registra_in_sys_modules():
    """Regressione R11: senza registrazione, un modulo con @dataclass e
    from __future__ import annotations falliva con un errore
    incomprensibile, e l'utente leggeva "file non trovato"."""
    import sys
    sys.modules.pop("mars_citations", None)
    modulo = load_external_module("mars_citations")
    assert modulo is not None
    assert sys.modules.get("mars_citations") is modulo


def test_load_external_module_indipendente_dalla_cwd(tmp_path, monkeypatch):
    """Regressione R11: lanciato da un'altra cartella, il programma non
    trovava nessun modulo e produceva un referto vuoto senza errori."""
    monkeypatch.chdir(tmp_path)
    assert load_external_module("mars_tech") is not None


def test_load_external_module_inesistente():
    assert load_external_module("mars_non_esiste") is None


def test_load_external_module_restituisce_lo_stesso_oggetto():
    """Prima due chiamate davano oggetti DIVERSI: un isinstance contro
    una classe del modulo falliva e lo stato di modulo si azzerava a
    ogni richiesta."""
    assert load_external_module("mars_tech") is load_external_module(
        "mars_tech")


def test_load_external_module_ricarica_se_il_file_cambia(tmp_path,
                                                         monkeypatch):
    """La cache non deve nascondere una modifica: modificare un plugin
    deve avere effetto senza riavviare l'API."""
    import time
    import mars_core
    finto = tmp_path / "mars_finto.py"
    finto.write_text("VALORE = 1\n", encoding="utf-8")
    monkeypatch.setattr(mars_core.os.path, "abspath",
                        lambda p: str(tmp_path / "mars_core.py"))
    primo = load_external_module("mars_finto")
    assert primo.VALORE == 1
    assert load_external_module("mars_finto") is primo

    time.sleep(0.01)
    finto.write_text("VALORE = 2\n", encoding="utf-8")
    secondo = load_external_module("mars_finto")
    assert secondo is not primo
    assert secondo.VALORE == 2


def test_load_external_module_file_sparito(tmp_path, monkeypatch):
    import mars_core
    finto = tmp_path / "mars_effimero.py"
    finto.write_text("VALORE = 1\n", encoding="utf-8")
    monkeypatch.setattr(mars_core.os.path, "abspath",
                        lambda p: str(tmp_path / "mars_core.py"))
    assert load_external_module("mars_effimero") is not None
    finto.unlink()
    assert load_external_module("mars_effimero") is None
