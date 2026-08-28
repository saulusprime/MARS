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
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

from mars_core import (SEV_INFO, Finding, describe_chunk,
                       reciprocal_rank_fusion, RRF_K)

MODEL = "claude-opus-5"
MAX_CHUNK = 8          # quanti passaggi sottoporre al modello
MAX_CARATTERI = 1200   # per passaggio
MAX_TOKENS = 4000      # il giudizio e' breve: non serve di piu'
EFFORT = "medium"


class Tema(NamedTuple):
    """Una voce del vocabolario chiuso dei punti deboli (U10.1)."""

    key: str      # la chiave del rilievo che ne nasce
    title: str    # titolo stabile, invariante come la chiave
    source: str   # chiave dell'area che quel difetto lo MISURA, se c'e'
    gloss: str    # come il tema si spiega al modello


# Il vocabolario chiuso dei punti deboli.
# ----------------------------------------------------------------------
# U1.9 lasciava i `punti_deboli` come prosa libera, e la ragione era
# `Finding.key`: una chiave ricavata da prosa sarebbe variabile fra due
# esecuzioni — `thinking: adaptive` — e fra due modelli, cioe' inutile
# esattamente a U7 e U9, che su quella chiave poggiano. Qui il modello
# la chiave non la scrive: la SCEGLIE da questo elenco, che entra nello
# SCHEMA come `enum`. Il vocabolario e' chiuso, quindi la chiave e'
# stabile per costruzione.
#
# I temi sono solo quelli che il modello e' in condizione di osservare:
# `costruisci_prompt` gli consegna l'URL e otto passaggi, non l'HTML,
# non i `<title>`, non le query, non robots.txt. Un tema su cio' che
# non vede sarebbe un'opinione su un dato che non ha.
#
# `source` e' l'indirizzo dell'area che quel difetto lo QUANTIFICA, e
# resta vuoto dove nessuna lo fa: cinque temi su sette non hanno una
# misura dietro, ed e' il motivo per cui il rilievo che ne nasce vale
# `derived` — vedi `_derivato`.
VOCABOLARIO: Dict[str, Tema] = {
    "thin": Tema(
        "llm.content.thin",
        "Passaggi troppo scarni per essere citati",
        "lex.words.thin",
        "il passaggio e' troppo breve o povero: non c'e' abbastanza "
        "sostanza da citare"),
    "not_answer": Tema(
        "llm.content.not_answer",
        "Passaggi che non rispondono a una domanda",
        "sem.answer_shaped.low",
        "il passaggio descrive senza concludere: nessuna domanda vi "
        "trova risposta"),
    "not_standalone": Tema(
        "llm.content.not_standalone",
        "Passaggi che non si reggono fuori dal loro contesto",
        "",
        "il passaggio non si capisce da solo: rimandi, pronomi senza "
        "referente, riferimenti a cio' che sta sopra"),
    "duplicate": Tema(
        "llm.content.duplicate",
        "Passaggi che ripetono lo stesso contenuto",
        "",
        "piu' passaggi dicono la stessa cosa, o pagine diverse portano "
        "lo stesso testo"),
    "boilerplate": Tema(
        "llm.content.boilerplate",
        "Passaggi che sono impalcatura del sito, non contenuto",
        "",
        "il passaggio e' menu, testata, piede, briciole di pane o "
        "modulo di contatto"),
    "promotional": Tema(
        "llm.content.promotional",
        "Passaggi promozionali invece che informativi",
        "",
        "il passaggio vende invece di informare: slogan e superlativi, "
        "nessun fatto"),
    "unverifiable": Tema(
        "llm.content.unverifiable",
        "Affermazioni che nulla rende verificabili",
        "",
        "il passaggio afferma senza dati, fonti, date o numeri: nulla "
        "che un assistente possa riportare come verificabile"),
}

# Il tema di chi non ne ha uno: forzare l'osservazione dentro il tema
# piu' vicino falserebbe il referto, che sui temi conta.
FUORI_VOCABOLARIO = "altro"

# Dove quelle osservazioni finiscono. NON e' nel vocabolario — al
# modello si offre `altro`, non questa chiave — ma un rilievo ce l'ha
# lo stesso, ed e' voluto: la resa Markdown di un'area preferisce i
# rilievi alle `issues`, quindi senza questo la prosa senza tema
# sparirebbe proprio dalla vista che U10.1 doveva raggiungere.
# La chiave resta stabile perche' non viene dalla prosa: e' il secchio,
# e cio' che ci sta dentro cambia a ogni esecuzione — motivo per cui
# anche questo rilievo e' `derived` e non entra nello storico.
TEMA_ALTRO = Tema("llm.content.other",
                  "Altre osservazioni del modello sul contenuto",
                  "", "")

# L'ordine e' quello dell'enum inviato al modello, ed e' ordinato per
# non cambiare da un'esecuzione all'altra: il prompt e' un prefisso di
# cache, e un dict riordinato lo invaliderebbe senza alcun motivo.
TEMI_AMMESSI: Tuple[str, ...] = tuple(sorted(VOCABOLARIO)) + (
    FUORI_VOCABOLARIO,)

# Il modello risponde in JSON validato: cosi' il parsing non dipende da
# come ha deciso di formattare la prosa.
SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "citabilita": {
                "type": "integer",
                "description": "0-100: quanto e' probabile che un "
                               "assistente IA citi questo sito",
            },
            "motivazione": {"type": "string"},
            "punti_forti": {"type": "array", "items": {"type": "string"}},
            "punti_deboli": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tema": {
                            "type": "string",
                            "enum": list(TEMI_AMMESSI),
                            "description": "il tema del punto debole, "
                                           "scelto fra questi",
                        },
                        "testo": {"type": "string"},
                    },
                    "required": ["tema", "testo"],
                    "additionalProperties": False,
                },
            },
            "passaggio_migliore": {
                "type": "integer",
                "description": "indice del passaggio piu' citabile fra "
                               "quelli forniti, a partire da 0",
            },
        },
        "required": ["citabilita", "motivazione", "punti_forti",
                     "punti_deboli", "passaggio_migliore"],
        "additionalProperties": False,
    },
}

ISTRUZIONI = """Sei un valutatore di citabilità per assistenti IA.

Ti vengono forniti i passaggi più recuperabili di un sito, selezionati
da una fusione RRF fra un recuperatore lessicale BM25 e uno vettoriale.
Valuta quanto è probabile che un assistente IA con ricerca web citi
questo sito quando risponde a domande sul suo argomento.

Giudica il CONTENUTO dei passaggi: sono autoconsistenti? Rispondono a
una domanda in modo verificabile? Contengono affermazioni citabili, o
sono materiale promozionale generico? Un passaggio citabile si regge da
solo fuori dal suo contesto.

Non giudicare gli aspetti tecnici (robots.txt, header, dati
strutturati): sono già misurati altrove. Sii severo: la maggior parte
dei siti non è citabile, e un voto alto deve significare qualcosa.

Ogni punto debole porta un `tema` scelto fra questi:

%s

Scegli `%s` quando nessuno dei temi descrive l'osservazione: forzarla
dentro il tema più vicino falserebbe il referto, che sui temi conta.""" \
    % ("\n".join("- %s: %s" % (nome, VOCABOLARIO[nome].gloss)
                 for nome in sorted(VOCABOLARIO)),
       FUORI_VOCABOLARIO)


def _stato(chiave: str, testo: str, dettaglio: str = "",
           **params: object) -> dict:
    """Un fatto sull'ESECUZIONE del giudizio, mai un difetto del sito.

    Meta' dei rilievi di quest'area: `llm.status.*`. L'altra meta' la
    fa `_derivato`, ed e' la meta' che parla del SITO. Le due famiglie
    non si mescolano — `status` dice se il giudizio c'e' stato,
    `content` dice cosa il giudizio ha detto — e chi legge il referto
    distingue le due cose dalla chiave.

    Tutti `info` a peso 1.0: nessuno di questi esiti si ripara cambiando
    il sito — una libreria mancante, una chiave assente, un modello che
    risponde male sono guasti dei nostri strumenti, e alzarne la gravita'
    li farebbe risalire sopra ogni rilievo reale nel piano di interventi.
    Nessuna `penalty`: chiave assente significa "non e' un difetto".
    `source_severity` vuoto: l'API restituisce stati HTTP, che non sono
    una scala di gravita'.

    `attempted` dice se si e' arrivati a chiamare il modello. NON
    significa "speso": un 429 non si paga, e nessun ramo puo' sapere se
    la richiesta e' stata fatturata.
    """
    return Finding(area="mars_llm_judge", severity=SEV_INFO, key=chiave,
                   title=testo, detail=dettaglio,
                   params=dict(params)).as_dict()


def _derivato(tema: Tema, prosa: List[str], model: str) -> dict:
    """Un punto debole del modello, come rilievo.

    **`derived: True` su ogni rilievo di questa famiglia**, ed e' un
    invariante, non un giudizio caso per caso: quello che il modello
    dice e' un'OPINIONE, non una misura. Chi consuma i rilievi per
    sommarli — piano di interventi, conteggi per gravita', confronto fra
    due esecuzioni — deve saltarla, e la salta gia' per `mars_citability`
    (R41). Il motivo qui e' piu' forte: un'opinione cambia a ogni
    esecuzione, e nello storico comparirebbe fra i «risolti» un difetto
    che nessuno ha toccato.

    Nessuna `penalty` e nessun `fix`: `mars_fixes.vesti()` veste per
    CHIAVE, e riusare la chiave d'origine — `lex.words.thin` — avrebbe
    messo su un'opinione la prescrizione di una misura. La chiave e'
    quindi nostra, `llm.content.*`, e l'indirizzo dell'area che quel
    difetto lo quantifica sta in `params["source_key"]`, dove c'e'.

    `info` a peso 1.0 come i derivati di `mars_citability`, e per la
    stessa ragione: la severita' e' l'asse su cui il piano si ordina, e
    un'opinione non deve mai scavalcare la misura.

    `text_lang` perche' `detail` e' testo di TERZI: le ISTRUZIONI sono
    in italiano e il modello risponde in italiano, quindi in un referto
    inglese quella prosa resta italiana e il referto lo dichiara. Il
    `title` invece e' nostro, ed e' a catalogo.
    """
    params: Dict[str, object] = {"derived": True, "model": model,
                                 "text_lang": "it"}
    if tema.source:
        params["source_key"] = tema.source
    return Finding(area="mars_llm_judge", severity=SEV_INFO, key=tema.key,
                   title=tema.title,
                   # Punto e virgola, non `\n`: `detail` finisce anche
                   # in un elenco Markdown, dove una seconda riga non
                   # rientrata esce dalla voce e spezza la lista.
                   # Misurato sul golden prima di scegliere.
                   detail="; ".join(prosa),
                   params=params).as_dict()


def punti_deboli_etichettati(grezzi: object) -> List[Tuple[str, str]]:
    """I punti deboli come coppie `(tema, prosa)`, in ordine d'arrivo.

    Lo SCHEMA obbliga il modello alla coppia e il `tema` a stare
    nell'enum, ma la risposta resta dato esterno: una stringa nuda —
    la forma che il modello dava prima di U10.1 — vale prosa senza
    tema, e un tema fuori vocabolario vale `altro`. Nessuno dei due
    casi fa perdere l'osservazione, che e' l'unica cosa che conta.
    """
    coppie: List[Tuple[str, str]] = []
    for voce in (grezzi if isinstance(grezzi, list) else []):
        if isinstance(voce, str):
            tema, testo = FUORI_VOCABOLARIO, voce
        elif isinstance(voce, dict):
            tema = str(voce.get("tema") or FUORI_VOCABOLARIO)
            testo = str(voce.get("testo") or "")
        else:
            continue
        if not testo.strip():
            continue
        coppie.append((tema if tema in VOCABOLARIO else FUORI_VOCABOLARIO,
                       testo.strip()))
    return coppie


def rilievi_dei_punti_deboli(coppie: List[Tuple[str, str]],
                             model: str = MODEL) -> List[dict]:
    """Un rilievo per TEMA, non per punto debole.

    E' la regola di tutta MARS — un rilievo e' un controllo, non
    un'occorrenza — e qui evita anche due rilievi con la stessa chiave
    dentro la stessa area: le ancore del referto HTML indicizzano per
    chiave, e la seconda avrebbe sovrascritto la prima.

    L'ordine e' quello di prima apparizione, non alfabetico: il modello
    elenca i punti deboli in ordine di importanza, e le `issues`
    mostrano i primi tre. Riordinare farebbe divergere le due viste.
    """
    per_tema: Dict[str, List[str]] = {}
    for tema, testo in coppie:
        per_tema.setdefault(tema, []).append(testo)
    return [_derivato(VOCABOLARIO.get(tema, TEMA_ALTRO), prosa, model)
            for tema, prosa in per_tema.items()]


def credenziali_presenti(context: Optional[dict] = None) -> bool:
    """Vero se una credenziale e' disponibile.

    Guarda prima quella fornita dal chiamante nella richiesta, poi
    l'ambiente. L'SDK sa risolvere anche un profilo 'ant auth login',
    che questa funzione non vede: per quello serve --llm on, che tenta
    comunque.
    """
    if (context or {}).get("credentials", {}).get("anthropic_api_key"):
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def credenziale_risolta(client: object) -> bool:
    """Vero se il client ha di che autenticarsi, senza toccare la rete.

    Le tre fonti sono quelle che l'SDK stesso guarda prima di firmare la
    richiesta — `api_key`, `auth_token` e il fornitore di token di un
    profilo `ant auth login`, che nessuna variabile d'ambiente mostra —
    e la condizione e' copiata da li'. Se divergesse, MARS direbbe
    «nessuna credenziale» a un invio che sarebbe partito.

    Un oggetto che non espone NESSUNA delle tre non e' un client
    dell'SDK: e' quello iniettato dai test, su cui non si puo' affermare
    nulla, e vale usabile.
    """
    fonti = [getattr(client, nome)
             for nome in ("api_key", "auth_token", "credentials")
             if hasattr(client, nome)]
    return not fonti or any(fonti)


def seleziona_chunk(context: dict) -> List[dict]:
    """I passaggi piu' recuperabili, secondo la fusione RRF.

    Si sottopone al modello cio' che una ricerca ibrida selezionerebbe
    davvero, non le prime pagine del sito: e' l'unico campione che
    rende il giudizio pertinente. Se i due ranghi non ci sono si
    ripiega sull'ordine naturale.
    """
    chunks = context.get("chunks") or []
    if not chunks:
        return []
    results = context.get("results") or {}
    lessicale = (results.get("mars_lexical") or {}).get("rank")
    semantico = (results.get("mars_semantic") or {}).get("rank")
    if lessicale and semantico:
        fusi = reciprocal_rank_fusion([lessicale, semantico],
                                      context.get("rrf_k", RRF_K))
        indici = [i for i, _ in fusi if i < len(chunks)]
    else:
        indici = list(range(len(chunks)))
    return [chunks[i] for i in indici[:MAX_CHUNK]]


def costruisci_prompt(url: str, chunks: List[dict]) -> str:
    """Prompt con i passaggi numerati, troncati a lunghezza nota."""
    parti = ["Sito: %s" % url, ""]
    for i, chunk in enumerate(chunks):
        testo = (chunk.get("text") or "")[:MAX_CARATTERI]
        parti.append("--- Passaggio %d — %s ---"
                     % (i, describe_chunk(chunk)))
        parti.append(testo)
        parti.append("")
    return "\n".join(parti)


def costo_stimato(prompt: str) -> Dict[str, int]:
    """Dimensione di cio' che verra' inviato, per dichiararlo prima.

    Il rapporto 1 token ogni 4 caratteri e' una stima grossolana e va
    detto: serve a dare un ordine di grandezza prima della spesa, non a
    prevedere la fattura.
    """
    return {"caratteri": len(prompt),
            "token_stimati_input": len(prompt) // 4,
            "token_massimi_output": MAX_TOKENS}


class RichiestaDeclinata(RuntimeError):
    """I classificatori del modello hanno rifiutato la richiesta.

    Eccezione **nostra**, non dell'SDK, quindi si distingue per tipo e
    non guardando il messaggio — al contrario del `TypeError` di C2, che
    viene da fuori e non lascia altra scelta. E' un fatto diverso da
    «giudizio non interpretabile»: li' il modello ha risposto e la
    risposta non si legge, qui non ha risposto affatto.

    Sottoclasse di `RuntimeError` perche' lo era gia': chi cattura la
    vecchia continua a catturarla (R31).
    """


def interroga(client, prompt: str, model: str = MODEL) -> dict:
    """Unica funzione che tocca la rete. Restituisce il JSON validato."""
    resp = client.beta.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        # Fallback lato server: se i classificatori declinano la
        # richiesta, viene rieseguita sul modello di ripiego invece di
        # andare persa.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT, "format": SCHEMA},
        system=ISTRUZIONI,
        messages=[{"role": "user", "content": prompt}],
    )
    if getattr(resp, "stop_reason", None) == "refusal":
        raise RichiestaDeclinata("richiesta declinata dai classificatori")
    testo = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(testo)


def audit(context: dict) -> dict:
    """Area 9: giudizio LLM sulla citabilità dei passaggi migliori.

    Modalita' (context["llm"]): "auto" attiva il giudizio solo se una
    credenziale e' presente, "on" tenta comunque, "off" non fa nulla.
    E' l'unico modulo che spende denaro: non deve mai partire per
    sbaglio, e dichiara la dimensione dell'invio prima di inviarlo.

    context["_anthropic_client"], se presente, viene usato al posto di
    un client reale: e' il punto di iniezione per i test, che devono
    poter esercitare tutto il percorso senza spendere nulla.
    """
    modalita = (context.get("llm") or "auto").lower()
    # `modalita`, non context["llm"]: con llm None o "OFF" il valore
    # grezzo e il ramo davvero preso divergerebbero.
    stato = {"mode": modalita, "attempted": False}
    if modalita == "off":
        return {"score": None, "status": "disabled",
                "issues": ["Giudizio LLM disattivato (--llm off)"],
                # Chiave sua, e non fusa con not_attempted: e' l'unico
                # esito del progetto che dipende da una SCELTA
                # dell'utente e non da uno stato del mondo. E `info`,
                # non SEV_OK: `ok` significa "controllo eseguito e
                # superato", mentre qui non e' stato eseguito nulla —
                # sarebbe la confusione fra score 0 e score None
                # spostata di un livello.
                "findings": [_stato(
                    "llm.status.disabled",
                    "Giudizio LLM disattivato (--llm off)", **stato)]}
    if modalita == "auto" and not credenziali_presenti(context):
        return {"score": None, "status": "unavailable",
                "issues": ["ANTHROPIC_API_KEY non presente: giudizio LLM "
                           "non eseguito (--llm on per tentare comunque)"],
                # `not_attempted` e non `no_key`: la chiave manca anche
                # in `no_credentials`, e cio' che distingue questo ramo
                # e' che non si e' tentato — per politica di --llm auto,
                # e infatti si ripara anche con --llm on.
                "findings": [_stato(
                    "llm.status.not_attempted",
                    "ANTHROPIC_API_KEY non presente: giudizio LLM non "
                    "eseguito (--llm on per tentare comunque)", **stato)]}
    try:
        import anthropic
    except ImportError:
        return {"score": None, "status": "unavailable",
                "issues": ["Libreria anthropic non installata "
                           "(pip install -r requirements-optional.txt)"],
                "findings": [_stato(
                    "llm.status.no_library",
                    "Libreria anthropic non installata "
                    "(pip install -r requirements-optional.txt)", **stato)]}

    chunks = seleziona_chunk(context)
    if not chunks:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessun passaggio da valutare"],
                # `no_chunks` come `sd.status.no_pages` e
                # `wcag.status.no_pages`: la chiave nomina la cosa che
                # manca, non il fatto astratto che manchi un ingresso.
                "findings": [_stato("llm.status.no_chunks",
                                    "Nessun passaggio da valutare",
                                    **stato)]}

    # Il client si costruisce PRIMA di annunciare la spesa, e la
    # credenziale si verifica su di lui: annunciare un invio che non
    # avverra' sarebbe fuorviante. Il `try` da solo non bastava —
    # l'SDK 0.122.0 costruisce sempre e risolve alla richiesta, quindi
    # non sollevava qui e l'annuncio si stampava lo stesso (R58). Resta
    # perche' un'altra versione, o un argomento incoerente, puo'
    # sollevare: e' l'altro modo in cui lo stesso fatto si presenta.
    chiave = (context.get("credentials") or {}).get("anthropic_api_key")
    try:
        client = (context.get("_anthropic_client")
                  or (anthropic.Anthropic(api_key=chiave) if chiave
                      else anthropic.Anthropic()))
    except (TypeError, ValueError, anthropic.AnthropicError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna credenziale Anthropic utilizzabile "
                           "(%s)" % type(exc).__name__],
                # Stessa chiave del ramo piu' sotto, con `stage` a
                # distinguere il momento: che l'SDK sollevi costruendo
                # il client o facendo la richiesta dipende dalla sua
                # versione, non da un fatto sull'audit. Senza `stage`,
                # un aggiornamento sposterebbe il fatto da un ramo
                # all'altro senza lasciare traccia.
                "findings": [_stato(
                    "llm.status.no_credentials",
                    "Nessuna credenziale Anthropic utilizzabile",
                    type(exc).__name__, stage="client", **stato)]}
    if not credenziale_risolta(client):
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna credenziale Anthropic utilizzabile"],
                # Stesse chiave e `stage` del ramo qui sopra: e' lo
                # stesso fatto — l'SDK non ha una credenziale da usare —
                # visto prima che sollevi invece che dopo. `detail`
                # resta vuoto perche' non c'e' un'eccezione da nominare.
                "findings": [_stato(
                    "llm.status.no_credentials",
                    "Nessuna credenziale Anthropic utilizzabile",
                    stage="client", **stato)]}

    prompt = costruisci_prompt(context.get("url", ""), chunks)
    costo = costo_stimato(prompt)
    print("  Giudizio LLM: invio %d passaggi (~%d token stimati) a %s..."
          % (len(chunks), costo["token_stimati_input"], MODEL), file=sys.stderr)

    # Da qui in avanti la richiesta e' partita: i rilievi lo dicono, e
    # portano con se' la traccia della spesa. `costo_stimato` esce oggi
    # solo dal ramo di successo, cioe' sparisce esattamente quando
    # qualcosa e' andato storto dopo l'invio.
    inviato = {"mode": modalita, "attempted": True, "model": MODEL,
               "chunks_sent": len(chunks),
               "estimated_input_tokens": costo["token_stimati_input"]}
    try:
        giudizio = interroga(client, prompt)
    except anthropic.APIError as exc:
        # `api_failed` e non `api_error`: `llm.status.error` e' gia' la
        # chiave che il referto sintetizza quando il MODULO solleva, e
        # due chiavi che differiscono per una parola e significano cose
        # diverse si confondono a mano.
        #
        # Da sapere: anthropic.AuthenticationError E' un APIError,
        # quindi una chiave sbagliata o scaduta finisce QUI e non in
        # `no_credentials`. I due fatti sono distinti e hanno riparazioni
        # diverse — l'SDK non ha RISOLTO una credenziale contro l'API ha
        # RIFIUTATO quella risolta — e `detail` porta il nome
        # dell'eccezione, che si autonomina.
        return {"score": None, "status": "unavailable",
                "issues": ["Errore API Anthropic: %s" % type(exc).__name__],
                "findings": [_stato("llm.status.api_failed",
                                    "Errore API Anthropic",
                                    type(exc).__name__, **inviato)]}
    except TypeError as exc:
        # L'SDK segnala l'assenza di credenziali con un TypeError, e lo
        # fa al momento della richiesta, non della costruzione del
        # client: senza questa distinzione un problema di chiave
        # verrebbe riportato come "giudizio non interpretabile".
        credenziali = "authentication" in str(exc).lower()
        if credenziali:
            return {"score": None, "status": "unavailable",
                    "issues": ["Nessuna credenziale Anthropic utilizzabile"],
                    "findings": [_stato(
                        "llm.status.no_credentials",
                        "Nessuna credenziale Anthropic utilizzabile",
                        type(exc).__name__, stage="request", **inviato)]}
        # Fatto DIVERSO, quindi chiave diversa: un TypeError senza
        # "authentication" nel messaggio vuol dire che la chiamata a
        # interroga() e' malformata — un kwarg ignoto, un SDK
        # incompatibile — ed e' un difetto nostro, non una credenziale
        # mancante. Fonderli rifarebbe il difetto che C2 ha gia' chiuso.
        return {"score": None, "status": "unavailable",
                "issues": ["Chiamata non valida: %s" % exc],
                # `str(exc)` in detail e non nel title: il titolo resta
                # invariante come la chiave, e la issue quel messaggio
                # lo pubblica gia'.
                "findings": [_stato("llm.status.bad_call",
                                    "Chiamata non valida",
                                    str(exc), **inviato)]}
    except RichiestaDeclinata as exc:
        # Ramo e status propri (R31). Prima finiva nel gruppo generico
        # qui sotto, e la vista compatta diceva «Giudizio non
        # interpretabile: RuntimeError» — che e' impreciso due volte:
        # non c'e' alcun giudizio da interpretare, e il nome
        # dell'eccezione Python non dice niente a chi legge un referto.
        # U1.9 aveva gia' portato il messaggio nel `detail`; la meta'
        # che mancava e' questa.
        #
        # Resta `info` come gli altri `llm.status.*`: e' un fatto sulla
        # scansione, non un difetto del sito, e non si ripara cambiando
        # il sito. La richiesta e' comunque partita, quindi `inviato`
        # porta con se' il conto dei passaggi e la stima dei token.
        return {"score": None, "status": "unavailable",
                "issues": ["Richiesta declinata dai classificatori del "
                           "modello"],
                "findings": [_stato(
                    "llm.status.refused",
                    "Richiesta declinata dai classificatori del modello",
                    str(exc), **inviato)]}
    except (RuntimeError, KeyError, StopIteration,
            json.JSONDecodeError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Giudizio non interpretabile: %s"
                           % type(exc).__name__],
                # Una chiave per quattro eccezioni — sono gia' indistinte
                # nella issue, e quattro chiavi per quattro nomi di
                # eccezione Python farebbero della chiave un dettaglio
                # del linguaggio. Il messaggio entra in `detail` perche'
                # e' l'unico posto in cui sopravvive il "richiesta
                # declinata dai classificatori" che interroga() solleva:
                # la issue pubblica il solo tipo, RuntimeError.
                "findings": [_stato(
                    "llm.status.unreadable", "Giudizio non interpretabile",
                    "%s: %s" % (type(exc).__name__, exc), **inviato)]}

    indice: Optional[int] = giudizio.get("passaggio_migliore")
    migliore = (describe_chunk(chunks[indice])
                if isinstance(indice, int) and 0 <= indice < len(chunks)
                else None)
    # Il modello puo' rispondere con un JSON valido e ometterne il
    # punteggio: e' una risposta, non una misura, e senza status
    # finiva nel referto come score None indistinguibile da un'area
    # mai eseguita.
    citabilita = giudizio.get("citabilita")
    deboli = punti_deboli_etichettati(giudizio.get("punti_deboli"))
    prosa = [testo for _, testo in deboli]
    issues = prosa[:3]
    rilievi: List[dict] = rilievi_dei_punti_deboli(deboli)
    if citabilita is None:
        issues.insert(0, "Il modello ha risposto senza indicare un "
                         "punteggio di citabilita'")
        # In testa come la issue, e prima dei derivati: e' un fatto
        # sulla risposta, e cio' che la risposta dice viene dopo.
        # `info` e non `warning` benche' sia una delusione: e' una
        # risposta, non una misura, e resta un fatto sull'esecuzione —
        # nessuna modifica al sito lo ripara.
        rilievi.insert(0, _stato(
            "llm.status.no_score",
            "Il modello ha risposto senza indicare un punteggio di "
            "citabilita'", **inviato))

    return {
        "score": citabilita,
        "findings": rilievi,
        "status": None if citabilita is not None else "unavailable",
        "issues": issues,
        "model": MODEL,
        "motivazione": giudizio.get("motivazione"),
        "punti_forti": giudizio.get("punti_forti"),
        # La PROSA, non le coppie: la resa dei tre formati stampa i
        # punti deboli come righe, e il tema vive gia' nei rilievi.
        # Cambiare qui la forma del dato pubblicato spezzerebbe ogni
        # consumatore del JSON senza dargli nulla in cambio.
        "punti_deboli": prosa,
        "passaggio_migliore": migliore,
        "chunk_valutati": len(chunks),
        "costo_stimato": costo,
    }
