from __future__ import annotations

import os

from tass.models import ProjectInfo
from tass import detector
from tass import store

# Directories/patterns to skip during scanning
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "tass",  # Skip tass itself
}


def is_skip_dir(name: str) -> bool:
    """Check if a directory should be skipped."""
    return name.startswith(".") or name in SKIP_DIRS


def scan_projects(root_dir: str) -> list[ProjectInfo]:
    """Scan root_dir for projects and return their metadata."""
    projects: list[ProjectInfo] = []

    if not os.path.isdir(root_dir):
        print(f"⚠  扫描目录不存在: {root_dir}")
        return projects

    try:
        entries = sorted(os.listdir(root_dir))
    except PermissionError:
        print(f"⚠  无权限访问: {root_dir}")
        return projects

    for entry in entries:
        full_path = os.path.join(root_dir, entry)

        # Skip non-directories and excluded directories
        if not os.path.isdir(full_path):
            continue
        if is_skip_dir(entry):
            continue

        try:
            info = _scan_single_project(entry, full_path)
            projects.append(info)
        except Exception as e:
            print(f"⚠  扫描项目 {entry} 时出错: {e}")
            # Still add a minimal entry
            projects.append(ProjectInfo(
                name=entry,
                path=full_path,
                type="Unknown",
                entry_points=[],
                has_readme=False,
                readme_preview="",
                dependencies=[],
                git_status="no_git",
                last_modified="",
                has_pyproject=False,
                subdirs=[],
            ))

    return projects


def _scan_single_project(name: str, path: str) -> ProjectInfo:
    """Scan a single project directory and return its metadata."""
    # Type detection
    proj_type = detector.detect_project_type(path)

    # Entry points
    entry_points = detector.detect_entry_points(path)

    # Dependencies
    dependencies = detector.detect_dependencies(path)

    # README
    has_readme, readme_preview = detector.detect_readme_preview(path)

    # Git status
    git_status = detector.detect_git_status(path)

    # Last modified
    last_modified = detector.detect_last_modified(path)

    # pyproject.toml
    has_pyproject = os.path.isfile(os.path.join(path, "pyproject.toml"))

    # Subdirectories
    subdirs = detector.get_subdirs(path)

    return ProjectInfo(
        name=name,
        path=path,
        type=proj_type,
        entry_points=entry_points,
        has_readme=has_readme,
        readme_preview=readme_preview,
        dependencies=dependencies,
        git_status=git_status,
        last_modified=last_modified,
        has_pyproject=has_pyproject,
        subdirs=subdirs,
    )


def run_scan(scan_dir: str | None = None) -> None:
    """Run a scan and save results."""
    if scan_dir is None:
        scan_dir = os.path.expanduser("/home/socket/projects")

    print(f"🔍 扫描目录: {scan_dir}")
    projects = scan_projects(scan_dir)

    store.save_project_index(projects)
    print(f"✅ 扫描完成，发现 {len(projects)} 个项目")
    print(f"   结果已保存到 {store.get_project_index_path()}")

    # Print summary
    for p in projects:
        git_mark = "✓" if p.git_status == "clean" else ("⚡" if p.git_status == "dirty" else "-")
        print(f"   [{p.type:12}] {p.name:<20} {git_mark} {', '.join(p.entry_points) if p.entry_points else '-'}")
