"""Measure dimensions in a photo with app/measure.py, without running the whole pipeline.

Usage (from the repo root):
  .venv\\Scripts\\python scripts\\measure_cli.py demo_inputs\\photo.jpg "sheet width=148" "sheet length=210" \
      [--true "sheet width=148" --true "sheet length=210"] [--out marks.png]

Each dimension is "name=rough estimate in mm" (the estimate only filters out absurd results, x0.5..x2).
With --true the error against the known size is printed. --out saves the photo with all located points drawn.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import gemini, measure  # noqa: E402
from app.schemas import (AnimationBrief, DesignPlan, Measurement, PrintSettings, ScaleReference)  # noqa: E402


def _kv(s: str) -> tuple[str, float]:
    name, _, val = s.rpartition("=")
    return name.strip(), float(val)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("dims", nargs="+", help='"name=estimate_mm"')
    ap.add_argument("--true", action="append", default=[], help='"name=true_mm"')
    ap.add_argument("--out", help="save annotated photo here")
    ap.add_argument("--task", default="Measure the objects in the photo.")
    a = ap.parse_args()

    dims = [_kv(d) for d in a.dims]
    truth = dict(_kv(t) for t in a.true)
    plan = DesignPlan(
        task_summary=a.task, observed_in_media="", functional_limitations=[], root_problem="", design_requirements=[],
        scale_reference=ScaleReference(detected=False, object="", known_size_mm=0, method=""),
        measurements=[Measurement(name=n, value_mm=v, source="media") for n, v in dims],
        approach="custom", template_id="", template_parameters=[], fit_links=[], custom_design_brief="",
        device_name="", how_it_helps="", usage_steps=[],
        print_settings=PrintSettings(material="", layer_height_mm=0.2, infill_percent=20, walls=2, supports=False,
                                     orientation="", notes=""),
        safety_notes=[], assumptions=[], questions_for_user=[],
        animation=AnimationBrief(start_scene="", end_scene="", motion=""), confidence=0)

    photo = Path(a.photo)
    part, w, h = measure._load_photo(photo)
    request = measure._request(plan, plan.measurements)
    gemini.client()
    t0 = time.time()
    with ThreadPoolExecutor(measure.RUNS) as ex:
        marks = list(ex.map(lambda _: measure._locate(part, request), range(measure.RUNS)))
    print(f"{measure.RUNS} runs, thinking={measure.THINKING}: {time.time() - t0:.1f} s")

    per: dict[str, list[float]] = {}
    for i, mk in enumerate(marks):
        vals, info = measure.measure_marks(mk, w, h)
        print(f"  run {i + 1}: reference={info.get('kind')} " +
              (f"tilt={info['tilt']:.2f} " if "tilt" in info else "") +
              " ".join(f"{k}={v:.1f}" for k, v in vals.items()))
        for k, v in vals.items():
            per.setdefault(k, []).append(v)

    print("result (median ± half spread of the runs):")
    for name, est in dims:
        vals = per.get(name)
        if not vals:
            print(f"  {name}: not measured (no reference or not visible) -> keeps estimate {est}")
            continue
        val, unc = measure.aggregate(vals, 0.0)
        line = f"  {name}: {val:.1f} ± {unc:.1f} mm"
        if name in truth:
            err = val - truth[name]
            line += f"   true {truth[name]:g} -> error {err:+.1f} mm ({100 * err / truth[name]:+.1f} %)"
        print(line)

    if a.out:
        from PIL import Image, ImageDraw, ImageOps
        with Image.open(photo) as im0:
            im = ImageOps.exif_transpose(im0).convert("RGB")
        im.thumbnail((measure.MAX_SIDE_PX, measure.MAX_SIDE_PX))
        d = ImageDraw.Draw(im)
        r = max(3, w // 300)
        for i, mk in enumerate(marks):
            col = ["red", "blue", "lime", "orange", "magenta"][i % 5]
            ref = mk.reference
            pts = [ref.coin_left, ref.coin_right, ref.coin_top, ref.coin_bottom] + list(ref.corners)
            for p in pts:
                if p.x or p.y:
                    x, y = measure.to_px(p, w, h)
                    d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=2)
            for ln in mk.lines:
                if ln.visible:
                    d.line([tuple(measure.to_px(ln.p1, w, h)), tuple(measure.to_px(ln.p2, w, h))], fill=col, width=3)
        im.save(a.out)
        print("annotated:", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
