# AidForge – vom Alltagsproblem zum druckfertigen Hilfsmittel

Eingabe: **Foto/Video** + **Einschränkung** + **Aktivität** (getippt oder per Spracheingabe) →
Ausgabe: **druckfertiges 3D-Modell (STL + OpenSCAD)** eines Hilfsmittels, das genau diese Aktivität
ermöglicht – plus eine **KI-Visualisierung**, wie die echte Benutzung aussehen könnte.

## Pipeline

```
Foto/Video + Text (+ Sprache via gemini-3.5-transcribe)
   │
   ▼  1. Analyse  (gemini-4-hydrogen, multimodal, Structured Output → DesignPlan)
   │     Aufgabe, Beobachtung, Einschränkungen, Anforderungen,
   │     Maßstab über Referenzobjekt im Bild (Münze / Bankkarte / A4) → Maße in mm,
   │     Vorlage + Parameter ODER eigenes Design, Passmaß-Verknüpfungen, Animations-Briefing
   ▼  2. Design
   │     Vorlage  → parametrische .scad aus app/scad_templates/ (8 Ergotherapie-Hilfsmittel)
   │     Custom   → Gemini schreibt OpenSCAD-Code
   ▼  3. Kompilieren (OpenSCAD → STL); Kompilierfehler → Gemini repariert (max. 3 Versuche)
   ▼  4. Agentischer Loop (max. 2 Runden), jede Version bleibt sichtbar (v1 → Kritik → v2):
   │     a) deterministische Druck-Checks: geschlossenes Mesh, Einzelteile, Druckbett,
   │        Wandstärke per Raycasting, Überhänge, Auflagefläche, Passmaß Objekt ↔ Parameter
   │     b) Render aus 3 Blickwinkeln → Gemini-Kritik gegen Anforderungen + Check-Ergebnisse
   │     c) Fehler/Kritik → neue Parameter bzw. neuer Code → neu kompilieren
   ▼  UI: 3D-Viewer, Loop-Timeline, Parameter-Regler („Neu bauen“ ohne KI), Freitext-Anpassung,
         Benutzungs-Animation in three.js (ohne API), STL/.scad-Download
   ▼  Auf Knopfdruck: KI-Visualisierung
         Nano Banana: Startbild (Hand nutzt das Hilfsmittel in der Szene des Fotos) + Endbild (Aufgabe erledigt)
         Omni: 8-s-Video als Übergang Start → Ende, Render als Referenz
```

Ergebnisse werden in `outputs/<job>/job.json` gespeichert und nach einem Neustart wieder geladen.
Jedes Ergebnis ist per Link `http://localhost:8000/?job=<id>` direkt aufrufbar → **Demo-Backup**.

## Setup (Windows)

1. OpenSCAD installieren: `winget install --id OpenSCAD.OpenSCAD -e`
2. Python-Umgebung:
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
3. `.env` anlegen (siehe `.env.example`) mit `GEMINI_API_KEY=...` und
   `VIDEO_MODEL=gemini-omni-flash-preview`. **`.env` niemals committen, `.env.example` ohne Key lassen.**
4. Starten:
   ```
   .venv\Scripts\python -m uvicorn app.main:app --port 8000
   ```
   → http://localhost:8000

## Modelle (mit dem Hackathon-Key getestet)

| Schritt | Modell | Dauer |
|---|---|---|
| Analyse, Review, Anpassung | `gemini-4-hydrogen` | 15–40 s |
| CAD-Code | `gemini-4-hydrogen` (thinking medium) | ~30 s (carbon/high: ~10 min) |
| Start-/Endbild | `gemini-nano-banana-2.1` | ~20 s pro Bild |
| Video | `gemini-omni-flash-preview` (`gemini-omni-1.2-flash` gibt 404) | ~50 s |
| Spracheingabe | `gemini-3.5-transcribe` | wenige s |

## Projektstruktur

| Datei | Inhalt |
|---|---|
| `app/main.py` | FastAPI-Endpunkte: Jobs, Rebuild, Refine, Visualize, Transcribe, Vorlagen |
| `app/pipeline.py` | Analyse → Design → Kompilieren → Check/Review-Loop, Iterationen, Speicherung |
| `app/checks.py` | Deterministische Druckbarkeits-Checks (numpy) |
| `app/visualize.py` | Nano-Banana-Bilder + Omni-Video |
| `app/gemini.py` | Interactions-API-Wrapper, Transkription |
| `app/prompts.py`, `app/schemas.py` | Prompts und Structured-Output-Schemas |
| `app/cad.py` | OpenSCAD: säubern, Parameter einsetzen, kompilieren, rendern, Maße |
| `app/templates_registry.py`, `app/scad_templates/` | Vorlagen-Katalog + parametrische Modelle |
| `web/` | UI (Vanilla JS + three.js per CDN), `usage_anim.js` = Benutzungs-Animation |
| `scripts/smoke_visualize.py` | Manueller Test der Bild/Video-Generierung |
| `demo_inputs/` | Testfotos (z. B. Schlüssel mit 1-€-Münze, KI-generiert) |

## Demo-Szenarien

| Einschränkung | Aktivität | Bild | Erwartet |
|---|---|---|---|
| Rheumatoide Arthritis, schwacher Pinzettengriff | Haustür aufschließen | `demo_inputs/key_with_coin.jpg` | Schlüsseldreher, Maße per Münze |
| Tremor | Mit Löffel essen | Löffel | Schwere Griffverdickung |
| Tetraplegie C6, kein Faustschluss | Zähne putzen | Hand + Zahnbürste | Universalmanschette |
| Nur eine Hand (Schlaganfall) | Marmeladenglas öffnen | Glas von oben | Drehhilfe mit Hebel |
| Nur eine Hand | Essen vom Teller schieben | Teller | Tellerranderhöhung |
| Nur eine Hand | Hemd zuknöpfen | Hemd | Knöpfhilfe |
| Halbseitenlähmung | Zahnpasta auftragen | – | Eigenes CAD-Design (Zahnbürstenhalter) |
