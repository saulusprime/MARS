#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from mars_config import PENALITA_STATICA, PESI_AXE
from mars_core import (SEV_INFO, Finding, chiave_esterna,
                       frammento_identificante, normalizza_severita)

# Quanti frammenti entrano in un esempio. Chi ha venti immagini senza
# alt non le corregge leggendone venti nel referto: da cinque riconosce
# il caso, e il conteggio vero resta in `params["instances"]`.
MAX_FRAMMENTI = 5

# Livello dichiarato: axe-core viene limitato a queste etichette, e
# l'euristica statica controlla criteri dello stesso livello. Dirlo e'
# necessario: "accessibile" senza un livello non significa nulla.
WCAG_LIVELLO = "WCAG 2.1 A + AA"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

AXE_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "node_modules", "axe-core", "axe.min.js")

# I testi delle regole axe vengono da axe stesso, non da `mars_fixes`:
# la regola violata la conosce lui, e le sue sono oltre cento. I file di
# locale viaggiano nello stesso pacchetto npm di axe.min.js, quindi dove
# c'e' l'uno c'e' quasi sempre l'altro.
#
# axe parla **inglese di suo**: `help` e `description` arrivano gia'
# nella risposta di `axe.run`. Un file di locale serve solo per le altre
# lingue, e per l'inglese non esiste affatto — cercarlo e non trovarlo
# non e' un difetto (R44).
AXE_LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "node_modules", "axe-core", "locales")
LINGUA_NATIVA_AXE = "en"


def percorso_locale_axe(lang: str) -> str:
    """Il file di locale di axe per una lingua. Vuoto per l'inglese."""
    if not lang or lang == LINGUA_NATIVA_AXE:
        return ""
    return os.path.join(AXE_LOCALE_DIR, "%s.json" % lang)


# Browser lento: si controllano le prime pagine, non tutte. Dichiarato
# nel referto, cosi' nessuno crede che sia stato guardato l'intero sito.
MAX_PAGINE_AXE = 5
TIMEOUT_AXE = 30000  # millisecondi

TESTI_GENERICI = {"clicca qui", "click here", "leggi tutto", "read more",
                  "qui", "here", "link", "continua", "more", "vai"}

# Gravita' EDITORIALE dei controlli statici, dichiarata qui invece che
# dedotta. axe una scala ce l'ha; questi sette no, e sceglierla e'
# nostro: `critico` va a cio' che blocca uno screen reader — nessuna
# alternativa testuale, nessuna etichetta, nessuna lingua dichiarata —
# mentre un tabindex positivo o una tabella senza <th> rendono la
# navigazione peggiore, non impossibile.
#
# Il criterio WCAG NON e' una gravita': "[1.3.1/3.3.2]" e' il
# riferimento che rende il rilievo verificabile da chi lo riceve, e
# resta nel testo della issue.
STATICI = {
    "wcag.lang.missing": ("critico", "1.3.1/3.1.1"),
    "wcag.img.alt_missing": ("critico", "1.1.1"),
    "wcag.form.label_missing": ("critico", "1.3.1/3.3.2"),
    "wcag.heading.skip": ("medio", "1.3.1"),
    "wcag.table.th_missing": ("medio", "1.3.1"),
    "wcag.tabindex.positive": ("medio", "2.4.3"),
    "wcag.link.generic": ("lieve", "2.4.4"),
}


def _statico(chiave: str, testo: str,
             istanze: Optional[Tuple[str, int]] = None,
             citati: Optional[List[str]] = None,
             quanti_distinti: int = 0,
             **params: object) -> Finding:
    """Un rilievo statico come dato, con il suo criterio WCAG.

    `istanze` e' una COPPIA `(nome parlante, conteggio)`: il nome
    parlante resta nei params, perche' i template di traduzione lo
    usano, e lo stesso numero finisce in `instances`, il nome canonico
    che il piano di interventi legge (R46). Il numero si scrive UNA
    volta sola.
    """
    if istanze is not None:
        nome, quante = istanze
        params[nome] = quante
        params["instances"] = quante
    gravita, criterio = STATICI[chiave]
    severita, peso = normalizza_severita("mars", gravita)
    if citati:
        # Gli elementi del sito, accanto all'esempio del catalogo e non
        # al posto suo (I20).
        params["cited"] = list(citati)
        if quanti_distinti and quanti_distinti > len(citati):
            # Il tetto non deve essere muto: chi legge cinque nomi su
            # venti crederebbe che siano cinque.
            params["cited_total"] = quanti_distinti
    return Finding(area="mars_wcag", severity=severita, weight=peso,
                   title=testo, key=chiave,
                   # source_severity resta vuoto: axe non ha parlato,
                   # la gravita' l'abbiamo scelta noi.
                   params=dict(params, criterio=criterio, penalty=0.0))


def _issue_statica(f: Finding) -> str:
    """La riga di sempre: "[criterio] testo"."""
    return "[%s] %s" % (f.params["criterio"], f.title)


# ======================================================================
# Euristica statica: sempre disponibile, nessuna dipendenza
# ======================================================================

def controlli_statici(pages: dict) -> List[Finding]:
    """Rilievi WCAG ricavabili dal solo markup.

    Non sostituiscono un audit reale: sono criteri verificabili senza
    rendering, quindi niente contrasto colore, focus o ordine di
    lettura. Ognuno cita il criterio a cui si riferisce, perche' un
    rilievo senza riferimento non e' verificabile da chi lo riceve.

    Lavora sui dati che il crawler ha gia' estratto — `images`,
    `heading_levels`, `form_fields`, `tables`, `links`, `tabindex` —
    e non riapre l'HTML: il DOM viene attraversato una volta sola.

    Ogni rilievo dichiara in `params["urls"]` le pagine su cui e'
    scattato. Il rilievo resta **uno per controllo**, come in tutta
    MARS — spezzarlo per pagina moltiplicherebbe la penalita' — quindi
    il conteggio e le pagine rispondono a due domande diverse e
    convivono (R47).
    """
    rilievi = []
    # Chiave del controllo -> pagine su cui e' scattato, nell'ordine
    # del campione. Il contatore dice QUANTO, questo dice DOVE: sono
    # due domande diverse, e finora il modulo rispondeva solo alla
    # prima (R47). Non e' un set, perche' due esecuzioni sullo stesso
    # sito devono dare lo stesso referto.
    dove: Dict[str, List[str]] = {}

    # Chiave del controllo -> come si chiamano gli elementi citati.
    # NON e' markup: qui MARS il markup non ce l'ha, e ricostruirne uno
    # sarebbe mostrare un tag mai esistito sotto una didascalia che dice
    # «dal tuo sito». Si cita cio' che identifica l'elemento — il `src`
    # di un'immagine, il `name` di un campo — che dal sito viene davvero.
    # Il gruppo B ha gia' stabilito che un esempio vero non deve essere
    # markup: l'`evidence` di ZAP non lo e' (I20).
    citati: Dict[str, List[str]] = {}
    # Quanti elementi DISTINTI per controllo, anche oltre il tetto.
    distinti: Dict[str, set] = {}

    def segna(chiave: str, url: str) -> None:
        pagine_del_controllo = dove.setdefault(chiave, [])
        if url not in pagine_del_controllo:
            pagine_del_controllo.append(url)

    def cita(chiave: str, nome: str) -> None:
        """Il nome di un elemento citato, deduplicato e col tetto.

        Vuoto significa «senza identificatore»: un campo senza `name`
        ne' `id`, una tabella senza didascalia. Si tace invece di
        inventargli un nome, e il conteggio resta quello vero.
        """
        nome = (nome or "").strip()
        if not nome:
            return
        distinti.setdefault(chiave, set()).add(nome)
        elenco = citati.setdefault(chiave, [])
        if nome not in elenco and len(elenco) < MAX_FRAMMENTI:
            elenco.append(nome)

    senza_lang = [u for u, d in pages.items() if not d.get("lang")]
    if senza_lang:
        rilievi.append(_statico(
            "wcag.lang.missing",
            "%d pagine su %d senza attributo 'lang'"
            % (len(senza_lang), len(pages)),
            istanze=("pagine", len(senza_lang)), totale=len(pages),
            urls=sorted(senza_lang)))

    totale_img = mancanti = 0
    for url, dati in pages.items():
        immagini = dati.get("images") or []
        totale_img += len(immagini)
        # `alt is None` e non `not alt`: l'attributo ASSENTE e'
        # l'unica violazione. `alt=""` e' la marcatura CORRETTA di
        # un'immagine decorativa (tecnica H67), e contarla come
        # difetto penalizzava proprio chi aveva fatto la cosa giusta.
        # Il crawler la distinzione la conserva; era questo filtro a
        # buttarla via.
        rotte = [i for i in immagini
                 if i.get("alt") is None and not i.get("aria-label")]
        senza_alt = len(rotte)
        mancanti += senza_alt
        if senza_alt:
            segna("wcag.img.alt_missing", url)
            for immagine in rotte:
                cita("wcag.img.alt_missing", immagine.get("src") or "")
    if mancanti:
        rilievi.append(_statico(
            "wcag.img.alt_missing",
            "%d/%d immagini prive di testo alternativo"
            % (mancanti, totale_img),
            istanze=("immagini", mancanti), totale=totale_img,
            citati=citati.get("wcag.img.alt_missing"),
            quanti_distinti=len(distinti.get("wcag.img.alt_missing") or ()),
            urls=dove.get("wcag.img.alt_missing") or []))

    salti = 0
    input_senza_etichetta = 0
    tabelle_senza_th = 0
    link_generici = 0
    tabindex_positivi = 0

    for url, dati in pages.items():
        # Nessun parse qui: la struttura arriva da estrai_struttura(),
        # che l'ha letta mentre il crawler aveva il DOM aperto. Questo
        # modulo decide cosa sia un difetto, non come si legge l'HTML.
        livelli = dati.get("heading_levels") or []
        testi = dati.get("heading_texts") or []
        for i, (precedente, corrente) in enumerate(zip(livelli, livelli[1:])):
            if corrente > precedente + 1:
                salti += 1
                segna("wcag.heading.skip", url)
                # Il salto sta FRA due titoli: citarne uno solo non
                # direbbe dove guardare. Se i testi mancano — una
                # pagina prodotta da un crawler piu' vecchio — si tace.
                if i + 1 < len(testi):
                    cita("wcag.heading.skip",
                         "h%d %s → h%d %s" % (precedente, testi[i],
                                              corrente, testi[i + 1]))

        for campo in dati.get("form_fields") or []:
            # I campi non interattivi non hanno un'etichetta da
            # mostrare: un hidden non si vede, e submit/button/reset
            # prendono il nome dal proprio valore.
            if campo.get("type") in ("hidden", "submit", "button", "reset"):
                continue
            if not campo.get("labelled"):
                input_senza_etichetta += 1
                segna("wcag.form.label_missing", url)
                cita("wcag.form.label_missing", campo.get("name") or "")

        for tabella in dati.get("tables") or []:
            if tabella.get("role") == "presentation":
                continue
            if not tabella.get("has_th"):
                tabelle_senza_th += 1
                segna("wcag.table.th_missing", url)
                cita("wcag.table.th_missing", tabella.get("caption") or "")

        for ancora in dati.get("links") or []:
            testo = (ancora.get("text") or "").lower().strip(" .:>»→")
            if testo in TESTI_GENERICI and not ancora.get("aria-label"):
                link_generici += 1
                segna("wcag.link.generic", url)
                # Il testo da solo e' il difetto, non l'identificativo:
                # «clicca qui» su otto link e' otto volte lo stesso. E'
                # la destinazione a dire di quale si parla.
                cita("wcag.link.generic",
                     "%s → %s" % (ancora.get("text") or "",
                                  ancora.get("href") or ""))

        for valore in dati.get("tabindex") or []:
            try:
                if int(valore) > 0:
                    tabindex_positivi += 1
                    segna("wcag.tabindex.positive", url)
            except (TypeError, ValueError):
                pass

    if salti:
        rilievi.append(_statico(
            "wcag.heading.skip",
            "%d salti nella gerarchia degli heading (es. h2 seguito da h4)"
            % salti, istanze=("salti", salti),
            citati=citati.get("wcag.heading.skip"),
            quanti_distinti=len(distinti.get("wcag.heading.skip") or ()),
            urls=dove.get("wcag.heading.skip") or []))
    if input_senza_etichetta:
        rilievi.append(_statico(
            "wcag.form.label_missing",
            "%d campi di modulo senza etichetta" % input_senza_etichetta,
            istanze=("campi", input_senza_etichetta),
            citati=citati.get("wcag.form.label_missing"),
            quanti_distinti=len(distinti.get("wcag.form.label_missing") or ()),
            urls=dove.get("wcag.form.label_missing") or []))
    if tabelle_senza_th:
        rilievi.append(_statico(
            "wcag.table.th_missing",
            "%d tabelle dati senza intestazioni <th>" % tabelle_senza_th,
            istanze=("tabelle", tabelle_senza_th),
            citati=citati.get("wcag.table.th_missing"),
            quanti_distinti=len(distinti.get("wcag.table.th_missing") or ()),
            urls=dove.get("wcag.table.th_missing") or []))
    if link_generici:
        rilievi.append(_statico(
            "wcag.link.generic",
            "%d link con testo generico (\"clicca qui\", \"leggi tutto\")"
            % link_generici, istanze=("link", link_generici),
            citati=citati.get("wcag.link.generic"),
            quanti_distinti=len(distinti.get("wcag.link.generic") or ()),
            urls=dove.get("wcag.link.generic") or []))
    if tabindex_positivi:
        rilievi.append(_statico(
            "wcag.tabindex.positive",
            "%d elementi con tabindex positivo: alterano l'ordine di "
            "navigazione" % tabindex_positivi,
            istanze=("elementi", tabindex_positivi),
            urls=dove.get("wcag.tabindex.positive") or []))
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


def _leggi_locale_axe(percorso: str) -> Dict[str, Dict[str, str]]:
    """Il file di locale di axe-core come mappa id -> {help, description}.

    **Tutti e due i testi, non piu' la sola `description`** (R44): fino
    a U9.2 il titolo del rilievo era il `help` inglese che axe manda
    nella risposta, e usciva dentro un referto italiano accanto a un
    `fix` che italiano lo era — perche' quello veniva di qui.

    Separata da `testi_axe` per essere verificabile: quella e'
    memoizzata, e una funzione con una cache non si interroga due volte
    su due file diversi. Qui il percorso e' un argomento, quindi il
    file vero e un file che non esiste si provano tutti e due.
    """
    if not percorso:
        return {}
    try:
        with open(percorso, encoding="utf-8") as fh:
            regole = (json.load(fh) or {}).get("rules") or {}
    except (OSError, ValueError):
        # File assente, illeggibile o non JSON: sono lo stesso caso —
        # i testi non ci sono. Quale delle tre non cambia nulla per
        # chi legge il referto.
        return {}
    testi: Dict[str, Dict[str, str]] = {}
    for chiave, voce in regole.items():
        if not isinstance(voce, dict):
            continue
        # Una voce puo' avere l'uno e non l'altro: si tiene cio' che
        # c'e', e chi legge ripiega campo per campo sul testo che axe
        # ha mandato con la violazione.
        campi = {nome: str(voce[nome]).strip()
                 for nome in ("help", "description")
                 if voce.get(nome)}
        if campi:
            testi[str(chiave)] = campi
    return testi


@lru_cache(maxsize=4)
def testi_axe(lang: str = "it") -> Dict[str, Dict[str, str]]:
    """id della regola -> i suoi due testi nella lingua chiesta.

    axe descrive ogni regola due volte: `help` dice che cosa **deve**
    valere ("Le immagini devono avere un testo alternativo"),
    `description` che cosa **fare** perche' valga ("Assicurati che gli
    elementi <img> abbiano un testo alternativo o un ruolo none o
    presentation"). In italiano la seconda e' un imperativo in 100
    delle 103 regole del locale 4.13.0: e' un `fix`, ed e' anche piu'
    specifica del titolo, perche' nomina gli elementi e le vie
    d'uscita che il titolo tace.

    E' la traduzione di Deque, non una nostra: si aggiorna con axe-core
    invece di invecchiare accanto a lui. Il file di locale sta dentro il
    pacchetto npm, quindi non e' una dipendenza in piu'. Per l'inglese
    non c'e' un file e non serve — axe manda i suoi testi nella
    risposta, e sono gia' quelli.

    Il testo lo si legge QUI e non nel browser (axe accetta un
    `axe.configure({locale})`) per due ragioni: cosi'
    `score_from_violations` resta verificabile senza avviare nulla, e
    un locale illeggibile costa i testi e non la misura — dentro la
    pagina farebbe fallire `axe.run` e con lui l'intera area.

    Il dizionario vuoto e' un esito legittimo, e chi lo riceve lo
    dichiara: vedi `wcag.status.no_fixes`.

    Memoizzata perche' il file e' un centinaio di kilobyte e la lettura
    ricadrebbe su ogni gruppo di violazioni, mentre il contenuto non
    cambia dentro un'esecuzione. La cache tiene piu' di una voce perche'
    la lingua e' un argomento: con `maxsize=1` due audit in due lingue
    dentro lo stesso processo — l'API — si sfratterebbero a vicenda.
    """
    return _leggi_locale_axe(percorso_locale_axe(lang))


# Sotto quale chiave `run_axe` scrive la pagina dentro la violazione.
# Il trattino basso segnala che non viene da axe: e' nostra, e sta
# dentro la violazione perche' li' resta agganciata alla sua, mentre
# una lista parallela si disallinea alla prima riga che filtra.
CHIAVE_PAGINA = "_mars_url"


def score_from_violations(violations: List[dict],
                          pagine_testate: int = 1,
                          lang: str = "it") -> dict:
    """Punteggio dalle violazioni axe, raggruppate per REGOLA.

    Raggruppare e' necessario: axe restituisce le violazioni pagina per
    pagina, quindi un solo difetto ricorrente su cinque pagine
    arriverebbe cinque volte e affonderebbe il punteggio da solo. Si
    penalizza la regola violata, non quante volte la si incontra.

    La diffusione conta comunque: il peso va da 1x, se la regola tocca
    una pagina sola, a 2x se le tocca tutte. Su un campione di una
    pagina resta quindi 1x: non c'e' informazione di diffusione, e
    addebitare il massimo era il difetto R64.

    **Quali** pagine, e non solo quante, finiscono in `params["urls"]`:
    le violazioni arrivano gia' etichettate da `run_axe` sotto
    `CHIAVE_PAGINA`. Il contatore `pages` resta quello che decide il
    punteggio; `urls` e' cio' che permette al referto di dire dove
    (R47). Una violazione senza etichetta — un test, un'altra sorgente
    — conta e non aggiunge pagine, che e' il degrado giusto.

    Funzione pura: verificabile senza avviare un browser.
    """
    per_regola: Dict[str, dict] = {}
    for violazione in violations:
        chiave = str(violazione.get("id") or "?")
        # `impact` puo' mancare, e finora veniva appiattito a "minor"
        # senza lasciarne traccia. E' una NOSTRA assunzione, non un
        # giudizio di axe: se ne tiene conto per non attribuirgli piu'
        # tardi un "axe:minor" che non ha mai detto.
        grezzo = violazione.get("impact")
        voce = per_regola.setdefault(chiave, {
            "id": chiave,
            "impact": str(grezzo or "minor").lower(),
            "impact_dichiarato": bool(grezzo),
            # I due testi COME AXE LI HA MANDATI, cioe' in inglese.
            # Sono il ripiego quando il locale non conosce la regola:
            # axe puo' segnalarne di aggiunte a mano con
            # `axe.configure`, e un add-on non sta dentro axe-core.
            "help": violazione.get("help") or chiave,
            "description": violazione.get("description") or "",
            "help_url": violazione.get("helpUrl") or "",
            "nodes": 0, "pages": 0, "urls": [],
            # I frammenti veri, per l'esempio dal sito (I20). Lista e
            # non set: l'ordine e' quello di scansione, e due
            # esecuzioni sullo stesso sito devono dare lo stesso
            # referto — la stessa ragione per cui `urls` e' una lista.
            "frammenti": [],
            # Quanti elementi DISTINTI, anche oltre il tetto: senza,
            # il referto elencherebbe cinque immagini su venti e non
            # direbbe di star troncando (I20). Distinti e non
            # occorrenze — quelle le conta gia' `instances` — perche'
            # e' con questi che si fa la sottrazione.
            "distinti": set(),
        })
        voce["nodes"] += len(violazione.get("nodes") or []) or 1
        for nodo in (violazione.get("nodes") or []):
            # `html` e' il tag come sta nella pagina — lo stesso dato
            # che Lighthouse chiama `node.snippet`, misurato su
            # axe-core 4.13. Deduplicato: lo stesso elemento su tre
            # pagine e' UN frammento, e quante volte ricorra lo dice
            # gia' `instances`.
            testo = frammento_identificante(
                nodo.get("html") if isinstance(nodo, dict) else None)
            if not testo:
                continue
            voce["distinti"].add(testo)
            if (testo not in voce["frammenti"]
                    and len(voce["frammenti"]) < MAX_FRAMMENTI):
                voce["frammenti"].append(testo)
        voce["pages"] += 1
        # Le PAGINE, non solo quante sono: `pages` resta il contatore
        # su cui si calcola la diffusione — e quindi il punteggio —
        # mentre `urls` e' cio' che permette di dire DOVE. Lista e non
        # set: l'ordine di scansione e' quello del campione, e due
        # esecuzioni sullo stesso sito devono dare lo stesso referto.
        pagina = violazione.get(CHIAVE_PAGINA)
        if pagina and pagina not in voce["urls"]:
            voce["urls"].append(str(pagina))

    penalita = 0.0
    conteggio: Dict[str, int] = {}
    rilievi_dato: List[Finding] = []
    for voce in per_regola.values():
        # (viste-1)/(testate-1), non viste/testate: la vecchia forma non
        # dava mai l'1x promesso e su un campione di UNA pagina partiva
        # dal massimo — il peso raddoppiava proprio dove di diffusione
        # non c'e' informazione (R64). Il max al numeratore copre
        # l'input ostile testate=0 con violazioni.
        viste = min(voce["pages"], pagine_testate)
        diffusione = 1.0 + max(viste - 1, 0) / max(pagine_testate - 1, 1)
        costo = PESI_AXE.get(voce["impact"], 2) * diffusione
        penalita += costo
        conteggio[voce["impact"]] = conteggio.get(voce["impact"], 0) + 1
        voce["penalty"] = costo

    testi = testi_axe(lang)
    ordinate = sorted(per_regola.values(),
                      key=lambda v: -PESI_AXE.get(v["impact"], 2))
    for voce in ordinate:
        severita, peso = normalizza_severita("axe", voce["impact"])
        tradotti = testi.get(voce["id"]) or {}
        # Il titolo risolto si conserva sulla voce: lo usa il rilievo e
        # lo usa la riga compatta qui sotto. Ricalcolarlo la' sarebbe la
        # solita coppia di implementazioni che diverge in silenzio — ed
        # era divergente davvero, perche' la riga compatta leggeva
        # `voce["help"]` e restava in inglese mentre il rilievo era
        # tradotto.
        voce["titolo"] = tradotti.get("help") or voce["help"]
        rilievi_dato.append(Finding(
            area="mars_wcag", severity=severita, weight=peso,
            key="wcag.axe.%s" % chiave_esterna(voce["id"]),
            # Il locale se c'e', altrimenti cio' che axe ha mandato.
            # Prima il titolo era SEMPRE l'inglese della risposta, e
            # usciva dentro un referto italiano accanto a un `fix` che
            # italiano lo era: e' il difetto R44.
            title=voce["titolo"],
            fix=tradotti.get("description") or voce["description"],
            # La documentazione della REGOLA, che e' cio' che axe manda
            # in `helpUrl`. Stava in `url`, e quel nome la faceva
            # sembrare la pagina colpita: le pagine sono in
            # `params["urls"]` (R47).
            doc_url=voce["help_url"],
            # Vuoto quando axe NON ha dichiarato l'impact: scrivere
            # "axe:minor" dove axe ha taciuto significherebbe
            # attribuirgli un giudizio che non ha espresso.
            source_severity=("axe:%s" % voce["impact"]
                             if voce["impact_dichiarato"] else ""),
            params={"rule": voce["id"], "nodes": voce["nodes"],
                    # Il conteggio canonico e' quello dei NODI e non
                    # delle pagine: sono gli elementi da correggere, ed
                    # e' la grandezza su cui scala lo sforzo (R46).
                    "instances": voce["nodes"],
                    "pages": voce["pages"], "urls": list(voce["urls"]),
                    "penalty": voce["penalty"],
                    # Gli elementi del sito su cui la regola e'
                    # scattata: accanto all'esempio del catalogo, non
                    # al posto suo (I20).
                    **({"cited": list(voce["frammenti"])}
                       if voce["frammenti"] else {}),
                    # Solo quando serve: uguale alla lista sarebbe
                    # rumore, e il referto lo confronterebbe con se'.
                    **({"cited_total": len(voce["distinti"])}
                       if len(voce["distinti"]) > len(voce["frammenti"])
                       else {}),
                    # Per REGOLA e non per area: un locale copre quasi
                    # tutte le regole ma non quelle aggiunte a mano, e
                    # dire "l'area e' in italiano" con dentro due
                    # regole inglesi sarebbe la mezza verita' che il
                    # referto evita ovunque.
                    "text_lang": (lang if tradotti
                                  else LINGUA_NATIVA_AXE)}))

    # Senza il file di locale i testi axe restano nella lingua di axe,
    # cioe' in inglese dentro un referto che inglese non e'. Non e'
    # piu' un `fix` che manca — quello arriva comunque dalla risposta —
    # ma una LINGUA che manca, ed e' la degradazione non dichiarata che
    # il principio 2 vieta. Si dichiara SOLO quando costa qualcosa:
    # quando ci sono violazioni da vestire e la lingua chiesta non e'
    # quella nativa di axe.
    #
    # Rilievo e non issue, a differenza di `wcag.status.partial`: la
    # riga compatta elenca cio' che non va nel SITO, e una scansione
    # parziale ci sta perche' cambia come si legge il punteggio.
    # Questa no — il punteggio e' lo stesso, cambia solo la lingua.
    stato: List[Finding] = []
    if rilievi_dato and not testi and percorso_locale_axe(lang):
        stato.append(Finding(
            area="mars_wcag", severity=SEV_INFO, key="wcag.status.no_fixes",
            title="Testi axe non tradotti: manca il locale '%s' di "
                  "axe-core" % lang,
            # Il percorso RELATIVO, non quello assoluto: un referto si
            # consegna a un cliente, e la struttura delle directory
            # della macchina che ha fatto girare la scansione non e' un
            # suo problema — la stessa regola per cui `detail` non
            # porta mai il proxy o la chiave di ZAP.
            detail="atteso in node_modules/axe-core/locales/%s.json"
                   % lang,
            params={"regole": len(rilievi_dato), "lang": lang}))

    # La vista compatta ne mostra cinque; il dato li porta tutti.
    rilievi = ["[axe:%s] %s (%d elementi su %d pagine)"
               % (v["impact"], v["titolo"], v["nodes"], v["pages"])
               for v in ordinate[:5]]
    return {"score": max(0, round(100 - penalita)),
            "violations_by_impact": conteggio,
            "rules_violated": len(per_regola),
            "issues": rilievi,
            "findings": [f.as_dict() for f in stato + rilievi_dato]}


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
                    # La PAGINA viaggia con la violazione. axe le
                    # restituisce pagina per pagina, e appiattirle in
                    # una lista sola buttava via l'unica occasione di
                    # sapere dove il difetto stia: dopo il ciclo il
                    # dato non c'e' piu' (R47). `score_from_violations`
                    # legge questa chiave e non la trova quando le
                    # violazioni arrivano da un test o da un'altra
                    # sorgente, che e' un caso legittimo.
                    for violazione in (esito or []):
                        if isinstance(violazione, dict):
                            violazione[CHIAVE_PAGINA] = url
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
# Il numero dell'altro strumento
# ======================================================================

# Quale categoria di Lighthouse misura la stessa cosa di quest'area.
CATEGORIA_LIGHTHOUSE = "accessibility"


def punteggio_riferimento(context: dict) -> Optional[float]:
    """Il punteggio di accessibilita' di Lighthouse, se qualcuno l'ha gia'.

    Non si lancia un secondo Lighthouse: `mars_seo` ne ha gia' eseguito
    uno per intero — Lighthouse calcola tutte le categorie a ogni run —
    e da qui si legge il numero che aveva in mano e buttava via. Il
    modulo gira DOPO mars_seo in MODULES_REGISTRY, ed e' la stessa
    cucitura su cui poggia `mars_citability`.

    None quando Lighthouse non c'e', quando e' fallito, o quando
    quest'area viene invocata da sola (l'endpoint `/audit/wcag`): sono
    tutti casi in cui il secondo numero non esiste, e il referto non
    deve inventarlo.

    **Perche' due numeri e non uno.** Misurano la stessa superficie con
    lo stesso strumento — axe-core — e danno risultati molto diversi,
    perche' le scale sono diverse: Lighthouse fa una media pesata dei
    propri controlli su UNA pagina, MARS sottrae penalita' per gravita'
    e diffusione su un campione. Misurato su un sito vero: 97 contro
    59, con lo stesso identico difetto trovato da entrambi. Un cliente
    che apra PageSpeed accanto al referto vede i due numeri comunque:
    tacerne uno non li rende uguali, li rende inspiegabili.
    """
    seo = ((context.get("results") or {}).get("mars_seo") or {})
    valore = (seo.get("lighthouse_scores") or {}).get(CATEGORIA_LIGHTHOUSE)
    return float(valore) if isinstance(valore, (int, float)) else None


def _riferimento(context: dict) -> Dict[str, object]:
    """Le chiavi del confronto, o un dict vuoto se non c'e' con chi."""
    punteggio = punteggio_riferimento(context)
    if punteggio is None:
        return {}
    return {"reference_score": punteggio, "reference_tool": "Lighthouse"}


# ======================================================================

def audit(context: dict) -> dict:
    """Area 7: accessibilità, con axe-core quando disponibile.

    Due livelli: axe-core su browser reale se Playwright e la libreria
    ci sono, altrimenti l'euristica statica sul markup. Il referto
    dichiara sempre quale dei due ha prodotto il punteggio e a quale
    livello WCAG si riferisce.
    """
    pages = context.get("pages") or {}
    if not pages:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna pagina da analizzare"],
                "findings": [Finding(
                    area="mars_wcag", severity=SEV_INFO,
                    key="wcag.status.no_pages",
                    title="Nessuna pagina da analizzare").as_dict()]}

    statici = controlli_statici(pages)
    testi_statici = [_issue_statica(f) for f in statici]

    if axe_disponibile():
        urls = list(pages)[:MAX_PAGINE_AXE]
        esito_axe = run_axe(urls, context.get("delay") or 0.0)
        if esito_axe is not None:
            violazioni, analizzate = esito_axe
            # La diffusione si misura sulle pagine ANALIZZATE, non su
            # quelle tentate, altrimenti una regola presente su tutte
            # sembrerebbe presente su meno.
            esito = score_from_violations(violazioni, analizzate,
                                          context.get("lang") or "it")
            rilievi = list(esito["issues"])
            # Il rilievo di stato, se la scansione e' stata parziale.
            parziale: List[dict] = []
            if analizzate < len(urls):
                # Una scansione parziale vale piu' di niente, ma
                # spacciarla per completa no: e' la stessa regola
                # applicata alle scansioni ZAP interrotte (C9).
                mancate = len(urls) - analizzate
                rilievi.insert(0, "axe non ha potuto esaminare %d delle %d "
                                  "pagine del campione: i rilievi sono "
                                  "parziali" % (mancate, len(urls)))
                parziale = [Finding(
                    area="mars_wcag", severity=SEV_INFO,
                    key="wcag.status.partial",
                    title="axe non ha esaminato %d delle %d pagine del "
                          "campione" % (mancate, len(urls)),
                    params={"mancate": mancate, "tentate": len(urls),
                            "analizzate": analizzate}).as_dict()]
            return {
                "score": esito["score"],
                **_riferimento(context),
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
                "issues": rilievi + testi_statici,
                # In questo ramo il punteggio viene DA AXE: i controlli
                # statici non lo toccano, quindi la loro penalita' e'
                # zero — ed e' cio' che _statico() gia' dichiara.
                "findings": (parziale + esito["findings"]
                             + [f.as_dict() for f in statici]),
                "static_findings": testi_statici,
            }

    # Ripiego dichiarato: senza rendering restano fuori contrasto,
    # focus e ordine di lettura. Non e' un audit di conformita'.
    score = 100 - min(len(statici) * PENALITA_STATICA, 100)
    # Qui, e SOLO qui, i controlli statici pagano il punteggio. Ogni
    # rilievo porta anche `surface`: senza, un elenco di soli findings
    # (Fase 6) mostrerebbe un `critical` come se venisse da una misura
    # che non c'e' stata.
    for f in statici:
        f.params["penalty"] = float(PENALITA_STATICA)
        f.params["surface"] = True
    return {"score": max(0, score), "status": "surface", "tool": "markup",
            **_riferimento(context),
            "wcag_level": "%s (parziale: solo criteri statici)" % WCAG_LIVELLO,
            "pages_total": len(pages), "issues": testi_statici,
            "findings": [f.as_dict() for f in statici],
            "static_findings": testi_statici}
