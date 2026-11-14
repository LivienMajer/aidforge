"""Generation pipeline: media + impairment + activity -> plan -> OpenSCAD -> STL -> checks/review loop.

Every compiled version is kept as an "iteration" (v1 -> critique -> v2 ...), so the agentic loop is
visible in the UI. Jobs run in background threads, live in memory and are persisted to
outputs/<id>/job.json so results survive a server restart (demo safety net).
"""

import json
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import cad, config, gemini, prompts
from . import measure  # --- precise-measurement ---
from .schemas import CadDesign, DesignPlan, RefineParams, Review
from .templates_registry import BY_ID, resolve_params

try:  # deterministic printability checks (numpy); optional so the app still runs without it
    from . import checks as checks_mod
except Exception:  # noqa: BLE001
    checks_mod = None

JOBS: dict[str, "Job"] = {}
GENERATE_STEPS = ("analyze", "design", "compile", "improve")


def _rel_url(p: Path | None) -> str | None:
    if not p:
        return None
    try:
        return "/outputs/" + p.resolve().relative_to(config.OUTPUT_DIR.resolve()).as_posix()
    except ValueError:
        return None


class Job:
    def __init__(self, language: str = "de", review: bool = True, steps=GENERATE_STEPS, job_id: str | None = None):
        self.id = job_id or uuid.uuid4().hex[:10]
        self.dir = config.OUTPUT_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir = config.UPLOAD_DIR / self.id
        self.created = time.time()
        self.language = language
        self.review_enabled = review
        self.inputs: dict = {}
        self.status = "queued"
        self.error: str | None = None
        self.steps = [{"key": k, "status": "pending", "detail": ""} for k in steps]
        self.plan: DesignPlan | None = None
        self.approach = ""
        self.template_id = ""
        self.source_code = ""
        self.params: list[dict] = []
        self.version = 0
        self.stl: Path | None = None
        self.scad: Path | None = None
        self.stats: dict = {}
        self.checks: dict | None = None
        self.compile_info: dict = {}
        self.previews: list[Path] = []
        self.review: dict | None = None
        self.design_notes = ""
        self.iterations: list[dict] = []
        self.visual: dict = {"status": "idle"}
        self.visual_photo: Path | None = None
        self.lock = threading.Lock()
        JOBS[self.id] = self

    # ---- progress -------------------------------------------------------
    def reset_steps(self, keys):
        self.steps = [{"key": k, "status": "pending", "detail": ""} for k in keys]

    def step(self, key: str, status: str, detail: str = ""):
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
                if detail or status in ("running", "done"):
                    s["detail"] = detail

    def fail_running_step(self, msg: str):
        for s in self.steps:
            if s["status"] == "running":
                s["status"] = "error"
                s["detail"] = msg[:300]

    @property
    def current_iteration(self) -> dict | None:
        for it in reversed(self.iterations):
            if it.get("version") == self.version:
                return it
        return None

    # ---- serialisation --------------------------------------------------
    def to_dict(self) -> dict:
        t = BY_ID.get(self.template_id)
        return {
            "id": self.id,
            "created": self.created,
            "status": self.status,
            "error": self.error,
            "steps": self.steps,
            "language": self.language,
            "inputs": self.inputs,
            "plan": self.plan.model_dump() if self.plan else None,
            "approach": self.approach,
            "template_id": self.template_id,
            "template_name": t.name if t else None,
            "params": self.params,
            "code": self.scad.read_text(encoding="utf-8") if self.scad and self.scad.exists() else "",
            "design_notes": self.design_notes,
            "version": self.version,
            "stl_url": _rel_url(self.stl),
            "scad_url": _rel_url(self.scad),
            "preview_urls": [_rel_url(p) for p in self.previews],
            "stats": self.stats,
            "checks": self.checks,
            "compile": self.compile_info,
            "review": self.review,
            "iterations": self.iterations,
            "visual": self.visual,
            "has_photo": bool(self.visual_photo and self.visual_photo.exists()),
        }

    def save(self) -> None:
        data = self.to_dict()
        data["_internal"] = {
            "source_code": self.source_code,
            "review_enabled": self.review_enabled,
            "stl": self.stl.name if self.stl else None,
            "scad": self.scad.name if self.scad else None,
            "previews": [p.name for p in self.previews],
            "visual_photo": str(self.visual_photo) if self.visual_photo else None,
        }
        tmp = self.dir / "job.json.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.dir / "job.json")

    @classmethod
    def load(cls, path: Path) -> "Job":
        data = json.loads(path.read_text(encoding="utf-8"))
        internal = data.get("_internal", {})
        job = cls(language=data.get("language", "de"), review=internal.get("review_enabled", True),
                  job_id=data["id"])
        job.created = data.get("created", path.stat().st_mtime)
        job.status = data.get("status", "done")
        if job.status in ("running", "queued"):
            job.status, job.error = "error", "Server restarted while this job was running."
        job.error = job.error or data.get("error")
        job.steps = data.get("steps", [])
        job.inputs = data.get("inputs", {})
        job.plan = DesignPlan.model_validate(data["plan"]) if data.get("plan") else None
        job.approach = data.get("approach", "")
        job.template_id = data.get("template_id", "")
        job.source_code = internal.get("source_code", "")
        job.params = data.get("params", [])
        job.version = data.get("version", 0)
        job.stl = job.dir / internal["stl"] if internal.get("stl") else None
        job.scad = job.dir / internal["scad"] if internal.get("scad") else None
        job.previews = [job.dir / n for n in internal.get("previews", [])]
        job.stats = data.get("stats", {})
        job.checks = data.get("checks")
        job.compile_info = data.get("compile", {})
        job.review = data.get("review")
        job.design_notes = data.get("design_notes", "")
        job.iterations = data.get("iterations", [])
        job.visual = data.get("visual") or {"status": "idle"}
        if job.visual.get("status") == "running":
            job.visual = {"status": "error", "error": "Server restarted during generation."}
        vp = internal.get("visual_photo")
        job.visual_photo = Path(vp) if vp and Path(vp).exists() else None
        return job


def load_saved_jobs() -> int:
    n = 0
    for f in sorted(config.OUTPUT_DIR.glob("*/job.json")):
        if f.parent.name in JOBS:
            continue
        try:
            Job.load(f)
            n += 1
        except Exception:  # noqa: BLE001 - a broken file should not stop the server
            traceback.print_exc()
    return n


def job_summary(job: Job) -> dict:
    it = job.current_iteration or {}
    return {
        "id": job.id,
        "created": job.created,
        "status": job.status,
        "version": job.version,
        "device_name": job.plan.device_name if job.plan else (BY_ID[job.template_id].name if job.template_id in BY_ID else ""),
        "activity": job.inputs.get("activity", ""),
        "approach": job.approach,
        "preview_url": it.get("preview_url"),
        "has_video": bool(job.visual.get("video_url")),
    }


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _guess_step(lo: float, hi: float) -> float:
    span = abs(hi - lo)
    return 1 if span >= 20 else 0.5 if span >= 4 else 0.1


def _custom_params(design: CadDesign) -> list[dict]:
    out = []
    for p in design.parameters:
        if not cad.NAME_RE.match(p.name):
            continue
        lo, hi = min(p.min, p.max), max(p.min, p.max)
        lo, hi = min(lo, p.value), max(hi, p.value)
        out.append({"name": p.name, "value": p.value, "min": lo, "max": hi,
                    "step": _guess_step(lo, hi), "description": p.description})
    return out


def _apply_changes(job: Job, changes: dict[str, float]) -> list[dict]:
    if job.approach == "template":
        current = {p["name"]: p["value"] for p in job.params}
        current.update(changes)
        return resolve_params(job.template_id, current)
    out = []
    for p in job.params:
        q = dict(p)
        if p["name"] in changes:
            q["value"] = max(p["min"], min(p["max"], float(changes[p["name"]])))
        out.append(q)
    return out


def _param_diff(old: list[dict], new: list[dict]) -> dict:
    o = {p["name"]: p["value"] for p in old}
    return {p["name"]: [o.get(p["name"]), p["value"]] for p in new
            if p["name"] in o and abs(float(o[p["name"]]) - float(p["value"])) > 1e-9}


# ---- deterministic checks --------------------------------------------------

def _check(cid, en, de, status, value, detail_en, detail_de):
    return {"id": cid, "label_en": en, "label_de": de, "status": status, "value": value,
            "detail_en": detail_en, "detail_de": detail_de}


def fit_checks(job: Job) -> list[dict]:
    """Object fit: template size parameters must match the measured object (template adds tolerance)."""
    if not job.plan or not job.plan.fit_links:
        return []
    meas = {m.name.strip().lower(): m for m in job.plan.measurements}
    params = {p["name"]: float(p["value"]) for p in job.params}
    tol = params.get("tolerance", 0.0)
    out = []
    for link in job.plan.fit_links:
        m = meas.get(link.measurement_name.strip().lower())
        if not m or link.param_name not in params:
            continue
        p = params[link.param_name]
        diff = p - m.value_mm
        clearance = diff + 2 * tol
        value = f"{cad.fmt(p)} mm vs {cad.fmt(m.value_mm)} mm"
        if clearance < 0:
            status = "fail"
            en = f"{link.param_name} is {abs(diff):.1f} mm smaller than the measured {m.name}: it will not fit."
            de = f"{link.param_name} ist {abs(diff):.1f} mm kleiner als {m.name} - passt nicht."
        elif diff > max(2.0, 0.08 * m.value_mm):
            status = "warn"
            en = f"{link.param_name} is {diff:.1f} mm larger than the measured {m.name}: loose fit."
            de = f"{link.param_name} ist {diff:.1f} mm größer als {m.name} - sitzt locker."
        else:
            status = "pass"
            en = f"Matches the measured {m.name} (+{cad.fmt(2 * tol)} mm clearance from tolerance)."
            de = f"Passt zu {m.name} (+{cad.fmt(2 * tol)} mm Spiel durch Toleranz)."
        out.append(_check(f"fit:{link.param_name}", f"Fit: {m.name}", f"Passmaß: {m.name}", status, value, en, de))
    return out


def run_all_checks(job: Job) -> dict:
    t0 = time.time()
    if checks_mod is not None:
        try:
            res = checks_mod.run_checks(job.stl, bed_mm=config.PRINT_BED_MM)
        except Exception as e:  # noqa: BLE001
            res = {"passed": True, "checks": [_check("mesh", "Mesh checks", "Mesh-Prüfung", "warn", "-",
                                                     f"Mesh checks crashed: {e}", f"Mesh-Prüfung fehlgeschlagen: {e}")],
                   "feedback": ""}
    else:
        s = job.stats
        res = {"passed": bool(s.get("fits_bed", True)), "feedback": "", "checks": [
            _check("bed_fit", "Fits print bed", "Passt aufs Druckbett", "pass" if s.get("fits_bed") else "fail",
                   " x ".join(cad.fmt(v) for v in s.get("size_mm", [])), "", "")]}
    fits = fit_checks(job)
    res = dict(res)
    res["checks"] = list(res.get("checks", [])) + fits
    fit_fb = [c["detail_en"] for c in fits if c["status"] != "pass"]
    if fit_fb:
        res["feedback"] = (res.get("feedback", "") + "\nObject fit: " + " ".join(fit_fb)).strip()
    res["passed"] = all(c["status"] != "fail" for c in res["checks"])
    res["counts"] = {k: sum(1 for c in res["checks"] if c["status"] == k) for k in ("pass", "warn", "fail")}
    res["seconds"] = round(time.time() - t0, 2)
    return res


# ---- compile ---------------------------------------------------------------

def compile_version(job: Job, code: str, params: list[dict], source: str, note: str = "") -> None:
    """Bake params into code and compile; only on success it becomes the current version."""
    version = job.version + 1
    scad_path = job.dir / f"model_v{version}.scad"
    stl_path = job.dir / f"model_v{version}.stl"
    scad_path.write_text(cad.bake_params(code, params), encoding="utf-8")
    info = cad.compile_stl(scad_path, stl_path)
    old_params = job.params
    job.version = version
    job.source_code, job.params = code, params
    job.scad, job.stl = scad_path, stl_path
    job.compile_info = info
    job.stats = cad.mesh_stats(stl_path)
    job.previews = []
    job.review = None
    job.checks = run_all_checks(job)
    job.iterations.append({
        "version": version,
        "source": source,  # initial | repair | review_fix | checks_fix | refine | manual
        "note": note[:300],
        "stl_url": _rel_url(stl_path),
        "scad_url": _rel_url(scad_path),
        "preview_url": None,
        "size_mm": job.stats.get("size_mm"),
        "checks": job.checks.get("counts"),
        "checks_feedback": job.checks.get("feedback", "")[:600],
        "changed": _param_diff(old_params, params) if old_params else {},
        "critique": None,
        "issues": [],
        "verdict": None,
    })


def _record_failed_attempt(job: Job, err: Exception, note: str = "") -> None:
    first = next((l for l in str(err).splitlines() if l.strip()), str(err))
    job.iterations.append({"version": None, "source": "compile_error", "note": (note or first)[:300],
                           "error": first[:300]})


def compile_custom_with_repair(job: Job, design: CadDesign, source: str = "initial", note: str = "") -> None:
    code = cad.sanitize(cad.strip_fences(design.openscad_code))
    params = _custom_params(design) or [
        {**p, "min": min(0.0, p["value"]), "max": max(p["value"] * 2, 10.0), "step": 0.5}
        for p in cad.extract_top_level_params(code)
    ]
    job.design_notes = design.design_notes or job.design_notes
    for attempt in range(1, config.MAX_REPAIR_ATTEMPTS + 1):
        job.step("compile", "running", f"OpenSCAD attempt {attempt}")
        try:
            compile_version(job, code, params, source if attempt == 1 else "repair", note if attempt == 1 else "")
            return
        except cad.CadError as e:
            _record_failed_attempt(job, e)
            if attempt == config.MAX_REPAIR_ATTEMPTS:
                raise
            job.step("compile", "running", f"Gemini repairs compile error ({attempt}/{config.MAX_REPAIR_ATTEMPTS - 1})")
            fixed = gemini.generate_json(
                config.CAD_MODEL,
                [gemini.text(f"This OpenSCAD file failed to compile.\n\nERROR LOG:\n{e}\n\nCODE:\n{code}\n\n"
                             "Fix the problem and return the complete corrected file. Keep the parameter names.")],
                CadDesign, prompts.cad_system(), thinking="medium")
            code = cad.sanitize(cad.strip_fences(fixed.openscad_code))
            params = _custom_params(fixed) or params
            job.design_notes = fixed.design_notes or job.design_notes


# ---- prompts ---------------------------------------------------------------

def _user_brief(impairment: str, activity: str, notes: str, n_media: int) -> str:
    media = (f"{n_media} image/video file(s) are attached above." if n_media
             else "No media attached - rely on the text and typical dimensions.")
    return (f"{media}\n\nIMPAIRMENT / LIMITATION OF THE PERSON:\n{impairment.strip()}\n\n"
            f"ACTIVITY THE PERSON WANTS TO DO:\n{activity.strip()}\n\n"
            f"ADDITIONAL NOTES AND MEASUREMENTS (user-provided, authoritative):\n{notes.strip() or '(none)'}")


def _plan_for_cad(plan: DesignPlan) -> str:
    keep = {k: v for k, v in plan.model_dump().items() if k in (
        "device_name", "task_summary", "functional_limitations", "root_problem", "design_requirements",
        "measurements", "custom_design_brief", "how_it_helps", "print_settings")}
    return ("Model this assistive device in OpenSCAD. The values in `measurements` are authoritative: where "
            "custom_design_brief states a different size for the same dimension, use the measurement.\n\n"
            "DESIGN PLAN:\n" + json.dumps(keep, indent=2, ensure_ascii=False))


def _checks_for_prompt(job: Job) -> list[dict]:
    if not job.checks:
        return []
    return [{"check": c["label_en"], "status": c["status"], "value": c["value"], "detail": c["detail_en"]}
            for c in job.checks.get("checks", [])]


def _design_context(job: Job) -> str:
    ctx = {
        "approach": job.approach,
        "template_id": job.template_id,
        "parameters": [{k: p[k] for k in ("name", "value", "min", "max", "description")} for p in job.params],
        "mesh_bounding_box_mm": job.stats.get("size_mm"),
        "automated_printability_checks": _checks_for_prompt(job),
    }
    if job.plan:
        ctx["plan"] = {k: v for k, v in job.plan.model_dump().items() if k in (
            "device_name", "task_summary", "functional_limitations", "design_requirements", "measurements",
            "how_it_helps")}
    text = json.dumps(ctx, indent=2, ensure_ascii=False)
    if job.approach == "custom":
        text += "\n\nOPENSCAD CODE:\n" + job.source_code[:15000]
    return text


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------

def _render_current(job: Job, views=("iso", "back", "top")) -> None:
    job.previews = cad.render_previews(job.stl, views=views)
    it = job.current_iteration
    iso = next((p for p in job.previews if p.stem.endswith("_iso")), None)
    if it is not None and iso is not None:
        it["preview_url"] = _rel_url(iso)


def visual_review(job: Job, round_no: int) -> Review:
    job.step("improve", "running", f"round {round_no}: rendering views")
    _render_current(job)
    parts = [gemini.image_file(p) for p in job.previews]
    parts.append(gemini.text("Rendered views of the compiled part (iso, back, top).\n\n" + _design_context(job)))
    job.step("improve", "running", f"round {round_no}: Gemini inspects renders + checks")
    review: Review = gemini.generate_json(config.REVIEW_MODEL, parts, Review,
                                          prompts.review_system(job.language), thinking="medium")
    job.review = review.model_dump()
    it = job.current_iteration
    if it is not None:
        it["critique"] = review.summary[:400]
        it["issues"] = review.issues[:8]
        it["verdict"] = "ok" if (review.meets_requirements and review.printable) else "needs_fix"
    return review


def improve(job: Job, rounds: int | None = None) -> None:
    """Agentic loop: deterministic checks + visual review -> fix -> recompile, until clean or out of rounds."""
    rounds = config.MAX_FIX_ROUNDS if rounds is None else rounds
    job.step("improve", "running", "printability checks")
    for r in range(1, rounds + 1):
        review = visual_review(job, r) if job.review_enabled else None
        checks_failed = bool(job.checks and not job.checks.get("passed", True))
        review_wants = bool(review and not (review.meets_requirements and review.printable)
                            and (review.parameter_changes or review.code_changes))
        if not checks_failed and not review_wants:
            break
        changes = {c.name: c.value for c in review.parameter_changes} if review else {}
        why = "; ".join(([review.summary] if review_wants else [])
                        + ([job.checks.get("feedback", "")] if checks_failed else []))[:300]
        source = "review_fix" if review_wants else "checks_fix"
        job.step("improve", "running", f"round {r}: applying fixes")
        try:
            if job.approach == "template":
                if not changes:
                    break  # templates are fixed geometry: only parameters can change
                compile_version(job, job.source_code, _apply_changes(job, changes), source, why)
            else:
                params = _apply_changes(job, changes)
                instructions = []
                if review_wants:
                    instructions.append("REVIEW:\n" + (review.code_changes or "") + "\nISSUES:\n- " + "\n- ".join(review.issues))
                if checks_failed:
                    instructions.append("AUTOMATED PRINTABILITY CHECKS (must be fixed):\n" + job.checks.get("feedback", ""))
                fixed = gemini.generate_json(
                    config.CAD_MODEL,
                    [gemini.text("Improve this OpenSCAD file so the following problems are solved. Return the "
                                 "complete file.\n\n" + "\n\n".join(instructions) + "\n\nCODE:\n"
                                 + cad.bake_params(job.source_code, params))],
                    CadDesign, prompts.cad_system(), thinking="medium")
                compile_custom_with_repair(job, fixed, source, why)
        except Exception as e:  # noqa: BLE001 - keep the last good version
            traceback.print_exc()
            job.iterations.append({"version": None, "source": "fix_failed", "note": str(e)[:300]})
            break
    if not job.previews:
        _render_current(job, views=("iso",))
    c = (job.checks or {}).get("counts", {})
    job.step("improve", "done", f"v{job.version} · checks {c.get('pass', 0)}✓ {c.get('warn', 0)}! {c.get('fail', 0)}✗")


def run_generate(job: Job, media: list[tuple[Path, str]], impairment: str, activity: str, notes: str) -> None:
    uploaded: list[str] = []
    try:
        job.status = "running"
        job.inputs = {"impairment": impairment, "activity": activity, "notes": notes, "media": len(media)}
        job.step("analyze", "running", f"{len(media)} file(s)")
        parts = []
        for path, mime in media:
            part, name = gemini.media_part(path, mime)
            parts.append(part)
            if name:
                uploaded.append(name)
        parts.append(gemini.text(_user_brief(impairment, activity, notes, len(media))))
        plan: DesignPlan = gemini.generate_json(config.ANALYSIS_MODEL, parts, DesignPlan,
                                                prompts.analysis_system(job.language), thinking="medium")
        job.plan = plan
        # --- precise-measurement ---
        plan = measure.refine_plan(plan, photos=[p for p, m in media if m.startswith("image/")] or
                                   ([job.visual_photo] if job.visual_photo else []),
                                   on_progress=lambda d: job.step("analyze", "running", d), language=job.language)
        job.plan = plan
        use_template = plan.approach.strip().lower() == "template" and plan.template_id in BY_ID
        job.step("analyze", "done", plan.device_name)

        job.step("design", "running")
        if use_template:
            job.approach, job.template_id = "template", plan.template_id
            code = (config.TEMPLATE_DIR / BY_ID[plan.template_id].file).read_text(encoding="utf-8")
            params = resolve_params(plan.template_id, {p.name: p.value for p in plan.template_parameters})
            job.step("design", "done", f"template: {BY_ID[plan.template_id].name}")
            job.step("compile", "running", "OpenSCAD")
            compile_version(job, code, params, "initial")
        else:
            job.approach = "custom"
            job.step("design", "running", "Gemini writes OpenSCAD code")
            design: CadDesign = gemini.generate_json(config.CAD_MODEL, [gemini.text(_plan_for_cad(plan))], CadDesign,
                                                     prompts.cad_system(), thinking="medium")
            job.step("design", "done", "custom OpenSCAD design")
            compile_custom_with_repair(job, design, "initial")
        job.step("compile", "done", f"{job.compile_info.get('seconds', '?')} s")

        improve(job)
        job.status = "done"
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        job.error = str(e)
        job.fail_running_step(str(e))
        job.status = "error"
    finally:
        gemini.delete_files(uploaded)
        # keep only the single photo used for the optional visualization; delete all other media
        for path, _ in media:
            if path != job.visual_photo:
                path.unlink(missing_ok=True)
        job.save()


def run_refine(job: Job, feedback: str) -> None:
    try:
        job.status = "running"
        job.reset_steps(("refine", "compile", "improve"))
        job.step("refine", "running", "Gemini adapts the design")
        context = _design_context(job) + f"\n\nUSER FEEDBACK:\n{feedback}"
        if job.approach == "template":
            r: RefineParams = gemini.generate_json(config.REVIEW_MODEL, [gemini.text(context)], RefineParams,
                                                   prompts.refine_system(job.language), thinking="low")
            job.step("refine", "done", r.explanation[:200])
            job.step("compile", "running", "OpenSCAD")
            compile_version(job, job.source_code, _apply_changes(job, {c.name: c.value for c in r.parameter_changes}),
                            "refine", feedback)
        else:
            design: CadDesign = gemini.generate_json(
                config.CAD_MODEL,
                [gemini.text("Change this OpenSCAD design according to the user feedback. Return the full file.\n\n"
                             + context)],
                CadDesign, prompts.cad_system(), thinking="medium")
            job.step("refine", "done", design.design_notes[:200])
            compile_custom_with_repair(job, design, "refine", feedback)
        job.step("compile", "done", f"{job.compile_info.get('seconds', '?')} s")
        improve(job, rounds=1)
        job.status = "done"
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        job.error = str(e)
        job.fail_running_step(str(e))
        job.status = "error"
    finally:
        job.save()


def run_template_only(job: Job, template_id: str) -> None:
    """Library mode: compile a template with default values, no Gemini involved."""
    try:
        job.status = "running"
        job.approach, job.template_id = "template", template_id
        job.step("compile", "running", "OpenSCAD")
        code = (config.TEMPLATE_DIR / BY_ID[template_id].file).read_text(encoding="utf-8")
        compile_version(job, code, resolve_params(template_id, {}), "initial")
        _render_current(job, views=("iso",))
        c = (job.checks or {}).get("counts", {})
        job.step("compile", "done", f"{job.compile_info.get('seconds', '?')} s · checks {c.get('pass', 0)}✓ "
                                    f"{c.get('warn', 0)}! {c.get('fail', 0)}✗")
        job.status = "done"
    except Exception as e:  # noqa: BLE001
        job.error = str(e)
        job.fail_running_step(str(e))
        job.status = "error"
    finally:
        job.save()


def rebuild(job: Job, values: dict[str, float]) -> None:
    """Recompile the current design with new parameter values (no Gemini)."""
    compile_version(job, job.source_code, _apply_changes(job, values), "manual")
    _render_current(job, views=("iso",))
    job.save()


# --------------------------------------------------------------------------
# AI usage visualization (Nano Banana frames + Omni video) - only on demand
# --------------------------------------------------------------------------

def _animation_prompts(job: Job) -> tuple[str, str, str]:
    if job.plan:
        a = job.plan.animation
        return a.start_scene, a.end_scene, a.motion
    t = BY_ID.get(job.template_id)
    name = t.name if t else "assistive device"
    return (f"A person with reduced hand function uses the 3D-printed {name} in a bright, everyday home. "
            f"{t.description if t else ''}",
            f"The same person a few seconds later has successfully finished the task with the {name}.",
            f"Calm, natural hand movement using the {name} to complete the everyday task, static camera.")


def run_storyboard(job: Job, poses: list[Path], captions: list[str] | None = None) -> None:
    """Realistic storyboard from rendered poses of the real STL (three.js usage animation)."""
    from . import visualize

    t0 = time.time()
    version = job.version
    out_dir = job.dir / f"visual_v{version}"

    def progress(stage: str, detail: str = "") -> None:
        job.visual.update({"stage": stage, "detail": detail[:200]})

    try:
        scene = _animation_prompts(job)[0]
        captions = captions or []
        frames = visualize.make_storyboard(out_dir, poses=poses, photo=job.visual_photo, scene_prompt=scene,
                                           captions=captions, on_progress=progress)
        job.visual.update({"status": "done", "stage": "done", "version": version,
                           "storyboard": [{"step": i + 1, "url": _rel_url(p),
                                           "caption": captions[i] if i < len(captions) else ""}
                                          for i, p in enumerate(frames)],
                           "pose_urls": [_rel_url(p) for p in poses],
                           "seconds": round(time.time() - t0)})
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        job.visual.update({"status": "error", "error": str(e)[:400]})
    finally:
        job.save()


def run_visualize(job: Job, with_video: bool) -> None:
    from . import visualize  # imported lazily: heavy and only needed on demand

    t0 = time.time()
    version = job.version
    vis_dir = job.dir / f"visual_v{version}"
    prev = job.visual if job.visual.get("version") == version else {}

    def progress(stage: str, detail: str = "") -> None:
        job.visual.update({"stage": stage, "detail": detail[:200]})

    job.visual = {**prev, "status": "running", "version": version, "with_video": with_video, "stage": "render",
                  "detail": "", "error": None}
    try:
        render = cad.render_previews(job.stl, views=("iso",))
        if not render:
            raise RuntimeError("Could not render the model for the visualization.")
        start_p, end_p, motion_p = _animation_prompts(job)
        start = vis_dir / Path(prev["start_url"]).name if prev.get("start_url") else None
        end = vis_dir / Path(prev["end_url"]).name if prev.get("end_url") else None
        if not (start and end and start.exists() and end.exists()):
            frames = visualize.make_frames(vis_dir, device_render=render[0], photo=job.visual_photo,
                                           start_prompt=start_p, end_prompt=end_p, on_progress=progress)
            start, end = frames["start"], frames["end"]
            job.visual.update({"start_url": _rel_url(start), "end_url": _rel_url(end)})
        video = None
        if with_video:
            video = visualize.make_video(vis_dir, start_frame=start, end_frame=end, device_render=render[0],
                                         motion_prompt=motion_p, on_progress=progress)
            job.visual["video_url"] = _rel_url(video)
        job.visual.update({"status": "done", "stage": "done", "seconds": round(time.time() - t0)})
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        job.visual.update({"status": "error", "error": str(e)[:400]})
    finally:
        job.save()
