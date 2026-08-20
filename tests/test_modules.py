#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — i moduli d'area, su fixture offline.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import subprocess

import pytest

import mars_citability
import mars_lexical
import mars_llm_judge
import mars_schema
import mars_semantic
import mars_seo
import mars_tech
import mars_wapt
import mars_wcag
from conftest import pagina


# ----------------------------------------------------------------------
# Contratto comune a tutte le aree
# ----------------------------------------------------------------------

MODULI = [mars_tech, mars_lexical, mars_semantic, mars_schema,
          mars_wcag, mars_citability, mars_llm_judge]


@pytest.mark.parametrize("modulo", MODULI, ids=lambda m: m.__name__)
def test_ogni_modulo_rispetta_il_contratto(modulo, contesto):
    esito = modulo.audit(contesto)
    assert isinstance(esito, dict)
    if "score" in esito and esito["score"] is not None:
        assert 0 <= esito["score"] <= 100
    assert isinstance(esito.get("issues", []), list)


@pytest.mark.parametrize("modulo", [mars_schema, mars_wcag],
                         ids=lambda m: m.__name__)
def test_pagine_vuote_danno_non_misurato(modulo):
    """Regressione R6: mars_wcag andava in IndexError."""
    esito = modulo.audit({"pages": {}, "url": "https://x/"})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"


# ----------------------------------------------------------------------
# mars_tech (C10)
# ----------------------------------------------------------------------

def _contesto_tech(robots_txt="User-agent: *\nAllow: /", **pagine_extra):
    pagine = {"https://esempio.test/": pagina(**pagine_extra)}
    return {"url": "https://esempio.test/", "pages": pagine,
            "robots": {"found": True, "text": robots_txt, "sitemaps": []},
            "sitemap": {"found": True, "from_robots": True, "urls": 3,
                        "with_lastmod": 3, "unreadable": 0}}


def test_tech_blocco_crawler_ia_e_critico():
    """Un crawler escluso non legge nulla: nessun'altra area compensa."""
    esito = mars_tech.audit(_contesto_tech(
        "User-agent: GPTBot\nDisallow: /\n\nUser-agent: ClaudeBot\n"
        "Disallow: /\n\nUser-agent: *\nAllow: /"))
    assert esito["findings_by_severity"].get("critico") == 1
    assert "GPTBot" in esito["issues"][0] and "ClaudeBot" in esito["issues"][0]
    assert esito["score"] <= 60


def test_tech_distingue_assenza_da_blocco():
    """Regressione C10: il controllo per sottostringa confondeva
    'nessuna regola' con 'bloccato', che sono opposti."""
    muto = mars_tech.audit(_contesto_tech())
    esplicito = mars_tech.audit(_contesto_tech(
        "User-agent: GPTBot\nAllow: /\n\nUser-agent: *\nAllow: /"))
    assert muto["score"] < esplicito["score"]
    assert not muto["findings_by_severity"].get("critico")


def test_tech_noindex_dal_meta_e_dall_header():
    """X-Robots-Tag agisce come il meta ma non compare nel DOM."""
    da_meta = mars_tech.audit(_contesto_tech(
        html='<html lang="it"><head><meta name="robots" '
             'content="noindex"></head><body><p>x</p></body></html>'))
    da_header = mars_tech.audit(_contesto_tech(x_robots_tag="noindex"))
    for esito in (da_meta, da_header):
        assert any("noindex" in i for i in esito["issues"])
        assert esito["findings_by_severity"].get("critico") == 1


def test_tech_canonical_verso_un_altro_host():
    esito = mars_tech.audit(_contesto_tech(
        canonical="https://altro-sito.example/"))
    assert any("altro host" in i for i in esito["issues"])


def test_tech_scala_pesata_non_lineare():
    """Regressione C10: 100 - len(issues)*15 dava lo stesso peso a un
    noindex su tutto il sito e a un lastmod mancante."""
    grave = mars_tech.audit(_contesto_tech(x_robots_tag="noindex"))
    lieve = mars_tech.audit(_contesto_tech())
    assert lieve["score"] - grave["score"] > 20


def test_tech_sitemap_assente_e_grave():
    ctx = _contesto_tech()
    ctx["sitemap"] = {"found": False}
    assert any("Nessuna sitemap" in i
               for i in mars_tech.audit(ctx)["issues"])


# ----------------------------------------------------------------------
# mars_schema (R6)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("frammento, atteso", [
    ('<script type="application/ld+json">{"@type":"Organization"}</script>',
     None),
    ('<script type="application/ld+json"></script>', "vuoto"),
    ('<script type="application/ld+json">{non json}</script>', "malformato"),
])
def test_schema_distingue_vuoto_da_malformato(frammento, atteso):
    """Regressione R6: json.loads(None) dava TypeError, catturato
    dall'except generico e riportato come "malformato" su un blocco
    che era soltanto vuoto."""
    ctx = {"pages": {"https://x/": pagina(
        html="<html><body>%s</body></html>" % frammento)}}
    esito = mars_schema.audit(ctx)
    if atteso is None:
        assert esito["issues"] == [] and esito["score"] == 100
    else:
        assert atteso in esito["issues"][0]


def test_schema_nessun_json_ld():
    esito = mars_schema.audit({"pages": {"https://x/": pagina()}})
    assert esito["score"] == 50


# ----------------------------------------------------------------------
# mars_wcag (C8)
# ----------------------------------------------------------------------

HTML_ACCESSIBILE = """<html lang="it"><body><h1>A</h1><h2>B</h2>
<label for="q">Cerca</label><input id="q">
<table><tr><th>H</th></tr></table>
<a href="/g">Guida completa alla fusione</a></body></html>"""

HTML_INACCESSIBILE = """<html><body><h1>A</h1><h4>Salto</h4>
<form><input type="text" name="senza"></form>
<table><tr><td>dati</td></tr></table>
<table role="presentation"><tr><td>layout</td></tr></table>
<a href="/x">clicca qui</a><a href="/y" aria-label="Vai">leggi tutto</a>
<div tabindex="3">x</div><div tabindex="0">ok</div>
<img src="a.png"></body></html>"""


def test_wcag_statico_riconosce_i_difetti():
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_INACCESSIBILE)}})
    testo = " ".join(esito["static_findings"])
    for criterio in ("3.1.1", "1.1.1", "1.3.1", "2.4.4", "2.4.3"):
        assert criterio in testo, "manca il criterio %s" % criterio


def test_wcag_statico_non_lamenta_il_corretto():
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_ACCESSIBILE)}})
    assert esito["static_findings"] == []


def test_wcag_esclusioni_corrette():
    """Un controllo rumoroso e' peggio di nessun controllo:
    role=presentation, aria-label e tabindex=0 non devono contare."""
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_INACCESSIBILE)}})
    testo = " ".join(esito["static_findings"])
    assert "1 tabelle" in testo, "la tabella di layout non va contata"
    assert "1 link" in testo, "il link con aria-label non va contato"
    assert "1 elementi con tabindex" in testo, "tabindex=0 non va contato"


def test_wcag_dichiara_sempre_il_livello():
    esito = mars_wcag.audit({"pages": {"https://x/": pagina()}})
    assert "WCAG 2.1" in esito["wcag_level"]


def test_wcag_axe_raggruppa_per_regola():
    """Regressione C8: la stessa violazione su cinque pagine arrivava
    cinque volte e affondava il punteggio da sola."""
    def viol(rid, gravita):
        return {"id": rid, "impact": gravita, "help": rid, "nodes": [0]}
    una = mars_wcag.score_from_violations([viol("a", "serious")], 5)
    cinque = mars_wcag.score_from_violations([viol("a", "serious")] * 5, 5)
    assert una["rules_violated"] == cinque["rules_violated"] == 1
    assert cinque["score"] < una["score"]
    assert cinque["score"] > una["score"] - 20, "il fattore deve essere 2, non 5"


# ----------------------------------------------------------------------
# mars_lexical e mars_semantic
# ----------------------------------------------------------------------

def test_lexical_sopravvive_ai_campi_none(contesto):
    """Regressione R6: un valore None arrivava dentro " ".join() e
    faceva cadere il modulo lessicale, e con esso l'intera
    simulazione RRF.

    Il None va messo nei CHUNK: da R10 e' li' che il modulo guarda.
    Metterlo nelle pagine, come faceva la prima versione di questo
    test, non esercitava piu' nulla.
    """
    for chunk in contesto["chunks"]:
        chunk["heading"] = None
        chunk["text"] = None
    esito = mars_lexical.audit(contesto)
    assert "rank" in esito


def test_crawler_estrae_titoli_difficili():
    """Regressione R6 alla fonte: soup.title.string e' None su
    <title></title>, non "" — ed e' quel None che si propagava."""
    from bs4 import BeautifulSoup
    casi = [("<title></title>", ""), ("<title>  Spazi  </title>", "Spazi"),
            ("", "")]
    for frammento, atteso in casi:
        soup = BeautifulSoup("<html>%s<body>x</body></html>" % frammento,
                             "lxml")
        titolo = soup.title.get_text(strip=True) if soup.title else ""
        assert titolo == atteso


def test_lexical_una_voce_per_query(contesto):
    esito = mars_lexical.audit(contesto)
    assert [v["query"] for v in esito["per_query"]] == contesto["queries"]
    assert len(esito["rank"]) == len(contesto["chunks"])


def test_lexical_trova_il_chunk_nonostante_la_punteggiatura(contesto):
    """Regressione R18, sul percorso vero del modulo.

    Il chunk in forma di domanda — quello che il progetto vuole
    premiare — non prendeva credito per la parola cercata, perche'
    nell'indice era "funziona?" e nella query "funziona". Con la
    normalizzazione BM25 sulla lunghezza poteva finire SOTTO un chunk
    piu' corto che quella parola non la conteneva affatto.
    """
    contesto["chunks"] = [
        {"url": "https://x/", "heading": "Come funziona?",
         "text": "Il servizio si attiva in pochi minuti dopo la "
                 "registrazione online, senza configurazione manuale."},
        {"url": "https://x/", "heading": "Dove siamo",
         "text": "Come raggiungerci: la sede e' in centro."},
    ]
    contesto["queries"] = ["come funziona"]
    esito = mars_lexical.audit(contesto)
    assert esito["per_query"][0]["rank"][0] == 0, \
        "il chunk che contiene la frase cercata deve vincere"
    assert "Come funziona?" in esito["top_chunk"]


def test_lexical_tokenizza_anche_la_query(contesto):
    """Regressione R18, lato query.

    Corpus e query devono passare per la STESSA funzione: se solo il
    corpus viene ripulito, una query scritta con il punto interrogativo
    — cioe' come la scriverebbe un utente — smette di trovare quello
    che l'indice contiene. E' meta' del difetto, e da sola non
    produrrebbe alcun errore visibile.

    Il chunk atteso e' il SECONDO di proposito: quando nessun termine
    matcha, i punteggi sono tutti zero e sorted() restituisce l'ordine
    naturale. Con il bersaglio in prima posizione il test passerebbe
    anche a difetto reintrodotto — verificato, ed e' successo.
    """
    contesto["chunks"] = [
        {"url": "https://x/", "heading": "Sede",
         "text": "La nostra sede si trova in centro citta'."},
        {"url": "https://x/", "heading": "Preventivi",
         "text": "Il preventivo si richiede online in pochi minuti."},
    ]
    contesto["queries"] = ["preventivo?"]      # punteggiatura NELLA QUERY
    esito = mars_lexical.audit(contesto)
    assert esito["per_query"][0]["rank"][0] == 1


def test_semantic_falsi_positivi_answer_shaped():
    """Regressione R9: "chi" dentro chiave/archivio/macchina, e "come"
    e "dove" come congiunzioni."""
    falsi = ["La chiave di accesso e la macchina per l'architettura.",
             "Archivio storico: documenti, schede e chiavi di lettura.",
             "Un servizio comodo come la neve, nel luogo dove operiamo."]
    for testo in falsi:
        assert not mars_semantic.question_signals(testo, lingua="it"), testo


@pytest.mark.parametrize("testo, lingua", [
    ("Come funziona la fusione? Ecco la spiegazione.", "it"),
    ("What is reciprocal rank fusion", "en"),
    ("Wie funktioniert die Suche", "de"),
    ("Pourquoi utiliser cet outil", "fr"),
])
def test_semantic_riconosce_le_domande(testo, lingua):
    assert mars_semantic.question_signals(testo, lingua=lingua)


def test_semantic_segnali_strutturali():
    segnali = mars_semantic.question_signals(
        "Il prodotto si installa in pochi passi.",
        {"headings": ["Come si installa?"],
         "html": '<script type="application/ld+json">{"@type":"FAQPage"}'
                 '</script>'}, "it")
    assert "titolo interrogativo" in segnali
    assert "FAQPage JSON-LD" in segnali


# ----------------------------------------------------------------------
# mars_wapt (C9)
# ----------------------------------------------------------------------

def test_wapt_raggruppa_gli_alert_per_regola():
    """Regressione C9: ZAP emette un alert per URL, quindi un difetto
    su venti pagine affondava il punteggio da solo."""
    alert = [{"pluginId": "10038", "alert": "CSP assente", "risk": "High",
              "url": "https://x/%d" % i} for i in range(6)]
    esito = mars_wapt.score_from_alerts(alert)
    assert esito["rules_violated"] == 1
    assert esito["score"] > 40, "sei occorrenze non sono sei difetti"


def test_wapt_confidenza_fra_parentesi():
    esito = mars_wapt.score_from_alerts(
        [{"pluginId": "1", "risk": "Medium (High)", "alert": "X",
          "url": "https://x/"}])
    assert esito["alerts_by_risk"] == {"Medium": 1}


def test_wapt_informational_non_penalizza():
    esito = mars_wapt.score_from_alerts(
        [{"pluginId": "1", "risk": "Informational", "alert": "X",
          "url": "https://x/"}] * 3)
    assert esito["score"] == 100


def test_wapt_active_scan_richiede_la_dichiarazione():
    """Regressione C9: l'active scan invia payload d'attacco."""
    chiamate = {}

    class ClientFinto:
        def spider_scan(self, url):
            chiamate["spider"] = True
            return "0"

        def spider_status(self, sid):
            return 100

        def ascan_scan(self, url):
            chiamate["ascan"] = True
            return "0"

        def ascan_status(self, sid):
            return 100

        def alerts(self, baseurl):
            return []

    mars_wapt.run_zap("https://x/", ClientFinto(), active=False)
    assert chiamate.get("spider") and not chiamate.get("ascan")
    chiamate.clear()
    mars_wapt.run_zap("https://x/", ClientFinto(), active=True)
    assert chiamate.get("ascan")


# ----------------------------------------------------------------------
# mars_seo (R3)
# ----------------------------------------------------------------------

def test_seo_nessuna_shell(monkeypatch):
    """Regressione R3: l'URL veniva interpolato in una stringa di shell
    e arriva dal corpo di una richiesta API."""
    visto = {}

    def finto_run(cmd, **kwargs):
        visto["cmd"] = cmd
        visto["kwargs"] = kwargs
        # Un'eccezione che il modulo cattura: qui interessa COSA gli
        # viene passato, non cosa fa Lighthouse.
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/lighthouse")
    monkeypatch.setattr("subprocess.run", finto_run)
    mars_seo.audit({"url": "https://x/; rm -rf ~ #"})
    assert isinstance(visto["cmd"], list), "argomenti come lista, non stringa"
    assert visto["kwargs"].get("shell") is not True
    assert "https://x/; rm -rf ~ #" in visto["cmd"], "URL come argomento unico"
    assert visto["kwargs"].get("timeout"), "serve un timeout"


def test_seo_senza_lighthouse_non_da_zero(monkeypatch):
    """Regressione R4: score 0 e' un giudizio, non un'assenza."""
    monkeypatch.setattr("shutil.which", lambda n: None)
    esito = mars_seo.audit({"url": "https://x/"})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"


# ----------------------------------------------------------------------
# mars_citability (C1)
# ----------------------------------------------------------------------

def _risultati(**scores):
    base = {"mars_tech": {"score": 80}, "mars_seo": {"score": 70},
            "mars_schema": {"score": 60}, "mars_wcag": {"score": 90},
            "mars_wapt": {"score": 50},
            "mars_lexical": {"rank": [0, 1, 2]},
            "mars_semantic": {"rank": [0, 1, 2], "answer_shaped_ratio": 0.5}}
    for chiave, valore in scores.items():
        base[chiave] = valore
    return base


def test_citability_esclude_i_non_misurati():
    """Regressione R4/C1: un'area senza strumento non abbassa il
    profilo, lo rende meno informato."""
    completo = mars_citability.audit(
        {"results": _risultati(), "market": "global"})
    parziale = mars_citability.audit(
        {"results": _risultati(mars_seo={"score": None,
                                         "status": "unavailable"}),
         "market": "global"})
    assert parziale["signals"]["Qualità SEO"] is None
    assert any("non misurati" in i for i in parziale["issues"])
    assert parziale["score"] > completo["score"] - 30


def test_citability_il_mercato_conta():
    cn = mars_citability.audit({"results": _risultati(), "market": "cn"})
    eu = mars_citability.audit({"results": _risultati(), "market": "eu"})
    assert cn["score"] != eu["score"]
    assert cn["market"] == "cn"


def test_citability_mercato_ignoto_ripiega_dichiarandolo():
    esito = mars_citability.audit(
        {"results": _risultati(), "market": "atlantide"})
    assert esito["market"] == "global"
    assert any("sconosciuto" in i for i in esito["issues"])


def test_citability_dichiara_sempre_la_natura_euristica():
    esito = mars_citability.audit({"results": _risultati()})
    assert "euristiche" in esito["disclaimer"]


def test_citability_senza_risultati():
    esito = mars_citability.audit({"results": {}})
    assert esito["score"] is None and esito["status"] == "unavailable"


# ----------------------------------------------------------------------
# mars_llm_judge (C2)
# ----------------------------------------------------------------------

def test_llm_off_non_chiama_nulla(contesto):
    contesto["llm"] = "off"
    esito = mars_llm_judge.audit(contesto)
    assert esito["status"] == "disabled"


def test_llm_auto_senza_credenziali(contesto, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    contesto["llm"] = "auto"
    esito = mars_llm_judge.audit(contesto)
    assert esito["status"] == "unavailable"


def test_llm_percorso_completo_con_client_finto(contesto):
    inviato = {}

    class Blocco:
        type = "text"
        text = json.dumps({"citabilita": 71, "motivazione": "Motivo.",
                           "punti_forti": ["A"], "punti_deboli": ["B"],
                           "passaggio_migliore": 0})

    class Risposta:
        content = [Blocco()]
        stop_reason = "end_turn"

    class ClientFinto:
        def __init__(self):
            self.beta = type("B", (), {"messages": self})()

        def create(self, **kw):
            inviato.update(kw)
            return Risposta()

    contesto["llm"] = "on"
    contesto["_anthropic_client"] = ClientFinto()
    esito = mars_llm_judge.audit(contesto)
    assert esito["score"] == 71
    assert inviato["model"] == mars_llm_judge.MODEL
    assert inviato["output_config"]["format"]["type"] == "json_schema"
    assert "server-side-fallback" in inviato["betas"][0]
    assert inviato["max_tokens"] <= mars_llm_judge.MAX_TOKENS
    assert esito["costo_stimato"]["token_stimati_input"] > 0


def test_llm_seleziona_i_chunk_dall_rrf(contesto):
    contesto["results"] = {"mars_lexical": {"rank": [1, 0]},
                           "mars_semantic": {"rank": [1, 0]}}
    scelti = mars_llm_judge.seleziona_chunk(contesto)
    assert scelti[0] is contesto["chunks"][1]
