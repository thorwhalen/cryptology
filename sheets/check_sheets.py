"""Check the spreadsheets by recalculating them with LibreOffice.

Opens every ``sheets/NN-*.xlsx`` in headless LibreOffice (with "always
recalculate" on load), saves the computed copy to a temporary folder, and checks
that each sample gives the answer the reference ciphers in ``build_sheets.py``
say it should, and that no cell shows an error. Run after ``build_sheets.py``::

    python sheets/check_sheets.py            # all sheets
    python sheets/check_sheets.py caesar     # one sheet (by slug or number)

Needs LibreOffice (``soffice`` on the PATH, or the macOS app).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # the build script sits beside this one
import build_sheets as B  # noqa: E402
SOFFICE_CANDIDATES = ("soffice", "libreoffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
ERRORS = ("#VALUE!", "#REF!", "#NAME?", "#DIV/0!", "#N/A", "#NUM!", "Err:")
RECALC_ALWAYS = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
"""


def soffice() -> str:
    for name in SOFFICE_CANDIDATES:
        found = shutil.which(name) or (name if Path(name).exists() else None)
        if found:
            return found
    sys.exit("LibreOffice not found: install it from https://www.libreoffice.org/ (or put soffice on the PATH).")


def recalculate(files: list[Path], out: Path) -> None:
    profile = out / "profile"
    (profile / "user").mkdir(parents=True)
    (profile / "user" / "registrymodifications.xcu").write_text(RECALC_ALWAYS)
    subprocess.run([soffice(), f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "xlsx",
                    "--outdir", str(out), *map(str, files)], check=True, capture_output=True)


def lines_of(text: str) -> list[str]:
    return [text[i:i + B.LINE_WIDTH] for i in range(0, len(text), B.LINE_WIDTH)]


def expected(slug: str) -> list[str]:
    """Strings that must appear among the front tab's computed values."""
    if slug == "letter-counts":
        ct = B.only_letters(B.substitute(B.LIGHTHOUSE, B.LIGHTHOUSE_KEY))
        ioc = sum(ct.count(c) * (ct.count(c) - 1) for c in B.ALPHABET) / (len(ct) * (len(ct) - 1))
        return [f"ioc={ioc:.3f}", "One alphabet, disguised"]
    if slug == "caesar":
        return [f"best={B.CAESAR_SHIFT}", lines_of(B.BAKER.lower())[0]]
    if slug == "affine":
        a, b = B.AFFINE_KEY
        return [lines_of(B.MUSEUM.lower())[0], f"a = {a}, b = {b}."]
    if slug == "substitution":
        known = {B.CLUB_KEY[B.ALPHABET.index(p.upper())] for p in B.CLUB_SOLVED}
        ct = B.substitute(B.CLUB, B.CLUB_KEY)
        partial = "".join(c.lower() if c in known else c for c in B.CLUB.upper())
        partial = "".join(p if (not ch.isalpha() or ch in known) else B.PLACEHOLDER
                          for p, ch in zip(partial.lower(), ct))
        return [lines_of(partial)[0]]
    if slug == "vigenere-slices":
        return [B.PROBE_KEY, lines_of(B.only_letters(B.PROBE).lower())[0]]
    if slug == "repeats-and-factors":
        return [f"found_best={len(B.TREASURE_KEY)}", f"typed_best={len(B.TREASURE_KEY)}"]
    if slug == "columnar":
        plain = B.only_letters(B.GATE)
        return [lines_of(plain + B.PAD_LETTER * (-len(plain) % len(B.GATE_KEYWORD)))[0], "OK: each number"]
    if slug == "digraphs":
        return ["Could be Playfair", "Could be 2x2 Hill"]
    if slug == "hill":
        return [lines_of(B.only_letters(B.APPLES).lower())[0]]
    raise KeyError(slug)


def values(ws) -> list[str]:
    return [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]


def labelled(ws, label: str):
    """The value in column C beside a label in column B."""
    for row in ws.iter_rows(min_col=2, max_col=3):
        if row[0].value == label:
            return row[1].value
    return None


def facts(slug: str, ws) -> list[str]:
    """Extra computed facts, as strings, for the checks above."""
    if slug == "letter-counts":
        return [f"ioc={labelled(ws, 'Index of coincidence (IoC)'):.3f}"]
    if slug == "caesar":
        return [f"best={labelled(ws, 'Lowest chi-squared at shift')}"]
    if slug == "repeats-and-factors":
        return [f"found_best={labelled(ws, B.BEST_GUESS_FOUND)}", f"typed_best={labelled(ws, B.BEST_GUESS_YOURS)}"]
    return []


def check(spec, computed: Path) -> list[str]:
    wb = load_workbook(computed, data_only=True)
    front = wb.worksheets[0]
    seen = values(front) + facts(spec.slug, front)
    problems = [f"missing {want!r}" for want in expected(spec.slug) if not any(want in v for v in seen)]
    for ws in wb.worksheets:
        bad = [c.coordinate for row in ws.iter_rows() for c in row
               if isinstance(c.value, str) and c.value.startswith(ERRORS)]
        if bad:
            problems.append(f"{ws.title}: errors in {', '.join(bad[:8])}{' ...' if len(bad) > 8 else ''}")
    return problems


def main(only: list[str]) -> int:
    specs = [s for s in B.SHEETS if not only or s.slug in only or f"{s.num:02d}" in only]
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        recalculate([HERE / s.file for s in specs], out)
        for s in specs:
            problems = check(s, out / s.file)
            failures += bool(problems)
            print(f"{'FAIL' if problems else 'ok  '} {s.file}" + "".join(f"\n     {p}" for p in problems))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
