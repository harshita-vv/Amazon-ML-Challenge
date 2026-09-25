"""
data.py
Centralized, safe TSV loading so every notebook/script in the project uses
identical (correct) pandas read settings — no one accidentally reloads a
file with pandas' default type-guessing and silently corrupts it.
"""
import pandas as pd

# Load everything as text, and treat ONLY a truly empty cell as missing —
# NOT the literal words "NA"/"NULL"/"None"/etc, which pandas treats as
# missing BY DEFAULT and which could silently eat a real business name or
# address containing one of those words. (We handle those literal tokens
# ourselves, explicitly, in normalization.py — see is_missing_token.)
SAFE_READ_KWARGS = dict(
    sep="\t",
    dtype=str,
    keep_default_na=False,
    na_values=[""],
)


def read_tsv(path) -> pd.DataFrame:
    """Read one of the challenge's TSV files with the project's safe
    settings (all-text dtypes, no default-NA guessing)."""
    return pd.read_csv(path, **SAFE_READ_KWARGS)


def load_training_data(train_s1, train_s2, train_s3, train_gt) -> dict:
    """Convenience loader for all four training files at once.

    Pass the Path objects from src.config, e.g.:
        from src.config import TRAIN_S1, TRAIN_S2, TRAIN_S3, TRAIN_GT
        from src.data import load_training_data
        data = load_training_data(TRAIN_S1, TRAIN_S2, TRAIN_S3, TRAIN_GT)
        df_s1, df_s2, df_s3, df_gt = data["s1"], data["s2"], data["s3"], data["gt"]
    """
    return {
        "s1": read_tsv(train_s1),
        "s2": read_tsv(train_s2),
        "s3": read_tsv(train_s3),
        "gt": read_tsv(train_gt),
    }
