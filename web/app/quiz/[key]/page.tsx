import { notFound } from "next/navigation";
import QuizClient from "@/components/QuizClient";
import { courseOf } from "@/lib/data";
import { getCourseExtra, QUIZ_KEYS } from "@/lib/extras";

export function generateStaticParams() {
  return QUIZ_KEYS.map((key) => ({ key }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const course = courseOf(key);
  return {
    title: course ? `面试题库 · ${course.title} · AI大全栈` : "面试题库 · AI大全栈",
    description: course
      ? `${course.title}课程配套面试题，按知识板块练习并查看解析。`
      : undefined,
  };
}

export default async function QuizPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const course = courseOf(key);
  const extra = getCourseExtra(key);
  if (!course || !extra) notFound();

  return (
    <main className="mx-auto max-w-[56rem] px-4 pb-20 pt-6 sm:px-6">
      <QuizClient
        courseKey={key}
        title={course.title}
        intro={extra.quiz.intro}
        blocks={extra.quiz.blocks}
      />
    </main>
  );
}
