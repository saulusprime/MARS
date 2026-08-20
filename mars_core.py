#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

import gzip
import importlib.util
import json
import math
import os
import sys
import time
import unicodedata
from collections import defaultdict
from types import ModuleType
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag, UnicodeDammit

# Identificarsi e' la prima regola della buona educazione fra crawler:
# "python-requests/2.x" viene bloccato da molti siti, e giustamente.
# Quando il progetto avra' una pagina pubblica, va aggiunta qui.
__version__ = "2.0.0"

# La versione compare nello User-Agent, in --version e nell'API:
# tenerla in un posto solo evita che le tre divergano.
USER_AGENT = "MARSBeacon/%s" % __version__
DEFAULT_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 10
HTML_TYPES = ("text/html", "application/xhtml+xml")
MAX_SITEMAP_DEPTH = 3
MAX_REDIRECT = 5      # quanti ne segue Googlebot prima di rinunciare
MAX_CODA = 2000       # tetto alla coda di scoperta, non alle pagine
# Quanti URL candidati raccogliere per ogni pagina richiesta. Servono
# di piu' delle pagine volute perche' molti candidati vengono scartati
# a valle: duplicati dopo la normalizzazione, host esterni, vietati da
# robots.txt, 404, risorse non HTML. Limitare i candidati a max_pages
# faceva consumare il budget a URL che non diventavano mai pagine.
CANDIDATI_PER_PAGINA = 5
SCHEMI_NON_HTTP = ("#", "mailto:", "tel:", "javascript:", "data:")

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
    """Host normalizzato: minuscolo, senza www., senza schema.

    L'IPv6 letterale va riconosciuto PRIMA di tagliare sui due punti:
    e' pieno di due punti, e "[2001:db8::1]".split(":")[0] restituisce
    "[2001". Due indirizzi diversi si riducevano cosi' alla stessa
    stringa, e host_matches() li dava per lo stesso host — il filtro
    same-host che R7 e R17 hanno costruito saltava proprio dove
    serviva.
    """
    value = url_or_host.strip().lower()
    if "://" in value:
        value = urlparse(value).netloc or value
    value = value.split("/")[0]
    if value.startswith("["):
        chiusura = value.find("]")
        if chiusura != -1:
            return value[:chiusura + 1]
    value = value.split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    return value


def host_matches(url: str, target_host: str) -> bool:
    """True se l'URL appartiene all'host (sottodomini inclusi)."""
    host = norm_host(url)
    return host == target_host or host.endswith("." + target_host)


MODULES_REGISTRY = [
    ("mars_tech", "1. Tecnica"),
    ("mars_seo", "2. SEO"),
    ("mars_lexical", "3. Lessicale"),
    ("mars_semantic", "4. Semantica"),
    ("mars_schema", "5. Dati Strutturati"),
    ("mars_wcag", "6. Accessibilità"),
    ("mars_wapt", "7. Sicurezza"),
    # La sintesi va per ultima: legge context["results"].
    ("mars_citability", "8. Citabilità IA"),
    # Ultimo: e' l'unico modulo che spende denaro.
    ("mars_llm_judge", "9. Giudizio LLM"),
]


# Moduli gia' caricati: nome -> (firma del file, modulo).
# La firma e' (mtime in nanosecondi, dimensione): se il file cambia si
# ricarica, cosi' modificare un plugin ha effetto senza riavviare l'API.
_MODULI: Dict[str, Tuple[Tuple[int, int], ModuleType]] = {}


def load_external_module(module_name: str) -> Optional[ModuleType]:
    """Carica un modulo di audit dalla cartella di MARS.

    Il percorso e' relativo a __file__, non alla directory di lavoro:
    lanciato da un'altra cartella il programma non trovava nessun
    modulo e stampava "ignorato" per tutte e sette le aree, producendo
    un referto vuoto senza un solo errore.

    La registrazione in sys.modules prima dell'esecuzione non e'
    facoltativa: senza, un modulo che usa @dataclass insieme a
    "from __future__ import annotations" fallisce con un errore
    incomprensibile, perche' dataclasses risolve le annotazioni
    passando da sys.modules[cls.__module__].

    Il risultato e' in cache. Non per velocita': il costo misurato era
    0,8 ms per audit, nulla accanto a una scansione. Il punto e' che
    due chiamate restituivano oggetti DIVERSI, quindi un isinstance
    contro una classe del modulo falliva e lo stato di modulo veniva
    azzerato a ogni richiesta.
    """
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             f"{module_name}.py")
    try:
        stato = os.stat(file_path)
    except OSError:
        _MODULI.pop(module_name, None)
        return None

    firma = (stato.st_mtime_ns, stato.st_size)
    in_cache = _MODULI.get(module_name)
    if in_cache is not None and in_cache[0] == firma:
        return in_cache[1]

    try:
        with open(file_path, encoding="utf-8") as sorgente:
            testo = sorgente.read()
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        # Si compila la sorgente invece di usare exec_module(): il
        # bytecode cache di Python valida su (mtime in SECONDI interi,
        # dimensione), quindi un file modificato nello stesso secondo e
        # della stessa lunghezza — cambiare una cifra, invertire un
        # booleano — verrebbe eseguito nella versione vecchia, senza un
        # solo errore. Compilare costa nulla e toglie la sorpresa.
        exec(compile(testo, file_path, "exec"), mod.__dict__)
    except Exception as e:
        sys.modules.pop(module_name, None)
        _MODULI.pop(module_name, None)
        print(f"Errore caricamento {file_path}: {e}")
        return None

    _MODULI[module_name] = (firma, mod)
    return mod


def normalizza_risultato(module_name: str, res: object) -> dict:
    """Il risultato di un plugin, ricondotto al contratto.

    Il contratto e' audit(context) -> dict. Un plugin che restituisce
    altro — tipicamente None, per un `return` dimenticato — faceva
    cadere la costruzione del referto DOPO che tutti i moduli erano
    girati: l'audit intero perso per la distrazione di un plugin, con
    un AttributeError incomprensibile e fuori dai codici di uscita
    documentati.

    Si dichiara l'anomalia e si prosegue, che e' la stessa scelta gia'
    fatta per gli strumenti mancanti: il referto perde un'area, non
    tutto. Vive qui perche' CLI e API caricano gli stessi plugin.
    """
    if isinstance(res, dict):
        return res
    return {"error": "%s ha restituito %s invece di un dict"
                     % (module_name, type(res).__name__)}


def errore_modulo(exc: BaseException) -> dict:
    """Un'eccezione di plugin come risultato d'area.

    Perche' il referto possa dire "questa area e' fallita, ed ecco
    perche'" invece di non nominarla affatto.
    """
    return {"error": "%s: %s" % (type(exc).__name__, exc)}


def _local_name(tag: str) -> str:
    """Nome del tag senza namespace: le sitemap reali ne usano di vari."""
    return tag.rsplit("}", 1)[-1]


def normalize_url(url: str) -> str:
    """URL confrontabile: senza frammento, host minuscolo, porta implicita.

    Serve a non trattare /a e /a#top come due pagine distinte, che
    finirebbero due volte nel corpus falsando BM25.
    """
    parts = urlsplit(url.strip())
    host = parts.hostname or ""
    if ":" in host:
        # parts.hostname toglie le parentesi quadre a un IPv6
        # letterale, ma senza quelle l'URL ricomposto e' invalido e
        # ogni richiesta fallisce: "http://::1:8080/x" non e' un
        # indirizzo, e' una diagnosi sbagliata che segue.
        host = "[%s]" % host
    default = {"http": 80, "https": 443}.get(parts.scheme.lower())
    if parts.port and parts.port != default:
        host = "%s:%d" % (host, parts.port)
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/",
                       parts.query, ""))


def safe_normalize_url(url: str, base: Optional[str] = None) -> Optional[str]:
    """URL normalizzato, oppure None se non e' analizzabile.

    Gli URL da normalizzare arrivano dal sito analizzato — un href, un
    <loc> di sitemap — quindi sono dato ostile, non un errore di
    programmazione. Una porta non numerica ("http://x:port/") o un
    IPv6 malformato ("http://[::1/") fanno sollevare ValueError, e
    propagata quell'eccezione faceva cadere l'audit INTERO, buttando
    via anche le pagine gia' scaricate: scartare il singolo URL e
    dichiararlo costa incomparabilmente meno.

    L'urljoin per gli URL relativi sta DENTRO la guardia perche'
    solleva anche lui, prima ancora che normalize_url venga chiamata.
    """
    try:
        return normalize_url(urljoin(base, url) if base else url)
    except ValueError:
        return None


# I soli BOM che lo standard HTML impone di riconoscere. Quando c'e',
# il BOM vince su qualunque dichiarazione: e' il caso classico della
# pagina scritta su Windows e servita da un server che dichiara ancora
# latin-1. Misurato: known_definite_encodings di UnicodeDammit NON gli
# cede il passo, quindi il BOM va guardato prima.
BOM_HTML = ((b"\xef\xbb\xbf", "utf-8-sig"),
            (b"\xff\xfe", "utf-16"),
            (b"\xfe\xff", "utf-16"))


def _charset_dichiarato(content_type: str) -> str:
    """Il charset dell'header Content-Type, se c'e'."""
    for parametro in content_type.split(";")[1:]:
        chiave, _, valore = parametro.partition("=")
        if chiave.strip().lower() == "charset":
            return valore.strip().strip("'\"")
    return ""


def decode_html(content: bytes, content_type: str = "") -> str:
    """Decodifica una pagina come farebbe un browser.

    NON si usa resp.text: requests applica a ogni "text/*" privo di
    charset il default legacy di RFC 2616, cioe' ISO-8859-1. Su un sito
    UTF-8 servito senza charset nell'header — configurazione comunissima
    — questo significa title, heading, testo, chunk e HTML grezzo che
    entrano CORROTTI nel corpus, senza un solo errore: BM25, proxy
    char-TFIDF, RRF e referto lavorano tutti su mojibake. HTML5 ha
    abbandonato quel default esattamente per questa ragione.

    Si applica l'ordine dello standard: BOM, poi il charset dell'header,
    poi <meta charset> o rilevamento statistico. Gli ultimi due li fa
    UnicodeDammit, che BeautifulSoup porta gia' con se': nessuna
    dipendenza nuova.
    """
    for firma, codifica in BOM_HTML:
        if content.startswith(firma):
            return content.decode(codifica, "replace")
    dichiarato = _charset_dichiarato(content_type)
    # user_encodings mette UTF-8 in prova prima del <meta> e del
    # rilevamento statistico. Il tentativo e' AUTOVERIFICANTE: i byte
    # accentati di una pagina davvero latin-1 non sono UTF-8 valido,
    # quindi fallisce e si prosegue con gli altri candidati.
    # Due effetti misurati, non uno:
    #  - su una pagina da 80 KB senza dichiarazioni si passa da 175 ms
    #    a 0,06, perche' il rilevamento non parte affatto;
    #  - una pagina con <meta charset> STANTIO (dice latin-1, i byte
    #    sono UTF-8: il residuo tipico di una migrazione) smette di
    #    produrre mojibake. Cercavo la velocita' e ho trovato anche
    #    questo.
    dammit = UnicodeDammit(
        content, is_html=True,
        known_definite_encodings=[dichiarato] if dichiarato else [],
        user_encodings=["utf-8"])
    if dammit.unicode_markup is not None:
        return dammit.unicode_markup
    # Nessuna codifica ha retto: meglio qualche carattere sostituito che
    # perdere la pagina.
    return content.decode("utf-8", "replace")


class Crawler:
    """Scansione di un sito via sitemap.

    Rispetta robots.txt, si identifica, mette una pausa fra le
    richieste e scarta cio' che non e' HTML servito con successo.
    """

    def __init__(self, base_url: str, max_pages: int = 20,
                 delay: float = DEFAULT_DELAY,
                 timeout: int = DEFAULT_TIMEOUT,
                 user_agent: str = USER_AGENT,
                 owner_declaration: bool = False):
        """owner_declaration: chi lancia l'audit dichiara di essere il
        proprietario del dominio e se ne assume la responsabilita'.
        E' l'unico modo per ignorare robots.txt: non e' un interruttore
        di comodo ma una dichiarazione, ed e' registrata nel referto.
        """
        self.base_url = base_url
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.user_agent = user_agent
        self.owner_declaration = owner_declaration
        self.base_host = norm_host(base_url)
        self.pages: dict = {}
        self.skipped: List[str] = []
        self._url_illeggibili: set = set()
        # URL gia' esaminati. Vive sul crawler e non dentro crawl()
        # perche' _scarica_pagina deve poterlo consultare PRIMA di
        # seguire un redirect: e' cosi' che la richiesta doppia non
        # parte affatto.
        self._visti: set = set()
        self.discovery = "sitemap"
        # Dati grezzi su robots.txt e sitemap: mars_tech li
        # legge invece di rifare le stesse richieste.
        self.robots_info: dict = {}
        self.sitemap_info: dict = {}
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._robots: Optional[RobotFileParser] = None
        self._last_request = 0.0

    # -- rete -----------------------------------------------------

    def _get(self, url: str,
             allow_redirects: bool = True) -> requests.Response:
        """GET con User-Agent, timeout e pausa rispetto alla richiesta
        precedente.

        I redirect si seguono da soli per robots.txt e le sitemap, che
        non sono pagine da indicizzare (e per robots.txt RFC 9309
        chiede esplicitamente di seguirli). Le pagine passano invece da
        _scarica_pagina(), che controlla ogni salto.
        """
        attesa = self.delay - (time.monotonic() - self._last_request)
        if attesa > 0:
            time.sleep(attesa)
        self._last_request = time.monotonic()
        return self.session.get(url, timeout=self.timeout,
                                allow_redirects=allow_redirects)

    def _scarica_pagina(
            self, url: str) -> Optional[Tuple[requests.Response, str]]:
        """Scarica una pagina seguendo i redirect UNO A UNO.

        requests li seguirebbe da solo, ma allora l'URL di arrivo non
        verrebbe mai ricontrollato, e un redirect basterebbe al sito
        per farci scaricare un percorso Disallow o per farci
        indicizzare come nostro il contenuto di un altro host.

        Il controllo sta PRIMA del salto, non dopo: verificare
        resp.url a cose fatte eviterebbe di indicizzare la pagina, ma
        la richiesta vietata sarebbe gia' partita — e il crawler
        avrebbe comunque disobbedito a robots.txt.

        Restituisce (risposta, URL finale), oppure None dopo aver
        registrato il motivo in skipped.
        """
        corrente = url
        percorso = {url}
        for _ in range(MAX_REDIRECT + 1):
            resp = self._get(corrente, allow_redirects=False)
            if not resp.is_redirect:
                return resp, corrente
            posizione = (resp.headers.get("Location") or "").strip()
            if not posizione:
                # Location assente o vuota: urljoin la risolverebbe
                # nell'URL di partenza, e il salto a vuoto verrebbe
                # riportato come "troppi redirect" — diagnosi sbagliata
                # sul difetto sbagliato.
                self.skipped.append(
                    "redirect senza destinazione: %s" % corrente)
                return None
            destinazione = safe_normalize_url(posizione, corrente)
            if destinazione is None:
                self.skipped.append(
                    "redirect verso URL non analizzabile: %s -> %s"
                    % (corrente, posizione))
                return None
            if destinazione in percorso:
                # Il tetto sui salti lo fermerebbe comunque, ma dopo
                # aver chiesto cinque volte la stessa cosa al sito.
                self.skipped.append("redirect circolare: %s" % destinazione)
                return None
            if destinazione in self._visti:
                # /vecchia e /nuova entrambe in sitemap, con la prima
                # che redirige sulla seconda. Il controllo sta qui e
                # non a valle perche' a valle la pagina sarebbe gia'
                # stata scaricata due volte (misurato).
                self.skipped.append("duplicato dopo redirect: %s -> %s"
                                    % (url, destinazione))
                return None
            percorso.add(destinazione)
            if not host_matches(destinazione, self.base_host):
                self.skipped.append("redirect verso host esterno: %s -> %s"
                                    % (corrente, destinazione))
                return None
            if not self.can_fetch(destinazione):
                self.skipped.append(
                    "redirect verso URL vietato da robots.txt: %s -> %s"
                    % (corrente, destinazione))
                return None
            corrente = destinazione
        self.skipped.append("piu' di %d redirect: %s" % (MAX_REDIRECT, url))
        return None

    # -- robots.txt -----------------------------------------------

    def robots(self) -> RobotFileParser:
        """robots.txt del sito, letto una volta sola.

        parse() va chiamato SEMPRE, anche quando il file manca: un
        RobotFileParser mai popolato risponde False a ogni can_fetch(),
        e il crawler non scaricherebbe nulla senza dire perche'.
        """
        if self._robots is None:
            self._robots = RobotFileParser()
            righe: List[str] = []
            # Esistenza e contenuto sono cose diverse: un robots.txt
            # servito a 200 ma vuoto significa "tutto permesso", ed e'
            # una scelta del sito. Dedurre l'esistenza dal contenuto lo
            # faceva riportare come assente, che e' un'altra cosa.
            trovato = False
            try:
                resp = self._get(urljoin(self.base_url, "/robots.txt"))
                if resp.status_code == 200:
                    trovato = True
                    # robots.txt e' UTF-8 per RFC 9309, ma viaggia come
                    # text/plain: resp.text lo decodificherebbe in
                    # ISO-8859-1 come le pagine (vedi decode_html), e
                    # una direttiva Sitemap: con un IDN ne uscirebbe
                    # storpiata.
                    righe = resp.content.decode(
                        "utf-8", "replace").splitlines()
            except requests.RequestException:
                pass
            self._robots.parse(righe)
            self.robots_info = {
                "found": trovato,
                "text": "\n".join(righe),
                "sitemaps": list(self._robots.site_maps() or []),
            }
            ritardo = (self._robots.crawl_delay(self.user_agent)
                       or self._robots.crawl_delay("*"))
            if ritardo:
                # crawl_delay() non eredita da "*" verso un agente
                # specifico: si guardano entrambi e si prende il piu'
                # prudente fra quello del sito e il nostro.
                self.delay = max(self.delay, float(ritardo))
        return self._robots

    def can_fetch(self, url: str) -> bool:
        if self.owner_declaration:
            return True
        return self.robots().can_fetch(self.user_agent, url)

    # -- scarti ---------------------------------------------------

    def _scarta_illeggibile(self, url: str) -> None:
        """Registra un URL non analizzabile, una volta sola.

        Lo stesso href rotto in un template compare su OGNI pagina del
        sito: senza deduplicazione riempirebbe il referto ripetendo la
        stessa riga, e "cosa non e' stato guardato" diventerebbe
        illeggibile proprio dove serve.
        """
        if url not in self._url_illeggibili:
            self._url_illeggibili.add(url)
            self.skipped.append("URL non analizzabile: %s" % url)

    # -- sitemap --------------------------------------------------

    def sitemap_urls(self) -> List[str]:
        """Sitemap dichiarate in robots.txt, altrimenti /sitemap.xml."""
        dichiarate = list(self.robots().site_maps() or [])
        return dichiarate or [urljoin(self.base_url, "/sitemap.xml")]

    def _read_sitemap(self, url: str) -> Optional[ET.Element]:
        try:
            resp = self._get(url)
            if resp.status_code != 200:
                return None
            dati = resp.content
            if dati[:2] == b"\x1f\x8b":  # sitemap compressa (.xml.gz)
                dati = gzip.decompress(dati)
            return ET.fromstring(dati)
        except (requests.RequestException, ET.ParseError, OSError, ValueError):
            return None

    def fetch_sitemap(self) -> List[str]:
        """URL dalla sitemap, seguendo gli indici annidati."""
        trovati: List[str] = []
        con_lastmod = indici = illeggibili = 0
        tetto = min(max(self.max_pages * CANDIDATI_PER_PAGINA, 50), MAX_CODA)
        coda = [(u, 0) for u in self.sitemap_urls()]
        visti = set()
        while coda and len(trovati) < tetto:
            url, profondita = coda.pop(0)
            if url in visti or profondita > MAX_SITEMAP_DEPTH:
                continue
            visti.add(url)
            root = self._read_sitemap(url)
            if root is None:
                illeggibili += 1
                continue
            indice = _local_name(root.tag) == "sitemapindex"
            if indice:
                indici += 1
            for elem in root.iter():
                nome = _local_name(elem.tag)
                if nome == "lastmod" and elem.text:
                    con_lastmod += 1
                if nome != "loc" or not elem.text:
                    continue
                # Risolti rispetto alla sitemap che li contiene: lo
                # standard vuole <loc> assoluti, ma le sitemap reali
                # ne hanno di relativi, e presi alla lettera venivano
                # scartati come "host esterno" — motivo falso, e'
                # lo stesso host — lasciando l'audit senza pagine.
                loc = urljoin(url, elem.text.strip())
                if indice:
                    coda.append((loc, profondita + 1))
                elif len(trovati) < tetto:
                    trovati.append(loc)
        self.sitemap_info = {
            "found": bool(trovati),
            "sources": self.sitemap_urls(),
            "from_robots": bool(self.robots().site_maps()),
            "files_read": len(visti),
            "index_files": indici,
            "urls": len(trovati),
            "with_lastmod": con_lastmod,
            "unreadable": illeggibili,
        }
        return trovati

    # -- scoperta dei link ----------------------------------------

    def estrai_link(self, soup: BeautifulSoup, base: str) -> List[str]:
        """Link interni della pagina, normalizzati e filtrati.

        Il filtro same-host e la normalizzazione sono gli stessi usati
        per gli URL della sitemap: la scoperta per link non e' una
        seconda strada che aggira le regole, e' la stessa strada con
        una sorgente diversa.
        """
        trovati = []
        for ancora in soup.find_all("a", href=True):
            href = (ancora.get("href") or "").strip()
            if not href or href.lower().startswith(SCHEMI_NON_HTTP):
                continue
            url = safe_normalize_url(href, base)
            if url is None:
                self._scarta_illeggibile(href)
                continue
            if url.startswith(("http://", "https://")) \
                    and host_matches(url, self.base_host):
                trovati.append(url)
        return trovati

    # -- scansione ------------------------------------------------

    def crawl(self) -> dict:
        if self.owner_declaration:
            print("  \u26a0 Dichiarazione di proprieta' attiva su %s: "
                  "robots.txt ignorato." % self.base_host)
        da_sitemap = self.fetch_sitemap()
        # La sitemap, quando c'e', e' la dichiarazione del sito su cosa
        # vuole far indicizzare: si rispetta e non si va a caccia di
        # altro. Senza, si scopre seguendo i link interni.
        self.discovery = "sitemap" if da_sitemap else "link interni"
        segui_link = not da_sitemap
        coda = list(da_sitemap) or [self.base_url]
        visti = self._visti = set()

        while coda and len(self.pages) < self.max_pages:
            grezzo = coda.pop(0)  # FIFO: ampiezza, non profondita'
            richiesto = safe_normalize_url(grezzo)
            if richiesto is None:
                # Un <loc> di sitemap malformato non e' un errore
                # nostro: si scarta questo URL, non l'audit.
                self._scarta_illeggibile(grezzo)
                continue
            if richiesto in visti:
                continue
            visti.add(richiesto)

            if not host_matches(richiesto, self.base_host):
                self.skipped.append("host esterno: %s" % richiesto)
                continue
            if not self.can_fetch(richiesto):
                self.skipped.append("vietato da robots.txt: %s" % richiesto)
                continue

            try:
                esito = self._scarica_pagina(richiesto)
            except requests.RequestException as exc:
                print("Errore nel crawling di %s: %s" % (richiesto, exc))
                continue
            if esito is None:
                continue    # il motivo l'ha gia' registrato _scarica_pagina

            # Da qui in avanti conta l'URL di ARRIVO: e' li' che il
            # contenuto vive davvero, ed e' quello che va messo nei
            # chunk e confrontato con i canonical.
            resp, url = esito
            visti.add(url)   # l'arrivo, cosi' non lo si richiede dopo

            if resp.status_code != 200:
                # Senza questo controllo la pagina d'errore entrava nel
                # corpus BM25 e falsava i ranking.
                self.skipped.append("HTTP %d: %s" % (resp.status_code, url))
                continue
            tipo = resp.headers.get("Content-Type", "")
            tipo = tipo.split(";")[0].strip().lower()
            if tipo and tipo not in HTML_TYPES:
                self.skipped.append("non HTML (%s): %s" % (tipo, url))
                continue

            # Si decodifica UNA volta e si parsa quella stringa: cosi'
            # il DOM e l'HTML grezzo conservato non possono divergere.
            testo_html = decode_html(resp.content,
                                     resp.headers.get("Content-Type", ""))
            soup = BeautifulSoup(testo_html, "lxml")
            # get_text() invece di .string: su <title></title>
            # .string e' None (non ""), e quel None propagava fino a
            # un TypeError dentro " ".join() in mars_lexical,
            # facendo cadere il modulo lessicale e con esso l'RRF.
            title = soup.title.get_text(strip=True) if soup.title else ""
            html_tag = soup.find("html")
            lingua = (html_tag.get("lang") or "") if html_tag else ""
            self.pages[url] = {
                "title": title,
                # Estratti qui, dove il DOM e' gia' in memoria: prima
                # mars_schema e mars_wcag riparsavano l'HTML ciascuno
                # per conto suo, tre parse per pagina invece di uno.
                # Si estraggono DATI grezzi, non giudizi: decidere cosa
                # sia un difetto resta compito dei moduli.
                "chunks": chunk_page(soup, url, title),
                "json_ld": [t.get_text(strip=True) for t in soup.find_all(
                    "script", type="application/ld+json")],
                # Indicizzabilita': meta robots, canonical e l'header
                # X-Robots-Tag, che agisce come il meta ma non e' nel DOM.
                "meta_robots": " ".join(
                    (m.get("content") or "").strip().lower()
                    for m in soup.find_all("meta")
                    if (m.get("name") or "").strip().lower()
                    in ("robots", "googlebot")),
                "canonical": (lambda t: (t.get("href") or "").strip()
                              if t else "")(
                    soup.find("link", rel=lambda v: v and "canonical" in
                              (v if isinstance(v, list) else [v]))),
                "x_robots_tag": resp.headers.get(
                    "X-Robots-Tag", "").strip().lower(),
                "images": [{"alt": i.get("alt"),
                            "aria-label": i.get("aria-label")}
                           for i in soup.find_all("img")],
                # Letto qui una volta sola: serve a mars_wcag (criterio
                # WCAG 3.1.1) e a mars_semantic per scegliere i termini
                # interrogativi giusti.
                "lang": lingua.strip().lower()[:2],
                "text": soup.get_text(separator=" ", strip=True),
                "headings": [h.get_text(strip=True)
                             for h in soup.find_all(["h1", "h2", "h3"])],
                "html": testo_html,
            }

            if segui_link and len(coda) < MAX_CODA:
                # urljoin sull'URL di ARRIVO, non su quello richiesto:
                # dopo un redirect i link relativi si risolvono
                # rispetto a dove si e' finiti.
                for link in self.estrai_link(soup, url):
                    if link not in visti:
                        coda.append(link)
        return self.pages


def _spoglia(token: str) -> str:
    """Toglie la punteggiatura in TESTA e in CODA a un token.

    Si guarda la categoria Unicode invece di elencare i caratteri:
    l'elenco ASCII dimentica «», “”, ‘’, —, …, ¿, che nei testi reali
    ci sono eccome. Le categorie "P*" li coprono tutte per costruzione.

    I simboli (categoria "S") restano: "C++" e "C#" sono nomi, non
    parole con un segno appiccicato, e "€" da solo non fa danno.
    """
    inizio, fine = 0, len(token)
    while inizio < fine and unicodedata.category(token[inizio])[0] == "P":
        inizio += 1
    while fine > inizio and unicodedata.category(token[fine - 1])[0] == "P":
        fine -= 1
    return token[inizio:fine]


def tokenize(testo: str) -> List[str]:
    """Testo in token per il recuperatore lessicale.

    Vive qui e non in mars_lexical perche' corpus e query DEVONO
    passare per la stessa funzione: se divergono, la query smette di
    trovare cio' che l'indice contiene, ed e' un difetto invisibile
    perche' non produce errori, solo punteggi sbagliati.

    Prima si faceva .lower().split(), quindi "funziona?" restava un
    token diverso da "funziona": il chunk che conteneva davvero la
    frase cercata non prendeva alcun credito per quella parola, e con
    la normalizzazione BM25 sulla lunghezza poteva finire SOTTO un
    chunk che la parola non ce l'aveva. Colpiva soprattutto i passaggi
    in forma di domanda, cioe' proprio quelli che il progetto vuole
    premiare.

    Si toglie solo la punteggiatura di CONFINE: "e-mail", "COVID-19",
    "3,14" e "info@esempio.it" restano interi, perche' spezzarli
    sarebbe una scelta diversa e non misurata (vedi I15).
    """
    return [t for t in (_spoglia(p) for p in testo.lower().split()) if t]


class LexicalRetriever:
    def __init__(self, corpus: List[List[str]], k1: float = 1.5,
                 b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self._build_index()

    def _build_index(self) -> None:
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

    def get_scores(self, query: List[str]) -> List[float]:
        """Punteggio BM25 di ogni documento per la query tokenizzata."""
        # Guardia esplicita: con avgdl a 0 la formula BM25 dividerebbe
        # per zero. Oggi non accade perche' avgdl e' 0 solo se tutti i
        # documenti sono vuoti, e allora idf e' vuoto e il ciclo interno
        # non entra mai — una protezione accidentale, non voluta.
        if not self.avgdl:
            return [0.0] * self.corpus_size
        scores = []
        for i in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_len[i]
            for token in query:
                if token in self.idf:
                    tf = self.doc_freqs[i].get(token, 0)
                    idf = self.idf[token]
                    norm = self.k1 * (1 - self.b
                                      + self.b * doc_len / self.avgdl)
                    score += idf * (tf * (self.k1 + 1)) / (tf + norm)
            scores.append(score)
        return scores


class VectorRetriever:
    def __init__(self, corpus: List[str],
                 model_name: str = DEFAULT_EMBEDDINGS,
                 force_proxy: bool = False,
                 hf_token: Optional[str] = None):
        self.corpus = corpus
        st = None if force_proxy else load_sentence_transformers()
        self.use_real = st is not None

        if self.use_real:
            model_cls, self._cosine = st
            print(f"  Caricamento modello SentenceTransformer: {model_name}...")
            # token= serve solo per i modelli ad accesso limitato o
            # privati dell'Hub; per quelli pubblici e' ininfluente.
            # Senza, huggingface_hub legge comunque HF_TOKEN
            # dall'ambiente da solo.
            self.model = (model_cls(model_name, token=hf_token) if hf_token
                          else model_cls(model_name))
            self.embeddings = self.model.encode(self.corpus)
        else:
            print("  Utilizzo proxy Char-TFIDF.")
            self.df: dict = {}
            self.doc_vecs: List[dict] = []
            self.doc_norms: List[float] = []
            self._build_proxy()

    def _get_ngrams(self, text: str, n: int = 3) -> List[str]:
        text = text.lower().replace(" ", "")
        return [text[i:i+n] for i in range(len(text) - n + 1)]

    def _idf(self, ngram: str) -> float:
        """IDF di un n-gramma, dalla document frequency conservata."""
        return math.log(
            (len(self.corpus) + 1) / (self.df.get(ngram, 0) + 1)) + 1

    def _build_proxy(self) -> None:
        """Indice SPARSO: di ogni documento si tengono solo gli
        n-grammi che contiene.

        I vettori densi [0.0] * len(vocab) sprecavano N x V float: con
        80 pagine e un vocabolario di 17.000 trigrammi sono 1,4 milioni
        di celle, quasi tutte zero.

        Le document frequency finiscono in self.df invece di essere
        buttate via: get_scores() le ricalcolava ri-tokenizzando
        l'INTERO corpus per ogni n-gramma della query.
        """
        df: dict = defaultdict(int)
        for doc in self.corpus:
            for ng in set(self._get_ngrams(doc)):
                df[ng] += 1
        self.df = df

        for doc in self.corpus:
            ngrams = self._get_ngrams(doc)
            freq: dict = defaultdict(int)
            for ng in ngrams:
                freq[ng] += 1
            totale = len(ngrams)
            vec = {ng: (count / totale) * self._idf(ng)
                   for ng, count in freq.items()} if totale else {}
            self.doc_vecs.append(vec)
            # Norma calcolata una volta sola: prima veniva rifatta a
            # ogni query, per ogni documento.
            self.doc_norms.append(
                math.sqrt(sum(v * v for v in vec.values())))

    def get_scores(self, query: str) -> List[float]:
        """Similarita' di ogni documento con la query.

        Coseno sugli embedding reali se disponibili, altrimenti sul
        proxy char-TFIDF: il chiamante non deve sapere quale dei due
        sia attivo.
        """
        if self.use_real:
            q_emb = self.model.encode([query])
            return self._cosine(q_emb, self.embeddings)[0].tolist()

        q_ngrams = self._get_ngrams(query)
        if not q_ngrams:
            return [0.0] * len(self.corpus)
        freq: dict = defaultdict(int)
        for ng in q_ngrams:
            freq[ng] += 1
        q_vec = {ng: (count / len(q_ngrams)) * self._idf(ng)
                 for ng, count in freq.items() if ng in self.df}

        q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
        if not q_norm:
            return [0.0] * len(self.corpus)

        scores = []
        for vec, d_norm in zip(self.doc_vecs, self.doc_norms):
            if not d_norm:
                scores.append(0.0)
                continue
            # Si itera la query (poche decine di n-grammi) cercando nel
            # documento, non il vocabolario intero: qui il costo per
            # documento passa da O(V) a O(|q|).
            dot = sum(peso * vec.get(ng, 0.0)
                      for ng, peso in q_vec.items())
            scores.append(dot / (q_norm * d_norm))
        return scores


CHUNK_CHARS = 1000     # lunghezza massima di un chunk
CHUNK_OVERLAP = 150    # sovrapposizione fra finestre consecutive
MIN_CHUNK_CHARS = 120  # sotto, non e' un passaggio autoconsistente
HEADINGS = ("h1", "h2", "h3")
NON_CONTENUTO = ("script", "style", "noscript", "template")


def split_windows(testo: str, size: int = CHUNK_CHARS,
                  overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Spezza un testo lungo in finestre sovrapposte.

    La sovrapposizione serve a non tagliare a meta' un'affermazione:
    un passaggio citabile deve reggersi da solo anche se la frase
    iniziava poco prima del taglio.
    """
    if len(testo) <= size:
        return [testo]
    finestre = []
    inizio = 0
    while inizio < len(testo):
        fine = inizio + size
        if fine < len(testo):
            # taglio su confine di parola, se ce n'e' uno vicino
            spazio = testo.rfind(" ", inizio + size - 120, fine)
            if spazio > inizio:
                fine = spazio
        finestre.append(testo[inizio:fine].strip())
        if fine >= len(testo):
            break
        inizio = max(fine - overlap, inizio + 1)
    return [f for f in finestre if f]


DEFAULT_MAX_QUERIES = 15

# Query generiche usate quando --queries non e' passato. Quattro
# intenti che quasi ogni sito dovrebbe saper soddisfare; sono un punto
# di partenza dichiarato, non un benchmark: le query che contano sono
# quelle del dominio, e si passano con --queries.
QUERY_GENERICHE = {
    "it": ("cos'è questo sito", "come funziona",
           "chi siamo", "quali servizi offre"),
    "en": ("what is this site about", "how does it work",
           "who we are", "what services do you offer"),
    "es": ("qué es este sitio", "cómo funciona",
           "quiénes somos", "qué servicios ofrece"),
    "fr": ("qu'est-ce que ce site", "comment ça marche",
           "qui sommes-nous", "quels services proposez-vous"),
    "de": ("was ist diese website", "wie funktioniert es",
           "wer wir sind", "welche leistungen bieten sie"),
}


def default_queries(pages: dict) -> List[str]:
    """Query generiche nella lingua prevalente del sito.

    Interrogare un sito inglese in italiano produce un consenso RRF
    basso che non dice nulla sul sito: dice solo che le domande erano
    nella lingua sbagliata. Lingua ignota: si usano italiano e inglese.
    """
    conteggio: dict = defaultdict(int)
    for pagina in (pages or {}).values():
        codice = (pagina.get("lang") or "")[:2]
        if codice in QUERY_GENERICHE:
            conteggio[codice] += 1
    if not conteggio:
        return list(QUERY_GENERICHE["it"]) + list(QUERY_GENERICHE["en"])
    prevalente = max(conteggio, key=lambda k: conteggio[k])
    return list(QUERY_GENERICHE[prevalente])


def load_queries(path: Optional[str] = None,
                 report_path: Optional[str] = None,
                 max_queries: int = DEFAULT_MAX_QUERIES
                 ) -> Tuple[List[str], str]:
    """Query da un file, oppure dal referto JSON di un audit.

    Condivisa fra mars_audit.py e mars_citations.py: le stesse query
    che guidano la simulazione RRF devono poter guidare il
    monitoraggio delle citazioni, altrimenti i due strumenti misurano
    cose diverse e i confronti non significano nulla.

    Restituisce (query, errore): errore vuoto se e' andata bene.

    Dal referto accetta sia `rrf_simulation` (voci con chiave "query",
    o stringhe) sia un `queries` di primo livello: il formato lo fissa
    C4, e leggere entrambe le forme evita di doverla riscrivere.
    """
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                righe = [r.strip() for r in handle if r.strip()]
            return righe[:max_queries], ""
        except OSError as exc:
            return [], "Impossibile leggere %s: %s" % (path, exc)

    if report_path:
        try:
            with open(report_path, encoding="utf-8") as handle:
                referto = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return [], "Referto non leggibile %s: %s" % (report_path, exc)
        grezze = referto.get("rrf_simulation") or referto.get("queries") or []
        query = []
        for voce in grezze:
            testo = voce.get("query") if isinstance(voce, dict) else voce
            if isinstance(testo, str) and testo.strip():
                query.append(testo.strip())
        if not query:
            return [], ("Nessuna query nel referto %s "
                        "(attese in 'rrf_simulation' o 'queries')"
                        % report_path)
        return query[:max_queries], ""

    return [], "Servono le query: da file oppure da un referto JSON"


def describe_chunk(chunk: dict) -> str:
    """Etichetta leggibile di un chunk: URL e, se c'e', il suo heading.

    Un indice numerico nel referto non dice nulla a chi legge: deve
    essere risalibile al passaggio esatto del sito.
    """
    heading = (chunk.get("heading") or "").strip()
    url = chunk.get("url") or "?"
    return "%s § %s" % (url, heading) if heading else url


def chunk_page(soup: BeautifulSoup, url: str, titolo: str = "") -> List[dict]:
    """Segmenta una pagina in passaggi autoconsistenti.

    Un chunk = un heading piu' il testo che lo segue fino all'heading
    successivo. E' l'unita' che un motore ibrido o una pipeline RAG
    cita davvero. Prima si usavano i primi 500 caratteri della pagina,
    che sono tipicamente il menu di navigazione: tutto il contenuto
    oltre quella soglia era invisibile all'audit semantico.

    Si cammina sui nodi di testo invece che sugli elementi di blocco
    perche' ogni nodo viene visitato una volta sola: con find_all() il
    testo di un <p> dentro un <li> verrebbe contato due volte.
    """
    corpo = soup.body or soup
    sezioni: List[Tuple[str, str]] = []
    heading = ""
    parti: List[str] = []

    for nodo in corpo.descendants:
        if isinstance(nodo, Tag):
            if nodo.name in HEADINGS:
                if parti:
                    sezioni.append((heading, " ".join(parti)))
                    parti = []
                heading = nodo.get_text(" ", strip=True)
            continue
        if isinstance(nodo, Comment) or not isinstance(nodo, NavigableString):
            continue
        if nodo.find_parent(NON_CONTENUTO + HEADINGS):
            continue
        testo = " ".join(str(nodo).split())
        if testo:
            parti.append(testo)
    if parti:
        sezioni.append((heading, " ".join(parti)))

    chunks = []
    for intestazione, testo in sezioni:
        for finestra in split_windows(testo):
            if len(finestra) >= MIN_CHUNK_CHARS:
                chunks.append({"url": url, "heading": intestazione,
                               "text": finestra})
    if not chunks:
        # Pagina troppo corta per essere segmentata: meglio un chunk
        # solo che nessuno, altrimenti sparisce dall'analisi.
        intero = soup.get_text(" ", strip=True)
        if intero:
            chunks.append({"url": url, "heading": titolo, "text": intero})
    return chunks


def build_context(url: str, max_pages: int = 10,
                  embeddings_model: str = DEFAULT_EMBEDDINGS,
                  market: str = "global",
                  delay: float = DEFAULT_DELAY,
                  timeout: int = DEFAULT_TIMEOUT,
                  owner_declaration: bool = False,
                  llm: str = "auto",
                  queries: Optional[List[str]] = None,
                  credentials: Optional[dict] = None) -> Optional[dict]:
    """Scansiona il sito UNA volta e prepara il contesto per i moduli.

    Unica fonte di verita' per CLI e API: prima ognuna costruiva il
    proprio dizionario, e l'API lo rifaceva per ogni modulo. Un solo
    crawl non serve solo a risparmiare richieste — serve perche' i
    moduli devono osservare lo stesso stato del sito, altrimenti i loro
    punteggi non sono confrontabili fra loro.

    Restituisce None se il sito e' irraggiungibile: tradurre l'assenza
    in un errore HTTP spetta al chiamante, non a questo modulo.
    """
    crawler = Crawler(url, max_pages, delay=delay, timeout=timeout,
                      owner_declaration=owner_declaration)
    pages = crawler.crawl()
    if not pages:
        return None
    return {
        "url": url,
        "pages": pages,
        "urls": list(pages.keys()),
        # Lista unica di chunk, ciascuno con url e heading: e' su
        # QUESTA che lavorano entrambi i retriever, perche' l'RRF ha
        # senso solo fondendo ranking sulle stesse unita'.
        "chunks": [c for p in pages.values() for c in p.get("chunks", [])],
        "embeddings_model": embeddings_model,
        "force_proxy": embeddings_model.lower() == "none",
        "market": market,
        # Registrati nel contesto perche' finiscano nel referto: chi lo
        # legge deve sapere se e cosa e' stato saltato, e se robots.txt
        # e' stato ignorato per dichiarazione di proprieta'.
        "robots_ignored": owner_declaration,
        # Distinto da robots_ignored: la dichiarazione di proprieta'
        # abilita anche l'active scan WAPT, che invia payload d'attacco.
        "owner_declaration": owner_declaration,
        "skipped": crawler.skipped,
        # Come sono state trovate le pagine: cambia il significato del
        # campione, e chi legge il referto deve saperlo.
        "discovery": crawler.discovery,
        "robots": dict(crawler.robots_info),
        "sitemap": dict(crawler.sitemap_info),
        "llm": llm,
        # Credenziali del chiamante, alternative alle variabili
        # d'ambiente. Non finiscono nel referto: build_report() legge
        # chiavi nominate, non l'intero contesto.
        "credentials": dict(credentials or {}),
        # Le query su cui gira la simulazione RRF. Fondere due ranghi
        # prodotti da UNA query dice pochissimo: la formula del paper
        # ha senso su un insieme di interrogazioni.
        "queries": list(queries) if queries else default_queries(pages),
    }


def reciprocal_rank_fusion(rankings: List[List[int]],
                           k: int = 60) -> List[Tuple[int, float]]:
    """Fonde piu' classifiche con la formula di Cormack et al. (2009).

    score(d) = somma su ogni lista di 1 / (k + rank(d) + 1)

    Usa la POSIZIONE e non il punteggio, che non e' confrontabile fra
    recuperatori diversi: e' l'intera ragione per cui la fusione ibrida
    funziona. k=60 e' il valore del paper e attenua il peso delle prime
    posizioni.

    Perche' abbia senso, le classifiche in ingresso devono riferirsi
    alle STESSE unita': vedi R10 in AS-IS.md.
    """
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking):
            scores[doc_idx] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
