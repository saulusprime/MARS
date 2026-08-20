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
def strumenti_esterni_assenti(monkeypatch):
    """Nessun test avvia Lighthouse, ZAP o un browser.

    Senza questa fixture mars_seo lanciava davvero Lighthouse: la
    suite passava da otto secondi a ottantacinque. Le logiche di quei
    moduli sono verificate altrove con dati finti; qui interessa che
    l'assenza degli strumenti sia gestita, che e' anche lo stato piu'
    comune in una pipeline.
    """
    # shutil.which copre Lighthouse; il daemon ZAP e il browser di axe
    # non rispondono perche' la rete e' vietata, ed e' esattamente il
    # percorso di ripiego che vogliamo esercitare. Non si applicano
    # patch ai moduli d'area: load_external_module li riesegue a ogni
    # chiamata, quindi una patch sull'oggetto importato qui non
    # sopravviverebbe.
    monkeypatch.setattr("shutil.which", lambda nome: None)
