#!/usr/bin/env python3
"""
Übersetzbare Texte aus den deutschen Seiten herausziehen.

Einmal ausgeführt, erzeugt dieses Skript aus src/pages/<seite>.de.html:

  * src/pages/<seite>.tpl.html  — das Gerüst, Texte durch {{t:id}} ersetzt
  * src/i18n/text-de.json       — die deutschen Texte unter denselben ids

Die Übersetzungen entstehen dann als text-en.json, text-ru.json und
text-el.json mit genau denselben ids. Dadurch gibt es die Struktur einer
Seite nur ein einziges Mal: Wird ein Abschnitt umgebaut, ändert sich das
Gerüst, und alle vier Sprachen folgen. Die Alternative – vier Kopien
jeder Seite – führt zuverlässig dazu, dass die englische Fassung ein
halbes Jahr später eine andere Struktur hat als die deutsche.

Übersetzt wird auf Blockebene, nicht Wort für Wort: Der Inhalt einer
Überschrift oder eines Absatzes bleibt als Einheit zusammen, inklusive
<br> und <em> darin. Ein Satz, der an einem <em> auseinandergeschnitten
wird, lässt sich in Sprachen mit anderer Satzstellung nicht sinnvoll
übersetzen.

Das Skript ist ein Werkzeug für den Umbau, kein Teil des Bauens. Es
läuft einmal und wird danach nur gebraucht, wenn neue deutsche Seiten
hinzukommen.
"""

import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
PAGES = WURZEL / "src" / "pages"

# Elemente, deren Inhalt übersetzt wird – in dieser Reihenfolge.
#
# Die Reihenfolge ist der Kern des Ganzen: von außen nach innen. Ein
# Absatz mit einem <em> darin muss als ganzer Satz in die Übersetzung
# gehen. Würde man zuerst das <em> herausziehen, zerfiele der Satz in
# Bruchstücke – in Sprachen mit anderer Satzstellung ist er dann nicht
# mehr übersetzbar. Deshalb greifen die Textbehälter zuerst; was danach
# noch frei im Gerüst steht (einzelne Linktexte, lose <span>), holen die
# späteren Durchläufe.
DURCHLAEUFE = [
    r"h1|h2|h3|h4|h5|h6|p|li|summary|label|legend|option|button"
    r"|caption|th|td|dt|dd|blockquote|address",
    r"figcaption",
    r"a",
    r"span|strong",
]

# Inline-Auszeichnung, die innerhalb eines Blocks erlaubt ist.
# Alles andere macht den Block zum Behälter und nicht zum Text.
ERLAUBT = {"br", "em", "span", "a", "strong", "b", "i", "sup"}

# Attribute, die Text für Menschen enthalten.
# data-label liest app.js aus, um bei einem Fehlschlag des Formulars
# einen E-Mail-Entwurf zu bauen. Bliebe es deutsch, stünde in der
# englischen Fassung deutscher Text in der Mail des Besuchers.
ATTRIBUTE = ["alt", "aria-label", "placeholder", "title", "data-label"]

# Inhalte, die keine Übersetzung brauchen: Pfeile, Zahlen, Zeichen.
OHNE_TEXT = re.compile(r"^[\s\d↗↓↑→←×+−·/&.,:()–—-]*$")


def enthaelt_block(inner: str) -> bool:
    """Steckt in diesem Inhalt ein weiterer Behälter?"""
    for tag in re.findall(r"<\s*/?\s*([a-z0-9]+)", inner, re.I):
        if tag.lower() not in ERLAUBT:
            return True
    return False


def extrahieren(seite: str, html: str, texte: dict) -> str:
    zaehler = [0]

    def neue_id() -> str:
        zaehler[0] += 1
        return f"{seite}.{zaehler[0]:03d}"

    def merken(wert: str) -> str:
        wert = wert.strip()
        # Gleicher Text zweimal auf einer Seite: dieselbe id, eine
        # Übersetzung. Spart Arbeit und hält beides zwangsläufig gleich.
        for vorhanden, alt in texte.items():
            if alt == wert and vorhanden.startswith(seite + "."):
                return vorhanden
        kennung = neue_id()
        texte[kennung] = wert
        return kennung

    # 1. Attribute
    def attr_ersetzen(m):
        name, wert = m.group(1), m.group(2)
        if OHNE_TEXT.match(wert) or "{{" in wert:
            return m.group(0)
        return f'{name}="{{{{t:{merken(wert)}}}}}"'

    html = re.sub(
        r'\b(' + "|".join(ATTRIBUTE) + r')="([^"]*)"',
        attr_ersetzen,
        html,
    )

    # 2. Blockinhalte, Durchlauf für Durchlauf von außen nach innen.
    for tags in DURCHLAEUFE:
        muster = re.compile(
            r"<(" + tags + r")((?:\s[^>]*)?)>((?:(?!</?(?:" + tags + r")\b).)*?)</\1>",
            re.S,
        )

        def block_ersetzen(m):
            tag, attrs, inner = m.group(1), m.group(2), m.group(3)
            if not inner.strip() or OHNE_TEXT.match(inner) or "{{t:" in inner:
                return m.group(0)
            if enthaelt_block(inner):
                return m.group(0)
            return f"<{tag}{attrs}>{{{{t:{merken(inner)}}}}}</{tag}>"

        # Mehrfach, weil gleichartige Elemente geschachtelt sein können
        # (etwa <span> in <span>); der Lauf endet, wenn nichts mehr passt.
        for _ in range(12):
            html, n = muster.subn(block_ersetzen, html)
            if n == 0:
                break

    return html


def main():
    texte = {}
    seiten = sorted(p.stem.replace(".de", "") for p in PAGES.glob("*.de.html"))
    for seite in seiten:
        html = (PAGES / f"{seite}.de.html").read_text("utf-8")
        gerüst = extrahieren(seite, html, texte)
        (PAGES / f"{seite}.tpl.html").write_text(gerüst, "utf-8")
        offen = re.findall(r"\{\{t:[^}]+\}\}", gerüst)
        print(f"{seite:14} {len(offen):4} Textstellen")

    ziel = WURZEL / "src" / "i18n" / "text-de.json"
    ziel.write_text(
        json.dumps(texte, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"\n{len(texte)} Texte nach {ziel.relative_to(WURZEL)}")


if __name__ == "__main__":
    sys.exit(main())
