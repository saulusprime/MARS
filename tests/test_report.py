#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — referto: dato canonico e sue viste.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import csv
import io
import json
import os
import re

import pytest

from mars_core import (SEV_CRITICAL, SEV_INFO, SEV_WARNING, Finding,
                       load_queries)
import mars_core
import mars_remediation
import mars_report
from mars_core import RRF_K, reciprocal_rank_fusion
from mars_report import (RENDERERS, SOGLIA_BUONO, SOGLIA_MEDIO, _classe,
                         SCALA_K, rrf_sensitivity, _consenso,
                         _ancora, _correzioni, _md_cella,
                         ancore_dei_rilievi,
                         conteggi_per_gravita, depth_distribution,
                         pagine_scansionate, segnali_derivati,
                         surface_math, treemap_data, gravita_per_pagina,
                         _squarify,
                         _plurale, _coda, link_graph_data,
                         _force_layout,
                         _correzioni_testo, _elenco_controlli,
                         _etichetta_area, _area_di, _quadrante, build_report,
                         render_csv, render_html, render_json,
                         render_markdown, render_text, COLONNE_CSV)


@pytest.fixture
def referto(contesto):
    contesto["results"] = {
        # Con un `findings`: dalla Fase 1 ogni area ne emette, e una
        # fixture che non ne ha esercita le viste su una forma che in
        # produzione non esiste — il CSV, per esempio, uscirebbe con la
        # sola intestazione.
        "mars_tech": {"score": 85, "issues": ["[lieve] robots.txt muto"],
                      "findings": [Finding(
                          area="mars_tech", severity=SEV_INFO,
                          key="tech.robots.no_sitemap",
                          title="robots.txt non dichiara la sitemap",
                          params={"penalty": 15.0}).as_dict()]},
        "mars_seo": {"score": None, "status": "unavailable",
                     "issues": ["Lighthouse assente"]},
        # status, tool, score e findings come li dichiarano i moduli
        # veri (R38, U13): senza, la fixture proverebbe una resa che in
        # produzione non esiste. Il punteggio c'e' da U13, e con esso i
        # rilievi che lo spiegano.
        "mars_lexical": {"status": "ranking", "tool": "BM25 (k1=1.5, b=0.75)",
                         "score": 80, "rank": [0, 1],
                         "top_chunk": "https://x/ § H",
                         "queries": ["alfa", "beta"],
                         "issues": ["[grave] 1/2 pagine sotto le 300 parole"],
                         "findings": [Finding(
                             area="mars_lexical", severity=SEV_WARNING,
                             source_severity="grave",
                             key="lex.words.thin",
                             title="1/2 pagine sotto le 300 parole",
                             params={"penalty": 20.0, "pagine": 1,
                                     "totale": 2, "soglia": 300,
                                     "media": 150,
                                     "urls": ["https://x/"]}).as_dict()],
                         "per_query": [{"query": "alfa", "rank": [0, 1]},
                                       {"query": "beta", "rank": [1, 0]}]},
        "mars_semantic": {"status": "ranking", "tool": "proxy char-TFIDF",
                          "score": 92, "rank": [0, 1],
                          "answer_shaped_ratio": 0.5, "n_chunks": 2,
                          "issues": ["[medio] 2 passaggi indicizzabili su 1 "
                                     "pagine, sotto i 20 attesi"],
                          "findings": [Finding(
                              area="mars_semantic", severity=SEV_WARNING,
                              source_severity="medio",
                              key="sem.chunks.few",
                              title="2 passaggi indicizzabili su 1 pagine, "
                                    "sotto i 20 attesi",
                              params={"penalty": 8.0, "chunk": 2,
                                      "pagine": 1,
                                      "soglia": 20}).as_dict()],
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
    for chiave in ("tool", "version", "schema_version", "generated_at",
                   "url", "market", "pages_crawled", "discovery", "chunks",
                   "areas", "rrf", "thresholds", "rrf_simulation",
                   "rrf_aggregate", "citability", "llm_judgement", "skipped",
                   "remediation", "overall"):
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


# Le quattro forme in cui un HTML puo' chiedere un file fuori da se'.
# La prima era l'unica cercata fino a R33: le altre tre — CSS `url()`,
# `@import`, `srcset` — restavano invisibili, e con esse quattro
# regressioni dell'autoconsistenza.
_RIFERIMENTI = re.compile(
    r'(?:src|href)\s*=\s*[\'"]([^\'"]+)'
    r'|srcset\s*=\s*[\'"]([^\'"]+)'
    r'|url\(\s*[\'"]?([^)\'"]+)'
    r'|@import\s+(?:url\(\s*)?[\'"]([^\'"]+)', re.I)


_PRE = re.compile(r"<pre\b[^>]*>.*?</pre>", re.S)


def riferimenti_esterni(html: str) -> list:
    """Gli URL che il referto andrebbe a cercare fuori da se stesso.

    Restituisce la lista vuota su un referto autoconsistente: e' cio'
    che i test asseriscono, e la lista non vuota dice *quale* origine
    e' rientrata, che su un HTML da 300 KB e' l'unica diagnosi utile.
    """
    # Il contenuto di un <pre> non e' markup: i `<` sono gia' `&lt;` e
    # il browser lo rende come testo, quindi un `url(...)` li' dentro
    # non e' una richiesta — e' l'esempio di correzione che il referto
    # mostra a chi legge (I20, dove l'esempio `@font-face` dell'area
    # Prestazioni ha fatto scattare questo controllo per la ragione
    # sbagliata). L'esenzione regge SOLO finche' quel contenuto e'
    # davvero escapato, e `test_nei_blocchi_esempio_non_c_e_markup_vivo`
    # lo verifica: senza quella prova questa riga sarebbe un buco.
    fuori = []
    for src, srcset, in_url, importato in _RIFERIMENTI.findall(
            _PRE.sub("<pre></pre>", html)):
        if srcset:
            # `srcset` e' l'unico attributo che porta piu' URL, separati
            # da virgole, ed e' l'unico che si spezza. Spezzare TUTTI i
            # candidati scavalcherebbe il filtro `data:` qui sotto: un
            # data URI contiene una virgola per specifica, e a pezzi non
            # comincia piu' per `data:` — sui golden uscirebbe `DIGEST`,
            # sulla fixture l'intero base64 della favicon.
            # Dentro `srcset` lo stesso problema non si pone: le virgole
            # di un URL vanno percent-encoded, altrimenti l'attributo e'
            # invalido, quindi qui la virgola separa e basta.
            candidati = [c.strip().split()[0]
                         for c in srcset.split(",") if c.strip()]
        else:
            candidati = [src or in_url or importato]
        for candidato in candidati:
            candidato = candidato.strip()
            # Un frammento non esce dal file: `url(#grafo-freccia)` e' il
            # marcatore delle frecce del grafo (`mars_report`), e gli
            # `href="#..."` sono le ancore stabili dei rilievi. Senza
            # questa esenzione i golden diventano rossi per la ragione
            # sbagliata.
            if candidato and not candidato.startswith(("data:", "#")):
                fuori.append(candidato)
    return fuori


def test_nei_blocchi_esempio_non_c_e_markup_vivo():
    """La prova che rende lecita l'esenzione dei <pre> sopra.

    `riferimenti_esterni` salta il contenuto dei <pre> perche' li' i
    `<` sono escapati e nessun elemento nasce. Se un giorno un esempio
    ci finisse **non** escapato, quell'esenzione diventerebbe un buco:
    uno `<script src>` dentro un <pre> uscirebbe dal file e il
    controllo non lo vedrebbe. Qui si verifica il presupposto invece di
    darlo per buono."""
    for nome in ("referto.html", "referto_degradato.html"):
        percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "golden", nome)
        with open(percorso, encoding="utf-8") as fh:
            html = fh.read()
        for blocco in _PRE.findall(html):
            interno = blocco[blocco.index(">") + 1:-len("</pre>")]
            assert "<" not in interno, \
                "%s: markup vivo dentro un <pre>: %r" % (nome, interno[:80])


def test_html_autoconsistente(referto):
    """Nessuna origine esterna: il referto deve restare un file solo,
    apribile fra due anni da un archivio senza rete.

    Fino alla Fase 8 questo test diceva «nessuno script», e D1 lo ha
    ristretto a ciò che davvero garantisce l'autoconsistenza. Non è un
    allentamento: uno `<script src>` esce dal file, uno `<script>`
    inline no — e il vincolo vero era sempre stato il primo. Il
    presidio sul contenuto dello script sta nei due test qui sotto.

    R33 ha esteso il controllo oltre `src`/`href`: cercava solo quelli,
    e un `url()` nel `<style>`, un `@import` o un `srcset` passavano.
    """
    uscita = render_html(referto)
    assert riferimenti_esterni(uscita) == []
    # Il tipo si legge dai byte del file (R43), quindi il test lo chiede
    # alla stessa funzione invece di cablarlo: cablare `x-icon` era la
    # dichiarazione falsa che la voce ha chiuso.
    with open(os.path.join(os.path.dirname(os.path.abspath(mars_report.__file__)),
                           mars_report.FAVICON), "rb") as fh:
        atteso = mars_report.tipo_icona(fh.read())
    assert "data:%s;base64," % atteso in uscita
    assert atteso == "image/png", \
        "il file si chiama .ico ma e' un PNG: se cambia, cambia il referto"


@pytest.mark.parametrize("nome", ["referto.html", "referto_degradato.html"])
def test_i_golden_html_non_hanno_origini_esterne(nome):
    """Lo stesso controllo sui due referti congelati, e non solo su
    quello della fixture.

    La fixture ha **una** pagina, **un** rilievo e un solo `href` in
    tutto l'HTML: anche esteso, il controllo non attraversa i rami dove
    una regressione ha piu' probabilita' di nascere — il grafo, la
    treemap, il donut, le tabelle. I golden li attraversano tutti.
    """
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "golden", nome)
    with open(percorso, encoding="utf-8") as fh:
        assert riferimenti_esterni(fh.read()) == []


def test_il_controllo_dell_autoconsistenza_vede_le_quattro_forme():
    """R33: il controllo cercava `src` e `href`, e quattro modi su
    cinque di uscire dal file gli passavano davanti.

    Senza questo test l'estensione sarebbe verificabile solo
    reintroducendo a mano la regressione che vuole impedire. Il caso
    `data:` con la virgola e' il piu' insidioso: e' cio' che distingue
    lo split fatto sul solo `srcset` da quello fatto su tutti i
    candidati.
    """
    fuori = "https://cdn.example/x"
    assert riferimenti_esterni('<script src="%s.js"></script>' % fuori)
    assert riferimenti_esterni('<style>@font-face{src:url(%s.woff2)}</style>'
                               % fuori)
    assert riferimenti_esterni("<style>body{background:url('%s.png')}</style>"
                               % fuori)
    assert riferimenti_esterni('<style>@import "%s.css";</style>' % fuori)
    assert riferimenti_esterni('<style>@import url("%s.css");</style>' % fuori)
    assert riferimenti_esterni("<img srcset='%s/a.png 1x, /b.png 2x'>" % fuori)

    # Il relativo dentro `srcset` esce anche lui: e' un file che non c'e'
    # nel referto.
    assert "/b.png" in riferimenti_esterni("<img srcset='/b.png 2x'>")

    # E cio' che resta dentro il file non deve comparire.
    assert riferimenti_esterni('<img src="data:image/png;base64,AAAA">') == []
    assert riferimenti_esterni('<a href="#tech">x</a>') == []
    assert riferimenti_esterni("<path marker-end='url(#grafo-freccia)'/>") == []


def test_la_ripartizione_delle_pagine_non_afferma_cio_che_nessuno_ha_misurato():
    """R49: il donut a tre settori, coi nomi che portano il caveat.

    Il piano prevedeva «senza rilievi / con rilievi / scartate». Due
    vincoli misurati lo hanno cambiato:

    - nessuna area registra QUALI pagine ha guardato — Lighthouse ne
      misura una, axe le prime del campione — quindi «senza rilievi»
      affermerebbe ciò che nessuno ha misurato, su un disegno che si
      legge come una ripartizione esaustiva. Il settore si chiama
      «nessun rilievo le cita», che è la frase già usata dalla treemap;
    - `skipped` non contiene pagine ma MOTIVI, e dentro ci sono un
      altro host e un URL non analizzabile: il terzo settore si chiama
      «URL scartati», non «pagine scartate».
    """
    referto = {
        "pages": [{"url": "https://x/a"}, {"url": "https://x/b"},
                  {"url": "https://x/c"}],
        "skipped": ["altro host: https://altro/", "non HTML: https://x/d.pdf"],
        "areas": [{"findings": [
            {"severity": SEV_CRITICAL, "params": {"urls": ["https://x/a"]}},
            {"severity": SEV_WARNING,
             "params": {"urls": ["https://x/a", "https://x/b"]}},
        ]}],
    }
    quote = mars_report.ripartizione_pagine(referto)

    assert quote["con_rilievi"] == 2
    assert quote["non_citate"] == 1
    assert quote["scartati"] == 2
    # Il totale e' cio' che il crawler ha INCONTRATO, non le sole pagine.
    assert sum(quote.values()) == 5


def test_la_ripartizione_ignora_gli_url_che_non_sono_stati_scansionati():
    """Un rilievo puo' citare un URL che non e' fra le pagine — succede
    con gli strumenti esterni, che seguono i propri redirect. Contarlo
    fra le pagine con rilievi gonfierebbe un settore oltre il totale."""
    referto = {
        "pages": [{"url": "https://x/a"}],
        "skipped": [],
        "areas": [{"findings": [
            {"severity": SEV_CRITICAL,
             "params": {"urls": ["https://x/a", "https://altrove/z"]}}]}],
    }
    quote = mars_report.ripartizione_pagine(referto)

    assert quote["con_rilievi"] == 1
    assert quote["non_citate"] == 0
    assert sum(quote.values()) == 1


def test_la_ripartizione_delle_pagine_compare_nell_hero():
    """I tre settori arrivano fino al disegno, coi nomi decisi. Da I19
    il disegno e' una barra e non piu' un donut: cambia la forma, non i
    nomi — sono loro a portare il caveat di R49."""
    referto = build_report(
        {"mars_tech": {"score": 50, "issues": ["x"], "findings": [
            {"area": "mars_tech", "key": "tech.x", "title": "x",
             "severity": SEV_CRITICAL,
             "params": {"urls": ["https://esempio.test/"]}}]}},
        {"url": "https://esempio.test/", "market": "global",
         "pages": {"https://esempio.test/": {}, "https://esempio.test/b": {}},
         "chunks": [], "discovery": "sitemap",
         "skipped": ["altro host: https://altro/"]})
    uscita = render_html(referto)

    assert "nessun rilievo le cita" in uscita
    assert "con rilievi" in uscita
    assert "URL scartati" in uscita
    # Il disegno resta autoconsistente: nessuna origine esterna.
    assert riferimenti_esterni(uscita) == []


def test_il_layout_ad_anelli_e_aritmetica_e_sta_in_python():
    """R48: la disposizione ad anelli era 26 righe di JavaScript che
    nessun test eseguiva — quattro test guardavano la STRINGA.

    E' aritmetica pura: portarla in Python la rende verificabile con la
    suite di sempre, senza allargare l'ambiente a node e jsdom. Il
    GESTO — eventi, classi, zoom — resta al banco `tools/banco_grafo.py`,
    e R48 non si chiude: si rimpicciolisce.
    """
    # Livelli: la home, due a un click, uno a due, due orfani.
    livelli = [0, 1, 1, 2, None, None]
    punti = mars_report.disposizione_ad_anelli(livelli, 400, 400)

    assert len(punti) == len(livelli)
    cx = cy = 200.0

    def raggio(punto):
        return ((punto[0] - cx) ** 2 + (punto[1] - cy) ** 2) ** 0.5

    # La home sta al centro: e' il livello zero.
    assert raggio(punti[0]) < 0.01
    # Stesso livello, stesso raggio.
    assert abs(raggio(punti[1]) - raggio(punti[2])) < 0.01
    # Piu' lontano dalla home, piu' fuori.
    assert raggio(punti[1]) < raggio(punti[3])
    # Gli orfani stanno FUORI da tutti: non «prima» della home, fuori
    # dal percorso.
    assert raggio(punti[4]) > raggio(punti[3])
    assert abs(raggio(punti[4]) - raggio(punti[5])) < 0.01

    # Sullo stesso anello i nodi si DISTRIBUISCONO. Senza questa
    # asserzione una mutazione che dia a tutti lo stesso angolo passa
    # inosservata — i raggi restano quelli giusti e i nodi finiscono uno
    # sopra l'altro. Misurato: sfuggiva al primo giro di mutazioni.
    assert punti[1] != punti[2]
    assert punti[4] != punti[5]
    # E il primo di ogni anello sta in alto, non a destra: e' la
    # rotazione di -90 gradi, che rende il disegno leggibile.
    assert punti[1][1] < cy and abs(punti[1][0] - cx) < 0.01


def test_il_layout_ad_anelli_regge_i_casi_degeneri():
    """Un grafo di una pagina sola, e uno di soli orfani: il primo non
    deve dividere per zero, il secondo non deve ammucchiare tutto al
    centro."""
    assert mars_report.disposizione_ad_anelli([], 400, 400) == []

    sola = mars_report.disposizione_ad_anelli([0], 400, 400)
    assert sola == [(200.0, 200.0)]

    orfani = mars_report.disposizione_ad_anelli([None, None], 400, 400)
    raggi = [((x - 200.0) ** 2 + (y - 200.0) ** 2) ** 0.5
             for x, y in orfani]
    assert all(r > 1.0 for r in raggi), "gli orfani non stanno al centro"


def test_i_nodi_del_grafo_portano_la_posizione_ad_anelli():
    """Il JavaScript non ricalcola piu' nulla: legge due attributi.

    Si guarda il golden e non la fixture: la fixture non ha un grafo, e
    cercare `grafo-nodo` nel suo HTML da' comunque un riscontro perche'
    la stringa compare nel CSS — un test che passa per la ragione
    sbagliata, cioe' quello che R33 ha appena finito di togliere."""
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "golden", "referto.html")
    with open(percorso, encoding="utf-8") as fh:
        html = fh.read()
    assert "class='grafo-nodo" in html, "il golden non ha piu' un grafo"

    nodi = html.count("class='grafo-nodo")
    etichette = html.count("class='grafo-etichetta")
    # I nodi e le etichette portano entrambi la posizione ad anelli: le
    # seconde non sono una per nodo — oltre una certa dimensione il
    # grafo etichetta solo le piu' linkate — quindi i due conteggi si
    # sommano invece di coincidere.
    assert html.count("data-ax='") == nodi + etichette
    assert html.count("data-ay='") == nodi + etichette
    # E l'aritmetica che il JS ha lasciato non deve tornarci.
    assert "Math.cos" not in mars_report.REFERTO_JS
    assert "Math.PI" not in mars_report.REFERTO_JS
    # `Math.sqrt` era rimasta — la lunghezza dell'arco dentro
    # `ridisegna` — e questo test lo asseriva. La seconda meta' di R48
    # l'ha portata via: le due viste sono due e note, quindi entrambe
    # le geometrie stanno negli attributi e il JavaScript le applica.
    assert "Math.sqrt" not in mars_report.REFERTO_JS


def _referto_citabilita(contesto, risultato):
    return build_report({"mars_citability": risultato}, dict(contesto))


def test_la_citabilita_fallita_compare_nella_vista_testo(contesto):
    """R42: la vista testo saltava `mars_citability` sul NOME del modulo,
    perché ha un blocco tutto suo in fondo — ma quel blocco è protetto
    dai profili. Quando i profili non c'erano, e cioè proprio quando
    qualcosa era andato storto, non si stampava **nulla**: né il nome
    dell'area né il motivo, mentre l'HTML la mostrava.

    Era R38 rimasta aperta per una sola area su nove."""
    rotto = mars_core.errore_modulo(RuntimeError("plugin rotto"))
    testo = render_text(_referto_citabilita(contesto, rotto))
    assert "Citabilit" in testo, "l'area non deve sparire"
    assert "plugin rotto" in testo, "né il motivo"


def test_la_citabilita_senza_profili_compare_lo_stesso(contesto):
    """Il secondo ramo: l'uscita anticipata, quando le altre aree non
    hanno prodotto punteggi. Non è un guasto, ma tacerla lascia il
    lettore senza sapere che l'area esiste."""
    testo = render_text(_referto_citabilita(contesto, {
        "score": None, "status": "unavailable",
        "issues": ["Richiede le altre aree"], "findings": []}))
    assert "Citabilit" in testo
    assert "Richiede le altre aree" in testo


def test_la_citabilita_riuscita_non_compare_due_volte(contesto, referto):
    """L'altro verso, e il motivo per cui la condizione è UNA sola: se
    la vista saltasse l'area sempre o mai, comparirebbe zero o due
    volte. Con i profili presenti deve comparire una volta, nel blocco
    dedicato."""
    testo = render_text(referto)
    assert "Profili di citabilità IA" in testo
    # La riga d'area la produce `_riga_area` dall'etichetta del registro,
    # che comincia col numero d'ordine: e' cio' che la distingue da
    # «Citabilità stimata», che e' il giudizio LLM ed e' un'altra cosa.
    # La prima stesura del test non le distingueva e falliva su quella.
    etichetta = _etichetta_area(_area_di(referto, "mars_citability"))
    righe = [r for r in testo.splitlines() if r.startswith("9. ")]
    assert righe == [], "l'area comparirebbe due volte: %s" % righe
    assert etichetta, "l'area deve esistere nel referto"


def test_il_tipo_dell_icona_si_legge_dai_byte():
    """R43: il file si chiama `favicon.ico` ma `file(1)` dice «PNG image
    data, 32 x 32», e il referto lo dichiarava `image/x-icon`. I browser
    lo digeriscono, ma la dichiarazione era falsa.

    Si legge la firma invece di cablare `image/png`, altrimenti la bugia
    si sposterebbe soltanto al giorno in cui l'icona cambia."""
    assert mars_report.tipo_icona(b"\x89PNG\r\n\x1a\n resto") == "image/png"
    assert mars_report.tipo_icona(b"\x00\x00\x01\x00 resto") == "image/x-icon"
    assert mars_report.tipo_icona(b"GIF89a") == "image/gif"
    assert mars_report.tipo_icona(b"<svg xmlns=") == "image/svg+xml"
    # Byte che non dicono nulla: NON si finge un tipo. Un data URI senza
    # tipo varrebbe text/plain, che nessun browser disegnerebbe.
    assert mars_report.tipo_icona(b"boh") == "application/octet-stream"
    assert mars_report.tipo_icona(b"") == "application/octet-stream"


def test_l_icona_mancante_e_dichiarata(referto, monkeypatch):
    """R43, seconda metà: `except OSError: return ""` faceva sparire la
    riga `<link rel='icon'>` **senza traccia**. Su un checkout parziale
    il referto perdeva l'icona e nessuno lo sapeva.

    La riga compare solo quando succede: un referto sano non guadagna
    rumore, ed è la regola di `wcag.status.no_fixes`."""
    monkeypatch.setattr(mars_report, "FAVICON", "non-esiste.ico")
    uscita = render_html(referto)
    assert "<link rel='icon'" not in uscita
    assert "Icona non incorporata" in uscita
    # E il referto resta valido: nessun riferimento ESTERNO comparso al
    # posto dell'icona. Le ancore interne — `href='#r-...'`, il
    # cancelletto che rende citabile un rilievo — non lo sono, e vanno
    # escluse: senza, il test misurava anche quanti rilievi con un
    # `fix` porti la fixture, che non c'entra con R43 e l'ha reso rosso
    # il giorno in cui U13 ne ha aggiunti.
    assert re.findall(r'(?:src|href)\s*=\s*[\'"](?!data:|#)([^\'"]+)',
                      uscita) == []


def test_l_icona_presente_non_dichiara_nulla(referto):
    """L'altro verso: senza, il vincolo si leggerebbe come «la riga c'è
    sempre», e un referto sano porterebbe un avviso che non gli
    compete."""
    uscita = render_html(referto)
    assert "<link rel='icon'" in uscita
    assert "Icona non incorporata" not in uscita


def _token_palette(html: str) -> dict:
    """I token colore dichiarati in `:root`, letti dal referto reso."""
    blocco = re.search(r":root \{(.*?)\}", html, re.S)
    assert blocco, "nel referto non c'e' una palette"
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})",
                           blocco.group(1)))


def _contrasto(primo: str, secondo: str) -> float:
    """Il rapporto di contrasto WCAG 2.1 fra due colori esadecimali."""
    def luminanza(colore: str) -> float:
        if len(colore) == 4:
            colore = "#" + "".join(c * 2 for c in colore[1:])
        canali = [int(colore[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                   for c in canali]
        return (0.2126 * lineari[0] + 0.7152 * lineari[1]
                + 0.0722 * lineari[2])
    a, b = luminanza(primo), luminanza(secondo)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def test_html_e_solo_chiaro(referto):
    """U11.1: il referto ha un tema solo, deciso dall'utente.

    Sostituisce `test_html_supporta_il_tema_scuro`, che non era
    sbagliato: chiedeva una cosa che il proprietario del referto ha
    deciso di non volere piu'. L'identita' del sito e' pensata per il
    chiaro, e una variante scura inventata da noi non sarebbe la sua."""
    html = render_html(referto)
    assert "prefers-color-scheme" not in html
    assert len(re.findall(r":root \{", html)) == 1, "una palette sola"


def test_la_palette_e_quella_del_sito(referto):
    """I token misurati su lymphatechnologies.com, non scelti a occhio:
    petrolio scuro dei titoli, petrolio dei link, testo del corpo."""
    token = _token_palette(render_html(referto))
    assert token["brand"] == "#0c3540"
    assert token["link"] == "#1e4c5a"
    assert token["fg"] == "#14272b"


def test_ogni_colore_di_testo_passa_il_proprio_controllo(referto):
    """Un referto che misura l'accessibilita' non puo' fallire i propri
    criteri, ed e' cio' che faceva: `--ok` (#0cce6b) e `--warn`
    (#ffa400), presi da Lighthouse, stanno a **2,09:1** e **1,99:1** su
    bianco, cioe' sotto perfino la soglia 3:1 dei componenti. Sono i
    colori con cui il referto scrive i punteggi e i segni dei controlli.

    I colori del sito sono quelli di Bootstrap Italia, disegnati per il
    contrasto: tutti sopra 4,5:1.

    Si controllano TUTTI i fondi su cui quel testo finisce davvero, e
    non il solo bianco: la prima versione di questo test guardava
    `--bg`, passava, e axe sul referto trovava lo stesso quattro
    `<code>` a 4,19:1 — il grigio del sito su `--track`. `--line` resta
    fuori: e' un bordo, non un fondo di testo."""
    token = _token_palette(render_html(referto))
    tutti = ("fg", "muted", "ok", "warn", "bad", "brand", "link")
    # I fondi con SOPRA i colori che ci finiscono davvero. `--track` non
    # prende `ok` e `bad`: e' il fondo degli anelli SVG — dove non c'e'
    # testo — di `code`, di `pre.ex` e del rilievo raggiunto da
    # un'ancora, e li' scrivono `fg`, `muted` e l'etichetta
    # «Correzione:», che e' `warn`. Elencarli e' meno elegante del
    # prodotto cartesiano ed e' l'unica forma vera: chiedere 4,5:1 a una
    # coppia che non esiste avrebbe schiarito `--track` fino a
    # confonderlo con `--card`.
    for fondo, sopra in (("bg", tutti), ("card", tutti),
                         ("track", ("fg", "muted", "warn"))):
        for nome in sopra:
            rapporto = _contrasto(token[nome], token[fondo])
            assert rapporto >= 4.5, "--%s su --%s: %.2f:1" % (
                nome, fondo, rapporto)


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
    esserci, e i quadranti si disegnano in SVG **calcolato in Python**,
    non da uno script — cosi' restano identici anche dove il JavaScript
    non gira, come nella stampa o in un lettore che lo disabilita."""
    uscita = render_html(referto)
    assert uscita.count("<svg viewBox='0 0 120 120'") >= 5
    assert "<script" not in uscita, \
        "senza grafo dei link non c'e' nulla da animare"


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


def test_html_dichiara_classifica_e_voto_per_lessicale_e_semantica(referto):
    """Il voto c'e' da U13, e accanto resta detto che l'area ordina.

    **Questo test asseriva l'opposto** — «nessun voto inventato»,
    `"/100" not in scheda` — ed era giusto finche' le due aree un voto
    non l'avevano. U13 gliel'ha dato, con dei controlli dietro: la
    riscrittura e' la decisione, non un aggiustamento per far tornare
    il verde. Cio' che non cambia e' il meccanismo, che e' il difetto
    da cui il test nacque (R38): la parola arriva dallo STATO
    dichiarato dal modulo, mai dal nome del modulo cablato nella
    vista."""
    uscita = render_html(referto)

    # Lo strumento c'e': un rango senza il nome di chi l'ha calcolato
    # non e' verificabile, e prima il referto non lo diceva affatto.
    assert "BM25 (k1=1.5, b=0.75)" in uscita
    assert "proxy char-TFIDF" in uscita

    schede = uscita.split("<div class='area'>")[1:]
    for etichetta in ("4. Lessicale", "5. Semantica"):
        trovate = [s for s in schede if etichetta in s]
        assert len(trovate) == 1, "scheda %s: %d" % (etichetta, len(trovate))
        assert "/100" in trovate[0], "%s ha un punteggio" % etichetta
        assert "con una classifica dei passaggi" in trovate[0], \
            "%s lo dice accanto al voto, non al suo posto" % etichetta
        assert "non un voto" not in trovate[0]


@pytest.mark.parametrize("modulo, etichetta", [
    ("mars_lexical", "4. Lessicale"),
    ("mars_semantic", "5. Semantica"),
])
def test_un_errore_nelle_aree_di_classifica_non_sparisce(contesto, modulo,
                                                         etichetta):
    """Regressione R38: R22 non valeva per due aree su nove.

    render_text intercettava mars_lexical e mars_semantic per NOME e
    stampava "Analizzato", saltando sia la riga di stato sia il ciclo
    dei rilievi. Un plugin che rompeva spariva dentro una parola che
    dichiarava il contrario — e "un'area persa in silenzio e' peggio
    di una dichiarata fallita" (CLAUDE.md).
    """
    contesto["results"] = {modulo: {"error": "RuntimeError: plugin rotto"}}
    referto = build_report(contesto["results"], contesto)

    testo = render_text(referto)
    assert "errore del modulo" in testo
    assert "RuntimeError: plugin rotto" in testo, \
        "il motivo del fallimento e' il rilievo dell'area"
    assert "Analizzato" not in testo

    # E in HTML: il verdetto non deve piu' essere sovrascritto.
    html = render_html(referto)
    scheda = [x for x in html.split("<div class='area'>")[1:]
              if etichetta in x]
    assert len(scheda) == 1
    assert "errore del modulo" in scheda[0]
    assert "RuntimeError: plugin rotto" in scheda[0]
    # Nessun paragrafo che descriva una classifica inesistente.
    assert "Passaggio in testa" not in scheda[0]


def test_ogni_area_porta_la_chiave_findings(referto):
    """U1.2: il consumatore prima dei produttori.

    build_report copia una LISTA CHIUSA di chiavi: finche' non la
    conosce, un modulo puo' produrre `findings` perfetti e il referto
    li butta via — con i test di modulo tutti verdi. Per questo il
    referto viene adeguato prima dei sei moduli, non dopo.

    La chiave dev'esserci su OGNI area, anche su quelle che non li
    producono ancora: una lista vuota si consuma, una chiave assente
    fa cadere chi la legge.
    """
    for area in referto["areas"]:
        assert isinstance(area["findings"], list), \
            "%s: findings assente o non lista" % area["module"]


def test_un_area_fallita_riceve_un_rilievo_strutturato(contesto):
    """Il modulo non puo' produrlo: e' fallito. Lo sintetizza il referto.

    Un'area in errore e' proprio quella che ha piu' bisogno di comparire
    negli elenchi che si costruiranno sui rilievi — piano di interventi,
    conteggi per gravita', confronto fra due esecuzioni. Senza, sarebbe
    l'unica a sparire da tutti."""
    contesto["results"] = {"mars_tech": {"error": "RuntimeError: rotto"}}
    referto = build_report(contesto["results"], contesto)
    area = referto["areas"][0]

    assert len(area["findings"]) == 1
    f = area["findings"][0]
    assert f["key"] == "tech.status.error", "prefisso d'area, non nome file"
    assert f["area"] == "mars_tech"
    assert "RuntimeError: rotto" in f["detail"], \
        "il motivo del fallimento non va perso"
    # La gravita' e' del nostro strumento, non del sito: gonfiarla
    # sarebbe una misura falsa a danno di chi viene analizzato.
    assert f["severity"] == SEV_INFO
    assert f["weight"] == 1.0


def test_i_findings_sopravvivono_alla_vista_json(referto):
    """render_json fa json.dumps SENZA default=: una dataclass che
    sfuggisse solleverebbe TypeError dopo che tutti i moduli sono
    girati, cioe' nel punto piu' caro possibile."""
    referto["areas"][0]["findings"] = [Finding(
        area="mars_tech", severity=SEV_CRITICAL, key="tech.robots.ai_blocked",
        title="robots.txt blocca i crawler IA", weight=2.0,
        source_severity="critico",
        params={"penalty": 40.0, "bloccati": ["GPTBot"]}).as_dict()]
    riletto = json.loads(render_json(referto))
    f = riletto["areas"][0]["findings"][0]
    assert f["key"] == "tech.robots.ai_blocked"
    assert f["params"]["penalty"] == 40.0
    assert f["source_severity"] == "critico"


def test_i_quadranti_coprono_tutte_le_aree(referto):
    """R38: la fascia saltava mars_lexical e mars_semantic per NOME.

    Due ambiti su nove non comparivano affatto in testa al referto —
    nemmeno per dire che non avevano un voto — mentre il ramo generico
    `score is None` sa gia' disegnare il quadrante tratteggiato con la
    nota di stato, che e' il trattamento onesto. Il caso speciale non
    andava spostato: andava tolto.
    """
    html = render_html(referto)
    # L'elenco atteso viene dal referto stesso: cosi' il test non
    # invecchia quando si aggiunge un'area, e non puo' passare
    # elencando meno di quel che c'e'.
    for area in referto["areas"]:
        nome = _etichetta_area(area)
        assert "<div class='nome'>%s" % nome in html, \
            "%s manca dalla fascia dei quadranti" % nome


def test_html_dichiara_lo_stato_di_cio_che_non_ha_misurato(referto):
    uscita = render_html(referto)
    assert "non misurato" in uscita        # mars_seo, unavailable
    assert "Cosa non è stato guardato" in uscita
    assert "vietato da robots.txt" in uscita


# ----------------------------------------------------------------------
# Query senza riscontro (R23)
# ----------------------------------------------------------------------

def _referto_rrf(matched_lex=True, matched_sem=True, chiavi=True):
    voce_lex = {"query": "q", "rank": [0, 1]}
    voce_sem = {"query": "q", "rank": [0, 1]}
    if chiavi:
        voce_lex["matched"] = matched_lex
        voce_sem["matched"] = matched_sem
    return build_report(
        {"mars_lexical": {"rank": [0, 1], "per_query": [voce_lex],
                          "queries": ["q"]},
         "mars_semantic": {"rank": [0, 1], "per_query": [voce_sem]}},
        {"url": "https://x/", "market": "global", "pages": {"a": {}},
         "queries": ["q"], "discovery": "sitemap", "skipped": [],
         "chunks": [{"url": "https://x/", "heading": "A", "text": "a"},
                    {"url": "https://x/", "heading": "B", "text": "b"}]})


def test_consenso_di_una_query_a_vuoto_non_e_un_numero():
    """Regressione R23: due ordini di scansione identici coincidono.

    Il consenso usciva 3/3 — il risultato migliore possibile — proprio
    dove non c'era un solo riscontro. "nessun riscontro" e "0/3" sono
    cose diverse: la prima dice che la domanda non ha trovato nulla, la
    seconda che i due recuperatori hanno trovato cose diverse.
    """
    voce = _referto_rrf(matched_lex=False)["rrf_simulation"][0]
    assert voce["consensus_top3"] is None
    assert voce["matched"] is False
    assert voce["top_chunk"] is None


def test_basta_un_retriever_a_vuoto_perche_non_ci_sia_confronto():
    for lex, sem in ((False, True), (True, False), (False, False)):
        voce = _referto_rrf(lex, sem)["rrf_simulation"][0]
        assert voce["consensus_top3"] is None
    assert _referto_rrf(True, True)["rrf_simulation"][0][
        "consensus_top3"] is not None


def test_referto_vecchio_senza_il_flag_resta_leggibile():
    """Chi non dichiara `matched` viene considerato misurato: e' la
    lettura compatibile, e vale per i moduli esterni scritti prima."""
    assert _referto_rrf(chiavi=False)["rrf_simulation"][0][
        "consensus_top3"] == 2


@pytest.mark.parametrize("vista", [render_text, render_html],
                         ids=["testo", "html"])
def test_le_viste_dicono_nessun_riscontro(vista):
    assert "nessun riscontro" in vista(_referto_rrf(matched_lex=False))
    assert "nessun riscontro" not in vista(_referto_rrf())


def test_le_query_sopravvivono_a_un_retriever_caduto(tmp_path):
    """Regressione R23: le query vivevano solo dentro rrf_simulation.

    Se un retriever cadeva quella lista era vuota, e `mars_citations
    --from-audit` usciva 2 con "Nessuna query nel referto" — benche'
    load_queries sapesse gia' leggere una chiave `queries` di primo
    livello, che nessuno scriveva.
    """
    r = build_report(
        {"mars_semantic": {"rank": [0], "per_query": []}},
        {"url": "https://x/", "market": "global", "pages": {"a": {}},
         "chunks": [], "discovery": "sitemap", "skipped": [],
         "queries": ["alfa", "beta"]})
    assert r["rrf_simulation"] == [], "il retriever caduto non la produce"
    assert r["queries"] == ["alfa", "beta"]
    f = tmp_path / "r.json"
    f.write_text(render_json(r), encoding="utf-8")
    query, errore = load_queries(report_path=str(f))
    assert errore == ""
    assert query == ["alfa", "beta"]


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
    # La frase intera, non la sola parola: da U8.2 il referto ha una
    # sezione «Superficie» che parla della superficie CONTENUTISTICA,
    # e cercare «superficie» da sola la incontrerebbe in ogni referto.
    # Restringere la spia rende il presidio piu' forte, non piu' debole.
    assert "controllo di superficie" in superficie.lower()
    assert "controllo di superficie" not in completa.lower()


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


# ----------------------------------------------------------------------
# U3.3: la resa dei testi di correzione
# ----------------------------------------------------------------------

def _rilievo(**kw) -> dict:
    base = {"area": "mars_tech", "severity": SEV_CRITICAL, "title": "Titolo",
            "key": "tech.x.y", "detail": "", "fix": "", "example": "",
            "doc_url": "", "weight": 1.0, "source_severity": "",
            "params": {}}
    base.update(kw)
    return base


def test_correzioni_rende_fix_ed_esempio():
    reso = _correzioni([_rilievo(fix="Aggiungi X.", example="<link rel='x'>")])
    assert "Aggiungi X." in reso
    assert "<pre class='ex'>" in reso
    assert "Come si aggiusta" in reso


def test_correzioni_esce_vuoto_senza_nulla_da_dire():
    """Nessun blocco vuoto: un titolo senza contenuto sotto e' rumore."""
    assert _correzioni([]) == ""
    assert _correzioni([_rilievo()]) == ""


def test_correzioni_ignora_chi_ha_solo_una_spiegazione():
    """Il blocco si intitola «Come si aggiusta»: una spiegazione non aggiusta.

    Sono due i casi che verrebbero dentro, e sono proprio quelli che non
    devono starci: l'area in ERRORE, il cui `detail` e' il messaggio
    dell'eccezione, e `wcag.status.no_fixes`, che dice a chi fa girare
    MARS dove manca il locale di axe.
    """
    assert _correzioni([_rilievo(detail="MemoryError: corpus troppo grande")
                        ]) == ""


def test_correzioni_mostra_la_spiegazione_accanto_al_fix():
    """Con un fix la spiegazione serve: e' il PERCHE' prima del COME."""
    reso = _correzioni([_rilievo(detail="Senza CSP il browser non sa.",
                                 fix="Configura l'header.")])
    assert "Senza CSP il browser non sa." in reso
    assert "Configura l&#x27;header." in reso


def test_correzioni_non_ripete_la_gravita_dello_strumento():
    """`[axe:critical]` sta gia' nella riga della vista compatta.

    Il blocco sta due centimetri piu' sotto: ridirlo sarebbe la terza
    volta che il referto dice la stessa cosa nella stessa scheda.
    """
    reso = _correzioni([_rilievo(source_severity="axe:critical", fix="Fai X.")])
    assert "axe:critical" not in reso


def test_correzioni_neutralizza_il_markup_del_sito():
    """Un fix o un esempio possono contenere HTML: sono testo, non markup.

    Il catalogo ne e' pieno per costruzione — gli esempi sono <link>,
    <label>, <table> — e la `solution` di ZAP arriva da fuori.
    """
    reso = _correzioni([_rilievo(fix="<script>alert(1)</script>",
                                 example="<img src=x onerror=alert(1)>",
                                 detail="<b>grassetto</b>")])
    assert "<script>" not in reso
    # `onerror=alert(1)` sopravvive come TESTO, ed e' giusto cosi': il
    # difetto sarebbe un `<img` che apre un tag, non le parole dentro.
    assert "<img" not in reso
    assert "<b>grassetto</b>" not in reso
    assert "&lt;script&gt;" in reso
    assert "&lt;img src=x onerror=alert(1)&gt;" in reso


def test_controlli_agganciano_la_spiegazione_per_id_e_non_per_posizione():
    """L'aggancio e' una CHIAVE: `params["rule"]` e' l'id dell'audit.

    Con i due elenchi in ordine diverso, un aggancio per posizione
    metterebbe la spiegazione sotto il controllo sbagliato — e nessuno
    se ne accorgerebbe, perche' il testo resterebbe plausibile.
    """
    controlli = [{"id": "canonical", "title": "Canonical", "passed": False},
                 {"id": "image-alt", "title": "Alt", "passed": False}]
    rilievi = [_rilievo(area="mars_seo", key="seo.lh.image_alt",
                        detail="Perche' conta l'alt.",
                        params={"rule": "image-alt"}),
               _rilievo(area="mars_seo", key="seo.lh.canonical",
                        detail="Perche' conta il canonical.",
                        params={"rule": "canonical"})]
    reso = _elenco_controlli(controlli, rilievi)
    canonico = reso[reso.index("Canonical"):reso.index("Alt")]
    assert "Perche&#x27; conta il canonical." in canonico
    assert "alt" not in canonico.lower().replace("canonical", "")


def test_un_controllo_fallito_mostra_il_suo_esempio():
    """I20: nell'HTML l'area SEO rende `_elenco_controlli`, non
    `_correzioni`, e quello mostrava `detail` ma non l'esempio. Il
    frammento vero del sito finiva nel JSON e nel Markdown e **non
    nella vista che il committente legge**: consegnarlo cosi' sarebbe
    stato consegnare niente."""
    controlli = [{"id": "image-alt", "title": "Alt", "passed": False}]
    rilievi = [_rilievo(area="mars_seo", key="seo.lh.image_alt",
                        detail="Perche' conta l'alt.",
                        example='<img src="/x.jpg" alt="La sala">',
                        params={"rule": "image-alt",
                                "cited": ['<img src="/img/sala-pesi.jpg">']})]
    reso = _elenco_controlli(controlli, rilievi)
    assert "sala-pesi.jpg" in reso
    assert "Nel tuo sito" in reso
    assert "non è contenuto del tuo sito" in reso
    # La stessa invariante del resto del referto: mai un blocco senza
    # la sua didascalia.
    assert reso.count("<pre class='ex'>") == reso.count("ex-nota") == 2


def test_un_esempio_dal_sito_non_puo_eseguire_niente():
    """Da I20 gruppo B il referto incorpora contenuto del SITO
    ANALIZZATO — lo snippet di axe, l'`evidence` di ZAP — e l'evidence
    di un XSS riflesso E' per definizione un payload. Se l'escaping
    cedesse, aprire un referto eseguirebbe l'attacco che il referto
    denuncia: il file e' pensato per essere archiviato e riaperto anni
    dopo.

    Non basta che i golden lo coprano per caso: qui il payload e'
    l'input del test."""
    payload = "<script>alert(1)</script><img src=x onerror=alert(2)>"
    reso = _correzioni([_rilievo(fix="Codifica l'output.",
                                 example=payload,
                                 params={"example_real": True})])
    # L'invariante e' «nessun ELEMENTO vivo», non «nessuna parola
    # sospetta»: `onerror=` resta nel testo escapato ed e' inerte, ma
    # un `<` non escapato aprirebbe un tag vero.
    assert "<script" not in reso
    assert "<img" not in reso
    assert "&lt;script&gt;" in reso
    assert "&lt;img src=x onerror=alert(2)&gt;" in reso
    # E lo stesso per la vista dei controlli, che e' l'altra strada per
    # cui un esempio arriva nell'HTML.
    controlli = [{"id": "40012", "title": "XSS", "passed": False}]
    rilievi = [_rilievo(area="mars_wapt", key="sec.zap.40012",
                        example=payload,
                        params={"rule": "40012", "example_real": True})]
    assert "<script" not in _elenco_controlli(controlli, rilievi)


def test_un_controllo_superato_non_mostra_esempi():
    """Un controllo superato non si corregge: e' la stessa porta di
    `mars_fixes.prescrivibile`, applicata alla resa."""
    controlli = [{"id": "image-alt", "title": "Alt", "passed": True}]
    rilievi = [_rilievo(area="mars_seo", key="seo.lh.image_alt",
                        example="<img alt='...'>",
                        params={"rule": "image-alt"})]
    assert "<pre class='ex'>" not in _elenco_controlli(controlli, rilievi)


def test_controlli_senza_rilievi_restano_come_prima():
    """Retrocompatibilita': `rilievi` e' facoltativo."""
    reso = _elenco_controlli([{"id": "a", "title": "A", "passed": True}])
    assert "A" in reso
    assert "spiegazione" not in reso


def test_html_nessun_rilievo_solo_senza_findings_e_senza_issues(contesto):
    """Il vincolo di U3.3, e non e' teorico: due aree lo violerebbero.

    `mars_llm_judge` riuscito porta tre issues e ZERO findings (scelta
    di U1.9: i punti deboli non sono rilievi), e un'area che avesse
    solo rilievi strutturati sarebbe il caso opposto. Guardare un solo
    elenco farebbe dire «Nessun rilievo.» a un'area che i rilievi ce
    li ha, cioe' il referto che smentisce se' stesso.
    """
    contesto["results"] = {
        "mars_tech": {"score": 90, "issues": ["Solo issue"], "findings": []},
        # `info`, cosi' il piano non lo prende e il test misura una
        # cosa sola: il ramo «Nessun rilievo.», non la resa del piano.
        "mars_schema": {"score": 90, "issues": [],
                        "findings": [_rilievo(area="mars_schema",
                                              key="sd.a.b",
                                              severity=SEV_INFO,
                                              title="Solo finding")]},
        "mars_wcag": {"score": 100, "issues": [], "findings": []},
    }
    html = render_html(build_report(contesto["results"], contesto))
    assert html.count("Nessun rilievo.") == 1, \
        "solo l'area senza ne' issues ne' findings"
    assert "Solo issue" in html
    # L'area coi soli findings non dice «Nessun rilievo.» ed e' il punto
    # del test. Che poi non mostri nemmeno il titolo e' corretto qui —
    # quel rilievo non ha ne' fix ne' example — e resta un caso
    # ipotetico: oggi ogni modulo che produce findings produce anche
    # issues.
    assert "Solo finding" not in html


def test_html_un_area_con_soli_findings_non_dice_nessun_rilievo(contesto):
    contesto["results"] = {
        "mars_tech": {"score": 90, "issues": [],
                      "findings": [_rilievo(fix="Fai X.")]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "Nessun rilievo." not in html
    assert "Fai X." in html


def test_testo_porta_titolo_e_correzione():
    """Titolo e poi prescrizione: senza il titolo non si sa a che si
    riferisca, perche' fra issues e findings non c'e' una chiave."""
    righe = _correzioni_testo([_rilievo(title="CSP mancante",
                                        fix="Aggiungi l'header.")])
    assert righe == ["  → CSP mancante", "    Aggiungi l'header."]


def test_testo_si_ferma_a_due_come_le_issues():
    """E' la vista che sta in un terminale: due, non nove."""
    molti = [_rilievo(title="T%d" % i, fix="F%d" % i) for i in range(9)]
    assert _correzioni_testo(molti) == ["  → T0", "    F0",
                                        "  → T1", "    F1"]


def test_testo_ignora_i_rilievi_senza_fix():
    """L'area in errore non deve comparire fra le correzioni: il suo
    `detail` e' il messaggio dell'eccezione, non una prescrizione."""
    assert _correzioni_testo([_rilievo(detail="MemoryError: corpus")]) == []
    assert _correzioni_testo([]) == []


def test_ogni_esempio_porta_la_sua_didascalia():
    """R60: un esempio senza etichetta si legge come una misura.

    Nel referto vero di un cliente il blocco «<h2>Quanto dura una
    seduta?</h2>» — che e' l'`example` di `sem.answer_shaped.low` —
    e' stato letto come contenuto di un ALTRO sito finito nel suo. Un
    blocco nginx si riconosce da solo; un esempio scritto in prosa
    italiana plausibile no, ed e' proprio quello che quel rilievo deve
    mostrare, perche' parla della forma della prosa."""
    reso = _correzioni([_rilievo(fix="Aggiungi X.",
                                 example="<h2>Quanto dura?</h2>")])
    assert "non è contenuto del tuo sito" in reso
    # Sopra il blocco, non sotto: dopo averlo letto e' tardi.
    assert reso.index("ex-nota") < reso.index("<pre class='ex'>")


def test_nessun_blocco_esempio_resta_senza_didascalia():
    """L'invariante, e non il solo caso di sopra: i due conteggi
    coincidono su un referto intero, comunque siano i rilievi."""
    for nome in ("referto", "referto_degradato"):
        percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "golden", nome + ".json")
        with open(percorso, encoding="utf-8") as handle:
            referto = json.load(handle)
        for lingua in ("it", "en"):
            html = RENDERERS["html"](referto, lingua)
            # Lo span, non la stringa nuda: `ex-nota` compare anche
            # nella regola CSS, e il conteggio direbbe 8 contro 7.
            assert (html.count("<pre class='ex'>")
                    == html.count("<span class='ex-nota'>")), \
                "%s/%s: esempi e didascalie non coincidono" % (nome, lingua)


def test_la_didascalia_dell_esempio_e_tradotta():
    """Come «Come si aggiusta» due righe piu' su: se restasse italiana
    in un referto inglese sarebbe R44 in un altro punto. E il letterale
    sta nel renderer, non in una costante, perche' e' li' che il
    presidio del catalogo lo va a cercare."""
    rilievo = _rilievo(fix="Add X.", example="<h2>How long?</h2>")
    assert "not content from your site" in _correzioni([rilievo], lang="en")
    assert "non è contenuto del tuo sito" in _correzioni([rilievo])


def test_gli_elementi_del_sito_stanno_accanto_all_esempio():
    """I20: «quali sono i miei» e «come devono diventare» sono due
    domande, e l'esempio risponde alla seconda. Sostituirlo con la prima
    perdeva la forma corretta — misurato sul referto: al posto di
    `<img src="/sala.jpg" alt="La sala trattamenti">` restava `/b.png`.

    Il sito PRIMA: si guarda cio' che si ha, poi come dovrebbe essere."""
    rilievo = _rilievo(fix="Aggiungi alt.",
                       example='<img src="/x.jpg" alt="La sala">',
                       params={"cited": ["/media/sala-pesi.jpg"]})
    reso = _correzioni([rilievo])
    assert "Nel tuo sito" in reso
    assert "sala-pesi.jpg" in reso
    # L'esempio resta, con la didascalia di R60 che qui e' di nuovo
    # vera: quel markup non e' contenuto del sito.
    assert "non è contenuto del tuo sito" in reso
    assert "La sala" in reso
    assert reso.index("Nel tuo sito") < reso.index("non è contenuto")
    # L'invariante: una didascalia per ogni blocco, comunque siano.
    assert reso.count("<pre class='ex'>") == reso.count("ex-nota") == 2


def test_il_tetto_degli_elementi_non_e_muto():
    """I20: cinque nomi su venti, senza dirlo, si leggono come venti su
    venti. Il numero che manca lo porta `cited_total`."""
    rilievo = _rilievo(fix="Aggiungi alt.", example="<img>",
                       params={"cited": ["/a.jpg", "/b.jpg"],
                               "cited_total": 17})
    reso = _correzioni([rilievo])
    assert "15" in reso, "non dice quanti ne restano fuori"
    righe = mars_report._md_rilievo(rilievo)
    assert "15" in "\n".join(righe)


def test_senza_troncamento_il_referto_non_conta_nulla():
    """Nessun «e altri 0»: il silenzio e' la risposta giusta quando la
    lista e' completa."""
    reso = _correzioni([_rilievo(fix="X.", example="<img>",
                                 params={"cited": ["/a.jpg"]})])
    assert "e altri" not in reso


def _voce_piano(**kw):
    base = {"key": "wcag.img.alt_missing", "area": "mars_wcag",
            "area_label": "7. Accessibilità", "severity": SEV_CRITICAL,
            "title": "1/2 immagini prive di alt", "fix": "Dai un alt.",
            "example": '<img src="/x.jpg" alt="La sala">', "doc_url": "",
            "params": {}, "penalty": 5.0, "recovery": 5,
            "score_before": 80, "score_after": 85, "index_gain": None,
            "profile_gains": None, "market": "global", "effort": "ore",
            "quick_win": False, "lane": "misurato", "lane_reason": "",
            "certified": True, "additive": True, "priority": 1}
    base.update(kw)
    return base


def test_il_piano_dice_quali_elementi_ma_su_una_riga():
    """I20: il piano rendeva `fix` e nient'altro, quindi chi agiva di
    li' non sapeva QUALE elemento correggere.

    Su una riga e non nel blocco recintato: l'esempio resta alla scheda
    d'area, e la ragione la fissa gia'
    `test_il_piano_html_non_ripete_gli_esempi` — sedici blocchi di
    codice dentro un elenco di priorita' lo renderebbero illeggibile
    proprio come elenco. Il «quale elemento» invece e' una riga, e
    serve dove si agisce."""
    reso = mars_report._voce_piano_html(
        _voce_piano(params={"cited": ["/b.png"], "cited_total": 4}))
    assert "Nel tuo sito" in reso
    assert "/b.png" in reso
    # «e altri 3», non un 3 qualunque: la prima stesura asseriva `"3"
    # in reso` e passava per un 3 che stava altrove nella scheda — una
    # mutazione che toglieva il conteggio e' sopravvissuta.
    assert "altri 3" in reso, "il tetto resta muto nel piano"
    # L'esempio no: quello sta nella scheda d'area.
    assert "<pre class='ex'>" not in reso
    assert "La sala" not in reso


def test_il_piano_senza_elementi_resta_com_era():
    """La maggior parte delle voci non ha elementi da citare — un
    header mancante e' un'assenza — e li' non deve comparire nulla."""
    reso = mars_report._voce_piano_html(_voce_piano())
    assert "Nel tuo sito" not in reso
    assert "Dai un alt." in reso


def test_senza_elementi_citati_resta_il_solo_esempio():
    """La maggior parte dei rilievi non ha elementi da citare — un
    header mancante e' un'assenza — e li' il blocco non deve comparire
    vuoto."""
    reso = _correzioni([_rilievo(fix="Aggiungi X.", example="<link>")])
    assert "Nel tuo sito" not in reso
    assert reso.count("<pre class='ex'>") == 1


def test_la_didascalia_degli_elementi_citati_e_tradotta():
    """Come «Come si aggiusta» e come quella dell'esempio: italiana in
    un referto inglese sarebbe R44 in un punto nuovo."""
    rilievo = _rilievo(fix="Add alt.", example="<img>",
                       params={"cited": ["/x.jpg"]})
    assert "In your site" in _correzioni([rilievo], lang="en")


def test_il_markdown_elenca_gli_elementi_come_l_html():
    """Le due viste devono dire la stessa cosa — e' la ragione per cui
    esiste il test gemello sull'esempio."""
    righe = mars_report._md_rilievo(
        _rilievo(fix="Fai X.", example="<img>",
                 params={"cited": ["/x.jpg", "/y.jpg"]}))
    testo = "\n".join(righe)
    assert "Nel tuo sito" in testo
    assert "/y.jpg" in testo
    assert testo.index("Nel tuo sito") < testo.index("non è contenuto")


def test_il_markdown_etichetta_l_esempio_come_l_html():
    """Il recinto ``` dice «codice», non «inventato»: le due viste che
    l'esempio lo mostrano devono dire la stessa cosa."""
    righe = mars_report._md_rilievo(_rilievo(fix="Fai X.", example="riga1"))
    testo = "\n".join(righe)
    assert "non è contenuto del tuo sito" in testo
    assert testo.index("non è contenuto") < testo.index("```")


def test_l_etichetta_della_correzione_segue_la_lingua_del_referto():
    """R61, trovato chiudendo R60 due righe piu' su.

    «Correzione: » stava nel CSS come `content`, che nessun catalogo
    puo' tradurre: un referto inglese diceva «How to fix it» in testa
    al blocco e «Correzione:» su ogni voce dentro. Il Markdown la
    traduceva gia' — due viste dello stesso dato, due lingue."""
    assert "Correzione:" in _correzioni([_rilievo(fix="Aggiungi X.")])
    assert "Fix:" in _correzioni([_rilievo(fix="Add X.")], lang="en")

    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "golden", "referto.json")
    with open(percorso, encoding="utf-8") as handle:
        referto = json.load(handle)
    # Sul referto INTERO, CSS compreso: e' li' che la parola italiana
    # si nascondeva, e un controllo sul solo blocco non l'avrebbe vista.
    inglese = RENDERERS["html"](referto, "en")
    assert "Correzione" not in inglese
    assert inglese.count("Fix:") == inglese.count("<span class='fix'>")


def test_testo_lascia_fuori_l_esempio():
    """Cinque o sette righe di nginx per area triplicherebbero il
    referto: gli example vivono nell'HTML e nel JSON, per intero."""
    righe = _correzioni_testo([_rilievo(fix="Fai X.",
                                        example="riga1\nriga2\nriga3")])
    assert not any("riga1" in r for r in righe)


def test_testo_l_area_mostra_solo_cio_che_il_piano_non_prende(contesto):
    """La duplicazione che U4.3 ha tolto, e che si vedeva a occhio.

    Il rilievo critico entra nel piano, quindi sotto l'area non si
    ripete; quello informativo il piano non lo prende — filtra
    `critical` e `warning` — e resta l'unico posto della vista testo
    dove la sua correzione compare.
    """
    contesto["results"] = {
        "mars_tech": {"score": 60, "issues": ["[critico] robots muto"],
                      "findings": [
                          _rilievo(title="robots muto",
                                   key="tech.robots.missing",
                                   fix="Pubblica un robots.txt."),
                          _rilievo(title="canonical assente",
                                   key="tech.canonical.missing",
                                   severity=SEV_INFO,
                                   fix="Dichiara il canonical.")]}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert testo.count("Pubblica un robots.txt.") == 1, "solo nel piano"
    assert "  → robots muto" not in testo
    assert "  → canonical assente" in testo
    assert "    Dichiara il canonical." in testo


# ----------------------------------------------------------------------
# U4.2: il piano nel dato canonico
# ----------------------------------------------------------------------

def test_il_piano_e_una_lista_anche_quando_e_vuoto(contesto):
    """Chiave sempre presente, come `findings` in U1.2.

    Una lista vuota si consuma, una chiave assente fa cadere chi la
    legge — e chi la leggera' sono il CSV della Fase 6 e il confronto
    della Fase 7, che nascono dopo e non possono verificarla.
    """
    contesto["results"] = {"mars_tech": {"score": 100, "issues": []}}
    referto = build_report(contesto["results"], contesto)
    assert referto["remediation"] == []


def test_il_piano_nasce_dopo_le_aree_e_la_citabilita(contesto):
    """L'ordine non e' un dettaglio: il piano RILEGGE il referto.

    Gli servono le aree — per le penalita' e i punteggi — e la
    citabilita', per i coefficienti. Costruito dentro il letterale che
    le definisce, le troverebbe assenti e uscirebbe senza guadagni,
    senza un solo errore.
    """
    contesto["results"] = {
        "mars_tech": {"score": 57, "issues": ["[critico] robots muto"],
                      "findings": [Finding(
                          area="mars_tech", severity=SEV_CRITICAL,
                          key="tech.robots.ai_blocked",
                          title="robots.txt BLOCCA 1 crawler IA",
                          params={"penalty": 43.0}).as_dict()]},
        "mars_citability": {"score": 50.0, "market": "global",
                            "profiles": {"Claude": 50.0},
                            "signals": {"Accesso e indicizzabilità": 57.0},
                            "issues": []},
    }
    piano = build_report(contesto["results"], contesto)["remediation"]
    assert len(piano) == 1
    assert piano[0]["recovery"] == 43, "senza le aree non ci sarebbe"
    assert piano[0]["index_gain"] is not None, "senza la citabilita' nemmeno"
    assert piano[0]["market"] == "global"


def test_il_piano_e_lo_stesso_che_costruisce_mars_remediation(referto):
    """Una copia sola: la vista non ricalcola, legge.

    Se un giorno una resa ricostruisse il piano per conto suo, le due
    copie divergerebbero senza che nulla si rompa — e' lo stesso
    argomento per cui la sezione citabilita' non ha una `top_actions`
    duplicata.
    """
    assert referto["remediation"] == mars_remediation.build_remediation(
        referto)


def test_il_piano_sopravvive_alla_vista_json(referto):
    """`render_json` fa `json.dumps` senza `default=`: un valore non
    serializzabile romperebbe dopo che tutti i moduli sono girati."""
    reso = json.loads(render_json(referto))
    assert reso["remediation"] == referto["remediation"]


def test_un_area_fallita_non_entra_nel_piano(contesto):
    """`_finding_errore` sintetizza `*.status.error`, che il piano
    esclude due volte: e' `info` ed e' un rilievo di stato. Un piano
    che dicesse "correggi il MemoryError" avrebbe sbagliato lettore."""
    contesto["results"] = {"mars_tech": {"error": "MemoryError: corpus"}}
    referto = build_report(contesto["results"], contesto)
    assert referto["areas"][0]["findings"], "l'area il rilievo ce l'ha"
    assert referto["remediation"] == []


# ----------------------------------------------------------------------
# U4.3: il piano nella vista testo
# ----------------------------------------------------------------------

def _referto_con_piano(contesto, quanti=1):
    rilievi = [_rilievo(key="tech.robots.ai_blocked", title="robots blocca",
                        fix="Togli il Disallow.", params={"penalty": 43.0})]
    for n in range(quanti - 1):
        rilievi.append(_rilievo(key="tech.sitemap.missing",
                                title="sitemap assente %d" % n,
                                severity=SEV_WARNING, fix="Pubblicala.",
                                params={"penalty": 0.0}))
    contesto["results"] = {
        "mars_tech": {"score": 57, "issues": [], "findings": rilievi},
        # Senza `signals` i coefficienti non esistono e il guadagno
        # d'indice non comparirebbe: e' il ramo degradato, provato
        # altrove.
        "mars_citability": {"score": 57.0, "market": "eu", "issues": [],
                            "profiles": {"Claude": 57.0},
                            "signals": {"Accesso e indicizzabilità": 57.0}},
    }
    return build_report(contesto["results"], contesto)


def test_il_piano_a_testo_dichiara_i_conteggi(contesto):
    testo = render_text(_referto_con_piano(contesto))
    assert "PIANO DI INTERVENTI  : 1 interventi (1 critici, 0 avvertenze)" \
        in testo
    assert "1. [CRITICO · Tecnica · minuti] robots blocca" in testo
    assert "+43 punti d'area (57 → 100)" in testo
    assert "Togli il Disallow." in testo


def test_il_piano_a_testo_marca_i_quick_win(contesto):
    assert "** QUICK WIN" in render_text(_referto_con_piano(contesto))


def test_il_piano_a_testo_si_ferma_a_cinque(contesto):
    """Come i cinque alert ZAP e le cinque violazioni axe: la vista
    compatta ne mostra cinque, il dato li porta tutti — e la riga di
    troncamento lo dichiara invece di lasciarlo intuire."""
    testo = render_text(_referto_con_piano(contesto, quanti=9))
    assert testo.count("[CRITICO ·") + testo.count("[AVVERTENZA ·") == 5
    assert "... e altri 4 interventi" in testo


def test_il_piano_a_testo_c_e_anche_quando_e_vuoto(contesto):
    """Le altre tre sezioni spariscono quando manca il dato; qui
    sarebbe un errore, perche' un piano che sparisce non si distingue
    da un piano non calcolato."""
    contesto["results"] = {"mars_tech": {"score": 100, "issues": []}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert "PIANO DI INTERVENTI  : nessun rilievo critico o di avvertenza" \
        in testo


def test_il_piano_a_testo_non_tace_dove_manca_un_numero(contesto):
    """Un rilievo senza recupero non deve lasciare la riga vuota: al
    posto del numero va il motivo, e sono tre motivi diversi."""
    contesto["results"] = {"mars_tech": {
        "score": 100, "issues": [],
        "findings": [_rilievo(key="tech.robots.ai_blocked",
                              params={"penalty": 0.0})]}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert "non entra nel punteggio dell'area" in testo
    assert "punti d'area" not in testo


def test_il_piano_a_testo_conta_le_aree_e_non_le_cabla(contesto):
    referto = _referto_con_piano(contesto)
    # Una sola area alimenta il piano su due presenti: la citabilita'
    # non puo' entrarci, i suoi rilievi sono tutti derivati.
    assert "1 aree su 2;" in render_text(referto)


def test_il_piano_a_testo_non_guarda_il_nome_del_modulo(contesto):
    """R42: la citabilita' spariva dalla vista testo perche' la si
    saltava per NOME anche quando falliva. La sezione del piano si
    condiziona sul dato, quindi un'area che cambia nome o un plugin di
    terzi non la fanno sparire."""
    contesto["results"] = {"mars_tech": {
        "score": 57, "issues": [],
        "findings": [_rilievo(area="un_plugin_di_terzi",
                              key="tech.robots.ai_blocked",
                              title="rilievo di un plugin",
                              params={"penalty": 43.0})]}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert "rilievo di un plugin" in testo


# ----------------------------------------------------------------------
# U4.4: il piano nella vista HTML
# ----------------------------------------------------------------------

def test_il_piano_html_ha_badge_e_numeri(contesto):
    html = render_html(_referto_con_piano(contesto))
    assert "<h2>Piano di interventi</h2>" in html
    assert "<span class='badge bad'>CRITICO</span>" in html
    assert "<span class='priorita'>1</span>" in html
    assert "+43 punti d&#x27;area (57 → 100)" in html or \
        "+43 punti d'area (57 → 100)" in html
    assert "<span class='qw'>QUICK WIN</span>" in html


def test_il_piano_html_c_e_anche_quando_e_vuoto(contesto):
    contesto["results"] = {"mars_tech": {"score": 100, "issues": []}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "<h2>Piano di interventi</h2>" in html
    assert "Nessun rilievo critico o di avvertenza" in html


def test_il_piano_html_li_porta_tutti(contesto):
    """Nessun tetto di cinque: e' il documento che si consegna."""
    html = render_html(_referto_con_piano(contesto, quanti=9))
    assert html.count("<div class='intervento'>") == 9


def test_il_piano_html_non_ripete_gli_esempi(contesto):
    """L'`example` resta alla scheda d'area: sedici blocchi di codice
    dentro un elenco di priorita' lo renderebbero illeggibile proprio
    come elenco."""
    contesto["results"] = {"mars_tech": {
        "score": 57, "issues": [],
        "findings": [_rilievo(key="tech.robots.ai_blocked", fix="Fai X.",
                              example="ESEMPIO-UNICO",
                              params={"penalty": 43.0})]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert html.count("ESEMPIO-UNICO") == 1, "solo nella scheda d'area"
    assert html.count("Fai X.") == 2, "nella scheda e nel piano"


def test_il_piano_html_neutralizza_il_markup_del_sito(contesto):
    """Titolo e fix possono contenere HTML: vengono dal sito e dagli
    strumenti, e la `solution` di ZAP e' piena di <meta http-equiv>."""
    contesto["results"] = {"mars_tech": {
        "score": 57, "issues": [],
        "findings": [_rilievo(key="tech.robots.ai_blocked",
                              title="<script>alert(1)</script>",
                              fix="<img src=x onerror=alert(1)>",
                              params={"penalty": 43.0})]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_il_piano_html_dice_perche_un_numero_manca(contesto):
    contesto["results"] = {"mars_tech": {
        "score": 100, "issues": [],
        "findings": [_rilievo(key="tech.robots.ai_blocked",
                              params={"penalty": 0.0})]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "non entra nel punteggio dell&#x27;area" in html
    assert "class='guadagno'" not in html


def test_il_css_del_piano_non_e_ristretto_alle_schede_d_area(referto):
    """Trappola dei selettori annidati: `.area .riga` e' SCOPED.

    Riusare `riga` dentro `.intervento` senza estendere il selettore
    lascerebbe titolo e badge impilati invece che affiancati — un
    difetto che nessun test sul contenuto vedrebbe, perche' l'HTML
    sarebbe identico.
    """
    html = render_html(referto)
    assert ".area .riga, .intervento .riga" in html


def test_il_piano_html_dichiara_che_l_indice_e_una_stima(contesto):
    """I due numeri hanno statuto diverso: i punti d'area sono la stessa
    aritmetica che ha prodotto i punteggi, il guadagno d'indice esce da
    una matrice di pesi editoriali. Il referto lo dice."""
    html = render_html(_referto_con_piano(contesto))
    assert "è una stima derivata dai pesi per assistente" in html
    assert "mercato eu, stima" in html


# ----------------------------------------------------------------------
# R45: il numero dell'altro strumento nelle viste
# ----------------------------------------------------------------------

def _area_con_riferimento(contesto):
    contesto["results"] = {
        "mars_seo": {"score": 27.0, "issues": [],
                     "lighthouse_scores": {"seo": 27.0,
                                           "accessibility": 97.0}},
        "mars_wcag": {"score": 59, "tool": "axe-core",
                      "wcag_level": "WCAG 2.1 A + AA", "pages_tested": 5,
                      "issues": [], "reference_score": 97.0,
                      "reference_tool": "Lighthouse"},
    }
    return build_report(contesto["results"], contesto)


def test_le_viste_mostrano_il_secondo_numero_e_il_perche(contesto):
    """Due numeri in contraddizione sono un dubbio; due numeri con la
    ragione per cui differiscono sono un'informazione in piu'."""
    referto = _area_con_riferimento(contesto)
    for reso in (render_text(referto), render_html(referto)):
        assert "Lighthouse 97/100" in reso
        assert "scala diversa" in reso
    # L'apostrofo tipografico l'HTML lo escapa, quindi la frase per
    # intero si verifica dove arriva intera.
    assert "la nostra è più severa" in render_text(referto)


def test_il_secondo_numero_e_tracciabile(contesto):
    """Il 97 compare nell'area accessibilita', ma viene dal run di
    Lighthouse pagato dall'area SEO: senza `lighthouse_scores` nel dato
    non ci sarebbe modo di risalire a chi l'ha misurato."""
    referto = _area_con_riferimento(contesto)
    seo = [a for a in referto["areas"] if a["module"] == "mars_seo"][0]
    assert seo["lighthouse_scores"]["accessibility"] == 97.0


def test_senza_secondo_numero_le_viste_non_dicono_nulla(contesto):
    contesto["results"] = {"mars_wcag": {"score": 59, "tool": "axe-core",
                                         "issues": []}}
    referto = build_report(contesto["results"], contesto)
    for reso in (render_text(referto), render_html(referto)):
        # "Lighthouse" da solo non basta: compare in un commento del
        # CSS, dove la fascia dei quadranti dichiara da dove viene.
        assert "Lighthouse 97/100" not in reso
        assert "scala diversa" not in reso


def test_il_secondo_numero_zero_non_sparisce(contesto):
    """`if area.get("reference_score")` invece di `is not None` farebbe
    sparire proprio il caso peggiore: un'area a zero secondo l'altro
    strumento."""
    contesto["results"] = {"mars_wcag": {"score": 59, "tool": "axe-core",
                                         "issues": [], "reference_score": 0.0,
                                         "reference_tool": "Lighthouse"}}
    assert "Lighthouse 0/100" in render_text(
        build_report(contesto["results"], contesto))


# ----------------------------------------------------------------------
# U4.5: le azioni con maggior guadagno di profilo
# ----------------------------------------------------------------------

def _referto_profili(contesto):
    """Un critico che muove poco e un'avvertenza che muove molto.

    Serve a distinguere i due ordini: il piano mette il critico
    davanti, questa sezione l'avvertenza.
    """
    contesto["results"] = {
        # Il punteggio dev'essere COERENTE con la penalita', altrimenti
        # l'area non e' certificata e i suoi numeri spariscono: R(2) = 98.
        "mars_tech": {"score": 98, "issues": [], "findings": [
            _rilievo(key="tech.robots.missing", title="critico che muove poco",
                     severity=SEV_CRITICAL, params={"penalty": 2.0})]},
        "mars_schema": {"score": 20, "issues": [], "findings": [
            _rilievo(area="mars_schema", key="sd.jsonld.missing",
                     title="avvertenza che muove molto",
                     severity=SEV_WARNING, params={"penalty": 80.0})]},
        "mars_citability": {
            "score": 55.0, "market": "global", "issues": [],
            "profiles": {"Claude": 55.0, "ChatGPT/Perplexity": 55.0},
            "signals": {"Accesso e indicizzabilità": 98.0,
                        "Dati strutturati": 20.0}},
    }
    return build_report(contesto["results"], contesto)


def test_le_azioni_di_profilo_riordinano_per_solo_guadagno(contesto):
    """Non e' l'elenco dei primi interventi: li' la gravita' domina."""
    referto = _referto_profili(contesto)
    assert [v["key"] for v in referto["remediation"]] == [
        "tech.robots.missing", "sd.jsonld.missing"], "il piano: gravità prima"
    html = render_html(referto)
    prima = html.index("Azioni con maggior guadagno di profilo")
    coda = html[prima:]
    assert coda.index("avvertenza che muove molto") < \
        coda.index("critico che muove poco"), "qui vince il guadagno"


def test_le_azioni_di_profilo_nominano_l_assistente_che_guadagna(contesto):
    """I pesi per assistente sono diversi: la stessa correzione non
    vale uguale per tutti, ed e' l'unica cosa che questa sezione dice e
    il piano no."""
    html = render_html(_referto_profili(contesto))
    assert "soprattutto" in html
    assert "ChatGPT/Perplexity" in html or "Claude" in html


def test_le_azioni_di_profilo_si_fermano_a_tre(contesto):
    contesto["results"] = {
        # base 90 -> R(90) = 10, coerente col punteggio dichiarato.
        "mars_tech": {"score": 10, "issues": [], "findings": [
            _rilievo(key="tech.robots.missing", title="uno",
                     params={"penalty": 30.0}),
            _rilievo(key="tech.sitemap.missing", title="due",
                     params={"penalty": 25.0}),
            _rilievo(key="tech.index.noindex", title="tre",
                     params={"penalty": 20.0}),
            _rilievo(key="tech.index.nofollow", title="quattro",
                     params={"penalty": 15.0})]},
        "mars_citability": {"score": 10.0, "market": "global", "issues": [],
                            "profiles": {"Claude": 10.0},
                            "signals": {"Accesso e indicizzabilità": 10.0}},
    }
    html = render_html(build_report(contesto["results"], contesto))
    coda = html[html.index("Azioni con maggior guadagno di profilo"):]
    assert "quattro" not in coda
    assert coda.count("sull'indice") == 3


def test_senza_guadagni_la_sezione_dei_profili_non_compare(contesto):
    """Senza citabilita' non ci sono coefficienti, quindi non c'e'
    nulla da ordinare: meglio niente che un elenco a guadagno zero."""
    contesto["results"] = {
        "mars_tech": {"score": 57, "issues": [], "findings": [
            _rilievo(key="tech.robots.ai_blocked", params={"penalty": 43.0})]},
        "mars_citability": {"score": 57.0, "market": "global", "issues": [],
                            "profiles": {"Claude": 57.0}},
    }
    html = render_html(build_report(contesto["results"], contesto))
    assert "Azioni con maggior guadagno di profilo" not in html


def test_le_azioni_di_profilo_neutralizzano_il_markup(contesto):
    contesto["results"] = {
        "mars_tech": {"score": 57, "issues": [], "findings": [
            _rilievo(key="tech.robots.ai_blocked",
                     title="<script>alert(1)</script>",
                     params={"penalty": 43.0})]},
        "mars_citability": {"score": 57.0, "market": "global", "issues": [],
                            "profiles": {"Claude": 57.0},
                            "signals": {"Accesso e indicizzabilità": 57.0}},
    }
    html = render_html(build_report(contesto["results"], contesto))
    assert "<script>alert(1)</script>" not in html


# ----------------------------------------------------------------------
# U5.1: il punteggio complessivo
# ----------------------------------------------------------------------

def _referto_complessivo(contesto, **cambi):
    risultati = {"mars_tech": {"score": 60, "issues": []},
                 "mars_schema": {"score": 100, "issues": []}}
    risultati.update(cambi)
    contesto["results"] = risultati
    return build_report(risultati, contesto)


def test_il_complessivo_si_ricostruisce_a_mano(contesto):
    """Due aree a peso 1: (60 + 100) / 2 = 80."""
    complessivo = _referto_complessivo(contesto)["overall"]
    assert complessivo["score"] == 80.0
    assert complessivo["weight_total"] == 2.0
    assert [c["value"] for c in complessivo["components"]] == [60.0, 100.0]


def test_il_complessivo_si_rinormalizza_sulle_aree_misurate(contesto):
    """Un'area senza strumento non abbassa il complessivo, lo rende meno
    informato: e' la stessa regola dei segnali di mars_citability."""
    con_tre = _referto_complessivo(contesto, mars_wapt={
        "score": None, "status": "unavailable", "issues": []})["overall"]
    assert con_tre["score"] == 80.0, "l'area non misurata non pesa"
    assert con_tre["weight_total"] == 2.0


def test_il_segnale_derivato_pesa_una_volta_e_mezza(contesto):
    """(60 + 100 + 1.5*100) / 3.5 = 88.6 — D3."""
    contesto["results"] = {"mars_tech": {"score": 60, "issues": []},
                           "mars_schema": {"score": 100, "issues": []},
                           "mars_semantic": {"status": "ranking",
                                             "answer_shaped_ratio": 1.0,
                                             "n_chunks": 4, "rank": [0]}}
    complessivo = build_report(contesto["results"], contesto)["overall"]
    assert complessivo["weight_total"] == 3.5
    assert complessivo["score"] == 88.6


def test_citabilita_e_llm_restano_fuori_dal_complessivo(contesto):
    """D3: una e' la sintesi degli altri punteggi, l'altra e' opzionale e
    a pagamento — con dentro, lo stesso sito darebbe due complessivi a
    seconda che si sia speso o no."""
    complessivo = _referto_complessivo(
        contesto,
        mars_citability={"score": 10.0, "profiles": {"Claude": 10.0},
                         "issues": []},
        mars_llm_judge={"score": 10, "issues": []})["overall"]
    assert complessivo["score"] == 80.0
    assert complessivo["excluded"] == ["mars_citability", "mars_llm_judge"]


def test_le_aree_di_classifica_restano_fuori_dal_complessivo(contesto):
    """U13 ha dato loro un punteggio, non un posto nella media.

    Le stesse due aree ci entrano gia' dai segnali derivati, a peso 1.5
    ciascuno: contarle anche a 1.0 come aree darebbe a due aree su nove
    esattamente META' del complessivo (1+1+1.5+1.5 su 10). E' la stessa
    ragione per cui D3 tiene fuori `mars_citability`, che sintetizza
    misure gia' contate."""
    # `per_query` da I17: la Recuperabilita' viene dalla media per
    # query, e senza queste voci il segnale sparirebbe dalla media
    # invece di valere zero. I primi tre sono disgiunti apposta.
    complessivo = _referto_complessivo(
        contesto,
        mars_lexical={"score": 0, "status": "ranking", "issues": [],
                      "rank": [0],
                      "per_query": [{"query": "q", "rank": [0, 1, 2],
                                     "matched": True}]},
        mars_semantic={"score": 0, "status": "ranking", "issues": [],
                       "rank": [1], "answer_shaped_ratio": 0.0,
                       "n_chunks": 4,
                       "per_query": [{"query": "q", "rank": [3, 4, 5],
                                      "matched": True}]})["overall"]
    assert "mars_lexical" in complessivo["excluded"]
    assert "mars_semantic" in complessivo["excluded"]
    # I due zeri non entrano nella media; il segnale derivato che ne
    # deriva, quello si': (60 + 100 + 1.5*0 + 1.5*0) / 5 = 32.
    assert [c["value"] for c in complessivo["components"]] == [60.0, 100.0,
                                                               0.0, 0.0]
    assert complessivo["weight_total"] == 5.0


def test_il_punteggio_di_un_area_di_classifica_non_si_dice_non_un_voto(
        contesto):
    """`_qualificatori` annota lo stato solo accanto a un punteggio, e
    da U13 quel punteggio c'e': la frase «classifica, non un voto»
    comparirebbe a due centimetri dal voto che nega."""
    area = {"module": "mars_lexical", "label": "4. Lessicale", "score": 60,
            "status": "ranking", "tool": "BM25 (k1=1.5, b=0.75)"}
    reso = " ".join(mars_report._qualificatori(area))
    assert "non un voto" not in reso
    assert "classifica" in reso, "il fatto resta detto, cambia solo dove"


def test_le_due_aree_escluse_lo_restano_anche_quando_falliscono(contesto):
    """E' il motivo per cui si escludono per NOME: una regola basata sul
    dato le lascerebbe rientrare proprio quando il dato non c'e'."""
    complessivo = _referto_complessivo(
        contesto, mars_citability={"error": "rotto"},
        mars_llm_judge={"error": "rotto"})["overall"]
    assert complessivo["score"] == 80.0
    assert "mars_citability" in complessivo["excluded"]


def test_senza_nulla_da_mediare_il_complessivo_e_none(contesto):
    """Non zero: e' un "non misurato", e il referto li distingue."""
    contesto["results"] = {"mars_tech": {"score": None,
                                         "status": "unavailable",
                                         "issues": []}}
    assert build_report(contesto["results"], contesto)["overall"] is None


def test_i_segnali_derivati_sono_gli_stessi_per_fascia_e_complessivo(contesto):
    """Scritti una volta sola: due implementazioni dello stesso numero
    divergerebbero senza che nulla si rompa (la lezione di R18)."""
    contesto["results"] = {"mars_tech": {"score": 60, "issues": []},
                           "mars_semantic": {"status": "ranking",
                                             "answer_shaped_ratio": 0.5,
                                             "n_chunks": 4, "rank": [0]}}
    referto = build_report(contesto["results"], contesto)
    segnali = segnali_derivati(referto)
    assert [s["name"] for s in segnali] == ["In forma di risposta"]
    assert segnali[0]["value"] == 50.0
    # lo stesso numero compare nella fascia e dentro il complessivo
    assert "su 4 chunk" in render_html(referto)
    assert [c["value"] for c in referto["overall"]["components"]
            if c["name"] == "In forma di risposta"] == [50.0]


def test_la_recuperabilita_e_la_media_per_query_e_ignora_l_aggregato():
    """I17: il consenso aggregato incrocia due classifiche GIA' fuse
    con k — misurato ±18.7 punti di complessivo a sito invariato,
    3/3 con k=10 e 0/3 con k=60 — mentre la media per query incrocia i
    primi 3 delle liste grezze: k non entra per costruzione, ed e' cio'
    che accade davvero al momento del recupero, perche' un assistente
    risponde a una domanda alla volta. L'aggregato resta nel referto
    come diagnostica ma non regge piu' il segnale: qui dice 3/3 e non
    deve entrare."""
    referto = {"rrf_simulation": [
        {"consensus_top3": 0, "consensus_out_of": 3},
        {"consensus_top3": 0, "consensus_out_of": 3},
        {"consensus_top3": 1, "consensus_out_of": 3},
        {"consensus_top3": 1, "consensus_out_of": 3},
        # `consensus_out_of` non e' sempre 3: e' min(3, len(rank)), e
        # su un sito con un chunk solo vale 1. Qui 1/1 vale quota
        # piena, non un terzo — una mutazione che fissava il
        # denominatore a 3 passava con i soli casi da tre attesi.
        {"consensus_top3": 1, "consensus_out_of": 1},
        # Non misurabile: esclusa dalla media, non contata zero (R23).
        {"consensus_top3": None, "consensus_out_of": None},
    ], "rrf_aggregate": {"consensus_top3": 3, "consensus_out_of": 3}}
    segnali = segnali_derivati(referto)
    assert [s["name"] for s in segnali] == ["Recuperabilità"]
    assert segnali[0]["value"] == pytest.approx(100.0 / 3)
    assert "5" in segnali[0]["note"], "la nota dice su quante query"


def test_r65_una_query_da_un_riscontro_solo_vale_sulla_sua_base():
    """Decisione dichiarata (I17 + R65), non una svista: con un
    riscontro solo da un lato il consenso si valuta su cio' che quel
    lato ha trovato — 1/1 se l'altro lo conferma nei suoi primi tre,
    0/1 se no. Non e' il regalo della coda: l'accordo contato e' su un
    chunk che ENTRAMBI hanno davvero trovato, e la resa mostra la base
    («1/1»), non un percento."""
    chunks = [{"url": "https://x/%d" % i, "heading": "h%d" % i,
               "text": "t"} for i in range(6)]
    confermato = _consenso([3], [4, 5, 3, 2], chunks, "q", 60)
    assert (confermato["consensus_top3"],
            confermato["consensus_out_of"]) == (1, 1)
    smentito = _consenso([3], [4, 5, 2, 3], chunks, "q", 60)
    assert (smentito["consensus_top3"],
            smentito["consensus_out_of"]) == (0, 1)


def test_senza_una_query_misurabile_la_recuperabilita_non_esiste():
    """La stessa regola di ogni area: non misurato, non zero — e
    nemmeno il 3/3 che due ordini di scansione identici darebbero
    (R23)."""
    solo_vuote = {"rrf_simulation": [
        {"consensus_top3": None, "consensus_out_of": None}],
        "rrf_aggregate": {"consensus_top3": 3, "consensus_out_of": 3}}
    assert segnali_derivati(solo_vuote) == []
    assert segnali_derivati({}) == []


def test_il_complessivo_e_in_testa_alla_vista_testo(contesto):
    testo = render_text(_referto_complessivo(contesto))
    righe = [r for r in testo.split("\n") if r.strip()]
    # righe[0] e [2] sono i separatori, [1] il titolo del referto.
    assert righe[3].startswith("COMPLESSIVO")
    assert "80/100" in righe[3]
    assert "media pesata di 2 misure" in righe[4]


def test_senza_complessivo_la_riga_non_compare(contesto):
    contesto["results"] = {"mars_tech": {"score": None,
                                         "status": "unavailable",
                                         "issues": []}}
    assert "COMPLESSIVO" not in render_text(
        build_report(contesto["results"], contesto))


@pytest.mark.parametrize("valore,atteso", [
    (100, "buono"), (SOGLIA_BUONO, "buono"), (SOGLIA_BUONO - 1,
                                              "da migliorare"),
    (SOGLIA_MEDIO, "da migliorare"), (SOGLIA_MEDIO - 1, "critico"), (0,
                                                                     "critico"),
])
def test_il_verdetto_segue_le_stesse_soglie_del_colore(contesto, valore,
                                                       atteso):
    """Se un giorno le soglie si ritarano, la parola e il pallino non
    possono divergere: leggono le stesse due costanti."""
    contesto["results"] = {"mars_tech": {"score": valore, "issues": []}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert "(%s)" % atteso in testo
    assert _classe(valore) == {"buono": "ok", "da migliorare": "warn",
                               "critico": "bad"}[atteso]


# ----------------------------------------------------------------------
# U5.2: l'hero
# ----------------------------------------------------------------------

def test_i_conteggi_per_gravita_escludono_i_derivati(contesto):
    """La seconda casella di R41. I derivati ridicono difetti gia'
    misurati altrove: contarli riaprirebbe sui CONTEGGI il doppio
    conteggio che D3 chiude sul punteggio."""
    contesto["results"] = {
        "mars_tech": {"score": 60, "issues": [], "findings": [
            _rilievo(key="tech.robots.missing", severity=SEV_CRITICAL),
            _rilievo(key="tech.canonical.missing", severity=SEV_INFO)]},
        "mars_citability": {"score": 60.0, "issues": [], "profiles": {},
                            "findings": [
                                _rilievo(area="mars_citability",
                                         key="cit.seo.weak",
                                         severity=SEV_INFO,
                                         params={"derived": True})]},
    }
    referto = build_report(contesto["results"], contesto)
    assert conteggi_per_gravita(referto) == {SEV_CRITICAL: 1, SEV_INFO: 1}


def test_un_derivato_grave_resta_comunque_fuori(contesto):
    """Oggi sono tutti `info`, ma e' una protezione incidentale: il
    giorno che uno nascesse `warning`, il conteggio si gonfierebbe in
    silenzio."""
    contesto["results"] = {
        "mars_citability": {"score": 60.0, "issues": [], "profiles": {},
                            "findings": [
                                _rilievo(area="mars_citability",
                                         key="cit.seo.weak",
                                         severity=SEV_CRITICAL,
                                         params={"derived": True})]}}
    referto = build_report(contesto["results"], contesto)
    assert conteggi_per_gravita(referto) == {}


def test_le_tre_quote_coprono_tutte_le_gravita_prodotte(referto):
    """Presidio: se un giorno un modulo emettesse `ok`, la quota non
    ci sarebbe e il rilievo sparirebbe dall'hero senza che nulla si
    rompa. Questo test lo rende rosso invece che invisibile."""
    conteggi = conteggi_per_gravita(referto)
    note = {gravita for gravita, _, _ in mars_report.QUOTE_GRAVITA}
    assert set(conteggi) <= note, "gravità non rappresentata nell'hero: %s" % (
        set(conteggi) - note)


def test_l_hero_mostra_voto_verdetto_e_scala(contesto):
    html = render_html(_referto_complessivo(contesto))
    assert "<section class='hero'>" in html
    assert "aria-label='Complessivo: 80 su 100'" in html
    # 80 sta sotto la soglia del buono, che e' 90.
    assert "<p class='verdetto warn'>da migliorare</p>" in html
    assert "scala dichiarata: critico sotto 50" in html
    assert "media pesata di 2 misure" in html


def test_l_hero_conta_i_rilievi_e_le_pagine(contesto):
    """R49 aveva messo gli URL scartati in un settore del donut, col
    numero accanto al nome. Da I19 il donut non c'e' piu' — su un
    campione a un solo stato era un cerchio pieno di un colore solo —
    ma la forma «<b>N</b> nome» resta, ed e' quella che questo test
    presidia. I conteggi delle gravita' l'hanno adottata a loro volta:
    prima erano tessere di uguale peso visivo."""
    contesto["skipped"] = ["non HTML: https://x/a.pdf", "altro host"]
    contesto["results"] = {"mars_tech": {"score": 60, "issues": [],
                                         "findings": [_rilievo()]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "<b>1</b> critici" in html
    assert "<b>2</b> URL scartati" in html


def test_senza_complessivo_l_hero_non_compare(contesto):
    """Un hero con un trattino al posto del voto non aggiunge niente:
    la fascia dei quadranti dice gia' che non c'e' nulla di misurato."""
    contesto["results"] = {"mars_tech": {"score": None,
                                         "status": "unavailable",
                                         "issues": []}}
    assert "class='hero'" not in render_html(
        build_report(contesto["results"], contesto))


def test_l_hero_riusa_il_quadrante_della_fascia(contesto):
    """Due archi identici da tenere allineati sarebbero due
    implementazioni della stessa cosa: l'hero usa `_quadrante`, e lo si
    vede dal fatto che il suo SVG e' quello."""
    html = render_html(_referto_complessivo(contesto))
    # Quattro dal 2026-08-26: il donut delle pagine (R49) condivide il
    # viewBox perche' condivide la circonferenza — e' la stessa
    # geometria, non una seconda implementazione.
    assert html.count("viewBox='0 0 120 120'") == 3, \
        "hero + due aree"
    assert ".hero .quadrante svg { width:8.5rem" in html


# ----------------------------------------------------------------------
# I19: l'hero ricomposto — la variazione in testa, le quote come barre
# ----------------------------------------------------------------------

def _precedente_senza_riserve(contesto, **cambi):
    """Un'esecuzione precedente della STESSA versione.

    Serve a isolare la variazione dai caveat: fra due versioni diverse
    scattano migrazioni di chiave e misure cambiate, e il confronto
    nasce con riserva per ragioni che non c'entrano con questo test.
    """
    riga = {"generated_at": "2025-12-01T09:00:00+0000",
            "version": mars_core.__version__, "url": contesto["url"],
            "scores": {"mars_tech": 40}, "overall": 40.0, "findings": []}
    riga.update(cambi)
    return riga


def test_l_hero_porta_la_variazione_del_complessivo(contesto):
    """Il numero piu' dinamico che il referto possiede stava duecento
    righe piu' in basso. Il colore segue il SEGNO e non la scala, come
    gia' fa la tabella del delta: qui non si giudica quanto vale il
    sito, si dice se e' salito."""
    html = render_html(_referto_con_delta(
        contesto, _precedente_senza_riserve(contesto)))

    # 40 -> 57: +17, in salita.
    assert "<p class='hero-delta ok'>" in html
    assert "+17" in html


def test_una_variazione_nulla_non_e_ne_buona_ne_cattiva(contesto):
    """Con `ok` per il positivo e `bad` per tutto il resto, «invariato»
    sarebbe rosso. Non e' un peggioramento: e' l'assenza di uno."""
    html = render_html(_referto_con_delta(
        contesto, _precedente_senza_riserve(contesto, overall=57.0)))

    assert "<p class='hero-delta muted'>" in html
    assert "invariato" in html


def test_la_variazione_nell_hero_dichiara_le_riserve(contesto):
    """Un «+17» in testa, grande, senza dire che fra le due esecuzioni
    e' cambiato il metro, e' la promessa di onesta' rotta nel punto piu'
    letto del referto. Il motivo per esteso resta nella sezione del
    delta; qui basta il segnale che ce n'e' uno."""
    referto = _referto_con_delta(contesto,
                                 _precedente_senza_riserve(contesto))
    referto["delta"]["form_factor_changed"] = {"before": "mobile",
                                               "after": "desktop"}
    html = render_html(referto)

    assert "<p class='hero-delta ok con-riserva'>" in html
    assert "con riserva" in html


def test_senza_esecuzione_precedente_l_hero_non_inventa_una_variazione(
        contesto):
    """`delta` e' None alla prima esecuzione: uno «0» in testa direbbe
    «non e' cambiato nulla» invece di «non c'e' un prima»."""
    html = render_html(_referto_complessivo(contesto))

    assert "<p class='hero-delta" not in html
    assert "<section class='hero'>" in html


def test_le_gravita_sono_una_barra_proporzionale(contesto):
    """Tre scatole di uguale peso visivo dicevano che «0 critici» e «5
    avvertenze» pesano uguale. La larghezza e' la quota; una gravita' a
    zero non ha fetta, ma il suo numero resta scritto — zero e' una
    misura, e toglierlo dalla legenda lo farebbe sparire."""
    contesto["results"] = {"mars_tech": {"score": 60, "issues": [], "findings": [
        _rilievo(key="tech.a", severity=SEV_WARNING),
        _rilievo(key="tech.b", severity=SEV_WARNING),
        _rilievo(key="tech.c", severity=SEV_WARNING),
        _rilievo(key="tech.d", severity=SEV_INFO)]}}
    html = render_html(build_report(contesto["results"], contesto))

    assert "<span class='fetta warn' style='width:75.0%'></span>" in html
    assert "<span class='fetta muted' style='width:25.0%'></span>" in html
    # Nessun critico: nessuna fetta, ma il numero si legge lo stesso.
    assert "class='fetta bad'" not in html
    assert "<b>0</b> critici" in html


def _hero_reso(html: str) -> str:
    """Il solo hero: il CSS nomina le stesse classi, e cercarle in
    tutta la pagina darebbe verde a un disegno che non c'e'."""
    return html.split("<section class='hero'>")[1].split("</section>")[0]


def test_senza_rilievi_la_barra_delle_gravita_non_si_disegna(contesto):
    """Una barra vuota si legge come una ripartizione, e non c'e' niente
    da ripartire: e' la stessa regola che il donut applicava a zero URL."""
    hero = _hero_reso(render_html(_referto_complessivo(contesto)))

    assert "<b>0</b> critici" in hero
    assert "class='barra'" not in hero


def test_un_solo_stato_pieno_non_e_una_ripartizione(contesto):
    """Il difetto per cui il donut e' stato tolto: su un campione in cui
    ogni pagina ha un rilievo disegnava un anello intero d'un colore
    solo, promettendo una ripartizione che non mostrava. Una barra piena
    al 100%% ricadrebbe nello stesso punto — i numeri accanto bastano."""
    contesto["skipped"] = []
    contesto["results"] = {"mars_tech": {"score": 60, "issues": [], "findings": [
        _rilievo(key="tech.a", severity=SEV_WARNING,
                 params={"urls": [contesto["url"]]}),
        _rilievo(key="tech.b", severity=SEV_WARNING,
                 params={"urls": [contesto["url"]]})]}}
    hero = _hero_reso(render_html(build_report(contesto["results"], contesto)))

    # Due avvertenze e nient'altro: una fetta sola, quindi nessuna barra.
    assert "<b>2</b> avvertenze" in hero
    assert "class='barra'" not in hero


def test_l_arco_del_quadrante_si_disegna_da_zero(contesto):
    """L'arco si anima solo se il suo punto di partenza e' esprimibile
    in CSS: con `dasharray` variabile il fotogramma iniziale andrebbe
    calcolato per ogni quadrante. Con `dashoffset` la partenza e' la
    circonferenza, una costante, e lo stato BASE resta quello finale —
    cioe' con le animazioni spente il disegno e' gia' giusto."""
    html = render_html(_referto_complessivo(contesto))

    assert "stroke-dasharray='351.86' stroke-dashoffset='70.37'" in html
    assert "@keyframes traccia { from { stroke-dashoffset:351.86; } }" in html


def test_il_movimento_e_tutto_dietro_prefers_reduced_motion(contesto):
    """MARS misura l'accessibilita' altrui: il suo referto non fa
    muovere nulla a chi ha chiesto che non si muova. Il presidio conta
    le `animation`, cosi' una aggiunta fuori dal blocco non passa."""
    html = render_html(_referto_complessivo(contesto))
    dentro = html.split("@media (prefers-reduced-motion: no-preference)")

    assert html.count("animation:") == "".join(dentro[1:]).count("animation:")
    assert html.count("animation:") >= 3, "arco, barre, variazione"


# ----------------------------------------------------------------------
# U5.3: le ancore stabili
# ----------------------------------------------------------------------

def test_l_ancora_viene_dalla_chiave_e_non_dal_titolo():
    """E' la ragione per cui non serve normalizzare i numeri.

    UPGRADE.md prevedeva uno slug ricavato dal titolo, coi numeri
    portati a `n` perche' «2/3 pagine» e «1/3 pagine» non dessero due
    ancore diverse. La chiave della Fase 1 quel problema non ce l'ha:
    per contratto non contiene mai un valore variabile.
    """
    assert _ancora("tech.robots.ai_blocked") == "r-tech-robots-ai-blocked"
    assert _ancora("wcag.axe.color_contrast") == "r-wcag-axe-color-contrast"


def test_l_ancora_non_cambia_se_cambiano_i_conteggi(contesto):
    """La proprieta' che rende citabile un link: due esecuzioni dove
    cambiano solo i numeri devono dare la stessa ancora."""
    def ancore(titolo):
        contesto["results"] = {"mars_tech": {
            "score": 60, "issues": [], "findings": [
                _rilievo(key="tech.canonical.missing", title=titolo,
                         fix="Dichiara il canonical.")]}}
        return ancore_dei_rilievi(build_report(contesto["results"], contesto))
    assert ancore("2/3 pagine senza canonical") == \
        ancore("117/400 pagine senza canonical")


def test_nessun_link_del_referto_punta_a_un_ancora_che_non_esiste(referto):
    """L'invariante che conta. Un href verso un id che nessuno emette
    e' un salto che non succede: la pagina resta valida, il browser non
    protesta, e nessun test sul contenuto se ne accorge."""
    html = render_html(referto)
    emessi = set(re.findall(r"id='(r-[^']+)'", html))
    puntati = set(re.findall(r"href='#(r-[^']+)'", html))
    assert not puntati - emessi, "link rotti: %s" % sorted(puntati - emessi)


def test_le_ancore_del_referto_sono_uniche(referto):
    """Due elementi con lo stesso id: il browser salta al primo, e
    l'altro diventa irraggiungibile senza un errore."""
    html = render_html(referto)
    emessi = re.findall(r"id='(r-[^']+)'", html)
    assert len(emessi) == len(set(emessi))


def test_solo_i_rilievi_resi_ricevono_un_ancora(contesto):
    """Un rilievo senza `fix` ne' `example` la scheda d'area non lo
    mostra come elemento proprio: dargli un'ancora significherebbe
    promettere un salto verso il nulla."""
    # La chiave senza fix e' di una famiglia DINAMICA: quelle che
    # stanno nel catalogo di mars_fixes il fix se lo vedono riempire
    # da `vesti_findings`, e l'ancora la otterrebbero comunque.
    contesto["results"] = {"mars_wcag": {"score": 60, "issues": [], "findings": [
        _rilievo(area="mars_wcag", key="wcag.axe.image_alt",
                 fix="Assicurati che le immagini abbiano un alt."),
        _rilievo(area="mars_wcag", key="wcag.axe.color_contrast",
                 fix="", example="")]}}
    referto = build_report(contesto["results"], contesto)
    assert set(ancore_dei_rilievi(referto)) == {"wcag.axe.image_alt"}
    html = render_html(referto)
    assert "href='#r-wcag-axe-color-contrast'" not in html


def test_il_piano_linka_le_ancore(contesto):
    contesto["results"] = {"mars_tech": {"score": 57, "issues": [], "findings": [
        _rilievo(key="tech.robots.ai_blocked", fix="Togli il Disallow.",
                 params={"penalty": 43.0})]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "<a href='#r-tech-robots-ai-blocked'>" in html
    assert "id='r-tech-robots-ai-blocked'" in html


def test_il_riquadro_in_testa_mostra_i_primi_cinque(contesto):
    html = render_html(_referto_con_piano(contesto, quanti=9))
    coda = html[html.index("Da dove cominciare"):]
    elenco = coda[:coda.index("</ol>")]
    assert elenco.count("<li") == 5


def test_senza_piano_il_riquadro_in_testa_non_compare(contesto):
    contesto["results"] = {"mars_tech": {"score": 100, "issues": []}}
    assert "Da dove cominciare" not in render_html(
        build_report(contesto["results"], contesto))


def test_il_css_evidenzia_il_rilievo_raggiunto(referto):
    """Senza `:target` il salto avviene ma non si vede: in una pagina
    lunga il lettore non sa dove e' atterrato."""
    assert "li:target" in render_html(referto)


# ----------------------------------------------------------------------
# U6: Markdown e CSV
# ----------------------------------------------------------------------

def test_i_nuovi_formati_sono_nel_registro():
    """La CLI li acquisisce da sola: `choices=tuple(RENDERERS)`."""
    assert set(RENDERERS) == {"text", "json", "html", "markdown", "csv"}


def test_il_markdown_neutralizza_le_celle():
    """Due caratteri rompono una tabella GFM, e arrivano da fuori: la
    pipe aprirebbe una colonna in piu', l'a-capo chiuderebbe la riga."""
    assert _md_cella("a|b") == "a\\|b"
    assert _md_cella("prima\nseconda") == "prima seconda"
    assert _md_cella(None) == ""


def test_il_markdown_rende_il_piano_una_task_list(contesto):
    """E' il motivo per cui questo formato esiste: incollato in una
    issue, il piano diventa una checklist spuntabile."""
    reso = render_markdown(_referto_con_piano(contesto, quanti=4))
    piano = reso[reso.index("## Piano di interventi"):
                 reso.index("## Rilievi per area")]
    assert piano.count("\n- [ ] ") == 4
    assert piano.count("- [x]") == 0, "le caselle si consegnano vuote"


def test_il_markdown_marca_la_gravita_con_le_parole(contesto):
    """Mai solo il colore: in Markdown non c'e', e affidare la gravita'
    alla posizione la perderebbe appena qualcuno copia una riga."""
    reso = render_markdown(_referto_con_piano(contesto, quanti=2))
    assert "**[CRITICO]**" in reso
    assert "[AVVISO]" in reso


def test_il_markdown_recinta_gli_esempi(contesto):
    """Indentazione e a-capo di un blocco nginx SONO il suo contenuto."""
    contesto["results"] = {"mars_tech": {"score": 57, "issues": [], "findings": [
        _rilievo(key="tech.robots.ai_blocked", fix="Fai X.",
                 example="riga1\nriga2", params={"penalty": 43.0})]}}
    reso = render_markdown(build_report(contesto["results"], contesto))
    assert "  ```\n  riga1\n  riga2\n  ```" in reso


def test_il_markdown_dichiara_la_scala(referto):
    reso = render_markdown(referto)
    assert "Scala dichiarata: critico sotto 50" in reso


def test_il_csv_ha_il_bom_e_il_punto_e_virgola(referto):
    """Senza BOM, Excel legge un CSV UTF-8 nella codepage di sistema e
    «Accessibilità» diventa «AccessibilitÃ». Senza punto e virgola,
    nelle impostazioni italiane finisce tutto in una colonna."""
    reso = render_csv(referto)
    assert reso.startswith("\ufeff")
    prima = reso[1:].split("\r\n")[0]
    assert prima == ";".join(COLONNE_CSV)


def test_il_csv_ha_una_riga_per_rilievo(referto):
    righe = list(csv.reader(io.StringIO(render_csv(referto)[1:]),
                            delimiter=";"))
    rilievi = [f for a in referto["areas"] for f in a["findings"]]
    assert len(righe) - 1 == len(rilievi)


def test_il_csv_tiene_i_derivati(contesto):
    """R41 esclude i derivati da chi AGGREGA e li tiene per chi li
    mostra uno per uno: il CSV e' esattamente quel caso."""
    contesto["results"] = {"mars_citability": {
        "score": 60.0, "issues": [], "profiles": {},
        "findings": [_rilievo(area="mars_citability", key="cit.seo.weak",
                              severity=SEV_INFO, title="Segnale debole",
                              params={"derived": True})]}}
    reso = render_csv(build_report(contesto["results"], contesto))
    assert "Segnale debole" in reso


def test_il_csv_lascia_vuoto_lo_sforzo_dove_non_e_azionabile(contesto):
    """Vuoto e non «no»: un quick_win a «no» su un rilievo informativo
    sembrerebbe una valutazione che nessuno ha fatto."""
    contesto["results"] = {"mars_tech": {"score": 57, "issues": [], "findings": [
        _rilievo(key="tech.robots.ai_blocked", title="azionabile",
                 params={"penalty": 43.0}),
        _rilievo(key="tech.canonical.missing", title="informativo",
                 severity=SEV_INFO, params={"penalty": 0.0})]}}
    righe = list(csv.reader(
        io.StringIO(render_csv(build_report(contesto["results"], contesto))[1:]),
        delimiter=";"))
    # Per NOME di colonna e non per posizione: aggiungerne una in mezzo
    # — `pagine` e `riferimento` al posto di `url`, R47 — faceva
    # fallire questo test per una ragione che non lo riguarda.
    colonna = {nome: i for i, nome in enumerate(righe[0])}
    per_titolo = {r[colonna["titolo"]]: r for r in righe[1:]}
    assert per_titolo["azionabile"][colonna["sforzo"]] == "minuti"
    assert per_titolo["azionabile"][colonna["quick_win"]] == "sì"
    assert per_titolo["informativo"][colonna["sforzo"]] == ""
    assert per_titolo["informativo"][colonna["quick_win"]] == ""


def test_il_csv_quota_le_celle_ostili(contesto):
    """Un fix di ZAP pieno di virgolette, o un titolo con un punto e
    virgola, spezzerebbe il file se lo si scrivesse a mano."""
    contesto["results"] = {"mars_tech": {"score": 57, "issues": [], "findings": [
        _rilievo(key="tech.robots.ai_blocked",
                 title='titolo; con "virgolette"',
                 fix="prima riga\nseconda riga", params={"penalty": 43.0})]}}
    reso = render_csv(build_report(contesto["results"], contesto))
    righe = list(csv.reader(io.StringIO(reso[1:]), delimiter=";"))
    assert righe[1][4] == 'titolo; con "virgolette"'
    assert righe[1][6] == "prima riga\nseconda riga"


# ----------------------------------------------------------------------
# U7.1: i metadati che rendono un referto rileggibile
# ----------------------------------------------------------------------

def test_lo_schema_e_dichiarato_e_indipendente_dalla_versione(referto):
    """Due numeri diversi, e non e' una ridondanza: `version` cambia a
    ogni fase, `schema_version` solo su un cambiamento incompatibile.
    Chi consuma il JSON da un programma legge questa."""
    assert referto["schema_version"] == mars_core.JSON_SCHEMA_VERSION
    assert referto["schema_version"] != referto["version"]


def test_il_referto_dichiara_i_parametri_della_fusione(referto):
    """Il k viveva come default di una funzione: due esecuzioni con k
    diversi non sono confrontabili, e senza scriverlo bisognerebbe
    aprire il codice di quella versione."""
    assert referto["rrf"] == {"k": mars_core.RRF_K,
                              "formula": mars_core.RRF_FORMULA}
    assert "1 / (k + rank(d) + 1)" in referto["rrf"]["formula"]


def test_il_k_dichiarato_e_quello_che_gira_davvero():
    """Presidio della dichiarazione, non del valore.

    Fino a I3 diceva l'opposto — «nessuno passa un k esplicito» — ed
    era giusto finche' il k era una costante: chi lo passasse avrebbe
    fatto girare la fusione con un numero diverso da quello dichiarato.
    Da I3 il k viene dal contesto, quindi la stessa divergenza si
    ottiene NON passandolo: la chiamata userebbe il default della
    funzione mentre il referto dichiara la scelta dell'utente.

    Il valore non dev'essere un letterale: un `60` scritto a mano in un
    modulo e' esattamente il k inventato che questo presidio esiste per
    impedire. Si guarda il codice perche' e' l'unico posto dove la
    divergenza esiste.
    """
    import ast
    import glob
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chiamate = 0
    for percorso in glob.glob(os.path.join(radice, "mars_*.py")):
        albero = ast.parse(open(percorso, encoding="utf-8").read())
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.Call):
                continue
            nome = getattr(nodo.func, "id", None) or getattr(
                nodo.func, "attr", None)
            if nome != "reciprocal_rank_fusion":
                continue
            chiamate += 1
            argomenti = list(nodo.args[1:]) + [kw.value for kw in nodo.keywords
                                               if kw.arg == "k"]
            assert argomenti, (
                "%s:%d: k non passato, il referto direbbe il falso"
                % (os.path.basename(percorso), nodo.lineno))
            assert not isinstance(argomenti[0], ast.Constant), (
                "%s:%d: k e' un letterale, cioe' inventato li'"
                % (os.path.basename(percorso), nodo.lineno))
    assert chiamate >= 6, "le chiamate sono sei: trovate %d" % chiamate


def test_le_soglie_sono_dichiarate_assenti(referto):
    """`null` e non chiave mancante: quando le soglie arriveranno,
    nessuno dovra' distinguere «assente perche' vecchio» da «assente
    perche' di serie»."""
    assert "thresholds" in referto
    assert referto["thresholds"] is None


# ----------------------------------------------------------------------
# U7.2: il delta nelle viste
# ----------------------------------------------------------------------

def _referto_con_delta(contesto, precedente=None):
    contesto["results"] = {"mars_tech": {"score": 57, "issues": [], "findings": [
        _rilievo(key="tech.robots.ai_blocked", title="robots blocca",
                 params={"penalty": 43.0})]}}
    contesto["previous"] = precedente if precedente is not None else {
        "generated_at": "2025-12-01T09:00:00+0000", "version": "1.0.0",
        "url": contesto["url"], "scores": {"mars_tech": 40},
        "overall": 40.0,
        "findings": [{"area": "mars_tech", "key": "tech.sitemap.missing",
                      "title": "sitemap assente", "severity": "warning"}]}
    return build_report(contesto["results"], contesto)


def test_il_delta_entra_nel_dato_canonico(contesto):
    delta = _referto_con_delta(contesto)["delta"]
    assert delta["previous_run"] == "2025-12-01T09:00:00+0000"
    assert [f["key"] for f in delta["resolved"]] == ["tech.sitemap.missing"]
    assert [f["key"] for f in delta["new"]] == ["tech.robots.ai_blocked"]


def test_alla_prima_esecuzione_il_delta_e_null_e_le_viste_tacciono(contesto):
    """Una sezione «rispetto a prima» con tutto invariato direbbe che
    non è cambiato nulla, che è un'altra cosa da «non c'è un prima». È
    l'opposto della scelta fatta per il piano, dove la sezione resta
    anche vuota: lì il vuoto è un risultato, qui è un'assenza."""
    contesto["results"] = {"mars_tech": {"score": 57, "issues": []}}
    referto = build_report(contesto["results"], contesto)
    assert referto["delta"] is None
    assert "RISPETTO A PRIMA" not in render_text(referto)
    assert "esecuzione precedente" not in render_html(referto)
    assert "esecuzione precedente" not in render_markdown(referto)


def test_le_tre_viste_mostrano_risolti_e_nuovi(contesto):
    referto = _referto_con_delta(contesto)
    for reso in (render_text(referto), render_html(referto),
                 render_markdown(referto)):
        assert "sitemap assente" in reso
        assert "robots blocca" in reso


def test_il_delta_mostra_il_segno_sempre(contesto):
    """«+17» e «-10», mai «17»: senza segno una variazione si legge
    come un punteggio."""
    testo = render_text(_referto_con_delta(contesto))
    assert "+17" in testo, "40 → 57"


def test_il_colore_del_delta_segue_il_segno_non_la_scala(contesto):
    """Qui non si giudica quanto vale l'area, si dice se è salita: un
    59 che sale da 40 è una buona notizia, e la scala dei punteggi lo
    dipingerebbe di rosso."""
    html = render_html(_referto_con_delta(contesto))
    tabella = html[html.index("Rispetto all"):]
    assert "<td class='num ok'>+17</td>" in tabella


def test_il_delta_a_testo_si_ferma_a_tre_per_elenco(contesto):
    molti = {"generated_at": "2025-12-01T09:00:00+0000", "version": "1.0.0",
             "url": contesto["url"], "scores": {}, "overall": None,
             "findings": [{"area": "mars_tech", "key": "tech.k%d" % i,
                           "title": "vecchio %d" % i, "severity": "warning"}
                          for i in range(9)]}
    testo = render_text(_referto_con_delta(contesto, molti))
    assert "... e altri 6" in testo


# ----------------------------------------------------------------------
# U8.1: la superficie come dato
# ----------------------------------------------------------------------

def test_le_pagine_escono_senza_il_loro_contenuto(referto):
    """`context["pages"]` porta anche `html` e `text`, centinaia di
    kilobyte per pagina: nel referto non hanno posto."""
    assert referto["pages"], "il contesto ne ha"
    for pagina in referto["pages"]:
        assert set(pagina) == {"url", "title", "lang", "depth", "headings",
                               "chunks", "words", "links_to",
                               "links_internal", "json_ld_types"}
    json.dumps(referto["pages"])


def test_le_pagine_non_dichiarano_uno_status_che_nessuno_ha_misurato(referto):
    """Solo le 200 entrano in `pages`, il resto va in `skipped`: un 200
    fisso sarebbe una misura che nessuno ha fatto."""
    assert all("status" not in p for p in referto["pages"])


def test_i_tipi_json_ld_si_leggono_anche_dentro_un_graph(contesto):
    """`@type` puo' essere una stringa, una lista, o stare in un
    `@graph`: sono tutte forme che i siti veri usano."""
    contesto["pages"]["https://esempio.test/"]["json_ld"] = [
        '{"@type": "Organization"}',
        '{"@type": ["LocalBusiness", "Store"]}',
        '{"@graph": [{"@type": "FAQPage"}]}',
    ]
    pagine = pagine_scansionate(contesto)
    assert pagine[0]["json_ld_types"] == ["FAQPage", "LocalBusiness",
                                          "Organization", "Store"]


def test_un_json_ld_malformato_non_diventa_un_giudizio(contesto):
    """Che sia rotto lo dice gia' `mars_schema` con un rilievo suo:
    ripeterlo qui sarebbe la seconda voce sullo stesso difetto."""
    contesto["pages"]["https://esempio.test/"]["json_ld"] = ["{rotto",
                                                             '{"@type": "X"}']
    assert pagine_scansionate(contesto)[0]["json_ld_types"] == ["X"]


def test_i_secchielli_di_profondita_contano_le_pagine():
    pagine = [{"depth": 0}, {"depth": 1}, {"depth": 1}, {"depth": 3},
              {"depth": 7}, {"depth": 9}]
    assert depth_distribution(pagine) == [
        {"label": "home", "pages": 1, "unknown": False},
        {"label": "1 click", "pages": 2, "unknown": False},
        {"label": "3 click", "pages": 1, "unknown": False},
        {"label": "4+ click", "pages": 2, "unknown": False}]


def test_le_pagine_di_sola_sitemap_hanno_un_secchiello_loro():
    """E' la scoperta piu' utile della sezione: un contenuto che sta
    nella sitemap e in nessun percorso di navigazione e' un contenuto
    che un assistente trova solo se sa gia' che esiste."""
    assert depth_distribution([{"depth": None}, {"depth": 0}]) == [
        {"label": "home", "pages": 1, "unknown": False},
        {"label": "profondità ignota", "pages": 1, "unknown": True}]


def test_i_secchielli_vuoti_non_compaiono():
    """Un istogramma con dodici colonne da zero non si legge."""
    assert depth_distribution([{"depth": 0}]) == [
        {"label": "home", "pages": 1, "unknown": False}]
    assert depth_distribution([]) == []


# ----------------------------------------------------------------------
# U8.2: la matematica della superficie, e la sua resa
# ----------------------------------------------------------------------

def test_la_superficie_si_ricostruisce_a_mano(contesto):
    """Tre pagine, quattro passaggi: il potenziale è 3 x 4 = 12, cioè
    x3 rispetto ai quattro di adesso."""
    contesto["pages"] = {"https://a/": {}, "https://b/": {}, "https://c/": {}}
    contesto["chunks"] = [{"text": "una parola " * 10} for _ in range(4)]
    m = surface_math(contesto)
    assert (m["pages"], m["chunks"], m["words"]) == (3, 4, 80)
    assert m["chunks_per_page"] == 1.33
    assert m["potential_chunks"] == 12
    assert m["multiplier"] == 3.0


def test_la_proiezione_dichiara_la_propria_assunzione(contesto):
    """È la differenza fra dire «potresti avere 12 passaggi» e dire «se
    ogni pagina arrivasse a 900 parole»: l'assunzione viaggia nel dato
    perché ogni vista la ripeta."""
    m = surface_math(contesto)
    assert "proiezione, non misura" in m["assumption"]
    assert "900" in m["assumption"]
    for reso in (render_text(build_report({}, contesto)),
                 render_html(build_report({}, contesto)),
                 render_markdown(build_report({}, contesto))):
        assert "proiezione, non misura" in reso


def test_senza_pagine_non_c_e_superficie_di_cui_parlare(contesto):
    contesto["pages"] = {}
    assert surface_math(contesto) is None


def test_senza_passaggi_il_moltiplicatore_non_e_uno(contesto):
    """`x1` su zero passaggi suonerebbe come «sei già a posto»."""
    contesto["chunks"] = []
    assert surface_math(contesto)["multiplier"] is None


def test_le_tre_viste_mostrano_la_distribuzione_di_profondita(contesto):
    contesto["pages"]["https://esempio.test/"]["depth"] = 0
    referto = build_report({}, contesto)
    for reso in (render_text(referto), render_html(referto),
                 render_markdown(referto)):
        assert "home" in reso


def test_il_secchiello_delle_ignote_e_giallo_non_rosso(contesto):
    """Non è un livello peggiore degli altri: è un livello che non
    sappiamo, e il rosso lo leggerebbe come un difetto."""
    referto = build_report({}, contesto)
    html = render_html(referto)
    sezione = html[html.index("<h2>Superficie</h2>"):]
    assert "class='bar warn'" in sezione
    assert "class='bar bad'" not in sezione


# ----------------------------------------------------------------------
# U8.3: la treemap della superficie
# ----------------------------------------------------------------------

def _pagine(*coppie) -> list:
    """Le pagine come le espone `pages[]`: url e parole, nient'altro."""
    return [{"url": u, "words": w, "chunks": 1} for u, w in coppie]


def test_l_area_di_ogni_rettangolo_e_proporzionale_alle_parole():
    """È l'unica cosa che la treemap afferma: se le aree non stanno nel
    rapporto dei valori, il disegno mente su ciò che mostra."""
    rettangoli = _squarify([50.0, 30.0, 20.0], 0.0, 0.0, 100.0, 100.0)
    aree = [r["w"] * r["h"] for r in rettangoli]
    assert [round(a) for a in aree] == [5000, 3000, 2000]
    # E riempiono lo spazio dato: senza questo le aree sarebbero
    # proporzionali fra loro ma non alla superficie che si vede.
    assert round(sum(aree)) == 100 * 100


def test_i_rettangoli_non_si_sovrappongono_e_restano_dentro():
    rettangoli = _squarify([9.0, 7.0, 5.0, 3.0, 1.0], 0.0, 0.0, 200.0, 120.0)
    for r in rettangoli:
        assert r["x"] >= -0.001 and r["y"] >= -0.001
        assert r["x"] + r["w"] <= 200.001 and r["y"] + r["h"] <= 120.001
    for i, a in enumerate(rettangoli):
        for b in rettangoli[i + 1:]:
            sovrapposti = (a["x"] < b["x"] + b["w"] - 0.001
                           and b["x"] < a["x"] + a["w"] - 0.001
                           and a["y"] < b["y"] + b["h"] - 0.001
                           and b["y"] < a["y"] + a["h"] - 0.001)
            assert not sovrapposti, (a, b)


def test_lo_spazio_vuoto_non_fa_rettangoli():
    assert _squarify([], 0.0, 0.0, 10.0, 10.0) == []
    assert _squarify([0.0, 0.0], 0.0, 0.0, 10.0, 10.0) == []
    assert _squarify([1.0], 0.0, 0.0, 0.0, 10.0) == []


def test_una_pagina_sola_non_e_una_distribuzione():
    """Un rettangolo che riempie lo spazio ha la stessa forma qualunque
    sia il sito: non dice nulla, e disegnarlo suggerirebbe il
    contrario."""
    assert treemap_data(_pagine(("https://a/", 500))) is None
    assert treemap_data([]) is None


def test_le_pagine_senza_testo_si_contano_invece_di_sparire():
    """Sono quelle che interessano di più, e non hanno superficie da
    disegnare: sparire in silenzio le farebbe sembrare inesistenti
    invece che vuote."""
    mappa = treemap_data(_pagine(("https://a/", 300), ("https://b/", 100),
                                 ("https://c/", 0), ("https://d/", 0)))
    assert (mappa["total"], mappa["shown"], mappa["empty"]) == (4, 2, 2)
    assert [v["url"] for v in mappa["items"]] == ["https://a/", "https://b/"]


def test_il_tetto_ai_rettangoli_e_dichiarato():
    """Quaranta rettangoli sono già più di quanti se ne distinguano: il
    tetto c'è, ma un troncamento taciuto si legge come «è tutto qui»."""
    mappa = treemap_data(_pagine(*[("https://esempio.test/p%02d" % i, 100 + i)
                                   for i in range(50)]))
    assert (mappa["total"], mappa["shown"]) == (50, 40)
    reso = []
    mars_report._treemap_html({"pages": _pagine(
        *[("https://esempio.test/p%02d" % i, 100 + i) for i in range(50)])},
        reso)
    assert "Le 40 più estese di 50 pagine." in "".join(reso)


def test_il_disegno_e_deterministico():
    """I golden congelano l'SVG: due esecuzioni sullo stesso sito devono
    dare gli stessi rettangoli, anche a parità di parole."""
    pagine = _pagine(("https://b/", 100), ("https://a/", 100),
                     ("https://c/", 300))
    primo = treemap_data(pagine)
    secondo = treemap_data(list(reversed(pagine)))
    assert primo == secondo
    assert [v["url"] for v in primo["items"]] == ["https://c/", "https://a/",
                                                  "https://b/"]


def test_le_parole_della_pagina_sono_quelle_dei_suoi_passaggi(contesto):
    """Due numeri sulla stessa cosa che non tornano sono peggio di uno
    solo: la somma delle pagine deve dare il totale di `surface_math`."""
    referto = build_report({}, contesto)
    assert sum(p["words"] for p in referto["pages"]) == \
        referto["surface_math"]["words"]


def _due_pagine(contesto):
    """Il campione minimo perche' la treemap si disegni: sotto le due
    pagine con testo `treemap_data` restituisce None."""
    contesto["pages"]["https://esempio.test/b/"] = dict(
        contesto["pages"]["https://esempio.test/"],
        chunks=[{"url": "https://esempio.test/b/", "heading": "",
                 "text": "una parola " * 40}])
    contesto["chunks"] = [c for p in contesto["pages"].values()
                          for c in p["chunks"]]


def _svg_treemap(html: str) -> str:
    sezione = html[html.index("<svg class='treemap'"):]
    return sezione[:sezione.index("</svg>")]


def test_la_treemap_non_colora_le_pagine_che_nessun_rilievo_cita(contesto):
    """Il grigio non e' un via libera: una pagina che nessun rilievo cita
    puo' essere pulita come puo' non essere stata guardata — Lighthouse
    ne misura una sola, axe le prime del campione. Dipingerla di verde
    sarebbe un giudizio che nessuno ha dato (R21, R47)."""
    _due_pagine(contesto)
    html = render_html(build_report({}, contesto))
    sezione = _svg_treemap(html)
    for colore in ("class='bad'", "class='warn'", "class='muted'",
                   "class='ok'"):
        assert colore not in sezione, \
            "un colore di gravità su una gravità che nessuno ha misurato"
    assert "nessun rilievo la cita" in html
    assert "non vuol dire che siano a posto" in html


def test_la_treemap_colora_la_pagina_che_il_rilievo_dichiara(contesto):
    """Il passo 3 della Fase 8, che R47 ha sbloccato: la gravita'
    peggiore dei rilievi che citano la pagina finisce sul rettangolo, e
    **solo** su quello — l'altra pagina resta senza colore."""
    _due_pagine(contesto)
    contesto["results"] = {"mars_tech": {"score": 40, "issues": [],
                                         "findings": [
        _rilievo(key="tech.index.noindex", severity=SEV_CRITICAL,
                 params={"penalty": 30.0,
                         "urls": ["https://esempio.test/b/"]}),
        _rilievo(key="tech.canonical.missing", severity=SEV_INFO,
                 params={"penalty": 5.0,
                         "urls": ["https://esempio.test/b/"]})]}}
    html = render_html(build_report(contesto["results"], contesto))
    sezione = _svg_treemap(html)
    assert sezione.count("class='bad'") == 1, "solo la pagina citata"
    assert "class='warn'" not in sezione
    # Il colore non viaggia mai da solo: il titolo del rettangolo e la
    # tabella dicono a parole quanti sono e qual e' il peggiore.
    assert "2 rilievi, il peggiore: rilievo critico" in html
    assert "nessun rilievo la cita" in html, "l'altra pagina resta muta"


def test_la_treemap_tiene_la_gravita_peggiore_non_l_ultima(contesto):
    """Due rilievi sulla stessa pagina in ordine crescente di gravita':
    se la mappa tenesse l'ultimo letto invece del peggiore, il critico
    sparirebbe sotto l'informativo."""
    _due_pagine(contesto)
    contesto["results"] = {"mars_tech": {"score": 40, "issues": [],
                                         "findings": [
        _rilievo(key="tech.canonical.missing", severity=SEV_INFO,
                 params={"penalty": 5.0, "urls": ["https://esempio.test/"]}),
        _rilievo(key="tech.index.noindex", severity=SEV_CRITICAL,
                 params={"penalty": 30.0,
                         "urls": ["https://esempio.test/"]})]}}
    referto = build_report(contesto["results"], contesto)
    mappa = gravita_per_pagina(referto)
    assert mappa["https://esempio.test/"]["severity"] == SEV_CRITICAL
    assert mappa["https://esempio.test/"]["findings"] == 2


def test_i_rettangoli_non_sono_fermate_di_tabulazione(contesto):
    """Senza JavaScript il `<title>` al fuoco non compare: quaranta
    fermate che non mostrano nulla sono un ostacolo travestito da
    accessibilità. La lettura accessibile è la tabella."""
    contesto["pages"]["https://esempio.test/b/"] = dict(
        contesto["pages"]["https://esempio.test/"],
        chunks=[{"url": "https://esempio.test/b/", "heading": "",
                 "text": "una parola " * 40}])
    contesto["chunks"] = [c for p in contesto["pages"].values()
                          for c in p["chunks"]]
    html = render_html(build_report({}, contesto))
    svg = html[html.index("<svg class='treemap'"):]
    svg = svg[:svg.index("</svg>")]
    assert "tabindex" not in svg
    assert "role='img'" in svg
    assert "<title>" in svg
    # La tabella di ripiego porta gli stessi numeri dei rettangoli.
    dettagli = html[html.index("<details>"):html.index("</details>")]
    for pagina in ("https://esempio.test/", "https://esempio.test/b/"):
        assert pagina in dettagli


def test_i_rettangoli_restano_confrontabili_a_occhio():
    """È tutto il senso di «squarified»: due aree si confrontano guardandole
    solo se hanno forme simili, e una scheggia lunga trecento volte quanto è
    larga non si confronta con niente. Misurato su questi dieci valori: il
    layout corretto sta a 2.0 di rapporto peggiore, mentre estendere la riga
    quando il rapporto peggiora porta a 327 e riempire dal lato lungo a 72.
    La soglia è larga apposta — non presidia il numero, presidia il metodo."""
    valori = [300.0, 210.0, 150.0, 90.0, 60.0, 40.0, 25.0, 15.0, 10.0, 5.0]
    aspetti = [max(r["w"], r["h"]) / min(r["w"], r["h"])
               for r in _squarify(valori, 0.0, 0.0, 760.0, 420.0)]
    assert max(aspetti) <= 4.0, "rettangoli troppo allungati per confrontarli"


def test_l_accordo_del_singolare():
    """«1 passaggi» è la prima cosa che si nota in un referto che si
    consegna, e costa meno scriverlo giusto che spiegarlo."""
    assert _plurale(1, "passaggio", "passaggi") == "1 passaggio"
    assert _plurale(2, "passaggio", "passaggi") == "2 passaggi"
    assert _plurale(0, "pagina", "pagine") == "0 pagine"


def test_le_etichette_si_troncano_dalla_testa():
    """È la testa che le pagine hanno in comune: su un sito vero i
    percorsi condividono le sezioni, e troncare a destra darebbe dieci
    etichette identiche. Misurato prima di correggerlo: su cinquanta
    pagine sotto lo stesso percorso, tutti e quaranta i rettangoli
    portavano `/sezione-molto-l`."""
    mappa = treemap_data(_pagine(
        *[("https://esempio.test/sezione-molto-lunga-comune/p%02d/" % i,
           400 - i) for i in range(12)]))
    etichette = [v["label"] for v in mappa["items"]]
    assert len(set(etichette)) == len(etichette), \
        "etichette indistinguibili: il troncamento nasconde ciò che varia"
    assert etichette[0].startswith("…") and etichette[0].endswith("/p00/")


def test_un_percorso_corto_non_si_tocca():
    assert _coda("/servizi/", 30) == "/servizi/"
    assert _coda("", 30) == ""
    # Spazio per un carattere solo: meglio niente che il solo segno di
    # troncamento, che non dice quale pagina sia.
    assert _coda("/servizi/", 1) == ""


# ----------------------------------------------------------------------
# U8.4: il grafo dei link, e il primo JavaScript del referto (D1)
# ----------------------------------------------------------------------

def _contesto_collegato(contesto, collegamenti=None) -> dict:
    """Un sito di quattro pagine con dei link fra loro.

    Il `contesto` di serie ne ha una sola, e un grafo di una pagina non
    esiste: quasi tutto ciò che riguarda l'architettura ha bisogno di
    un sito, non di una pagina.
    """
    collegamenti = collegamenti if collegamenti is not None else {
        "https://esempio.test/": ["https://esempio.test/a/",
                                  "https://esempio.test/b/"],
        "https://esempio.test/a/": ["https://esempio.test/b/"],
        "https://esempio.test/b/": ["https://esempio.test/"],
        "https://esempio.test/orfana/": [],
    }
    modello = contesto["pages"]["https://esempio.test/"]
    contesto["pages"] = {
        url: dict(modello, link_targets=list(uscenti),
                  chunks=[{"url": url, "heading": "", "text": "parola " * 30}])
        for url, uscenti in collegamenti.items()}
    contesto["urls"] = list(contesto["pages"])
    contesto["chunks"] = [c for p in contesto["pages"].values()
                          for c in p["chunks"]]
    return contesto


def test_il_layout_del_grafo_e_deterministico():
    """I golden lo congelano, e due esecuzioni sullo stesso sito devono
    dare lo stesso disegno: l'inizializzazione è su un cerchio, non a
    caso, ed è ciò che rende il grafo verificabile."""
    archi = [(0, 1), (1, 2), (2, 0), (0, 3)]
    assert _force_layout(4, archi) == _force_layout(4, archi)


def test_la_home_resta_al_centro_e_nessuno_esce_dal_riquadro():
    posizioni = _force_layout(6, [(0, 1), (0, 2), (1, 3), (4, 5)])
    assert posizioni[0] == (390.0, 270.0), "la home è ancorata al centro"
    for x, y in posizioni:
        assert 0 <= x <= 780 and 0 <= y <= 540


def test_un_grafo_senza_archi_non_e_un_architettura(contesto):
    """Punti senza linee non dicono «il sito non ha link»: dicono che
    fra QUESTE pagine non ne abbiamo visti, ed è un'altra cosa."""
    referto = build_report({}, _contesto_collegato(contesto, {
        "https://esempio.test/": [], "https://esempio.test/a/": []}))
    assert link_graph_data(referto["pages"], referto["url"]) is None
    assert "id='grafo'" not in render_html(referto)


def test_le_pagine_non_raggiunte_dalla_home_sono_orfane(contesto):
    """È la scoperta più utile del grafo: un assistente che segue i
    collegamenti non le incontra mai."""
    referto = build_report({}, _contesto_collegato(contesto))
    grafo = link_graph_data(referto["pages"], referto["url"])
    per_url = {n["url"]: n for n in grafo["nodes"]}
    assert per_url["https://esempio.test/orfana/"]["clicks"] is None
    assert per_url["https://esempio.test/a/"]["clicks"] == 1
    assert per_url["https://esempio.test/"]["clicks"] == 0
    assert grafo["orphans"] == 1


def test_la_home_viene_per_prima_anche_se_nessuno_la_linka(contesto):
    """L'ordine e\' home, poi i piu\' linkati: se il tetto taglia, taglia
    le pagine che il sito stesso richiama di meno — mai il punto di
    partenza. Ed essendo la radice del BFS la sua distanza e\' 0, non
    ignota: non puo\' risultare orfana."""
    referto = build_report({}, _contesto_collegato(contesto, {
        "https://esempio.test/": ["https://esempio.test/a/"],
        "https://esempio.test/a/": []}))
    grafo = link_graph_data(referto["pages"], referto["url"])
    assert grafo["nodes"][0]["home"] and grafo["nodes"][0]["incoming"] == 0
    assert grafo["nodes"][0]["clicks"] == 0
    assert grafo["orphans"] == 0


def test_senza_un_punto_di_partenza_gli_orfani_non_si_contano(contesto):
    """Ogni pagina risulterebbe irraggiungibile, e il numero direbbe
    qualcosa sul sito quando invece dice solo che non sappiamo da dove
    si parte. `None` e non zero, come per i punteggi non misurati."""
    referto = build_report({}, _contesto_collegato(contesto))
    grafo = link_graph_data(referto["pages"], "https://mai-scansionata.test/")
    assert grafo["has_home"] is False
    assert grafo["orphans"] is None
    html = render_html(referto)
    assert "non si raggiunge dalla home" in html


def test_il_tetto_ai_nodi_taglia_i_meno_linkati(contesto):
    """Sessanta nodi sono gia\' oltre quanti se ne seguano a occhio. Chi
    esce non deve lasciare archi appesi: un arco verso un nodo che non
    c\'e\' e\' un capo nel vuoto."""
    collegamenti = {"https://esempio.test/":
                    ["https://esempio.test/p%02d/" % i for i in range(70)]}
    for i in range(70):
        collegamenti["https://esempio.test/p%02d/" % i] = []
    referto = build_report({}, _contesto_collegato(contesto, collegamenti))
    grafo = link_graph_data(referto["pages"], referto["url"])
    assert (grafo["total"], grafo["shown"]) == (71, 60)
    for arco in grafo["links"]:
        assert arco["source"] < 60 and arco["target"] < 60
    assert "I 60 più linkati di 71." in render_html(referto)


def test_la_distanza_nel_grafo_non_e_la_profondita_di_crawl(contesto):
    """Due misure diverse che convivono: `depth` dice come il crawler
    ci è arrivato ed è ignota per le pagine da sitemap, `clicks` è il
    cammino più breve dentro il campione. Su un sito con sitemap la
    prima è ignota ovunque e la seconda si misura — confonderle
    farebbe sembrare risolto un problema che resta."""
    referto = build_report({}, _contesto_collegato(contesto))
    assert all(p["depth"] is None for p in referto["pages"]), \
        "il contesto dichiara discovery: sitemap"
    grafo = link_graph_data(referto["pages"], referto["url"])
    assert any(n["clicks"] is not None for n in grafo["nodes"])


def test_gli_archi_verso_pagine_mai_guardate_non_si_disegnano(contesto):
    """Inventarne il capo dall'altra parte direbbe che quella pagina è
    stata guardata. Quanti link restino fuori lo dice `links_internal`."""
    contesto = _contesto_collegato(contesto, {
        "https://esempio.test/": ["https://esempio.test/a/",
                                  "https://esempio.test/mai-scaricata/"],
        "https://esempio.test/a/": []})
    referto = build_report({}, contesto)
    home = referto["pages"][0]
    assert home["links_to"] == ["https://esempio.test/a/"]
    assert home["links_internal"] == 2
    grafo = link_graph_data(referto["pages"], referto["url"])
    assert grafo["edges"] == 1
    assert grafo["closed"] is False


def test_un_campione_parziale_lo_dichiara(contesto):
    """Dentro dieci pagine «orfana» può voler dire solo che chi la
    linka non è stato scaricato: dirlo dopo, a lavoro fatto, costa."""
    contesto = _contesto_collegato(contesto, {
        "https://esempio.test/": ["https://esempio.test/a/",
                                  "https://esempio.test/fuori/"],
        "https://esempio.test/a/": []})
    html = render_html(build_report({}, contesto))
    assert "Il campione è parziale" in html


def test_il_grafo_e_completo_senza_javascript(contesto):
    """Progressive enhancement: lo script non crea nodi, né archi, né
    etichette. Senza JavaScript resta lo stesso disegno, senza comandi."""
    html = render_html(build_report({}, _contesto_collegato(contesto)))
    statico = html[html.index("<svg id='grafo'"):html.index("</svg>",
                                                            html.index(
                                                                "<svg id='grafo'"))]
    assert statico.count("<circle") == 4
    assert statico.count("<line") >= 3
    assert statico.count("<text") == 4
    assert statico.count("<title>") == 4


def test_i_comandi_nascono_spenti_e_li_accende_lo_script(contesto):
    """Un bottone che non fa nulla è peggio di un bottone assente,
    perché promette qualcosa."""
    html = render_html(build_report({}, _contesto_collegato(contesto)))
    comandi = html[html.index("<p class='grafo-comandi'"):]
    comandi = comandi[:comandi.index("</p>")]
    assert "hidden" in comandi
    assert 'removeAttribute("hidden")' in html


def test_i_nodi_non_sono_focalizzabili_nell_html_statico(contesto):
    """Stessa regola della treemap, applicata al contrario: qui il
    fuoco ha qualcosa da mostrare, ma solo se lo script gira, quindi è
    lo script a creare le fermate di tabulazione."""
    html = render_html(build_report({}, _contesto_collegato(contesto)))
    svg = html[html.index("<svg id='grafo'"):html.index("</svg>",
                                                        html.index(
                                                            "<svg id='grafo'"))]
    assert "tabindex" not in svg
    assert 'setAttribute("tabindex", "0")' in html


def test_lo_script_non_ha_origini_esterne(contesto):
    """D1: inline sì, da fuori no. Il referto deve restare un file solo,
    e nulla qui dentro deve poter fare una richiesta di rete."""
    html = render_html(build_report({}, _contesto_collegato(contesto)))
    script = html[html.index("<script>") + 8:html.index("</script>")]
    assert script.strip(), "il grafo c'è, lo script deve esserci"
    for vietato in ("src=", "http://", "https://", "//cdn", "fetch(",
                    "XMLHttpRequest", "import(", "eval(", "new Function"):
        assert vietato not in script, vietato


def test_nel_codice_non_finisce_un_solo_dato_del_sito(contesto):
    """Lo script legge tutto dagli attributi `data-*` del DOM.
    Interpolare il referto in una stringa JavaScript sarebbe un secondo
    percorso di escaping accanto a `_e()`, ed è così che nasce una XSS
    in un file che contiene testo preso dal sito analizzato."""
    contesto = _contesto_collegato(contesto, {
        "https://esempio.test/": ["https://esempio.test/</script>ostile/"],
        "https://esempio.test/</script>ostile/": ["https://esempio.test/"]})
    html = render_html(build_report({}, contesto))
    script = html[html.index("<script>") + 8:html.index("</script>")]
    assert "ostile" not in script
    assert "esempio.test" not in script


def test_lo_script_non_c_e_dove_non_ha_nulla_da_fare(referto):
    """Un referto di una pagina sola non ha architettura da mostrare:
    non deve portarsi dietro codice inerte."""
    assert "<script" not in render_html(referto)


# ----------------------------------------------------------------------
# R48: archi, etichette e vicini escono dal JavaScript
# ----------------------------------------------------------------------

def _grafo_del_golden() -> str:
    """L'SVG del grafo, dal golden completo: la fixture non ne ha uno."""
    import json
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "golden", "referto.json")
    with open(percorso, encoding="utf-8") as fh:
        html = render_html(json.load(fh))
    inizio = html.index("<svg id='grafo'")
    return html[inizio:html.index("</svg>", inizio)]


def test_gli_archi_portano_anche_la_geometria_ad_anelli():
    """R48: `ridisegna()` ricalcolava in JavaScript le due estremita' di
    ogni arco — radice quadrata compresa — a ogni cambio di vista.

    Le viste sono **due e conosciute**: il layout a forze, che sta gia'
    negli attributi `x1..y2`, e quello ad anelli, che Python calcola dal
    2026-08-26. Pubblicare anche la seconda geometria toglie al
    JavaScript l'ultimo pezzo di aritmetica e lo riduce ad
    applicazione di attributi."""
    svg = _grafo_del_golden()
    archi = re.findall(r"<line class='grafo-arco'[^>]*>", svg)
    assert archi, "il golden ha un grafo con archi"
    for arco in archi:
        coordinate = re.search(r"data-a='([^']*)'", arco)
        assert coordinate, arco
        # Quattro numeri in un attributo solo, separati da spazi come
        # un `viewBox`: quattro attributi distinti costavano 7,9 KB in
        # piu' su un grafo al massimo della sua dimensione, misurati.
        assert len(coordinate.group(1).split(" ")) == 4, arco
    # E la geometria e' quella che Python calcola per la vista ad
    # anelli, non un numero qualunque: si rifa' il conto sul primo arco.
    nodi = re.findall(r"<circle class='grafo-nodo[^>]*>", svg)
    per_indice = {int(re.search(r"data-i='(\d+)'", n).group(1)): n
                  for n in nodi}

    def anello(indice):
        nodo = per_indice[indice]
        return (float(re.search(r"data-ax='([^']*)'", nodo).group(1)),
                float(re.search(r"data-ay='([^']*)'", nodo).group(1)))

    primo = archi[0]
    s = int(re.search(r"data-s='(\d+)'", primo).group(1))
    d = int(re.search(r"data-t='(\d+)'", primo).group(1))
    raggio = float(re.search(r"data-r='([^']*)'",
                             per_indice[d]).group(1))
    atteso = mars_report.geometria_arco(anello(s), anello(d), raggio)
    letto = [float(x) for x in
             re.search(r"data-a='([^']*)'", primo).group(1).split(" ")]
    assert letto == [round(v, 1) for v in atteso]


def test_le_etichette_portano_la_posizione_ad_anelli():
    """Stessa ragione degli archi: la posizione dell'etichetta e' il
    centro del nodo piu' il raggio, ed e' aritmetica."""
    svg = _grafo_del_golden()
    etichette = re.findall(r"<text class='grafo-etichetta'[^>]*>", svg)
    assert etichette, "il golden ha etichette"
    nodi = {int(re.search(r"data-i='(\d+)'", n).group(1)): n
            for n in re.findall(r"<circle class='grafo-nodo[^>]*>", svg)}
    for etichetta in etichette:
        i = int(re.search(r"data-i='(\d+)'", etichetta).group(1))
        nodo = nodi[i]
        raggio = float(re.search(r"data-r='([^']*)'", nodo).group(1))
        # L'etichetta sta a DESTRA del cerchio e non sul suo centro:
        # e' lo scostamento che il JavaScript ricalcolava a ogni
        # ridisegno, raggio compreso.
        for asse, scarto in (("x", raggio + 3), ("y", 4)):
            atteso = float(re.search(
                r"data-a%s='([^']*)'" % asse, nodo).group(1)) + scarto
            letto = float(re.search(
                r"data-a%s='([^']*)'" % asse, etichetta).group(1))
            assert letto == pytest.approx(atteso, abs=0.05), (i, asse)


def test_ogni_nodo_dichiara_i_propri_vicini_e_i_propri_archi():
    """`evidenzia()` scandiva tutti gli archi per trovare i vicini di un
    nodo, a ogni passaggio del puntatore. La risposta non dipende dal
    gesto: e' una proprieta' del grafo, e Python la conosce."""
    svg = _grafo_del_golden()
    nodi = re.findall(r"<circle class='grafo-nodo[^>]*>", svg)
    assert nodi
    for nodo in nodi:
        assert "data-v='" in nodo, nodo
        assert "data-e='" in nodo, nodo
    # Il nodo di partenza ha almeno un vicino: un grafo di archi in cui
    # nessuno confina con nessuno sarebbe un elenco, non un grafo.
    assert any("data-v='" in n and n.split("data-v='")[1][0] != "'"
               for n in nodi)


def test_i_vicini_dichiarati_sono_quelli_degli_archi():
    """L'invariante che lega i due dati: se `data-v` e `data-s`/`data-t`
    divergessero, l'evidenziazione accenderebbe archi che non toccano il
    nodo, e nessun test lo vedrebbe — e' un fatto di resa, non di
    punteggio."""
    svg = _grafo_del_golden()
    archi = [(int(s), int(t)) for s, t in re.findall(
        r"<line class='grafo-arco' data-s='(\d+)' data-t='(\d+)'", svg)]
    atteso_v, atteso_e = {}, {}
    for k, (s, t) in enumerate(archi):
        for uno, altro in ((s, t), (t, s)):
            atteso_v.setdefault(uno, {uno}).add(altro)
            atteso_e.setdefault(uno, set()).add(k)
    for nodo in re.findall(r"<circle class='grafo-nodo[^>]*>", svg):
        i = int(re.search(r"data-i='(\d+)'", nodo).group(1))
        vicini = re.search(r"data-v='([^']*)'", nodo).group(1)
        incidenti = re.search(r"data-e='([^']*)'", nodo).group(1)
        elencati = [int(x) for x in vicini.split(",") if x]
        assert len(elencati) == len(set(elencati)), \
            "un vicino elencato due volte accende due volte lo stesso nodo"
        assert set(elencati) == atteso_v.get(i, {i}), i
        assert {int(x) for x in incidenti.split(",") if x} == \
            atteso_e.get(i, set()), i


def test_due_pagine_che_si_linkano_a_vicenda_restano_un_vicino_solo():
    """Il caso che il golden non ha: due archi fra la stessa coppia.

    Due pagine che si linkano a vicenda producono `A->B` e `B->A`, e
    senza il controllo B comparirebbe **due volte** fra i vicini di A.
    Non e' un difetto di resa: `evidenzia()` accenderebbe due volte lo
    stesso nodo, che oggi non si vede — le classi sono idempotenti — ma
    e' un elenco che afferma una cosa falsa, e il giorno che qualcuno
    ne contasse la lunghezza direbbe che A ha due vicini."""
    archi = [{"source": 0, "target": 1}, {"source": 1, "target": 0},
             {"source": 0, "target": 2}]
    vicini, incidenti = mars_report.vicinato(archi, 3)
    assert vicini == [[0, 1, 2], [0, 1], [0, 2]]
    # Gli archi invece sono due davvero, e vanno accesi entrambi.
    assert incidenti == [[0, 1, 2], [0, 1], [2]]


def test_il_javascript_del_grafo_non_calcola_piu_una_geometria():
    """Il presidio della decisione, non della resa.

    R48 e' nata perche' `REFERTO_JS` conteneva aritmetica che nessun
    test eseguiva. Lo zoom resta — dipende da quante volte si e'
    cliccato, quindi non si puo' precalcolare — ma la geometria del
    grafo no: se `Math.sqrt` torna qui dentro, e' tornata anche
    l'aritmetica non verificata."""
    assert "Math.sqrt" not in mars_report.REFERTO_JS


# ----------------------------------------------------------------------
# I3: il k della fusione, esposto e mostrato
# ----------------------------------------------------------------------

def test_il_referto_dichiara_il_k_del_contesto(contesto):
    """`rrf.k` era la costante: con `--rrf-k` diventa una scelta, e un
    referto che dichiarasse 60 mentre l'audit ne ha usato un altro
    sarebbe irriproducibile proprio nel campo nato per renderlo tale."""
    referto = build_report({}, dict(contesto, rrf_k=17))
    assert referto["rrf"]["k"] == 17
    assert build_report({}, dict(contesto))["rrf"]["k"] == RRF_K


def _ranghi_per_k():
    """Due aree con classifiche per query che rendono k osservabile."""
    lex = {"rank": [], "per_query": [{"query": "a", "rank": [7, 0, 5],
                                      "matched": True},
                                     {"query": "b", "rank": [1, 2, 5],
                                      "matched": True}]}
    sem = {"rank": [], "per_query": [{"query": "a", "rank": [5, 7, 0],
                                      "matched": True},
                                     {"query": "b", "rank": [5, 1, 2],
                                      "matched": True}]}
    return {"mars_lexical": lex, "mars_semantic": sem}


def test_la_sensibilita_a_k_e_una_misura_non_una_dichiarazione():
    """I3: «mostrare come cambia il consenso al variare di k».

    Il consenso di ogni singola query NON dipende da k — e' l'incrocio
    dei primi tre di due liste, e la fusione non c'entra — quindi il
    sondaggio si fa sul consenso AGGREGATO, che dai ranghi fusi viene e
    che con k cambia davvero. Misurato su un sito reale da 128 chunk:
    3/3 a k=10, 0/3 a k=60."""
    chunks = [{"url": "https://x/", "heading": str(i), "text": "t"}
              for i in range(8)]
    voci = rrf_sensitivity(_ranghi_per_k(), chunks, 60)
    assert [v["k"] for v in voci] == sorted(SCALA_K)
    for v in voci:
        atteso = _consenso(
            [i for i, _ in reciprocal_rank_fusion(
                [p["rank"] for p in _ranghi_per_k()["mars_lexical"]
                 ["per_query"]], v["k"])],
            [i for i, _ in reciprocal_rank_fusion(
                [p["rank"] for p in _ranghi_per_k()["mars_semantic"]
                 ["per_query"]], v["k"])],
            chunks, "x", v["k"])
        assert v["consensus_top3"] == atteso["consensus_top3"], "k=%d" % v["k"]


def test_la_sensibilita_include_il_k_in_uso(contesto):
    """Un sondaggio che non contenesse il valore con cui l'audit e'
    girato lascerebbe il lettore a interpolare."""
    voci = rrf_sensitivity(_ranghi_per_k(), [], 17)
    assert 17 in [v["k"] for v in voci]
    assert [v["k"] for v in voci] == sorted([v["k"] for v in voci])


def _risultati_con_ranghi() -> dict:
    """Due aree con classifiche vere, per far esistere il sondaggio."""
    return {"mars_lexical": dict(_ranghi_per_k()["mars_lexical"],
                                 status="ranking", score=100, issues=[],
                                 findings=[], rank=[7, 0, 5]),
            "mars_semantic": dict(_ranghi_per_k()["mars_semantic"],
                                  status="ranking", score=100, issues=[],
                                  findings=[], rank=[5, 7, 0])}


def test_senza_ranghi_la_sensibilita_non_si_inventa():
    """Nessuna delle due aree ha classifiche: non c'e' nulla da
    sondare, e una lista vuota e' diversa da un sondaggio piatto."""
    assert rrf_sensitivity({}, [], 60) == []


def test_le_tre_viste_mostrano_la_sensibilita_a_k(contesto):
    """I3 chiedeva di MOSTRARE come cambia il consenso, non solo di
    poterlo cambiare: se il sondaggio resta nel JSON, l'intuizione la
    vede solo chi legge il dato con un programma."""
    referto = build_report(_risultati_con_ranghi(), dict(contesto))
    assert referto["rrf_sensitivity"], "il dato c'e'"
    for formato in ("text", "markdown", "html"):
        reso = RENDERERS[formato](referto)
        assert "k=0" in reso and "k=300" in reso, formato
        assert "60" in reso, formato


def test_la_riga_della_sensibilita_dice_quale_k_e_in_uso(contesto):
    """Senza, il lettore vede quattro numeri e nessuno che sia il suo."""
    referto = build_report(_risultati_con_ranghi(), dict(contesto, rrf_k=10))
    testo = RENDERERS["text"](referto)
    riga = [r for r in testo.split("\n") if "k=0" in r][0]
    assert "k=10" in riga
    assert riga.index("in uso") > riga.index("k=10")


def test_le_viste_dichiarano_il_k_cambiato_fra_due_esecuzioni(referto):
    """Un consenso aggregato che scende da 3/3 a 0/3 perche' e' cambiato
    il k non e' un fatto del sito, ed e' esattamente ciò che la sezione
    «rispetto a prima» sembrerebbe dire."""
    con_delta = dict(referto)
    con_delta["delta"] = {"previous_run": "2025-12-01T09:00:00+0000",
                          "previous_version": "0.0.0", "scores": [],
                          "overall": None, "resolved": [], "new": [],
                          "by_title_fallback": False, "key_migrations": [],
                          "rrf_k_changed": {"before": 10, "after": 60}}
    for formato in ("text", "markdown", "html"):
        reso = RENDERERS[formato](con_delta)
        assert "10" in reso and "60" in reso, formato
        assert "k" in reso, formato
        riga = [r for r in reso.split("\n") if "10" in r and "60" in r]
        assert riga, "%s: i due k non compaiono insieme" % formato


def test_le_viste_dichiarano_un_form_factor_cambiato(referto):
    """I16, il gemello del k: 83 desktop contro 58 mobile misurati a
    sito invariato — senza la nota la sezione «rispetto a prima»
    direbbe «migliorato» di una cosa che non e' successa."""
    con_delta = dict(referto)
    con_delta["delta"] = {"previous_run": "2025-12-01T09:00:00+0000",
                          "previous_version": "0.0.0", "scores": [],
                          "overall": None, "resolved": [], "new": [],
                          "by_title_fallback": False, "key_migrations": [],
                          "rrf_k_changed": None,
                          "form_factor_changed": {"before": "mobile",
                                                  "after": "desktop"}}
    for formato in ("text", "markdown", "html"):
        reso = RENDERERS[formato](con_delta)
        riga = [r for r in reso.split("\n")
                if "mobile" in r and "desktop" in r]
        assert riga, "%s: i due dispositivi non compaiono insieme" % formato


def test_le_viste_dichiarano_una_misura_cambiata(referto):
    """R63: quando cambia CHE COSA si misura, i numeri si muovono a sito
    invariato — sul sito che ha aperto la voce, complessivo da 59.2 a
    67.1 con lo stesso HTML. La sezione «rispetto a prima» lo direbbe
    «migliorato», e non sarebbe vero.

    Il numero di versione NON compare nella resa: è volatile, e sta in
    `since` nel JSON per chi deve sapere da quando."""
    con_delta = dict(referto)
    con_delta["delta"] = {"previous_run": "2025-12-01T09:00:00+0000",
                          "previous_version": "0.0.0", "scores": [],
                          "overall": None, "resolved": [], "new": [],
                          "by_title_fallback": False, "key_migrations": [],
                          "rrf_k_changed": None,
                          "measure_changes": [
                              {"since": "9.9.9-SENTINELLA",
                               "reason": "il menu resta fuori dal corpus"}]}
    for formato in ("text", "markdown", "html"):
        reso = RENDERERS[formato](con_delta)
        assert "cambiato che cosa si misura" in reso, formato
        # Il MOTIVO solo dove c'e' spazio, come per le migrazioni di
        # chiave: la vista testo sta in 55 colonne e si ferma al fatto.
        if formato != "text":
            assert "il menu resta fuori dal corpus" in reso, formato
        # Una sentinella al posto della versione: cercare «2.10.0»
        # avrebbe trovato la versione che il referto dichiara in testa,
        # che e' un'altra cosa e ci deve stare.
        assert "SENTINELLA" not in reso, \
            "%s: la versione e' volatile e non va nella resa" % formato


# ======================================================================
# U11 — il deliverable: stampa, tabelle, piede
# ======================================================================
#
# Misurato con axe-core su Chromium, sul referto sintetico completo,
# prima e dopo la voce:
#
#   regole WCAG 2.1 A/AA   0 violazioni prima, 0 dopo; superate 25 -> 26
#   regole COMPLETE        1 violazione prima (`empty-table-header`,
#                          minor), 0 dopo; superate 39 -> 43
#
# Le quattro regole nuove sono `aria-hidden-focus`, `scope-attr-valid` e
# le due dei punti di riferimento `contentinfo`. Il `<th>` vuoto della
# tabella della superficie era quindi un difetto VERO, non una
# scortesia: axe lo classifica best-practice, e il referto che misura
# l'accessibilita' altrui lo portava addosso.


def _zuppa(html_testo):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html_testo, "lxml")


def test_il_referto_porta_le_regole_di_stampa(referto):
    """Un referto di consulenza finisce in PDF, e prima di U11 non
    c'era ALCUNA regola di stampa: quadranti senza colore, schede
    spezzate a meta' pagina."""
    uscita = render_html(referto)
    assert "@media print" in uscita
    assert "@page" in uscita
    # Senza, i browser scartano i fondi in stampa e i quadranti — che
    # il colore ce l'hanno nel riempimento SVG — escono vuoti.
    assert "print-color-adjust:exact" in uscita
    assert "break-inside:avoid" in uscita
    # Le ancore su carta sono cancelletti muti.
    assert ".ancora, .grafo-comandi, script { display:none; }" in uscita


def test_ogni_tabella_del_referto_ha_una_intestazione(monkeypatch):
    """`thead` e `th scope='col'` su TUTTE, e nessun `th` vuoto.

    Sui DUE referti sintetici e non sulla fixture di questo file: quella
    accende tre tabelle su sei, e una nuova scritta senza intestazione
    resterebbe fuori dal presidio finche' un sito reale non la accende.
    """
    from test_golden import DATASET
    tabelle = []
    for costruisci in DATASET.values():
        tabelle += _zuppa(render_html(costruisci(monkeypatch))).find_all(
            "table")
    assert len(tabelle) >= 6, "i referti sintetici accendono le tabelle"
    for tabella in tabelle:
        testa = tabella.find("thead")
        assert testa is not None, tabella.decode()[:120]
        intestazioni = testa.find_all("th")
        assert intestazioni, tabella.decode()[:120]
        for cella in intestazioni:
            assert cella.get("scope") == "col", cella.decode()
            # `empty-table-header`: era la sola violazione che axe
            # trovava sul referto, ed era la colonna della barra.
            assert cella.get_text(strip=True), tabella.decode()[:120]


def test_le_barre_sono_nascoste_a_chi_ascolta(referto):
    """La barra e' il numero della colonna accanto ridisegnato: un
    lettore di schermo che la annunciasse leggerebbe due volte lo
    stesso dato."""
    zuppa = _zuppa(render_html(referto))
    barre = zuppa.select("span.bar")
    assert barre, "il referto sintetico disegna barre"
    for barra in barre:
        assert barra.get("aria-hidden") == "true", barra.decode()


def test_il_piede_dice_chi_ha_misurato_e_come(referto):
    """La firma e la formula, dal REFERTO e non dalle costanti.

    `--rrf-k` cambia la k, e un piede che dichiarasse sempre 60
    mentirebbe proprio dove promette di dire come si e' misurato."""
    referto["rrf"] = dict(referto["rrf"], k=17)
    uscita = render_html(referto)
    piede = _zuppa(uscita).find("footer")
    assert piede is not None
    testo = piede.get_text(" ", strip=True)
    assert "MARS Beacon" in testo
    assert "k=17" in testo, testo
    assert referto["version"] in testo
    # FUORI da `<main>`: dentro sarebbe il piede di quella sezione e non
    # del documento, e non varrebbe come punto di riferimento
    # `contentinfo`. Misurato: axe accende due regole in piu'.
    assert uscita.index("</main>") < uscita.index("<footer")


def test_il_piede_non_introduce_origini_esterne(referto):
    """Gli URL delle fonti sono TESTO, non `<a href>`.

    Un link non scarica nulla, ma la guardia dell'autoconsistenza e'
    volutamente larga e allargarla per un piede sarebbe scambiare una
    promessa per una comodita'. L'indirizzo si copia lo stesso."""
    uscita = render_html(referto)
    assert riferimenti_esterni(uscita) == []
    assert "https://schema.org/" in uscita, "l'indirizzo c'e', come testo"


def test_le_fonti_del_piede_sono_quelle_del_README():
    """Due elenchi della stessa cosa divergono, e qui in silenzio.

    E' la deriva fra documentazione e codice che R32 ha gia' chiuso una
    volta: il README elenca le fonti del metodo, il piede ne mostra un
    sottoinsieme, e nessuno se ne accorgerebbe se una delle due
    cambiasse."""
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(radice, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    for testo, url in mars_report.RIFERIMENTI:
        if url:
            assert url in readme, url
    # Gli autori, non le frasi intere: il README le formatta su piu'
    # righe e il piede su una.
    for autore in ("Cormack", "Robertson", "Zaragoza"):
        assert autore in readme
        assert any(autore in testo for testo, _ in mars_report.RIFERIMENTI)


# ----------------------------------------------------------------------
# I4 + I9: QUALI passaggi stanno fuori dall'intersezione
# ----------------------------------------------------------------------

def _referto_divergente(rank_lex=(0, 1, 2), rank_sem=(2, 3, 4),
                        quanti_chunk=6):
    """Due classifiche che concordano su un solo passaggio."""
    chunks = [{"url": "https://x/p%d" % i, "heading": "H%d" % i,
               "text": "t"} for i in range(quanti_chunk)]
    voce_lex = {"query": "q", "rank": list(rank_lex), "matched": True}
    voce_sem = {"query": "q", "rank": list(rank_sem), "matched": True}
    return build_report(
        {"mars_lexical": {"rank": list(rank_lex), "per_query": [voce_lex],
                          "queries": ["q"]},
         "mars_semantic": {"rank": list(rank_sem), "per_query": [voce_sem]}},
        {"url": "https://x/", "market": "global", "pages": {"a": {}},
         "queries": ["q"], "discovery": "sitemap", "skipped": [],
         "chunks": chunks})


def test_il_consenso_dice_quali_passaggi_divergono():
    """I4 + I9: `consensus_top3` dice QUANTI, non QUALI.

    Un passaggio nei primi tre del solo lessicale e' trovato dalle
    PAROLE e non dal significato; uno del solo semantico e' il
    contrario. Sono due difetti editoriali diversi e opposti, e il
    conteggio 1/3 non permette di distinguerli.
    """
    aggregato = _referto_divergente()["rrf_aggregate"]
    assert aggregato["consensus_top3"] == 1, "l'intersezione e' {2}"
    assert [v["url"] for v in aggregato["only_lexical"]] == \
        ["https://x/p0", "https://x/p1"]
    assert [v["url"] for v in aggregato["only_semantic"]] == \
        ["https://x/p3", "https://x/p4"]


def test_i_passaggi_divergenti_portano_l_etichetta_leggibile():
    """Un indice numerico non dice nulla a chi legge: e' la stessa
    ragione per cui esiste `describe_chunk`."""
    aggregato = _referto_divergente()["rrf_aggregate"]
    assert aggregato["only_lexical"][0]["label"] == "https://x/p0 § H0"


def test_i_divergenti_sono_nell_ordine_del_loro_recuperatore():
    """Non nell'ordine dell'indice del chunk.

    Un `set` di interi si itera per valore, quindi ordinarlo per
    indice sembrerebbe deterministico e sarebbe privo di significato:
    chi legge vuole sapere qual e' il PRIMO dei passaggi che solo quel
    recuperatore ha trovato.
    """
    aggregato = _referto_divergente(rank_lex=(5, 4, 2),
                                    rank_sem=(2, 1, 0))["rrf_aggregate"]
    assert [v["url"] for v in aggregato["only_lexical"]] == \
        ["https://x/p5", "https://x/p4"]
    assert [v["url"] for v in aggregato["only_semantic"]] == \
        ["https://x/p1", "https://x/p0"]


def test_ogni_query_porta_i_propri_divergenti():
    """Non solo l'aggregato: il JSON e' il dato canonico, e chi lo
    consuma deve poter guardare la singola domanda."""
    voce = _referto_divergente()["rrf_simulation"][0]
    assert [v["url"] for v in voce["only_lexical"]] == \
        ["https://x/p0", "https://x/p1"]


def test_una_query_senza_riscontro_non_ha_divergenti():
    """`None` per il conteggio, liste VUOTE per i quali: non c'e'
    nulla su cui divergere, e inventare due elenchi direbbe il falso."""
    voce = _referto_rrf(matched_lex=False)["rrf_simulation"][0]
    assert voce["only_lexical"] == []
    assert voce["only_semantic"] == []


def test_un_indice_fuori_dai_chunk_non_fa_cadere_il_referto():
    """I ranghi arrivano dai moduli, che sono plugin: un indice oltre
    il corpus e' dato ostile, e `_consenso` gia' se ne guarda per il
    passaggio in testa."""
    aggregato = _referto_divergente(rank_lex=(0, 99), rank_sem=(1, 2),
                                    quanti_chunk=3)["rrf_aggregate"]
    assert [v["url"] for v in aggregato["only_lexical"]] == ["https://x/p0"]


def test_consenso_pieno_non_ha_divergenti():
    aggregato = _referto_divergente(rank_lex=(0, 1, 2),
                                    rank_sem=(0, 1, 2))["rrf_aggregate"]
    assert aggregato["consensus_top3"] == 3
    assert aggregato["only_lexical"] == []
    assert aggregato["only_semantic"] == []


@pytest.mark.parametrize("vista", [render_text, render_html, render_markdown],
                         ids=["testo", "html", "markdown"])
def test_le_viste_dicono_quali_passaggi_divergono(vista):
    """Il dato nel JSON e basta non serve a chi riceve il referto: il
    numero 1/3 lo vede gia', ed e' il QUALE che gli manca."""
    testo = vista(_referto_divergente())
    assert "https://x/p0" in testo, "il divergente lessicale"
    assert "https://x/p3" in testo, "il divergente semantico"


@pytest.mark.parametrize("vista", [render_text, render_html, render_markdown],
                         ids=["testo", "html", "markdown"])
def test_le_viste_dicono_la_direzione_della_divergenza(vista):
    """Elencare sei URL senza dire da che parte stanno sarebbe peggio
    del conteggio: la direzione E' la diagnosi."""
    testo = vista(_referto_divergente())
    assert "solo dalle parole" in testo
    assert "solo dal significato" in testo


@pytest.mark.parametrize("vista", [render_text, render_html, render_markdown],
                         ids=["testo", "html", "markdown"])
def test_le_viste_tacciono_quando_non_c_e_divergenza(vista):
    testo = vista(_referto_divergente(rank_lex=(0, 1, 2), rank_sem=(0, 1, 2)))
    assert "solo dalle parole" not in testo


def test_nel_testo_i_divergenti_stanno_dopo_l_elenco_per_query():
    """L'elenco per query non ha un'intestazione propria: un blocco
    rientrato messo sopra se lo prendeva, e le query sembravano una
    terza direzione della divergenza."""
    testo = render_text(_referto_divergente())
    assert testo.index("Fuori dall'intersezione:") > testo.index("  q  ")
