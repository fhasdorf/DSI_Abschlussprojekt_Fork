# -*- coding: utf-8 -*-
"""
Ozon-spezifische Chart-Funktionen.

Konvention fuer dieses Modul:
1. Jede Funktion erhaelt einen DataFrame (i.d.R. dfOrginal) und gibt
   eine matplotlib.figure.Figure zurueck.
2. KEINE Streamlit-Aufrufe hier drin (kein st.pyplot, kein st.markdown).
   Das geschieht in app.py - so bleibt dieses Modul auch in Jupyter
   testbar.
3. KEINE eigenen Farb-/Font-Definitionen. Das globale Styling wird in
   app.py durch styling.apply_global_style() gesetzt und gilt fuer
   alle Figures.
4. Fuer Akzentfarben (z. B. fuer Saisons): Import aus styling.COLORS,
   damit die Palette appweit konsistent bleibt.

Aufruf in app.py:
    import src.visualization.charts_ozon as co
    st.pyplot(co.tagesgang_nach_saison(dfOrginal))
"""

import matplotlib.pyplot as plt
import pandas as pd
from src.utils import styling
import matplotlib.dates as mdates
import matplotlib.patches as mpatches

# Akzentfarben aus dem globalen Styling-Modul ziehen,
# damit die Palette ueber die ganze App konsistent ist.
from src.utils.styling import COLORS


# ------------------------------------------------------------
# Helper: meteorologische Saison aus Monat ableiten
# ------------------------------------------------------------
def _saison_aus_monat(monat: int) -> str:
    """
    Ordnet einen Kalendermonat (1–12) der meteorologischen Jahreszeit zu.

    Meteorologische Konvention (DWD):
      Winter  = Dez, Jan, Feb  (12, 1, 2)
      Frühling = Mär, Apr, Mai  (3, 4, 5)
      Sommer  = Jun, Jul, Aug  (6, 7, 8)
      Herbst  = Sep, Okt, Nov  (9, 10, 11)

    Parameters
    ----------
    monat : int
        Kalendermonat (1 = Januar … 12 = Dezember).

    Returns
    -------
    str
        Einer der Werte ``"Winter"``, ``"Frühling"``, ``"Sommer"``, ``"Herbst"``.
    """
    if monat in (12, 1, 2):
        return "Winter"
    if monat in (3, 4, 5):
        return "Frühling"
    if monat in (6, 7, 8):
        return "Sommer"
    return "Herbst"


# Reihenfolge der Jahreszeiten für Legenden und Schleifeniterationen
SAISON_REIHENFOLGE = ["Frühling", "Sommer", "Herbst", "Winter"]

# Farb-Mapping Jahreszeit → Hex-Farbe; konsistent mit COLORS aus styling.py
SAISON_FARBEN = {
    "Frühling": COLORS["good"],        # grün
    "Sommer":   COLORS["accent_warm"], # orange
    "Herbst":   "#8D6E63",             # braun
    "Winter":   "#2196F3",             # blau
}

def berechne_langzeit_veraenderung(
    df: pd.DataFrame,
    spalte: str,
    fenster: int = 3,
) -> dict:
    """
    Berechnet die prozentuale Veränderung einer Größe über den Messzeitraum.

    Vergleicht den Mittelwert der ersten `fenster` Jahre mit dem Mittelwert
    der letzten `fenster` Jahre (Default: 3), um robuste Trendaussagen zu
    erhalten und Einzeljahr-Ausreißer zu dämpfen.

    Returns
    -------
    dict mit Keys: 'start_jahr', 'end_jahr', 'start_wert', 'end_wert',
                   'absolute_aenderung', 'prozent_aenderung'
    """
    df_clean = df.dropna(subset=[spalte]).copy()
    df_clean["jahr"] = df_clean["datum"].dt.year
    jahresmittel = df_clean.groupby("jahr")[spalte].mean().sort_index()

    start_wert = jahresmittel.iloc[:fenster].mean()
    end_wert   = jahresmittel.iloc[-fenster:].mean()
    prozent    = (end_wert - start_wert) / start_wert * 100

    return {
        "start_jahr":         int(jahresmittel.index[0]),
        "end_jahr":           int(jahresmittel.index[-1]),
        "start_wert":         start_wert,
        "end_wert":           end_wert,
        "absolute_aenderung": end_wert - start_wert,
        "prozent_aenderung":  prozent,
    }

# ------------------------------------------------------------
# Chart: Tagesgang nach Jahreszeit
# ------------------------------------------------------------
def tagesgang_nach_saison(df: pd.DataFrame) -> plt.Figure:
    """
    Mittlere O3-Konzentration je Tagesstunde, gruppiert nach Jahreszeit.

    Parameters
    ----------
    df : pd.DataFrame
        Muss die Spalten 'datum', 'stunde' und 'o3' enthalten.

    Returns
    -------
    matplotlib.figure.Figure
        Wird in app.py mit st.pyplot(fig) angezeigt.
    """
    daten = df[["datum", "stunde", "o3"]].dropna(subset=["o3"]).copy()
    daten["saison"] = daten["datum"].dt.month.map(_saison_aus_monat)

    pivot = (
        daten.groupby(["saison", "stunde"])["o3"]
             .mean()
             .reset_index()
    )

    fig, ax = plt.subplots()

    for saison in SAISON_REIHENFOLGE:
        sub = pivot[pivot["saison"] == saison]
        if sub.empty:
            continue
        ax.plot(
            sub["stunde"], sub["o3"],
            label=saison,
            color=SAISON_FARBEN[saison],
            marker="o",
        )

    ax.set_xlabel("Stunde des Tages")
    ax.set_ylabel("Ø O₃ (µg/m³)")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(-0.5, 23.5)
    ax.legend(title="Jahreszeit", loc="upper left")

    return fig


def langzeit_primaere_schadstoffe(df: pd.DataFrame) -> plt.Figure:
    """
    Liniendiagramm: Jahresmittel NO₂, PM10 und PM2.5 über den Gesamtzeitraum.

    Primäre, direkt emittierte Schadstoffe (Verkehr, Verbrennung) zeigen über
    die Jahrzehnte einen Rückgang infolge von Luftreinhaltemaßnahmen
    (Partikelfilter, Abgasnormen, Umweltzonen). PM2.5 beginnt erst ab 2008,
    da CAMS-Reanalysen diese Variable erst ab diesem Zeitraum durchgängig liefern.

    Parameters
    ----------
    df : pd.DataFrame
        Hauptdatensatz mit Spalten ``datum`` (datetime64), ``no2``, ``pm10``,
        ``pm2x5`` (alle in µg/m³).

    Returns
    -------
    matplotlib.figure.Figure
    """
    df_year = (
        df.assign(jahr=df["datum"].dt.year)
          .groupby("jahr")[["no2", "pm10", "pm2x5"]]
          .mean()
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df_year.index, df_year["no2"],   label="NO₂",   color=styling.COLORS["accent"],      linewidth=2)
    ax.plot(df_year.index, df_year["pm10"],  label="PM10",  color=styling.COLORS["accent_warm"], linewidth=2)
    ax.plot(df_year.index, df_year["pm2x5"], label="PM2.5", color=styling.COLORS["bad"],         linewidth=2)

    ax.set_xlabel("Jahr")
    ax.set_ylabel("Konzentration (µg/m³)")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def langzeit_temperatur_ozon(df: pd.DataFrame) -> plt.Figure:
    """
    Doppelachsen-Liniendiagramm: Jahresmittel Temperatur (links) und O₃ (rechts).

    Visualisiert den klimatischen Treiber der O₃-Bildung: Steigende Temperaturen
    erhöhen die photochemische Reaktionsrate und damit die Ozonproduktion. Sichtbare
    Kälteeinbrüche (z. B. 1996, 2021) sind reale meteorologische Ereignisse, keine
    Datenartefakte.

    Parameters
    ----------
    df : pd.DataFrame
        Hauptdatensatz mit Spalten ``datum`` (datetime64), ``temperatur`` (°C),
        ``o3`` (µg/m³).

    Returns
    -------
    matplotlib.figure.Figure
    """
    df_year = (
        df.assign(jahr=df["datum"].dt.year)
          .groupby("jahr")[["temperatur", "o3"]]
          .mean()
    )

    fig, ax1 = plt.subplots(figsize=(8, 4.5))

    # Linke Achse: Temperatur
    color_temp = styling.COLORS["accent_warm"]
    ax1.plot(df_year.index, df_year["temperatur"],
             label="Temperatur", color=color_temp, linewidth=2)
    ax1.set_xlabel("Jahr")
    ax1.set_ylabel("Temperatur (°C)", color=color_temp)
    ax1.tick_params(axis="y", labelcolor=color_temp)
    ax1.grid(True, alpha=0.3)

    # Rechte Achse: Ozon
    ax2 = ax1.twinx()
    color_o3 = styling.COLORS["accent"]
    ax2.plot(df_year.index, df_year["o3"],
             label="Ozon (O₃)", color=color_o3, linewidth=2)
    ax2.set_ylabel("Ozon (µg/m³)", color=color_o3)
    ax2.tick_params(axis="y", labelcolor=color_o3)

    # Kombinierte Legende
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)

    fig.tight_layout()
    return fig

# -----------------------------------------------------------------------------
# Ozon-Paradoxon: Stadt vs. Land im Langzeitverlauf (2016–2025)
# Datenquellen: DWD/LfU Nürnberg (Stadt) und DWD-Station Tiefenbach (Land)
# -----------------------------------------------------------------------------

def ozonparadoxon(
    df_stadt: pd.DataFrame,
    df_land: pd.DataFrame,
    jahr_von: int = 2016,
    jahr_bis: int = 2025,
    rolling_window: int = 30,
) -> plt.Figure:
    """Vergleicht O₃-Verlauf Stadt (Nürnberg) vs. Land (Tiefenbach) mit NO₂ und Temperatur.

    Parameters
    ----------
    df_stadt : pd.DataFrame
        Stündliche Nürnberg-Daten (data.parquet). Erwartete Spalten:
        ``datum`` (datetime64), ``o3``, ``no2``, ``temperatur``.
    df_land : pd.DataFrame
        Tages-O₃-Maxima Tiefenbach
        (``o3_dailymax_2016_2025_station_tiefenbach_bayern.parquet``).
        Erwartete Spalten: ``datum`` (datetime64), ``o3_land``.
    jahr_von, jahr_bis : int
        Zeitraumsgrenzen (inklusive).
    rolling_window : int
        Fensterbreite für den gleitenden Mittelwert (Tage).
    """
    # -- 1. Land-Daten: Filter auf Zeitraum --------------------------------
    df_l = df_land.copy()
    df_l["datum"] = pd.to_datetime(df_l["datum"])
    df_l = df_l[(df_l["datum"].dt.year >= jahr_von) & (df_l["datum"].dt.year <= jahr_bis)]

    # -- 2. Stadt-Daten: Tagesaggregate aus Stundenwerten ------------------
    df_s = df_stadt.copy()
    df_s["datum"] = pd.to_datetime(df_s["datum"])
    df_s = df_s[(df_s["datum"].dt.year >= jahr_von) & (df_s["datum"].dt.year <= jahr_bis)]

    # Datum auf Tag normalisieren (falls Stundenwerte mit Uhrzeit reinkommen)
    df_s["datum"] = df_s["datum"].dt.normalize()
    df_stadt_daily = (
        df_s.groupby("datum")
        .agg(o3_stadt=("o3", "max"), no2_stadt=("no2", "max"), temperatur=("temperatur", "mean"))
        .reset_index()
    )

    # -- 3. Merge & Glätten -------------------------------------------------
    df_merged = pd.merge(df_stadt_daily, df_l, on="datum", how="inner").set_index("datum")
    df_smoothed = df_merged.rolling(window=rolling_window, min_periods=1).mean()

    # -- 4. Plot ------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # Linke Y-Achse: Schadstoffe
    ax1.plot(
        df_smoothed.index, df_smoothed["o3_land"],
        label="Ozon (O₃) Land – Tiefenbach",
        color=COLORS["good"], linewidth=2.5,
    )
    ax1.plot(
        df_smoothed.index, df_smoothed["o3_stadt"],
        label="Ozon (O₃) Stadt – Nürnberg",
        color=COLORS["text_muted"], linewidth=2,
    )
    ax1.plot(
        df_smoothed.index, df_smoothed["no2_stadt"],
        label="Stickstoffdioxid (NO₂) Stadt – Nürnberg",
        color=COLORS["bad"], linestyle="--", linewidth=2,
    )

    ax1.set_xlabel("Jahr")
    ax1.set_ylabel(f"Konzentration (µg/m³) – {rolling_window}-Tage-Schnitt")
    ax1.set_ylim(bottom=0)

    # Rechte Y-Achse: Temperatur als Hintergrundfläche
    ax2 = ax1.twinx()
    ax2.fill_between(
        df_smoothed.index, 0, df_smoothed["temperatur"],
        color=COLORS["accent_warm"], alpha=0.15, label="Temperatur (°C)",
    )
    ax2.set_ylabel("Temperatur (°C)", color=COLORS["accent_warm"])
    ax2.tick_params(axis="y", colors=COLORS["accent_warm"])
    ax2.set_ylim(bottom=-10, top=df_smoothed["temperatur"].max() * 1.5)

    # Legende
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines_1 + lines_2, labels_1 + labels_2,
        loc="upper center", bbox_to_anchor=(0.5, -0.1),
        ncol=4, frameon=False,
    )

    fig.tight_layout()
    return fig


# -----------------------------------------------------------------------------
# Titrationseffekt: Sonntag vs. Werktag im Stundenverlauf
# -----------------------------------------------------------------------------

def _titration_zweitageplot(
    df_merged: pd.DataFrame,
    tage: dict,
) -> plt.Figure:
    """Interner Helper: rendert zwei Tage nebeneinander mit O₃/NO₂/Sonne.

    Wird von ``titration_sonntag_vs_werktag`` und
    ``titration_wettergematcht`` wiederverwendet.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 8), sharey=True)

    for ax, (tag, label) in zip(axes, tage.items()):
        mask = (df_merged.index >= tag) & (df_merged.index <= f"{tag} 23:59:59")
        df_tag = df_merged.loc[mask]

        if df_tag.empty:
            ax.text(
                0.5, 0.5, f"Keine Daten für {label}",
                ha="center", va="center", transform=ax.transAxes,
            )
            continue

        # Sonnenscheindauer als Hintergrundfläche (zweite Y-Achse)
        ax2 = ax.twinx()
        ax2.fill_between(
            df_tag.index, 0, df_tag["sonne_prozent"],
            color=COLORS["accent_warm"], alpha=0.20, zorder=0,
        )
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("Sonnenscheindauer (% der Stunde)", color=COLORS["accent_warm"])
        ax2.tick_params(axis="y", colors=COLORS["accent_warm"])

        # Schadstoff-Linien
        ax.plot(
            df_tag.index, df_tag["o3_land"],
            label="Ozon (O₃) Land – Tiefenbach",
            color=COLORS["good"], linewidth=3, zorder=3,
        )
        ax.plot(
            df_tag.index, df_tag["o3_stadt"],
            label="Ozon (O₃) Stadt – Nürnberg",
            color=COLORS["text_muted"], linewidth=2.5, zorder=3,
        )
        ax.plot(
            df_tag.index, df_tag["no2_stadt"],
            label="Stickstoffdioxid (NO₂) Stadt – Nürnberg",
            color=COLORS["bad"], linestyle="--", linewidth=2, zorder=3,
        )

        # Berufsverkehr-Zonen nur am Werktag
        if pd.to_datetime(tag).weekday() < 5:
            day = pd.to_datetime(tag)
            ax.axvspan(
                day + pd.Timedelta(hours=6, minutes=30),
                day + pd.Timedelta(hours=9, minutes=30),
                color=COLORS["grid"], alpha=0.35, zorder=1,
            )
            ax.axvspan(
                day + pd.Timedelta(hours=15, minutes=30),
                day + pd.Timedelta(hours=18, minutes=30),
                color=COLORS["grid"], alpha=0.35, zorder=1,
            )

        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_xlabel(f"Uhrzeit am {label}")
        ax.set_ylim(0, 170)
        ax.set_title(label, pad=10)

    axes[0].set_ylabel("Konzentration (µg/m³)")

    # Gemeinsame Legende unten
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(mpatches.Patch(color=COLORS["accent_warm"], alpha=0.20))
    labels.append("Sonnenschein (% der Stunde)")
    handles.append(mpatches.Patch(color=COLORS["grid"], alpha=0.35))
    labels.append("Berufsverkehr (nur Werktag)")

    fig.legend(
        handles=handles, labels=labels,
        loc="lower center", bbox_to_anchor=(0.5, -0.02),
        ncol=5, frameon=False,
    )

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def _baue_titrationsdaten(
    df_stadt: pd.DataFrame,
    df_land: pd.DataFrame,
) -> pd.DataFrame:
    """Bereitet das Merge-DataFrame für die Titrations-Plots vor.

    Parameters
    ----------
    df_stadt : pd.DataFrame
        Stündliche Nürnberg-Daten. Spalten: ``datum``, ``stunde``,
        ``o3``, ``no2``, ``sonnenscheindauer_minuten``.
    df_land : pd.DataFrame
        Stündliche Tiefenbach-Daten
        (``o3_stundenwerte_2018_station_tiefenbach.parquet``).
        Spalten: ``timestamp``, ``o3_land``.
    """
    df_s = df_stadt.copy()
    df_s["timestamp"] = pd.to_datetime(df_s["datum"]) + pd.to_timedelta(
        df_s["stunde"] - 1, unit="h"
    )
    df_s = df_s[["timestamp", "o3", "no2", "sonnenscheindauer_minuten"]].rename(
        columns={"o3": "o3_stadt", "no2": "no2_stadt"}
    )
    df_s["sonne_prozent"] = df_s["sonnenscheindauer_minuten"] / 60 * 100

    df_merged = pd.merge(df_s, df_land, on="timestamp", how="inner")
    df_merged = df_merged.set_index("timestamp").sort_index()
    return df_merged


def titration_wettergematcht(
    df_stadt: pd.DataFrame,
    df_land: pd.DataFrame,
) -> plt.Figure:
    """
    Titrationseffekt bei nahezu identischem Wetter: Di 24.07. vs. So 19.08.2018.

    Beide Tage wiesen ähnliche Sonnenstunden und Temperaturen auf; der einzige
    wesentliche Unterschied war das NO₂-Aufkommen durch den Berufsverkehr am
    Dienstag. Das Nebeneinander demonstriert die Titrations-Reaktion
    NO + O₃ → NO₂ + O₂ im städtischen Morgenprofil.

    Parameters
    ----------
    df_stadt : pd.DataFrame
        Stündliche Nürnberg-Daten (data.parquet). Benötigte Spalten:
        ``datum``, ``stunde``, ``o3``, ``no2``, ``sonnenscheindauer_minuten``.
    df_land : pd.DataFrame
        Stündliche Tiefenbach-Daten
        (o3_stundenwerte_2018_station_tiefenbach.parquet).
        Benötigte Spalten: ``timestamp``, ``o3_land``.

    Returns
    -------
    matplotlib.figure.Figure
        Zwei-Panel-Plot (links: Dienstag, rechts: Sonntag).
    """
    tage = {
        "2018-07-24": "Dienstag, 24.07.2018",
        "2018-08-19": "Sonntag, 19.08.2018",
    }
    df_merged = _baue_titrationsdaten(df_stadt, df_land)
    return _titration_zweitageplot(df_merged, tage)

def box_ozon_stadt_land_nach_saison(
    df_stadt: pd.DataFrame,
    df_land: pd.DataFrame,
    jahr_von: int = 2016,
    jahr_bis: int = 2025,
) -> plt.Figure:
    """
    Boxplot: O₃-Tagesmaxima nach Jahreszeit, gruppiert nach Stadt (Nürnberg)
    und Land (Tiefenbach).

    Zeigt das Ozon-Paradoxon als VERTEILUNG statt als Mittelwert: je Jahreszeit
    stehen zwei Boxen (Stadt/Land) nebeneinander. Sichtbar werden damit (a) Ozon
    als ausgeprägtes Sommerphänomen und (b) den saisonabhängigen Stadt-Land-
    Abstand: Das städtische Tagesmaximum schwankt stark übers Jahr, das Land
    bleibt ganzjährig stabil – der Abstand ist im Winterhalbjahr groß, im
    Sommer klein – inklusive Streuung und Ausreißern, die ein einzelner
    Mittelwert verschluckt.

    Vergleichsbasis sind Tagesmaxima beider Stationen im Überlappungszeitraum
    2016–2025: Das Land liegt nur als Tagesmax vor, die Stadt wird aus den
    Stundenwerten entsprechend zu Tagesmaxima aggregiert. So stehen beide
    Stationen auf derselben Aggregationsebene.

    Parameters
    ----------
    df_stadt : pd.DataFrame
        Stündliche Nürnberg-Daten (data.parquet). Benötigt: ``datum``, ``o3``.
    df_land : pd.DataFrame
        O₃-Tagesmaxima Tiefenbach
        (o3_dailymax_2016_2025_station_tiefenbach_bayern.parquet).
        Benötigt: ``datum``, ``o3_land``.

    Returns
    -------
    matplotlib.figure.Figure
    """
    # -- Stadt: Stundenwerte -> Tagesmaxima --------------------------------
    df_s = df_stadt[["datum", "o3"]].copy()
    df_s["datum"] = pd.to_datetime(df_s["datum"])
    df_s = df_s[(df_s["datum"].dt.year >= jahr_von) & (df_s["datum"].dt.year <= jahr_bis)]
    df_s = df_s.dropna(subset=["o3"])
    df_s["tag"] = df_s["datum"].dt.normalize()
    df_s = df_s.groupby("tag")["o3"].max().reset_index()
    df_s = df_s.rename(columns={"tag": "datum", "o3": "wert"})
    df_s["saison"] = df_s["datum"].dt.month.map(_saison_aus_monat)

    # -- Land: liegt bereits als Tagesmax vor ------------------------------
    df_l = df_land[["datum", "o3_land"]].copy()
    df_l["datum"] = pd.to_datetime(df_l["datum"])
    df_l = df_l[(df_l["datum"].dt.year >= jahr_von) & (df_l["datum"].dt.year <= jahr_bis)]
    df_l = df_l.dropna(subset=["o3_land"]).rename(columns={"o3_land": "wert"})
    df_l["saison"] = df_l["datum"].dt.month.map(_saison_aus_monat)

    # -- Plot: je Saison zwei Boxen (Stadt links, Land rechts) -------------
    fig, ax = plt.subplots(figsize=(12, 7))

    breite = 0.3
    offset = 0.2
    farbe_stadt = COLORS["text_muted"]   # konsistent mit ozonparadoxon()
    farbe_land  = COLORS["good"]

    for i, saison in enumerate(SAISON_REIHENFOLGE):
        werte_stadt = df_s.loc[df_s["saison"] == saison, "wert"].values
        werte_land  = df_l.loc[df_l["saison"] == saison, "wert"].values

        if len(werte_stadt):
            bp_s = ax.boxplot(werte_stadt, positions=[i - offset], widths=breite,
                              patch_artist=True, showfliers=False)
            for box in bp_s["boxes"]:
                box.set_facecolor(farbe_stadt); box.set_alpha(0.85)
            for med in bp_s["medians"]:
                med.set_color(COLORS["text"]); med.set_linewidth(1.5)

        if len(werte_land):
            bp_l = ax.boxplot(werte_land, positions=[i + offset], widths=breite,
                              patch_artist=True, showfliers=False)
            for box in bp_l["boxes"]:
                box.set_facecolor(farbe_land); box.set_alpha(0.85)
            for med in bp_l["medians"]:
                med.set_color(COLORS["text"]); med.set_linewidth(1.5)

    ax.set_xticks(range(len(SAISON_REIHENFOLGE)))
    ax.set_xticklabels(SAISON_REIHENFOLGE)
    ax.set_ylabel("O₃-Tagesmaximum (µg/m³)")
    ax.set_title(
        "Ozon-Paradoxon als Verteilung: Stadt vs. Land je Jahreszeit\n"
        f"Tagesmaxima {jahr_von}–{jahr_bis} – Stadt stark saisonabhängig, Land ganzjährig stabil",
        fontsize=14, fontweight="bold", pad=12,
    )
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    legenden_handles = [
        mpatches.Patch(facecolor=farbe_stadt, alpha=0.85, label="Stadt – Nürnberg"),
        mpatches.Patch(facecolor=farbe_land,  alpha=0.85, label="Land – Tiefenbach"),
    ]
    ax.legend(handles=legenden_handles, loc="upper right", frameon=False)

    fig.tight_layout()
    return fig


def scatter_ozon_temperatur(df: pd.DataFrame, anzahl_bins: int = 20) -> plt.Figure:
    """
    Hexbin-Dichte O₃ vs. Temperatur mit überlagerter Bin-Mittelwert-Kurve.

    Bei ~394.000 Stundenpunkten würde ein rohes Streudiagramm zum schwarzen
    Klumpen (Overplotting). Stattdessen zeigt eine Hexbin-Dichte (logarithmisch
    skaliert), WO die Masse der Punkte liegt; die überlagerte Linie verbindet
    die mittleren O₃-Werte je Temperatur-Bin und macht die FORM des
    Zusammenhangs sichtbar.

    Kernaussage: Der Zusammenhang ist nichtlinear – O₃ steigt mit der Temperatur
    und flacht bei großer Hitze ab (Sättigung). Genau diese Krümmung bleibt in
    einer einzelnen Korrelationszahl unsichtbar und begründet, warum der Random
    Forest (folgende Tabs) den linearen OLS schlägt.

    Parameters
    ----------
    df : pd.DataFrame
        Stundenwerte aus data.parquet. Benötigt: ``temperatur``, ``o3``.
    anzahl_bins : int
        Anzahl der Temperatur-Bins für die Mittelwert-Kurve.

    Returns
    -------
    matplotlib.figure.Figure
    """
    sub = df[["temperatur", "o3"]].dropna()

    fig, ax = plt.subplots(figsize=(11, 7))

    # -- Punktdichte als Hexbin (log-Skala gegen Overplotting) -------------
    hb = ax.hexbin(
        sub["temperatur"], sub["o3"],
        gridsize=45, bins="log", cmap="viridis", mincnt=1,
    )
    cbar = fig.colorbar(hb, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Anzahl Stunden (log)", fontsize=10)

    # -- Bin-Mittelwerte: Form des Zusammenhangs ---------------------------
    bins = pd.cut(sub["temperatur"], bins=anzahl_bins)
    gruppe = sub.groupby(bins, observed=True)["o3"].agg(["mean", "count"])
    gruppe["mitte"] = [iv.mid for iv in gruppe.index]
    # nur Bins mit genug Punkten -> stabile Mittel an den Temperatur-Rändern
    gruppe = gruppe[gruppe["count"] >= 50]

    ax.plot(
        gruppe["mitte"], gruppe["mean"],
        color=COLORS["bad"], linewidth=2.5, marker="o", markersize=5,
        label="Ø O₃ je Temperatur-Bin",
    )

    ax.set_xlabel("Temperatur (°C)")
    ax.set_ylabel("O₃ (µg/m³)")
    ax.set_title(
        "Ozon vs. Temperatur: nichtlinearer Zusammenhang\n"
        "Punktdichte (Hexbin) + mittlere O₃-Kurve je Temperatur-Bin",
        fontsize=14, fontweight="bold", pad=12,
    )
    ax.legend(loc="upper left", frameon=False)

    fig.tight_layout()
    return fig


def korrelationsmatrix_ganzjahr_vs_sommer(df: pd.DataFrame) -> plt.Figure:
    """
    Zeichnet zwei Spearman-Korrelations-Heatmaps nebeneinander:
      - links:  gesamtes Jahr (alle Monate)   – "Rohbild"
      - rechts: nur Sommer (Jun/Jul/Aug)        – photochemisches Regime

    Methodischer Hintergrund
    ------------------------
    Beide Panels nutzen Spearman (robust gegen Ausreißer, erfasst monotone
    nichtlineare Zusammenhänge). Variiert wird hier NICHT die Methode, sondern
    der Zeitausschnitt. Der Sommerfilter entfernt die *Saison-Achse* (Winter-NO₂-
    Spitzen durch Inversionswetterlagen vs. Sommer-O₃-Peaks) und legt damit die
    photochemische Dynamik freier. Die DIFFERENZ beider Matrizen ist die
    eigentliche Aussage: Verschärft sich z. B. O₃↔Temperatur im Sommer, wird
    der Saisoneffekt sichtbar.

    WICHTIG: Der Sommerfilter beseitigt NUR die Saison-Achse. Tagesgang
    (Titration) und Langzeittrend (Klimawandel) stecken weiterhin in den rohen
    Stundenwerten – die Sommer-Matrix ist also kein "neutraler", sondern ein
    *bedingter* Ausschnitt (Bedingung: Sommerregime).

    Args:
        df: DataFrame mit den Stundenwerten aus data.parquet (Spalte ``datum``
            als datetime64 wird zum Filtern benötigt).

    Returns:
        matplotlib.figure.Figure mit zwei nebeneinanderliegenden Heatmaps.
    """
    spalten = [
        "o3",
        "no2",
        "temperatur",
        "relative_luftfeuchtigkeit",
        "sonnenscheindauer_minuten",
        "windgeschwindigkeit",
        "luftdruck",
    ]
    spalten = [c for c in spalten if c in df.columns]  # defensiv

    labels = {
        "o3": "Ozon (O₃)",
        "no2": "Stickstoffdioxid (NO₂)",
        "temperatur": "Temperatur",
        "relative_luftfeuchtigkeit": "Rel. Luftfeuchte",
        "sonnenscheindauer_minuten": "Sonnenscheindauer",
        "windgeschwindigkeit": "Windgeschwindigkeit",
        "luftdruck": "Luftdruck",
    }
    anzeige_labels = [labels.get(c, c) for c in spalten]

    # --- Zeitausschnitte: ganzes Jahr vs. nur Sommer (meteorologisch Jun–Aug) ---
    df_jahr   = df
    df_sommer = df[df["datum"].dt.month.isin([6, 7, 8])]

    corr_jahr   = df_jahr[spalten].corr(method="spearman")
    corr_sommer = df_sommer[spalten].corr(method="spearman")

    # Stichprobengröße (vollständige O₃-Stunden) – fürs Verteidigen der Panels
    n_jahr   = int(df_jahr["o3"].notna().sum())
    n_sommer = int(df_sommer["o3"].notna().sum())

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    panels = [
        (axes[0], corr_jahr,   f"Gesamtes Jahr  (n = {n_jahr:,} h)"),
        (axes[1], corr_sommer, f"Nur Sommer · Jun–Aug  (n = {n_sommer:,} h)"),
    ]

    for ax, corr, titel in panels:
        im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")

        ax.set_xticks(range(len(spalten)))
        ax.set_yticks(range(len(spalten)))
        ax.set_xticklabels(anzeige_labels, rotation=45, ha="right", fontsize=10)
        ax.set_yticklabels(anzeige_labels, fontsize=10)

        for i in range(len(spalten)):
            for j in range(len(spalten)):
                wert = corr.iloc[i, j]
                farbe = COLORS["text"] if abs(wert) < 0.5 else "#ffffff"
                ax.text(j, i, f"{wert:.2f}", ha="center", va="center",
                        fontsize=9, color=farbe)

        ax.set_title(titel, fontsize=14, fontweight="bold", pad=12)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=9)

    fig.suptitle(
        "Spearman-Korrelation: Gesamtes Jahr vs. Sommerregime\n"
        "Gleiche Methode, anderer Zeitausschnitt – der Unterschied ist der Saisoneffekt",
        fontsize=15, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    return fig

def langzeit_korrelation_jahresmittel(df: pd.DataFrame) -> pd.Series:
    """
    Spearman-Korrelation auf JAHRESMITTELN gegen die Zeitachse 'jahr'.

    Durch die Aggregation auf Jahresebene fallen Tagesgang und Saison weg –
    der Langzeittrend tritt damit als EINZELNE Zahl hervor. Die Stundenmatrix
    kann das prinzipiell nicht, weil sie keine Zeitachse besitzt und von der
    Tag/Saison-Varianz dominiert wird.

    Hinweis: Basiert auf ~45 Jahrespunkten – das ist für eine Trendaussage
    angemessen (monotone Richtung über die Jahre), aber bewusst eine andere
    Aggregationsebene als die Stundenmatrix.
    """
    jahres = (
        df.assign(jahr=df["datum"].dt.year)
          .groupby("jahr")[["o3", "no2", "temperatur"]]
          .mean()
    )
    jahres["jahr"] = jahres.index
    corr = jahres.corr(method="spearman")["jahr"].drop("jahr")
    return corr.rename("Spearman-Korrelation mit dem Jahr (Langzeittrend)")


def ols_modellvergleich(df: pd.DataFrame) -> tuple[plt.Figure, pd.DataFrame]:
    """
    Rechnet zwei OLS-Modelle zur Erklärung von O₃ und stellt die
    standardisierten Koeffizienten gegenüber:
      - Modell 1: nur Wettervariablen
      - Modell 2: Wetter + Schadstoffe (NO₂, PM10)

    Standardisierte Prädiktoren (z-Scores) machen die Koeffizienten direkt
    vergleichbar: Der Betrag zeigt, wie stark eine Variable auf O₃ wirkt.

    Args:
        df: DataFrame mit den Stundenwerten aus data.parquet.

    Returns:
        (fig, kennzahlen): Balkendiagramm der Koeffizienten und ein
        DataFrame mit R², adj. R² und Beobachtungszahl je Modell.
    """
    import statsmodels.api as sm
    from sklearn.preprocessing import StandardScaler

    ziel = "o3"
    wetter = [
        "temperatur",
        "relative_luftfeuchtigkeit",
        "sonnenscheindauer_minuten",
        "windgeschwindigkeit",
        "luftdruck",
        "gesamtbewoelkung",
    ]
    schadstoffe = ["no2", "pm10"]

    labels = {
        "temperatur": "Temperatur",
        "relative_luftfeuchtigkeit": "Rel. Luftfeuchte",
        "sonnenscheindauer_minuten": "Sonnenscheindauer",
        "windgeschwindigkeit": "Windgeschwindigkeit",
        "luftdruck": "Luftdruck",
        "gesamtbewoelkung": "Gesamtbewölkung",
        "no2": "Stickstoffdioxid (NO₂)",
        "pm10": "Feinstaub (PM10)",
    }

    def fit(praediktoren: list[str]):
        sub = df[[ziel] + praediktoren].dropna()
        X = StandardScaler().fit_transform(sub[praediktoren].values)
        X = sm.add_constant(X)
        modell = sm.OLS(sub[ziel].values, X).fit()
        # Koeffizienten ohne Intercept, als Series mit Variablennamen
        coefs = pd.Series(modell.params[1:], index=praediktoren)
        return modell, coefs, sub.shape[0]

    m1, coef1, n1 = fit(wetter)
    m2, coef2, n2 = fit(wetter + schadstoffe)

    kennzahlen = pd.DataFrame(
        {
            "Modell": ["Nur Wetter", "Wetter + Schadstoffe"],
            "R²": [round(m1.rsquared, 3), round(m2.rsquared, 3)],
            "Adj. R²": [round(m1.rsquared_adj, 3), round(m2.rsquared_adj, 3)],
            "Beobachtungen": [n1, n2],
        }
    )

    # --- Plot: Koeffizienten beider Modelle nebeneinander ---
    alle_vars = wetter + schadstoffe
    anzeige = [labels.get(v, v) for v in alle_vars]
    y_pos = range(len(alle_vars))

    # Werte je Modell (NaN, wo Variable nicht im Modell ist)
    werte_m1 = [coef1.get(v, float("nan")) for v in alle_vars]
    werte_m2 = [coef2.get(v, float("nan")) for v in alle_vars]

    fig, ax = plt.subplots(figsize=(12, 7))
    hoehe = 0.38

    ax.barh(
        [y - hoehe / 2 for y in y_pos], werte_m1, height=hoehe,
        label=f"Nur Wetter (R²={m1.rsquared:.2f})",
        color=COLORS["accent"],
    )
    ax.barh(
        [y + hoehe / 2 for y in y_pos], werte_m2, height=hoehe,
        label=f"Wetter + Schadstoffe (R²={m2.rsquared:.2f})",
        color=COLORS["accent_warm"],
    )

    ax.axvline(0, color=COLORS["text_muted"], linewidth=0.8)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(anzeige, fontsize=11)
    ax.invert_yaxis()  # erste Variable oben
    ax.set_xlabel(
        "Standardisierter Koeffizient (β) – Effekt auf O₃ in µg/m³ je Standardabweichung",
        fontsize=11,
    )
    ax.set_title(
        "OLS-Modellvergleich: Welche Faktoren treiben das Ozon?\n"
        "Standardisierte Koeffizienten – Betrag = Stärke, Vorzeichen = Richtung",
        fontsize=15, fontweight="bold", pad=15,
    )
    ax.legend(loc="lower right", frameon=False, fontsize=11)
    ax.grid(True, axis="x", linestyle=":", alpha=0.6)

    fig.tight_layout()
    return fig, kennzahlen

def rf_feature_importance_und_vergleich(
    importances: pd.Series,
    r2_ols: float,
    r2_rf: float,
) -> plt.Figure:
    """
    Zeichnet zwei Panels nebeneinander:
      - links: Feature Importance des Random Forest (horizontale Balken)
      - rechts: R²-Vergleich OLS vs. Random Forest (Balken)

    Die Funktion rechnet NICHT selbst – Modell und Kennzahlen werden übergeben,
    damit das (teure) Training in app.py gecacht werden kann.

    Die Importance-Werte stammen aus der Permutation Importance (mittlerer
    R²-Verlust beim Durchmischen einer Variable auf den Testdaten). Sie sind
    KEINE Anteile und summieren nicht auf 1; groessere Werte bedeuten groesseren
    Vorhersageverlust und damit hoehere Wichtigkeit.

    Args:
        importances: Series {feature_name: permutation_importance}, bereits sortiert.
        r2_ols: Test-R² des OLS-Modells (Wetter + Schadstoffe).
        r2_rf:  Test-R² des Random-Forest-Modells.

    Returns:
        matplotlib.figure.Figure mit zwei Panels.
    """
    labels = {
        "temperatur": "Temperatur",
        "relative_luftfeuchtigkeit": "Rel. Luftfeuchte",
        "sonnenscheindauer_minuten": "Sonnenscheindauer",
        "windgeschwindigkeit": "Windgeschwindigkeit",
        "luftdruck": "Luftdruck",
        "gesamtbewoelkung": "Gesamtbewölkung",
        "no2": "Stickstoffdioxid (NO₂)",
        "pm10": "Feinstaub (PM10)",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7),
                                   gridspec_kw={"width_ratios": [3, 2]})

    # --- Panel 1: Feature Importance (Permutation) ---
    imp_sorted = importances.sort_values(ascending=True)  # kleinste unten
    anzeige = [labels.get(v, v) for v in imp_sorted.index]
    max_imp = max(imp_sorted.values)
    abstand = max_imp * 0.02  # Textabstand relativ zur Skala (robust bei kleinen Werten)
    ax1.barh(anzeige, imp_sorted.values, color=COLORS["accent"])
    for i, v in enumerate(imp_sorted.values):
        ax1.text(v + abstand, i, f"{v:.3f}", va="center",
                 fontsize=10, color=COLORS["text"])
    ax1.set_xlabel("Permutation Importance (R²-Verlust beim Durchmischen)", fontsize=11)
    ax1.set_title("Welcher Faktor treibt das Ozon?\nRandom-Forest-Wichtigkeit",
                  fontsize=14, fontweight="bold", pad=12)
    ax1.set_xlim(0, max_imp * 1.15)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    # --- Panel 2: R²-Vergleich OLS vs. RF ---
    modelle = ["OLS\n(linear)", "Random Forest\n(nichtlinear)"]
    werte = [r2_ols, r2_rf]
    farben = [COLORS["accent_warm"], COLORS["good"]]
    balken = ax2.bar(modelle, werte, color=farben, width=0.6)
    for b, v in zip(balken, werte):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}",
                 ha="center", fontsize=13, fontweight="bold", color=COLORS["text"])
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("Test-R² (erklärte Varianz)", fontsize=11)
    ax2.set_title("Modellgüte im Vergleich\nNichtlinear schlägt linear",
                  fontsize=14, fontweight="bold", pad=12)
    ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

    fig.tight_layout()
    return fig