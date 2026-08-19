MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.

Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT

Lo script esegue una scansione di un sito (via sitemap o crawling
interno), ne estrae la struttura, e valuta sette aree strategiche:

1. Tecnica          (mars_tech)     indicizzabilita', robots.txt, 
                                    sitemap, crawler IA
2. SEO              (mars_seo)      utilizzando lighthouse
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

Implementato nativamente le parti algoritmiche più complesse
(il crawler, il retriever lessicale BM25, il proxy vettoriale TF-IDF
sui caratteri e la fusione RRF)

Lighthouse (SEO): Lo script cerca il comando lighthouse nel PATH.
Per attivarlo devi avere Node.js e Lighthouse installati globalmente
(npm install -g lighthouse). In alternativa, restituirà uno score di
fallback. Opzionale installa la libreria corepack (npm install -g corepack)

WAPT e WCAG: Le funzioni attuali per l'accessibilità sono state impostate
come stub euristici o possono essere espanse. Per un audit WCAG reale
ti consiglio di integrare librerie come axe-core (tramite Selenium o
Playwright, pip install playwright, playwright install chromium) 
all'interno del loop di crawling. L'integrazione di ZAP (Zed Attack Proxy) 
(pip install zapcli) tramite zap-cli eleva notevolmente il valore dell'audit 
di sicurezza (WAPT), passando da un semplice controllo degli header a uno 
scan attivo (spidering, active scan delle vulnerabilità comuni come XSS, 
SQLi, ecc.).

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
citabilità (attivo di default in modalità "auto" quando la chiave 
ANTHROPIC_API_KEY è presente installare la libreria Anthropic 
(pip install anthropic).

Installazione. Le dipendenze sono divise per ruolo:

    pip install -r requirements.txt            # CLI e API: sempre
    pip install -r requirements-optional.txt   # embedding reali, ZAP, Anthropic
    pip install -r requirements-dev.txt        # pytest, flake8

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
    uvicorn mars_api:app --host 127.0.0.1 --port 8000

MARS_SECRET_KEY firma i token JWT. Se non e' impostata il server parte
comunque, ma genera una chiave effimera e lo dichiara: i token smettono
di valere a ogni riavvio. E' un ripiego per lo sviluppo, non per la
produzione.

Se la porta 8000 e' gia' occupata uvicorn esce con "address already in
use": usare --port 8010 o un'altra libera. Vale la pena controllare il
log all'avvio, perche' un server che non si e' agganciato lascia
rispondere qualunque altra applicazione stia su quella porta, e le
risposte sembrano provenire da MARS.

Documentazione interattiva su http://127.0.0.1:8000/docs (Swagger UI);
la radice / vi reindirizza con un 307. La specifica OpenAPI vera e'
generata da FastAPI su /openapi.json.

Autenticazione. Tutti gli endpoint di audit richiedono un token JWT
(OAuth2 password flow). Credenziali predefinite: admin / mars2026 —
da cambiare prima di qualunque uso reale.

    # 1. ottenere il token
    TOKEN=$(curl -s -X POST http://127.0.0.1:8000/token \
        -d "username=admin&password=mars2026" | python3 -c \
        "import sys,json;print(json.load(sys.stdin)['access_token'])")

    # 2. usarlo
    curl -s -X POST http://127.0.0.1:8000/audit/full \
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

Corpo della richiesta (AuditRequest), tutti i campi opzionali tranne url:

    url                 URL del sito da scansionare
    max_pages           numero massimo di pagine (default 10)
    embeddings          modello SentenceTransformer, o "none" per il
                        proxy char-tfidf (default: modello multilingue)
    market              mercato di riferimento per la citabilita' IA
    delay               pausa fra le richieste in secondi (default 0.5)
    timeout             timeout di rete in secondi (default 10)
    i_own_this_domain   DICHIARAZIONE di proprieta' del dominio e di
                        assunzione di responsabilita'. E' l'unico modo
                        per ignorare robots.txt, e viene registrata nel
                        referto. Default false.

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