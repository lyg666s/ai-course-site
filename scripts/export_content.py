# -*- coding: utf-8 -*-
"""把课件内容导出为 Next.js 站点使用的数据文件。

复用 build_site.py 的解析管线（Markdown / Jupyter Notebook → 预渲染 HTML）。
产出：
  web/content/index.json   课程清单（方向 → 课程 → 章节元信息，无正文）
  web/content/{key}.json   各课程章节正文（预渲染 HTML）
  web/public/search.json   全站搜索索引
  web/public/{key}/assets/ 课件引用的本地图片资源
  web/public/pyodide/      浏览器 Python 运行时

用法：/usr/bin/python3 scripts/export_content.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_site as bs

WEB: Path = bs.ROOT / "web"
CONTENT: Path = WEB / "content"
PUBLIC: Path = WEB / "public"

BASE: str = "/ai-course-site"  # GitHub Pages 子路径

# 两大方向（IA）：Agent 类课程独立成一级入口，与开发基础类隔离
FAMILIES: list[dict] = [
    {"key": "agent", "name": "AI · Agent 开发", "courses": ["ac", "lg", "da"]},
    {
        "key": "dev",
        "name": "编程与工程基础",
        "courses": ["py", "fw", "db", "dst", "java", "cloud"],
    },
]

# 占位课程（内容未更新，先建分类空位）
COMING_SOON: dict[str, dict] = {
    "java": {
        "title": "Java",
        "desc": "Java 语言与 Web 开发课程，内容更新中，敬请期待。",
        "glyph": "J",
        "cls": "b-java",
    },
    "cloud": {
        "title": "云计算",
        "desc": "云计算与运维课程，内容更新中，敬请期待。",
        "glyph": "云",
        "cls": "b-cloud",
    },
}


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------

def asset_prefix_for(ch: dict, layout: str) -> str | None:
    """课件本地资源在站点上的绝对前缀；无资源目录时返回 None。"""
    if not (ch["src"].parent / "assets").is_dir():
        return None
    if layout == "flat":
        return f"{BASE}/{ch['course']}/assets"
    return f"{BASE}/{ch['course']}/assets/ch{ch['n']:02d}"


def build_chapter(
    n: int | None,
    slug: str,
    title: str,
    group: str,
    kicker_mod: str,
    html: str,
    toc_tokens: list[dict],
    search_secs: list[dict],
    progress_key: str,
) -> dict:
    return {
        "n": n,
        "slug": slug,
        "title": title,
        "group": group,
        "kicker_mod": kicker_mod,
        "sec_meta": bs.h2_meta(toc_tokens),
        "html": html,
        "search_secs": search_secs,
        "progress_key": progress_key,
    }


def search_secs_for_md(md: str) -> list[dict]:
    return [{"name": s["name"], "body": s["body"]} for s in bs.section_bodies(md)]


def ipynb_markdown_text(path: Path) -> str:
    """取 notebook 的全部 markdown 单元文本（搜索索引用）。"""
    nb = json.loads(path.read_text(encoding="utf-8"))
    return "\n\n".join(
        "".join(c.get("source", []))
        for c in nb.get("cells", [])
        if c.get("cell_type") == "markdown"
    )


def course_summary(course: dict) -> dict:
    """课程卡片 / 侧栏需要的元信息（不含正文）。"""
    return {
        "key": course["key"],
        "title": course["title"],
        "desc": course.get("desc", "") or "",
        "glyph": course["glyph"],
        "cls": course["cls"],
        "coming_soon": bool(course.get("coming_soon")),
        "chapter_count": sum(len(m["chapters"]) for m in course["modules"]),
        "section_count": sum(
            len(c["sec_meta"]) for m in course["modules"] for c in m["chapters"]
        ),
        "modules": [
            {"name": m["name"], "chapters": [
                {
                    "n": c["n"],
                    "slug": c["slug"],
                    "title": c["title"],
                    "group": c["group"],
                    "progress_key": c["progress_key"],
                }
                for c in m["chapters"]
            ]}
            for m in course["modules"]
        ],
    }


def copy_assets(sibling_chapters: list[dict], layouts: dict[str, str]) -> None:
    """拷贝课件引用的本地图片资源到 web/public/{key}/assets/。"""
    for sib in bs.SIBLINGS:
        key = sib["key"]
        course_chs = [c for c in sibling_chapters if c["course"] == key]
        if not course_chs:
            continue
        assets_root = PUBLIC / key / "assets"
        if assets_root.exists():
            shutil.rmtree(assets_root)
        refs: set[str] = set()
        for c in course_chs:
            refs |= c.get("asset_refs") or set()
        if not refs:
            continue
        if layouts.get(key) == "flat":
            shared = course_chs[0]["src"].parent / "assets"
            bs.copy_referenced_files(shared, assets_root, refs)
        else:
            for ch in course_chs:
                if ch.get("asset_refs"):
                    bs.copy_referenced_files(
                        ch["src"].parent / "assets",
                        assets_root / f"ch{ch['n']:02d}",
                        ch["asset_refs"],
                    )


def copy_pyodide() -> None:
    vendor = bs.ROOT / "vendor" / "pyodide"
    if vendor.exists():
        shutil.copytree(vendor, PUBLIC / "pyodide", dirs_exist_ok=True)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def main() -> None:
    py_chapters = bs.load_chapters()
    sibling_chapters = bs.load_sibling_courses()
    layouts = {s["key"]: s.get("layout", "standard") for s in bs.SIBLINGS}

    # 回填同级课程的标题/描述
    for sib in bs.SIBLINGS:
        meta_path = bs.ROOT.parent / sib["dir"] / "课程内容.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                sib["title"] = meta.get("title", sib["key"])
                sib["desc"] = (meta.get("description") or "").strip()
            except (OSError, json.JSONDecodeError):
                pass

    courses: dict[str, dict] = {}

    # ---- Python 语言核心精讲（模块 + 项目案例）----
    py_modules: list[dict] = []
    for mod_name, nums, _glyph, _cls in bs.MODULES:
        chs = []
        for ch in py_chapters:
            if ch["n"] not in nums:
                continue
            html, toc = bs.convert_md(bs.strip_leading_h1(ch["md"]))
            chs.append(
                build_chapter(
                    n=ch["n"],
                    slug=str(ch["n"]),
                    title=ch["title"],
                    group=mod_name,
                    kicker_mod=bs.module_of(ch["n"]),
                    html=html,
                    toc_tokens=toc,
                    search_secs=search_secs_for_md(ch["md"]),
                    progress_key=str(ch["n"]),
                )
            )
        py_modules.append({"name": mod_name, "chapters": chs})
    proj_chs: list[dict] = []
    for proj in bs.PROJECTS:
        text = proj["path"].read_text(encoding="utf-8")
        html, toc = bs.convert_md(bs.strip_leading_h1(text))
        proj_chs.append(
            build_chapter(
                n=None,
                slug=f"proj-{proj['key']}",
                title=proj["title"],
                group="项目案例",
                kicker_mod="项目案例",
                html=html,
                toc_tokens=toc,
                search_secs=search_secs_for_md(text),
                progress_key="",  # 项目页不参与进度
            )
        )
    py_modules.append({"name": "项目案例", "chapters": proj_chs})
    courses["py"] = {
        "key": "py",
        "title": bs.COURSE_TITLE,
        "desc": bs.COURSE_DESC,
        "glyph": "Py",
        "cls": "b1",
        "modules": py_modules,
    }

    # ---- 同级课程 ----
    for sib in bs.SIBLINGS:
        chs = [c for c in sibling_chapters if c["course"] == sib["key"]]
        if not chs:
            continue
        layout = layouts.get(sib["key"], "standard")
        modules: dict[str, list[dict]] = {}
        for ch in chs:
            prefix = asset_prefix_for(ch, layout)
            ch["asset_refs"] = bs.asset_refs_in_text(ch["src"].read_text(encoding="utf-8"))
            if ch["kind"] == "ipynb":
                html, toc = bs.convert_ipynb(ch["src"], prefix)
                search_secs = search_secs_for_md(ipynb_markdown_text(ch["src"]))
            else:
                md = ch["src"].read_text(encoding="utf-8")
                if prefix:
                    md = bs.rewrite_local_assets(md, prefix)
                html, toc = bs.convert_md(md, runnable=False)
                search_secs = search_secs_for_md(md)
            module_name = ch["title"].split(" - ")[0] if sib["key"] == "dst" and " - " in ch["title"] else None
            if sib["key"] == "fw" and ch["title"].startswith("部署"):
                module_name = "部署"
            if module_name is None:
                module_name = "课程内容"
            modules.setdefault(module_name, []).append(
                build_chapter(
                    n=ch["n"],
                    slug=str(ch["n"]),
                    title=ch["title"],
                    group=module_name,
                    kicker_mod=sib["title"],
                    html=html,
                    toc_tokens=toc,
                    search_secs=search_secs,
                    progress_key=f"{sib['key']}-{ch['n']}",
                )
            )
        courses[sib["key"]] = {
            "key": sib["key"],
            "title": sib["title"],
            "desc": sib.get("desc", ""),
            "glyph": sib["glyph"],
            "cls": sib["cls"],
            "modules": [{"name": name, "chapters": items} for name, items in modules.items()],
        }

    # ---- 占位课程（Java / 云计算）----
    for key, meta in COMING_SOON.items():
        courses[key] = {
            "key": key,
            "title": meta["title"],
            "desc": meta["desc"],
            "glyph": meta["glyph"],
            "cls": meta["cls"],
            "coming_soon": True,
            "modules": [],
        }

    # ---- index.json（方向 → 课程 → 章节元信息）----
    families: list[dict] = []
    for fam in FAMILIES:
        fam_courses = [course_summary(courses[k]) for k in fam["courses"] if k in courses]
        families.append({"key": fam["key"], "name": fam["name"], "courses": fam_courses})
    CONTENT.mkdir(parents=True, exist_ok=True)
    (CONTENT / "index.json").write_text(
        json.dumps({"families": families}, ensure_ascii=False), encoding="utf-8"
    )

    # ---- {key}.json（章节正文）----
    for key, course in courses.items():
        (CONTENT / f"{key}.json").write_text(
            json.dumps(course, ensure_ascii=False), encoding="utf-8"
        )

    # ---- search.json ----
    search: list[dict] = []
    for key, course in courses.items():
        if course.get("coming_soon"):
            continue
        for mod in course["modules"]:
            for ch in mod["chapters"]:
                url = f"{BASE}/course/{key}/{ch['slug']}/"
                title = f"第{ch['n']}章 {ch['title']}" if ch["n"] is not None else ch["title"]
                search.append(
                    {
                        "n": ch["n"],
                        "title": title,
                        "module": course["title"],
                        "url": url,
                        "sections": [
                            {
                                "name": s["name"],
                                "body": s["body"],
                                "anchor": (
                                    ch["sec_meta"][i]["anchor"]
                                    if i < len(ch["sec_meta"])
                                    else None
                                ),
                            }
                            for i, s in enumerate(ch["search_secs"])
                        ],
                    }
                )
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "search.json").write_text(
        json.dumps(search, ensure_ascii=False), encoding="utf-8"
    )

    # ---- 本地资源 + Pyodide ----
    copy_assets(sibling_chapters, layouts)
    copy_pyodide()

    total = sum(
        len(m["chapters"])
        for c in courses.values()
        if not c.get("coming_soon")
        for m in c["modules"]
    )
    print(f"内容导出完成：{len(courses)} 门课程，{total} 章 → {CONTENT}")


if __name__ == "__main__":
    main()
