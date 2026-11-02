import evalExtra from "@/extras/eval.json";
import infraExtra from "@/extras/infra.json";
import ragExtra from "@/extras/rag.json";

export type QuizQuestion = {
  q: string;
  options: string[];
  answer: number;
  explain: string;
};

export type QuizBlock = {
  id: string;
  name: string;
  range: string;
  questions: QuizQuestion[];
};

export type CourseExtra = {
  chapters: Record<string, string>;
  quiz: {
    intro: string;
    blocks: QuizBlock[];
  };
};

const EXTRAS: Record<string, CourseExtra> = {
  eval: evalExtra as CourseExtra,
  infra: infraExtra as CourseExtra,
  rag: ragExtra as CourseExtra,
};

export const QUIZ_KEYS = Object.keys(EXTRAS);

export function getCourseExtra(key: string): CourseExtra | undefined {
  return EXTRAS[key];
}

export function getChapterInsight(key: string, slug: string): string | undefined {
  return EXTRAS[key]?.chapters[slug];
}

export function getQuizBlocks(key: string): QuizBlock[] {
  return EXTRAS[key]?.quiz.blocks ?? [];
}

export function getQuizIntro(key: string): string {
  return EXTRAS[key]?.quiz.intro ?? "";
}

export function getQuizQuestionCount(key: string): number {
  return getQuizBlocks(key).reduce((total, block) => total + block.questions.length, 0);
}
