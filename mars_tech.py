#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set, Tuple
from urllib.robotparser import RobotFileParser

from mars_config import PENALITA, PENALITA_IGNOTA
from mars_core import (USER_AGENT, Finding, norm_host,
                       normalizza_severita)

# Crawler degli assistenti IA e di chi li alimenta. Un sito che li
# esclude non verra' citato: e' il primo fattore di citabilita', prima
# di qualunque considerazione sul contenuto.
CRAWLER_IA = {
    "GPTBot": "OpenAI, addestramento e ricerca di ChatGPT",
    "OAI-SearchBot": "OpenAI, indice di ricerca di ChatGPT",
    "ChatGPT-User": "OpenAI, navigazione su richiesta dell'utente",
    "ClaudeBot": "Anthropic, addestramento",
    "Claude-Web": "Anthropic, navigazione",
    "anthropic-ai": "Anthropic, agente storico",
    "PerplexityBot": "Perplexity",
    "CCBot": "Common Crawl, alimenta molti modelli",
    "Google-Extended": "Google, Gemini e Vertex",
    "Applebot-Extended": "Apple Intelligence",
    "Bytespider": "ByteDance",
    "Amazonbot": "Amazon",
    "meta-externalagent": "Meta",
}

# I nomi di CRAWLER_IA in minuscolo. Le direttive sono insensibili al
# maiuscolo per specifica, quindi il confronto avviene qui e non a
# ogni chiamata.
_CRAWLER_IA_MINUSCOLI = frozenset(n.lower() for n in CRAWLER_IA)

# Direttive che escludono la pagina dagli indici, e direttive che
# impediscono di seguirne i link. `none` sta in entrambe: per Google e
# Bing equivale a `noindex, nofollow`.
#
# `all` — il default esplicito — non compare di proposito: non e' un
# rilievo, e non annulla nulla. Quando le direttive si contraddicono
# (`all, noindex`) vince la piu' restrittiva, ed e' esattamente cio'
# che fa l'intersezione con questi insiemi.
DIRETTIVE_NOINDEX = frozenset({"noindex", "none"})
DIRETTIVE_NOFOLLOW = frozenset({"nofollow", "none"})

# Il divieto di frammento. E' la direttiva che pesa di piu' sull'oggetto
# di questo progetto: la pagina resta regolarmente indicizzata e non
# puo' essere CITATA, perche' nessuna riga del suo testo puo' comparire
# in una risposta. `max-snippet:0` e' `nosnippet` scritto diversamente.
# `max-snippet:-1` e' l'opposto — nessun limite — e non sta qui.
DIRETTIVE_NOSNIPPET = frozenset({"nosnippet", "max-snippet:0"})
# `noarchive` vieta la copia in cache, non il frammento: il testo resta
# citabile, quindi non e' la stessa cosa e non ha la stessa gravita'.
DIRETTIVE_NOARCHIVE = frozenset({"noarchive"})

# Le direttive sono una lista separata da virgole, con spazi liberi.
_SEPARATORI = re.compile(r"[,\s]+")

# Alcune direttive portano un valore dopo i due punti, e lo spazio
# intorno ai due punti e' legale: `max-snippet: 0` si spezzerebbe nei
# due token `max-snippet:` e `0`, che non corrispondono a nulla. Si
# ricuciono per NOME, non su ogni `:`, perche' ricucire tutto
# incollerebbe il prefisso per agente alla sua direttiva
# (`googlebot:noindex`) e nasconderebbe un noindex — l'opposto di cio'
# che serve. Le quattro con valore sono elencate per intero anche se
# oggi il modulo ne giudica due: e' la stessa riga, e ometterle
# lascerebbe il difetto in agguato per la prossima che si aggiunge.
NOMI_CON_VALORE = frozenset({
    "max-snippet", "max-image-preview", "max-video-preview",
    "unavailable_after"})
_DIRETTIVE_CON_VALORE = re.compile(
    r"\b(%s)\s*:\s*" % "|".join(sorted(NOMI_CON_VALORE)))

# La scadenza si legge dal GREZZO, non dai token: il suo valore e' una
# data, e una data puo' contenere spazi e virgole — cioe' esattamente i
# separatori delle direttive. Si cattura tutta la coda e si decide dopo
# dove finisce, in `scadenza_dichiarata()`.
_SCADENZA = re.compile(r"\bunavailable_after\s*:\s*(.*)", re.IGNORECASE)


def _rilievo(gravita: str, testo: str, chiave: str,
             istanze: Optional[Tuple[str, int]] = None,
             **params: object) -> Finding:
    """Un rilievo dell'area, come dato strutturato.

    Imbuto unico del modulo: ogni rilievo passa di qui, quindi e' qui
    che nasce il Finding e non in tredici punti.

    `source_severity` conserva la parola italiana grezza — "critico",
    "grave" — che e' quella che l'utente vede da sempre nelle issues e
    in `findings_by_severity`. La severita' canonica ci sta accanto,
    non al suo posto: le quattro severita' collassano `grave` e
    `medio` entrambe in `warning`, e chi conosce la scala di MARS
    perderebbe l'informazione.

    `params["penalty"]` porta la penalita' EFFETTIVAMENTE applicata al
    punteggio. Non e' `weight`, che vale 2.0/1.0 ed e' importanza
    relativa: senza il numero vero, la Fase 4 non potrebbe calcolare
    quanto risalirebbe il punteggio d'area se il rilievo fosse risolto.

    `istanze` e' una COPPIA `(nome parlante, conteggio)`: il nome
    parlante finisce nei params come sempre — i template di traduzione
    lo usano — e lo stesso numero finisce in `instances`, il nome
    canonico che il piano di interventi legge (R46). Una coppia e non
    due argomenti perche' il numero si scrive UNA volta sola: due
    assegnazioni dello stesso valore, prima o poi, divergono.
    """
    if istanze is not None:
        nome, quante = istanze
        params[nome] = quante
        params["instances"] = quante
    severita, peso = normalizza_severita("mars", gravita)
    return Finding(
        area="mars_tech", severity=severita, weight=peso,
        source_severity=gravita, title=testo, key=chiave,
        params=dict(params, penalty=float(PENALITA.get(gravita, PENALITA_IGNOTA))))


def controlla_robots(context: dict) -> List[Finding]:
    """robots.txt: esistenza e regole per i crawler IA.

    Distingue tre casi che il codice precedente confondeva: nessuna
    regola (i crawler passano, ma per silenzio), permesso esplicito, e
    blocco esplicito. Solo il terzo e' un difetto per la citabilita' —
    ed e' un difetto grave, perche' nessun'altra area puo' compensarlo.
    """
    robots = context.get("robots") or {}
    if not robots.get("found"):
        return [_rilievo("medio", "robots.txt assente: i crawler non "
                                  "hanno indicazioni",
                         "tech.robots.missing")]

    parser = RobotFileParser()
    parser.parse((robots.get("text") or "").splitlines())
    url = context["url"]
    bloccati, citati = [], []
    for agente in CRAWLER_IA:
        if not parser.can_fetch(agente, url):
            bloccati.append(agente)
        if agente.lower() in (robots.get("text") or "").lower():
            citati.append(agente)

    rilievi = []
    if bloccati:
        # L'elenco troncato viaggia nei params accanto a quello intero
        # perche' il titolo e' prosa, e la prosa si traduce: senza,
        # ogni lingua rifarebbe il troncamento per conto suo e due
        # viste dello stesso rilievo elencherebbero un numero diverso
        # di crawler. Vedi mars_i18n.finding_texts().
        elenco = ", ".join(sorted(bloccati)[:5])
        rilievi.append(_rilievo(
            "critico", "robots.txt BLOCCA %d crawler IA: %s"
                       % (len(bloccati), elenco),
            "tech.robots.ai_blocked",
            # L'elenco COMPLETO: la stringa ne mostra cinque ma il
            # conteggio non e' troncato, quindi con sei crawler bloccati
            # il testo dice un numero ed elenca meno. Il dato canonico
            # non tronca — a troncare e' la vista compatta.
            bloccati=sorted(bloccati), istanze=("n", len(bloccati)),
            elenco=elenco))
    if not citati:
        rilievi.append(_rilievo(
            "lieve", "Nessuna regola esplicita per i crawler IA: passano "
                     "per silenzio, non per scelta",
            "tech.robots.ai_unmentioned", controllati=len(CRAWLER_IA)))
    if not parser.can_fetch(USER_AGENT, url):
        rilievi.append(_rilievo("grave", "robots.txt esclude anche questo "
                                         "audit dalla home",
                                "tech.robots.self_blocked",
                                agente=USER_AGENT))
    return rilievi


def controlla_sitemap(context: dict) -> List[Finding]:
    """Sitemap: esistenza, leggibilita', ampiezza, lastmod."""
    info = context.get("sitemap") or {}
    rilievi = []
    if not info.get("found"):
        rilievi.append(_rilievo("grave", "Nessuna sitemap utilizzabile: le "
                                         "pagine sono state trovate seguendo "
                                         "i link",
                                "tech.sitemap.missing"))
        return rilievi
    if not info.get("from_robots"):
        rilievi.append(_rilievo("lieve", "La sitemap non e' dichiarata in "
                                         "robots.txt (trovata su "
                                         "/sitemap.xml)",
                                "tech.sitemap.not_in_robots"))
    if info.get("unreadable"):
        rilievi.append(_rilievo("medio", "%d file di sitemap illeggibili o "
                                         "non validi" % info["unreadable"],
                                "tech.sitemap.unreadable",
                                n=info["unreadable"]))
    urls = info.get("urls") or 0
    if urls and not info.get("with_lastmod"):
        rilievi.append(_rilievo("lieve", "Nessun <lastmod> nella sitemap: i "
                                         "crawler non sanno cosa e' "
                                         "cambiato",
                                "tech.sitemap.no_lastmod", urls=urls))
    return rilievi


def _direttive_grezze(pagina: dict) -> str:
    """Meta `robots`, `X-Robots-Tag` e meta per agente, in una stringa.

    Due funzioni leggono le direttive e devono guardare le **stesse**
    fonti: se un giorno se ne aggiungesse una quarta qui, una sola
    delle due la vedrebbe, e la differenza non produrrebbe alcun
    errore.

    I meta per agente vanno **in coda**, ciascuno col proprio prefisso.
    La posizione non e' un dettaglio: in questa stringa il prefisso
    vale fino al prossimo, quindi un blocco per agente messo in mezzo
    colorerebbe di quell'agente tutto cio' che lo segue. In coda ogni
    blocco apre col proprio nome e nessuno eredita.
    """
    pezzi = [pagina.get("meta_robots") or "",
             pagina.get("x_robots_tag") or ""]
    pezzi += ["%s: %s" % (agente, contenuto) for agente, contenuto
              in sorted((pagina.get("meta_robots_by_agent") or {}).items())]
    return ",".join(pezzi)


def direttive_robots(pagina: dict) -> Set[str]:
    """Direttive robots di una pagina — meta e header insieme, come token.

    Il meta `robots` e l'header `X-Robots-Tag` condividono la stessa
    grammatica, quindi si leggono insieme. Si tokenizza invece di
    cercare sottostringhe perche' cosi' l'elenco delle direttive
    riconosciute e' esplicito ed elencabile: `none` significa
    `noindex, nofollow` senza contenere "noindex", e cercare quella
    sottostringa bastava a mancare un sito interamente de-indicizzato.

    Le direttive con valore (`max-snippet: 0`) arrivano come UN token,
    valore compreso: vedi `_DIRETTIVE_CON_VALORE`.

    Dal 2026-08-26 (R37) questa e' la vista **efficace per gli
    assistenti**: le direttive senza prefisso piu' quelle mirate a un
    crawler di `CRAWLER_IA`. Una direttiva riservata a `googlebot` non
    compare qui — non toglie il sito agli assistenti — e viene
    riportata a parte da `controlla_indicizzabilita`. Fino a R37 il
    prefisso restava fra i token e la direttiva era contata come se
    valesse per tutti: e' il difetto che quella voce ha chiuso, e la
    riga che lo descriveva e' uscita di qui con esso.
    """
    return direttive_efficaci(*direttive_per_agente(pagina))


def _iso(valore: str) -> datetime:
    """`datetime.fromisoformat` con la Zulu minuscola ammessa.

    Il crawler abbassa `meta_robots` e `x_robots_tag` con `.lower()`
    (`mars_core`), quindi qui una `Z` maiuscola non arriva **mai** — e
    `fromisoformat` rifiuta la minuscola con `ValueError`. Il risultato
    era che l'unica forma che il crawler consegna davvero,
    `2020-09-21t12:00:00z`, non si leggeva: il difetto e' stato
    scoperto correggendo un test di R36 che esercitava la maiuscola,
    cioe' un percorso gia' chiuso un livello piu' su.
    """
    if valore.endswith("z"):
        valore = valore[:-1] + "Z"
    return datetime.fromisoformat(valore)


def _agente_del_pezzo(pezzo: str) -> Tuple[Optional[str], str]:
    """Il prefisso per agente di un pezzo, e cio' che ne resta.

    Un agente e' un token **senza spazi** seguito dai due punti. Il
    vincolo non e' cosmetico: un'ora contiene i due punti e una data
    RFC 850 le virgole, quindi
    `unavailable_after: saturday, 21-sep-2020 12:00:00 gmt` si spezza
    in due pezzi e il secondo ha i due punti dell'ora. Senza il
    vincolo, `21-sep-2020 12` diventava un agente e con esso nasceva un
    rilievo `agent_only` inventato — misurato.

    E non e' un agente il nome di una direttiva con valore, o
    `max-snippet: 0` creerebbe l'agente «max-snippet» facendo sparire
    il divieto di frammento (R36).
    """
    testa, separatore, resto = pezzo.partition(":")
    nome = testa.strip()
    if (separatore and nome and " " not in nome
            and nome not in NOMI_CON_VALORE):
        return nome, resto.strip()
    return None, pezzo


def direttive_efficaci(globali: Set[str],
                       per_agente: Dict[str, Set[str]]) -> Set[str]:
    """Le direttive che valgono per gli assistenti IA.

    Le globali piu' quelle mirate a un crawler di `CRAWLER_IA`. Sta in
    una funzione sola perche' la usano sia `direttive_robots` sia
    `controlla_indicizzabilita`: calcolarla due volte significherebbe
    che mutarne una non si vede — misurato, tre mutazioni di R37
    passavano inosservate finche' la regola era scritta in due punti.
    """
    efficaci = set(globali)
    for agente, direttive in per_agente.items():
        if agente in _CRAWLER_IA_MINUSCOLI:
            efficaci |= direttive
    return efficaci


def direttive_per_agente(pagina: dict) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """Le direttive che valgono per tutti, e quelle ristrette a un agente.

    `X-Robots-Tag` ammette un prefisso che limita la direttiva a un solo
    crawler (`X-Robots-Tag: googlebot: noindex`), e i tre casi sono
    diversi: escludere tutti, escludere il solo Google, escludere
    proprio i crawler degli assistenti. Prima ricevevano lo stesso
    giudizio (R37).

    Il prefisso si legge per POSIZIONE, non per token: piu' header
    `X-Robots-Tag` arrivano uniti da una virgola sola — e' `requests`
    che li concatena — quindi un prefisso vale fino al prossimo che
    compare. E' il caso documentato da Google:

        X-Robots-Tag: googlebot: nofollow
        X-Robots-Tag: otherbot: noindex, nofollow

    Un pezzo con i due punti NON e' un prefisso se cio' che sta a
    sinistra e' il nome di una direttiva con valore: `max-snippet: 0`
    creerebbe altrimenti l'agente «max-snippet» e farebbe sparire il
    divieto di frammento senza un errore.

    Il meta `robots` non ha prefisso e finisce tutto fra le globali. Il
    `<meta name="googlebot">` e' l'equivalente nel DOM, e dal 2026-08-26
    (R51) arriva separato: il crawler lo pubblica in
    `meta_robots_by_agent`, e qui vale come il prefisso dell'header.
    Non passa pero' dallo stesso parser posizionale, e non e' una
    scorciatoia: nel DOM ogni meta e' un elemento a se', quindi il suo
    agente e' **noto**, non dedotto dalla posizione. Farlo dedurre da
    una stringa unita rimetterebbe in gioco proprio la confusione che
    la chiave nuova toglie.
    """
    globali = {t for t in _SEPARATORI.split(
        _DIRETTIVE_CON_VALORE.sub(
            r"\1:", (pagina.get("meta_robots") or "").lower())) if t}
    per_agente: Dict[str, Set[str]] = {}

    for agente, contenuto in (pagina.get("meta_robots_by_agent")
                              or {}).items():
        testo = _DIRETTIVE_CON_VALORE.sub(r"\1:", (contenuto or "").lower())
        for token in _SEPARATORI.split(testo):
            if token:
                per_agente.setdefault(agente.lower(), set()).add(token)

    grezzo = _DIRETTIVE_CON_VALORE.sub(
        r"\1:", (pagina.get("x_robots_tag") or "").lower())
    agente = None
    for pezzo in grezzo.split(","):
        pezzo = pezzo.strip()
        if not pezzo:
            continue
        nome, resto = _agente_del_pezzo(pezzo)
        if nome is not None:
            agente = nome
            pezzo = resto
            if not pezzo:
                continue
        for token in _SEPARATORI.split(pezzo):
            if not token:
                continue
            if agente:
                per_agente.setdefault(agente, set()).add(token)
            else:
                globali.add(token)
    return globali, per_agente


def _grezzo_efficace(pagina: dict) -> str:
    """Il testo delle direttive che valgono per gli assistenti.

    Il prefisso per agente vale anche per la SCADENZA, e questa
    funzione e' l'unico modo per farglielo rispettare: la data si legge
    dal grezzo con una regex — perche' puo' contenere spazi e virgole,
    cioe' i separatori delle direttive — e una regex non sa nulla di
    chi sia l'agente corrente.

    Senza, `googlebot: unavailable_after: <passato>` produceva il
    rilievo pieno PIU' `agent_only`, e il punteggio scendeva a 46:
    peggio di una scadenza che vale per tutti, che ne fa 54. Una
    restrizione a un solo agente non puo' pesare di piu' di quella che
    vale per chiunque.
    """
    grezzo = _DIRETTIVE_CON_VALORE.sub(
        r"\1:", _direttive_grezze(pagina).lower())
    agente = None
    tenuti = []
    for pezzo in grezzo.split(","):
        nome, resto = _agente_del_pezzo(pezzo)
        if nome is not None:
            agente, pezzo = nome, resto
        if agente is None or agente in _CRAWLER_IA_MINUSCOLI:
            tenuti.append(pezzo)
    # Si ricompone il TESTO, non i token: una data occupa quattro token
    # e ricostruirla da un insieme ne perderebbe l'ordine. La virgola
    # con lo spazio e' quella che il grezzo aveva.
    return ", ".join(p.strip() for p in tenuti if p.strip())


def scadenza_dichiarata(pagina: dict) -> Optional[datetime]:
    """La data di `unavailable_after`, o `None` se assente o illeggibile.

    Google ne documenta due formati, e vanno letti entrambi: ISO 8601
    (`2020-09-21`) e RFC 850 (`Saturday, 21-Sep-2020 12:00:00 GMT`).
    Il secondo contiene una virgola, che e' anche il separatore delle
    direttive: tagliare sempre alla prima virgola lascerebbe
    `Saturday`, e la data non si leggerebbe mai. Quindi si prova prima
    la coda intera — il caso normale, la direttiva e' l'ultima — e solo
    se non si legge si taglia alla virgola, che e' il caso di una ISO
    seguita da altre direttive.

    Il valore viene dal sito analizzato: e' dato ostile. Una data che
    non si legge restituisce `None` e non produce alcun giudizio —
    dedurne 'scaduta' sarebbe un rilievo critico su una misura che non
    c'e'.

    Una data senza fuso orario e' letta come UTC: la specifica non lo
    dice, ma il confronto deve avvenire fra istanti confrontabili, e
    l'alternativa e' l'ora locale della macchina che esegue l'audit.
    """
    trovato = _SCADENZA.search(_grezzo_efficace(pagina))
    if not trovato:
        return None
    coda = trovato.group(1).strip()
    for candidato in (coda, coda.split(",")[0]):
        for leggi in (_iso, parsedate_to_datetime):
            try:
                quando = leggi(candidato.strip())
            except (TypeError, ValueError):
                continue
            return (quando if quando.tzinfo
                    else quando.replace(tzinfo=timezone.utc))
    return None


def _agenti(agenti_di: Dict[str, Set[str]], categoria: str) -> Dict[str, object]:
    """`agents` solo se la direttiva era riservata a qualcuno.

    La chiave ASSENTE significa «valeva per tutti», che e' il caso
    normale: metterla sempre, vuota, obbligherebbe ogni lettore a
    distinguere la lista vuota dall'assenza.
    """
    chi = agenti_di.get(categoria)
    return {"agents": sorted(chi)} if chi else {}


def controlla_indicizzabilita(context: dict) -> List[Finding]:
    """meta robots, X-Robots-Tag e canonical, pagina per pagina.

    X-Robots-Tag va guardato accanto al meta: agisce allo stesso modo
    ma viaggia negli header, quindi non compare nel DOM ed e' il modo
    piu' facile per escludersi dagli indici senza accorgersene.
    """
    pages = context.get("pages") or {}
    if not pages:
        return []
    noindex, nofollow, senza_canonical, canonical_altrove = [], [], [], []
    nosnippet, noarchive, scadute = [], [], []
    # Un solo istante per tutte le pagine: leggendo l'orologio dentro il
    # ciclo, due pagine con la stessa data ai due lati di un secondo
    # riceverebbero giudizi diversi, e l'audit non sarebbe riproducibile
    # su se stesso.
    adesso = datetime.now(timezone.utc)
    # Chi, per NOME, ha chiesto ciascuna direttiva. Un rilievo aggrega
    # piu' pagine, quindi qui si accumula l'unione: `params["agents"]`
    # dice a quali crawler IA la direttiva era riservata, e la sua
    # assenza dice che valeva per tutti (R37).
    agenti_di: Dict[str, Set[str]] = {}
    # Le direttive riservate a chi NON e' un assistente: non tolgono il
    # sito agli assistenti, ma vanno dette.
    ristrette, agenti_altrui, direttive_altrui = [], set(), set()
    for url, dati in pages.items():
        globali, per_agente = direttive_per_agente(dati)
        direttive = direttive_efficaci(globali, per_agente)
        agenti_ia = sorted(a for a in per_agente
                           if a in _CRAWLER_IA_MINUSCOLI)
        altrui = {a: d for a, d in per_agente.items()
                  if a not in _CRAWLER_IA_MINUSCOLI}
        if altrui:
            ristrette.append(url)
            agenti_altrui |= set(altrui)
            for d in altrui.values():
                direttive_altrui |= d

        def nomina(categoria: str, insieme: frozenset) -> None:
            """Quali crawler IA hanno chiesto questa direttiva per nome."""
            chi = {a for a in agenti_ia if per_agente[a] & insieme}
            if chi:
                agenti_di.setdefault(categoria, set()).update(chi)

        nomina("noindex", DIRETTIVE_NOINDEX)
        nomina("nofollow", DIRETTIVE_NOFOLLOW)
        nomina("nosnippet", DIRETTIVE_NOSNIPPET)
        nomina("noarchive", DIRETTIVE_NOARCHIVE)

        escluso = bool(direttive & DIRETTIVE_NOINDEX)
        if escluso:
            noindex.append(url)
        else:
            # Una data passata e un `noindex` dicono lo stesso fatto:
            # si conta il primo che c'e', non tutti e due.
            scadenza = scadenza_dichiarata(dati)
            if scadenza is not None and scadenza <= adesso:
                scadute.append(url)
                escluso = True
        if direttive & DIRETTIVE_NOFOLLOW:
            nofollow.append(url)
        # Su una pagina gia' fuori dagli indici il divieto di frammento
        # non toglie nulla che non fosse gia' tolto: contarlo anche li'
        # farebbe pagare due volte lo stesso fatto — 80 punti su 100
        # per un difetto solo, e `noindex, nosnippet` e' una scrittura
        # reale, non un caso di laboratorio.
        if not escluso and direttive & DIRETTIVE_NOSNIPPET:
            nosnippet.append(url)
        if direttive & DIRETTIVE_NOARCHIVE:
            noarchive.append(url)
        canonical = (dati.get("canonical") or "").strip()
        if not canonical:
            senza_canonical.append(url)
        elif norm_host(canonical) and norm_host(canonical) != norm_host(url):
            canonical_altrove.append(url)

    rilievi = []
    if noindex:
        gravita = "critico" if len(noindex) == len(pages) else "grave"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine escluse dagli indici (noindex o none, "
                     "in meta robots o X-Robots-Tag)"
                     % (len(noindex), len(pages)),
            "tech.index.noindex",
            istanze=("pagine", len(noindex)), totale=len(pages),
            urls=sorted(noindex),
            **_agenti(agenti_di, "noindex")))
    if scadute:
        # Stesso denominatore del divieto di frammento: le pagine non
        # gia' dichiarate fuori dagli indici per altra via.
        gravita = ("critico" if len(scadute) == len(pages) - len(noindex)
                   else "grave")
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine con unavailable_after gia' passato: "
                     "escluse dagli indici come da un noindex"
                     % (len(scadute), len(pages)),
            "tech.index.unavailable_after",
            istanze=("pagine", len(scadute)), totale=len(pages),
            urls=sorted(scadute)))
    if nosnippet:
        # Il denominatore della gravita' sono le pagine ancora
        # CITABILI, non tutte: se le altre sono gia' escluse dagli
        # indici il sito resta muto lo stesso, e chiamarlo `grave`
        # direbbe che qualcosa si salva. `citabili` non e' mai zero
        # qui, perche' le pagine escluse non entrano in `nosnippet`.
        citabili = len(pages) - len(noindex)
        gravita = "critico" if len(nosnippet) == citabili else "grave"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine indicizzate ma non citabili: nessun "
                     "frammento del loro testo puo' comparire in una "
                     "risposta (nosnippet o max-snippet:0)"
                     % (len(nosnippet), len(pages)),
            "tech.index.nosnippet",
            istanze=("pagine", len(nosnippet)), totale=len(pages),
            urls=sorted(nosnippet),
            **_agenti(agenti_di, "nosnippet")))
    if canonical_altrove:
        rilievi.append(_rilievo(
            "grave", "%d pagine con canonical verso un altro host: il "
                     "contenuto viene attribuito altrove"
                     % len(canonical_altrove),
            "tech.canonical.cross_host",
            istanze=("pagine", len(canonical_altrove)), totale=len(pages),
            urls=sorted(canonical_altrove)))
    if nofollow:
        # Un 'nofollow' non nasconde la pagina: impedisce di raggiungere
        # le altre partendo da li'. Su una pagina sola e' una scelta
        # legittima e frequente; quando e' la regola del sito, la
        # scoperta dipende interamente dalla sitemap. Da qui le due
        # gravita'.
        gravita = "medio" if len(nofollow) == len(pages) else "lieve"
        rilievi.append(_rilievo(
            gravita, "%d/%d pagine non fanno seguire i propri link "
                     "(nofollow o none)" % (len(nofollow), len(pages)),
            "tech.index.nofollow",
            istanze=("pagine", len(nofollow)), totale=len(pages),
            urls=sorted(nofollow),
            **_agenti(agenti_di, "nofollow")))
    if noarchive:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine vietano la copia in cache "
                     "(noarchive): il testo resta citabile, la versione "
                     "archiviata no" % (len(noarchive), len(pages)),
            "tech.index.noarchive",
            istanze=("pagine", len(noarchive)), totale=len(pages),
            urls=sorted(noarchive),
            **_agenti(agenti_di, "noarchive")))
    if ristrette:
        # Medio e non critico: escludersi da Google pesa, ma questo
        # progetto misura la citabilita' IA, e una direttiva mirata a
        # chi non e' un assistente non toglie il sito agli assistenti.
        # E' la scelta che ABBASSA la gravita' di un'esclusione reale
        # da Google, ed e' editoriale: sta scritta anche in `audit`.
        rilievi.append(_rilievo(
            "medio", "%d/%d pagine con direttive riservate a un agente che "
                     "non e' un assistente IA (%s): %s"
                     % (len(ristrette), len(pages),
                        ", ".join(sorted(agenti_altrui)),
                        ", ".join(sorted(direttive_altrui))),
            "tech.index.agent_only",
            istanze=("pagine", len(ristrette)), totale=len(pages),
            urls=sorted(ristrette),
            agents=sorted(agenti_altrui),
            directives=sorted(direttive_altrui)))
    if senza_canonical:
        rilievi.append(_rilievo(
            "lieve", "%d/%d pagine senza <link rel=\"canonical\">"
                     % (len(senza_canonical), len(pages)),
            "tech.canonical.missing",
            istanze=("pagine", len(senza_canonical)), totale=len(pages),
            # L'unico controllo dell'area che sapeva su quali pagine
            # aveva guardato e non lo diceva: gli altri tre dichiarano
            # `urls` da sempre (R47).
            urls=sorted(senza_canonical)))
    return rilievi


def audit(context: dict) -> dict:
    """Area 1: indicizzabilità, robots.txt, sitemap, crawler IA.

    Copre le quattro cose che il nome dell'area promette. Il punteggio
    e' pesato per gravita': un 'noindex' su tutto il sito e un
    <lastmod> mancante non possono valere uguale, come invece
    accadeva con la penalita' fissa di prima.
    """
    rilievi: List[Finding] = []
    rilievi += controlla_robots(context)
    rilievi += controlla_sitemap(context)
    rilievi += controlla_indicizzabilita(context)

    # Punteggio, ordinamento e conteggio restano sulla scala GREZZA,
    # non su quella canonica. Non e' pigrizia: le quattro severita'
    # collassano "grave" e "medio" entrambe in warning, distinte solo
    # da 2.0 contro 1.0 — un rapporto di 2:1 — mentre PESI le tiene a
    # 20:8, cioe' 2.5:1. Ricalcolare da li' cambierebbe i punteggi in
    # silenzio, e con essi mars_citability e l'indice composito.
    penalita = sum(f.params["penalty"] for f in rilievi)
    conteggio: Dict[str, int] = {}
    for f in rilievi:
        conteggio[f.source_severity] = conteggio.get(f.source_severity, 0) + 1

    ordinati = sorted(rilievi, key=lambda f: -f.params["penalty"])
    return {
        # round() e non il solo max(): le penalita' sono float perche'
        # altre aree le scalano per diffusione, e senza arrotondare il
        # punteggio uscirebbe 9.0 dove prima usciva 9. La vista non
        # cambierebbe (stampa %.0f), ma il JSON si', e sarebbe un
        # cambio di contratto silenzioso — per giunta invisibile ai
        # test, perche' 9 == 9.0.
        "score": max(0, round(100 - penalita)),
        # La vista compatta di sempre, parola per parola: e' sotto test
        # come sottostringa in una decina di punti, ed e' cio' che
        # l'utente legge da C10 in poi.
        "issues": ["[%s] %s" % (f.source_severity, f.title)
                   for f in ordinati],
        # Il dato canonico. La dataclass NON attraversa il confine dei
        # plugin: as_dict() la serializza (principio 3 di CLAUDE.md).
        "findings": [f.as_dict() for f in ordinati],
        "findings_by_severity": conteggio,
        "ai_crawlers_checked": len(CRAWLER_IA),
    }
