"""Offline tests for app/measure.py (no API calls)."""

import numpy as np
import pytest

from app import measure
from app.measure import LineMark, MeasureMarks, P2, ReferenceMarks
from app.schemas import (AnimationBrief, DesignPlan, FitLink, Measurement, ParamValue, PrintSettings,
                         ScaleReference)

W, H = 2000, 1500


def norm(px, py):
    """pixel -> normalised 0..1000 point"""
    return P2(x=px / W * 1000, y=py / H * 1000)


def plan(**kw) -> DesignPlan:
    base = dict(
        task_summary="unlock door", observed_in_media="", functional_limitations=[], root_problem="",
        design_requirements=[], scale_reference=ScaleReference(detected=True, object="1 EUR coin", known_size_mm=23.25,
                                                               method=""),
        measurements=[Measurement(name="key head width", value_mm=24.0, source="reference"),
                      Measurement(name="key head thickness", value_mm=2.0, source="user")],
        approach="template", template_id="key_turner",
        template_parameters=[ParamValue(name="key_bow_width", value=24.0), ParamValue(name="tolerance", value=0.3)],
        fit_links=[FitLink(measurement_name="key head width", param_name="key_bow_width"),
                   FitLink(measurement_name="key head thickness", param_name="key_bow_thickness")],
        custom_design_brief="", device_name="Key turner", how_it_helps="", usage_steps=[],
        print_settings=PrintSettings(material="PLA", layer_height_mm=0.2, infill_percent=30, walls=3, supports=False,
                                     orientation="flat", notes=""),
        safety_notes=[], assumptions=[], questions_for_user=[],
        animation=AnimationBrief(start_scene="", end_scene="", motion=""), confidence=0.8)
    base.update(kw)
    return DesignPlan(**base)


# ---- coin -----------------------------------------------------------------------------------------

def test_coin_pixel_to_mm():
    # 1 EUR coin, 232.5 px wide -> 0.1 mm/px; a 240 px line -> 24 mm
    c = np.array([500.0, 500.0]); r = 116.25
    marks = MeasureMarks(
        reference=ReferenceMarks(kind="coin_1_eur", coin_left=norm(c[0] - r, c[1]), coin_right=norm(c[0] + r, c[1]),
                                 coin_top=norm(c[0], c[1] - r), coin_bottom=norm(c[0], c[1] + r), corners=[]),
        lines=[LineMark(name="key head width", visible=True, p1=norm(1000, 700), p2=norm(1240, 700)),
               LineMark(name="hidden", visible=False, p1=norm(0, 0), p2=norm(10, 10))])
    vals, info = measure.measure_marks(marks, W, H)
    assert vals["key head width"] == pytest.approx(24.0, rel=1e-6)
    assert "hidden" not in vals
    assert info["method"] == "coin" and info["tilt"] == pytest.approx(1.0)


def test_coin_tilt_is_rectified_per_axis():
    # camera tilted forward: coin 200 px wide, 120 px tall; a vertical line in the image is foreshortened the same
    mmpp, ratio = measure.coin_scale(np.array([0, 0.0]), np.array([200, 0.0]),
                                     np.array([100, -60.0]), np.array([100, 60.0]), 23.25)
    assert mmpp == pytest.approx([23.25 / 200, 23.25 / 120])
    assert ratio == pytest.approx(0.6)
    assert np.linalg.norm(np.array([0, 120.0]) * mmpp) == pytest.approx(23.25)   # vertical = true size
    assert np.linalg.norm(np.array([200, 0.0]) * mmpp) == pytest.approx(23.25)   # horizontal = true size


# ---- homography -----------------------------------------------------------------------------------

def test_homography_recovers_obliquely_projected_rectangle():
    # bank card + a 40 mm x 20 mm object in the same plane (mm), projected with a strong perspective
    card = np.array([[0, 0], [85.6, 0], [85.6, 53.98], [0, 53.98]])
    obj = np.array([[100, 10], [140, 10], [140, 30]])          # 40 mm edge, 20 mm edge
    p = np.array([[9.0, 2.0, 300], [1.5, 7.0, 200], [0.004, 0.002, 1]])  # true homography mm -> px
    proj = lambda pts: measure.apply_h(p, pts)
    card_px = proj(card)[[2, 0, 3, 1]]                           # shuffled order on purpose
    hm = measure.rect_homography(card_px, 85.6, 53.98)
    o = measure.apply_h(hm, proj(obj))
    assert np.linalg.norm(o[0] - o[1]) == pytest.approx(40.0, rel=0.01)
    assert np.linalg.norm(o[1] - o[2]) == pytest.approx(20.0, rel=0.01)


def test_card_marks_end_to_end():
    # card 856 x 539.8 px axis-aligned -> 0.1 mm/px
    corners = [norm(100, 100), norm(956, 100), norm(956, 639.8), norm(100, 639.8)]
    marks = MeasureMarks(reference=ReferenceMarks(kind="card", coin_left=P2(x=0, y=0), coin_right=P2(x=0, y=0),
                                                  coin_top=P2(x=0, y=0), coin_bottom=P2(x=0, y=0), corners=corners),
                         lines=[LineMark(name="key head width", visible=True, p1=norm(1200, 300), p2=norm(1200, 530))])
    vals, info = measure.measure_marks(marks, W, H)
    assert vals["key head width"] == pytest.approx(23.0, rel=0.005)
    assert info["method"] == "homography" and info["floor_mm"] > 0


def test_no_reference_gives_nothing():
    marks = MeasureMarks(reference=ReferenceMarks(kind="none", coin_left=P2(x=0, y=0), coin_right=P2(x=0, y=0),
                                                  coin_top=P2(x=0, y=0), coin_bottom=P2(x=0, y=0), corners=[]),
                         lines=[LineMark(name="x", visible=True, p1=norm(0, 0), p2=norm(5, 5))])
    assert measure.measure_marks(marks, W, H)[0] == {}


# ---- aggregation / tolerance / plan update --------------------------------------------------------

def test_median_and_uncertainty():
    assert measure.aggregate([23.0, 24.0, 23.4], 0.1) == (23.4, 0.5)
    assert measure.aggregate([23.0, 23.0, 23.0], 0.3) == (23.0, 0.3)   # floor


def test_tolerance_coupling_and_clamp():
    assert measure.couple_tolerance(0.3, 0.4, 0.1, 1.0) == 0.5
    assert measure.couple_tolerance(0.3, 5.0, 0.1, 1.0) == 1.0


def test_apply_results_updates_linked_params_and_tolerance():
    out = measure.apply_results(plan(), {"key head width": (23.04, 0.4, "coin (coin_1_eur), 3 runs")})
    m = {x.name: x for x in out.measurements}["key head width"]
    assert (m.value_mm, m.uncertainty_mm, m.source) == (23.0, 0.4, "reference")
    params = {p.name: p.value for p in out.template_parameters}
    assert params["key_bow_width"] == 23.0
    assert params["tolerance"] == 0.5          # 0.3 + 0.5 * 0.4
    assert out.questions_for_user == []


def test_user_values_are_never_overwritten():
    p = plan()
    out = measure.apply_results(p, {"key head thickness": (3.5, 0.2, "coin")})
    m = {x.name: x for x in out.measurements}["key head thickness"]
    assert (m.value_mm, m.source) == (2.0, "user")
    assert out == p


def test_unsure_measurement_asks_user():
    out = measure.apply_results(plan(), {"key head width": (23.0, 2.0, "coin")}, language="en")
    assert len(out.questions_for_user) == 1 and "key head width" in out.questions_for_user[0]


def test_refine_plan_falls_back_on_error(monkeypatch):
    p = plan()
    monkeypatch.setattr(measure, "measure_photos", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert measure.refine_plan(p, ["x.jpg"]) is p
    assert measure.refine_plan(p, []) is p


def test_old_plans_without_new_fields_still_load():
    m = Measurement.model_validate({"name": "a", "value_mm": 1.0, "source": "typical"})
    assert m.uncertainty_mm == 0.0 and m.method == ""


# ---- review fixes ---------------------------------------------------------------------------------

def test_long_side_from_corner_order_beats_image_lengths():
    # A5 sheet seen very obliquely: its long side (210 mm) looks SHORTER in the image than the short side.
    sheet = np.array([[0, 0], [210.0, 0], [210.0, 148.0], [0, 148.0]])
    p = np.array([[2.0, 0.3, 300], [0.0, 6.0, 100], [0.0, 0.012, 1]])    # strong tilt along y
    px = measure.apply_h(p, sheet)
    d = lambda i, j: np.linalg.norm(px[i] - px[j])
    assert d(0, 1) < d(1, 2)                                             # the trap: long side looks short
    obj = np.array([[20, 20], [60, 20]])                                 # 40 mm line on the sheet
    for order in ([0, 1, 2, 3], [1, 0, 3, 2], [2, 3, 0, 1], [3, 2, 1, 0]):   # any start, both directions
        hm = measure.rect_homography(px[order], 210.0, 148.0)
        o = measure.apply_h(hm, measure.apply_h(p, obj))
        assert np.linalg.norm(o[0] - o[1]) == pytest.approx(40.0, rel=0.01), order


def test_paper_sizes_known():
    assert measure.RECTS["a5"] == (210.0, 148.0)
    assert measure.RECTS["a6"] == (148.0, 105.0)
    assert "letter" in measure.RECTS


def test_names_match_case_and_space_insensitive():
    p = plan(fit_links=[FitLink(measurement_name="Key head  width ", param_name="key_bow_width")])
    assert [m.name for m in measure._targets(p)] == ["key head width"]
    out = measure.apply_results(p, {"KEY HEAD WIDTH": (22.0, 0.3, "coin")})
    assert {x.name: x.value_mm for x in out.measurements}["key head width"] == 22.0
    assert {x.name: x.value for x in out.template_parameters}["key_bow_width"] == 22.0


def test_line_names_from_gemini_are_normalised():
    c, r = np.array([500.0, 500.0]), 116.25
    marks = MeasureMarks(
        reference=ReferenceMarks(kind="coin_1_eur", coin_left=norm(c[0] - r, c[1]), coin_right=norm(c[0] + r, c[1]),
                                 coin_top=norm(c[0], c[1] - r), coin_bottom=norm(c[0], c[1] + r), corners=[]),
        lines=[LineMark(name="Key Head Width", visible=True, p1=norm(1000, 700), p2=norm(1240, 700))])
    assert measure.measure_marks(marks, W, H)[0] == {"key head width": pytest.approx(24.0)}


def test_unreadable_photo_does_not_cancel_the_others(monkeypatch, tmp_path):
    from app import gemini
    good, bad = tmp_path / "good.jpg", tmp_path / "bad.heic"
    good.write_bytes(b"x"); bad.write_bytes(b"x")

    def load(path):
        if path == bad:
            raise OSError("cannot identify image file")
        return {"type": "image"}, W, H
    c, r = np.array([500.0, 500.0]), 116.25
    marks = MeasureMarks(
        reference=ReferenceMarks(kind="coin_1_eur", coin_left=norm(c[0] - r, c[1]), coin_right=norm(c[0] + r, c[1]),
                                 coin_top=norm(c[0], c[1] - r), coin_bottom=norm(c[0], c[1] + r), corners=[]),
        lines=[LineMark(name="key head width", visible=True, p1=norm(1000, 700), p2=norm(1240, 700))])
    monkeypatch.setattr(measure, "_load_photo", load)
    monkeypatch.setattr(measure, "_locate", lambda part, req: marks)
    monkeypatch.setattr(gemini, "client", lambda: None)
    res = measure.measure_photos(plan(), [bad, good])
    assert res["key head width"][0] == pytest.approx(24.0)


def test_single_run_is_not_enough(monkeypatch):
    # 1 of 3 runs guesses a reference, the others see none -> no result (it was a guess)
    from app import gemini
    c, r = np.array([500.0, 500.0]), 116.25
    coin = MeasureMarks(
        reference=ReferenceMarks(kind="coin_1_eur", coin_left=norm(c[0] - r, c[1]), coin_right=norm(c[0] + r, c[1]),
                                 coin_top=norm(c[0], c[1] - r), coin_bottom=norm(c[0], c[1] + r), corners=[]),
        lines=[LineMark(name="key head width", visible=True, p1=norm(1000, 700), p2=norm(1240, 700))])
    none = coin.model_copy(update={"reference": coin.reference.model_copy(update={"kind": "none"})})
    seq = iter([coin, none, none])
    monkeypatch.setattr(measure, "_load_photo", lambda p: ({"type": "image"}, W, H))
    monkeypatch.setattr(measure, "_locate", lambda part, req: next(seq))
    monkeypatch.setattr(measure, "RUNS", 3)
    monkeypatch.setattr(gemini, "client", lambda: None)
    assert measure.measure_photos(plan(), ["a.jpg"]) == {}
