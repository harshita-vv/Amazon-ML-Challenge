from pathlib import Path

# This file lives at code/business_entity_resolution/src/config.py
# so the project root is 3 levels up from here.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "dataset"
TRAIN_DIR = DATA_DIR / "train"
TEST_DIR = DATA_DIR / "test"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

TRAIN_S1 = TRAIN_DIR / "train_source1.tsv"
TRAIN_S2 = TRAIN_DIR / "train_source2.tsv"
TRAIN_S3 = TRAIN_DIR / "train_source3.tsv"
TRAIN_GT = TRAIN_DIR / "train_ground_truth.tsv"

TEST_S1 = TEST_DIR / "test_source1.tsv"
TEST_S2 = TEST_DIR / "test_source2.tsv"
TEST_S3 = TEST_DIR / "test_source3.tsv"
