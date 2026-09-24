# tests/conftest.py
"""Add the analysis package to sys.path so `import core` works."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "crosscorr_lib" / "analysis"
sys.path.insert(0, str(ANALYSIS_DIR))