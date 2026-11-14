"""Thin wrapper around the Gemini Interactions API (google-genai >= 3.2)."""

import base64
import os
import re
import threading
import time
from pathlib import Path

from google import genai
from pydantic import BaseModel

from . import config
from .schemas import inline_schema

_client = None


def has_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


_client_lock = threading.Lock()


def client() -> genai.Client:
    """Shared client. Created once under a lock: concurrent jobs creating several clients made one of
    them close its HTTP connection pool ("Cannot send a request, as the client has been closed")."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client()  # reads GEMINI_API_KEY from the environment
    return _client


def media_part(path: Path, mime: str) -> tuple[dict, str | None]:
    """Return an input part for an image/video and, if uploaded, the Files API name (to delete later)."""
    kind = "video" if mime.startswith("video/") else "image"
    # short clips of a person's attempt: sample 4 fps (default is 1) so grip slips and tremor are visible
    extra = {"processing": {"type": "static", "fps": 4}} if kind == "video" else {}
    if path.stat().st_size <= config.INLINE_MAX_BYTES:
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return {"type": kind, "data": data, "mime_type": mime, **extra}, None
    f = client().files.upload(file=str(path), config={"mime_type": mime})
    deadline = time.time() + 300
    while not f.state or f.state.name != "ACTIVE":
        if f.state and f.state.name == "FAILED":
            raise RuntimeError(f"Gemini could not process {path.name}")
        if time.time() > deadline:
            raise RuntimeError("Timed out waiting for the uploaded video to be processed")
        time.sleep(3)
        f = client().files.get(name=f.name)
    return {"type": kind, "uri": f.uri, "mime_type": f.mime_type or mime, **extra}, f.name


def delete_files(names: list[str]) -> None:
    for n in names:
        try:
            client().files.delete(name=n)
        except Exception:
            pass


def text(t: str) -> dict:
    return {"type": "text", "text": t}


def image_file(path: Path) -> dict:
    return {"type": "image", "data": base64.b64encode(path.read_bytes()).decode("utf-8"), "mime_type": "image/png"}


_beta_client = None

LANG_CODES = {"de": ["de-DE"], "en": ["en-US"]}
AUDIO_MIME_FIX = {"audio/mp4": "audio/m4a", "audio/x-m4a": "audio/m4a", "audio/x-wav": "audio/wav",
                  "audio/wave": "audio/wav", "video/webm": "audio/webm"}


def transcribe(audio: bytes, mime: str, language: str = "de") -> str:
    """Speech-to-text for the voice input buttons (gemini-3.5-transcribe, v1beta)."""
    global _beta_client
    if _beta_client is None:
        _beta_client = genai.Client(http_options={"api_version": "v1beta"})
    mime = (mime or "audio/webm").split(";")[0].strip().lower()
    mime = AUDIO_MIME_FIX.get(mime, mime)
    interaction = _beta_client.interactions.create(
        model=config.TRANSCRIBE_MODEL,
        input=[{"type": "audio", "data": base64.b64encode(audio).decode("utf-8"), "mime_type": mime}],
        generation_config={"transcription_config": {"mode": "smart",
                                                    "language_codes": LANG_CODES.get(language, [])}},
    )
    return (interaction.output_text or "").strip()


def _parse_json(raw: str, schema: type[BaseModel]) -> BaseModel:
    raw = (raw or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.S)
    if m:
        raw = m.group(1)
    return schema.model_validate_json(raw)


def generate_json(model: str, parts: list[dict], schema: type[BaseModel], system: str,
                  thinking: str = "medium", retries: int = 2) -> BaseModel:
    """One structured-output call. Retries transient failures."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            interaction = client().interactions.create(
                model=model,
                input=parts,
                system_instruction=system,
                response_format={"type": "text", "mime_type": "application/json", "schema": inline_schema(schema)},
                generation_config={"thinking_level": thinking},
                store=False,  # do not keep personal images/videos on the server
                timeout=config.GEMINI_TIMEOUT_S,
            )
            status = getattr(interaction, "status", "completed")
            if status not in (None, "completed"):
                raise RuntimeError(f"Gemini returned status '{status}'")
            return _parse_json(interaction.output_text, schema)
        except Exception as e:  # noqa: BLE001 - surface the last error after retries
            last_err = e
            msg = str(e)
            transient = any(s in msg for s in ("429", "500", "502", "503", "504", "UNAVAILABLE", "RESOURCE_EXHAUSTED",
                                               "status 'incomplete'", "validation error", "Invalid JSON"))
            if attempt < retries and transient:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_err  # pragma: no cover
