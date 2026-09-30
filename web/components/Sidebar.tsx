"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { getDone, type DoneMap } from "@/lib/progress";

export type ChMeta = {
  n: number | null;
  slug: string;
  title: string;
  group: string;
  progress_key: string;
  sections?: { name: string; anchor: string | null }[];
};

export type CourseLite = {
  key: string;
  title: string;
  glyph: string;
  cls: string;
  coming_soon: boolean;
  modules: { name: string; chapters: ChMeta[] }[];
};

export default function Sidebar({
  courses,
  currentKey,
  currentSlug,
}: {
  courses: CourseLite[];
  currentKey: string;
  currentSlug: string | null;
}) {
  const [done, setDone] = useState<DoneMap>({});
  const [open, setOpen] = useState<Set<string>>(() => {
    const init = new Set<string>();
    if (currentKey) {
      init.add(`c-${currentKey}`);
      const course = courses.find((c) => c.key === currentKey);
      if (course && currentSlug) {
        init.add(`ch-${currentKey}-${currentSlug}`);
        for (const m of course.modules) {
          if (m.chapters.some((c) => c.slug === currentSlug)) {
            init.add(`m-${currentKey}-${m.name}`);
            break;
          }
        }
      }
    }
    return init;
  });

  useEffect(() => {
    document.body.classList.add("has-sidebar");
    const update = () => setDone(getDone());
    update();
    window.addEventListener("pycourse-progress", update);
    return () => {
      document.body.classList.remove("has-sidebar");
      window.removeEventListener("pycourse-progress", update);
    };
  }, []);

  // 跳转后自动收起移动端抽屉
  const pathname = usePathname();
  useEffect(() => {
    document.body.classList.remove("nav-open");
  }, [pathname]);

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const total = courses.reduce(
    (acc, c) => acc + c.modules.reduce((a, m) => a + m.chapters.filter((ch) => ch.progress_key).length, 0),
    0
  );
  const count = courses.reduce(
    (acc, c) =>
      acc +
      c.modules.reduce(
        (a, m) => a + m.chapters.filter((ch) => ch.progress_key && done[ch.progress_key]).length,
        0
      ),
    0
  );

  return (
    <aside className="sidebar">
      <nav className="side-nav" aria-label="课程目录">
        {courses.map((course) => {
          const cid = `c-${course.key}`;
          const isOpen = open.has(cid);
          return (
            <div className="side-group" key={course.key}>
              <div className={`fold ${isOpen ? "open" : ""}`}>
                <button
                  type="button"
                  className="fold-head side-course-head"
                  aria-expanded={isOpen}
                  onClick={() => toggle(cid)}
                >
                  <span className="side-chev" aria-hidden>›</span>
                  <span className={`badge badge-mini ${course.cls}`} aria-hidden>{course.glyph}</span>
                  <span className="side-cat-name">{course.title}</span>
                </button>
                <div className="fold-body">
                  <div className="fold-inner">
                    {course.coming_soon && (
                      <p className="coming-pill mx-3 my-2">即将上线</p>
                    )}
                    {course.modules.map((mod, mi) => {
                      const mid = `m-${course.key}-${mod.name}`;
                      const single = course.modules.length === 1;
                      const rows = mod.chapters.map((ch) => (
                        <ChapterRow
                          key={ch.slug}
                          ch={ch}
                          courseKey={course.key}
                          done={!!done[ch.progress_key]}
                          open={open.has(`ch-${course.key}-${ch.slug}`)}
                          toggle={toggle}
                        />
                      ));
                      return single ? (
                        <div key={mi}>{rows}</div>
                      ) : (
                        <div className={`fold ${open.has(mid) ? "open" : ""}`} key={mi}>
                          <button
                            type="button"
                            className="fold-head side-mod-head"
                            aria-expanded={open.has(mid)}
                            onClick={() => toggle(mid)}
                          >
                            <span className="side-chev" aria-hidden>›</span>
                            {mod.name}
                          </button>
                          <div className="fold-body">
                            <div className="fold-inner">{rows}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        <div className="side-foot">
          <div className="progress">
            <i style={{ width: `${total ? (count / total) * 100 : 0}%` }} />
          </div>
          <span>已学 {count} / {total}</span>
        </div>
      </nav>
      <div className="backdrop" onClick={() => document.body.classList.remove("nav-open")} />
    </aside>
  );
}

function ChapterRow({
  ch,
  courseKey,
  done,
  open,
  toggle,
}: {
  ch: ChMeta;
  courseKey: string;
  done: boolean;
  open: boolean;
  toggle: (id: string) => void;
}) {
  const id = `ch-${courseKey}-${ch.slug}`;
  const num = ch.n !== null ? String(ch.n).padStart(2, "0") : "◈";
  const href = `/course/${courseKey}/${ch.slug}/`;
  const hasSecs = (ch.sections?.length ?? 0) > 0;
  return (
    <div className={`side-ch fold ${open ? "open" : ""}`}>
      <div className="side-ch-row">
        <Link
          href={href}
          className={`side-link ${done ? "done" : ""}`}
          data-ch={ch.progress_key || undefined}
        >
          <span className="side-num">{num}</span>
          <span className="side-name">{ch.title}</span>
        </Link>
        {hasSecs && (
          <button
            type="button"
            className="side-fold fold-head"
            aria-expanded={open}
            onClick={() => toggle(id)}
          >
            <span className="side-chev" aria-hidden>›</span>
          </button>
        )}
      </div>
      {hasSecs && (
        <div className="fold-body">
          <div className="fold-inner">
            <div className="side-sec">
              {ch.sections!.map((s, i) => (
                <Link key={i} href={href + (s.anchor ? `#${s.anchor}` : "")}>
                  {s.name}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
