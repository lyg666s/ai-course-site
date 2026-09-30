"use client";

// 把正文里的 .codehilite 块增强为可编辑、可运行的代码卡（逻辑与旧版站点一致）

import { useEffect, useRef } from "react";
import { ensurePyodide } from "@/lib/pyodide";
import { caretOffset, pyHighlight, setCaretAt } from "@/lib/pyHighlight";

export default function ChapterContent({ html }: { html: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;

    // ---- 可运行 Python 代码卡 ----
    root
      .querySelectorAll(".codehilite.lang-python:not(.lang-norun)")
      .forEach((block) => {
        const el = block as HTMLElement;
        if (el.dataset.card) return;
        el.dataset.card = "1";
        const pre = el.querySelector("pre");
        if (!pre) return;

        const card = document.createElement("div");
        card.className = "codecard";
        el.parentNode!.insertBefore(card, el);
        const bar = document.createElement("div");
        bar.className = "codecard-bar";
        bar.innerHTML =
          '<span class="codecard-lang">python</span>' +
          '<span class="codecard-actions">' +
          '<button type="button" class="codecard-btn codecard-reset" hidden>还原</button>' +
          '<button type="button" class="codecard-btn codecard-run"><span class="run-ico">▶</span>运行</button>' +
          "</span>";
        const out = document.createElement("pre");
        out.className = "codecard-out";
        out.hidden = true;
        card.append(bar, el, out);

        const emptySpan = pre.querySelector("span:empty");
        if (emptySpan && emptySpan === pre.firstChild) emptySpan.remove();

        const original = pre.textContent || "";
        let dirty = false;
        let running = false;
        let composing = false;
        let hlTimer: ReturnType<typeof setTimeout> | null = null;
        const resetBtn = bar.querySelector(".codecard-reset") as HTMLButtonElement;
        const runBtn = bar.querySelector(".codecard-run") as HTMLButtonElement;

        (pre as HTMLElement).contentEditable = "true";
        pre.setAttribute("spellcheck", "false");
        pre.setAttribute("autocorrect", "off");
        pre.setAttribute("autocapitalize", "off");

        pre.addEventListener("keydown", (e) => {
          if (e.key === "Tab") {
            e.preventDefault();
            document.execCommand("insertText", false, "    ");
          }
        });
        pre.addEventListener("compositionstart", () => (composing = true));
        pre.addEventListener("compositionend", () => {
          composing = false;
          scheduleHighlight();
        });
        function scheduleHighlight() {
          if (composing) return;
          if (hlTimer) clearTimeout(hlTimer);
          hlTimer = setTimeout(() => {
            const off = caretOffset(pre as HTMLElement);
            const preEl = pre as HTMLElement;
            preEl.innerHTML = pyHighlight(preEl.textContent || "");
            if (off !== null) setCaretAt(preEl, off);
          }, 250);
        }
        pre.addEventListener("input", () => {
          if (!dirty) {
            dirty = true;
            resetBtn.hidden = false;
          }
          scheduleHighlight();
        });
        resetBtn.addEventListener("click", () => {
          pre.innerHTML = pyHighlight(original);
          dirty = false;
          resetBtn.hidden = true;
          out.hidden = true;
        });

        runBtn.addEventListener("click", () => {
          if (running) return;
          running = true;
          runBtn.classList.add("busy");
          runBtn.innerHTML = "运行中…";
          out.hidden = false;
          out.classList.remove("err");
          out.textContent = "正在加载 Python 运行时…（首次约需几秒）";
          const write = (s: string) => {
            out.textContent += s + "\n";
            out.scrollTop = out.scrollHeight;
          };
          ensurePyodide()
            .then((py) => {
              if (out.textContent && out.textContent.indexOf("正在加载") === 0) out.textContent = "";
              py.setStdout({ batched: write });
              py.setStderr({ batched: write });
              const code = (pre.textContent || "").replace(/\n+$/, "");
              return py.runPythonAsync(code).then((result: any) => {
                if (result !== undefined && result !== null) write(String(result));
                if (result && typeof result.destroy === "function") result.destroy();
              });
            })
            .catch((e) => {
              const msg = e && e.message ? e.message : String(e);
              out.textContent += (out.textContent ? "\n" : "") + msg;
              out.classList.add("err");
            })
            .then(() => {
              running = false;
              runBtn.classList.remove("busy");
              runBtn.innerHTML = '<span class="run-ico">▶</span>运行';
            });
        });
      });

    // ---- 复制按钮（非 Python 块） ----
    root
      .querySelectorAll(".codehilite:not(.lang-python), .md > pre")
      .forEach((block) => {
        const el = block as HTMLElement;
        if (el.dataset.copy) return;
        el.dataset.copy = "1";
        const pre = (el.querySelector("pre") || el) as HTMLElement;
        const btn = document.createElement("button");
        btn.className = "copy-btn";
        btn.type = "button";
        btn.textContent = "复制";
        btn.addEventListener("click", () => {
          navigator.clipboard.writeText(pre.textContent || "").then(() => {
            btn.textContent = "已复制";
            btn.classList.add("ok");
            setTimeout(() => {
              btn.textContent = "复制";
              btn.classList.remove("ok");
            }, 1600);
          });
        });
        el.appendChild(btn);
      });
  }, [html]);

  return <div className="md" ref={ref} dangerouslySetInnerHTML={{ __html: html }} />;
}
