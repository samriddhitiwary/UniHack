"""Remove only known generated files inside the repository."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    ROOT / ".pytest_cache",
    ROOT / ".mypy_cache",
    ROOT / ".ruff_cache",
    ROOT / "apps" / "web" / "dist",
    ROOT / "apps" / "web" / "coverage",
)

for target in TARGETS:
    if target.is_dir():
        shutil.rmtree(target)
