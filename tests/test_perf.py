#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — test dell'area Prestazioni (I10).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0

L'area legge i Core Web Vitals dallo stesso LHR dell'area SEO
(`context["results"]["mars_seo"]["performance_metrics"]`), senza un
secondo Lighthouse. Qui si fissano le decisioni prese con I10:

- score = 100 meno le penalita' delle sole metriche sotto «buono»
  (90/100): una metrica buona non costa nulla;
- la penalita' e' il contributo lineare esatto alla media pesata di
  Lighthouse, non una stima — quindi l'area e' CERTIFICABILE;
- il punteggio di categoria di Lighthouse resta accanto come
  riferimento (pattern R45);
- l'INP non si misura in laboratorio e l'elenco dei controlli lo
  dichiara invece di tacerlo.
"""

from __future__ import annotations

import pytest

import mars_core
import mars_perf
import mars_remediation
import mars_report
import mars_seo

from test_modules import _lhr


def _metrica(id_, score, weight, display="", value=None, unit=None,
             mode="numeric", title=None):
    return {"id": id_, "title": title or id_, "score": score,
            "mode": mode, "weight": weight, "numeric_value": value,
            "numeric_unit": unit, "display_value": display,
            "text_lang": "it"}


# Cinque metriche pesate piu' l'INP, con la media pesata che vale
# 0.5625: FCP e CLS sopra la soglia «buono», LCP e TBT sotto il 50,
# SI in mezzo. E' la stessa forma che il LHR sintetico dei golden
# congela.
METRICHE_TIPO = [
    _metrica("first-contentful-paint", 0.95, 10, "1,8 s",
             1800, "millisecond"),
    _metrica("largest-contentful-paint", 0.45, 25, "4,3 s",
             4300, "millisecond"),
    _metrica("total-blocking-time", 0.28, 30, "890 ms",
             890, "millisecond"),
    _metrica("cumulative-layout-shift", 0.92, 25, "0,05",
             0.05, "unitless"),
    _metrica("speed-index", 0.75, 10, "4,2 s", 4200, "millisecond"),
    _metrica("interaction-to-next-paint", None, 0, mode="notApplicable",
             title="Interaction to Next Paint"),
]


def _contesto(metriche=None, **extra):
    seo = {"performance_metrics": (METRICHE_TIPO if metriche is None
                                   else metriche),
           "lighthouse_scores": {"performance": 56.0},
           "tool": "Lighthouse 13.4.1",
           "form_factor": "mobile",
           "audited_url": "https://esempio.test/"}
    seo.update(extra)
    return {"results": {"mars_seo": seo}}


# ----------------------------------------------------------------------
# Il canale: senza il referto dell'area SEO non c'e' nulla da misurare
# ----------------------------------------------------------------------

def test_perf_senza_risultati_seo_e_non_misurato():
    """Niente secondo Lighthouse: se l'area SEO non ha prodotto un LHR,
    qui si dichiara «non misurato» — mai uno zero."""
    for contesto in ({}, {"results": {}},
                     {"results": {"mars_seo": {"score": None,
                                               "status": "unavailable"}}}):
        esito = mars_perf.audit(contesto)
        assert esito["score"] is None
        assert esito["status"] == "unavailable"
        assert esito["findings"][0]["key"] == "perf.status.no_data"
        assert "penalty" not in esito["findings"][0]["params"]
        assert esito["issues"]


# ----------------------------------------------------------------------
# Il punteggio: 100 meno le penalita' sotto soglia, e si ricostruisce
# ----------------------------------------------------------------------

def test_perf_score_e_100_meno_le_penalita_sotto_soglia():
    esito = mars_perf.audit(_contesto())
    # LCP 25*0.55 + TBT 30*0.72 + SI 10*0.25 = 37.85. Lo score e'
    # GREZZO, non arrotondato: il certificato d'area confronta
    # round(100 - somma) con round(score), e un decimale gia'
    # arrotondato li fa divergere quando 100 - somma cade su un mezzo.
    assert esito["score"] == pytest.approx(62.15)
    assert esito["score"] == (
        100.0 - sum(f["params"]["penalty"] for f in esito["findings"]))
    assert {f["key"] for f in esito["findings"]} == {
        "perf.lcp.slow", "perf.tbt.high", "perf.si.slow"}


def test_perf_una_metrica_buona_non_produce_rilievi_ne_costa():
    chiavi = {f["key"] for f in mars_perf.audit(_contesto())["findings"]}
    assert "perf.fcp.slow" not in chiavi
    assert "perf.cls.unstable" not in chiavi


def test_perf_tutte_buone_e_un_area_pulita():
    metriche = [_metrica("largest-contentful-paint", 0.98, 25, "1,2 s"),
                _metrica("cumulative-layout-shift", 1.0, 25, "0")]
    esito = mars_perf.audit(_contesto(metriche))
    assert esito["score"] == 100.0
    assert esito["findings"] == [] and esito["issues"] == []


def test_perf_la_penalita_e_il_contributo_lineare_esatto():
    """weight/totale * 100 * (1 - score): la formula di mars_seo (U1.7),
    esatta e invertibile, non una scelta editoriale."""
    per_chiave = {f["key"]: f for f in
                  mars_perf.audit(_contesto())["findings"]}
    assert (per_chiave["perf.tbt.high"]["params"]["penalty"]
            == pytest.approx(21.6))
    assert (per_chiave["perf.lcp.slow"]["params"]["penalty"]
            == pytest.approx(13.75))


def test_perf_l_area_e_certificata():
    """La somma delle penalita' dichiarate ricostruisce il punteggio:
    e' cio' che tiene le voci perf.* nel piano con i numeri, invece
    che in corsia «ignoto»."""
    esito = mars_perf.audit(_contesto())
    area = {"module": "mars_perf", "label": "3. Prestazioni",
            "score": esito["score"], "findings": esito["findings"]}
    assert mars_remediation.certificato_area(area)["certified"]


def test_perf_certificata_anche_quando_la_somma_cade_su_un_mezzo():
    """Il caso che il doppio arrotondamento perdeva: con questi
    punteggi la somma delle penalita' fa 54.55, e uno score gia'
    arrotondato a un decimale (45.5) certificava 46 contro 45 —
    misurato su 200.000 combinazioni, ~4% di aree «non certificate»
    per un artefatto. Lo score resta grezzo apposta."""
    punteggi = {"first-contentful-paint": 0.67,
                "largest-contentful-paint": 0.35,
                "total-blocking-time": 0.66,
                "cumulative-layout-shift": 0.30,
                "speed-index": 0.27}
    pesi = {"first-contentful-paint": 10, "largest-contentful-paint": 25,
            "total-blocking-time": 30, "cumulative-layout-shift": 25,
            "speed-index": 10}
    metriche = [_metrica(nome, punteggi[nome], pesi[nome], "n/a")
                for nome in punteggi]
    esito = mars_perf.audit(_contesto(metriche))
    area = {"module": "mars_perf", "label": "3. Prestazioni",
            "score": esito["score"], "findings": esito["findings"]}
    certificato = mars_remediation.certificato_area(area)
    assert certificato["certified"], certificato["reason"]


def test_perf_una_metrica_sconosciuta_vince_invece_di_far_cadere_l_area():
    """La promessa «il dato vince» resa vera: una metrica pesata fuori
    dal catalogo dei cinque id — un run timespan con l'INP, una
    metrica futura di Lighthouse — produce un rilievo dinamico
    `perf.lh.*` col titolo dello strumento e la sua penalita', invece
    del KeyError che faceva uscire l'area in `status: error` (e un
    500 sull'endpoint). Trovato dalla revisione avversariale."""
    metriche = [_metrica("interaction-to-next-paint", 0.4, 25, "620 ms",
                         title="Interaction to Next Paint"),
                _metrica("largest-contentful-paint", 0.95, 25, "1,9 s")]
    esito = mars_perf.audit(_contesto(metriche))
    assert esito.get("status") is None
    rilievo, = esito["findings"]
    assert rilievo["key"] == "perf.lh.interaction_to_next_paint"
    assert "Interaction to Next Paint" in rilievo["title"]
    assert "620 ms" in rilievo["title"]
    assert rilievo["params"]["penalty"] == pytest.approx(
        25 / 50 * 100 * 0.6)
    assert esito["score"] == pytest.approx(100 - 25 / 50 * 100 * 0.6)


def test_perf_uno_score_ostile_e_illeggibile_non_perfetto():
    """`True` e' un int che vale 1, e un punteggio fuori da [0, 1] non
    e' un punteggio Lighthouse: contarli produrrebbe un 100 regalato o
    un'area negativa. Si dichiarano illeggibili (stessa difesa di
    `istanze_del_rilievo`)."""
    for ostile in (True, -2.0, 1.5):
        metriche = [_metrica("largest-contentful-paint", ostile, 25)]
        esito = mars_perf.audit(_contesto(metriche))
        assert esito["score"] is None, repr(ostile)
        assert esito["status"] == "unavailable"
        assert esito["findings"][0]["key"] == "perf.status.not_scored"


def test_perf_il_valore_nel_titolo_dichiara_la_propria_lingua():
    """«1.200 ms» formattato da un run italiano letto in un referto
    inglese sono 1,2 ms: il valore e' testo dello strumento, e il
    rilievo lo dichiara in params["text_lang"] come fanno axe, ZAP e
    mars_seo."""
    for f in mars_perf.audit(_contesto())["findings"]:
        assert f["params"]["text_lang"] == "it"


# ----------------------------------------------------------------------
# Le bande: quelle della scala gia' dichiarata dal referto (90/50)
# ----------------------------------------------------------------------

def test_perf_il_confine_del_buono_e_novanta():
    """0.9 esatto e' buono (nessun rilievo); appena sotto no.
    Il caso di confine e' l'unico che distingue < da <= (U13)."""
    al_limite = [_metrica("largest-contentful-paint", 0.9, 25, "2,5 s")]
    assert mars_perf.audit(_contesto(al_limite))["findings"] == []
    sotto = [_metrica("largest-contentful-paint", 0.89, 25, "2,6 s")]
    rilievi = mars_perf.audit(_contesto(sotto))["findings"]
    assert [f["key"] for f in rilievi] == ["perf.lcp.slow"]


def test_perf_il_confine_del_grave_e_cinquanta():
    """0.5 esatto resta info; appena sotto diventa warning, e il peso
    canonico segue la gravita' (D2: la granularita' sta nel peso)."""
    al_limite = [_metrica("total-blocking-time", 0.5, 30, "600 ms")]
    rilievo = mars_perf.audit(_contesto(al_limite))["findings"][0]
    assert rilievo["severity"] == mars_core.SEV_INFO
    assert rilievo["weight"] == 1.0
    sotto = [_metrica("total-blocking-time", 0.49, 30, "620 ms")]
    rilievo = mars_perf.audit(_contesto(sotto))["findings"][0]
    assert rilievo["severity"] == mars_core.SEV_WARNING
    assert rilievo["weight"] == 2.0


def test_perf_nessun_rilievo_e_mai_critico():
    """In MARS `critical` significa invisibile agli assistenti (U1.4):
    una pagina lenta e' penalizzata, non invisibile."""
    pessime = [_metrica(m["id"], 0.0, m["weight"], "n/a")
               for m in METRICHE_TIPO if m["weight"] > 0]
    for f in mars_perf.audit(_contesto(pessime))["findings"]:
        assert f["severity"] != mars_core.SEV_CRITICAL


# ----------------------------------------------------------------------
# Cio' che il rilievo dichiara: pagina, aggancio, valore
# ----------------------------------------------------------------------

def test_perf_il_rilievo_dichiara_pagina_e_regola():
    rilievo = mars_perf.audit(_contesto())["findings"][0]
    assert rilievo["params"]["urls"] == ["https://esempio.test/"]
    assert rilievo["params"]["rule"] in {m["id"] for m in METRICHE_TIPO}
    assert rilievo["params"]["valore"]
    assert rilievo["params"]["valore"] in rilievo["title"]


def test_perf_senza_url_misurato_non_si_inventa_la_pagina():
    contesto = _contesto()
    contesto["results"]["mars_seo"]["audited_url"] = None
    for f in mars_perf.audit(contesto)["findings"]:
        assert "urls" not in f["params"]


def test_perf_dichiara_il_riferimento_lighthouse():
    """Il pattern R45: il nostro numero e quello di Lighthouse, con la
    ragione della divergenza. La condizione e' `is not None`, non la
    verita': uno zero di Lighthouse non deve sparire."""
    esito = mars_perf.audit(_contesto())
    assert esito["reference_score"] == 56.0
    assert esito["reference_tool"] == "Lighthouse"
    contesto = _contesto(lighthouse_scores={"performance": None})
    esito = mars_perf.audit(contesto)
    assert "reference_score" not in esito
    zero = mars_perf.audit(_contesto(lighthouse_scores={"performance": 0.0}))
    assert zero["reference_score"] == 0.0


def test_perf_eredita_strumento_e_dispositivo():
    esito = mars_perf.audit(_contesto())
    assert esito["tool"] == "Lighthouse 13.4.1"
    assert esito["form_factor"] == "mobile"


# ----------------------------------------------------------------------
# I controlli: tutte le metriche, INP compreso, superati distinguibili
# ----------------------------------------------------------------------

def test_perf_l_elenco_controlli_copre_tutte_le_metriche():
    controlli = mars_perf.audit(_contesto())["audits"]
    assert [c["id"] for c in controlli] == [m["id"] for m in METRICHE_TIPO]
    per_id = {c["id"]: c for c in controlli}
    assert per_id["first-contentful-paint"]["passed"]
    assert per_id["cumulative-layout-shift"]["passed"]
    assert not per_id["largest-contentful-paint"]["passed"]


def test_perf_l_inp_si_dichiara_non_misurato():
    """L'INP non si misura in laboratorio (`supportedModes:
    ['timespan']` in Lighthouse): l'elenco lo mostra come non misurato
    invece di tacerlo, e non entra mai nel punteggio. Qui il dato c'e'
    (come in un run timespan) ed e' illeggibile: vince il dato."""
    per_id = {c["id"]: c for c in mars_perf.audit(_contesto())["audits"]}
    inp = per_id["interaction-to-next-paint"]
    assert inp["manual"] and not inp["passed"]
    misurate = [c for c in per_id.values() if not c["manual"]]
    assert len(misurate) == 5


def test_perf_l_inp_si_dichiara_anche_quando_il_lhr_lo_pota():
    """In modalita' navigation Lighthouse pota l'INP dal referto —
    misurato sul LHR vero, non dedotto dalla configurazione: la prima
    fixture lo congelava presente, cioe' una forma che in produzione
    non esiste. La voce non misurata la aggiunge MARS, e la
    dichiarazione non dipende da cio' che lo strumento ha taciuto."""
    senza_inp = [m for m in METRICHE_TIPO
                 if m["id"] != "interaction-to-next-paint"]
    controlli = mars_perf.audit(_contesto(senza_inp))["audits"]
    inp = [c for c in controlli
           if c["id"] == "interaction-to-next-paint"]
    assert len(inp) == 1
    assert inp[0]["manual"] and not inp[0]["passed"]
    # E quando il dato c'e' (timespan), la voce non si duplica.
    doppioni = [c for c in mars_perf.audit(_contesto())["audits"]
                if c["id"] == "interaction-to-next-paint"]
    assert len(doppioni) == 1


def test_perf_le_issues_sono_la_vista_compatta_dei_rilievi():
    esito = mars_perf.audit(_contesto())
    assert esito["issues"] == [f["title"] for f in esito["findings"]]


# ----------------------------------------------------------------------
# Una metrica pesata illeggibile: non misurato, non inventato
# ----------------------------------------------------------------------

def test_perf_una_metrica_pesata_illeggibile_toglie_il_punteggio():
    """Come il ramo `not_scored` di mars_seo (R40): il punteggio non si
    ricava dalle metriche leggibili — sarebbe inventare la media che
    Lighthouse non ha potuto fare — ma i rilievi leggibili restano,
    con la loro penalita' (corsia «ignoto» nel piano, dichiarata)."""
    metriche = [_metrica("largest-contentful-paint", None, 25, "",
                         mode="error"),
                _metrica("total-blocking-time", 0.28, 30, "890 ms")]
    esito = mars_perf.audit(_contesto(metriche))
    assert esito["score"] is None
    assert esito["status"] == "unavailable"
    assert esito["findings"][0]["key"] == "perf.status.not_scored"
    assert "penalty" not in esito["findings"][0]["params"]
    chiavi = [f["key"] for f in esito["findings"][1:]]
    assert chiavi == ["perf.tbt.high"]
    # Il denominatore sono i pesi PRESENTI (25+30=55), illeggibile
    # compreso: e' la normalizzazione che Lighthouse fa sulla propria
    # categoria, non un 100 assunto.
    assert (esito["findings"][1]["params"]["penalty"]
            == pytest.approx(30 / 55 * 100 * 0.72))
    # Senza il nostro punteggio non c'e' un confronto da dichiarare.
    assert "reference_score" not in esito


def test_perf_la_nota_del_riferimento_dichiara_la_direzione_giusta():
    """La nota di R45 nacque per l'accessibilita', dove MARS e' piu'
    severo; per le prestazioni vale l'opposto — le metriche sopra
    soglia non costano nulla — e una frase sola direbbe il falso in
    uno dei due casi. La direzione si legge dal confronto."""
    def nota(score, riferimento):
        area = {"module": "mars_perf", "label": "3. Prestazioni",
                "score": score, "reference_score": riferimento,
                "reference_tool": "Lighthouse"}
        return " ".join(mars_report._qualificatori(area))

    assert "più indulgente" in nota(58.2, 56.0)
    assert "più severa" in nota(37.0, 97.0)
    # Pari, o senza il nostro numero: nessuna direzione da affermare.
    assert "più" not in nota(56.0, 56.0)
    assert "scala diversa" in nota(56.0, 56.0)


# ----------------------------------------------------------------------
# Il contratto col resto di MARS
# ----------------------------------------------------------------------

def test_perf_sta_nel_registro_subito_dopo_seo():
    nomi = [nome for nome, _ in mars_core.MODULES_REGISTRY]
    assert nomi.index("mars_perf") == nomi.index("mars_seo") + 1
    etichette = dict(mars_core.MODULES_REGISTRY)
    assert etichette["mars_perf"] == "3. Prestazioni"
    assert mars_core.AREA_PREFIX["mars_perf"] == "perf"


def test_perf_resta_fuori_dal_complessivo():
    """Decisione I10: misura di laboratorio su una pagina, la piu'
    rumorosa del referto fra due esecuzioni — il complessivo deve
    muoversi col sito, non col rumore dello strumento."""
    assert "mars_perf" in mars_report.AREE_FUORI_DAL_COMPLESSIVO


# ----------------------------------------------------------------------
# La sorgente: mars_seo pubblica le metriche dello stesso LHR
# ----------------------------------------------------------------------

def test_seo_pubblica_le_metriche_di_performance():
    """Cinque metriche, non sei: in navigation Lighthouse pota l'INP
    dal referto, e la fixture e' fedele a quella forma."""
    esito = mars_seo.riassumi(_lhr())
    metriche = esito["performance_metrics"]
    assert [m["id"] for m in metriche] == [
        "first-contentful-paint", "largest-contentful-paint",
        "total-blocking-time", "cumulative-layout-shift", "speed-index"]
    per_id = {m["id"]: m for m in metriche}
    assert per_id["total-blocking-time"]["weight"] == 30
    assert per_id["total-blocking-time"]["score"] == 0.28
    assert per_id["total-blocking-time"]["display_value"]


def test_seo_le_metriche_escludono_il_gruppo_hidden():
    """`interactive` (TTI) sta nella categoria con `group: 'hidden'`:
    non e' una metrica pesata ne' mostrata da Lighthouse, e portarla
    fra i controlli direbbe che e' stata giudicata."""
    ids = {m["id"] for m in mars_seo.riassumi(_lhr())["performance_metrics"]}
    assert "interactive" not in ids


def test_seo_pubblica_le_metriche_anche_senza_categoria_seo():
    """Il ramo `not_scored` della categoria SEO non deve costare le
    prestazioni: sono categorie diverse dello stesso run. E col
    CORREDO — strumento, dispositivo, pagina misurata — perche' senza
    l'`audited_url` i rilievi delle prestazioni uscirebbero dalla
    treemap senza un errore (R47), mentre il LHR lo porta. Trovato
    dalla revisione avversariale."""
    lhr = _lhr(punteggio=None)
    esito = mars_seo.riassumi(lhr)
    assert esito["status"] == "unavailable"
    assert esito["performance_metrics"]
    assert esito["tool"] == "Lighthouse 13.4.1"
    assert esito["form_factor"] == "mobile"
    assert esito["audited_url"] == "https://esempio.test/"
    # E la catena intera: i rilievi di mars_perf su quel risultato
    # portano la pagina.
    area = mars_perf.audit({"results": {"mars_seo": esito}})
    assert area["score"] is not None
    for f in area["findings"]:
        assert f["params"]["urls"] == ["https://esempio.test/"]
