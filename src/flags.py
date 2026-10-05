"""Flaggen als Inline-SVG.

Warum inline und nicht als Bilddatei oder Emoji:

* Emoji-Flaggen (🇬🇧) zeigt Windows bis heute als Buchstabenpaar "GB"
  an – auf dem häufigsten Betriebssystem unserer Besucher also kaputt.
* Eine Bilddatei pro Flagge wären vier zusätzliche Anfragen für
  zusammen unter 2 KB Inhalt.

Die Zeichnungen folgen den amtlichen Seitenverhältnissen (3:2 bei
Deutschland, Russland und Griechenland, 2:1 beim Union Jack) und den
amtlichen Farben.

{id} wird beim Bauen durch eine eindeutige Kennung ersetzt – der Union
Jack braucht einen clipPath, und der Umschalter steht zweimal auf der
Seite (Kopfzeile und Mobilmenü). Zwei gleiche id-Werte wären ungültiges
HTML und der zweite Verweis würde ins Leere greifen.
"""

FLAGGEN = {
    # Schwarz-Rot-Gold, drei gleiche Bahnen.
    "de": (
        '<svg viewBox="0 0 3 2" aria-hidden="true" focusable="false">'
        '<rect width="3" height="2" fill="#FFCE00"/>'
        '<rect width="3" height="1.3333" fill="#DD0000"/>'
        '<rect width="3" height=".6667" fill="#000"/>'
        "</svg>"
    ),
    # Weiß-Blau-Rot, drei gleiche Bahnen.
    "ru": (
        '<svg viewBox="0 0 3 2" aria-hidden="true" focusable="false">'
        '<rect width="3" height="2" fill="#D52B1E"/>'
        '<rect width="3" height="1.3333" fill="#0039A6"/>'
        '<rect width="3" height=".6667" fill="#fff"/>'
        "</svg>"
    ),
    # Neun Bahnen und das Obereck mit dem Kreuz. Bei 27x18 ist jede
    # Bahn genau 2 hoch, das Obereck 10x10 und die Kreuzarme 2 breit –
    # alles ganzzahlig, also keine Rundungskanten.
    "gr": (
        '<svg viewBox="0 0 27 18" aria-hidden="true" focusable="false">'
        '<rect width="27" height="18" fill="#0D5EAF"/>'
        '<path d="M0 2h27v2H0zm0 4h27v2H0zm0 4h27v2H0zm0 4h27v2H0z" fill="#fff"/>'
        '<rect width="10" height="10" fill="#0D5EAF"/>'
        '<path d="M4 0h2v10H4zM0 4h10v2H0z" fill="#fff"/>'
        "</svg>"
    ),
    # Union Jack. Das Andreaskreuz ist versetzt (counterchanged):
    # Die rote Diagonale liegt nicht mittig auf der weißen, sondern in
    # jedem Viertel zur anderen Seite verschoben. Genau das macht der
    # clipPath – ohne ihn sieht die Flagge falsch aus.
    "gb": (
        '<svg viewBox="0 0 60 30" aria-hidden="true" focusable="false">'
        '<clipPath id="uj{id}">'
        '<path d="M30 15h30v15zv15H30zH0V15zV0h30z"/>'
        "</clipPath>"
        '<path d="M0 0v30h60V0z" fill="#012169"/>'
        '<path d="M0 0 60 30M60 0 0 30" stroke="#fff" stroke-width="6"/>'
        '<path d="M0 0 60 30M60 0 0 30" clip-path="url(#uj{id})" '
        'stroke="#C8102E" stroke-width="4"/>'
        '<path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/>'
        '<path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/>'
        "</svg>"
    ),
}


def svg(flagge: str, kennung: str) -> str:
    """Gibt das SVG mit eindeutiger id zurück."""
    return FLAGGEN[flagge].replace("{id}", kennung)
