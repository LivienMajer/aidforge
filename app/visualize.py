"""AI "how it could look in real use" visualization.

1. Nano Banana (IMAGE_MODEL, default gemini-nano-banana-2.1) edits the user's photo - or invents a
   bright home scene - so the person's hand uses the 3D-printed device  -> start frame.
2. Nano Banana derives the end frame from that start frame ("same scene, same camera, a few seconds
   later"), which keeps person, scene, camera and device consistent      -> end frame.
3. Gemini Omni (VIDEO_MODEL, default gemini-omni-1.2-flash) interpolates start -> end frame into a
   short clip, with the device render as an extra reference so the part keeps its shape -> usage.mp4.

Everything goes through the Interactions API (google-genai >= 3.2). Images for Nano Banana are sent
inline as base64 (very large photos via the Files API); Omni inputs are uploaded to the Files API and
deleted again afterwards (best effort). Errors surface as RuntimeError with a short, key-free message.

Public API: make_frames(), make_video(), run_visualization().
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

from google import genai
from google.genai import errors, types

from . import config  # noqa: F401  (imported first: loads .env so the env overrides below apply)
from .gemini import client as _shared_client

log = logging.getLogger(__name__)

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-nano-banana-2.1")
VIDEO_MODEL = os.environ.get("VIDEO_MODEL", "gemini-omni-1.2-flash")

IMAGE_SIZES = ("512", "1K", "2K", "4K")  # SDK literal; must be uppercase
IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "1K").strip().upper()
if IMAGE_SIZE not in IMAGE_SIZES:
    log.warning("visualize: IMAGE_SIZE=%r is not one of %s, using 1K", IMAGE_SIZE, IMAGE_SIZES)
    IMAGE_SIZE = "1K"
IMAGE_TIMEOUT_S = int(os.environ.get("IMAGE_TIMEOUT_S", "300"))  # per Nano Banana call
IMAGE_ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
                       "1:8", "8:1", "1:4", "4:1")  # ImageResponseFormatAspectRatio in the SDK

VIDEO_FILE = "usage.mp4"
VIDEO_MIN_S, VIDEO_MAX_S = 3, 10  # first+last-frame transitions support 3-10 s
VIDEO_RESOLUTIONS = ("360p", "720p", "1080p", "4k")
VIDEO_ASPECT_RATIOS = ("16:9", "9:16")

INLINE_IMAGE_MAX_BYTES = 7 * 1024 * 1024  # bigger images go through the Files API
FILE_ACTIVE_TIMEOUT_S = 180
FILE_POLL_S = 1.5
FRAME_EXTS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}

ProgressFn = Optional[Callable[[str, str], None]]

__all__ = ["make_frames", "make_video", "run_visualization", "IMAGE_MODEL", "VIDEO_MODEL", "VIDEO_FILE"]


# --------------------------------------------------------------------------
# prompts (English, tuned for photorealism / identical device / respectful depiction)
# --------------------------------------------------------------------------

_DEVICE_SPEC = (
    "The device is the exact part shown in the CAD render: reproduce its silhouette, proportions, thickness, "
    "holes, slots and edges faithfully. Do not redesign, simplify, add or remove any feature. The render's "
    "colour, flat shading and plain background are not part of the device: the real part is 3D-printed in "
    "matte orange PLA with very fine horizontal layer lines and slightly softened edges, at a realistic size "
    "relative to the hand."
)

_QUALITY = (
    "Photorealistic, like an unedited photo from a good smartphone: natural light, true-to-life skin texture, "
    "correct shadows and contact points, sharp focus on the hand and the device. Anatomically correct, relaxed "
    "and natural hand pose with five fingers and a believable grip; the device is clearly visible and not "
    "hidden behind the fingers. No text, labels, logos, watermarks, arrows, split screens or overlays."
)

_RESPECT = (
    "Depict the person with dignity and authenticity, as a capable person doing an everyday task: do not "
    "exaggerate, dramatize or caricature any impairment, no pity framing, and no hospital, clinic or medical "
    "equipment unless it is already part of the scene or the description."
)

_DEFAULT_START = "The person is about to use the device for its everyday purpose."
_DEFAULT_END = "The person has calmly completed the everyday task with the help of the device."
_DEFAULT_MOTION = ("The person calmly uses the device to complete the everyday task, moving from the starting "
                   "pose to the final pose.")


def _clean(text: str | None, fallback: str, limit: int = 1500) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return (t or fallback)[:limit]


def _start_prompt(start_prompt: str, with_photo: bool) -> str:
    action = _clean(start_prompt, _DEFAULT_START)
    if with_photo:
        return "\n".join([
            "Edit the first image, a real photo, so that the person's hand is using the 3D-printed assistive "
            "device shown in the second image.",
            f"What happens: {action}",
            _DEVICE_SPEC,
            "Keep everything else exactly as in the photo: the same person (face, body, skin tone, hair, "
            "clothing), the same environment and objects, the same lighting and the same camera position, "
            "angle, lens and framing. Change only what is needed so that the hand holds or uses the device. "
            "If no person is visible, add a realistic hand and forearm entering the frame to use the device, "
            "matching the photo's light. If the output aspect ratio differs from the photo, extend the "
            "surroundings naturally instead of stretching, squashing or cropping the person.",
            _QUALITY,
            _RESPECT,
        ])
    return "\n".join([
        "Create a photorealistic photo of a person's hand using the 3D-printed assistive device shown in the image.",
        f"What happens: {action}",
        _DEVICE_SPEC,
        "Setting: a bright, realistic, lived-in home (for example a kitchen or living room) with soft natural "
        "daylight, unless the description above names another everyday place. Camera: static, at hand height, "
        "medium close-up, so the hand, the device and the object it is used with fill the centre of the frame; "
        "the face may be out of frame.",
        _QUALITY,
        _RESPECT,
    ])


def _end_prompt(end_prompt: str) -> str:
    return "\n".join([
        "The first image is the opening frame of a short, continuous video shot with a static camera. Create the "
        "frame of the same shot a few seconds later.",
        f"Same scene, same camera, a few seconds later: {_clean(end_prompt, _DEFAULT_END)}",
        "Keep the camera position, angle, lens and framing, the lighting, the person, their clothing and the "
        "background identical. Only the hand, the device and the objects being used may move, as a natural "
        "result of the action.",
        "The 3D-printed device must stay identical to the first image: same shape, size, matte orange PLA colour "
        "and the same way it is held or attached. The second image is a CAD render of that exact part, for its "
        "shape only (ignore the render's colour and background). Do not redesign it.",
        _QUALITY,
        _RESPECT,
    ])


def _video_prompt(motion_prompt: str) -> str:
    return "\n".join([
        "Use the first image as the starting frame and the second image as the final frame. The third image "
        "shows the 3D-printed device; keep its shape identical. It is printed in matte orange PLA, so ignore the "
        "render's colour and background.",
        "A single continuous shot with a static, locked-off camera: no cuts, no zoom, no pan, no camera shake.",
        f"Action: {_clean(motion_prompt, _DEFAULT_MOTION)}",
        "The person moves naturally and smoothly at real-time speed with anatomically correct hands. The device "
        "stays rigid and keeps exactly the same shape, size and colour in every frame; it never morphs, bends, "
        "duplicates or disappears, and stays in believable contact with the hand.",
        "Photorealistic, natural lighting consistent with both frames. Depict the person with dignity as a capable "
        "person; do not exaggerate any impairment.",
        "Audio: quiet natural room ambience and the soft sounds of the action only. No music, no dialogue, no "
        "voice-over, no on-screen text, no embellishments.",
    ])


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _notify(on_progress: ProgressFn, stage: str, detail: str) -> None:
    if on_progress is None:
        return
    try:
        on_progress(stage, detail)
    except Exception:  # noqa: BLE001 - a broken progress callback must not kill the job
        log.exception("visualize: on_progress callback failed")


def _status_code(err: Any) -> int | None:
    """HTTP status of an SDK error: google.genai.errors.APIError (.code) or interactions APIError (.status_code)."""
    for attr in ("code", "status_code"):
        v = getattr(err, attr, None)
        if isinstance(v, int):
            return v
    return None


def _sanitize(err: Any) -> str:
    """Short, key-free error text (adapted from the Omni skill's sanitize_error)."""
    if isinstance(err, errors.APIError):  # Files API / classic client errors
        bits = [str(err.code)] if getattr(err, "code", None) else []
        if getattr(err, "status", None):
            bits.append(f"({err.status})")
        if getattr(err, "message", None):
            bits.append(f": {err.message}")
        s = " ".join(bits) or str(err)
    elif isinstance(getattr(err, "body", None), dict) or hasattr(err, "status_code"):
        # Interactions API errors (google.genai._gaos compat APIError): prefer body.error.message
        body = getattr(err, "body", None)
        e = body.get("error") if isinstance(body, dict) else None
        msg = (e.get("message") if isinstance(e, dict) else None) or getattr(err, "message", None) or str(err)
        status = (e.get("status") if isinstance(e, dict) else None) or ""
        code = _status_code(err)
        s = " ".join(x for x in (str(code) if code else "", f"({status})" if status else "") if x)
        s = f"{s}: {msg}" if s else str(msg)
    elif isinstance(err, BaseException) and not isinstance(err, RuntimeError):
        s = f"{type(err).__name__}: {err}"
    else:
        s = str(err)
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.environ.get(var)
        if key and len(key) >= 8:
            s = s.replace(key, "[REDACTED_KEY]")
    s = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[REDACTED_KEY]", s)
    s = re.sub(r"AQ\.[0-9A-Za-z_\-]{20,}", "[REDACTED_KEY]", s)
    s = re.sub(r"ya29\.[0-9A-Za-z_\-]+", "[REDACTED_TOKEN]", s)
    s = re.sub(r"Bearer\s+[A-Za-z0-9_\-.]+", "Bearer [REDACTED_TOKEN]", s, flags=re.I)
    s = re.sub(r"([?&](?:key|api_key|apiKey|access_token|auth|signature)=)[^&\s\"'<>()]+", r"\1[REDACTED]", s)
    s = re.sub(r"https?://[a-zA-Z0-9.\-_]*\.corp\.goog[^\s\"'<>)]*", "[INTERNAL_HOST]", s)
    s = re.sub(r"https?://[a-zA-Z0-9.\-_]*\.sandbox\.googleapis\.com[^\s\"'<>)]*", "[SANDBOX_ENDPOINT]", s)
    s = re.sub(r"\bbody\s*=.*\Z", "body=[REDACTED_BODY]", s, flags=re.I | re.S)
    if "<html" in s.lower() or "<!doctype" in s.lower():
        m = re.search(r"<title>(.*?)</title>", s, re.I | re.S)
        s = f"HTTP error page: {m.group(1).strip()}" if m else re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= 300 else s[:297] + "..."


_TRANSIENT_CODES = {429, 500, 502, 503, 504}
_TRANSIENT_TOKENS = ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "Server disconnected", "Connection reset")


def _is_transient(err: Exception) -> bool:
    code = _status_code(err)
    if code is not None:
        return code in _TRANSIENT_CODES
    names = {c.__name__ for c in type(err).__mro__}
    if "APITimeoutError" in names or "TimeoutException" in names:
        return False  # a client-side timeout already waited the full budget: do not wait again
    if "APIConnectionError" in names:
        return True
    msg = str(err)
    return any(t in msg for t in _TRANSIENT_TOKENS)


def _has_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def _image_client():
    """The app-wide shared client (app.gemini.client)."""
    if not _has_key():
        raise RuntimeError("GEMINI_API_KEY is not set - add it to .env to enable the AI visualization")
    try:
        return _shared_client()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Could not create the Gemini client: {_sanitize(e)}") from None


def _video_client(timeout_s: int):
    """Separate client with a long per-request timeout (Omni calls block for minutes)."""
    if not _has_key():
        raise RuntimeError("GEMINI_API_KEY is not set - add it to .env to enable the AI visualization")
    try:
        return genai.Client(http_options=types.HttpOptions(timeout=int(timeout_s) * 1000))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Could not create the Gemini video client: {_sanitize(e)}") from None


def _create(cl, what: str, retries: int, **kwargs):
    """interactions.create with a small retry on transient errors; errors -> sanitized RuntimeError."""
    for attempt in range(retries + 1):
        try:
            return cl.interactions.create(**kwargs)
        except Exception as e:  # noqa: BLE001
            if attempt < retries and _is_transient(e):
                log.warning("visualize: %s attempt %d failed (%s), retrying", what, attempt + 1, _sanitize(e))
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"{what} failed: {_sanitize(e)}") from None
    raise RuntimeError(f"{what} failed")  # pragma: no cover


def _sniff_mime(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"heim", b"heis", b"hevc"):
            return "image/heic"
        if brand in (b"mif1", b"msf1", b"heif"):
            return "image/heif"
        return "video/mp4"  # mp4 / mov family
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


def _image_mime(path: Path) -> str:
    with open(path, "rb") as fh:
        head = fh.read(16)
    mime = _sniff_mime(head) or mimetypes.guess_type(path.name)[0]
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"{path.name} is not a supported image ({mime or 'unknown type'}); "
                         "pass a still photo (PNG/JPEG/WebP), e.g. a frame grabbed from the video")
    return mime


def _require_file(p: Path, label: str) -> Path:
    p = Path(p)
    if not p.is_file():
        raise FileNotFoundError(f"{label} not found: {p}")
    return p


def _state(f) -> str:
    s = getattr(f, "state", None)
    if s is None:
        return ""
    name = getattr(s, "name", None) or str(s)
    return str(name).rsplit(".", 1)[-1].upper()


def _file_uri(f) -> str:
    """Files API URI as the Omni skill's proven script passes it: query stripped, version-less
    https://generativelanguage.googleapis.com/files/<id> (falls back to the raw uri)."""
    uri = getattr(f, "uri", None) or ""
    m = re.search(r"files/([A-Za-z0-9_-]+)", uri) or re.search(r"^files/([A-Za-z0-9_-]+)", getattr(f, "name", None) or "")
    if m:
        return f"https://generativelanguage.googleapis.com/files/{m.group(1)}"
    if not uri:
        raise RuntimeError("The Files API returned no URI for the upload")
    return urllib.parse.urlunparse(urllib.parse.urlparse(uri)._replace(query=""))


def _upload(cl, path: Path, mime: str, uploaded: list[str]):
    """Upload to the Files API, record the name for cleanup, poll until ACTIVE."""
    try:
        f = cl.files.upload(file=str(path), config={"mime_type": mime, "display_name": path.name})
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Uploading {path.name} failed: {_sanitize(e)}") from None
    if getattr(f, "name", None):
        uploaded.append(f.name)
    deadline = time.monotonic() + FILE_ACTIVE_TIMEOUT_S
    while _state(f) != "ACTIVE":
        if _state(f) == "FAILED":
            raise RuntimeError(f"Gemini could not process the uploaded {path.name}")
        if time.monotonic() > deadline:
            raise RuntimeError(f"Timed out waiting for the uploaded {path.name} to become ACTIVE")
        time.sleep(FILE_POLL_S)
        try:
            f = cl.files.get(name=f.name)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Checking the upload of {path.name} failed: {_sanitize(e)}") from None
    return f


def _uploaded_part(cl, path: Path, mime: str, uploaded: list[str]) -> dict:
    f = _upload(cl, path, mime, uploaded)
    return {"type": "image", "uri": _file_uri(f), "mime_type": getattr(f, "mime_type", None) or mime}


def _delete_files(cl, names: list[str]) -> None:
    for n in names:
        try:
            cl.files.delete(name=n)
        except Exception as e:  # noqa: BLE001 - best effort
            log.warning("visualize: could not delete uploaded file %s: %s", n, _sanitize(e))


def _download(cl, uri: str, what: str) -> bytes:
    try:
        data = cl.files.download(file=uri)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Downloading the {what} failed: {_sanitize(e)}") from None
    if not data:
        raise RuntimeError(f"Downloading the {what} returned no data")
    return bytes(data)


def _output(interaction, kind: str):
    """interaction.output_<kind> (SDK helper), falling back to scanning the trailing model_output steps."""
    item = getattr(interaction, f"output_{kind}", None)
    if item is not None:
        return item
    for step in reversed(getattr(interaction, "steps", None) or []):
        stype = getattr(step, "type", None)
        if stype == "user_input":
            break
        if stype != "model_output":
            continue
        for c in reversed(getattr(step, "content", None) or []):
            if getattr(c, "type", None) == kind:
                return c
    return None


def _explain(interaction) -> str:
    bits = []
    status = getattr(interaction, "status", None)
    if status and status != "completed":
        bits.append(f"status '{status}'")
    errs = getattr(interaction, "errors", None) or []
    if errs:
        bits.append(_sanitize(getattr(errs[0], "message", None) or errs[0])[:150])
    text = (getattr(interaction, "output_text", None) or "").strip()
    if text:
        bits.append(f"model said: {_sanitize(text)[:200]}")
    return f" ({'; '.join(bits)})" if bits else ""


def _image_part(cl, path: Path, uploaded: list[str]) -> dict:
    mime = _image_mime(path)
    if path.stat().st_size <= INLINE_IMAGE_MAX_BYTES:
        return {"type": "image", "data": base64.b64encode(path.read_bytes()).decode("ascii"), "mime_type": mime}
    return _uploaded_part(cl, path, mime, uploaded)


def _generate_image(cl, what: str, parts: list[dict], aspect_ratio: str) -> tuple[bytes, str]:
    """One Nano Banana call -> (image bytes, mime). Retries once if the model answers without an image."""
    response_format = {"type": "image", "aspect_ratio": aspect_ratio, "image_size": IMAGE_SIZE}
    interaction = None
    for _attempt in range(2):
        interaction = _create(cl, what, retries=2, model=IMAGE_MODEL, input=parts,
                              response_format=response_format,
                              store=False,  # do not keep personal photos on the server
                              timeout=IMAGE_TIMEOUT_S)
        img = _output(interaction, "image")
        if img is not None and getattr(img, "data", None):
            try:
                data = base64.b64decode(img.data)
            except (ValueError, TypeError):
                data = b""
        elif img is not None and getattr(img, "uri", None):
            data = _download(cl, img.uri, f"{what} image")
        else:
            log.warning("visualize: %s returned no image%s", what, _explain(interaction))
            continue
        if not data:
            continue
        mime = (getattr(img, "mime_type", None) or _sniff_mime(data[:16]) or "image/png").lower()
        return data, mime
    raise RuntimeError(f"{what}: the image model returned no image{_explain(interaction)}")


def _save_frame(out_dir: Path, stem: str, data: bytes, mime: str) -> Path:
    if mime not in FRAME_EXTS:  # trust the bytes over an unexpected label
        mime = _sniff_mime(data[:16]) or "image/png"
    target = out_dir / f"{stem}{FRAME_EXTS.get(mime, '.png')}"
    for ext in set(FRAME_EXTS.values()):  # drop a stale frame of another type from an earlier run
        old = out_dir / f"{stem}{ext}"
        if old != target and old.exists():
            try:
                old.unlink()
            except OSError:
                pass
    target.write_bytes(data)
    return target


def _clamp_duration(duration_s) -> int:
    try:
        d = int(round(float(duration_s)))
    except (TypeError, ValueError):
        d = 8
    return max(VIDEO_MIN_S, min(VIDEO_MAX_S, d))


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def make_frames(out_dir: Path, *, device_render: Path, photo: Path | None, start_prompt: str, end_prompt: str,
                aspect_ratio: str = "16:9", on_progress=None) -> dict:
    """Generate the start and end frame with Nano Banana.

    Returns {"start": Path, "end": Path} (start_frame.<ext> / end_frame.<ext> in out_dir, ext from the
    returned mime type: .png / .jpg / .webp). Raises RuntimeError (sanitized) on API failures,
    FileNotFoundError / ValueError on bad inputs.
    """
    out_dir = Path(out_dir)
    device_render = _require_file(device_render, "Device render")
    photo = _require_file(photo, "Photo") if photo else None
    if aspect_ratio not in IMAGE_ASPECT_RATIOS:
        raise ValueError(f"Unsupported image aspect ratio '{aspect_ratio}' (use one of {', '.join(IMAGE_ASPECT_RATIOS)})")
    out_dir.mkdir(parents=True, exist_ok=True)

    cl = _image_client()
    uploaded: list[str] = []
    try:
        render_part = _image_part(cl, device_render, uploaded)

        # 1) start frame: edit the user's photo (or invent a home scene) so the hand uses the device
        _notify(on_progress, "frames", "Generating start frame" + (" from your photo" if photo else ""))
        if photo:
            parts = [{"type": "text", "text": _start_prompt(start_prompt, with_photo=True)},
                     _image_part(cl, photo, uploaded), render_part]
        else:
            parts = [{"type": "text", "text": _start_prompt(start_prompt, with_photo=False)}, render_part]
        data, mime = _generate_image(cl, "Start frame generation", parts, aspect_ratio)
        start = _save_frame(out_dir, "start_frame", data, mime)

        # 2) end frame: derived from the start frame (+ render) so both stay consistent
        _notify(on_progress, "frames", "Generating end frame")
        start_part = {"type": "image", "data": base64.b64encode(data).decode("ascii"), "mime_type": _image_mime(start)}
        parts = [{"type": "text", "text": _end_prompt(end_prompt)}, start_part, render_part]
        data, mime = _generate_image(cl, "End frame generation", parts, aspect_ratio)
        end = _save_frame(out_dir, "end_frame", data, mime)
    finally:
        _delete_files(cl, uploaded)
    return {"start": start, "end": end}


def make_video(out_dir: Path, *, start_frame: Path, end_frame: Path, device_render: Path, motion_prompt: str,
               duration_s: int = 8, resolution: str = "720p", aspect_ratio: str = "16:9", timeout_s: int = 600,
               on_progress=None) -> Path:
    """First+last-frame transition with Gemini Omni; returns out_dir / "usage.mp4".

    duration_s is clamped to 3..10 s. The three input images are uploaded to the Files API and deleted
    afterwards (best effort, also on failure). timeout_s is the per-request HTTP timeout of the video client.
    """
    out_dir = Path(out_dir)
    images = [_require_file(start_frame, "Start frame"), _require_file(end_frame, "End frame"),
              _require_file(device_render, "Device render")]
    duration = _clamp_duration(duration_s)
    resolution = str(resolution or "720p").strip().lower()
    if resolution not in VIDEO_RESOLUTIONS:
        raise ValueError(f"Unsupported video resolution '{resolution}' (use one of {', '.join(VIDEO_RESOLUTIONS)})")
    if aspect_ratio not in VIDEO_ASPECT_RATIOS:
        raise ValueError(f"Unsupported video aspect ratio '{aspect_ratio}' (use 16:9 or 9:16)")
    timeout_s = int(timeout_s)
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    out_dir.mkdir(parents=True, exist_ok=True)

    cl = _video_client(timeout_s)
    uploaded: list[str] = []
    try:
        # Omni binds media by order: first frame, last frame, reference image(s), then the text.
        _notify(on_progress, "upload", "Uploading start frame, end frame and device render")
        parts: list[dict] = []
        cache: dict[Path, dict] = {}
        for p in images:
            key = p.resolve()
            if key not in cache:  # same file twice (e.g. a loop) -> upload once
                cache[key] = _uploaded_part(cl, p, _image_mime(p), uploaded)
            parts.append(dict(cache[key]))
        parts.append({"type": "text", "text": _video_prompt(motion_prompt)})
        response_format = {"type": "video", "delivery": "uri", "aspect_ratio": aspect_ratio,
                           "duration": f"{duration}s", "resolution": resolution}

        _notify(on_progress, "video", f"Generating a {duration} s {resolution} clip with {VIDEO_MODEL} "
                                      "(this can take a few minutes)")
        t0 = time.monotonic()
        interaction = _create(cl, "Video generation", retries=1, model=VIDEO_MODEL, input=parts,
                              response_format=response_format)
        log.info("visualize: video interaction %s finished in %.0fs", getattr(interaction, "id", "?"),
                 time.monotonic() - t0)
        video = _output(interaction, "video")
        if video is None or not (getattr(video, "uri", None) or getattr(video, "data", None)):
            # (The EEA/UK/CH restriction only concerns *video inputs*; we only send images.)
            raise RuntimeError(f"The video model returned no video{_explain(interaction)}. "
                               "Try again or simplify the motion description.")

        _notify(on_progress, "download", "Downloading the generated video")
        if getattr(video, "uri", None):
            data = _download(cl, video.uri, "generated video")
        else:
            data = base64.b64decode(video.data)
        target = out_dir / VIDEO_FILE
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        return target
    finally:
        _delete_files(cl, uploaded)


def run_visualization(out_dir: Path, *, device_render: Path, photo: Path | None, start_prompt: str,
                      end_prompt: str, motion_prompt: str, with_video: bool = True, on_progress=None) -> dict:
    """Frames, then (optionally) the transition video. Returns {"start", "end", "video" (Path or None)}."""
    frames = make_frames(out_dir, device_render=device_render, photo=photo, start_prompt=start_prompt,
                         end_prompt=end_prompt, on_progress=on_progress)
    video = None
    if with_video:
        video = make_video(out_dir, start_frame=frames["start"], end_frame=frames["end"],
                           device_render=device_render, motion_prompt=motion_prompt, on_progress=on_progress)
    return {"start": frames["start"], "end": frames["end"], "video": video}
