#!/usr/bin/env python3
"""Builds the site into dist/. Pure standard library, no installs.

    python build.py            build once
    python build.py --drafts   also build guides marked `status: draft`
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


# ---------------------------------------------------------------- helpers

def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s), quote=True)


def slugify(s):
    s = re.sub(r"<[^>]+>", "", str(s)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def fill(template, **values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), "")), template)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def num(i):
    return f"{i:02d}"


# ---------------------------------------------------------------- markdown
# A small Markdown subset: headings, paragraphs, lists, checkboxes,
# pipe tables, blockquotes, callouts (> [!TBD] / [!TIP] / [!WARN]),
# bold, italic, code, links and images.

CALLOUTS = {"tbd": "Fill in at launch", "tip": "Tip", "warn": "Heads up"}


def inline(s):
    s = esc(s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1" loading="lazy">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*", r"<em>\1</em>", s)
    return s


def markdown(src, page_key):
    out, toc = [], []
    para, table = [], []
    lst = None  # [tag, class_attr, items]

    def flush_para():
        nonlocal para
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para = []

    def flush_list():
        nonlocal lst
        if lst:
            tag, cls, items = lst
            out.append(f"<{tag}{cls}>{''.join(items)}</{tag}>")
            lst = None

    def flush_table():
        nonlocal table
        if table:
            rows = [
                [c.strip() for c in r.strip().strip("|").split("|")]
                for r in table
                if not re.match(r"^\|?\s*:?-{3,}", r.strip())
            ]
            head, body = rows[0], rows[1:]
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            table = []

    def flush_all():
        flush_para()
        flush_list()
        flush_table()

    def list_item(tag, cls, item_html):
        nonlocal lst
        flush_para()
        flush_table()
        if not lst or lst[0] != tag or lst[1] != cls:
            flush_list()
            lst = [tag, cls, []]
        lst[2].append(item_html)

    for raw in src.replace("\r", "").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush_all()
            continue
        if line.lstrip().startswith("|"):
            flush_para()
            flush_list()
            table.append(line)
            continue
        flush_table()

        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush_all()
            level = len(m.group(1)) + 1  # page title is the only h1
            text = m.group(2)
            hid = slugify(text)
            if level == 2:
                toc.append((hid, text))
            out.append(f'<h{level} id="{hid}">{inline(text)}</h{level}>')
            continue

        m = re.match(r"^>\s?\[!(\w+)\]\s*(.*)$", line)
        if m:
            flush_all()
            kind = m.group(1).lower()
            label = CALLOUTS.get(kind, kind.title())
            out.append(f'<div class="callout callout-{kind}"><span class="callout-label">{label}</span> {inline(m.group(2))}</div>')
            continue

        m = re.match(r"^>\s?(.*)$", line)
        if m:
            flush_all()
            out.append(f"<blockquote>{inline(m.group(1))}</blockquote>")
            continue

        m = re.match(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$", line)
        if m:
            key = f"{page_key}:{slugify(m.group(2))}"
            list_item("ul", ' class="checks"',
                      f'<li><label><input type="checkbox" data-check="{esc(key)}"> <span>{inline(m.group(2))}</span></label></li>')
            continue

        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            list_item("ol", "", f"<li>{inline(m.group(1))}</li>")
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            list_item("ul", "", f"<li>{inline(m.group(1))}</li>")
            continue

        flush_list()
        para.append(line.strip())

    flush_all()
    return "\n".join(out), toc


def front_matter(src):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", src, re.S)
    if not m:
        return {}, src
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data, src[m.end():]


# ---------------------------------------------------------------- shared blocks

def article_head(kicker, title, dek="", byline=""):
    return (
        '<header class="article-head">'
        f'<p class="kicker">{kicker}</p>'
        f"<h1>{esc(title)}</h1>"
        + (f'<p class="dek">{esc(dek)}</p>' if dek else "")
        + (f'<p class="byline">{byline}</p>' if byline else "")
        + "</header>"
    )


def progress_block():
    return ('<div class="progress" hidden><span class="big"></span>'
            '<div class="bar"><span></span></div><small></small></div>')


# ---------------------------------------------------------------- site

class Site:
    def __init__(self, drafts=False):
        self.cfg = load_json("data/site.json")
        self.map = load_json("data/map.json")
        self.markers = load_json("data/markers.json")["markers"]
        self.checklist = load_json("data/checklist.json")
        self.updates = sorted(load_json("data/updates.json")["updates"], key=lambda u: u["time"], reverse=True)
        self.layout = (ROOT / "src/templates/layout.html").read_text(encoding="utf-8")
        self.drafts = drafts
        self.pages = []         # (url, lastmod) for the sitemap
        self.search = []        # search index entries
        self.today = dt.date.today().isoformat()
        self.guides = self.load_guides()

    # ---- content

    def load_guides(self):
        guides = []
        for path in sorted((ROOT / "content/guides").glob("*.md")):
            meta, body = front_matter(path.read_text(encoding="utf-8"))
            if meta.get("status") == "draft" and not self.drafts:
                continue
            slug = meta.get("slug") or path.stem
            body_html, toc = markdown(body, slug)
            guides.append({
                "slug": slug,
                "url": f"/guides/{slug}/",
                "title": meta.get("title", slug),
                # <title> for search results: keep under ~60 chars, keyword first
                "seo_title": meta.get("seo_title", meta.get("title", slug)),
                "published": meta.get("published", meta.get("updated", self.today)),
                "short": meta.get("short", meta.get("title", slug)),
                "description": meta.get("description", ""),
                "order": int(meta.get("order", 100)),
                "updated": meta.get("updated", self.today),
                "status": meta.get("status", "live"),
                "html": body_html,
                "toc": toc,
            })
        guides.sort(key=lambda g: (g["order"], g["title"]))
        for i, g in enumerate(guides, 1):
            g["num"] = num(i)
        return guides

    # ---- output

    def nav(self, current):
        links = [("/map/", "Map"), ("/guides/", "Guides"), ("/checklist/", "Checklist"),
                 ("/updates/", "Live log"), ("/tip/", "Tip jar")]
        items = []
        for href, label in links:
            cur = ' aria-current="page"' if current.startswith(href) else ""
            items.append(f'<a href="{href}"{cur}>{label}</a>')
        return "".join(items)

    def ad(self, slot):
        return f'<div class="ad-slot" data-ad="{slot}"></div>'

    def abs_url(self, path):
        return self.cfg["url"].rstrip("/") + path

    def og_image_for(self, slug=None):
        if slug and (ROOT / "static" / "og" / f"{slug}.png").exists():
            return self.abs_url(f"/og/{slug}.png")
        return self.abs_url("/og/default.png")

    def write(self, url, title, description, body, head_extra="", scripts="",
              lastmod=None, index=True, search_text=None, seo_title=None,
              og_image=None, og_type="website"):
        cfg = self.cfg
        page_title = seo_title or title
        full_title = page_title if url == "/" else f"{page_title} | {cfg['name']}"
        canonical = self.abs_url(url)
        robots = ("index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
                  if index else "noindex, follow")
        classes = []
        if url != "/":
            classes.append("inner")
        if cfg.get("showAdPlaceholders"):
            classes.append("show-ad-placeholders")
        page = fill(
            self.layout,
            title=esc(full_title),
            og_title=esc(page_title),
            og_type=og_type,
            og_image=esc(og_image or self.og_image_for()),
            robots=robots,
            description=esc(description),
            canonical=esc(canonical),
            site_name=esc(cfg["name"]),
            nav=self.nav(url),
            body=body,
            head_extra=cfg.get("headHtml", "") + head_extra,
            scripts=scripts,
            body_class=" ".join(classes),
            launch=esc(cfg["launchDate"]),
            ticker=self.ticker(),
            footer_guides="".join(f'<a href="{g["url"]}">{esc(g["short"])}</a>' for g in self.guides[:8]),
            year=dt.date.today().year,
            tip_url="/tip/",
            disclaimer=esc(cfg["disclaimer"]),
            affiliate_note=esc(cfg["affiliateNote"]),
        )
        target = DIST / "404.html" if url == "/404.html" else DIST / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        if index:
            self.pages.append((url, lastmod or self.today))
            self.search.append({
                "title": title, "url": url, "type": "page",
                "text": (search_text if search_text is not None else description)[:600],
            })

    def confirmed_cheats(self):
        """Counts rows in the cheats guide's confirmed table, so the home stat can't drift from the guide."""
        g = next((g for g in self.guides if g["slug"] == "gta-6-cheats"), None)
        if not g:
            return 0
        m = re.search(r'id="confirmed-codes".*?<tbody>(.*?)</tbody>', g["html"], re.S)
        return m.group(1).count("<tr>") if m else 0

    def ticker(self):
        """Scrolling strip of the newest live-log entries, shown under the nav on every page."""
        if not self.updates:
            return ""
        parts = []
        for u in self.updates[:6]:
            text = html.unescape(strip_tags(inline(u["text"])))
            if len(text) > 120:
                text = text[:117].rsplit(" ", 1)[0] + "…"
            link = re.search(r"\]\((/[^)\s]*)\)", u["text"])
            href = link.group(1) if link else "/updates/"
            parts.append(f'<a href="{esc(href)}">{esc(text)}</a><span class="sep" aria-hidden="true">✦</span>')
        run = "".join(parts)
        return ('<div class="ticker" role="region" aria-label="Latest updates">'
                '<a class="ticker-label" href="/updates/"><span class="live-dot"></span>Live</a>'
                f'<div class="ticker-viewport"><div class="ticker-track">{run}<span aria-hidden="true" class="dup">{run}</span></div></div>'
                '</div>')

    def updates_list(self, updates):
        if not updates:
            return '<p class="muted">Nothing yet. Check back on launch day.</p>'
        rows = "".join(
            f'<li><time datetime="{esc(u["time"])}" data-rel></time><span>{inline(u["text"])}</span></li>'
            for u in updates
        )
        return f'<ul class="updates">{rows}</ul>'

    def tiles(self, items):
        """Equal-width tiles: items are (num, title, text, href)."""
        return '<div class="tiles">' + "".join(
            f'<a class="tile" href="{href}"><span class="num">{n}</span><h3>{esc(t)}</h3><p>{esc(p)}</p></a>'
            for n, t, p, href in items) + "</div>"

    # ---- pages

    def build_home(self):
        cfg = self.cfg
        index = "".join(
            f'<li><a href="{g["url"]}"><span class="num">{g["num"]}</span><span class="t">{esc(g["short"])}</span></a></li>'
            for g in self.guides[:8])
        body = f"""
<section class="front">
  <aside>
    <h2 class="rule-head">Latest finds</h2>
    {self.updates_list(self.updates[:4])}
    <a class="more" href="/updates/">Full live log &rarr;</a>
  </aside>
  <div class="feature">
    <a class="feature-media" href="/map/">
      <img src="/images/leonida-schematic.svg" alt="Schematic map of Leonida" width="2048" height="2048">
      <span class="tag">Explore Leonida &rarr;</span>
    </a>
    <p class="status-pill"><span class="live-dot"></span>Out now &middot; PS5 &amp; Xbox Series X|S</p>
    <h1>{esc(cfg['headline'])}</h1>
    <p class="dek">{esc(cfg['tagline'])}</p>
    <div class="cta">
      <a class="btn btn-primary" href="/map/">Open the map</a>
      <a class="btn" href="/guides/gta-6-first-48-hours/">What to do first</a>
    </div>
    <div class="search hero-search">
      <input id="search" type="search" placeholder="Search guides, places, cheats…" autocomplete="off" aria-label="Search the site">
      <div id="search-results" class="search-results" hidden></div>
    </div>
  </div>
  <aside>
    <h2 class="rule-head">The guides</h2>
    <ol class="index-list">{index}</ol>
    <a class="more" href="/guides/">All {len(self.guides)} guides &rarr;</a>
  </aside>
</section>
<section class="stats" aria-label="What's on the site">
  <a href="/guides/"><b>{len(self.guides)}</b><span>Guides</span></a>
  <a href="/map/"><b>{len(self.markers)}</b><span>Places mapped</span></a>
  <a href="/guides/gta-6-cheats/"><b>{self.confirmed_cheats()}</b><span>Confirmed cheats</span></a>
  <a href="/updates/"><b>{len(self.updates)}</b><span>Live updates</span></a>
</section>
{self.ad('home-top')}
{self.tiles([
    ("01", "Cheat codes", "Every cheat code that two or more guides agree on, plus what unlocks each one.", "/guides/gta-6-cheats/"),
    ("02", "Make money", "Every money method by chapter, from early drug runs to $205,000 bank vaults.", "/guides/gta-6-make-money-fast/"),
    ("03", "The live log", "New confirmed info, newest first, all launch week.", "/updates/"),
])}
<section class="band">
  <p class="kicker">Reader finds</p>
  <h2>Found something?</h2>
  <p>Send us a location, money method or secret. Confirmed finds go on the map with your name on them.</p>
  <a class="btn btn-primary" href="/submit/">Submit a find</a>
</section>"""
        base = cfg["url"].rstrip("/")
        ld = json.dumps([
            {"@context": "https://schema.org", "@type": "WebSite", "name": cfg["name"], "url": base + "/",
             "description": cfg["tagline"], "inLanguage": "en-US"},
            {"@context": "https://schema.org", "@type": "Organization", "name": cfg["name"], "url": base + "/",
             "logo": base + "/og/logo.png"},
        ]).replace("</", "<\\/")
        self.write("/", f"{cfg.get('homeTitle', cfg['headline'])} | {cfg['name']}", cfg["tagline"], body,
                   head_extra=f'<script type="application/ld+json">{ld}</script>')

    def build_updates(self):
        body = article_head("Live log", "Everything confirmed so far",
                            "Every find we've checked, newest first. This page updates through launch week.")
        body += f'<div class="log">{self.updates_list(self.updates)}{self.ad("updates-top")}</div>'
        last = self.updates[0]["time"][:10] if self.updates else None
        self.write("/updates/", "GTA 6 live log: new finds as they're confirmed",
                   "Every confirmed GTA 6 find, location and money method, newest first.", body, lastmod=last)

    def build_guides(self):
        for g in self.guides:
            toc = ""
            if g["toc"]:
                toc = ('<nav class="toc sticky" aria-label="On this page"><h2 class="rule-head">In this guide</h2><ol>'
                       + "".join(f'<li><a href="#{hid}">{inline(t)}</a></li>' for hid, t in g["toc"])
                       + "</ol></nav>")
            content = g["html"].replace("<h2", self.ad("guide-mid") + "<h2", 1)
            # spread internal links: each guide points at the next three in order (wrapping)
            i = self.guides.index(g)
            related = [self.guides[(i + k) % len(self.guides)] for k in (1, 2, 3) if len(self.guides) > k]
            badge = ' &middot; <span class="badge badge-warn">Pre-launch draft</span>' if g["status"] == "prelaunch" else ""
            page_url = self.abs_url(g["url"])
            org = {"@type": "Organization", "name": self.cfg["name"], "url": self.abs_url("/"),
                   "logo": {"@type": "ImageObject", "url": self.abs_url("/og/logo.png")}}
            ld = json.dumps([
                {
                    "@context": "https://schema.org", "@type": "Article",
                    "headline": g["seo_title"][:110], "description": g["description"],
                    "image": [self.og_image_for(g["slug"])],
                    "datePublished": g["published"], "dateModified": g["updated"],
                    "author": org, "publisher": org,
                    "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
                    "about": {"@type": "VideoGame", "name": "Grand Theft Auto VI",
                              "gamePlatform": ["PlayStation 5", "Xbox Series X|S"]},
                },
                {
                    "@context": "https://schema.org", "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Home", "item": self.abs_url("/")},
                        {"@type": "ListItem", "position": 2, "name": "Guides", "item": self.abs_url("/guides/")},
                        {"@type": "ListItem", "position": 3, "name": g["short"], "item": page_url},
                    ],
                },
            ]).replace("</", "<\\/")
            body = article_head(
                f'<a href="/guides/">Guide No. {g["num"]}</a>', g["title"], g["description"],
                f'Updated <time datetime="{esc(g["updated"])}">{esc(g["updated"])}</time>{badge}')
            body += f"""
<div class="article-grid" data-check-scope>
  <aside class="article-rail left">{toc}</aside>
  <article class="prose">{content}</article>
  <aside class="article-rail right">
    <div class="sticky">
      {progress_block()}
      {self.tip_card()}
      {self.ad('guide-rail')}
      <p class="rail-note small">Spotted something wrong or missing? <a href="/submit/">Send it in</a> and we'll credit you.</p>
    </div>
  </aside>
</div>
<div class="tip-inline">{self.tip_card()}</div>
<section class="read-next">
  <h2 class="rule-head center">Keep reading</h2>
  {self.tiles([(o["num"], o["short"], o["description"], o["url"]) for o in related])}
</section>"""
            head = (f'<script type="application/ld+json">{ld}</script>'
                    f'<meta property="article:published_time" content="{esc(g["published"])}">'
                    f'<meta property="article:modified_time" content="{esc(g["updated"])}">')
            self.write(g["url"], g["title"], g["description"], body, head_extra=head,
                       lastmod=g["updated"], search_text=g["description"] + " " + strip_tags(g["html"]),
                       seo_title=g["seo_title"], og_image=self.og_image_for(g["slug"]), og_type="article")

        rows = "".join(
            f'<li><a href="{g["url"]}"><span class="num">{g["num"]}</span>'
            f'<div><h2>{esc(g["short"])}</h2><p>{esc(g["description"])}</p></div>'
            f'<span class="arrow" aria-hidden="true">&rarr;</span></a></li>'
            for g in self.guides)
        body = article_head("Contents", "The guides",
                            "Short, practical guides, updated as the game gets figured out.")
        body += f'<ol class="toc-index">{rows}</ol>'
        self.write("/guides/", "All GTA 6 Guides & Walkthrough Help", f"Every {self.cfg['name']} guide for GTA 6 in one place.", body)

    def build_checklist(self):
        c = self.checklist
        sections, nav = [], []
        for s in c["sections"]:
            sid = slugify(s["title"])
            nav.append(f'<li><a href="#{sid}">{esc(s["title"])}</a></li>')
            items = []
            for it in s["items"]:
                tag = "" if it.get("verified") else ' <span class="badge">unconfirmed</span>'
                link = f'<a href="{esc(it["link"])}">How &rarr;</a>' if it.get("link") else ""
                items.append(
                    f'<li><label><input type="checkbox" data-check="checklist:{esc(it["id"])}"> '
                    f'<span>{inline(it["text"])}{tag}{link}</span></label></li>')
            sections.append(f'<h2 id="{sid}">{esc(s["title"])}</h2><ul class="checks">{"".join(items)}</ul>')
        body = article_head("Checklist", c["title"], c["intro"])
        body += f"""
<div class="article-grid" data-check-scope>
  <aside class="article-rail left">
    <nav class="toc sticky" aria-label="Sections"><h2 class="rule-head">Sections</h2><ol>{''.join(nav)}</ol></nav>
  </aside>
  <article class="prose checklist">{''.join(sections)}</article>
  <aside class="article-rail right">
    <div class="sticky">
      {progress_block()}
      {self.ad('checklist-rail')}
      <p class="rail-note small">Your ticks are saved in this browser only.</p>
    </div>
  </aside>
</div>"""
        text = " ".join(it["text"] for s in c["sections"] for it in s["items"])
        self.write("/checklist/", c["title"], c["intro"], body, search_text=c["intro"] + " " + text)

    def build_map(self):
        cats = {c["id"]: c for c in self.map["categories"]}
        regions = self.map["regions"]
        # static list (for search engines and no-JS readers), grouped by region
        groups = []
        for r in regions:
            ms = [m for m in self.markers if m.get("region") == r["id"]]
            if not ms:
                continue
            lis = "".join(
                f'<li><a href="/map/#m={esc(m["id"])}">{esc(m["title"])}</a>'
                f'<span class="muted"> · {esc(m.get("place", ""))}</span><br>{esc(m.get("desc", ""))}</li>'
                for m in ms)
            groups.append(f'<div class="group"><h3><span class="swatch" style="--c:{r["color"]}"></span>'
                          f'{esc(r["name"])} ({len(ms)})</h3><ul>{lis}</ul></div>')
        for m in self.markers:
            self.search.append({
                "title": m["title"], "url": f"/map/#m={m['id']}",
                "type": cats.get(m["category"], {}).get("label", "Map"),
                "text": (m.get("place", "") + " " + m.get("desc", ""))[:300],
            })
        region_cards = "".join(
            f'<a class="region-card" href="/map/#r={esc(r["id"])}" style="--c:{r["color"]}">'
            f'<span class="rc-n">{sum(1 for m in self.markers if m.get("region") == r["id"])} places</span>'
            f'<h3>{esc(r["name"])}</h3><p>{esc(r["desc"])}</p></a>'
            for r in regions)
        payload = dict(self.map, markers=self.markers)
        cfg_json = json.dumps(payload).replace("</", "<\\/")
        body = article_head("Interactive map", "Leonida",
                            "Search every place we've confirmed, filter by what you need, and track what you've found. "
                            "Click a region to explore it.")
        body += f"""
<div class="atlas" id="atlas" data-zoom="far">
  <div id="map" class="atlas-map" role="region" aria-label="Map of Leonida"></div>

  <aside class="atlas-panel" aria-label="Places on the map">
    <button type="button" class="sheet-handle" data-sheet aria-expanded="false">
      <span class="grip" aria-hidden="true"></span><span>Places <b id="atlas-count">0</b></span>
    </button>
    <div class="panel-head">
      <label class="atlas-search">
        <span class="sr-only">Search places</span>
        <input id="atlas-search" type="search" placeholder="Search places, fences, banks…" autocomplete="off">
        <kbd aria-hidden="true">/</kbd>
      </label>
      <div class="chips-row" id="atlas-chips" role="group" aria-label="Show categories"></div>
      <div class="panel-meta">
        <label class="toggle"><input type="checkbox" id="atlas-hide-found"> Hide found</label>
        <span id="atlas-progress"></span>
      </div>
      <div class="found-bar"><span id="atlas-bar"></span></div>
    </div>
    <div class="atlas-list" id="atlas-list"></div>
  </aside>

  <aside class="atlas-detail" id="atlas-detail" hidden aria-live="polite"></aside>

  <div class="atlas-tools" role="toolbar" aria-label="Map controls">
    <button type="button" data-zoom-in aria-label="Zoom in" title="Zoom in">+</button>
    <button type="button" data-zoom-out aria-label="Zoom out" title="Zoom out">&minus;</button>
    <button type="button" data-home aria-label="Reset view" title="Reset view">&#8634;</button>
    <button type="button" data-full aria-label="Full screen" title="Full screen">&#x26F6;</button>
  </div>
  <p class="atlas-note">Schematic map, not to scale. Pins sit in the right town or district; exact spots are added as they're verified.</p>
</div>
<p class="atlas-foot-note">Schematic map, not to scale. Pins sit in the right town or district; exact spots are added as they're verified.</p>

<div id="edit-box" class="edit-box" hidden>
  <p class="kicker">Edit mode</p>
  <p class="small">Click the map. A new place is copied for you to paste into <code>data/markers.json</code>.</p>
  <textarea id="edit-out" rows="7" readonly></textarea>
</div>

<section class="region-strip">
  <h2 class="rule-head center">Explore by region</h2>
  <div class="region-grid">{region_cards}</div>
</section>

<section class="map-list">
  <h2 class="rule-head center">Every place on the map</h2>
  <div class="cols">{''.join(groups)}</div>
  <p class="center small muted">Found something we're missing? <a href="/submit/">Submit a location</a>.</p>
</section>
<script type="application/json" id="map-config">{cfg_json}</script>"""
        head = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
        scripts = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" defer></script>'
                   '<script src="/assets/map.js" defer></script>')
        self.write("/map/", "GTA 6 Map of Leonida: Interactive Locations", 
                   "Interactive GTA 6 map of Leonida: fences, bank vaults, safehouses, money spots and missables. Search, filter and track what you've found.",
                   body, head_extra=head, scripts=scripts, seo_title="GTA 6 Map: Interactive Leonida Map")

    def build_submit(self):
        opts = "".join(f'<option value="{esc(c["id"])}">{esc(c["label"])}</option>'
                       for c in self.map["categories"])
        body = article_head("Reader finds", "Submit a find",
                            "Found a collectible, money method, secret or mistake on the site? We check every submission, and credit you if you want.")
        body += f"""
<div class="narrow">
  <form name="submit-find" method="POST" action="/thanks/" data-netlify="true" netlify-honeypot="bot-field" class="form">
    <input type="hidden" name="form-name" value="submit-find">
    <p hidden><label>Leave this empty <input name="bot-field"></label></p>
    <label>Type<select name="category" required>{opts}<option value="correction">Correction to the site</option></select></label>
    <label>What is it?<input name="what" required maxlength="140" placeholder="e.g. Hidden stash under the pier"></label>
    <label>Where is it, and how do you get it?<textarea name="where" rows="5" required></textarea></label>
    <label>Screenshot or video link <small>optional</small><input name="proof" type="url" placeholder="https://"></label>
    <label>Credit me as <small>optional</small><input name="credit" maxlength="40"></label>
    <button class="btn btn-primary" type="submit">Send it</button>
  </form>
</div>"""
        self.write("/submit/", "Submit a GTA 6 find", f"Send a location, money method or secret to {self.cfg['name']}.", body)
        self.write("/thanks/", "Thanks!", "Submission received.",
                   article_head("Reader finds", "Got it, thanks.", "We check every find before it goes on the map.")
                   + '<div class="cta"><a class="btn" href="/map/">Back to the map</a></div>', index=False)

    # ---- tip jar

    TIP_PROVIDERS = [
        # (config key, label, url template, supports amount in URL, note)
        ("kofi", "Ko-fi", "https://ko-fi.com/{h}", False, "Card, PayPal or Apple Pay. No account needed."),
        ("paypal", "PayPal", "https://paypal.me/{h}/{amount}USD", True, "Opens with your amount filled in."),
        ("cashapp", "Cash App", "https://cash.app/${h}/{amount}", True, "Opens with your amount filled in."),
        ("venmo", "Venmo", "https://venmo.com/u/{h}", False, "Enter the amount in Venmo."),
        ("buymeacoffee", "Buy Me a Coffee", "https://buymeacoffee.com/{h}", False, "Card or Apple Pay. No account needed."),
    ]

    def tip_providers(self):
        tj = self.cfg.get("tipJar", {})
        out = []
        for key, label, tmpl, has_amount, note in self.TIP_PROVIDERS:
            handle = str(tj.get(key, "")).strip().lstrip("$@")
            if handle:
                out.append((key, label, tmpl.replace("{h}", handle), has_amount, note))
        return out

    def tip_card(self):
        return ('<aside class="tip-card"><p class="kicker">Tip jar</p>'
                '<p>This guide is free and checked by hand. If it helped, a tip keeps it going.</p>'
                '<a class="btn btn-primary" href="/tip/">Leave a tip</a></aside>')

    def build_tip(self):
        tj = self.cfg.get("tipJar", {})
        providers = self.tip_providers()
        default = tj.get("defaultAmount", 5)
        chips = "".join(
            f'<button type="button" class="chip{" is-on" if a == default else ""}" data-amount="{a}" '
            f'aria-pressed="{"true" if a == default else "false"}">${a}</button>'
            for a in tj.get("amounts", [3, 5, 10, 25]))
        chips += ('<label class="chip chip-custom"><span>$</span>'
                  '<input type="number" min="1" max="999" step="1" inputmode="numeric" placeholder="Other" '
                  'aria-label="Custom amount" data-custom></label>')
        if providers:
            buttons = "".join(
                f'<a class="pay" data-provider="{key}" data-template="{esc(url)}" href="{esc(url.replace("{amount}", str(default)))}" '
                f'target="_blank" rel="noopener"><strong>{esc(label)}</strong><small>{esc(note)}</small></a>'
                for key, label, url, _, note in providers)
            pay = f'<div class="pay-grid">{buttons}</div>'
        elif self.cfg.get("showAdPlaceholders"):
            pay = ('<div class="callout callout-tbd"><span class="callout-label">Setup needed</span> Add at least one handle under '
                   '<code>tipJar</code> in <code>data/site.json</code> (Ko-fi, PayPal, Cash App, Venmo or '
                   'Buy Me a Coffee). The buttons appear automatically. This note only shows while '
                   '<code>showAdPlaceholders</code> is on.</div>')
        else:
            pay = '<p class="muted">The tip jar opens soon. Thanks for thinking of it.</p>'
        body = article_head("Support the atlas", tj.get("headline", "Tip jar"), tj.get("message", ""))
        body += f"""
<div class="narrow tipjar">
  <p class="kicker center">1 · Pick an amount</p>
  <div class="chips" role="group" aria-label="Tip amount">{chips}</div>
  <p class="kicker center">2 · Pick how to pay</p>
  {pay}
  <p class="fine center">Tips are a gift, not a purchase. You don't get anything extra, and the guide stays free for everyone. Payments go straight to the provider you pick; this site never sees your card details.</p>
  <div class="prose">
    <h2>Where tips go</h2>
    <ul>
      <li>Hosting and the domain, so the map and guides stay fast.</li>
      <li>Time spent checking every claim against at least two sources before it goes up.</li>
      <li>Keeping ads to a minimum.</li>
    </ul>
  </div>
</div>"""
        self.write("/tip/", "Tip jar", f"Support {self.cfg['name']}, the free GTA 6 field guide.", body, index=True)

    def build_about(self):
        cfg = self.cfg
        body = article_head("About", f"About {cfg['name']}",
                            "A small, fast fan guide for the first days of GTA 6.")
        body += f"""
<div class="narrow prose">
  <p>We focus on what players need early: where things are, what to do first, and how to make money. Short pages, fast answers, and a map you can link to.</p>
  <h2>How we confirm things</h2>
  <p>Items marked <span class="badge">unconfirmed</span> are expected but not yet checked in the released game. We remove the tag once we, or a credited player, have confirmed it in-game.</p>
  <h2>Disclaimer</h2>
  <p>{esc(cfg['disclaimer'])}</p>
  <p>{esc(cfg['affiliateNote'])}</p>
  <h2>Contact</h2>
  <p><a href="mailto:{esc(cfg['contactEmail'])}">{esc(cfg['contactEmail'])}</a></p>
</div>"""
        self.write("/about/", "About", f"About {cfg['name']}, how we confirm finds, and how to reach us.", body)

    def build_404(self):
        self.write("/404.html", "Page not found", "Page not found.",
                   article_head("Error 404", "Off the map", "That page doesn't exist, or it moved.")
                   + '<div class="cta"><a class="btn btn-primary" href="/map/">Open the map</a>'
                     '<a class="btn" href="/guides/">Browse guides</a></div>',
                   index=False)

    def build_meta_files(self):
        base = self.cfg["url"].rstrip("/")
        urls = "".join(f"<url><loc>{esc(base + u)}</loc><lastmod>{esc(d)}</lastmod></url>" for u, d in self.pages)
        (DIST / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
            encoding="utf-8")
        (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
        (DIST / "search-index.json").write_text(json.dumps(self.search), encoding="utf-8")
        self.build_feed()

    def build_feed(self):
        """RSS 2.0 feed of the live log, so readers and aggregators pick up new finds."""
        from email.utils import format_datetime
        cfg = self.cfg
        items = []
        for u in self.updates[:40]:
            when = dt.datetime.fromisoformat(u["time"])
            text = html.unescape(strip_tags(inline(u["text"])))
            link = re.search(r"\]\((/[^)\s]*)\)", u["text"])
            href = self.abs_url(link.group(1) if link else "/updates/")
            title = text if len(text) <= 100 else text[:97].rsplit(" ", 1)[0] + "…"
            items.append(
                f"<item><title>{esc(title)}</title><link>{esc(href)}</link>"
                f"<guid isPermaLink=\"false\">{esc(u['time'])}</guid>"
                f"<pubDate>{format_datetime(when)}</pubDate>"
                f"<description>{esc(text)}</description></item>")
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f"<title>{esc(cfg['name'])}: GTA 6 live log</title>"
            f"<link>{esc(self.abs_url('/updates/'))}</link>"
            f'<atom:link href="{esc(self.abs_url("/updates/feed.xml"))}" rel="self" type="application/rss+xml"/>'
            f"<description>New confirmed GTA 6 finds, newest first.</description>"
            f"<language>en-us</language>{''.join(items)}</channel></rss>")
        (DIST / "updates" / "feed.xml").write_text(feed, encoding="utf-8")

    def build(self):
        if DIST.exists():
            shutil.rmtree(DIST)
        shutil.copytree(ROOT / "static", DIST)
        shutil.copytree(ROOT / "src/assets", DIST / "assets")
        (DIST / "data").mkdir()
        shutil.copy(ROOT / "data/markers.json", DIST / "data/markers.json")
        self.build_home()
        self.build_map()
        self.build_checklist()
        self.build_guides()
        self.build_updates()
        self.build_submit()
        self.build_tip()
        self.build_about()
        self.build_404()
        self.build_meta_files()
        return len(self.pages)


def build(drafts=False):
    count = Site(drafts=drafts).build()
    print(f"Built {count} pages into {DIST}")


if __name__ == "__main__":
    build(drafts="--drafts" in sys.argv)
