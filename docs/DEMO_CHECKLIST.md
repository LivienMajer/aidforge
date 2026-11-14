# Demo-Video – Checkliste (≈ 2:00, ein Fall: Schlüsseldreher)

Ziel: Ein Fall komplett durchgezogen – echtes Foto → Analyse → 3D-Modell → Bildstrecke an der
eigenen Tür → druckfertig im Slicer. Wir drucken nicht; „druckfertig“ beweisen Slicer + Passmaß-Check.

---

## 1. Vorbereitung Demo-Laptop

- [ ] Repo klonen: `git clone https://github.com/LivienMajer/aidforge` (oder `git pull`)
- [ ] Setup laut README: OpenSCAD installieren, `.venv` anlegen, `pip install -r requirements.txt`
- [ ] `.env` anlegen (Key von Livien bekommen, **nie committen**):
      `GEMINI_API_KEY=...` und `VIDEO_MODEL=gemini-omni-flash-preview`
- [ ] Server starten: `.venv\Scripts\python -m uvicorn app.main:app --port 8000` → http://localhost:8000
      (beide Pills oben rechts „Gemini“ und „OpenSCAD“ müssen grün sein)
- [ ] **Slicer installieren** (kostenlos, ohne Drucker nutzbar): PrusaSlicer (einfachste Wahl) oder
      Bambu Studio. Einen beliebigen Standard-Drucker als Profil wählen (z. B. Prusa MK4 oder Bambu A1),
      Material PETG.
- [ ] `.stl`-Dateien mit dem Slicer verknüpfen (Rechtsklick auf eine .stl → Öffnen mit → Slicer →
      „Immer“), damit der Download per Doppelklick direkt im Slicer landet.
- [ ] Browser: Lesezeichen/Tabs aus, Zoom 100 %, Vollbild (F11), Benachrichtigungen aus (Fokus-Modus),
      Downloads-Leiste sichtbar lassen.
- [ ] Bildschirmaufnahme: OBS Studio oder Windows Snipping Tool (Win+Shift+R), 1920×1080, 30 fps,
      Mikrofon nur an, wenn live gesprochen wird.

## 2. Fotos aufnehmen (am Vortag/vorab)

| Foto | Wie | Wofür |
|---|---|---|
| **A – Schlüssel + 1-€-Münze** | Schlüssel und Münze flach nebeneinander auf einer **einfarbigen, hellen** Fläche, Handy **senkrecht von oben** (parallel zur Fläche, sonst stimmt der Maßstab nicht), Tageslicht, kein Schatten über dem Schlüssel, beide füllen ~⅓ des Bildes. | Analyse + Maßstab (Gemini erkennt die Münze und misst den Schlüsselkopf) |
| **B – eigene Haustür mit Schloss** | Seitlich auf Hüfthöhe, Schloss und Klinke gut sichtbar, natürliches Licht, ruhiger Hintergrund. | Bildstrecke „an unserer Tür“ |
| **C – Problem-Szene (Video, 5–8 s)** | Hand (ältere Person mit Einverständnis, oder nachgestellt) dreht mühsam einen kleinen Schlüssel im Schloss. Ruhig, Nahaufnahme. | Einstieg ins Video |

- [ ] Schlüsselkopf zusätzlich mit Lineal messen und notieren (Breite × Länge × Dicke) – zum Vergleich mit
      der KI-Messung; im Video *nicht* eintippen, damit die Messung aus dem Foto sichtbar ist.
- [ ] Einverständnis aller gezeigten Personen einholen. Keine Gesichter nötig.

> **Wichtig:** Die App nutzt für die Bildstrecke das **erste hochgeladene Foto** als Szene. Für den
> Demo-Lauf also **Foto B (Tür) zuerst** und **Foto A (Schlüssel + Münze) als zweites** hochladen –
> beide gehen in die Analyse, die Tür wird zur Szene der Bildstrecke.

## 3. Demo-Lauf vorab (Generalprobe) und Backup

- [ ] Einmal komplett durchspielen: Fotos B + A hochladen →
      Einschränkung (per **Mikrofon** einsprechen): *„Rheumatoide Arthritis in beiden Händen, kaum Kraft
      im Pinzettengriff, Drehen des Handgelenks schmerzt“* →
      Aktivität: *„Die Haustür selbstständig aufschließen“* → **Hilfsmittel generieren**.
- [ ] Prüfen: Vorlage „Key turner“ gewählt? Maßstab „1-€-Münze“ erkannt? Passmaß-Checks grün?
      Gemessene Werte plausibel zum Lineal (± 1–2 mm)?
- [ ] Panel *Visualisierung* → **„Realistische Bildstrecke erzeugen“** (≈ 90 s). Drei Bilder an eurer Tür
      prüfen; bei Ausreißern einfach erneut erzeugen.
- [ ] URL des guten Laufs notieren: `http://localhost:8000/?job=<id>` = **Backup** (bleibt nach Neustart).
- [ ] STL herunterladen → im Slicer öffnen → **„Slice“** → Druckzeit, Gewicht, Filamentkosten notieren.
- [ ] Falls etwas schiefgeht: Fotos verbessern (Abschnitt 2), nicht den Code ändern.

## 4. Aufnahme – Ablauf (Rohmaterial, wird geschnitten)

| Zeit im Video | Szene | Aufnahme-Hinweis |
|---|---|---|
| 0:00–0:15 | Problem: Video C + Satz „Hilfsmittel sind teuer und brauchen Wochen.“ | Handy-Clip |
| 0:15–0:35 | Fotos hochladen, Einschränkung **einsprechen** (Mikrofon-Button), Aktivität tippen, Generieren | Bildschirm, echte Geschwindigkeit |
| 0:35–0:55 | Wartezeit: Fortschritt, Loop-Timeline, Checks werden grün | **im Schnitt 3–4× beschleunigen** |
| 0:55–1:20 | Ergebnis: 3D-Modell drehen, **„Benutzung zeigen“** (Schlüssel gleitet rein, Hebel dreht), Maßstab-Zeile „1-€-Münze erkannt“, Passmaß-Check groß, kurz einen Regler bewegen + Neu bauen | langsam, Maus ruhig |
| 1:20–1:35 | Bildstrecke Schritt 1 → 3 an der eigenen Tür (Lightbox, sobald das UI-Redesign drin ist) | ggf. Bilder im Schnitt vollflächig einblenden (liegen in `outputs/<id>/visual_v*/story_*.jpg`) |
| 1:35–1:50 | „STL herunterladen“ → Slicer öffnet sich → Slice → Druckzeit/Gewicht/Kosten | Slicer vorher einmal geöffnet (schneller Start) |
| 1:50–2:00 | 5-s-Montage weiterer Ergebnisse (Griffverdickung, Becherhalter, Zahnbürstenhalter) + Architektur-Grafik + Schlusssatz | Screenshots aus „Gespeicherte Ergebnisse“ |

**Schlusssatz:** „Vom Foto zum druckfertigen Hilfsmittel in unter zwei Minuten – für etwa einen Euro
Material statt Wochen Wartezeit.“ (Preisvergleich mit gekauften Hilfsmitteln nur mit echter Quelle.)

## 5. Montage-Material (weitere Ergebnisse)

- [ ] Je 1 Lauf mit Foto für: Griffverdickung (Tremor, Löffel), Becherhalter (Tremor, Trinken),
      eigenes CAD-Design (Halbseitenlähmung, Zahnpasta auf Zahnbürste – zeigt freien CAD-Code).
- [ ] Je einen Screenshot vom 3D-Viewer machen (helles Theme, Animation läuft).

## 6. Schnitt

- [ ] Tool: CapCut, DaVinci Resolve (kostenlos) oder Clipchamp (in Windows enthalten).
- [ ] Wartezeiten beschleunigen und mit kleinem Label „3× Geschwindigkeit“ kennzeichnen (ehrlich bleiben).
- [ ] Untertitel für alles Gesprochene (Barrierefreiheit – passt zum Thema).
- [ ] Ruhige Hintergrundmusik, leise; Gesamtlänge ≤ 2:00; Export 1080p MP4.
- [ ] Am Ende: Projektname, Team, Repo-Link.

## 7. Notfallplan

- API langsam/weg → Backup-URL `?job=<id>` öffnen und das fertige Ergebnis zeigen.
- Bildstrecke misslungen → Vorher/Nachher-Bilder nutzen oder nur die 3D-Animation zeigen.
- Mikrofon klappt nicht → Text tippen.
