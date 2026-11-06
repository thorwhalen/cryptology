"""Build the book and the web edition from the guides.

    python guides/scripts/build_book.py            # both
    python guides/scripts/build_book.py --only pdf  # pdf/cryptanalysis-guides-for-young-codebreakers.pdf
    python guides/scripts/build_book.py --only web  # html/*.html and html/index.json

The book is the nine guides (guides/NN-*.md) as chapters, between front matter (a cover from
book/cover.jpg, a title page, a copyright page, the dedication in book/dedication.md, the contents, book/before-you-start.md) and back
matter (every guide's "Words to know", merged A to Z, then where to go next and about the book).

The web edition is one HTML fragment per guide (no <html> or <head>: the cryptology app wraps
it), with math as MathML, figures as relative `figures/...` paths, and "In the app" boxes as
<div class="in-app">; html/cover.jpg, the cover with its author; html/icon.png, the cover as a square favicon; plus html/index.json listing each guide's sections and words, which the
app reads for its contents and search. Both use scripts/app_links.lua.

Needs pandoc and, for the PDF, XeLaTeX with tcolorbox and pdfpages, and Pillow.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

GUIDES = Path(__file__).resolve().parents[1]
REPO = GUIDES.parent
BOOK = GUIDES / "book"
FILTER = GUIDES / "scripts" / "app_links.lua"
HEADER = BOOK / "latex-header.tex"

TITLE = "Cryptanalysis guides for young codebreakers"
SUBTITLE = "How to break classical ciphers with a pencil, squared paper and your own head"
EDITION = "First edition, November 2026"
AUTHOR = "Thor Whalen"
AUTHOR_NOTE = "(...but mostly his sleepless unpaid digital ghostwriters)"
APP_URL = "https://apps.thorwhalen.com/cryptology/"
REPO_URL = "https://github.com/thorwhalen/cryptology"
BOOK_PDF = REPO / "pdf" / "cryptanalysis-guides-for-young-codebreakers.pdf"
HTML_DIR = REPO / "html"

PANDOC_PDF = [
    "--pdf-engine=xelatex",
    f"--lua-filter={FILTER}",
    f"--include-in-header={HEADER}",
    "-V", "mainfont=Arial Unicode MS",
    "-V", "mainfontoptions=BoldFont=Arial Bold,ItalicFont=Arial Italic,BoldItalicFont=Arial Bold Italic",
    "-V", "monofont=Menlo",
    "-V", "fontsize=11pt",
    "-V", "colorlinks=true", "-V", "linkcolor=blue", "-V", "urlcolor=blue",
]


@dataclass
class Guide:
    """One guide's markdown, split into its metadata and its body."""

    path: Path
    title: str
    subtitle: str
    body: str
    words: list[tuple[str, str]] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.path.stem

    @property
    def number(self) -> int:
        return int(self.id[:2]) if self.id[:2].isdigit() else 0


def read_guide(path: Path) -> Guide:
    """Split the YAML block (title, subtitle) from the body, and collect its Words to know."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = dict(re.findall(r'^(\w+):\s*"(.*)"\s*$', match.group(1), re.M)) if match else {}
    body = text[match.end():] if match else text
    words_block = re.search(r"^## Words to know\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    words = re.findall(r"^- \*\*(.+?)\*\*(?: \((.+?)\))?:\s*(.+)$", words_block.group(1), re.M) if words_block else []
    return Guide(
        path=path,
        title=re.sub(r"^Guide \d+:\s*", "", meta.get("title", path.stem)),
        subtitle=meta.get("subtitle", ""),
        body=body,
        words=[(term + (f" ({extra})" if extra else ""), definition) for term, extra, definition in words],
    )


def guides() -> list[Guide]:
    return [read_guide(p) for p in sorted(GUIDES.glob("[0-9][0-9]-*.md"))]


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed:\n{result.stderr[-3000:]}")
    return result


# --- the book ------------------------------------------------------------------------------


def as_chapter(guide: Guide) -> str:
    """The guide's body under one `# Title` heading (some guides have it only in their YAML), then its subtitle."""
    body = guide.body.lstrip()
    if body.startswith("# "):
        body = body.partition("\n")[2]
    subtitle = f"*{guide.subtitle}*\n\n" if guide.subtitle else ""
    return f"# {guide.title}\n\n{subtitle}{body.lstrip()}\n"


def words_a_to_z(all_guides: list[Guide]) -> str:
    """Every guide's Words to know, merged by term, with the guides that define it."""
    merged: dict[str, tuple[str, str, list[int]]] = {}
    for g in all_guides:
        for term, definition in g.words:
            key = re.sub(r"[^a-z0-9]", "", term.split(" (")[0].lower())  # "Factor (or divisor)" is "Factor"
            if key in merged:
                merged[key][2].append(g.number)
            else:
                merged[key] = (term, definition, [g.number])
    lines = []
    for term, definition, nums in sorted(merged.values(), key=lambda t: re.sub(r"[^a-z0-9]", "", t[0].lower())):
        where = ", ".join(str(n) for n in nums)
        lines.append(f"- **{term}**: {definition} *(Guide{'s' if len(nums) > 1 else ''} {where})*")
    return "\n".join(lines)


def back_matter(all_guides: list[Guide]) -> str:
    return f"""
# Words to know, A to Z {{.unnumbered}}

Every word the guides teach, in one list. The numbers after each one say which guides explain it.

{words_a_to_z(all_guides)}

# Where to go next {{.unnumbered}}

- **The cryptology app**, [apps.thorwhalen.com/cryptology]({APP_URL}): the tools and exercises the green boxes point to, the family tree of ciphers, learning paths, and the competitions below with their calendars and rules.
- **The National Cipher Challenge** (UK), [cipherchallenge.org](https://www.cipherchallenge.org/): a story told in weekly ciphers each autumn, for school teams. Its archive of past challenges is the best practice there is.
- **Concours Alkindi** (France), [concours-alkindi.fr](https://concours-alkindi.fr/): a team competition for 13 to 16 year olds, in French.
- **Science Olympiad Codebusters** (US), [toebes.com/codebusters](https://toebes.com/codebusters/): timed tests on many cipher types, with practice tests.
- **Simon Singh, *The Code Book***: the history of codes and codebreaking, from Mary Queen of Scots to Enigma and beyond, told as a series of stories.
- **Practical Cryptography**, [practicalcryptography.com](http://practicalcryptography.com/ciphers/): short, clear pages on each cipher and how to break it, with the statistics of English.

# About this book {{.unnumbered}}

The nine guides were written to be read on their own, as PDFs, and are collected here as one book. Every worked example was checked by running code, and every figure was drawn by a short Python program that comes with the source.

The text and figures are licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/): you may copy, share and adapt them, for any purpose, as long as you say where they came from. The source, the figure programs and every guide as its own PDF are at [{REPO_URL.removeprefix('https://')}]({REPO_URL}). The cover is an illustration made with an AI image tool.

Typeset with pandoc and XeLaTeX. Figures drawn with matplotlib.

*{EDITION}.*
"""


def copyright_page() -> str:
    return rf"""
\thispagestyle{{empty}}
\vspace*{{\fill}}
{{\small
\noindent\textbf{{{TITLE}}}\\
{SUBTITLE}

\medskip
\noindent \copyright\ 2026 {AUTHOR}. {EDITION}.

\medskip
\noindent Text and figures licensed under Creative Commons Attribution 4.0 (CC BY 4.0): \url{{https://creativecommons.org/licenses/by/4.0/}}. You may copy, share and adapt them, for any purpose, with credit.

\medskip
\noindent Source, figure programs and every guide as its own PDF: \url{{{REPO_URL}}}

\noindent The companion app, with tools and exercises: \url{{{APP_URL}}}
\par}}
\clearpage
"""


def title_page(cover: Path) -> str:
    """Preamble: \\maketitle becomes the cover, then a title page; chapters are numbered as guides."""
    return rf"""\usepackage{{pdfpages}}
\renewcommand{{\maketitle}}{{%
  \includepdf{{{cover}}}%
  \begin{{titlepage}}\raggedright
  \vspace*{{4cm}}
  {{\fontsize{{34}}{{40}}\selectfont\bfseries {TITLE}\par}}
  \vspace{{1cm}}
  {{\Large {SUBTITLE}\par}}
  \vspace{{1.4cm}}
  {{\LARGE\bfseries {AUTHOR}\par}}
  \vspace{{0.25cm}}
  {{\large\itshape\color{{black!65}} {AUTHOR_NOTE}\par}}
  \vspace{{1.2cm}}
  {{\color{{appgreen}}\rule{{5cm}}{{4pt}}}}\par
  \vfill
  {{\large {EDITION}\par}}
  \vspace{{0.4cm}}
  {{\normalsize Companion app: \url{{{APP_URL}}}\par}}
  \end{{titlepage}}}}
\setcounter{{secnumdepth}}{{0}}
\renewcommand{{\chaptername}}{{Guide}}
"""


def unnumbered(markdown: str) -> str:
    """Mark each `{.unnumbered}` chapter for the running header, which LaTeX's \\chapter* leaves stale."""
    return re.sub(
        r"^# (.+?) \{\.unnumbered\}\n",
        lambda m: f"# {m.group(1)} {{.unnumbered}}\n\n\\markboth{{{m.group(1)}}}{{{m.group(1)}}}\n",
        markdown,
        flags=re.M,
    )


def dedication() -> list[str]:
    """The dedication's paragraphs (book/dedication.md), for its own page in the book and the app's book page."""
    path = BOOK / "dedication.md"
    return [p.strip() for p in path.read_text(encoding="utf-8").split("\n\n") if p.strip()] if path.exists() else []


def dedication_page() -> str:
    paragraphs = dedication()
    if not paragraphs:
        return ""
    body = "\n\n\\medskip\n".join(paragraphs)
    return rf"""
\thispagestyle{{empty}}
\vspace*{{0.28\textheight}}
\begin{{center}}
\begin{{minipage}}{{0.72\textwidth}}\centering\itshape\large
{body}
\end{{minipage}}
\end{{center}}
\clearpage
"""


# Where the author goes on book/cover.jpg: the empty band above the title, aligned with its left edge.
COVER_LEFT, COVER_NAME_TOP, COVER_NOTE_GAP = 66, 118, 22
COVER_NAME_PX, COVER_NOTE_PX = 84, 38
COVER_FONTS = ("/System/Library/Fonts/HelveticaNeue.ttc", "/Library/Fonts/Arial Unicode.ttf")


def cover_with_author():
    """book/cover.jpg with the author's name, and the note under it, in the band above the title."""
    from PIL import Image, ImageDraw, ImageFont

    def font(px: int, index: int):
        for path in COVER_FONTS:
            try:
                return ImageFont.truetype(path, px, index=index if path.endswith(".ttc") else 0)
            except OSError:
                continue
        return ImageFont.load_default(px)

    cover = Image.open(BOOK / "cover.jpg").convert("RGB")
    draw = ImageDraw.Draw(cover)
    name = font(COVER_NAME_PX, 1)  # Helvetica Neue Bold
    note = font(COVER_NOTE_PX, 2)  # Helvetica Neue Italic
    draw.text((COVER_LEFT, COVER_NAME_TOP), AUTHOR, font=name, fill=(20, 20, 20))
    name_bottom = draw.textbbox((COVER_LEFT, COVER_NAME_TOP), AUTHOR, font=name)[3]
    draw.text((COVER_LEFT, name_bottom + COVER_NOTE_GAP), AUTHOR_NOTE, font=note, fill=(80, 80, 80))
    return cover


def cover_pdf(work: Path) -> Path:
    """The cover on an A4 page: fit to the height, the sides padded in the cover's own paper color."""
    from PIL import Image

    a4_w, a4_h = 2480, 3508  # 300 dpi
    cover = cover_with_author()
    scale = a4_h / cover.height
    cover = cover.resize((round(cover.width * scale), a4_h), Image.LANCZOS)
    paper = cover.getpixel((4, a4_h // 2))
    page = Image.new("RGB", (a4_w, a4_h), paper)
    page.paste(cover, ((a4_w - cover.width) // 2, 0))
    out = work / "cover.pdf"
    page.save(out, resolution=300.0, quality=90)
    return out


def build_pdf(all_guides: list[Guide]) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cover = cover_pdf(work)
        (work / "copyright.tex").write_text(copyright_page() + dedication_page(), encoding="utf-8")
        (work / "titlepage.tex").write_text(title_page(cover), encoding="utf-8")
        front = read_guide(BOOK / "before-you-start.md")
        parts = [as_chapter(front).replace("# Before you start", "# Before you start {.unnumbered}", 1)]
        parts += [as_chapter(g) for g in all_guides]
        parts.append("\\backmatter\n" + back_matter(all_guides))
        source = work / "book.md"
        source.write_text(unnumbered("\n\n".join(parts)), encoding="utf-8")
        BOOK_PDF.parent.mkdir(exist_ok=True)
        _run([
            "pandoc", str(source), "-o", str(BOOK_PDF), *PANDOC_PDF,
            f"--resource-path={GUIDES}",
            f"--include-in-header={work / 'titlepage.tex'}",
            f"--include-before-body={work / 'copyright.tex'}",
            "--top-level-division=chapter", "--toc", "-V", "toc-depth=0",
            "-V", "documentclass=book", "-V", "classoption=oneside,openany",
            "-V", "geometry:margin=2.2cm",
            "-M", f"title={TITLE}", "-M", f"subtitle={SUBTITLE}", "-M", f"date={EDITION}", "-M", f"author={AUTHOR}",
            "-V", "toc-title=Contents",
        ])
    return BOOK_PDF


# --- the web edition -----------------------------------------------------------------------


def sections_of(html: str) -> list[dict]:
    """Every level-2 heading with its id, from pandoc's section-divs output."""
    return [
        {"id": sid, "heading": re.sub(r"<[^>]+>", "", text).strip()}
        for sid, text in re.findall(r'<section id="([^"]+)" class="level2">\s*<h2>(.*?)</h2>', html, re.S)
    ]


def sized_images(html: str) -> str:
    """Give every figure its width and height, so a page that loads them lazily never jumps."""
    from PIL import Image

    def size(match: re.Match) -> str:
        tag, src = match.group(0), match.group(1)
        path = GUIDES / src
        if " width=" in tag or not path.exists():
            return tag
        w, h = Image.open(path).size
        return tag.replace("<img ", f'<img width="{w}" height="{h}" ', 1)

    return re.sub(r'<img [^>]*src="([^"]+)"[^>]*>', size, html)


def cover_icon(size: int = 256) -> Path:
    """The cover as a square icon (a browser tab's favicon): the whole cover, centered on transparent."""
    from PIL import Image

    cover = Image.open(BOOK / "cover.jpg").convert("RGBA")
    cover.thumbnail((size, size), Image.LANCZOS)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(cover, ((size - cover.width) // 2, (size - cover.height) // 2))
    out = HTML_DIR / "icon.png"
    icon.save(out, optimize=True)
    return out


def build_web(all_guides: list[Guide]) -> Path:
    HTML_DIR.mkdir(exist_ok=True)
    cover_icon()
    cover_with_author().save(HTML_DIR / "cover.jpg", quality=88, optimize=True, progressive=True)
    entries = []
    front = read_guide(BOOK / "before-you-start.md")
    front.path = BOOK / "00-before-you-start.md"
    for g in [front, *all_guides]:
        html = _run(
            ["pandoc", "-f", "markdown", "-t", "html5", "--mathml", "--section-divs", f"--lua-filter={FILTER}"],
            input=as_chapter(g),
        ).stdout
        html = sized_images(html)
        (HTML_DIR / f"{g.id}.html").write_text(html, encoding="utf-8")
        entries.append({
            "id": g.id, "number": g.number, "title": g.title, "subtitle": g.subtitle,
            "pdf": f"pdf/{g.id}.pdf" if g.number else None,
            "sections": sections_of(html),
            "words": [{"term": t, "definition": d} for t, d in g.words],
        })
    index = {"title": TITLE, "subtitle": SUBTITLE, "edition": EDITION, "book": f"pdf/{BOOK_PDF.name}", "author": AUTHOR, "author_note": AUTHOR_NOTE, "cover": "html/cover.jpg", "icon": "html/icon.png", "dedication": dedication(), "guides": entries}
    (HTML_DIR / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return HTML_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["pdf", "web"])
    args = parser.parse_args()
    all_guides = guides()
    if args.only in (None, "web"):
        print("built", build_web(all_guides))
    if args.only in (None, "pdf"):
        print("built", build_pdf(all_guides))


if __name__ == "__main__":
    main()
