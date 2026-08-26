## Sicurezza

- `MARS_SECRET_KEY` firma i JWT. Senza, il server genera una chiave
  effimera e lo dichiara: i token scadono a ogni riavvio.
- **Mai interpolare un URL in una stringa di shell.** Gli URL arrivano
  dall'utente, anche dal corpo di una richiesta API: lista di argomenti
  e `shell=False`.
- Il crawler rispetta robots.txt. L'unico modo per ignorarlo è la
  dichiarazione di proprietà del dominio (`--i-own-this-domain`,
  `i_own_this_domain`), che viene registrata nel referto.
