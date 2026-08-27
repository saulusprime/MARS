MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.

Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT

Versione 2.9.0

Lo script esegue una scansione di un sito (via sitemap o crawling
interno), ne estrae la struttura, e valuta sette aree strategiche.
La sitemap, quando c'e', e' autoritativa: e' la dichiarazione del sito
su cosa vuole far indicizzare, e viene rispettata, salvo l'utente
non si dichiari proprietario e si assume la responsabilita' di non
rispettare robots.txt oppure llms.txt. Si cercano prima le direttive
Sitemap di robots.txt, poi /sitemap.xml, seguendo gli indici
annidati e le sitemap compresse. Senza sitemap si scoprono le pagine
seguendo i link interni sempre con la stessa regola di prima e ci si
ferma dopo aver raggiunto --max-pages. Il referto dichiara con quale
delle due il campione e' stato costruito (sitemap o crawling interno).
Queste sono le aree tematiche su cui il programma effettua l'analisi
e crea il referto:

1. Tecnica          (mars_tech)     indicizzabilita', robots.txt, 
                                    sitemap, crawler IA
                                    (13 crawler IA controllati per
                                    agente: OpenAI, Anthropic,
                                    Perplexity, Common Crawl, Google,
                                    Apple, ByteDance, Amazon, Meta;
                                    meta robots, X-Robots-Tag e
                                    canonical su ogni pagina, con le
                                    direttive rivolte a un solo
                                    agente tenute distinte da quelle
                                    che valgono per tutti;
                                    noindex, nofollow, nosnippet,
                                    noarchive e unavailable_after
                                    scaduto)
2. SEO              (mars_seo)      utilizzando lighthouse: gli
                                    stessi undici controlli della
                                    sezione SEO di Lighthouse, non
                                    il solo punteggio
3. Lessicale        (mars_lexical)  BM25 sui passaggi, piu' i tre
                                    controlli che lo alimentano
                                    (pagine sotto le 300 parole,
                                    title ripetuti fra pagine,
                                    query senza riscontro)
4. Semantica        (mars_semantic) recupero vettoriale sui passaggi,
                                    piu' i tre controlli che lo
                                    nutrono (quanti passaggi, quota
                                    "answer-shaped", query senza
                                    riscontro)
5. Dati strutturati (mars_schema)   JSON-LD / Schema.org
6. Accessibilità    (mars_wcag)     compatibilità WCAG
7. Sicurezza        (mars_wapt)     test WAPT di superficie

Vi è poi una analisi generale di "superficie" che guarda al sito
analizzato concentrandosi su tutte le singole aree specifiche e cerca
di rispondere ad una domanda che nessuna area specifica pone: quanto
c'e' da recuperare, e come ci si arriva, ovvero la fotografia attuale
con la valutazione e la remediation con esempi per aiutare a migliorare
il punteggio. L'analisi generale di superficie guarda anche:
  - la **distribuzione di profondita'**, cioe' quanti click dalla home
    servono per raggiungere ogni pagina. Le pagine che vengono dalla
    sola sitemap hanno profondita' IGNOTA: sono dichiarate dal sito 
    ma nessuno le ha raggiunte seguendo i link;
  - la **treemap della superficie**: un rettangolo per pagina, area
    proporzionale alle parole recuperabili. Si legge a colpo d'occhio
    un sito che ha tutto il testo in una pagina sola. Il colore e' la
    gravita' peggiore dei rilievi che citano quella pagina; il grigio
    e' «nessun rilievo la cita», che NON vuol dire «a posto» — non
    tutte le aree guardano tutte le pagine, Lighthouse ne misura una
    sola e axe le prime del campione. Il colore non viaggia mai da
    solo: il titolo del rettangolo e la tabella lo dicono a parole;
  - il **grafo dei link interni**: chi linka chi fra le pagine viste,
    con i nodi grandi quanto i link che ricevono e le pagine che dalla
    home non si raggiungono per link marcate come tali;
  - la **matematica della superficie**: quanti passaggi recuperabili
    ci sono e quanti ce ne sarebbero con pagine di contenuto
    sostanziale. E' una PROIEZIONE dichiarata, non una misura, e
    l'assunzione (circa 900 parole per pagina, da cui il chunker
    ricava quattro passaggi);

In piu' esegue una **simulazione RRF**: costruisce due recuperatori
indipendenti (uno lessicale Okapi BM25, uno vettoriale) sui chunk del
sito, li fonde con la formula del Reciprocal Rank Fusion

    score(d) = somma su ogni lista di  1 / (k + rank_i(d))

e misura il *consenso*, cioe' quante volte lo stesso chunk compare in
alto in entrambe le liste. E' esattamente la logica con cui i motori
di ricerca ibridi e le pipeline RAG selezionano i passaggi da citare.

Dai punteggi di area deriva i **profili di citabilita'** per
assistente IA (Claude, ChatGPT/Perplexity, Qwen, Kimi) con indice
composito pesato per mercato (--market): stime euristiche
dichiarate, non comportamento documentato dai vendor.

I mercati riconosciuti sono global (predefinito), eu, us, cn; un
valore diverso ricade su global e lo dichiara nel referto. Il mercato
agisce su due piani: quanto ciascun assistente conta in quell'area
geografica, e — dove esiste una ragione concreta — un moltiplicatore
sui segnali. L'unico oggi attivo e' l'accessibilita' per il mercato
eu, per via dell'European Accessibility Act.

La matrice dei pesi sta in chiaro in testa a mars_citability.py, con
la motivazione di ogni riga. E' fatta per essere discussa e corretta:
Qwen e Kimi hanno pesi identici perche' non ci sono basi pubbliche per
differenziarli, e inventare una differenza sarebbe falsa precisione.

Il profilo si ottiene con l'audit completo (CLI, oppure POST
/audit/full), perche' e' una sintesi dei punteggi delle altre aree.
Per MISURARE le citazioni reali invece di stimarle c'e'
mars_citations.py.

Implementato nativamente le parti algoritmiche più complesse
(il crawler, il retriever lessicale BM25, il proxy vettoriale TF-IDF
sui caratteri, la fusione RRF, e i due layout del referto: squarified
alla Bruls-Huizing-van Wijk per la treemap, a forze alla
Fruchterman-Reingold per il grafo dei link — entrambi deterministici,
cosi' che lo stesso sito dia sempre lo stesso disegno)

Lighthouse (SEO): Lo script cerca il comando lighthouse nel PATH.
Per attivarlo devi avere Node.js e Lighthouse installati globalmente
(npm install -g lighthouse). Senza, l'area risulta "non misurato" —
non zero. Opzionale installa la libreria corepack
(npm install -g corepack)

Il referto riporta i singoli controlli della categoria SEO cosi' come
li elenca Lighthouse — indicizzabilita', title, meta description, stato
HTTP, testo dei link, link scansionabili, robots.txt, testi alternativi,
hreflang, canonical e i dati strutturati da verificare a mano — con gli
elementi incriminati di ciascuno, superati compresi: un punteggio pieno
deve potersi distinguere da un controllo che non e' stato eseguito. I
titoli arrivano da Lighthouse stesso, nella lingua del referto
(--locale), non da una nostra traduzione.

Il referto dichiara sempre versione di Lighthouse e tipo di dispositivo
(oggi mobile, il predefinito dello strumento): un referto mobile e uno
desktop non sono confrontabili.

WCAG: se Playwright e axe-core sono disponibili, l'accessibilita' viene
misurata con axe-core su Chromium, limitato alle regole WCAG 2.1 livelli
A e AA. Serve un browser reale: criteri come il contrasto colore
dipendono dal CSS applicato, e valutarli sull'HTML grezzo darebbe
risultati sbagliati, che e' peggio che non darli. Per attivarlo:

    pip install -r requirements-optional.txt
    python -m playwright install chromium
    npm install axe-core     (oppure e' gia' in node_modules)

I testi delle regole axe — il titolo del rilievo e la sua correzione —
vengono dal file di locale che axe-core porta nel proprio pacchetto npm,
scelto secondo --lang. Per l'inglese non ce n'e' uno e non serve: axe
manda i suoi testi in inglese dentro la risposta. Una regola che il
locale non conosce (axe.configure ne permette di aggiunte a mano) resta
nella lingua di axe, e il referto lo dichiara.

Il browser e' lento, quindi axe gira sulle prime pagine del campione e
il referto dichiara quante ne ha viste. Senza Playwright o axe-core si
usa l'euristica statica sul markup — lang, testi alternativi, gerarchia
degli heading, etichette dei campi, intestazioni di tabella, testi di
link generici, tabindex positivi — che copre tutte le pagine ma non i
criteri che richiedono rendering. Il referto dichiara sempre quale dei
due percorsi ha prodotto il punteggio.

WAPT: se un daemon ZAP e' raggiungibile, la sicurezza viene misurata
con una scansione reale. MARS parla direttamente l'API JSON di ZAP: il
client ufficiale python-owasp-zap-v2.4 non e' utilizzabile perche'
cabla l'indirizzo "http://zap/" e ZAP 2.17 non serve piu' quell'alias
attraverso il proxy. Non serve alcun pacchetto pip, solo il daemon.

    ATTENZIONE. L'active scan invia payload d'attacco (XSS, SQL
    injection, path traversal). Contro un sito che non si possiede e'
    un attacco e, a seconda della giurisdizione, un reato. Per questo
    l'active scan richiede --i-own-this-domain, la stessa dichiarazione
    di proprieta' che permette di ignorare robots.txt.

    Anche lo SPIDER di ZAP richiede la stessa dichiarazione, e dal
    2026-08-27: e' un secondo crawler, e robots.txt non lo rispetta.
    Misurato su ZAP 2.17.0 — richiede gli URL vietati, e usa le voci
    Disallow come semi da cui partire, quindi robots.txt lo fa
    scansionare di piu' proprio dove il sito chiede di non andare.
    Un'opzione per obbedire non esiste.

    Senza dichiarazione si raccolgono gli alert PASSIVI — header
    mancanti, informazioni divulgate, cookie senza attributi: utili e
    innocui — sulle sole pagine che il crawler ha gia' scaricato, che
    sono conformi a robots.txt per costruzione. Il perimetro e' quindi
    esatto e il referto lo dichiara, insieme a quale delle due
    scansioni ha girato. Misurato su un sito di prova: rispetto allo
    spider si conservano 4 regole distinte su 5, senza una sola
    richiesta in piu' verso il sito.

    CON la dichiarazione il perimetro NON e' piu' il campione, e MARS
    non lo conosce: lo spider percorre il sito per conto suo e
    --max-pages non lo vincola. Il referto lo DICHIARA invece di
    tacerlo, con i due limiti che agiscono davvero — il tetto per
    pagina che passi tu (--max-children) e il MaxDepth che il tuo
    daemon ha in configurazione, letto da ZAP e non supposto.

    --max-children e' l'unico tetto che l'API dello spider accetta, e
    NON e' un numero di pagine: limita i link seguiti per pagina.
    Misurato su un indice con otto figli — con 0 (predefinito, il
    default di ZAP) ZAP ha percorso tutte e otto le pagine, con 2 ne ha
    percorsa UNA, perche' robots.txt e sitemap.xml contano anch'essi
    come figli. Serve a contenere una scansione, non a renderla
    esatta: esatta non puo' essere, e il referto lo dice.

MARS si collega a un daemon GIA' in esecuzione e non lo avvia:
orchestrare un processo Java dal codice significa rischiare di
lasciarlo orfano dopo un timeout, e delegarlo a chi lancia l'audit e'
piu' semplice e piu' onesto. Il modo piu' rapido:

    docker run -u zap -p 8080:8080 zaproxy/zap-stable zap.sh -daemon \
        -host 0.0.0.0 -port 8080 -config api.disablekey=true

Indirizzo e chiave si configurano con ZAP_PROXY (predefinito
http://127.0.0.1:8080) e ZAP_API_KEY. Senza daemon si ripiega sul
controllo degli header HTTP, che NON e' un WAPT e viene dichiarato come
controllo di superficie. Se la scansione va in timeout, i rilievi
parziali vengono riportati come tali.

Un daemon ZAP eleva molto il valore dell'audit di sicurezza: si passa da un
controllo degli header a una scansione vera delle pagine analizzate, e con la
dichiarazione di proprieta' anche allo spidering e all'active scan delle
vulnerabilita' comuni — XSS, SQLi, path traversal. Oltre al Docker qui sopra si puo' installare il pacchetto di
sistema: `sudo snap install zaproxy --classic`, poi avviarlo in modalita'
daemon.

    NON serve alcun pacchetto pip. MARS parla direttamente l'API JSON di ZAP
    con `requests`, che e' gia' una dipendenza: ne' `zapcli` ne' il client
    ufficiale `python-owasp-zap-v2.4` sono richiesti o supportati — il secondo
    cabla l'indirizzo "http://zap/", che ZAP 2.17 non serve piu' attraverso il
    proxy. Chi trova altrove istruzioni per installarli, e per disinstallare
    urllib3/requests/six come loro prerequisito, sta leggendo indicazioni
    stantie: qui non servono, e quel blocco di comandi su un Python di sistema
    puo' rompere strumenti del sistema operativo.

Sentence Transformers: Se installi il pacchetto (pip install torch 
torchvision torchaudio sentence-transformers numpy), lo script 
caricherà automaticamente il modello multilingue di default per generare 
embedding reali (paraphrase-multilingual-MiniLM-L12-v2) invece del 
proxy Char-TFIDF (che usa i n-grammi sui caratteri).

Per il monitoraggio delle citazioni IA e per il giudizio LLM sulla
citabilità installare la libreria Anthropic (e' in
requirements-optional.txt).

Il giudizio LLM (mars_llm_judge) sottopone al modello i passaggi piu'
recuperabili secondo la fusione RRF — non le prime pagine del sito — e
ne chiede una valutazione di citabilita' in JSON validato. E' l'unico
modulo che comporta una spesa, quindi il controllo e' esplicito:

    --llm auto   (predefinito) esegue solo se ANTHROPIC_API_KEY e'
                 presente; altrimenti lo dichiara e prosegue
    --llm on     tenta comunque, cosi' da usare anche un profilo
                 'ant auth login' che la variabile d'ambiente non mostra
    --llm off    non lo esegue mai

Via API il campo equivalente e' "llm". Prima di inviare, il modulo
stampa quanti passaggi e quanti token stimati partiranno: la stima e'
grossolana (un token ogni quattro caratteri) e serve a dare un ordine
di grandezza, non a prevedere la fattura. Al massimo vengono inviati 8
passaggi da 1200 caratteri.

L'annuncio compare SOLO se qualcosa partira' davvero: con --llm on e
nessuna credenziale risolvibile — ne' chiave, ne' token, ne' profilo
'ant auth login' — il referto dice «Nessuna credenziale Anthropic
utilizzabile» e non annuncia alcun invio. Fino al 2026-08-27 lo
annunciava lo stesso (R58).

Installazione. Le dipendenze sono divise per ruolo:

    pip install -r requirements.txt            # CLI e API: sempre
    pip install -r requirements-optional.txt   # embedding reali, ZAP, Anthropic
    pip install -r requirements-dev.txt        # pytest, flake8

I test si lanciano con `pytest` dalla radice del progetto: girano in
meno di dieci secondi, non toccano la rete e non avviano Lighthouse,
ZAP o un browser. Non possono nemmeno spendere: l'unica area che
chiama un'API a pagamento e' bloccata al livello del transport HTTP,
e un test che ci provasse fallirebbe dicendolo.

Golden del referto. tests/golden/ contiene la resa attesa dei tre
formati su due referti sintetici: uno con ogni strumento a
disposizione, uno con Lighthouse, ZAP e axe assenti e un'area caduta.
Sei file, che qualunque cambiamento di resa fa fallire con un diff.

Congelano la PIPELINE, non i soli renderer: i risultati d'area
vengono dai moduli veri, quindi anche un punteggio che cambia li fa
fallire. E' voluto, ed e' il motivo per cui la rigenerazione non e'
il rimedio ma il primo dei due passi:

    MARS_RIGENERA_GOLDEN=1 pytest tests/test_golden.py
    git diff tests/golden/          # il passo che non si salta

E' li' che si distingue una resa cambiata da una misura cambiata. I
test rigenerati escono "skipped", non "passed": la variabile serve a
rigenerare, non a far tornare il verde, e non va impostata in CI.

Due cose cambiano il golden HTML senza che nessuno abbia toccato un
renderer: favicon.ico, incorporata come data URI (nel golden compare
come digest, cosi' il diff resta leggibile), e il CSS. Sono resa
entrambe, ed e' giusto che il diff le mostri.

requirements.txt copre sia l'audit da riga di comando sia l'API REST.
Servizi utilizzati dall'API:
- FastAPI: Il framework web.
- Uvicorn: Il server ASGI per eseguirlo.
- python-jose: Per la gestione dei token JWT.
- passlib: Per l'hashing sicuro delle password.

Nota su bcrypt: e' pinnato a 4.0.1 di proposito. passlib 1.7.4 non sa
leggere la versione di bcrypt >= 4.1 e solleva AttributeError, il che
rende impossibile ogni login. Non alzare il vincolo senza aver prima
verificato che passlib sia stato aggiornato.

API REST (mars_api.py)
----------------------

Le stesse sette aree di audit sono esposte via HTTP. CLI e API
condividono gli stessi moduli e la stessa costruzione del contesto:
sono due interfacce sopra il medesimo motore, non due implementazioni.

Avvio:

    export MARS_SECRET_KEY="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
    uvicorn mars_api:app --host 127.0.0.1 --port 8555

MARS_SECRET_KEY firma i token JWT. Se non e' impostata il server parte
comunque, ma genera una chiave effimera e lo dichiara: i token smettono
di valere a ogni riavvio. E' un ripiego per lo sviluppo, non per la
produzione.

Se la porta 8000 e' gia' occupata uvicorn esce con "address already in
use": usare --port 8010 o un'altra libera. Vale la pena controllare il
log all'avvio, perche' un server che non si e' agganciato lascia
rispondere qualunque altra applicazione stia su quella porta, e le
risposte sembrano provenire da MARS.

Documentazione interattiva su http://127.0.0.1:8555/docs (Swagger UI);
la radice / vi reindirizza con un 307. La specifica OpenAPI vera e'
generata da FastAPI su /openapi.json.

Autenticazione. Tutti gli endpoint di audit richiedono un token JWT
(OAuth2 password flow). Credenziali predefinite: admin / mars2026 —
da cambiare prima di qualunque uso reale.

    # 1. ottenere il token
    TOKEN=$(curl -s -X POST http://127.0.0.1:8555/token \
        -d "username=admin&password=mars2026" | python3 -c \
        "import sys,json;print(json.load(sys.stdin)['access_token'])")

    # 2. usarlo
    curl -s -X POST http://127.0.0.1:8555/audit/full \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"url":"https://example.com","max_pages":10}'

Endpoint:

    POST /token           rilascia il token JWT (scade in 30 minuti)
    GET  /users/me        utente autenticato (senza credenziali)

    POST /audit/tech      area 1  indicizzabilita', robots.txt, crawler IA
    POST /audit/seo       area 2  Lighthouse
    POST /audit/lexical   area 3  BM25 sui chunk
    POST /audit/semantic  area 4  chunk answer-shaped, recupero vettoriale
    POST /audit/schema    area 5  JSON-LD / Schema.org
    POST /audit/wcag      area 6  accessibilita'
    POST /audit/wapt      area 7  sicurezza
    POST /audit/full      tutte e sette piu' la fusione RRF

Un corpo di esempio completo sta in examples/audit_request.json.

Corpo della richiesta (AuditRequest), tutti i campi opzionali tranne url:

    url                 URL del sito da scansionare
    max_pages           numero massimo di pagine (default 10)
    embeddings          modello SentenceTransformer, o "none" per il
                        proxy char-tfidf (default: modello multilingue)
    market              mercato di riferimento per la citabilita' IA
    delay               pausa fra le richieste in secondi (default 0.5)
    timeout             timeout di rete in secondi (default 10)
    queries             elenco di query per la simulazione RRF; senza,
                        si usano quattro query generiche nella lingua
                        prevalente del sito. L'API non applica il tetto
                        di 15 query della CLI: le usa tutte
    llm                 "auto" (default), "on" oppure "off": governa il
                        solo modulo che comporta una spesa
    max_children        tetto ai link seguiti PER PAGINA dallo spider
                        ZAP, che gira solo con i_own_this_domain. 0
                        (default) e' il default di ZAP: nessun tetto.
                        Non e' un numero di pagine
    i_own_this_domain   DICHIARAZIONE di proprieta' del dominio e di
                        assunzione di responsabilita'. Abilita TRE cose:
                        ignorare robots.txt, lo spider ZAP — che
                        robots.txt non lo rispetta — e l'active scan
                        WAPT, che invia payload d'attacco. Registrata
                        nel referto. Default false.
    credentials         Credenziali per gli strumenti opzionali, se non
                        si vogliono impostare come variabili d'ambiente
                        sul server (vedi sotto).

Nessun campo "lang". Gli endpoint restituiscono tutti il dato canonico e
nessuno rende prosa, quindi una lingua nel corpo della richiesta sarebbe
configurazione che non configura nulla. La traduzione la fa chi consuma il
JSON, che ha `key` e `params` su ogni rilievo. Il giorno che l'API esporra'
una resa HTML o testuale, il campo nascera' con lei.

Credenziali nella richiesta. Il campo "credentials" accetta:

    anthropic_api_key   abilita il giudizio LLM (area 9)
    hf_token            token Hugging Face, necessario SOLO per modelli
                        di embedding ad accesso limitato o privati; per
                        quelli pubblici, incluso il predefinito, non
                        serve. Da riga di comando basta la variabile
                        d'ambiente HF_TOKEN, che huggingface_hub legge
                        da se'
    zap_api_key         chiave del daemon ZAP, se non e' stato avviato
                        con api.disablekey=true
    zap_proxy           indirizzo del daemon ZAP, se diverso da
                        http://127.0.0.1:8080

Servono quando una sola istanza dell'API serve chiamanti diversi, che
portano le proprie chiavi. Se il campo manca si usano le variabili
d'ambiente del server, che restano il modo consigliato per un'istanza a
uso singolo.

    ATTENZIONE. Nel corpo di una richiesta le chiavi viaggiano fino al
    server: usare SOLO su HTTPS. Nello schema OpenAPI sono dichiarate
    format: password e writeOnly, quindi Swagger le maschera e nessuna
    risposta le restituisce mai. E non vanno scritte in
    examples/audit_request.json, che e' versionato in git: quel file
    contiene segnaposto, e cosi' deve restare.

    Le chiavi di mars_citations.py (PERPLEXITY_API_KEY, OPENAI_API_KEY,
    ANTHROPIC_API_KEY) restano solo su variabili d'ambiente: e' uno
    strumento da riga di comando, non esposto via API.

Un punteggio a null con "status": "unavailable" significa che l'area
non e' stata misurata perche' lo strumento necessario manca — non che
il sito abbia preso zero. Sono cose diverse e il referto le distingue.

Codici di risposta: 200 esito; 401 token assente, scaduto o non valido;
404 sito irraggiungibile o modulo di audit non presente sul filesystem;
422 corpo della richiesta non valido.


Riferimenti (fonti aperte e ufficiali):
  - Cormack, Clarke, Buettcher (2009), "Reciprocal Rank Fusion
    outperforms Condorcet and individual Rank Learning Methods",
    SIGIR '09.
  - Microsoft Learn, "Hybrid search scoring (RRF) - Azure AI Search":
    https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
  - Elastic, "Reciprocal rank fusion":
    https://www.elastic.co/docs/reference/elasticsearch/rest-apis/
    reciprocal-rank-fusion
  - OpenSearch, "Introducing reciprocal rank fusion for hybrid search":
    https://opensearch.org/blog/introducing-reciprocal-rank-fusion-
    hybrid-search/
  - Robertson & Zaragoza (2009), "The Probabilistic Relevance
    Framework: BM25 and Beyond".
  - Schema.org, https://schema.org/

Se sentence-transformers e' installato gli embedding reali si
attivano da soli con un modello multilingue predefinito; --embeddings
sceglie un modello diverso, --embeddings none forza il proxy
char-tfidf.

Uso:
    python3 mars_audit.py https://www.example.com
    python3 mars_audit.py https://example.com --max-pages 40 \\
        --format html --output report.html
    python3 mars_audit.py https://example.com --queries q.txt \\
        --embeddings sentence-transformers/all-MiniLM-L6-v2
    python3 mars_audit.py https://example.com --lang en \\
        --format html --output report-en.html
    python3 mars_audit.py https://example.com \\
        --credentials chiavi.local.json --llm on

Chiavi degli strumenti opzionali (--credentials FILE). Senza il flag
valgono le variabili d'ambiente, e MARS non legge i file .env: senza
python-dotenv chiamato da qualcuno, un .env non ha alcun effetto, e una
variabile assegnata senza `export` non e' visibile al processo. E' il
modo piu' comune di credere di aver passato una chiave senza averlo
fatto — il referto in quel caso dice «Nessuna credenziale Anthropic
utilizzabile», che e' diverso da «Errore API Anthropic», il messaggio
di una chiave presente e rifiutata.

Il file e' JSON e accetta due forme: il solo blocco delle credenziali,
oppure il corpo di richiesta dell'API, di cui si legge `credentials`.
Si ottiene copiando examples/audit_request.json:

    cp examples/audit_request.json chiavi.local.json
    $EDITOR chiavi.local.json          # solo il blocco credentials
    chmod 600 chiavi.local.json        # *.local.json e' ignorato da git

Un FILE e non un valore sul flag, e la ragione e' misurata: su Linux
/proc/<pid>/cmdline e' leggibile da ogni utente locale a meno di
hidepid, quindi una chiave passata come argomento resta visibile in ps
per tutta la durata dell'audit e finisce integra nella cronologia della
shell. Nel file ci finisce il percorso.

Il file si legge in modo severo, e per una ragione sola: un file
passato e ignorato in silenzio fa credere di aver misurato con la
propria chiave. Un file assente, illeggibile, non JSON, senza alcuna
credenziale nota o con un valore che non e' una stringa **ferma
l'audit** con codice 2; una chiave scritta male — antropic_api_key
senza la h — viene nominata; un file leggibile da altri utenti produce
un avviso. Nessun messaggio contiene mai il valore di una chiave.

Query della simulazione RRF (--queries FILE, una per riga, UTF-8).
Senza il flag si usano quattro query generiche nella lingua prevalente
del sito, rilevata dall'attributo lang: interrogare un sito inglese in
italiano produrrebbe un consenso basso che non dice nulla sul sito, ma
solo che le domande erano nella lingua sbagliata.

Del file si leggono al massimo le **prime 15 query**
(`DEFAULT_MAX_QUERIES`), e il tetto non e' regolabile da riga di comando:
ogni query fa girare due recuperatori sull'intero corpus, quindi il costo
cresce con esse. Via API il campo `queries` **non** ha questo tetto — chi
chiama l'API sa quante ne sta mandando.

Le query generiche sono un punto di partenza dichiarato, non un
riferimento: le query che contano sono quelle del dominio. Su un sito
di documentazione tecnica, per esempio, "come funziona la fusione
reciproca dei ranghi" produce un consenso 3/3 dove "chi siamo" si ferma
a 2/3 — ed e' la differenza fra misurare il sito e misurare la
genericita' della domanda.

Il referto riporta il consenso di ogni query e un consenso aggregato,
ottenuto fondendo con l'RRF le classifiche di tutte le query. Quello
aggregato e' la misura piu' solida: un passaggio che sale in alto per
entrambi i recuperatori su piu' domande e' recuperabile davvero, mentre
un consenso su una sola domanda puo' essere un caso.

Formati del referto (--format, predefinito text):

    text      il referto a video, come sopra
    json      la struttura canonica: le altre viste ne sono derivate, e
              l'API restituisce gli stessi campi su POST /audit/full
    html      pagina autoconsistente — CSS incorporato, favicon inclusa,
              nessuna origine esterna — con tema chiaro e scuro
    markdown  da incollare in una issue o in un wiki: il piano di
              interventi e' una task list GFM, quindi si spunta, e la
              gravita' e' un marcatore testuale e non un colore
    csv       una riga per rilievo, con punto e virgola e BOM UTF-8: si
              apre in Excel o Fogli con gli accenti giusti e le colonne
              separate. Due colonne dicono cose diverse e vanno lette
              come tali: `pagine` sono le pagine del sito su cui il
              rilievo e' scattato, `riferimento` e' il link alla
              documentazione della regola dello strumento (axe)

Lingua del referto (--lang, predefinito it). Due lingue: **it** ed **en**.
E' un livello dichiaratamente inferiore al riferimento a cinque lingue, e la
ragione sta in testa a mars_i18n.py con la misura che l'ha motivata — dei
cataloghi del progetto di riferimento coincidono 4 chiavi su 49, perche' non
ha una sola chiave per le aree accessibilita', sicurezza e SEO. Le traduzioni
si scrivono, e quattro lingue che nessuno qui puo' verificare sarebbero
quattro lingue di qualita' non misurata.

--lang non e' solo una scelta di resa: e' anche la lingua che si chiede agli
strumenti esterni, perche' i loro testi nascono al momento della misura.
Lighthouse la riceve come --locale, axe-core sceglie di conseguenza il file
di locale del proprio pacchetto npm, ZAP parla inglese e basta. Il referto
dichiara in testa quali strumenti hanno scritto in un'altra lingua, e lo fa
anche in italiano: un referto che tacesse l'inglese di ZAP lascerebbe credere
a una dimenticanza cio' che e' un limite dello strumento.

Cio' che nessuna lingua puo' tradurre resta com'e', e il referto lo dice: le
evidenze citate dal sito analizzato (un titolo mancante, il testo di un link
generico) e la prosa del giudizio LLM, che e' scritta dal modello. Le aree
lessicale e semantica erano nell'elenco finche' non producevano rilievi
strutturati; da U13 li producono, quindi si traducono come le altre.

Il JSON e' **canonico e resta in italiano** per tutto cio' che scrive MARS,
in ogni lingua: e' il dato da cui le altre viste derivano, e due JSON diversi
per lingua sarebbero due dati canonici. Chi lo consuma da un programma ha
`key` e `params` su ogni rilievo e traduce da se'. Fanno eccezione — e non
poteva essere altrimenti — i testi che vengono da axe, ZAP e Lighthouse:
quelli nascono nella lingua con cui l'audit ha girato, e ogni rilievo la
dichiara in `params["text_lang"]`.

Il JSON dichiara la versione del proprio schema in `schema_version`, che è
cosa diversa dalla versione del programma: sale **solo** su un cambiamento
incompatibile — una chiave rimossa, rinominata, o il cui significato cambia —
mentre le aggiunte sono additive e non la muovono. Chi consuma il referto da
un programma legge quella, non `version`. È a **3**.

La **2** ha rinominato `url` in `doc_url` su ogni rilievo, che è sempre stato
il link alla documentazione della regola e mai la pagina analizzata. La **3**
ha allargato il significato di `audits[].manual` nell'area SEO: portava due
dei quattro modi in cui Lighthouse dichiara di non aver misurato, e gli altri
due finivano nelle classi sbagliate — un `informative` fra i controlli
superati, un `error` fra i falliti, cioè un guasto dello strumento contato
come difetto del sito. Ora porta tutti e quattro. Il nome è rimasto: non ha
mai significato «da fare a mano» — `notApplicable` c'è sempre stato — e
cambiarlo sarebbe stato un secondo cambiamento incompatibile per un guadagno
di sola lettura. Le pagine di un
rilievo stanno in `params["urls"]`, ed è una lista perché un rilievo è un
CONTROLLO e non un'occorrenza — lo stesso difetto su venti pagine resta un
rilievo solo, altrimenti la penalità si moltiplicherebbe per venti. Accanto ci sono i parametri che
rendono il referto riproducibile: `rrf` con il k della fusione e la formula,
e `thresholds`, oggi `null` perché le soglie non sono configurabili — due
referti con soglie diverse non sarebbero confrontabili alla pari, e la chiave
c'è da subito perché il giorno che lo diventeranno nessuno debba distinguere
«assente perché vecchio» da «assente perché di serie».

Con --history il referto guadagna la sezione «rispetto all'esecuzione
precedente»: una riga compatta per esecuzione in un file JSONL append-only,
e il confronto dei rilievi per **chiave stabile** — cosi' un conteggio che
cambia nel titolo non fa sembrare un difetto risolto e uno nuovo. Alla prima
esecuzione non c'e' nulla da confrontare e la sezione non compare;
--no-history disattiva lettura e scrittura.

Con --output il referto va su file invece che a video. Il referto JSON
si dà in pasto a mars_citations.py --from-audit, che ne riusa le stesse
query della simulazione RRF: cosi' stima e misura della citabilita'
guardano le stesse domande.

Codici di uscita di mars_audit.py: 0 referto prodotto; 2 nessuna pagina
indicizzata **oppure** errore d'uso (argomento non valido, file di --queries
illeggibile); 3 impossibile scrivere il file di --output. Il valore 1 resta
libero per una futura soglia --fail-under.

Monitoraggio delle citazioni IA effettive di un sito.

Interroga i principali assistenti IA con ricerca web sulle query
target del sito e verifica se il sito (ed eventuali concorrenti)
viene citato nelle risposte. Pensato per esecuzioni periodiche
(cron/systemd timer): ogni esecuzione puo' essere accodata a uno
storico JSONL e confrontata con la precedente.

Provider supportati:
  - anthropic   Claude (SDK ufficiale, strumento web_search).
                Richiede: pip install anthropic e ANTHROPIC_API_KEY
                (o un profilo `ant auth login`).
  - perplexity  Perplexity Sonar. Richiede PERPLEXITY_API_KEY.
  - openai      ChatGPT via Responses API con web_search.
                Richiede OPENAI_API_KEY.

Le chiavi API si passano SOLO via variabili d'ambiente, mai da
riga di comando.

Uso:
    python3 mars_citations.py https://miosito.it --queries q.txt
    python3 mars_citations.py https://miosito.it \\
        --from-audit referto.json --provider anthropic \\
        --competitor concorrente.it --history storico.jsonl \\
        --fail-under 30

Codici di uscita: 0 ok; 1 tasso di citazione sotto --fail-under;
2 errore d'uso o provider non configurato; 3 impossibile scrivere il file
di --output. Un percorso di --history non scrivibile non e' fatale: lo
storico e' un archivio, il referto viene stampato lo stesso e il guasto
dichiarato su stderr.

Il campo `rate` di un provider e' `null`, non 0.0, quando nessuna query ha
ottenuto risposta: non e' stato misurato nulla, e uno 0% inventato sarebbe
indistinguibile da uno 0% vero. Vale nel JSON e nella riga di storico; le
righe scritte prima della versione 1.2.1 portano ancora 0.0.

Licenza: Apache 2.0