"""Deterministic printability checks for compiled STL meshes (numpy only, no trimesh).

    run_checks(stl_path, min_wall_mm=2.0, bed_mm=(220, 220, 250)) -> {
        "passed": bool, "checks": [...], "feedback": str, "seconds": float}

Used inside the agentic CAD loop (fails/warnings are turned into concrete English feedback for
Gemini) and shown in the UI (English + German labels/details).

Checks: watertight, shells, bed_fit, min_wall, overhang, bed_contact, triangles.
Coordinates are in mm, Z is the print direction (bed at the lowest Z of the mesh).
"""

from __future__ import annotations

import math
import re
import time
from pathlib import Path

import numpy as np

# ---- tunables ------------------------------------------------------------------------------
WELD_MM = 1e-4               # vertices closer than this (grid rounding) are the same vertex
BED_EPS_MM = 0.2             # faces within this height above min Z count as "on the bed"
HARD_MIN_WALL_MM = 1.0       # below this a wall is not reliably printable -> fail
WALL_SAMPLES = 400           # ray samples for the wall thickness estimate (area-weighted)
WALL_SEED = 1234             # deterministic sampling
WALL_START_MM = 1e-3         # ray origin offset into the solid
WALL_IGNORE_MM = 0.05        # hits closer than this are grazing hits at edges / chamfers
WALL_EDGE_MARGIN = 0.15      # keep sample points away from triangle edges (barycentric shrink)
WALL_TOL_MM = 0.05           # measurement slack (float32 STL coordinates, facetted curves)
WALL_CHUNK = 5000           # triangles per culling chunk (memory: samples x chunk floats)
OVERHANG_DEG = 45.0          # from vertical; steeper (flatter) downward faces need support
OVERHANG_TOL_DEG = 1.0       # exact 45 deg chamfers / tessellated 45 deg roofs are printable
OVERHANG_WARN_PCT = 3.0
NEAR_BED_MM = 1.0            # overhangs entirely below this height (rounded/chamfered bottom edges) print fine
OVERHANG_WARN_MM2 = 150.0
FLAT_NZ = 0.99               # |normal_z| above this = horizontal face
BED_CONTACT_WARN_MM2 = 80.0
MAX_TRIANGLES = 400_000
TINY_SHELL_MM3 = 1.0         # extra shells smaller than this are CSG debris, not real parts
TINY_SHELL_MM = 0.5

LABELS = {
    "watertight": ("Closed mesh (watertight)", "Geschlossenes Mesh"),
    "shells": ("Separate parts", "Einzelteile"),
    "bed_fit": ("Fits print bed", "Passt aufs Druckbett"),
    "min_wall": ("Wall thickness", "Wandstärke"),
    "overhang": ("Overhangs", "Überhänge"),
    "bed_contact": ("Bed contact area", "Auflagefläche"),
    "triangles": ("Triangle count", "Dreiecksanzahl"),
}

_STL_DTYPE = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
_VERTEX_RE = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", re.I)


# ---- loading -------------------------------------------------------------------------------

def load_triangles(stl_path: Path) -> np.ndarray:
    """Read a binary or ASCII STL -> float64 array of shape (N, 3, 3) (triangle, vertex, xyz)."""
    data = Path(stl_path).read_bytes()
    if len(data) >= 84:
        n = int.from_bytes(data[80:84], "little")
        if 84 + 50 * n == len(data):
            return np.frombuffer(data, dtype=_STL_DTYPE, count=n, offset=84)["v"].astype(np.float64)
    if data.lstrip()[:5].lower() == b"solid":
        vals = _VERTEX_RE.findall(data)
        if len(vals) % 3:
            raise ValueError(f"ASCII STL has {len(vals)} vertices (not a multiple of 3)")
        if not vals:
            return np.zeros((0, 3, 3))
        try:
            arr = np.array(vals).astype(np.float64)
        except ValueError as e:
            raise ValueError(f"ASCII STL has an unparseable vertex: {e}") from None
        return arr.reshape(-1, 3, 3)
    if len(data) >= 84:  # binary with trailing garbage / padding
        n = int.from_bytes(data[80:84], "little")
        if 84 + 50 * n <= len(data):
            return np.frombuffer(data, dtype=_STL_DTYPE, count=n, offset=84)["v"].astype(np.float64)
    raise ValueError(f"{Path(stl_path).name} is not a valid binary or ASCII STL")


# ---- small helpers -------------------------------------------------------------------------

def _en(x: float, nd: int = 1) -> str:
    s = f"{x:.{nd}f}"
    return s[1:] if s.startswith("-") and float(s) == 0 else s   # no "-0.0"


def _de(x: float, nd: int = 1) -> str:
    return _en(x, nd).replace(".", ",")


def _pl(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _int_en(n: int) -> str:
    return f"{n:,}"


def _int_de(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _dims(v, sep=" x ", nd=1, de=False) -> str:
    f = _de if de else _en
    return sep.join(f(float(x), nd) for x in v)


def _check(cid: str, status: str, value: str, detail_en: str, detail_de: str) -> dict:
    en, de = LABELS[cid]
    return {"id": cid, "label_en": en, "label_de": de, "status": status, "value": value,
            "detail_en": detail_en, "detail_de": detail_de}


def _components(n: int, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Connected components of an undirected graph (vectorized union-find: hook + pointer jumping).
    Returns the root (smallest vertex id) of every vertex."""
    parent = np.arange(n, dtype=np.int64)
    while True:
        ra, rb = parent[a], parent[b]
        diff = ra != rb
        if not diff.any():
            return parent
        lo = np.minimum(ra[diff], rb[diff])
        hi = np.maximum(ra[diff], rb[diff])
        np.minimum.at(parent, hi, lo)  # hi is a root, lo < hi -> stays a forest
        while True:
            nxt = parent[parent]
            if np.array_equal(nxt, parent):
                break
            parent = nxt


# ---- mesh analysis -------------------------------------------------------------------------

class _Mesh:
    def __init__(self, tris: np.ndarray):
        self.tris = tris
        self.n = len(tris)
        flat = tris.reshape(-1, 3)
        self.mins = flat.min(axis=0)
        self.maxs = flat.max(axis=0)
        self.size = self.maxs - self.mins
        v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
        cr = np.cross(v1 - v0, v2 - v0)
        self.dbl = np.linalg.norm(cr, axis=1)          # 2 * area
        self.area = self.dbl / 2.0
        with np.errstate(invalid="ignore", divide="ignore"):
            self.normal = np.where(self.dbl[:, None] > 0, cr / self.dbl[:, None], 0.0)
        c = (self.mins + self.maxs) / 2.0                # reduce cancellation in the volume sum
        a, b, d = v0 - c, v1 - c, v2 - c
        self.tri_vol = np.einsum("ij,ij->i", a, np.cross(b, d)) / 6.0
        self.zmin_t = tris[:, :, 2].min(axis=1)
        self.zmax_t = tris[:, :, 2].max(axis=1)

        # weld vertices on a WELD_MM grid
        q = np.round(flat / WELD_MM).astype(np.int64)
        _, inv = np.unique(q, axis=0, return_inverse=True)
        self.faces = inv.reshape(-1).reshape(-1, 3)
        self.nv = int(self.faces.max()) + 1 if self.n else 0


def _topology(m: _Mesh) -> dict:
    f = m.faces
    degenerate = (f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 2] == f[:, 0])
    fg = f[~degenerate]
    a = np.concatenate([fg[:, 0], fg[:, 1], fg[:, 2]])
    b = np.concatenate([fg[:, 1], fg[:, 2], fg[:, 0]])
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo * np.int64(m.nv) + hi
    ukey, inv, counts = np.unique(key, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    # orientation: on a consistently oriented 2-manifold edge the two half-edges run opposite ways
    sign = np.where(a < b, 1, -1)
    dir_sum = np.bincount(inv, weights=sign, minlength=len(ukey))
    flipped = int(np.count_nonzero((counts == 2) & (dir_sum != 0)))
    return {
        "edges": int(len(ukey)),
        "boundary": int(np.count_nonzero(counts == 1)),
        "nonmanifold": int(np.count_nonzero(counts > 2)),
        "flipped": flipped,
        "degenerate": int(np.count_nonzero(degenerate)),
        "volume": float(m.tri_vol.sum()),
    }


def _shells(m: _Mesh, orient: float) -> list[dict]:
    f = m.faces
    root = _components(m.nv, np.concatenate([f[:, 0], f[:, 1]]), np.concatenate([f[:, 1], f[:, 2]]))
    _, lab = np.unique(root[f[:, 0]], return_inverse=True)
    lab = lab.reshape(-1)
    k = int(lab.max()) + 1
    tri_n = np.bincount(lab, minlength=k)
    area = np.bincount(lab, weights=m.area, minlength=k)
    vol = np.bincount(lab, weights=m.tri_vol, minlength=k) * orient
    tmin = m.tris.min(axis=1)
    tmax = m.tris.max(axis=1)
    bmin = np.full((k, 3), np.inf)
    bmax = np.full((k, 3), -np.inf)
    for ax in range(3):
        np.minimum.at(bmin[:, ax], lab, tmin[:, ax])
        np.maximum.at(bmax[:, ax], lab, tmax[:, ax])
    out = [{"triangles": int(tri_n[i]), "area": float(area[i]), "volume": float(vol[i]),
            "min": bmin[i], "max": bmax[i]} for i in range(k)]
    out.sort(key=lambda s: -abs(s["volume"]))
    return out


def _wall_thickness(m: _Mesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ray-cast wall thickness at area-weighted sample points.
    Returns (thickness per sample, inf where the ray escaped; sample points; ray directions)."""
    good = np.nonzero(m.dbl > 1e-12)[0]
    if len(good) == 0:
        return np.zeros(0), np.zeros((0, 3)), np.zeros((0, 3))
    rng = np.random.default_rng(WALL_SEED)
    p = m.area[good] / m.area[good].sum()
    pick = good[rng.choice(len(good), size=WALL_SAMPLES, p=p)]
    r1, r2 = rng.random(WALL_SAMPLES), rng.random(WALL_SAMPLES)
    s = np.sqrt(r1)
    bary = np.stack([1.0 - s, s * (1.0 - r2), s * r2], axis=1)
    bary = (1.0 - WALL_EDGE_MARGIN) * bary + WALL_EDGE_MARGIN / 3.0
    pts = np.einsum("si,sij->sj", bary, m.tris[pick])
    D = -m.normal[pick]                                  # into the solid
    O = pts + D * WALL_START_MM
    od = np.einsum("ij,ij->i", O, D)
    oo = np.einsum("ij,ij->i", O, O)

    v0 = m.tris[:, 0]
    E1 = m.tris[:, 1] - v0
    E2 = m.tris[:, 2] - v0
    cen = m.tris.mean(axis=1)
    rad = np.sqrt(((m.tris - cen[:, None, :]) ** 2).sum(axis=2).max(axis=1))
    cc = np.einsum("ij,ij->i", cen, cen)
    best = np.full(WALL_SAMPLES, np.inf)

    for s0 in range(0, m.n, WALL_CHUNK):
        s1 = min(s0 + WALL_CHUNK, m.n)
        C = cen[s0:s1]
        r = rad[s0:s1]
        proj = D @ C.T - od[:, None]                     # distance of the centroid along each ray
        dist2 = oo[:, None] + cc[None, s0:s1] - 2.0 * (O @ C.T) - proj * proj
        mask = (dist2 <= (r * r)[None, :] + 1e-6) & (proj + r[None, :] >= WALL_IGNORE_MM)
        ri, ti = np.nonzero(mask)
        if len(ri) == 0:
            continue
        ti = ti + s0
        d = D[ri]
        e1, e2 = E1[ti], E2[ti]
        pvec = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pvec)
        ok = np.abs(det) > 1e-9 * m.dbl[ti]              # skip rays parallel to the triangle
        if not ok.any():
            continue
        ri, ti, d, e1, e2, pvec, det = ri[ok], ti[ok], d[ok], e1[ok], e2[ok], pvec[ok], det[ok]
        inv = 1.0 / det
        tvec = O[ri] - v0[ti]
        u = np.einsum("ij,ij->i", tvec, pvec) * inv
        qvec = np.cross(tvec, e1)
        v = np.einsum("ij,ij->i", d, qvec) * inv
        t = np.einsum("ij,ij->i", e2, qvec) * inv
        hit = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (t > WALL_IGNORE_MM)
        if hit.any():
            np.minimum.at(best, ri[hit], t[hit])
    return best + WALL_START_MM, pts, D


# ---- individual checks ---------------------------------------------------------------------

def _check_watertight(m: _Mesh, topo: dict):
    nb, nm, fl = topo["boundary"], topo["nonmanifold"], topo["flipped"]
    if nb or nm:
        parts_en, parts_de, hints = [], [], []
        if nb:
            parts_en.append(_pl(nb, "open edge", "open edges") + " (holes)")
            parts_de.append(_pl(nb, "offene Kante", "offene Kanten") + " (Löcher)")
            hints.append("close every hole: no 2D or zero-thickness geometry in 3D, let difference() cutters "
                         "pass fully through (extend them by 1 mm) instead of ending exactly on a face")
        if nm:
            parts_en.append(_pl(nm, "non-manifold edge", "non-manifold edges") + " (shared by more than 2 triangles)")
            parts_de.append(_pl(nm, "nicht-mannigfaltige Kante", "nicht-mannigfaltige Kanten")
                            + " (an mehr als 2 Dreiecken)")
            hints.append("solids that only touch along an edge or a point must overlap by at least 0.1 mm "
                         "(or be clearly separated)")
        detail_en = "Mesh is not closed: " + ", ".join(parts_en) + "."
        detail_de = "Mesh ist nicht geschlossen: " + ", ".join(parts_de) + "."
        value = ", ".join(p for p in (f"{nb} open" if nb else "", f"{nm} non-manifold" if nm else "") if p)
        fb = f"Mesh not watertight: {', '.join(parts_en)}. Fix: {'; '.join(hints)}."
        return _check("watertight", "fail", value, detail_en, detail_de), fb
    if fl or topo["volume"] < 0:
        if fl:
            en = f"Closed, but faces at {_pl(fl, 'edge', 'edges')} are inconsistently oriented (flipped normals)."
            de = f"Geschlossen, aber an {_pl(fl, 'Kante', 'Kanten')} sind Flächen falsch orientiert (umgedrehte Normalen)."
        else:
            en = "Closed, but all normals point inwards (inside-out mesh)."
            de = "Geschlossen, aber alle Normalen zeigen nach innen (Mesh ist umgestülpt)."
        fb = "Mesh orientation: " + en + " Fix: check polyhedron() vertex order; most slicers repair this automatically."
        return _check("watertight", "warn", "closed, flipped normals", en, de), fb
    en = f"All {_int_en(topo['edges'])} edges are shared by exactly 2 triangles; normals consistent."
    de = f"Alle {_int_de(topo['edges'])} Kanten gehören zu genau 2 Dreiecken; Normalen konsistent."
    if topo["degenerate"]:
        en += f" ({_pl(topo['degenerate'], 'degenerate triangle', 'degenerate triangles')} ignored.)"
        de += f" ({_pl(topo['degenerate'], 'entartetes Dreieck', 'entartete Dreiecke')} ignoriert.)"
    return _check("watertight", "pass", "closed", en, de), ""


def _check_shells(m: _Mesh, shells: list[dict]):
    zbed = m.mins[2] + BED_EPS_MM
    solids, voids, tiny = [], [], []
    for s in shells:
        small = abs(s["volume"]) < TINY_SHELL_MM3 or float((s["max"] - s["min"]).max()) < TINY_SHELL_MM
        if s is shells[0]:
            solids.append(s)
        elif small:
            tiny.append(s)
        elif s["volume"] < 0:
            voids.append(s)
        else:
            solids.append(s)
    if len(solids) > 1:
        extra = solids[1:]
        floating = [s for s in extra if s["min"][2] > zbed]
        desc = []
        for s in extra[:4]:
            where = "floating" if s["min"][2] > zbed else "on the bed"
            desc.append(f"{_en(s['volume'] / 1000.0, 2)} cm3 at x={_en(s['min'][0])}..{_en(s['max'][0])}, "
                        f"y={_en(s['min'][1])}..{_en(s['max'][1])}, z={_en(s['min'][2])}..{_en(s['max'][2])} mm "
                        f"({where})")
        more = f" (+{len(extra) - 4} more)" if len(extra) > 4 else ""
        main_cm3 = solids[0]["volume"] / 1000.0
        nf = len(floating)
        en = (f"{len(solids)} separate solid parts" + (f", {nf} of them floating in mid-air" if nf else "")
              + f". Main part {_en(main_cm3, 1)} cm³; extra: "
              + "; ".join(d.replace("cm3", "cm³") for d in desc) + more + ".")
        de = (f"{len(solids)} getrennte Teile" + (f", davon {nf} frei schwebend" if nf else "")
              + f". Hauptteil {_de(main_cm3, 1)} cm³, dazu "
              + _pl(len(extra), "weiteres loses Teil", "weitere lose Teile") + ".")
        fb = (f"Mesh has {len(solids)} disconnected solid parts instead of 1 (main part {_en(main_cm3, 1)} cm3). "
              f"Extra parts: {'; '.join(desc)}{more}. They would print as loose or floating pieces. "
              "Fix: connect them to the main body with union() and real overlap (>= 1 mm), "
              "or remove the stray geometry.")
        return _check("shells", "fail", f"{len(solids)} parts", en, de), fb
    if voids or tiny:
        bits_en, bits_de = [], []
        if voids:
            vv = sum(-s["volume"] for s in voids)
            bits_en.append(_pl(len(voids), "closed internal cavity", "closed internal cavities") + f" ({_en(vv, 0)} mm³)")
            bits_de.append(_pl(len(voids), "geschlossener Hohlraum", "geschlossene Hohlräume") + f" ({_de(vv, 0)} mm³)")
        if tiny:
            bits_en.append(_pl(len(tiny), "tiny fragment", "tiny fragments") + f" below {TINY_SHELL_MM3:g} mm³ (CSG debris)")
            bits_de.append(_pl(len(tiny), "winziges Fragment", "winzige Fragmente")
                           + f" unter {_de(TINY_SHELL_MM3, 0)} mm³ (CSG-Reste)")
        en = "One solid part, plus " + " and ".join(bits_en) + "."
        de = "Ein zusammenhängendes Teil, dazu " + " und ".join(bits_de) + "."
        fb = "Extra shells: " + en + (" Fix: avoid coincident faces in difference()/union() (offset cutters by 0.01-1 mm)."
                   if tiny else " Enclosed cavities print fine but cannot be cleaned; make sure that is intended.")
        return _check("shells", "warn", f"1 part + {len(voids) + len(tiny)}", en, de), fb
    return _check("shells", "pass", "1", "The model is one connected part.",
                  "Das Modell ist ein einziges zusammenhängendes Teil."), ""


def _check_bed_fit(m: _Mesh, bed):
    x, y, z = (float(v) for v in m.size)
    bx, by, bz = (float(v) for v in bed)
    eps = 1e-6
    as_is = z <= bz + eps and ((x <= bx + eps and y <= by + eps) or (y <= bx + eps and x <= by + eps))
    srt, bsrt = sorted([x, y, z]), sorted([bx, by, bz])
    any_fit = all(s <= b + eps for s, b in zip(srt, bsrt))
    value = f"{_dims((x, y, z))} mm"
    bed_s = f"{_dims((bx, by, bz), nd=0)} mm"
    bed_de = f"{_dims((bx, by, bz), sep=' × ', nd=0, de=True)} mm"
    size_de = _dims((x, y, z), sep=" × ", de=True)
    if as_is:
        return _check("bed_fit", "pass", value,
                      f"X {_en(x)} × Y {_en(y)} × Z {_en(z)} mm fits the {bed_s.replace(' x ', ' × ')} bed.",
                      f"X {_de(x)} × Y {_de(y)} × Z {_de(z)} mm passt auf das {bed_de} große Druckbett."), ""
    if any_fit:
        en = (f"X {_en(x)} × Y {_en(y)} × Z {_en(z)} mm fits the {bed_s.replace(' x ', ' × ')} bed only "
              "if it is laid on another side (different print orientation).")
        de = (f"{size_de} mm passt nur auf das {bed_de} große Druckbett, wenn es auf eine andere Seite "
              "gelegt wird (andere Druckausrichtung).")
        fb = (f"Bounding box X {_en(x)} x Y {_en(y)} x Z {_en(z)} mm fits the {bed_s} bed only after reorienting it. "
              "Fix: model it in its print orientation or reduce the height to <= "
              f"{_en(bz, 0)} mm.")
        return _check("bed_fit", "warn", value, en, de), fb
    over = [f"{_en(s)} > {_en(b, 0)}" for s, b in zip(srt, bsrt) if s > b + eps]
    en = (f"X {_en(x)} × Y {_en(y)} × Z {_en(z)} mm does not fit the {bed_s.replace(' x ', ' × ')} bed "
          f"in any orientation ({', '.join(over)} mm).")
    de = (f"{size_de} mm passt in keiner Ausrichtung auf das {bed_de} große Druckbett.")
    fb = (f"Part is too big: bounding box X {_en(x)} x Y {_en(y)} x Z {_en(z)} mm does not fit the {bed_s} bed in "
          f"any orientation (sorted dimensions vs. bed: {', '.join(over)} mm). Fix: shrink the longest "
          f"dimension to <= {_en(bsrt[2], 0)} mm (the other two to <= {_en(bsrt[1], 0)} / {_en(bsrt[0], 0)} mm), "
          "e.g. reduce length parameters, or split the design into parts joined after printing.")
    return _check("bed_fit", "fail", value, en, de), fb


def _check_min_wall(m: _Mesh, min_wall_mm: float):
    th, pts, dirs = _wall_thickness(m)
    ok = np.isfinite(th)
    nvalid = int(ok.sum())
    if nvalid < max(20, len(th) // 5):
        en = f"Could not measure: only {nvalid} of {len(th)} test rays hit the opposite wall (mesh open?)."
        de = f"Nicht messbar: nur {nvalid} von {len(th)} Messstrahlen treffen die Gegenwand (Mesh offen?)."
        return _check("min_wall", "warn", "n/a", en, de), "Wall thickness: " + en
    t = th[ok]
    p5 = float(np.percentile(t, 5))
    med = float(np.median(t))
    tmin = float(t.min())
    fail_thr = min(HARD_MIN_WALL_MM, min_wall_mm)
    value = f"p5 {_en(p5, 2)} mm · median {_en(med, 1)} mm"
    base_en = f"5th percentile {_en(p5, 2)} mm, median {_en(med, 1)} mm, thinnest {_en(tmin, 2)} mm ({nvalid} ray samples)"
    base_de = f"5. Perzentil {_de(p5, 2)} mm, Median {_de(med, 1)} mm, dünnste Stelle {_de(tmin, 2)} mm ({nvalid} Messstrahlen)"
    if p5 >= min_wall_mm - WALL_TOL_MM:
        return _check("min_wall", "pass", value, base_en + f"; target ≥ {_en(min_wall_mm, 1)} mm.",
                      base_de + f"; Ziel ≥ {_de(min_wall_mm, 1)} mm."), ""
    status = "fail" if p5 < fail_thr - WALL_TOL_MM else "warn"
    thin = ok.copy()
    thin[ok] = th[ok] < min_wall_mm - WALL_TOL_MM
    tp, td = pts[thin], dirs[thin]
    lo, hi = tp.min(axis=0), tp.max(axis=0)
    mean_dir = np.abs(td).mean(axis=0)
    if mean_dir[2] > 0.7:
        axis = " in Z (horizontal plates / floors / ceilings)"
    elif mean_dir[2] < 0.3:
        axis = (" in X" if mean_dir[0] > 0.8 else " in Y" if mean_dir[1] > 0.8
                else " horizontally (vertical or curved side walls)")
    else:
        axis = ""
    share = 100.0 * thin.sum() / nvalid
    where = (f"x={_en(lo[0])}..{_en(hi[0])}, y={_en(lo[1])}..{_en(hi[1])}, z={_en(lo[2])}..{_en(hi[2])} mm")
    if status == "fail":
        en = base_en + f" - walls thinner than {_en(fail_thr, 1)} mm will not print reliably."
        de = base_de + f" - Wände unter {_de(fail_thr, 1)} mm lassen sich nicht zuverlässig drucken."
    else:
        en = base_en + f" - below the recommended {_en(min_wall_mm, 1)} mm (fragile)."
        de = base_de + f" - unter den empfohlenen {_de(min_wall_mm, 1)} mm (bruchgefährdet)."
    fb = (f"Walls too thin: 5th percentile wall thickness {_en(p5, 2)} mm (median {_en(med, 1)} mm, thinnest "
          f"{_en(tmin, 2)} mm); {_en(share, 0)} % of the surface samples are below {_en(min_wall_mm, 1)} mm, located at "
          f"{where}; thin{axis or ' in mixed directions'}. Fix: make every wall, plate and rib there at least "
          f"{_en(min_wall_mm, 1)} mm thick (increase the wall/thickness parameter or the size of that feature, "
          "or shrink the cut-out next to it); never below 1.0 mm.")
    return _check("min_wall", status, value, en, de), fb


def _check_overhang(m: _Mesh):
    nz = m.normal[:, 2]
    total = float(m.area.sum())
    zb = m.mins[2] + BED_EPS_MM
    on_bed = m.zmax_t <= zb
    thr = -math.sin(math.radians(OVERHANG_DEG + OVERHANG_TOL_DEG))
    down = (nz < thr) & ~on_bed
    near = down & (m.zmax_t <= m.mins[2] + NEAR_BED_MM)   # bottom-edge roundings / chamfers
    over = down & ~near
    a = float(m.area[over].sum())
    a_near = float(m.area[near].sum())
    flat = float(m.area[over & (nz < -FLAT_NZ)].sum())
    pct = 100.0 * a / total if total > 0 else 0.0
    value = f"{_en(a, 0)} mm² ({_en(pct, 1)} %)"
    near_en = (f" ({_en(a_near, 0)} mm² more within {_en(NEAR_BED_MM, 0)} mm of the bed, e.g. rounded bottom edges, "
               "ignored - they print fine.)") if a_near >= 0.5 else ""
    near_de = (f" ({_de(a_near, 0)} mm² weitere bis {_de(NEAR_BED_MM, 0)} mm über dem Bett, z. B. abgerundete "
               "Unterkanten, nicht gezählt - unkritisch.)") if a_near >= 0.5 else ""
    if a <= 0:
        return _check("overhang", "pass", value, "No downward faces flatter than 45° (apart from the bed)." + near_en,
                      "Keine nach unten zeigenden Flächen flacher als 45° (außer auf dem Bett)." + near_de), ""
    zlo, zhi = float(m.zmin_t[over].min()), float(m.zmax_t[over].max())
    en = (f"{_en(a, 0)} mm² ({_en(pct, 1)} % of the surface) faces downward flatter than 45° from vertical, "
          f"at z = {_en(zlo)}..{_en(zhi)} mm; {_en(flat, 0)} mm² of it are flat ceilings (bridges).")
    de = (f"{_de(a, 0)} mm² ({_de(pct, 1)} % der Oberfläche) zeigen flacher als 45° nach unten, "
          f"bei z = {_de(zlo)}..{_de(zhi)} mm; davon {_de(flat, 0)} mm² waagerechte Decken (Brücken).")
    if pct > OVERHANG_WARN_PCT or a > OVERHANG_WARN_MM2:
        o = m.tris[over].reshape(-1, 3)
        lo, hi = o.min(axis=0), o.max(axis=0)
        fb = (f"Overhangs: {_en(a, 0)} mm2 ({_en(pct, 1)} % of the surface) face downwards flatter than 45 deg "
              f"(x={_en(lo[0])}..{_en(hi[0])}, y={_en(lo[1])}..{_en(hi[1])}, z={_en(zlo)}..{_en(zhi)} mm; "
              f"{_en(flat, 0)} mm2 flat ceilings/bridges) - supports will probably be needed. Fix: replace flat "
              "undersides with 45-degree chamfers, use teardrop/diamond shapes for horizontal holes, "
              "or model the part in an orientation where the large flat face is on the bed.")
        return _check("overhang", "warn", value, en + " Supports are probably needed." + near_en,
                      de + " Vermutlich sind Stützstrukturen nötig." + near_de), fb
    return _check("overhang", "pass", value, en + " Small enough to print without supports." + near_en,
                  de + " Klein genug für den Druck ohne Stützen." + near_de), ""


def _check_bed_contact(m: _Mesh):
    nz = m.normal[:, 2]
    on = (nz < -FLAT_NZ) & (m.zmax_t <= m.mins[2] + BED_EPS_MM)
    a = float(m.area[on].sum())
    footprint = float(m.size[0] * m.size[1])
    value = f"{_en(a, 0)} mm²"
    hint = ("Fix: give the part a flat bottom face of at least ~"
            f"{_en(BED_CONTACT_WARN_MM2, 0)} mm2 (cut the underside flat, add a flat base/foot or a sacrificial "
            "brim), or model it so its largest flat face lies at the lowest Z.")
    if a <= 0:
        en = "No flat face touches the bed - the part rests on an edge or a point and will not stick or will tip over."
        de = "Keine ebene Fläche liegt auf dem Druckbett - das Teil steht auf einer Kante oder Spitze und hält nicht."
        return _check("bed_contact", "fail", value, en, de), "No bed contact: " + en + " " + hint
    if a < BED_CONTACT_WARN_MM2:
        en = (f"Only {_en(a, 0)} mm² of flat surface touches the bed (recommended ≥ {_en(BED_CONTACT_WARN_MM2, 0)} mm²) "
              "- poor adhesion, the part may come loose or tip over.")
        de = (f"Nur {_de(a, 0)} mm² liegen flach auf dem Druckbett (empfohlen ≥ {_de(BED_CONTACT_WARN_MM2, 0)} mm²) "
              "- schlechte Haftung, das Teil kann sich lösen oder umkippen.")
        return _check("bed_contact", "warn", value, en, de), \
            f"Small bed contact: only {_en(a, 1)} mm2 of flat face at the lowest Z touches the bed. " + hint
    pct = 100.0 * a / footprint if footprint > 0 else 0.0
    return _check("bed_contact", "pass", value,
                  f"{_en(a, 0)} mm² flat contact with the bed ({_en(pct, 0)} % of the bounding-box footprint).",
                  f"{_de(a, 0)} mm² liegen flach auf dem Druckbett ({_de(pct, 0)} % der Grundfläche)."), ""


def _check_triangles(m: _Mesh):
    value = f"{m.n:,}".replace(",", " ")
    if m.n > MAX_TRIANGLES:
        en = f"{_int_en(m.n)} triangles - very detailed mesh, slicing and previewing will be slow."
        de = f"{_int_de(m.n)} Dreiecke - sehr fein, Slicen und Vorschau werden langsam."
        fb = (f"Mesh has {_int_en(m.n)} triangles (> {_int_en(MAX_TRIANGLES)}). Fix: lower $fn (48-96 is enough), "
              "reduce loop/step counts and avoid minkowski().")
        return _check("triangles", "warn", value, en, de), fb
    return _check("triangles", "pass", value, f"{_int_en(m.n)} triangles.", f"{_int_de(m.n)} Dreiecke."), ""


# ---- public API ----------------------------------------------------------------------------

def run_checks(stl_path: Path, *, min_wall_mm: float = 2.0,
               bed_mm: tuple[float, float, float] = (220.0, 220.0, 250.0)) -> dict:
    """Run all printability checks on an STL file (binary or ASCII).

    Returns {"passed": bool, "checks": [check dicts], "feedback": str, "seconds": float}; a check dict is
    {"id", "label_en", "label_de", "status": "pass"|"warn"|"fail", "value", "detail_en", "detail_de"}.
    "feedback" is concise English for an LLM (every fail/warn with numbers and a fix hint), "" if all pass.
    """
    t0 = time.time()
    tris = load_triangles(Path(stl_path))
    results: list[tuple[dict, str]] = []
    if len(tris) == 0:
        en, de = "The STL contains no triangles.", "Die STL-Datei enthält keine Dreiecke."
        results.append((_check("watertight", "fail", "empty", en, de),
                        "The exported mesh is empty. Fix: make sure the top-level geometry is a non-empty 3D solid."))
    else:
        m = _Mesh(tris)
        topo = _topology(m)
        orient = -1.0 if topo["volume"] < 0 else 1.0
        results.append(_check_watertight(m, topo))
        if orient < 0:  # inside-out mesh: flip so wall/overhang/bed checks still use outward normals
            m.normal = -m.normal
        results.append(_check_shells(m, _shells(m, orient)))
        results.append(_check_bed_fit(m, bed_mm))
        results.append(_check_min_wall(m, float(min_wall_mm)))
        results.append(_check_overhang(m))
        results.append(_check_bed_contact(m))
        results.append(_check_triangles(m))
    checks = [c for c, _ in results]
    order = {"fail": 0, "warn": 1}
    fb_items = sorted(((c, fb) for c, fb in results if c["status"] != "pass" and fb),
                      key=lambda x: order[x[0]["status"]])
    feedback = "\n".join(f"- [{c['status'].upper()}] {fb}" for c, fb in fb_items)
    return {
        "passed": all(c["status"] != "fail" for c in checks),
        "checks": checks,
        "feedback": feedback,
        "seconds": round(time.time() - t0, 3),
    }


if __name__ == "__main__":  # quick manual test: python -m app.checks file.stl [...]
    import json
    import sys

    for arg in sys.argv[1:]:
        print(json.dumps(run_checks(Path(arg)), indent=2, ensure_ascii=False))
