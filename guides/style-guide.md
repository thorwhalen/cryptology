# How the guides are written

These guides teach cryptanalysis (breaking ciphers) to very smart 11 to 13 year olds: the kind who win math competitions. They are also meant as sources for Gemini Notebook (NotebookLM), whose Video Overviews pull images, diagrams, quotes and numbers from the PDFs. So each guide must stand on its own and carry its own pictures.

## The reader

- Clever, quick and curious, but **assume nothing they have not been taught**: no modular arithmetic, no sigma notation, no logarithms, no probability beyond "1 in 26". Introduce each grown-up idea when it is needed, in plain words first, then the real notation, then a worked example with small numbers.
- Never talk down. No "don't worry, this is easy!". Respect them: "This is the same idea mathematicians use for..." works well.
- Short sentences. Active voice. Second person ("you count the letters").
- **US spelling throughout** (color, analyze, practice, center, favorite, behavior).

## The shape of every guide

1. **Title and a one-line promise** ("By the end you can tell, from counting letters alone, whether a message uses one alphabet or several.")
2. **The big idea in one paragraph**, with a picture.
3. **Which ciphers it breaks** (a small table: cipher family, does this method help? how?). Name the ciphers the method applies to and the ones it does not, and why.
4. **Why it works**: the intuition, with a picture or a tiny experiment the reader could do with pencil and paper.
5. **The grown-up version**: the real notation and vocabulary (for example $\kappa$, $\sum$, $\equiv \pmod{26}$, "index of coincidence", "chi-squared"), each symbol explained the first time it appears. Keep formulas few and earn each one.
6. **A worked example**, start to finish, on a short ciphertext you make up yourself (original text only; never copy a competition's text). Show every number the reader would compute. Check your arithmetic with code before you write it down.
7. **When to try it** (the signals that say "reach for this now") and **when not to**.
8. **Traps and tips**: what goes wrong with short texts, unusual texts, names, missing spaces.
9. **By hand or by computer**: a table of the method's mechanical jobs (job, rough time by hand for a practiced reader and about 300 letters, tools to learn with, tools that just do it). Learn-with tools are the app's tools and exercises and the spreadsheets in `sheets/`; just-do-it tools are solvers. Every tool is a footnote (`[^gNN-key]`, labels unique across the book), never an inline link, so the prose keeps its flow. Open with one sentence on which part of this method is judgement worth keeping, and point to the chapter *Brain, pencil or computer?*.
10. **Try it yourself**: two or three small exercises, with answers at the end of the guide.
11. **Words to know**: a small glossary of the terms the guide introduced (one line each).
12. **Going further**: a few links (Wikipedia, Practical Cryptography, Simon Singh's The Code Book, Cipher Challenge resources), as `[name](url)` links.

## The stance on tools

The author's view, which every guide follows: do each mechanical job by hand once, so the reader knows what the machine does; after that, hand it to the machine and spend the time on judgement and the bird's-eye view. Teach the method the classical way, and always say which tool relieves the reader of the low bang-for-the-buck part. Deskilling is a real cost, and so is refusing a tool. The full argument is `book/brain-pencil-or-computer.md`. Keep competition rules visible: in a live round, the competition's rules decide which tools are allowed.

Aim for 1,800 to 3,500 words. A video narrator should be able to read any section aloud and have it make sense.

## Pictures

- At least **four figures per guide**, made by a Python script with matplotlib (or plain SVG rendered to PNG), saved as `figures/NN-<name>.png` at 200 dpi, roughly 1600 px wide. Bright, friendly colors, large labels (14 pt or more), white background, no tiny text. A figure must make sense without its caption, because a video may show it alone.
- Good figure ideas: bar charts of letter frequencies (English vs the ciphertext), cipher wheels, shifted alphabets, tables drawn as images with colored cells, step-by-step diagrams, a "decision" flowchart, a graph of a score against a key.
- Each guide has its own script, `scripts/fig_NN_<slug>.py`, which writes all of that guide's figures and can be re-run. Use only matplotlib and the standard library (numpy is fine). Put English letter frequencies in the script (standard published values) rather than reading a file.
- Reference figures in markdown as `![Caption that explains the picture](figures/NN-name.png)`. The caption is a full sentence.

## Format rules

- One markdown file per guide: `guides/NN-<slug>.md`, starting with a YAML block holding `title` and `subtitle`.
- **Never hard-wrap prose**: one line per paragraph or list item.
- Math in `$...$` (inline) and `$$...$$` (display): the PDF build renders LaTeX math.
- Ciphertext and plaintext in code blocks or `inline code`. Convention: CIPHERTEXT IN CAPITALS, plaintext in lower case.
- Build the PDF with `guides/scripts/build_pdfs.sh NN-<slug>.md` and look at it (read the PDF) before you call the guide done: figures placed, no missing characters, math rendered.

## The guides

| # | File | Family of methods | Applies to |
|---|---|---|---|
| 01 | `01-reading-the-clues.md` | Identifying the cipher: what a ciphertext tells you before you try anything | every cipher |
| 02 | `02-frequency-analysis.md` | Letter frequencies, fitting a shift, chi-squared | Caesar, affine, keyword and general substitution |
| 03 | `03-keys-and-brute-force.md` | Key spaces, modular arithmetic, trying every key, multiplicative inverses | Caesar, affine, small key spaces; why substitution resists |
| 04 | `04-index-of-coincidence.md` | The index of coincidence, Friedman's test, finding a key length | telling mono from poly; Vigenère, Beaufort, transposition vs substitution |
| 05 | `05-repeats-and-key-length.md` | Kasiski examination, repeated fragments, common factors, splitting into columns | Vigenère, Beaufort, autokey (and why autokey resists) |
| 06 | `06-cribs-and-patterns.md` | Known or probable words, word patterns, rebuilding a keyword alphabet | substitution, keyword, Vigenère (crib dragging), transposition |
| 07 | `07-transposition-detective-work.md` | Spotting and breaking transpositions: anagramming, column widths, letter contacts | rail fence, columnar, block permutation, reversal |
| 08 | `08-scoring-and-hill-climbing.md` | Fitness scores (n-grams), hill climbing, simulated annealing | substitution, transposition, Playfair, anything with a big key space |
| 09 | `09-two-letters-at-a-time.md` | Polygraphic ciphers: the tells of Playfair and Hill, digraph counts, solving Hill from a crib | Playfair, Hill, Polybius-based ciphers |

Cross-reference other guides by number and title ("see Guide 04, The index of coincidence") but do not depend on them: each guide must work alone.
