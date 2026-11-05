"""Figures for Guide 08, Scoring and hill climbing.

Writes figures/08-*.png. Re-run from anywhere: ``python scripts/fig_08_scoring_and_hill_climbing.py``.

Most figures need nothing but matplotlib. The two figures drawn from a real hill-climbing
run (08-climb-run.png, 08-snapshots.png, 08-annealing.png) need a table of English
quadgram counts. Point the environment variable QUADGRAMS at such a file: one quadgram and
its count per line, separated by spaces or a tab (plain text or .gz). The file
english_quadgrams.txt from Practical Cryptography works:
http://practicalcryptography.com/cryptanalysis/text-characterisation/quadgrams/
Lines that are not "FOUR_LETTERS count" (a header, for example) are skipped. Without
QUADGRAMS the script draws the other figures and says which it skipped.

The run is seeded, so the same table gives the same pictures. The numbers quoted in the
guide come from this script, run on a table counted from public-domain novels, so a
different table gives slightly different numbers (the shape is the same).
"""

from __future__ import annotations

import gzip
import os
import random
import sys
from math import log10
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
WIDTH = 8.0  # inches: 8 x 200 dpi = 1600 px
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

BLUE, ORANGE, GREEN, RED, PURPLE, GRAY, YELLOW = (
    "#1f77d0", "#ff8c1a", "#2ca02c", "#e0383e", "#8e44ad", "#7f8c8d", "#ffd23f",
)
RUN_COLORS = [BLUE, ORANGE, GREEN, RED, PURPLE, "#16a3a3"]

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

# Log10 probabilities of the quadgrams used in figure 08-quadgram-window, read once from a
# table of about 4.8 million quadgrams counted in public-domain novels (rounded to 0.01).
# "Unseen" quadgrams get the floor value.
SMALL_TABLE = {
    "THEW": -3.05, "HEWI": -3.67, "EWIN": -3.86, "WIND": -3.72,
    "INDB": -4.72, "NDBL": -4.57, "DBLE": -4.84, "BLEW": -4.02,
    "BIED": -5.38, "IEDL": -4.91,
}
SMALL_FLOOR = -7.68
GOOD_PHRASE = "THEWINDBLEW"
BAD_PHRASE = "WTNHBIEDLWE"  # the same eleven letters, shuffled

PLAINTEXT = (
    "The old lighthouse keeper had kept a diary for forty years. Every night he wrote down "
    "the weather, the ships that passed and the strange lights he sometimes saw far out at "
    "sea. When he died, his granddaughter found the diary in a locked chest. Most of it was "
    "ordinary, but the last ten pages were written in a code she had never seen before, and "
    "she was sure they hid a secret."
)
CIPHER_ALPHABET = "QWERTYUIOPASDFGHJKLZXCVBNM"  # plain A->Q, B->W, ... (a made-up key)


SNAPSHOT_STEPS = (250, 500, 1000, 1500, 2000)
CLIMB_SEED, CLIMB_STEPS, RESTARTS = 2, 4000, 6
ANNEAL_SEED, ANNEAL_STEPS, START_T, END_T = 2, 8000, 30.0, 0.3
SUCCESS_TRIALS, SUCCESS_STEPS = 30, 8000


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


# --- Figures that need no data --------------------------------------------------------


def fig_quadgram_window() -> None:
    """Slide a four-letter window along a phrase and show each window's log score."""

    def score_of(phrase):
        grams = [phrase[i:i + 4] for i in range(len(phrase) - 3)]
        return grams, [SMALL_TABLE.get(g, SMALL_FLOOR) for g in grams]

    fig, axes = plt.subplots(2, 1, figsize=(WIDTH, 8.6))
    for ax, phrase, color, label in (
        (axes[0], GOOD_PHRASE, GREEN, "English"),
        (axes[1], BAD_PHRASE, RED, "Same letters, shuffled"),
    ):
        grams, scores = score_of(phrase)
        xs = range(len(grams))
        ax.bar(xs, scores, color=color, width=0.7)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(grams, fontsize=14, family="monospace", rotation=0)
        ax.set_ylim(-8, 0)
        ax.set_ylabel("log score")
        ax.axhline(0, color="black", lw=1)
        total = sum(scores)
        ax.set_title(f"{label}: {phrase}   total {total:.2f}", fontsize=16,
                     family="monospace", color=color, fontweight="bold")
        for x, s in zip(xs, scores):
            ax.text(x, s + 0.3, f"{s:.2f}", ha="center", va="bottom", fontsize=12,
                    color="white", fontweight="bold")
    fig.suptitle("Score every four-letter window, then add the scores up", fontsize=19,
                 fontweight="bold", y=1.0)
    fig.text(0.5, -0.02, "Closer to zero = more English", ha="center", fontsize=15, color=GRAY)
    fig.tight_layout()
    save(fig, "08-quadgram-window.png")


def fig_powers_of_ten() -> None:
    """A number line: each step left is 'divide by 10 once more', i.e. log goes down by 1."""
    fig, ax = plt.subplots(figsize=(WIDTH * 1.25, 5.0))
    values = ["1", "0.1", "0.01", "0.001", "0.0001", "0.00001"]
    for i, v in enumerate(values):
        x = -i
        ax.add_patch(FancyBboxPatch((x - 0.42, 0.55), 0.84, 0.6, boxstyle="round,pad=0.04",
                                    fc="#e8f1fb", ec=BLUE, lw=2))
        ax.text(x, 0.85, v, ha="center", va="center", fontsize=13 if len(v) > 5 else 15,
                fontweight="bold")
        ax.add_patch(FancyBboxPatch((x - 0.42, -0.6), 0.84, 0.6, boxstyle="round,pad=0.04",
                                    fc="#fff1e0", ec=ORANGE, lw=2))
        ax.text(x, -0.3, f"{-i}", ha="center", va="center", fontsize=19, fontweight="bold",
                color="#b35900")
    ax.text(0.65, 0.85, "number", ha="left", va="center", fontsize=15, color=BLUE)
    ax.text(0.65, -0.3, "its log", ha="left", va="center", fontsize=15, color="#b35900")
    ax.text(-2.5, 1.6, "each step left: divide by 10 once more", ha="center", fontsize=15,
            color=GRAY)
    ax.text(-2.5, -1.25,
            "0.001 × 0.01 = 0.00001     becomes     (-3) + (-2) = -5",
            ha="center", fontsize=16, fontweight="bold")
    ax.set_xlim(-5.7, 1.9)
    ax.set_ylim(-1.6, 1.9)
    ax.axis("off")
    ax.set_title("Logs turn multiplying into adding", fontsize=20, fontweight="bold")
    save(fig, "08-powers-of-ten.png")


def fig_landscape() -> None:
    """A hilly landscape: a climber on a small hill cannot see the mountain."""
    import numpy as np

    x = np.linspace(0, 10, 600)
    y = (1.6 * np.exp(-((x - 2.0) ** 2) / 0.6) + 2.4 * np.exp(-((x - 4.6) ** 2) / 0.5)
         + 4.2 * np.exp(-((x - 7.7) ** 2) / 0.9) + 0.9 * np.exp(-((x - 9.4) ** 2) / 0.2) + 0.3)
    fig, ax = plt.subplots(figsize=(WIDTH * 1.2, 5.6))
    ax.fill_between(x, 0, y, color="#cdebc4")
    ax.plot(x, y, color=GREEN, lw=3)

    def mark(xv, text, color, dy=0.35, marker="o"):
        yv = float(np.interp(xv, x, y))
        ax.plot(xv, yv, marker=marker, ms=16, color=color, mec="black", zorder=5)
        ax.text(xv, yv + dy, text, ha="center", va="bottom", fontsize=15, color=color,
                fontweight="bold")

    mark(2.0, "stuck!\n(local top)", RED)
    mark(4.6, "stuck!\n(local top)", RED)
    mark(7.7, "the real answer\n(highest top)", BLUE, marker="*")
    start = 3.2
    ys = float(np.interp(start, x, y))
    ax.plot(start, ys, marker="o", ms=13, color=ORANGE, mec="black", zorder=6)
    ax.annotate("start here,\nonly walk uphill", xy=(start, ys), xytext=(2.6, 3.7),
                fontsize=14, color="#b35900", ha="center",
                arrowprops=dict(arrowstyle="->", color="#b35900", lw=2))
    ax.annotate("", xy=(4.35, float(np.interp(4.35, x, y)) + 0.1),
                xytext=(3.45, float(np.interp(3.45, x, y)) + 0.1),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("all the possible keys, laid out side by side")
    ax.set_ylabel("score (how English)")
    ax.set_title("Hill climbing can get stuck on a small hill", fontsize=20, fontweight="bold")
    save(fig, "08-landscape.png")


# --- The real run ------------------------------------------------------------------


def load_quadgrams(path: str):
    """A flat list of log10 probabilities indexed in base 26, and the floor for unseen ones."""
    opener = gzip.open if path.endswith(".gz") else open
    counts = {}
    with opener(path, "rt") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and len(parts[0]) == 4 and parts[0].isalpha() and parts[1].isdigit():
                counts[parts[0].upper()] = int(parts[1])
    if not counts:
        raise SystemExit(f"QUADGRAMS={path} holds no 'ABCD 123' lines")
    total = sum(counts.values())
    floor = log10(0.1 / total)
    table = [floor] * 26**4
    for gram, n in counts.items():
        a, b, c, d = (ord(ch) - 65 for ch in gram)
        table[((a * 26 + b) * 26 + c) * 26 + d] = log10(n / total)
    return table, floor, total


def make_scorer(table):
    def score(values):
        total = 0.0
        index = values[0] * 676 + values[1] * 26 + values[2]
        for v in values[3:]:
            index = (index * 26 + v) % 456976
            total += table[index]
        return total

    return score


def encrypt(text: str) -> str:
    return "".join(CIPHER_ALPHABET[ord(c) - 65] for c in text.upper() if c.isalpha())


def decrypt(cipher_values, key):
    """key[c] is the plain letter (0-25) that cipher letter c stands for."""
    return [key[c] for c in cipher_values]


def climb(cipher_values, score, rng, *, steps):
    key = list(range(26))
    rng.shuffle(key)
    best = score(decrypt(cipher_values, key))
    trace, snapshots = [best], {0: list(key)}
    for step in range(1, steps + 1):
        i, j = rng.sample(range(26), 2)
        key[i], key[j] = key[j], key[i]
        value = score(decrypt(cipher_values, key))
        if value > best:
            best = value
        else:
            key[i], key[j] = key[j], key[i]
        trace.append(best)
        if step in SNAPSHOT_STEPS or step == steps:
            snapshots[step] = list(key)
    return key, best, trace, snapshots


def anneal(cipher_values, score, rng, *, steps, start_t, end_t):
    """Accept a worse key with chance 10 ** (change / temperature): the guide's form."""
    key = list(range(26))
    rng.shuffle(key)
    current = score(decrypt(cipher_values, key))
    best, best_key = current, list(key)
    ratio = (end_t / start_t) ** (1 / steps)
    t = start_t
    trace, temps = [current], [t]
    for _ in range(steps):
        i, j = rng.sample(range(26), 2)
        key[i], key[j] = key[j], key[i]
        value = score(decrypt(cipher_values, key))
        change = value - current
        if change >= 0 or rng.random() < 10 ** (change / t):
            current = value
            if value > best:
                best, best_key = value, list(key)
        else:
            key[i], key[j] = key[j], key[i]
        t *= ratio
        trace.append(current)
        temps.append(t)
    return best_key, best, trace, temps


def as_text(values) -> str:
    return "".join(ALPHABET[v] for v in values).lower()


def real_run_figures(path: str) -> None:
    table, floor, total = load_quadgrams(path)
    score = make_scorer(table)
    cipher = encrypt(PLAINTEXT)
    cv = [ord(c) - 65 for c in cipher]
    plain_values = [ord(c) - 65 for c in PLAINTEXT.upper() if c.isalpha()]
    true_score = score(plain_values)
    print(f"quadgrams in table: {total}; letters: {len(cv)}; quadgrams in text: {len(cv) - 3}")
    print("ciphertext:", cipher)
    print(f"true plaintext score: {true_score:.1f} (per quadgram {true_score / (len(cv) - 3):.2f})")
    print(f"ciphertext as if plain: {score(cv):.1f}")

    steps, restarts = CLIMB_STEPS, RESTARTS
    rng = random.Random(CLIMB_SEED)
    runs = [climb(cv, score, rng, steps=steps) for _ in range(restarts)]
    for n, (key, best, trace, _) in enumerate(runs, 1):
        print(f"restart {n}: final {best:.1f}  {as_text(decrypt(cv, key))[:60]}")

    # Score against iteration, every restart.
    fig, ax = plt.subplots(figsize=(WIDTH * 1.2, 6.0))
    for n, (key, best, trace, _) in enumerate(runs):
        solved = abs(best - true_score) < 1e-6
        ax.plot(trace, color=RUN_COLORS[n % len(RUN_COLORS)], lw=3 if solved else 2,
                label=f"restart {n + 1}" + (" (solved)" if solved else " (stuck)"))
    ax.axhline(true_score, color="black", ls="--", lw=1.5)
    ax.text(steps * 0.78, true_score - 18, "score of the real message", ha="center",
            va="top", fontsize=14)
    ax.set_xlabel("iteration (one swap tried per iteration)")
    ax.set_ylabel("score of the best key so far")
    ax.set_title("A real hill climb on a substitution cipher", fontsize=20, fontweight="bold")
    ax.legend(loc="lower right", fontsize=13)
    ax.set_xlim(0, steps)
    save(fig, "08-climb-run.png")

    # What the "plaintext" looks like along the best restart.
    best_run = next(r for r in runs if abs(r[1] - true_score) < 1e-6)
    snaps = best_run[3]
    lines = []
    for step in sorted(snaps):
        key = snaps[step]
        values = decrypt(cv, key)
        lines.append((step, score(values), as_text(values)[:44]))
    fig, ax = plt.subplots(figsize=(WIDTH * 1.25, 0.8 + 0.62 * len(lines)))
    ax.axis("off")
    for row, (step, value, text) in enumerate(lines):
        y = 1 - (row + 0.5) / len(lines)
        shade = row / max(len(lines) - 1, 1)
        color = (0.88 - 0.7 * shade, 0.25 + 0.45 * shade, 0.2)
        ax.text(0.0, y, f"step {step:>4}", fontsize=15, fontweight="bold", va="center",
                transform=ax.transAxes)
        ax.text(0.17, y, f"{value:7.0f}", fontsize=15, va="center", color=color,
                fontweight="bold", transform=ax.transAxes)
        ax.text(0.31, y, text, fontsize=15, va="center", family="monospace",
                transform=ax.transAxes)
        print(f"snapshot step {step}: {value:.1f} {text}")
    ax.text(0.17, 1.03, "score", fontsize=14, color=GRAY, transform=ax.transAxes)
    ax.text(0.31, 1.03, "first 44 letters of the decryption", fontsize=14, color=GRAY,
            transform=ax.transAxes)
    ax.set_title("Gibberish turns into English as the score climbs", fontsize=19,
                 fontweight="bold", pad=40)
    save(fig, "08-snapshots.png")

    # Simulated annealing on the same ciphertext.
    a_key, a_best, a_trace, temps = anneal(cv, score, random.Random(ANNEAL_SEED),
                                           steps=ANNEAL_STEPS, start_t=START_T, end_t=END_T)
    print(f"annealing final best {a_best:.1f}: {as_text(decrypt(cv, a_key))[:60]}")
    fig, ax = plt.subplots(figsize=(WIDTH * 1.2, 6.0))
    ax.plot(a_trace, color=PURPLE, lw=1.2, label="score of the current key")
    ax.axhline(true_score, color="black", ls="--", lw=1.5)
    ax.text(len(a_trace) * 0.6, true_score - 18, "score of the real message", ha="center",
            va="top", fontsize=14)
    ax.set_xlabel("iteration")
    ax.set_ylabel("score")
    ax.set_xlim(0, len(a_trace))
    ax2 = ax.twinx()
    ax2.plot(temps, color=ORANGE, lw=3, label="temperature")
    ax2.set_ylabel("temperature", color="#b35900")
    ax2.tick_params(axis="y", colors="#b35900")
    ax2.spines["right"].set_visible(True)
    ax2.set_ylim(0, max(temps) * 1.05)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=13)
    ax.set_title("Simulated annealing: wobbly while hot, steady when cold", fontsize=19,
                 fontweight="bold")
    save(fig, "08-annealing.png")

    # How often each method finds the answer from one random start, same budget.
    rng = random.Random(100)
    solved_climb = sum(abs(climb(cv, score, rng, steps=SUCCESS_STEPS)[1] - true_score) < 0.1
                       for _ in range(SUCCESS_TRIALS))
    solved_anneal = sum(
        abs(anneal(cv, score, random.Random(1000 + s), steps=SUCCESS_STEPS, start_t=START_T,
                   end_t=END_T)[1] - true_score) < 0.1
        for s in range(SUCCESS_TRIALS))
    print(f"from one random start, {SUCCESS_STEPS} swaps: hill climbing solved "
          f"{solved_climb}/{SUCCESS_TRIALS}, annealing solved {solved_anneal}/{SUCCESS_TRIALS}")


def main() -> None:
    fig_quadgram_window()
    fig_powers_of_ten()
    fig_landscape()
    path = os.environ.get("QUADGRAMS")
    if not path:
        print("QUADGRAMS is not set: skipped 08-climb-run.png, 08-snapshots.png and "
              "08-annealing.png. Set it to a quadgram count file (see this script's "
              "docstring).", file=sys.stderr)
        return
    if not Path(path).is_file():
        raise SystemExit(f"QUADGRAMS={path} is not a file")
    real_run_figures(path)


if __name__ == "__main__":
    main()
