#!/usr/bin/env python3
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from mars_core import (SEV_INFO, Finding, chiave_esterna,
                       severita_lighthouse)

LIGHTHOUSE_TIMEOUT = 120  # secondi: Lighthouse puo' bloccarsi a lungo
CATEGORIA = "seo"

# Dove cercare Lighthouse oltre al PATH. `package.json` lo dichiara fra
# le dipendenze del progetto, quindi un `npm install` senza `-g` lo
# mette qui e **non** nel PATH: prima di R32 il referto diceva
# «Lighthouse non trovato» a chi aveva appena seguito il package.json
# del progetto. Stessa cucitura con cui `mars_wcag` legge
# `node_modules/axe-core`, e risolta da `__file__` per la stessa
# ragione di R11 — la directory di lavoro non c'entra.
LIGHTHOUSE_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "node_modules", ".bin")

# I titoli li traduce Lighthouse, non noi: `--locale` glieli fa
# restituire gia' nella lingua chiesta, quindi restano allineati allo
# strumento invece di essere una nostra traduzione destinata a
# invecchiare. Dalla Fase 9 il valore arriva dal `context`: e' la lingua
# dell'audit, non una costante — e Lighthouse ne conosce piu' di quelle
# che MARS serve, quindi non c'e' nulla da validare qui. Questa resta la
# lingua di ripiego quando il contesto non la dichiara.
LOCALE = "it"

# Quanti elementi incriminati riportare per audit fallito. Lighthouse
# ne elenca anche decine: bastano i primi per capire dove guardare.
MAX_ELEMENTI = 5

# I modi in cui la VOCE considera un controllo non misurato. E'
# deliberatamente piu' stretta di `LH_MODI_NON_MISURATI` in mars_core,
# che comprende anche "informative" ed "error": allargarla qui
# sposterebbe i conteggi passed/failed/manual, la riga "N superati, M
# falliti" del referto e la ripartizione delle issues — cioe' proprio
# cio' che un adeguamento di forma non deve fare. La gravita' del
# rilievo usa invece la tupla completa, ed e' l'unico punto in cui le
# due viste divergono di proposito. Divergenza registrata in R40.
MODI_NON_MISURATI_VOCE = ("manual", "notApplicable")

# Come si intitola un rilievo che Lighthouse NON ha misurato.
#
# Serve perche' `failureTitle` viene usato solo quando
# `score !== null && score < 0.9` (core/audits/audit.js): un audit non
# misurato porta quindi il titolo del SUCCESSO, e un rilievo intitolato
# "Il documento ha un elemento rel=canonical valido" su una pagina che
# quel canonical non ce l'ha e' una frase falsa. Il prefisso e' anche
# cio' che fa il referto di Lighthouse, che quei controlli li raggruppa
# sotto "Non applicabile" conservandone il titolo.
#
# Le `issues` NON cambiano: la' il testo resta quello di sempre. E'
# l'unico punto in cui il dato nuovo si discosta dalla vista compatta,
# e si discosta perche' quella riga e' nota per falsa.
PREFISSO_NON_MISURATO = {
    "manual": "Da verificare a mano",
    "notApplicable": "Non applicabile a questa pagina",
    "error": "Controllo non eseguito da Lighthouse",
}


# I `description` di Lighthouse sono in Markdown, e l'unica sintassi
# che usano davvero e' il link: `[testo](url)`. Misurato sugli undici
# audit della categoria SEO nel locale italiano di Lighthouse 13.4.1 —
# dieci ne hanno uno, `structured-data` due — piu' i code span fra
# apici inversi, che restano perche' sono leggibili come sono.
#
# L'URL non si butta: e' documentazione dello strumento, e finisce in
# `params["references"]` come i `reference` di ZAP. La forma e' la
# stessa — una lista, non un `Finding.url` — perche' il problema e' lo
# stesso: i link possono essere piu' d'uno, e sceglierne uno vuol dire
# nascondere gli altri.
#
# `[^()\s]+` per l'URL: si ferma alla prima parentesi, quindi un URL
# che ne contenga (Wikipedia) non verrebbe riconosciuto come link e
# resterebbe nel testo com'e'. Preferibile all'alternativa, che e'
# tagliare l'URL a meta' e lasciare ")" appeso nella frase.
_LINK_MARKDOWN = re.compile(r"\[([^\]]*)\]\(([^()\s]+)\)")


def _senza_link_markdown(testo: str) -> Tuple[str, List[str]]:
    """Il testo con i link ridotti alla loro etichetta, piu' gli URL.

    "Assicurati che [l'attributo href](https://x/) rimandi..." diventa
    "Assicurati che l'attributo href rimandi..." e ["https://x/"].
    Si tiene l'etichetta e non la si butta insieme all'URL: in
    `crawlable-anchors` e in `structured-data` il link sta a meta'
    frase, e toglierlo lascerebbe una frase monca.

    Gli URL escono nell'ordine in cui compaiono, duplicati compresi:
    e' il testo dello strumento, non una bibliografia da normalizzare.
    """
    urls = [m.group(2) for m in _LINK_MARKDOWN.finditer(testo)]
    return _LINK_MARKDOWN.sub(lambda m: m.group(1), testo).strip(), urls


def _peso(valore: object) -> float:
    """Il peso di un auditRef, sempre un float, mai un'eccezione.

    Va letto dal LHR e **mai** dal `default-config.js`: Lighthouse
    azzera il peso degli audit non applicabili, informativi e manuali
    prima di scriverlo nel referto (`core/scoring.js`), quindi un
    `is-crawlable` non applicabile pesa 0 nel LHR e 4,04 nella
    configurazione. Una tabella cablata lo farebbe uscire `critical`.

    Zero, non uno, quando il campo manca o non e' un numero: `0.0` e'
    cio' che `severita_lighthouse` legge come "nessuna importanza
    dichiarata" e degrada a `info`, mentre `1.0` inventerebbe
    un'importanza che nessuno ha espresso. E non solleva: `estrai_audit`
    gira dentro il `try` di `audit()`, dove `TypeError` e' catturato, e
    un `weight` malformato farebbe sparire l'intera area con
    "Lighthouse non riuscito" — R22 sotto altra forma.
    """
    try:
        return float(valore)
    except (TypeError, ValueError):
        return 0.0


def _stato(chiave: str, testo: str, dettaglio: str = "",
           **params: object) -> dict:
    """Un fatto sull'ESECUZIONE, non un difetto del sito.

    Sempre `info`: Lighthouse assente dal PATH o andato in timeout non
    si ripara cambiando il sito, e alzarne la gravita' lo farebbe
    risalire sopra ogni rilievo reale nel piano di interventi. E' la
    stessa ragione per cui il referto tiene `info` un'area fallita.
    Nessuna chiave `penalty`: non e' un difetto.
    """
    return Finding(area="mars_seo", severity=SEV_INFO, key=chiave,
                   title=testo, detail=dettaglio,
                   params=dict(params)).as_dict()


def _penalita(voce: dict, totale_pesi: float) -> Optional[float]:
    """Di quanti punti su 100 risalirebbe l'area se il controllo passasse.

    Qui la penalita' non e' una scelta editoriale come nelle altre aree:
    si RICOSTRUISCE dalla formula che Lighthouse usa davvero — la media
    pesata dei punteggi di `core/scoring.js` — che essendo lineare rende
    il contributo di ogni audit esatto, additivo e invertibile. La somma
    dei contributi ricostruisce `100 - score` a meno del solo
    arrotondamento a due decimali che Lighthouse applica al punteggio di
    categoria, cioe' mezzo punto.

    Resta una ricostruzione, non una misura: Lighthouse quel numero non
    lo pubblica. Ma e' esatta dato il LHR, ed e' la prima penalita' del
    progetto a non essere una stima.

    `None` — chiave assente, non zero — quando non e' calcolabile: peso
    nullo (Lighthouse lo azzera per i non misurati), categoria senza
    pesi, o punteggio assente. L'ultimo caso non e' teorico: un
    auditRef il cui `id` non compare fra gli `audits` da' `score: None`
    e non e' ne' superato ne' manuale, quindi `1 - None` solleverebbe
    `TypeError` — che l'except di `audit()` cattura, facendo sparire
    l'intera area.
    """
    if voce["weight"] <= 0 or totale_pesi <= 0:
        return None
    if not isinstance(voce["score"], (int, float)):
        return None
    return voce["weight"] / totale_pesi * 100.0 * (1.0 - voce["score"])


def _rilievo_audit(voce: dict, totale_pesi: float,
                   text_lang: str = LOCALE, url: str = "") -> dict:
    """Un controllo Lighthouse non superato, come rilievo strutturato.

    `source_severity` resta VUOTO, ed e' il caso piu' netto di tutta la
    fase: Lighthouse una scala di gravita' non ce l'ha proprio — ha un
    punteggio, un modo e un peso. La severita' e' una derivazione
    nostra, e `[Lighthouse]` nelle issues e' un'etichetta di STRUMENTO,
    non di gravita': scrivercela dentro metterebbe un nome di strumento
    in un campo di scala, che e' peggio del vuoto perche' sembra pieno.
    Cio' che rende la derivazione verificabile sta nei params, dove
    `score`, `mode`, `lh_weight` e `lh_weight_total` sono i suoi
    ingressi al completo.

    La `description` di Lighthouse diventa `detail` e **non** `fix`.
    Sembra il contrario finche' non la si legge: dei suoi undici audit
    SEO nove spiegano perche' il controllo conta ("I motori di ricerca
    non sono in grado di includere le pagine..."), e solo
    `crawlable-anchors` e `structured-data` prescrivono qualcosa. Un
    testo cosi' dentro `fix` sarebbe il piano della Fase 4 che, alla
    voce "come si aggiusta", spiega il problema — un difetto che si
    legge subito e si corregge tardi, perche' a quel punto sono
    duecento righe di catalogo. Il `fix` dei controlli che Lighthouse
    duplica esiste gia' sotto `tech.*`, dove MARS la stessa cosa la
    misura da se'.
    """
    modo = str(voce["scoreDisplayMode"] or "")
    severita, peso = severita_lighthouse(voce["score"], modo, voce["weight"])
    params: Dict[str, object] = {
        # L'id grezzo, col trattino che chiave_esterna toglie.
        "rule": voce["id"],
        "mode": modo,
        "score": voce["score"],
        # `lh_weight` e non `weight`: `Finding.weight` sta un livello
        # sopra nello stesso oggetto ed e' la scala chiusa 1.0-3.0. E'
        # esattamente la confusione contro cui mette in guardia la
        # docstring di Finding.
        "lh_weight": voce["weight"],
        # Il denominatore viaggia con il rilievo: nella Fase 4 e nel CSV
        # un Finding si legge staccato dal LHR, e tenere il totale
        # altrove sarebbe la solita coppia di implementazioni che
        # divergono in silenzio.
        "lh_weight_total": totale_pesi,
        "items": list(voce["items"]),
        # La lingua in cui LIGHTHOUSE ha scritto questi testi, letta
        # dal LHR e non da cio' che gli abbiamo chiesto: se non
        # conosce la lingua richiesta ripiega sull'inglese e lo scrive
        # in `configSettings.locale`. Serve al referto per dichiarare
        # che cosa non e' nella sua lingua invece di lasciarlo intuire.
        "text_lang": text_lang,
    }
    # La pagina su cui il controllo e' stato misurato. Quest'area ne ha
    # sempre e sola UNA — Lighthouse gira sull'URL di partenza — e la
    # dichiarava solo a livello d'area, in `audited_url`: chi leggeva un
    # rilievo staccato dal referto non sapeva a che pagina si
    # riferisse (R47).
    #
    # E' l'URL che LIGHTHOUSE dichiara di aver misurato, cioe' l'arrivo
    # dopo i redirect, non quello che gli abbiamo chiesto. Puo' quindi
    # non coincidere con nessuna pagina del campione, e allora nessuno
    # lo aggancia: e' preferibile a scrivere l'URL di partenza, che
    # sarebbe una pagina diversa da quella misurata.
    if url:
        params["urls"] = [url]
    dettaglio, riferimenti = _senza_link_markdown(str(voce["description"]))
    if riferimenti:
        params["references"] = riferimenti
    penalita = _penalita(voce, totale_pesi)
    if penalita is not None:
        params["penalty"] = penalita
    prefisso = PREFISSO_NON_MISURATO.get(modo)
    return Finding(
        area="mars_seo", severity=severita, weight=peso,
        key="seo.lh.%s" % chiave_esterna(voce["id"]),
        title=("%s: %s" % (prefisso, voce["title"]) if prefisso
               else voce["title"]),
        detail=dettaglio,
        params=params).as_dict()


def _descrivi_item(item: object) -> str:
    """Un elemento incriminato in forma leggibile.

    Lighthouse li restituisce in forme diverse a seconda dell'audit:
    una sorgente testuale per is-crawlable, un nodo del DOM per
    image-alt. Si prende cio' che identifica l'elemento e si scarta il
    resto (coordinate, percorsi interni), che non aiuta chi legge.
    """
    if not isinstance(item, dict):
        return str(item)
    sorgente = item.get("source")
    if isinstance(sorgente, str):
        return sorgente
    if isinstance(sorgente, dict):
        return str(sorgente.get("url") or sorgente.get("value") or "")
    nodo = item.get("node")
    if isinstance(nodo, dict):
        return str(nodo.get("selector") or nodo.get("snippet") or "")
    for chiave in ("href", "text", "url", "value"):
        if isinstance(item.get(chiave), str):
            return item[chiave]
    return ""


def lingua_lhr(lhr: dict) -> str:
    """La lingua in cui Lighthouse ha scritto i testi di questo LHR.

    Si legge da `configSettings.locale`, cioe' da cio' che Lighthouse
    ha FATTO, non da cio' che gli abbiamo chiesto: davanti a un locale
    che non conosce ripiega sull'inglese, e un referto che dichiarasse
    la lingua richiesta direbbe una cosa non vera.

    Il locale di Lighthouse puo' essere regionale (`en-US`, `pt-BR`):
    si tiene il solo codice di lingua, che e' cio' che il referto
    confronta con la propria.
    """
    impostazioni = lhr.get("configSettings") or {}
    locale = str(impostazioni.get("locale") or LOCALE)
    return locale.split("-")[0].lower()


def estrai_audit(lhr: dict) -> List[Dict[str, object]]:
    """I singoli controlli della categoria SEO, come li elenca Lighthouse.

    Il referto conteneva finora il solo punteggio complessivo: 92/100
    non dice quale controllo sia fallito, mentre e' esattamente quello
    che serve per correggere. Si riportano tutti gli audit della
    categoria — superati, falliti e manuali — perche' un elenco di soli
    fallimenti non permette di sapere che cosa sia stato guardato.

    E' l'UNICO punto di contatto con la forma del LHR: da qui in avanti
    si lavora sulle voci. Per questo la voce porta anche `score`,
    `scoreDisplayMode` e `weight` — i tre valori su cui poggia la
    gravita' di un rilievo, e che prima venivano letti e buttati via.
    Portano i nomi di Lighthouse perche' sono suoi valori verbatim,
    come `id`, `title` e `items`; `passed` e `manual` sono nomi nostri
    perche' sono giudizi nostri.

    Funzione pura: si verifica su un LHR salvato, senza avviare nulla.
    """
    categoria = (lhr.get("categories") or {}).get(CATEGORIA) or {}
    audits = lhr.get("audits") or {}
    esito: List[Dict[str, object]] = []
    for ref in categoria.get("auditRefs") or []:
        voce = audits.get(ref.get("id")) or {}
        punteggio = voce.get("score")
        modo = voce.get("scoreDisplayMode")
        manuale = modo in MODI_NON_MISURATI_VOCE
        dettagli = voce.get("details") or {}
        elementi = [d for d in
                    (_descrivi_item(i) for i in
                     (dettagli.get("items") or [])[:MAX_ELEMENTI]) if d]
        esito.append({
            "id": ref.get("id"),
            "title": voce.get("title") or ref.get("id"),
            # Il titolo di Lighthouse cambia gia' fra superato e
            # fallito ("Il documento ha / non ha un elemento <title>"),
            # quindi non serve aggiungerci nulla.
            # "and not manuale" e' una guardia, non una differenza: che
            # un audit manuale o non applicabile abbia SEMPRE score
            # None non e' un'osservazione empirica ma una garanzia di
            # costruzione — `_normalizeAuditScore` in
            # core/audits/audit.js restituisce null per ogni modo che
            # non sia binary, numeric o metricSavings. Serve a rendere
            # la classificazione inequivocabile — superato, fallito e
            # manuale devono partizionare l'elenco — se un giorno
            # Lighthouse cambiasse forma.
            "passed": bool(punteggio) and not manuale,
            "manual": manuale,
            "items": elementi,
            # I tre campi che prima si perdevano. `score` e
            # `scoreDisplayMode` vengono dall'audit, `weight` dal ref:
            # sono due sorgenti diverse dentro lo stesso LHR, e il ref
            # fino a qui serviva solo a leggere l'id.
            "score": punteggio,
            "scoreDisplayMode": modo,
            "weight": _peso(ref.get("weight")),
            # La `description` spiega PERCHE' il controllo conta.
            # Verbatim e in Markdown: chi ne fa un `detail` la ripulisce.
            "description": voce.get("description") or "",
        })
    return esito


def punteggi_categorie(lhr: dict) -> Dict[str, Optional[float]]:
    """Tutti i punteggi di categoria che Lighthouse ha calcolato.

    Lighthouse gira SEMPRE per intero — `esegui_lighthouse` non passa
    `--only-categories` — quindi performance, accessibilita', best
    practices e agentic browsing sono gia' nel referto che abbiamo
    pagato, e finora venivano buttati via insieme al resto del LHR.

    Servono perche' MARS misura alcune di quelle aree con strumenti e
    SCALE proprie, e un cliente che apra PageSpeed accanto al nostro
    referto vede due numeri diversi sulla stessa cosa. Pubblicarli
    tutt'e due, dichiarando che la nostra scala e' piu' severa, e' il
    principio 5: un punteggio che non si sa da dove venga vale meno di
    due punteggi che si sa perche' differiscono.

    Verbatim, moltiplicati per 100 come fa il referto per il SEO.
    None per una categoria che Lighthouse non ha saputo calcolare: e'
    la stessa distinzione fra "zero" e "non misurato" di tutto il
    progetto.
    """
    esito: Dict[str, Optional[float]] = {}
    for chiave, categoria in (lhr.get("categories") or {}).items():
        punteggio = (categoria or {}).get("score")
        # `round(..., 2)` non e' una ritaratura: Lighthouse arrotonda
        # gia' il punteggio di categoria a due decimali sulla scala
        # 0-1 (`clampTo2Decimals`), quindi su 0-100 il valore esatto e'
        # un intero e le due cifre non possono perdere nulla. Servono a
        # togliere l'artefatto binario — 0.56 * 100 fa
        # 56.00000000000001 — che in un referto consegnato si legge
        # come falsa precisione.
        esito[str(chiave)] = (round(float(punteggio) * 100.0, 2)
                              if isinstance(punteggio, (int, float))
                              else None)
    return esito


def riassumi(lhr: dict) -> dict:
    """Il risultato d'area a partire dal referto Lighthouse.

    Separata da audit() perche' e' la parte che contiene le decisioni,
    e va potuta verificare senza Lighthouse installato.
    """
    punteggio = ((lhr.get("categories") or {}).get(CATEGORIA) or {}).get(
        "score")
    if punteggio is None:
        # Lo schema LHR ammette score null: il run e' riuscito, il JSON
        # e' valido, ma la categoria non e' calcolabile. E' un "non
        # misurato", non un errore di Lighthouse — e dirlo giusto vale
        # piu' che dirlo genericamente (lezione di R6).
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non ha calcolato la categoria SEO "
                           "per questa pagina"],
                "findings": [_stato(
                    "seo.status.not_scored",
                    "Lighthouse non ha calcolato la categoria SEO per "
                    "questa pagina")],
                # Le ALTRE categorie possono esserci lo stesso: il run
                # e' riuscito, e' la sola categoria SEO a non essere
                # calcolabile.
                "lighthouse_scores": punteggi_categorie(lhr)}

    controlli = estrai_audit(lhr)
    falliti = [c for c in controlli if not c["passed"] and not c["manual"]]
    superati = [c for c in controlli if c["passed"]]
    manuali = [c for c in controlli if c["manual"]]

    issues = []
    for c in falliti:
        elementi = c["items"]
        issues.append("[Lighthouse] %s%s"
                      % (c["title"],
                         " (%s)" % ", ".join(elementi) if elementi else ""))
    for c in manuali:
        issues.append("[Lighthouse] da verificare a mano: %s" % c["title"])

    # Il denominatore della penalita': la somma dei pesi che Lighthouse
    # fa entrare nella media, cioe' quelli maggiori di zero
    # (core/scoring.js scarta gli altri prima di mediare).
    totale_pesi = sum(c["weight"] for c in controlli if c["weight"] > 0)
    # Nessun `sorted`: i rilievi escono nello stesso ordine delle issues,
    # dagli stessi due elenchi. Ordinare per penalita' decrescente qui
    # scavalcherebbe i pari-merito — nove degli undici audit pesano
    # uguale — e le due viste racconterebbero lo stesso referto in due
    # ordini diversi. A riordinare sara' il piano di interventi, che ha
    # un criterio suo.
    #
    # I superati NON diventano rilievi: sono gia' elencati per intero in
    # `audits`, che il referto rende, e un sito perfetto mostrerebbe
    # altrimenti nove voci da fare. Il filtro non e' un'ottimizzazione:
    # `severita_lighthouse` decide su modo e peso e NON guarda lo score,
    # quindi un superato a peso 1 uscirebbe `warning`.
    misurata = lhr.get("finalDisplayedUrl") or lhr.get("finalUrl")
    rilievi = [_rilievo_audit(c, totale_pesi, lingua_lhr(lhr),
                              misurata or "")
               for c in falliti + manuali]

    impostazioni = lhr.get("configSettings") or {}
    return {
        "score": punteggio * 100,
        "issues": issues,
        "findings": rilievi,
        "tool": "Lighthouse %s" % (lhr.get("lighthouseVersion") or "?"),
        # Il tipo di dispositivo cambia i risultati e va dichiarato:
        # un referto mobile e uno desktop non sono confrontabili.
        "form_factor": impostazioni.get("formFactor"),
        "audited_url": misurata,
        "audits": controlli,
        # Le altre categorie dello stesso run: non le misura quest'area,
        # ma le ha pagate lei.
        "lighthouse_scores": punteggi_categorie(lhr),
        "passed": len(superati),
        "failed": len(falliti),
        "manual": len(manuali),
    }


def esegui_lighthouse(url: str, lighthouse: str,
                      locale: str = LOCALE) -> Optional[dict]:
    """L'unica parte con I/O. None se non e' stato possibile misurare.

    L'URL arriva dall'utente (via CLI o dal corpo di una richiesta API):
    va passato come argomento di una lista con shell=False, MAI
    interpolato in una stringa di shell. Con shell=True un URL come
    'https://x/; rm -rf ~ #' verrebbe eseguito dalla shell.
    """
    result = subprocess.run(
        [lighthouse, url, "--output=json", "--quiet",
         "--chrome-flags=--headless", "--locale=%s" % locale],
        capture_output=True, text=True, check=True,
        timeout=LIGHTHOUSE_TIMEOUT,
    )
    return json.loads(result.stdout)


def trova_lighthouse() -> Optional[str]:
    """Il comando Lighthouse: prima il PATH, poi `node_modules/.bin`.

    Il PATH per primo perche' e' la scelta esplicita di chi ha
    installato lo strumento a livello di sistema; `node_modules/.bin`
    come ripiego perche' e' dove finisce un `npm install` dentro il
    repository, che `package.json` invita a fare (R32).

    **Anche il ripiego passa da `shutil.which`**, con `path=`, e non da
    un `os.access` sul percorso composto. Non e' un vezzo: e' l'unico
    modo perche' la neutralizzazione della suite continui a valere. La
    fixture `strumenti_esterni_assenti` sostituisce `shutil.which`, e
    un secondo meccanismo le sfuggirebbe — misurato: con un `os.access`
    la suite ha lanciato Lighthouse per davvero, 263 secondi invece di
    15, e i quattro golden del referto degradato sono diventati rossi
    perche' l'area SEO risultava misurata. Su una macchina senza
    `node_modules` sarebbe stata verde: e' la trappola di
    `node_modules/axe-core` in una forma nuova.

    `which` fa per giunta il lavoro giusto — verifica che sia
    eseguibile, e su Windows conosce le estensioni.

    None quando non c'e' ne' l'uno ne' l'altro. Separata da `audit()`
    per essere verificabile senza far girare l'area.
    """
    return (shutil.which("lighthouse")
            or shutil.which("lighthouse", path=LIGHTHOUSE_BIN))


def audit(context: dict) -> dict:
    """Area 2: SEO via Lighthouse, se disponibile.

    Riporta gli stessi controlli che Lighthouse mostra nella sua
    sezione SEO, non il solo punteggio: e' cio' che permette di sapere
    che cosa correggere invece che soltanto quanto si e' preso.
    """
    lighthouse = trova_lighthouse()
    if not lighthouse:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non trovato nel PATH"],
                "findings": [_stato("seo.status.no_tool",
                                    "Lighthouse non trovato nel PATH",
                                    tool="lighthouse")]}
    try:
        return riassumi(esegui_lighthouse(
            context["url"], lighthouse, context.get("lang") or LOCALE))
    except subprocess.TimeoutExpired:
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse: timeout dopo %ds"
                           % LIGHTHOUSE_TIMEOUT],
                "findings": [_stato("seo.status.timeout",
                                    "Lighthouse: timeout dopo %ds"
                                    % LIGHTHOUSE_TIMEOUT,
                                    timeout=LIGHTHOUSE_TIMEOUT)]}
    except (subprocess.CalledProcessError, json.JSONDecodeError,
            KeyError, TypeError) as exc:
        # Una chiave sola per quattro eccezioni: sono gia' indistinte
        # nella issue, e quattro chiavi per quattro nomi di eccezione
        # Python farebbero della chiave un dettaglio d'implementazione.
        # Quale sia lo dice `detail`.
        return {"score": None, "status": "unavailable",
                "issues": ["Lighthouse non riuscito: %s"
                           % type(exc).__name__],
                "findings": [_stato("seo.status.failed",
                                    "Lighthouse non riuscito",
                                    type(exc).__name__)]}
