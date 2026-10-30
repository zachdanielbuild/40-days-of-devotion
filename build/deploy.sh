#!/usr/bin/env bash
# Rebuild every page and copy the result to the repo root (what Cloudflare Pages serves).
# Usage: bash build/deploy.sh   (from anywhere). Then commit and push to main.
set -e
B="$(cd "$(dirname "$0")" && pwd)"; R="$(dirname "$B")"
cd "$B" && python3 buildsite.py
rm -rf "$R/devos" "$R/discipleship"
cp -r "$B"/site/devos "$B"/site/discipleship "$R/"
cp "$B"/site/*.html "$B"/site/style.css "$B"/site/site.js "$B"/site/favicon.svg \
   "$B"/site/_redirects "$B"/site/robots.txt "$B"/site/sitemap.xml "$R/"
echo "Built. Now: git add -A && git commit -m \"...\" && git push"
