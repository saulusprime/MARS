#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARS Beacon — Meta-fusion, Accessibility, Ranking & Security Audit.
Audit SEO, RRF (Reciprocal Rank Fusion), WCAG e WAPT
Copyright 2026 Paolo Pierno
Licenza: Apache 2.0

I pesi e le soglie che decidono un punteggio, in un posto solo.

Qui sta ciò il cui valore è una **scelta**, non un fatto: quanto costa
un rilievo grave, sotto quante parole una pagina è sottile, quanto pesa
un'area nel complessivo. Restano fuori gli elenchi che descrivono il
mondo — quali crawler IA esistono, quali header di sicurezza contano —
perché quelli non sono tarabili e vivono meglio accanto al codice che
li interroga.

**Le ragioni stanno qui, con i valori.** Spostare un numero lontano dal
commento che lo giustifica lo renderebbe arbitrario, ed è il difetto
che questo file esiste per non introdurre: chi vuole sapere come misura
MARS legge questo file, non dieci.

**Non è un file di configurazione**, ed è deliberato (I8). Un valore
letto a runtime da un file esterno renderebbe ogni punteggio
condizionato a un file non versionato, e il referto dovrebbe dichiarare
con quale configurazione ha girato — è il precedente di `--rrf-k` (I3).
Nessuno ha mai avuto bisogno di tarare un peso senza toccare il codice;
il giorno che servisse, questo modulo è il posto da cui sovrascrivere, e
la chiave `thresholds` del referto — oggi `null` — è dove andrebbe
dichiarato con quali soglie l'audit ha girato.

**Le tabelle sono condivise per riferimento**: un test che muta
`PENALITA` la muta per tutte e tre le aree che la leggono.
"""

from __future__ import annotations

from typing import Dict, Tuple

# ----------------------------------------------------------------------
# La scala editoriale "mars"
# ----------------------------------------------------------------------

# Penalità per CONTROLLO, condivisa da `mars_tech`, `mars_lexical` e
# `mars_semantic`. È la stessa scala e non tre scale uguali:
# `normalizza_severita` traduce la parola, questa tabella la prezza, e
# due aree che dicono "grave" devono togliere lo stesso.
#
# Sostituisce il vecchio `100 - len(issues) * 15`, che dava lo stesso
# peso a un noindex sull'intero sito e a un lastmod mancante.
#
# Fisse, **non moltiplicate per le occorrenze**: un rilievo è un
# controllo, e su un sito da cinquanta pagine il solo `lex.words.thin`
# saturerebbe il punteggio da solo. Quante volte il difetto ricorra lo
# dicono i `params`, che è la stessa separazione di R47 fra il
# conteggio e il luogo.
#
# Fino a I8 era scritta tre volte, identica, con un commento che
# diceva «ripetuta e non importata perché i moduli sono plugin e non si
# importano fra loro». La ragione vale fra plugin, non verso un modulo
# condiviso: tutti e dieci i moduli d'area importano già da `mars_core`.
PENALITA: Dict[str, int] = {"critico": 40, "grave": 20,
                            "medio": 8, "lieve": 3}

# Penalità di una gravità che non conosciamo, sulla scala qui sopra.
# Non è teorica: se un giorno si aggiungesse un livello e si
# dimenticasse la tabella, il rilievo peserebbe 5 invece di sparire.
PENALITA_IGNOTA = 5

# Il peso di un rilievo è una scala CHIUSA, non un float libero. Serve
# a conservare la granularità che le quattro severità perdono:
# `mars_tech` distingue "grave" da "medio", axe "serious" da
# "moderate", e senza il peso i due livelli collasserebbero
# indistinguibili. Dichiararla chiusa evita che compaia un 1.7 e
# l'ordinamento del piano diventi illeggibile.
WEIGHTS: Tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)

# ----------------------------------------------------------------------
# Penalità proprie di un'area
# ----------------------------------------------------------------------

# Dati strutturati, penalità per OCCORRENZA — non per controllo, a
# differenza della scala editoriale. Sono quelle di sempre: il
# punteggio non è cambiato con l'adeguamento, e i test lo verificano.
PENALITA_SCHEMA: Dict[str, int] = {"missing": 50, "malformed": 10,
                                   "empty": 5}

# Accessibilità, penalità per gravità axe. Scelta editoriale,
# dichiarata come tale.
PESI_AXE: Dict[str, int] = {"critical": 25, "serious": 12,
                            "moderate": 5, "minor": 2}

# Quanto costa un rilievo statico WCAG NEL SOLO ramo di ripiego: è il
# `100 - len(statici) * 12` di sempre. Nel ramo axe i controlli statici
# non entrano nel punteggio, che viene dalle violazioni, quindi la loro
# penalità lì è zero — e dirlo conta, perché il piano di interventi
# calcola i guadagni proprio da quel numero.
PENALITA_STATICA = 12

# Sicurezza, penalità per livello di rischio ZAP. Scelta editoriale
# dichiarata: non sono calibrate su un corpus di scansioni reali, e
# finché non lo saranno vanno lette come un ordinamento, non come una
# misura.
ZAP_PENALTIES: Dict[str, int] = {"High": 25, "Medium": 10,
                                 "Low": 3, "Informational": 0}

# Penalità di un livello di rischio che ZAP introducesse e noi non
# conoscessimo: un livello nuovo peserebbe 2 invece di sparire.
#
# Da sapere: la stessa gravità ignota, passata a
# `normalizza_severita("zap", ...)`, degrada a (info, 1.0). Un rischio
# sconosciuto esce quindi come rilievo `info` che però costa punti. Le
# due tabelle restano in file diversi — questa qui, la scala in
# `mars_core` — e chi ne aggiornasse una sola non romperebbe nulla:
# c'è un test che verifica che coprano gli stessi livelli.
PENALITA_IGNOTA_ZAP = 2

# La soglia oltre la quale un audit Lighthouse è rompi-categoria, e non
# è arbitraria. Nella categoria SEO Lighthouse assegna peso 1 a ogni
# audit tranne due: `is-crawlable` pesa 93/23 (~4,04) — e il commento
# nel suo default-config.js dice perché, è calibrato perché quel solo
# fallimento faccia fallire l'intera categoria (>=31% del punteggio) —
# mentre gli audit manuali pesano 0. Una soglia a 3 separa quindi
# esattamente ciò che Lighthouse stesso considera rompi-categoria, e lo
# zero esattamente ciò che non è misurato.
LH_PESO_CRITICO = 3.0

# ----------------------------------------------------------------------
# I pesi del punteggio complessivo
# ----------------------------------------------------------------------

# I due segnali derivati pesano una volta e mezza un'area: non vengono
# da uno strumento esterno ma dal CONFRONTO fra i due recuperatori, che
# è la domanda del progetto — un passaggio verrebbe davvero scelto da
# una ricerca ibrida?
PESO_AREA = 1.0
PESO_SEGNALE_DERIVATO = 1.5

# ----------------------------------------------------------------------
# Le soglie editoriali
# ----------------------------------------------------------------------

# Sotto quante parole una pagina è troppo sottile perché i suoi termini
# raggiungano una frequenza che BM25 possa valorizzare: la formula
# normalizza la frequenza sulla lunghezza del documento, quindi due
# paragrafi competono male con una pagina che tratta lo stesso tema per
# esteso. È prassi editoriale e non uno standard — per questo il numero
# viaggia nei `params` del rilievo: un referto che dica "sotto la
# soglia" senza dire quale afferma una misura che il lettore non può
# rifare.
SOGLIA_PAROLE = 300

# Quante parole deve avere un passaggio perché il suo essere in forma
# di risposta conti: sotto, i segnali interrogativi sono rumore.
MIN_PAROLE = 40

# Sotto questo numero di passaggi il sito offre poche occasioni di
# comparire in una lista di risultati: nella somma RRF il numero di
# chunk pertinenti è il moltiplicatore, e venti è il punto sotto il
# quale un sito non ha abbastanza superficie perché la fusione dica
# qualcosa. Soglia editoriale, e viaggia nei `params`.
SOGLIA_CHUNK = 20

# Sotto quale punteggio un segnale di citabilità si dichiara debole.
# Soglia editoriale, nel codice da C1: ha un nome perché entra anche
# nei rilievi — un `cit.sicurezza.weak` che viaggi da solo nel piano o
# in un catalogo di traduzione deve poter dire sotto quale soglia lo
# sia.
SOGLIA_DEBOLE = 60

# La quota di passaggi in forma di risposta sotto la quale l'area
# semantica lo dichiara. **È lo stesso numero di `SOGLIA_DEBOLE`, e non
# per caso**: sullo stesso valore nasce `cit.answer_shaped.weak`, e con
# due soglie diverse il referto direbbe "segnale debole" accanto a
# un'area che non ha nulla da segnalare, senza che alcun errore lo
# riveli. Fino a I8 stavano in due file e a tenerle insieme c'era un
# test; ora sono un valore solo, e il test presidia che nessuno dei due
# moduli torni a scriversi il proprio.
SOGLIA_ANSWER_SHAPED = SOGLIA_DEBOLE

# Soglie e colori del verdetto, adottati da Lighthouse perché il
# referto gli somigli: chi legge entrambi non deve tradurre due scale
# diverse. ATTENZIONE: la scala precedente di MARS era 80/50; questa è
# 90/50, quindi lo stesso punteggio può cambiare colore rispetto ai
# referti generati prima. Il colore è una convenzione, il numero no.
SOGLIA_BUONO = 90
SOGLIA_MEDIO = 50
