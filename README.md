# Zotero Paper Summary

用 Claude（或其它支持 skill 的 AI agent）从 Zotero 文献一键生成论文解读 PDF，并自动作为附件挂回 Zotero 对应条目。

只需提供一个 Better BibTeX 的 **citation-key**，整条链路自动完成：

```
citekey  ──►  解析原论文 PDF  ──►  生成解读 PDF（紧凑 1-2 页 / 详细多章节）  ──►  作为附件挂回 Zotero
```

![解读 PDF 示例](asserts/demo.png)

## 组成

本仓库包含两部分，配合使用：

| 目录 | 作用 |
|------|------|
| [`plugin/`](plugin/) | **Paper Summary Bridge** —— 一个极简 Zotero 插件，注册本地 HTTP endpoint，把生成好的 PDF 通过官方 API 挂载为附件 |
| [`skill/`](skill/) | **paper_summary skill** —— 给 AI agent 的规范，定义如何用 citekey 解析论文、生成 LaTeX 解读 PDF、调用 bridge 挂载 |

```
zotero-paper-summary/
├── plugin/
│   ├── src/
│   │   ├── manifest.json     # 插件清单（Zotero 7+ bootstrap）
│   │   └── bootstrap.js      # 注册 /paper-bridge/attach endpoint
│   ├── paper-bridge.xpi      # 打包好的插件，可直接安装
│   └── build.sh              # 从 src/ 重新打包 xpi
└── skill/
    ├── SKILL.md              # 解读 PDF 生成规范（核心）
    └── assets/
        └── paper_style.tex   # LaTeX 样式模板（配色/环境/preamble）
```

## 工作原理

1. **解析**：skill 调用 Better BibTeX 的 JSON-RPC `item.attachments(citekey)`，拿到原论文 PDF 的绝对路径和附件 key。
2. **生成**：AI agent 按 `SKILL.md` 规范，从原 PDF 截图、用 `xelatex` 编译出解读 PDF（默认紧凑 1-2 页，可要求详细多章节版）。
3. **挂载**：skill `POST` 到插件的本地 endpoint `http://127.0.0.1:23119/paper-bridge/attach`，插件内部调用官方 `Zotero.Attachments.importFromFile` 把 PDF 作为 `imported_file` 附件挂到论文条目下——走官方 API，**不直接改数据库，零损库风险**。

## 安装

### 前置依赖

- **Zotero 7+**（在 Zotero 9.0.4 上验证通过），且保持运行
- **[Better BibTeX](https://retorque.re/zotero-better-bibtex/)** 插件（提供 citekey 与 JSON-RPC 解析）
- 生成 PDF 需要 **TeX Live**（`xelatex`）与 **pymupdf**（`pip install pymupdf`，用于截图）

### 1. 安装 Bridge 插件

在 Zotero 中：**工具 → 插件 → 右上角齿轮 → Install Add-on From File**，选择 [`plugin/paper-bridge.xpi`](plugin/paper-bridge.xpi)。

验证是否生效（返回 `400` 且提示缺参数即为成功）：

```bash
curl -s -X POST http://127.0.0.1:23119/paper-bridge/attach \
  -H 'Content-Type: application/json' -d '{}'
# 预期: 缺少 attachmentKey 或 reportPath
```

> 想自行修改插件后重新打包：`bash plugin/build.sh`

### 2. 安装 skill

把 `skill/` 内容放到你的 AI agent 的 skill 目录。以 Claude Code 为例：

```bash
cp -r skill ~/.claude/skills/paper_summary
# 或软链到本仓库
```

## 使用

在 AI agent 里直接给出 citekey：

- `解读 suAttentionSinkTransformers2026` —— 默认紧凑 1-2 页简短版
- `详细解读 suAttentionSinkTransformers2026` —— 详细多章节、图文并茂版

agent 会自动解析原 PDF、生成解读 PDF，并挂到该论文条目下。

## 两种解读模式

| 模式 | 触发 | 篇幅 | 文件名 |
|------|------|------|--------|
| **简短（默认）** | 未明确要求"详细" | 紧凑 1-2 页 | `<论文标题>_brief.pdf` |
| **详细** | 明确说"详细/完整/图文并茂" | 逐章节深入 | `<论文标题>.pdf` |

解读 PDF 的排版规范（中文叙述、术语保留英文、公式用 LaTeX、关键图截图、数值例子、AI 批判性分析等）详见 [`skill/SKILL.md`](skill/SKILL.md)。

## Bridge 插件接口

`POST http://127.0.0.1:23119/paper-bridge/attach`

请求体：

```json
{
  "attachmentKey": "NZ5LELWY",
  "reportPath": "/abs/path/to/report.pdf",
  "title": "AI 解读报告 - 论文标题"
}
```

- `attachmentKey`：论文现有 PDF 附件的 key，插件据此反查父条目（无需手动指定父 item）
- `reportPath`：要挂载的 PDF 绝对路径
- `title`（可选）：附件显示名

成功返回：

```json
{"ok": true, "newAttachmentKey": "8HCPQDBP", "parentKey": "H7N45LPU"}
```