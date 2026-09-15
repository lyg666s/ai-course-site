# AI大全栈 · 课程手册（iOS 风格课件站）

纯静态课程阅读站，由 [`build_site.py`](build_site.py) 从本地课件（Markdown / Jupyter Notebook）自动生成，通过 GitHub Pages 托管。

收录七大课程：

1. Python语言核心精讲
2. 数据库
3. Python框架
4. 数据科学工具包
5. Agents底层逻辑
6. LangGraph工作流开发
7. LangChain + DeepAgent 开发实战

**功能**：三级折叠目录 · 全文搜索 · 可编辑并运行的 Python 代码块（内置 Pyodide，离线可用）· 学习进度记录 · 每页目录 · 深色模式 · 移动端适配。

## 在线访问

启用 GitHub Pages 后访问：**https://lyg666s.github.io/ai-course-site/**

## 仓库结构

```
build_site.py    站点生成器（Markdown/Notebook → 静态 HTML，含搜索索引、代码高亮主题）
serve_site.py    本地预览用的极简静态服务器
site/            生成的静态站点（Pages 部署的就是这个目录，勿手改）
vendor/pyodide/  Pyodide 运行时（构建时复制进 site/assets/pyodide）
```

## 本地重建

```bash
/usr/bin/python3 build_site.py
```

> 需要本机装有 `markdown`、`pygments`（macOS 系统自带 Python 已满足），且上级目录中存在各课程的课件文件夹。生成后提交 `site/` 并推送，Pages 会自动更新。
