#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import importlib.util
import os
import sys

from mars_core import DEFAULT_DELAY, DEFAULT_EMBEDDINGS, DEFAULT_TIMEOUT
from mars_core import build_context as core_build_context
from mars_core import describe_chunk, reciprocal_rank_fusion

# ==============================================================================
# CONFIGURAZIONE API & SICUREZZA
# ==============================================================================

SECRET_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" # CAMBIA IN PROD!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="MARS Beacon API",
    description="Meta-fusion, Accessibility, Ranking & Security Audit. Audit SEO, RRF, WCAG e WAPT esposti via REST API.",
    version="2.0.0",
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
        #"hashed_password": hash_password("mars2026"),
        "hashed_password": get_password_hash("mars2026"),
        "disabled": False,
    }
}

# Moduli Registry
MODULES_REGISTRY = [
    ("mars_tech", "1. Tecnica"),
    ("mars_seo", "2. SEO"),
    ("mars_lexical", "3. Lessicale"),
    ("mars_semantic", "4. Semantica"),
    ("mars_schema", "5. Dati Strutturati"),
    ("mars_wcag", "6. Accessibilità"),
    ("mars_wapt", "7. Sicurezza")
]

# ==============================================================================
# MODELLI PYDANTIC
# ==============================================================================

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    """Utente come esce dall'API: senza credenziali."""

    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    """Utente come sta nel DB: aggiunge l'hash, non esce mai di qui."""

    hashed_password: str

class AuditRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 10
    embeddings: str = DEFAULT_EMBEDDINGS
    market: str = "global"
    delay: float = DEFAULT_DELAY
    timeout: int = DEFAULT_TIMEOUT
    i_own_this_domain: bool = Field(
        default=False,
        description="DICHIARAZIONE di proprietà del dominio e di assunzione "
                    "di responsabilità. È l'unico modo per ignorare "
                    "robots.txt; viene registrata nel referto.")

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
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
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
    if user is None:
        raise credentials_exception
    return User(**user.model_dump(exclude={"hashed_password"}))

# ==============================================================================
# HELPERS ESECUTORE AUDIT
# ==============================================================================

def load_external_module(module_name):
    """Carica un modulo di audit dal filesystem.

    La registrazione in sys.modules prima di exec_module() non e'
    facoltativa: senza, un modulo che usa @dataclass insieme a
    "from __future__ import annotations" fallisce con un errore
    incomprensibile, perche' dataclasses risolve le annotazioni
    passando da sys.modules[cls.__module__].
    """
    file_path = f"{module_name}.py"
    if os.path.exists(file_path):
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            return mod
        except Exception as e:
            sys.modules.pop(module_name, None)
            print(f"Errore caricamento {file_path}: {e}")
    return None

def build_context(req: AuditRequest) -> dict:
    """Contesto condiviso da tutti i moduli di una richiesta."""
    context = core_build_context(str(req.url), req.max_pages,
                                 req.embeddings, req.market,
                                 delay=req.delay, timeout=req.timeout,
                                 owner_declaration=req.i_own_this_domain)
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
        return mod.audit(context)
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
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

@app.post("/audit/tech", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_tech(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 1: Tecnica (robots.txt, sitemap, crawler IA)."""
    res = run_single_audit("mars_tech", build_context(req))
    return AuditResponse(module="mars_tech", score=res.get("score"), issues=res.get("issues"), details=res)

@app.post("/audit/seo", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_seo(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 2: SEO (Lighthouse)."""
    res = run_single_audit("mars_seo", build_context(req))
    return AuditResponse(module="mars_seo", score=res.get("score"), issues=res.get("issues"), details=res)

@app.post("/audit/lexical", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_lexical(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 3: Lessicale (BM25 su title, heading, termini)."""
    res = run_single_audit("mars_lexical", build_context(req))
    return AuditResponse(module="mars_lexical", score=None, details=res)

@app.post("/audit/semantic", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_semantic(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 4: Semantica (chunk answer-shaped, vector retrieval)."""
    res = run_single_audit("mars_semantic", build_context(req))
    # Si escludono scores/rank: sono array lunghi quanto il corpus e
    # non servono a chi consuma l'endpoint.
    dettagli = {k: res[k] for k in
                ("answer_shaped_ratio", "answer_shaped_signals", "languages")
                if k in res}
    return AuditResponse(module="mars_semantic", details=dettagli)

@app.post("/audit/schema", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_schema(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 5: Dati strutturati (JSON-LD / Schema.org)."""
    res = run_single_audit("mars_schema", build_context(req))
    return AuditResponse(module="mars_schema", score=res.get("score"), issues=res.get("issues"), details=res)

@app.post("/audit/wcag", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_wcag(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 6: Accessibilità (WCAG)."""
    res = run_single_audit("mars_wcag", build_context(req))
    return AuditResponse(module="mars_wcag", score=res.get("score"), issues=res.get("issues"), details=res)

@app.post("/audit/wapt", response_model=AuditResponse, tags=["Audit Modules"])
async def audit_wapt(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue l'audit dell'Area 7: Sicurezza (WAPT, ZAP CLI o HTTP Headers)."""
    res = run_single_audit("mars_wapt", build_context(req))
    return AuditResponse(module="mars_wapt", score=res.get("score"), issues=res.get("issues"), details=res)

@app.post("/audit/full", response_model=dict, tags=["Audit Modules"])
async def audit_full(req: AuditRequest, current_user: User = Depends(get_current_user)):
    """Esegue tutti gli audit disponibili, calcolando anche la fusione RRF."""
    context = build_context(req)  # una volta sola, per tutti i moduli
    results = {}
    for mod_name, mod_desc in MODULES_REGISTRY:
        try:
            results[mod_name] = run_single_audit(mod_name, context)
        except HTTPException as exc:
            results[mod_name] = {"error": exc.detail}
        except Exception as exc:
            results[mod_name] = {"error": f"{type(exc).__name__}: {exc}"}

    # Calcolo RRF se entrambi i retriever sono attivi
    lex_res = results.get("mars_lexical", {})
    sem_res = results.get("mars_semantic", {})
    if "rank" in lex_res and "rank" in sem_res:
        rrf = reciprocal_rank_fusion([lex_res["rank"], sem_res["rank"]])
        top_3_lex = set(lex_res["rank"][:3])
        top_3_sem = set(sem_res["rank"][:3])
        consensus = len(top_3_lex.intersection(top_3_sem))

        chunks = context["chunks"]  # stesso crawl, nessun ricalcolo
        top = chunks[rrf[0][0]] if rrf and rrf[0][0] < len(chunks) else None
        results["rrf_analysis"] = {
            "consensus_top3": consensus,
            "n_chunks": len(chunks),
            "top_chunk": describe_chunk(top) if top else None,
            "top_chunk_url": top.get("url") if top else None,
            "top_chunk_heading": top.get("heading") if top else None,
        }

    return results

# ==============================================================================
# ESECUZIONE DIRETTA
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    print("Avvio MARS Beacon API Server...")
    print("Documentazione Swagger UI disponibile su: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)