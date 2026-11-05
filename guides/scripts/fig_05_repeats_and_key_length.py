"""Figures for Guide 05, Repeats and key length (the Kasiski examination).

Run from anywhere: ``python guides/scripts/fig_05_repeats_and_key_length.py``.
Writes every figure of the guide to ``guides/figures/05-*.png`` (200 dpi, about 1600 px wide)
and prints the numbers the guide quotes, so the text can be checked against them.
Uses only matplotlib and the standard library.
"""

from collections import Counter
from functools import reduce
from math import gcd
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Standard published English letter frequencies (fractions), A to Z.
ENGLISH = (
    0.082, 0.015, 0.028, 0.043, 0.127, 0.022, 0.020, 0.061, 0.070, 0.0015, 0.0077, 0.040, 0.024,
    0.067, 0.075, 0.019, 0.00095, 0.060, 0.063, 0.091, 0.028, 0.0098, 0.024, 0.0015, 0.020, 0.00074,
)
PLAINTEXT = (
    "meet me at the old mill at nine. bring the map and the lamp. the map shows the path "
    "from the old mill to the river, and the river leads to the cave. if the path is flooded, "
    "wait at the old mill until dawn and then follow the river north. do not light the lamp "
    "until you reach the cave."
)
KEY = "BRIDGE"
FACTORS = range(2, 13)

BLUE, ORANGE, GREEN, PINK, PURPLE, GREY = (
    "#2b7bff", "#ff8a00", "#1db954", "#ff3d7f", "#8e44ff", "#9aa0a6")
REPEAT_COLORS = ["#ff6b6b", "#ffb347", "#ffe066", "#6bd968", "#5cc8ff", "#c39bff", "#ff9ad5"]

plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 18, "axes.labelsize": 16, "xtick.labelsize": 14,
    "ytick.labelsize": 14, "legend.fontsize": 14, "figure.facecolor": "white",
    "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
})


def letters(text):
    return "".join(c for c in text.upper() if c in ALPHABET)


def num(c):
    return ALPHABET.index(c)


def vigenere(text, key):
    return "".join(ALPHABET[(num(c) + num(key[i % len(key)])) % 26] for i, c in enumerate(text))


def beaufort(text, key):
    return "".join(ALPHABET[(num(key[i % len(key)]) - num(c)) % 26] for i, c in enumerate(text))


def autokey(text, key):
    stream = key + text
    return "".join(ALPHABET[(num(c) + num(stream[i])) % 26] for i, c in enumerate(text))


def repeats(text, length=3):
    """Every repeated run of `length` letters, with its starting positions (counting from 1)."""
    found = {}
    for i in range(len(text) - length + 1):
        found.setdefault(text[i:i + length], []).append(i + 1)
    return {k: v for k, v in found.items() if len(v) > 1}


def merged_repeats(text):
    """Repeated runs of 3+ letters, with overlapping trigrams joined into one longer run.

    Returns (run, positions) pairs; a run that is part of a longer run at the same
    positions is dropped, so each distance is counted once.
    """
    runs = []
    for tri, pos in repeats(text).items():
        runs.append((tri, tuple(pos)))
    changed = True
    while changed:
        changed = False
        for a in runs:
            for b in runs:
                if a is b or len(a[1]) != len(b[1]):
                    continue
                if all(pb == pa + len(a[0]) - 2 for pa, pb in zip(a[1], b[1])) and \
                        a[0][-2:] == b[0][:2]:
                    runs.remove(a)
                    runs.remove(b)
                    runs.append((a[0] + b[0][2:], a[1]))
                    changed = True
                    break
            if changed:
                break
    # drop a run whose occurrences all sit inside a longer run's occurrences
    def inside(small, big):
        return all(any(q <= p and p + len(small[0]) <= q + len(big[0]) for q in big[1])
                   for p in small[1])
    keep = [r for r in runs if not any(o is not r and len(o[0]) > len(r[0]) and inside(r, o)
                                       for o in runs)]
    return sorted(keep, key=lambda r: r[1][0])


def distances(runs):
    return [b - a for _, pos in runs for a, b in zip(pos, pos[1:])]


def factor_counts(ds):
    return {f: sum(d % f == 0 for d in ds) for f in FACTORS}


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def cell(ax, x, y, ch, color, *, size=18, w=0.92, weight="bold", text_color="black"):
    ax.add_patch(Rectangle((x, y), w, 0.92, color=color))
    ax.text(x + w / 2, y + 0.46, ch, ha="center", va="center", fontsize=size,
            family="monospace", weight=weight, color=text_color)


def fig_why_repeats(p):
    """The same word under the same key letters gives the same ciphertext."""
    fig, ax = plt.subplots(figsize=(8, 5.4))
    cases = [(9, PINK), (39, PINK), (30, GREY)]
    for row, (start, color) in enumerate(cases):
        y = -row * 4.2
        i = start - 1
        key = "".join(KEY[(i + j) % len(KEY)] for j in range(3))
        cipher = vigenere(p, KEY)[i:i + 3]
        for j in range(3):
            cell(ax, 3 + j, y + 1, key[j], "#ffe9a8")
            cell(ax, 3 + j, y, p[i + j].lower(), "#d9f2ff", weight="normal")
            cell(ax, 3 + j, y - 1, cipher[j], color, text_color="white")
        for dy, lab in [(1, "key"), (0, "plain"), (-1, "cipher")]:
            ax.text(2.8, y + dy + 0.46, lab, ha="right", va="center", fontsize=15)
        ax.text(0, y + 2.3, f"letters {start} to {start + 2}", fontsize=16, weight="bold")
        note = ("same key letters, so the\nSAME ciphertext: " + cipher) if color == PINK else \
            ("different key letters, so a\ndifferent ciphertext: " + cipher)
        ax.text(6.6, y + 0.46, note, va="center", fontsize=15, color=color if color == PINK else "#555")
    ax.text(0, -12.6, "39 - 9 = 30 = 5 x 6: the gap is a multiple of the key length (6)",
            fontsize=16, weight="bold", color=PINK)
    ax.set_xlim(-0.2, 12.5)
    ax.set_ylim(-13.2, 3.4)
    ax.axis("off")
    ax.set_title("Why repeats appear: key BRIDGE, plaintext 'the' three times", fontsize=18)
    save(fig, "05-why-repeats.png")


def fig_repeats_in_ciphertext(c, runs):
    width = 30
    colors = {}
    for k, (run, pos) in enumerate(runs):
        for p0 in pos:
            for j in range(len(run)):
                colors.setdefault(p0 - 1 + j, REPEAT_COLORS[k % len(REPEAT_COLORS)])
    fig, ax = plt.subplots(figsize=(8, 5.4))
    for i, ch in enumerate(c):
        r, col = divmod(i, width)
        cell(ax, col * 0.62, -r, ch, colors.get(i, "#eef0f3"), size=12, w=0.58,
             weight="bold" if i in colors else "normal")
    for r in range((len(c) + width - 1) // width):
        ax.text(-0.3, -r + 0.46, str(r * width + 1), ha="right", va="center", fontsize=12,
                color="#666")
    for k, (run, pos) in enumerate(runs):
        y = -9.0 - (k // 2) * 0.95
        x = (k % 2) * 9.4
        ax.add_patch(Rectangle((x, y), 0.6, 0.6, color=REPEAT_COLORS[k % len(REPEAT_COLORS)]))
        ax.text(x + 0.9, y + 0.3, f"{run}: letters {', '.join(map(str, pos))}", va="center",
                fontsize=13)
    ax.set_xlim(-1.4, width * 0.62 + 0.2)
    ax.set_ylim(-9.2 - ((len(runs) + 1) // 2) * 0.95, 1.2)
    ax.axis("off")
    ax.set_title("The ciphertext, 30 letters per row, with its repeats colored", fontsize=18)
    save(fig, "05-repeats-in-ciphertext.png")


def fig_factor_table(ds):
    factors = list(range(2, 11))
    fig, ax = plt.subplots(figsize=(8, 7.2))
    for j, f in enumerate(factors):
        cell(ax, 1.6 + j, 1, str(f), "#e0e4ea", size=16)
    ax.text(1.4, 1.46, "factor", ha="right", va="center", fontsize=15, weight="bold")
    for i, d in enumerate(ds):
        y = -i * 0.8
        ax.text(1.4, y + 0.4, f"gap {d}", ha="right", va="center", fontsize=15)
        for j, f in enumerate(factors):
            hit = d % f == 0
            color = (PINK if f == 6 else GREEN) if hit else "#f3f4f6"
            ax.add_patch(Rectangle((1.6 + j, y), 0.92, 0.72, color=color))
            if hit:
                ax.text(2.06 + j, y + 0.36, "yes", ha="center", va="center", fontsize=12,
                        color="white", weight="bold")
    y = -len(ds) * 0.8 - 0.3
    ax.text(1.4, y + 0.4, "total", ha="right", va="center", fontsize=15, weight="bold")
    for j, f in enumerate(factors):
        n = sum(d % f == 0 for d in ds)
        ax.text(2.06 + j, y + 0.4, str(n), ha="center", va="center", fontsize=16, weight="bold",
                color=PINK if f == 6 else "black")
    ax.set_xlim(-0.6, 11)
    ax.set_ylim(y - 0.4, 2.2)
    ax.axis("off")
    ax.set_title("Which numbers divide each gap?  Every gap is a multiple of 6", fontsize=18)
    save(fig, "05-factor-table.png")


def fig_divisors():
    numbers = [18, 30, 102]
    common = set.intersection(*({d for d in range(1, n + 1) if n % d == 0} for n in numbers))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for r, n in enumerate(numbers):
        ds = [d for d in range(1, n + 1) if n % d == 0]
        y = -r * 1.3
        ax.text(-0.3, y + 0.46, f"{n}:", ha="right", va="center", fontsize=18, weight="bold")
        for j, d in enumerate(ds):
            cell(ax, j * 1.05, y, str(d), PINK if d == max(common) else
                 (YELLOW_LIGHT if d in common else "#e8ebef"), size=15, w=0.98)
    ax.text(0, -4.1, "Divisors shared by all three: 1, 2, 3, 6.  The greatest is 6.",
            fontsize=16, weight="bold", color=PINK)
    ax.set_xlim(-1.6, 8.6)
    ax.set_ylim(-4.6, 1.2)
    ax.axis("off")
    ax.set_title("The greatest common divisor of 18, 30 and 102", fontsize=18)
    save(fig, "05-divisors.png")


YELLOW_LIGHT = "#ffe066"


def fig_column_fit(c):
    """Column 2 of the ciphertext against the English pattern, before and after sliding."""
    col = c[1::len(KEY)]
    counts = Counter(col)
    shift = num(KEY[1])
    n = len(col)
    fig, axes = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True)
    xs = range(26)
    for ax, s, title in [(axes[0], 0, "English pattern not slid: peaks miss"),
                         (axes[1], shift, f"English pattern slid by {shift} (key letter {KEY[1]}): peaks line up")]:
        ax.bar(xs, [counts[ch] for ch in ALPHABET], color=BLUE, label="column 2 counts")
        expected = [ENGLISH[(x - s) % 26] * n for x in xs]
        ax.plot(xs, expected, color=ORANGE, lw=3, marker="o", label="English, scaled")
        ax.set_title(title, fontsize=16)
        ax.set_ylabel("count")
        ax.set_xticks(list(xs), list(ALPHABET))
        ax.tick_params(labelbottom=True)
    axes[0].legend(loc="upper left", ncol=2, frameon=False)
    for ax in axes:
        ax.set_ylim(0, 12)
        ax.set_yticks([0, 2, 4, 6, 8, 10])
    for plain in "eta":
        x = (num(plain.upper()) + shift) % 26
        axes[1].annotate(f"{plain} -> {ALPHABET[x]}", xy=(x, counts[ALPHABET[x]]),
                         xytext=(x, counts[ALPHABET[x]] + 2.2), ha="center", fontsize=14,
                         color=PINK, weight="bold", arrowprops=dict(arrowstyle="->", color=PINK))
    fig.tight_layout()
    save(fig, "05-column-fit.png")


def fig_three_ciphers(tallies):
    fig, axes = plt.subplots(1, 3, figsize=(8, 3.9), sharey=True)
    for ax, (name, (tally, n)) in zip(axes, tallies.items()):
        fs = list(tally)
        ax.bar(fs, [tally[f] / n for f in fs],
               color=[PINK if f == 6 else BLUE for f in fs])
        ax.set_title(f"{name}\n({n} gaps)", fontsize=15)
        ax.set_xticks([2, 4, 6, 8, 10, 12])
        ax.set_xlabel("factor")
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("share of gaps it divides")
    fig.suptitle("Same message, same key BRIDGE, three ciphers", fontsize=17)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, "05-three-ciphers.png")


if __name__ == "__main__":
    p = letters(PLAINTEXT)
    c = vigenere(p, KEY)
    print("letters", len(p))
    runs = merged_repeats(c)
    for run, pos in runs:
        print("  vig repeat", run, pos, [b - a for a, b in zip(pos, pos[1:])],
              [p[q - 1:q - 1 + len(run)] for q in pos])
    ds = distances(runs)
    print("vig gaps", ds, "gcd", reduce(gcd, ds), factor_counts(ds))
    b = beaufort(p, KEY)
    bruns = merged_repeats(b)
    bds = distances(bruns)
    for run, pos in bruns:
        print("  beau repeat", run, pos, [p[q - 1:q - 1 + len(run)] for q in pos])
    print("beau gaps", bds, "gcd", reduce(gcd, bds), factor_counts(bds))
    a = autokey(p, KEY)
    aruns = merged_repeats(a)
    ads = distances(aruns)
    for run, pos in aruns:
        print("  auto repeat", run, pos, [p[q - 1:q - 1 + len(run)] for q in pos])
    print("auto gaps", ads, "gcd", reduce(gcd, ads), factor_counts(ads))
    fig_why_repeats(p)
    fig_repeats_in_ciphertext(c, runs)
    fig_factor_table(ds)
    fig_divisors()
    fig_column_fit(c)
    fig_three_ciphers({
        "Vigenère": (factor_counts(ds), len(ds)),
        "Beaufort": (factor_counts(bds), len(bds)),
        "Autokey": (factor_counts(ads), len(ads)),
    })
