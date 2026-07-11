from __future__ import annotations

import os
import re
import platform
from typing import Optional

from tass.models import Finding, NoteEntry
from tass.notes import parse_notes
from tass import store

# Regex for Windows drive letter paths (e.g., C:\Users\...)
_WIN_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\\\s\"'|<>]+\\)*[^\\\s\"'|<>]*")

# Regex to extract file references from code blocks
_FILE_REF_RE = re.compile(r"`([^`]+)`")

# Regex for directory tree entries (requires ── double dash, captures first filename token)
_TREE_LINE_RE = re.compile(r"^(?:[ └├│]*?)(?:├|└)──\s*(\S+)")

# Regex for code blocks
_CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def run_check(check_dir: str | None = None) -> list[Finding]:
    """Run all 4 check rules against notes and project data.

    Args:
        check_dir: The projects root directory (for resolving relative paths).
                   Defaults to /home/socket/projects.

    Returns:
        List of Finding objects (empty if no issues).
    """
    if check_dir is None:
        check_dir = "/home/socket/projects"

    notes_file = os.path.join(check_dir, "agent-learning-notes", "Agent学习笔记.md")
    entries = parse_notes(notes_file)

    if not entries:
        print("⚠  无法解析笔记文件，跳过一致性检查")
        return []

    all_findings: list[Finding] = []

    # Run each rule
    all_findings.extend(_rule_1_entry_points(entries, check_dir))
    all_findings.extend(_rule_3_windows_paths(entries))
    all_findings.extend(_rule_5_references(entries, check_dir))
    all_findings.extend(_rule_6_directory_structure(entries, check_dir))

    return all_findings


# ── Rule #1: Entry point existence ──


def _rule_1_entry_points(entries: list[NoteEntry], projects_root: str) -> list[Finding]:
    """#1: Check that files mentioned in code location sections actually exist.

    Extracts:
    - Project paths from "### 代码位置" sections
    - File names from directory tree listings in code blocks
    - Verifies they exist on disk
    """
    findings: list[Finding] = []

    for entry in entries:
        if not entry.project:
            continue

        project_path = os.path.join(projects_root, entry.project)
        if not os.path.isdir(project_path):
            findings.append(Finding(
                rule_id="#1",
                project=entry.project,
                issue=f"项目目录不存在",
                detail=f"笔记第{entry.day}天引用的项目目录不存在: {project_path}",
            ))
            continue

        # Extract file names from directory tree listings in code blocks
        files_from_trees = _extract_tree_files(entry.content)
        if not files_from_trees:
            # Some day entries don't have tree listings (e.g., Day 1), that's fine
            continue

        for fname in files_from_trees:
            if not _find_file_recursive(fname, project_path):
                findings.append(Finding(
                    rule_id="#1",
                    project=entry.project,
                    issue=f"入口文件/路径不存在",
                    detail=f"笔记第{entry.day}天列出 '{fname}'，但项目目录中未找到 (已递归搜索)",
                ))

    return findings


def _extract_tree_files(content: str) -> list[str]:
    """Extract file names from directory tree listings in code blocks.

    Handles formats like:
    ```
    joke-pipeline/
    ├── my_agent.py
    ├── mcp_time_server.py
    └── main.py
    ```
    """
    files: list[str] = []
    for match in _CODE_BLOCK_RE.finditer(content):
        block = match.group(1)
        lines = block.split("\n")
        for line in lines:
            m = _TREE_LINE_RE.match(line)
            if m:
                name = m.group(1).strip()
                # Skip the project root dir name itself (e.g., "joke-pipeline/")
                if name.endswith("/"):
                    continue
                # Skip directory listings
                if name in {"├", "└", "│", "─"} or not name:
                    continue
                files.append(name)
    return files


# ── Rule #3: Windows path detection ──


def _rule_3_windows_paths(entries: list[NoteEntry]) -> list[Finding]:
    """#3: Detect Windows-style paths (C:...) in notes on WSL environment.

    If the current platform is WSL (Linux with 'microsoft' in kernel release),
    flag any Windows drive letter paths found in notes.
    """
    is_wsl = _is_wsl()
    if not is_wsl:
        return []

    findings: list[Finding] = []

    for entry in entries:
        matches = _WIN_PATH_RE.findall(entry.content)
        if matches:
            # Deduplicate
            unique_paths = sorted(set(matches))
            findings.append(Finding(
                rule_id="#3",
                project=entry.project or "—",
                issue=f"笔记包含 Windows 路径（当前环境为 WSL）",
                detail=(f"第{entry.day}天发现 {len(unique_paths)} 个 Windows 路径: "
                        f"{'; '.join(unique_paths[:5])}"
                        f"{'...' if len(unique_paths) > 5 else ''}"),
            ))

    return findings


def _is_wsl() -> bool:
    """Detect if running inside WSL."""
    try:
        return "microsoft" in platform.uname().release.lower()
    except Exception:
        return False


# ── Rule #5: Referenced files/tools/functions existence ──


def _rule_5_references(entries: list[NoteEntry], projects_root: str) -> list[Finding]:
    """#5: Check that files, tools, or functions referenced in code blocks exist.

    Extracts inline code references (backtick-quoted names) and checks:
    - If the name looks like a file (ends with .py or .md), check file existence
    - If the name looks like a function/tool name, try to find it in project files
    """
    findings: list[Finding] = []

    for entry in entries:
        if not entry.project:
            continue

        project_path = os.path.join(projects_root, entry.project)
        if not os.path.isdir(project_path):
            continue

        # Skip entries marked as pending (not started yet)
        if entry.status == "pending":
            continue

        # Skip entries where code is explicitly noted as lost/overwritten
        if "代码被" in entry.content and "覆盖" in entry.content:
            continue

        # Extract inline code references
        refs = _FILE_REF_RE.findall(entry.content)
        # Filter out non-file/function references (URLs, paths with slashes)
        for ref in refs:
            ref = ref.strip()
            if _is_ignorable_reference(ref):
                continue

            # Check if it's a file reference (.py, .md, .txt, .yaml, .toml, .env)
            if _is_file_reference(ref):
                if not _check_file_exists(ref, project_path):
                    findings.append(Finding(
                        rule_id="#5",
                        project=entry.project,
                        issue=f"引用的文件不存在",
                        detail=(f"笔记第{entry.day}天引用 '{ref}'，"
                                f"在 '{entry.project}' 中未找到对应文件"),
                    ))
            # Check if it's a function/tool name
            elif _is_code_identifier(ref) and len(ref) > 1:
                if not _check_function_exists(ref, project_path):
                    # Be conservative: only flag if we can confirm it's definitely missing
                    pass  # Skip: too many false positives for function names

    return findings


def _is_ignorable_reference(ref: str) -> bool:
    """Check if a backtick reference should be ignored (URLs, paths, etc.)."""
    if ref.startswith("http") or ref.startswith("ftp"):
        return True
    if "/" in ref or "\\" in ref:
        return True  # It's a path, not a simple file/function name
    if ref.startswith("@") or ref.startswith("#"):
        return True
    if ref in {"", " ", "-", "_"}:
        return True
    if ref.startswith("{") or ref.startswith("}"):
        return True
    if ref in {"uv", "pip", "cd", "ls", "git", "echo", "eval"}:
        return True  # Common shell commands
    return False


def _is_file_reference(ref: str) -> bool:
    """Check if a reference looks like a filename."""
    return any(ref.endswith(ext) for ext in [
        ".py", ".md", ".txt", ".yaml", ".yml", ".toml", ".json",
        ".env", ".gitignore", ".cfg", ".ini", ".conf",
    ])


def _is_code_identifier(ref: str) -> bool:
    """Check if a reference looks like a code identifier (variable, function, class)."""
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ref))


def _check_file_exists(ref: str, project_path: str) -> bool:
    """Check if a referenced file exists anywhere in the project tree."""
    return _find_file_recursive(ref, project_path)


def _check_function_exists(func_name: str, project_path: str) -> Optional[bool]:
    """Try to find a function definition in project Python files.

    Returns:
        True if found, False if confirmed missing, None if uncertain.
    """
    try:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "__pycache__", "node_modules", "venv", ".venv"
            }]
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        # Look for function/class definitions
                        if re.search(
                            rf"^(def {func_name}|class {func_name}|{func_name}\s*=\s*)",
                            content,
                            re.MULTILINE,
                        ):
                            return True
                        # Also check for the name in imports and assignments
                        if re.search(
                            rf"\b{func_name}\b", content
                        ):
                            return True
                    except Exception:
                        continue
    except Exception:
        return None

    return False


# ── Rule #6: Directory structure comparison ──


def _rule_6_directory_structure(entries: list[NoteEntry], projects_root: str) -> list[Finding]:
    """#6: Compare directory trees described in notes with actual filesystem.

    Extracts tree listings from code blocks and compares with os.listdir output.
    """
    findings: list[Finding] = []

    for entry in entries:
        if not entry.project:
            continue

        project_path = os.path.join(projects_root, entry.project)
        if not os.path.isdir(project_path):
            continue

        # Extract files from tree listings in this entry
        tree_files = set(_extract_tree_files(entry.content))
        if not tree_files:
            continue

        # Find discrepancies: files in tree but not on disk (recursive search)
        for f in sorted(tree_files):
            if _find_file_recursive(f, project_path):
                continue
            # Skip common transient/config files
            if f in {".env", ".gitignore", "uv.lock", "requirements.txt",
                     "AGENTS.md", "README.md"}:
                continue
            findings.append(Finding(
                rule_id="#6",
                project=entry.project,
                issue=f"笔记中列出的文件/目录与实际不符",
                detail=(f"第{entry.day}天笔记列出 '{f}'，"
                        f"但当前项目目录中未找到"),
            ))

    return findings


def _find_file_recursive(filename: str, search_root: str) -> bool:
    """Search for a file by name recursively under search_root."""
    try:
        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "__pycache__", "node_modules", "venv", ".venv", ".idea"
            }]
            if filename in files:
                return True
    except Exception:
        pass
    return False


def _get_all_files_recursive(project_path: str) -> set[str]:
    """Get all filenames (not paths) recursively, excluding hidden and junk."""
    result: set[str] = set()
    try:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "__pycache__", "node_modules", "venv", ".venv", ".idea"
            }]
            for f in files:
                if f.startswith("."):
                    continue
                if f in {"uv.lock", "requirements.txt"}:
                    continue
                # Skip egg-info files
                if ".egg-info" in root or ".egg-info" in f:
                    continue
                result.add(f)
    except Exception:
        pass
    return result


def _get_actual_files(project_path: str) -> set[str]:
    """Get sorted list of files/dirs in the project root (no hidden files)."""
    files: set[str] = set()
    try:
        for item in os.listdir(project_path):
            if item.startswith(".") and item not in {".env", ".gitignore"}:
                continue
            if item in {"__pycache__", ".venv", "venv", "node_modules", ".idea",
                         "uv.lock", "*.egg-info"}:
                continue
            files.add(item)
    except PermissionError:
        pass
    return files


# ── Reporting ──


def print_check_results(findings: list[Finding]) -> None:
    """Display check results in a formatted way."""
    if not findings:
        print("\n✅ 未发现问题\n")
        return

    print(f"\n{'='*60}")
    print(f"   发现 {len(findings)} 个问题")
    print(f"{'='*60}")

    for f in sorted(findings, key=lambda x: (x.rule_id, x.project)):
        color = "\033[93m" if f.rule_id in {"#1", "#5", "#6"} else "\033[91m"
        print(f"\n  {color}{f.rule_id} [{f.project}]{_reset()}")
        print(f"   问题: {f.issue}")
        print(f"   详情: {f.detail}")

    print()


def _reset() -> str:
    return "\033[0m"
