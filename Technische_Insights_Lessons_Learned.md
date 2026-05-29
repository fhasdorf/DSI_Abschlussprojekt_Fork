## Vorwort

## Vorwort
 
Dieses Projekt entstand als Abschlussarbeit der Data-Science-Fortbildung am
**Data Science Institute Berlin**. Ein herzlicher Dank gilt dem Institut für
die fundierte Ausbildung, die das nötige Rüstzeug für dieses Projekt
vermittelt hat.
 
Die Fortbildung umfasste ein breites Spektrum an Methoden und Werkzeugen der
Datenanalyse: **Python** als zentrale Programmiersprache, **SQL** für die
Datenabfrage, **Power BI** für interaktive Visualisierung und Reporting, die
**explorative Datenanalyse (EDA)**, **ETL-Prozesse** zur Datenaufbereitung
sowie Verfahren des **maschinellen Lernens**.
 
Ein Teil dieser Kompetenzen findet sich direkt in der vorliegenden Arbeit
wieder. Die gesamte Anwendung ist in **Python** umgesetzt; die Datenstrecke
von der Roh-CSV bis zur komprimierten Parquet-Datei bildet einen klassischen
**ETL-Prozess** ab. Die **explorative Datenanalyse** prägt die Tabs zur
Datenbasis und zur Langzeitentwicklung, und mit der OLS-Regression sowie dem
Random Forest kommen zwei Verfahren des **maschinellen Lernens** zum Einsatz.
Die in der Ausbildung ebenfalls vermittelten Werkzeuge SQL und Power BI wurden
hier bewusst nicht verwendet, da die Kombination aus Parquet-Dateien und einer
Streamlit-Oberfläche besser zum Umfang und zur Zielsetzung dieses Projekts
passt.
 
Die folgenden Notizen dokumentieren die wichtigsten technischen Entscheidungen
und Fallstricke entlang dieses Wegs.

## Quellen und methodische Grundlagen

Die folgenden Quellen dienen als methodische Grundlage für die in diesem
Projekt eingesetzten Analyseverfahren. Die IBM-Think-Artikel werden als leicht
zugängliche Einführung genutzt; die wissenschaftliche Grundlage der Verfahren
bilden die Primärarbeiten von Breiman sowie die offizielle scikit-learn-
Dokumentation der konkreten Implementierung.

### Korrelations- und Regressionsanalyse

- **Lineare Regression (OLS)** – Einführung in die Methode der kleinsten
  Quadrate sowie die Modellannahmen (Linearität, Unabhängigkeit der
  Beobachtungen, Homoskedastizität, Normalverteilung der Residuen). Die
  Annahme unabhängiger Beobachtungen ist bei einer stündlichen Zeitreihe
  relevant: Autokorrelation benachbarter Stunden verletzt diese Annahme und
  motiviert die ergänzende, annahmefreie Modellierung per Random Forest.
  IBM Think, „Was ist lineare Regression?“:
  https://www.ibm.com/de-de/think/topics/linear-regression

- **Abwägung zwischen Verzerrung und Varianz (Bias-Variance-Tradeoff)** –
  Grundlage für die Modellauswahl: erklärt, warum ein einzelner, tiefer
  Entscheidungsbaum zu Überanpassung neigt und wie ein Ensemble die
  Gesamtvarianz reduziert.
  IBM Think, „Abwägung zwischen Verzerrung und Varianz“:
  https://www.ibm.com/de-de/think/topics/bias-variance-tradeoff

### Random Forest und Feature Importance

- **Random Forest** – Aufbau aus mehreren Entscheidungsbäumen (Bagging,
  Feature-Randomisierung) sowie die Unterscheidung der Wichtigkeitsmaße:
  Gini-Wichtigkeit (Mean Decrease in Impurity) gegenüber der in diesem Projekt
  verwendeten Permutation Importance (Mean Decrease Accuracy). Letztere wird
  bevorzugt, da sie bei korrelierten Prädiktoren robuster ist.
  IBM Think, „Was ist Random Forest?“:
  https://www.ibm.com/de-de/think/topics/random-forest

- **Breiman, L. (2001): Random Forests.** Machine Learning 45(1), 5–32 –
  Originalarbeit zum Random-Forest-Algorithmus.
  https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf

- **Breiman, L. (1996): Bagging Predictors.** Machine Learning 24(2), 123–140 –
  Originalarbeit zur Bagging-Methode, auf der Random Forest aufbaut.
  https://link.springer.com/content/pdf/10.1007/BF00058655.pdf

### Implementierung

- **scikit-learn: Permutation Importance** – Dokumentation des konkret
  verwendeten Verfahrens (`sklearn.inspection.permutation_importance`),
  inklusive Hinweis, die Importance auf den Testdaten zu berechnen.
  https://scikit-learn.org/stable/modules/permutation_importance.html

- **scikit-learn: RandomForestRegressor** – Dokumentation des verwendeten
  Regressionsmodells.
  https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html

*Alle Online-Quellen zuletzt abgerufen am 28.05.2026.*


## 1. Datenbasis & Datenbeschaffung (Data Sourcing)

Die Analyse basiert auf einer Kombination aus historischen Wetterdaten und Luftschadstoff-Messreihen amtlicher deutscher Messnetze. Beide Quellen wurden über den Zeitstempel zu einem gemeinsamen, stündlich aufgelösten Datensatz zusammengeführt.

### 1.a. Datenquellen

* **Meteorologische Treiber (Features):**
  * **Quelle:** Deutscher Wetterdienst (DWD), Open-Data-Portal.
  * **Variablen:** Temperatur, relative Luftfeuchtigkeit, Windgeschwindigkeit, Windrichtung, Luftdruck, Niederschlagshöhe, Sonnenscheindauer, Gesamtbewölkung.
* **Luftschadstoffe & Zielvariable:**
  * **Quelle:** Umweltbundesamt (UBA) bzw. Bayerisches Landesamt für Umwelt (LfU), Stationsmessungen Großraum Nürnberg.
  * **Variablen:** Stickstoffdioxid (NO₂), Ozon (O₃, Zielvariable), Feinstaub PM₁₀ und PM₂.₅.
* **Ländliche Referenzstation (Stadt-Land-Vergleich):**
  * **Station:** Tiefenbach/Bayern (DWD/LfU) – dient im Ozon-Paradoxon-Modul als ländlicher Gegenpol zur städtischen Messung.

### 1.b. Zeitlicher Rahmen

* **Untersuchungszeitraum:** `1980-01-01` bis `2024-12-31`
* **Zeitliche Auflösung:** Stündlich
* **Datensatzgröße:** ~394.000 Zeilen (Hauptdatensatz `data.parquet`)
* **Zeitzone:** Europe/Berlin

> **⚠️ Wichtiger methodischer Hinweis (Data Science Insight):**
> Die Wetterreihen des DWD reichen lückenlos bis 1980 zurück. Die Luftschadstoff-Messungen setzen je nach Komponente und Station später bzw. lückenhafter ein. Für die Modellierung (Korrelation, Regression, Random Forest) wurde daher konsequent mit **vollständigen Fällen (complete cases)** gearbeitet: Nach dem `dropna()` über alle verwendeten Prädiktoren verbleiben rund **250.000 Zeilen** mit durchgängiger Abdeckung 1980–2023 – mehr als ausreichend für robuste Schätzungen.

### 1.c. Einheiten & Datenvorbereitung

* Alle Gase und Feinstäube (NO₂, O₃, PM₁₀, PM₂.₅) liegen in **µg/m³** vor.
* Der Datensatz enthält zwei Feuchte-Spalten (`luftfeuchtigkeit` und `relative_luftfeuchtigkeit`) aus unterschiedlichen Quellen; für die Modellierung wurde durchgängig `relative_luftfeuchtigkeit` verwendet.
* `pm2x5` weist über 60 % Fehlwerte auf und wurde daher aus den Korrelations- und Modell-Features ausgeschlossen, um Scheinpräzision auf einer verzerrten Teilstichprobe zu vermeiden.
* Fehlende Werte wurden nicht imputiert, sondern paarweise bzw. listenweise ausgeschlossen (`dropna`), um keine künstlichen Zusammenhänge in die Schadstoffchemie einzuführen.

---

## 2. Dynamische Datenerweiterung im RAM (Skalierbarkeit)

**Der Fallstrick:** Das manuelle Bearbeiten von Rohdateien bricht die Automatisierungskette (ETL) und macht das System starr für zukünftige Erweiterungen (z. B. Integration weiterer Städte wie München oder Augsburg).

**Die Lösung:** Stadt- bzw. Kontextspalten werden – wo nötig – erst zur Laufzeit im Arbeitsspeicher erzeugt, statt sie in die Rohdaten zu schreiben. Die Rohdaten (CSV → Parquet) bleiben damit unangetastet und wiederverwendbar.


---

## 3. Die Filter-Bedingung des Jahres-Sliders

```python
dfOrginal[dfOrginal["datum"].dt.year == selected_year].copy()
```

* `dfOrginal["datum"]` greift auf die Datumsspalte zu.
* `.dt.year` ist ein **Accessor**: Er weist Pandas an, die Spalte als Datum zu behandeln und je Eintrag nur das Kalenderjahr zu extrahieren.
* `== selected_year` vergleicht jedes Jahr mit dem im Slider gewählten Wert und erzeugt eine boolesche Maske (True/False je Zeile).

### 3.a. Boolesche Filterung

```python
dfOrginal[ ... ]
```

Pandas nutzt die True/False-Maske als **booleschen Filter** und behält nur die Zeilen, deren Bedingung True ist.

### 3.b. `.copy()` – Best Practice

```python
.copy()
```

Ohne `.copy()` erhielte man nur eine **Sicht** (View) auf den Originaldatensatz. Spätere Änderungen an `df_year` lösten dann eine `SettingWithCopyWarning` aus. `.copy()` erzeugt einen unabhängigen Datensatz im RAM.

> **Streamlit-Kontext:** Da das Skript bei jeder Slider-Bewegung von oben nach unten neu ausgeführt wird, sorgt diese Zeile dafür, dass die nachgelagerten Diagramme dynamisch und konsistent aktualisiert werden.

---

## 4. Dynamische Slider-Grenzen mittels Datetime-Auswertung

**Der Fallstrick:** Fest verdrahtete Min/Max-Werte (Hardcoding, z. B. `min_value=1980`, `max_value=2024`) führen zu Fehlern oder ignorierten Daten, sobald der Datensatz erweitert wird.

**Die Lösung:** Die Grenzen werden vollautomatisch aus den Echtdaten abgeleitet:

```python
min_year = int(dfOrginal["datum"].dt.year.min())
max_year = int(dfOrginal["datum"].dt.year.max())
```



---

## 5. Optisches Feintuning: `config.toml` vs. CSS-Injection

**Der Fallstrick:** Streamlits Standard-Design wirkt für wissenschaftliche Dashboards oft zu großflächig; KPI-Karten (`st.metric`) beanspruchen viel Platz. Über die `config.toml` lassen sich nur grobe Parameter (Primärfarbe, Hintergrund) steuern, nicht aber einzelne Elemente.

**Die Lösung:** Das globale Theme kommt aus der `config.toml`; für präzise Anpassungen von Schriftgrößen und Abständen wird gezielt CSS über `st.markdown(..., unsafe_allow_html=True)` in die Tabs injiziert:

```python
st.markdown(
    """
    <style>
    div[data-testid="stMetricLabel"] p { font-size: 14px !important; }
    div[data-testid="stMetricValue"]   { font-size: 24px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
```


---

## 6. Re-Rendering-Logik & invertierte Delta-Farben

### 6.a. Das Re-Rendering-Modell von Streamlit

In klassischen Web-Frameworks steuert man dynamische Inhalte über JavaScript-Event-Listener. Streamlit arbeitet anders: Jede UI-Interaktion löst einen vollständigen Skript-Rerun von oben nach unten aus. Über eine `if-elif`-Struktur wird gezielt nur der aktive Inhalt gerendert:

```python
if schadstoff_auswahl == "Übersicht aller Stoffe":
    # WHO-Metriken und globale Auswertungen
elif schadstoff_auswahl == "Ozon (O₃)":
    # spezifische Ozon-Grafiken
```

> Der `@st.fragment`-Decorator über den Tab-Funktionen begrenzt diesen Rerun zusätzlich auf das jeweilige Fragment, statt die gesamte App neu zu zeichnen – ein spürbarer Performance-Gewinn bei interaktiven Tabs.

### 6.b. Die „Börsenkurs-Inversion" bei Umweltmetriken

Standardmäßig wertet `st.metric` einen positiven Delta-Wert als *gut* (grün), einen negativen als *schlecht* (rot) – sinnvoll für Umsätze, falsch für Schadstoffe: **Mehr Schadstoff ist ein Alarmzeichen.**

| Situation | Differenz | Gewünschte Farbe |
|---|---|---|
| Jahresmittel **über** WHO-Limit | positiv (+4,2 µg/m³) | Dreieck hoch, **ROT** |
| Jahresmittel **unter** WHO-Limit | negativ (−5,1 µg/m³) | Dreieck runter, **GRÜN** |

```python
diff_ozon = mean_ozon - 100  # positiv bei Überschreitung

st.metric(
    label="Ø Ozon (Ziel: ≤100)",
    value=f"{mean_ozon:.1f} µg/m³",
    delta=f"{diff_ozon:+.1f} µg/m³ vs. WHO",
    delta_color="inverse",  # Plus = Rot, Minus = Grün
)
```

---

## 7. Kaskadierende Filterung: Cache, RAM-Kopie und Unter-Tabs

Die Daten werden im RAM hierarchisch in drei Stufen gefiltert:

| Stufe | Auslöser | Aktion |
|---|---|---|
| **1 – Global** | App-Start | Gesamtdatensatz (~394.000 Zeilen) wird via `@st.cache_data` unveränderlich gecacht |
| **2 – User-Interaktion** | Slider-Bewegung | `df_year = dfOrginal[...].copy()` erstellt eine isolierte Jahreskopie im RAM |
| **3 – Lokal im Tab** | Radio-Button-Klick | `if-elif`-Logik greift auf das bereits vorgefilterte `df_year` zu |


---

## 8. Speicherstrategie: Warum Parquet statt CSV

### 8.a. Spaltenorientierte Speicherung & Komprimierung

CSV speichert zeilenweise als Klartext – bei Hunderttausenden Zeilen ein erheblicher Overhead. Parquet speichert **spaltenorientiert (columnar)**: Da eine Spalte stets denselben Datentyp enthält (z. B. Float für Temperatur), greifen Komprimierungsverfahren (Snappy) sehr effizient.

* **Effekt:** Deutlich kleinere Dateien und geringerer RAM-Verbrauch beim Einlesen gegenüber unkomprimierter CSV.

### 8.b. Ladezeit & Streamlit-Performance

Jede Interaktion löst in Streamlit einen Rerun aus. Parquet bringt hier zwei Vorteile:

* **Selektives Spaltenlesen:** Nur benötigte Spalten werden geladen (`columns=[...]`), statt die gesamte Datei sequenziell zu parsen.
* **Typsicherheit:** Datentypen (inkl. `datetime`) sind im Schema hinterlegt; das aufwendige Parsen von Datums-Strings entfällt. In Kombination mit `@st.cache_data` wird die Datei nur einmal pro Session gelesen.

### 8.c. Skalierungsperspektive (Cloud)

Für eine spätere Cloud-Überführung legt Parquet bereits das Fundament: Serverless-Analytics-Dienste rechnen Kosten nach gescannter Datenmenge ab. Dank Spaltenformat und Komprimierung wird pro Abfrage nur ein Bruchteil der Daten gelesen – kosteneffizient und schnell.


---

## 9. Methodische Modellstrecke: Von Korrelation zu nichtlinearer Vorhersage

Das analytische Herzstück folgt einer bewussten Eskalationslogik – jedes Modell beantwortet eine Frage, an deren Grenze das nächste ansetzt.

### 9.a. Korrelationsanalyse (Spearman statt Pearson)

Als Einstieg wurde geprüft, *welche* Variablen mit Ozon zusammenhängen. Bewusst stand **Spearman** im Vordergrund: Da atmosphärische Daten Ausreißer (Rushhour-Spitzen, Hitzetage) enthalten und die Ozonbildung nichtlinear sättigt, ist die rangbasierte Spearman-Korrelation robuster als Pearson. Die Gegenüberstellung beider Matrizen ist dabei selbst eine Aussage: Wo Spearman und Pearson auseinanderlaufen, ist der Zusammenhang monoton, aber nicht linear.

### 9.b. Multiple lineare Regression (OLS)

Im zweiten Schritt wurde quantifiziert, *wie stark* jeder Faktor wirkt. Zwei Modelle wurden verglichen – nur Wetter vs. Wetter + Schadstoffe –, um den Erklärungsbeitrag der Schadstoffe sichtbar zu machen (R² ≈ 0,58 → 0,65). Die **Standardisierung der Prädiktoren (z-Scores)** macht die Koeffizienten trotz unterschiedlicher Einheiten direkt vergleichbar.

> **Data Science Insight (Multikollinearität):** Das kontraintuitiv negative Vorzeichen der Sonnenscheindauer ist kein Fehler, sondern Folge der starken Kopplung an die Temperatur – der „Sonnen-Effekt" wird vom Temperatur-Koeffizienten aufgenommen. Ein wichtiges Beispiel dafür, dass Regressionskoeffizienten *bedingte* Effekte sind und nicht isoliert interpretiert werden dürfen.

### 9.c. Random Forest (nichtlinear)

Das verbleibende, von OLS unerklärte Drittel der Varianz motiviert das nichtlineare Modell. Der Random Forest hebt das Test-R² spürbar an (≈ 0,65 → 0,78) und liefert über die **Feature Importance** eine Treiber-Rangfolge. Der direkte R²-Vergleich OLS vs. RF schließt die Storyline: Die Verbesserung *ist* der empirische Beleg für die Nichtlinearität der Ozonbildung.

> **Data Science Insight (Interpretation der Importance):** Feature Importance misst den Beitrag zur *Vorhersagegüte*, nicht die *Wirkrichtung* – ob ein Faktor O₃ erhöht oder senkt, zeigen erst die OLS-Koeffizienten. Zudem kann die Importance bei korrelierten Prädiktoren (Temperatur ↔ Sonnenschein) verzerren, da der Wald die Wichtigkeit zwischen austauschbaren Variablen aufteilt. Beide Modelle ergänzen sich daher: OLS für die Richtung, RF für die Vorhersage.

### 9.d. Performance-Entscheidung: `@st.cache_resource`

Das RF-Training auf ~250.000 Zeilen ist zu teuer, um es bei jedem Rerun zu wiederholen. Lösung: Das **trainierte Modell** wird über `@st.cache_resource` (nicht `cache_data`) gecacht – passend, weil ein Modell eine nicht-serialisierbare Ressource ist. Der große DataFrame wird über den Parameternamen `_df` (führender Unterstrich) bewusst vom Hashing ausgenommen. Das Training läuft so genau einmal pro Session, danach reagiert der Tab unmittelbar.

---

## 10. Lessons Learned (Zusammenfassung)

* **Datenwahrheit vor Bequemlichkeit:** Frühe Projektannahmen (Zeitraum, Quellen, Vergleichsstadt) wurden gegen die realen Daten geprüft und korrigiert, statt sie in der Doku fortzuschreiben.
* **Fehlwerte ehrlich behandeln:** Kein blindes Imputieren von Schadstoffdaten; `pm2x5` mit >60 % Lücken wurde bewusst ausgeschlossen.
* **Konsistente Architektur schlägt Einzellösungen:** Ein einheitliches Muster (globales `dfOrginal`, `@st.fragment`-Tabs) verhindert Fehlerklassen wie das wiederkehrende `NameError`/`missing argument`-Problem bei abweichenden Funktionssignaturen.
* **Das richtige Cache-Werkzeug wählen:** `cache_data` für Daten, `cache_resource` für Modelle.
* **Modelle erzählen gemeinsam mehr als einzeln:** Korrelation, OLS und Random Forest sind nicht redundant, sondern bauen aufeinander auf.
