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
import secrets

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

from mars_core import (DEFAULT_DELAY, DEFAULT_EMBEDDINGS, DEFAULT_TIMEOUT,
                       MODULES_REGISTRY, __version__,
                       load_external_module, normalizza_risultato)
from mars_core import build_context as core_build_context
from mars_report import build_report

# ==============================================================================
# CONFIGURAZIONE API & SICUREZZA
# ==============================================================================

SECRET_KEY = os.environ.get("MARS_SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("ATTENZIONE: MARS_SECRET_KEY non impostata. Uso una chiave "
          "effimera: i token scadranno al riavvio. In produzione "
          "esportare MARS_SECRET_KEY.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="MARS Beacon API",
    description="Meta-fusion, Accessibility, Ranking & Security Audit. "
                "Audit SEO, RRF, WCAG e WAPT esposti via REST API.",
    version=__version__,
    contact={"name": "MARS Team"}
)


def get_password_hash(password: str) -> str:
    """Hashing bcrypt. Il costo di calcolo e' voluto: rallenta il brute-force."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Confronto sicuro tra password in chiaro e hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


# Fake DB Utenti (in produzione usa un DB reale)
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "MARS Administrator",
        "email": "admin@mars.local",
        # "hashed_password": hash_password("mars2026"),
        "hashed_password": get_password_hash("mars2026"),
        "disabled": False,
    }
}

# ==============================================================================
# MODELLI PYDANTIC
# ==============================================================================


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = Field(
        default=None,
        description="Account sospeso. Un utente sospeso non ottiene token "
                    "e i token già emessi smettono di valere alla richiesta "
                    "successiva.")


class UserInDB(User):
    hashed_password: str


class Credentials(BaseModel):
    """Credenziali fornite dal chiamante, alternative alle variabili
    d'ambiente del server.

    Sono SecretStr: pydantic le maschera in log, repr e messaggi
    d'errore, cosi' una chiave non finisce in un traceback per
    distrazione. Non vengono mai restituite in risposta.

    Usare solo su HTTPS: nel corpo di una richiesta viaggiano fino al
    server, e su HTTP sarebbero in chiaro sulla rete.
    """

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Abilita il giudizio LLM (area 9) senza impostare "
                    "ANTHROPIC_API_KEY sul server.")
    hf_token: SecretStr | None = Field(
        default=None,
        description="Token Hugging Face, necessario solo per modelli di "
                    "embedding ad accesso limitato o privati. Per i "
                    "modelli pubblici, incluso quello predefinito, non "
                    "serve.")
    zap_api_key: SecretStr | None = Field(
        default=None,
        description="Chiave API del daemon ZAP, se non è stato avviato "
                    "con api.disablekey=true.")
    zap_proxy: str | None = Field(
        default=None,
        description="Indirizzo del daemon ZAP, se diverso da "
                    "http://127.0.0.1:8080.")


class AuditRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 10
    embeddings: str = DEFAULT_EMBEDDINGS
    market: str = "global"
    delay: float = DEFAULT_DELAY
    timeout: int = DEFAULT_TIMEOUT
    queries: list[str] | None = Field(
        default=None,
        description="Query su cui gira la simulazione RRF. Senza, si "
                    "usano query generiche nella lingua prevalente "
                    "del sito.")
    llm: str = Field(
        default="auto",
        pattern="^(auto|on|off)$",
        description="Giudizio LLM sulla citabilità: 'auto' solo con "
                    "ANTHROPIC_API_KEY presente, 'on' tenta comunque, "
                    "'off' mai. È l'unico modulo che comporta una spesa.")
    credentials: Credentials | None = Field(
        default=None,
        description="Credenziali per gli strumenti opzionali. Se assenti "
                    "si usano le variabili d'ambiente del server.")
    max_children: int = Field(
        0, ge=0, le=10000,
        description="Tetto ai link seguiti per pagina dallo spider ZAP, "
                    "che gira solo con i_own_this_domain. 0 = nessun "
                    "tetto, come il default di ZAP.")
    i_own_this_domain: bool = Field(
        default=False,
        description="DICHIARAZIONE di proprietà del dominio e di assunzione "
                    "di responsabilità. È l'unico modo per ignorare "
                    "robots.txt — dal crawler di MARS e dallo spider di "
                    "ZAP, che non lo rispetta — e per l'active scan; "
                    "viene registrata nel referto.")


class AuditResponse(BaseModel):
    module: str
    score: float | None = None
    issues: list[str] | None = None
    details: dict | None = None

# ==============================================================================
# LOGICHE DI AUTENTICAZIONE
# ==============================================================================


def get_user(db, username: str) -> UserInDB | None:
    """Cerca l'utente nel DB. Il risultato contiene l'hash: uso interno."""
    if username in db:
        return UserInDB(**db[username])
    return None


def authenticate_user(fake_db, username: str,
                      password: str) -> UserInDB | None:
    user = get_user(fake_db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if user.disabled:
        return None
    return user


def create_access_token(data: dict,
                        expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Utente autenticato, gia' privato dell'hash.

    La proiezione su User qui e' difesa in profondita': anche un
    endpoint che dimenticasse response_model non potrebbe far uscire
    le credenziali, perche' l'oggetto non le contiene proprio.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(FAKE_USERS_DB, username=username)
    if user is None or user.disabled:
        # Ricontrollato a ogni richiesta, non solo al rilascio del
        # token: i JWT non si revocano e durano 30 minuti, quindi
        # senza questo un account sospeso resterebbe operativo fino
        # alla scadenza. E' l'unico meccanismo di revoca che esiste.
        raise credentials_exception
    return User(**user.model_dump(exclude={"hashed_password"}))

# ==============================================================================
# HELPERS ESECUTORE AUDIT
# ==============================================================================


def _credenziali(req: AuditRequest) -> dict:
    """Credenziali della richiesta come stringhe, per i moduli.

    get_secret_value() si chiama QUI e una volta sola: i moduli
    ricevono stringhe e non devono conoscere pydantic.
    """
    cred = req.credentials
    if cred is None:
        return {}
    estratte = {}
    for nome in ("anthropic_api_key", "hf_token", "zap_api_key"):
        valore = getattr(cred, nome)
        if valore is not None:
            estratte[nome] = valore.get_secret_value()
    if cred.zap_proxy:
        estratte["zap_proxy"] = cred.zap_proxy
    return estratte


def build_context(req: AuditRequest) -> dict:
    """Contesto condiviso da tutti i moduli di una richiesta."""
    context = core_build_context(str(req.url), req.max_pages,
                                 req.embeddings, req.market,
                                 delay=req.delay, timeout=req.timeout,
                                 owner_declaration=req.i_own_this_domain,
                                 max_children=req.max_children,
                                 llm=req.llm, queries=req.queries,
                                 credentials=_credenziali(req))
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Nessuna pagina indicizzata o sito irraggiungibile.")
    return context


def run_single_audit(module_name: str, context: dict) -> dict:
    """Esegue un modulo su un contesto GIA' costruito.

    Prende il contesto, non la richiesta: cosi' /audit/full puo'
    scansionare una volta sola e riusarlo per tutti i moduli.
    """
    mod = load_external_module(module_name)
    if mod and hasattr(mod, 'audit'):
        # Stessa normalizzazione della CLI: un plugin che non
        # restituisce un dict darebbe un 500 sugli endpoint singoli,
        # dove non c'e' il try/except di /audit/full.
        return normalizza_risultato(module_name, mod.audit(context))
    raise HTTPException(
        status_code=404,
        detail=f"Modulo di audit '{module_name}' non trovato nel filesystem.")


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.post("/token", response_model=Token, tags=["Authentication"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Ottieni un token JWT per accedere agli endpoint protetti.
    Credenziali di default: username='admin', password='mars2026'
    """
    user = authenticate_user(FAKE_USERS_DB, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User, tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- Endpoint Audit Specifici ---
#
# `def` e NON `async def`, e non e' una svista (R29). In FastAPI un
# handler `async` gira **sull'event loop**: un audit — che scansiona il
# sito con `session.get()`, dorme per il rate limit, lancia Lighthouse
# con `subprocess.run(timeout=120)` e attende ZAP fino a 900 secondi —
# bloccherebbe l'intero server per tutti gli altri client fino alla
# fine della scansione. Un handler `def` FastAPI lo sposta invece su un
# threadpool.
#
# Misurato sull'applicazione vera, con un `build_context` che dorme due
# secondi e una `/users/me` concorrente:
#
#     async def : la richiesta banale attende  1,71 s
#     def       : attende                      0,01 s
#
# Vale anche per `/token`, che non fa I/O ma verifica una password
# bcrypt: 179 ms di CPU misurati su questa macchina, tenuti fuori
# dall'event loop per la stessa ragione.
#
# `root` e `/users/me` restano `async`: non bloccano, e spostarle sul
# threadpool costerebbe un cambio di contesto per niente.
#
# Un test presidia il vincolo, perche' reintrodurre un `async def` qui
# non farebbe fallire nulla — il comportamento resta corretto, cambia
# solo che il server smette di servire chiunque altro.


@app.post("/audit/tech", response_model=AuditResponse, tags=["Audit Modules"])
def audit_tech(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 1: Tecnica (robots.txt, sitemap, crawler IA)."""
    res = run_single_audit("mars_tech", build_context(req))
    return AuditResponse(module="mars_tech", score=res.get("score"),
                         issues=res.get("issues"), details=res)


@app.post("/audit/seo", response_model=AuditResponse, tags=["Audit Modules"])
def audit_seo(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 2: SEO (Lighthouse)."""
    res = run_single_audit("mars_seo", build_context(req))
    return AuditResponse(module="mars_seo", score=res.get("score"),
                         issues=res.get("issues"), details=res)


@app.post("/audit/lexical", response_model=AuditResponse, tags=["Audit Modules"])
def audit_lexical(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 3: Lessicale (BM25 su title, heading, termini)."""
    res = run_single_audit("mars_lexical", build_context(req))
    return AuditResponse(module="mars_lexical", score=None, details=res)


@app.post("/audit/semantic", response_model=AuditResponse, tags=["Audit Modules"])
def audit_semantic(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 4: Semantica (chunk answer-shaped, vector retrieval)."""
    res = run_single_audit("mars_semantic", build_context(req))
    # Si escludono scores/rank: sono array lunghi quanto il corpus e
    # non servono a chi consuma l'endpoint.
    dettagli = {k: res[k] for k in
                ("answer_shaped_ratio", "answer_shaped_signals",
                 "page_signals", "languages")
                if k in res}
    return AuditResponse(module="mars_semantic", details=dettagli)


@app.post("/audit/schema", response_model=AuditResponse, tags=["Audit Modules"])
def audit_schema(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 5: Dati strutturati (JSON-LD / Schema.org)."""
    res = run_single_audit("mars_schema", build_context(req))
    return AuditResponse(module="mars_schema", score=res.get("score"),
                         issues=res.get("issues"), details=res)


@app.post("/audit/wcag", response_model=AuditResponse, tags=["Audit Modules"])
def audit_wcag(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 6: Accessibilità (WCAG)."""
    res = run_single_audit("mars_wcag", build_context(req))
    return AuditResponse(module="mars_wcag", score=res.get("score"),
                         issues=res.get("issues"), details=res)


@app.post("/audit/wapt", response_model=AuditResponse, tags=["Audit Modules"])
def audit_wapt(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 7: Sicurezza (WAPT via ZAP, o HTTP Headers).

    ZAP si raggiunge parlando la sua API JSON: non passa da `zap-cli`
    ne' dal client ufficiale, ed e' la correzione di R32 al testo — il
    comportamento e' quello dal 2026-08-20 (C9).
    """
    res = run_single_audit("mars_wapt", build_context(req))
    return AuditResponse(module="mars_wapt", score=res.get("score"),
                         issues=res.get("issues"), details=res)


@app.post("/audit/full", response_model=dict, tags=["Audit Modules"])
def audit_full(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue tutti gli audit disponibili, calcolando anche la fusione RRF."""
    context = build_context(req)  # una volta sola, per tutti i moduli
    results = {}
    context["results"] = results  # sintesi: vedi mars_citability
    for mod_name, mod_desc in MODULES_REGISTRY:
        try:
            results[mod_name] = run_single_audit(mod_name, context)
        except HTTPException as exc:
            results[mod_name] = {"error": exc.detail}
        except Exception as exc:
            results[mod_name] = {"error": f"{type(exc).__name__}: {exc}"}

    # Stessa struttura canonica del referto CLI: l'API non ricalcola
    # per conto proprio cio' che mars_report sa gia' produrre, ed
    # espone di conseguenza gli stessi campi.
    referto = build_report(results, context)
    referto["modules"] = results
    return referto


# ==============================================================================
# ESECUZIONE DIRETTA
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    print("Avvio MARS Beacon API Server...")
    print("Documentazione Swagger UI disponibile su: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
