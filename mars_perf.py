#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — area 3: Prestazioni (Core Web Vitals di laboratorio).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0

Legge le metriche della categoria performance dallo STESSO referto
Lighthouse che l'area SEO ha gia' pagato — `context["results"]
["mars_seo"]["performance_metrics"]` — quindi non avvia nulla e non fa
una sola richiesta: e' il canale con cui l'accessibilita' legge il
proprio punteggio di riferimento (R45), e richiede di girare DOPO
mars_seo nel registro.

Il punteggio e' 100 meno le penalita' delle sole metriche sotto la
soglia «buono» (SOGLIA_BUONO, la scala 90/50 gia' dichiarata dal
referto): una metrica buona non costa nulla. Ogni penalita' e' il
contributo lineare esatto della metrica alla media pesata di
Lighthouse (`core/scoring.js`), come per l'area SEO — non una stima —
quindi la somma ricostruisce il punteggio e l'area e' certificabile
dal piano di interventi. Il punteggio di categoria di Lighthouse, che
sconta anche l'imperfezione delle metriche sopra soglia, resta accanto
come riferimento: chi apre PageSpeed vede due numeri e il perche'
divergono.

Che cosa quest'area NON copre, dichiarato:

- l'INP dei Core Web Vitals non si misura in laboratorio — Lighthouse
  lo raccoglie solo su interazioni reali (`supportedModes:
  ['timespan']`) e in navigation lo POTA dal referto, misurato su un
  LHR vero — quindi l'elenco dei controlli lo mostra come non
  misurato con una voce aggiunta da MARS invece di tacerlo, e il
  proxy pesato resta il TBT, come fa Lighthouse;
- la misura e' di laboratorio, su UNA pagina e con throttling
  simulato: e' la piu' rumorosa del referto fra due esecuzioni, ed e'
  la ragione per cui l'area resta fuori dal punteggio complessivo
  (`AREE_FUORI_DAL_COMPLESSIVO` in mars_report);
- i suggerimenti diagnostici di Lighthouse (render-blocking, immagini
  non ottimizzate...) non entrano: qui stanno le metriche e le loro
  soglie, la prescrizione la porta il catalogo dei fix.
"""

from __future__ import annotations

from typing import Dict

from mars_config import SOGLIA_BUONO, SOGLIA_MEDIO
from mars_core import Finding, SEV_INFO, SEV_WARNING, chiave_esterna

# id Lighthouse -> (chiave MARS, titolo del rilievo). Le soglie scritte
# nei titoli (2,5 s / 4 s per LCP, 0,1 / 0,25 per CLS) sono i valori
# che Google documenta per i Core Web Vitals: fatti del mondo, non
# tarature, quindi vivono nei testi accanto al codice e non in
# mars_config (perimetro di I8). FCP, TBT e Speed Index non portano
# numeri nel titolo: le loro curve cambiano col form factor, e un
# numero valido per il solo mobile diventerebbe falso su un referto
# desktop senza che nulla lo segnali.
CONTROLLI: Dict[str, tuple] = {
    "first-contentful-paint": (
        "perf.fcp.slow",
        "Primo contenuto lento: FCP %(valore)s"),
    "largest-contentful-paint": (
        "perf.lcp.slow",
        "LCP lento: %(valore)s — il contenuto principale dovrebbe "
        "comparire entro 2,5 s (scarso oltre 4 s)"),
    "total-blocking-time": (
        "perf.tbt.high",
        "Thread principale bloccato: TBT %(valore)s (proxy di "
        "laboratorio dell'INP)"),
    "cumulative-layout-shift": (
        "perf.cls.unstable",
        "Layout instabile: CLS %(valore)s — stabile fino a 0,1 "
        "(scarso oltre 0,25)"),
    "speed-index": (
        "perf.si.slow",
        "Pagina lenta a riempirsi: Speed Index %(valore)s"),
}

# La spiegazione di che cosa misura la metrica: e' il `detail` del
# rilievo. La prescrizione NON sta qui: la porta mars_fixes, per
# chiave, come per ogni altra area (U3.1).
DETTAGLI: Dict[str, str] = {
    "perf.fcp.slow":
        "Il First Contentful Paint misura quando compare il primo "
        "contenuto: fino ad allora la pagina e' bianca. Dipende quasi "
        "sempre da risorse che bloccano il rendering (CSS e font).",
    "perf.lcp.slow":
        "Il Largest Contentful Paint e' un Core Web Vital: misura "
        "quando compare l'elemento principale della pagina. Sopra i 4 "
        "secondi Google lo classifica scarso.",
    "perf.tbt.high":
        "Somma dei blocchi del thread principale oltre i 50 ms durante "
        "il caricamento: misura quanto la pagina resta sorda "
        "all'input. L'INP, il Core Web Vital corrispondente, esiste "
        "solo su interazioni reali: in laboratorio Lighthouse pesa "
        "questo proxy.",
    "perf.cls.unstable":
        "Il Cumulative Layout Shift e' un Core Web Vital: misura "
        "quanto il layout si sposta mentre la pagina carica. Sopra "
        "0,25 Google lo classifica scarso.",
    "perf.si.slow":
        "Lo Speed Index misura quanto in fretta si riempie la parte "
        "visibile della pagina.",
}


def _stato(chiave: str, testo: str, dettaglio: str = "",
           **params: object) -> dict:
    """Un fatto sull'ESECUZIONE, non un difetto del sito.

    Sempre `info` e senza `penalty`, come i `seo.status.*`: non si
    ripara cambiando il sito, e non deve scavalcare i rilievi reali
    nel piano di interventi.
    """
    return Finding(area="mars_perf", severity=SEV_INFO, key=chiave,
                   title=testo, detail=dettaglio,
                   params=dict(params)).as_dict()


def _misurata(metrica: dict) -> bool:
    """Vero se la metrica porta un punteggio numerico.

    I bool sono esclusi apposta: in Python `True` e' un `int` che vale
    1, e uno `score: true` malformato passerebbe per una metrica
    perfetta — stessa difesa di `istanze_del_rilievo` in mars_core.
    """
    punteggio = metrica.get("score")
    # Fuori da [0, 1] non e' un punteggio Lighthouse: trattarlo come
    # illeggibile lo dichiara, mentre usarlo produrrebbe penalita'
    # oltre il peso della metrica e un punteggio d'area negativo.
    return (isinstance(punteggio, (int, float))
            and not isinstance(punteggio, bool)
            and 0.0 <= punteggio <= 1.0)


def _valore(metrica: dict) -> str:
    """Il valore da mostrare: il testo di Lighthouse, se c'e'.

    `display_value` nasce gia' formattato nella lingua del run
    (`--locale`), quindi non si riformatta; il ripiego sul numero
    grezzo serve alle metriche di un LHR che non lo porta.
    """
    if metrica.get("display_value"):
        return str(metrica["display_value"])
    numero = metrica.get("numeric_value")
    if isinstance(numero, (int, float)):
        return ("%g %s" % (numero, metrica.get("numeric_unit") or "")).strip()
    return "n/d"


def _controllo(metrica: dict) -> Dict[str, object]:
    """Una voce dell'elenco controlli, nella forma che il referto rende.

    `manual` significa «non misurato», come per mars_seo: e' cosi' che
    l'INP — non misurabile in navigation — resta visibile con un `?`
    invece di sparire. Il titolo e' quello di Lighthouse (un nome
    proprio, non tradotto nemmeno dal suo locale italiano).
    """
    misurata = _misurata(metrica)
    return {"id": metrica.get("id"),
            "title": metrica.get("title") or metrica.get("id"),
            "passed": (misurata
                       and metrica["score"] * 100.0 >= SOGLIA_BUONO),
            "manual": not misurata,
            "items": [],
            "displayValue": _valore(metrica) if misurata else "",
            "explanation": "",
            "warnings": []}


def _rilievo(metrica: dict, totale_pesi: float, url: str) -> dict:
    """Il rilievo di una metrica sotto la soglia «buono».

    La penalita' e' `weight/totale * 100 * (1 - score)`: il contributo
    della metrica alla media pesata di Lighthouse, esatto e additivo
    (stessa formula di `mars_seo._penalita`, U1.7). La gravita' segue
    le bande gia' dichiarate dal referto — sotto SOGLIA_MEDIO e'
    un'avvertenza, sotto SOGLIA_BUONO un'informazione — e non arriva
    mai a `critical`: in MARS critico significa invisibile agli
    assistenti (U1.4), e una pagina lenta e' penalizzata, non
    invisibile.
    """
    punteggio = float(metrica["score"])
    penalita = (metrica["weight"] / totale_pesi * 100.0
                * (1.0 - punteggio))
    grave = punteggio * 100.0 < SOGLIA_MEDIO
    params: Dict[str, object] = {
        "rule": metrica.get("id"),
        "valore": _valore(metrica),
        "numeric_value": metrica.get("numeric_value"),
        "numeric_unit": metrica.get("numeric_unit"),
        "lh_score": punteggio,
        "penalty": penalita,
    }
    if metrica.get("text_lang"):
        # Il valore nel titolo e' formattato da Lighthouse nel locale
        # del run («1.200 ms» non e' «1,2 ms»): si dichiara come fanno
        # axe, ZAP e mars_seo.
        params["text_lang"] = metrica["text_lang"]
    if url:
        # La pagina che Lighthouse dichiara di aver misurato: e' cio'
        # che colora la treemap (R47). Senza URL non si inventa.
        params["urls"] = [url]
    voce = CONTROLLI.get(metrica["id"])
    if voce:
        chiave, modello = voce
        titolo = modello % {"valore": params["valore"]}
        dettaglio = DETTAGLI[chiave]
    else:
        # Una metrica pesata che non conosciamo — un run timespan con
        # l'INP, o una metrica futura di Lighthouse. Il DATO vince: il
        # deficit entra nel punteggio e il rilievo esiste, col titolo
        # dello strumento, come per axe e ZAP (famiglia dinamica
        # `perf.lh.*`, senza prescrizione nostra). L'accesso diretto a
        # CONTROLLI qui sollevava KeyError e faceva cadere l'intera
        # area: il contrario di «vincere».
        chiave = "perf.lh.%s" % chiave_esterna(str(metrica.get("id") or ""))
        titolo = "%s: %s" % (metrica.get("title") or metrica.get("id"),
                             params["valore"])
        dettaglio = ""
    return Finding(area="mars_perf",
                   severity=SEV_WARNING if grave else SEV_INFO,
                   title=titolo,
                   key=chiave,
                   detail=dettaglio,
                   weight=2.0 if grave else 1.0,
                   params=params).as_dict()


def valuta(seo: dict) -> dict:
    """Il risultato d'area a partire dal risultato di mars_seo.

    Separata da audit() perche' e' la parte con le decisioni, e si
    verifica su un dict costruito a mano, senza Lighthouse.
    """
    metriche = [m for m in (seo.get("performance_metrics") or [])
                if isinstance(m, dict)]
    pesate = [m for m in metriche if (m.get("weight") or 0) > 0]
    totale_pesi = sum(m["weight"] for m in pesate)
    leggibili = [m for m in pesate if _misurata(m)]
    illeggibili = [m for m in pesate if not _misurata(m)]
    sotto_soglia = [m for m in leggibili
                    if m["score"] * 100.0 < SOGLIA_BUONO]

    url = str(seo.get("audited_url") or "")
    findings = [_rilievo(m, totale_pesi, url) for m in sotto_soglia]
    controlli = [_controllo(m) for m in metriche]
    if not any(m.get("id") == "interaction-to-next-paint"
               for m in metriche):
        # In modalita' navigation Lighthouse POTA l'INP dal referto
        # (`supportedModes: ['timespan']`): la metrica non arriva
        # nemmeno come non applicabile — misurato sul LHR vero, mentre
        # la prima fixture la congelava presente, cioe' una forma che
        # in produzione non esiste. La voce e' quindi NOSTRA: dichiara
        # che il Core Web Vital dell'interazione non si misura in
        # laboratorio, invece di tacerlo. Nome proprio e niente prosa,
        # cosi' non c'e' nulla da tradurre; se un giorno un run
        # (timespan) la portasse davvero, il dato vince su questa
        # dichiarazione.
        controlli.append({"id": "interaction-to-next-paint",
                          "title": "Interaction to Next Paint (INP)",
                          "passed": False, "manual": True, "items": [],
                          "displayValue": "", "explanation": "",
                          "warnings": []})
    esito: Dict[str, object] = {
        "issues": [f["title"] for f in findings],
        "findings": findings,
        "audits": controlli or None,
        "tool": seo.get("tool"),
        "form_factor": seo.get("form_factor"),
    }

    if illeggibili:
        # Come il ramo `not_scored` di mars_seo (R40): il punteggio non
        # si ricava dalle metriche leggibili — sarebbe inventare la
        # media che Lighthouse non ha potuto fare — ma i rilievi
        # leggibili restano, con la loro penalita'. Senza punteggio
        # l'area non si certifica e il piano li mette in corsia
        # «ignoto»: e' la catena giusta, e la dichiara.
        nomi = ", ".join(str(m.get("title") or m.get("id"))
                         for m in illeggibili)
        esito["score"] = None
        esito["status"] = "unavailable"
        esito["issues"] = (["Lighthouse non ha misurato: %s" % nomi]
                           + esito["issues"])
        esito["findings"] = [_stato(
            "perf.status.not_scored",
            "Lighthouse non ha misurato tutte le metriche di "
            "prestazione",
            "Senza tutte le metriche pesate la media non si "
            "ricostruisce, e un punteggio ricavato dalle sole "
            "leggibili sarebbe inventato. Mancano: %s." % nomi,
            metriche=[str(m.get("id")) for m in illeggibili],
        )] + findings
        return esito

    # 100 meno cio' che le metriche sotto soglia costano nella formula
    # di Lighthouse. Le buone non costano nulla: e' la differenza,
    # dichiarata, col punteggio di categoria qui accanto.
    #
    # NIENTE arrotondamento, e non e' trascuratezza: il certificato
    # d'area confronta round(100 - somma_penalita) con round(score), e
    # uno score gia' arrotondato a un decimale li fa divergere quando
    # 100 - somma cade su un mezzo — misurato su 200.000 combinazioni
    # di punteggi, ~4% di aree «non certificate» per un artefatto.
    # Grezzo e' anche il precedente di mars_seo (`punteggio * 100`), e
    # le viste arrotondano da se'.
    esito["score"] = 100.0 - sum(
        f["params"]["penalty"] for f in findings)

    # Il pattern R45: accanto al nostro numero, quello che Lighthouse
    # pubblica per la stessa categoria — la direzione della differenza
    # la dichiara il referto leggendo i due valori. `is not None` e non
    # la verita' del valore: uno zero dell'altro strumento non deve
    # sparire. Solo nel ramo misurato: senza il nostro punteggio non
    # c'e' un confronto da dichiarare.
    riferimento = (seo.get("lighthouse_scores") or {}).get("performance")
    if isinstance(riferimento, (int, float)):
        esito["reference_score"] = float(riferimento)
        esito["reference_tool"] = "Lighthouse"
    return esito


def audit(context: dict) -> dict:
    """Punto di ingresso del modulo (contratto MARS)."""
    seo = (context.get("results") or {}).get("mars_seo") or {}
    metriche = seo.get("performance_metrics") or []
    pesate = [m for m in metriche
              if isinstance(m, dict) and (m.get("weight") or 0) > 0]
    if not pesate:
        return {
            "score": None, "status": "unavailable",
            "issues": ["Metriche di prestazione non disponibili: "
                       "l'area SEO non ha prodotto un referto "
                       "Lighthouse, e le prestazioni si leggono dallo "
                       "stesso run"],
            "findings": [_stato(
                "perf.status.no_data",
                "Metriche di prestazione non disponibili",
                "L'area legge i Core Web Vitals dal referto Lighthouse "
                "dell'area SEO, senza un secondo run: se Lighthouse "
                "non ha girato, qui non c'e' nulla da misurare.")],
        }
    return valuta(seo)
