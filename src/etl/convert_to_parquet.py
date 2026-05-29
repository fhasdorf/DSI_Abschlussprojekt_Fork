# -*- coding: utf-8 -*-
"""
Einmaliges Skript: Konvertiert data/raw/data.csv -> data/processed/data.parquet.

Ausfuehrung (aus dem Projekt-Verzeichnis, in dem auch app.py liegt):
    python -m src.etl.convert_to_parquet

Voraussetzungen:
    pip install pandas pyarrow

Hintergrund:
- Die CSV bleibt in data/raw/ als Rohdaten-/Backup-Datei erhalten.
- Die Parquet-Datei landet in data/processed/ und wird von app.py geladen.
- Parquet behaelt Datentypen (datum -> datetime64, stunde -> int, o3 -> float)
  und ist deutlich kleiner und schneller zu laden als die CSV.

Wann das Skript erneut ausfuehren:
- Nach jedem Update der Rohdaten-CSV.
- Wenn neue Spalten hinzukommen oder Datentypen sich aendern.
"""

import sys
from pathlib import Path

import pandas as pd


# ------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------
# parents[2]: src/etl/ → src/ → Projektroot
BASE_DIR     = Path(__file__).resolve().parents[2]
CSV_PFAD     = BASE_DIR / "data" / "raw" / "data.csv"       # Rohdaten-Eingabe
PARQUET_PFAD = BASE_DIR / "data" / "processed" / "data.parquet"  # Ausgabe

# Spalten, die in die Parquet übernommen werden (Reihenfolge bleibt erhalten).
# Nicht gelistete Spalten der CSV (z. B. Qualitätsniveaus, interne IDs)
# werden bewusst weggelassen, um Dateigröße und Schema schlank zu halten.
SPALTEN = [
    "datum", "stunde", "temperatur", "luftfeuchtigkeit",
    "windgeschwindigkeit", "windrichtung", "luftdruck",
    "niederschlagshoehe_mm", "sonnenscheindauer_minuten",
    "relative_luftfeuchtigkeit", "gesamtbewoelkung",
    "no2", "o3", "pm10", "pm2x5",
]


def konvertiere() -> None:
    """
    Liest data/raw/data.csv ein, setzt Datentypen korrekt und schreibt
    data/processed/data.parquet (Snappy-komprimiert, ohne Index).

    Schritte
    --------
    1. CSV-Existenz prüfen – Abbruch mit sys.exit bei fehlender Datei.
    2. Datentypen setzen: ``datum`` → datetime64; ``datumstunde`` (falls vorhanden)
       → datetime64 aus Format ``%Y%m%d%H``.
    3. Spalten-Set validieren: Abbruch, wenn SPALTEN nicht vollständig in der CSV.
    4. Sanity-Check: Datentypen, Zeitraum und Fehlwert-Summe auf stdout.
    5. Parquet schreiben (engine=pyarrow, compression=snappy).
    6. Größenvergleich CSV vs. Parquet auf stdout.

    Seiteneffekte
    -------------
    - Schreibt ``PARQUET_PFAD`` (überschreibt ggf. vorhandene Datei).
    - Gibt Fortschritts- und Größeninfos auf stdout aus.
    - Legt ``data/processed/`` an, falls nicht vorhanden.
    """
    # --- 1. CSV-Existenz pruefen ---
    if not CSV_PFAD.exists():
        sys.exit(f"FEHLER: CSV nicht gefunden unter {CSV_PFAD}")

    print(f"Lese CSV:   {CSV_PFAD}")
    df = pd.read_csv(CSV_PFAD)
    print(f"  -> {len(df):,} Zeilen, {len(df.columns)} Spalten gelesen")

    # --- 2. Typen sauber setzen (das ist der Punkt, weshalb Parquet hilft) ---
    df["datum"] = pd.to_datetime(df["datum"])

    if "datumstunde" in df.columns:
        df["datumstunde"] = pd.to_datetime(
            df["datumstunde"].astype(str),
            format="%Y%m%d%H",
            errors="coerce",
        )

    # --- 3. Spalten-Set pruefen und ggf. einschraenken ---
    fehlend = [s for s in SPALTEN if s not in df.columns]
    if fehlend:
        sys.exit(f"FEHLER: Spalten fehlen in CSV: {fehlend}")

    df = df[SPALTEN].copy()

    # --- 4. Sanity-Check: kurze Datenuebersicht ---
    print("\nDatentypen:")
    for spalte, dtype in df.dtypes.items():
        print(f"  {spalte:<32} {dtype}")

    print(f"\nZeitraum: {df['datum'].min().date()} bis {df['datum'].max().date()}")
    print(f"Fehlwerte gesamt: {df.isna().sum().sum():,}")

    # --- 5. Parquet schreiben ---
    PARQUET_PFAD.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET_PFAD, engine="pyarrow", compression="snappy", index=False)

    # --- 6. Groessenvergleich ---
    csv_mb     = CSV_PFAD.stat().st_size / 1024 / 1024
    parquet_mb = PARQUET_PFAD.stat().st_size / 1024 / 1024
    faktor     = csv_mb / parquet_mb if parquet_mb else 0

    print(f"\nGeschrieben: {PARQUET_PFAD}")
    print(f"  CSV:     {csv_mb:7.2f} MB")
    print(f"  Parquet: {parquet_mb:7.2f} MB  ({faktor:.1f}x kleiner)")


if __name__ == "__main__":
    konvertiere()
