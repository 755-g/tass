# tass

`tass`（Terminal Assistant）是一个用于管理 Agent 学习项目的命令行工具。
它可以扫描项目目录、识别项目类型、查看入口文件和依赖，并检查学习笔记与实际代码之间的偏差。

## 特点

- 纯 Python 标准库实现，无外部运行时依赖
- 支持扫描项目类型、入口文件、依赖和 Git 状态
- 使用 `project_meta.json` 保存学习阶段、状态和标签
- 支持按天查看和追加学习笔记
- 支持检查笔记引用的项目、文件和路径
- 不接入大模型，不产生 API 费用

## 环境要求

- WSL/Linux
- Python 3.12+
- `uv`

## 快速开始

在项目目录中运行：

```bash
cd /home/socket/projects/tass
uv run tass --help
```

首次扫描项目：

```bash
uv run tass scan
```

默认扫描目录为 `/home/socket/projects/`，扫描结果保存到：

```text
data/project_index.json
```

## 常用命令

```bash
# 扫描默认项目目录
uv run tass scan

# 扫描指定目录
uv run tass scan --dir /some/path

# 查看项目概览
uv run tass list

# 查看单个项目
uv run tass show latest_ai_flow

# 检查笔记和项目的一致性
uv run tass check

# 查看所有学习笔记
uv run tass notes list

# 查看指定天数的笔记
uv run tass notes show 3

# 使用其他笔记文件
uv run tass notes --file /some/notes.md list

# 追加新的学习笔记模板
uv run tass notes create 5 "新的学习主题"
```

## 数据文件

`data/project_index.json` 是扫描自动生成的项目索引，不建议手动编辑。

`data/project_meta.json` 用于补充自动扫描无法判断的学习信息，例如：

```json
{
  "latest_ai_flow": {
    "learning_days": [3, 4],
    "title": "CrewAI 健身计划多 Agent",
    "status": "completed",
    "tags": ["CrewAI", "提示注入", "Agent安全"]
  }
}
```

支持的状态包括：`completed`、`in_progress` 和 `abandoned`。

## 项目结构

```text
tass/
├── data/
├── src/tass/
│   ├── cli.py
│   ├── detector.py
│   ├── scanner.py
│   ├── check.py
│   ├── notes.py
│   ├── models.py
│   ├── reports.py
│   └── store.py
├── pyproject.toml
└── uv.lock
```

## 当前范围

当前版本使用确定性规则完成扫描和检查，不接入大模型，也不提供 Web 界面。
`data/project_index.json`、Python 缓存和构建产物不会提交到 Git。
