#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — fixture condivise.
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
import requests  # noqa: E402

import mars_core  # noqa: E402


class NienteRete(AssertionError, requests.RequestException):
    """Sostituisce ogni richiesta di rete nei test.

    Eredita da entrambe di proposito: un modulo che gestisce
    correttamente gli errori di rete la cattura come RequestException e
    ripiega, cosi' il percorso di ripiego viene esercitato davvero; un
    modulo che NON la gestisce la lascia passare come AssertionError e
    il test fallisce rumorosamente. Un solo meccanismo verifica due
    cose opposte.
    """


HTML_BASE = """<html lang="it"><head><title>Titolo</title></head><body>
<h1>Intestazione principale</h1>
<p>Un paragrafo abbastanza lungo da superare la soglia minima del
chunker, cosi' che la segmentazione produca un passaggio utilizzabile
dai due recuperatori senza artifici.</p>
<h2>Come funziona?</h2>
<p>Un secondo paragrafo, altrettanto lungo, che appartiene a una
sezione diversa e deve quindi finire in un chunk distinto dal primo
secondo la segmentazione per heading.</p>
</body></html>"""


def pagina(html: str = HTML_BASE, url: str = "https://esempio.test/",
           **extra) -> dict:
    """Una pagina come la produce il Crawler, senza toccare la rete."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    titolo = soup.title.get_text(strip=True) if soup.title else ""
    tag_html = soup.find("html")
    canonical = soup.find("link", rel=lambda v: v and "canonical" in (
        v if isinstance(v, list) else [v]))
    dati = {
        "title": titolo,
        "text": soup.get_text(" ", strip=True),
        "headings": [h.get_text(strip=True)
                     for h in soup.find_all(["h1", "h2", "h3"])],
        "html": html,
        "lang": ((tag_html.get("lang") or "") if tag_html else "")[:2],
        "chunks": mars_core.chunk_page(soup, url, titolo),
        "json_ld": [t.get_text(strip=True) for t in soup.find_all(
            "script", type="application/ld+json")],
        "images": [{"alt": i.get("alt"), "aria-label": i.get("aria-label")}
                   for i in soup.find_all("img")],
        "meta_robots": " ".join((m.get("content") or "").strip().lower()
                                for m in soup.find_all("meta")
                                if (m.get("name") or "").strip().lower()
                                in ("robots", "googlebot")),
        "canonical": (canonical.get("href") or "").strip() if canonical else "",
        "x_robots_tag": "",
        # Dalla stessa funzione del crawler, non riscritta: se le due
        # divergessero i controlli statici di mars_wcag girerebbero nei
        # test su una struttura che in produzione non esiste.
        **mars_core.estrai_struttura(soup),
    }
    dati.update(extra)
    return dati


@pytest.fixture
def contesto():
    """Contesto minimo e completo, come lo costruisce build_context."""
    pagine = {"https://esempio.test/": pagina()}
    chunks = [c for p in pagine.values() for c in p["chunks"]]
    return {
        "url": "https://esempio.test/",
        "pages": pagine,
        "urls": list(pagine),
        "chunks": chunks,
        "queries": ["cos'è questo sito", "come funziona"],
        "embeddings_model": "none",
        "force_proxy": True,
        "market": "global",
        "robots_ignored": False,
        "owner_declaration": False,
        "skipped": [],
        "discovery": "sitemap",
        "llm": "off",
        "credentials": {},
        "robots": {"found": True, "text": "User-agent: *\nAllow: /",
                   "sitemaps": []},
        "sitemap": {"found": True, "sources": [], "from_robots": True,
                    "files_read": 1, "index_files": 0, "urls": 2,
                    "with_lastmod": 2, "unreadable": 0},
        "results": {},
    }


@pytest.fixture(autouse=True)
def niente_rete(monkeypatch):
    """Nessun test tocca la rete.

    autouse e' deliberato: un test che sfugga al divieto renderebbe la
    suite lenta e dipendente da un sito esterno, e nessuno se ne
    accorgerebbe finche' quel sito non cambia.
    """
    def vietato(*args, **kwargs):
        raise NienteRete("un test ha tentato una richiesta di rete")

    for nome in ("get", "post", "head", "request"):
        monkeypatch.setattr("requests." + nome, vietato, raising=False)
    monkeypatch.setattr(mars_core, "Crawler", None, raising=False)


@pytest.fixture(autouse=True)
def nessuna_spesa(monkeypatch):
    """L'unica area che spende denaro non deve poter spendere in un test.

    `niente_rete` copre `requests`; l'SDK Anthropic passa da **httpx**, e
    non lo vede. Misurato prima di scrivere questa fixture: un test con
    `ANTHROPIC_API_KEY` nell'ambiente e `llm: "auto"` faceva partire tre
    POST veri verso api.anthropic.com. E' R20 nella stessa forma — si
    neutralizza la LIBRERIA, non il modulo — sull'unico modulo che, se
    sfugge, presenta un conto.

    Si intercetta il **transport** e non `httpx.Client.send`: il
    `TestClient` di FastAPI e' esso stesso un client httpx, con un
    transport suo che parla all'applicazione in memoria. Bloccare `send`
    fermerebbe anche quello; `HTTPTransport` e' esattamente e soltanto la
    rete vera.

    L'asserzione sta DOPO lo yield perche' sollevare non basta: l'SDK
    incapsula qualunque eccezione del transport in un
    `APIConnectionError`, che `mars_llm_judge` gestisce e dichiara. Senza
    il controllo in coda, un test che sfugge finirebbe verde esercitando
    il ramo sbagliato.
    """
    tentati = []

    def vietato(self, request, **kwargs):
        tentati.append(str(request.url))
        raise RuntimeError("un test ha tentato una richiesta HTTP reale")

    # Marcatore: e' l'unico modo che un test ha di verificare che il
    # blocco sia installato senza tentare una richiesta — e chi ci prova
    # fallisce in teardown, non asserisce.
    vietato._mars_blocca_la_rete = True
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", vietato,
                        raising=False)
    yield
    assert not tentati, ("un test ha tentato una richiesta HTTP reale: %s"
                         % tentati)


@pytest.fixture(autouse=True)
def strumenti_esterni_assenti(monkeypatch):
    """Nessun test avvia Lighthouse, ZAP o un browser.

    Senza questa fixture mars_seo lanciava davvero Lighthouse: la
    suite passava da otto secondi a ottantacinque. Le logiche di quei
    moduli sono verificate altrove con dati finti; qui interessa che
    l'assenza degli strumenti sia gestita, che e' anche lo stato piu'
    comune in una pipeline.
    """
    # shutil.which copre Lighthouse e il daemon ZAP non risponde
    # perche' la rete e' vietata.
    monkeypatch.setattr("shutil.which", lambda nome: None)

    # Il browser NON era coperto, e la dichiarazione qui sopra era
    # falsa: misurato con strace, la sola porzione WCAG della suite
    # lanciava 15 volte chrome-headless-shell. La rete vietata non
    # basta, perche' Playwright non passa da requests.
    #
    # Si rende non importabile playwright.sync_api invece di toccare
    # mars_wcag: cosi' la neutralizzazione non dipende da QUALE
    # oggetto-modulo sia vivo (import diretto nei test o
    # load_external_module), e copre entrambe le porte d'ingresso —
    # axe_disponibile() e run_axe() degradano tutte e due.
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
