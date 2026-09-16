# MARS Beacon — HANDOFF

> Questo file esiste perché il lavoro è **interrotto a metà**: I30 è
> aperta e aspetta una decisione. Quando quella decisione è presa e
> realizzata, questo file si cancella.
>
> Ultimo aggiornamento: **2026-09-16**.

## Dove siamo

- `main` allineato con `origin/main`, working tree pulito.
- `__version__` **2.40.0**; `pytest` **1467 passati**, `flake8` a zero.
- [TO-DO.md](TO-DO.md): **nessuna casella aperta**. Quattro idee non
  decise — I7, I11, I14, I20 — più **I30**, l'ultima arrivata.
- Lo stato verificato della macchina (versioni, strumenti presenti e
  assenti) sta in testa ad [AS-IS.md](AS-IS.md): **si legge da lì**, non
  si ricostruisce.

## Il prossimo passo

**I30 — potenziare la remediation.** Il committente ha detto che «è poco
più di un consiglio»; la voce nel TO-DO porta quattro letture misurate e
**nessuna è ancora scelta**. La sola cosa da fare adesso è farsi dire
quale:

- **A — il pacchetto** (quanto vale chiudere le prime N insieme). È
  quella che consiglierei: aritmetica già in casa, nessuna prosa nuova.
- **B — il raggruppamento** per pagina o per modifica.
- **C — la verifica** di una voce chiusa.
- **D — i `example` mancanti** (16 su 27).

I numeri che hanno prodotto le quattro letture sono nella voce: non
rimisurarli, ma **rifarli prima di scrivere codice** se passa del tempo,
perché vengono dal referto sintetico e i golden si muovono.

## Stati temporanei di QUESTA macchina

Non sono nel repository e un clone nuovo non li ha:

- `.venv` a **Python 3.10.12**, ricostruito con `uv` il 2026-09-15.
  L'interprete sta in `~/.local/share/uv/python/` e `uv` in
  `~/.local/bin/` — **fuori** dalla revisione dello snap di VS Code,
  dove `XDG_DATA_HOME` punta e dove il prossimo aggiornamento
  dell'editor romperebbe la venv senza un errore comprensibile.
- `node_modules/` installato: axe-core 4.13.0 e Lighthouse 13.4.1.
  Senza, cinque test si saltano e l'area 7 ripiega sul markup.
- **Assenti**: `sentence-transformers`, `torch`, `scikit-learn`, `numpy`
  — il recuperatore vettoriale gira col proxy char-TFIDF dichiarato.
  Reinstallarli costa alcuni GB.
- **Nessun daemon ZAP in esecuzione**: l'area 8 non è stata misurata in
  questa sessione.
- I banchi di prova di questa sessione stavano nella cartella temporanea
  della sessione e **sono persi**: erano banchi, non test. Ciò che
  meritava di restare è diventato un test.

## Comandi che servono subito

    .venv/bin/pytest            # senza -q: setup.cfg ce l'ha già
    .venv/bin/flake8 .

    MARS_RIGENERA_GOLDEN=1 .venv/bin/pytest tests/test_golden.py
    git diff tests/golden/      # il passo che non si salta

    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python <banco-mutazioni>

Variabili d'ambiente del progetto: `MARS_SECRET_KEY` (firma i JWT),
`MARS_API_PASSWORD_HASH_FILE` (il **percorso** dell'hash, non il valore),
`MARS_RIGENERA_GOLDEN`. Il push usa una chiave SSH dedicata, già
configurata in `.git/config` di questa copia.

## Il metodo che ha funzionato, e conviene ripetere

Nella revisione dell'area 7 (dieci voci, 2026-09-15/16) **cinque volte su
dieci la prima tornata di mutazioni ha trovato un ramo che nessun test
esercitava**, e due volte la misura ha smentito ciò che avevo scritto
prima di eseguire. L'ordine che ha prodotto questo: misurare, scrivere il
test che fallisce, implementare, **mutare**, e solo allora documentare.
