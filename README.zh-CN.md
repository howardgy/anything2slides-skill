# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` 是一个符合标准目录结构的通用 skill，用来把多种源材料转换为可编辑、可本地打开、适合演讲的 Reveal.js HTML 幻灯片。

本项目在非 PPT 文档转幻灯片的工作流设计上参考并扩展了 [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill) 的思路，尤其是 `paper2slides` 风格的“先提取，再理解，再组织讲述结构”的流程。

它有两种工作模式：

- 对于 `ppt` / `pptx`：严格按照原版 PPT 的页序和主要版式进行网页化重建
- 对于 `pdf` / `text` / `html` / `md` / `docx`：参考 `paper2slides` 的流程，先提取文字与图片，再决定演示结构，最后制作 HTML 演示

## 这是什么

这个项目包含一套可分发的 skill、一个统一入口，以及两条实际可运行的转换管线：

- `anything2slides.py`：统一入口，按源文件类型自动路由
- `extract_pptx_bundle.py`：从 `.pptx` 中提取结构化内容、备注和媒体资源
- `bootstrap_reveal_from_bundle.py`：根据提取结果生成 Reveal.js HTML 演示文稿
- `extract_document_bundle.py`：从 `pdf` / `docx` / `md` / `html` / `txt` 中提取结构化文本与图片
- `bootstrap_reveal_from_document_bundle.py`：根据文档 bundle 生成面向演讲的 Reveal.js deck

输出结果适合以下场景：

- 把现有 PPT 转成浏览器可演示版本
- 把 PDF、Markdown、Word 或网页内容整理成 show-ready 幻灯片
- 制作可托管到网页上的内部演示 demo
- 将文档内容转成便于 AI 或人工继续编辑的 HTML deck
- 在保留原始 PPT 页序和主要布局的前提下，做一版 show-ready 的 Web Slides

## 核心特性

- 对 `ppt` / `pptx` 保留原始页序，默认不擅自重排幻灯片
- 对 `ppt` / `pptx` 尽量保留原始布局，使用 PPT 的几何坐标重建文本和图片位置
- 提取 speaker notes，并生成可继续润色的备注文档
- 自动拷贝嵌入媒体资源，生成相对路径可离线打开的 HTML
- 对非 PPT 材料采用 `paper2slides` 风格的“先理解、再策划、再出片”流程
- 默认输出 Reveal.js 风格的 show-ready 页面
- 生成结果仍可手工编辑，适合后续继续美化或重构
- 提供图片缩放、lightbox、设置面板等演示增强能力

## 标准兼容性

这个项目采用标准的 skill 目录结构：

- `SKILL.md`
- `agents/`
- `assets/`
- `references/`
- `scripts/`

因此它不只适用于 Codex，也适合安装到支持这类 skill 目录约定的环境中，例如：

- OpenClaw
- 各类 Claw / claw-compatible 环境
- Codex Desktop
- Codex CLI
- Claude Code
- 其他支持本地 skill 目录挂载的兼容工具

换句话说，它不是某个单一产品专属格式，而是一个可以在多种 agent / coding assistant 环境中复用的标准 skill 包。

目前仓库没有直接提供以下形态的独立插件封装：

- PowerPoint 插件
- 浏览器扩展
- Cursor / VS Code marketplace 插件
- ChatGPT 自定义 GPT 插件包

## 安装方式

### 方式 1：安装到兼容 skill 目录的环境

把 `anything2slides-skill/` 这个目录复制到你的 skill 搜索目录即可。

例如在 Codex 类环境里，常见目录是 `~/.codex/skills`：

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/anything2slides-skill/anything2slides-skill ~/.codex/skills/
```

安装完成后，目录通常会变成：

```text
~/.codex/skills/anything2slides-skill/
├── SKILL.md
├── agents/
├── assets/
├── references/
└── scripts/
```

如果你的宿主环境需要重启或重新加载 skills，请重新打开对应工具。

### 方式 2：作为 GitHub 项目拉取后安装

```bash
git clone <your-github-repo-url>
mkdir -p ~/.codex/skills
cp -R anything2slides-skill/anything2slides-skill ~/.codex/skills/
```

## 依赖要求

- `python3` 用于 PPT/PPTX 自动提取流程
- 输入可以是：
  `ppt`、`pptx`、`pdf`、`txt`、`text`、`html`、`md`、`docx`

如果原始文件是 `.ppt`，先转成 `.pptx`，例如：

```bash
libreoffice --headless --convert-to pptx --outdir "./converted" "./input.ppt"
```

## 怎么使用

### 作为 skill 调用

你可以直接让代理调用这个 skill，例如：

```text
用 $anything2slides-skill 把这个源材料转成一个可演讲的 Reveal.js HTML 演示文稿
```

适合的请求方式包括：

- 把这个 PPT 转成 HTML slides，并保持原始结构
- 把这个 PDF 做成一个适合汇报的网页演示
- 基于这个 Markdown 文档做一版 show-ready 的 slides
- 把这个 HTML 页面内容整理成一套演讲稿式的演示
- 输出一个本地可打开、可编辑的 HTML presentation

### 手动运行脚本

推荐优先使用统一入口：

```bash
python3 /path/to/anything2slides-skill/scripts/anything2slides.py \
  /path/to/input \
  /path/to/work/show_ready
```

这个入口会自动判断：

- `ppt` / `pptx`：走保真重建流程
- `pdf` / `txt` / `html` / `md` / `docx`：走文档提炼 + 叙事生成流程

如果你想分步运行，可以按下面的方式分别执行。

### 分支 A：PPT / PPTX

1. 提取 PPTX bundle

```bash
python3 /path/to/anything2slides-skill/scripts/extract_pptx_bundle.py \
  /path/to/input.pptx \
  /path/to/work/extracted
```

这一步会生成：

- `manifest.json`
- `slides_outline.md`
- `media/`

2. 生成 Reveal.js HTML deck

```bash
python3 /path/to/anything2slides-skill/scripts/bootstrap_reveal_from_bundle.py \
  /path/to/work/extracted \
  /path/to/work/show_ready
```

这一步会生成：

- `show_ready/index.html`
- `show_ready/speaker_notes.md`
- `show_ready/assets/css/style.css`
- `show_ready/assets/media/`

### 分支 B：PDF / Text / HTML / Markdown / DOCX

1. 提取文档 bundle

```bash
python3 /path/to/anything2slides-skill/scripts/extract_document_bundle.py \
  /path/to/input.pdf \
  /path/to/work/document_bundle
```

这一步会生成：

- `manifest.json`
- `source_outline.md`
- `media/`

2. 生成 Reveal.js HTML deck

```bash
python3 /path/to/anything2slides-skill/scripts/bootstrap_reveal_from_document_bundle.py \
  /path/to/work/document_bundle \
  /path/to/work/show_ready
```

这一步会生成：

- `show_ready/index.html`
- `show_ready/speaker_notes.md`
- `show_ready/assets/css/style.css`
- `show_ready/assets/media/`

## 输出目录说明

### 提取阶段输出

```text
extracted/
├── manifest.json
├── slides_outline.md
└── media/
```

文档型源的提取目录类似：

```text
document_bundle/
├── manifest.json
├── source_outline.md
└── media/
```

### 生成阶段输出

```text
show_ready/
├── index.html
├── speaker_notes.md
└── assets/
    ├── css/
    └── media/
```

## 工作流程

### 分支 A：PPT / PPTX

1. 从 `.pptx` 提取文字、备注、图片和几何布局信息
2. 生成结构化 `manifest.json`
3. 根据布局和媒体信息生成 HTML 幻灯片
4. 保留原始 slide count 和大体排版
5. 输出可继续手工编辑的 Reveal.js deck 和 speaker notes

### 分支 B：PDF / Text / HTML / Markdown / DOCX

1. 先提取标题、章节、段落和可用图片
2. 判断应该做成什么类型的演示
3. 自动规划合适的叙事结构、页数和重点
4. 生成 HTML slides 和 speaker notes
5. 这一分支参考 `paper2slides` 的 agent-driven 流程，而不是保真复刻原文档页面

## 项目结构

```text
anything2slides-skill/
├── anything2slides-skill/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   └── scripts/
```

其中：

- `anything2slides-skill/SKILL.md`：skill 主说明和使用规则
- `anything2slides-skill/agents/openai.yaml`：代理展示配置
- `anything2slides-skill/assets/`：HTML 模板、CSS、speaker notes 模板
- `anything2slides-skill/references/output_contract.md`：提取结果字段说明
- `anything2slides-skill/scripts/`：统一入口 + PPT/PPTX + 文档型源核心脚本

## 命令示例

你可以用下面的方式手动验证流程：

```bash
python3 anything2slides-skill/scripts/extract_pptx_bundle.py /path/to/input.pptx /tmp/anything2slides_extracted
python3 anything2slides-skill/scripts/bootstrap_reveal_from_bundle.py /tmp/anything2slides_extracted /tmp/anything2slides_show_ready
```

## 限制说明

对于 PPT 模式，当前版本优先保证“稳健提取 + 可编辑重建”，不是 PowerPoint 的像素级完全复刻。以下内容可能需要人工复核：

- SmartArt 语义
- 图表数据重建
- 动画和切换效果
- 复杂分组对象
- 主题字体继承
- 视频播放相关元数据

如果原始 PPT 对这些效果依赖很重，建议把生成的 HTML 作为初稿，再做人工微调。

## 上传到 GitHub 的推荐做法

如果你准备把这个项目发到自己的 GitHub，建议仓库根目录保留：

- `README.md`
- `README.zh-CN.md`
- `README.en.md`
- `anything2slides-skill/`

然后执行：

```bash
git init
git add .
git commit -m "Initial commit: add anything2slides-skill"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
