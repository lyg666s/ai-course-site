"use client";

import { useEffect, useState } from "react";

// 章节页挂载时记录「最近阅读」，供首页继续学习按钮使用
export default function LastReadTracker({
  url,
  title,
  course,
}: {
  url: string;
  title: string;
  course: string;
}) {
  useEffect(() => {
    try {
      localStorage.setItem("pycourse-last", JSON.stringify({ url, title, course }));
    } catch {}
  }, [url, title, course]);
  return null;
}
