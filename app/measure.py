"""Precise measurement from photos (feature flag PRECISE_MEASURE, default on).

Gemini only LOCATES points in the photo (reference object + two end points per dimension, normalised 0..1000);
Python converts them to millimetres:
  - coin    -> mm per pixel from its diameter (larger of the two axes; a tilted coin looks elliptical)
  - card/A4 -> perspective correction: homography from the 4 corners onto the known rectangle in mm
The measuring call runs N times in parallel; median = value, half the spread = +/- uncertainty.
The result updates plan.measurements (source "reference"), the linked template_parameters (fit_links) and the
template's `tolerance`. Values with source "user" are never touched. Every error falls back to the unchanged plan.
"""

from __future__ import annotations

import base64
import io
import math
import os
import statistics
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import numpy as np
from pydantic import BaseModel, Field

from . import config
from .schemas import DesignPlan, Measurement, ParamValue
from .templates_registry import BY_ID

ENABLED = os.environ.get("PRECISE_MEASURE", "1").strip().lower() not in ("0", "false", "no", "off")
RUNS = int(os.environ.get("MEASURE_RUNS", "3"))
THINKING = os.environ.get("MEASURE_THINKING", "low")
MAX_PHOTOS = 3
MAX_SIDE_PX = 2048            # photos are normalised (EXIF rotation, size) before Gemini sees them
LOCATE_FLOOR = 2.0            # +/- this many 1/1000 of the image: floor for the uncertainty of one point pair
COIN_TILT_WARN = 0.95         # minor/major axis ratio below this -> coin is tilted, add uncertainty
PLAUSIBLE_RATIO = (0.5, 2.0)  # reject a measured value this far from the analysis estimate
UNSURE_MM = 1.5               # above this uncertainty ask the user to re-measure
TOLERANCE_GAIN = 0.5          # tolerance = base + gain * max(uncertainty of the linked dimensions)

# known reference sizes in mm: circle -> diameter, rectangle -> (long, short)
CIRCLES = {"coin_1_eur": 23.25, "coin_2_eur": 25.75, "coin_50_cent": 24.25, "coin_20_cent": 22.25,
           "coin_10_cent": 19.75, "coin_5_cent": 21.25, "quarter_usd": 24.26}
RECTS = {"card": (85.60, 53.98), "a4": (297.0, 210.0)}


# ---- structured output of the locating call ---------------------------------------------------

class P2(BaseModel):
    y: float = Field(description="Vertical position, 0 = top edge of the image, 1000 = bottom edge.")
    x: float = Field(description="Horizontal position, 0 = left edge of the image, 1000 = right edge.")


class ReferenceMarks(BaseModel):
    kind: str = Field(description="One of: " + ", ".join([*CIRCLES, *RECTS, "none"]) + ". 'card' = any ISO "
                      "ID-1 card (bank/credit/health insurance card).")
    coin_left: P2 = Field(description="Coin only: leftmost point of the coin's rim. 0,0 otherwise.")
    coin_right: P2 = Field(description="Coin only: rightmost point of the coin's rim. 0,0 otherwise.")
    coin_top: P2 = Field(description="Coin only: topmost point of the coin's rim. 0,0 otherwise.")
    coin_bottom: P2 = Field(description="Coin only: bottommost point of the coin's rim. 0,0 otherwise.")
    corners: list[P2] = Field(description="Card / A4 only: the 4 outer corners, going around the rectangle "
                                          "(e.g. clockwise from top-left). Empty otherwise.")


class LineMark(BaseModel):
    name: str = Field(description="Exactly the dimension name from the request.")
    visible: bool = Field(description="False if both end points cannot be seen clearly in this photo.")
    p1: P2 = Field(description="First end point of the dimension, on the object's outer edge.")
    p2: P2 = Field(description="Second end point, opposite edge; the segment p1-p2 spans the dimension.")


class MeasureMarks(BaseModel):
    reference: ReferenceMarks
    lines: list[LineMark]


SYSTEM = """You are a precise photogrammetry assistant. You do NOT estimate sizes. You only locate points in the
image as accurately as possible, in normalised coordinates (y and x from 0 to 1000; y=0 top, x=0 left).

1. Reference object: identify the coin, card or A4 sheet used for scale and mark it.
   - Coin: seen at an angle it is an ellipse. Mark the leftmost, rightmost, topmost and bottommost points of
     the rim of its FLAT TOP FACE (the face you see), not of the coin's side edge / thickness band below it
     and not of its shadow.
   - Card / A4 sheet: its 4 outer corners in order around the rectangle (where the edges would meet if the
     corners are rounded).
   - If there is no such object, kind = "none".
2. For every requested dimension: two end points EXACTLY ON the object's outer silhouette - the boundary where
   the object ends and the background begins - on opposite sides, so that the straight segment between them
   crosses the whole part and spans exactly that dimension. Example: key head width = from one side edge of the
   key head across to the opposite side edge, at its widest point, perpendicular to the blade; both points lie
   on the background just at the metal's edge, never inside the metal, never at a hole. Lengths along the part
   run from its very end to the stated feature. Edges, not shadows or reflections.
   Only dimensions lying flat in the plane of the table / reference object can be measured: thickness, height
   or anything pointing towards the camera -> visible = false. Also visible = false if an end point is hidden.
Use exactly the requested dimension names."""


# ---- pure geometry (tested in tests/test_measure.py) ---------------------------------------------

def to_px(p: P2, w: int, h: int) -> np.ndarray:
    return np.array([p.x / 1000.0 * w, p.y / 1000.0 * h], dtype=float)


def homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """3x3 H with dst ~ H @ src for 4 point pairs (DLT, h33 = 1)."""
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(a, dtype=float), np.array(b, dtype=float))
    return np.append(h, 1.0).reshape(3, 3)


def apply_h(h: np.ndarray, pts: np.ndarray) -> np.ndarray:
    p = np.c_[pts, np.ones(len(pts))] @ h.T
    return p[:, :2] / p[:, 2:3]


def order_cyclic(pts: np.ndarray) -> np.ndarray:
    """Sort 4 corner points by angle around their centroid (consistent order around the quadrilateral)."""
    c = pts.mean(axis=0)
    return pts[np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))]


def rect_homography(corners_px: np.ndarray, long_mm: float, short_mm: float) -> np.ndarray:
    """Homography image px -> mm plane of a rectangle of known size; long side = longer pair in the image."""
    q = order_cyclic(corners_px)
    d = [np.linalg.norm(q[i] - q[(i + 1) % 4]) for i in range(4)]
    if d[0] + d[2] >= d[1] + d[3]:
        dst = np.array([[0, 0], [long_mm, 0], [long_mm, short_mm], [0, short_mm]], dtype=float)
    else:
        dst = np.array([[0, 0], [short_mm, 0], [short_mm, long_mm], [0, long_mm]], dtype=float)
    return homography(q, dst)


def coin_scale(left: np.ndarray, right: np.ndarray, top: np.ndarray, bottom: np.ndarray,
               diameter_mm: float) -> tuple[np.ndarray, float]:
    """Per-axis mm per pixel (x, y) from a coin and its minor/major axis ratio (1.0 = seen straight from above).

    A circle on the table seen by a tilted camera is an ellipse; with the usual forward tilt its axes are the image
    axes, so scaling x and y separately undoes the foreshortening (affine rectification of the table plane)."""
    dx, dy = abs(right[0] - left[0]), abs(bottom[1] - top[1])
    if min(dx, dy) <= 0:
        raise ValueError("degenerate coin")
    return np.array([diameter_mm / dx, diameter_mm / dy]), min(dx, dy) / max(dx, dy)


def aggregate(values: list[float], floor_mm: float) -> tuple[float, float]:
    """Median and +/- uncertainty (half the spread, at least floor_mm)."""
    med = float(statistics.median(values))
    spread = (max(values) - min(values)) / 2.0 if len(values) > 1 else 0.0
    return med, max(spread, floor_mm)


def couple_tolerance(base: float, max_unc: float, lo: float, hi: float) -> float:
    return round(max(lo, min(hi, base + TOLERANCE_GAIN * max_unc)), 2)


def measure_marks(marks: MeasureMarks, w: int, h: int) -> tuple[dict[str, float], dict]:
    """Convert one locating result to {dimension name: mm} plus info about the reference."""
    ref = marks.reference
    kind = ref.kind.strip().lower()
    lines = [ln for ln in marks.lines if ln.visible]
    out: dict[str, float] = {}
    if kind in RECTS and len(ref.corners) == 4:
        long_mm, short_mm = RECTS[kind]
        hm = rect_homography(np.array([to_px(p, w, h) for p in ref.corners]), long_mm, short_mm)
        for ln in lines:
            a, b = apply_h(hm, np.array([to_px(ln.p1, w, h), to_px(ln.p2, w, h)]))
            out[ln.name] = float(np.linalg.norm(a - b))
        # floor: one locating step (LOCATE_FLOOR/1000 of the image) mapped to mm at the card's centre
        c = np.array([[w / 2, h / 2], [w / 2 + LOCATE_FLOOR / 1000 * w, h / 2]])
        cm = apply_h(hm, c)
        return out, {"kind": kind, "method": "homography", "floor_mm": float(np.linalg.norm(cm[0] - cm[1])),
                     "tilt": 1.0}
    if kind in CIRCLES:
        pts = [to_px(p, w, h) for p in (ref.coin_left, ref.coin_right, ref.coin_top, ref.coin_bottom)]
        mmpp, ratio = coin_scale(*pts, CIRCLES[kind])
        for ln in lines:
            out[ln.name] = float(np.linalg.norm((to_px(ln.p1, w, h) - to_px(ln.p2, w, h)) * mmpp))
        return out, {"kind": kind, "method": "coin", "floor_mm": LOCATE_FLOOR / 1000 * max(w, h) * float(mmpp.max()),
                     "tilt": ratio}
    return {}, {"kind": "none"}


# ---- plan update (tested) ----------------------------------------------------------------------

def apply_results(plan: DesignPlan, results: dict[str, tuple[float, float, str]], language: str = "de") -> DesignPlan:
    """results: {measurement name: (value_mm, uncertainty_mm, method)} -> updated copy of the plan."""
    plan = plan.model_copy(deep=True)
    by_name = {m.name: m for m in plan.measurements}
    changed: dict[str, Measurement] = {}
    for name, (val, unc, method) in results.items():
        m = by_name.get(name)
        if m is None or m.source == "user":
            continue
        m.value_mm, m.uncertainty_mm, m.method, m.source = round(val, 1), round(unc, 1), method, "reference"
        changed[name] = m
    if not changed:
        return plan

    params = {p.name: p for p in plan.template_parameters}
    linked_unc = []
    for link in plan.fit_links:
        m = changed.get(link.measurement_name)
        if m is None:
            continue
        linked_unc.append(m.uncertainty_mm)
        if link.param_name in params:
            params[link.param_name].value = m.value_mm
        else:
            plan.template_parameters.append(ParamValue(name=link.param_name, value=m.value_mm))
            params[link.param_name] = plan.template_parameters[-1]

    t = BY_ID.get(plan.template_id)
    tol = next((p for p in t.params if p.name == "tolerance"), None) if t else None
    if tol and linked_unc:
        base = params["tolerance"].value if "tolerance" in params else tol.default
        new = couple_tolerance(base, max(linked_unc), tol.min, tol.max)
        if "tolerance" in params:
            params["tolerance"].value = new
        else:
            plan.template_parameters.append(ParamValue(name="tolerance", value=new))

    for m in changed.values():
        if m.uncertainty_mm > UNSURE_MM:
            q = (f"Bitte {m.name} nachmessen (Foto-Messung: {m.value_mm:g} ± {m.uncertainty_mm:g} mm)."
                 if language == "de" else
                 f"Please measure {m.name} by hand (photo measurement: {m.value_mm:g} ± {m.uncertainty_mm:g} mm).")
            plan.questions_for_user.append(q)
    return plan


# ---- Gemini + orchestration ----------------------------------------------------------------------

def _load_photo(path: Path) -> tuple[dict, int, int]:
    """Upright, size-limited JPEG part for Gemini + its exact pixel size (the size the coordinates refer to)."""
    from PIL import Image, ImageOps

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=92)
        w, h = im.size
    return {"type": "image", "data": base64.b64encode(buf.getvalue()).decode(), "mime_type": "image/jpeg"}, w, h


def _targets(plan: DesignPlan) -> list[Measurement]:
    names = [l.measurement_name for l in plan.fit_links] or [m.name for m in plan.measurements]
    return [m for m in plan.measurements if m.name in names and m.source != "user"]


def _request(plan: DesignPlan, targets: list[Measurement]) -> str:
    t = BY_ID.get(plan.template_id)
    pdesc = {p.name: p.description for p in t.params} if t else {}
    link = {l.measurement_name: l.param_name for l in plan.fit_links}
    dims = "\n".join(f"- {m.name}" + (f" (= {pdesc[link[m.name]]})" if link.get(m.name) in pdesc else "")
                     for m in targets)
    hint = plan.scale_reference.object if plan.scale_reference.detected else "unknown"
    return (f"Object / task: {plan.task_summary}\nReference object seen by a previous analysis: {hint}\n"
            f"Dimensions to mark:\n{dims}")


def _locate(part: dict, request: str) -> MeasureMarks:
    from . import gemini
    return gemini.generate_json(config.ANALYSIS_MODEL, [part, gemini.text(request)], MeasureMarks, SYSTEM,
                                thinking=THINKING, retries=1)


def measure_photos(plan: DesignPlan, photos: list[Path]) -> dict[str, tuple[float, float, str]]:
    targets = _targets(plan)
    if not targets or not photos:
        return {}
    request = _request(plan, targets)
    loaded = [_load_photo(p) for p in photos[:MAX_PHOTOS]]
    jobs = [(part, w, h) for part, w, h in loaded for _ in range(RUNS)]
    from . import gemini
    gemini.client()  # create the shared client once; lazy creation in parallel threads closes clients in use
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futures = [(ex.submit(_locate, part, request), w, h) for part, w, h in jobs]
        runs = []
        for f, w, h in futures:
            try:
                runs.append(measure_marks(f.result(), w, h))
            except Exception:  # noqa: BLE001 - a failed run just does not count
                traceback.print_exc()

    estimate = {m.name: m.value_mm for m in targets}
    results: dict[str, tuple[float, float, str]] = {}
    for name in estimate:
        vals, floors, tilts, kinds = [], [], [], set()
        for values, info in runs:
            v = values.get(name)
            if v is None or not math.isfinite(v) or v <= 0:
                continue
            if estimate[name] > 0 and not (PLAUSIBLE_RATIO[0] <= v / estimate[name] <= PLAUSIBLE_RATIO[1]):
                continue
            vals.append(v); floors.append(info["floor_mm"]); tilts.append(info["tilt"]); kinds.add(info["kind"])
        if not vals:
            continue
        val, unc = aggregate(vals, max(floors))
        tilt = min(tilts)
        if tilt < COIN_TILT_WARN:  # tilted view: the per-axis correction ignores depth changes across the photo
            unc += val * (1 - tilt) * 0.25
        how = "homography" if any(k in RECTS for k in kinds) else "coin"
        results[name] = (val, unc, f"{how} ({'/'.join(sorted(kinds))}), {len(vals)} runs")
    return results


def refine_plan(plan: DesignPlan, photos: list[Path], on_progress: Callable[[str], None] | None = None,
                language: str = "de") -> DesignPlan:
    """Re-measure the fit-critical dimensions in the photos. Never raises; returns the unchanged plan on failure."""
    if not ENABLED or not photos:
        return plan
    try:
        if on_progress:
            on_progress("Messe Maße im Foto …" if language == "de" else "Measuring dimensions in the photo …")
        results = measure_photos(plan, [Path(p) for p in photos if p])
        return apply_results(plan, results, language) if results else plan
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return plan
