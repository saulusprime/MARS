#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — monitoraggio delle citazioni IA (R28).
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0

Prima di R28 questo file non esisteva: `mars_citations` era l'unico
strumento del progetto senza un solo test, e i due difetti che la voce
descrive vivevano proprio li' dove nessuno guardava.

Nessun test qui tocca la rete o spende: il provider e' finto e
restituisce risposte costruite a mano, quindi `niente_rete` non deve
nemmeno intervenire.
"""

from __future__ import annotations

import json
import os

import pytest

import mars_citations
from mars_citations import ProviderAnswer


class ProviderFinto:
    """Un provider che risponde senza rete: `ok` decide se ha risposto.

    L'interfaccia e' tutta qui — `name` e `ask()` — ed e' la prova che
    il contratto dei provider e' abbastanza piccolo da essere sostituito
    nei test senza mock: lo stesso motivo per cui `evaluate_answer` e
    `overall_rate` sono funzioni pure.
    """

    name = "finto"

    def __init__(self, ok: bool = True, citato: bool = True) -> None:
        self.ok = ok
        self.citato = citato

    def ask(self, query: str) -> ProviderAnswer:
        if not self.ok:
            return ProviderAnswer(provider=self.name, query=query,
                                  ok=False, error="provider giu'")
        urls = ["https://esempio.test/pagina"] if self.citato else []
        return ProviderAnswer(provider=self.name, query=query,
                              cited_urls=list(urls), searched_urls=list(urls))


@pytest.fixture
def queries(tmp_path):
    percorso = tmp_path / "queries.txt"
    percorso.write_text("prima domanda\nseconda domanda\n", encoding="utf-8")
    return str(percorso)


def _esegui(monkeypatch, queries, *extra, ok=True, citato=True):
    """Lancia `main()` con il provider finto, senza rete e senza attese."""
    monkeypatch.setitem(mars_citations.PROVIDERS, "finto",
                        lambda: ProviderFinto(ok=ok, citato=citato))
    return mars_citations.main(
        ["https://esempio.test/", "--queries", queries,
         "--provider", "finto", "--delay", "0", "--quiet", *extra])


# ----------------------------------------------------------------------
# Scritture: un percorso non scrivibile non e' «sotto soglia»
# ----------------------------------------------------------------------

def test_output_non_scrivibile_ha_un_codice_di_uscita_suo(
        monkeypatch, queries, tmp_path, capsys):
    """R28: l'`open` di `--output` non gestiva `OSError`, e il traceback
    usciva con **1** — lo stesso codice di `--fail-under`.

    Una pipeline che distingue «sotto soglia» da «rotto» leggeva quindi
    un guasto di scrittura come un giudizio sul sito. Il 3 non e' una
    scelta libera: e' quello di `mars_audit.EXIT_SCRITTURA`, il cui
    commento promette da sempre l'allineamento con questo file.

    La leva dell'errore e' una DIRECTORY, non un chmod: `open()` su una
    directory solleva `IsADirectoryError` — sottoclasse di `OSError` —
    a prescindere dai permessi, mentre un chmod sarebbe verde per caso
    su una macchina che gira da root.
    """
    codice = _esegui(monkeypatch, queries, "--output", str(tmp_path))

    assert codice == mars_citations.EXIT_SCRITTURA
    assert codice != mars_citations.EXIT_SOTTO_SOGLIA
    assert str(tmp_path) in capsys.readouterr().err


def test_lo_storico_non_scrivibile_non_porta_via_il_referto(
        monkeypatch, queries, tmp_path, capsys):
    """R28: `append_history` sollevava **prima** del rendering, quindi
    un percorso di storico non scrivibile buttava via un referto gia'
    pagato in chiamate API.

    Lo storico e' un archivio: perdere una riga non vale il codice di
    uscita, ed e' la stessa scelta gia' scritta in `mars_audit` e in
    `mars_history.appendi_storico`. Il referto si stampa, il guasto si
    dichiara, si esce con 0.
    """
    codice = _esegui(monkeypatch, queries, "--history", str(tmp_path))
    uscita = capsys.readouterr()

    assert codice == mars_citations.EXIT_OK
    assert "CITAZIONI IA" in uscita.out, "il referto e' andato perso"
    assert str(tmp_path) in uscita.err, "il guasto non e' dichiarato"


def test_lo_storico_si_scrive_quando_il_percorso_e_buono(
        monkeypatch, queries, tmp_path):
    """Il ramo felice, altrimenti il test qui sopra passerebbe anche se
    lo storico non venisse mai scritto."""
    storico = tmp_path / "storico.jsonl"
    codice = _esegui(monkeypatch, queries, "--history", str(storico))

    assert codice == mars_citations.EXIT_OK
    righe = storico.read_text(encoding="utf-8").strip().split("\n")
    assert len(righe) == 1
    assert json.loads(righe[0])["site"] == "esempio.test"


def test_output_scritto_quando_il_percorso_e_buono(
        monkeypatch, queries, tmp_path):
    codice = _esegui(monkeypatch, queries, "--output",
                     str(tmp_path / "referto.txt"))

    assert codice == mars_citations.EXIT_OK
    assert "CITAZIONI IA" in (tmp_path / "referto.txt").read_text(
        encoding="utf-8")


# ----------------------------------------------------------------------
# Zero su zero non e' zero per cento
# ----------------------------------------------------------------------

def test_nessuna_risposta_non_e_zero_per_cento(monkeypatch, queries):
    """R28: se tutte le query di un provider fallivano, `run_monitor`
    scriveva `rate: 0.0` — «0% di citazioni» per un dato **mai
    misurato**, indistinguibile da uno 0% reale nel referto e nello
    storico.

    Nella stessa riga JSONL le due misure dello stesso non-dato si
    contraddicevano: `overall_rate` diceva gia' `null`. Ora dicono la
    stessa cosa.
    """
    payload = mars_citations.run_monitor(
        "https://esempio.test/", ["a", "b"], [ProviderFinto(ok=False)],
        delay=0, verbose=False)
    stats = payload["providers"]["finto"]

    assert stats["answered"] == 0
    assert stats["failed"] == 2
    assert stats["rate"] is None, "0 su 0 non e' 0%"
    assert mars_citations.overall_rate(payload) is None


def test_zero_citazioni_su_risposte_vere_resta_zero(monkeypatch, queries):
    """L'altra meta': uno 0% **misurato** deve restare 0.0, o la
    correzione avrebbe solo spostato la bugia."""
    payload = mars_citations.run_monitor(
        "https://esempio.test/", ["a", "b"],
        [ProviderFinto(ok=True, citato=False)], delay=0, verbose=False)
    stats = payload["providers"]["finto"]

    assert stats["answered"] == 2
    assert stats["rate"] == 0.0
    assert mars_citations.overall_rate(payload) == 0.0


def test_la_vista_testo_regge_un_tasso_non_misurato():
    """`render_text` formattava `rate` con `%.1f`: un `None` la faceva
    sollevare `TypeError`.

    Le due modifiche — `None` in `run_monitor` e `n/d` qui — devono
    stare nello stesso commit, altrimenti la prima rompe la seconda.
    La dicitura e' quella che il totale usa gia' da sempre.
    """
    payload = mars_citations.run_monitor(
        "https://esempio.test/", ["a"], [ProviderFinto(ok=False)],
        delay=0, verbose=False)
    testo = mars_citations.render_text(payload, None)
    riga = [r for r in testo.split("\n") if r.startswith("[finto]")]

    assert riga, "la riga del provider e' sparita"
    assert "n/d" in riga[0], \
        "il totale diceva gia' n/d: il presidio serve sulla riga del provider"
    assert "0.0%" not in riga[0]
    assert "Tasso complessivo di citazione: n/d" in testo


def test_il_tasso_non_misurato_arriva_nullo_anche_nel_json(
        monkeypatch, queries, tmp_path):
    """Il JSON e la riga di storico sono le due superfici pubbliche: il
    `null` deve arrivare a entrambe, o un consumatore continuerebbe a
    leggere 0.0."""
    storico = tmp_path / "storico.jsonl"
    codice = _esegui(monkeypatch, queries, "--format", "json",
                     "--history", str(storico),
                     "--output", str(tmp_path / "r.json"), ok=False)

    assert codice == mars_citations.EXIT_OK
    referto = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert referto["providers"]["finto"]["rate"] is None
    riga = json.loads(storico.read_text(encoding="utf-8").strip())
    assert riga["overall_rate"] is None
    assert riga["providers"]["finto"]["rate"] is None


# ----------------------------------------------------------------------
# I codici di uscita sono dichiarati, non sparsi
# ----------------------------------------------------------------------

def test_i_codici_di_uscita_sono_quelli_di_mars_audit():
    """I due strumenti si usano nella stessa pipeline: due scale diverse
    per lo stesso guasto sarebbero peggio di nessuna scala.

    `mars_audit` porta il commento «Codici di uscita, allineati a quelli
    di mars_citations.py» da prima che questo file avesse le costanti:
    era una promessa senza controparte, e questo test e' la controparte.
    """
    import mars_audit

    assert mars_citations.EXIT_OK == mars_audit.EXIT_OK == 0
    assert mars_citations.EXIT_USO == mars_audit.EXIT_USO == 2
    assert mars_citations.EXIT_SCRITTURA == mars_audit.EXIT_SCRITTURA == 3
    # Il solo che mars_audit non ha ancora: la soglia e' l'idea I2.
    assert mars_citations.EXIT_SOTTO_SOGLIA == 1


def test_la_soglia_resta_distinta_dal_guasto_di_scrittura(
        monkeypatch, queries, tmp_path):
    """Il difetto di R28 era che i due casi si confondevano: qui si
    esercitano entrambi, e devono dare numeri diversi."""
    sotto = _esegui(monkeypatch, queries, "--fail-under", "99",
                    citato=False)
    guasto = _esegui(monkeypatch, queries, "--output", str(tmp_path))

    assert sotto == mars_citations.EXIT_SOTTO_SOGLIA
    assert guasto == mars_citations.EXIT_SCRITTURA
    assert sotto != guasto


def test_il_readme_dichiara_il_codice_di_scrittura():
    """Un codice di uscita non documentato non e' usabile in una
    pipeline: chi la scrive non sa che esiste.

    Il README ha DUE righe di codici di uscita, una per strumento: si
    cerca quella di `mars_citations`, che e' la seconda e non nomina
    `mars_audit.py`. Prendere la prima che capita renderebbe il test
    verde grazie alla riga dell'altro strumento, che il 3 ce l'ha da
    sempre.
    """
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(radice, "README.md"), encoding="utf-8") as fh:
        righe = fh.read().split("\n")

    inizi = [i for i, r in enumerate(righe)
             if r.startswith("Codici di uscita:")]
    assert len(inizi) == 1, \
        "la riga dei codici di mars_citations non e' piu' identificabile"

    # Il paragrafo, non le prime due righe: la descrizione dei codici e'
    # cresciuta, e un test che ne guardava un pezzo fisso sarebbe rosso
    # per la lunghezza del testo invece che per il suo contenuto.
    fine = righe.index("", inizi[0])
    paragrafo = " ".join(righe[inizi[0]:fine])

    assert "--fail-under" in paragrafo
    assert "3" in paragrafo, "il codice di scrittura non e' documentato"
    assert "--output" in paragrafo


# ----------------------------------------------------------------------
# `evaluate_answer`: la misura centrale dello strumento (C12)
# ----------------------------------------------------------------------
#
# Era chiamata SOLO di sponda, da `main()` attraverso `run_monitor`, e con
# un provider finto che mette la stessa lista in `cited_urls` e in
# `searched_urls` e non nomina alcun concorrente. Misurato prima di
# scrivere: sei mutazioni su sei passavano inosservate — «citato» che
# legge i consultati, «consultato» che legge i citati, i concorrenti letti
# dalla lista sbagliata o non ordinati, `cited_urls` non pubblicati,
# `error` non propagato. La suite era verde per ognuna.
#
# Qui la si esercita per quello che e': una funzione PURA, senza rete e
# senza chiavi.

SITO = "esempio.test"


def _risposta(citati=(), consultati=(), ok=True, error="",
              query="domanda"):
    """Una risposta di provider con le due liste DISGIUNTE per default.

    E' il punto: tenerle uguali — come fa `ProviderFinto`, dove e'
    giusto perche' simula un provider vero — rende indistinguibili
    «citato» e «consultato».
    """
    return ProviderAnswer(provider="finto", query=query, ok=ok,
                          error=error, cited_urls=list(citati),
                          searched_urls=list(consultati))


def test_citato_e_consultato_leggono_due_liste_diverse():
    """La distinzione su cui poggia la scala a tre stati del referto.

    Un assistente che apre il sito e poi non lo cita e' il caso piu'
    istruttivo dell'intero strumento: dice che il contenuto e' stato
    raggiunto e scartato, non che era irraggiungibile."""
    solo_consultato = mars_citations.evaluate_answer(
        _risposta(citati=["https://altro.test/x"],
                  consultati=["https://esempio.test/pagina"]), SITO, ())
    assert solo_consultato["site_consulted"] is True
    assert solo_consultato["site_cited"] is False

    solo_citato = mars_citations.evaluate_answer(
        _risposta(citati=["https://esempio.test/pagina"],
                  consultati=["https://altro.test/x"]), SITO, ())
    assert solo_citato["site_cited"] is True
    assert solo_citato["site_consulted"] is False


def test_un_sottodominio_conta_e_un_omonimo_no():
    """`host_matches` include i sottodomini, e NON i domini che finiscono
    per caso con lo stesso testo: `nonesempio.test` non e' un
    sottodominio di `esempio.test`, ed e' la stessa difesa del filtro
    same-host del crawler (R24)."""
    esito = mars_citations.evaluate_answer(
        _risposta(citati=["https://blog.esempio.test/articolo"]), SITO, ())
    assert esito["site_cited"] is True
    estraneo = mars_citations.evaluate_answer(
        _risposta(citati=["https://nonesempio.test/articolo"]), SITO, ())
    assert estraneo["site_cited"] is False


CONCORRENTI = ("zeta.test", "alfa.test", "delta.test", "beta.test",
               "gamma.test", "epsilon.test", "omega.test")


def test_i_concorrenti_citati_sono_un_insieme_ordinato():
    """Un insieme perche' due URL dello stesso concorrente sono UNA
    citazione, ordinato perche' la riga del referto li stampa in fila:
    un ordine che dipende dall'iterazione di un set cambierebbe la resa
    a ogni esecuzione, e i golden di MARS esistono contro questo.

    **Sette concorrenti e non due, ed e' il punto del test.** L'ordine
    di iterazione di un set di stringhe e' randomizzato per processo
    (`PYTHONHASHSEED`), quindi nessuna asserzione di valore puo'
    distinguere `sorted(...)` da `list(...)` con certezza: con due
    elementi la mutazione passava una volta su due, e nel giro di
    mutazioni e' passata davvero. Con sette, le passa una volta su
    5040. Non e' una prova deterministica e non si finge tale: e' il
    massimo ottenibile senza fissare il seme in un sottoprocesso, che
    per una riga di resa costerebbe piu' di quanto valga."""
    esito = mars_citations.evaluate_answer(
        _risposta(citati=["https://%s/a" % host for host in CONCORRENTI]
                  + ["https://zeta.test/duplicato"]),
        SITO, CONCORRENTI)
    assert esito["competitors_cited"] == sorted(CONCORRENTI)
    # Una LISTA, non un set: `sorted` senza la funzione intorno
    # restituirebbe un set, e `json.dumps` del referto solleverebbe.
    assert isinstance(esito["competitors_cited"], list)


def test_un_concorrente_solo_consultato_non_e_citato():
    """La stessa asimmetria del sito, sui concorrenti: `competitors_cited`
    dice CITATO, e leggerlo dai consultati gonfierebbe il confronto."""
    esito = mars_citations.evaluate_answer(
        _risposta(consultati=["https://alfa.test/b"]), SITO, ("alfa.test",))
    assert esito["competitors_cited"] == []


def test_una_risposta_fallita_porta_con_se_il_motivo():
    """`ok` ed `error` arrivano fino alla riga del referto: senza il
    motivo, una query fallita e una query senza citazioni si leggono
    allo stesso modo."""
    esito = mars_citations.evaluate_answer(
        _risposta(ok=False, error="HTTP 503"), SITO, ("alfa.test",))
    assert esito["ok"] is False
    assert esito["error"] == "HTTP 503"
    assert esito["site_cited"] is False
    assert esito["site_consulted"] is False
    assert esito["competitors_cited"] == []


def test_gli_url_citati_arrivano_interi_nel_dato():
    """Il conteggio dice QUANTO, gli URL dicono DOVE: sono due domande
    diverse, e senza la seconda il referto non e' verificabile da chi lo
    riceve."""
    urls = ["https://esempio.test/a", "https://esempio.test/b"]
    esito = mars_citations.evaluate_answer(_risposta(citati=urls), SITO, ())
    assert esito["cited_urls"] == urls
    assert esito["query"] == "domanda"


def test_evaluate_answer_pretende_un_host_gia_normalizzato():
    """Precondizione, non difetto: `run_monitor` normalizza con
    `norm_host` prima di chiamare, e rifarlo qui per ogni URL di ogni
    query costerebbe senza aggiungere nulla.

    Sta scritto in un test perche' e' una trappola per chi chiamasse la
    funzione da fuori: un URL passato come `site_host` non solleva, non
    avverte, e restituisce semplicemente «mai citato»."""
    esito = mars_citations.evaluate_answer(
        _risposta(citati=["https://esempio.test/a"]),
        "https://esempio.test/", ())
    assert esito["site_cited"] is False


def test_la_scala_a_tre_stati_arriva_al_referto():
    """La conseguenza osservabile: CITATO, consultato, assente.

    Tre risposte costruite a mano attraversano `run_monitor` e la resa
    testo. Senza questo test lo stato di mezzo era irraggiungibile: il
    provider finto della suite mette la stessa lista nelle due, quindi
    non produceva mai un «consultato e non citato»."""
    class ProviderTreStati:
        """Un provider che risponde una cosa diversa a ogni query."""

        name = "tre"

        RISPOSTE = {
            "citata": dict(citati=["https://esempio.test/a"]),
            "consultata": dict(consultati=["https://esempio.test/b"]),
            "assente": dict(citati=["https://altro.test/c"]),
        }

        def ask(self, query):
            return _risposta(query=query, **self.RISPOSTE[query])

    payload = mars_citations.run_monitor(
        "https://esempio.test/", list(ProviderTreStati.RISPOSTE),
        [ProviderTreStati()], delay=0, verbose=False)
    righe = mars_citations.render_text(payload).split("\n")
    stati = {r.split()[0]: r.split()[-1] for r in righe
             if r.startswith("    ") and r.split()[0]
             in ProviderTreStati.RISPOSTE}
    assert stati == {"citata": "CITATO", "consultata": "consultato",
                     "assente": "assente"}
    # Il conteggio d'aggregazione segue la stessa distinzione: il
    # «consultato» non entra fra i citati.
    assert payload["providers"]["tre"]["site_cited"] == 1
    assert payload["providers"]["tre"]["answered"] == 3
