#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — i cataloghi di traduzione dei rilievi (U9.1).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import os
import re

import pytest

import mars_citability
import mars_fixes
import mars_i18n
import mars_tech
from conftest import pagina
from mars_core import AREA_PREFIX
from mars_i18n import LINGUE, RILIEVI, finding_texts, normalizza_lingua
from test_golden import DATASET

# La radice del repo dal file, non dalla cwd: R33 registra che i test
# con percorsi relativi passano vacuamente quando `pytest` gira da
# un'altra directory.
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Le lingue diverse dalla canonica: e' su queste che si traduce, ed e'
# scritto cosi' perche' aggiungerne una NON richieda di toccare i test.
TRADOTTE = [lingua for lingua in LINGUE
            if lingua != mars_i18n.LINGUA_CANONICA]

# Una chiave come letterale nel sorgente di un modulo. Il primo segmento
# deve essere un prefisso d'area vero, altrimenti "axe.min.js" passa per
# una chiave.
_CHIAVE = re.compile(
    r"""["'](%s)\.([a-z_0-9]+)\.([a-z_0-9]+)["']"""
    % "|".join(sorted(set(AREA_PREFIX.values()))))


def _chiavi_nei_sorgenti() -> set:
    """Le chiavi scritte per esteso nei moduli, mars_i18n escluso.

    Escluso perche' altrimenti il catalogo si darebbe ragione da se':
    ogni chiave inventata qui risulterebbe emessa da qualcuno.
    """
    trovate = set()
    for nome in sorted(os.listdir(RADICE)):
        if not nome.startswith("mars_") or not nome.endswith(".py"):
            continue
        if nome == "mars_i18n.py":
            continue
        with open(os.path.join(RADICE, nome), encoding="utf-8") as f:
            for pezzi in _CHIAVE.findall(f.read()):
                trovate.add(".".join(pezzi))
    return trovate


def _chiavi_dei_dataset(monkeypatch) -> set:
    """Le chiavi che i due referti sintetici accendono davvero."""
    chiavi = set()
    for costruisci in DATASET.values():
        for area in costruisci(monkeypatch)["areas"]:
            for f in area["findings"]:
                if f.get("key"):
                    chiavi.add(f["key"])
    return chiavi


def _params_dei_dataset(monkeypatch) -> dict:
    """chiave -> params veri, dai due referti sintetici."""
    veri = {}
    for costruisci in DATASET.values():
        for area in costruisci(monkeypatch)["areas"]:
            for f in area["findings"]:
                if f.get("key"):
                    veri.setdefault(f["key"], f.get("params") or {})
    return veri


def _params_del_banco(monkeypatch) -> dict:
    """chiave -> params veri, per le chiavi che i golden non accendono.

    I due referti sintetici di U2 sono un CAMPIONE, non l'inventario: su
    `tech` accendono due chiavi su dodici. Qui si fanno girare i moduli
    veri su contesti costruiti apposta, cosi' che i segnaposto dei
    template si esercitino contro i params che il modulo passa davvero e
    non contro quelli che chi ha tradotto immaginava.
    """
    import mars_schema
    import mars_seo
    import mars_wcag

    veri = {}

    def raccogli(esito):
        for f in esito.get("findings") or []:
            if f.get("key"):
                veri.setdefault(f["key"], f.get("params") or {})

    # Area 1: noindex, nofollow e canonical altrove sulla stessa pagina,
    # piu' una sitemap illeggibile e senza lastmod.
    tech = {
        "url": "https://esempio.test/",
        "pages": {"https://esempio.test/": pagina(
            '<html><head><meta name="robots" content="noindex, nofollow">'
            '<link rel="canonical" href="https://altro.test/x">'
            '</head><body><p>x</p></body></html>')},
        "robots": {"found": True, "text": "User-agent: *\nAllow: /",
                   "sitemaps": []},
        "sitemap": {"found": True, "from_robots": True, "urls": 3,
                    "with_lastmod": 0, "unreadable": 2},
    }
    raccogli(mars_tech.audit(tech))

    # Area 5: un blocco JSON-LD vuoto accanto a uno valido.
    schema = {"pages": {"https://esempio.test/": pagina(
        '<html><head><script type="application/ld+json"></script>'
        '<script type="application/ld+json">{"@type":"X"}</script>'
        '</head><body><p>x</p></body></html>')}}
    raccogli(mars_schema.audit(schema))

    # Area 6, ramo statico: pagina senza lang e con tabindex positivo.
    wcag = {"pages": {"https://esempio.test/": pagina(
        '<html><body><h1>t</h1><div tabindex="3">x</div></body></html>')}}
    raccogli(mars_wcag.audit(wcag))

    # Area 2: Lighthouse c'e' ma non risponde entro il tempo.
    monkeypatch.setattr(mars_seo.shutil, "which", lambda _: "/bin/lighthouse")
    monkeypatch.setattr(mars_seo, "esegui_lighthouse", _timeout_lighthouse)
    raccogli(mars_seo.audit({"url": "https://esempio.test/"}))
    monkeypatch.undo()

    # Area 8: i sette segnali tutti deboli, poi tutti non misurati.
    # I due derivati non vengono da uno `score`: `answer_shaped` dal
    # rapporto di mars_semantic, `recuperabilita` dal consenso fra i due
    # ranghi — qui disgiunti, quindi zero.
    deboli = {nome: {"score": 10.0}
              for nome in ("mars_tech", "mars_seo", "mars_schema",
                           "mars_wcag", "mars_wapt")}
    deboli["mars_semantic"] = {"answer_shaped_ratio": 0.1,
                               "rank": [0, 1, 2]}
    deboli["mars_lexical"] = {"rank": [3, 4, 5]}
    raccogli(mars_citability.audit({"results": deboli, "market": "global"}))
    raccogli(mars_citability.audit({"results": {"mars_tech": {}}}))
    return veri


def _timeout_lighthouse(*args, **kwargs):
    import subprocess
    raise subprocess.TimeoutExpired("lighthouse", 1)


def _chiavi_della_citabilita() -> set:
    """`cit.<segnale>.<esito>` per i sette segnali e i due esiti.

    Le chiavi non compaiono come letterali in `mars_citability`: le
    compone `_rilievo_segnale`. Qui si ricostruiscono dalla stessa
    fonte da cui le costruisce lui, cosi' un segnale nuovo rende rosso
    il catalogo invece di ripiegare in silenzio.
    """
    return {"cit.%s.%s" % (segnale, esito)
            for segnale in mars_citability.SEGNALI
            for esito in ("weak", "unmeasured")}


def _chiavi_di_errore() -> set:
    """Il fallimento d'area indossa una chiave per prefisso."""
    return {"%s.status.error" % p
            for p in set(AREA_PREFIX.values()) | {"area"}}


# ======================================================================
# Le lingue
# ======================================================================

def test_le_lingue_dichiarate_sono_due_e_la_canonica_e_prima():
    """D4 ratificata: it ed en, ed e' un livello dichiarato.

    Se un giorno se ne aggiunge una, questo test va aggiornato con
    intenzione — e' il punto in cui la decisione si rilegge."""
    assert LINGUE == ("it", "en")
    assert LINGUE[0] == mars_i18n.LINGUA_CANONICA


@pytest.mark.parametrize("richiesta", ["pt", "de", "", None, "  ", "en-GB"])
def test_una_lingua_sconosciuta_ripiega_sulla_canonica(richiesta):
    """E non indovina: `pt` non diventa `es` per vicinanza, `en-GB` non
    diventa `en` per prefisso. Chi vuole dichiarare il ripiego
    confronta richiesta e risultato, che qui non si perdono."""
    assert normalizza_lingua(richiesta) == "it"


@pytest.mark.parametrize("richiesta,attesa", [
    ("en", "en"), ("EN", "en"), (" en ", "en"), ("It", "it")])
def test_una_lingua_nota_sopravvive_a_maiuscole_e_spazi(richiesta, attesa):
    """L'esito ATTESO, non «una lingua qualunque delle nostre».

    Scritto come `in LINGUE` il test passava anche togliendo il
    `.lower()`: "EN" ripiegava su "it", e "it" e' in LINGUE. Colto da
    una mutazione, che e' il motivo per cui si fanno."""
    assert normalizza_lingua(richiesta) == attesa


# ======================================================================
# Copertura del catalogo
# ======================================================================

@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_chiave_statica_dei_moduli_e_tradotta(lingua):
    """Le chiavi scritte nei moduli, comprese quelle che nessun dataset
    accende: un sito reale le accende, e allora e' tardi per scoprirle
    senza traduzione."""
    mancanti = sorted(_chiavi_nei_sorgenti() - set(RILIEVI[lingua]))
    assert not mancanti, "chiavi senza traduzione %s: %s" % (lingua,
                                                             mancanti)


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_chiave_accesa_dai_dataset_e_tradotta(lingua, monkeypatch):
    """Le chiavi che i due referti sintetici producono davvero.

    Si sovrappone in parte al test precedente e non lo duplica: quelle
    di `mars_citability` non sono letterali in alcun sorgente."""
    accese = {c for c in _chiavi_dei_dataset(monkeypatch)
              if not mars_i18n.dallo_strumento(c)}
    mancanti = sorted(accese - set(RILIEVI[lingua]))
    assert not mancanti, "chiavi senza traduzione %s: %s" % (lingua,
                                                             mancanti)


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_i_sette_segnali_di_citabilita_sono_tradotti(lingua):
    """L'etichetta del segnale sta nei `params` ed e' italiana: una
    chiave `cit.` senza voce a catalogo darebbe un titolo inglese con
    dentro «Accessibilità»."""
    mancanti = sorted(_chiavi_della_citabilita() - set(RILIEVI[lingua]))
    assert not mancanti, mancanti


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_il_fallimento_di_ogni_area_e_tradotto(lingua):
    """Nove chiavi per un controllo solo, derivate da AREA_PREFIX:
    un'area nuova porta con se' la propria traduzione."""
    mancanti = sorted(_chiavi_di_errore() - set(RILIEVI[lingua]))
    assert not mancanti, mancanti


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_nessuna_voce_del_catalogo_e_orfana(lingua, monkeypatch):
    """Il verso opposto: una chiave tradotta che nessuno emette piu'.

    Senza questo test una rinomina lascerebbe dietro la traduzione
    vecchia, che non fa fallire nulla e fa credere coperto cio' che non
    lo e'."""
    vere = (_chiavi_nei_sorgenti() | _chiavi_dei_dataset(monkeypatch)
            | _chiavi_della_citabilita() | _chiavi_di_errore())
    orfane = sorted(set(RILIEVI[lingua]) - vere)
    assert not orfane, "tradotte ma non emesse da nessuno: %s" % orfane


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_il_catalogo_non_traduce_cio_che_viene_dallo_strumento(lingua):
    """axe, ZAP e Lighthouse dicono la loro regola meglio di noi, e la
    dicono ancora dopo il prossimo aggiornamento."""
    dinamiche = [c for c in RILIEVI[lingua] if mars_i18n.dallo_strumento(c)]
    assert not dinamiche, dinamiche


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_i_fix_tradotti_stanno_dove_stanno_quelli_italiani(lingua):
    """Parita' col catalogo italiano, nei due versi.

    Un `fix` tradotto dove l'italiano non ne ha uno significa aver
    prescritto qualcosa in una lingua sola; uno mancante significa che
    il referto inglese perde l'istruzione e nessuno se ne accorge,
    perche' il ripiego e' silenzioso per costruzione."""
    con_fix_it = {c for c, v in mars_fixes.CATALOGO.items() if v.get("fix")}
    con_fix_altro = {c for c, v in RILIEVI[lingua].items() if v.get("fix")}
    assert con_fix_altro == con_fix_it

    con_es_it = {c for c, v in mars_fixes.CATALOGO.items()
                 if v.get("example")}
    con_es_altro = {c for c, v in RILIEVI[lingua].items()
                    if v.get("example")}
    assert con_es_altro == con_es_it


# ======================================================================
# La risoluzione dei testi
# ======================================================================

def test_in_italiano_il_rilievo_non_viene_toccato():
    rilievo = {"key": "tech.canonical.missing", "title": "2/3 pagine",
               "detail": "", "fix": "Dichiara.", "example": "",
               "params": {"pagine": 2, "totale": 3}}
    assert finding_texts(rilievo, "it")["title"] == "2/3 pagine"
    assert finding_texts(rilievo, "it")["fix"] == "Dichiara."


def test_una_lingua_sconosciuta_lascia_l_italiano():
    rilievo = {"key": "tech.canonical.missing", "title": "2/3 pagine",
               "params": {"pagine": 2, "totale": 3}}
    assert finding_texts(rilievo, "pt")["title"] == "2/3 pagine"


def test_un_rilievo_senza_chiave_resta_com_e():
    """Un plugin di terzi puo' non usare le chiavi: i suoi testi non si
    perdono, restano quelli che ha scritto lui."""
    rilievo = {"key": "", "title": "Un rilievo mio", "params": {}}
    assert finding_texts(rilievo, "en")["title"] == "Un rilievo mio"


def test_una_chiave_fuori_catalogo_resta_in_italiano():
    rilievo = {"key": "tech.inventata.mai_vista", "title": "Boh",
               "params": {}}
    assert finding_texts(rilievo, "en")["title"] == "Boh"


def test_finding_texts_torna_sempre_i_quattro_campi():
    """Anche vuoti: il chiamante non deve distinguere «campo assente»
    da «campo non tradotto»."""
    assert set(finding_texts({}, "en")) == set(mars_i18n.CAMPI_TRADOTTI)


def test_le_liste_nei_params_diventano_leggibili():
    """`%(urls)s` su una lista stamperebbe la repr Python, quadre e
    virgolette comprese."""
    leggibili = mars_i18n._params_leggibili({"urls": ["/a", "/b"], "n": 2})
    assert leggibili["urls"] == "/a, /b"
    assert leggibili["n"] == 2


def test_una_lista_arriva_leggibile_fino_al_testo_reso(monkeypatch):
    """Lo stesso, al confine che conta.

    Nessun template del catalogo usa oggi un parametro-lista, quindi
    senza questa prova la regola varrebbe solo per la funzione che la
    scrive: il giorno che qualcuno scrive `%(urls)s` il referto direbbe
    `['/a', '/b']` e nessun test diventerebbe rosso."""
    monkeypatch.setitem(RILIEVI["en"], "tech.index.noindex",
                        {"title": "Excluded: %(urls)s"})
    testi = finding_texts({"key": "tech.index.noindex", "title": "escluse",
                           "params": {"urls": ["/a", "/b"]}}, "en")
    assert testi["title"] == "Excluded: /a, /b"


def test_un_template_incoerente_lascia_in_piedi_gli_altri_campi(
        monkeypatch):
    """La degradazione dichiarata del principio 2, applicata alla prosa.

    Il catalogo qui e' rotto apposta: un `%(mai_visto)s` che i params
    non contengono. Il titolo resta italiano, il `fix` si traduce lo
    stesso, e nulla solleva."""
    monkeypatch.setitem(
        RILIEVI["en"], "tech.canonical.missing",
        {"title": "%(mai_visto)s pages", "fix": "Declare it."})
    testi = finding_texts(
        {"key": "tech.canonical.missing", "title": "2/3 pagine",
         "fix": "Dichiara.", "params": {"pagine": 2, "totale": 3}}, "en")
    assert testi["title"] == "2/3 pagine", "l'italiano regge il campo rotto"
    assert testi["fix"] == "Declare it.", "gli altri si traducono lo stesso"


@pytest.mark.parametrize("params", [
    {},                                   # nessun parametro
    {"pagine": "due", "totale": "tre"},   # tipo sbagliato per %d
    {"pagine": None, "totale": None},
])
def test_finding_texts_non_solleva_mai(params):
    """Un referto con una riga nella lingua sbagliata si legge, uno
    interrotto a meta' no."""
    testi = finding_texts({"key": "tech.canonical.missing",
                           "title": "titolo italiano",
                           "params": params}, "en")
    assert testi["title"]


def test_finding_texts_legge_anche_un_oggetto_finding():
    """Il rilievo attraversa il referto come dict, ma un chiamante puo'
    avere ancora il `Finding` in mano."""
    from mars_core import Finding, SEV_INFO
    f = Finding(area="mars_tech", severity=SEV_INFO,
                title="1/2 pagine senza <link rel=\"canonical\">",
                key="tech.canonical.missing",
                params={"pagine": 1, "totale": 2})
    assert finding_texts(f, "en")["title"] == \
        '1/2 pages without <link rel="canonical">'


# ======================================================================
# Nessun ripiego dove la traduzione c'e'
# ======================================================================

@pytest.mark.parametrize("lingua", TRADOTTE)
def test_sui_due_referti_sintetici_nessun_campo_ripiega(lingua,
                                                        monkeypatch):
    """Il test che coglie i template sbagliati.

    Il ripiego e' silenzioso per costruzione — e' cio' che rende il
    referto robusto — quindi un `%(pagine)d` scritto dove il modulo
    passa `pagine_totali` non si vedrebbe: uscirebbe l'italiano, e
    sembrerebbe una traduzione mancante invece di una rotta. Qui si
    esercita ogni campo tradotto contro i params VERI dei moduli.

    La prova e' che il template si RISOLVA, non che il risultato
    differisca dall'italiano: l'esempio nginx di `X-Frame-Options` non
    contiene una parola italiana, quindi tradotto e' identico, ed e'
    giusto cosi'. La differenza si pretende dal solo `title`, che e'
    prosa sempre."""
    for costruisci in DATASET.values():
        for area in costruisci(monkeypatch)["areas"]:
            for rilievo in area["findings"]:
                voce = RILIEVI[lingua].get(rilievo.get("key") or "")
                if not voce:
                    continue
                params = mars_i18n._params_leggibili(
                    rilievo.get("params") or {})
                testi = finding_texts(rilievo, lingua)
                for campo, template in voce.items():
                    # Solleva qui, e il rilievo avrebbe ripiegato in
                    # silenzio nel referto.
                    reso = template % params
                    assert testi[campo] == reso, \
                        "%s/%s ripiega sull'italiano" % (rilievo["key"],
                                                         campo)
                    assert "%(" not in testi[campo], \
                        "%s/%s: segnaposto non risolto" % (rilievo["key"],
                                                           campo)
                assert testi["title"] != rilievo.get("title"), \
                    "%s: il titolo tradotto e' identico" % rilievo["key"]


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_segnaposto_e_esercitato_contro_i_params_veri(lingua,
                                                           monkeypatch):
    """Il test precedente su un campione; questo sull'inventario.

    I due referti sintetici accendono due chiavi `tech.` su dodici: un
    `%(pages)d` scritto dove il modulo passa `pagine` sarebbe rimasto
    verde per sempre, perche' il ripiego e' silenzioso. Qui ogni
    template che contiene un segnaposto DEVE essere accompagnato da un
    caso che lo accenda — nei golden o nel banco qui sopra — e il
    segnaposto si risolve contro i params veri del modulo.

    Una chiave nuova con un segnaposto e senza caso diventa rossa il
    giorno in cui nasce, non il giorno in cui un sito la accende."""
    veri = dict(_params_dei_dataset(monkeypatch))
    veri.update(_params_del_banco(monkeypatch))
    for chiave, voce in RILIEVI[lingua].items():
        segnaposto = [c for c, t in voce.items() if "%(" in t]
        if not segnaposto:
            continue
        assert chiave in veri, \
            "%s ha un segnaposto e nessun caso che lo accenda" % chiave
        params = mars_i18n._params_leggibili(veri[chiave])
        for campo in segnaposto:
            reso = voce[campo] % params      # solleva se non combacia
            assert "%(" not in reso, "%s/%s" % (chiave, campo)


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_titolo_tradotto_e_non_vuoto(lingua):
    for chiave, voce in RILIEVI[lingua].items():
        assert voce.get("title", "").strip(), \
            "%s: titolo vuoto e' peggio di nessuna traduzione" % chiave


# ======================================================================
# Gli esempi tradotti sono ancora esempi che funzionano
# ======================================================================

def test_l_esempio_inglese_di_robots_chiude_davvero_il_rilievo():
    """Lo stesso presidio dell'italiano (U3.1), sulla copia tradotta.

    Tradurre i commenti di un esempio e' innocuo; tradurre un `Disallow`
    no, e un esempio che non chiude il rilievo che pretende di
    correggere e' peggio di nessun esempio."""
    esempio = RILIEVI["en"]["tech.robots.ai_blocked"]["example"]
    contesto = {"url": "https://esempio.test/", "pages": {},
                "robots": {"found": True, "text": esempio}, "sitemap": {}}
    chiavi = [f.key for f in mars_tech.controlla_robots(contesto)]
    assert "tech.robots.ai_blocked" not in chiavi


def test_l_esempio_inglese_di_robots_txt_dichiara_la_sitemap():
    esempio = RILIEVI["en"]["tech.robots.missing"]["example"]
    contesto = {"url": "https://esempio.test/", "pages": {},
                "robots": {"found": True, "text": esempio,
                           "sitemaps": ["https://example.com/sitemap.xml"]},
                "sitemap": {"found": True, "urls": 1, "with_lastmod": 1,
                            "unreadable": 0, "from_robots": True}}
    chiavi = [f.key for f in mars_tech.controlla_robots(contesto)
              + mars_tech.controlla_sitemap(contesto)]
    assert "tech.robots.missing" not in chiavi
    assert "tech.sitemap.not_in_robots" not in chiavi


def test_l_esempio_inglese_di_jsonld_si_analizza():
    import json
    esempio = RILIEVI["en"]["sd.jsonld.missing"]["example"]
    dentro = esempio.split(">", 1)[1].rsplit("<", 1)[0]
    assert json.loads(dentro)["@type"] == "LocalBusiness"


def test_l_elenco_troncato_dei_crawler_viaggia_nei_params():
    """Il titolo italiano ne mostra cinque; senza `elenco` nei params
    ogni lingua rifarebbe il troncamento per conto suo, e due viste
    dello stesso rilievo elencherebbero un numero diverso di crawler."""
    blocca = "\n".join("User-agent: %s\nDisallow: /" % a
                       for a in sorted(mars_tech.CRAWLER_IA))
    contesto = {"url": "https://esempio.test/", "pages": {},
                "robots": {"found": True, "text": blocca}, "sitemap": {}}
    rilievo = [f for f in mars_tech.controlla_robots(contesto)
               if f.key == "tech.robots.ai_blocked"][0]
    assert rilievo.params["elenco"].count(",") == 4, "cinque, non tutti"
    assert rilievo.params["elenco"] in rilievo.title
    tradotto = finding_texts(rilievo.as_dict(), "en")["title"]
    assert rilievo.params["elenco"] in tradotto, \
        "le due lingue elencano gli stessi crawler"
