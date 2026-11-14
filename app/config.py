"""Central configuration. Override anything via environment variables or a .env file."""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

APP_NAME = os.environ.get("APP_NAME", "AidForge")

# Gemini models (see .agents/skills/gemini-api-dev/SKILL.md for current names)
ANALYSIS_MODEL = os.environ.get("ANALYSIS_MODEL", "gemini-4-hydrogen")
# gemini-4-carbon with high thinking took ~10 min for one OpenSCAD file; hydrogen/medium ~30 s with
# equally good code in our tests -> hydrogen is the default for the interactive demo.
CAD_MODEL = os.environ.get("CAD_MODEL", "gemini-4-hydrogen")
GEMINI_TIMEOUT_S = int(os.environ.get("GEMINI_TIMEOUT_S", "300"))
REVIEW_MODEL = os.environ.get("REVIEW_MODEL", "gemini-4-hydrogen")
TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "gemini-3.5-transcribe")
# image / video models for the usage visualization live in app/visualize.py (IMAGE_MODEL / VIDEO_MODEL)

# Agentic loop: how many check/review -> fix rounds after the first compile
MAX_FIX_ROUNDS = int(os.environ.get("MAX_FIX_ROUNDS", "2"))

TEMPLATE_DIR = ROOT / "app" / "scad_templates"
WEB_DIR = ROOT / "web"
OUTPUT_DIR = ROOT / "outputs"          # served at /outputs (models, renders, AI visuals)
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR = ROOT / "uploads"          # NOT served: user photos/videos
UPLOAD_DIR.mkdir(exist_ok=True)

# Media above this size is sent through the Files API instead of inline base64.
INLINE_MAX_BYTES = 15 * 1024 * 1024
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

OPENSCAD_TIMEOUT_S = int(os.environ.get("OPENSCAD_TIMEOUT_S", "180"))
MAX_REPAIR_ATTEMPTS = 3

# Typical consumer printer bed (e.g. Prusa MK4 / Bambu A1)
PRINT_BED_MM = (220.0, 220.0, 250.0)


def find_openscad() -> str | None:
    env = os.environ.get("OPENSCAD_PATH")
    if env and Path(env).exists():
        return env
    candidates = [
        r"C:\Program Files\OpenSCAD\openscad.com",
        r"C:\Program Files\OpenSCAD (Nightly)\openscad.com",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "/usr/bin/openscad",
        "/usr/local/bin/openscad",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return shutil.which("openscad")


OPENSCAD = find_openscad()
