#!/bin/bash
# 重建 Next.js 课程站点并部署到 GitHub Pages
# 用法：./deploy.sh
set -e
cd "$(dirname "$0")"

# 命令行访问 github.com 需要走本机代理（端口按需调整）
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890

# 1. 导出内容数据（课件 → JSON / 搜索索引 / 图片资源）
/usr/bin/python3 scripts/export_content.py

# 2. 构建 Next.js 静态站点 → web/out/
(cd web && npx next build)
touch web/out/.nojekyll

# 3. 提交 main（源码；构建产物与内容 JSON 已被 gitignore）
git add -A
git commit -q -m "rebuild: 更新课程站点" || echo "（main 无变更，跳过提交）"
for i in 1 2 3; do git push -q origin main && break; echo "（main 推送重试 $i）"; sleep 3; done

# 4. 刷新 gh-pages 分支（Pages 部署源 = web/out/ 的内容）
git worktree add /tmp/gh-pages-deploy gh-pages 2>/dev/null || true
rsync -a --delete web/out/ /tmp/gh-pages-deploy/ --exclude=.git
(cd /tmp/gh-pages-deploy
  git add -A
  git commit -q -m "rebuild: 更新课程站点" --allow-empty
  for i in 1 2 3 4 5; do git push -q origin gh-pages && break; echo "（gh-pages 推送重试 $i）"; sleep 3; done
)
git worktree remove /tmp/gh-pages-deploy --force 2>/dev/null || true

echo "部署完成：https://lyg666s.github.io/ai-course-site/"
