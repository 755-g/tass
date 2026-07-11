# tass 使用教程

## 1. 工具简介

tass（Terminal Assistant）是一个用于管理 Agent 学习项目的命令行工具。

它可以：

- 扫描项目目录并识别项目类型
- 查找入口文件、依赖和 Git 状态
- 汇总多个学习项目的信息
- 查看和管理按天记录的学习笔记
- 检查笔记与实际项目之间的路径、文件和目录结构差异

当前版本不接入大模型，使用 Python 标准库和确定性规则运行。

## 2. 环境要求

- WSL/Linux
- Python 3.12 或更高版本
- uv

进入项目目录：

~~~bash
cd /home/socket/projects/tass
~~~

查看帮助：

~~~bash
uv run tass --help
~~~

开发阶段推荐始终使用 uv run tass，这样可以自动使用当前项目环境。

## 3. 第一次扫描

执行：

~~~bash
uv run tass scan
~~~

默认扫描：

~~~text
/home/socket/projects/
~~~

也可以指定其他目录：

~~~bash
uv run tass scan --dir /some/other/path
~~~

扫描结果保存到：

~~~text
data/project_index.json
~~~

这个文件是自动生成的，不要手动编辑。项目发生变化后，重新执行 scan 更新索引。

扫描时会跳过：

- 隐藏目录
- .git
- .venv
- venv
- __pycache__
- node_modules
- 构建产物目录

## 4. 查看项目

### 查看全部项目

~~~bash
uv run tass list
~~~

列表会显示项目名称、类型、学习阶段和状态。

如果项目还没有人工元数据，学习阶段和状态会显示为 --。

### 查看单个项目

~~~bash
uv run tass show latest_ai_flow
~~~

项目名称不区分大小写。详细信息包括：

- 项目路径
- 项目类型
- 入口文件
- 依赖
- README 摘要
- Git 状态
- 最近修改时间
- 一级子目录
- 人工维护的学习信息

## 5. 维护项目元数据

自动扫描只能发现文件事实，无法准确判断项目属于学习第几天或是否完成。这些信息写在：

~~~text
data/project_meta.json
~~~

示例：

~~~json
{
  "joke-pipeline": {
    "learning_days": [2],
    "title": "LangChain 与 MCP Agent",
    "status": "completed",
    "tags": ["LangChain", "MCP", "Function Calling"]
  },
  "latest_ai_flow": {
    "learning_days": [3, 4],
    "title": "CrewAI 健身计划多 Agent",
    "status": "completed",
    "tags": ["CrewAI", "提示注入", "Agent安全"]
  }
}
~~~

支持的状态：

- completed：已完成
- in_progress：进行中
- abandoned：已放弃或不再使用

修改元数据后，重新运行：

~~~bash
uv run tass list
uv run tass show latest_ai_flow
~~~

## 6. 管理学习笔记

默认笔记文件是：

~~~text
/home/socket/projects/agent-learning-notes/Agent学习笔记.md
~~~

查看学习天数列表：

~~~bash
uv run tass notes list
~~~

查看某一天：

~~~bash
uv run tass notes show 3
~~~

使用其他笔记文件：

~~~bash
uv run tass notes --file /some/notes.md list
uv run tass notes --file /some/notes.md show 3
~~~

创建新一天的模板：

~~~bash
uv run tass notes create 5 "ReAct 与 Agent 编程"
~~~

这个命令会直接在笔记文件末尾追加模板，并且会拒绝重复的天数。执行前请确认天数和标题，因为它会修改原始 Markdown 文件。

## 7. 检查笔记和项目的一致性

执行：

~~~bash
uv run tass check
~~~

当前检查规则包括：

- 笔记中列出的项目目录是否存在
- 笔记中引用的文件是否存在
- WSL 环境中是否仍然使用 Windows 路径
- 笔记描述的目录或文件是否已经被删除

检查结果是辅助审计，不是 Python 代码静态分析器。对于嵌套目录、函数名称和历史笔记，结果需要结合实际项目人工确认。

## 8. 推荐的日常流程

项目结构发生变化后：

~~~bash
cd /home/socket/projects/tass
uv run tass scan
uv run tass list
uv run tass check
~~~

想回顾学习内容时：

~~~bash
uv run tass notes list
uv run tass notes show 3
~~~

想深入查看一个项目时：

~~~bash
uv run tass show latest_ai_flow
~~~

## 9. Git 工作流

查看状态：

~~~bash
git status
~~~

提交修改：

~~~bash
git add .
git commit -m "描述本次修改"
~~~

推送到 GitHub：

~~~bash
git push
~~~

查看提交历史：

~~~bash
git log --oneline
~~~

生成的 data/project_index.json、Python 缓存、*.egg-info 和虚拟环境已经由 .gitignore 排除，不应提交到仓库。

## 10. 常见问题

### 找不到 tass 命令

请确认当前位于项目目录，并使用：

~~~bash
uv run tass --help
~~~

### list 没有显示最新变化

先重新扫描：

~~~bash
uv run tass scan
~~~

list 读取的是上一次扫描保存的索引。

### 项目状态显示为 --

说明项目还没有在 data/project_meta.json 中维护人工元数据。

### notes 没有解析出内容

检查笔记标题是否符合格式：

~~~markdown
## 第3天：学习主题 | 2026-07-10
~~~

### push 被 GitHub 拒绝

先测试 SSH：

~~~bash
ssh -T git@github.com
~~~

如果出现 Permission denied (publickey)，说明当前 WSL 的 SSH 公钥还没有正确添加到 GitHub 账号，或 SSH Agent 没有加载私钥。
