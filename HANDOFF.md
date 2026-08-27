# HANDOFF — 2026-08-27

> Questo file esiste solo perché resta lavoro a metà. Quando R58 e R59 sono
> chiuse, **si cancella**: il suo contenuto duraturo sta già altrove.
>
> Ordine di lettura: questo → [AS-IS.md](AS-IS.md) → [TO-DO.md](TO-DO.md).

## Come si sta lavorando

- **Un ramo solo, `main`**, e si committa lì: `upgrade` è stato rifuso e
  cancellato oggi. Il remoto è `git@github.com:saulusprime/MARS.git`.
- Il push funziona solo con la chiave giusta: `~/.ssh/id_ed25519` è
  l'account `LymphaTechnologies`, che su questo repo **non ha scrittura**.
  Il clone ha già `core.sshCommand` legato a `~/.ssh/id_ed25519_2`
  (`saulusprime`) — se sparisse, il push tornerebbe «Permission denied».
- `flake8` e `pytest` **non sono nel PATH**: si invocano da `.venv/bin/`.
  Riferimento a fine sessione: `flake8` 0, `pytest` **1130 passed**.

## Che cosa è stato fatto oggi

Sette voci chiuse — R53, R54, R55, R56, R57 più le due pulizie del TO-DO —
tutte in [AS-IS.md](AS-IS.md) con difetto, misura e prove. Le tre che
contano per chi riprende:

- **R55/R56**: lo spider di ZAP non rispettava robots.txt ed è ora dietro
  `--i-own-this-domain`. Senza dichiarazione l'area 7 vede solo le pagine
  che il crawler ha già scaricato. Nuovo flag `--max-children`.
- **R57**: nuovo `--credentials FILE`. `main()` è diventata una funzione
  che restituisce il codice di uscita, e non un blocco `if __name__`.
- **`schema_version` è a 3** (R53). `__version__` resta 2.9.0.

## Prossimo passo: R58 e R59

Sono le due voci aperte, **entrambe già riprodotte**: i numeri stanno nel
TO-DO, non serve rimisurare per cominciare.

- **R58** — l'annuncio della spesa si stampa anche quando nulla partirà.
  Verificato su SDK anthropic **0.122.0**: `anthropic.Anthropic()` non
  valida alla costruzione, risolve alla richiesta. Da sapere prima di
  toccare: il ramo `no_credentials` con `stage="client"` oggi **non è mai
  raggiungibile**, e la correzione deve renderlo tale.
- **R59** — `mars_audit.py URL --format json > f.json` non si rilegge.
  13 stampe in `mars_audit.py`, 8 nei moduli, altre 8 in
  `mars_citations.py`: quest'ultima è la decisione da prendere — una voce
  sola o due.

## Stati temporanei da sapere

- **`cliente_1.json` è nella radice, non tracciato e non ignorato**, e
  contiene l'URL di un cliente. Viene da un'esecuzione reale; decidere se
  ignorarlo (`*.local.json` lo sarebbe già) o spostarlo.
- **`python-dotenv` 1.2.3 è installato nel `.venv`** ma **nessuno lo
  chiama** e non sta in alcun `requirements*.txt`. È stato installato per
  far leggere `.env`, che MARS non legge: dopo R57 la strada è
  `--credentials`, quindi il pacchetto si può disinstallare.
- **Nessun daemon ZAP né server di prova è rimasto acceso** (porte 8080 e
  8933-8938 chiuse a fine sessione).

## Credenziali, dopo R57

`.env` **non viene letto** e una variabile senza `export` non è visibile al
processo. Le due strade sono le variabili d'ambiente esportate, oppure:

    cp examples/audit_request.json chiavi.local.json
    chmod 600 chiavi.local.json      # *.local.json è ignorato da git
    python3 mars_audit.py https://sito.it \
        --credentials chiavi.local.json --llm on

**C4 resta non verificata**: il giudizio LLM non è mai stato eseguito contro
il servizio reale. L'esecuzione dell'utente di oggi non fa fede — la chiave
non era nel processo, e il referto lo dichiarava.
