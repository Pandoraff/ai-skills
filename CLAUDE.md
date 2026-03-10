# CLAUDE.md — 仓库操作指南

本文件供 AI（Claude Code 等）在操作此仓库时参考。请在修改任何文件前先完整阅读本文件。

---

## 仓库用途

这是一个 **Claude Code Skills 合集仓库**。每个 skill 是一个可安装到 Claude Code 的功能扩展，放在 `skills/` 目录下。

---

## 目录结构

```
claude-skills/                        ← 仓库根目录
├── CLAUDE.md                         ← 本文件（AI 操作指南）
├── README.md                         ← 仓库总览（面向人类读者）
├── .claude-plugin/
│   └── plugin.json                   ← 插件清单（仓库级元信息）
└── skills/
    ├── pdf-to-image/                 ← skill 示例
    │   ├── SKILL.md                  ← skill 定义（必须）
    │   ├── scripts/                  ← 可选：辅助脚本
    │   ├── references/               ← 可选：参考文档
    │   └── assets/                   ← 可选：模板/资源文件
    └── <other-skill>/
        └── SKILL.md
```

---

## 添加新 Skill

### 1. 在 `skills/` 下创建目录

目录名即 skill 名，使用小写连字符格式（kebab-case）：

```bash
skills/<skill-name>/
```

### 2. 创建 `SKILL.md`（必须）

SKILL.md 是每个 skill 的核心文件，格式如下：

```markdown
---
name: skill-name
description: 一句话说明该 skill 的用途和触发时机。描述要具体，
  包含用户可能说出的关键词，让 Claude 能准确判断何时使用它。
---

# Skill 标题

## 功能说明
...

## 使用方式
...
```

**description 字段是触发机制**，写得越具体、覆盖的触发场景越多，skill 被正确调用的概率越高。

### 3. 按需添加辅助文件

| 目录 | 用途 |
|------|------|
| `scripts/` | 可执行脚本（Python、Shell 等），减少重复工作 |
| `references/` | 供 Claude 按需读取的参考文档 |
| `assets/` | 模板文件、图标等静态资源 |

### 4. 更新根目录 README.md

在 README 的 **Skills 列表**表格中追加一行：

```markdown
| [skill-name](skills/skill-name/) | 一句话描述 |
```

### 5. 提交

```bash
git add skills/<skill-name>/ README.md
git commit -m "feat(skills): add <skill-name> skill"
git push
```

---

## 修改已有 Skill

修改 skill 时，**必须同步更新以下所有相关内容**，不能只改其中一处：

| 修改内容 | 需要同步更新 |
|----------|-------------|
| skill 的功能逻辑 | `SKILL.md` 正文中的说明和步骤 |
| 触发场景变化 | `SKILL.md` frontmatter 的 `description` 字段 |
| 新增/删除脚本 | `SKILL.md` 中对脚本的引用说明 |
| 新增/删除参数或选项 | `SKILL.md` 中的参数说明表格 |
| 功能名称或用途变化 | 根目录 `README.md` 的 Skills 列表描述 |

修改完成后提交：

```bash
git add skills/<skill-name>/
git commit -m "fix(skills): <描述修改内容>"
git push
```

---

## SKILL.md 写作规范

- **frontmatter `name`**：与目录名保持一致
- **frontmatter `description`**：面向 Claude 触发判断，不是面向用户的说明，要包含具体触发词
- **正文**：面向执行 skill 的 Claude，使用祈使句，解释"为什么"而非只写"做什么"
- **长度**：尽量控制在 500 行以内；如内容多，拆分到 `references/` 子文件并在 SKILL.md 中注明何时读取
- **脚本引用**：在 SKILL.md 中写明脚本路径和调用方式，让 Claude 知道脚本的存在

---

## 禁止事项

- 不要直接修改 `.claude-plugin/plugin.json` 的 `name` 字段（会破坏插件识别）
- 不要在 `skills/` 以外的位置存放 skill 定义文件
- 不要删除 `SKILL.md`（这是每个 skill 的必须文件）
- 修改 skill 功能后，不要遗漏更新 README 和 SKILL.md 的 description
