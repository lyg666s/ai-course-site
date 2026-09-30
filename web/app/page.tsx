import Link from "next/link";
import { allFamilies } from "@/lib/data";
import ContinueLearning from "@/components/ContinueLearning";
import CourseCard from "@/components/CourseCard";

// 学习路径（Udemy 式步骤条）
const PATH = [
  { step: "01", name: "Python 语言核心", href: "/course/py/", desc: "语法 · OOP · 异步，AI 时代的地基" },
  { step: "02", name: "数据库 + 数据科学", href: "/course/db/", desc: "PostgreSQL · NumPy · Pandas · Matplotlib" },
  { step: "03", name: "Python 框架", href: "/course/fw/", desc: "FastAPI · SQLAlchemy · 部署上云" },
  { step: "04", name: "AI · Agent 开发", href: "/agent/", desc: "底层逻辑 · LangGraph · DeepAgent" },
  { step: "05", name: "Java · 云计算", href: "/course/java/", desc: "即将上线", soon: true },
];

export default function Home() {
  const families = allFamilies();
  const total = families.reduce(
    (a, f) => a + f.courses.reduce((x, c) => x + c.chapter_count, 0),
    0
  );
  return (
    <main className="mx-auto max-w-[52rem] px-4 pb-20 pt-8 sm:px-6">
      <header className="hero">
        <p className="text-sm font-semibold tracking-wide opacity-70">袁进 主讲 · 系列课程</p>
        <h1>
          AI大全栈<span className="hl">课程手册</span>
        </h1>
        <p>
          从 Python 语言核心，到数据库、数据科学、Web 框架，再到 AI · Agent
          开发——一条完整的学习路线，全程干货，大量练习，重视概念与设计。
        </p>
        <p className="hero-facts">
          {families.length} 大方向 · {families.reduce((a, f) => a + f.courses.length, 0)} 门课程 · {total} 章 · 内置可运行的 Python 代码块
        </p>
        <ContinueLearning />
      </header>

      <section className="mt-2">
        <h2 className="mb-3 px-1 text-xl font-bold tracking-tight text-label">学习路径</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PATH.map((p) => (
            <Link
              key={p.step}
              href={p.href}
              className={`path-step no-underline ${p.soon ? "opacity-60" : ""}`}
            >
              <span className={`path-num ${p.soon ? "bg-fill text-label3" : "bg-blue-tint text-blue"}`}>
                {p.step}
              </span>
              <span className="min-w-0">
                <span className="block text-[15px] font-semibold text-label">{p.name}</span>
                <span className="block text-xs text-label2">{p.desc}</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      {families.map((f) => (
        <section key={f.key} className="mt-10">
          <div className="mb-3 flex items-baseline justify-between px-1">
            <h2 className="text-xl font-bold tracking-tight text-label">{f.name}</h2>
            <Link href={`/${f.key}/`} className="text-[13px] text-blue no-underline hover:underline">
              查看方向 →
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {f.courses.map((c) => (
              <CourseCard key={c.key} course={c} />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
