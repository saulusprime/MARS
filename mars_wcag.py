#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

# Livello dichiarato: axe-core viene limitato a queste etichette, e
# l'euristica statica controlla criteri dello stesso livello. Dirlo e'
# necessario: "accessibile" senza un livello non significa nulla.
WCAG_LIVELLO = "WCAG 2.1 A + AA"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

AXE_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "node_modules", "axe-core", "axe.min.js")

# Browser lento: si controllano le prime pagine, non tutte. Dichiarato
# nel referto, cosi' nessuno crede che sia stato guardato l'intero sito.
MAX_PAGINE_AXE = 5
TIMEOUT_AXE = 30000  # millisecondi

# Penalita' per gravita' axe. Scelta editoriale, dichiarata come tale.
PESI_AXE = {"critical": 25, "serious": 12, "moderate": 5, "minor": 2}

TESTI_GENERICI = {"clicca qui", "click here", "leggi tutto", "read more",
                  "qui", "here", "link", "continua", "more", "vai"}


# ======================================================================
# Euristica statica: sempre disponibile, nessuna dipendenza
# ======================================================================

def controlli_statici(pages: dict) -> List[str]:
    """Rilievi WCAG ricavabili dal solo markup.

    Non sostituiscono un audit reale: sono criteri verificabili senza
    rendering, quindi niente contrasto colore, focus o ordine di
    lettura. Ognuno cita il criterio a cui si riferisce, perche' un
    rilievo senza riferimento non e' verificabile da chi lo riceve.

    Lavora sui dati che il crawler ha gia' estratto — `images`,
    `heading_levels`, `form_fields`, `tables`, `links`, `tabindex` —
    e non riapre l'HTML: il DOM viene attraversato una volta sola.
    """
    rilievi = []

    senza_lang = [u for u, d in pages.items() if not d.get("lang")]
    if senza_lang:
        rilievi.append("[1.3.1/3.1.1] %d pagine su %d senza attributo "
                       "'lang'" % (len(senza_lang), len(pages)))

    totale_img = mancanti = 0
    for dati in pages.values():
        immagini = dati.get("images") or []
        totale_img += len(immagini)
        # `alt is None` e non `not alt`: l'attributo ASSENTE e'
        # l'unica violazione. `alt=""` e' la marcatura CORRETTA di
        # un'immagine decorativa (tecnica H67), e contarla come
        # difetto penalizzava proprio chi aveva fatto la cosa giusta.
        # Il crawler la distinzione la conserva; era questo filtro a
        # buttarla via.
        mancanti += sum(1 for i in immagini
                        if i.get("alt") is None and not i.get("aria-label"))
    if mancanti:
        rilievi.append("[1.1.1] %d/%d immagini prive di testo alternativo"
                       % (mancanti, totale_img))

    salti = 0
    input_senza_etichetta = 0
    tabelle_senza_th = 0
    link_generici = 0
    tabindex_positivi = 0

    for dati in pages.values():
        # Nessun parse qui: la struttura arriva da estrai_struttura(),
        # che l'ha letta mentre il crawler aveva il DOM aperto. Questo
        # modulo decide cosa sia un difetto, non come si legge l'HTML.
        livelli = dati.get("heading_levels") or []
        for precedente, corrente in zip(livelli, livelli[1:]):
            if corrente > precedente + 1:
                salti += 1

        for campo in dati.get("form_fields") or []:
            # I campi non interattivi non hanno un'etichetta da
            # mostrare: un hidden non si vede, e submit/button/reset
            # prendono il nome dal proprio valore.
            if campo.get("type") in ("hidden", "submit", "button", "reset"):
                continue
            if not campo.get("labelled"):
                input_senza_etichetta += 1

        for tabella in dati.get("tables") or []:
            if tabella.get("role") == "presentation":
                continue
            if not tabella.get("has_th"):
                tabelle_senza_th += 1

        for ancora in dati.get("links") or []:
            testo = (ancora.get("text") or "").lower().strip(" .:>»→")
            if testo in TESTI_GENERICI and not ancora.get("aria-label"):
                link_generici += 1

        for valore in dati.get("tabindex") or []:
            try:
                if int(valore) > 0:
                    tabindex_positivi += 1
            except (TypeError, ValueError):
                pass

    if salti:
        rilievi.append("[1.3.1] %d salti nella gerarchia degli heading "
                       "(es. h2 seguito da h4)" % salti)
    if input_senza_etichetta:
        rilievi.append("[1.3.1/3.3.2] %d campi di modulo senza etichetta"
                       % input_senza_etichetta)
    if tabelle_senza_th:
        rilievi.append("[1.3.1] %d tabelle dati senza intestazioni <th>"
                       % tabelle_senza_th)
    if link_generici:
        rilievi.append("[2.4.4] %d link con testo generico "
                       "(\"clicca qui\", \"leggi tutto\")" % link_generici)
    if tabindex_positivi:
        rilievi.append("[2.4.3] %d elementi con tabindex positivo: "
                       "alterano l'ordine di navigazione" % tabindex_positivi)
    return rilievi


# ======================================================================
# axe-core: audit reale, quando browser e libreria sono disponibili
# ======================================================================

def axe_disponibile() -> bool:
    """Vero se axe-core e Playwright ci sono entrambi."""
    if not os.path.exists(AXE_JS):
        return False
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def score_from_violations(violations: List[dict],
                          pagine_testate: int = 1) -> dict:
    """Punteggio dalle violazioni axe, raggruppate per REGOLA.

    Raggruppare e' necessario: axe restituisce le violazioni pagina per
    pagina, quindi un solo difetto ricorrente su cinque pagine
    arriverebbe cinque volte e affonderebbe il punteggio da solo. Si
    penalizza la regola violata, non quante volte la si incontra.

    La diffusione conta comunque: il peso va da 1x, se la regola tocca
    una pagina sola, a 2x se le tocca tutte.

    Funzione pura: verificabile senza avviare un browser.
    """
    per_regola: Dict[str, dict] = {}
    for violazione in violations:
        chiave = str(violazione.get("id") or "?")
        voce = per_regola.setdefault(chiave, {
            "impact": str(violazione.get("impact") or "minor").lower(),
            "help": violazione.get("help") or chiave,
            "nodes": 0, "pages": 0,
        })
        voce["nodes"] += len(violazione.get("nodes") or []) or 1
        voce["pages"] += 1

    penalita = 0.0
    conteggio: Dict[str, int] = {}
    for voce in per_regola.values():
        diffusione = 1.0 + min(voce["pages"], pagine_testate) / max(
            pagine_testate, 1)
        penalita += PESI_AXE.get(voce["impact"], 2) * diffusione
        conteggio[voce["impact"]] = conteggio.get(voce["impact"], 0) + 1

    ordinate = sorted(per_regola.values(),
                      key=lambda v: -PESI_AXE.get(v["impact"], 2))
    rilievi = ["[axe:%s] %s (%d elementi su %d pagine)"
               % (v["impact"], v["help"], v["nodes"], v["pages"])
               for v in ordinate[:5]]
    return {"score": max(0, round(100 - penalita)),
            "violations_by_impact": conteggio,
            "rules_violated": len(per_regola),
            "issues": rilievi}


def run_axe(urls: List[str],
            delay: float = 0.0) -> Optional[Tuple[List[dict], int]]:
    """Esegue axe-core sulle pagine indicate.

    Si naviga alle pagine reali invece di iniettare l'HTML gia'
    scaricato: senza CSS e JavaScript i criteri su contrasto, focus e
    contenuto generato darebbero risultati sbagliati, che e' peggio che
    non darli.

    Restituisce (violazioni, pagine ANALIZZATE) oppure None. Il
    conteggio non e' un dettaglio: prima i fallimenti per-URL venivano
    inghiottiti senza tenerne traccia, quindi con tutte le pagine
    irraggiungibili la funzione restituiva una lista VUOTA — che
    audit() leggeva come "nessuna violazione" e pubblicava come
    100/100 misurato con axe-core. Zero pagine analizzate non e' un
    sito perfetto: e' una misura che non c'e' stata.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    violazioni: List[dict] = []
    analizzate = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            pagina = browser.new_page()
            for url in urls:
                try:
                    pagina.goto(url, timeout=TIMEOUT_AXE,
                                wait_until="domcontentloaded")
                    pagina.add_script_tag(path=AXE_JS)
                    esito = pagina.evaluate(
                        "async (tags) => (await axe.run(document, "
                        "{runOnly: {type: 'tag', values: tags}})).violations",
                        AXE_TAGS)
                    violazioni.extend(esito or [])
                    analizzate += 1
                except Exception:
                    continue
                if delay:
                    pagina.wait_for_timeout(int(delay * 1000))
            browser.close()
    except Exception:
        return None
    if not analizzate:
        return None
    return violazioni, analizzate


# ======================================================================

def audit(context: dict) -> dict:
    """Area 6: accessibilità, con axe-core quando disponibile.

    Due livelli: axe-core su browser reale se Playwright e la libreria
    ci sono, altrimenti l'euristica statica sul markup. Il referto
    dichiara sempre quale dei due ha prodotto il punteggio e a quale
    livello WCAG si riferisce.
    """
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"]}

    statici = controlli_statici(pages)

    if axe_disponibile():
        urls = list(pages)[:MAX_PAGINE_AXE]
        esito_axe = run_axe(urls, context.get("delay") or 0.0)
        if esito_axe is not None:
            violazioni, analizzate = esito_axe
            # La diffusione si misura sulle pagine ANALIZZATE, non su
            # quelle tentate, altrimenti una regola presente su tutte
            # sembrerebbe presente su meno.
            esito = score_from_violations(violazioni, analizzate)
            rilievi = list(esito["issues"])
            if analizzate < len(urls):
                # Una scansione parziale vale piu' di niente, ma
                # spacciarla per completa no: e' la stessa regola
                # applicata alle scansioni ZAP interrotte (C9).
                rilievi.insert(0, "axe non ha potuto esaminare %d delle %d "
                                  "pagine del campione: i rilievi sono "
                                  "parziali" % (len(urls) - analizzate,
                                                len(urls)))
            return {
                "score": esito["score"],
                "tool": "axe-core",
                "wcag_level": WCAG_LIVELLO,
                # Le pagine davvero esaminate, non quelle tentate.
                "pages_tested": analizzate,
                "pages_attempted": len(urls),
                "pages_total": len(pages),
                "complete": analizzate == len(urls),
                "violations_by_impact": esito["violations_by_impact"],
                "rules_violated": esito["rules_violated"],
                # I rilievi statici restano: coprono l'intero campione,
                # mentre axe ne ha visto solo le prime pagine.
                "issues": rilievi + statici,
                "static_findings": statici,
            }

    # Ripiego dichiarato: senza rendering restano fuori contrasto,
    # focus e ordine di lettura. Non e' un audit di conformita'.
    score = 100 - min(len(statici) * 12, 100)
    return {"score": max(0, score), "status": "surface", "tool": "markup",
            "wcag_level": "%s (parziale: solo criteri statici)" % WCAG_LIVELLO,
            "pages_total": len(pages), "issues": statici,
            "static_findings": statici}
