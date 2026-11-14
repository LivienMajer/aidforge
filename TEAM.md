# Aufteilung & Zusammenarbeit

Bewertung: **50 % Technik · 30 % Kreativität/Wow · 20 % Praxisnutzen.**
Die Aufteilung folgt den Dateien, damit sich niemand gegenseitig Merge-Konflikte baut.

## Regeln

- `main` muss immer laufen. Jede Person arbeitet auf einem eigenen Branch (`a/...`, `b/...`, ...), kleine PRs, schnell mergen.
- Nur in den eigenen Dateien arbeiten. Wer eine fremde Datei braucht, sagt kurz im Chat Bescheid.
- **API-Vertrag** zwischen Backend und UI = die JSON-Antwort von `GET /api/jobs/{id}` (`Job.to_dict()` in `app/pipeline.py`). Felder nur ergänzen, nie umbenennen.
- `.env` nie committen, `.env.example` bleibt ohne Key.
- Setup: siehe README (OpenSCAD + `.venv` + `.env`). Server: `.venv\Scripts\python -m uvicorn app.main:app --port 8000`.

## Rollen

### A – Gemini-Pipeline & Qualität (Technik)
Dateien: `app/pipeline.py`, `app/prompts.py`, `app/schemas.py`, `app/gemini.py`
- 5 Demo-Fälle mit echten Fotos durchspielen (siehe README) und Prompts nachschärfen, bis Vorlage und Maße stimmen.
- Maßschätzung per Referenzobjekt verbessern (z. B. zweiter Gemini-Aufruf nur zum Messen, mit Bounding Boxes).
- Loop robuster machen: Review-Vorschläge außerhalb der Parametergrenzen, Pingpong zwischen Versionen vermeiden.

### B – CAD-Vorlagen & Druck-Checks (Technik + Praxis)
Dateien: `app/scad_templates/*`, `app/templates_registry.py`, `app/checks.py`
- Neue Vorlagen `plate_guard` und `button_hook` im UI testen (Bibliothek → Vorlage öffnen → Checks).
- Mindestens 1 Teil real drucken (Schlüsseldreher!) – ein echtes Teil in der Hand ist der stärkste Pitch-Moment.
- Weitere Vorlagen nach Bedarf: Stifthalter, Reißverschlusshilfe, Tablet-/Handyhalter.

### C – Frontend & 3D-Animation (Wow)
Dateien: `web/*`
- **Bug:** „Benutzung zeigen“ wirft `Cannot destructure property 'side' of 'spec'` in `web/usage_anim.js` (`mat()`), zuerst fixen. Testseite: `/static/anim_test.html`.
- Animationen für weitere Vorlagen, Feinschliff am Loop-Timeline-Design, Mobile-Ansicht.
- Barrierefreiheit (Tastatur, Screenreader) – passt zum Thema und fällt der Jury auf.

### D – KI-Visualisierung, Demo & Pitch (Wow + Praxis)
Dateien: `app/visualize.py`, `demo_inputs/`, Pitch-Folien
- **Problem:** Das Omni-Video zeigt unrealistische Bewegungen. Ideen:
  1. Bewegung im Prompt hart einschränken (Kamera statisch, Schlüssel bleibt im Schloss, nur 90°-Drehung des Handgelenks, nichts anderes bewegt sich).
  2. Kürzer: 4–5 s statt 8 s.
  3. Start- und Endbild näher beieinander (nur die Drehung unterscheidet sich).
  4. Fallback: nur Vorher/Nachher-Bilder + three.js-Animation zeigen, Video weglassen.
- Echte Fotos für die Demo-Fälle sammeln, Backup-Ergebnisse vorab erzeugen (Link `?job=<id>`).
- Pitch: Problem (Hilfsmittel sind teuer/langsam) → Live-Demo → Loop-Timeline → echtes Druckteil.

## Reihenfolge bis zur Abgabe

1. Animation-Bug fixen (C) und Demo-Fälle durchtesten (A) – parallel.
2. Video-Realismus (D), Teil drucken (B).
3. Feature-Freeze ~1 h vor Abgabe, dann nur noch Backup-Video aufnehmen und Pitch proben.
