#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — il piano di interventi (U4).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os

import pytest

import mars_citability
import mars_fixes
import mars_remediation as rem
from mars_core import SEV_CRITICAL, SEV_INFO, SEV_WARNING

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


def _rilievo(**kw) -> dict:
    """Un rilievo gia' serializzato, come lo consuma il piano.

    Dict e non `Finding`: e' cio' che attraversa il confine dei plugin
    e cio' che arriva a `build_remediation` dentro il referto.
    """
    base = {"area": "mars_tech", "severity": SEV_CRITICAL, "title": "Titolo",
            "key": "tech.robots.ai_blocked", "detail": "", "fix": "Fai X.",
            "example": "", "url": "", "weight": 2.0, "source_severity": "",
            "params": {"penalty": 40.0}}
    base.update(kw)
    return base


def _area(modulo="mars_tech", score=57, rilievi=None, **kw) -> dict:
    area = {"module": modulo, "label": "1. Tecnica", "score": score,
            "status": None, "issues": [], "findings": rilievi or []}
    area.update(kw)
    return area


def _referto(aree, citability=None) -> dict:
    return {"areas": aree, "citability": citability or {}}


def _golden(nome: str) -> dict:
    with open(os.path.join(GOLDEN, nome), encoding="utf-8") as fh:
        return json.load(fh)


# ----------------------------------------------------------------------
# R(): la stessa aritmetica dei moduli, scritta una volta sola
# ----------------------------------------------------------------------

@pytest.mark.parametrize("penalita,atteso", [
    (0, 100), (43, 57), (10, 90), (63, 37),
    # Il clamp: oltre 100 di penalita' il punteggio non scende sotto zero.
    (100, 0), (108, 0), (154, 0),
    # L'arrotondamento e' quello di Python — al pari — ed e' lo stesso
    # che i moduli applicano: 100 - 72.5 fa 27.5, che diventa 28.
    (72.5, 28), (71.5, 28),
])
def test_il_punteggio_si_ricostruisce_dalla_penalita(penalita, atteso):
    assert rem.punteggio_ricostruito(penalita) == atteso


def test_r_ricostruisce_il_punteggio_di_ogni_area_certificata():
    """Il presidio vero: sui due golden, R(base) E' lo score pubblicato.

    Non e' una tautologia — nessun codice di produzione leggeva
    `params["penalty"]` prima di U4, quindi la coerenza fra penalita' e
    punteggio non era mai stata verificata da nessuno.
    """
    visitate = 0
    for nome in ("referto.json", "referto_degradato.json"):
        for area in _golden(nome)["areas"]:
            cert = rem.certificato_area(area)
            if cert["base"] is None:
                continue
            visitate += 1
            assert cert["certified"], "%s: %s" % (area["module"],
                                                  cert["reason"])
            assert rem.punteggio_ricostruito(cert["base"]) == round(
                area["score"]), area["module"]
    assert visitate == 13, ("tredici aree con penalita' fra i due golden: "
                            "erano nove fino a U13 (i controlli delle due "
                            "aree di classifica), dodici fino a I10 — le "
                            "prestazioni pesano solo nel referto completo, "
                            "nel degradato Lighthouse manca")


# ----------------------------------------------------------------------
# base: tutte le penalita', anche quelle dei rilievi `info`
# ----------------------------------------------------------------------

def test_la_base_somma_anche_gli_info():
    """Sommare i soli candidati romperebbe la ricostruzione in silenzio.

    E' il caso vero di mars_tech nel golden: 40 (critico) + 3 (un
    `info`) fa 43, e R(43) = 57 = il punteggio. Con la sola voce
    critica verrebbe R(40) = 60, e nessuno se ne accorgerebbe.
    """
    rilievi = [_rilievo(params={"penalty": 40.0}),
               _rilievo(severity=SEV_INFO, key="tech.canonical.missing",
                        params={"penalty": 3.0})]
    assert rem.base_area(rilievi) == 43.0
    assert rem.punteggio_ricostruito(43.0) == 57


def test_la_base_e_none_quando_nessuno_dichiara_una_penalita():
    """None non e' zero: zero significa misurata e nulla."""
    assert rem.base_area([_rilievo(params={})]) is None
    assert rem.base_area([]) is None
    assert rem.base_area([_rilievo(params={"penalty": 0.0})]) == 0.0


def test_la_base_ignora_una_penalita_non_numerica():
    """I params attraversano il confine dei plugin: sono dato ostile."""
    assert rem.base_area([_rilievo(params={"penalty": "molta"}),
                          _rilievo(params={"penalty": 8.0})]) == 8.0


# ----------------------------------------------------------------------
# Il certificato d'area
# ----------------------------------------------------------------------

def test_area_incoerente_non_e_certificata():
    """Se le penalita' non ricostruiscono il punteggio, niente numeri.

    Non e' un caso di scuola: R36 e R37 aggiungeranno rilievi e R40
    tocchera' mars_seo. Il piano deve accorgersene invece di pubblicare
    recuperi calcolati su una base che non regge.
    """
    cert = rem.certificato_area(_area(score=90, rilievi=[_rilievo()]))
    assert not cert["certified"]
    assert "non chiude" in cert["reason"]
    assert "60" in cert["reason"] and "90" in cert["reason"]


def test_area_satura_resta_certificata_e_dichiara_l_eccedenza():
    """Con score 0 il confronto diretto non puo' funzionare.

    `100 - 154` fa -54, che non e' 0: senza il ramo della saturazione
    un'area satura perderebbe tutti i suoi numeri proprio dove servono
    di piu'. L'eccedenza si pubblica perche' e' cio' che spiega perche'
    un rilievo da 40 ne recuperi 32.
    """
    cert = rem.certificato_area(_area(score=0, rilievi=[
        _rilievo(params={"penalty": 108.0})]))
    assert cert["certified"]
    assert cert["excess"] == 8.0


def test_area_senza_punteggio_non_e_certificabile():
    cert = rem.certificato_area(_area(score=None, rilievi=[_rilievo()]))
    assert not cert["certified"]
    assert "punteggio" in cert["reason"]


# ----------------------------------------------------------------------
# Il recupero: la differenza fra due punteggi, non la penalita'
# ----------------------------------------------------------------------

def test_il_recupero_e_la_penalita_quando_l_area_non_e_satura():
    assert rem.recupero(43.0, 40.0) == 40
    assert rem.recupero(43.0, 3.0) == 3


def test_in_un_area_satura_il_recupero_e_minore_della_penalita():
    """Il difetto piu' facile della fase: pubblicare la penalita'.

    Con base 108 il punteggio e' gia' 0, e i primi 8 punti di qualunque
    intervento pagano l'eccedenza invece di comparire nel referto.
    """
    assert rem.recupero(108.0, 40.0) == 32
    assert rem.recupero(108.0, 20.0) == 12
    # Sotto l'eccedenza non si muove niente.
    assert rem.recupero(108.0, 8.0) == 0
    assert rem.recupero(108.0, 8.5) == 0


def test_i_recuperi_non_sono_additivi():
    """Ed e' per questo che nessuna voce porta un totale.

    Numeri veri di mars_wcag nel golden completo: base 63, tre regole
    axe da 37.5, 18 e 7.5.
    """
    uno_alla_volta = sum(rem.recupero(63.0, p) for p in (37.5, 18.0, 7.5))
    insieme = rem.recupero(63.0, 63.0)
    assert uno_alla_volta == 62
    assert insieme == 63
    assert uno_alla_volta != insieme


# ----------------------------------------------------------------------
# I coefficienti di citabilita'
# ----------------------------------------------------------------------

def test_i_coefficienti_sommano_a_uno():
    """Invariante del modello: l'indice e' una media, non una somma.

    Vale perche' i sette segnali coprono per intero il denominatore
    rinormalizzato. Se un giorno non valesse, la derivata non sarebbe
    piu' quella dell'indice pubblicato.
    """
    for nome in ("referto.json", "referto_degradato.json"):
        cit = _golden(nome)["citability"]
        k, _, mercato = rem.coefficienti(cit)
        assert abs(sum(k.values()) - 1.0) < 1e-9, nome
        assert mercato == cit["market"]


def test_i_coefficienti_dipendono_dall_esecuzione():
    """`tecnica` non vale lo stesso numero nei due referti.

    Mercato diverso e segnali misurati diversi: e' il motivo per cui
    ogni voce porta con se' il mercato, e per cui confrontare due
    `index_gain` di referti diversi non significa niente.
    """
    completo, _, _ = rem.coefficienti(_golden("referto.json")["citability"])
    degradato, _, _ = rem.coefficienti(
        _golden("referto_degradato.json")["citability"])
    assert round(completo["tecnica"], 4) == 0.1885
    assert round(degradato["tecnica"], 4) == 0.4045


def test_il_guadagno_dichiarato_segue_l_indice_vero():
    """Controprova sul modulo VERO, non sulla formula riscritta.

    Si muove un segnale e si ricalcola l'indice composito come lo
    calcola `mars_citability`: la derivata deve ricostruire il
    movimento a meno dell'arrotondamento. Il modulo arrotonda due
    volte — i profili a 0.1 e poi l'indice — quindi la differenza fra
    due indici puo' scostarsi fino a due passi.
    """
    cit = _golden("referto.json")["citability"]
    k, _, _ = rem.coefficienti(cit)
    nomi = {e: n for n, e in mars_citability.SEGNALI.items()}
    segnali = {nomi[e]: v for e, v in cit["signals"].items()}
    mercato = mars_citability.MERCATI[cit["market"]]

    def composito(valori):
        profili = [mars_citability.profilo(a, valori, mercato["aree"])
                   for a in mars_citability.PESI_ASSISTENTE]
        pesi = list(mercato["assistenti"].values())
        coppie = [(p, w) for p, w in zip(profili, pesi) if p is not None]
        return round(sum(p * w for p, w in coppie)
                     / sum(w for _, w in coppie), 1)

    partenza = composito(segnali)
    assert partenza == cit["score"], "il ricalcolo deve riprodurre il dato"
    for segnale, guadagno in (("tecnica", 40), ("accessibilita", 37),
                              ("dati_strutturati", 10)):
        mosso = dict(segnali)
        mosso[segnale] = segnali[segnale] + guadagno
        osservato = composito(mosso) - partenza
        dichiarato = guadagno * k[segnale]
        assert abs(osservato - dichiarato) <= 0.2, (
            "%s: osservato %.2f, dichiarato %.2f" % (segnale, osservato,
                                                     dichiarato))


def test_un_etichetta_sconosciuta_spegne_i_guadagni():
    """La Fase 9 tradurra' le etichette, e questa e' la sua rete.

    Il referto pubblica i segnali per etichetta italiana. Quando
    saranno tradotte l'inversione non riconoscera' piu' nulla: i
    guadagni devono sparire dichiarandolo, non uscire sbagliati.
    """
    assert rem.coefficienti({"market": "eu",
                             "signals": {"Technical access": 50.0}}) is None


def test_una_sola_etichetta_sconosciuta_basta_a_fermare_tutto():
    """Il caso che conta, e che il precedente non copre.

    Con tutte le etichette ignote il dizionario resta vuoto e i
    coefficienti sono None comunque, per un'altra strada. Il difetto
    vero e' un'etichetta ignota su sette: saltarla darebbe
    coefficienti calcolati su un denominatore SBAGLIATO — piu' grandi
    del vero, e quindi guadagni gonfiati — senza un solo errore.
    """
    segnali = {e: 50.0 for e in mars_citability.SEGNALI.values()}
    intero = rem.coefficienti({"market": "eu", "signals": dict(segnali)})
    assert intero is not None
    segnali["Segnale che la Fase 9 ha tradotto"] = segnali.pop(
        mars_citability.SEGNALI["sicurezza"])
    assert rem.coefficienti({"market": "eu", "signals": segnali}) is None


def test_l_inversione_delle_etichette_e_iniettiva():
    """Presidio dell'unico aggancio fragile: due segnali con la stessa
    etichetta renderebbero l'inversione ambigua senza un errore."""
    etichette = list(mars_citability.SEGNALI.values())
    assert len(set(etichette)) == len(etichette)


def test_senza_citabilita_il_piano_resta_ordinabile():
    """I guadagni spariscono, l'ordinamento no: degrada sul recupero."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[_rilievo(), _rilievo(key="tech.sitemap.missing",
                                            severity=SEV_WARNING,
                                            params={"penalty": 3.0})])]))
    assert [v["index_gain"] for v in piano] == [None, None]
    assert [v["key"] for v in piano] == ["tech.robots.ai_blocked",
                                         "tech.sitemap.missing"]


# ----------------------------------------------------------------------
# Che cosa entra nel piano
# ----------------------------------------------------------------------

def test_gli_info_entrano_nel_piano():
    """**Decisione del committente, 2026-09-01**: il piano copre tutti i
    rilievi, `info` compresi. Fino a qui li teneva fuori la gravita', con
    la ragione «info descrive, non prescrive».

    La misura che ha reso ragionevole il cambio: dei diciannove esclusi
    del referto sintetico, **otto sono difetti veri del sito** —
    `tech.canonical.missing`, `perf.fcp.slow`, `wcag.link.generic`,
    `sec.zap.10035` — e `prescrivibile` gia' lo diceva nella propria
    docstring, «un rilievo `info` puo' essere un difetto vero». Gli altri
    undici restano fuori, ma per le altre due ragioni, che sono
    diverse e non sono state toccate."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[_rilievo(severity=SEV_INFO)])]))
    assert [v["key"] for v in piano] == ["tech.robots.ai_blocked"]
    assert piano[0]["severity"] == SEV_INFO


def test_gli_info_stanno_in_fondo_al_piano():
    """La gravita' domina l'ordine, e resta cosi': un `info` non
    scavalca un'avvertenza perche' recupera piu' punti."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[
            _rilievo(key="tech.a.b", severity=SEV_INFO,
                     params={"penalty": 40.0}),
            _rilievo(key="tech.c.d", severity=SEV_WARNING,
                     params={"penalty": 1.0}),
            _rilievo(key="tech.e.f", severity=SEV_CRITICAL,
                     params={"penalty": 1.0})])]))
    assert [v["severity"] for v in piano] == [SEV_CRITICAL, SEV_WARNING,
                                              SEV_INFO]


def test_il_riepilogo_conta_anche_gli_info():
    """La testata dice «N interventi (X critici, Y avvertenze)»: senza
    il terzo numero i conti non tornerebbero piu', e chi legge
    penserebbe a un errore di somma."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[_rilievo(severity=SEV_INFO)])]))
    conti = rem.riepilogo(piano, _referto([_area()]))
    assert conti["info"] == 1
    assert conti["total"] == conti["critical"] + conti["warning"] + conti["info"]


def test_un_controllo_non_fallito_non_entra_nel_piano():
    """Il difetto che la decisione sugli `info` ha portato a galla.

    Lighthouse produce un rilievo per OGNI audit — superati e non
    applicabili compresi — e sono tutti `info`. Alzato il filtro sulla
    gravita', nel piano sono entrate tre voci come «Non applicabile a
    questa pagina: robots.txt è valido»: in un piano d'azione non c'e'
    niente da fare, ed e' il referto che si smentisce.

    Il discriminante giusto esisteva gia' ed e' la PENALITA' dichiarata:
    `mars_fixes.prescrivibile`, che U3.1 usa per non scrivere «Correggi
    la sintassi di robots.txt» sotto «robots.txt e' valido». Chiave
    assente significa «non misurato, o non fallito»; `0.0` significa
    «misurato, ma qui non muove il punteggio» ed e' un difetto vero.
    """
    superato = _rilievo(key="seo.lh.robots_txt", severity=SEV_INFO,
                        params={"rule": "robots-txt",
                                "mode": "notApplicable"})
    assert rem.build_remediation(_referto([_area(rilievi=[superato])])) == []

    # `penalty: 0.0` invece entra: e' un difetto misurato che in questa
    # esecuzione non muove il punteggio — i controlli statici di
    # mars_wcag nel ramo axe.
    nullo = _rilievo(key="wcag.link.generic", severity=SEV_INFO,
                     params={"penalty": 0.0})
    piano = rem.build_remediation(_referto([_area(rilievi=[nullo])]))
    assert [v["key"] for v in piano] == ["wcag.link.generic"]


def test_i_derivati_restano_fuori_anche_se_gravi():
    """Il vincolo di R41, e non e' teorico.

    Oggi i rilievi di mars_citability sono tutti `info`, quindi li
    terrebbe fuori anche la sola gravita': ma quella e' una protezione
    incidentale, e il giorno che un derivato nascesse `warning` il
    piano prescriverebbe due volte lo stesso difetto — una volta
    nell'area che lo misura e una nella sintesi che lo ridice.
    """
    piano = rem.build_remediation(_referto([
        _area("mars_citability", rilievi=[
            _rilievo(area="mars_citability", key="cit.seo.weak",
                     severity=SEV_CRITICAL,
                     params={"derived": True, "penalty": 40.0})])]))
    assert piano == []


def test_i_rilievi_di_stato_restano_fuori():
    """Parlano della scansione, non del sito: destinatario sbagliato."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[_rilievo(key="tech.status.error",
                                severity=SEV_CRITICAL)])]))
    assert piano == []


def test_un_rilievo_senza_fix_entra_lo_stesso():
    """Nasconderlo perche' non sappiamo dire come si chiude sarebbe
    peggio che dichiararlo senza prescrizione."""
    piano = rem.build_remediation(_referto([
        _area(rilievi=[_rilievo(fix="", example="")])]))
    assert len(piano) == 1
    assert piano[0]["fix"] == ""


# ----------------------------------------------------------------------
# Le corsie
# ----------------------------------------------------------------------

def test_le_quattro_corsie():
    """Ognuna dice una cosa diversa, e nessuna e' "zero"."""
    piano = rem.build_remediation(_referto([
        # base 108: satura. Il primo recupera 32, il secondo niente.
        _area("mars_tech", score=0, rilievi=[
            _rilievo(params={"penalty": 100.0}),
            _rilievo(key="tech.sitemap.missing", params={"penalty": 8.0})]),
        # certificata, ma un rilievo dichiara penalita' zero
        _area("mars_schema", score=100, rilievi=[
            _rilievo(area="mars_schema", key="sd.jsonld.missing",
                     params={"penalty": 0.0})]),
        # certificata, ma questo rilievo la penalita' la dichiara e non
        # e' un numero. NON `params={}`: dal 2026-09-01 un rilievo che
        # la penalita' non la dichiara affatto non entra proprio nel
        # piano — misurato, i soli rilievi in quello stato sono i
        # controlli Lighthouse non falliti. La corsia «ignoto» resta
        # per QUESTO caso e per l'area non certificata.
        _area("mars_wapt", score=100, rilievi=[
            _rilievo(area="mars_wapt", key="sec.headers.csp_missing",
                     params={"penalty": 0.0}),
            _rilievo(area="mars_wapt", key="sec.headers.hsts_missing",
                     params={"penalty": "alto"})]),
    ]))
    corsie = {v["key"]: v["lane"] for v in piano}
    assert corsie["tech.robots.ai_blocked"] == "misurato"
    assert corsie["tech.sitemap.missing"] == "bloccato"
    assert corsie["sd.jsonld.missing"] == "nullo"
    assert corsie["sec.headers.hsts_missing"] == "ignoto"
    # E ognuna spiega se stessa, tranne quella che non ha nulla da dire.
    motivi = {v["key"]: v["lane_reason"] for v in piano}
    assert motivi["tech.robots.ai_blocked"] == ""
    assert all(motivi[k] for k in ("tech.sitemap.missing",
                                   "sd.jsonld.missing",
                                   "sec.headers.hsts_missing"))


def test_l_ordinamento_regge_due_voci_senza_numeri():
    """Due voci in corsia "ignoto" hanno index_gain, recupero e
    penalita' tutti None: una chiave che li negasse solleverebbe
    TypeError, e il referto morirebbe dopo che tutte le aree hanno
    girato — cioe' nel punto piu' caro possibile."""
    piano = rem.build_remediation(_referto([
        _area(score=None, rilievi=[
            _rilievo(key="tech.robots.missing", params={"penalty": "alto"}),
            _rilievo(key="tech.sitemap.missing",
                     params={"penalty": "alto"})])]))
    assert [v["lane"] for v in piano] == ["ignoto", "ignoto"]
    assert [v["key"] for v in piano] == ["tech.robots.missing",
                                         "tech.sitemap.missing"]


# ----------------------------------------------------------------------
# L'ordinamento
# ----------------------------------------------------------------------

def test_la_gravita_domina_sul_guadagno():
    """Un critico a guadagno zero resta sopra un'avvertenza che il
    punteggio lo muove: la gravita' e' un fatto sul sito, il guadagno
    un fatto su come lo misuriamo in questa esecuzione."""
    piano = rem.build_remediation(_referto([
        _area("mars_wcag", score=37, rilievi=[
            _rilievo(area="mars_wcag", key="wcag.img.alt_missing",
                     severity=SEV_CRITICAL, params={"penalty": 0.0}),
            _rilievo(area="mars_wcag", key="wcag.axe.color_contrast",
                     severity=SEV_WARNING, params={"penalty": 63.0})])]))
    assert [v["key"] for v in piano] == ["wcag.img.alt_missing",
                                         "wcag.axe.color_contrast"]


def test_a_parita_di_gravita_vince_il_guadagno_di_indice_non_il_recupero():
    """E' il lavoro che l'index_gain deve fare: 37 punti di SEO valgono
    meno di 40 di tecnica, perche' i due segnali non pesano uguale.

    Numeri veri del golden completo, dove `seo.lh.is_crawlable`
    recupera 37 punti d'area contro i 40 di `tech.robots.ai_blocked`,
    e il piano mette comunque la tecnica davanti.
    """
    piano = rem.build_remediation(_golden("referto.json"))
    primi = [v["key"] for v in piano[:2]]
    assert primi == ["tech.robots.ai_blocked", "seo.lh.is_crawlable"]
    assert piano[0]["recovery"] == 40 and piano[0]["index_gain"] == 7.54
    assert piano[1]["recovery"] == 37 and piano[1]["index_gain"] == 4.74


def test_la_chiave_scioglie_i_pareggi():
    """Senza, due voci pari-merito si scambierebbero al variare
    dell'ordine di produzione e i golden sarebbero instabili."""
    def piano(ordine):
        return [v["key"] for v in rem.build_remediation(_referto([
            _area(score=20, rilievi=[
                _rilievo(key=k, params={"penalty": 40.0}) for k in ordine])]))]
    assert piano(("tech.index.noindex", "tech.robots.ai_blocked")) == \
        piano(("tech.robots.ai_blocked", "tech.index.noindex")) == \
        ["tech.index.noindex", "tech.robots.ai_blocked"]


def test_la_corsia_viene_prima_dei_numeri():
    """Senza la corsia l'ordine lo deciderebbe la chiave alfabetica.

    Due voci pari-gravita' senza un solo numero da confrontare: una
    dichiara penalita' zero (corsia "nullo": sappiamo che non muove
    niente), l'altra la penalita' non ce l'ha (corsia "ignoto": non lo
    sappiamo). Le chiavi sono scelte perche' l'ordine alfabetico le
    metta al contrario, cosi' un ordinamento che perdesse la corsia si
    vede subito.
    """
    piano = rem.build_remediation(_referto([
        _area(score=100, rilievi=[
            _rilievo(key="tech.canonical.missing", severity=SEV_WARNING,
                     params={"penalty": 0.0}),
            # Penalita' dichiarata ma non numerica: e' la via per cui
            # la corsia «ignoto» si raggiunge da un'area certificata,
            # dopo che i rilievi senza penalita' sono usciti dal piano.
            _rilievo(key="tech.robots.missing", severity=SEV_WARNING,
                     params={"penalty": "alto"})])]))
    assert [(v["key"], v["lane"]) for v in piano] == [
        ("tech.robots.missing", "ignoto"),
        ("tech.canonical.missing", "nullo")]


def test_la_priorita_e_progressiva_e_parte_da_uno():
    piano = rem.build_remediation(_golden("referto.json"))
    assert [v["priority"] for v in piano] == list(range(1, len(piano) + 1))


# ----------------------------------------------------------------------
# Lo sforzo e i quick win
# ----------------------------------------------------------------------

def test_il_catalogo_dello_sforzo_copre_esattamente_quello_dei_fix():
    """Due cataloghi sugli stessi controlli divergono in silenzio.

    Un controllo con un `fix` e senza sforzo non potrebbe mai essere un
    quick win; uno con lo sforzo e senza fix prometterebbe un
    intervento che il referto non sa descrivere.
    """
    assert set(rem.SFORZO) == set(mars_fixes.CATALOGO)


def test_lo_sforzo_non_riguarda_i_rilievi_di_stato():
    """Stessa esclusione dei fix: il destinatario e' chi fa girare MARS."""
    assert not [k for k in rem.SFORZO if ".status." in k]


def test_i_tre_livelli_sono_quelli_dichiarati():
    assert set(rem.SFORZO.values()) == {rem.MINUTI, rem.ORE, rem.GIORNI}


def test_le_due_famiglie_dinamiche_non_hanno_uno_sforzo_dichiarato():
    """axe e ZAP: le chiavi non sono nostre.

    Un default "ore" sarebbe un'assenza travestita da stima, e
    spegnerebbe i quick win senza che nessuno se ne accorga.

    Fino a I18 la regola valeva anche per `seo.lh.*`, e la ragione era
    la stessa. Non reggeva allo stesso modo: gli audit SEO di
    Lighthouse sono undici, non oltre cento, e li elenchiamo. Le altre
    due restano fuori, ed e' quello che questo test presidia.
    """
    piano = rem.build_remediation(_golden("referto.json"))
    dinamiche = [v for v in piano
                 if v["key"].startswith(("wcag.axe.", "sec.zap."))]
    assert dinamiche, "il golden ne contiene"
    assert all(v["effort"] is None for v in dinamiche)
    assert all(not v["quick_win"] for v in dinamiche)


def test_un_audit_seo_che_non_conosciamo_resta_senza_sforzo():
    """La degradazione dichiarata di I18: le chiavi `seo.lh.*` vengono
    dagli id di Lighthouse, e una versione futura puo' rinominarne uno.
    Allora la voce del catalogo resta inutilizzata e il rilievo torna
    senza sforzo — cioe' com'era prima — invece di ricevere una stima
    inventata."""
    piano = rem.build_remediation(_referto([
        _area("mars_seo", score=90, rilievi=[
            _rilievo(area="mars_seo", key="seo.lh.audit_mai_visto",
                     params={"penalty": 10.0})]),
    ]))
    voce = [v for v in piano if v["key"] == "seo.lh.audit_mai_visto"][0]
    assert voce["effort"] is None
    assert not voce["quick_win"]


def test_un_audit_seo_conosciuto_ha_lo_sforzo(monkeypatch):
    """L'altra meta': i dieci che elenchiamo lo sforzo ce l'hanno, e
    senza di esso `seo.lh.robots_txt` non potrebbe mai essere un quick
    win — che e' proprio cio' che I18 gli ha dato."""
    assert rem.SFORZO["seo.lh.robots_txt"] == rem.MINUTI
    piano = rem.build_remediation(_golden("referto.json"))
    noti = [v for v in piano if v["key"].startswith("seo.lh.")
            and v["key"] in rem.SFORZO]
    assert noti, "il golden ne contiene"
    assert all(v["effort"] is not None for v in noti)


def test_quick_win_vuole_tre_condizioni():
    """Critico, da minuti, e con un recupero che esiste davvero."""
    piano = rem.build_remediation(_referto([
        # critico + minuti + recupero: quick win
        _area("mars_tech", score=57, rilievi=[
            _rilievo(key="tech.robots.ai_blocked", params={"penalty": 43.0})]),
        # critico + minuti ma recupero zero: NON quick win
        _area("mars_wcag", score=37, rilievi=[
            _rilievo(area="mars_wcag", key="wcag.lang.missing",
                     params={"penalty": 0.0}),
            _rilievo(area="mars_wcag", key="wcag.axe.image_alt",
                     severity=SEV_WARNING, params={"penalty": 63.0})]),
        # critico + recupero ma sforzo di giorni: NON quick win
        _area("mars_schema", score=90, rilievi=[
            _rilievo(area="mars_schema", key="wcag.img.alt_missing",
                     params={"penalty": 10.0})]),
        # minuti + recupero ma solo avvertenza: NON quick win
        _area("mars_wapt", score=90, rilievi=[
            _rilievo(area="mars_wapt", key="sec.headers.hsts_missing",
                     severity=SEV_WARNING, params={"penalty": 10.0})]),
    ]))
    quick = {v["key"]: v["quick_win"] for v in piano}
    assert quick == {"tech.robots.ai_blocked": True,
                     "wcag.lang.missing": False,
                     "wcag.axe.image_alt": False,
                     "wcag.img.alt_missing": False,
                     "sec.headers.hsts_missing": False}


def test_lo_sforzo_non_entra_nell_ordinamento():
    """Ordinare per sforzo metterebbe una stima editoriale davanti a una
    misura: il piano ordina per quanto vale, non per quanto costa."""
    piano = rem.build_remediation(_referto([
        _area(score=57, rilievi=[
            # giorni, ma recupera di piu'
            _rilievo(key="wcag.img.alt_missing", params={"penalty": 40.0}),
            # minuti, ma recupera di meno
            _rilievo(key="tech.robots.missing", params={"penalty": 3.0})])]))
    assert [v["key"] for v in piano] == ["wcag.img.alt_missing",
                                         "tech.robots.missing"]


# ----------------------------------------------------------------------
# Il caso numerico, verificabile a mano dall'inizio alla fine
# ----------------------------------------------------------------------

def test_il_piano_si_ricostruisce_a_mano():
    """Due aree, due segnali, mercato "global": ogni numero a mano.

    mars_tech, score 0 — base 40+40+20+8 = 108, dunque area SATURA con
    8 punti di eccedenza:
        T1 tech.robots.ai_blocked  critico  40 -> R(68)-R(108) = 32
        T2 tech.index.noindex      critico  40 -> 32
        T3 tech.sitemap.missing    grave    20 -> R(88)-0     = 12
        T4 tech.index.nofollow     grave     8 -> R(100)-0    =  0
    mars_schema, score 40 — base 60, non satura:
        S1 sd.jsonld.missing       critico  50 -> R(10)-R(60) = 50
        S2 sd.jsonld.block_empty   grave    10 -> R(50)-R(60) = 10

    Segnali misurati: due soli, `tecnica` 0 e `dati_strutturati` 40.
    Pesi di "global": Claude 5, ChatGPT 9, Qwen 3, Kimi 3.
    Pesi dei segnali (tecnica, dati_strutturati): Claude (3, 2),
    ChatGPT (3, 3), Qwen (3, 2), Kimi (3, 2).

        k_a[tecnica] = 3/5 (Claude, Qwen, Kimi) e 3/6 (ChatGPT)
        k[tecnica] = (5*0.6 + 9*0.5 + 3*0.6 + 3*0.6)/20 = 11.1/20 = 0.555
        k[dati_strutturati] = 1 - 0.555 = 0.445

        T1 e T2: 32 * 0.555 = 17.76
        T3:      12 * 0.555 =  6.66
        S1:      50 * 0.445 = 22.25
        S2:      10 * 0.445 =  4.45

    L'ordine che ne esce mostra il punto del piano: fra i tre critici
    vince S1, che recupera 50 punti d'area e ne porta 22.25 all'indice,
    davanti a T1 e T2 che ne recuperano 32 e ne portano 17.76 — un
    recupero d'area piu' grande che vale davvero di piu' solo dopo
    essere passato per i pesi. Con due soli segnali misurati la tecnica
    pesa 0.555 contro 0.445, e non basta a ribaltare 50 contro 32.
    """
    aree = [
        _area("mars_tech", score=0, rilievi=[
            _rilievo(key="tech.robots.ai_blocked", severity=SEV_CRITICAL,
                     params={"penalty": 40.0}),
            _rilievo(key="tech.index.noindex", severity=SEV_CRITICAL,
                     params={"penalty": 40.0}),
            _rilievo(key="tech.sitemap.missing", severity=SEV_WARNING,
                     params={"penalty": 20.0}),
            _rilievo(key="tech.index.nofollow", severity=SEV_WARNING,
                     params={"penalty": 8.0})]),
        _area("mars_schema", score=40, rilievi=[
            _rilievo(area="mars_schema", key="sd.jsonld.missing",
                     severity=SEV_CRITICAL, params={"penalty": 50.0}),
            _rilievo(area="mars_schema", key="sd.jsonld.block_empty",
                     severity=SEV_WARNING, params={"penalty": 10.0})]),
    ]
    citability = {"market": "global", "signals": {
        mars_citability.SEGNALI["tecnica"]: 0.0,
        mars_citability.SEGNALI["dati_strutturati"]: 40.0,
        mars_citability.SEGNALI["seo"]: None,
        mars_citability.SEGNALI["accessibilita"]: None,
        mars_citability.SEGNALI["sicurezza"]: None,
        mars_citability.SEGNALI["recuperabilita"]: None,
        mars_citability.SEGNALI["answer_shaped"]: None,
    }}
    k, _, mercato = rem.coefficienti(citability)
    assert mercato == "global"
    assert round(k["tecnica"], 4) == 0.555
    assert round(k["dati_strutturati"], 4) == 0.445

    piano = rem.build_remediation(_referto(aree, citability))
    reso = [(v["key"], v["recovery"], v["index_gain"], v["lane"])
            for v in piano]
    assert reso == [
        ("sd.jsonld.missing", 50, 22.25, "misurato"),
        ("tech.index.noindex", 32, 17.76, "misurato"),
        ("tech.robots.ai_blocked", 32, 17.76, "misurato"),
        ("tech.sitemap.missing", 12, 6.66, "misurato"),
        ("sd.jsonld.block_empty", 10, 4.45, "misurato"),
        ("tech.index.nofollow", 0, None, "bloccato"),
    ]
    # I punteggi di partenza e arrivo viaggiano con la voce: sono gli
    # ingredienti della differenza, e senza non si potrebbe rifare il
    # conto leggendo il referto.
    saturo = [v for v in piano if v["key"] == "tech.robots.ai_blocked"][0]
    assert (saturo["score_before"], saturo["score_after"]) == (0, 32)
    assert saturo["penalty"] == 40.0 and saturo["additive"] is False

    riepilogo = rem.riepilogo(piano, _referto(aree, citability))
    assert riepilogo["total"] == 6
    assert riepilogo["critical"] == 3 and riepilogo["warning"] == 3
    assert riepilogo["by_lane"] == {"misurato": 5, "bloccato": 1,
                                    "ignoto": 0, "nullo": 0}
    assert riepilogo["quick_wins"] == 1  # solo T1: T2 e' "ore"
    assert riepilogo["areas_covered"] == 2 and riepilogo["areas_total"] == 2


# ----------------------------------------------------------------------
# Il riepilogo
# ----------------------------------------------------------------------

def test_le_aree_del_piano_si_contano_e_non_si_cablano():
    """Al massimo otto su dieci, non dieci.

    I rilievi di mars_citability sono per costruzione derivati e quelli
    di mars_llm_judge sono tutti di stato: nessuna delle due puo'
    entrare nel piano. Erano cinque fino a U13, che ha dato dei
    controlli alle due aree di classifica, sette fino a I10, che ha
    aggiunto le prestazioni — ed e' esattamente il genere di numero che
    invecchia da solo, cioe' la ragione per cui si conta invece di
    scriverlo.
    """
    referto = _golden("referto.json")
    riep = rem.riepilogo(rem.build_remediation(referto), referto)
    assert riep["areas_total"] == 10
    assert riep["areas_covered"] == 8
    assert set(riep["areas_excluded"]) == {"mars_citability",
                                           "mars_llm_judge"}


def test_il_riepilogo_non_pubblica_un_totale_dei_guadagni():
    """Sarebbe il numero piu' letto e il piu' sbagliato del referto."""
    referto = _golden("referto.json")
    riep = rem.riepilogo(rem.build_remediation(referto), referto)
    assert riep["additive"] is False
    assert not [c for c in riep if "gain" in c or "total_recovery" in c]


def test_un_referto_senza_aree_da_un_piano_vuoto():
    assert rem.build_remediation({}) == []
    assert rem.riepilogo([], {})["total"] == 0


# ----------------------------------------------------------------------
# R46: lo sforzo scala col conteggio delle istanze
# ----------------------------------------------------------------------

def _voce_con(chiave, istanze=None, severita=SEV_CRITICAL):
    params = {"penalty": 10.0}
    if istanze is not None:
        params["instances"] = istanze
    return {"key": chiave, "severity": severita, "title": "T",
            "params": params}


@pytest.mark.parametrize("istanze, atteso", [
    (1, rem.ORE),         # una sola immagine: si fa e si verifica subito
    (2, rem.GIORNI),      # la ricorrenza tipica, cioe' la mappa com'e'
    (9, rem.GIORNI),
    (10, rem.GIORNI),     # gia' al tetto: non si sale oltre
    (400, rem.GIORNI),
    (None, rem.GIORNI),   # non dichiarato: lo sforzo di base
])
def test_lo_sforzo_scala_col_conteggio(istanze, atteso):
    """R46: «1 immagine senza alt» e «400 immagini senza alt» avevano la
    stessa chiave, quindi lo stesso sforzo — `giorni` in entrambi i
    casi, che sul primo e' una sopravvalutazione.

    La mappa `SFORZO` resta il livello della **ricorrenza tipica**, e il
    conteggio lo muove di un gradino per volta. Resta una stima
    dichiarata: il referto scrive `giorni`, non «3 giorni», e la
    differenza e' voluta — un ordine di grandezza e' una stima, un
    numero sembra una misura."""
    assert rem._sforzo(_voce_con("wcag.img.alt_missing", istanze)) == atteso


@pytest.mark.parametrize("istanze, atteso", [
    (1, rem.MINUTI),
    (3, rem.ORE),
    (30, rem.GIORNI),
    (300, rem.GIORNI),    # due gradini sopra ORE si ferma a GIORNI
])
def test_lo_sforzo_sale_e_scende_dal_livello_di_base(istanze, atteso):
    """Il gradino si conta dal livello della chiave, non da zero:
    `tech.canonical.missing` parte da ORE, `wcag.img.alt_missing` da
    GIORNI, e lo stesso conteggio li muove in modo diverso."""
    assert rem._sforzo(_voce_con("tech.canonical.missing", istanze)) == atteso


def test_una_chiave_senza_sforzo_di_base_resta_senza():
    """Le famiglie dinamiche — axe, ZAP, Lighthouse — non hanno uno
    sforzo dichiarato, e il conteggio non puo' inventarne uno: un
    gradino sopra il nulla e' ancora il nulla."""
    assert rem._sforzo(_voce_con("wcag.axe.image_alt", 400)) is None


def test_un_conteggio_assurdo_non_sposta_lo_sforzo():
    """`instances` viene dai params di un rilievo, che un plugin di
    terzi puo' scrivere come vuole: zero, negativo o non intero non
    sono conteggi, e `istanze_del_rilievo` li rende None."""
    for assurdo in (0, -3, "molte", None, True):
        voce = _voce_con("wcag.img.alt_missing")
        voce["params"]["instances"] = assurdo
        assert rem._sforzo(voce) == rem.GIORNI, assurdo
