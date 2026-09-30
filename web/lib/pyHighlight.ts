// 轻量 Python 语法高亮：代码被用户编辑后重新着色（类名与 Pygments 一致）
"use client";

const PY_KW =
  /^(?:def|return|class|if|elif|else|for|while|in|not|and|or|import|from|as|with|try|except|finally|raise|pass|break|continue|lambda|global|nonlocal|yield|del|assert|async|await|is|None|True|False)\b/;
const PY_BUILTIN =
  /^(?:print|len|range|str|int|float|bool|list|dict|set|tuple|type|isinstance|issubclass|super|getattr|setattr|hasattr|delattr|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|open|repr|format|input|iter|next|any|all|id|hash|callable|classmethod|staticmethod|property|self|cls)\b/;

function escHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function pyHighlight(src: string): string {
  // 三引号常量逐段拼接，避免源码里出现字面量三连引号
  const DQ = '"';
  const TQ = DQ + DQ + DQ;
  const quoteRe = new RegExp("^(?:[rbfu]{0,2})(" + TQ + "|'''" + "|" + DQ + "|')");
  const out: string[] = [];
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    if (c === "#") {
      let j = src.indexOf("\n", i);
      if (j < 0) j = n;
      out.push(`<span class="c1">${escHtml(src.slice(i, j))}</span>`);
      i = j;
      continue;
    }
    const sm = quoteRe.exec(src.slice(i));
    if (sm) {
      const q = sm[1];
      const qi = i + sm[0].length - q.length;
      let search = qi + q.length;
      let end = n;
      for (;;) {
        const k = src.indexOf(q, search);
        if (k < 0) break;
        let bs = 0;
        let p = k - 1;
        while (src[p] === "\\") {
          bs++;
          p--;
        }
        if (bs % 2 === 0) {
          end = k + q.length;
          break;
        }
        search = k + q.length;
      }
      out.push(`<span class="s1">${escHtml(src.slice(i, end))}</span>`);
      i = end;
      continue;
    }
    if (c >= "0" && c <= "9") {
      const nm = /^\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?[jJ]?/.exec(src.slice(i))!;
      out.push(`<span class="mi">${escHtml(nm[0])}</span>`);
      i += nm[0].length;
      continue;
    }
    if (c === "@") {
      const dm = /^@[\w.]+/.exec(src.slice(i));
      if (dm) {
        out.push(`<span class="nd">${escHtml(dm[0])}</span>`);
        i += dm[0].length;
        continue;
      }
    }
    if (/[A-Za-z_]/.test(c)) {
      const im = /^[\w]+/.exec(src.slice(i))![0];
      const isCall = /^\s*\(/.test(src.slice(i + im.length));
      if (PY_KW.test(im)) out.push(`<span class="k">${escHtml(im)}</span>`);
      else if (PY_BUILTIN.test(im)) out.push(`<span class="nb">${escHtml(im)}</span>`);
      else if (isCall) out.push(`<span class="nf">${escHtml(im)}</span>`);
      else if (/^[A-Z]/.test(im)) out.push(`<span class="nc">${escHtml(im)}</span>`);
      else out.push(escHtml(im));
      i += im.length;
      continue;
    }
    out.push(escHtml(c));
    i++;
  }
  return out.join("");
}

export function caretOffset(el: HTMLElement): number | null {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount || !el.contains(sel.anchorNode)) return null;
  const range = sel.getRangeAt(0).cloneRange();
  const pre = document.createRange();
  pre.selectNodeContents(el);
  pre.setEnd(range.endContainer, range.endOffset);
  return pre.toString().length;
}

export function setCaretAt(el: HTMLElement, offset: number) {
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let node: Node | null;
  let cur = 0;
  let range: Range;
  while ((node = walker.nextNode())) {
    if (cur + node.textContent!.length >= offset) {
      range = document.createRange();
      range.setStart(node, offset - cur);
      range.collapse(true);
      const s = window.getSelection()!;
      s.removeAllRanges();
      s.addRange(range);
      return;
    }
    cur += node.textContent!.length;
  }
  range = document.createRange();
  range.selectNodeContents(el);
  range.collapse(false);
  const s = window.getSelection()!;
  s.removeAllRanges();
  s.addRange(range);
}
