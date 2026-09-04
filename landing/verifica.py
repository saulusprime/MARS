#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controlli statici sulla pagina di M.A.R.S. Beacon.

Su questa macchina un browser non c'e' — niente Node, e Chromium sta
solo dentro l'immagine del container — quindi la resa non si puo'
provare. Questo script prova cio' che si puo' provare senza aprirlo: un
selettore che esce dai propri confini, un id che lo script cerca e non
trova, un'etichetta che non punta al proprio campo, un contrasto sotto
la soglia in una pagina che vende un audit di accessibilita', un file
di assets/ citato e non presente.

I controlli distinguono CIO' CHE E' NOSTRO dal telaio del sito. Il
telaio — testata, menu, piede — e' copiato da ia-agenti-rag.html: il
suo piede porta un badge di terze parti e i suoi link vanno a pagine
che qui non ci sono, e giudicarlo con le nostre regole significherebbe
solo imparare a ignorare l'esito.

Esce 1 se qualcosa non torna, cosi' vale in una pipeline.

    .venv/bin/python landing/verifica.py
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Tuple

from bs4 import BeautifulSoup

QUI = os.path.dirname(os.path.abspath(__file__))
PAGINA = os.path.join(QUI, "mars-beacon.html")

# La soglia AA per il testo, e quella dei componenti non testuali
# (WCAG 1.4.11), che vale per il contorno di un campo.
SOGLIA_TESTO = 4.5
SOGLIA_COMPONENTE = 3.0


def luminanza(colore: str) -> float:
    """Luminanza relativa di un colore `#rrggbb`, come da WCAG 2."""
    canali = [int(colore[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
               for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def contrasto(primo: str, secondo: str) -> float:
    """Rapporto di contrasto fra due colori, sempre >= 1."""
    a, b = luminanza(primo), luminanza(secondo)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


# Le coppie che il frammento realizza davvero: tinta, fondo, soglia.
# Scritte a mano e non dedotte dal CSS, perche' quale testo finisca su
# quale fondo lo decide il markup e non il foglio di stile.
COPPIE: List[Tuple[str, str, str, float]] = [
    ("gravita' ok su bianco", "#008055", "#ffffff", SOGLIA_TESTO),
    ("gravita' ok su card", "#008055", "#f4f7f8", SOGLIA_TESTO),
    ("gravita' warn su bianco", "#995c00", "#ffffff", SOGLIA_TESTO),
    ("gravita' warn su card", "#995c00", "#f4f7f8", SOGLIA_TESTO),
    ("gravita' bad su bianco", "#cc334d", "#ffffff", SOGLIA_TESTO),
    ("gravita' bad su card", "#cc334d", "#f4f7f8", SOGLIA_TESTO),
    ("errore su fondo errore", "#cc334d", "#fdf3f4", SOGLIA_TESTO),
    ("testo su bianco", "#14272b", "#ffffff", SOGLIA_TESTO),
    ("secondario su bianco", "#556879", "#ffffff", SOGLIA_TESTO),
    ("secondario su card", "#556879", "#f4f7f8", SOGLIA_TESTO),
    ("marchio su bianco", "#186078", "#ffffff", SOGLIA_TESTO),
    ("marchio su card", "#186078", "#f4f7f8", SOGLIA_TESTO),
    ("esempio: testo su scuro", "#eaf2f4", "#0b2830", SOGLIA_TESTO),
    ("bianco sul bottone", "#ffffff", "#186078", SOGLIA_TESTO),
    ("bordo di un campo", "#748891", "#ffffff", SOGLIA_COMPONENTE),
]


# Tinte che NON portano informazione, e per cui WCAG non chiede una
# soglia: separatori e fondi decorativi. Ognuna con la sua ragione,
# perche' un elenco di esenzioni senza motivo diventa il posto dove si
# nasconde il contrasto che non si voleva sistemare.
ESENTI = {
    "#dde5e7": "bordo fra riquadri: separa, non identifica un componente",
    "#e6edee": "fondo dell'anello del quadrante: sotto c'e' sempre il "
               "numero, che porta il valore",
    "#5bb6bf": "onda decorativa dell'hero, aria-hidden, presa dal sito",
    "#fdf3f4": "fondo del riquadro d'errore, misurato come fondo sopra",
    "#0b2830": "fondo del blocco d'esempio, misurato come fondo sopra",
}


def controlla(percorso: str) -> List[str]:
    """L'elenco dei guai. Vuoto significa che non ne ho trovati."""
    grezzo = open(percorso, encoding="utf-8").read()
    zuppa = BeautifulSoup(grezzo, "lxml")
    guai: List[str] = []

    # 1. Ogni selettore e' ancorato a una classe. Un `h2` nudo qui
    #    dentro arriverebbe su ogni altra pagina del sito.
    css = "\n".join(t.string or "" for t in zuppa.find_all("style"))
    pulito = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for blocco in re.findall(r"([^{}]+)\{", pulito):
        for selettore in blocco.split(","):
            selettore = selettore.strip()
            if selettore and not selettore.startswith((".", "@")):
                guai.append("selettore non ancorato a una classe: %r"
                            % selettore)

    # 2. Ogni id cercato dallo script esiste nel markup. Un id sbagliato
    #    non solleva: restituisce `null`, e la pagina resta a meta'.
    ids = {e["id"] for e in zuppa.find_all(attrs={"id": True})}
    script = "\n".join(t.string or "" for t in zuppa.find_all("script"))
    cercati = set(re.findall(r'id\("([^"]+)"\)', script))
    cercati |= set(re.findall(r'getElementById\("([^"]+)"\)', script))
    # I paragrafi d'errore si compongono: `mars-e-` piu' il nome del campo.
    for chiave in re.findall(r'\["(mars-[a-z]+)", function', script):
        cercati.add("mars-e-" + chiave.replace("mars-", ""))
    for assente in sorted(c for c in cercati if c not in ids):
        guai.append("lo script cerca l'id %r, che non esiste" % assente)

    # 3. Le cuciture dell'accessibilita': etichette e descrizioni.
    for etichetta in zuppa.find_all("label"):
        se_punta = etichetta.get("for")
        if se_punta and se_punta not in ids:
            guai.append("<label for=%r> non punta a nessun campo" % se_punta)
    for elemento in zuppa.find_all(attrs={"aria-describedby": True}):
        for riferimento in elemento["aria-describedby"].split():
            if riferimento not in ids:
                guai.append("aria-describedby=%r non esiste" % riferimento)

    # 4. Nessuna origine esterna DA CIO' CHE E' NOSTRO: il sito ha una
    #    CSP e un consenso Cookiebot, e una richiesta a un terzo li
    #    aggirerebbe entrambi. Si guarda dentro <main>, perche' il piede
    #    del sito un badge esterno ce l'ha davvero e non e' roba nostra.
    principale = zuppa.find("main")
    if principale is None:
        guai.append("<main> assente: la pagina non ha un contenuto")
    else:
        nostro = str(principale)
        for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', nostro):
            if "w3.org" not in url:
                guai.append("origine esterna dentro <main>: %s" % url)

    # 5. Un solo h1 e nessun salto di gerarchia: e' un criterio che
    #    l'area 7 del prodotto misura sui siti dei clienti.
    livelli = [int(t.name[1]) for t in zuppa.find_all(re.compile(r"^h[1-6]$"))]
    if livelli.count(1) != 1:
        guai.append("gli <h1> sono %d e dev'essere uno" % livelli.count(1))
    for prima, dopo in zip(livelli, livelli[1:]):
        if dopo > prima + 1:
            guai.append("salto di gerarchia: h%d subito dopo h%d"
                        % (dopo, prima))

    # 6. Nessuna lista con figli che non siano <li>.
    for lista in zuppa.find_all(["ul", "ol"]):
        for figlio in lista.find_all(recursive=False):
            if figlio.name != "li":
                guai.append("<%s> figlio diretto di <%s>"
                            % (figlio.name, lista.name))

    # 7. I contrasti.
    for nome, tinta, fondo, soglia in COPPIE:
        rapporto = contrasto(tinta, fondo)
        if rapporto < soglia:
            guai.append("contrasto %s: %.2f:1, sotto la soglia %.1f:1"
                        % (nome, rapporto, soglia))

    # 8. Ogni tinta del foglio o e' misurata sopra, o e' esente CON UNA
    #    RAGIONE. Non e' pedanteria: senza, chi cambia un colore fra sei
    #    mesi non fa fallire nulla, e i quindici contrasti misurati qui
    #    diventano una riga di README che non corrisponde piu' al file.
    dichiarate = {t.lower() for _, t, _, _ in COPPIE}
    dichiarate |= {f.lower() for _, _, f, _ in COPPIE}
    dichiarate |= set(ESENTI)
    for colore in sorted(set(re.findall(r"#[0-9a-fA-F]{6}", pulito))):
        if colore.lower() not in dichiarate:
            guai.append("il colore %s non e' ne' misurato ne' dichiarato "
                        "esente: aggiungerlo a COPPIE o a ESENTI" % colore)

    # 9. Ogni file di assets/ che la pagina cita esiste davvero. E' la
    #    proprieta' per cui la pagina si apre da sola: un percorso
    #    sbagliato non solleva nulla, il browser lascia solo un buco
    #    dove c'era il foglio di stile.
    #
    #    Se assets/ NON C'E' AFFATTO il controllo si salta, e lo dice:
    #    quella cartella e' del sito e non sta in questo repository, e
    #    un controllo verde qui e rosso su un clone appena fatto
    #    renderebbe la verifica dipendente dalla macchina — la stessa
    #    trappola gia' pagata con node_modules.
    citati = sorted(set(re.findall(r'(?:src|href)="(assets/[^"]+)"', grezzo)))
    #    Le immagini nostre stanno fuori da assets/ e in git ci sono:
    #    quelle si controllano sempre.
    if principale is not None:
        for tag in principale.find_all("img"):
            fonte = tag.get("src", "")
            if fonte and not re.match(r"(?:https?:|data:|//)", fonte):
                if not os.path.exists(os.path.join(QUI, fonte)):
                    guai.append("<img src=%r> non esiste" % fonte)
                elif not (tag.get("width") and tag.get("height")):
                    # Senza le due misure il testo salta quando
                    # l'immagine arriva, ed e' il CLS che il prodotto
                    # misura sui siti dei clienti.
                    guai.append("<img src=%r> senza width/height" % fonte)
    if not os.path.isdir(os.path.join(QUI, "assets")):
        print("assets/ assente: i %d file citati non sono stati controllati "
              "(vedi landing/README.md)" % len(citati), file=sys.stderr)
    else:
        for percorso in citati:
            if not os.path.exists(os.path.join(QUI, percorso)):
                guai.append("citato e assente: %s" % percorso)

    # 10. Il telaio del sito e' arrivato tutto: i due fogli di stile, lo
    #     script, e i punti in cui la pagina si aggancia a loro.
    for atteso, dove in (
            ("assets/vendor/bootstrap-italia/css/bootstrap-italia.min.css",
             "Bootstrap Italia"),
            ("assets/css/lympha.css", "il foglio del sito"),
            ("assets/js/lympha.js", "lo script del sito")):
        if atteso not in grezzo:
            guai.append("manca %s (%s)" % (atteso, dove))
    if not zuppa.find(attrs={"data-article": True}):
        guai.append("nessun [data-article]: lo scrollspy dell'indice "
                    "resta spento")

    # 11. Ogni ancora interna porta da qualche parte. Un `#` che non
    #     esiste non solleva: il browser resta dov'e', e l'indice
    #     laterale sembra rotto senza che nulla lo dica.
    if principale is not None:
        for collegamento in principale.find_all("a", href=True):
            meta = collegamento["href"]
            if meta.startswith("#") and len(meta) > 1 and meta[1:] not in ids:
                guai.append("l'ancora %s non porta a nessun id" % meta)

    return guai


def main() -> int:
    if not os.path.exists(PAGINA):
        print("pagina assente: %s" % PAGINA, file=sys.stderr)
        return 1
    guai = controlla(PAGINA)
    if guai:
        print("PROBLEMI (%d):" % len(guai))
        for guaio in guai:
            print("  - %s" % guaio)
        return 1
    print("nessun problema rilevato in %s" % os.path.basename(PAGINA))
    print("  %d contrasti misurati, il piu' basso %.2f:1"
          % (len(COPPIE), min(contrasto(t, f) for _, t, f, _ in COPPIE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
