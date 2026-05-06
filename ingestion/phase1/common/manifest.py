"""Load `corpus/url_manifest.yaml` for Phase 1 (shared by subphases)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SchemeTarget:
    """One row from the manifest: internal id + canonical Groww URL."""

    scheme_id: str
    slug: str
    display_name: str
    groww_scheme_url: str


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a mapping.")
    return data


def iter_scheme_targets(manifest: dict[str, Any]) -> list[SchemeTarget]:
    schemes = manifest.get("schemes")
    if not isinstance(schemes, list):
        raise ValueError("Manifest must contain a 'schemes' list.")
    out: list[SchemeTarget] = []
    for row in schemes:
        if not isinstance(row, dict):
            raise ValueError("Each scheme entry must be a mapping.")
        out.append(
            SchemeTarget(
                scheme_id=str(row["scheme_id"]),
                slug=str(row["slug"]),
                display_name=str(row.get("display_name", "")),
                groww_scheme_url=str(row["groww_scheme_url"]),
            )
        )
    return out
