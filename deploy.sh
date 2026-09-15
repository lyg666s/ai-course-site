#!/bin/bash
# 重建课程站点并部署到 GitHub Pages
# 用法：./deploy.sh
set -e
cd "$(dirname "$0")"

# 命令行访问 github.com 需要走本机代理（端口按需调整）
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890

# 1. 重新生成站点
/usr/bin/python3 build_site.py

# 2. 提交 main（源码 + 生成的 site/）
git add site README.md build_site.py serve_site.py
git commit -q -m "rebuild: 更新课程站点" || echo "（main 无变更，跳过提交）"
git push -q origin main

# 3. 刷新 gh-pages 分支（Pages 部署源）
git worktree add /tmp/gh-pages-deploy gh-pages 2>/dev/null || true
rsync -a --delete site/ /tmp/gh-pages-deploy/ --exclude=.git
cd /tmp/gh-pages-deploy
git add -A
if git diff --cached --quiet; then
  echo "（gh-pages 无变更）"
else
  git commit -q -m "rebuild: 更新课程站点"
  git push -q origin gh-pages
fi
cd "$OLDPWD"
git worktree remove /tmp/gh-pages-deploy --force 2>/dev/null || true

echo "部署完成：https://lyg666s.github.io/ai-course-site/"
