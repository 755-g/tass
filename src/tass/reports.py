from __future__ import annotations

from typing import Optional

from tass.models import ProjectInfo, ProjectMeta
from tass import store

# ANSI color codes (simple, no dependency on rich)
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"
_GRAY = "\033[90m"


def _na(val: str | None) -> str:
    """Return '--' for None or empty values."""
    if not val:
        return f"{_GRAY}--{_RESET}"
    return val


def _bool_mark(val: bool) -> str:
    return f"{_GREEN}✓{_RESET}" if val else f"{_RED}✗{_RESET}"


def _status_str(status: str | None) -> str:
    if status == "completed":
        return f"{_GREEN}completed{_RESET}"
    elif status == "in_progress":
        return f"{_YELLOW}in_progress{_RESET}"
    elif status == "abandoned":
        return f"{_RED}abandoned{_RESET}"
    return _na(status)


def _git_status_str(status: str) -> str:
    if status == "clean":
        return f"{_GREEN}clean{_RESET}"
    elif status == "dirty":
        return f"{_YELLOW}dirty{_RESET}"
    return _na(status)


def _type_str(t: str) -> str:
    colors = {
        "CrewAI": _CYAN,
        "LangChain": _GREEN,
        "FastAPI": _YELLOW,
        "Node": _GREEN,
        "Python": _GREEN,
    }
    c = colors.get(t, _GRAY)
    return f"{c}{t}{_RESET}"


def _truncate(s: str, max_len: int = 30) -> str:
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


# ── list: table view ──


def print_project_list(projects: list[ProjectInfo], metas: dict[str, ProjectMeta]) -> None:
    """Print a formatted table of all projects merged with metadata."""
    if not projects and not metas:
        print("没有发现项目。请先运行 `tass scan`。")
        return

    # Header
    header = f"{'项目名':<22} {'类型':<12} {'学习天数':<10} {'状态':<14} {'入口':<16} {'Git':<8}"
    sep = "-" * len(header)
    print(f"\n{_BOLD}{header}{_RESET}")
    print(sep)

    # Build merged view: scan entries first, then meta-only entries
    shown: set[str] = set()

    for p in projects:
        meta_key, meta = store.find_meta_case_insensitive(metas, p.name)
        days = _na(", ".join(str(d) for d in meta.learning_days) if meta else None)
        status = _status_str(meta.status if meta else None)
        ep = ", ".join(p.entry_points) if p.entry_points else _na(None)
        git = _git_status_str(p.git_status)

        print(
            f"{p.name:<22} "
            f"{_type_str(p.type):<20} "
            f"{days:<10} "
            f"{status:<20} "
            f"{ep:<16} "
            f"{git:<8}"
        )
        shown.add(meta_key) if meta_key else shown.add(p.name.lower())

    # Meta-only entries (not in scan results)
    for key, meta in metas.items():
        if key.lower() not in shown:
            days = ", ".join(str(d) for d in meta.learning_days)
            status = _status_str(meta.status)
            print(
                f"{key:<22} "
                f"{_na('--'):<20} "
                f"{days:<10} "
                f"{status:<20} "
                f"{_na('--'):<16} "
                f"{_na('--'):<8}"
            )

    print()


# ── show: detailed view ──


def print_project_detail(
    name: str,
    project: Optional[ProjectInfo],
    meta: Optional[ProjectMeta],
) -> None:
    """Print detailed information for a single project."""
    print(f"\n{_BOLD}{'='*60}{_RESET}")
    print(f"{_BOLD}  项目: {name}{_RESET}")
    print(f"{_BOLD}{'='*60}{_RESET}")

    # Scan data section
    print(f"\n{_CYAN}── 扫描数据 ──{_RESET}")
    if project:
        print(f"  路径:          {project.path}")
        print(f"  类型:          {_type_str(project.type)}")
        print(f"  入口文件:      {', '.join(project.entry_points) if project.entry_points else _na(None)}")
        print(f"  README:        {_bool_mark(project.has_readme)}")
        if project.has_readme and project.readme_preview:
            print(f"  预览:          {_truncate(project.readme_preview, 80)}")
        print(f"  关键依赖:      {', '.join(project.dependencies) if project.dependencies else _na(None)}")
        print(f"  Git:           {_git_status_str(project.git_status)}")
        print(f"  最近修改:      {project.last_modified or _na(None)}")
        print(f"  pyproject.toml: {_bool_mark(project.has_pyproject)}")
        print(f"  子目录:        {', '.join(project.subdirs) if project.subdirs else _na(None)}")
    else:
        print(f"  {_GRAY}-- 尚未扫描 --{_RESET}")
        print(f"  提示: 运行 `tass scan` 来扫描此项目")

    # Meta data section
    print(f"\n{_YELLOW}── 人工元数据 ──{_RESET}")
    if meta:
        days = ", ".join(str(d) for d in meta.learning_days)
        print(f"  学习天数:      {days}")
        print(f"  标题:          {meta.title}")
        print(f"  状态:          {_status_str(meta.status)}")
        print(f"  标签:          {', '.join(meta.tags) if meta.tags else _na(None)}")
    else:
        print(f"  {_GRAY}-- 无元数据 --{_RESET}")
        print(f"  提示: 编辑 {store.get_project_meta_path()} 添加元数据")

    print()
