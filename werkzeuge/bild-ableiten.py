#!/usr/bin/env python3
"""Erzeugt aus einem Grossbild die Ableitungen fuer assets/img/.

Aufruf:  python3 werkzeuge/bild-ableiten.py <quelle.jpg> <name> [breiten]

Fuer jede Breite entstehen eine JPG- und eine WebP-Fassung. Breiter als
die Quelle wird nie skaliert: Hochrechnen erfindet keine Schaerfe,
kostet aber Bytes. Die Namen folgen <name>-<breite>.<endung>, weil
build.py die srcset-Eintraege genau so zusammensetzt.
"""
import sys, pathlib
from PIL import Image

STANDARD = [600, 750, 900, 1200, 1800]
ZIEL = pathlib.Path(__file__).resolve().parent.parent / "assets" / "img"

def main():
    if len(sys.argv) < 3:
        print(__doc__.strip())
        return 1
    quelle, name = pathlib.Path(sys.argv[1]), sys.argv[2]
    breiten = [int(b) for b in sys.argv[3].split(",")] if len(sys.argv) > 3 else STANDARD
    if not quelle.is_file():
        print(f"FEHLER: {quelle} gibt es nicht.")
        return 1
    ZIEL.mkdir(parents=True, exist_ok=True)

    im = Image.open(quelle).convert("RGB")
    qb, qh = im.size
    print(f"{quelle.name}  {qb}x{qh}  ->  {name}")
    for b in breiten:
        if b > qb:
            print(f"  {b:5}  uebersprungen, Quelle ist nur {qb} breit")
            continue
        h = round(qh * b / qb)
        k = im.resize((b, h), Image.LANCZOS)
        j = ZIEL / f"{name}-{b}.jpg"
        w = ZIEL / f"{name}-{b}.webp"
        k.save(j, "JPEG", quality=82, optimize=True, progressive=True)
        k.save(w, "WEBP", quality=80, method=6)
        print(f"  {b:5}x{h:<5} jpg {j.stat().st_size//1024:4} KB   "
              f"webp {w.stat().st_size//1024:4} KB")
    # Die Masszahlen, die in BILDER eingetragen werden muessen.
    gr = max(b for b in breiten if b <= qb)
    print(f"  BILDER-Eintrag:  \"{name}\": ({gr}, {round(qh*gr/qb)}, "
          f"{[b for b in breiten if b <= qb]}),")
    return 0

if __name__ == "__main__":
    sys.exit(main())
