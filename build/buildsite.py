"""Build every page of 40DayJourneys.com into build/site/.

Content lives in build/content/ as one Markdown file per day (the same text as the
Notion pages). Run `bash build/deploy.sh` from the repo root, then commit and push.
"""
import glob, html, os, re

D = os.path.dirname(os.path.abspath(__file__))
C, OUT = D + '/content', D + '/site'
DOMAIN = 'https://www.40dayjourneys.com'
KIT_DEVOTION = 'https://passionandpurpose.kit.com/40-days-of-devotion'
KIT_DISCIPLESHIP = 'https://passionandpurpose.kit.com/discipleship'
CDN = 'https://images.squarespace-cdn.com/content/v1/6765a61dee5146683ca33b13/'
SECTIONS = [('Drawing Near', 1, 7), ('Worship', 8, 14), ('The Word', 15, 21), ('Prayer', 22, 33), ('Listening', 34, 40)]
NEW_SLUGS = {36: 'he-calls-his-sheep'}          # days that never existed on the old site
SONG_LINKS = {29: ('O Come to the Altar by Elevation Worship',
                   'https://www.youtube.com/results?search_query=O+Come+to+the+Altar+Elevation+Worship')}

def photo(u, w=1500):
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
    return '/40-days-of-discipleship' if h.rstrip('/') == '/discipleship' else h

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
LOGO = ('<svg viewBox="0 0 52 52" role="img" aria-label="40 Day Journeys"><circle cx="26" cy="26" r="26" fill="#CFCFCF"/>'
        '<text x="26" y="35" text-anchor="middle" font-family="Helvetica Neue,Helvetica,Arial,sans-serif" font-size="26" font-weight="600" fill="#FFFFFF">A</text></svg>')

def shell(title, desc, path, body, image='', signup=None, script=False):
    nav = ['<a href="/devotion">Devotion</a>', '<a href="/40-days-of-discipleship">Discipleship</a>']
    if signup: nav.append(f'<a class="signup" href="{signup}">Sign up</a>')
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
<meta property="og:site_name" content="40 Day Journeys">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
{og}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&amp;display=swap">
<link rel="stylesheet" href="/style.css">
</head>
<body>
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
    if series == 'devotion':
        name = d['title'].split(': ', 1)[1]
        eyebrow = f'Day {n} of {total} · {section_of(n)[0]}'
        signup, base, home, home_t = KIT_DEVOTION, '/devos/', '/devotion', '40 Days of Devotion'
    else:
        name = d['title'].split(': ', 1)[1] if ': ' in d['title'] else d['title']
        eyebrow = f'Day {n} of {total}' if n else 'Before Day 1'
        signup, base, home, home_t = KIT_DISCIPLESHIP, '/discipleship/', '/40-days-of-discipleship', '40 Days of Discipleship'
    pct = max(n, 0) / total * 100
    banner = f'<div class="banner"><img src="{photo(d["photo"])}" alt="" width="1500" height="1071"></div>' if d['photo'] else ''
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
    return shell(title, first_sentence(d), base + d['slug'], body, photo(d['photo'], 1200), signup, script=True)

def build_series(series, files, numbering):
    items = []
    for f in files:
        d = parse(f)
        n = numbering(f)
        if not d['slug']: d['slug'] = NEW_SLUGS[n]
        items.append((n, d))
    for i, (n, d) in enumerate(items):
        prev = items[i - 1] if i else None
        nxt = items[i + 1] if i + 1 < len(items) else None
        folder = 'devos' if series == 'devotion' else 'discipleship'
        write(f'{folder}/{d["slug"]}.html', day_page(d, n, series, prev, nxt))
    return items

num = lambda f: int(os.path.basename(f)[:2])
DEV = build_series('devotion', sorted(glob.glob(C + '/devotion/*.md')), num)
DISC = build_series('discipleship', sorted(glob.glob(C + '/discipleship/*.md')), num)

# ---------- landing pages ----------
def day_rows(items, base):
    return ''.join(f'<li><a href="{base}{d["slug"]}"><span class="n">{n if n else "·"}</span><span class="t">{inline(d["title"].split(": ", 1)[1] if ": " in d["title"] else d["title"])}</span></a></li>' for n, d in items)

def card(img, eyebrow, title, text, href, more):
    a = f'<a class="more" href="{href}">{more} →</a>' if href else ''
    im = f'<img class="ph" src="{photo(img, 1000)}" alt="" loading="lazy">' if img else ''
    return f'<article class="card">{im}<p class="eyebrow">{eyebrow}</p><h2>{title}</h2><p>{text}</p>{a}</article>'

def devotion_landing():
    groups = ''.join(f'''<div class="group"><div class="group-head"><h3>{s}</h3><span>Days {a} to {b}</span></div>
<ol class="day-list">{day_rows([x for x in DEV if a <= x[0] <= b], "/devos/")}</ol></div>''' for s, a, b in SECTIONS)
    body = f'''<section class="hero">
<p class="eyebrow">A 40 Day Journey</p>
<h1>40 Days of Devotion</h1>
<p class="lede">A series of teachings and a daily devotional designed to help you start, strengthen or reignite the daily habit of spending time with the Lord.</p>
<div class="actions"><a class="btn" href="{KIT_DEVOTION}">Sign up for the daily email</a><a class="btn btn-outline" href="/devos/{DEV[0][1]["slug"]}">Start with Day 1</a></div>
</section>
<div class="wide-photo"><img src="{photo(CDN + '63458635-21e6-4dcd-a98b-581bacd3b86e/yusron-el-jihan-pc4OfudfwOo-unsplash.jpg')}" alt=""></div>
<section class="cards" aria-label="Resources">
{card(CDN + 'd4b62a2c-ca5a-4f28-8d46-4e23169885a1/Face+to+Face+Square.png', 'Teaching Series', 'Face to Face', 'A six-part series on Scripture, worship, prayer, listening, obeying, and abiding in Jesus.', 'https://www.youtube.com/playlist?list=PLoXSy2HiYN4uEu-SuVRHI5QVy5RowVX_E', 'Watch the series')}
{card(CDN + 'd5151301-02f3-4cb8-b699-02086d9fd987/daiga-ellaby-zdCLnTwD52Q-unsplash.jpg', 'Daily Devotional', '40 Days in Your Inbox', 'A free email each morning for forty days to help you build the habit of spending daily time with the Lord.', KIT_DEVOTION, 'Sign up')}
{card(CDN + 'cff63a66-5bf8-4b1c-9498-c259fe20fe99/Untitled+design+%283%29.png', 'Guidebook', 'Alone With God', 'Practical tools and examples for prayer, worship, and Bible study, for a more intimate connection with God through daily devotions.', 'https://antiochwaco.com/alone-with-god-page', 'Get the guidebook')}
</section>
<section class="days" id="days"><h2>The 40 Days</h2><p>Five movements, one day at a time.</p>{groups}</section>
<section class="closing"><blockquote>“Abide in Me, and I in you. As the branch cannot bear fruit of itself unless it abides in the vine, so neither can you unless you abide in Me.”</blockquote><p class="ref">John 15:4</p></section>'''
    write('devotion.html', shell('40 Days of Devotion', 'A daily devotional to help you start, strengthen or reignite the daily habit of spending time with the Lord.', '/devotion', body,
                                 photo(CDN + '63458635-21e6-4dcd-a98b-581bacd3b86e/yusron-el-jihan-pc4OfudfwOo-unsplash.jpg', 1200), KIT_DEVOTION))

def discipleship_landing():
    orient = [x for x in DISC if x[0] == 0]
    rest = [x for x in DISC if x[0] > 0]
    body = f'''<section class="hero">
<p class="eyebrow">A 40 Day Journey</p>
<h1>40 Days of Discipleship</h1>
<p class="lede">A series of teachings, daily devotionals and discipleship lessons designed to help build good foundations in being and making disciples of Jesus.</p>
<div class="actions"><a class="btn" href="{KIT_DISCIPLESHIP}">Sign up for the daily email</a><a class="btn btn-outline" href="/discipleship/{orient[0][1]["slug"]}">Start with Orientation</a></div>
</section>
<div class="wide-photo"><img src="{photo(CDN + 'd00abda0-39cc-41f8-a24c-11babb10b349/dawid-tkocz-l0BtQcG5300-unsplash.jpg')}" alt=""></div>
<section class="cards" aria-label="Resources">
{card(CDN + '9616aa73-1205-4ac3-bb97-6338912fabfe/Square+Thumbnail.png', 'Teaching Series', 'Life on Life Discipleship', 'A teaching series to help you build or rebuild good foundations for being and making disciples of Jesus.', '', '')}
{card(CDN + '612915b0-0366-42a3-9ac0-795ef5ce80e2/daiga-ellaby-pBLEn9Vc5jo-unsplash.jpg', 'Daily Devotional', '40 Days in Your Inbox', 'A 40 day email devotional on the joy of being a disciple of Jesus and our calling to make disciples.', KIT_DISCIPLESHIP, 'Sign up')}
{card(CDN + 'fc14b84a-94e2-42f6-87b8-befd81b5451e/ChatGPT+Image+May+29%2C+2025%2C+01_59_15+PM.png', 'Discipleship Lessons', 'DiscipleshipLessons.com', 'Simple, Biblical, powerful lessons to help you make disciples in your sphere of influence.', 'https://www.discipleshiplessons.com', 'Get the lessons')}
</section>
<section class="days" id="days"><h2>The 40 Days</h2><p>Being and making disciples of Jesus, one day at a time.</p>
<div class="group"><div class="group-head"><h3>Start Here</h3></div><ol class="day-list">{day_rows(orient, "/discipleship/")}</ol></div>
<div class="group"><div class="group-head"><h3>The Journey</h3><span>Days 1 to 40</span></div><ol class="day-list">{day_rows(rest, "/discipleship/")}</ol></div>
</section>
<section class="closing"><blockquote>“Go therefore and make disciples of all the nations, baptizing them in the name of the Father and the Son and the Holy Spirit, teaching them to observe all that I commanded you; and lo, I am with you always, even to the end of the age.”</blockquote><p class="ref">Matthew 28:19-20</p></section>'''
    write('40-days-of-discipleship.html', shell('40 Days of Discipleship', 'Teachings, daily devotionals and discipleship lessons to help build good foundations in being and making disciples of Jesus.', '/40-days-of-discipleship', body,
                                                photo(CDN + 'd00abda0-39cc-41f8-a24c-11babb10b349/dawid-tkocz-l0BtQcG5300-unsplash.jpg', 1200), KIT_DISCIPLESHIP))

def home():
    body = f'''<section class="hero">
<h1>40 Day Journeys</h1>
<p class="lede">A series of teachings, devotional guides, discipleship lessons and recommended resources designed to help you and your friends grow in Jesus.</p>
</section>
<div class="wide-photo"><img src="{photo(CDN + 'd72eede5-3430-466e-9a31-2e201f4b2385/andrii-solok-eC-Bcw3pGbg-unsplash.jpg')}" alt=""></div>
<section class="cards two" aria-label="Journeys">
{card(CDN + '63458635-21e6-4dcd-a98b-581bacd3b86e/yusron-el-jihan-pc4OfudfwOo-unsplash.jpg', 'A 40 Day Journey', '<a href="/devotion" style="color:inherit;text-decoration:none">40 Days of Devotion</a>', 'Designed to help you start, strengthen or reignite the daily habit of spending time with the Lord.', '/devotion', 'Begin')}
{card(CDN + 'd00abda0-39cc-41f8-a24c-11babb10b349/dawid-tkocz-l0BtQcG5300-unsplash.jpg', 'A 40 Day Journey', '<a href="/40-days-of-discipleship" style="color:inherit;text-decoration:none">40 Days of Discipleship</a>', 'Designed to build good foundations in being and making disciples of Jesus.', '/40-days-of-discipleship', 'Begin')}
</section>
<section class="closing"><p class="ref">Made with love from <a href="https://antiochwaco.com/">Antioch Waco</a></p></section>'''
    write('index.html', shell('40 Day Journeys', 'Teachings, devotional guides, discipleship lessons and resources designed to help you and your friends grow in Jesus. From Antioch Waco.', '/', body,
                              photo(CDN + 'd72eede5-3430-466e-9a31-2e201f4b2385/andrii-solok-eC-Bcw3pGbg-unsplash.jpg', 1200)))

FREEDOM_SERMONS = [
 ('You Can Be Free', 'In this sermon introducing the "Journey to Freedom" sermon series, Pastor Jimmy Seibert emphasizes that true freedom from sin is not only possible, but biblically promised through Christ\'s sacrifice and the Holy Spirit\'s power. He explores the process of sanctification, involving spirit, soul, and body, while emphasizing the crucial role of surrendering our will to God and the importance of community in our journey to freedom.'),
 ('Healing The Brokenhearted', 'The journey to freedom is a love story — one where God\'s unconditional love for us drives out fear, anxiety and brokenness. In this sermon, Jimmy Seibert teaches on how to work out our salvation, heal our broken hearts and find true freedom in Christ.'),
 ('The Framework of Freedom', 'In this message, Pastor Jimmy explored the process of sanctification and the renewal of our minds — key elements in experiencing the fullness of God’s love and purpose for our lives.'),
 ('Freedom From Idolatry', 'In this message, Pastor Mick explored the concept of idolatry and our journey to freedom from it. He emphasized how idolatry arises from our fears and insecurities, and how redirecting our worship to God is key to experiencing true freedom.'),
 ('Freedom From Bitterness', 'In this sermon, Pastor Jason Ramos explores the challenging topic of freedom from bitterness. Drawing from personal experiences and Scripture, he guides us through the process of identifying unforgiveness in our lives and embracing the transformative power of God’s grace.'),
 ('Freedom From Rebellion', 'Pastor Zach contrasts modern culture\'s view of freedom with Jesus\'s vision of true freedom. While our culture’s view of freedom leads to bondage, submission to Jesus leads to true and lasting freedom and and joy.'),
 ('Freedom From Pride', 'Through personal stories and Biblical wisdom, Joe Ewen illustrates how pride can imprison us while humility opens the door to God’s transformative grace. The sermon challenges us to examine our hearts, recognize areas of pride — both obvious and subtle — and embrace the freedom that comes through practicing genuine humility.'),
 ('Freedom From Lies', 'In this powerful message about freedom from lies and deception, Pastor Vincent Carpenter explores how deception can subtly influence our lives and relationships. Through Biblical examples and personal stories, he reveals how identifying lies and embracing God’s truth can lead to genuine freedom.'),
 ('The Freedom of Walking In The Spirit', 'The sermon explores the biblical concept of walking in the freedom of the Spirit. The speaker unpacks the contrast between the "flesh" and the "Spirit" and how we can align our minds, yield our will, and bring our emotions to God in order to experience the fruit of the Spirit - love, joy, peace, patience, kindness, goodness, faithfulness, gentleness, and self-control.'),
 ('Freedom From Generational Bondage', 'Understanding the impact of generational patterns — both blessings and curses — is vital for our spiritual growth and family legacy. In this powerful message, Pastor Jimmy Seibert explores how God\'s design for blessing can overcome generational struggles through Jesus Christ.'),
]

def freedom():
    sermons = ''.join(f'<h3>Pt {i} · {esc(t)}</h3><p>{esc(x)}</p>' for i, (t, x) in enumerate(FREEDOM_SERMONS, 1))
    body = f'''<section class="hero">
<p class="eyebrow">A 40 Day Journey</p>
<h1>40 Days of Freedom</h1>
<p class="lede">Designed to help you grow in the freedom and healing that Jesus died to give you.</p>
</section>
<div class="wide-photo"><img src="{photo(CDN + '81206524-64b1-41f4-9951-e1a2289c68a0/33521628-10A7-483B-BF08-6D3377ADB886.JPG')}" alt=""></div>
<div class="prose" style="padding-top:72px">
<p>We believe freedom and healing are for all God’s people and learning to walk in them is a key part of the abundant life Jesus desires for all of us.</p>
<h2>Journey to Freedom</h2>
<p>Our Journey To Freedom teaching series from the Fall of 2024 provides inspiration and practical, biblical foundations for walking in freedom and healing in Jesus. We encourage you to watch or listen to each one.</p>
{sermons}
</div>
<section class="closing"><blockquote>“Now may the God of peace himself sanctify you completely, and may your whole spirit and soul and body be kept blameless at the coming of our Lord Jesus Christ. He who calls you is faithful; he will surely do it.”</blockquote><p class="ref">1 Thessalonians 5:23-24</p></section>'''
    write('40-days-of-freedom.html', shell('40 Days of Freedom', 'Grow in the freedom and healing that Jesus died to give you.', '/40-days-of-freedom', body))

def notices():
    write('whats-next.html', shell('You are all signed up! · 40 Day Journeys', 'You are signed up for a 40 Day Journey.', '/whats-next',
        '<section class="notice"><h1>You are all signed up!</h1><p>Each morning at 3am (starting tomorrow morning) you will receive a link in your inbox to the devotional for that day!</p><a class="btn" href="/">Back to 40 Day Journeys</a></section>'))
    write('404.html', shell('Page not found · 40 Day Journeys', 'Page not found.', '/404',
        '<section class="notice"><h1>This page has moved</h1><p>The page you were looking for isn’t here anymore. Every day of both journeys is still on the site.</p><a class="btn" href="/devotion#days">40 Days of Devotion</a> <a class="btn btn-outline" href="/40-days-of-discipleship#days">40 Days of Discipleship</a></section>'))

devotion_landing(); discipleship_landing(); home(); freedom(); notices()

# ---------- launch files ----------
paths = ['/', '/devotion', '/40-days-of-discipleship', '/40-days-of-freedom'] + ['/devos/' + d['slug'] for _, d in DEV] + ['/discipleship/' + d['slug'] for _, d in DISC]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{DOMAIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
write('_redirects', '''# Old Squarespace addresses
/40-day-journeys          /                          301
/home                     /                          301
/devos                    /devotion#days             301
/devos/pass-it-on         /devos/peter-and-john      301
/discipleship             /40-days-of-discipleship   301
/group-events             /                          301
/cart                     /                          301
# Not built yet (the old page was mostly placeholder text)
/40-days-in-the-spirit    /                          302
''')
print(f'Built {len(DEV)} devotion days, {len(DISC)} discipleship pages, landing pages and launch files.')
