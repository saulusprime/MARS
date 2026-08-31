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

    # --- Area 4: lessicale (U13) ----------------------------------------
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

    # --- Area 5: semantica (U13) ----------------------------------------
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

    # --- Area 6: dati strutturati --------------------------------------
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

    # --- Area 7: accessibilita' (i controlli statici) -------------------
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

    # --- Area 8: sicurezza (i tre header del ripiego) -------------------
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

    # --- Area 2: SEO, i controlli di Lighthouse (I18) ------------------
    # Lighthouse porta la DIAGNOSI — la sua `description` finisce in
    # `detail`, i suoi link in `params["references"]` — e non porta la
    # prescrizione. Erano gli unici rilievi di contenuto di MARS ad
    # arrivare a chi legge senza dirgli che cosa fare.
    #
    # Sono i dieci controlli MISURATI della categoria SEO, letti dal
    # `default-config.js` di Lighthouse 13.4.1. L'undicesimo,
    # `structured-data`, resta fuori: pesa 0, Lighthouse lo dichiara
    # manuale e non lo valuta, e i dati strutturati hanno un'area
    # propria (`sd.*`) che prescrive gia' la sua.
    #
    # Le chiavi vengono da `chiave_esterna(id)`, quindi dipendono dagli
    # id di Lighthouse: se una versione futura ne rinomina uno, la voce
    # qui resta inutilizzata e il rilievo torna senza fix — come prima
    # di I18, senza dire nulla di falso.
    "seo.lh.is_crawlable": {
        "fix": "Togli la direttiva che blocca l'indicizzazione, e "
               "cercala in tutti e tre i posti dove puo' stare: il "
               "meta robots della pagina, l'header X-Robots-Tag della "
               "risposta, il Disallow di robots.txt. Toglierla da uno "
               "solo lascia il blocco in piedi.",
        # I tre posti insieme, come per `tech.robots.ai_blocked`: un
        # esempio che ne mostrasse uno farebbe credere di aver
        # corretto mentre il blocco resta altrove.
        "example": "<!-- 1. nella pagina: il meta va TOLTO, non "
                   "negato -->\n"
                   "<meta name=\"robots\" content=\"index, follow\">\n"
                   "\n"
                   "# 2. nella risposta HTTP: l'header non deve esserci\n"
                   "X-Robots-Tag: index, follow\n"
                   "\n"
                   "# 3. in /robots.txt: nessun Disallow su questo "
                   "percorso\n"
                   "User-agent: *\n"
                   "Disallow:",
    },
    "seo.lh.document_title": {
        "fix": "Dai a ogni pagina un <title> che la distingua dalle "
               "altre: e' la riga che l'assistente cita e che l'utente "
               "legge nei risultati. Un titolo uguale su tutto il sito "
               "vale quanto nessun titolo.",
        "example": "<head>\n"
                   "  <title>Drenaggio linfatico manuale — Studio "
                   "Rossi, Bari</title>\n"
                   "</head>",
    },
    "seo.lh.meta_description": {
        "fix": "Scrivi una meta description per pagina che risponda "
               "alla domanda della pagina invece di elencare parole "
               "chiave. E' il testo che compare sotto il titolo nei "
               "risultati, e una sola descrizione ripetuta ovunque non "
               "distingue nulla.",
        "example": "<meta name=\"description\" content=\"Drenaggio "
                   "linfatico manuale a Bari: come funziona una "
                   "seduta, quanto dura e quanto costa.\">",
    },
    "seo.lh.http_status_code": {
        "fix": "Fai rispondere la pagina con 200. Se e' stata "
               "spostata, un 301 verso il nuovo indirizzo; se non "
               "esiste piu', un 410, che dichiara la rimozione "
               "definitiva invece di lasciarla ambigua come fa un 404.",
        "example": "# la pagina esiste\n"
                   "HTTP/1.1 200 OK\n"
                   "\n"
                   "# la pagina si e' spostata\n"
                   "HTTP/1.1 301 Moved Permanently\n"
                   "Location: https://esempio.it/servizi/drenaggio\n"
                   "\n"
                   "# la pagina non tornera'\n"
                   "HTTP/1.1 410 Gone",
    },
    "seo.lh.link_text": {
        "fix": "Sostituisci «clicca qui» e «leggi tutto» con il nome "
               "di cio' che sta dall'altra parte. Il testo del link e' "
               "l'unica descrizione della pagina di destinazione che "
               "si legge dalla pagina di partenza.",
        "example": "<!-- invece di: <a href=\"/prezzi\">clicca "
                   "qui</a> -->\n"
                   "<a href=\"/prezzi\">i prezzi del drenaggio "
                   "linfatico</a>",
    },
    "seo.lh.crawlable_anchors": {
        "fix": "Dai a ogni ancora un href verso l'indirizzo reale. Un "
               "<a> che naviga con onclick, o che ha href=\"#\", non "
               "e' un link per chi non esegue il JavaScript, e la "
               "pagina di destinazione resta irraggiungibile.",
        # Niente apici annidati nell'esempio: la vista HTML lo
        # escapa una volta, e un'entita' scritta a mano uscirebbe
        # letterale.
        "example": "<!-- invece di un <a> che naviga con onclick -->\n"
                   "<a href=\"/prezzi\">Prezzi</a>",
    },
    "seo.lh.robots_txt": {
        "fix": "Correggi la sintassi di robots.txt. Le direttive "
               "valgono solo dentro un gruppo che comincia con "
               "User-agent, e una riga che il parser non riconosce "
               "viene saltata in silenzio. Il rilievo dice che il file "
               "c'e' ma non si legge, non che manca.",
        "example": "# /robots.txt\n"
                   "User-agent: *\n"
                   "Disallow: /area-riservata/\n"
                   "\n"
                   "Sitemap: https://esempio.it/sitemap.xml",
    },
    "seo.lh.image_alt": {
        "fix": "Descrivi in alt che cosa mostra l'immagine, non come "
               "si chiama il file. Le immagini decorative prendono "
               "alt=\"\", vuoto e presente, cosi' chi legge con uno "
               "screen reader non se le sente elencare.",
        "example": "<img src=\"/sala.jpg\" alt=\"Il lettino della "
                   "sala trattamenti\">\n"
                   "<img src=\"/onda.svg\" alt=\"\">"
                   "   <!-- decorativa -->",
    },
    "seo.lh.hreflang": {
        "fix": "Dichiara le versioni linguistiche con un codice valido "
               "e un URL assoluto, e fai in modo che ogni versione "
               "rimandi a tutte le altre e a se stessa: un hreflang "
               "che non torna indietro viene ignorato.",
        "example": "<link rel=\"alternate\" hreflang=\"it\" "
                   "href=\"https://esempio.it/servizi\">\n"
                   "<link rel=\"alternate\" hreflang=\"en\" "
                   "href=\"https://esempio.it/en/services\">\n"
                   "<link rel=\"alternate\" hreflang=\"x-default\" "
                   "href=\"https://esempio.it/servizi\">",
    },
    "seo.lh.canonical": {
        "fix": "Lascia un solo rel=canonical per pagina, con un URL "
               "assoluto che risponda 200 e non sia a sua volta "
               "canonicalizzato altrove. Due canonical in conflitto "
               "valgono come nessuno.",
        "example": "<link rel=\"canonical\" "
                   "href=\"https://esempio.it/servizi/drenaggio\">",
    },

    # --- Area 3: prestazioni (I10) --------------------------------------
    # I titoli e i dettagli sono NOSTRI (mars_perf), quindi anche la
    # prescrizione: la famiglia non e' «dallo strumento» come axe o ZAP.
    "perf.fcp.slow": {
        "fix": "Elimina cio' che blocca il primo render: CSS critico "
               "in linea nel <head>, il resto caricato dopo, e i font "
               "con font-display: swap cosi' il testo compare subito "
               "col carattere di sistema.",
        "example": "@font-face {\n"
                   "  font-family: \"Titillium Web\";\n"
                   "  src: url(\"/font/titillium.woff2\") "
                   "format(\"woff2\");\n"
                   "  font-display: swap;\n"
                   "}",
    },
    "perf.lcp.slow": {
        "fix": "Alleggerisci l'elemento principale della pagina: servi "
               "l'immagine hero compressa e nel formato moderno, "
               "precaricala, e abbatti il tempo di risposta del server "
               "con cache o CDN. E' il singolo intervento che sposta "
               "di piu' i Core Web Vitals.",
        "example": "<link rel=\"preload\" as=\"image\" "
                   "href=\"/img/hero.avif\">\n"
                   "<img src=\"/img/hero.avif\" width=\"1200\" "
                   "height=\"600\"\n"
                   "     alt=\"La sala trattamenti\" "
                   "fetchpriority=\"high\">",
    },
    "perf.tbt.high": {
        "fix": "Spezza i task JavaScript lunghi e rimanda gli script "
               "non essenziali con defer o con un import dinamico: il "
               "thread principale deve restare libero di rispondere "
               "all'input mentre la pagina carica.",
        "example": "<script src=\"/js/analytics.js\" defer></script>\n"
                   "<script type=\"module\">\n"
                   "  addEventListener(\"load\", () => "
                   "import(\"/js/widget.js\"));\n"
                   "</script>",
    },
    "perf.cls.unstable": {
        "fix": "Dichiara larghezza e altezza (o aspect-ratio) su "
               "immagini, video ed embed, e riserva in anticipo lo "
               "spazio di banner e contenuti caricati dopo: il layout "
               "non deve spostarsi sotto gli occhi di chi legge.",
        "example": "<img src=\"/img/team.jpg\" width=\"800\" "
                   "height=\"533\"\n"
                   "     alt=\"Lo studio\">\n"
                   "<div class=\"banner\" style=\"aspect-ratio: 970 / "
                   "250\"></div>",
    },
    "perf.si.slow": {
        "fix": "Fai arrivare prima la parte visibile: markup "
               "essenziale in testa, immagini sotto la piega con "
               "loading lazy, e niente script che ridisegnano la "
               "pagina durante il caricamento.",
        "example": "<img src=\"/img/galleria-1.jpg\" width=\"600\" "
                   "height=\"400\"\n"
                   "     loading=\"lazy\" alt=\"La palestra\">",
    },
}


def prescrivibile(finding: dict) -> bool:
    """Vero se il rilievo descrive un difetto su cui si puo' prescrivere.

    Il discriminante e' la **penalita' dichiarata**, e non la gravita':
    un rilievo `info` puo' essere un difetto vero — `tech.canonical
    .missing` lo e' — mentre un controllo superato non lo e' mai.
    Chiave assente significa "non misurato, o non fallito"; `0.0`
    significa "misurato, ma qui il punteggio non lo muove" ed e' un
    difetto a tutti gli effetti (i controlli statici di `mars_wcag` nel
    ramo axe).

    Serve da I18, che ha dato una prescrizione ai controlli SEO:
    Lighthouse produce un rilievo per OGNI audit, superati e non
    applicabili compresi, e il catalogo cerca per chiave. Senza questa
    porta, sotto «robots.txt e' valido» compariva «Correggi la sintassi
    di robots.txt».
    """
    return "penalty" in (finding.get("params") or {})


def vesti(finding: dict) -> dict:
    """Aggiunge `fix` ed `example` a un rilievo, dove mancano.

    **Il modulo vince, il catalogo colma**: si scrive solo dove il
    rilievo li ha vuoti. E' cio' che permette a `mars_wapt` di
    conservare la `solution` che ZAP gli ha dato, e a un plugin di terzi
    di portare i propri testi senza sapere che questo file esista.

    E colma solo dove c'e' un difetto: vedi `prescrivibile`.

    Lavora sul dict serializzato, non sulla dataclass: e' cio' che
    attraversa il confine dei plugin.
    """
    voce = CATALOGO.get(finding.get("key") or "")
    if not voce or not prescrivibile(finding):
        return finding
    for campo in ("fix", "example"):
        if not finding.get(campo) and voce.get(campo):
            finding[campo] = voce[campo]
    return finding
