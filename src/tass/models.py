from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass
class ProjectInfo:
    """扫描结果：自动生成的项目信息。"""

    name: str
    path: str
    type: str  # CrewAI / LangChain / FastAPI / Node / Python / Unknown
    entry_points: list[str]
    has_readme: bool
    readme_preview: str
    dependencies: list[str]
    git_status: str  # clean / dirty / no_git
    last_modified: str  # ISO format
    has_pyproject: bool
    subdirs: list[str]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ProjectInfo:
        return cls(**d)


@dataclasses.dataclass
class ProjectMeta:
    """人工维护的项目语义信息。"""

    learning_days: list[int]
    title: str
    status: str  # completed / in_progress / abandoned
    tags: list[str]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ProjectMeta:
        return cls(**d)


@dataclasses.dataclass
class Finding:
    """check 命令的输出结构。"""

    rule_id: str  # "#1" / "#3" / "#5" / "#6"
    project: str
    issue: str
    detail: str


@dataclasses.dataclass
class NoteEntry:
    """解析笔记中的每一天。"""

    day: int
    title: str
    date: str
    content: str  # full content between ## headers
    project: Optional[str] = None
    status: Optional[str] = None  # completed / in_progress / pending
