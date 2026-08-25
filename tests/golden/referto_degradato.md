# MARS Beacon — https://esempio.test/

*2026-01-01T00:00:00+0000 · v0.0.0 · 3 pagine trovate via sitemap · 4 chunk · mercato italia*

## Complessivo

**66/100** — da migliorare

Media pesata di 4 misure; citabilità e giudizio LLM esclusi. Scala dichiarata: critico sotto 50, da migliorare 50-89, buono da 90.

## Punteggi per area

| Area | Punteggio | Con che cosa |
|---|---|---|
| 1. Tecnica | 57/100 |  |
| 2. SEO | non misurato |  |
| 3. Lessicale | classifica, non un voto | BM25 (k1=1.5, b=0.75) |
| 4. Semantica | errore del modulo |  |
| 5. Dati Strutturati | 90/100 |  |
| 6. Accessibilità | 40/100 | markup · WCAG 2.1 A + AA (parziale: solo criteri statici) · controllo di superficie |
| 7. Sicurezza | 75/100 | HTTP-Headers · controllo di superficie |
| 8. Citabilità IA | 68/100 |  |
| 9. Giudizio LLM | disattivato |  |

## Piano di interventi

8 interventi (3 critici, 5 avvertenze) · 1 quick win.

- [ ] **[CRITICO]** robots.txt BLOCCA 1 crawler IA: GPTBot — *Tecnica · sforzo: minuti · +40 punti d'area · indice +16.18* · **QUICK WIN**
      Togli il Disallow che blocca gli agenti che vuoi ti citino. Non basta aggiungere un blocco permissivo in fondo: per ogni agente vale il PRIMO gruppo che lo nomina, quindi la riga va corretta dov'e'.
- [ ] **[CRITICO]** 1 campi di modulo senza etichetta — *Accessibilità · sforzo: giorni · +12 punti d'area · indice +1.62*
      Collega ogni campo a una <label>: un `placeholder` non la sostituisce, perche' sparisce appena si scrive.
- [ ] **[CRITICO]** 1/2 immagini prive di testo alternativo — *Accessibilità · sforzo: giorni · +12 punti d'area · indice +1.62*
      Dai un testo alternativo a ogni immagine che porta informazione, e alt="" a quelle decorative: le due cose sono diverse, e omettere l'attributo non e' nessuna delle due.
- [ ] [AVVISO] 1 blocchi JSON-LD malformati — *Dati Strutturati · sforzo: ore · +10 punti d'area · indice +3.26*
      Correggi la sintassi del blocco: un JSON-LD che non si analizza viene ignorato per intero, non in parte.
- [ ] [AVVISO] CSP mancante — *Sicurezza · sforzo: giorni · +15 punti d'area · indice +2.02*
      Aggiungi Content-Security-Policy. Conviene partire in sola osservazione con -Report-Only e leggere le violazioni prima di applicarla — ma il rilievo resta finche' non passi all'header vero.
- [ ] [AVVISO] 1 salti nella gerarchia degli heading (es. h2 seguito da h4) — *Accessibilità · sforzo: ore · +12 punti d'area · indice +1.62*
      Non saltare i livelli di heading: la gerarchia e' l'indice con cui si naviga una pagina senza vederla. Per rimpicciolire un titolo si usa il CSS.
- [ ] [AVVISO] 1 tabelle dati senza intestazioni <th> — *Accessibilità · sforzo: ore · +12 punti d'area · indice +1.62*
      Usa <th> per le intestazioni delle tabelle di dati, con `scope`: senza, ogni cella viene letta senza sapere di che colonna sia.
- [ ] [AVVISO] X-Frame-Options mancante — *Sicurezza · sforzo: minuti · +10 punti d'area · indice +1.35*
      Impedisci che il sito venga incorniciato da terzi: X-Frame-Options DENY se non deve mai esserlo, SAMEORIGIN se lo incornici tu.

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

- [INFO] Lighthouse non trovato nel PATH

### 3. Lessicale

Nessun rilievo.

### 4. Semantica

- [INFO] Area non calcolata: il modulo e' fallito
  MemoryError: corpus troppo grande

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

- [AVVISO] CSP mancante
  *Correzione:* Aggiungi Content-Security-Policy. Conviene partire in sola osservazione con -Report-Only e leggere le violazioni prima di applicarla — ma il rilievo resta finche' non passi all'header vero.

  ```
  # nginx — prima si osserva
  add_header Content-Security-Policy-Report-Only "default-src 'self'" always;
  # poi, quando le violazioni sono a zero
  add_header Content-Security-Policy "default-src 'self'" always;
  ```
- [AVVISO] X-Frame-Options mancante
  *Correzione:* Impedisci che il sito venga incorniciato da terzi: X-Frame-Options DENY se non deve mai esserlo, SAMEORIGIN se lo incornici tu.

  ```
  # nginx
  add_header X-Frame-Options "SAMEORIGIN" always;
  ```

### 8. Citabilità IA

- [INFO] Mercato 'italia' sconosciuto: uso 'global'
- [INFO] Segnale non misurato: Qualità SEO
- [INFO] Segnale non misurato: Recuperabilità ibrida (consenso RRF)
- [INFO] Segnale non misurato: Contenuto in forma di risposta
- [INFO] Segnale debole: Accessibilità (40/100)
- [INFO] Segnale debole: Accesso e indicizzabilità (57/100)

### 9. Giudizio LLM

- [INFO] Giudizio LLM disattivato (--llm off)

## Profili di citabilità IA

Mercato: global

| Assistente | Indice |
|---|---|
| Claude | 66.6 |
| ChatGPT/Perplexity | 69.5 |
| Qwen | 66.6 |
| Kimi | 66.6 |
| **Indice composito** | **67.9** |

*stime euristiche dichiarate, non comportamento documentato dai vendor*
