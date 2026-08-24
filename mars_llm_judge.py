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
from typing import Dict, List, Optional

from mars_core import (SEV_INFO, Finding, describe_chunk,
                       reciprocal_rank_fusion)

MODEL = "claude-opus-5"
MAX_CHUNK = 8          # quanti passaggi sottoporre al modello
MAX_CARATTERI = 1200   # per passaggio
MAX_TOKENS = 4000      # il giudizio e' breve: non serve di piu'
EFFORT = "medium"

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
            "punti_deboli": {"type": "array", "items": {"type": "string"}},
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
dei siti non è citabile, e un voto alto deve significare qualcosa."""


def _stato(chiave: str, testo: str, dettaglio: str = "",
           **params: object) -> dict:
    """Un fatto sull'ESECUZIONE del giudizio, mai un difetto del sito.

    Quest'area emette SOLO rilievi di stato. I `punti_deboli` che il
    modello restituisce restano `issues` e non diventano Finding:
    `Finding.key` e' cio' su cui poggeranno il confronto fra due
    esecuzioni e i cataloghi di traduzione, e una chiave ricavata da
    prosa libera sarebbe o variabile — vietato — o ripetuta, che
    distrugge l'identita'. Quella prosa cambia per giunta a ogni
    esecuzione (`thinking: adaptive`) e a ogni modello: un confronto fra
    due referti riporterebbe differenze a ogni giro.

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
        fusi = reciprocal_rank_fusion([lessicale, semantico])
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
        raise RuntimeError("richiesta declinata dai classificatori")
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

    # Il client si costruisce PRIMA di annunciare la spesa: senza
    # credenziali risolvibili l'SDK solleva TypeError, e annunciare un
    # invio che non avverra' sarebbe fuorviante.
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

    prompt = costruisci_prompt(context.get("url", ""), chunks)
    costo = costo_stimato(prompt)
    print("  Giudizio LLM: invio %d passaggi (~%d token stimati) a %s..."
          % (len(chunks), costo["token_stimati_input"], MODEL))

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
    issues = list(giudizio.get("punti_deboli") or [])[:3]
    rilievi: List[dict] = []
    if citabilita is None:
        issues.insert(0, "Il modello ha risposto senza indicare un "
                         "punteggio di citabilita'")
        # In testa come la issue. `info` e non `warning` benche' sia una
        # delusione: e' una risposta, non una misura, e resta un fatto
        # sull'esecuzione — nessuna modifica al sito lo ripara.
        rilievi.append(_stato(
            "llm.status.no_score",
            "Il modello ha risposto senza indicare un punteggio di "
            "citabilita'", **inviato))
    # Quando il giudizio riesce l'elenco resta VUOTO, ed e' voluto: i
    # punti deboli che il modello nomina sono prosa, non rilievi (vedi
    # _stato). E' l'unico punto della fase in cui la vista compatta dice
    # piu' del dato canonico, e va saputo.

    return {
        "score": citabilita,
        "findings": rilievi,
        "status": None if citabilita is not None else "unavailable",
        "issues": issues,
        "model": MODEL,
        "motivazione": giudizio.get("motivazione"),
        "punti_forti": giudizio.get("punti_forti"),
        "punti_deboli": giudizio.get("punti_deboli"),
        "passaggio_migliore": migliore,
        "chunk_valutati": len(chunks),
        "costo_stimato": costo,
    }
