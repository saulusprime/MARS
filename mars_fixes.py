#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict

# ======================================================================
# Il catalogo dei testi di correzione (U3.1 / Fase 3 di UPGRADE.md)
# ----------------------------------------------------------------------
# ======================================================================

CATALOGO: Dict[str, Dict[str, str]] = {

    # --- Area 1: tecnica -----------------------------------------------
    "tech.robots.missing": {
        "fix": "Pubblica un robots.txt che dichiari la sitemap: senza, "
               "i crawler procedono per tentativi.",
        "example": "# /robots.txt\n"
                   "User-agent: *\n"
                   "Disallow:\n"
                   "\n"
                   "Sitemap: https://esempio.it/sitemap.xml",
    },
    "tech.robots.ai_blocked": {
        "fix": "Togli il Disallow che blocca gli agenti che vuoi ti "
               "citino. Non basta aggiungere un blocco permissivo in "
               "fondo: per ogni agente vale il PRIMO gruppo che lo "
               "nomina, quindi la riga va corretta dov'e'.",
        # L'esempio mostra la SOSTITUZIONE e non l'aggiunta, ed e' il
        # punto: incollato in coda al robots.txt esistente non
        # chiuderebbe il rilievo — RobotFileParser tiene il primo
        # gruppo trovato per quell'agente — e chi l'ha applicato
        # crederebbe di aver corretto.
        "example": "# robots.txt — il gruppo va CORRETTO, non aggiunto\n"
                   "# prima:\n"
                   "#   User-agent: GPTBot\n"
                   "#   Disallow: /\n"
                   "# dopo:\n"
                   "User-agent: GPTBot\n"
                   "Disallow:",
    },
    "tech.robots.ai_unmentioned": {
        "fix": "Nomina esplicitamente gli agenti IA in robots.txt: oggi "
               "passano per silenzio, e un domani una regola generica "
               "potrebbe escluderli senza che nessuno se ne accorga.",
        "example": "# robots.txt — permesso esplicito\n"
                   "User-agent: GPTBot\n"
                   "Disallow:\n"
                   "\n"
                   "User-agent: ClaudeBot\n"
                   "Disallow:",
    },
    "tech.robots.self_blocked": {
        "fix": "Il robots.txt esclude l'URL da cui parte l'audit: "
               "correggi la regola, o dichiara la proprieta' del "
               "dominio se l'esclusione e' voluta e vuoi analizzarlo "
               "lo stesso.",
    },
    "tech.sitemap.missing": {
        "fix": "Pubblica una sitemap XML e dichiarala nel robots.txt.",
        "example": '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/'
                   'sitemap/0.9">\n'
                   '  <url>\n'
                   '    <loc>https://esempio.it/</loc>\n'
                   '    <lastmod>2026-08-24</lastmod>\n'
                   '  </url>\n'
                   '</urlset>',
    },
    "tech.sitemap.unreadable": {
        "fix": "Controlla che i file di sitemap rispondano 200 e siano "
               "XML valido: una sitemap illeggibile vale come assente.",
    },
    "tech.sitemap.not_in_robots": {
        "fix": "Dichiara la sitemap nel robots.txt: e' il primo posto "
               "in cui un crawler la cerca.",
        "example": "# in fondo al robots.txt\n"
                   "Sitemap: https://esempio.it/sitemap.xml",
    },
    "tech.sitemap.no_lastmod": {
        "fix": "Aggiungi <lastmod> a ogni <url>: e' cio' che dice a un "
               "crawler quali pagine rivisitare.",
        "example": "<url>\n"
                   "  <loc>https://esempio.it/servizi/</loc>\n"
                   "  <lastmod>2026-08-24</lastmod>\n"
                   "</url>",
    },
    "tech.index.noindex": {
        # Non "verifica che sia voluta": e' una domanda, e sotto un
        # rilievo critico e' un invito a non fare nulla.
        "fix": "Togli `noindex` dal meta robots e dall'X-Robots-Tag "
               "sulle pagine che devono essere trovate. Se l'esclusione "
               "e' voluta, quelle pagine non saranno mai citate.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.index.agent_only": {
        # Niente `example`: la forma di ARRIVO dipende da che cosa si
        # voleva ottenere col prefisso, e un esempio inventato sarebbe
        # peggio di nessun esempio (U3.1).
        "fix": "Togli il prefisso per agente se la direttiva deve valere "
               "per tutti i crawler. Se la restrizione e' voluta, gli "
               "assistenti IA non ne sono toccati.",
    },
    "tech.index.unavailable_after": {
        "fix": "Togli `unavailable_after` o porta avanti la data: "
               "quella dichiarata e' passata, e da allora la pagina e' "
               "esclusa dagli indici come da un noindex.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.index.nosnippet": {
        "fix": "Togli `nosnippet` e `max-snippet:0` dalle pagine che "
               "devono essere citate: restano negli indici, ma nessun "
               "assistente puo' riportarne una riga.",
        "example": '<meta name="robots" content="index, follow, '
                   'max-snippet:-1">',
    },
    "tech.index.noarchive": {
        "fix": "Togli `noarchive` se non c'e' una ragione legale o "
               "contrattuale: vieta la copia archiviata, a cui si "
               "attinge quando l'originale e' lento o irraggiungibile.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.index.nofollow": {
        "fix": "Togli `nofollow`: impedisce di seguire i link interni, "
               "quindi il resto del sito resta irraggiungibile da "
               "quella pagina.",
        "example": '<meta name="robots" content="index, follow">',
    },
    "tech.canonical.missing": {
        "fix": "Dichiara <link rel=\"canonical\"> su ogni pagina: senza, "
               "due URL che servono lo stesso contenuto competono fra "
               "loro.",
        "example": '<link rel="canonical" '
                   'href="https://esempio.it/servizi/">',
    },
    "tech.canonical.cross_host": {
        "fix": "Il canonical punta a un altro host: se non e' voluto, "
               "correggilo — stai dichiarando che la versione buona di "
               "questa pagina sta altrove.",
    },

    # --- Area 3: lessicale (U13) ----------------------------------------
    #
    # Le due aree di classifica non hanno un `fix` che si applichi a un
    # tag: i loro difetti sono di CONTENUTO, e la prescrizione dice
    # quale forma dargli. Gli esempi ci sono solo dove esiste un
    # prima/dopo minimo di markup — altrove sarebbero una frase
    # travestita da codice.
    "lex.words.thin": {
        "fix": "Porta le pagine chiave oltre la soglia con contenuto "
               "informativo, non promozionale: BM25 normalizza la "
               "frequenza dei termini sulla lunghezza del documento, e "
               "due paragrafi non arrivano alla frequenza che la "
               "formula premia.",
    },
    "lex.title.dup": {
        "fix": "Dai a ogni pagina un <title> distinto: due pagine con "
               "lo stesso titolo si contendono le stesse query e "
               "nessuna delle due si distingue nell'indice.",
        "example": '// prima — due pagine, un titolo solo\n'
                   '<title>Servizi</title>\n'
                   '<title>Servizi</title>\n'
                   '// dopo\n'
                   '<title>Drenaggio linfatico manuale | Centro '
                   'Esempio</title>\n'
                   '<title>Percorsi post-operatori | Centro '
                   'Esempio</title>',
    },
    "lex.query.no_match": {
        "fix": "Nessun termine della domanda compare nel sito: scrivi "
               "un passaggio che usi le parole con cui la domanda viene "
               "posta, non i sinonimi interni all'azienda.",
    },

    # --- Area 4: semantica (U13) ----------------------------------------
    "sem.chunks.none": {
        "fix": "Le pagine non offrono testo segmentabile in passaggi: "
               "scrivi paragrafi discorsivi sotto intestazioni, perche' "
               "il passaggio e' l'unita' che un motore ibrido cita.",
    },
    "sem.chunks.few": {
        "fix": "Aumenta il numero di passaggi tematici autonomi: ogni "
               "passaggio e' un'occasione distinta di comparire in una "
               "lista di risultati.",
    },
    "sem.answer_shaped.low": {
        "fix": "Dai ai passaggi la forma di una risposta: "
               "l'intestazione pone la domanda, le prime righe la "
               "chiudono. E' il formato che gli assistenti citano piu' "
               "volentieri, perche' e' gia' estraibile da solo.",
        "example": "<h2>Quanto dura una seduta?</h2>\n"
                   "<p>Una seduta dura circa cinquanta minuti, prima "
                   "valutazione compresa.</p>",
    },
    "sem.query.no_match": {
        "fix": "Il recuperatore vettoriale non trova nulla di vicino "
               "alla domanda: manca un passaggio che tratti quel tema, "
               "non una parola chiave da aggiungere.",
    },

    # --- Area 5: dati strutturati --------------------------------------
    "sd.jsonld.missing": {
        # Il fix NON elenca i tipi Schema.org: mars_schema verifica che
        # i blocchi si analizzino, non quali tipi ci siano (I11 aperta).
        # Prescrivere piu' di quanto si misuri e' la falsa precisione
        # che il principio 5 vieta.
        "fix": "Aggiungi un blocco JSON-LD che descriva l'organizzazione "
               "o il servizio: e' la forma che gli assistenti leggono "
               "senza doverla dedurre dal testo.",
        "example": '<script type="application/ld+json">\n'
                   '{"@context": "https://schema.org",\n'
                   ' "@type": "LocalBusiness",\n'
                   ' "name": "Centro Esempio",\n'
                   ' "url": "https://esempio.it/",\n'
                   ' "telephone": "+39 0521 123456",\n'
                   ' "address": {"@type": "PostalAddress",\n'
                   '  "streetAddress": "Via Roma 1",\n'
                   '  "addressLocality": "Parma",\n'
                   '  "postalCode": "43121",\n'
                   '  "addressCountry": "IT"}}\n'
                   '</script>',
    },
    "sd.jsonld.block_malformed": {
        "fix": "Correggi la sintassi del blocco: un JSON-LD che non si "
               "analizza viene ignorato per intero, non in parte.",
        "example": '// prima — la virgola finale rende il blocco invalido\n'
                   '{"@type": "Service",}\n'
                   '// dopo\n'
                   '{"@type": "Service"}',
    },
    "sd.jsonld.block_empty": {
        "fix": "Togli i blocchi <script type=\"application/ld+json\"> "
               "vuoti, o riempili: un blocco vuoto e' rumore per chi "
               "legge la pagina e per chi la analizza.",
    },

    # --- Area 6: accessibilita' (i controlli statici) -------------------
    "wcag.lang.missing": {
        "fix": "Dichiara la lingua sull'elemento <html>: senza, uno "
               "screen reader legge il testo con la pronuncia sbagliata "
               "e un motore non sa in quale lingua indicizzarlo.",
        "example": '<html lang="it">',
    },
    "wcag.img.alt_missing": {
        "fix": "Dai un testo alternativo a ogni immagine che porta "
               "informazione, e alt=\"\" a quelle decorative: le due "
               "cose sono diverse, e omettere l'attributo non e' "
               "nessuna delle due.",
        "example": '<img src="/sala.jpg" alt="La sala trattamenti">\n'
                   '<img src="/onda.svg" alt="">',
    },
    "wcag.form.label_missing": {
        "fix": "Collega ogni campo a una <label>: un `placeholder` non "
               "la sostituisce, perche' sparisce appena si scrive.",
        "example": '<label for="nome">Nome</label>\n'
                   '<input id="nome" name="nome" type="text">',
    },
    "wcag.heading.skip": {
        "fix": "Non saltare i livelli di heading: la gerarchia e' "
               "l'indice con cui si naviga una pagina senza vederla. "
               "Per rimpicciolire un titolo si usa il CSS.",
    },
    "wcag.table.th_missing": {
        "fix": "Usa <th> per le intestazioni delle tabelle di dati, con "
               "`scope`: senza, ogni cella viene letta senza sapere di "
               "che colonna sia.",
        "example": '<table>\n'
                   '  <tr><th scope="col">Trattamento</th>'
                   '<th scope="col">Durata</th></tr>\n'
                   '  <tr><td>Drenaggio</td><td>50 minuti</td></tr>\n'
                   '</table>',
    },
    "wcag.tabindex.positive": {
        "fix": "Togli i tabindex positivi: forzano un ordine di "
               "navigazione diverso da quello visivo. Per rendere "
               "raggiungibile un elemento basta `tabindex=\"0\"`.",
    },
    "wcag.link.generic": {
        "fix": "Scrivi nel link la destinazione, non l'azione: chi "
               "naviga per elenco di link legge solo quel testo, fuori "
               "dal contesto della frase.",
        "example": '<!-- invece di: <a href="/prezzi/">clicca qui</a> -->\n'
                   '<a href="/prezzi/">Il listino dei trattamenti</a>',
    },

    # --- Area 7: sicurezza (i tre header del ripiego) -------------------
    "sec.headers.hsts_missing": {
        # L'avvertenza non e' prudenza formale: HSTS e' irrevocabile per
        # tutta la durata di max-age. Un anno con includeSubDomains su un
        # sito con sottodomini ancora in HTTP li rende irraggiungibili, e
        # nessuna modifica del server lo annulla nei browser che
        # l'hanno gia' visto.
        "fix": "Aggiungi Strict-Transport-Security. Comincia con un "
               "max-age breve e AGGIUNGI includeSubDomains solo dopo "
               "aver verificato che ogni sottodominio risponda in "
               "HTTPS: l'impegno non si puo' revocare prima della "
               "scadenza.",
        "example": "# nginx — un giorno, per cominciare\n"
                   "add_header Strict-Transport-Security "
                   "\"max-age=86400\" always;",
    },
    "sec.headers.csp_missing": {
        # Report-Only NON chiude il rilievo, e il fix deve dirlo: il
        # controllo cerca la chiave esatta "Content-Security-Policy".
        "fix": "Aggiungi Content-Security-Policy. Conviene partire in "
               "sola osservazione con -Report-Only e leggere le "
               "violazioni prima di applicarla — ma il rilievo resta "
               "finche' non passi all'header vero.",
        "example": "# nginx — prima si osserva\n"
                   "add_header Content-Security-Policy-Report-Only "
                   "\"default-src 'self'\" always;\n"
                   "# poi, quando le violazioni sono a zero\n"
                   "add_header Content-Security-Policy "
                   "\"default-src 'self'\" always;",
    },
    "sec.headers.xframe_missing": {
        "fix": "Impedisci che il sito venga incorniciato da terzi: "
               "X-Frame-Options DENY se non deve mai esserlo, "
               "SAMEORIGIN se lo incornici tu.",
        "example": "# nginx\n"
                   "add_header X-Frame-Options \"SAMEORIGIN\" always;",
    },
}


def vesti(finding: dict) -> dict:
    """Aggiunge `fix` ed `example` a un rilievo, dove mancano.

    **Il modulo vince, il catalogo colma**: si scrive solo dove il
    rilievo li ha vuoti. E' cio' che permette a `mars_wapt` di
    conservare la `solution` che ZAP gli ha dato, e a un plugin di terzi
    di portare i propri testi senza sapere che questo file esista.

    Lavora sul dict serializzato, non sulla dataclass: e' cio' che
    attraversa il confine dei plugin.
    """
    voce = CATALOGO.get(finding.get("key") or "")
    if not voce:
        return finding
    for campo in ("fix", "example"):
        if not finding.get(campo) and voce.get(campo):
            finding[campo] = voce[campo]
    return finding
