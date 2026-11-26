# SPDX-License-Identifier: MIT
"""Build the Python lessons: check every snippet under CPython, then write the app's data and the notebooks.

The lessons teach the plain Python a student needs to write their own codebreaking tools. Each
lesson is one TOML file in ``python/lessons/`` in the PRIMM shape (Predict, Run, Investigate,
Modify, Make); the practice texts are ``python/texts.toml``. This script is the only thing that
reads them, and it writes:

- ``python/lessons.json``: every lesson with its texts filled in, and the concept explainers of
  ``python/concepts.toml``, which the cryptology app syncs at a pinned commit (its
  ``scripts/sync-guides.mjs``) and shows as fiddles;
- ``python/notebooks/NN-<id>.ipynb``: the same lesson as a notebook, opened in Google Colab from
  the app's "Open in Colab" link;
- ``python/notebooks/<id>.ipynb``: each workbook of ``python/workbooks/``, a longer notebook in
  short, foldable chapters, each with a few examples and a playground cell, whose functions build
  on each other up to a whole tool (counting, cracking a cipher). Workbooks may import from the
  standard library.

Before writing anything it checks, by running them:

- every snippet runs without an error, and the lessons use built-ins only (no ``import``) except
  in a lesson marked ``imports = true``;
- each Predict's right choice is exactly what its code prints, and no other choice is;
- each Modify and Make solution passes its check, and each starter does not (so the task is real);
- each concept explainer names a lesson that exists;
- every cell of every workbook runs, in order, in one namespace (a cell's ``stand_in`` runs in
  its place: the cell that fetches a live challenge text, say), the workbook imports nothing
  outside the standard library, and its hidden ``check`` passes after the last cell.

Usage::

    python python/scripts/build_python.py           # check, then write
    python python/scripts/build_python.py --check   # check, and fail if the written files are stale
    python python/scripts/build_python.py --workbooks DIR --out DIR   # check and build workbooks kept elsewhere
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "thorwhalen/cryptology"
BRANCH = "main"
APP_URL = "https://apps.thorwhalen.com/cryptology/"
COLAB = f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/python/notebooks/"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
WRAP = 50
RUN_TIMEOUT_S = 20
WORKBOOK_TIMEOUT_S = 600
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
STEPS = ("predict", "run", "investigate", "modify", "make")


# --- the practice texts -------------------------------------------------------------------------


def _letters(s: str) -> str:
    return "".join(c for c in s.upper() if c.isalpha())


def _keyed_alphabet(keyword: str) -> str:
    seen: list[str] = []
    for c in keyword.upper() + ALPHABET:
        if c.isalpha() and c not in seen:
            seen.append(c)
    return "".join(seen)


def _map_letters(text: str, fn) -> str:
    return "".join(fn(i, c) if c.isalpha() else c for i, c in enumerate(text))


def encipher(plaintext: str, cipher: str, key) -> str:
    """The ciphertext of ``plaintext``. Caesar, substitution and Vigenère keep spaces and punctuation;
    the transpositions work on the letters alone."""
    p = plaintext.upper()
    if cipher == "caesar":
        return _map_letters(p, lambda _, c: chr((ord(c) - 65 + key) % 26 + 65))
    if cipher == "substitution":
        table = str.maketrans(ALPHABET, _keyed_alphabet(key))
        return p.translate(table)
    if cipher == "vigenere":
        shifts = [ord(k) - 65 for k in key.upper()]
        out, n = [], 0
        for c in p:
            if c.isalpha():
                out.append(chr((ord(c) - 65 + shifts[n % len(shifts)]) % 26 + 65))
                n += 1
            else:
                out.append(c)
        return "".join(out)
    t = _letters(p)
    if cipher == "block":
        w = len(key)
        assert len(t) % w == 0, f"block text length {len(t)} is not a multiple of {w}"
        rows = []
        for i in range(0, len(t), w):
            row = [""] * w
            for j, k in enumerate(key):
                row[k] = t[i + j]
            rows.append("".join(row))
        return "".join(rows)
    if cipher == "columnar":
        assert len(t) % key == 0, f"columnar text length {len(t)} is not a multiple of {key}"
        return "".join(t[c::key] for c in range(key))
    raise ValueError(f"unknown cipher {cipher!r}")


def _wrap(text: str, *, groups: int = 0) -> str:
    if groups:
        text = " ".join(text[i : i + groups] for i in range(0, len(text), groups))
    return "\n".join(textwrap.wrap(text, WRAP))


def load_texts(path: Path = ROOT / "texts.toml", *, specs: dict | None = None) -> dict[str, dict]:
    """Every text's ciphertext and plaintext, ready to be put into a lesson.

    A text is a plaintext with a ``cipher`` and ``key``, enciphered here, or (for a cipher this
    script does not know) a plaintext with its ``ciphertext`` already made, and ``cipher`` naming it.
    ``specs`` gives the texts directly instead of reading ``path`` (a workbook's own texts).
    """
    out = {}
    for name, spec in (specs if specs is not None else tomllib.loads(path.read_text())).items():
        cipher, plain = spec["cipher"], spec["plaintext"]
        key = spec.get("key")
        ct = spec["ciphertext"].upper() if "ciphertext" in spec else encipher(plain, cipher, key)
        transposition = cipher in ("block", "columnar") or spec.get("transposition", False)
        out[name] = {
            "title": spec["title"],
            "cipher": cipher,
            "text": _wrap(ct, groups=5) if transposition else _wrap(ct),
            "plain": _letters(plain) if transposition else _wrap(plain.upper()),
        }
        if cipher == "substitution":
            out[name]["alphabet"] = _keyed_alphabet(key)
    return out


def _fill(value, values: dict[str, str]):
    """Put the texts into every string of a lesson ({{caesar}}, {{caesar_plain}}, ...)."""
    if isinstance(value, str):

        def sub(m):
            if m.group(1) not in values:
                raise KeyError(f"unknown placeholder {{{{{m.group(1)}}}}}")
            return values[m.group(1)]

        return PLACEHOLDER.sub(sub, value)
    if isinstance(value, list):
        return [_fill(v, values) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, values) for k, v in value.items()}
    return value


def _placeholders(texts: dict[str, dict]) -> dict[str, str]:
    values = {}
    for name, t in texts.items():
        values[name] = t["text"]
        values[f"{name}_plain"] = t["plain"]
        if "alphabet" in t:
            values[f"{name}_alphabet"] = t["alphabet"]
    return values


# --- the lessons --------------------------------------------------------------------------------


def load_lessons(texts: dict[str, dict]) -> list[dict]:
    values = _placeholders(texts)
    lessons = []
    for path in sorted((ROOT / "lessons").glob("*.toml")):
        raw = tomllib.loads(path.read_text())
        lesson = _fill(raw, values)
        lesson["source"] = path.name
        lessons.append(lesson)
    lessons.sort(key=lambda l: l["number"])
    return lessons


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=RUN_TIMEOUT_S)


def _imports(code: str) -> bool:
    return any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(ast.parse(code)))


def check_lesson(lesson: dict) -> list[str]:
    """Every problem with one lesson, as readable lines (empty when it is right)."""
    where = lesson["source"]
    problems: list[str] = []
    for field in ("id", "number", "title", "job", "learn", "intro", "run"):
        if field not in lesson:
            problems.append(f"{where}: missing {field}")
    if not re.fullmatch(r"[a-z0-9-]+", lesson.get("id", "")):
        problems.append(f"{where}: id must be lower-case words joined by hyphens")
    if problems:
        return problems

    def snippets():
        if "predict" in lesson:
            yield "predict", lesson["predict"]["code"]
        yield "run", lesson["run"]["code"]
        for step in ("modify", "make"):
            if step in lesson:
                yield f"{step} starter", lesson[step]["code"]
                yield f"{step} solution", lesson[step]["solution"]
                yield f"{step} check", lesson[step]["check"]

    for label, code in snippets():
        if _imports(code) and not lesson.get("imports"):
            problems.append(f"{where}: {label} imports a module; lessons use built-ins only")

    for label, code in [("run", lesson["run"]["code"])] + [(f"{s} solution", lesson[s]["solution"]) for s in ("modify", "make") if s in lesson]:
        r = _run(code)
        if r.returncode:
            problems.append(f"{where}: {label} raised:\n{r.stderr}")

    if "predict" in lesson:
        p = lesson["predict"]
        r = _run(p["code"])
        printed = r.stdout.rstrip("\n")
        right = p["choices"][p["answer"]]
        if r.returncode:
            problems.append(f"{where}: predict raised:\n{r.stderr}")
        elif printed != right:
            problems.append(f"{where}: predict prints {printed!r}, but the right choice says {right!r}")
        others = [c for i, c in enumerate(p["choices"]) if i != p["answer"]]
        if printed in others:
            problems.append(f"{where}: predict has a wrong choice equal to the output")
        if len(set(p["choices"])) != len(p["choices"]):
            problems.append(f"{where}: predict has two equal choices")

    for step in ("modify", "make"):
        if step not in lesson:
            continue
        s = lesson[step]
        r = _run(f"{s['solution']}\n{s['check']}")
        if r.returncode:
            problems.append(f"{where}: the {step} solution fails its check:\n{r.stderr}")
        r = _run(f"{s['code']}\n{s['check']}")
        if not r.returncode:
            problems.append(f"{where}: the {step} starter already passes its check")
    return problems


# --- the workbooks ------------------------------------------------------------------------------

CELL_KINDS = ("md", "code", "play")
PLAY_HEADER = "# Playground: change anything here and run it again. Nothing you do here can break the notebook.\n"
FOLD_TIP = (
    "**How to use it.** Run a cell with the ▶ button beside it, or Shift+Enter. Run the cells in order the "
    "first time: later chapters use the functions earlier ones made. Each chapter is a section: fold one "
    "you already know with the arrow beside its heading, or jump with the table of contents (the ☰ icon on the left). "
    "The cells marked *Playground* are yours: change them, break them, run them again."
)

# Runs a workbook's cells in order in one namespace, and names the cell that failed.
_RUNNER = """
import json, sys, traceback
cells = json.loads(sys.stdin.read())
ns = {"__name__": "__main__"}
for label, code in cells:
    try:
        exec(compile(code, label, "exec"), ns)
    except BaseException:
        print(f"{label} raised:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
"""


def load_workbooks(folder: Path = ROOT / "workbooks", *, texts: dict[str, dict] | None = None) -> list[dict]:
    """Every workbook in ``folder``, with the texts filled in: the shared ones and its own ``[texts]``."""
    texts = load_texts() if texts is None else texts
    books = []
    for path in sorted(folder.glob("*.toml")):
        raw = tomllib.loads(path.read_text())
        own = load_texts(specs=raw.pop("texts", {}))
        book = _fill(raw, _placeholders({**texts, **own}))
        book["source"] = path.name
        books.append(book)
    books.sort(key=lambda b: (b.get("order", 0), b.get("id", "")))
    return books


def _cells(book: dict):
    """Each cell as (chapter number, chapter title, cell)."""
    for n, chapter in enumerate(book.get("chapter", []), 1):
        for cell in chapter.get("cell", []):
            yield n, chapter["title"], cell


def check_workbook(book: dict) -> list[str]:
    """Every problem with one workbook, as readable lines (empty when it is right)."""
    where = book["source"]
    problems = [f"{where}: missing {f}" for f in ("id", "title", "summary", "intro", "chapter") if f not in book]
    problems += [f"{where}: chapter {c.get('title')!r} has unknown keys {sorted(set(c) - {'title', 'cell'})}" for c in book.get("chapter", []) if set(c) - {"title", "cell"}]
    if not re.fullmatch(r"[a-z0-9-]+", book.get("id", "")):
        problems.append(f"{where}: id must be lower-case words joined by hyphens")
    if problems:
        return problems
    run = []
    for i, (n, title, cell) in enumerate(_cells(book)):
        kinds = [k for k in CELL_KINDS if k in cell]
        unknown = set(cell) - set(CELL_KINDS) - {"stand_in"}
        if unknown:  # a key written after a [[chapter.cell]] header lands in that cell: a misplaced `check`, say
            problems.append(f"{where}: chapter {n} ({title}), cell {i}: unknown keys {sorted(unknown)} (top-level keys go before the first table)")
        if len(kinds) != 1:
            problems.append(f"{where}: chapter {n} ({title}), cell {i}: needs exactly one of {CELL_KINDS}")
            continue
        if kinds[0] == "md":
            continue
        code = cell.get("stand_in", cell[kinds[0]])
        try:
            imported = _imported(code) | _imported(cell[kinds[0]])
        except SyntaxError as e:
            problems.append(f"{where}: chapter {n} ({title}), cell {i}: {e}")
            continue
        for name in imported:
            if name not in sys.stdlib_module_names:
                problems.append(f"{where}: chapter {n} imports {name}, which is not in the standard library")
        run.append((f"{where}, chapter {n} ({title}), cell {i}", code))
    if book.get("check"):
        run.append((f"{where}: the hidden check", book["check"]))
    if problems:
        return problems
    r = subprocess.run([sys.executable, "-I", "-c", _RUNNER], input=json.dumps(run), capture_output=True, text=True, timeout=WORKBOOK_TIMEOUT_S)
    if r.returncode:
        problems.append(r.stderr.strip())
    return problems


def _imported(code: str) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def workbook_name(book: dict) -> str:
    return f"{book['id']}.ipynb"


def workbook_notebook(book: dict) -> dict:
    """The workbook as a notebook: a title, then one foldable section per chapter."""
    footer = book.get("footer", f"<small>From [{REPO}](https://github.com/{REPO}). Code: MIT. Text: CC BY 4.0.</small>")
    cells = [_md(f"# {book['title']}", "", f"*{book['summary']}*", "", book["intro"].strip(), "", FOLD_TIP, "",
                 "*Save a copy to your own Drive (File → Save a copy in Drive) to keep your work.*", "", footer)]
    for n, chapter in enumerate(book["chapter"], 1):
        cells.append(_md(f"## {n}. {chapter['title']}"))
        for cell in chapter.get("cell", []):
            if "md" in cell:
                cells.append(_md(cell["md"].strip()))
            elif "play" in cell:
                cells.append(_code(PLAY_HEADER + cell["play"]))
            else:
                cells.append(_code(cell["code"]))
    for i, cell in enumerate(cells):
        cell["id"] = f"{book['id']}-{i}"
    return {
        "cells": cells,
        "metadata": {
            "colab": {"name": workbook_name(book), "provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# --- the outputs --------------------------------------------------------------------------------


def notebook_name(lesson: dict) -> str:
    return f"{lesson['number']:02d}-{lesson['id']}.ipynb"


def _md(*lines: str) -> dict:
    text = "\n".join(lines)
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def _code(code: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": code.rstrip("\n").splitlines(keepends=True)}


def _fence(code: str) -> str:
    return f"```python\n{code.rstrip()}\n```"


def notebook(lesson: dict) -> dict:
    """The lesson as a notebook: the same steps, with the checks as cells the student runs."""
    n, title = lesson["number"], lesson["title"]
    app = f"{APP_URL}#/python/{lesson['id']}"
    cells = [
        _md(
            f"# {'Bonus' if lesson.get('bonus') else f'Lesson {n}'}: {title}",
            "",
            f"**The job:** {lesson['job']}",
            "",
            f"**New Python:** {', '.join(lesson['learn'])}.",
            "",
            lesson["intro"],
            "",
            f"*The same lesson, with code that runs in your browser, is in the [cryptology app]({app}). Save a copy of this notebook to your own Drive (File → Save a copy in Drive) to keep your work.*",
            "",
            f"<small>From [{REPO}](https://github.com/{REPO}). Code: MIT. Text: CC BY 4.0.</small>",
        )
    ]
    if "predict" in lesson:
        p = lesson["predict"]
        choices = "\n".join(f"{chr(65 + i)}. `{c!r}`" if "\n" not in c else f"{chr(65 + i)}.\n\n```\n{c}\n```" for i, c in enumerate(p["choices"]))
        cells += [
            _md("## 1. Predict", "", p["question"], "", _fence(p["code"]), "", choices, "", "Decide before you run it. Then run the cell below to see."),
            _code(p["code"]),
            _md(f"<details><summary>Why</summary>\n\n{p['explain']}\n\n</details>"),
        ]
    r = lesson["run"]
    cells += [_md("## 2. Run", "", r.get("note", "Run this cell and read what it prints.")), _code(r["code"])]
    if "investigate" in lesson:
        cells.append(_md("## 3. Investigate", "", "Change the code above and run it again:", "", *[f"- {q}" for q in lesson["investigate"]["prompts"]]))
    for number, step, heading in ((4, "modify", "Modify"), (5, "make", "Make")):
        if step not in lesson:
            continue
        s = lesson[step]
        cells += [
            _md(f"## {number}. {heading}", "", s["task"]),
            _code(s["code"]),
            _md("Run this cell to check your answer. It looks at the variables your code made."),
            _code(s["check"] + '\nprint("Check passed.")'),
        ]
        if s.get("hint"):
            cells.append(_md(f"<details><summary>A hint</summary>\n\n{s['hint']}\n\n</details>"))
        cells.append(_md(f"<details><summary>One way to do it</summary>\n\n{_fence(s['solution'])}\n\n</details>"))
    for i, cell in enumerate(cells):
        cell["id"] = f"{lesson['id']}-{i}"  # stable ids, so a rebuild changes nothing it need not
    return {
        "cells": cells,
        "metadata": {
            "colab": {"name": notebook_name(lesson), "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def load_concepts(path: Path = ROOT / "concepts.toml") -> list[dict]:
    """The concept explainers, in file order, each as ``{"id", "title", "summary", "lesson"}``."""
    return [{"id": k, **v} for k, v in tomllib.loads(path.read_text()).items()]


def check_concepts(concepts: list[dict], lessons: list[dict]) -> list[str]:
    ids = {l["id"] for l in lessons}
    fields = {"title", "summary", "lesson"}
    problems = [f"concept {c['id']}: needs exactly {sorted(fields)}" for c in concepts if set(c) - {"id"} != fields]
    return problems + [f"concept {c['id']}: no lesson {c.get('lesson')!r}" for c in concepts if c.get("lesson") not in ids]


def app_data(lessons: list[dict], texts: dict[str, dict], concepts: list[dict] = (), workbooks: list[dict] = ()) -> dict:
    """What the app reads: the lessons, each with its Colab link, the concept explainers, and the workbooks."""
    keep = ("id", "number", "title", "job", "learn", "intro", "bonus", *STEPS)
    return {
        "texts": {k: {"title": v["title"], "cipher": v["cipher"]} for k, v in texts.items()},
        "lessons": [{**{k: l[k] for k in keep if k in l}, "colab": COLAB + notebook_name(l)} for l in lessons],
        "concepts": list(concepts),
        "workbooks": [{**{k: b[k] for k in ("id", "title", "summary", "learn") if k in b}, "colab": COLAB + workbook_name(b)} for b in workbooks],
    }


def _json(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def outputs(lessons: list[dict], texts: dict[str, dict], concepts: list[dict] = (), workbooks: list[dict] = ()) -> dict[Path, str]:
    files = {ROOT / "lessons.json": _json(app_data(lessons, texts, concepts, workbooks))}
    for l in lessons:
        files[ROOT / "notebooks" / notebook_name(l)] = _json(notebook(l))
    for b in workbooks:
        files[ROOT / "notebooks" / workbook_name(b)] = _json(workbook_notebook(b))
    return files


def build_elsewhere(folder: Path, out: Path) -> int:
    """Check the workbooks in ``folder`` (kept outside this repo) and write their notebooks to ``out``."""
    books = load_workbooks(folder)
    problems = [p for b in books for p in check_workbook(b)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    for b in books:
        (out / workbook_name(b)).write_text(_json(workbook_notebook(b)))
    print(f"{len(books)} workbooks checked; wrote {', '.join(workbook_name(b) for b in books)} to {out}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="check only, and fail if the written files are out of date")
    ap.add_argument("--workbooks", type=Path, help="build only the workbooks in this folder (kept outside the repo), to --out")
    ap.add_argument("--out", type=Path, help="where --workbooks writes its notebooks")
    args = ap.parse_args(argv)
    if args.workbooks:
        if not args.out:
            ap.error("--workbooks needs --out")
        return build_elsewhere(args.workbooks, args.out)
    texts = load_texts()
    lessons = load_lessons(texts)
    ids = [l["id"] for l in lessons]
    problems = [f"duplicate lesson id {i}" for i in set(ids) if ids.count(i) > 1]
    for l in lessons:
        problems += check_lesson(l)
    concepts = load_concepts()
    problems += check_concepts(concepts, lessons)
    workbooks = load_workbooks(texts=texts)
    wids = [b.get("id") for b in workbooks] + ids
    problems += [f"duplicate id {i} (lessons and workbooks share the notebooks folder)" for i in set(wids) if wids.count(i) > 1]
    for b in workbooks:
        problems += check_workbook(b)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    files = outputs(lessons, texts, concepts, workbooks)
    if args.check:
        stale = [str(p.relative_to(ROOT.parent)) for p, s in files.items() if not p.exists() or p.read_text() != s]
        written = set(files)
        extra = [str(p.relative_to(ROOT.parent)) for p in (ROOT / "notebooks").glob("*.ipynb") if p not in written]
        if stale or extra:
            print("Out of date (run build_python.py): " + ", ".join(stale + extra), file=sys.stderr)
            return 1
        print(f"{len(lessons)} lessons and {len(workbooks)} workbooks checked; files up to date.")
        return 0
    (ROOT / "notebooks").mkdir(exist_ok=True)
    for p in (ROOT / "notebooks").glob("*.ipynb"):
        if p not in files:
            p.unlink()
    for p, s in files.items():
        p.write_text(s)
    print(f"{len(lessons)} lessons and {len(workbooks)} workbooks checked; wrote lessons.json and {len(lessons) + len(workbooks)} notebooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
