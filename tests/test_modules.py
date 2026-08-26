#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — i moduli d'area, su fixture offline.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
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
from conftest import TESTI_AXE, WHICH_VERO, pagina
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


def test_tech_nosnippet_toglie_la_citabilita_pur_lasciando_l_indice():
    """R36: `nosnippet` era invisibile, ed e' la direttiva che pesa di
    piu' sull'oggetto di questo progetto.

    Una pagina con `nosnippet` resta regolarmente indicizzata e **non
    puo' essere citata**: nessun frammento del suo testo puo' comparire
    in una risposta. Misurato prima della correzione, contro un
    riferimento senza direttive che vale 94, valeva 94: cioe' nulla."""
    aperto = mars_tech.audit(_contesto_tech())
    zittita = mars_tech.audit(_contesto_tech(meta_robots="nosnippet"))
    per_chiave = {f["key"]: f for f in zittita["findings"]}

    assert "tech.index.nosnippet" in per_chiave
    assert aperto["score"] - zittita["score"] >= 20
    # Resta negli indici: e' l'altra meta' del difetto, e confonderla
    # con `noindex` direbbe una cosa falsa su che cosa e' rotto.
    assert "tech.index.noindex" not in per_chiave


@pytest.mark.parametrize("direttiva", [
    "nosnippet", "max-snippet:0", "max-snippet: 0", "NoSnippet",
    "max-snippet:0, nofollow", "index, follow, nosnippet",
])
def test_tech_le_scritture_del_divieto_di_frammento_valgono_uguale(direttiva):
    """`max-snippet:0` e' `nosnippet` scritto in un altro modo, e lo
    spazio dopo i due punti e' legale.

    Senza normalizzare il valore il token si spezza in `max-snippet:` e
    `0`, e il confronto con l'insieme delle direttive non trova nulla:
    misurato, e' il caso che un `frozenset({"max-snippet:0"})` manca."""
    esito = mars_tech.audit(_contesto_tech(meta_robots=direttiva))
    assert any(f["key"] == "tech.index.nosnippet" for f in esito["findings"])


@pytest.mark.parametrize("direttiva", [
    "max-snippet:-1", "max-snippet: 50", "max-image-preview:none",
    "max-video-preview:0",
])
def test_tech_un_limite_di_frammento_diverso_da_zero_non_e_un_divieto(
        direttiva):
    """`max-snippet:-1` significa 'nessun limite' ed e' l'opposto del
    divieto; `max-video-preview:0` non tocca il testo. Un confronto per
    prefisso li tratterebbe tutti come `nosnippet`."""
    esito = mars_tech.audit(_contesto_tech(meta_robots=direttiva))
    assert not any(f["key"] == "tech.index.nosnippet"
                   for f in esito["findings"])


def test_tech_noarchive_pesa_ma_non_come_il_divieto_di_frammento():
    """`noarchive` vieta la copia in cache, non il frammento: il testo
    resta citabile, quindi e' un rilievo lieve. L'asserzione forte e'
    l'ordine fra i tre punteggi, non l'esistenza del rilievo."""
    aperto = mars_tech.audit(_contesto_tech())
    archivio = mars_tech.audit(_contesto_tech(meta_robots="noarchive"))
    frammento = mars_tech.audit(_contesto_tech(meta_robots="nosnippet"))
    per_chiave = {f["key"]: f for f in archivio["findings"]}

    assert per_chiave["tech.index.noarchive"]["source_severity"] == "lieve"
    assert aperto["score"] > archivio["score"] > frammento["score"]


def test_tech_su_una_pagina_esclusa_il_frammento_non_si_paga_due_volte():
    """`noindex, nosnippet` e' una combinazione reale. La pagina e' gia'
    fuori dagli indici: il divieto di frammento non toglie nulla che non
    fosse gia' tolto, e sommare le due penalita' farebbe pagare due
    volte lo stesso fatto — 80 punti su 100 per un difetto solo."""
    solo_noindex = mars_tech.audit(_contesto_tech(meta_robots="noindex"))
    insieme = mars_tech.audit(_contesto_tech(meta_robots="noindex, nosnippet"))

    assert insieme["score"] == solo_noindex["score"]
    assert not any(f["key"] == "tech.index.nosnippet"
                   for f in insieme["findings"])


def test_tech_il_divieto_di_frammento_su_tutto_il_sito_pesa_di_piu():
    """Come per `noindex`, la gravita' segue la diffusione. Il
    denominatore pero' sono le pagine **ancora citabili**, non tutte:
    se le altre sono gia' escluse dagli indici, il sito e' muto lo
    stesso, e chiamarlo `grave` direbbe che qualcosa si salva."""
    def sito(*direttive):
        ctx = _contesto_tech()
        ctx["pages"] = {"https://esempio.test/p%d" % n: pagina(meta_robots=d)
                        for n, d in enumerate(direttive)}
        return {f["key"]: f for f in mars_tech.audit(ctx)["findings"]}

    parziale = sito("", "nosnippet")["tech.index.nosnippet"]
    totale = sito("nosnippet", "nosnippet")["tech.index.nosnippet"]
    misto = sito("noindex", "nosnippet")["tech.index.nosnippet"]

    assert parziale["source_severity"] == "grave"
    assert parziale["params"]["pagine"] == 1
    assert parziale["params"]["totale"] == 2
    assert parziale["params"]["urls"] == ["https://esempio.test/p1"]
    assert totale["source_severity"] == "critico"
    assert misto["source_severity"] == "critico"


def test_tech_le_due_ricuciture_dei_due_punti_non_si_confondono():
    """Nel modulo i due punti significano due cose, e non vanno confuse.

    `max-snippet: 0` e' una direttiva col suo VALORE, e i due pezzi si
    ricuciono (R36). `googlebot: noindex` e' un PREFISSO per agente, e i
    due pezzi si separano (R37). Un parser che trattasse i due casi allo
    stesso modo romperebbe l'altro in silenzio: ricucendo tutto,
    `googlebot:noindex` diventerebbe un token unico e il noindex
    sparirebbe; separando tutto, `max-snippet` diventerebbe un agente e
    sparirebbe il divieto di frammento.

    Fino a R37 questo test asseriva che `googlebot:` restasse fra i
    token, che era il comportamento di allora — contato come se la
    direttiva valesse per tutti. R37 lo cambia DI PROPOSITO: qui si
    fissa il confine fra le due ricuciture, che e' cio' che deve
    restare vero comunque."""
    globali, agenti = mars_tech.direttive_per_agente(
        {"x_robots_tag": "googlebot: noindex, max-snippet: 0"})

    # Il prefisso e' un agente, e si porta dietro cio' che segue.
    assert set(agenti) == {"googlebot"}
    assert "noindex" in agenti["googlebot"]
    # La direttiva con valore resta un token solo, e NON e' un agente.
    assert "max-snippet:0" in agenti["googlebot"]
    assert "max-snippet" not in agenti
    assert globali == set()


def test_tech_una_data_non_diventa_un_agente():
    """Un'ora contiene i due punti, e una data RFC 850 le virgole.

    `unavailable_after: saturday, 21-sep-2020 12:00:00 gmt` si spezza
    sulle virgole in due pezzi, e il secondo — ` 21-sep-2020 12:00:00
    gmt` — ha i due punti dell'ORA: letto come prefisso creava l'agente
    `21-sep-2020 12` e con esso un rilievo `agent_only` inventato.
    Misurato. Un nome di crawler non contiene spazi, ed e' il criterio
    che distingue le due cose.
    """
    _, agenti = mars_tech.direttive_per_agente(
        {"x_robots_tag": "unavailable_after: saturday, "
                         "21-sep-2020 12:00:00 gmt"})
    assert agenti == {}, "una data e' diventata un agente: %s" % sorted(agenti)

    esito = mars_tech.audit(_contesto_tech(
        x_robots_tag="unavailable_after: saturday, 21-sep-2020 "
                     "12:00:00 gmt"))
    chiavi = {f["key"] for f in esito["findings"]}
    assert "tech.index.agent_only" not in chiavi
    assert "tech.index.unavailable_after" in chiavi


def test_tech_il_grezzo_efficace_ricompone_la_spaziatura_di_partenza():
    """Il testo si ricompone con `, `, non con `,`.

    Senza lo spazio, `saturday,21-sep-2020 12:00:00 gmt` si legge
    ancora — ma solo per un dettaglio implementativo di
    `email._parseaddr`, che cerca l'ultima virgola dentro il primo
    token. Appoggiarsi a quello significa che la data smetterebbe di
    leggersi il giorno in cui CPython lo cambia, senza che nulla qui
    diventi rosso."""
    grezzo = mars_tech._grezzo_efficace(
        {"x_robots_tag": "unavailable_after: saturday, "
                         "21-sep-2020 12:00:00 gmt"})
    assert grezzo == "unavailable_after:saturday, 21-sep-2020 12:00:00 gmt"

    # E i pezzi di un agente altrui non entrano affatto.
    solo_ia = mars_tech._grezzo_efficace(
        {"x_robots_tag": "googlebot: noindex, gptbot: nofollow"})
    assert "noindex" not in solo_ia
    assert "nofollow" in solo_ia


def test_tech_una_scadenza_per_un_altro_agente_non_scade_per_tutti():
    """Il prefisso per agente vale anche per la SCADENZA.

    `scadenza_dichiarata()` legge la data dal grezzo con una regex, e
    fino a qui ignorava il prefisso: `googlebot: unavailable_after:
    <passato>` produceva il rilievo pieno **piu'** `agent_only`, e il
    punteggio scendeva a 46 — cioe' **peggio** di una scadenza che vale
    per tutti (54). Una direttiva meno grave riceveva un giudizio piu'
    grave: e' l'incoerenza fra R36, che legge il grezzo, e R37, che
    separa gli agenti.
    """
    globale = mars_tech.audit(_contesto_tech(
        x_robots_tag="unavailable_after: 2020-01-01"))
    altrui = mars_tech.audit(_contesto_tech(
        x_robots_tag="googlebot: unavailable_after: 2020-01-01"))
    chiavi = {f["key"] for f in altrui["findings"]}

    assert "tech.index.unavailable_after" not in chiavi
    assert "tech.index.agent_only" in chiavi
    assert altrui["score"] > globale["score"], \
        "una restrizione a un solo agente non puo' pesare di piu'"


def test_tech_una_pagina_scaduta_e_fuori_dagli_indici():
    """R36: `unavailable_after` passato equivale a `noindex`, e valeva
    zero. Chiave propria e non l'elenco del noindex: il titolo di
    quel rilievo e' tradotto e congelato nei golden, e nominarvi una
    terza direttiva muoverebbe testi che non c'entrano."""
    aperto = mars_tech.audit(_contesto_tech())
    scaduta = mars_tech.audit(_contesto_tech(
        meta_robots="unavailable_after: 2020-01-01"))
    per_chiave = {f["key"]: f for f in scaduta["findings"]}

    assert per_chiave["tech.index.unavailable_after"]["source_severity"] \
        == "critico"
    assert aperto["score"] - scaduta["score"] >= 40
    assert per_chiave["tech.index.unavailable_after"]["params"]["urls"] == \
        ["https://esempio.test/"]


def test_tech_una_scadenza_futura_non_e_un_rilievo():
    """La direttiva e' una programmazione, non un difetto: finche' la
    data non e' passata la pagina e' regolarmente indicizzata."""
    futura = mars_tech.audit(_contesto_tech(
        meta_robots="unavailable_after: 2099-01-01"))
    assert futura["score"] == mars_tech.audit(_contesto_tech())["score"]


@pytest.mark.parametrize("valore", [
    "2020-09-21",                            # ISO 8601, come documentata
    "2020-09-21t12:00:00z",                  # ISO con ora e fuso
    "saturday, 21-sep-2020 12:00:00 gmt",    # RFC 850, l'altra documentata
    "sat, 21 sep 2020 12:00:00 gmt",         # RFC 2822
])
def test_tech_i_formati_di_data_ammessi_si_leggono_tutti(valore):
    """Google documenta ISO 8601 e RFC 850. La virgola di RFC 850 e'
    anche il separatore delle direttive: se il valore si tagliasse
    sempre li', 'Saturday' sarebbe tutto cio' che resta e la data non
    si leggerebbe mai.

    **I valori sono minuscoli perche' il crawler li abbassa.**
    `mars_core` scrive `meta_robots` e `x_robots_tag` con `.lower()`,
    quindi una `Z` maiuscola non arriva mai qui: esercitarla — come
    faceva la prima stesura di questo test — avrebbe presidiato un
    percorso che il crawler ha gia' chiuso un livello piu' su, mentre
    il solo caso reale restava scoperto."""
    esito = mars_tech.audit(_contesto_tech(
        meta_robots="unavailable_after: %s" % valore))
    assert any(f["key"] == "tech.index.unavailable_after"
               for f in esito["findings"]), valore


def test_tech_la_scadenza_si_legge_anche_dall_header():
    """Tutti i casi qui sopra passano dal meta. L'header e' l'altra
    fonte, e senza un caso che la eserciti si potrebbe smettere di
    leggerla senza che nulla diventi rosso."""
    esito = mars_tech.audit(_contesto_tech(
        x_robots_tag="unavailable_after: 2020-01-01"))
    per_chiave = {f["key"]: f for f in esito["findings"]}

    assert "tech.index.unavailable_after" in per_chiave
    assert per_chiave["tech.index.unavailable_after"]["source_severity"] \
        == "critico"


def test_tech_la_scadenza_di_un_crawler_ia_vale_come_globale():
    """`gptbot: unavailable_after: <passato>` e' il caso che questo
    progetto misura: la scadenza mirata proprio a un assistente.

    Deve produrre il rilievo pieno e non `agent_only`, ed e' il gemello
    obbligatorio del test qui sopra — senza, il ramo IA del parser per
    agente resta scoperto sulla scadenza."""
    esito = mars_tech.audit(_contesto_tech(
        x_robots_tag="gptbot: unavailable_after: 2020-01-01"))
    chiavi = {f["key"] for f in esito["findings"]}

    assert "tech.index.unavailable_after" in chiavi
    assert "tech.index.agent_only" not in chiavi


@pytest.mark.parametrize("valore", [
    "", "domani", "25 dicembre", "0000-00-00", "2020-13-45",
])
def test_tech_una_scadenza_illeggibile_non_e_una_scadenza(valore):
    """Il valore viene dal sito analizzato, quindi e' dato ostile: una
    data che non si legge non produce un rilievo e non solleva. Dedurre
    'scaduta' da una data illeggibile sarebbe un giudizio critico su
    una misura che non c'e'."""
    esito = mars_tech.audit(_contesto_tech(
        meta_robots="unavailable_after: %s" % valore))
    assert not any(f["key"] == "tech.index.unavailable_after"
                   for f in esito["findings"]), valore


def test_tech_la_scadenza_convive_con_le_altre_direttive():
    """La coda dopo i due punti non e' tutta la data: quando la
    direttiva non e' l'ultima, il valore finisce alla prima virgola."""
    esito = mars_tech.audit(_contesto_tech(
        meta_robots="nofollow, unavailable_after: 2020-09-21, noarchive"))
    chiavi = {f["key"] for f in esito["findings"]}
    assert {"tech.index.unavailable_after", "tech.index.nofollow",
            "tech.index.noarchive"} <= chiavi


def test_tech_su_una_pagina_gia_esclusa_la_scadenza_non_si_paga_due_volte():
    """`noindex` e una data passata dicono lo stesso fatto. Come per il
    divieto di frammento, il secondo non aggiunge penalita'."""
    solo_noindex = mars_tech.audit(_contesto_tech(meta_robots="noindex"))
    insieme = mars_tech.audit(_contesto_tech(
        meta_robots="noindex, unavailable_after: 2020-01-01"))

    assert insieme["score"] == solo_noindex["score"]
    assert not any(f["key"] == "tech.index.unavailable_after"
                   for f in insieme["findings"])


def test_tech_una_pagina_scaduta_non_paga_anche_il_divieto_di_frammento():
    """Una pagina scaduta e' gia' fuori dagli indici: il `nosnippet` che
    porta con se' non toglie nulla che non fosse gia' tolto."""
    esito = mars_tech.audit(_contesto_tech(
        meta_robots="nosnippet, unavailable_after: 2020-01-01"))
    chiavi = {f["key"] for f in esito["findings"]}

    assert "tech.index.unavailable_after" in chiavi
    assert "tech.index.nosnippet" not in chiavi


def test_tech_la_gravita_della_scadenza_segue_la_diffusione():
    """Come per `noindex`, e col denominatore del divieto di frammento:
    le pagine non gia' escluse per altra via. L'ultimo caso e' quello
    che distingue i due denominatori — una scaduta su due, ma l'altra
    e' gia' noindex, quindi non resta nulla di indicizzato."""
    def sito(*direttive):
        ctx = _contesto_tech()
        ctx["pages"] = {"https://esempio.test/p%d" % n: pagina(meta_robots=d)
                        for n, d in enumerate(direttive)}
        return {f["key"]: f for f in mars_tech.audit(ctx)["findings"]}

    scaduta = "unavailable_after: 2020-01-01"
    tutte = sito(scaduta, scaduta)["tech.index.unavailable_after"]
    una = sito("", scaduta)["tech.index.unavailable_after"]
    con_esclusa = sito("noindex", scaduta)["tech.index.unavailable_after"]

    assert tutte["source_severity"] == "critico"
    assert tutte["params"]["pagine"] == 2
    assert una["source_severity"] == "grave"
    assert con_esclusa["source_severity"] == "critico"


def test_tech_l_orologio_si_legge_una_volta_sola_per_audit():
    """Leggendo l'orologio dentro il ciclo, due pagine con la stessa
    data ai due lati di un secondo riceverebbero giudizi diversi, e
    l'audit non sarebbe riproducibile su se stesso.

    Il commento nel codice lo dichiara; senza questo test nessuno lo
    verificherebbe, perche' spostare la riga dentro il ciclo lascia
    ogni altra asserzione verde."""
    letture = []
    vero = mars_tech.datetime

    class OrologioContato(vero):          # type: ignore[misc, valid-type]
        @classmethod
        def now(cls, tz=None):
            letture.append(tz)
            return vero.now(tz)

    ctx = _contesto_tech()
    ctx["pages"] = {"https://esempio.test/p%d" % n:
                    pagina(meta_robots="unavailable_after: 2020-01-01")
                    for n in range(4)}
    mars_tech.datetime = OrologioContato
    try:
        esito = mars_tech.audit(ctx)
    finally:
        mars_tech.datetime = vero

    assert len(letture) == 1, "un audit, un istante: %d letture" % len(letture)
    assert any(f["key"] == "tech.index.unavailable_after"
               for f in esito["findings"])


@pytest.mark.parametrize("chiave", [
    "tech.index.nosnippet", "tech.index.noarchive",
    "tech.index.unavailable_after",
])
def test_l_esempio_delle_direttive_chiude_davvero_il_rilievo(chiave):
    """Lo stesso presidio di U3.1, sulle tre chiavi nuove: un esempio e'
    la forma di ARRIVO, e se applicato non chiude il rilievo che
    pretende di correggere e' peggio di nessun esempio.

    Il caso che lo rende utile e' `max-snippet:-1`, che sembra un
    limite ed e' il suo contrario: se finisse per errore fra le
    direttive vietate, l'esempio del `nosnippet` accenderebbe proprio
    il rilievo che chiude. L'esempio passa dal DOM vero, non da un
    `meta_robots` scritto a mano."""
    import mars_fixes
    from mars_i18n import RILIEVI

    for esempio in (mars_fixes.CATALOGO[chiave]["example"],
                    RILIEVI["en"][chiave]["example"]):
        ctx = _contesto_tech()
        ctx["pages"] = {"https://esempio.test/": pagina(
            "<html><head>%s</head><body><p>x</p></body></html>" % esempio)}
        chiavi = {f["key"] for f in mars_tech.audit(ctx)["findings"]}
        assert chiave not in chiavi, "%s: l'esempio non chiude" % esempio


def test_tech_una_direttiva_per_google_non_e_una_per_gli_assistenti():
    """R37: `X-Robots-Tag: googlebot: noindex` esclude Google e **non**
    GPTBot, ClaudeBot o PerplexityBot.

    Misurato prima della correzione, i tre casi ricevevano lo stesso
    identico giudizio — 54, `tech.index.noindex` critico — mentre sono
    fatti diversi. Questo progetto misura la citabilita' IA: una
    direttiva mirata al solo Google non toglie il sito agli assistenti,
    e chiamarla critica direbbe il falso.

    La contropartita e' dichiarata: la gravita' di un'esclusione reale
    da Google SCENDE. E' una scelta editoriale coerente con l'oggetto
    del progetto, non una svista, e sta nella docstring del modulo."""
    tutti = mars_tech.audit(_contesto_tech(x_robots_tag="noindex"))
    solo_google = mars_tech.audit(
        _contesto_tech(x_robots_tag="googlebot: noindex"))
    chiavi = {f["key"] for f in solo_google["findings"]}

    per_chiave = {f["key"]: f for f in solo_google["findings"]}
    assert "tech.index.noindex" not in chiavi
    assert "tech.index.agent_only" in chiavi
    assert solo_google["score"] > tutti["score"]

    ristretto = per_chiave["tech.index.agent_only"]
    assert ristretto["params"]["agents"] == ["googlebot"]
    assert ristretto["params"]["directives"] == ["noindex"]
    # Senza `urls` il rilievo esce dalla treemap, e senza un errore (R47).
    assert ristretto["params"]["urls"] == ["https://esempio.test/"]


def test_tech_una_direttiva_mirata_a_un_crawler_ia_resta_grave():
    """L'altra meta', ed e' quella che conta: `gptbot: noindex` colpisce
    esattamente i crawler che l'area 1 enumera in `CRAWLER_IA`.

    Deve restare il rilievo di sempre, con la gravita' di sempre, e
    dire per NOME chi e' escluso."""
    tutti = mars_tech.audit(_contesto_tech(x_robots_tag="noindex"))
    solo_ia = mars_tech.audit(_contesto_tech(x_robots_tag="gptbot: noindex"))
    per_chiave = {f["key"]: f for f in solo_ia["findings"]}

    assert "tech.index.noindex" in per_chiave
    assert per_chiave["tech.index.noindex"]["source_severity"] == "critico"
    assert solo_ia["score"] == tutti["score"]
    assert per_chiave["tech.index.noindex"]["params"]["agents"] == ["gptbot"]


def test_tech_il_prefisso_vale_fino_al_prossimo(monkeypatch):
    """Piu' header `X-Robots-Tag` arrivano uniti da una virgola sola —
    e' `requests` che li concatena — quindi il prefisso non si legge
    per token ma per POSIZIONE: vale fino al prossimo che compare.

    Il caso e' quello documentato da Google:
        X-Robots-Tag: googlebot: nofollow
        X-Robots-Tag: otherbot: noindex, nofollow
    """
    esito = mars_tech.audit(_contesto_tech(
        x_robots_tag="googlebot: nofollow, gptbot: noindex, nosnippet"))
    per_chiave = {f["key"]: f for f in esito["findings"]}

    # Le due direttive dopo `gptbot:` sono entrambe sue.
    assert "tech.index.noindex" in per_chiave
    assert per_chiave["tech.index.noindex"]["params"]["agents"] == ["gptbot"]
    # E il nofollow di googlebot non e' diventato un nofollow di tutti.
    assert "tech.index.nofollow" not in per_chiave
    assert "tech.index.agent_only" in per_chiave


def test_tech_senza_prefisso_la_direttiva_vale_per_tutti():
    """Il caso normale non deve cambiare: nessun prefisso, nessun
    agente, e il rilievo non porta `agents`."""
    esito = mars_tech.audit(_contesto_tech(x_robots_tag="noindex, nofollow"))
    per_chiave = {f["key"]: f for f in esito["findings"]}

    assert per_chiave["tech.index.noindex"]["source_severity"] == "critico"
    assert "agents" not in per_chiave["tech.index.noindex"]["params"]
    assert "tech.index.agent_only" not in per_chiave


@pytest.mark.parametrize("direttiva", [
    "max-snippet: 0", "max-snippet:0", "unavailable_after: 2020-01-01",
    "max-image-preview: none",
])
def test_tech_una_direttiva_con_valore_non_e_un_prefisso(direttiva):
    """Regressione incrociata con R36: `max-snippet: 0` contiene i due
    punti come `googlebot: noindex`, e un parser che leggesse ogni `:`
    come prefisso creerebbe l'agente «max-snippet», facendo sparire il
    divieto di frammento senza un errore."""
    esito = mars_tech.audit(_contesto_tech(x_robots_tag=direttiva))
    chiavi = {f["key"] for f in esito["findings"]}
    assert "tech.index.agent_only" not in chiavi


def _tech_su(html: str) -> dict:
    """L'audit tecnico su una pagina sola, costruita dal suo HTML."""
    ctx = _contesto_tech()
    ctx["pages"] = {"https://esempio.test/": pagina(html=html)}
    return mars_tech.audit(ctx)


def test_tech_il_meta_per_agente_vale_come_il_prefisso_dell_header():
    """R51, cioe' la meta' di R37 che era rimasta aperta.

    `<meta name="googlebot" content="noindex">` esclude il SOLO Google,
    esattamente come `X-Robots-Tag: googlebot: noindex`, e Google non e'
    un assistente IA: il rilievo giusto e' `agent_only`, di gravita'
    media, non il `noindex` pieno che dichiarerebbe il sito invisibile.

    **Questo test asseriva l'opposto** — `tech.index.noindex in chiavi`
    — e fissava il comportamento di allora dichiarando che sarebbe
    diventato rosso il giorno in cui la voce si fosse chiusa. E' quel
    giorno."""
    esito = _tech_su('<html lang="it"><head>'
                     '<meta name="googlebot" content="noindex">'
                     '</head><body><p>x</p></body></html>')
    rilievi = {f["key"]: f for f in esito["findings"]}

    assert "tech.index.noindex" not in rilievi, \
        "una direttiva per il solo Google non esclude il sito dagli assistenti"
    assert rilievi["tech.index.agent_only"]["params"]["agents"] == ["googlebot"]
    assert rilievi["tech.index.agent_only"]["params"]["directives"] == \
        ["noindex"]


def test_tech_il_meta_globale_e_quello_per_agente_non_si_confondono():
    """Due meta sulla stessa pagina, e l'agente del secondo non deve
    colare sul primo ne' viceversa.

    E' il difetto che la grammatica dell'header porta con se': li' il
    prefisso vale per POSIZIONE, fino al prossimo. Nel DOM ogni meta e'
    un elemento a se', e unirli in una stringa posizionale
    ricreerebbe la confusione da un'altra parte."""
    esito = _tech_su('<html lang="it"><head>'
                     '<meta name="robots" content="nofollow">'
                     '<meta name="googlebot" content="noindex">'
                     '</head><body><p>x</p></body></html>')
    rilievi = {f["key"]: f for f in esito["findings"]}

    assert "tech.index.nofollow" in rilievi, "il meta globale vale per tutti"
    assert "tech.index.noindex" not in rilievi
    assert rilievi["tech.index.agent_only"]["params"]["directives"] == \
        ["noindex"]


def test_tech_la_scadenza_per_agente_non_scade_per_tutti():
    """La stessa regola di R37 sulla scadenza, ora anche per il meta:
    `unavailable_after` riservato a Google non toglie la pagina agli
    assistenti, e produrre il rilievo pieno la peserebbe piu' di una
    scadenza che vale per chiunque."""
    esito = _tech_su('<html lang="it"><head>'
                     '<meta name="googlebot" '
                     'content="unavailable_after: 2020-01-01">'
                     '</head><body><p>x</p></body></html>')
    chiavi = {f["key"] for f in esito["findings"]}

    assert "tech.index.unavailable_after" not in chiavi
    assert "tech.index.agent_only" in chiavi


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


def test_tech_una_scadenza_globale_non_si_perde_per_un_meta_altrui():
    """La scadenza si legge dal GREZZO, dove le fonti sono unite e il
    prefisso vale fino al prossimo: i blocchi per agente stanno percio'
    in coda. Messi in testa, il loro agente colerebbe sul meta globale
    e una scadenza che vale per tutti sparirebbe."""
    esito = _tech_su('<html lang="it"><head>'
                     '<meta name="robots" '
                     'content="unavailable_after: 2020-01-01">'
                     '<meta name="googlebot" content="noarchive">'
                     '</head><body><p>x</p></body></html>')
    chiavi = {f["key"] for f in esito["findings"]}

    assert "tech.index.unavailable_after" in chiavi, \
        "la scadenza e' del meta globale e vale per chiunque"
    assert "tech.index.agent_only" in chiavi


def test_tech_l_agente_del_meta_si_confronta_in_minuscolo():
    """`direttive_per_agente` riceve un **dict**, che attraversa il
    confine dei plugin: puo' arrivare da un modulo di terzi, non solo
    dal crawler che normalizza. Un agente maiuscolo che non incontrasse
    `CRAWLER_IA` renderebbe globale una direttiva mirata, senza errore."""
    _, per_agente = mars_tech.direttive_per_agente(
        {"meta_robots_by_agent": {"ClaudeBot": "noindex"}})
    assert per_agente == {"claudebot": {"noindex"}}
    assert mars_tech.direttive_efficaci(set(), per_agente) == {"noindex"}, \
        "ClaudeBot E' un assistente: la direttiva lo riguarda davvero"


def test_tech_direttive_da_piu_meta_tag():
    """Il crawler unisce con uno spazio i `content` di piu' meta
    `robots`: le direttive vanno separate anche li', non solo sulle
    virgole. Qui la pagina passa dal costruttore vero, non da un
    dizionario scritto a mano.

    I due meta erano `robots` e `googlebot` finche' il crawler li
    univa; da R51 il secondo vive in `meta_robots_by_agent` e questo
    test non lo riguarda piu' — lo riguardano i tre qui sopra. Cio' che
    resta suo e' lo SPAZIO come separatore, che due meta `robots` sulla
    stessa pagina producono ancora."""
    p = pagina(html='<html lang="it"><head>'
                    '<meta name="robots" content="noindex">'
                    '<meta name="robots" content="nofollow">'
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
    "tech.index.nosnippet", "tech.index.noarchive",
    "tech.index.unavailable_after", "tech.index.agent_only",
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

def test_schema_un_sito_senza_json_ld_non_e_un_difetto_che_ricorre():
    """R46: `instances` dice quante volte il difetto ricorre, e la sua
    assenza e' un significato.

    «Nessun JSON-LD sul sito» e' un fatto UNICO, non un'occorrenza che
    capita una volta: dichiarare `instances: 1` lo farebbe scendere di
    un gradino di sforzo insieme alle immagini singole, che e'
    esattamente il contrario — un sito senza dati strutturati e'
    lavoro, non una svista."""
    vuoto = {"pages": {"https://x/": pagina(
        html="<html><head></head><body><p>x</p></body></html>")}}
    per_chiave = {f["key"]: f for f in mars_schema.audit(vuoto)["findings"]}
    assert "instances" not in per_chiave["sd.jsonld.missing"]["params"]

    rotto = {"pages": {"https://x/": pagina(
        html='<html><head><script type="application/ld+json">{,}</script>'
             "</head><body><p>x</p></body></html>")}}
    malformato = {f["key"]: f
                  for f in mars_schema.audit(rotto)["findings"]}
    assert malformato["sd.jsonld.block_malformed"]["params"]["instances"] == 1


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
    alla spiegazione della regola, cioe' meta' del lavoro della Fase 3.

    Sta in `doc_url` e non in `url`: e' la documentazione della regola,
    non una pagina del sito. Finche' il campo si chiamava `url` era
    l'unico valorizzato in tutto il referto, e prometteva la seconda
    cosa mentre portava la prima (R47)."""
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical", "help": "H",
          "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/image-alt",
          "nodes": [0]}], 1)
    finding = esito["findings"][0]
    assert finding["doc_url"].endswith("/image-alt")
    assert "url" not in finding, "il nome che prometteva la pagina"


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


def test_run_axe_etichetta_ogni_violazione_con_la_sua_pagina(monkeypatch):
    """axe restituisce le violazioni pagina per pagina e non dice di
    quale: appiattirle in una lista sola buttava via l'unica occasione
    di saperlo, e dopo il ciclo il dato non c'e' piu' (R47).

    E' cio' su cui poggia la colorazione della treemap: senza
    l'etichetta il rilievo axe non sa dove sta, e il rettangolo resta
    grigio pur essendoci un critico sopra."""
    urls = ["https://x/1", "https://x/2", "https://x/3"]
    _playwright_finto(monkeypatch, falliscono=["https://x/2"])
    violazioni, _ = mars_wcag.run_axe(urls)
    assert [v[mars_wcag.CHIAVE_PAGINA] for v in violazioni] == [
        "https://x/1", "https://x/3"], "la pagina fallita non ne porta"

    # E la catena fino al rilievo: due pagine, una regola, `pages` che
    # resta il contatore del punteggio e `urls` che dice dove.
    esito = mars_wcag.score_from_violations(violazioni, 2)
    finding = esito["findings"][0]
    assert finding["params"]["urls"] == ["https://x/1", "https://x/3"]
    assert finding["params"]["pages"] == 2


def test_wcag_una_violazione_senza_etichetta_non_inventa_pagine():
    """`score_from_violations` e' pubblica e pura: la si esercita anche
    su violazioni che non vengono da `run_axe`. Li' l'etichetta non c'e',
    e il rilievo deve dichiarare zero pagine invece di inventarne."""
    esito = mars_wcag.score_from_violations([_viol()], 1)
    assert esito["findings"][0]["params"]["urls"] == []


def test_wcag_i_controlli_statici_dicono_su_quali_pagine(contesto):
    """Il rilievo resta UNO per controllo — spezzarlo per pagina
    moltiplicherebbe la penalita' — ma il conteggio e le pagine sono
    due domande diverse, e finora rispondeva solo alla prima (R47)."""
    pages = {
        "https://x/a": {"lang": "it", "images": [{"src": "1.png"}],
                        "tabindex": ["2"]},
        "https://x/b": {"lang": "it", "images": [{"src": "2.png",
                                                  "alt": "ok"}]},
        "https://x/c": {"lang": "it", "images": [{"src": "3.png"}]},
    }
    per_chiave = {f.key: f for f in mars_wcag.controlli_statici(pages)}
    assert per_chiave["wcag.img.alt_missing"].params["urls"] == [
        "https://x/a", "https://x/c"], "non la pagina con l'alt a posto"
    assert per_chiave["wcag.img.alt_missing"].params["immagini"] == 2
    assert per_chiave["wcag.tabindex.positive"].params["urls"] == [
        "https://x/a"]


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


# --- U3.2: il fix di axe viene dal locale di axe ----------------------
#
# Le tre famiglie dinamiche prendono il testo dallo strumento e non dal
# catalogo di `mars_fixes`: la regola violata la conosce axe, e le sue
# sono oltre cento. Il locale italiano e' il posto dove axe scrive come
# si aggiusta.

def test_wcag_la_suite_non_legge_il_locale_vero():
    """Presidio della fixture `locale_axe_fisso`.

    Senza, la fixture sarebbe indistinguibile dalla sua assenza su una
    macchina dove `npm install` e' stato lanciato — cioe' su tutte
    quelle dove qualcuno lavora: i testi arriverebbero dal file vero e
    i test resterebbero verdi lo stesso. Un guardiano si rileva solo se
    qualcosa prova a passargli davanti, e qui a provarci e' questa
    asserzione: 103 regole invece di 2.
    """
    assert mars_wcag.testi_axe() == TESTI_AXE


def test_wcag_i_due_testi_axe_vengono_dal_locale():
    """Titolo e prescrizione, tutti e due dal locale — e' R44.

    Prima il `fix` veniva dal locale italiano e il titolo restava il
    `help` inglese che axe manda nella risposta: il referto diceva
    «Images must have alternative text» dentro un'interfaccia italiana,
    accanto a un fix che italiano lo era.

    Restano frasi DIVERSE, ed e' il punto della coppia: `help` dice che
    cosa deve valere, `description` che cosa fare perche' valga."""
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical",
          "help": "Images must have alternative text",
          "description": "Ensure <img> elements have alternative text",
          "nodes": [0]}], 1)
    rilievo = esito["findings"][0]
    assert rilievo["title"] == TESTI_AXE["image-alt"]["help"]
    assert rilievo["fix"] == TESTI_AXE["image-alt"]["description"]
    assert rilievo["title"] != rilievo["fix"]


def test_wcag_in_inglese_i_testi_axe_vengono_dalla_risposta():
    """Per l'inglese non c'e' un file di locale, e non serve: axe manda
    `help` e `description` gia' in inglese dentro la violazione.

    E' la ragione per cui `percorso_locale_axe("en")` e' vuoto: cercare
    un file che non esiste e dichiararne l'assenza segnalerebbe un
    difetto dove non ce n'e' uno."""
    assert mars_wcag.percorso_locale_axe("en") == ""
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical",
          "help": "Images must have alternative text",
          "description": "Ensure <img> elements have alternative text",
          "nodes": [0]}], 1, "en")
    rilievo = esito["findings"][0]
    assert rilievo["title"] == "Images must have alternative text"
    assert rilievo["fix"] == "Ensure <img> elements have alternative text"
    # E nessun rilievo di stato: non manca nulla.
    assert not [f for f in esito["findings"]
                if f["key"] == "wcag.status.no_fixes"]


def test_wcag_regola_che_il_locale_non_conosce_resta_nella_lingua_di_axe():
    """`axe.configure` permette regole aggiunte a mano: non sono tradotte.

    Meglio i testi inglesi di axe che quelli di un'altra regola, ed e'
    anche perche' `testi_axe` restituisce una mappa e non una lista.
    Il ripiego e' campo per campo, come in `mars_i18n.finding_texts`.
    """
    esito = mars_wcag.score_from_violations(
        [{"id": "regola-di-un-addon", "impact": "serious",
          "help": "Something must hold",
          "description": "Ensure something holds", "nodes": [0]}], 1)
    rilievo = esito["findings"][0]
    assert rilievo["title"] == "Something must hold"
    assert rilievo["fix"] == "Ensure something holds"


def test_wcag_senza_locale_lo_dichiara(monkeypatch):
    """Rilievi axe senza testi: si dichiara invece di lasciarli vuoti.

    E' il principio 2 — se manca, si ripiega e LO SI DICE — applicato
    a un file di dati la cui assenza non produce alcun errore: senza il
    rilievo di stato, un `fix` vuoto sembrerebbe un `fix` che non
    serviva.
    """
    monkeypatch.setattr(mars_wcag, "testi_axe", lambda lang="it": {})
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical", "help": "x", "nodes": [0]},
         {"id": "label", "impact": "moderate", "help": "y", "nodes": [0]}], 1)
    stato = [f for f in esito["findings"]
             if f["key"] == "wcag.status.no_fixes"]
    assert len(stato) == 1, "uno, non uno per regola"
    assert stato[0]["params"]["regole"] == 2
    assert stato[0]["params"]["lang"] == "it"
    assert stato[0]["severity"] == mars_core.SEV_INFO
    # Sta in testa, come wcag.status.partial: i rilievi sullo stato
    # della scansione precedono quelli sul sito.
    assert esito["findings"][0]["key"] == "wcag.status.no_fixes"


def test_wcag_il_locale_assente_non_tocca_il_punteggio(monkeypatch):
    """Perdere i testi non e' perdere la misura.

    E' la ragione per cui il locale si legge in Python e non lo si
    passa a `axe.configure` dentro la pagina: la' un file rotto farebbe
    fallire `axe.run`, e con lui l'intera area.

    Da U9.3 le `issues` invece CAMBIANO, ed e' voluto: la riga compatta
    porta il titolo tradotto, quindi senza locale torna quello inglese
    di axe. Prima non cambiavano perche' erano inglesi in entrambi i
    casi — cioe' il difetto R44 misurato al contrario.
    """
    violazioni = [{"id": "image-alt", "impact": "critical",
                   "help": "Images must have alternative text",
                   "description": "Ensure <img> elements have alt text",
                   "nodes": [0, 1]}]
    con = mars_wcag.score_from_violations(violazioni, 1)
    monkeypatch.setattr(mars_wcag, "testi_axe",
                        lambda lang="it": {})
    senza = mars_wcag.score_from_violations(violazioni, 1)
    assert con["score"] == senza["score"]
    assert con["rules_violated"] == senza["rules_violated"]

    def penalita(esito):
        return [f["params"]["penalty"] for f in esito["findings"]
                if f["key"].startswith("wcag.axe.")]

    assert penalita(con) == penalita(senza)
    # I testi sì: e' l'unica cosa che il locale porta.
    assert con["issues"] != senza["issues"]
    assert TESTI_AXE["image-alt"]["help"] in con["issues"][0]
    assert "Images must have alternative text" in senza["issues"][0]


def test_wcag_senza_violazioni_non_dichiara_il_locale(monkeypatch):
    """Il rilievo di stato esiste solo se costa qualcosa.

    Nessuna violazione, nessun fix da scrivere: dichiarare la mancanza
    di testi che non servivano sarebbe rumore in un referto pulito.
    """
    monkeypatch.setattr(mars_wcag, "testi_axe",
                        lambda lang="it": {})
    assert mars_wcag.score_from_violations([], 1)["findings"] == []


def test_wcag_no_fixes_non_espone_il_percorso_della_macchina(monkeypatch):
    """Un referto si consegna: la struttura delle directory non e' sua.

    Stessa regola per cui `detail` non porta mai il proxy o la chiave
    di ZAP (test_wapt_nessuna_credenziale_nei_rilievi).
    """
    monkeypatch.setattr(mars_wcag, "testi_axe", lambda lang="it": {})
    esito = mars_wcag.score_from_violations(
        [{"id": "image-alt", "impact": "critical", "help": "x",
          "nodes": [0]}], 1)
    percorso = mars_wcag.percorso_locale_axe("it")
    assert percorso not in json.dumps(esito["findings"])
    assert os.path.dirname(percorso) not in json.dumps(esito["findings"])


def test_wcag_il_lettore_del_locale_regge_un_file_che_non_c_e():
    """Nessuna eccezione: senza il file, i testi sono un dict vuoto."""
    assert mars_wcag._leggi_locale_axe("/non/esiste/mai.json") == {}


def test_wcag_il_lettore_del_locale_regge_un_file_che_non_e_json(tmp_path):
    """Un locale troncato o sovrascritto e' lo stesso caso di uno assente."""
    rotto = tmp_path / "it.json"
    rotto.write_text('{"rules": {"image-alt"', encoding="utf-8")
    assert mars_wcag._leggi_locale_axe(str(rotto)) == {}


def test_wcag_il_lettore_del_locale_ignora_le_regole_senza_descrizione(
        tmp_path):
    """Una voce senza `description` non diventa un fix vuoto.

    Distinzione che conta: una chiave presente col valore "" spegnerebbe
    `wcag.status.no_fixes` pur non avendo nulla da dire.
    """
    parziale = tmp_path / "it.json"
    parziale.write_text(json.dumps({"rules": {
        "a": {"description": "Assicurati di a", "help": "A"},
        "b": {"help": "B"},
        "c": "non un dict",
        "d": {},
    }}), encoding="utf-8")
    # `b` sopravvive col solo `help`: e' un titolo tradotto senza
    # prescrizione, e il `fix` ripiega su quello che ha detto axe.
    # `d`, che non ha nulla, non entra affatto — una chiave presente e
    # vuota spegnerebbe `wcag.status.no_fixes` senza avere nulla da dire.
    assert mars_wcag._leggi_locale_axe(str(parziale)) == {
        "a": {"description": "Assicurati di a", "help": "A"},
        "b": {"help": "B"}}


@pytest.mark.skipif(
    not os.path.exists(mars_wcag.percorso_locale_axe("it")),
    reason="axe-core non installato (npm install)")
def test_wcag_il_locale_vero_si_legge_e_copre_le_regole():
    """L'unico test che tocca `node_modules`, e per questo puo' saltare.

    Il resto della suite lavora sul locale fissato in conftest: qui si
    verifica che il file VERO abbia la forma che quel finto imita —
    altrimenti la fixture congelerebbe un'idea sbagliata del file, e
    nessun test se ne accorgerebbe.
    """
    testi = mars_wcag._leggi_locale_axe(mars_wcag.percorso_locale_axe("it"))
    assert len(testi) > 50, "un locale axe elenca un centinaio di regole"
    for regola, atteso in TESTI_AXE.items():
        assert testi[regola] == atteso, (
            "il locale di axe-core e' cambiato: rivedere TESTI_AXE")
    # Le `description` sono prescrizioni: e' cio' che le rende un `fix`.
    imperativi = [v["description"] for v in testi.values()
                  if v.get("description", "").startswith("Assicurati")]
    assert len(imperativi) > len(testi) * 0.9
    # E gli `help` in stragrande maggioranza NON sono prescrizioni:
    # dicono che cosa deve valere, ed e' la ragione per cui i due campi
    # non sono intercambiabili. Misurato sul locale 4.13.0: 100
    # `description` imperative su 103 regole, e 2 `help` — due voci in
    # cui Deque ha invertito i due campi (`landmark-unique` e
    # `presentation-role-conflict`). Sono le eccezioni del file vero,
    # non un difetto nostro, e il test dice "quasi nessuno" invece di
    # "nessuno" perche' e' quello che si misura.
    imperativi_sbagliati = [v for v in testi.values()
                            if v.get("help", "").startswith("Assicurati")]
    assert len(imperativi_sbagliati) < len(testi) * 0.05


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
# Peso reale di `is-crawlable` nella categoria SEO di Lighthouse:
# `default-config.js` lo scrive letteralmente `93 / 23`, col commento
# che spiega perche' — e' risolto in modo che quel solo fallimento
# faccia fallire la categoria (>= 31% del punteggio). Gli altri nove
# pesano 1, `structured-data` 0.
PESO_CRAWLABLE = 93 / 23


def _lhr(punteggio=0.27):
    """Un LHR fedele: gli undici audit SEO reali, coi pesi reali.

    Ricalcata su un referto vero prodotto dalla Lighthouse 13.4.1 di
    `node_modules` contro una pagina servita in locale. Fedele in tre
    punti che contano:

    - **undici** auditRefs nell'ordine di `default-config.js`, non sei;
    - i **pesi**, che prima mancavano del tutto: senza, ogni rilievo
      uscirebbe `info` e un test sulla gravita' passerebbe per il
      motivo sbagliato;
    - il peso **azzerato** sui non applicabili e sul manuale, che e'
      cio' che Lighthouse scrive nel LHR (`core/scoring.js`) e non cio'
      che sta nella configurazione;
    - le **`description`**, verbatim dal locale italiano di Lighthouse
      13.4.1, coi link Markdown dentro. Sono cio' che diventa il
      `detail` di un rilievo: riscriverle a mano vorrebbe dire
      inventare il Markdown che si dice di saper ripulire.

    Il punteggio non e' inventato: con questi pesi e questi esiti la
    media pesata di Lighthouse vale 3 / 11,043478 = 0,2717, che il suo
    arrotondamento a due decimali porta a **0,27**.
    """
    return {
        "lighthouseVersion": "13.4.1",
        "finalDisplayedUrl": "https://esempio.test/",
        "configSettings": {"formFactor": "mobile"},
        # Lighthouse gira SEMPRE per intero: `esegui_lighthouse` non
        # passa `--only-categories`, quindi tutte e cinque le categorie
        # sono nel LHR. I punteggi delle altre quattro vengono da un
        # run vero (lymphatechnologies.com, mobile, 13.4.1): senza,
        # `punteggi_categorie` verrebbe provata su un LHR che dichiara
        # una sola categoria, cioe' su una forma che non esiste.
        "categories": {
            "performance": {"id": "performance", "score": 0.56},
            "accessibility": {"id": "accessibility", "score": 0.97},
            "best-practices": {"id": "best-practices", "score": 0.96},
            "agentic-browsing": {"id": "agentic-browsing", "score": 1},
            "seo": {"score": punteggio, "auditRefs": [
                {"id": "is-crawlable", "weight": PESO_CRAWLABLE},
                {"id": "document-title", "weight": 1},
                {"id": "meta-description", "weight": 1},
                {"id": "http-status-code", "weight": 1},
                {"id": "link-text", "weight": 1},
                {"id": "crawlable-anchors", "weight": 1},
                # Non applicabili: Lighthouse azzera il peso, non la
                # configurazione, dove valgono 1.
                {"id": "robots-txt", "weight": 0},
                {"id": "image-alt", "weight": 1},
                {"id": "hreflang", "weight": 1},
                {"id": "canonical", "weight": 0},
                {"id": "structured-data", "weight": 0},
            ]},
        },
        "audits": {
            "is-crawlable": {
                "description": "I motori di ricerca non sono in grado di "
                               "includere le pagine nei risultati di ricerca "
                               "se non dispongono dell'autorizzazione per "
                               "eseguirne la scansione. [Scopri di più sulle "
                               "istruzioni dei crawler](https://developer.chro"
                               "me.com/docs/lighthouse/seo/is-crawlable/).",
                "title": "L'indicizzazione della pagina è bloccata",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table",
                            "items": [{"source": "X-Robots-Tag: noindex"}]}},
            "document-title": {
                "description": "Il titolo fornisce agli utenti di screen "
                               "reader una panoramica della pagina, mentre per"
                               " gli utenti di motori di ricerca è utile per "
                               "stabilire se una pagina è pertinente alla loro"
                               " ricerca. [Scopri di più sui titoli dei docume"
                               "nti](https://dequeuniversity.com/rules/axe/4.1"
                               "2/document-title).",
                "title": "Il documento non ha un elemento `<title>`",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table", "items": [
                    {"node": {"type": "node", "selector": "html",
                              "boundingRect": {"top": 0}}}]}},
            "meta-description": {
                "description": "Le meta descrizioni possono essere incluse nei"
                               " risultati di ricerca per riassumere "
                               "brevemente i contenuti della pagina. [Scopri "
                               "di più sulla meta descrizione](https://develop"
                               "er.chrome.com/docs/lighthouse/seo/meta-descrip"
                               "tion/).",
                "title": "Il documento non ha una meta descrizione",
                "score": 0, "scoreDisplayMode": "binary"},
            "http-status-code": {
                "description": "Le pagine con codici di stato HTTP non validi "
                               "potrebbero non essere indicizzate "
                               "correttamente. [Scopri di più sui codici di "
                               "stato HTTP](https://developer.chrome.com/docs/"
                               "lighthouse/seo/http-status-code/).",
                "title": "La pagina ha un codice di stato HTTP valido",
                "score": 1, "scoreDisplayMode": "binary"},
            # Otto elementi: e' l'unico audit che supera MAX_ELEMENTI,
            # e prima della fixture fedele quel troncamento non era
            # esercitato da nessun test.
            "link-text": {
                "description": "Il testo descrittivo dei link aiuta i motori "
                               "di ricerca a comprendere i tuoi contenuti. "
                               "[Scopri come rendere più accessibili i link](h"
                               "ttps://developer.chrome.com/docs/lighthouse/se"
                               "o/link-text/).",
                "title": "I link non hanno testo descrittivo",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table", "items": [
                    {"href": "/p%d" % i, "text": "clicca qui"}
                    for i in range(8)]}},
            "crawlable-anchors": {
                "description": "I motori di ricerca potrebbero usare gli "
                               "attributi `href` dei link per eseguire la "
                               "scansione dei siti web. Assicurati che "
                               "l'attributo `href` degli elementi anchor "
                               "rimandi a una destinazione appropriata per "
                               "consentire il rilevamento di un numero "
                               "maggiore di pagine del sito. [Scopri come "
                               "consentire la scansione dei link](https://supp"
                               "ort.google.com/webmasters/answer/9112205)",
                "title": "I link sono sottoponibili a scansione",
                "score": 1, "scoreDisplayMode": "binary"},
            "robots-txt": {
                "description": "Se il file robots.txt non è valido, i crawler "
                               "potrebbero non essere in grado di capire come "
                               "vuoi che il tuo sito web venga sottoposto a "
                               "scansione o indicizzato. [Scopri di più sul "
                               "file robots.txt](https://developer.chrome.com/"
                               "docs/lighthouse/seo/invalid-robots-txt/).",
                "title": "robots.txt è valido",
                "score": None, "scoreDisplayMode": "notApplicable"},
            "image-alt": {
                "description": "Gli elementi informativi dovrebbero mostrare "
                               "testo alternativo breve e descrittivo. Gli "
                               "elementi decorativi possono essere ignorati "
                               "con un attributo ALT vuoto. [Scopri di più "
                               "sull'attributo `alt`](https://dequeuniversity."
                               "com/rules/axe/4.12/image-alt).",
                "title": "Gli elementi immagine non hanno attributi `[alt]`",
                "score": 0, "scoreDisplayMode": "binary",
                "details": {"type": "table", "items": [
                    {"node": {"selector": "body > img"}},
                    {"node": {"selector": "body > img"}}]}},
            "hreflang": {
                "description": "I link hreflang indicano ai motori di ricerca "
                               "quale versione di una pagina devono elencare "
                               "nei risultati di ricerca per una determinata "
                               "lingua o regione. [Scopri di più su `hreflang`"
                               "](https://developer.chrome.com/docs/lighthouse"
                               "/seo/hreflang/).",
                "title": "Il documento ha un `hreflang` valido",
                "score": 1, "scoreDisplayMode": "binary"},
            "canonical": {
                "description": "I link canonici suggeriscono quale URL "
                               "mostrare nei risultati di ricerca. [Scopri di "
                               "più sui link canonici](https://developer.chrom"
                               "e.com/docs/lighthouse/seo/canonical/).",
                "title": "Il documento ha un elemento `rel=canonical` valido",
                "score": None, "scoreDisplayMode": "notApplicable"},
            "structured-data": {
                "description": "Esegui lo [Strumento di test per i dati strutt"
                               "urati](https://developers.google.com/search/do"
                               "cs/appearance/structured-data/) per "
                               "convalidare i dati strutturati. [Scopri di più"
                               " sui dati strutturati](https://developer.chrom"
                               "e.com/docs/lighthouse/seo/structured-data/).",
                "title": "Dati strutturati validi",
                "score": None, "scoreDisplayMode": "manual"},
        },
    }


def _lhr_tutto_pesato(punteggio=0.23):
    """La stessa pagina senza audit non applicabili: Sigma pesi = 13,043.

    Serve perche' nella fixture principale la somma dei pesi (11,043) e'
    a filo del NUMERO di auditRefs (11): una mutazione che usasse il
    conteggio invece della somma resterebbe dentro il mezzo punto di
    tolleranza dell'invariante, e passerebbe inosservata. Qui i due
    numeri distano abbastanza da renderla rumorosa.
    """
    lhr = _lhr(punteggio)
    for ref in lhr["categories"]["seo"]["auditRefs"]:
        if ref["id"] in ("robots-txt", "canonical"):
            ref["weight"] = 1
    for nome in ("robots-txt", "canonical"):
        lhr["audits"][nome].update(score=0, scoreDisplayMode="binary")
    return lhr


def test_seo_estrae_tutti_i_controlli_non_solo_i_falliti():
    """Il referto conteneva il solo punteggio complessivo.

    42/100 non dice QUALE controllo sia fallito, ed elencare i soli
    fallimenti non direbbe che cosa sia stato guardato: un punteggio
    pieno resterebbe indistinguibile da un controllo mai eseguito.
    """
    controlli = mars_seo.estrai_audit(_lhr())
    assert [c["id"] for c in controlli] == [
        "is-crawlable", "document-title", "meta-description",
        "http-status-code", "link-text", "crawlable-anchors", "robots-txt",
        "image-alt", "hreflang", "canonical", "structured-data"]
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
    assert esito["passed"] + esito["failed"] + esito["manual"] == 11


def test_seo_riassume_con_conteggi_e_strumento():
    esito = mars_seo.riassumi(_lhr())
    assert esito["score"] == 27.0
    # Tre superati, cinque falliti, tre non misurati: due non
    # applicabili piu' il manuale.
    assert (esito["passed"], esito["failed"], esito["manual"]) == (3, 5, 3)
    assert esito["tool"] == "Lighthouse 13.4.1"
    # Un referto mobile e uno desktop non sono confrontabili.
    assert esito["form_factor"] == "mobile"
    assert esito["audited_url"] == "https://esempio.test/"


def _finto_lighthouse(cartella) -> str:
    """Un eseguibile finto dentro `cartella`, come lo lascia npm."""
    comando = cartella / "lighthouse"
    comando.write_text("#!/bin/sh\nexit 0\n")
    comando.chmod(0o755)
    return str(comando)


def test_seo_lighthouse_si_cerca_anche_in_node_modules(monkeypatch, tmp_path):
    """`package.json` dichiara `lighthouse` fra le dipendenze, quindi un
    `npm install` senza `-g` lo mette in `node_modules/.bin` e **non** nel
    PATH: prima di R32 il referto diceva «non trovato» proprio a chi aveva
    seguito il package.json del progetto."""
    monkeypatch.setattr(mars_seo, "LIGHTHOUSE_BIN", str(tmp_path))
    # Il `which` VERO: qui si esercita la ricerca, non il finto della
    # fixture — che risponde None a tutto e renderebbe il test vacuo.
    # Il PATH resta comunque svuotato, perche' `path=` lo scavalca.
    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome, path=None:
                        WHICH_VERO(nome, path=path) if path else None)

    # Senza il file locale l'area resta non misurata, com'era.
    assert mars_seo.trova_lighthouse() is None

    percorso = _finto_lighthouse(tmp_path)
    assert mars_seo.trova_lighthouse() == percorso

    # Un file NON eseguibile non e' un comando: non lo si annuncia.
    (tmp_path / "lighthouse").chmod(0o644)
    assert mars_seo.trova_lighthouse() is None


def test_seo_il_path_vince_su_node_modules(monkeypatch, tmp_path):
    """Il PATH e' la scelta esplicita di chi ha installato lo strumento a
    livello di sistema; `node_modules` e' il ripiego, non il contrario."""
    _finto_lighthouse(tmp_path)
    monkeypatch.setattr(mars_seo, "LIGHTHOUSE_BIN", str(tmp_path))
    monkeypatch.setattr(
        mars_seo.shutil, "which",
        lambda nome, path=None: None if path else "/usr/bin/lighthouse")
    assert mars_seo.trova_lighthouse() == "/usr/bin/lighthouse"


def test_seo_la_cartella_locale_e_quella_che_npm_usa():
    """Il valore della costante, non solo il fatto che venga consultata.

    Tutti gli altri test sostituiscono `LIGHTHOUSE_BIN` con una directory
    finta, quindi nessuno lo guarda: una mutazione da `.bin` a `bin` — la
    directory che npm NON usa — passava verde. E' la lezione di U1.4, una
    costante mai confrontata con il suo valore.

    Risolto da `__file__` e non dalla directory di lavoro, per la ragione
    di R11: lanciare l'audit da un'altra cartella non deve spostare la
    ricerca."""
    atteso = os.path.join(os.path.dirname(os.path.abspath(mars_seo.__file__)),
                          "node_modules", ".bin")
    assert mars_seo.LIGHTHOUSE_BIN == atteso
    assert os.path.isabs(mars_seo.LIGHTHOUSE_BIN)


def test_seo_la_ricerca_locale_passa_da_which(monkeypatch, tmp_path):
    """Il vincolo che tiene la suite indipendente dalla macchina.

    `node_modules/.bin/lighthouse` esiste su questa macchina e non su un
    clone appena fatto. La fixture della suite neutralizza `shutil.which`:
    se la ricerca locale usasse un secondo meccanismo — un `os.access` sul
    percorso composto — le sfuggirebbe, e la suite lancerebbe Lighthouse
    per davvero. Misurato quando e' successo: 263 secondi invece di 15, e
    quattro golden rossi perche' l'area SEO risultava misurata."""
    _finto_lighthouse(tmp_path)
    monkeypatch.setattr(mars_seo, "LIGHTHOUSE_BIN", str(tmp_path))
    chiamate = []

    def spia(nome, path=None):
        chiamate.append(path)
        return None

    monkeypatch.setattr(mars_seo.shutil, "which", spia)
    assert mars_seo.trova_lighthouse() is None, \
        "il file c'e' ed e' eseguibile: se non passa da which, lo trova"
    assert chiamate == [None, str(tmp_path)], \
        "prima il PATH, poi node_modules/.bin, entrambi da which"


def test_seo_ogni_rilievo_dichiara_la_pagina_misurata():
    """L'area la sapeva da sempre — `audited_url` — ma solo a livello
    d'area: un rilievo letto staccato dal referto, nel CSV o nel piano,
    non diceva a che pagina si riferisse (R47).

    E' quella che LIGHTHOUSE dichiara di aver misurato, cioe' l'arrivo
    dopo i redirect: scrivere l'URL di partenza significherebbe
    attribuire la misura a una pagina diversa da quella misurata."""
    esito = mars_seo.riassumi(_lhr())
    assert esito["findings"], "senza rilievi il test passerebbe a vuoto"
    for rilievo in esito["findings"]:
        assert rilievo["params"]["urls"] == ["https://esempio.test/"]


def test_seo_senza_url_dichiarato_il_rilievo_non_ne_inventa_uno():
    """`finalDisplayedUrl` e `finalUrl` possono mancare entrambi: la
    chiave allora non c'e', che e' diverso da una lista vuota — e da
    una lista con dentro la stringa vuota, che il CSV renderebbe come
    una pagina chiamata «»."""
    lhr = _lhr()
    lhr.pop("finalDisplayedUrl", None)
    lhr.pop("finalUrl", None)
    esito = mars_seo.riassumi(lhr)
    assert esito["audited_url"] is None
    assert all("urls" not in r["params"] for r in esito["findings"])


def test_seo_issues_contengono_i_falliti_con_il_dettaglio():
    issues = mars_seo.riassumi(_lhr())["issues"]
    assert any("X-Robots-Tag: noindex" in i for i in issues)
    assert any(mars_seo.PREFISSO_NON_MISURATO["manual"] in i
               for i in issues)
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
                        lambda nome, path=None: "/usr/bin/lighthouse")
    monkeypatch.setattr(mars_seo.subprocess, "run", finto_run)
    esito = mars_seo.audit({"url": "https://esempio.test/"})
    assert "--locale=it" in visti["argv"]
    assert esito["score"] == 27.0
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
                        lambda nome, path=None: "/usr/bin/lighthouse")
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
                        lambda nome, path=None: "/usr/bin/lighthouse")
    for grezzo, atteso in ((0.92, 92.0), (0, 0.0), (1, 100.0)):
        monkeypatch.setattr(
            mars_seo.subprocess, "run",
            lambda *a, _g=grezzo, **k: types.SimpleNamespace(
                stdout=json.dumps({"categories": {"seo": {"score": _g}}})))
        assert mars_seo.audit({"url": "https://x/"})["score"] == atteso


# --- U1.7: i rilievi di mars_seo come dato -----------------------------
#
# Prima di U1.7 il modulo leggeva `score`, `scoreDisplayMode` e il
# `weight` di auditRefs e li buttava via, e la fixture non aveva pesi:
# nessun test poteva accorgersi della differenza fra un controllo che
# fa fallire la categoria da solo e uno che vale un nono.

def _findings(lhr) -> dict:
    """I rilievi di un LHR, indicizzati per chiave."""
    return {f["key"]: f for f in mars_seo.riassumi(lhr)["findings"]}


def test_seo_la_voce_porta_punteggio_modo_e_peso():
    """I tre campi che si perdevano, coi nomi di Lighthouse.

    Sono suoi valori verbatim, come `id` e `title`; `passed` e `manual`
    portano nomi nostri perche' sono giudizi nostri."""
    per_id = {c["id"]: c for c in mars_seo.estrai_audit(_lhr())}
    assert per_id["is-crawlable"]["score"] == 0
    assert per_id["is-crawlable"]["scoreDisplayMode"] == "binary"
    assert per_id["is-crawlable"]["weight"] == PESO_CRAWLABLE
    assert per_id["canonical"]["scoreDisplayMode"] == "notApplicable"
    assert per_id["canonical"]["score"] is None


def test_seo_il_peso_viene_dal_referto_non_dalla_configurazione():
    """Lighthouse azzera il peso dei non applicabili prima di scriverlo
    nel LHR; nella configurazione quegli stessi audit pesano 1.

    Leggerlo dalla configurazione farebbe uscire `critical` un
    `is-crawlable` che Lighthouse non ha nemmeno potuto applicare."""
    per_chiave = _findings(_lhr())
    assert per_chiave["seo.lh.canonical"]["params"]["lh_weight"] == 0.0
    assert per_chiave["seo.lh.canonical"]["params"]["lh_weight_total"] == (
        pytest.approx(PESO_CRAWLABLE + 7))


def test_seo_un_peso_assente_non_fa_cadere_l_area():
    """Un LHR senza pesi degrada a `info`, non a un'importanza inventata,
    e soprattutto non fa sparire l'area."""
    lhr = _lhr()
    for ref in lhr["categories"]["seo"]["auditRefs"]:
        del ref["weight"]
    rilievi = _findings(lhr)
    assert all(f["severity"] == SEV_INFO for f in rilievi.values())
    assert all("penalty" not in f["params"] for f in rilievi.values())
    assert mars_seo.riassumi(lhr)["score"] == 27.0, "il punteggio non cambia"


@pytest.mark.parametrize("valore", ["molto", None, {}, [1]])
def test_seo_un_peso_illeggibile_non_solleva(valore):
    """`estrai_audit` gira dentro il try di audit(), dove TypeError e'
    catturato: un peso malformato farebbe sparire l'intera area con
    "Lighthouse non riuscito" — R22 sotto altra forma."""
    lhr = _lhr()
    for ref in lhr["categories"]["seo"]["auditRefs"]:
        ref["weight"] = valore
    assert mars_seo.riassumi(lhr)["score"] == 27.0


def test_seo_un_controllo_superato_non_e_un_rilievo():
    """`severita_lighthouse` decide su modo e peso e NON guarda lo
    score: senza il filtro, un sito perfetto produrrebbe nove
    `warning`."""
    rilievi = _findings(_lhr())
    for superato in ("http-status-code", "crawlable-anchors", "hreflang"):
        assert "seo.lh.%s" % superato.replace("-", "_") not in rilievi


def test_seo_findings_e_issues_sono_la_stessa_lista():
    """Due viste dello stesso referto: stessa cardinalita', stesso
    ordine, altrimenti non si possono leggere affiancate."""
    esito = mars_seo.riassumi(_lhr())
    assert len(esito["findings"]) == len(esito["issues"]) == 8
    assert [f["params"]["rule"] for f in esito["findings"]] == [
        # prima i falliti, nell'ordine degli auditRefs...
        "is-crawlable", "document-title", "meta-description", "link-text",
        "image-alt",
        # ...poi i non misurati, nello stesso ordine.
        "robots-txt", "canonical", "structured-data"]


def test_seo_solo_is_crawlable_puo_essere_critico():
    """E' l'unico audit che da solo fa fallire la categoria: pesa 93/23,
    cioe' il 31% del totale, e LH_PESO_CRITICO e' tarata su quello."""
    rilievi = _findings(_lhr())
    crawlable = rilievi["seo.lh.is_crawlable"]
    assert (crawlable["severity"], crawlable["weight"]) == (SEV_CRITICAL, 2.0)
    altri = [f for k, f in rilievi.items() if k != "seo.lh.is_crawlable"]
    assert all(f["severity"] != SEV_CRITICAL for f in altri)


def test_seo_un_audit_da_peso_uno_e_un_avvertimento():
    rilievo = _findings(_lhr())["seo.lh.document_title"]
    assert (rilievo["severity"], rilievo["weight"]) == (SEV_WARNING, 1.0)


def test_seo_un_non_misurato_e_info_e_non_costa_punti():
    """Manuali e non applicabili non sono difetti del sito: `penalty`
    assente, non zero. Zero direbbe "difetto che qui non costa"."""
    rilievi = _findings(_lhr())
    for chiave in ("seo.lh.robots_txt", "seo.lh.canonical",
                   "seo.lh.structured_data"):
        assert rilievi[chiave]["severity"] == SEV_INFO
        assert "penalty" not in rilievi[chiave]["params"]


def test_seo_un_non_applicabile_non_e_un_manuale():
    """Le issues li chiamavano entrambi "da verificare a mano", ed e'
    una frase falsa: Lighthouse dice "non applicabile", e usa il titolo
    del SUCCESSO perche' `failureTitle` scatta solo sotto 0,9 — quindi
    la riga affermava il contrario del vero **due volte**.

    U1.7 aveva corretto il titolo del rilievo e lasciato la issue
    com'era, perche' cambiarla era una regressione di testo dentro un
    commit di sola forma. **Questo test asseriva quella riga**; R40 la
    corregge, e le due viste ora dicono la stessa cosa."""
    rilievi = _findings(_lhr())
    assert rilievi["seo.lh.canonical"]["params"]["mode"] == "notApplicable"
    assert rilievi["seo.lh.canonical"]["title"].startswith(
        "Non applicabile a questa pagina: ")
    assert rilievi["seo.lh.structured_data"]["params"]["mode"] == "manual"
    assert rilievi["seo.lh.structured_data"]["title"].startswith(
        "Da verificare a mano: ")
    # E la issue dice lo stesso modo del rilievo, non piu' un altro.
    issues = mars_seo.riassumi(_lhr())["issues"]
    assert any(i.startswith("[Lighthouse] Non applicabile a questa pagina: "
                            "Il documento ha un elemento") for i in issues)
    assert not any("da verificare a mano" in i for i in issues), \
        "in minuscolo era la vecchia riga, quella che diceva il falso"


def test_seo_un_audit_in_errore_non_e_un_difetto_del_sito():
    """Un audit che Lighthouse non e' riuscito a eseguire e' un guasto
    dello strumento. `error` NON e' fra i modi a cui Lighthouse azzera
    il peso, quindi senza la correzione in mars_core un `is-crawlable`
    non riuscito sarebbe uscito `critical` — R21.

    Si usa `structured-data`, l'unico a peso zero: un audit pesato in
    errore annulla il punteggio di categoria e non arriverebbe qui."""
    lhr = _lhr()
    lhr["audits"]["structured-data"]["scoreDisplayMode"] = "error"
    lhr["audits"]["structured-data"]["errorMessage"] = "boom"
    rilievo = _findings(lhr)["seo.lh.structured_data"]
    assert rilievo["severity"] == SEV_INFO
    assert rilievo["title"].startswith("Controllo non eseguito da Lighthouse")
    assert "penalty" not in rilievo["params"]
    # E qui la divergenza deliberata fra le due viste, fissata perche'
    # non la si chiuda per distrazione: la VOCE lo classifica fallito,
    # perche' MODI_NON_MISURATI_VOCE si ferma a due modi. Allargarla
    # sposterebbe i CONTEGGI, ed e' una decisione a se'.
    esito = mars_seo.riassumi(lhr)
    assert (esito["passed"], esito["failed"], esito["manual"]) == (3, 6, 2)
    # Il TESTO invece si e' allineato con R40, e le due meta' vanno
    # tenute distinte: la issue diceva "Dati strutturati validi" di un
    # controllo mai eseguito, cioe' il titolo del successo — perche'
    # `failureTitle` scatta solo sotto 0,9. Il conteggio resta dov'era,
    # l'affermazione falsa no.
    assert ("[Lighthouse] Controllo non eseguito da Lighthouse: "
            "Dati strutturati validi") in esito["issues"]


def test_seo_un_informative_resta_un_superato_nella_voce():
    """La voce classifica su due modi, mars_core su quattro, ed e'
    voluto: allargare la tupla della voce sposterebbe i conteggi
    passed/failed/manual e la riga "N superati, M falliti" del referto.

    Un `informative` ha `score: 1` per costruzione, quindi resta
    superato e non produce alcun rilievo. Registrato in R40."""
    lhr = _lhr()
    lhr["audits"]["hreflang"]["scoreDisplayMode"] = "informative"
    per_id = {c["id"]: c for c in mars_seo.estrai_audit(lhr)}
    assert per_id["hreflang"]["passed"] is True
    assert per_id["hreflang"]["manual"] is False
    assert "seo.lh.hreflang" not in _findings(lhr)


def test_seo_le_chiavi_hanno_tre_segmenti_e_niente_trattini():
    """Gli id di Lighthouse sono in kebab-case: un trattino non rompe
    la profondita' fissa, ma `chiave_esterna` normalizza il dato
    esterno e l'id grezzo resta nei params."""
    rilievi = _findings(_lhr())
    for chiave, rilievo in rilievi.items():
        parti = chiave.split(".")
        assert parti[0] == AREA_PREFIX["mars_seo"]
        assert len(parti) == 3
        assert "-" not in chiave
    assert rilievi["seo.lh.is_crawlable"]["params"]["rule"] == \
        "is-crawlable", "l'id grezzo resta fedele"


def test_seo_source_severity_resta_vuoto():
    """Lighthouse una scala di gravita' non ce l'ha: ha punteggio, modo
    e peso. `[Lighthouse]` e' un'etichetta di STRUMENTO, e metterla in
    un campo di gravita' sarebbe peggio del vuoto."""
    assert all(f["source_severity"] == ""
               for f in _findings(_lhr()).values())


def test_seo_gli_ingressi_della_gravita_restano_nel_dato():
    """La severita' e' una derivazione nostra: cio' che la rende
    verificabile sono i suoi ingressi, tutti e quattro."""
    params = _findings(_lhr())["seo.lh.is_crawlable"]["params"]
    assert params["mode"] == "binary"
    assert params["score"] == 0
    assert params["lh_weight"] == PESO_CRAWLABLE
    assert params["lh_weight_total"] == pytest.approx(PESO_CRAWLABLE + 7)


@pytest.mark.parametrize("fixture, punteggio", [
    ("_lhr", 27.0),
    # Sigma pesi 13,043 contro 11 auditRefs: qui usare il conteggio
    # invece della somma si vede.
    ("_lhr_tutto_pesato", 23.0),
])
def test_seo_le_penalita_sommano_a_cento_meno_il_punteggio(fixture,
                                                           punteggio):
    """L'invariante piu' forte della voce: lega il nostro calcolo al
    numero che ha scritto Lighthouse.

    La sua media pesata e' lineare, quindi il contributo di ogni audit
    e' esatto e additivo. Lo scarto ammesso e' mezzo punto, ed e'
    interamente l'arrotondamento a due decimali che Lighthouse applica
    al punteggio di categoria."""
    lhr = {"_lhr": _lhr, "_lhr_tutto_pesato": _lhr_tutto_pesato}[fixture]()
    esito = mars_seo.riassumi(lhr)
    assert esito["score"] == punteggio
    somma = sum(f["params"].get("penalty", 0.0) for f in esito["findings"])
    assert abs(somma - (100 - esito["score"])) <= 0.5


def test_seo_la_penalita_e_la_quota_del_peso():
    """I valori, non solo la loro relazione: l'invariante resta verde
    anche se i due lati cambiano insieme (lezione di U1.4)."""
    rilievi = _findings(_lhr())
    totale = PESO_CRAWLABLE + 7
    assert rilievi["seo.lh.is_crawlable"]["params"]["penalty"] == \
        pytest.approx(PESO_CRAWLABLE / totale * 100)
    assert rilievi["seo.lh.document_title"]["params"]["penalty"] == \
        pytest.approx(1 / totale * 100)
    # ...e il piu' pesante costa piu' del quadruplo di uno qualunque.
    assert (rilievi["seo.lh.is_crawlable"]["params"]["penalty"]
            > 4 * rilievi["seo.lh.document_title"]["params"]["penalty"])


def test_seo_senza_pesi_nessuna_penalita_e_nessuna_divisione_per_zero():
    """Il caso peggiore della degradazione: se Lighthouse smettesse di
    scrivere `weight`, il segnale di recupero dell'area si azzererebbe
    in silenzio. `lh_weight_total: 0.0` e' cio' che lo dichiara."""
    lhr = _lhr()
    for ref in lhr["categories"]["seo"]["auditRefs"]:
        ref["weight"] = 0
    rilievi = _findings(lhr)
    assert rilievi, "i rilievi ci sono comunque"
    assert all("penalty" not in f["params"] for f in rilievi.values())
    assert all(f["params"]["lh_weight_total"] == 0.0
               for f in rilievi.values())


def test_seo_un_ref_fantasma_non_fa_cadere_l_area():
    """Un auditRef il cui id non compare fra gli audits da' score None e
    non e' ne' superato ne' manuale: `1 - None` solleverebbe TypeError,
    che l'except di audit() cattura facendo sparire l'intera area."""
    esito = mars_seo.riassumi({
        "categories": {"seo": {"score": 0.5, "auditRefs": [
            {"id": "fantasma", "weight": 1}]}}, "audits": {}})
    assert esito["score"] == 50.0
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "seo.lh.fantasma"
    assert "penalty" not in rilievo["params"], "senza score non e' calcolabile"


def test_seo_gli_elementi_incriminati_entrano_nei_params():
    """Lighthouse dice anche DOVE, e il troncamento a MAX_ELEMENTI e'
    quello della vista: prima della fixture fedele nessun audit ne
    aveva abbastanza da esercitarlo."""
    rilievi = _findings(_lhr())
    assert rilievi["seo.lh.is_crawlable"]["params"]["items"] == [
        "X-Robots-Tag: noindex"]
    # I VALORI, non il confronto con la costante: `len(items) ==
    # MAX_ELEMENTI` e' circolare — cambiando la costante cambiano
    # entrambi i lati e il test resta verde. E' la lezione di U1.4.
    assert mars_seo.MAX_ELEMENTI == 5
    assert rilievi["seo.lh.link_text"]["params"]["items"] == [
        "/p0", "/p1", "/p2", "/p3", "/p4"], "otto elementi, cinque riportati"


# --- R40: la categoria non calcolabile, e i buchi di _descrivi_item ----

def _lhr_con_audit_in_errore() -> dict:
    """Un LHR reale nella forma che azzera la categoria.

    Lighthouse toglie dalla media il peso degli audit non applicabili,
    informativi e manuali, ma **non** quello di un audit andato in
    `error` (`core/scoring.js`): il suo `score: null` sopravvive al
    filtro e annulla il punteggio dell'intera categoria. Gli altri
    dieci restano misurati perfettamente.
    """
    lhr = _lhr()
    lhr["categories"]["seo"]["score"] = None
    lhr["audits"]["hreflang"] = {
        "title": "Il documento ha un `hreflang` valido",
        "description": "Descrizione.",
        "score": None, "scoreDisplayMode": "error",
        "errorMessage": "Required Hreflang gatherer did not run."}
    return lhr


def test_seo_una_categoria_non_calcolata_non_butta_gli_audit_misurati():
    """R40: `riassumi` usciva al primo `if` senza mai chiamare
    `estrai_audit`, mentre nel LHR c'erano dieci controlli misurati.

    Un audit in errore su undici azzera la CATEGORIA, non la
    misurazione: buttare via anche gli altri dieci e' perdere dati che
    Lighthouse ha prodotto e che sono gia' stati pagati col tempo del
    run."""
    esito = mars_seo.riassumi(_lhr_con_audit_in_errore())

    # Il punteggio resta None: calcolarne uno dagli audit leggibili
    # sarebbe inventare la categoria che Lighthouse si e' rifiutata di
    # calcolare.
    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert len(esito["audits"]) == 11
    chiavi = {f["key"] for f in esito["findings"]}
    assert "seo.status.not_scored" in chiavi
    assert "seo.lh.document_title" in chiavi, "i dieci misurati ci sono"


def test_seo_una_categoria_non_calcolata_e_illeggibile_resta_muta():
    """L'altro caso, che va tenuto distinto: non calcolabile **e** nulla
    da leggere. Un `audits` vuoto nella scheda d'area non e' come un
    `audits` con dieci controlli, e la vista HTML mostra l'elenco dei
    controlli AL POSTO dei rilievi."""
    esito = mars_seo.riassumi({"categories": {"seo": {"score": None}}})
    assert esito["score"] is None
    assert [f["key"] for f in esito["findings"]] == ["seo.status.not_scored"]
    assert not esito.get("audits")


def test_seo_le_issues_dei_non_misurati_dicono_il_modo_giusto():
    """R40: «da verificare a mano» detto a un `notApplicable`.

    Lighthouse usa `failureTitle` solo quando `score < 0.9`, quindi un
    controllo non misurato porta il titolo del SUCCESSO: la issue di
    una pagina senza canonical recitava «da verificare a mano: Il
    documento ha un elemento `rel=canonical` valido», che afferma il
    contrario del vero due volte. U1.7 aveva corretto il titolo del
    RILIEVO; qui si allinea la issue, che e' la vista compatta dello
    stesso fatto."""
    issues = mars_seo.riassumi(_lhr())["issues"]
    canonical = [i for i in issues if "rel=canonical" in i]
    assert canonical, "il LHR fedele ne ha uno notApplicable"
    assert canonical[0].startswith(
        "[Lighthouse] %s:" % mars_seo.PREFISSO_NON_MISURATO["notApplicable"])
    manuali = [i for i in issues if "Dati strutturati" in i]
    assert manuali[0].startswith(
        "[Lighthouse] %s:" % mars_seo.PREFISSO_NON_MISURATO["manual"])


def test_seo_un_audit_in_errore_non_si_annuncia_come_riuscito():
    """Lo stesso difetto della casella 2, sul modo `error`.

    Un audit andato in errore ha `score: null`, quindi `failureTitle`
    non scatta e il titolo e' quello del SUCCESSO: la issue recitava
    «Il documento ha un `hreflang` valido» per un controllo che non e'
    stato eseguito affatto. Il rilievo lo diceva gia' («Controllo non
    eseguito da Lighthouse»), la issue no — ed e' esattamente
    l'asimmetria che questa voce toglie.

    Il modo NON entra in `MODI_NON_MISURATI_VOCE`: allargare quella
    tupla sposterebbe i conteggi passed/failed/manual, che e' un'altra
    decisione. Qui cambia solo il TESTO."""
    esito = mars_seo.riassumi(_lhr_con_audit_in_errore())
    riga = [i for i in esito["issues"] if "hreflang" in i][0]
    assert riga.startswith(
        "[Lighthouse] %s:" % mars_seo.PREFISSO_NON_MISURATO["error"])
    # I conteggi restano dov'erano: l'errore e' fra i falliti, com'era.
    assert mars_seo.MODI_NON_MISURATI_VOCE == ("manual", "notApplicable")


def test_seo_il_meta_che_blocca_la_scansione_non_e_piu_una_riga_vuota():
    """R40, il buco piu' pesante: `is-crawlable` bloccato da un
    `<meta robots noindex>` porta un `source` che e' un **NodeValue**,
    non una stringa, e `_descrivi_item` vi cercava `url` e `value`.

    Il campo giusto e' `snippet`, che Lighthouse sovrascrive proprio
    con il tag incriminato (`handleMetaElement` in
    core/audits/seo/is-crawlable.js): e' il caso piu' grave della
    categoria, e usciva come stringa vuota."""
    item = {"source": {"type": "node", "selector": "head > meta",
                       "snippet": '<meta name="robots" content="noindex" />',
                       "boundingRect": {"top": 0}}}
    assert mars_seo._descrivi_item(item) == \
        '<meta name="robots" content="noindex" />'


def test_seo_un_errore_di_robots_txt_dice_riga_e_motivo():
    """Gli item di `robots-txt` sono `{index, line, message}` e non
    hanno ne' `source` ne' `node`: uscivano tutti come stringa vuota,
    cioe' l'audit diceva «ci sono errori» e nessuno di quali."""
    item = {"index": "12", "line": "Disallow /admin",
            "message": "Syntax not understood"}
    assert mars_seo._descrivi_item(item) == \
        "12: Disallow /admin — Syntax not understood"


def test_seo_gli_hreflang_invalidi_portano_le_proprie_ragioni():
    """`hreflang` mette il MOTIVO nei `subItems`, non nella riga: senza,
    resta il tag e non si sa che cosa abbia di sbagliato."""
    item = {"source": '<link rel="alternate" hreflang="xx" href="/x" />',
            "subItems": {"type": "subitems",
                         "items": [{"reason": "Codice lingua non valido"},
                                   {"reason": "URL non assoluto"}]}}
    assert mars_seo._descrivi_item(item) == (
        '<link rel="alternate" hreflang="xx" href="/x" /> '
        "(Codice lingua non valido; URL non assoluto)")


def test_seo_un_item_senza_nulla_da_dire_resta_vuoto():
    """Il verso opposto: `_descrivi_item` non deve inventare un testo
    da un item che non ne porta. La stringa vuota viene poi filtrata da
    `estrai_audit`, ed e' il modo in cui l'elenco dice «non lo so»."""
    assert mars_seo._descrivi_item({"boundingRect": {"top": 0}}) == ""


@pytest.mark.parametrize("chiave, prepara", [
    ("seo.status.no_tool", "assente"),
    ("seo.status.timeout", "timeout"),
    ("seo.status.failed", "guasto"),
    ("seo.status.not_scored", "non_calcolata"),
])
def test_seo_ogni_ramo_non_misurato_porta_un_solo_rilievo(monkeypatch,
                                                          chiave, prepara):
    """Un'area non misurata deve comunque comparire negli elenchi che le
    fasi successive costruiranno sui findings: senza, sparisce."""
    if prepara != "assente":
        monkeypatch.setattr(mars_seo.shutil, "which",
                            lambda nome, path=None: "/usr/bin/lighthouse")
    if prepara == "timeout":
        def run(*a, **k):
            raise subprocess.TimeoutExpired("lighthouse", 120)
    elif prepara == "guasto":
        def run(*a, **k):
            raise subprocess.CalledProcessError(1, "lighthouse")
    elif prepara == "non_calcolata":
        def run(*a, **k):
            return types.SimpleNamespace(
                stdout='{"categories":{"seo":{"score":null}}}')
    else:
        monkeypatch.setattr(mars_seo.shutil, "which", lambda nome, path=None: None)

        def run(*a, **k):
            raise AssertionError("non si deve arrivare qui")
    monkeypatch.setattr(mars_seo.subprocess, "run", run)

    esito = mars_seo.audit({"url": "https://x/"})
    assert esito["score"] is None and esito["status"] == "unavailable"
    assert [f["key"] for f in esito["findings"]] == [chiave]
    rilievo = esito["findings"][0]
    assert rilievo["severity"] == SEV_INFO
    assert "penalty" not in rilievo["params"]


def test_seo_il_fallimento_dice_quale(monkeypatch):
    """Quattro eccezioni condividono la chiave — sono gia' indistinte
    nella issue — ma `detail` dice quale, altrimenti la diagnosi si
    perde."""
    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome, path=None: "/usr/bin/lighthouse")
    monkeypatch.setattr(mars_seo.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(
                            stdout="non e' json"))
    rilievo = mars_seo.audit({"url": "https://x/"})["findings"][0]
    assert rilievo["key"] == "seo.status.failed"
    assert rilievo["detail"] == "JSONDecodeError"


def test_seo_i_findings_arrivano_al_referto(monkeypatch):
    """Il modulo puo' produrli perfetti e build_report buttarli via:
    copia una lista chiusa di chiavi."""
    from mars_report import build_report
    monkeypatch.setattr(mars_seo.shutil, "which",
                        lambda nome, path=None: "/usr/bin/lighthouse")
    monkeypatch.setattr(mars_seo.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(
                            stdout=json.dumps(_lhr())))
    esito = mars_seo.audit({"url": "https://x/"})
    referto = build_report({"mars_seo": esito}, {"url": "https://x/"})
    area = [a for a in referto["areas"] if a["module"] == "mars_seo"][0]
    assert area["findings"] == esito["findings"]
    assert all(f["key"].startswith("seo.") for f in area["findings"])
    # e il referto resta serializzabile: i params portano float e None
    json.dumps(referto)


# --- U3.2: la description di Lighthouse, ripulita ---------------------
#
# Lighthouse gira con --locale=it e la description arriva gia' tradotta,
# in Markdown. Diventa il `detail` del rilievo e non il `fix`: nove
# degli undici audit SEO spiegano perche' il controllo conta, e solo
# due prescrivono qualcosa.

def test_seo_il_link_markdown_diventa_la_sua_etichetta():
    """Si tiene il testo e si toglie l'URL: la frase deve restare intera."""
    testo, urls = mars_seo._senza_link_markdown(
        "Assicurati che [l'attributo href](https://x/doc) rimandi altrove.")
    assert testo == "Assicurati che l'attributo href rimandi altrove."
    assert urls == ["https://x/doc"]


def test_seo_due_link_danno_due_riferimenti():
    """`structured-data` ne ha due, uno a meta' frase e uno in coda."""
    testo, urls = mars_seo._senza_link_markdown(
        "Esegui lo [Strumento](https://a/) per convalidare. "
        "[Scopri di piu'](https://b/).")
    assert testo == "Esegui lo Strumento per convalidare. Scopri di piu'."
    assert urls == ["https://a/", "https://b/"]


def test_seo_testo_senza_link_resta_identico():
    testo, urls = mars_seo._senza_link_markdown(
        "Gli `alt` vuoti sono leciti sulle immagini decorative.")
    assert testo == "Gli `alt` vuoti sono leciti sulle immagini decorative."
    assert urls == []


def test_seo_un_url_con_parentesi_resta_nel_testo():
    """Limite dichiarato, verificato: meglio intatto che tagliato a meta'.

    L'alternativa — un `[^)]+` avido di parentesi — riconoscerebbe il
    link e ne troncherebbe l'URL alla prima chiusa, lasciando ")"
    appeso in mezzo alla frase e un riferimento che non si apre.
    """
    grezzo = "Vedi [la voce](https://it.wikipedia.org/wiki/Foo_(bar))."
    testo, urls = mars_seo._senza_link_markdown(grezzo)
    assert testo == grezzo
    assert urls == []


def test_seo_la_description_diventa_detail_e_non_fix():
    """La scelta di U3.2, fissata: e' una spiegazione, non una prescrizione.

    Se un giorno finisse in `fix`, il piano di interventi della Fase 4
    direbbe, alla voce "come si aggiusta", perche' il controllo conta.
    """
    rilievi = mars_seo.riassumi(_lhr())["findings"]
    crawlable = [f for f in rilievi if f["key"] == "seo.lh.is_crawlable"][0]
    assert crawlable["detail"].startswith("I motori di ricerca non sono in "
                                          "grado di includere le pagine")
    assert crawlable["fix"] == ""


def test_seo_nessun_detail_conserva_il_markdown():
    """Il Markdown non deve arrivare al referto: nessuno lo renderizza."""
    for rilievo in mars_seo.riassumi(_lhr())["findings"]:
        assert "](" not in rilievo["detail"], rilievo["key"]
        assert "[Scopri" not in rilievo["detail"], rilievo["key"]


def test_seo_i_link_della_description_diventano_riferimenti():
    """L'URL non si butta: e' documentazione dello strumento.

    Lista e non `Finding.url` per la stessa ragione dei `reference` di
    ZAP (U1.6): i link possono essere piu' d'uno, e sceglierne uno
    nasconderebbe gli altri. `structured-data` ne ha due davvero.
    """
    rilievi = {f["key"]: f for f in mars_seo.riassumi(_lhr())["findings"]}
    assert rilievi["seo.lh.is_crawlable"]["params"]["references"] == [
        "https://developer.chrome.com/docs/lighthouse/seo/is-crawlable/"]
    assert len(rilievi["seo.lh.structured_data"]["params"]["references"]) == 2


def test_seo_senza_description_non_inventa_riferimenti():
    """Un LHR senza description non deve produrre params vuoti.

    `references: []` in ogni rilievo sarebbe una chiave che promette un
    dato che non c'e' — e nel CSV della Fase 6 una colonna sempre vuota.
    """
    lhr = _lhr()
    for voce in lhr["audits"].values():
        voce.pop("description", None)
    for rilievo in mars_seo.riassumi(lhr)["findings"]:
        assert rilievo["detail"] == ""
        assert "references" not in rilievo["params"]


def test_seo_estrai_audit_conserva_la_description():
    """Il punto di contatto col LHR e' uno solo: se non passa di qui,
    a valle non si ricostruisce."""
    voci = {c["id"]: c for c in mars_seo.estrai_audit(_lhr())}
    assert voci["canonical"]["description"].startswith("I link canonici")
    # Verbatim: il Markdown lo toglie chi ne fa un detail, non
    # l'estrattore, che dei valori di Lighthouse e' fedele.
    assert "](" in voci["canonical"]["description"]


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


def _ctx_heading(query):
    """Un corpus dove la parola cercata sta SOLO nell'heading."""
    return {"chunks": [
        {"url": "https://x/a", "heading": "Servizi di consulenza",
         "text": "Lavoriamo con aziende di ogni dimensione da molti anni."},
        {"url": "https://x/b", "heading": "Chi siamo",
         "text": "La nostra storia comincia nel duemila con tre persone."}],
        "queries": [query], "pages": {}, "embeddings_model": "x",
        "force_proxy": True, "lang": "it"}


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_i_due_recuperatori_leggono_lo_STESSO_contenuto(modulo):
    """R35: R10 aveva lavorato perche' i due ranghi si riferissero alle
    stesse UNITA'. Nessuno aveva poi controllato che leggessero lo
    stesso CONTENUTO di quelle unita'.

    `mars_lexical` indicizzava heading + testo, `mars_semantic` il solo
    testo. Misurato prima della correzione, con la parola cercata
    presente solo nell'heading: lessicale `matched=True`, vettoriale
    `matched=False`. Su un sito con le FAQ nei titoli i due erano in
    disaccordo **per costruzione**, e il consenso RRF ne usciva depresso
    per una ragione che non riguarda il sito.
    """
    voce = modulo.audit(_ctx_heading("servizi"))["per_query"][0]
    assert voce["matched"] is True
    assert voce["top_chunk"] is not None
    assert "/a" in voce["top_chunk"]


def test_semantic_l_heading_non_conta_due_volte_nei_segnali():
    """La correzione tocca il corpus del RECUPERATORE, non i segnali.

    `question_signals` riceve gia' l'heading a parte, e `MIN_PAROLE`
    conta le parole del testo: dare a entrambi un testo che comincia
    con l'heading lo conterebbe due volte e sposterebbe una soglia che
    non c'entra con R35."""
    ctx = _ctx_heading("servizi")
    ctx["chunks"] = [{"url": "https://x/a", "heading": "Come funziona?",
                      "text": "Bastano tre passi."}]
    esito = mars_semantic.audit(ctx)
    # Un solo chunk, un solo segnale di domanda: se l'heading finisse
    # anche nel testo, `question_signals` lo vedrebbe due volte.
    conteggi = esito.get("signals") or esito.get("segnali") or {}
    for nome, quante in (conteggi.items() if hasattr(conteggi, "items") else []):
        assert quante <= 1, "%s contato %d volte" % (nome, quante)


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
# U13: le due aree di classifica emettono controlli
# ----------------------------------------------------------------------
#
# Fino a U13 `mars_lexical` e `mars_semantic` producevano metriche e
# nessun controllo con un esito: sette aree su nove alimentavano il
# piano di interventi, e le due che nutrono i quadranti derivati non
# contribuivano un solo rilievo.

def _pagina_u13(testo: str, titolo: str = "Pagina", url: str = "https://x/"):
    """Una pagina finta con un conteggio di parole controllato.

    Non passa da `conftest.pagina()` perche' qui serve dosare le
    PAROLE, che e' la grandezza su cui BM25 normalizza: costruire
    l'HTML e farlo riparsare renderebbe il conteggio un effetto
    collaterale del chunker invece del dato del test.
    """
    return {"title": titolo, "text": testo, "lang": "it", "html": "",
            "headings": [], "chunks": [{"url": url, "heading": titolo,
                                        "text": testo}]}


def _ctx_u13(pagine: dict, queries=("organizzazione",)) -> dict:
    return {"url": "https://x/", "pages": pagine,
            "chunks": [c for p in pagine.values() for c in p["chunks"]],
            "queries": list(queries), "embeddings_model": "none",
            "force_proxy": True, "credentials": {}, "market": "global"}


def _chiavi(esito: dict) -> set:
    return {f["key"] for f in esito["findings"]}


def _rilievo_con(esito: dict, chiave: str) -> dict:
    trovati = [f for f in esito["findings"] if f["key"] == chiave]
    assert trovati, "atteso %s, presenti %s" % (chiave, _chiavi(esito))
    return trovati[0]


def test_lexical_le_pagine_sottili_sono_un_rilievo():
    """BM25 normalizza la frequenza dei termini sulla lunghezza del
    documento: una pagina di due righe non raggiunge una frequenza che
    la formula possa valorizzare, e finora l'area non lo diceva."""
    magra = _pagina_u13("parole poche davvero", url="https://x/magra")
    grassa = _pagina_u13(" ".join(["organizzazione"] * 400),
                         titolo="Grassa", url="https://x/grassa")
    esito = mars_lexical.audit(_ctx_u13({"https://x/magra": magra,
                                         "https://x/grassa": grassa}))
    rilievo = _rilievo_con(esito, "lex.words.thin")
    assert rilievo["params"]["pagine"] == 1
    assert rilievo["params"]["totale"] == 2
    assert rilievo["params"]["soglia"] == mars_lexical.SOGLIA_PAROLE
    # R47: il rilievo dichiara DOVE, e solo la pagina che l'ha acceso.
    assert rilievo["params"]["urls"] == ["https://x/magra"]


def test_lexical_i_title_ripetuti_sono_un_rilievo():
    """Due pagine con lo stesso <title> non si distinguono nell'indice
    lessicale, ed e' un fatto FRA pagine: Lighthouse guarda una pagina
    sola, quindi nessuna altra area di MARS puo' vederlo."""
    pagine = {
        "https://x/a": _pagina_u13(" ".join(["testo"] * 400), "Servizi",
                                   "https://x/a"),
        "https://x/b": _pagina_u13(" ".join(["testo"] * 400), "Servizi",
                                   "https://x/b"),
        "https://x/c": _pagina_u13(" ".join(["testo"] * 400), "Contatti",
                                   "https://x/c"),
    }
    rilievo = _rilievo_con(mars_lexical.audit(_ctx_u13(pagine)),
                           "lex.title.dup")
    assert rilievo["params"]["titoli"] == 1
    assert rilievo["params"]["pagine"] == 2
    assert rilievo["params"]["urls"] == ["https://x/a", "https://x/b"]


def test_lexical_un_title_vuoto_non_e_un_duplicato():
    """Due pagine senza <title> non hanno lo STESSO titolo: non ne
    hanno affatto, ed e' un difetto che misura Lighthouse. Contarle
    qui darebbe due rilievi sullo stesso fatto, uno dei quali falso."""
    pagine = {"https://x/a": _pagina_u13("testo " * 400, "", "https://x/a"),
              "https://x/b": _pagina_u13("testo " * 400, "", "https://x/b")}
    assert "lex.title.dup" not in _chiavi(mars_lexical.audit(_ctx_u13(pagine)))


@pytest.mark.parametrize("modulo, chiave", [
    (mars_lexical, "lex.query.no_match"),
    (mars_semantic, "sem.query.no_match"),
])
def test_una_query_senza_riscontro_diventa_un_rilievo(modulo, chiave):
    """R23 aveva insegnato a NON spacciare l'ordine di scansione per
    una classifica; il fatto restava pero' solo dentro `per_query`, e
    il referto non ne faceva nulla."""
    esito = modulo.audit(_ctx_r23(["zzzzz qqqqq wwwww", "organizzazione"]))
    rilievo = _rilievo_con(esito, chiave)
    assert rilievo["params"]["senza_riscontro"] == 1
    assert rilievo["params"]["totale"] == 2
    # Non e' un fatto di UNA pagina: dichiarare `urls` qui colorerebbe
    # la treemap su una pagina scelta a caso.
    assert "urls" not in rilievo["params"]


@pytest.mark.parametrize("modulo, chiave", [
    (mars_lexical, "lex.status.no_pages"),
    (mars_semantic, "sem.status.no_pages"),
])
def test_senza_pagine_le_aree_di_classifica_non_inventano_un_punteggio(
        modulo, chiave):
    """Un punteggio calcolato sulle sole query direbbe 100 su un sito
    da cui non e' stata letta una riga. `score: None` piu'
    `unavailable` e' il contratto."""
    esito = modulo.audit({"url": "https://x/", "pages": {}, "chunks": [],
                          "queries": [], "embeddings_model": "none",
                          "force_proxy": True, "credentials": {}})
    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert _chiavi(esito) == {chiave}


def test_semantic_pochi_passaggi_sono_un_rilievo():
    """Ogni chunk e' un'occasione di comparire in una lista: il numero
    di passaggi e' il moltiplicatore della somma RRF."""
    pagina_sola = _pagina_u13(" ".join(["organizzazione"] * 400))
    esito = mars_semantic.audit(_ctx_u13({"https://x/": pagina_sola}))
    rilievo = _rilievo_con(esito, "sem.chunks.few")
    assert rilievo["params"]["chunk"] == 1
    assert rilievo["params"]["soglia"] == mars_semantic.SOGLIA_CHUNK


def test_semantic_nessun_passaggio_e_un_rilievo_critico():
    """Pagine che ci sono e non producono un passaggio: il sito non
    offre nulla su cui un recuperatore possa lavorare. E' diverso da
    «nessuna pagina», che e' uno stato della scansione."""
    vuota = {"title": "Vuota", "text": "", "lang": "it", "html": "",
             "headings": [], "chunks": []}
    esito = mars_semantic.audit(_ctx_u13({"https://x/": vuota}))
    rilievo = _rilievo_con(esito, "sem.chunks.none")
    assert rilievo["severity"] == mars_core.SEV_CRITICAL
    assert esito["status"] == "ranking", "le pagine c'erano: e' un giudizio"


def test_semantic_la_quota_in_forma_di_risposta_bassa_e_un_rilievo():
    """`answer_shaped_ratio` era misurato e non giudicato: il solo
    rilievo che lo citava era `cit.answer_shaped.weak`, derivato, che
    rimandava a un'area senza un rilievo da indicare."""
    testo = " ".join(["organizzazione"] * 60)
    pagine = {"https://x/%d" % i: _pagina_u13(testo, "Sezione %d" % i,
                                              "https://x/%d" % i)
              for i in range(3)}
    esito = mars_semantic.audit(_ctx_u13(pagine))
    assert esito["answer_shaped_ratio"] == 0.0
    rilievo = _rilievo_con(esito, "sem.answer_shaped.low")
    assert rilievo["params"]["soglia"] == mars_semantic.SOGLIA_ANSWER_SHAPED
    # Dove: le pagine che non portano un solo passaggio in forma di
    # risposta, cosi' la treemap colora quelle e non l'intero sito.
    assert rilievo["params"]["urls"] == sorted(pagine)


def test_la_soglia_in_forma_di_risposta_e_quella_della_citabilita():
    """Due soglie sullo stesso numero: sotto 60 `mars_citability`
    dichiara il segnale debole. Se qui fosse 10, il referto direbbe
    «segnale debole» accanto a un'area che non ha nulla da segnalare —
    e nessun errore lo rivelerebbe."""
    assert (mars_semantic.SOGLIA_ANSWER_SHAPED
            == mars_citability.SOGLIA_DEBOLE)


def _chunk_risposta(url: str) -> dict:
    """Un passaggio in forma di risposta: heading interrogativo e oltre
    MIN_PAROLE parole, che sono le due condizioni del rapporto."""
    return {"url": url, "heading": "Quanto dura una seduta?",
            "text": " ".join(["parola"] * (mars_semantic.MIN_PAROLE + 5))}


def _chunk_muto(url: str) -> dict:
    return {"url": url, "heading": "Chi siamo",
            "text": " ".join(["parola"] * (mars_semantic.MIN_PAROLE + 5))}


def test_semantic_alla_soglia_esatta_il_rilievo_non_scatta():
    """Il confronto e' `>=`, e il caso di confine e' l'unico che
    distingue `>=` da `>`: tre passaggi su cinque fanno esattamente il
    60% atteso, e a quel punto l'area non ha nulla da segnalare."""
    chunks = ([_chunk_risposta("https://x/a") for _ in range(3)]
              + [_chunk_muto("https://x/a") for _ in range(2)])
    pagine = {"https://x/a": {"lang": "it", "html": "", "headings": [],
                              "title": "A", "text": "x", "chunks": chunks}}
    esito = mars_semantic.audit({"url": "https://x/", "pages": pagine,
                                 "chunks": chunks, "queries": [],
                                 "embeddings_model": "none",
                                 "force_proxy": True, "credentials": {}})
    assert esito["answer_shaped_ratio"] == 0.6
    assert "sem.answer_shaped.low" not in _chiavi(esito)


def test_semantic_le_pagine_con_una_risposta_restano_fuori_dal_rilievo():
    """R47 dice DOVE, e «dove» non e' «ovunque».

    Con il rapporto sotto soglia ma una pagina che una risposta ce
    l'ha, elencare anche quella colorerebbe la treemap su una pagina
    che il difetto non ha."""
    chunks = ([_chunk_risposta("https://x/buona")]
              + [_chunk_muto("https://x/buona")]
              + [_chunk_muto("https://x/muta") for _ in range(3)])
    pagine = {url: {"lang": "it", "html": "", "headings": [], "title": url,
                    "text": "x", "chunks": []}
              for url in ("https://x/buona", "https://x/muta")}
    esito = mars_semantic.audit({"url": "https://x/", "pages": pagine,
                                 "chunks": chunks, "queries": [],
                                 "embeddings_model": "none",
                                 "force_proxy": True, "credentials": {}})
    assert esito["answer_shaped_ratio"] == 0.2
    rilievo = _rilievo_con(esito, "sem.answer_shaped.low")
    assert rilievo["params"]["urls"] == ["https://x/muta"]


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_le_aree_di_classifica_non_pubblicano_un_punteggio_negativo(
        modulo, contesto, monkeypatch):
    """Il pavimento a zero, provato invece che assunto.

    Coi controlli di oggi le penalita' non arrivano a 100 — 48 sul
    lessicale, 80 sul semantico — quindi il ramo non si raggiunge con
    un sito, per quanto malmesso. Si raggiunge alzando la tabella delle
    penalita', ed e' cio' che rende il presidio vero: il giorno in cui
    un controllo nuovo la fara' saturare, questo test c'e' gia'."""
    monkeypatch.setitem(modulo.PENALITA, "grave", 200.0)
    monkeypatch.setitem(modulo.PENALITA, "medio", 200.0)
    monkeypatch.setitem(modulo.PENALITA, "critico", 200.0)
    contesto["queries"] = ["zzzzz qqqqq wwwww"]
    esito = modulo.audit(contesto)
    assert esito["findings"], "il caso ha senso solo con dei rilievi"
    assert esito["score"] == 0


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_le_aree_di_classifica_ricostruiscono_il_punteggio(modulo, contesto):
    """Le penalita' dichiarate devono ricostruire lo score, altrimenti
    il piano di interventi non puo' quantificare alcun recupero: e'
    `certificato_area`, applicata alle due aree nuove."""
    esito = modulo.audit(contesto)
    penalita = sum(f["params"]["penalty"] for f in esito["findings"])
    assert esito["score"] == max(0, round(100 - penalita))


@pytest.mark.parametrize("modulo", [mars_lexical, mars_semantic],
                         ids=lambda m: m.__name__)
def test_ogni_rilievo_delle_aree_di_classifica_dichiara_una_penalita(
        modulo, contesto):
    """Tranne quelli di stato, che non sono difetti del sito."""
    for f in modulo.audit(contesto)["findings"]:
        if ".status." in f["key"]:
            continue
        assert isinstance(f["params"].get("penalty"), float), f["key"]


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


def _variante(plugin, ref=None, risk="Medium", url="https://x/", **extra):
    voce = {"pluginId": plugin, "alert": "Regola %s" % plugin,
            "risk": risk, "url": url}
    if ref is not None:
        voce["alertRef"] = ref
    voce.update(extra)
    return voce


def test_wapt_le_sotto_varianti_diventano_rilievi_distinti():
    """R39: `alertRef` non veniva mai raggiunto, ed era codice morto.

    La catena era `pluginId or alertRef or ...`, ma `pluginId` e'
    SEMPRE presente nel JSON di ZAP (`AlertAPI.alertToSet` lo scrive con
    `String.valueOf`). La regola CSP 10038 emette `10038-1`, `-2` e
    `-3`: alert distinti, con testi e soluzioni proprie, che
    diventavano **una** voce sola con la soluzione del primo."""
    esito = mars_wapt.score_from_alerts([
        _variante("10038", "10038-1", solution="Imposta l'header."),
        _variante("10038", "10038-2", solution="Togli unsafe-inline."),
    ])
    rilievi = {f["key"]: f for f in esito["findings"]}

    assert set(rilievi) == {"sec.zap.10038_1", "sec.zap.10038_2"}
    assert rilievi["sec.zap.10038_1"]["fix"] == "Imposta l'header."
    assert rilievi["sec.zap.10038_2"]["fix"] == "Togli unsafe-inline."
    # La regola violata resta UNA: il conteggio dice quante regole, non
    # quanti rilievi, e i due numeri ora differiscono.
    assert esito["rules_violated"] == 1
    assert esito["alerts_grouped"] == 2


def test_wapt_la_ritaratura_non_sposta_il_punteggio():
    """La decisione del 2026-08-26: si ritara sulla REGOLA — penalita'
    sull'unione degli URL, ripartita fra le sotto-varianti — cosi' i
    rilievi diventano distinti e **la somma resta quella di prima**.

    Senza, ogni sito che viola una regola con tre varianti ne
    perderebbe il triplo: la cardinalita' dei gruppi *e'* il punteggio.
    """
    urls = ["https://x/a", "https://x/b", "https://x/c"]
    prima = mars_wapt.score_from_alerts(
        [_variante("10038", url=u) for u in urls])
    dopo = mars_wapt.score_from_alerts(
        [_variante("10038", "10038-%d" % i, url=u)
         for i, u in enumerate(urls, 1)])

    assert dopo["score"] == prima["score"]
    assert len(dopo["findings"]) == 3 and len(prima["findings"]) == 1


def test_wapt_la_ripartizione_della_penalita_e_auditabile():
    """Un numero del referto vale quanto la possibilita' di rifarne il
    conto: `penalty * variants == rule_penalty`, e `rule_penalty` si
    ricalcola dalla formula sull'unione degli URL."""
    esito = mars_wapt.score_from_alerts([
        _variante("10038", "10038-1", url="https://x/a"),
        _variante("10038", "10038-2", url="https://x/b"),
    ])
    for f in esito["findings"]:
        p = f["params"]
        assert p["variants"] == 2
        assert p["penalty"] * p["variants"] == pytest.approx(
            p["rule_penalty"])
        # Due URL distinti fra le due varianti: la diffusione si misura
        # sull'UNIONE, non sulla singola variante.
        assert p["rule_n"] == 2
        assert p["n"] == 1
        assert p["rule_penalty"] == pytest.approx(10 * (1 + 2 / 10.0))


def test_wapt_la_diffusione_non_conta_due_volte_lo_stesso_url():
    """Due varianti sulla stessa pagina sono una pagina sola: l'unione
    e' un insieme, e contarle due volte gonfierebbe la diffusione."""
    esito = mars_wapt.score_from_alerts([
        _variante("10038", "10038-1", url="https://x/a"),
        _variante("10038", "10038-2", url="https://x/a"),
    ])
    assert esito["findings"][0]["params"]["rule_n"] == 1


@pytest.mark.parametrize("ref", [None, "10038"])
def test_wapt_una_regola_senza_varianti_tiene_la_chiave_di_prima(ref):
    """`alertRef` assente, o uguale al `pluginId`: la chiave non migra,
    e il confronto con gli archivi gia' scritti regge."""
    esito = mars_wapt.score_from_alerts([_variante("10038", ref)])
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "sec.zap.10038"
    assert rilievo["params"]["variants"] == 1
    # Vuoto in entrambi i casi: `alertRef` uguale al `pluginId` non
    # dichiara una variante, dichiara che la regola non ne ha.
    assert rilievo["params"]["alert_ref"] == ""


def test_wapt_il_rischio_della_variante_e_quello_della_regola_convivono():
    """La gravita' del rilievo e' quella che ZAP ha dato a QUELLA
    variante; la penalita' viene dalla regola, che ne ha una sola.

    Quando le due differiscono il dato lo dice invece di nasconderlo:
    un rilievo `info` che porta una quota di penalita' `High` sarebbe
    altrimenti inspiegabile."""
    esito = mars_wapt.score_from_alerts([
        _variante("10038", "10038-1", risk="High"),
        _variante("10038", "10038-2", risk="Low"),
    ])
    per_chiave = {f["key"]: f for f in esito["findings"]}
    assert per_chiave["sec.zap.10038_2"]["params"]["risk"] == "Low"
    assert per_chiave["sec.zap.10038_2"]["params"]["rule_risk"] == "High"
    assert per_chiave["sec.zap.10038_2"]["source_severity"] == "ZAP:Low"


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
    base = {"pluginId": "10038",
            "alert": "CSP Header Not Set", "name": "CSP Header Not Set",
            "risk": "Medium", "url": "https://x/",
            "description": "The header is not set.",
            "solution": "Ensure the header is set.",
            "reference": "https://a/\nhttps://b/"}
    base.update(kw)
    # L'`alertRef` di ZAP COMINCIA sempre col pluginId: e' il pluginId
    # piu' un indice di variante, ed e' il pluginId nudo per le regole
    # che varianti non ne hanno. Derivarlo invece di cablarlo tiene il
    # finto fedele quando un test cambia il pluginId — da R39 e'
    # l'alertRef a raggruppare, e un default cablato metterebbe due
    # regole diverse nello stesso gruppo senza che nulla lo riveli.
    base.setdefault("alertRef", base.get("pluginId"))
    return {k: v for k, v in base.items() if v is not None}


class _Risposta:
    """Risposta HTTP finta, FEDELE su cio' che il modulo usa.

    `headers` e' una `CaseInsensitiveDict`, non un `dict`: e' cio' che
    `requests` restituisce, e `audit_headers` fa `header not in
    resp.headers`. Con un dict semplice il test verificherebbe un
    confronto che il codice reale non esegue — la stessa lezione
    dell'adattatore finto del Crawler in tests/test_core.py.

    `url` per la stessa ragione: una `requests.Response` ce l'ha
    sempre, ed e' l'URL a cui la risposta e' ARRIVATA — dopo i
    redirect. `_risposte` lo riempie con l'URL richiesto quando il
    copione non ne fissa uno; un test che voglia esercitare un redirect
    lo passa esplicitamente.
    """

    def __init__(self, status_code: int = 200, headers=(), url: str = ""):
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(dict(headers))
        self.url = url


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
        if not esito.url:
            esito.url = url
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


def test_wapt_un_daemon_che_fallisce_non_ripiega_in_silenzio(monkeypatch):
    """R39: se `run_zap` restituiva `None` c'era solo un `print`, e il
    referto dichiarava «HTTP-Headers, superficie» senza mai dire che un
    daemon c'era e non aveva portato a termine la scansione.

    Chi legge il referto non ha la console davanti: vede un'area di
    sicurezza fatta di soli header e non sa che la vera scansione era
    stata tentata ed e' fallita. E' lo stesso difetto di onesta' che
    R38 ha chiuso altrove, e il principio 2 lo vieta — cio' che manca
    si dichiara, non si tace.
    """
    monkeypatch.setattr(mars_wapt, "connect_zap",
                        lambda credentials=None: _ZapFinto())
    monkeypatch.setattr(mars_wapt, "run_zap",
                        lambda url, client=None, active=False: None)
    # Il ripiego porta un rilievo suo: senza, la lista avrebbe un
    # elemento solo e l'asserzione sulla POSIZIONE sarebbe vuota —
    # misurato, una mutazione che sposta l'avviso in coda passava.
    monkeypatch.setattr(mars_wapt, "audit_headers",
                        lambda url: {"score": 80, "status": "surface",
                                     "tool": "HTTP-Headers",
                                     "issues": ["manca CSP"],
                                     "findings": [{"key": "sec.headers.csp_missing",
                                                   "title": "manca CSP"}]})

    esito = mars_wapt.audit({"url": "https://x/", "owner_declaration": False})
    chiavi = [f["key"] for f in esito["findings"]]

    assert len(chiavi) == 2, "serve piu' di un rilievo, o la posizione non dice nulla"

    assert "sec.status.zap_failed" in chiavi
    # In TESTA, come gli altri rilievi di stato: e' la premessa per
    # leggere il punteggio, non una nota a pie' di pagina.
    assert chiavi[0] == "sec.status.zap_failed"
    assert "ZAP" in esito["issues"][0]
    # Il ripiego resta un ripiego: il punteggio degli header non si
    # tocca, e lo strumento dichiarato e' quello che ha misurato.
    assert esito["score"] == 80
    assert esito["tool"] == "HTTP-Headers"
    assert esito["status"] == "surface"


def test_wapt_senza_daemon_il_ripiego_resta_muto(monkeypatch):
    """L'altra meta': se nessun daemon era raggiungibile non c'e' nulla
    da dichiarare, e un rilievo «ZAP ha fallito» sarebbe falso.

    Senza questo test la correzione potrebbe aggiungere l'avviso sempre,
    e nessuno se ne accorgerebbe."""
    monkeypatch.setattr(mars_wapt, "connect_zap",
                        lambda credentials=None: None)
    monkeypatch.setattr(mars_wapt, "audit_headers",
                        lambda url: {"score": 80, "status": "surface",
                                     "tool": "HTTP-Headers",
                                     "issues": [], "findings": []})

    esito = mars_wapt.audit({"url": "https://x/"})
    assert not [f for f in esito["findings"]
                if f["key"] == "sec.status.zap_failed"]


def test_wapt_le_due_diagnosi_degli_header_non_si_perdono(monkeypatch):
    """R39: se HEAD solleva e GET risponde >= 400, `errore` veniva
    riassegnato a `None` e la diagnosi diventava il solo «HTTP 500».

    Il `ConnectionError` che spiegava il primo tentativo spariva, e con
    esso l'informazione piu' utile: i due tentativi sono falliti per
    ragioni DIVERSE, il che dice qualcosa che nessuno dei due dice da
    solo."""
    def head(url, **kw):
        raise requests.ConnectionError("niente HEAD")

    class Risposta:
        status_code = 500
        headers = {}
        url = "https://x/"

    monkeypatch.setattr(mars_wapt.requests, "head", head)
    monkeypatch.setattr(mars_wapt.requests, "get", lambda url, **kw: Risposta())

    esito = mars_wapt.audit_headers("https://x/")
    dettaglio = esito["findings"][0]["detail"]

    assert esito["status"] == "unavailable"
    assert esito["score"] is None
    assert "ConnectionError" in dettaglio, "il primo errore e' andato perso"
    assert "500" in dettaglio, "il secondo errore e' andato perso"


def test_wapt_una_diagnosi_sola_resta_una_diagnosi_sola(monkeypatch):
    """Conservare entrambe non deve diventare ripetere la stessa due
    volte: quando i due tentativi falliscono allo stesso modo, il
    dettaglio ne porta una."""
    class Risposta:
        status_code = 503
        headers = {}
        url = "https://x/"

    monkeypatch.setattr(mars_wapt.requests, "head", lambda url, **kw: Risposta())
    monkeypatch.setattr(mars_wapt.requests, "get", lambda url, **kw: Risposta())

    dettaglio = mars_wapt.audit_headers("https://x/")["findings"][0]["detail"]
    assert dettaglio.count("503") == 1, dettaglio


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
    """La chiave e' stabile quando nasce dal `pluginId` o dall'
    `alertRef`, che ne e' il pluginId piu' un indice; un nome viene dai
    Messages.properties di ZAP, cambia fra due release ed e'
    localizzato. Chi confrontera' due esecuzioni deve poterlo sapere.

    L'`alertRef` uguale al pluginId non fa `alertRef`: li' i due valori
    sono lo stesso, e dire il campo piu' specifico dei due sarebbe
    dichiarare una precisione che non c'e'."""
    da_plugin = mars_wapt.score_from_alerts([_alert()])
    da_variante = mars_wapt.score_from_alerts([_alert(alertRef="10038-1")])
    da_nome = mars_wapt.score_from_alerts(
        [_alert(pluginId=None, alertRef=None)])
    assert da_plugin["findings"][0]["params"]["key_source"] == "pluginId"
    assert da_variante["findings"][0]["params"]["key_source"] == "alertRef"
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
    """`fix` ne porta una, e se le altre si perdono il dato deve dirlo
    invece di lasciar credere che fosse l'unica.

    **Il caso era un altro**: due `alertRef` dello stesso `pluginId`,
    che R39 ha separato in due rilievi — ciascuno ora tiene la propria
    soluzione, e non se ne perde nessuna. Resta il caso vero, piu'
    stretto: lo STESSO alert su due URL con soluzioni diverse."""
    esito = mars_wapt.score_from_alerts([
        _alert(alertRef="10038-1", solution="Prima."),
        _alert(alertRef="10038-1", solution="Seconda.", url="https://x/b")])
    finding = esito["findings"][0]
    assert len(esito["findings"]) == 1, "un alertRef solo, un rilievo solo"
    assert finding["fix"] == "Prima.", "la prima non vuota, deterministica"
    assert finding["params"]["soluzioni"] == 2


def test_wapt_le_reference_diventano_una_lista():
    """`reference` e' UNA stringa con dentro piu' URL: metterla in
    `Finding.doc_url`, che e' un link solo, ne mostrerebbe uno e
    nasconderebbe gli altri."""
    esito = mars_wapt.score_from_alerts(
        [_alert(reference="https://a/\r\nhttps://b/\nhttps://c/\n")])
    finding = esito["findings"][0]
    assert finding["params"]["references"] == ["https://a/", "https://b/",
                                               "https://c/"]
    assert finding["doc_url"] == "", "ZAP non manda un link per regola"


def test_wapt_ogni_variante_dichiara_il_proprio_alert_ref():
    """`params["alert_refs"]` era l'insieme del gruppo, conservato da
    U1.6 come «il dato che permettera' di spezzarlo quando lo si
    vorra'». R39 lo ha spezzato: il gruppo E' la variante, quindi il
    campo diventa singolare e ogni rilievo porta il suo."""
    esito = mars_wapt.score_from_alerts([
        _alert(alertRef="10038-2"),
        _alert(alertRef="10038-1", url="https://x/b")])
    per_chiave = {f["key"]: f["params"]["alert_ref"]
                  for f in esito["findings"]}
    assert per_chiave == {"sec.zap.10038_2": "10038-2",
                          "sec.zap.10038_1": "10038-1"}


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


# --- U3.2: la description di ZAP diventa il detail ---------------------

def test_wapt_la_description_di_zap_diventa_detail():
    """Due campi in ZAP, due campi nel rilievo.

    `description` spiega, `solution` prescrive: fonderle darebbe alla
    Fase 4 un intervento che comincia con una spiegazione.
    """
    esito = mars_wapt.score_from_alerts([_alert()])
    rilievo = esito["findings"][0]
    assert rilievo["detail"] == "The header is not set."
    assert rilievo["fix"] == "Ensure the header is set."


def test_wapt_il_detail_e_il_primo_non_vuoto_del_gruppo():
    """Stessa regola della solution, per la stessa ragione.

    Dentro un pluginId gli alertRef possono avere descrizioni diverse:
    concatenarle darebbe un testo che non e' di nessuno dei due.
    """
    esito = mars_wapt.score_from_alerts([
        _alert(description=None, url="https://x/a"),
        _alert(description="La prima che parla.", url="https://x/b"),
        _alert(description="La seconda, che non deve vincere.",
               url="https://x/c")])
    assert len(esito["findings"]) == 1
    assert esito["findings"][0]["detail"] == "La prima che parla."


def test_wapt_senza_description_il_detail_resta_vuoto():
    """Non e' un errore: esistono alert Informational senza descrizione."""
    esito = mars_wapt.score_from_alerts([_alert(description=None)])
    assert esito["findings"][0]["detail"] == ""


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

    monkeypatch.setattr("shutil.which",
                        lambda n, path=None: "/usr/bin/lighthouse")
    monkeypatch.setattr("subprocess.run", finto_run)
    mars_seo.audit({"url": "https://x/; rm -rf ~ #"})
    assert isinstance(visto["cmd"], list), "argomenti come lista, non stringa"
    assert visto["kwargs"].get("shell") is not True
    assert "https://x/; rm -rf ~ #" in visto["cmd"], "URL come argomento unico"
    assert visto["kwargs"].get("timeout"), "serve un timeout"


def test_seo_senza_lighthouse_non_da_zero(monkeypatch):
    """Regressione R4: score 0 e' un giudizio, non un'assenza."""
    monkeypatch.setattr("shutil.which", lambda n, path=None: None)
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


# --- U1.8: i rilievi derivati di mars_citability -----------------------
#
# Quest'area non misura il sito: rilegge i punteggi delle altre. I suoi
# rilievi devono poter essere SALTATI da chi li somma, altrimenti lo
# stesso difetto viene contato due volte — e' la decisione D3 portata
# dentro il dato.

def _rilievi(**cambi) -> dict:
    """I rilievi di un audit di citabilita', indicizzati per chiave."""
    esito = mars_citability.audit(
        {"results": _risultati(**cambi), "market": "global"})
    return {f["key"]: f for f in esito["findings"]}


# Quattro segnali deboli con valori DISTINTI: answer_shaped va portato a
# 1.0, altrimenti _risultati() lo lascia a 50 e pareggia con wcag.
DEBOLI_DISTINTI = dict(
    mars_seo={"score": 10}, mars_schema={"score": 30},
    mars_wcag={"score": 50}, mars_wapt={"score": 59},
    mars_semantic={"rank": [0, 1, 2], "answer_shaped_ratio": 1.0})


def test_citability_ogni_rilievo_e_dichiarato_derivato():
    """L'invariante d'area, non un giudizio caso per caso: nulla di
    quello che dice quest'area nasce da una misura sua."""
    for cambi in ({}, DEBOLI_DISTINTI, {"mars_seo": {"score": None}}):
        esito = mars_citability.audit({"results": _risultati(**cambi)})
        assert esito["findings"], "l'area deve dire qualcosa"
        assert all(f["params"]["derived"] is True
                   for f in esito["findings"])
    # Anche i due rami che escono prima di ogni calcolo.
    for ctx in ({"results": {}},
                {"results": {"mars_tech": {"score": None}}}):
        assert all(f["params"]["derived"] is True
                   for f in mars_citability.audit(ctx)["findings"])


def test_citability_nessun_rilievo_porta_una_penalita():
    """L'assenza di `penalty` E' il significato di `derived`: un segnale
    debole e' un difetto del sito, ma quantificarlo tocca all'area che
    l'ha misurato. Sarebbe calcolabile — il composito e' una media
    pesata — e proprio per questo non va messo."""
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI)})
    assert esito["findings"]
    assert all("penalty" not in f["params"] for f in esito["findings"])


def test_citability_una_sintesi_non_scavalca_la_misura():
    """Tutti `info` a peso 1.0: la severita' e' l'asse su cui la Fase 4
    ordinera' il piano, e su quell'asse un rilievo derivato non deve mai
    precedere quello che lo spiega — che ha regola, URL e soluzione."""
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI),
                                   "market": "atlantide"})
    assert esito["findings"]
    for f in esito["findings"]:
        assert f["severity"] == SEV_INFO
        assert f["weight"] == 1.0
        assert f["source_severity"] == ""


def test_citability_le_chiavi_sono_ben_formate_e_uniche():
    """Tre segmenti, prefisso d'area, nessun duplicato quando piu'
    segnali sono deboli insieme."""
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI),
                                   "market": "atlantide"})
    chiavi = [f["key"] for f in esito["findings"]]
    assert len(chiavi) == len(set(chiavi))
    for chiave in chiavi:
        parti = chiave.split(".")
        assert parti[0] == AREA_PREFIX["mars_citability"] == "cit"
        assert len(parti) == 3


def test_citability_i_nomi_dei_segnali_sono_segmenti_validi():
    """La chiave si compone col nome interno del segnale e NON passa da
    `chiave_esterna`: il vocabolario e' scritto in questo file, e un
    refuso deve far fallire un test invece di essere ripulito in
    silenzio. E nessun segnale puo' chiamarsi "status", o le due
    famiglie collidereb bero."""
    for segnale in mars_citability.SEGNALI:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", segnale), segnale
        assert segnale != "status"


def test_citability_ogni_segnale_dice_da_quale_area_viene():
    """Un rilievo derivato senza indirizzo e' una lamentela: `sources`
    e' cio' che permettera' di agganciarlo ai rilievi veri."""
    rilievi = _rilievi(**DEBOLI_DISTINTI)
    assert rilievi["cit.seo.weak"]["params"]["sources"] == ["mars_seo"]
    # Il nome interno e l'etichetta viaggiano col rilievo: chi lo legge
    # non deve doverli estrarre dalla chiave o dal titolo.
    assert rilievi["cit.seo.weak"]["params"]["signal"] == "seo"
    assert rilievi["cit.seo.weak"]["params"]["label"] == "Qualità SEO"
    # Sempre una lista, anche di uno; e mai una tupla, che as_dict()
    # non converte e che in JSON diventerebbe comunque una lista.
    for f in rilievi.values():
        if "sources" in f["params"]:
            assert isinstance(f["params"]["sources"], list)
    senza = mars_citability.audit({"results": {"mars_tech": {"score": 50}}})
    per_chiave = {f["key"]: f for f in senza["findings"]}
    assert per_chiave["cit.recuperabilita.unmeasured"]["params"]["sources"] \
        == ["mars_lexical", "mars_semantic"], "due sorgenti, non una"


@pytest.mark.parametrize("segnale", list(mars_citability.ORIGINE))
def test_citability_origine_dice_davvero_chi_misura(segnale):
    """ORIGINE e' una SECONDA dichiarazione di cio' che raccogli_segnali
    legge: a tenerle insieme non c'e' un accorgimento ma questo test.

    Si costruiscono i results a partire dalla tabella, e il segnale
    corrispondente — e nessun altro — deve risultare misurato."""
    results = {}
    for modulo in mars_citability.ORIGINE[segnale]:
        results[modulo] = {"score": 50, "rank": [0, 1, 2],
                           "answer_shaped_ratio": 0.5}
    segnali = mars_citability.raccogli_segnali(results)
    assert segnali[segnale] is not None, "ORIGINE indica l'area sbagliata"


def test_citability_il_dato_porta_tutti_i_deboli_le_issues_due():
    """La vista compatta ne mostra due; il dato li porta tutti. E'
    l'asimmetria gia' scelta per i cinque alert ZAP."""
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI)})
    deboli = [f for f in esito["findings"] if f["key"].endswith(".weak")]
    assert len(deboli) == 4
    assert len([i for i in esito["issues"]
                if i.startswith("Segnale debole")]) == 2


def test_citability_i_deboli_escono_dal_peggiore():
    """L'ordine dei rilievi e' quello delle issues: valore crescente,
    il peggiore per primo."""
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI)})
    deboli = [f for f in esito["findings"] if f["key"].endswith(".weak")]
    assert [f["params"]["value"] for f in deboli] == [10.0, 30.0, 50.0, 59.0]
    assert [f["key"] for f in deboli] == [
        "cit.seo.weak", "cit.dati_strutturati.weak",
        "cit.accessibilita.weak", "cit.sicurezza.weak"]


def test_citability_a_parita_di_valore_decide_l_etichetta():
    """Il pareggio attraversa il taglio a due, quindi decide QUALE
    segnale diventa issue, non solo l'ordine.

    Il criterio e' l'etichetta italiana, non il nome interno: con
    `tecnica` e `answer_shaped` entrambi a 50, "Accesso e
    indicizzabilita'" precede "Contenuto in forma di risposta", mentre
    ordinando per nome interno vincerebbe `answer_shaped`. Sei coppie
    su ventuno si invertono fra i due criteri."""
    esito = mars_citability.audit({"results": _risultati(
        mars_tech={"score": 50}, mars_seo={"score": 40},
        mars_schema={"score": 100}, mars_wcag={"score": 100},
        mars_wapt={"score": 100},
        mars_semantic={"rank": [0, 1, 2], "answer_shaped_ratio": 0.5})})
    assert esito["issues"] == [
        "Segnale debole: Qualità SEO (40/100)",
        "Segnale debole: Accesso e indicizzabilità (50/100)"]
    deboli = [f["key"] for f in esito["findings"]
              if f["key"].endswith(".weak")]
    assert deboli == ["cit.seo.weak", "cit.tecnica.weak",
                      "cit.answer_shaped.weak"]


def test_citability_il_valore_nel_dato_non_e_arrotondato():
    """Il titolo stampa "%.0f" come la issue; il dato conserva il float.
    La vista arrotonda, il dato no."""
    esito = mars_citability.audit({"results": _risultati(
        mars_seo={"score": 59.6},
        mars_semantic={"rank": [0, 1, 2], "answer_shaped_ratio": 1.0})})
    debole = [f for f in esito["findings"] if f["key"] == "cit.seo.weak"][0]
    assert debole["params"]["value"] == 59.6
    assert debole["title"] == "Segnale debole: Qualità SEO (60/100)"


def test_citability_il_rilievo_debole_dice_la_soglia():
    """Un cit.sicurezza.weak che viaggi da solo nel piano o in un
    catalogo deve poter dire sotto quale soglia sia debole."""
    debole = _rilievi(**DEBOLI_DISTINTI)["cit.seo.weak"]
    assert debole["params"]["threshold"] == 60
    assert mars_citability.SOGLIA_DEBOLE == 60, "il valore, non la costante"


def test_citability_un_segnale_non_misurato_e_un_rilievo_per_segnale():
    """Una issue sola che li elenca tutti, un rilievo per segnale:
    aggregarli toglierebbe l'unica informazione azionabile — QUALE
    strumento manca — e renderebbe la chiave incomparabile fra due
    esecuzioni."""
    esito = mars_citability.audit({"results": {"mars_tech": {"score": 80}}})
    non_misurati = [f for f in esito["findings"]
                    if f["key"].endswith(".unmeasured")]
    assert len(non_misurati) == 6, "sei dei sette segnali"
    assert len([i for i in esito["issues"]
                if i.startswith("Segnali non misurati")]) == 1
    # e nell'ordine in cui la issue li elenca
    assert [f["params"]["label"] for f in non_misurati] == [
        e.strip() for e in
        esito["issues"][0].split(":", 1)[1].split(",")]


def test_citability_il_mercato_ignoto_conserva_quello_chiesto():
    """Il rilievo si costruisce PRIMA della riassegnazione: due righe
    piu' sotto `nome_mercato` vale gia' "global", e `requested` direbbe
    che l'utente ha chiesto proprio cio' che ha ottenuto."""
    esito = mars_citability.audit(
        {"results": _risultati(), "market": "atlantide"})
    rilievo = [f for f in esito["findings"]
               if f["key"] == "cit.status.unknown_market"][0]
    assert rilievo["params"]["requested"] == "atlantide"
    assert rilievo["params"]["used"] == "global"
    assert rilievo["params"]["known"] == ["cn", "eu", "global", "us"]
    # e con un mercato noto quel rilievo non c'e'
    noto = mars_citability.audit({"results": _risultati(), "market": "eu"})
    assert all(f["key"] != "cit.status.unknown_market"
               for f in noto["findings"])


def test_citability_il_composito_assente_e_un_rilievo_in_coda():
    """E' una conclusione, non una premessa: i segnali non misurati che
    lo precedono ne sono la causa.

    E non e' deducibile dai sette `unmeasured`: `profilo()` restituisce
    None anche quando i pesi si annullano, e dedurlo significherebbe
    reimplementarla nel consumatore."""
    esito = mars_citability.audit({"results": {"mars_tech": {"score": None}}})
    assert esito["score"] is None and esito["status"] == "unavailable"
    assert esito["findings"][-1]["key"] == "cit.status.no_composite"
    assert len(esito["findings"]) == 8, "sette segnali piu' la conclusione"
    # Con un composito calcolabile non c'e'.
    pieno = mars_citability.audit({"results": _risultati()})
    assert all(f["key"] != "cit.status.no_composite"
               for f in pieno["findings"])


def test_citability_senza_aree_porta_il_proprio_rilievo():
    """Anche l'uscita anticipata deve comparire negli elenchi che le
    fasi successive costruiranno sui findings."""
    esito = mars_citability.audit({"results": {}})
    assert [f["key"] for f in esito["findings"]] == ["cit.status.no_results"]
    assert esito["findings"][0]["severity"] == SEV_INFO


def test_citability_i_findings_arrivano_al_referto():
    """Il modulo puo' produrli perfetti e build_report buttarli via.

    Qui escono per DUE canali — la copia integrale del dict e la voce
    di area — ed e' l'unica area con questo doppio canale: chi rendera'
    i findings in HTML dovra' agganciarsi a uno solo."""
    from mars_report import build_report
    esito = mars_citability.audit({"results": _risultati(**DEBOLI_DISTINTI)})
    referto = build_report({"mars_citability": esito}, {"url": "https://x/"})
    area = [a for a in referto["areas"]
            if a["module"] == "mars_citability"][0]
    assert area["findings"] == esito["findings"]
    assert referto["citability"]["findings"] == esito["findings"]
    assert all(f["key"].startswith("cit.") for f in area["findings"])
    json.dumps(referto)


def test_citability_l_area_fallita_non_e_un_derivato():
    """L'eccezione all'invariante, e va conosciuta: `cit.status.error`
    lo sintetizza il referto, non il modulo, e non porta `derived`.

    E' giusto cosi': non e' una sintesi, e' un guasto del nostro
    strumento — e a differenza dei derivati non va escluso dai conteggi,
    perche' non lo sta gia' dicendo nessun altro."""
    from mars_report import build_report
    referto = build_report({"mars_citability": {"error": "RuntimeError"}},
                           {"url": "https://x/"})
    area = [a for a in referto["areas"]
            if a["module"] == "mars_citability"][0]
    assert [f["key"] for f in area["findings"]] == ["cit.status.error"]
    assert "derived" not in area["findings"][0]["params"]


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


# --- U1.9: i rilievi di stato di mars_llm_judge ------------------------
#
# Quest'area emette SOLO llm.status.*: i punti deboli che il modello
# nomina restano issues, perche' prosa libera non ha una chiave stabile.
# Conseguenza dichiarata: quando il giudizio RIESCE l'area non produce
# rilievi, ed e' l'unico punto della fase in cui la vista compatta dice
# piu' del dato canonico.

def _risposta_llm(payload, stop="end_turn"):
    """Una risposta dell'SDK, nella forma che `interroga` legge."""
    return _risposta_llm_grezza(json.dumps(payload), stop)


def _risposta_llm_grezza(testo, stop="end_turn"):
    """Come sopra, ma col testo VERBATIM invece che serializzato.

    Serve per il ramo `unreadable`: passare una stringa a
    `_risposta_llm` non lo esercita, perche' `json.dumps("x")` produce
    `"x"`, che e' JSON validissimo — il modello risponderebbe con una
    stringa e non con un oggetto, e `json.loads` non protesterebbe.
    """
    class Blocco:
        type = "text"
        text = testo

    class Risposta:
        content = [Blocco()]
        stop_reason = stop
    return Risposta()


class _ClientLLM:
    """Client finto: `esito` e' una risposta oppure un'eccezione."""

    def __init__(self, esito):
        self.esito = esito
        self.beta = type("B", (), {"messages": self})()

    def create(self, **kw):
        if isinstance(self.esito, BaseException):
            raise self.esito
        return self.esito


GIUDIZIO = {"citabilita": 71, "motivazione": "Motivo.",
            "punti_forti": ["A"], "punti_deboli": ["B", "C"],
            "passaggio_migliore": 0}


def _llm(contesto, esito=None, **cambi):
    """Un audit LLM col client iniettato: non tocca la rete, non spende."""
    contesto.update(dict({"llm": "on"}, **cambi))
    if esito is not None:
        contesto["_anthropic_client"] = _ClientLLM(esito)
    return mars_llm_judge.audit(contesto)


def _rami_llm(contesto, monkeypatch):
    """Tutti i rami che escono senza un giudizio, chiave attesa."""
    import anthropic
    senza_key = dict(contesto, llm="auto", credentials={})
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    return [
        ("llm.status.disabled", lambda: _llm(dict(contesto), llm="off")),
        ("llm.status.not_attempted",
         lambda: mars_llm_judge.audit(dict(senza_key))),
        ("llm.status.no_chunks",
         lambda: _llm(dict(contesto, chunks=[]),
                      _risposta_llm(GIUDIZIO))),
        ("llm.status.api_failed",
         lambda: _llm(dict(contesto),
                      anthropic.APIConnectionError(request=object()))),
        ("llm.status.no_credentials",
         lambda: _llm(dict(contesto),
                      TypeError("Could not resolve authentication method"))),
        ("llm.status.bad_call",
         lambda: _llm(dict(contesto), TypeError("kwarg ignoto 'foo'"))),
        ("llm.status.refused",
         lambda: _llm(dict(contesto),
                      _risposta_llm(GIUDIZIO, stop="refusal"))),
        # Il ramo generico ha ora un caso suo, che non e' il rifiuto:
        # un JSON che non si analizza. Senza, `unreadable` sarebbe
        # uscito dall'elenco dei rami e nessuno lo proverebbe piu'.
        ("llm.status.unreadable",
         lambda: _llm(dict(contesto), _risposta_llm_grezza("non e' JSON"))),
        ("llm.status.no_score",
         lambda: _llm(dict(contesto),
                      _risposta_llm(dict(GIUDIZIO, citabilita=None)))),
    ]


def test_llm_ogni_ramo_senza_giudizio_porta_un_rilievo(contesto, monkeypatch):
    """Senza l'area 9 il referto resta muto in ogni vista basata sui
    findings, e proprio nei casi in cui qualcosa non ha funzionato."""
    for chiave, esegui in _rami_llm(contesto, monkeypatch):
        esito = esegui()
        assert esito["score"] is None, chiave
        assert [f["key"] for f in esito["findings"]] == [chiave], chiave


def test_llm_le_chiavi_sono_tutte_di_stato_e_ben_formate(
        contesto, monkeypatch):
    """Tre segmenti, prefisso d'area preso dalla costante e non cablato:
    `llm.status.error` lo costruisce il referto proprio da AREA_PREFIX, e
    due spazi di nomi diversi non darebbero alcun errore."""
    chiavi = []
    for chiave, esegui in _rami_llm(contesto, monkeypatch):
        chiavi += [f["key"] for f in esegui()["findings"]]
    for chiave in chiavi:
        parti = chiave.split(".")
        assert parti[0] == AREA_PREFIX["mars_llm_judge"] == "llm"
        assert parti[1] == "status", "quest'area emette SOLO stati"
        assert len(parti) == 3
    assert "llm.status.error" not in chiavi, "quella e' del referto"


def test_llm_nessun_rilievo_e_un_difetto_del_sito(contesto, monkeypatch):
    """Una libreria mancante o un modello che risponde male non si
    riparano cambiando il sito: alzarne la gravita' li farebbe risalire
    sopra ogni rilievo reale nel piano di interventi."""
    for chiave, esegui in _rami_llm(contesto, monkeypatch):
        for f in esegui()["findings"]:
            assert f["severity"] == SEV_INFO, chiave
            assert f["weight"] == 1.0
            assert f["source_severity"] == ""
            assert "penalty" not in f["params"]
            # Il NOME del modulo, non il prefisso: `area` e `key` sono
            # due cose diverse, e a un carattere di distanza dall'errore
            # nessun test del progetto lo asseriva.
            assert f["area"] == "mars_llm_judge"


def test_llm_disattivato_non_e_un_esito_pulito(contesto):
    """`disabled` ha una chiave sua perche' e' l'unico esito che dipende
    da una SCELTA dell'utente. E resta `info`, non `ok`: `ok` significa
    "controllo eseguito e superato", mentre qui non e' stato eseguito
    nulla — sarebbe score 0 spacciato per score None al contrario."""
    esito = _llm(contesto, llm="off")
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "llm.status.disabled"
    assert rilievo["severity"] == SEV_INFO
    assert rilievo["params"]["attempted"] is False
    assert esito["issues"] == ["Giudizio LLM disattivato (--llm off)"]
    assert rilievo["title"] == "Giudizio LLM disattivato (--llm off)"


def test_llm_la_modalita_nel_dato_e_quella_normalizzata(contesto):
    """`params["mode"]` viene da `modalita`, non da context["llm"]: con
    "OFF" o None il valore grezzo e il ramo davvero preso divergono."""
    for grezzo, atteso in (("OFF", "off"), ("Off", "off")):
        esito = _llm(dict(contesto), llm=grezzo)
        assert esito["findings"][0]["params"]["mode"] == atteso


def test_llm_non_tentato_e_credenziale_non_risolta_sono_due_fatti(
        contesto, monkeypatch):
    """La chiave manca in entrambi, ma il primo si ripara anche con
    --llm on — lo dice il testo stesso della issue — e il secondo no."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    non_tentato = mars_llm_judge.audit(
        dict(contesto, llm="auto", credentials={}))
    non_risolta = _llm(dict(contesto),
                       TypeError("Could not resolve authentication method"))
    assert non_tentato["findings"][0]["key"] == "llm.status.not_attempted"
    assert non_risolta["findings"][0]["key"] == "llm.status.no_credentials"
    assert non_tentato["findings"][0]["params"]["attempted"] is False
    assert non_risolta["findings"][0]["params"]["attempted"] is True


def test_llm_la_credenziale_non_risolta_dice_in_quale_momento(contesto,
                                                              monkeypatch):
    """Che l'SDK sollevi costruendo il client o facendo la richiesta
    dipende dalla SUA versione, non da un fatto sull'audit: una chiave
    sola, e `stage` a distinguere il momento. Senza, un aggiornamento
    sposterebbe il fatto senza lasciare traccia."""
    import anthropic
    alla_richiesta = _llm(
        dict(contesto), TypeError("Could not resolve authentication method"))
    assert alla_richiesta["findings"][0]["params"]["stage"] == "request"

    monkeypatch.setattr(anthropic, "Anthropic",
                        lambda **kw: (_ for _ in ()).throw(
                            TypeError("niente credenziali")))
    ctx = dict(contesto, llm="on", credentials={})
    ctx.pop("_anthropic_client", None)
    alla_costruzione = mars_llm_judge.audit(ctx)
    rilievo = alla_costruzione["findings"][0]
    assert rilievo["key"] == "llm.status.no_credentials"
    assert rilievo["params"]["stage"] == "client"
    assert rilievo["params"]["attempted"] is False


def test_llm_una_chiamata_malformata_non_e_una_credenziale_mancante(
        contesto):
    """Un TypeError senza "authentication" nel messaggio vuol dire che la
    chiamata e' malformata — kwarg ignoto, SDK incompatibile — ed e' un
    difetto nostro. Fonderlo con l'altro rifarebbe il difetto che C2 ha
    gia' chiuso."""
    esito = _llm(contesto, TypeError("unexpected keyword argument 'foo'"))
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "llm.status.bad_call"
    assert rilievo["title"] == "Chiamata non valida", "il titolo e' fisso"
    assert "foo" in rilievo["detail"], "il messaggio sta in detail"
    assert esito["issues"] == [
        "Chiamata non valida: unexpected keyword argument 'foo'"]


def test_llm_il_rifiuto_dei_classificatori_ha_un_ramo_suo(contesto):
    """R31, chiusa. U1.9 aveva portato il motivo nel `detail`; la vista
    compatta continuava pero' a dire «Giudizio non interpretabile:
    RuntimeError», impreciso due volte — non c'e' alcun giudizio da
    interpretare, e il nome dell'eccezione Python non dice nulla a chi
    legge un referto."""
    esito = _llm(contesto, _risposta_llm(GIUDIZIO, stop="refusal"))
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "llm.status.refused"
    assert rilievo["detail"] == "richiesta declinata dai classificatori"
    assert esito["issues"] == [
        "Richiesta declinata dai classificatori del modello"]
    # La richiesta e' comunque partita: il conto di cio' che poteva
    # essere fatturato non deve sparire proprio nei rami che falliscono
    # DOPO l'invio.
    assert rilievo["params"]["attempted"] is True
    assert rilievo["params"]["chunks_sent"] >= 1


def test_llm_il_rifiuto_resta_un_runtimeerror(contesto):
    """`RichiestaDeclinata` e' sottoclasse di `RuntimeError`: un
    chiamante esterno che catturasse la vecchia eccezione continua a
    catturarla, e il ramo generico di `audit()` resta una rete."""
    assert issubclass(mars_llm_judge.RichiestaDeclinata, RuntimeError)


def test_llm_un_json_illeggibile_resta_non_interpretabile(contesto):
    """L'altra meta' della distinzione: qui il modello HA risposto, e la
    risposta non si legge. Sono due fatti diversi con due chiavi."""
    esito = _llm(contesto, _risposta_llm_grezza("questo non e' JSON"))
    assert esito["findings"][0]["key"] == "llm.status.unreadable"
    assert esito["issues"] == [
        "Giudizio non interpretabile: JSONDecodeError"]


def test_llm_una_chiave_sbagliata_non_e_una_chiave_assente(contesto):
    """`anthropic.AuthenticationError` E' un `APIError`, quindi una
    chiave scaduta o revocata esce come `api_failed` e non come
    `no_credentials`. Sono due fatti con riparazioni diverse — l'SDK non
    ha RISOLTO una credenziale contro l'API ha RIFIUTATO quella
    risolta — e `detail` porta il nome dell'eccezione, che si
    autonomina."""
    import anthropic
    assert issubclass(anthropic.AuthenticationError, anthropic.APIError)
    esito = _llm(contesto, anthropic.APIConnectionError(request=object()))
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "llm.status.api_failed"
    assert rilievo["detail"] == "APIConnectionError"


def test_llm_i_rami_dopo_l_invio_portano_la_traccia_della_spesa(contesto):
    """E' l'unica area che spende, e `costo_stimato` esce solo dal ramo
    di successo: la traccia spariva esattamente quando qualcosa andava
    storto DOPO l'invio."""
    riuscito = _llm(dict(contesto), _risposta_llm(GIUDIZIO))
    fallito = _llm(dict(contesto), TypeError("kwarg ignoto"))
    params = fallito["findings"][0]["params"]
    assert params["attempted"] is True
    assert params["model"] == mars_llm_judge.MODEL
    assert params["chunks_sent"] == riuscito["chunk_valutati"]
    # Non ricalcolato dal modulo — sarebbe circolare — ma confrontato col
    # ramo di successo sullo stesso contesto, che quel numero lo pubblica
    # gia' da prima di U1.9.
    assert params["estimated_input_tokens"] == \
        riuscito["costo_stimato"]["token_stimati_input"]


def test_llm_prima_dell_invio_non_c_e_traccia_di_spesa(contesto,
                                                       monkeypatch):
    """`attempted: False` e nessun numero: dichiarare un costo dove non
    e' partito nulla sarebbe peggio che tacerlo."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    for esito in (_llm(dict(contesto), llm="off"),
                  mars_llm_judge.audit(dict(contesto, llm="auto",
                                            credentials={})),
                  _llm(dict(contesto, chunks=[]),
                       _risposta_llm(GIUDIZIO))):
        params = esito["findings"][0]["params"]
        assert params["attempted"] is False
        assert "estimated_input_tokens" not in params
        assert "model" not in params


def test_llm_un_giudizio_riuscito_non_produce_rilievi(contesto):
    """Conseguenza dichiarata dell'ambito "solo llm.status.*": l'area
    compare negli elenchi basati sui findings SOLO quando non ha
    prodotto un giudizio.

    Qui la vista compatta dice piu' del dato canonico — le issues
    portano fino a tre punti deboli — ed e' l'unico punto della Fase 1
    in cui la divergenza va in questa direzione."""
    esito = _llm(contesto, _risposta_llm(GIUDIZIO))
    assert esito["score"] == 71
    assert esito["findings"] == []
    assert esito["issues"] == ["B", "C"], "i punti deboli restano issues"


def test_llm_una_risposta_senza_punteggio_lo_dichiara_in_testa(contesto):
    """`info` e non `warning` benche' sia una delusione: e' una
    risposta, non una misura, e resta un fatto sull'esecuzione."""
    esito = _llm(contesto, _risposta_llm(dict(GIUDIZIO, citabilita=None)))
    rilievo = esito["findings"][0]
    assert rilievo["key"] == "llm.status.no_score"
    assert rilievo["severity"] == SEV_INFO
    # in testa come la issue corrispondente
    assert esito["issues"][0].startswith("Il modello ha risposto senza")
    assert rilievo["title"] == esito["issues"][0]


def test_llm_la_rete_vera_e_bloccata_anche_per_httpx():
    """`niente_rete` copre `requests`; l'SDK Anthropic passa da httpx e
    non lo vede.

    Misurato prima di scrivere la fixture: un test con
    ANTHROPIC_API_KEY nell'ambiente e `llm: "auto"` faceva partire tre
    POST veri verso api.anthropic.com. Qui si verifica il MECCANISMO —
    che il transport sia sostituito — perche' verificarne l'effetto
    richiederebbe di tentare una richiesta, e la fixture fa fallire in
    teardown proprio i test che ci provano."""
    import httpx
    assert getattr(httpx.HTTPTransport.handle_request,
                   "_mars_blocca_la_rete", False), \
        "la rete vera non e' bloccata: un test puo' spendere"


def test_llm_i_findings_arrivano_al_referto(contesto):
    """Come mars_citability, quest'area esce dal referto per DUE canali:
    la voce d'area e la copia integrale in `llm_judgement`."""
    from mars_report import build_report
    esito = _llm(contesto, llm="off")
    referto = build_report({"mars_llm_judge": esito}, {"url": "https://x/"})
    area = [a for a in referto["areas"]
            if a["module"] == "mars_llm_judge"][0]
    assert area["findings"] == esito["findings"]
    assert referto["llm_judgement"]["findings"] == esito["findings"]
    json.dumps(referto)


# --- R45: due numeri sulla stessa area, e perche' differiscono --------
#
# Misurato su un sito vero (lymphatechnologies.com): Lighthouse dava 97
# all'accessibilita' e MARS 59, con lo STESSO strumento — axe-core — e
# lo STESSO difetto trovato da entrambi (color-contrast). Cambia solo
# l'aritmetica: Lighthouse fa una media pesata dei propri controlli su
# una pagina, MARS sottrae penalita' per gravita' e diffusione su un
# campione. Un cliente che apra PageSpeed accanto al referto vede i due
# numeri comunque: tacerne uno non li rende uguali.

def test_seo_pubblica_tutte_le_categorie_di_lighthouse():
    """Lighthouse le calcola tutte a ogni run, e finora quattro su
    cinque venivano buttate via insieme al resto del LHR."""
    esito = mars_seo.riassumi(_lhr())
    assert esito["lighthouse_scores"] == {
        "performance": 56.0, "accessibility": 97.0, "best-practices": 96.0,
        "agentic-browsing": 100.0, "seo": 27.0}


def test_seo_una_categoria_non_calcolata_resta_none():
    """`None` non e' zero: e' la distinzione di tutto il progetto."""
    lhr = _lhr()
    lhr["categories"]["performance"]["score"] = None
    assert mars_seo.punteggi_categorie(lhr)["performance"] is None


def test_seo_i_punteggi_di_categoria_non_hanno_falsa_precisione():
    """0.56 * 100 fa 56.00000000000001, che in un referto consegnato si
    legge come precisione che non c'e'. Lighthouse arrotonda gia' a due
    decimali sulla scala 0-1, quindi su 0-100 non si perde nulla."""
    for valore in mars_seo.punteggi_categorie(_lhr()).values():
        assert valore == round(valore, 2)


def test_seo_pubblica_le_categorie_anche_senza_il_punteggio_seo():
    """Il run e' riuscito: e' la sola categoria SEO a non essere
    calcolabile, e le altre quattro ci sono lo stesso."""
    lhr = _lhr()
    lhr["categories"]["seo"]["score"] = None
    esito = mars_seo.riassumi(lhr)
    assert esito["score"] is None and esito["status"] == "unavailable"
    assert esito["lighthouse_scores"]["accessibility"] == 97.0


def test_wcag_legge_il_numero_di_lighthouse_senza_rilanciarlo(contesto):
    """Nessun secondo Lighthouse: il numero e' gia' stato pagato da
    mars_seo, che gira prima in MODULES_REGISTRY."""
    contesto["results"] = {"mars_seo": mars_seo.riassumi(_lhr())}
    esito = mars_wcag.audit(contesto)
    assert esito["reference_score"] == 97.0
    assert esito["reference_tool"] == "Lighthouse"


def test_wcag_senza_lighthouse_non_inventa_un_secondo_numero(contesto):
    """Tre casi che portano allo stesso esito: Lighthouse assente,
    fallito, o quest'area invocata da sola dall'endpoint /audit/wcag."""
    for risultati in ({}, {"mars_seo": {"score": None,
                                        "status": "unavailable"}},
                      {"mars_seo": {"lighthouse_scores": {}}}):
        contesto["results"] = risultati
        esito = mars_wcag.audit(contesto)
        assert "reference_score" not in esito, risultati
        assert "reference_tool" not in esito, risultati


def test_wcag_il_confronto_c_e_anche_nel_ramo_di_ripiego(contesto,
                                                         monkeypatch):
    """Il ramo statico e' quello in cui il confronto serve di piu': il
    nostro numero e' un controllo di superficie, il suo no."""
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: False)
    contesto["results"] = {"mars_seo": mars_seo.riassumi(_lhr())}
    esito = mars_wcag.audit(contesto)
    assert esito["status"] == "surface"
    assert esito["reference_score"] == 97.0
