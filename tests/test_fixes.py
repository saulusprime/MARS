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
    suo = {"key": "tech.robots.missing", "fix": "Il mio fix.",
           "example": ""}
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


def test_il_catalogo_copre_le_quattro_aree_che_lo_usano():
    """Le famiglie a catalogo, dichiarate: se ne nasce una quinta senza
    testi, qui si vede."""
    aree = {chiave.split(".")[0] for chiave in mars_fixes.CATALOGO}
    assert aree == {"tech", "sd", "wcag", "sec"}
    # Nessuna chiave di stato, nessun derivato: sono le due esenzioni.
    assert not [c for c in mars_fixes.CATALOGO if ".status." in c]
    assert not [c for c in mars_fixes.CATALOGO if c.startswith("cit.")]


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
