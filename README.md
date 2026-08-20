MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.

Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT

Lo script esegue una scansione di un sito (via sitemap o crawling
interno), ne estrae la struttura, e valuta sette aree strategiche:

La sitemap, quando c'e', e' autoritativa: e' la dichiarazione del sito
su cosa vuole far indicizzare, e viene rispettata. Si cercano prima le
direttive Sitemap: di robots.txt, poi /sitemap.xml, seguendo gli indici
annidati e le sitemap compresse. Senza sitemap si scoprono le pagine
seguendo i link interni in ampiezza, con le stesse regole: robots.txt
rispettato, solo stesso host, URL normalizzati, e stop a --max-pages.
Il referto dichiara con quale delle due il campione e' stato costruito.

1. Tecnica          (mars_tech)     indicizzabilita', robots.txt, 
                                    sitemap, crawler IA
                                    (13 crawler IA controllati per
                                    agente: OpenAI, Anthropic,
                                    Perplexity, Common Crawl, Google,
                                    Apple, ByteDance, Amazon, Meta;
                                    meta robots, X-Robots-Tag e
                                    canonical su ogni pagina)
2. SEO              (mars_seo)      utilizzando lighthouse: gli
                                    stessi undici controlli della
                                    sezione SEO di Lighthouse, non
                                    il solo punteggio
3. Lessicale        (mars_lexical)  segnali di tipo BM25 (title, 
                                    heading, termini)
4. Semantica        (mars_semantic) chunk autoconsistenti, contenuto 
                                    "answer-shaped"
5. Dati strutturati (mars_schema)   JSON-LD / Schema.org
6. Accessibilità    (mars_wcag)     compatibilità WCAG
7. Sicurezza        (mars_wapt)     test WAPT di superficie

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
sui caratteri e la fusione RRF)

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
titoli arrivano in italiano da Lighthouse stesso (--locale=it), non da
una nostra traduzione.

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

    Senza dichiarazione viene eseguito solo lo spider e si raccolgono
    gli alert PASSIVI, ricavati osservando le risposte: header
    mancanti, informazioni divulgate, cookie senza attributi. Utili e
    innocui. Il referto dichiara quale delle due scansioni ha girato.

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

Nota: L'integrazione di ZAP (Zed Attack Proxy) 
(pip install zapcli) tramite zap-cli eleva notevolmente il valore dell'audit 
di sicurezza (WAPT: sudo snap install zaproxy --classic), passando da un 
semplice controllo degli header a uno scan attivo (spidering, active scan 
delle vulnerabilità comuni come XSS, SQLi, ecc.).

In caso di problemi con pacchetti prerequisito per zap-cli provare a 
lanciare i comandi qui sotto.

    ATTENZIONE: eseguirli SOLO dentro un virtualenv attivo. Il secondo
    comando disinstalla urllib3, requests e six dall'ambiente corrente:
    lanciato sul Python di sistema puo' rompere altri programmi e, su
    alcune distribuzioni, strumenti del sistema operativo stesso.
    Verificare prima che "which python" punti dentro il virtualenv.

(
python -m pip install --upgrade pip setuptools wheel
python -m pip uninstall -y urllib3 requests six
python -m pip cache purge
python -m pip install --no-cache-dir --upgrade 'requests>=2.32.0' 'urllib3>=2.2.0'
)

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

Installazione. Le dipendenze sono divise per ruolo:

    pip install -r requirements.txt            # CLI e API: sempre
    pip install -r requirements-optional.txt   # embedding reali, ZAP, Anthropic
    pip install -r requirements-dev.txt        # pytest, flake8

I test si lanciano con `pytest` dalla radice del progetto: girano in
meno di dieci secondi, non toccano la rete e non avviano Lighthouse,
ZAP o un browser.

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
    i_own_this_domain   DICHIARAZIONE di proprieta' del dominio e di
                        assunzione di responsabilita'. Abilita due cose:
                        ignorare robots.txt e l'active scan WAPT, che
                        invia payload d'attacco. Registrata nel referto.
                        Default false.
    credentials         Credenziali per gli strumenti opzionali, se non
                        si vogliono impostare come variabili d'ambiente
                        sul server (vedi sotto).

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

Query della simulazione RRF (--queries FILE, una per riga, UTF-8).
Senza il flag si usano quattro query generiche nella lingua prevalente
del sito, rilevata dall'attributo lang: interrogare un sito inglese in
italiano produrrebbe un consenso basso che non dice nulla sul sito, ma
solo che le domande erano nella lingua sbagliata.

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

    text   il referto a video, come sopra
    json   la struttura canonica: testo e HTML ne sono viste, e l'API
           restituisce gli stessi campi su POST /audit/full
    html   pagina autoconsistente — CSS incorporato, favicon inclusa,
           nessuna CDN e nessuno script — con tema chiaro e scuro

Con --output il referto va su file invece che a video. Il referto JSON
si dà in pasto a mars_citations.py --from-audit, che ne riusa le stesse
query della simulazione RRF: cosi' stima e misura della citabilita'
guardano le stesse domande.

Codici di uscita di mars_audit.py: 0 referto prodotto; 2 nessuna pagina
indicizzata; 3 impossibile scrivere il file di --output.

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
2 errore d'uso o provider non configurato.

Licenza: Apache 2.0