
(function () {
  "use strict";
  var base = document.body.dataset.base || "";
  var LS_KEY = "pycourse-done";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- 已学进度 ---------- */
  function getDone() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch (e) { return {}; }
  }
  function setDone(map) { localStorage.setItem(LS_KEY, JSON.stringify(map)); }
  function refreshProgress() {
    var done = getDone();
    var total = $$(".side-link[data-ch]").length;
    var count = $$(".side-link[data-ch]").filter(function (a) { return done[a.dataset.ch]; }).length;
    $$(".side-link[data-ch]").forEach(function (a) {
      a.classList.toggle("done", !!done[a.dataset.ch]);
    });
    $$(".ch-row[data-ch]").forEach(function (a) {
      a.classList.toggle("done", !!done[a.dataset.ch]);
    });
    var bar = $("#progress-bar"), text = $("#progress-text");
    if (bar) bar.style.width = (total ? (count / total) * 100 : 0) + "%";
    if (text) text.textContent = "已学 " + count + " / " + total;
  }
  function initLearn() {
    var learnBtn = $(".learn");
    if (!learnBtn) return;
    var n = learnBtn.dataset.ch;
    var paint = function () {
      var on = !!getDone()[n];
      learnBtn.classList.toggle("done", on);
      learnBtn.textContent = on ? "✓ 已学" : "标记已学";
    };
    paint();
    learnBtn.addEventListener("click", function () {
      var d = getDone();
      if (d[n]) delete d[n]; else d[n] = true;
      setDone(d);
      paint(); refreshProgress();
    });
  }
  refreshProgress();

  /* ---------- 折叠树（大类 / 小类 / 小小类） ---------- */
  var TREE_KEY = "pycourse-tree";
  var treeOpen = {};
  try {
    (JSON.parse(localStorage.getItem(TREE_KEY)) || []).forEach(function (k) {
      treeOpen[k] = true;
    });
  } catch (e) {}
  function setFold(el, open) {
    el.classList.toggle("open", open);
    var head = el.querySelector(".fold-head");
    if (head) head.setAttribute("aria-expanded", open ? "true" : "false");
  }
  function initFolds() {
    $$(".fold").forEach(function (el) {
      var head = el.querySelector(".fold-head");
      if (!head) return;
      if (head.hasAttribute("data-pinned")) { setFold(el, true); }
      else if (treeOpen[el.dataset.fold]) { setFold(el, true); }
      head.addEventListener("click", function () {
        var open = !el.classList.contains("open");
        setFold(el, open);
        if (open) treeOpen[el.dataset.fold] = true;
        else delete treeOpen[el.dataset.fold];
        try {
          localStorage.setItem(TREE_KEY, JSON.stringify(Object.keys(treeOpen)));
        } catch (e) {}
      });
    });
  }

  /* ---------- 代码复制（非 Python 块） ---------- */
  function initCopy() {
  $$(".md .codehilite:not(.lang-python), .md > pre").forEach(function (block) {
    var pre = block.querySelector("pre") || block;
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "复制";
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(pre.textContent).then(function () {
        btn.textContent = "已复制"; btn.classList.add("ok");
        setTimeout(function () { btn.textContent = "复制"; btn.classList.remove("ok"); }, 1600);
      });
    });
    block.appendChild(btn);
  });
  }

  /* ---------- 轻量 Python 高亮（编辑后自动重新着色） ---------- */
  var PY_KW = /^(?:def|return|class|if|elif|else|for|while|in|not|and|or|import|from|as|with|try|except|finally|raise|pass|break|continue|lambda|global|nonlocal|yield|del|assert|async|await|is|None|True|False)\b/;
  var PY_BUILTIN = /^(?:print|len|range|str|int|float|bool|list|dict|set|tuple|type|isinstance|issubclass|super|getattr|setattr|hasattr|delattr|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|open|repr|format|input|iter|next|any|all|id|hash|callable|classmethod|staticmethod|property|self|cls)\b/;
  function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function pyHighlight(src) {
    // 引号常量逐段拼接，避免在本文件的三引号字符串里出现字面量三连引号
    var DQ = '"';
    var TQ = DQ + DQ + DQ;
    var quoteRe = new RegExp("^(?:[rbfu]{0,2})(" + TQ + "|'''" + "|" + DQ + "|')");
    var out = [], i = 0, n = src.length;
    while (i < n) {
      var c = src[i];
      if (c === "#") {
        var j = src.indexOf("\n", i); if (j < 0) j = n;
        out.push('<span class="c1">' + escHtml(src.slice(i, j)) + "</span>"); i = j; continue;
      }
      var sm = quoteRe.exec(src.slice(i));
      if (sm) {
        var q = sm[1], qi = i + sm[0].length - q.length, search = qi + q.length, end = n;
        while (true) {
          var k = src.indexOf(q, search);
          if (k < 0) break;
          var bs = 0, p = k - 1;
          while (src[p] === "\\") { bs++; p--; }
          if (bs % 2 === 0) { end = k + q.length; break; }
          search = k + q.length;
        }
        out.push('<span class="s1">' + escHtml(src.slice(i, end)) + "</span>"); i = end; continue;
      }
      if (c >= "0" && c <= "9") {
        var nm = /^\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?[jJ]?/.exec(src.slice(i));
        out.push('<span class="mi">' + escHtml(nm[0]) + "</span>"); i += nm[0].length; continue;
      }
      if (c === "@") {
        var dm = /^@[\w.]+/.exec(src.slice(i));
        if (dm) { out.push('<span class="nd">' + escHtml(dm[0]) + "</span>"); i += dm[0].length; continue; }
      }
      if (/[A-Za-z_]/.test(c)) {
        var im = /^[\w]+/.exec(src.slice(i))[0];
        var isCall = /^\s*\(/.test(src.slice(i + im.length));
        if (PY_KW.test(im)) out.push('<span class="k">' + escHtml(im) + "</span>");
        else if (PY_BUILTIN.test(im)) out.push('<span class="nb">' + escHtml(im) + "</span>");
        else if (isCall) out.push('<span class="nf">' + escHtml(im) + "</span>");
        else if (/^[A-Z]/.test(im)) out.push('<span class="nc">' + escHtml(im) + "</span>");
        else out.push(escHtml(im));
        i += im.length; continue;
      }
      out.push(escHtml(c)); i++;
    }
    return out.join("");
  }
  function caretOffset(el) {
    var sel = window.getSelection();
    if (!sel.rangeCount || !el.contains(sel.anchorNode)) return null;
    var range = sel.getRangeAt(0).cloneRange();
    var pre = document.createRange();
    pre.selectNodeContents(el);
    pre.setEnd(range.endContainer, range.endOffset);
    return pre.toString().length;
  }
  function setCaretAt(el, offset) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var node, cur = 0, r, s;
    while ((node = walker.nextNode())) {
      if (cur + node.length >= offset) {
        r = document.createRange();
        r.setStart(node, offset - cur);
        r.collapse(true);
        s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        return;
      }
      cur += node.length;
    }
    r = document.createRange(); r.selectNodeContents(el); r.collapse(false);
    s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  /* ---------- 可运行的 Python 代码卡 ---------- */
  var pyodideReady = null;
  function loadFrom(indexURL) {
    return import(indexURL + "pyodide.mjs").then(function (m) {
      return m.loadPyodide({ indexURL: indexURL });
    });
  }
  function ensurePyodide() {
    if (!pyodideReady) {
      var local = base + "assets/pyodide/";
      var CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
      pyodideReady = loadFrom(local).catch(function () { return loadFrom(CDN); });
    }
    return pyodideReady;
  }

  function initCodeCards() {
    $$(".md .codehilite.lang-python:not(.lang-norun)").forEach(function (block) {
    var pre = block.querySelector("pre");
    if (!pre) return;
    var card = document.createElement("div");
    card.className = "codecard";
    var bar = document.createElement("div");
    bar.className = "codecard-bar";
    bar.innerHTML =
      '<span class="codecard-lang">python</span>' +
      '<span class="codecard-actions">' +
      '<button type="button" class="codecard-btn codecard-reset" hidden>还原</button>' +
      '<button type="button" class="codecard-btn codecard-run"><span class="run-ico">▶</span>运行</button>' +
      "</span>";
    var out = document.createElement("pre");
    out.className = "codecard-out";
    out.hidden = true;
    block.parentNode.insertBefore(card, block);
    card.appendChild(bar);
    card.appendChild(block);
    card.appendChild(out);

    var emptySpan = pre.querySelector("span:empty");
    if (emptySpan && emptySpan === pre.firstChild) emptySpan.remove();

    var original = pre.textContent;
    var dirty = false;
    var running = false;
    var composing = false;
    var hlTimer = null;
    var resetBtn = bar.querySelector(".codecard-reset");
    var runBtn = bar.querySelector(".codecard-run");

    pre.contentEditable = "true";
    pre.spellcheck = false;
    pre.setAttribute("autocorrect", "off");
    pre.setAttribute("autocapitalize", "off");
    pre.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        document.execCommand("insertText", false, "    ");
      }
    });
    pre.addEventListener("compositionstart", function () { composing = true; });
    pre.addEventListener("compositionend", function () {
      composing = false;
      scheduleHighlight();
    });
    function scheduleHighlight() {
      if (composing) return;
      clearTimeout(hlTimer);
      hlTimer = setTimeout(function () {
        var off = caretOffset(pre);
        pre.innerHTML = pyHighlight(pre.textContent);
        if (off !== null) setCaretAt(pre, off);
      }, 250);
    }
    pre.addEventListener("input", function () {
      if (!dirty) { dirty = true; resetBtn.hidden = false; }
      scheduleHighlight();
    });
    resetBtn.addEventListener("click", function () {
      pre.innerHTML = pyHighlight(original);
      dirty = false;
      resetBtn.hidden = true;
      out.hidden = true;
    });

    runBtn.addEventListener("click", function () {
      if (running) return;
      running = true;
      runBtn.classList.add("busy");
      runBtn.innerHTML = "运行中…";
      out.hidden = false;
      out.classList.remove("err");
      out.textContent = pyodideReady ? "" : "正在加载 Python 运行时…（首次约需几秒）";
      var write = function (s) {
        out.textContent += s + "\n";
        out.scrollTop = out.scrollHeight;
      };
      ensurePyodide().then(function (py) {
        if (out.textContent.indexOf("正在加载") === 0) out.textContent = "";
        py.setStdout({ batched: write });
        py.setStderr({ batched: write });
        var code = pre.textContent.replace(/\n+$/, "");
        return py.runPythonAsync(code).then(function (res) {
          if (res !== undefined && res !== null) write(String(res));
          if (res && typeof res.destroy === "function") res.destroy();
        });
      }).catch(function (e) {
        var msg = e && e.message ? e.message : String(e);
        out.textContent += (out.textContent ? "\n" : "") + msg;
        out.classList.add("err");
      }).then(function () {
        running = false;
        runBtn.classList.remove("busy");
        runBtn.innerHTML = '<span class="run-ico">▶</span>运行';
      });
    });
  });
  }

  /* ---------- 右栏目录 scrollspy ---------- */
  var pageSpy = null;
  function initScrollspy() {
    if (pageSpy) { pageSpy.disconnect(); pageSpy = null; }
    var tocLinks = $$(".toc-list a");
    if (!tocLinks.length || !("IntersectionObserver" in window)) return;
    var byId = {};
    tocLinks.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var headings = Object.keys(byId)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    var active = null;
    pageSpy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          if (active) active.classList.remove("active");
          active = byId[en.target.id];
          active.classList.add("active");
        }
      });
    }, { rootMargin: "-10% 0px -75% 0px", threshold: 0 });
    headings.forEach(function (h) { pageSpy.observe(h); });
  }

  /* ---------- 搜索 ---------- */
  var input = $("#search-input"), panel = $("#search-panel");
  var INDEX = null, FETCH_FAILED = false;
  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function snippet(text, q) {
    var i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) { return esc(text.slice(0, 60)); }
    var start = Math.max(0, i - 18);
    var frag = text.slice(start, i + q.length + 42);
    var marked = esc(frag).replace(
      new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
      function (m) { return "<mark>" + m + "</mark>"; }
    );
    return (start > 0 ? "…" : "") + marked;
  }
  function search(q) {
    if (!INDEX) return [];
    var out = [];
    var ql = q.toLowerCase();
    INDEX.forEach(function (ch) {
      var hits = [];
      if (ch.title.toLowerCase().indexOf(ql) >= 0) {
        hits.push({ sec: null, body: "第 " + ch.n + " 章目录项", anchor: null });
      }
      ch.sections.forEach(function (s) {
        if (s.name.toLowerCase().indexOf(ql) >= 0) {
          hits.push({ sec: s.name, body: s.body, anchor: s.anchor });
        } else if (s.body.toLowerCase().indexOf(ql) >= 0) {
          hits.push({ sec: s.name, body: s.body, anchor: s.anchor });
        }
      });
      out.push({ ch: ch, hits: hits.slice(0, 3) });
    });
    return out.filter(function (r) { return r.hits.length; }).slice(0, 10);
  }
  function renderResults(q, results) {
    if (!q) { panel.hidden = true; return; }
    if (INDEX === null) {
      panel.innerHTML = '<p class="search-empty">索引加载中…</p>';
      panel.hidden = false; return;
    }
    if (!results.length) {
      panel.innerHTML = '<p class="search-empty">' +
        (FETCH_FAILED
          ? "直接打开文件时搜索不可用，请通过本地服务器访问"
          : "没有找到「" + esc(q) + "」相关内容") +
        "</p>";
      panel.hidden = false; return;
    }
    var html = results.map(function (r) {
      return r.hits.map(function (h) {
        var href = base + r.ch.url + (h.anchor ? "#" + h.anchor : "");
        return '<a class="search-item" href="' + href + '">' +
          '<span class="search-item-title"><span class="s-num">' +
          (r.ch.n ? String(r.ch.n).padStart(2, "0") : "◈") + "</span>" +
          esc(r.ch.title) + "</span>" +
          (h.sec ? '<span class="search-item-sec">' + esc(h.sec) + "</span>" : "") +
          '<span class="search-item-sec">' + snippet(h.body || h.sec || "", q) + "</span>" +
          "</a>";
      }).join("");
    }).join("");
    panel.innerHTML = html;
    panel.hidden = false;
  }
  if (input && panel) {
    fetch(base + "assets/search.json")
      .then(function (r) { return r.json(); })
      .then(function (data) { INDEX = data; })
      .catch(function () { INDEX = []; FETCH_FAILED = true; });
    input.addEventListener("input", function () { renderResults(input.value.trim(), search(input.value.trim())); });
    input.addEventListener("focus", function () { if (input.value.trim()) renderResults(input.value.trim(), search(input.value.trim())); });
    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && e.target !== input) panel.hidden = true;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { panel.hidden = true; input.blur(); }
    });
  }

  /* ---------- 侧栏滚动定位：跳转后让当前章节保持可见 ---------- */
  function jumpToActive() {
    var sideNav = $(".side-nav");
    if (!sideNav) return;
    var active = sideNav.querySelector(".side-link.active");
    if (!active) return;
    active.scrollIntoView({ block: "nearest", inline: "nearest" });
    // 贴着底边时上移一点，让当前章节和它的下一章都能看到
    var nb = sideNav.getBoundingClientRect().bottom;
    var ab = active.getBoundingClientRect().bottom;
    if (nb - ab < 32) sideNav.scrollTop -= 32 - (nb - ab);
  }
  function bindSideNavScroll() {
    var sideNav = $(".side-nav");
    if (!sideNav) return;
    var savedScroll = NaN;
    try {
      savedScroll = parseInt(sessionStorage.getItem("pycourse-side-scroll"), 10);
    } catch (e) {}
    if (!isNaN(savedScroll)) sideNav.scrollTop = savedScroll;
    var scrollTimer = null;
    sideNav.addEventListener("scroll", function () {
      if (scrollTimer) clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function () {
        try {
          sessionStorage.setItem("pycourse-side-scroll", String(sideNav.scrollTop));
        } catch (e) {}
      }, 120);
    });
  }
  bindSideNavScroll();
  jumpToActive();
  setTimeout(jumpToActive, 300); // 等折叠展开动画结束再校准一次

  /* ---------- 移动端抽屉 ---------- */
  var burger = $("#burger");
  if (burger) {
    burger.addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
      burger.setAttribute("aria-expanded", document.body.classList.contains("nav-open"));
    });
    $("#backdrop").addEventListener("click", function () {
      document.body.classList.remove("nav-open");
    });
  }

  /* ---------- 键盘翻页 ---------- */
  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea") || e.target.isContentEditable ||
        e.metaKey || e.ctrlKey || e.altKey) return;
    var prev = $(".pager-prev"), next = $(".pager-next");
    if (e.key === "ArrowLeft" && prev) navigate(prev.href, true);
    if (e.key === "ArrowRight" && next) navigate(next.href, true);
  });

  /* ---------- 客户端路由：站内跳转无刷新 ---------- */
  function applyPage(doc) {
    document.title = doc.title;
    var newLayout = doc.querySelector(".layout");
    var oldLayout = document.querySelector(".layout");
    if (newLayout && oldLayout) oldLayout.replaceWith(newLayout);
    var newNav = doc.querySelector(".side-nav");
    var oldNav = document.querySelector(".side-nav");
    if (newNav && oldNav) oldNav.replaceWith(newNav);
    var input = $("#search-input"), panel = $("#search-panel");
    if (input) input.value = "";
    if (panel) panel.hidden = true;
    document.body.classList.remove("nav-open");
    bindSideNavScroll();
    initFolds();
    initLearn();
    initCopy();
    initCodeCards();
    initScrollspy();
    refreshProgress();
    jumpToActive();
    setTimeout(jumpToActive, 300);
  }
  function navigate(href, push) {
    var u = new URL(href, location.href);
    if (u.origin !== location.origin) { location.href = href; return; }
    fetch(u.pathname + u.search)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (text) {
        var doc = new DOMParser().parseFromString(text, "text/html");
        applyPage(doc);
        if (push) history.pushState({}, "", u.pathname + u.search + u.hash);
        var target = u.hash ? document.getElementById(decodeURIComponent(u.hash.slice(1))) : null;
        if (target) target.scrollIntoView();
        else window.scrollTo(0, 0);
      })
      .catch(function () { location.href = href; });
  }
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
    if (a.origin !== location.origin || !/\.html$/.test(a.pathname)) return;
    if (a.pathname === location.pathname && a.hash) return; // 同页锚点走浏览器默认
    if (a.pathname + a.search === location.pathname + location.search) { e.preventDefault(); return; }
    e.preventDefault();
    navigate(a.href, true);
  });
  window.addEventListener("popstate", function () {
    navigate(location.href, false);
  });

  /* ---------- 启动 ---------- */
  initFolds();
  initLearn();
  initCopy();
  initCodeCards();
  initScrollspy();
})();
