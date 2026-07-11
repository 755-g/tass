from __future__ import annotations

import os
import re
from typing import Optional

from tass.models import NoteEntry

# Regex to match note day headers:
# ## 第1天：Function Calling 基础 | 2026-07-03
_DAY_HEADER_RE = re.compile(r"^## 第(\d+)天：(.+?) \| (\d{4}-\d{2}-\d{2})\s*$")

# Regex for project reference in "### 代码位置" section
_CODE_LOCATION_RE = re.compile(r"### 代码位置.*?\n([^#]+)", re.DOTALL)

# Status indicators in notes
_STATUS_PENDING_RE = re.compile(r"⏳\s*待开始")
_STATUS_COMPLETED_RE = re.compile(r"⚠️\s*代码状态")


def parse_notes(file_path: str) -> list[NoteEntry]:
    """Parse the markdown notes file into NoteEntry objects.

    Each entry starts with '## 第N天：标题 | YYYY-MM-DD' and ends at the next
    similar header or end of file.
    """
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    entries: list[NoteEntry] = []
    lines = content.split("\n")
    current_entry: Optional[dict] = None
    current_lines: list[str] = []

    for line in lines:
        m = _DAY_HEADER_RE.match(line)
        if m:
            # Save previous entry
            if current_entry is not None:
                entry_content = "\n".join(current_lines).strip()
                entry = NoteEntry(
                    day=current_entry["day"],
                    title=current_entry["title"],
                    date=current_entry["date"],
                    content=entry_content,
                    project=_extract_project(entry_content),
                    status=_extract_status(entry_content),
                )
                entries.append(entry)

            # Start new entry
            current_entry = {
                "day": int(m.group(1)),
                "title": m.group(2).strip(),
                "date": m.group(3),
            }
            current_lines = [line]
        else:
            if current_entry is not None:
                current_lines.append(line)

    # Last entry
    if current_entry is not None:
        entry_content = "\n".join(current_lines).strip()
        entry = NoteEntry(
            day=current_entry["day"],
            title=current_entry["title"],
            date=current_entry["date"],
            content=entry_content,
            project=_extract_project(entry_content),
            status=_extract_status(entry_content),
        )
        entries.append(entry)

    return entries


def _extract_project(content: str) -> Optional[str]:
    """Extract associated project name from 代码位置 section.

    The section typically contains a path like '~/projects/joke-pipeline/'
    from which we extract the project directory name.
    """
    m = _CODE_LOCATION_RE.search(content)
    if m:
        section = m.group(1).strip()
        # Look for project path patterns
        path_match = re.search(r"~/?projects?/([^/\s\)]+)", section)
        if path_match:
            return path_match.group(1)
        # Also try raw paths like `/home/socket/projects/xxx`
        path_match = re.search(r"/home/socket/projects/([^/\s\)]+)", section)
        if path_match:
            return path_match.group(1)
        # Just check first line of section if it's a simple project dir name
        first_line = section.split("\n")[0].strip().rstrip("/")
        if first_line and not first_line.startswith("`") and not first_line.startswith("#"):
            # Might be a bare directory name
            return first_line
    return None


def _extract_status(content: str) -> Optional[str]:
    """Extract completion status from note content."""
    if _STATUS_PENDING_RE.search(content):
        return "pending"
    if _STATUS_COMPLETED_RE.search(content):
        # Check if it mentions "已丢失" or similar
        if re.search(r"已丢失|已删除|不适用", content):
            return "abandoned"
        return "completed"
    return None


# ── Public API ──


def list_notes(file_path: str, metas: dict | None = None) -> list[NoteEntry]:
    """Parse and return all note entries from the given file."""
    entries = parse_notes(file_path)
    if not entries:
        print(f"⚠  笔记文件中未找到有效的天数条目: {file_path}")
        return entries

    # Header
    header = f"{'天数':<6} {'标题':<30} {'日期':<12} {'关联项目':<18} {'状态':<12}"
    print(f"\n{header}")
    print("-" * len(header))

    for entry in entries:
        status_str = entry.status or "—"
        project_str = entry.project or "—"
        print(f"{entry.day:<6} {entry.title:<30} {entry.date:<12} {project_str:<18} {status_str:<12}")

    print()
    return entries


def show_note(file_path: str, day: int) -> None:
    """Display the full content of a specific day's entry."""
    entries = parse_notes(file_path)
    if not entries:
        print(f"⚠  笔记文件中未找到有效的天数条目: {file_path}")
        return

    for entry in entries:
        if entry.day == day:
            print(f"\n── 第{day}天：{entry.title} | {entry.date} ──\n")
            # Show content without the header line
            lines = entry.content.split("\n")
            if lines:
                # Skip the ## header line (first line)
                body = "\n".join(lines[1:]).strip()
                if body:
                    print(body)
                else:
                    print("(空内容)")
            return

    print(f"⚠  未找到第 {day} 天的笔记")
    print(f"   笔记文件: {file_path}")


def create_note(file_path: str, day: int, title: str) -> None:
    """Append a new day entry template to the notes file."""
    if not os.path.isfile(file_path):
        print(f"⚠  笔记文件不存在: {file_path}")
        return

    # Check for duplicate day
    entries = parse_notes(file_path)
    for entry in entries:
        if entry.day == day:
            print(f"⚠  第 {day} 天已存在: 第{entry.day}天：{entry.title} | {entry.date}")
            print(f"   请使用 `tass notes show {day}` 查看现有内容")
            return

    # Generate template
    template = (
        f"\n---\n"
        f"\n"
        f"## 第{day}天：{title} | {datetime_now()}\n"
        f"\n"
        f"### 学习目标\n"
        f"\n"
        f"### 代码位置\n"
        f"**`~/projects/`**\n"
        f"\n"
        f"### 完成内容\n"
        f"\n"
        f"### 踩坑记录\n"
    )

    # Append to file
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(template)
        print(f"✅ 已在笔记文件末尾追加第 {day} 天模板")
        print(f"   文件: {file_path}")
    except IOError as e:
        print(f"⚠  写入笔记文件失败: {e}")


def datetime_now() -> str:
    """Return current date as ISO string (avoiding timezone complexity)."""
    from datetime import date
    return date.today().isoformat()
