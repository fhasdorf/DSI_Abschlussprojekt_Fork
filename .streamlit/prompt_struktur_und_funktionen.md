Analysiere die komplette Projektstruktur und erstelle eine Datei `PROJECT_OVERVIEW.md` im Projekt-Root mit folgendem Inhalt:

## 1. Projektübersicht
- Kurze Beschreibung des Projekts (abgeleitet aus README, package.json, pyproject.toml o.ä.)
- Verwendete Sprachen, Frameworks und wichtigste Dependencies
- Einstiegspunkt(e) der Anwendung

## 2. Ordner- und Dateistruktur
Erstelle einen Verzeichnisbaum als Code-Block (```text ... ```), der die komplette Struktur abbildet. 
- Ignoriere: node_modules, .git, .venv, venv, __pycache__, dist, build, .next, .cache, *.lock, .DS_Store, coverage, .pytest_cache, .mypy_cache
- Hinter jedem Ordner/jeder Datei: eine kurze Beschreibung (1 Zeile) was darin enthalten ist bzw. wofür sie dient

Beispielformat:
├── src/
│   ├── api/              # REST-Endpunkte
│   │   └── users.py      # User-CRUD-Operationen
│   └── models/           # Datenmodelle

## 3. Funktionen, Klassen und Module
Pro relevanter Quellcode-Datei eine Sektion mit:
- **Pfad zur Datei**
- Tabelle mit Spalten: `Name | Typ (Function/Class/Method) | Signatur | Kurzbeschreibung`
- Bei Klassen: Methoden eingerückt darunter
- Docstrings/Kommentare nutzen, um Kurzbeschreibung abzuleiten; falls keine vorhanden, aus Code-Logik schließen

## 4. Abhängigkeiten zwischen Modulen
Kurze Auflistung der wichtigsten Import-Beziehungen (welches Modul nutzt welches).

## 5. Offene TODOs / FIXMEs
Grep nach `TODO`, `FIXME`, `XXX`, `HACK` im Code und liste sie mit Datei:Zeile auf.

## Vorgaben
- Sprache: Deutsch
- Keine Code-Snippets im Output (nur Signaturen)
- Sortiere Dateien alphabetisch innerhalb ihres Ordners
- Falls das Projekt sehr groß ist (>50 Quellcode-Dateien), gruppiere nach Modulen statt jede Datei einzeln aufzulisten
- Erzeuge die Datei am Ende mit dem `Write`-Tool, gib mir danach eine kurze Zusammenfassung im Chat, was du gefunden hast