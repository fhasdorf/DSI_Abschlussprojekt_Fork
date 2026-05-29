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