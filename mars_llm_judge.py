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

import requests

from mars_core import (SEV_INFO, Finding, describe_chunk,
                       reciprocal_rank_fusion, RRF_K)

MODEL = "claude-opus-5"
MAX_CHUNK = 8          # quanti passaggi sottoporre al modello
MAX_CARATTERI = 1200   # per passaggio
MAX_TOKENS = 4000      # il giudizio e' breve: non serve di piu'
EFFORT = "medium"
TIMEOUT_HTTP = 120     # secondi, per i giudici OpenAI-compatibili


class Giudice(NamedTuple):
    """Un provider del giudizio, e come lo si interroga."""

    model: str          # modello predefinito, sovrascrivibile dal flag
    profile: str        # la chiave in citability["profiles"]
    kind: str           # "anthropic" (SDK) oppure "openai" (HTTP)
    base_url: str       # solo per kind "openai"
    env: Tuple[str, ...]     # variabili d'ambiente della credenziale
    credential: str          # nome in context["credentials"]
    base_url_env: str        # variabile che sovrascrive base_url
    tokens_field: str = ""   # come si chiama il tetto ai token generati


# I giudici, e da dove vengono i loro indirizzi.
# ----------------------------------------------------------------------
# Tre dei quattro parlano lo stesso protocollo — `POST
# /chat/completions` con `response_format`, risposta in
# `choices[0].message.content` — quindi hanno UN solo percorso di codice.
# Le forme sono state verificate sulla documentazione dei fornitori il
# 2026-08-28, non ricordate:
#
#   openai  developers.openai.com/api/docs/api-reference/chat/create
#   kimi    platform.kimi.ai/docs/api/chat
#   qwen    alibabacloud.com/help/en/model-studio/
#           compatibility-of-openai-with-dashscope
#
# `profile` aggancia il giudice al profilo che `mars_citability` stima
# per quello stesso assistente: e' cio' che rende calcolabile lo scarto
# fra quanto un modello si giudica citabile e quanto la nostra euristica
# prevede che lo giudichi. Le chiavi sono quelle di `PESI_ASSISTENTE`,
# che e' un dict nome -> punteggio: `'ChatGPT/Perplexity'` e non
# `'openai'`.
#
# `base_url_env` esiste per i test: il server finto ci si aggancia senza
# che il codice sappia di essere in prova.
JUDGE_PROVIDERS: Dict[str, Giudice] = {
    "anthropic": Giudice(
        MODEL, "Claude", "anthropic", "",
        ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
        "anthropic_api_key", "ANTHROPIC_BASE_URL"),
    "openai": Giudice(
        "gpt-5.6", "ChatGPT/Perplexity", "openai",
        "https://api.openai.com/v1", ("OPENAI_API_KEY",),
        "openai_api_key", "OPENAI_BASE_URL",
        # `max_tokens` e' deprecato su OpenAI e incompatibile con la
        # serie o; i due compatibili documentano ancora il vecchio nome.
        # Il campo sta nel registro invece che nel codice proprio
        # perche' "OpenAI-compatibile" non vuol dire "identico".
        "max_completion_tokens"),
    "qwen": Giudice(
        # L'endpoint internazionale: quello di Pechino
        # (dashscope.aliyuncs.com) si sceglie con DASHSCOPE_BASE_URL.
        "qwen-plus", "Qwen", "openai",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ("DASHSCOPE_API_KEY",), "dashscope_api_key",
        "DASHSCOPE_BASE_URL",
        "max_tokens"),
    "kimi": Giudice(
        "kimi-k2.5", "Kimi", "openai",
        "https://api.moonshot.ai/v1", ("MOONSHOT_API_KEY",),
        "moonshot_api_key", "MOONSHOT_BASE_URL",
        "max_tokens"),
}

GIUDICE_PREDEFINITO = "anthropic"


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


def _derivato(tema: Tema, prosa: List[str], provider: str,
              model: str) -> dict:
    """Un punto debole del modello, come rilievo.

    **Un rilievo per giudice e per tema** (U10): quattro modelli che
    nominano lo stesso tema danno quattro rilievi, non uno. Le chiavi
    si ripetono quindi dentro l'area, e va saputo che non e' un
    problema: chi indicizza per chiave o salta i derivati — piano di
    interventi, storico, conteggi per gravita' — o guarda solo i
    rilievi con un `fix`, che un derivato non ha mai (`_ancore` in
    `mars_report`). Il provider entra nel TITOLO, non nella chiave: un
    titolo porta valori variabili gia' altrove (`%(pagine)d di
    %(totale)d`), una chiave non deve.

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
    params: Dict[str, object] = {"derived": True, "provider": provider,
                                 "model": model, "text_lang": "it"}
    if tema.source:
        params["source_key"] = tema.source
    return Finding(area="mars_llm_judge", severity=SEV_INFO, key=tema.key,
                   title="%s — %s" % (tema.title, provider),
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
                             provider: str = GIUDICE_PREDEFINITO,
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
    return [_derivato(VOCABOLARIO.get(tema, TEMA_ALTRO), prosa,
                      provider, model)
            for tema, prosa in per_tema.items()]


def giudici_richiesti(context: dict
                      ) -> Tuple[List[Tuple[str, Giudice, str]], List[str]]:
    """I giudici scelti, e i nomi che il registro non conosce.

    Il formato e' `provider[:modello],...`, da `--judge-models` o dal
    corpo API. Un nome ignoto NON ferma l'audit e non sparisce: torna
    nel secondo elenco, e diventa un rilievo di stato — sbagliare a
    scrivere `qwn` non deve produrre un referto che tace.

    Senza richiesta vale il solo `anthropic`, che e' quello che MARS
    interrogava prima di U10: aggiungere provider e' una scelta, e
    quest'area e' l'unica che spende.
    """
    grezzo = str(context.get("judge_models") or "").strip()
    if not grezzo:
        grezzo = GIUDICE_PREDEFINITO
    scelti: List[Tuple[str, Giudice, str]] = []
    ignoti: List[str] = []
    visti = set()
    for voce in grezzo.split(","):
        voce = voce.strip()
        if not voce:
            continue
        nome, _, modello = voce.partition(":")
        nome = nome.strip().lower()
        giudice = JUDGE_PROVIDERS.get(nome)
        if giudice is None:
            if nome not in ignoti:
                ignoti.append(nome)
            continue
        # Lo stesso provider due volte e' quasi certamente un refuso, e
        # interrogarlo due volte lo si paga due volte.
        if nome in visti:
            continue
        visti.add(nome)
        scelti.append((nome, giudice, modello.strip() or giudice.model))
    return scelti, ignoti


def credenziale_del_giudice(giudice: Giudice,
                            context: Optional[dict] = None) -> str:
    """La chiave di questo giudice: prima il chiamante, poi l'ambiente.

    Stesso ordine di `credenziali_presenti` e di ogni altro modulo: chi
    fa una richiesta API porta le proprie chiavi e non deve dipendere
    dall'ambiente del server.
    """
    fornita = (context or {}).get("credentials", {}).get(giudice.credential)
    if fornita:
        return str(fornita)
    for nome in giudice.env:
        valore = os.environ.get(nome)
        if valore:
            return valore
    return ""


def indirizzo_del_giudice(giudice: Giudice) -> str:
    """Il base_url, sovrascrivibile dall'ambiente.

    Serve ai server finti dei test — che si agganciano senza che il
    codice sappia di essere in prova — e a chi usa un endpoint
    regionale: DashScope ne ha uno internazionale e uno di Pechino.
    """
    return os.environ.get(giudice.base_url_env) or giudice.base_url


def interroga_openai(giudice: Giudice, modello: str, prompt: str,
                     chiave: str, base_url: str,
                     sessione: object = None) -> Tuple[dict, bool]:
    """Unica funzione che tocca la rete per i giudici OpenAI-compatibili.

    Restituisce `(giudizio, schema_imposto)`. Lo schema si chiede con
    `response_format: json_schema`, che i tre fornitori documentano; su
    DashScope pero' il supporto dipende dal MODELLO e non dal servizio,
    quindi un rifiuto e' un esito previsto: si riprova una volta sola
    con `json_object`, e `schema_imposto` diventa falso perche' il
    referto deve poterlo dire. Senza quella dichiarazione un tema
    inventato dal modello passerebbe per una scelta dal vocabolario.

    Il ripiego scatta su un **400 qualunque**, ed e' deliberatamente
    largo: distinguere «schema non supportato» da un'altra richiesta
    malformata richiederebbe di indovinare messaggi d'errore che non
    abbiamo verificato. Una richiesta davvero malformata fallisce due
    volte, e il secondo errore e' quello che si riporta.
    """
    http = sessione if sessione is not None else requests
    url = base_url.rstrip("/") + "/chat/completions"
    intestazioni = {"Authorization": "Bearer %s" % chiave,
                    "Content-Type": "application/json"}
    corpo: Dict[str, object] = {
        "model": modello,
        "messages": [{"role": "system", "content": ISTRUZIONI},
                     {"role": "user", "content": prompt}],
        giudice.tokens_field: MAX_TOKENS,
    }
    formati = (
        ({"type": "json_schema",
          "json_schema": {"name": "giudizio_citabilita",
                          "schema": SCHEMA["schema"], "strict": True}},
         True),
        ({"type": "json_object"}, False),
    )
    ultima: Optional[requests.Response] = None
    for formato, imposto in formati:
        resp = http.post(url, headers=intestazioni,
                         json=dict(corpo, response_format=formato),
                         timeout=TIMEOUT_HTTP)
        if resp.status_code == 200:
            return _leggi_scelta(resp.json()), imposto
        ultima = resp
        if resp.status_code != 400:
            break
    stato = ultima.status_code if ultima is not None else 0
    raise requests.HTTPError("HTTP %d" % stato)


def _leggi_scelta(dati: dict) -> dict:
    """Il JSON del giudizio da una risposta chat/completions.

    `refusal` e' un campo dell'assistente, non un codice di stato: un
    rifiuto arriva con HTTP 200 e va riconosciuto, o si leggerebbe un
    `content` vuoto come «giudizio non interpretabile».
    """
    scelte = dati.get("choices") or []
    if not scelte:
        raise KeyError("choices")
    messaggio = (scelte[0] or {}).get("message") or {}
    if messaggio.get("refusal"):
        raise RichiestaDeclinata(str(messaggio["refusal"]))
    return json.loads(messaggio.get("content") or "")


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


def scarti_di_onesta(giudice: Giudice, punteggio: Optional[int],
                     results: Optional[dict]) -> Dict[str, object]:
    """Di quanto il modello si discosta da cio' che l'euristica prevede.

    Due scarti, e sono due domande diverse. Il primo confronta il voto
    del giudice con l'**indice composito** di `mars_citability`: quanto
    l'opinione di un modello si allontana dalla stima complessiva. Il
    secondo lo confronta col profilo che quella stessa euristica
    calcola **per quell'assistente** — Claude contro il profilo
    "Claude", ChatGPT contro "ChatGPT/Perplexity" — ed e' il piu'
    stringente: li' l'euristica prova a prevedere proprio quel giudice.

    Convenzione: **giudizio meno euristica**. Positivo significa che il
    modello si giudica piu' citabile di quanto la nostra stima preveda.
    Dichiararla e' necessario: uno scarto senza segno concordato si
    legge al contrario.

    `None` dove manca un termine, e non zero: `mars_citability` puo' non
    aver calcolato il composito, e un profilo puo' non esserci. Zero
    direbbe «coincidono».

    Si puo' calcolare qui perche' l'area 8 gira PRIMA della 9 nel
    registro: `context["results"]["mars_citability"]` c'e' gia'. Farlo
    nei renderer significherebbe la stessa aritmetica in tre posti.
    """
    cit = (results or {}).get("mars_citability") or {}
    composito = cit.get("score")
    profilo = (cit.get("profiles") or {}).get(giudice.profile)

    def scarto(atteso: object) -> Optional[float]:
        if punteggio is None or not isinstance(atteso, (int, float)):
            return None
        return round(float(punteggio) - float(atteso), 1)

    return {"profile": giudice.profile,
            "composite_score": composito,
            "profile_score": profilo,
            "delta_composite": scarto(composito),
            "delta_profile": scarto(profilo)}


def _giudizio_vuoto(nome: str, giudice: Giudice, modello: str,
                    issues: List[str], rilievi: List[dict]) -> dict:
    """L'esito di un giudice che non ha risposto.

    `answered` e' la sola cosa che distingue questo caso da un giudizio
    riuscito senza punteggio: senza, «il modello non ha risposto» e «ha
    risposto e non ha dato un voto» collasserebbero su `score: None`, che
    e' la confusione che U1.9 aveva gia' tolto una volta.
    """
    return {"provider": nome, "model": modello, "profile": giudice.profile,
            "status": "unavailable", "answered": False, "score": None,
            "issues": issues, "findings": rilievi}


def giudica(nome: str, giudice: Giudice, modello: str, context: dict,
            chunks: List[dict], prompt: str,
            costo: Dict[str, int]) -> dict:
    """Interroga UN giudice e ne restituisce l'esito, senza mai sollevare.

    Ogni ramo che esce senza giudizio porta con se' un rilievo di stato:
    un giudice che manca si dichiara, non sparisce (principio 2). E un
    giudice che fallisce non toglie gli altri dal referto — e' la ragione
    per cui questa funzione cattura tutto e `run_judges` non ha un
    `try`.
    """
    modalita = (context.get("llm") or "auto").lower()
    stato = {"mode": modalita, "attempted": False, "provider": nome}
    chiave = credenziale_del_giudice(giudice, context)
    iniettato = context.get("_anthropic_client")

    if modalita == "auto" and not chiave and not iniettato:
        testo = ("%s non presente: giudizio LLM non eseguito "
                 "(--llm on per tentare comunque)" % giudice.env[0])
        # `not_attempted` e non `no_key`: la chiave manca anche in
        # `no_credentials`, e cio' che distingue questo ramo e' che non
        # si e' tentato — per politica di --llm auto, e infatti si
        # ripara anche con --llm on.
        return _giudizio_vuoto(nome, giudice, modello, [testo], [
            _stato("llm.status.not_attempted", testo, **stato)])

    if giudice.kind == "anthropic":
        return _giudica_anthropic(nome, giudice, modello, context, chunks,
                                  prompt, costo, stato, chiave)
    return _giudica_openai(nome, giudice, modello, context, chunks,
                           prompt, costo, stato, chiave)


def _inviato(stato: dict, modello: str, chunks: List[dict],
             costo: Dict[str, int]) -> dict:
    """La traccia della spesa, per i rami che escono DOPO l'invio.

    `costo_stimato` esce dal solo ramo di successo, cioe' sparirebbe
    esattamente quando qualcosa e' andato storto dopo l'invio.
    """
    return dict(stato, attempted=True, model=modello,
                chunks_sent=len(chunks),
                estimated_input_tokens=costo["token_stimati_input"])


def _annuncia(nome: str, modello: str, chunks: List[dict],
              costo: Dict[str, int]) -> None:
    """La spesa si dichiara PRIMA di farla, e su stderr (R59)."""
    print("  Giudizio LLM [%s]: invio %d passaggi (~%d token stimati) a %s..."
          % (nome, len(chunks), costo["token_stimati_input"], modello),
          file=sys.stderr)


def _giudica_anthropic(nome: str, giudice: Giudice, modello: str,
                       context: dict, chunks: List[dict], prompt: str,
                       costo: Dict[str, int], stato: dict,
                       chiave: str) -> dict:
    """Il giudice via SDK ufficiale."""
    try:
        import anthropic
    except ImportError:
        testo = ("Libreria anthropic non installata "
                 "(pip install -r requirements-optional.txt)")
        return _giudizio_vuoto(nome, giudice, modello, [testo], [
            _stato("llm.status.no_library", testo, **stato)])

    # Il client si costruisce PRIMA di annunciare la spesa, e la
    # credenziale si verifica su di lui: annunciare un invio che non
    # avverra' sarebbe fuorviante. Il `try` da solo non bastava —
    # l'SDK 0.122.0 costruisce sempre e risolve alla richiesta, quindi
    # non sollevava qui e l'annuncio si stampava lo stesso (R58). Resta
    # perche' un'altra versione, o un argomento incoerente, puo'
    # sollevare: e' l'altro modo in cui lo stesso fatto si presenta.
    try:
        client = (context.get("_anthropic_client")
                  or (anthropic.Anthropic(api_key=chiave) if chiave
                      else anthropic.Anthropic()))
    except (TypeError, ValueError, anthropic.AnthropicError) as exc:
        testo = "Nessuna credenziale Anthropic utilizzabile"
        # Stessa chiave del ramo piu' sotto, con `stage` a distinguere il
        # momento: che l'SDK sollevi costruendo il client o facendo la
        # richiesta dipende dalla sua versione, non da un fatto
        # sull'audit. Senza `stage`, un aggiornamento sposterebbe il
        # fatto da un ramo all'altro senza lasciare traccia.
        return _giudizio_vuoto(
            nome, giudice, modello,
            ["%s (%s)" % (testo, type(exc).__name__)],
            [_stato("llm.status.no_credentials", testo,
                    type(exc).__name__, stage="client", **stato)])
    if not credenziale_risolta(client):
        testo = "Nessuna credenziale Anthropic utilizzabile"
        # Stesse chiave e `stage` del ramo qui sopra: e' lo stesso fatto
        # — l'SDK non ha una credenziale da usare — visto prima che
        # sollevi invece che dopo. `detail` resta vuoto perche' non c'e'
        # un'eccezione da nominare.
        return _giudizio_vuoto(nome, giudice, modello, [testo], [
            _stato("llm.status.no_credentials", testo, stage="client",
                   **stato)])

    _annuncia(nome, modello, chunks, costo)
    inviato = _inviato(stato, modello, chunks, costo)
    try:
        giudizio = interroga(client, prompt, modello)
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
        return _giudizio_vuoto(
            nome, giudice, modello,
            ["Errore API Anthropic: %s" % type(exc).__name__],
            [_stato("llm.status.api_failed", "Errore API Anthropic",
                    type(exc).__name__, **inviato)])
    except TypeError as exc:
        # L'SDK segnala l'assenza di credenziali con un TypeError, e lo
        # fa al momento della richiesta, non della costruzione del
        # client: senza questa distinzione un problema di chiave
        # verrebbe riportato come "giudizio non interpretabile".
        if "authentication" in str(exc).lower():
            testo = "Nessuna credenziale Anthropic utilizzabile"
            return _giudizio_vuoto(nome, giudice, modello, [testo], [
                _stato("llm.status.no_credentials", testo,
                       type(exc).__name__, stage="request", **inviato)])
        # Fatto DIVERSO, quindi chiave diversa: un TypeError senza
        # "authentication" nel messaggio vuol dire che la chiamata a
        # interroga() e' malformata — un kwarg ignoto, un SDK
        # incompatibile — ed e' un difetto nostro, non una credenziale
        # mancante. Fonderli rifarebbe il difetto che C2 ha gia' chiuso.
        return _giudizio_vuoto(
            nome, giudice, modello, ["Chiamata non valida: %s" % exc],
            # `str(exc)` in detail e non nel title: il titolo resta
            # invariante come la chiave, e la issue quel messaggio lo
            # pubblica gia'.
            [_stato("llm.status.bad_call", "Chiamata non valida",
                    str(exc), **inviato)])
    except RichiestaDeclinata as exc:
        return _rifiutato(nome, giudice, modello, exc, inviato)
    except (RuntimeError, KeyError, StopIteration,
            json.JSONDecodeError) as exc:
        return _illeggibile(nome, giudice, modello, exc, inviato)
    return _leggi_giudizio(nome, giudice, modello, giudizio, chunks,
                           costo, inviato, context, True)


def _giudica_openai(nome: str, giudice: Giudice, modello: str,
                    context: dict, chunks: List[dict], prompt: str,
                    costo: Dict[str, int], stato: dict,
                    chiave: str) -> dict:
    """Il giudice via endpoint OpenAI-compatibile.

    `context["_judge_sessions"][nome]`, se c'e', prende il posto di
    `requests`: e' il punto di iniezione dei test, gemello di
    `_anthropic_client`, e permette di esercitare tutto il percorso
    senza rete e senza spesa.
    """
    if not chiave:
        testo = "Nessuna credenziale %s utilizzabile" % nome
        return _giudizio_vuoto(nome, giudice, modello, [testo], [
            _stato("llm.status.no_credentials", testo, stage="client",
                   **stato)])

    _annuncia(nome, modello, chunks, costo)
    inviato = _inviato(stato, modello, chunks, costo)
    sessione = (context.get("_judge_sessions") or {}).get(nome)
    try:
        giudizio, imposto = interroga_openai(
            giudice, modello, prompt, chiave,
            indirizzo_del_giudice(giudice), sessione)
    except requests.RequestException as exc:
        # Un solo ramo per rete e stato HTTP: dal punto di vista di chi
        # legge il referto sono lo stesso fatto — il servizio non ha
        # risposto come doveva — e `detail` porta il dettaglio.
        return _giudizio_vuoto(
            nome, giudice, modello,
            ["Errore API %s: %s" % (nome, exc)],
            [_stato("llm.status.api_failed", "Errore API %s" % nome,
                    str(exc), **inviato)])
    except RichiestaDeclinata as exc:
        return _rifiutato(nome, giudice, modello, exc, inviato)
    except (RuntimeError, KeyError, TypeError, StopIteration,
            json.JSONDecodeError) as exc:
        return _illeggibile(nome, giudice, modello, exc, inviato)
    return _leggi_giudizio(nome, giudice, modello, giudizio, chunks,
                           costo, inviato, context, imposto)


def _rifiutato(nome: str, giudice: Giudice, modello: str,
               exc: Exception, inviato: dict) -> dict:
    """I classificatori del modello hanno declinato (R31).

    Ramo e chiave propri: nel gruppo generico la vista compatta diceva
    «Giudizio non interpretabile: RuntimeError», impreciso due volte —
    non c'e' alcun giudizio da interpretare, e il nome dell'eccezione
    Python non dice niente a chi legge un referto.
    """
    testo = "Richiesta declinata dai classificatori del modello"
    return _giudizio_vuoto(nome, giudice, modello, [testo], [
        _stato("llm.status.refused", testo, str(exc), **inviato)])


def _illeggibile(nome: str, giudice: Giudice, modello: str,
                 exc: Exception, inviato: dict) -> dict:
    """Il modello ha risposto e la risposta non si legge.

    Una chiave per piu' eccezioni — sono gia' indistinte nella issue, e
    una chiave per ogni nome di eccezione Python farebbe della chiave un
    dettaglio del linguaggio. Il messaggio entra in `detail` perche' e'
    l'unico posto in cui sopravvive.
    """
    return _giudizio_vuoto(
        nome, giudice, modello,
        ["Giudizio non interpretabile: %s" % type(exc).__name__],
        [_stato("llm.status.unreadable", "Giudizio non interpretabile",
                "%s: %s" % (type(exc).__name__, exc), **inviato)])


def _leggi_giudizio(nome: str, giudice: Giudice, modello: str,
                    giudizio: dict, chunks: List[dict],
                    costo: Dict[str, int], inviato: dict, context: dict,
                    schema_imposto: bool) -> dict:
    """Il giudizio del modello come esito d'area, per un solo giudice."""
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
    rilievi = rilievi_dei_punti_deboli(deboli, nome, modello)
    if not schema_imposto:
        # Va DETTO. Senza lo schema il `tema` non e' vincolato all'enum,
        # quindi cio' che il modello scrive finisce in `llm.content.other`
        # per la via del ripiego e non perche' l'abbia scelto: il referto
        # farebbe passare per scelta da vocabolario una stringa inventata.
        issues.append("Schema non imposto da %s: i temi dei punti deboli "
                      "non sono vincolati al vocabolario" % nome)
        rilievi.insert(0, _stato(
            "llm.status.no_schema",
            "Schema non imposto: i temi non sono vincolati al vocabolario",
            **inviato))
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
        "provider": nome,
        "model": modello,
        "profile": giudice.profile,
        "status": None if citabilita is not None else "unavailable",
        "answered": True,
        "schema_enforced": schema_imposto,
        "score": citabilita,
        "issues": issues,
        "findings": rilievi,
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
        "scarti": scarti_di_onesta(giudice, citabilita,
                                   context.get("results")),
    }


def run_judges(context: dict, chunks: List[dict], prompt: str,
               costo: Dict[str, int]) -> Tuple[List[dict], List[str]]:
    """Tutti i giudici richiesti, nell'ordine in cui sono stati chiesti.

    Nessun `try` qui: `giudica` non solleva mai, ed e' li' che la
    promessa «un giudice che fallisce non toglie gli altri dal referto»
    e' mantenuta. Un `try` in questo ciclo la manterrebbe lo stesso e
    nasconderebbe dove sta davvero.
    """
    scelti, ignoti = giudici_richiesti(context)
    return ([giudica(nome, giudice, modello, context, chunks, prompt, costo)
             for nome, giudice, modello in scelti], ignoti)


def audit(context: dict) -> dict:
    """Area 9: giudizio LLM sulla citabilità dei passaggi migliori.

    Modalita' (context["llm"]): "auto" attiva il giudizio solo se una
    credenziale e' presente, "on" tenta comunque, "off" non fa nulla.
    E' l'unico modulo che spende denaro: non deve mai partire per
    sbaglio, e dichiara la dimensione dell'invio prima di inviarlo.

    Da U10 i giudici sono piu' d'uno — `context["judge_models"]`,
    `provider[:modello],...` — e ricevono **lo stesso campione e lo
    stesso prompt**: un confronto fra modelli interrogati diversamente
    non direbbe nulla sui modelli. Il dato canonico li porta tutti in
    `judgements`; i campi in cima restano quelli del **primo giudice che
    ha risposto**, per i consumatori scritti prima di U10.

    context["_anthropic_client"] e context["_judge_sessions"], se
    presenti, prendono il posto dei client reali: sono i punti di
    iniezione per i test, che devono poter esercitare tutto il percorso
    senza spendere nulla.
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
                    "Giudizio LLM disattivato (--llm off)", **stato)],
                "judgements": []}

    chunks = seleziona_chunk(context)
    if not chunks:
        return {"score": None, "status": "unavailable",
                "issues": ["Nessun passaggio da valutare"],
                # `no_chunks` come `sd.status.no_pages` e
                # `wcag.status.no_pages`: la chiave nomina la cosa che
                # manca, non il fatto astratto che manchi un ingresso.
                "findings": [_stato("llm.status.no_chunks",
                                    "Nessun passaggio da valutare",
                                    **stato)],
                "judgements": []}

    prompt = costruisci_prompt(context.get("url", ""), chunks)
    costo = costo_stimato(prompt)
    giudizi, ignoti = run_judges(context, chunks, prompt, costo)

    issues: List[str] = []
    rilievi: List[dict] = []
    for nome in ignoti:
        # Un nome sbagliato non deve produrre un referto che tace: chi
        # scrive `--judge-models qwn` otterrebbe l'audit senza giudizio
        # e senza sapere perche'.
        testo = "Giudice sconosciuto: '%s' (noti: %s)" % (
            nome, ", ".join(sorted(JUDGE_PROVIDERS)))
        issues.append(testo)
        rilievi.append(_stato("llm.status.unknown_provider", testo,
                              requested=nome,
                              known=sorted(JUDGE_PROVIDERS), **stato))
    # Con piu' di un giudice ogni issue dice DI CHI e'. La vista
    # compatta di un'area mostra le issues, e in italiano solo quelle:
    # senza il prefisso, cinque righe di due modelli diversi si
    # leggerebbero come il parere di uno solo. Con un giudice solo il
    # prefisso non c'e', perche' non c'e' nulla da distinguere.
    molti = len(giudizi) > 1
    for giudizio in giudizi:
        issues += [("[%s] %s" % (giudizio["provider"], testo)) if molti
                   else testo for testo in giudizio["issues"]]
        rilievi += giudizio["findings"]

    risposti = [g for g in giudizi if g.get("answered")]
    esito: Dict[str, object] = {
        "score": None, "status": "unavailable",
        "issues": issues, "findings": rilievi,
        "judgements": giudizi,
    }
    if risposti:
        primo = risposti[0]
        esito["score"] = primo["score"]
        esito["status"] = primo["status"]
        for campo in ("model", "motivazione", "punti_forti", "punti_deboli",
                      "passaggio_migliore", "chunk_valutati",
                      "costo_stimato", "scarti"):
            esito[campo] = primo[campo]
    return esito
