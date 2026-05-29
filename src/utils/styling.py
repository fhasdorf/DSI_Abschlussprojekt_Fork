# -*- coding: utf-8 -*-
"""
Globales Styling fuer alle matplotlib-Charts der App.

Konzept:
Matplotlib hat einen globalen Konfigurations-Store (`plt.rcParams`).
Was hier einmal gesetzt wird, gilt fuer JEDE Figure, die danach im selben
Python-Prozess erzeugt wird - unabhaengig davon, in welcher Datei sie
erstellt wird.

Konvention im Projekt:
- `apply_global_style()` wird EINMAL ganz oben in app.py aufgerufen.
- Chart-Funktionen in `charts_*.py` setzen KEINE eigenen Farben/Schriften,
  damit alle Plots optisch konsistent bleiben.
- Pro-Chart-Anpassungen (z.B. spezielle Saison-Farben) sind okay, sollten
  aber bewusst gesetzt sein.

Farbschema:
Dark Mode passend zum Streamlit-Standard-Hintergrund (#0E1117).
Akzentfarbe Tuerkis (#03B5B0) als Anlehnung an den Streamlit-Primary-Color.
"""

import matplotlib.pyplot as plt
from cycler import cycler


# ------------------------------------------------------------
# Farbpalette – zentral ausgelagert, damit alle Chart-Module
# (charts_ozon.py u. a.) dieselben Farben importieren koennen.
# ------------------------------------------------------------
COLORS = {
    # Hintergrund- und Oberflächenfarben (Dark Mode, passend zu Streamlit)
    "background":  "#0E1117",   # Streamlit-Standard-Hintergrund
    "surface":     "#262730",   # Streamlit-Sidebar-Hintergrund
    # Textfarben
    "text":        "#FAFAFA",   # Primärtext (hell auf dunklem Grund)
    "text_muted":  "#888888",   # Sekundärtext, gedämpfte Liniendarstellung
    # Rasterlinien
    "grid":        "#444444",   # Gitterlinienfarbe in Charts
    # Akzentfarben
    "accent":      "#03B5B0",   # Türkis – Streamlit-Primary-Anlehnung; Hauptakzent
    "accent_warm": "#FF9800",   # Orange – zweiter Akzent (Temperatur, Wärme)
    # Semantische Farben (Ampellogik)
    "good":        "#4CAF50",   # Grün – Werte im Normbereich / ländliche O₃-Kurve
    "bad":         "#E63946",   # Rot – Grenzwertüberschreitung / NO₂-Kurve
}

# Standard-Farbzyklus fuer mehrere Linien/Balken im selben Plot.
# Wird als ``axes.prop_cycle`` in plt.rcParams gesetzt; Reihenfolge entspricht
# der visuellen Priorität (Hauptlinie zuerst).
PALETTE = [
    "#03B5B0",   # türkis  – Hauptlinie / erste Serie
    "#FF9800",   # orange  – zweite Serie
    "#4CAF50",   # grün    – dritte Serie
    "#E63946",   # rot     – vierte Serie
    "#9C27B0",   # violett – fünfte Serie
    "#2196F3",   # blau    – sechste Serie
    "#FFC107",   # gelb    – siebte Serie
    "#7f7f7f",   # grau    – achte Serie / neutrale Referenz
]


def apply_global_style() -> None:
    """
    Setzt die globalen matplotlib-Standardwerte für die gesamte App.

    Schreibt alle relevanten Einträge in ``plt.rcParams``. Der Aufruf muss
    einmalig ganz oben in app.py erfolgen, bevor irgendeine Figure erzeugt
    wird – danach gelten die Einstellungen für JEDE Figure im selben Prozess,
    unabhängig von der Datei, in der sie erstellt wird.

    Seiteneffekte
    -------------
    - ``plt.rcParams`` wird dauerhaft verändert (für die Laufzeit des Prozesses).
    - Kein Rückgabewert; keine Figure wird erzeugt.
    """
    plt.rcParams.update({
        # --- Hintergrund ---
        "figure.facecolor":    COLORS["background"],
        "axes.facecolor":      COLORS["background"],
        "savefig.facecolor":   COLORS["background"],

        # --- Achsen ---
        "axes.edgecolor":      COLORS["text_muted"],
        "axes.labelcolor":     COLORS["text"],
        "axes.titlecolor":     COLORS["text"],
        "axes.titlesize":      13,
        "axes.titleweight":    "bold",
        "axes.titlepad":       12,
        "axes.labelsize":      11,
        "axes.spines.top":     False,
        "axes.spines.right":   False,

        # --- Ticks ---
        "xtick.color":         COLORS["text"],
        "ytick.color":         COLORS["text"],
        "xtick.labelsize":     9,
        "ytick.labelsize":     9,

        # --- Grid ---
        "axes.grid":           True,
        "grid.color":          COLORS["grid"],
        "grid.linestyle":      ":",
        "grid.linewidth":      0.6,
        "grid.alpha":          0.6,

        # --- Text & Legende ---
        "text.color":          COLORS["text"],
        "font.family":         "sans-serif",
        "font.size":           10,
        "legend.frameon":      False,
        "legend.fontsize":     9,
        "legend.labelcolor":   COLORS["text"],

        # --- Linien & Marker ---
        "lines.linewidth":     2.0,
        "lines.markersize":    5,

        # --- Farbzyklus fuer mehrere Serien im selben Plot ---
        "axes.prop_cycle":     cycler(color=PALETTE),

        # --- Figure-Defaults ---
        "figure.figsize":      (10, 5),
        "figure.dpi":          100,
        "figure.autolayout":   True,   # ruft tight_layout() automatisch auf
    })
