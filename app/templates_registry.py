"""Catalog of parametric assistive-device templates (OpenSCAD files in scad_templates/).

Each template lists its parameters with defaults and safe ranges. Gemini picks a template
and fills the parameters; values are clamped to the ranges before compiling.
"""

from dataclasses import dataclass, field


@dataclass
class P:
    name: str
    default: float
    min: float
    max: float
    step: float
    description: str


@dataclass
class Template:
    id: str
    name: str
    file: str
    description: str
    good_for: str
    params: list[P] = field(default_factory=list)


TEMPLATES: list[Template] = [
    Template(
        id="built_up_handle",
        name="Built-up handle",
        file="built_up_handle.scad",
        description="Thick ergonomic grip with finger grooves that slides over the handle of a spoon, fork, "
        "knife, pen, toothbrush, razor, makeup brush, paint brush or similar.",
        good_for="weak grip, limited finger flexion, arthritis, tremor (adds mass + diameter), "
        "eating, writing, brushing teeth, painting",
        params=[
            P("grip_length", 110, 60, 200, 1, "total length of the handle (mm)"),
            P("grip_diameter", 32, 20, 60, 1, "outer diameter (mm); 30-40 for weak grip"),
            P("bore_shape", 0, 0, 1, 1, "0 = round bore (pens, round handles), 1 = flat rectangular bore (flat cutlery)"),
            P("bore_diameter", 9, 4, 30, 0.5, "round bore: diameter of the inserted shaft (mm)"),
            P("bore_width", 12, 4, 30, 0.5, "flat bore: width of the inserted handle (mm)"),
            P("bore_thickness", 3.5, 1.5, 15, 0.5, "flat bore: thickness of the inserted handle (mm)"),
            P("bore_depth", 80, 20, 200, 1, "depth of the bore from the top end (mm)"),
            P("finger_grooves", 4, 0, 6, 1, "number of finger grooves (0 = smooth)"),
            P("groove_depth", 2, 0, 5, 0.5, "depth of the finger grooves (mm)"),
            P("end_radius", 4, 1, 10, 0.5, "rounding of the ends (mm)"),
            P("flat_side", 1, 0, 1, 1, "1 = flat side so it does not roll away"),
            P("tolerance", 0.3, 0.1, 1, 0.05, "clearance around the bore (mm)"),
        ],
    ),
    Template(
        id="universal_cuff",
        name="Universal cuff",
        file="universal_cuff.scad",
        description="C-shaped band worn around the palm with a pocket that holds a utensil, pen or toothbrush "
        "without any grip.",
        good_for="no active grip at all (tetraplegia C5/C6, severe arthritis, stroke, hand paralysis), "
        "eating, writing, brushing teeth, using a stylus",
        params=[
            P("palm_width", 85, 60, 110, 1, "palm width across the knuckles (mm)"),
            P("hand_thickness", 30, 18, 45, 1, "hand thickness palm-to-back at the knuckles (mm)"),
            P("band_width", 28, 18, 45, 1, "band width along the hand (mm)"),
            P("wall", 3, 2, 5, 0.5, "band wall thickness (mm)"),
            P("opening", 24, 10, 45, 1, "gap on the thumb side to slip the hand in (mm)"),
            P("holder_diameter", 12, 5, 25, 0.5, "diameter of the utensil handle that goes into the pocket (mm)"),
            P("holder_length", 50, 25, 80, 1, "length of the utensil pocket (mm)"),
            P("holder_wall", 3, 2, 5, 0.5, "wall around the pocket (mm)"),
            P("holder_offset", 0, -30, 30, 1, "shift of the pocket along the palm width (mm)"),
            P("tolerance", 0.4, 0.1, 1, 0.05, "clearance (mm)"),
        ],
    ),
    Template(
        id="key_turner",
        name="Key turner",
        file="key_turner.scad",
        description="Large lever handle that clamps the head of a key, so the key can be turned with the "
        "whole hand instead of a pinch grip.",
        good_for="weak pinch grip, arthritis, reduced wrist rotation, tremor; locking/unlocking doors, "
        "mailboxes, bike locks",
        params=[
            P("key_bow_width", 24, 12, 40, 0.5, "width of the key head (mm)"),
            P("key_bow_length", 22, 10, 40, 0.5, "length of the key head inserted into the handle (mm)"),
            P("key_bow_thickness", 2.5, 1.5, 6, 0.1, "thickness of the key head (mm)"),
            P("lever_length", 85, 50, 140, 1, "total length of the turner (mm)"),
            P("lever_width", 50, 30, 80, 1, "width of the grip end (mm)"),
            P("thickness", 14, 8, 25, 1, "handle thickness (mm)"),
            P("finger_hole", 1, 0, 1, 1, "1 = finger hole in the grip end"),
            P("finger_hole_d", 24, 15, 40, 1, "finger hole diameter (mm)"),
            P("bolt_hole", 1, 0, 1, 1, "1 = M3 bolt hole + nut trap to fix the key through its hole"),
            P("bolt_offset", 11, 5, 30, 0.5, "distance of the bolt hole from the slot opening (mm)"),
            P("chamfer", 2, 0.5, 4, 0.5, "edge chamfer (mm)"),
            P("tolerance", 0.3, 0.1, 1, 0.05, "clearance (mm)"),
        ],
    ),
    Template(
        id="lever_turner",
        name="Lever turner for lids, knobs and taps",
        file="lever_turner.scad",
        description="Ribbed cap that slides over a round jar lid, bottle cap, tap handle or knob and adds one "
        "or two long levers for much more torque.",
        good_for="weak grip, arthritis, one-handed use, reduced wrist strength; opening jars and bottles, "
        "turning taps, stove or radiator knobs",
        params=[
            P("object_diameter", 70, 15, 120, 0.5, "diameter of the lid/knob/tap (mm)"),
            P("grip_depth", 12, 5, 30, 0.5, "how far the cap slides over the object (mm)"),
            P("wall", 4, 2.5, 8, 0.5, "ring wall thickness (mm)"),
            P("top_thickness", 3, 0, 6, 0.5, "closed top plate thickness (0 = open ring)"),
            P("lever_length", 110, 50, 180, 1, "from the centre to the lever tip (mm)"),
            P("lever_width", 26, 15, 40, 1, "lever width (mm)"),
            P("lever_height", 15, 6, 30, 1, "lever thickness (mm)"),
            P("levers", 1, 1, 2, 1, "1 = single lever, 2 = T-handle for two hands"),
            P("rib_count", 30, 0, 60, 1, "number of grip ribs inside"),
            P("rib_depth", 1, 0.3, 3, 0.1, "rib height (mm)"),
            P("hang_hole", 1, 0, 1, 1, "1 = hole at the lever tip to hang it up"),
            P("tolerance", 0.5, 0.1, 1.5, 0.05, "clearance (mm)"),
        ],
    ),
    Template(
        id="cup_holder",
        name="Two-handled cup holder",
        file="cup_holder.scad",
        description="Sleeve that fits around an existing cup or glass and adds one or two large handles.",
        good_for="tremor (two-handed drinking), weak grip, thin glasses that slip, hot drinks; drinking",
        params=[
            P("cup_bottom_diameter", 70, 40, 110, 0.5, "outer diameter of the cup at its base (mm)"),
            P("cup_top_diameter", 80, 40, 120, 0.5, "outer diameter of the cup at its rim (mm)"),
            P("cup_height", 95, 50, 180, 1, "full cup height (mm)"),
            P("sleeve_height", 65, 35, 120, 1, "height of the sleeve (mm)"),
            P("wall", 3, 2, 5, 0.5, "sleeve wall thickness (mm)"),
            P("base_lip", 4, 0, 10, 0.5, "inward lip at the bottom the cup rests on (mm, 0 = none)"),
            P("handles", 2, 1, 2, 1, "number of handles"),
            P("handle_opening_w", 28, 18, 45, 1, "finger opening width (mm)"),
            P("handle_bar", 10, 6, 16, 1, "handle bar thickness (mm)"),
            P("handle_thickness", 14, 8, 25, 1, "handle thickness (mm)"),
            P("tolerance", 0.8, 0.2, 2, 0.1, "clearance around the cup (mm)"),
        ],
    ),
    Template(
        id="card_holder",
        name="Playing card holder",
        file="card_holder.scad",
        description="Weighted block with one or two tilted slots that hold a hand of playing cards upright.",
        good_for="one-handed use, weak grip, tremor, stroke; playing cards and board games, holding "
        "tickets, recipe cards or photos",
        params=[
            P("holder_length", 180, 80, 220, 1, "total length (mm)"),
            P("holder_depth", 55, 30, 100, 1, "front-to-back depth (mm)"),
            P("holder_height", 28, 15, 50, 1, "block height (mm)"),
            P("slots", 2, 1, 2, 1, "number of slot rows"),
            P("slot_width", 2.2, 1, 8, 0.1, "slot gap (mm)"),
            P("slot_depth", 20, 8, 40, 1, "how deep the cards sit (mm)"),
            P("slot_angle", 12, 0, 25, 1, "backward tilt of the cards (deg)"),
            P("end_margin", 10, 5, 30, 1, "closed ends of the slots (mm)"),
            P("corner_radius", 8, 1, 20, 1, "corner radius (mm)"),
            P("chamfer", 2, 0.5, 4, 0.5, "top edge chamfer (mm)"),
        ],
    ),
    Template(
        id="plate_guard",
        name="Plate guard",
        file="plate_guard.scad",
        description="Raised wall with an inward lip that clips onto the edge of a round plate, so food can be "
        "pushed against it onto the spoon or fork with one hand.",
        good_for="one-handed use, stroke / hemiplegia, tremor, poor coordination, loss of one arm, children "
        "with motor impairments; eating from a flat plate, scooping food onto a spoon or fork",
        params=[
            P("plate_diameter", 260, 150, 300, 1, "outer diameter of the plate (mm)"),
            P("rim_thickness", 5, 2, 12, 0.5, "thickness of the plate at its outer edge, where the clip grips (mm)"),
            P("rim_slope", 10, 0, 25, 1, "angle the plate rim rises towards its edge (deg, 0 = flat rim)"),
            P("clip_depth", 14, 6, 30, 1, "how far the lower jaw reaches under the plate, from the edge (mm)"),
            P("grip_bump", 1, 0, 2.5, 0.1, "bump at the lower jaw tip that clamps the plate (mm, 0 = none)"),
            P("arc_angle", 100, 40, 170, 1, "part of the plate edge covered by the wall (deg); "
              "shortened automatically to fit a 220 mm bed"),
            P("wall_height", 30, 15, 60, 1, "wall height above the plate surface (mm)"),
            P("wall_thickness", 3, 2, 6, 0.5, "wall and clip thickness (mm)"),
            P("lip", 5, 0, 12, 0.5, "inward lip at the top that turns food back (mm, 0 = none)"),
            P("tolerance", 0.3, 0.1, 1.5, 0.05, "clearance at the plate edge (mm)"),
        ],
    ),
    Template(
        id="button_hook",
        name="Button hook and zipper pull",
        file="button_hook.scad",
        description="Thick non-rolling handle with a flat wire loop that is pushed through the buttonhole to "
        "pull the button through, plus an optional small hook on the other end for zipper pulls.",
        good_for="one-handed dressing, stroke / hemiplegia, weak grip, arthritis, limited finger dexterity, "
        "tremor, numb fingertips; buttoning shirts, blouses, coats and cuffs, pulling up zippers",
        params=[
            P("handle_length", 100, 70, 140, 1, "length of the handle (mm); shortened automatically if the whole "
              "tool would exceed 214 mm"),
            P("grip_diameter", 30, 22, 45, 1, "handle diameter (mm); 30-40 for weak grip"),
            P("finger_grooves", 3, 0, 5, 1, "number of finger grooves (0 = smooth); about one per 20 mm of handle"),
            P("groove_depth", 1.5, 0, 3, 0.5, "depth of the finger grooves (mm)"),
            P("shaft_length", 30, 10, 60, 1, "distance from the handle end to the button loop (mm)"),
            P("loop_width", 16, 12, 30, 0.5, "outer width of the button loop (mm); about button diameter + 1, "
              "must pass through the buttonhole"),
            P("loop_length", 34, 20, 50, 1, "outer length of the button loop (mm); about twice the button "
              "diameter, at least loop_width + 4"),
            P("loop_bar", 3, 3, 5, 0.5, "width of the loop wire (mm)"),
            P("hook_thickness", 3.5, 3, 6, 0.5, "thickness of shaft, loop and zipper hook (mm)"),
            P("zipper_hook", 1, 0, 1, 1, "1 = zipper-pull hook at the other end of the handle"),
            P("zipper_gap", 4, 2, 8, 0.5, "opening of the zipper hook (mm)"),
        ],
    ),
]

BY_ID = {t.id: t for t in TEMPLATES}


def catalog_text() -> str:
    """Human/LLM-readable description of all templates and their parameters."""
    lines = []
    for t in TEMPLATES:
        lines.append(f"## template_id: {t.id} — {t.name}")
        lines.append(f"What it is: {t.description}")
        lines.append(f"Good for: {t.good_for}")
        lines.append("Parameters (name: default [min..max] — meaning):")
        for p in t.params:
            lines.append(f"  - {p.name}: {p.default} [{p.min}..{p.max}] — {p.description}")
        lines.append("")
    return "\n".join(lines)


def resolve_params(template_id: str, overrides: dict[str, float]) -> list[dict]:
    """Merge overrides into defaults and clamp to the allowed range."""
    t = BY_ID[template_id]
    out = []
    for p in t.params:
        v = overrides.get(p.name, p.default)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = p.default
        v = max(p.min, min(p.max, v))
        if p.step >= 1:
            v = round(v)
        out.append(
            {"name": p.name, "value": v, "min": p.min, "max": p.max, "step": p.step, "description": p.description}
        )
    return out
