/* =====================================================================
   M.A.R.S. — landing page. JavaScript vanilla, nessuna dipendenza.
   I dati dei profili di citabilita' sono quelli veri di
   mars_citability.py: pesi per assistente, pesi di mercato e il solo
   moltiplicatore attivo (accessibilita' per il mercato UE).
   Ogni animazione e' subordinata a prefers-reduced-motion.
   ===================================================================== */
(function () {
  'use strict';

  var motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  function reduced() { return motionQuery.matches; }

  /* ---------------- menu ---------------- */
  var toggle = document.getElementById('nav-toggle');
  var menu = document.getElementById('nav-menu');

  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('open')) {
        menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  /* ---------------- rivelazione allo scorrimento ---------------- */
  var revealables = document.querySelectorAll(
    '.card, .area, .step, .limits li, .hero-card, .report-mock, .assistants, .rrf');

  if (!reduced() && 'IntersectionObserver' in window) {
    Array.prototype.forEach.call(revealables, function (el, i) {
      el.classList.add('reveal');
      el.style.transitionDelay = (Math.min(i % 6, 5) * 55) + 'ms';
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    Array.prototype.forEach.call(revealables, function (el) { io.observe(el); });
  }

  /* ---------------- il referto d'esempio che si compila ----------------
     Barre e punteggi partono da zero, restano fermi un secondo e poi
     salgono insieme fino ai valori del markup.

     Lo zero delle barre lo tiene il CSS, non questo script, e non e' un
     vezzo: `app.js` e' `defer`, quindi gira dopo l'analisi del documento,
     e fra l'analisi e la sua esecuzione il browser puo' avere gia'
     disegnato un fotogramma. Azzerare le larghezze da qui e' una corsa
     con quel fotogramma, e a perderla si vedono le barre gia' piene —
     misurata: su cinque caricamenti identici, uno la perdeva.

     I numeri invece stanno nel testo e solo JavaScript puo' toccarli.
     Li si azzera subito — il valore finale e' nel markup, e' quello che
     vede chi non ha JavaScript — e li si fa salire su `animationstart`
     della prima barra: quell'evento scocca a ritardo scaduto, cosi'
     cifre e barre partono insieme senza che lo script debba indovinare
     l'orologio del foglio di stile.
     -------------------------------------------------------------------- */
  var counters = document.querySelectorAll('[data-count]');
  var barre = document.querySelectorAll('.card-bars .bar i');
  var ATTESA = 1000;   // deve combaciare con il ritardo in styles.css

  /* La gravita' segue il punteggio a gradini di 10 punti: 0-10 none,
     10-20 verybad, ... 90-100 ok. La classe sta gia' nel markup, per chi
     non ha JavaScript; qui la si riallinea al valore perche' cambiare un
     punteggio senza cambiare la classe non lasci una barra del colore
     sbagliato. */
  var GRADINI = ['none', 'verybad', 'bad', 'notsobad', 'hotwarn',
                 'verywarn', 'warn', 'semiok', 'quasiok', 'ok'];

  function classifica() {
    Array.prototype.forEach.call(barre, function (el) {
      var v = parseFloat(el.style.getPropertyValue('--w'));
      if (isNaN(v)) { return; }
      GRADINI.forEach(function (g) { el.classList.remove(g); });
      el.classList.add(GRADINI[Math.max(0, Math.min(9, Math.floor(v / 10)))]);
    });
  }

  function contaFinoA(el, durata) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target)) { return; }

    var start = null;
    function frame(ts) {
      if (start === null) { start = ts; }
      var p = Math.min((ts - start) / durata, 1);
      // easeOutCubic: parte veloce e si posa, invece di finire di scatto
      el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) { requestAnimationFrame(frame); }
    }
    requestAnimationFrame(frame);
  }

  var salito = false;
  function sali() {
    if (salito) { return; }
    salito = true;
    Array.prototype.forEach.call(counters, function (el, i) {
      contaFinoA(el, i === 0 ? 1250 : 850);
    });
  }

  if (counters.length) {
    classifica();
    if (reduced()) {
      Array.prototype.forEach.call(counters, function (el) {
        el.textContent = el.getAttribute('data-count');
      });
    } else {
      Array.prototype.forEach.call(counters, function (el) { el.textContent = '0'; });
      if (barre.length) {
        barre[0].addEventListener('animationstart', sali);
      }
      // rete di sicurezza: se l'animazione non scocca, i numeri salgono lo stesso
      window.setTimeout(sali, ATTESA + 300);
    }
  }

  /* ---------------- voce di menu attiva ---------------- */
  var links = document.querySelectorAll('.nav a[href^="#"]');
  var targets = [];
  Array.prototype.forEach.call(links, function (a) {
    var el = document.querySelector(a.getAttribute('href'));
    if (el) { targets.push({ link: a, el: el }); }
  });

  if (targets.length && 'IntersectionObserver' in window) {
    var ios = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var hit = targets.filter(function (t) { return t.el === entry.target; })[0];
        if (!hit) { return; }
        if (entry.isIntersecting) {
          targets.forEach(function (t) { t.link.removeAttribute('aria-current'); });
          hit.link.setAttribute('aria-current', 'true');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    targets.forEach(function (t) { ios.observe(t.el); });
  }

  /* =====================================================================
     Simulazione RRF
     score(d) = somma su ogni lista di 1 / (k + rank_i(d)), rank da 1.

     Due scelte che rendono visibile cio' che k fa davvero:

     1. Il cursore e' LOGARITMICO. In RRF le inversioni di classifica
        avvengono quasi tutte sotto k = 20: su una scala lineare 1-120
        il 90% della corsa non muoveva nulla, ed era il difetto.
     2. Lo spessore di ogni connettore e' il contributo 1/(k + rank)
        rapportato al massimo possibile a quel k, cioe' 1/(k + 1).
        A k basso le linee sono diseguali, a k alto si pareggiano: e'
        l'appiattimento che k produce, disegnato invece che spiegato.

     I ranghi sono d'esempio; la formula, il valore 60 del paper e il
     comportamento sono quelli veri.
     ===================================================================== */
  var PASSAGGI = [
    { t: 'Come richiedere assistenza',        lex: 1, vec: 5 },
    { t: 'Domande frequenti sull’assistenza', lex: 2, vec: 4 },
    { t: 'Tempi di risposta del supporto',    lex: 3, vec: 2 },
    { t: 'Condizioni del servizio',           lex: 4, vec: 6 },
    { t: 'Contatti e sedi',                   lex: 5, vec: 3 },
    { t: 'Manuale d’uso, capitolo 4',         lex: 6, vec: 1 }
  ];
  var TOP = 3;      // "in alto" = fra i primi tre, per il consenso
  var K_BASE = 60;  // il valore del paper: le frecce misurano da qui
  var K_MAX = 120;

  var listLex = document.getElementById('list-lex');
  var listVec = document.getElementById('list-vec');
  var listRrf = document.getElementById('list-rrf');
  var slider = document.getElementById('k-slider');
  var kOut = document.getElementById('k-out');
  var kSpread = document.getElementById('k-spread');
  var kCons = document.getElementById('k-consensus');
  var svg = document.querySelector('.rrf-links');
  var presets = document.querySelectorAll('.kp');
  var NS = 'http://www.w3.org/2000/svg';

  function kDaPosizione(v) {
    return Math.max(1, Math.round(Math.pow(K_MAX, v / 100)));
  }

  function fondi(k) {
    return PASSAGGI.map(function (p) {
      return { t: p.t, lex: p.lex, vec: p.vec,
               score: 1 / (k + p.lex) + 1 / (k + p.vec) };
    }).sort(function (a, b) { return b.score - a.score; });
  }

  var ORDINE_BASE = fondi(K_BASE).map(function (r) { return r.t; });

  function titolo(li) {
    var el = li.querySelector('.ft');
    return el ? el.textContent : li.textContent;
  }

  function voce(r, posizione, massimo) {
    var li = document.createElement('li');
    if (r.lex <= TOP && r.vec <= TOP) { li.className = 'both'; }

    var ft = document.createElement('span');
    ft.className = 'ft';
    ft.textContent = r.t;
    li.appendChild(ft);

    var meta = document.createElement('span');
    meta.className = 'fmeta';
    [['L', r.lex], ['V', r.vec]].forEach(function (par) {
      var chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = par[0] + par[1];
      meta.appendChild(chip);
    });
    var sc = document.createElement('span');
    sc.className = 'sc';
    sc.textContent = r.score.toFixed(5);
    meta.appendChild(sc);

    // quanto si e' spostato rispetto all'ordine a k = 60
    var salto = ORDINE_BASE.indexOf(r.t) - posizione;
    if (salto !== 0) {
      var d = document.createElement('span');
      d.className = 'delta ' + (salto > 0 ? 'su' : 'giu');
      d.textContent = (salto > 0 ? '▲' : '▼') + Math.abs(salto);
      meta.appendChild(d);
    }
    li.appendChild(meta);

    var bar = document.createElement('span');
    bar.className = 'fbar';
    var i = document.createElement('i');
    i.style.width = Math.round(r.score / massimo * 100) + '%';
    bar.appendChild(i);
    li.appendChild(bar);
    return li;
  }

  function disegnaLinee(dati, k) {
    if (!svg || !listLex || !listVec || !listRrf) { return; }
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    var cols = svg.parentNode;
    var base = cols.getBoundingClientRect();
    if (!base.width) { return; }

    // A colonne impilate (telefono) i connettori non vogliono dire nulla.
    // Si guarda la geometria delle COLONNE e non quella delle voci: durante
    // il riordino le voci sono trasformate, e leggerle qui faceva sparire
    // le linee proprio ai k bassi, cioe' dove servono di piu'.
    var colonne = cols.querySelectorAll('.rrf-col');
    if (colonne.length < 2) { return; }
    var x0 = colonne[0].getBoundingClientRect().left;
    var x1 = colonne[1].getBoundingClientRect().left;
    if (Math.abs(x1 - x0) < 4) { return; }
    svg.setAttribute('viewBox', '0 0 ' + base.width + ' ' + base.height);

    var contributoMax = 1 / (k + 1);
    dati.forEach(function (r, i) {
      var dest = listRrf.children[i];
      if (!dest) { return; }
      var rd = dest.getBoundingClientRect();
      [[listLex.children[r.lex - 1], r.lex, true, 'lex'],
       [listVec.children[r.vec - 1], r.vec, false, 'vec']].forEach(function (par) {
        var src = par[0];
        if (!src) { return; }
        var rs = src.getBoundingClientRect();
        var x1 = (par[2] ? rs.right : rs.left) - base.left;
        var y1 = rs.top - base.top + rs.height / 2;
        var x2 = (par[2] ? rd.left : rd.right) - base.left;
        var y2 = rd.top - base.top + rd.height / 2;
        var dx = (x2 - x1) * 0.5;
        var quota = (1 / (k + par[1])) / contributoMax;

        var p = document.createElementNS(NS, 'path');
        p.setAttribute('class', 'da-' + par[3]);
        p.setAttribute('d', 'M' + x1 + ' ' + y1 + ' C' + (x1 + dx) + ' ' + y1
                            + ',' + (x2 - dx) + ' ' + y2 + ',' + x2 + ' ' + y2);
        p.setAttribute('stroke-width', (1.2 + 5.5 * quota).toFixed(2));
        p.setAttribute('opacity', (0.45 + 0.45 * quota).toFixed(2));
        p.setAttribute('data-i', i);
        svg.appendChild(p);
      });
    });
    applicaEvidenza();
  }

  /* Col puntatore su una voce della fusione, restano accese le sue sole
     due linee. E' un rinforzo: la stessa informazione sta gia' scritta
     nei gettoni L3 e V2, quindi chi non usa un puntatore non perde nulla. */
  var evidenziato = null;

  function applicaEvidenza() {
    if (!svg) { return; }
    svg.classList.toggle('isola', evidenziato !== null);
    Array.prototype.forEach.call(svg.children, function (el) {
      el.classList.toggle('acceso',
        evidenziato !== null && el.getAttribute('data-i') === String(evidenziato));
    });
  }

  if (listRrf) {
    listRrf.addEventListener('mouseover', function (e) {
      var li = e.target.closest ? e.target.closest('li') : null;
      if (!li || li.parentNode !== listRrf) { return; }
      var i = Array.prototype.indexOf.call(listRrf.children, li);
      if (i === evidenziato) { return; }
      evidenziato = i;
      applicaEvidenza();
    });
    listRrf.addEventListener('mouseleave', function () {
      evidenziato = null;
      applicaEvidenza();
    });
  }

  function aggiorna(animare) {
    if (!slider || !listRrf) { return; }
    var k = kDaPosizione(parseFloat(slider.value));
    if (kOut) { kOut.textContent = String(k); }
    slider.setAttribute('aria-valuetext', 'k uguale a ' + k);
    Array.prototype.forEach.call(presets, function (b) {
      b.classList.toggle('is-on', parseInt(b.getAttribute('data-k'), 10) === k);
    });

    var dati = fondi(k);
    var massimo = dati[0].score;

    // FLIP: si misura prima, si ricostruisce, si anima la differenza
    var prima = {};
    if (animare) {
      Array.prototype.forEach.call(listRrf.children, function (li) {
        prima[titolo(li)] = li.getBoundingClientRect().top;
      });
    }

    listRrf.textContent = '';
    dati.forEach(function (r, i) { listRrf.appendChild(voce(r, i, massimo)); });

    if (animare) {
      Array.prototype.forEach.call(listRrf.children, function (li) {
        var y0 = prima[titolo(li)];
        if (y0 === undefined) { return; }
        var dy = y0 - li.getBoundingClientRect().top;
        if (!dy) { return; }
        li.style.transform = 'translateY(' + dy + 'px)';
        li.offsetHeight;                       // forza il calcolo del layout
        li.classList.add('si-muove');
        li.style.transform = '';
      });
    }

    disegnaLinee(dati, k);
    if (animare) {
      // le linee inseguono le voci che scorrono, invece di aspettarle ferme
      var fine = performance.now() + 460;
      (function passo() {
        disegnaLinee(dati, k);
        if (performance.now() < fine) { requestAnimationFrame(passo); }
      }());
    }

    if (kSpread) {
      var d = (dati[0].score - dati[dati.length - 1].score) / dati[0].score * 100;
      kSpread.innerHTML = 'Distacco fra il primo e l’ultimo: <b>'
        + d.toFixed(1).replace('.', ',') + '%</b>';
    }
    if (kCons) {
      var comuni = PASSAGGI.filter(function (p) {
        return p.lex <= TOP && p.vec <= TOP;
      }).length;
      kCons.innerHTML = 'Consenso: <b>' + comuni + ' '
        + (comuni === 1 ? 'passaggio' : 'passaggi') + ' su ' + TOP + '</b> '
        + (comuni === 1 ? 'sta' : 'stanno')
        + ' in alto in entrambe le liste. Non dipende da <var>k</var>: dipende '
        + 'dalle due liste. Quello che <var>k</var> sposta è l’ordine della fusione.';
    }
  }

  if (slider && listRrf) {
    slider.addEventListener('input', function () { aggiorna(!reduced()); });
    Array.prototype.forEach.call(presets, function (b) {
      b.addEventListener('click', function () {
        var k = parseInt(b.getAttribute('data-k'), 10);
        slider.value = (Math.log(k) / Math.log(K_MAX) * 100).toFixed(1);
        aggiorna(!reduced());
      });
    });
    var attesa;
    window.addEventListener('resize', function () {
      clearTimeout(attesa);
      attesa = setTimeout(function () { aggiorna(false); }, 120);
    });
    aggiorna(false);
  }

  /* =====================================================================
     Profili di citabilita' — dati veri da mars_citability.py
     ===================================================================== */
  var SEGNALI = [
    ['tecnica', 'Accesso e indicizzabilità'],
    ['seo', 'Qualità SEO'],
    ['recuperabilita', 'Recuperabilità ibrida'],
    ['answer_shaped', 'Contenuto in forma di risposta'],
    ['dati_strutturati', 'Dati strutturati'],
    ['accessibilita', 'Accessibilità'],
    ['sicurezza', 'Sicurezza']
  ];

  var ASSISTENTI = ['Claude', 'ChatGPT/Perplexity', 'Qwen', 'Kimi'];

  //                          tec seo rec ans dat acc sic
  var PESI = {
    'Claude':             [3, 1, 3, 3, 2, 1, 1],
    'ChatGPT/Perplexity': [3, 3, 2, 3, 3, 1, 1],
    'Qwen':               [3, 1, 2, 3, 2, 1, 1],
    'Kimi':               [3, 1, 2, 3, 2, 1, 1]
  };

  /* `mult` esiste solo dove un moltiplicatore c'e' davvero: e' l'unico
     oggi attivo in mars_citability. Il testo della nota di trasparenza
     sotto le barre NON sta qui — lo script non lo tocca, sta nel markup. */
  var MERCATI = {
    global: { pesi: { 'Claude': 5, 'ChatGPT/Perplexity': 9, 'Qwen': 3, 'Kimi': 3 } },
    eu:     { pesi: { 'Claude': 6, 'ChatGPT/Perplexity': 10, 'Qwen': 1, 'Kimi': 1 },
              area: 'accessibilita',
              mult: 'Mercato UE: il segnale «Accessibilità» pesa il doppio. È l\'European '
                  + 'Accessibility Act, cioè una ragione normativa verificabile, non una stima.' },
    us:     { pesi: { 'Claude': 6, 'ChatGPT/Perplexity': 10, 'Qwen': 1, 'Kimi': 1 } },
    cn:     { pesi: { 'Claude': 1, 'ChatGPT/Perplexity': 1, 'Qwen': 9, 'Kimi': 9 } }
  };

  var elAssist = document.getElementById('assistants');
  var elMult = document.getElementById('market-mult');
  var elMatrice = document.getElementById('matrix-body');
  var formMercati = document.getElementById('markets');

  function disegnaAssistenti(mercato) {
    if (!elAssist) { return; }
    var dati = MERCATI[mercato];
    var max = Math.max.apply(null, ASSISTENTI.map(function (a) { return dati.pesi[a]; }));
    elAssist.textContent = '';

    ASSISTENTI.forEach(function (nome) {
      var v = dati.pesi[nome];
      var li = document.createElement('li');

      var n = document.createElement('span');
      n.className = 'an';
      n.textContent = nome;

      var bar = document.createElement('span');
      bar.className = 'abar';
      var i = document.createElement('i');
      i.style.width = Math.round((v / max) * 100) + '%';
      bar.appendChild(i);

      var val = document.createElement('span');
      val.className = 'av';
      val.textContent = v;

      li.appendChild(n);
      li.appendChild(bar);
      li.appendChild(val);
      elAssist.appendChild(li);
    });

    if (elMult) { elMult.textContent = dati.mult || ''; }
    if (elMatrice) {
      var righe = elMatrice.querySelectorAll('tr');
      Array.prototype.forEach.call(righe, function (tr) {
        tr.classList.toggle('row-mult', tr.dataset.signal === dati.area);
      });
    }
  }

  function disegnaMatrice() {
    if (!elMatrice) { return; }
    elMatrice.textContent = '';
    SEGNALI.forEach(function (seg, idx) {
      var tr = document.createElement('tr');
      tr.dataset.signal = seg[0];

      var th = document.createElement('th');
      th.scope = 'row';
      th.textContent = seg[1];
      tr.appendChild(th);

      ASSISTENTI.forEach(function (nome) {
        var td = document.createElement('td');
        var w = PESI[nome][idx];
        var pastiglia = document.createElement('span');
        pastiglia.className = 'peso';
        pastiglia.textContent = w;
        td.appendChild(pastiglia);
        td.setAttribute('data-w', String(w));
        tr.appendChild(td);
      });
      elMatrice.appendChild(tr);
    });
  }

  if (formMercati) {
    formMercati.addEventListener('change', function (e) {
      if (e.target.name === 'market') { disegnaAssistenti(e.target.value); }
    });
  }

  disegnaMatrice();
  disegnaAssistenti('global');

  /* =====================================================================
     Modulo: fallimento rumoroso invece che silenzioso.
     `_csrfToken` e `_Token[fields]` li genera il server a ogni render.
     Se questa copia della pagina non passa da li', restano vuoti e la
     POST verrebbe rifiutata: il contatto sparirebbe senza che nessuno
     se ne accorga. Meglio non partire e dire dove andare.
     ===================================================================== */
  var modulo = document.getElementById('richiedi_un_check_up_preliminare');
  if (modulo) {
    modulo.addEventListener('submit', function (e) {
      var csrf = modulo.querySelector('input[name="_csrfToken"]');
      if (csrf && csrf.value.trim()) { return; }
      e.preventDefault();
      var avviso = document.getElementById('form-fallback');
      if (!avviso) { return; }
      avviso.hidden = false;
      avviso.setAttribute('tabindex', '-1');
      avviso.focus();
    });
  }
}());
