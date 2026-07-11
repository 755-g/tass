from __future__ import annotations

import json
import os
from typing import Optional

from tass.models import ProjectInfo, ProjectMeta

# Default data directory: inside the tass project itself
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
_PROJECT_INDEX_PATH = os.path.join(_DATA_DIR, "project_index.json")
_PROJECT_META_PATH = os.path.join(_DATA_DIR, "project_meta.json")


def ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def get_project_index_path() -> str:
    return _PROJECT_INDEX_PATH


def get_project_meta_path() -> str:
    return _PROJECT_META_PATH


# ── project_index.json (scan results) ──


def save_project_index(projects: list[ProjectInfo]) -> None:
    ensure_data_dir()
    data = [p.to_dict() for p in projects]
    with open(_PROJECT_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project_index() -> list[ProjectInfo]:
    if not os.path.exists(_PROJECT_INDEX_PATH):
        return []
    try:
        with open(_PROJECT_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [ProjectInfo.from_dict(item) for item in data]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


# ── project_meta.json (user-maintained metadata) ──


def load_project_meta() -> dict[str, ProjectMeta]:
    if not os.path.exists(_PROJECT_META_PATH):
        return {}
    try:
        with open(_PROJECT_META_PATH, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)
        result: dict[str, ProjectMeta] = {}
        for name, data in raw.items():
            result[name] = ProjectMeta.from_dict(data)
        return result
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


# ── Helper: find project by name (case-insensitive) ──


def find_project_case_insensitive(
    projects: list[ProjectInfo], name: str
) -> Optional[ProjectInfo]:
    name_lower = name.lower()
    for p in projects:
        if p.name.lower() == name_lower:
            return p
    return None


def find_meta_case_insensitive(
    metas: dict[str, ProjectMeta], name: str
) -> tuple[Optional[str], Optional[ProjectMeta]]:
    """Returns (original_key, meta) matched case-insensitively."""
    name_lower = name.lower()
    for key, meta in metas.items():
        if key.lower() == name_lower:
            return key, meta
    return None, None
