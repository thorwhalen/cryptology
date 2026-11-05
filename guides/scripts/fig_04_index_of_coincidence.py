"""Figures for Guide 04, The index of coincidence.

Run from anywhere: ``python guides/scripts/fig_04_index_of_coincidence.py``.
Writes every figure of the guide to ``guides/figures/04-*.png`` (200 dpi, about 1600 px wide).
Uses only matplotlib, numpy and the standard library; the worked-example text and the
English letter frequencies live in this file.
"""

from collections import Counter
from pathlib import Path
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Standard published English letter frequencies (fractions), A to Z.
ENGLISH = dict(zip(ALPHABET, (
    0.082, 0.015, 0.028, 0.043, 0.127, 0.022, 0.020, 0.061, 0.070, 0.0015, 0.0077, 0.040, 0.024,
    0.067, 0.075, 0.019, 0.00095, 0.060, 0.063, 0.091, 0.028, 0.0098, 0.024, 0.0015, 0.020, 0.00074,
)))
KAPPA_ENGLISH = 0.066
KAPPA_RANDOM = 1 / 26

BLUE, ORANGE, GREEN, PINK, PURPLE, YELLOW, GREY = (
    "#2b7bff", "#ff8a00", "#1db954", "#ff3d7f", "#8e44ff", "#ffd23f", "#9aa0a6")
COLUMN_COLORS = ["#ff6b6b", "#ffb347", "#ffe066", "#6bd968", "#5cc8ff"]

PLAINTEXT = (
    "the lighthouse keeper had not spoken to anyone for three weeks when the boat finally "
    "came. it brought flour, oil, a stack of letters and a small wooden box with no name on "
    "it. inside the box was a brass key and a note that said only this: the light is not "
    "what it seems. look under the seventh step at midnight and tell no one what you find there."
)
KEY = "STORM"

plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 19, "axes.labelsize": 16, "xtick.labelsize": 14,
    "ytick.labelsize": 14, "legend.fontsize": 14, "figure.facecolor": "white",
    "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
})


def letters(text):
    return "".join(c for c in text.upper() if c in ALPHABET)


def ioc(text):
    counts = Counter(text)
    n = sum(counts.values())
    return sum(f * (f - 1) for f in counts.values()) / (n * (n - 1))


def vigenere(text, key):
    k = [ALPHABET.index(c) for c in key]
    return "".join(ALPHABET[(ALPHABET.index(c) + k[i % len(k)]) % 26] for i, c in enumerate(text))


def keyword_substitution(text, keyword):
    seen = list(dict.fromkeys(keyword))
    cipher_alphabet = "".join(seen + [c for c in ALPHABET if c not in seen])
    return text.translate(str.maketrans(ALPHABET, cipher_alphabet))


def columnar(text, keyword):
    order = sorted(range(len(keyword)), key=lambda i: (keyword[i], i))
    return "".join(text[i::len(keyword)] for i in order)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def fig_match_grids():
    """1000 pairs of letters as 1000 squares: about 66 match in English, about 38 at random."""
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.6))
    for ax, (title, hits, color) in zip(axes, [
        ("English text", round(KAPPA_ENGLISH * 1000), GREEN),
        ("Random letters", round(KAPPA_RANDOM * 1000), ORANGE),
    ]):
        rng = random.Random(7 if color == GREEN else 3)
        chosen = set(rng.sample(range(1000), hits))
        for i in range(1000):
            r, c = divmod(i, 40)
            ax.add_patch(Rectangle((c, -r), 0.86, 0.86, color=color if i in chosen else "#e3e6ea"))
        ax.set_xlim(-0.5, 40.5)
        ax.set_ylim(-25.5, 1.5)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{title}:\n{hits} matches in 1000 pairs", fontsize=16, color=color, weight="bold")
    fig.suptitle("Pick two letters at random. How often are they the same?", fontsize=18, y=0.93)
    fig.subplots_adjust(wspace=0.12)
    save(fig, "04-match-grids.png")


def fig_where_matches_come_from():
    """Each letter's share of the English match chance: p times p, biggest first."""
    shares = sorted(((p * p, c) for c, p in ENGLISH.items()), reverse=True)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    xs = range(26)
    ax.bar(xs, [s for s, _ in shares], color=[PINK if i < 6 else BLUE for i in xs])
    ax.axhline((1 / 26) ** 2, color=ORANGE, lw=3, ls="--")
    ax.text(25.4, (1 / 26) ** 2 + 0.0004, "random letters: 1/26 x 1/26 each",
            color=ORANGE, ha="right", fontsize=14)
    ax.set_xticks(list(xs), [c for _, c in shares])
    ax.set_ylabel("chance both picks are\nthis letter")
    ax.annotate("E then E:\n0.127 x 0.127 = 0.016", xy=(0, shares[0][0]), xytext=(4, 0.0145),
                fontsize=15, arrowprops=dict(arrowstyle="->", lw=2))
    ax.set_title("Add up all 26 bars and you get English's match chance, about 0.066")
    save(fig, "04-where-matches-come-from.png")


def fig_ioc_by_cipher():
    p = letters(PLAINTEXT)
    rows = [
        ("plaintext (English)", ioc(p), GREEN),
        ("substitution", ioc(keyword_substitution(p, "HARBOR")), GREEN),
        ("transposition", ioc(columnar(p, "ANCHOR")), GREEN),
        ("Vigenère, key SEAGULLS", ioc(vigenere(p, "SEAGULLS")), ORANGE),
        ("Vigenère, key STORM", ioc(vigenere(p, KEY)), ORANGE),
        ("perfectly random letters", KAPPA_RANDOM, GREY),
    ]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ys = range(len(rows))[::-1]
    ax.barh(list(ys), [r[1] for r in rows], color=[r[2] for r in rows], height=0.65)
    for y, (_, v, _) in zip(ys, rows):
        ax.text(v + 0.001, y, f"{v:.3f}", va="center", fontsize=15)
    ax.set_yticks(list(ys), [r[0] for r in rows])
    for x, lab, col in [(KAPPA_ENGLISH, "English 0.066", GREEN), (KAPPA_RANDOM, "random 0.038", GREY)]:
        ax.axvline(x, color=col, ls="--", lw=2)
        ax.text(x, len(rows) - 0.35, lab, color=col, ha="center", fontsize=14, weight="bold")
    ax.set_xlim(0, 0.085)
    ax.set_xlabel("index of coincidence")
    ax.set_title("The same 271-letter message, five ways", pad=28)
    save(fig, "04-ioc-by-cipher.png")


def fig_flattened():
    p = letters(PLAINTEXT)
    c = vigenere(p, KEY)
    fig, axes = plt.subplots(2, 1, figsize=(8, 6.2), sharex=True, sharey=True)
    for ax, text, title, col in [
        (axes[0], p, f"Plaintext: IoC {ioc(p):.3f} (tall peaks, deep valleys)", GREEN),
        (axes[1], c, f"Vigenère with key STORM: IoC {ioc(c):.3f} (flattened)", ORANGE),
    ]:
        counts = Counter(text)
        ax.bar(range(26), [counts[ch] for ch in ALPHABET], color=col)
        ax.set_title(title, fontsize=17)
        ax.set_ylabel("count")
        ax.set_xticks(range(26), list(ALPHABET))
        ax.tick_params(labelbottom=True)
    fig.tight_layout()
    save(fig, "04-flattened.png")


def fig_columns():
    c = vigenere(letters(PLAINTEXT), KEY)
    rows = [c[i:i + 5] for i in range(0, 40, 5)]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.text(-0.3, 1.25, "Ciphertext, written in rows of 5:", fontsize=16, weight="bold")
    ax.text(-0.3, 0.6, c[:40] + "...", fontsize=15, family="monospace")
    for r, row in enumerate(rows):
        for j, ch in enumerate(row):
            y = -0.6 - r
            ax.add_patch(Rectangle((j, y), 0.92, 0.92, color=COLUMN_COLORS[j]))
            ax.text(j + 0.46, y + 0.46, ch, ha="center", va="center", fontsize=18,
                    family="monospace", weight="bold")
    for j in range(5):
        ax.text(j + 0.46, -9.2, f"{j + 1}", ha="center", va="top", fontsize=16)
        ax.text(j + 0.46, -10.2, KEY[j], ha="center", va="top", fontsize=18,
                weight="bold", color="#c0392b")
    ax.text(-0.4, -9.2, "column", ha="right", va="top", fontsize=15)
    ax.text(-0.4, -10.2, "key letter", ha="right", va="top", fontsize=15, color="#c0392b")
    ax.text(5.6, -2.5, "Every letter in a column\nwas shifted by the\nSAME key letter.\n\n"
            "So each column is a\nplain Caesar cipher,\nand its IoC climbs\nback to about 0.066.",
            fontsize=15, va="top")
    ax.set_xlim(-2.6, 9.8)
    ax.set_ylim(-11.6, 1.8)
    ax.axis("off")
    save(fig, "04-columns.png")


def period_scores(text, max_period):
    return [(q, sum(ioc(text[i::q]) for i in range(q)) / q) for q in range(1, max_period + 1)]


def fig_period_scan():
    c = vigenere(letters(PLAINTEXT), KEY)
    scores = period_scores(c, 16)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = [PINK if q % 5 == 0 else BLUE for q, _ in scores]
    ax.bar([q for q, _ in scores], [s for _, s in scores], color=colors)
    for x, lab, col in [(KAPPA_ENGLISH, "English 0.066", GREEN), (KAPPA_RANDOM, "random 0.038", GREY)]:
        ax.axhline(x, color=col, ls="--", lw=2.5)
        ax.text(17.0, x, lab, color=col, va="center", fontsize=14, weight="bold")
    ax.set_xlim(0.3, 16.7)
    ax.set_xticks([q for q, _ in scores])
    ax.set_xlabel("guessed key length (number of columns)")
    ax.set_ylabel("average IoC of the columns")
    ax.set_ylim(0, 0.1)
    ax.annotate("true key length 5", xy=(5, scores[4][1]), xytext=(1.0, 0.09), fontsize=15,
                color=PINK, weight="bold", arrowprops=dict(arrowstyle="->", color=PINK, lw=2))
    ax.text(11.8, 0.09, "10 and 15 spike too:\nthey are multiples of 5", color=PINK, fontsize=14,
            ha="center", va="center")
    ax.set_title("Split the ciphertext into columns and measure each guess")
    save(fig, "04-period-scan.png")


def fig_short_texts():
    rng = random.Random(1)
    lengths = [20, 50, 100, 200, 500, 1000]
    weights = [ENGLISH[c] for c in ALPHABET]
    bands = {"English": [], "random": []}
    for n in lengths:
        for name, w in [("English", weights), ("random", None)]:
            xs = sorted(ioc("".join(rng.choices(ALPHABET, weights=w, k=n))) for _ in range(2000))
            bands[name].append((xs[100], xs[1000], xs[1900]))
    fig, ax = plt.subplots(figsize=(8, 4.9))
    for name, col in [("English", GREEN), ("random", ORANGE)]:
        name_label = "English-like text" if name == "English" else "random letters"
        lo, mid, hi = zip(*bands[name])
        ax.fill_between(lengths, lo, hi, color=col, alpha=0.3)
        ax.plot(lengths, mid, color=col, lw=3, marker="o",
                label=f"{name_label} (middle 90% of 2000 samples)")
    ax.set_xscale("log")
    ax.set_xticks(lengths, [str(n) for n in lengths])
    ax.set_xlabel("number of letters in the text")
    ax.set_ylabel("index of coincidence")
    ax.legend(loc="upper right")
    ax.set_ylim(0.015, 0.13)
    ax.set_title("Short texts give wobbly numbers")
    ax.text(22, 0.02, "at 20 letters the two\nbands overlap", fontsize=14)
    save(fig, "04-short-texts.png")


if __name__ == "__main__":
    fig_match_grids()
    fig_where_matches_come_from()
    fig_ioc_by_cipher()
    fig_flattened()
    fig_columns()
    fig_period_scan()
    fig_short_texts()
