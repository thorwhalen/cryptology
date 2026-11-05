"""Figures for Guide 01, Reading the clues: what a ciphertext tells you before you attack it.

Run from anywhere: ``python guides/scripts/fig_01_reading_the_clues.py``.
Writes PNGs into ``guides/figures/``. Uses only matplotlib, numpy and the standard library.

The six mystery messages are the guide's worked example: one original plaintext (written for
this guide) put through six different ciphers. They are stored here as constants so the
figures can be rebuilt without any cipher library.
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

PLAIN = (
    "THELIGHTHOUSEKEEPERCOUNTEDTHESHIPSEVERYEVENINGANDWROTETHEIRNAMESINASMALLGREENBOOK"
    "ONENIGHTASHIPWITHNONAMEANDNOLIGHTSSLIPPEDPASTTHEROCKSANDVANISHEDINTOTHEFOGBEFOREDAWN"
)
MYSTERY = {
    "A": "AOLSPNOAOVBZLRLLWLYJVBUALKAOLZOPWZLCLYFLCLUPUNHUKDYVALAOLPYUHTLZPUHZTHSSNYLLUIVVRVULUPNOAHZOPWDPAOUVUHTLHUKUVSPNOAZZSPWWLKWHZAAOLYVJRZHUKCHUPZOLKPUAVAOLMVNILMVYLKHDU",
    "B": "ETEENHPRNNTIESGBNHIHMNHIPHKVHTFFALHKRTESYIDERSMROETPNEOTPAESAEOOOWHHSPUTIEEAOEMALNOGHTADGLDTCDSNEEDIOECESEENWTNIAEONAWOALSPSRANDTGRNTGUEODHVVGRHANLEKISINNISETONIIHBE",
    "C": "YVKQWMMHNTIYJYKJDKWQUZBZJRZMSYMWVXSBJFEJJKSWTLOTIKXTHKYVKNFTFAKXWTFGSFZRLFKJBHTCQTBKSWMMHGXVOUKOYVTTBGRSGSRTTZOLVZXGRNDVJRVFGZYVKWCIPGGSRBFBOXVKIWTYCZMSLTUHJTUWSJFKT",
    "E": "PBLSNCBPAHPTDLLRCSLEGHZUSFFQRCPRPVXLXCBXCXGLKIDOKGXABUFSRCLHKOLFPLKOTLRKNEELGLOHANGUGLNCBPRQCPQVMPOIGUBKDRKGUGMKCOUTXSPVSCCQRQSYPBLEHGLQOKCWOKLPRCCKMUBURCGBFOFGHBFEDALZ",
    "F": "IUEYVSUIUCJHEXEEDEGNCJBIETIUEHUVDHEKEGPEKEBVBSLBTMGCIEIUEVGBLZEHVBLHZLYYSGEEBACCXCBEBVSUILHUVDMVIUBCBLZELBTBCYVSUIHHYVDDETDLHIIUEGCNXHLBTKLBVHUETVBICIUERCSAERCGETLMB",
}

BLUE, ORANGE, GREEN, PURPLE = "#3B82F6", "#F97316", "#22C55E", "#A855F7"
RED, YELLOW, TEAL, GREY, INK = "#EF4444", "#FACC15", "#14B8A6", "#9CA3AF", "#1F2937"
LIGHT = {BLUE: "#DBEAFE", ORANGE: "#FFEDD5", GREEN: "#DCFCE7", PURPLE: "#F3E8FF", RED: "#FEE2E2", YELLOW: "#FEF9C3", TEAL: "#CCFBF1", GREY: "#F3F4F6"}

plt.rcParams.update({"font.size": 14, "font.family": "DejaVu Sans", "axes.titlesize": 16, "axes.labelsize": 14})


def ioc(text):
    """Index of coincidence: the chance that two letters picked at random are the same."""
    counts = Counter(text)
    n = sum(counts.values())
    return sum(f * (f - 1) for f in counts.values()) / (n * (n - 1))


def percents(text):
    counts = Counter(text)
    return [100 * counts[c] / len(text) for c in ALPHABET]


def groups(text, n=5):
    return " ".join(text[i:i + n] for i in range(0, len(text), n))


def box(ax, x, y, w, h, text, color, *, size=14, weight="normal", text_color=INK, round_=0.02):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={round_}",
                                facecolor=LIGHT.get(color, color), edgecolor=color, linewidth=2.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, weight=weight,
            color=text_color, wrap=True, linespacing=1.3)


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", FIG_DIR / name)


def fig_clue_board():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.97, "Six clues to read before you try any key", ha="center", va="top", fontsize=22, weight="bold", color=INK)
    sample = groups(MYSTERY["A"][:40])
    box(ax, 0.02, 0.72, 0.96, 0.13, sample, GREY, size=16, weight="bold")
    ax.text(0.5, 0.70, "a mystery ciphertext: measure it six ways", ha="center", va="top", fontsize=15, color="#4B5563", style="italic")
    ax.annotate("", xy=(0.5, 0.595), xytext=(0.5, 0.655), arrowprops=dict(arrowstyle="-|>", color=INK, lw=3, mutation_scale=28))
    cards = [
        ("1. Which symbols?", "letters, digits, dots,\nonly A D F G V X ...", BLUE),
        ("2. How long?", "even or odd,\nand its factors", ORANGE),
        ("3. Letter shape", "like English, slid,\nscrambled or flat?", GREEN),
        ("4. IoC", "one alphabet\nor several?", PURPLE),
        ("5. Doubled letters", "LL, EE ... are\nthey ever missing?", RED),
        ("6. Spaces kept?", "word lengths and\none-letter words", TEAL),
    ]
    w, h = 0.315, 0.22
    xs = [0.01, 0.3425, 0.675]
    ys = [0.36, 0.06]
    for i, (title, body, color) in enumerate(cards):
        x, y = xs[i % 3], ys[i // 3]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.02",
                                    facecolor=LIGHT[color], edgecolor=color, linewidth=3))
        ax.text(x + w / 2, y + h - 0.045, title, ha="center", va="center", fontsize=15, weight="bold", color=color)
        ax.text(x + w / 2, y + h / 2 - 0.035, body, ha="center", va="center", fontsize=14, color=INK, linespacing=1.3)
    save(fig, "01-clue-board.png")


def fig_symbol_sets():
    rows = [
        ("- .... . .-.. .. --. ....", "only dots, dashes\nand gaps", "Morse code\n(decode it first)", BLUE),
        ("10011 00111 00100 01011", "only two symbols,\nin groups of 5", "binary or Baconian\n(an encoding)", BLUE),
        ("44 23 15 31 24 22 23 44", "digits 1 to 5,\nin pairs", "Polybius square", ORANGE),
        ("68 26 48 57 46 50 35 59", "two-digit numbers,\noften above 55", "Nihilist cipher", ORANGE),
        ("GAFVA DAFDA DDGGA GADDD", "only A D F G V X", "ADFGVX\n(or ADFGX without V)", PURPLE),
        ("PBLSN CBPAH PTDLL RCSLE", "25 letters, J never\nappears, even length", "a 5 x 5 square: Playfair,\nbifid, four-square", RED),
        ("YVKQW MMHNT IYJYK JDKWQ", "all 26 letters", "keep measuring:\nlength, shape, IoC", GREEN),
    ]
    fig, ax = plt.subplots(figsize=(12, 8.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(rows) + 1.2)
    ax.axis("off")
    cols = [(0.0, 0.39), (0.40, 0.27), (0.68, 0.32)]
    heads = ["What you see", "The clue", "Suspect"]
    top = len(rows) + 0.2
    for (x, w), head in zip(cols, heads):
        ax.add_patch(Rectangle((x, top), w - 0.005, 0.85, facecolor=INK, edgecolor="white"))
        ax.text(x + w / 2, top + 0.42, head, ha="center", va="center", color="white", fontsize=18, weight="bold")
    for i, (sample, clue, suspect, color) in enumerate(rows):
        y = len(rows) - 1 - i + 0.1
        for (x, w), txt, fam in zip(cols, (sample, clue, suspect), ("monospace", "DejaVu Sans", "DejaVu Sans")):
            ax.add_patch(Rectangle((x, y), w - 0.005, 0.92, facecolor=LIGHT[color], edgecolor="white", linewidth=2))
            ax.text(x + w / 2, y + 0.46, txt, ha="center", va="center", fontsize=15 if fam == "monospace" else 14,
                    family=fam, weight="bold" if txt is suspect else "normal", color=INK, linespacing=1.25)
    ax.text(0.5, len(rows) + 1.15, "Step one: look at which symbols appear", ha="center", va="bottom", fontsize=21, weight="bold", color=INK)
    save(fig, "01-symbol-sets.png")


def fig_length_factors():
    fig, ax = plt.subplots(figsize=(10, 7.2))
    ax.set_xlim(0, 40)
    ax.set_ylim(-1, 32)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(20, 31.6, "165 letters  =  3 x 5 x 11", ha="center", va="top", fontsize=26, weight="bold", color=INK)
    ax.text(20, 29.2, "so the text fits exactly into these rectangles (a hint for transpositions)", ha="center", va="top", fontsize=15, color="#374151")

    def grid(x0, y0, rows, cols, color, label):
        for r in range(rows):
            for c in range(cols):
                ax.add_patch(Rectangle((x0 + c, y0 + r), 1, 1, facecolor=LIGHT[color], edgecolor=color, linewidth=0.8))
        ax.text(x0 + cols / 2, y0 - 0.5, label, ha="center", va="top", fontsize=15, weight="bold", color=color)

    grid(1, 22, 5, 33, BLUE, "5 rows of 33")
    grid(1, 3, 11, 15, ORANGE, "11 rows of 15")
    grid(19, 3, 15, 11, GREEN, "15 rows of 11")
    ax.text(35.5, 9, "Odd length:\nnot Playfair,\nnot a 2 x 2 Hill\n(they need\nan even count)", ha="center", va="center", fontsize=15,
            color=RED, weight="bold", bbox=dict(boxstyle="round,pad=0.5", facecolor=LIGHT[RED], edgecolor=RED, linewidth=2))
    save(fig, "01-length-factors.png")


def fig_frequency_shapes():
    panels = [
        ("The hidden English message", PLAIN, GREY, "E, N, T, H tall; J, Q, X, Z missing"),
        ("Message B: same bars as English", MYSTERY["B"], GREEN, "letters kept, order changed: transposition"),
        ("Message A: English slid 7 places", MYSTERY["A"], BLUE, "same shape, moved along: Caesar"),
        ("Message F: bars shuffled", MYSTERY["F"], ORANGE, "tall and short bars, wrong letters: substitution"),
        ("Message C: bars flattened", MYSTERY["C"], PURPLE, "all 26 letters, no tall towers: several alphabets"),
        ("Message E: even, no J", MYSTERY["E"], RED, "fairly flat, J missing: Playfair-like"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(12.5, 10.5), sharey=True)
    for ax, (title, text, color, note) in zip(axes.flat, panels):
        ax.bar(range(26), percents(text), color=color, edgecolor="white")
        ax.set_xticks(range(26))
        ax.set_xticklabels(list(ALPHABET), fontsize=12, family="monospace")
        ax.set_title(title, fontsize=17, weight="bold", color=INK, loc="left")
        ax.text(0.98, 0.93, note, transform=ax.transAxes, ha="right", va="top", fontsize=13, color=INK,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color))
        ax.set_ylim(0, 17.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(-0.7, 25.7)
    for ax in axes[:, 0]:
        ax.set_ylabel("% of letters")
    fig.suptitle("Letter counts: the shape of the bars is a fingerprint", fontsize=22, weight="bold", color=INK, y=1.0)
    fig.tight_layout()
    save(fig, "01-frequency-shapes.png")


def fig_ioc_scale():
    points = [("A", MYSTERY["A"], BLUE), ("B", MYSTERY["B"], GREEN), ("F", MYSTERY["F"], ORANGE),
              ("C", MYSTERY["C"], PURPLE), ("E", MYSTERY["E"], RED)]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.set_xlim(0.030, 0.076)
    ax.set_ylim(-1.6, 3.4)
    ax.axhline(0, color=INK, lw=2)
    ax.axvspan(0.030, 0.045, color=LIGHT[PURPLE], alpha=0.8)
    ax.axvspan(0.045, 0.058, color=LIGHT[YELLOW], alpha=0.9)
    ax.axvspan(0.058, 0.076, color=LIGHT[GREEN], alpha=0.8)
    ax.text(0.0375, -1.15, "flat: many alphabets,\nor random letters", ha="center", va="center", fontsize=13, color=INK)
    ax.text(0.0515, -1.15, "in between: pairs,\nor a short key", ha="center", va="center", fontsize=13, color=INK)
    ax.text(0.067, -1.15, "one alphabet: like English", ha="center", va="center", fontsize=13, color=INK)
    for x, label in ((1 / 26, "random\n0.038"), (0.0667, "English\n0.067")):
        ax.plot([x, x], [-0.25, 0.25], color=INK, lw=3)
        ax.text(x, 3.25, label, ha="center", va="top", fontsize=14, weight="bold", color=INK)
        ax.plot([x, x], [0.3, 2.45], color=INK, lw=1, ls=":")
    levels = {"A": 0, "B": 1, "F": 2, "C": 0, "E": 1}  # stacked so no two labels overlap
    for name, text, color in points:
        value = round(ioc(text), 3)
        y = 0.55 + 0.75 * levels[name]
        ax.scatter([value], [y], s=520, color=color, zorder=3, edgecolor="white", linewidth=2)
        ax.text(value, y, name, ha="center", va="center", color="white", fontsize=15, weight="bold", zorder=4)
        ax.text(value + 0.0011, y, f"{value:.3f}", ha="left", va="center", fontsize=13, color=INK)
    ax.set_yticks([])
    ax.spines[["left", "top", "right"]].set_visible(False)
    ax.set_xlabel("index of coincidence (IoC)")
    ax.set_title("Where the mystery messages sit on the IoC line", fontsize=19, weight="bold", color=INK)
    save(fig, "01-ioc-scale.png")


def fig_flowchart():
    fig, ax = plt.subplots(figsize=(12, 15))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 15)
    ax.axis("off")

    def q(x, y, text, w=4.6, h=1.15):
        box(ax, x - w / 2, y - h / 2, w, h, text, BLUE, size=15, weight="bold", round_=0.25)

    def ans(x, y, text, color, w=3.9, h=1.15):
        box(ax, x - w / 2, y - h / 2, w, h, text, color, size=14, weight="bold", round_=0.25)

    def arrow(x0, y0, x1, y1, label="", color=INK, lx=0.15, ly=0.0):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2, mutation_scale=20))
        if label:
            ax.text((x0 + x1) / 2 + lx, (y0 + y1) / 2 + ly, label, fontsize=14, weight="bold", color=color, ha="left", va="center")

    ax.text(6, 14.85, "Which cipher is it? A first-look flowchart", ha="center", va="top", fontsize=23, weight="bold", color=INK)
    qx, ax_x = 3.4, 9.3
    ys = [13.1, 11.0, 8.9, 6.8, 4.7, 2.6]
    qs = [
        "Only 2 or 3 symbols?\n(dots/dashes, 0/1, A/B)",
        "Digits, or only\nA D F G (V) X?",
        "Bars look like English?\n(E, T tall; Z, Q rare)",
        "IoC near 0.067?",
        "Even length, J missing,\nno doubled pair in a pair?",
        "Slices every k letters\nlook like English?",
    ]
    answers = [
        ("Encoding: decode it\n(Morse, binary), restart", TEAL),
        ("Polybius, Nihilist\nor ADFGVX", ORANGE),
        ("TRANSPOSITION\nletters only moved", GREEN),
        ("One alphabet: Caesar,\naffine or substitution", BLUE),
        ("PLAYFAIR\n(a 5 x 5 square)", RED),
        ("VIGENERE family\nkey length k", PURPLE),
    ]
    for i, (y, text) in enumerate(zip(ys, qs)):
        q(qx, y, text)
        ans(ax_x, y, *answers[i])
        arrow(qx + 2.3, y, ax_x - 1.95, y, "yes", GREEN, lx=-0.35, ly=0.25)
        if i < len(ys) - 1:
            arrow(qx, y - 0.58, qx, ys[i + 1] + 0.58, "no", RED)
    ans(qx, 0.75, "Hill, autokey, or a layer\nyou missed (try reversed)", GREY, w=4.6)
    arrow(qx, ys[-1] - 0.58, qx, 0.75 + 0.58, "no", RED)
    ax.text(ax_x, ys[3] - 0.95, "slid shape: Caesar (26 keys)", ha="center", va="center", fontsize=13, color=INK)
    save(fig, "01-decision-flowchart.png")


if __name__ == "__main__":
    fig_clue_board()
    fig_symbol_sets()
    fig_length_factors()
    fig_frequency_shapes()
    fig_ioc_scale()
    fig_flowchart()
