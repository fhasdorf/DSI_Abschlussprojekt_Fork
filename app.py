# -*- coding: utf-8 -*-
# Schadstoff/Wetter-Korrelation am Beispiel der Stadt Nürnberg
# Solo-Projekt – Schwerpunkt: Ozon (O₃)

from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils import styling
import src.visualization.charts_ozon as co
from src.utils.paths import (
    PARQUET_HAUPTDATEN,
    PARQUET_TIEFENBACH_TAGESMAX,
    PARQUET_TIEFENBACH_STUNDEN,
    DATA_PROCESSED,
)

import news

# ============================================================
# 00 GLOBALES STYLING (einmalig fuer alle matplotlib-Charts)
# ============================================================
styling.apply_global_style()

# ============================================================
# 01 SEITENKONFIGURATION
# ============================================================
custom_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' height='24px' viewBox='0 -960 960 960' width='24px' fill='%231f1f1f'><path d='M131.5-131.5Q120-143 120-160v-40q0-17 11.5-28.5T160-240q17 0 28.5 11.5T200-200v40q0 17-11.5 28.5T160-120q-17 0-28.5-11.5Zm160 0Q280-143 280-160v-220q0-17 11.5-28.5T320-420q17 0 28.5 11.5T360-380v220q0 17-11.5 28.5T320-120q-17 0-28.5-11.5Zm160 0Q440-143 440-160v-140q0-17 11.5-28.5T480-340q17 0 28.5 11.5T520-300v140q0 17-11.5 28.5T480-120q-17 0-28.5-11.5Zm160 0Q600-143 600-160v-200q0-17 11.5-28.5T640-400q17 0 28.5 11.5T680-360v200q0 17-11.5 28.5T640-120q-17 0-28.5-11.5Zm160 0Q760-143 760-160v-360q0-17 11.5-28.5T800-560q17 0 28.5 11.5T840-520v360q0 17-11.5 28.5T800-120q-17 0-28.5-11.5ZM560-481q-16 0-30.5-6T503-504L400-607 188-395q-12 12-28.5 11.5T131-396q-11-12-10.5-28.5T132-452l211-211q12-12 26.5-17.5T400-686q16 0 31 5.5t26 17.5l103 103 212-212q12-12 28.5-11.5T829-771q11 12 10.5 28.5T828-715L617-504q-11 11-26 17t-31 6Z'/></svg>"

st.set_page_config(
    page_title="„Ozonparadoxon“: Wetter- und Luftqualitätsanalyse Nürnberg",
    page_icon=custom_svg,
    layout="wide",
)

# ============================================================
# 01.a PROJEKT-HEADER (ersetzt die frühere Sidebar)
# ============================================================


# ============================================================
# 02 DATEN LADEN (cached)
# ============================================================
@st.cache_data
def load():
    """
    Laedt die kombinierten Wetter- und Schadstoffdaten aus der Parquet-Datei.

    Die Parquet wird einmalig per `python -m src.etl.convert_to_parquet` aus der CSV
    erzeugt. Datentypen (datum, numerische Spalten) sind dort bereits korrekt
    gesetzt, daher reicht hier ein simples read_parquet.
    """
    if not PARQUET_HAUPTDATEN.exists():
        st.error(
            f"Parquet-Datei nicht gefunden: `{PARQUET_HAUPTDATEN.name}`. "
            "Bitte einmalig `python -m src.etl.convert_to_parquet` ausführen, "
            "um sie aus der CSV zu erzeugen."
        )
        st.stop()

    return pd.read_parquet(PARQUET_HAUPTDATEN)

@st.cache_data
def load_tiefenbach_tagesmax() -> pd.DataFrame:
    """
    Laedt die O₃-Tagesmaxima der DWD-Station Tiefenbach/Bayern (2016–2025).

    Wird fuer das Ozon-Paradoxon-Chart als laendliche Referenz benoetigt.
    """
    if not PARQUET_TIEFENBACH_TAGESMAX.exists():
        st.error(f"Parquet-Datei nicht gefunden: `{PARQUET_TIEFENBACH_TAGESMAX.name}`.")
        st.stop()

    return pd.read_parquet(PARQUET_TIEFENBACH_TAGESMAX)


@st.cache_data
def load_tiefenbach_stunden() -> pd.DataFrame:
    """
    Laedt die stuendlichen O₃-Messwerte der DWD-Station Tiefenbach/Bayern (2018).

    Wird fuer den Titrationseffekt-Vergleich (Sonntag vs. Werktag) benoetigt.
    """
    if not PARQUET_TIEFENBACH_STUNDEN.exists():
        st.error(f"Parquet-Datei nicht gefunden: `{PARQUET_TIEFENBACH_STUNDEN.name}`.")
        st.stop()

    return pd.read_parquet(PARQUET_TIEFENBACH_STUNDEN)


@st.cache_data
def load_all_parquets() -> dict[str, pd.DataFrame]:
    """
    Laedt alle Parquet-Dateien aus data/processed/ und gibt sie als Dictionary
    zurück (Dateiname → DataFrame).

    Nützlich für die Übersicht aller Datengrundlagen in Tab 2.
    """
    parquet_files = sorted(DATA_PROCESSED.glob("*.parquet"))

    if not parquet_files:
        st.warning("Keine Parquet-Dateien im data/processed/-Verzeichnis gefunden.")
        return {}

    return {p.name: pd.read_parquet(p) for p in parquet_files}

@st.cache_resource
def train_random_forest(_df: pd.DataFrame) -> dict:
    """
    Trainiert einen Random Forest zur O₃-Schaetzung und vergleicht ihn fair
    mit einem OLS-Modell auf identischem, ZEITBASIERTEM Test-Set.

    Methodischer Hinweis: Da eine stuendliche Zeitreihe vorliegt, wird NICHT
    zufaellig gesplittet (ein Zufallssplit fuehrt durch die Autokorrelation
    benachbarter Stunden zu Data Leakage und ueberoptimistischem R²), sondern
    chronologisch: die aeltesten 80 % der Zeitpunkte bilden das Training, die
    juengsten 20 % das Test-Set.

    Die Feature Importance wird als Permutation Importance auf den Testdaten
    bestimmt. Diese ist gegenueber der eingebauten (Gini-)Importance robuster
    bei korrelierten Praediktoren und misst den realen Vorhersageverlust auf
    ungesehenen Daten.

    @st.cache_resource sorgt dafuer, dass das (teure) Training nur EINMAL
    pro Session laeuft. Der Parameter heisst _df (fuehrender Unterstrich),
    damit Streamlit den grossen DataFrame nicht zu hashen versucht.

    Returns:
        dict mit Schluesseln:
            importances (pd.Series) – Permutation Importance je Feature, absteigend
            r2_rf, r2_ols (float)   – Bestimmtheitsmass auf dem Test-Set
            mae_rf, rmse_rf (float) – absolute Fehler des Random Forest (µg/m³)
    """
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

    ziel = "o3"
    features = [
        "no2", "pm10", "temperatur", "relative_luftfeuchtigkeit",
        "sonnenscheindauer_minuten", "windgeschwindigkeit",
        "luftdruck", "gesamtbewoelkung",
    ]

    # Chronologisch sortieren – Grundvoraussetzung fuer den zeitbasierten Split
    sub = _df[["datum", ziel] + features].dropna().sort_values("datum")
    X = sub[features]
    y = sub[ziel]

    # Zeitbasierter Schnitt: aelteste 80 % Training, juengste 20 % Test
    split_idx = int(len(sub) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Random Forest (nichtlinear)
    rf = RandomForestRegressor(
        n_estimators=100, max_depth=18, n_jobs=-1, random_state=42
    )
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    r2_rf = r2_score(y_test, y_pred_rf)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))

    # OLS auf demselben (zeitbasierten) Split – fairer Vergleich, gleiche Testdaten
    ols = LinearRegression()
    ols.fit(X_train, y_train)
    r2_ols = r2_score(y_test, ols.predict(X_test))

    # Permutation Importance auf den Testdaten (robuster als Gini-Importance)
    perm = permutation_importance(
        rf, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1
    )
    importances = pd.Series(
        perm.importances_mean, index=features
    ).sort_values(ascending=False)

    return {
        "importances": importances,
        "r2_rf": r2_rf,
        "r2_ols": r2_ols,
        "mae_rf": mae_rf,
        "rmse_rf": rmse_rf,
    }


# ============================================================
# 03 TAB-FUNKTIONEN
# ============================================================
@st.fragment
def showTab1():
    """
    Tab 1 – Startseite: Jahresübersicht mit Wetter- und Schadstoffkennzahlen.

    Rendert einen Jahres-Slider sowie vier Wetter- und vier Schadstoff-Metriken
    (inkl. Abweichung zu den WHO-Jahresgrenzwerten) für das gewählte Jahr.
    Liest und schreibt ``st.session_state.selected_year``.
    """
    st.header("Wenn saubere Luft mehr Ozon bedeutet")
    st.subheader("Das Ozon-Paradoxon im Datencheck. Eine datenbasierte Spurensuche zwischen Stadt und Land")
    st.markdown("---")
    # Jahres-Slider – Grenzen dynamisch aus den Echtdaten abgeleitet
    min_year = int(dfOrginal["datum"].dt.year.min())
    max_year = int(dfOrginal["datum"].dt.year.max())

    if "selected_year" not in st.session_state:
        st.session_state.selected_year = 2023

    selected_year = st.slider(
        "Jahresauswahl: Die Jahreskennzahlen zeigen auf einen Blick, ob ein besonders heißes, "
        "windiges oder sonniges Jahr vorlag – und die Entwicklung der Luftqualität im Vergleich "
        "zu den WHO-Grenzwerten über die Jahre.",
        min_value=min_year,
        max_value=max_year,
        value=st.session_state.selected_year,
        key="year_slider_tab1",
    )
    st.session_state.selected_year = selected_year

    df_year = dfOrginal[dfOrginal["datum"].dt.year == selected_year].copy()

    st.subheader(f"Übersicht für das Jahr {selected_year}")

    # --- Wetter-Kennzahlen ---
    avg_temp     = df_year["temperatur"].mean()
    max_wind     = df_year["windgeschwindigkeit"].max()
    sun_hours    = df_year["sonnenscheindauer_minuten"].fillna(0).sum() / 60
    precip_total = df_year["niederschlagshoehe_mm"].fillna(0).sum()

    # --- Schadstoff-Kennzahlen vs. WHO-Jahresgrenzwerte ---
    mean_ozon = df_year["o3"].mean()
    mean_no2  = df_year["no2"].mean()
    mean_pm10 = df_year["pm10"].mean()
    mean_pm25 = df_year["pm2x5"].mean()

    diff_ozon = mean_ozon - 100
    diff_no2  = mean_no2  - 25
    diff_pm10 = mean_pm10 - 15
    diff_pm25 = mean_pm25 - 5

    st.markdown(
        """
        <style>
        div[data-testid="stMetricLabel"] p { font-size: 14px !important; }
        div[data-testid="stMetricValue"]   { font-size: 24px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Reihe 1: Wetter
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Ø Temperatur",             f"{avg_temp:.1f} °C",     border=True)
    w2.metric("Max. Windgeschwindigkeit", f"{max_wind:.1f} m/s",    border=True)
    w3.metric("Gesamte Sonnenstunden",    f"{sun_hours:.0f} h",     border=True)
    w4.metric("Niederschlagssumme",       f"{precip_total:.0f} mm", border=True)

    # Reihe 2: Schadstoffe vs. WHO-Grenzwerte
    st.markdown(
        "<small><i>Kurze Übersicht der Wetterwerte im ausgewählten Jahr</i></small>",
        unsafe_allow_html=True,
    )
   
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Ø Ozon (Ziel: ≤100)",  f"{mean_ozon:.1f} µg/m³",
              delta=f"{diff_ozon:+.1f} µg/m³ vs. WHO",
              delta_color="inverse", border=True)
    s2.metric("Ø NO₂ (Ziel: ≤25)",    f"{mean_no2:.1f} µg/m³",
              delta=f"{diff_no2:+.1f} µg/m³ vs. WHO",
              delta_color="inverse", border=True)
    s3.metric("Ø PM10 (Ziel: ≤15)",   f"{mean_pm10:.1f} µg/m³",
              delta=f"{diff_pm10:+.1f} µg/m³ vs. WHO",
              delta_color="inverse", border=True)
    s4.metric("Ø PM2.5 (Ziel: ≤5)",   f"{mean_pm25:.1f} µg/m³",
              delta=f"{diff_pm25:+.1f} µg/m³ vs. WHO",
              delta_color="inverse", border=True)
    
    # Reihe 2: Schadstoffe vs. WHO-Grenzwerte
    st.markdown(
        "<small><i>Luftbelastung im Jahresmittel – Abweichung zu den WHO-Jahresgrenzwerten "
        "(grün = unter Grenzwert, rot = Überschreitung).</i></small>",
        unsafe_allow_html=True,
    )

@st.fragment
def showTab2():
    """
    Tab 2 – Datenbasis: Parquet-Snapshots aller Quelldateien.

    Zeigt Vorschau (Head/Tail), Schema (Dtypes, Null-Anteile) und deskriptive
    Statistik für jede Parquet-Datei in data/processed/. Erklärt den Vorteil
    des Parquet-Formats gegenüber CSV (Komprimierung, Typsicherheit, Ladezeit).
    """
    st.header("Datenbasis - Parquet-Snapshots")
    st.write(
        "Übersicht aller Parquet-Datengrundlagen dieses Projekts: "
        "**Vorschau**, **Schema** (Datentypen, Spalten) und **Statistik** "
        "(deskriptive Kennzahlen + Missing Values) je Datei."
    )

    with st.expander("ℹ️ Warum Parquet statt CSV?"):
        st.markdown(
            "Die Daten liegen bewusst im **Parquet-Format** vor – nicht als CSV. "
            "Bei einem Datensatz mit rund 394.000 stündlichen Messwerten macht das "
            "einen spürbaren Unterschied:\n\n"
            "- **Spaltenorientierte Speicherung & Komprimierung:** CSV speichert "
            "zeilenweise als Klartext. Parquet speichert *spaltenweise* – da eine "
            "Spalte stets denselben Datentyp enthält (z. B. Float für Temperatur), "
            "greifen Komprimierungsverfahren wie Snappy sehr effizient. Die Dateien "
            "werden dadurch deutlich kleiner und der RAM-Verbrauch beim Einlesen sinkt.\n"
            "- **Schnelleres Laden in Streamlit:** Jede Interaktion löst einen "
            "Skript-Rerun aus. Parquet erlaubt das gezielte Lesen einzelner Spalten, "
            "statt die gesamte Datei sequenziell zu parsen – zusammen mit "
            "`@st.cache_data` wird die Datei ohnehin nur einmal pro Session geladen.\n"
            "- **Typsicherheit:** Datentypen (inklusive `datetime`) sind im Schema "
            "hinterlegt. Das aufwendige Parsen von Datums-Strings entfällt komplett – "
            "Pandas erhält die korrekten Typen direkt.\n"
            "- **Skalierungsperspektive:** Für eine spätere Cloud-Nutzung rechnen "
            "Serverless-Analytics-Dienste nach gescannter Datenmenge ab. Dank "
            "Spaltenformat und Komprimierung wird pro Abfrage nur ein Bruchteil der "
            "Daten gelesen.\n\n"
            "Mehr dazu im Tab **Technische Insights** (Abschnitt 8)."
        )

    st.markdown("---")
    parquets = load_all_parquets()

    if not parquets:
        st.warning("Keine Parquet-Dateien gefunden.")
        return

    # Datei-Auswahl per Selectbox
    selected_file = st.selectbox(
        "Parquet-Datei auswählen:",
        options=list(parquets.keys()),
        key="parquet_selector",
    )

    df_snap = parquets[selected_file]

    # Kurz-Kennzahlen oben
    m1, m2, m3 = st.columns(3)
    m1.metric("Zeilen",   f"{len(df_snap):,}",         border=True)
    m2.metric("Spalten",  f"{df_snap.shape[1]}",       border=True)
    m3.metric("Speicher", f"{df_snap.memory_usage(deep=True).sum() / 1024**2:.2f} MB", border=True)

    st.markdown("---")

    # Drei Tabs: Vorschau | Schema | Statistik
    snap_tab1, snap_tab2, snap_tab3 = st.tabs(["📋 Vorschau", "🧱 Schema", "📊 Statistik"])

    # --- Vorschau (head + tail) ---
    with snap_tab1:
        st.markdown("##### Erste 10 Zeilen")
        st.dataframe(df_snap.head(10), use_container_width=True, hide_index=True)

        st.markdown("##### Letzte 10 Zeilen")
        st.dataframe(df_snap.tail(10), use_container_width=True, hide_index=True)

    # --- Schema (dtypes + Spaltenübersicht) ---
    with snap_tab2:
        st.markdown("##### Spalten und Datentypen")
        schema_df = pd.DataFrame({
            "Spalte":   df_snap.columns,
            "Dtype":    df_snap.dtypes.astype(str).values,
            "Non-Null": df_snap.notna().sum().values,
            "Null":     df_snap.isna().sum().values,
            "Unique":   [df_snap[c].nunique(dropna=True) for c in df_snap.columns],
        })
        st.dataframe(schema_df, use_container_width=True, hide_index=True)

    # --- Statistik (describe + Missing Values) ---
    with snap_tab3:
        st.markdown("##### Deskriptive Statistik (numerische Spalten)")
        st.dataframe(
            df_snap.describe().T.round(2),
            use_container_width=True,
        )

        st.markdown("##### Missing Values je Spalte")
        missing_df = pd.DataFrame({
            "Spalte":     df_snap.columns,
            "Fehlend":    df_snap.isna().sum().values,
            "Anteil (%)": (df_snap.isna().mean() * 100).round(2).values,
        }).sort_values("Fehlend", ascending=False)
        st.dataframe(missing_df, use_container_width=True, hide_index=True)


@st.fragment
def showTab3():
    """
    Tab 3 – Langzeitentwicklung 1980–2024: Primäre Schadstoffe und Temperatur.

    Berechnet 3-Jahres-Mittel für Anfang und Ende jeder Messreihe (robuster als
    ein direkter Anfang-vs-Ende-Vergleich) und zeigt zwei Liniendiagramme:
    primäre Schadstoffe (NO₂, PM10, PM2.5) sowie Doppelachsen-Diagramm
    Temperatur/O₃ über den Gesamtzeitraum.
    """
    st.header("Langzeitentwicklung 1980–2024")
    st.write("Veränderung über den gesamten Messzeitraum")
    st.caption(
        "Vergleich der 3-Jahres-Mittel zu Beginn und am Ende der jeweiligen "
        "Messreihe – robuster gegen Einzeljahr-Ausreißer als ein direkter "
        "Anfang-vs-Ende-Vergleich."
    )
    st.markdown("---")
    # Veränderungen berechnen
    delta_no2  = co.berechne_langzeit_veraenderung(dfOrginal, "no2")
    delta_pm10 = co.berechne_langzeit_veraenderung(dfOrginal, "pm10")
    delta_pm25 = co.berechne_langzeit_veraenderung(dfOrginal, "pm2x5")
    delta_o3   = co.berechne_langzeit_veraenderung(dfOrginal, "o3")
    delta_temp = co.berechne_langzeit_veraenderung(dfOrginal, "temperatur")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        f"NO₂ ({delta_no2['start_jahr']}–{delta_no2['end_jahr']})",
        f"{delta_no2['end_wert']:.1f} µg/m³",
        delta=f"{delta_no2['prozent_aenderung']:+.1f} %",
        delta_color="inverse", border=True,
    )
    c2.metric(
        f"PM10 ({delta_pm10['start_jahr']}–{delta_pm10['end_jahr']})",
        f"{delta_pm10['end_wert']:.1f} µg/m³",
        delta=f"{delta_pm10['prozent_aenderung']:+.1f} %",
        delta_color="inverse", border=True,
    )
    c3.metric(
        f"PM2.5 (seit {delta_pm25['start_jahr']})",
        f"{delta_pm25['end_wert']:.1f} µg/m³",
        delta=f"{delta_pm25['prozent_aenderung']:+.1f} %",
        delta_color="inverse", border=True,
    )
    c4.metric(
        f"Ozon ({delta_o3['start_jahr']}–{delta_o3['end_jahr']})",
        f"{delta_o3['end_wert']:.1f} µg/m³",
        delta=f"{delta_o3['prozent_aenderung']:+.1f} %",
        delta_color="inverse", border=True,
    )
    c5.metric(
    f"Temperatur ({delta_temp['start_jahr']}–{delta_temp['end_jahr']})",
    f"{delta_temp['end_wert']:.1f} °C",
    delta=f"{delta_temp['absolute_aenderung']:+.2f} K",
    delta_color="off", border=True,
)
    st.markdown("---")
    st.write(
            "Die Charts über den gesamten Zeitraumen zeigen die erfolgreichen Massnahmen zur Luftreinhaltung (Neue Motoren, Partikelfilter, Umweltzonen), " \
            "  während die Ozonentwicklung trotz sinkender Vorläuferstoffe durch den Klimawandel beeinflusst wird – steigende Temperaturen fördern die O₃-Bildung, was sich in den letzten Jahren besonders deutlich zeigt." 
        )

    col_left, col_right = st.columns(2)

    with col_left:
        st.pyplot(co.langzeit_primaere_schadstoffe(dfOrginal))
        st.caption(
            "Primäre, direkt emittierte Schadstoffe (Verkehr, Verbrennung) "
            "zeigen über die Jahrzehnte einen klaren Rückgang."
        )
        with st.expander("ℹ️ Hinweis zu den Daten"):
            st.write(
                "ℹ️ **Datenhinweis:** PM2.5 wird in der CAMS-Reanalyse erst ab 2008 "
                "durchgängig bereitgestellt – der spätere Linienbeginn ist kein Datenfehler, "
                "sondern spiegelt den Start der flächendeckenden Messung wider."
            )

    with col_right:
        st.pyplot(co.langzeit_temperatur_ozon(dfOrginal))
        st.caption(
            "Die Temperatur un die Ozonwerte zeigen über den gesamten Zeitraum einen deutlichen Aufwärtstrend."
            
        )
        with st.expander("ℹ️ Hinweis zu den Daten"):
            st.write(
                "ℹ️ **Zu den Temperatur-Tiefs:** Die sichtbaren Einbrüche 1996 und 2021 sind "
                "keine Datenartefakte, sondern reale Kaltjahre – 1996 war europaweit auffällig "
                "kalt, 2021 ungewöhnlich nass und kühl."
            )


@st.fragment
def showTab4():
    """
    Tab 4 – Das Ozon-Paradoxon: Stadt-Land-Vergleich und Titrationseffekt.

    Zeigt den Langzeitverlauf O₃ Stadt (Nürnberg) vs. Land (Tiefenbach, DWD)
    mit NO₂ und Temperatur (2016–2025) sowie einen wettergematchten Vergleich
    zweier Einzeltage (Di 24.07.2018 vs. So 19.08.2018) zur Demonstration des
    NO₂-Titrationseffekts auf das Ozon-Tagesprofil.
    """
    st.header("Das Ozon-Paradoxon: Je schlechter die Luft, desto besser der Ozon-Level")
    st.write(
        "Ozon (O₃) entsteht nicht direkt aus dem Auspuff, sondern als sekundärer "
        "Schadstoff aus Vorläufern (NOₓ, VOC) unter Sonneneinstrahlung. \nIn der Stadt wird O₃ durch frisches NO sofort wieder **titriert** – auf dem "
        "Land fehlt dieser Abbau, und die Konzentration bleibt hoch."
    )

    st.markdown("---")

    df_land_tagesmax = load_tiefenbach_tagesmax()
    df_land_stunden  = load_tiefenbach_stunden()

    # --- Langzeitvergleich Stadt vs. Land ---
    st.pyplot(co.ozonparadoxon(dfOrginal, df_land_tagesmax))
    with st.expander("Erklärung"):
        st.markdown("""
        Das Ozon-Paradoxon: Urbane vs. Rurale Dynamik

Diese Darstellung visualisiert den chemischen Abbau von Ozon durch Stickstoffdioxid (NO₂).

* Urbane Belastung (rote Linie): In der Stadt führen hohe NO₂-Emissionen zu einer sofortigen Titration, wodurch die Ozon-Konzentration trotz intensiverer Bildungsprozesse temporär sinkt.

* Rurale Belastung (grüne Linie): Auf dem Land fehlt dieser direkte Abbau durch frische Abgase. Die Ozon-Werte bleiben dadurch deutlich stabiler und erreichen häufig höhere Niveaus.

* Einflussfaktor Temperatur: Die graue Kurve unterstreicht die photochemische Abhängigkeit: Steigt die Temperatur und Sonneneinstrahlung, nimmt die Ozonbildung in beiden Gebieten zu, wird jedoch im urbanen Raum durch die Schadstofflast stärker maskiert.
        """)

    st.markdown("---")
    st.subheader("Ozon-Titration: Werktag vs. Sonntag bei gleichem Wetter")
    st.caption("Sonne und Temperatur fast identisch – nur der Berufsverkehr unterscheidet die Tage")

        # --- Wetter-gematchter Vergleich ---
    st.pyplot(co.titration_wettergematcht(dfOrginal, df_land_stunden))

    with st.expander("Erklärung"):
        st.markdown("""
        Am **Dienstag, 24.07.2018** und am **Sonntag, 19.08.2018** waren die meteorologischen 
        Bedingungen nahezu identisch: vergleichbare Sonneneinstrahlung, ähnliche Temperaturen.
        Der entscheidende Unterschied war der **Berufsverkehr**.
        
        An Werktagen entstehen morgens hohe NO₂-Emissionen aus dem Verkehr. Dieses NO₂ reagiert
        mit bereits vorhandenem Ozon (O₃) und „titriert" es weg – die Ozonwerte in der Stadt
        sinken kurzfristig, bevor die Photochemie sie tagsüber wieder aufbaut.
        
        Am Sonntag fehlt dieser NO-Eintrag – die Titration bleibt aus, das Ozon-Profil
        verläuft glatter.
        """)

def showTab5() -> None:
    """
    Tab 5 – Korrelationsanalyse: Methodenvergleich und Heatmap.

    Erklärt Unterschiede zwischen Pearson-, Spearman- und Kendall-Korrelation
    und zeigt eine nebeneinandergestellte Korrelationsmatrix (Spearman | Pearson)
    für Wetter- und Schadstoffvariablen (Nürnberg 1980–2024). Spearman ist die
    Hauptaussage: robust gegen Ausreißer, erfasst monotone nichtlineare Zusammenhänge.
    """
    st.header("Methoden der Korrelationsanalyse: Welches Modell ist das richtige?")

    st.write(
        "Um den Einfluss von Variablen wie NO₂, Temperatur und Luftfeuchtigkeit auf die "
        "Ozonentwicklung wissenschaftlich fundiert zu analysieren, ist die Wahl des "
        "passenden Korrelationskoeffizienten entscheidend."
    )
    st.markdown("---")
    st.markdown("#### Vergleich der Korrelationsmodelle")

    df_methoden = pd.DataFrame(
        {
            "Methode": ["Pearson", "Spearman", "Kendall"],
            "Eignung & Charakteristik": [
                "Klassisch; setzt lineare Zusammenhänge und normalverteilte Daten voraus.",
                "Empfohlen: Robust gegen Ausreißer; erkennt auch nichtlineare, monotone Trends.",
                "Konservativ; sehr zuverlässig bei kleinen Stichproben oder vielen gleichen Werten.",
            ],
            "Fokus": [
                "Stärke des linearen Zusammenhangs.",
                "Stärke der Rangfolge-Beziehung.",
                "Konkordanz von Datenpaaren.",
            ],
        }
    )

    st.table(df_methoden.set_index("Methode"))

    st.markdown("#### Erläuterung der Unterschiede")

    st.markdown(
        "**Pearson:** Dieses Modell misst, wie stark sich zwei Variablen linear zueinander "
        "verhalten. Da atmosphärische Daten jedoch häufig durch extreme Spitzenwerte "
        "(z. B. Rushhour-Emissionen) geprägt sind, kann Pearson hier leicht zu verfälschten "
        "Ergebnissen führen, wenn die Daten nicht strikt normalverteilt sind."
    )

    st.markdown(
        "**Spearman:** Anstatt absolute Werte zu nutzen, arbeitet Spearman mit Rängen. Das "
        "macht das Modell extrem robust gegenüber Ausreißern. Da chemische Prozesse in der "
        "Atmosphäre (wie die Ozonbildung) oft nicht linear verlaufen, sondern bei bestimmten "
        "Schwellenwerten sättigen, erfasst Spearman diese dynamischen Zusammenhänge deutlich "
        "präziser."
    )

    st.markdown(
        "**Kendall:** Kendall ist die statistisch „strengere\" Variante. Sie ist besonders "
        "dann nützlich, wenn man die Konsistenz der Zusammenhänge in sehr kleinen Datensätzen "
        "prüfen möchte. Bei großen Zeitreihen (wie UBA/LfU-Daten) liefern Spearman "
        "und Kendall meist ähnliche Erkenntnisse, wobei Spearman rechnerisch effizienter ist."
    )

    st.markdown("---")
    st.markdown("#### Korrelationsmatrix der Variablen")
    st.write("Korrelationsmatrix: Wetter- und Schadstoffvariablen (Nürnberg, 1980–2024)\n"
        "Spearman erfasst monotone, auch nichtlineare Zusammenhänge – Pearson nur lineare",
    )

    st.info(
        "Die folgende Matrix zeigt links die **Spearman**-Korrelationen (Hauptaussage) "
        "und rechts zum Vergleich **Pearson**. Werte nahe +1 oder −1 "
        "bedeuten starke Zusammenhänge, Werte nahe 0 keine. Aufschlussreich sind "
        "die Stellen, an denen sich beide Matrizen unterscheiden: Dort verläuft der "
        "Zusammenhang nichtlinear – genau das, was bei der Ozonbildung zu erwarten ist."
    )

    fig = co.korrelationsmatrix_vergleich(dfOrginal)
    st.pyplot(fig)

    with st.expander("Wie ist die Matrix zu lesen?"):
        st.markdown(
            "- **Diagonale = 1.0:** Jede Variable korreliert perfekt mit sich selbst.\n"
            "- **O₃ ↔ Temperatur / Sonnenschein:** positiver Zusammenhang erwartet "
            "(Ozonbildung unter Sonneneinstrahlung).\n"
            "- **O₃ ↔ NO₂:** negativer Zusammenhang erwartet (Titrationseffekt – "
            "NO₂ baut Ozon ab).\n"
            "- **Spearman vs. Pearson:** Weicht Spearman deutlich von Pearson ab, "
            "ist der Zusammenhang monoton, aber nicht linear."
        )


@st.fragment
def showTab6() -> None:
    """
    Tab 6 – Multiple lineare Regression (OLS): Modellvergleich.

    Vergleicht zwei standardisierte OLS-Modelle zur Erklärung von O₃:
    Nur-Wetter-Modell (R² ≈ 0,58) vs. Wetter-plus-Schadstoffe-Modell (R² ≈ 0,65).
    Zeigt Modellgüte-Tabelle und Koeffizienten-Balkendiagramm. Prädiktoren sind
    z-standardisiert, sodass Koeffizienten trotz unterschiedlicher Einheiten
    direkt vergleichbar sind.
    """
    st.header("📈 Multiple lineare Regression (OLS): Was erklärt das Ozon?")

    st.write(
        "Die Korrelationsanalyse hat gezeigt, *welche* Variablen mit Ozon "
        "zusammenhängen. Die Regression geht einen Schritt weiter und schätzt, "
        "*wie stark* jeder Faktor wirkt, wenn alle anderen konstant gehalten "
        "werden. Verglichen werden zwei Modelle: eines nur mit Wettergrößen und "
        "eines, das zusätzlich die Schadstoffe NO₂ und PM10 einbezieht."
    )

    fig, kennzahlen = co.ols_modellvergleich(dfOrginal)

    st.markdown("#### Modellgüte im Vergleich")
    st.table(kennzahlen.set_index("Modell"))

    st.write(
        "Schon die Wettervariablen erklären rund 58 % der Ozon-Schwankungen. "
        "Nimmt man die Schadstoffe hinzu, steigt die Erklärungskraft auf rund "
        "65 %. Da die Prädiktoren standardisiert wurden, lässt sich an der Länge "
        "der Balken direkt ablesen, welcher Faktor am stärksten wirkt."
    )

    st.pyplot(fig)

    with st.expander("Wie sind die Koeffizienten zu lesen?"):
        st.markdown(
            "- **Standardisiert (z-Scores):** Jeder Koeffizient zeigt die "
            "O₃-Änderung (in µg/m³) pro **einer Standardabweichung** der "
            "jeweiligen Variable. Dadurch sind die Effekte trotz "
            "unterschiedlicher Einheiten (°C, %, hPa …) direkt vergleichbar.\n"
            "- **Vorzeichen = Wirkrichtung:** Positiv treibt O₃ nach oben, "
            "negativ senkt es.\n"
            "- **Temperatur** wirkt am stärksten positiv, **relative Luftfeuchte** "
            "am stärksten negativ – beides physikalisch erwartbar.\n"
            "- **NO₂** zeigt einen deutlich negativen Effekt: der **Titrationseffekt**, "
            "den wir auch im Rushhour-Vergleich sehen.\n"
            "- **Hinweis Sonnenscheindauer:** Das negative Vorzeichen wirkt "
            "kontraintuitiv. Ursache ist die starke Kopplung an die Temperatur "
            "(Multikollinearität) – der „Sonnen-Effekt\" steckt bereits zu großen "
            "Teilen im Temperatur-Koeffizienten.\n"
            "- **Grenze des Modells:** Mit R² ≈ 0,65 bleibt rund ein Drittel "
            "unerklärt. Das deutet auf **nichtlineare Zusammenhänge** hin – genau "
            "hier setzt im nächsten Tab der Random Forest an."
        )


@st.fragment
def showTab7() -> None:
    """
    Tab 7 – Random Forest: Nichtlineare Ozon-Vorhersage und Feature Importance.

    Ruft ``train_random_forest`` auf (via ``@st.cache_resource`` gecacht, läuft
    einmalig pro Session) und zeigt Feature-Importance-Balken sowie einen
    R²-Vergleich OLS vs. Random Forest. Der R²-Sprung belegt die Nichtlinearität
    der Ozonbildung als Kernaussage dieser Analyse.
    """
    st.header("🌲 Random Forest: Wetter als Prädiktor für Ozon")

    st.write(
        "Die lineare Regression stieß an ihre Grenze: Rund ein Drittel der "
        "Ozon-Schwankung blieb unerklärt, weil viele atmosphärische Zusammenhänge "
        "nicht linear verlaufen. Der **Random Forest** kann solche nichtlinearen "
        "Effekte und Schwellenwerte abbilden – und zeigt zugleich, welche Faktoren "
        "wirklich den größten Beitrag zur Vorhersage leisten."
    )

    with st.spinner("Trainiere Random Forest (einmalig, danach gecacht)…"):
        ergebnis = train_random_forest(dfOrginal)

    fig = co.rf_feature_importance_und_vergleich(
        ergebnis["importances"],
        r2_ols=ergebnis["r2_ols"],
        r2_rf=ergebnis["r2_rf"],
    )
    st.pyplot(fig)

    spalte1, spalte2, spalte3 = st.columns(3)
    spalte1.metric("R² – OLS (linear)", f"{ergebnis['r2_ols']:.3f}")
    spalte2.metric(
        "R² – Random Forest", f"{ergebnis['r2_rf']:.3f}",
        delta=f"{ergebnis['r2_rf'] - ergebnis['r2_ols']:+.3f}",
    )
    spalte3.metric("Ø Fehler RF (MAE)", f"{ergebnis['mae_rf']:.1f} µg/m³")

    with st.expander("Wie ist das Ergebnis zu lesen?"):
        st.markdown(
            "- **Feature Importance (Permutation):** Gemessen wird, wie stark die "
            "Vorhersagegüte auf den Testdaten einbricht, wenn eine Variable "
            "zufällig durchmischt wird. Je größer der Einbruch, desto wichtiger "
            "die Variable. Dieses Verfahren ist robuster gegen korrelierte "
            "Prädiktoren als die eingebaute Gini-Importance.\n"
            "- **Zeitbasierte Validierung:** Trainiert wird auf den älteren 80 % "
            "der Zeitreihe, getestet auf den jüngsten 20 %. Ein zufälliger Split "
            "würde bei stündlichen Daten zu Data Leakage führen, weil benachbarte "
            "Stunden stark korreliert sind – die hier gezeigten Werte spiegeln die "
            "Vorhersage auf tatsächlich ungesehenen Zeiträumen wider.\n"
            "- **R²-Vergleich:** Der Random Forest erklärt mehr Varianz als die "
            "lineare Regression. Dieser Abstand belegt, dass die Ozonbildung "
            "**nichtlinear** ist – die Kernaussage dieser Analyse.\n"
            "- **MAE:** Der mittlere absolute Fehler in µg/m³ zeigt, wie weit die "
            "Vorhersage im Schnitt vom tatsächlichen O₃-Wert abweicht.\n"
            "- **Achtung Interpretation:** Importance zeigt *Wichtigkeit für die "
            "Vorhersage*, nicht die Wirkrichtung. Ob ein Faktor O₃ erhöht oder "
            "senkt, verraten die OLS-Koeffizienten im vorigen Tab."
        )


@st.fragment
def showTab8():
    """
    Tab 8 – News-API: RSS-Feeds zu Klima und Luftqualität.

    Lädt aktuelle Pressemeldungen von verifizierten RSS-Feeds (tagesschau,
    Deutsche Welle, Carbon Brief, The Guardian) via ``news.lade_feed()``.
    Sprache (DE/EN) und Quellen sind per Radio-Button und Multiselect filterbar.
    Feeds werden stündlich via ``@st.cache_data(ttl=3600)`` aktualisiert.
    """
    st.header("Aktuelles zu Klima & EU-Klimapolitik")
    st.write(
        "Aktuelle Meldungen aus offiziellen Quellen zu Luftqualität, Klimawandel "
        "und EU-Klimazielen. Die Inhalte werden live per RSS-Feed geladen und "
        "stündlich aktualisiert."
    )

    # Sprachauswahl
    sprache_anzeige = st.radio(
        "Sprache:",
        options=["Deutsch", "Englisch"],
        horizontal=True,
        key="news_sprache",
    )
    sprache_code: news.Sprache = "de" if sprache_anzeige == "Deutsch" else "en"

    verfuegbare_feeds = news.feeds_nach_sprache(sprache_code)

    # Quellenauswahl
    quellen_namen = [f.name for f in verfuegbare_feeds]
    gewaehlte_quellen = st.multiselect(
        "Quellen auswählen:",
        options=quellen_namen,
        default=quellen_namen,  # alle vorausgewählt
        key="news_quellen",
    )

    if not gewaehlte_quellen:
        st.warning("Bitte mindestens eine Quelle auswählen.")
        return

    st.markdown("---")

    # Pro Quelle ein Abschnitt
    for feed in verfuegbare_feeds:
        if feed.name not in gewaehlte_quellen:
            continue

        st.markdown(f"### {feed.name}")
        st.caption(feed.quelle)

        try:
            eintraege = news.lade_feed(feed.url, max_eintraege=5)
        except Exception as e:
            st.error(f"Feed konnte nicht geladen werden: {e}")
            continue

        if not eintraege:
            st.info("Keine aktuellen Meldungen gefunden.")
            continue

        for eintrag in eintraege:
            datum_str = (
                eintrag["datum"].strftime("%d.%m.%Y")
                if eintrag["datum"] else "Datum unbekannt"
            )
            with st.expander(f"📰 {eintrag['titel']}  ·  _{datum_str}_"):
                if eintrag["zusammenfassung"]:
                    # HTML aus Feed-Summaries wird per unsafe_allow_html=True durchgereicht
                    st.markdown(eintrag["zusammenfassung"], unsafe_allow_html=True)
                st.markdown(f"[🔗 Vollständigen Artikel lesen]({eintrag['link']})")

        st.markdown("---")


@st.fragment
def showTab9():
    """
    Tab 9 – Technische Insights & Lessons Learned.

    Liest ``Technische_Insights_Lessons_Learned.md`` aus dem Projekt-Root und
    rendert den Inhalt als Markdown. Dokumentiert technische Entscheidungen zu
    Datenbeschaffung, Streamlit-Architektur, Caching-Strategie und Modellstrecke.
    """
    st.header("🛠️ Technische Insights & Lessons Learned")
    st.write(
        "Hinter dem Dashboard stecken einige bewusste technische Entscheidungen – "
        "von der Datenbeschaffung über die Streamlit-Architektur bis zur "
        "Modellstrecke. Die folgenden Notizen dokumentieren die wichtigsten "
        "Fallstricke und Lösungen."
    )
    st.markdown("---")

    # Markdown-Datei liegt im Projekt-Root neben app.py
    insights_pfad = Path(__file__).parent / "Technische_Insights_Lessons_Learned.md"

    if insights_pfad.exists():
        inhalt = insights_pfad.read_text(encoding="utf-8")
        st.markdown(inhalt, unsafe_allow_html=True)
    else:
        st.warning(
            f"Datei nicht gefunden: `{insights_pfad.name}`. "
            "Bitte die Markdown-Datei ins Projekt-Root legen (neben app.py)."
        )

# ============================================================
# 04 DATEN LADEN
# ============================================================
dfOrginal = load()


# ============================================================
# 05 TABS RENDERN
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Startseite",
    "Datenbasis",
    "Explorative Analyse",
    "Das Ozon-Paradoxon",
    "Korrelationsanalyse",
    "Multiple Regression",
    "Random Forest",
    "News-API",
    "Technische Insights"
])

with tab1: showTab1()
with tab2: showTab2()
with tab3: showTab3()
with tab4: showTab4()
with tab5: showTab5()
with tab6: showTab6()
with tab7: showTab7()
with tab8: showTab8()
with tab9: showTab9()


# ============================================================
# 06 PROJEKT-FOOTER (Titel + Danksagung)
# ============================================================
st.markdown(
    """
    <div style="background-color: rgba(3, 149, 176, 0.08); padding: 14px 20px;
                border-radius: 0.5rem; border-left: 4px solid rgba(3, 149, 176, 0.9);
                margin-top: 32px;">
        <b style="font-size: 22px; color: #FAFAFA;">
            Thema: Ozonbildung unter dem Einfluss von Klima und Verkehr
        </b><br>
        <span style="font-size: 16px; color: #FAFAFA;">
            Eine Langzeitanalyse für den Großraum Nürnberg mit Fokus auf das Ozon-Paradoxon (Stadt vs. Land, Messstellenvergleich)
        </span><br>
        <span style="font-size: 13px; color: #FAFAFA;">
            Autor: Frank Hasdorf
        </span>
        <div style="border-top: 1px solid rgba(255, 255, 255, 0.08);
                    margin-top: 10px; padding-top: 8px;">
            <span style="font-size: 14px; color: #FAFAFA; font-style: italic; line-height: 1.5;">
                Dieses Projekt entstand als Abschlussarbeit der Data-Science-Fortbildung
                am Data Science Institute Berlin. Ein herzlicher Dank gilt dem Institut
                für die fundierte Ausbildung, die das nötige Rüstzeug für dieses Projekt
                vermittelt hat – von der Datenaufbereitung über die Korrelations- und
                Regressionsanalyse bis hin zum Einsatz des Random Forest.
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
