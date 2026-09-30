import { allFamilies } from "@/lib/data";
import CourseCard from "@/components/CourseCard";
import { notFound } from "next/navigation";

export function generateStaticParams() {
  return allFamilies().map((f) => ({ family: f.key }));
}

export default async function FamilyPage({
  params,
}: {
  params: Promise<{ family: string }>;
}) {
  const { family } = await params;
  const fam = allFamilies().find((f) => f.key === family);
  if (!fam) notFound();

  const total = fam.courses.reduce((a, c) => a + c.chapter_count, 0);
  return (
    <main className="mx-auto max-w-[52rem] px-4 pb-20 pt-8 sm:px-6">
      <header className="hero !py-10">
        <h1 className="!text-[32px]">{fam.name}</h1>
        <p>
          {fam.courses.filter((c) => !c.coming_soon).length} 门课程 · {total} 章
          {fam.key === "agent"
            ? " · 从神经网络的底层逻辑，到 LangGraph 工作流编排，再到 DeepAgent 实战——搞懂 Agent 的每一层。"
            : " · 语言、框架、数据库与数据科学：把开发的地基打牢。"}
        </p>
      </header>
      <div className="grid gap-3 sm:grid-cols-2">
        {fam.courses.map((c) => (
          <CourseCard key={c.key} course={c} />
        ))}
      </div>
    </main>
  );
}
