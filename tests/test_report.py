#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — referto: dato canonico e sue viste.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import re

import pytest

from mars_core import (SEV_CRITICAL, SEV_INFO, SEV_WARNING, Finding,
                       load_queries)
import mars_remediation
import mars_report
from mars_report import (RENDERERS, SOGLIA_BUONO, SOGLIA_MEDIO, _classe,
                         _ancora, _correzioni, ancore_dei_rilievi,
                         conteggi_per_gravita, segnali_derivati,
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


def test_le_tre_caselle_coprono_tutte_le_gravita_prodotte(referto):
    """Presidio: se un giorno un modulo emettesse `ok`, la casella non
    ci sarebbe e il rilievo sparirebbe dall'hero senza che nulla si
    rompa. Questo test lo rende rosso invece che invisibile."""
    conteggi = conteggi_per_gravita(referto)
    note = {gravita for gravita, _, _ in mars_report.TESSERE_GRAVITA}
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
    contesto["skipped"] = ["non HTML: https://x/a.pdf", "altro host"]
    contesto["results"] = {"mars_tech": {"score": 60, "issues": [],
                                         "findings": [_rilievo()]}}
    html = render_html(build_report(contesto["results"], contesto))
    assert "<span class='grande bad'>1</span>" in html
    assert "<span class='meta'>2 URL scartati</span>" in html


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
    assert html.count("viewBox='0 0 120 120'") == 3, "hero + due aree"
    assert ".hero .quadrante svg { width:8.5rem" in html


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
