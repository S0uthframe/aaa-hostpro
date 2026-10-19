#!/usr/bin/env bash
# Wandelt ein animiertes GIF in MP4 und WebM um.
#
#   werkzeuge/gif-zu-video.sh eingabe.gif hero
#
# Warum ueberhaupt: GIF kennt keine Interframe-Kompression. Jedes Bild
# wird praktisch einzeln gespeichert, und eine fotorealistische
# Animation landet schnell im zweistelligen Megabyte-Bereich. Dasselbe
# Material als H.264 oder VP9 ist um den Faktor 10 bis 30 kleiner, bei
# gleichem Aussehen.
#
# Kein Ton: Die Quelle hat keinen, und ohne Tonspur darf ein Video in
# allen Browsern selbsttaetig starten.
set -euo pipefail

QUELLE="${1:?Aufruf: $0 <eingabe.gif> <name>}"
NAME="${2:?Aufruf: $0 <eingabe.gif> <name>}"
ZIEL="assets/video"
mkdir -p "$ZIEL"

# H.264 braucht gerade Kantenlaengen, GIFs haben oft ungerade.
SKALA="scale=trunc(iw/2)*2:trunc(ih/2)*2"

echo "Quelle: $(du -h "$QUELLE" | cut -f1)"

ffmpeg -v error -y -i "$QUELLE" \
  -vf "$SKALA" -movflags +faststart -pix_fmt yuv420p \
  -c:v libx264 -crf 26 -preset slow -an \
  "$ZIEL/$NAME.mp4"

ffmpeg -v error -y -i "$QUELLE" \
  -vf "$SKALA" \
  -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 -an \
  "$ZIEL/$NAME.webm"

echo "MP4:  $(du -h "$ZIEL/$NAME.mp4"  | cut -f1)"
echo "WebM: $(du -h "$ZIEL/$NAME.webm" | cut -f1)"
echo
echo "Fertig. Der Bau nimmt die Dateien beim naechsten Lauf von selbst auf."
