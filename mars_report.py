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
import math
import os
import time
from typing import Dict, List, Optional

from mars_core import (MODULES_REGISTRY, __version__, describe_chunk,
                       normalizza_risultato, reciprocal_rank_fusion)

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
        # Un plugin che non rispetta il contratto non deve far cadere
        # il referto DOPO che tutti i moduli sono girati: diventa
        # un'area fallita e dichiarata.
        res = normalizza_risultato(nome, results[nome])
        errore = res.get("error")
        aree.append({
            "module": nome,
            "label": descrizione,
            "score": res.get("score"),
            "status": "error" if errore else res.get("status"),
            # Il motivo del fallimento E' il rilievo dell'area: senza,
            # il referto direbbe solo "non misurato" senza dire perche'.
            "issues": ([str(errore)] if errore
                       else list(res.get("issues") or [])),
            # Con quale strumento e a quale livello: un punteggio di
            # accessibilita' senza il livello WCAG non significa nulla.
            "tool": res.get("tool"),
            "wcag_level": res.get("wcag_level"),
            "pages_tested": res.get("pages_tested"),
            # Elenco dei singoli controlli, quando lo strumento lo
            # fornisce: e' cio' che Lighthouse mostra nella sua
            # sezione, e senza non si sa QUALE controllo sia fallito.
            "audits": list(res.get("audits") or []) or None,
            "form_factor": res.get("form_factor"),
            # False quando lo strumento non e' arrivato in fondo (ZAP
            # interrotto dal timeout, axe che non ha caricato tutte le
            # pagine): un punteggio parziale non e' un punteggio pieno.
            "complete": res.get("complete"),
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
                      "answer_shaped_signals", "page_signals", "languages")
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


# Come si legge lo "status" di un'area nelle viste umane. "surface" e'
# l'unico che convive con un punteggio, ed e' quello che R21 ha trovato
# invisibile: 100/100 dai soli header HTTP e 100/100 da una scansione
# ZAP completa sono lo stesso numero e due fatti diversi.
STATO_LEGGIBILE = {
    "surface": "controllo di superficie",
    "unavailable": "non misurato",
    "disabled": "disattivato",
    "error": "errore del modulo",
}


def _qualificatori(area: dict) -> List[str]:
    """Con che cosa e' stato ottenuto il punteggio, e quanto vale.

    Un numero senza strumento, profondita' e campione non e' una misura
    ma un'impressione. La funzione e' condivisa fra le due viste umane
    perche' testo e HTML non possano tornare a dire cose diverse:
    prima queste informazioni comparivano solo dove esisteva un
    wcag_level, cioe' per la sola accessibilita'.

    Lo stato si annota solo se convive con un punteggio: quando il
    punteggio manca, "non misurato" e "disattivato" prendono gia' il
    posto del numero e ripeterli sarebbe rumore.
    """
    pezzi: List[str] = []
    if area.get("tool"):
        pezzi.append(str(area["tool"]))
    if area.get("wcag_level"):
        pezzi.append(str(area["wcag_level"]))
    if area.get("score") is not None and area.get("status") in STATO_LEGGIBILE:
        pezzi.append(STATO_LEGGIBILE[area["status"]])
    if area.get("complete") is False:
        pezzi.append("scansione parziale")
    if area.get("pages_tested"):
        pezzi.append("%d pagine esaminate" % area["pages_tested"])
    if area.get("form_factor"):
        # Un referto mobile e uno desktop non sono confrontabili.
        pezzi.append(str(area["form_factor"]))
    controlli = area.get("audits") or []
    if controlli:
        superati = sum(1 for c in controlli if c.get("passed"))
        falliti = sum(1 for c in controlli
                      if not c.get("passed") and not c.get("manual"))
        pezzi.append("%d controlli superati, %d falliti"
                     % (superati, falliti))
    return pezzi


def _riga_area(area: dict) -> str:
    if area["score"] is None:
        stato = STATO_LEGGIBILE.get(area["status"], "non misurato")
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
        # Con che cosa e' stato misurato, per OGNI area e non piu' per
        # la sola accessibilita': senza, 100/100 dai soli header HTTP
        # e 100/100 da un WAPT completo erano due righe identiche.
        qualifiche = _qualificatori(area)
        if qualifiche:
            righe.append("  " + " · ".join(qualifiche))
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


def _e(valore: object) -> str:
    """Escape: il referto contiene testo preso dal sito analizzato."""
    return html.escape(str(valore if valore is not None else ""))


# Soglie e colori di Lighthouse, adottati perche' il referto gli
# somigli: chi legge entrambi non deve tradurre due scale diverse.
# ATTENZIONE: la scala precedente di MARS era 80/50; questa e' 90/50,
# quindi lo stesso punteggio puo' cambiare colore rispetto ai referti
# generati prima. Il colore e' una convenzione, il numero no.
SOGLIA_BUONO = 90
SOGLIA_MEDIO = 50

CSS = """
:root { --ok:#0cce6b; --warn:#ffa400; --bad:#ff4e42; --bg:#fff;
        --fg:#1f2328; --muted:#5f6771; --line:#dfe3e8; --card:#f7f9fa;
        --track:#e8ebee; --ombra:0 1px 3px rgba(0,0,0,.08); }
@media (prefers-color-scheme: dark) {
  :root { --bg:#12161c; --fg:#e6edf3; --muted:#98a1ad; --line:#2a3038;
          --card:#1a1f27; --track:#2a3038; --ombra:none; } }
* { box-sizing:border-box; }
body { margin:0; padding:0 0 3rem; background:var(--bg); color:var(--fg);
       font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:64rem; margin:0 auto; padding:0 1rem; }
header.testata { border-bottom:1px solid var(--line); margin-bottom:1.5rem;
                 padding:1.75rem 0 1.25rem; }
h1 { font-size:1.35rem; margin:0 0 .3rem; letter-spacing:-.01em; }
h2 { font-size:1.05rem; margin:2.25rem 0 .85rem;
     border-bottom:1px solid var(--line); padding-bottom:.4rem; }
h3 { font-size:.95rem; margin:0; }
.meta { color:var(--muted); font-size:.87rem; margin:.15rem 0; }
.meta code { word-break:break-all; }

/* --- fascia dei quadranti, la firma visiva di Lighthouse --- */
.quadranti { display:flex; flex-wrap:wrap; gap:.5rem 1.5rem;
             justify-content:center; padding:1.25rem 0 .5rem; }
.quadrante { width:8.5rem; text-align:center; }
.quadrante svg { display:block; margin:0 auto; width:5.5rem; height:5.5rem; }
.quadrante .nome { font-size:.82rem; margin-top:.35rem; line-height:1.3;
                   color:var(--fg); }
.quadrante .nota { font-size:.72rem; color:var(--muted); }
.quadrante .nota.parziale, .strumento.parziale { color:var(--warn); }
.anello-fondo { stroke:var(--track); }
.valore { font:600 30px/1 system-ui,sans-serif; }
.valore.piccolo { font-size:22px; }

/* --- legenda della scala --- */
.legenda { display:flex; flex-wrap:wrap; gap:1rem; justify-content:center;
           font-size:.78rem; color:var(--muted); padding:.5rem 0 .25rem; }
.legenda span { white-space:nowrap; }
.pallino { display:inline-block; width:.62rem; height:.62rem;
           border-radius:50%; vertical-align:-1px; margin-right:.3rem; }
.pallino.vuoto { background:none; border:1.5px dashed var(--muted); }

/* --- schede d'area --- */
.area { background:var(--card); border:1px solid var(--line);
        border-radius:.6rem; padding:.9rem 1rem; margin:.6rem 0;
        box-shadow:var(--ombra); }
.area .riga { display:flex; align-items:baseline; gap:.6rem;
              justify-content:space-between; }
.punteggio { font-variant-numeric:tabular-nums; font-weight:600;
             white-space:nowrap; }
.strumento { font-size:.78rem; color:var(--muted); margin:.3rem 0 0; }
ul.rilievi { margin:.55rem 0 0; padding-left:1.15rem; }
ul.controlli { list-style:none; margin:.6rem 0 0; padding:0; }
ul.controlli li { font-size:.88rem; margin:.22rem 0; display:flex;
                  gap:.5rem; align-items:baseline; }
ul.controlli .segno { font-weight:700; flex:0 0 1rem; text-align:center; }
ul.controlli li.fallito .segno { color:var(--bad); }
ul.controlli li.superato .segno { color:var(--ok); }
ul.controlli li.manuale .segno, ul.controlli li.manuale { color:var(--muted); }
ul.controlli .dettaglio { color:var(--muted); font-size:.82rem;
                          word-break:break-all; }
ul.rilievi li { font-size:.88rem; margin:.15rem 0; }
.nessun-rilievo { font-size:.85rem; color:var(--muted); margin:.4rem 0 0; }

table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:.5rem .6rem;
        border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:.75rem; text-transform:uppercase; color:var(--muted);
     letter-spacing:.04em; }
td.num { text-align:right; font-variant-numeric:tabular-nums;
         white-space:nowrap; }
.ok{color:var(--ok)} .warn{color:var(--warn)} .bad{color:var(--bad)}
.muted{color:var(--muted)}
.bar { display:inline-block; height:.5rem; border-radius:.25rem;
       background:currentColor; vertical-align:middle; min-width:2px; }
.card { background:var(--card); border:1px solid var(--line);
        border-radius:.6rem; padding:1rem; margin:.6rem 0;
        box-shadow:var(--ombra); }
.disclaimer { font-size:.83rem; color:var(--muted); font-style:italic; }
code { background:var(--track); padding:.1rem .3rem; border-radius:.25rem;
       font-size:.85em; }
.grande { font-size:1.6rem; font-weight:600;
          font-variant-numeric:tabular-nums; }
@media (max-width:40rem){
  .quadrante { width:6.5rem; }
  .quadrante svg { width:4.5rem; height:4.5rem; }
  th,td { padding:.4rem .35rem; font-size:.9rem; }
}
"""

# Geometria del quadrante: raggio 56 in un viewBox 120x120.
_RAGGIO = 56
_CIRCONFERENZA = 2 * math.pi * _RAGGIO


def _classe(valore: Optional[float]) -> str:
    if valore is None:
        return "muted"
    return ("ok" if valore >= SOGLIA_BUONO
            else "warn" if valore >= SOGLIA_MEDIO else "bad")


def _quadrante(valore: Optional[float], nome: str, nota: str = "",
               parziale: bool = False) -> str:
    """Un quadrante circolare, come quelli in testa a un referto Lighthouse.

    E' SVG inline calcolato qui: l'arco si ottiene con stroke-dasharray
    sulla circonferenza, quindi non serve alcuno script — e il referto
    resta un file solo, apribile senza rete (principio del referto
    autoconsistente).

    Un valore assente NON diventa uno zero: si disegna un anello
    tratteggiato con un trattino al centro, perche' "non misurato" e
    "misurato zero" sono cose diverse e il referto le distingue.
    """
    classe = _classe(valore)
    if valore is None:
        arco = ("<circle class='anello-fondo' cx='60' cy='60' r='%d' "
                "fill='none' stroke-width='9' stroke-dasharray='4 6'/>"
                % _RAGGIO)
        testo = ("<text class='valore muted' x='60' y='60' "
                 "text-anchor='middle' dominant-baseline='central' "
                 "fill='currentColor'>—</text>")
    else:
        pieno = _CIRCONFERENZA * max(0.0, min(valore, 100.0)) / 100.0
        arco = ("<circle class='anello-fondo' cx='60' cy='60' r='%d' "
                "fill='none' stroke-width='9'/>" % _RAGGIO)
        if pieno > 0.5:
            # Sotto mezzo pixel l'arco non si disegna: con
            # stroke-linecap arrotondato un valore di zero lascerebbe
            # comunque un puntino colorato, che si legge come "poco"
            # invece che come "niente".
            arco += (
                "<circle cx='60' cy='60' r='%d' fill='none' "
                "stroke='currentColor' stroke-width='9' "
                "stroke-linecap='round' stroke-dasharray='%.2f %.2f' "
                "transform='rotate(-90 60 60)'/>"
                % (_RAGGIO, pieno, _CIRCONFERENZA - pieno))
        testo = ("<text class='valore' x='60' y='60' text-anchor='middle' "
                 "dominant-baseline='central' fill='currentColor'>%.0f</text>"
                 % valore)
    return (
        "<div class='quadrante %s'>"
        "<svg viewBox='0 0 120 120' role='img' aria-label='%s: %s'>%s%s</svg>"
        "<div class='nome'>%s</div>%s</div>"
        # L'aria-label descrive il solo quadrante: la qualifica sta
        # nella nota qui sotto, che e' un fratello nel DOM e viene letta
        # subito dopo. Ripeterla qui la duplicherebbe, e sbagliarla —
        # "superficie" su una scansione soltanto interrotta — sarebbe
        # peggio che ometterla.
        % (classe, _e(nome),
           "non misurato" if valore is None else "%.0f su 100" % valore,
           arco, testo, _e(nome),
           "<div class='nota%s'>%s</div>"
           % (" parziale" if parziale else "", _e(nota)) if nota else ""))


def _etichetta_area(area: dict) -> str:
    """Nome dell'area senza il numero d'ordine: nel quadrante lo spazio
    e' poco e "1. Tecnica" non aggiunge nulla a "Tecnica"."""
    etichetta = area.get("label") or area.get("module") or "?"
    return etichetta.split(". ", 1)[-1]


def _stato_area(area: dict) -> str:
    return STATO_LEGGIBILE.get(area.get("status"), "non misurato")


def _fascia_quadranti(referto: dict) -> str:
    """La fascia in testa, come in Lighthouse: un quadrante per area.

    Le aree lessicale e semantica non producono un voto ma una
    classifica, e mettere loro uno zero sarebbe una bugia: al loro
    posto la fascia mostra i due segnali DERIVATI che C1 gia' calcola —
    consenso RRF e contenuto in forma di risposta — dichiarati come
    tali nella riga sotto il quadrante.
    """
    pezzi = []
    for area in referto["areas"]:
        if area["module"] in ("mars_lexical", "mars_semantic"):
            continue
        if area["score"] is None:
            nota, parziale = _stato_area(area), False
        else:
            # Sotto il quadrante lo spazio e' poco: strumento, e la
            # parola che cambia il senso del numero. Un 100 verde
            # ottenuto guardando tre header non deve poter passare
            # per un WAPT completo.
            breve = [area["tool"]] if area.get("tool") else []
            parziale = (area.get("status") == "surface"
                        or area.get("complete") is False)
            if area.get("status") == "surface":
                breve.append("superficie")
            if area.get("complete") is False:
                breve.append("parziale")
            nota = " · ".join(breve)
        pezzi.append(_quadrante(area["score"], _etichetta_area(area), nota,
                                parziale))

    aggregato = referto.get("rrf_aggregate")
    if aggregato and aggregato.get("consensus_out_of"):
        consenso = (100.0 * aggregato["consensus_top3"]
                    / aggregato["consensus_out_of"])
        pezzi.append(_quadrante(consenso, "Recuperabilità",
                                "consenso %d/%d"
                                % (aggregato["consensus_top3"],
                                   aggregato["consensus_out_of"])))
    sem = referto.get("semantic") or {}
    if sem.get("n_chunks"):
        pezzi.append(_quadrante(100.0 * (sem.get("answer_shaped_ratio") or 0),
                                "In forma di risposta",
                                "su %d chunk" % sem["n_chunks"]))
    if not pezzi:
        return ""
    return "<div class='quadranti'>%s</div>" % "".join(pezzi)


def _legenda() -> str:
    """La scala e' una convenzione: dichiararla evita che il colore
    venga letto come una misura."""
    return (
        "<div class='legenda'>"
        "<span><i class='pallino bad'></i>0-49</span>"
        "<span><i class='pallino warn'></i>50-89</span>"
        "<span><i class='pallino ok'></i>90-100</span>"
        "<span><i class='pallino vuoto'></i>non misurato</span>"
        "</div>"
        "<style>.pallino.bad{background:var(--bad)}"
        ".pallino.warn{background:var(--warn)}"
        ".pallino.ok{background:var(--ok)}</style>")


def _elenco_controlli(controlli: List[dict]) -> str:
    """I singoli controlli, nell'ordine in cui Lighthouse li mostra.

    Prima i falliti — sono quelli su cui si interviene — poi quelli da
    verificare a mano, infine i superati. Elencare anche i superati non
    e' ridondanza: senza, non si sa CHE COSA sia stato guardato, e un
    punteggio pieno resta indistinguibile da un controllo che non e'
    stato eseguito affatto.
    """
    def chiave(c: dict) -> int:
        if c.get("manual"):
            return 1
        return 0 if not c.get("passed") else 2

    righe = []
    for c in sorted(controlli, key=chiave):
        if c.get("manual"):
            classe, segno = "manuale", "?"
        elif c.get("passed"):
            # NON "ok": e' gia' una classe globale del CSS e
            # colorerebbe di verde l'intera riga invece del solo segno.
            classe, segno = "superato", "\u2713"
        else:
            classe, segno = "fallito", "\u2717"
        dettaglio = ", ".join(c.get("items") or [])
        righe.append(
            "<li class='%s'><span class='segno'>%s</span><span>%s%s</span>"
            "</li>"
            % (classe, segno, _e(c.get("title")),
               "<br><span class='dettaglio'>%s</span>" % _e(dettaglio)
               if dettaglio else ""))
    return "<ul class='controlli'>%s</ul>" % "".join(righe)


def _scheda_area(area: dict, referto: dict) -> str:
    """Una scheda per area, con i rilievi sotto — come le categorie di
    Lighthouse elencano i propri audit."""
    if area["score"] is None:
        voto = "<span class='muted'>%s</span>" % _stato_area(area)
    else:
        voto = ("<span class='%s'>%.0f<span class='muted'>/100</span></span>"
                % (_classe(area["score"]), area["score"]))

    corpo = []
    if area["module"] == "mars_lexical":
        corpo.append("<p class='strumento'>Classifica BM25, non un voto. "
                     "Passaggio in testa: <code>%s</code></p>"
                     % _e((referto.get("lexical") or {}).get("top_chunk")
                          or "—"))
        voto = "<span class='muted'>classifica</span>"
    elif area["module"] == "mars_semantic":
        sem = referto.get("semantic") or {}
        corpo.append("<p class='strumento'>Classifica vettoriale, non un "
                     "voto. %.0f%% di %s chunk in forma di risposta.</p>"
                     % (100 * (sem.get("answer_shaped_ratio") or 0),
                        sem.get("n_chunks") or 0))
        # Segnali di PAGINA, tenuti fuori dal rapporto ma non nascosti:
        # dicono qualcosa di vero sul sito (vedi R19).
        for nome, quante in (sem.get("page_signals") or {}).items():
            corpo.append("<p class='strumento'>%s: %d pagine su %d.</p>"
                         % (_e(nome), quante, referto["pages_crawled"]))
        voto = "<span class='muted'>classifica</span>"

    qualifiche = _qualificatori(area)
    if qualifiche:
        # Marcato quando il punteggio non e' una misura piena: e' la
        # differenza fra "sicuro" e "non abbiamo guardato a fondo".
        parziale = (area.get("status") == "surface"
                    or area.get("complete") is False)
        corpo.append("<p class='strumento%s'>%s</p>"
                     % (" parziale" if parziale else "",
                        _e(" · ".join(qualifiche))))
    if area.get("audits"):
        # L'elenco dei controlli sostituisce quello dei rilievi: li
        # contiene gia' tutti, e in piu' dice che cosa e' stato
        # guardato e superato — che e' l'informazione che mancava.
        corpo.append(_elenco_controlli(area["audits"]))
    elif area["issues"]:
        corpo.append("<ul class='rilievi'>%s</ul>"
                     % "".join("<li>%s</li>" % _e(i) for i in area["issues"]))
    elif area["score"] is not None:
        corpo.append("<p class='nessun-rilievo'>Nessun rilievo.</p>")

    return ("<div class='area'><div class='riga'><h3>%s</h3>"
            "<span class='punteggio'>%s</span></div>%s</div>"
            % (_e(area["label"]), voto, "".join(corpo)))


def _sezione_rrf(referto: dict, p: List[str]) -> None:
    aggregato = referto.get("rrf_aggregate")
    simulazione = referto.get("rrf_simulation") or []
    if not aggregato and not simulazione:
        return
    p.append("<h2>Simulazione RRF</h2>")
    if aggregato:
        quota = (100.0 * aggregato["consensus_top3"]
                 / max(aggregato["consensus_out_of"], 1))
        p.append("<div class='card'><p class='meta'>Consenso fra il "
                 "recuperatore lessicale e quello vettoriale, aggregato su "
                 "%d query — la misura più solida, perché un accordo su "
                 "una sola domanda può essere un caso.</p>"
                 "<p class='grande %s'>%d/%d</p>"
                 % (len(simulazione), _classe(quota),
                    aggregato["consensus_top3"],
                    aggregato["consensus_out_of"]))
        if aggregato.get("top_chunk"):
            p.append("<p class='meta'>Passaggio più recuperabile:<br>"
                     "<code>%s</code></p>" % _e(aggregato["top_chunk"]))
        p.append("</div>")
    if simulazione:
        p.append("<table><tr><th>Query</th><th>Consenso</th>"
                 "<th>Passaggio migliore</th></tr>")
        for voce in simulazione:
            quota = (100.0 * voce["consensus_top3"]
                     / max(voce["consensus_out_of"], 1))
            p.append("<tr><td><code>%s</code></td>"
                     "<td class='num %s'>%d/%d</td><td>%s</td></tr>"
                     % (_e(voce["query"]), _classe(quota),
                        voce["consensus_top3"], voce["consensus_out_of"],
                        _e(voce["top_chunk"] or "—")))
        p.append("</table>")


def _sezione_citabilita(referto: dict, p: List[str]) -> None:
    cit = referto.get("citability")
    if not cit or not cit.get("profiles"):
        return
    p.append("<h2>Profili di citabilità IA</h2>")
    p.append("<p class='meta'>Mercato: %s</p><table>" % _e(cit.get("market")))
    for assistente, valore in cit["profiles"].items():
        barra = ("<span class='bar %s' style='width:%.0f%%'></span>"
                 % (_classe(valore), (valore or 0)))
        testo = ("%.1f" % valore) if valore is not None else "n/d"
        p.append("<tr><td>%s</td><td class='num %s'>%s</td>"
                 "<td style='width:55%%'>%s</td></tr>"
                 % (_e(assistente), _classe(valore), testo, barra))
    if cit.get("score") is not None:
        p.append("<tr><td><strong>Indice composito</strong></td>"
                 "<td class='num %s'><strong>%.1f</strong></td><td></td></tr>"
                 % (_classe(cit["score"]), cit["score"]))
    p.append("</table>")
    # Il disclaimer sta subito sotto i numeri, non in fondo alla pagina:
    # chi legge il punteggio deve leggere anche cosa non è.
    p.append("<p class='disclaimer'>%s</p>" % _e(cit.get("disclaimer")))
    if cit.get("issues"):
        p.append("<ul class='rilievi'>%s</ul>"
                 % "".join("<li>%s</li>" % _e(i) for i in cit["issues"]))


def _sezione_llm(referto: dict, p: List[str]) -> None:
    llm = referto.get("llm_judgement") or {}
    if not llm.get("motivazione"):
        return
    p.append("<h2>Giudizio LLM</h2><div class='card'>")
    p.append("<p class='meta'>%s · %s passaggi valutati</p>"
             % (_e(llm.get("model")), _e(llm.get("chunk_valutati"))))
    if llm.get("score") is not None:
        p.append("<p class='grande %s'>%s<span class='muted'>/100</span></p>"
                 % (_classe(llm["score"]), _e(llm["score"])))
    p.append("<p>%s</p>" % _e(llm["motivazione"]))
    if llm.get("passaggio_migliore"):
        p.append("<p class='meta'>Passaggio migliore: <code>%s</code></p>"
                 % _e(llm["passaggio_migliore"]))
    for titolo, chiave in (("Punti di forza", "punti_forti"),
                           ("Da migliorare", "punti_deboli")):
        voci = llm.get(chiave) or []
        if voci:
            p.append("<p class='strumento'><strong>%s</strong></p>"
                     "<ul class='rilievi'>%s</ul>"
                     % (titolo,
                        "".join("<li>%s</li>" % _e(v) for v in voci)))
    p.append("</div>")


def render_html(referto: dict) -> str:
    """Referto HTML nello stile di Lighthouse, esteso alle nostre aree.

    Autoconsistente per costruzione: CSS incorporato, favicon come data
    URI, quadranti in SVG calcolato qui. Nessuna CDN e NESSUNO SCRIPT —
    un referto deve potersi aprire fra due anni, da un archivio, senza
    rete.
    """
    p: List[str] = []
    icona = _favicon_data_uri()
    p.append("<!doctype html><html lang='it'><head><meta charset='utf-8'>")
    p.append("<meta name='viewport' content='width=device-width,"
             "initial-scale=1'>")
    p.append("<title>MARS Beacon — %s</title>" % _e(referto["url"]))
    if icona:
        p.append("<link rel='icon' href='%s'>" % icona)
    p.append("<style>%s</style></head><body><main>" % CSS)

    p.append("<header class='testata'><h1>MARS Beacon</h1>")
    p.append("<p class='meta'><code>%s</code></p>" % _e(referto["url"]))
    p.append("<p class='meta'>%s · %s pagine trovate via %s · %s chunk · "
             "mercato %s · v%s</p></header>"
             % (_e(referto["generated_at"]), referto["pages_crawled"],
                _e(referto.get("discovery")), referto["chunks"],
                _e(referto["market"]), _e(referto["version"])))

    p.append(_fascia_quadranti(referto))
    p.append(_legenda())

    p.append("<h2>Aree</h2>")
    for area in referto["areas"]:
        p.append(_scheda_area(area, referto))

    _sezione_rrf(referto, p)
    _sezione_citabilita(referto, p)
    _sezione_llm(referto, p)

    if referto["robots_ignored"] or referto["skipped"]:
        p.append("<h2>Cosa non è stato guardato</h2>")
        if referto["robots_ignored"]:
            p.append("<p class='bad'>robots.txt ignorato per dichiarazione "
                     "di proprietà del dominio.</p>")
        if referto["skipped"]:
            p.append("<div class='card'><p class='meta'>%d URL saltati:</p>"
                     "<ul class='rilievi'>%s</ul></div>"
                     % (len(referto["skipped"]),
                        "".join("<li>%s</li>" % _e(m)
                                for m in referto["skipped"])))

    p.append("</main></body></html>")
    return "".join(p)


RENDERERS = {"text": render_text, "json": render_json, "html": render_html}
