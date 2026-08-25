# MARS Beacon — https://esempio.test/

*2026-01-01T00:00:00+0000 · v0.0.0 · 3 pagine trovate via sitemap · 4 chunk · mercato eu*

## Complessivo

**66/100** — da migliorare

Media pesata di 7 misure; citabilità e giudizio LLM esclusi. Scala dichiarata: critico sotto 50, da migliorare 50-89, buono da 90.

## Punteggi per area

| Area | Punteggio | Con che cosa |
|---|---|---|
| 1. Tecnica | 57/100 |  |
| 2. SEO | 27/100 | Lighthouse 13.4.1 · mobile · 3 controlli superati, 5 falliti |
| 3. Lessicale | classifica, non un voto | BM25 (k1=1.5, b=0.75) |
| 4. Semantica | classifica, non un voto | proxy char-TFIDF |
| 5. Dati Strutturati | 90/100 |  |
| 6. Accessibilità | 37/100 | axe-core · WCAG 2.1 A + AA · scansione parziale · 2 pagine esaminate · Lighthouse 97/100 (1 pagina, scala diversa: la nostra è più severa) |
| 7. Sicurezza | 57/100 | ZAP (passiva) |
| 8. Citabilità IA | 66/100 |  |
| 9. Giudizio LLM | 61/100 |  |

## Piano di interventi

16 interventi (6 critici, 10 avvertenze) · 1 quick win.

- [ ] **[CRITICO]** robots.txt BLOCCA 1 crawler IA: GPTBot — *Tecnica · sforzo: minuti · +40 punti d'area · indice +7.54* · **QUICK WIN**
      Togli il Disallow che blocca gli agenti che vuoi ti citino. Non basta aggiungere un blocco permissivo in fondo: per ogni agente vale il PRIMO gruppo che lo nomina, quindi la riga va corretta dov'e'.
- [ ] **[CRITICO]** L'indicizzazione della pagina è bloccata — *SEO · sforzo: non dichiarato · +37 punti d'area · indice +4.74*
- [ ] **[CRITICO]** Le immagini devono avere un testo alternativo — *Accessibilità · sforzo: non dichiarato · +37 punti d'area · indice +4.65*
      Assicurati che gli elementi <img> abbiano un testo alternativo o un ruolo none o presentation
- [ ] **[CRITICO]** Cross Site Scripting (Reflected) — *Sicurezza · sforzo: non dichiarato · +28 punti d'area · indice +1.76*
      Convalida l'input e codifica l'output.
- [ ] **[CRITICO]** 1 campi di modulo senza etichetta — *Accessibilità · sforzo: giorni*
      Collega ogni campo a una <label>: un `placeholder` non la sostituisce, perche' sparisce appena si scrive.
- [ ] **[CRITICO]** 1/2 immagini prive di testo alternativo — *Accessibilità · sforzo: giorni*
      Dai un testo alternativo a ogni immagine che porta informazione, e alt="" a quelle decorative: le due cose sono diverse, e omettere l'attributo non e' nessuna delle due.
- [ ] [AVVISO] Il contrasto deve essere sufficiente — *Accessibilità · sforzo: non dichiarato · +18 punti d'area · indice +2.26*
      Assicurati che il contrasto tra i colori in primo piano e di sfondo soddisfi le soglie minime del rapporto di contrasto WCAG 2 AA
- [ ] [AVVISO] 1 blocchi JSON-LD malformati — *Dati Strutturati · sforzo: ore · +10 punti d'area · indice +1.58*
      Correggi la sintassi del blocco: un JSON-LD che non si analizza viene ignorato per intero, non in parte.
- [ ] [AVVISO] Il documento non ha un elemento `<title>` — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] Gli elementi immagine non hanno attributi `[alt]` — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] I link non hanno testo descrittivo — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] Il documento non ha una meta descrizione — *SEO · sforzo: non dichiarato · +9 punti d'area · indice +1.15*
- [ ] [AVVISO] I campi di modulo devono avere un'etichetta — *Accessibilità · sforzo: non dichiarato · +7 punti d'area · indice +0.88*
- [ ] [AVVISO] Content Security Policy (CSP) Header Not Set — *Sicurezza · sforzo: non dichiarato · +12 punti d'area · indice +0.75*
      Configura il server per impostare l'header CSP.
- [ ] [AVVISO] 1 salti nella gerarchia degli heading (es. h2 seguito da h4) — *Accessibilità · sforzo: ore*
      Non saltare i livelli di heading: la gerarchia e' l'indice con cui si naviga una pagina senza vederla. Per rimpicciolire un titolo si usa il CSS.
- [ ] [AVVISO] 1 tabelle dati senza intestazioni <th> — *Accessibilità · sforzo: ore*
      Usa <th> per le intestazioni delle tabelle di dati, con `scope`: senza, ogni cella viene letta senza sapere di che colonna sia.

## Rilievi per area

### 1. Tecnica

- **[CRITICO]** robots.txt BLOCCA 1 crawler IA: GPTBot
  *Correzione:* Togli il Disallow che blocca gli agenti che vuoi ti citino. Non basta aggiungere un blocco permissivo in fondo: per ogni agente vale il PRIMO gruppo che lo nomina, quindi la riga va corretta dov'e'.

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

Nessun rilievo.

### 4. Semantica

Nessun rilievo.

### 5. Dati Strutturati

- [AVVISO] 1 blocchi JSON-LD malformati
  *Correzione:* Correggi la sintassi del blocco: un JSON-LD che non si analizza viene ignorato per intero, non in parte.

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
- [AVVISO] Il contrasto deve essere sufficiente
  *Correzione:* Assicurati che il contrasto tra i colori in primo piano e di sfondo soddisfi le soglie minime del rapporto di contrasto WCAG 2 AA
- [AVVISO] I campi di modulo devono avere un'etichetta
- **[CRITICO]** 1/2 immagini prive di testo alternativo
  *Correzione:* Dai un testo alternativo a ogni immagine che porta informazione, e alt="" a quelle decorative: le due cose sono diverse, e omettere l'attributo non e' nessuna delle due.

  ```
  <img src="/sala.jpg" alt="La sala trattamenti">
  <img src="/onda.svg" alt="">
  ```
- [AVVISO] 1 salti nella gerarchia degli heading (es. h2 seguito da h4)
  *Correzione:* Non saltare i livelli di heading: la gerarchia e' l'indice con cui si naviga una pagina senza vederla. Per rimpicciolire un titolo si usa il CSS.
- **[CRITICO]** 1 campi di modulo senza etichetta
  *Correzione:* Collega ogni campo a una <label>: un `placeholder` non la sostituisce, perche' sparisce appena si scrive.

  ```
  <label for="nome">Nome</label>
  <input id="nome" name="nome" type="text">
  ```
- [AVVISO] 1 tabelle dati senza intestazioni <th>
  *Correzione:* Usa <th> per le intestazioni delle tabelle di dati, con `scope`: senza, ogni cella viene letta senza sapere di che colonna sia.

  ```
  <table>
    <tr><th scope="col">Trattamento</th><th scope="col">Durata</th></tr>
    <tr><td>Drenaggio</td><td>50 minuti</td></tr>
  </table>
  ```
- [INFO] 1 link con testo generico ("clicca qui", "leggi tutto")
  *Correzione:* Scrivi nel link la destinazione, non l'azione: chi naviga per elenco di link legge solo quel testo, fuori dal contesto della frase.

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
- [INFO] Strict-Transport-Security non impostato
- [INFO] Solo scansione passiva: l'active scan richiede --i-own-this-domain

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
| Claude | 68.9 |
| ChatGPT/Perplexity | 63.4 |
| Qwen | 66.7 |
| Kimi | 66.7 |
| **Indice composito** | **65.6** |

*stime euristiche dichiarate, non comportamento documentato dai vendor*

## Giudizio LLM

Modello: claude-opus-5, su 4 passaggi.

Citabilità stimata: **61/100**

I passaggi rispondono a domande esplicite e si reggono fuori dal contesto, ma il listino non e' verificabile.

## Simulazione RRF

| Query | Consenso | Passaggio migliore |
|---|---|---|
| drenaggio linfatico | 3/3 | https://esempio.test/ § Che cos'e' il drenaggio linfatico? |
| quanto costa una seduta di drenaggio linfatico | 2/3 | https://esempio.test/ § Che cos'e' il drenaggio linfatico? |
| parcheggio riservato | nessun riscontro | — |

## Cosa non è stato guardato

- vietato da robots.txt: https://esempio.test/privato
- altro host: https://altro.test/
- non HTML: https://esempio.test/listino.pdf
- URL non analizzabile: https://esempio.test/[2001
