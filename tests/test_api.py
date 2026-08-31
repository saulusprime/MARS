#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — API REST.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import inspect
import json
import os

import pytest
from fastapi.testclient import TestClient

import mars_api
import mars_core
from conftest import pagina

CREDENZIALI = {"username": "admin", "password": "mars2026"}


@pytest.fixture
def crawler_finto(monkeypatch):
    """Crawler che non tocca la rete e conta le scansioni."""
    conteggio = {"crawl": 0}
    PAGINE = {"https://esempio.test/%s" % n: pagina(
        url="https://esempio.test/%s" % n) for n in ("a", "b", "c")}

    class Finto:
        def __init__(self, base_url, max_pages=20, delay=0.5, timeout=10,
                     user_agent=None, owner_declaration=False):
            self.max_pages = max_pages
            # Il crawler vero lo conserva, e robots.txt puo' alzarlo:
            # build_context lo pubblica nel contesto. Un finto che lo
            # scartasse non potrebbe accorgersi di nulla.
            self.delay = delay
            self.skipped = []
            self.discovery = "sitemap"
            self.robots_info = {"found": True, "text": "User-agent: *\n"
                                                       "Allow: /",
                                "sitemaps": []}
            self.sitemap_info = {"found": True, "from_robots": True,
                                 "urls": 3, "with_lastmod": 3,
                                 "unreadable": 0}

        def crawl(self):
            conteggio["crawl"] += 1
            return dict(list(PAGINE.items())[:self.max_pages])

    monkeypatch.setattr(mars_core, "Crawler", Finto)
    return conteggio


@pytest.fixture
def client():
    return TestClient(mars_api.app)


@pytest.fixture
def token(client):
    return client.post("/token", data=CREDENZIALI).json()["access_token"]


@pytest.fixture
def auth(token):
    return {"Authorization": "Bearer %s" % token}


CORPO = {"url": "https://esempio.test/", "embeddings": "none", "delay": 0,
         "llm": "off", "max_pages": 3}


# ----------------------------------------------------------------------
# Autenticazione (R1, R2, R14)
# ----------------------------------------------------------------------

def test_login_riuscito(client):
    """Regressione R1: verify_password era definita due volte e il DB
    conteneva SHA256 dove passlib attendeva bcrypt. Tutti gli endpoint
    protetti erano irraggiungibili."""
    r = client.post("/token", data=CREDENZIALI)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert len(r.json()["access_token"].split(".")) == 3


@pytest.mark.parametrize("dati", [
    {"username": "admin", "password": "sbagliata"},
    {"username": "nessuno", "password": "mars2026"},
])
def test_login_fallito(client, dati):
    assert client.post("/token", data=dati).status_code == 401


def test_users_me_non_espone_l_hash(client, auth):
    """Regressione R2: lo schema pubblicava l'hash bcrypt."""
    r = client.get("/users/me", headers=auth)
    assert r.status_code == 200
    assert "hashed_password" not in r.json()
    assert "hashed_password" not in r.text


def test_get_current_user_non_porta_mai_l_hash(token):
    """Regressione R2, difesa in profondita'.

    Il test sull'endpoint non basta: response_model=User filtra
    comunque, quindi passerebbe anche se la dipendenza restituisse
    l'oggetto interno. Qui si verifica il livello che protegge i
    prossimi endpoint, quelli che qualcuno scrivera' dimenticando
    response_model.
    """
    import asyncio
    utente = asyncio.run(mars_api.get_current_user(token))
    assert isinstance(utente, mars_api.User)
    assert not isinstance(utente, mars_api.UserInDB)
    assert not hasattr(utente, "hashed_password")


#: Gli handler che fanno lavoro BLOCCANTE, e che quindi non devono
#: essere corutine. Scritto per nome invece che dedotto: un endpoint
#: nuovo va deciso, non ereditato da un'euristica.
HANDLER_BLOCCANTI = ("audit_tech", "audit_seo", "audit_perf",
                     "audit_lexical", "audit_semantic", "audit_schema",
                     "audit_wcag", "audit_wapt", "audit_full",
                     "login_for_access_token")


@pytest.mark.parametrize("nome", HANDLER_BLOCCANTI)
def test_gli_handler_bloccanti_non_sono_corutine(nome):
    """R29: in FastAPI un handler `async` gira sull'event loop, quindi un
    audit — crawl, `subprocess.run(timeout=120)`, polling ZAP fino a 900 s
    — bloccherebbe il server per **tutti** gli altri client.

    Misurato sull'applicazione vera con un `build_context` che dorme due
    secondi: una `/users/me` concorrente attendeva 1,71 s con `async
    def` e 0,01 s con `def`. Vale anche per `/token`, che verifica una
    password bcrypt — 179 ms di CPU.

    Il presidio serve perche' rimettere un `async def` **non farebbe
    fallire nulla**: le risposte restano corrette, cambia solo che il
    server smette di servire chiunque altro mentre lavora."""
    assert not inspect.iscoroutinefunction(getattr(mars_api, nome)), \
        "%s fa lavoro bloccante: deve essere `def`, non `async def`" % nome


def test_gli_handler_leggeri_restano_corutine():
    """L'altro verso: root e /users/me non bloccano, e spostarle sul
    threadpool costerebbe un cambio di contesto per niente. Senza questa
    asserzione il vincolo si leggerebbe come «mai async», che non e'."""
    for nome in ("root", "read_users_me"):
        assert inspect.iscoroutinefunction(getattr(mars_api, nome)), nome


def test_ogni_handler_di_audit_e_nell_elenco_dei_bloccanti():
    """L'elenco e' scritto a mano, quindi un endpoint d'audit nuovo
    potrebbe non entrarci e nessuno se ne accorgerebbe. Le rotte le
    conosce l'applicazione: si confrontano con l'elenco."""
    dalle_rotte = {r.endpoint.__name__ for r in mars_api.app.routes
                   if getattr(r, "path", "").startswith("/audit/")}
    assert dalle_rotte <= set(HANDLER_BLOCCANTI), \
        "endpoint d'audit fuori dall'elenco: %s" % (
            dalle_rotte - set(HANDLER_BLOCCANTI))


@pytest.mark.parametrize("intestazioni", [
    {}, {"Authorization": "Bearer spazzatura"}, {"Authorization": "Basic x"},
])
def test_endpoint_protetto_senza_token_valido(client, intestazioni):
    assert client.get("/users/me", headers=intestazioni).status_code == 401


def test_utente_sospeso_non_ottiene_il_token(client, monkeypatch):
    """Regressione R14: il campo disabled non era mai applicato."""
    monkeypatch.setitem(mars_api.FAKE_USERS_DB, "sospeso", {
        "username": "sospeso", "full_name": "S", "email": "s@x",
        "hashed_password": mars_api.get_password_hash("pwd"),
        "disabled": True})
    assert client.post("/token", data={"username": "sospeso",
                                       "password": "pwd"}).status_code == 401


def test_token_gia_emesso_decade_alla_sospensione(client, monkeypatch):
    """I JWT non si revocano e durano 30 minuti: senza il ricontrollo
    in get_current_user un account sospeso resterebbe operativo."""
    utente = {"username": "temp", "full_name": "T", "email": "t@x",
              "hashed_password": mars_api.get_password_hash("pwd"),
              "disabled": False}
    monkeypatch.setitem(mars_api.FAKE_USERS_DB, "temp", utente)
    tok = client.post("/token", data={"username": "temp",
                                      "password": "pwd"}).json()["access_token"]
    h = {"Authorization": "Bearer %s" % tok}
    assert client.get("/users/me", headers=h).status_code == 200
    utente["disabled"] = True
    assert client.get("/users/me", headers=h).status_code == 401


def test_radice_reindirizza_alla_documentazione(client):
    assert client.get("/", follow_redirects=False).status_code == 307


# ----------------------------------------------------------------------
# Endpoint di audit
# ----------------------------------------------------------------------

AREE = ["tech", "seo", "lexical", "semantic", "schema", "wcag", "wapt", "full"]


@pytest.mark.parametrize("area", AREE)
def test_ogni_endpoint_richiede_il_token(client, area):
    assert client.post("/audit/%s" % area, json=CORPO).status_code == 401


@pytest.mark.parametrize("area", AREE)
def test_ogni_endpoint_risponde(client, auth, crawler_finto, area):
    r = client.post("/audit/%s" % area, json=CORPO, headers=auth)
    assert r.status_code == 200


def test_plugin_non_dict_non_da_500(client, auth, crawler_finto,
                                    monkeypatch):
    """Regressione R22, lato API.

    Gli endpoint singoli non hanno il try/except di /audit/full: un
    plugin che restituisce None — il `return` dimenticato — arrivava
    intatto ad AuditResponse e faceva 500. Ora l'anomalia si dichiara
    e la richiesta riesce, come per uno strumento mancante.
    """
    class Rotto:
        @staticmethod
        def audit(context):
            return None

    monkeypatch.setattr(mars_api, "load_external_module",
                        lambda nome: Rotto())
    r = client.post("/audit/tech", json=CORPO, headers=auth)
    assert r.status_code == 200
    assert "invece di un dict" in r.json()["details"]["error"]


def test_audit_perf_esegue_prima_seo_sullo_stesso_contesto(
        client, auth, crawler_finto, monkeypatch):
    """/audit/perf legge le metriche dal referto Lighthouse dell'area
    SEO — stesso run, nessun secondo Lighthouse (I10) — quindi
    l'endpoint esegue prima mars_seo e gli passa il risultato per la
    via di context["results"], la stessa di /audit/full. E' la
    tubatura di R56: ogni anello rotto qui e' silenzioso, l'area
    uscirebbe «non misurato» senza un errore."""
    chiamate = []

    def finto(nome, context):
        chiamate.append(
            (nome, bool((context.get("results") or {}).get("mars_seo"))))
        return {"score": 1.0}

    monkeypatch.setattr(mars_api, "run_single_audit", finto)
    r = client.post("/audit/perf", json=CORPO, headers=auth)
    assert r.status_code == 200
    assert r.json()["module"] == "mars_perf"
    assert [nome for nome, _ in chiamate] == ["mars_seo", "mars_perf"]
    assert chiamate[1][1], "mars_perf non riceve il risultato di mars_seo"


def test_audit_full_scansiona_una_volta_sola(client, auth, crawler_finto):
    """Regressione R5: build_context veniva chiamato per ogni modulo,
    quindi 7 scansioni piu' un'ottava per gli URL. I moduli potevano
    osservare stati diversi del sito."""
    crawler_finto["crawl"] = 0
    client.post("/audit/full", json=CORPO, headers=auth)
    assert crawler_finto["crawl"] == 1


def test_sito_irraggiungibile_da_404(client, auth, monkeypatch):
    """Regressione R5: il try/except inghiottiva l'HTTPException e
    /audit/full rispondeva 200 con sette "Modulo fallito"."""
    class Vuoto:
        def __init__(self, *a, **k):
            self.skipped = []
            self.discovery = "sitemap"
            self.robots_info = {}
            self.sitemap_info = {}

        def crawl(self):
            return {}

    monkeypatch.setattr(mars_core, "Crawler", Vuoto)
    for area in ("tech", "full"):
        assert client.post("/audit/%s" % area, json=CORPO,
                           headers=auth).status_code == 404


def test_url_non_valido_da_422(client, auth):
    assert client.post("/audit/tech", json={"url": "non-un-url"},
                       headers=auth).status_code == 422


def test_llm_valore_non_ammesso(client, auth):
    assert client.post("/audit/tech", json={**CORPO, "llm": "forse"},
                       headers=auth).status_code == 422


# ----------------------------------------------------------------------
# I parametri hanno effetto
# ----------------------------------------------------------------------

def test_max_pages_limita_le_pagine(client, auth, crawler_finto):
    """Regressione: max_pages limitava i CANDIDATI, non le pagine."""
    for n in (1, 2, 3):
        r = client.post("/audit/full", json={**CORPO, "max_pages": n},
                        headers=auth)
        assert r.json()["pages_crawled"] == n


def test_queries_arrivano_alla_simulazione(client, auth, crawler_finto):
    r = client.post("/audit/full",
                    json={**CORPO, "queries": ["alfa", "beta"]}, headers=auth)
    assert [v["query"] for v in r.json()["rrf_simulation"]] == ["alfa", "beta"]


def test_il_piano_arriva_dall_api(client, auth, crawler_finto):
    """/audit/full non ha lavoro suo da fare: il piano nasce dentro
    `build_report`, e `response_model=dict` lo lascia passare intero.

    Vale la pena provarlo comunque: e' l'unica delle tre interfacce che
    non passa da `render_*`, quindi un piano costruito dentro una vista
    invece che nel dato canonico sparirebbe proprio qui.
    """
    piano = client.post("/audit/full", json=CORPO,
                        headers=auth).json()["remediation"]
    assert isinstance(piano, list)
    for voce in piano:
        assert voce["severity"] in ("critical", "warning")
        assert ".status." not in voce["key"]
        assert voce["priority"] >= 1


def test_market_cambia_il_composito(client, auth, crawler_finto):
    def composito(mercato):
        return client.post("/audit/full", json={**CORPO, "market": mercato},
                           headers=auth).json()["citability"]["score"]
    assert composito("cn") != composito("eu")


def test_dichiarazione_di_proprieta_registrata(client, auth, crawler_finto):
    r = client.post("/audit/full", json={**CORPO, "i_own_this_domain": True},
                    headers=auth)
    assert r.json()["robots_ignored"] is True


def test_llm_off_disattiva_il_modulo(client, auth, crawler_finto):
    r = client.post("/audit/full", json={**CORPO, "llm": "off"}, headers=auth)
    assert r.json()["modules"]["mars_llm_judge"]["status"] == "disabled"


# ----------------------------------------------------------------------
# Credenziali
# ----------------------------------------------------------------------

SPIA = "chiave-che-non-deve-mai-uscire-42"


def test_le_credenziali_non_tornano_nelle_risposte(client, auth,
                                                   crawler_finto):
    corpo = {**CORPO, "credentials": {"anthropic_api_key": SPIA,
                                      "hf_token": SPIA, "zap_api_key": SPIA}}
    for area in ("full", "wcag", "wapt"):
        r = client.post("/audit/%s" % area, json=corpo, headers=auth)
        assert SPIA not in r.text, "la chiave e' uscita da /audit/%s" % area


def test_le_credenziali_sono_mascherate_nel_repr():
    req = mars_api.AuditRequest(url="https://x.it",
                                credentials={"anthropic_api_key": SPIA})
    assert SPIA not in repr(req)


def test_lo_schema_dichiara_le_credenziali_writeonly(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    for campo, dati in schema["Credentials"]["properties"].items():
        if campo == "zap_proxy":
            continue
        stringa = dati["anyOf"][0]
        assert stringa["format"] == "password"
        assert stringa["writeOnly"] is True


def test_esempio_valido_e_completo():
    """L'esempio deve restare allineato allo schema, e senza chiavi."""
    percorso = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "audit_request.json")
    with open(percorso, encoding="utf-8") as f:
        esempio = json.load(f)
    req = mars_api.AuditRequest(**{k: v for k, v in esempio.items()
                                   if not k.startswith("_")})
    assert req.url
    campi = set(mars_api.AuditRequest.model_fields)
    assert campi <= set(esempio), "campi non documentati nell'esempio: %s" % (
        campi - set(esempio))
    credenziali = set(mars_api.Credentials.model_fields)
    assert credenziali <= set(esempio["credentials"])
    assert all("SEGNAPOSTO" in v for k, v in esempio["credentials"].items()
               if k.endswith(("key", "token")))


def test_api_max_children_arriva_al_contesto(client, auth, monkeypatch):
    """R56: l'anello che sfuggiva alle mutazioni. L'API e' il secondo
    consumatore degli stessi moduli (principio 4), e un campo che si
    ferma al modello Pydantic e' indistinguibile da uno che funziona.
    """
    visti = {}

    def finto(url, max_pages=10, *a, **k):
        visti.update(k)
        return None

    monkeypatch.setattr(mars_api, "core_build_context", finto)
    client.post("/audit/full", json=dict(CORPO, max_children=19), headers=auth)
    assert visti.get("max_children") == 19


def test_api_rrf_k_arriva_al_contesto(client, auth, monkeypatch):
    """I3, e la stessa lezione di R56: CLI e API sono due interfacce
    sopra lo stesso motore, quindi il k della fusione si passa da
    entrambe o il principio 4 e' una frase."""
    visti = {}

    def finto(url, max_pages=10, *a, **k):
        visti.update(k)
        return None

    monkeypatch.setattr(mars_api, "core_build_context", finto)
    client.post("/audit/full", json=dict(CORPO, rrf_k=10), headers=auth)
    assert visti.get("rrf_k") == 10
    client.post("/audit/full", json=dict(CORPO), headers=auth)
    assert visti.get("rrf_k") == 60, "il default resta quello del paper"


def test_api_un_k_negativo_e_rifiutato(client, auth):
    """La formula divide per (k + posizione + 1): il modello lo ferma
    prima della scansione, come `--rrf-k` da riga di comando."""
    esito = client.post("/audit/full", json=dict(CORPO, rrf_k=-1),
                        headers=auth)
    assert esito.status_code == 422
