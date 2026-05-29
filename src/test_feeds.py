"""Schneller Feed-Health-Check – lokal ausführen mit: python test_feeds.py"""
import requests
import feedparser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

# Alle Kandidaten – alte + neue – auf einmal testen
FEEDS = [
    # --- alte Liste (vermutlich tot) ---
    ("UBA alt",         "https://www.umweltbundesamt.de/rss/uba-pressemitteilungen.xml"),
    ("EEA alt",         "https://www.eea.europa.eu/en/newsroom/news/RSS"),
    ("DG CLIMA alt",    "https://climate.ec.europa.eu/news_en/rss.xml"),
    ("Copernicus alt",  "https://climate.copernicus.eu/news-and-media/feed"),
    # --- neue Kandidaten ---
    ("BMUKN",           "https://www.bmuv.de/rss/aktuelles"),
    ("tagesschau Klima","https://www.tagesschau.de/wissen/klima/index~rss2.xml"),
    ("DW Umwelt",       "https://rss.dw.com/rdf/rss-de-eco"),
    ("Carbon Brief",    "https://www.carbonbrief.org/feed/"),
    ("Guardian Climate","https://www.theguardian.com/environment/climate-crisis/rss"),
    ("Euractiv Climate","https://www.euractiv.com/sections/climate-environment/feed/"),
]

for name, url in FEEDS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            parsed = feedparser.parse(r.content)
            n = len(parsed.entries)
            status = "✅" if n > 0 else "⚠️ "
            print(f"{status} {name:20s} HTTP {r.status_code}  entries: {n}")
        else:
            print(f"❌ {name:20s} HTTP {r.status_code}")
    except Exception as e:
        print(f"❌ {name:20s} ERROR: {type(e).__name__}: {e}")


"""Letzter Check: BMUKN unter neuer URL, Euractiv mit vollem Header"""
import requests, feedparser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

FEEDS = [
    ("BMUKN Meldungen",   "https://www.bundesumweltministerium.de/meldungen.rss"),
    ("BMUKN Klimaschutz", "https://www.bundesumweltministerium.de/klimaschutz.rss"),
    ("Euractiv Climate",  "https://www.euractiv.com/sections/climate-environment/feed/"),
]

for name, url in FEEDS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            n = len(feedparser.parse(r.content).entries)
            print(f"{'✅' if n else '⚠️ '} {name:20s} HTTP 200  entries: {n}")
        else:
            print(f"❌ {name:20s} HTTP {r.status_code}")
    except Exception as e:
        print(f"❌ {name:20s} ERROR: {type(e).__name__}: {e}")