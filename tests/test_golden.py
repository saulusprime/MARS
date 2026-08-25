#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — la resa del referto, congelata (U2 / Fase 2).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import copy
import difflib
import os
import re
import sys
import types

import pytest

import mars_core
import mars_report
from conftest import pagina
from mars_core import MODULES_REGISTRY, load_external_module
from mars_report import RENDERERS
from test_modules import _lhr

GOLDEN = os.path.join(os.path.dirname(__file__), "golden")

# I due campi che cambiano a ogni esecuzione, iniettati PRIMA di
# rendere invece che sostituiti dopo. La differenza conta: sostituire
# a valle congela il valore ma non il PUNTO in cui compare, quindi
# spostare la data dalla testata al piede — cosa che la Fase 11
# prevede — non produrrebbe alcun diff. E vale per i formati che non
# esistono ancora: `md` e `csv` della Fase 6 nascono deterministici
# senza una regex per formato.
#
# Il valore e' plausibile, non un segnaposto: un renderer futuro che
# formattasse la data cadrebbe su "GENERATED_AT". La versione e'
# 0.0.0 per lo stesso motivo — inconfondibile in un diff, ma ancora
# parsabile da un confronto semver.
GENERATED_AT = "2026-01-01T00:00:00+0000"
VERSIONE = "0.0.0"

# La favicon incorporata e' 3773 caratteri di base64 su una riga sola:
# il 20% del golden HTML, e qualunque diff vicino alla testata
# diventerebbe illeggibile. Si sostituisce col digest, che cambia se
# cambia l'icona e sparisce se l'icona sparisce: il fatto resta
# rilevato, la riga resta leggibile.
_ICONA = re.compile(r"data:image/x-icon;base64,[A-Za-z0-9+/=]+")

# `render_html` e' un "".join(): tutto cio' che segue </style> e' una
# riga sola da 13 KB. Si spezza fra un tag e l'altro PRIMA di scrivere
# il golden, non solo prima di mostrare il diff: il mezzo della
# revisione e' `git diff tests/golden/`, e su una riga da 13 KB la
# revisione non e' possibile — il presidio diventerebbe un rito.
#
# Limite dichiarato: la riformattazione e' leggermente lossy. Un
# a-capo LETTERALE fra due tag diventerebbe invisibile, e il file su
# disco non e' byte per byte cio' che `render_html` emette (in HTML
# quell'a-capo si rende come uno spazio). E' l'unico angolo cieco, e
# non riguarda nulla che il renderer faccia oggi.


def _leggibile(html: str) -> str:
    return re.sub(r"><", ">\n<", html)


# Estensione del file per formato: unica eccezione, "text" -> .txt,
# perche' e' cio' che un umano si aspetta di poter aprire.
ESTENSIONI = {"text": "txt", "markdown": "md"}
# Rese che non portano a-capo propri. Con il default trasparente, i
# formati della Fase 6 entrano nel presidio senza toccare questo file.
LEGGIBILI = {"html": _leggibile}


# ======================================================================
# Il sito sintetico
# ======================================================================
#
# Regola che attraversa tutto il dataset: **dichiara il proprio
# ambiente, non lo eredita**. Su questa macchina Lighthouse, ZAP,
# Playwright e sentence-transformers sono tutti installati; su un
# runner nudo nessuno. Un golden costruito lasciando decidere
# all'ambiente misurerebbe QUALI STRUMENTI MANCANO, non come si rende
# un referto — e la issue "Header non leggibili: NienteRete" ci
# scriverebbe dentro il nome di un attrezzo del banco di prova.

# Un paragrafo lungo: `mars_semantic` conta come "in forma di
# risposta" solo i chunk oltre MIN_PAROLE = 40. Sotto quella soglia
# il rapporto esce 0.0 e il golden congelerebbe un caso degenere.
_LUNGO = ("Il drenaggio linfatico manuale e' una tecnica di massaggio "
          "leggero che segue il decorso dei vasi linfatici e accompagna "
          "il liquido in eccesso verso le stazioni di scarico. Una "
          "seduta dura circa cinquanta minuti e viene concordata con "
          "il terapista dopo una prima valutazione, che considera lo "
          "stato della cute, la presenza di cicatrici e il quadro "
          "clinico complessivo della persona che la richiede.")

HTML_HOME = """<html lang="it"><head><title>Drenaggio linfatico</title>
<meta name="description" content="Sedute, prezzi e percorsi.">
<link rel="canonical" href="https://esempio.test/">
<script type="application/ld+json">{"@context":"https://schema.org",
"@type":"FAQPage","name":"Domande frequenti"}</script>
</head><body>
<h1>Drenaggio linfatico manuale</h1>
<h2>Che cos'e' il drenaggio linfatico?</h2>
<p>%s</p>
<h2>Quanto dura una seduta?</h2>
<p>%s</p>
<img src="/a.png" alt="Sala trattamenti">
<img src="/b.png">
<a href="/servizi/">clicca qui</a>
<table><tr><td>Seduta</td><td>50 minuti</td></tr></table>
<form><input type="text" name="nome"></form>
</body></html>""" % (_LUNGO, _LUNGO)

# Seconda pagina: JSON-LD rotto, cosi' mars_schema ha da dire qualcosa.
HTML_SERVIZI = """<html lang="it"><head><title>Servizi</title>
<script type="application/ld+json">{"@type": "Service",}</script>
</head><body>
<h1>I nostri servizi</h1>
<h3>Percorsi post-operatori</h3>
<p>%s</p>
</body></html>""" % _LUNGO

# Terza pagina: sana e senza nulla da segnalare. Serve ad accendere
# il ramo "Nessun rilievo." della scheda d'area, che altrimenti
# resterebbe scoperto.
HTML_FAQ = """<html lang="it"><head><title>Domande frequenti</title>
<script type="application/ld+json">{"@context":"https://schema.org",
"@type":"FAQPage"}</script></head><body>
<h1>Domande frequenti</h1>
<h2>Serve la prescrizione medica?</h2>
<p>%s</p>
</body></html>""" % _LUNGO

BASE = "https://esempio.test/"


def _pagine() -> dict:
    return {
        BASE: pagina(HTML_HOME, BASE),
        BASE + "servizi/": pagina(HTML_SERVIZI, BASE + "servizi/"),
        BASE + "faq/": pagina(HTML_FAQ, BASE + "faq/"),
    }


def _contesto(**cambi) -> dict:
    pagine = _pagine()
    contesto = {
        "url": BASE,
        "pages": pagine,
        "urls": list(pagine),
        "chunks": [c for p in pagine.values() for c in p["chunks"]],
        # Tre query: una lunga 44 caratteri (esercita il troncamento a
        # 34 della riga di testo) e una senza riscontro sul
        # recuperatore lessicale, che accende "nessun riscontro".
        "queries": ["drenaggio linfatico",
                    "quanto costa una seduta di drenaggio linfatico",
                    "parcheggio riservato"],
        "embeddings_model": "none",
        # Il proxy char-TFIDF non chiama sentence-transformers nemmeno
        # se e' installato: il golden non dipende dalle librerie
        # opzionali presenti sulla macchina.
        "force_proxy": True,
        "market": "eu",
        "robots_ignored": False,
        "owner_declaration": False,
        "discovery": "sitemap",
        "llm": "on",
        "credentials": {},
        "delay": 1.0,
        "skipped": ["vietato da robots.txt: https://esempio.test/privato",
                    "altro host: https://altro.test/",
                    "non HTML: https://esempio.test/listino.pdf",
                    "URL non analizzabile: https://esempio.test/[2001"],
        "robots": {"found": True, "sitemaps": [BASE + "sitemap.xml"],
                   "text": "User-agent: *\nAllow: /\n"
                           "User-agent: GPTBot\nDisallow: /"},
        "sitemap": {"found": True, "sources": [BASE + "sitemap.xml"],
                    "from_robots": True, "files_read": 1, "index_files": 0,
                    "urls": 3, "with_lastmod": 1, "unreadable": 0},
        "results": {},
    }
    contesto.update(cambi)
    return contesto


# ======================================================================
# Le uscite degli strumenti esterni, iniettate alla loro cucitura di I/O
# ======================================================================

def _violazioni_axe() -> list:
    return [
        {"id": "image-alt", "impact": "critical",
         "help": "Le immagini devono avere un testo alternativo",
         "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/image-alt",
         "nodes": [{"target": ["img"]}, {"target": ["img:nth-child(2)"]}]},
        {"id": "color-contrast", "impact": "serious",
         "help": "Il contrasto deve essere sufficiente",
         "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/color-contrast",
         "nodes": [{"target": ["a"]}]},
        {"id": "label", "impact": "moderate",
         "help": "I campi di modulo devono avere un'etichetta",
         "nodes": [{"target": ["input"]}]},
    ]


def _alert_zap() -> list:
    # La `description` e' la spiegazione, la `solution` la prescrizione:
    # ZAP le tiene distinte e il rilievo pure (`detail` e `fix`). Il
    # terzo alert e' apposta senza descrizione, cosi' il golden congela
    # anche il gruppo che la eredita dal primo del suo pluginId, e
    # l'ultimo non ne ha affatto: `detail` vuoto e' un esito legittimo.
    return [
        {"pluginId": "40012", "alertRef": "40012",
         "alert": "Cross Site Scripting (Reflected)", "risk": "High",
         "url": BASE + "servizi/",
         "description": "Il valore inviato viene restituito nella pagina "
                        "senza codifica: un attaccante puo' farvi eseguire "
                        "script arbitrario nel browser della vittima.",
         "solution": "Convalida l'input e codifica l'output.",
         "reference": "https://owasp.org/xss\nhttps://cwe.mitre.org/79"},
        {"pluginId": "10038", "alertRef": "10038-1",
         "alert": "Content Security Policy (CSP) Header Not Set",
         "risk": "Medium", "url": BASE,
         "description": "Senza Content-Security-Policy il browser non ha "
                        "modo di sapere quali origini siano legittime.",
         "solution": "Configura il server per impostare l'header CSP."},
        {"pluginId": "10038", "alertRef": "10038-1",
         "alert": "Content Security Policy (CSP) Header Not Set",
         "risk": "Medium", "url": BASE + "faq/"},
        {"pluginId": "10035", "alert": "Strict-Transport-Security non impostato",
         "risk": "Low", "url": BASE},
    ]


def _testi_axe() -> dict:
    """Il locale italiano di axe-core, congelato alle tre regole in gioco.

    Il golden non puo' leggere `node_modules`: la' axe-core c'e' solo
    se qualcuno ha lanciato `npm install`, e il referto direbbe cose
    diverse a seconda della macchina — lo stesso motivo per cui il
    recuperatore vettoriale e' forzato sul proxy e `anthropic` e' uno
    stub. E' la cucitura di I/O di `mars_wcag.testi_axe`, iniettata
    dove gia' si iniettano `run_axe` e `axe_disponibile`.

    I testi sono verbatim da axe-core 4.13.0. `label` resta FUORI di
    proposito: e' il ramo della regola che il locale non conosce, e nel
    referto congelato si vede come `fix` vuoto invece che come niente.
    """
    return {
        "image-alt": "Assicurati che gli elementi <img> abbiano un testo "
                     "alternativo o un ruolo none o presentation",
        "color-contrast": "Assicurati che il contrasto tra i colori in "
                          "primo piano e di sfondo soddisfi le soglie "
                          "minime del rapporto di contrasto WCAG 2 AA",
    }


def _giudizio_llm() -> dict:
    return {"citabilita": 61, "passaggio_migliore": 0,
            "motivazione": "I passaggi rispondono a domande esplicite e si "
                           "reggono fuori dal contesto, ma il listino non e' "
                           "verificabile.",
            "punti_forti": ["Titoli interrogativi con risposta immediata",
                            "Durata e modalita' della seduta dichiarate"],
            "punti_deboli": ["Nessun prezzo verificabile",
                             "Nessuna fonte citata",
                             "Nessuna data di aggiornamento"]}


class _ClientLLM:
    """Il client Anthropic, con la risposta gia' decisa.

    E' la cucitura documentata `context["_anthropic_client"]`, la
    stessa che usano i test del modulo: il giudizio LLM entra nel
    golden passando dal codice di produzione, senza rete e senza spesa.
    """

    def __init__(self, payload):
        import json as _json
        self._testo = _json.dumps(payload)
        self.beta = types.SimpleNamespace(messages=self)

    def create(self, **kw):
        blocco = types.SimpleNamespace(type="text", text=self._testo)
        return types.SimpleNamespace(content=[blocco],
                                     stop_reason="end_turn")


def _anthropic_finto() -> types.ModuleType:
    """`anthropic` come modulo minimo, per non dipendere dall'ambiente.

    `mars_llm_judge.audit` importa anthropic DENTRO il percorso di
    successo e ne usa le eccezioni nelle clausole `except`: senza
    questo stub il golden direbbe cose diverse a seconda che la
    libreria opzionale sia installata. E' lo stesso schema con cui
    conftest.py rende non importabile `playwright.sync_api`: si
    neutralizza la libreria, non il modulo che la usa.
    """
    finto = types.ModuleType("anthropic")

    class AnthropicError(Exception):
        pass

    class APIError(AnthropicError):
        pass

    finto.AnthropicError = AnthropicError
    finto.APIError = APIError
    finto.Anthropic = lambda **kw: (_ for _ in ()).throw(
        AssertionError("il golden non costruisce un client vero"))
    return finto


# ======================================================================
# I due referti
# ======================================================================
#
# Due e non uno: ci sono rami che nessun singolo referto puo'
# contenere insieme — un'area misurata e la stessa area senza
# strumento, il giudizio LLM reso e disattivato, robots rispettato e
# ignorato, la sezione RRF presente e assente. Con un dataset solo
# resterebbero scoperti per costruzione.
#
# I moduli si prendono da `load_external_module` e NON da un `import`:
# il caricatore sostituisce l'oggetto in `sys.modules`, quindi i due
# non sono lo stesso — e una patch applicata all'oggetto importato
# non arriverebbe a quello che gira, lasciando il golden a congelare
# in silenzio il ramo sbagliato.

def _modulo(nome: str):
    return load_external_module(nome)


def _referto_completo(monkeypatch) -> dict:
    """Il sito misurato con ogni strumento a disposizione."""
    contesto = _contesto()
    risultati = {}
    for nome, _ in MODULES_REGISTRY:
        modulo = _modulo(nome)
        contesto["results"] = risultati
        if nome == "mars_seo":
            # `audit()` restituisce `riassumi(...)` verbatim: non c'e'
            # wrapper da congelare, e cosi' non si deve rimettere in
            # piedi `shutil.which`, che una fixture autouse azzera.
            risultati[nome] = modulo.riassumi(_lhr())
            continue
        if nome == "mars_wcag":
            monkeypatch.setattr(modulo, "axe_disponibile", lambda: True)
            monkeypatch.setattr(modulo, "run_axe",
                                lambda urls, delay=0.0: (_violazioni_axe(), 2))
            monkeypatch.setattr(modulo, "testi_axe", _testi_axe)
        if nome == "mars_wapt":
            # La cucitura documentata: il client entra dal context.
            contesto["_zap_client"] = object()
            monkeypatch.setattr(
                modulo, "run_zap",
                lambda url, client=None, active=False:
                (_alert_zap(), True, True))
        if nome == "mars_llm_judge":
            monkeypatch.setitem(sys.modules, "anthropic", _anthropic_finto())
            contesto["_anthropic_client"] = _ClientLLM(_giudizio_llm())
        risultati[nome] = modulo.audit(contesto)
    return mars_report.build_report(risultati, contesto)


def _referto_degradato(monkeypatch) -> dict:
    """Lo stesso sito senza un solo strumento, e con un'area caduta.

    Un fatto solo — mars_semantic che solleva — accende tre rami
    insieme: l'area in `error`, la sezione RRF che sparisce
    (`rrf_aggregate: None`) e il quadrante «In forma di risposta» non
    misurato. E' il ramo che `errore_modulo` serve in produzione.
    """
    contesto = _contesto(market="italia", robots_ignored=True, llm="off",
                         skipped=[])
    risultati = {}
    for nome, _ in MODULES_REGISTRY:
        modulo = _modulo(nome)
        contesto["results"] = risultati
        if nome == "mars_semantic":
            risultati[nome] = mars_core.errore_modulo(
                MemoryError("corpus troppo grande"))
            continue
        if nome == "mars_wapt":
            monkeypatch.setattr(modulo, "connect_zap",
                                lambda credentials=None: None)
            monkeypatch.setattr(
                modulo.requests, "head",
                lambda url, **kw: types.SimpleNamespace(
                    status_code=200,
                    headers={"Strict-Transport-Security": "max-age=31536000"}))
        risultati[nome] = modulo.audit(contesto)
    return mars_report.build_report(risultati, contesto)


DATASET = {"referto": _referto_completo,
           "referto_degradato": _referto_degradato}


def _rendi(nome: str, monkeypatch) -> dict:
    """Le rese di un dataset, coi campi volatili gia' fissati."""
    referto = DATASET[nome](monkeypatch)
    referto["generated_at"] = GENERATED_AT
    referto["version"] = VERSIONE
    return {formato: LEGGIBILI.get(formato, lambda t: t)(
        _ICONA.sub("data:image/x-icon;base64,DIGEST", render(referto)))
        for formato, render in RENDERERS.items()}


# ======================================================================
# I test
# ======================================================================

def _percorso(dataset: str, formato: str) -> str:
    return os.path.join(GOLDEN,
                        "%s.%s" % (dataset, ESTENSIONI.get(formato, formato)))


def _confronta(dataset: str, formato: str, reso: str):
    """Il diff col golden, oppure None. Non asserisce e non scrive."""
    percorso = _percorso(dataset, formato)
    if not os.path.exists(percorso):
        return ("Manca il golden %s.\nRigenerare con:\n"
                "    MARS_RIGENERA_GOLDEN=1 pytest tests/test_golden.py"
                % percorso)
    with open(percorso, encoding="utf-8") as handle:
        atteso = handle.read()
    if reso == atteso:
        return None
    return "\n".join(list(difflib.unified_diff(
        atteso.splitlines(), reso.splitlines(),
        fromfile=os.path.relpath(percorso), tofile="reso",
        lineterm=""))[:80])


@pytest.mark.parametrize("dataset", sorted(DATASET))
@pytest.mark.parametrize("formato", sorted(RENDERERS))
def test_golden(dataset, formato, monkeypatch):
    """La resa del referto, congelata riga per riga.

    Un'asserzione puntuale coglie cio' che qualcuno ha pensato di
    guardare; questo coglie tutto il resto — ed e' l'unica rete che
    regge le otto fasi di lavoro sul renderer che vengono dopo.

    Congela la PIPELINE, non solo i renderer: i risultati d'area
    vengono dai moduli veri, quindi anche un punteggio che cambia fa
    fallire i golden. E' voluto, ed e' il motivo per cui la
    rigenerazione va sempre seguita dalla revisione del diff: e'
    li' che si distingue una resa cambiata da una misura cambiata.
    """
    reso = _rendi(dataset, monkeypatch)[formato]
    percorso = _percorso(dataset, formato)
    if os.environ.get("MARS_RIGENERA_GOLDEN"):
        os.makedirs(GOLDEN, exist_ok=True)
        with open(percorso, "w", encoding="utf-8") as handle:
            handle.write(reso)
        pytest.skip("rigenerato %s: rivedere il diff con "
                    "`git diff tests/golden/` prima del commit"
                    % os.path.relpath(percorso))
    diff = _confronta(dataset, formato, reso)
    if diff:
        # Il diff dentro l'AssertionError e non stampato: in un
        # container con locale C, stampare i caratteri del referto
        # (⚠ · █) solleverebbe UnicodeEncodeError e il fallimento
        # diventerebbe illeggibile.
        raise AssertionError(
            "%s non coincide col golden. Se il cambiamento e' voluto:\n"
            "    MARS_RIGENERA_GOLDEN=1 pytest tests/test_golden.py\n"
            "    git diff tests/golden/\n\n%s" % (formato, diff))


def test_le_rese_sono_deterministiche_nello_stesso_processo(monkeypatch):
    """Due costruzioni e due rese devono coincidere.

    Un golden che dipendesse dall'ordine di un set o di un dict
    fallirebbe a intermittenza, e verrebbe rigenerato invece che
    capito."""
    for dataset in DATASET:
        prima = _rendi(dataset, monkeypatch)
        seconda = _rendi(dataset, monkeypatch)
        assert prima == seconda, dataset


def test_le_viste_non_modificano_il_referto(monkeypatch):
    """Rendere e' una lettura.

    Un renderer che mutasse il dato canonico farebbe divergere il JSON
    dall'HTML a seconda dell'ordine in cui sono stati prodotti, e il
    golden lo direbbe come "a volte fallisce"."""
    referto = DATASET["referto"](monkeypatch)
    prima = copy.deepcopy(referto)
    for render in RENDERERS.values():
        render(referto)
    assert referto == prima


def test_le_rese_non_contengono_campi_volatili(monkeypatch):
    """La rete sotto l'iniezione.

    Fallirebbe in silenzio se un renderer futuro leggesse
    `mars_core.__version__` invece di `referto["version"]`: il golden
    diventerebbe rosso a ogni bump di versione, e verrebbe rigenerato
    senza capire perche'."""
    iso = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    for dataset in DATASET:
        for formato, reso in _rendi(dataset, monkeypatch).items():
            dove = "%s/%s" % (dataset, formato)
            assert mars_core.__version__ not in reso, dove
            assert set(iso.findall(reso)) <= {GENERATED_AT[:19]}, dove
            assert os.path.dirname(os.path.abspath(__file__)) not in reso


def test_i_due_dataset_coprono_il_registro_e_il_vocabolario(monkeypatch):
    """Il golden vale quanto il dataset che congela.

    Un'area nuova nel registro o uno stato nuovo nel vocabolario non
    devono poter entrare senza che qualcuno decida come vanno RESI:
    qui diventano rossi invece che invisibili."""
    aree, stati = set(), set()
    for dataset in DATASET:
        referto = DATASET[dataset](monkeypatch)
        for area in referto["areas"]:
            aree.add(area["module"])
            stati.add(area["status"])
    assert aree == {nome for nome, _ in MODULES_REGISTRY}
    assert stati >= set(mars_report.STATO_LEGGIBILE)


def test_una_modifica_al_css_fa_fallire_il_golden_html(monkeypatch):
    """Il criterio di accettazione della Fase 2, eseguito.

    Un carattere di CSS e' il cambiamento di resa piu' piccolo
    possibile: se passasse inosservato, il golden non sarebbe una
    rete. E il diff deve restare LEGGIBILE — senza la riformattazione
    e il digest della favicon il criterio sarebbe soddisfatto per il
    solo CSS, che porta gli a-capo suoi, mentre il corpo e' una riga
    da 13 KB.

    `monkeypatch` e non una modifica al file: il repo resta pulito
    anche se il test fallisce a meta'."""
    if os.environ.get("MARS_RIGENERA_GOLDEN"):
        pytest.skip("il golden su disco e' appena stato riscritto")
    monkeypatch.setattr(mars_report, "CSS",
                        mars_report.CSS.replace("--ok:#0cce6b",
                                                "--ok:#0cce6c"))
    diff = _confronta("referto", "html", _rendi("referto", monkeypatch)["html"])
    assert diff, "un carattere di CSS e' passato inosservato"
    assert "--ok:#0cce6c" in diff
    assert max(len(r) for r in diff.splitlines()) < 400, "diff illeggibile"
