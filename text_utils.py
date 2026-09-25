"""
text_utils.py
Low-level, reusable text-cleaning primitives used by normalization.py.

These are intentionally generic (no business-name/address-specific logic)
so they're easy to unit-test and reuse for both business_name and
business_address cleaning. Stdlib only — no external dependencies.
"""
import math
import re
import unicodedata

# Literal tokens that mean "this field/component is actually empty".
# Matched ONLY against the FULL (stripped, casefolded) string — never as a
# substring — so real content like "NA Enterprises" or "Nil Trading Co" is
# never mistaken for a missing value.
MISSING_TOKENS = {"", "null", "none", "na", "n/a", "nan", "nil", "-", "--"}


def is_missing_token(value) -> bool:
    """True if `value` represents 'no real content': None, float NaN, or a
    literal missing-token string (e.g. 'null', 'None', 'NA') once stripped
    and casefolded. Does NOT match on substrings."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().casefold() in MISSING_TOKENS


def nfkc_casefold(value: str) -> str:
    """Unicode NFKC normalization + casefold.

    NFKC makes visually/semantically equivalent Unicode sequences compare
    equal (e.g. full-width vs half-width characters, combining accents vs
    precomposed characters). casefold is a stronger, more correct lowercase
    than .lower() for caseless matching across scripts.

    This does NOT touch script or language — Devanagari/Tamil/Kannada text
    passes through unchanged, just Unicode-normalized and casefolded.
    """
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", value).casefold()


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    """Collapse any run of whitespace (spaces, tabs, newlines) into a single
    space, and strip leading/trailing whitespace."""
    return _WHITESPACE_RE.sub(" ", value).strip()


# IMPORTANT: we do NOT use regex \w here. \w matches letters/digits/
# underscore but EXCLUDES Unicode combining marks (category M) — the small
# vowel signs/diacritics that Devanagari, Tamil, Kannada and many other
# scripts attach to a base letter (e.g. the "ो" matra in Hindi, category
# Mc/Mn). Using \w would silently delete those marks and corrupt the word
# (verified against real data: "मॉडर्न" -> "म डर न", losing two matras).
# Instead we keep any character whose Unicode category is Letter (L*),
# Mark (M*), or Number (N*), plus whitespace, and replace everything else
# (punctuation P*, symbols S*, etc.) with a space.
_KEEP_CATEGORY_PREFIXES = ("L", "M", "N")


def normalize_punctuation(value: str) -> str:
    """Replace punctuation/symbols with a SPACE (not delete outright), so
    'AT&T' -> 'AT T' rather than 'ATT' — token boundaries are preserved
    instead of accidentally merging two separate words.

    Letters, combining marks, and digits from ANY Unicode script are
    preserved untouched (see note above on why this must be category-based,
    not a \\w regex).
    """
    kept_chars = [
        ch if (ch.isspace() or unicodedata.category(ch)[0] in _KEEP_CATEGORY_PREFIXES) else " "
        for ch in value
    ]
    return normalize_whitespace("".join(kept_chars))


_DIGIT_RUN_RE = re.compile(r"\d+")


def extract_number_tokens(value: str):
    """Return every standalone run of digits in `value`, in order of
    appearance. Used for house/building numbers and other numeric address
    tokens (works on the ORIGINAL text, before punctuation is stripped)."""
    return _DIGIT_RUN_RE.findall(value)


def extract_postal_candidates(value: str):
    """Return digit runs of length 5 or 6 — plausible Indian PIN (6-digit)
    or US ZIP (5-digit) candidates.

    This is intentionally a CANDIDATE list, not a validated postal code:
    country-aware validation/scoring belongs in the feature-engineering
    stage (Person 2), not here.
    """
    return [d for d in _DIGIT_RUN_RE.findall(value) if len(d) in (5, 6)]


def tokenize(value: str):
    """Split an already punctuation-normalized string into whitespace
    tokens, dropping any empty strings."""
    return [t for t in value.split(" ") if t]
