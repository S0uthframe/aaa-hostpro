#!/usr/bin/env python3
"""
AAA HostPro — Seiten bauen
==========================

Erzeugt aus src/ den Ordner public/, der auf den Webspace übertragen
wird. Vier Sprachen: Deutsch in der Wurzel, Englisch, Russisch und
Griechisch darunter.

    python3 build.py

Warum überhaupt gebaut wird
---------------------------
Die Originalseiten trugen ihr CSS inline — sechsmal dieselben 15.524
Zeichen, dazu auf jeder Seite dieselbe Kopf- und Fußzeile. Bei einer
Sprache ist das noch überschaubar. Bei vier wären es 24 Dateien, in
denen jede Änderung an der Navigation 24-mal nachgezogen werden müsste.
Genau so entstehen Seiten, auf denen die Fußzeile je nach Sprache etwas
anderes behauptet.

Deshalb liegt das Gerüst einmal in src/layout.html, das CSS einmal in
src/style.css, und die Texte der Kopf- und Fußzeile in src/i18n/*.json.
Was bleibt, sind die eigentlichen Seiteninhalte: src/pages/<seite>.<sprache>.html

Das Inline-CSS bleibt inline
----------------------------
Es wäre naheliegend, das CSS jetzt in eine externe Datei zu legen —
einmal laden, überall zwischengespeichert. Das wäre aber eine
Verschlechterung: Inline-CSS blockiert kein Rendering durch eine
zusätzliche Anfrage, und die Seite ist mit Font-Preloads sichtbar auf
genau diesen ersten Bildaufbau hin gebaut. Also baut das Skript das CSS
wieder in jede Seite ein. Gepflegt wird es trotzdem nur an einer Stelle.
"""

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from flags import svg as flagge_svg  # noqa: E402

WURZEL = Path(__file__).resolve().parent
SRC = WURZEL / "src"
ZIEL = WURZEL / "public"
DOMAIN = "https://aaa-hostpro.de"

ITALIC = (
    '<link rel="preload" href="/assets/fonts/InstrumentSerif-Italic.woff2" '
    'as="font" type="font/woff2" crossorigin>'
)

# Reihenfolge im Sprachumschalter und in der Sitemap.
SPRACHEN = ["de", "en", "ru", "el"]

# Reihenfolge in der Navigation.
MENUE = ["index", "arbitrage", "co-hosting", "about"]

# Was an einer Seite nicht von der Sprache abhängt: Bilder und das
# Grundgerüst. og_image und das Vorladebild stehen so im Original –
# bei arbitrage zeigt og:image auf living, der Hero lädt aber table.
# Das ist im Original so und wird hier nicht stillschweigend geändert.
SEITEN = {
    "index": {
        "body_class": "has-hero",
        "og_image": "chalet-1200.jpg",
        "preload": ("chalet", [600, 750, 900, 1200, 1672]),
    },
    "arbitrage": {
        "body_class": "has-hero",
        "og_image": "living-1200.jpg",
        "preload": ("table", [600, 750, 900, 1200, 1800]),
    },
    "co-hosting": {
        "body_class": "has-hero",
        "og_image": "living-1200.jpg",
        "preload": ("living", [600, 750, 900, 1200, 1800]),
    },
    "about": {
        "body_class": "has-hero",
        "og_image": "living-1200.jpg",
        "preload": ("kitchen", [600, 750, 900, 1200, 1800]),
    },
    "kontakt": {
        "body_class": "",
        "og_image": "living-1200.jpg",
        "preload": None,
        "extra_css": "kontakt",
        "tuck": False,
    },
    # Impressum und Datenschutz tragen kein <em>, also auch keinen
    # Preload fuer die Kursive: eine vorgeladene Schrift, die die Seite
    # nicht braucht, ist verschenkte Bandbreite auf dem kritischen Pfad.
    "impressum": {
        "body_class": "",
        "og_image": "living-1200.jpg",
        "preload": None,
        "tuck": False,
        "italic": False,
    },
    "datenschutz": {
        "body_class": "",
        "og_image": "living-1200.jpg",
        "preload": None,
        "tuck": False,
        "italic": False,
    },
}


def laden():
    sprachen = {}
    for code in SPRACHEN:
        sprachen[code] = json.loads((SRC / "i18n" / f"{code}.json").read_text("utf-8"))
        sprachen[code]["texte"] = json.loads(
            (SRC / "i18n" / f"text-{code}.json").read_text("utf-8")
        )
    return sprachen


def tiefe(pfad: str) -> str:
    """Relativer Weg zur Wurzel. 'en/contact/' -> '../../'"""
    stufen = len([t for t in pfad.split("/") if t])
    return "./" if stufen == 0 else "../" * stufen


def url(sprache: dict, seite: str) -> str:
    """Wurzelrelativer Pfad einer Seite, z. B. 'en/contact/'."""
    return sprache["prefix"] + sprache["slugs"][seite]


def preload_tag(seite: dict) -> str:
    if not seite["preload"]:
        return ""
    basis, breiten = seite["preload"]
    srcset = ", ".join(f"/assets/img/{basis}-{b}.webp {b}w" for b in breiten)
    return (
        '<link rel="preload" as="image" type="image/webp" '
        f'imagesrcset="{srcset}" imagesizes="100vw" fetchpriority="high">'
    )


def hreflang_tags(sprachen: dict, seite: str) -> str:
    """Nur Sprachen, die diese Seite wirklich haben.

    Impressum und Datenschutz gibt es bewusst nur auf Deutsch. Für sie
    entstehen deshalb keine Alternativen – ein hreflang auf eine Seite,
    die es nicht gibt, ist ein Fehler, den die Search Console auch
    anzeigt.
    """
    vorhanden = [c for c in SPRACHEN if seite in sprachen[c]["slugs"]]
    if len(vorhanden) < 2:
        return ""
    tags = [
        f'<link rel="alternate" hreflang="{sprachen[c]["lang"]}" '
        f'href="{DOMAIN}/{url(sprachen[c], seite)}">'
        for c in vorhanden
    ]
    tags.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{DOMAIN}/{url(sprachen["de"], seite)}">'
    )
    return "".join(tags)


def navigation(sprache: dict, aktuell: str, root: str, mobil: bool) -> str:
    teile = []
    for seite in MENUE:
        ziel = root + sprache["slugs"][seite] if sprache["prefix"] == "" else root + url(sprache, seite)
        cur = ' aria-current="page"' if seite == aktuell else ""
        teile.append(f'<a href="{ziel}"{cur}>{sprache["nav"][seite]}</a>')
    if mobil:
        ziel = root + url(sprache, "kontakt")
        cur = ' aria-current="page"' if aktuell == "kontakt" else ""
        teile.append(f'<a href="{ziel}"{cur}>{sprache["chrome"]["contact"]}</a>')
    teile.append(
        '<a href="http://buchung.aaa-hostpro.de/" target="_blank" '
        f'rel="noopener noreferrer">{sprache["chrome"]["accommodations"]} ↗</a>'
    )
    return "".join(teile)


def umschalter(sprachen: dict, aktiv: str, seite: str, root: str, mobil: bool) -> str:
    """Sprachumschalter mit Flagge und Sprachkürzel.

    Die Flagge allein wäre zu wenig: Flaggen bezeichnen Staaten, nicht
    Sprachen, und ein Screenreader liest aus einem SVG nichts vor.
    Deshalb steht neben jeder Flagge das Kürzel als Text, und der Link
    trägt zusätzlich den ausgeschriebenen Sprachnamen als aria-label.

    Seiten, die es in einer Sprache nicht gibt (Impressum,
    Datenschutz), verweisen auf die Startseite jener Sprache – nicht
    auf eine Adresse, die 404 liefert.
    """
    klasse = "lang-mobile" if mobil else "lang"
    teile = []
    for code in SPRACHEN:
        s = sprachen[code]
        ziel_seite = seite if seite in s["slugs"] else "index"
        ziel = root + url(s, ziel_seite)
        kennung = f'{code}{"m" if mobil else "d"}'
        if code == aktiv:
            teile.append(
                f'<a href="{ziel}" hreflang="{s["lang"]}" aria-current="true" '
                f'aria-label="{s["chrome"]["lang_switch_to"]}">'
                f'{flagge_svg(s["flag"], kennung)}'
                f'<span class="lang-code">{s["code"]}</span></a>'
            )
        else:
            teile.append(
                f'<a href="{ziel}" hreflang="{s["lang"]}" lang="{s["lang"]}" '
                f'aria-label="{s["chrome"]["lang_switch_to"]}">'
                f'{flagge_svg(s["flag"], kennung)}'
                f'<span class="lang-code">{s["code"]}</span></a>'
            )
    nav_label = sprachen[aktiv]["chrome"]["lang_switch"]
    return f'<nav class="{klasse}" aria-label="{nav_label}">{"".join(teile)}</nav>'


def bauen():
    sprachen = laden()
    layout = (SRC / "layout.html").read_text("utf-8")
    css_basis = (SRC / "style.css").read_text("utf-8")
    # Reihenfolge: Original-Basis, dann der seitenspezifische Zusatz
    # aus dem Original, dann unsere Ergaenzung fuer den Umschalter.
    # Zuletzt geschrieben gewinnt in der Kaskade bei gleicher
    # Spezifitaet – unsere Regeln duerfen die des Originals nicht
    # ueberstimmen, nur ergaenzen.
    css_lang = (SRC / "style-lang.css").read_text("utf-8")
    css_zusatz = {
        p.stem.replace("style-", ""): p.read_text("utf-8")
        for p in SRC.glob("style-*.css")
        if p.stem != "style-lang"
    }

    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    ZIEL.mkdir()

    gebaut = []
    for code in SPRACHEN:
        sprache = sprachen[code]
        for seite, slug in sprache["slugs"].items():
            quelle = SRC / "pages" / f"{seite}.tpl.html"
            if not quelle.is_file():
                raise SystemExit(f"Es fehlt {quelle.relative_to(WURZEL)}")

            pfad = url(sprache, seite)
            root = tiefe(pfad)
            konf = SEITEN[seite]
            css = css_basis + css_zusatz.get(konf.get("extra_css", ""), "") + css_lang

            inhalt = quelle.read_text("utf-8")

            # Texte einsetzen. Eine fehlende Übersetzung ist ein Fehler
            # und kein Grund, still auf Deutsch zurückzufallen – eine
            # englische Seite mit deutschen Absätzen darin ist schlimmer
            # als ein abgebrochener Lauf.
            fehlend = []

            def text_einsetzen(m):
                kennung = m.group(1)
                if kennung not in sprache["texte"]:
                    fehlend.append(kennung)
                    return m.group(0)
                return sprache["texte"][kennung]

            inhalt = re.sub(r"\{\{t:([a-z-]+\.\d+)\}\}", text_einsetzen, inhalt)
            if fehlend:
                raise SystemExit(
                    f"{code}/{seite}: {len(fehlend)} Texte fehlen in "
                    f"text-{code}.json: {sorted(set(fehlend))[:6]}"
                )

            # Marker in den Seiteninhalten auflösen
            inhalt = inhalt.replace("{{root}}", root)
            inhalt = re.sub(
                r"\{\{u:([a-z-]+)\}\}",
                lambda m: root + url(sprache, m.group(1))
                if m.group(1) in sprache["slugs"]
                else root + url(sprachen["de"], m.group(1)),
                inhalt,
            )

            ersetzungen = {
                "lang": sprache["lang"],
                "og_locale": sprache["locale"],
                "title": sprache["pages"][seite]["title"],
                "description": sprache["pages"][seite]["description"],
                "canonical": f"{DOMAIN}/{pfad}",
                "hreflang": hreflang_tags(sprachen, seite),
                "og_image": konf["og_image"],
                "hero_preload": preload_tag(konf),
                "css": css,
                "root": root,
                "body_class": konf["body_class"],
                "footer_class": " class=\"tuck\"" if konf.get("tuck", True) else "",
                "italic_preload": ITALIC if konf.get("italic", True) else "",
                "main": inhalt.strip(),
                "home": root + sprache["prefix"] if sprache["prefix"] else root,
                "nav": navigation(sprache, seite, root, mobil=False),
                "nav_mobile": navigation(sprache, seite, root, mobil=True),
                "switch": umschalter(sprachen, code, seite, root, mobil=False),
                "switch_mobile": umschalter(sprachen, code, seite, root, mobil=True),
                "legal_impressum": root + url(sprachen["de"], "impressum"),
                "legal_datenschutz": root + url(sprachen["de"], "datenschutz"),
                "u_kontakt": root + url(sprache, "kontakt"),
                "u_arbitrage": root + url(sprache, "arbitrage"),
                "u_co-hosting": root + url(sprache, "co-hosting"),
                "u_about": root + url(sprache, "about"),
                "t_skip": sprache["chrome"]["skip"],
                "t_home": sprache["chrome"]["home"],
                "t_nav_main": sprache["chrome"]["nav_main"],
                "t_nav_mobile": sprache["chrome"]["nav_mobile"],
                "t_menu": sprache["chrome"]["menu"],
                "t_menu_close": sprache["chrome"]["menu_close"],
                "t_menu_close_aria": sprache["chrome"]["menu_close_aria"],
                "t_contact": sprache["chrome"]["contact"],
                "t_claim": sprache["chrome"]["claim"],
                "t_footer_claim": sprache["chrome"]["footer_claim"],
                "t_discover": sprache["chrome"]["discover"],
                "t_contact_label": sprache["chrome"]["contact_label"],
                "t_stay_connected": sprache["chrome"]["stay_connected"],
                "t_book": sprache["chrome"]["book"],
                "t_website_by": sprache["chrome"]["website_by"],
                "t_impressum": sprache["chrome"]["impressum"],
                "t_datenschutz": sprache["chrome"]["datenschutz"],
                "t_top": sprache["chrome"]["top"],
                "t_nav_arbitrage": sprache["nav"]["arbitrage"],
                "t_nav_co_hosting": sprache["nav"]["co-hosting"],
                "t_nav_about": sprache["nav"]["about"],
            }

            seiteninhalt = layout
            for schluessel, wert in ersetzungen.items():
                seiteninhalt = seiteninhalt.replace("{{" + schluessel + "}}", wert)

            uebrig = re.findall(r"\{\{[a-z_:-]+\}\}", seiteninhalt)
            if uebrig:
                raise SystemExit(
                    f"{code}/{seite}: nicht ersetzte Platzhalter {sorted(set(uebrig))}"
                )

            datei = ZIEL / pfad / "index.html"
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(seiteninhalt, "utf-8")
            gebaut.append((code, seite, pfad))

    # Bilder, Schriften, Skript
    shutil.copytree(WURZEL / "assets", ZIEL / "assets")
    shutil.copy(SRC / "robots.txt", ZIEL / "robots.txt")

    # Sitemap mit Sprachalternativen – so findet Google die
    # Übersetzungen auch dann, wenn es nur die Sitemap liest.
    xhtml = 'xmlns:xhtml="http://www.w3.org/1999/xhtml"'
    zeilen = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" {xhtml}>',
    ]
    for code, seite, pfad in gebaut:
        alt = ""
        vorhanden = [c for c in SPRACHEN if seite in sprachen[c]["slugs"]]
        if len(vorhanden) > 1:
            alt = "".join(
                f'<xhtml:link rel="alternate" hreflang="{sprachen[c]["lang"]}" '
                f'href="{DOMAIN}/{url(sprachen[c], seite)}"/>'
                for c in vorhanden
            )
        zeilen.append(f"<url><loc>{DOMAIN}/{pfad}</loc>{alt}</url>")
    zeilen.append("</urlset>")
    (ZIEL / "sitemap.xml").write_text("".join(zeilen), "utf-8")

    print(f"{len(gebaut)} Seiten gebaut:")
    for code in SPRACHEN:
        seiten = [p for c, s, p in gebaut if c == code]
        print(f"  {code}: {len(seiten):2}  " + ", ".join("/" + p for p in seiten))
    print(f"\nSitemap: {len(gebaut)} Adressen")


if __name__ == "__main__":
    bauen()
