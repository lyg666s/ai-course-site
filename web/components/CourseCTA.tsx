"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDone } from "@/lib/progress";
import { chapterPath } from "@/lib/data";
import type { CourseSummary } from "@/lib/data";

// 课程详情页的「开始学习 / 继续学习」按钮：定位到第一个未完成的章节
export default function CourseCTA({ course }: { course: CourseSummary }) {
  const [target, setTarget] = useState<{ url: string; label: string } | null>(null);
  useEffect(() => {
    const done = getDone();
    const chapters = course.modules.flatMap((m) => m.chapters);
    const next =
      chapters.find((c) => c.progress_key && !done[c.progress_key]) ?? chapters[chapters.length - 1];
    if (next) {
      setTarget({
        url: chapterPath(course.key, next.slug),
        label: done[next.progress_key ?? ""] ? "重新学习：第一章" : "继续学习",
      });
    }
  }, [course]);

  if (!target) return null;
  return (
    <Link href={target.url} className="btn-primary no-underline">
      {target.label}
    </Link>
  );
}
