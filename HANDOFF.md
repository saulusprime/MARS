# HANDOFF — 2026-08-27

> Questo file esiste solo perché resta lavoro a metà. Il lavoro **tecnico**
> non ne ha più: le cinque correzioni della sessione sono chiuse. Restano
> due **decisioni tue** sugli stati temporanei qui sotto: quando le hai
> prese, questo file si cancella.
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
  Riferimento a fine sessione: `flake8` 0, `pytest` **1138 passed**.
- I commit del 2026-08-27 sono **su `origin/main`**.

## Che cosa è stato fatto oggi

Undici voci chiuse — da R53 a R61, più le due pulizie del TO-DO — tutte
in [AS-IS.md](AS-IS.md) con difetto, misura e prove. Le cinque che
contano per chi riprende:

- **R55/R56**: lo spider di ZAP non rispettava robots.txt ed è ora dietro
  `--i-own-this-domain`. Senza dichiarazione l'area 7 vede solo le pagine
  che il crawler ha già scaricato. Nuovo flag `--max-children`.
- **R57**: nuovo `--credentials FILE`. `main()` è diventata una funzione
  che restituisce il codice di uscita, e non un blocco `if __name__`.
- **R58**: l'annuncio della spesa del giudizio LLM esce solo se qualcosa
  partirà davvero. `credenziale_risolta()` guarda le **tre** fonti che
  l'SDK guarda — `api_key`, `auth_token`, `credentials` — e non la sola
  chiave, altrimenti un profilo `ant auth login` verrebbe scambiato per
  assenza.
- **R59**: diagnostica su `stderr`, referto su `stdout`. Da sapere prima
  di aggiungere una stampa: un `print()` senza `file=sys.stderr` in
  `mars_audit`, `mars_core`, `mars_wapt` o `mars_llm_judge` fa fallire
  `test_su_stdout_va_solo_il_referto`, che legge l'AST dei sorgenti. Il
  referto si scrive con `sys.stdout.write`, apposta.
- **R60/R61**: nel referto ogni esempio di correzione porta la didascalia
  «Esempio — non è contenuto del tuo sito», e l'etichetta «Correzione:»
  è uscita dal CSS. Da sapere prima di toccare i renderer: i letterali
  passati a `t()` vanno scritti **in linea**, non in una costante —
  `test_ogni_letterale_della_cornice_e_a_catalogo` indicizza sull'AST, e
  una costante scollega la traduzione senza rompere nulla.
- **`schema_version` è a 3** (R53). `__version__` resta 2.9.0.

## Prossimo passo

Nessuna correzione aperta. Il [TO-DO](TO-DO.md) ha cinque caselle: le tre
fasi UPGRADE residue (U10, U10.1, U11) e le due prove mancanti (C4, il
giudizio LLM mai eseguito contro il servizio reale — **bloccata su una
chiave**, non sul codice — e `evaluate_answer` di `mars_citations.py`).

## Le due decisioni che tengono in vita questo file

- **`cliente_1.json` è nella radice, non tracciato e non ignorato**, e
  contiene l'URL di un cliente. Viene da un'esecuzione reale: da ignorare
  (`*.local.json` lo sarebbe già), da spostare o da cancellare.
- **`python-dotenv` 1.2.3 è installato nel `.venv`** ma **nessuno lo
  chiama** e non sta in alcun `requirements*.txt`. È stato installato per
  far leggere `.env`, che MARS non legge: dopo R57 la strada è
  `--credentials`, quindi il pacchetto si può disinstallare.

## Credenziali, dopo R57

`.env` **non viene letto** e una variabile senza `export` non è visibile al
processo. Le due strade sono le variabili d'ambiente esportate, oppure:

    cp examples/credentials.json chiavi.local.json
    chmod 600 chiavi.local.json      # *.local.json è ignorato da git
    $EDITOR chiavi.local.json        # {"credentials": {"anthropic_api_key": "sk-ant-..."}}
    python3 mars_audit.py https://sito.it \
        --credentials chiavi.local.json --llm on

Il modello è `examples/credentials.json` e **non** `audit_request.json`,
che è il corpo di una richiesta API: passato a `--credentials` consegna
quattro segnaposto come se fossero chiavi (R62).

**C4 resta non verificata**: il giudizio LLM non è mai stato eseguito contro
il servizio reale. L'esecuzione dell'utente di oggi non fa fede — la chiave
non era nel processo, e il referto lo dichiarava.
