"""Figures for Guide 02, Frequency analysis: letter counts, fitting a Caesar shift, chi-squared,
and breaking a substitution with frequencies and common words.

Run from anywhere: ``python guides/scripts/fig_02_frequency_analysis.py``.
Writes PNGs into ``guides/figures/``. Uses only matplotlib, numpy and the standard library.

Both ciphertexts are the guide's worked examples, made from original plaintexts written for
this guide, and are stored here as constants. Running the script also prints the chi-squared
numbers quoted in the guide, so they can be checked.
"""

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Standard published English letter frequencies (percent), A to Z.
ENGLISH_PCT = [
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4,
    6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074,
]

# Worked example 1: a Caesar cipher (152 letters).
CAESAR_CT = (
    "PGPCJXZCYTYRESPMLVPCZYZFCDECPPEDPWWDESPQTCDEWZLQZQESPOLJEZLWLCRPMWLNVNCZHESPNCZHHLTEDZYESP"
    "HTYOZHDTWWLYOALJDHTESLDSTYJMFEEZYESLETEQZFYODZXPHSPCPTYESPEZHY"
)
# Worked example 2: a keyword substitution with the word breaks kept.
SUB_CT = (
    "EV ZSU S OPIW SMW RXEFV MEAKV ZKFM VKF PIW OIPOH EM VKF VPZFT UVPQQFW SV FBSOVIC MEMF. "
    "MPNPWC EM VKF YEIISAF OPXIW TFJFJNFT S VEJF ZKFM VKF OIPOH KSW NFFM ZTPMA, UP VKF QFPQIF "
    "ASVKFTFW EM VKF URXSTF VP UVSTF SV EV. VKF NSHFT USEW VKSV VKF VPZFT ZSU KSXMVFW. VKF "
    "VFSOKFT USEW VKSV VKF AFSTU ZFTF UEJQIC LTPDFM. NXV S UJSII AETI ZEVK S ISMVFTM OIEJNFW "
    "VKF UVSETU SMW LPXMW S MPVF VXOHFW NFVZFFM VKF ZKFFIU. EV USEW VKSV VKF OIPOH ZPXIW UVSTV "
    "SASEM ZKFM UPJFPMF EM VKF YEIISAF VPIW VKF VTXVK."
)
# The order in which the guide recovers the substitution, one step per color.
SUB_STEPS = [
    ("1. VKF = the", {"V": "t", "K": "h", "F": "e"}),
    ("2. S = a", {"S": "a"}),
    ("3. EM = in, ZKFM = when", {"E": "i", "M": "n", "Z": "w"}),
    ("4. was, and, old, clock", {"U": "s", "W": "d", "P": "o", "I": "l", "O": "c", "H": "k"}),
]

BLUE, ORANGE, GREEN, PURPLE = "#3B82F6", "#F97316", "#22C55E", "#A855F7"
RED, YELLOW, TEAL, GREY, INK = "#EF4444", "#FACC15", "#14B8A6", "#9CA3AF", "#1F2937"
LIGHT = {BLUE: "#DBEAFE", ORANGE: "#FFEDD5", GREEN: "#DCFCE7", PURPLE: "#F3E8FF", RED: "#FEE2E2", YELLOW: "#FEF9C3", TEAL: "#CCFBF1", GREY: "#F3F4F6"}
STEP_COLORS = [BLUE, ORANGE, GREEN, PURPLE]

plt.rcParams.update({"font.size": 14, "font.family": "DejaVu Sans", "axes.titlesize": 16, "axes.labelsize": 14})


def letters(text):
    return "".join(c for c in text.upper() if c in ALPHABET)


def caesar_back(text, shift):
    return "".join(ALPHABET[(ALPHABET.index(c) - shift) % 26] for c in text)


def chi_squared(text):
    """Sum over the 26 letters of (observed - expected)^2 / expected."""
    counts = Counter(text)
    n = len(text)
    return sum((counts[c] - n * p / 100) ** 2 / (n * p / 100) for c, p in zip(ALPHABET, ENGLISH_PCT))


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", FIG_DIR / name)


def fig_english_frequencies():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    top = set("ETAOIN")
    colors = [ORANGE if c in top else BLUE for c in ALPHABET]
    ax.bar(range(26), ENGLISH_PCT, color=colors, edgecolor="white")
    ax.set_xticks(range(26))
    ax.set_xticklabels(list(ALPHABET), fontsize=15, family="monospace")
    for i, p in enumerate(ENGLISH_PCT):
        if ALPHABET[i] in top:
            ax.text(i, p + 0.25, f"{p:g}", ha="center", va="bottom", fontsize=12, color=INK)
    ax.set_ylabel("% of letters in English")
    ax.set_ylim(0, 14.5)
    ax.set_xlim(-0.7, 25.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("How often each letter appears in English", fontsize=20, weight="bold", color=INK)
    ax.text(25.5, 13.6, "Commonest six: E T A O I N", ha="right", va="top", fontsize=16, weight="bold", color=ORANGE)
    ax.text(25.5, 12.3, "Rarest: J Q X Z", ha="right", va="top", fontsize=16, weight="bold", color=BLUE)
    save(fig, "02-english-frequencies.png")


def fig_rank_matching():
    """Ciphertext letters sorted by count, next to English letters sorted by frequency."""
    counts = Counter(letters(SUB_CT))
    n = sum(counts.values())
    cipher_sorted = counts.most_common(10)
    english_sorted = sorted(zip(ALPHABET, ENGLISH_PCT), key=lambda x: -x[1])[:10]
    truth = {"F": "E", "V": "T", "S": "A", "K": "H", "M": "N", "E": "I", "P": "O", "I": "L", "W": "D", "T": "R"}
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.6, 10.6)
    ax.axis("off")
    ax.text(1.5, 10.4, "Ciphertext\n(commonest first)", ha="center", va="top", fontsize=17, weight="bold", color=ORANGE)
    ax.text(8.5, 10.4, "English\n(commonest first)", ha="center", va="top", fontsize=17, weight="bold", color=BLUE)
    y_of = {}
    for i, ((c, k), (e, p)) in enumerate(zip(cipher_sorted, english_sorted)):
        y = 8.6 - i * 0.9
        y_of[e] = y
        ax.barh(y, 2.4 * k / n * 100 / 15, left=0.4, height=0.65, color=LIGHT[ORANGE], edgecolor=ORANGE)
        ax.text(0.15, y, c, ha="right", va="center", fontsize=18, weight="bold", family="monospace", color=INK)
        ax.text(0.5, y, f"{100 * k / n:.1f}%", ha="left", va="center", fontsize=12, color=INK)
        ax.barh(y, 2.4 * p / 15, left=10.0 - 2.4 * p / 15 - 0.4, height=0.65, color=LIGHT[BLUE], edgecolor=BLUE)
        ax.text(10.15, y, e, ha="left", va="center", fontsize=18, weight="bold", family="monospace", color=INK)
        ax.text(9.5, y, f"{p:g}%", ha="right", va="center", fontsize=12, color=INK)
    for i, (c, _) in enumerate(cipher_sorted):
        y0 = 8.6 - i * 0.9
        target = truth[c]
        if target in y_of:
            right = y_of[target] == y0
            ax.annotate("", xy=(6.9, y_of[target]), xytext=(3.1, y0),
                        arrowprops=dict(arrowstyle="-|>", lw=2.5, color=GREEN if right else RED, mutation_scale=18))
    ax.text(5, -0.35, "green: rank matches exactly    red: close, but swapped", ha="center", va="center", fontsize=15, color=INK)
    ax.set_title("Matching by rank gets you close, not all the way", fontsize=20, weight="bold", color=INK)
    save(fig, "02-rank-matching.png")


def fig_caesar_slide():
    ct = CAESAR_CT
    shifts = [(0, RED, "shift 0: tall bars miss"), (4, ORANGE, "shift 4: still wrong"), (11, GREEN, "shift 11: bars line up")]
    fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True)
    for ax, (k, color, label) in zip(axes, shifts):
        plain = caesar_back(ct, k)
        counts = Counter(plain)
        pct = [100 * counts[c] / len(plain) for c in ALPHABET]
        ax.bar(range(26), ENGLISH_PCT, color=LIGHT[BLUE], edgecolor=BLUE, width=0.85, label="English")
        ax.bar(range(26), pct, color=color, width=0.45, label="ciphertext, moved back")
        ax.set_ylim(0, 15)
        ax.set_xlim(-0.7, 25.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylabel("%")
        ax.text(0.01, 0.95, label, transform=ax.transAxes, fontsize=18, weight="bold", color=color, va="top")
        ax.text(0.99, 0.95, f"chi-squared = {chi_squared(plain):.1f}", transform=ax.transAxes, fontsize=16,
                ha="right", va="top", color=INK, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=15, frameon=False, bbox_to_anchor=(0.5, 0.965))
    axes[-1].set_xticks(range(26))
    axes[-1].set_xticklabels([c.lower() for c in ALPHABET], fontsize=15, family="monospace")
    fig.suptitle("Slide the ciphertext's bars until they sit on the English bars", fontsize=20, weight="bold", color=INK, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "02-caesar-slide.png")


def fig_chi_by_shift():
    scores = [chi_squared(caesar_back(CAESAR_CT, k)) for k in range(26)]
    best = min(range(26), key=lambda k: scores[k])
    fig, ax = plt.subplots(figsize=(11, 5.8))
    colors = [GREEN if k == best else PURPLE for k in range(26)]
    ax.bar(range(26), scores, color=colors, edgecolor="white")
    ax.set_xticks(range(26))
    ax.set_xticklabels([str(k) for k in range(26)], fontsize=12)
    ax.set_xlabel("shift tried (letters moved back)")
    ax.set_ylim(0, 4700)
    ax.set_ylabel("chi-squared score")
    ax.set_xlim(-0.7, 25.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate(f"shift {best}: score {scores[best]:.1f}\nthe lowest score,\nso most like English", xy=(best, scores[best] + 30),
                xytext=(11, 3800), ha="center", va="bottom", fontsize=15, weight="bold", color=GREEN,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=GREEN),
                arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2.5, mutation_scale=20))
    ax.set_title("The chi-squared score for every Caesar shift", fontsize=20, weight="bold", color=INK)
    save(fig, "02-chi-squared-by-shift.png")
    return scores


def fig_substitution_steps():
    line = SUB_CT[:62]
    fig, ax = plt.subplots(figsize=(12, 7.6))
    n = len(line)
    ax.set_xlim(-0.5, n + 0.5)
    ax.set_ylim(-0.4, 2 * len(SUB_STEPS) + 1.6)
    ax.axis("off")
    known, color_of = {}, {}
    for step, (title, mapping) in enumerate(SUB_STEPS):
        for c, p in mapping.items():
            known[c] = p
            color_of[c] = STEP_COLORS[step]
        y = 2 * (len(SUB_STEPS) - step) - 0.6
        ax.text(-0.3, y + 0.85, title, fontsize=16, weight="bold", color=STEP_COLORS[step], va="center")
        for i, ch in enumerate(line):
            if ch == " ":
                continue
            ax.text(i, y + 0.15, ch, ha="center", va="center", fontsize=13, family="monospace", color="#6B7280")
            if ch in known:
                newest = ch in mapping
                ax.add_patch(Rectangle((i - 0.45, y - 0.72), 0.9, 0.62, facecolor=LIGHT[color_of[ch]] if not newest else color_of[ch],
                                       edgecolor="none"))
                ax.text(i, y - 0.41, known[ch], ha="center", va="center", fontsize=15, family="monospace", weight="bold",
                        color="white" if newest else INK)
            elif ch in ALPHABET:
                ax.text(i, y - 0.41, "·", ha="center", va="center", fontsize=15, family="monospace", color="#9CA3AF")
            else:
                ax.text(i, y - 0.41, ch, ha="center", va="center", fontsize=15, family="monospace", color=INK)
    ax.text(n / 2, 2 * len(SUB_STEPS) + 1.35, "Cracking a substitution, a few letters at a time", ha="center", va="center",
            fontsize=20, weight="bold", color=INK)
    ax.text(n / 2, -0.25, "grey: ciphertext   colored: letters found (darkest = found at this step)   dot: not yet known",
            ha="center", va="center", fontsize=13, color=INK)
    save(fig, "02-substitution-steps.png")


def fig_key_recovered():
    cipher_alpha = "SNOWFLAKEGHIJMPQRTUVXYZBCD"
    fig, ax = plt.subplots(figsize=(12, 3.4))
    ax.set_xlim(-3.0, 26)
    ax.set_ylim(-0.4, 3.1)
    ax.axis("off")
    ax.text(-2.9, 1.85, "plain", fontsize=15, weight="bold", va="center", color=INK)
    ax.text(-2.9, 0.75, "cipher", fontsize=15, weight="bold", va="center", color=INK)
    for i, (p, c) in enumerate(zip(ALPHABET.lower(), cipher_alpha)):
        in_kw = i < 9
        ax.add_patch(Rectangle((i, 1.4), 0.95, 0.9, facecolor=LIGHT[BLUE], edgecolor=BLUE))
        ax.text(i + 0.475, 1.85, p, ha="center", va="center", fontsize=17, family="monospace", color=INK)
        ax.add_patch(Rectangle((i, 0.3), 0.95, 0.9, facecolor=ORANGE if in_kw else LIGHT[ORANGE], edgecolor=ORANGE))
        ax.text(i + 0.475, 0.75, c, ha="center", va="center", fontsize=17, family="monospace", weight="bold",
                color="white" if in_kw else INK)
    ax.text(13, 2.85, "Write the cipher letters under a b c ... z and the keyword appears", ha="center", va="center",
            fontsize=18, weight="bold", color=INK)
    ax.text(4.5, -0.15, "S N O W F L A K E", ha="center", va="center", fontsize=15, weight="bold", color=ORANGE)
    ax.text(17.5, -0.15, "then the unused letters, in order, after E", ha="center", va="center", fontsize=14, color=INK)
    save(fig, "02-key-recovered.png")


if __name__ == "__main__":
    fig_english_frequencies()
    fig_rank_matching()
    fig_caesar_slide()
    scores = fig_chi_by_shift()
    fig_substitution_steps()
    fig_key_recovered()
    print("chi-squared by shift:", [round(s, 1) for s in scores])
