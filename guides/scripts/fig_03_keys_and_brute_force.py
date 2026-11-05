"""Figures for Guide 03, Keys and brute force: counting keys, clock arithmetic mod 26, trying
every Caesar key, why the affine multiplier must share no factor with 26, inverses, and solving
an affine key from two guessed letters.

Run from anywhere: ``python guides/scripts/fig_03_keys_and_brute_force.py``.
Writes PNGs into ``guides/figures/``. Uses only matplotlib, numpy and the standard library.
The worked-example ciphertexts are original and are recomputed here from their plaintexts.
"""

from math import factorial, gcd
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
M = 26

BLUE, ORANGE, GREEN, PURPLE = "#3B82F6", "#F97316", "#22C55E", "#A855F7"
RED, YELLOW, TEAL, GREY, INK = "#EF4444", "#FACC15", "#14B8A6", "#9CA3AF", "#1F2937"
LIGHT = {BLUE: "#DBEAFE", ORANGE: "#FFEDD5", GREEN: "#DCFCE7", PURPLE: "#F3E8FF", RED: "#FEE2E2", YELLOW: "#FEF9C3", TEAL: "#CCFBF1", GREY: "#F3F4F6"}

plt.rcParams.update({"font.size": 14, "font.family": "DejaVu Sans", "axes.titlesize": 16, "axes.labelsize": 14})

CAESAR_PLAIN = "MEETMEBYTHEOLDMILL"
CAESAR_KEY = 17
AFFINE_PLAIN = (
    "THESECRETMEETINGISSETFORTENTONIGHTATTHEEASTGATEBRINGTHELETTERTHETORCHANDTHESTREETMAPANDTELLNOBODYWHEREWEAREGOING"
)
AFFINE_KEY = (11, 6)


def shift(text, k):
    return "".join(ALPHABET[(ALPHABET.index(c) + k) % M] for c in text)


def affine(text, a, b):
    return "".join(ALPHABET[(a * ALPHABET.index(c) + b) % M] for c in text)


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", FIG_DIR / name)


def fig_key_space():
    big = factorial(26)
    rows = [
        ("Caesar", "26", 26, BLUE, "try them all in a minute by hand"),
        ("Affine", "12 x 26 = 312", 312, ORANGE, "an afternoon by hand; instant by computer"),
        ("Substitution", f"26! = {big:,}", big, RED, "at a billion keys a second:\nabout 12.8 billion years"),
    ]
    fig, ax = plt.subplots(figsize=(11, 6))
    digits = [len(str(n)) for _, _, n, _, _ in rows]
    y = np.arange(len(rows))[::-1]
    ax.barh(y, digits, color=[r[3] for r in rows], height=0.55)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=18, weight="bold")
    ax.set_xlim(0, 30)
    ax.set_xlabel("how many digits the number of keys has")
    for yi, d, (name, label, n, color, note) in zip(y, digits, rows):
        if d < 10:
            ax.text(d + 0.4, yi + 0.12, label, va="center", fontsize=15, weight="bold", color=INK)
            ax.text(d + 0.4, yi - 0.14, note, va="center", fontsize=14, color=INK, style="italic")
        else:  # the huge one: write inside its own bar
            ax.text(0.5, yi + 0.1, label, va="center", fontsize=15, weight="bold", color="white")
            ax.text(0.5, yi - 0.15, note.replace("\n", " "), va="center", fontsize=14, color="white", style="italic")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("How many keys? Counting the key space", fontsize=21, weight="bold", color=INK)
    save(fig, "03-key-space.png")


def fig_clock():
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.5, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 1.0, facecolor=LIGHT[BLUE], edgecolor=BLUE, linewidth=4))
    angle = lambda i: np.pi / 2 - 2 * np.pi * i / M
    for i, c in enumerate(ALPHABET):
        t = angle(i)
        hot = i in (23, 2)
        ax.text(1.18 * np.cos(t), 1.18 * np.sin(t), c, ha="center", va="center", fontsize=19, weight="bold",
                color=RED if hot else INK)
        ax.text(0.86 * np.cos(t), 0.86 * np.sin(t), str(i), ha="center", va="center", fontsize=13,
                color=RED if hot else "#374151")
    # Arrow from 23 forward 5 steps to 2 (28 = 26 + 2).
    p0 = (0.68 * np.cos(angle(23)), 0.68 * np.sin(angle(23)))
    p1 = (0.68 * np.cos(angle(28)), 0.68 * np.sin(angle(28)))
    ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=5, mutation_scale=32,
                                                       connectionstyle="arc3,rad=-0.35"))
    ax.text(0, 0.5, "+5", ha="center", va="center", fontsize=20, weight="bold", color=ORANGE)
    ax.text(0, 0.12, "23 + 5 = 28", ha="center", va="center", fontsize=24, weight="bold", color=INK)
    ax.text(0, -0.15, "28 - 26 = 2", ha="center", va="center", fontsize=20, color=INK)
    ax.text(0, -0.42, "X + 5 steps = C", ha="center", va="center", fontsize=19, weight="bold", color=ORANGE)
    ax.text(0, -1.42, "A 26-hour clock: after 25 comes 0 again", ha="center", va="center", fontsize=19, weight="bold", color=INK)
    save(fig, "03-clock-26.png")


def fig_brute_force():
    ct = shift(CAESAR_PLAIN, CAESAR_KEY)
    fig, ax = plt.subplots(figsize=(9, 11))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.6, M + 1.6)
    ax.axis("off")
    ax.text(5, M + 1.2, f"Trying all 26 keys on  {ct}", ha="center", va="center", fontsize=19, weight="bold", color=INK)
    for k in range(M):
        y = M - 1 - k
        right = k == CAESAR_KEY
        if right:
            ax.add_patch(Rectangle((0.1, y - 0.45), 9.8, 0.9, facecolor=GREEN, edgecolor="none"))
        elif k % 2:
            ax.add_patch(Rectangle((0.1, y - 0.45), 9.8, 0.9, facecolor="#E5E7EB", edgecolor="none"))
        ax.text(1.4, y, f"back {k:2d}", ha="right", va="center", fontsize=14, family="monospace",
                color="white" if right else "#4B5563", weight="bold" if right else "normal")
        ax.text(2.0, y, shift(ct, -k).lower(), ha="left", va="center", fontsize=17, family="monospace",
                color="white" if right else INK, weight="bold" if right else "normal")
    ax.text(8.0, M - 1 - CAESAR_KEY, "reads!", ha="left", va="center", fontsize=16, weight="bold", color="white")
    save(fig, "03-caesar-brute-force.png")


def fig_multiply():
    rows = [(2, RED, "times 2: only even numbers, each hit twice"),
            (13, RED, "times 13: only 0 and 13"),
            (3, GREEN, "times 3: every number exactly once")]
    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.set_xlim(-2.6, M + 0.2)
    ax.set_ylim(-0.6, 10.4)
    ax.axis("off")
    ax.text(M / 2 - 1.2, 10.05, "Multiplying every letter by a number, mod 26", ha="center", va="center", fontsize=21, weight="bold", color=INK)
    y0 = 8.2
    ax.text(-0.3, y0 + 0.4, "x", ha="right", va="center", fontsize=17, weight="bold", color=INK)
    for x in range(M):
        ax.add_patch(Rectangle((x, y0), 0.95, 0.8, facecolor=LIGHT[BLUE], edgecolor=BLUE))
        ax.text(x + 0.475, y0 + 0.4, str(x), ha="center", va="center", fontsize=12.5, color=INK)
    for r, (a, color, note) in enumerate(rows):
        y = 5.7 - 2.6 * r
        vals = [(a * x) % M for x in range(M)]
        seen = {}
        for v in vals:
            seen[v] = seen.get(v, 0) + 1
        ax.text(-0.3, y + 0.4, f"{a}x", ha="right", va="center", fontsize=17, weight="bold", color=color)
        for x, v in enumerate(vals):
            repeat = seen[v] > 1
            ax.add_patch(Rectangle((x, y), 0.95, 0.8, facecolor=LIGHT[RED] if repeat else LIGHT[GREEN],
                                   edgecolor=RED if repeat else GREEN))
            ax.text(x + 0.475, y + 0.4, str(v), ha="center", va="center", fontsize=12.5, color=INK)
        ax.text(0, y + 1.15, note, ha="left", va="center", fontsize=16, weight="bold", color=color)
    save(fig, "03-multiply-mod-26.png")


def fig_inverses():
    allowed = [a for a in range(1, M) if gcd(a, M) == 1]
    fig, ax = plt.subplots(figsize=(13, 4.6))
    ax.set_xlim(-3.2, len(allowed))
    ax.set_ylim(-0.5, 4.3)
    ax.axis("off")
    labels = [("a", BLUE), ("inverse", ORANGE), ("a x inverse", PURPLE)]
    ax.text(len(allowed) / 2 - 1.6, -0.15, "each product is 1 more than a multiple of 26, so it counts as 1", ha="center",
            va="center", fontsize=15, color=PURPLE, style="italic")
    for r, (lab, color) in enumerate(labels):
        y = 2.6 - 1.05 * r
        ax.text(-0.15, y + 0.45, lab, ha="right", va="center", fontsize=16, weight="bold", color=color)
        for i, a in enumerate(allowed):
            inv = pow(a, -1, M)
            txt = [str(a), str(inv), str(a * inv)][r]
            ax.add_patch(Rectangle((i, y), 0.95, 0.9, facecolor=LIGHT[color], edgecolor=color))
            ax.text(i + 0.475, y + 0.45, txt, ha="center", va="center",
                    fontsize=17 if r < 2 else 15, weight="bold" if r < 2 else "normal", color=INK)
    ax.text(len(allowed) / 2 - 1.6, 3.95, "The 12 allowed multipliers and their inverses (mod 26)", ha="center", va="center",
            fontsize=20, weight="bold", color=INK)
    save(fig, "03-inverses.png")


def fig_two_equations():
    a, b = AFFINE_KEY
    steps = [
        ("Guess", "commonest cipher letter Y (24) is e (4)\nsecond commonest H (7) is t (19)", BLUE),
        ("Write two equations", "4a + b = 24   (mod 26)\n19a + b = 7   (mod 26)", ORANGE),
        ("Subtract to lose b", "15a = 7 - 24 = -17 = 9   (mod 26)", PURPLE),
        ("Undo the 15", "15 x 7 = 105 = 4 x 26 + 1, so the inverse of 15 is 7\na = 7 x 9 = 63 = 11   (mod 26)", GREEN),
        ("Find b", f"b = 24 - 4 x {a} = -20 = {b}   (mod 26)", TEAL),
        ("Check", "a = 11 shares no factor with 26, and\nthe whole message decrypts to English", RED),
    ]
    fig, ax = plt.subplots(figsize=(12, 12.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 14.4)
    ax.axis("off")
    ax.text(6, 14.0, "Solving an affine key from two letters", ha="center", va="center", fontsize=22, weight="bold", color=INK)
    h, gap = 1.85, 0.42
    for i, (title, body, color) in enumerate(steps):
        y = 13.3 - (i + 1) * h - i * gap
        ax.add_patch(FancyBboxPatch((0.2, y), 11.6, h, boxstyle="round,pad=0,rounding_size=0.2",
                                    facecolor=LIGHT[color], edgecolor=color, linewidth=3))
        ax.add_patch(Circle((0.95, y + h / 2), 0.45, facecolor=color, edgecolor="white", linewidth=2))
        ax.text(0.95, y + h / 2, str(i + 1), ha="center", va="center", fontsize=20, weight="bold", color="white")
        ax.text(1.75, y + h - 0.4, title, ha="left", va="center", fontsize=18, weight="bold", color=color)
        ax.text(1.75, y + 0.68, body, ha="left", va="center", fontsize=15.5, color=INK, family="DejaVu Sans Mono", linespacing=1.4)
        if i < len(steps) - 1:
            ax.annotate("", xy=(6, y - gap + 0.02), xytext=(6, y - 0.02),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=2, mutation_scale=18))
    save(fig, "03-affine-two-equations.png")


if __name__ == "__main__":
    fig_key_space()
    fig_clock()
    fig_brute_force()
    fig_multiply()
    fig_inverses()
    fig_two_equations()
    ct = affine(AFFINE_PLAIN, *AFFINE_KEY)
    print("affine ciphertext:", ct)
    print("26! =", factorial(26), "; years at 1e9/s:", factorial(26) / 1e9 / (365.25 * 24 * 3600))
