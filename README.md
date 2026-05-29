## Ozonbildung unter dem Einfluss von Klima und Verkehr
* Eine Langzeitanalyse für den Großraum Nürnberg mit Fokus auf das Ozon-Paradoxon (Stadt vs. Land, Messstellenvergleich)
##### Autor: Frank Hasdorf

### Dieses Projekt entstand als Abschlussarbeit der Data-Science-Fortbildung am Data Science Institute Berlin. 
#### Ein herzlicher Dank gilt dem Institut für die fundierte Ausbildung, die das nötige Rüstzeug für dieses Projekt vermittelt hat – von der Datenaufbereitung über die Korrelations- und Regressionsanalyse bis hin zum Einsatz des Random Forest. ####

[![Streamlit App]()]()

---

Interaktives Streamlit-Dashboard zur datenbasierten Untersuchung des **Ozon-Paradoxons** im Großraum Nürnberg: Warum sind Ozonwerte in der Stadt trotz höherer Emissionen oft niedriger als auf dem Land? Kern der Analyse ist die photochemische Titration von O₃ durch frisches NO aus dem Kfz-Verkehr.

Der Datensatz umfasst stündliche Wetter- und Schadstoffmessungen von 1980 bis 2024 (~394.000 Zeilen), ergänzt durch DWD-Referenzdaten der ländlichen Station Tiefenbach/Bayern.

## Features

| Tab | Inhalt |
|-----|--------|
| Startseite | Jahres-Slider mit Wetter- und Schadstoffkennzahlen im Vergleich zu WHO-Grenzwerten |
| Datenbasis | Parquet-Vorschau, Schema, Statistik und fehlende Werte |
| Explorative Analyse | Langzeittrend Schadstoffe (NO₂, PM10, PM2.5) und Temperatur/Ozon-Entwicklung seit 1980 |
| Ozon-Paradoxon | Stadt-Land-Vergleich (Nürnberg vs. Tiefenbach) und Titrationseffekt Werktag vs. Sonntag |
| News | Aktuelle Klimameldungen via RSS-Feeds (tagesschau, DW, Carbon Brief, The Guardian) |

## Stack

Python · Streamlit · pandas · matplotlib · Apache Parquet

## Starten

```bash
pip install -r requirements.txt
streamlit run app.py
```
