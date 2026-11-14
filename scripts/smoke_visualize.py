#!/usr/bin/env python3
"""Manual smoke test for app/visualize.py (Nano Banana frames + optional Gemini Omni video).

Makes REAL, billable Gemini API calls - run it once a GEMINI_API_KEY is in .env:

    .venv/Scripts/python.exe scripts/smoke_visualize.py --render outputs/<job>/model_iso.png \
        --photo my_kitchen.jpg --start "..." --end "..." --motion "..." --out outputs/smoke_vis [--video]

Without --video only the two frames are generated (two image calls, about a minute).
With --video a 3-10 s first+last-frame clip is generated as well (several minutes).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_START = ("A person with reduced grip strength sits at a bright kitchen table and holds a spoon "
                 "with the 3D-printed handle, about to scoop cereal from a bowl.")
DEFAULT_END = "The same person a few seconds later lifts the full spoon calmly towards their mouth."
DEFAULT_MOTION = "The person scoops cereal with the spoon and lifts it smoothly towards their mouth, static camera."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Manual smoke test of the AI usage visualization (real Gemini API calls; needs GEMINI_API_KEY).")
    ap.add_argument("--render", required=True, type=Path, help="PNG render of the device (e.g. an OpenSCAD *_iso.png)")
    ap.add_argument("--photo", type=Path, default=None, help="optional JPG/PNG scene photo to edit")
    ap.add_argument("--video", action="store_true", help="also generate the Omni transition video (slow, billable)")
    ap.add_argument("--start", default=DEFAULT_START, help="start frame description (English)")
    ap.add_argument("--end", default=DEFAULT_END, help="end frame description (English)")
    ap.add_argument("--motion", default=DEFAULT_MOTION, help="motion description for the video (English)")
    ap.add_argument("--out", required=True, type=Path, help="output directory")
    ap.add_argument("--image-model", default=None, help="override IMAGE_MODEL (default gemini-nano-banana-2.1)")
    ap.add_argument("--video-model", default=None, help="override VIDEO_MODEL (default gemini-omni-1.2-flash)")
    args = ap.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if args.image_model:
        os.environ["IMAGE_MODEL"] = args.image_model
    if args.video_model:
        os.environ["VIDEO_MODEL"] = args.video_model
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print(f"GEMINI_API_KEY is not set (looked in the environment and {ROOT / '.env'}).", file=sys.stderr)
        return 1
    for label, p in (("--render", args.render), ("--photo", args.photo)):
        if p is not None and not p.is_file():
            print(f"{label} file not found: {p}", file=sys.stderr)
            return 2

    from app import visualize  # imported after .env / overrides so IMAGE_MODEL / VIDEO_MODEL apply

    print(f"image model: {visualize.IMAGE_MODEL} | video model: {visualize.VIDEO_MODEL} | "
          f"video: {'yes' if args.video else 'no'} | photo: {args.photo or '(none - generated home scene)'}")

    t0 = time.monotonic()
    last = [t0, None]  # time of the last progress event, its stage

    def progress(stage: str, detail: str) -> None:
        now = time.monotonic()
        prev = f" (+{now - last[0]:.1f}s since '{last[1]}')" if last[1] else ""
        print(f"[{now - t0:7.1f}s] {stage:<8} {detail}{prev}", flush=True)
        last[0], last[1] = now, stage

    try:
        result = visualize.run_visualization(
            args.out, device_render=args.render, photo=args.photo, start_prompt=args.start,
            end_prompt=args.end, motion_prompt=args.motion, with_video=args.video, on_progress=progress)
    except Exception as e:  # noqa: BLE001 - visualize already sanitizes API errors
        print(f"[{time.monotonic() - t0:7.1f}s] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    total = time.monotonic() - t0
    print(f"[{total:7.1f}s] done (last stage '{last[1]}' took {time.monotonic() - last[0]:.1f}s)")
    for k in ("start", "end", "video"):
        p = result.get(k)
        size = f"{p.stat().st_size / 1024:.0f} KB" if p and Path(p).exists() else "-"
        print(f"  {k:<5}: {p or '(skipped)'}  {size}")
    print(f"total: {total:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
