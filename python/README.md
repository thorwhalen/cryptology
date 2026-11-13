# Python for codebreakers

For the same readers as the guides, with no Python needed to start: thirteen short lessons and a bonus that teach just enough Python to build your own codebreaking tools, from holding a ciphertext in a variable to trying a partial substitution key. Every exercise works on a ciphertext, and the lessons use only what comes with Python itself, apart from the bonus.

**[Start lesson 1 in the app](https://apps.thorwhalen.com/cryptology/#/python/hold)**: the code runs in your web browser, with nothing to install and no sign-in, and your work is kept on your device. Each lesson is also a notebook below that opens in Google Colab, where you can save your own copy to Google Drive; Colab needs a Google account (for a young reader, a parent's or the school's).

Each lesson follows PRIMM (Predict, Run, Investigate, Modify, Make), the method the UK's [National Centre for Computing Education teaches](https://static.teachcomputing.org/pedagogy/QR11-PRIMM.pdf). It starts with a question like this one, from lesson 3: what does this print?

```python
t = "ABCDEFGHIJ"
print(t[1::3])
```

| # | Lesson | The job | Notebook |
|---|---|---|---|
| 1 | Hold the ciphertext | Keep the text in a variable, so every tool after this one can use it. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/01-hold.ipynb) |
| 2 | Clean it | Keep only the letters, in capitals, so counting and slicing see the cipher and nothing else. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/02-clean.ipynb) |
| 3 | Look at parts of it | Take pieces of the text by position: the start, the end, every fifth letter. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/03-slice.ipynb) |
| 4 | Print it in a grid | Write the text out in rows of a fixed width, to look for patterns that line up. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/04-grid.ipynb) |
| 5 | Read a grid by columns | Read the columns of a grid, top to bottom, as a columnar transposition does. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/05-columns.ipynb) |
| 6 | Rearrange columns | Put the letters of every row back in order with a key: the way to undo a block transposition. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/06-rearrange.ipynb) |
| 7 | Look for a crib or a name | Check which expected words appear in a text, how often, and where. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/07-cribs.ipynb) |
| 8 | Count letters | Count every letter of the text, and draw the counts as bars. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/08-count.ipynb) |
| 9 | Rank them | Sort the letters from most to least common, to match them with English's commonest letters. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/09-rank.ipynb) |
| 10 | Measure: the index of coincidence | Work out the index of coincidence, which tells one alphabet from several. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/10-ioc.ipynb) |
| 11 | Letters as numbers | Turn letters into numbers and back, so a shift is just adding and wrapping round. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/11-numbers.ipynb) |
| 12 | Keep a tool | Wrap a job in a function, so one line runs it on any text with any key. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/12-functions.ipynb) |
| 13 | Try a partial key | Write your guesses into a substitution ciphertext and see what appears. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/13-partial-key.ipynb) |
| Bonus | Three imports worth knowing | Three one-line helpers from Python's standard library, once the long way is clear. | [Open in Colab](https://colab.research.google.com/github/thorwhalen/cryptology/blob/main/python/notebooks/14-bonus.ipynb) |

## How it is built

The lessons are one TOML file each in [`lessons/`](lessons/), and the practice texts (all original) are [`texts.toml`](texts.toml), stored as plaintext plus cipher and key. `python python/scripts/build_python.py` enciphers the texts, fills them into the lessons, runs every snippet under CPython, checks that each Predict's right answer is exactly what its code prints, that each Modify and Make solution passes its check and each starter does not, and that the lessons use no imports outside the bonus. Then it writes [`lessons.json`](lessons.json), which the app reads at a pinned commit, and the notebooks in [`notebooks/`](notebooks/). `--check` checks without writing and fails if those files are out of date. Never edit `lessons.json` or a notebook by hand.

The Python a fiddle uses is explained in [`concepts.toml`](concepts.toml): a title, a few lines, and the lesson that teaches it. The app lists them, collapsed, under the fiddles that use them, each linking to its lesson; the build checks that every lesson named there exists.
