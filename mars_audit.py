#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

from __future__ import annotations

import argparse
import sys
from mars_core import (DEFAULT_DELAY, DEFAULT_EMBEDDINGS, DEFAULT_TIMEOUT,
                       MODULES_REGISTRY, __version__, build_context,
                       describe_chunk, load_external_module,
                       reciprocal_rank_fusion)


# Codici di uscita, allineati a quelli di mars_citations.py.
# Il valore 1 resta libero per una futura soglia --fail-under (idea I2).
EXIT_OK = 0
EXIT_NESSUNA_PAGINA = 2


def print_report(results: dict, context: dict | None = None) -> None:
    """Stampa il referto finale a video.

    Dichiara anche cio' che NON e' stato misurato: aree senza strumento
    e URL saltati dal crawler. Dodici pagine escluse cambiano il
    significato di ogni punteggio, e tacerlo sarebbe una bugia per
    omissione.
    """
    print("\n" + "="*55)
    print("           MARS BEACON - REPORT FINALE           ")
    print("="*55)

    lex_res = results.get("mars_lexical")
    sem_res = results.get("mars_semantic")

    for mod_name, desc in MODULES_REGISTRY:
        if mod_name in results:
            res = results[mod_name]
            if "score" in res:
                # score None = area non misurabile (strumento assente o
                # fallito): va distinta da 0/100, che e' un giudizio.
                if res["score"] is None:
                    print(f"{desc:<20} : non misurato")
                else:
                    print(f"{desc:<20} : {res['score']:>3.0f}/100")
                if "issues" in res and res["issues"]:
                    for iss in res["issues"][:2]:
                        print(f"  ⚠ {iss}")
            elif mod_name == "mars_lexical":
                print(f"{desc:<20} : Analizzato "
                      f"(Top: {res.get('top_chunk', 'N/A')})")
            elif mod_name == "mars_semantic":
                ratio = res.get("answer_shaped_ratio", 0)
                n = res.get("n_chunks", 0)
                print(f"{desc:<20} : Analizzato "
                      f"({ratio:.0%} di {n} chunk answer-shaped)")

    if lex_res and sem_res and "rank" in lex_res and "rank" in sem_res:
        chunks = (context or {}).get("chunks") or []
        rrf = reciprocal_rank_fusion([lex_res["rank"], sem_res["rank"]])
        top_3_lex = set(lex_res["rank"][:3])
        top_3_sem = set(sem_res["rank"][:3])
        consensus = len(top_3_lex.intersection(top_3_sem))
        print("-" * 55)
        # Ora i due ranghi si riferiscono agli STESSI chunk: prima uno
        # indicizzava pagine e l'altro chunk, e il consenso non aveva
        # il significato dichiarato nel README.
        print(f"Simulazione RRF      : Consenso Top-3 = {consensus}/3 "
              f"su {len(chunks)} chunk")
        if rrf and rrf[0][0] < len(chunks):
            print(f"Top Chunk Ibrido     : {describe_chunk(chunks[rrf[0][0]])}")

    if context:
        # Un referto deve dire cosa NON ha guardato: 12 pagine saltate
        # cambiano il significato di ogni punteggio qui sopra.
        saltati = context.get("skipped") or []
        if context.get("robots_ignored"):
            print("-" * 55)
            print("\u26a0 robots.txt IGNORATO per dichiarazione di proprieta'")
        if saltati:
            print("-" * 55)
            print(f"URL saltati          : {len(saltati)}")
            for motivo in saltati[:3]:
                print(f"  · {motivo}")
            if len(saltati) > 3:
                print(f"  · ... e altri {len(saltati) - 3}")

    print("="*55 + "\n")


def run_audit(url: str, max_pages: int, embeddings_model: str,
              market: str, delay: float = DEFAULT_DELAY,
              timeout: int = DEFAULT_TIMEOUT,
              owner_declaration: bool = False) -> int:
    print(f"Avvio scansione MARS Beacon su: {url}")
    context = build_context(url, max_pages, embeddings_model, market,
                            delay=delay, timeout=timeout,
                            owner_declaration=owner_declaration)

    if context is None:
        print("Nessuna pagina indicizzata.")
        # Codice 2, non 0: un audit che non ha guardato nulla non e'
        # un audit riuscito, e una pipeline deve poterlo distinguere.
        return EXIT_NESSUNA_PAGINA

    print("\n--- Rilevamento Moduli Attivi ---")
    results = {}

    for mod_name, mod_desc in MODULES_REGISTRY:
        ext_mod = load_external_module(mod_name)

        if ext_mod:
            print(f"[✓] {mod_desc} ({mod_name}.py)")
            try:
                if hasattr(ext_mod, 'audit'):
                    results[mod_name] = ext_mod.audit(context)
                else:
                    print(f"  ⚠ Modulo {mod_name}.py trovato ma manca funzione 'audit()'")
            except Exception as e:
                print(f"  Errore esecuzione audit: {e}")
        else:
            print(f"[ ] {mod_desc} ignorato (file non trovato)")

    print_report(results, context)
    return EXIT_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MARS Beacon - Meta-fusion Audit")
    parser.add_argument("url", help="URL del sito da scansionare")
    parser.add_argument("--max-pages", type=int, default=10, help="Numero massimo di pagine")
    parser.add_argument("--embeddings", default=DEFAULT_EMBEDDINGS,
                        help="Modello ST o 'none'")
    parser.add_argument("--market", default="global", help="Target market per citabilità IA")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="Pausa fra le richieste in secondi (default %(default)s)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout di rete in secondi (default %(default)s)")
    parser.add_argument("--version", action="version",
                        version="MARS Beacon %s" % __version__)
    parser.add_argument("--i-own-this-domain", action="store_true",
                        dest="owner_declaration",
                        help="DICHIARAZIONE: sono il proprietario del dominio e "
                             "mi assumo la responsabilità dell'audit. Solo con "
                             "questa dichiarazione robots.txt viene ignorato.")

    args = parser.parse_args()
    sys.exit(run_audit(args.url, args.max_pages, args.embeddings,
                       args.market, delay=args.delay, timeout=args.timeout,
                       owner_declaration=args.owner_declaration))
