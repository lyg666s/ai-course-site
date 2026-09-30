import Link from "next/link";
import { allFamilies, courseOf, familyOf, loadCourse } from "@/lib/data";
import { notFound } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import ChapterContent from "@/components/ChapterContent";
import LearnToggle from "@/components/LearnToggle";
import LastReadTracker from "@/components/LastReadTracker";
import Toc from "@/components/Toc";
import type { CourseLite } from "@/components/Sidebar";

export async function generateStaticParams() {
  const params: { key: string; ch: string }[] = [];
  for (const f of allFamilies()) {
    for (const c of f.courses) {
      if (c.coming_soon) continue;
      for (const m of c.modules) {
        for (const ch of m.chapters) params.push({ key: c.key, ch: ch.slug });
      }
    }
  }
  return params;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ key: string; ch: string }>;
}) {
  const { key, ch } = await params;
  const meta = courseOf(key);
  const num = /^\d+$/.test(ch) ? parseInt(ch, 10) : null;
  return {
    title: meta
      ? `${num !== null ? `第 ${num} 章 ` : ""} · ${meta.title} · AI大全栈`
      : "AI大全栈",
  };
}

export default async function ChapterPage({
  params,
}: {
  params: Promise<{ key: string; ch: string }>;
}) {
  const { key, ch: slug } = await params;
  const meta = courseOf(key);
  if (!meta) notFound();
  const data = await loadCourse(key);

  const flat = data.modules.flatMap((m) =>
    m.chapters.map((c) => ({ ...c, module: m.name }))
  );
  const idx = flat.findIndex((c) => c.slug === slug);
  if (idx < 0) notFound();
  const cur = flat[idx];
  const prev = idx > 0 ? flat[idx - 1] : null;
  const next = idx < flat.length - 1 ? flat[idx + 1] : null;

  const family = familyOf(key);
  const sidebarCourses: CourseLite[] = family.courses.map((c) => {
    const base = {
      key: c.key,
      title: c.title,
      glyph: c.glyph,
      cls: c.cls,
      coming_soon: c.coming_soon,
    };
    if (c.key === key) {
      return {
        ...base,
        modules: data.modules.map((m) => ({
          name: m.name,
          chapters: m.chapters.map((cc) => ({
            n: cc.n,
            slug: cc.slug,
            title: cc.title,
            group: cc.group,
            progress_key: cc.progress_key,
            sections: cc.sec_meta,
          })),
        })),
      };
    }
    return { ...base, modules: c.modules };
  });

  return (
    <>
      <LastReadTracker
        url={`/course/${key}/${slug}/`}
        title={cur.title}
        course={data.title}
      />
      <div className="doc-wrap">
        <Sidebar courses={sidebarCourses} currentKey={key} currentSlug={slug} />
        <article className="doc" id="content">
          <div className="doc-head-row mb-2 flex items-center justify-between gap-4">
            <p className="kicker">
              <span className="kicker-num">
                {cur.n !== null ? `第 ${cur.n} 章` : "章节"}
              </span>
              <span className="kicker-mod">{cur.kicker_mod}</span>
            </p>
            {cur.progress_key && <LearnToggle progressKey={cur.progress_key} />}
          </div>
          <h1 className="doc-h1">{cur.title}</h1>
          <ChapterContent html={cur.html} />
          <nav className="pager" aria-label="章节导航">
            {prev ? (
              <Link
                className="pager-link pager-prev"
                href={`/course/${key}/${prev.slug}/`}
              >
                <span className="pager-dir">上一章</span>
                <span className="pager-name">{prev.title}</span>
              </Link>
            ) : (
              <span className="flex-1" />
            )}
            {next ? (
              <Link
                className="pager-link pager-next"
                href={`/course/${key}/${next.slug}/`}
              >
                <span className="pager-dir">下一章</span>
                <span className="pager-name">{next.title}</span>
              </Link>
            ) : (
              <Link className="pager-link pager-next" href={`/course/${key}/`}>
                <span className="pager-dir">课程完</span>
                <span className="pager-name">返回课程目录</span>
              </Link>
            )}
          </nav>
        </article>
        <Toc sections={cur.sec_meta} />
      </div>
    </>
  );
}
