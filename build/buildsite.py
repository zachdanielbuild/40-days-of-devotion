"""Build every page of 40DayJourneys.com into build/site/.

Content lives in build/content/ as one Markdown file per day (the same text as the
Notion pages). Run `bash build/deploy.sh` from the repo root, then commit and push.
"""
import glob, html, json, os, re

D = os.path.dirname(os.path.abspath(__file__))
C, OUT = D + '/content', D + '/site'
DOMAIN = 'https://www.40daysofdevotion.com'
KIT_DEVOTION = 'https://passionandpurpose.kit.com/40-days-of-devotion'
CDN = 'https://images.squarespace-cdn.com/content/v1/6765a61dee5146683ca33b13/'
SECTIONS = [('Drawing Near', 1, 7), ('Worship', 8, 14), ('The Word', 15, 21), ('Prayer', 22, 33), ('Listening', 34, 40)]
NEW_SLUGS = {36: 'he-calls-his-sheep'}          # days that never existed on the old site
SONG_LINKS = {}   # day -> (song name, YouTube search URL), for a day whose video link is wrong or missing

# Photos live in /photos at the repo root (uploaded Oct 30, 2026). A photo not found there
# still loads from Squarespace. Days whose photo isn't the old site's banner:
PHOTOS = os.path.join(os.path.dirname(D), 'photos')
DAY_PHOTOS = {1: '1.webp', 2: '2.webp', 36: 'tim-mossholder-4VkGIl-2z18-unsplash.webp'}
DAY_FOCUS = {36: '50% 12%'}   # where to crop a tall photo (default: the middle)

def local_photo(u):
    """The uploaded file for a photo address (or a 'local:<file>' name), if there is one."""
    if not u: return None
    if u.startswith('local:'): return u[6:]
    stem = os.path.splitext(u.rsplit('/', 1)[1])[0]
    for f in os.listdir(PHOTOS) if os.path.isdir(PHOTOS) else []:
        if os.path.splitext(f)[0] == stem: return f
    return None

def share_image(f):
    """A 1200x630 JPG copy for link previews (texts, social media), made once."""
    out = os.path.join(PHOTOS, 'share', os.path.splitext(f)[0] + '.jpg')
    if not os.path.exists(out):
        try:
            from PIL import Image
        except ImportError:
            return f'/photos/{f}'
        im = Image.open(os.path.join(PHOTOS, f)).convert('RGB')
        r = 1200 / 630
        if im.width / im.height > r:
            w = int(im.height * r); im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height))
        else:
            h = int(im.width / r); im = im.crop((0, (im.height - h) // 2, im.width, (im.height - h) // 2 + h))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.resize((1200, 630), Image.LANCZOS).save(out, quality=85, optimize=True)
    return f'/photos/share/{os.path.basename(out)}'

def small_image(rel, width=800):
    """An 800px-wide WebP copy of a photo for phones, made once. rel is the path under /photos."""
    src = os.path.join(PHOTOS, rel)
    d, f = os.path.split(rel)
    out = os.path.join(PHOTOS, d, 'w800', f)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        try:
            from PIL import Image
            im = Image.open(src)
            if im.width <= width: return None
            im = im.convert('RGB')
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            im.save(out, 'WEBP', quality=72, method=6)
        except Exception:
            return None
    return '/photos/' + '/'.join(x for x in (d, 'w800', f) if x)

def srcset(url, _w, sizes):
    """srcset/sizes attributes for a local /photos URL, so phones get the 800px copy."""
    if not url.startswith('/photos/'): return ''
    path, _, q = url.partition('?')
    small = small_image(path[len('/photos/'):])
    if not small: return ''
    q = '?' + q if q else ''
    from PIL import Image
    full_w = Image.open(os.path.join(PHOTOS, path[len('/photos/'):])).width
    return f' srcset="{small}{q} 800w, {path}{q} {full_w}w" sizes="{sizes}"'

def photo(u, w=1500, share=False):
    f = local_photo(u)
    if f: return share_image(f) if share else f'/photos/{f}'
    return f'{u}?format={w}w' if u else ''

def esc(s):
    return html.escape(s, quote=True)

# ---------- reading the Markdown ----------
def parse(path):
    text = open(path, encoding='utf-8').read()
    title, rest = text.split('\n', 1)
    m = re.search(r'<callout[^>]*>(.*?)</callout>', rest, re.S)
    meta, body = m.group(1), rest[m.end():]
    old = re.search(r'<b>Old URL:</b>\s*(\S+)', meta)
    ph = re.search(r'\[Banner photo\]\(([^)]+)\)', meta)
    secs, cur = [], None
    for block in re.split(r'\n\s*\n', body.strip()):
        if block.startswith('## '):
            cur = [block[3:].strip(), []]; secs.append(cur)
        elif cur is not None:
            cur[1].append(block.strip())
    return dict(title=title.strip(), slug=old.group(1).rsplit('/', 1)[1] if old else None,
                photo=ph.group(1) if ph else '', sections=secs)

def fixhref(h):
    h = h.replace('https://www.40dayjourneys.com', '')
    return h

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{fixhref(m[2])}">{m[1]}</a>', s)
    s = re.sub(r'(\*\*[^*]+\?\*\*)(?=\S)', r'\1<br>', s)        # FAQ: question then answer
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    return s.replace('*', '').replace('\n', '<br>')

def is_italic(b):
    return b.startswith('*') and not b.startswith('**') and b.endswith('*')

def is_placeholder(b):
    return re.fullmatch(r'\[[^\]]+\]', b) is not None

def plain(b):
    return b.replace('*', '').strip()

VERSES = r'\d+[a-z]?(?:[\-–]\d+[a-z]?)?(?:,\s?\d+(?:[\-–]\d+)?)*(?:\s?-\s?\d+)?'
REF = re.compile(r'^((?:[1-3] )?[A-Z][a-z]+ \d+(?:[.:]' + VERSES + r')?(?: \([A-Z]+\))?)[\s:\-–]*(\S.*)$', re.S)
TRAIL = re.compile(r'^(.*?)\s+((?:[1-3] )?[A-Z][a-z]+ \d+[.:][\d\-–a-z,]+)$', re.S)

def ref_colon(r):
    return re.sub(r'(\d)\.(\d)', r'\1:\2', r)

def block(b):
    lines = b.split('\n')
    if all(l.startswith('- ') for l in lines):
        return '<ul>' + ''.join(f'<li>{inline(l[2:])}</li>' for l in lines) + '</ul>'
    if all(l.startswith('> ') for l in lines):
        return '<blockquote>' + inline('\n'.join(l[2:] for l in lines)) + '</blockquote>'
    if is_italic(b):
        return f'<p><em>{inline(plain(b))}</em></p>'
    return f'<p>{inline(b)}</p>'

# ---------- sections ----------
ICON_COPY = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#141414" stroke-width="1.6" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a1 1 0 0 1 1-1h10"/></svg>'
ICON_TIMER = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 2h6"/></svg>'
ICON_PLAY = '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="#FFFFFF"/></svg>'

def sec_word_verse(blocks):
    raw = plain(' '.join(l[2:] if l.startswith('> ') else l for b in blocks for l in b.split('\n')))
    ref, text = '', raw
    m = REF.match(raw)
    if m: ref, text = m.group(1), m.group(2)
    else:
        m = TRAIL.match(raw)
        if m: text, ref = m.group(1), m.group(2)
    out = f'<blockquote>{inline(text)}</blockquote>'
    if ref: out += f'<p class="ref">{esc(ref_colon(ref))}</p>'
    return f'<div class="verse">{out}</div>'


def video(vid, title):
    return (f'<div class="video" data-id="{vid}" data-title="{esc(title)}">'
            f'<img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" loading="lazy">'
            f'<button type="button" aria-label="Play worship video">{ICON_PLAY}</button></div>'
            f'<noscript><a href="https://www.youtube.com/watch?v={vid}">Watch on YouTube</a></noscript>')

def sec_worship(blocks, n=None, series='devotion'):
    song, out = '', []
    for b in blocks:
        if is_placeholder(b): continue
        m = re.match(r'\*\*Song:\*\*\s*(.*)', b)
        if m:
            song = re.sub(r'\s*\[[^\]]*\]', '', m.group(1))
            if '[' in m.group(1): song = song.rsplit(' by ', 1)[0]
            continue
        y = re.fullmatch(r'\[Watch on YouTube\]\(https://www\.youtube\.com/watch\?v=([\w-]+)\)', b)
        if y: out.append(('video', y.group(1)))
        else: out.append(('html', block(b)))
    if series == 'devotion' and n in SONG_LINKS:
        name, url = SONG_LINKS[n]
        return f'<p><a class="btn btn-outline" href="{url}">{ICON_PLAY.replace("#FFFFFF", "#141414")}<span>Find “{esc(name)}” on YouTube</span></a></p>'
    if not out and not song: return ''
    html_ = ''.join(video(v, song or 'Worship video') if k == 'video' else v for k, v in out)
    if song: html_ += f'<p class="song">{esc(song)}</p>'
    return html_

def sec_prayer(blocks):
    blocks = [b for b in blocks if not is_placeholder(b)]
    if not blocks: return ''
    if all(is_italic(b) for b in blocks):
        return '<div class="prayer-panel">' + ''.join(f'<p>{inline(plain(b))}</p>' for b in blocks) + '</div>'
    return ''.join(block(b) for b in blocks)

def sec_invite(blocks):
    out = []
    for b in blocks:
        m = re.search(r'\((https://passionandpurpose\.kit\.com/[^)]+)\)', b)
        if b.startswith('- ') and m:
            u = m.group(1)
            out.append(f'<div class="share-row"><button type="button" class="btn btn-outline" data-copy="{u}">{ICON_COPY}<span class="label">Copy the sign-up link</span></button>'
                       f'<span class="url">{esc(u.replace("https://", ""))}</span></div>')
        else:
            out.append(block(b))
    return ''.join(out)

def sec_listen(blocks):
    parts = [block(b) for b in blocks if not is_placeholder(b)]
    timer = f'<button type="button" class="btn timer">{ICON_TIMER}<span class="label">Begin two minutes of quiet</span></button>'
    parts.insert(1 if parts else 0, timer)
    parts.append('<div class="journal"><label for="journal">What I sense the Lord saying</label>'
                 '<textarea id="journal" rows="5"></textarea>'
                 '<span class="note">Saved on this device only.</span></div>')
    return ''.join(parts)

# ---------- day layout: four movements (Word, Worship, Pray, Listen & Obey); Invite a Friend last, only where a day has it ----------
def sec_scriptures(blocks):
    # Each passage: the text in italics, then its reference in small capitals underneath (like the Word verse).
    out, cur = [], None
    def close():
        nonlocal cur
        if cur: out.append(f'<div class="passage">{"".join(cur[1])}<p class="ref">{esc(ref_colon(cur[0]))}</p></div>')
        cur = None
    for i, b in enumerate(blocks):
        if is_placeholder(b): continue
        m = REF.match(plain(b)) if i or is_italic(b) else None
        if m:
            close(); cur = (m.group(1), [f'<p>{inline(m.group(2))}</p>'])
        elif cur and is_italic(b):
            cur[1].append(f'<p>{inline(plain(b))}</p>')
        else:
            close(); out.append(f'<p class="intro">{inline(b)}</p>' if i == 0 else block(b))
    close()
    return ''.join(out)

def render_sections(d, n, series):
    secs = dict(d['sections'])
    def body(name): return ''.join(block(b) for b in secs.get(name, []) if not is_placeholder(b))
    word = (sec_word_verse(secs['Word'])
            + f'<div class="devo">{body("Daily Devotional")}</div>'
            + f'<div class="today"><h3 class="label">Scriptures for Today</h3>{sec_scriptures(secs["Scriptures For Today"])}</div>')
    out = [f'<section class="word"><h2>Word</h2>{word}</section>']
    w = sec_worship(secs.get('Worship', []), n, series)
    if w: out.append(f'<section><h2>Worship</h2>{w}</section>')
    pr = sec_prayer(secs.get('Prayer', []))
    if pr: out.append(f'<section><h2>Pray</h2>{pr}</section>')
    out.append(f'<section><h2>Listen &amp; Obey</h2>{sec_listen(secs.get("Listen & Obey", []))}</section>')
    if 'Invite a Friend' in secs:
        out.append(f'<section class="invite"><h3 class="label">Invite a Friend</h3>{sec_invite(secs["Invite a Friend"])}</section>')
    return ''.join(out)


# ---------- page shell ----------
# Antioch logo (traced from the black PNG). It takes its color from CSS: black, or white on the home page photo.
LOGO = ('<svg viewBox="0 0 500 500" role="img" aria-label="40 Days of Devotion home"><path fill="currentColor" fill-rule="evenodd" d="M234.5,482.0C194.1,479.0 155.0,465.8 122.0,443.7C113.0,437.7 104.2,431.0 101.8,428.3C100.1,426.4 102.7,420.5 174.3,267.2C225.2,158.0 249.0,108.0 250.0,108.0C251.1,108.0 274.8,157.8 325.5,266.6C366.2,353.8 399.6,425.8 399.8,426.4C400.2,428.0 381.5,441.9 369.0,449.4C329.2,473.4 280.1,485.3 234.5,482.0ZM52.3,371.3C45.3,360.3 40.8,351.9 36.1,341.2C6.3,273.5 10.7,194.3 47.9,130.8C75.5,83.6 119.3,47.3 170.0,29.9C192.9,22.0 224.2,15.7 226.9,18.5C228.2,19.9 61.0,378.4 58.8,378.8C57.8,379.0 55.6,376.4 52.3,371.3ZM436.5,371.8C434.6,367.8 396.8,286.9 352.6,192.0C301.1,81.6 272.5,19.1 273.1,18.5C274.2,17.4 278.6,17.6 290.5,19.6C387.3,35.8 462.7,110.3 479.9,206.7C488.0,251.9 482.4,299.3 464.0,341.1C456.7,357.5 443.9,379.0 441.4,379.0C440.5,379.0 438.4,375.8 436.5,371.8ZM191.1,294.6C224.9,279.7 268.8,278.8 304.0,292.5C316.9,297.4 317.0,297.5 317.0,295.9C317.0,295.1 311.8,283.1 305.4,269.2L293.7,244.0L289.7,242.9C273.5,238.6 249.1,236.9 232.4,238.9C223.3,240.1 207.3,243.3 206.6,244.1C205.6,245.2 183.0,294.9 183.0,295.8C183.0,297.6 185.2,297.3 191.1,294.6Z"/></svg>')

# Version tag on the stylesheet link, so browsers fetch the new file as soon as style.css changes.
import hashlib
CSS_V = hashlib.md5(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site', 'style.css'), 'rb').read()).hexdigest()[:8]

GA_ID = 'G-4K89PV3SRJ'  # Google Analytics 4 (40 Days of Devotion property)

def shell(title, desc, path, body, image='', signup=None, script=False, overlay=False, noindex=False):
    nav = ['<a href="/devotion#days">All 40 Days</a>', '<a href="/resources">Resources</a>']
    if signup: nav.append(f'<a class="signup" href="{signup}">Sign up</a>')
    if image.startswith('/'): image = DOMAIN + image
    og = f'<meta property="og:image" content="{esc(image)}">\n<meta name="twitter:card" content="summary_large_image">\n' if image else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">{chr(10) + '<meta name="robots" content="noindex">' if noindex else ''}
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="40 Days of Devotion">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
{og}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&amp;family=Spectral:ital,wght@0,400;0,600;1,400&amp;display=swap">
<link rel="stylesheet" href="/style.css?v={CSS_V}">
</head>
<body{' class="overlay"' if overlay else ''}>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
<a class="logo" href="/">{LOGO}</a>
<nav class="site-nav" aria-label="Main">{"".join(nav)}</nav>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">Made with love from <a href="https://antiochwaco.com/">Antioch Waco</a></footer>
{'<script src="/site.js" defer></script>' if script else ''}
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "60f7bffc099e494d968954bbf6b5bca0"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
'''

def first_sentence(d):
    for name, blocks in d['sections']:
        if name in ('Daily Devotional', 'Word', 'Vision', 'Vision for This Week', 'Wrap Up'):
            for b in blocks:
                if not b.startswith(('>', '-', '[')):
                    t = plain(re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', b))
                    return (t[:155].rsplit(' ', 1)[0] + '…') if len(t) > 160 else t
    return ''

def write(name, s):
    p = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)

def section_of(n):
    return next(s for s in SECTIONS if s[1] <= n <= s[2])

# ---------- day pages ----------
def day_page(d, n, series, prev, nxt, total=40, variant=''):
    name = d['title'].split(': ', 1)[1]
    eyebrow = f'Day {n} of {total} · {section_of(n)[0]}'
    signup, base, home, home_t = KIT_DEVOTION, '/devos/', '/devotion', '40 Days of Devotion'
    pct = max(n, 0) / total * 100
    focus = f' style="object-position:{DAY_FOCUS[n]}"' if n in DAY_FOCUS else ''
    bsrc = photo(d["photo"]) if d['photo'] else ''
    banner = f'<div class="banner"><img src="{bsrc}"{srcset(bsrc, 1500, "(max-width: 1020px) 100vw, 956px")} alt="" width="1500" height="1071" fetchpriority="high"{focus}></div>' if d['photo'] else ''
    def link(item, cls, k):
        if not item:
            return f'<a class="{cls}" href="{home}#days"><span class="k">{"← Back" if cls == "prev" else "Finished →"}</span><span class="t">{"All 40 Days" if cls == "prev" else home_t}</span></a>'
        pn, pd = item
        t = pd['title'].split(': ', 1)[1] if ': ' in pd['title'] else pd['title']
        lab = f'Day {pn}' if pn else 'Orientation'
        arrow = f'← {lab}' if cls == 'prev' else f'{lab} →'
        return f'<a class="{cls}" href="{base}{pd["slug"]}"><span class="k">{arrow}</span><span class="t">{esc(t)}</span></a>'
    body = f'''<div class="day-head">
<p class="eyebrow">{esc(eyebrow)}</p>
<div class="progress" aria-hidden="true"><span style="width:{pct:.1f}%"></span></div>
<h1>{inline(name)}</h1>
</div>
{banner}
<article class="day{' ' + variant if variant else ''}">
{render_sections(d, n, series)}
<nav class="day-nav" aria-label="Days">{link(prev, "prev", 0)}{link(nxt, "next", 1)}</nav>
</article>'''
    title = f'{"Day " + str(n) + ": " if n else ""}{plain(name)} · {home_t}'
    if len(title) > 60: title = title.rsplit(' · ', 1)[0]
    return shell(title, first_sentence(d), base + d['slug'], body, photo(d['photo'], 1200, share=True), signup, script=True, noindex=bool(variant))

def build_series(series, files, numbering):
    items = []
    for f in files:
        d = parse(f)
        n = numbering(f)
        if not d['slug']: d['slug'] = NEW_SLUGS[n]
        if n in DAY_PHOTOS: d['photo'] = 'local:' + DAY_PHOTOS[n]
        items.append((n, d))
    for i, (n, d) in enumerate(items):
        prev = items[i - 1] if i else None
        nxt = items[i + 1] if i + 1 < len(items) else None
        folder = 'devos' if series == 'devotion' else 'discipleship'
        write(f'{folder}/{d["slug"]}.html', day_page(d, n, series, prev, nxt))
    return items

num = lambda f: int(os.path.basename(f)[:2])
DEV = build_series('devotion', sorted(glob.glob(C + '/devotion/*.md')), num)

# ---------- landing pages ----------
def day_rows(items, base):
    return ''.join(f'<li><a href="{base}{d["slug"]}"><span class="n">{n if n else "·"}</span><span class="t">{inline(d["title"].split(": ", 1)[1] if ": " in d["title"] else d["title"])}</span></a></li>' for n, d in items)

def card(img, eyebrow, title, text, href, more):
    a = f'<a class="more" href="{href}">{more} →</a>' if href else ''
    im = f'<img class="ph" src="{photo(img, 1000)}" alt="" loading="lazy">' if img else ''
    return f'<article class="card">{im}<p class="eyebrow">{eyebrow}</p><h2>{title}</h2><p>{text}</p>{a}</article>'

BOOK_URL = 'https://www.store.antiochcc.net/collections/books/products/40-day-devotional-book'   # link for the printed book; leave empty to show "Link coming soon"
HERO_PHOTO = 'local:2.webp'   # the misty valley photo behind the home page title

# Each "way" card is topped with a small topographic map: soft contour rings around two
# hills and a dotted trail from a trailhead (open dot) to a destination (filled dot).
MAPS = [
    ([(90, 120, 0.4, 1.5), (300, 30, 1.6, 1.3)], 'M30,140 C90,120 120,80 180,95 S270,70 300,52', (30, 140), (300, 52)),
    ([(200, 70, 2.1, 1.6), (20, 160, 0.9, 1.2)], 'M40,60 C100,40 140,130 200,120 S280,60 320,110', (40, 60), (320, 110)),
    ([(110, 40, 1.3, 1.4), (320, 150, 2.6, 1.5)], 'M30,100 C80,150 150,150 190,100 S260,30 330,45', (30, 100), (330, 45)),
]

def topo_svg(i):
    import math
    hills, trail, start, end = MAPS[i]
    rings = []
    for cx, cy, ph, sx in hills:
        for k in range(1, 8):
            r, p = 20 * k, ph + k * 0.3
            pts = []
            for j in range(40):
                t = 2 * math.pi * j / 40
                rr = r * (1 + 0.18 * math.sin(3 * t + p) + 0.11 * math.sin(5 * t + p * 1.7))
                pts.append(f'{cx + rr * math.cos(t) * sx:.0f},{cy + rr * math.sin(t):.0f}')
            rings.append(f'<path class="{"c2" if k % 4 == 0 else "c1"}" d="M{" L".join(pts)}Z"/>')
    return (f'<svg viewBox="0 0 360 170" preserveAspectRatio="xMidYMid slice" aria-hidden="true">{"".join(rings)}'
            f'<path class="trail" d="{trail}"/><circle class="start" cx="{start[0]}" cy="{start[1]}" r="5"/>'
            f'<circle class="end" cx="{end[0]}" cy="{end[1]}" r="6"/></svg>')

def way(i, label, title, text, action):
    return (f'<article class="way"><div class="map">{topo_svg(i)}<span>{label}</span></div>'
            f'<div class="way-body"><h3>{title}</h3><p>{text}</p>{action}</div></article>')

def resources():
    body = f'''<section class="hero">
<p class="eyebrow">Go deeper</p>
<h1>Resources</h1>
<p class="lede">Companions for the 40 days, and for the daily rhythm that continues after them.</p>
</section>
<section class="cards two resources" aria-label="Resources">
{card(CDN + 'd4b62a2c-ca5a-4f28-8d46-4e23169885a1/Face+to+Face+Square.png', 'Teaching Series', 'Face to Face', 'A six-part series on Scripture, worship, prayer, listening, obeying, and abiding in Jesus.', 'https://www.youtube.com/playlist?list=PLoXSy2HiYN4uEu-SuVRHI5QVy5RowVX_E', 'Watch the series')}
{card(CDN + 'cff63a66-5bf8-4b1c-9498-c259fe20fe99/Untitled+design+%283%29.png', 'Guidebook', 'Alone With God', 'Practical tools and examples for prayer, worship, and Bible study, for a more intimate connection with God through daily devotions.', 'https://antiochwaco.com/alone-with-god-page', 'Get the guidebook')}
</section>'''
    write('resources.html', shell('Resources · 40 Days of Devotion', 'Go deeper after 40 Days of Devotion with the Face to Face teaching series and the Alone With God guidebook for daily time with God.', '/resources', body, '', KIT_DEVOTION))

# ---------- Don't Miss Jesus: seasonal home page (Nov 2026 to Jan 1 2027) ----------
# Set DMJ_SEASON = False after Jan 1 to put the 40 Days of Devotion landing page back on the home page.
DMJ_SEASON = True
DMJ_FORM = 'https://app.kit.com/forms/10209100/subscriptions'   # Kit landing page "Don't Miss Jesus 2026"
DMJ_FORM_ES = 'https://app.kit.com/forms/10220197/subscriptions'   # Kit landing page "No te pierdas a Jesús 2026 (Español)": tags, Spanish welcome email
DMJ_CSS_V = hashlib.md5(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site', 'dmj.css'), 'rb').read()).hexdigest()[:8]
DMJ_WEEKS = [('Thanksgiving', 1, 7, 'Nov 23 to 29'), ('Hope', 8, 14, 'Nov 30 to Dec 6'), ('Peace', 15, 21, 'Dec 7 to 13'),
             ('Joy', 22, 28, 'Dec 14 to 20'), ('Love', 29, 35, 'Dec 21 to 27'), ('Grace', 36, 40, 'Dec 28 to Jan 1')]

def dots(n): return '<div class="dots" aria-hidden="true">' + ''.join('<span class="on"></span>' if i == 0 else '<span></span>' for i in range(n)) + '</div>'

DMJ_UI = {
    'en': dict(brand="DON'T MISS JESUS", home='/', nav=[('/#weeks', 'The weeks'), ('/devotion', '40 Days of Devotion')], toggle=('EN', '/es/', 'es', 'Ver en español'), signup='Sign up',
               merry='Merry Christmas', family='From your family at Antioch Waco', skip='Skip to content',
               foot=[('/devotion', '40 Days of Devotion'), ('/resources', 'Resources'), ('/es/', 'Español'), ('https://antiochwaco.com/', 'Antioch Waco')]),
    'es': dict(brand='NO TE PIERDAS A JESÚS', home='/es/', nav=[('/es/#weeks', 'Las semanas')], toggle=('ES', '/', 'en', 'View in English'), signup='Inscríbete',
               merry='Feliz Navidad', family='De parte de tu familia en Antioch Waco', skip='Ir al contenido',
               foot=[('/', 'English'), ('https://antiochwaco.com/', 'Antioch Waco')]),
}
GLOBE = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">'
         '<circle cx="12" cy="12" r="10"/><ellipse cx="12" cy="12" rx="4.5" ry="10"/><path d="M2 12h20M4 6.5h16M4 17.5h16M12 2v20"/></svg>')
# English page <-> its Spanish version. Drives the EN/ES toggle and the hreflang links.
DMJ_PAIRS = [('/', '/es/'), ('/dontmissjesus/family-devotions', '/es/devocionales-en-familia'),
             ('/dontmissjesus/top-10-thanksgiving', '/es/accion-de-gracias'), ('/dontmissjesus/top-20-christmas', '/es/navidad'),
             ('/dontmissjesus/welcome', '/es/bienvenido')]

def dmj_shell(title, desc, path, body, signup='/#join', extra='', lang='en', image='/dmj-share.png', image_alt='The Antioch A logo', head=''):
    ui = DMJ_UI[lang]
    nav = ''.join(f'<a href="{h}">{t}</a>' for h, t in ui['nav'])
    code, href, other, label = ui['toggle']
    pair = next((pr for pr in DMJ_PAIRS if path in pr), None)
    if pair: href = pair[1] if lang == 'en' else pair[0]
    alts = (f'<link rel="alternate" hreflang="en" href="{DOMAIN}{pair[0]}">\n<link rel="alternate" hreflang="es" href="{DOMAIN}{pair[1]}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{DOMAIN}{pair[0]}">\n') if pair else ''
    toggle = (f'<a class="lang-toggle" href="{href}" hreflang="{other}" lang="{other}" aria-label="{label}" title="{label}">'
              f'<span lang="{lang}">{code}</span>{GLOBE}</a>')
    foot = ''.join(f'<a href="{h}">{t}</a>' for h, t in ui['foot'])
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{DOMAIN}{path}">
{alts}<meta property="og:type" content="website">
<meta property="og:site_name" content="40 Days of Devotion">
<meta property="og:locale" content="{'es_US' if lang == 'es' else 'en_US'}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
<meta property="og:image" content="{DOMAIN}{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(image_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{DOMAIN}{image}">
<meta name="theme-color" content="#7C1F1F">
<link rel="icon" href="/dmj-favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/dmj-icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,900&amp;family=Outfit:wght@400;500;600;700&amp;family=Yellowtail&amp;display=swap">
<link rel="stylesheet" href="/dmj.css?v={DMJ_CSS_V}">
{head}</head>
<body class="dmj{extra}">
<a class="skip" href="#main">{ui['skip']}</a>
<header class="dmj-header"><a class="dmj-brand" href="{ui['home']}"><span class="dmj-logo">{LOGO}</span>{ui['brand']}</a>
<nav class="dmj-nav" aria-label="Main">{nav}<a class="btn btn-red" href="{signup}">{ui['signup']}</a>{toggle}</nav></header>
<main id="main" class="dmj-main">
{body}
</main>
<footer class="dmj-footer"><span class="dmj-logo foot" aria-hidden="true">{LOGO}</span><span class="script">{ui['merry']}</span><p>{ui['family']}</p>
<nav aria-label="Footer">{foot}</nav></footer>
<script>document.querySelectorAll('form[action*="app.kit.com"]').forEach(function(f){{f.addEventListener('submit',function(e){{if(f.dataset.sent)return;e.preventDefault();f.dataset.sent='1';var go=function(){{if(f.dataset.next&&window.fetch){{fetch(f.action,{{method:'POST',body:new FormData(f),mode:'no-cors'}}).then(function(){{location.href=f.dataset.next}},function(){{f.submit()}})}}else f.submit()}};var t=setTimeout(go,1000);try{{gtag('event','sign_up',{{method:"Don't Miss Jesus",form_location:f.id==='join'?'hero':'signup_box',language:document.documentElement.lang,transport_type:'beacon',event_callback:function(){{clearTimeout(t);go()}}}})}}catch(err){{clearTimeout(t);go()}}}})}});</script>
<script>document.querySelectorAll('.rail,.more').forEach(function(r){{var d=r.nextElementSibling;if(!d||!d.classList.contains('dots'))return;r.addEventListener('scroll',function(){{var c=r.children[0];if(!c)return;var i=Math.round(r.scrollLeft/(c.offsetWidth+16));d.querySelectorAll('span').forEach(function(s,k){{s.classList.toggle('on',k===i)}})}},{{passive:true}})}});</script>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "60f7bffc099e494d968954bbf6b5bca0"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
'''

def dmj_family():
    desc = "A simple way to start each day with God at the center as a family: give thanks, read and talk, then pray."
    body = """<article class="guide">
<header class="guide-head"><p class="eyebrow">For families</p><h1><span class="script">How to do</span><span class="slab">Family Devotions</span></h1>
<p class="byline">From Jimmy and Laura Seibert</p>
<p class="lede">“The family that prays together stays together.” This simple phrase really is a truth.</p></header>
<div class="guide-body">
<p>When we were raising our kids, the Lord gave us a vision to build a family of love, honor, and purpose. Family devotions were a key part of creating that environment in our home. For us it was a very simple process that looked something like this:</p>
<ol class="guide-steps">
<li><span class="n">01</span><div><h2>Give thanks</h2><p>We pray for breakfast, and then everyone describes one thing they are thankful for. “In everything give thanks; for this is God’s will for you in Christ Jesus.” We want to create thankful hearts and thankful attitudes, and there is always something to be thankful for.</p></div></li>
<li><span class="n">02</span><div><h2>Read and talk</h2><p>Then we share a passage of Scripture or a thought from a devotion, and we discuss it for about five minutes.</p></div></li>
<li><span class="n">03</span><div><h2>Pray</h2><p>We usually pray for one missionary, one need, and then over our day.</p></div></li>
</ol>
<p>This simple structure has allowed us to stay connected and to put a stake in the ground: we start every day with God at the center.</p>
<h2 class="guide-h">Time alone with Jesus, at every stage</h2>
<p>Along with family devotions, we wanted to help our children build their own personal devotional life. We knew this would help them walk with Jesus when they were young and would be a habit they could joyfully carry with them into adulthood.</p>
<p>From the day they were born, even while being held in our arms, our kids were with us while we read the Bible, prayed and sought God. We would read the Bible to them and pray for them. As soon as they were old enough to speak, we taught them Scripture, had them memorize it, and helped them begin to understand God.</p>
<p>Each of our kids has time alone with Jesus every morning. When they were little, we started with short Bible story videos. While we spent time with the Lord, they would watch these stories about Jesus, and then we would talk about them together. As they got a little older, we got them large-print kids’ Bibles. They would read, pray, wait on God and learn to hear Him.</p>
<p>At every stage of life we sat side by side with them, helped them get started, and taught them to spend time alone with Jesus. Today, with grown kids who are now raising their own children, it is our joy that they have carried this value with them and are passing it on to our grandkids, not because we ask them to, but because they have found it to be the source of life they need for everything in front of them.</p>
<p class="guide-pull">Remember, your example matters in everything.</p>
<h2 class="guide-h">Don’t Miss Jesus</h2>
<p>The Holiday season was always a whirlwind for us, but family devotions helped us meaningfully encounter God together in the midst of all the events of the season. As you go through these 40 days, you can use these devotionals not only for your personal devotional life, but to fuel your family devotions.</p>
<p>We love you, and we are excited to encounter Jesus with you this Holiday season!</p>
<p class="signoff">Jimmy and Laura</p>
</div>
<aside class="guide-cta"><p class="eyebrow">Starts Monday, Nov 23</p><h2>Use Don’t Miss Jesus as your family’s passage</h2><p>Each morning’s devotional gives you a Scripture, a song and a prayer to share around the table.</p><a class="btn btn-cream" href="/#join">Count Me In</a></aside>
</article>"""
    write('dontmissjesus/family-devotions.html', dmj_shell("How to Do Family Devotions · Don't Miss Jesus", desc, '/dontmissjesus/family-devotions', body, extra=' dmj-page'))

def dmj_list_page(slug, title_script, title_slab, eyebrow, lede, desc, page_title, sections, cta_h, cta_p, lang='en'):
    es = lang == 'es'
    parts = []
    for heading, start, items in sections:
        lis = ''.join(f'<li>{it}</li>' for it in items)
        parts.append(f'<h2 class="guide-h">{heading}</h2>\n<ol class="num-list" start="{start}" style="counter-reset:n {start-1}">{lis}</ol>')
    body = f"""<article class="guide">
<header class="guide-head"><p class="eyebrow">{eyebrow}</p><h1><span class="script">{title_script}</span><span class="slab">{title_slab}</span></h1>
<p class="byline">{'De parte de Jimmy y Laura Seibert' if es else 'From Jimmy and Laura Seibert'}</p>
<p class="lede">{lede}</p>
<button class="btn btn-red print-btn" type="button" onclick="window.print()">{'Imprimir esta lista' if es else 'Print this list'}</button></header>
<div class="guide-body">
{chr(10).join(parts)}
</div>
<aside class="guide-cta"><p class="eyebrow">{'23 de nov. al 1 de ene.' if es else 'Nov 23 to Jan 1'}</p><h2>{cta_h}</h2><p>{cta_p}</p><a class="btn btn-cream" href="{'/es/#join' if es else '/#join'}">{'¡Cuenta conmigo!' if es else 'Count Me In'}</a></aside>
</article>"""
    if es: write(f'es/{slug}.html', dmj_shell(page_title, desc, f'/es/{slug}', body, signup='/es/#join', extra=' dmj-page', lang='es'))
    else: write(f'dontmissjesus/{slug}.html', dmj_shell(page_title, desc, f'/dontmissjesus/{slug}', body, extra=' dmj-page'))

def dmj_top10():
    dmj_list_page('top-10-thanksgiving', 'Top 10 things to do for a', 'Powerful Thanksgiving', 'Thanksgiving',
        'Simple ways to give thanks with God, with the people you love, and around the table.',
        'Ten simple ways to have a powerful Thanksgiving: personally, with your people, and around the table.',
        "Top 10 Things to Do for a Powerful Thanksgiving · Don't Miss Jesus",
        [('Personal', 1, [
            'Journal a list of things you’re thankful for from this past year. <em>One idea is to wake up early and make a list of 10 things.</em>',
            'Ask God to speak to you about His thankfulness to you for things done in the past year. <em>“Lord, where are You proud of me, or what have I done that is honoring and pleasing to You?”</em>',
            'Text an encouragement of gratitude to someone God puts on your heart.']),
         ('People', 4, [
            'Take a walk with a child, spouse or family member. <em>Ask them, “What is one thing you want me to know about your life?” or “What is one thing you’d like to know about my life?”</em>',
            'Ask forgiveness from someone you know you’ve hurt or need to reconcile with.',
            'Be intentional while kids nap or after they go to bed. Get some free time to play a game or worship to a song. Ask how you can pray for each other, and take time to do that.']),
         ('At the table', 7, [
            'Pass around a bowl with creative questions about life, and have each person pick one to answer.',
            'Put a jar in the middle of the table. Have everyone write down two things they’re thankful for on separate strips of paper. Mix them up. Pull out pieces of paper during the meal and guess who wrote what, then have them expound on it.',
            'Highlight a family member (parents or grandparents) to honor them and encourage them.',
            'Play a group game with prizes.'])],
        'Start Thanksgiving week with Don’t Miss Jesus', 'Week one of the 40 days is all about thanksgiving. A short devotional in your inbox every morning at 5 AM.')

def dmj_top20():
    dmj_list_page('top-20-christmas', 'Top 20 ways to have a', 'Joy-Filled Christmas', 'Christmas',
        'Ideas for your own time with God, for your family and the people you gather with, and for Christmas Day.',
        'Twenty ways to have a joy-filled Christmas: personally, with your family, and on Christmas Day around the tree and the table.',
        "Top 20 Ways to Have a Joy-Filled Christmas · Don't Miss Jesus",
        [('Personal', 1, [
            'Start each day of the holidays alone with God. Pray through passages like Psalm 103:1–6 and Isaiah 9:6–7, pausing to be with Jesus as you connect with the One who created you.',
            'Take at least one day to put your phone down. Choose a set time to text or check email, but step away from the constant communication and be present with your family. This season invites us to pause and engage with the love Jesus has for us and our love for one another.',
            'After Christmas, take time to complete the <a href="https://passionandpurpose.kit.com/rolesandgoalsguide">Roles &amp; Goals worksheet</a>.']),
         ('Family and the people I gather with', 4, [
            'Pick a family game to play every day and build on it throughout the holiday. It can be a card game or a board game. Our family finds so much joy and love in doing something fun together.',
            'Join our church family for our Christmas Eve and New Year’s Eve services.',
            'Find someone to give to. Whether it’s an individual or a cause, find someone or something outside your immediate family that you can give to and show Christ’s love to this holiday season.',
            'Watch <em>The Chosen</em> Christmas special.',
            'Have a Christmas cookie decorating or baking contest.',
            'Drive around and look at Christmas lights, and have everyone secretly pick their favorite house. After you get back home, talk about your favorite!',
            'Make or give small Christmas gifts to your mail carrier. This season is busy for them, so look for simple ways to bless them.',
            'Visit a nursing home and sing Christmas carols to the residents as a family or Lifegroup!',
            'Watch <em>The Nativity Story</em> together.',
            'Make a fort and have a family campout in front of the Christmas tree one night. Your back will be sore, but memories will be made!',
            'Pray and ask the Lord to highlight any family members who need special encouragement this season, then reach out to them.']),
         ('Christmas Day around the tree and the table', 15, [
            'Before you open presents on Christmas Day, read the story of Jesus from Luke 2:1–20, sing one Christmas carol together, and pray prayers of gratitude for Jesus.',
            'Read the Christmas story and have family members act out the nativity.',
            'Before each gift is opened, speak encouragement over that person: how God sees them and how they’ve blessed you in 2026.',
            'Share one way each person has been a gift to your life this year.',
            'Sit together and call out the specific “gifts” God has placed in each person, for the whole family to celebrate.',
            'Extra conversation starters:<ul class="guide-list sub"><li>What is one thing you want to do in 2027 that is for the good of someone other than yourself?</li><li>What quality of God are you most thankful for this Christmas?</li><li>What is the best Christmas gift you have ever received?</li><li>Share an encouragement with someone around your table. What is one way they have blessed you or done something meaningful for you in 2026?</li><li>What attribute of God have you been reminded of by a friend or family member in 2026?</li></ul>'])],
        'Make room for Jesus all season', 'Don’t Miss Jesus brings a short devotional to your inbox every morning at 5 AM, all the way to New Year’s Day.')

def dmj_welcome():
    desc = "You're signed up for Don't Miss Jesus. Your first devotional arrives Monday, November 23 at 5 AM."
    body = """<article class="guide welcome">
<header class="guide-head"><div class="red-dot big" aria-hidden="true"></div><p class="eyebrow">You're signed up</p><h1><span class="script">You're</span><span class="slab">In!</span></h1>
<p class="lede" id="when">Your first devotional arrives Monday, November 23 at 5 AM.</p></header>
<div class="guide-body">
<p>We're so glad you're joining us for Don't Miss Jesus. Check your inbox for a welcome email from Jimmy Seibert. If you don't see it in a few minutes, look in your Promotions or Spam folder and move it to your inbox so you don't miss a day.</p>
<ol class="guide-steps">
<li><span class="n">01</span><div><h2>Put a red dot on your phone</h2><p>Let it remind you all season that He holds it all together.</p></div></li>
<li><span class="n">02</span><div><h2>Bring someone with you</h2><p>Invite a friend, roommate or family member to sign up at <a href="/">40daysofdevotion.com</a>.</p></div></li>
<li><span class="n">03</span><div><h2>Do it with your family</h2><p>Read our <a href="/dontmissjesus/family-devotions">simple guide to family devotions</a>, and check out the <a href="/#resources">other resources</a> for Thanksgiving and Christmas.</p></div></li>
</ol>
<p class="guide-pull">We're excited to encounter Jesus with you!</p>
</div>
</article>
<script>(function(){var d=new Date(),start=new Date('2026-11-23T05:00:00-06:00');if(d>=start){var el=document.getElementById('when');if(el)el.textContent='Your next devotional arrives tomorrow at 5 AM.';}})();</script>"""
    write('dontmissjesus/welcome.html', dmj_shell("You're In! · Don't Miss Jesus", desc, '/dontmissjesus/welcome', body, extra=' dmj-page'))

def dmj_family_es():
    desc = "Una manera sencilla de empezar cada día en familia con Dios en el centro: den gracias, lean y conversen, y luego oren."
    body = """<article class="guide">
<header class="guide-head"><p class="eyebrow">Para familias</p><h1><span class="script">Cómo hacer</span><span class="slab">Devocionales en familia</span></h1>
<p class="byline">De parte de Jimmy y Laura Seibert</p>
<p class="lede">“La familia que ora unida permanece unida.” Esta frase sencilla de verdad es cierta.</p></header>
<div class="guide-body">
<p>Cuando criábamos a nuestros hijos, el Señor nos dio la visión de formar una familia de amor, honra y propósito. Los devocionales en familia fueron una parte clave para crear ese ambiente en nuestro hogar. Para nosotros era algo muy sencillo, más o menos así:</p>
<ol class="guide-steps">
<li><span class="n">01</span><div><h2>Den gracias</h2><p>Oramos por el desayuno y luego cada uno cuenta una cosa por la que está agradecido. “Dad gracias en todo, porque esta es la voluntad de Dios para con vosotros en Cristo Jesús.” Queremos formar corazones y actitudes agradecidas, y siempre hay algo por lo cual dar gracias.</p></div></li>
<li><span class="n">02</span><div><h2>Lean y conversen</h2><p>Después compartimos un pasaje de la Biblia o una idea de un devocional, y lo conversamos durante unos cinco minutos.</p></div></li>
<li><span class="n">03</span><div><h2>Oren</h2><p>Normalmente oramos por un misionero, por una necesidad y luego por nuestro día.</p></div></li>
</ol>
<p>Esta estructura sencilla nos ha permitido mantenernos conectados y tomar una decisión firme: empezamos cada día con Dios en el centro.</p>
<h2 class="guide-h">Tiempo a solas con Jesús, en cada etapa</h2>
<p>Además de los devocionales en familia, quisimos ayudar a nuestros hijos a formar su propia vida devocional. Sabíamos que esto les ayudaría a caminar con Jesús desde pequeños y que sería un hábito que podrían llevar con alegría a su vida adulta.</p>
<p>Desde el día en que nacieron, incluso cuando los teníamos en brazos, nuestros hijos estaban con nosotros mientras leíamos la Biblia, orábamos y buscábamos a Dios. Les leíamos la Biblia y orábamos por ellos. En cuanto tuvieron edad para hablar, les enseñamos la Palabra, les ayudamos a memorizarla y a empezar a entender a Dios.</p>
<p>Cada uno de nuestros hijos tiene un tiempo a solas con Jesús cada mañana. Cuando eran pequeños, empezamos con videos cortos de historias bíblicas. Mientras nosotros pasábamos tiempo con el Señor, ellos veían estas historias de Jesús, y luego las conversábamos juntos. Cuando crecieron un poco, les dimos Biblias para niños con letra grande. Leían, oraban, esperaban en Dios y aprendían a escuchar Su voz.</p>
<p>En cada etapa de la vida nos sentamos a su lado, les ayudamos a empezar y les enseñamos a pasar tiempo a solas con Jesús. Hoy, con hijos adultos que ya crían a sus propios hijos, nos da mucha alegría ver que han llevado este valor consigo y lo están pasando a nuestros nietos. No lo hacen porque se lo pidamos, sino porque han descubierto que es la fuente de vida que necesitan para todo lo que tienen por delante.</p>
<p class="guide-pull">Recuerda: tu ejemplo importa en todo.</p>
<h2 class="guide-h">No te pierdas a Jesús</h2>
<p>La temporada navideña siempre era un torbellino para nosotros, pero los devocionales en familia nos ayudaron a encontrarnos con Dios juntos, de manera significativa, en medio de todas las actividades de la temporada. Durante estos 40 días, puedes usar estos devocionales no solo para tu vida devocional personal, sino también para alimentar los devocionales de tu familia.</p>
<p>¡Te amamos, y estamos emocionados de encontrarnos con Jesús contigo en esta temporada navideña!</p>
<p class="signoff">Jimmy y Laura</p>
</div>
<aside class="guide-cta"><p class="eyebrow">Comienza el lunes 23 de nov.</p><h2>Usa No te pierdas a Jesús como el pasaje de tu familia</h2><p>El devocional de cada mañana te da un pasaje, una canción y una oración para compartir en la mesa. Por ahora, los devocionales diarios llegan en inglés.</p><a class="btn btn-cream" href="/es/#join">¡Cuenta conmigo!</a></aside>
</article>"""
    write('es/devocionales-en-familia.html', dmj_shell("Cómo hacer devocionales en familia · No te pierdas a Jesús", desc, '/es/devocionales-en-familia', body, signup='/es/#join', extra=' dmj-page', lang='es'))

def dmj_top10_es():
    dmj_list_page('accion-de-gracias', '10 cosas para un', 'Día de Acción de Gracias poderoso', 'Acción de Gracias',
        'Maneras sencillas de dar gracias con Dios, con las personas que amas y alrededor de la mesa.',
        'Diez maneras sencillas de tener un Día de Acción de Gracias poderoso: a solas, con tu gente y alrededor de la mesa.',
        "10 cosas para un Día de Acción de Gracias poderoso · No te pierdas a Jesús",
        [('A solas', 1, [
            'Escribe en un diario una lista de cosas por las que estás agradecido este último año. <em>Una idea es levantarte temprano y hacer una lista de 10 cosas.</em>',
            'Pídele a Dios que te hable de Su gratitud hacia ti por cosas que hiciste este año. <em>“Señor, ¿en qué estás orgulloso de mí, o qué he hecho que te honra y te agrada?”</em>',
            'Envíale un mensaje de gratitud y ánimo a alguien que Dios ponga en tu corazón.']),
         ('Con tu gente', 4, [
            'Sal a caminar con un hijo, tu cónyuge o un familiar. <em>Pregúntale: “¿Qué es algo de tu vida que quieres que yo sepa?” o “¿Qué es algo que te gustaría saber de mi vida?”</em>',
            'Pide perdón a alguien que sabes que has lastimado o con quien necesitas reconciliarte.',
            'Aprovecha con intención la siesta de los niños o el rato después de que se duermen. Busca un tiempo libre para jugar algo o adorar con una canción. Pregúntense cómo pueden orar el uno por el otro, y tomen tiempo para hacerlo.']),
         ('Alrededor de la mesa', 7, [
            'Pasen un tazón con preguntas creativas sobre la vida, y que cada persona escoja una para responder.',
            'Pongan un frasco en el centro de la mesa. Que cada uno escriba dos cosas por las que está agradecido en tiras de papel separadas. Mézclenlas. Durante la comida, saquen los papelitos, adivinen quién escribió cada uno y pídanle que cuente más.',
            'Escojan a un miembro de la familia (padres o abuelos) para honrarlo y animarlo.',
            'Jueguen un juego en grupo con premios.'])],
        'Empieza la semana de Acción de Gracias con No te pierdas a Jesús', 'La primera semana de los 40 días se trata de dar gracias. Un devocional breve en tu correo cada mañana a las 5 AM (por ahora, en inglés).', lang='es')

def dmj_top20_es():
    dmj_list_page('navidad', '20 maneras de tener una', 'Navidad llena de gozo', 'Navidad',
        'Ideas para tu tiempo a solas con Dios, para tu familia y las personas con quienes te reúnes, y para el día de Navidad.',
        'Veinte maneras de tener una Navidad llena de gozo: a solas, en familia y el día de Navidad alrededor del árbol y la mesa.',
        "20 maneras de tener una Navidad llena de gozo · No te pierdas a Jesús",
        [('A solas', 1, [
            'Empieza cada día de las fiestas a solas con Dios. Ora con pasajes como Salmo 103:1–6 e Isaías 9:6–7, deteniéndote para estar con Jesús mientras te conectas con Aquel que te creó.',
            'Toma por lo menos un día para dejar tu teléfono. Escoge un horario fijo para revisar mensajes o correos, pero apártate de la comunicación constante y está presente con tu familia. Esta temporada nos invita a hacer una pausa y recibir el amor que Jesús tiene por nosotros y el amor que nos tenemos unos a otros.',
            'Después de Navidad, toma tiempo para completar la <a href="https://passionandpurpose.kit.com/rolesandgoalsguide" hreflang="en">hoja de Roles y Metas</a> (en inglés).']),
         ('En familia y con las personas con quienes me reúno', 4, [
            'Escojan un juego familiar para jugar todos los días y sigan con él durante las fiestas. Puede ser de cartas o de mesa. Nuestra familia encuentra mucho gozo y amor en hacer algo divertido juntos.',
            'Únete a nuestra familia de la iglesia en los servicios de Nochebuena y de Fin de Año.',
            'Busca a alguien a quien dar. Ya sea una persona o una causa, busca a alguien o algo fuera de tu familia inmediata a quien puedas dar y mostrarle el amor de Cristo en esta temporada.',
            'Vean el especial de Navidad de <em>The Chosen</em>.',
            'Hagan un concurso de decorar u hornear galletas navideñas.',
            'Salgan en el carro a ver las luces de Navidad, y que cada uno escoja en secreto su casa favorita. Al volver a casa, ¡cuenten cuál fue su favorita!',
            'Hagan o regalen pequeños obsequios de Navidad a su cartero. Esta temporada es muy ocupada para ellos, así que busquen maneras sencillas de bendecirlos.',
            '¡Visiten un asilo de ancianos y cántenles villancicos a los residentes en familia o con su Lifegroup!',
            'Vean juntos la película <em>Natividad</em> (<em>The Nativity Story</em>).',
            'Hagan un fuerte y acampen en familia una noche frente al árbol de Navidad. Les va a doler la espalda, ¡pero crearán recuerdos!',
            'Oren y pídanle al Señor que les muestre qué familiares necesitan un ánimo especial esta temporada, y luego comuníquense con ellos.']),
         ('El día de Navidad alrededor del árbol y la mesa', 15, [
            'Antes de abrir los regalos el día de Navidad, lean la historia de Jesús en Lucas 2:1–20, canten juntos un villancico y oren dando gracias por Jesús.',
            'Lean la historia de Navidad y que los miembros de la familia representen el nacimiento.',
            'Antes de abrir cada regalo, digan palabras de ánimo sobre esa persona: cómo la ve Dios y cómo los ha bendecido a ustedes en 2026.',
            'Compartan una manera en que cada persona ha sido un regalo en su vida este año.',
            'Siéntense juntos y nombren los “regalos” específicos que Dios ha puesto en cada persona, para que toda la familia los celebre.',
            'Más preguntas para conversar:<ul class="guide-list sub"><li>¿Qué es algo que quieres hacer en 2027 para el bien de alguien más?</li><li>¿Por cuál cualidad de Dios estás más agradecido esta Navidad?</li><li>¿Cuál es el mejor regalo de Navidad que has recibido?</li><li>Anima a alguien en tu mesa. ¿De qué manera te ha bendecido o ha hecho algo significativo por ti en 2026?</li><li>¿Qué atributo de Dios te ha recordado un amigo o familiar en 2026?</li></ul>'])],
        'Hazle lugar a Jesús toda la temporada', 'No te pierdas a Jesús te lleva un devocional breve a tu correo cada mañana a las 5 AM, hasta el Día de Año Nuevo (por ahora, en inglés).', lang='es')

def dmj_welcome_es():
    desc = "Ya estás inscrito en No te pierdas a Jesús. Tu primer devocional llega el lunes 23 de noviembre a las 5 AM."
    body = """<article class="guide welcome">
<header class="guide-head"><div class="red-dot big" aria-hidden="true"></div><p class="eyebrow">Ya estás inscrito</p><h1><span class="script">¡Ya</span><span class="slab">estás!</span></h1>
<p class="lede" id="when">Tu primer devocional llega el lunes 23 de noviembre a las 5 AM.</p></header>
<div class="guide-body">
<p>Qué alegría que te unas a nosotros en No te pierdas a Jesús. Revisa tu correo: te enviamos un mensaje de bienvenida de Jimmy Seibert. Si no lo ves en unos minutos, búscalo en Promociones o Spam y muévelo a tu bandeja de entrada para que no te pierdas ningún día. Por ahora, los devocionales diarios llegan en inglés.</p>
<ol class="guide-steps">
<li><span class="n">01</span><div><h2>Pon un punto rojo en tu teléfono</h2><p>Que te recuerde toda la temporada que Él lo sostiene todo.</p></div></li>
<li><span class="n">02</span><div><h2>Invita a alguien</h2><p>Invita a un amigo, compañero de cuarto o familiar a inscribirse en <a href="/es/">40daysofdevotion.com/es</a>.</p></div></li>
<li><span class="n">03</span><div><h2>Hazlo en familia</h2><p>Lee nuestra <a href="/es/devocionales-en-familia">guía sencilla para devocionales en familia</a> y mira los <a href="/es/#resources">otros recursos</a> para Acción de Gracias y Navidad.</p></div></li>
</ol>
<p class="guide-pull">¡Estamos emocionados de encontrarnos con Jesús contigo!</p>
</div>
</article>
<script>(function(){var d=new Date(),start=new Date('2026-11-23T05:00:00-06:00');if(d>=start){var el=document.getElementById('when');if(el)el.textContent='Tu próximo devocional llega mañana a las 5 AM.';}})();</script>"""
    write('es/bienvenido.html', dmj_shell("¡Ya estás inscrito! · No te pierdas a Jesús", desc, '/es/bienvenido', body, signup='/es/#join', extra=' dmj-page', lang='es'))

def dmj_home():
    desc = "Sign up for a free 40 day devotional to help you experience Jesus this Holiday season."
    weeks = ''.join(f'''<li class="week">{'<a class="week-link" href="/dontmissjesus/week-' + str(i+1) + '">' if i + 1 in DMJ_WEEK_PAGES else ''}<div class="candy"></div><div class="week-body"><div class="meta"><span>WEEK {i+1}</span><span>DAYS {a}–{b}</span></div><h3>{t}</h3><span class="when">{w}</span>{'<span class="go">See the week →</span>' if i + 1 in DMJ_WEEK_PAGES else ''}</div>{'</a>' if i + 1 in DMJ_WEEK_PAGES else ''}</li>''' for i, (t, a, b, w) in enumerate(DMJ_WEEKS))
    body = f'''<section class="hero"><div class="hero-box"><div class="hero-inner">
<div class="hero-copy">
<p class="eyebrow dates">Nov 23 to Jan 1 · 40 Days</p>
<h1><span class="slab">DON'T MISS</span><span class="script">Jesus</span></h1>
<p class="lede">{desc}</p>
<form class="hero-form" id="join" action="{DMJ_FORM}" method="post">
<label class="sr" for="hero-name">First name</label><input id="hero-name" name="fields[first_name]" placeholder="First name" autocomplete="given-name" required>
<label class="sr" for="hero-email">Email</label><input id="hero-email" type="email" name="email_address" placeholder="Email" autocomplete="email" required>
<button type="submit">Count Me In</button>
</form>
</div>
<div class="phone" aria-hidden="true"><div class="phone-body"><div class="phone-dot"></div><div class="phone-screen">
<span class="phone-date">Monday, November 23</span><span class="phone-time">5:00</span>
<div class="phone-note"><div class="app"><span>DON'T MISS JESUS</span><span>now</span></div><strong>Day 1 · Thanksgiving</strong><p>Give thanks to the Lord, for He is good. Today's devotional is ready.</p></div>
</div></div></div>
</div></div><div class="stripe hero-stripe"></div></section>
<section class="verse"><div class="red-dot" aria-hidden="true"></div>
<blockquote>“He is before all things, and in Him all things hold together… so that He Himself will come to have first place in everything.”</blockquote>
<p class="eyebrow ref">Colossians 1:17–18</p>
<p class="dot-note">This season is full. In all of it, there is one thing not to miss.</p></section>
<section class="sec weeks" id="weeks"><div class="sec-head"><p class="eyebrow">Six weeks, one King</p><h2 class="script">The weeks</h2><p>Each week of the season has its own theme, from Thanksgiving to the new year.</p></div>
<ol class="rail">{weeks}</ol>{dots(6)}</section>
<section class="signup grid-bg" id="signup"><div class="signup-box">
<div class="signup-side"><div><p class="eyebrow">Starts Monday, Nov 23</p><h2>One email.<br>Every morning.<br>Forty days.</h2></div><p>Thanksgiving week to New Year's Day</p></div>
<form action="{DMJ_FORM}" method="post">
<h2>Count me in</h2>
<div class="fields"><div class="field"><label for="dmj-name">First name</label><input id="dmj-name" name="fields[first_name]" autocomplete="given-name" required></div>
<div class="field"><label for="dmj-email">Email</label><input id="dmj-email" type="email" name="email_address" autocomplete="email" required></div></div>
<button type="submit">SIGN ME UP</button>
<p class="fine">One email a day, Nov 23 to Jan 1, from Antioch Waco. Unsubscribe anytime. We'll never share your email.</p>
</form></div></section>
<section class="sec" id="resources"><div class="sec-head"><p class="eyebrow">More for the season</p><h2 class="slab">Other resources</h2></div>
<div class="res">
<a class="playlist" href="/dontmissjesus/family-devotions"><p class="eyebrow">For families</p><h3>Family devotions</h3><p>A simple way to start each morning with God at the center: give thanks, read and talk, then pray together.</p><span class="go">Read the guide →</span></a>
<ul class="res-list">
<li class="res-item"><div class="art art-dot" aria-hidden="true"><span></span></div><div class="body"><span class="eyebrow">40 days of songs</span><h3>The playlist</h3><p>One song for every day of Don’t Miss Jesus, from “Gratitude” to “Doxology.”</p><a class="go" href="https://open.spotify.com/playlist/3zKOYFC8yjDHfWAfFUlsB9">Open in Spotify →</a></div></li>
<li class="res-item"><div class="art candy" aria-hidden="true"></div><div class="body"><span class="eyebrow">Thanksgiving</span><h3>Top 10 things to do for a powerful Thanksgiving</h3><p>Ideas for you personally, with the people you love, and around the table.</p><a class="go" href="/dontmissjesus/top-10-thanksgiving">See the list →</a></div></li>
<li class="res-item"><div class="art stripe" aria-hidden="true"></div><div class="body"><span class="eyebrow">Christmas</span><h3>Top 20 ways to have a joy-filled Christmas</h3><p>Ideas for your own time with God, your family, and Christmas Day around the tree and the table.</p><a class="go" href="/dontmissjesus/top-20-christmas">See the list →</a></div></li>
<li class="res-item"><div class="art grid-bg" aria-hidden="true"></div><div class="body"><span class="eyebrow">New Year</span><h3>30-Day Journal</h3><p>Look back on 2026, pray over 2027 and plan your next step in the Word.</p><a class="go" href="https://30dayjournal.com/">Get the journal →</a></div></li>
</ul></div></section>'''
    page = dmj_shell("Don't Miss Jesus · 40 Days of Devotion", desc, '/', body, '#join')
    write('index.html', page)

DMJ_WEEKS_ES = [('Acción de Gracias', '23 al 29 de nov.'), ('Esperanza', '30 de nov. al 6 de dic.'), ('Paz', '7 al 13 de dic.'),
                ('Gozo', '14 al 20 de dic.'), ('Amor', '21 al 27 de dic.'), ('Gracia', '28 de dic. al 1 de ene.')]

def dmj_home_es():
    """Spanish version of the Don't Miss Jesus home page, at /es/.
    Sign-ups go to the same Kit form, with the custom field Language = es so Spanish speakers
    can be found in Kit (filter or segment on Language). The daily emails are in English for now."""
    desc = "Inscríbete gratis en un devocional de 40 días que te ayudará a encontrarte con Jesús en esta temporada navideña."
    weeks = ''.join(f'''<li class="week">{'<a class="week-link" href="/es/dia-1">' if i == 0 else ''}<div class="candy"></div><div class="week-body"><div class="meta"><span>SEMANA {i+1}</span><span>DÍAS {a}–{b}</span></div><h3>{DMJ_WEEKS_ES[i][0]}</h3><span class="when">{DMJ_WEEKS_ES[i][1]}</span>{'<span class="go">Comienza el Día 1 →</span>' if i == 0 else ''}</div>{'</a>' if i == 0 else ''}</li>''' for i, (t, a, b, w) in enumerate(DMJ_WEEKS))
    lang_field = '<input type="hidden" name="fields[language]" value="es">'
    body = f'''<section class="hero"><div class="hero-box"><div class="hero-inner">
<div class="hero-copy">
<p class="eyebrow dates">23 de nov. al 1 de ene. · 40 días</p>
<h1><span class="slab">NO TE PIERDAS A</span><span class="script">Jesús</span></h1>
<p class="lede">{desc}</p>
<form class="hero-form" id="join" action="{DMJ_FORM_ES}" data-next="/es/bienvenido" method="post">{lang_field}
<label class="sr" for="hero-name">Nombre</label><input id="hero-name" name="fields[first_name]" placeholder="Nombre" autocomplete="given-name" required>
<label class="sr" for="hero-email">Correo electrónico</label><input id="hero-email" type="email" name="email_address" placeholder="Correo" autocomplete="email" required>
<button type="submit">¡Cuenta conmigo!</button>
</form>
</div>
<div class="phone" aria-hidden="true"><div class="phone-body"><div class="phone-dot"></div><div class="phone-screen">
<span class="phone-date">Lunes, 23 de noviembre</span><span class="phone-time">5:00</span>
<div class="phone-note"><div class="app"><span>NO TE PIERDAS A JESÚS</span><span>ahora</span></div><strong>Día 1 · Acción de Gracias</strong><p>Da gracias al Señor, porque Él es bueno. Tu devocional de hoy ya está listo.</p></div>
</div></div></div>
</div></div><div class="stripe hero-stripe"></div></section>
<section class="verse"><div class="red-dot" aria-hidden="true"></div>
<blockquote>“Y él es antes de todas las cosas, y todas las cosas en él subsisten… para que en todo tenga la preeminencia.”</blockquote>
<p class="eyebrow ref">Colosenses 1:17–18 (RVR1960)</p>
<p class="dot-note">Esta temporada está llena de cosas. En medio de todo, hay una que no te puedes perder.</p></section>
<section class="sec weeks" id="weeks"><div class="sec-head"><p class="eyebrow">Seis semanas, un Rey</p><h2 class="script">Las semanas</h2><p>Cada semana de la temporada tiene su propio tema, desde Acción de Gracias hasta el Año Nuevo.</p></div>
<ol class="rail">{weeks}</ol>{dots(6)}</section>
<section class="signup grid-bg" id="signup"><div class="signup-box">
<div class="signup-side"><div><p class="eyebrow">Comienza el lunes 23 de nov.</p><h2>Un correo.<br>Cada mañana.<br>Cuarenta días.</h2></div><p>De la semana de Acción de Gracias al Día de Año Nuevo</p></div>
<form action="{DMJ_FORM_ES}" data-next="/es/bienvenido" method="post">{lang_field}
<h2>Cuenta conmigo</h2>
<div class="fields"><div class="field"><label for="dmj-name">Nombre</label><input id="dmj-name" name="fields[first_name]" autocomplete="given-name" required></div>
<div class="field"><label for="dmj-email">Correo electrónico</label><input id="dmj-email" type="email" name="email_address" autocomplete="email" required></div></div>
<button type="submit">INSCRÍBEME</button>
<p class="fine">Un correo al día, del 23 de nov. al 1 de ene., de parte de Antioch Waco. Por ahora, los devocionales diarios llegan en inglés. Puedes darte de baja cuando quieras. Nunca compartiremos tu correo.</p>
</form></div></section>
<section class="sec" id="resources"><div class="sec-head"><p class="eyebrow">Más para la temporada</p><h2 class="slab">Otros recursos</h2></div>
<div class="res">
<a class="playlist" href="/es/devocionales-en-familia"><p class="eyebrow">Para familias</p><h3>Devocionales en familia</h3><p>Una manera sencilla de empezar cada mañana con Dios en el centro: den gracias, lean y conversen, y luego oren juntos.</p><span class="go">Lee la guía →</span></a>
<ul class="res-list">
<li class="res-item"><div class="art art-dot" aria-hidden="true"><span></span></div><div class="body"><span class="eyebrow">40 días de canciones</span><h3>La lista de canciones</h3><p>Una canción para cada día de No te pierdas a Jesús, desde “Gratitude” hasta “Doxology.”</p><a class="go" href="https://open.spotify.com/playlist/3zKOYFC8yjDHfWAfFUlsB9">Abrir en Spotify →</a></div></li>
<li class="res-item"><div class="art candy" aria-hidden="true"></div><div class="body"><span class="eyebrow">Acción de Gracias</span><h3>10 cosas para un Día de Acción de Gracias poderoso</h3><p>Ideas para ti, para las personas que amas y para la mesa.</p><a class="go" href="/es/accion-de-gracias">Ver la lista →</a></div></li>
<li class="res-item"><div class="art stripe" aria-hidden="true"></div><div class="body"><span class="eyebrow">Navidad</span><h3>20 maneras de tener una Navidad llena de gozo</h3><p>Ideas para tu tiempo a solas con Dios, para tu familia y para el día de Navidad alrededor del árbol y la mesa.</p><a class="go" href="/es/navidad">Ver la lista →</a></div></li>
<li class="res-item"><div class="art grid-bg" aria-hidden="true"></div><div class="body"><span class="eyebrow">Año Nuevo · en inglés</span><h3>Diario de 30 días</h3><p>Mira hacia atrás a 2026, ora por 2027 y planea tu próximo paso en la Palabra.</p><a class="go" href="https://30dayjournal.com/" hreflang="en">Consigue el diario →</a></div></li>
</ul></div></section>'''
    write('es/index.html', dmj_shell("No te pierdas a Jesús · 40 Days of Devotion", desc, '/es/', body, '#join', lang='es'))

def devotion_landing():
    groups = ''.join(f'''<div class="group"><div class="group-head"><h3>{s}</h3><span>Days {a} to {b}</span></div>
<ol class="day-list">{day_rows([x for x in DEV if a <= x[0] <= b], "/devos/")}</ol></div>''' for s, a, b in SECTIONS)
    day1 = f'/devos/{DEV[0][1]["slug"]}'
    book = (f'<a class="btn btn-outline" href="{BOOK_URL}">Get the book</a>' if BOOK_URL
            else '<p class="soon">Link coming soon</p>')
    body = f'''<section class="photo-hero" style="background-image:url('{photo(HERO_PHOTO)}')">
<div class="photo-hero-inner">
<p class="eyebrow">A 40 Day Journey</p>
<h1>40 Days of Devotion</h1>
<p class="lede">A daily devotional to help you start, strengthen or reignite the daily habit of spending time with the Lord.</p>
</div>
</section>
<section class="ways" id="ways">
<h2>Three ways to take the journey</h2>
<p class="sub">Same forty days. Choose the one that fits your mornings.</p>
<div class="ways-track">
{way(0, 'Trail 1 · Free', 'Read it here', 'All forty days are on this site. Start whenever you like and walk at your own pace.', f'<a class="btn btn-outline" href="{day1}">Start with Day 1</a>')}
{way(1, 'Trail 2 · Free', 'Get it by email', 'One devotional in your inbox each morning, forty days in a row.', f'<a class="btn" href="{KIT_DEVOTION}">Sign up for the daily email</a>')}
{way(2, 'Trail 3 · Print', 'Get the book', 'The printed edition, for a quiet morning with a pen in hand.', book)}
</div>
</section>
<section class="days" id="days"><h2>The 40 Days</h2>{groups}</section>
<p class="deeper">Want to go deeper? The Face to Face teaching series and the Alone With God guidebook are on the <a href="/resources">Resources page</a>.</p>
<section class="closing"><blockquote>“Abide in Me, and I in you. As the branch cannot bear fruit of itself unless it abides in the vine, so neither can you unless you abide in Me.”</blockquote><p class="ref">John 15:4</p></section>'''
    page = shell('40 Days of Devotion', 'A daily devotional to help you start, strengthen or reignite the daily habit of spending time with the Lord.', '/devotion', body,
                 photo(HERO_PHOTO, 1200, share=True), KIT_DEVOTION, overlay=True)
    write('devotion.html', page)
    if not DMJ_SEASON: write('index.html', page)   # outside the Don't Miss Jesus season the home page is the devotion landing page

def notices():
    write('whats-next.html', shell('You are all signed up! · 40 Days of Devotion', 'You are signed up for 40 Days of Devotion.', '/whats-next',
        '<section class="notice"><h1>You are all signed up!</h1><p>Each morning at 3am (starting tomorrow morning) you will receive a link in your inbox to the devotional for that day!</p><a class="btn" href="/devotion#days">See all 40 days</a></section>'))
    write('404.html', shell('Page not found · 40 Days of Devotion', 'Page not found.', '/404',
        '<section class="notice"><h1>Page not found</h1><p>The page you were looking for isn’t here anymore. All 40 days of the devotional are still on the site.</p><a class="btn" href="/devotion#days">See all 40 days</a></section>'))


# ---------- Don't Miss Jesus day pages ----------
def dmj_photo(name):
    """Photo URL with a content hash, so a replaced photo is never served from cache."""
    import hashlib
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'photos', 'dmj', name)
    try:
        h = hashlib.md5(open(fp, 'rb').read()).hexdigest()[:8]
        return f'/photos/dmj/{name}?v={h}'
    except OSError:
        return f'/photos/dmj/{name}'

# Content: content/dontmissjesus/week1.json (from the Week 1 doc). Photos: /photos/dmj/day-NN.webp (+ -share.jpg for link previews).
# Layout follows the "Single post" mockup: title, photo, Word, Scriptures for Today, Worship, Pray (+ "Write down 7"), Listen & Obey.
DMJ_FOCUS = {1: '50% 80%', 2: '50% 55%', 4: '50% 45%', 5: '50% 50%', 6: '50% 0%', 7: '50% 12%'}   # where each photo is cropped (x% y%)
DMJ_WEEK_PAGES = {1}   # weeks that have a week page (/dontmissjesus/week-N)
DMJ_TR = {'nasb': 'NASB1995', 'esv': 'ESV', 'nkjv': 'NKJV', 'bsb': 'BSB'}
DMJ_DAY_JS = """<script>document.querySelectorAll('.dmj-video').forEach(function(v){v.addEventListener('click',function(){var f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+v.dataset.id+'?autoplay=1&rel=0';f.title=v.dataset.title;f.allow='autoplay; encrypted-media; picture-in-picture';f.allowFullscreen=true;v.replaceWith(f)})});
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){var t=b.dataset.copy,done=function(){var o=b.textContent;b.textContent='Link copied';setTimeout(function(){b.textContent=o},2000)};if(navigator.share&&matchMedia('(pointer:coarse)').matches){navigator.share({title:"Don't Miss Jesus",url:t}).catch(function(){});return}if(navigator.clipboard)navigator.clipboard.writeText(t).then(done);else prompt('Copy this link:',t)})});</script>"""


DMJ_SERMONS = {1: dict(yt='7bI6LEwcPmA', date='Sunday, Nov 22', title='The launch message', who='Jimmy Seibert')}
DMJ_WEEK_RES = {1: [('candy', 'For Thanksgiving', 'Top 10 things to do for a powerful Thanksgiving', 'Ideas for you personally, with the people you love, and around the table.', '/dontmissjesus/top-10-thanksgiving', 'See the list →'),
                     ('stripe-sq', 'For families', 'How to do family devotions', 'A simple way to start each morning with God at the center: give thanks, read and talk, then pray together.', '/dontmissjesus/family-devotions', 'Read the guide →')]}
DMJ_WEEK_INTRO = {}   # optional intro under the week title, e.g. {2: "..."}

def dmj_week(n, days):
    theme, a, b, when = DMJ_WEEKS[n-1]
    pills = ''.join((f'<a class="pill on" href="/dontmissjesus/week-{i+1}" aria-current="page">{i+1} · {t}</a>' if i + 1 == n else
                     f'<a class="pill" href="/dontmissjesus/week-{i+1}">{i+1} · {t}</a>' if i + 1 in DMJ_WEEK_PAGES else
                     f'<span class="pill off">{i+1} · {t}</span>') for i, (t, *_r) in enumerate(DMJ_WEEKS))
    s = DMJ_SERMONS.get(n)
    sermon = ''
    if s:
        sermon = f"""<section class="wk-sermon"><div class="wrap-900">
<div class="wk-sermon-head"><div><p class="kicker"><span class="red-dot" aria-hidden="true"></span>Sunday's message · {esc(s['date'])}</p><h2>{esc(s['title'])}</h2><p class="who">{esc(s['who'])} · Antioch Waco</p></div>
<p class="script">This message launched {esc(theme)} week</p></div>
<button class="dmj-video" type="button" data-id="{s['yt']}" data-title="{esc(s['title'])}" aria-label="Play Sunday's message"><img src="https://i.ytimg.com/vi/{s['yt']}/hqdefault.jpg" alt="" loading="lazy"><span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="#FFFDF8"/></svg></span></button>
<div class="wk-sermon-foot"><p>Missed Sunday? Start here. This week's seven devos build on this message.</p>
<div class="row"><a class="btn btn-cream" href="https://www.youtube.com/watch?v={s['yt']}">Watch on YouTube</a><button class="btn btn-line" type="button" data-copy="https://www.youtube.com/watch?v={s['yt']}">Share the message</button></div></div>
</div></section>"""
    rows = ''
    for d in days:
        rows += f"""<li><a class="wk-day" href="/dontmissjesus/day-{d['n']}" data-date="{d['date']}" data-open="{esc(d['day'].split(',')[0][:3] + ', ' + d['day'].split(', ')[1])}">
<span class="num"><span>Day</span><b>{d['n']}</b></span><span class="info"><span class="when"><span class="today-tag">Today · </span>{esc(d['day'])}{(' · ' + esc(d['tag'])) if d.get('tag') else ''}</span><span class="t">{esc(d['title'])}</span><span class="sub">{esc(d['ref'])} · Song: {esc(d['song'])}</span><span class="opens">Opens {esc(d['day'])} at 5:00 AM</span></span>
<span class="go"><span class="read">Read →</span><span class="now">Read now</span><svg class="lock" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg></span></a></li>"""
    songs = ''.join(f'<li><a href="https://www.youtube.com/watch?v={d["yt"]}"><b>{esc(d["song"])}</b> · {esc(d["artist"])}</a></li>' for d in days)
    res = ''.join(f'<a class="card wk-res" href="{h}"><div class="{art}" aria-hidden="true"></div><div><p class="kicker">{esc(k)}</p><h3>{esc(t)}</h3><p class="desc">{esc(dsc)}</p><span class="wk-go">{go}</span></div></a>' for art, k, t, dsc, h, go in DMJ_WEEK_RES.get(n, []))
    nxt = DMJ_WEEKS[n] if n < len(DMJ_WEEKS) else None
    prev_a = (f'<a class="prev" href="/dontmissjesus/week-{n-1}"><span class="k">← Week {n-1}</span><span class="script">{DMJ_WEEKS[n-2][0]}</span></a>' if n > 1
              else '<a class="prev" href="/#weeks"><span class="k">← All six weeks</span><span class="script">The plan</span></a>')
    next_a = ''
    if nxt:
        href = f'/dontmissjesus/week-{n+1}' if n + 1 in DMJ_WEEK_PAGES else '/#weeks'
        next_a = f'<a class="next" href="{href}"><span class="k">Week {n+1} · starts {nxt[3].split(" to ")[0]} →</span><span class="script">{nxt[0]}</span></a>'
    body = f"""<div class="stripe" aria-hidden="true"></div>
<nav class="wk-pills" aria-label="Weeks">{pills}</nav>
<section class="wk-hero grid-bg"><div class="wk-box"><div class="wk-box-in">
<p class="eyebrow">Week {n} · Days {a}–{b}</p><h1 class="script">{esc(theme)}</h1><p class="eyebrow dates">{esc(days[0]['day'].split(',')[0][:3])} {esc(days[0]['day'].split(', ')[1])} · {esc(days[-1]['day'].split(',')[0][:3])} {esc(days[-1]['day'].split(', ')[1])}</p>
{f'<p class="lede">{esc(DMJ_WEEK_INTRO[n])}</p>' if n in DMJ_WEEK_INTRO else ''}</div></div></section>
{sermon}
<section class="wk-days"><div class="wrap-900"><div class="wk-days-head"><h2>This week's devos</h2></div>
<ol class="wk-list">{rows}</ol></div></section>
<section class="wk-songs"><div class="wrap-900"><div class="card"><div class="stripe-sq" aria-hidden="true"></div><div><p class="kicker">{esc(theme)} week songs</p><h3>7 songs for the week</h3><ol>{songs}</ol></div></div>{res}</div></section>
<nav class="wk-nav" aria-label="Previous and next week"><div class="wrap-900">{prev_a}{next_a}</div></nav>
<section class="day-strip"><div><p class="script">Never miss a day</p><p>Get each devotional in your inbox every morning.</p></div><a class="btn btn-cream" href="/#join">Sign me up</a></section>"""
    js = """<script>(function(){var t=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
document.querySelectorAll('.wk-day').forEach(function(a){var d=a.dataset.date;var li=a.parentNode;if(d<t)li.className='past';else if(d===t)li.className='today';else li.className='upcoming'})})();</script>"""
    desc = f"Don't Miss Jesus, week {n}: {theme}. Seven short devotionals, Days {a}–{b}, plus Sunday's message."
    write(f'dontmissjesus/week-{n}.html', dmj_shell(f"Week {n}: {theme} · Don't Miss Jesus", desc, f'/dontmissjesus/week-{n}', body + DMJ_DAY_JS + js,
          extra=' dmj-page dmj-week', image=dmj_photo(f'day-{a:02d}-share.jpg'), image_alt=f'{theme} week'))
    return f'/dontmissjesus/week-{n}'

def dmj_days():
    DMJ_PAIRS.extend((f'/dontmissjesus/day-{k}', f'/es/dia-{k}') for k in range(1, 8))
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'dontmissjesus', 'week1.json')))
    days, cr = data['days'], data['credits']
    out = []
    for i, d in enumerate(days):
        n = d['n']; path = f'/dontmissjesus/day-{n}'
        week = next(w for w in DMJ_WEEKS if w[1] <= n <= w[2])
        tag = f'<span class="sep brk">·</span><span>{esc(d["tag"])}</span>' if d.get('tag') else ''
        scrip = ''.join(f'<p class="passage"><span class="ref">{esc(x["ref"])}</span> {esc(x["text"])}</p>' for x in d['scriptures'])
        used = {}
        for x in d['scriptures']:
            if x['tr'] != 'nasb': used.setdefault(x['tr'], []).append(x['ref'])
        credit = [f'{cr["nasb"]} <a href="https://www.lockman.org">lockman.org</a>']
        for k in ('esv', 'nkjv', 'bsb'):
            if k in used:
                refs = '; '.join(used[k]); text = cr[k]
                credit.append(f'{esc(refs)}: {"taken from the " if k != "bsb" else ""}{esc(text)}')
        listen = ''.join(f'<li>{esc(q)}</li>' for q in d['listen'])
        invite = ''
        if n == 1:
            invite = f"""<aside class="day-invite"><p class="label">Invite a friend</p><p>Who could do these 40 days with you? Text your Lifegroup, your family or a friend and invite them to read along.</p>
<div class="row"><button class="btn btn-red" type="button" data-copy="{DOMAIN}/">Copy invite link</button><a class="btn btn-line" href="/#join">Share the sign-up page</a></div></aside>"""
        prev = days[i-1] if i > 0 else None; nxt = days[i+1] if i + 1 < len(days) else None
        nav = (f'<a class="prev" href="/dontmissjesus/day-{prev["n"]}"><span class="k">← Day {prev["n"]}</span><span class="t">{esc(prev["title"])}</span></a>' if prev
               else '<a class="prev" href="/dontmissjesus/week-1"><span class="k">This week</span><span class="t">Thanksgiving week</span></a>')
        nav += (f'<a class="next" href="/dontmissjesus/day-{nxt["n"]}"><span class="k">Tomorrow · Day {nxt["n"]} →</span><span class="t">{esc(nxt["title"])}</span></a>' if nxt
                else '<a class="next" href="/#weeks"><span class="k">Next week</span><span class="t">Hope · starts Nov 30</span></a>')
        body = f"""<div class="stripe" aria-hidden="true"></div>
<article class="day-post">
<header class="day-head"><p class="day-meta"><span class="red-dot" aria-hidden="true"></span><span>Day {n} of 40</span><span class="sep wk">·</span><span class="wk">{esc(week[0])} week</span><span class="sep">·</span><span>{esc(d['day'])}</span>{tag}</p>
<h1>{esc(d['title'])}</h1></header>
<figure class="day-photo"><img src="{dmj_photo(d['photo'])}"{srcset(dmj_photo(d['photo']), 1500, "(max-width: 760px) 100vw, 728px")} alt="" fetchpriority="high" style="object-position:{DMJ_FOCUS.get(n, '50% 50%')}">{f'<figcaption>{esc(d["credit"])}</figcaption>' if d.get('credit') else ''}</figure>
<section class="day-sec word"><h2>Word</h2>
<blockquote class="day-verse">{esc(d['verse'])}<cite>{esc(d['ref'])}</cite></blockquote>
{''.join(f'<p>{esc(p)}</p>' for p in d['devo'])}
<h3 class="label">Scriptures for today</h3>
<p class="hint">As you read today's Scriptures, read slowly and attentively, allowing the Holy Spirit to speak to you as you meditate on His Word.</p>
{scrip}</section>
<section class="day-sec"><h2>Worship</h2>
<button class="dmj-video" type="button" data-id="{d['yt']}" data-title="{esc(d['song'])}" aria-label="Play {esc(d['song'])} by {esc(d['artist'])}"><img src="https://i.ytimg.com/vi/{d['yt']}/hqdefault.jpg" alt="" loading="lazy"><span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="#FFFDF8"/></svg></span></button>
<p class="song"><strong>{esc(d['song'])}</strong> · {esc(d['artist'])}</p>
<p class="links"><a href="https://www.youtube.com/watch?v={d['yt']}">Watch on YouTube</a><a href="{d['spotify']}">Listen on Spotify</a></p></section>
<section class="day-sec"><h2>Pray</h2>
<p class="prayer">{esc(d['prayer'])}</p>
<div class="seven"><p class="label">Give thanks for 7</p><p>{esc(d['seven'])}</p></div></section>
<section class="day-sec"><h2>Listen &amp; Obey</h2>
<p>{esc(d['listen_intro'])}</p><ul class="prompts">{listen}</ul></section>
{invite}
<nav class="day-nav" aria-label="Day navigation">{nav}</nav>
<footer class="day-credits">{''.join(f'<p>{c}</p>' for c in credit)}</footer>
</article>
<section class="day-strip"><div><p class="script">Don't miss tomorrow</p><p>Get each day's devotional in your inbox every morning.</p></div><a class="btn btn-cream" href="/#join">Sign me up</a></section>"""
        desc = f"Day {n} of Don't Miss Jesus: {d['ref']}. A short devotional with Scripture, worship, prayer and listening."
        head = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&amp;display=swap">\n'
        write(f'dontmissjesus/day-{n}.html', dmj_shell(f"Day {n}: {d['title']} · Don't Miss Jesus", desc, path, body + DMJ_DAY_JS, extra=' dmj-page dmj-day',
              image=dmj_photo(f'day-{n:02d}-share.jpg'), image_alt=d['title'], head=head))
        out.append(path)
    out.append(dmj_week(1, days))
    return out

def dmj_days_es():
    """Spanish Week 1 day pages at /es/dia-N. Content: content/dontmissjesus/week1.es.json (Scripture: Reina-Valera 1909, public domain)."""
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'dontmissjesus', 'week1.es.json')))
    days = data['days']; out = []
    js = DMJ_DAY_JS.replace("'Link copied'", "'Enlace copiado'").replace("'Copy this link:'", "'Copia este enlace:'").replace('"Don\'t Miss Jesus"', '"No te pierdas a Jesús"')
    for i, d in enumerate(days):
        n = d['n']; path = f'/es/dia-{n}'
        wi = next(k for k, w in enumerate(DMJ_WEEKS) if w[1] <= n <= w[2])
        tag = f'<span class="sep brk">·</span><span>{esc(d["tag"])}</span>' if d.get('tag') else ''
        scrip = ''.join(f'<p class="passage"><span class="ref">{esc(x["ref"])}</span> {esc(x["text"])}</p>' for x in d['scriptures'])
        listen = ''.join(f'<li>{esc(q)}</li>' for q in d['listen'])
        invite = ''
        if n == 1:
            invite = f"""<aside class="day-invite"><p class="label">Invita a un amigo</p><p>¿Quién podría hacer estos 40 días contigo? Envíale un mensaje a tu grupo de vida, a tu familia o a un amigo e invítalo a leer contigo.</p>
<div class="row"><button class="btn btn-red" type="button" data-copy="{DOMAIN}/es/">Copiar enlace de invitación</button><a class="btn btn-line" href="/es/#join">Compartir la página de inscripción</a></div></aside>"""
        prev = days[i-1] if i > 0 else None; nxt = days[i+1] if i + 1 < len(days) else None
        nav = (f'<a class="prev" href="/es/dia-{prev["n"]}"><span class="k">← Día {prev["n"]}</span><span class="t">{esc(prev["title"])}</span></a>' if prev
               else f'<a class="prev" href="/es/#weeks"><span class="k">Las semanas</span><span class="t">Semana de {esc(DMJ_WEEKS_ES[0][0])}</span></a>')
        nav += (f'<a class="next" href="/es/dia-{nxt["n"]}"><span class="k">Mañana · Día {nxt["n"]} →</span><span class="t">{esc(nxt["title"])}</span></a>' if nxt
                else f'<a class="next" href="/es/#weeks"><span class="k">Próxima semana</span><span class="t">{esc(DMJ_WEEKS_ES[1][0])} · comienza el 30 de nov.</span></a>')
        body = f"""<div class="stripe" aria-hidden="true"></div>
<article class="day-post">
<header class="day-head"><p class="day-meta"><span class="red-dot" aria-hidden="true"></span><span>Día {n} de 40</span><span class="sep wk">·</span><span class="wk">Semana de {esc(DMJ_WEEKS_ES[wi][0])}</span><span class="sep">·</span><span>{esc(d['day'])}</span>{tag}</p>
<h1>{esc(d['title'])}</h1></header>
<figure class="day-photo"><img src="{dmj_photo(d['photo'])}"{srcset(dmj_photo(d['photo']), 1500, "(max-width: 760px) 100vw, 728px")} alt="" fetchpriority="high" style="object-position:{DMJ_FOCUS.get(n, '50% 50%')}">{f'<figcaption>{esc(d["credit"])}</figcaption>' if d.get('credit') else ''}</figure>
<section class="day-sec word"><h2>Palabra</h2>
<blockquote class="day-verse">{esc(d['verse'])}<cite>{esc(d['ref'])}</cite></blockquote>
{''.join(f'<p>{esc(p)}</p>' for p in d['devo'])}
<h3 class="label">Escrituras para hoy</h3>
<p class="hint">Al leer las Escrituras de hoy, lee despacio y con atención, permitiendo que el Espíritu Santo te hable mientras meditas en Su Palabra.</p>
{scrip}</section>
<section class="day-sec"><h2>Adoración</h2>
<button class="dmj-video" type="button" data-id="{d['yt']}" data-title="{esc(d['song'])}" aria-label="Reproducir {esc(d['song'])} de {esc(d['artist'])}"><img src="https://i.ytimg.com/vi/{d['yt']}/hqdefault.jpg" alt="" loading="lazy"><span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="#FFFDF8"/></svg></span></button>
<p class="song"><strong>{esc(d['song'])}</strong> · {esc(d['artist'])}</p>
<p class="links"><a href="https://www.youtube.com/watch?v={d['yt']}">Ver en YouTube</a><a href="{d['spotify']}">Escuchar en Spotify</a></p></section>
<section class="day-sec"><h2>Oración</h2>
<p class="prayer">{esc(d['prayer'])}</p>
<div class="seven"><p class="label">Da gracias por 7</p><p>{esc(d['seven'])}</p></div></section>
<section class="day-sec"><h2>Escuchar y obedecer</h2>
<p>{esc(d['listen_intro'])}</p><ul class="prompts">{listen}</ul></section>
{invite}
<nav class="day-nav" aria-label="Navegación de días">{nav}</nav>
<footer class="day-credits"><p>{esc(data['credit'])}</p></footer>
</article>
<section class="day-strip"><div><p class="script">No te pierdas mañana</p><p>Recibe el devocional de cada día en tu correo cada mañana.</p></div><a class="btn btn-cream" href="/es/#join">Inscríbeme</a></section>"""
        desc = f"Día {n} de No te pierdas a Jesús: {d['ref']}. Un devocional corto con Escritura, adoración, oración y tiempo para escuchar."
        head = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&amp;display=swap">\n'
        write(f'es/dia-{n}.html', dmj_shell(f"Día {n}: {d['title']} · No te pierdas a Jesús", desc, path, body + js, signup='/es/#join', extra=' dmj-page dmj-day', lang='es',
              image=dmj_photo(f'day-{n:02d}-share.jpg'), image_alt=d['title'], head=head))
        out.append(path)
    return out

devotion_landing(); resources(); notices()
DMJ_DAY_PATHS = (dmj_days() + dmj_days_es()) if DMJ_SEASON else []
if DMJ_SEASON: dmj_home(); dmj_home_es(); dmj_welcome_es(); dmj_family_es(); dmj_top10_es(); dmj_top20_es(); dmj_family(); dmj_top10(); dmj_top20(); dmj_welcome()

# ---------- launch files ----------
paths = ['/'] + (['/es/', '/es/devocionales-en-familia', '/es/accion-de-gracias', '/es/navidad'] if DMJ_SEASON else []) + ['/dontmissjesus/family-devotions', '/dontmissjesus/top-10-thanksgiving', '/dontmissjesus/top-20-christmas', '/devotion', '/resources'] + DMJ_DAY_PATHS + ['/devos/' + d['slug'] for _, d in DEV]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{DOMAIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
write('_redirects', '''/dontmissjesus/thanksgiving-table /dontmissjesus/top-10-thanksgiving 301
# Old Squarespace addresses
/40-day-journeys          /                          301
/home                     /                          301
/devos                    /devotion#days             301
/devos/pass-it-on         /devos/peter-and-john      301
/group-events             /                          301
/cart                     /                          301
# Retired test pages
/devos/bread-of-life-test /devos/bread-of-life       301
/devos/bread-of-life-word-line /devos/bread-of-life  301
/devos/bread-of-life-word-card /devos/bread-of-life  301
/devos/bread-of-life-layout-test /devos/bread-of-life 301
''')
print(f'Built {len(DEV)} devotion days, the landing page and launch files.')
