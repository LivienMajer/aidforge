// AidForge - "realistic storyboard": key poses of the three.js usage animation of the REAL STL
// are rendered offscreen and sent to the backend, which turns each pose into a photorealistic
// image with Nano Banana (image-to-image; allowed in the EEA, unlike video inputs to Omni).
//
// Self-contained on purpose (own renderer/scene), so it does not depend on web/app.js internals.
//
// Public API
//   hasStoryboard(templateId) -> boolean
//   capturePoses({ stlUrl, templateId, params, width?, height? }) -> Promise<Blob[]>   (PNG per pose)
//   requestStoryboard(jobId, { stlUrl, templateId, params }) -> Promise<{job_id}>     (captures + uploads)
//   Results appear in GET /api/jobs/<id> as job.visual.storyboard = [{url, step}], status in job.visual.

import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { createUsageAnimation, hasUsageAnimation } from "./usage_anim.js";

// Seconds into each usage animation that tell the story (see the ramp() timings in usage_anim.js).
const KEYFRAMES = {
  key_turner: [3.0, 5.0, 7.0],      // key fixed in the turner -> turner at the lock -> turned 90 deg
  lever_turner: [3.6, 5.3, 6.6],    // cap on the lid -> twisted -> lid lifted off
  built_up_handle: [2.2, 4.0, 5.2], // spoon in the grip -> scooping -> lifting food
  cup_holder: [2.2, 3.4, 5.0],      // cup in the sleeve -> lifted -> drinking tilt
  card_holder: [3.0, 5.0, 6.5],     // cards slide in -> fanned -> one card played
};

// What each keyframe shows (English, sent to the image model so it follows the pose change).
const CAPTIONS = {
  key_turner: [
    "The key is clamped in the orange turner; the hand holds the turner in front of the door lock, key not yet inserted.",
    "The key is fully inserted in the lock cylinder; the orange lever is horizontal, held with a relaxed whole-hand grip.",
    "The hand has rotated the orange lever by 90 degrees around the key axis: the lever now points straight down (vertical) and the key is turned in the lock.",
  ],
  lever_turner: [
    "The orange cap sits on the jar lid; the hand rests on the lever.",
    "The hand has pushed the lever a quarter turn sideways; cap and lid have twisted together.",
    "The lid is lifted off the jar together with the orange cap; the jar is open.",
  ],
  built_up_handle: [
    "The spoon handle is inserted into the thick orange grip, held loosely in the hand above a bowl.",
    "The spoon dips into the bowl and scoops food.",
    "The spoon is lifted with food on it, level and steady.",
  ],
  cup_holder: [
    "The cup stands in the orange two-handled holder on the table, hands reaching for both handles.",
    "Both hands lift the holder with the cup off the table.",
    "The cup is tilted towards the mouth for drinking, held steadily with both handles.",
  ],
  card_holder: [
    "Playing cards are being slid into the orange card holder on the table.",
    "The cards stand fanned in the holder, readable.",
    "One hand pulls a single card out of the holder to play it.",
  ],
};

export function hasStoryboard(templateId) {
  return !!KEYFRAMES[templateId] && hasUsageAnimation(templateId);
}

function loadGeometry(url) {
  return new Promise((resolve, reject) => new STLLoader().load(url, resolve, undefined, reject));
}

export async function capturePoses({ stlUrl, templateId, params, width = 1280, height = 720 }) {
  if (!hasStoryboard(templateId)) throw new Error(`No storyboard for template ${templateId}`);

  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(1);
  renderer.setClearColor(0xffffff, 1);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x9aa3a0, 1.7));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(150, 260, 180);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, 0.8);
  fill.position.set(-200, 80, -150);
  scene.add(fill);

  // same transform as the main viewer (web/app.js), so usage_anim.js lines up with the part
  const geo = await loadGeometry(stlUrl);
  geo.rotateX(-Math.PI / 2);
  geo.computeBoundingBox();
  const bb = geo.boundingBox;
  const c = new THREE.Vector3(); bb.getCenter(c);
  const offset = new THREE.Vector3(-c.x, -bb.min.y, -c.z);
  geo.translate(offset.x, offset.y, offset.z);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.5, metalness: 0.05 }));
  scene.add(mesh);

  const anim = createUsageAnimation({ THREE, scene, deviceMesh: mesh, templateId, params, offset });
  const camera = new THREE.PerspectiveCamera(35, width / height, 0.5, 5000);
  const box = anim.bounds && !anim.bounds.isEmpty() ? anim.bounds : new THREE.Box3().setFromObject(mesh);
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  const dist = radius / Math.sin((camera.fov * Math.PI) / 360) * 1.05;
  camera.position.copy(center).add(new THREE.Vector3(0.75, 0.55, 0.85).normalize().multiplyScalar(dist));
  camera.lookAt(center);
  camera.near = dist / 100; camera.far = dist * 10; camera.updateProjectionMatrix();

  const blobs = [];
  try {
    for (const t of KEYFRAMES[templateId]) {
      anim.update(Math.min(t, anim.duration));
      renderer.render(scene, camera);
      blobs.push(await new Promise((res) => renderer.domElement.toBlob(res, "image/png")));
    }
  } finally {
    anim.dispose();
    geo.dispose();
    mesh.material.dispose();
    renderer.dispose();
  }
  return blobs;
}

export async function requestStoryboard(jobId, { stlUrl, templateId, params }) {
  const blobs = await capturePoses({ stlUrl, templateId, params });
  const fd = new FormData();
  blobs.forEach((b, i) => fd.append("poses", b, `pose_${i + 1}.png`));
  fd.append("captions", JSON.stringify(CAPTIONS[templateId] || []));
  const res = await fetch(`/api/jobs/${jobId}/storyboard`, { method: "POST", body: fd });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}
