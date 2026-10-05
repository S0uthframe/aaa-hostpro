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
import os
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

# Der Ratgeber liegt unter diesem Pfad und gibt es nur auf Deutsch:
# Die Keyword-Daten, auf denen die Themenwahl beruht, stammen aus dem
# deutschen Markt.
RATGEBER_BASIS = "ratgeber/"

# Mit AAA_ENTWUERFE=1 werden auch Entwuerfe gebaut - zum Ansehen vor der
# Veroeffentlichung. Sie tragen dann noindex und fehlen in Uebersicht
# und Sitemap, landen also nie versehentlich in der Suche.
ENTWUERFE = os.environ.get("AAA_ENTWUERFE") == "1"

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
    """Sprachumschalter.

    In der Kopfzeile als aufklappbares Menü, im Mobilmenü als Reihe.
    Vier nebeneinanderliegende Flaggen kosteten in der Kopfzeile rund
    200 px – bei 1100 px wurde es dort eng. Zugeklappt braucht das Menü
    etwa ein Drittel davon.

    Gebaut als <details>, nicht als JavaScript-Menü: Das Element ist von
    sich aus tastaturbedienbar, klappt auch ohne JavaScript auf und
    folgt derselben Machart wie die FAQ-Abschnitte. Das Skript ergänzt
    nur, was <details> nicht kann – Schließen bei Escape und bei Klick
    daneben.

    Die Flagge allein wäre zu wenig: Flaggen bezeichnen Staaten, nicht
    Sprachen, und aus einem SVG liest ein Screenreader nichts vor.
    Deshalb steht neben jeder Flagge das Kürzel als Text, im Aufklappmenü
    zusätzlich der ausgeschriebene Name in der jeweiligen Sprache.

    Seiten, die es in einer Sprache nicht gibt (Impressum, Datenschutz,
    Ratgeber), verweisen auf die Startseite jener Sprache – nicht auf
    eine Adresse, die 404 liefert.
    """
    def ziel_von(s: dict) -> str:
        ziel_seite = seite if seite in s["slugs"] else "index"
        return root + url(s, ziel_seite)

    nav_label = sprachen[aktiv]["chrome"]["lang_switch"]

    if mobil:
        teile = []
        for code in SPRACHEN:
            s = sprachen[code]
            cur = ' aria-current="true"' if code == aktiv else ''
            lang = '' if code == aktiv else f' lang="{s["lang"]}"'
            teile.append(
                f'<a href="{ziel_von(s)}" hreflang="{s["lang"]}"{lang}{cur} '
                f'aria-label="{s["chrome"]["lang_switch_to"]}">'
                f'{flagge_svg(s["flag"], code + "m")}'
                f'<span class="lang-code">{s["code"]}</span></a>'
            )
        return (f'<nav class="lang-mobile" aria-label="{nav_label}">'
                f'{"".join(teile)}</nav>')

    jetzt = sprachen[aktiv]
    teile = []
    for code in SPRACHEN:
        s = sprachen[code]
        cur = ' aria-current="true"' if code == aktiv else ''
        lang = '' if code == aktiv else f' lang="{s["lang"]}"'
        teile.append(
            f'<a href="{ziel_von(s)}" hreflang="{s["lang"]}"{lang}{cur}>'
            f'{flagge_svg(s["flag"], code + "d")}'
            f'<span class="lang-name">{s["name"]}</span>'
            f'<span class="lang-code">{s["code"]}</span></a>'
        )
    return (
        '<details class="lang">'
        f'<summary><span class="vh">{nav_label}: </span>'
        f'{flagge_svg(jetzt["flag"], "jetzt")}'
        f'<span class="lang-code">{jetzt["code"]}</span>'
        '<span class="lang-pfeil" aria-hidden="true"></span></summary>'
        f'<div class="lang-panel">{"".join(teile)}</div>'
        '</details>'
    )


MONATE = ["Januar", "Februar", "M\u00e4rz", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def datum_lesbar(iso: str) -> str:
    """2026-10-15 -> 15. Oktober 2026. Kein locale noetig - das setzt auf
    Baurechnern voraus, dass die deutsche Lokalisierung installiert ist,
    und faellt sonst still auf Englisch zurueck."""
    j, m, t = iso.split("-")
    return f"{int(t)}. {MONATE[int(m) - 1]} {j}"


def ratgeber_laden():
    daten = json.loads((SRC / "ratgeber" / "artikel.json").read_text("utf-8"))
    alle = daten["artikel"]
    return [a for a in alle if ENTWUERFE or not a.get("entwurf")], alle


def brotkrume(sprache: dict, root: str, titel: str | None) -> str:
    """Sichtbarer Pfad plus BreadcrumbList fuer die Suchmaschine.

    Ohne Brotkrume steht ein Beitrag im Suchergebnis ohne Kontext da -
    und der Besucher, der ueber Google direkt im Artikel landet, hat
    keinen Weg zurueck in die Seitenstruktur.
    """
    glieder = [(sprache["chrome"]["home"], root),
               (sprache["chrome"]["ratgeber"], root + RATGEBER_BASIS)]
    if titel:
        glieder.append((titel, None))
    teile = []
    for name, ziel in glieder:
        if ziel and not (titel is None and ziel.endswith(RATGEBER_BASIS)):
            teile.append(f'<a href="{ziel}">{name}</a>')
        else:
            teile.append(f'<span aria-current="page">{name}</span>')
    label = sprache["chrome"]["brotkrume"]
    return (f'<nav class="brotkrume" aria-label="{label}">'
            + '<span aria-hidden="true">/</span>'.join(teile) + '</nav>')


def brotkrume_schema(sprache: dict, titel: str | None, pfad: str) -> dict:
    eintraege = [(sprache["chrome"]["home"], f"{DOMAIN}/"),
                 (sprache["chrome"]["ratgeber"], f"{DOMAIN}/{RATGEBER_BASIS}")]
    if titel:
        eintraege.append((titel, f"{DOMAIN}/{pfad}"))
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(eintraege)
        ],
    }


def faq_schema(rumpf: str) -> dict | None:
    """Zieht die <details>-Bloecke eines Beitrags als FAQPage heraus.

    Nur was auf der Seite sichtbar steht, kommt ins Schema - alles andere
    waere eine Falschangabe gegenueber der Suchmaschine.
    """
    paare = re.findall(
        r"<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>", rumpf, re.S
    )
    if not paare:
        return None
    def nur_text(h):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h)).strip()
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": nur_text(f),
             "acceptedAnswer": {"@type": "Answer", "text": nur_text(a)}}
            for f, a in paare
        ],
    }


def jsonld_block(*teile) -> str:
    objekte = [t for t in teile if t]
    if not objekte:
        return ""
    daten = {"@context": "https://schema.org", "@graph": objekte}
    text = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    # </script> im Inhalt wuerde den Block vorzeitig schliessen.
    text = text.replace("</", "<\\/")
    return f'<script type="application/ld+json">{text}</script>'


def artikelkarten(artikel: list, root: str) -> str:
    if not artikel:
        return ('<p class="artikel-leer">Die ersten Beitr\u00e4ge erscheinen in '
                'den n\u00e4chsten Tagen.</p>')
    karten = []
    for a in sorted(artikel, key=lambda x: x["datum"], reverse=True):
        ziel = f'{root}{RATGEBER_BASIS}{a["slug"]}/'
        karten.append(
            f'<a class="artikel-karte" href="{ziel}">'
            f'<h3>{a["titel"]}</h3>'
            f'<p>{a["teaser"]}</p>'
            f'<span class="text-link">Weiterlesen <span aria-hidden="true">\u2197</span></span>'
            f'</a>'
        )
    return f'<div class="artikel-liste">{"".join(karten)}</div>'


def ratgeber_sichtbar() -> bool:
    """Gibt es einen veroeffentlichten Beitrag? Davon haengt ab, ob es
    die Uebersicht ueberhaupt gibt - und damit, ob die Fusszeile darauf
    verweisen darf."""
    return bool(ratgeber_laden()[0])


def chrome(sprachen: dict, code: str, seite: str, root: str) -> dict:
    """Die Ersetzungen, die jede Seite braucht: Kopfzeile, Navigation,
    Sprachumschalter, Fußzeile. Herausgeloest, damit die Ratgeber-Seiten
    sie mitbenutzen koennen, statt sie zu duplizieren - zwei Fusszeilen,
    die sich auseinanderentwickeln, waeren genau der Fehler, den dieses
    Projekt vermeiden soll."""
    sprache = sprachen[code]
    # Der Ratgeber steht nur in der deutschen Fussleiste. Die Beitraege
    # gibt es nur auf Deutsch; ein Link ins Leere waere schlimmer als
    # kein Link.
    fuss_ratgeber = ""
    if code == "de" and ratgeber_sichtbar():
        fuss_ratgeber = (f'<a href="{root}{RATGEBER_BASIS}">'
                         f'{sprache["chrome"]["ratgeber"]}</a>')
    return {
        "lang": sprache["lang"],
        "og_locale": sprache["locale"],
        "root": root,
        "home": root + sprache["prefix"] if sprache["prefix"] else root,
        "nav": navigation(sprache, seite, root, mobil=False),
        "nav_mobile": navigation(sprache, seite, root, mobil=True),
        "switch": umschalter(sprachen, code, seite, root, mobil=False),
        "switch_mobile": umschalter(sprachen, code, seite, root, mobil=True),
        "footer_ratgeber": fuss_ratgeber,
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


def bauen():
    sprachen = laden()
    layout = (SRC / "layout.html").read_text("utf-8")
    css_basis = (SRC / "style.css").read_text("utf-8")
    # Reihenfolge: Original-Basis, dann der seitenspezifische Zusatz
    # aus dem Original, dann unsere globalen Ergaenzungen.
    # Zuletzt geschrieben gewinnt in der Kaskade bei gleicher
    # Spezifitaet – unsere Ergaenzungen duerfen die Regeln des Originals
    # nicht ueberstimmen, nur ergaenzen. Deshalb stehen sie am Ende.
    GLOBAL = ["style-lang.css", "style-effekte.css"]
    css_global = "".join((SRC / n).read_text("utf-8") for n in GLOBAL)
    css_zusatz = {
        p.stem.replace("style-", ""): p.read_text("utf-8")
        for p in SRC.glob("style-*.css")
        if p.name not in GLOBAL
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
            css = css_basis + css_zusatz.get(konf.get("extra_css", ""), "") + css_global

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

            ersetzungen = chrome(sprachen, code, seite, root)
            ersetzungen.update({
                "title": sprache["pages"][seite]["title"],
                "description": sprache["pages"][seite]["description"],
                "canonical": f"{DOMAIN}/{pfad}",
                "hreflang": hreflang_tags(sprachen, seite),
                "og_image": konf["og_image"],
                "hero_preload": preload_tag(konf),
                "italic_preload": ITALIC if konf.get("italic", True) else "",
                "css": css,
                "body_class": konf["body_class"],
                "footer_class": ' class="tuck"' if konf.get("tuck", True) else "",
                "main": inhalt.strip(),
                "jsonld": "",
            })

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

    # ---- Ratgeber (nur Deutsch) ----------------------------------------
    sichtbar, alle = ratgeber_laden()
    sprache = sprachen["de"]
    css_ratgeber = css_basis + css_zusatz.get("ratgeber", "") + css_global

    def ratgeber_seite(pfad, titel, beschreibung, rumpf, schema_extra, entwurf,
                       teaser="", datum=""):
        root = tiefe(pfad)
        inhalt = rumpf.replace("{{root}}", root)
        inhalt = re.sub(
            r"\{\{u:([a-z-]+)\}\}",
            lambda m: root + url(sprache, m.group(1)),
            inhalt,
        )
        inhalt = inhalt.replace("{{artikelliste}}", artikelkarten(sichtbar, root))

        # Der Kopf eines Beitrags entsteht aus den Metadaten, nicht in
        # der Inhaltsdatei. So kann die H1 bei keinem Beitrag fehlen -
        # und sie bleibt zwangslaeufig identisch mit dem Titel in
        # artikel.json, in der Brotkrume und im strukturierten Datensatz.
        if pfad != RATGEBER_BASIS:
            datum_text = datum_lesbar(datum)
            inhalt = (
                '<section class="section wrap artikel-kopf">'
                f'<p class="label">{sprache["chrome"]["ratgeber"].upper()}</p>'
                f'<h1>{titel}</h1>'
                f'<p class="artikel-intro">{teaser}</p>'
                f'<p class="artikel-datum">'
                f'<time datetime="{datum}">'
                f'{sprache["chrome"]["aktualisiert"]} {datum_text}</time></p>'
                '</section>'
            ) + inhalt

        inhalt = brotkrume(sprache, root, titel if pfad != RATGEBER_BASIS else None) + inhalt

        kopf = jsonld_block(*schema_extra)
        if entwurf:
            # Ein Entwurf, der doch einmal ausgeliefert wird, soll nicht
            # in der Suche landen.
            kopf = '<meta name="robots" content="noindex,nofollow">' + kopf

        e = chrome(sprachen, "de", "ratgeber", root)
        e.update({
            "title": titel if "AAA HostPro" in titel else f"{titel} | AAA HostPro",
            "description": beschreibung,
            "canonical": f"{DOMAIN}/{pfad}",
            "hreflang": "",          # gibt es nur auf Deutsch
            "og_image": "living-1200.jpg",
            "hero_preload": "",
            "italic_preload": ITALIC,
            "css": css_ratgeber,
            "body_class": "",
            "footer_class": "",
            "main": inhalt.strip(),
            "jsonld": kopf,
        })
        seiteninhalt = layout
        for k, v in e.items():
            seiteninhalt = seiteninhalt.replace("{{" + k + "}}", v)
        uebrig = re.findall(r"\{\{[a-z_:-]+\}\}", seiteninhalt)
        if uebrig:
            raise SystemExit(f"ratgeber/{pfad}: nicht ersetzt {sorted(set(uebrig))}")
        datei = ZIEL / pfad / "index.html"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(seiteninhalt, "utf-8")
        if not entwurf:
            gebaut.append(("de", "ratgeber", pfad))

    # Die Uebersicht entsteht nur, wenn mindestens ein Beitrag
    # veroeffentlicht ist. Eine Rubrikseite ohne Inhalte ist fuer
    # Besucher wertlos und fuer die Suche eine duenne Seite - und der
    # Link in der Fusszeile zeigte sonst ins Leere.
    if not sichtbar:
        print("Ratgeber: kein veroeffentlichter Beitrag, Uebersicht "
              "entfaellt (auch der Link in der Fusszeile)")
    else:
      ratgeber_seite(
          RATGEBER_BASIS,
          "Ferienwohnung vermieten: Ratgeber f\u00fcr Eigent\u00fcmer | AAA HostPro",
          "Was Eigent\u00fcmer vor der ersten Buchung kl\u00e4ren sollten, wie viel Arbeit "
          "Kurzzeitvermietung macht und wann sich die Abgabe an eine Verwaltung rechnet.",
          (SRC / "ratgeber" / "_hub.html").read_text("utf-8"),
          [
              {"@type": "CollectionPage", "@id": f"{DOMAIN}/{RATGEBER_BASIS}",
               "name": "Ratgeber", "inLanguage": "de-DE",
               "isPartOf": {"@type": "WebSite", "url": f"{DOMAIN}/"}},
              brotkrume_schema(sprache, None, RATGEBER_BASIS),
          ],
          entwurf=False,
      )

    # Beitraege
    for a in (alle if ENTWUERFE else sichtbar):
        pfad = f'{RATGEBER_BASIS}{a["slug"]}/'
        rumpf = (SRC / "ratgeber" / f'{a["slug"]}.html').read_text("utf-8")
        artikel_schema = {
            "@type": "Article",
            "headline": a["titel"],
            "description": a["beschreibung"],
            "datePublished": a["datum"],
            "dateModified": a["datum"],
            "inLanguage": "de-DE",
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{DOMAIN}/{pfad}"},
            "author": {"@type": "Organization", "name": "AAA HostPro",
                       "url": f"{DOMAIN}/"},
            "publisher": {"@type": "Organization", "name": "AAA HostPro",
                          "url": f"{DOMAIN}/"},
        }
        ratgeber_seite(
            pfad, a["titel"], a["beschreibung"], rumpf,
            [artikel_schema, brotkrume_schema(sprache, a["titel"], pfad),
             faq_schema(rumpf)],
            entwurf=bool(a.get("entwurf")),
            teaser=a["teaser"], datum=a["datum"],
        )

    entwuerfe = [a for a in alle if a.get("entwurf")]

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
    print(f"\nRatgeber: 1 Uebersicht + {len(sichtbar)} Beitraege"
          + (f", {len(entwuerfe)} Entwuerfe" if entwuerfe else ""))
    if entwuerfe and not ENTWUERFE:
        for a in entwuerfe:
            print(f"  Entwurf (nicht gebaut): {a['slug']}")
    print(f"\nSitemap: {len(gebaut)} Adressen")


if __name__ == "__main__":
    bauen()
