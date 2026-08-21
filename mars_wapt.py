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

SECURITY_HEADERS = {
    "Strict-Transport-Security": (15, "HSTS mancante"),
    "Content-Security-Policy": (15, "CSP mancante"),
    "X-Frame-Options": (10, "X-Frame-Options mancante"),
}


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
        chiave = str(alert.get("pluginId") or alert.get("alertRef")
                     or alert.get("name") or alert.get("alert") or "?")
        # ZAP usa "risk": "High"; alcune versioni "High (Medium)",
        # dove il secondo valore e' la confidenza.
        livello = str(alert.get("risk") or "Informational").split(" ")[0]
        voce = per_regola.setdefault(chiave, {
            "risk": livello,
            "name": alert.get("alert") or alert.get("name") or chiave,
            "urls": set(),
        })
        if alert.get("url"):
            voce["urls"].add(alert["url"])

    penalita = 0.0
    conteggio: Dict[str, int] = {}
    for voce in per_regola.values():
        quanti = max(len(voce["urls"]), 1)
        diffusione = 1.0 + min(quanti, 10) / 10.0
        penalita += ZAP_PENALTIES.get(voce["risk"], 2) * diffusione
        conteggio[voce["risk"]] = conteggio.get(voce["risk"], 0) + 1

    ordinate = sorted(per_regola.values(),
                      key=lambda v: -ZAP_PENALTIES.get(v["risk"], 2))
    issues = ["[ZAP:%s] %s (%d URL)"
              % (v["risk"], v["name"], max(len(v["urls"]), 1))
              for v in ordinate[:5]]
    return {"score": max(0, round(100 - penalita)),
            "alerts_by_risk": conteggio,
            "rules_violated": len(per_regola),
            "issues": issues}


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
                "issues": ["Header non leggibili: %s" % dettaglio]}

    score = 100
    issues = []
    for header, (penalita, messaggio) in SECURITY_HEADERS.items():
        if header not in resp.headers:
            issues.append(messaggio)
            score -= penalita
    return {"score": max(0, score), "status": "surface",
            "tool": "HTTP-Headers", "issues": issues}


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
            if not completa and fermate:
                issues.insert(0, "Scansione ZAP interrotta dal timeout e "
                                 "fermata: i rilievi sono parziali")
            elif not completa:
                # Il caso peggiore, e prima era l'unico: MARS ha smesso
                # di aspettare, il daemon no. Dirlo, perche' chi legge
                # deve sapere che c'e' ancora traffico in corso — di
                # attacco, se l'active scan era abilitato.
                issues.insert(0, "Scansione ZAP scaduta e NON fermata: "
                                 "prosegue nel daemon ZAP, e i rilievi "
                                 "qui sono parziali")
            if not active:
                issues.append("Solo scansione passiva: l'active scan "
                              "richiede --i-own-this-domain")
            return {"score": esito["score"],
                    "tool": "ZAP (attiva)" if active else "ZAP (passiva)",
                    "complete": completa, "active_scan": active,
                    # Distingue "interrotta" da "abbandonata": senza,
                    # il referto dichiarava interrotta una scansione
                    # che stava ancora girando.
                    "stopped": fermate,
                    "alerts_by_risk": esito["alerts_by_risk"],
                    "rules_violated": esito["rules_violated"],
                    "issues": issues}
        print("  ZAP non ha completato: ripiego sui soli header HTTP.")
    return audit_headers(url)
