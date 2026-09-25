"""
normalization.py
Builds the lossless, multi-view normalized columns for business_name and
business_address, per the team's finalized cleaning spec.

Design rules (do not violate these when editing):
  1. Original columns are NEVER modified or overwritten. Every derived view
     is an ADDITIONAL column.
  2. Legal/corporate suffixes are only ever stripped into a separate
     `_core` view — the basic name is always preserved intact alongside it,
     so a downstream step can always fall back to the un-stripped form.
  3. Non-Latin scripts (Devanagari, Tamil, Kannada, ...) are preserved as-is
     in every view except `_transliterated`. We never translate to English
     — transliteration (Unidecode) is an ADDITIONAL view, never a
     replacement for the original script.
  4. Literal "null"/"none"/"na"/etc. tokens are treated as missing content,
     but only when they are the WHOLE field or a WHOLE comma-separated
     address component — never as a substring match. This means a "null"
     component inside an address is dropped, but the rest of a real
     address around it is left completely untouched.
"""
import pandas as pd
from unidecode import unidecode

from .text_utils import (
    is_missing_token,
    nfkc_casefold,
    normalize_punctuation,
    extract_number_tokens,
    extract_postal_candidates,
    tokenize,
)

# Trailing corporate/legal suffix tokens we recognize, matched only at the
# END of a name (after basic normalization + tokenization). Only up to
# MAX_SUFFIX_TOKENS_STRIPPED trailing tokens are ever stripped, and
# stripping stops the moment a non-suffix trailing token is hit — so
# "ABC Technologies Pvt Ltd Services" is NOT reduced to "abc technologies"
# (the actual trailing token there is "services", not a recognized suffix,
# so nothing is stripped in that example — which is exactly the failure
# mode the team flagged and wanted avoided).
CORPORATE_SUFFIXES = {
    "ltd", "limited", "inc", "incorporated", "corp", "corporation",
    "llc", "llp", "pvt", "private", "co", "company", "plc",
    "sa", "sas", "sarl", "gmbh", "ag", "nv", "bv", "srl", "pte", "pty",
    "group", "holdings", "enterprises", "enterprise",
}

MAX_SUFFIX_TOKENS_STRIPPED = 2


def _strip_trailing_suffixes(tokens):
    """Strip up to MAX_SUFFIX_TOKENS_STRIPPED trailing tokens, but only if
    they are recognized corporate suffixes. Returns a NEW list; `tokens`
    (typically business_name_tokens) is left untouched by the caller."""
    tokens = list(tokens)
    stripped = 0
    while tokens and stripped < MAX_SUFFIX_TOKENS_STRIPPED and tokens[-1] in CORPORATE_SUFFIXES:
        tokens.pop()
        stripped += 1
    return tokens


# ---------------------------------------------------------------------------
# Business name
# ---------------------------------------------------------------------------

_EMPTY_NAME_VIEWS = {
    "business_name_basic": "",
    "business_name_core": "",
    "business_name_tokens": [],
    "business_name_sorted": "",
    "business_name_transliterated": "",
}


def build_name_views(raw_name):
    """Given ONE raw business_name value, return a dict of every derived
    view. `raw_name` should be the untouched original cell (str, or
    None/NaN for a missing field) — never a pre-cleaned value."""
    if is_missing_token(raw_name):
        return dict(_EMPTY_NAME_VIEWS)

    basic = normalize_punctuation(nfkc_casefold(raw_name))
    tokens = tokenize(basic)
    core_tokens = _strip_trailing_suffixes(tokens)
    core = " ".join(core_tokens)
    sorted_name = " ".join(sorted(tokens))
    transliterated = normalize_punctuation(nfkc_casefold(unidecode(raw_name)))

    return {
        "business_name_basic": basic,
        "business_name_core": core,
        "business_name_tokens": tokens,
        "business_name_sorted": sorted_name,
        "business_name_transliterated": transliterated,
    }


# ---------------------------------------------------------------------------
# Business address
# ---------------------------------------------------------------------------

_EMPTY_ADDRESS_VIEWS = {
    "business_address_basic": "",
    "business_address_tokens": [],
    "business_address_transliterated": "",
    "address_numbers": [],
    "address_postal_candidates": [],
}


def _drop_null_components(raw_address: str) -> str:
    """Split on commas, drop components that are literal missing-tokens
    (e.g. a component that is just 'null' or 'NA'), and rejoin the rest.
    This is why a 'null' *component* disappears while the rest of a real
    address around it survives untouched."""
    parts = raw_address.split(",")
    kept = [p.strip() for p in parts if not is_missing_token(p)]
    return ", ".join(kept)


def build_address_views(raw_address):
    """Given ONE raw business_address value, return a dict of every derived
    view. `raw_address` should be the untouched original cell."""
    if is_missing_token(raw_address):
        return dict(_EMPTY_ADDRESS_VIEWS)

    # Numbers/postal candidates are extracted from the ORIGINAL text first,
    # before any component-dropping or punctuation stripping, so numeric
    # extraction stays fully lossless relative to the raw field.
    numbers = extract_number_tokens(raw_address)
    postal_candidates = extract_postal_candidates(raw_address)

    de_nulled = _drop_null_components(raw_address)
    basic = normalize_punctuation(nfkc_casefold(de_nulled))
    tokens = tokenize(basic)
    transliterated = normalize_punctuation(nfkc_casefold(unidecode(de_nulled)))

    return {
        "business_address_basic": basic,
        "business_address_tokens": tokens,
        "business_address_transliterated": transliterated,
        "address_numbers": numbers,
        "address_postal_candidates": postal_candidates,
    }


# ---------------------------------------------------------------------------
# Dataframe-level convenience wrapper
# ---------------------------------------------------------------------------

def add_normalized_columns(
    df: pd.DataFrame,
    name_col: str = "business_name",
    address_col: str = "business_address",
) -> pd.DataFrame:
    """Apply build_name_views / build_address_views across a whole dataframe.

    Returns a NEW dataframe: every original column is preserved exactly as
    given, with the derived views added as additional columns. Does not
    mutate `df` in place.

    Note on performance: this does one Python-level function call per row
    per column (name + address), which is the honest cost of doing
    Unicode-correct, script-safe cleaning rather than a vectorized-but-naive
    string op. For the challenge's largest file (~5.3M rows) this takes a
    few minutes, not seconds — that's expected, not a bug. Run it once per
    source file and cache the result (e.g. to parquet) rather than
    re-running it on every notebook restart.
    """
    df = df.copy()

    name_records = df[name_col].map(build_name_views)
    name_df = pd.DataFrame(list(name_records), index=df.index)

    address_records = df[address_col].map(build_address_views)
    address_df = pd.DataFrame(list(address_records), index=df.index)

    for col in name_df.columns:
        df[col] = name_df[col]
    for col in address_df.columns:
        df[col] = address_df[col]

    return df
