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
import time
from typing import Dict, List, Optional

import requests

from mars_core import (SEV_INFO, Finding, chiave_esterna,
                       normalizza_severita)

# ZAP si raggiunge come daemon GIA' in esecuzione, non lo si avvia.
# Avviarlo e spegnerlo dal codice significava orchestrare un processo
# Java, con il rischio di lasciarlo orfano dopo un timeout; delegarlo a
# chi lancia l'audit e' piu' semplice e piu' onesto:
#
#   docker run -u zap -p 8080:8080 zaproxy/zap-stable zap.sh -daemon \
#       -host 0.0.0.0 -port 8080 -config api.disablekey=true
ZAP_PROXY = os.environ.get("ZAP_PROXY", "http://127.0.0.1:8080")
ZAP_API_KEY = os.environ.get("ZAP_API_KEY", "")

ZAP_TIMEOUT_SCAN = 900   # secondi per spider + active scan
ZAP_ATTESA = 3           # secondi fra due controlli di avanzamento

# Penalita' per livello di rischio. Scelta editoriale dichiarata: non
# sono calibrate su un corpus di scansioni reali, e finche' non lo
# saranno vanno lette come un ordinamento, non come una misura.
ZAP_PENALTIES = {"High": 25, "Medium": 10, "Low": 3, "Informational": 0}

# Penalita' di un livello di rischio che ZAP introducesse e noi non
# conoscessimo. Era cablata due volte come `2` dentro le `.get()`; ora
# ha un nome, perche' i punti che la usano sono tre e perche' e' un
# valore editoriale, non un dettaglio: un livello nuovo peserebbe 2
# invece di sparire.
#
# Da sapere: la stessa gravita' ignota, passata a
# `normalizza_severita("zap", ...)`, degrada a (info, 1.0). Un rischio
# sconosciuto esce quindi come rilievo `info` che pero' costa punti. Le
# due tabelle vivono in file diversi — questa qui, la scala in
# mars_core — e chi ne aggiornasse una sola non romperebbe nulla: c'e'
# un test che verifica che coprano gli stessi livelli.
PENALITA_IGNOTA = 2

# I tre header del ripiego: penalita', testo della issue, gravita'
# editoriale e chiave stabile del rilievo. L'ordine di dichiarazione e'
# per penalita' decrescente ed e' quello in cui escono sia le issues
# sia i findings — Python conserva l'ordine d'inserimento, e un
# `sorted` aggiuntivo potrebbe riordinare i due pari-merito da una
# parte sola.
#
# Le penalita' sono quelle di sempre, tarate su due punti reali in C9:
# non si toccano. La gravita' invece e' nuova, ed e' una scelta
# EDITORIALE nostra: nessuno strumento ha parlato in questo ramo — ZAP
# non e' stato nemmeno raggiunto — quindi `source_severity` resta vuoto.
#
# Nessuno dei tre e' `critico`. In quest'area `critico` e' riservato a
# una vulnerabilita' sfruttabile constatata; un header di sicurezza
# mancante e' una difesa in profondita' assente, che rende sfruttabile
# UN ALTRO difetto senza esserlo di per se'. E questo ramo, per giunta,
# non ha scansionato nulla: ha letto tre header di una risposta.
# Dichiarare `critical` di li' sarebbe R21 — vendere per misura cio'
# che non lo e'. Lo conferma l'unico strumento con una scala tarata:
# ZAP classifica gli stessi tre fatti Medium (10038 CSP, 10020
# anti-clickjacking) e Low (10035 HSTS), mai High.
#
# Fra `grave` e `medio` decide la monotonia con le penalita', che sono
# gia' tarate: 15 -> grave, 10 -> medio. Cosi' la granularita' che le
# quattro severita' perdono si ritrova nel peso (2.0 contro 1.0), che
# e' la decisione D2 del programma UPGRADE. Conseguenza da conoscere:
# un `grave` dedotto da un solo HEAD pesa 2.0, cioe' PIU' di un Medium
# di ZAP, che pesa 1.0. E' innocuo soltanto perche' i due rami si
# escludono a vicenda; se un giorno convivessero, il confronto andrebbe
# rifatto.
SECURITY_HEADERS = {
    "Strict-Transport-Security": (15, "HSTS mancante", "grave",
                                  "sec.headers.hsts_missing"),
    "Content-Security-Policy": (15, "CSP mancante", "grave",
                                "sec.headers.csp_missing"),
    "X-Frame-Options": (10, "X-Frame-Options mancante", "medio",
                        "sec.headers.xframe_missing"),
}


def _righe(testo: object) -> List[str]:
    """Un campo ZAP a piu' righe, come lista.

    `reference` e' UNA stringa con dentro piu' URL separati da a-capo:
    `DefaultVulnerability.getReferencesAsString()` li unisce con '\\n',
    e i `.refs` dei Messages.properties fanno lo stesso. Metterla in
    `Finding.url`, che e' un link solo, ne mostrerebbe uno e
    nasconderebbe gli altri — la troncatura che il dato canonico
    rifiuta. Si spezza anche su '\\r\\n' perche' ZAP stesso, quando
    quel testo lo impagina, gestisce entrambi.
    """
    grezzo = str(testo or "").replace("\r\n", "\n")
    return [riga.strip() for riga in grezzo.split("\n") if riga.strip()]


#: La lingua in cui ZAP scrive i propri testi. Non e' una scelta:
#: `description` e `solution` vengono dai Messages.properties dello
#: strumento, che non ha traduzioni, e l'API non espone alcun locale.
LINGUA_ZAP = "en"


def _stato(chiave: str, testo: str, **params: object) -> Finding:
    """Un fatto sulla SCANSIONE, non un difetto del sito.

    Sempre `info`, ed e' la decisione piu' discutibile del modulo: una
    scansione scaduta e non fermata lascia del traffico in corso, di
    attacco se l'active scan era abilitato. Ma `severity` e' la
    gravita' del difetto DEL SITO, ed e' l'asse su cui la Fase 4
    ordinera' il piano di interventi: un daemon che non si ferma non si
    ripara cambiando il sito, e alzarne la gravita' lo farebbe risalire
    sopra ogni rilievo reale, in permanenza. E' la stessa ragione per
    cui il referto tiene `info` un'area fallita. L'urgenza la portano
    la posizione — in testa all'elenco — e il testo.

    Nessuna chiave `penalty`: `penalty: 0.0` significa "e' un difetto,
    ma in questo ramo non costa punti"; la chiave assente significa
    "non e' un difetto".
    """
    return Finding(area="mars_wapt", severity=SEV_INFO,
                   key=chiave, title=testo, params=dict(params))


def _rilievo_zap(voce: dict) -> Finding:
    """Un gruppo di alert ZAP come rilievo strutturato.

    `source_severity` resta VUOTO quando ZAP non ha dichiarato il
    rischio: il modulo assume "Informational" per poter comunque
    pesare l'alert, ma e' una NOSTRA assunzione, e scrivere
    "ZAP:Informational" gli attribuirebbe un giudizio che non ha
    espresso. Il livello effettivamente usato per il calcolo resta
    leggibile in `params["risk"]`, cosi' l'assunzione e' auditabile
    invece che invisibile.
    """
    severita, peso = normalizza_severita("zap", voce["risk"])
    return Finding(
        area="mars_wapt", severity=severita, weight=peso,
        key="sec.zap.%s" % chiave_esterna(voce["id"]),
        title=voce["name"],
        detail=voce["description"],
        # La `solution` di ZAP e' testo semplice: i <p> che si vedono
        # nei referti tradizionali li aggiunge il loro generatore, non
        # l'alert. Arriva quindi cosi' com'e' — ripulirla mangerebbe in
        # silenzio i "<meta http-equiv=...>" di cui un testo di
        # sicurezza e' pieno. Chi la stampera' la escapa (Fase 3).
        fix=voce["solution"],
        source_severity=("ZAP:%s" % voce["risk"]
                         if voce["risk_dichiarato"] else ""),
        params={
            # L'id grezzo, fedele allo strumento: `chiave_esterna` non
            # e' iniettiva (un pluginId "-1" e uno "1" danno la stessa
            # chiave), quindi questo e' l'unico dato che non collide.
            "rule": voce["id"],
            # Da quale campo nasce la chiave. Solo `pluginId` la rende
            # stabile: un `name` viene dai Messages.properties, cambia
            # fra due release di ZAP ed e' localizzato.
            "key_source": voce["key_source"],
            "risk": voce["risk"],
            "urls": sorted(voce["urls"]),
            "n": voce["n"],
            # Gli alertRef visti nel gruppo. Il raggruppamento resta
            # per regola — cambiarlo sposterebbe i punteggi, ed e' una
            # ritaratura, non un adeguamento di forma — ma questo e' il
            # dato che permettera' di spezzarlo quando lo si vorra'.
            "alert_refs": sorted(voce["alert_refs"]),
            "references": list(voce["references"]),
            # Quante soluzioni DISTINTE ha il gruppo: `fix` ne porta
            # una sola, e se sono piu' d'una il dato deve dire che e'
            # approssimata invece di lasciarlo credere.
            "soluzioni": len(voce["soluzioni"]),
            "penalty": float(voce["penalty"]),
            # ZAP parla inglese e basta: i suoi Messages.properties non
            # hanno una traduzione italiana, e non c'e' un `--locale`
            # da passargli. Dichiararlo qui permette al referto di
            # dirlo invece di lasciare che il lettore lo scopra
            # leggendo. Costante e non calcolata: e' un fatto sullo
            # strumento, non su questa esecuzione.
            "text_lang": LINGUA_ZAP,
        })


def _rilievo_header(header: str, penalita: int, messaggio: str,
                    gravita: str, chiave: str) -> Finding:
    """Un header di sicurezza mancante, come rilievo strutturato.

    `params["surface"]` dichiara nel DATO cio' che `status: "surface"`
    dichiara nel referto: qui non c'e' stata una scansione, si sono
    letti tre header. Senza il marcatore, un elenco di soli findings
    mostrerebbe un `warning` come se un WAPT ci fosse stato — e' R21
    portato dentro il dato, come nel ripiego di mars_wcag.
    """
    severita, peso = normalizza_severita("mars", gravita)
    return Finding(area="mars_wapt", severity=severita, weight=peso,
                   title=messaggio, key=chiave,
                   # Vuoto: la gravita' l'abbiamo scelta noi, e le
                   # issues di questo ramo non pubblicano prefissi.
                   params={"header": header, "penalty": float(penalita),
                           "surface": True})


def score_from_alerts(alerts: List[dict]) -> dict:
    """Punteggio dagli alert ZAP, raggruppati per REGOLA.

    Raggruppare non e' un dettaglio: ZAP segnala un alert per ogni URL
    interessato, quindi un solo difetto presente su venti pagine
    arriverebbe venti volte e affonderebbe il punteggio da solo. Si
    penalizza la regola violata, con un fattore di diffusione da 1x
    (un URL) a 2x (molti). E' la stessa correzione applicata ad
    axe-core in C8.

    Funzione pura: verificabile senza un daemon ZAP.
    """
    per_regola: Dict[str, dict] = {}
    for alert in alerts:
        # Da QUALE campo nasce l'id conta quanto l'id: solo il
        # pluginId rende la chiave del rilievo stabile nel tempo.
        origine = ""
        for campo in ("pluginId", "alertRef", "name", "alert"):
            if alert.get(campo):
                origine = campo
                break
        chiave = str(alert.get(origine)) if origine else "?"
        # ZAP dichiara il rischio in "risk" e la confidenza in un campo
        # suo, "confidence": il "High (Medium)" che si vede nei referti
        # e' "riskdesc", che esiste solo li'. Lo split resta come
        # difesa verso gli alert che NON vengono dalle regole di serie
        # — script utente, add-on di terzi, alert/action/addAlert —
        # dove il testo e' quello che ne ha scritto l'autore.
        grezzo_rischio = alert.get("risk")
        livello = str(grezzo_rischio or "Informational").split(" ")[0]
        voce = per_regola.setdefault(chiave, {
            "id": chiave,
            "key_source": origine,
            "risk": livello,
            # `risk` assente e' un'assunzione nostra, non un giudizio
            # di ZAP: chi costruisce il Finding deve poterlo dire.
            "risk_dichiarato": bool(grezzo_rischio),
            "name": alert.get("alert") or alert.get("name") or chiave,
            "urls": set(),
            "alert_refs": set(),
            "solution": "",
            "soluzioni": set(),
            "references": [],
            "description": "",
        })
        if alert.get("url"):
            voce["urls"].add(alert["url"])
        if alert.get("alertRef"):
            voce["alert_refs"].add(str(alert["alertRef"]))
        # La `solution` era scartata, ed e' il campo su cui poggia la
        # Fase 3. Si tiene la prima non vuota del gruppo: dentro un
        # pluginId gli alertRef possono averne di diverse, e
        # concatenarle produrrebbe un'istruzione che non e' quella di
        # nessuno dei tre. La sua assenza non e' un errore: esistono
        # alert Informational senza soluzione.
        soluzione = str(alert.get("solution") or "").strip()
        if soluzione:
            voce["soluzioni"].add(soluzione)
            if not voce["solution"]:
                voce["solution"] = soluzione
        if not voce["references"]:
            voce["references"] = _righe(alert.get("reference"))
        # La `description` dice PERCHE' l'alert e' un problema, la
        # `solution` come si chiude: sono due campi distinti in ZAP e
        # restano due campi distinti nel rilievo. Fonderle darebbe alla
        # Fase 4 una prescrizione che comincia con una spiegazione, e
        # il piano di interventi si legge per fare, non per capire.
        # Stessa regola della soluzione — la prima non vuota del
        # gruppo — per la stessa ragione: dentro un pluginId gli
        # alertRef possono averne di diverse.
        descrizione = str(alert.get("description") or "").strip()
        if descrizione and not voce["description"]:
            voce["description"] = descrizione

    penalita = 0.0
    conteggio: Dict[str, int] = {}
    for voce in per_regola.values():
        quanti = max(len(voce["urls"]), 1)
        diffusione = 1.0 + min(quanti, 10) / 10.0
        costo = ZAP_PENALTIES.get(voce["risk"], PENALITA_IGNOTA) * diffusione
        penalita += costo
        conteggio[voce["risk"]] = conteggio.get(voce["risk"], 0) + 1
        # La penalita' si registra QUI, dentro il ciclo che la applica:
        # `diffusione` non esiste altrove, e senza il numero vero la
        # Fase 4 non potrebbe calcolare quanto risalirebbe il punteggio
        # se il rilievo fosse risolto.
        voce["n"] = quanti
        voce["penalty"] = costo

    # L'ordinamento resta per CLASSE di rischio, non per penalita'
    # effettiva, e non va "adeguato" alla convenzione di U1.3: e' lo
    # stesso ordine in cui escono le issues, e ordinare per penalita'
    # scavalcherebbe i pari-classe (un High su 10 URL passerebbe
    # davanti a un High su 1 URL), cambiando testo e ordine di cio' che
    # l'utente legge. Per i quattro livelli noti i due ordini
    # coincidono comunque — High sta in [27.5, 50], Medium in [11, 20],
    # Low in [3.3, 6] — mentre un livello IGNOTO, che costa
    # PENALITA_IGNOTA, sta in [2.2, 4.0] e puo' quindi sovrapporsi a un
    # Low.
    ordinate = sorted(per_regola.values(),
                      key=lambda v: -ZAP_PENALTIES.get(v["risk"],
                                                       PENALITA_IGNOTA))
    # La vista compatta ne mostra cinque; il dato li porta tutti.
    issues = ["[ZAP:%s] %s (%d URL)" % (v["risk"], v["name"], v["n"])
              for v in ordinate[:5]]
    return {"score": max(0, round(100 - penalita)),
            "alerts_by_risk": conteggio,
            "rules_violated": len(per_regola),
            "issues": issues,
            "findings": [_rilievo_zap(v).as_dict() for v in ordinate]}


class ZapClient:
    """Client minimo per l'API JSON di ZAP.

    Scritto a mano invece di usare python-owasp-zap-v2.4 perche' quel
    pacchetto (0.0.14) cabla l'indirizzo "http://zap/" e rifiuta ogni
    altro URL: ZAP 2.17 non serve piu' quell'alias attraverso il
    proxy, quindi il client ufficiale non riesce a collegarsi.
    Verificato sul campo: il proxy inoltra normalmente example.com ma
    chiude la connessione su http://zap/.

    L'API e' un semplice GET che restituisce JSON, e requests e' gia'
    una dipendenza: farlo a mano costa meno che dipendere da un
    wrapper fermo al 2018.
    """

    def __init__(self, base: str = ZAP_PROXY, api_key: str = ZAP_API_KEY,
                 timeout: int = 30):
        self.base = base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _get(self, percorso: str, **parametri) -> dict:
        if self.api_key:
            parametri["apikey"] = self.api_key
        risposta = requests.get("%s/JSON/%s/" % (self.base, percorso),
                                params=parametri, timeout=self.timeout)
        risposta.raise_for_status()
        return risposta.json()

    def version(self) -> str:
        return str(self._get("core/view/version").get("version", ""))

    def spider_scan(self, url: str) -> str:
        return str(self._get("spider/action/scan", url=url).get("scan"))

    def spider_status(self, scan_id: str) -> int:
        return int(self._get("spider/view/status",
                             scanId=scan_id).get("status", 0))

    def ascan_scan(self, url: str) -> str:
        return str(self._get("ascan/action/scan", url=url).get("scan"))

    def ascan_status(self, scan_id: str) -> int:
        return int(self._get("ascan/view/status",
                             scanId=scan_id).get("status", 0))

    # Fermare una scansione non e' un dettaglio di cortesia: senza,
    # allo scadere del timeout MARS smetteva di ASPETTARE e il daemon
    # proseguiva. Per l'active scan significa lasciare in corso l'invio
    # di payload d'attacco contro un sito, senza piu' nessuno che
    # guardi. Verificato su ZAP 2.17.0: fermare una scansione gia'
    # conclusa risponde HTTP 400 {"code":"does_not_exist"}, quindi
    # _get() solleverebbe — chi chiama deve tollerarlo, perche' e' una
    # corsa normale fra l'ultimo controllo e la fermata.
    def spider_stop(self, scan_id: str) -> None:
        self._get("spider/action/stop", scanId=scan_id)

    def ascan_stop(self, scan_id: str) -> None:
        self._get("ascan/action/stop", scanId=scan_id)

    def alerts(self, baseurl: str) -> List[dict]:
        return list(self._get("core/view/alerts",
                              baseurl=baseurl).get("alerts") or [])


def connect_zap(credentials: Optional[dict] = None) -> Optional[ZapClient]:
    """Client ZAP se un daemon risponde, altrimenti None.

    Indirizzo e chiave arrivano prima dalla richiesta, poi
    dall'ambiente: cosi' un'unica istanza dell'API puo' servire
    chiamanti con daemon ZAP diversi.
    """
    credentials = credentials or {}
    client = ZapClient(base=credentials.get("zap_proxy") or ZAP_PROXY,
                       api_key=credentials.get("zap_api_key") or ZAP_API_KEY)
    try:
        if client.version():
            return client
    except (requests.RequestException, ValueError, KeyError):
        # Qualunque cosa vada storta qui significa "niente ZAP": non
        # deve mai interrompere l'audit.
        pass
    return None


def _attendi(stato, scan_id: str, scadenza: float) -> bool:
    """Attende il completamento di una scansione. False se scade."""
    while time.time() < scadenza:
        try:
            if stato(scan_id) >= 100:
                return True
        except (requests.RequestException, ValueError, TypeError):
            return False
        time.sleep(ZAP_ATTESA)
    return False


def _ferma(azione, scan_id: str) -> bool:
    """Ferma una scansione. True se il daemon ha accettato l'ordine.

    Non solleva mai: una scansione che si e' conclusa da sola fra
    l'ultimo controllo e la fermata risponde 400 `does_not_exist`, ed
    e' l'esito buono, non un guasto. Ma il valore restituito NON va
    ignorato: se il daemon non ha accettato, la scansione prosegue e
    il referto deve dirlo invece di dichiararla interrotta.
    """
    try:
        azione(scan_id)
        return True
    except requests.HTTPError as exc:
        # Verificato su ZAP 2.17.0: fermare una scansione che non c'e'
        # piu' risponde 400 {"code": "does_not_exist"}. E' l'esito
        # VOLUTO — quella scansione non sta girando — non un guasto, e
        # succede davvero: fra l'ultimo controllo di avanzamento e la
        # fermata passano fino a ZAP_ATTESA secondi, e la scansione
        # puo' concludersi da sola proprio li'. Confonderlo con un
        # errore farebbe dichiarare al referto che una scansione
        # conclusa sta ancora girando.
        try:
            return exc.response.json().get("code") == "does_not_exist"
        except (ValueError, AttributeError):
            return False
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return False


def run_zap(url: str, client=None,
            active: bool = False) -> Optional[tuple]:
    """Spider, alert e — solo se autorizzato — active scan.

    L'active scan INVIA PAYLOAD D'ATTACCO: XSS, SQL injection, path
    traversal. Contro un sito che non si possiede e' un attacco, e a
    seconda della giurisdizione un reato. Per questo richiede la stessa
    dichiarazione di proprieta' introdotta per ignorare robots.txt.

    Senza dichiarazione si esegue solo lo spider, e gli alert sono
    quelli PASSIVI, ricavati osservando le risposte: header mancanti,
    informazioni divulgate, cookie senza attributi. Utili e innocui.

    Restituisce (alerts, completata, fermate). None se fallisce.
    `fermate` e' False quando una scansione e' scaduta e il daemon non
    ha accettato l'ordine di fermarla: sta ancora girando, e chi scrive
    il referto deve poterlo dire.
    """
    client = client or connect_zap()
    if client is None:
        return None
    scadenza = time.time() + ZAP_TIMEOUT_SCAN
    # Diventa False se una scansione e' scaduta e il daemon non ha
    # accettato l'ordine di fermarla: in quel caso sta ancora girando,
    # e il referto non puo' dichiararla interrotta.
    fermate = True
    try:
        scan_id = client.spider_scan(url)
        spider_ok = _attendi(client.spider_status, scan_id, scadenza)
        if not spider_ok:
            fermate &= _ferma(client.spider_stop, scan_id)

        ascan_ok = True
        if active and time.time() >= scadenza:
            # Avviare un attacco che non si potrebbe sorvegliare e'
            # peggio che non avviarlo: il budget e' uno per spider piu'
            # active scan, e se lo spider l'ha esaurito qui restava
            # comunque un ascan/action/scan, seguito da zero controlli
            # di avanzamento e da nessuna fermata.
            ascan_ok = False
        elif active:
            scan_id = client.ascan_scan(url)
            ascan_ok = _attendi(client.ascan_status, scan_id, scadenza)
            if not ascan_ok:
                fermate &= _ferma(client.ascan_stop, scan_id)

        alerts = client.alerts(url)
        # Gli alert parziali di una scansione interrotta valgono piu'
        # di niente, ma spacciarli per completi no: il chiamante deve
        # poterlo dire nel referto.
        return alerts, (spider_ok and ascan_ok), fermate
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def audit_headers(url: str) -> dict:
    """Ripiego: controllo di superficie sui soli header HTTP.

    Non e' un WAPT. Lo status "surface" lo dichiara a chi legge il
    referto, cosi' che 100/100 qui non venga scambiato per un sito
    scansionato e trovato pulito.
    """
    # HEAD prima, GET come ripiego: non tutti i server implementano
    # HEAD, e alcuni rispondono 405 o 501. Leggere gli header di
    # quella risposta e concluderne che mancano tutti sarebbe un
    # verdetto falso dato con sicurezza.
    resp = None
    for metodo in (requests.head, requests.get):
        try:
            tentativo = metodo(url, allow_redirects=True, timeout=10)
        except requests.RequestException as exc:
            errore = type(exc).__name__
            continue
        errore = None
        if tentativo.status_code < 400:
            resp = tentativo
            break
    if resp is None:
        dettaglio = errore or "HTTP %d" % tentativo.status_code
        return {"score": None, "status": "unavailable", "tool": "HTTP-Headers",
                "issues": ["Header non leggibili: %s" % dettaglio],
                # Anche un'area non misurata porta il proprio rilievo:
                # altrimenti e' l'unica a sparire dagli elenchi che le
                # fasi successive costruiranno sui findings. E' uno
                # STATO, non un difetto, quindi niente `penalty`; il
                # motivo sta in `detail`, che e' un nome di eccezione o
                # un codice HTTP — mai l'indirizzo del proxy o la
                # chiave, che escono dall'API dentro `details`.
                "findings": [Finding(
                    area="mars_wapt", severity=SEV_INFO,
                    key="sec.status.unreadable",
                    title="Header non leggibili",
                    detail=dettaglio).as_dict()]}

    score = 100
    issues = []
    rilievi: List[Finding] = []
    for header, dati in SECURITY_HEADERS.items():
        penalita, messaggio, gravita, chiave = dati
        if header not in resp.headers:
            issues.append(messaggio)
            score -= penalita
            rilievi.append(_rilievo_header(header, penalita, messaggio,
                                           gravita, chiave))
    return {"score": max(0, score), "status": "surface",
            "tool": "HTTP-Headers", "issues": issues,
            # Nessun `sorted`: issues e findings escono dallo stesso
            # ciclo, e riordinarne uno solo li farebbe raccontare la
            # stessa risposta in due ordini diversi.
            "findings": [f.as_dict() for f in rilievi]}


def audit(context: dict) -> dict:
    """Area 7: sicurezza, con ZAP quando un daemon e' raggiungibile."""
    url = context["url"]
    credenziali = context.get("credentials") or {}
    client = context.get("_zap_client") or connect_zap(credenziali)
    if client is not None:
        active = bool(context.get("owner_declaration"))
        print("  ZAP raggiunto su %s: scansione %s in corso "
              "(puo' richiedere diversi minuti)..."
              % (credenziali.get("zap_proxy") or ZAP_PROXY,
                 "ATTIVA" if active else "passiva"))
        esito_zap = run_zap(url, client, active=active)
        if esito_zap is not None:
            alerts, completa, fermate = esito_zap
            esito = score_from_alerts(alerts)
            issues = list(esito["issues"])
            # I rilievi di stato rispecchiano ESATTAMENTE la posizione
            # delle issues corrispondenti: in testa quelli di timeout,
            # in coda la nota sulla scansione passiva. Le due viste
            # sono la stessa informazione per due lettori, e se
            # raccontassero la scansione in due ordini diversi non si
            # potrebbero piu' confrontare.
            testa: List[Finding] = []
            coda: List[Finding] = []
            if not completa and fermate:
                issues.insert(0, "Scansione ZAP interrotta dal timeout e "
                                 "fermata: i rilievi sono parziali")
                testa.append(_stato(
                    "sec.status.partial",
                    "Scansione ZAP interrotta dal timeout e fermata: i "
                    "rilievi sono parziali",
                    stopped=True, active_scan=active))
            elif not completa:
                # Il caso peggiore, e prima era l'unico: MARS ha smesso
                # di aspettare, il daemon no. Dirlo, perche' chi legge
                # deve sapere che c'e' ancora traffico in corso — di
                # attacco, se l'active scan era abilitato.
                issues.insert(0, "Scansione ZAP scaduta e NON fermata: "
                                 "prosegue nel daemon ZAP, e i rilievi "
                                 "qui sono parziali")
                # Chiave DISTINTA da sec.status.partial, non un flag su
                # una chiave sola: sono due fatti diversi — una
                # scansione conclusa in anticipo e del traffico ancora
                # in corso — ed e' esattamente cio' che R27 esiste per
                # non confondere. `not_stopped` e' inoltre la negazione
                # del campo `stopped` che il dict gia' pubblica: chiave
                # e campo non possono raccontare due storie.
                testa.append(_stato(
                    "sec.status.not_stopped",
                    "Scansione ZAP scaduta e NON fermata: prosegue nel "
                    "daemon ZAP, e i rilievi qui sono parziali",
                    stopped=False, active_scan=active))
            if not active:
                issues.append("Solo scansione passiva: l'active scan "
                              "richiede --i-own-this-domain")
                coda.append(_stato(
                    "sec.status.passive_only",
                    "Solo scansione passiva: l'active scan richiede "
                    "--i-own-this-domain",
                    active_scan=False))
            return {"score": esito["score"],
                    "tool": "ZAP (attiva)" if active else "ZAP (passiva)",
                    "complete": completa, "active_scan": active,
                    # Distingue "interrotta" da "abbandonata": senza,
                    # il referto dichiarava interrotta una scansione
                    # che stava ancora girando.
                    "stopped": fermate,
                    "alerts_by_risk": esito["alerts_by_risk"],
                    "rules_violated": esito["rules_violated"],
                    "issues": issues,
                    "findings": ([f.as_dict() for f in testa]
                                 + esito["findings"]
                                 + [f.as_dict() for f in coda])}
        print("  ZAP non ha completato: ripiego sui soli header HTTP.")
    return audit_headers(url)
