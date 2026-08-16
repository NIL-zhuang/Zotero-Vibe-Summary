---
name: paper-summary
description: When the user provides a Zotero Better BibTeX citation-key and asks to summarize/interpret a paper, refer to this rule. The ONLY input is a Zotero citekey; output is an interpretation PDF (brief or detailed) attached back into Zotero.
---

# 学术论文 PDF 解读规范（Zotero citekey 驱动）

本 skill **唯一输入是 Zotero Better BibTeX 的 citation-key**（如 `suAttentionSinkTransformers2026`）。流程固定为：用 citekey 从 Zotero 解析出原论文 PDF → 生成解读 PDF（简短或详细）→ 作为附件挂回 Zotero 对应论文条目。产物**统一用 LaTeX 编写、用 `xelatex` 编译为 PDF**，不生成 HTML/Markdown。

## 零、固定流程（先判定再动手）

动手前先确定**篇幅模式**，其余步骤固定不变：

| 模式 | 触发方式 | 篇幅 | 解读 PDF 文件名 |
|------|---------|------|-----------|
| **简短解读（默认）** | 用户未明确要求"详细"时一律走此模式 | **约 2 页，优先含 1 张主图** | `<论文标题>_brief.pdf` |
| **详细解读** | 用户**明确**说"详细解读""图文并茂""写一份详细的论文报告""完整解读"等 | 不限，逐章节深入 | `<论文标题>.pdf` |

- **默认简短**：只要用户没有明确点名要"详细 / 完整 / 图文并茂"，就走约 2 页的简短模式，并尽量嵌入 1 张最能代表论文贡献的主图。不确定时按简短处理，并在回复里说明"已按约 2 页简短模式生成，需要详细版请告知"。
- 简短模式规范见 **第三章**；详细模式规范见 **第一、二章**；**Zotero 解析与挂载（必做收尾）见第四章**。

### 0.1 整体步骤

1. **拿 citekey**：用户提供 citekey；未提供则要求用户给出，不要用标题猜。
2. **解析原 PDF 与 attachmentKey**（详见 4.1）：调 Better BibTeX JSON-RPC `item.attachments(citekey)`，得到原论文 PDF 的绝对 `path` 和附件 key（从 `open` URL 末段解析）。
3. **创建独立运行目录并生成解读 PDF**：为本次任务创建唯一的临时 `runDir`，写入标记文件 `.paper-summary-run`；所有截图、LaTeX 文件、校验产物及最终解读 PDF 都只能写入该目录。将 skill 自带的 `assets/paper_style.tex` 复制到 `runDir/assets/paper_style.tex` 后再编译。
4. **挂回 Zotero**（详见 4.3）：调 bridge endpoint，把解读 PDF 作为附件挂到该论文条目下。
5. **确认并强制清理**：仅在挂载结果通过 4.4 的成功判定后，删除整个 `runDir`，包括最终解读 PDF；挂载失败则保留 `runDir` 供重试或手动挂载。

### 0.2 独立运行目录与挂载后强制清理

- **先隔离再生成**：每次任务必须创建唯一、绝对路径的临时 `runDir`（目录名以 `paper-summary-` 开头），并在其中创建 `.paper-summary-run` 标记文件。不得直接在当前工作目录、skill 目录或 Zotero storage 中生成过程文件。
- **全部产物进入 `runDir`**：最终解读 PDF、`paper.tex`、`*.aux`、`*.log`、`*.out`、`*.toc`、全文文本、截图、渲染校验图及临时 `assets/` 都必须放入 `runDir`。工作目录不得遗留本次任务的任何文件。
- **模板使用方式**：skill 原始模板 `assets/paper_style.tex` 永远只读、不得删除。编译前将它复制到 `runDir/assets/paper_style.tex`；该临时副本可随 `runDir` 删除。
- **成功后全部删除**：挂载结果满足 4.4 的全部成功条件后，立即删除整个 `runDir`，包括最终生成的 `<论文标题>.pdf` 或 `<论文标题>_brief.pdf`。成功状态下，本地不保留本次任务的任何产物。
- **严格限定删除目标**：删除前必须同时确认：`runDir` 是绝对路径、basename 以 `paper-summary-` 开头、目录内存在 `.paper-summary-run`，且它不是 `/`、当前工作目录、工作区根目录、skill 目录、Zotero 目录或上述目录的父目录。只能删除记录下来的这个精确 `runDir`；禁止清空当前目录、使用宽泛 glob，或删除其父目录。
- **原论文只读**：4.1 解析出的原论文 `path` 只作为输入，永远不得删除、移动、重命名或修改。这里“删除 PDF”只指 `runDir` 中生成的解读 PDF，不是 Zotero storage 中的原论文 PDF。
- **失败必须保留**：请求失败、响应无法解析、成功条件不完整或手动挂载尚未确认时，不得清理 `runDir`。必须向用户报告解读 PDF 的绝对路径以便重试或手动拖入；只有用户明确确认手动挂载完成后才删除 `runDir`。

---

## 详细解读模式

> 以下第一、二章为**详细解读模式**的规范。简短模式直接跳到第三章。

每篇论文**只生成一份合并的完整 PDF**。它既要快速可读（第一页是简洁的 TL;DR + 目录），又要内容翔实（逐章节深入分析、完整公式、数值例子、关键图片截图）。

**解读 PDF 文件名直接用论文原文标题**，把空格和特殊字符（`:`、`/`、`,` 等）全部替换为下划线 `_`（如 `Dynamic_Linear_Attention.pdf`）。

---

## 一、通用要求

- **语言**：正文用中文叙述，但**所有术语一律保留英文原文**，包括 benchmark 名（如 RULER、LongBench、PIQA）、任务名（如 single-needle retrieval、in-context retrieval）、模型/方法名（如 Mamba-2、Gated DeltaNet）、特定操作与机制名（如 state merging、soft gating、hard segmentation）、指标名（如 throughput、accuracy）等。不要把术语翻译成中文（如不要写"吞吐量""单针检索""软门控"，直接用 throughput / single-needle / soft gating）
- **详细程度**：尽可能详尽，不遗漏关键细节。每个方法模块单独成节，配公式、数值例子、关键图片
- **实验与消融**：只做**简要文字概括**（说清结论与趋势即可），**不展示具体数值、不放结果表格**。方法部分的公式与数值例子不受此限制，仍需详尽
- **结构**：用 `\section` / `\subsection` / `\subsubsection` 三级标题组织，层级清晰，PDF 自带书签目录便于跳转
- **引用来源**：所有数据/公式/图片需注明来自原论文的哪个 Section / Table / Figure / Equation
- **文件命名**：解读 PDF 用论文原标题（空格/特殊字符→下划线）；tex 源文件用 `paper.tex`（最终会被清理），编译时通过 `\input{assets/paper_style.tex}` 引用 skill 自带的样式模板。原论文 PDF 在 Zotero storage 里，不复制、不重命名到工作目录

## 二、LaTeX 生成规范（面向 PDF 阅读）

### 2.1 编译工具链

- **编译器**：统一用 `xelatex`（中文支持稳定，本机已装 TeX Live 全套）
- **中文支持**：用 `ctexart` 文档类（内置中文断行、字体、标点）
- **编译命令**：`xelatex -interaction=nonstopmode paper.tex` 连续跑两遍（第一遍生成目录/引用，第二遍定稿）
- **验证**：编译必须零 error；生成的 PDF 中所有公式正常渲染、所有图片正常显示、目录页码正确

### 2.2 文档骨架（固定模板）

配色、风格与全部 preamble（宏包、6 色配色板、`callout`/`example` 环境、定理环境、章节标题配色、hyperref 书签）统一收敛在 skill 自带的 **`assets/paper_style.tex`** 模板里。`paper.tex` 只需引用模板再写正文，**不要把 preamble 重新内联回 `paper.tex`**：

```latex
\documentclass[11pt,a4paper]{ctexart}
\input{assets/paper_style.tex}   % 配色 + 风格 + 完整 preamble，统一复用

\title{\textbf{论文原文标题}}   % 直接用论文英文原标题，不加"整理：AI 助手"等任何额外信息
\author{}
\date{}

\begin{document}
\maketitle
% 第一页：简洁 TL;DR + 目录
\begin{callout}[deeppurple] ... TL;DR（3-5 句核心结论） ... \end{callout}
\tableofcontents
\newpage
% ... 正文 sections ...
\end{document}
```

模板提供的内容（详见 `assets/paper_style.tex`，勿在正文自创）：

- **宏包**：`amsmath/amssymb/amsthm/mathtools/bm`（数学）、`graphicx/booktabs/array/multirow/makecell`、`[table]{xcolor}`、`[margin=2.3cm]{geometry}`、`enumitem`、`tcolorbox`(+skins,breakable)、`titlesec`、`hyperref`(colorlinks, bookmarksnumbered)
- **6 色配色板**：`brandblue`、`okgreen`、`warnorange`、`badred`、`deeppurple`、`headgray`（用途见 2.5）
- **可复用环境**：`callout`（提示框，缺省 brandblue）、`example`（数值例子框）
- **定理环境**：`theorem`（定理）、`corollary`（推论）
- **章节标题**：`\section`/`\subsection`/`\subsubsection` 统一用 headgray 上色

### 2.3 面向 PDF 阅读的排版纪律（重点）

PDF 是连续、可打印、靠目录/书签导航的静态版式，排版要求与网页不同：

1. **单栏、A4、页边距 2.3cm**：行宽适中，长公式不溢出，适合屏幕和打印
2. **第一页 = 简洁 TL;DR + 目录**：首页只放标题、一个 TL;DR callout（3-5 句核心结论）和 `\tableofcontents`，然后 `\newpage` 进入正文。首页不堆指标表、不放图
3. **必有目录与书签**：`\tableofcontents` + hyperref `bookmarksnumbered`，让读者在 PDF 阅读器侧栏快速跳章节
4. **禁止任何交互元素**：不要滑块、不要 token 网格联动、不要 JS —— 这些在 PDF 中无意义
5. **图片就近排版**：关键图用 `\begin{figure}[!ht]` 紧跟解释它的段落，`width=\linewidth` 或 `0.9\linewidth`，必须有 `\caption` 注明来源
6. **实验/消融不放表格**：实验与消融结果只用文字简要概括趋势与结论，**不展示具体数值、不放结果表**（方法部分的公式与数值例子仍需详尽）
7. **公式编号**：重要公式用 `equation` 带编号，便于正文回指（如"由式 (3)"）

### 2.4 公式书写规范（硬性纪律）

| 公式类型 | 语法 | 说明 |
|---------|------|------|
| **行内公式** | `$...$` | 如 `$I_t = \|S_t-S_{t-1}\|_F / (\|S_{t-1}\|_F+\epsilon)$` |
| **独立公式** | `\begin{equation}...\end{equation}` | 带编号，可被正文回指 |
| **多行对齐** | `\begin{aligned}...\end{aligned}` | 用 `&` 对齐、`\\` 换行 |
| **分段函数** | `\begin{cases}...\end{cases}` | 用 `&` 分隔取值与条件 |
| **矩阵** | `\begin{bmatrix}...\end{bmatrix}` | 用 `&` 分列、`\\` 分行 |
| **范数/期望等** | `\|\cdot\|_F`、`\mathbb{E}`、`\mathcal{N}`、`\bm{}` | 标准 LaTeX 宏 |

**绝对禁止**：
- ❌ 用纯文本或符号拼凑公式（如 `||S_t - S_t-1||`）
- ❌ 矢量/数学符号用图片截图代替（公式必须用 LaTeX 排，只有原论文的"图"才截图）

### 2.5 配色与组件（统一，勿自创）

用 `tcolorbox` 实现提示框，颜色按内容性质选，与 2.2 定义的色板一一对应：

| 组件 | 用途 | 颜色 |
|------|------|------|
| `\section`/`\subsection` 标题 | 章节 | headgray |
| 提示框 `callout` | 一般信息/背景 | brandblue |
| 提示框 `callout` | 正面结果/改进 | okgreen |
| 提示框 `callout` | 注意事项/关键设计 | warnorange |
| 提示框 `callout` | 问题/挑战/缺陷 | badred |
| 提示框 `callout` | 算法机制/核心创新 / AI 分析 | deeppurple |

（实验/消融不放结果表；如确需表格仅限方法部分的小型说明表，用 `booktabs` 三线表、headgray 表头）

提示框用模板提供的可复用环境 `callout`（定义见 `assets/paper_style.tex`，已放在 preamble，无需重复定义）：

使用：`\begin{callout}[okgreen] ... \end{callout}`（缺省色为 brandblue）

不要使用色板之外的颜色，不要自创新环境。

### 2.6 内容组织顺序

1. **第一页：标题 + TL;DR + 目录**：用论文原文标题（不加作者/整理者），一个 TL;DR callout（3-5 句核心结论），`\tableofcontents`，然后 `\newpage`
2. **核心问题/动机**：论文要解决什么、为什么现有方法不够
3. **方法详解**：按 algorithm/architecture/training/data 逐个展开，每个模块包含：公式 + 数值例子 + 关键图片
4. **实验结果**：**只用文字简要概括**结论与趋势（如"在 X 类任务上一致领先、长上下文提升尤为显著"），不放数值、不放表格
5. **消融研究**：同样**只做文字概括**（如"两个模块各有独立贡献""对超参数稳健"），不放数值、不放表格
6. **关键发现/启发**：用 callout 逐条给出，并附 AI 分析
7. **参考/引用信息**：原论文出处

### 2.7 关键图片截图（强制）

论文的核心图（架构图、流程图、主结果曲线、效率对比图等）比文字更直观，**必须**从原 PDF 截图嵌入。

**哪些图必须截**：架构/方法总览图、不同方法对比示意图、主结果曲线/柱状图、效率对比图、消融曲线。

**截图方法**（用 pymupdf，本机已装）：
```python
import fitz
doc = fitz.open("原论文.pdf")
mat = fitz.Matrix(3.0, 3.0)   # ~216 dpi，清晰
# 先用 page.search_for("Figure N") 定位图注，裁图注上方/相邻的图区
pix = doc[页号].get_pixmap(matrix=mat, clip=fitz.Rect(x0,y0,x1,y1))
pix.save("assets/figN_xxx.png")
```
裁完务必用 Read 工具查看截图，确认裁全、不含正文、不切边，错了就调 `clip` 重裁。

**嵌入方法**：
```latex
\begin{figure}[!ht]
  \centering
  \includegraphics[width=\linewidth]{assets/fig1_overview.png}
  \caption{DLA 方法总览（源自原论文 Figure 1）}
\end{figure}
```

**纪律**：图是辅助，每张关键图旁仍需文字解读其要点；图注必须注明原论文 Figure 编号；若某图实在无法截取，用 `callout[warnorange]` 注明"对应原论文 Figure X，建议查阅原文"，不得静默省略。

### 2.8 必须实例化解释的概念

任何**抽象的、公式驱动的、非直觉的**概念都不能只给公式，必须配具体数值例子（"喂进去什么、出来什么"）。包括但不限于：

- 损失/目标函数的工作机制：给定输入值，逐步展示计算与结果
- 归一化/打分方法：给一组原始数据，展示均值、范数、归一化结果
- 权重/聚合/合并策略：对比不同策略对同一组数据的处理差异
- 新提出的模块/机制：用具体输入输出对展示"做了什么、怎么做、效果如何"
- 超参数影响：不同取值下同一指标的变化对比（用表格）

**核心原则**：每个新提出的算法/模块/机制，必须配至少一个完整数值例子。例子用 `example` 环境或 `callout` + 行间公式呈现。

### 2.9 对新颖观察/结论的 AI 分析（强制）

论文中每个**新颖观察**、**反直觉发现**、**核心洞见**，都要附 AI 助手的独立分析，不能只复述原文。格式：

```latex
\begin{callout}[deeppurple]
\textbf{原文观察}：[引用论文的具体观察]
\end{callout}
\begin{callout}[brandblue]
\textbf{AI 分析}：[解读，涵盖：
  1. 为何重要/新颖；
  2. 与其他论文的关联或矛盾；
  3. 对实际实验/训练的指导意义；
  4. 局限性或开放问题]
\end{callout}
```

分析须站在研究者角度，提供批判性视角：与前人工作的联系、实际可操作性、局限/开放问题。

### 2.10 直观类比原则

每种新提出或难以直觉理解的机制，**必须**配一个日常生活类比辅助理解。要求：**贴切**（核心逻辑一致）、**通俗**（用考试/工作/生活场景，不用专业类比）、**简洁**（1-2 句）、**独立**（自包含）。可放在解释该机制后的 `callout` 中。

### 2.11 内容质量要求

- 每个算法/方法必须有具体数值例子（非抽象描述）
- Benchmark 数据完整，不省略对比基线；表格数据带单位（如 %）
- 中英文之间加空格（如"这 3 个算法"）
- 专业术语首次出现保留英文原文
- 抽象机制必须有直观类比和关键图片

### 2.12 适用场景

当用户提供 citekey 且**明确**说"详细解读""图文并茂""写一份详细的论文报告""完整解读""可视化的说明"等时触发详细模式。产物为一份合并的 `<论文标题>.pdf`，并按第四章挂回 Zotero。未明确要求"详细"时，走第三章的约 2 页简短模式。

---

## 三、简短解读模式（约 2 页，默认）

> 用户未明确要求"详细"时走本模式。目标：**用约 2 页**给出快速可读、自包含的核心解析，并尽量嵌入 1 张论文主图。沿用第二章的工具链与样式模板，但内容保持精炼。

### 3.1 硬性约束

1. **篇幅以 2 页为目标**：正常情况下生成约 2 页；内容很少时 1 页可接受，但不再以压进 1 页为目标。使用适度紧凑排版（见 3.4），优先保证主图、正文和 caption 清晰可读。超过 2 页时按"删次要内容 → 收紧间距 → 适度缩图"的顺序压缩，禁止把主图缩到难以辨认。
2. **不要目录、不要 `\tableofcontents`、不要书签分级**：篇幅短无需导航。
3. **不要 `\newpage`**：内容连续排，自然分页即可。
4. **文件命名**：解读 PDF 用 `<论文标题>_brief.pdf`（空格/特殊字符→下划线）；tex 源用 `paper.tex`（最终清理）。
5. **清理与产物**：同零章，所有内容均写入独立 `runDir`；挂载成功后删除整个 `runDir`，包括 `<论文标题>_brief.pdf`，本地不留任何本次任务产物。

### 3.2 内容结构（固定顺序，约 2 页内）

1. **标题**：用论文英文原标题（不加作者/整理者）。
2. **TL;DR callout**（`deeppurple`，3-5 句）：论文解决什么问题、核心方法、关键结论。
3. **核心问题/动机**（1-2 句）：现有方法的不足。
4. **核心方法**（要点式，2-4 条）：用 `itemize` 列出方法关键设计；如有**一个最核心的公式**，用 `equation` 排出，并配一句话解读。
5. **论文主图**（优先 1 张）：放置 method/framework overview；若没有合适的 overview，再选核心机制图或最能支撑主结论的结果图。图片旁必须有 1-2 句解读，caption 标注原论文 Figure 编号。
6. **关键结论**（1-2 句文字概括）：实验趋势与主要收益，**不放数值、不放表格**。
7. **AI 点评 callout**（`brandblue`，1-2 句）：一句话批判性视角（创新点 / 局限 / 启发）。

### 3.3 排版与组件纪律

- **语言/术语**：同详细模式——正文中文，所有术语保留英文原文。
- **公式**：必须用 LaTeX 排（行内 `$...$` 或单条 `equation`），**绝不用文本拼凑、绝不用截图代替公式**。最多放 1-2 个最核心的公式。
- **配色与环境**：复用 `assets/paper_style.tex` 的色板与 `callout`/`example` 环境，不自创颜色或环境。
- **图片（优先一张，至多一张）**：默认必须尝试从原论文嵌入 1 张主图，选择顺序为 method/framework overview → 核心机制图 → 主结果图。使用 `\begin{figure}[H]` 就地放置，通常取 `width=0.75\linewidth` 到 `\linewidth`，以图中文字清晰可辨为准；caption 必须注明来源 Figure 编号，旁边补 1-2 句解读。截图方法与裁图检查见 2.7。只有原文没有适合的图、无法可靠裁取，或图片本身无法在两页内保持可读时才允许省略；不得仅因想压进 1 页而省略。
- **省略**：不做逐章节展开、不做数值例子（与详细模式不同，简短模式不要求每个机制配数值例子）、不放消融细节。

### 3.4 文档骨架（简短模式参考）

```latex
\documentclass[10pt,a4paper]{ctexart}
\input{assets/paper_style.tex}
\usepackage{float}                      % 提供 [H] 让图就地不浮动
\geometry{margin=1.5cm}                 % 收紧页边距（覆盖模板默认 2.3cm）
\setlength{\parskip}{2pt}               % 压缩段间距
\linespread{1.05}                       % 收紧行距
\setlist{nosep,leftmargin=1.4em}        % itemize/enumerate 去掉条目间多余间距

\title{\textbf{论文原文标题}}
\author{}\date{}

\begin{document}
\maketitle
\vspace{-2.5em}                         % 收紧标题与正文间距
\begin{callout}[deeppurple] TL;DR（3-5 句核心结论） \end{callout}
% 核心问题 / 核心方法（itemize + 至多 1-2 个核心公式）
% 优先嵌入一张论文主图：\begin{figure}[H] ... \end{figure}
% 关键结论 / AI 点评
\end{document}
```

> 注：上述 `\geometry`/`\setlength`/`\linespread`/`\setlist` 是简短模式的紧凑参数，统一放在 preamble。`geometry` 用 `\geometry{...}`（模板已加载该宏包）调整，不要再 `\usepackage[...]{geometry}` 以免选项冲突。默认以约 2 页为目标，优先保证主图、正文和 caption 的可读性，不要为了压进 1 页而牺牲内容或缩小图片。

---

## 四、Zotero 解析与挂载（必做）

本章是固定流程的**首尾两步**：开头用 citekey 解析原 PDF（4.1），结尾把解读 PDF 挂回 Zotero（4.3）。两步都依赖 Zotero 在运行。

### 4.1 用 citekey 解析原 PDF 与 attachmentKey

调 Better BibTeX 的 JSON-RPC `item.attachments(citekey)`：

```bash
curl -s -X POST http://127.0.0.1:23119/better-bibtex/json-rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"item.attachments","params":["suAttentionSinkTransformers2026"],"id":1}'
```

返回示例：

```json
{"result":[{
  "open":"zotero://open-pdf/library/items/NZ5LELWY",
  "path":"/Users/zeon/Zotero/storage/NZ5LELWY/Su 等 - 2026 - Attention Sink ....pdf"
}]}
```

- **`path`**：原论文 PDF 的绝对路径，供后续截图与解读使用。
- **`attachmentKey`**：取 `open` URL 末段（`items/` 后那一段，如 `NZ5LELWY`）。挂载时传给 bridge，用于反查父条目。
- **多个附件**：若 `result` 有多条（如论文带多个 PDF），优先取 `contentType` 为 PDF、或文件名与论文标题最匹配的一条；无法判定时向用户确认。
- **citekey not found / 无 PDF 附件**：明确报错并停止，提示用户核对 citekey；不要退化去用标题搜索。

### 4.2 生成解读 PDF

用 4.1 拿到的 `path` 作为只读的原论文 PDF，按第二章（详细）或第三章（简短）规范截图，并将解读 PDF 及所有过程文件生成到本次任务的独立 `runDir`。

### 4.3 挂回 Zotero

挂载依赖常驻的极简 Zotero 插件 **Paper Summary Bridge**（源码与 xpi 在项目根目录 `zotero-paper-bridge/`、`paper-bridge.xpi`），它注册了本地 endpoint `http://127.0.0.1:23119/paper-bridge/attach`，内部调用官方 `Zotero.Attachments.importFromFile` 完成挂载，零损库风险。

调用（`attachmentKey` 用 4.1 解析出的值，`reportPath` 必须是绝对路径）：

```bash
curl -s -X POST http://127.0.0.1:23119/paper-bridge/attach \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json; print(json.dumps({
      "attachmentKey": "NZ5LELWY",
      "reportPath": "/Users/zeon/Documents/Paper/<论文标题>.pdf",
      "title": "AI 解读报告 - <论文标题>"
  }))')"
```

成功返回 `{"ok":true,"newAttachmentKey":"...","parentKey":"..."}`，解读 PDF 即作为附件出现在该论文条目下，并被 Zotero 拷入 storage、纳入同步与全文索引。Bridge 必须等待 `Zotero.Attachments.importFromFile(...)` 和附件标题保存完成后才返回该响应；不得把请求已发送或 HTTP 200 单独视为挂载成功。

### 4.4 挂载确认与本地强制清理

只有同时满足以下条件，才判定挂载成功：

1. HTTP 响应状态为 200；
2. 响应体可解析为 JSON；
3. JSON 中 `ok` 严格等于 `true`；
4. `newAttachmentKey` 存在且为非空字符串。

全部满足后，先按 0.2 校验 `runDir` 的绝对路径、目录名与 `.paper-summary-run` 标记，再删除整个 `runDir`。删除后确认该路径已不存在；如果仍存在，必须报告清理失败，不得声称“本地文件已全部删除”。最终回复只说明“解读 PDF 已挂载到 Zotero，本地临时产物已全部删除”，不要提供已经失效的本地 PDF 路径。

### 4.5 失败兜底

- **连接失败 / 404**：说明 Bridge 插件未安装/未启用，或 Zotero 未运行。提示用户：先确认 Zotero 在运行，再在「工具 → 插件 → 齿轮 → Install Add-on From File」安装 `paper-bridge.xpi`。
- **退化方案**：插件不可用时，给出等效的 Run JavaScript 片段（`Zotero.Attachments.importFromFile({file, parentItemID, contentType:"application/pdf"})`，parentItemID 由 attachmentKey 反查），让用户在「工具 → 开发者 → Run JavaScript」手动执行。用户明确确认手动挂载成功前，必须保留 `runDir`。
- 不得静默失败：挂载未成功时必须明确告知用户解读 PDF 的本地绝对路径，以便手动拖入；不得删除 `runDir`。
