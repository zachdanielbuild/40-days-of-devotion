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
- **Change styles:** edit `site/style.css`.

## Photos

Photos live in `/photos` at the repo root (WebP, uploaded Oct 30, 2026). The build matches each day to its photo by the original file name from the old site; `DAY_PHOTOS` in `buildsite.py` covers the exceptions (Days 1, 2 and 36). `DAY_FOCUS` sets where a tall photo is cropped. Link-preview copies (1200x630 JPG) are made into `photos/share/` the first time the build sees a photo.

To change a day's photo, upload the new file to `photos/`, add the day to `DAY_PHOTOS`, and rebuild.

Still loading from Squarespace, so upload them before Squarespace is cancelled: the landing page banner (`yusron-el-jihan-pc4OfudfwOo-unsplash`), the Face to Face card (`Face+to+Face+Square`) and the Alone With God card (`Untitled+design+(3)`). Keep those names and the build picks them up.
