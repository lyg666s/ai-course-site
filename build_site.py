# -*- coding: utf-8 -*-
"""《Python语言核心精讲》课件静态站点生成器（iOS 风格）。

读取根目录课程元数据与各章节 课件.md，生成纯静态站点到 site/：
  - index.html          课程首页（模块分组列表 + 终端示例）
  - ch/chNN.html        各章课件页
  - proj/*.html         项目案例页
  - assets/             样式、脚本、代码高亮 CSS、搜索索引

用法：python3 build_site.py
"""

from __future__ import annotations

import json
import html as html_lib
import re
import shutil
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

ROOT: Path = Path(__file__).resolve().parent
OUT: Path = ROOT / "site"

META: dict = json.loads((ROOT / "课程内容.json").read_text(encoding="utf-8"))
COURSE_TITLE: str = META["title"]
COURSE_AUTHOR: str = META["author"]
COURSE_DESC: str = META["description"]

# 章节按内容划分为五个模块（badge 为 iOS 风格渐变圆角徽标用字）
MODULES: list[tuple[str, list[int], str, str]] = [
    ("语言基础", [1, 2, 3, 4, 5, 6, 7], "语", "b1"),
    ("面向对象", [8, 9, 10, 11, 12, 13, 14, 15], "面", "b2"),
    ("语言进阶", [16, 17, 18, 19, 20, 21, 22, 23], "进", "b3"),
    ("异步与并发", [24, 25, 26, 27, 28], "异", "b4"),
    ("工程化实践", [29, 30, 31, 32], "工", "b5"),
]

PROJECTS: list[dict] = [
    {
        "key": "async-agents",
        "title": "多智能体协同调研系统",
        "sub": "异步编程综合项目解析",
        "path": ROOT / "27. 异步编程" / "answer" / "README.md",
    },
    {
        "key": "duyi-utils",
        "title": "duyi-utils 构建发布示例",
        "sub": "构建发布示例工程说明",
        "path": ROOT / "29. 构建发布" / "duyi-utils" / "README.md",
    },
]

# 同级课程目录（上级文件夹里的其他课程），每门课作为站点的一个顶级模块。
# 顺序即站点中的大类顺序。layout:
#   standard — "NN. 名称/课件.md|课件.ipynb" 章节文件夹布局
#   flat     — "课件/NN. 名称.md|ipynb" 平铺文件布局
# 第三方库依赖较多（numpy/pandas/fastapi 等），其 Python 代码块不启用浏览器运行。
SIBLINGS: list[dict] = [
    {"key": "db", "dir": "database-main", "glyph": "库", "cls": "b-db", "layout": "standard"},
    {"key": "fw", "dir": "python-framework-main", "glyph": "架", "cls": "b-fw", "layout": "standard"},
    {"key": "dst", "dir": "data-science-tools-main", "glyph": "数", "cls": "b-ds", "layout": "standard"},
    {"key": "ac", "dir": "agent-core-main", "glyph": "智", "cls": "b2", "layout": "standard"},
    {"key": "lg", "dir": "langgraph-python-main", "glyph": "图", "cls": "b3", "layout": "flat"},
    {"key": "da", "dir": "langchain-deepagent-main", "glyph": "链", "cls": "b4", "layout": "flat"},
]
COURSEWARE_NAMES: tuple[str, ...] = ("课件.md", "课件.ipynb", "课件md")

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='0' y2='1'%3E"
    "%3Cstop offset='0' stop-color='%233EA0FF'/%3E%3Cstop offset='1' stop-color='%230A6BFF'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='64' height='64' rx='14.5' fill='url(%23g)'/%3E"
    "%3Ctext x='32' y='42' font-family='-apple-system,Helvetica,sans-serif' font-size='25' "
    "font-weight='700' fill='%23fff' text-anchor='middle'%3EPy%3C/text%3E%3C/svg%3E"
)


# --------------------------------------------------------------------------
# Markdown 转换
# --------------------------------------------------------------------------

def slugify_cn(value: str, separator: str) -> str:
    """目录锚点 slug：保留中文。"""
    value = re.sub(r"[^\w一-鿿 -]+", "", value).strip()
    value = re.sub(r"\s+", separator, value)
    return value or "section"


def preprocess(text: str) -> str:
    """转换前的预处理：==重点== → <mark>，并转义伪 HTML 标签。"""
    fence_re = re.compile(r"(```.*?```|~~~.*?~~~)", re.S)
    parts: list[str] = []
    for i, part in enumerate(fence_re.split(text)):
        if i % 2 == 1:  # 代码围栏原样保留
            parts.append(part)
            continue
        # 保护行内代码
        inline_code: list[str] = []

        def stash(m: re.Match) -> str:
            inline_code.append(m.group(0))
            return f"\x00{len(inline_code) - 1}\x00"

        part = re.sub(r"`[^`\n]+`", stash, part)
        # 非标签开头的 <  转义，避免 <包名> 之类被浏览器吞掉
        part = re.sub(r"<(?![a-zA-Z/!])", "&lt;", part)
        # ==高亮== → <mark>
        part = re.sub(r"==([^=\n]+?)==", r"<mark>\1</mark>", part)
        part = re.sub(r"\x00(\d+)\x00", lambda m: inline_code[int(m.group(1))], part)
        parts.append(part)
    return "".join(parts)


def strip_leading_h1(text: str) -> str:
    """去掉文档开头的一级标题（页面模板已单独渲染章节名）。"""
    return re.sub(r"^\s*#\s+[^\n]+\n+", "", text, count=1)


FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)^```", re.S | re.M)


def add_lang_classes(html: str, src: str, runnable: bool = True) -> str:
    """按源文件中围栏的出现顺序，给 codehilite div 补上 lang-xxx 类。

    codehilite 本身不输出语言信息，这里依赖两者在文档中顺序一致。
    数量对不上（如存在缩进代码块）则放弃标记，仅影响可运行按钮，不影响渲染。
    runnable=False 时追加 lang-norun（第三方库依赖的代码，不启用浏览器运行）。
    """
    langs = [lang.lower() for lang, _body in FENCE_RE.findall(src)]
    pieces: list[str] = []
    idx = 0
    for part in re.split(r'(<div class="codehilite">)', html):
        if part == '<div class="codehilite">':
            if idx >= len(langs):
                return html
            lang = langs[idx]
            idx += 1
            if lang:
                cls = "lang-python" if lang == "python" else f"lang-{lang}"
                if lang == "python" and not runnable:
                    cls += " lang-norun"
                pieces.append(f'<div class="codehilite {cls}">')
            else:
                pieces.append(part)
        else:
            pieces.append(part)
    if idx != len(langs):
        return html
    return "".join(pieces)


MD_EXTENSIONS: list = [
    "tables",
    "fenced_code",
    "codehilite",
    "sane_lists",
]


def new_markdown() -> markdown.Markdown:
    toc = TocExtension(slugify=slugify_cn, toc_depth="2-3")
    return markdown.Markdown(
        extensions=MD_EXTENSIONS + [toc],
        extension_configs={"codehilite": {"guess_lang": False, "noclasses": False}},
    )


def convert_md(text: str, runnable: bool = True) -> tuple[str, list[dict]]:
    """Markdown → (HTML, toc_tokens)。"""
    md = new_markdown()
    html = md.convert(preprocess(text))
    html = add_lang_classes(html, text, runnable)
    html = html.replace("<img ", '<img loading="lazy" ')
    return html, md.toc_tokens


def flatten_toc(tokens: list[dict]) -> list[dict]:
    """把嵌套 toc 展平成 (level, id, name) 列表。"""
    out: list[dict] = []
    for t in tokens:
        out.append({"level": t["level"], "id": t["id"], "name": t["name"]})
        out.extend(flatten_toc(t["children"]))
    return out


def plain_text(md_text: str) -> str:
    """粗略提取纯文本，用于搜索索引。"""
    text = re.sub(r"```.*?```", " ", md_text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#+\s*", " ", text, flags=re.M)
    text = re.sub(r"^>\s?", " ", text, flags=re.M)
    text = re.sub(r"^\|.*\|$", " ", text, flags=re.M)
    text = re.sub(r"^[-*]\s+", " ", text, flags=re.M)
    text = text.replace("==", "").replace("**", "").replace("*", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def section_bodies(md_text: str) -> list[dict]:
    """按 ## 切分章节正文，供搜索索引使用。"""
    lines = md_text.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    fence = False
    for line in lines:
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            fence = not fence
        if not fence and re.match(r"^##\s+", line):
            name = re.sub(r"^##\s+", "", line).strip()
            current = {"name": name, "chunks": []}
            sections.append(current)
        elif current is not None:
            current["chunks"].append(line)
    return [
        {"name": s["name"], "body": plain_text("\n".join(s["chunks"]))[:400]}
        for s in sections
    ]


# --------------------------------------------------------------------------
# Jupyter Notebook 渲染
# --------------------------------------------------------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def render_code_cell(cell: dict) -> str:
    """notebook 代码单元格 → 代码块 + 输出（文本/图片/错误）。"""
    code = "".join(cell.get("source", [])).strip("\n")
    if not code:
        return ""
    formatter = HtmlFormatter(cssclass="codehilite lang-nb", nowrap=False)
    body = pyg_highlight(code, PythonLexer(), formatter)
    outs: list[str] = []
    for o in cell.get("outputs", []):
        ot = o.get("output_type")
        data = o.get("data", {})
        if ot == "stream":
            text = html_lib.escape("".join(o.get("text", [])))
            if text.strip():
                outs.append(f'<pre class="nb-stream">{text}</pre>')
        elif ot in ("execute_result", "display_data"):
            if "image/png" in data:
                png = data["image/png"]
                if isinstance(png, list):
                    png = "".join(png)
                outs.append(
                    f'<img class="nb-img" src="data:image/png;base64,{png}" loading="lazy" />'
                )
            elif "text/plain" in data:
                text = html_lib.escape("".join(data["text/plain"]))
                outs.append(f'<pre class="nb-result">{text}</pre>')
        elif ot == "error":
            tb = ANSI_RE.sub("", "\n".join(o.get("traceback", [])))
            outs.append(
                f'<pre class="nb-error">{html_lib.escape(tb)}</pre>'
            )
    out_html = f'<div class="nb-out">{"".join(outs)}</div>' if outs else ""
    return f'<div class="nb-cell">{body}{out_html}</div>'


def rewrite_local_assets(text: str, prefix: str) -> str:
    """把课件里对本地 assets/ 的引用改写到站点目录（prefix 形如 assets/ch24）。"""
    return re.sub(r"\]\((?:\./)?assets/", f"]({prefix}/", text)


def asset_refs_in_text(text: str) -> set[str]:
    """收集课件里引用的本地 assets 文件名。"""
    return set(re.findall(r"\]\((?:\./)?assets/([^)\s]+)", text or ""))


def copy_referenced_files(src_dir: Path, dest_dir: Path, names: set[str]) -> int:
    """只拷贝被引用的资源文件（跳过 .excalidraw 等未引用的源文件）。"""
    copied = 0
    for name in sorted(names):
        f = src_dir / name
        if f.is_file():
            (dest_dir / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest_dir / name)
            copied += 1
    return copied


def convert_ipynb(path: Path, asset_prefix: str | None = None) -> tuple[str, list[dict]]:
    """Jupyter Notebook → (HTML, toc_tokens)。markdown 单元继续走 Markdown 管线。"""
    nb = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    toc_tokens: list[dict] = []
    md_buf: list[str] = []

    def flush_md() -> None:
        if not md_buf:
            return
        text = "\n".join(md_buf).strip()
        md_buf.clear()
        if not text:
            return
        md = new_markdown()
        html = md.convert(preprocess(text))
        html = html.replace("<img ", '<img loading="lazy" ')
        parts.append(html)
        toc_tokens.extend(md.toc_tokens)

    for cell in nb.get("cells", []):
        ct = cell.get("cell_type")
        src = "".join(cell.get("source", []))
        if ct == "markdown":
            if asset_prefix:
                src = rewrite_local_assets(src, asset_prefix)
            md_buf.append(src)
            md_buf.append("")
        elif ct == "code":
            flush_md()
            cell_html = render_code_cell(cell)
            if cell_html:
                parts.append(cell_html)
    flush_md()
    return "\n".join(parts), toc_tokens


# --------------------------------------------------------------------------
# 同级课程加载
# --------------------------------------------------------------------------

def load_sibling_courses() -> list[dict]:
    """扫描同级课程目录，返回章节列表。"""
    chapters: list[dict] = []
    for sib in SIBLINGS:
        root = ROOT.parent / sib["dir"]
        if not root.is_dir():
            continue
        meta = {}
        meta_path = root / "课程内容.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
        title = meta.get("title", sib["key"])
        found: list[dict] = []
        if sib.get("layout") == "flat":
            # 课件/ 目录下的 "NN. 名称.md|.ipynb" 课件文件
            cw_dir = root / "课件"
            if cw_dir.is_dir():
                for f in sorted(cw_dir.iterdir()):
                    m = re.match(r"^(\d+)[.．]\s*(.+?)\.(md|ipynb)$", f.name)
                    if not (f.is_file() and m):
                        continue
                    found.append(
                        {
                            "course": sib["key"],
                            "course_title": title,
                            "n": int(m.group(1)),
                            "title": m.group(2).strip(),
                            "kind": "ipynb" if m.group(3) == "ipynb" else "md",
                            "src": f,
                        }
                    )
        else:
            for d in sorted(root.iterdir()):
                m = re.match(r"^(\d{2})\. (.+)$", d.name)
                if not (d.is_dir() and m):
                    continue
                courseware = next(
                    (d / name for name in COURSEWARE_NAMES if (d / name).is_file()), None
                )
                if courseware is None:
                    continue
                found.append(
                    {
                        "course": sib["key"],
                        "course_title": title,
                        "n": int(m.group(1)),
                        "title": m.group(2),
                        "kind": "ipynb" if courseware.suffix == ".ipynb" else "md",
                        "src": courseware,
                    }
                )
        chapters.extend(found)
    return chapters


# --------------------------------------------------------------------------
# 章节与页面数据
# --------------------------------------------------------------------------

def load_chapters() -> list[dict]:
    chapters: list[dict] = []
    for d in sorted(ROOT.iterdir()):
        m = re.match(r"^(\d{2})\. (.+)$", d.name)
        if not (d.is_dir() and m):
            continue
        courseware = d / "课件.md"
        if not courseware.exists():
            continue
        chapters.append(
            {
                "n": int(m.group(1)),
                "title": m.group(2),
                "url": f"ch/ch{int(m.group(1)):02d}.html",
                "md": courseware.read_text(encoding="utf-8"),
            }
        )
    return chapters


def module_of(n: int) -> str:
    for name, nums, _glyph, _cls in MODULES:
        if n in nums:
            return name
    return "其他"


def toc_nav_from_tokens(tokens: list[dict]) -> str:
    """把 toc_tokens 渲染成带嵌套的列表（保持层级）。"""
    if not tokens:
        return ""

    def walk(ts: list[dict]) -> str:
        out = ['<ol class="toc-list">']
        for t in ts:
            children = walk(t["children"]) if t["children"] else ""
            out.append(
                f'<li class="toc-l{t["level"]}"><a href="#{t["id"]}">{t["name"]}</a>{children}</li>'
            )
        out.append("</ol>")
        return "".join(out)

    return f'<p class="toc-title">本页目录</p>{walk(tokens)}'


# --------------------------------------------------------------------------
# 页面模板
# --------------------------------------------------------------------------

def h2_meta(toc_tokens: list[dict]) -> list[dict]:
    """取二级标题的 (名称, 锚点)，供侧栏章节折叠列表使用。"""
    return [
        {"name": t["name"], "anchor": t["id"]}
        for t in flatten_toc(toc_tokens)
        if t["level"] == 2
    ]


def side_chapter_fold(e: dict, base: str, pinned: bool) -> str:
    """侧栏章节行：链接 + 小小类折叠（展开显示各节）。"""
    fold_id = "fold-" + e["url"].replace("/", "-").replace(".", "-")
    num = f'{e["num"]:02d}' if e["num"] else "◈"
    dch = e.get("data_ch", "")
    dch_attr = f' data-ch="{dch}"' if dch else ""
    link = (
        f'<a class="side-link{" active" if pinned else ""}" href="{base}{e["url"]}"{dch_attr}>'
        f'<span class="side-num">{num}</span>'
        f'<span class="side-name">{e["title"]}</span></a>'
    )
    secs = e.get("sec_meta") or []
    fold_btn = ""
    body = ""
    if secs:
        pin_attr = " data-pinned" if pinned else ""
        fold_btn = (
            f'<button type="button" class="side-fold fold-head" '
            f'aria-expanded="false"{pin_attr}>'
            f'<span class="side-chev" aria-hidden="true">›</span></button>'
        )
        links = "".join(
            f'<a href="{base}{e["url"]}'
            + (f'#{s["anchor"]}' if s["anchor"] else "")
            + f'">{s["name"]}</a>'
            for s in secs
        )
        body = (
            '<div class="fold-body"><div class="fold-inner">'
            f'<div class="side-sec">{links}</div></div></div>'
        )
    cls = "side-ch fold" + (" open" if pinned else "")
    return (
        f'<div class="{cls}" data-fold="{fold_id}">'
        f'<div class="side-ch-row">{link}{fold_btn}</div>{body}</div>'
    )


def side_group_fold(
    fold_id: str, head_html: str, body_html: str, pinned: bool, head_cls: str
) -> str:
    """大类/小类折叠容器。"""
    cls = f"fold {head_cls}" + (" open" if pinned else "")
    pin_attr = " data-pinned" if pinned else ""
    return (
        f'<div class="{cls.strip()}" data-fold="{fold_id}">'
        f'<button type="button" class="fold-head {head_cls}-head" '
        f'aria-expanded="false"{pin_attr}>'
        f'<span class="side-chev" aria-hidden="true">›</span>{head_html}</button>'
        f'<div class="fold-body"><div class="fold-inner">{body_html}</div></div></div>'
    )


def course_subgroups(course_key: str, chs: list[dict]) -> list[tuple[str | None, list[dict]]]:
    """把一门课的章节按顺序切成 (小类名|None, 章节) 段；None 表示直接挂大类。"""
    if course_key == "fw":

        def key(ch: dict) -> str | None:
            return "部署" if ch["title"].startswith("部署") else None

    elif course_key == "dst":  # 标题形如 "Numpy - 核心概念"，取前缀作小类

        def key(ch: dict) -> str | None:
            return ch["title"].split(" - ")[0] if " - " in ch["title"] else None

    else:
        return [(None, chs)]

    out: list[tuple[str | None, list[dict]]] = []
    for ch in chs:
        k = key(ch)
        if k and out and out[-1][0] == k:
            out[-1][1].append(ch)
        elif k:
            out.append((k, [ch]))
        else:
            out.append((None, [ch]))
    return out


def sidebar_html(current_url: str, entries: list[dict], base: str = "") -> str:
    """左侧目录栏。entries: {url, num, title, sub, is_project}；base 为页面到站点根的前缀。"""
    current_e = next((e for e in entries if e["url"] == current_url), None)

    def chapter_fold(e: dict) -> str:
        return side_chapter_fold(e, base, pinned=(current_e is not None and e["url"] == current_url))

    py_chapters = [e for e in entries if not e["is_project"] and e.get("course", "py") == "py"]
    proj_entries = [e for e in entries if e["is_project"]]

    # —— 大类一：Python语言核心精讲（小类 = 模块 + 项目案例） ——
    py_body: list[str] = []
    for idx, (mod_name, nums, _glyph, _cls) in enumerate(MODULES):
        mod_chs = [e for e in py_chapters if e["num"] in nums]
        if not mod_chs:
            continue
        mod_pinned = current_e is not None and current_e.get("course", "py") == "py" and any(
            c["url"] == current_url for c in mod_chs
        )
        py_body.append(
            side_group_fold(
                f"m-py-{idx}",
                mod_name,
                "".join(chapter_fold(e) for e in mod_chs),
                mod_pinned,
                "side-mod",
            )
        )
    if proj_entries:
        proj_pinned = current_e is not None and current_e.get("is_project", False)
        py_body.append(
            side_group_fold(
                "m-py-proj",
                "项目案例",
                "".join(chapter_fold(e) for e in proj_entries),
                proj_pinned,
                "side-mod",
            )
        )
    groups: list[str] = [
        '<div class="side-group">'
        + side_group_fold(
            "c-py",
            '<span class="badge badge-mini b1" aria-hidden="true">Py</span>'
            f'<span class="side-cat-name">{COURSE_TITLE}</span>',
            "".join(py_body),
            current_e is not None and current_e.get("course", "py") == "py",
            "side-cat",
        )
        + "</div>"
    ]
    # —— 大类二至四：同级课程 ——
    for sib in SIBLINGS:
        chs = [e for e in entries if e.get("course") == sib["key"]]
        if not chs:
            continue
        parts: list[str] = []
        for name, group_chs in course_subgroups(sib["key"], chs):
            if name is None:
                parts.extend(chapter_fold(e) for e in group_chs)
            else:
                sub_pinned = current_e is not None and any(
                    c["url"] == current_url for c in group_chs
                )
                parts.append(
                    side_group_fold(
                        f"m-{sib['key']}-{name}",
                        name,
                        "".join(chapter_fold(e) for e in group_chs),
                        sub_pinned,
                        "side-mod",
                    )
                )
        course_pinned = current_e is not None and current_e.get("course") == sib["key"]
        groups.append(
            '<div class="side-group">'
            + side_group_fold(
                f"c-{sib['key']}",
                '<span class="badge badge-mini '
                + sib["cls"]
                + '" aria-hidden="true">'
                + sib["glyph"]
                + '</span><span class="side-cat-name">'
                + sib["title"]
                + "</span>",
                "".join(parts),
                course_pinned,
                "side-cat",
            )
            + "</div>"
        )
    active = " active" if current_url == "index.html" else ""
    return f"""
<aside class="sidebar" id="sidebar">
  <div class="side-head">
    <a class="side-brand" href="{base}index.html">
      <span class="side-brand-name">AI大全栈</span>
      <span class="side-brand-sub">{COURSE_AUTHOR} 主讲，系列课程手册</span>
    </a>
    <div class="search">
      <input id="search-input" type="search" placeholder="搜索课件内容" autocomplete="off" aria-label="搜索课件内容" />
      <div class="search-panel" id="search-panel" hidden></div>
    </div>
  </div>
  <nav class="side-nav" aria-label="课程目录">
    <a class="side-home{active}" href="{base}index.html">课程总览</a>
    {"".join(groups)}
  </nav>
  <div class="side-foot">
    <div class="progress"><i id="progress-bar"></i></div>
    <span id="progress-text">已学 0 / 32</span>
  </div>
</aside>
<div class="backdrop" id="backdrop"></div>
<header class="topbar">
  <button class="burger" id="burger" aria-label="打开目录" aria-controls="sidebar">☰</button>
  <a class="topbar-title" href="{base}index.html">AI大全栈 · 课程手册</a>
</header>
"""


def page_shell(base: str, title: str, body: str, current_url: str, entries: list[dict], desc: str = "") -> str:
    desc_attr = f'<meta name="description" content="{desc}" />' if desc else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="color-scheme" content="light dark" />
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F2F2F7" />
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#000000" />
<title>{title}</title>
{desc_attr}
<script>document.documentElement.classList.add("js")</script>
<link rel="icon" href="{FAVICON}" />
<link rel="stylesheet" href="{base}assets/pygments.css" />
<link rel="stylesheet" href="{base}assets/style.css" />
</head>
<body data-base="{base}">
<a class="skip" href="#content">跳到正文</a>
{sidebar_html(current_url, entries, base)}
{body}
<script src="{base}assets/app.js"></script>
</body>
</html>
"""


def chapter_page(ch: dict, entries: list[dict], prev_e: dict | None, next_e: dict | None) -> str:
    url = ch["url"]
    if "html" in ch:  # 预渲染内容（notebook）
        body_html, toc_tokens = ch["html"], ch["toc"]
    else:
        body_html, toc_tokens = convert_md(
            strip_leading_h1(ch["md"]), runnable=ch.get("runnable", True)
        )
    toc_html = toc_nav_from_tokens(toc_tokens)
    toc_block = f'<aside class="toc">{toc_html}</aside>' if toc_html else ""
    kicker_mod = ch.get("kicker_mod", module_of(ch["n"]))
    course_title = ch.get("course_title", COURSE_TITLE)
    course_desc = ch.get("desc", COURSE_DESC)

    prev_html = (
        f'<a class="pager-link pager-prev" href="../{prev_e["url"]}">'
        f'<span class="pager-dir">上一章</span><span class="pager-name">{prev_e["title"]}</span></a>'
        if prev_e else '<span class="pager-spacer"></span>'
    )
    next_html = (
        f'<a class="pager-link pager-next" href="../{next_e["url"]}">'
        f'<span class="pager-dir">下一章</span><span class="pager-name">{next_e["title"]}</span></a>'
        if next_e else ""
    )

    body = f"""
<div class="layout doc-layout">
  <article class="doc" id="content">
    <header class="doc-head">
      <div class="doc-head-row">
        <p class="kicker"><span class="kicker-num">第 {ch["n"]} 章</span><span class="kicker-mod">{kicker_mod}</span></p>
        <button class="learn" data-ch="{ch.get("data_ch", ch["n"])}" type="button">标记已学</button>
      </div>
      <h1>{ch["title"]}</h1>
    </header>
    <div class="md">
{body_html}
    </div>
    <nav class="pager" aria-label="章节导航">
      {prev_html}
      {next_html}
    </nav>
  </article>
  {toc_block}
</div>
"""
    return page_shell(
        "../", f'第 {ch["n"]} 章 {ch["title"]} · {course_title}', body, url, entries, course_desc
    )


def project_page(proj: dict, entries: list[dict], prev_e: dict | None, next_e: dict | None) -> str:
    url = f"proj/{proj['key']}.html"
    text = proj["path"].read_text(encoding="utf-8")
    body_html, toc_tokens = convert_md(strip_leading_h1(text))
    toc_html = toc_nav_from_tokens(toc_tokens)
    toc_block = f'<aside class="toc">{toc_html}</aside>' if toc_html else ""

    prev_html = (
        f'<a class="pager-link pager-prev" href="../{prev_e["url"]}">'
        f'<span class="pager-dir">上一章</span><span class="pager-name">{prev_e["title"]}</span></a>'
        if prev_e else '<span class="pager-spacer"></span>'
    )
    next_html = (
        f'<a class="pager-link pager-next" href="../{next_e["url"]}">'
        f'<span class="pager-dir">下一章</span><span class="pager-name">{next_e["title"]}</span></a>'
        if next_e else ""
    )

    body = f"""
<div class="layout doc-layout">
  <article class="doc" id="content">
    <header class="doc-head">
      <div class="doc-head-row">
        <p class="kicker"><span class="kicker-num">项目案例</span><span class="kicker-mod">{proj["sub"]}</span></p>
      </div>
      <h1>{proj["title"]}</h1>
    </header>
    <div class="md">
{body_html}
    </div>
    <nav class="pager" aria-label="章节导航">
      {prev_html}
      {next_html}
    </nav>
  </article>
  {toc_block}
</div>
"""
    return page_shell(
        "../", f'{proj["title"]} · {COURSE_TITLE}', body, url, entries, COURSE_DESC
    )


def index_page(entries: list[dict]) -> str:
    chapter_total = sum(1 for e in entries if not e["is_project"])
    facts = f"{1 + len([s for s in SIBLINGS if any(e.get('course') == s['key'] for e in entries)])} 门课程，{chapter_total} 章，从 Python 核心到数据科学与后端框架"
    repl = """<div class="repl" aria-label="Python 交互示例">
<pre><code><span class="rp-prompt">&gt;&gt;&gt;</span> <span class="rp-code">from ai_stack import Series</span>
<span class="rp-prompt">&gt;&gt;&gt;</span> <span class="rp-code">series = Series(author=<span class="rp-str">"袁进"</span>)</span>
<span class="rp-prompt">&gt;&gt;&gt;</span> <span class="rp-code">series.course_titles</span>
<span class="rp-out">['Python语言核心精讲', '数据库', 'Python框架', '数据科学工具包']</span>
<span class="rp-prompt">&gt;&gt;&gt;</span> <span class="rp-code">series.philosophy</span>
<span class="rp-out">'全程干货，大量练习，重视概念与设计，弱化 API 使用'</span>
<span class="rp-prompt">&gt;&gt;&gt;</span> <span class="cursor" aria-hidden="true"></span></code></pre>
</div>"""

    py_chapters = [e for e in entries if not e["is_project"] and e.get("course", "py") == "py"]
    proj_entries = [e for e in entries if e["is_project"]]

    def home_row(e: dict) -> str:
        meta = f'{e["sections"]} 节' if e["sections"] else ""
        dch = e.get("data_ch", "")
        dch_attr = f' data-ch="{dch}"' if dch else ""
        icon = (
            '<span class="ch-num badge badge-mini bp" aria-hidden="true">◈</span>'
            if e["is_project"]
            else f'<span class="ch-num">{e["num"]:02d}</span>'
        )
        name = e["title"]
        if e.get("sub"):
            name += f'<span class="ch-sub">{e["sub"]}</span>'
        return (
            f'<a class="ch-row" href="{e["url"]}"{dch_attr}>'
            f'{icon}<span class="ch-name">{name}</span>'
            f'<span class="ch-meta">{meta}</span>'
            f'<span class="chev" aria-hidden="true">›</span></a>'
        )

    sections: list[str] = []
    # 大类一：Python语言核心精讲（卡片内按模块分子区块）
    py_rows: list[str] = []
    for mod_name, nums, _glyph, _cls in MODULES:
        py_rows.append(f'<div class="ch-modhead">{mod_name}</div>')
        py_rows.extend(home_row(e) for e in py_chapters if e["num"] in nums)
    py_rows.append('<div class="ch-modhead">项目案例</div>')
    py_rows.extend(home_row(e) for e in proj_entries)
    sections.append(
        f'<section class="catalog-group"><h2 class="mod-title">'
        f'<span class="badge b1" aria-hidden="true">Py</span>{COURSE_TITLE}</h2>'
        f'<div class="ch-list">{"".join(py_rows)}</div></section>'
    )
    # 大类二至四：同级课程
    for sib in SIBLINGS:
        rows = [home_row(e) for e in entries if e.get("course") == sib["key"]]
        if rows:
            desc = sib.get("desc", "")
            desc_html = f'<p class="mod-desc">{desc}</p>' if desc else ""
            sections.append(
                f'<section class="catalog-group"><h2 class="mod-title">'
                f'<span class="badge {sib["cls"]}" aria-hidden="true">{sib["glyph"]}</span>'
                f'{sib["title"]}</h2>{desc_html}'
                f'<div class="ch-list">{"".join(rows)}</div></section>'
            )

    body = f"""
<div class="layout home-layout">
  <article class="home" id="content">
    <header class="hero">
      <p class="hero-kicker">{COURSE_AUTHOR} 主讲 · 系列课程</p>
      <h1 class="hero-title">AI大全栈<span class="hl">课程手册</span></h1>
      <p class="hero-desc">袁进主讲的系列课程：Python 语言核心精讲、数据科学工具包、数据库、Python 框架，从语言基础一路到企业级后端部署。</p>
      <p class="hero-facts">{facts}</p>
      {repl}
    </header>
    {"".join(sections)}
    <footer class="home-foot">本站由 build_site.py 从课件 Markdown 自动生成 · 仅供学习使用</footer>
  </article>
</div>
"""
    return page_shell("", f"AI大全栈 · 课程手册", body, "index.html", entries, COURSE_DESC)


# --------------------------------------------------------------------------
# 静态资源
# --------------------------------------------------------------------------

STYLE_CSS = r"""
/* ===== 《Python语言核心精讲》课件站 · iOS 风格 ===== */
:root {
  color-scheme: light dark;
  --bg: #F2F2F7;
  --card: #FFFFFF;
  --label: #000000;
  --label2: rgba(60, 60, 67, 0.60);
  --label3: rgba(60, 60, 67, 0.33);
  --blue: #007AFF;
  --blue-tint: rgba(0, 122, 255, 0.12);
  --green: #34C759;
  --green-tint: rgba(52, 199, 89, 0.16);
  --green-ink: #1F8A3C;
  --fill: rgba(120, 120, 128, 0.16);
  --fill2: rgba(120, 120, 128, 0.08);
  --sep: rgba(60, 60, 67, 0.29);
  --sep-soft: rgba(60, 60, 67, 0.14);
  --code-bg: #F6F6F8;
  --code-border: rgba(60, 60, 67, 0.15);
  --code-fg: #1D1D1F;
  --code-out-bg: #FFFFFF;
  --code-err: #D70015;
  --code-inline: #C81E4B;
  --repl-bg: #1D1D1F;
  --mark: rgba(255, 204, 0, 0.45);
  --shadow: 0 10px 34px rgba(0, 0, 0, 0.10);
  --bar-bg: rgba(242, 242, 247, 0.82);
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC",
          "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
  --side-w: 296px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #000000;
    --card: #1C1C1E;
    --label: #F5F5F7;
    --label2: rgba(235, 235, 245, 0.60);
    --label3: rgba(235, 235, 245, 0.30);
    --blue: #0A84FF;
    --blue-tint: rgba(10, 132, 255, 0.22);
    --green: #30D158;
    --green-tint: rgba(48, 209, 88, 0.24);
    --green-ink: #30D158;
    --fill: rgba(120, 120, 128, 0.32);
    --fill2: rgba(120, 120, 128, 0.18);
    --sep: rgba(84, 84, 88, 0.60);
    --sep-soft: rgba(84, 84, 88, 0.36);
    --code-bg: #2A2A2C;
    --code-border: rgba(84, 84, 88, 0.5);
    --code-fg: #E8E8ED;
    --code-out-bg: #1C1C1E;
    --code-err: #FF453A;
    --code-inline: #FF7B92;
    --repl-bg: #1C1C1E;
    --mark: rgba(255, 214, 10, 0.35);
    --shadow: 0 10px 34px rgba(0, 0, 0, 0.55);
    --bar-bg: rgba(18, 18, 20, 0.82);
  }
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  * { animation: none !important; transition: none !important; }
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--label);
  font-family: var(--sans);
  font-size: 16.5px;
  line-height: 1.8;
  letter-spacing: 0.01em;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 3px; }
:focus-visible { outline: 3px solid rgba(0, 122, 255, 0.45); outline-offset: 2px; border-radius: 6px; }
::selection { background: var(--blue-tint); }

.skip {
  position: absolute; left: -9999px; top: 0; z-index: 100;
  background: var(--blue); color: #fff; padding: 8px 16px; border-radius: 0 0 10px 0;
}
.skip:focus { left: 0; top: 0; }

/* ===== 徽标 ===== */
.badge {
  display: inline-flex; align-items: center; justify-content: center; flex: none;
  width: 28px; height: 28px; border-radius: 8px;
  color: #fff; font-size: 14px; font-weight: 700; line-height: 1;
  font-family: var(--sans);
}
.badge-mini { width: 22px; height: 22px; border-radius: 6.5px; font-size: 11px; }
.b1 { background: linear-gradient(180deg, #3EA0FF, #0A6BFF); }
.b2 { background: linear-gradient(180deg, #8E8CFF, #5D5BD6); }
.b3 { background: linear-gradient(180deg, #4FD0E8, #1E9FD0); }
.b4 { background: linear-gradient(180deg, #FFB444, #F08A00); }
.b5 { background: linear-gradient(180deg, #D892FF, #A645DE); }
.bp { background: linear-gradient(180deg, #FF6B87, #F22B55); }
.b-ds { background: linear-gradient(180deg, #5BD877, #248A3D); }
.b-db { background: linear-gradient(180deg, #40D6CC, #00A39A); }
.b-fw { background: linear-gradient(180deg, #98989E, #48484A); }

/* ===== 左侧目录栏 ===== */
.sidebar {
  position: fixed; inset: 0 auto 0 0; width: var(--side-w); z-index: 40;
  background: var(--bg); color: var(--label);
  border-right: 0.5px solid var(--sep-soft);
  display: flex; flex-direction: column;
}
.side-head { padding: 20px 18px 14px; }
.side-brand { display: block; color: var(--label); }
.side-brand:hover { text-decoration: none; }
.side-brand-name {
  display: block; font-size: 17px; font-weight: 700; letter-spacing: -0.2px; line-height: 1.4;
}
.side-brand-sub { display: block; margin-top: 3px; font-size: 12px; color: var(--label2); }
.search { position: relative; margin-top: 14px; }
.search input {
  width: 100%; height: 36px; padding: 0 12px; font: 15px/1.4 var(--sans);
  color: var(--label); background: var(--fill);
  border: none; border-radius: 10px; appearance: none; -webkit-appearance: none;
}
.search input::placeholder { color: var(--label3); }
.search input:focus { outline: none; box-shadow: 0 0 0 3.5px rgba(0, 122, 255, 0.30); }
.search-panel {
  position: absolute; top: calc(100% + 8px); left: -8px; right: -8px; z-index: 50;
  max-height: 62vh; overflow: auto;
  background: var(--card); border: 0.5px solid var(--sep-soft);
  border-radius: 13px; box-shadow: var(--shadow);
  padding: 6px;
}
.search-item { display: block; padding: 9px 12px; border-radius: 9px; color: var(--label); }
.search-item:hover, .search-item:focus { background: var(--fill2); text-decoration: none; }
.search-item-title { font-size: 14px; font-weight: 600; }
.search-item-title .s-num { color: var(--blue); font-family: var(--mono); margin-right: 6px; font-size: 12px; }
.search-item-sec { font-size: 12.5px; color: var(--label2); margin-top: 2px; line-height: 1.55; }
.search-item mark { background: none; color: var(--blue); padding: 0; }
.search-empty { padding: 14px; font-size: 13px; color: var(--label2); text-align: center; margin: 0; }

.side-nav { flex: 1; overflow-y: auto; padding: 6px 12px 20px; }
.side-home {
  display: block; padding: 8px 12px; margin-top: 6px; border-radius: 10px;
  font-size: 14.5px; font-weight: 500; color: var(--label);
}
.side-home.active { background: var(--blue-tint); color: var(--blue); }
.side-home:hover { background: var(--fill2); text-decoration: none; }
.side-group { margin-top: 18px; }
.side-group-title {
  display: flex; align-items: center; gap: 7px;
  margin: 0 0 4px; padding: 0 12px; font-size: 12px; letter-spacing: 0.08em;
  color: var(--label2); font-weight: 600;
}
.side-group-title .badge-mini { width: 18px; height: 18px; border-radius: 5.5px; font-size: 10px; }
.side-subhead {
  margin: 12px 0 2px; padding: 0 12px;
  font-size: 11px; letter-spacing: 0.08em; color: var(--label3); font-weight: 600;
}

/* ===== 折叠树（大类 → 小类 → 小小类） ===== */
.fold-body { display: grid; grid-template-rows: 1fr; transition: grid-template-rows 0.22s ease; }
.js .fold:not(.open) > .fold-body { grid-template-rows: 0fr; }
.fold-inner { overflow: hidden; min-height: 0; }
.side-chev {
  display: inline-block; flex: none; font-size: 13px; line-height: 1;
  color: var(--label3); transition: transform 0.2s ease;
}
.fold.open .fold-head .side-chev, .side-ch.fold.open .side-fold .side-chev {
  transform: rotate(90deg);
}
.side-cat-head, .side-mod-head {
  display: flex; align-items: center; gap: 8px; width: 100%;
  background: none; border: none; cursor: pointer; text-align: left;
  font-family: var(--sans); color: var(--label);
}
.side-cat-head { padding: 8px 10px; border-radius: 10px; font-size: 14px; font-weight: 600; }
.side-cat-head:hover { background: var(--fill2); }
.side-cat-name { flex: 1; min-width: 0; }
.side-mod-head {
  padding: 6px 10px 6px 4px; border-radius: 8px;
  font-size: 12px; font-weight: 600; color: var(--label2); letter-spacing: 0.05em;
}
.side-mod-head:hover { background: var(--fill2); }
.side-mod-head .side-chev { font-size: 11px; }
.side-mod .side-group, .side-cat-body .side-group { margin: 0; }
.side-ch-row { display: flex; align-items: center; }
.side-ch-row .side-link { flex: 1; min-width: 0; }
.side-mod .side-ch-row .side-link, .side-mod .side-ch-row .side-fold { margin-left: 10px; }
.side-fold {
  background: none; border: none; cursor: pointer; flex: none;
  padding: 4px 8px; border-radius: 6px; color: inherit;
}
.side-fold:hover { background: var(--fill2); }
.side-sec { padding: 0 8px 4px 44px; }
.side-sec a {
  display: block; padding: 3px 8px; font-size: 12.5px; line-height: 1.5;
  color: var(--label2); border-radius: 6px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.side-sec a:hover { color: var(--blue); background: var(--fill2); text-decoration: none; }
.side-link {
  display: flex; align-items: center; gap: 9px;
  padding: 7px 12px; border-radius: 10px; font-size: 13.5px; line-height: 1.5;
  color: var(--label);
}
.side-link:hover { background: var(--fill2); text-decoration: none; }
.side-link.active { background: var(--blue-tint); color: var(--blue); font-weight: 600; }
.side-num { font-family: var(--mono); font-size: 11.5px; color: var(--label3); flex: none; width: 20px; text-align: right; }
.side-link.active .side-num { color: var(--blue); }
.side-name { flex: 1; min-width: 0; }
.side-link.done .side-name::after { content: " ✓"; color: var(--green-ink); font-size: 12px; font-weight: 700; }
.side-link-proj .side-num { width: 22px; text-align: center; }

.side-foot {
  padding: 14px 18px calc(16px + env(safe-area-inset-bottom));
  border-top: 0.5px solid var(--sep-soft);
  display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--label2);
}
.progress { flex: 1; height: 4px; background: var(--fill); border-radius: 2px; overflow: hidden; }
.progress i { display: block; height: 100%; width: 0; background: var(--blue); border-radius: 2px; transition: width 0.3s; }

.backdrop { display: none; }

/* ===== 移动端顶栏（毛玻璃） ===== */
.topbar {
  display: none; position: fixed; top: 0; left: 0; right: 0; z-index: 30;
  align-items: center; gap: 10px; padding: calc(10px + env(safe-area-inset-top)) 14px 10px;
  background: var(--bar-bg);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 0.5px solid var(--sep-soft);
}
.burger {
  background: var(--fill); border: none; color: var(--label);
  border-radius: 8px; padding: 5px 11px; font-size: 16px; cursor: pointer;
}
.topbar-title { color: var(--label); font-size: 16px; font-weight: 600; letter-spacing: -0.2px; }

/* ===== 主布局 ===== */
.layout {
  margin-left: var(--side-w); min-height: 100vh;
  display: flex; justify-content: center; gap: 48px;
  padding: 40px 32px 110px;
}
.doc {
  width: min(47rem, 100%);
  background: var(--card); border-radius: 18px; padding: 44px 52px 40px;
  animation: rise 0.4s ease both;
}
@keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

.doc-head { margin-bottom: 6px; }
.doc-head-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.kicker { margin: 0 0 8px; font-size: 13px; color: var(--label2); font-weight: 600; letter-spacing: 0.02em; }
.kicker-mod { margin-left: 10px; color: var(--label3); font-weight: 500; }
h1 {
  font-size: 31px; font-weight: 700; line-height: 1.35;
  letter-spacing: -0.5px; margin: 0 0 26px; color: var(--label);
}
.learn {
  flex: none; align-self: flex-start;
  font: 600 13.5px/1 var(--sans); color: var(--blue); background: var(--blue-tint);
  border: none; border-radius: 999px; padding: 8px 16px; cursor: pointer;
}
.learn:hover { filter: brightness(1.05); }
.learn.done { background: var(--green-tint); color: var(--green-ink); }

/* ===== 目录（右栏） ===== */
.toc {
  width: 200px; flex: none; position: sticky; top: 44px; align-self: flex-start;
  max-height: calc(100vh - 100px); overflow: auto; padding-top: 46px;
}
.toc-title { margin: 0 0 8px; font-size: 12px; color: var(--label2); font-weight: 600; letter-spacing: 0.06em; }
.toc-list { list-style: none; margin: 0; padding: 0; font-size: 13px; line-height: 1.5; }
.toc-list .toc-list { padding-left: 13px; }
.toc-list a { display: block; padding: 4px 8px; color: var(--label2); border-radius: 7px; }
.toc-list a:hover { color: var(--label); background: var(--fill2); text-decoration: none; }
.toc-list a.active { color: var(--blue); font-weight: 600; }
.toc-l3 a { font-size: 12.5px; }

/* ===== 正文排版 ===== */
.md { font-size: 16.5px; }
.md p { margin: 0 0 1.15em; }
.md h2, .md h3, .md h4 { color: var(--label); line-height: 1.4; }
.md h2 { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; margin: 2em 0 0.7em; }
.md h3 { font-size: 18.5px; font-weight: 650; margin: 1.6em 0 0.5em; }
.md h4 { font-size: 16.5px; font-weight: 650; margin: 1.4em 0 0.4em; }
.md hr { border: 0; border-top: 0.5px solid var(--sep-soft); margin: 2.2em 0; }
.md strong { font-weight: 650; }
.md mark {
  background: linear-gradient(transparent 10%, var(--mark) 10% 90%, transparent 90%);
  color: inherit; padding: 0 2px; border-radius: 3px;
  box-decoration-break: clone; -webkit-box-decoration-break: clone;
}
.md ul, .md ol { padding-left: 1.5em; margin: 0 0 1.15em; }
.md li { margin: 0.3em 0; }
.md li::marker { color: var(--label3); }
.md img { max-width: 100%; height: auto; border-radius: 12px; }
.md blockquote {
  margin: 1.3em 0; padding: 0.2em 1.2em;
  background: var(--fill2); border-radius: 12px; color: var(--label);
}
.md blockquote p { margin: 0.8em 0; }
.md table { border-collapse: collapse; width: 100%; margin: 1.3em 0; font-size: 14.5px; }
.md th, .md td { border-bottom: 0.5px solid var(--sep-soft); padding: 8px 12px; text-align: left; }
.md th { color: var(--label2); font-weight: 600; font-size: 13px; }
.md tr:last-child td { border-bottom: none; }
.md :not(pre) > code {
  font-family: var(--mono); font-size: 0.86em; color: var(--code-inline);
  background: var(--fill2); border-radius: 5px; padding: 1.5px 6px; margin: 0 1px;
}
.md a { -webkit-text-decoration-skip-ink: none; }

/* ===== 代码卡片 ===== */
.codehilite, .md pre {
  position: relative; background: var(--code-bg);
  border: 0.5px solid var(--code-border);
  border-radius: 14px; margin: 1.4em 0; overflow: hidden;
}
.md pre { padding: 18px 26px 20px; overflow-x: auto; }
.codehilite > pre { margin: 0; padding: 18px 26px 20px; overflow-x: auto; }
.md pre, .md pre code {
  font-family: var(--mono); font-size: 13.5px; line-height: 1.85;
  color: var(--code-fg); background: none; padding: 0; border: 0; letter-spacing: 0;
}
.copy-btn {
  position: absolute; top: 10px; right: 10px; z-index: 2;
  font: 600 11.5px/1 var(--sans); color: var(--label2);
  background: var(--fill2);
  border: none; border-radius: 7px;
  padding: 6px 11px; cursor: pointer; opacity: 0; transition: opacity 0.15s;
}
.codehilite:hover .copy-btn, .md pre:hover .copy-btn, .copy-btn:focus-visible { opacity: 1; }
.copy-btn:hover { color: var(--label); }
.copy-btn.ok { color: var(--green-ink); }

/* 可运行的 Python 代码卡 */
.codecard {
  background: var(--code-bg);
  border: 0.5px solid var(--code-border);
  border-radius: 14px; margin: 1.4em 0; overflow: hidden;
}
.codecard .codehilite { background: none; border: none; border-radius: 0; margin: 0; }
.codecard .codehilite > pre { padding: 12px 26px 22px; }
.codecard-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 12px 12px 0 26px;
}
.codecard-lang { font: 500 11px/1 var(--mono); color: var(--label3); }
.codecard-actions { display: flex; gap: 8px; }
.codecard-btn {
  font: 600 12.5px/1 var(--sans); border: none; cursor: pointer;
  border-radius: 999px; padding: 7px 13px;
  background: var(--fill2); color: var(--label2);
}
.codecard-btn:hover { background: var(--fill); }
.codecard-run { background: var(--blue-tint); color: var(--blue); }
.codecard-run:hover { background: var(--blue-tint); filter: brightness(0.97); }
.codecard-run.busy { opacity: 0.55; pointer-events: none; }
.run-ico { font-size: 9px; margin-right: 5px; vertical-align: 1px; }
.codecard-out {
  margin: 0; padding: 14px 26px 18px;
  border-top: 0.5px solid var(--code-border);
  background: var(--code-out-bg);
  font-family: var(--mono); font-size: 13px; line-height: 1.75;
  color: var(--label2); white-space: pre-wrap; word-break: break-word;
  max-height: 340px; overflow: auto;
}
.codecard-out.err { color: var(--code-err); }
pre[contenteditable="true"] { outline: none; caret-color: var(--blue); -webkit-user-modify: read-write-plaintext-only; }

/* ===== Notebook 单元格 ===== */
.nb-cell .codehilite { margin: 1.4em 0 0.6em; }
.nb-out {
  margin: 0 0 1.4em; padding: 14px 24px 16px;
  background: var(--code-out-bg);
  border: 0.5px solid var(--code-border); border-radius: 14px;
}
.nb-stream, .nb-result, .nb-error {
  margin: 0 0 10px; font-family: var(--mono); font-size: 13px; line-height: 1.75;
  color: var(--label2); white-space: pre-wrap; word-break: break-word;
}
.nb-stream:last-child, .nb-result:last-child, .nb-error:last-child { margin-bottom: 0; }
.nb-error { color: var(--code-err); }
.nb-img { display: block; max-width: 100%; height: auto; border-radius: 8px; margin: 4px 0; }

/* ===== 章节翻页 ===== */
.pager { display: flex; gap: 12px; margin-top: 52px; }
.pager-link {
  flex: 1; display: flex; flex-direction: column; gap: 3px; padding: 14px 18px;
  border-radius: 14px; color: var(--label); background: var(--fill2);
}
.pager-link:hover { text-decoration: none; background: var(--fill); }
.pager-next { text-align: right; }
.pager-dir { font-size: 12px; color: var(--blue); font-weight: 600; }
.pager-name { font-size: 14.5px; font-weight: 600; color: var(--label); }
.pager-spacer { flex: 1; }

/* ===== 首页 ===== */
.home { width: min(50rem, 100%); }
.hero { padding: 26px 6px 10px; }
.hero-kicker { margin: 0 0 10px; font-size: 14px; color: var(--label2); font-weight: 600; }
.hero-title {
  font-size: clamp(34px, 5vw, 46px); font-weight: 800;
  letter-spacing: -0.8px; line-height: 1.25; margin: 0 0 14px; color: var(--label);
}
.hl { background: linear-gradient(transparent 55%, var(--mark) 55% 92%, transparent 92%); padding: 0 3px; border-radius: 3px; }
.hero-desc { font-size: 16px; color: var(--label2); max-width: 40em; margin: 0 0 8px; }
.hero-facts { font-size: 13px; color: var(--label3); margin: 0 0 30px; }
.repl {
  background: var(--repl-bg); border-radius: 18px; padding: 22px 26px;
  box-shadow: var(--shadow); margin-bottom: 10px;
}
.repl pre { margin: 0; overflow-x: auto; }
.repl code { font-family: var(--mono); font-size: 13.5px; line-height: 1.9; color: #E8E8ED; }
.rp-prompt { color: #0A84FF; user-select: none; font-weight: 600; }
.rp-code { color: #E8E8ED; }
.rp-str { color: #FF7B92; }
.rp-kw { color: #BF5AF2; }
.rp-out { color: #8E8E93; }
.cursor {
  display: inline-block; width: 8px; height: 17px; margin-bottom: -3px;
  background: #0A84FF; animation: blink 1.1s steps(1) infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .cursor { animation: none; } }

.catalog-group { margin-top: 34px; }
.mod-desc { margin: -2px 0 10px; padding: 0 4px; font-size: 13px; line-height: 1.7; color: var(--label2); }
.mod-title {
  display: flex; align-items: center; gap: 11px;
  font-size: 20px; font-weight: 700; letter-spacing: -0.3px; color: var(--label);
  margin: 0 0 10px; padding: 0 4px;
}
.ch-list {
  display: flex; flex-direction: column;
  background: var(--card); border-radius: 16px; overflow: hidden;
}
.ch-row {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  color: var(--label); font-size: 15.5px;
}
.ch-row + .ch-row { border-top: 0.5px solid var(--sep-soft); }
.ch-modhead {
  padding: 9px 16px 5px; font-size: 12px; font-weight: 600;
  color: var(--label3); background: var(--fill2); letter-spacing: 0.06em;
}
.ch-row:hover { background: var(--fill2); text-decoration: none; }
.ch-num { font-family: var(--mono); font-size: 13px; color: var(--label3); width: 24px; flex: none; text-align: center; }
.ch-name { font-weight: 500; min-width: 0; }
.ch-sub { display: block; font-size: 12.5px; color: var(--label2); font-weight: 400; margin-top: 1px; }
.ch-meta { margin-left: auto; font-size: 13px; color: var(--label3); flex: none; }
.chev { color: var(--label3); font-size: 19px; font-weight: 600; flex: none; line-height: 1; margin-left: 2px; }
.ch-row.done .ch-name::after { content: " ✓"; color: var(--green-ink); font-size: 13px; font-weight: 700; }
.ch-row-proj .ch-num { width: 22px; }
.home-foot { margin-top: 56px; font-size: 12px; color: var(--label3); text-align: center; }

/* ===== 响应式 ===== */
@media (max-width: 1240px) {
  .toc { display: none; }
  .layout { gap: 0; }
}
@media (max-width: 920px) {
  .topbar { display: flex; }
  .layout { margin-left: 0; padding: 78px 14px 70px; }
  .doc { padding: 28px 22px 30px; border-radius: 16px; }
  .sidebar { transform: translateX(-100%); transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1); width: min(320px, 85vw); }
  body.nav-open .sidebar { transform: none; box-shadow: 0 0 70px rgba(0, 0, 0, 0.35); }
  body.nav-open .backdrop {
    display: block; position: fixed; inset: 0; z-index: 35;
    background: rgba(0, 0, 0, 0.4);
  }
  h1 { font-size: 26px; }
  .md h2 { font-size: 20px; }
  .pager { flex-direction: column; }
  .pager-next { text-align: left; }
  .repl { padding: 16px 16px; border-radius: 14px; }
  .md pre, .codehilite > pre { padding: 14px 18px 16px; }
  .codecard .codehilite > pre { padding: 10px 18px 16px; }
  .codecard-bar { padding: 10px 10px 0 18px; }
  .codecard-out { padding: 12px 18px 14px; }
}
"""

APP_JS = r"""
(function () {
  "use strict";
  var base = document.body.dataset.base || "";
  var LS_KEY = "pycourse-done";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- 已学进度 ---------- */
  function getDone() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch (e) { return {}; }
  }
  function setDone(map) { localStorage.setItem(LS_KEY, JSON.stringify(map)); }
  function refreshProgress() {
    var done = getDone();
    var total = $$(".side-link[data-ch]").length;
    var count = $$(".side-link[data-ch]").filter(function (a) { return done[a.dataset.ch]; }).length;
    $$(".side-link[data-ch]").forEach(function (a) {
      a.classList.toggle("done", !!done[a.dataset.ch]);
    });
    $$(".ch-row[data-ch]").forEach(function (a) {
      a.classList.toggle("done", !!done[a.dataset.ch]);
    });
    var bar = $("#progress-bar"), text = $("#progress-text");
    if (bar) bar.style.width = (total ? (count / total) * 100 : 0) + "%";
    if (text) text.textContent = "已学 " + count + " / " + total;
  }
  function initLearn() {
    var learnBtn = $(".learn");
    if (!learnBtn) return;
    var n = learnBtn.dataset.ch;
    var paint = function () {
      var on = !!getDone()[n];
      learnBtn.classList.toggle("done", on);
      learnBtn.textContent = on ? "✓ 已学" : "标记已学";
    };
    paint();
    learnBtn.addEventListener("click", function () {
      var d = getDone();
      if (d[n]) delete d[n]; else d[n] = true;
      setDone(d);
      paint(); refreshProgress();
    });
  }
  refreshProgress();

  /* ---------- 折叠树（大类 / 小类 / 小小类） ---------- */
  var TREE_KEY = "pycourse-tree";
  var treeOpen = {};
  try {
    (JSON.parse(localStorage.getItem(TREE_KEY)) || []).forEach(function (k) {
      treeOpen[k] = true;
    });
  } catch (e) {}
  function setFold(el, open) {
    el.classList.toggle("open", open);
    var head = el.querySelector(".fold-head");
    if (head) head.setAttribute("aria-expanded", open ? "true" : "false");
  }
  function initFolds() {
    $$(".fold").forEach(function (el) {
      var head = el.querySelector(".fold-head");
      if (!head) return;
      if (head.hasAttribute("data-pinned")) { setFold(el, true); }
      else if (treeOpen[el.dataset.fold]) { setFold(el, true); }
      head.addEventListener("click", function () {
        var open = !el.classList.contains("open");
        setFold(el, open);
        if (open) treeOpen[el.dataset.fold] = true;
        else delete treeOpen[el.dataset.fold];
        try {
          localStorage.setItem(TREE_KEY, JSON.stringify(Object.keys(treeOpen)));
        } catch (e) {}
      });
    });
  }

  /* ---------- 代码复制（非 Python 块） ---------- */
  function initCopy() {
  $$(".md .codehilite:not(.lang-python), .md > pre").forEach(function (block) {
    var pre = block.querySelector("pre") || block;
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "复制";
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(pre.textContent).then(function () {
        btn.textContent = "已复制"; btn.classList.add("ok");
        setTimeout(function () { btn.textContent = "复制"; btn.classList.remove("ok"); }, 1600);
      });
    });
    block.appendChild(btn);
  });
  }

  /* ---------- 轻量 Python 高亮（编辑后自动重新着色） ---------- */
  var PY_KW = /^(?:def|return|class|if|elif|else|for|while|in|not|and|or|import|from|as|with|try|except|finally|raise|pass|break|continue|lambda|global|nonlocal|yield|del|assert|async|await|is|None|True|False)\b/;
  var PY_BUILTIN = /^(?:print|len|range|str|int|float|bool|list|dict|set|tuple|type|isinstance|issubclass|super|getattr|setattr|hasattr|delattr|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|open|repr|format|input|iter|next|any|all|id|hash|callable|classmethod|staticmethod|property|self|cls)\b/;
  function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function pyHighlight(src) {
    // 引号常量逐段拼接，避免在本文件的三引号字符串里出现字面量三连引号
    var DQ = '"';
    var TQ = DQ + DQ + DQ;
    var quoteRe = new RegExp("^(?:[rbfu]{0,2})(" + TQ + "|'''" + "|" + DQ + "|')");
    var out = [], i = 0, n = src.length;
    while (i < n) {
      var c = src[i];
      if (c === "#") {
        var j = src.indexOf("\n", i); if (j < 0) j = n;
        out.push('<span class="c1">' + escHtml(src.slice(i, j)) + "</span>"); i = j; continue;
      }
      var sm = quoteRe.exec(src.slice(i));
      if (sm) {
        var q = sm[1], qi = i + sm[0].length - q.length, search = qi + q.length, end = n;
        while (true) {
          var k = src.indexOf(q, search);
          if (k < 0) break;
          var bs = 0, p = k - 1;
          while (src[p] === "\\") { bs++; p--; }
          if (bs % 2 === 0) { end = k + q.length; break; }
          search = k + q.length;
        }
        out.push('<span class="s1">' + escHtml(src.slice(i, end)) + "</span>"); i = end; continue;
      }
      if (c >= "0" && c <= "9") {
        var nm = /^\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?[jJ]?/.exec(src.slice(i));
        out.push('<span class="mi">' + escHtml(nm[0]) + "</span>"); i += nm[0].length; continue;
      }
      if (c === "@") {
        var dm = /^@[\w.]+/.exec(src.slice(i));
        if (dm) { out.push('<span class="nd">' + escHtml(dm[0]) + "</span>"); i += dm[0].length; continue; }
      }
      if (/[A-Za-z_]/.test(c)) {
        var im = /^[\w]+/.exec(src.slice(i))[0];
        var isCall = /^\s*\(/.test(src.slice(i + im.length));
        if (PY_KW.test(im)) out.push('<span class="k">' + escHtml(im) + "</span>");
        else if (PY_BUILTIN.test(im)) out.push('<span class="nb">' + escHtml(im) + "</span>");
        else if (isCall) out.push('<span class="nf">' + escHtml(im) + "</span>");
        else if (/^[A-Z]/.test(im)) out.push('<span class="nc">' + escHtml(im) + "</span>");
        else out.push(escHtml(im));
        i += im.length; continue;
      }
      out.push(escHtml(c)); i++;
    }
    return out.join("");
  }
  function caretOffset(el) {
    var sel = window.getSelection();
    if (!sel.rangeCount || !el.contains(sel.anchorNode)) return null;
    var range = sel.getRangeAt(0).cloneRange();
    var pre = document.createRange();
    pre.selectNodeContents(el);
    pre.setEnd(range.endContainer, range.endOffset);
    return pre.toString().length;
  }
  function setCaretAt(el, offset) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var node, cur = 0, r, s;
    while ((node = walker.nextNode())) {
      if (cur + node.length >= offset) {
        r = document.createRange();
        r.setStart(node, offset - cur);
        r.collapse(true);
        s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        return;
      }
      cur += node.length;
    }
    r = document.createRange(); r.selectNodeContents(el); r.collapse(false);
    s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  /* ---------- 可运行的 Python 代码卡 ---------- */
  var pyodideReady = null;
  function loadFrom(indexURL) {
    return import(indexURL + "pyodide.mjs").then(function (m) {
      return m.loadPyodide({ indexURL: indexURL });
    });
  }
  function ensurePyodide() {
    if (!pyodideReady) {
      var local = base + "assets/pyodide/";
      var CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
      pyodideReady = loadFrom(local).catch(function () { return loadFrom(CDN); });
    }
    return pyodideReady;
  }

  function initCodeCards() {
    $$(".md .codehilite.lang-python:not(.lang-norun)").forEach(function (block) {
    var pre = block.querySelector("pre");
    if (!pre) return;
    var card = document.createElement("div");
    card.className = "codecard";
    var bar = document.createElement("div");
    bar.className = "codecard-bar";
    bar.innerHTML =
      '<span class="codecard-lang">python</span>' +
      '<span class="codecard-actions">' +
      '<button type="button" class="codecard-btn codecard-reset" hidden>还原</button>' +
      '<button type="button" class="codecard-btn codecard-run"><span class="run-ico">▶</span>运行</button>' +
      "</span>";
    var out = document.createElement("pre");
    out.className = "codecard-out";
    out.hidden = true;
    block.parentNode.insertBefore(card, block);
    card.appendChild(bar);
    card.appendChild(block);
    card.appendChild(out);

    var emptySpan = pre.querySelector("span:empty");
    if (emptySpan && emptySpan === pre.firstChild) emptySpan.remove();

    var original = pre.textContent;
    var dirty = false;
    var running = false;
    var composing = false;
    var hlTimer = null;
    var resetBtn = bar.querySelector(".codecard-reset");
    var runBtn = bar.querySelector(".codecard-run");

    pre.contentEditable = "true";
    pre.spellcheck = false;
    pre.setAttribute("autocorrect", "off");
    pre.setAttribute("autocapitalize", "off");
    pre.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        document.execCommand("insertText", false, "    ");
      }
    });
    pre.addEventListener("compositionstart", function () { composing = true; });
    pre.addEventListener("compositionend", function () {
      composing = false;
      scheduleHighlight();
    });
    function scheduleHighlight() {
      if (composing) return;
      clearTimeout(hlTimer);
      hlTimer = setTimeout(function () {
        var off = caretOffset(pre);
        pre.innerHTML = pyHighlight(pre.textContent);
        if (off !== null) setCaretAt(pre, off);
      }, 250);
    }
    pre.addEventListener("input", function () {
      if (!dirty) { dirty = true; resetBtn.hidden = false; }
      scheduleHighlight();
    });
    resetBtn.addEventListener("click", function () {
      pre.innerHTML = pyHighlight(original);
      dirty = false;
      resetBtn.hidden = true;
      out.hidden = true;
    });

    runBtn.addEventListener("click", function () {
      if (running) return;
      running = true;
      runBtn.classList.add("busy");
      runBtn.innerHTML = "运行中…";
      out.hidden = false;
      out.classList.remove("err");
      out.textContent = pyodideReady ? "" : "正在加载 Python 运行时…（首次约需几秒）";
      var write = function (s) {
        out.textContent += s + "\n";
        out.scrollTop = out.scrollHeight;
      };
      ensurePyodide().then(function (py) {
        if (out.textContent.indexOf("正在加载") === 0) out.textContent = "";
        py.setStdout({ batched: write });
        py.setStderr({ batched: write });
        var code = pre.textContent.replace(/\n+$/, "");
        return py.runPythonAsync(code).then(function (res) {
          if (res !== undefined && res !== null) write(String(res));
          if (res && typeof res.destroy === "function") res.destroy();
        });
      }).catch(function (e) {
        var msg = e && e.message ? e.message : String(e);
        out.textContent += (out.textContent ? "\n" : "") + msg;
        out.classList.add("err");
      }).then(function () {
        running = false;
        runBtn.classList.remove("busy");
        runBtn.innerHTML = '<span class="run-ico">▶</span>运行';
      });
    });
  });
  }

  /* ---------- 右栏目录 scrollspy ---------- */
  var pageSpy = null;
  function initScrollspy() {
    if (pageSpy) { pageSpy.disconnect(); pageSpy = null; }
    var tocLinks = $$(".toc-list a");
    if (!tocLinks.length || !("IntersectionObserver" in window)) return;
    var byId = {};
    tocLinks.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var headings = Object.keys(byId)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    var active = null;
    pageSpy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          if (active) active.classList.remove("active");
          active = byId[en.target.id];
          active.classList.add("active");
        }
      });
    }, { rootMargin: "-10% 0px -75% 0px", threshold: 0 });
    headings.forEach(function (h) { pageSpy.observe(h); });
  }

  /* ---------- 搜索 ---------- */
  var input = $("#search-input"), panel = $("#search-panel");
  var INDEX = null, FETCH_FAILED = false;
  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function snippet(text, q) {
    var i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) { return esc(text.slice(0, 60)); }
    var start = Math.max(0, i - 18);
    var frag = text.slice(start, i + q.length + 42);
    var marked = esc(frag).replace(
      new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
      function (m) { return "<mark>" + m + "</mark>"; }
    );
    return (start > 0 ? "…" : "") + marked;
  }
  function search(q) {
    if (!INDEX) return [];
    var out = [];
    var ql = q.toLowerCase();
    INDEX.forEach(function (ch) {
      var hits = [];
      if (ch.title.toLowerCase().indexOf(ql) >= 0) {
        hits.push({ sec: null, body: "第 " + ch.n + " 章目录项", anchor: null });
      }
      ch.sections.forEach(function (s) {
        if (s.name.toLowerCase().indexOf(ql) >= 0) {
          hits.push({ sec: s.name, body: s.body, anchor: s.anchor });
        } else if (s.body.toLowerCase().indexOf(ql) >= 0) {
          hits.push({ sec: s.name, body: s.body, anchor: s.anchor });
        }
      });
      out.push({ ch: ch, hits: hits.slice(0, 3) });
    });
    return out.filter(function (r) { return r.hits.length; }).slice(0, 10);
  }
  function renderResults(q, results) {
    if (!q) { panel.hidden = true; return; }
    if (INDEX === null) {
      panel.innerHTML = '<p class="search-empty">索引加载中…</p>';
      panel.hidden = false; return;
    }
    if (!results.length) {
      panel.innerHTML = '<p class="search-empty">' +
        (FETCH_FAILED
          ? "直接打开文件时搜索不可用，请通过本地服务器访问"
          : "没有找到「" + esc(q) + "」相关内容") +
        "</p>";
      panel.hidden = false; return;
    }
    var html = results.map(function (r) {
      return r.hits.map(function (h) {
        var href = base + r.ch.url + (h.anchor ? "#" + h.anchor : "");
        return '<a class="search-item" href="' + href + '">' +
          '<span class="search-item-title"><span class="s-num">' +
          (r.ch.n ? String(r.ch.n).padStart(2, "0") : "◈") + "</span>" +
          esc(r.ch.title) + "</span>" +
          (h.sec ? '<span class="search-item-sec">' + esc(h.sec) + "</span>" : "") +
          '<span class="search-item-sec">' + snippet(h.body || h.sec || "", q) + "</span>" +
          "</a>";
      }).join("");
    }).join("");
    panel.innerHTML = html;
    panel.hidden = false;
  }
  if (input && panel) {
    fetch(base + "assets/search.json")
      .then(function (r) { return r.json(); })
      .then(function (data) { INDEX = data; })
      .catch(function () { INDEX = []; FETCH_FAILED = true; });
    input.addEventListener("input", function () { renderResults(input.value.trim(), search(input.value.trim())); });
    input.addEventListener("focus", function () { if (input.value.trim()) renderResults(input.value.trim(), search(input.value.trim())); });
    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && e.target !== input) panel.hidden = true;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { panel.hidden = true; input.blur(); }
    });
  }

  /* ---------- 侧栏滚动定位：跳转后让当前章节保持可见 ---------- */
  function jumpToActive() {
    var sideNav = $(".side-nav");
    if (!sideNav) return;
    var active = sideNav.querySelector(".side-link.active");
    if (!active) return;
    active.scrollIntoView({ block: "nearest", inline: "nearest" });
    // 贴着底边时上移一点，让当前章节和它的下一章都能看到
    var nb = sideNav.getBoundingClientRect().bottom;
    var ab = active.getBoundingClientRect().bottom;
    if (nb - ab < 32) sideNav.scrollTop -= 32 - (nb - ab);
  }
  function bindSideNavScroll() {
    var sideNav = $(".side-nav");
    if (!sideNav) return;
    var savedScroll = NaN;
    try {
      savedScroll = parseInt(sessionStorage.getItem("pycourse-side-scroll"), 10);
    } catch (e) {}
    if (!isNaN(savedScroll)) sideNav.scrollTop = savedScroll;
    var scrollTimer = null;
    sideNav.addEventListener("scroll", function () {
      if (scrollTimer) clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function () {
        try {
          sessionStorage.setItem("pycourse-side-scroll", String(sideNav.scrollTop));
        } catch (e) {}
      }, 120);
    });
  }
  bindSideNavScroll();
  jumpToActive();
  setTimeout(jumpToActive, 300); // 等折叠展开动画结束再校准一次

  /* ---------- 移动端抽屉 ---------- */
  var burger = $("#burger");
  if (burger) {
    burger.addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
      burger.setAttribute("aria-expanded", document.body.classList.contains("nav-open"));
    });
    $("#backdrop").addEventListener("click", function () {
      document.body.classList.remove("nav-open");
    });
  }

  /* ---------- 键盘翻页 ---------- */
  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea") || e.target.isContentEditable ||
        e.metaKey || e.ctrlKey || e.altKey) return;
    var prev = $(".pager-prev"), next = $(".pager-next");
    if (e.key === "ArrowLeft" && prev) navigate(prev.href, true);
    if (e.key === "ArrowRight" && next) navigate(next.href, true);
  });

  /* ---------- 客户端路由：站内跳转无刷新 ---------- */
  function applyPage(doc) {
    document.title = doc.title;
    var newLayout = doc.querySelector(".layout");
    var oldLayout = document.querySelector(".layout");
    if (newLayout && oldLayout) oldLayout.replaceWith(newLayout);
    var newNav = doc.querySelector(".side-nav");
    var oldNav = document.querySelector(".side-nav");
    if (newNav && oldNav) oldNav.replaceWith(newNav);
    var input = $("#search-input"), panel = $("#search-panel");
    if (input) input.value = "";
    if (panel) panel.hidden = true;
    document.body.classList.remove("nav-open");
    bindSideNavScroll();
    initFolds();
    initLearn();
    initCopy();
    initCodeCards();
    initScrollspy();
    refreshProgress();
    jumpToActive();
    setTimeout(jumpToActive, 300);
  }
  function navigate(href, push) {
    var u = new URL(href, location.href);
    if (u.origin !== location.origin) { location.href = href; return; }
    fetch(u.pathname + u.search)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (text) {
        var doc = new DOMParser().parseFromString(text, "text/html");
        applyPage(doc);
        if (push) history.pushState({}, "", u.pathname + u.search + u.hash);
        var target = u.hash ? document.getElementById(decodeURIComponent(u.hash.slice(1))) : null;
        if (target) target.scrollIntoView();
        else window.scrollTo(0, 0);
      })
      .catch(function () { location.href = href; });
  }
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
    if (a.origin !== location.origin || !/\.html$/.test(a.pathname)) return;
    if (a.pathname === location.pathname && a.hash) return; // 同页锚点走浏览器默认
    if (a.pathname + a.search === location.pathname + location.search) { e.preventDefault(); return; }
    e.preventDefault();
    navigate(a.href, true);
  });
  window.addEventListener("popstate", function () {
    navigate(location.href, false);
  });

  /* ---------- 启动 ---------- */
  initFolds();
  initLearn();
  initCopy();
  initCodeCards();
  initScrollspy();
})();
"""


# 语法配色：参考 Xcode / Swift Playgrounds 的浅色与深色主题
TOKEN_GROUPS: dict[str, list[str]] = {
    "keyword": [".k", ".kn", ".kr", ".kd", ".kc", ".ow"],
    "function": [".nf", ".fm", ".nb", ".bp"],
    "type": [".nc", ".nn", ".ne"],
    "string": [".s", ".sa", ".sb", ".sc", ".dl", ".sd", ".s1", ".s2", ".se", ".si", ".sh", ".sx", ".sr"],
    "number": [".mi", ".mf", ".mb", ".mh", ".il"],
    "comment": [".c", ".c1", ".ch", ".cm", ".cp", ".cpf", ".cs"],
    "decorator": [".nd"],
}
TOKEN_COLORS: dict[str, tuple[str, str]] = {
    #                浅色        深色
    "keyword": ("#AD3DA4", "#FC5FA3"),
    "function": ("#3E8087", "#67B7A4"),
    "type": ("#3E1E81", "#D0A8FF"),
    "string": ("#C41A16", "#FC6A5D"),
    "number": ("#272AD8", "#D0BF69"),
    "comment": ("#707F8C", "#6C7986"),
    "decorator": ("#78492A", "#BF5AF2"),
}


def pygments_css() -> str:
    """生成代码高亮 CSS：浅色规则在前，深色规则包在 prefers-color-scheme 里。"""
    light_parts: list[str] = []
    dark_parts: list[str] = []
    for group, selectors in TOKEN_GROUPS.items():
        light, dark = TOKEN_COLORS[group]
        sel = ",\n".join(selectors)
        light_parts.append(f"{sel} {{ color: {light}; }}")
        dark_parts.append(f"{sel} {{ color: {dark}; }}")
    # 注释统一斜体
    comment_sel = ",\n".join(TOKEN_GROUPS["comment"])
    light_parts.append(f"{comment_sel} {{ font-style: italic; }}")
    dark_parts.append(f"{comment_sel} {{ font-style: italic; }}")
    return (
        "/* 代码高亮 · Xcode 风格浅/深双主题（由 build_site.py 生成） */\n"
        + "\n".join(light_parts)
        + "\n\n@media (prefers-color-scheme: dark) {\n"
        + "\n".join(dark_parts)
        + "\n}\n"
    )


def build() -> None:
    chapters = load_chapters()
    assert chapters, "未找到任何章节课件"
    sibling_chapters = load_sibling_courses()

    # 把课程元数据回填到 SIBLINGS（侧栏/首页分组标题用）
    for sib in SIBLINGS:
        meta_path = ROOT.parent / sib["dir"] / "课程内容.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                sib["title"] = meta.get("title", sib["key"])
                sib["desc"] = (meta.get("description") or "").strip()
            except (OSError, json.JSONDecodeError):
                pass

    # 统一页面序列：Python 32 章 → 项目案例 → 三门同级课程
    entries: list[dict] = []
    for ch in chapters:
        ch["sec_meta"] = h2_meta(convert_md(ch["md"])[1])
        entries.append(
            {
                "course": "py",
                "num": ch["n"],
                "data_ch": str(ch["n"]),
                "title": ch["title"],
                "url": ch["url"],
                "is_project": False,
                "sections": sum(1 for _ in re.finditer(r"^##\s+", ch["md"], re.M)),
                "sec_meta": ch["sec_meta"],
            }
        )
    for proj in PROJECTS:
        text = proj["path"].read_text(encoding="utf-8")
        proj_secs = h2_meta(convert_md(strip_leading_h1(text))[1])
        entries.append(
            {
                "course": "py",
                "num": None,
                "title": proj["title"],
                "sub": proj["sub"],
                "url": f"proj/{proj['key']}.html",
                "is_project": True,
                "sections": sum(1 for _ in re.finditer(r"^##\s+", text, re.M)),
                "sec_meta": proj_secs,
            }
        )
    layout_of = {s["key"]: s.get("layout", "standard") for s in SIBLINGS}
    for ch in sibling_chapters:
        asset_dir = ch["src"].parent / "assets"
        if layout_of[ch["course"]] == "flat":
            prefix = "assets" if asset_dir.is_dir() else None
        else:
            prefix = f"assets/ch{ch['n']:02d}" if asset_dir.is_dir() else None
        ch["asset_refs"] = asset_refs_in_text(ch["src"].read_text(encoding="utf-8"))
        if ch["kind"] == "ipynb":
            html, toc = convert_ipynb(ch["src"], prefix)
            ch["html"], ch["toc"] = html, toc
            sections = sum(1 for t in flatten_toc(toc) if t["level"] == 2)
            ch["sec_meta"] = h2_meta(toc)
        else:
            ch["md"] = ch["src"].read_text(encoding="utf-8")
            if prefix:
                ch["md"] = rewrite_local_assets(ch["md"], prefix)
            sections = sum(1 for _ in re.finditer(r"^##\s+", ch["md"], re.M))
            ch["sec_meta"] = h2_meta(convert_md(ch["md"], runnable=False)[1])
        ch["url"] = f"{ch['course']}/ch{ch['n']:02d}.html"
        ch["data_ch"] = f"{ch['course']}-{ch['n']}"
        ch["kicker_mod"] = ch["course_title"]
        ch["runnable"] = False
        ch["desc"] = next(
            (s.get("desc", "") for s in SIBLINGS if s["key"] == ch["course"]), ""
        )
        entries.append(
            {
                "course": ch["course"],
                "num": ch["n"],
                "data_ch": ch["data_ch"],
                "title": ch["title"],
                "url": ch["url"],
                "is_project": False,
                "sections": sections,
                "sec_meta": ch["sec_meta"],
            }
        )

    # 输出目录
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "ch").mkdir(exist_ok=True)
    (OUT / "proj").mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("")  # 跳过 GitHub Pages 的 Jekyll 处理
    for sib in SIBLINGS:
        if any(e.get("course") == sib["key"] for e in entries):
            (OUT / sib["key"]).mkdir(exist_ok=True)

    # 首页
    (OUT / "index.html").write_text(index_page(entries), encoding="utf-8")

    # 章节页（前后翻页贯穿全部课程与项目）
    for i, e in enumerate(entries):
        prev_e = entries[i - 1] if i > 0 else None
        next_e = entries[i + 1] if i < len(entries) - 1 else None
        if e["is_project"]:
            proj = next(p for p in PROJECTS if p["title"] == e["title"])
            (OUT / "proj" / f"{proj['key']}.html").write_text(
                project_page(proj, entries, prev_e, next_e), encoding="utf-8"
            )
        else:
            if e["course"] == "py":
                ch = next(c for c in chapters if c["n"] == e["num"])
            else:
                ch = next(
                    c
                    for c in sibling_chapters
                    if c["course"] == e["course"] and c["n"] == e["num"]
                )
            (OUT / e["url"]).write_text(
                chapter_page(ch, entries, prev_e, next_e), encoding="utf-8"
            )

    # 拷贝课件引用的本地图片资源：共享目录只拷一份，且只拷被引用的文件
    for sib in SIBLINGS:
        key = sib["key"]
        course_chs = [c for c in sibling_chapters if c["course"] == key]
        if not course_chs:
            continue
        assets_root = OUT / key / "assets"
        if assets_root.exists():
            shutil.rmtree(assets_root)
        refs = set()
        for c in course_chs:
            refs |= c.get("asset_refs") or set()
        if not refs:
            continue
        if sib.get("layout") == "flat":
            shared = course_chs[0]["src"].parent / "assets"
            copy_referenced_files(shared, assets_root, refs)
        else:
            for ch in course_chs:
                if ch.get("asset_refs"):
                    copy_referenced_files(
                        ch["src"].parent / "assets",
                        assets_root / f"ch{ch['n']:02d}",
                        ch["asset_refs"],
                    )

    # 静态资源
    (OUT / "assets" / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (OUT / "assets" / "app.js").write_text(APP_JS, encoding="utf-8")
    (OUT / "assets" / "pygments.css").write_text(pygments_css(), encoding="utf-8")

    # 内置 Python 运行时（vendor/pyodide → site/assets/pyodide）
    vendor = ROOT / "vendor" / "pyodide"
    if vendor.exists():
        shutil.copytree(vendor, OUT / "assets" / "pyodide", dirs_exist_ok=True)

    # 搜索索引
    index: list[dict] = []
    for ch in chapters:
        h2_tokens = [t for t in flatten_toc(convert_md(ch["md"])[1]) if t["level"] == 2]
        secs = section_bodies(ch["md"])
        index.append(
            {
                "n": ch["n"],
                "title": f"第{ch['n']}章 {ch['title']}",
                "module": COURSE_TITLE,
                "url": f"ch/ch{ch['n']:02d}.html",
                "sections": [
                    {
                        "name": s["name"],
                        "body": s["body"],
                        "anchor": h2_tokens[i]["id"] if i < len(h2_tokens) else None,
                    }
                    for i, s in enumerate(secs)
                ],
            }
        )
    for proj in PROJECTS:
        text = proj["path"].read_text(encoding="utf-8")
        secs = section_bodies(text)
        index.append(
            {
                "n": None,
                "title": proj["title"],
                "module": "项目案例",
                "url": f"proj/{proj['key']}.html",
                "sections": [
                    {"name": s["name"], "body": s["body"], "anchor": None} for s in secs
                ],
            }
        )
    for ch in sibling_chapters:
        if ch["kind"] == "ipynb":
            nb = json.loads(ch["src"].read_text(encoding="utf-8"))
            pseudo = "\n\n".join(
                "".join(c.get("source", []))
                for c in nb.get("cells", [])
                if c.get("cell_type") == "markdown"
            )
            secs = section_bodies(pseudo)
            anchors: list[str | None] = [None] * len(secs)
        else:
            secs = section_bodies(ch["md"])
            h2s = [
                t
                for t in flatten_toc(convert_md(ch["md"], runnable=False)[1])
                if t["level"] == 2
            ]
            anchors = [h2s[i]["id"] if i < len(h2s) else None for i in range(len(secs))]
        index.append(
            {
                "n": ch["n"],
                "title": f"第{ch['n']}章 {ch['title']}",
                "module": ch["course_title"],
                "url": ch["url"],
                "sections": [
                    {"name": s["name"], "body": s["body"], "anchor": a}
                    for s, a in zip(secs, anchors)
                ],
            }
        )
    (OUT / "assets" / "search.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )

    # 同步一份到 /tmp，供桌面应用内置预览使用
    # （应用拉起的预览进程受 macOS TCC 限制，读取不到 Desktop 下的文件；
    #   先写临时目录再改名，避免预览请求撞上目录被清空的瞬间）
    try:
        mirror = Path("/tmp/py-course-site")
        staging = Path("/tmp/py-course-site.new")
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(OUT, staging)
        if mirror.exists():
            shutil.rmtree(mirror)
        staging.rename(mirror)
        # 预览服务器脚本也放一份到 /tmp（应用进程读不到 Desktop）
        shutil.copy2(ROOT / "serve_site.py", "/tmp/serve_site.py")
    except OSError:
        pass

    n_sib = sum(1 for e in entries if e.get("course") not in (None, "py"))
    print(
        f"完成：Python {len(chapters)} 章 + {len(PROJECTS)} 个项目案例 + "
        f"同级课程 {n_sib} 章 → {OUT}"
    )


if __name__ == "__main__":
    build()
