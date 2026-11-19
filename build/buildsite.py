"""Build every page of 40DayJourneys.com into build/site/.

Content lives in build/content/ as one Markdown file per day (the same text as the
Notion pages). Run `bash build/deploy.sh` from the repo root, then commit and push.
"""
import glob, html, os, re

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
    banner = f'<div class="banner"><img src="{photo(d["photo"])}" alt="" width="1500" height="1071"{focus}></div>' if d['photo'] else ''
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
    write('resources.html', shell('Resources · 40 Days of Devotion', 'The Face to Face teaching series and the Alone With God guidebook.', '/resources', body, '', KIT_DEVOTION))

# ---------- Don't Miss Jesus: seasonal home page (Nov 2026 to Jan 1 2027) ----------
# Set DMJ_SEASON = False after Jan 1 to put the 40 Days of Devotion landing page back on the home page.
DMJ_SEASON = True
DMJ_FORM = 'https://app.kit.com/forms/10209100/subscriptions'   # Kit landing page "Don't Miss Jesus 2026"
DMJ_CSS_V = hashlib.md5(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site', 'dmj.css'), 'rb').read()).hexdigest()[:8]
DMJ_WEEKS = [('Thanksgiving', 1, 7, 'Nov 23 to 29'), ('Hope', 8, 14, 'Nov 30 to Dec 6'), ('Peace', 15, 21, 'Dec 7 to 13'),
             ('Joy', 22, 28, 'Dec 14 to 20'), ('Love', 29, 35, 'Dec 21 to 27'), ('Grace', 36, 40, 'Dec 28 to Jan 1')]

def dots(n): return '<div class="dots" aria-hidden="true">' + ''.join('<span class="on"></span>' if i == 0 else '<span></span>' for i in range(n)) + '</div>'

def dmj_shell(title, desc, path, body, signup='/#join', extra=''):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="40 Days of Devotion">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
<meta property="og:image" content="{DOMAIN}/dmj-share.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Antioch A logo">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{DOMAIN}/dmj-share.png">
<meta name="theme-color" content="#7C1F1F">
<link rel="icon" href="/dmj-favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/dmj-icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,900&amp;family=Outfit:wght@400;500;600;700&amp;family=Yellowtail&amp;display=swap">
<link rel="stylesheet" href="/dmj.css?v={DMJ_CSS_V}">
</head>
<body class="dmj{extra}">
<a class="skip" href="#main">Skip to content</a>
<header class="dmj-header"><a class="dmj-brand" href="/"><span class="dmj-logo">{LOGO}</span>DON'T MISS JESUS</a>
<nav class="dmj-nav" aria-label="Main"><a href="/#weeks">The weeks</a><a href="/devotion">40 Days of Devotion</a><a class="btn btn-red" href="{signup}">Sign up</a></nav></header>
<main id="main" class="dmj-main">
{body}
</main>
<footer class="dmj-footer"><span class="dmj-logo foot" aria-hidden="true">{LOGO}</span><span class="script">Merry Christmas</span><p>From your family at Antioch Waco</p>
<nav aria-label="Footer"><a href="/devotion">40 Days of Devotion</a><a href="/resources">Resources</a><a href="https://antiochwaco.com/">Antioch Waco</a></nav></footer>
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

def dmj_thanksgiving():
    desc = "Simple ways to give thanks and honor one another around the Thanksgiving table, and to keep thanking God all day long."
    body = """<article class="guide">
<header class="guide-head"><p class="eyebrow">Thanksgiving</p><h1><span class="script">Give thanks at</span><span class="slab">The Table</span></h1>
<p class="byline">From Jimmy and Laura Seibert</p>
<p class="lede">“In everything give thanks; for this is God’s will for you in Christ Jesus.” 1 Thessalonians 5:18</p></header>
<div class="guide-body">
<p>Many of us grew up in homes where thanksgiving and appreciation for one another were not voiced very often. A few years ago, my brother and I took some time to honor our parents in front of our children. We talked about the valuable things they had given us. We were able to build them up, and our kids got to see what it looks like to honor your parents along the journey.</p>
<p>There are so many ways to do this at the Thanksgiving table:</p>
<ol class="guide-steps">
<li><span class="n">01</span><div><h2>A Scripture at every plate</h2><p>Put a verse in front of everyone’s plate. Have each person read their Scripture out loud and say what they are thankful for.</p></div></li>
<li><span class="n">02</span><div><h2>A name on every tag</h2><p>Put someone’s name on each place card, and have each person say one encouraging thing about the person whose name they drew.</p></div></li>
<li><span class="n">03</span><div><h2>Honor your grandparents</h2><p>If grandparents are at the table, take time to honor them, and let the younger ones see what honor and thanksgiving are all about.</p></div></li>
<li><span class="n">04</span><div><h2>Remember and pray</h2><p>Read Abraham Lincoln’s 1863 <a href="https://www.abrahamlincolnonline.org/lincoln/speeches/thanks.htm">Thanksgiving Proclamation</a> together. Be in awe again of what this season is all about, and take some time to pray for our country.</p></div></li>
</ol>
<h2 class="guide-h">More for the day</h2>
<ul class="guide-list">
<li><strong>Tell the story.</strong> Talk about the history of Thanksgiving.</li>
<li><strong>Remember His faithfulness.</strong> Ask: What blessing are you thankful for? Where did you find God faithful in a hard time?</li>
<li><strong>Have fun.</strong> Joy is a partner with thankfulness. Play a family game together.</li>
<li><strong>Speak life.</strong> Encourage one another, especially the college students and young adults at the table who are learning what it means to be an adult and give life to others.</li>
</ul>
<h2 class="guide-h">Give thanks all day long</h2>
<p>Set a reminder on your watch or phone for every hour. Each time it goes off, take a moment with 1 Thessalonians 5:18:</p>
<ul class="guide-list">
<li>Acknowledge God’s presence and His love for you.</li>
<li>Thank Him for what is happening in that moment.</li>
<li>Pray, “Speak, Lord, Your servant is listening.”</li>
</ul>
<h2 class="guide-h">Make it a thankfulness feast</h2>
<p>Gather the family around the table and let everyone share three things they are thankful for. Make room for deep conversation, and finish with something you do together as a family.</p>
<p>We are sharing these because we want you to have a great Thanksgiving!</p>
<p class="signoff">Jimmy and Laura</p>
</div>
<aside class="guide-cta"><p class="eyebrow">Starts Monday, Nov 23</p><h2>Start Thanksgiving week with Don’t Miss Jesus</h2><p>Week one of the 40 days is all about thanksgiving. A short devotional in your inbox each morning.</p><a class="btn btn-cream" href="/#join">Count Me In</a></aside>
</article>"""
    write('dontmissjesus/thanksgiving-table.html', dmj_shell("Give Thanks at the Table · Don't Miss Jesus", desc, '/dontmissjesus/thanksgiving-table', body, extra=' dmj-page'))

def dmj_home():
    desc = "Sign up for a free 40 day devotional to help you experience Jesus this Holiday season."
    weeks = ''.join(f'''<li class="week"><div class="candy"></div><div class="week-body"><div class="meta"><span>WEEK {i+1}</span><span>DAYS {a}–{b}</span></div><h3>{t}</h3><span class="when">{w}</span></div></li>''' for i, (t, a, b, w) in enumerate(DMJ_WEEKS))
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
<span class="phone-date">Monday, November 23</span><span class="phone-time">6:00</span>
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
<li class="res-item"><div class="art candy" aria-hidden="true"></div><div class="body"><span class="eyebrow">Thanksgiving</span><h3>Give thanks at the table</h3><p>Simple ways to give thanks and honor one another around the Thanksgiving table.</p><a class="go" href="/dontmissjesus/thanksgiving-table">Read the guide →</a></div></li>
<li class="res-item"><div class="art stripe" aria-hidden="true"></div><div class="body"><span class="eyebrow">Christmas</span><h3>Family Christmas Eve Guide</h3><p>Read the Christmas story together, with simple questions for kids and adults.</p><span class="soon">Coming soon</span></div></li>
<li class="res-item"><div class="art grid-bg" aria-hidden="true"></div><div class="body"><span class="eyebrow">New Year</span><h3>30-Day Journal</h3><p>Look back on 2026, pray over 2027 and plan your next step in the Word.</p><a class="go" href="https://passionandpurpose.kit.com/30dayjournal">Get the journal →</a></div></li>
</ul></div></section>'''
    page = dmj_shell("Don't Miss Jesus · 40 Days of Devotion", desc, '/', body, '#join')
    write('index.html', page)

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

devotion_landing(); resources(); notices()
if DMJ_SEASON: dmj_home(); dmj_family(); dmj_thanksgiving()

# ---------- launch files ----------
paths = ['/', '/dontmissjesus/family-devotions', '/dontmissjesus/thanksgiving-table', '/devotion', '/resources'] +['/devos/' + d['slug'] for _, d in DEV]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{DOMAIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
write('_redirects', '''# Old Squarespace addresses
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
