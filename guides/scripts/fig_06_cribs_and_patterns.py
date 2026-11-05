"""Figures for Guide 06, Cribs and patterns.

Run from anywhere: ``python guides/scripts/fig_06_cribs_and_patterns.py``.
Writes every figure of the guide to ``guides/figures/06-*.png`` (200 dpi, about 1600 px wide).
Uses only matplotlib and the standard library. The worked-example texts, keys and the
short candidate word lists (taken from a list of the 5,000 commonest English words) live
in this file, and the script checks them before drawing.
"""

from pathlib import Path
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "figures"
DPI = 200
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

BLUE, ORANGE, GREEN, PINK, PURPLE, YELLOW, GREY = (
    "#2b7bff", "#ff8a00", "#1db954", "#ff3d7f", "#8e44ff", "#ffd23f", "#9aa0a6")
LIGHT_GREY, RED, DARK = "#e3e6ea", "#e53935", "#222222"
PATTERN_COLORS = ["#ff6b6b", "#ffb347", "#ffe066", "#6bd968", "#5cc8ff", "#b28dff", "#ff9ecf"]

# --- Worked example 1: a keyword substitution with word breaks -------------------------
SUB_PLAIN = (
    "dear tom, the letter you found is from the keeper. he hid a second letter under the "
    "bell in the old chapel. meet me there at seven and bring a lamp. eleanor"
)
SUB_KEYWORD = "GUARDIAN"

# --- Worked example 2: a Vigenere cipher and a probable word ---------------------------
VIG_PLAIN = (
    "at nine the professor left the museum by the east door. the map is hidden inside the "
    "clock in his study. find it before the guards return at dawn"
)
VIG_KEY = "FALCON"
VIG_CRIB = "PROFESSOR"

# --- Worked example 3: a columnar transposition and a known word ------------------------
TRANS_PLAIN = (
    "the submarine will surface near the north pier soon after dark. bring the signal lamp "
    "and wait by the old crane"
)
TRANS_KEY = "CORAL"
TRANS_CRIB = "SUBMARINE"

# --- Enigma illustration: a made-up ciphertext and the WETTERVORHERSAGE crib ------------
ENIGMA_CRIB = "WETTERVORHERSAGE"
ENIGMA_SEED = 11
ENIGMA_LENGTH = 30

plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 19, "axes.labelsize": 16, "xtick.labelsize": 14,
    "ytick.labelsize": 14, "legend.fontsize": 14, "figure.facecolor": "white",
    "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
})


# --- Ciphers and helpers ---------------------------------------------------------------


def letters(text):
    return "".join(c for c in text.upper() if c in ALPHABET)


def pattern(word):
    """Label each letter by order of first appearance: THAT -> ABCA."""
    labels = {}
    return "".join(labels.setdefault(c, ALPHABET[len(labels)]) for c in word.upper())


def keyword_alphabet(keyword):
    """Keyword without repeats, then the alphabet carrying on after its last letter."""
    seen = list(dict.fromkeys(letters(keyword)))
    start = ALPHABET.index(seen[-1]) + 1
    return "".join(seen + [c for c in ALPHABET[start:] + ALPHABET[:start] if c not in seen])


def substitute(text, cipher_alphabet):
    return text.upper().translate(str.maketrans(ALPHABET, cipher_alphabet))


def vigenere(text, key):
    k = [ALPHABET.index(c) for c in key]
    return "".join(ALPHABET[(ALPHABET.index(c) + k[i % len(k)]) % 26] for i, c in enumerate(text))


def subtract(cipher, crib):
    """Key fragment = cipher minus crib, letter by letter, wrapping round the alphabet."""
    return "".join(ALPHABET[(ALPHABET.index(c) - ALPHABET.index(p)) % 26] for c, p in zip(cipher, crib))


def columnar(text, keyword):
    order = sorted(range(len(keyword)), key=lambda i: (keyword[i], i))
    width = len(keyword)
    text += "X" * (-len(text) % width)
    return "".join(text[i::width] for i in order)


def crib_pairs(crib, width):
    return [crib[i] + crib[i + width] for i in range(len(crib) - width)]


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def tile(ax, x, y, ch, color, *, w=0.92, h=0.92, size=18, text_color=DARK, weight="bold"):
    ax.add_patch(Rectangle((x, y), w, h, color=color))
    ax.text(x + w / 2, y + h / 2, ch, ha="center", va="center", fontsize=size,
            family="monospace", weight=weight, color=text_color)


SUB_ALPHABET = keyword_alphabet(SUB_KEYWORD)
SUB_CIPHER = substitute(SUB_PLAIN, SUB_ALPHABET)
VIG_CIPHER = vigenere(letters(VIG_PLAIN), VIG_KEY)
TRANS_CIPHER = columnar(letters(TRANS_PLAIN), TRANS_KEY)

# Candidate lists from the 5,000 commonest English words, checked here.
CANDIDATES = {
    "ABBCBD": ["SEEMED", "ASSIST", "DEEPER", "KEEPER", "PEERED"],
    "ABCCBD": ["BETTER", "LETTER", "BENNET", "COMMON", "FOLLOW", "MORROW", "BOTTOM",
               "HOLLOW", "SORROW", "BEGGED", "HANNAY", "VESSEL", "COTTON"],
}
for _p, _words in CANDIDATES.items():
    assert all(pattern(w) == _p for w in _words), _p


# --- Figures ---------------------------------------------------------------------------


def fig_crib_idea():
    """The substitution ciphertext as word tiles, with three cribs written under them."""
    words = [w.strip(",.") for w in SUB_CIPHER.split()]
    plain = [w.strip(",.").upper() for w in SUB_PLAIN.split()]
    cribs = {0: ("dear", GREEN), 1: ("tom", GREEN), 2: ("the", BLUE), 8: ("the", BLUE),
             len(words) - 1: ("eleanor", PINK)}
    for i, (c, p) in enumerate(zip(words, plain)):
        if i in cribs:
            assert substitute(cribs[i][0], SUB_ALPHABET) == c, (c, p)
    fig, ax = plt.subplots(figsize=(8, 5.4))
    x, y, max_x = 0.0, 0.0, 20.5
    for i, word in enumerate(words):
        w = 0.55 * len(word) + 0.3
        if x + w > max_x:
            x, y = 0.0, y - 1.7
        color = cribs[i][1] if i in cribs else LIGHT_GREY
        ax.add_patch(FancyBboxPatch((x, y), w, 0.8, boxstyle="round,pad=0.04",
                                    color=color, alpha=0.35 if i in cribs else 1))
        ax.text(x + w / 2, y + 0.4, word, ha="center", va="center", fontsize=14,
                family="monospace", weight="bold")
        if i in cribs:
            ax.text(x + w / 2, y - 0.35, cribs[i][0], ha="center", va="center", fontsize=15,
                    family="monospace", weight="bold", color=cribs[i][1])
        x += w + 0.25
    legend_y = y - 1.6
    for k, (label, col) in enumerate([
        ("a greeting: letters often start 'dear ...'", GREEN),
        ("the commonest word in English", BLUE),
        ("a name you know from an earlier message", PINK),
    ]):
        yy = legend_y - 0.75 * k
        ax.add_patch(Rectangle((0, yy - 0.25), 0.6, 0.5, color=col, alpha=0.6))
        ax.text(0.9, yy, label, va="center", fontsize=15)
    ax.set_xlim(-0.3, max_x + 0.3)
    ax.set_ylim(legend_y - 2.0, 1.2)
    ax.axis("off")
    ax.set_title("A crib is a guess at a piece of the plaintext", fontsize=19)
    save(fig, "06-crib-idea.png")


def fig_word_patterns():
    words = ["THAT", "LETTER", "PEOPLE", "KEEPER", "SEVEN", "ELEANOR"]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    for r, word in enumerate(words):
        y = -r * 1.25
        colors = {}
        for j, ch in enumerate(word):
            col = colors.setdefault(ch, PATTERN_COLORS[len(colors)])
            tile(ax, j, y, ch, col)
        ax.text(8.3, y + 0.46, pattern(word), va="center", fontsize=22, family="monospace",
                weight="bold", color=PURPLE)
        ax.annotate("", xy=(8.1, y + 0.46), xytext=(len(word) + 0.2, y + 0.46),
                    arrowprops=dict(arrowstyle="->", lw=2, color=GREY))
    ax.text(0, 1.35, "word", fontsize=16, weight="bold")
    ax.text(8.3, 1.35, "pattern", fontsize=16, weight="bold", color=PURPLE)
    ax.set_xlim(-0.3, 12.6)
    ax.set_ylim(-6.7, 2.0)
    ax.axis("off")
    ax.set_title("Same letter, same color: a word's pattern survives substitution", fontsize=17)
    save(fig, "06-word-patterns.png")


def fig_pattern_lookup():
    """SDDYDB -> ABBCBD -> five candidates -> only KEEPER fits the letters already known."""
    cipher_word = "SDDYDB"
    assert pattern(cipher_word) == "ABBCBD"
    known = {"D": "E", "B": "R"}  # cipher -> plain, found from the cribs
    used_plain = {"D"}  # plain d is already taken by cipher R (from "dear")
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for j, ch in enumerate(cipher_word):
        tile(ax, j, 3.2, ch, LIGHT_GREY)
        ax.text(j + 0.46, 2.85, known.get(ch, "?").lower(), ha="center", va="top", fontsize=18,
                family="monospace", weight="bold", color=GREEN if ch in known else GREY)
    ax.text(6.4, 3.66, "ciphertext word", va="center", fontsize=15)
    ax.text(6.4, 2.55, "letters already known", va="center", fontsize=15, color=GREEN)
    ax.text(0, 1.55, f"pattern {pattern(cipher_word)}: common words that fit", fontsize=16,
            weight="bold", color=PURPLE)
    verdicts = []
    for w in CANDIDATES["ABBCBD"]:
        fits = all(w[i] == known[c] for i, c in enumerate(cipher_word) if c in known)
        if not fits:
            verdicts.append((w, "wrong letters", RED))
        elif set(w) & used_plain:
            verdicts.append((w, "d is already taken", ORANGE))
        else:
            verdicts.append((w, "fits!", GREEN))
    for k, (w, why, col) in enumerate(verdicts):
        y = 0.6 - k * 0.8
        ax.text(0.2, y, w.lower(), fontsize=19, family="monospace", weight="bold", color=col,
                va="center")
        ax.text(3.6, y, why, fontsize=15, color=col, va="center")
        if col != GREEN:
            ax.plot([0.1, 2.15], [y, y], color=col, lw=2.5)
    ax.set_xlim(-0.3, 11)
    ax.set_ylim(-3.6, 4.4)
    ax.axis("off")
    ax.set_title("Look the pattern up, then cross out what clashes", fontsize=18)
    save(fig, "06-pattern-lookup.png")


def fig_keyword_alphabet():
    plain_used = set(letters(SUB_PLAIN))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    w = 0.6
    rows = [("plain", 2.4), ("found", 1.4), ("rebuilt", 0.0)]
    kw = list(dict.fromkeys(SUB_KEYWORD))
    for i, p in enumerate(ALPHABET):
        x = i * w
        tile(ax, x, 2.4, p.lower(), "#f4f5f7", w=w * 0.92, h=0.8, size=13, weight="normal")
        c = SUB_ALPHABET[i]
        if p in plain_used:
            tile(ax, x, 1.4, c, "#bcd7ff", w=w * 0.92, h=0.8, size=13)
        else:
            tile(ax, x, 1.4, "?", LIGHT_GREY, w=w * 0.92, h=0.8, size=13, text_color=GREY)
        col = PINK if i < len(kw) else "#c8f0c8"
        text_col = ORANGE if p not in plain_used else DARK
        tile(ax, x, 0.0, c, col, w=w * 0.92, h=0.8, size=13, text_color=text_col)
    for label, y in rows:
        ax.text(-0.25, y + 0.4, label, ha="right", va="center", fontsize=14)
    ax.annotate(f"keyword part: {''.join(kw)}, which is GUARDIAN with its second A dropped",
                xy=(len(kw) * w / 2, -0.05), xytext=(0.0, -1.0), fontsize=14, color=PINK,
                weight="bold", arrowprops=dict(arrowstyle="->", color=PINK, lw=2, relpos=(0.08, 1.0)))
    ax.text(0.0, -1.55,
            "then the rest of the alphabet in order (O P Q S T V ...), skipping the keyword's\n"
            "letters. The orange letters were never seen, but the order gives them away.",
            fontsize=14, va="top", color="#2e7d32")
    ax.set_xlim(-1.6, 26 * w + 0.2)
    ax.set_ylim(-2.8, 3.6)
    ax.axis("off")
    ax.set_title("21 letters found by cribs; the alphabet's order gives the other 5", fontsize=17)
    save(fig, "06-keyword-alphabet.png")


def fig_crib_subtract():
    """Cipher minus crib, column by column, for the right position."""
    start = letters(VIG_PLAIN).find(VIG_CRIB)
    window = VIG_CIPHER[start:start + len(VIG_CRIB)]
    frag = subtract(window, VIG_CRIB)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for j, (c, p, k) in enumerate(zip(window, VIG_CRIB, frag)):
        x = j * 1.05
        tile(ax, x, 2.8, c, "#bcd7ff")
        ax.text(x + 0.46, 2.72, str(ALPHABET.index(c)), ha="center", va="top", fontsize=13)
        tile(ax, x, 1.0, p.lower(), "#c8f0c8")
        ax.text(x + 0.46, 0.92, str(ALPHABET.index(p)), ha="center", va="top", fontsize=13)
        tile(ax, x, -0.9, k, YELLOW)
        diff = ALPHABET.index(c) - ALPHABET.index(p)
        ax.text(x + 0.46, -1.15, f"{diff}" if diff >= 0 else f"{diff}\n+26", ha="center",
                va="top", fontsize=11, color=PURPLE)
    for label, y in [("ciphertext", 3.26), ("crib", 1.46), ("key", -0.44)]:
        ax.text(-0.2, y, label, ha="right", va="center", fontsize=15, weight="bold")
    ax.text(-0.2, 2.15, "minus", ha="right", va="center", fontsize=14, color=PURPLE)
    ax.text(-0.2, 0.35, "equals", ha="right", va="center", fontsize=14, color=PURPLE)
    ax.text(4.7, -2.45, f"The key fragment reads {frag}: the word FALCON, going round and round.",
            ha="center", fontsize=14, weight="bold")
    ax.set_xlim(-2.6, 9.6)
    ax.set_ylim(-2.8, 4.0)
    ax.axis("off")
    ax.set_title("Cipher letter minus crib letter gives the key letter (A=0 ... Z=25)",
                 fontsize=16)
    save(fig, "06-crib-subtract.png")


def fig_crib_drag():
    rows = [(i + 1, VIG_CIPHER[i:i + len(VIG_CRIB)],
             subtract(VIG_CIPHER[i:i + len(VIG_CRIB)], VIG_CRIB)) for i in range(14)]
    hit = letters(VIG_PLAIN).find(VIG_CRIB) + 1
    fig, ax = plt.subplots(figsize=(8, 6.6))
    for x, head in [(0.2, "position"), (3.2, "ciphertext\nunder the crib"),
                    (7.8, "key fragment\n(cipher minus crib)")]:
        ax.text(x, 14.7, head, fontsize=14, weight="bold", ha="center", va="bottom")
    for pos, window, frag in rows:
        y = 15 - pos
        good = pos == hit
        if good:
            ax.add_patch(Rectangle((-0.6, y - 0.42), 11.4, 0.84, color="#c8f0c8"))
        ax.text(0.2, y, str(pos), ha="center", va="center", fontsize=15,
                weight="bold" if good else "normal")
        ax.text(3.2, y, window, ha="center", va="center", fontsize=16, family="monospace")
        ax.text(7.8, y, frag, ha="center", va="center", fontsize=17, family="monospace",
                weight="bold" if good else "normal", color="#1b7f3a" if good else GREY)
    ax.text(10.9, 15 - hit, "readable!", va="center", fontsize=15, color="#1b7f3a",
            weight="bold")
    ax.text(5.2, -0.4, f"crib = {VIG_CRIB.lower()}, slid one letter at a time", ha="center",
            fontsize=15, color=PURPLE)
    ax.set_xlim(-0.8, 12.6)
    ax.set_ylim(-1.0, 16.4)
    ax.axis("off")
    ax.set_title("Crib dragging: slide the probable word along the ciphertext", fontsize=17)
    save(fig, "06-crib-drag.png")


def fig_transposition_grids():
    fig, axes = plt.subplots(1, 3, figsize=(8, 4.6), gridspec_kw=dict(wspace=0.15))
    for ax, width in zip(axes, (3, 4, 5)):
        pairs = crib_pairs(TRANS_CRIB, width)
        found = [p in TRANS_CIPHER for p in pairs]
        for i, ch in enumerate(TRANS_CRIB):
            r, c = divmod(i, width)
            tile(ax, c, -r * 1.4, ch, "#dfe9f7", size=17)
        for i, ok in enumerate(found):
            r, c = divmod(i, width)
            ax.plot([c + 0.46, c + 0.46], [-r * 1.4 - 0.02, -r * 1.4 - 0.46], lw=6,
                    color=GREEN if ok else RED, solid_capstyle="butt")
        n_rows = (len(TRANS_CRIB) - 1) // width + 1
        y_text = -(n_rows - 1) * 1.4 - 0.4
        ax.text(width / 2, y_text, f"width {width}", ha="center", va="top", fontsize=17,
                weight="bold")
        ax.text(width / 2, y_text - 0.9, f"{sum(found)} of {len(pairs)} pairs\nin the ciphertext",
                ha="center", va="top", fontsize=14,
                color="#1b7f3a" if all(found) else RED)
        ax.set_xlim(-0.4, 5.4)
        ax.set_ylim(-6.9, 1.2)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("Write the crib in rows: letters stacked in a column\nmust sit side by side "
                 "in the ciphertext (green bar: found, red: missing)", fontsize=15, y=1.02)
    save(fig, "06-transposition-grids.png")


def fig_width_scores():
    widths = range(2, 8)
    scores = []
    for w in widths:
        pairs = crib_pairs(TRANS_CRIB, w)
        scores.append((w, sum(p in TRANS_CIPHER for p in pairs), len(pairs)))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar([w for w, _, _ in scores], [f / n for _, f, n in scores],
           color=[PINK if f == n and n >= 3 else BLUE for _, f, n in scores])
    for w, f, n in scores:
        ax.text(w, f / n + 0.02, f"{f} of {n}", ha="center", fontsize=15)
    ax.set_xticks(list(widths))
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("guessed number of columns (width)")
    ax.set_ylabel("share of crib pairs found")
    ax.set_title(f"Crib \"{TRANS_CRIB.lower()}\" against a 90-letter columnar transposition", pad=16)
    ax.text(7, 0.62, "only 2 pairs\nto test:\nweak evidence", fontsize=13,
            ha="center", va="bottom", color=GREY)
    save(fig, "06-width-scores.png")


def enigma_ciphertext():
    rng = random.Random(ENIGMA_SEED)
    return "".join(rng.choice(ALPHABET) for _ in range(ENIGMA_LENGTH))


def fig_enigma_slide():
    c = enigma_ciphertext()
    n_pos = len(c) - len(ENIGMA_CRIB) + 1
    fig, ax = plt.subplots(figsize=(8, 7.2))
    s = 0.5
    for j, ch in enumerate(c):
        tile(ax, j * s, 1.0, ch, "#bcd7ff", w=s * 0.9, h=s * 0.9, size=11)
    ax.text(-0.15, 1.0 + s * 0.45, "made-up\nciphertext", ha="right", va="center", fontsize=12)
    survivors = 0
    for pos in range(n_pos):
        y = -pos * s * 1.05
        clashes = [j for j, ch in enumerate(ENIGMA_CRIB) if c[pos + j] == ch]
        survivors += not clashes
        for j, ch in enumerate(ENIGMA_CRIB):
            col = RED if j in clashes else ("#eceff1" if clashes else "#c8f0c8")
            tile(ax, (pos + j) * s, y, ch, col, w=s * 0.9, h=s * 0.9, size=11,
                 text_color="white" if j in clashes else DARK)
        ax.text(-0.15, y + s * 0.45, f"{pos + 1}", ha="right", va="center", fontsize=12)
        ax.text(len(c) * s + 0.15, y + s * 0.45, "ruled out" if clashes else "possible",
                va="center", fontsize=12, color=RED if clashes else "#1b7f3a",
                weight="normal" if clashes else "bold")
    ax.set_xlim(-1.6, len(c) * s + 2.2)
    ax.set_ylim(-n_pos * s * 1.05 - 0.3, 1.8)
    ax.axis("off")
    ax.set_title("Enigma never turned a letter into itself, so a red match\nrules a position "
                 f"out ({n_pos - survivors} of {n_pos} here)", fontsize=15)
    save(fig, "06-enigma-slide.png")
    return c, n_pos, survivors


if __name__ == "__main__":
    fig_crib_idea()
    fig_word_patterns()
    fig_pattern_lookup()
    fig_keyword_alphabet()
    fig_crib_subtract()
    fig_crib_drag()
    fig_transposition_grids()
    fig_width_scores()
    print("enigma:", fig_enigma_slide())
    print("substitution ciphertext:", SUB_CIPHER)
    print("vigenere ciphertext:", " ".join(VIG_CIPHER[i:i + 5] for i in range(0, len(VIG_CIPHER), 5)))
    print("transposition ciphertext:", TRANS_CIPHER)
