"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getDone } from "@/lib/progress";

type Mod = {
  name: string;
  chapters: { slug: string; n: number | null; title: string; group: string; progress_key: string }[];
};

export default function CourseChapterList({
  courseKey,
  modules,
}: {
  courseKey: string;
  modules: Mod[];
}) {
  const [done, setDone] = useState<Record<string, true>>({});
  useEffect(() => {
    const update = () => setDone(getDone());
    update();
    window.addEventListener("pycourse-progress", update);
    return () => window.removeEventListener("pycourse-progress", update);
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {modules.map((m, i) => (
        <section key={i}>
          <h2 className="mb-2 px-1 text-[15px] font-semibold text-label2">{m.name}</h2>
          <div className="overflow-hidden rounded-2xl bg-card">
            {m.chapters.map((c) => (
              <Link
                key={c.slug}
                href={`/course/${courseKey}/${c.slug}/`}
                className="flex items-center gap-3 border-b-[0.5px] border-sep-soft px-4 py-3 text-[15px] text-label no-underline last:border-0 hover:bg-fill2"
              >
                <span className="w-6 flex-none text-center font-mono text-xs text-label3">
                  {c.n !== null ? String(c.n).padStart(2, "0") : "◈"}
                </span>
                <span className="min-w-0 flex-1 font-medium">
                  {c.title}
                  {done[c.progress_key] && (
                    <span className="ml-1.5 text-[13px] font-bold text-[var(--green-ink)]">✓</span>
                  )}
                </span>
                <span className="flex-none text-label3" aria-hidden>
                  ›
                </span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
