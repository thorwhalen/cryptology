# cryptology

Learn how classical ciphers are broken. Nine illustrated guides to cryptanalysis, written for very curious 11 to 13 year olds (the kind who enjoy math competitions), with the grown-up notation introduced gently and every worked example checked by code.

**The interactive app** that goes with them, with tools, exercises and competition sections: [apps.thorwhalen.com/cryptology](https://apps.thorwhalen.com/cryptology/).

## The book

All nine guides as one book, with a cover, contents, a preface for readers and the adults helping them, and every guide's words merged A to Z: [**Cryptanalysis guides for young codebreakers** (PDF)](pdf/cryptanalysis-guides-for-young-codebreakers.pdf). Read it online, with links straight into the app's tools and exercises: [apps.thorwhalen.com/cryptology/#/guides](https://apps.thorwhalen.com/cryptology/#/guides).

## The guides

Each guide is a PDF (in [`pdf/`](pdf/)) built from markdown (in [`guides/`](guides/)), with its figures. Each stands on its own, and each says which ciphers its method breaks, why it works, when to try it, and ends with exercises and answers.

| # | Guide | The method | Breaks |
|---|---|---|---|
| 01 | [Reading the clues](pdf/01-reading-the-clues.pdf) | What a ciphertext tells you before you try anything | tells you which cipher it is |
| 02 | [Frequency analysis](pdf/02-frequency-analysis.pdf) | Counting letters; fitting a shift; chi-squared | Caesar, affine, substitution |
| 03 | [Keys and brute force](pdf/03-keys-and-brute-force.pdf) | Counting keys; clock arithmetic; inverses | Caesar, affine |
| 04 | [The index of coincidence](pdf/04-index-of-coincidence.pdf) | How often two letters match; finding a key length | telling one alphabet from several; Vigenère |
| 05 | [Repeats and key length](pdf/05-repeats-and-key-length.pdf) | The Kasiski examination; common factors | Vigenère, Beaufort |
| 06 | [Cribs and patterns](pdf/06-cribs-and-patterns.pdf) | Probable words; word patterns; rebuilding a keyword | substitution, keyword, Vigenère, transposition |
| 07 | [Transposition detective work](pdf/07-transposition-detective-work.pdf) | Column widths; anagramming; letter contacts | rail fence, columnar, block |
| 08 | [Scoring and hill climbing](pdf/08-scoring-and-hill-climbing.pdf) | Fitness scores; hill climbing; simulated annealing | anything with a huge key space |
| 09 | [Two letters at a time](pdf/09-two-letters-at-a-time.pdf) | The tells of Playfair and Hill; solving Hill from a crib | Playfair, Hill, Polybius |

They also work well as sources for Google's Gemini Notebook (NotebookLM): its Video Overviews draw on the figures in the PDFs.

## Python for codebreakers

For the same readers as the guides, with no Python needed to start: thirteen short lessons and a bonus that teach just enough Python to build your own codebreaking tools, and every exercise works on a ciphertext. **[Start lesson 1 in the app](https://apps.thorwhalen.com/cryptology/#/python/hold)**: the code runs in your web browser, with nothing to install and no sign-in. Each lesson is also a notebook in [`python/`](python/) that opens in Google Colab, which needs a Google account (for a young reader, a parent's or the school's).

## Building

```sh
python guides/scripts/fig_04_index_of_coincidence.py   # one guide's figures (matplotlib)
guides/scripts/build_pdfs.sh                          # every guide's PDF (pandoc + xelatex)
python guides/scripts/build_book.py                   # the book PDF, and html/ for the web edition
python python/scripts/build_python.py                 # the Python lessons: check every snippet, write lessons.json and the notebooks
```

Green "In the app" boxes are blockquotes that start with `**In the app:**`; `guides/scripts/app_links.lua` styles them in the PDFs and the HTML. The book's cover, preface and LaTeX header are in `guides/book/`. The web edition in `html/` is one HTML fragment per guide plus `index.json` (sections and words); the cryptology app reads it at a pinned commit.

How the guides are written: [`guides/style-guide.md`](guides/style-guide.md). Guide 08's live hill-climbing figures need an English quadgram table: set `QUADGRAMS` to a file of `QUADGRAM COUNT` lines (for example Practical Cryptography's `english_quadgrams.txt`).

## License

Text and figures: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ([`LICENSE-content`](LICENSE-content)). Code: MIT ([`LICENSE`](LICENSE)).
