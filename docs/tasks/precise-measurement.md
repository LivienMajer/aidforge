# Aufgabe: Präzisere Maße aus Fotos (für einen Agenten auf eigenem Branch)

## Ziel
Die Passform der Hilfsmittel hängt an wenigen kritischen Maßen des Objekts (z. B. Schlüsselkopf-Breite,
Deckel-Durchmesser). Heute schätzt Gemini diese Maße frei aus dem Foto. Diese Aufgabe macht die Messung
**deterministisch und nachvollziehbar**: Gemini lokalisiert nur Punkte im Bild, Python rechnet die Millimeter.

Umsetzen (in dieser Reihenfolge):
1. **Pixel-Messung mit Referenzobjekt** (Kern)
2. **Perspektivkorrektur** über die 4 Ecken einer Bankkarte (Homographie)
3. **Mehrfachmessung → Unsicherheit** (± mm)
4. **Toleranz an Unsicherheit koppeln**
5. **Foto-Anleitung im UI** (nur Text)

## Arbeitsweise – so bleibt es leicht integrierbar
Am Hauptbranch wird parallel gearbeitet. Deshalb:
- Branch: `git checkout -b feature/precise-measurement origin/main`
- **Fast alles in NEUE Dateien:** `app/measure.py`, `tests/test_measure.py`, ggf. `scripts/measure_cli.py`.
- In bestehenden Dateien nur **kleine, klar markierte Einhängepunkte** (jeweils `# --- precise-measurement ---`).
  Keine Umbenennungen, keine Umformatierung, keine Refactorings fremden Codes.
- Feature-Flag `PRECISE_MEASURE=1` (Default an); bei Fehler immer still auf das alte Verhalten zurückfallen.
- Vor dem PR: `git fetch && git rebase origin/main`, Konflikte nur in den Einhängepunkten.
- Kleine Commits, PR gegen `main` mit kurzer Beschreibung + Vorher/Nachher-Zahlen.

## Kontext (bitte zuerst lesen)
- `README.md` (Setup, Pipeline), `TEAM.md`
- `app/pipeline.py` → `run_generate()`: Analyse-Aufruf erzeugt `DesignPlan`; danach `resolve_params(...)` aus `plan.template_parameters`.
- `app/schemas.py` → `DesignPlan`, `Measurement`, `ScaleReference`, `FitLink`.
- `app/prompts.py` → `analysis_system()` beschreibt die bisherige Messung.
- `app/gemini.py` → `generate_json(model, parts, schema, system, thinking=...)` (Structured Output), `media_part()`, `image_file()`.
- `app/templates_registry.py` → Vorlagen-Parameter; Größenparameter beschreiben das **echte Objekt**, die Vorlage addiert `tolerance` selbst.
- Gemini-Modelle siehe README-Tabelle (Analyse: `gemini-4-hydrogen`). `.env` mit `GEMINI_API_KEY` nötig.
- Testfoto: `demo_inputs/key_with_coin.jpg` (Schlüssel + 1-€-Münze, Ø 23,25 mm).

## 1. Pixel-Messung (`app/measure.py`)
Zweiter, kleiner Gemini-Aufruf **nach** der Analyse, nur für Fotos (bei Video: das Standbild `job.visual_photo`):
- Eingabe: Bild + Liste der benötigten Maße = `plan.fit_links` (bzw. `plan.measurements`) + erkanntes Referenzobjekt.
- Gemini liefert per Structured Output **nur Bildkoordinaten** (normiert 0–1000, Gemini-üblich):
  - Referenz: Kreis → zwei gegenüberliegende Randpunkte (Durchmesser) bzw. Karte → 4 Ecken in Reihenfolge.
  - Je Maß: zwei Endpunkte `p1`, `p2` + Name (exakt wie in `measurements`).
- Python: Pixelabstand → mm über bekannte Referenzgröße
  (1-€ 23,25 mm, 2-€ 25,75 mm, 50-ct 24,25 mm, Bankkarte 85,60 × 53,98 mm, A4 210 × 297 mm).
- Ergebnis überschreibt die Werte in `plan.measurements` (source = `"reference"`) **und** die verknüpften
  `template_parameters` (über `fit_links`), aber **nie** Werte mit source `"user"`.
- Bildgröße für die Umrechnung aus der Datei lesen (Pillow ist ok, zu `requirements.txt` hinzufügen).

## 2. Perspektivkorrektur
Wenn die Referenz eine Karte (oder A4) mit 4 Ecken ist: Homographie berechnen (`cv2.getPerspectiveTransform`
oder eigene 4-Punkt-DLT mit numpy, numpy ist schon da) → alle Messpunkte in die entzerrte Ebene
transformieren → dort messen. Bei Münze (nur Kreis) keine Homographie, aber Hinweis auf Unsicherheit.
Hinweis in den Ergebnissen: Messung gilt nur für Objekte in der Ebene der Referenz.

## 3. Mehrfachmessung → Unsicherheit
- Messaufruf 3× (parallel, `thinking="low"`) → Median als Wert, Spannweite/2 als ± Unsicherheit.
- Mehrere hochgeladene Fotos: alle messen und zusammenfassen.
- Unsicherheit pro Maß im Plan ablegen. Schema-Erweiterung **rückwärtskompatibel**:
  `Measurement.uncertainty_mm: float = 0.0` (mit Default!), optional `Measurement.method: str = ""`.

## 4. Toleranz koppeln
Vor `compile_version` (Einhängepunkt in `run_generate`): wenn die Vorlage einen Parameter `tolerance` hat,
`tolerance = clamp(Basis + 0.5 * max(Unsicherheit der verknüpften Maße), min, max)` (Grenzen aus der Registry).
Ist ein Maß sehr unsicher (> 1,5 mm), einen Eintrag in `plan.questions_for_user` ergänzen
("Bitte Schlüsselkopf-Breite nachmessen").

## 5. UI (minimal, nur Text)
- In `web/app.js` (I18N de/en) Hinweistext unter dem Upload: "Objekt flach, von oben fotografieren,
  Bankkarte oder Münze direkt daneben."
- Im Analyse-Tab bei Maßen `± x mm` anzeigen, falls `uncertainty_mm > 0`.
- Hinweis: Das UI wird parallel umgebaut. Nur diese zwei kleinen Stellen ändern, IDs nicht anfassen.

## Integration (Einhängepunkte – nicht mehr)
- `app/pipeline.py` `run_generate()`: direkt nach `job.plan = plan`:
  ```python
  # --- precise-measurement ---
  plan = measure.refine_plan(plan, photos=[p for p, m in media if m.startswith("image/")] or
                             ([job.visual_photo] if job.visual_photo else []), on_progress=lambda d: job.step("analyze", "running", d))
  job.plan = plan
  ```
  `refine_plan` fängt alle Fehler selbst ab und gibt bei Problemen den unveränderten Plan zurück.
- `app/schemas.py`: die zwei optionalen Felder in `Measurement`.
- `app/prompts.py`: nichts ändern nötig (Messprompt lebt in `measure.py`).

## Tests / Abnahme
- `tests/test_measure.py` (pytest, ohne API): Pixel→mm-Umrechnung, Homographie mit synthetischen Punkten
  (bekanntes Rechteck schräg projiziert → Maße auf < 1 % genau), Median/Unsicherheit, Toleranz-Kopplung,
  "user"-Werte werden nie überschrieben.
- Live (mit Key): `demo_inputs/key_with_coin.jpg` → Schlüsselkopf-Breite plausibel (typisch 22–26 mm) mit ±.
  Eigenes Foto mit Bankkarte + Objekt bekannter Größe (z. B. Lineal, Stift) → Fehler < 1 mm dokumentieren.
- Ohne Referenz im Bild: altes Verhalten, keine Fehler.
- `run_generate` Gesamtzeit + max. ~15 s.
- PR-Beschreibung: Messgenauigkeit vorher/nachher an 2–3 Fotos.
