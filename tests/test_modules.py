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
import sys
import time
import types

import pytest
import requests
from requests.structures import CaseInsensitiveDict

import mars_citability
import mars_core
import mars_lexical
import mars_llm_judge
import mars_schema
import mars_semantic
import mars_seo
import mars_tech
import mars_wapt
import mars_wcag
from conftest import pagina
from mars_core import (AREA_PREFIX, MODULES_REGISTRY, SEV_CRITICAL,
                       SEV_INFO, SEV_WARNING, chiave_esterna,
                       load_external_module)
from mars_report import STATO_LEGGIBILE


# ----------------------------------------------------------------------
# Contratto comune a tutte le aree
# ----------------------------------------------------------------------

# Derivata dal REGISTRO, non scritta a mano: mars_seo e mars_wapt ne
# erano fuori — due moduli su nove mai verificati contro il contratto —
# e nessuno se n'era accorto perche' l'elenco andava tenuto allineato a
# mano. Cosi' un'area nuova entra nel contratto il giorno in cui entra
# nel registro, e la fixture strumenti_esterni_assenti garantisce che
# nessuno di loro avvii davvero Lighthouse, ZAP o un browser.
MODULI = [load_external_module(nome) for nome, _ in MODULES_REGISTRY]
assert all(MODULI), "un modulo del registro non si carica: %s" % [
    n for (n, _), m in zip(MODULES_REGISTRY, MODULI) if m is None]


def test_il_contratto_copre_ogni_area_del_registro():
    """Nessuna area fuori dal contratto, mai piu'.

    mars_seo e mars_wapt ne erano fuori — due su nove — perche'
    l'elenco andava tenuto allineato a mano e nessuno se n'era accorto:
    una suite non puo' accorgersi da se' di QUANTI casi ha girato, e
    troncare la lista non fa fallire nulla. L'invariante va quindi
    asserito, non dedotto dalla derivazione.
    """
    assert [m.__name__ for m in MODULI] == [n for n, _ in MODULES_REGISTRY]


@pytest.mark.parametrize("modulo", MODULI, ids=lambda m: m.__name__)
def test_ogni_modulo_rispetta_il_contratto(modulo, contesto):
    esito = modulo.audit(contesto)
    assert isinstance(esito, dict)
    if "score" in esito and esito["score"] is not None:
        assert 0 <= esito["score"] <= 100
    assert isinstance(esito.get("issues", []), list)


@pytest.mark.parametrize("modulo", MODULI, ids=lambda m: m.__name__)
def test_nessuno_score_none_senza_stato(modulo, contesto):
    """Regressione R38: score None SENZA status era un terzo stato che
    il vocabolario del referto non contempla.

    `score: None` piu' `status` dice PERCHE' non c'e' un punteggio —
    strumento assente, area disattivata, classifica invece di voto. Un
    None muto le collassa tutte su "non misurato", che e' una diagnosi
    diversa da ciascuna di esse. Vale per ogni modulo, non solo per i
    due che avevano il difetto: e' un contratto, non una correzione."""
    esito = modulo.audit(contesto)
    if esito.get("score") is None and "error" not in esito:
        assert esito.get("status"), (
            "%s: score None senza dire perche'" % modulo.__name__)
        assert esito["status"] in STATO_LEGGIBILE, (
            "%s: stato %r fuori dal vocabolario del referto"
            % (modulo.__name__, esito["status"]))


@pytest.mark.parametrize("modulo, chiave", [
    (mars_schema, "sd.status.no_pages"),
    (mars_wcag, "wcag.status.no_pages"),
], ids=lambda x: getattr(x, "__name__", x))
def test_pagine_vuote_danno_non_misurato(modulo, chiave):
    """Regressione R6: mars_wcag andava in IndexError.

    E U1: anche un'area non misurata deve portare il proprio rilievo,
    altrimenti e' l'unica a sparire dagli elenchi che le fasi
    successive costruiranno sui findings."""
    esito = modulo.audit({"pages": {}, "url": "https://x/"})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert [f["key"] for f in esito["findings"]] == [chiave]
    assert esito["findings"][0]["severity"] == SEV_INFO


def test_citability_senza_un_solo_segnale_dichiara_lo_stato():
    """R38: con nessun segnale misurabile il composito non esiste, e
    prima usciva come score None muto — indistinguibile da un'area mai
    eseguita."""
    esito = mars_citability.audit({
        "market": "eu",
        # C'e' un'area, quindi non scatta l'uscita anticipata, ma
        # nessuna porta un punteggio.
        "results": {"mars_tech": {"score": None},
                    "mars_seo": {"score": None}}})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"


def test_llm_judge_senza_punteggio_dichiara_lo_stato(contesto):
    """R38: il modello puo' rispondere con un JSON valido e ometterne il
    punteggio.

    E' una risposta, non una misura: senza status finiva nel referto
    come score None muto, indistinguibile da un'area mai eseguita. Il
    percorso e' quello vero — client iniettato da
    context["_anthropic_client"], che e' il punto documentato — non un
    ramo scorciatoiato."""
    class Blocco:
        type = "text"
        # JSON valido, ma senza "citabilita".
        text = json.dumps({"motivazione": "Motivo.",
                           "punti_forti": ["A"], "punti_deboli": ["B"]})

    class Risposta:
        content = [Blocco()]
        stop_reason = "end_turn"

    class ClientFinto:
        def __init__(self):
            self.beta = type("B", (), {"messages": self})()

        def create(self, **kw):
            return Risposta()

    contesto["llm"] = "on"
    contesto["_anthropic_client"] = ClientFinto()
    esito = mars_llm_judge.audit(contesto)

    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert any("senza indicare un punteggio" in i for i in esito["issues"]), \
        "e va detto perche', non solo che non c'e'"


@pytest.mark.parametrize("modulo, atteso", [
    (mars_lexical, "BM25"),
    (mars_semantic, "proxy char-TFIDF"),
])
def test_le_aree_di_classifica_dichiarano_lo_strumento(contesto, modulo,
                                                       atteso):
    """Un rango senza il nome di chi l'ha calcolato non e' verificabile,
    e il referto non lo diceva affatto.

    Per il vettoriale la distinzione conta il doppio: il modello
    multilingue e il proxy char-TFIDF non misurano la stessa cosa, e
    dichiarare il primo mentre gira il secondo sarebbe una misura
    attribuita a uno strumento che non l'ha prodotta."""
    contesto["force_proxy"] = True
    esito = modulo.audit(contesto)
    assert esito["status"] == "ranking"
    assert atteso in esito["tool"]


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


def test_tech_none_equivale_a_noindex_nofollow():
    """Regressione R25: la ricerca della sottostringa 'noindex' mancava
    `none`, che per Google e Bing significa esattamente
    `noindex, nofollow`. Un sito interamente de-indicizzato prendeva 97
    su 100, lo stesso di un sito perfettamente aperto.

    L'asserzione forte e' l'uguaglianza fra i due sinonimi: due
    scritture della stessa direttiva devono ricevere lo stesso
    giudizio, non solo un giudizio qualsiasi."""
    compatto = mars_tech.audit(_contesto_tech(meta_robots="none"))
    esteso = mars_tech.audit(_contesto_tech(meta_robots="noindex, nofollow"))
    aperto = mars_tech.audit(_contesto_tech())

    assert compatto["issues"] == esteso["issues"]
    assert compatto["score"] == esteso["score"]
    assert compatto["findings_by_severity"].get("critico") == 1
    assert aperto["score"] - compatto["score"] >= 40

    # E dall'header, dove nessuno la vede guardando il DOM.
    header = mars_tech.audit(_contesto_tech(x_robots_tag="none"))
    assert header["issues"] == esteso["issues"]

    # Per specifica le direttive sono insensibili al maiuscolo. Oggi il
    # crawler le abbassa gia' lui, ma il `context` e' un dict che
    # attraversa il confine dei plugin: la funzione non puo' contarci.
    urlato = mars_tech.audit(_contesto_tech(meta_robots="NONE"))
    assert urlato["issues"] == esteso["issues"]


def test_tech_all_non_e_una_restrizione():
    """`all` e' il default esplicito: non e' un rilievo, e non annulla
    nulla. Fra direttive in conflitto vince la piu' restrittiva."""
    esplicito = mars_tech.audit(_contesto_tech(meta_robots="all"))
    muto = mars_tech.audit(_contesto_tech())
    conflitto = mars_tech.audit(_contesto_tech(meta_robots="all, noindex"))

    assert esplicito["score"] == muto["score"]
    assert esplicito["issues"] == muto["issues"]
    assert not any("indici" in i or "seguire" in i
                   for i in esplicito["issues"])
    assert conflitto["findings_by_severity"].get("critico") == 1


def test_tech_nofollow_su_tutto_il_sito_pesa_piu_che_su_una_pagina():
    """Un `nofollow` su una pagina e' una scelta legittima; su tutte,
    la scoperta dipende interamente dalla sitemap.

    Le due pagine sono ordinate con quella *senza* nofollow per prima,
    cosi' il test non passerebbe per l'ordine naturale del dict."""
    def sito(*direttive):
        ctx = _contesto_tech()
        ctx["pages"] = {
            "https://esempio.test/p%d" % n: pagina(meta_robots=d)
            for n, d in enumerate(direttive)}
        return mars_tech.audit(ctx)

    parziale = sito("", "nofollow")
    totale = sito("nofollow", "nofollow")

    assert parziale["findings_by_severity"].get("lieve")
    assert totale["findings_by_severity"].get("medio")
    assert parziale["score"] > totale["score"]
    assert "1/2" in "".join(parziale["issues"])
    assert "2/2" in "".join(totale["issues"])


def test_tech_direttive_da_piu_meta_tag():
    """Il crawler unisce con uno spazio i `content` di piu' meta
    (`robots` e `googlebot`): le direttive vanno separate anche li',
    non solo sulle virgole. Qui la pagina passa dal costruttore vero,
    non da un dizionario scritto a mano."""
    p = pagina(html='<html lang="it"><head>'
                    '<meta name="robots" content="noindex">'
                    '<meta name="googlebot" content="nofollow">'
                    '</head><body><p>x</p></body></html>')
    assert p["meta_robots"] == "noindex nofollow"

    ctx = _contesto_tech()
    ctx["pages"] = {"https://esempio.test/": p}
    esito = mars_tech.audit(ctx)
    assert esito["findings_by_severity"].get("critico") == 1
    assert any("seguire i propri link" in i for i in esito["issues"])


# --- U1.3: i rilievi di mars_tech come dato --------------------------

TECH_CHIAVI = {
    "tech.robots.missing", "tech.robots.ai_blocked",
    "tech.robots.ai_unmentioned", "tech.robots.self_blocked",
    "tech.sitemap.missing", "tech.sitemap.not_in_robots",
    "tech.sitemap.unreadable", "tech.sitemap.no_lastmod",
    "tech.index.noindex", "tech.index.nofollow",
    "tech.canonical.cross_host", "tech.canonical.missing",
}


def test_tech_ogni_rilievo_ha_una_chiave_stabile():
    """La chiave e' cio' su cui poggeranno il piano di interventi, il
    confronto fra due esecuzioni e la traduzione: non contiene mai un
    valore variabile, e il primo segmento e' il prefisso dell'area."""
    ctx = _contesto_tech("User-agent: GPTBot\nDisallow: /\n\n"
                         "User-agent: *\nAllow: /",
                         meta_robots="none",
                         canonical="https://altro.example/")
    ctx["sitemap"] = {"found": False}
    esito = mars_tech.audit(ctx)
    chiavi = [f["key"] for f in esito["findings"]]

    assert chiavi, "nessun rilievo strutturato"
    assert len(chiavi) == len(set(chiavi)), "chiavi duplicate nello stesso audit"
    for chiave in chiavi:
        assert chiave in TECH_CHIAVI, "chiave non prevista: %s" % chiave
        parti = chiave.split(".")
        assert len(parti) == 3, "profondita' fissa a tre segmenti: %s" % chiave
        assert parti[0] == AREA_PREFIX["mars_tech"]

    # Tanti findings quante issues: sono lo stesso insieme, due viste.
    assert len(esito["findings"]) == len(esito["issues"])


def test_tech_la_gravita_grezza_non_si_perde():
    """Le quattro severita' canoniche collassano `grave` e `medio`
    entrambe in warning. Chi conosce la scala di MARS perderebbe
    l'informazione, quindi la parola italiana resta accanto — non al
    posto — di quella canonica."""
    ctx = _contesto_tech()
    ctx["sitemap"] = {"found": True, "from_robots": False, "urls": 3,
                      "with_lastmod": 0, "unreadable": 2}
    per_chiave = {f["key"]: f for f in mars_tech.audit(ctx)["findings"]}

    unreadable = per_chiave["tech.sitemap.unreadable"]
    assert (unreadable["severity"], unreadable["source_severity"]) == \
        (SEV_WARNING, "medio")
    assert unreadable["weight"] == 1.0

    lastmod = per_chiave["tech.sitemap.no_lastmod"]
    assert (lastmod["severity"], lastmod["source_severity"]) == \
        (SEV_INFO, "lieve")


def test_tech_la_gravita_calcolata_a_runtime_e_quella_vera():
    """Due rilievi cambiano gravita' secondo la diffusione: non basta
    dedurla dalla chiave, va portata quella CALCOLATA."""
    def sito(*direttive):
        ctx = _contesto_tech()
        ctx["pages"] = {"https://esempio.test/p%d" % n: pagina(meta_robots=d)
                        for n, d in enumerate(direttive)}
        return {f["key"]: f for f in mars_tech.audit(ctx)["findings"]}

    tutte = sito("noindex", "noindex")["tech.index.noindex"]
    assert (tutte["severity"], tutte["source_severity"]) == \
        (SEV_CRITICAL, "critico")

    alcune = sito("", "noindex")["tech.index.noindex"]
    assert (alcune["severity"], alcune["source_severity"]) == \
        (SEV_WARNING, "grave")
    assert alcune["params"]["pagine"] == 1
    assert alcune["params"]["totale"] == 2


def test_tech_ogni_rilievo_porta_la_penalita_applicata():
    """La Fase 4 calcolera' quanto risalirebbe il punteggio se un
    rilievo fosse risolto: senza la penalita' vera non e' calcolabile,
    e `weight` non serve — vale 2.0/1.0 ed e' importanza relativa,
    non punti.

    L'asserzione forte e' l'identita' con il punteggio: la somma delle
    penalita' dichiarate deve ricostruire lo score, altrimenti il
    referto direbbe un numero e i rilievi un altro."""
    ctx = _contesto_tech("User-agent: GPTBot\nDisallow: /\n\n"
                         "User-agent: *\nAllow: /", meta_robots="noindex")
    esito = mars_tech.audit(ctx)
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == max(0, round(100 - somma))
    assert somma > 0

    per_chiave = {f["key"]: f for f in esito["findings"]}
    assert per_chiave["tech.robots.ai_blocked"]["params"]["penalty"] == 40.0
    # E il peso NON e' la penalita': due numeri diversi, due scale.
    assert per_chiave["tech.robots.ai_blocked"]["weight"] == 2.0


def test_tech_il_dato_canonico_non_tronca():
    """La issue elenca cinque crawler ma il conteggio non e' troncato:
    con sei bloccati il testo dice un numero ed elenca meno. La vista
    compatta puo' permetterselo, il dato no."""
    ctx = _contesto_tech("\n\n".join(
        "User-agent: %s\nDisallow: /" % a
        for a in ("GPTBot", "ClaudeBot", "CCBot", "Bytespider",
                  "Amazonbot", "PerplexityBot")) + "\n\nUser-agent: *\nAllow: /")
    esito = mars_tech.audit(ctx)
    f = [x for x in esito["findings"]
         if x["key"] == "tech.robots.ai_blocked"][0]
    issue = [i for i in esito["issues"] if "BLOCCA" in i][0]

    assert f["params"]["n"] == 6
    assert len(f["params"]["bloccati"]) == 6, "il dato deve portarli tutti"
    assert issue.count(",") == 4, "la vista compatta ne elenca cinque"
    assert "PerplexityBot" not in issue and "PerplexityBot" in f["params"]["bloccati"]


def test_tech_la_vista_compatta_usa_la_parola_italiana():
    """`[critico]`, non `[critical]`.

    E' cio' che l'utente legge dal C10 in poi, ed e' la scala che il
    referto documenta. Nessun test lo asseriva: le uguaglianze fra due
    esecuzioni (R25) cambierebbero insieme, quindi non discriminano."""
    ctx = _contesto_tech("User-agent: GPTBot\nDisallow: /\n\n"
                         "User-agent: *\nAllow: /")
    issues = mars_tech.audit(ctx)["issues"]
    assert issues[0].startswith("[critico] ")
    for issue in issues:
        prefisso = issue.split("]")[0].lstrip("[")
        assert prefisso in mars_tech.PESI, \
            "prefisso %r fuori dalla scala di MARS" % prefisso


def test_tech_lo_score_resta_un_intero():
    """Le penalita' sono float perche' altre aree le scalano per
    diffusione. Senza arrotondare, lo score uscirebbe 94.0 dove usciva
    94: la vista non cambierebbe (stampa %.0f) ma il JSON si', e i
    test non se ne accorgerebbero perche' 94 == 94.0."""
    esito = mars_tech.audit(_contesto_tech())
    assert isinstance(esito["score"], int), \
        "score %r: cambio di contratto silenzioso nel JSON" % esito["score"]


def test_tech_l_ordine_dei_rilievi_segue_la_penalita_non_il_peso():
    """Ordinare per `weight` sembra equivalente e non lo e': `critico`
    e `grave` pesano entrambi 2.0, quindi pareggerebbero, e un
    ordinamento stabile lascerebbe l'ordine d'inserimento.

    Il caso e' costruito perche' i due ordini divergano: la sitemap
    mancante (grave) viene prodotta PRIMA del noindex (critico)."""
    ctx = _contesto_tech(meta_robots="noindex")
    ctx["sitemap"] = {"found": False}
    esito = mars_tech.audit(ctx)

    chiavi = [f["key"] for f in esito["findings"]]
    assert chiavi.index("tech.index.noindex") < \
        chiavi.index("tech.sitemap.missing"), \
        "il critico deve precedere il grave, non pareggiarci"
    # E le issues seguono lo stesso ordine: sono la stessa lista.
    assert esito["issues"][0].startswith("[critico]")


def test_tech_i_findings_arrivano_al_referto(contesto):
    """Il punto d'integrazione: il modulo puo' produrli benissimo e
    build_report buttarli via, perche' copia una lista chiusa di
    chiavi. E' il difetto che U1.2 ha prevenuto — qui si verifica che
    resti prevenuto."""
    from mars_report import build_report
    contesto["results"] = {"mars_tech": mars_tech.audit(_contesto_tech())}
    referto = build_report(contesto["results"], contesto)
    area = [a for a in referto["areas"] if a["module"] == "mars_tech"][0]
    assert area["findings"], "i findings non arrivano al referto"
    assert all(f["key"].startswith("tech.") for f in area["findings"])


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


def test_tech_robots_vuoto_non_e_robots_assente():
    """Regressione R24: un robots.txt servito a 200 ma vuoto veniva
    riportato come assente, con un rilievo di gravita' media.

    "Tutto permesso" e "nessuna indicazione" sono cose diverse, e la
    prima e' una scelta esplicita del sito."""
    vuoto = mars_tech.audit(_contesto_tech(""))
    assente = _contesto_tech()
    assente["robots"] = {"found": False, "text": "", "sitemaps": []}
    assente = mars_tech.audit(assente)
    assert not any("assente" in i for i in vuoto["issues"])
    assert any("assente" in i for i in assente["issues"])
    assert vuoto["score"] > assente["score"]


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


# --- U1.4: i rilievi di mars_schema come dato ------------------------

SD_BUONO = '<script type="application/ld+json">{"@type":"Organization"}</script>'
SD_VUOTO = '<script type="application/ld+json"></script>'
SD_ROTTO = '<script type="application/ld+json">{non json}</script>'


def _sito_schema(*frammenti_per_pagina):
    return {"pages": {"https://x/p%d" % i: pagina(
        html="<html><body>%s</body></html>" % "".join(f))
        for i, f in enumerate(frammenti_per_pagina)}}


def test_schema_un_controllo_e_un_rilievo_anche_con_molti_blocchi():
    """Regola dell'adeguamento: un controllo = un Finding, le occorrenze
    stanno nei params.

    Non e' estetica. In quest'area `score -= 5` sta accanto a ogni
    append, quindi la cardinalita' della lista E' accoppiata al
    punteggio: spezzare un controllo in N rilievi farebbe crollare i
    punteggi di chiunque li conti. E' il difetto C10 gia' pagato in
    mars_tech.

    Qui i due ordini divergono di proposito: tre blocchi difettosi,
    tre issues, ma DUE rilievi."""
    esito = mars_schema.audit(_sito_schema([SD_VUOTO, SD_ROTTO],
                                           [SD_VUOTO, SD_BUONO]))
    assert len(esito["issues"]) == 3, "la vista compatta resta per blocco"
    assert len(esito["findings"]) == 2, "il dato canonico aggrega per controllo"

    per_chiave = {f["key"]: f for f in esito["findings"]}
    assert per_chiave["sd.jsonld.block_empty"]["params"]["n"] == 2
    assert per_chiave["sd.jsonld.block_malformed"]["params"]["n"] == 1
    # E gli URL ci sono, deduplicati e ordinati: servono a chi corregge.
    assert per_chiave["sd.jsonld.block_empty"]["params"]["urls"] == [
        "https://x/p0", "https://x/p1"]


def test_schema_le_penalita_ricostruiscono_il_punteggio():
    """La penalita' dichiarata da un rilievo aggregato e' quella TOTALE
    del controllo: n x per-occorrenza. Se non lo fosse, il referto
    direbbe un punteggio e i rilievi ne giustificherebbero un altro."""
    for ctx in (_sito_schema([], []),
                _sito_schema([SD_VUOTO, SD_ROTTO], [SD_VUOTO]),
                _sito_schema([SD_BUONO])):
        esito = mars_schema.audit(ctx)
        somma = sum(f["params"]["penalty"] for f in esito["findings"])
        assert esito["score"] == max(0, round(100 - somma))


@pytest.mark.parametrize("frammenti, score, motivo", [
    ([SD_BUONO], 100, "un blocco valido non costa nulla"),
    ([SD_VUOTO], 95, "un blocco vuoto costa 5"),
    ([SD_ROTTO], 90, "un blocco malformato costa 10, il doppio di un vuoto"),
    ([SD_VUOTO, SD_ROTTO], 85, "e si sommano"),
    ([], 50, "l'assenza totale costa 50, meta' del punteggio"),
])
def test_schema_le_penalita_hanno_valori_fissati(frammenti, score, motivo):
    """I valori, non solo la loro relazione.

    Un test che verifica soltanto «la somma delle penalita' ricostruisce
    lo score» resta verde anche se si cambia una penalita': cambiano
    insieme. Ma quei numeri sono la scala editoriale dell'area, e
    spostarne uno sposta ogni punteggio del sito in silenzio.

    L'ordine fra i due difetti e' la parte con un significato: un
    blocco malformato costa il DOPPIO di uno vuoto, perche' un JSON
    rotto e' un errore, un blocco vuoto una dimenticanza."""
    assert mars_schema.audit(_sito_schema(frammenti))["score"] == score, motivo


def test_schema_la_gravita_e_dichiarata_come_editoriale():
    """Quest'area non ha una scala propria: la gravita' l'abbiamo
    scelta noi, e `source_severity` deve restare VUOTO.

    Le issues di mars_schema non portano alcun prefisso di severita',
    quindi dichiararne una attribuirebbe al modulo una scala che non
    pubblica — l'opposto di mars_tech, dove `[critico]` e' la parola
    che l'utente legge."""
    esito = mars_schema.audit(_sito_schema([SD_VUOTO], []))
    assert esito["findings"]
    for f in esito["findings"]:
        assert f["source_severity"] == "", \
            "%s: nessuno strumento ha detto questa gravita'" % f["key"]


def test_schema_json_ld_assente_non_e_critico():
    """Scelta dichiarata: costa meta' punteggio ma resta `warning`.

    In MARS `critical` significa che il sito e' INVISIBILE agli
    assistenti — e' l'uso che ne fa mars_tech con i crawler bloccati e
    le pagine noindex. Senza JSON-LD il sito e' meno leggibile, non
    invisibile: appiattire la differenza toglierebbe senso al livello
    piu' alto."""
    esito = mars_schema.audit(_sito_schema([], []))
    f = esito["findings"][0]
    assert f["key"] == "sd.jsonld.missing"
    assert f["severity"] == SEV_WARNING
    assert f["weight"] == 2.0
    assert f["params"]["penalty"] == 50.0


def test_schema_le_chiavi_usano_il_prefisso_dell_area():
    """`sd.`, non `schema.`: e' il prefisso del riferimento, e i
    cataloghi di traduzione della Fase 9 sono riusabili solo se le
    chiavi coincidono dove il controllo coincide."""
    esito = mars_schema.audit(_sito_schema([SD_VUOTO, SD_ROTTO]))
    esito["findings"].append(
        mars_schema.audit({"pages": {}})["findings"][0])
    for f in esito["findings"]:
        parti = f["key"].split(".")
        assert len(parti) == 3, f["key"]
        assert parti[0] == AREA_PREFIX["mars_schema"] == "sd"


def test_schema_anche_l_area_non_misurata_ha_un_rilievo():
    """Senza pagine l'area non e' misurabile, ed e' uno STATO: deve
    comparire negli elenchi costruiti sui rilievi, non sparirne."""
    esito = mars_schema.audit({"pages": {}})
    assert esito["status"] == "unavailable"
    assert [f["key"] for f in esito["findings"]] == ["sd.status.no_pages"]
    assert esito["findings"][0]["severity"] == SEV_INFO


# ----------------------------------------------------------------------
# mars_wcag (C8)
# ----------------------------------------------------------------------

HTML_ACCESSIBILE = """<html lang="it"><body><h1>A</h1><h2>B</h2>
<label for="q">Cerca</label><input id="q">
<table><tr><th>H</th></tr></table>
<a href="/g">Guida completa alla fusione</a></body></html>"""

HTML_INACCESSIBILE = """<html><body><h1>A</h1><h4>Salto</h4>
<form><input type="text" name="senza">
<input type="submit" value="Invia"><input type="reset" value="Annulla">
<button type="button">Chiudi</button><input type="hidden" name="csrf"></form>
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
    # submit, reset e hidden non hanno un'etichetta da mostrare: i primi
    # due prendono il nome dal proprio valore, il terzo non si vede.
    # Solo il campo di testo nudo e' un difetto.
    assert "1 campi di modulo" in testo, \
        "i campi non interattivi non vanno contati"


def test_wcag_dichiara_sempre_il_livello():
    esito = mars_wcag.audit({"pages": {"https://x/": pagina()}})
    assert "WCAG 2.1" in esito["wcag_level"]


# --- U1.5: i rilievi di mars_wcag come dato --------------------------

def test_wcag_il_criterio_non_e_una_gravita():
    """`[1.3.1/3.3.2]` e' il RIFERIMENTO che rende il rilievo
    verificabile da chi lo riceve, non un livello di severita'.

    Va nei params e resta nel testo della issue; la gravita' e'
    un'altra cosa, ed e' una scelta editoriale nostra — quindi
    `source_severity` resta vuoto."""
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_INACCESSIBILE)}})
    per_chiave = {f["key"]: f for f in esito["findings"]}

    campi = per_chiave["wcag.form.label_missing"]
    assert campi["params"]["criterio"] == "1.3.1/3.3.2"
    assert campi["source_severity"] == "", \
        "nessuno strumento ha espresso questa gravita'"
    # E il criterio resta dov'era, nella riga che l'utente legge.
    assert any(i.startswith("[1.3.1/3.3.2] ") for i in esito["issues"])


def test_wcag_la_gravita_statica_distingue_cio_che_blocca():
    """Scelta dichiarata: `critico` a cio' che blocca uno screen
    reader — niente alternativa testuale, niente etichetta, niente
    lingua — e non a cio' che rende la navigazione peggiore."""
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_INACCESSIBILE)}})
    per_chiave = {f["key"]: f for f in esito["findings"]}
    for chiave in ("wcag.img.alt_missing", "wcag.form.label_missing",
                   "wcag.lang.missing"):
        assert per_chiave[chiave]["severity"] == SEV_CRITICAL, chiave
    for chiave in ("wcag.table.th_missing", "wcag.tabindex.positive",
                   "wcag.heading.skip"):
        assert per_chiave[chiave]["severity"] == SEV_WARNING, chiave
    assert per_chiave["wcag.link.generic"]["severity"] == SEV_INFO


def test_wcag_il_ripiego_marca_ogni_rilievo_come_di_superficie():
    """Senza il marcatore, un elenco di soli findings mostrerebbe un
    `critical` come se venisse da una misura che non c'e' stata.

    E' lo stesso principio di R21, portato dentro il dato: qui il
    punteggio nasce dal markup, non da un browser."""
    esito = mars_wcag.audit({"pages": {"https://x/": pagina(
        html=HTML_INACCESSIBILE)}})
    assert esito["status"] == "surface"
    assert esito["findings"]
    for f in esito["findings"]:
        assert f["params"]["surface"] is True, f["key"]
        # E qui, e solo qui, i controlli statici pagano il punteggio.
        assert f["params"]["penalty"] == 12.0
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == max(0, round(100 - somma))


def test_wcag_nel_ramo_axe_gli_statici_non_pagano_il_punteggio(contesto,
                                                               monkeypatch):
    """Il punteggio viene dalle violazioni: i controlli statici
    restano nei rilievi — coprono l'intero campione, mentre axe ne
    vede solo le prime pagine — ma la loro penalita' e' zero.

    Dirlo conta: la Fase 4 calcolera' i guadagni proprio da quel
    numero, e attribuire 12 punti a un rilievo che non ne toglie
    nessuno prometterebbe un miglioramento inesistente."""
    contesto["pages"] = {"https://x/": pagina(html=HTML_INACCESSIBILE)}
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe",
                        lambda urls, delay=0.0: ([_viol()], 1))
    esito = mars_wcag.audit(contesto)

    statici = [f for f in esito["findings"] if f["key"] in mars_wcag.STATICI]
    assert statici, "i controlli statici devono restare"
    for f in statici:
        assert f["params"]["penalty"] == 0.0, \
            "%s: nel ramo axe non tocca il punteggio" % f["key"]
        assert "surface" not in f["params"]


def test_wcag_axe_impact_assente_non_diventa_un_giudizio_di_axe():
    """axe puo' omettere `impact`, e MARS lo appiattisce a "minor" per
    poter comunque pesare la violazione. E' una NOSTRA assunzione:
    scrivere "axe:minor" attribuirebbe ad axe un giudizio che non ha
    espresso."""
    dichiarato = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical", "help": "H", "nodes": [0]}], 1)
    taciuto = mars_wcag.score_from_violations(
        [{"id": "image-alt", "help": "H", "nodes": [0]}], 1)

    assert dichiarato["findings"][0]["source_severity"] == "axe:critical"
    assert taciuto["findings"][0]["source_severity"] == ""
    # Il punteggio invece si calcola lo stesso: l'assunzione serve a quello.
    assert taciuto["score"] < 100


def test_wcag_la_penalita_axe_ricostruisce_il_punteggio():
    """La penalita' di axe non e' il peso della regola: e' il peso
    SCALATO PER DIFFUSIONE, da 1x se la regola tocca una pagina sola a
    2x se le tocca tutte.

    E' calcolabile solo dentro il ciclo che la applica, quindi va
    registrata li'. Il caso e' costruito perche' le due diffusioni
    divergano: una regola su entrambe le pagine, una su una sola."""
    violazioni = [
        {"id": "image-alt", "impact": "critical", "help": "H", "nodes": [0]},
        {"id": "image-alt", "impact": "critical", "help": "H", "nodes": [0]},
        {"id": "label", "impact": "serious", "help": "L", "nodes": [0]},
    ]
    esito = mars_wcag.score_from_violations(violazioni, pagine_testate=2)
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == max(0, round(100 - somma))

    per_chiave = {f["key"]: f for f in esito["findings"]}
    # image-alt tocca 2 pagine su 2 -> 2x; label 1 su 2 -> 1.5x
    assert per_chiave["wcag.axe.image_alt"]["params"]["penalty"] == 25 * 2.0
    assert per_chiave["wcag.axe.label"]["params"]["penalty"] == 12 * 1.5


def test_wcag_la_scansione_parziale_e_un_rilievo(contesto, monkeypatch):
    """Una scansione parziale vale piu' di niente, ma spacciarla per
    completa no (C9). Il fatto sta gia' in `complete`; qui deve
    comparire anche fra i rilievi, altrimenti sparisce da ogni elenco
    costruito su quelli."""
    contesto["pages"] = {"https://x/%d" % i: pagina() for i in range(4)}
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe",
                        lambda urls, delay=0.0: ([_viol()], 2))
    esito = mars_wcag.audit(contesto)

    assert esito["complete"] is False
    stato = [f for f in esito["findings"] if f["key"] == "wcag.status.partial"]
    assert len(stato) == 1
    assert stato[0]["params"] == {"mancate": 2, "tentate": 4, "analizzate": 2}
    # E non pesa sul punteggio: e' uno stato, non un difetto del sito.
    assert "penalty" not in stato[0]["params"]


def test_wcag_gli_id_di_axe_vengono_sanificati():
    """Gli id vengono da axe, quindi sono dato esterno: un punto
    dentro l'id romperebbe la profondita' fissa a tre segmenti, e con
    essa le ancore del referto e la ricerca a catalogo."""
    esito = mars_wcag.score_from_violations(
        [{"id": "color.contrast", "impact": "serious", "help": "H",
          "nodes": [0]}], 1)
    f = esito["findings"][0]
    assert f["key"] == "wcag.axe.color_contrast"
    assert len(f["key"].split(".")) == 3
    # L'id grezzo non si perde: e' quello che axe conosce.
    assert f["params"]["rule"] == "color.contrast"


def test_wcag_il_dato_axe_non_tronca_a_cinque():
    """La vista compatta ne elenca cinque; il dato li porta tutti."""
    violazioni = [{"id": "regola-%d" % n, "impact": "minor",
                   "help": "H%d" % n, "nodes": [0]} for n in range(8)]
    esito = mars_wcag.score_from_violations(violazioni, 1)
    assert len(esito["issues"]) == 5
    assert len(esito["findings"]) == 8


def test_wcag_axe_porta_l_helpurl_per_la_correzione():
    """axe fornisce `helpUrl` e finora veniva scartato: e' il link
    alla spiegazione della regola, cioe' meta' del lavoro della Fase 3."""
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical", "help": "H",
          "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/image-alt",
          "nodes": [0]}], 1)
    assert esito["findings"][0]["url"].endswith("/image-alt")


def _viol(rid="a", gravita="serious"):
    return {"id": rid, "impact": gravita, "help": rid, "nodes": [0]}


# --- finto Playwright: esercita il CORPO di run_axe senza un browser ---
# Iniettare run_axe dall'esterno prova audit() ma lascia il conteggio
# delle pagine — cioe' il difetto R20 — mai eseguito. E' lo stesso
# schema del finto daemon ZAP in C9, con la stessa avvertenza: un banco
# di prova troppo accomodante conferma anche cio' che e' sbagliato,
# quindi qui la navigazione fallisce davvero sugli URL indicati.

class _PaginaFinta:
    def __init__(self, falliscono):
        self.falliscono = set(falliscono)
        self.visitate = []
        # Le pause richieste, per verificare che il ritardo fra due
        # visite non sia codice morto (R26).
        self.pause = []

    def goto(self, url, **kwargs):
        self.visitate.append(url)
        if url in self.falliscono:
            raise RuntimeError("navigazione fallita")

    def add_script_tag(self, **kwargs):
        pass

    def evaluate(self, script, arg=None):
        return [_viol()]

    def wait_for_timeout(self, ms):
        self.pause.append(ms)


class _PlaywrightFinto:
    def __init__(self, pagina_finta):
        self._pagina = pagina_finta
        self.chromium = types.SimpleNamespace(
            launch=lambda **kwargs: types.SimpleNamespace(
                new_page=lambda: self._pagina, close=lambda: None))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _playwright_finto(monkeypatch, falliscono=()):
    pagina_finta = _PaginaFinta(falliscono)
    modulo = types.ModuleType("playwright.sync_api")
    modulo.sync_playwright = lambda: _PlaywrightFinto(pagina_finta)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", modulo)
    return pagina_finta


def test_run_axe_senza_una_sola_pagina_analizzata(monkeypatch):
    """Regressione R20, nel punto esatto in cui viveva il difetto.

    Con tutte le navigazioni fallite run_axe restituiva [] — che
    audit() leggeva come "nessuna violazione". Deve restituire None:
    zero pagine analizzate non e' un sito perfetto, e' una misura che
    non c'e' stata.
    """
    urls = ["https://x/1", "https://x/2"]
    spia = _playwright_finto(monkeypatch, falliscono=urls)
    assert mars_wcag.run_axe(urls) is None
    assert spia.visitate == urls, "le pagine devono essere state tentate"


def test_run_axe_conta_le_pagine_riuscite(monkeypatch):
    """Il conteggio e' il dato che mancava: senza, un fallimento
    parziale era indistinguibile da una scansione completa."""
    urls = ["https://x/1", "https://x/2", "https://x/3"]
    _playwright_finto(monkeypatch, falliscono=["https://x/2"])
    violazioni, analizzate = mars_wcag.run_axe(urls)
    assert analizzate == 2
    assert len(violazioni) == 2      # una per pagina riuscita

    _playwright_finto(monkeypatch)
    assert mars_wcag.run_axe(urls)[1] == 3


def test_wcag_alt_vuoto_e_marcatura_corretta(contesto):
    """R26: `alt=""` e' la tecnica H67, non una violazione 1.1.1.

    Il filtro `not i.get("alt")` contava anche l'immagine decorativa
    marcata correttamente, penalizzando proprio chi aveva fatto la cosa
    giusta. Il crawler la distinzione `None`/`""` la conserva: era il
    modulo a buttarla via.
    """
    p = pagina(html='<html lang="it"><head><title>t</title></head><body>'
                    '<img src="a.png" alt="">'            # H67: corretta
                    '<img src="b.png" alt="Descritta">'   # corretta
                    '<img src="c.png" aria-label="Con aria">'
                    '<img src="d.png">'                   # unica violazione
                    '</body></html>')
    assert [i["alt"] for i in p["images"]] == ["", "Descritta", None, None], \
        "il crawler deve distinguere alt assente da alt vuoto"

    rilievi = [mars_wcag._issue_statica(f) for f in
               mars_wcag.controlli_statici({"https://esempio.test/": p})]
    alternativi = [r for r in rilievi if "[1.1.1]" in r]
    assert alternativi == ["[1.1.1] 1/4 immagini prive di testo alternativo"]


def test_wcag_non_riparsa_l_html(contesto):
    """R26: i controlli statici leggono la struttura estratta dal
    crawler, non l'HTML.

    La prova e' costruita perche' non possa passare per caso: l'HTML
    della pagina e' vuoto, quindi ogni rilievo che compare puo' venire
    solo dai dati strutturali. Un ritorno al parse li azzererebbe
    tutti — che e' anche il guasto silenzioso da cui questa correzione
    protegge, se un giorno il crawler smettesse di conservare l'HTML.
    """
    p = pagina(html='<html lang="it"><head><title>t</title></head>'
                    '<body><p>x</p></body></html>')
    p["html"] = ""
    p["heading_levels"] = [1, 2, 5]
    p["form_fields"] = [{"type": "text", "labelled": False}]
    p["tables"] = [{"has_th": False, "role": ""}]
    p["links"] = [{"text": "clicca qui", "aria-label": None}]
    p["tabindex"] = ["4"]

    rilievi = " | ".join(mars_wcag._issue_statica(f) for f in
                         mars_wcag.controlli_statici({"https://x/": p}))
    assert "1 salti" in rilievi
    assert "1 campi di modulo senza etichetta" in rilievi
    assert "1 tabelle dati senza intestazioni" in rilievi
    assert "1 link con testo generico" in rilievi
    assert "1 elementi con tabindex positivo" in rilievi


def test_wcag_rispetta_il_ritardo_chiesto_dal_sito(contesto, monkeypatch):
    """R26: `context.get("delay")` era sempre None, quindi il ramo
    `if delay:` di run_axe non veniva mai preso e Chromium apriva le
    pagine di fila anche su un sito che aveva chiesto una pausa.

    Il ritardo deve attraversare tutti e tre i passaggi: contesto ->
    audit() -> run_axe -> browser.
    """
    contesto["pages"] = {"https://x/%d" % i: pagina() for i in range(3)}
    contesto["delay"] = 7.0
    spia = _playwright_finto(monkeypatch)
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)

    mars_wcag.audit(contesto)

    assert len(spia.visitate) == 3
    assert spia.pause == [7000, 7000, 7000], \
        "il ritardo deve arrivare fino al browser, in millisecondi"


def test_wcag_senza_browser_usa_il_ripiego_statico(contesto):
    """Il ramo statico va fissato, non lasciato all'ambiente.

    Prima nessun test diceva QUALE ramo di audit() venisse eseguito:
    su una macchina con Playwright girava axe, su una senza il
    markup, e il difetto R20 passava verde in entrambi i casi.
    La fixture rende playwright non importabile, quindi qui siamo
    certi di stare sul ripiego.
    """
    assert mars_wcag.axe_disponibile() is False
    esito = mars_wcag.audit(contesto)
    assert esito["tool"] == "markup"
    assert esito["status"] == "surface"
    assert "parziale" in esito["wcag_level"]


def test_wcag_ramo_axe_con_dati_iniettati(contesto, monkeypatch):
    """Il ramo axe, senza avviare un browser.

    Zero violazioni su pagine DAVVERO analizzate sono un 100/100
    legittimo: e' il caso che va distinto da quello di R20.
    """
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe", lambda urls, delay=0.0: ([], 1))
    esito = mars_wcag.audit(contesto)
    assert esito["tool"] == "axe-core"
    assert esito["score"] == 100
    assert esito["pages_tested"] == 1
    assert esito["complete"] is True


def test_wcag_axe_fallita_non_fabbrica_un_cento(contesto, monkeypatch):
    """Regressione R20: zero pagine analizzate diventavano 100/100.

    run_axe inghiottiva i fallimenti per-URL senza contarli, quindi con
    tutte le pagine irraggiungibili restituiva una lista VUOTA — che
    audit() leggeva come "nessuna violazione" e pubblicava come misura
    axe-core riuscita. Un sito mai caricato non e' un sito perfetto.
    """
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe", lambda urls, delay=0.0: None)
    esito = mars_wcag.audit(contesto)
    assert esito["tool"] == "markup", \
        "senza pagine analizzate non si puo' dichiarare axe-core"
    assert esito["status"] == "surface"


def test_wcag_axe_parziale_e_dichiarata(contesto, monkeypatch):
    """Una scansione parziale vale piu' di niente, ma spacciarla per
    completa no: e' la regola gia' applicata a ZAP in C9."""
    pagine = {"https://x/%d" % i: pagina() for i in range(5)}
    contesto["pages"] = pagine
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe",
                        lambda urls, delay=0.0: ([_viol()], 2))
    esito = mars_wcag.audit(contesto)
    assert esito["pages_tested"] == 2, "le pagine ESAMINATE, non le tentate"
    assert esito["pages_attempted"] == 5
    assert esito["complete"] is False
    assert "parziali" in esito["issues"][0]


def test_wcag_axe_parziale_pesa_sulle_pagine_viste(contesto, monkeypatch):
    """La diffusione si misura su cio' che axe ha VISTO.

    Una regola presente su tutte le pagine esaminate e' diffusa al
    100%, anche se il campione tentato era piu' grande: calcolarla
    sulle pagine tentate la farebbe sembrare piu' rara di quanto e',
    e il punteggio ne uscirebbe piu' generoso del dovuto.
    """
    contesto["pages"] = {"https://x/%d" % i: pagina() for i in range(5)}
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe",
                        lambda urls, delay=0.0: ([_viol(), _viol()], 2))
    parziale = mars_wcag.audit(contesto)
    completa = mars_wcag.score_from_violations([_viol(), _viol()], 2)
    assert parziale["score"] == completa["score"], \
        "due pagine viste su cinque tentate pesano come due pagine viste"


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


# ----------------------------------------------------------------------
# mars_seo: gli stessi controlli che mostra Lighthouse
# ----------------------------------------------------------------------

# Le forme di questi dati sono state OSSERVATE su referti Lighthouse
# 13.4.1 reali, non dedotte: is-crawlable porta una "source" testuale,
# image-alt un "node" del DOM, meta-description nessun dettaglio, e
# structured-data e' sempre manuale.
def _lhr(punteggio=0.42):
    return {
        "lighthouseVersion": "13.4.1",
        "finalDisplayedUrl": "https://esempio.test/",
        "configSettings": {"formFactor": "mobile"},
        "categories": {"seo": {"score": punteggio, "auditRefs": [
            {"id": "is-crawlable"}, {"id": "document-title"},
            {"id": "meta-description"}, {"id": "image-alt"},
            {"id": "http-status-code"}, {"id": "structured-data"},
        ]}},
        "audits": {
            "is-crawlable": {
                "title": "L'indicizzazione della pagina è bloccata",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table",
                            "items": [{"source": "X-Robots-Tag: noindex"}]}},
            "document-title": {
                "title": "Il documento non ha un elemento `<title>`",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table", "items": [
                    {"node": {"type": "node", "selector": "html",
                              "boundingRect": {"top": 0}}}]}},
            "meta-description": {
                "title": "Il documento non ha una meta descrizione",
                "score": 0, "scoreDisplayMode": "binary"},
            "image-alt": {
                "title": "Gli elementi immagine non hanno attributi `[alt]`",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table", "items": [
                    {"node": {"selector": "body > img"}},
                    {"node": {"selector": "body > img"}}]}},
            "http-status-code": {
                "title": "La pagina ha un codice di stato HTTP valido",
                "score": 1, "scoreDisplayMode": "binary"},
            "structured-data": {
                "title": "Dati strutturati validi",
                "score": None, "scoreDisplayMode": "manual"},
        },
    }


def test_seo_estrae_tutti_i_controlli_non_solo_i_falliti():
    """Il referto conteneva il solo punteggio complessivo.

    42/100 non dice QUALE controllo sia fallito, ed elencare i soli
    fallimenti non direbbe che cosa sia stato guardato: un punteggio
    pieno resterebbe indistinguibile da un controllo mai eseguito.
    """
    controlli = mars_seo.estrai_audit(_lhr())
    assert [c["id"] for c in controlli] == [
        "is-crawlable", "document-title", "meta-description", "image-alt",
        "http-status-code", "structured-data"]
    per_id = {c["id"]: c for c in controlli}
    assert per_id["http-status-code"]["passed"] is True
    assert per_id["is-crawlable"]["passed"] is False
    assert per_id["structured-data"]["manual"] is True
    assert per_id["structured-data"]["passed"] is False


@pytest.mark.parametrize("audit_id, atteso", [
    ("is-crawlable", ["X-Robots-Tag: noindex"]),   # dettaglio testuale
    ("document-title", ["html"]),                  # nodo del DOM
    ("image-alt", ["body > img", "body > img"]),
    ("meta-description", []),                      # nessun dettaglio
])
def test_seo_riporta_gli_elementi_incriminati(audit_id, atteso):
    """Lighthouse dice anche DOVE: il selettore o la sorgente. Senza,
    "immagini senza alt" non basta a trovarle."""
    per_id = {c["id"]: c for c in mars_seo.estrai_audit(_lhr())}
    assert per_id[audit_id]["items"] == atteso


def test_seo_un_manuale_non_e_mai_un_superato():
    """Superato, fallito e manuale devono partizionare l'elenco.

    Sui referti reali un audit manuale ha sempre score None, quindi la
    guardia non cambia nulla oggi: fissa l'intenzione se Lighthouse
    cambiasse forma, e impedisce che i conteggi si sovrappongano.
    """
    lhr = _lhr()
    lhr["audits"]["structured-data"]["score"] = 1     # forma non osservata
    per_id = {c["id"]: c for c in mars_seo.estrai_audit(lhr)}
    assert per_id["structured-data"]["manual"] is True
    assert per_id["structured-data"]["passed"] is False
    esito = mars_seo.riassumi(lhr)
    assert esito["passed"] + esito["failed"] + esito["manual"] == 6


def test_seo_riassume_con_conteggi_e_strumento():
    esito = mars_seo.riassumi(_lhr())
    assert esito["score"] == 42.0
    assert (esito["passed"], esito["failed"], esito["manual"]) == (1, 4, 1)
    assert esito["tool"] == "Lighthouse 13.4.1"
    # Un referto mobile e uno desktop non sono confrontabili.
    assert esito["form_factor"] == "mobile"
    assert esito["audited_url"] == "https://esempio.test/"


def test_seo_issues_contengono_i_falliti_con_il_dettaglio():
    issues = mars_seo.riassumi(_lhr())["issues"]
    assert any("X-Robots-Tag: noindex" in i for i in issues)
    assert any("da verificare a mano" in i for i in issues)
    assert not any("codice di stato HTTP valido" in i for i in issues), \
        "un controllo superato non e' un rilievo"


def test_seo_chiede_i_titoli_in_italiano(monkeypatch):
    """I titoli li traduce Lighthouse, non noi: cosi' restano allineati
    allo strumento invece di essere una traduzione che invecchia."""
    visti = {}

    def finto_run(argomenti, **kwargs):
        visti["argv"] = argomenti
        return types.SimpleNamespace(stdout=json.dumps(_lhr()))

    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome: "/usr/bin/lighthouse")
    monkeypatch.setattr(mars_seo.subprocess, "run", finto_run)
    esito = mars_seo.audit({"url": "https://esempio.test/"})
    assert "--locale=it" in visti["argv"]
    assert esito["score"] == 42.0
    # Regressione R3: l'URL resta un argomento, mai una stringa di shell
    assert visti["argv"][1] == "https://esempio.test/"


def test_seo_score_null_non_e_un_errore_di_lighthouse(monkeypatch):
    """Regressione R22: lo schema LHR ammette score null.

    Il run riesce, il JSON e' valido, ma la categoria non e'
    calcolabile: None * 100 sollevava TypeError, che non era nella
    tupla dell'except e propagava fuori da audit() — 500 su
    /audit/seo. E la diagnosi giusta non e' "Lighthouse non riuscito"
    ma "non ha calcolato la categoria" (lezione di R6).
    """
    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome: "/usr/bin/lighthouse")
    monkeypatch.setattr(
        mars_seo.subprocess, "run",
        lambda *a, **k: types.SimpleNamespace(
            stdout='{"categories":{"seo":{"score":null}}}'))
    esito = mars_seo.audit({"url": "https://x/"})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert "non ha calcolato" in esito["issues"][0]


def test_seo_score_valido_resta_valido(monkeypatch):
    """La guardia non deve mangiarsi i punteggi buoni, zero incluso."""
    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome: "/usr/bin/lighthouse")
    for grezzo, atteso in ((0.92, 92.0), (0, 0.0), (1, 100.0)):
        monkeypatch.setattr(
            mars_seo.subprocess, "run",
            lambda *a, _g=grezzo, **k: types.SimpleNamespace(
                stdout=json.dumps({"categories": {"seo": {"score": _g}}})))
        assert mars_seo.audit({"url": "https://x/"})["score"] == atteso


# ----------------------------------------------------------------------
# Query che non trovano nulla (R23)
# ----------------------------------------------------------------------

CHUNK_R23 = [
    {"url": "https://x/", "heading": "Chi siamo",
     "text": "Siamo una organizzazione che opera nella ricerca applicata."},
    {"url": "https://x/", "heading": "Contatti",
     "text": "Scrivete al nostro indirizzo oppure telefonate in ufficio."},
]


def _ctx_r23(queries):
    return {"url": "https://x/", "chunks": CHUNK_R23, "queries": queries,
            "pages": {"https://x/": {"lang": "it", "headings": [],
                                     "html": ""}},
            "embeddings_model": "none", "force_proxy": True,
            "credentials": {}, "market": "global"}


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_query_senza_riscontro_e_dichiarata(modulo):
    """Regressione R23: l'ordine di scansione spacciato per classifica.

    Quando nessun termine trova riscontro i punteggi sono tutti zero e
    sorted() restituisce l'ordine naturale dei chunk. Non e' una
    classifica: e' l'ordine in cui sono stati scansionati, e dichiarare
    un top_chunk su quella base e' inventare un vincitore.
    """
    esito = modulo.audit(_ctx_r23(["zzzzz qqqqq wwwww"]))
    voce = esito["per_query"][0]
    assert voce["matched"] is False
    assert voce["top_chunk"] is None


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_query_con_riscontro_resta_una_classifica(modulo):
    """La guardia non deve mangiarsi le query che funzionano."""
    esito = modulo.audit(_ctx_r23(["organizzazione ricerca"]))
    voce = esito["per_query"][0]
    assert voce["matched"] is True
    assert voce["top_chunk"] is not None


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_query_a_vuoto_esclusa_dal_rango_aggregato(modulo):
    """Fondere un ordine di scansione con una classifica vera sposta il
    risultato senza dire nulla sul sito."""
    solo_vuote = modulo.audit(_ctx_r23(["zzzzz qqqqq", "kkkkk jjjjj"]))
    assert solo_vuote["rank"] == [], \
        "senza una sola query utile non c'e' rango aggregato"
    misto = modulo.audit(_ctx_r23(["zzzzz qqqqq", "organizzazione ricerca"]))
    assert misto["rank"], "la query utile deve comunque produrre un rango"


def test_citability_non_prende_cento_dal_nulla():
    """Regressione R23: il segnale "Recuperabilità ibrida" leggeva 100.

    Due ordini di scansione identici davano consenso 3/3, cioe' il
    massimo, proprio dove non c'era un solo riscontro — e quel numero
    pesa 2 o 3 su 3 per ogni assistente nel profilo di citabilita'.
    """
    ctx = _ctx_r23(["zzzzz qqqqq wwwww"])
    ctx["results"] = {"mars_lexical": mars_lexical.audit(ctx),
                      "mars_semantic": mars_semantic.audit(ctx),
                      "mars_tech": {"score": 80}}
    segnali = mars_citability.audit(ctx)["signals"]
    assert segnali["Recuperabilità ibrida (consenso RRF)"] is None, \
        "non misurato, non cento"


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
    """Il titolo del CHUNK conta; quelli delle altre sezioni no.

    Il test verificava che l'heading di un'altra sezione della stessa
    pagina accendesse il segnale: era il difetto R19, non la funzione
    che si voleva. Ora la domanda deve stare nel titolo di questo
    passaggio.
    """
    proprio = mars_semantic.question_signals(
        "Il prodotto si installa in pochi passi.", "Come si installa?", "it")
    assert "titolo interrogativo" in proprio

    altrui = mars_semantic.question_signals(
        "Il prodotto si installa in pochi passi.", "Requisiti tecnici", "it")
    assert "titolo interrogativo" not in altrui


def test_semantic_il_titolo_del_chunk_conta_come_testo():
    """Scelta di R9 da non perdere: l'heading FA PARTE del passaggio.

    "Come funziona?" come titolo vale quanto la stessa frase nel corpo,
    quindi accende anche i segnali testuali — non solo quello sul
    titolo. Senza, un chunk la cui unica domanda sta nel titolo
    perderebbe due segnali su tre.
    """
    segnali = mars_semantic.question_signals(
        "Il servizio si attiva subito dopo la registrazione.",
        "Come funziona?", "it")
    assert "punto interrogativo" in segnali
    assert "interrogativo a inizio frase" in segnali


CORPO_LUNGO = (
    "Siamo un'azienda che progetta e gestisce infrastrutture informatiche "
    "per imprese e pubbliche amministrazioni, con un data center di "
    "proprieta' in Italia e un gruppo di tecnici che segue i clienti dalla "
    "progettazione all'esercizio quotidiano dei sistemi affidati.")


@pytest.mark.parametrize("titolo", [
    "Chi siamo", "Dove siamo", "Come raggiungerci", "Cosa facciamo",
    "Quali servizi offriamo", "Come funziona", "Perche' sceglierci",
    "Quando siamo aperti", "Quanto costa il servizio",
    "How it works", "What we do", "Who we are", "Why choose us",
    # I due punti sono un inizio frase per _INIZIO_FRASE, quindi questa
    # classe si accendeva a META' titolo.
    "AI Act: cosa scatta davvero il 2 agosto",
    "Il backup non basta: perche' c'e' chi riparte in ore",
    "Come funziona: le tecnologie integrate",
])
def test_semantic_un_titolo_di_sezione_non_e_una_domanda(titolo):
    """Regressione R34: bastava che il titolo aprisse con un
    interrogativo, e cadeva una classe intera di intestazioni standard.
    "Chi siamo" sta su quasi ogni sito italiano.

    L'asserzione e' su TUTTI i segnali, non sul solo "titolo
    interrogativo", e non e' un dettaglio: il rapporto conta un chunk
    se un qualunque segnale e' acceso, quindi restringere il solo
    segnale sul titolo avrebbe lasciato "Chi siamo" acceso lo stesso
    attraverso "interrogativo a inizio frase", che leggeva titolo e
    testo uniti. Misurato prima di correggere: answer_shaped_ratio
    sarebbe rimasto identico. Un test sul solo titolo sarebbe passato
    su una correzione che non correggeva nulla.
    """
    assert mars_semantic.question_signals(
        CORPO_LUNGO, heading=titolo, lingua="it") == []
    assert mars_semantic.question_signals(
        CORPO_LUNGO, heading=titolo, lingua="en") == []


@pytest.mark.parametrize("titolo", [
    "Come funziona il servizio?", "Quanto costa?",
    "Posso disdire in qualsiasi momento?", "What is included?",
])
def test_semantic_un_titolo_punteggiato_e_una_domanda(titolo):
    """L'altra meta': la regola non deve spegnere le domande vere."""
    segnali = mars_semantic.question_signals(
        CORPO_LUNGO, heading=titolo, lingua="it")
    assert "titolo interrogativo" in segnali


def test_semantic_la_domanda_nel_corpo_resta_riconosciuta():
    """La regola vale per il TITOLO, non per il corpo: una FAQ scritta
    senza '?' nel titolo resta riconoscibile da cio' che dice."""
    segnali = mars_semantic.question_signals(
        "Come si attiva il servizio? Basta una richiesta. " + CORPO_LUNGO,
        heading="Attivazione", lingua="it")
    assert "punto interrogativo" in segnali
    assert "interrogativo a inizio frase" in segnali
    assert "titolo interrogativo" not in segnali


def test_semantic_i_due_punti_aprono_una_frase_nel_CORPO():
    """I due punti restano un inizio di frase, ma solo dove servono.

    Erano la meta' non ovvia di R34: _INIZIO_FRASE li tratta come
    confine, quindi "AI Act: cosa scatta davvero" si accendeva a META'
    titolo. Ora il titolo entra nel passaggio solo se punteggiato come
    domanda, e il confine sui due punti resta a fare il suo lavoro nel
    corpo, dove una frase dopo i due punti e' una frase davvero."""
    assert mars_semantic.question_signals(
        "Un dubbio ricorrente: come si attiva il servizio senza un "
        "tecnico in sede. " + CORPO_LUNGO, lingua="it")
    # ...e non deve accendersi da un titolo che ha solo la forma.
    assert mars_semantic.question_signals(
        CORPO_LUNGO, heading="AI Act: cosa scatta davvero", lingua="it") == []


def test_semantic_le_etichette_di_sezione_non_gonfiano_il_rapporto():
    """R34 end-to-end, sul dato che il referto pubblica.

    Tre sezioni: due etichette standard e una domanda vera. Il rapporto
    onesto e' 1/3; prima erano 3/3, perche' "Chi siamo" e "Come
    funziona" aprono con un interrogativo."""
    lungo = (CORPO_LUNGO + " ") * 3
    html = ("<html lang='it'><body>"
            "<h2>Chi siamo</h2><p>%s</p>"
            "<h2>Come funziona</h2><p>%s</p>"
            "<h2>Quanto costa il servizio?</h2><p>%s</p>"
            "</body></html>" % (lungo, lungo, lungo))
    p = pagina(html=html, url="https://x/")
    esito = mars_semantic.audit({
        "pages": {"https://x/": p}, "chunks": p["chunks"], "queries": [],
        "embeddings_model": "none", "force_proxy": True, "credentials": {}})
    assert esito["n_chunks"] == 3
    assert esito["answer_shaped_ratio"] == pytest.approx(1 / 3)
    assert esito["answer_shaped_signals"].get("titolo interrogativo") == 1


def test_semantic_faqpage_e_un_segnale_di_pagina():
    """FAQPage descrive la PAGINA, non il singolo passaggio."""
    pagina_faq = {"html": '<script type="application/ld+json">'
                          '{"@type":"FAQPage"}</script>'}
    assert mars_semantic.page_signals(pagina_faq) == ["FAQPage JSON-LD"]
    assert mars_semantic.page_signals({"html": "<html></html>"}) == []
    assert mars_semantic.page_signals(None) == []


def _pagina_con_una_sola_domanda():
    # Oltre MIN_PAROLE, altrimenti nessun chunk conta e il test
    # misurerebbe la soglia invece del difetto.
    lungo = ("Il gruppo di lavoro accompagna enti pubblici e imprese private "
             "nei percorsi di innovazione da oltre venti anni, con progetti "
             "che spaziano dalla formazione tecnica alla consulenza "
             "organizzativa fino al supporto continuativo sul campo, sempre "
             "con la stessa attenzione ai risultati verificabili e "
             "documentati. ")
    html = ("<html lang='it'><body>"
            "<h2>I nostri servizi</h2><p>%s</p>"
            "<h2>La nostra storia</h2><p>%s</p>"
            "<h2>Come funziona il servizio?</h2><p>%s</p>"
            "</body></html>" % (lungo, lungo, lungo))
    return pagina(html=html, url="https://x/")


def test_semantic_una_domanda_non_marca_tutta_la_pagina():
    """Regressione R19: i segnali di pagina gonfiavano il rapporto.

    Il "titolo interrogativo" si accendeva se una QUALUNQUE
    intestazione della pagina era una domanda, quindi una sola FAQ
    portava answer_shaped_ratio al 100% su un sito generico — e quel
    numero alimenta il segnale "Contenuto in forma di risposta" di C1.
    """
    p = _pagina_con_una_sola_domanda()
    esito = mars_semantic.audit({
        "pages": {"https://x/": p}, "chunks": p["chunks"], "queries": [],
        "embeddings_model": "none", "force_proxy": True, "credentials": {}})
    assert esito["n_chunks"] == 3
    assert esito["answer_shaped_ratio"] == pytest.approx(1 / 3), \
        "solo la sezione che E' una domanda deve contare"
    assert esito["answer_shaped_signals"].get("titolo interrogativo") == 1


def test_semantic_faqpage_non_gonfia_il_rapporto():
    """Regressione R19: bastava un FAQPage nell'HTML perche' OGNI
    chunk della pagina risultasse in forma di risposta."""
    p = _pagina_con_una_sola_domanda()
    p["html"] += ('<script type="application/ld+json">{"@type":"FAQPage"}'
                  '</script>')
    esito = mars_semantic.audit({
        "pages": {"https://x/": p}, "chunks": p["chunks"], "queries": [],
        "embeddings_model": "none", "force_proxy": True, "credentials": {}})
    assert esito["answer_shaped_ratio"] == pytest.approx(1 / 3)
    # il fatto non si perde: viene riportato dove gli compete
    assert esito["page_signals"] == {"FAQPage JSON-LD": 1}
    assert esito["n_pages"] == 1
    assert "FAQPage JSON-LD" not in esito["answer_shaped_signals"]


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


class _ZapFinto:
    """Daemon ZAP finto che REGISTRA gli ordini ricevuti.

    Registrare e' il punto: R27 non riguarda cosa MARS restituisce, ma
    che cosa MARS dice al daemon. Un finto che accettasse tutto in
    silenzio non potrebbe rivelare una fermata mai chiesta.
    """

    def __init__(self, spider_finisce=True, ascan_finisce=True,
                 stop_solleva=None, lentezza=0.0):
        self.chiamate = []
        self.spider_finisce = spider_finisce
        self.ascan_finisce = ascan_finisce
        self.stop_solleva = stop_solleva
        self.lentezza = lentezza

    def spider_scan(self, url):
        self.chiamate.append(("spider_scan", url))
        return "11"

    def spider_status(self, sid):
        self.chiamate.append(("spider_status", sid))
        if self.lentezza:
            time.sleep(self.lentezza)
        return 100 if self.spider_finisce else 40

    def spider_stop(self, sid):
        self.chiamate.append(("spider_stop", sid))
        if self.stop_solleva:
            raise self.stop_solleva

    def ascan_scan(self, url):
        self.chiamate.append(("ascan_scan", url))
        return "22"

    def ascan_status(self, sid):
        self.chiamate.append(("ascan_status", sid))
        return 100 if self.ascan_finisce else 15

    def ascan_stop(self, sid):
        self.chiamate.append(("ascan_stop", sid))
        if self.stop_solleva:
            raise self.stop_solleva

    def alerts(self, baseurl):
        self.chiamate.append(("alerts", baseurl))
        return []

    def fatte(self, nome):
        return [c for c in self.chiamate if c[0] == nome]


@pytest.fixture
def zap_veloce(monkeypatch):
    """Timeout minuscolo: la scadenza deve scattare dentro il test."""
    monkeypatch.setattr(mars_wapt, "ZAP_TIMEOUT_SCAN", 0.6)
    monkeypatch.setattr(mars_wapt, "ZAP_ATTESA", 0.1)


def test_wapt_il_timeout_ferma_lo_spider(zap_veloce):
    """Regressione R27: allo scadere del timeout MARS smetteva di
    ASPETTARE e il daemon proseguiva.

    Verificato end-to-end su ZAP 2.17.0 prima di scrivere questo test:
    quattro secondi dopo il timeout il daemon dichiarava la scansione
    RUNNING al 35%, mentre il referto la dava per interrotta.
    """
    c = _ZapFinto(spider_finisce=False)
    alerts, completa, fermate = mars_wapt.run_zap("https://x/", c)
    assert completa is False
    assert fermate is True
    assert c.fatte("spider_stop") == [("spider_stop", "11")], \
        "lo spider scaduto va fermato, con il suo scanId"


def test_wapt_il_timeout_ferma_lactive_scan(zap_veloce):
    """L'active scan invia payload d'attacco: abbandonarlo in corso e'
    la forma peggiore del difetto."""
    c = _ZapFinto(ascan_finisce=False)
    alerts, completa, fermate = mars_wapt.run_zap("https://x/", c, active=True)
    assert completa is False and fermate is True
    assert c.fatte("ascan_stop") == [("ascan_stop", "22")]
    # Lo spider era finito: non va fermato.
    assert not c.fatte("spider_stop")


def test_wapt_non_avvia_un_attacco_che_non_puo_sorvegliare(zap_veloce):
    """La scadenza e' UNA per spider piu' active scan e non si rinnova.

    Se lo spider la esaurisce, prima restava comunque un
    ascan/action/scan — payload d'attacco — seguito da zero controlli
    di avanzamento e da nessuna fermata: un attacco lanciato e
    abbandonato. Meglio non avviarlo.
    """
    c = _ZapFinto(spider_finisce=True, lentezza=0.8)   # consuma il budget
    alerts, completa, fermate = mars_wapt.run_zap("https://x/", c, active=True)
    assert not c.fatte("ascan_scan"), \
        "nessun payload d'attacco senza tempo per sorvegliarlo"
    assert completa is False, "e l'audit deve dichiararsi incompleto"


def test_wapt_una_scansione_gia_conclusa_non_e_un_fallimento(zap_veloce):
    """La corsa fra l'ultimo controllo e la fermata.

    Fra i due passano fino a ZAP_ATTESA secondi, e la scansione puo'
    concludersi da sola proprio li'. ZAP risponde allora 400
    does_not_exist. Verificato sul daemon vero. Trattarlo come guasto
    farebbe dichiarare al referto che una scansione conclusa sta
    ancora girando.
    """
    risposta = requests.Response()
    risposta.status_code = 400
    risposta._content = b'{"code":"does_not_exist","message":"Non esiste"}'
    c = _ZapFinto(spider_finisce=False,
                  stop_solleva=requests.HTTPError(response=risposta))
    alerts, completa, fermate = mars_wapt.run_zap("https://x/", c)
    assert completa is False
    assert fermate is True, "non c'e' piu' nulla da fermare: e' l'esito buono"


@pytest.mark.parametrize("stato, corpo", [
    (500, b'{"code":"internal_error","message":"boom"}'),
    (400, b'{"code":"illegal_parameter","message":"scanId"}'),
    (400, b'non e\' nemmeno JSON'),
])
def test_wapt_solo_does_not_exist_vale_come_fermata(zap_veloce, stato, corpo):
    """`does_not_exist` e' l'unico errore che significa "non sta
    girando". Ogni altro guasto lascia la scansione in dubbio, e il
    dubbio va dichiarato, non risolto a favore nostro."""
    risposta = requests.Response()
    risposta.status_code = stato
    risposta._content = corpo
    c = _ZapFinto(spider_finisce=False,
                  stop_solleva=requests.HTTPError(response=risposta))
    _, completa, fermate = mars_wapt.run_zap("https://x/", c)
    assert completa is False
    assert fermate is False, "un errore diverso non prova che si sia fermata"


def test_wapt_un_daemon_muto_non_puo_dirsi_fermato(zap_veloce):
    """L'opposto: se il daemon non risponde, la scansione puo' benissimo
    proseguire, e il referto non deve dichiararla interrotta."""
    c = _ZapFinto(spider_finisce=False,
                  stop_solleva=requests.ConnectionError("daemon muto"))
    alerts, completa, fermate = mars_wapt.run_zap("https://x/", c)
    assert completa is False and fermate is False


def test_wapt_il_referto_distingue_fermata_da_abbandonata(zap_veloce,
                                                          monkeypatch):
    """R27 chiede che il messaggio corrisponda al fatto."""
    def esito(fermate):
        monkeypatch.setattr(mars_wapt, "connect_zap",
                            lambda credentials=None: _ZapFinto())
        monkeypatch.setattr(mars_wapt, "run_zap",
                            lambda url, client=None, active=False:
                            ([], False, fermate))
        return mars_wapt.audit({"url": "https://x/",
                                "owner_declaration": False})

    fermata = esito(True)
    abbandonata = esito(False)
    assert fermata["stopped"] is True
    assert abbandonata["stopped"] is False
    assert "fermata" in fermata["issues"][0]
    assert "NON fermata" in abbandonata["issues"][0]
    assert "prosegue nel daemon" in abbandonata["issues"][0]


# ----------------------------------------------------------------------
# mars_wapt — i rilievi come dato (U1.6)
# ----------------------------------------------------------------------
#
# Prima di U1.6 quest'area aveva una rete su R27 (le fermate) e su C9
# (il raggruppamento per regola), ma NIENTE su cio' che U1.6 tocca:
# `audit_headers` non aveva un solo test proprio, il ramo "surface" non
# era mai stato raggiunto, e `audit()` non aveva mai visto un alert non
# vuoto. Questi test sono quella rete, non solo la verifica dei
# findings.

def _alert(**kw) -> dict:
    """Un alert come lo restituisce `core/view/alerts` di ZAP.

    I default sono quelli veri: `pluginId` sempre presente e stringa,
    `risk` uno dei quattro `MSG_RISK`, `reference` UNA stringa con piu'
    URL separati da a-capo. Un valore messo a None sparisce dal dict,
    che e' come si prova il caso "campo assente".
    """
    base = {"pluginId": "10038", "alertRef": "10038-1",
            "alert": "CSP Header Not Set", "name": "CSP Header Not Set",
            "risk": "Medium", "url": "https://x/",
            "solution": "Ensure the header is set.",
            "reference": "https://a/\nhttps://b/"}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


class _Risposta:
    """Risposta HTTP finta, FEDELE su cio' che il modulo usa.

    `headers` e' una `CaseInsensitiveDict`, non un `dict`: e' cio' che
    `requests` restituisce, e `audit_headers` fa `header not in
    resp.headers`. Con un dict semplice il test verificherebbe un
    confronto che il codice reale non esegue — la stessa lezione
    dell'adattatore finto del Crawler in tests/test_core.py.
    """

    def __init__(self, status_code: int = 200, headers=()):
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(dict(headers))


def _risposte(monkeypatch, *sequenza):
    """Monta un copione su requests.head e requests.get.

    La fixture `niente_rete` vieta la rete ma non fornisce risposte:
    per esercitare il ramo "surface", mai raggiunto prima, serve un
    finto locale.
    """
    coda = list(sequenza)

    def servi(url, **kw):
        esito = coda.pop(0)
        if isinstance(esito, Exception):
            raise esito
        return esito

    monkeypatch.setattr(mars_wapt.requests, "head", servi)
    monkeypatch.setattr(mars_wapt.requests, "get", servi)


def _audit_zap(monkeypatch, alerts, completa=True, fermate=True,
               active=False):
    """`audit()` sul ramo ZAP, con alert veri.

    Si sostituisce `run_zap` intero e non il solo client: per ottenere
    `completa=False` servirebbe far scadere `_attendi`, che aspetta
    ZAP_TIMEOUT_SCAN secondi — quindici minuti dentro un test.
    """
    monkeypatch.setattr(mars_wapt, "connect_zap",
                        lambda credentials=None: object())
    monkeypatch.setattr(mars_wapt, "run_zap",
                        lambda url, client=None, active=False:
                        (alerts, completa, fermate))
    return mars_wapt.audit({"url": "https://x/",
                            "owner_declaration": active})


def test_wapt_ogni_rilievo_zap_ha_una_chiave_stabile():
    """Tre segmenti e il prefisso d'area: e' cio' su cui poggeranno il
    confronto fra due esecuzioni e i cataloghi di traduzione."""
    esito = mars_wapt.score_from_alerts([
        _alert(pluginId="10038"),
        _alert(pluginId="40012", alert="XSS", name="XSS", risk="High"),
        # Gli alert manuali, da script e da alert/action/addAlert hanno
        # pluginId "-1": e' dato reale, non un caso di laboratorio.
        _alert(pluginId="-1", alert="Manuale", name="Manuale"),
    ])
    chiavi = [f["key"] for f in esito["findings"]]
    assert len(chiavi) == 3
    for chiave in chiavi:
        parti = chiave.split(".")
        assert parti[0] == AREA_PREFIX["mars_wapt"]
        assert len(parti) == 3, "profondita' fissa a tre segmenti"
    assert "sec.zap.10038" in chiavi


def test_wapt_la_chiave_zap_e_sanificata_ma_collide():
    """Un id di ZAP e' dato esterno: passa da `chiave_esterna`, che pero'
    NON e' iniettiva. Il fatto e' documentato, non nascosto: `-1` e `1`
    danno la stessa chiave, e l'unico dato fedele e' params["rule"]."""
    esito = mars_wapt.score_from_alerts(
        [_alert(pluginId=None, alertRef=None,
                alert="Cross Site Scripting (Reflected)",
                name="Cross Site Scripting (Reflected)")])
    finding = esito["findings"][0]
    assert finding["key"] == "sec.zap.cross_site_scripting__reflected"
    assert finding["params"]["rule"] == "Cross Site Scripting (Reflected)"
    # E la collisione, dichiarata:
    assert chiave_esterna("-1") == chiave_esterna("1")


def test_wapt_la_chiave_dichiara_da_quale_campo_nasce():
    """La chiave e' stabile SOLO quando nasce dal pluginId: un nome
    viene dai Messages.properties di ZAP, cambia fra due release ed e'
    localizzato. Chi confrontera' due esecuzioni deve poterlo sapere."""
    da_plugin = mars_wapt.score_from_alerts([_alert()])
    da_nome = mars_wapt.score_from_alerts(
        [_alert(pluginId=None, alertRef=None)])
    assert da_plugin["findings"][0]["params"]["key_source"] == "pluginId"
    assert da_nome["findings"][0]["params"]["key_source"] == "name"


@pytest.mark.parametrize("rischio, severita, peso", [
    ("High", SEV_CRITICAL, 2.0),
    ("Medium", SEV_WARNING, 1.0),
    ("Low", SEV_INFO, 1.0),
    ("Informational", SEV_INFO, 1.0),
])
def test_wapt_la_gravita_arriva_dalla_scala_zap(rischio, severita, peso):
    """I quattro livelli di ZAP sulla scala canonica, con il peso che
    conserva la granularita' che le quattro severita' perdono."""
    esito = mars_wapt.score_from_alerts([_alert(risk=rischio)])
    finding = esito["findings"][0]
    assert (finding["severity"], finding["weight"]) == (severita, peso)
    assert finding["source_severity"] == "ZAP:%s" % rischio


def test_wapt_il_rischio_taciuto_non_diventa_un_giudizio_di_zap():
    """Il modulo assume "Informational" quando `risk` manca, per poter
    comunque pesare l'alert. E' una NOSTRA assunzione: scrivere
    "ZAP:Informational" attribuirebbe a ZAP un giudizio mai espresso."""
    esito = mars_wapt.score_from_alerts([_alert(risk=None)])
    finding = esito["findings"][0]
    assert finding["source_severity"] == "", "ZAP non ha parlato"
    # ...ma il livello usato per il calcolo resta auditabile:
    assert finding["params"]["risk"] == "Informational"
    assert finding["params"]["penalty"] == 0.0


def test_wapt_il_rischio_dichiarato_porta_la_parola_di_zap():
    """L'opposto del caso sopra: quando ZAP il rischio lo dichiara,
    `source_severity` deve dirlo, e con la stessa parola del prefisso
    `[ZAP:...]` della issue — altrimenti chi legge il testo e chi legge
    il dato vedono due scale."""
    esito = mars_wapt.score_from_alerts([_alert(risk="High")])
    assert esito["findings"][0]["source_severity"] == "ZAP:High"
    assert esito["issues"][0].startswith("[ZAP:High]")


def test_wapt_la_penalita_ricostruisce_il_punteggio():
    """Senza la penalita' vera nel dato, la Fase 4 non puo' calcolare
    quanto risalirebbe il punteggio se il rilievo fosse risolto."""
    alerts = [_alert(pluginId="1", risk="High"),
              _alert(pluginId="2", risk="Medium", url="https://x/b"),
              _alert(pluginId="3", risk="Low", url="https://x/c")]
    esito = mars_wapt.score_from_alerts(alerts)
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == max(0, round(100 - somma))


def test_wapt_sotto_clamp_la_penalita_non_e_un_recupero():
    """Il punteggio si ferma a zero, la somma delle penalita' no.

    Va detto, perche' la Fase 4 usera' `penalty` come RECUPERO: su
    un'area saturata prometterebbe un miglioramento che non arriva."""
    alerts = [_alert(pluginId=str(i), risk="High") for i in range(30)]
    esito = mars_wapt.score_from_alerts(alerts)
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == 0
    assert somma > 100, "la somma supera il punteggio: e' il clamp"
    assert esito["score"] == max(0, round(100 - somma))


@pytest.mark.parametrize("quanti_url, moltiplicatore", [
    (2, 1.2), (5, 1.5), (10, 2.0), (20, 2.0),
])
def test_wapt_la_penalita_tiene_conto_della_diffusione(quanti_url,
                                                       moltiplicatore):
    """La diffusione e' calcolabile solo dentro il ciclo che la applica:
    se non finisce nel dato, nessuno la ricostruisce piu'.

    I moltiplicatori sono scelti rappresentabili in binario: 1.1 non lo
    e', e l'uguaglianza esatta fallirebbe per l'ultimo bit."""
    alerts = [_alert(pluginId="1", risk="High", url="https://x/%d" % i)
              for i in range(quanti_url)]
    esito = mars_wapt.score_from_alerts(alerts)
    penalita = esito["findings"][0]["params"]["penalty"]
    assert penalita == 25 * moltiplicatore
    assert esito["findings"][0]["params"]["n"] == quanti_url


def test_wapt_un_alert_senza_url_conta_comunque_per_uno():
    """ZAP puo' emettere un alert senza URL — quelli manuali e da
    script non ne hanno.

    Il moltiplicatore di diffusione resta 1, non 0: azzerarlo
    annullerebbe la penalita' della regola e la issue direbbe
    "(0 URL)". Sfuggiva a ogni test finche' `n` non e' finito nel
    dato."""
    esito = mars_wapt.score_from_alerts([_alert(url=None)])
    assert esito["findings"][0]["params"]["n"] == 1
    assert esito["findings"][0]["params"]["urls"] == []
    assert esito["issues"][0].endswith("(1 URL)")
    assert esito["score"] == 100 - round(10 * 1.1)


def test_wapt_il_dato_non_tronca_a_cinque():
    """La vista compatta ne mostra cinque; il dato canonico li porta
    tutti — e' l'asimmetria gia' scelta in mars_wcag."""
    alerts = [_alert(pluginId=str(i), url="https://x/%d" % i)
              for i in range(8)]
    esito = mars_wapt.score_from_alerts(alerts)
    assert len(esito["issues"]) == 5
    assert len(esito["findings"]) == 8
    assert esito["rules_violated"] == 8


def test_wapt_gli_url_colpiti_arrivano_tutti_e_serializzabili():
    """Il raggruppamento usa un `set`, che `render_json` non sa
    serializzare: `json.dumps` senza `default=` solleverebbe DOPO che
    tutti i moduli sono girati, cioe' a lavoro fatto."""
    alerts = [_alert(url="https://x/%d" % i) for i in range(3)]
    esito = mars_wapt.score_from_alerts(alerts)
    params = esito["findings"][0]["params"]
    assert params["urls"] == ["https://x/0", "https://x/1", "https://x/2"]
    json.dumps(esito["findings"])


def test_wapt_la_solution_di_zap_diventa_la_correzione():
    """La `solution` veniva scartata, ed e' il campo su cui poggia la
    Fase 3. Non si ripulisce: e' testo semplice, i <p> dei referti
    tradizionali li aggiunge il loro generatore, non l'alert."""
    testo = "Ensure that your web server is configured to set the header."
    esito = mars_wapt.score_from_alerts([_alert(solution=testo)])
    assert esito["findings"][0]["fix"] == testo


def test_wapt_una_solution_assente_non_e_un_errore():
    """Esistono alert Informational senza soluzione (10049-2 di ZAP ne
    e' uno): l'assenza non e' un motivo per scartare il rilievo."""
    esito = mars_wapt.score_from_alerts([_alert(solution=None)])
    assert esito["findings"][0]["fix"] == ""
    assert esito["findings"][0]["params"]["soluzioni"] == 0


def test_wapt_un_gruppo_con_piu_soluzioni_lo_dichiara():
    """Dentro un pluginId gli alertRef possono avere soluzioni diverse:
    `fix` ne porta una, e se le altre si perdono il dato deve dirlo
    invece di lasciar credere che fosse l'unica."""
    esito = mars_wapt.score_from_alerts([
        _alert(alertRef="10038-1", solution="Prima."),
        _alert(alertRef="10038-2", solution="Seconda.", url="https://x/b")])
    finding = esito["findings"][0]
    assert finding["fix"] == "Prima.", "la prima non vuota, deterministica"
    assert finding["params"]["soluzioni"] == 2


def test_wapt_le_reference_diventano_una_lista():
    """`reference` e' UNA stringa con dentro piu' URL: metterla in
    `Finding.url`, che e' un link solo, ne mostrerebbe uno e
    nasconderebbe gli altri."""
    esito = mars_wapt.score_from_alerts(
        [_alert(reference="https://a/\r\nhttps://b/\nhttps://c/\n")])
    finding = esito["findings"][0]
    assert finding["params"]["references"] == ["https://a/", "https://b/",
                                               "https://c/"]
    assert finding["url"] == "", "ambiguo fra pagina colpita e documentazione"


def test_wapt_gli_alert_refs_del_gruppo_non_si_perdono():
    """Il raggruppamento resta per regola — cambiarlo sposterebbe i
    punteggi — ma il dato che permettera' di affinarlo va conservato
    ADESSO, perche' dopo il ciclo non c'e' piu'."""
    esito = mars_wapt.score_from_alerts([
        _alert(alertRef="10038-2"),
        _alert(alertRef="10038-1", url="https://x/b")])
    assert esito["findings"][0]["params"]["alert_refs"] == ["10038-1",
                                                            "10038-2"]


def test_wapt_le_due_tabelle_di_rischio_coprono_gli_stessi_livelli():
    """`ZAP_PENALTIES` e la scala "zap" di mars_core vivono in file
    diversi e devono conoscere gli stessi livelli.

    Se divergessero, un livello noto a una sola delle due uscirebbe
    come rilievo `info` che pero' costa punti (o viceversa), senza che
    nulla si rompa."""
    assert ({r.lower() for r in mars_wapt.ZAP_PENALTIES}
            == set(mars_core._SCALE_SEVERITA["zap"]))


# --- il ramo di superficie: gli header ---------------------------------

@pytest.mark.parametrize("header, chiave, severita, peso", [
    ("Strict-Transport-Security", "sec.headers.hsts_missing",
     SEV_WARNING, 2.0),
    ("Content-Security-Policy", "sec.headers.csp_missing",
     SEV_WARNING, 2.0),
    ("X-Frame-Options", "sec.headers.xframe_missing", SEV_WARNING, 1.0),
])
def test_wapt_ogni_header_ha_chiave_e_gravita_editoriale(
        monkeypatch, header, chiave, severita, peso):
    """La gravita' di questi tre e' NOSTRA: in questo ramo ZAP non e'
    stato nemmeno raggiunto, e `source_severity` vuoto lo dichiara.

    Nessuno e' `critical`: un header mancante e' una difesa in
    profondita' assente, non una vulnerabilita' constatata — ed e' la
    stessa lettura di ZAP, che li classifica Medium e Low."""
    presenti = {h: "v" for h in mars_wapt.SECURITY_HEADERS if h != header}
    _risposte(monkeypatch, _Risposta(200, presenti))
    esito = mars_wapt.audit_headers("https://x/")
    assert len(esito["findings"]) == 1
    finding = esito["findings"][0]
    assert finding["key"] == chiave
    assert (finding["severity"], finding["weight"]) == (severita, peso)
    assert finding["source_severity"] == "", "la gravita' l'abbiamo scelta noi"
    assert finding["params"]["header"] == header


@pytest.mark.parametrize("presenti, punteggio", [
    (["Strict-Transport-Security", "Content-Security-Policy",
      "X-Frame-Options"], 100),
    (["Strict-Transport-Security", "Content-Security-Policy"], 90),
    (["Content-Security-Policy", "X-Frame-Options"], 85),
    (["X-Frame-Options"], 70),
    ([], 60),
])
def test_wapt_le_penalita_degli_header_sono_quelle_di_sempre(
        monkeypatch, presenti, punteggio):
    """I VALORI, non solo la loro relazione.

    Un test che verifica "la somma ricostruisce lo score" resta verde
    anche cambiando una penalita', perche' i due lati cambiano insieme:
    e' la lezione di U1.4. Questi cinque punti pinnano i numeri, e con
    essi il fatto che HSTS e CSP costino il doppio di X-Frame-Options."""
    _risposte(monkeypatch, _Risposta(200, {h: "v" for h in presenti}))
    esito = mars_wapt.audit_headers("https://x/")
    assert esito["score"] == punteggio
    assert esito["status"] == "surface"
    somma = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == 100 - somma


def test_wapt_il_ripiego_marca_ogni_rilievo_come_di_superficie(monkeypatch):
    """Senza il marcatore, un elenco di soli findings mostrerebbe tre
    `warning` come se una scansione di sicurezza ci fosse stata. E'
    R21 portato dentro il dato, come nel ripiego di mars_wcag."""
    _risposte(monkeypatch, _Risposta(200, {}))
    esito = mars_wapt.audit_headers("https://x/")
    assert all(f["params"]["surface"] is True for f in esito["findings"])


def test_wapt_il_ramo_zap_non_e_di_superficie():
    """La meta' negativa del test sopra: `surface` marca un controllo
    che non ha scansionato, e una scansione ZAP non lo e'."""
    esito = mars_wapt.score_from_alerts([_alert()])
    assert all("surface" not in f["params"] for f in esito["findings"])


def test_wapt_l_ordine_degli_header_e_lo_stesso_nelle_due_viste(monkeypatch):
    """HSTS e CSP costano uguale: un `sorted` applicato a una sola delle
    due viste li riordinerebbe solo li', e le due racconterebbero la
    stessa risposta in due ordini diversi."""
    _risposte(monkeypatch, _Risposta(200, {}))
    esito = mars_wapt.audit_headers("https://x/")
    assert esito["issues"] == ["HSTS mancante", "CSP mancante",
                               "X-Frame-Options mancante"]
    assert [f["params"]["header"] for f in esito["findings"]] == [
        "Strict-Transport-Security", "Content-Security-Policy",
        "X-Frame-Options"]


def test_wapt_gli_header_illeggibili_sono_uno_stato_non_un_difetto(
        monkeypatch):
    """Anche un'area non misurata porta il proprio rilievo: senza,
    sarebbe l'unica a sparire dagli elenchi costruiti sui findings.

    `penalty` assente e non zero: zero significa "e' un difetto che qui
    non costa punti", assente significa "non e' un difetto"."""
    _risposte(monkeypatch, requests.ConnectionError("giu'"),
              requests.ConnectionError("giu'"))
    esito = mars_wapt.audit_headers("https://x/")
    assert esito["score"] is None and esito["status"] == "unavailable"
    assert [f["key"] for f in esito["findings"]] == ["sec.status.unreadable"]
    finding = esito["findings"][0]
    assert finding["severity"] == SEV_INFO
    assert "penalty" not in finding["params"]
    assert finding["detail"] == "ConnectionError", "il motivo, non solo il fatto"


def test_wapt_il_ripiego_su_get_resta_un_ripiego(monkeypatch):
    """Esistono server che rifiutano HEAD con 405 o 501: leggerne gli
    header e concluderne che mancano tutti sarebbe un verdetto falso
    dato con sicurezza. Il ramo non aveva alcun test."""
    _risposte(monkeypatch, _Risposta(405, {}),
              _Risposta(200, {h: "v" for h in mars_wapt.SECURITY_HEADERS}))
    esito = mars_wapt.audit_headers("https://x/")
    assert esito["score"] == 100 and esito["findings"] == []


# --- i rilievi di stato di audit() -------------------------------------

def test_wapt_la_scansione_fermata_e_un_rilievo_di_stato(monkeypatch):
    """Una scansione parziale vale piu' di niente, ma spacciarla per
    completa no — e negli elenchi costruiti sui findings il fatto deve
    esserci, non solo nel campo `complete`."""
    esito = _audit_zap(monkeypatch, [_alert()], completa=False, fermate=True)
    assert esito["findings"][0]["key"] == "sec.status.partial"
    assert esito["findings"][0]["params"]["stopped"] is True


def test_wapt_la_scansione_non_fermata_e_un_rilievo_distinto(monkeypatch):
    """R27: interrotta e abbandonata sono due fatti diversi, e una
    chiave sola con un flag li rimetterebbe insieme. `not_stopped` e'
    la negazione esatta del campo `stopped` che il dict pubblica."""
    esito = _audit_zap(monkeypatch, [_alert()], completa=False, fermate=False,
                       active=True)
    finding = esito["findings"][0]
    assert finding["key"] == "sec.status.not_stopped"
    assert finding["params"] == {"stopped": False, "active_scan": True}
    # info e non warning: il difetto e' del nostro strumento, non del
    # sito, e la Fase 4 ordina il piano di interventi su `severity`.
    assert finding["severity"] == SEV_INFO


def test_wapt_una_scansione_completa_non_porta_rilievi_di_stato(monkeypatch):
    """Il ramo "tutto bene" non era mai stato esercitato: `complete`
    era False in ogni test esistente."""
    esito = _audit_zap(monkeypatch, [_alert()], completa=True, active=True)
    assert all(not f["key"].startswith("sec.status.")
               for f in esito["findings"])


@pytest.mark.parametrize("attiva, attesa", [(False, True), (True, False)])
def test_wapt_la_scansione_passiva_si_dichiara_nei_rilievi(monkeypatch,
                                                           attiva, attesa):
    """Un 100/100 passivo non e' un sito scansionato e trovato pulito:
    l'active scan richiede la dichiarazione di proprieta'."""
    esito = _audit_zap(monkeypatch, [_alert()], active=attiva)
    chiavi = [f["key"] for f in esito["findings"]]
    assert ("sec.status.passive_only" in chiavi) is attesa
    if attesa:
        assert chiavi[-1] == "sec.status.passive_only", "in coda, come la issue"


def test_wapt_i_rilievi_di_stato_non_pesano_sul_punteggio(monkeypatch):
    """`penalty: 0.0` significa "difetto che qui non costa"; la chiave
    assente significa "non e' un difetto". La distinzione va tenuta
    ferma, perche' la Fase 4 legge il primo e deve ignorare il
    secondo."""
    esito = _audit_zap(monkeypatch, [_alert()], completa=False, fermate=False)
    stati = [f for f in esito["findings"] if f["key"].startswith("sec.status")]
    assert len(stati) == 2
    assert all("penalty" not in f["params"] for f in stati)


def test_wapt_l_ordine_dei_rilievi_rispecchia_quello_delle_issues(monkeypatch):
    """Due viste della stessa scansione non possono raccontarla in due
    ordini diversi: chi legge il testo e chi legge il dato devono
    vedere gli stessi fatti nella stessa successione."""
    alerts = [_alert(pluginId="1", risk="High"),
              _alert(pluginId="2", risk="Medium", url="https://x/b"),
              _alert(pluginId="3", risk="Low", url="https://x/c")]
    esito = _audit_zap(monkeypatch, alerts, completa=False, fermate=True)
    chiavi = [f["key"] for f in esito["findings"]]
    assert chiavi[0] == "sec.status.partial", "in testa, come la issue"
    assert chiavi[-1] == "sec.status.passive_only", "in coda, come la issue"
    assert chiavi[1:-1] == ["sec.zap.1", "sec.zap.2", "sec.zap.3"]
    # e i titoli dei rilievi ZAP seguono l'ordine delle issues centrali
    titoli = [f["title"] for f in esito["findings"][1:-1]]
    assert all(t in i for t, i in zip(titoli, esito["issues"][1:4]))


def test_wapt_i_findings_arrivano_al_referto(monkeypatch):
    """Il modulo puo' produrli perfetti e `build_report` buttarli via:
    copia una lista CHIUSA di chiavi. Il consumatore va verificato."""
    from mars_report import build_report
    esito = _audit_zap(monkeypatch, [_alert()])
    referto = build_report({"mars_wapt": esito}, {"url": "https://x/"})
    area = [a for a in referto["areas"] if a["module"] == "mars_wapt"][0]
    assert area["findings"] == esito["findings"]
    assert all(f["key"].startswith("sec.") for f in area["findings"])


def test_wapt_nessuna_credenziale_finisce_nei_rilievi(monkeypatch):
    """`details` porta il dict intero fuori dall'API: un rilievo che
    citasse il proxy con la sua chiave la pubblicherebbe."""
    monkeypatch.setattr(mars_wapt, "connect_zap",
                        lambda credentials=None: object())
    monkeypatch.setattr(mars_wapt, "run_zap",
                        lambda url, client=None, active=False:
                        ([_alert()], True, True))
    esito = mars_wapt.audit({
        "url": "https://x/", "owner_declaration": True,
        "credentials": {"zap_api_key": "SPIA",
                        "zap_proxy": "http://interno:8080"}})
    assert "SPIA" not in json.dumps(esito["findings"])
    assert "interno" not in json.dumps(esito["findings"])


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
