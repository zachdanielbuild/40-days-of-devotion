# 40 Days of Devotion

The redesigned 40 Days of Devotion site, a resource from Antioch Waco.

Plain static HTML, one stylesheet (`style.css`) and one small script (`site.js`). Cloudflare serves the files in the repo root.

## Deploying on Cloudflare
- Deployed as a Cloudflare Worker serving static files; settings are in `wrangler.jsonc` (files left out of the site are listed in `.assetsignore`).

Pushing to `main` redeploys in about a minute.

## Addresses
- `/` and `/devotion`: the landing page with all 40 days
- `/devos/<day>`: the 40 days
- Old Squarespace day addresses are kept, so links in emails already sent still work. Retired addresses redirect (see `_redirects`).

## Making changes
Everything is generated from `build/`. See `build/README.md`.
