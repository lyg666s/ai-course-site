#!/bin/bash
# 重建 Next.js 课程站点并部署到 GitHub Pages
# 用法：./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

SITE_URL="https://lyg666s.github.io/ai-course-site"
MAIN_BRANCH="main"
PAGES_BRANCH="gh-pages"
WORKTREE="/tmp/gh-pages-deploy"

# 0. 命令行访问 github.com 需要走本机代理
#    优先复用已导出的环境变量；否则自动探测常见代理端口（7890 Clash / 7897 Clash Verge / 1087 等）
if [ -z "${HTTPS_PROXY:-}" ] && [ -z "${https_proxy:-}" ]; then
  for port in 7890 7897 1087 7891 6152; do
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
      export HTTPS_PROXY="http://127.0.0.1:$port"
      export HTTP_PROXY="http://127.0.0.1:$port"
      echo "→ 使用本地代理 127.0.0.1:$port"
      break
    fi
  done
fi

# 推送重试，失败要真的失败（别让脚本假装部署成功）
push_branch() {
  local branch="$1" dir="${2:-.}" i
  for i in 1 2 3 4 5; do
    if (cd "$dir" && git push -q origin "$branch"); then
      return 0
    fi
    echo "（$branch 推送失败，重试 $i/5）"
    sleep 3
  done
  echo "✗ 推送到 $branch 失败：检查网络或代理设置（当前 HTTPS_PROXY=${HTTPS_PROXY:-未设置}）" >&2
  return 1
}

# 1. 导出内容数据（课件 → JSON / 搜索索引 / 图片资源）
#    只改前端/样式、课件没动时可以 SKIP_EXPORT=1 ./deploy.sh 跳过这一步
if [ "${SKIP_EXPORT:-0}" = "1" ]; then
  echo "→ 跳过内容导出（SKIP_EXPORT=1），沿用现有 JSON 与图片资源"
else
  /usr/bin/python3 scripts/export_content.py
fi

# 2. 构建 Next.js 静态站点 → web/out/
(cd web && npx next build)
touch web/out/.nojekyll

# 3. 提交 main（源码；构建产物与内容 JSON 已被 gitignore）
git add -A
git commit -q -m "rebuild: 更新课程站点" || echo "（main 无变更，跳过提交）"
push_branch "$MAIN_BRANCH"

# 4. 刷新 gh-pages 分支（Pages 部署源 = web/out/ 的内容）
git worktree remove "$WORKTREE" --force 2>/dev/null || true
rm -rf "$WORKTREE"
git worktree prune
git worktree add -q "$WORKTREE" "$PAGES_BRANCH"
rsync -a --delete web/out/ "$WORKTREE"/ --exclude=.git
(
  cd "$WORKTREE"
  git add -A
  git commit -q -m "rebuild: 更新课程站点" --allow-empty
)
push_branch "$PAGES_BRANCH" "$WORKTREE"
git worktree remove "$WORKTREE" --force 2>/dev/null || true

# 5. 校验线上是否真的切到本次构建（Pages 构建有几十秒延迟）
CSS_PATH=$(grep -o '/ai-course-site/_next/static/css/[a-z0-9]*\.css' web/out/index.html | head -1 || true)
if [ -n "$CSS_PATH" ]; then
  for i in $(seq 1 12); do
    if curl -sf --max-time 10 "$SITE_URL$CSS_PATH" -o /dev/null; then
      echo "✓ 部署完成，线上已是本次构建：$SITE_URL/"
      exit 0
    fi
    echo "… 等待 GitHub Pages 构建（$i/12）"
    sleep 15
  done
  echo "已推送，但 3 分钟内还没探测到新构建（Pages 可能仍在排队），稍后刷新 $SITE_URL/" >&2
  exit 0
fi

echo "✓ 已推送：$SITE_URL/"
