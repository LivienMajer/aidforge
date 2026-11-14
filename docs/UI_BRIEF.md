# UI-Brief: „Viewer als Bühne“ – Redesign v3 (für Antigravity)

**Scope:** nur `web/index.html`, `web/style.css`, `web/app.js`. Nicht anfassen: `app/*` (Backend),
`web/usage_anim.js`, `web/storyboard.js`. Server läuft unter http://localhost:8000; Testjob:
http://localhost:8000/?job=dbea3f6b6b (Schlüsseldreher mit Storyboard-Bildern).

## Ziel

Das 3D-Fenster mit Animation ist das Herzstück und bleibt wie es ist. Alles andere wird ruhiger,
kürzer und professioneller. **Keine Textwände, nichts Abgeschnittenes.**

## Festgelegte Entscheidungen

1. **Feste Seitenleiste entfällt → Schubladen (Drawer).**
   - Schmale vertikale Icon-Leiste am rechten Viewer-Rand: Analyse · Parameter · Prüfung ·
     Visualisierung · Druck · Code (Icon + Tooltip, aktiver Zustand sichtbar).
   - Klick öffnet **genau ein** Panel als Drawer (~400 px) über/neben dem Viewer; erneuter Klick, ✕ oder
     Esc schließt. Viewer nutzt sonst die volle Fläche.
   - Mobil (< 900 px): Drawer = Bottom-Sheet (max. 75 vh), Icon-Leiste horizontal unter dem Viewer.
2. **Ergebnis-Karte im Viewer** (oben links, schwebend, kompakt): Gerätename, `plan.brief.one_liner`,
   3 Kennzahlen als Chips (Maße · ≈ Gewicht · Druckbarkeit x/y ✓), Vorlage/Custom-Badge.
   Der STL-Download bleibt prominent in der Viewer-Toolbar.
3. **Kurztexte statt Absätze.** Das Backend liefert jetzt `job.plan.brief`:
   ```
   brief.one_liner            Nutzen in ≤ 12 Wörtern
   brief.limitation_chips[]   2–4 Einschränkungen, je ≤ 4 Wörter  → als Chips
   brief.requirement_bullets[] 3–5 Anforderungen, je ≤ 8 Wörter    → Häkchen-Liste
   brief.usage_bullets[]      2–4 Nutzungsschritte                  → nummerierte Kurzliste
   brief.safety_bullets[]     1–3 Hinweise                          → dezente Hinweisbox
   brief.print_line           z. B. "PETG · 0.2 mm · 40 % Infill · keine Stützen"
   ```
   Langtexte (`task_summary`, `observed_in_media`, `root_problem`, `how_it_helps`, …) nur noch hinter
   einem „Mehr anzeigen“-Aufklapper. **Fallback:** ältere Jobs haben leere `brief`-Felder → dann die
   Langtexte auf ~2 Zeilen kürzen (line-clamp) + „Mehr“.
4. **Panels inhaltlich:**
   - *Analyse:* Einschränkungs-Chips, Anforderungen (✓-Liste), Maße als kompakte Tabelle
     (Name · Wert mm · Quelle als Icon: 👤 Angabe / 📏 Referenz / ≈ geschätzt), Maßstab-Zeile
     („📏 1-€-Münze erkannt“), Rest unter „Mehr“.
   - *Parameter:* Slider kompakt (Label + Wert in einer Zeile, Beschreibung als Tooltip),
     „Neu bauen“ sticky am Panel-Ende.
   - *Prüfung:* Druck-Checks als kompakte Liste mit Status-Punkt + Wert; Details per Tooltip/Aufklapper;
     Gemini-Kritik als 1–2 Zeilen + „Mehr“.
   - *Visualisierung:* Storyboard (`job.visual.storyboard[]`, je `url`, `step`, `caption`) als **großer
     Filmstreifen** mit Lightbox (Klick = groß, Pfeiltasten), nicht als Mini-Thumbnails. Buttons:
     primär „Realistische Bildstrecke erzeugen“ (`#vis-story`), sekundär Vorher/Nachher, Video als
     kleiner „experimentell“-Link.
   - *Druck:* `brief.print_line` groß, darunter Kennzahlen; Nutzung/Sicherheit als Kurzlisten.
   - *Code:* unverändert (Mono, kopierbar).
5. **Loop-Timeline** bleibt als schmale Leiste direkt unter dem Viewer, immer sichtbar
   (Chips v1 → v2 …); Details zur Iteration als Popover beim Klick statt Textblock darunter.
6. **„Anpassen“-Eingabe** als schlanke Zeile unter der Timeline (ein Input + Button), nicht im Panel.
7. **Look – professioneller, hell als Standard, Dark Mode poliert:**
   - Eine Akzentfarbe (Teal), keine Verläufe/Glows im Hintergrund, keine Schatten-Orgien;
     Flächen: Weiß/Grau-50, 1 px Linien.
   - 8-px-Abstandsraster, 3 Textgrößen (12/14/18) + 1 Titelgröße, Zahlen in Mono (`tabular-nums`).
   - Einheitliche Line-Icons (Lucide-Stil, inline SVG), dezente Hover-/Focus-States (Focus sichtbar!).
   - Ladezustände: Skeletons / dünner Fortschrittsbalken statt Text.
   - Dark Mode mit denselben Komponenten, Modell bleibt orange.

## Muss erhalten bleiben

- Alle Funktionen: Upload (inkl. Video-Standbild), Mikrofon-Eingabe, Generieren, Vorlage öffnen,
  gespeicherte Ergebnisse, `?job=<id>`, Neu bauen, Anpassen, Benutzung zeigen (Animation), Drehen,
  Gitter, Vollbild, Filamentfarben, STL/.scad-Download, Storyboard, Vorher/Nachher, Video, DE/EN, Theme.
- API-Vertrag: `GET /api/jobs/{id}` (Felder siehe `Job.to_dict()` in `app/pipeline.py`), nur lesen.
- Barrierefreiheit: Tastatur bedienbar (Tab, Esc schließt Drawer), `aria-expanded`/`aria-controls`
  an Icon-Leiste, Kontraste ≥ 4.5:1.

## Abnahme

1. Startseite, `?job=dbea3f6b6b`, Vorlage „Key turner“ öffnen → Animation, Neu bauen.
2. Jedes der 6 Panels öffnen/schließen (Maus + Esc); nirgends abgeschnittener Text oder Textwand
   ohne „Mehr“.
3. Storyboard-Lightbox mit 3 Bildern bei `?job=dbea3f6b6b`.
4. Hell/Dunkel, DE/EN, 1280×800 (Timeline ohne Scrollen sichtbar), 375 px mobil ohne horizontales
   Scrollen, 0 Konsolenfehler.

---

## Nachtrag: Personalisierung & Demo-Fälle (neu im Backend)

**Neue Felder in `job.plan`** (ältere Jobs: leer → Abschnitt ausblenden):
- `functional_assessment`: `condition`, `usable_hand`, `grip_status`, `range_of_motion`, `tremor`,
  `strength`, `hand_size_mm`, `compensations[]`, `evidence[]`.
  `evidence[]` = `{source: video|photo|text, ref: "0:03" | "Foto 2", observation, limitation, design_consequence}`.
- `parameter_rationale[]` = `{name, value, reason}` – warum dieser Wert für genau diese Person.
- `persona_story` – 2 Sätze aus Sicht der Person.

**Darstellung (Vorschlag):**
- Panel *Analyse* beginnt mit einer **„Befund“-Karte**: Griff-Status als Ampel-Chips (ok / schwach / fehlt),
  Tremor, nutzbare Hand. Darunter die **Belege als Timeline**: Zeitstempel-Chip („▶ 0:03“) → Beobachtung →
  Pfeil → Design-Konsequenz. Klick auf den Zeitstempel springt im hochgeladenen Video an die Stelle
  (Video-Vorschau im Panel; Medien eines Demo-Falls liegen unter `media_urls`, s. u.).
- Panel *Parameter*: pro Regler ein kleines **„Warum?“**-Icon mit `parameter_rationale.reason` als Tooltip.
- `persona_story` als Zitat in der Ergebnis-Karte bzw. oben im Analyse-Panel.

**Demo-Fälle (für den Startbildschirm, ein Klick):**
- `GET /api/cases` → `[{id, title: {de, en}, impairment, activity, notes, media[], media_urls[], expected_template}]`
- `POST /api/cases/{id}/run` mit `{"language": "de", "review": true}` → `{job_id}` (dann wie gewohnt pollen).
- Vorhanden: `rheuma_key`, `parkinson_spoon`, `tetra_toothbrush` (Testmedien sind KI-generiert und werden
  durch echte Aufnahmen mit gleichem Dateinamen ersetzt).
- Vorschlag: auf dem Start-Composer 3 Karten „Beispiel ausprobieren“ mit Vorschaubild (`media_urls[0]`) + Titel.
