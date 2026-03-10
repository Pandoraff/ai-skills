# ai-skills

AI Skills 合集，供各类 AI 编程助手（Claude Code、GitHub Copilot 等）使用的功能扩展。

## Skills 列表

| Skill | 描述 |
|-------|------|
| [pdf-to-image](skills/pdf-to-image/) | 将 PDF 转换为 JPEG 图片，支持目标文件大小控制 |

## 仓库结构

```
ai-skills/
├── CLAUDE.md                   # AI 操作指南（添加/修改 skill 的规范）
├── README.md                   # 本文件
├── .claude-plugin/
│   └── plugin.json             # Claude Code 插件清单
└── skills/
    └── <skill-name>/
        ├── SKILL.md            # Skill 定义（必须）
        ├── scripts/            # 辅助脚本（可选）
        ├── references/         # 参考文档（可选）
        └── assets/             # 静态资源（可选）
```

## 添加新 Skill

详见 [CLAUDE.md](CLAUDE.md)，其中包含完整的目录规范、SKILL.md 写作要求和更新检查清单。

---

## pdf-to-image

将 PDF 文件转换为 JPEG 图片，精准控制输出文件大小。

**特性：**
- 多后端自动检测：`gs` → `pdftoppm+convert` → `pdftoppm` → `pdf2image` → `fitz`
- 二分法质量调节，命中目标 KB 大小
- 多页 PDF 自动按页分割输出

**快速使用：**

```bash
python3 skills/pdf-to-image/scripts/pdf2jpeg.py input.pdf --target-kb 250
```

详细文档见 [skills/pdf-to-image/SKILL.md](skills/pdf-to-image/SKILL.md)。
