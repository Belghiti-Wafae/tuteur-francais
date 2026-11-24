const $ = id => document.getElementById(id);
let me = null, cid = null, mode = "chat", setupMode = "chat", av = false, inscr = false;
const show = v => ["auth", "app"].forEach(x => $("v-" + x).hidden = x != v);
const panel = p => ["setup", "conv"].forEach(x => $("p-" + x).hidden = x != p);
const norm = s => String(s).toLowerCase().trim();

async function api(url, body, method) {
  const r = await fetch(url, { method: method || (body ? "POST" : "GET"), headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (r.status == 401) {
    const ok = (await fetch("/api/me")).ok;      // la session est-elle vraiment perdue ?
    if (!ok) show("auth");
    throw new Error(ok ? "Erreur 401 sur " + url : "Session expirée, reconnectez-vous.");
  }
  if (!r.ok) { let d; try { d = (await r.json()).detail; } catch {} throw new Error(typeof d == "string" ? d : "Erreur " + r.status); }
  return r.json();
}
function bulle(t, cls = "") { const d = document.createElement("div"); d.className = "bulle " + cls; d.textContent = t; $("chat").append(d); d.scrollIntoView({ block: "end" }); return d; }

// ----- affichage des messages (en direct et à la réouverture) -----
function exo(x) {
  const d = bulle(x.enonce);
  if (x.options && x.options.length) {
    const o = document.createElement("div"); o.className = "opts";
    x.options.forEach(t => { const b = document.createElement("button"); b.type = "button"; b.textContent = t;
      b.onclick = () => b.classList.add(norm(t) == norm(x.reponse) ? "ok" : "ko"); o.append(b); });
    d.append(o);
  }
  const det = document.createElement("details"), s = document.createElement("summary");
  s.textContent = "Réponse et explication"; det.append(s, `${x.reponse} — ${x.explication}`); d.append(det);
}
function correction(k) {
  if (!k.erreurs.length) return bulle("✓ " + (k.encouragement || "Parfait !"), "correction");
  const d = bulle(k.phrase_corrigee, "correction");
  k.erreurs.forEach(e => { const p = document.createElement("p"); p.textContent = `${e.extrait} (${e.type}) : ${e.explication}`; d.append(p); });
}
function render(kind, d) {
  if (kind == "user") return bulle(d.text, "moi");
  if (kind == "chat") return bulle(d.reponse);
  if (kind == "correction") return correction(d);
  if (kind == "explain") return bulle(`${d.titre}\n${d.explication}\n${d.exemples.map(x => "• " + x).join("\n")}\n${d.verification}`);
  if (kind == "exercises") return d.exercices.forEach(exo);
}

// ----- conversation -----
async function send(texte) {
  texte = (texte || "").trim();
  if (!cid || (!texte && mode == "explain")) return setEtat("repos");
  if (texte) bulle(texte, "moi");
  setEtat("reflechit");
  const wait = bulle("…", "mute");
  let corr = null;
  try {
    const r = await api(`/api/conversations/${cid}/message`, { text: texte });
    wait.remove(); render(r.kind, r.data);
    if (mode == "chat" && texte) corr = api(`/api/conversations/${cid}/correct`, { text: texte }).catch(() => null);
    if (r.kind == "chat") speak(r.data.reponse); else if (r.kind == "explain") speak(r.data.explication); else setEtat("repos");
  } catch (e) { wait.textContent = e.message; wait.classList.add("erreur"); setEtat("repos"); }
  if (corr) { const k = await corr; if (k) correction(k); }
  loadList();
}

async function openConv(id, nouveau) {
  const c = await api("/api/conversations/" + id);
  cid = id; mode = c.mode; $("titre").textContent = c.titre; $("chat").innerHTML = "";
  c.messages.forEach(m => render(m.kind, m.data));
  $("texte").placeholder = mode == "chat" ? "Écrivez en français…" : mode == "explain" ? "Une autre notion à expliquer…" : "Notion (vide = mes erreurs fréquentes)";
  $("mic").hidden = mode != "chat";
  panel("conv"); loadList(); setEtat("repos");
  if (nouveau) { if (mode == "chat") send(""); else if (mode == "exercise" || c.theme) send(c.theme); }
}

async function loadList() {
  const l = await api("/api/conversations").catch(() => []);
  $("liste").innerHTML = "";
  l.forEach(c => {
    const d = document.createElement("div"); d.className = "item" + (c.id == cid ? " actif" : "");
    const o = document.createElement("button"); o.className = "ouvrir"; o.textContent = c.titre; o.onclick = () => openConv(c.id);
    const x = document.createElement("button"); x.className = "suppr"; x.textContent = "×"; x.setAttribute("aria-label", "Supprimer");
    x.onclick = async () => { if (!confirm("Supprimer cette conversation ?")) return; await api("/api/conversations/" + c.id, null, "DELETE");
      if (c.id == cid) { cid = null; panel("setup"); } loadList(); };
    d.append(o, x); $("liste").append(d);
  });
}

// ----- avatar facultatif -----
function applyAvatar() {
  const z = $("avatarzone"); z.hidden = !me.avatar;
  if (me.avatar && !av) { av = true; z.innerHTML = '<div id="avatar"><canvas id="cv"></canvas></div>'; import("/static/avatar3d.js"); }
}

// ----- authentification -----
$("bascule").onclick = () => { inscr = !inscr; $("nom").hidden = !inscr; $("auth-err").textContent = "";
  $("auth-ok").textContent = inscr ? "Créer mon compte" : "Se connecter"; $("bascule").textContent = inscr ? "J'ai déjà un compte" : "Créer un compte"; };
$("f-auth").onsubmit = async e => { e.preventDefault();
  try { me = await api(inscr ? "/api/register" : "/api/login", { email: $("email").value, password: $("pwd").value, nom: $("nom").value }); $("pwd").value = ""; await enter(); }
  catch (x) { $("auth-err").textContent = x.message; } };
$("logout").onclick = async () => { await api("/api/logout", {}); me = null; cid = null; show("auth"); };

async function enter() {
  show("app"); $("hello").textContent = me.nom || me.email;
  $("level").value = me.niveau; $("l1").value = me.l1; $("objectif").value = me.objectif; $("avatar-on").checked = !!me.avatar;
  applyAvatar(); await loadList(); panel("setup");
}

// ----- choix des options -----
const LAB = { chat: ["Thème de la conversation", "ex : au restaurant, voyage, entretien d'embauche"],
  explain: ["Notion à expliquer", "ex : le subjonctif, les articles"], exercise: ["Notion à travailler (facultatif)", "vide = cibler mes erreurs fréquentes"] };
document.querySelectorAll("#modes button").forEach(b => b.onclick = () => {
  setupMode = b.dataset.m;
  document.querySelectorAll("#modes button").forEach(x => x.setAttribute("aria-pressed", x == b));
  $("theme-lab").textContent = LAB[setupMode][0]; $("theme").placeholder = LAB[setupMode][1]; });
$("nouveau").onclick = () => panel("setup");
$("f-setup").onsubmit = async e => { e.preventDefault();
  const theme = $("theme").value.trim(); $("setup-err").textContent = "";
  if (setupMode == "explain" && !theme) return $("theme").focus();
  try {
    me = await api("/api/prefs", { l1: $("l1").value, niveau: $("level").value, objectif: $("objectif").value, avatar: $("avatar-on").checked }, "PUT");
    applyAvatar();
    const { id } = await api("/api/conversations", { mode: setupMode, theme, niveau: $("level").value });
    $("theme").value = ""; await openConv(id, true);
  } catch (x) { $("setup-err").textContent = x.message; } };
$("f-conv").onsubmit = e => { e.preventDefault(); const t = $("texte").value.trim(); if (!t && mode != "exercise") return; $("texte").value = ""; send(t); };

api("/api/me").then(u => { me = u; enter(); }).catch(() => show("auth"));