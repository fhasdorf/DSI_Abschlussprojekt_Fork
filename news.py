# -*- coding: utf-8 -*-
"""
RSS-Feed-Loader für den News-Tab.

Holt aktuelle Pressemeldungen zu Klima, Umwelt und EU-Klimapolitik aus
kostenlosen RSS-Feeds. Keine API-Keys, keine Rate Limits.

Alle Feed-URLs wurden am 27.05.2026 mit `python test_feeds.py` verifiziert.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import feedparser
import requests
import streamlit as st

Sprache = Literal["de", "en"]


@dataclass
class Feed:
    """Beschreibt einen RSS-Feed mit Metadaten für die UI-Darstellung."""

    name: str        # Anzeigename in der Quellenauswahl (st.multiselect)
    url: str         # Vollständige RSS-Feed-URL
    sprache: Sprache # Sprachcode: "de" (Deutsch) oder "en" (Englisch)
    quelle: str      # Kurzbeschreibung der Quelle für die UI-Caption


# Verifizierte Feeds (Stand 27.05.2026). Bei 404er-Fehlern in Zukunft:
# test_feeds.py erneut laufen lassen und URLs aktualisieren.
FEEDS: list[Feed] = [
    # --- Deutsch ---
    Feed(
        name="tagesschau – Klima",
        url="https://www.tagesschau.de/wissen/klima/index~rss2.xml",
        sprache="de",
        quelle="Klima-Berichterstattung der ARD-Tagesschau.",
    ),
    Feed(
        name="Deutsche Welle – Umwelt",
        url="https://rss.dw.com/rdf/rss-de-eco",
        sprache="de",
        quelle="DW-Berichte zu Umwelt, Klima und Nachhaltigkeit.",
    ),
    # --- Englisch ---
    Feed(
        name="Carbon Brief",
        url="https://www.carbonbrief.org/feed/",
        sprache="en",
        quelle="Faktenbasierter Klimajournalismus – Policy, Wissenschaft, EU-Klimarecht.",
    ),
    Feed(
        name="The Guardian – Climate Crisis",
        url="https://www.theguardian.com/environment/climate-crisis/rss",
        sprache="en",
        quelle="Tägliche Klimaberichterstattung des Guardian.",
    ),
]

# Vollständiger Browser-Header-Satz – nötig für Carbon Brief (Cloudflare).
# Tagesschau, DW und Guardian funktionieren auch mit weniger, schadet aber nicht.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


@st.cache_data(ttl=3600, show_spinner=False)
def lade_feed(url: str, max_eintraege: int = 5) -> list[dict]:
    """
    Lädt einen RSS-Feed und gibt eine Liste normalisierter Einträge zurück.

    Parameters
    ----------
    url : str
        URL des RSS-Feeds.
    max_eintraege : int
        Maximale Anzahl Einträge (jüngste zuerst). Default: 5.

    Returns
    -------
    list[dict] mit Keys: titel, link, datum (datetime|None), zusammenfassung
        Leere Liste, wenn der Feed nicht geladen werden konnte.
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        st.warning(f"Feed konnte nicht geladen werden ({url}): {exc}")
        return []

    parsed = feedparser.parse(response.content)

    if parsed.bozo and not parsed.entries:
        st.warning(f"Feed-Format ungültig ({url}): {parsed.bozo_exception}")
        return []

    eintraege: list[dict] = []
    for entry in parsed.entries[:max_eintraege]:
        datum: datetime | None = None
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            if entry.get(key):
                datum = datetime(*entry[key][:6])
                break

        eintraege.append({
            "titel":            entry.get("title", "(kein Titel)"),
            "link":             entry.get("link", "#"),
            "datum":            datum,
            "zusammenfassung":  entry.get("summary", ""),
        })

    return eintraege


def feeds_nach_sprache(sprache: Sprache) -> list[Feed]:
    """
    Filtert die globale Feed-Liste nach Sprachcode.

    Parameters
    ----------
    sprache : Sprache
        ``"de"`` für deutschsprachige, ``"en"`` für englischsprachige Feeds.

    Returns
    -------
    list[Feed]
        Teilmenge von ``FEEDS`` mit passendem Sprachcode.
    """
    return [f for f in FEEDS if f.sprache == sprache]