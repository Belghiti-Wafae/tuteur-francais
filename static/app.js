const $ = id => document.getElementById(id);
const history = [];
const cfg = () => ({ level: $("level").value, theme: $("theme").value, l1: $("l1").value });

function bulle(texte, cls = "") {
  const d = document.createElement("div");
  d.className = "bulle " + cls; d.textContent = texte;
  $("chat").append(d); d.scrollIntoView({ block: "end" }); return d;
}
async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.text()).slice(0, 200));
  return r.json();
}

async function send(texte) {
  bulle(texte, "moi");
  setEtat("reflechit");
  const reponse = bulle("…", "");
  const correction = post("/api/correct", { phrase: texte, ...cfg() }).catch(() => null); // en parallèle
  try {
    const c = await post("/api/chat", { message: texte, history, ...cfg() });
    reponse.textContent = c.reponse;
    history.push({ role: "user", content: texte }, { role: "assistant", content: c.reponse });
    speak(c.reponse);
  } catch (e) { reponse.textContent = "Erreur : " + e.message; reponse.classList.add("erreur"); setEtat("repos"); }
  const k = await correction; if (k) montrerCorrection(k);
}

function montrerCorrection(k) {
  if (!k.erreurs.length) return bulle("✓ " + (k.encouragement || "Parfait !"), "correction");
  const d = bulle(k.phrase_corrigee, "correction");
  k.erreurs.forEach(e => { const p = document.createElement("p"); p.textContent = `${e.extrait} (${e.type}) : ${e.explication}`; d.append(p); });
}

$("form").onsubmit = e => { e.preventDefault(); const t = $("texte").value.trim(); if (t) { $("texte").value = ""; send(t); } };

$("btn-explain").onclick = async () => {
  const n = prompt("Quelle notion ? (ex : le passé composé)"); if (!n) return;
  const e = await post("/api/explain", { notion: n, ...cfg() });
  bulle(`${e.titre}\n${e.explication}\n${e.exemples.map(x => "• " + x).join("\n")}\n${e.verification}`);
  speak(e.explication);
};
$("btn-exo").onclick = async () => {
  const n = prompt("Notion (vide = vos erreurs fréquentes)") || "";
  const r = await post("/api/exercises", { notion: n, ...cfg() });
  r.exercices.forEach(x => {
    const d = bulle(x.enonce + (x.options.length ? "\n" + x.options.map(o => "• " + o).join("\n") : ""));
    const det = document.createElement("details"), s = document.createElement("summary");
    s.textContent = "Réponse"; det.append(s, `${x.reponse} — ${x.explication}`); d.append(det);
  });
};

// Remplacés aux étapes 9 et 10 :
const player = $("player");
let file = Promise.resolve();

function speak(texte) {
  const phrases = texte.match(/[^.!?…]+[.!?…]*/g) || [texte];
  // toutes les synthèses démarrent tout de suite, mais sont jouées dans l'ordre
  const audios = phrases.map(p => fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texte: p.trim() }) }).then(r => { if (!r.ok) throw 0; return r.blob(); }).catch(() => null));
  audios.forEach((a, i) => file = file.then(async () => jouer(await a, phrases[i])));
  file = file.then(() => setEtat("repos"));
}

function jouer(blob, texte) {
  setEtat("parle");
  return new Promise(fin => {
    if (!blob) { // plan B : voix du navigateur
      const u = new SpeechSynthesisUtterance(texte); u.lang = "fr-FR"; u.onend = fin; speechSynthesis.speak(u); return;
    }
    player.src = URL.createObjectURL(blob);
    player.onended = fin; player.onerror = fin;
    player.play().catch(fin);
  });
}
const NOMS = { repos: "Prêt(e)", ecoute: "J'écoute…", reflechit: "Je réfléchis…", parle: "Je parle" };
function setEtat(e) { window.avatarEtat = e; $("etat").textContent = NOMS[e]; }
// Bouche synchronisée sur le volume de l'audio
const ctx = new AudioContext();
const analyseur = ctx.createAnalyser(); analyseur.fftSize = 256;
const source = ctx.createMediaElementSource(player);
source.connect(analyseur); analyseur.connect(ctx.destination);
["click", "keydown"].forEach(ev => document.addEventListener(ev, () => ctx.resume()));
const buf = new Uint8Array(analyseur.fftSize);
(function boucle() {
  analyseur.getByteTimeDomainData(buf);
  let s = 0; for (const v of buf) s += Math.abs(v - 128);
  window.avatarVol = Math.min(1, s / buf.length / 25);   // lu par avatar3d.js
  requestAnimationFrame(boucle);
})();

let rec, morceaux = [];
$("mic").onclick = async () => {
  if (rec && rec.state === "recording") return rec.stop();
  const flux = await navigator.mediaDevices.getUserMedia({ audio: true });
  rec = new MediaRecorder(flux); morceaux = [];
  rec.ondataavailable = e => morceaux.push(e.data);
  rec.onstop = async () => {
    flux.getTracks().forEach(t => t.stop());
    $("mic").classList.remove("on"); $("mic").textContent = "Parler"; setEtat("reflechit");
    const fd = new FormData(); fd.append("audio", new Blob(morceaux, { type: rec.mimeType }), "voix");
    const { texte } = await (await fetch("/api/stt", { method: "POST", body: fd })).json();
    if (texte) send(texte); else setEtat("repos");
  };
  rec.start(); $("mic").classList.add("on"); $("mic").textContent = "Arrêter"; setEtat("ecoute");
};


$("btn-bilan").onclick = async () => {
  if (!history.length) return bulle("Parlez d'abord avec Camille.");
  const b = await post("/api/bilan", { history, level: $("level").value });
  bulle(`${b.resume}\n\nPoints forts : ${b.points_forts.join(", ")}\nÀ retravailler : ${b.a_retravailler.join(", ")}\nVocabulaire : ${b.vocabulaire.join(", ")}\nProchain objectif : ${b.objectif_prochain}`);
};
$("btn-prog").onclick = async () => {
  const p = await (await fetch("/api/progress")).json();
  const t = p.taux_erreur === null ? "pas encore de données" : Math.round(p.taux_erreur * 100) + " % de mots fautifs";
  bulle(`Erreurs fréquentes : ${p.erreurs_frequentes.join(", ") || "aucune"}\nTaux d'erreur : ${t}\nNiveau : ${p.suggestion_niveau || "-"}`);
};