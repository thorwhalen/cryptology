# Spreadsheets for the mechanical parts of cryptanalysis

Nine spreadsheets that do the counting and arithmetic the guides teach, so you can spend your time thinking instead of tallying. Each one opens with a short "How to use" block: you type into the yellow cells, everything else works itself out, and each already holds a made-up sample ciphertext so you can see it working.

**Google Sheets:** open the copy link, and Google makes you your own editable copy (the shared original is read-only). **Excel or LibreOffice:** download the `.xlsx` file from this folder.

| # | Sheet | What it does | Guides | Google Sheets (make a copy) | Excel / LibreOffice |
|---|---|---|---|---|---|
| 01 | Letter counts and IoC | Counts every letter beside English's percentages, works out the index of coincidence and chi-squared against English, and says what that suggests. | 01, 02, 04 | (coming) | [01-letter-counts.xlsx](01-letter-counts.xlsx) |
| 02 | Caesar: all 26 shifts | Shows the text moved back by every shift, scores each with chi-squared, and highlights the best one. | 02, 03 | (coming) | [02-caesar.xlsx](02-caesar.xlsx) |
| 03 | Affine: decrypt and inverses | Decrypts (and encrypts) with a and b, lists the inverses mod 26, and solves the key from two guessed letters. | 03 | (coming) | [03-affine.xlsx](03-affine.xlsx) |
| 04 | Substitution helper | Type a plain letter under each cipher letter and watch the message fill in; counts beside English's order; warns about letters used twice. | 02, 06 | (coming) | [04-substitution.xlsx](04-substitution.xlsx) |
| 05 | Vigenere slices | Scans key lengths 1 to 20 by average slice IoC, solves each slice as a Caesar shift with chi-squared, spells the key and decrypts. | 04, 05 | (coming) | [05-vigenere-slices.xlsx](05-vigenere-slices.xlsx) |
| 06 | Repeats and factors | Counts how many gaps each number from 2 to 20 divides, from gaps you type or from repeats it finds in the text. | 05 | (coming) | [06-repeats-and-factors.xlsx](06-repeats-and-factors.xlsx) |
| 07 | Columnar grid | Writes a text into a grid of any width and reads it off by columns in the order you type, or undoes a columnar (the strips set in order). | 07 | (coming) | [07-columnar.xlsx](07-columnar.xlsx) |
| 08 | Letter pairs (digraphs) | Counts letter pairs (a 26 x 26 table and the top 15) and checks the Playfair and Hill tells: even length, doubled pairs, J. | 09, 01 | (coming) | [08-digraphs.xlsx](08-digraphs.xlsx) |
| 09 | Hill 2x2 | Finds a key's determinant and undo matrix mod 26, checks it, and encrypts or decrypts a text, with the first pair worked step by step. | 09 | [copy](https://docs.google.com/spreadsheets/d/1-IDlvCVldkjXQqE_Yp_ElFSHladW0GH4O6c9o_kj2-Y/copy) | [09-hill.xlsx](09-hill.xlsx) |

All the sheets are in one Google Drive folder: [Cryptanalysis guides: sheets](https://drive.google.com/drive/folders/1lBgVwDSJYblwKUYUzuXNTdeiFoXQAkvN). The links, titles and guide ids are also in [`sheets.json`](sheets.json), for the app and the book.

## How they are built

The formulas are portable (LEN, SUBSTITUTE, MID, CODE, CHAR, MOD, INDEX, MATCH, COUNTIF, SUMPRODUCT, FREQUENCY, OFFSET, GCD, AVERAGEIF), so the same file works in Google Sheets, Excel and LibreOffice. Each workbook has three tabs: the front tab, a Summary tab repeating its headline results, and a Workings tab with the behind-the-scenes columns. Long outputs are shown as lines of 60 characters. Size limits: about 1800 letters for most outputs; the Vigenere scan reads the first 600 letters, the repeat finder 400, the pair counts 800, the columnar grid 720.

```sh
python sheets/build_sheets.py     # writes the nine .xlsx files and sheets.json (Google links are kept)
python sheets/check_sheets.py     # recalculates them in LibreOffice and checks every sample's answer
```

The sample texts are original, encrypted by the small reference ciphers in `build_sheets.py`, so `check_sheets.py` knows each right answer.
