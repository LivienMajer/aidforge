"""Generate AI test media (photos + short videos) for the demo cases in demo_inputs/cases/.

These are placeholders for development; replace them with real recordings (same file names) for the demo.

    .venv\\Scripts\\python scripts/make_test_media.py            # all cases, skip existing files
    .venv\\Scripts\\python scripts/make_test_media.py rheuma_key  # one case
"""

import base64
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

from app import config  # noqa: E402,F401  (loads .env)
from app import gemini  # noqa: E402

IMAGE_MODEL = "gemini-nano-banana-2.1"
VIDEO_MODEL = __import__("os").environ.get("VIDEO_MODEL", "gemini-omni-flash-preview")
CASES_DIR = ROOT / "demo_inputs" / "cases"

STYLE = ("Realistic, unedited smartphone footage, natural daylight, static camera, sharp focus. Respectful, "
         "dignified depiction of an everyday situation; no medical setting, no text, no music.")

MEDIA = {
    "rheuma_key": {
        "photo_1_door.jpg": "A realistic smartphone photo of the outside of an apartment front door, taken from the "
                            "side at hip height: the brass door handle and the round euro-profile cylinder lock below "
                            "it are clearly visible, soft daylight from a stairwell window, slightly worn white paint.",
        "photo_2_key_coin.jpg": None,  # copied from demo_inputs/key_with_coin.jpg
        "video_attempt.mp4": "Close-up at a front door lock: the hand of a woman in her late sixties with rheumatoid "
                             "arthritis - visibly swollen knuckles and fingers slightly deviated towards the little "
                             "finger - tries to turn a small brass key that is already in the lock, holding the key "
                             "head between thumb and the side of the index finger. The grip slips off the small key "
                             "head twice, she winces slightly, lets go and shakes her hand, then tries again by "
                             "turning her whole forearm, the key barely moves. " + STYLE,
    },
    "parkinson_spoon": {
        "photo_1_spoon_coin.jpg": "A realistic smartphone photo taken straight from above: an ordinary thin stainless "
                                  "steel tablespoon lying flat on a light wooden kitchen table next to a 1 euro coin "
                                  "for scale, natural daylight, nothing else on the table.",
        "video_attempt.mp4": "Medium close-up at a kitchen table: a man in his seventies with Parkinson's disease eats "
                             "soup from a bowl with a thin metal spoon. His right hand shows a clear rhythmic tremor; "
                             "as he lifts the spoon towards his mouth the soup spills back into the bowl and onto the "
                             "table, he tries again more slowly, supporting his right wrist with his left hand. "
                             + STYLE,
    },
    "tetra_toothbrush": {
        "photo_1_hand_card.jpg": "A realistic smartphone photo taken straight from above: the right hand of a young "
                                 "man with tetraplegia rests palm-down and relaxed on a light grey bathroom counter, "
                                 "fingers loosely curled and not touching each other, next to it a standard bank card "
                                 "(credit card size) for scale and a plain manual toothbrush. Soft daylight.",
        "video_attempt.mp4": "Close-up at a bathroom sink: a young man with tetraplegia (C6) tries to pick up a "
                             "manual toothbrush from the counter. He can lift his wrist, and when he extends the "
                             "wrist his fingers close slightly (tenodesis), but they cannot close around the thin "
                             "handle; he tries to trap the toothbrush between both palms, it slips and falls back "
                             "onto the counter. " + STYLE,
    },
}


def make_image(prompt: str, out: Path) -> None:
    it = gemini.client().interactions.create(
        model=IMAGE_MODEL, input=[{"type": "text", "text": prompt}],
        response_format={"type": "image", "aspect_ratio": "4:3", "image_size": "1K"},
    )
    out.write_bytes(base64.b64decode(it.output_image.data))


def make_video(prompt: str, out: Path) -> None:
    cl = genai.Client(http_options=types.HttpOptions(timeout=600 * 1000))
    it = cl.interactions.create(
        model=VIDEO_MODEL, input=[{"type": "text", "text": prompt}],
        response_format={"type": "video", "delivery": "uri", "aspect_ratio": "16:9", "duration": "6s",
                         "resolution": "720p"},
    )
    if not it.output_video or not it.output_video.uri:
        raise RuntimeError("no video returned")
    out.write_bytes(cl.files.download(file=it.output_video.uri))


def run_case(case: str) -> None:
    d = CASES_DIR / case
    d.mkdir(parents=True, exist_ok=True)
    for name, prompt in MEDIA[case].items():
        out = d / name
        if out.exists():
            print(f"[{case}] {name}: exists, skipped")
            continue
        t0 = time.time()
        try:
            if prompt is None:
                out.write_bytes((ROOT / "demo_inputs" / "key_with_coin.jpg").read_bytes())
            elif name.endswith(".mp4"):
                make_video(prompt, out)
            else:
                make_image(prompt, out)
            print(f"[{case}] {name}: ok in {time.time() - t0:.0f}s")
        except Exception as e:  # noqa: BLE001
            print(f"[{case}] {name}: FAILED {str(e)[:200]}")


if __name__ == "__main__":
    cases = sys.argv[1:] or list(MEDIA)
    threads = [threading.Thread(target=run_case, args=(c,)) for c in cases]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
