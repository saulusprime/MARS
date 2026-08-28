#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — il catalogo dei testi di correzione (U3.1).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import pytest

import mars_core
import mars_fixes
import mars_schema
import mars_tech
from conftest import pagina
from test_golden import DATASET

# Le tre famiglie che prendono il testo DALLO STRUMENTO e non dal
# catalogo, come coppie (area, famiglia) e non come nomi soli: `seo` e'
# anche il secondo segmento di `cit.seo.weak`, e confrontare un segmento
# per volta li confonderebbe.
DINAMICHE = {("wcag", "axe"), ("sec", "zap"), ("seo", "lh")}


def _tutti_i_findings(monkeypatch) -> list:
    """Ogni rilievo che i due referti sintetici sanno produrre."""
    rilievi = []
    for costruisci in DATASET.values():
        for area in costruisci(monkeypatch)["areas"]:
            rilievi += area["findings"]
    return rilievi


def test_il_catalogo_veste_solo_dove_il_modulo_ha_lasciato_vuoto():
    """Il modulo vince, il catalogo colma.

    E' cio' che permette a mars_wapt di conservare la `solution` che ZAP
    gli ha dato, e a un plugin di terzi di portare i propri testi senza
    sapere che il catalogo esista."""
    # `penalty` nei params: da I18 il catalogo veste i soli rilievi che
    # dichiarano un difetto — vedi `test_il_catalogo_non_veste_un_
    # controllo_che_non_e_fallito`.
    suo = {"key": "tech.robots.missing", "fix": "Il mio fix.",
           "example": "", "params": {"penalty": 40.0}}
    mars_fixes.vesti(suo)
    assert suo["fix"] == "Il mio fix.", "il modulo vince"
    assert suo["example"], "e il catalogo colma cio' che era vuoto"


def test_una_chiave_fuori_catalogo_non_viene_toccata():
    vuoto = {"key": "tech.inventata.mai_vista", "fix": "", "example": ""}
    assert mars_fixes.vesti(dict(vuoto)) == vuoto


def test_ogni_rilievo_che_puo_essere_corretto_dice_come(monkeypatch):
    """La regola di quest'area, resa eseguibile.

    Riceve un fix solo il rilievo che descrive uno stato DEL SITO che
    chi lo possiede puo' cambiare. Tre esenzioni, e sono `elif` di un
    unico ramo: gli stati della scansione, i derivati della citabilita'
    — che ridicono un difetto gia' quantificato altrove — e le tre
    famiglie che il testo lo prendono dallo strumento.

    Cosi' una chiave nuova senza fix diventa rossa il giorno in cui
    nasce, invece che alla Fase 9."""
    for f in _tutti_i_findings(monkeypatch):
        area, famiglia = f["key"].split(".")[:2]
        if ".status." in f["key"]:
            assert not f["fix"], "%s: e' un fatto sulla scansione" % f["key"]
        elif f["params"].get("derived"):
            assert not f["fix"], "%s: e' un derivato" % f["key"]
        elif (area, famiglia) in DINAMICHE:
            pass          # il testo viene dallo strumento, non da qui
        else:
            assert f["fix"], "%s non dice come si corregge" % f["key"]


def test_ogni_voce_del_catalogo_e_prescrittiva():
    """Un fix e' un'istruzione, non un'osservazione.

    I due dataset dei golden esercitano dieci chiavi su venticinque:
    le altre quindici non le vedrebbe nessuno finche' un sito reale non
    le accende. Qui si guardano tutte."""
    for chiave, voce in mars_fixes.CATALOGO.items():
        fix = voce.get("fix", "")
        assert fix, chiave
        assert len(fix) > 40, "%s: troppo corto per essere utile" % chiave
        assert fix[0].isupper(), "%s: comincia in minuscolo" % chiave
        assert fix.rstrip().endswith((".", ":")), chiave
        # Nessuna domanda: "verifica che sia voluto" non e' un fix, e'
        # un invito a non fare nulla.
        assert "?" not in fix, "%s: e' una domanda" % chiave


def test_il_catalogo_copre_le_sei_aree_che_lo_usano():
    """Le famiglie a catalogo, dichiarate: se ne nasce un'ottava
    senza testi, qui si vede.

    Erano quattro fino a U13, che ha dato dei controlli — e quindi dei
    testi di correzione — alle due aree di classifica. Sono diventate
    sette con I18: `seo` entra perche' Lighthouse porta la diagnosi e
    non la prescrizione, ed era l'unica area con rilievi di CONTENUTO
    che arrivavano a chi legge senza dirgli che cosa fare.

    Restano fuori `cit` e `llm`, e non prescrivono: la citabilita' e'
    una sintesi di misure altrui — la correzione sta nell'area che ha
    prodotto il numero — e i punti deboli del giudizio LLM sono
    `derived`, con la prosa del modello che gia' e' la prescrizione."""
    aree = {chiave.split(".")[0] for chiave in mars_fixes.CATALOGO}
    assert aree == {"tech", "lex", "sem", "sd", "wcag", "sec", "seo"}
    # Nessuna chiave di stato, nessun derivato: sono le due esenzioni.
    assert not [c for c in mars_fixes.CATALOGO if ".status." in c]
    assert not [c for c in mars_fixes.CATALOGO if c.startswith("cit.")]
    assert not [c for c in mars_fixes.CATALOGO if c.startswith("llm.")]


def test_l_esempio_di_robots_chiude_davvero_il_rilievo():
    """Un esempio e' la forma di ARRIVO: se applicato non chiude il
    rilievo, e' peggio di niente.

    Il caso e' reale e per poco non ci cascavo: l'esempio riusato dal
    progetto di riferimento mostra tre blocchi permissivi, e chi lo
    incollasse IN CODA al proprio robots.txt resterebbe bloccato —
    RobotFileParser tiene il primo gruppo che nomina quell'agente. Ora
    l'esempio mostra la sostituzione, e questo test lo verifica sul
    codice vero."""
    esempio = mars_fixes.CATALOGO["tech.robots.ai_blocked"]["example"]
    contesto = {"url": "https://esempio.test/", "pages": {},
                "robots": {"found": True, "text": esempio}, "sitemap": {}}
    chiavi = [f.key for f in mars_tech.controlla_robots(contesto)]
    assert "tech.robots.ai_blocked" not in chiavi, \
        "l'esempio non chiude il rilievo che dovrebbe correggere"


def test_l_esempio_di_robots_txt_dichiara_la_sitemap():
    """Stessa prova sull'altro esempio di robots: applicarlo deve
    chiudere sia `missing` sia `not_in_robots`."""
    esempio = mars_fixes.CATALOGO["tech.robots.missing"]["example"]
    contesto = {"url": "https://esempio.test/", "pages": {},
                "robots": {"found": True, "text": esempio,
                           "sitemaps": ["https://esempio.it/sitemap.xml"]},
                "sitemap": {"found": True, "urls": 1, "with_lastmod": 1,
                            "unreadable": 0, "from_robots": True}}
    chiavi = [f.key for f in mars_tech.controlla_robots(contesto)
              + mars_tech.controlla_sitemap(contesto)]
    assert "tech.robots.missing" not in chiavi
    assert "tech.sitemap.not_in_robots" not in chiavi


def test_l_esempio_di_jsonld_si_analizza():
    """Un esempio JSON-LD che non si analizzasse sarebbe il difetto che
    pretende di correggere."""
    esempio = mars_fixes.CATALOGO["sd.jsonld.missing"]["example"]
    grezzo = esempio.split(">", 1)[1].rsplit("<", 1)[0]
    html = ('<html><head><script type="application/ld+json">%s</script>'
            "</head><body><h1>x</h1></body></html>" % grezzo)
    esito = mars_schema.audit({"pages": {"https://x/": pagina(html)}})
    assert esito["score"] == 100
    assert not [f for f in esito["findings"]
                if f["key"] != "sd.status.no_pages"]


def test_le_issues_non_dipendono_dal_catalogo(monkeypatch):
    """Le `issues` sono la vista compatta congelata: il catalogo non
    deve poterle toccare.

    Si svuota il catalogo e si RIESEGUONO i moduli — azzerare i
    findings a valle non proverebbe nulla, perche' le issues sono gia'
    state calcolate nella stessa chiamata che li ha prodotti."""
    con = {n: [a["issues"] for a in DATASET[n](monkeypatch)["areas"]]
           for n in DATASET}
    monkeypatch.setattr(mars_fixes, "CATALOGO", {})
    senza = {n: [a["issues"] for a in DATASET[n](monkeypatch)["areas"]]
             for n in DATASET}
    assert con == senza


def test_un_catalogo_illeggibile_non_fa_cadere_l_audit(monkeypatch):
    """Il catalogo e' prosa editoriale, non un pezzo del motore: se
    sparisse, l'audit deve proseguire senza i testi.

    E' la stessa degradazione dichiarata di Lighthouse e ZAP."""
    import sys
    monkeypatch.setitem(sys.modules, "mars_fixes", None)
    esito = mars_core.normalizza_risultato("mars_tech", {
        "score": 50, "issues": ["x"],
        "findings": [{"key": "tech.robots.missing", "fix": "",
                      "example": ""}]})
    assert esito["findings"][0]["fix"] == ""


@pytest.mark.parametrize("res", [
    None, "non un dict", {"score": 1}, {"findings": "non una lista"},
    {"findings": [None, 3, "x"]},
])
def test_la_vestizione_non_cade_su_un_plugin_male_educato(res):
    """`normalizza_risultato` esiste per non far cadere il referto su un
    plugin che sbaglia: la vestizione non deve reintrodurre quel rischio."""
    mars_core.normalizza_risultato("mars_finto", res)


# ----------------------------------------------------------------------
# I18: la correzione anche per l'area SEO
# ----------------------------------------------------------------------

# I dieci controlli MISURATI della categoria SEO di Lighthouse, letti
# dal suo `default-config.js` (13.4.1). L'undicesimo, `structured-data`,
# resta fuori di proposito: pesa 0, Lighthouse non lo valuta — lo
# dichiara «manuale» — e i dati strutturati hanno in MARS un'area
# intera, `sd.*`, che prescrive gia' la sua.
SEO_PRESCRIVIBILI = {
    "seo.lh.is_crawlable", "seo.lh.document_title",
    "seo.lh.meta_description", "seo.lh.http_status_code",
    "seo.lh.link_text", "seo.lh.crawlable_anchors",
    "seo.lh.robots_txt", "seo.lh.image_alt",
    "seo.lh.hreflang", "seo.lh.canonical",
}

# Lo stesso difetto, misurato da due strumenti diversi. Non possono
# costare due sforzi diversi: il piano di interventi sommerebbe due
# stime incoerenti dello stesso lavoro, e chi legge non saprebbe quale
# credere.
GEMELLI = (
    ("seo.lh.image_alt", "wcag.img.alt_missing"),
    ("seo.lh.link_text", "wcag.link.generic"),
    ("seo.lh.canonical", "tech.canonical.missing"),
    ("seo.lh.is_crawlable", "tech.index.noindex"),
)


def test_i_dieci_controlli_seo_misurati_hanno_una_correzione():
    """L'area 2 era l'unica con rilievi di CONTENUTO e nessuna
    prescrizione: portava la `description` di Lighthouse in `detail`,
    cioe' la diagnosi, e nient'altro."""
    a_catalogo = {c for c in mars_fixes.CATALOGO if c.startswith("seo.")}
    assert a_catalogo == SEO_PRESCRIVIBILI


def test_structured_data_resta_senza_correzione():
    """E non e' una dimenticanza: prescrivere due volte la stessa cosa
    da due aree diverse e' peggio che tacere una volta."""
    assert "seo.lh.structured_data" not in mars_fixes.CATALOGO


def test_lo_stesso_difetto_non_costa_due_sforzi_diversi():
    import mars_remediation
    for uno, altro in GEMELLI:
        assert mars_remediation.SFORZO[uno] == mars_remediation.SFORZO[altro], \
            "%s e %s misurano lo stesso difetto" % (uno, altro)


def test_i_rilievi_seo_dei_golden_ricevono_il_fix(monkeypatch):
    """La tubatura, non il solo dato: `vesti()` cerca per chiave, e un
    rilievo che nasce dinamico da Lighthouse deve trovarla lo stesso."""
    visti = {}
    for f in _tutti_i_findings(monkeypatch):
        if f["key"].startswith("seo.lh."):
            visti[f["key"]] = f
    assert visti, "i golden devono produrre rilievi Lighthouse"
    prescritti = 0
    for chiave, f in visti.items():
        atteso = (chiave in SEO_PRESCRIVIBILI
                  and mars_fixes.prescrivibile(f))
        if atteso:
            prescritti += 1
            assert f["fix"], "%s non dice come si corregge" % chiave
            assert f["example"], "%s non mostra la forma di arrivo" % chiave
        else:
            assert not f["fix"], "%s non deve prescrivere" % chiave
    assert prescritti >= 4, "i golden devono esercitare la strada"


@pytest.mark.parametrize("chiave, atteso", [
    ("seo.lh.meta_description", '<meta name="description"'),
    ("seo.lh.canonical", 'rel="canonical"'),
    ("seo.lh.hreflang", 'hreflang="'),
    ("seo.lh.document_title", "<title>"),
    ("seo.lh.image_alt", 'alt="'),
    ("seo.lh.crawlable_anchors", 'href="'),
])
def test_l_esempio_seo_mostra_la_forma_di_arrivo(chiave, atteso):
    """Un esempio che non contenga il tag che il rilievo chiede non e'
    la forma di arrivo: applicato, non chiude nulla."""
    assert atteso in mars_fixes.CATALOGO[chiave]["example"]


def test_l_esempio_di_is_crawlable_copre_tutti_e_tre_i_blocchi():
    """Il blocco all'indicizzazione puo' venire da tre posti diversi, e
    toglierlo da uno solo lo lascia in piedi: un esempio che ne mostri
    uno farebbe credere di aver corretto. E' la stessa trappola di
    `tech.robots.ai_blocked`."""
    esempio = mars_fixes.CATALOGO["seo.lh.is_crawlable"]["example"]
    for dove in ("robots", "X-Robots-Tag", "robots.txt"):
        assert dove in esempio, dove


def test_il_catalogo_non_veste_un_controllo_che_non_e_fallito():
    """Trovato rivedendo il diff dei golden di I18.

    Lighthouse produce un rilievo per OGNI audit, anche per quelli
    superati e per quelli non applicabili — «Non applicabile a questa
    pagina: robots.txt e' valido». Il catalogo cerca per chiave, quindi
    quelle righe ricevevano una prescrizione per un difetto che non
    c'e': «Correggi la sintassi di robots.txt» sotto «robots.txt e'
    valido».

    Il discriminante e' gia' nel dato e non e' la gravita': un rilievo
    `info` puo' essere un difetto vero (`tech.canonical.missing`). E' la
    PENALITA': assente significa che il controllo non e' stato misurato
    o non e' fallito, quindi non c'e' nulla da recuperare e nulla da
    prescrivere.
    """
    passato = {"key": "seo.lh.robots_txt", "fix": "", "example": "",
               "params": {"mode": "notapplicable"}}
    mars_fixes.vesti(passato)
    assert not passato["fix"], "un controllo superato non si corregge"
    assert not passato["example"]


def test_una_penalita_di_zero_si_veste_lo_stesso():
    """Zero non e' assente: nel ramo axe i controlli statici di
    `mars_wcag` hanno penalita' 0.0 — il punteggio lo fa axe — e sono
    difetti veri con una correzione vera. Confondere i due casi
    toglierebbe il fix a meta' dell'area 6."""
    misurato = {"key": "wcag.img.alt_missing", "fix": "", "example": "",
                "params": {"penalty": 0.0}}
    mars_fixes.vesti(misurato)
    assert misurato["fix"]
    assert misurato["example"]


def test_il_modulo_vince_anche_su_un_controllo_non_fallito():
    """La regola non toglie nulla a chi i testi ce li ha gia': il
    catalogo COLMA, e qui non ha nulla da colmare."""
    suo = {"key": "seo.lh.robots_txt", "fix": "Il mio fix.",
           "example": "", "params": {}}
    mars_fixes.vesti(suo)
    assert suo["fix"] == "Il mio fix."
