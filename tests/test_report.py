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

from mars_core import SEV_CRITICAL, SEV_INFO, Finding, load_queries
import mars_remediation
from mars_report import (RENDERERS, _classe, _correzioni,
                         _correzioni_testo, _elenco_controlli,
                         _etichetta_area, _quadrante, build_report,
                         render_html, render_json, render_text)


@pytest.fixture
def referto(contesto):
    contesto["results"] = {
        "mars_tech": {"score": 85, "issues": ["[lieve] robots.txt muto"]},
        "mars_seo": {"score": None, "status": "unavailable",
                     "issues": ["Lighthouse assente"]},
        # status e tool come li dichiarano i moduli veri (R38): senza,
        # la fixture proverebbe una resa che in produzione non esiste.
        "mars_lexical": {"status": "ranking", "tool": "BM25 (k1=1.5, b=0.75)",
                         "rank": [0, 1], "top_chunk": "https://x/ § H",
                         "queries": ["alfa", "beta"],
                         "per_query": [{"query": "alfa", "rank": [0, 1]},
                                       {"query": "beta", "rank": [1, 0]}]},
        "mars_semantic": {"status": "ranking", "tool": "proxy char-TFIDF",
                          "rank": [0, 1], "answer_shaped_ratio": 0.5,
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
                   "llm_judgement", "skipped", "remediation"):
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
    uno zero — o un quadrante qualunque — sarebbe inventare una misura.

    L'intento e' lo stesso di prima; il meccanismo no. Il verdetto
    veniva sovrascritto con "classifica" cablando il NOME del modulo
    nella vista, ed e' da li' che nasceva il difetto R38: la vista
    decideva sul nome invece che sul dato, e su un'area andata in
    errore stampava comunque l'etichetta normale. Ora la parola arriva
    dallo stato dichiarato dal modulo."""
    uscita = render_html(referto)

    # Lo strumento c'e': un rango senza il nome di chi l'ha calcolato
    # non e' verificabile, e prima il referto non lo diceva affatto.
    assert "BM25 (k1=1.5, b=0.75)" in uscita
    assert "proxy char-TFIDF" in uscita

    schede = uscita.split("<div class='area'>")[1:]
    for etichetta in ("3. Lessicale", "4. Semantica"):
        trovate = [s for s in schede if etichetta in s]
        assert len(trovate) == 1, "scheda %s: %d" % (etichetta, len(trovate))
        assert "classifica, non un voto" in trovate[0]
        # L'asserzione forte: nessun voto inventato.
        assert "/100" not in trovate[0], \
            "%s non deve esibire un punteggio" % etichetta


@pytest.mark.parametrize("modulo, etichetta", [
    ("mars_lexical", "3. Lessicale"),
    ("mars_semantic", "4. Semantica"),
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


# ----------------------------------------------------------------------
# U3.3: la resa dei testi di correzione
# ----------------------------------------------------------------------

def _rilievo(**kw) -> dict:
    base = {"area": "mars_tech", "severity": SEV_CRITICAL, "title": "Titolo",
            "key": "tech.x.y", "detail": "", "fix": "", "example": "",
            "url": "", "weight": 1.0, "source_severity": "", "params": {}}
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
        "mars_schema": {"score": 90, "issues": [],
                        "findings": [_rilievo(area="mars_schema",
                                              key="sd.a.b",
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


def test_testo_lascia_fuori_l_esempio():
    """Cinque o sette righe di nginx per area triplicherebbero il
    referto: gli example vivono nell'HTML e nel JSON, per intero."""
    righe = _correzioni_testo([_rilievo(fix="Fai X.",
                                        example="riga1\nriga2\nriga3")])
    assert not any("riga1" in r for r in righe)


def test_testo_mostra_le_correzioni_nel_referto_intero(contesto):
    contesto["results"] = {
        "mars_tech": {"score": 60, "issues": ["[critico] robots muto"],
                      "findings": [_rilievo(title="robots muto",
                                            fix="Pubblica un robots.txt.")]}}
    testo = render_text(build_report(contesto["results"], contesto))
    assert "  → robots muto" in testo
    assert "    Pubblica un robots.txt." in testo


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
