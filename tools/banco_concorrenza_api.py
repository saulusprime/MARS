"""R29: un audit blocca l'intero server per gli altri client?

    python3 tools/banco_concorrenza_api.py

Non e' in `pytest` e non ci va: apre una porta e fa girare uvicorn, cioe'
esce dall'ambiente che la suite si e' data. Il vincolo dentro la suite e'
un'asserzione statica — gli handler bloccanti non devono essere corutine
(`tests/test_api.py`) — e questo banco e' cio' che dimostra **perche'**
quell'asserzione conti. Stessa scelta di `tools/banco_grafo.py`.

Misurato il 2026-08-26, con una pausa di 2 s dentro `build_context`:

    async def : la richiesta banale attende  1,71 s
    def       : attende                      0,01 s

Si fa girare l'applicazione VERA con uvicorn, con `build_context`
sostituito da una pausa: interessa il modello di concorrenza degli
handler, non la scansione. Poi due richieste in parallelo — l'audit
lento e una `/users/me` che non fa nulla — e si misura quanto attende
la seconda.
"""
import os
import socket
import sys
import threading
import time

os.environ.setdefault("MARS_SECRET_KEY", "banco-di-prova-r29")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx                                            # noqa: E402
import uvicorn                                          # noqa: E402

import mars_api                                         # noqa: E402

PAUSA = 2.0


def _porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _lento(req):
    time.sleep(PAUSA)          # sincrono, come crawl()/subprocess/ZAP
    return {"url": str(req.url), "pages": {}, "chunks": [], "urls": []}


mars_api.build_context = _lento

PORTA = _porta_libera()
server = uvicorn.Server(uvicorn.Config(mars_api.app, host="127.0.0.1",
                                       port=PORTA, log_level="error"))
threading.Thread(target=server.run, daemon=True).start()
BASE = "http://127.0.0.1:%d" % PORTA
for _ in range(100):
    try:
        httpx.get(BASE + "/docs", timeout=1)
        break
    except Exception:
        time.sleep(0.05)

token = httpx.post(BASE + "/token",
                   data={"username": "admin", "password": "mars2026"},
                   timeout=10).json()["access_token"]
intestazioni = {"Authorization": "Bearer " + token}

attese = []


def audit():
    httpx.post(BASE + "/audit/tech", json={"url": "https://esempio.test"},
               headers=intestazioni, timeout=30)


def veloce():
    time.sleep(0.3)            # l'audit e' gia' partito
    t = time.perf_counter()
    httpx.get(BASE + "/users/me", headers=intestazioni, timeout=30)
    attese.append(time.perf_counter() - t)


a = threading.Thread(target=audit)
v = threading.Thread(target=veloce)
a.start()
v.start()
a.join()
v.join()

print("audit bloccante: %.1f s" % PAUSA)
print("attesa di /users/me durante l'audit: %.2f s" % attese[0])
print("verdetto:", "BLOCCA l'event loop" if attese[0] > PAUSA / 2 else "non blocca")
