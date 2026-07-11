#!/usr/bin/env python3
"""tass - Terminal Assistant: Agent learning project manager.

Usage:
    tass scan [--dir <path>]
    tass list
    tass show <project_name>
    tass check
    tass notes [--file <path>] list
    tass notes [--file <path>] show <day>
    tass notes [--file <path>] create <day> <title>
"""

from __future__ import annotations

import argparse
import os
import sys

from tass import scanner
from tass import store
from tass import reports
from tass import check as check_module
from tass import notes as notes_module

DEFAULT_PROJECTS_DIR = "/home/socket/projects"
DEFAULT_NOTES_FILE = os.path.join(
    DEFAULT_PROJECTS_DIR, "agent-learning-notes", "Agent学习笔记.md"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tass",
        description="终端助手 - Agent 学习项目管理工具",
        epilog="使用 `tass <command> --help` 查看子命令帮助",
    )
    parser.add_argument(
        "--version", action="version",
        version="tass 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ── scan ──
    scan_parser = subparsers.add_parser("scan", help="扫描项目目录")
    scan_parser.add_argument(
        "--dir", "-d",
        default=DEFAULT_PROJECTS_DIR,
        help=f"要扫描的目录（默认: {DEFAULT_PROJECTS_DIR}）",
    )

    # ── list ──
    subparsers.add_parser("list", help="列出所有项目")

    # ── show ──
    show_parser = subparsers.add_parser("show", help="显示单个项目详情")
    show_parser.add_argument("name", help="项目名")

    # ── check ──
    subparsers.add_parser("check", help="检查笔记与项目的一致性")

    # ── notes ──
    notes_parser = subparsers.add_parser("notes", help="管理学习笔记")
    notes_parser.add_argument(
        "--file", "-f",
        default=None,
        help=f"笔记文件路径（默认: {DEFAULT_NOTES_FILE}）",
    )
    notes_sub = notes_parser.add_subparsers(dest="notes_command", help="笔记子命令")

    notes_list = notes_sub.add_parser("list", help="列出所有笔记条目")
    notes_show = notes_sub.add_parser("show", help="显示指定天数的笔记")
    notes_show.add_argument("day", type=int, help="学习天数")
    notes_create = notes_sub.add_parser("create", help="创建新的笔记条目")
    notes_create.add_argument("day", type=int, help="学习天数")
    notes_create.add_argument("title", help="笔记标题")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # ── Execute commands ──

    if args.command == "scan":
        scanner.run_scan(args.dir)

    elif args.command == "list":
        projects = store.load_project_index()
        metas = store.load_project_meta()
        reports.print_project_list(projects, metas)

    elif args.command == "show":
        projects = store.load_project_index()
        metas = store.load_project_meta()

        # Try to find project and meta (case-insensitive)
        project = store.find_project_case_insensitive(projects, args.name)
        _, meta = store.find_meta_case_insensitive(metas, args.name)

        if project is None and meta is None:
            print(f"⚠  未找到项目: {args.name}")
            print(f"   提示: 运行 `tass scan` 扫描项目，或编辑 "
                  f"{store.get_project_meta_path()} 添加元数据")
            sys.exit(1)

        reports.print_project_detail(args.name, project, meta)

    elif args.command == "check":
        findings = check_module.run_check()
        check_module.print_check_results(findings)

    elif args.command == "notes":
        notes_file = args.file if args.file else DEFAULT_NOTES_FILE

        if not os.path.isfile(notes_file):
            print(f"⚠  笔记文件不存在: {notes_file}")
            sys.exit(1)

        if args.notes_command == "list":
            metas = store.load_project_meta()
            notes_module.list_notes(notes_file, metas)

        elif args.notes_command == "show":
            notes_module.show_note(notes_file, args.day)

        elif args.notes_command == "create":
            notes_module.create_note(notes_file, args.day, args.title)

        else:
            # No notes subcommand given, show help
            notes_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
