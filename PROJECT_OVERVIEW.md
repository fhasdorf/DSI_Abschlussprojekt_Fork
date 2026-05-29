# PROJECT_OVERVIEW – Ozonparadoxon: Wetter- und Luftqualitätsanalyse Nürnberg

> Automatisch generiert am 2026-05-28

---

## 1. Projektübersicht

Das Projekt ist ein interaktives Streamlit-Dashboard, das das **Ozon-Paradoxon** im Großraum Nürnberg datenbasiert untersucht: Warum sind Ozonwerte in der Stadt trotz intensiverer Schadstoffemissionen oft niedriger als auf dem Land? Kern der Analyse ist die photochemische Titration von O₃ durch frisches NO aus dem Kfz-Verkehr. Der Datensatz umfasst stündliche Wetter- und Schadstoffmessungen von 1980 bis 2024 (ca. 394.000 Zeilen), ergänzt durch DWD-Referenzdaten der ländlichen Station Tiefenbach/Bayern.

Die App gliedert sich in neun Tabs: Jahreskennzahlen im Vergleich zu WHO-Grenzwerten, Datenbasis-Inspektion, Langzeitentwicklung der Schadstoffe, Ozon-Paradoxon-Visualisierung mit Stadt-Land-Vergleich, sowie vier geplante Analyse-Tabs (Korrelation, Regression, Random Forest, Vorhersage). Ein News-Tab lädt aktuelle Klimameldungen per RSS-Feed live ein.

### Sprachen, Frameworks und Dependencies

| Kategorie | Technologie |
|---|---|
| Sprache | Python 3.x |
| Dashboard / UI | Streamlit ≥ 1.36 |
| Datenverarbeitung | pandas ≥ 2.2, pyarrow ≥ 15.0 |
| Visualisierung | matplotlib ≥ 3.8, seaborn ≥ 0.13, cycler ≥ 0.12 |
| Datenformat | Apache Parquet (snappy-komprimiert) |
| News-Tab | feedparser ≥ 6.0, requests ≥ 2.31 |
| Notebooks / API | jupyter ≥ 1.0, requests-cache ≥ 1.2, retry-requests ≥ 2.0, numpy ≥ 1.26 |
| Konfiguration | Streamlit TOML (`.streamlit/config.toml`) |

### Einstiegspunkte

| Datei | Befehl | Zweck |
|---|---|---|
| [app.py](app.py) | `streamlit run app.py` | Startet das interaktive Dashboard |
| [convert_to_parquet.py](convert_to_parquet.py) | `python convert_to_parquet.py` | Einmalige CSV→Parquet-Konvertierung (Hauptdatensatz) |
| [scripts/convert_to_parquet.py](scripts/convert_to_parquet.py) | `python scripts/convert_to_parquet.py` | Identisches Konvertierungsskript im scripts/-Ordner |
| [scripts/test_feeds.py](scripts/test_feeds.py) | `python scripts/test_feeds.py` | Health-Check aller RSS-Feed-URLs |
| [scripts/test_urls.py](scripts/test_urls.py) | `python scripts/test_urls.py` | Erweiterter URL-Check (BMUKN, Euractiv) |

---

## 2. Ordner- und Dateistruktur

```text
Abschlussprojekt_Ozon/
│
├── app.py                          # Streamlit-Haupt-App, Tab-Struktur, Daten-Loader
├── charts_ozon.py                  # Alle matplotlib-Chart-Funktionen (kein Streamlit-Code)
├── styling.py                      # Globale matplotlib-rcParams, Farbpalette COLORS
├── news.py                         # RSS-Feed-Loader (feedparser + requests), Feed-Definitionen
├── convert_to_parquet.py           # Einmaliges CSV→Parquet-Konvertierungsskript
├── requirements-frozen.txt         # Pinned Dependencies für das Projekt
│
├── data/                           # Datendateien (Rohdaten + aufbereitete Parquets)
│   ├── data.csv                    # Rohdaten: Stündliche Wetter- + Schadstoffwerte 1980–2024
│   ├── data.parquet                # Konvertierte Hauptdatei (aus data.csv, von app.py geladen)
│   ├── o3_dailymax_2016_2025_station_tiefenbach_bayern.parquet   # O₃-Tagesmaxima DWD-Station Tiefenbach
│   ├── o3_hitzetage_2018_station_tiefenbach_bayern.parquet       # Hitzetage 2018, Tiefenbach
│   └── o3_stundenwerte_2018_station_tiefenbach.parquet           # Stündliche O₃-Werte 2018, Tiefenbach
│
├── scripts/                        # Analyse-Notebooks und Hilfsskripte
│   ├── convert_to_parquet.py       # Identisch mit Root-Skript (Kopie für scripts/-Kontext)
│   ├── fh_df_info.ipynb            # Datenstruktur-Inspektion: Schema, dtypes, Spaltenliste
│   ├── fh_ozon_abfrage_api_open_meteo.ipynb   # Open-Meteo-API-Abfrage (historische Wetter-/Ozondaten)
│   ├── fh_chart_hitzetage_1980_2023.ipynb     # Balkendiagramm Hitzetage (>30 °C) pro Jahr
│   ├── fh_chart_ozonparadoxon.ipynb           # Explorativer Prototyp: Stadt vs. Land O₃-Vergleich
│   ├── fh_chart_ozonschere.ipynb              # Scatter-Regression: Temperatur vs. Ozon-Peaks (Sommer)
│   ├── fh_chart_schadstoffe_langzeitentwicklung.ipynb  # Langzeitreihe Schadstoffe + Temperaturanomalie
│   ├── fh_chart_titrationseffekt_rushhour_3tage.ipynb  # Titrationseffekt Sonntag vs. Werktag 2018
│   ├── fh_ozon_korrelationsmatrix_titration.ipynb      # Korrelationsmatrix + O₃/NO-Scatter (simuliertes NO)
│   ├── test_feeds.py               # Health-Check aller RSS-Feed-Kandidaten
│   └── test_urls.py                # Erweiterter HTTP-Check einzelner Feed-URLs
│
├── .streamlit/
│   ├── config.toml                 # Streamlit Dark-Theme (Farben synchron mit styling.py)
│   └── prompt_struktur_und_funktionen.md   # Interne Entwicklungsnotizen / Prompt-Dokumentation
│
└── .claude/
    └── settings.local.json         # Lokale Claude-Code-Konfiguration
```

---

## 3. Funktionen, Klassen und Module

### [app.py](app.py)

#### Funktionen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `load` | Function | `load() -> pd.DataFrame` | Lädt `data.parquet` (Hauptdatensatz, gecacht) |
| `load_tiefenbach_tagesmax` | Function | `load_tiefenbach_tagesmax() -> pd.DataFrame` | Lädt O₃-Tagesmaxima Tiefenbach 2016–2025 (gecacht) |
| `load_tiefenbach_stunden` | Function | `load_tiefenbach_stunden() -> pd.DataFrame` | Lädt stündliche O₃-Werte Tiefenbach 2018 (gecacht) |
| `load_all_parquets` | Function | `load_all_parquets() -> dict[str, pd.DataFrame]` | Lädt alle Parquet-Dateien aus `data/` als Dictionary |
| `showTab1` | Function | `showTab1() -> None` | Tab „Startseite": Jahres-Slider, Wetter- und Schadstoff-Kennzahlen vs. WHO |
| `showTab2` | Function | `showTab2() -> None` | Tab „Datenbasis": Parquet-Vorschau, Schema, Statistik und Missing Values |
| `showTab3` | Function | `showTab3() -> None` | Tab „Explorative Analyse": Langzeittrend Schadstoffe + Temperatur/Ozon |
| `showTab4` | Function | `showTab4() -> None` | Tab „Ozon-Paradoxon": Stadt-Land-Vergleich + Titrationseffekt Werktag vs. Sonntag |
| `showTab5` | Function | `showTab5() -> None` | Tab „Korrelationsanalyse": Platzhalter (geplant) |
| `showTab6` | Function | `showTab6() -> None` | Tab „Multiple Regression": Platzhalter (geplant) |
| `showTab7` | Function | `showTab7() -> None` | Tab „Random Forest": Platzhalter (geplant) |
| `showTab8` | Function | `showTab8() -> None` | Tab „Vorhersage": Platzhalter (geplant) |
| `showTab9` | Function | `showTab9() -> None` | Tab „News-API": RSS-Feeds mit Sprach- und Quellenauswahl |

#### Modulkonstanten

| Name | Typ | Beschreibung |
|---|---|---|
| `custom_svg` | `str` | Inline-SVG für das Streamlit-Page-Icon (Balkendiagramm-Symbol) |
| `dfOrginal` | `pd.DataFrame` | Globaler Haupt-DataFrame (aus `load()`) – von allen Tab-Funktionen genutzt |

---

### [charts_ozon.py](charts_ozon.py)

#### Funktionen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `_saison_aus_monat` | Function | `_saison_aus_monat(monat: int) -> str` | Bildet meteorologische Saison aus Monatszahl ab |
| `berechne_langzeit_veraenderung` | Function | `berechne_langzeit_veraenderung(df: pd.DataFrame, spalte: str, fenster: int = 3) -> dict` | Berechnet prozentuale Veränderung über den Messzeitraum (Fenster-Mittelwert) |
| `tagesgang_nach_saison` | Function | `tagesgang_nach_saison(df: pd.DataFrame) -> plt.Figure` | Liniendiagramm: mittlere O₃-Konzentration je Tagesstunde, nach Jahreszeit |
| `langzeit_primaere_schadstoffe` | Function | `langzeit_primaere_schadstoffe(df: pd.DataFrame) -> plt.Figure` | Liniendiagramm: Jahresmittel NO₂, PM10, PM2.5 über gesamte Zeitspanne |
| `langzeit_temperatur_ozon` | Function | `langzeit_temperatur_ozon(df: pd.DataFrame) -> plt.Figure` | Doppelachsen-Liniendiagramm: Jahresmittel Temperatur + Ozon |
| `ozonparadoxon` | Function | `ozonparadoxon(df_stadt: pd.DataFrame, df_land: pd.DataFrame, jahr_von: int = 2016, jahr_bis: int = 2025, rolling_window: int = 30) -> plt.Figure` | Langzeitvergleich O₃ Stadt (Nürnberg) vs. Land (Tiefenbach) mit NO₂ und Temperatur |
| `_titration_zweitageplot` | Function | `_titration_zweitageplot(df_merged: pd.DataFrame, tage: dict) -> plt.Figure` | Interner Helper: rendert zwei Tage nebeneinander mit O₃/NO₂/Sonnenschein |
| `_baue_titrationsdaten` | Function | `_baue_titrationsdaten(df_stadt: pd.DataFrame, df_land: pd.DataFrame) -> pd.DataFrame` | Bereitet das Merge-DataFrame für Titrations-Plots vor (Timestamp-Join) |
| `titration_wettergematcht` | Function | `titration_wettergematcht(df_stadt: pd.DataFrame, df_land: pd.DataFrame) -> plt.Figure` | Titrationseffekt bei nahezu identischem Wetter: Di 24.07. vs. So 19.08.2018 |

#### Modulkonstanten

| Name | Typ | Beschreibung |
|---|---|---|
| `SAISON_REIHENFOLGE` | `list[str]` | Feste Reihenfolge der Jahreszeiten für Plot-Legenden |
| `SAISON_FARBEN` | `dict[str, str]` | Farbzuordnung Jahreszeit → Hex-Farbe (aus `COLORS` des Styling-Moduls) |
| `COLORS` | `dict` | Re-Export aus `styling.COLORS` (Kurzimport für Farbkonsistenz) |

---

### [styling.py](styling.py)

#### Funktionen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `apply_global_style` | Function | `apply_global_style() -> None` | Setzt alle globalen matplotlib-rcParams einmalig für die gesamte App |

#### Modulkonstanten

| Name | Typ | Beschreibung |
|---|---|---|
| `COLORS` | `dict[str, str]` | Zentrales Farbschema (Dark Mode): background, surface, text, accent, good, bad, … |
| `PALETTE` | `list[str]` | Standardfarbzyklus (8 Farben) für mehrere Serien im selben Plot |

---

### [news.py](news.py)

#### Klassen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `Feed` | Class | `@dataclass Feed` | Datenklasse für einen RSS-Feed: `name`, `url`, `sprache`, `quelle` |

#### Funktionen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `lade_feed` | Function | `lade_feed(url: str, max_eintraege: int = 5) -> list[dict]` | Lädt einen RSS-Feed und gibt normalisierte Einträge zurück (gecacht, TTL 1 h) |
| `feeds_nach_sprache` | Function | `feeds_nach_sprache(sprache: Sprache) -> list[Feed]` | Filtert die globale Feed-Liste nach Sprache |

#### Modulkonstanten

| Name | Typ | Beschreibung |
|---|---|---|
| `Sprache` | `TypeAlias` | `Literal["de", "en"]` – erlaubte Sprachcodes |
| `FEEDS` | `list[Feed]` | Verifizierte RSS-Feeds (tagesschau, DW, Carbon Brief, The Guardian) |
| `_HEADERS` | `dict[str, str]` | Browser-User-Agent-Header für HTTP-Requests (umgeht Cloudflare-Blocks) |

---

### [convert_to_parquet.py](convert_to_parquet.py)

#### Funktionen

| Name | Typ | Signatur | Kurzbeschreibung |
|---|---|---|---|
| `konvertiere` | Function | `konvertiere() -> None` | Liest `data.csv`, setzt Datentypen, validiert Spalten und schreibt `data.parquet` |

#### Modulkonstanten

| Name | Typ | Beschreibung |
|---|---|---|
| `BASE_DIR` | `Path` | Projektverzeichnis (Elternverzeichnis der Skriptdatei) |
| `CSV_PFAD` | `Path` | Pfad zur Quelldatei `data/data.csv` |
| `PARQUET_PFAD` | `Path` | Zielpfad `data/data.parquet` |
| `SPALTEN` | `list[str]` | Definierte Spaltenauswahl für die Parquet-Ausgabe (15 Spalten) |

---

### Notebooks in [scripts/](scripts/)

| Notebook | Inhalt |
|---|---|
| [fh_df_info.ipynb](scripts/fh_df_info.ipynb) | Datenstruktur-Inspektion des Rohdatensatzes: Schema, dtypes, Spaltenliste, `.info()` |
| [fh_ozon_abfrage_api_open_meteo.ipynb](scripts/fh_ozon_abfrage_api_open_meteo.ipynb) | Abruf historischer Wetter- und Ozondaten (1980–2026) über die Open-Meteo Archive API; Zusammenführung mit CSV-Altdaten |
| [fh_chart_hitzetage_1980_2023.ipynb](scripts/fh_chart_hitzetage_1980_2023.ipynb) | Balkendiagramm: Anzahl Hitzetage (>30 °C) pro Jahr in Nürnberg 1980–2024 |
| [fh_chart_ozonparadoxon.ipynb](scripts/fh_chart_ozonparadoxon.ipynb) | Explorativer Prototyp des Stadt-Land-Vergleichs (Nürnberg vs. Tiefenbach), 30-Tage-Rolling-Mean |
| [fh_chart_ozonschere.ipynb](scripts/fh_chart_ozonschere.ipynb) | Scatter-Regression Tagestemperatur vs. O₃-Tagesmaxima (Sommermonate); Ozonschere-Visualisierung |
| [fh_chart_schadstoffe_langzeitentwicklung.ipynb](scripts/fh_chart_schadstoffe_langzeitentwicklung.ipynb) | Langzeitreihe aller Schadstoffe + Temperaturanomalie (Referenz 1980–1989); drei Visualisierungsvarianten |
| [fh_chart_titrationseffekt_rushhour_3tage.ipynb](scripts/fh_chart_titrationseffekt_rushhour_3tage.ipynb) | Titrationseffekt: Sonntag vs. Werktag (August 2018), stündlicher O₃/NO₂-Verlauf mit Rushhour-Markierungen |
| [fh_ozon_korrelationsmatrix_titration.ipynb](scripts/fh_ozon_korrelationsmatrix_titration.ipynb) | Korrelationsmatrix (Temperatur, Sonnenschein, O₃, NO₂, synthetisches NO) + O₃/NO-Scatter |

---

## 4. Abhängigkeiten zwischen Modulen

```text
app.py
├── intern: styling          (apply_global_style, COLORS)
├── intern: charts_ozon      (alle Chart-Funktionen, berechne_langzeit_veraenderung)
├── intern: news             (Feed, FEEDS, lade_feed, feeds_nach_sprache, Sprache)
├── extern: streamlit        (UI, Caching, Tabs, Metriken, Fragments)
├── extern: pandas           (DataFrame-Laden aus Parquet)
├── extern: pathlib          (Pfadkonstruktion für data/)
└── extern: time             (sleep im Sidebar-Spinner)

charts_ozon.py
├── intern: styling          (COLORS, PALETTE – für konsistente Farben)
├── extern: matplotlib       (Figure-Erstellung, Axes, rcParams)
├── extern: matplotlib.dates (Achsenformatierung für Zeitreihen)
├── extern: matplotlib.patches (mpatches.Patch für Legenden-Proxy-Handles)
└── extern: pandas           (DataFrame-Operationen, Groupby, Merge, Rolling)

styling.py
├── extern: matplotlib       (plt.rcParams.update)
└── extern: cycler           (cycler() für Farbzyklus)

news.py
├── extern: feedparser       (RSS-Feed-Parsing)
├── extern: requests         (HTTP-Requests mit Browser-Headers)
├── extern: streamlit        (st.cache_data, st.warning)
└── stdlib: dataclasses, datetime, typing

convert_to_parquet.py
├── extern: pandas           (CSV lesen, Parquet schreiben mit pyarrow/snappy)
└── stdlib: sys, pathlib

scripts/test_feeds.py
├── extern: requests         (HTTP Health-Check)
└── extern: feedparser       (Entry-Count-Prüfung)

scripts/test_urls.py
├── extern: requests
└── extern: feedparser

Notebooks (scripts/*.ipynb)
├── extern: pandas, matplotlib, seaborn, numpy
├── extern: requests, requests_cache, retry_requests  (nur API-Notebook)
└── Daten: data/data.csv, data/*.parquet (relative Pfade aus scripts/)
```

---

## 5. Offene TODOs / FIXMEs

### Explizite Platzhalter im Code

| Datei | Zeile | Inhalt |
|---|---|---|
| [app.py](app.py#L407) | 407 | `st.info("🚧 Geplant: Korrelationsmatrix Wetter ↔ O₃ über die Jahre.")` |
| [app.py](app.py#L413) | 413 | `st.info("🚧 Geplant: OLS-Regression mit Wettergrößen als Prädiktoren.")` |
| [app.py](app.py#L419) | 419 | `st.info("🚧 Geplant: RandomForestRegressor inkl. Feature Importance.")` |
| [app.py](app.py#L424) | 424 | `st.info("🚧 Geplant: RandomForestRegressor inkl. Feature Importance.")` – identischer Text wie Zeile 419, vermutlich Duplikat |

### Leere Tab-Funktionen (nur Platzhalter-Text, keine Implementierung)

| Datei | Zeile | Funktion | Status |
|---|---|---|---|
| [app.py](app.py#L404) | 404–408 | `showTab5()` – Korrelationsanalyse | Nur `st.header` + `st.info`-Platzhalter |
| [app.py](app.py#L410) | 410–414 | `showTab6()` – Multiple Regression | Nur `st.header` + `st.info`-Platzhalter |
| [app.py](app.py#L416) | 416–420 | `showTab7()` – Random Forest | Nur `st.header` + `st.info`-Platzhalter |
| [app.py](app.py#L421) | 421–425 | `showTab8()` – Vorhersage | Nur `st.header` + `st.info`-Platzhalter |

### Sonstige Hinweise

| Datei | Befund |
|---|---|
| [scripts/convert_to_parquet.py](scripts/convert_to_parquet.py) | Duplikat von [convert_to_parquet.py](convert_to_parquet.py) im Root – ggf. Synchronisierung nötig |
| [charts_ozon.py](charts_ozon.py#L88) | `tagesgang_nach_saison` wird in keinem Tab aufgerufen (Beispiel-/Prototyp-Funktion) |
| [scripts/fh_ozon_korrelationsmatrix_titration.ipynb](scripts/fh_ozon_korrelationsmatrix_titration.ipynb) | NO-Werte werden synthetisch simuliert (`no2 * 0.8 - o3 * 0.2 + Rauschen`), da keine echten NO-Messdaten vorliegen |
