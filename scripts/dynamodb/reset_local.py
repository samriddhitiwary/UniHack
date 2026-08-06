"""Reset only the ignored DynamoDB Local persistence directory."""

import shutil
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "infrastructure" / "docker" / "dynamodb"
if target.is_dir():
    shutil.rmtree(target)
target.mkdir(parents=True, exist_ok=True)
