# 40 Days of Devotion build kit

Everything needed to rebuild the whole site.

## Rebuild the site

```
bash build/deploy.sh
git add -A && git commit -m "..." && git push
```

## What's here

| File | What it is |
| --- | --- |
| `content/devotion/NN.md` | The 40 devotion days, one file each. Text follows the book draft (the Google Doc) and matches the Notion pages. The gray note block at the top of each file holds the old address (kept as the page address) and the banner photo; it is not shown on the site. |
| `buildsite.py` | Builds the 40 day pages, the landing page (also used as the home page), the sign-up and not-found pages, and `_redirects`, `robots.txt`, `sitemap.xml`. |
| `site/style.css` | All styles, including phone and print. Edited by hand. |
| `site/site.js` | Video play button, copy-link button, two-minute timer, journal box (saved in the reader's browser only). |
| `site/favicon.svg` | Browser tab icon. |
| `deploy.sh` | Runs the build and copies the results to the repo root. |

## Common changes

- **Fix wording on a day:** edit that day's file in `content/`, then rebuild. Keep the Notion page in step.
- **Add a missing worship song or prayer (Day 36):** add a `**Song:**` line and a `[Watch on YouTube](https://www.youtube.com/watch?v=...)` line under `## Worship`, and the prayer as an italic paragraph (`*...*`) under `## Prayer`. Bracketed placeholders like `[Prayer still to be written]` are skipped on the site.
- **Day 29 video:** the book draft changed the song to "O Come to the Altar", so the page links to a YouTube search for now. When you have the right video, put it in `content/devotion/29.md` and remove day 29 from `SONG_LINKS` in `buildsite.py`.
- **Change styles:** edit `site/style.css`, then rebuild. The stylesheet link carries a version tag, so changes show up right away.
- **Day page layout:** four movements, each with a big heading: Word (the main verse, then the devotional, then "Scriptures for Today" under a small label), Worship, Pray, Listen & Obey. A day's `## Invite a Friend` section (only Day 1 has one) shows last, under a small label. Built by `render_sections` in `buildsite.py`.
- **Day page reading type:** matched to Substack posts (Spectral 19px, line height 1.6, 20px between paragraphs, 728px column; 17px on phones). Sections are 48px apart with no divider lines. The Word verse has a thin green line down its left side (`.word .verse`). Set by `.day` and the `--serif` and `--read` variables in `site/style.css`.

## Spanish landing page (/es/)

`dmj_home_es()` in `buildsite.py` builds the Spanish Don't Miss Jesus page at `/es/`, and `dmj_welcome_es()` builds the Spanish thank-you page at `/es/bienvenido`. The Spanish forms post to their own Kit landing page, "No te pierdas a Jesús 2026 (Español)" (form 10220197, `DMJ_FORM_ES`), in the background and then send the reader to `/es/bienvenido`. They also set the **Language** custom field to `es`.

In Kit, the automation "No te pierdas a Jesús 2026 (Español): etiquetar inscripciones" adds the tag "No te pierdas a Jesús 2026 (Español)", adds the main "Don't Miss Jesus 2026" tag (so they get the daily emails, which are in English for now) and sends the Spanish welcome email (sequence "No te pierdas a Jesús 2026: Bienvenida (Español)").

The resource pages have Spanish versions too: `/es/devocionales-en-familia`, `/es/accion-de-gracias` and `/es/navidad` (`dmj_family_es`, `dmj_top10_es`, `dmj_top20_es`). `DMJ_PAIRS` in `buildsite.py` lists each English page with its Spanish version; it sets where the toggle goes and the hreflang links. Each pair of pages carries hreflang links to each other, and every Don't Miss Jesus page has a language toggle in the header (a pill showing EN or ES with a globe; tapping it switches language).

## Don't Miss Jesus day pages

`dmj_days()` in `buildsite.py` builds `/dontmissjesus/day-1` through `day-7` from `content/dontmissjesus/week1.json` (the Week 1 doc). Each day has its title, photo, main verse, devotional, Scriptures for Today, worship video, prayer, the "Give thanks for 7" prompt and Listen & Obey. Photos are in `/photos/dmj/` (`day-NN.webp`, plus `day-NN-share.jpg` for link previews). Each page lists the Scripture credits it needs at the bottom: NASB1995 by default, with any ESV, NKJV or BSB passages named. Styles are at the end of `site/dmj.css` under "Don't Miss Jesus day pages".

## Photos

Photos live in `/photos` at the repo root (WebP, uploaded Oct 30, 2026). The build matches each day to its photo by the original file name from the old site; `DAY_PHOTOS` in `buildsite.py` covers the exceptions (Days 1, 2 and 36). `DAY_FOCUS` sets where a tall photo is cropped. Link-preview copies (1200x630 JPG) are made into `photos/share/` the first time the build sees a photo.

To change a day's photo, upload the new file to `photos/`, add the day to `DAY_PHOTOS`, and rebuild.

Still loading from Squarespace, so upload them before Squarespace is cancelled: the landing page banner (`yusron-el-jihan-pc4OfudfwOo-unsplash`), the Face to Face card (`Face+to+Face+Square`) and the Alone With God card (`Untitled+design+(3)`). Keep those names and the build picks them up.
