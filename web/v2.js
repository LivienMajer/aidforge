import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

let usageAnim = null;
let storyboardMod = null;
import("/static/usage_anim.js").then((m) => { usageAnim = m; if (currentJob) updateAnimBtn(currentJob); }).catch(() => {});
import("/static/storyboard.js").then((m) => { storyboardMod = m; if (currentJob) renderVisual(currentJob); }).catch(() => {});

const I18N = {
  de: {
    newBtn: "+ Neu",
    heroTitle: "Welches Alltagsproblem lösen wir?",
    heroSub: "Foto oder kurze Beschreibung genügt – AidForge konstruiert ein druckfertiges 3D-Hilfsmittel.",
    dropText: "Foto oder Video hinzufügen (optional)",
    impTitle: "Was fällt schwer?",
    impPh: "z. B. Rheumatoide Arthritis, schwacher Pinzettengriff",
    actTitle: "Was soll klappen?",
    actPh: "z. B. Haustür selbstständig aufschließen",
    go: "Hilfsmittel bauen",
    working: "Wird konstruiert …",
    browseTemplates: "Vorlage direkt testen",
    browseRecent: "Letzte Ergebnisse",
    detailsLink: "Details & Code",
    playAnim: "Benutzung",
    stopAnim: "Stopp",
    tweakBtn: "Anpassen",
    previewBtn: "Foto-Vorschau",
    refineShort: "Text",
    rotateShort: "Drehen",
    dlStl: "STL",
    agentLoop: "Agentischer Loop",
    tweakTitle: "Maße & Form anpassen",
    rebuild: "Neu bauen",
    rebuilding: "Baue neu …",
    rebuilt: "Fertig · v",
    refinePh: "Passt noch nicht? z. B. Griff 5 mm dicker …",
    refineGo: "Ändern",
    previewTitle: "So sieht es im Alltag aus",
    visStory: "Fotostrecke erzeugen",
    visFrames: "Vorher / Nachher",
    visVideoExp: "Video (experimentell)",
    visStep: "Schritt",
    visStart: "Start",
    visEnd: "Geschafft",
    templatesTitle: "Vorlage direkt testen",
    recentTitle: "Letzte Ergebnisse",
    detailsTitle: "Analyse, Druck & OpenSCAD",
    copy: "Code kopieren",
    copied: "Kopiert ✓",
    approachTemplate: "Vorlage",
    approachCustom: "Eigenes Design",
    checksBadge: "Druckbar {p}/{n}",
    checksTitle: "Druckbarkeits-Checks",
    whyDesign: "Warum so konstruiert",
    howItHelpsTitle: "So hilft es",
    usageTitle: "Anwendung",
    safetyTitle: "Sicherheitshinweise",
    measTitle: "Maße",
    printTitle: "Druck-Empfehlung",
    codeTitle: "OpenSCAD-Code",
    noParams: "Keine Parameter.",
    missingInput: "Bitte beide Felder ausfüllen.",
    presets: [
      { label: "🔑 Schlüsseldreher", imp: "Rheumatoide Arthritis, schwacher Pinzettengriff", act: "Haustür selbstständig aufschließen" },
      { label: "🥄 Löffel-Griff", imp: "Starker Tremor in beiden Händen", act: "Ruhig mit dem Löffel essen" },
      { label: "🫙 Glas-Öffner", imp: "Nur eine Hand nutzbar (Schlaganfall)", act: "Marmeladenglas öffnen" },
    ],
    steps: {
      analyze: "Verstehe Situation & Maße …", design: "Synthetisiere CAD-Entwurf …", compile: "Kompiliere Manifold-STL …",
      improve: "Agentischer Prüf- & Korrektur-Loop …", review: "Prüfe Druckbarkeit …", refine: "Passe Modell an …",
    },
    hudKicker: "Agentische CAD-Pipeline",
    archFlow: "Gemini Vision → OpenSCAD 2021 → NumPy-Raycasting → Manifold STL",
    archD1: "1. Multimodale Analyse & Fotogrammetrie-Skalierung",
    archD2: "2. Parametrische Template-Wahl oder OpenSCAD-Synthese",
    archD3: "3. CGAL-Kompilierung mit automatischem Compile-Self-Repair",
    archD4: "4. Deterministische Mesh-Checks & Multi-View Vision-QA",
    stepPipe: [
      { key: "analyze", num: "01", label: "Multimodale Analyse", tech: "Gemini Vision · Fotogrammetrie", desc: "Erkennt Einschränkung, Objektgeometrie & Referenzmaße." },
      { key: "design", num: "02", label: "CAD-Synthese", tech: "Parametrik · OpenSCAD 2021", desc: "Wählt verifiziertes Template oder generiert parametrischen Code." },
      { key: "compile", num: "03", label: "Compile & Self-Repair", tech: "OpenSCAD CGAL · STL-Export", desc: "Kompiliert 3D-Mesh und repariert Syntaxfehler automatisch." },
      { key: "improve", num: "04", label: "Agentischer QA-Loop", tech: "NumPy-Raycasting · Multi-View", desc: "Prüft Wandstärke, 45°-Überhänge, Druckbett & Multi-Angle-Renders." },
    ],
    verSource: { initial: "Erstentwurf", review: "Geprüft", review_fix: "KI-Review-Fix", checks_fix: "Check-Fix", repair: "Repariert", manual: "Manuell", refine: "Angepasst" },
    visStages: {
      queued: "Startet …", render: "Rendere Posen …", frames: "Erzeuge Bilder …",
      storyboard: "Erzeuge Fotostrecke …", upload: "Lade hoch …", video: "Erzeuge Video …", download: "Lade …", done: "Fertig",
    },
  },
  en: {
    newBtn: "+ New",
    heroTitle: "Which everyday barrier should we solve?",
    heroSub: "A photo or short description is enough – AidForge builds a print-ready 3D assistive device.",
    dropText: "Add photo or video (optional)",
    impTitle: "What is difficult?",
    impPh: "e.g. rheumatoid arthritis, weak pinch grip",
    actTitle: "What should work?",
    actPh: "e.g. unlock the front door independently",
    go: "Build device",
    working: "Building …",
    browseTemplates: "Try a template",
    browseRecent: "Recent results",
    detailsLink: "Details & Code",
    playAnim: "Show use",
    stopAnim: "Stop",
    tweakBtn: "Adjust",
    previewBtn: "Photo preview",
    refineShort: "Text",
    rotateShort: "Rotate",
    dlStl: "STL",
    agentLoop: "Agentic loop",
    tweakTitle: "Adjust size & shape",
    rebuild: "Rebuild",
    rebuilding: "Rebuilding …",
    rebuilt: "Done · v",
    refinePh: "Not quite right? e.g. grip 5 mm thicker …",
    refineGo: "Apply",
    previewTitle: "How it looks in daily use",
    visStory: "Generate photo story",
    visFrames: "Before / After",
    visVideoExp: "Video (experimental)",
    visStep: "Step",
    visStart: "Start",
    visEnd: "Done",
    templatesTitle: "Try a template",
    recentTitle: "Recent results",
    detailsTitle: "Analysis, Print & OpenSCAD",
    copy: "Copy code",
    copied: "Copied ✓",
    approachTemplate: "Template",
    approachCustom: "Custom design",
    checksBadge: "Printable {p}/{n}",
    checksTitle: "Printability checks",
    whyDesign: "Design rationale",
    howItHelpsTitle: "How it helps",
    usageTitle: "How to use",
    safetyTitle: "Safety notes",
    measTitle: "Measurements",
    printTitle: "Print recommendation",
    codeTitle: "OpenSCAD code",
    noParams: "No parameters.",
    missingInput: "Please fill in both fields.",
    presets: [
      { label: "🔑 Key turner", imp: "Rheumatoid arthritis, weak pinch grip", act: "Unlock the front door independently" },
      { label: "🥄 Spoon grip", imp: "Strong tremor in both hands", act: "Eat steadily with a spoon" },
      { label: "🫙 Jar opener", imp: "Only one usable hand (stroke)", act: "Open a jam jar" },
    ],
    steps: {
      analyze: "Analyzing situation & scale …", design: "Synthesizing CAD design …", compile: "Compiling manifold STL …",
      improve: "Agentic review & repair loop …", review: "Checking printability …", refine: "Adapting model …",
    },
    hudKicker: "Agentic CAD pipeline",
    archFlow: "Gemini Vision → OpenSCAD 2021 → NumPy Raycasting → Manifold STL",
    archD1: "1. Multimodal analysis & photogrammetry scaling",
    archD2: "2. Parametric template selection or OpenSCAD synthesis",
    archD3: "3. CGAL compilation with automatic compile self-repair",
    archD4: "4. Deterministic mesh checks & multi-view vision QA",
    stepPipe: [
      { key: "analyze", num: "01", label: "Multimodal Analysis", tech: "Gemini Vision · Photogrammetry", desc: "Extracts functional limits, object geometry & scale." },
      { key: "design", num: "02", label: "CAD Synthesis", tech: "Parametric · OpenSCAD 2021", desc: "Selects verified template or writes parametric OpenSCAD code." },
      { key: "compile", num: "03", label: "Compile & Self-Repair", tech: "OpenSCAD CGAL · STL Export", desc: "Compiles 3D mesh and auto-repairs any compiler errors." },
      { key: "improve", num: "04", label: "Agentic QA Loop", tech: "NumPy Raycasting · Multi-View", desc: "Checks wall thickness, 45° overhangs, bed fit & rendered views." },
    ],
    verSource: { initial: "Initial", review: "Reviewed", review_fix: "AI review fix", checks_fix: "Check fix", repair: "Repaired", manual: "Manual", refine: "Refined" },
    visStages: {
      queued: "Starting …", render: "Rendering poses …", frames: "Generating images …",
      storyboard: "Generating photo story …", upload: "Uploading …", video: "Generating video …", download: "Downloading …", done: "Done",
    },
  },
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v) => (v == null || Number.isNaN(+v) ? "–" : Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : String(+(+v).toFixed(2)));

let lang = (() => { try { return localStorage.getItem("lang") || "de"; } catch { return "de"; } })();
const t = (k) => I18N[lang][k] ?? k;
const tf = (k, vars) => t(k).replace(/\{(\w+)\}/g, (_, n) => vars[n] ?? "");

const TPL_I18N = {
  built_up_handle: {
    de: {
      name: "Verdickter Ergonomie-Griff",
      one_liner: "Dicker Griff mit Fingerrillen zum Aufstecken auf Besteck, Stifte oder Zahnbürsten.",
      context: "Schwacher Griff · Alltagshilfen sicher greifen",
      reqs: ["Dicker Griff ersetzt feinen Pinzettengriff", "Fingerrillen geben sicheren Halt", "Abgeflachte Seite verhindert Wegrollen"],
    },
    en: {
      name: "Built-up handle",
      one_liner: "Thick ergonomic grip with finger grooves for cutlery, pens, or toothbrushes.",
      context: "Weak grip · Hold everyday utensils securely",
      reqs: ["Thick grip replaces fine pinch grip", "Finger grooves improve hold", "Flat side prevents rolling"],
    },
  },
  universal_cuff: {
    de: {
      name: "Universal-Handmanschette",
      one_liner: "C-förmige Manschette um die Handfläche mit Stecktasche für Besteck oder Stifte.",
      context: "Kein aktiver Griff · Besteck oder Stift ohne Greifen halten",
      reqs: ["Hält sicher an der Handfläche ohne Fingerkraft", "Stecktasche nimmt Standard-Griffe auf", "Weiche Kanten für angenehmen Hautkontakt"],
    },
    en: {
      name: "Universal cuff",
      one_liner: "C-shaped palm band with a pocket that holds a utensil or pen without gripping.",
      context: "No active grip · Hold utensil without finger strength",
      reqs: ["Rests around palm without finger force", "Pocket holds standard handles", "Smooth edges for skin comfort"],
    },
  },
  key_turner: {
    de: {
      name: "Ergonomischer Hebel-Schlüsseldreher",
      one_liner: "Breiter Hebelgriff, der einen Türschlüssel ohne schmerzhaften Kneifgriff dreht.",
      context: "Rheumatoide Arthritis, schwacher Pinzettengriff · Haustür selbstständig aufschließen",
      reqs: ["Vollhandgriff ersetzt den Kneifgriff", "Verlängerter Hebel reduziert den Kraftaufwand", "Dicker abgerundeter Griff schont die Gelenke", "M3-Schraube sichert Standard-Schlüssel"],
    },
    en: {
      name: "Ergonomic Lever Key Turner",
      one_liner: "Wide lever handle that turns a door key without pinching.",
      context: "Rheumatoid arthritis, weak pinch grip · Unlock the front door independently",
      reqs: ["Whole-hand grasp replaces pinch grip", "Extended lever reduces turning effort", "Thick chamfered handle protects joints", "M3 bolt secures standard key"],
    },
  },
  lever_turner: {
    de: {
      name: "Hebel-Drehhilfe für Deckel & Knöpfe",
      one_liner: "Gerippte Kappe mit Hebelarm für Schraubdeckel, Drehknöpfe oder Wasserhähne.",
      context: "Schwacher Griff · Deckel und Drehknöpfe mit Hebelkraft öffnen",
      reqs: ["Innenrippen greifen Deckel sicher", "Langer Hebel vervielfacht das Drehmoment", "Optional zwei Hebel für beidhändiges Drehen"],
    },
    en: {
      name: "Lever turner for lids, knobs and taps",
      one_liner: "Ribbed cap with one or two levers for jars, knobs, or taps.",
      context: "Weak grip · Turn lids and knobs with leverage",
      reqs: ["Internal ribs grip round caps", "Long lever multiplies torque", "Optional dual levers for two hands"],
    },
  },
  cup_holder: {
    de: {
      name: "Becherhalter mit zwei Griffen",
      one_liner: "Manschette für Becher oder Gläser mit ein oder zwei großen Greifhenkeln.",
      context: "Tremor oder schwacher Griff · Becher sicher halten und trinken",
      reqs: ["Große Henkel für sicheres Greifen", "Manschette umschließt konische Becher", "Bodenlippe verhindert Durchrutschen"],
    },
    en: {
      name: "Two-handled cup holder",
      one_liner: "Sleeve around a cup or glass with one or two large handles.",
      context: "Tremor or weak grip · Hold cup steadily while drinking",
      reqs: ["Large handles for secure grasp", "Tapered sleeve fits cups", "Bottom lip prevents slipping"],
    },
  },
  card_holder: {
    de: {
      name: "Spielkarten-Halter",
      one_liner: "Standfester Block mit geneigten Schlitzen zum Halten von Spielkarten ohne Festhalten.",
      context: "Einhändige Nutzung · Spielkarten frei aufstellen",
      reqs: ["Geneigte Schlitze für gute Lesbarkeit", "Standfeste Basis gegen Umkippen", "Abgerundete Kanten"],
    },
    en: {
      name: "Playing card holder",
      one_liner: "Weighted block with tilted slots that hold playing cards upright.",
      context: "One-handed use · Hold cards upright hands-free",
      reqs: ["Tilted slots for clear view", "Stable base", "Chamfered top edges"],
    },
  },
  plate_guard: {
    de: {
      name: "Tellerrand-Erhöhung",
      one_liner: "Aufsteckbare Randwand mit Innenlippe zum einhändigen Aufladen auf Löffel oder Gabel.",
      context: "Einhändiges Essen · Speisen gegen den Rand aufschieben",
      reqs: ["Clip klemmt sicher am Tellerrand", "Innenlippe lenkt Essen auf den Löffel", "Ohne Stützstrukturen druckbar"],
    },
    en: {
      name: "Plate guard",
      one_liner: "Clip-on raised wall with inward lip for one-handed scooping.",
      context: "One-handed eating · Scoop food against raised edge",
      reqs: ["Clip grips plate rim", "Inward lip guides food onto spoon", "Printable without supports"],
    },
  },
  button_hook: {
    de: {
      name: "Knöpfhilfe & Reißverschluss-Zieher",
      one_liner: "Dicker Griff mit Drahtschlaufe zum Knöpfen und optionalem Reißverschluss-Haken.",
      context: "Eingeschränkte Fingerfertigkeit · Hemden und Jacken schließen",
      reqs: ["Rutschfester dicker Griff", "Schlaufe passt durch Knopflöcher", "Optionaler Haken für Reißverschlüsse"],
    },
    en: {
      name: "Button hook and zipper pull",
      one_liner: "Thick handle with button loop and optional zipper pull hook.",
      context: "Limited dexterity · Button shirts and pull zippers",
      reqs: ["Non-rolling thick handle", "Loop passes through buttonholes", "Optional zipper hook"],
    },
  },
};

const PARAM_I18N = {
  // key_turner
  key_bow_width: { de: "Breite Schlüsselkopf", en: "Key head width", unit: "mm" },
  key_bow_length: { de: "Länge Schlüsselkopf", en: "Key head length", unit: "mm" },
  key_bow_thickness: { de: "Dicke Schlüsselkopf", en: "Key head thickness", unit: "mm" },
  lever_length: { de: "Hebellänge", en: "Lever length", unit: "mm" },
  lever_width: { de: "Hebelbreite", en: "Lever width", unit: "mm" },
  thickness: { de: "Griffdicke", en: "Handle thickness", unit: "mm" },
  finger_hole: { de: "Fingerloch", en: "Finger hole", unit: "" },
  finger_hole_d: { de: "Ø Fingerloch", en: "Finger hole dia.", unit: "mm" },
  bolt_hole: { de: "Schraubenloch (M3)", en: "M3 bolt hole", unit: "" },
  bolt_offset: { de: "Abstand Schraube", en: "Bolt offset", unit: "mm" },
  chamfer: { de: "Kantenfase", en: "Edge chamfer", unit: "mm" },
  tolerance: { de: "Spiel / Toleranz", en: "Clearance", unit: "mm" },
  // built_up_handle
  grip_length: { de: "Grifflänge", en: "Grip length", unit: "mm" },
  grip_diameter: { de: "Griffdurchmesser", en: "Grip diameter", unit: "mm" },
  bore_shape: { de: "Flachbohrung (statt rund)", en: "Flat bore (vs round)", unit: "" },
  bore_diameter: { de: "Ø Innenbohrung", en: "Round bore dia.", unit: "mm" },
  bore_width: { de: "Breite Innenöffnung", en: "Flat bore width", unit: "mm" },
  bore_thickness: { de: "Dicke Innenöffnung", en: "Flat bore thickness", unit: "mm" },
  bore_depth: { de: "Bohrtiefe", en: "Bore depth", unit: "mm" },
  finger_grooves: { de: "Anzahl Fingerrillen", en: "Finger grooves", unit: "" },
  groove_depth: { de: "Rillentiefe", en: "Groove depth", unit: "mm" },
  end_radius: { de: "Endradius", en: "End rounding", unit: "mm" },
  flat_side: { de: "Abgeflachte Seite", en: "Flat anti-roll side", unit: "" },
  // universal_cuff
  palm_width: { de: "Handflächenbreite", en: "Palm width", unit: "mm" },
  hand_thickness: { de: "Handdicke", en: "Hand thickness", unit: "mm" },
  band_width: { de: "Bandbreite", en: "Band width", unit: "mm" },
  wall: { de: "Wandstärke", en: "Wall thickness", unit: "mm" },
  opening: { de: "Daumenöffnung", en: "Thumb opening", unit: "mm" },
  holder_diameter: { de: "Ø Halteröffnung", en: "Pocket diameter", unit: "mm" },
  holder_length: { de: "Länge Haltertasche", en: "Pocket length", unit: "mm" },
  holder_wall: { de: "Wandstärke Tasche", en: "Pocket wall", unit: "mm" },
  holder_offset: { de: "Versatz Tasche", en: "Pocket offset", unit: "mm" },
  // lever_turner
  object_diameter: { de: "Ø Deckel / Knopf", en: "Object diameter", unit: "mm" },
  grip_depth: { de: "Aufstecktiefe", en: "Grip depth", unit: "mm" },
  top_thickness: { de: "Deckeldicke", en: "Top thickness", unit: "mm" },
  lever_height: { de: "Hebelhöhe", en: "Lever height", unit: "mm" },
  levers: { de: "Anzahl Hebel", en: "Number of levers", unit: "" },
  rib_count: { de: "Anzahl Innenrippen", en: "Grip ribs", unit: "" },
  rib_depth: { de: "Rippentiefe", en: "Rib depth", unit: "mm" },
  hang_hole: { de: "Aufhängeloch", en: "Hanging hole", unit: "" },
  // cup_holder
  cup_bottom_diameter: { de: "Ø Becher unten", en: "Cup bottom dia.", unit: "mm" },
  cup_top_diameter: { de: "Ø Becher oben", en: "Cup top dia.", unit: "mm" },
  cup_height: { de: "Becherhöhe", en: "Cup height", unit: "mm" },
  sleeve_height: { de: "Manschettenhöhe", en: "Sleeve height", unit: "mm" },
  base_lip: { de: "Bodenlippe", en: "Bottom lip", unit: "mm" },
  handles: { de: "Anzahl Henkel", en: "Handles", unit: "" },
  handle_opening_w: { de: "Öffnungsweite Henkel", en: "Finger opening", unit: "mm" },
  handle_bar: { de: "Stegbreite Henkel", en: "Handle bar", unit: "mm" },
  handle_thickness: { de: "Henkeldicke", en: "Handle thickness", unit: "mm" },
  // card_holder
  holder_length_card: { de: "Halterlänge", en: "Holder length", unit: "mm" },
  holder_length: { de: "Gesamtlänge", en: "Total length", unit: "mm" },
  holder_depth: { de: "Tiefe", en: "Depth", unit: "mm" },
  holder_height: { de: "Höhe", en: "Height", unit: "mm" },
  slots: { de: "Anzahl Schlitze", en: "Slot rows", unit: "" },
  slot_width: { de: "Schlitzbreite", en: "Slot width", unit: "mm" },
  slot_depth: { de: "Schlitztiefe", en: "Slot depth", unit: "mm" },
  slot_angle: { de: "Neigungswinkel", en: "Tilt angle", unit: "°" },
  end_margin: { de: "Endrand", en: "End margin", unit: "mm" },
  corner_radius: { de: "Eckenradius", en: "Corner radius", unit: "mm" },
  // plate_guard
  plate_diameter: { de: "Ø Teller", en: "Plate diameter", unit: "mm" },
  rim_thickness: { de: "Randdicke Teller", en: "Rim thickness", unit: "mm" },
  rim_slope: { de: "Randneigung", en: "Rim slope", unit: "°" },
  clip_depth: { de: "Clip-Tiefe", en: "Clip depth", unit: "mm" },
  grip_bump: { de: "Klemmwulst", en: "Grip bump", unit: "mm" },
  arc_angle: { de: "Bogenwinkel", en: "Arc angle", unit: "°" },
  wall_height: { de: "Wandhöhe", en: "Wall height", unit: "mm" },
  wall_thickness: { de: "Wandstärke", en: "Wall thickness", unit: "mm" },
  lip: { de: "Innenlippe", en: "Inward lip", unit: "mm" },
  // button_hook
  handle_length: { de: "Grifflänge", en: "Handle length", unit: "mm" },
  shaft_length: { de: "Schaftlänge", en: "Shaft length", unit: "mm" },
  loop_width: { de: "Schlaufenbreite", en: "Loop width", unit: "mm" },
  loop_length: { de: "Schlaufenlänge", en: "Loop length", unit: "mm" },
  loop_bar: { de: "Drahtbreite", en: "Loop wire width", unit: "mm" },
  hook_thickness: { de: "Hakendicke", en: "Hook thickness", unit: "mm" },
  zipper_hook: { de: "Reißverschluss-Haken", en: "Zipper hook", unit: "" },
  zipper_gap: { de: "Hakenöffnung", en: "Zipper gap", unit: "mm" },
};

const isBoolParam = (p) => Number(p.min) === 0 && Number(p.max) === 1 && Number(p.step) === 1;
const paramLabel = (name) => PARAM_I18N[name]?.[lang] || name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const paramUnit = (p) => {
  if (isBoolParam(p)) return "";
  if (PARAM_I18N[p.name]?.unit !== undefined) return PARAM_I18N[p.name].unit;
  const d = (p.description || "").toLowerCase();
  if (d.includes("(deg)")) return "°";
  if (d.includes("(mm)")) return "mm";
  return "";
};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

// ------------------------------------------------------------------ theme & i18n
let hemi = null, fill = null, grid = null, shadowPlane = null, animNodes = [];
function applyTheme(mode) {
  document.documentElement.dataset.theme = mode;
  try { localStorage.setItem("aidforge-theme", mode); } catch {}
  if (grid) {
    grid.material.opacity = mode === "dark" ? 0.14 : 0.35;
    grid.material.needsUpdate = true;
  }
  if (shadowPlane) shadowPlane.material.opacity = mode === "dark" ? 0.25 : 0.14;
  if (hemi) hemi.intensity = mode === "dark" ? 1.65 : 1.55;
  if (fill) fill.intensity = mode === "dark" ? 0.9 : 0.75;
  brightenAnimContext();
}
applyTheme((() => { try { return localStorage.getItem("aidforge-theme") === "dark" ? "dark" : "light"; } catch { return "light"; } })());
$("btn-theme").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

function applyI18n() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll(".lang button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  renderPresets();
  if (typeof renderTemplatesList === "function") renderTemplatesList();
  if (currentJob) renderJob(currentJob, { force: true });
}
document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => {
  lang = b.dataset.lang;
  try { localStorage.setItem("lang", lang); } catch {}
  applyI18n();
}));

function renderPresets() {
  const box = $("presets");
  box.innerHTML = "";
  t("presets").forEach((p) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "preset-chip"; b.textContent = p.label;
    b.addEventListener("click", () => {
      $("impairment").value = p.imp;
      $("activity").value = p.act;
      $("activity").focus();
    });
    box.appendChild(b);
  });
  renderCases(box);
}

// Prepared demo cases (demo_inputs/cases): one click runs the full pipeline WITH their photos / videos,
// so measurement from the reference object and the video assessment are part of the demo.
let demoCases = null;
async function renderCases(box) {
  try { demoCases = demoCases || await api("/api/cases"); } catch { return; }
  if (!demoCases.length) return;
  box.innerHTML = "";
  demoCases.forEach((c) => {
    const b = document.createElement("button");
    const nVid = c.media.filter((m) => /\.(mp4|mov|webm)$/i.test(m)).length, nImg = c.media.length - nVid;
    b.type = "button"; b.className = "preset-chip";
    b.textContent = `▶ ${c.title?.[lang] || c.title?.de || c.id}`;
    b.title = `${nImg ? `${nImg} 📷 ` : ""}${nVid ? `${nVid} 🎬 ` : ""}· ${c.impairment}`;
    b.addEventListener("click", async () => {
      $("impairment").value = c.impairment || "";
      $("activity").value = c.activity || "";
      showError("");
      $("go").disabled = true; $("go").querySelector("span").textContent = t("working");
      try {
        const { job_id } = await api(`/api/cases/${c.id}/run`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language: lang, review: true }),
        });
        openJob(job_id);
      } catch (err) {
        $("go").disabled = false; $("go").querySelector("span").textContent = t("go");
        showError(err.message);
      }
    });
    box.appendChild(b);
  });
}

// ------------------------------------------------------------------ media & mic
let mediaFiles = [];
const drop = $("drop");
$("files").addEventListener("change", (e) => addFiles(e.target.files));
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));

function addFiles(list) {
  for (const f of list) {
    if (!/^(image|video)\//.test(f.type) || mediaFiles.length >= 4) continue;
    mediaFiles.push(f);
  }
  $("files").value = "";
  renderThumbs();
}
function renderThumbs() {
  const box = $("thumbs");
  box.hidden = !mediaFiles.length;
  box.innerHTML = "";
  mediaFiles.forEach((f, i) => {
    const d = document.createElement("div"); d.className = "thumb";
    const url = URL.createObjectURL(f);
    d.innerHTML = f.type.startsWith("video/") ? `<video src="${url}" muted></video>` : `<img src="${url}" alt="">`;
    const rm = document.createElement("button"); rm.type = "button"; rm.textContent = "×";
    rm.addEventListener("click", () => { mediaFiles.splice(i, 1); renderThumbs(); });
    d.appendChild(rm); box.appendChild(d);
  });
}

let recorder = null;
document.querySelectorAll(".mic").forEach((btn) => btn.addEventListener("click", async () => {
  if (recorder && recorder.btn === btn) { recorder.stop(); return; }
  if (recorder) recorder.stop();
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { showError(e.message); return; }
  const chunks = [];
  const rec = new MediaRecorder(stream); rec.btn = btn;
  rec.addEventListener("dataavailable", (e) => e.data.size && chunks.push(e.data));
  rec.addEventListener("stop", async () => {
    stream.getTracks().forEach((tr) => tr.stop()); recorder = null;
    btn.setAttribute("aria-pressed", "false");
    const blob = new Blob(chunks, { type: (rec.mimeType || "audio/webm").split(";")[0] });
    if (!blob.size) return;
    try {
      const fd = new FormData();
      fd.append("audio", blob, "speech.webm"); fd.append("language", lang);
      const { text } = await api("/api/transcribe", { method: "POST", body: fd });
      const inp = $(btn.dataset.target);
      inp.value = (inp.value.trim() ? inp.value.trim() + " " : "") + text;
    } catch (e) { showError(e.message); }
  });
  rec.start(); recorder = rec; btn.setAttribute("aria-pressed", "true");
}));

// ------------------------------------------------------------------ 3D viewer
const viewerEl = $("viewer");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
viewerEl.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.5, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.autoRotateSpeed = 1.6;

hemi = new THREE.HemisphereLight(0xffffff, 0x8a9590, document.documentElement.dataset.theme === "dark" ? 1.95 : 1.55);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 2.3);
sun.position.set(150, 260, 180);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.bias = -0.0005;
scene.add(sun);
fill = new THREE.DirectionalLight(0xdbeafe, document.documentElement.dataset.theme === "dark" ? 1.15 : 0.75);
fill.position.set(-200, 80, -150);
scene.add(fill);

grid = new THREE.GridHelper(220, 22, 0x7a8a85, 0xc4ccc9);
grid.material.transparent = true;
grid.material.opacity = document.documentElement.dataset.theme === "dark" ? 0.14 : 0.35;
scene.add(grid);
shadowPlane = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.ShadowMaterial({ opacity: document.documentElement.dataset.theme === "dark" ? 0.25 : 0.14 }));
shadowPlane.rotation.x = -Math.PI / 2; shadowPlane.position.y = -0.1; shadowPlane.receiveShadow = true;
scene.add(shadowPlane);

const material = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.48, metalness: 0.06 });
let mesh = null, meshOffset = new THREE.Vector3(), fitState = null, anim = null, animStart = 0;
const clock = new THREE.Clock();

let lastViewSize = { w: 0, h: 0 };
function resize() {
  const w = viewerEl.clientWidth, h = viewerEl.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
  if (w !== lastViewSize.w || h !== lastViewSize.h) {
    lastViewSize = { w, h };
    if (fitState) fitCamera(anim ? 2.1 : 1);
  }
}
new ResizeObserver(resize).observe(viewerEl);

(function loop() {
  if (anim) {
    const el = clock.getElapsedTime() - animStart;
    try { anim.update(el % anim.duration); } catch { stopAnim(); }
  }
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();

function fitCamera(scaleUp = 1) {
  if (!fitState) return;
  const w = viewerEl.clientWidth || 1, h = viewerEl.clientHeight || 1;
  const tweakOpen = !$("sheet-tweak").hidden;
  const isMobile = w <= 760;

  const infoH = $("stage-info").hidden ? 0 : $("stage-info").getBoundingClientRect().height + 16;
  const dockH = $("dock-stack").hidden ? 0 : $("dock-stack").getBoundingClientRect().height + 20;
  const rightInset = (!isMobile && tweakOpen) ? 360 : 0;
  const bottomInset = (isMobile && tweakOpen) ? Math.max(dockH, h * 0.5 + 16) : dockH;
  const topInset = infoH;

  const availW = Math.max(160, w - rightInset - 24);
  const availH = Math.max(160, h - topInset - bottomInset - 16);

  const { size, center } = fitState;
  const radius = size.length() * 0.5 * scaleUp;
  const fovV = (camera.fov * Math.PI) / 180;
  const aspect = w / h;
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * aspect);
  const effFovV = fovV * (availH / h);
  const effFovH = fovH * (availW / w);
  const minHalfFov = Math.max(0.12, Math.min(effFovV, effFovH) * 0.5);
  const dist = (radius / Math.sin(minHalfFov)) * 1.15;

  camera.position.set(center.x + dist * 0.72, center.y + dist * 0.58, center.z + dist * 0.85);
  controls.target.copy(center);

  // Shift view offset so model centers inside unobstructed area
  const shiftX = (!isMobile && tweakOpen) ? rightInset * 0.5 : 0;
  const shiftY = (bottomInset - topInset) * 0.45;
  if (Math.abs(shiftX) > 1 || Math.abs(shiftY) > 1) {
    camera.setViewOffset(w, h, shiftX, shiftY, w, h);
  } else {
    camera.clearViewOffset();
  }
  camera.near = Math.max(0.1, dist / 100);
  camera.far = dist * 20;
  camera.updateProjectionMatrix();
  controls.update();
}

function brightenAnimContext() {
  if (!animNodes.length) return;
  const isDark = document.documentElement.dataset.theme === "dark";
  animNodes.forEach((root) => {
    root.traverse((obj) => {
      if (!obj.isMesh || !obj.material) return;
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      mats.forEach((m) => {
        if (!m.color) return;
        if (!m.userData._origColor) m.userData._origColor = m.color.clone();
        if (isDark) {
          const hsl = {};
          m.userData._origColor.getHSL(hsl);
          m.color.setHSL(hsl.h, hsl.s, Math.min(0.88, Math.max(0.45, hsl.l + 0.28)));
        } else {
          m.color.copy(m.userData._origColor);
        }
        m.needsUpdate = true;
      });
    });
  });
}

const loader = new STLLoader();
function loadStl(url) {
  stopAnim();
  return new Promise((resolve, reject) => loader.load(url, (geo) => {
    geo.rotateX(-Math.PI / 2);
    geo.computeBoundingBox();
    const bb = geo.boundingBox, c = new THREE.Vector3(); bb.getCenter(c);
    meshOffset = new THREE.Vector3(-c.x, -bb.min.y, -c.z);
    geo.translate(meshOffset.x, meshOffset.y, meshOffset.z);
    geo.computeVertexNormals();
    geo.computeBoundingBox();
    if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); }
    mesh = new THREE.Mesh(geo, material);
    mesh.castShadow = true; mesh.receiveShadow = true;
    scene.add(mesh);
    const size = new THREE.Vector3(); geo.boundingBox.getSize(size);
    const center = new THREE.Vector3(); geo.boundingBox.getCenter(center);
    const first = !fitState;
    fitState = { size, center };
    if (first) fitCamera();
    resolve();
  }, undefined, reject));
}

document.querySelectorAll("#filament-colors .swatch").forEach((sw) => sw.addEventListener("click", () => {
  material.color.set(sw.dataset.color);
  document.querySelectorAll("#filament-colors .swatch").forEach((b) => b.classList.toggle("active", b === sw));
}));
$("btn-rotate").addEventListener("click", (e) => {
  controls.autoRotate = !controls.autoRotate;
  e.currentTarget.setAttribute("aria-pressed", String(controls.autoRotate));
});

// usage animation
function paramsObject(job) { return Object.fromEntries((job.params || []).map((p) => [p.name, p.value])); }
function canAnimate(job) { return !!(usageAnim && job && job.approach === "template" && usageAnim.hasUsageAnimation(job.template_id)); }
function updateAnimBtn(job) {
  const b = $("btn-anim");
  b.hidden = !canAnimate(job) || viewingVersion !== job.version;
  b.setAttribute("aria-pressed", String(!!anim));
  b.querySelector("span").textContent = anim ? t("stopAnim") : t("playAnim");
}
function stopAnim() {
  if (!anim) return;
  try { anim.dispose(); } catch {}
  anim = null;
  animNodes = [];
  if (currentJob) updateAnimBtn(currentJob);
}
$("btn-anim").addEventListener("click", () => {
  if (anim) { stopAnim(); fitCamera(); return; }
  if (!canAnimate(currentJob) || !mesh) return;
  controls.autoRotate = false;
  $("btn-rotate").setAttribute("aria-pressed", "false");
  const before = new Set(scene.children);
  anim = usageAnim.createUsageAnimation({ THREE, scene, deviceMesh: mesh, templateId: currentJob.template_id, params: paramsObject(currentJob), offset: meshOffset.clone() });
  animNodes = scene.children.filter((c) => !before.has(c));
  brightenAnimContext();
  animStart = clock.getElapsedTime();
  fitCamera(2.1);
  updateAnimBtn(currentJob);
});

// ------------------------------------------------------------------ navigation & popovers/modals
let currentJob = null, loadedUrl = "", viewingVersion = 0, pollTimer = null, renderedKey = "";

function clearMesh() {
  stopAnim();
  if (mesh) {
    scene.remove(mesh);
    mesh.geometry.dispose();
    mesh = null;
  }
  fitState = null;
}

function showStart() {
  clearTimeout(pollTimer);
  clearMesh();
  updateHudTimer(false);
  currentJob = null;
  $("start-screen").hidden = false;
  $("stage").hidden = true;
  $("btn-new").hidden = true;
  closeAllPopovers();
  closeModals();
  try { history.replaceState(null, "", location.pathname); } catch {}
}

function showStage() {
  $("start-screen").hidden = true;
  $("stage").hidden = false;
  $("btn-new").hidden = false;
  setTimeout(resize, 20);
}

$("btn-home").addEventListener("click", showStart);
$("btn-new").addEventListener("click", showStart);

function closeAllPopovers() {
  ["sheet-tweak", "sheet-preview"].forEach((id) => { $(id).hidden = true; });
  $("btn-tweak").setAttribute("aria-expanded", "false");
  $("btn-preview").setAttribute("aria-expanded", "false");
  if (fitState) fitCamera(anim ? 2.1 : 1);
}
function togglePopover(btnId, sheetId) {
  const wasOpen = !$(sheetId).hidden;
  closeAllPopovers();
  if (!wasOpen) {
    $(sheetId).hidden = false;
    $(btnId).setAttribute("aria-expanded", "true");
    if (fitState) fitCamera(anim ? 2.1 : 1);
  }
}
$("btn-tweak").addEventListener("click", () => togglePopover("btn-tweak", "sheet-tweak"));
$("btn-preview").addEventListener("click", () => togglePopover("btn-preview", "sheet-preview"));
$("btn-refine-toggle").addEventListener("click", () => {
  const open = $("refine").classList.toggle("open");
  $("btn-refine-toggle").setAttribute("aria-expanded", String(open));
  if (open) $("feedback").focus();
  if (fitState) fitCamera(anim ? 2.1 : 1);
});
document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeAllPopovers));

function openModal(id, focusElId = null) {
  $("modal-backdrop").hidden = false;
  ["modal-templates", "modal-recent", "modal-details"].forEach((m) => { $(m).hidden = m !== id; });
  if (focusElId) {
    requestAnimationFrame(() => { $(focusElId)?.scrollIntoView({ behavior: "smooth", block: "start" }); });
  }
}
function closeModals() {
  $("modal-backdrop").hidden = true;
  ["modal-templates", "modal-recent", "modal-details"].forEach((m) => { $(m).hidden = true; });
}
document.querySelectorAll("[data-close-modal]").forEach((b) => b.addEventListener("click", closeModals));
$("modal-backdrop").addEventListener("click", (e) => { if (e.target === $("modal-backdrop")) closeModals(); });
$("btn-open-templates").addEventListener("click", () => openModal("modal-templates"));
$("btn-open-recent").addEventListener("click", () => openModal("modal-recent"));
$("btn-details").addEventListener("click", () => openModal("modal-details"));
$("check-badge").addEventListener("click", () => openModal("modal-details", "section-checks"));

// Lightbox
let lbItems = [], lbIdx = 0;
function openLightbox(idx) {
  if (!lbItems.length) return;
  lbIdx = (idx + lbItems.length) % lbItems.length;
  const it = lbItems[lbIdx];
  $("lb-img").src = it.url;
  $("lb-cap").textContent = `${t("visStep")} ${it.step}${it.caption ? " — " + it.caption : ""}`;
  $("lightbox").hidden = false;
}
$("lb-close").addEventListener("click", () => { $("lightbox").hidden = true; });
$("lb-prev").addEventListener("click", () => openLightbox(lbIdx - 1));
$("lb-next").addEventListener("click", () => openLightbox(lbIdx + 1));
$("lightbox").addEventListener("click", (e) => { if (e.target === $("lightbox")) $("lightbox").hidden = true; });

document.addEventListener("keydown", (e) => {
  if (!$("lightbox").hidden) {
    if (e.key === "Escape") $("lightbox").hidden = true;
    else if (e.key === "ArrowLeft") openLightbox(lbIdx - 1);
    else if (e.key === "ArrowRight") openLightbox(lbIdx + 1);
    return;
  }
  if (e.key === "Escape") {
    if (!$("modal-backdrop").hidden) closeModals();
    else closeAllPopovers();
  }
});

// ------------------------------------------------------------------ rendering
let hudStartMs = 0, hudTimerId = null, hudLogEntries = [], hudSeenKey = "";
function updateHudTimer(running) {
  if (!running) {
    if (hudTimerId) { clearInterval(hudTimerId); hudTimerId = null; }
    hudStartMs = 0;
    return;
  }
  if (!hudStartMs) hudStartMs = performance.now();
  const tick = () => {
    const el = $("hud-timer");
    if (el && hudStartMs) el.textContent = `${((performance.now() - hudStartMs) / 1000).toFixed(1)} s`;
  };
  tick();
  if (!hudTimerId) hudTimerId = setInterval(tick, 100);
}

function renderBuildHud(job, running) {
  $("progress-pill").hidden = !running;
  updateHudTimer(running);
  if (!running) return;

  if (!hudSeenKey.startsWith(job.id + ":")) {
    hudLogEntries = [];
    hudSeenKey = `${job.id}:`;
  }
  const stepMap = Object.fromEntries((job.steps || []).map((s) => [s.key, s]));
  const activeStep = (job.steps || []).find((s) => s.status === "running");
  $("progress-text").textContent = activeStep ? (t("steps")[activeStep.key] || activeStep.key) : t("working");

  const ctx = [job.inputs?.impairment, job.inputs?.activity].filter(Boolean).join(" · ");
  $("hud-context").textContent = ctx;
  $("hud-context").hidden = !ctx;

  // Record real backend step events into live telemetry log
  (job.steps || []).forEach((s) => {
    if (s.status === "pending") return;
    const msg = s.detail ? `${s.key} · ${s.detail}` : `${s.key} · ${s.status}`;
    const sig = `${s.key}:${s.status}:${s.detail || ""}`;
    if (!hudLogEntries.some((e) => e.sig === sig)) {
      const sec = hudStartMs ? ((performance.now() - hudStartMs) / 1000).toFixed(1).padStart(4, " ") : " 0.0";
      hudLogEntries.push({ sig, sec, key: s.key, detail: s.detail || s.status });
    }
  });

  $("progress-steps").innerHTML = t("stepPipe").map((sp) => {
    const stObj = stepMap[sp.key] || (sp.key === "improve" ? stepMap.review : null);
    const st = stObj?.status || "pending";
    const cls = st === "done" ? "done" : st === "running" ? "active" : st === "error" ? "error" : "pending";
    const badge = st === "done" ? "✓" : st === "error" ? "✕" : sp.num;
    const liveDetail = stObj?.detail || sp.desc;
    return `<li class="hud-stage ${cls}">
      <div class="hud-stage-top">
        <span class="hud-stage-name">${esc(sp.label)}</span>
        <span class="hud-stage-num">${badge}</span>
      </div>
      <div class="hud-stage-tech">${esc(sp.tech)}</div>
      <div class="hud-stage-detail">${esc(liveDetail)}</div>
    </li>`;
  }).join("");

  const logEl = $("hud-log");
  logEl.innerHTML = hudLogEntries.slice(-6).map((e) =>
    `<div class="hud-log-line">[${e.sec}s] <b>${esc(e.key)}</b> → ${esc(e.detail)}</div>`
  ).join("");
  logEl.scrollTop = logEl.scrollHeight;
}

function renderJob(job, { force = false } = {}) {
  const same = currentJob && currentJob.id === job.id;
  currentJob = job;
  showStage();

  const running = job.status === "running" || job.status === "queued";
  renderBuildHud(job, running);

  if (running) {
    closeAllPopovers();
    $("stage-info").hidden = true;
    $("loop-bar").hidden = true;
    $("dock-stack").hidden = true;
    return;
  }

  renderVisual(job);
  if (!job.stl_url) return;

  const key = `${job.id}:${job.version}:${job.status}:${(job.iterations || []).length}:${lang}`;
  if (key === renderedKey && !force) return;
  const newVer = !same || !renderedKey.startsWith(`${job.id}:${job.version}:`);
  renderedKey = key;

  if (newVer) {
    viewingVersion = job.version;
    loadStl(`${job.stl_url}?v=${job.version}`).then(() => fitCamera(anim ? 2.1 : 1)).catch(console.error);
  }

  $("stage-info").hidden = false;
  $("dock-stack").hidden = false;
  $("dl-stl").href = job.stl_url;

  const tplLoc = job.template_id ? TPL_I18N[job.template_id]?.[lang] : null;
  const useLoc = tplLoc && (job.language !== lang || !job.plan);
  const devName = useLoc ? tplLoc.name : (job.plan?.device_name || tplLoc?.name || job.template_name || "");
  const oneLiner = useLoc ? tplLoc.one_liner : (job.plan?.brief?.one_liner || job.plan?.how_it_helps || tplLoc?.one_liner || "");

  $("dl-stl").setAttribute("download", `${(devName || job.template_id || "aid").replace(/[^\w-]+/g, "_")}.stl`);
  $("dl-scad").href = job.scad_url;

  const tplTitle = tplLoc?.name || job.template_name || job.template_id;
  $("approach").textContent = job.approach === "template" ? `${t("approachTemplate")} · ${tplTitle}` : t("approachCustom");

  const rawCtx = [job.inputs?.impairment, job.inputs?.activity].filter(Boolean).join(" · ");
  const ctxText = (job.language !== lang && tplLoc?.context) ? tplLoc.context : rawCtx;
  $("job-context").textContent = ctxText;
  $("job-context").hidden = !ctxText;
  $("job-context").title = ctxText;

  $("device-name").textContent = devName;
  $("one-liner").textContent = oneLiner;
  const s = job.stats || {};
  $("dims").textContent = s.size_mm ? `${s.size_mm.map(fmt).join("×")} mm · ≈${s.weight_estimate_g} g` : "";

  const c = job.checks?.counts;
  const cb = $("check-badge");
  if (c) {
    const n = (c.pass || 0) + (c.warn || 0) + (c.fail || 0);
    cb.hidden = false;
    cb.className = `pill-badge check-btn ${c.fail ? "fail" : c.warn ? "warn" : "ok"}`;
    cb.textContent = (c.fail ? "✕ " : c.warn ? "! " : "✓ ") + tf("checksBadge", { p: c.pass || 0, n });
  } else cb.hidden = true;

  // Versions (Agentic Loop — always visible when >= 1 version exists)
  const its = (job.iterations || []).filter((it) => it.version != null);
  const lb = $("loop-bar");
  const vp = $("version-pills");
  lb.hidden = !its.length;
  vp.innerHTML = its.map((it) => {
    const srcLbl = t("verSource")[it.source] || it.source || "";
    const ic = it.checks?.counts || it.checks || (it.version === job.version ? job.checks?.counts : null);
    const stCls = ic ? (ic.fail ? "fail" : ic.warn ? "warn" : "ok") : "";
    const stGlyph = ic ? (ic.fail ? "✕" : ic.warn ? "!" : "✓") : "";
    return `<button type="button" class="v-btn ${it.version === viewingVersion ? "active" : ""}" data-v="${it.version}">
      <span>v${it.version}${srcLbl ? " " + esc(srcLbl) : ""}</span>${stGlyph ? `<span class="v-status ${stCls}">${stGlyph}</span>` : ""}
    </button>`;
  }).join("");
  vp.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    const it = its.find((x) => x.version === +b.dataset.v);
    if (!it) return;
    viewingVersion = it.version;
    loadStl(`${it.stl_url}?v=${it.version}`).then(() => fitCamera(anim ? 2.1 : 1)).catch(console.error);
    renderJob(job, { force: true });
  }));

  renderParams(job);
  renderDetails(job);
  updateAnimBtn(job);
  $("rebuild").disabled = running;
  requestAnimationFrame(() => { if (fitState) fitCamera(anim ? 2.1 : 1); });
}

function renderParams(job) {
  const box = $("params");
  if (!job.params?.length) { box.innerHTML = `<p class="muted small-txt">${t("noParams")}</p>`; return; }
  box.innerHTML = job.params.map((p, i) => {
    const lbl = paramLabel(p.name);
    if (isBoolParam(p)) {
      return `
        <div class="param param-bool" title="${esc(p.description)}">
          <label for="pb-${i}">${esc(lbl)}</label>
          <div class="param-val">
            <label class="switch">
              <input type="checkbox" id="pb-${i}" data-name="${esc(p.name)}" ${p.value >= 0.5 ? "checked" : ""}>
              <span class="switch-track" aria-hidden="true"></span>
            </label>
          </div>
        </div>`;
    }
    const unit = paramUnit(p);
    return `
      <div class="param" title="${esc(p.description)}">
        <label for="pn-${i}">${esc(lbl)}</label>
        <div class="param-val">
          <input type="number" id="pn-${i}" min="${p.min}" max="${p.max}" step="${p.step}" value="${fmt(p.value)}" data-name="${esc(p.name)}">
          <span class="unit">${esc(unit)}</span>
        </div>
        <input type="range" id="pr-${i}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}" aria-label="${esc(lbl)}">
      </div>`;
  }).join("");
  job.params.forEach((p, i) => {
    if (isBoolParam(p)) return;
    const r = $(`pr-${i}`), n = $(`pn-${i}`);
    r.addEventListener("input", () => { n.value = r.value; });
    n.addEventListener("input", () => { r.value = n.value; });
  });
}

function renderDetails(job) {
  const p = job.plan, b = p?.brief || {}, ps = p?.print_settings;
  const tplLoc = job.template_id ? TPL_I18N[job.template_id]?.[lang] : null;
  const useLoc = tplLoc && (job.language !== lang || !p);

  const reqs = useLoc ? tplLoc.reqs : (b.requirement_bullets?.length ? b.requirement_bullets : (p?.design_requirements || []).slice(0, 4));
  let printLine = b.print_line || (ps ? `${ps.material} · ${ps.layer_height_mm} mm · ${ps.infill_percent} %` : "");
  if (lang === "de" && printLine) {
    printLine = printLine.replace(/\binfill\b/gi, "Füllung").replace(/\bno supports\b/gi, "ohne Stützen").replace(/\bwith supports\b/gi, "mit Stützen");
  }
  const meas = (!useLoc && p?.measurements?.length)
    ? `${p.scale_reference?.detected ? `<p class="muted small-txt">📏 ${esc(p.scale_reference.object)}${p.scale_reference.known_size_mm ? ` (${fmt(p.scale_reference.known_size_mm)} mm)` : ""}</p>` : ""}
       <table class="kv">${p.measurements.map((m) => `<tr title="${esc(m.method || m.source || "")}"><th>${esc(m.name)}</th><td>${fmt(m.value_mm)}${m.uncertainty_mm > 0 ? ` ± ${fmt(m.uncertainty_mm)}` : ""} mm</td></tr>`).join("")}</table>` : "";

  // AI analysis: what was observed (with timestamps), why each parameter, and the review critique per version
  const de = lang === "de";
  const ev = (!useLoc && p?.functional_assessment?.evidence) || [];
  const evHtml = ev.length ? `<div><h4>${de ? "Beobachtungen der KI" : "What the AI observed"}</h4><ul>${ev.map((e) =>
    `<li><b>${esc(e.ref || e.source)}</b>: ${esc(e.observation)} → ${esc(e.design_consequence)}</li>`).join("")}</ul></div>` : "";
  const rat = (!useLoc && p?.parameter_rationale) || [];
  const ratHtml = rat.length ? `<div><h4>${de ? "Warum diese Werte" : "Why these values"}</h4><ul>${rat.map((r) =>
    `<li><b>${esc(paramLabel(r.name))} ${fmt(r.value)}</b>: ${esc(r.reason)}</li>`).join("")}</ul></div>` : "";
  const crit = (job.iterations || []).filter((it) => it.version != null && (it.critique || it.note));
  const critHtml = crit.length ? `<div><h4>${de ? "QA-Loop: Kritik je Version" : "QA loop: critique per version"}</h4><ul>${crit.map((it) =>
    `<li><b>v${it.version}</b>: ${esc(it.critique || it.note)}${Object.keys(it.changed || {}).length
      ? ` <span class="muted">(${Object.entries(it.changed).map(([k, v]) => `${esc(paramLabel(k))} ${fmt(v[0])} → ${fmt(v[1])}`).join(", ")})</span>` : ""}</li>`).join("")}</ul></div>` : "";
  const story = (!useLoc && p?.persona_story) ? `<p><em>${esc(p.persona_story)}</em></p>` : "";

  const checksList = job.checks?.checks || [];
  const checksHtml = checksList.length ? `
    <div id="section-checks">
      <h4>${t("checksTitle")}</h4>
      <div class="checks-list">
        ${checksList.map((ck) => {
          const st = ck.status === "fail" ? "fail" : ck.status === "warn" ? "warn" : "pass";
          const glyph = st === "fail" ? "✕" : st === "warn" ? "!" : "✓";
          const label = lang === "de" ? (ck.label_de || ck.label_en || ck.id) : (ck.label_en || ck.label_de || ck.id);
          const detail = lang === "de" ? (ck.detail_de || ck.detail_en || "") : (ck.detail_en || ck.detail_de || "");
          return `<div class="check-row">
            <span class="check-icon ${st}" aria-hidden="true">${glyph}</span>
            <div>
              <div class="check-title">${esc(label)}</div>
              ${detail ? `<div class="check-detail">${esc(detail)}</div>` : ""}
            </div>
            ${ck.value != null ? `<span class="check-val">${esc(ck.value)}</span>` : ""}
          </div>`;
        }).join("")}
      </div>
    </div>` : "";

  $("details-body").innerHTML = `
    ${story}
    ${checksHtml}
    ${critHtml}
    ${evHtml}
    ${ratHtml}
    ${reqs.length ? `<div><h4>${t("whyDesign")}</h4><ul>${reqs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
    ${meas ? `<div><h4>${t("measTitle")}</h4>${meas}</div>` : ""}
    ${printLine ? `<div><h4>${t("printTitle")}</h4><p>${esc(printLine)}</p></div>` : ""}
    <div><h4>${t("codeTitle")}</h4><pre><code id="code">${esc(job.code || "")}</code></pre></div>`;
}

function renderVisual(job) {
  const v = job.visual || { status: "idle" };
  const running = v.status === "running";
  $("vis-frames").disabled = running || !job.stl_url;
  $("vis-video").disabled = running || !job.stl_url;
  const canStory = !!(storyboardMod && job.approach === "template" && storyboardMod.hasStoryboard(job.template_id));
  $("vis-story").hidden = !canStory;
  $("vis-story").disabled = running || !job.stl_url;
  $("vis-status").textContent = running ? (t("visStages")[v.stage] || v.stage || "") : (v.status === "error" ? (v.error || "") : "");

  lbItems = v.storyboard || [];
  const so = $("vis-story-out");
  so.innerHTML = lbItems.map((s, idx) => `<button type="button" class="story-card" data-idx="${idx}"><img src="${s.url}" alt=""><span><b>${t("visStep")} ${s.step}</b></span></button>`).join("");
  so.querySelectorAll(".story-card").forEach((c) => c.addEventListener("click", () => openLightbox(+c.dataset.idx)));

  const frames = [];
  if (v.start_url) frames.push(`<figure><img src="${v.start_url}" alt=""><figcaption>${t("visStart")}</figcaption></figure>`);
  if (v.end_url) frames.push(`<figure><img src="${v.end_url}" alt=""><figcaption>${t("visEnd")}</figcaption></figure>`);
  $("vis-frames-out").innerHTML = frames.join("");

  const player = $("vis-player");
  if (v.video_url) {
    if (player.dataset.src !== v.video_url) { player.src = v.video_url; player.dataset.src = v.video_url; player.play().catch(() => {}); }
    player.hidden = false;
  } else { player.hidden = true; player.removeAttribute("src"); player.dataset.src = ""; }
}

// ------------------------------------------------------------------ actions & polling
function showError(msg) {
  const el = $("form-error");
  el.hidden = !msg; el.textContent = msg || "";
}

async function poll(jobId) {
  clearTimeout(pollTimer);
  try {
    const job = await api(`/api/jobs/${jobId}`);
    renderJob(job);
    const busy = job.status === "running" || job.status === "queued" || job.visual?.status === "running";
    if (busy) pollTimer = setTimeout(() => poll(jobId), 1200);
    else { $("go").disabled = false; $("go").querySelector("span").textContent = t("go"); loadRecent(); }
  } catch {
    pollTimer = setTimeout(() => poll(jobId), 2000);
  }
}

function openJob(jobId) {
  closeModals(); closeAllPopovers();
  clearMesh();
  loadedUrl = ""; renderedKey = "";
  $("stage-info").hidden = true;
  $("loop-bar").hidden = true;
  $("dock-stack").hidden = true;
  try { history.replaceState(null, "", `?job=${jobId}`); } catch {}
  poll(jobId);
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const imp = $("impairment").value.trim(), act = $("activity").value.trim();
  if (!imp || !act) { showError(t("missingInput")); return; }
  showError("");
  $("go").disabled = true; $("go").querySelector("span").textContent = t("working");
  const fd = new FormData();
  fd.append("impairment", imp); fd.append("activity", act); fd.append("notes", "");
  fd.append("language", lang); fd.append("review", "true");
  mediaFiles.forEach((f) => fd.append("files", f, f.name));
  try {
    const { job_id } = await api("/api/jobs", { method: "POST", body: fd });
    openJob(job_id);
  } catch (err) {
    $("go").disabled = false; $("go").querySelector("span").textContent = t("go");
    showError(err.message);
  }
});

$("rebuild").addEventListener("click", async () => {
  if (!currentJob) return;
  const params = {};
  document.querySelectorAll("#params input[type=number]").forEach((n) => { params[n.dataset.name] = parseFloat(n.value); });
  document.querySelectorAll("#params input[type=checkbox]").forEach((cb) => { params[cb.dataset.name] = cb.checked ? 1 : 0; });
  $("rebuild").disabled = true; $("rebuild-status").textContent = t("rebuilding");
  try {
    const job = await api(`/api/jobs/${currentJob.id}/rebuild`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ params }),
    });
    renderJob(job);
    $("rebuild-status").textContent = `${t("rebuilt")}${job.version}`;
  } catch (err) {
    $("rebuild-status").textContent = err.message;
  } finally { $("rebuild").disabled = false; }
});

$("refine").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fb = $("feedback").value.trim();
  if (!fb || !currentJob) return;
  $("feedback").value = "";
  closeAllPopovers();
  await api(`/api/jobs/${currentJob.id}/refine`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feedback: fb }),
  }).catch(console.error);
  poll(currentJob.id);
});

$("vis-story").addEventListener("click", async () => {
  if (!currentJob || !storyboardMod) return;
  $("vis-story").disabled = true; $("vis-status").textContent = t("visStages").render;
  try {
    await storyboardMod.requestStoryboard(currentJob.id, { stlUrl: currentJob.stl_url, templateId: currentJob.template_id, params: paramsObject(currentJob) });
    poll(currentJob.id);
  } catch (e) { $("vis-story").disabled = false; $("vis-status").textContent = e.message; }
});
$("vis-frames").addEventListener("click", async () => {
  if (!currentJob) return;
  await api(`/api/jobs/${currentJob.id}/visualize`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ with_video: false }) });
  poll(currentJob.id);
});
$("vis-video").addEventListener("click", async () => {
  if (!currentJob) return;
  await api(`/api/jobs/${currentJob.id}/visualize`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ with_video: true }) });
  poll(currentJob.id);
});

$("copy-code").addEventListener("click", async (e) => {
  try { await navigator.clipboard.writeText($("code")?.textContent || ""); e.currentTarget.textContent = t("copied"); } catch {}
  setTimeout(() => { $("copy-code").textContent = t("copy"); }, 1500);
});

async function loadRecent() {
  try {
    const jobs = await api("/api/jobs");
    $("btn-open-recent").hidden = !jobs.length;
    const box = $("recent-list"); box.innerHTML = "";
    jobs.forEach((j) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "modal-item";
      b.innerHTML = `<strong>${esc(j.device_name || j.id)}</strong><small>${esc(j.activity || "")} · v${j.version}</small>`;
      b.addEventListener("click", () => openJob(j.id));
      box.appendChild(b);
    });
  } catch {}
}

let cachedTemplates = [];
function renderTemplatesList() {
  const box = $("lib-list");
  if (!box) return;
  box.innerHTML = "";
  cachedTemplates.forEach((tpl) => {
    const loc = TPL_I18N[tpl.id]?.[lang];
    const b = document.createElement("button"); b.type = "button"; b.className = "modal-item";
    b.innerHTML = `<strong>${esc(loc?.name || tpl.name)}</strong><small>${esc(loc?.one_liner || tpl.description)}</small>`;
    b.addEventListener("click", async () => {
      const { job_id } = await api("/api/jobs/template", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ template_id: tpl.id, language: lang }),
      });
      openJob(job_id);
    });
    box.appendChild(b);
  });
}

async function loadHealth() {
  try {
    const h = await api("/api/health");
    const pg = $("pill-gemini"), po = $("pill-openscad");
    if (pg) {
      pg.className = `status-pill ${h.gemini_key ? "ok" : "warn"}`;
      pg.textContent = h.gemini_key ? "Gemini" : "Gemini (off)";
    }
    if (po) {
      po.className = `status-pill ${h.openscad ? "ok" : "err"}`;
      po.textContent = h.openscad ? "OpenSCAD" : "OpenSCAD (off)";
    }
  } catch {}
}

$("btn-arch-info")?.addEventListener("click", (e) => {
  const det = $("arch-detail");
  const open = !det.hidden;
  det.hidden = open;
  e.currentTarget.setAttribute("aria-expanded", String(!open));
});

async function init() {
  applyI18n();
  loadHealth();
  loadRecent();
  try {
    cachedTemplates = await api("/api/templates");
    renderTemplatesList();
  } catch {}
  const deep = new URLSearchParams(location.search).get("job");
  if (deep) openJob(deep);
}
init();
