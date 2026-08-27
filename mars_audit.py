#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import argparse
import sys
from mars_core import (DEFAULT_DELAY, DEFAULT_EMBEDDINGS,
                       DEFAULT_MAX_QUERIES, DEFAULT_TIMEOUT,
                       MODULES_REGISTRY, __version__, build_context,
                       errore_modulo, load_external_module,
                       normalizza_risultato)
from mars_core import load_credentials, load_queries
from mars_citability import MERCATI
import mars_history
from mars_i18n import LINGUA_CANONICA, LINGUE
from mars_report import RENDERERS, build_report


# Codici di uscita, allineati a quelli di mars_citations.py.
# Il valore 1 resta libero per una futura soglia --fail-under (idea I2).
EXIT_OK = 0
EXIT_NESSUNA_PAGINA = 2
EXIT_SCRITTURA = 3
EXIT_USO = 2


def run_audit(url: str, max_pages: int, embeddings_model: str,
              market: str, delay: float = DEFAULT_DELAY,
              timeout: int = DEFAULT_TIMEOUT,
              owner_declaration: bool = False,
              max_children: int = 0,
              credentials: dict | None = None,
              llm: str = "auto", formato: str = "text",
              output: str | None = None,
              queries: list[str] | None = None,
              storico: str | None = None,
              lang: str = LINGUA_CANONICA) -> int:
    print(f"Avvio scansione MARS Beacon su: {url}", file=sys.stderr)
    context = build_context(url, max_pages, embeddings_model, market,
                            delay=delay, timeout=timeout,
                            owner_declaration=owner_declaration,
                            max_children=max_children,
                            credentials=credentials,
                            llm=llm, queries=queries, lang=lang)

    if context is None:
        print("Nessuna pagina indicizzata.", file=sys.stderr)
        # Codice 2, non 0: un audit che non ha guardato nulla non e'
        # un audit riuscito, e una pipeline deve poterlo distinguere.
        return EXIT_NESSUNA_PAGINA

    print("\n--- Rilevamento Moduli Attivi ---", file=sys.stderr)
    results = {}
    # Stesso dict, popolato mentre il ciclo avanza: un modulo di
    # sintesi puo' cosi' leggere i punteggi delle aree gia' eseguite.
    # I moduli girano nell'ordine di MODULES_REGISTRY.
    context["results"] = results

    for mod_name, mod_desc in MODULES_REGISTRY:
        ext_mod = load_external_module(mod_name)

        if ext_mod:
            print(f"[✓] {mod_desc} ({mod_name}.py)", file=sys.stderr)
            # L'esito finisce SEMPRE in results, anche quando e' un
            # fallimento: un'area che sparisce dal referto senza
            # lasciare traccia e' peggio di una dichiarata fallita, e
            # con --output il file consegnato non ne diceva nulla.
            # E' cio' che l'API faceva gia'.
            try:
                if hasattr(ext_mod, 'audit'):
                    results[mod_name] = normalizza_risultato(
                        mod_name, ext_mod.audit(context))
                else:
                    results[mod_name] = {
                        "error": "manca la funzione audit()"}
                    print(f"  ⚠ Modulo {mod_name}.py trovato ma manca "
                          "funzione 'audit()'", file=sys.stderr)
            except Exception as e:
                results[mod_name] = errore_modulo(e)
                print(f"  Errore esecuzione audit: {e}", file=sys.stderr)
        else:
            print(f"[ ] {mod_desc} ignorato (file non trovato)", file=sys.stderr)

    # L'esecuzione precedente si legge PRIMA di comporre il referto:
    # il delta e' una chiave del dato canonico, non una nota della
    # vista, cosi' JSON, CSV e API lo ricevono senza altro lavoro.
    if storico:
        context["previous"] = mars_history.leggi_ultima_esecuzione(
            storico, context["url"])

    referto = build_report(results, context)

    # Lo storico si aggiorna DOPO: se l'append fallisce il referto e'
    # gia' fatto, e perdere una riga di archivio non vale il codice di
    # uscita. Lo si dichiara e si va avanti.
    if storico:
        if mars_history.appendi_storico(storico,
                                        mars_history.riga_storico(referto)):
            print(f"Storico aggiornato in {storico}", file=sys.stderr)
        else:
            print(f"⚠ Impossibile scrivere lo storico in {storico}", file=sys.stderr)

    testo = RENDERERS[formato](referto, lang)
    if output:
        try:
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(testo)
        except OSError as exc:
            print(f"Impossibile scrivere {output}: {exc}", file=sys.stderr)
            return EXIT_SCRITTURA
        print(f"Referto scritto in {output}", file=sys.stderr)
    else:
        # Il referto NON e' un print: e' il DATO, e su stdout ci va solo
        # lui (R59). Scriverlo con `sys.stdout.write` lascia
        # l'invariante «ogni print di questo file va su stderr» senza
        # un'eccezione da ricordare — ed e' l'eccezione dimenticata che
        # rendeva illeggibile `--format json > referto.json`.
        sys.stdout.write(testo + "\n")
    return EXIT_OK


DESCRIZIONE = """MARS Beacon — audit di citabilità per assistenti IA.

Scansiona un sito (via sitemap o seguendo i link interni), lo segmenta in
passaggi e valuta nove aree: indicizzabilità, SEO, recupero lessicale BM25,
semantica, dati strutturati, accessibilità, sicurezza, profili di citabilità
e — se richiesto — un giudizio LLM. Simula infine la fusione RRF fra il
recuperatore lessicale e quello vettoriale."""

ESEMPI = """
esempi:
  # audit rapido, referto a video
  mars_audit.py https://example.com

  # più pagine e referto HTML da aprire nel browser
  mars_audit.py https://example.com --max-pages 40 \\
      --format html --output referto.html

  # con le proprie query, e referto JSON riusabile da mars_citations.py
  mars_audit.py https://example.com --queries domande.txt \\
      --format json --output referto.json
  mars_citations.py https://example.com --from-audit referto.json

  # da incollare in una issue: il piano di interventi e' una task list
  mars_audit.py https://example.com --format markdown --output referto.md

  # i rilievi come tabella, da aprire in Excel o Fogli
  mars_audit.py https://example.com --format csv --output rilievi.csv

  # confronto con l'esecuzione precedente dello stesso sito
  mars_audit.py https://example.com --history storico.jsonl

  # sito proprio: robots.txt ignorato e scansione WAPT attiva
  mars_audit.py https://miosito.it --i-own-this-domain

  # veloce e senza spese: proxy char-tfidf e niente giudizio LLM
  mars_audit.py https://example.com --embeddings none --llm off

codici di uscita:
  0  referto prodotto
  2  nessuna pagina indicizzata, o errore d'uso
  3  impossibile scrivere il file di --output

variabili d'ambiente (tutte opzionali):
  ANTHROPIC_API_KEY   abilita il giudizio LLM con --llm auto
  HF_TOKEN            solo per modelli di embedding privati su Hugging Face
  ZAP_PROXY           daemon ZAP per la scansione WAPT
                      (default http://127.0.0.1:8080)
  ZAP_API_KEY         chiave del daemon ZAP, se richiesta

strumenti opzionali: senza Lighthouse, ZAP, sentence-transformers, axe-core
o una chiave Anthropic il programma non fallisce — ripiega e lo dichiara nel
referto, distinguendo "non misurato" da un punteggio basso."""


def costruisci_parser() -> argparse.ArgumentParser:
    """Il parser degli argomenti.

    Funzione e non blocco __main__ perche' i test possano
    verificare che gli esempi dell'aiuto siano ancora validi.
    """
    parser = argparse.ArgumentParser(
        prog="mars_audit.py",
        description=DESCRIZIONE,
        epilog=ESEMPI,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        "url", metavar="URL",
        help="Sito da scansionare, con lo schema. "
             "Esempio: https://www.example.com")

    parser.add_argument(
        "--max-pages", type=int, default=10, metavar="N",
        help="Pagine da scansionare al massimo. Esempi: 10 (default), 40 "
             "per un sito medio, 100 per una scansione ampia. Piu' pagine "
             "significa piu' tempo e piu' richieste al sito.")

    parser.add_argument(
        "--credentials", metavar="FILE",
        help="File JSON con le chiavi degli strumenti opzionali: "
             "anthropic_api_key, hf_token, zap_api_key, zap_proxy. "
             "Esempio: chiavi.local.json — si ottiene copiando "
             "examples/audit_request.json, di cui accetta anche il "
             "corpo intero. Un FILE e non un valore sul flag perche' "
             "gli argomenti di un processo sono leggibili da ogni "
             "utente locale in /proc e finiscono nella cronologia "
             "della shell: nel file ci finisce il percorso. Proteggilo "
             "con chmod 600. Senza questo flag valgono le variabili "
             "d'ambiente, che MARS non legge da .env.")

    parser.add_argument(
        "--max-children", type=int, default=0, metavar="N",
        help="Tetto ai link seguiti PER PAGINA dallo spider ZAP, che gira "
             "solo con --i-own-this-domain. Esempi: 0 (default, nessun "
             "tetto, come ZAP), 10 per un giro contenuto, 50 per una "
             "scansione ampia. Non e' un numero di PAGINE e non puo' "
             "esserlo — l'API dello spider non accetta nulla che limiti "
             "il totale — quindi il referto dichiara il perimetro come "
             "non esatto. Senza la dichiarazione non serve: li' l'area 7 "
             "guarda le pagine gia' scansionate, e a quelle basta "
             "--max-pages.")

    parser.add_argument(
        "--queries", metavar="FILE",
        help="File di testo con una query per riga (UTF-8). Esempio: "
             "domande.txt. Senza, si usano quattro query generiche nella "
             "lingua prevalente del sito. Le query del dominio danno una "
             "misura molto piu' significativa di quelle generiche. "
             "Si leggono al massimo le prime %d righe utili."
             % DEFAULT_MAX_QUERIES)

    parser.add_argument(
        "--embeddings", default=DEFAULT_EMBEDDINGS, metavar="MODELLO",
        help="Modello sentence-transformers per il recupero vettoriale. "
             "Valori: 'none' forza il proxy char-tfidf (nessun download, "
             "molto piu' rapido); un nome di modello dell'Hub, per esempio "
             "sentence-transformers/all-MiniLM-L6-v2. "
             "Default: %(default)s")

    parser.add_argument(
        "--market", default="global", metavar="MERCATO",
        help="Mercato per i profili di citabilita' IA. Valori: "
             + ", ".join(sorted(MERCATI))
             + ". Un valore diverso ricade su 'global' e lo dichiara nel "
               "referto. Default: %(default)s")

    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY, metavar="SECONDI",
        help="Pausa fra due richieste al sito. Esempi: 0.5 (default), 0 "
             "per un server locale di prova, 2 per un sito lento o "
             "delicato. Un Crawl-delay piu' alto in robots.txt vince "
             "comunque su questo valore.")

    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="SECONDI",
        help="Timeout di ogni richiesta di rete. Esempi: 10 (default), 30 "
             "per siti lenti.")

    parser.add_argument(
        "--format", choices=tuple(RENDERERS), default="text",
        dest="formato",
        help="Resa del referto. Valori: text (a video, default), json "
             "(struttura canonica, riusabile da mars_citations.py "
             "--from-audit), html (pagina autoconsistente, apribile "
             "senza rete), markdown (da incollare in una issue: il piano "
             "e' una task list), csv (una riga per rilievo, per Excel o "
             "Fogli).")

    parser.add_argument(
        "--lang", choices=LINGUE, default=LINGUA_CANONICA,
        help="Lingua del referto. Valori: it (default), en. Il JSON "
             "resta in italiano in ogni caso — e' il dato canonico, e "
             "porta `key` e `params` su ogni rilievo perche' chi lo "
             "consuma traduca da se'. Una lingua sconosciuta ricade "
             "sull'italiano.")

    parser.add_argument(
        "--output", metavar="FILE",
        help="Scrive il referto su file invece che a video. Esempi: "
             "referto.html, referto.json. Uscita 3 se il file non e' "
             "scrivibile.")

    parser.add_argument(
        "--history", metavar="FILE", dest="storico",
        help="File JSONL dello storico, per confrontare questa "
             "esecuzione con la precedente dello stesso sito. Esempio: "
             "storico-clienti.jsonl. Default: %s accanto a --output, o "
             "nella cartella corrente. Il referto guadagna la sezione "
             "'rispetto all'esecuzione precedente'; alla prima non c'e' "
             "nulla da confrontare e non compare."
             % mars_history.STORICO_PREDEFINITO)

    parser.add_argument(
        "--no-history", action="store_true", dest="senza_storico",
        help="Non legge e non scrive lo storico. Utile in una pipeline "
             "che riesegue l'audit molte volte, dove il confronto con "
             "l'esecuzione di dieci minuti prima non dice nulla.")

    parser.add_argument(
        "--llm", choices=("auto", "on", "off"), default="auto",
        help="Giudizio LLM sulla citabilita' dei passaggi migliori. "
             "Valori: auto (default) esegue solo se ANTHROPIC_API_KEY e' "
             "presente; on tenta comunque, utile con un profilo "
             "'ant auth login'; off non esegue mai. E' L'UNICO MODULO CHE "
             "COMPORTA UNA SPESA: prima di inviare dichiara quanti "
             "passaggi e quanti token partiranno.")

    parser.add_argument(
        "--i-own-this-domain", action="store_true",
        dest="owner_declaration",
        help="DICHIARAZIONE: sono il proprietario del dominio e mi assumo "
             "la responsabilita' dell'audit. Abilita tre cose: ignorare "
             "robots.txt; lo SPIDER di ZAP, che robots.txt non lo rispetta "
             "e usa i Disallow come punti di partenza; e la scansione WAPT "
             "ATTIVA, che invia payload d'attacco (XSS, SQL injection). "
             "Contro un sito non proprio e' un attacco. La dichiarazione "
             "viene registrata nel referto.")

    parser.add_argument(
        "--version", action="version",
        version="MARS Beacon %s" % __version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Il punto d'ingresso, come FUNZIONE.

    Stava in un blocco `if __name__ == "__main__"`, che nessun test
    puo' eseguire: due mutazioni ci sono sopravvissute — togliere la
    propagazione delle credenziali, e togliere l'uscita su un file di
    chiavi illeggibile — perche' il codice fra argparse e `run_audit`
    era fuori portata. Restituisce il codice di uscita invece di
    chiamare `sys.exit`, cosi' un test lo legge.
    """
    args = costruisci_parser().parse_args(argv)
    elenco_query = None
    if args.queries:
        elenco_query, errore = load_queries(path=args.queries)
        if errore:
            print(errore, file=sys.stderr)
            return EXIT_USO
    chiavi = None
    if args.credentials:
        chiavi, messaggio = load_credentials(args.credentials)
        # Con credenziali vuote il messaggio e' un ERRORE e si esce: un
        # file passato e ignorato in silenzio fa credere di aver
        # misurato con la propria chiave. Con credenziali piene e' un
        # avviso — un refuso, dei permessi larghi — e l'audit prosegue
        # con cio' che si e' letto davvero.
        if messaggio:
            print(messaggio, file=sys.stderr)
        if not chiavi:
            return EXIT_USO
    return run_audit(args.url, args.max_pages, args.embeddings,
                     args.market, delay=args.delay, timeout=args.timeout,
                     owner_declaration=args.owner_declaration,
                     max_children=args.max_children,
                     credentials=chiavi,
                     llm=args.llm, formato=args.formato,
                     output=args.output, queries=elenco_query,
                     lang=args.lang,
                     storico=(None if args.senza_storico else
                              args.storico
                              or mars_history.percorso_storico(args.output)))


if __name__ == "__main__":
    sys.exit(main())
