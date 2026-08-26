## Come si lavora

- **`pytest` deve restare verde**, e la suite non deve toccare la rete:
  la fixture `niente_rete` lo impedisce, ed e' `autouse` perche' nessuno
  possa dimenticarla.
  Si invoca **senza `-q`**: `setup.cfg` ce l'ha già in `addopts`, e un
  secondo `-q` fa `-qq`, che sopprime la riga di riepilogo finale — la
  suite può essere rossa senza che si veda. In uno script, decidere dal
  **codice di uscita**, mai da una parola nell'output.
- **Reintrodurre il difetto per fidarsi del test.** Un test verde non
  dimostra nulla finche' non lo si e' visto fallire. Un giro di mutazioni
  va eseguito con **`PYTHONDONTWRITEBYTECODE=1`**: applicare e
  ripristinare una mutazione della stessa lunghezza dentro lo stesso
  secondo lascia in `__pycache__` il bytecode vecchio (vedi la trappola
  qui sotto), e le mutazioni di un carattere — `3.0` -> `5.0` — vengono
  valutate sul codice sbagliato. Verificare inoltre che il file resti
  **importabile**: una mutazione che rompe la sintassi fa fallire tutto
  e non dimostra che il test cogliesse quel difetto.
- **Il referto ha dei golden.** `tests/golden/` congela la resa dei tre
  formati su due referti sintetici. Cambiare una resa — o un punteggio,
  perche' i golden congelano la pipeline intera — fa fallire
  `tests/test_golden.py`: si rigenera con `MARS_RIGENERA_GOLDEN=1 pytest`
  e **si rivede il diff**, non si rigenera per far tornare il verde.
- **`flake8` deve restare a zero.** `setup.cfg` è già configurato:
  basta `flake8 .`. È il controllo che ha rivelato il difetto più grave
  del progetto (login rotto da una funzione definita due volte).
- **Verificare, non dedurre.** Prima di correggere, riprodurre il
  difetto; dopo, dimostrare che è chiuso. Diverse voci di
  [AS-IS.md](AS-IS.md) documentano previsioni smentite dalla misura:
  registrarle vale più che cancellarle.
- **Un commit per voce del TO-DO**, e **la riformattazione in un commit
  separato** da ciò che cambia il comportamento.
- **Chiuso ≠ cancellato.** Una voce risolta si sposta dal TO-DO ad
  AS-IS con difetto, soluzione e verifiche, così nessuno rifà la stessa
  indagine.
