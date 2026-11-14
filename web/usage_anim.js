// AidForge - usage animations (three.js only, no API calls).
//
// Shows how the REAL generated STL is used: simple proxy objects (key + lock, jar,
// spoon, cup, playing cards) are sized from the template parameters and placed in the
// template's own OpenSCAD coordinates, mapped into the viewer exactly like web/app.js
// maps the STL:
//     three = (scad.x, scad.z, -scad.y) + offset
//
// Public API
//   hasUsageAnimation(templateId) -> boolean
//   createUsageAnimation({ THREE, scene, deviceMesh, templateId, params, offset })
//     -> { duration, update(t), dispose(), bounds }
//   `bounds` (THREE.Box3, world space) is an optional extra: the box swept by the whole
//   animation, useful for framing the camera.
//
// The module imports nothing: THREE is passed in, so it always uses the caller's
// three.js instance.

const DEG = Math.PI / 180;

// Defaults mirror app/templates_registry.py (used when a parameter is missing).
const DEFAULTS = {
  key_turner: {
    key_bow_width: 24, key_bow_length: 22, key_bow_thickness: 2.5, lever_length: 85, lever_width: 50,
    thickness: 14, finger_hole: 1, finger_hole_d: 24, bolt_hole: 1, bolt_offset: 11, chamfer: 2, tolerance: 0.3,
  },
  lever_turner: {
    object_diameter: 70, grip_depth: 12, wall: 4, top_thickness: 3, lever_length: 110, lever_width: 26,
    lever_height: 15, levers: 1, rib_count: 30, rib_depth: 1, hang_hole: 1, tolerance: 0.5,
  },
  built_up_handle: {
    grip_length: 110, grip_diameter: 32, bore_shape: 0, bore_diameter: 9, bore_width: 12, bore_thickness: 3.5,
    bore_depth: 80, finger_grooves: 4, groove_depth: 2, end_radius: 4, flat_side: 1, tolerance: 0.3,
  },
  cup_holder: {
    cup_bottom_diameter: 70, cup_top_diameter: 80, cup_height: 95, sleeve_height: 65, wall: 3, base_lip: 4,
    handles: 2, handle_opening_w: 28, handle_bar: 10, handle_thickness: 14, tolerance: 0.8,
  },
  card_holder: {
    holder_length: 180, holder_depth: 55, holder_height: 28, slots: 2, slot_width: 2.2, slot_depth: 20,
    slot_angle: 12, end_margin: 10, corner_radius: 8, chamfer: 2,
  },
};

// Neutral proxy materials ('double' = THREE.DoubleSide).
const MAT = {
  steel: { color: 0xc4cad2, metalness: 0.55, roughness: 0.3 },
  darkSteel: { color: 0x7f868e, metalness: 0.55, roughness: 0.35 },
  brass: { color: 0xc9a54c, metalness: 0.55, roughness: 0.32 },
  dark: { color: 0x1d2126, metalness: 0, roughness: 0.9 },
  plate: { color: 0xaab1b9, metalness: 0.5, roughness: 0.38 },
  door: { color: 0xc9ab84, metalness: 0, roughness: 0.7, opacity: 0.55, depthWrite: false },
  glass: { color: 0xdcebf2, metalness: 0, roughness: 0.05, opacity: 0.3, depthWrite: false, side: "double" },
  honey: { color: 0xd99a32, metalness: 0, roughness: 0.35, opacity: 0.85 },
  label: { color: 0xf3ecdc, metalness: 0, roughness: 0.8, side: "double" },
  lid: { color: 0x9ea8b2, metalness: 0.55, roughness: 0.35 },
  bottleGlass: { color: 0x3f9a63, metalness: 0, roughness: 0.08, opacity: 0.45, depthWrite: false, side: "double" },
  water: { color: 0xbfe3ee, metalness: 0, roughness: 0.2, opacity: 0.55 },
  cap: { color: 0xf2f3f5, metalness: 0, roughness: 0.6 },
  tea: { color: 0xa8612a, metalness: 0, roughness: 0.2, opacity: 0.85, side: "double" },
  food: { color: 0xead8a0, metalness: 0, roughness: 0.85 },
  card: { color: 0xffffff, metalness: 0, roughness: 0.6 },
  cardBack: { color: 0x3f5f9a, metalness: 0, roughness: 0.6 },
};

// ------------------------------------------------------------------ small helpers
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const clamp01 = (x) => clamp(x, 0, 1);
const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
/** eased 0 -> 1 between times a and b */
const ramp = (t, a, b) => easeInOut(clamp01((t - a) / (b - a)));
const lerp = (a, b, s) => a + (b - a) * s;
/** fade in over [a, b], fade out over [c, d] */
const fadeWin = (t, a, b, c, d) => Math.min(ramp(t, a, b), 1 - ramp(t, c, d));
/** smooth 0 -> 1 -> 0 bump between a and b */
const bump = (t, a, b) => Math.sin(Math.PI * clamp01((t - a) / (b - a))) ** 2;

function readParams(templateId, params) {
  const out = { ...DEFAULTS[templateId] };
  if (params && typeof params === "object") {
    const entries = Array.isArray(params)
      ? params.map((q) => [q && q.name, q && q.value])   // tolerate the job.params list format too
      : Object.entries(params);
    for (const [name, v] of entries) {
      const n = Number(v);
      if (name in out && Number.isFinite(n)) out[name] = n;
    }
  }
  return out;
}

/** obj pose = rotate by quat about `pivot`, then translate by `move` (all in the parent's frame) */
function setPose(obj, pivot, quat, move) {
  obj.quaternion.copy(quat);
  obj.position.copy(pivot).applyQuaternion(quat).negate().add(pivot);
  if (move) obj.position.add(move);
}

function makeKit(THREE, offset) {
  const owned = []; // geometries, materials, textures -> disposed in dispose()
  const own = (x) => { owned.push(x); return x; };
  const kit = {
    THREE, offset, own,
    v3: (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z),
    v2: (x, y) => new THREE.Vector2(x, y),
    q: (x, y, z, angle) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(x, y, z), angle),
    group(parent) { const g = new THREE.Group(); parent.add(g); return g; },
    /** group whose children use the template's OpenSCAD coordinates (Z-up, mm) */
    scadGroup(parent) {
      const g = kit.group(parent);
      g.rotation.x = -Math.PI / 2;     // (x, y, z) -> (x, z, -y)
      g.position.copy(offset);
      return g;
    },
    /** OpenSCAD point -> three.js point (same frame as the STL mesh) */
    S(x, y, z) { return new THREE.Vector3(x, z, -y).add(offset); },
    mat(spec) {
      const { side, ...rest } = spec;
      const base = rest.opacity ?? 1;
      const m = new THREE.MeshStandardMaterial({ ...rest, opacity: base, transparent: base < 1 });
      if (side === "double") m.side = THREE.DoubleSide;
      m.userData.baseOpacity = base;
      return own(m);
    },
    /** a fadeable proxy: own group + materials whose opacity follows fade(f) */
    prop(parent) {
      const g = kit.group(parent);
      const mats = [];
      return {
        group: g,
        mat(spec) { const m = kit.mat(spec); mats.push(m); return m; },
        mesh(geo, material, where) {
          own(geo);
          const me = new THREE.Mesh(geo, material);
          (where || g).add(me);
          return me;
        },
        fade(f) {
          f = clamp01(f);
          g.visible = f > 0.003;
          for (const m of mats) {
            const base = m.userData.baseOpacity;
            m.opacity = base * f;
            const tr = base < 1 || f < 0.999;
            if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; }
          }
        },
        addMat(m) { mats.push(m); return m; },
      };
    },
    disposeAll() {
      for (const x of owned) { try { x.dispose(); } catch (e) { /* ignore */ } }
      owned.length = 0;
    },
  };
  return kit;
}

// ================================================================== 1) key turner
// Key bow slides into the slot (opens at scad y=0 towards -y, centred in x, mid-thickness
// in z), an M3 bolt drops through the bolt hole, the device is lifted, a lock cylinder in
// a door plate moves onto the blade and device + key turn 90 deg about the key axis (scad Y).
function keyTurner(k, p, root, device) {
  const { THREE } = k;
  const T = p.thickness, zc = T / 2;
  const w = p.key_bow_width, Lb = p.key_bow_length, kt = p.key_bow_thickness;
  const bw = clamp(w * 0.36, 6, 10);            // blade width
  const blen = clamp(w * 1.6, 30, 48);          // blade length (from the slot opening)
  const lw = p.lever_width;
  const hasBolt = p.bolt_hole >= 0.5;
  const keyHole = hasBolt && p.bolt_offset > 3 && p.bolt_offset < Lb - 3 ? p.bolt_offset : null;

  const liftG = k.group(root);
  const rotG = k.group(liftG);
  if (device) rotG.add(device);
  const sR = k.scadGroup(rotG);   // rotates with the device
  const sL = k.scadGroup(liftG);  // lock housing: lifts, does not rotate

  // --- key (bow + shoulder + blade with bitting), extruded in scad z around the slot mid-plane
  const key = k.prop(sR);
  const sh = new THREE.Shape();
  const r = Math.min(4, w / 4, Lb / 3);
  const sw = Math.min(w / 2 - 1, bw / 2 + 2);   // shoulder half width
  sh.moveTo(-w / 2, 0);
  sh.lineTo(-w / 2, Lb - r); sh.quadraticCurveTo(-w / 2, Lb, -w / 2 + r, Lb);
  sh.lineTo(w / 2 - r, Lb); sh.quadraticCurveTo(w / 2, Lb, w / 2, Lb - r);
  sh.lineTo(w / 2, 0);
  sh.lineTo(sw, 0); sh.lineTo(sw, -3); sh.lineTo(bw / 2, -3);
  const y0 = -6, y1 = -blen + bw * 0.9, depths = [0.35, 0.18, 0.42, 0.25, 0.38];
  const step = (y1 - y0) / depths.length;
  sh.lineTo(bw / 2, y0);
  depths.forEach((d, i) => {
    sh.lineTo(bw / 2 - d * bw, y0 + step * (i + 0.5));
    sh.lineTo(bw / 2, y0 + step * (i + 1));
  });
  sh.lineTo(bw * 0.1, -blen); sh.lineTo(-bw / 2, -blen + bw * 0.45);
  sh.lineTo(-bw / 2, -3); sh.lineTo(-sw, -3); sh.lineTo(-sw, 0);
  sh.closePath();
  if (keyHole !== null) {
    const hole = new THREE.Path();
    hole.absarc(0, keyHole, 1.9, 0, Math.PI * 2, true);
    sh.holes.push(hole);
  }
  const keyGeo = new THREE.ExtrudeGeometry(sh, { depth: kt, bevelEnabled: false, curveSegments: 8 });
  keyGeo.translate(0, 0, zc - kt / 2);
  const keyMesh = key.mesh(keyGeo, key.mat(MAT.steel));

  // --- M3 bolt (head sits in the counterbore at z = T-2.6 .. T)
  let bolt = null;
  if (hasBolt) {
    bolt = k.prop(sR);
    const bm = bolt.mat(MAT.darkSteel);
    const shaftL = Math.max(2, T - 2.6 - 0.8);
    bolt.mesh(new THREE.CylinderGeometry(1.5, 1.5, shaftL, 16).rotateX(Math.PI / 2).translate(0, 0, -shaftL / 2), bm);
    bolt.mesh(new THREE.CylinderGeometry(2.7, 2.7, 2.4, 24).rotateX(Math.PI / 2).translate(0, 0, 1.2), bm);
    bolt.mesh(new THREE.CylinderGeometry(1.3, 1.3, 0.3, 6).rotateX(Math.PI / 2).translate(0, 0, 2.45), bolt.mat(MAT.dark));
  }

  // --- lock: plug (turns with the key) + housing, rosette, door plate (static)
  const rp = bw / 2 + 3.2, rh = rp + 3.5, yFace = -4, lockLen = blen + 10;
  const plateW = 2 * rh + 12, plateH = plateW * 3, plateT = 3;
  const plateZ = zc + plateH * 0.25;
  const plug = k.prop(sR);
  plug.mesh(new THREE.CylinderGeometry(rp, rp, lockLen, 40).translate(0, yFace - lockLen / 2, zc), plug.mat(MAT.brass));
  plug.mesh(new THREE.BoxGeometry(bw + 1.2, 0.8, kt + 1.2).translate(0, yFace + 0.1, zc), plug.mat(MAT.dark));
  const lock = k.prop(sL);
  const chrome = lock.mat(MAT.steel);
  const housingL = lockLen - 0.4;
  lock.mesh(new THREE.CylinderGeometry(rh, rh, housingL, 48).translate(0, yFace - 0.4 - housingL / 2, zc), chrome);
  lock.mesh(new THREE.CylinderGeometry(rh + 5, rh + 6, 2.5, 48).translate(0, yFace - 5.25, zc), chrome);
  lock.mesh(new THREE.BoxGeometry(plateW, plateT, plateH).translate(0, yFace - 6.5 - plateT / 2, plateZ), lock.mat(MAT.plate));
  // ghosted door leaf behind the plate (translucent so it never hides the device)
  const doorT = lockLen - 6.5;
  const door = lock.mesh(new THREE.BoxGeometry(plateW + 50, doorT, plateH).translate(0, yFace - 9.5 - doorT / 2, plateZ), lock.mat(MAT.door));
  door.renderOrder = 2;

  // lift so the turned lever and the door plate stay above the grid
  const liftH = Math.max(0, lw / 2 + 6 - zc, plateH * 0.25 - zc + 1) - k.offset.y;
  const pivot = k.S(0, 0, zc);
  const axis = k.v3(0, 0, -1);  // scad +Y in three.js
  const keyStart = -(Lb + 22), lockStart = -(blen + 6);

  return {
    duration: 9.4,
    update(t) {
      key.fade(fadeWin(t, 0, 0.35, 8.7, 9.2));
      keyMesh.position.y = lerp(keyStart, 0, ramp(t, 0.3, 1.8));
      if (bolt) {
        bolt.fade(fadeWin(t, 1.9, 2.2, 8.7, 9.2));
        bolt.group.position.set(0, p.bolt_offset, T - 2.6 + lerp(24, 0, ramp(t, 2.0, 2.8)));
      }
      liftG.position.y = liftH * (ramp(t, 3.1, 4.0) - ramp(t, 8.2, 9.0));
      const lf = fadeWin(t, 3.5, 4.0, 7.9, 8.4);
      lock.fade(lf); plug.fade(lf);
      const ly = lockStart * (1 - (ramp(t, 4.0, 4.9) - ramp(t, 7.9, 8.4)));
      lock.group.position.y = ly; plug.group.position.y = ly;
      const ang = -Math.PI / 2 * (ramp(t, 5.2, 6.4) - ramp(t, 7.2, 7.9));
      setPose(rotG, pivot, new THREE.Quaternion().setFromAxisAngle(axis, ang));
    },
  };
}

// ================================================================== 2) lever turner
// Printed cavity-up; it lifts, flips 180 deg, lowers onto a jar whose lid diameter is
// object_diameter, turns 90 deg (open) with the lid and lifts the lid off.
function leverTurner(k, p, root, device) {
  const { THREE } = k;
  const tol = p.tolerance, od = p.object_diameter, tt = p.top_thickness;
  const Dc = od + 2 * tol, Do = Dc + 2 * p.wall, H = tt + p.grip_depth;
  const lh = Math.max(p.lever_height, 4), lw = p.lever_width;
  const P = k.S(0, 0, H / 2);           // centre of the cap = flip pivot, jar axis
  const devG = k.group(root);
  if (device) devG.add(device);

  // --- jar (glass + honey + label) and lid, standing on the grid under the cap axis
  // small screw caps (<= 45 mm) sit on a bottle, wide lids on a jar
  const bottle = od <= 45;
  const rb = bottle ? Math.max(od * 0.78, od / 2 + 8) : od / 2 + clamp(od * 0.08, 2, 6);
  const hb = bottle ? clamp(od * 3.6, 100, 135) : clamp(od * 1.05, 45, 130);
  const rn = bottle ? od / 2 - 3 : od / 2 - 1;
  const lidH = p.grip_depth + 4;
  const lidBase = hb - 3, lidTopY = lidBase + lidH;
  const jarG = k.group(root);
  jarG.position.set(P.x, 0, P.z);
  const jar = k.prop(jarG);
  const honeyH = hb * (bottle ? 0.5 : 0.6);
  const honey = jar.mesh(new THREE.CylinderGeometry(rb - 2.6, rb - 2.6, honeyH, 48).translate(0, 2.6 + honeyH / 2, 0), jar.mat(bottle ? MAT.water : MAT.honey));
  honey.renderOrder = 1;
  const shoulder = bottle ? hb * 0.42 : Math.min(14, hb * 0.2), neck = bottle ? hb * 0.14 : 5;
  const pts = [k.v2(0, 0), k.v2(rb - 4, 0), k.v2(rb - 1, 1), k.v2(rb, 4), k.v2(rb, hb - shoulder)];
  for (let i = 1; i <= 6; i++) {
    const s = i / 6;
    pts.push(k.v2(lerp(rb, rn, (1 - Math.cos(Math.PI * s)) / 2), lerp(hb - shoulder, hb - neck, s)));
  }
  pts.push(k.v2(rn, hb), k.v2(0, hb));
  const glass = jar.mesh(new THREE.LatheGeometry(pts, 64), jar.mat(bottle ? MAT.bottleGlass : MAT.glass));
  glass.renderOrder = 2;
  jar.mesh(new THREE.CylinderGeometry(rb + 0.35, rb + 0.35, hb * (bottle ? 0.26 : 0.34), 64, 1, true).translate(0, hb * (bottle ? 0.3 : 0.4), 0), jar.mat(MAT.label));
  const lidG = k.group(jarG);
  const lid = k.prop(lidG);
  lid.mesh(new THREE.CylinderGeometry(od / 2, od / 2, lidH, 72).translate(0, lidBase + lidH / 2, 0), lid.mat(bottle ? MAT.cap : MAT.lid));

  // --- poses
  const Rflip = Math.hypot(Math.max(Do, lw) / 2, Math.max(H / 2, lh - H / 2));
  const mountY = lidTopY - 2 * P.y + tt + k.offset.y;   // flipped: cavity floor (scad z=tt) on the lid top
  const hoverY = mountY + Math.max(p.grip_depth, lh) + 14;
  const liftA = Math.min(Math.max(0, Rflip + 4 - P.y), hoverY);
  const liftOff = lidH + 28;
  const move = k.v3();

  return {
    duration: 9.0,
    update(t) {
      let y = liftA * ramp(t, 0, 0.9);
      y = lerp(y, hoverY, ramp(t, 0.9, 1.8));
      y = lerp(y, mountY, ramp(t, 2.5, 3.5));
      const off = ramp(t, 5.4, 6.4);
      y += liftOff * off;
      const back = ramp(t, 7.5, 8.8);
      y = lerp(y, 0, back);
      const flip = Math.PI * ramp(t, 0.6, 1.8) * (1 - back);
      const twist = ramp(t, 3.8, 5.1);
      const yaw = (Math.PI / 2) * twist * (1 - back);   // counter-clockwise seen from above = open
      setPose(devG, P, k.q(0, 1, 0, yaw).multiply(k.q(1, 0, 0, flip)), move.set(0, y, 0));
      const jf = fadeWin(t, 1.7, 2.3, 7.0, 7.5);
      jar.fade(jf); lid.fade(jf);
      lidG.rotation.y = (Math.PI / 2) * twist;
      lidG.position.y = 1.5 * twist + liftOff * off;   // unscrews slightly, then lifts with the cap
    },
  };
}

// ================================================================== 3) built-up handle
// A spoon whose handle matches the bore (round: bore_diameter, flat: bore_width x
// bore_thickness) slides into the bore from the top end (z = grip_length), then the
// assembly is picked up and tilted ~60 deg like scooping food.
function builtUpHandle(k, p, root, device) {
  const { THREE } = k;
  const L = p.grip_length, R = p.grip_diameter / 2;
  const d = Math.min(p.bore_depth, L + 2);
  const flat = p.bore_shape >= 0.5;
  const ins = Math.max(6, Math.min(d, L) - 1);           // inserted handle length
  const hw = flat ? p.bore_width : p.bore_diameter;
  const ht = flat ? p.bore_thickness : p.bore_diameter;
  const devG = k.group(root);
  if (device) devG.add(device);
  const sG = k.scadGroup(devG);

  // --- spoon in its own scad sub-frame: axis +z, z=0 = handle end, bowl opening towards -y
  const spoon = k.prop(sG);
  const steel = spoon.mat(MAT.steel);
  const hl = ins + 12, neckL = 12;
  const bowlL = clamp(hw * 3.2, 36, 50), bowlW = bowlL * 0.66, bowlD = Math.min(7, bowlW * 0.25);
  if (flat) spoon.mesh(new THREE.BoxGeometry(p.bore_width, p.bore_thickness, hl).translate(0, 0, hl / 2), steel);
  else spoon.mesh(new THREE.CylinderGeometry(hw / 2, hw / 2, hl, 28).rotateX(Math.PI / 2).translate(0, 0, hl / 2), steel);
  const nt = Math.min(ht, 2.4);
  const ns = new THREE.Shape();
  ns.moveTo(-hw / 2, 0); ns.lineTo(hw / 2, 0); ns.lineTo(3, neckL + 4); ns.lineTo(-3, neckL + 4); ns.closePath();
  spoon.mesh(new THREE.ExtrudeGeometry(ns, { depth: nt, bevelEnabled: false }).rotateX(Math.PI / 2).translate(0, nt / 2, hl), steel);
  const zb = hl + neckL + bowlL / 2;
  const bowlGeo = new THREE.SphereGeometry(1, 40, 14, 0, Math.PI * 2, 0, Math.PI / 2).scale(bowlW / 2, bowlD, bowlL / 2).translate(0, 0, zb);
  spoon.mesh(bowlGeo, spoon.mat({ ...MAT.steel, side: "double" }));
  const food = k.prop(spoon.group);
  const foodMesh = food.mesh(new THREE.SphereGeometry(1, 24, 14).scale(bowlW * 0.3, bowlD * 0.7, bowlL * 0.3), food.mat(MAT.food));
  foodMesh.position.set(0, bowlD * 0.2, zb);

  // start just above the opening, or partly inserted if a fully withdrawn spoon would
  // leave the default camera frame (app.js frames 2.2x the device size)
  const spoonLen = hl + neckL + bowlL;
  const visTop = L / 2 + 1.45 * 1.1 * Math.max(L, 2 * R);
  const zEnd1 = L - ins;
  let zEnd0 = L + 6;
  if (zEnd0 + spoonLen > visTop) zEnd0 = Math.max(L - ins * 0.4, visTop - spoonLen);

  const P = k.S(0, 0, L / 2);
  const tilt = 60 * DEG, dipA = 12 * DEG;
  const lift = 14 + Math.max(0, 4 + (L / 2) * Math.cos(tilt + dipA) + R * Math.sin(tilt + dipA) - P.y);
  const move = k.v3();

  return {
    duration: 8.2,
    update(t) {
      spoon.fade(fadeWin(t, 0, 0.35, 7.4, 7.9));
      const zIn = lerp(zEnd0, zEnd1, ramp(t, 0.3, 2.0));
      spoon.group.position.z = lerp(zIn, zEnd0 + 10, ramp(t, 7.0, 7.9));
      const tiltS = ramp(t, 2.4, 3.6) - ramp(t, 5.5, 6.7);
      const ang = -(tilt * tiltS + dipA * bump(t, 3.7, 4.5));   // tip away, bowl opening up
      setPose(devG, P, k.q(1, 0, 0, ang), move.set(0, lift * tiltS, 0));
      const fs = ramp(t, 3.95, 4.4) * (1 - ramp(t, 5.3, 5.8));
      food.fade(fs > 0.01 ? 1 : 0);
      foodMesh.scale.setScalar(Math.max(0.001, fs));
    },
  };
}

// ================================================================== 4) cup holder
// A cup (truncated cone cup_bottom_diameter -> cup_top_diameter, cup_height) lowers into
// the sleeve onto the base lip, then the assembly is lifted and tilted as if drinking.
function cupHolder(k, p, root, device) {
  const { THREE } = k;
  const tol = p.tolerance, sh = p.sleeve_height, ch = p.cup_height;
  const dAt = (z) => p.cup_bottom_diameter + (p.cup_top_diameter - p.cup_bottom_diameter) * z / ch;
  const lipH = p.base_lip > 0 ? 2.5 : 0;
  const r1 = dAt(0) / 2 + tol, r2 = dAt(sh) / 2 + tol;
  const ro = Math.max(r1, r2) + p.wall;
  const rb = p.cup_bottom_diameter / 2, rt = p.cup_top_diameter / 2;
  const devG = k.group(root);
  if (device) devG.add(device);
  const cupG = k.group(devG);   // three.js orientation (y up), origin = cup bottom centre
  const cup = k.prop(cupG);
  const wallT = 2.2, botT = 5;
  const rAt = (y) => rb + (rt - rb) * y / ch;
  const pts = [k.v2(0, 0), k.v2(rb - 1.5, 0), k.v2(rb, 1.5), k.v2(rt, ch), k.v2(rt - wallT, ch),
    k.v2(rAt(botT) - wallT, botT), k.v2(0, botT)];
  const glass = cup.mesh(new THREE.LatheGeometry(pts, 72), cup.mat(MAT.glass));
  glass.renderOrder = 2;
  const liquid = makeLiquid(k, cup, rAt(botT) - wallT - 0.25, botT + 0.05, rt - wallT - 0.25, ch - 0.6, 48);
  liquid.mesh.renderOrder = 1;

  const base = k.S(0, 0, lipH);
  const P = k.S(0, 0, sh / 2);
  const tiltMax = 58 * DEG;
  const lift = 18 + Math.max(0, 4 + (sh / 2) * Math.cos(tiltMax) + ro * Math.sin(tiltMax) - P.y);
  const slide0 = sh - lipH + 16;
  const move = k.v3();

  return {
    duration: 8.6,
    update(t) {
      cup.fade(fadeWin(t, 0, 0.35, 7.7, 8.3));
      cupG.position.copy(base);
      cupG.position.y += lerp(slide0, 0, ramp(t, 0.3, 2.0)) + 25 * ramp(t, 7.6, 8.3);
      const up = ramp(t, 2.4, 3.3) - ramp(t, 6.2, 7.2);
      const ang = (50 * DEG * ramp(t, 3.1, 4.4) + 8 * DEG * ramp(t, 4.4, 5.6)) * (1 - ramp(t, 5.8, 7.0));
      setPose(devG, P, k.q(1, 0, 0, ang), move.set(0, lift * up, 0));  // rim tilts towards +z
      if (cup.group.visible) liquid.update(lerp(0.62, 0.38, ramp(t, 4.4, 5.6)));
    },
  };
}

/** Liquid in a conical cup whose surface stays horizontal in world space: the inner
 *  frustum (local y0..y1) is clipped by the plane worldY = level every frame. */
function makeLiquid(k, prop, r0, y0, r1, y1, N) {
  const { THREE } = k;
  const maxV = 24 * N + 48;
  const pos = new Float32Array(maxV * 3), nor = new Float32Array(maxV * 3);
  const geo = new THREE.BufferGeometry();
  const pa = new THREE.BufferAttribute(pos, 3), na = new THREE.BufferAttribute(nor, 3);
  pa.setUsage(THREE.DynamicDrawUsage); na.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute("position", pa); geo.setAttribute("normal", na);
  geo.setDrawRange(0, 0);
  const mesh = prop.mesh(geo, prop.mat(MAT.tea));
  mesh.frustumCulled = false;
  const ring = (r, y) => Array.from({ length: N }, (_, i) => {
    const a = (i / N) * Math.PI * 2;
    return [r * Math.cos(a), y, r * Math.sin(a)];
  });
  const bot = ring(r0, y0), top = ring(r1, y1);
  const polys = [bot.slice().reverse(), top];
  for (let i = 0; i < N; i++) { const j = (i + 1) % N; polys.push([bot[i], bot[j], top[j], top[i]]); }

  function update(fill) {
    mesh.updateWorldMatrix(true, false);
    const e = mesh.matrixWorld.elements;
    const wy = (x, y, z) => e[1] * x + e[5] * y + e[9] * z + e[13];
    const g = [e[1], e[5], e[9]];
    const gl = Math.hypot(g[0], g[1], g[2]) || 1;
    g[0] /= gl; g[1] /= gl; g[2] /= gl;
    const rimLow = e[5] * y1 + e[13] - r1 * Math.hypot(e[1], e[9]);
    const level = Math.min(wy(0, y0 + (y1 - y0) * fill, 0), rimLow - 0.4);
    const f = (v) => wy(v[0], v[1], v[2]) - level;
    let n = 0;
    const tri = (a, b, c) => {
      if (n + 3 > maxV) return;
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
      const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const l = Math.hypot(nx, ny, nz);
      if (l < 1e-9) return;
      nx /= l; ny /= l; nz /= l;
      for (const q of [a, b, c]) {
        pos[n * 3] = q[0]; pos[n * 3 + 1] = q[1]; pos[n * 3 + 2] = q[2];
        nor[n * 3] = nx; nor[n * 3 + 1] = ny; nor[n * 3 + 2] = nz;
        n++;
      }
    };
    const cut = [];
    for (const poly of polys) {
      const out = [];
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const fa = f(a), fb = f(b);
        if (fa <= 0) out.push(a);
        if ((fa <= 0) !== (fb <= 0)) {
          const s = fa / (fa - fb);
          const q = [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s];
          out.push(q); cut.push(q);
        }
      }
      for (let i = 1; i + 1 < out.length; i++) tri(out[0], out[i], out[i + 1]);
    }
    if (cut.length >= 3) {   // flat liquid surface
      const c = [0, 0, 0];
      for (const q of cut) { c[0] += q[0]; c[1] += q[1]; c[2] += q[2]; }
      c[0] /= cut.length; c[1] /= cut.length; c[2] /= cut.length;
      // basis (u, v) in the plane with u x v = g (so the fan faces up)
      const ref = Math.abs(g[0]) < 0.9 ? [1, 0, 0] : [0, 0, 1];
      let u = [g[1] * ref[2] - g[2] * ref[1], g[2] * ref[0] - g[0] * ref[2], g[0] * ref[1] - g[1] * ref[0]];
      const ul = Math.hypot(u[0], u[1], u[2]); u = u.map((x) => x / ul);
      const v = [g[1] * u[2] - g[2] * u[1], g[2] * u[0] - g[0] * u[2], g[0] * u[1] - g[1] * u[0]];
      const ang = (q) => {
        const dx = q[0] - c[0], dy = q[1] - c[1], dz = q[2] - c[2];
        return Math.atan2(dx * v[0] + dy * v[1] + dz * v[2], dx * u[0] + dy * u[1] + dz * u[2]);
      };
      cut.sort((a, b) => ang(a) - ang(b));
      for (let i = 0; i < cut.length; i++) tri(c, cut[i], cut[(i + 1) % cut.length]);
    }
    geo.setDrawRange(0, n);
    pa.needsUpdate = true; na.needsUpdate = true;
  }
  return { mesh, update };
}

// ================================================================== 5) card holder
// A fan of cards slides into the tilted slot(s) one after another, then one card is
// pulled out and laid on the table in front of the holder.
function cardHolder(k, p, root) {
  const { THREE } = k;
  const a = p.slot_angle * DEG;
  const u = k.v3(0, Math.sin(a), Math.cos(a));      // up along the slot (scad)
  const nF = k.v3(0, -Math.cos(a), Math.sin(a));    // card face normal, towards the player (-y)
  const gamma = Math.PI / 2 - a;                    // card local frame (x, u, nF) = Rx(gamma)
  const sl = p.holder_length - 2 * p.end_margin;
  const sc = clamp((sl - 6) / 63, 0.3, 1);          // standard 63 x 88 mm cards, smaller if the slot is short
  const cw = 63 * sc, chh = 88 * sc;
  const fanMax = 6 * DEG;
  const insert = clamp(p.slot_depth - (cw / 2) * Math.sin(fanMax) - 1, 2, Math.max(2, p.slot_depth - 0.5));
  const rowY = (i) => (p.slots < 1.5 ? 0 : -p.holder_depth * 0.2 + i * p.holder_depth * 0.4);
  const rows = p.slots < 1.5 ? [{ y: rowY(0), n: 6 }] : [{ y: rowY(1), n: 4 }, { y: rowY(0), n: 3 }];
  const sG = k.scadGroup(root);
  const FACES = [["A", "♠"], ["K", "♥"], ["Q", "♣"], ["J", "♦"], ["10", "♥"], ["9", "♠"], ["7", "♦"]];
  const cards = [];
  for (const row of rows) {
    const n = row.n;
    const spread = Math.max(0, Math.min(sl - cw - 4, (n - 1) * cw * 0.42));
    const sep = clamp((p.slot_width - 0.4) / Math.max(1, n - 1), 0.06, 0.4);
    for (let i = 0; i < n; i++) {
      const s = n > 1 ? i / (n - 1) : 0.5;
      const pos = k.v3(-spread / 2 + spread * s, row.y, p.holder_height)
        .addScaledVector(u, -insert)
        .addScaledVector(nF, (s - 0.5) * sep * (n - 1));
      const prop = k.prop(sG);
      const [rank, suit] = FACES[cards.length % FACES.length];
      const edge = prop.mat(MAT.card), back = prop.mat(MAT.cardBack);
      const face = prop.mat(MAT.card);
      const tex = cardTexture(THREE, rank, suit);
      if (tex) { k.own(tex); face.map = tex; }
      const geo = new THREE.BoxGeometry(cw, chh, Math.max(0.05, sep * 0.5)).translate(0, chh / 2, 0);
      prop.mesh(geo, [edge, edge, edge, edge, face, back]);   // +z face = towards the player
      cards.push({ prop, pos, beta: fanMax * (1 - 2 * s) });
    }
  }
  const played = cards[cards.length - 2];
  const flatPos = k.v3(played.pos.x, -p.holder_depth / 2 - 14 - chh, 0.3);

  return {
    duration: 8.2,
    update(t) {
      cards.forEach((c, j) => {
        const t0 = 0.2 + j * 0.4;
        c.prop.fade(fadeWin(t, t0, t0 + 0.3, 7.4, 7.9));
        const g = c.prop.group;
        g.position.copy(c.pos).addScaledVector(u, (1 - ramp(t, t0, t0 + 0.85)) * 60);
        let gam = gamma, bet = c.beta;
        if (c === played) {
          const mv = ramp(t, 5.0, 6.3);
          g.position.addScaledVector(u, ramp(t, 4.3, 5.0) * (insert + 22));
          // forward first (clear of the holder), then down onto the table
          const fy = ramp(t, 5.0, 5.9), fz = ramp(t, 5.35, 6.3);
          g.position.set(lerp(g.position.x, flatPos.x, mv), lerp(g.position.y, flatPos.y, fy), lerp(g.position.z, flatPos.z, fz));
          gam = gamma * (1 - mv); bet = c.beta * (1 - mv);
        }
        g.rotation.set(gam, 0, bet, "XYZ");
      });
    },
  };
}

function cardTexture(THREE, rank, suit) {
  if (typeof document === "undefined") return null;
  const W = 256, Hh = 358;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = Hh;
  const g = cv.getContext("2d");
  if (!g) return null;
  g.fillStyle = "#ffffff"; g.fillRect(0, 0, W, Hh);
  g.strokeStyle = "#cfd5db"; g.lineWidth = 8; g.strokeRect(4, 4, W - 8, Hh - 8);
  const red = suit === "♥" || suit === "♦";
  g.fillStyle = red ? "#c62828" : "#1f2328";
  const corner = () => {
    g.textAlign = "center"; g.textBaseline = "top";
    g.font = "bold 56px Georgia, 'Times New Roman', serif"; g.fillText(rank, 44, 16);
    g.font = "48px 'Segoe UI Symbol', 'DejaVu Sans', sans-serif"; g.fillText(suit, 44, 76);
  };
  corner();
  g.save(); g.translate(W, Hh); g.rotate(Math.PI); corner(); g.restore();
  g.textAlign = "center"; g.textBaseline = "middle";
  g.font = "150px 'Segoe UI Symbol', 'DejaVu Sans', sans-serif"; g.fillText(suit, W / 2, Hh / 2 + 6);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

// ================================================================== public API
const BUILDERS = {
  key_turner: keyTurner,
  lever_turner: leverTurner,
  built_up_handle: builtUpHandle,
  cup_holder: cupHolder,
  card_holder: cardHolder,
};

export function hasUsageAnimation(templateId) {
  return typeof templateId === "string" && Object.prototype.hasOwnProperty.call(BUILDERS, templateId);
}

export function createUsageAnimation({ THREE, scene, deviceMesh, templateId, params, offset } = {}) {
  if (!THREE || !scene || !hasUsageAnimation(templateId)) {
    console.warn("usage_anim: no usage animation for", templateId);
    return { duration: 1, update() {}, dispose() {}, bounds: null };
  }
  const kit = makeKit(THREE, offset && offset.isVector3 ? offset.clone() : new THREE.Vector3());
  const p = readParams(templateId, params);

  // remember everything about the device mesh that the animation may change
  const dev = deviceMesh || null;
  const saved = dev && {
    parent: dev.parent,
    index: dev.parent ? dev.parent.children.indexOf(dev) : -1,
    position: dev.position.clone(),
    quaternion: dev.quaternion.clone(),
    scale: dev.scale.clone(),
    matrixAutoUpdate: dev.matrixAutoUpdate,
  };
  if (dev) {   // the animation works in the mesh's own (parent) frame
    dev.position.set(0, 0, 0); dev.quaternion.identity(); dev.scale.set(1, 1, 1);
    dev.matrixAutoUpdate = true;
  }

  const root = new THREE.Group();
  root.name = "usage-animation";
  if (saved && saved.parent) {   // keep the caller's parent transform (normally the scene itself)
    root.position.copy(saved.position); root.quaternion.copy(saved.quaternion); root.scale.copy(saved.scale);
    saved.parent.add(root);
  } else {
    scene.add(root);
  }

  let disposed = false;
  function restore() {
    if (!dev || !saved) return;
    if (saved.parent) {
      saved.parent.add(dev);   // also removes it from our groups
      const ch = saved.parent.children;
      const i = ch.indexOf(dev);
      if (i >= 0 && saved.index >= 0 && saved.index < ch.length && i !== saved.index) {
        ch.splice(i, 1);
        ch.splice(saved.index, 0, dev);
      }
    } else {
      dev.removeFromParent();
    }
    dev.position.copy(saved.position);
    dev.quaternion.copy(saved.quaternion);
    dev.scale.copy(saved.scale);
    dev.matrixAutoUpdate = saved.matrixAutoUpdate;
    dev.updateMatrix();
    dev.updateMatrixWorld(true);
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    restore();
    root.removeFromParent();
    root.clear();
    kit.disposeAll();
  }

  let anim;
  try {
    anim = BUILDERS[templateId](kit, p, root, dev);
  } catch (e) {
    dispose();
    throw e;
  }
  const D = anim.duration;
  function update(t) {
    if (disposed) return;
    let x = Number(t) || 0;
    if (x < 0 || x > D) x = ((x % D) + D) % D;
    anim.update(x);
  }

  // world-space box swept by the visible parts of the whole animation (optional, for camera framing)
  let bounds = null;
  try {
    bounds = new THREE.Box3();
    const box = new THREE.Box3();
    for (let i = 0; i <= 36; i++) {
      update((D * i) / 36);
      root.updateWorldMatrix(true, true);
      root.traverseVisible((o) => {
        if (!o.isMesh || !o.geometry || o.frustumCulled === false) return;
        if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
        bounds.union(box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld));
      });
    }
  } catch (e) {
    bounds = null;
  }
  update(0);

  return { duration: D, update, dispose, bounds };
}
