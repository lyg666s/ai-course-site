"use client";

import { useEffect, useState } from "react";
import { isDone, toggleDone } from "@/lib/progress";

export default function LearnToggle({ progressKey }: { progressKey: string }) {
  const [done, setDone] = useState(false);
  useEffect(() => {
    const update = () => setDone(isDone(progressKey));
    update();
    window.addEventListener("pycourse-progress", update);
    return () => window.removeEventListener("pycourse-progress", update);
  }, [progressKey]);

  return (
    <button
      type="button"
      className={`learn ${done ? "done" : ""}`}
      onClick={() => toggleDone(progressKey)}
    >
      {done ? "✓ 已学" : "标记已学"}
    </button>
  );
}
