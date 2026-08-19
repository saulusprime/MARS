#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Licenza: Apache 2.0
"""

import argparse
import os
import sys
import importlib.util
from mars_core import (DEFAULT_DELAY, DEFAULT_TIMEOUT, build_context,
                       reciprocal_rank_fusion)

MODULES_REGISTRY = [
    ("mars_tech", "1. Tecnica"),
    ("mars_seo", "2. SEO"),
    ("mars_lexical", "3. Lessicale"),
    ("mars_semantic", "4. Semantica"),
    ("mars_schema", "5. Dati Strutturati"),
    ("mars_wcag", "6. Accessibilità"),
    ("mars_wapt", "7. Sicurezza")
]

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

def print_report(results, urls, context=None):
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
                print(f"{desc:<20} : Analizzato (Top: {res.get('top_url', 'N/A')})")
            elif mod_name == "mars_semantic":
                ratio = res.get("answer_shaped_ratio", 0)
                print(f"{desc:<20} : Analizzato ({ratio:.0%} chunk answer-shaped)")
                
    if lex_res and sem_res:
        rrf = reciprocal_rank_fusion([lex_res["rank"], sem_res["rank"]])
        top_3_lex = set(lex_res["rank"][:3])
        top_3_sem = set(sem_res["rank"][:3])
        consensus = len(top_3_lex.intersection(top_3_sem))
        print("-" * 55)
        print(f"Simulazione RRF      : Consenso Top-3 = {consensus}/3")
        print(f"Top Chunk Ibrido     : {urls[rrf[0][0]] if rrf else 'N/A'}")
        
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

def run_audit(url, max_pages, embeddings_model, market,
              delay=DEFAULT_DELAY, timeout=DEFAULT_TIMEOUT,
              owner_declaration=False):
    print(f"Avvio scansione MARS Beacon su: {url}")
    context = build_context(url, max_pages, embeddings_model, market,
                            delay=delay, timeout=timeout,
                            owner_declaration=owner_declaration)

    if context is None:
        print("Nessuna pagina indicizzata.")
        return
    
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

    print_report(results, context["urls"], context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MARS Beacon - Meta-fusion Audit")
    parser.add_argument("url", help="URL del sito da scansionare")
    parser.add_argument("--max-pages", type=int, default=10, help="Numero massimo di pagine")
    parser.add_argument("--embeddings", default="paraphrase-multilingual-MiniLM-L12-v2", help="Modello ST o 'none'")
    parser.add_argument("--market", default="global", help="Target market per citabilità IA")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="Pausa fra le richieste in secondi (default %(default)s)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout di rete in secondi (default %(default)s)")
    parser.add_argument("--i-own-this-domain", action="store_true",
                        dest="owner_declaration",
                        help="DICHIARAZIONE: sono il proprietario del dominio e "
                             "mi assumo la responsabilità dell'audit. Solo con "
                             "questa dichiarazione robots.txt viene ignorato.")
    
    args = parser.parse_args()
    run_audit(args.url, args.max_pages, args.embeddings, args.market,
              delay=args.delay, timeout=args.timeout,
              owner_declaration=args.owner_declaration)