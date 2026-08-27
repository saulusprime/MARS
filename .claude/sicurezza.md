## Sicurezza

- `MARS_SECRET_KEY` firma i JWT. Senza, il server genera una chiave
  effimera e lo dichiara: i token scadono a ogni riavvio.
- **Mai interpolare un URL in una stringa di shell.** Gli URL arrivano
  dall'utente, anche dal corpo di una richiesta API: lista di argomenti
  e `shell=False`.
- Il crawler rispetta robots.txt. L'unico modo per ignorarlo è la
  dichiarazione di proprietà del dominio (`--i-own-this-domain`,
  `i_own_this_domain`), che viene registrata nel referto.
- **La regola vale per ogni cosa che tocchi il sito, non per il solo
  crawler**, ed è costata R55: lo spider di ZAP è un secondo crawler,
  e robots.txt non lo rispetta. Misurato su ZAP 2.17.0 — richiede gli
  URL vietati, e usa le voci `Disallow` come **semi** da cui partire,
  quindi robots.txt lo fa scansionare *di più* proprio dove il sito
  chiede di non andare. Fra le ventiquattro opzioni dello spider una
  per obbedire non esiste. Da R55 lo spider è dietro la dichiarazione
  come l'active scan, e senza dichiarazione ZAP vede le sole pagine
  che il crawler ha già scaricato. Chi aggiunge uno strumento esterno
  che naviga da sé si faccia la stessa domanda **prima**: la promessa
  è del progetto, non del modulo.
