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
    return out

def sec_scriptures(blocks):
    out, opened = [], False
    for i, b in enumerate(blocks):
        if is_placeholder(b): continue
        m = REF.match(plain(b)) if i or is_italic(b) else None
        if m:
            if opened: out.append('</div>')
            out.append(f'<div class="passage"><h3>{esc(ref_colon(m.group(1)))}</h3><p>{inline(m.group(2))}</p>'); opened = True
        elif opened and is_italic(b):
            out.append(f'<p>{inline(plain(b))}</p>')
        else:
            if opened: out.append('</div>'); opened = False
            out.append(f'<p class="intro">{inline(b)}</p>' if i == 0 else block(b))
    if opened: out.append('</div>')
    return ''.join(out)

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

def render_sections(d, n, series):
    out = []
    for name, blocks in d['sections']:
        label = {'Scriptures For Today': 'Scriptures for Today', 'Vision for This Week': 'Vision for This Week'}.get(name, name)
        if name == 'Word' and series == 'devotion': inner, cls = sec_word_verse(blocks), 'word'
        elif name == 'Scriptures For Today': inner, cls = sec_scriptures(blocks), ''
        elif name == 'Worship' or (name == 'Wrap Up' and any('youtube' in b for b in blocks)):
            inner, cls = (sec_worship(blocks, n, series) if name == 'Worship' else
                          ''.join(video(re.search(r'v=([\w-]+)', b).group(1), 'Worship video') if 'youtube.com/watch' in b else block(b) for b in blocks)), ''
        elif name == 'Prayer': inner, cls = sec_prayer(blocks), ''
        elif name == 'Invite a Friend': inner, cls = sec_invite(blocks), ''
        elif name == 'Listen & Obey': inner, cls = sec_listen(blocks), ''
        else: inner, cls = ''.join(block(b) for b in blocks if not is_placeholder(b)), ''
        if not inner: continue
        c = f' class="{cls}"' if cls else ''
        out.append(f'<section{c}><h2>{esc(label)}</h2>{inner}</section>')
    return '<hr class="rule">'.join(out)

# ---------- page shell ----------
# Antioch logo (traced from the black PNG). It takes its color from CSS: black, or white on the home page photo.
LOGO = ('<svg viewBox="0 0 500 500" role="img" aria-label="40 Day Journeys home"><path fill="currentColor" fill-rule="evenodd" d="M234.5,482.0C194.1,479.0 155.0,465.8 122.0,443.7C113.0,437.7 104.2,431.0 101.8,428.3C100.1,426.4 102.7,420.5 174.3,267.2C225.2,158.0 249.0,108.0 250.0,108.0C251.1,108.0 274.8,157.8 325.5,266.6C366.2,353.8 399.6,425.8 399.8,426.4C400.2,428.0 381.5,441.9 369.0,449.4C329.2,473.4 280.1,485.3 234.5,482.0ZM52.3,371.3C45.3,360.3 40.8,351.9 36.1,341.2C6.3,273.5 10.7,194.3 47.9,130.8C75.5,83.6 119.3,47.3 170.0,29.9C192.9,22.0 224.2,15.7 226.9,18.5C228.2,19.9 61.0,378.4 58.8,378.8C57.8,379.0 55.6,376.4 52.3,371.3ZM436.5,371.8C434.6,367.8 396.8,286.9 352.6,192.0C301.1,81.6 272.5,19.1 273.1,18.5C274.2,17.4 278.6,17.6 290.5,19.6C387.3,35.8 462.7,110.3 479.9,206.7C488.0,251.9 482.4,299.3 464.0,341.1C456.7,357.5 443.9,379.0 441.4,379.0C440.5,379.0 438.4,375.8 436.5,371.8ZM191.1,294.6C224.9,279.7 268.8,278.8 304.0,292.5C316.9,297.4 317.0,297.5 317.0,295.9C317.0,295.1 311.8,283.1 305.4,269.2L293.7,244.0L289.7,242.9C273.5,238.6 249.1,236.9 232.4,238.9C223.3,240.1 207.3,243.3 206.6,244.1C205.6,245.2 183.0,294.9 183.0,295.8C183.0,297.6 185.2,297.3 191.1,294.6Z"/></svg>')

def shell(title, desc, path, body, image='', signup=None, script=False, overlay=False):
    nav = ['<a href="/devotion#days">All 40 Days</a>', '<a href="/resources">Resources</a>']
    if signup: nav.append(f'<a class="signup" href="{signup}">Sign up</a>')
    if image.startswith('/'): image = DOMAIN + image
    og = f'<meta property="og:image" content="{esc(image)}">\n<meta name="twitter:card" content="summary_large_image">\n' if image else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="40 Days of Devotion">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
{og}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&amp;display=swap">
<link rel="stylesheet" href="/style.css">
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
def day_page(d, n, series, prev, nxt, total=40):
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
<article class="day">
{render_sections(d, n, series)}
<nav class="day-nav" aria-label="Days">{link(prev, "prev", 0)}{link(nxt, "next", 1)}</nav>
</article>'''
    title = f'{"Day " + str(n) + ": " if n else ""}{plain(name)} · {home_t}'
    return shell(title, first_sentence(d), base + d['slug'], body, photo(d['photo'], 1200, share=True), signup, script=True)

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
    write('index.html', page)   # the home page is the devotion landing page

def notices():
    write('whats-next.html', shell('You are all signed up! · 40 Day Journeys', 'You are signed up for a 40 Day Journey.', '/whats-next',
        '<section class="notice"><h1>You are all signed up!</h1><p>Each morning at 3am (starting tomorrow morning) you will receive a link in your inbox to the devotional for that day!</p><a class="btn" href="/devotion#days">See all 40 days</a></section>'))
    write('404.html', shell('Page not found · 40 Day Journeys', 'Page not found.', '/404',
        '<section class="notice"><h1>This page has moved</h1><p>The page you were looking for isn’t here anymore. All 40 days of the devotional are still on the site.</p><a class="btn" href="/devotion#days">See all 40 days</a></section>'))

devotion_landing(); resources(); notices()

# ---------- launch files ----------
paths = ['/devotion', '/resources'] +['/devos/' + d['slug'] for _, d in DEV]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{DOMAIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
write('_redirects', '''# Old Squarespace addresses
/40-day-journeys          /                          301
/home                     /                          301
/devos                    /devotion#days             301
/devos/pass-it-on         /devos/peter-and-john      301
/group-events             /                          301
/cart                     /                          301
''')
print(f'Built {len(DEV)} devotion days, the landing page and launch files.')
