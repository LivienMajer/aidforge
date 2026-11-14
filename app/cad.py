"""OpenSCAD wrapper: sanitize code, bake parameters, compile to STL, render previews, mesh stats."""

import re
import struct
import subprocess
import time
from pathlib import Path

from . import config


class CadError(Exception):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize(code: str) -> str:
    """Strip anything that could read files from disk (include/use/import/surface)."""
    code = re.sub(r"^\s*(include|use)\s*<[^>]*>\s*;?", "// (removed include/use)", code, flags=re.M)
    code = re.sub(r"\b(import|surface)\s*\([^;]*\)\s*;", "/* (removed file import) */;", code)
    return code


def strip_fences(code: str) -> str:
    m = re.search(r"```(?:openscad|scad)?\s*\n(.*?)```", code, flags=re.S)
    return m.group(1) if m else code


def fmt(v: float) -> str:
    v = float(v)
    return str(int(v)) if v.is_integer() else f"{v:.4g}"


def bake_params(code: str, params: list[dict]) -> str:
    """Rewrite top-level `name = value;` assignments with the chosen values."""
    for p in params:
        name = p["name"]
        if not NAME_RE.match(name):
            continue
        pattern = re.compile(rf"^(\s*{re.escape(name)}\s*=\s*)([^;]+)(;.*)$", flags=re.M)
        code, n = pattern.subn(lambda m: f"{m.group(1)}{fmt(p['value'])}{m.group(3)}", code, count=1)
        if n == 0:
            code = f"{name} = {fmt(p['value'])};\n" + code
    return code


def extract_top_level_params(code: str) -> list[dict]:
    """Fallback: read `name = number; // description` lines from the top of a file."""
    out = []
    for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*;\s*(?://\s*(.*))?$", code, flags=re.M):
        name, value, desc = m.group(1), float(m.group(2)), (m.group(3) or "").strip()
        if name.startswith("$"):
            continue
        out.append({"name": name, "value": value, "description": desc})
    return out


def _important_log_lines(log: str, limit: int = 25) -> str:
    lines = [l for l in log.splitlines() if re.search(r"ERROR|WARNING|error|Parser", l)]
    return "\n".join(lines[:limit]) or log[-2000:]


def compile_stl(scad_path: Path, stl_path: Path) -> dict:
    if not config.OPENSCAD:
        raise CadError("OpenSCAD not found. Install it or set OPENSCAD_PATH.")
    if stl_path.exists():
        stl_path.unlink()
    t0 = time.time()
    try:
        proc = subprocess.run(
            [config.OPENSCAD, "-o", str(stl_path), "--export-format=binstl", str(scad_path)],
            capture_output=True,
            text=True,
            timeout=config.OPENSCAD_TIMEOUT_S,
            cwd=str(scad_path.parent),
        )
    except subprocess.TimeoutExpired:
        raise CadError(f"OpenSCAD timed out after {config.OPENSCAD_TIMEOUT_S}s (geometry too complex - "
                       "avoid minkowski, reduce $fn and loop counts).")
    log = (proc.stdout or "") + (proc.stderr or "")
    empty = "top level object is empty" in log.lower()
    if proc.returncode != 0 or empty or not stl_path.exists() or stl_path.stat().st_size < 200:
        reason = "The top-level object is empty (nothing to export)." if empty else "OpenSCAD failed."
        raise CadError(f"{reason}\n{_important_log_lines(log)}", log)
    return {"seconds": round(time.time() - t0, 1), "warnings": _important_log_lines(log, 10) if "WARNING" in log else ""}


VIEWS = {
    "iso": "0,0,0,55,0,30,300",
    "back": "0,0,0,60,0,210,300",
    "top": "0,0,0,0,0,0,300",
    "front": "0,0,0,90,0,0,300",
}


def render_previews(stl_path: Path, views=("iso", "back", "top")) -> list[Path]:
    """Render PNGs of an STL (fast: imports the mesh, no CSG)."""
    out = []
    if not config.OPENSCAD:
        return out
    preview_scad = stl_path.with_name(stl_path.stem + "_preview.scad")
    preview_scad.write_text(f'color([0.27,0.52,0.85]) import("{stl_path.name}");\n', encoding="utf-8")
    for v in views:
        png = stl_path.with_name(f"{stl_path.stem}_{v}.png")
        try:
            subprocess.run(
                [config.OPENSCAD, "-o", str(png), "--imgsize=800,600", "--viewall", "--autocenter",
                 f"--camera={VIEWS[v]}", "--colorscheme=Tomorrow", str(preview_scad)],
                capture_output=True, text=True, timeout=60, cwd=str(stl_path.parent),
            )
        except subprocess.TimeoutExpired:
            continue
        if png.exists():
            out.append(png)
    return out


def mesh_stats(stl_path: Path) -> dict:
    """Bounding box, volume and rough weight from a binary STL."""
    data = stl_path.read_bytes()
    if len(data) < 84:
        return {}
    n = struct.unpack_from("<I", data, 80)[0]
    if 84 + n * 50 != len(data):  # not binary - give up gracefully
        return {"triangles": None}
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    vol = 0.0
    for tri in struct.iter_unpack("<12fH", data[84:84 + n * 50]):
        v1, v2, v3 = tri[3:6], tri[6:9], tri[9:12]
        for v in (v1, v2, v3):
            for i in range(3):
                if v[i] < mins[i]:
                    mins[i] = v[i]
                if v[i] > maxs[i]:
                    maxs[i] = v[i]
        vol += (v1[0] * (v2[1] * v3[2] - v2[2] * v3[1])
                - v1[1] * (v2[0] * v3[2] - v2[2] * v3[0])
                + v1[2] * (v2[0] * v3[1] - v2[1] * v3[0])) / 6.0
    size = [round(maxs[i] - mins[i], 1) for i in range(3)]
    vol_cm3 = abs(vol) / 1000.0
    bed = config.PRINT_BED_MM
    fits = all(s <= b for s, b in zip(sorted(size), sorted(bed)))
    return {
        "triangles": n,
        "size_mm": size,
        "volume_cm3": round(vol_cm3, 1),
        # PLA ~1.24 g/cm3; small parts at ~20% infill end up roughly 40-60% of solid weight
        "weight_solid_g": round(vol_cm3 * 1.24, 1),
        "weight_estimate_g": round(vol_cm3 * 1.24 * 0.5, 1),
        "fits_bed": fits,
        "bed_mm": list(bed),
    }
