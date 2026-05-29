# -*- coding: utf-8 -*-
"""
Zentrale Pfad-Konstanten fuer das Projekt.

Alle Pfade werden relativ zum Projekt-Root aufgelöst, sodass das Projekt
verschiebbar bleibt. Importieren mit:
    from src.utils.paths import DATA_RAW, DATA_PROCESSED
"""

from pathlib import Path

# Projekt-Root: parents[2] = src/utils/ → src/ → Projektroot
BASE_DIR = Path(__file__).resolve().parents[2]

# Verzeichnisse
DATA_RAW       = BASE_DIR / "data" / "raw"        # Original-CSV-Rohdaten
DATA_PROCESSED = BASE_DIR / "data" / "processed"  # Parquet-Ausgabeverzeichnis

# Hauptdatensatz: ~394.000 stündliche Messwerte Nürnberg 1980–2024
# (DWD-Wetterdaten + UBA/LfU-Schadstoffmessungen, zusammengeführt)
CSV_HAUPTDATEN     = DATA_RAW       / "data.csv"
PARQUET_HAUPTDATEN = DATA_PROCESSED / "data.parquet"

# Ländliche Referenzstation Tiefenbach/Bayern (DWD-Station, O₃-Langzeitmessung)
# Wird im Ozon-Paradoxon-Modul als Gegenpol zur städtischen Nürnberger Messung verwendet.
PARQUET_TIEFENBACH_TAGESMAX  = DATA_PROCESSED / "o3_dailymax_2016_2025_station_tiefenbach_bayern.parquet"
# O₃-Tagesmaxima 2016–2025 (für den Langzeitvergleich Stadt vs. Land)

PARQUET_TIEFENBACH_HITZETAGE = DATA_PROCESSED / "o3_hitzetage_2018_station_tiefenbach_bayern.parquet"
# O₃-Werte an Hitzetagen (Tmax > 30 °C) 2018 – für Extremwert-Analysen

PARQUET_TIEFENBACH_STUNDEN   = DATA_PROCESSED / "o3_stundenwerte_2018_station_tiefenbach.parquet"
# Stündliche O₃-Werte 2018 – für den Titrationseffekt-Vergleich (Werktag vs. Sonntag)
