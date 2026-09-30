import { allFamilies, courseOf, loadCourse } from "@/lib/data";
import { notFound } from "next/navigation";
import CourseCTA from "@/components/CourseCTA";
import CourseChapterList from "@/components/CourseChapterList";
import type { CourseSummary } from "@/lib/data";

export function generateStaticParams() {
  const params: { key: string }[] = [];
  for (const f of allFamilies()) for (const c of f.courses) params.push({ key: c.key });
  return params;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const course = courseOf(key);
  return { title: course ? `${course.title} · AI大全栈` : "课程 · AI大全栈" };
}

export default async function CoursePage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const meta = courseOf(key);
  if (!meta) notFound();

  if (meta.coming_soon) {
    return (
      <main className="mx-auto max-w-[52rem] px-4 pb-20 pt-10 sm:px-6">
        <div className="course-card items-start !p-8">
          <div className="flex items-center gap-3">
            <span className={`badge ${meta.cls}`} aria-hidden>
              {meta.glyph}
            </span>
            <h1 className="m-0 text-2xl font-bold tracking-tight text-label">{meta.title}</h1>
            <span className="coming-pill">即将上线</span>
          </div>
          <p className="m-0 text-label2">{meta.desc}</p>
          <p className="m-0 text-sm text-label3">
            课件整理中 —— 上线后这里会显示完整的章节目录与学习进度。
          </p>
        </div>
      </main>
    );
  }

  const data = await loadCourse(key);
  const summary = meta as CourseSummary;
  const chapters = data.modules.flatMap((m) => m.chapters);

  return (
    <main className="mx-auto max-w-[52rem] px-4 pb-20 pt-10 sm:px-6">
      <header className="mb-8 flex flex-wrap items-center gap-3">
        <span className={`badge ${data.cls}`} aria-hidden>
          {data.glyph}
        </span>
        <h1 className="m-0 text-[28px] font-bold tracking-tight text-label">{data.title}</h1>
      </header>
      <p className="mt-0 max-w-[42em] text-[15px] leading-relaxed text-label2">{data.desc}</p>
      <div className="mb-6 flex items-center gap-3 text-[13px] text-label3">
        <span>{chapters.length} 章</span>
        <span>·</span>
        <span>{summary.section_count} 节</span>
      </div>
      <div className="mb-8">
        <CourseCTA course={meta} />
      </div>

      <CourseChapterList
        courseKey={key}
        modules={data.modules.map((m) => ({
          name: m.name,
          chapters: m.chapters.map((c) => ({
            slug: c.slug,
            n: c.n,
            title: c.title,
            group: c.group,
            progress_key: c.progress_key,
          })),
        }))}
      />
    </main>
  );
}
