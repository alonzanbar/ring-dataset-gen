"""I/O utilities for file operations."""

import json
import os
from pathlib import Path
from typing import Dict, Any


def ensure_dir(path: Path) -> None:
    """Ensure directory exists, creating if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def write_json(data: Dict[str, Any], path: Path) -> None:
    """Write JSON data to file."""
    ensure_dir(path.parent)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def read_json(path: Path) -> Dict[str, Any]:
    """Read JSON data from file."""
    with open(path, 'r') as f:
        return json.load(f)


def get_sample_dir(output_dir: Path, split_name: str, sample_idx: int) -> Path:
    """Get the directory path for a sample."""
    return output_dir / split_name / f"sample_{sample_idx:06d}"

