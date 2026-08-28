#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — i cataloghi di traduzione dei rilievi (U9.1).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import ast
import os
import re

import pytest

import mars_citability
import mars_core
import mars_fixes
import mars_i18n
import mars_tech
from conftest import pagina
from mars_core import AREA_PREFIX
from mars_i18n import LINGUE, RILIEVI, finding_texts, normalizza_lingua
from test_golden import DATASET, GENERATED_AT

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
    import mars_lexical
    import mars_schema
    import mars_semantic
    import mars_seo
    import mars_wcag

    veri = {}

    def raccogli(esito):
        for f in esito.get("findings") or []:
            if f.get("key"):
                veri.setdefault(f["key"], f.get("params") or {})

    # Area 1: noindex, nofollow e canonical altrove sulla stessa pagina,
    # piu' una sitemap illeggibile e senza lastmod. La seconda pagina
    # porta il divieto di frammento e la cache vietata, e li porta
    # SENZA noindex: su una pagina esclusa dagli indici il rilievo del
    # frammento non scatta, e il segnaposto resterebbe non esercitato.
    tech = {
        "url": "https://esempio.test/",
        "pages": {"https://esempio.test/": pagina(
            '<html><head><meta name="robots" content="noindex, nofollow">'
            '<link rel="canonical" href="https://altro.test/x">'
            '</head><body><p>x</p></body></html>'),
            "https://esempio.test/b": pagina(
            '<html><head><meta name="robots" content="nosnippet, '
            'noarchive"></head><body><p>x</p></body></html>'),
            # Terza pagina e non una direttiva in piu' sulla seconda:
            # una pagina scaduta e' fuori dagli indici, e il divieto di
            # frammento non vi scatterebbe piu'.
            "https://esempio.test/c": pagina(
            '<html><head><meta name="robots" content="unavailable_after: '
            '2020-01-01"></head><body><p>x</p></body></html>'),
            # Quarta pagina: una direttiva riservata a un agente che non
            # e' un assistente. Sta sull'HEADER e non sul meta, perche'
            # il prefisso per agente vive solo li' (R37).
            "https://esempio.test/d": dict(
            pagina('<html><head></head><body><p>x</p></body></html>'),
            x_robots_tag="googlebot: noindex")},
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
    monkeypatch.setattr(mars_seo.shutil, "which", lambda _, path=None: "/bin/lighthouse")
    monkeypatch.setattr(mars_seo, "esegui_lighthouse", _timeout_lighthouse)
    raccogli(mars_seo.audit({"url": "https://esempio.test/"}))
    monkeypatch.undo()

    # Aree 3 e 4 (U13): due pagine con lo STESSO title, testo senza una
    # domanda, e una query che non trova nulla ne' lessicalmente ne'
    # semanticamente. I golden accendono `lex.words.thin`,
    # `lex.query.no_match` e `sem.chunks.few`; le altre quattro chiavi
    # hanno bisogno di questo caso.
    def _pag(url, titolo, testo):
        return {"title": titolo, "text": testo, "lang": "it", "html": "",
                "headings": [], "chunks": [{"url": url, "heading": titolo,
                                            "text": testo}]}

    prosa = " ".join(["organizzazione"] * 60)
    doppie = {"https://esempio.test/a": _pag("https://esempio.test/a",
                                             "Servizi", prosa),
              "https://esempio.test/b": _pag("https://esempio.test/b",
                                             "Servizi", prosa)}
    ranghi = {"url": "https://esempio.test/", "pages": doppie,
              "chunks": [c for p in doppie.values() for c in p["chunks"]],
              # "zzzzz qqqqq" non ha riscontro nemmeno per il proxy
              # char-TFIDF: e' lo stesso corpus-guardia di R23.
              "queries": ["zzzzz qqqqq"], "embeddings_model": "none",
              "force_proxy": True, "credentials": {}}
    raccogli(mars_lexical.audit(ranghi))
    raccogli(mars_semantic.audit(ranghi))

    # Pagine che ci sono e non producono un passaggio: `sem.chunks.none`.
    vuote = {"pages": {"https://esempio.test/": {
        "title": "Vuota", "text": "", "lang": "it", "html": "",
        "headings": [], "chunks": []}},
        "chunks": [], "queries": [], "embeddings_model": "none",
        "force_proxy": True, "credentials": {}}
    raccogli(mars_semantic.audit(vuote))

    # Area 9 (U10.1, U10): gli otto temi del vocabolario piu' il secchio,
    # e il giudice sconosciuto. I golden ne accendono tre su nove: le
    # altre le accende un sito vero, e allora e' tardi per scoprirle
    # senza traduzione. `rilievi_dei_punti_deboli` E' il modulo che
    # quei params li costruisce — chiamarlo e' esercitare il vero.
    import mars_llm_judge
    for chiave, tema in list(mars_llm_judge.VOCABOLARIO.items()) + [
            (mars_llm_judge.FUORI_VOCABOLARIO, mars_llm_judge.TEMA_ALTRO)]:
        for f in mars_llm_judge.rilievi_dei_punti_deboli(
                [(chiave, "Osservazione del modello.")], "anthropic",
                mars_llm_judge.MODEL):
            veri.setdefault(f["key"], f["params"])
    raccogli(mars_llm_judge.audit({
        "url": "https://esempio.test/", "llm": "on",
        "judge_models": "giudice-che-non-esiste",
        "chunks": [{"url": "https://esempio.test/", "heading": "Titolo",
                    "text": "Un passaggio qualunque."}]}))

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

    # Area 7: il perimetro dello spider, che i golden non accendono
    # perche' vi girano senza dichiarazione di proprieta'. Serve un
    # daemon finto: la chiave nasce solo dove lo spider parte davvero.
    import mars_wapt

    class _ZapPerIl18n:
        def spider_scan(self, url, max_children=0):
            return "1"

        def spider_status(self, sid):
            return 100

        def ascan_scan(self, url):
            return "2"

        def ascan_status(self, sid):
            return 100

        def max_depth(self):
            return 5

        def alerts(self, baseurl):
            return []

    raccogli(mars_wapt.audit({"url": "https://esempio.test/",
                              "urls": ["https://esempio.test/"],
                              "_zap_client": _ZapPerIl18n(),
                              "owner_declaration": True,
                              "max_children": 10}))
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


# ======================================================================
# La cornice: le etichette e le note che il referto scrive di suo (U9.2)
# ======================================================================

def _costanti_traducibili(nodo: ast.AST) -> set:
    """Le stringhe che un'espressione passata a `t()` puo' valere.

    Scende in `if/else` e in `or` — le due forme che il renderer usa per
    scegliere fra due testi — e si ferma davanti a tutto il resto: un
    `.get(chiave, default)` o un `area["label"]` non sono testi da
    tradurre ma il modo di andarli a prendere.
    """
    if isinstance(nodo, ast.Constant):
        return {nodo.value} if isinstance(nodo.value, str) and nodo.value \
            else set()
    if isinstance(nodo, ast.IfExp):
        return (_costanti_traducibili(nodo.body)
                | _costanti_traducibili(nodo.orelse))
    if isinstance(nodo, ast.BoolOp):
        return set().union(*(_costanti_traducibili(v) for v in nodo.values))
    return set()


def _letterali_di_t() -> set:
    """(testo, contesto) di ogni `t("...")` scritto in mars_report.py.

    Letto dall'AST e non con una regex: `t()` compare dentro `%`,
    concatenazioni e f-string, e una regex su una stringa spezzata su
    quattro righe non la ricompone.
    """
    percorso = os.path.join(RADICE, "mars_report.py")
    with open(percorso, encoding="utf-8") as f:
        arbre = ast.parse(f.read())
    trovati = set()
    for nodo in ast.walk(arbre):
        if not (isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Name)):
            continue
        if nodo.func.id == "t" and nodo.args:
            contesto = ""
            if len(nodo.args) > 2 and isinstance(nodo.args[2], ast.Constant):
                contesto = str(nodo.args[2].value)
            # Il primo argomento puo' essere un letterale, un
            # condizionale — `t("buono" if ... else "critico")` — o una
            # catena `or`. Si scende in quelli e non in tutto il
            # sottoalbero: `ast.walk` prenderebbe anche la "label" di
            # `t(area["label"], lang)`, che e' la chiave di un dict e
            # non un testo da tradurre.
            for testo in _costanti_traducibili(nodo.args[0]):
                trovati.add((testo, contesto))
        elif nodo.func.id == "_plurale" and len(nodo.args) >= 3:
            # Le due forme di `_plurale` finiscono in `t()` una alla
            # volta, e il contesto glielo mette lui dal numero.
            for posizione, contesto in ((1, "singolare"), (2, "plurale")):
                arg = nodo.args[posizione]
                if isinstance(arg, ast.Constant) \
                        and isinstance(arg.value, str):
                    trovati.add((arg.value, contesto))
    return trovati


def _testi_dal_dato() -> set:
    """I testi che arrivano a `t()` dal DATO invece che dal renderer.

    Non li vede l'AST — la chiamata e' `t(area["label"], lang)` — e i
    due referti sintetici ne accendono solo una parte: le corsie del
    piano hanno quattro motivi possibili e i golden ne esercitano uno.
    Si enumerano quindi dalle costanti che li producono, che e' la
    stessa fonte da cui li prende il codice vero.
    """
    import mars_citability
    import mars_remediation
    import mars_report as rp

    testi = set()
    testi |= {etichetta for _, etichetta in mars_core.MODULES_REGISTRY}
    testi |= set(rp.STATO_LEGGIBILE.values())
    testi |= {e for _, _, e in rp.SECCHIELLI_PROFONDITA}
    testi.add("profondità ignota")
    testi.add(rp.ASSUNZIONE_SUPERFICIE)
    testi |= set(mars_remediation.SFORZO.values())
    testi |= {motivo for penalita in (None, 0.0, 5.0)
              for guadagno in (None, 0, 3)
              for certificata in (True, False)
              for _, motivo in [mars_remediation._corsia(penalita, guadagno,
                                                         certificata)]
              if motivo}
    # Il motivo di ogni migrazione di chiave dichiarata: e' prosa
    # italiana in una tabella di mars_history, e arriva a `t()` come
    # variabile — lo scanner dei letterali non la vede (R39).
    import mars_history
    testi |= {m["reason"] for m in mars_history.MIGRAZIONI_CHIAVE}
    # Stessa storia per le misure cambiate (R63): prosa italiana in una
    # tabella, che arriva a `t()` come variabile.
    testi |= {m["reason"] for m in mars_history.MISURE_CAMBIATE}
    # Le due discovery del crawler, e i due nomi dei segnali derivati.
    testi |= {"sitemap", "link interni"}
    testi |= {"Recuperabilità", "In forma di risposta"}
    testi.add(mars_citability.DISCLAIMER)
    testi |= set(rp._MARCATORE.values())
    testi |= set(rp._GRAVITA_TESTO.values())
    testi |= {e for _, e in rp._BADGE_GRAVITA.values()}
    testi |= {e for _, e, _ in rp.TESSERE_GRAVITA}
    testi |= {e for _, e in rp.TREEMAP_GRAVITA.values()}
    # I tre settori del donut delle pagine: le etichette stanno in una
    # costante e arrivano a `t()` come variabile, quindi lo scanner dei
    # letterali non le vede (R49).
    testi |= {e for _, e, _ in rp.SETTORI_PAGINE}
    testi |= set(rp.COLONNE_CSV)
    # I segnali di pagina di mars_semantic, dalla funzione che li emette.
    import mars_semantic
    testi |= set(mars_semantic.page_signals(
        {"html": "<script>faqpage</script>"}))
    # I nomi di strumento che portano una parola italiana. Quelli che il
    # modulo COMPONE — «vettoriale <modello>», «BM25 (k1=…)» — nessun
    # catalogo puo' contenerli, ed e' scritto in `_qualificatori`.
    testi |= {"HTTP-Headers", "ZAP (attiva)", "ZAP (passiva)", "axe-core",
              "markup"}
    return {x for x in testi if x}


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_letterale_della_cornice_e_a_catalogo(lingua):
    """Il presidio che regge la scelta di indicizzare sul testo italiano.

    Cambiare una parola in `mars_report.py` scollega la traduzione senza
    rompere nulla — esce l'italiano, che e' un ripiego valido e quindi
    invisibile. Qui la riconnessione e' obbligatoria."""
    catalogo = mars_i18n.CORNICE[lingua]
    mancanti = sorted(
        testo for testo, contesto in _letterali_di_t()
        if testo not in catalogo
        and (contesto + mars_i18n.SEPARATORE_CONTESTO + testo)
        not in catalogo)
    assert not mancanti, "cornice senza traduzione %s: %s" % (lingua,
                                                              mancanti)


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_ogni_testo_che_viene_dal_dato_e_a_catalogo(lingua):
    """Le etichette d'area, i secchielli, gli sforzi, le corsie.

    Non stanno nel renderer, quindi il test precedente non li vede: se
    ne aggiunge uno — un'area nuova, un livello di sforzo, un motivo di
    corsia — questo diventa rosso."""
    mancanti = sorted(_testi_dal_dato() - set(mars_i18n.CORNICE[lingua]))
    assert not mancanti, "dal dato, senza traduzione: %s" % mancanti


@pytest.mark.parametrize("lingua", TRADOTTE)
def test_nessuna_voce_di_cornice_e_orfana(lingua):
    """Il verso opposto: una traduzione che nessuno chiede piu'.

    Senza, una riscrittura del renderer lascerebbe dietro le voci
    vecchie, che non rompono nulla e fanno sembrare coperto cio' che
    non lo e'."""
    vive = {testo for testo, _ in _letterali_di_t()} | _testi_dal_dato()
    orfane = []
    for chiave in mars_i18n.CORNICE[lingua]:
        nudo = chiave.split(mars_i18n.SEPARATORE_CONTESTO, 1)[-1]
        if nudo not in vive:
            orfane.append(chiave)
    assert not sorted(orfane), "tradotte e mai chieste: %s" % sorted(orfane)


def test_il_contesto_disambigua_due_significati():
    """«da migliorare» e' un verdetto e un'etichetta del giudizio LLM.

    Senza contesto una delle due sarebbe sbagliata, e non lo direbbe
    nessuno: entrambe sono traduzioni plausibili della stessa stringa."""
    assert mars_i18n.t("da migliorare", "en") == "needs work"
    assert mars_i18n.t("da migliorare", "en", "llm") == "to improve"
    # Un contesto senza voce propria ripiega sulla chiave nuda invece
    # di sparire.
    assert mars_i18n.t("da migliorare", "en", "mai_visto") == "needs work"


def test_il_plurale_inglese_non_dice_tre_click():
    """In italiano «click» non cambia al plurale, in inglese sì.

    `_plurale(3, "click", "click")` chiede due volte la stessa parola:
    senza il contesto del numero il catalogo non puo' distinguerle, e
    il referto inglese direbbe «3 click»."""
    from mars_report import _plurale
    assert _plurale(1, "click", "click", "en") == "1 click"
    assert _plurale(3, "click", "click", "en") == "3 clicks"
    assert _plurale(1, "pagina", "pagine", "en") == "1 page"
    assert _plurale(3, "pagina", "pagine", "en") == "3 pages"
    # L'italiano non si muove.
    assert _plurale(3, "click", "click") == "3 click"


# ======================================================================
# Il referto reso in inglese, da un capo all'altro
# ======================================================================

PROSA = ("text", "html", "markdown", "csv")


def _resa(monkeypatch, dataset: str, formato: str, lingua: str) -> str:
    """Una resa del referto, con l'orario fissato.

    `generated_at` nasce da `time.strftime` al SECONDO
    (`mars_report.py`) e arriva fino alla resa. Meta' dei test qui
    sotto confrontano DUE `_resa` — «pt rende come it», «il JSON resta
    italiano» — e due costruzioni a cavallo di un secondo producono due
    documenti diversi: rosso a caso, su un difetto che non c'e'.
    `tests/test_golden.py` fissa lo stesso campo, per la stessa ragione,
    da sempre.
    """
    from mars_report import RENDERERS
    referto = DATASET[dataset](monkeypatch)
    referto["generated_at"] = GENERATED_AT
    return RENDERERS[formato](referto, lingua)


def test_due_rese_non_dipendono_dal_secondo_in_cui_girano(monkeypatch):
    """Il confronto fra due rese non deve poter fallire per l'orologio.

    Trovato chiudendo R28: `test_una_lingua_sconosciuta_rende_come_l_
    italiano[html]` e' uscito rosso una volta su sei esecuzioni, e non
    era riproducibile a comando — perche' serve che le due costruzioni
    cadano su due secondi diversi. Qui l'orologio avanza di proposito a
    ogni lettura: senza il campo fissato in `_resa` questo test e' rosso
    sempre, invece che a caso.
    """
    import time
    scatti = iter(["2026-01-01T00:00:0%d+0000" % n for n in range(9)])
    monkeypatch.setattr(time, "strftime",
                        lambda *a, **k: next(scatti))

    assert _resa(monkeypatch, "referto", "html", "it") == \
        _resa(monkeypatch, "referto", "html", "it")


@pytest.mark.parametrize("formato", PROSA)
@pytest.mark.parametrize("dataset", sorted(DATASET))
def test_il_titolo_italiano_non_sopravvive_dove_la_traduzione_c_e(
        dataset, formato, monkeypatch):
    """Il test che ha trovato il difetto delle voci di piano.

    Il ripiego e' silenzioso: un titolo che non si traduce esce in
    italiano, ed e' indistinguibile da uno che non ha traduzione. Qui si
    guarda la RESA e si pretende che, per ogni rilievo con una voce a
    catalogo, ci sia il titolo inglese e non quello italiano.

    Cosi' e' venuto fuori che le voci del piano non portavano i
    `params`: `%(campi)d campi di modulo senza etichetta` non si poteva
    risolvere, e il piano — la parte del referto che si consegna —
    restava in italiano mentre le schede d'area erano tradotte.

    La prova e' NEGATIVA — nessun titolo italiano sopravvive — e non
    anche positiva, perche' le viste compatte tagliano a due o tre voci
    e l'elenco dei rilievi non ha lo stesso ordine di quello delle
    issues: pretendere che un titolo inglese *compaia* significherebbe
    pretendere che sopravviva al taglio. Il verso positivo lo prova il
    test sul CSV, che i rilievi li porta tutti."""
    referto = DATASET[dataset](monkeypatch)
    from mars_report import RENDERERS
    reso = RENDERERS[formato](referto, "en")
    italiano_reso = RENDERERS[formato](referto, "it")
    controllati = 0
    for area in referto["areas"]:
        for rilievo in area.get("findings") or []:
            voce = RILIEVI["en"].get(rilievo.get("key") or "")
            if not voce or "title" not in voce:
                continue
            italiano = rilievo.get("title") or ""
            if not italiano or italiano == finding_texts(rilievo,
                                                         "en")["title"]:
                continue
            if italiano not in italiano_reso:
                continue      # non compare in questa vista: nulla da dire
            controllati += 1
            assert italiano not in reso, \
                "%s: il titolo italiano sopravvive" % rilievo["key"]
    assert controllati, "il test non ha guardato nulla"


@pytest.mark.parametrize("dataset", sorted(DATASET))
def test_nel_csv_ogni_rilievo_traducibile_e_tradotto(dataset, monkeypatch):
    """Il verso positivo, dove si puo' fare: il CSV e' l'unica vista che
    porta TUTTI i rilievi, senza tagli e senza ordinamenti propri."""
    referto = DATASET[dataset](monkeypatch)
    from mars_report import RENDERERS
    # Il CSV si PARSA e non si cerca per sottostringa: un titolo che
    # contiene una virgoletta — `<link rel="canonical">` — viene
    # quotato e le virgolette raddoppiate, e un `in` fallirebbe su un
    # file perfettamente corretto.
    import csv as modulo_csv
    import io
    reso = RENDERERS["csv"](referto, "en").lstrip("\ufeff")
    titoli = {r[4] for r in modulo_csv.reader(io.StringIO(reso),
                                              delimiter=";")}
    controllati = 0
    for area in referto["areas"]:
        for rilievo in area.get("findings") or []:
            voce = RILIEVI["en"].get(rilievo.get("key") or "")
            if not voce or "title" not in voce:
                continue
            controllati += 1
            assert finding_texts(rilievo, "en")["title"] in titoli, \
                "%s: il titolo inglese non compare" % rilievo["key"]
    assert controllati, "il test non ha guardato nulla"


@pytest.mark.parametrize("dataset", sorted(DATASET))
def test_il_piano_e_tradotto_come_le_schede(dataset, monkeypatch):
    """Le voci del piano sono COPIE dei rilievi, e devono tradursi
    uguale: e' la parte del referto che si consegna."""
    referto = DATASET[dataset](monkeypatch)
    for voce in referto.get("remediation") or []:
        atteso = RILIEVI["en"].get(voce.get("key") or "")
        if not atteso or "title" not in atteso:
            continue
        assert finding_texts(voce, "en")["title"] == \
            atteso["title"] % mars_i18n._params_leggibili(voce["params"]), \
            "%s: la voce di piano ripiega" % voce["key"]


@pytest.mark.parametrize("formato", PROSA)
def test_una_lingua_sconosciuta_rende_come_l_italiano(formato, monkeypatch):
    """Il ripiego arriva fino alla resa, non solo a `normalizza_lingua`."""
    assert _resa(monkeypatch, "referto", formato, "pt") == \
        _resa(monkeypatch, "referto", formato, "it")


def test_il_json_resta_italiano_in_ogni_lingua(monkeypatch):
    """Il dato canonico non ha una lingua per chiamante: chi lo consuma
    ha `key` e `params` e traduce da se'."""
    assert _resa(monkeypatch, "referto", "json", "en") == \
        _resa(monkeypatch, "referto", "json", "it")


def test_l_html_dichiara_la_lingua_che_parla(monkeypatch):
    """`<html lang>` e' il criterio WCAG 3.1.1 che questo referto misura
    sulle pagine altrui: cablarlo a `it` su un referto inglese sarebbe
    il difetto che il documento rileva, commesso dal documento."""
    assert "<html lang='it'>" in _resa(monkeypatch, "referto", "html", "it")
    assert "<html lang='en'>" in _resa(monkeypatch, "referto", "html", "en")


def _referto_con_area_muta() -> dict:
    """Un referto con un'area che ha `issues` e nessun rilievo.

    Fino a U10.1 quell'area era il giudizio LLM, e i due referti
    sintetici la portavano da soli: i `punti_deboli` erano prosa, e
    prosa senza chiave non si traduce. Da U10.1 ogni area del progetto
    emette rilievi, quindi il caso — che resta possibile, e per un
    modulo di terzi resta il caso normale — si costruisce qui invece di
    contare su un'area che non lo esercita piu'.
    """
    from mars_report import build_report
    return build_report(
        {"mars_lexical": {"score": 50, "issues": ["prosa italiana"]}},
        {"url": "https://esempio.test/"})


def test_la_nota_di_onesta_compare_solo_fuori_dall_italiano(monkeypatch):
    """E nomina le aree, invece di dire genericamente che qualcosa non
    è stato tradotto."""
    italiano = _resa(monkeypatch, "referto", "text", "it")
    inglese = _resa(monkeypatch, "referto", "text", "en")
    assert "evidence quoted from the audited site" in inglese
    assert "evidence quoted" not in italiano
    assert "Nota: le evidenze" not in italiano
    # Sul referto sintetico la seconda riga della nota NON c'e' piu', ed
    # e' un fatto su U10.1: ogni area emette rilievi, quindi non resta
    # italiano da dichiarare. Asserirlo qui fa fallire il giorno in cui
    # un'area smettesse di emetterne senza che nessuno se ne accorga.
    assert "These areas speak Italian only" not in inglese


def test_l_intestazione_del_csv_e_tradotta(monkeypatch):
    prima = _resa(monkeypatch, "referto", "csv", "en").split("\r\n")[0]
    assert prima.lstrip("﻿").startswith("site;area;severity;weight")


def test_le_aree_senza_rilievi_restano_dichiarate():
    """`_righe_compatte` mostra i titoli dei rilievi fuori dall'italiano,
    ma dove i rilievi non ci sono le issues restano italiane: e' un
    fatto, e va dichiarato invece che nascosto."""
    from mars_report import aree_non_tradotte, render_text
    referto = _referto_con_area_muta()
    assert aree_non_tradotte(referto, "it") == []
    assert aree_non_tradotte(referto, "en") == ["3. Lexical"]
    riga = [r for r in render_text(referto, "en").split("\n")
            if r.startswith("These areas speak Italian only:")]
    assert riga == ["These areas speak Italian only: 3. Lexical."]


# ======================================================================
# La lingua chiesta agli strumenti (U9.3, e con essa R44)
# ======================================================================

def test_la_lingua_entra_nel_contesto():
    """`lang` sta nel contesto accanto a `market` e `llm`, e non e' una
    scelta di resa: gli strumenti producono i propri testi al momento
    della misura, e glieli si deve chiedere allora."""
    import inspect
    firma = inspect.signature(mars_core.build_context)
    assert firma.parameters["lang"].default == "it"


def test_lighthouse_riceve_il_locale_del_referto(monkeypatch):
    """`--locale` glielo passiamo noi: senza, Lighthouse scriverebbe
    nella lingua del sistema su cui gira, che nessuno ha scelto."""
    import mars_seo
    visti = {}

    class _Esito:
        stdout = "{}"

    def finto(cmd, **kwargs):
        visti["cmd"] = cmd
        return _Esito()

    monkeypatch.setattr(mars_seo.subprocess, "run", finto)
    mars_seo.esegui_lighthouse("https://esempio.test/", "/bin/lighthouse",
                               "en")
    assert "--locale=en" in visti["cmd"]
    # E l'URL resta un ARGOMENTO, mai interpolato: e' R3.
    assert "https://esempio.test/" in visti["cmd"]


def test_la_lingua_di_lighthouse_si_legge_dal_referto_non_dalla_richiesta():
    """Davanti a un locale che non conosce Lighthouse ripiega
    sull'inglese e lo scrive in `configSettings.locale`.

    Dichiarare la lingua RICHIESTA direbbe una cosa non vera, ed e' il
    genere di mezza verita' che il referto evita ovunque."""
    import mars_seo
    assert mars_seo.lingua_lhr({"configSettings": {"locale": "en-US"}}) == \
        "en"
    assert mars_seo.lingua_lhr({"configSettings": {"locale": "it"}}) == "it"
    # Senza il campo si assume la lingua di ripiego dichiarata.
    assert mars_seo.lingua_lhr({}) == mars_seo.LOCALE


def test_axe_non_cerca_un_locale_inglese():
    """axe parla inglese di suo: `help` e `description` arrivano nella
    risposta. Cercare un `en.json` che non esiste e dichiararne
    l'assenza segnalerebbe un difetto dove non ce n'e' uno."""
    import mars_wcag
    assert mars_wcag.percorso_locale_axe("en") == ""
    assert mars_wcag.percorso_locale_axe("it").endswith("it.json")
    assert mars_wcag.percorso_locale_axe("") == ""


def test_gli_strumenti_dichiarano_la_lingua_dei_propri_testi(monkeypatch):
    """Le tre famiglie che prendono i testi da terzi lo dicono nei
    params, rilievo per rilievo: e' cio' su cui il referto costruisce
    la nota, invece di indovinare una lingua leggendo il testo."""
    referto = DATASET["referto"](monkeypatch)
    visti = {}
    for area in referto["areas"]:
        for rilievo in area.get("findings") or []:
            if mars_i18n.dallo_strumento(rilievo.get("key") or ""):
                visti[rilievo["key"]] = rilievo["params"].get("text_lang")
    assert visti, "il referto sintetico ha rilievi dalle tre famiglie"
    assert all(v for v in visti.values()), \
        "un rilievo da strumento senza `text_lang`: %s" % visti
    # ZAP parla inglese e basta; Lighthouse ha girato in italiano.
    assert visti["sec.zap.40012"] == "en"
    assert visti["seo.lh.document_title"] == "it"
    # axe: tradotto dove il locale conosce la regola, inglese dove no.
    assert visti["wcag.axe.image_alt"] == "it"
    assert visti["wcag.axe.label"] == "en"


def test_la_nota_sugli_strumenti_compare_anche_in_italiano(monkeypatch):
    """ZAP scrive solo in inglese, e un referto italiano che non lo
    dicesse lascerebbe credere a una dimenticanza cio' che e' un limite
    dello strumento."""
    from mars_report import strumenti_in_altra_lingua
    referto = DATASET["referto"](monkeypatch)
    italiano = strumenti_in_altra_lingua(referto, "it")
    assert any(s.startswith("ZAP") for s in italiano)
    reso = _resa(monkeypatch, "referto", "text", "it")
    assert "ZAP (passiva) (en)" in reso
    # In inglese ZAP non compare piu': e' gia' nella lingua giusta.
    inglese = strumenti_in_altra_lingua(referto, "en")
    assert not [s for s in inglese if s.startswith("ZAP")]


def test_in_inglese_lighthouse_e_axe_finiscono_nella_nota(monkeypatch):
    """Il referto sintetico gira con Lighthouse e axe in italiano: reso
    in inglese, sono LORO a non essere nella lingua giusta.

    E' la prova che la nota si legge dal dato e non da una costante:
    gli stessi strumenti compaiono o no a seconda della lingua."""
    from mars_report import strumenti_in_altra_lingua
    referto = DATASET["referto"](monkeypatch)
    inglese = strumenti_in_altra_lingua(referto, "en")
    assert any(s.startswith("Lighthouse") for s in inglese)
    assert any(s.startswith("axe-core") for s in inglese)


def test_r44_il_titolo_axe_non_e_piu_inglese_in_un_referto_italiano(
        monkeypatch):
    """R44, reso eseguibile sul referto congelato.

    Il difetto: `wcag.axe.*` portava come titolo il `help` inglese che
    axe manda nella risposta, dentro un'interfaccia italiana e accanto
    a un `fix` che italiano lo era — perche' quello veniva dal locale.
    """
    referto = DATASET["referto"](monkeypatch)
    area = [a for a in referto["areas"] if a["module"] == "mars_wcag"][0]
    per_chiave = {f["key"]: f for f in area["findings"]}
    tradotto = per_chiave["wcag.axe.image_alt"]
    assert tradotto["title"] == "Le immagini devono avere un testo alternativo"
    assert tradotto["title"] != tradotto["fix"], \
        "help e description sono due frasi diverse, ed e' il punto"
    # E la riga compatta dice la stessa cosa del rilievo: prima
    # divergevano, perche' leggeva il `help` grezzo.
    assert any(tradotto["title"] in i for i in area["issues"])


def test_la_lingua_dell_audit_arriva_ad_axe(contesto, monkeypatch):
    """La cucitura fra `context["lang"]` e `score_from_violations`.

    Colta da una mutazione: togliendo il parametro dalla chiamata, la
    suite restava verde. Il predefinito e' l'italiano, e ogni altro
    test del ramo axe gira in italiano — quindi la plumbing non era
    esercitata da nessuno, e un audit in inglese avrebbe prodotto testi
    italiani senza che nulla lo dicesse.
    """
    import mars_wcag
    from conftest import pagina
    violazione = {"id": "image-alt", "impact": "critical",
                  "help": "Images must have alternative text",
                  "description": "Ensure <img> elements have alt text",
                  "nodes": [{"target": ["img"]}]}
    contesto["pages"] = {"https://x/": pagina()}
    monkeypatch.setattr(mars_wcag, "axe_disponibile", lambda: True)
    monkeypatch.setattr(mars_wcag, "run_axe",
                        lambda urls, delay=0.0: ([dict(violazione)], 1))

    contesto["lang"] = "it"
    italiano = [f for f in mars_wcag.audit(contesto)["findings"]
                if f["key"] == "wcag.axe.image_alt"][0]
    contesto["lang"] = "en"
    inglese = [f for f in mars_wcag.audit(contesto)["findings"]
               if f["key"] == "wcag.axe.image_alt"][0]

    assert italiano["title"] == "Le immagini devono avere un testo alternativo"
    assert italiano["params"]["text_lang"] == "it"
    assert inglese["title"] == "Images must have alternative text"
    assert inglese["params"]["text_lang"] == "en"


def test_i18n_il_perimetro_dellarea_7_e_un_numero_anche_in_inglese():
    """Sfuggita alle mutazioni di R55: togliere `%(pages)d` dal titolo
    inglese lasciava verde tutto. I test di parita' controllano che una
    chiave sia tradotta, non che la traduzione dica la stessa cosa —
    e un perimetro senza numero non dichiara alcun perimetro."""
    rilievo = {"key": "sec.status.passive_only", "title": "originale",
               "detail": "", "fix": "", "example": "",
               "params": {"active_scan": False, "pages": 7,
                          "urls": ["a"] * 7}}
    assert "7" in finding_texts(rilievo, "en")["title"]
