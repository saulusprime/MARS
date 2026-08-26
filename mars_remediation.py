#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import mars_citability
from mars_core import SEV_CRITICAL, SEV_WARNING

# ======================================================================
# Il piano di interventi (U4 / Fase 4 di UPGRADE.md)
# ----------------------------------------------------------------------
# Fra "elenco dei difetti" e "che cosa faccio lunedi' mattina" non
# c'era nulla. Dalla Fase 1 ogni rilievo e' un dato con una gravita' e
# una penalita', dalla Fase 3 dice anche come si aggiusta: qui quei
# rilievi diventano un elenco ORDINATO, e ogni voce dichiara quanto si
# guadagna a chiuderla.
#
# ----------------------------------------------------------------------
# Non e' un'area, e per questo non sta in MODULES_REGISTRY
#
#   Non espone `audit(context)`, non misura niente e non tocca il sito:
#   rilegge il referto quando tutte le aree hanno gia' parlato. Il
#   precedente e' `mars_fixes`. La differenza con quello e' che qui
#   l'import e' DURO: il catalogo dei testi e' prosa editoriale e la
#   sua assenza degrada un referto che resta vero, il piano e' dato
#   canonico e la sua assenza deve rompere, non produrre un referto
#   silenziosamente monco.
#
# ----------------------------------------------------------------------
# Il numero che il piano pubblica: RECUPERO, non penalita'
#
#   La domanda a cui il piano risponde e' "di quanto risale il
#   punteggio se chiudo questa voce". Non e' la penalita' del rilievo,
#   e confonderle e' il difetto piu' facile di tutta la fase:
#
#     recupero = R(base - penalita) - R(base)
#     con R(P) = max(0, round(100 - P))
#
#   `base` e' la somma delle penalita' dichiarate da TUTTI i rilievi
#   dell'area, `info` compresi. R() e' la stessa aritmetica che ha
#   prodotto il punteggio pubblicato — clamp e arrotondamento DENTRO il
#   conto, invece che dichiarati a parte — e questo la rende
#   verificabile: se `R(base)` non ricostruisce lo score dell'area,
#   qualcosa non torna e il piano lo dice invece di calcolare.
#
#   Due conseguenze che non sono dettagli:
#
#   - **un'area satura vale meno di quel che sembra.** Con base 108 e
#     score 0, un rilievo da 40 ne recupera 32, non 40: gli altri 8
#     pagano l'eccedenza. E uno da 8 non muove niente;
#   - **i recuperi non sono additivi.** Misurato su mars_wcag del
#     golden: 37 + 18 + 7 uno alla volta fanno 62, chiudendoli insieme
#     si guadagnano 63. Ogni voce porta `additive: False`, perche' la
#     Fase 6 (CSV) e la Fase 7 (delta) sommeranno cio' che trovano.
#
# ----------------------------------------------------------------------
# Il guadagno di citabilita': una derivata, e i suoi limiti
#
#   L'indice composito e' una media pesata di medie pesate, e i pesi si
#   rinormalizzano sui soli segnali misurati. E' lineare nei segnali,
#   quindi la derivata rispetto al punteggio di un'area e' un numero
#   solo, `k[segnale]`, e il guadagno e' `recupero * k`.
#
#   I `k` NON sono costanti: dipendono dal mercato e da QUANTI segnali
#   sono stati misurati in quella esecuzione. Misurato sui due golden:
#   `tecnica` vale 0.1885 nel referto completo (mercato eu, 7 segnali)
#   e 0.4045 in quello degradato (global, 4 segnali). Per questo ogni
#   voce porta con se' il mercato: un `index_gain` e' una proprieta'
#   dell'esecuzione, non del rilievo, e confrontarne due fra referti
#   diversi non significa niente.
#
#   La derivata NON e' il movimento che si osservera' nel referto:
#   `profilo()` arrotonda a 0.1 e l'indice arrotonda di nuovo, quindi
#   la differenza fra due indici pubblicati puo' discostarsi fino a due
#   passi (0.2). E' dichiarato, ed e' il prezzo per avere un numero
#   attribuibile alla singola voce.
#
# ----------------------------------------------------------------------
# Perche' `mars_citability` si importa
#
#   Servono quattro cose sue: PESI_ASSISTENTE, MERCATI, SEGNALI e la
#   corrispondenza area -> segnale. Sono costanti, non stato: un
#   `import` diretto le legge identiche a quelle del modulo che
#   `load_external_module` ha eseguito — verificato, gli oggetti-modulo
#   sono due ma le tabelle sono uguali. Ricopiarle qui sarebbe la
#   seconda implementazione che diverge in silenzio.
#
#   Una dipendenza pero' c'e', e va detta: il referto pubblica
#   `citability["signals"]` indicizzato per ETICHETTA italiana, non per
#   nome interno. Qui si inverte `SEGNALI` per tornare ai nomi, e la
#   Fase 9 — che traduce le etichette — romperebbe l'inversione. Non in
#   silenzio: `_segnali_interni` restituisce None su un'etichetta che
#   non riconosce, i guadagni spariscono e il piano dichiara di aver
#   ordinato con un altro criterio. Un test presidia l'inversione.
# ======================================================================

# Solo cio' su cui si interviene. `info` resta fuori: sono rilievi che
# descrivono, non difetti da chiudere.
GRAVITA_PIANO = (SEV_CRITICAL, SEV_WARNING)
_ORDINE_GRAVITA = {SEV_CRITICAL: 0, SEV_WARNING: 1}

# Le quattro corsie in cui puo' finire una voce. Servono perche' "non
# lo so" e "so che vale zero" sono opposti per chi decide lunedi'
# mattina, e un ordinamento che li mettesse insieme in fondo perderebbe
# proprio la differenza.
CORSIE = ("misurato", "bloccato", "ignoto", "nullo")
_ORDINE_CORSIA = {nome: i for i, nome in enumerate(CORSIE)}

# Quanto costa chiudere un controllo. Scala editoriale a tre livelli,
# dichiarata come tale: e' una stima di ordine di grandezza, non una
# misura, e serve a una cosa sola — riconoscere i quick win.
#
# Le chiavi sono ESATTAMENTE quelle di `mars_fixes.CATALOGO`, ed e' un
# test a pretenderlo: sono i controlli che MARS misura da se', un
# insieme chiuso che cambia solo quando lo cambiamo noi.
#
# Le tre famiglie dinamiche — `wcag.axe.*`, `sec.zap.*`, `seo.lh.*` —
# restano FUORI, tutte e tre, e il piano dichiara "sforzo non
# dichiarato". Un default "ore" sarebbe un'assenza travestita da stima,
# e per quelle famiglie l'insieme delle chiavi non e' nostro: le regole
# di axe sono oltre cento, quelle di ZAP dipendono dagli add-on
# installati, e gli audit SEO dipendono dalla versione di Lighthouse
# che si trova nel PATH — il referto ne registra la versione proprio
# perche' varia.
MINUTI, ORE, GIORNI = "minuti", "ore", "giorni"

SFORZO: Dict[str, str] = {
    # Una riga in robots.txt, un tag in <head>: si fa e si verifica
    # nella stessa mezz'ora.
    "tech.robots.missing": MINUTI,
    "tech.robots.ai_blocked": MINUTI,
    "tech.robots.ai_unmentioned": MINUTI,
    "tech.robots.self_blocked": MINUTI,
    "tech.sitemap.not_in_robots": MINUTI,
    "wcag.lang.missing": MINUTI,
    "sec.headers.hsts_missing": MINUTI,
    "sec.headers.xframe_missing": MINUTI,
    # Toccano un template o una configurazione, e vanno verificate su
    # piu' pagine.
    "tech.index.noindex": ORE,
    "tech.index.nofollow": ORE,
    "tech.index.nosnippet": ORE,
    "tech.index.unavailable_after": ORE,
    "tech.index.noarchive": ORE,
    "tech.canonical.missing": ORE,
    "tech.canonical.cross_host": ORE,
    "tech.sitemap.missing": ORE,
    "tech.sitemap.no_lastmod": ORE,
    "tech.sitemap.unreadable": ORE,
    "sd.jsonld.missing": ORE,
    "sd.jsonld.block_malformed": ORE,
    "sd.jsonld.block_empty": ORE,
    "wcag.heading.skip": ORE,
    "wcag.table.th_missing": ORE,
    "wcag.tabindex.positive": ORE,
    # CSP si applica in sola osservazione, si leggono le violazioni e
    # poi si passa all'header vero: sono giorni, e il fix lo dice.
    "sec.headers.csp_missing": GIORNI,
    # Riguardano il contenuto, una pagina alla volta: i testi
    # alternativi, le etichette dei moduli, i testi dei link.
    "wcag.img.alt_missing": GIORNI,
    "wcag.form.label_missing": GIORNI,
    "wcag.link.generic": GIORNI,
}


def _e_candidato(rilievo: dict) -> bool:
    """Vero se il rilievo va nel piano.

    Tre esclusioni, e nessuna e' un'ottimizzazione:

    - la **gravita'**: `info` descrive, non prescrive;
    - i **derivati** di `mars_citability`, che ridicono un difetto gia'
      quantificato dall'area d'origine. E' il vincolo che R41 chiede a
      ogni consumatore che AGGREGA: oggi li terrebbe fuori anche la
      sola gravita', ma quella e' una protezione incidentale — se un
      giorno un derivato nascesse `warning`, il piano lo prescriverebbe
      due volte;
    - i rilievi di **stato**, `*.status.*`, che parlano della
      scansione e non del sito. Il loro destinatario e' chi fa girare
      MARS, ed e' la stessa esclusione per cui U3.1 non da' loro un
      `fix`: un piano consegnato a un cliente che dica "installa
      Lighthouse" ha sbagliato lettore.

    Nessun filtro sulla presenza di un `fix`: un rilievo senza
    prescrizione resta un difetto da chiudere, e nasconderlo perche'
    non sappiamo dire come lo si chiude sarebbe la cosa peggiore.
    """
    if rilievo.get("severity") not in GRAVITA_PIANO:
        return False
    if (rilievo.get("params") or {}).get("derived"):
        return False
    return ".status." not in (rilievo.get("key") or "")


def punteggio_ricostruito(penalita: float) -> int:
    """R(P): il punteggio d'area che corrisponde a P punti di penalita'.

    E' la stessa aritmetica dei moduli — `max(0, round(100 - somma))` —
    scritta una volta sola perche' il piano la applica tre volte per
    voce: al punteggio di partenza, a quello di arrivo e alla loro
    differenza.
    """
    return max(0, round(100 - penalita))


def base_area(rilievi: List[dict]) -> Optional[float]:
    """La penalita' totale dichiarata da un'area, o None.

    Somma su TUTTI i rilievi che portano `params["penalty"]`, `info`
    compresi: nel golden `mars_tech` ha 40 (critico) piu' 3 (un `info`),
    e sommare i soli candidati darebbe base 40, cioe' un punteggio
    ricostruito di 60 contro il 57 pubblicato. La ricostruzione si
    romperebbe in silenzio, ed e' proprio cio' che il certificato serve
    a impedire.

    None quando nessun rilievo la dichiara: e' diverso da zero, che
    significa "misurata e nulla".
    """
    penalita = [r["params"]["penalty"] for r in rilievi
                if isinstance(r.get("params"), dict)
                and isinstance(r["params"].get("penalty"), (int, float))]
    return float(sum(penalita)) if penalita else None


def certificato_area(area: dict) -> dict:
    """Le penalita' dichiarate ricostruiscono il punteggio pubblicato?

    U4 e' il **primo consumatore** di `params["penalty"]`: fino a qui
    quel campo lo leggevano solo i test. Prima di pubblicare numeri
    che ne derivano si verifica che l'area regga, invece di assumerlo —
    e restera' vero domani, quando R36 e R37 aggiungeranno rilievi e
    R40 toccherà mars_seo.

    Sotto saturazione l'uguaglianza fra punteggi non dimostra nulla:
    con score gia' a 0 la soddisfa qualunque base sopra 100.5, da 101 a
    1000. Per questo il confronto si fa sul valore NON limitato, e
    l'eccedenza si pubblica invece di sparire dentro il `max(0, ...)`.
    """
    score = area.get("score")
    rilievi = area.get("findings") or []
    base = base_area(rilievi)
    esito = {"base": base, "score": score, "excess": None,
             "certified": False, "reason": ""}
    if base is None:
        esito["reason"] = "nessun rilievo dichiara una penalita'"
        return esito
    if not isinstance(score, (int, float)):
        esito["reason"] = "l'area non ha un punteggio"
        return esito
    esito["excess"] = round(max(0.0, base - 100.0), 4)
    if round(100 - base) == round(score):
        esito["certified"] = True
        return esito
    # Area satura: il punteggio e' zero e le penalita' lo superano. La
    # ricostruzione E' coerente — `max(0, ...)` fa il resto — ma il
    # confronto sul valore non limitato non puo' vederlo, perche' li'
    # 100 - base e' negativo. Senza questo ramo un'area satura
    # perderebbe tutti i suoi numeri proprio quando servono di piu'.
    # L'eccedenza resta pubblicata: e' cio' che spiega perche' un
    # rilievo da 40 ne recuperi 32.
    if round(score) == 0 and base >= 99.5:
        esito["certified"] = True
        return esito
    esito["reason"] = ("la ricostruzione non chiude: 100 - %.2f fa %d, "
                       "il punteggio dichiarato e' %d"
                       % (base, round(100 - base), round(score)))
    return esito


def recupero(base: float, penalita: float) -> int:
    """Di quanto risale il punteggio d'area se il rilievo e' chiuso."""
    return punteggio_ricostruito(base - penalita) - punteggio_ricostruito(base)


# ----------------------------------------------------------------------
# I coefficienti di citabilita'
# ----------------------------------------------------------------------

# Da quale modulo viene ogni segnale, invertendo `ORIGINE`. Solo i
# segnali che vengono da UN'area: `recuperabilita` nasce da due moduli
# e `answer_shaped` da un rapporto e non da un punteggio, quindi
# nessuna voce del piano puo' muoverli — e il piano lo dichiara invece
# di tacerlo.
_SEGNALE_DI_AREA: Dict[str, str] = {
    moduli[0]: segnale
    for segnale, moduli in mars_citability.ORIGINE.items()
    if len(moduli) == 1 and segnale != "answer_shaped"
}


def _segnali_interni(signals: dict) -> Optional[Dict[str, Optional[float]]]:
    """I segnali pubblicati, reindicizzati per nome interno.

    Il referto li pubblica per etichetta italiana perche' li' servono
    a essere letti. None se una etichetta non e' riconosciuta: e' cio'
    che succedera' quando la Fase 9 le tradurra', e allora i guadagni
    spariscono dichiarandolo invece di uscire sbagliati.
    """
    nomi = {etichetta: nome
            for nome, etichetta in mars_citability.SEGNALI.items()}
    esito: Dict[str, Optional[float]] = {}
    for etichetta, valore in (signals or {}).items():
        if etichetta not in nomi:
            return None
        esito[nomi[etichetta]] = valore
    return esito


def coefficienti(citability: dict) -> Optional[Tuple[dict, dict, str]]:
    """(k del composito, k per assistente, mercato), o None.

    `k[s]` e' di quanto sale l'indice composito per ogni punto di
    punteggio guadagnato dall'area che alimenta il segnale `s`. Esce
    dalla derivata della media pesata, con i pesi rinormalizzati sui
    SOLI segnali misurati — la stessa rinormalizzazione di
    `mars_citability.profilo`, che e' anche il motivo per cui questi
    numeri cambiano da un referto all'altro.

    Verificato sui due golden: i coefficienti sommano a 1.0 e
    `recupero * k` ricostruisce il movimento vero dell'indice a meno
    dell'arrotondamento.
    """
    if not isinstance(citability, dict):
        return None
    segnali = _segnali_interni(citability.get("signals") or {})
    if not segnali:
        return None
    nome_mercato = citability.get("market") or "global"
    mercato = mars_citability.MERCATI.get(nome_mercato)
    if mercato is None:
        return None
    moltiplicatori, pesi_mercato = mercato["aree"], mercato["assistenti"]
    misurati = [s for s, v in segnali.items() if v is not None]
    if not misurati:
        return None

    per_assistente: Dict[str, Dict[str, float]] = {}
    totale_mercato = 0.0
    for assistente, pesi in mars_citability.PESI_ASSISTENTE.items():
        totale = sum(pesi.get(s, 0) * moltiplicatori.get(s, 1.0)
                     for s in misurati)
        if not totale:
            # Nessun peso: l'assistente non entra nel composito, ed e'
            # la stessa condizione per cui `profilo()` restituisce None.
            continue
        per_assistente[assistente] = {
            s: pesi.get(s, 0) * moltiplicatori.get(s, 1.0) / totale
            for s in misurati}
        totale_mercato += pesi_mercato.get(assistente, 0)
    if not totale_mercato:
        return None
    composito = {
        s: sum(pesi_mercato.get(a, 0) * k[s]
               for a, k in per_assistente.items()) / totale_mercato
        for s in misurati}
    return composito, per_assistente, nome_mercato


# ----------------------------------------------------------------------
# Il piano
# ----------------------------------------------------------------------

def _corsia(penalita: Optional[float], guadagno: Optional[int],
            certificata: bool) -> Tuple[str, str]:
    """(corsia, motivo) di una voce."""
    if not certificata or penalita is None:
        return ("ignoto", "recupero non dichiarato: %s"
                % ("la penalita' non e' calcolabile per questo controllo"
                   if certificata
                   else "il punteggio dell'area non si ricostruisce"))
    if penalita == 0:
        return ("nullo", "in questa esecuzione il controllo non entra nel "
                         "punteggio dell'area")
    if guadagno == 0:
        return ("bloccato", "il punteggio dell'area e' gia' a zero: "
                            "questa penalita' non lo muove")
    return ("misurato", "")


def _sforzo(rilievo: dict) -> Optional[str]:
    """Il livello di sforzo, o None se non lo dichiariamo."""
    return SFORZO.get(rilievo.get("key") or "")


def build_remediation(referto: dict) -> List[dict]:
    """Il piano di interventi, ordinato.

    Ordine: `(gravita, corsia, -index_gain, -recupero, -penalita,
    -peso, key)`.

    La **gravita' domina**, e resta cosi' anche quando una voce critica
    non muove il punteggio: un'immagine senza alternativa testuale e'
    un difetto grave comunque, e quale strumento la prezzi in questa
    esecuzione e' un fatto nostro, non suo. Il perche' del suo zero lo
    dice la corsia.

    La **corsia viene prima dei numeri** perche' i numeri possono
    mancare: separa le voci misurate da quelle bloccate, ignote o
    nulle, cosi' nessun confronto numerico incontra un None.

    `key` chiude la chiave e non e' un ornamento: senza, due voci
    pari-merito si scambierebbero al variare dell'ordine di produzione
    e i golden diventerebbero instabili.
    """
    aree = referto.get("areas") or []
    k_composito, k_assistenti, mercato = (None, None, None)
    coeff = coefficienti(referto.get("citability") or {})
    if coeff:
        k_composito, k_assistenti, mercato = coeff

    voci: List[dict] = []
    for area in aree:
        modulo = area.get("module") or ""
        cert = certificato_area(area)
        base = cert["base"]
        segnale = _SEGNALE_DI_AREA.get(modulo)
        for rilievo in area.get("findings") or []:
            if not _e_candidato(rilievo):
                continue
            params = rilievo.get("params") or {}
            penalita = params.get("penalty")
            if not isinstance(penalita, (int, float)):
                penalita = None
            guadagno = prima = dopo = None
            if cert["certified"] and penalita is not None:
                prima = punteggio_ricostruito(base)
                dopo = punteggio_ricostruito(base - penalita)
                guadagno = dopo - prima
            corsia, motivo = _corsia(penalita, guadagno, cert["certified"])

            indice = None
            profili = None
            if guadagno and k_composito and segnale in k_composito:
                indice = round(guadagno * k_composito[segnale], 2)
                profili = {a: round(guadagno * k[segnale], 2)
                           for a, k in k_assistenti.items()
                           if segnale in k}

            sforzo = _sforzo(rilievo)
            voci.append({
                "key": rilievo.get("key") or "",
                "area": modulo,
                "area_label": area.get("label") or modulo,
                "severity": rilievo.get("severity"),
                "title": rilievo.get("title") or "",
                "fix": rilievo.get("fix") or "",
                "example": rilievo.get("example") or "",
                # Il link alla documentazione della regola, non una
                # pagina: quelle viaggiano dentro `params["urls"]`, che
                # la voce copia insieme al resto (R47).
                "doc_url": rilievo.get("doc_url") or "",
                # I `params` viaggiano con la voce come ci viaggiano
                # titolo e fix, e per la stessa ragione: la voce e' una
                # COPIA del rilievo, non un rimando. Senza, un titolo
                # come «%(campi)d campi di modulo senza etichetta» non
                # si puo' tradurre — `mars_i18n.finding_texts` risolve
                # il template sui params, non li trova e ripiega
                # sull'italiano, in silenzio (misurato chiudendo U9.2).
                "params": dict(rilievo.get("params") or {}),
                "penalty": penalita,
                "recovery": guadagno,
                "score_before": prima,
                "score_after": dopo,
                "index_gain": indice,
                "profile_gains": profili,
                "market": mercato,
                "effort": sforzo,
                # Tre condizioni, non due. La terza — un recupero
                # calcolabile e maggiore di zero — non e' pignoleria:
                # nel golden completo due rilievi critici di mars_wcag
                # hanno penalita' 0.0 perche' in quel ramo il punteggio
                # lo fa axe, e senza il terzo termine il piano
                # aprirebbe con due vittorie rapide che lasciano l'area
                # dov'era.
                "quick_win": (rilievo.get("severity") == SEV_CRITICAL
                              and sforzo == MINUTI
                              and bool(guadagno)),
                "lane": corsia,
                "lane_reason": motivo,
                # I recuperi non si sommano, e nemmeno i guadagni che
                # ne derivano. Sta nel DATO e non solo nella resa,
                # perche' il CSV della Fase 6 e il confronto della Fase
                # 7 sommeranno cio' che trovano.
                "additive": False,
                "certified": cert["certified"],
            })

    voci.sort(key=lambda v: (
        _ORDINE_GRAVITA.get(v["severity"], 9),
        _ORDINE_CORSIA.get(v["lane"], 9),
        -(v["index_gain"] or 0.0),
        -(v["recovery"] or 0),
        -(v["penalty"] or 0.0),
        v["key"],
    ))
    for numero, voce in enumerate(voci, 1):
        voce["priority"] = numero
    return voci


def riepilogo(piano: List[dict], referto: dict) -> dict:
    """I conteggi della testata, calcolati e mai cablati.

    `aree_nel_piano` si conta a runtime: le aree che possono
    contribuire sono al massimo cinque, non nove, perche'
    `mars_lexical` e `mars_semantic` non producono rilievi e i rilievi
    di `mars_citability` e `mars_llm_judge` sono per costruzione tutti
    `info`. Stampare un numero cablato in un referto consegnato a un
    cliente sarebbe una dichiarazione falsa in una riga scritta per
    essere onesta.
    """
    aree = referto.get("areas") or []
    rappresentate = sorted({v["area"] for v in piano})
    escluse = [a.get("module") for a in aree
               if a.get("module") not in rappresentate]
    return {
        "total": len(piano),
        "critical": sum(1 for v in piano if v["severity"] == SEV_CRITICAL),
        "warning": sum(1 for v in piano if v["severity"] == SEV_WARNING),
        "quick_wins": sum(1 for v in piano if v["quick_win"]),
        "by_lane": {corsia: sum(1 for v in piano if v["lane"] == corsia)
                    for corsia in CORSIE},
        "no_effort": sum(1 for v in piano if v["effort"] is None),
        "areas_covered": len(rappresentate),
        "areas_total": len(aree),
        "areas_excluded": escluse,
        # Nessun "guadagno totale": i recuperi non sono additivi, e una
        # somma sarebbe il numero piu' letto e il piu' sbagliato del
        # referto.
        "additive": False,
    }
