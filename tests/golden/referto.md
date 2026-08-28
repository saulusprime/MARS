# MARS Beacon — https://esempio.test/

*2026-01-01T00:00:00+0000 · v0.0.0 · 3 pagine trovate via sitemap · 4 chunk · mercato eu*

*I testi di questi strumenti restano nella loro lingua: ZAP (passiva) (en), axe-core (en).*

## Complessivo

**60/100** — da migliorare

Media pesata di 7 misure; escluse 3. Lessicale, 4. Semantica, 8. Citabilità IA, 9. Giudizio LLM. Scala dichiarata: critico sotto 50, da migliorare 50-89, buono da 90.

## Punteggi per area

| Area | Punteggio | Con che cosa |
|---|---|---|
| 1. Tecnica | 57/100 |  |
| 2. SEO | 27/100 | Lighthouse 13.4.1 · mobile · 3 controlli superati, 5 falliti |
| 3. Lessicale | 60/100 | BM25 (k1=1.5, b=0.75) · con una classifica dei passaggi |
| 4. Semantica | 92/100 | proxy char-TFIDF · con una classifica dei passaggi |
| 5. Dati Strutturati | 90/100 |  |
| 6. Accessibilità | 37/100 | axe-core · WCAG 2.1 A + AA · scansione parziale · 2 pagine esaminate · Lighthouse 97/100 (1 pagina, scala diversa: la nostra è più severa) |
| 7. Sicurezza | 57/100 | ZAP (passiva) · 3 pagine esaminate |
| 8. Citabilità IA | 61/100 |  |
| 9. Giudizio LLM | 61/100 |  |

## Superficie

| Distanza dalla home | Pagine |
|---|---|
| profondità ignota | 3 |

3 pagine, 4 passaggi — 1.33 per pagina, 87 parole per pagina.
Con 900 parole per pagina i passaggi sarebbero **12**, cioè **x3.0**.

*proiezione, non misura: si assume una pagina di contenuto sostanziale intorno alle 900 parole, da cui il chunker ricava circa 4 passaggi*

## Rispetto all'esecuzione precedente

Confronto con il 2025-12-01T09:00:00+0000 (v0.0.0).

| Area | Prima | Dopo | Variazione |
|---|---|---|---|
| Complessivo | 61 | 60 | -1 |
| tech | 40 | 57 | +17 |
| schema | 100 | 90 | -10 |
| llm_judge | 55 | 61 | +6 |
| citability | 60 | 61 | +1 |

**Risolti (1)**

- Nessuna sitemap dichiarata

**Nuovi (19)**

- L'indicizzazione della pagina è bloccata
- Il documento non ha un elemento `<title>`
- Il documento non ha una meta descrizione
- I link non hanno testo descrittivo
- Gli elementi immagine non hanno attributi `[alt]`
- 3/3 pagine sotto le 300 parole
- 1/3 query senza un riscontro lessicale
- 4 passaggi indicizzabili su 3 pagine, sotto i 20 attesi
- 1 blocchi JSON-LD malformati
- Le immagini devono avere un testo alternativo
- Gli elementi devono soddisfare le soglie minime del rapporto di contrasto di colore
- Form elements must have labels
- 1/2 immagini prive di testo alternativo
- 1 salti nella gerarchia degli heading (es. h2 seguito da h4)
- 1 campi di modulo senza etichetta
- 1 tabelle dati senza intestazioni <th>
- Cross Site Scripting (Reflected)
- Content Security Policy (CSP) Header Not Set
- CSP: Wildcard Directive

*È cambiato che cosa si misura — il menu di navigazione, la testata e il piede non entrano piu' nel corpus dei passaggi ne' nel conteggio delle parole (R63): i numeri si muovono anche a sito invariato.*

*Le chiavi sec.zap. hanno cambiato forma — gli alert ZAP si raggruppano per sotto-variante e non piu' per sola regola: sec.zap.10038 e' diventato sec.zap.10038_1, _2, _3 (R39): in quest'area «risolto» e «comparso» non sono fatti del sito.*

## Piano di interventi

20 interventi (6 critici, 14 avvertenze) · 1 quick win.

- [ ] **[CRITICO]** robots.txt BLOCCA 1 crawler IA: GPTBot — *Tecnica · sforzo: minuti · +40 punti d'area · indice +7.54* · **QUICK WIN**
      Togli il Disallow che blocca gli agenti che vuoi ti citino. Non basta aggiungere un blocco permissivo in fondo: per ogni agente vale il PRIMO gruppo che lo nomina, quindi la riga va corretta dov'e'.
- [ ] **[CRITICO]** L'indicizzazione della pagina è bloccata — *SEO · sforzo: non dichiarato · +37 punti d'area · indice +4.74*
- [ ] **[CRITICO]** Le immagini devono avere un testo alternativo — *Accessibilità · sforzo: non dichiarato · +37 punti d'area · indice +4.65*
      Assicurati che gli elementi <img> abbiano un testo alternativo o un ruolo none o presentation
- [ ] **[CRITICO]** Cross Site Scripting (Reflected) — *Sicurezza · sforzo: non dichiarato · +28 punti d'area · indice +1.76*
      Convalida l'input e codifica l'output.
- [ ] **[CRITICO]** 1 campi di modulo senza etichetta — *Accessibilità · sforzo: ore*
      Collega ogni campo a una <label>: un `placeholder` non la sostituisce, perche' sparisce appena si scrive.
- [ ] **[CRITICO]** 1/2 immagini prive di testo alternativo — *Accessibilità · sforzo: ore*
      Dai un testo alternativo a ogni immagine che porta informazione, e alt="" a quelle decorative: le due cose sono diverse, e omettere l'attributo non e' nessuna delle due.
- [ ] [AVVISO] Gli elementi devono soddisfare le soglie minime del rapporto di contrasto di colore — *Accessibilità · sforzo: non dichiarato · +18 punti d'area · indice +2.26*
      Assicurati che il contrasto tra i colori in primo piano e di sfondo soddisfi le soglie minime del rapporto di contrasto WCAG 2 AA
- [ ] [AVVISO] 1 blocchi JSON-LD malformati — *Dati Strutturati · sforzo: minuti · +10 punti d'area · indice +1.58*
      Correggi la sintassi del blocco: un JSON-LD che non si analizza viene ignorato per intero, non in parte.
- [ ] [AVVISO] Il documento non ha un elemento `<title>` — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] Gli elementi immagine non hanno attributi `[alt]` — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] I link non hanno testo descrittivo — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] Il documento non ha una meta descrizione — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] Form elements must have labels — *Accessibilità · sforzo: non dichiarato · +7 punti d'area · indice +0.88*
      Ensure every form element has a label
- [ ] [AVVISO] Content Security Policy (CSP) Header Not Set — *Sicurezza · sforzo: non dichiarato · +6 punti d'area · indice +0.38*
      Configura il server per impostare l'header CSP.
- [ ] [AVVISO] CSP: Wildcard Directive — *Sicurezza · sforzo: non dichiarato · +6 punti d'area · indice +0.38*
      Sostituisci il carattere jolly con le origini che servono davvero.
- [ ] [AVVISO] 1/3 query senza un riscontro lessicale — *Lessicale · sforzo: ore · +20 punti d'area*
      Nessun termine della domanda compare nel sito: scrivi un passaggio che usi le parole con cui la domanda viene posta, non i sinonimi interni all'azienda.
- [ ] [AVVISO] 3/3 pagine sotto le 300 parole — *Lessicale · sforzo: giorni · +20 punti d'area*
      Porta le pagine chiave oltre la soglia con contenuto informativo, non promozionale: BM25 normalizza la frequenza dei termini sulla lunghezza del documento, e due paragrafi non arrivano alla frequenza che la formula premia.
- [ ] [AVVISO] 4 passaggi indicizzabili su 3 pagine, sotto i 20 attesi — *Semantica · sforzo: giorni · +8 punti d'area*
      Aumenta il numero di passaggi tematici autonomi: ogni passaggio e' un'occasione distinta di comparire in una lista di risultati.
- [ ] [AVVISO] 1 salti nella gerarchia degli heading (es. h2 seguito da h4) — *Accessibilità · sforzo: minuti*
      Non saltare i livelli di heading: la gerarchia e' l'indice con cui si naviga una pagina senza vederla. Per rimpicciolire un titolo si usa il CSS.
- [ ] [AVVISO] 1 tabelle dati senza intestazioni <th> — *Accessibilità · sforzo: minuti*
      Usa <th> per le intestazioni delle tabelle di dati, con `scope`: senza, ogni cella viene letta senza sapere di che colonna sia.

## Rilievi per area

### 1. Tecnica

- **[CRITICO]** robots.txt BLOCCA 1 crawler IA: GPTBot
  *Correzione:* Togli il Disallow che blocca gli agenti che vuoi ti citino. Non basta aggiungere un blocco permissivo in fondo: per ogni agente vale il PRIMO gruppo che lo nomina, quindi la riga va corretta dov'e'.

  *Esempio — non è contenuto del tuo sito*
  ```
  # robots.txt — il gruppo va CORRETTO, non aggiunto
  # prima:
  #   User-agent: GPTBot
  #   Disallow: /
  # dopo:
  User-agent: GPTBot
  Disallow:
  ```
- [INFO] 2/3 pagine senza <link rel="canonical">
  *Correzione:* Dichiara <link rel="canonical"> su ogni pagina: senza, due URL che servono lo stesso contenuto competono fra loro.

  *Esempio — non è contenuto del tuo sito*
  ```
  <link rel="canonical" href="https://esempio.it/servizi/">
  ```

### 2. SEO

- **[CRITICO]** L'indicizzazione della pagina è bloccata
  I motori di ricerca non sono in grado di includere le pagine nei risultati di ricerca se non dispongono dell'autorizzazione per eseguirne la scansione. Scopri di più sulle istruzioni dei crawler.
- [AVVISO] Il documento non ha un elemento `<title>`
  Il titolo fornisce agli utenti di screen reader una panoramica della pagina, mentre per gli utenti di motori di ricerca è utile per stabilire se una pagina è pertinente alla loro ricerca. Scopri di più sui titoli dei documenti.
- [AVVISO] Il documento non ha una meta descrizione
  Le meta descrizioni possono essere incluse nei risultati di ricerca per riassumere brevemente i contenuti della pagina. Scopri di più sulla meta descrizione.
- [AVVISO] I link non hanno testo descrittivo
  Il testo descrittivo dei link aiuta i motori di ricerca a comprendere i tuoi contenuti. Scopri come rendere più accessibili i link.
- [AVVISO] Gli elementi immagine non hanno attributi `[alt]`
  Gli elementi informativi dovrebbero mostrare testo alternativo breve e descrittivo. Gli elementi decorativi possono essere ignorati con un attributo ALT vuoto. Scopri di più sull'attributo `alt`.
- [INFO] Non applicabile a questa pagina: robots.txt è valido
  Se il file robots.txt non è valido, i crawler potrebbero non essere in grado di capire come vuoi che il tuo sito web venga sottoposto a scansione o indicizzato. Scopri di più sul file robots.txt.
- [INFO] Non applicabile a questa pagina: Il documento ha un elemento `rel=canonical` valido
  I link canonici suggeriscono quale URL mostrare nei risultati di ricerca. Scopri di più sui link canonici.
- [INFO] Da verificare a mano: Dati strutturati validi
  Esegui lo Strumento di test per i dati strutturati per convalidare i dati strutturati. Scopri di più sui dati strutturati.

### 3. Lessicale

- [AVVISO] 3/3 pagine sotto le 300 parole
  *Correzione:* Porta le pagine chiave oltre la soglia con contenuto informativo, non promozionale: BM25 normalizza la frequenza dei termini sulla lunghezza del documento, e due paragrafi non arrivano alla frequenza che la formula premia.
- [AVVISO] 1/3 query senza un riscontro lessicale
  *Correzione:* Nessun termine della domanda compare nel sito: scrivi un passaggio che usi le parole con cui la domanda viene posta, non i sinonimi interni all'azienda.

### 4. Semantica

- [AVVISO] 4 passaggi indicizzabili su 3 pagine, sotto i 20 attesi
  *Correzione:* Aumenta il numero di passaggi tematici autonomi: ogni passaggio e' un'occasione distinta di comparire in una lista di risultati.

### 5. Dati Strutturati

- [AVVISO] 1 blocchi JSON-LD malformati
  *Correzione:* Correggi la sintassi del blocco: un JSON-LD che non si analizza viene ignorato per intero, non in parte.

  *Esempio — non è contenuto del tuo sito*
  ```
  // prima — la virgola finale rende il blocco invalido
  {"@type": "Service",}
  // dopo
  {"@type": "Service"}
  ```

### 6. Accessibilità

- [INFO] axe non ha esaminato 1 delle 3 pagine del campione
- **[CRITICO]** Le immagini devono avere un testo alternativo
  *Correzione:* Assicurati che gli elementi <img> abbiano un testo alternativo o un ruolo none o presentation
- [AVVISO] Gli elementi devono soddisfare le soglie minime del rapporto di contrasto di colore
  *Correzione:* Assicurati che il contrasto tra i colori in primo piano e di sfondo soddisfi le soglie minime del rapporto di contrasto WCAG 2 AA
- [AVVISO] Form elements must have labels
  *Correzione:* Ensure every form element has a label
- **[CRITICO]** 1/2 immagini prive di testo alternativo
  *Correzione:* Dai un testo alternativo a ogni immagine che porta informazione, e alt="" a quelle decorative: le due cose sono diverse, e omettere l'attributo non e' nessuna delle due.

  *Esempio — non è contenuto del tuo sito*
  ```
  <img src="/sala.jpg" alt="La sala trattamenti">
  <img src="/onda.svg" alt="">
  ```
- [AVVISO] 1 salti nella gerarchia degli heading (es. h2 seguito da h4)
  *Correzione:* Non saltare i livelli di heading: la gerarchia e' l'indice con cui si naviga una pagina senza vederla. Per rimpicciolire un titolo si usa il CSS.
- **[CRITICO]** 1 campi di modulo senza etichetta
  *Correzione:* Collega ogni campo a una <label>: un `placeholder` non la sostituisce, perche' sparisce appena si scrive.

  *Esempio — non è contenuto del tuo sito*
  ```
  <label for="nome">Nome</label>
  <input id="nome" name="nome" type="text">
  ```
- [AVVISO] 1 tabelle dati senza intestazioni <th>
  *Correzione:* Usa <th> per le intestazioni delle tabelle di dati, con `scope`: senza, ogni cella viene letta senza sapere di che colonna sia.

  *Esempio — non è contenuto del tuo sito*
  ```
  <table>
    <tr><th scope="col">Trattamento</th><th scope="col">Durata</th></tr>
    <tr><td>Drenaggio</td><td>50 minuti</td></tr>
  </table>
  ```
- [INFO] 1 link con testo generico ("clicca qui", "leggi tutto")
  *Correzione:* Scrivi nel link la destinazione, non l'azione: chi naviga per elenco di link legge solo quel testo, fuori dal contesto della frase.

  *Esempio — non è contenuto del tuo sito*
  ```
  <!-- invece di: <a href="/prezzi/">clicca qui</a> -->
  <a href="/prezzi/">Il listino dei trattamenti</a>
  ```

### 7. Sicurezza

- **[CRITICO]** Cross Site Scripting (Reflected)
  Il valore inviato viene restituito nella pagina senza codifica: un attaccante puo' farvi eseguire script arbitrario nel browser della vittima.
  *Correzione:* Convalida l'input e codifica l'output.
- [AVVISO] Content Security Policy (CSP) Header Not Set
  Senza Content-Security-Policy il browser non ha modo di sapere quali origini siano legittime.
  *Correzione:* Configura il server per impostare l'header CSP.
- [AVVISO] CSP: Wildcard Directive
  La direttiva ammette qualunque origine, quindi non restringe nulla.
  *Correzione:* Sostituisci il carattere jolly con le origini che servono davvero.
- [INFO] Strict-Transport-Security non impostato
- [INFO] Solo scansione passiva sulle 3 pagine scansionate: spider e active scan richiedono --i-own-this-domain

### 8. Citabilità IA

- [INFO] Segnale debole: Qualità SEO (27/100)
- [INFO] Segnale debole: Accessibilità (37/100)
- [INFO] Segnale debole: Accesso e indicizzabilità (57/100)
- [INFO] Segnale debole: Sicurezza (57/100)

### 9. Giudizio LLM

- Nessun prezzo verificabile
- Nessuna fonte citata
- Nessuna data di aggiornamento

## Profili di citabilità IA

Mercato: eu

| Assistente | Indice |
|---|---|
| Claude | 62.3 |
| ChatGPT/Perplexity | 59.5 |
| Qwen | 62.0 |
| Kimi | 62.0 |
| **Indice composito** | **60.7** |

*stime euristiche dichiarate, non comportamento documentato dai vendor*

## Giudizio LLM

Modello: claude-opus-5, su 4 passaggi.

Citabilità stimata: **61/100**

I passaggi rispondono a domande esplicite e si reggono fuori dal contesto, ma il listino non e' verificabile.

## Simulazione RRF

| Query | Consenso | Passaggio migliore |
|---|---|---|
| drenaggio linfatico | 3/3 | https://esempio.test/ § Che cos'e' il drenaggio linfatico? |
| quanto costa una seduta di drenaggio linfatico | 3/3 | https://esempio.test/ § Quanto dura una seduta? |
| parcheggio riservato | nessun riscontro | — |

al variare di k: k=0 2/3 · k=10 2/3 · k=60 (in uso) 2/3 · k=300 2/3

## Cosa non è stato guardato

- vietato da robots.txt: https://esempio.test/privato
- altro host: https://altro.test/
- non HTML: https://esempio.test/listino.pdf
- URL non analizzabile: https://esempio.test/[2001
