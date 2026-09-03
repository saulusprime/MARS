/* MARS Beacon — landing. JavaScript vanilla, nessuna dipendenza.
 *
 * Due cose, e nessuna delle due e' decorativa:
 *   1. l'anteprima del referto, che passa fra due esecuzioni dello stesso
 *      sito di esempio per mostrare come il prodotto racconta un CONFRONTO;
 *   2. la validazione del modulo, con i messaggi accanto al campo e un
 *      riassunto in testa che riceve il fuoco.
 *
 * La pagina resta leggibile e il modulo resta inviabile senza JavaScript:
 * l'HTML porta gia' i valori della prima esecuzione e i vincoli
 * `required`. Questo file migliora, non abilita. */
(function () {
  "use strict";

  /* ================================================================
   * 1. L'anteprima del referto
   * ================================================================
   * I numeri sono INVENTATI e la pagina lo dichiara. La geometria no:
   * r=56 come nel referto vero, quindi la circonferenza e' 2*pi*56 =
   * 351,86 e l'offset e' la parte non coperta. Un disegno che somigli a
   * un quadrante non e' la stessa cosa di un quadrante. */
  var CIRCONFERENZA = 351.86;

  /* La scala dichiarata del referto: critico sotto 50, da migliorare
   * fino a 89, buono da 90. Vive qui una volta sola perche' decide sia
   * il colore sia la parola, e due copie divergerebbero. */
  function classe(voto) {
    if (voto === null || voto === undefined) { return "neutro"; }
    if (voto >= 90) { return "ok"; }
    if (voto >= 50) { return "warn"; }
    return "bad";
  }

  function verdetto(voto) {
    if (voto >= 90) { return "buono"; }
    if (voto >= 50) { return "da migliorare"; }
    return "critico";
  }

  var AREE = [
    { nome: "Tecnica", nota: "" },
    { nome: "SEO", nota: "Lighthouse 13.4.1" },
    { nome: "Prestazioni", nota: "desktop" },
    { nome: "Lessicale", nota: "BM25" },
    { nome: "Semantica", nota: "proxy dichiarato" },
    { nome: "Dati strutturati", nota: "" },
    { nome: "Accessibilità", nota: "axe-core 4.13" },
    { nome: "Sicurezza", nota: "ZAP (passiva)" },
    { nome: "Citabilità IA", nota: "stima" },
    { nome: "Giudizio LLM", nota: "opinione" }
  ];

  /* Due esecuzioni dello stesso dominio di esempio. La seconda e' quella
   * che un cliente vede dopo aver lavorato sul piano del referto: e'
   * questo il confronto che il prodotto sa raccontare. */
  var ESECUZIONI = [
    {
      meta: "2026-08-04T09:12:00+0000 · 24 pagine trovate via sitemap · " +
            "301 chunk · mercato eu · v2.29.0",
      complessivo: 51,
      delta: null,
      voti: [74, 96, 88, 69, 77, 82, 58, 34, 55, 45],
      conteggi: { critici: 1, avvertenze: 11, informativi: 14 },
      primi: [
        { g: "bad", t: "Content Security Policy (CSP) Header Not Set" },
        { g: "warn", t: "Gli elementi devono soddisfare le soglie minime " +
                        "del rapporto di contrasto di colore" },
        { g: "warn", t: "3/24 pagine escluse dagli indici (noindex o none, " +
                        "in meta robots o X-Robots-Tag)" }
      ],
      wcag: 58
    },
    {
      meta: "2026-09-03T08:40:00+0000 · 26 pagine trovate via sitemap · " +
            "348 chunk · mercato eu · v2.29.0",
      complessivo: 73,
      delta: 22,
      voti: [91, 100, 92, 78, 84, 95, 86, 71, 68, 61],
      conteggi: { critici: 0, avvertenze: 4, informativi: 16 },
      primi: [
        { g: "warn", t: "2/26 pagine sotto le 300 parole recuperabili" },
        { g: "warn", t: "Sub Resource Integrity Attribute Missing" },
        { g: "warn", t: "L'INP non si misura in laboratorio: non misurato" }
      ],
      wcag: 86
    }
  ];

  function quadrante(nome, voto, nota, grande) {
    var g = classe(voto);
    var misurato = voto !== null && voto !== undefined;
    var offset = misurato
      ? (CIRCONFERENZA * (1 - Math.min(voto, 100) / 100)).toFixed(2)
      : CIRCONFERENZA;
    var etichetta = misurato
      ? nome + ": " + voto + " su 100"
      : nome + ": non misurato";
    /* Un <li> e non un <div>: il contenitore e' l'elenco che fa da
     * ripiego senza JavaScript, e infilarci dei <div> darebbe markup non
     * valido — su una pagina che vende un audit di accessibilita'. */
    var div = document.createElement("li");
    div.className = "quadrante " + g + (grande ? " grande" : "");
    div.innerHTML =
      '<svg viewBox="0 0 120 120" role="img" aria-label="' + etichetta + '">' +
      '<circle class="anello" cx="60" cy="60" r="56" fill="none" ' +
      'stroke-width="9"/>' +
      '<circle class="arco" cx="60" cy="60" r="56" fill="none" ' +
      'stroke="currentColor" stroke-width="9" stroke-linecap="round" ' +
      'stroke-dasharray="' + CIRCONFERENZA + '" stroke-dashoffset="' +
      offset + '" transform="rotate(-90 60 60)"/>' +
      '<text class="valore" x="60" y="60" text-anchor="middle" ' +
      'dominant-baseline="central" fill="currentColor">' +
      (misurato ? voto : "–") + "</text></svg>" +
      '<p class="nome"></p>';
    /* Il nome via textContent e non nell'HTML: l'anteprima e' nostra, ma
     * l'abitudine di comporre markup con del testo e' esattamente come
     * si finisce a iniettare il contenuto di un sito analizzato. */
    div.querySelector(".nome").textContent = nome;
    if (nota) {
      var n = document.createElement("span");
      n.className = "nota";
      n.textContent = nota;
      div.querySelector(".nome").appendChild(document.createElement("br"));
      div.querySelector(".nome").appendChild(n);
    }
    return div;
  }

  function disegna(indice) {
    var run = ESECUZIONI[indice];
    if (!run) { return; }

    document.getElementById("rp-meta").textContent = run.meta;

    /* Complessivo */
    var box = document.getElementById("rp-complessivo");
    var g = classe(run.complessivo);
    box.className = "quadrante grande " + g;
    var arco = box.querySelector(".arco");
    arco.setAttribute(
      "stroke-dashoffset",
      (CIRCONFERENZA * (1 - run.complessivo / 100)).toFixed(2)
    );
    box.querySelector(".valore").textContent = run.complessivo;
    box.querySelector("svg").setAttribute(
      "aria-label", "Complessivo: " + run.complessivo + " su 100"
    );

    var v = document.getElementById("rp-verdetto");
    v.className = "verdetto " + g;
    v.textContent = verdetto(run.complessivo);

    /* La variazione: il simbolo accanto al colore, sempre. */
    var d = document.getElementById("rp-delta");
    if (run.delta === null) {
      d.hidden = true;
      d.textContent = "";
    } else {
      d.hidden = false;
      d.className = "delta " + (run.delta >= 0 ? "ok" : "bad");
      d.innerHTML = "";
      d.appendChild(document.createTextNode(
        (run.delta >= 0 ? "▲ +" : "▼ ") + run.delta + " "
      ));
      var r = document.createElement("span");
      r.className = "rispetto";
      r.textContent = "rispetto all'esecuzione precedente";
      d.appendChild(r);
    }

    /* Le quote: la barra e i tre conteggi dicono la stessa cosa, e la
     * barra da sola non direbbe nulla a chi non la vede. */
    var c = run.conteggi;
    var totale = c.critici + c.avvertenze + c.informativi;
    var quota = totale ? ((c.critici + c.avvertenze) / totale) * 100 : 0;
    var fetta = document.getElementById("rp-fetta");
    fetta.style.width = quota.toFixed(1) + "%";
    fetta.className = "fetta " + (c.critici ? "bad" : "warn");
    document.getElementById("rp-conteggi").innerHTML = "";
    [[c.critici, c.critici === 1 ? "critico" : "critici"],
     [c.avvertenze, c.avvertenze === 1 ? "avvertenza" : "avvertenze"],
     [c.informativi, "informativi"]].forEach(function (voce, i) {
      var p = document.getElementById("rp-conteggi");
      if (i) { p.appendChild(document.createTextNode(" · ")); }
      var b = document.createElement("b");
      b.textContent = voce[0];
      p.appendChild(b);
      p.appendChild(document.createTextNode(" " + voce[1]));
    });

    /* Da dove cominciare */
    var ol = document.getElementById("rp-primi");
    ol.innerHTML = "";
    run.primi.forEach(function (voce) {
      var li = document.createElement("li");
      li.className = voce.g;
      li.textContent = voce.t;
      ol.appendChild(li);
    });

    /* I dieci quadranti */
    var griglia = document.getElementById("rp-quadranti");
    /* Si cambia anche la classe: l'elenco di ripiego e la griglia dei
     * quadranti hanno regole diverse, e lasciare quella del ripiego
     * disporrebbe i quadranti come righe di testo. */
    griglia.className = "quadranti";
    griglia.innerHTML = "";
    AREE.forEach(function (area, i) {
      griglia.appendChild(quadrante(area.nome, run.voti[i], area.nota, false));
    });

    /* Il punteggio nella scheda d'area, che deve concordare col quadrante:
     * due numeri sulla stessa area che si contraddicono sono il difetto
     * peggiore di un referto. */
    var pill = document.getElementById("rp-wcag");
    pill.className = "pill " + classe(run.wcag);
    pill.textContent = run.wcag;
  }

  var bottoni = Array.prototype.slice.call(
    document.querySelectorAll(".commuta button")
  );
  bottoni.forEach(function (b) {
    b.addEventListener("click", function () {
      bottoni.forEach(function (altro) {
        altro.classList.remove("attivo");
        altro.setAttribute("aria-pressed", "false");
      });
      b.classList.add("attivo");
      b.setAttribute("aria-pressed", "true");
      disegna(parseInt(b.getAttribute("data-run"), 10));
    });
  });

  if (document.getElementById("rp-quadranti")) {
    disegna(0);
  }

  /* ================================================================
   * 2. Il modulo
   * ================================================================ */

  /* L'email deve essere AZIENDALE: e' un requisito del prodotto, non un
   * capriccio, perche' un lead senza dominio non si qualifica. L'elenco
   * e' dichiarato e corto per scelta: indovinare che un dominio sia
   * "personale" da una regola generale produrrebbe falsi rifiuti, e un
   * rifiuto sbagliato costa piu' di un lead in piu' da guardare. */
  var DOMINI_PERSONALI = [
    "gmail.com", "googlemail.com", "outlook.com", "outlook.it",
    "hotmail.com", "hotmail.it", "live.com", "live.it", "msn.com",
    "yahoo.com", "yahoo.it", "icloud.com", "me.com", "aol.com",
    "libero.it", "virgilio.it", "alice.it", "tin.it", "tiscali.it",
    "fastwebnet.it", "email.it", "inwind.it", "protonmail.com", "proton.me",
    "gmx.com", "yandex.com", "mail.com", "zoho.com"
  ];

  var form = document.getElementById("registrazione");
  if (!form) { return; }

  var REGOLE = [
    ["azienda", function (v) {
      if (!v.trim()) { return "Indica la ragione sociale."; }
      if (v.trim().length < 2) { return "La ragione sociale è troppo corta."; }
      return "";
    }],
    ["sito", function (v) {
      if (!v.trim()) { return "Indica il sito da analizzare."; }
      /* Si valida con il parser del browser invece di una regex: un URL
       * e' dato ostile anche qui, e una regex scritta a mano su questo
       * ha una storia di casi limite — IPv6 fra le quadre, per dirne
       * uno — che nessuno vuole riscrivere. */
      var u;
      try { u = new URL(v.trim()); } catch (e) {
        return "Serve un indirizzo completo, per esempio " +
               "https://www.esempio.it";
      }
      if (u.protocol !== "http:" && u.protocol !== "https:") {
        return "Sono ammessi solo indirizzi http:// o https://";
      }
      if (u.hostname.indexOf(".") === -1) {
        return "L'indirizzo non contiene un dominio valido.";
      }
      return "";
    }],
    ["nome", function (v) {
      if (!v.trim()) { return "Indica nome e cognome."; }
      return "";
    }],
    ["ruolo", function (v) {
      if (!v) { return "Scegli il tuo ruolo."; }
      return "";
    }],
    ["email", function (v) {
      var s = v.trim().toLowerCase();
      if (!s) { return "Indica l'email aziendale."; }
      /* Un solo @, qualcosa prima, un dominio con un punto dopo. Non si
       * pretende di validare RFC 5322: quello lo fa il messaggio che
       * arriva o non arriva. */
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s)) {
        return "Questo indirizzo non sembra valido.";
      }
      var dominio = s.split("@")[1];
      if (DOMINI_PERSONALI.indexOf(dominio) !== -1) {
        return "Serve un indirizzo aziendale: " + dominio +
               " è un provider personale.";
      }
      return "";
    }],
    ["telefono", function (v) {
      var s = v.replace(/[\s./()-]/g, "");
      if (!s) { return "Indica un numero di telefono."; }
      if (!/^\+?\d{6,15}$/.test(s)) {
        return "Il numero non sembra valido: cifre, eventualmente con +.";
      }
      return "";
    }],
    ["termini", function (_, el) {
      return el.checked ? "" : "Devi accettare i termini di servizio.";
    }],
    ["privacy", function (_, el) {
      return el.checked ? "" : "Devi accettare l'informativa privacy.";
    }],
    ["responsabilita", function (_, el) {
      return el.checked
        ? ""
        : "Senza questa dichiarazione l'analisi non può partire.";
    }]
  ];

  function mostraErrore(id, messaggio) {
    var el = document.getElementById(id);
    var p = document.getElementById("e-" + id);
    if (messaggio) {
      el.setAttribute("aria-invalid", "true");
      p.textContent = messaggio;
      p.hidden = false;
    } else {
      el.removeAttribute("aria-invalid");
      p.textContent = "";
      p.hidden = true;
    }
  }

  function controlla(id, regola) {
    var el = document.getElementById(id);
    var messaggio = regola(el.value, el);
    mostraErrore(id, messaggio);
    return messaggio;
  }

  /* Si valida all'uscita dal campo e non a ogni tasto: dire «email non
   * valida» a chi ha appena scritto la prima lettera e' rumore. Ma un
   * errore GIA' mostrato si toglie appena rientra, altrimenti resta
   * rosso mentre la persona lo sta correggendo. */
  REGOLE.forEach(function (coppia) {
    var id = coppia[0];
    var regola = coppia[1];
    var el = document.getElementById(id);
    if (!el) { return; }
    var evento = el.type === "checkbox" ? "change" : "blur";
    el.addEventListener(evento, function () { controlla(id, regola); });
    el.addEventListener("input", function () {
      if (el.getAttribute("aria-invalid") === "true") {
        controlla(id, regola);
      }
    });
  });

  var riassunto = document.getElementById("riassunto-errori");

  form.addEventListener("submit", function (evento) {
    evento.preventDefault();
    var guasti = [];
    REGOLE.forEach(function (coppia) {
      var messaggio = controlla(coppia[0], coppia[1]);
      if (messaggio) { guasti.push([coppia[0], messaggio]); }
    });

    if (guasti.length) {
      /* Il riassunto in testa esiste per chi non vede il campo rosso:
       * ogni voce e' un link all'input che l'ha prodotta, e il riquadro
       * prende il fuoco perche' un `role="alert"` fuori dallo schermo
       * viene letto e poi perso. */
      riassunto.innerHTML = "";
      var titolo = document.createElement("p");
      titolo.textContent = guasti.length === 1
        ? "C'è un campo da correggere:"
        : "Ci sono " + guasti.length + " campi da correggere:";
      riassunto.appendChild(titolo);
      var ul = document.createElement("ul");
      guasti.forEach(function (guasto) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#" + guasto[0];
        a.textContent = guasto[1];
        a.addEventListener("click", function (e) {
          e.preventDefault();
          document.getElementById(guasto[0]).focus();
        });
        li.appendChild(a);
        ul.appendChild(li);
      });
      riassunto.appendChild(ul);
      riassunto.hidden = false;
      riassunto.focus();
      return;
    }

    riassunto.hidden = true;

    /* Nessuna rete: e' una dimostrazione, e prometterlo e poi spedire
     * altrove sarebbe la bugia peggiore di una pagina che vende
     * onesta' metodologica. I dati restano in questa scheda del
     * browser e servono alla pagina successiva.
     *
     * `sessionStorage` e non `localStorage`: muoiono con la scheda. E
     * l'accesso e' fra try/catch perche' in navigazione privata o con i
     * dati dei siti bloccati la sola LETTURA della proprieta' solleva. */
    var dati = {
      azienda: document.getElementById("azienda").value.trim(),
      sito: document.getElementById("sito").value.trim(),
      nome: document.getElementById("nome").value.trim(),
      ruolo: document.getElementById("ruolo").value,
      email: document.getElementById("email").value.trim(),
      telefono: document.getElementById("telefono").value.trim()
    };
    try {
      window.sessionStorage.setItem("mars.lead", JSON.stringify(dati));
    } catch (e) {
      /* Senza archivio la pagina successiva mostra il generico: si
       * degrada, non si rompe. */
    }
    window.location.href = "servizio.html";
  });
}());
