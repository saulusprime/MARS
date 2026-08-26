# Contribuire a MARS Beacon

Grazie dell'interesse. Questo documento descrive come è organizzato il
lavoro; il contratto tecnico dei moduli sta in [CLAUDE.md](CLAUDE.md).

## Prima di aprire una modifica

Il lavoro aperto è in [TO-DO.md](TO-DO.md), diviso in tre capitoli:

- **Completamento** — ciò che il README promette e il codice non fa ancora;
- **Correzioni** — difetti (attualmente vuoto: R1-R14 sono risolte);
- **Idee** — proposte non promesse dal README, da valutare prima di farle.

Ciò che è stato chiuso sta in [AS-IS.md](AS-IS.md), con difetto,
soluzione e verifiche. **Leggerlo prima di indagare su qualcosa**: molte
domande hanno già una risposta misurata, comprese alcune ipotesi
plausibili che si sono rivelate false.

Se la modifica non corrisponde a una voce esistente, aprirne una nel
TO-DO come parte della proposta.

## Ambiente

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # CLI e API
pip install -r requirements-dev.txt    # pytest, flake8
pip install -r requirements-optional.txt   # solo se servono ST/ZAP/Anthropic
```

`requirements-optional.txt` trascina torch: alcuni GB. Non serve per
lavorare sul codice — `--embeddings none` usa il proxy char-TFIDF.

## Regole di lavoro

**`pytest` deve restare verde.** La suite gira in meno di dieci secondi e
non tocca la rete: una fixture `autouse` sostituisce ogni richiesta con
un'eccezione che eredita sia da `AssertionError` sia da
`requests.RequestException`. Un modulo che gestisce correttamente gli errori
di rete la cattura e ripiega — e il percorso di ripiego viene cosi' esercitato
davvero; un modulo che non la gestisce la lascia passare e il test fallisce
rumorosamente.

**Un test verde non dimostra nulla finche' non lo si vede fallire.** Prima di
considerare coperto un difetto, reintrodurlo e verificare che la suite se ne
accorga. Scrivendo questi test, tre su sei erano vacui e sembravano corretti:
uno misurava la seconda difesa invece della prima, uno guardava un campo che
il modulo non legge piu' da R10, e uno verificava separatamente due meccanismi
senza mai provarne l'innesto.

**Il JavaScript del referto si prova a mano.** `mars_report.REFERTO_JS` —
il grafo dei link, l'unico script del referto — la suite lo verifica come
testo (nessuna origine esterna, nessun dato del sito dentro il codice) ma
non lo esegue: servirebbe `node`, e una suite che gira su una macchina e
non su un clone appena fatto è la trappola già pagata con
`node_modules/axe-core`. Chi tocca quel codice lancia

    python3 tools/banco_grafo.py

che fa girare lo script su un DOM finto e controlla nove comportamenti.
Esce 0 se sono tutti verdi, 2 se `node` non c'è. La voce **R48** del
TO-DO tiene aperta la scelta di come portarlo dentro `pytest`.

**La concorrenza dell'API si prova a mano, per la stessa ragione.**

    python3 tools/banco_concorrenza_api.py

fa girare l'applicazione vera con uvicorn e misura quanto attende una
richiesta banale mentre un audit lavora. Apre una porta, quindi esce
dall'ambiente che la suite si è data; dentro `pytest` il vincolo è
un'asserzione statica — gli handler bloccanti non devono essere corutine
— e questo banco è ciò che dimostra **perché** conti. Misurato chiudendo
**R29**: 1,71 s con `async def`, 0,01 s con `def`.

**`flake8 .` deve restare a zero avvisi.** La configurazione è in
`setup.cfg`, non servono flag. `flake8 --select=F` è il minimo prima di
ogni commit: è il controllo che ha rivelato il difetto più grave del
progetto, una funzione definita due volte che rendeva impossibile ogni
login.

**Riprodurre prima, dimostrare dopo.** Una correzione senza una prova
che il difetto esisteva, e una che ora non esiste più, non è
verificabile da nessun altro. Se una misura smentisce l'ipotesi di
partenza, va scritta lo stesso: in AS-IS.md ce ne sono diverse.

**La riformattazione va in un commit separato** da ciò che cambia il
comportamento. Mescolarle rende la revisione impossibile.

**Un commit per voce del TO-DO.** Il messaggio spiega il *perché*, non
l'elenco dei file toccati: quello lo dice già il diff. Prima riga breve,
poi una riga vuota, poi il ragionamento.

**Quando una voce è chiusa** si sposta dal TO-DO ad AS-IS, con difetto,
soluzione e verifiche. Non si cancella: il valore sta nel non dover
rifare la stessa indagine.

## Aggiungere un'area di audit

1. Creare `mars_<area>.py` con `def audit(context: dict) -> dict`.
2. Aggiungere la riga in `MODULES_REGISTRY` (`mars_core.py`).
3. Esporre l'endpoint in `mars_api.py`, se ha senso via HTTP.

Il modulo riceve pagine e chunk **già estratti**: non riparsare l'HTML.
Se lo strumento esterno di cui ha bisogno manca, restituire
`score: None` con `status: "unavailable"` — mai `score: 0`, che è un
giudizio e non un'assenza di misura.

## Cosa non cambiare senza discuterne

- La sostituzione degli algoritmi scritti a mano (BM25, RRF, chunker,
  proxy char-TFIDF) con librerie esterne: sono il valore del progetto.
- L'obbligatorietà di una dipendenza oggi opzionale.
- Il passaggio del `context` da dict a classi: attraversa il confine dei
  plugin.

Le ragioni per esteso sono nei principi in [CLAUDE.md](CLAUDE.md).

## Segnalazioni di sicurezza

Non aprire una issue pubblica per una vulnerabilità sfruttabile.
Scrivere in privato al responsabile del repository e attendere una
risposta prima di divulgare.
