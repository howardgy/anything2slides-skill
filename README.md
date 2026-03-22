# PPT2slides-skill

`PPT2slides-skill` 是一个符合标准目录结构的通用 skill，用来把 PowerPoint `.pptx` 演示文稿转换为可编辑、可本地打开、适合演讲的 Reveal.js HTML 幻灯片。

它的工作方式不是简单截图导出，而是先解析 PPTX 里的文本、备注、图片和版式几何信息，再生成一个结构尽量忠实于原稿的网页演示文档。

## 这是什么

这个项目包含一套可分发的 skill 和两个核心脚本：

- `extract_pptx_bundle.py`：从 `.pptx` 中提取结构化内容、备注和媒体资源
- `bootstrap_reveal_from_bundle.py`：根据提取结果生成 Reveal.js HTML 演示文稿

输出结果适合以下场景：

- 把现有 PPT 转成浏览器可演示版本
- 制作可托管到网页上的内部演示 demo
- 将 PowerPoint 内容转成便于 AI 或人工继续编辑的 HTML deck
- 在保留原始页序和主要布局的前提下，做一版 show-ready 的 Web Slides

## 核心特性

- 保留原始页序，默认不擅自重排幻灯片
- 尽量保留原始布局，使用 PPT 的几何坐标重建文本和图片位置
- 提取 speaker notes，并生成可继续润色的备注文档
- 自动拷贝嵌入媒体资源，生成相对路径可离线打开的 HTML
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

把 `ppt2slides-skill/` 这个目录复制到你的 skill 搜索目录即可。

例如在 Codex 类环境里，常见目录是 `~/.codex/skills`：

```bash
mkdir -p ~/.codex/skills
cp -R /path/to/PPT2slides-skill/ppt2slides-skill ~/.codex/skills/
```

安装完成后，目录通常会变成：

```text
~/.codex/skills/ppt2slides-skill/
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
cp -R PPT2slides-skill/ppt2slides-skill ~/.codex/skills/
```

## 依赖要求

- `python3`
- 输入文件为 `.pptx`

如果原始文件是 `.ppt`，先转成 `.pptx`，例如：

```bash
libreoffice --headless --convert-to pptx --outdir "./converted" "./input.ppt"
```

## 怎么使用

### 作为 skill 调用

你可以直接让代理调用这个 skill，例如：

```text
用 $ppt2slides-skill 把这个 PPTX 转成一个可演讲的 Reveal.js HTML 演示文稿
```

适合的请求方式包括：

- 把这个 PPT 转成 HTML slides
- 保持原始结构，做一个网页版演示
- 把这个 deck 转成 Reveal.js
- 输出一个本地可打开、可编辑的 HTML presentation

### 手动运行脚本

1. 提取 PPTX bundle

```bash
python3 /path/to/ppt2slides-skill/scripts/extract_pptx_bundle.py \
  /path/to/input.pptx \
  /path/to/work/extracted
```

这一步会生成：

- `manifest.json`
- `slides_outline.md`
- `media/`

2. 生成 Reveal.js HTML deck

```bash
python3 /path/to/ppt2slides-skill/scripts/bootstrap_reveal_from_bundle.py \
  /path/to/work/extracted \
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

1. 从 `.pptx` 提取文字、备注、图片和几何布局信息
2. 生成结构化 `manifest.json`
3. 根据布局和媒体信息生成 HTML 幻灯片
4. 保留原始 slide count 和大体排版
5. 输出可继续手工编辑的 Reveal.js deck 和 speaker notes

## 项目结构

```text
PPT2slides-skill/
├── ppt2slides-skill/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   └── scripts/
```

其中：

- `ppt2slides-skill/SKILL.md`：skill 主说明和使用规则
- `ppt2slides-skill/agents/openai.yaml`：代理展示配置
- `ppt2slides-skill/assets/`：HTML 模板、CSS、speaker notes 模板
- `ppt2slides-skill/references/output_contract.md`：提取结果字段说明
- `ppt2slides-skill/scripts/`：两个核心脚本

## 命令示例

你可以用下面的方式手动验证流程：

```bash
python3 ppt2slides-skill/scripts/extract_pptx_bundle.py /path/to/input.pptx /tmp/ppt2slides_skill_extracted
python3 ppt2slides-skill/scripts/bootstrap_reveal_from_bundle.py /tmp/ppt2slides_skill_extracted /tmp/ppt2slides_skill_show_ready
```

## 限制说明

当前版本优先保证“稳健提取 + 可编辑重建”，不是 PowerPoint 的像素级完全复刻。以下内容可能需要人工复核：

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
- `ppt2slides-skill/`

然后执行：

```bash
git init
git add .
git commit -m "Initial commit: add PPT2slides-skill"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

如果你想让我继续帮你把远端也连好并直接 push，我可以接着做这一步。
