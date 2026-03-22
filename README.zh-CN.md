# anything2slides-skill

[中文](README.zh-CN.md) | [English](README.en.md)

`anything2slides-skill` 是一个符合标准目录结构的通用 skill，用来把多种源材料转换为可编辑、可本地打开、适合演讲的 Reveal.js HTML 幻灯片。

本项目在非 PPT 文档转幻灯片的工作流设计上参考并扩展了 [inhyeoklee/paper2slides-skill](https://github.com/inhyeoklee/paper2slides-skill) 的思路，尤其是 `paper2slides` 风格的“先提取，再理解，再组织讲述结构”的流程。

它有两种工作模式：

- 对于 `ppt` / `pptx`：严格按照原版 PPT 的页序和主要版式进行网页化重建
- 对于 `pdf` / `text` / `html` / `md` / `docx`：参考 `paper2slides` 的流程，先提取文字与图片，再决定演示结构，最后制作 HTML 演示

## 输出结果适合以下场景：

- 把现有 PPT 转成浏览器可演示版本
- 把 PDF、Markdown、Word 或网页内容整理成 show-ready 幻灯片
- 制作可托管到网页上的内部演示 demo
- 将文档内容转成便于 AI 或人工继续编辑的 HTML deck
- 在保留原始 PPT 页序和主要布局的前提下，做一版 show-ready 的 Web Slides


## 安装方式

### 方式 1：输入以下命令
```
帮我安装skill https://github.com/howardgy/anything2slides-skill/
```

### 方式 2：作为 GitHub 项目拉取后安装

```bash
cd <你的项目文件夹>
git clone https://github.com/howardgy/anything2slides-skill/
cp -R anything2slides-skill/anything2slides-skill ~/<你的工具，例如~/.codex>/skills/
```



## 怎么使用

### Python 环境安装
先进入 skill 目录，通过 `requirements.txt` 安装运行时依赖：

```bash
cd anything2slides-skill
python3 -m pip install -r requirements.txt
```

依赖要求：
- Python 3.9 及以上


### 作为 skill 调用

你可以直接让代理调用这个 skill，例如：

```text
把这个ppt文件转成一个slide
```

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

也就是说，你生成出来的 HTML 通常会在你指定输出目录下的 `show_ready/index.html`。
