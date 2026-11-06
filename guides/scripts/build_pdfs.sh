#!/usr/bin/env bash
# Build every guide (guides/NN-*.md) into pdf/NN-*.pdf with pandoc + xelatex.
# Figures are referenced from the markdown as figures/<name>.png and embedded in the PDF,
# so a reader (or NotebookLM, whose Video Overviews pull images from PDF sources) gets them.
# "In the app:" blockquotes become green boxes (scripts/app_links.lua, book/latex-header.tex).
# The book and the web edition: scripts/build_book.py.
# Usage: guides/scripts/build_pdfs.sh [guides/04-index-of-coincidence.md ...]
set -euo pipefail
cd "$(dirname "$0")/.."
out=../pdf
mkdir -p "$out"
files=("$@")
[ ${#files[@]} -eq 0 ] && files=([0-9][0-9]-*.md)
for md in "${files[@]}"; do
  md=$(basename "$md")
  pandoc "$md" -o "$out/${md%.md}.pdf" --pdf-engine=xelatex --resource-path=. \
    -V geometry:margin=2.2cm -V mainfont="Arial Unicode MS" -V mainfontoptions="BoldFont=Arial Bold,ItalicFont=Arial Italic,BoldItalicFont=Arial Bold Italic" -V monofont="Menlo" \
    -V fontsize=11pt -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
    --lua-filter=scripts/app_links.lua --include-in-header=book/latex-header.tex
  echo "built $out/${md%.md}.pdf"
done
