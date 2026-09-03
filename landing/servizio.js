/* MARS Beacon — la pagina dopo la registrazione.
 *
 * Legge i dati che `app.js` ha lasciato nella sessione e li mostra. Se
 * non ci sono — link aperto a mano, navigazione privata, scheda nuova —
 * la pagina resta valida e lo dichiara, invece di stampare "undefined"
 * o di rimandare al modulo chi magari e' arrivato da un segnalibro. */
(function () {
  "use strict";

  function leggi() {
    /* Fra try/catch perche' con i dati dei siti bloccati la sola lettura
     * di `sessionStorage` solleva, e non restituisce null. */
    try {
      var grezzo = window.sessionStorage.getItem("mars.lead");
      return grezzo ? JSON.parse(grezzo) : null;
    } catch (e) {
      return null;
    }
  }

  function riga(etichetta, valore) {
    var li = document.createElement("li");
    var b = document.createElement("b");
    b.textContent = etichetta + ": ";
    li.appendChild(b);
    /* textContent e non innerHTML: questi valori li ha scritti una
     * persona in un modulo, quindi sono dato non fidato anche quando la
     * persona e' il cliente. */
    li.appendChild(document.createTextNode(valore));
    return li;
  }

  var dati = leggi();

  if (dati) {
    var nome = (dati.nome || "").split(" ")[0];
    document.getElementById("saluto").textContent =
      nome ? "Benvenuto, " + nome + "." : "Accesso aperto.";
    document.getElementById("sottotitolo").textContent =
      "Lo spazio di " + (dati.azienda || "la tua azienda") +
      " è pronto: da qui parte il primo referto.";

    var ul = document.getElementById("dati");
    ul.innerHTML = "";
    ul.appendChild(riga("Azienda", dati.azienda || "—"));
    ul.appendChild(riga("Referente", (dati.nome || "—") +
                                     (dati.ruolo ? " · " + dati.ruolo : "")));
    ul.appendChild(riga("Contatti", (dati.email || "—") +
                                    (dati.telefono ? " · " + dati.telefono : "")));
    ul.appendChild(riga("Sito da analizzare", dati.sito || "—"));

    var url = document.getElementById("url");
    if (url && dati.sito) { url.value = dati.sito; }
  }

  /* Il modulo non fa partire nulla, e lo dice invece di far finta di
   * lavorare: una finta barra di avanzamento su una pagina che vende
   * onesta' metodologica sarebbe la promessa sbagliata. */
  var form = document.getElementById("esecuzione");
  if (!form) { return; }

  form.addEventListener("submit", function (evento) {
    evento.preventDefault();
    var esito = document.getElementById("esito");
    var dispositivo = document.getElementById("dispositivo").value;
    var pagine = document.getElementById("pagine").value;
    var mercato = document.getElementById("mercato").value;
    var lingua = document.getElementById("lingua").value;
    var sito = document.getElementById("url").value || "https://www.esempio.it";

    esito.innerHTML = "";
    var p = document.createElement("span");
    p.textContent = "Dimostrazione: nessun audit è partito. " +
                    "Con questi parametri il comando vero sarebbe";
    esito.appendChild(p);
    esito.appendChild(document.createElement("br"));
    var pre = document.createElement("code");
    pre.textContent = "mars_audit.py " + sito +
      " --max-pages " + pagine +
      " --form-factor " + dispositivo +
      " --market " + mercato +
      " --lang " + lingua +
      " --i-own-this-domain --format html --output referto.html";
    esito.appendChild(pre);
  });
}());
