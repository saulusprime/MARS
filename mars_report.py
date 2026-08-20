#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

import base64
import html
import json
import os
import time
from typing import Dict, List, Optional

from mars_core import (MODULES_REGISTRY, __version__, describe_chunk,
                       reciprocal_rank_fusion)

FAVICON = "favicon.ico"


# ======================================================================
# Il dato: struttura canonica del referto
# ======================================================================

def build_report(results: dict, context: Optional[dict] = None) -> dict:
    """Referto come DATO, indipendente da come verra' mostrato.

    E' la struttura canonica: il JSON la serializza tal quale, testo e
    HTML ne sono viste. Prima la logica del referto viveva dentro le
    print, quindi esisteva un solo formato possibile e l'API dovevaripetere
    gli stessi calcoli per conto proprio.
    """
    context = context or {}
    chunks = context.get("chunks") or []

    aree = []
    for nome, descrizione in MODULES_REGISTRY:
        if nome not in results:
            continue
        res = results[nome]
        aree.append({
            "module": nome,
            "label": descrizione,
            "score": res.get("score"),
            "status": res.get("status"),
            "issues": list(res.get("issues") or []),
            # Con quale strumento e a quale livello: un punteggio di
            # accessibilita' senza il livello WCAG non significa nulla.
            "tool": res.get("tool"),
            "wcag_level": res.get("wcag_level"),
            "pages_tested": res.get("pages_tested"),
        })

    referto: Dict[str, object] = {
        "tool": "mars_audit.py",
        "version": __version__,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "url": context.get("url"),
        "market": context.get("market"),
        "pages_crawled": len(context.get("pages") or {}),
        "discovery": context.get("discovery"),
        "chunks": len(chunks),
        "robots_ignored": bool(context.get("robots_ignored")),
        "skipped": list(context.get("skipped") or []),
        "areas": aree,
        # Chiave del contratto con mars_citations.py --from-audit:
        # lista di voci ciascuna con la propria "query".
        "rrf_simulation": rrf_simulation(results, chunks),
        "rrf_aggregate": rrf_aggregate(results, chunks),
        "citability": results.get("mars_citability"),
        "llm_judgement": results.get("mars_llm_judge"),
        "lexical": {"top_chunk":
                    (results.get("mars_lexical") or {}).get("top_chunk")},
        "semantic": {
            k: (results.get("mars_semantic") or {}).get(k)
            for k in ("answer_shaped_ratio", "n_chunks",
                      "answer_shaped_signals", "languages")
        },
    }
    return referto


def _consenso(rank_a: List[int], rank_b: List[int],
              chunks: List[dict], query: str) -> dict:
    """Consenso fra due classifiche sui primi tre chunk."""
    attesi = min(3, len(rank_a), len(rank_b))
    fusi = reciprocal_rank_fusion([rank_a, rank_b])
    top = fusi[0][0] if fusi and fusi[0][0] < len(chunks) else None
    return {
        "query": query,
        "consensus_top3": len(set(rank_a[:3]) & set(rank_b[:3])),
        "consensus_out_of": attesi,
        "top_chunk": describe_chunk(chunks[top]) if top is not None else None,
        "top_chunk_url": chunks[top]["url"] if top is not None else None,
    }


def rrf_simulation(results: dict, chunks: List[dict]) -> List[dict]:
    """Esito della fusione, una voce per query interrogata.

    E' la chiave che mars_citations.py --from-audit legge per riusare
    le stesse query: cosi' la stima della citabilita' e la misura delle
    citazioni reali guardano le stesse domande.
    """
    lex = results.get("mars_lexical") or {}
    sem = results.get("mars_semantic") or {}
    voci_lex = {v["query"]: v["rank"] for v in lex.get("per_query") or []}
    voci_sem = {v["query"]: v["rank"] for v in sem.get("per_query") or []}
    comuni = [q for q in voci_lex if q in voci_sem]
    return [_consenso(voci_lex[q], voci_sem[q], chunks, q) for q in comuni]


def rrf_aggregate(results: dict, chunks: List[dict]) -> Optional[dict]:
    """Consenso sui ranghi aggregati, cioe' su tutte le query insieme.

    E' la misura piu' solida delle due: un chunk che sale in alto per
    entrambi i recuperatori su piu' domande e' recuperabile davvero,
    mentre un consenso su una sola query puo' essere un caso.
    """
    lex = results.get("mars_lexical") or {}
    sem = results.get("mars_semantic") or {}
    if "rank" not in lex or "rank" not in sem:
        return None
    aggregato = _consenso(lex["rank"], sem["rank"], chunks,
                          "(aggregato su tutte le query)")
    aggregato["queries"] = lex.get("queries") or []
    return aggregato


# ======================================================================
# Le viste
# ======================================================================

def render_json(referto: dict) -> str:
    return json.dumps(referto, indent=2, ensure_ascii=False)


def _riga_area(area: dict) -> str:
    if area["score"] is None:
        stato = ("disattivato" if area["status"] == "disabled"
                 else "non misurato")
        return f"{area['label']:<20} : {stato}"
    return f"{area['label']:<20} : {area['score']:>3.0f}/100"


def render_text(referto: dict) -> str:
    righe = ["", "=" * 55,
             "           MARS BEACON - REPORT FINALE           ", "=" * 55]

    for area in referto["areas"]:
        if area["module"] == "mars_citability":
            continue  # ha un blocco tutto suo, in fondo
        if area["module"] == "mars_lexical":
            righe.append("%-20s : Analizzato (Top: %s)"
                         % (area["label"],
                            referto["lexical"]["top_chunk"] or "N/A"))
            continue
        if area["module"] == "mars_semantic":
            sem = referto["semantic"]
            righe.append("%-20s : Analizzato (%.0f%% di %s chunk "
                         "answer-shaped)"
                         % (area["label"],
                            100 * (sem["answer_shaped_ratio"] or 0),
                            sem["n_chunks"] or 0))
            continue
        righe.append(_riga_area(area))
        if area.get("wcag_level"):
            provate = area.get("pages_tested")
            campione = (" su %d pagine" % provate) if provate else ""
            righe.append("  %s · %s%s"
                         % (area.get("tool") or "?", area["wcag_level"],
                            campione))
        for problema in area["issues"][:2]:
            righe.append(f"  ⚠ {problema}")

    aggregato = referto.get("rrf_aggregate")
    if aggregato:
        righe.append("-" * 55)
        righe.append("Simulazione RRF      : Consenso Top-3 = %d/%d su %d "
                     "chunk" % (aggregato["consensus_top3"],
                                aggregato["consensus_out_of"],
                                referto["chunks"]))
        righe.append("  aggregato su %d query"
                     % len(referto["rrf_simulation"]))
        if aggregato["top_chunk"]:
            righe.append(f"Top Chunk Ibrido     : {aggregato['top_chunk']}")
        for voce in referto["rrf_simulation"]:
            righe.append("  %-34s %d/%d"
                         % (voce["query"][:34], voce["consensus_top3"],
                            voce["consensus_out_of"]))

    cit = referto.get("citability")
    if cit and cit.get("profiles"):
        righe.append("-" * 55)
        righe.append("Profili di citabilità IA  (mercato: %s)"
                     % cit.get("market"))
        for assistente, valore in cit["profiles"].items():
            barra = "█" * int((valore or 0) / 5)
            testo = f"{valore:>5.1f}" if valore is not None else "  n/d"
            righe.append(f"  {assistente:<20} {testo}  {barra}")
        if cit.get("score") is not None:
            righe.append(f"  {'INDICE COMPOSITO':<20} {cit['score']:>5.1f}")
        # Il disclaimer sta QUI e non in fondo: chi legge il numero
        # deve leggere anche cosa non è.
        righe.append(f"  ({cit.get('disclaimer', '')})")
        for nota in (cit.get("issues") or [])[:3]:
            righe.append(f"  · {nota}")

    llm = referto.get("llm_judgement") or {}
    if llm.get("motivazione"):
        righe.append("-" * 55)
        righe.append("Giudizio LLM (%s)  su %s passaggi"
                     % (llm.get("model"), llm.get("chunk_valutati")))
        if llm.get("score") is not None:
            righe.append(f"  Citabilità stimata   : {llm['score']}/100")
        righe.append(f"  {llm['motivazione']}")
        if llm.get("passaggio_migliore"):
            righe.append("  Passaggio migliore   : %s"
                         % llm["passaggio_migliore"])
        for punto in (llm.get("punti_deboli") or [])[:2]:
            righe.append(f"  · da migliorare: {punto}")

    if referto["robots_ignored"]:
        righe.append("-" * 55)
        righe.append("⚠ robots.txt IGNORATO per dichiarazione "
                     "di proprieta'")
    saltati = referto["skipped"]
    if saltati:
        righe.append("-" * 55)
        righe.append(f"URL saltati          : {len(saltati)}")
        for motivo in saltati[:3]:
            righe.append(f"  · {motivo}")
        if len(saltati) > 3:
            righe.append(f"  · ... e altri {len(saltati) - 3}")

    righe.append("-" * 55)
    righe.append("Pagine trovate via   : %s  (%d pagine, %d chunk)"
                 % (referto.get("discovery"), referto["pages_crawled"],
                    referto["chunks"]))
    righe.append("=" * 55)
    righe.append("")
    return "\n".join(righe)


def _favicon_data_uri() -> str:
    """favicon.ico incorporata come data URI.

    Si usa il .ico (2,8 KB) e non il .png (344 KB): il referto deve
    restare un file solo, ma non a costo di mezzo megabyte di icona.
    """
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            FAVICON)
    try:
        with open(percorso, "rb") as handle:
            dati = base64.b64encode(handle.read()).decode("ascii")
        return "data:image/x-icon;base64,%s" % dati
    except OSError:
        return ""


CSS = """
:root { --ok:#1a7f37; --warn:#9a6700; --bad:#cf222e; --bg:#fff;
        --fg:#1f2328; --muted:#656d76; --line:#d0d7de; --card:#f6f8fa; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#30363d;
          --card:#161b22; --ok:#3fb950; --warn:#d29922; --bad:#f85149; } }
* { box-sizing:border-box; }
body { margin:0; padding:2rem 1rem; background:var(--bg); color:var(--fg);
       font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:60rem; margin:0 auto; }
h1 { font-size:1.5rem; margin:0 0 .25rem; }
h2 { font-size:1.1rem; margin:2rem 0 .75rem;
     border-bottom:1px solid var(--line); padding-bottom:.35rem; }
.meta { color:var(--muted); font-size:.9rem; margin-bottom:1.5rem; }
table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:.5rem .6rem;
        border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:.8rem; text-transform:uppercase; color:var(--muted);
     letter-spacing:.03em; }
td.num { text-align:right; font-variant-numeric:tabular-nums;
         white-space:nowrap; }
.ok{color:var(--ok)} .warn{color:var(--warn)} .bad{color:var(--bad)}
.muted{color:var(--muted)}
.bar { display:inline-block; height:.55rem; border-radius:.28rem;
       background:currentColor; vertical-align:middle; }
ul { margin:.35rem 0 0; padding-left:1.1rem; }
li { font-size:.9rem; }
.card { background:var(--card); border:1px solid var(--line);
        border-radius:.5rem; padding:1rem; margin:.5rem 0; }
.disclaimer { font-size:.85rem; color:var(--muted); font-style:italic; }
code { background:var(--card); padding:.1rem .3rem; border-radius:.2rem;
       font-size:.85em; word-break:break-all; }
@media (max-width:40rem){ body{padding:1rem .6rem} th,td{padding:.4rem} }
"""


def _classe(valore: Optional[float]) -> str:
    if valore is None:
        return "muted"
    return "ok" if valore >= 80 else "warn" if valore >= 50 else "bad"


def _e(valore: object) -> str:
    """Escape: il referto contiene testo preso dal sito analizzato."""
    return html.escape(str(valore if valore is not None else ""))


def render_html(referto: dict) -> str:
    """Referto HTML autoconsistente: nessuna CDN, nessuno script."""
    p: List[str] = []
    icona = _favicon_data_uri()
    p.append("<!doctype html><html lang='it'><head><meta charset='utf-8'>")
    p.append("<meta name='viewport' content='width=device-width,"
             "initial-scale=1'>")
    p.append("<title>MARS Beacon — %s</title>" % _e(referto["url"]))
    if icona:
        p.append("<link rel='icon' href='%s'>" % icona)
    p.append("<style>%s</style></head><body><main>" % CSS)

    p.append("<h1>MARS Beacon</h1>")
    p.append("<p class='meta'><code>%s</code><br>%s · %s pagine · "
             "%s chunk · mercato %s · v%s</p>"
             % (_e(referto["url"]), _e(referto["generated_at"]),
                referto["pages_crawled"], referto["chunks"],
                _e(referto["market"]), _e(referto["version"])))
    p.append("<p class='meta'>Pagine trovate via <strong>%s</strong>.</p>"
             % _e(referto.get("discovery")))

    p.append("<h2>Aree</h2><table><tr><th>Area</th><th>Punteggio</th>"
             "<th>Rilievi</th></tr>")
    for area in referto["areas"]:
        if area["score"] is None:
            stato = ("disattivato" if area["status"] == "disabled"
                     else "non misurato")
            voto = "<span class='muted'>%s</span>" % stato
        else:
            voto = ("<span class='%s'>%.0f/100</span>"
                    % (_classe(area["score"]), area["score"]))
        rilievi = ("<ul>%s</ul>"
                   % "".join("<li>%s</li>" % _e(i) for i in area["issues"])
                   if area["issues"] else "<span class='muted'>—</span>")
        if area.get("wcag_level"):
            provate = area.get("pages_tested")
            rilievi = ("<p class='meta'>%s · %s%s</p>%s"
                       % (_e(area.get("tool")), _e(area["wcag_level"]),
                          " su %d pagine" % provate if provate else "",
                          rilievi))
        p.append("<tr><td>%s</td><td class='num'>%s</td><td>%s</td></tr>"
                 % (_e(area["label"]), voto, rilievi))
    p.append("</table>")

    aggregato = referto.get("rrf_aggregate")
    if aggregato:
        p.append("<h2>Simulazione RRF</h2>")
        p.append("<div class='card'><p>Consenso aggregato su %d query: "
                 "<strong class='%s'>%d/%d</strong></p>"
                 % (len(referto["rrf_simulation"]),
                    _classe(100 * aggregato["consensus_top3"]
                            / max(aggregato["consensus_out_of"], 1)),
                    aggregato["consensus_top3"],
                    aggregato["consensus_out_of"]))
        if aggregato["top_chunk"]:
            p.append("<p>Passaggio più recuperabile:<br><code>%s</code></p>"
                     % _e(aggregato["top_chunk"]))
        p.append("</div>")
    if referto["rrf_simulation"]:
        p.append("<table><tr><th>Query</th><th>Consenso</th>"
                 "<th>Passaggio migliore</th></tr>")
        for voce in referto["rrf_simulation"]:
            p.append("<tr><td><code>%s</code></td><td class='num'>%d/%d</td>"
                     "<td>%s</td></tr>"
                     % (_e(voce["query"]), voce["consensus_top3"],
                        voce["consensus_out_of"],
                        _e(voce["top_chunk"] or "—")))
        p.append("</table>")

    cit = referto.get("citability")
    if cit and cit.get("profiles"):
        p.append("<h2>Profili di citabilità IA</h2>")
        p.append("<p class='meta'>Mercato: %s</p><table>"
                 % _e(cit.get("market")))
        for assistente, valore in cit["profiles"].items():
            larghezza = (valore or 0) * 2
            barra = ("<span class='bar %s' style='width:%.0fpx'></span>"
                     % (_classe(valore), larghezza))
            testo = ("%.1f" % valore) if valore is not None else "n/d"
            p.append("<tr><td>%s</td><td class='num %s'>%s</td><td>%s</td>"
                     "</tr>" % (_e(assistente), _classe(valore), testo,
                                barra))
        if cit.get("score") is not None:
            p.append("<tr><td><strong>Indice composito</strong></td>"
                     "<td class='num %s'><strong>%.1f</strong></td><td></td>"
                     "</tr>" % (_classe(cit["score"]), cit["score"]))
        p.append("</table>")
        # Il disclaimer sta subito sotto i numeri, non in fondo alla
        # pagina: chi legge il punteggio deve leggere anche cosa non è.
        p.append("<p class='disclaimer'>%s</p>" % _e(cit.get("disclaimer")))
        if cit.get("issues"):
            p.append("<ul>%s</ul>"
                     % "".join("<li>%s</li>" % _e(i) for i in cit["issues"]))

    llm = referto.get("llm_judgement") or {}
    if llm.get("motivazione"):
        p.append("<h2>Giudizio LLM</h2><div class='card'>")
        p.append("<p class='meta'>%s · %s passaggi valutati</p>"
                 % (_e(llm.get("model")), _e(llm.get("chunk_valutati"))))
        if llm.get("score") is not None:
            p.append("<p class='%s'><strong>Citabilità stimata: %s/100"
                     "</strong></p>" % (_classe(llm["score"]),
                                        _e(llm["score"])))
        p.append("<p>%s</p>" % _e(llm["motivazione"]))
        for titolo, chiave in (("Punti di forza", "punti_forti"),
                               ("Da migliorare", "punti_deboli")):
            voci = llm.get(chiave) or []
            if voci:
                p.append("<p><strong>%s</strong></p><ul>%s</ul>"
                         % (titolo,
                            "".join("<li>%s</li>" % _e(v) for v in voci)))
        p.append("</div>")

    if referto["robots_ignored"] or referto["skipped"]:
        p.append("<h2>Cosa non è stato guardato</h2>")
        if referto["robots_ignored"]:
            p.append("<p class='bad'>robots.txt ignorato per dichiarazione "
                     "di proprietà del dominio.</p>")
        if referto["skipped"]:
            p.append("<p>%d URL saltati:</p><ul>%s</ul>"
                     % (len(referto["skipped"]),
                        "".join("<li>%s</li>" % _e(m)
                                for m in referto["skipped"])))

    p.append("</main></body></html>")
    return "".join(p)


RENDERERS = {"text": render_text, "json": render_json, "html": render_html}
