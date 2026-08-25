# UPGRADE — Adeguamento della reportistica di MARS/ al livello di MARS-Beacon

> Documento redatto il 2026-08-21 confrontando sul codice le due versioni:
> **MARS/** (monolitica a plugin, `mars_core.__version__ = 2.0.0`) e
> **marsbeacon/** (package, `base.__version__ = 1.63.0`, renderer in
> `marsbeacon/render.py`). MARS/ è la versione definitiva ed è più avanti
> su motore, API e architettura a plugin; la reportistica di marsbeacon/
> è però più completa (remediation, formati, i18n, delta, golden).
> Questo file elenca **tutte** le modifiche per portare il referto di
> MARS/ allo stesso livello, in ordine di lavorazione, con i riferimenti
> `file:riga` verificati su entrambe le codebase. In coda c'è la
> **scheda definitiva** del referto di MARS/ a lavori conclusi.
>
> Metodo: 15 divari individuati incrociando quattro mappe di lettura
> integrale del codice, ciascuno poi **verificato in modo avversariale**
> sul codice reale (evidenze su entrambi i lati, ricerca attiva di
> implementazioni equivalenti sfuggite). Tutti e 15 sono risultati reali.
> Le "Avvertenze di adattamento" dentro le fasi vengono da quella
> verifica: sono i punti in cui copiare da marsbeacon/ alla lettera
> **non** funzionerebbe.

---

## Stato del programma (aggiornato il 2026-08-25)

**Nove fasi su dodici sono eseguite.** `__version__` è a **2.8.0**, il lavoro
sta sul ramo `upgrade`, e ogni fase chiusa ha la propria voce in
[AS-IS.md](AS-IS.md) con misure, decisioni editoriali e mutazioni. Restano
**U10** (giudizio LLM multi-modello), **U11** (deliverable rifinito) e **U12**
(ancore esterne, opzionale); le voci aperte stanno in [TO-DO.md](TO-DO.md).

**Questo documento resta il PIANO, e non diventa un registro**: la differenza
conta, perché il piano è ciò rispetto a cui si misura una divergenza. Il testo
delle nove fasi chiuse **non è stato potato** proprio per questo — trentacinque
punti fra codice, test e AS-IS citano ciò che il piano *prevedeva* per dire che
si è fatto diversamente, e perché. Tre esempi, che sono anche il modo in cui
questo documento va letto oggi:

- l'ancora di un rilievo doveva essere uno slug ricavato dal **titolo**, coi
  numeri normalizzati perché «2/3 pagine» e «1/3 pagine» non producessero due
  ancore diverse. Non è servito: dalla Fase 1 ogni rilievo ha una `key` stabile
  per costruzione, che è esattamente il problema che quello slug risolveva a
  valle. Il riferimento non aveva chiavi, noi sì
  ([mars_report.py:1859](mars_report.py#L1859));
- la Fase 8 prevedeva di **colorare ogni pagina della treemap** con la gravità
  peggiore dei rilievi che la citano. Applicata alla lettera, quella regola non
  trova mai una corrispondenza e dipinge tutto di «nessun problema» — un via
  libera che nessuno ha misurato. La treemap è uscita neutra e lo dichiara; il
  divario è **R47** ([mars_report.py:585](mars_report.py#L585));
- la Fase 4 prevedeva una chiave `top_actions` accanto ai profili di
  citabilità. Non è stata aggiunta: sarebbe stata una seconda copia del piano,
  che diverge in silenzio dalla prima
  ([AS-IS.md:3856](AS-IS.md#L3856)).

Da qui la regola per chi riprende in mano il documento: **le fasi 1-9 si
leggono insieme alla loro voce in AS-IS**, che dice che cosa è stato fatto
davvero. Dove le due divergono, ha ragione AS-IS.

---

## 1. Le due versioni in breve

| Aspetto | MARS/ (definitiva) | marsbeacon/ (riferimento report) |
|---|---|---|
| Architettura | plugin `audit(context) -> dict`, registro in `mars_core.py:102-114` | package con moduli interni |
| Referto: filosofia | **dato canonico** `build_report()` + viste (`mars_report.py:30`) | renderer con argomenti espliciti |
| Formati | text, json, html (`mars_report.py:839`) | text, json, html, **md, csv** |
| Rilievi | stringhe piatte in `issues` | dataclass `Finding` (`base.py:1258-1291`) |
| Remediation | **assente** | piano ordinato con sforzo/quick win/guadagni |
| i18n | italiano cablato | it/en/fr/de/es con cataloghi e fallback |
| Delta fra run | assente (esiste solo in `mars_citations.py`) | `compute_delta` + storico JSONL |
| Punteggio complessivo | assente | `overall_score` pesato + hero visuale |
| Golden test | assenti | 5 golden + rigenerazione controllata |
| Stile HTML | quadranti Lighthouse, **nessuno script** | card + JS inline progressive-enhancement |

Il punto di forza da NON perdere di MARS/: il referto è un **dato**
(`build_report` produce il dict canonico, le viste lo leggono). Tutte le
novità entrano **prima nel dato, poi nelle viste** — mai il contrario.

---

## 2. Cosa NON cambia (invarianti di MARS/ da preservare)

1. **Contratto plugin a dict** (`MARS/CLAUDE.md`, principio 3): i moduli
   restituiscono dict. La nuova dataclass `Finding` è struttura interna;
   attraversa il confine dei plugin **serializzata** con `as_dict()`.
2. **Referto autoconsistente**: un solo file, nessuna CDN, favicon e
   asset come data URI. Presidiato da `MARS/tests/test_report.py:132-141`.
3. **Onestà metodologica**: `score: None` ≠ `score: 0`; stati
   `surface`/`unavailable`/`disabled`/`error` e qualificatori
   (`_qualificatori`, `mars_report.py:196-230`) restano; ogni stima
   euristica resta dichiarata (disclaimer citabilità vicino ai numeri).
4. **Scala colori Lighthouse 90/50** (`mars_report.py:383-384`): scelta
   deliberata e documentata di MARS/ ("il colore è una convenzione, il
   numero no"). NON si importa la scala 70/40 di marsbeacon
   (`render.py:489-499`): le nuove sezioni (hero, verdetti) adottano
   90/50. Il simbolo accompagna sempre il colore, mai solo colore.
5. **Interfaccia in italiano, identificatori in inglese** (principio 6):
   l'italiano resta la lingua canonica; l'i18n aggiunge lingue, non
   sostituisce.
6. **Fascia quadranti, qualificatori, sezione "Cosa non è stato
   guardato"**: sono conquiste di MARS/ che marsbeacon non ha; restano.
7. **La suite non tocca la rete** (fixture `niente_rete` autouse) e
   `flake8 .` resta a zero.

---

## 3. Decisioni da ratificare prima di iniziare — ✅ tutte ratificate

> **Aggiornamento 2026-08-25.** Tutte e quattro sono ratificate e
> **applicate**: D2 dalla Fase 1, D3 dalla Fase 5, D1 dalla Fase 8.4, D4 dalla
> Fase 9.1. L'esito di ciascuna, con la fase che l'ha applicata, sta in
> [AS-IS.md](AS-IS.md).
>
> Il testo qui sotto **resta**, e non è un doppione: è la *proposta* com'era
> scritta prima di decidere, con la risposta data allora. AS-IS registra
> l'esito, non la domanda — e su D4 le due cose divergono, il che è
> esattamente ciò che si vuole poter rileggere: la proposta era cinque lingue
> «riusando i cataloghi già scritti», e misurando prima di eseguire si è visto
> che dei cataloghi del riferimento coincidono **4 chiavi su 49**.

Quattro punti in cui l'adeguamento tocca un invariante o richiede una
scelta di progetto. Vanno decisi (e registrati in AS-IS/TO-DO) prima
della fase che li incontra, per non deciderli "di fatto" scrivendo codice.

- **D1 — JavaScript inline nel referto.** `render_html` di MARS/ dichiara
  "NESSUNO SCRIPT" (`mars_report.py:787-793`) e il vincolo è testato
  (`tests/test_report.py:132-141`). marsbeacon ha ribaltato lo stesso
  vincolo il 2026-08-05 con una decisione documentata: JS **inline,
  vanilla, progressive enhancement puro** — l'SVG statico resta la base,
  niente payload propri, niente origini esterne, `prefers-reduced-motion`
  spegne le animazioni (`render.py:1379-1384`). Proposta: adottare la
  stessa decisione **solo alla Fase 8** (grafo dei link interattivo);
  fino ad allora ogni sezione nuova è statica. Se D1 = no, la Fase 8
  consegna comunque treemap e profondità (statiche) e rinuncia al solo
  grafo interattivo.
  Risposta: nessun problema, utilizziamo script vanilla javascript

- **D2 — Scala di severità canonica.** Quattro livelli come marsbeacon
  (`base.py:267-276`): `critical`, `warning`, `info`, `ok`
  (identificatori in inglese, etichette in italiano). La granularità in
  più delle scale esistenti si conserva nel **peso**, non in livelli
  extra (tabella in Fase 1).
  Risposta: va bene

- **D3 — Pesi del punteggio complessivo.** Proposta in Fase 5: media
  pesata delle aree misurate (Tecnica, SEO, Dati strutturati,
  Accessibilità, Sicurezza a peso 1.0; Recuperabilità-RRF e "In forma di
  risposta" a peso 1.5 come fa marsbeacon con Lex/Sem/RRF,
  `audits.py:3273-3284`), **esclusi** Citabilità (già sintesi derivata:
  conterebbe due volte) e Giudizio LLM (opzionale e a pagamento).
  Rinormalizzazione automatica sulle aree presenti.
  Risposta: va bene

- **D4 — Lingue.** marsbeacon serve it/en/fr/de/es (`i18n.py:32`).
  Proposta: stesse cinque lingue, riusando i cataloghi già scritti dove i
  controlli coincidono (Fase 9). Ridurre a it/en è legittimo ma va
  dichiarato come livello inferiore rispetto al riferimento.
  Risposta: i18n lo inseriamo in TO-DO.md e lo facciamo dopo

---

## 4. Ordine dei lavori e dipendenze

> **Aggiornamento 2026-08-25.** L'ordine è stato seguito ed è **speso per le
> prime nove**: G01 per primo, i golden subito dopo, e da lì ogni fase con la
> rete sotto. Resta valido per le tre che mancano, che non hanno dipendenze
> fra loro — U11 e U12 si possono fare in qualunque ordine, U10 porta con sé
> **U10.1** (i punti deboli del giudizio come rilievi strutturati), che senza
> il multi-modello non ha la misura che le serve.

Il divario G01 (modello dati dei rilievi) è il **prerequisito** di quasi
tutto: G02, G03, G05, G06, G07 (tile e donut), G11. Va chiuso per primo.
I golden (G10) arrivano subito dopo, così ogni fase successiva ha una
rete: ogni cambiamento di resa passa da una rigenerazione **intenzionale**
con revisione del diff.

| Fase | Divari | Contenuto | Priorità |
|---|---|---|---|
| 1 | G01 | Dataclass `Finding`, scala severità unificata | alta |
| 2 | G10 | Golden test dei formati | media |
| 3 | G03 | Testi `fix` ed `example` per ogni controllo | alta |
| 4 | G02 | Piano di remediation ordinato | alta |
| 5 | G07, G11 | Punteggio complessivo, hero, ancore stabili | media |
| 6 | G04 | Formati Markdown e CSV | media |
| 7 | G09, G06 | schema_version/RRF/soglie; delta e storico | media |
| 8 | G12 | Profondità, treemap, grafo (D1), matematica, pages[] | media |
| 9 | G05 | i18n a cataloghi con `--lang` | media |
| 10 | G08 | Giudizio LLM multi-modello | media |
| 11 | G14, G15 | CSS di stampa, a11y tabelle, brand nel footer | bassa |
| 12 | G13 | Brave Search e confronto competitivo (opzionale) | bassa |

Convenzioni trasversali (valgono per OGNI fase, dal flusso di lavoro del
progetto): un commit per voce di TO-DO; la voce chiusa **si sposta** da
TO-DO.md ad AS-IS.md con difetto/soluzione/verifiche; bump di
`__version__` in `mars_core.py` (minor per fase: 2.1.0, 2.2.0, …) e badge
nel README; `pytest` verde senza rete e `flake8 .` a zero prima del
commit; dalla Fase 2 in poi, golden rigenerati con `MARS_RIGENERA_GOLDEN=1`
e diff rivisto a ogni modifica di resa intenzionale.

---

## 5. Le fasi in dettaglio

### Fase 1 — Il modello dati dei rilievi (G01) — ✅ CHIUSA (2026-08-24)

> **Fatta.** `__version__` a 2.1.0, nove sotto-voci. Ha lasciato aperte **R39**, **R40**, **R42** e **U13**: adeguare la forma ha fatto leggere sei moduli riga per riga, e ogni difetto trovato lì è rimasto aperto invece di essere corretto dentro un commit che non doveva spostare punteggi né testi. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

**Il problema.** In MARS/ i rilievi sono stringhe piatte con la gravità
codificata in prefissi testuali **diversi per modulo**: `[critico]`…
`[lieve]` in mars_tech (`mars_tech.py:54-58`, `213-215`), `[axe:serious]`
in mars_wcag (`mars_wcag.py:185`), `[ZAP:High]` in mars_wapt
(`mars_wapt.py:80`), `[Lighthouse]` in mars_seo (`mars_seo.py:119-123`,
che peraltro è un'etichetta di **strumento**, non una gravità). Tre scale
non mappate fra loro, nessun peso per singolo rilievo, nessuna chiave
stabile. In marsbeacon ogni esito è una dataclass `Finding`
(`marsbeacon/base.py:1258-1291`) su cui poggiano ordinamenti, piano di
remediation, i18n, ancore e delta.

**Passi.**

1. In `mars_core.py` (le strutture condivise stanno lì, principio 4 di
   CLAUDE.md) aggiungere:
   - le costanti `SEV_CRITICAL = "critical"`, `SEV_WARNING = "warning"`,
     `SEV_INFO = "info"`, `SEV_OK = "ok"`;
   - la dataclass `Finding` con i campi di marsbeacon adattati:
     `area` (nome modulo, es. `"mars_tech"`), `severity` (canonica),
     `title`, `detail=""`, `fix=""`, `example=""`, `url=""`,
     `weight=1.0`, `key=""` (id stabile del controllo, es.
     `"tech.robots.ai_blocked"`), `params={}` (valori dinamici già
     interpolati, per l'i18n della Fase 9), `source_severity=""`
     (la gravità originale dello strumento, per onestà verso chi
     conosce le scale axe/ZAP), e `as_dict()`;
   - la funzione `normalizza_severita(scala, valore) -> (severity,
     weight)` con la mappa di conversione:

   | Origine | Valore | `severity` | `weight` |
   |---|---|---|---|
   | mars_tech | critico | critical | 2.0 |
   | mars_tech | grave | warning | 2.0 |
   | mars_tech | medio | warning | 1.0 |
   | mars_tech | lieve | info | 1.0 |
   | axe | critical | critical | 2.0 |
   | axe | serious | warning | 2.0 |
   | axe | moderate | warning | 1.0 |
   | axe | minor | info | 1.0 |
   | ZAP | High | critical | 2.0 |
   | ZAP | Medium | warning | 1.0 |
   | ZAP | Low / Informational | info | 1.0 |

   La granularità persa dai 4 livelli si conserva nel peso: è lo stesso
   criterio d'ordinamento di marsbeacon (gravità, poi peso decrescente).

2. Adeguare i moduli **uno per commit** (mars_tech, mars_wcag, mars_wapt,
   mars_schema, mars_seo, mars_citability) a costruire internamente
   `Finding` e a restituire nel dict, accanto alle attuali `issues`
   (che restano: vista legacy e contratto di `tests/test_modules.py:38-44`),
   la nuova chiave **`findings`: lista di `as_dict()`**. Il contratto
   plugin resta dict: la dataclass NON attraversa il confine (principio 3
   di CLAUDE.md — vincolo confermato in verifica).

3. `build_report()` (`mars_report.py:30-107`): ogni voce di `areas`
   guadagna `"findings": list(res.get("findings") or [])`. Le `issues`
   restano com'erano: nessun consumatore esistente si rompe
   (`normalizza_risultato`, `mars_core.py:179-196`, già garantisce il
   default sui plugin che non le producono).

4. Le viste, per ora, non cambiano: la Fase 1 chiude quando il dato
   canonico porta i findings strutturati.

**Test.** In `tests/test_modules.py`: per ogni modulo adeguato, un test
che verifica la presenza di `findings` con severità canonica e
`source_severity` originale; un test della mappa di conversione (tutti i
valori delle tre scale, incluso un valore ignoto → `info` con peso 1.0,
mai un'eccezione). Reintrodurre il difetto (togliere la mappatura) per
vedere il test fallire, come da metodo del progetto.

---

### Fase 2 — Golden test dei formati (G10) — ✅ CHIUSA (2026-08-24)

> **Fatta.** Sei file in `tests/golden/`. Congelano la **pipeline**, non i soli renderer: anche un punteggio che cambia li fa fallire. Ha lasciato aperta **R43**. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

**Il problema.** `MARS/tests/test_report.py:54-59` e `132-141` fanno solo
asserzioni puntuali: una modifica di resa non intenzionale che non tocca
i punti asseriti passa inosservata. marsbeacon congela la resa con golden
byte-a-byte (`tests/test_golden.py`) e rigenerazione controllata. Con
dieci fasi di lavoro sul renderer davanti, questa rete va montata
**adesso**.

**Passi.**

1. Creare `MARS/tests/test_golden.py` sul modello di
   `tests/test_golden.py` di MARS-Beacon (variabile
   `MARS_RIGENERA_GOLDEN`, riga 18; confronto con diff unified,
   374-394; test di determinismo — due render identici — 397-402):
   - fixture sintetica **deterministica e senza rete** che costruisce
     `results` + `context` riusando `pagina()`/`contesto()` di
     `MARS/tests/conftest.py:47-109`, coprendo le 9 aree del registro
     (`mars_core.py:102-114`), i tre stati (`score`, `unavailable`,
     `surface`), un'area in `error`, RRF con query misurabile e non
     (`matched: False`), citabilità e giudizio LLM;
   - `generated_at` e `version` normalizzati prima del confronto (sono
     gli unici campi volatili);
   - golden in `MARS/tests/golden/referto.{txt,json,html}`; iterare sui
     formati registrati in `RENDERERS` (`mars_report.py:839`), così i
     formati delle fasi successive (md, csv) entrano nel presidio da
     soli.
2. Aggiungere al `.gitignore` di MARS/ (se ha i pattern `referto*`)
   l'eccezione `!tests/golden/referto*`, come nel repo MARS-Beacon.
3. Documentare nel README la rigenerazione:
   `MARS_RIGENERA_GOLDEN=1 pytest` + revisione del diff in git.

**Accettazione.** Suite verde; un cambiamento volontario di un carattere
nel CSS fa fallire il golden HTML con diff leggibile.

---

### Fase 3 — I testi di correzione: `fix` ed `example` (G03) — ✅ CHIUSA (2026-08-24)

> **Fatta.** `__version__` a 2.2.0, il catalogo `mars_fixes.py`. Ha lasciato aperta **R44**, chiusa poi dalla Fase 9.3. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

**Il problema.** I moduli di MARS/ descrivono il difetto ("CSP mancante",
"[grave] 2/100 pagine con noindex") ma non dicono mai **come** risolvere
(verificato: zero campi fix/example in `mars_tech.py:194-218`,
`mars_wcag.py:280-303`, `mars_wapt.py:244-273`; unica prosa orientata al
miglioramento è quella libera del giudice LLM,
`mars_llm_judge.py:224-234`). In marsbeacon ogni rilievo nasce con un
`fix` prescrittivo e spesso un `example` pronto all'uso (~120+ istanze
`Finding(...)` censite, catalogo i18n ancora più ampio).

**Passi.**

1. Per ogni controllo dei moduli, valorizzare `fix` ed `example` nei
   `Finding` della Fase 1. Tre fonti, in quest'ordine:
   - **riuso da marsbeacon** dove il controllo coincide — robots/crawler
     IA (`marsbeacon/crawler.py:296-309`, con esempio robots.txt),
     HTTPS (`marsbeacon/audits.py:1332-1342`, con snippet nginx/Apache),
     noindex, sitemap, canonical, JSON-LD assente/incompleto
     (`audits.py:2740-2748` + `EX_LOCALBUSINESS`,
     `marsbeacon/base.py:1013-1024`), header di sicurezza;
   - **derivazione dallo strumento** per i controlli propri di MARS/:
     axe fornisce `help`/`helpUrl` nel payload (mars_wcag usa già `help`
     a `mars_wcag.py:185-187` — aggiungere `helpUrl` alla raccolta);
     ZAP fornisce `solution` nell'alert, che oggi viene **scartata**
     (`mars_wapt.py:55-68` tiene solo risk/name/urls — raccoglierla);
     Lighthouse fornisce `description` nel LHR, da ripulire dai link
     Markdown come fa `marsbeacon/audits.py:476-479` (`_strip_md_links`);
   - **redazione ex novo** per il resto, nello stile prescrittivo di
     marsbeacon ("Pubblica…", "Attiva…", "Aggiungi…").
2. Resa nelle viste (`mars_report.py`):
   - `render_text`: riga `-> Fix: …` sotto il rilievo e blocco esempio
     indentato (modello: `marsbeacon/render.py:360-365` e `436-442`);
   - `render_html`, `_scheda_area` (`mars_report.py:651-702`): span
     `.fix` (con prefisso "Fix:" via CSS come `render.py:1875`) e
     `pre.ex` per l'esempio; i golden si rigenerano qui, col diff
     rivisto.
3. Le stringhe `issues` NON cambiano: sono la vista compatta legacy.

**Test.** Per ogni modulo un test "il controllo X fallito produce un
Finding con fix non vuoto"; test che l'esempio, quando c'è, finisce nel
`pre.ex` dell'HTML con escape corretto (il testo può venire dal sito
analizzato: passare tutto da `_e()`, `mars_report.py:373-375`).

---

### Fase 4 — Il piano di remediation (G02) — ✅ CHIUSA (2026-08-25)

> **Fatta.** `__version__` a 2.3.0. Ogni intervento dichiara il **recupero**, non la penalità. La `top_actions` prevista qui **non** è stata aggiunta: sarebbe stata una seconda copia del piano. Ha lasciato aperta **R46**. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

> **Vincolo dei rilievi derivati (R41).** Ogni consumatore che **aggrega**
> rilievi — piano di interventi, conteggi per gravità, confronto fra due
> esecuzioni — deve escludere quelli con `params.get("derived")`, cioè le
> sintesi di `mars_citability`: ridicono difetti che altre aree hanno già
> misurato, e contarli due volte gonfierebbe l'aggregato. Chi invece li mostra
> uno per uno (elenco d'area, JSON, CSV) li tiene. Non basta filtrare per
> gravità: oggi sono tutti `info`, ma è una protezione incidentale.


**Il problema.** MARS/ non ha nulla fra "elenco dei difetti" e "cosa
faccio lunedì mattina" (verificato: zero occorrenze di
remediation/raccomandazioni in `MARS/*.py`; i rilievi HTML sono un `ul`
di stringhe, `mars_report.py:694-696`). marsbeacon costruisce un piano
d'azione ordinato per resa (`build_remediation`,
`marsbeacon/audits.py:165-223`) e lo rende in **tutti** i formati.

**Passi.**

1. Nuovo modulo `MARS/mars_remediation.py` (o sezione di
   `mars_report.py`, ma il modulo separato rispetta "I/O separato dalla
   logica" e tiene mars_report sotto controllo di dimensione) con:
   - `estimate_effort(finding) -> "minuti"|"ore"|"giorni"`: le regex di
     `marsbeacon/base.py:1306-1321` sono riusabili quasi tal quali —
     rivederle contro i titoli reali dei controlli MARS (aggiungere i
     termini di ZAP e axe che marsbeacon non ha);
   - `build_remediation(findings, referto) -> List[dict]`: filtro sui
     `critical`+`warning`, ordinamento `(gravità, -index_gain, -peso)`,
     voci `{priority, severity, area, title, fix, example, url, effort,
     quick_win, key, params, …guadagni}`; quick win = critico da minuti
     (`audits.py:214-215`);
   - `_citability_gains` **adattato**. Avvertenza di adattamento
     (verificata sul codice): in marsbeacon il punteggio d'area è una
     somma di pesi, in MARS/ deriva da **penalità** sottratte a 100
     (`mars_tech.py:207-214`, `mars_wcag.py:175-188`,
     `mars_wapt.py:70-86`). Il guadagno di un rilievo va quindi
     calcolato come **recupero della sua penalità**: quanto risalirebbe
     lo score d'area se il rilievo fosse risolto. Da lì, i guadagni per
     profilo usano la matrice pesi già esistente in
     `MARS/mars_citability.py:63-105` (`PESI_ASSISTENTE` + `MERCATI`):
     `gain_profilo = peso_assistente[area] × recupero × fattore_mercato`,
     `index_gain` con i pesi di mercato dell'indice composito, flag
     `cross` quando i profili toccati sono più d'uno. Serve che ogni
     modulo, nel costruire il Finding, registri la **penalità** applicata
     (campo `weight` della Fase 1 o `params["penalty"]`): senza, il
     recupero non è calcolabile.
2. Dato canonico: `build_report` guadagna la chiave `"remediation"`
   (lista) — e la sezione citabilità la chiave derivata
   `"top_actions"` (le prime 3 voci annotate col miglior profilo, come
   `citability_top_actions`, `marsbeacon/audits.py:3390-3404`).
3. Rese:
   - `render_text`: sezione `PIANO DI REMEDIATION · N interventi per
     {criterio} · M quick win` con voci numerate
     `[CRITICO · area · sforzo: ore] titolo`, marcatore `** QUICK WIN`,
     riga Fix, esempio indentato, nota sui trasversali (modello:
     `marsbeacon/render.py:401-442`);
   - `render_html`: sezione "Piano di remediation" con badge sforzo /
     QUICK WIN / trasversale (modello: `render.py:1215-1256`) **e**
     widget "Top rilievi" in testa, subito dopo l'hero della Fase 5
     (top-5 del piano, pattern Top Issues; `render.py:709-733`);
   - dentro la sezione citabilità: "Azioni con maggior guadagno di
     profilo" (`render.py:829-853`).
4. Golden rigenerati con diff rivisto.

**Test.** In `tests/test_report.py`: ordinamento (un critico pesante
sopra un warning; a parità di gravità vince l'index_gain), quick win
marcato solo su critico+minuti, presenza del piano nelle tre viste,
coerenza numerica fra `index_gain` dichiarato e matrice di
mars_citability su un caso costruito a mano.

---

### Fase 5 — Punteggio complessivo, hero e ancore (G07, G11) — ✅ CHIUSA (2026-08-25)

> **Fatta.** `__version__` a 2.4.0. Le ancore vengono dalla `key` e non dallo slug del titolo previsto qui — il riferimento non aveva chiavi, MARS sì. Chiude **R41**. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

> **Vincolo dei rilievi derivati (R41).** Ogni consumatore che **aggrega**
> rilievi — piano di interventi, conteggi per gravità, confronto fra due
> esecuzioni — deve escludere quelli con `params.get("derived")`, cioè le
> sintesi di `mars_citability`: ridicono difetti che altre aree hanno già
> misurato, e contarli due volte gonfierebbe l'aggregato. Chi invece li mostra
> uno per uno (elenco d'area, JSON, CSV) li tiene. Non basta filtrare per
> gravità: oggi sono tutti `info`, ma è una protezione incidentale.


**Passi (G07 — complessivo e hero).**

1. `overall_score(referto)` in `mars_report.py` secondo la decisione D3:
   media pesata delle aree **misurate** (score non-None), pesi 1.0 per
   Tecnica/SEO/Dati strutturati/Accessibilità/Sicurezza e 1.5 per i due
   segnali derivati già calcolati dalla fascia quadranti (consenso RRF
   aggregato e quota answer-shaped, `mars_report.py:584-596`);
   Citabilità e Giudizio LLM esclusi (D3). Rinormalizzazione automatica
   come `marsbeacon/audits.py:3273-3284`. Chiave `"overall"` nel dato
   canonico.
2. Hero in `render_html`, sopra la fascia quadranti (modello:
   `_render_hero`, `marsbeacon/render.py:562-629`, adattato allo stile
   quadranti di MARS/):
   - quadrante **grande** del complessivo con verdetto testuale e riga
     delle soglie dichiarate (etichette: Buono ≥90, Da migliorare 50-89,
     Critico <50 — scala di MARS/, invariante 4);
   - tre tile coi conteggi per gravità (Critici/Avvertenze/Info) dai
     findings della Fase 1;
   - donut dello stato pagine. **Avvertenza di adattamento**
     (verificata): il dict pagina di MARS/ non conserva lo status HTTP
     (solo le 200 entrano in `pages`, il resto va in `skipped`,
     `mars_core.py:643-646`) e le issues non sono oggi agganciate agli
     URL. Finché i Finding non portano `url` valorizzati dai moduli, il
     donut rende **scansionate vs scartate** (`pages_crawled` vs
     `len(skipped)`); quando i moduli valorizzano `url`, si passa al
     taglio senza rilievi / con rilievi / scartate come
     `page_status_counts` (`render.py:520-535`).
3. `render_text`: riga `COMPLESSIVO : NN/100` in testa ai punteggi.

**Passi (G11 — ancore stabili).**

4. Portare `_finding_anchor` (`marsbeacon/render.py:502-517`): slug
   `r-{area}-{titolo}` con i numeri normalizzati a `n` (stabile fra
   esecuzioni quando cambiano solo i conteggi), duplicati con suffisso.
   Applicarla ai rilievi delle schede area (id sul `li`, permalink
   `<a class='anchor' href='#…' aria-label='…'>#</a>`) e ai controlli di
   `_elenco_controlli`; regola `:target` nel CSS (modello
   `render.py:1916-1917`). Il widget Top rilievi e il piano della Fase 4
   linkano le ancore tramite una mappa per chiave, come `link_to`
   (`render.py:664-683`).

**Test.** Rinormalizzazione del complessivo (area assente → pesi
ricalcolati); stabilità delle ancore al variare dei soli numeri nel
titolo; hero presente e conteggi coerenti coi findings.

---

### Fase 6 — Formati Markdown e CSV (G04) — ✅ CHIUSA (2026-08-25)

> **Fatta.** `__version__` a 2.5.0. Registrati in `RENDERERS`, quindi la CLI e i golden li acquisiscono da soli. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

**Passi.**

1. `render_markdown(referto)` in `mars_report.py` (modello:
   `marsbeacon/render.py:2024-2293`): testata, tabella punteggi per area
   + complessivo, profili di citabilità, giudizio LLM, **piano di
   remediation come task list GFM `- [ ]`** (incollato in una issue
   diventa una checklist spuntabile, `render.py:2232-2240`), rilievi per
   area con gravità come **marcatori testuali** (`**[CRITICO]**`,
   `[AVVISO]` — mai solo colore), simulazione RRF.
2. `render_csv(referto)` (modello: `render.py:2296-2335`): una riga per
   rilievo strutturato (i findings della Fase 1 — non serve più estrarre
   la gravità dai prefissi, che esistono solo in mars_tech), colonne
   `sito;area;gravita;peso;titolo;dettaglio;correzione;url;sforzo;quick_win`,
   delimitatore `;`, **BOM UTF-8** in testa (apertura diretta in
   Excel/Sheets con accenti e colonne giuste), sforzo/quick win
   valorizzati solo per i rilievi azionabili.
3. Registrarli in `RENDERERS` (`mars_report.py:839`): la CLI acquisisce
   i nuovi formati da sola (`choices=tuple(RENDERERS)`,
   `mars_audit.py:198-204`). Aggiornare epilog ed esempi
   (`mars_audit.py:104-138`) e il README.
4. Golden: aggiungere `referto.md` e `referto.csv` (la Fase 2 itera già
   su `RENDERERS`).

**Test.** BOM presente, delimitatore `;`, escaping delle celle md
(`_md_cell`: pipe e newline), task list presente e conteggio coerente
col piano.

---

### Fase 7 — Riproducibilità e storia (G09, G06) — ✅ CHIUSA (2026-08-25)

> **Fatta.** `__version__` a 2.6.0. Il confronto è per **chiave stabile** e non per titolo. Realizza anche l'idea **I1** del TO-DO, in una forma diversa da quella proposta lì. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

> **Vincolo dei rilievi derivati (R41).** Ogni consumatore che **aggrega**
> rilievi — piano di interventi, conteggi per gravità, confronto fra due
> esecuzioni — deve escludere quelli con `params.get("derived")`, cioè le
> sintesi di `mars_citability`: ridicono difetti che altre aree hanno già
> misurato, e contarli due volte gonfierebbe l'aggregato. Chi invece li mostra
> uno per uno (elenco d'area, JSON, CSV) li tiene. Non basta filtrare per
> gravità: oggi sono tutti `info`, ma è una protezione incidentale.


**Passi (G09 — metadati di schema).**

1. `JSON_SCHEMA_VERSION = 1` in `mars_core.py` (modello:
   `marsbeacon/base.py:47`) e chiave `"schema_version"` in
   `build_report`. Politica documentata nel README: si incrementa solo
   su cambi **incompatibili**; le aggiunte di chiavi sono additive.
2. Blocco `"rrf"` nel dato canonico: `{k, formula}` — il k=60 oggi vive
   solo come default di `reciprocal_rank_fusion`
   (`mars_core.py:1220-1229`): esporlo nel context e copiarlo nel
   referto, con la formula esplicita come `render.py:1969-1970`.
3. Chiave `"thresholds"` con `null` finché MARS/ non ha soglie
   configurabili (la docstring di marsbeacon spiega il perché: "due
   referti con soglie diverse non sono confrontabili alla pari e il JSON
   lo dichiara", `render.py:1964-1967`).
4. Aggiornare l'asserzione delle chiavi top-level in
   `tests/test_report.py:54-59`.

**Passi (G06 — delta e storico).**

5. Storico JSONL per sito: dopo `build_report`, `mars_audit.py` appende
   una riga compatta `{generated_at, url, version, scores per area,
   overall, findings critici+avvertenze (area, key, title)}` a un file
   configurabile (`--history PATH`, default accanto all'output;
   `--no-history` per disattivare). **Il modello interno c'è già**:
   `mars_citations.py` fa esattamente questo per il tracker di citazioni
   (`read_last_run` a `371-388`, `append_history` a `391-405`, delta del
   tasso a `446-449`) — stesso stile, stesso file-pattern.
6. `compute_delta(precedente, corrente)` (modello:
   `marsbeacon/audits.py:3419-3494`): variazioni di score per area e
   complessivo, rilievi **risolti** e **nuovi** confrontati per chiave
   stabile `(area, key)` — la Fase 1 la fornisce; per i rilievi senza
   key, confronto sul titolo coi numeri normalizzati, dichiarando nella
   nota che i conteggi nei titoli possono variare. Chiave `"delta"` nel
   dato canonico (null alla prima esecuzione).
7. Rese: sezione "Rispetto all'esecuzione precedente" in `render_text`
   (`render.py:172-197`) e `render_html` con h3 Risolti/Nuovi
   (`render.py:757-786`); nel md, elenco puntato.

**Test.** Due referti sintetici → delta con un risolto, un nuovo, una
variazione di score; prima esecuzione → `delta: null` senza sezione;
riga di storico ben formata e append-only.

---

### Fase 8 — Le analisi della superficie (G12) — ✅ CHIUSA (2026-08-25)

> **Fatta.** `__version__` a 2.7.0, e con U8.4 **D1 è applicata**. La colorazione della treemap prevista qui è rimasta **non fatta**, e non per dimenticanza: applicata alla lettera non trova mai una corrispondenza. Ha lasciato aperte **R47** e **R48**. Il dettaglio — misure, decisioni editoriali, mutazioni — sta in [AS-IS.md](AS-IS.md). Il piano qui sotto resta com'era scritto: è il termine di paragone delle divergenze.

**Passi.**

1. **`pages[]` nel JSON** (primo passo, basso costo, alto valore per le
   integrazioni): `build_report` espone il sottoinsieme serializzabile
   dei dati pagina già nel context (`mars_core.py:666-703`): url, title,
   n. headings, n. chunks, tipi JSON-LD, lang. **Avvertenza verificata**:
   lo status HTTP non è nel dict pagina (le non-200 finiscono in
   `skipped`) — o si registra nel crawler, o `pages[]` esce senza
   status: non inventarlo.
2. **Profondità di crawl**: registrare nel crawler BFS la distanza in
   click dalla home (il crawler è già FIFO, `mars_core.py`), poi portare
   `depth_distribution` (`marsbeacon/indexes.py:314`) e la sua tabella
   HTML a barre (`render.py:1010-1029`). Le pagine da sola sitemap hanno
   profondità ignota e bucket dedicato (in giallo: irraggiungibili per
   link).
3. **Treemap della superficie contenutistica**: portare `treemap_data`
   (`indexes.py:515`) adattandola ai dict pagina di MARS/ (niente
   dataclass `Page`); resa SVG statica con `role="img"`, `tabindex`,
   `<title>` per rettangolo e **tabella di fallback in `<details>`**
   (`render.py:1031-1081`). Colore = gravità peggiore dei findings
   agganciati all'URL (richiede `url` valorizzato nei Finding; finché
   manca, colore neutro e la treemap dice solo superficie).
4. **"La matematica del problema"**: portare `surface_math`
   (`marsbeacon/base.py:1334-1359`) — superficie attuale vs potenziale
   (~900 parole/pagina, 4 chunk + FAQ) ed effetto moltiplicativo
   sull'RRF, con l'assunzione dichiarata nel testo. Chiave
   `"surface_math"` nel dato canonico, sezioni text/HTML
   (`render.py:368-399` e `1193-1213`).
5. **Grafo dei link interni** — dipende da D1:
   - D1 = sì: portare `link_graph_data` (`indexes.py:414`; il crawler
     estrae già `links` per pagina, `mars_core.py:766`) e il JS inline
     progressive-enhancement (`render.py:1385-1795`): base SVG statica
     identica senza JS, viste forza/anelli, evidenziazione, zoom,
     `prefers-reduced-motion` rispettato. Adeguare il test no-script
     (`tests/test_report.py:132-141`) nello stesso commit della
     decisione: da "nessuno `<script>`" a "nessuna origine esterna,
     nessun payload non inline".
   - D1 = no: fermarsi a profondità + treemap; registrare in AS-IS la
     rinuncia consapevole.

**Test.** `pages[]` presente e serializzabile; bucket di profondità
corretti su un sito sintetico a 3 livelli; treemap con somma aree ≈
superficie; con D1 = sì, golden HTML rigenerato e test che il JS non
referenzia origini esterne.

---

### Fase 9 — i18n del referto (G05) — ✅ CHIUSA (2026-08-25)

> **Come è stata fatta davvero, e in che cosa differisce da questo piano.**
> Le voci U9.1-U9.3 stanno in [AS-IS.md](AS-IS.md); qui restano le due
> divergenze che chi rilegge il piano deve conoscere.
>
> **Le lingue sono due, it ed en, non cinque** (decisione D4). Il piano
> prevede di riusare i cataloghi di marsbeacon «dove i controlli coincidono»:
> misurato prima di cominciare, il riferimento ha 145 chiavi, MARS ne emette
> 49, e **ne coincidono quattro**. Non è una questione di nomi da riallineare
> — il riferimento copre `tech`/`sem`/`lex`/`sd`/`rrf` e non ha una sola
> chiave `wcag.`, `sec.` o `seo.`, che sono tre delle nove aree di MARS. Le
> traduzioni si scrivono, e quattro lingue che nessuno qui può verificare
> sarebbero quattro lingue di qualità non misurata. È **dichiarato** come
> livello inferiore, e l'impianto non assume che le lingue siano due.
>
> **Il catalogo della cornice è indicizzato sul testo italiano**, non su
> chiavi simboliche: così l'italiano resta scritto nel renderer e la stessa
> funzione traduce anche i testi che arrivano dal dato. Il prezzo — due
> significati che condividono una stringa — si paga col `contesto` di `t()`,
> che è il `msgctxt` di gettext.
>
> **Il JSON resta canonico italiano** come previsto al passo 2, con una
> eccezione che il piano non poteva prevedere: i testi di axe, ZAP e
> Lighthouse nascono al momento della misura, quindi nella lingua con cui
> l'audit ha girato. Ogni rilievo la dichiara in `params["text_lang"]`.



**Il problema.** Referto solo in italiano cablato (`<html lang='it'>`
fisso a `mars_report.py:796`, etichette hardcoded tipo `STATO_LEGGIBILE`
a `188-193`, nessun flag di lingua nella CLI). marsbeacon serve 5 lingue
con tre meccanismi e un principio: **fallback dichiarato sull'italiano,
mai un'eccezione** (`i18n.py:5620-5650`).

**Passi.**

1. Nuovo `MARS/mars_i18n.py` sul modello di `marsbeacon/i18n.py`:
   - catalogo della **cornice** per le sezioni del referto MARS/
     (testata, quadranti e note, legenda, stati `STATO_LEGGIBILE`,
     qualificatori, RRF, citabilità, giudizio, delta, piano, "Cosa non è
     stato guardato", footer) nelle lingue di D4;
   - cataloghi dei **rilievi** per lingua: template
     title/detail/fix/example indicizzati per `key`, risolti su
     `key`+`params` del Finding (Fase 1) da una `finding_texts` con
     fallback campo per campo sull'italiano. Riusare le traduzioni già
     scritte in marsbeacon (`_FINDINGS_EN/FR/DE/ES`,
     `i18n.py:1045/1991/3002/4043`) dove i controlli coincidono;
   - per Lighthouse, le lingue vengono dai file di locale del fork
     (meccanismo `_LH_FRAME`, `i18n.py:5656+`), non si ritraducono a
     mano.
2. Parametro `lang="it"` nei renderer di prosa (text/html/md/csv);
   il **JSON resta canonico italiano** ma porta `key`+`params` così le
   integrazioni traducono da sole (documentarlo). Nota di onestà in
   testa ai formati di prosa non-it: le evidenze citate dal sito restano
   nella lingua del sito (`evidence_note`, `i18n.py:5583`).
3. `--lang {it,en,fr,de,es}` in `mars_audit.py`, default `it`.
4. Golden: si congelano in `it` (canonico); per le altre lingue bastano
   test funzionali.

**Test** (modello `tests/test_i18n.py` di MARS-Beacon): parità di chiavi
fra cataloghi; tutti i template formattabili coi `params` dichiarati;
fallback su chiave mancante senza eccezioni; "zero fallback" su un audit
sintetico completo in `en` (ogni rilievo emesso ha la sua traduzione).

---

### Fase 10 — Giudizio LLM multi-modello (G08) — ⬜ DA FARE

**Il problema.** MARS/ ha il solo giudice Anthropic
(`mars_llm_judge.py:18`, client a `184-192`) con esito aggregato;
marsbeacon interroga fino a 4 provider con esiti per query e **due
scarti di onestà**: giudice vs indice euristico e giudice vs profilo
dell'assistente corrispondente (`render.py:856-909`).

**Passi.**

1. Registro `JUDGE_PROVIDERS` in `mars_llm_judge.py` sul modello di
   `marsbeacon/base.py:525-559`: anthropic via SDK; openai, qwen, kimi
   via endpoint HTTP OpenAI-compatibile `chat/completions` con
   `requests`; chiavi **solo** da ambiente/`context["credentials"]`
   (`OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, `MOONSHOT_API_KEY`),
   `*_BASE_URL` sovrascrivibile (serve ai server finti nei test); campo
   `profile` che aggancia il provider al profilo di citabilità.
   **Avvertenza verificata**: in MARS/ `citability["profiles"]` è un
   **dict nome → punteggio** (`'Claude'`, `'ChatGPT/Perplexity'`, …,
   `mars_citability.py:214-221`), non una lista di dict con key/label
   come in marsbeacon: il campo `profile` del registro usa quelle
   chiavi-nome (per openai: `'ChatGPT/Perplexity'`) e il calcolo dello
   scarto va adattato a quella forma.
2. `run_judges(context, providers)` che itera i provider selezionati
   (nuovo flag `--judge-models provider[:modello],…` in `mars_audit.py`,
   default `anthropic`), stessa campionatura e stesso prompt per tutti,
   e **non interrompe mai** né gli altri provider né il referto
   (modello: `marsbeacon/audits.py:3827-3851`): ogni esito è
   `{status: ok|skipped|error, provider, model, sampled, average,
   verdicts: [{query, score, reason}], note, profile}`.
3. Dato canonico: `"llm_judgements"` (lista) accanto a `"llm_judgement"`
   legacy (il primo provider riuscito, per compatibilità con i
   consumatori esistenti).
4. Rese: `_sezione_llm` e la vista testo iterano sugli esiti; per ogni
   giudice `ok`, tabella dei verdetti per query e le due righe di
   scarto: vs `citability["score"]` e vs
   `citability["profiles"][profile]`; nota di onestà resa **una sola
   volta** (`render.py:862-881`). I provider `skipped`/`error` compaiono
   con il motivo: un giudice che manca si dichiara, non sparisce
   (principio 2).
5. Il giudizio resta l'ultimo modulo del registro (unico che spende).

**Test.** Client iniettati via context come l'attuale
`_anthropic_client` (`mars_llm_judge.py:186-188`) + server HTTP finto
per gli OpenAI-compatibili; un provider che fallisce non toglie gli
altri dal referto; scarti calcolati giusti su numeri costruiti.

---

### Fase 11 — Il deliverable rifinito: stampa, tabelle, brand (G14, G15) — ⬜ DA FARE

**Passi (G14 — stampa e accessibilità).**

1. Blocco `@media print` nella costante `CSS` di `mars_report.py`
   (modello: `render.py:1926-1943`): palette funzionale a contrasto
   pieno, `print-color-adjust: exact` (i quadranti SVG stampano i
   colori), `@page` con margini, `break-inside: avoid` su `.area` e
   `.card`, ancore nascoste, URL dei link stampati via `::after`.
   Un referto di consulenza finisce in PDF: oggi MARS/ non ha **alcuna**
   regola di stampa.
2. Tabelle: **avvertenza verificata** — la tabella dei profili di
   citabilità (`mars_report.py:740-752`) non ha `th`, e la tabella RRF
   (`724-725`) ha `th` ma **non** `thead`: aggiungere `thead` + `th
   scope='col'` a entrambe; `aria-hidden='true'` sulle barre decorative
   (`span.bar`, riga 742).
3. Test: presenza del blocco print e dei `th`/`thead`
   (modello: `tests/test_report_html.py:69-73`).

**Passi (G15 — brand nel footer).**

4. `<footer>` in `render_html` (oggi il documento chiude a
   `mars_report.py:835` **senza** footer): firma testuale, riga
   "Generato da mars_audit.py v{version} · formula RRF k={k}",
   riferimenti (Cormack et al. SIGIR 2009, Microsoft Learn, Elastic,
   Schema.org — `render.py:1361-1374`).
5. `_brand_logo_svg()` e `_brand_font_css()` portate da
   `render.py:80-115`, lette da una directory brand del progetto MARS/:
   logo SVG inline solo se il file esiste e inizia con `<svg` (altrimenti
   resta la firma testuale), font woff2 come data URI **tutto o niente**
   (mai un incorporo parziale), stack di sistema in fallback. La lezione
   che ha motivato la Fase 1 del fork vale qui: **il fallback non deve
   essere silenzioso nei test** — il test del caso BUONO verifica che
   con gli asset presenti logo e `@font-face` siano davvero nel referto,
   quello di degrado che senza asset il referto resti valido e firmato
   (modello: `tests/test_report_html.py:189-205`).
6. Il white-label completo (palette da TOML con guardia di contrasto,
   `tools/brandizza.py`) riguarda la GUI: **rimandato esplicitamente**
   a quando MARS/ ne avrà una — registrarlo in TO-DO, non improvvisarlo.

---

### Fase 12 — Ancore esterne alla simulazione (G13) — ⬜ DA FARE, OPZIONALE

Due sezioni di marsbeacon confrontano la simulazione col mondo reale.
Richiedono prima il **motore**, poi la resa; sono l'ultima fase perché
il valore è alto ma non dipende da nulla e nulla vi dipende.

1. **Ancora di realtà (Brave Search)**: portare `run_search_check`
   (`marsbeacon/audits.py:3896-3976`): posizione reale del sito sulle
   query accanto al consenso RRF, esiti ok/skipped/error mai bloccanti,
   nota di onestà. **Avvertenza verificata**: in marsbeacon la chiave si
   legge da `os.environ` (`SEARCH_CHECK_ENV = "BRAVE_API_KEY"`,
   `base.py:585`); in MARS/ va letta da `context["credentials"]` con
   fallback sull'ambiente, coerente col meccanismo documentato in
   CLAUDE.md. Chiave `"search_check"` nel dato canonico, sezioni in
   text/HTML (`render.py:312-347`, `945-980`).
2. **Confronto competitivo / share of voice**: nuovo flag
   `--competitors`, crawl leggero dei concorrenti, indicizzazione
   condivisa e share per query (adattare `ShareResult` e
   `simulate_share_of_voice`, `audits.py:3085-3258`, ai chunk di
   mars_core). Resa: tabella share con marcatore "← tuo sito", tabella
   per query, mappa a bolle SVG **dichiarata decorativa** (i numeri
   stanno nelle tabelle; `render.py:1285-1359`).
3. **Alternativa minimale** (se la fase non si fa): integrare nel
   referto i risultati di `mars_citations --from-audit` — che già legge
   `rrf_simulation` (`mars_core.py:1074-1084`) — come sezione "Citazioni
   reali", e registrare in AS-IS la scelta.

---

## 6. La scheda definitiva del referto di MARS/ dopo l'adeguamento

> **Aggiornamento 2026-08-25.** È la scheda **a lavori conclusi**, quindi
> descrive in parte il presente e in parte l'obiettivo. Ciò che manca viene
> tutto dalle tre fasi che restano: i giudizi multi-modello con gli scarti
> (Fase 10), il CSS di stampa, l'accessibilità delle tabelle e il brand nel
> footer (Fase 11), le ancore esterne (Fase 12). Il resto è in piedi, e la
> forma esatta del dato canonico prodotto oggi si legge senza fidarsi di
> questa scheda: sta congelata in `tests/golden/referto.json`, che è
> aggiornato per costruzione.

Questa è la fotografia del referto a lavori conclusi: il contratto che
le fasi devono realizzare e che i golden congelano.

### 6.1 Il dato canonico (`build_report` → JSON)

Chiavi top-level (le **nuove** in grassetto; l'ordine è quello di
serializzazione):

| Chiave | Tipo | Contenuto | Fase |
|---|---|---|---|
| `tool` | str | `"mars_audit.py"` | — |
| `version` | str | `mars_core.__version__` | — |
| **`schema_version`** | int | versione dello schema JSON (parte da 1; bump solo su cambi incompatibili) | 7 |
| `generated_at` | str | ISO-8601 con timezone | — |
| `url` | str | URL di partenza | — |
| `market` | str | mercato per la citabilità | — |
| `pages_crawled` | int | pagine indicizzate | — |
| `discovery` | str | `sitemap` o `link interni` | — |
| `chunks` | int | chunk totali | — |
| `robots_ignored` | bool | dichiarazione di proprietà | — |
| `queries` | list | query della simulazione | — |
| `skipped` | list | URL scartati con motivo | — |
| **`rrf`** | dict | `{k, formula}` dichiarati | 7 |
| **`thresholds`** | dict/null | echo delle soglie configurate (null coi default) | 7 |
| **`overall`** | float/null | punteggio complessivo pesato (D3) | 5 |
| `areas` | list | una voce per area, vedi sotto | — |
| `rrf_simulation` | list | consenso per query (contratto con mars_citations `--from-audit`) | — |
| `rrf_aggregate` | dict/null | consenso aggregato | — |
| `citability` | dict/null | profili per assistente, indice, disclaimer, **`top_actions`** | 4 |
| `llm_judgement` | dict/null | primo giudice riuscito (legacy) | — |
| **`llm_judgements`** | list | un esito per provider: `{status, provider, model, sampled, average, verdicts[], note, profile}` | 10 |
| **`delta`** | dict/null | `{previous_generated_at, scores, resolved[], new[]}` | 7 |
| **`remediation`** | list | piano ordinato, vedi sotto | 4 |
| **`pages`** | list | `{url, title, headings, chunks, jsonld_types, lang}` per pagina | 8 |
| **`surface_math`** | dict/null | superficie attuale vs potenziale, moltiplicatore RRF, assunzione | 8 |
| **`depth_distribution`** | dict/null | bucket di profondità in click | 8 |
| **`link_graph`** | dict/null | nodi/archi del grafo interno (se D1/Fase 8) | 8 |
| **`search_check`** | dict/null | ancora di realtà Brave (se Fase 12) | 12 |
| **`competitive`** | dict/null | share of voice (se Fase 12) | 12 |
| `lexical`, `semantic` | dict | segnali derivati (invariati) | — |

Ogni voce di `areas` (chiavi nuove in grassetto):

```
{
  "module":  "mars_tech",         "label": "1. Tecnica",
  "score":   87.0 | null,         "status": "surface" | "unavailable" |
                                            "disabled" | "error" | null,
  "issues":  ["…"],               # vista compatta legacy, INVARIATA
  "findings": [                   # NUOVO — il dato strutturato
    {
      "area": "mars_tech",
      "severity": "critical" | "warning" | "info" | "ok",
      "source_severity": "grave" | "axe:serious" | "ZAP:High" | "",
      "title": "…", "detail": "…",
      "fix": "…",  "example": "…",       # la remediation del rilievo
      "url": "…",  "weight": 2.0,
      "key": "tech.robots.ai_blocked",   # id stabile (delta, i18n, ancore)
      "params": {"n": 2, "total": 100}   # valori dinamici per i template
    }, …
  ],
  "tool": "…", "wcag_level": "…", "pages_tested": N,
  "audits": […] | null, "form_factor": "…", "complete": true|false|null
}
```

Ogni voce di `remediation`:

```
{
  "priority": 1, "severity": "critical", "area": "mars_tech",
  "title": "…", "fix": "…", "example": "…", "url": "…",
  "effort": "minuti" | "ore" | "giorni",
  "quick_win": true,                  # critico + minuti
  "key": "…", "params": {…},
  "profile_gains": {"Claude": 1.2, "ChatGPT/Perplexity": 0.8, …},
  "best_label": "Claude", "best_gain": 1.2,
  "index_gain": 0.9,                  # guadagno sull'indice composito
  "cross": true, "profiles_hit": ["Claude", "Qwen", …]
}
```

### 6.2 Referto HTML — ordine definitivo delle sezioni

Autoconsistente (un file, nessuna origine esterna), `lang` dinamico,
chiaro/scuro via `prefers-color-scheme`, scala colori 90/50, simbolo
sempre accanto al colore, stampabile.

1. **Testata** — wordmark, URL, riga meta (data · pagine · discovery ·
   chunk · mercato · versione).
2. **Hero** *(nuovo)* — quadrante grande del Complessivo con verdetto
   testuale e soglie dichiarate; tile Critici / Avvertenze / Info;
   donut dello stato pagine.
3. **Fascia quadranti per area** + legenda della scala *(invariata,
   inclusi i quadranti derivati Recuperabilità e In forma di risposta)*.
4. **Top rilievi** *(nuovo)* — top-5 del piano di remediation, pallino +
   etichetta gravità + area + guadagno, link all'ancora del rilievo.
5. **Aree** — una scheda per area *(invariata: voto, qualificatori,
   elenco controlli o rilievi)* con in più, per ogni rilievo: gravità
   canonica, **Fix**, **esempio** in `pre.ex`, **ancora stabile** con
   permalink `#`.
6. **Simulazione RRF** — aggregato + tabella per query *(invariata)*.
7. **Profili di citabilità IA** — tabella profili (ora con `thead`/`th
   scope`) + disclaimer vicino ai numeri *(invariata)* + **Azioni con
   maggior guadagno di profilo** *(nuovo)*.
8. **Giudizio LLM** *(esteso)* — un blocco per provider: tabella dei
   verdetti per query, scarto giudice-euristica, scarto
   giudice-profilo; provider non eseguiti dichiarati col motivo; nota di
   onestà una sola volta.
9. **Rispetto all'esecuzione precedente** *(nuovo)* — variazioni di
   punteggio, Risolti (N), Nuovi (N).
10. **Profondità di crawl** *(nuovo)* — tabella a barre per bucket di
    click; pagine da sola sitemap dichiarate.
11. **Superficie contenutistica** *(nuovo)* — treemap SVG accessibile
    (area = parole, colore = gravità) + tabella di fallback in
    `<details>`.
12. **Architettura dei link** *(nuovo, secondo D1)* — grafo SVG statico;
    con D1 = sì, viste forza/anelli, zoom, evidenziazione via JS inline
    progressive-enhancement.
13. **La matematica del problema** *(nuovo)* — superficie attuale vs
    potenziale, effetto sull'RRF, assunzione dichiarata.
14. **Piano di remediation** *(nuovo)* — tutte le voci numerate con
    badge sforzo / QUICK WIN / trasversale, Fix, esempio, link
    all'ancora del rilievo.
15. **Cosa non è stato guardato** — robots ignorato, URL saltati
    *(invariata)*.
16. **Footer** *(nuovo)* — logo brand (o firma testuale in fallback),
    "Generato da mars_audit.py v… · formula RRF k=…", riferimenti.

CSS: blocco `@media print` completo (palette a contrasto, `@page`,
`break-inside: avoid`, URL stampati); `:target` evidenzia il rilievo
raggiunto da un permalink; `@font-face` brand incorporato tutto-o-niente.

### 6.3 Referto testuale — struttura definitiva

```
=======================================================
           MARS BEACON - REPORT FINALE
=======================================================
COMPLESSIVO          :  78/100                      (nuovo)
{area per area: voto o stato, qualificatori, ⚠ rilievi}   (invariato)
  -> Fix: …                                         (nuovo, per rilievo)
-------------------------------------------------------
RISPETTO ALL'ESECUZIONE PRECEDENTE · {data}          (nuovo)
  {variazioni per area} · Risolti (N) · Nuovi (N)
-------------------------------------------------------
Simulazione RRF      : …                            (invariato)
Profili di citabilità IA …                          (invariato)
  Azioni con maggior guadagno di profilo: …          (nuovo)
Giudizio LLM ({provider}) …   × N provider           (esteso)
  scarto giudice-euristica / giudice-profilo
-------------------------------------------------------
LA MATEMATICA DEL PROBLEMA                           (nuovo)
-------------------------------------------------------
PIANO DI REMEDIATION · N interventi · M quick win    (nuovo)
 1. [CRITICO · Tecnica · sforzo: minuti] …  ** QUICK WIN
    Fix: …
    Esempio: …
-------------------------------------------------------
⚠ robots.txt IGNORATO … / URL saltati                (invariato)
Pagine trovate via   : …                            (invariato)
=======================================================
```

### 6.4 Referto Markdown (nuovo formato)

Testata; tabella Punteggi (aree + **Complessivo**); Profili di
citabilità; Giudizio LLM per provider; **Piano di remediation come task
list `- [ ]`** con gravità/area/sforzo in corsivo; Rilievi per area con
marcatori testuali (`**[CRITICO]**`, `[AVVISO]`, `[info]`, `[ok]`) e
righe Fix; Simulazione RRF in tabella. Pensato per issue e PR: la
checklist si spunta.

### 6.5 Export CSV (nuovo formato)

Una riga per rilievo strutturato; intestazione tradotta secondo
`--lang`; delimitatore `;`; **BOM UTF-8** in testa; colonne:

```
sito;area;gravita;peso;titolo;dettaglio;correzione;url;sforzo;quick_win
```

Sforzo e quick win valorizzati solo per critici e avvertenze.

### 6.6 La CLI dopo l'adeguamento

```
mars_audit.py URL
  --format {text,json,html,md,csv}      # md e csv nuovi (Fase 6)
  --output FILE
  --lang {it,en,fr,de,es}               # nuovo (Fase 9), default it
  --judge-models prov[:modello],…       # nuovo (Fase 10), default anthropic
  --history PATH | --no-history         # nuovo (Fase 7)
  --competitors URL,URL,…               # opzionale (Fase 12)
  … (tutti i flag esistenti invariati)
```

Codici di uscita invariati (0/2/3). Nuove variabili d'ambiente
riconosciute: `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, `MOONSHOT_API_KEY`
(+ `*_BASE_URL` per i test), `BRAVE_API_KEY` (Fase 12) — tutte
opzionali, tutte con degradazione dichiarata.

### 6.7 Presìdi di qualità a regime

- `tests/golden/referto.{txt,json,html,md,csv}` congelano la resa;
  rigenerazione solo intenzionale (`MARS_RIGENERA_GOLDEN=1` + diff
  rivisto) + test di determinismo.
- `tests/test_report.py` esteso: chiavi top-level (con `schema_version`),
  piano di remediation, delta, ancore, print CSS, `thead`/`th`.
- Test i18n: parità cataloghi, template formattabili, fallback, zero
  fallback in `en` su audit sintetico.
- Test brand: caso buono (asset incorporati davvero) E degrado
  (referto valido senza asset) — mai un fallback verificato solo "non
  esplode".
- Suite sempre offline; `flake8 .` a zero; un commit per voce di TO-DO;
  voci chiuse spostate in AS-IS con difetto/soluzione/verifiche.

---

## 7. Tracciabilità divario → fase

La colonna **Verificato** dice che il divario è stato accertato sul codice
il 2026-08-21; **Colmato** dice che la fase che lo chiude è stata eseguita.

| Divario | Titolo breve | Fase | Verificato | Colmato |
|---|---|---|---|---|
| G01 | Finding tipizzato e severità unificata | 1 | ✔ | ✅ |
| G02 | Piano di remediation ordinato | 4 | ✔ | ✅ |
| G03 | Fix ed esempi per ogni controllo | 3 | ✔ | ✅ |
| G04 | Formati Markdown e CSV | 6 | ✔ | ✅ |
| G05 | i18n con `--lang` | 9 | ✔ | ✅ **it/en**, non cinque lingue: D4 |
| G06 | Delta e storico JSONL | 7 | ✔ | ✅ |
| G07 | Complessivo + hero | 5 | ✔ | ✅ |
| G08 | Judges multi-modello con scarti | 10 | ✔ | ⬜ |
| G09 | schema_version, RRF, soglie | 7 | ✔ | ✅ |
| G10 | Golden test | 2 | ✔ | ✅ |
| G11 | Ancore stabili e permalink | 5 | ✔ | ✅ dalla `key`, non dallo slug |
| G12 | Profondità, treemap, grafo, matematica, pages[] | 8 | ✔ | ✅ senza il colore della treemap: **R47** |
| G13 | Brave Search e competitivo | 12 (opz.) | ✔ | ⬜ |
| G14 | Stampa e a11y tabelle | 11 | ✔ | ⬜ |
| G15 | Brand nel footer con fallback | 11 | ✔ | ⬜ |

Tutti i riferimenti `file:riga` di questo documento sono stati
verificati sul codice il 2026-08-21; se il codice evolve prima
dell'esecuzione di una fase, rifare il controllo delle righe citate
prima di intervenire.

> **E il codice è evoluto.** Misurato il 2026-08-25 su un campione: dei
> `file:riga` scritti nel piano nessuno punta più a ciò che nomina —
> `mars_core.py:102` cade su un `return value`, `mars_report.py:30` su una riga
> di import, `tests/test_report.py:132` su una riga vuota.
>
> **Non sono stati rinfrescati, ed è deliberato**, a differenza di quelli del
> TO-DO, che indicano lavoro *da fare* e sono stati riverificati uno per uno.
> Qui indicano il codice **com'era il 2026-08-21**: sono la fotografia su cui
> il divario è stato accertato, e aggiornarli la cancellerebbe senza aggiungere
> nulla, perché il piano delle nove fasi chiuse non si esegue più. Fanno
> eccezione i riferimenti nello **Stato del programma** in testa, che sono di
> oggi perché servono a leggere il presente.
>
> Chi apre la Fase 10, 11 o 12 rifaccia il controllo prima di intervenire, come
> questa nota chiedeva già.
