# SPDX-License-Identifier: MIT
"""Build the Python lessons: check every snippet under CPython, then write the app's data and the notebooks.

The lessons teach the plain Python a student needs to write their own codebreaking tools. Each
lesson is one TOML file in ``python/lessons/`` in the PRIMM shape (Predict, Run, Investigate,
Modify, Make); the practice texts are ``python/texts.toml``. This script is the only thing that
reads them, and it writes:

- ``python/lessons.json``: every lesson with its texts filled in, which the cryptology app syncs
  at a pinned commit (its ``scripts/sync-guides.mjs``) and shows as fiddles;
- ``python/notebooks/NN-<id>.ipynb``: the same lesson as a notebook, opened in Google Colab from
  the app's "Open in Colab" link.

Before writing anything it checks, by running them:

- every snippet runs without an error, and the lessons use built-ins only (no ``import``) except
  in a lesson marked ``imports = true``;
- each Predict's right choice is exactly what its code prints, and no other choice is;
- each Modify and Make solution passes its check, and each starter does not (so the task is real).

Usage::

    python python/scripts/build_python.py           # check, then write
    python python/scripts/build_python.py --check   # check, and fail if the written files are stale
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


def load_texts(path: Path = ROOT / "texts.toml") -> dict[str, dict]:
    """Every text's ciphertext and plaintext, ready to be put into a lesson."""
    out = {}
    for name, spec in tomllib.loads(path.read_text()).items():
        cipher, key, plain = spec["cipher"], spec["key"], spec["plaintext"]
        ct = encipher(plain, cipher, key)
        transposition = cipher in ("block", "columnar")
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


def app_data(lessons: list[dict], texts: dict[str, dict]) -> dict:
    """What the app reads: the lessons, each with its Colab link."""
    keep = ("id", "number", "title", "job", "learn", "intro", "bonus", *STEPS)
    return {
        "texts": {k: {"title": v["title"], "cipher": v["cipher"]} for k, v in texts.items()},
        "lessons": [{**{k: l[k] for k in keep if k in l}, "colab": COLAB + notebook_name(l)} for l in lessons],
    }


def outputs(lessons: list[dict], texts: dict[str, dict]) -> dict[Path, str]:
    files = {ROOT / "lessons.json": json.dumps(app_data(lessons, texts), indent=1, ensure_ascii=False) + "\n"}
    for l in lessons:
        files[ROOT / "notebooks" / notebook_name(l)] = json.dumps(notebook(l), indent=1, ensure_ascii=False) + "\n"
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="check only, and fail if the written files are out of date")
    args = ap.parse_args(argv)
    texts = load_texts()
    lessons = load_lessons(texts)
    ids = [l["id"] for l in lessons]
    problems = [f"duplicate lesson id {i}" for i in set(ids) if ids.count(i) > 1]
    for l in lessons:
        problems += check_lesson(l)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    files = outputs(lessons, texts)
    if args.check:
        stale = [str(p.relative_to(ROOT.parent)) for p, s in files.items() if not p.exists() or p.read_text() != s]
        written = set(files)
        extra = [str(p.relative_to(ROOT.parent)) for p in (ROOT / "notebooks").glob("*.ipynb") if p not in written]
        if stale or extra:
            print("Out of date (run build_python.py): " + ", ".join(stale + extra), file=sys.stderr)
            return 1
        print(f"{len(lessons)} lessons checked; files up to date.")
        return 0
    (ROOT / "notebooks").mkdir(exist_ok=True)
    for p in (ROOT / "notebooks").glob("*.ipynb"):
        if p not in files:
            p.unlink()
    for p, s in files.items():
        p.write_text(s)
    print(f"{len(lessons)} lessons checked; wrote lessons.json and {len(lessons)} notebooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
