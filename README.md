# Person 1 — Data + Normalization Module

This is drop-in code for `code/business_entity_resolution/` in the project.
Extract this zip so its contents **merge into** your existing
`code/business_entity_resolution/` folder (same layout you already have —
this replaces/adds files under `src/`, plus `requirements.txt` and this
`README.md`).

## What's in here

```
business_entity_resolution/
├── requirements.txt      <- the team's final locked-down package list
├── README.md              <- this file
└── src/
    ├── __init__.py
    ├── config.py           <- portable paths (same as Step 0)
    ├── data.py             <- safe TSV loading (Step 1)
    ├── text_utils.py        <- low-level, stdlib-only cleaning primitives
    └── normalization.py     <- the multi-view name/address normalization
```

## Install

```bash
pip install -r requirements.txt
```

This installs exactly the six packages the team finalized: pandas,
scikit-learn, rapidfuzz, python-Levenshtein, lightgbm, Unidecode. No
libpostal, no Polars, no translation/LLM libraries.

## How to use it (from a notebook in `notebooks/`)

```python
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent
sys.path.append(str(PROJECT_ROOT / "code" / "business_entity_resolution"))

from src.config import TRAIN_S1, TRAIN_S2, TRAIN_S3, TRAIN_GT
from src.data import read_tsv
from src.normalization import add_normalized_columns

df_s1 = read_tsv(TRAIN_S1)
df_s1_normalized = add_normalized_columns(df_s1)   # adds views, never overwrites originals

df_s1_normalized.head()
```

Run the same `add_normalized_columns(...)` call on `df_s2` and `df_s3` too.

**Runtime note (measured against the real files):** normalization runs at
roughly 38 microseconds/row. That's about 3–4 minutes for Source 2 or
Source 3 (~5M rows each), a few seconds for Source 1. This is expected —
it's doing Unicode-correct, script-safe cleaning, not a naive vectorized
string op. Run it once per file and save the result (e.g.
`df_s1_normalized.to_parquet(...)`) rather than re-running it every time
you restart the notebook.

## What columns get added

**Name views** (from `business_name`):
| Column | What it is |
|---|---|
| `business_name_basic` | NFKC-normalized, casefolded, punctuation→space |
| `business_name_core` | `basic` with up to 2 trailing corporate suffixes stripped (Ltd, Pvt, Inc, ...) |
| `business_name_tokens` | `basic` split into a list of words |
| `business_name_sorted` | tokens sorted alphabetically and rejoined (catches word-order swaps) |
| `business_name_transliterated` | Unidecode of the name — a Latin-alphabet approximation, additional view only |

**Address views** (from `business_address`):
| Column | What it is |
|---|---|
| `business_address_basic` | NFKC-normalized, casefolded, "null"-like components dropped, punctuation→space |
| `business_address_tokens` | `basic` split into a list of words |
| `business_address_transliterated` | Unidecode of the de-nulled address |
| `address_numbers` | every standalone digit run in the ORIGINAL address (house numbers etc.) |
| `address_postal_candidates` | digit runs of length 5 or 6 — candidate US ZIP / Indian PIN codes (not validated, just extracted) |

The original `business_name`, `business_address`, `country`, and
`entity_id` columns are never modified.

## Design rules this code follows (don't violate these when extending it)

1. **Lossless.** Every derived column is additional — originals are never
   touched. If a cleaning rule turns out to be wrong later, you can always
   fall back to the untouched original.
2. **Suffix stripping is a side view, not the truth.** `business_name_core`
   removes things like "Pvt Ltd" — but only up to 2 trailing tokens, and
   only if they're recognized suffixes. `"ABC Technologies Pvt Ltd
   Services"` is correctly left alone, because `"services"` isn't a
   recognized suffix — stripping stops the moment a non-suffix token is
   hit at the end.
3. **No translation, ever.** Devanagari/Tamil/Kannada/etc. text is
   preserved character-for-character in every view except
   `_transliterated`. Transliteration is Latin-alphabet phonetic
   approximation (Unidecode), not translation — the meaning isn't looked
   up, only the sound/shape is approximated. This was tested directly
   against real multilingual strings from the dataset.
4. **Combining marks are protected — this matters a lot for Indian
   scripts.** An earlier version of this code used a `\w` regex to strip
   punctuation, which silently deleted vowel-sign marks in Devanagari/Tamil
   (e.g. "मॉडर्न" → "म डर न", losing two matras). This was caught by
   testing against real data and fixed: punctuation-stripping is now based
   on Unicode character *category* (keep Letters, Marks, Numbers; drop
   Punctuation/Symbols), not on `\w`. If you ever touch
   `text_utils.normalize_punctuation`, re-run the multilingual test cases
   before trusting it again.
5. **"null"/"NA"/"none" are only treated as missing on a FULL match** — a
   whole field, or a whole comma-separated address component — never as a
   substring. `"NA Enterprises"` and `"Nil Trading Co"` are real business
   names and are left completely alone; only a component that is *exactly*
   one of these literal tokens gets dropped.

## What's intentionally NOT in this module

- **Character n-gram TF-IDF** for fuzzy blocking — that's a modeling step,
  not a cleaning step. Compute it on `business_name_basic` /
  `business_name_transliterated` directly in the blocking script using
  `sklearn.feature_extraction.text.TfidfVectorizer(analyzer="char",
  ngram_range=(2,4))`, rather than pre-storing n-grams as columns.
- **Blocking/candidate generation itself** — this module only prepares the
  clean multi-view columns that blocking will run against. That's the next
  step.
- **Country-specific postal validation** — `address_postal_candidates`
  gives you raw 5/6-digit candidates only; validating "is this actually a
  real US ZIP vs Indian PIN" is a feature-engineering decision for Person 2,
  since it depends on the `country` column and shouldn't be baked into a
  cleaning step that has to stay country-agnostic (remember: France shows
  up in test with none of this logic built for it, so nothing here assumes
  only US/India).
