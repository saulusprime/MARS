## Principi da non violare

1. **Gli algoritmi core sono scritti a mano** — crawler, BM25, proxy
   char-TFIDF, RRF, chunker. Non sostituirli con librerie: sono il
   valore del progetto, non un dettaglio implementativo.
2. **Degradazione graduale.** Lighthouse, ZAP, sentence-transformers,
   Anthropic sono tutti opzionali. Se mancano si ripiega e **lo si
   dichiara**; non si solleva e non si inventa un punteggio.
3. **Moduli plugin, contratto sopra.** Il `context` e ciò che contiene
   restano **dict**: attraversano il confine dei plugin, e imporre
   classi di `mars_core` costringerebbe ogni modulo esterno a
   importarle. I `@dataclass` valgono per le strutture interne a un
   modulo.
4. **CLI e API sono due interfacce sopra lo stesso motore.**
   `build_context()`, `MODULES_REGISTRY` e `load_external_module()`
   stanno in `mars_core`: se ti trovi a copiare qualcosa fra
   `mars_audit.py` e `mars_api.py`, appartiene a `mars_core`.
5. **Onestà metodologica.** Ogni punteggio deve derivare da una misura.
   Se è una stima euristica, il referto lo dice. Se un'area non è stata
   guardata, il referto lo dice. Vale anche per le docstring: diverse
   dichiarano quanto della propria area *non* coprono ancora.
6. **Interfaccia in italiano**, identificatori in inglese.
7. **Stile di riferimento: `mars_citations.py`.** Type hints,
   `from __future__ import annotations`, I/O separato dalla logica, il
   dato prima della presentazione, docstring che spiegano il *perché*.
