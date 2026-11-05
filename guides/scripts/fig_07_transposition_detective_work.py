"""Figures for Guide 07, Transposition detective work.

Writes figures/07-*.png. Re-run from anywhere:
``python scripts/fig_07_transposition_detective_work.py``. Needs only matplotlib.
The ciphers are implemented here, so the figures and the guide's numbers can be checked.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
WIDTH = 8.0  # inches: 8 x 200 dpi = 1600 px
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

BLUE, ORANGE, GREEN, RED, PURPLE, GRAY = (
    "#1f77d0", "#ff8c1a", "#2ca02c", "#e0383e", "#8e44ad", "#7f8c8d",
)
COLUMN_COLORS = ["#ffd6d6", "#d6e9ff", "#d9f5d0", "#fff0c2", "#ead9ff", "#c9f1ef"]
RAIL_COLORS = [RED, BLUE, GREEN, PURPLE]

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

# Standard published English letter frequencies (percent), A to Z.
ENGLISH_PERCENT = [
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4,
    6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074,
]

PARAGRAPH = (
    "On the first morning of the holidays the twins found a narrow wooden door behind the "
    "bookcase in their grandmother's attic. It was locked, but the key was hanging on a nail "
    "just above it, as if someone wanted it to be found. Behind the door a steep staircase "
    "went down into the dark, and from somewhere far below came the sound of running water."
)
PARAGRAPH_KEY = "BEAST"
SUBSTITUTION_ALPHABET = "MNBVCXZLKJHGFDSAPOIUYTREWQ"  # plain A->M, B->N, ...

WORKED_PLAIN = "meetthequeenatthebridgeatnoonbringthemap"
WORKED_KEY = "TIGER"
RAIL_PLAIN = "theowlfliesatmidnight"
RAILS = 3


def letters(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalpha())


def key_order(key: str) -> list[int]:
    """Alphabetical rank of each key letter (ties left to right): TIGER -> 4 2 1 0 3."""
    ranked = sorted(range(len(key)), key=lambda i: (key[i], i))
    order = [0] * len(key)
    for rank, i in enumerate(ranked):
        order[i] = rank
    return order


def columnar_encrypt(text: str, key: str) -> str:
    order, text = key_order(key), letters(text)
    width = len(order)
    return "".join(text[order.index(r)::width] for r in range(width))


def rail_pattern(n: int, rails: int) -> list[int]:
    cycle = list(range(rails)) + list(range(rails - 2, 0, -1))
    return [cycle[i % len(cycle)] for i in range(n)]


def railfence_encrypt(text: str, rails: int) -> str:
    text = letters(text)
    pattern = rail_pattern(len(text), rails)
    return "".join(c for r in range(rails) for c, p in zip(text, pattern) if p == r)


def ioc(text: str) -> float:
    counts = Counter(text)
    n = len(text)
    return sum(f * (f - 1) for f in counts.values()) / (n * (n - 1))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def fig_frequencies() -> None:
    """A transposition keeps English's letter counts; a substitution shuffles them."""
    plain = letters(PARAGRAPH)
    trans = columnar_encrypt(plain, PARAGRAPH_KEY)
    subst = "".join(SUBSTITUTION_ALPHABET[ord(c) - 65] for c in plain)
    n = len(plain)
    print(f"paragraph: {n} letters; IoC plain {ioc(plain):.4f}, transposed {ioc(trans):.4f}, "
          f"substituted {ioc(subst):.4f}")
    print("transposed starts:", trans[:40])
    print("substituted starts:", subst[:40])
    fig, axes = plt.subplots(2, 1, figsize=(WIDTH * 1.2, 8.4), sharey=True)
    xs = range(26)
    for ax, text, color, title in (
        (axes[0], trans, BLUE, "Transposition ciphertext: same shape as English"),
        (axes[1], subst, RED, "Substitution ciphertext: the bars are shuffled"),
    ):
        counts = Counter(text)
        percent = [100 * counts[c] / n for c in ALPHABET]
        ax.bar(xs, percent, color=color, width=0.75, label="ciphertext")
        ax.plot(xs, ENGLISH_PERCENT, color="black", marker="o", ms=5, lw=2,
                label="normal English")
        ax.set_xticks(list(xs))
        ax.set_xticklabels(list(ALPHABET), fontsize=13, family="monospace")
        ax.set_ylabel("% of letters")
        ax.set_title(title, fontsize=17, fontweight="bold", color=color)
        ax.legend(loc="upper right", fontsize=13)
        ax.set_ylim(0, 16)
    fig.tight_layout()
    save(fig, "07-frequencies.png")


def fig_rail_fence() -> None:
    """The zigzag of THEOWLFLIESATMIDNIGHT on three rails, and the read-off."""
    text = letters(RAIL_PLAIN)
    pattern = rail_pattern(len(text), RAILS)
    cipher = railfence_encrypt(text, RAILS)
    print("rail fence:", text, "->", cipher)
    fig, ax = plt.subplots(figsize=(WIDTH * 1.3, 5.6))
    step = 1.0
    for i in range(len(text) - 1):
        ax.plot([i * step, (i + 1) * step], [-pattern[i], -pattern[i + 1]], color="#cccccc",
                lw=2, zorder=1)
    for i, (c, r) in enumerate(zip(text, pattern)):
        ax.add_patch(FancyBboxPatch((i * step - 0.38, -r - 0.38), 0.76, 0.76,
                                    boxstyle="round,pad=0.02", fc="white",
                                    ec=RAIL_COLORS[r], lw=2.5, zorder=2))
        ax.text(i * step, -r, c, ha="center", va="center", fontsize=17, fontweight="bold",
                color=RAIL_COLORS[r], zorder=3, family="monospace")
    for r in range(RAILS):
        ax.text(-1.0, -r, f"rail {r + 1}", ha="right", va="center", fontsize=15,
                color=RAIL_COLORS[r], fontweight="bold")
    # Read-off line: each rail's letters, in its color.
    x = 0.0
    y = -RAILS - 0.5
    ax.text(-1.0, y, "read rails\nin turn:", ha="right", va="center", fontsize=14)
    for r in range(RAILS):
        part = "".join(c for c, p in zip(text, pattern) if p == r)
        for c in part:
            ax.text(x, y, c, ha="center", va="center", fontsize=17, fontweight="bold",
                    color=RAIL_COLORS[r], family="monospace")
            x += 0.62
        x += 0.5
    ax.set_xlim(-3.2, len(text) * step)
    ax.set_ylim(-RAILS - 1.2, 0.8)
    ax.axis("off")
    ax.set_title("Rail fence: write in a zigzag, read along each rail", fontsize=20,
                 fontweight="bold")
    save(fig, "07-rail-fence.png")


def _grid(ax, rows, x0, y0, *, colors, cell=1.0, fontsize=17, header=None, header_color=None):
    """Draw a grid of letters (list of strings) with column colors; returns nothing."""
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            ax.add_patch(Rectangle((x0 + c * cell, y0 - (r + 1) * cell), cell, cell,
                                   fc=colors[c], ec="white", lw=2))
            ax.text(x0 + (c + 0.5) * cell, y0 - (r + 0.5) * cell, ch.upper(), ha="center",
                    va="center", fontsize=fontsize, family="monospace", fontweight="bold")
    if header:
        for c, h in enumerate(header):
            ax.text(x0 + (c + 0.5) * cell, y0 + 0.45 * cell, h, ha="center", va="center",
                    fontsize=fontsize, fontweight="bold",
                    color=header_color[c] if header_color else "black")


def fig_columnar_grid() -> None:
    """Write MEETTHEQUEEN... in rows under TIGER, number the columns, read them in order."""
    text = letters(WORKED_PLAIN)
    width = len(WORKED_KEY)
    order = key_order(WORKED_KEY)
    rows = [text[i:i + width] for i in range(0, len(text), width)]
    cipher = columnar_encrypt(text, WORKED_KEY)
    print("columnar:", text, "->", cipher, "order", order)
    fig, ax = plt.subplots(figsize=(WIDTH * 1.25, 6.6))
    colors = COLUMN_COLORS[:width]
    _grid(ax, rows, 0, 0, colors=colors, header=list(WORKED_KEY))
    for c in range(width):
        ax.text(c + 0.5, 1.15, f"{order[c] + 1}", ha="center", va="center", fontsize=15,
                color=RED, fontweight="bold")
    ax.text(-0.3, 1.15, "order:", ha="right", va="center", fontsize=14, color=RED)
    ax.text(-0.3, 0.45, "key:", ha="right", va="center", fontsize=14)
    # Ciphertext: the columns in key order, each in its column's color.
    x0, y0 = width + 1.6, -0.8
    ax.text(x0, 0.45, "read the columns in order 1, 2, 3, 4, 5:", fontsize=15,
            fontweight="bold", va="center")
    for rank in range(width):
        c = order.index(rank)
        column = text[c::width]
        y = y0 - rank * 1.25
        ax.add_patch(Rectangle((x0, y - 0.45), 0.62 * len(column) + 0.2, 0.9,
                               fc=colors[c], ec="none"))
        ax.text(x0 - 0.25, y, f"{rank + 1}", ha="right", va="center", fontsize=15,
                color=RED, fontweight="bold")
        ax.text(x0 + 0.1, y, " ".join(column), ha="left", va="center", fontsize=16,
                family="monospace", fontweight="bold")
    ax.text(0, -len(rows) - 0.8, "ciphertext:  " + " ".join(cipher[i:i + 8]
            for i in range(0, len(cipher), 8)), fontsize=15, family="monospace",
            fontweight="bold", va="center")
    ax.set_xlim(-1.6, width + 8.5)
    ax.set_ylim(-len(rows) - 1.3, 1.7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Columnar transposition with the key TIGER", fontsize=20, fontweight="bold")
    save(fig, "07-columnar-grid.png")


def fig_factors() -> None:
    """A 40-letter ciphertext can only fill rectangles whose sides multiply to 40."""
    n = 40
    shapes = [(w, n // w) for w in range(2, n) if n % w == 0 and 2 <= w <= 10]
    print("widths for", n, ":", [w for w, _ in shapes])
    fig, ax = plt.subplots(figsize=(WIDTH * 1.3, 5.4))
    x = 0.0
    cell = 0.32
    for w, h in shapes:
        x += max(0.0, (1.3 - w * cell) / 2)
        color = GREEN if w == 5 else BLUE
        for r in range(h):
            for c in range(w):
                ax.add_patch(Rectangle((x + c * cell, -r * cell), cell, cell,
                                       fc="#d9f5d0" if w == 5 else "#d6e9ff", ec=color,
                                       lw=1))
        ax.text(x + w * cell / 2, 0.55, f"{w} wide", ha="center", fontsize=16,
                fontweight="bold", color=color)
        ax.text(x + w * cell / 2, -h * cell - 0.15, f"{w} × {h}", ha="center", va="top",
                fontsize=15, color=color)
        x += max(w * cell, 1.3) + 0.9
    ax.set_xlim(-0.6, x)
    ax.set_ylim(-20 * cell - 0.9, 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("40 letters: the possible column widths are the factors of 40",
                 fontsize=19, fontweight="bold")
    save(fig, "07-factors.png")


def fig_strips() -> None:
    """Cut the ciphertext into 5 strips, then slide them: QU fixes two, the rest follows."""
    text = letters(WORKED_PLAIN)
    width = len(WORKED_KEY)
    cipher = columnar_encrypt(text, WORKED_KEY)
    height = len(cipher) // width
    strips = [cipher[i * height:(i + 1) * height] for i in range(width)]
    names = "ABCDE"
    order = key_order(WORKED_KEY)
    # The true left-to-right arrangement: strip index for each plaintext column.
    solution = [order[c] for c in range(width)]
    print("strips:", dict(zip(names, strips)), "solution:", "".join(names[s] for s in solution))
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH * 1.25, 6.8))
    colors = COLUMN_COLORS[:width]

    def draw(ax, arrangement, title, highlight_rows=()):
        rows = ["".join(strips[s][r] for s in arrangement) for r in range(height)]
        _grid(ax, rows, 0, 0, colors=[colors[s] for s in arrangement],
              header=[names[s] for s in arrangement])
        for r in highlight_rows:
            ax.add_patch(Rectangle((0, -(r + 1)), width, 1, fc="none", ec=RED, lw=3.5))
        ax.set_xlim(-0.3, width + 0.3)
        ax.set_ylim(-height - 0.3, 1.2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=16, fontweight="bold")

    draw(axes[0], list(range(width)), "1. Cut into 5 strips of 8")
    draw(axes[1], solution, "2. Slide the strips until rows read", highlight_rows=(1,))
    axes[1].text(width + 0.4, -1.5, "Q needs U:\nB goes just\nbefore A", fontsize=14,
                 color=RED, va="center", fontweight="bold")
    fig.suptitle("Anagramming the columns", fontsize=20, fontweight="bold")
    fig.tight_layout()
    save(fig, "07-strips.png")


def main() -> None:
    fig_frequencies()
    fig_rail_fence()
    fig_columnar_grid()
    fig_factors()
    fig_strips()


if __name__ == "__main__":
    main()
