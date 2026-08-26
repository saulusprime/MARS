# MARS Beacon — istruzioni per il lavoro assistito

Contesto essenziale per chi (persona o modello) mette mano al codice.
Il quadro completo sta in [README.md](README.md), il lavoro aperto in
[TO-DO.md](TO-DO.md), quello concluso in [AS-IS.md](AS-IS.md).

Le istruzioni vere stanno nei file qui sotto, uno per argomento, e le
righe `@` li importano: Claude Code le risolve e monta il testo in
questo punto, così ciò che arriva nel contesto è identico a prima della
divisione. Chi legge a mano segue i link.

- [Il contratto dei moduli](.claude/contratto-moduli.md) — cosa arriva
  in `context`, cosa `audit()` deve restituire.
- [Principi da non violare](.claude/principi.md) — le sette scelte di
  fondo del progetto.
- [Come si lavora](.claude/metodo.md) — pytest, flake8, golden,
  mutazioni, commit.
- [Trappole già pagate](.claude/trappole.md) — i difetti che sono
  costati ore e possono ancora tornare.
- [Sicurezza](.claude/sicurezza.md) — segreti, shell, robots.txt.

Aggiungere un argomento significa aggiungere **un file e la sua riga
`@`**: se un file c'è e la riga manca, il testo non arriva nel contesto
e nessuno se ne accorge, perché il file esiste e si legge benissimo.

@.claude/contratto-moduli.md
@.claude/principi.md
@.claude/metodo.md
@.claude/trappole.md
@.claude/sicurezza.md
