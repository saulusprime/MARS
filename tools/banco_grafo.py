#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — banco di prova del JavaScript del referto (R48).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0

`pytest` verifica di `REFERTO_JS` il **testo**: che non abbia origini
esterne, che non porti dentro dati del sito, che compaia solo dove c'e'
un grafo. Non lo esegue, e non puo': servirebbe `node` e con esso
`jsdom`, e una suite che gira qui e non su un clone appena fatto e' la
trappola gia' pagata con `node_modules/axe-core`.

Questo file colma il buco a mano. Costruisce un referto vero, ne
estrae l'SVG del grafo, e fa girare lo script su un DOM finto quanto
basta, controllando nove comportamenti. **Va rilanciato ogni volta che
si tocca `REFERTO_JS`**, finche' R48 non sceglie una delle sue tre
strade.

    python3 tools/banco_grafo.py

Codici di uscita: 0 tutto verificato; 1 un controllo fallito; 2 `node`
non disponibile.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import pagina                                    # noqa: E402
from mars_report import REFERTO_JS, build_report, render_html  # noqa: E402

# Quattro pagine: un triangolo di link piu' una che nessuno raggiunge.
# L'orfana serve a verificare che gli anelli la mettano fuori da tutti.
COLLEGAMENTI = {
    "https://e.test/": ["https://e.test/a/", "https://e.test/b/"],
    "https://e.test/a/": ["https://e.test/b/"],
    "https://e.test/b/": ["https://e.test/"],
    "https://e.test/orfana/": [],
}

BANCO = r"""
const fs = require("fs");
const svgTesto = fs.readFileSync(process.argv[2], "utf8");

class Elemento {
  constructor(tag, attr = {}) {
    this.tag = tag; this.attr = attr; this.figli = []; this.testo = "";
    this.ascoltatori = {};
    this._classi = new Set((attr.class || "").split(" ").filter(Boolean));
    const self = this;
    this.classList = {
      toggle(c, on) { on ? self._classi.add(c) : self._classi.delete(c); },
      remove(c) { self._classi.delete(c); },
      contains(c) { return self._classi.has(c); },
    };
  }
  getAttribute(n) {
    return n === "class" ? [...this._classi].join(" ")
      : (n in this.attr ? this.attr[n] : null);
  }
  setAttribute(n, v) { this.attr[n] = String(v); }
  removeAttribute(n) { delete this.attr[n]; }
  addEventListener(n, f) { (this.ascoltatori[n] ||= []).push(f); }
  emetti(n) { (this.ascoltatori[n] || []).forEach(f => f({ key: "x" })); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  querySelectorAll(sel) {
    const cerca = (e, out) => {
      for (const f of e.figli) {
        if (sel.startsWith(".") ? f._classi.has(sel.slice(1)) : f.tag === sel) {
          out.push(f);
        }
        cerca(f, out);
      }
      return out;
    };
    return cerca(this, []);
  }
  get textContent() { return this.testo; }
  set textContent(v) { this.testo = v; }
}

/* Parser grossolano: l'SVG del referto e' generato da noi, quindi
   niente entita', niente attributi con apici doppi, niente sorprese. */
function parse(testo) {
  const radice = new Elemento("svg", { viewBox: "0 0 780 540" });
  const pila = [radice];
  const re = /<(\/?)(\w+)([^>]*?)(\/?)>|([^<]+)/g;
  let m;
  while ((m = re.exec(testo))) {
    if (m[5]) {
      if (pila.length > 1) { pila[pila.length - 1].testo += m[5]; }
      continue;
    }
    const [, chiude, tag, grezzo, autoconcluso] = m;
    if (tag === "svg") { if (chiude) { break; } continue; }
    if (chiude) { pila.pop(); continue; }
    const attr = {};
    for (const a of grezzo.matchAll(/([\w-]+)='([^']*)'/g)) { attr[a[1]] = a[2]; }
    const el = new Elemento(tag, attr);
    pila[pila.length - 1].figli.push(el);
    if (!autoconcluso) { pila.push(el); }
  }
  return radice;
}

const svg = parse(svgTesto);
const comandi = new Elemento("p", { hidden: "" });
const stato = new Elemento("p", {});
const bottoni = {};
for (const id of ["grafo-forze", "grafo-anelli", "grafo-piu", "grafo-meno",
                  "grafo-zero"]) { bottoni[id] = new Elemento("button", {}); }
global.document = {
  getElementById(id) {
    return { "grafo": svg, "grafo-comandi": comandi, "grafo-stato": stato,
             ...bottoni }[id] || null;
  },
};

eval(fs.readFileSync(process.argv[3], "utf8"));

const nodi = svg.querySelectorAll(".grafo-nodo");
const archi = svg.querySelectorAll(".grafo-arco");
const dove = () => nodi.map(n => [+n.getAttribute("cx"), +n.getAttribute("cy")]);
const partenza = dove();
let rossi = 0;
function controlla(nome, esito, dettaglio) {
  if (!esito) { rossi += 1; }
  console.log((esito ? "  ok   " : "  ROSSO") + "  " + nome +
              (dettaglio === undefined ? "" : "  [" + dettaglio + "]"));
}

controlla("i comandi vengono accesi", !("hidden" in comandi.attr));
controlla("i nodi diventano focalizzabili",
          nodi.every(n => n.getAttribute("tabindex") === "0"));

nodi[0].emetti("focus");
const spenti = nodi.filter(n => n.classList.contains("spento")).length;
controlla("l'evidenziazione spegne i non vicini", spenti === 1,
          spenti + " spenti su " + nodi.length);
controlla("il fuoco scrive nella regione di stato",
          stato.textContent.indexOf("link in entrata") > 0);

nodi[0].emetti("blur");
controlla("uscendo si ripulisce tutto",
          nodi.every(n => !n.classList.contains("spento")) &&
          archi.every(a => !a.classList.contains("spento")) &&
          stato.textContent === "");

bottoni["grafo-anelli"].emetti("click");
const raggi = dove().map(([x, y]) => Math.round(Math.hypot(x - 390, y - 270)));
controlla("gli anelli: home al centro, orfana piu' fuori",
          raggi[0] === 0 && raggi[3] === Math.max(...raggi), raggi.join(" "));
controlla("gli archi seguono i nodi",
          Math.abs(+archi[0].getAttribute("x1")
                   - dove()[+archi[0].getAttribute("data-s")][0]) < 0.2);

bottoni["grafo-forze"].emetti("click");
controlla("si torna esattamente al layout calcolato in Python",
          JSON.stringify(dove()) === JSON.stringify(partenza));

bottoni["grafo-piu"].emetti("click");
const ingrandito = svg.getAttribute("viewBox");
bottoni["grafo-zero"].emetti("click");
controlla("zoom e reimposta",
          ingrandito !== "0 0 780 540" &&
          svg.getAttribute("viewBox") === "0 0 780 540", ingrandito);

process.exit(rossi === 0 ? 0 : 1);
"""


def svg_del_grafo() -> str:
    """L'SVG statico come lo produce il referto vero, non a mano."""
    pagine = {u: dict(pagina(url=u), link_targets=list(uscenti))
              for u, uscenti in COLLEGAMENTI.items()}
    referto = build_report({}, {
        "url": "https://e.test/", "pages": pagine, "urls": list(pagine),
        "chunks": [c for p in pagine.values() for c in p["chunks"]],
        "queries": [], "skipped": [], "market": "global",
        "discovery": "sitemap"})
    html = render_html(referto)
    inizio = html.index("<svg id='grafo'")
    return html[inizio:html.index("</svg>", inizio) + 6]


def main() -> int:
    if shutil.which("node") is None:
        print("node non e' nel PATH: il banco non puo' girare.")
        return 2
    cartella = tempfile.mkdtemp(prefix="mars-banco-")
    try:
        percorsi = {}
        for nome, contenuto in (("grafo.svg", svg_del_grafo()),
                                ("referto.js", REFERTO_JS),
                                ("banco.js", BANCO)):
            percorsi[nome] = os.path.join(cartella, nome)
            with open(percorsi[nome], "w", encoding="utf-8") as fh:
                fh.write(contenuto)
        print("Banco di prova del grafo (R48) — %d nodi nell'SVG"
              % svg_del_grafo().count("<circle"), flush=True)
        esito = subprocess.run(
            ["node", percorsi["banco.js"], percorsi["grafo.svg"],
             percorsi["referto.js"]])
        print("tutto verificato." if esito.returncode == 0
              else "QUALCOSA NON VA: vedi i ROSSO qui sopra.")
        return esito.returncode
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
