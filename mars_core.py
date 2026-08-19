#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

import math
from collections import defaultdict
from typing import Optional, Tuple
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

_ST_CACHE = None  # None = non ancora tentato; False = non disponibile


def load_sentence_transformers() -> Optional[Tuple[object, object]]:
    """Importa sentence-transformers solo quando serve davvero.

    L'import trascina torch e costa circa 3 secondi: pagarlo all'avvio
    penalizzerebbe chi usa il proxy char-tfidf, gli altri moduli di
    audit e mars_citations.py. Restituisce (SentenceTransformer,
    cosine_similarity) oppure None se il pacchetto non c'e'.
    """
    global _ST_CACHE
    if _ST_CACHE is None:
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            _ST_CACHE = (SentenceTransformer, cosine_similarity)
        except ImportError:
            _ST_CACHE = False
    return _ST_CACHE or None


def norm_host(url_or_host: str) -> str:
    """Host normalizzato: minuscolo, senza www., senza schema."""
    value = url_or_host.strip().lower()
    if "://" in value:
        value = urlparse(value).netloc or value
    value = value.split("/")[0].split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    return value


def host_matches(url: str, target_host: str) -> bool:
    """True se l'URL appartiene all'host (sottodomini inclusi)."""
    host = norm_host(url)
    return host == target_host or host.endswith("." + target_host)

class Crawler:
    def __init__(self, base_url, max_pages=20):
        self.base_url = base_url
        self.max_pages = max_pages
        self.pages = {}

    def fetch_sitemap(self):
        sitemap_url = urljoin(self.base_url, "/sitemap.xml")
        try:
            resp = requests.get(sitemap_url, timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                urls = [elem.text for elem in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                return urls[:self.max_pages]
        except Exception:
            pass
        return []

    def crawl(self):
        urls = self.fetch_sitemap()
        if not urls:
            urls = [self.base_url]
        
        for url in urls[:self.max_pages]:
            try:
                resp = requests.get(url, timeout=10)
                soup = BeautifulSoup(resp.text, 'lxml')
                title = soup.title.string if soup.title else ""
                text = soup.get_text(separator=" ", strip=True)
                
                self.pages[url] = {
                    "title": title,
                    "text": text,
                    "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
                    "html": resp.text
                }
            except Exception as e:
                print(f"Errore nel crawling di {url}: {e}")
        return self.pages

class LexicalRetriever:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self._build_index()

    def _build_index(self):
        df = defaultdict(int)
        for doc in self.corpus:
            self.doc_len.append(len(doc))
            freqs = defaultdict(int)
            for token in doc:
                freqs[token] += 1
            self.doc_freqs.append(freqs)
            for token in set(doc):
                df[token] += 1
                
        for token, freq in df.items():
            self.idf[token] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def get_scores(self, query):
        scores = []
        for i in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_len[i]
            for token in query:
                if token in self.idf:
                    tf = self.doc_freqs[i].get(token, 0)
                    idf = self.idf[token]
                    score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
            scores.append(score)
        return scores

class VectorRetriever:
    def __init__(self, corpus, model_name="paraphrase-multilingual-MiniLM-L12-v2", force_proxy=False):
        self.corpus = corpus
        st = None if force_proxy else load_sentence_transformers()
        self.use_real = st is not None

        if self.use_real:
            model_cls, self._cosine = st
            print(f"  Caricamento modello SentenceTransformer: {model_name}...")
            self.model = model_cls(model_name)
            self.embeddings = self.model.encode(self.corpus)
        else:
            print("  Utilizzo proxy Char-TFIDF.")
            self.vocab = {}
            self.doc_vecs = []
            self._build_proxy()

    def _get_ngrams(self, text, n=3):
        text = text.lower().replace(" ", "")
        return [text[i:i+n] for i in range(len(text) - n + 1)]

    def _build_proxy(self):
        df = defaultdict(int)
        for doc in self.corpus:
            ngrams = set(self._get_ngrams(doc))
            for ng in ngrams:
                df[ng] += 1
        idx = 0
        for ng in df:
            self.vocab[ng] = idx
            idx += 1
            
        for doc in self.corpus:
            vec = [0.0] * len(self.vocab)
            ngrams = self._get_ngrams(doc)
            freq = defaultdict(int)
            for ng in ngrams: freq[ng] += 1
            for ng, count in freq.items():
                if ng in self.vocab:
                    tf = count / len(ngrams) if ngrams else 0
                    idf = math.log((len(self.corpus) + 1) / (df[ng] + 1)) + 1
                    vec[self.vocab[ng]] = tf * idf
            self.doc_vecs.append(vec)

    def get_scores(self, query):
        if self.use_real:
            q_emb = self.model.encode([query])
            return self._cosine(q_emb, self.embeddings)[0].tolist()
        
        q_ngrams = self._get_ngrams(query)
        freq = defaultdict(int)
        for ng in q_ngrams: freq[ng] += 1
        q_vec = [0.0] * len(self.vocab)
        for ng, count in freq.items():
            if ng in self.vocab:
                tf = count / len(q_ngrams) if q_ngrams else 0
                idf = math.log((len(self.corpus) + 1) / (sum(1 for d in self.corpus if ng in self._get_ngrams(d)) + 1)) + 1
                q_vec[self.vocab[ng]] = tf * idf
                
        scores = []
        q_norm = math.sqrt(sum(v*v for v in q_vec))
        if q_norm == 0: return [0.0] * len(self.corpus)
            
        for doc_vec in self.doc_vecs:
            d_norm = math.sqrt(sum(v*v for v in doc_vec))
            if d_norm == 0:
                scores.append(0.0)
                continue
            dot = sum(q_vec[i] * doc_vec[i] for i in range(len(q_vec)))
            scores.append(dot / (q_norm * d_norm))
        return scores

CHUNK_CHARS = 500  # troncamento provvisorio: non e' ancora un chunker


def build_context(url: str, max_pages: int = 10,
                  embeddings_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
                  market: str = "global") -> Optional[dict]:
    """Scansiona il sito UNA volta e prepara il contesto per i moduli.

    Unica fonte di verita' per CLI e API: prima ognuna costruiva il
    proprio dizionario, e l'API lo rifaceva per ogni modulo. Un solo
    crawl non serve solo a risparmiare richieste — serve perche' i
    moduli devono osservare lo stesso stato del sito, altrimenti i loro
    punteggi non sono confrontabili fra loro.

    Restituisce None se il sito e' irraggiungibile: tradurre l'assenza
    in un errore HTTP spetta al chiamante, non a questo modulo.
    """
    pages = Crawler(url, max_pages).crawl()
    if not pages:
        return None
    return {
        "url": url,
        "pages": pages,
        "urls": list(pages.keys()),
        "chunks": [p["text"][:CHUNK_CHARS] for p in pages.values()],
        "embeddings_model": embeddings_model,
        "force_proxy": embeddings_model.lower() == "none",
        "market": market,
    }


def reciprocal_rank_fusion(rankings, k=60):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking):
            scores[doc_idx] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)