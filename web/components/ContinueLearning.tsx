"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Last = { url: string; title: string; course: string };

// 首页/课程页的「继续学习」按钮：读取最近阅读的章节，没有则指向推荐入口
export default function ContinueLearning({
  fallbackHref = "/agent/",
  fallbackLabel = "进入 AI · Agent 开发",
}: {
  fallbackHref?: string;
  fallbackLabel?: string;
}) {
  const [last, setLast] = useState<Last | null>(null);
  useEffect(() => {
    try {
      const raw = localStorage.getItem("pycourse-last");
      if (raw) setLast(JSON.parse(raw));
    } catch {}
  }, []);

  return (
    <div className="flex flex-wrap gap-3">
      {last && (
        <Link href={last.url} className="btn-primary no-underline">
          继续学习：{last.title}
        </Link>
      )}
      <Link
        href={last ? fallbackHref : fallbackHref}
        className={`no-underline ${last ? "btn-ghost" : "btn-primary"}`}
      >
        {last ? fallbackLabel : "开始学习"}
      </Link>
    </div>
  );
}
