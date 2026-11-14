"""Structured-output schemas for the Gemini calls."""

from pydantic import BaseModel, Field


class ScaleReference(BaseModel):
    detected: bool = Field(description="True if an object of known size is visible and was used to scale the image.")
    object: str = Field(description="The reference object, e.g. 'credit card', '1 EUR coin', 'A4 sheet', "
                                    "'adult hand'. Empty string if none.")
    known_size_mm: float = Field(description="The known real size of the reference that was used (e.g. 85.6 for "
                                             "the long edge of a card). 0 if none.")
    method: str = Field(description="One sentence: how pixel sizes were converted to millimetres, or why no "
                                    "reference could be used.")


class Measurement(BaseModel):
    name: str = Field(description="What was measured, e.g. 'key head width' or 'jar lid diameter'.")
    value_mm: float
    source: str = Field(description="'user' if stated by the user, 'reference' if scaled from a reference object "
                                    "in the media, 'media' if roughly estimated from the media without a "
                                    "reference, 'typical' if a typical default value was assumed.")


class FitLink(BaseModel):
    measurement_name: str = Field(description="Exact name of an entry in measurements.")
    param_name: str = Field(description="Template parameter that must match this measured object dimension "
                                        "(e.g. key_bow_width, object_diameter, bore_diameter).")


class AnimationBrief(BaseModel):
    start_scene: str = Field(description="ENGLISH. Photo description of the first moment of real use: whose hand, "
                                         "how the device is held/attached, the object, the setting.")
    end_scene: str = Field(description="ENGLISH. The same scene a few seconds later with the activity "
                                       "accomplished (e.g. the lid is off the jar, the key is turned).")
    motion: str = Field(description="ENGLISH. One or two sentences describing the movement between start and "
                                    "end, for a short video (static camera, natural, calm).")


class ParamValue(BaseModel):
    name: str
    value: float


class PrintSettings(BaseModel):
    material: str = Field(description="e.g. 'PETG (food-safe-ish, tougher than PLA)' or 'TPU 95A (flexible)'.")
    layer_height_mm: float
    infill_percent: int
    walls: int
    supports: bool
    orientation: str = Field(description="How to place the part on the print bed.")
    notes: str


class PlanBrief(BaseModel):
    """Short UI texts so the interface never has to show walls of text."""
    one_liner: str = Field(default="", description="What the device does for this person, max 12 words.")
    limitation_chips: list[str] = Field(default_factory=list, description="2-4 functional limitations, max 4 words each.")
    requirement_bullets: list[str] = Field(default_factory=list, description="3-5 key requirements, max 8 words each.")
    usage_bullets: list[str] = Field(default_factory=list, description="2-4 usage steps, max 8 words each.")
    safety_bullets: list[str] = Field(default_factory=list, description="1-3 safety notes, max 10 words each.")
    print_line: str = Field(default="", description="Print settings in one line, e.g. 'PETG · 0.2 mm · 30 % infill · no supports'.")


class DesignPlan(BaseModel):
    task_summary: str = Field(description="What the person wants to do, in one or two sentences.")
    observed_in_media: str = Field(description="What is visible in the image(s)/video that matters for the design: "
                                               "objects, their size, how the person currently tries to do the task.")
    functional_limitations: list[str] = Field(description="Concrete functional limitations relevant to this task "
                                                          "(e.g. 'cannot form a pinch grip', 'tremor in dominant hand').")
    root_problem: str = Field(description="Why exactly the activity fails today.")
    design_requirements: list[str] = Field(description="Measurable requirements the device must fulfil.")
    scale_reference: ScaleReference
    measurements: list[Measurement]
    approach: str = Field(description="'template' if a catalog template fits well, otherwise 'custom'.")
    template_id: str = Field(description="The chosen template_id if approach is 'template', else an empty string.")
    template_parameters: list[ParamValue] = Field(description="Values for the chosen template's parameters "
                                                              "(only those that differ from the default are required).")
    fit_links: list[FitLink] = Field(description="For every template parameter that describes the size of a real "
                                                 "object the device must fit around/into: which measurement it "
                                                 "must match. Empty for custom designs.")
    custom_design_brief: str = Field(description="If approach is 'custom': a precise geometric description of the part "
                                                 "for a CAD engineer - shapes, all key dimensions in mm, features, how it "
                                                 "attaches to the object, print orientation. Else an empty string.")
    device_name: str = Field(description="Short, friendly name of the device.")
    how_it_helps: str = Field(description="Two or three sentences: how the device compensates for the limitation.")
    usage_steps: list[str]
    print_settings: PrintSettings
    safety_notes: list[str]
    assumptions: list[str]
    questions_for_user: list[str] = Field(description="Up to 3 measurements or facts that would improve the fit.")
    animation: AnimationBrief
    confidence: float = Field(description="0..1 confidence that this device solves the problem.")
    brief: PlanBrief = Field(default_factory=PlanBrief,
                             description="Very short versions of the texts above for the UI (same language).")


class CadParam(BaseModel):
    name: str
    value: float
    min: float
    max: float
    description: str


class CadDesign(BaseModel):
    openscad_code: str = Field(description="Complete OpenSCAD source. Parameters as top-level assignments first.")
    parameters: list[CadParam] = Field(description="Every top-level numeric parameter declared in the code.")
    design_notes: str = Field(description="Short explanation of the geometry and print orientation.")


class Review(BaseModel):
    meets_requirements: bool
    printable: bool
    issues: list[str]
    parameter_changes: list[ParamValue] = Field(description="Parameter value changes that fix the issues "
                                                            "(use exact parameter names). Empty if none.")
    code_changes: str = Field(description="For custom code only: concrete instructions for changing the code. "
                                          "Empty string if not needed.")
    summary: str = Field(description="One or two sentences for the user.")


class RefineParams(BaseModel):
    parameter_changes: list[ParamValue]
    explanation: str


def inline_schema(model: type[BaseModel]) -> dict:
    """Pydantic JSON schema with all $refs inlined (most robust for structured output)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"].split("/")[-1]
                merged = {**resolve(defs[ref]), **{k: v for k, v in node.items() if k != "$ref"}}
                return merged
            return {k: resolve(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    def require_all(node):
        # fields with defaults (e.g. DesignPlan.brief, kept optional so old saved jobs still load)
        # must still be generated by the model
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"].keys())
            for v in node.values():
                require_all(v)
        elif isinstance(node, list):
            for v in node:
                require_all(v)
        return node

    return require_all(resolve(schema))
