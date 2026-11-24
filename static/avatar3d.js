import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

const box = document.getElementById("avatar");
const canvas = document.getElementById("cv");
const info = document.getElementById("etat");

// --- Scène : rendu, caméra, lumières ---
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
camera.position.set(0, 1.38, 1.6);      // distance et hauteur : cadrage du buste
camera.lookAt(0, 1.32, 0);
scene.add(new THREE.AmbientLight(0xffffff, 1));
const soleil = new THREE.DirectionalLight(0xffffff, 2);
soleil.position.set(1, 2, 2);
scene.add(soleil);

function resize() {
  const w = box.clientWidth, h = box.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(box);
resize();

// --- Chargement du modèle VRM ---
let vrm = null;
const loader = new GLTFLoader();
loader.register(p => new VRMLoaderPlugin(p));
loader.load("/static/avatar.vrm", gltf => {
  vrm = gltf.userData.vrm;
  VRMUtils.rotateVRM0(vrm);                         // oriente les anciens modèles VRM 0.x
  vrm.scene.traverse(o => (o.frustumCulled = false));
  scene.add(vrm.scene);
  const os = vrm.humanoid;                          // les bras quittent la pose en T
  os.getNormalizedBoneNode("leftUpperArm").rotation.z = -1.2;
  os.getNormalizedBoneNode("rightUpperArm").rotation.z = 1.2;
  if (vrm.lookAt) vrm.lookAt.target = camera;       // les yeux suivent l'utilisateur
}, undefined, () => { info.textContent = "avatar.vrm introuvable dans le dossier static"; });

// --- Animation ---
const lerp = (a, b, k) => a + (b - a) * k;
const VISEMES = ["aa", "oh", "ee", "ih", "ou"];
const POSE = {                       // inclinaison de la tête et sourire selon l'état
  repos:     { x: 0,    y: 0,   z: 0,    happy: 0.15 },
  ecoute:    { x: 0.04, y: 0,   z: -0.1, happy: 0.1 },
  reflechit: { x: -0.1, y: 0.3, z: 0.05, happy: 0 },
  parle:     { x: 0,    y: 0,   z: 0,    happy: 0.25 },
};
const val = {};
let cur = 0, prochainVisème = 0, prochainClin = 2, clinT = -1, vol = 0;

function exp(nom, cible, dt, vitesse) {            // valeur d'expression lissée
  val[nom] = lerp(val[nom] || 0, cible, Math.min(1, dt * vitesse));
  vrm.expressionManager.setValue(nom, val[nom]);
}

function animer(dt, t) {
  const etat = window.avatarEtat || "repos";
  const p = POSE[etat] || POSE.repos, k = Math.min(1, dt * 5);
  const tete = vrm.humanoid.getNormalizedBoneNode("head");
  const buste = vrm.humanoid.getNormalizedBoneNode("chest") || vrm.humanoid.getNormalizedBoneNode("spine");

  // tête : légère oscillation au repos, hochement quand il parle
  const hoche = etat === "parle" ? Math.sin(t * 3.1) * 0.03 : 0;
  tete.rotation.x = lerp(tete.rotation.x, p.x + hoche, k);
  tete.rotation.y = lerp(tete.rotation.y, p.y + Math.sin(t * 0.6) * 0.04, k);
  tete.rotation.z = lerp(tete.rotation.z, p.z, k);
  if (buste) buste.rotation.x = Math.sin(t * 1.5) * 0.012;   // respiration

  // clignement des yeux toutes les 2 à 5 secondes
  let clin = 0;
  if (clinT < 0 && t > prochainClin) clinT = 0;
  if (clinT >= 0) {
    clinT += dt;
    clin = Math.sin(Math.min(clinT / 0.18, 1) * Math.PI);
    if (clinT > 0.18) { clinT = -1; prochainClin = t + 2 + Math.random() * 3; }
  }
  vrm.expressionManager.setValue("blink", clin);

  // synchronisation labiale : volume de l'audio, voyelle qui change toutes les ~0,12 s
  const parle = etat === "parle";
  const v = Math.min(1, (window.avatarVol || 0) * 1.4);
  vol = lerp(vol, parle ? v : 0, Math.min(1, dt * 20));
  if (t > prochainVisème) {
    cur = (cur + 1 + Math.floor(Math.random() * 3)) % VISEMES.length;
    prochainVisème = t + 0.09 + Math.random() * 0.08;
  }
  VISEMES.forEach((nom, i) => exp(nom, i === cur ? vol * 0.85 : 0, dt, 25));
  exp("happy", p.happy, dt, 4);
}

const horloge = new THREE.Clock();
(function image() {
  requestAnimationFrame(image);
  const dt = Math.min(horloge.getDelta(), 0.1);
  if (vrm) { animer(dt, horloge.elapsedTime); vrm.update(dt); }
  renderer.render(scene, camera);
})();