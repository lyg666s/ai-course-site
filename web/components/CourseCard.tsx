"use client";

import Link from "next/link";
import type { CourseSummary } from "@/lib/data";

export default function CourseCard({ course }: { course: CourseSummary }) {
  const coming = course.coming_soon;
  return (
    <Link
      href={`/course/${course.key}/`}
      className={`course-card ${coming ? "coming pointer-events-none" : ""}`}
    >
      <div className="flex items-center gap-2.5">
        <span className={`badge ${course.cls}`} aria-hidden>
          {course.glyph}
        </span>
        <h3 className="m-0 text-[16.5px] font-bold tracking-tight text-label">{course.title}</h3>
      </div>
      <p className="m-0 line-clamp-2 min-h-[3.2em] text-[13.5px] leading-relaxed text-label2">
        {course.desc || "章节目录建设中。"}
      </p>
      <div className="mt-1 flex items-center gap-2 text-xs text-label3">
        <span>{course.chapter_count} 章</span>
        <span>·</span>
        <span>{course.section_count} 节</span>
        {coming && <span className="coming-pill ml-auto">即将上线</span>}
      </div>
    </Link>
  );
}
