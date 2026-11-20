#!/usr/bin/env bash
# Rebuild every page and copy the result to the repo root (what Cloudflare Pages serves).
# Usage: bash build/deploy.sh   (from anywhere). Then commit and push to main.
set -e
B="$(cd "$(dirname "$0")" && pwd)"; R="$(dirname "$B")"
cd "$B" && python3 buildsite.py
rm -rf "$R/devos"
cp -r "$B"/site/devos "$R/"
rm -rf "$R/dontmissjesus"; cp -r "$B"/site/dontmissjesus "$R/"
rm -rf "$R/es"; if [ -d "$B"/site/es ]; then cp -r "$B"/site/es "$R/"; fi
cp "$B"/site/*.html "$B"/site/style.css "$B"/site/dmj.css "$B"/site/dmj-favicon.svg "$B"/site/dmj-icon-180.png "$B"/site/dmj-share.png "$B"/site/site.js "$B"/site/favicon.svg \
   "$B"/site/_redirects "$B"/site/robots.txt "$B"/site/sitemap.xml "$R/"
echo "Built. Now: git add -A && git commit -m \"...\" && git push"
