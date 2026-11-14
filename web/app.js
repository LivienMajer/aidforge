import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

// optional module (API-free usage animation of the real STL)
let usageAnim = null;
import("/static/usage_anim.js").then((m) => { usageAnim = m; if (currentJob) updateAnimButton(currentJob); }).catch(() => {});

// ------------------------------------------------------------------ i18n
const I18N = {
  de: {
    skip: "Zum Formular springen",
    tagline: "Vom Alltagsproblem zum druckfertigen Hilfsmittel",
    mediaTitle: "Situation zeigen",
    dropText: "Foto oder kurzes Video hochladen",
    dropHint: "z. B. der Schlüssel, das Glas, die Hand beim Versuch – gern mit Münze/Karte als Größenreferenz",
    impTitle: "Einschränkung",
    impPh: "z. B. Rheumatoide Arthritis, kaum Kraft im Pinzettengriff",
    actTitle: "Aktivität",
    actPh: "z. B. Haustür selbstständig aufschließen",
    notesTitle: "Maße & Notizen (optional)",
    notesPh: "z. B. Schlüsselkopf 24 × 22 mm, Deckel Ø 82 mm, Linkshänder",
    micLabel: "Spracheingabe",
    micStart: "Spracheingabe starten",
    micStop: "Aufnahme beenden",
    micBusy: "Wird transkribiert …",
    reviewLabel: "Gemini prüft das gerenderte Modell und korrigiert es",
    go: "Hilfsmittel generieren",
    working: "Wird erstellt …",
    libTitle: "Oder: Vorlage direkt öffnen",
    recentTitle: "Gespeicherte Ergebnisse",
    resultTitle: "Ergebnis",
    emptyText: "Dein Hilfsmittel erscheint hier als druckfertiges 3D-Modell.",
    wire: "Gitter",
    resetView: "Ansicht zurücksetzen",
    playAnim: "Benutzung zeigen",
    stopAnim: "Animation stoppen",
    dlStl: "STL herunterladen",
    dlScad: ".scad",
    confidence: "Zuversicht",
    loopTitle: "Agentischer Loop – jede Version wird geprüft und verbessert",
    tabAnalysis: "Analyse",
    tabParams: "Parameter",
    tabPrint: "Druck & Nutzung",
    tabReview: "Prüfung",
    tabVisual: "So könnte es aussehen",
    tabCode: "Code",
    rebuild: "Neu bauen",
    copy: "Kopieren",
    copied: "Kopiert",
    refineLabel: "Passt noch nicht? Beschreibe die Änderung:",
    refinePh: "z. B. Griff 5 mm dicker, Hebel länger",
    refineGo: "Anpassen",
    footer: "Prototyp – Hilfsmittel vor dem Alltagseinsatz mit Ergotherapeut:in prüfen. Fotos und Videos werden nur zur Verarbeitung an Gemini gesendet.",
    steps: {
      analyze: "Situation verstehen", design: "Design wählen", compile: "3D-Modell bauen",
      improve: "Prüfen & verbessern", review: "Selbstprüfung", refine: "Anpassung",
    },
    sources: {
      initial: "Erstentwurf", repair: "Code repariert", review_fix: "nach Gemini-Kritik", checks_fix: "nach Druck-Checks",
      refine: "deine Anpassung", manual: "Regler", compile_error: "Kompilierfehler", fix_failed: "Korrektur verworfen",
    },
    viewingOld: "Du siehst Version {v} – aktuell ist Version {c}.",
    changedParams: "Geänderte Parameter",
    critique: "Gemini-Kritik",
    checksShort: "Druck-Checks",
    checksBadge: "Druckbarkeit {p}/{n}",
    approachTemplate: "Vorlage", approachCustom: "Eigenes CAD-Design",
    task: "Aufgabe", observed: "Beobachtet", limitations: "Funktionelle Einschränkungen",
    root: "Kernproblem", requirements: "Anforderungen", measurements: "Maße", assumptions: "Annahmen",
    scale: "Maßstab", scaleNone: "Kein Referenzobjekt erkannt – typische Maße angenommen.",
    questions: "Für eine bessere Passform", srcUser: "Angabe", srcRef: "per Referenz", srcMedia: "geschätzt", srcTypical: "typisch",
    printSettings: "Druckeinstellungen", material: "Material", layer: "Schichthöhe", infill: "Infill",
    walls: "Wände", supports: "Stützstrukturen", orientation: "Ausrichtung", yes: "ja", no: "nein",
    model: "Modell", size: "Größe", volume: "Volumen", weight: "Gewicht (grob)", bed: "Passt aufs Druckbett",
    usage: "So wird es benutzt", safety: "Sicherheit", compileTime: "Rechenzeit OpenSCAD",
    autoChecks: "Automatische Druckbarkeits-Checks",
    reviewNone: "Für diese Version gibt es keine Gemini-Prüfung (deaktiviert oder nach manueller Änderung).",
    reviewOk: "Gemini hat das Modell geprüft – keine Änderungen nötig.",
    reviewNeeds: "Gemini hat Verbesserungen vorgeschlagen.",
    reviewIssues: "Gefundene Punkte", reviewViews: "Was Gemini gesehen hat",
    designNotes: "Design-Notizen", noParams: "Keine einstellbaren Parameter.",
    rebuilding: "Baue neu …", rebuilt: "Fertig – Version", errorPrefix: "Fehler: ",
    missingInput: "Bitte Einschränkung und Aktivität angeben.",
    aiLabel: "KI-Visualisierung",
    aiNote: "zeigt, wie echte Benutzung aussehen könnte – nicht maßstabsgetreu.",
    visFrames: "Vorher/Nachher-Bilder erzeugen",
    visVideo: "Animation erzeugen",
    visHintPhoto: "Nutzt dein Foto als Szene. Video dauert 1–3 Minuten.",
    visHintNoPhoto: "Ohne Foto wird eine typische Alltagsszene erzeugt. Video dauert 1–3 Minuten.",
    visStages: { queued: "Startet …", render: "Rendere Modell …", frames: "Nano Banana erzeugt Start- und Endbild …", upload: "Lade Bilder hoch …", video: "Omni erzeugt das Video …", download: "Lade Video …", done: "Fertig" },
    visStart: "Start", visEnd: "Geschafft", visOld: "Diese Visualisierung gehört zu Version {v}.",
    recentEmpty: "Noch keine gespeicherten Ergebnisse.",
    impChips: ["Rheumatoide Arthritis, schwacher Griff", "Tremor in beiden Händen", "Nur eine Hand nutzbar (Schlaganfall)", "Tetraplegie C6 – kein aktiver Faustschluss"],
    actChips: ["Haustür aufschließen", "Mit Löffel essen", "Marmeladenglas öffnen", "Stift halten und schreiben", "Aus einem Becher trinken", "Karten spielen"],
  },
  en: {
    skip: "Skip to form",
    tagline: "From everyday barrier to print-ready assistive device",
    mediaTitle: "Show the situation",
    dropText: "Upload a photo or short video",
    dropHint: "e.g. the key, the jar, the hand trying – ideally with a coin/card for scale",
    impTitle: "Impairment",
    impPh: "e.g. rheumatoid arthritis, very weak pinch grip",
    actTitle: "Activity",
    actPh: "e.g. unlock the front door independently",
    notesTitle: "Measurements & notes (optional)",
    notesPh: "e.g. key head 24 × 22 mm, lid Ø 82 mm, left-handed",
    micLabel: "Voice input",
    micStart: "Start voice input",
    micStop: "Stop recording",
    micBusy: "Transcribing …",
    reviewLabel: "Gemini reviews the rendered model and fixes it",
    go: "Generate assistive device",
    working: "Generating …",
    libTitle: "Or: open a template directly",
    recentTitle: "Saved results",
    resultTitle: "Result",
    emptyText: "Your assistive device will appear here as a print-ready 3D model.",
    wire: "Wireframe",
    resetView: "Reset view",
    playAnim: "Show usage",
    stopAnim: "Stop animation",
    dlStl: "Download STL",
    dlScad: ".scad",
    confidence: "Confidence",
    loopTitle: "Agentic loop – every version is checked and improved",
    tabAnalysis: "Analysis",
    tabParams: "Parameters",
    tabPrint: "Print & use",
    tabReview: "Review",
    tabVisual: "How it could look",
    tabCode: "Code",
    rebuild: "Rebuild",
    copy: "Copy",
    copied: "Copied",
    refineLabel: "Not quite right? Describe the change:",
    refinePh: "e.g. grip 5 mm thicker, longer lever",
    refineGo: "Adjust",
    footer: "Prototype – have assistive devices checked by an occupational therapist before daily use. Photos and videos are only sent to Gemini for processing.",
    steps: {
      analyze: "Understand situation", design: "Choose design", compile: "Build 3D model",
      improve: "Check & improve", review: "Self-review", refine: "Adjustment",
    },
    sources: {
      initial: "first draft", repair: "code repaired", review_fix: "after Gemini critique", checks_fix: "after print checks",
      refine: "your change", manual: "sliders", compile_error: "compile error", fix_failed: "fix discarded",
    },
    viewingOld: "You are viewing version {v} – the current one is version {c}.",
    changedParams: "Changed parameters",
    critique: "Gemini critique",
    checksShort: "Print checks",
    checksBadge: "Printability {p}/{n}",
    approachTemplate: "Template", approachCustom: "Custom CAD design",
    task: "Task", observed: "Observed", limitations: "Functional limitations",
    root: "Root problem", requirements: "Requirements", measurements: "Measurements", assumptions: "Assumptions",
    scale: "Scale", scaleNone: "No reference object found – typical sizes assumed.",
    questions: "For a better fit", srcUser: "given", srcRef: "via reference", srcMedia: "estimated", srcTypical: "typical",
    printSettings: "Print settings", material: "Material", layer: "Layer height", infill: "Infill",
    walls: "Walls", supports: "Supports", orientation: "Orientation", yes: "yes", no: "no",
    model: "Model", size: "Size", volume: "Volume", weight: "Weight (rough)", bed: "Fits print bed",
    usage: "How to use it", safety: "Safety", compileTime: "OpenSCAD time",
    autoChecks: "Automated printability checks",
    reviewNone: "No Gemini review for this version (disabled or after a manual change).",
    reviewOk: "Gemini reviewed the model – no changes needed.",
    reviewNeeds: "Gemini suggested improvements.",
    reviewIssues: "Findings", reviewViews: "What Gemini saw",
    designNotes: "Design notes", noParams: "No adjustable parameters.",
    rebuilding: "Rebuilding …", rebuilt: "Done – version", errorPrefix: "Error: ",
    missingInput: "Please describe the impairment and the activity.",
    aiLabel: "AI visualization",
    aiNote: "shows what real use could look like – not to scale.",
    visFrames: "Generate before/after images",
    visVideo: "Generate animation",
    visHintPhoto: "Uses your photo as the scene. Video takes 1–3 minutes.",
    visHintNoPhoto: "Without a photo a typical everyday scene is generated. Video takes 1–3 minutes.",
    visStages: { queued: "Starting …", render: "Rendering model …", frames: "Nano Banana creates start and end image …", upload: "Uploading images …", video: "Omni creates the video …", download: "Downloading video …", done: "Done" },
    visStart: "Start", visEnd: "Done", visOld: "This visualization belongs to version {v}.",
    recentEmpty: "No saved results yet.",
    impChips: ["Rheumatoid arthritis, weak grip", "Tremor in both hands", "Only one usable hand (stroke)", "Tetraplegia C6 – no active fist"],
    actChips: ["Unlock the front door", "Eat with a spoon", "Open a jam jar", "Hold a pen and write", "Drink from a cup", "Play cards"],
  },
};

let lang = (() => { try { return localStorage.getItem("lang") || "de"; } catch { return "de"; } })();
const t = (k) => I18N[lang][k] ?? k;
const tf = (k, vars) => t(k).replace(/\{(\w+)\}/g, (_, n) => vars[n] ?? "");

function applyI18n() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll(".lang button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  document.querySelectorAll(".mic").forEach((b) => { b.title = t("micStart"); });
  renderChips();
  if (currentJob) renderJob(currentJob, { force: true });
  loadRecent();
}

document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => {
  lang = b.dataset.lang;
  try { localStorage.setItem("lang", lang); } catch {}
  applyI18n();
}));

// ------------------------------------------------------------------ helpers
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const list = (arr) => (arr && arr.length ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "<p class='muted'>–</p>");
const fmt = (v) => (v == null || Number.isNaN(+v) ? "–" : Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : String(+(+v).toFixed(2)));

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

// ------------------------------------------------------------------ chips
function renderChips() {
  for (const [id, key, target] of [["chips-imp", "impChips", "impairment"], ["chips-act", "actChips", "activity"]]) {
    const box = $(id);
    box.innerHTML = "";
    for (const text of t(key)) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = text;
      b.addEventListener("click", () => { $(target).value = text; $(target).focus(); });
      box.appendChild(b);
    }
  }
}

// ------------------------------------------------------------------ media upload
let mediaFiles = [];
const drop = $("drop");
$("files").addEventListener("change", (e) => addFiles(e.target.files));
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));

function addFiles(fileList) {
  for (const f of fileList) {
    if (!/^(image|video)\//.test(f.type)) continue;
    if (mediaFiles.length >= 6) break;
    mediaFiles.push(f);
  }
  $("files").value = "";
  renderThumbs();
}

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  mediaFiles.forEach((f, i) => {
    const d = document.createElement("div");
    d.className = "thumb";
    const url = URL.createObjectURL(f);
    d.innerHTML = f.type.startsWith("video/")
      ? `<video src="${url}" muted playsinline></video><span class="tag">Video</span>`
      : `<img src="${url}" alt="">`;
    const rm = document.createElement("button");
    rm.type = "button"; rm.textContent = "×"; rm.setAttribute("aria-label", `Remove ${f.name}`);
    rm.addEventListener("click", () => { mediaFiles.splice(i, 1); renderThumbs(); });
    d.appendChild(rm);
    box.appendChild(d);
  });
}

// Grab one frame of a video in the browser (used as scene photo for the AI visualization:
// video inputs to the video model are not available in the EEA, still images are).
function extractStill(file) {
  return new Promise((resolve) => {
    const v = document.createElement("video");
    v.muted = true; v.playsInline = true; v.preload = "auto";
    v.src = URL.createObjectURL(file);
    const done = (blob) => { URL.revokeObjectURL(v.src); resolve(blob); };
    v.addEventListener("loadedmetadata", () => {
      v.currentTime = Math.max(0, Math.min(v.duration * 0.4, v.duration - 0.1)) || 0;
    }, { once: true });
    v.addEventListener("seeked", () => {
      const scale = Math.min(1, 1280 / Math.max(v.videoWidth, v.videoHeight, 1));
      const c = document.createElement("canvas");
      c.width = Math.round(v.videoWidth * scale); c.height = Math.round(v.videoHeight * scale);
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
      c.toBlob((b) => done(b), "image/jpeg", 0.9);
    }, { once: true });
    v.addEventListener("error", () => done(null), { once: true });
    setTimeout(() => done(null), 8000);
  });
}

// ------------------------------------------------------------------ voice input
let recorder = null;
document.querySelectorAll(".mic").forEach((btn) => btn.addEventListener("click", () => toggleMic(btn)));

async function toggleMic(btn) {
  if (btn.classList.contains("busy")) return;
  if (recorder && recorder.btn === btn) { recorder.stop(); return; }
  if (recorder) recorder.stop();
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (e) { showError(e.message); return; }
  const chunks = [];
  const rec = new MediaRecorder(stream);
  rec.btn = btn;
  rec.addEventListener("dataavailable", (e) => e.data.size && chunks.push(e.data));
  rec.addEventListener("stop", async () => {
    stream.getTracks().forEach((tr) => tr.stop());
    recorder = null;
    btn.setAttribute("aria-pressed", "false");
    btn.title = t("micStart");
    const blob = new Blob(chunks, { type: (rec.mimeType || "audio/webm").split(";")[0] });
    if (!blob.size) return;
    btn.classList.add("busy"); btn.title = t("micBusy");
    try {
      const fd = new FormData();
      fd.append("audio", blob, "speech." + (blob.type.split("/")[1] || "webm"));
      fd.append("language", lang);
      const { text } = await api("/api/transcribe", { method: "POST", body: fd });
      const ta = $(btn.dataset.target);
      ta.value = (ta.value.trim() ? ta.value.trim() + " " : "") + text;
      ta.focus();
    } catch (e) { showError(e.message); }
    finally { btn.classList.remove("busy"); btn.title = t("micStart"); }
  });
  rec.start();
  recorder = rec;
  btn.setAttribute("aria-pressed", "true");
  btn.title = t("micStop");
}

// ------------------------------------------------------------------ 3D viewer
const viewerEl = $("viewer");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
viewerEl.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.5, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a9590, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(150, 260, 180);
scene.add(sun);
const fill = new THREE.DirectionalLight(0xffffff, 0.7);
fill.position.set(-200, 80, -150);
scene.add(fill);
const grid = new THREE.GridHelper(220, 22, 0x7a8a85, 0xc4ccc9);
grid.material.transparent = true; grid.material.opacity = 0.55;
scene.add(grid);
const material = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.55, metalness: 0.05 });
let mesh = null;
let meshOffset = new THREE.Vector3();
let fitState = null;
let anim = null;
let animStart = 0;
const clock = new THREE.Clock();

function resize() {
  const w = viewerEl.clientWidth, h = viewerEl.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewerEl);
resize();
(function loop() {
  if (anim) {
    const el = clock.getElapsedTime() - animStart;
    try { anim.update(el % anim.duration); } catch (e) { console.error(e); stopAnimation(); }
  }
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();

function fitCamera(scaleUp = 1) {
  if (!fitState) return;
  const { size, center } = fitState;
  const r = Math.max(size.x, size.y, size.z) * 0.5 * scaleUp;
  const dist = r / Math.sin((camera.fov * Math.PI) / 360) * 1.25;
  camera.position.set(center.x + dist * 0.75, center.y + dist * 0.6, center.z + dist * 0.85);
  controls.target.copy(center);
  camera.near = dist / 100; camera.far = dist * 20; camera.updateProjectionMatrix();
  controls.update();
}

const loader = new STLLoader();
function loadStl(url) {
  stopAnimation();
  return new Promise((resolve, reject) => loader.load(url, (geo) => {
    geo.rotateX(-Math.PI / 2);                // OpenSCAD is Z-up, three.js is Y-up
    geo.computeBoundingBox();
    const bb = geo.boundingBox;
    const c = new THREE.Vector3(); bb.getCenter(c);
    meshOffset = new THREE.Vector3(-c.x, -bb.min.y, -c.z);
    geo.translate(meshOffset.x, meshOffset.y, meshOffset.z);  // stand on the "print bed"
    geo.computeVertexNormals();
    geo.computeBoundingBox();
    if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); }
    mesh = new THREE.Mesh(geo, material);
    scene.add(mesh);
    const size = new THREE.Vector3(); geo.boundingBox.getSize(size);
    const center = new THREE.Vector3(); geo.boundingBox.getCenter(center);
    const firstLoad = !fitState;
    fitState = { size, center };
    if (firstLoad) fitCamera();
    $("empty").hidden = true;
    resolve();
  }, undefined, reject));
}

$("btn-reset").addEventListener("click", () => fitCamera(anim ? 2.2 : 1));
$("btn-wire").addEventListener("click", (e) => {
  material.wireframe = !material.wireframe;
  e.currentTarget.setAttribute("aria-pressed", String(material.wireframe));
});

// ------------------------------------------------------------------ usage animation (three.js, no API)
function paramsObject(job) {
  return Object.fromEntries((job.params || []).map((p) => [p.name, p.value]));
}

function canAnimate(job) {
  return !!(usageAnim && job && job.approach === "template" && usageAnim.hasUsageAnimation(job.template_id));
}

function updateAnimButton(job) {
  const b = $("btn-anim");
  b.hidden = !canAnimate(job) || viewingVersion !== job.version;
  b.textContent = anim ? t("stopAnim") : t("playAnim");
  b.setAttribute("aria-pressed", String(!!anim));
}

function startAnimation() {
  if (!canAnimate(currentJob) || !mesh) return;
  stopAnimation();
  anim = usageAnim.createUsageAnimation({
    THREE, scene, deviceMesh: mesh, templateId: currentJob.template_id,
    params: paramsObject(currentJob), offset: meshOffset.clone(),
  });
  animStart = clock.getElapsedTime();
  fitCamera(2.2);
  updateAnimButton(currentJob);
}

function stopAnimation() {
  if (!anim) return;
  try { anim.dispose(); } catch (e) { console.error(e); }
  anim = null;
  if (currentJob) updateAnimButton(currentJob);
}

$("btn-anim").addEventListener("click", () => { if (anim) { stopAnimation(); fitCamera(); } else startAnimation(); });

// ------------------------------------------------------------------ tabs
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => selectTab(b.dataset.tab)));
function selectTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".tab-panel").forEach((p) => { p.hidden = p.id !== `tab-${name}`; });
}

// ------------------------------------------------------------------ job rendering
let currentJob = null;
let loadedUrl = "";
let viewingVersion = 0;
let pollTimer = null;
let renderedKey = "";

function renderSteps(job) {
  const ol = $("steps");
  ol.hidden = !job.steps?.length;
  const icon = { done: "✓", error: "✕", skipped: "–" };
  ol.innerHTML = (job.steps || []).map((s) => `
    <li class="${s.status}">
      <span class="icon" aria-hidden="true">${icon[s.status] || ""}</span>
      <div><strong>${esc(t("steps")[s.key] || s.key)}</strong><small>${esc(s.detail || "")}</small></div>
    </li>`).join("");
}

function srcLabel(src) {
  const s = (src || "").toLowerCase();
  if (s.startsWith("user")) return `<span class="src user">${t("srcUser")}</span>`;
  if (s.startsWith("ref")) return `<span class="src user">${t("srcRef")}</span>`;
  if (s.startsWith("media")) return `<span class="src">${t("srcMedia")}</span>`;
  return `<span class="src">${t("srcTypical")}</span>`;
}

function renderAnalysis(job) {
  const p = job.plan;
  if (!p) {
    $("tab-analysis").innerHTML = `<p class="muted">${esc(job.template_name || "")}</p>`;
    return;
  }
  const meas = p.measurements?.length
    ? `<table class="kv">${p.measurements.map((m) => `<tr><th>${esc(m.name)}</th><td>${fmt(m.value_mm)} mm ${srcLabel(m.source)}</td></tr>`).join("")}</table>`
    : "<p class='muted'>–</p>";
  const sr = p.scale_reference;
  const scale = sr && sr.detected
    ? `<div class="note">${t("scale")}: <b>${esc(sr.object)}</b> (${fmt(sr.known_size_mm)} mm) – ${esc(sr.method)}</div>`
    : `<div class="note muted">${t("scaleNone")}${sr?.method ? " " + esc(sr.method) : ""}</div>`;
  $("tab-analysis").innerHTML = `
    <div class="grid2">
      <div>
        <h4>${t("task")}</h4><p>${esc(p.task_summary)}</p>
        <h4>${t("observed")}</h4><p>${esc(p.observed_in_media)}</p>
        <h4>${t("root")}</h4><p>${esc(p.root_problem)}</p>
        <h4>${t("limitations")}</h4>${list(p.functional_limitations)}
      </div>
      <div>
        <h4>${t("requirements")}</h4>${list(p.design_requirements)}
        <h4>${t("measurements")}</h4>${scale}<div style="height:8px"></div>${meas}
        <h4>${t("assumptions")}</h4>${list(p.assumptions)}
        ${p.questions_for_user?.length ? `<h4>${t("questions")}</h4>${list(p.questions_for_user)}` : ""}
      </div>
    </div>`;
}

function renderParams(job) {
  const box = $("params");
  if (!job.params?.length) { box.innerHTML = `<p class="muted">${t("noParams")}</p>`; return; }
  box.innerHTML = job.params.map((p, i) => `
    <div class="param">
      <label for="pn-${i}">${esc(p.name)}</label>
      <input type="range" id="pr-${i}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}" aria-label="${esc(p.name)}">
      <input type="number" id="pn-${i}" min="${p.min}" max="${p.max}" step="${p.step}" value="${fmt(p.value)}" data-name="${esc(p.name)}">
      <small>${esc(p.description)} · ${fmt(p.min)}–${fmt(p.max)}</small>
    </div>`).join("");
  job.params.forEach((_, i) => {
    const r = $(`pr-${i}`), n = $(`pn-${i}`);
    r.addEventListener("input", () => { n.value = r.value; });
    n.addEventListener("input", () => { r.value = n.value; });
  });
}

function checksHtml(checks) {
  if (!checks?.checks?.length) return "";
  const icon = { pass: "✓", warn: "!", fail: "✕" };
  return `<ul class="checks">${checks.checks.map((c) => `
    <li class="${c.status}">
      <span class="ci" aria-hidden="true">${icon[c.status] || "?"}</span>
      <span>${esc(lang === "de" ? c.label_de : c.label_en)}</span>
      <span class="cv">${esc(c.value)}</span>
      ${(lang === "de" ? c.detail_de : c.detail_en) ? `<small>${esc(lang === "de" ? c.detail_de : c.detail_en)}</small>` : ""}
    </li>`).join("")}</ul>`;
}

function renderPrint(job) {
  const p = job.plan, s = job.stats || {};
  const ps = p?.print_settings;
  const statsTable = s.size_mm ? `
    <table class="kv">
      <tr><th>${t("size")}</th><td>${s.size_mm.map(fmt).join(" × ")} mm</td></tr>
      <tr><th>${t("volume")}</th><td>${s.volume_cm3} cm³</td></tr>
      <tr><th>${t("weight")}</th><td>≈ ${s.weight_estimate_g} g PLA</td></tr>
      <tr><th>${t("bed")}</th><td>${s.fits_bed ? "✓" : "✕"} (${s.bed_mm.join(" × ")} mm)</td></tr>
      <tr><th>${t("compileTime")}</th><td>${job.compile?.seconds ?? "–"} s</td></tr>
    </table>` : "";
  const psTable = ps ? `
    <table class="kv">
      <tr><th>${t("material")}</th><td>${esc(ps.material)}</td></tr>
      <tr><th>${t("layer")}</th><td>${ps.layer_height_mm} mm</td></tr>
      <tr><th>${t("infill")}</th><td>${ps.infill_percent} %</td></tr>
      <tr><th>${t("walls")}</th><td>${ps.walls}</td></tr>
      <tr><th>${t("supports")}</th><td>${ps.supports ? t("yes") : t("no")}</td></tr>
      <tr><th>${t("orientation")}</th><td>${esc(ps.orientation)}</td></tr>
    </table>${ps.notes ? `<p class="muted" style="margin-top:8px">${esc(ps.notes)}</p>` : ""}` : "";
  $("tab-print").innerHTML = `
    <div class="grid2">
      <div>${psTable ? `<h4>${t("printSettings")}</h4>${psTable}` : ""}<h4>${t("model")}</h4>${statsTable}</div>
      <div>
        ${p ? `<h4>${t("usage")}</h4>${p.usage_steps?.length ? `<ol>${p.usage_steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}` : ""}
        ${p ? `<h4>${t("safety")}</h4><div class="note warn">${list(p.safety_notes)}</div>` : ""}
      </div>
    </div>`;
}

function renderReview(job) {
  const r = job.review;
  let html = `<h4>${t("autoChecks")}</h4>${checksHtml(job.checks) || "<p class='muted'>–</p>"}`;
  if (!r) {
    html += `<h4>${t("critique")}</h4><p class="muted">${t("reviewNone")}</p>`;
  } else {
    const ok = r.meets_requirements && r.printable;
    html += `<h4>${t("critique")}</h4><div class="note">${esc(ok ? t("reviewOk") : t("reviewNeeds"))}<br><span class="muted">${esc(r.summary)}</span></div>
      ${r.issues?.length ? `<h4>${t("reviewIssues")}</h4>${list(r.issues)}` : ""}`;
  }
  if (job.preview_urls?.length > 1) {
    html += `<h4>${t("reviewViews")}</h4><div class="previews">${job.preview_urls.map((u) => `<img src="${u}" alt="">`).join("")}</div>`;
  }
  if (job.design_notes) html += `<h4>${t("designNotes")}</h4><p>${esc(job.design_notes)}</p>`;
  $("tab-review").innerHTML = html;
}

function checksBadge(job) {
  const b = $("check-badge");
  const c = job.checks?.counts;
  if (!c) { b.hidden = true; return; }
  const n = (c.pass || 0) + (c.warn || 0) + (c.fail || 0);
  b.hidden = false;
  b.className = `check-badge ${c.fail ? "fail" : c.warn ? "warn" : "ok"}`;
  b.textContent = (c.fail ? "✕ " : c.warn ? "! " : "✓ ") + tf("checksBadge", { p: c.pass || 0, n });
}
$("check-badge").addEventListener("click", () => selectTab("review"));

// ---- agentic loop timeline
function dotClass(counts) {
  if (!counts) return "";
  return counts.fail ? "fail" : counts.warn ? "warn" : "ok";
}

function renderTimeline(job) {
  const its = job.iterations || [];
  $("loop").hidden = !its.length;
  $("timeline").innerHTML = its.map((it, i) => {
    const label = t("sources")[it.source] || it.source;
    if (it.version == null) {
      return `<li><span class="iter err" title="${esc(it.note || it.error || "")}">✕ <span class="src-l">${esc(label)}</span></span></li>`;
    }
    return `<li><button type="button" class="iter" data-i="${i}" aria-pressed="${it.version === viewingVersion}">
      ${it.preview_url ? `<img src="${it.preview_url}" alt="">` : ""}
      <b>v${it.version}</b><span class="src-l">${esc(label)}</span>
      <span class="dot ${dotClass(it.checks)}" title="${t("checksShort")}"></span>
      ${it.verdict === "ok" ? "✓" : it.verdict === "needs_fix" ? "↻" : ""}
    </button></li>`;
  }).join("");
  $("timeline").querySelectorAll("button.iter").forEach((b) => b.addEventListener("click", () => viewIteration(job, its[+b.dataset.i])));
  const cur = its.find((it) => it.version === viewingVersion);
  renderIterDetail(cur);
}

function renderIterDetail(it) {
  const box = $("iter-detail");
  if (!it) { box.innerHTML = ""; return; }
  const parts = [];
  if (it.note) parts.push(`<div class="muted">${esc(it.note)}</div>`);
  const changed = Object.entries(it.changed || {});
  if (changed.length) parts.push(`<div><b>${t("changedParams")}:</b> ${changed.map(([k, [a, b]]) => `<span class="chg">${esc(k)} ${fmt(a)} → ${fmt(b)}</span>`).join("")}</div>`);
  if (it.critique) parts.push(`<div><b>${t("critique")}:</b> ${esc(it.critique)}${it.issues?.length ? list(it.issues) : ""}</div>`);
  if (it.checks) parts.push(`<div><b>${t("checksShort")}:</b> ${it.checks.pass || 0} ✓ · ${it.checks.warn || 0} ! · ${it.checks.fail || 0} ✕${it.checks_feedback ? ` <span class="muted">– ${esc(it.checks_feedback)}</span>` : ""}</div>`);
  box.innerHTML = parts.join("");
}

function viewIteration(job, it) {
  if (!it || !it.stl_url) return;
  viewingVersion = it.version;
  showStl(it.stl_url, it.version);
  $("viewing-old").hidden = it.version === job.version;
  $("viewing-old").textContent = tf("viewingOld", { v: it.version, c: job.version });
  renderTimeline(job);
  updateAnimButton(job);
}

function showStl(url, version) {
  const u = `${url}?v=${version}`;
  if (u === loadedUrl) return;
  loadedUrl = u;
  loadStl(u).catch((e) => console.error(e));
}

// ---- AI visualization
let visPolling = false;
function renderVisual(job) {
  const v = job.visual || { status: "idle" };
  const running = v.status === "running";
  $("vis-frames").disabled = running || !job.stl_url;
  $("vis-video").disabled = running || !job.stl_url;
  $("vis-hint").textContent = job.has_photo ? t("visHintPhoto") : t("visHintNoPhoto");
  let status = "";
  if (running) status = (t("visStages")[v.stage] || v.stage || "") + (v.detail ? ` ${v.detail}` : "");
  else if (v.status === "error") status = t("errorPrefix") + (v.error || "");
  else if (v.status === "done" && v.version && v.version !== job.version) status = tf("visOld", { v: v.version });
  $("vis-status").textContent = status;
  const frames = [];
  if (v.start_url) frames.push(`<figure><img src="${v.start_url}" alt=""><figcaption>${t("visStart")}</figcaption></figure>`);
  if (v.end_url) frames.push(`<figure><img src="${v.end_url}" alt=""><figcaption>${t("visEnd")}</figcaption></figure>`);
  const fo = $("vis-frames-out");
  const html = frames.join("");
  if (fo.dataset.html !== html) { fo.innerHTML = html; fo.dataset.html = html; }
  const player = $("vis-player");
  if (v.video_url) {
    if (player.dataset.src !== v.video_url) { player.src = v.video_url; player.dataset.src = v.video_url; player.play().catch(() => {}); }
    player.hidden = false;
  } else { player.hidden = true; player.removeAttribute("src"); player.dataset.src = ""; }
}

async function startVisual(withVideo) {
  if (!currentJob) return;
  try {
    await api(`/api/jobs/${currentJob.id}/visualize`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ with_video: withVideo }),
    });
    poll(currentJob.id);
  } catch (e) { $("vis-status").textContent = t("errorPrefix") + e.message; }
}
$("vis-frames").addEventListener("click", () => startVisual(false));
$("vis-video").addEventListener("click", () => startVisual(true));

// ---- main render
function renderJob(job, { force = false } = {}) {
  const sameJob = currentJob && currentJob.id === job.id;
  currentJob = job;
  renderSteps(job);
  renderVisual(job);
  if (!job.stl_url) return;
  const key = `${job.id}:${job.version}:${job.status}:${job.review ? 1 : 0}:${(job.iterations || []).length}:${lang}`;
  if (key === renderedKey && !force) return;
  const newVersion = !sameJob || !renderedKey.startsWith(`${job.id}:${job.version}:`);
  renderedKey = key;
  if (newVersion) {
    viewingVersion = job.version;
    $("viewing-old").hidden = true;
    showStl(job.stl_url, job.version);
  }
  $("viewer-bar").hidden = false;
  $("result").hidden = false;
  $("dl-stl").href = job.stl_url;
  $("dl-stl").setAttribute("download", `${(job.plan?.device_name || job.template_id || "aid").replace(/[^\w-]+/g, "_")}.stl`);
  $("dl-scad").href = job.scad_url;
  const s = job.stats || {};
  $("dims").textContent = s.size_mm ? `${s.size_mm.map(fmt).join(" × ")} mm · ≈ ${s.weight_estimate_g} g` : "";
  $("approach").textContent = job.approach === "template"
    ? `${t("approachTemplate")} · ${job.template_name || job.template_id}` : t("approachCustom");
  $("device-name").textContent = job.plan?.device_name || job.template_name || "";
  $("how-it-helps").textContent = job.plan?.how_it_helps || "";
  if (job.plan) {
    $("confidence-wrap").hidden = false;
    $("confidence").style.width = `${Math.round(Math.max(0, Math.min(1, job.plan.confidence)) * 100)}%`;
  } else {
    $("confidence-wrap").hidden = true;
  }
  checksBadge(job);
  renderTimeline(job);
  renderAnalysis(job);
  renderParams(job);
  renderPrint(job);
  renderReview(job);
  updateAnimButton(job);
  $("code").textContent = job.code || "";
}

function setBusy(busy) {
  $("go").disabled = busy;
  $("go").querySelector("span").textContent = busy ? t("working") : t("go");
}

async function poll(jobId) {
  clearTimeout(pollTimer);
  try {
    const job = await api(`/api/jobs/${jobId}`);
    renderJob(job);
    const busy = job.status === "running" || job.status === "queued";
    const visBusy = job.visual?.status === "running";
    if (busy || visBusy) {
      pollTimer = setTimeout(() => poll(jobId), busy ? 1200 : 2500);
    }
    if (!busy) {
      setBusy(false);
      if (job.status === "error") showError(job.error);
    }
    if (!busy && !visBusy) loadRecent();
  } catch (e) {
    pollTimer = setTimeout(() => poll(jobId), 2500);
  }
}

function showError(msg) {
  const el = $("form-error");
  el.hidden = !msg;
  el.textContent = msg ? t("errorPrefix") + msg : "";
}

function openJob(jobId) {
  stopAnimation();
  loadedUrl = "";
  renderedKey = "";
  fitState = null;
  showError("");
  try { history.replaceState(null, "", `?job=${jobId}`); } catch {}
  poll(jobId);
}

// ------------------------------------------------------------------ actions
$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const impairment = $("impairment").value.trim();
  const activity = $("activity").value.trim();
  if (!impairment || !activity) { showError(t("missingInput")); return; }
  setBusy(true);
  showError("");
  const fd = new FormData();
  fd.append("impairment", impairment);
  fd.append("activity", activity);
  fd.append("notes", $("notes").value.trim());
  fd.append("language", lang);
  fd.append("review", $("review").checked ? "true" : "false");
  mediaFiles.forEach((f) => fd.append("files", f, f.name));
  const firstVideo = mediaFiles.find((f) => f.type.startsWith("video/"));
  if (firstVideo && !mediaFiles.some((f) => f.type.startsWith("image/"))) {
    const still = await extractStill(firstVideo);
    if (still) fd.append("still", still, "still.jpg");
  }
  try {
    const { job_id } = await api("/api/jobs", { method: "POST", body: fd });
    selectTab("analysis");
    openJob(job_id);
  } catch (err) {
    setBusy(false);
    showError(err.message);
  }
});

$("rebuild").addEventListener("click", async () => {
  if (!currentJob) return;
  const params = {};
  document.querySelectorAll("#params input[type=number]").forEach((n) => { params[n.dataset.name] = parseFloat(n.value); });
  $("rebuild").disabled = true;
  $("rebuild-status").textContent = t("rebuilding");
  try {
    const job = await api(`/api/jobs/${currentJob.id}/rebuild`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ params }),
    });
    renderJob(job);
    $("rebuild-status").textContent = `${t("rebuilt")} ${job.version}`;
  } catch (err) {
    $("rebuild-status").textContent = t("errorPrefix") + err.message;
  } finally {
    $("rebuild").disabled = false;
  }
});

$("refine").addEventListener("submit", async (e) => {
  e.preventDefault();
  const feedback = $("feedback").value.trim();
  if (!feedback || !currentJob) return;
  setBusy(true);
  try {
    await api(`/api/jobs/${currentJob.id}/refine`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feedback }),
    });
    $("feedback").value = "";
    poll(currentJob.id);
  } catch (err) {
    setBusy(false);
    showError(err.message);
  }
});

$("copy-code").addEventListener("click", async (e) => {
  try { await navigator.clipboard.writeText($("code").textContent); e.currentTarget.textContent = t("copied"); } catch {}
  setTimeout(() => { $("copy-code").textContent = t("copy"); }, 1500);
});

// ------------------------------------------------------------------ saved results
async function loadRecent() {
  try {
    const jobs = await api("/api/jobs");
    const box = $("recent-list");
    $("recent-wrap").hidden = !jobs.length;
    box.innerHTML = "";
    jobs.forEach((j) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost recent-item";
      const when = new Date(j.created * 1000).toLocaleString(lang === "de" ? "de-DE" : "en-GB", { dateStyle: "short", timeStyle: "short" });
      b.innerHTML = `<span>${esc(j.device_name || j.id)}${j.has_video ? " 🎬" : ""}</span><small>${esc(j.activity || "")} · v${j.version} · ${esc(when)}</small>`;
      b.addEventListener("click", () => { selectTab("analysis"); openJob(j.id); });
      box.appendChild(b);
    });
  } catch {}
}

// ------------------------------------------------------------------ init
async function init() {
  applyI18n();
  try {
    const h = await api("/api/health");
    $("pill-gemini").className = `pill ${h.gemini_key ? "ok" : "bad"}`;
    $("pill-gemini").title = Object.values(h.models).join(", ");
    $("pill-openscad").className = `pill ${h.openscad ? "ok" : "bad"}`;
  } catch {}
  try {
    const templates = await api("/api/templates");
    const box = $("lib-list");
    templates.forEach((tpl) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "ghost"; b.textContent = tpl.name; b.title = tpl.description;
      b.addEventListener("click", async () => {
        setBusy(true);
        try {
          const { job_id } = await api("/api/jobs/template", {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ template_id: tpl.id, language: lang }),
          });
          selectTab("params");
          openJob(job_id);
        } catch (err) { setBusy(false); showError(err.message); }
      });
      box.appendChild(b);
    });
  } catch {}
  const deep = new URLSearchParams(location.search).get("job");
  if (deep) openJob(deep);
}
init();
