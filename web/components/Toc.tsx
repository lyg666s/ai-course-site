"use client";

import { useEffect, useRef, useState } from "react";
import type { SecMeta } from "@/lib/data";

export default function Toc({ sections }: { sections: SecMeta[] }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const spyRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const links = Array.from(document.querySelectorAll<HTMLAnchorElement>(".toc-list a"));
    if (!links.length || !("IntersectionObserver" in window)) return;
    const byId: Record<string, HTMLAnchorElement> = {};
    links.forEach((a) => (byId[a.getAttribute("href")!.slice(1)] = a));
    const headings = Object.keys(byId)
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];
    let active: HTMLAnchorElement | null = null;
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            if (active) active.classList.remove("active");
            active = byId[en.target.id];
            active.classList.add("active");
            setActiveId(en.target.id);
          }
        });
      },
      { rootMargin: "-10% 0px -75% 0px", threshold: 0 }
    );
    headings.forEach((h) => spy.observe(h));
    spyRef.current = spy;
    return () => spy.disconnect();
  }, [sections]);

  if (!sections.length) return null;
  return (
    <aside className="toc">
      <p className="toc-title">本页目录</p>
      <ol className="toc-list">
        {sections.map((s) => (
          <li key={s.anchor ?? s.name}>
            <a
              href={`#${s.anchor ?? ""}`}
              className={activeId && s.anchor === activeId ? "active" : ""}
            >
              {s.name}
            </a>
          </li>
        ))}
      </ol>
    </aside>
  );
}
