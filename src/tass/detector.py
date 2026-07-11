from __future__ import annotations

import os
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from typing import Optional

_ENTRY_POINT_PRIORITY = ["main.py", "app.py", "cli.py", "run.py", "index.py"]


def detect_project_type(path: str) -> str:
    """Detect project type by checking structural patterns in priority order."""
    # 1. CrewAI: has crews/ directory under src/ (CrewAI Flow structure)
    if _has_crewai_structure(path):
        return "CrewAI"

    # 2. LangChain: pyproject.toml or requirements.txt mentions langchain
    if _has_dep(path, "langchain"):
        return "LangChain"

    # 3. FastAPI: pyproject.toml or requirements.txt mentions fastapi
    if _has_dep(path, "fastapi"):
        return "FastAPI"

    # 4. Node: has package.json
    if _has_file(path, "package.json"):
        return "Node"

    # 5. Python: has any .py files
    if _has_py_files(path):
        return "Python"

    # 6. Unknown
    return "Unknown"


def _has_crewai_structure(path: str) -> bool:
    """Check for src/*/crews/ directory structure (CrewAI Flow convention)."""
    src_dir = os.path.join(path, "src")
    if not os.path.isdir(src_dir):
        return False
    try:
        for item in os.listdir(src_dir):
            item_path = os.path.join(src_dir, item)
            if os.path.isdir(item_path):
                crews_dir = os.path.join(item_path, "crews")
                if os.path.isdir(crews_dir):
                    return True
    except PermissionError:
        pass
    return False


def _has_dep(path: str, dep_name: str) -> bool:
    """Check if pyproject.toml or requirements.txt mentions a dependency."""
    # Check pyproject.toml
    pyproject = os.path.join(path, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            deps: list[str] = data.get("project", {}).get("dependencies", []) or []
            for dep in deps:
                if dep_name in dep.lower():
                    return True
        except Exception:
            # Fall back to text search
            try:
                with open(pyproject, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                if dep_name in content:
                    return True
            except Exception:
                pass

    # Check requirements.txt
    req_txt = os.path.join(path, "requirements.txt")
    if os.path.isfile(req_txt):
        try:
            with open(req_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().lower()
                    if line and not line.startswith("#") and dep_name in line:
                        return True
        except Exception:
            pass

    return False


def _has_file(path: str, filename: str) -> bool:
    return os.path.isfile(os.path.join(path, filename))


def _has_py_files(path: str) -> bool:
    """Check if the directory contains any .py files (direct children only)."""
    try:
        for item in os.listdir(path):
            if item.endswith(".py"):
                return True
    except PermissionError:
        pass
    return False


# ── Entry Points ──


def detect_entry_points(path: str) -> list[str]:
    """Find entry point files by priority order. Returns those that exist."""
    found: list[str] = []
    for ep in _ENTRY_POINT_PRIORITY:
        if os.path.isfile(os.path.join(path, ep)):
            found.append(ep)
    return found


# ── Dependencies ──


def detect_dependencies(path: str) -> list[str]:
    """Extract dependency package names from pyproject.toml and requirements.txt."""
    deps: list[str] = []
    seen: set[str] = set()

    # From pyproject.toml (structured)
    pyproject = os.path.join(path, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            dep_list: list[str] = data.get("project", {}).get("dependencies", []) or []
            for dep in dep_list:
                name = _clean_dep_name(dep)
                if name and name not in seen:
                    seen.add(name)
                    deps.append(name)
        except Exception:
            # Fallback: regex extraction
            try:
                with open(pyproject, "r", encoding="utf-8") as f:
                    content = f.read()
                # Match dependencies from [project] dependencies array
                matches = re.findall(r'"(.*?)"', content)
                for m in matches:
                    name = _clean_dep_name(m)
                    if name and name not in seen:
                        seen.add(name)
                        deps.append(name)
            except Exception:
                pass

    # From requirements.txt
    req_txt = os.path.join(path, "requirements.txt")
    if os.path.isfile(req_txt):
        try:
            with open(req_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "://" not in line:
                        name = _clean_dep_name(line)
                        if name and name not in seen:
                            seen.add(name)
                            deps.append(name)
        except Exception:
            pass

    return deps


def _clean_dep_name(dep: str) -> Optional[str]:
    """Extract package name from a dependency string like 'langchain>=1.3.0' or 'crewai[tools]>=1.15.1'."""
    dep = dep.strip().strip('"').strip("'")
    if not dep:
        return None
    # Remove version specifiers
    for sep in [">=", "<=", "!=", "==", "~=", ">", "<", "@"]:
        idx = dep.find(sep)
        if idx > 0:
            dep = dep[:idx]
            break
    # Remove extras like [tools]
    bracket = dep.find("[")
    if bracket > 0:
        dep = dep[:bracket]
    dep = dep.strip()
    return dep if dep else None


# ── Git Status ──


def detect_git_status(path: str) -> str:
    """Check git repository status. Returns 'clean', 'dirty', or 'no_git'."""
    try:
        # Check if it's a git repo
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "no_git"

        # Check for changes
        result = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "dirty" if result.stdout.strip() else "clean"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "no_git"


# ── README ──


def detect_readme_preview(path: str) -> tuple[bool, str]:
    """Check for README file and return preview (first non-empty paragraph, up to 200 chars)."""
    for name in ["README.md", "README", "README.txt", "readme.md"]:
        readme_path = os.path.join(path, name)
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                preview = _extract_preview(content)
                return True, preview
            except Exception:
                return True, ""
    return False, ""


def _extract_preview(content: str) -> str:
    """Extract first non-empty paragraph from content, up to 200 chars."""
    lines = content.strip().split("\n")
    preview_parts: list[str] = []
    for line in lines:
        line = line.strip()
        # Skip headings, images, empty lines
        if line.startswith("#") or line.startswith("!["):
            continue
        if line:
            preview_parts.append(line)
            # Stop at first paragraph break (empty line after content)
        elif preview_parts:
            break
    preview = " ".join(preview_parts).strip()
    if not preview:
        # Fallback: first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                preview = line
                break
    return preview[:200]


# ── Subdirectories ──


SKIP_SUBDIRS = {
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".idea",
    "build",
    "dist",
    "wheels",
}


def get_subdirs(path: str) -> list[str]:
    """Get first-level subdirectory names (sorted), excluding junk dirs."""
    dirs: list[str] = []
    try:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue
            if item.startswith("."):
                continue
            if item in SKIP_SUBDIRS:
                continue
            if item.endswith(".egg-info"):
                continue
            dirs.append(item)
    except PermissionError:
        pass
    return dirs


# ── Last Modified ──


def detect_last_modified(path: str) -> str:
    """Find the most recent modification time of any file under path."""
    try:
        latest = 0.0
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "__pycache__", "node_modules", "venv", ".venv"
            }]
            for f in files:
                try:
                    mtime = os.path.getmtime(os.path.join(root, f))
                    if mtime > latest:
                        latest = mtime
                except OSError:
                    pass
        if latest > 0:
            dt = datetime.fromtimestamp(latest, tz=timezone.utc)
            return dt.isoformat()
    except Exception:
        pass
    return ""
