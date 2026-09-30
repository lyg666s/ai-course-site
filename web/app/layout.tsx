import type { Metadata } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import { allFamilies } from "@/lib/data";

export const metadata: Metadata = {
  title: "AI大全栈 · 课程手册",
  description:
    "袁进主讲的系列课程手册：Python 语言核心精讲、数据科学工具包、数据库、Python 框架、Agents 底层逻辑、LangGraph、LangChain + DeepAgent。iOS 风格阅读体验，内置可运行的 Python 代码块。",
};

// 主题防闪烁：首屏渲染前根据 localStorage / 系统偏好挂 .dark
const themeScript = `(function(){try{var t=localStorage.getItem("theme");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;if(d)document.documentElement.classList.add("dark");}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const families = allFamilies();
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <TopNav families={families.map((f) => ({ key: f.key, name: f.name }))} />
        {children}
        <footer className="mx-auto max-w-[52rem] px-6 pb-10 text-center text-xs text-label3">
          AI大全栈 · 课程手册 — 由课件自动生成，仅供学习使用
        </footer>
      </body>
    </html>
  );
}
