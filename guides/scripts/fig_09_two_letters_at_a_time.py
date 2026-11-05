"""Figures for Guide 09, Two letters at a time.

Writes figures/09-*.png. Re-run from anywhere: ``python scripts/fig_09_two_letters_at_a_time.py``.
Needs only matplotlib. Polybius, Playfair and Hill are implemented here so the guide's
numbers can be checked: the script prints every number it draws.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
WIDTH = 8.0  # inches: 8 x 200 dpi = 1600 px
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SQUARE_ALPHABET = "ABCDEFGHIKLMNOPQRSTUVWXYZ"  # no J

BLUE, ORANGE, GREEN, RED, PURPLE, GRAY = (
    "#1f77d0", "#ff8c1a", "#2ca02c", "#e0383e", "#8e44ad", "#7f8c8d",
)
LIGHT = {"blue": "#d6e9ff", "orange": "#ffe3c4", "green": "#d9f5d0", "red": "#ffd6d6",
         "purple": "#ead9ff", "gray": "#f0f0f0"}

plt.rcParams.update({
    "font.size": 15,
    "axes.titlesize": 19,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Commonest English digraphs, percent of all letter pairs (Peter Norvig's counts from the
# Google Books corpus, "English Letter Frequency Counts: Mayzner Revisited").
TOP_DIGRAPHS = [
    ("TH", 3.56), ("HE", 3.07), ("IN", 2.43), ("ER", 2.05), ("AN", 1.99), ("RE", 1.85),
    ("ON", 1.76), ("AT", 1.49), ("EN", 1.45), ("ND", 1.35), ("TI", 1.34), ("ES", 1.34),
]

PLAYFAIR_KEY = "LANTERN"
PLAYFAIR_PLAIN = "the balloon will rise at noon"
HILL_KEY = [[5, 8], [17, 3]]
HILL_PLAIN = "dear agent the papers are hidden inside the clock tower"
HILL_CRIB = "DEAR"

TELLS_TEXT = (
    "Every summer the travelling circus came to the village and set up its striped tent in "
    "the field behind the old mill. The children would climb the fence at dawn to watch the "
    "elephants being washed in the river, and the acrobats practising their jumps on the "
    "grass. One year a small brown dog followed the circus all the way from the next town, "
    "and by the end of the week it had learned to walk the tightrope better than anyone."
)


def letters(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalpha())


def square_from(keyword: str) -> str:
    seen = dict.fromkeys(letters(keyword).replace("J", "I"))
    return "".join(seen) + "".join(c for c in SQUARE_ALPHABET if c not in seen)


def playfair_pairs(text: str) -> list[str]:
    """Split into pairs, putting X between a doubled letter and at the end if odd."""
    text = letters(text).replace("J", "I")
    pairs, i = [], 0
    while i < len(text):
        a = text[i]
        b = text[i + 1] if i + 1 < len(text) else "X"
        if a == b:
            pairs.append(a + "X")
            i += 1
        else:
            pairs.append(a + b)
            i += 2
    return pairs


def playfair_pair(pair: str, square: str) -> tuple[str, str]:
    """Encrypt one pair; also say which rule applied."""
    ra, ca = divmod(square.index(pair[0]), 5)
    rb, cb = divmod(square.index(pair[1]), 5)
    if ra == rb:
        return square[ra * 5 + (ca + 1) % 5] + square[rb * 5 + (cb + 1) % 5], "row"
    if ca == cb:
        return square[(ra + 1) % 5 * 5 + ca] + square[(rb + 1) % 5 * 5 + cb], "column"
    return square[ra * 5 + cb] + square[rb * 5 + ca], "rectangle"


def playfair_encrypt(text: str, keyword: str) -> str:
    square = square_from(keyword)
    return "".join(playfair_pair(p, square)[0] for p in playfair_pairs(text))


def hill_encrypt(text: str, key) -> str:
    values = [ord(c) - 65 for c in letters(text)]
    if len(values) % 2:
        values.append(ord("X") - 65)
    out = []
    for i in range(0, len(values), 2):
        p1, p2 = values[i], values[i + 1]
        out += [(key[0][0] * p1 + key[0][1] * p2) % 26, (key[1][0] * p1 + key[1][1] * p2) % 26]
    return "".join(ALPHABET[v] for v in out)


def ioc(text: str) -> float:
    counts = Counter(text)
    n = len(text)
    return sum(f * (f - 1) for f in counts.values()) / (n * (n - 1))


def doubled_pairs(text: str) -> int:
    return sum(text[i] == text[i + 1] for i in range(0, len(text) - 1, 2))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def draw_square(ax, square: str, x0: float, y0: float, *, fills=None, edges=None, cell=1.0,
                fontsize=20, coords=False):
    fills = fills or {}
    edges = edges or {}
    for i, ch in enumerate(square):
        r, c = divmod(i, 5)
        ax.add_patch(Rectangle((x0 + c * cell, y0 - (r + 1) * cell), cell, cell,
                               fc=fills.get(ch, "white"), ec=edges.get(ch, "#999999"),
                               lw=4 if ch in edges else 1.5, zorder=2 if ch in edges else 1))
        ax.text(x0 + (c + 0.5) * cell, y0 - (r + 0.5) * cell, ch, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", family="monospace", zorder=3)
    if coords:
        for k in range(5):
            ax.text(x0 + (k + 0.5) * cell, y0 + 0.45 * cell, str(k + 1), ha="center",
                    va="center", fontsize=fontsize - 2, color=BLUE, fontweight="bold")
            ax.text(x0 - 0.45 * cell, y0 - (k + 0.5) * cell, str(k + 1), ha="center",
                    va="center", fontsize=fontsize - 2, color=RED, fontweight="bold")


# --- Figures ----------------------------------------------------------------------------


def fig_polybius() -> None:
    square = SQUARE_ALPHABET
    word = "HELLO"
    codes = []
    for ch in word:
        r, c = divmod(square.index(ch), 5)
        codes.append(f"{r + 1}{c + 1}")
    print("Polybius HELLO ->", " ".join(codes))
    fig, ax = plt.subplots(figsize=(WIDTH * 1.2, 5.6))
    fills = {"H": LIGHT["orange"], "E": LIGHT["green"], "L": LIGHT["blue"], "O": LIGHT["purple"]}
    draw_square(ax, square, 0.6, 5, fills=fills, coords=True)
    ax.text(0.15, 5.95, "row", color=RED, fontsize=14, ha="center")
    ax.text(3.1, 6.0, "column", color=BLUE, fontsize=14, ha="center")
    ax.text(6.6, 3.9, "H E L L O", fontsize=24, fontweight="bold", family="monospace")
    ax.text(6.6, 2.6, " ".join(codes), fontsize=24, fontweight="bold", family="monospace",
            color=PURPLE)
    ax.text(6.6, 1.5, "each letter = row, then column", fontsize=15, color=GRAY)
    ax.text(6.6, 0.8, "(I and J share a square)", fontsize=15, color=GRAY)
    ax.annotate("", xy=(6.95, 2.95), xytext=(6.95, 3.6),
                arrowprops=dict(arrowstyle="->", lw=2.5, color=GRAY))
    ax.set_xlim(-0.4, 12.5)
    ax.set_ylim(-0.3, 6.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("The Polybius square: letters become pairs of digits", fontsize=20,
                 fontweight="bold")
    save(fig, "09-polybius.png")


def fig_playfair_rules() -> None:
    square = square_from(PLAYFAIR_KEY)
    print("Playfair square:", [square[i:i + 5] for i in range(0, 25, 5)])
    examples = [("TH", "Rectangle: swap\nto the other corners"),
                ("AL", "Same row:\neach takes the letter\nto its right"),
                ("LO", "Same column:\neach takes the letter\nbelow it")]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH * 1.5, 5.4))
    for ax, (pair, title) in zip(axes, examples):
        out, rule = playfair_pair(pair, square)
        print(f"Playfair {pair} -> {out} ({rule})")
        fills = {pair[0]: LIGHT["blue"], pair[1]: LIGHT["blue"],
                 out[0]: LIGHT["orange"], out[1]: LIGHT["orange"]}
        edges = {pair[0]: BLUE, pair[1]: BLUE, out[0]: ORANGE, out[1]: ORANGE}
        draw_square(ax, square, 0, 5, fills=fills, edges=edges, fontsize=19)
        if rule == "rectangle":
            ra, ca = divmod(square.index(pair[0]), 5)
            rb, cb = divmod(square.index(pair[1]), 5)
            x, y = min(ca, cb), 5 - max(ra, rb) - 1
            ax.add_patch(Rectangle((x + 0.08, y + 0.08), abs(ca - cb) + 0.84,
                                   abs(ra - rb) + 0.84, fc="none", ec=PURPLE, lw=3,
                                   ls="--", zorder=4))
        ax.text(2.5, -0.55, f"{pair}  →  {out}", ha="center", va="top", fontsize=22,
                fontweight="bold", family="monospace")
        ax.set_title(title, fontsize=15, fontweight="bold", pad=10)
        ax.set_xlim(-0.2, 5.2)
        ax.set_ylim(-1.6, 5.2)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle(f"Playfair's three rules (keyword {PLAYFAIR_KEY})", fontsize=20,
                 fontweight="bold", y=1.03)
    fig.text(0.5, -0.03, "blue = plaintext pair     orange = ciphertext pair", ha="center",
             fontsize=15, color=GRAY)
    save(fig, "09-playfair-rules.png")
    pairs = playfair_pairs(PLAYFAIR_PLAIN)
    print("Playfair pairs:", pairs)
    print("Playfair ciphertext:", playfair_encrypt(PLAYFAIR_PLAIN, PLAYFAIR_KEY))


def fig_digraphs() -> None:
    fig, ax = plt.subplots(figsize=(WIDTH * 1.2, 5.4))
    names = [d for d, _ in TOP_DIGRAPHS]
    values = [v for _, v in TOP_DIGRAPHS]
    colors = [BLUE if i % 2 == 0 else ORANGE for i in range(len(names))]
    ax.bar(range(len(names)), values, color=colors, width=0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=16, family="monospace", fontweight="bold")
    for i, v in enumerate(values):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center", va="bottom", fontsize=13)
    ax.set_ylabel("% of all letter pairs")
    ax.set_ylim(0, 4.2)
    ax.text(len(names) - 1, 3.7, "if every pair were equally likely:\n1 in 676 = 0.15%",
            ha="right", va="top", fontsize=14, color=GRAY)
    ax.axhline(100 / 676, color=GRAY, ls="--", lw=1.5)
    ax.set_title("The commonest pairs of letters in English", fontsize=20, fontweight="bold")
    save(fig, "09-digraphs.png")


def fig_tells() -> None:
    """The same paragraph as plain English, Playfair and Hill: the measurable tells."""
    plain = letters(TELLS_TEXT)
    if len(plain) % 2:
        plain += "X"
    play = playfair_encrypt(plain, PLAYFAIR_KEY)
    hill = hill_encrypt(plain, HILL_KEY)
    rows = []
    for name, text in (("English", plain), ("Playfair", play), ("Hill", hill)):
        stats = {
            "letters": len(text),
            "even?": "yes" if len(text) % 2 == 0 else "no",
            "doubled pairs": doubled_pairs(text),
            "J count": text.count("J"),
            "different letters": len(set(text)),
            "IoC": f"{ioc(text):.3f}",
        }
        rows.append((name, stats))
        print("tells", name, stats)
    headers = ["letters", "even?", "doubled pairs", "J count", "different letters", "IoC"]
    fig, ax = plt.subplots(figsize=(WIDTH * 1.3, 4.2))
    ax.axis("off")
    col_x = [0.0, 0.17, 0.30, 0.43, 0.6, 0.74, 0.9]
    ax.text(col_x[0], 0.9, "", transform=ax.transAxes)
    for j, h in enumerate(headers):
        ax.text(col_x[j + 1] + 0.05, 0.86, h.replace(" ", "\n"), ha="center", va="center",
                fontsize=14, fontweight="bold", color=GRAY, transform=ax.transAxes)
    row_colors = [LIGHT["gray"], LIGHT["blue"], LIGHT["orange"]]
    highlight = {("Playfair", "doubled pairs"), ("Playfair", "J count"),
                 ("Playfair", "different letters"), ("Hill", "IoC")}
    for i, (name, stats) in enumerate(rows):
        y = 0.6 - i * 0.24
        ax.add_patch(Rectangle((-0.02, y - 0.1), 1.02, 0.2, fc=row_colors[i], ec="none",
                               transform=ax.transAxes))
        ax.text(col_x[0], y, name, fontsize=17, fontweight="bold", va="center",
                transform=ax.transAxes)
        for j, h in enumerate(headers):
            bold = (name, h) in highlight
            ax.text(col_x[j + 1] + 0.05, y, str(stats[h]), ha="center", va="center",
                    fontsize=18 if bold else 16, fontweight="bold" if bold else "normal",
                    color=RED if bold else "black", transform=ax.transAxes)
    ax.set_title("The same paragraph three ways: what you can count", fontsize=19,
                 fontweight="bold")
    save(fig, "09-tells.png")


def fig_matrix_multiply() -> None:
    """Rows times columns: [[5, 8], [17, 3]] times (3, 4) = (47, 63) -> (21, 11) = VL."""
    (a, b), (c, d) = HILL_KEY
    p1, p2 = 3, 4  # D, E
    top, bottom = a * p1 + b * p2, c * p1 + d * p2
    print(f"matrix: {a}*{p1}+{b}*{p2}={top} -> {top % 26}; {c}*{p1}+{d}*{p2}={bottom} -> "
          f"{bottom % 26}")
    fig, ax = plt.subplots(figsize=(WIDTH * 1.3, 5.6))
    ax.axis("off")

    def bracket(x, y, h, left=True):
        s = 1 if left else -1
        ax.plot([x + 0.2 * s, x, x, x + 0.2 * s], [y, y, y - h, y - h], color="black", lw=2.5)

    # Matrix
    bracket(0.0, 3.2, 2.0)
    bracket(2.4, 3.2, 2.0, left=False)
    for (r, c_), v in {(0, 0): a, (0, 1): b, (1, 0): c, (1, 1): d}.items():
        color = BLUE if r == 0 else ORANGE
        ax.add_patch(Rectangle((0.15 + c_ * 1.1, 2.3 - r * 1.0), 1.0, 0.85,
                               fc=LIGHT["blue"] if r == 0 else LIGHT["orange"], ec="none"))
        ax.text(0.65 + c_ * 1.1, 2.72 - r * 1.0, str(v), ha="center", va="center",
                fontsize=24, fontweight="bold", color=color)
    ax.text(1.2, 3.55, "key", ha="center", fontsize=15, color=GRAY)
    # Vector
    bracket(3.0, 3.2, 2.0)
    bracket(4.2, 3.2, 2.0, left=False)
    ax.add_patch(Rectangle((3.15, 1.3), 0.9, 1.85, fc=LIGHT["green"], ec="none"))
    ax.text(3.6, 2.72, f"{p1}", ha="center", va="center", fontsize=24, fontweight="bold",
            color=GREEN)
    ax.text(3.6, 1.72, f"{p2}", ha="center", va="center", fontsize=24, fontweight="bold",
            color=GREEN)
    ax.text(3.6, 3.55, "D E", ha="center", fontsize=15, color=GRAY)
    ax.text(4.75, 2.2, "=", ha="center", va="center", fontsize=28, fontweight="bold")
    # Results
    ax.text(5.3, 2.72, f"{a}×{p1} + {b}×{p2} = {top}", va="center", fontsize=20, color=BLUE,
            fontweight="bold")
    ax.text(5.3, 1.72, f"{c}×{p1} + {d}×{p2} = {bottom}", va="center", fontsize=20,
            color=ORANGE, fontweight="bold")
    ax.text(10.5, 2.72, f"→ {top % 26} = {ALPHABET[top % 26]}", va="center", fontsize=20,
            fontweight="bold")
    ax.text(10.5, 1.72, f"→ {bottom % 26} = {ALPHABET[bottom % 26]}", va="center",
            fontsize=20, fontweight="bold")
    ax.text(10.5, 3.55, "remainder after ÷ 26", fontsize=14, color=GRAY)
    ax.text(0.0, 0.55, "Each ROW of the key times the COLUMN of letters:", fontsize=16)
    ax.text(0.0, -0.05, "multiply matching numbers, then add.", fontsize=16)
    ax.set_xlim(-0.3, 14.5)
    ax.set_ylim(-0.5, 4.1)
    ax.set_title("Hill cipher: rows times columns", fontsize=20, fontweight="bold")
    save(fig, "09-matrix-multiply.png")


def fig_clock() -> None:
    """A 26-hour clock: 47 goes once round and lands on 21 (V)."""
    import math

    fig, ax = plt.subplots(figsize=(WIDTH, WIDTH))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 1.0, fc="#fbfbfb", ec="black", lw=2))
    for k in range(26):
        angle = math.pi / 2 - 2 * math.pi * k / 26
        x, y = math.cos(angle), math.sin(angle)
        hot = k == 21
        ax.text(0.86 * x, 0.86 * y, str(k), ha="center", va="center",
                fontsize=17 if hot else 14, fontweight="bold",
                color=RED if hot else "black")
        ax.text(1.12 * x, 1.12 * y, ALPHABET[k], ha="center", va="center",
                fontsize=17 if hot else 15, fontweight="bold",
                color=RED if hot else BLUE, family="monospace")
        ax.plot([0.95 * x, x], [0.95 * y, y], color="black", lw=1.5)
    angle = math.pi / 2 - 2 * math.pi * 21 / 26
    ax.annotate("", xy=(0.7 * math.cos(angle), 0.7 * math.sin(angle)), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", lw=4, color=RED))
    ax.text(0, -0.2, "47 = 26 + 21", ha="center", fontsize=20, fontweight="bold")
    ax.text(0, -0.36, "once round, then 21 more", ha="center", fontsize=15, color=GRAY)
    ax.text(0, 0.25, r"47 $\equiv$ 21 (mod 26)", ha="center", fontsize=20, fontweight="bold",
            color=RED)
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.35)
    ax.set_title("Clock arithmetic with 26 hours, one per letter", fontsize=20,
                 fontweight="bold")
    save(fig, "09-mod26-clock.png")


def fig_hill_crib() -> None:
    """Solve for the key from the crib DEAR -> VLGZ, with all four equations."""
    cipher = hill_encrypt(HILL_PLAIN, HILL_KEY)
    print("Hill ciphertext:", cipher)
    crib = [ord(ch) - 65 for ch in HILL_CRIB]
    got = [ord(ch) - 65 for ch in cipher[:4]]
    (a, b), (c, d) = HILL_KEY
    # Check the solving steps the guide shows.
    b_found = next(x for x in range(26) if crib[3] * x % 26 == got[2])
    a_found = next(x for x in range(26) if (crib[0] * x + crib[1] * b_found) % 26 == got[0])
    d_found = next(x for x in range(26) if crib[3] * x % 26 == got[3])
    c_found = next(x for x in range(26) if (crib[0] * x + crib[1] * d_found) % 26 == got[1])
    assert (a_found, b_found, c_found, d_found) == (a, b, c, d)
    print("crib values", crib, "cipher values", got, "solved", a_found, b_found, c_found, d_found)

    fig, ax = plt.subplots(figsize=(WIDTH * 1.35, 6.6))
    ax.axis("off")
    ax.text(0, 6.2, f"Crib:  D E  A R   →   {cipher[0]} {cipher[1]}  {cipher[2]} {cipher[3]}",
            fontsize=21, fontweight="bold", family="monospace")
    ax.text(0, 5.5, f"Numbers:  ({crib[0]}, {crib[1]}) → ({got[0]}, {got[1]})      "
            f"({crib[2]}, {crib[3]}) → ({got[2]}, {got[3]})", fontsize=18, family="monospace")
    ax.add_patch(Rectangle((-0.1, 2.2), 6.6, 2.8, fc=LIGHT["blue"], ec="none"))
    ax.add_patch(Rectangle((6.8, 2.2), 6.6, 2.8, fc=LIGHT["orange"], ec="none"))
    ax.text(0.1, 4.6, "Top row  (a, b):", fontsize=17, fontweight="bold", color=BLUE)
    ax.text(0.1, 3.9, f"{crib[0]}a + {crib[1]}b ≡ {got[0]}", fontsize=19, family="monospace")
    ax.text(0.1, 3.2, f"{crib[2]}a + {crib[3]}b ≡ {got[2]}", fontsize=19, family="monospace")
    ax.text(0.1, 2.5, f"so b = {b_found}, then a = {a_found}", fontsize=18, fontweight="bold",
            color=BLUE)
    ax.text(7.0, 4.6, "Bottom row  (c, d):", fontsize=17, fontweight="bold", color="#b35900")
    ax.text(7.0, 3.9, f"{crib[0]}c + {crib[1]}d ≡ {got[1]}", fontsize=19, family="monospace")
    ax.text(7.0, 3.2, f"{crib[2]}c + {crib[3]}d ≡ {got[3]}", fontsize=19, family="monospace")
    ax.text(7.0, 2.5, f"so d = {d_found}, then c = {c_found}", fontsize=18, fontweight="bold",
            color="#b35900")
    ax.text(0, 1.3, f"Key found:   a = {a}   b = {b}   c = {c}   d = {d}", fontsize=20,
            fontweight="bold", color=PURPLE)
    ax.text(0, 0.5, "Because A = 0, the second equation in each box has only one unknown.",
            fontsize=15, color=GRAY)
    ax.set_xlim(-0.3, 13.6)
    ax.set_ylim(0.1, 6.8)
    ax.set_title("Breaking Hill with a four-letter crib", fontsize=20, fontweight="bold")
    save(fig, "09-hill-crib.png")


def main() -> None:
    fig_polybius()
    fig_playfair_rules()
    fig_digraphs()
    fig_tells()
    fig_matrix_multiply()
    fig_clock()
    fig_hill_crib()


if __name__ == "__main__":
    main()
