"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

type Tab = { key: string; name: string };

type SearchEntry = {
  n: number | null;
  title: string;
  module: string;
  url: string;
  sections: { name: string; body: string; anchor: string | null }[];
};

const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

function esc(s: string) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
}

export default function TopNav({ families }: { families: Tab[] }) {
  const pathname = usePathname();
  const [dark, setDark] = useState(false);
  const [q, setQ] = useState("");
  const [index, setIndex] = useState<SearchEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setQ("");
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // 搜索索引懒加载
  useEffect(() => {
    if (index || failed) return;
    const t = setTimeout(() => {
      fetch(`${BASE}/search.json`)
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then((d) => setIndex(d as SearchEntry[]))
        .catch(() => setFailed(true));
    }, 400);
    return () => clearTimeout(t);
  }, [index, failed]);

  // 输入框失焦后延迟收起结果面板（留给点击跳转时间）
  const [focused, setFocused] = useState(false);
  const results = q.trim()
    ? index
      ? doSearch(index, q.trim())
      : []
    : null;

  function toggleTheme() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
    setDark(next);
  }

  const isHome = pathname === "/" || pathname === `${BASE}/`;

  return (
    <header className="topnav">
      <div className="mx-auto flex h-14 max-w-[80rem] items-center gap-3 px-4">
        <button
          type="button"
          className="burger-btn rounded-lg border border-sep-soft bg-fill2 px-2.5 py-1.5 text-sm leading-none text-label2"
          aria-label="打开课程目录"
          onClick={() => document.body.classList.toggle("nav-open")}
        >
          ☰
        </button>
        <Link
          href="/"
          className="font-bold tracking-tight text-[17px] text-label no-underline hover:no-underline"
        >
          AI大全栈
          <span className="ml-2 hidden text-xs font-medium text-label2 sm:inline">课程手册</span>
        </Link>

        <nav className="tabs ml-2 flex items-center gap-1" aria-label="方向">
          {!isHome && (
            <Link
              href="/"
              className={`rounded-lg px-3 py-1.5 text-[13.5px] no-underline hover:bg-fill2 ${
                isHome ? "bg-blue-tint font-semibold text-blue" : "text-label2"
              }`}
            >
              首页
            </Link>
          )}
          {families.map((f) => {
            const active = pathname.startsWith(`${BASE}/${f.key}/`) || pathname === `${BASE}/${f.key}`;
            return (
              <Link
                key={f.key}
                href={`/${f.key}/`}
                className={`rounded-lg px-3 py-1.5 text-[13.5px] no-underline hover:bg-fill2 ${
                  active ? "bg-blue-tint font-semibold text-blue" : "text-label2"
                }`}
              >
                {f.name}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <div className="search w-44 md:w-64" ref={boxRef}>
            <input
              ref={inputRef}
              type="search"
              placeholder="搜索课件内容"
              aria-label="搜索课件内容"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 150)}
            />
            {focused && q.trim() && (
              <div className="search-panel" id="search-panel">
                {index === null && !failed && <p className="search-empty">索引加载中…</p>}
                {failed && (
                  <p className="search-empty">搜索索引不可用，请刷新页面重试</p>
                )}
                {index !== null && results!.length === 0 && (
                  <p className="search-empty">没有找到「{esc(q)}」相关内容</p>
                )}
                {index !== null &&
                  results!.map((r) => (
                    <div key={r.url}>
                      {r.sections.map((s, i) => (
                        <Link
                          key={i}
                          href={r.url + (s.anchor ? `#${s.anchor}` : "")}
                          className="search-item block"
                          onClick={() => {
                            setQ("");
                            inputRef.current?.blur();
                          }}
                        >
                          <span className="search-item-title">
                            <span className="s-num">
                              {r.n ? String(r.n).padStart(2, "0") : "◈"}
                            </span>
                            {esc(r.title)}
                          </span>
                          <span className="search-item-sec">{esc(s.name)}</span>
                          <span className="search-item-sec">{snippet(s.body, q.trim())}</span>
                        </Link>
                      ))}
                    </div>
                  ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label="切换深色模式"
            className="rounded-lg border border-sep-soft bg-fill2 px-2.5 py-1.5 text-sm leading-none text-label2 hover:text-label"
          >
            {dark ? "☀︎" : "☾"}
          </button>
        </div>
      </div>
    </header>
  );
}

function doSearch(index: SearchEntry[], q: string): { url: string; n: number | null; title: string; sections: { name: string; body: string; anchor: string | null }[] }[] {
  const ql = q.toLowerCase();
  const out: { url: string; n: number | null; title: string; sections: SearchEntry["sections"] }[] = [];
  for (const ch of index) {
    const hits: SearchEntry["sections"] = [];
    if (ch.title.toLowerCase().includes(ql)) {
      hits.push({ name: null as unknown as string, body: "", anchor: null });
    }
    for (const s of ch.sections) {
      if (s.name.toLowerCase().includes(ql) || (s.body && s.body.toLowerCase().includes(ql))) {
        hits.push(s);
      }
      if (hits.length >= 3) break;
    }
    if (hits.length) out.push({ url: ch.url, n: ch.n, title: ch.title, sections: hits.slice(0, 3) });
  }
  return out.slice(0, 10);
}

function snippet(text: string, q: string): string {
  if (!text) return "";
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return esc(text.slice(0, 60));
  const start = Math.max(0, i - 18);
  const frag = text.slice(start, i + q.length + 42);
  const marked = esc(frag).replace(
    new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
    (m) => `<mark>${m}</mark>`
  );
  return (start > 0 ? "…" : "") + marked;
}
