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
                       load_external_module)
from mars_report import RENDERERS, build_report


# Codici di uscita, allineati a quelli di mars_citations.py.
# Il valore 1 resta libero per una futura soglia --fail-under (idea I2).
EXIT_OK = 0
EXIT_NESSUNA_PAGINA = 2
EXIT_SCRITTURA = 3


def run_audit(url: str, max_pages: int, embeddings_model: str,
              market: str, delay: float = DEFAULT_DELAY,
              timeout: int = DEFAULT_TIMEOUT,
              owner_declaration: bool = False,
              llm: str = "auto", formato: str = "text",
              output: str | None = None) -> int:
    print(f"Avvio scansione MARS Beacon su: {url}")
    context = build_context(url, max_pages, embeddings_model, market,
                            delay=delay, timeout=timeout,
                            owner_declaration=owner_declaration,
                            llm=llm)

    if context is None:
        print("Nessuna pagina indicizzata.")
        # Codice 2, non 0: un audit che non ha guardato nulla non e'
        # un audit riuscito, e una pipeline deve poterlo distinguere.
        return EXIT_NESSUNA_PAGINA

    print("\n--- Rilevamento Moduli Attivi ---")
    results = {}
    # Stesso dict, popolato mentre il ciclo avanza: un modulo di
    # sintesi puo' cosi' leggere i punteggi delle aree gia' eseguite.
    # I moduli girano nell'ordine di MODULES_REGISTRY.
    context["results"] = results

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

    referto = build_report(results, context)
    testo = RENDERERS[formato](referto)
    if output:
        try:
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(testo)
        except OSError as exc:
            print(f"Impossibile scrivere {output}: {exc}")
            return EXIT_SCRITTURA
        print(f"Referto scritto in {output}")
    else:
        print(testo)
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
    parser.add_argument("--format", choices=tuple(RENDERERS),
                        default="text", dest="formato",
                        help="Formato del referto (default: text)")
    parser.add_argument("--output", metavar="FILE",
                        help="Scrive il referto su file invece che a video")
    parser.add_argument("--llm", choices=("auto", "on", "off"),
                        default="auto",
                        help="Giudizio LLM sulla citabilità: 'auto' solo se "
                             "ANTHROPIC_API_KEY è presente (default), 'on' "
                             "tenta comunque, 'off' non lo esegue mai. "
                             "È l'unico modulo che comporta una spesa.")
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
                       owner_declaration=args.owner_declaration,
                       llm=args.llm, formato=args.formato,
                       output=args.output))
