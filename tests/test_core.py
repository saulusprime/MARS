#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — algoritmi e utilita' di mars_core.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup

import mars_core
from conftest import HTML_BASE
from mars_core import (AREA_PREFIX, MAX_REDIRECT, MODULES_REGISTRY,
                       SEV_CRITICAL, SEV_INFO, SEV_WARNING, WEIGHTS, Crawler,
                       Finding, LexicalRetriever, VectorRetriever,
                       pagine_del_rilievo,
                       chiave_esterna, chunk_page, decode_html,
                       default_queries, describe_chunk, estrai_struttura,
                       host_matches, load_external_module, load_queries,
                       norm_host, normalize_url, normalizza_severita,
                       reciprocal_rank_fusion, safe_normalize_url,
                       severita_lighthouse, split_windows, tokenize)


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


# ----------------------------------------------------------------------
# Host IPv6 letterali (R24)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("grezzo, atteso", [
    ("http://[::1]:8000/pagina", "http://[::1]:8000/pagina"),
    ("http://[2001:db8::1]/x", "http://[2001:db8::1]/x"),
    ("http://[2001:DB8::1]:80/", "http://[2001:db8::1]/"),
])
def test_normalize_url_conserva_le_quadre_ipv6(grezzo, atteso):
    """Regressione R24: parts.hostname toglie le parentesi quadre.

    Senza, l'URL ricomposto e' "http://::1:8000/x", che non e' un
    indirizzo: ogni richiesta falliva e il sito veniva diagnosticato
    irraggiungibile pur rispondendo.
    """
    assert normalize_url(grezzo) == atteso


@pytest.mark.parametrize("url, atteso", [
    ("http://[::1]:8000/x", "[::1]"),
    ("http://[2001:db8::1]/x", "[2001:db8::1]"),
])
def test_norm_host_non_taglia_un_ipv6_sui_due_punti(url, atteso):
    assert norm_host(url) == atteso


def test_host_matches_distingue_due_ipv6_diversi():
    """Regressione R24, la parte piu' seria.

    norm_host tagliava sul primo ":" e riduceva "[2001:db8::1]" a
    "[2001": due indirizzi DIVERSI diventavano lo stesso host, e il
    filtro same-host costruito da R7 e R17 lasciava passare un altro
    server.
    """
    proprio = norm_host("http://[2001:db8::1]/")
    assert host_matches("http://[2001:db8::1]/altra", proprio) is True
    assert host_matches("http://[2001:db8::2]/x", proprio) is False


def test_crawl_su_host_ipv6(monkeypatch):
    """Un sito servito su un IPv6 letterale dev'essere scansionabile."""
    crawler = Crawler("http://[::1]:8861/", max_pages=2, delay=0)
    crawler.session.mount("http://", _AdattatoreFinto({
        "http://[::1]:8861/": (PAGINA_UTILE, "text/html"),
    }))
    assert list(crawler.crawl()) == ["http://[::1]:8861/"]


# ----------------------------------------------------------------------
# Tokenizzazione (R18)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("testo, atteso", [
    ("Come funziona?", ["come", "funziona"]),
    ("Il servizio.", ["il", "servizio"]),
    ("«Qualità» — città, però…", ["qualità", "città", "però"]),
    ("(IVA esclusa);", ["iva", "esclusa"]),
    ("'virgolettato'", ["virgolettato"]),
    ("¿Qué?", ["qué"]),
])
def test_tokenize_toglie_la_punteggiatura_di_confine(testo, atteso):
    """Regressione R18: .lower().split() lasciava "funziona?" attaccato.

    L'elenco copre anche la punteggiatura tipografica, che un elenco
    ASCII dimenticherebbe: nei testi reali «», — e … ci sono eccome.
    """
    assert tokenize(testo) == atteso


@pytest.mark.parametrize("testo, atteso", [
    ("e-mail", ["e-mail"]),
    ("COVID-19", ["covid-19"]),
    ("3,14", ["3,14"]),
    ("info@esempio.it", ["info@esempio.it"]),
    ("l'azienda", ["l'azienda"]),
    ("C++", ["c++"]),          # "+" e' un simbolo (Sm), non punteggiatura
])
def test_tokenize_conserva_la_punteggiatura_interna(testo, atteso):
    """Si toglie solo il CONFINE, ed e' una scelta deliberata.

    Spezzare su ogni non-parola manderebbe in pezzi indirizzi, prezzi
    e sigle, e riempirebbe l'indice di frammenti ("l", "dell") che
    gonfiano la lunghezza dei documenti — cioe' la normalizzazione
    BM25. Vedi I15 per la questione dell'elisione italiana.
    """
    assert tokenize(testo) == atteso


def test_tokenize_perde_il_cancelletto_finale_ma_resta_simmetrico():
    """Limite noto, misurato e non ipotizzato: "#" e' categoria Po,
    quindi "C#" diventa "c".

    Non si aggiunge un'eccezione a mano perche' la prima ne chiama
    altre, e soprattutto perche' il danno e' di PRECISIONE, non di
    recall: corpus e query passano per la stessa funzione, quindi
    "C#" continua a trovare "C#". Si perde solo la distinzione da una
    "c" qualunque.
    """
    assert tokenize("C#") == ["c"]
    corpus = [tokenize("guida a C# per principianti"),
              tokenize("ricette di cucina tradizionale")]
    punteggi = LexicalRetriever(corpus).get_scores(tokenize("C#"))
    assert punteggi[0] > punteggi[1]


def test_tokenize_simmetrico_fra_corpus_e_query():
    """Il difetto era di CORRISPONDENZA, non di pulizia: va provato
    che la punteggiatura non impedisca il match da nessuno dei due
    lati, altrimenti si e' corretta meta' del problema."""
    sporco = LexicalRetriever([tokenize("il preventivo, si richiede."),
                               tokenize("tutt'altro argomento")])
    pulito = LexicalRetriever([tokenize("il preventivo si richiede"),
                               tokenize("tutt'altro argomento")])
    assert sporco.get_scores(tokenize("preventivo"))[0] > 0
    assert pulito.get_scores(tokenize("preventivo?"))[0] > 0
    assert (sporco.get_scores(tokenize("preventivo"))[0]
            == pytest.approx(pulito.get_scores(tokenize("preventivo?"))[0]))


@pytest.mark.parametrize("testo", ["", "   ", "!!!", "— … «»"])
def test_tokenize_su_testo_senza_parole(testo):
    """Solo punteggiatura non deve produrre token vuoti: entrerebbero
    nell'indice come termini fantasma e falserebbero le lunghezze."""
    assert tokenize(testo) == []


def test_tokenize_e_la_punteggiatura_ribaltano_la_classifica():
    """Regressione R18: il difetto non era estetico.

    Il chunk che contiene DAVVERO la frase cercata prendeva zero
    credito per quella parola e, con la normalizzazione BM25 sulla
    lunghezza, finiva SOTTO un chunk piu' corto che la parola non ce
    l'aveva. Qui si prova che l'ordine e' quello giusto.
    """
    corpus = ["Come funziona? Il servizio si attiva in pochi minuti "
              "dopo la registrazione online.",
              "Come raggiungerci: la nostra sede si trova in centro."]
    vecchio = LexicalRetriever([c.lower().split() for c in corpus])
    nuovo = LexicalRetriever([tokenize(c) for c in corpus])
    # il difetto, ancora dimostrabile: il chunk giusto non vince
    assert vecchio.get_scores("come funziona".split())[0] <= \
        vecchio.get_scores("come funziona".split())[1]
    # la correzione: vince, e nettamente
    punteggi = nuovo.get_scores(tokenize("come funziona"))
    assert punteggi[0] > punteggi[1]


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

    Deve restare FEDELE a HTTPAdapter.build_response, altrimenti
    conferma anche cio' che e' sbagliato (la lezione di C9):
    - l'encoding si deriva dagli header con la stessa funzione, perche'
      fissarlo a "utf-8" nascondeva il mojibake di R16;
    - resp.request e' impostata, perche' senza requests non sa
      risolvere i redirect e il difetto R17 non si manifesta.

    `richieste` registra gli URL davvero chiesti: e' cosi' che si
    verifica che una richiesta vietata NON sia partita.
    """

    def __init__(self, risposte: dict, redirect: dict | None = None) -> None:
        super().__init__()
        self.risposte = risposte
        self.redirect = redirect or {}
        self.richieste: list[str] = []

    def send(self, request, **kwargs):        # noqa: D102
        self.richieste.append(request.url)
        resp = requests.Response()
        resp.url = request.url
        resp.request = request
        resp._content_consumed = True
        if request.url in self.redirect:
            resp.status_code = 302
            resp._content = b""
            resp.headers["Location"] = self.redirect[request.url]
            resp.headers["Content-Type"] = "text/html"
        else:
            corpo, tipo = self.risposte.get(request.url, (None, None))
            if corpo is None:
                resp.status_code = 404
                resp._content = b""
                resp.headers["Content-Type"] = "text/plain"
            else:
                resp.status_code = 200
                resp._content = (corpo if isinstance(corpo, bytes)
                                 else corpo.encode("utf-8"))
                resp.headers["Content-Type"] = tipo
        resp.encoding = requests.utils.get_encoding_from_headers(resp.headers)
        return resp

    def close(self) -> None:
        pass


def _crawler_finto(risposte: dict, redirect: dict | None = None) -> Crawler:
    crawler = Crawler("http://esempio.test/", max_pages=10, delay=0)
    crawler.session.mount("http://", _AdattatoreFinto(risposte, redirect))
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


# ----------------------------------------------------------------------
# Codifica delle pagine (R16)
# ----------------------------------------------------------------------

ACCENTATA = "Perché è così: qualità più alta"


def _pagina_accentata(meta: str = "") -> str:
    return ("<html lang='it'><head>%s<title>%s</title></head>"
            "<body><h1>%s</h1></body></html>" % (meta, ACCENTATA, ACCENTATA))


@pytest.mark.parametrize("meta, header", [
    ("<meta charset='utf-8'>", "text/html"),                  # meta, header muto
    ("", "text/html"),                                        # nessuna dichiarazione
    ("", "text/html; charset=utf-8"),                         # solo header
    ("<meta charset='utf-8'>", "text/html; charset=utf-8"),   # entrambi
    ("", "application/xhtml+xml"),                            # niente da requests
])
def test_decode_html_non_produce_mojibake(meta, header):
    """Regressione R16: resp.text decodificava in ISO-8859-1.

    requests applica a ogni text/* senza charset il default legacy di
    RFC 2616: su un sito UTF-8 — la norma — l'intero corpus entrava
    corrotto senza un solo errore.
    """
    byte = _pagina_accentata(meta).encode("utf-8")
    assert ACCENTATA in decode_html(byte, header)
    # il difetto, ancora dimostrabile: e' cio' che faceva resp.text
    assert ACCENTATA not in byte.decode("iso-8859-1")


def test_decode_html_rispetta_una_pagina_davvero_latin1():
    """Non si assume UTF-8: una pagina latin-1 va letta come tale."""
    byte = _pagina_accentata("<meta charset='iso-8859-1'>").encode("iso-8859-1")
    assert ACCENTATA in decode_html(byte, "text/html")


def test_decode_html_header_batte_il_meta_sbagliato():
    """Precedenza dello standard: il charset dell'header vince sul meta.

    Il caso reale e' il <meta> stantio lasciato indietro da una
    migrazione, con il server gia' corretto.
    """
    byte = _pagina_accentata("<meta charset='iso-8859-1'>").encode("utf-8")
    assert ACCENTATA in decode_html(byte, "text/html; charset=utf-8")


def test_decode_html_usa_il_charset_dell_header():
    """Il charset dichiarato nell'header va onorato, non solo sniffato.

    Caso misurato in cui e' decisivo: pagina cirillica in windows-1251
    senza <meta>. Il solo rilevamento statistico sceglie 'maccyrillic'
    e sbaglia il primo carattere; l'header lo dice esattamente.
    """
    testo = "Здравствуйте, это наш сайт"
    byte = ("<html><head><title>%s</title></head><body>x</body></html>"
            % testo).encode("windows-1251")
    assert testo in decode_html(byte, "text/html; charset=windows-1251")


def test_decode_html_bom_batte_header_sbagliato():
    """Il BOM vince su tutto, header incluso.

    Pagina scritta su Windows e servita da un server che dichiara
    ancora latin-1: senza questo caso si otterrebbe mojibake proprio
    dove la codifica e' dichiarata in modo inequivocabile.
    """
    byte = b"\xef\xbb\xbf" + _pagina_accentata().encode("utf-8")
    decodificata = decode_html(byte, "text/html; charset=iso-8859-1")
    assert ACCENTATA in decodificata
    assert "﻿" not in decodificata      # il BOM non resta nel testo


def test_decode_html_non_solleva_mai():
    """Byte indecodificabili o charset inventato: si sostituisce, non
    si perde la pagina."""
    assert decode_html(b"\xff\xfe\xfa dati rotti", "text/html") is not None
    assert ACCENTATA in decode_html(
        _pagina_accentata().encode("utf-8"), "text/html; charset=inesistente-9")


def test_crawl_decodifica_le_pagine_senza_charset():
    """Regressione R16 dal lato del crawler, con l'HTML grezzo coerente.

    title, headings, chunks e html devono uscire tutti corretti dallo
    stesso crawl: sono gli ingressi di BM25, del proxy char-TFIDF e
    dell'RRF, e un mojibake qui falsa ogni punteggio a valle.
    """
    pagina_html = ("<html lang='it'><head><meta charset='utf-8'>"
                   "<title>%s</title></head><body><h1>%s</h1><p>%s</p>"
                   "</body></html>"
                   % (ACCENTATA, ACCENTATA,
                      "la città però è già lì da un pezzo, e così sia. " * 4))
    crawler = _crawler_finto({
        # Content-Type SENZA charset: e' la configurazione che rompeva
        "http://esempio.test/": (pagina_html, "text/html"),
    })
    pagina = crawler.crawl()["http://esempio.test/"]
    assert pagina["title"] == ACCENTATA
    assert pagina["headings"] == [ACCENTATA]
    assert "città" in pagina["chunks"][0]["text"]
    assert "Ã" not in pagina["html"]
    assert pagina["title"] in pagina["html"]     # DOM e grezzo concordi


def test_robots_txt_letto_come_utf8():
    """robots.txt e' UTF-8 per RFC 9309, ma viaggia come text/plain:
    resp.text lo avrebbe decodificato in ISO-8859-1 come le pagine."""
    robots = "User-agent: *\nAllow: /\nSitemap: http://esempio.test/però.xml\n"
    crawler = _crawler_finto({
        "http://esempio.test/robots.txt": (robots, "text/plain"),
    })
    crawler.robots()
    assert crawler.robots_info["sitemaps"] == ["http://esempio.test/però.xml"]


# ----------------------------------------------------------------------
# Redirect (R17)
# ----------------------------------------------------------------------

def _sitemap(*urls: str) -> str:
    return ("<?xml version='1.0'?><urlset>%s</urlset>"
            % "".join("<url><loc>%s</loc></url>" % u for u in urls))


def _crawler_con_sitemap(urls, redirect=None, robots="User-agent: *\nAllow: /\n",
                         **pagine):
    risposte = {
        "http://esempio.test/robots.txt": (robots, "text/plain"),
        "http://esempio.test/sitemap.xml": (_sitemap(*urls), "application/xml"),
    }
    risposte.update({u: (c, "text/html") for u, c in pagine.items()})
    return _crawler_finto(risposte, redirect)


def _pagina(titolo: str) -> str:
    return ("<html lang='it'><head><title>%s</title></head><body><h1>%s</h1>"
            "<p>Testo lungo a sufficienza per diventare un chunk "
            "autoconsistente nel corpus dei due recuperatori.</p></body></html>"
            % (titolo, titolo))


def test_redirect_verso_url_vietato_non_viene_nemmeno_chiesto():
    """Regressione R17: bastava un redirect per aggirare robots.txt.

    Il controllo sta PRIMA del salto: verificare resp.url a cose fatte
    eviterebbe di indicizzare, ma la richiesta vietata sarebbe gia'
    partita e il crawler avrebbe comunque disobbedito.
    """
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/porta"],
        redirect={"http://esempio.test/porta":
                  "http://esempio.test/privato/segreto"},
        robots="User-agent: *\nDisallow: /privato/\n",
        **{"http://esempio.test/privato/segreto": _pagina("SEGRETO")})
    pagine = crawler.crawl()
    assert pagine == {}
    assert any("vietato da robots.txt" in s for s in crawler.skipped)
    chieste = crawler.session.get_adapter("http://esempio.test/").richieste
    assert "http://esempio.test/privato/segreto" not in chieste


def test_redirect_verso_host_esterno_non_entra_nel_corpus():
    """Regressione R17: il contenuto di un altro host veniva
    indicizzato come pagina del sito, e finiva in BM25 e nell'RRF."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/fuori"],
        redirect={"http://esempio.test/fuori": "http://esterno.test/pagina"},
        **{"http://esterno.test/pagina": _pagina("CONTENUTO ESTERNO")})
    assert crawler.crawl() == {}
    assert any("host esterno" in s for s in crawler.skipped)
    chieste = crawler.session.get_adapter("http://esempio.test/").richieste
    assert "http://esterno.test/pagina" not in chieste


@pytest.mark.parametrize("ordine", [
    ["http://esempio.test/vecchia", "http://esempio.test/nuova"],
    ["http://esempio.test/nuova", "http://esempio.test/vecchia"],
])
def test_redirect_non_duplica_la_pagina(ordine):
    """Regressione R17: /vecchia -> /nuova, entrambe in sitemap,
    facevano entrare la stessa pagina due volte nel corpus.

    Va provato in ENTRAMBI gli ordini: sono due rami diversi, e nel
    secondo la pagina veniva scaricata due volte prima che il
    duplicato fosse riconosciuto — misurato, non dedotto.
    """
    crawler = _crawler_con_sitemap(
        ordine,
        redirect={"http://esempio.test/vecchia": "http://esempio.test/nuova"},
        **{"http://esempio.test/nuova": _pagina("Nuova")})
    pagine = crawler.crawl()
    assert list(pagine) == ["http://esempio.test/nuova"]
    # Il sito non va interrogato due volte per la stessa pagina: e' la
    # buona educazione di rete che R7 ha stabilito.
    chieste = crawler.session.get_adapter("http://esempio.test/").richieste
    assert chieste.count("http://esempio.test/nuova") == 1


def test_duplicato_dopo_redirect_dichiarato_nel_referto():
    """Una sitemap che elenca sia l'URL vecchio sia quello nuovo e' un
    rilievo sul sito: il referto deve dirlo, non tacerlo."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/nuova", "http://esempio.test/vecchia"],
        redirect={"http://esempio.test/vecchia": "http://esempio.test/nuova"},
        **{"http://esempio.test/nuova": _pagina("Nuova")})
    crawler.crawl()
    assert any("duplicato dopo redirect" in s for s in crawler.skipped)


def test_pagina_registrata_sotto_l_url_di_arrivo():
    """Il contenuto vive all'URL di arrivo: e' quello che va nei chunk
    e che mars_tech confronta con il canonical."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/vecchia"],
        redirect={"http://esempio.test/vecchia": "http://esempio.test/nuova"},
        **{"http://esempio.test/nuova": _pagina("Nuova")})
    pagine = crawler.crawl()
    assert list(pagine) == ["http://esempio.test/nuova"]
    chunks = pagine["http://esempio.test/nuova"]["chunks"]
    assert {c["url"] for c in chunks} == {"http://esempio.test/nuova"}


@pytest.mark.parametrize("redirect, atteso, richieste_max", [
    ({"http://esempio.test/a": ""}, "senza destinazione", 1),
    ({"http://esempio.test/a": "http://esempio.test/a"}, "circolare", 1),
    ({"http://esempio.test/a": "http://esempio.test/b",
      "http://esempio.test/b": "http://esempio.test/a"}, "circolare", 2),
    ({"http://esempio.test/a": "http://esempio.test:port/y"},
     "non analizzabile", 1),
])
def test_redirect_degeneri_diagnosticati_con_precisione(
        redirect, atteso, richieste_max):
    """Ogni caso degenere dice cosa e' successo davvero.

    Una Location vuota veniva risolta da urljoin nell'URL di partenza e
    riportata come "troppi redirect": diagnosi sbagliata sul difetto
    sbagliato, la lezione di R6. E un ciclo non deve costare cinque
    richieste al sito prima di essere riconosciuto.
    """
    crawler = _crawler_con_sitemap(["http://esempio.test/a"],
                                   redirect=redirect)
    assert crawler.crawl() == {}
    assert atteso in crawler.skipped[0]
    chieste = [u for u in crawler.session.get_adapter("http://esempio.test/").richieste
               if "robots" not in u and "sitemap" not in u]
    assert len(chieste) <= richieste_max


def test_catena_di_redirect_troppo_lunga():
    catena = {"http://esempio.test/h%d" % i: "http://esempio.test/h%d" % (i + 1)
              for i in range(MAX_REDIRECT + 4)}
    crawler = _crawler_con_sitemap(["http://esempio.test/h0"],
                                   redirect=catena)
    assert crawler.crawl() == {}
    assert "redirect" in crawler.skipped[0]


def test_sitemap_con_loc_relativi(monkeypatch):
    """Regressione R24: i <loc> relativi venivano presi alla lettera.

    Lo standard li vuole assoluti, ma le sitemap reali ne hanno di
    relativi: host_matches li bocciava come "host esterno" — motivo
    falso, e' lo stesso host — e l'audit restava senza una pagina,
    senza nemmeno ripiegare sui link interni.
    """
    crawler = _crawler_con_sitemap(
        [], **{"http://esempio.test/pagina1.html": _pagina("Una"),
               "http://esempio.test/pagina2.html": _pagina("Due")})
    adattatore = crawler.session.get_adapter("http://esempio.test/")
    adattatore.risposte["http://esempio.test/sitemap.xml"] = (
        "<?xml version='1.0'?><urlset>"
        "<url><loc>/pagina1.html</loc></url>"
        "<url><loc>pagina2.html</loc></url></urlset>", "application/xml")
    pagine = crawler.crawl()
    assert sorted(pagine) == ["http://esempio.test/pagina1.html",
                              "http://esempio.test/pagina2.html"]
    assert crawler.skipped == []


def test_sitemap_con_loc_assoluti_invariata():
    """La correzione non deve toccare il caso normale: urljoin su un
    URL gia' assoluto lo restituisce identico."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/pagina1.html"],
        **{"http://esempio.test/pagina1.html": _pagina("Una")})
    assert list(crawler.crawl()) == ["http://esempio.test/pagina1.html"]


@pytest.mark.parametrize("corpo, atteso", [
    ("", True),                              # esiste, ma vuoto: 200
    ("User-agent: *\nAllow: /\n", True),
    (None, False),                           # 404
])
def test_robots_esistente_anche_se_vuoto(corpo, atteso):
    """Regressione R24: `found` si deduceva dal CONTENUTO.

    Un robots.txt servito a 200 ma vuoto significa "tutto permesso",
    ed e' una scelta del sito: riportarlo come assente e' un'altra
    cosa, e mars_tech ne faceva un rilievo di gravita' media.
    """
    risposte = {}
    if corpo is not None:
        risposte["http://esempio.test/robots.txt"] = (corpo, "text/plain")
    crawler = _crawler_finto(risposte)
    crawler.robots()
    assert crawler.robots_info["found"] is atteso


def test_robots_txt_segue_ancora_i_redirect():
    """I redirect delle PAGINE si controllano salto per salto, ma
    robots.txt deve continuare a seguirli: RFC 9309 lo richiede, e
    /robots.txt che redirige e' comunissimo (http -> https, www)."""
    crawler = _crawler_finto(
        {"http://esempio.test/robots-vero.txt":
            ("User-agent: *\nDisallow: /privato/\n", "text/plain")},
        {"http://esempio.test/robots.txt":
            "http://esempio.test/robots-vero.txt"})
    crawler.robots()
    assert crawler.robots_info["found"] is True
    assert crawler.can_fetch("http://esempio.test/privato/x") is False
    assert crawler.can_fetch("http://esempio.test/pubblico") is True


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


def test_load_queries_un_file_senza_righe_utili_e_un_errore(tmp_path):
    """R31: restituire `([], "")` faceva ripiegare l'audit sulle query
    generiche **senza dirlo**, e chi aveva passato `--queries` credeva di
    aver misurato le proprie.

    Il ramo `report_path` un errore lo dava gia': erano le due meta'
    della stessa funzione a comportarsi in modo diverso."""
    vuoto = tmp_path / "vuoto.txt"
    vuoto.write_text("", encoding="utf-8")
    query, errore = load_queries(path=str(vuoto))
    assert query == []
    assert "Nessuna query utile" in errore

    bianche = tmp_path / "bianche.txt"
    bianche.write_text("\n   \n\t\n", encoding="utf-8")
    query, errore = load_queries(path=str(bianche))
    assert query == [], "righe bianche non sono query"
    assert "Nessuna query utile" in errore

    # Una riga utile in mezzo a righe bianche resta un successo: e' la
    # differenza fra «file vuoto» e «file con dentro poco».
    mista = tmp_path / "mista.txt"
    mista.write_text("\n\n  una domanda  \n\n", encoding="utf-8")
    assert load_queries(path=str(mista)) == (["una domanda"], "")


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


# ----------------------------------------------------------------------
# estrai_struttura e il delay effettivo (R26)
# ----------------------------------------------------------------------

HTML_STRUTTURA = """<html lang="it"><head><title>t</title></head><body>
<h1>Uno</h1><h2>Due</h2><h4>Salto</h4>
<form>
  <label for="ok">Etichettato</label><input type="text" id="ok">
  <label>Avvolto <input type="text" name="w"></label>
  <input type="text" name="nudo">
  <input type="hidden" name="h">
  <textarea name="t" aria-label="area"></textarea>
</form>
<table><tr><th>Testa</th></tr></table>
<table role="presentation"><tr><td>x</td></tr></table>
<a href="/1">Clicca qui</a><a href="/2" aria-label="Guida">qui</a>
<span tabindex="3">a</span><span tabindex="abc">b</span>
</body></html>"""


def test_estrai_struttura_legge_il_dom_una_volta_sola():
    """R26: i dati strutturali per i criteri WCAG statici escono dal
    crawler, non da un secondo parse dentro mars_wcag.

    Il test sta sul PRODUTTORE: mars_wcag ha i propri test, ma quelli
    passerebbero anche se questa funzione restituisse la struttura
    sbagliata, purche' coerente. Qui si fissa cosa il DOM contiene.
    """
    s = estrai_struttura(BeautifulSoup(HTML_STRUTTURA, "lxml"))

    # I livelli, in ordine: e' la successione a rivelare il salto h2->h4.
    assert s["heading_levels"] == [1, 2, 4]

    # Quattro campi, e l'etichettatura risolta dove serve il documento
    # intero: <label for> che punta al campo, e <label> che lo avvolge.
    assert [(c["type"], c["labelled"]) for c in s["form_fields"]] == [
        ("text", True),      # <label for="ok">
        ("text", True),      # avvolto da <label>
        ("text", False),     # nudo
        ("hidden", False),   # non interattivo: filtrarlo tocca al modulo
        ("", True),          # <textarea aria-label>, senza attributo type
    ]

    # Dati, non giudizi: il role resta grezzo, decidere che
    # "presentation" esenti dal criterio tocca a mars_wcag.
    assert s["tables"] == [{"has_th": True, "role": ""},
                           {"has_th": False, "role": "presentation"}]

    assert s["links"] == [{"text": "Clicca qui", "aria-label": None},
                          {"text": "qui", "aria-label": "Guida"}]

    # Grezzi: un tabindex non numerico e' esso stesso un dato, e
    # convertirlo qui lo cancellerebbe.
    assert s["tabindex"] == ["3", "abc"]


def test_pagina_del_crawler_porta_la_struttura():
    """Il punto d'integrazione: estrai_struttura puo' essere giusta e
    non essere chiamata. Qui la pagina passa dal crawler vero."""
    crawler = _crawler_finto({
        "http://esempio.test/": (HTML_STRUTTURA, "text/html")})
    pagine = crawler.crawl()
    dati = pagine["http://esempio.test/"]
    for chiave in ("heading_levels", "form_fields", "tables",
                   "links", "tabindex"):
        assert chiave in dati, "il crawler non pubblica %r" % chiave
    assert dati["heading_levels"] == [1, 2, 4]


# ----------------------------------------------------------------------
# estrai_meta_robots: l'agente del meta non si perde (R51)
# ----------------------------------------------------------------------

HTML_META = """<html lang="it"><head><title>t</title>
<meta name="robots" content="Nofollow">
<meta name="GoogleBot" content="noindex">
<meta name="googlebot" content="NOARCHIVE">
<meta name="description" content="noindex non e' una direttiva qui">
</head><body><p>x</p></body></html>"""


def test_estrai_meta_robots_separa_il_globale_dal_per_agente():
    """R51: il crawler univa i `content` di piu' meta in una stringa
    sola, e quale meta li portasse era perduto prima di arrivare al
    modulo. `<meta name="googlebot" content="noindex">` riceveva quindi
    lo stesso giudizio di `<meta name="robots">`, benche' escluda il
    solo Google — che e' la meta' che R37 aveva chiuso sull'header.

    Il test sta sul PRODUTTORE: mars_tech ha i propri, ma passerebbero
    anche con un'estrazione coerente e sbagliata.
    """
    globali, per_agente = mars_core.estrai_meta_robots(
        BeautifulSoup(HTML_META, "lxml"))

    assert globali == "nofollow", "solo name=robots, e minuscolo"
    # Nome e contenuto arrivano minuscoli: e' il produttore a
    # normalizzare, cosi' chi confronta con `CRAWLER_IA` non deve
    # rifarlo — e chi lo rifacesse non saprebbe di essere il secondo.
    # Piu' meta per lo stesso agente si uniscono con la virgola, che e'
    # il separatore della grammatica in cui il prefisso viene letto.
    assert per_agente == {"googlebot": "noindex, noarchive"}


def test_estrai_meta_robots_non_guarda_i_meta_che_non_sono_direttive():
    """`<meta name="description">` non e' una direttiva, per quanto il
    suo testo somigli a una."""
    globali, per_agente = mars_core.estrai_meta_robots(
        BeautifulSoup('<html><head><meta name="description" '
                      'content="noindex"></head></html>', "lxml"))
    assert (globali, per_agente) == ("", {})


def test_pagina_del_crawler_porta_l_agente_del_meta():
    """Il punto d'integrazione: la funzione puo' essere giusta e non
    essere chiamata."""
    crawler = _crawler_finto({
        "http://esempio.test/": (HTML_META, "text/html")})
    dati = crawler.crawl()["http://esempio.test/"]
    assert dati["meta_robots"] == "nofollow"
    assert dati["meta_robots_by_agent"] == {"googlebot": "noindex, noarchive"}


def test_build_context_pubblica_il_delay_effettivo(monkeypatch):
    """R26: audit() leggeva context["delay"], che non esisteva.

    E il valore giusto non e' quello chiesto dalla CLI: robots.txt puo'
    alzarlo con Crawl-delay, e allora e' quello il ritardo che il sito
    ha chiesto. Chi rivisita le pagine — il browser di mars_wcag — deve
    rispettare lo stesso.
    """
    risposte = {
        "http://esempio.test/robots.txt":
            ("User-agent: *\nCrawl-delay: 7\nAllow: /", "text/plain"),
        "http://esempio.test/": (PAGINA_UTILE, "text/html"),
    }
    pause: list[float] = []
    monkeypatch.setattr(mars_core.time, "sleep", pause.append)

    class CrawlerConAdattatore(Crawler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.session.mount("http://", _AdattatoreFinto(risposte))

    monkeypatch.setattr(mars_core, "Crawler", CrawlerConAdattatore)
    contesto = mars_core.build_context("http://esempio.test/", max_pages=2,
                                       delay=0.5)

    assert contesto is not None
    assert contesto["delay"] == 7.0, "e' il delay EFFETTIVO, non quello chiesto"
    assert pause and max(pause) > 6, "il crawler stesso deve averlo rispettato"


def test_build_context_pubblica_la_lingua(monkeypatch):
    """U9.3: la lingua sta nel contesto accanto a `market` e `llm`.

    Non e' solo una scelta di resa — Lighthouse e axe producono i
    propri testi al momento della misura, e glieli si deve chiedere
    allora. Il predefinito e' la lingua canonica, cosi' un chiamante
    che non la dichiara ottiene cio' che otteneva prima.
    """
    risposte = {
        "http://esempio.test/robots.txt": ("", "text/plain"),
        "http://esempio.test/": (PAGINA_UTILE, "text/html"),
    }

    class CrawlerConAdattatore(Crawler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.session.mount("http://", _AdattatoreFinto(risposte))

    monkeypatch.setattr(mars_core, "Crawler", CrawlerConAdattatore)
    predefinito = mars_core.build_context("http://esempio.test/",
                                          max_pages=1)
    chiesta = mars_core.build_context("http://esempio.test/", max_pages=1,
                                      lang="en")
    assert predefinito is not None and chiesta is not None
    assert predefinito["lang"] == "it"
    assert chiesta["lang"] == "en"


# ----------------------------------------------------------------------
# Rilievi strutturati — Fase 1 del programma UPGRADE
# ----------------------------------------------------------------------

@pytest.mark.parametrize("scala, valore, severita, peso", [
    # La scala editoriale italiana: la definisce mars_tech, ma la usano
    # anche gli header di mars_wapt, i controlli statici di mars_wcag e
    # mars_schema. Per questo si chiama "mars". (Non mars_citability:
    # vedi il commento di _SCALE_SEVERITA, corretto con U1.8.)
    ("mars", "critico", SEV_CRITICAL, 2.0),
    ("mars", "grave", SEV_WARNING, 2.0),
    ("mars", "medio", SEV_WARNING, 1.0),
    ("mars", "lieve", SEV_INFO, 1.0),
    ("axe", "critical", SEV_CRITICAL, 2.0),
    ("axe", "serious", SEV_WARNING, 2.0),
    ("axe", "moderate", SEV_WARNING, 1.0),
    ("axe", "minor", SEV_INFO, 1.0),
    ("zap", "High", SEV_CRITICAL, 2.0),
    ("zap", "Medium", SEV_WARNING, 1.0),
    ("zap", "Low", SEV_INFO, 1.0),
    ("zap", "Informational", SEV_INFO, 1.0),
])
def test_mappa_di_conversione_delle_tre_scale(scala, valore, severita, peso):
    """Tutti i valori delle tre scale, uno per uno.

    E' la tabella su cui poggia l'intero adeguamento: se una riga
    cambia, cambiano ordinamenti, piano di interventi e confronti fra
    esecuzioni, in silenzio."""
    assert normalizza_severita(scala, valore) == (severita, peso)


def test_grave_e_medio_restano_distinti_nel_peso():
    """Le quattro severita' collassano due livelli in 'warning': la
    granularita' persa deve sopravvivere nel peso, altrimenti non
    c'era ragione di conservarlo."""
    grave = normalizza_severita("mars", "grave")
    medio = normalizza_severita("mars", "medio")
    assert grave[0] == medio[0] == SEV_WARNING
    assert grave[1] > medio[1]


def test_zap_la_confidenza_non_e_una_gravita():
    """Un `risk` come 'High (Medium)' non deve declassare l'alert a info.

    La motivazione originale — «ZAP scrive il rischio con la confidenza
    accanto» — **non regge alla lettura del sorgente**, ed e' R32:
    `core/view/alerts` costruisce `risk` come `MSG_RISK[getRisk()]`,
    cioe' sempre uno dei quattro livelli nudi, e la confidenza sta in un
    campo suo. Il `"High (Medium)"` dei referti tradizionali e'
    `riskdesc`, che quell'endpoint non emette.

    Il caso resta da coprire per un'altra ragione, piu' stretta: gli
    alert che non nascono dalle regole di serie — script utente, add-on
    di terzi, `alert/action/addAlert` — portano il testo che ne ha
    scritto l'autore, e li' dentro puo' esserci qualunque cosa. Lo
    `split(" ")[0]` e' una difesa verso quelli, non verso un
    comportamento documentato di ZAP."""
    assert normalizza_severita("zap", "High (Medium)") == (SEV_CRITICAL, 2.0)
    assert normalizza_severita("zap", "  hIgH  ") == (SEV_CRITICAL, 2.0)


def test_lighthouse_un_audit_in_errore_non_e_un_fallimento():
    """Regressione U1.7: `error` mancava da LH_MODI_NON_MISURATI.

    Lighthouse azzera il peso dei non applicabili, degli informativi e
    dei manuali prima di scriverlo nel referto, ma NON quello di un
    audit andato in errore (`core/scoring.js`). Senza `error`
    nell'elenco, un `is-crawlable` che lo strumento non e' riuscito a
    eseguire usciva `critical` col suo peso 93/23: un guasto nostro
    presentato come difetto grave del sito."""
    assert severita_lighthouse(None, "error", 93 / 23) == (SEV_INFO, 1.0)


def test_valore_sconosciuto_degrada_non_solleva():
    """Un impact di axe o un risk di ZAP che non conosciamo e' DATO
    ESTERNO: uno strumento che aggiorna la propria scala non deve far
    cadere un audit."""
    for scala in ("mars", "axe", "zap"):
        assert normalizza_severita(scala, "gravissimo") == (SEV_INFO, 1.0)
        assert normalizza_severita(scala, "") == (SEV_INFO, 1.0)
        assert normalizza_severita(scala, None) == (SEV_INFO, 1.0)


def test_scala_sconosciuta_solleva():
    """L'opposto del caso sopra, e la ragione per cui vanno distinti.

    Una scala sbagliata e' un refuso di programmazione, non un dato:
    degradarla a (info, 1.0) appiattirebbe un intero modulo su un
    livello, con i punteggi intatti e i test verdi. Invisibile."""
    with pytest.raises(ValueError) as errore:
        normalizza_severita("mars_schema", "grave")
    assert "mars_schema" in str(errore.value)
    # Il messaggio deve dire quali sono quelle giuste, o non aiuta.
    assert "axe" in str(errore.value)


@pytest.mark.parametrize("score, mode, weight, atteso", [
    # is-crawlable pesa 93/23 nella categoria SEO, e Lighthouse lo
    # calibra apposta perche' il suo solo fallimento faccia fallire
    # l'intera categoria. E' l'unico audit SEO sopra la soglia.
    (0, "binary", 93 / 23, (SEV_CRITICAL, 2.0)),
    (0, "binary", 1, (SEV_WARNING, 1.0)),
    # Peso 0 = audit manuale: Lighthouse non lo conta nel punteggio.
    (None, "manual", 0, (SEV_INFO, 1.0)),
    (None, "notApplicable", 0, (SEV_INFO, 1.0)),
    (None, "informative", 0, (SEV_INFO, 1.0)),
    # `error` conserva invece il suo peso nel LHR: se non fosse
    # nell'elenco uscirebbe critical. Vedi il test qui sopra.
    (None, "error", 93 / 23, (SEV_INFO, 1.0)),
])
def test_severita_lighthouse(score, mode, weight, atteso):
    assert severita_lighthouse(score, mode, weight) == atteso


def test_lighthouse_un_audit_senza_punteggio_non_e_un_difetto_grave():
    """R54: `score` era in firma e non lo leggeva nessuno, e l'inerzia
    nascondeva un buco.

    Un `auditRef` della categoria il cui id NON compare fra gli
    `audits` arriva qui con score None e modo assente: il modo non
    entra in `LH_MODI_NON_MISURATI`, quindi decideva il solo peso, e
    `is-crawlable` — 93/23, l'unico sopra la soglia — usciva
    **critical**. Un difetto grave del sito su un controllo che
    Lighthouse non ha mai riportato.

    Il punteggio e' la guardia piu' forte del modo, e per costruzione:
    `_normalizeAuditScore` (core/audits/audit.js) restituisce **null**
    per ogni modo non misurato e un numero finito per ogni modo
    misurato — o solleva, e allora l'audit finisce in `error`, che e'
    di nuovo null. Quindi «score non numerico» equivale a «non
    misurato», e vale anche dove il modo manca o non si riconosce.
    """
    assert severita_lighthouse(None, "", 93 / 23) == (SEV_INFO, 1.0)
    assert severita_lighthouse(None, "binary", 93 / 23) == (SEV_INFO, 1.0)
    assert severita_lighthouse(None, "modo-che-non-esiste", 93 / 23) \
        == (SEV_INFO, 1.0)
    # Non `is None` ma `isinstance`, e la differenza si misura: il LHR
    # arriva da un sottoprocesso, quindi e' dato esterno, e un
    # `"score": "0"` non e' un punteggio. `_penalita` in mars_seo fa
    # gia' lo stesso controllo sullo stesso valore.
    assert severita_lighthouse("0", "binary", 93 / 23) == (SEV_INFO, 1.0)
    assert severita_lighthouse([], "binary", 93 / 23) == (SEV_INFO, 1.0)
    # E un punteggio c'e': allora decide il peso, come sempre.
    assert severita_lighthouse(0, "binary", 93 / 23) == (SEV_CRITICAL, 2.0)
    assert severita_lighthouse(0.5, "numeric", 93 / 23) == (SEV_CRITICAL, 2.0)


def test_lighthouse_non_misurato_non_e_un_fallimento():
    """Un audit manuale resta info anche se pesasse molto: non e' un
    difetto, e' un promemoria. Confonderli riempie l'elenco dei rilievi
    di voci su cui non c'e' nulla da fare."""
    assert severita_lighthouse(None, "manual", 93 / 23) == (SEV_INFO, 1.0)
    # E un peso illeggibile non deve far cadere nulla.
    assert severita_lighthouse(0, "binary", None) == (SEV_INFO, 1.0)
    assert severita_lighthouse(0, "binary", "molto") == (SEV_INFO, 1.0)


@pytest.mark.parametrize("grezzo, atteso", [
    ("is-crawlable", "is_crawlable"),
    ("document-title", "document_title"),
    ("color.contrast", "color_contrast"),      # un punto romperebbe la chiave
    ("10038", "10038"),                        # pluginId ZAP
    ("Aria-Allowed-Attr", "aria_allowed_attr"),
    ("  spazi  ", "spazi"),
    ("--bordi--", "bordi"),
    ("", "unknown"),
    ("///", "unknown"),
])
def test_chiave_esterna_sanifica_gli_id_di_strumento(grezzo, atteso):
    """Gli id vengono da axe, ZAP e Lighthouse: sono dato esterno.

    Un punto dentro l'id romperebbe la profondita' fissa a tre segmenti
    della chiave, e con essa le ancore del referto e la ricerca a
    catalogo della traduzione."""
    assert chiave_esterna(grezzo) == atteso


def test_finding_attraversa_il_confine_serializzato():
    """Il contratto plugin resta dict, e la vista JSON fa json.dumps
    SENZA default=: una dataclass che sfuggisse solleverebbe TypeError
    a valle, dopo che tutti i moduli sono girati."""
    f = Finding(area="mars_tech", severity=SEV_CRITICAL,
                title="robots.txt blocca i crawler IA",
                key="tech.robots.ai_blocked", weight=2.0,
                source_severity="critico",
                params={"bloccati": ["GPTBot", "ClaudeBot"], "n": 2})
    d = f.as_dict()
    assert isinstance(d, dict)
    assert d["key"] == "tech.robots.ai_blocked"
    assert d["source_severity"] == "critico"
    assert json.loads(json.dumps(d))["params"]["n"] == 2

    # I default non devono essere condivisi fra istanze.
    altro = Finding(area="mars_seo", severity=SEV_INFO, title="x")
    altro.params["solo_mio"] = 1
    assert Finding(area="a", severity=SEV_INFO, title="y").params == {}


class _ModelloFinto:
    """SentenceTransformer finto, FEDELE su cio' che il codice usa.

    `encode` restituisce una lista di vettori, uno per testo — quindi su
    una lista vuota una lista vuota, com'e' per il modello vero. Serve
    per esercitare il ramo `use_real` senza caricare torch: la suite non
    deve dipendere da sentence-transformers, ed e' cio' che `force_proxy`
    garantisce ovunque tranne qui, dove il ramo lo si vuole proprio.
    """

    def __init__(self, *args, **kwargs):
        pass

    def encode(self, testi):
        return [[float(len(t)), 1.0] for t in testi]


class _RigaFinta(list):
    """Una riga di array numpy: una lista che sa fare `.tolist()`.

    `get_scores` scrive `self._cosine(...)[0].tolist()`, quindi un finto
    che restituisse liste nude fallirebbe con `AttributeError` — ed e'
    successo scrivendo questo test. numpy non e' una dipendenza della
    suite (sta in requirements-optional con torch), quindi si imita la
    FORMA che il codice usa invece di importarlo.
    """

    def tolist(self):
        return list(self)


def _cosine_fedele(a, b):
    """`cosine_similarity` di sklearn, fedele sui due casi che contano.

    Su un array vuoto solleva `ValueError: Expected 2D array, got 1D
    array instead` — verificato eseguendo quello vero prima di scrivere
    questo finto. Un finto che restituisse `[[]]` renderebbe il test
    vacuo: e' esattamente il difetto che R30 chiude.
    """
    if not len(b):
        raise ValueError("Expected 2D array, got 1D array instead")
    return [_RigaFinta([0.5] * len(b))]


def test_vector_corpus_vuoto_da_lista_vuota_da_entrambi_i_rami(monkeypatch):
    """R30: la promessa che «il chiamante non deve sapere quale dei due
    sia attivo» si rompeva con un corpus vuoto.

    Il proxy restituiva `[]`, il ramo embeddings reali sollevava
    `ValueError` — riprodotto sul modello vero — e `mars_semantic` moriva
    invece di risultare non misurato. Un sito di sole pagine senza testo
    indicizzabile non e' un caso di laboratorio."""
    assert VectorRetriever([], force_proxy=True).get_scores("x") == []

    monkeypatch.setattr(mars_core, "load_sentence_transformers",
                        lambda: (_ModelloFinto, _cosine_fedele))
    reale = VectorRetriever([], force_proxy=False)
    assert reale.use_real, "il test deve esercitare il ramo reale"
    assert reale.get_scores("x") == []


def test_vector_il_ramo_reale_funziona_ancora_con_un_corpus(monkeypatch):
    """La guardia non deve spegnere il ramo che funzionava: con documenti
    veri il coseno viene chiamato e i punteggi escono."""
    monkeypatch.setattr(mars_core, "load_sentence_transformers",
                        lambda: (_ModelloFinto, _cosine_fedele))
    reale = VectorRetriever(["alfa", "beta"], force_proxy=False)
    assert reale.get_scores("x") == [0.5, 0.5]


def test_pagine_del_rilievo_regge_i_params_ostili():
    """Unico lettore della convenzione `params["urls"]`, e legge dati
    che attraversano il confine dei plugin: un modulo esterno puo'
    scriverci dentro qualunque cosa, e una sola eccezione qui
    spegnerebbe la treemap e il CSV di un referto intero.

    Lista vuota su tutto cio' che non e' una lista di pagine — che non
    e' la stessa cosa di «nessuna pagina colpita», ed e' il motivo per
    cui la treemap in quel caso non colora invece di colorare di
    verde."""
    assert pagine_del_rilievo({"params": {"urls": ["https://a/",
                                                   "https://b/"]}}) == [
        "https://a/", "https://b/"]
    assert pagine_del_rilievo({}) == []
    assert pagine_del_rilievo({"params": None}) == []
    assert pagine_del_rilievo({"params": "non un dict"}) == []
    assert pagine_del_rilievo({"params": {}}) == []
    assert pagine_del_rilievo({"params": {"urls": None}}) == []
    assert pagine_del_rilievo({"params": {"urls": "https://a/"}}) == [], \
        "una stringa non e' una lista di URL: sarebbe una pagina per carattere"
    # Le stringhe vuote spariscono: nel CSV sarebbero una pagina «», e
    # nella treemap una chiave che non e' l'URL di nessuna pagina.
    assert pagine_del_rilievo({"params": {"urls": ["https://a/", "", None]}}
                              ) == ["https://a/"]


def test_ogni_area_del_registro_ha_un_prefisso():
    """La chiave e' stabile, il nome del plugin no: i moduli sono
    sostituibili per progetto. Se un giorno si aggiunge la decima area
    e ci si dimentica del prefisso, le sue chiavi non avrebbero un
    primo segmento — e nessun altro test se ne accorgerebbe."""
    registro = {nome for nome, _ in MODULES_REGISTRY}
    assert registro == set(AREA_PREFIX)
    assert len(set(AREA_PREFIX.values())) == len(AREA_PREFIX), \
        "due aree non possono condividere lo stesso prefisso"
    for prefisso in AREA_PREFIX.values():
        assert prefisso and prefisso.isascii() and prefisso.islower()
        assert "." not in prefisso


def test_i_pesi_restano_una_scala_chiusa():
    """WEIGHTS e' dichiarata chiusa perche' l'ordinamento del piano di
    interventi resti leggibile: senza, fra qualche fase comparirebbe un
    1.7 scritto da qualcuno e nessuno saprebbe dire cosa significa."""
    prodotti = {normalizza_severita(scala, valore)[1]
                for scala in ("mars", "axe", "zap")
                for valore in ("critico", "grave", "medio", "lieve",
                               "critical", "serious", "moderate", "minor",
                               "high", "medium", "low", "informational",
                               "ignoto")}
    prodotti |= {severita_lighthouse(0, "binary", p)[1]
                 for p in (0, 1, 93 / 23)}
    assert prodotti <= set(WEIGHTS)


def test_la_versione_del_readme_segue_quella_del_codice():
    """Il numero di versione vive in due posti, e devono coincidere.

    `__version__` governa il referto e lo `User-Agent` del crawler; il
    README lo dichiara in testa insieme a che cosa quella versione
    porta. Alzarne uno solo non rompe nulla — e' esattamente la deriva
    fra documentazione e codice di R32 — quindi a legarli serve un
    test, non l'attenzione.
    """
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(radice, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    dichiarate = re.findall(r"^Versione (\d+\.\d+\.\d+)", readme,
                            re.MULTILINE)
    assert dichiarate == [mars_core.__version__], (
        "README dichiara %s, il codice %s" % (dichiarate,
                                              mars_core.__version__))


def test_le_istruzioni_di_progetto_sono_tutte_importate():
    """CLAUDE.md non contiene piu' le istruzioni: le importa.

    Ogni file sotto `.claude/` deve avere la sua riga `@`, e ogni riga
    `@` deve puntare a un file che c'e'. Il difetto che questo test
    coglie e' **muto in entrambe le direzioni**: un file senza la riga
    esiste, si apre e si legge benissimo, ma nel contesto non arriva
    mai; una riga senza il file non produce un errore, solo un pezzo di
    istruzioni che sparisce. E' la stessa forma di R47 — chi sa una
    cosa e non la dichiara la toglie di mezzo senza un errore.
    """
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(radice, "CLAUDE.md"), encoding="utf-8") as fh:
        indice = fh.read()
    importati = set(re.findall(r"^@(\S+)$", indice, re.MULTILINE))
    presenti = {"/".join(p.parts[-2:]) for p
                in pathlib.Path(radice, ".claude").glob("*.md")}
    assert presenti, ".claude/ e' vuota: la divisione e' stata disfatta"
    assert importati == presenti, (
        "senza riga @: %s; senza file: %s"
        % (sorted(presenti - importati), sorted(importati - presenti)))


def test_lo_user_agent_porta_la_versione():
    """Il sito analizzato vede quale versione lo sta scansionando: e'
    cio' che permette a chi legge i log di sapere con che cosa ha a che
    fare, e va aggiornato insieme al resto."""
    assert mars_core.USER_AGENT == "MARSBeacon/%s" % mars_core.__version__


# ----------------------------------------------------------------------
# U8: la profondita' di crawl
# ----------------------------------------------------------------------

def test_il_crawler_registra_la_distanza_dalla_home():
    """Un click per livello, seguendo i link: e' la misura che dice se
    un contenuto sta in vista o in fondo a un corridoio."""
    pagine = {
        "http://esempio.test/": '<html><body><a href="/a">a</a></body></html>',
        "http://esempio.test/a": '<html><body><a href="/b">b</a></body></html>',
        "http://esempio.test/b": "<html><body>fine</body></html>",
    }
    risposte = {"http://esempio.test/robots.txt": ("", "text/plain")}
    risposte.update({u: (c, "text/html") for u, c in pagine.items()})
    crawler = _crawler_finto(risposte)
    risultato = crawler.crawl()
    assert crawler.discovery == "link interni"
    assert {u: p["depth"] for u, p in risultato.items()} == {
        "http://esempio.test/": 0,
        "http://esempio.test/a": 1,
        "http://esempio.test/b": 2}


def test_dalla_sitemap_la_profondita_resta_ignota():
    """Dichiarate dal sito, non necessariamente raggiungibili per link:
    chiamarle «profondita' 0» direbbe che stanno in home, e ignota e'
    l'unica risposta vera."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/x", "http://esempio.test/y"],
        **{"http://esempio.test/x": "<html><body>x</body></html>",
           "http://esempio.test/y": "<html><body>y</body></html>"})
    risultato = crawler.crawl()
    assert crawler.discovery == "sitemap"
    assert [p["depth"] for p in risultato.values()] == [None, None]


def test_i_link_in_uscita_si_registrano_anche_venendo_dalla_sitemap():
    """Il grafo dei link e' un dato della PAGINA, non della strategia
    di scoperta: prima venivano estratti solo nel ramo che li segue, e
    un sito con sitemap — cioe' quasi tutti — sarebbe rimasto senza
    architettura da mostrare."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/x", "http://esempio.test/y"],
        **{"http://esempio.test/x":
           '<html><body><a href="/y">y</a><a href="/y">y ancora</a>'
           '<a href="https://altro.test/z">fuori</a></body></html>',
           "http://esempio.test/y": "<html><body>y</body></html>"})
    risultato = crawler.crawl()
    assert crawler.discovery == "sitemap"
    # Deduplicati (la stessa voce di menu e' un arco solo) e senza
    # l'host esterno, che non fa parte di questo sito.
    assert risultato["http://esempio.test/x"]["link_targets"] == [
        "http://esempio.test/y"]
    assert risultato["http://esempio.test/y"]["link_targets"] == []


def test_un_link_a_se_stessa_non_e_un_arco():
    """Un cerchio che punta a se' non dice nulla dell'architettura, e
    falserebbe il conteggio dei link in entrata."""
    crawler = _crawler_con_sitemap(
        ["http://esempio.test/x"],
        **{"http://esempio.test/x":
           '<html><body><a href="/x">io</a><a href="/x#top">io col '
           'frammento</a></body></html>'})
    assert crawler.crawl()["http://esempio.test/x"]["link_targets"] == []


# ----------------------------------------------------------------------
# istanze_del_rilievo (R46)
# ----------------------------------------------------------------------

def test_istanze_del_rilievo_legge_solo_conteggi_veri():
    """`instances` viene dai params di un rilievo, che un plugin di
    terzi puo' scrivere come vuole: e' dato esterno quanto un impact di
    axe.

    Zero e i negativi non sono conteggi — un difetto che ricorre zero
    volte non e' un difetto — e `True` in Python **e'** un `int` che
    vale 1: senza il controllo esplicito, un booleano scritto per
    sbaglio farebbe scendere di un gradino lo sforzo di quel rilievo.
    Nessuno dei due si vede da `_sforzo`, perche' li' un conteggio
    fuori scala si comporta come un conteggio assente."""
    def istanze(valore):
        return mars_core.istanze_del_rilievo({"params": {"instances": valore}})

    assert istanze(1) == 1
    assert istanze(400) == 400
    for non_conteggio in (0, -3, True, False, 1.5, "molte", None, []):
        assert istanze(non_conteggio) is None, non_conteggio
    assert mars_core.istanze_del_rilievo({}) is None
    assert mars_core.istanze_del_rilievo({"params": None}) is None


def test_build_context_porta_il_tetto_dello_spider(monkeypatch):
    """R56: sfuggita alle mutazioni — azzerare `max_children` nel
    context lasciava verde tutto.

    Non e' un parametro del `Crawler` e non deve esserlo: non riguarda
    il crawler di MARS, che ha gia' `--max-pages`, ma l'unico secondo
    crawler che scopre le pagine da se'. Zero e' il default di ZAP,
    cioe' nessun tetto.
    """
    class _CrawlerFinto:
        def __init__(self, *a, **k):
            self.delay = 0.0
            self.robots_info = {"found": False, "text": "", "sitemaps": []}
            self.sitemap_info = {}
            self.discovery = "link interni"
            self.skipped = {}

        def crawl(self):
            return {"https://x/": {"title": "x", "text": "x", "lang": "it",
                                   "html": "<p>x</p>", "headings": [],
                                   "chunks": ["x"]}}

    monkeypatch.setattr(mars_core, "Crawler", _CrawlerFinto)
    ctx = mars_core.build_context("https://x/", 1, "none", "global",
                                  max_children=42)
    assert ctx["max_children"] == 42
    ctx = mars_core.build_context("https://x/", 1, "none", "global")
    assert ctx["max_children"] == 0, "il default e' quello di ZAP"
