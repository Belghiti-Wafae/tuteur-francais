
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
    const r = await fetch("/api/stt", { method: "POST", body: fd });
    if (!r.ok) {
      bulle(r.status === 401 ? "Session expirée : reconnectez-vous." : "Erreur de transcription (" + r.status + ").", "erreur");
      setEtat("repos"); return;
    }
    const { texte } = await r.json();    if (texte) send(texte); else setEtat("repos");
   };
  rec.start(); $("mic").classList.add("on"); $("mic").textContent = "Arrêter"; setEtat("ecoute");
};

