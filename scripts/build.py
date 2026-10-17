"""Build willmair.com: wraps each pages/*.html in the shared layout and writes it to the site root.

Usage:  python3 scripts/build.py

Each page file starts with a comment block of settings, then the page body:
  <!--
  title: Speaking
  description: One sentence for search engines and link previews.
  -->

Placeholders you can use in a page body:
  {{WAVE}}           the decaying homeodynamics wave (signature line)
  {{FEATURED}}       the featured podcast from data/media.json, with listen buttons
  {{MEDIA_LIST}}     the full speaking & media list, with filter chips
  {{PRESS_STRIP}}    the five most recent press/essay items
  {{PODCASTS}}       all podcasts, as cards with listen buttons
"""
import html, json, math, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
SITE = "https://willmair.com"
V = str(int(time.time()))  # cache-busting version stamp
PREVIEW = False  # True = tell search engines not to index (preview at willmair.github.io). Set False when willmair.com switches over.

NAV = [
    ("ideas.html", "Ideas"),
    ("geroscience.html", "Geroscience"),
    ("speaking.html", "Speaking"),
    ("media.html", "Media"),
    ("advocacy.html", "Advocacy"),
    ("advising.html", "Advising"),
    ("about.html", "About"),
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LISTEN = {"spotify": "Spotify", "apple": "Apple Podcasts", "youtube": "YouTube"}

e = lambda s: html.escape(s or "", quote=True)


def wave(width=640, height=64, cycles=7.5, decay=1.9, cls="sig-wave"):
    """Decaying cosine (wide dynamic range in youth, narrowing with age), mint → amber."""
    cy, a0, n, pts = height / 2, height / 2 - 3, 360, []
    for i in range(n + 1):
        t = i / n
        pts.append(f"{width * t:.1f} {cy - a0 * math.exp(-decay * t) * math.cos(2 * math.pi * cycles * t):.1f}")
    gid = f"wg{width}"
    return (f'<svg class="{cls}" viewBox="0 -2 {width} {height + 4}" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" x2="1"><stop offset="0" stop-color="#3E9A8D"/>'
            f'<stop offset=".22" stop-color="#3F7FD6"/><stop offset=".45" stop-color="#4E62E0"/>'
            f'<stop offset=".65" stop-color="#7A50DF"/><stop offset=".82" stop-color="#A5687A"/>'
            f'<stop offset="1" stop-color="#C9762E"/></linearGradient></defs>'
            f'<path d="M{" L".join(pts)}" fill="none" stroke="url(#{gid})" stroke-width="2.4" '
            f'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" pathLength="1"/></svg>')


def nice_date(d):
    parts = d.split("-")
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}" if len(parts) > 1 else parts[0]


def media():
    items = json.loads((ROOT / "data" / "media.json").read_text())["items"]
    return sorted(items, key=lambda m: m["date"], reverse=True)


def listen_buttons(links):
    return "".join(
        f'<a class="listen listen-{k}" href="{e(links[k])}" target="_blank" rel="noopener">{LISTEN[k]}</a>'
        for k in ("spotify", "apple", "youtube") if links and links.get(k))


def featured():
    m = next((m for m in media() if m.get("featured")), None)
    if not m:
        return ""
    return f"""<article class="featured-listen">
  <div class="fl-meta"><span class="kicker">Featured listen</span><span>{e(m["source"])} · {nice_date(m["date"])}</span></div>
  <h3><a href="{e(m["url"])}" target="_blank" rel="noopener">{e(m["title"])}</a></h3>
  {f'<p>{e(m["blurb"])}</p>' if m.get("blurb") else ""}
  <div class="listen-row">{listen_buttons(m.get("links"))}</div>
</article>"""


def media_row(m):
    title = (f'<a href="{e(m["url"])}" target="_blank" rel="noopener">{e(m["title"])}</a>'
             if m.get("url") else e(m["title"]))
    extra = listen_buttons(m.get("links")) if m["type"] in ("Podcast", "Talk") else ""
    return f"""<li class="m-row" data-type="{e(m["type"])}">
  <span class="m-date">{nice_date(m["date"])}</span>
  <div class="m-body">
    <span class="m-source">{e(m["source"])}<span class="m-role">{e(m.get("role", m["type"]))}</span></span>
    <h3 class="m-title">{title}</h3>
    {f'<p>{e(m["blurb"])}</p>' if m.get("blurb") else ""}
    {f'<div class="listen-row">{extra}</div>' if extra else ""}
  </div>
</li>"""


def media_list():
    items = media()
    types = [t for t in ("Podcast", "Press", "Essay", "Talk", "Radio") if any(m["type"] == t for m in items)]
    plural = {"Press": "Press", "Radio": "Radio"}
    chips = '<button class="chip" aria-pressed="true" data-filter="all">All</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-filter="{t}">{plural.get(t, t + "s")}</button>' for t in types)
    return f'<div class="chips" role="group" aria-label="Filter">{chips}</div>\n<ol class="m-list">\n' + \
        "\n".join(media_row(m) for m in items) + "\n</ol>"


def press_strip():
    items = [m for m in media() if m["type"] in ("Press", "Essay") and m.get("url")][:5]
    return '<ul class="press-strip">' + "".join(
        f'<li><a href="{e(m["url"])}" target="_blank" rel="noopener"><span class="ps-source">{e(m["source"])}</span>'
        f'<span class="ps-title">{e(m["title"])}</span><span class="ps-date">{nice_date(m["date"])}</span></a></li>'
        for m in items) + "</ul>"


def podcasts():
    def card(m):
        blurb = f'<p>{e(m["blurb"])}</p>' if m.get("blurb") else ""
        return (f'<article class="pod"><span class="kicker">{e(m["source"])} · {nice_date(m["date"])}</span>'
                f'<h3><a href="{e(m["url"])}" target="_blank" rel="noopener">{e(m["title"])}</a></h3>{blurb}'
                f'<div class="listen-row">{listen_buttons(m.get("links"))}</div></article>')
    return '<div class="pod-grid">' + "".join(card(m) for m in media() if m["type"] == "Podcast" and not m.get("featured")) + "</div>"


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="William Mair">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="William Mair">
<meta name="twitter:card" content="summary_large_image">
{robots}<meta name="google-site-verification" content="LFT4IbH0KqM2VjvNQJcDmfEyh3unQygv19Ih4QHBUlo">
<meta name="theme-color" content="#F7F4EE">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/style.css?v={v}">
{jsonld}</head>
<body class="page-{slug}">
<!-- Generated by scripts/build.py from pages/{src} — edit that file, not this one. -->
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="index.html"><span class="brand-name">William Mair</span>{mini_wave}</a>
    <button class="nav-toggle" aria-label="Menu" aria-expanded="false"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 8h16M4 16h16"/></svg></button>
    <nav class="nav" aria-label="Main">
{nav}
      <a class="nav-ext" href="https://themairlab.com" target="_blank" rel="noopener">Research <span aria-hidden="true">↗</span></a>
      <a class="nav-cta" href="contact.html"{contact_current}>Get in touch</a>
    </nav>
  </div>
</header>
<main id="main">
"""

FOOT = """</main>
<footer class="site-footer">
  <div class="wrap">
    <div class="foot-cta">
      <p class="foot-line">Speaking, media or advising?</p>
      <div class="btn-row">
        <a class="btn btn-dark" href="contact.html?topic=speaking">Invite me to speak</a>
        <a class="btn btn-ghost-light" href="contact.html?topic=media">Media request</a>
        <a class="btn btn-ghost-light" href="contact.html?topic=advising">Advising enquiry</a>
      </div>
    </div>
    {wave}
    <div class="foot-grid">
      <div>
        <p class="foot-name">William Mair</p>
        <p class="foot-sub">Professor of Molecular Metabolism, Harvard T.H. Chan School of Public Health · Director, Harvard Chan Healthy Aging Initiative</p>
      </div>
      <div>
        <h4>Research</h4>
        <ul>
          <li><a href="https://themairlab.com" target="_blank" rel="noopener">The MAIR Lab</a></li>
          <li><a href="https://themairlab.com/publications.html" target="_blank" rel="noopener">Publications</a></li>
          <li><a href="https://hsph.harvard.edu/research/healthy-aging/" target="_blank" rel="noopener">Healthy Aging Initiative</a></li>
        </ul>
      </div>
      <div>
        <h4>Elsewhere</h4>
        <ul>
          <li><a href="https://www.linkedin.com/in/willmair/" target="_blank" rel="noopener">LinkedIn</a></li>
          <li><a href="https://www.instagram.com/william_mair/" target="_blank" rel="noopener">Instagram</a></li>
          <li><a href="https://hsph.harvard.edu/profile/william-b-mair/" target="_blank" rel="noopener">Harvard Chan profile</a></li>
          <li><a href="https://orcid.org/0000-0002-0661-1342" target="_blank" rel="noopener">ORCID</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-base"><span>© <span data-year>2026</span> William Mair</span><span>Views here are my own.</span></div>
  </div>
</footer>
<script src="assets/js/main.js?v={v}"></script>
</body>
</html>
"""

JSONLD = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","name":"William Mair","alternateName":"William B. Mair","url":"https://willmair.com","image":"https://willmair.com/assets/img/william-mair-formal.jpg","jobTitle":"Professor of Molecular Metabolism","worksFor":{"@type":"Organization","name":"Harvard T.H. Chan School of Public Health"},"alumniOf":[{"@type":"CollegeOrUniversity","name":"University College London"}],"sameAs":["https://themairlab.com","https://www.linkedin.com/in/willmair/","https://orcid.org/0000-0002-0661-1342","https://hsph.harvard.edu/profile/william-b-mair/"]}
</script>
"""


def build():
    blocks = {"{{WAVE}}": wave(), "{{WAVE_WIDE}}": wave(1200, 40, 12, 1.6, "foot-wave"), "{{FEATURED}}": featured(), "{{MEDIA_LIST}}": media_list(),
              "{{PRESS_STRIP}}": press_strip(), "{{PODCASTS}}": podcasts()}
    mini = wave(64, 14, 4, 1.7, "brand-wave")
    for src in sorted(PAGES.glob("*.html")):
        text = src.read_text()
        m = re.match(r"\s*<!--(.*?)-->\s*", text, re.S)
        meta = dict(re.findall(r"^\s*(\w+):\s*(.+?)\s*$", m.group(1), re.M)) if m else {}
        body = text[m.end():] if m else text
        for k, v in blocks.items():
            body = body.replace(k, v)
        name = src.name
        current = ' aria-current="page"'
        nav = "\n".join(
            f'      <a href="{href}"{current if href == name else ""}>{label}</a>'
            for href, label in NAV)
        title = meta.get("title", "William Mair")
        full_title = title if title.startswith("William Mair") else f"{title} · William Mair"
        url = SITE + "/" + ("" if name == "index.html" else name)
        out = HEAD.format(title=e(full_title), description=e(meta.get("description", "")), url=url, site=SITE,
                          slug=name[:-5], src=name, nav=nav, v=V, mini_wave=mini,
                          jsonld=JSONLD if name == "index.html" else "",
                          robots='<meta name="robots" content="noindex, nofollow">\n' if PREVIEW or name == "404.html" else "",
                          contact_current=' aria-current="page"' if name == "contact.html" else "")
        out += body.rstrip() + "\n" + FOOT.format(v=V, wave=wave(1200, 40, 12, 1.6, "foot-wave"))
        (ROOT / name).write_text(out)
        print("built", name)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{SITE}/{'' if p.name == 'index.html' else p.name}</loc></url>\n"
                for p in sorted(PAGES.glob("*.html")) if p.name != "404.html") + "</urlset>\n")


if __name__ == "__main__":
    build()
