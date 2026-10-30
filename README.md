# 40DayJourneys.com

The redesigned 40DayJourneys.com, a resource from Antioch Waco: 40 Days of Devotion and 40 Days of Discipleship.

Plain static HTML, one stylesheet (`style.css`) and one small script (`site.js`). Cloudflare Pages serves the files in the repo root.

## Deploying on Cloudflare Pages
- Framework preset: None
- Build command: (leave empty)
- Build output directory: `/`

Pushing to `main` redeploys in about a minute.

## Addresses
- `/` home, `/devotion` and `/40-days-of-discipleship` landing pages
- `/devos/<day>` the 40 devotion days, `/discipleship/<day>` Orientation plus the 40 discipleship days
- Old Squarespace day addresses are kept, so links in emails already sent still work. Retired addresses redirect (see `_redirects`).

## Making changes
Everything is generated from `build/`. See `build/README.md`.
