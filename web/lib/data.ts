// 站点数据类型与加载（构建期 / 服务端使用）

export type SecMeta = { name: string; anchor: string | null };

export type ChapterMeta = {
  n: number | null;
  slug: string;
  title: string;
  group: string;
  progress_key: string;
};

export type ChapterData = ChapterMeta & {
  kicker_mod: string;
  sec_meta: SecMeta[];
  html: string;
};

export type CourseModule = { name: string; chapters: ChapterMeta[] };

export type CourseSummary = {
  key: string;
  title: string;
  desc: string;
  glyph: string;
  cls: string;
  coming_soon: boolean;
  chapter_count: number;
  section_count: number;
  modules: CourseModule[];
};

export type Family = { key: string; name: string; courses: CourseSummary[] };

import indexJson from "@/content/index.json";

export const siteIndex = indexJson as unknown as { families: Family[] };

export function allFamilies(): Family[] {
  return siteIndex.families;
}

export function familyOf(key: string): Family {
  return siteIndex.families.find((f) => f.courses.some((c) => c.key === key)) ?? siteIndex.families[0];
}

export function courseOf(key: string): CourseSummary | undefined {
  for (const f of siteIndex.families) {
    const c = f.courses.find((c) => c.key === key);
    if (c) return c;
  }
  return undefined;
}

export async function loadCourse(key: string): Promise<CourseData> {
  const mod = (await import(`@/content/${key}.json`)) as { default: CourseData };
  return mod.default;
}

export type CourseData = {
  key: string;
  title: string;
  desc: string;
  glyph: string;
  cls: string;
  coming_soon?: boolean;
  modules: { name: string; chapters: ChapterData[] }[];
};

export function courseChapters(course: CourseData | CourseSummary): ChapterMeta[] {
  return course.modules.flatMap((m) => m.chapters);
}

export function chapterPath(key: string, slug: string): string {
  return `/course/${key}/${slug}/`;
}

export function coursePath(key: string): string {
  return `/course/${key}/`;
}

export function familyPath(key: string): string {
  return `/${key}/`;
}
