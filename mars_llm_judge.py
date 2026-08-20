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

from mars_core import describe_chunk, reciprocal_rank_fusion

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


def credenziali_presenti() -> bool:
    """Vero se l'SDK trovera' una credenziale nell'ambiente.

    L'SDK sa risolvere anche un profilo 'ant auth login', che questa
    funzione non vede: per quello serve --llm on, che tenta comunque.
    """
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
    if modalita == "off":
        return {"score": None, "status": "disabled",
                "issues": ["Giudizio LLM disattivato (--llm off)"]}
    if modalita == "auto" and not credenziali_presenti():
        return {"score": None, "status": "unavailable",
                "issues": ["ANTHROPIC_API_KEY non presente: giudizio LLM "
                           "non eseguito (--llm on per tentare comunque)"]}
    try:
        import anthropic
    except ImportError:
        return {"score": None, "status": "unavailable",
                "issues": ["Libreria anthropic non installata "
                           "(pip install -r requirements-optional.txt)"]}

    chunks = seleziona_chunk(context)
    if not chunks:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessun passaggio da valutare"]}

    # Il client si costruisce PRIMA di annunciare la spesa: senza
    # credenziali risolvibili l'SDK solleva TypeError, e annunciare un
    # invio che non avverra' sarebbe fuorviante.
    try:
        client = context.get("_anthropic_client") or anthropic.Anthropic()
    except (TypeError, ValueError, anthropic.AnthropicError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna credenziale Anthropic utilizzabile "
                           "(%s)" % type(exc).__name__]}

    prompt = costruisci_prompt(context.get("url", ""), chunks)
    costo = costo_stimato(prompt)
    print("  Giudizio LLM: invio %d passaggi (~%d token stimati) a %s..."
          % (len(chunks), costo["token_stimati_input"], MODEL))

    try:
        giudizio = interroga(client, prompt)
    except anthropic.APIError as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Errore API Anthropic: %s" % type(exc).__name__]}
    except TypeError as exc:
        # L'SDK segnala l'assenza di credenziali con un TypeError, e lo
        # fa al momento della richiesta, non della costruzione del
        # client: senza questa distinzione un problema di chiave
        # verrebbe riportato come "giudizio non interpretabile".
        credenziali = "authentication" in str(exc).lower()
        return {"score": None, "status": "unavailable",
                "issues": ["Nessuna credenziale Anthropic utilizzabile"
                           if credenziali else
                           "Chiamata non valida: %s" % exc]}
    except (RuntimeError, KeyError, StopIteration,
            json.JSONDecodeError) as exc:
        return {"score": None, "status": "unavailable",
                "issues": ["Giudizio non interpretabile: %s"
                           % type(exc).__name__]}

    indice: Optional[int] = giudizio.get("passaggio_migliore")
    migliore = (describe_chunk(chunks[indice])
                if isinstance(indice, int) and 0 <= indice < len(chunks)
                else None)
    return {
        "score": giudizio.get("citabilita"),
        "issues": list(giudizio.get("punti_deboli") or [])[:3],
        "model": MODEL,
        "motivazione": giudizio.get("motivazione"),
        "punti_forti": giudizio.get("punti_forti"),
        "punti_deboli": giudizio.get("punti_deboli"),
        "passaggio_migliore": migliore,
        "chunk_valutati": len(chunks),
        "costo_stimato": costo,
    }
