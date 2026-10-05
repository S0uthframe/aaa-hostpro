# aaa-hostpro.de

Website der AAA HostPro — Kurzzeitvermietungs-Management, Bad Abbach.
Statische Seiten, viersprachig: Deutsch, Englisch, Russisch, Griechisch.

## Was hier liegt

```
src/
  layout.html          Gerüst aller Seiten: Kopf, Kopfzeile, Fußzeile
  style.css            das Stylesheet des Originals, unverändert
  style-kontakt.css    Zusatz nur für die Kontaktseite (aus dem Original)
  style-lang.css       Ergänzung für den Sprachumschalter
  flags.py             die vier Flaggen als Inline-SVG
  pages/*.tpl.html     je Seite ein Gerüst, Texte als {{t:id}}
  i18n/de|en|ru|el.json   Titel, Beschreibungen, Navigation, Fußzeile
  i18n/text-*.json        die Seitentexte je Sprache
  robots.txt
assets/                Bilder, Schriften, app.js — unverändert
build.py               erzeugt public/
tools/extract.py       zieht Texte aus deutschen Seiten (nur beim Umbau)
tools/uebersetzungen_*.py   erzeugen die text-*.json
```

`public/` entsteht beim Bauen und liegt nicht im Repository.

## Bauen

```bash
python3 build.py        # erzeugt public/ mit 22 Seiten
```

Lokal ansehen:

```bash
cd public && python3 -m http.server 8000
```

## Warum gebaut wird

Die Originalseiten trugen ihr CSS inline — sechsmal dieselben 15.524
Zeichen, dazu auf jeder Seite dieselbe Kopf- und Fußzeile. Bei einer
Sprache geht das. Bei vier wären es 22 Dateien, in denen jede Änderung
an der Navigation 22-mal nachgezogen werden müsste. Genau so entstehen
Seiten, deren englische Fassung ein halbes Jahr später eine andere
Struktur hat als die deutsche.

Deshalb: Gerüst einmal, CSS einmal, Texte je Sprache.

**Das Inline-CSS bleibt inline.** Es wäre naheliegend, das CSS jetzt in
eine externe Datei zu legen. Das wäre aber eine Verschlechterung:
Inline-CSS kostet keine zusätzliche Anfrage auf dem kritischen Pfad,
und die Seite ist mit ihren Font-Preloads auf genau diesen ersten
Bildaufbau hin gebaut. `build.py` schreibt das CSS daher in jede Seite
zurück — gepflegt wird es trotzdem nur an einer Stelle.

## Sprachen

| Sprache | Adresse | Seiten |
|---|---|---|
| Deutsch | `/` | 7 |
| English | `/en/` | 5 |
| Русский | `/ru/` | 5 |
| Ελληνικά | `/el/` | 5 |

**Impressum und Datenschutz gibt es nur auf Deutsch.** Das ist eine
bewusste Entscheidung, keine Lücke: Für ein deutsches Unternehmen ist
die deutsche Fassung die rechtlich maßgebliche. Eine übersetzte
Datenschutzerklärung erweckt den Eindruck, sie sei es auch — und weicht
nach der ersten Änderung an einer der beiden Fassungen zwangsläufig ab.
Die fremdsprachigen Fußzeilen verweisen deshalb auf die deutschen
Seiten und kennzeichnen das mit „(DE)". Entsprechend tragen diese
beiden Seiten keine `hreflang`-Alternativen.

Der Sprachumschalter steht in der Kopfzeile und, unter 900 px, im
Mobilmenü. Jede Flagge trägt das Sprachkürzel daneben und ein
`aria-label` in der jeweiligen Sprache — Flaggen bezeichnen Staaten,
nicht Sprachen, und aus einem SVG liest ein Screenreader nichts vor.

### Eine Sprache ändern

Text ändern: in `src/i18n/text-<sprache>.json` die betreffende id.
Titel, Beschreibung, Navigation und Fußzeile: in `src/i18n/<sprache>.json`.
Danach `python3 build.py`.

Fehlt eine Übersetzung, bricht der Bau ab und nennt die ids. Das ist
Absicht — eine englische Seite mit deutschen Absätzen darin ist
schlimmer als ein abgebrochener Lauf.

### Eine Sprache hinzufügen

1. `src/i18n/<code>.json` und `src/i18n/text-<code>.json` anlegen
2. Den Code in `build.py` in `SPRACHEN` eintragen
3. Flagge in `src/flags.py` ergänzen

## Ausliefern

**Actions → „Deploy AAA HostPro" → Run workflow.** Zwei Felder:
„dry-run" zeigt nur, was übertragen würde; „deploy" überträgt wirklich
und verlangt zusätzlich das Wort `deploy` im zweiten Feld.

Nötige Secrets (Settings → Secrets and variables → Actions):

| Name | Wert |
|---|---|
| `SSH_HOST` | `w01839ab.kasserver.com` |
| `SSH_USER` | `ssh-w01839ab` |
| `SSH_PORT` | `22` |
| `SSH_PRIVATE_KEY` | privater Schlüssel, inklusive BEGIN- und END-Zeile |
| `DEPLOY_PATH` | `/www/htdocs/w01839ab/aaa-hostpro.de/` |

Der Pfad **mit** Schrägstrich am Ende — ohne ihn legt `rsync` ein
Unterverzeichnis an, statt hineinzukopieren.

`rsync` läuft ohne `--delete`: Was auf dem Server liegt und nicht aus
dem Neubau stammt, bleibt unangetastet.

## Offene Punkte aus dem Originalstand

Diese Dinge sind im ersten Commit unverändert übernommen und bisher
bewusst nicht angefasst worden:

* **`index.htm`** — eine fremde XHTML-Datei von 85 KB mit leerem
  `<title>`, vermutlich die Platzhalterseite des Hosters. Apache
  liefert `index.html` zuerst aus, sie stört also nicht. Sie liegt nur
  herum und sollte irgendwann weg.
* **`assets/style.css`** — liegt im Original da, wird aber von keiner
  Seite verlinkt. Die gepflegte Fassung ist jetzt `src/style.css`.
* **`buchung.aaa-hostpro.de`** ist in der Navigation als `http://`
  verlinkt, nicht `https://`. Die Subdomain liegt auf demselben Server.
  Unverändert gelassen, bis bestätigt ist, dass dort ein gültiges
  Zertifikat liegt.
* **`og:image` auf der Arbitrage-Seite** zeigt auf `living-1200.jpg`,
  der Hero der Seite lädt aber `table`. Sieht nach Kopierfehler aus,
  wurde aber nicht stillschweigend geändert.
* **`hostpro-aaa.de`** existiert als eigenes Verzeichnis auf dem
  Webspace. Falls dort eine Kopie der Website liegt statt einer
  Weiterleitung, ist das aus SEO-Sicht Duplicate Content.

## Kontaktformular

Das Formular sendet per `fetch` an einen n8n-Webhook
(`n8n.srv1450872.hstgr.cloud`). Schlägt das fehl, baut `app.js` aus den
eingegebenen Daten einen `mailto:`-Entwurf als Rückweg. Die
Beschriftungen der Anliegen stehen dafür als `data-label` im Markup und
werden mit übersetzt — sonst stünde in der englischen Fassung deutscher
Text in der E-Mail des Besuchers.
