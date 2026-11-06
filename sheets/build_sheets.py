"""Build the cryptanalysis spreadsheets that go with the book of guides.

Writes one workbook per task, ``sheets/NN-<slug>.xlsx``, and the manifest
``sheets/sheets.json``. Each workbook has a front tab (a "How to use" block,
yellow input cells, the results) and a ``Workings`` tab that holds the
behind-the-scenes columns. Re-run from anywhere::

    python sheets/build_sheets.py

Design rules:

- **Portable formulas only** (LEN, SUBSTITUTE, MID, CODE, CHAR, MOD, INDEX,
  MATCH, COUNTIF, SUMPRODUCT, ...), so the same file works in Google Sheets,
  Excel and LibreOffice. No TEXTJOIN, no array formulas, no scripts.
- **Long texts are shown as lines** of ``LINE_WIDTH`` characters (``MID`` on one
  string), never as one giant cell, because Excel only shows the first 1024
  characters of a cell.
- **Sample texts are made up here** and encrypted by the small reference
  ciphers below, so every sample is original and its expected answer is known.
- **Small files**: the ``Workings`` columns repeat one formula down many rows;
  ``_compact`` removes the optional cell addresses so the zip compresses those
  rows to almost nothing (the files are uploaded to Google Drive as base64).

The manifest keeps the Google ids already recorded in ``sheets.json``: rebuild
freely, the links survive.
"""

from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from xml.sax.saxutils import unescape
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.formula.translate import Translator
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "sheets.json"
REPO_DIR = "sheets"

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
N_LETTERS = len(ALPHABET)
# Standard published English letter frequencies (percent), A to Z: the same table as Guide 02.
ENGLISH_PCT = [
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4,
    6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074,
]
ENGLISH_ORDER = "".join(sorted(ALPHABET, key=lambda c: -ENGLISH_PCT[ALPHABET.index(c)]))
IOC_ENGLISH = 0.066  # Guide 04 (counts of English give 0.065 to 0.067)
IOC_RANDOM = 1 / 26  # about 0.038
IOC_LOOKS_ENGLISH = 0.055  # at or above: one alphabet
IOC_LOOKS_RANDOM = 0.047  # at or below: several alphabets
SLICE_IOC_GOOD = 0.058  # an average slice IoC at or above this looks like English
CHI_LOOKS_ENGLISH = 150  # chi-squared below this: the letters themselves are English's
CHI_DECIMALS = 6  # chi-squared is rounded so the lowest score can be found by exact match
PERCENT = 100

# Size limits (rows of workings). Long enough for a competition text.
MAX_LETTERS = 1800
LINE_WIDTH = 60  # characters per output line (even, so Hill pairs never straddle two lines)
MAX_LINES = 40  # output lines shown: 40 x 60 = 2400 characters
PREVIEW_CHARS = 64  # characters of each Caesar shift shown
TEXT_ROWS = 6  # yellow rows a pasted text may spill into
MAX_KEY_LENGTH = 20  # Vigenere scan: key lengths 1 to 20
SLICE_PREVIEW = 40  # letters of each slice shown
SCAN_LETTERS = 1000  # the key-length scan reads this many letters (plenty for the IoC)
PAST_END = 9999  # letter number given to positions past the end of the text
SUMMARY_TAB = "Summary"
SUMMARY_LINES = 2  # output lines repeated on the Summary tab
MAX_FORMULA = 8000  # Excel and LibreOffice refuse formulas longer than 8192 characters
MAX_FACTOR = 20  # Kasiski factor table: 2 to 20
MAX_GAPS = 15  # typed gaps
MAX_FOUND = 20  # repeats listed automatically
REPEAT_MIN, REPEAT_MAX, REPEAT_DEFAULT = 3, 5, 3
NEAR_TOP = 0.9  # a factor this close to the top count is still a candidate key length
BEST_GUESS_YOURS = "Best guess for the key length (your gaps)"
BEST_GUESS_FOUND = "Best guess for the key length (found gaps)"
MAX_WIDTH = 12  # columnar: widths up to 12
MAX_GRID_ROWS = 100  # columnar: 12 x 100 = 1200 letters
MAX_PAIRS = 600  # digraph sheet: pairs counted (1200 letters)
KASISKI_LETTERS = 600  # repeats sheet: letters searched for repeats
TOP_PAIRS = 15
TOP_LETTERS = 6
PLACEHOLDER = "_"  # an unsolved letter in the substitution helper
PAD_LETTER = "X"  # Hill: added to an odd-length text
BAR = "█"  # a full block, for text bar charts
BAR_PER_PERCENT = 2  # characters of bar per percent
BAR_PER_IOC = 400  # characters of bar per unit of IoC
BAR_FULL = 16  # characters in the longest gap-count bar

# Characters removed from a text before counting letters (everything else is upper-cased).
NOT_LETTERS = (
    [" ", "\n", "\r", "\t", ".", ",", ";", ":", "!", "?", "'", '"', "-", "(", ")", "/", "&", "_", "*", "[", "]"]
    + list("0123456789")
    + ["’", "‘", "“", "”", "—", "–", "…"]
)

# ---------------------------------------------------------------- look and feel
FONT = "Arial"
MONO = "Courier New"
SIZE_TITLE, SIZE_SUB, SIZE_BODY, SIZE_SMALL, SIZE_MONO = 24, 15, 14, 11, 13
INK, TITLE_INK, MUTED = "1F2933", "0D47A1", "52606D"
FILL_INPUT, EDGE_INPUT = "FFF176", "F9A825"
FILL_HOWTO, FILL_HEAD, FILL_BEST, FILL_WARN, FILL_OUT = "E3F2FD", "ECEFF1", "C8E6C9", "FFCDD2", "FAFAFA"
ROW_TITLE, ROW_TEXT_FIRST, ROW_TEXT_REST, ROW_LINE = 36, 110, 22, 20
WIDTH_MARGIN, WIDTH_LABEL = 2, 30
CHARS_PER_LINE = 115  # how many characters of 12 pt text fit across a full-width block
LINE_HEIGHT = 19  # points per wrapped line of 12 pt text

_side = Side(style="thin", color="B0BEC5")
_thick = Side(style="medium", color=EDGE_INPUT)
BOX = Border(left=_side, right=_side, top=_side, bottom=_side)
INPUT_BOX = Border(left=_thick, right=_thick, top=_thick, bottom=_thick)


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color, end_color=color)


def wrapped_height(text: str) -> float:
    """A row height that fits ``text`` wrapped across a full-width block."""
    lines = -(-len(text) // CHARS_PER_LINE)
    return LINE_HEIGHT * max(1, lines) + 8


def _font(size: int = SIZE_BODY, *, bold: bool = False, color: str = INK, mono: bool = False) -> Font:
    return Font(name=MONO if mono else FONT, size=size, bold=bold, color=color)


def put(ws, ref: str, value, *, size: int = SIZE_BODY, bold: bool = False, color: str = INK,
        fill: str | None = None, mono: bool = False, fmt: str | None = None, wrap: bool = False,
        align: str | None = None, box: bool = False):
    """Write a value or formula into one cell, styled."""
    cell = ws[ref]
    cell.value = None if value == "" else value
    cell.font = _font(size, bold=bold, color=color, mono=mono)
    if fill:
        cell.fill = _fill(fill)
    if fmt:
        cell.number_format = fmt
    cell.alignment = Alignment(wrap_text=wrap, vertical="top" if wrap else "center", horizontal=align)
    if box:
        cell.border = BOX
    return cell


def as_input(cell, *, align: str = "center") -> None:
    """Mark a cell as yellow input."""
    cell.fill = _fill(FILL_INPUT)
    cell.border = INPUT_BOX
    cell.font = _font(SIZE_BODY, bold=True)
    cell.alignment = Alignment(horizontal=align, vertical="center")


def merge_put(ws, row: int, first: str, last: str, value, **style) -> None:
    """Write into ``first``, merged across to ``last`` on the same row."""
    put(ws, f"{first}{row}", value, **style)
    if first != last:
        ws.merge_cells(f"{first}{row}:{last}{row}")


def col(index: int) -> str:
    return get_column_letter(index)


def cols(first: str, n: int) -> list[str]:
    start = column_index_from_string(first)
    return [col(start + i) for i in range(n)]


def lit(text: str) -> str:
    """A formula string literal for ``text``."""
    if text in ("\n", "\r", "\t"):
        return f"CHAR({ord(text)})"
    return '"' + text.replace('"', '""') + '"'


def nested_substitute(expr: str, pairs) -> str:
    """``SUBSTITUTE(SUBSTITUTE(expr, a1, b1), a2, b2) ...`` for (old literal, new formula) pairs."""
    for old, new in pairs:
        expr = f"SUBSTITUTE({expr},{lit(old)},{new})"
    return expr


def argmin(values: str, labels: str) -> str:
    """The label beside the smallest value (the first one if several tie).

    Written with SUMPRODUCT rather than MATCH(MIN(...)): LibreOffice's lookup cache can miss an
    exact match on a value computed in the same recalculation.
    """
    hit = f"({values}=MIN({values}))"
    return (f"IF(COUNTIF({values},MIN({values}))>1,INDEX({labels},MATCH(MIN({values}),{values},0)),"
            f"SUMPRODUCT({hit}*{labels}))")


def amp(parts) -> str:
    """Join formula parts with ``&``."""
    return "&".join(parts)


def q(sheet: str) -> str:
    return f"'{sheet}'!"


# ---------------------------------------------------------------- page building blocks
@dataclass
class Page:
    """A front tab being laid out top to bottom, and its Workings tab."""

    wb: Workbook
    ws: object
    work: object
    last: str  # last column used by full-width blocks
    row: int = 1
    results: list = field(default_factory=list)  # (label, front-tab ref) pairs for the Summary tab

    @property
    def name(self) -> str:
        return self.ws.title

    def skip(self, n: int = 1) -> None:
        self.row += n

    def heading(self, text: str) -> None:
        self.skip()
        merge_put(self.ws, self.row, "B", self.last, text, size=SIZE_SUB + 2, bold=True, color=TITLE_INK)
        self.skip()

    def note(self, text: str, *, color: str = MUTED, size: int = SIZE_SMALL + 1) -> None:
        merge_put(self.ws, self.row, "B", self.last, text, size=size, color=color, wrap=True)
        self.ws.row_dimensions[self.row].height = wrapped_height(text)
        self.skip()

    def stat(self, label: str, formula, *, fmt: str | None = None, value_last: str | None = None,
             bold: bool = True) -> str:
        """A label in B and a computed value in C (merged to ``value_last``). Returns the value ref."""
        put(self.ws, f"B{self.row}", label, bold=False)
        merge_put(self.ws, self.row, "C", value_last or self.last, formula, bold=bold, fmt=fmt, align="left")
        ref = f"$C${self.row}"
        self.results.append((label, ref))
        self.skip()
        return ref


def new_page(title: str, tab: str, promise: str, guides: str, how_to: list[str], *,
             last: str = "P", widths: dict[str, float] | None = None, default_width: float = 9) -> Page:
    """A workbook with its front tab titled and its How-to block written."""
    wb = Workbook()
    ws = wb.active
    ws.title = tab
    ws.sheet_view.showGridLines = False
    work = wb.create_sheet("Workings")
    put(work, "A1", "Message")
    put(work, "A2", "Letters")
    put(work, "A3", "Letter count")
    work.column_dimensions["A"].width = 16
    work.column_dimensions["B"].width = 40
    ws.column_dimensions["A"].width = WIDTH_MARGIN
    ws.column_dimensions["B"].width = WIDTH_LABEL
    for c in range(column_index_from_string("C"), column_index_from_string(last) + 1):
        ws.column_dimensions[col(c)].width = default_width
    for c, w in (widths or {}).items():
        ws.column_dimensions[c].width = w
    page = Page(wb, ws, work, last)
    merge_put(ws, 1, "B", last, title, size=SIZE_TITLE, bold=True, color=TITLE_INK)
    ws.row_dimensions[1].height = ROW_TITLE + 6
    merge_put(ws, 2, "B", last, promise, size=SIZE_SUB, color=INK)
    ws.row_dimensions[2].height = ROW_TITLE
    merge_put(ws, 3, "B", last, f"Goes with {guides} in the book Cryptanalysis guides for young codebreakers.",
              size=SIZE_SMALL, color=MUTED)
    page.row = 5
    merge_put(ws, page.row, "B", last, "How to use", size=SIZE_BODY, bold=True, fill=FILL_HOWTO)
    page.skip()
    lines = how_to + [
        "Yellow boxes are for you to type in. Everything else works itself out.",
        "Cannot type? You are looking at the shared original: choose File > Make a copy, and use your copy.",
    ]
    for line in lines:
        merge_put(ws, page.row, "B", last, "• " + line, size=SIZE_SMALL + 1, fill=FILL_HOWTO, wrap=True)
        ws.row_dimensions[page.row].height = wrapped_height(line)
        page.skip()
    return page


def finish(page: Page) -> Workbook:
    """Add the Summary tab: every headline result of the front tab on one short page."""
    ws = page.wb.create_sheet(SUMMARY_TAB, 1)
    ws.column_dimensions["A"].width = WIDTH_LABEL + 16
    ws.column_dimensions["B"].width = LINE_WIDTH + 10
    put(ws, "A1", "Result", bold=True, fill=FILL_HEAD)
    put(ws, "B1", f"Value (computed on the {page.name} tab)", bold=True, fill=FILL_HEAD)
    for i, (label, ref) in enumerate(page.results, start=2):
        put(ws, f"A{i}", label, size=SIZE_SMALL + 1)
        put(ws, f"B{i}", f"={q(page.name)}{ref}", size=SIZE_SMALL + 1, mono=True, align="left")
    return page.wb


def define(wb: Workbook, name: str, ref: str) -> None:
    wb.defined_names[name] = DefinedName(name, attr_text=ref)


def text_input(page: Page, sample: str, *, label: str = "Your text (paste it into the first yellow row)") -> None:
    """The yellow text box (several rows, all read) and the Message, Letters and LetterCount names."""
    ws = page.ws
    page.skip()
    merge_put(ws, page.row, "B", page.last, label, bold=True)
    page.skip()
    refs = []
    for i in range(TEXT_ROWS):
        r = page.row
        merge_put(ws, r, "B", page.last, sample if i == 0 else None, size=SIZE_SMALL + 1, mono=True, wrap=True)
        for c in range(column_index_from_string("B"), column_index_from_string(page.last) + 1):
            cell = ws[f"{col(c)}{r}"]
            cell.fill = _fill(FILL_INPUT)
            cell.border = INPUT_BOX
        ws.row_dimensions[r].height = ROW_TEXT_FIRST if i == 0 else ROW_TEXT_REST
        refs.append(f"{q(page.name)}B{r}")
        page.skip()
    work = page.work
    put(work, "B1", "=TRIM(" + amp(f'{r}&" "' if k < len(refs) - 1 else r for k, r in enumerate(refs)) + ")")
    put(work, "B2", "=" + nested_substitute("UPPER(Message)", [(ch, '""') for ch in NOT_LETTERS]))
    put(work, "B3", "=LEN(Letters)")
    define(page.wb, "Message", "Workings!$B$1")
    define(page.wb, "Letters", "Workings!$B$2")
    define(page.wb, "LetterCount", "Workings!$B$3")
    page.stat("Letters found (A to Z)", "=LetterCount", value_last="E")


def output_lines(page: Page, source: str, *, title: str, n_lines: int = MAX_LINES) -> None:
    """Show a long string (a Workings cell) as lines of LINE_WIDTH characters."""
    page.heading(title)
    first = page.row
    page.results += [(f"{title} (line {i + 1})", f"$B${first + i}") for i in range(SUMMARY_LINES)]
    for _ in range(n_lines):
        merge_put(page.ws, page.row, "B", page.last, f"=MID({source},(ROW()-{first})*{LINE_WIDTH}+1,{LINE_WIDTH})",
                  mono=True, size=SIZE_MONO, fill=FILL_OUT)
        page.ws.row_dimensions[page.row].height = ROW_LINE
        page.skip()


def column_lines(page: Page, column: str, first_row: int, *, title: str, n_lines: int) -> None:
    """Show a Workings column of single characters as lines of LINE_WIDTH characters."""
    rng = f"Workings!${column}${first_row}:${column}${first_row + n_lines * LINE_WIDTH - 1}"
    page.heading(title)
    first = page.row
    for _ in range(n_lines):
        parts = [f"INDEX({rng},(ROW()-{first})*{LINE_WIDTH}+{j + 1})" for j in range(LINE_WIDTH)]
        merge_put(page.ws, page.row, "B", page.last, "=" + amp(parts), mono=True, size=SIZE_MONO, fill=FILL_OUT)
        page.ws.row_dimensions[page.row].height = ROW_LINE
        page.skip()


def computed_lines(page: Page, term: Callable[[str, int], str], *, title: str, n_lines: int,
                   blank_if: str = "") -> None:
    """Lines whose characters are computed from their position: ``term(p, k)`` is the formula for character p,
    the k-th (from 1) of its line. Lines start at multiples of LINE_WIDTH, so k and p have the same parity.

    Every line is the same formula (a shared formula), reading its starting position from a cell
    just right of the block, so a long output costs one formula, not one cell per letter.
    """
    page.heading(title)
    first = page.row
    page.results += [(f"{title} (line {i + 1})", f"$B${first + i}") for i in range(SUMMARY_LINES)]
    offset_col = col(column_index_from_string(page.last) + 1)
    page.ws.column_dimensions[offset_col].width = WIDTH_MARGIN
    for _ in range(n_lines):
        r = page.row
        put(page.ws, f"{offset_col}{r}", f"=(ROW()-{first})*{LINE_WIDTH}", color="FFFFFF", size=SIZE_SMALL - 4)
        line = amp(term(f"(${offset_col}{r}+{k})", k) for k in range(1, LINE_WIDTH + 1))
        formula = f'=IF({blank_if},"",{line})' if blank_if else f"={line}"
        assert len(formula) <= MAX_FORMULA, f"{title}: formula of {len(formula)} characters"
        merge_put(page.ws, r, "B", page.last, formula, mono=True, size=SIZE_MONO, fill=FILL_OUT)
        page.ws.row_dimensions[r].height = ROW_LINE
        page.skip()


def letter_counts_row(work, row: int, first: str = "B") -> str:
    """Write A-Z (row) and their counts in Letters (row + 1). Returns the counts range."""
    cs = cols(first, N_LETTERS)
    for c, letter in zip(cs, ALPHABET):
        put(work, f"{c}{row}", letter)
        put(work, f"{c}{row + 1}", f'=LEN(Letters)-LEN(SUBSTITUTE(Letters,{c}${row},""))')
    put(work, f"A{row}", "Letter")
    put(work, f"A{row + 1}", "Count")
    return f"Workings!${cs[0]}${row + 1}:${cs[-1]}${row + 1}"


def english_row(work, row: int, first: str = "B") -> str:
    """Write English frequencies as fractions. Returns the range."""
    cs = cols(first, N_LETTERS)
    put(work, f"A{row}", "English")
    for c, p in zip(cs, ENGLISH_PCT):
        put(work, f"{c}{row}", p / PERCENT)
    return f"Workings!${cs[0]}${row}:${cs[-1]}${row}"


def header_row(ws, row: int, labels: dict[str, str], *, size: int = SIZE_BODY) -> None:
    for c, text in labels.items():
        put(ws, f"{c}{row}", text, bold=True, fill=FILL_HEAD, wrap=True, align="center", size=size, box=True)


def bar_chart(ws, *, title: str, cats, data, anchor: str, y_title: str, width: float = 22, height: float = 10):
    chart = BarChart()
    chart.type = "col"
    chart.title = title
    chart.y_axis.title = y_title
    chart.width, chart.height = width, height
    for d in data:
        chart.add_data(d, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, anchor)


# ---------------------------------------------------------------- reference ciphers (for the samples)
def only_letters(text: str) -> str:
    return "".join(c for c in text.upper() if c in ALPHABET)


def caesar(text: str, shift: int) -> str:
    return "".join(ALPHABET[(ALPHABET.index(c) + shift) % 26] if c in ALPHABET else c for c in text.upper())


def affine(text: str, a: int, b: int) -> str:
    return "".join(ALPHABET[(a * ALPHABET.index(c) + b) % 26] if c in ALPHABET else c for c in text.upper())


def keyword_alphabet(keyword: str) -> str:
    seen = []
    for c in keyword.upper() + ALPHABET:
        if c not in seen:
            seen.append(c)
    return "".join(seen)


def substitute(text: str, cipher_alphabet: str) -> str:
    return "".join(cipher_alphabet[ALPHABET.index(c)] if c in ALPHABET else c for c in text.upper())


def vigenere(text: str, key: str) -> str:
    letters = only_letters(text)
    return "".join(ALPHABET[(ALPHABET.index(c) + ALPHABET.index(key[i % len(key)])) % 26]
                   for i, c in enumerate(letters))


def column_order(keyword: str) -> list[int]:
    """The number on top of each column: alphabetical order of the keyword's letters."""
    ranked = sorted(range(len(keyword)), key=lambda i: (keyword[i], i))
    order = [0] * len(keyword)
    for rank, i in enumerate(ranked, start=1):
        order[i] = rank
    return order


def columnar(text: str, order: list[int]) -> str:
    letters, width = only_letters(text), len(order)
    return "".join(letters[i::width] for i in sorted(range(width), key=lambda i: order[i]))


def playfair(text: str, keyword: str) -> str:
    square = [c for c in keyword_alphabet(keyword.replace("J", "I")) if c != "J"]
    where = {c: divmod(i, 5) for i, c in enumerate(square)}
    letters = only_letters(text).replace("J", "I")
    pairs, i = [], 0
    while i < len(letters):
        a = letters[i]
        b = letters[i + 1] if i + 1 < len(letters) else PAD_LETTER
        if a == b:
            b, i = PAD_LETTER, i + 1
        else:
            i += 2
        pairs.append((a, b))
    out = []
    for a, b in pairs:
        (ra, ca), (rb, cb) = where[a], where[b]
        if ra == rb:
            out += [square[ra * 5 + (ca + 1) % 5], square[rb * 5 + (cb + 1) % 5]]
        elif ca == cb:
            out += [square[((ra + 1) % 5) * 5 + ca], square[((rb + 1) % 5) * 5 + cb]]
        else:
            out += [square[ra * 5 + cb], square[rb * 5 + ca]]
    return "".join(out)


def hill(text: str, key: tuple[int, int, int, int]) -> str:
    a, b, c, d = key
    letters = only_letters(text)
    if len(letters) % 2:
        letters += PAD_LETTER
    nums = [ALPHABET.index(ch) for ch in letters]
    out = []
    for x1, x2 in zip(nums[::2], nums[1::2]):
        out += [ALPHABET[(a * x1 + b * x2) % 26], ALPHABET[(c * x1 + d * x2) % 26]]
    return "".join(out)


def grouped(text: str, size: int = 5) -> str:
    return " ".join(text[i:i + size] for i in range(0, len(text), size))


# ---------------------------------------------------------------- original sample plaintexts
LIGHTHOUSE = (
    "The old lighthouse keeper kept a notebook of every ship that passed. On calm nights he wrote about "
    "the stars, and on stormy nights he wrote about the waves. One winter a ship sailed past with no "
    "lights at all, and the keeper wrote its name in a code that only his granddaughter could read. She "
    "found the notebook years later, hidden behind a loose brick in the lamp room, and spent the whole "
    "summer working out what he had seen."
)
BAKER = (
    "Every morning the baker on our street sings while the bread rises. The neighbors say his songs are "
    "the reason the loaves taste so good. Nobody has ever heard the words clearly, because he sings them "
    "backward, and he refuses to explain why."
)
MUSEUM = (
    "The museum guard noticed that the painting of the fox had moved two inches to the left overnight. "
    "Nothing else was out of place, and the alarm never rang. The next night he stayed awake and "
    "watched, and at midnight the fox in the painting blinked."
)
CLUB = (
    "Our club meets in the library every Thursday after school. We trade puzzles, invent new codes and "
    "try to break each other's messages before the bell rings. Last week a new member brought a message "
    "that nobody could crack, not even the teacher. It turned out to be written backward in a cipher "
    "with two keys, and she had made it up on the bus that morning."
)
PROBE = (
    "Far out in the dark between the planets, a small probe drifts with its engines switched off. It was "
    "launched before most of the people who now listen for it were born, and it is still sending a faint "
    "signal home every day. The signal is weaker than the light of a candle seen from the other side of "
    "the world, yet giant dishes in the desert catch it and turn it back into numbers. Those numbers tell "
    "the engineers how warm the probe is, how much power is left, and what the instruments have "
    "measured. One day the power will run out and the signal will stop, but the probe will keep falling "
    "outward for thousands of years, carrying a record of music and greetings from a planet it will "
    "never see again."
)
TREASURE = (
    "The treasure map was drawn on the back of an old shopping list. It showed the garden, the shed and "
    "the apple tree, and a dotted line from the tree to the pond. Under the pond, it said, the treasure "
    "waits for the patient. So we waited. We waited for the pond to dry in the summer heat, and when the "
    "water was gone we dug in the mud for three whole days. At the bottom of the hole we found a tin box, "
    "and inside the box we found another map, drawn on the back of another shopping list, showing "
    "another garden in another town."
)
GATE = "Meet me at the north gate of the castle when the clock strikes nine and bring the lantern"
FOG = (
    "The fog rolled in from the sea just after sunset, and the keepers lit the great lamp early. Far out "
    "on the water a small fishing boat had lost its way, and the crew followed the beam all the way home "
    "to the harbor wall."
)
APPLES = "Send more apples to the castle kitchen before the feast on Friday"

LIGHTHOUSE_KEY = keyword_alphabet("MOUNTAIN")
CAESAR_SHIFT = 7
AFFINE_KEY = (7, 10)
CLUB_KEY = keyword_alphabet("LANTERN")
CLUB_SOLVED = "etha"  # plain letters filled in on the sample key table
PROBE_KEY = "COMET"
TREASURE_KEY = "WILLOW"
GATE_KEYWORD = "GARDEN"
FOG_KEYWORD = "KEYSTONE"
HILL_KEY = (9, 4, 5, 7)


# ---------------------------------------------------------------- 1. letter counts and IoC
def build_counts(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Counts", "Count every letter, compare with English, and measure the index of coincidence.",
        spec.guide_names,
        ["Paste a ciphertext. The table counts each letter A to Z and puts English's percentages beside it.",
         "The index of coincidence (IoC) says how often two letters picked at random match: about 0.066 for "
         "English and any one-alphabet cipher, about 0.038 for random letters."],
    )
    ws, work = page.ws, page.work
    text_input(page, substitute(LIGHTHOUSE, LIGHTHOUSE_KEY))
    counts = letter_counts_row(work, 5)
    english_row(work, 7)
    # tie-broken scores for "commonest first"
    put(work, "A8", "Score (count, ties to the earlier letter)")
    for i, c in enumerate(cols("B", N_LETTERS)):
        put(work, f"{c}8", f"={c}6+{(N_LETTERS - i) / PERCENT}")
    scores = f"Workings!$B$8:${col(1 + N_LETTERS)}$8"
    alpha = f"Workings!$B$5:${col(1 + N_LETTERS)}$5"

    page.heading("What the counts say")
    page.stat("Different letters used", f'=COUNTIF({counts},">0")', value_last="E")
    missing = amp(f'IF(INDEX({counts},{i + 1})=0,"{c} ","")' for i, c in enumerate(ALPHABET))
    page.stat("Letters never used", f"=TRIM({missing})")
    page.stat("Length is", '=IF(LetterCount=0,"",IF(MOD(LetterCount,2)=0,"even","odd"))', value_last="E")
    ioc = page.stat("Index of coincidence (IoC)",
                    f'=IF(LetterCount<2,"",SUMPRODUCT({counts},{counts}-1)/(LetterCount*(LetterCount-1)))',
                    fmt="0.000", value_last="E")
    page.stat("English", IOC_ENGLISH, fmt="0.000", value_last="E", bold=False)
    page.stat("Random letters (1 in 26)", IOC_RANDOM, fmt="0.000", value_last="E", bold=False)
    chi = page.stat(
        "Chi-squared against English", f'=IF(LetterCount=0,"",SUMPRODUCT(({counts}-LetterCount*'
        f'{english_range("Workings", 7)})^2/(LetterCount*{english_range("Workings", 7)})))',
        fmt="0.0", value_last="E")
    page.stat(
        "What this suggests",
        f'=IF({ioc}="","",IF({ioc}>={IOC_LOOKS_ENGLISH},IF({chi}<{CHI_LOOKS_ENGLISH},'
        '"One alphabet, and the letters are English\'s own: probably a transposition (scrambled, not disguised).",'
        '"One alphabet, disguised: a Caesar, affine or substitution cipher. Try frequency analysis."),'
        f'IF({ioc}<={IOC_LOOKS_RANDOM},"Near random: several alphabets, such as a Vigenere. Find the key length next.",'
        '"In between: a short text, a Playfair, or a Vigenere with a short key. Check the pair tells too.")))',
        bold=True)
    ws.row_dimensions[page.row - 1].height = ROW_LINE * 2
    ws[f"C{page.row - 1}"].alignment = Alignment(wrap_text=True, vertical="top")

    page.heading("Commonest letters")
    put(ws, f"B{page.row}", "Rank", bold=False)
    put(ws, f"B{page.row + 1}", "Letter", bold=False)
    put(ws, f"B{page.row + 2}", "Count", bold=False)
    for k, c in enumerate(cols("C", TOP_LETTERS), start=1):
        put(ws, f"{c}{page.row}", k, align="center", fill=FILL_HEAD, box=True)
        find = f"MATCH(LARGE({scores},{k}),{scores},0)"
        put(ws, f"{c}{page.row + 1}", f'=IF(INDEX({counts},{find})=0,"",INDEX({alpha},{find}))',
            bold=True, align="center", box=True)
        put(ws, f"{c}{page.row + 2}", f'=IF(INDEX({counts},{find})=0,"",INDEX({counts},{find}))',
            align="center", box=True)
    page.skip(3)

    page.heading("Every letter, beside English")
    top = page.row
    header_row(ws, top, {"B": "Letter", "C": "Count", "D": "% of your text", "E": "English %",
                         "F": "Your text", "K": "English"})
    ws.merge_cells(f"F{top}:J{top}")
    ws.merge_cells(f"K{top}:{page.last}{top}")
    ws.row_dimensions[top].height = ROW_TITLE
    for i, letter in enumerate(ALPHABET):
        r = top + 1 + i
        put(ws, f"B{r}", letter, bold=True, align="center", box=True)
        put(ws, f"C{r}", f"=INDEX({counts},{i + 1})", align="center", box=True)
        put(ws, f"D{r}", f'=IF(LetterCount=0,"",C{r}/LetterCount*{PERCENT})', fmt="0.0", align="center", box=True)
        put(ws, f"E{r}", ENGLISH_PCT[i], fmt="0.0", align="center", box=True)
        merge_put(ws, r, "F", "J", f'=IF(D{r}="","",REPT("{BAR}",ROUND(D{r}*{BAR_PER_PERCENT},0)))',
                  color="1565C0", size=SIZE_SMALL)
        merge_put(ws, r, "K", page.last, f'=REPT("{BAR}",ROUND(E{r}*{BAR_PER_PERCENT},0))',
                  color="9E9E9E", size=SIZE_SMALL)
    end = top + N_LETTERS
    ws.conditional_formatting.add(f"B{top + 1}:C{end}", FormulaRule(formula=[f"$C{top + 1}=0"], fill=_fill(FILL_WARN)))
    bar_chart(ws, title="Your text (blue) and English (orange), percent",
              cats=Reference(ws, min_col=2, min_row=top + 1, max_row=end),
              data=[Reference(ws, min_col=4, min_row=top, max_row=end),
                    Reference(ws, min_col=5, min_row=top, max_row=end)],
              anchor=f"B{end + 2}", y_title="percent", width=26)
    return finish(page)


def english_range(sheet: str, row: int) -> str:
    return f"{sheet}!$B${row}:${col(1 + N_LETTERS)}${row}"


# ---------------------------------------------------------------- 2. Caesar
def build_caesar(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Caesar", "Try all 26 shifts at once, and let chi-squared pick the one that looks most like English.",
        spec.guide_names,
        ["Paste a ciphertext. Each row moves every letter back by one more place (shift 3 turns D into a).",
         "Chi-squared measures how far each row's letter counts are from English: the lowest score, in green, is "
         "almost always the key.",
         "The full decryption below uses the best shift, unless you type another shift into its yellow box."],
        last="P", widths={"C": 8, "O": 12, "P": 12},
    )
    ws, work = page.ws, page.work
    text_input(page, caesar(BAKER, CAESAR_SHIFT))
    counts = letter_counts_row(work, 5)
    english = english_row(work, 7)
    put(work, "A9", "Counts after moving back by the shift in column A (columns: plain a to z)")
    grid_top = 10
    for s in range(N_LETTERS):
        r = grid_top + s
        put(work, f"A{r}", s)
        for p, c in enumerate(cols("B", N_LETTERS)):
            put(work, f"{c}{r}", f"=INDEX({counts},MOD({p}+$A{r},{N_LETTERS})+1)")
        last = col(1 + N_LETTERS)
        put(work, f"{col(2 + N_LETTERS)}{r}",
            f'=IF(LetterCount=0,"",ROUND(SUMPRODUCT((B{r}:{last}{r}-LetterCount*{english})^2/(LetterCount*{english})),{CHI_DECIMALS}))')
    chi_col = col(2 + N_LETTERS)
    chis = f"Workings!${chi_col}${grid_top}:${chi_col}${grid_top + N_LETTERS - 1}"

    page.heading("The best shift")
    shifts = f"Workings!$A${grid_top}:$A${grid_top + N_LETTERS - 1}"
    best = page.stat("Lowest chi-squared at shift", "=" + argmin(chis, shifts), value_last="D")
    page.stat("Key letter (A + shift)", f"=CHAR(65+{best})", value_last="D")
    page.stat("Its chi-squared", f"=MIN({chis})", fmt="0.0", value_last="D")
    put(ws, f"B{page.row}", "Shift to use below (blank: the best)")
    shift_cell = ws[f"C{page.row}"]
    as_input(shift_cell)
    use = f"$C${page.row}"
    page.skip()
    dv = DataValidation(type="whole", operator="between", formula1="0", formula2="25", allow_blank=True,
                        showErrorMessage=True, error="Type a shift from 0 to 25.")
    ws.add_data_validation(dv)
    dv.add(use)

    page.heading("All 26 shifts")
    top = page.row
    header_row(ws, top, {"B": "Shift", "C": "Key", "D": "The start of your text, moved back", "O": "Chi-squared"})
    ws.merge_cells(f"D{top}:N{top}")
    ws.merge_cells(f"O{top}:P{top}")
    for s in range(N_LETTERS):
        r = top + 1 + s
        put(ws, f"B{r}", s, align="center", box=True, bold=True)
        put(ws, f"C{r}", f"=CHAR(65+B{r})", align="center", bold=True, box=True)
        pairs = [(L, f"CHAR(97+MOD({i}-$B{r},{N_LETTERS}))") for i, L in enumerate(ALPHABET)]
        merge_put(ws, r, "D", "N", "=" + nested_substitute(f"UPPER(LEFT(Message,{PREVIEW_CHARS}))", pairs),
                  mono=True, size=SIZE_SMALL + 1)
        merge_put(ws, r, "O", "P", f"=INDEX({chis},{s + 1})", fmt="0.0", align="center")
    end = top + N_LETTERS
    ws.conditional_formatting.add(
        f"B{top + 1}:P{end}", FormulaRule(formula=[f"$O{top + 1}=MIN($O${top + 1}:$O${end})"], fill=_fill(FILL_BEST)))
    page.row = end + 1

    put(work, "A40", "Shift used")
    put(work, "B40", f"=IF({q(page.name)}{use}=\"\",{q(page.name)}{best},{q(page.name)}{use})")
    put(work, "A41", "Decryption")
    pairs = [(L, f"CHAR(97+MOD({i}-$B$40,{N_LETTERS}))") for i, L in enumerate(ALPHABET)]
    put(work, "B41", "=" + nested_substitute("UPPER(Message)", pairs))
    output_lines(page, "Workings!$B$41", title="Your whole text, moved back by that shift")
    return finish(page)


# ---------------------------------------------------------------- 3. affine
def build_affine(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Affine", "Decrypt an affine cipher from its key (a, b), and find the key from two guessed letters.",
        spec.guide_names,
        ["The affine cipher turns plain letter x into a x + b (mod 26), counting a = 0, b = 1, ..., z = 25.",
         "To undo it you need the inverse of a: the number that times a leaves 1 on the 26-hour clock. Only "
         "12 values of a have one (the table on the right).",
         "Do not know the key? Guess two letters (the commonest cipher letter is often e, the next often t) and "
         "the 'Find a and b' box solves the two equations for you."],
        last="P", widths={"R": 8, "S": 12, "T": 10, "U": 14},
    )
    ws, work = page.ws, page.work
    # inverse table on the right
    inv_top = 5
    header_row(ws, inv_top, {"R": "a", "S": "Has an inverse?", "T": "Inverse", "U": "a x inverse"})
    ws.row_dimensions[inv_top].height = ROW_TITLE
    for a in range(1, N_LETTERS):
        r = inv_top + a
        put(ws, f"R{r}", a, align="center", box=True, bold=True)
        put(ws, f"S{r}", f'=IF(GCD(R{r},26)=1,"yes","no")', align="center", box=True)
        put(ws, f"T{r}", f'=IF(GCD(R{r},26)=1,SUMPRODUCT((MOD(R{r}*ROW($A$1:$A$25),26)=1)*ROW($A$1:$A$25)),"none")',
            align="center", box=True)
        put(ws, f"U{r}", f'=IF(ISNUMBER(T{r}),R{r}*T{r}&" = "&INT(R{r}*T{r}/26)&" x 26 + 1","")',
            align="center", box=True, size=SIZE_SMALL)
    inv_col = f"$T${inv_top + 1}:$T${inv_top + N_LETTERS - 1}"

    text_input(page, affine(MUSEUM, *AFFINE_KEY))
    page.heading("The key")
    put(ws, f"B{page.row}", "a (the multiplier)")
    as_input(ws[f"C{page.row}"])
    ws[f"C{page.row}"].value = AFFINE_KEY[0]
    a_ref = f"$C${page.row}"
    page.skip()
    put(ws, f"B{page.row}", "b (the shift)")
    as_input(ws[f"C{page.row}"])
    ws[f"C{page.row}"].value = AFFINE_KEY[1]
    b_ref = f"$C${page.row}"
    page.skip()
    page.stat("Can a be undone?",
                   f'=IF(GCD(MOD({a_ref},26),26)=1,"yes","no: a must be odd and not 13")', value_last="H")
    inv = page.stat("Inverse of a", f'=IF(GCD(MOD({a_ref},26),26)=1,INDEX({inv_col},MOD({a_ref},26)),"none")',
                    value_last="D")
    page.note("Decrypt: plain = inverse of a x (cipher - b), mod 26.   Encrypt: cipher = a x plain + b, mod 26.")
    ws.conditional_formatting.add(f"R{inv_top + 1}:U{inv_top + N_LETTERS - 1}",
                                  FormulaRule(formula=[f"$R{inv_top + 1}=MOD({a_ref},26)"], fill=_fill(FILL_BEST)))

    page.heading("The two alphabets")
    strip = cols("C", N_LETTERS)
    for c in strip:
        ws.column_dimensions[c].width = max(ws.column_dimensions[c].width or 0, 4.5)
    r1, r2, r3, r4 = page.row, page.row + 1, page.row + 3, page.row + 4
    put(ws, f"B{r1}", "Cipher letter", bold=True)
    put(ws, f"B{r2}", "decrypts to")
    put(ws, f"B{r3}", "Plain letter", bold=True)
    put(ws, f"B{r4}", "encrypts to")
    for i, c in enumerate(strip):
        put(ws, f"{c}{r1}", ALPHABET[i], bold=True, align="center", box=True, fill=FILL_HEAD)
        put(ws, f"{c}{r2}", f'=IF(ISNUMBER({inv}),CHAR(97+MOD({inv}*({i}-{b_ref}),26)),"?")', align="center", box=True)
        put(ws, f"{c}{r3}", ALPHABET[i].lower(), bold=True, align="center", box=True, fill=FILL_HEAD)
        put(ws, f"{c}{r4}", f"=CHAR(65+MOD({a_ref}*{i}+{b_ref},26))", align="center", box=True)
    page.row = r4 + 1

    page.heading("Find a and b from two guesses")
    g = page.row
    labels = [("Plain letter 1", "e"), ("is cipher letter", affine("E", *AFFINE_KEY)),
              ("Plain letter 2", "t"), ("is cipher letter", affine("T", *AFFINE_KEY))]
    refs = []
    for k, (label, value) in enumerate(labels):
        put(ws, f"B{g + k}", label)
        as_input(ws[f"C{g + k}"])
        ws[f"C{g + k}"].value = value
        refs.append(f"(CODE(UPPER($C${g + k}))-65)")
    p1, c1, p2, c2 = refs
    page.row = g + len(labels)
    d = f"MOD({p1}-{p2},26)"
    dinv = f"INDEX({inv_col},{d})"
    a_found = f"MOD({dinv}*({c1}-{c2}),26)"
    b_found = f"MOD({c1}-{a_found}*{p1},26)"
    page.stat("Answer", f'=IF(GCD({d},26)<>1,"Those two plain letters are too alike on the clock: pick a different pair.",'
                        f'IF(GCD({a_found},26)<>1,"a comes out as "&{a_found}&", which cannot be undone: a guess is wrong.",'
                        f'"a = "&{a_found}&", b = "&{b_found}&". Type them into the yellow a and b boxes."))')
    counts = letter_counts_row(work, 5)
    put(work, "A8", "Score")
    for i, c in enumerate(cols("B", N_LETTERS)):
        put(work, f"{c}8", f"={c}6+{(N_LETTERS - i) / PERCENT}")
    scores = f"Workings!$B$8:${col(1 + N_LETTERS)}$8"
    alpha = f"Workings!$B$5:${col(1 + N_LETTERS)}$5"
    top = amp(f'INDEX({alpha},MATCH(LARGE({scores},{k}),{scores},0))&" "' for k in range(1, TOP_LETTERS + 1))
    page.stat("Commonest cipher letters", f"={top}")

    put(work, "A10", "Decryption")
    pairs = [(L, f"{q(page.name)}${strip[i]}${r2}") for i, L in enumerate(ALPHABET)]
    put(work, "B10", "=" + nested_substitute("UPPER(Message)", pairs))
    put(work, "A11", "Encryption")
    pairs = [(L.lower(), f"{q(page.name)}${strip[i]}${r4}") for i, L in enumerate(ALPHABET)]
    put(work, "B11", "=" + nested_substitute("LOWER(Message)", pairs))
    output_lines(page, "Workings!$B$10", title="Your text decrypted with (a, b)", n_lines=MAX_LINES // 2)
    output_lines(page, "Workings!$B$11", title="Or: your text encrypted with (a, b), to make a puzzle",
                 n_lines=MAX_LINES // 4)
    return finish(page)


# ---------------------------------------------------------------- 4. substitution
def build_substitution(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Substitution", "Build a substitution key one letter at a time and watch the message appear.",
        spec.guide_names,
        ["Paste a ciphertext. Under each cipher letter, type the plain letter you think it stands for.",
         f"The decryption below fills in as you go: {PLACEHOLDER} marks a letter you have not solved yet.",
         "Start from the counts (the commonest cipher letter is often e), then use short words and patterns. "
         "A red cell means you used the same plain letter twice."],
        last="AB", default_width=4.6, widths={"B": 26},
    )
    ws, work = page.ws, page.work
    text_input(page, substitute(CLUB, CLUB_KEY))
    counts = letter_counts_row(work, 5)
    put(work, "A8", "Score")
    for i, c in enumerate(cols("B", N_LETTERS)):
        put(work, f"{c}8", f"={c}6+{(N_LETTERS - i) / PERCENT}")
    scores = f"Workings!$B$8:${col(1 + N_LETTERS)}$8"
    alpha = f"Workings!$B$5:${col(1 + N_LETTERS)}$5"

    page.heading("Your key")
    strip = cols("C", N_LETTERS)
    r_ct, r_pt, r_n, r_pc, r_two = (page.row + k for k in range(5))
    for label, r in (("Cipher letter", r_ct), ("Plain letter (type)", r_pt), ("Count", r_n), ("Percent", r_pc),
                     ("", r_two)):
        put(ws, f"B{r}", label, bold=r in (r_ct, r_pt))
    solved = {CLUB_KEY[ALPHABET.index(p.upper())]: p for p in CLUB_SOLVED}
    keys = f"${strip[0]}${r_pt}:${strip[-1]}${r_pt}"
    for i, c in enumerate(strip):
        L = ALPHABET[i]
        put(ws, f"{c}{r_ct}", L, bold=True, align="center", box=True, fill=FILL_HEAD)
        as_input(ws[f"{c}{r_pt}"])
        ws[f"{c}{r_pt}"].value = solved.get(L)
        put(ws, f"{c}{r_n}", f"=INDEX({counts},{i + 1})", align="center", box=True)
        put(ws, f"{c}{r_pc}", f'=IF(LetterCount=0,"",{c}{r_n}/LetterCount*{PERCENT})', fmt="0", align="center",
            box=True, size=SIZE_SMALL)
        put(ws, f"{c}{r_two}", f'=IF({c}{r_pt}="","",IF(COUNTIF({keys},{c}{r_pt})>1,"twice",""))',
            align="center", size=SIZE_SMALL - 2, color="C62828")
    ws.conditional_formatting.add(
        f"{strip[0]}{r_pt}:{strip[-1]}{r_pt}",
        FormulaRule(formula=[f'AND({strip[0]}{r_pt}<>"",COUNTIF({keys},{strip[0]}{r_pt})>1)'], fill=_fill(FILL_WARN)))
    page.row = r_two + 1
    unused = amp(f'IF(COUNTIF({keys},"{L}")=0,"{L.lower()} ","")' for L in ALPHABET)
    page.stat("Plain letters not used yet", f"=TRIM({unused})")

    page.heading("Commonest first: your ciphertext and English")
    r_sc, r_sn, r_sp, r_en, r_ep = (page.row + k for k in range(5))
    put(ws, f"B{r_sc}", "Your ciphertext", bold=True)
    put(ws, f"B{r_sn}", "count")
    put(ws, f"B{r_sp}", "your plain letter")
    put(ws, f"B{r_en}", "English", bold=True)
    put(ws, f"B{r_ep}", "English %")
    for k, c in enumerate(strip, start=1):
        find = f"MATCH(LARGE({scores},{k}),{scores},0)"
        put(ws, f"{c}{r_sc}", f"=INDEX({alpha},{find})", bold=True, align="center", box=True, fill=FILL_HEAD)
        put(ws, f"{c}{r_sn}", f"=INDEX({counts},{find})", align="center", box=True)
        put(ws, f"{c}{r_sp}", f'=IF(INDEX({keys},{find})="","",LOWER(INDEX({keys},{find})))',
            align="center", box=True, bold=True)
        put(ws, f"{c}{r_en}", ENGLISH_ORDER[k - 1].lower(), bold=True, align="center", box=True, fill=FILL_HEAD)
        put(ws, f"{c}{r_ep}", ENGLISH_PCT[ALPHABET.index(ENGLISH_ORDER[k - 1])], fmt="0", align="center", box=True,
            size=SIZE_SMALL)
    page.row = r_ep + 1

    put(work, "A10", "Partial decryption")
    pairs = [(L, f'IF({q(page.name)}${strip[i]}${r_pt}="","{PLACEHOLDER}",LOWER({q(page.name)}${strip[i]}${r_pt}))')
             for i, L in enumerate(ALPHABET)]
    put(work, "B10", "=" + nested_substitute("UPPER(Message)", pairs))
    output_lines(page, "Workings!$B$10", title=f"The message so far ({PLACEHOLDER} = not solved yet)")
    return finish(page)


# ---------------------------------------------------------------- 5. Vigenere slices
def build_vigenere(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Slices", "Find a Vigenere key length with the IoC, then solve each slice as a Caesar shift.",
        spec.guide_names,
        ["Paste a ciphertext. The scan splits it into L slices (every L-th letter) for each L from 1 to 20, "
         "and averages the slices' IoC. The right key length makes the average jump up toward English (0.066).",
         "Type that L into the yellow box. Each slice is then a Caesar cipher: chi-squared picks its best "
         "shift, and the shifts spell the key.",
         "The decryption uses that key, unless you type a key of your own into its yellow box."],
        last="P", widths={"C": 9, "D": 9, "E": 9, "F": 9, "G": 9},
    )
    ws, work = page.ws, page.work
    text_input(page, grouped(vigenere(PROBE, PROBE_KEY)))

    # Workings: one letter number per row (PAST_END after the text), for the scan's FREQUENCY counts
    pos_top = 8
    put(work, "A4", "Key used")
    put(work, "A5", "Key length")
    put(work, "B5", "=LEN(KeyUsed)")
    define(page.wb, "KeyLen", "Workings!$B$5")
    put(work, f"A{pos_top - 1}", f"Letter numbers (A = 0; {PAST_END} past the end), first {SCAN_LETTERS} letters")
    for _ in range(SCAN_LETTERS):
        r = pos_top + _
        work[f"B{r}"] = f"=IF(ROW()-{pos_top - 1}>LetterCount,{PAST_END},CODE(MID(Letters,ROW()-{pos_top - 1},1))-65)"
    define(page.wb, "Codes", f"Workings!$B${pos_top}:$B${pos_top + SCAN_LETTERS - 1}")
    scanned = f"MIN(LetterCount,{SCAN_LETTERS})"
    position = f"(ROW(Codes)-{pos_top})"  # 0, 1, 2, ... down the Codes column

    def slice_counts(L: str, j: str) -> str:
        """FREQUENCY of the letters of slice j (1-based) for key length L: 27 counts (A..Z, then the rest)."""
        return f"FREQUENCY(Codes+{PAST_END}*(MOD({position},{L})<>{j}-1),ROW($A$1:$A${N_LETTERS})-1)"

    def slice_size(L: str, j: str) -> str:
        return f"IF({j}>{scanned},0,INT(({scanned}-{j})/{L})+1)"

    # chi-squared weights, one column per shift s: W[x][s] = 1 / English[(x - s) mod 26], then a 0 row
    w_top = pos_top + SCAN_LETTERS + 5
    put(work, f"A{w_top - 4}", "Weights 1/English: cipher letter x (rows) and shift s (columns); a last row of 0")
    eng = english_row(work, w_top - 3)
    put(work, f"A{w_top - 1}", "x \\ s")
    for s, c in enumerate(cols("B", N_LETTERS)):
        put(work, f"{c}{w_top - 1}", s)
    for x in range(N_LETTERS + 1):
        r = w_top + x
        work[f"A{r}"] = x
        for c in cols("B", N_LETTERS):
            work[f"{c}{r}"] = 0 if x == N_LETTERS else f"=1/INDEX({eng},MOD($A{r}-{c}${w_top - 1},26)+1)"
    weights = f"Workings!$B${w_top}:${col(1 + N_LETTERS)}${w_top + N_LETTERS}"
    sum_english = f"SUM({eng})"

    page.heading("The scan: average slice IoC for each key length")
    page.note(f"English is about {IOC_ENGLISH}, random letters about {IOC_RANDOM:.3f}. Green: {SLICE_IOC_GOOD} or "
              f"more. The scan reads the first {SCAN_LETTERS} letters.")
    top = page.row
    header_row(ws, top, {"B": "Key length L", "C": "Average IoC", "D": ""})
    ws.merge_cells(f"D{top}:{page.last}{top}")
    bins = MAX_KEY_LENGTH * N_LETTERS
    idx = f"(ROW($A$1:$A${bins + 1})-1)"  # FREQUENCY gives one count per bin, plus one for "above"
    for L in range(1, MAX_KEY_LENGTH + 1):
        r = top + L
        Lr = f"$B{r}"
        freq = f"FREQUENCY(MOD({position},{Lr})*26+Codes,ROW($A$1:$A${bins})-1)"
        n_j = f"(INT(({scanned}-1-INT({idx}/26))/{Lr})+1)"
        put(ws, f"B{r}", L, align="center", box=True, bold=True)
        put(ws, f"C{r}", f'=IF({scanned}<2*{Lr},"",SUMPRODUCT({freq}*({freq}-1)*({idx}<26*{Lr})'
                         f"/({n_j}*({n_j}-1)+({n_j}<2)))/{Lr})", fmt="0.000", align="center", box=True)
        merge_put(ws, r, "D", page.last, f'=IF(C{r}="","",REPT("{BAR}",ROUND(C{r}*{BAR_PER_IOC},0)))',
                  color="1565C0", size=SIZE_SMALL)
    end = top + MAX_KEY_LENGTH
    ws.conditional_formatting.add(f"B{top + 1}:C{end}",
                                  FormulaRule(formula=[f'AND(ISNUMBER($C{top + 1}),$C{top + 1}>={SLICE_IOC_GOOD})'],
                                              fill=_fill(FILL_BEST)))
    bar_chart(ws, title="Average slice IoC for each key length",
              cats=Reference(ws, min_col=2, min_row=top + 1, max_row=end),
              data=[Reference(ws, min_col=3, min_row=top, max_row=end)],
              anchor=f"{col(column_index_from_string(page.last) + 3)}{top}", y_title="IoC")
    page.row = end + 1

    page.heading("Your key length, slice by slice")
    put(ws, f"B{page.row}", "Key length L to look at")
    as_input(ws[f"C{page.row}"])
    ws[f"C{page.row}"].value = len(PROBE_KEY)
    L_ref = f"$C${page.row}"
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2=str(MAX_KEY_LENGTH),
                        showErrorMessage=True, error=f"Type a key length from 1 to {MAX_KEY_LENGTH}.")
    ws.add_data_validation(dv)
    dv.add(L_ref)
    page.skip()
    L_q = f"{q(page.name)}{L_ref}"

    # Workings: chi-squared of each slice (rows) for each shift (columns), and the best shift
    ch_top = w_top + N_LETTERS + 5
    put(work, f"A{ch_top - 2}", "Chosen L: chi-squared of slice j (rows) moved back by shift s (columns)")
    chi_cols = cols("B", N_LETTERS)
    for s, c in enumerate(chi_cols):
        put(work, f"{c}{ch_top - 1}", s)
    best_col = col(2 + N_LETTERS)
    put(work, f"A{ch_top - 1}", "j \\ s")
    put(work, f"{best_col}{ch_top - 1}", "best shift")
    codes_row = f"${chi_cols[0]}${ch_top - 1}:${chi_cols[-1]}${ch_top - 1}"
    for j in range(1, MAX_KEY_LENGTH + 1):
        r = ch_top + j - 1
        work[f"A{r}"] = j
        n = slice_size(L_q, f"$A{r}")
        f2 = f"{slice_counts(L_q, f'$A{r}')}^2"
        for c in chi_cols:
            work[f"{c}{r}"] = (f'=IF(OR($A{r}>{L_q},{n}<1),"",ROUND(SUMPRODUCT({f2},INDEX({weights},0,{c}${ch_top - 1}+1))'
                               f"/{n}-2*{n}+{n}*{sum_english},{CHI_DECIMALS}))")
        chi_row = f"{chi_cols[0]}{r}:{chi_cols[-1]}{r}"
        work[f"{best_col}{r}"] = f'=IF($A{r}>{L_q},"",{argmin(chi_row, codes_row)})'

    top = page.row
    header_row(ws, top, {"B": "Slice (letters j, j+L, ...)", "C": "Letters", "D": "IoC", "E": "Best shift",
                         "F": "Key letter", "G": "The slice's first letters"})
    ws.merge_cells(f"G{top}:{page.last}{top}")
    ws.row_dimensions[top].height = ROW_TITLE
    for j in range(1, MAX_KEY_LENGTH + 1):
        r = top + j
        jj = f"(ROW()-{top})"
        n = slice_size(L_ref, jj)
        freq = slice_counts(L_ref, jj)
        put(ws, f"B{r}", f'=IF({jj}>{L_ref},"","Slice "&{jj})', align="center", box=True)
        put(ws, f"C{r}", f'=IF({jj}>{L_ref},"",{n})', align="center", box=True)
        put(ws, f"D{r}", f'=IF(OR({jj}>{L_ref},{n}<2),"",SUMPRODUCT({freq}*({freq}-1)*(ROW($A$1:$A${N_LETTERS + 1})'
                         f"<={N_LETTERS}))/({n}*({n}-1)))", fmt="0.000", align="center", box=True)
        put(ws, f"E{r}", f"=Workings!${best_col}{ch_top - 1 + j}", align="center", box=True)
        put(ws, f"F{r}", f'=IF(E{r}="","",CHAR(65+E{r}))', align="center", box=True, bold=True)
        parts = [f"MID(Letters,{jj}+{m}*{L_ref},1)" for m in range(SLICE_PREVIEW)]
        merge_put(ws, r, "G", page.last, f'=IF({jj}>{L_ref},"",' + amp(parts) + ")", mono=True, size=SIZE_SMALL + 1)
    page.row = top + MAX_KEY_LENGTH + 1
    suggested = page.stat("The key these shifts spell", "=" + amp(f"F{top + j}" for j in range(1, MAX_KEY_LENGTH + 1)))
    put(ws, f"B{page.row}", "Key to use (blank: the one above)")
    ws.merge_cells(f"C{page.row}:H{page.row}")
    as_input(ws[f"C{page.row}"], align="left")
    typed = f"$C${page.row}"
    page.skip()
    put(work, "B4", f'=UPPER(IF(TRIM({q(page.name)}{typed})="",{q(page.name)}{suggested},TRIM({q(page.name)}{typed})))')
    define(page.wb, "KeyUsed", "Workings!$B$4")

    def plain(p: str, _k: int) -> str:
        return (f'IF({p}>LetterCount,"",CHAR(97+MOD(CODE(MID(Letters,{p},1))'
                f"-CODE(MID(KeyUsed,MOD({p}-1,KeyLen)+1,1)),26)))")

    computed_lines(page, plain, title="Your text decrypted with that key", n_lines=MAX_LETTERS // LINE_WIDTH,
                   blank_if="KeyLen=0")
    return finish(page)


# ---------------------------------------------------------------- 6. repeats and factors
def build_repeats(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Repeats", "Turn the gaps between repeated fragments into the length of a Vigenere key.",
        spec.guide_names,
        ["Type the gaps you found between repeats into the yellow column (or leave the sample gaps). The table "
         "counts how many gaps each number from 2 to 20 divides.",
         "The sheet also finds repeats of 3 letters (or the length you choose) in your text by itself, and "
         "counts their gaps the same way.",
         "The key length is usually the biggest number that divides (nearly) every gap. Accidental repeats "
         "add a few gaps that fit nothing."],
        last="P", widths={"C": 11, "D": 11, "E": 11, "F": 11, "G": 11},
    )
    ws, work = page.ws, page.work
    ciphertext = vigenere(TREASURE, TREASURE_KEY)
    text_input(page, grouped(ciphertext))
    put(ws, f"B{page.row}", "Repeat length to look for")
    as_input(ws[f"C{page.row}"])
    ws[f"C{page.row}"].value = REPEAT_DEFAULT
    rep_ref = f"{q(page.name)}$C${page.row}"
    dv = DataValidation(type="whole", operator="between", formula1=str(REPEAT_MIN), formula2=str(REPEAT_MAX),
                        showErrorMessage=True, error=f"Type {REPEAT_MIN} to {REPEAT_MAX}.")
    ws.add_data_validation(dv)
    dv.add(f"C{page.row}")
    page.skip()
    define(page.wb, "RepeatLength", f"{q(page.name)}$C${page.row - 1}")

    # Workings, one row per starting letter k: the fragment there, the gap to its next copy (0: none),
    # and a running count of new repeats (a longer repeat counts once, at its start)
    top_w = 7
    for c, t in zip("ABC", ["fragment at k", "gap to its next copy", "repeats so far"]):
        put(work, f"{c}{top_w - 2}", t)
    work[f"B{top_w - 1}"] = 0
    work[f"C{top_w - 1}"] = 0
    end_w = top_w + KASISKI_LETTERS - 1
    for k in range(1, KASISKI_LETTERS + 1):
        r = top_w + k - 1
        here = f"(ROW()-{top_w - 1})"
        work[f"A{r}"] = f'=IF({here}+RepeatLength-1>LetterCount,"",MID(Letters,{here},RepeatLength))'
        work[f"B{r}"] = f'=IF(A{r}="",0,IFERROR(MATCH(A{r},A{r + 1}:A${end_w + 1},0),0))'
        work[f"C{r}"] = f"=C{r - 1}+IF(AND(B{r}>0,B{r}<>B{r - 1}),1,0)"
    gap_col = f"Workings!$B${top_w}:$B${end_w}"
    running = f"Workings!$C${top_w}:$C${end_w}"
    new_flags = f"({running}-Workings!$C${top_w - 1}:$C${end_w - 1})"

    # sample typed gaps: the genuine ones among the gaps the sheet finds itself (a careful reader's list)
    sample_gaps = [g for g in _neighbor_gaps(ciphertext, REPEAT_DEFAULT) if g % len(TREASURE_KEY) == 0][:MAX_GAPS // 2]

    page.heading("Gaps and the numbers that divide them")
    top = page.row
    header_row(ws, top, {"B": "Gaps you found (type)", "C": "Number", "D": "Divides how many of your gaps",
                         "E": "", "H": "Divides how many found gaps", "I": ""})
    ws.merge_cells(f"D{top}:G{top}")
    ws.merge_cells(f"H{top}:{page.last}{top}")
    ws.row_dimensions[top].height = ROW_TITLE
    gaps = f"$B${top + 1}:$B${top + MAX_GAPS}"
    for i in range(MAX_GAPS):
        cell = ws[f"B{top + 1 + i}"]
        as_input(cell)
        cell.value = sample_gaps[i] if i < len(sample_gaps) else None
    end = top + MAX_FACTOR - 1

    def bar(c: str, r: int) -> str:
        top_count = f"MAX(${c}${top + 1}:${c}${end})"
        return f'=IF({top_count}=0,"",REPT("{BAR}",ROUND({c}{r}/{top_count}*{BAR_FULL},0)))'

    for n in range(2, MAX_FACTOR + 1):
        r = top + n - 1
        put(ws, f"C{r}", n, align="center", bold=True, box=True)
        put(ws, f"D{r}", f"=SUMPRODUCT(({gaps}>0)*(MOD({gaps},C{r})=0))", align="center", box=True)
        merge_put(ws, r, "E", "G", bar("D", r), color="1565C0", size=SIZE_SMALL)
        put(ws, f"H{r}", f"=SUMPRODUCT({new_flags}*({gap_col}>0)*(MOD({gap_col},C{r})=0))", align="center", box=True)
        merge_put(ws, r, "I", page.last, bar("H", r), color="2E7D32", size=SIZE_SMALL)
    for c in ("D", "H"):
        ws.conditional_formatting.add(f"{c}{top + 1}:{c}{end}",
                                      FormulaRule(formula=[f"AND({c}{top + 1}>0,{c}{top + 1}>={NEAR_TOP}*MAX(${c}${top + 1}:${c}${end}))"],
                                                  fill=_fill(FILL_BEST)))
    page.row = max(end, top + MAX_GAPS) + 1
    n_typed = f"COUNTIF({gaps},\">0\")"
    page.stat("Your gaps", f"={n_typed}", value_last="D")
    page.stat("Greatest common divisor of your gaps", f'=IF({n_typed}=0,"",GCD({gaps}))', value_last="D")
    d_rng = f"$D${top + 1}:$D${end}"
    h_rng = f"$H${top + 1}:$H${end}"
    n_rng = f"$C${top + 1}:$C${end}"
    page.stat(BEST_GUESS_YOURS,
              f'=IF(MAX({d_rng})=0,"",SUMPRODUCT(MAX(({d_rng}>={NEAR_TOP}*MAX({d_rng}))*{n_rng})))', value_last="D")
    page.stat("Found gaps", f"=MAX({running})", value_last="D")
    page.stat(BEST_GUESS_FOUND,
              f'=IF(MAX({h_rng})=0,"",SUMPRODUCT(MAX(({h_rng}>={NEAR_TOP}*MAX({h_rng}))*{n_rng})))', value_last="D")
    page.note(f"Best guess: the biggest number that divides at least {NEAR_TOP:.0%} as many gaps as the top one "
              "(green). An accidental repeat or two then cannot hide the key length.")

    page.heading(f"Repeats found in your text (the first {MAX_FOUND})")
    t2 = page.row
    header_row(ws, t2, {"B": "Fragment", "C": "Starts at", "D": "Again at", "E": "Gap"})
    for i in range(1, MAX_FOUND + 1):
        r = t2 + i
        at = f"MATCH({i},{running},0)"
        put(ws, f"B{r}", f'=IFERROR(INDEX(Workings!$A${top_w}:$A${end_w},{at}),"")', mono=True, align="center",
            box=True, bold=True)
        put(ws, f"C{r}", f'=IFERROR({at},"")', align="center", box=True)
        put(ws, f"E{r}", f'=IFERROR(INDEX({gap_col},{at}),"")', align="center", box=True)
        put(ws, f"D{r}", f'=IF(C{r}="","",C{r}+E{r})', align="center", box=True)
    page.row = t2 + MAX_FOUND + 1
    page.note("A longer repeat shows up once, at its start. Each gap is to the next copy of the same fragment.")
    return finish(page)


def _neighbor_gaps(letters: str, length: int) -> list[int]:
    """Gaps to the next copy of each fragment, once per run (what the sheet computes)."""
    gaps, prev = [], None
    for k in range(len(letters) - length + 1):
        frag = letters[k:k + length]
        nxt = letters.find(frag, k + 1)
        gap = nxt - k if nxt >= 0 else None
        if gap is not None and gap != prev:
            gaps.append(gap)
        prev = gap
    return gaps


# ---------------------------------------------------------------- 7. columnar
UNDO, MAKE = "undo a columnar", "make a columnar"


def build_columnar(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Columns", "Cut a ciphertext into columns, put them in order, and read the rows.",
        spec.guide_names,
        [f"To undo a columnar: choose '{UNDO}', type the width (number of columns), and type the order "
         "numbers above the columns. The grid shows the ciphertext cut into strips and set in that order; "
         "read across the rows.",
         f"To make one: choose '{MAKE}'. Your text is written in rows, and the columns are read off in the "
         "order of the numbers (1 first).",
         "Detective work: try widths that divide the length, then swap the order numbers until the rows "
         "read as English. Blank order boxes count as 1, 2, 3, ..."],
        last="P", widths={c: 6 for c in cols("C", MAX_WIDTH)} | {"O": 16, "P": 16},
    )
    ws, work = page.ws, page.work
    order = column_order(GATE_KEYWORD)
    plain = only_letters(GATE)
    plain += PAD_LETTER * (-len(plain) % len(order))
    text_input(page, grouped(columnar(plain, order)))
    page.heading("Settings")
    put(ws, f"B{page.row}", "What to do")
    ws.merge_cells(f"C{page.row}:H{page.row}")
    as_input(ws[f"C{page.row}"], align="left")
    ws[f"C{page.row}"].value = UNDO
    mode = f"$C${page.row}"
    dv = DataValidation(type="list", formula1=f'"{UNDO},{MAKE}"', showErrorMessage=True)
    ws.add_data_validation(dv)
    dv.add(mode)
    page.skip()
    put(ws, f"B{page.row}", "Width (number of columns)")
    as_input(ws[f"C{page.row}"])
    ws[f"C{page.row}"].value = len(order)
    w = f"$C${page.row}"
    dv = DataValidation(type="whole", operator="between", formula1="2", formula2=str(MAX_WIDTH),
                        showErrorMessage=True, error=f"Type a width from 2 to {MAX_WIDTH}.")
    ws.add_data_validation(dv)
    dv.add(w)
    page.skip()
    divs = amp(f'IF(MOD(LetterCount,{d})=0,"{d} ","")' for d in range(2, MAX_WIDTH + 1))
    page.stat("Widths that divide the length", f"=TRIM({divs})")

    grid_cols = cols("C", MAX_WIDTH)
    page.heading("The grid")
    r_num, r_key = page.row, page.row + 1
    put(ws, f"B{r_num}", "Column")
    put(ws, f"B{r_key}", "Order (type)", bold=True)
    for c_i, c in enumerate(grid_cols, start=1):
        put(ws, f"{c}{r_num}", f'=IF({c_i}>{w},"",{c_i})', align="center", color=MUTED)
        as_input(ws[f"{c}{r_key}"])
        ws[f"{c}{r_key}"].value = order[c_i - 1] if c_i <= len(order) else None
    page.row = r_key + 1

    # Workings: per column c, its effective order number, length and start in the ciphertext
    top_c = 6
    for c, t in zip("ABCDE", ["column", "order", "length", "start", "column read at turn"]):
        put(work, f"{c}{top_c - 1}", t)
    keys = f"$B${top_c}:$B${top_c + MAX_WIDTH - 1}"
    lens = f"$C${top_c}:$C${top_c + MAX_WIDTH - 1}"
    starts = f"$D${top_c}:$D${top_c + MAX_WIDTH - 1}"
    wq = f"{q(page.name)}{w}"
    for c_i in range(1, MAX_WIDTH + 1):
        r = top_c + c_i - 1
        typed = f"{q(page.name)}${grid_cols[c_i - 1]}${r_key}"
        work[f"A{r}"] = c_i
        work[f"B{r}"] = f'=IF(A{r}>{wq},99,IF({typed}="",A{r},{typed}))'
        work[f"C{r}"] = f"=IF(A{r}>{wq},0,INT(LetterCount/{wq})+IF(A{r}<=MOD(LetterCount,{wq}),1,0))"
        work[f"D{r}"] = f"=SUMPRODUCT(({keys}<B{r})*{lens})"
        work[f"E{r}"] = f'=IF(A{r}>{wq},"",IFERROR(MATCH(A{r},{keys},0),""))'
    ok_formula = f"=SUMPRODUCT((Workings!$A${top_c}:$A${top_c + MAX_WIDTH - 1}<={wq})*(COUNTIF(Workings!{keys},Workings!$A${top_c}:$A${top_c + MAX_WIDTH - 1})=1))"
    put(work, "A3", "Letter count")
    put(work, "A4", "Order check")
    put(work, "B4", ok_formula)
    page.stat("Order check", f'=IF(Workings!$B$4={w},"OK: each number from 1 to "&{w}&" once",'
                             f'"Each number from 1 to "&{w}&" must appear exactly once")')

    g_top = page.row
    header_row(ws, g_top, {"B": "Row", "O": "Read across", "P": ""})
    ws.merge_cells(f"O{g_top}:P{g_top}")
    for c_i, c in enumerate(grid_cols, start=1):
        put(ws, f"{c}{g_top}", f'=IF({c_i}>{w},"",INDEX(Workings!{keys},{c_i}))', bold=True, align="center",
            fill=FILL_HEAD, box=True)
    for i in range(1, MAX_GRID_ROWS + 1):
        r = g_top + i
        put(ws, f"B{r}", f'=IF(({i}-1)*{w}<LetterCount,{i},"")', align="center", color=MUTED)
        # one formula for the whole grid: row i = ROW() - g_top, column c = COLUMN() - 2
        i_, c_ = f"(ROW()-{g_top})", f"(COLUMN()-{column_index_from_string(grid_cols[0]) - 1})"
        undo = (f'IF({i_}>INDEX(Workings!{lens},{c_}),"",'
                f"MID(Letters,INDEX(Workings!{starts},{c_})+{i_},1))")
        make = f"MID(Letters,({i_}-1)*{w}+{c_},1)"
        for c in grid_cols:
            put(ws, f"{c}{r}", f'=IF({c_}>{w},"",IF({mode}="{UNDO}",{undo},{make}))', align="center",
                mono=True, size=SIZE_MONO, box=True)
        merge_put(ws, r, "O", "P", "=" + amp(f"{c}{r}" for c in grid_cols), mono=True, size=SIZE_MONO)
    g_end = g_top + MAX_GRID_ROWS
    page.row = g_end + 1
    grid = f"{q(page.name)}${grid_cols[0]}${g_top + 1}:${grid_cols[-1]}${g_end}"

    # Workings: rows joined, and columns read in order
    put(work, "A20", "Rows joined")
    put(work, "B20", "=" + amp(f"{q(page.name)}$O${g_top + i}" for i in range(1, MAX_GRID_ROWS + 1)))
    put(work, "A21", "Columns in order")
    strip_refs = []
    for t in range(1, MAX_WIDTH + 1):
        r = 21 + t
        put(work, f"A{r}", f"turn {t}")
        c_at = f"Workings!$E${top_c + t - 1}"
        parts = [f"INDEX({grid},{i},{c_at})" for i in range(1, MAX_GRID_ROWS + 1)]
        put(work, f"B{r}", f'=IF({c_at}="",""," "&' + amp(parts) + ")")
        strip_refs.append(f"B{r}")
    put(work, "A35", "Output")
    put(work, "B35", f'=IF({q(page.name)}{mode}="{UNDO}",B20,TRIM({amp(strip_refs)}))')
    output_lines(page, "Workings!$B$35", title="The result (rows read across, or columns read in order)",
                 n_lines=MAX_LINES // 2)
    return finish(page)


# ---------------------------------------------------------------- 8. digraphs
ENGLISH_PAIRS = "TH HE IN ER AN RE ON AT EN ND TI ES OR TE OF"


def build_digraphs(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Pairs", "Count letter pairs and check the tells of Playfair and Hill.",
        spec.guide_names,
        ["Paste a ciphertext. It is cut into pairs from the very first letter (1-2, 3-4, 5-6, ...), the way "
         "Playfair and Hill cut it.",
         "Playfair can never make an odd length, a doubled pair such as EE, or a J. Hill (2x2) needs an even "
         "length but allows all of those.",
         "The big table counts every pair: row = first letter, column = second letter. Darker means more."],
        last="AB", default_width=4.6, widths={"B": 34},
    )
    ws, work = page.ws, page.work
    text_input(page, grouped(playfair(FOG, FOG_KEYWORD)))
    counts = letter_counts_row(work, 5)

    # Workings, one row per pair: the pair, a score (its count, plus a tie-breaker, on its first
    # appearance only), and whether its reverse also appears
    top_w = 9
    for c, t in zip("ABC", ["pair", "score (count on first appearance)", "reverse seen?"]):
        put(work, f"{c}{top_w - 1}", t)
    end_w = top_w + MAX_PAIRS - 1
    pairs = f"$A${top_w}:$A${end_w}"
    for k in range(1, MAX_PAIRS + 1):
        r = top_w + k - 1
        here = f"(ROW()-{top_w - 1})"
        work[f"A{r}"] = f'=IF(2*{here}>LetterCount,"",MID(Letters,2*{here}-1,2))'
        work[f"B{r}"] = f'=IF(A{r}="",0,IF(MATCH(A{r},{pairs},0)={here},COUNTIF({pairs},A{r})+1/({here}+1),0))'
        work[f"C{r}"] = (f'=IF(OR(B{r}=0,LEFT(A{r},1)=RIGHT(A{r},1)),0,'
                         f'IF(COUNTIF({pairs},RIGHT(A{r},1)&LEFT(A{r},1))>0,1,0))')
    W = "Workings!"
    scores = f"{W}$B${top_w}:$B${end_w}"
    pair_rng = f"{W}{pairs}"

    page.heading("The tells")
    page.stat("Length is", '=IF(LetterCount=0,"",IF(MOD(LetterCount,2)=0,"even","odd"))', value_last="E")
    dbl = page.stat("Doubled pairs (such as EE)",
                    f'=SUMPRODUCT(({pair_rng}<>"")*(LEFT({pair_rng},1)=RIGHT({pair_rng},1)))', value_last="E")
    js = page.stat("How many J", '=LEN(Letters)-LEN(SUBSTITUTE(Letters,"J",""))', value_last="E")
    diff = page.stat("Different letters used", f'=COUNTIF({counts},">0")', value_last="E")
    page.stat("Index of coincidence", f'=IF(LetterCount<2,"",SUMPRODUCT({counts},{counts}-1)/(LetterCount*(LetterCount-1)))',
              fmt="0.000", value_last="E")
    page.stat("Different pairs", f'=COUNTIF({scores},">0")', value_last="E")
    page.stat("Pairs whose reverse also appears (AB and BA)", f"=SUM({W}$C${top_w}:$C${end_w})/2", value_last="E")
    page.stat("Playfair?",
              f'=IF(LetterCount=0,"",IF(AND(MOD(LetterCount,2)=0,{dbl}=0,{js}=0,{diff}<=25),'
              '"Could be Playfair: even length, no doubled pair, no J.",'
              '"Not Playfair:"&IF(MOD(LetterCount,2)=1," odd length;","")&IF('
              f'{dbl}>0," a doubled pair;","")&IF({js}>0," a J;","")&IF({diff}>25," all 26 letters;","")))')
    page.stat("Hill (2x2)?", '=IF(LetterCount=0,"",IF(MOD(LetterCount,2)=0,"Could be 2x2 Hill: even length '
                             '(J and doubled pairs are allowed).","Not 2x2 Hill: odd length."))')

    page.heading(f"The {TOP_PAIRS} commonest pairs")
    r_p, r_n = page.row, page.row + 1
    put(ws, f"B{r_p}", "Your pairs", bold=True)
    put(ws, f"B{r_n}", "count")
    for k in range(1, TOP_PAIRS + 1):
        c1, c2 = cols(col(1 + 2 * k - 1 + 1), 2)
        find = f"MATCH(LARGE({scores},{k}),{scores},0)"
        put(ws, f"{c1}{r_p}", f'=IF(LARGE({scores},{k})=0,"",INDEX({W}{pairs},{find}))', bold=True, align="center",
            fill=FILL_HEAD, mono=True)
        ws.merge_cells(f"{c1}{r_p}:{c2}{r_p}")
        put(ws, f"{c1}{r_n}", f'=IF(LARGE({scores},{k})=0,"",INT(LARGE({scores},{k})))', align="center")
        ws.merge_cells(f"{c1}{r_n}:{c2}{r_n}")
    page.row = r_n + 1
    page.stat("English's commonest pairs", ENGLISH_PAIRS, bold=False)

    page.heading("Every pair: first letter down the side, second letter across the top")
    top = page.row
    strip = cols("C", N_LETTERS)
    put(ws, f"B{top}", "first \\ second", align="center", fill=FILL_HEAD, size=SIZE_SMALL)
    for c, L in zip(strip, ALPHABET):
        put(ws, f"{c}{top}", L, bold=True, align="center", fill=FILL_HEAD, size=SIZE_SMALL + 1)
    for i, L in enumerate(ALPHABET):
        r = top + 1 + i
        put(ws, f"B{r}", L, bold=True, align="center", fill=FILL_HEAD, size=SIZE_SMALL + 1)
        for c in strip:
            put(ws, f"{c}{r}", f'=COUNTIF({W}{pairs},$B{r}&{c}${top})', align="center", size=SIZE_SMALL - 1)
    end = top + N_LETTERS
    ws.conditional_formatting.add(f"C{top + 1}:{strip[-1]}{end}",
                                  ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                                                 end_type="max", end_color="1E88E5"))
    page.row = end + 1
    return finish(page)


# ---------------------------------------------------------------- 9. Hill 2x2
def build_hill(spec: SheetSpec) -> Workbook:
    page = new_page(
        spec.title, "Hill", "Check a 2x2 Hill key, find its undo matrix, and encrypt or decrypt a message.",
        spec.guide_names,
        ["Type the four numbers of the key matrix. The letters are numbered a = 0, b = 1, ..., z = 25.",
         "A key can be undone only if its determinant (a d - b c, mod 26) is odd and not 13. Then the sheet "
         "builds the undo matrix: swap a and d, flip the signs of b and c, times the inverse of the determinant.",
         f"Paste a text: it is cut into pairs (an {PAD_LETTER} is added to an odd length) and each pair is "
         "multiplied by the matrix."],
        last="P", widths={"C": 10, "D": 10, "E": 4, "F": 10, "G": 10},
    )
    ws, work = page.ws, page.work
    page.heading("The key matrix K")
    r1, r2 = page.row, page.row + 1
    for (r, c), v in zip([(r1, "C"), (r1, "D"), (r2, "C"), (r2, "D")], HILL_KEY):
        as_input(ws[f"{c}{r}"])
        ws[f"{c}{r}"].value = v
    put(ws, f"B{r1}", "a   b")
    put(ws, f"B{r2}", "c   d")
    a, b, c, d = f"$C${r1}", f"$D${r1}", f"$C${r2}", f"$D${r2}"
    page.row = r2 + 1
    det = page.stat("Determinant a d - b c", f"={a}*{d}-{b}*{c}", value_last="D")
    det26 = page.stat("Determinant mod 26", f"=MOD({det},26)", value_last="D")
    page.stat("Can K be undone?", f'=IF(GCD({det26},26)=1,"yes","no: the determinant must be odd and not 13")',
              value_last="H")
    dinv = page.stat("Inverse of the determinant",
                     f'=IF(GCD({det26},26)=1,SUMPRODUCT((MOD({det26}*ROW($A$1:$A$25),26)=1)*ROW($A$1:$A$25)),"none")',
                     value_last="D")

    page.heading("The undo matrix K⁻¹, and a check")
    r1, r2 = page.row, page.row + 1
    put(ws, f"B{r1}", "K⁻¹ (top row)")
    put(ws, f"B{r2}", "K⁻¹ (bottom row)")
    for (r, cc), expr in zip([(r1, "C"), (r1, "D"), (r2, "C"), (r2, "D")], [d, f"-{b}", f"-{c}", a]):
        put(ws, f"{cc}{r}", f'=IF(ISNUMBER({dinv}),MOD({dinv}*{expr},26),"")', bold=True, align="center",
            box=True, fill=FILL_BEST)
    ia, ib, ic, id_ = f"$C${r1}", f"$D${r1}", f"$C${r2}", f"$D${r2}"
    put(ws, f"H{r1}", "← K x K⁻¹ mod 26", size=SIZE_SMALL, color=MUTED)
    for (r, cc), expr in zip([(r1, "F"), (r1, "G"), (r2, "F"), (r2, "G")],
                             [f"{a}*{ia}+{b}*{ic}", f"{a}*{ib}+{b}*{id_}", f"{c}*{ia}+{d}*{ic}", f"{c}*{ib}+{d}*{id_}"]):
        put(ws, f"{cc}{r}", f'=IF(ISNUMBER({ia}),MOD({expr},26),"")', align="center", box=True)
    page.row = r2 + 1
    page.note("The check should show 1 0 / 0 1: then K⁻¹ undoes K.")

    text_input(page, grouped(hill(APPLES, HILL_KEY)))
    put(work, "A4", "Padded")
    put(work, "B4", f'=Letters&IF(MOD(LetterCount,2)=1,"{PAD_LETTER}","")')
    define(page.wb, "Padded", "Workings!$B$4")
    put(work, "A5", "Padded length")
    put(work, "B5", "=LEN(Padded)")
    define(page.wb, "PadLen", "Workings!$B$5")
    for name, ref in dict(HillA=a, HillB=b, HillC=c, HillD=d, UndoA=ia, UndoB=ib, UndoC=ic, UndoD=id_).items():
        define(page.wb, name, f"{q(page.name)}{ref}")

    def pair_term(first: str, second: str, case: int):
        """Character p of the result: the pair's top row for odd p, its bottom row for even p."""
        def x(p: str) -> str:
            return f"(CODE(MID(Padded,{p},1))-65)"

        def term(p: str, k: int) -> str:
            odd = k % 2 == 1
            value = f"{first}*{x(p)}+{second}*{x(p + '+1')}" if odd else f"{first}*{x(p + '-1')}+{second}*{x(p)}"
            return f'IF({p}>PadLen,"",CHAR({case}+MOD({value},26)))'
        return term

    def hill_lines(title: str, top: tuple[str, str], bottom: tuple[str, str], case: int, blank_if: str) -> None:
        top_term, bottom_term = pair_term(*top, case), pair_term(*bottom, case)

        def term(p: str, k: int) -> str:
            return top_term(p, k) if k % 2 == 1 else bottom_term(p, k)
        computed_lines(page, term, title=title, n_lines=MAX_LINES // 2, blank_if=blank_if)

    page.heading("The first pair, step by step")
    x1 = "(CODE(MID(Padded,1,1))-65)"
    x2 = "(CODE(MID(Padded,2,1))-65)"
    page.stat("First pair", f'=IF(LetterCount=0,"",MID(Padded,1,2)&" = ("&{x1}&", "&{x2}&")")')
    page.stat("Encrypt, top row", f'=IF(LetterCount=0,"",{a}&" x "&{x1}&" + "&{b}&" x "&{x2}&" = "&({a}*{x1}+{b}*{x2})'
                                  f'&", mod 26 = "&MOD({a}*{x1}+{b}*{x2},26)&" = "&CHAR(65+MOD({a}*{x1}+{b}*{x2},26)))')
    page.stat("Encrypt, bottom row", f'=IF(LetterCount=0,"",{c}&" x "&{x1}&" + "&{d}&" x "&{x2}&" = "&({c}*{x1}+{d}*{x2})'
                                     f'&", mod 26 = "&MOD({c}*{x1}+{d}*{x2},26)&" = "&CHAR(65+MOD({c}*{x1}+{d}*{x2},26)))')
    page.stat("Decrypt, top row", f'=IF(OR(LetterCount=0,NOT(ISNUMBER({ia}))),"",{ia}&" x "&{x1}&" + "&{ib}&" x "&{x2}'
                                  f'&" = "&({ia}*{x1}+{ib}*{x2})&", mod 26 = "&MOD({ia}*{x1}+{ib}*{x2},26)&" = "'
                                  f'&CHAR(97+MOD({ia}*{x1}+{ib}*{x2},26)))')
    page.stat("Decrypt, bottom row", f'=IF(OR(LetterCount=0,NOT(ISNUMBER({ia}))),"",{ic}&" x "&{x1}&" + "&{id_}&" x "'
                                     f'&{x2}&" = "&({ic}*{x1}+{id_}*{x2})&", mod 26 = "&MOD({ic}*{x1}+{id_}*{x2},26)'
                                     f'&" = "&CHAR(97+MOD({ic}*{x1}+{id_}*{x2},26)))')
    hill_lines("Decrypted with K⁻¹ (ciphertext to plaintext)", ("UndoA", "UndoB"), ("UndoC", "UndoD"),
               ord("a"), "NOT(ISNUMBER(UndoA))")
    hill_lines("Encrypted with K (plaintext to ciphertext)", ("HillA", "HillB"), ("HillC", "HillD"), ord("A"),
               "LetterCount=0")
    return finish(page)


# ---------------------------------------------------------------- the set
GUIDE_TITLES = {
    "01-reading-the-clues": "Guide 01, Reading the clues",
    "02-frequency-analysis": "Guide 02, Frequency analysis",
    "03-keys-and-brute-force": "Guide 03, Keys and brute force",
    "04-index-of-coincidence": "Guide 04, The index of coincidence",
    "05-repeats-and-key-length": "Guide 05, Repeats and key length",
    "06-cribs-and-patterns": "Guide 06, Cribs and patterns",
    "07-transposition-detective-work": "Guide 07, Transposition detective work",
    "08-scoring-and-hill-climbing": "Guide 08, Scoring and hill climbing",
    "09-two-letters-at-a-time": "Guide 09, Two letters at a time",
}


@dataclass(frozen=True)
class SheetSpec:
    """One spreadsheet: its manifest entry and the function that builds it."""

    num: int
    slug: str
    title: str
    does: str
    guides: tuple[str, ...]
    methods: tuple[str, ...]
    build: Callable[[SheetSpec], Workbook]

    @property
    def file(self) -> str:
        return f"{self.num:02d}-{self.slug}.xlsx"

    @property
    def guide_names(self) -> str:
        names = [GUIDE_TITLES[g] for g in self.guides]
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


SHEETS = [
    SheetSpec(1, "letter-counts", "Letter counts and IoC",
              "Counts every letter of a text beside English's percentages and works out the index of coincidence.",
              ("01-reading-the-clues", "02-frequency-analysis", "04-index-of-coincidence"),
              ("letter frequencies", "index of coincidence", "chi-squared"), build_counts),
    SheetSpec(2, "caesar", "Caesar: all 26 shifts",
              "Shows a text moved back by all 26 shifts and scores each with chi-squared, so the best shift stands out.",
              ("02-frequency-analysis", "03-keys-and-brute-force"),
              ("brute force", "chi-squared"), build_caesar),
    SheetSpec(3, "affine", "Affine: decrypt and inverses",
              "Decrypts an affine cipher from a and b, lists the inverses mod 26, and solves the key from two guessed letters.",
              ("03-keys-and-brute-force",),
              ("modular arithmetic", "multiplicative inverses", "two equations"), build_affine),
    SheetSpec(4, "substitution", "Substitution helper",
              "Lets you build a substitution key letter by letter and shows the partly decrypted message as you go.",
              ("02-frequency-analysis", "06-cribs-and-patterns"),
              ("frequency analysis", "cribs and patterns"), build_substitution),
    SheetSpec(5, "vigenere-slices", "Vigenere slices",
              "Scans key lengths 1 to 20 by average slice IoC, then solves each slice as a Caesar shift to suggest the key.",
              ("04-index-of-coincidence", "05-repeats-and-key-length"),
              ("index of coincidence", "splitting into slices", "chi-squared"), build_vigenere),
    SheetSpec(6, "repeats-and-factors", "Repeats and factors",
              "Counts how many gaps between repeats each number from 2 to 20 divides, from gaps you type or repeats it finds.",
              ("05-repeats-and-key-length",),
              ("Kasiski examination", "common factors"), build_repeats),
    SheetSpec(7, "columnar", "Columnar grid",
              "Writes a text into a grid of any width and reads it off by columns in the order you type, or undoes that.",
              ("07-transposition-detective-work",),
              ("columnar transposition", "widths from factors", "anagramming columns"), build_columnar),
    SheetSpec(8, "digraphs", "Letter pairs (digraphs)",
              "Counts letter pairs and checks the Playfair and Hill tells: even length, doubled pairs, J.",
              ("09-two-letters-at-a-time", "01-reading-the-clues"),
              ("digraph counts", "Playfair tells", "Hill tells"), build_digraphs),
    SheetSpec(9, "hill", "Hill 2x2",
              "Finds a 2x2 Hill key's determinant and undo matrix mod 26, and encrypts or decrypts a text with it.",
              ("09-two-letters-at-a-time",),
              ("matrices mod 26", "determinant", "inverse matrix"), build_hill),
]


# ---------------------------------------------------------------- writing
_CELL_REF = re.compile(r'<c r="([A-Z]+)(\d+)"')
_ROW = re.compile(r'<row r="(\d+)"([^>]*?)(/>|>(.*?)</row>)', re.S)
_FORMULA_CELL = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*)><f>([^<]*)</f></c>')
MIN_SHARED = 2  # a run of at least this many filled-down formulas becomes one shared formula
THEME_PART = "xl/theme/theme1.xml"
STRIP_ADDRESSES = False  # True is valid OOXML (and LibreOffice reads it) but Google Sheets refuses to convert it
DROP_THEME = True  # optional part; Google Sheets converts without it


def _share_formulas(xml: str) -> str:
    """Turn runs of filled-down formulas in a column into Excel shared formulas.

    A run is consecutive rows of one column whose formulas are the first one moved down (the way
    a spreadsheet fills a formula down). Only the first cell keeps the text; the rest point to it.
    """
    cells = list(_FORMULA_CELL.finditer(xml))
    by_col: dict[str, list] = {}
    for m in cells:
        by_col.setdefault(m.group(1), []).append(m)
    new: dict[int, str] = {}
    si = 0
    for column, items in by_col.items():
        i = 0
        while i < len(items):
            first = items[i]
            origin = f"{column}{first.group(2)}"
            tr = Translator("=" + unescape(first.group(4)), origin=origin)
            j = i + 1
            while (j < len(items) and int(items[j].group(2)) == int(items[j - 1].group(2)) + 1
                   and tr.translate_formula(f"{column}{items[j].group(2)}")[1:] == unescape(items[j].group(4))):
                j += 1
            if j - i >= MIN_SHARED:
                last = items[j - 1]
                ref = f"{origin}:{column}{last.group(2)}"
                new[first.start()] = (f'<c r="{origin}"{first.group(3)}><f t="shared" ref="{ref}" si="{si}">'
                                      f"{first.group(4)}</f></c>")
                for m in items[i + 1:j]:
                    new[m.start()] = f'<c r="{m.group(1)}{m.group(2)}"{m.group(3)}><f t="shared" si="{si}"/></c>'
                si += 1
            i = j
    out, pos = [], 0
    for m in cells:
        if m.start() in new:
            out += [xml[pos:m.start()], new[m.start()]]
            pos = m.end()
    out.append(xml[pos:])
    return "".join(out)


def _strip_cell_refs(row_xml: str) -> str:
    """Drop a cell's address when it follows the previous cell (the address is optional then).

    The first cell of a shared formula keeps its address: readers translate the formula from it.
    """
    prev = 0
    out, pos = [], 0
    for m in _CELL_REF.finditer(row_xml):
        index = column_index_from_string(m.group(1))
        out.append(row_xml[pos:m.start()])
        cell_end = row_xml.find("</c>", m.end())
        is_master = ' ref="' in row_xml[m.end():cell_end if cell_end >= 0 else None]
        out.append("<c" if index == prev + 1 and not is_master else m.group(0))
        prev, pos = index, m.end()
    out.append(row_xml[pos:])
    return "".join(out)


def _compact_sheet(xml: str, *, strip_addresses: bool) -> str:
    """Share filled-down formulas; optionally drop the addresses a reader can work out by position."""
    xml = re.sub(r"<v\s*/>|<v></v>", "", xml)
    xml = _share_formulas(xml)
    if not strip_addresses:
        return xml
    prev = 0

    def row(m):
        nonlocal prev
        number = int(m.group(1))
        head = "<row" if number == prev + 1 else f'<row r="{number}"'
        prev = number
        if m.group(4) is None:
            return f"{head}{m.group(2)}{m.group(3)}"
        return f"{head}{m.group(2)}>{_strip_cell_refs(m.group(4))}</row>"

    return _ROW.sub(row, xml)


def _compact(data: bytes, *, strip_addresses: bool = STRIP_ADDRESSES, drop_theme: bool = DROP_THEME) -> bytes:
    """Rewrite an xlsx with shared formulas and maximum compression (and the optional parts dropped)."""
    src = zipfile.ZipFile(io.BytesIO(data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as dst:
        for item in src.infolist():
            if drop_theme and item.filename == THEME_PART:
                continue  # optional: the sheets set every font and color themselves
            content = src.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet"):
                content = _compact_sheet(content.decode("utf-8"), strip_addresses=strip_addresses).encode("utf-8")
            elif drop_theme and item.filename in ("[Content_Types].xml", "xl/_rels/workbook.xml.rels"):
                content = re.sub(r"<(Override|Relationship)\b[^>]*theme1\.xml\"[^>]*/>", "",
                                 content.decode("utf-8")).encode("utf-8")
            dst.writestr(item.filename, content)
    return buf.getvalue()


def save(wb: Workbook, path: Path) -> int:
    buf = io.BytesIO()
    wb.active = 0
    wb.save(buf)
    data = _compact(buf.getvalue())
    path.write_bytes(data)
    return len(data)


def write_manifest(specs) -> None:
    """Write sheets.json, keeping the Google ids and links already recorded there."""
    old = {}
    if MANIFEST.exists():
        old = {e["id"]: e for e in json.loads(MANIFEST.read_text())}
    entries = []
    for s in specs:
        prev = old.get(s.slug, {})
        entries.append({
            "id": s.slug,
            "title": s.title,
            "does": s.does,
            "guides": list(s.guides),
            "methods": list(s.methods),
            "google_id": prev.get("google_id"),
            "view_url": prev.get("view_url"),
            "copy_url": prev.get("copy_url"),
            "xlsx": f"{REPO_DIR}/{s.file}",
        })
    MANIFEST.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")


def main(only: list[str] | None = None) -> None:
    specs = [s for s in SHEETS if not only or s.slug in only or f"{s.num:02d}" in only]
    for s in specs:
        size = save(s.build(s), HERE / s.file)
        print(f"{s.file}: {size:,} bytes")
    write_manifest(SHEETS)


if __name__ == "__main__":
    main(sys.argv[1:])
