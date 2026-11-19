# Day One Atlas

A fast, static GTA 6 fan guide: interactive map, first-48-hours checklist, guides, live log and a submission form. It needs nothing but Python 3.

The plan for launch week is in **[LAUNCH_PLAYBOOK.md](LAUNCH_PLAYBOOK.md)**.

## Run it locally

```
python serve.py
```

Then open http://localhost:8080. The site rebuilds whenever you save a file in `content/`, `data/`, `src/` or `static/`. Just refresh the browser.

To build the deployable site once: `python build.py` (output goes in `dist/`).

## Where things live

| What | File |
|---|---|
| Site name, domain, launch date, ad/analytics code, tip jar handles | `data/site.json` |
| Guides (one Markdown file each) | `content/guides/*.md` |
| Map markers | `data/markers.json` |
| Map image and categories | `data/map.json`, `static/images/` |
| Checklist | `data/checklist.json` |
| Live log entries | `data/updates.json` |
| Page layout (header, footer, meta tags) | `src/templates/layout.html` |
| Styles and scripts | `src/assets/` |

## Writing guides

Each guide starts with front matter:

```
---
title: Full SEO title shown in Google
short: Short name for cards
description: One sentence, shown in search results
order: 3
status: live          # live, prelaunch (shows a "Pre-launch draft" badge) or draft (not published)
updated: 2026-11-19
---
```

Supported Markdown: `#` headings (each `#` section goes in the table of contents), paragraphs, lists, `**bold**`, `*italic*`, `` `code` ``, links, images, pipe tables, and:

- `- [ ] Something to do` → a checkbox saved in the reader's browser, with a progress bar
- `> [!TBD] What goes here` → yellow "Fill in at launch" box. Search for `[!TBD]` to find gaps.
- `> [!TIP] ...` and `> [!WARN] ...` → callouts

## The map

`/map/` is a schematic map of Leonida (`static/images/leonida-schematic.svg`, drawn for this site and not traced from Rockstar's map).

- **Zoomed out:** each region shows its name and a count of places. Click a region, or zoom in, to see the pins.
- **Places panel (left):** search (press `/`), category chips (shift-click to show only one category), "Hide found", a progress bar, and a list grouped by region that stays in sync with the map.
- **Detail card (right):** opens when you pick a place or region. It has "Mark found", "Copy link" and a link to the matching guide.
- **Links:** `/map/#m=<place-id>` opens a place and `/map/#r=<region-id>` opens a region.
- **Phones:** the panel and the detail card become bottom sheets.

### Adding a place

1. Open http://localhost:8080/map/?edit=1 and click the spot. The JSON for a new place is copied to your clipboard.
2. Paste it into `data/markers.json` and fill it in:

| Field | What it is |
|---|---|
| `id` | Unique, lowercase-with-dashes (used in share links) |
| `category` | One of the category ids in `data/map.json` |
| `title`, `desc` | Name and one or two sentences of verified info |
| `region` | One of the region ids in `data/map.json` |
| `place` | Town or district, e.g. "Key Lento" |
| `pos` | [x, y] in map-image pixels (edit mode fills this in) |
| `chapter` | When it unlocks, e.g. "Chapter 2", or `null` |
| `area` | Optional radius. Draws a dashed circle for "somewhere around here" |
| `link`, `linkText` | The guide section with the details |

Regions (outline, label position, colour, description, facts) live in `data/map.json`.

### Zoom levels

- **Zoomed out:** region names with place counts.
- **Middle:** pins, town names and roads.
- **Zoomed in:** a building square for every place, its name, and district names. Overlapping names hide automatically; the selected place always shows.

Every place also gets an **atlas grid reference** (A–P across, 1–16 down, matching the frame printed on the map), shown in the list and the detail card.

### Roads: making them accurate

Roads live in the `roads` list in `data/map.json`, not in the image. The starter roads are `"status": "illustrative"`: rough placeholders, drawn slightly faded. To make them accurate, trace them from your own play. Rockstar's map and fan maps built from it are copyrighted, so don't trace those.

1. Open `/map/?edit=1`, choose **Trace a road**, and pick its type (highway, road, railway or tunnel).
2. Zoom in and click along the road. Backspace undoes a point; Enter or **Finish road** copies it.
3. Paste it into `roads`. It's saved as `"status": "traced"` and draws solid and slightly bolder. Delete the illustrative road it replaces.

Town, district and feature names are in the `labels` list (`kind`: town, district or feature; add `"water": true` for names that sit on the sea).

### Swapping in a real map

If you get a map image you're allowed to use, put it in `static/images/` and update `image`, `width` and `height` in `data/map.json`. Then re-place region outlines and pins with edit mode, since positions are in image pixels.

## Deploying

**Netlify (recommended, free):** push this folder to a GitHub repo and import it in Netlify. `netlify.toml` sets the build command and output folder. The submit form works through Netlify Forms automatically.

**Without git:** run `python build.py` and drag `dist/` onto https://app.netlify.com/drop.

The site uses root paths (`/assets/...`), so it needs to sit at the root of a domain, not in a subfolder.

## Tip jar

`/tip/` shows amount buttons ($3 / $5 / $10 / $25 / custom) and one payment button per handle you fill in under `tipJar` in `data/site.json`:

```
"kofi": "yourname",        -> ko-fi.com/yourname
"paypal": "yourname",      -> paypal.me/yourname/<amount>USD (amount pre-filled)
"cashapp": "yourname",     -> cash.app/$yourname/<amount>  (amount pre-filled)
"venmo": "yourname",       -> venmo.com/u/yourname
"buymeacoffee": "yourname" -> buymeacoffee.com/yourname
```

Leave a handle empty to hide that button. Payments go straight to the provider; the site never handles money. Every guide also shows a small "Tip jar" card.

## SEO: what's built in

- **Titles:** each guide has a `seo_title` for the `<title>` tag, kept short with the keyword first. The longer `title` is the on-page H1. Titles were picked from real Google autocomplete phrases (e.g. "gta 6 cheats", "how to fix railing", "best settings").
- **Descriptions:** keep them under 155 characters so they aren't cut off in results.
- **Structured data:** WebSite and Organization on the home page; Article and BreadcrumbList on every guide, with publish and update dates.
- **Social cards:** 1200x630 share images in `static/og/`. Re-run `python tools/og_images.py` after adding a guide (needs `pip install pillow`).
- **Feeds and sitemaps:** an RSS feed of the live log at `/updates/feed.xml`, plus `sitemap.xml` and `robots.txt`.
- **Internal links:** "Keep reading" rotates through the next three guides, and the footer links the top eight.

**Fastest ranking wins after launch:** answer specific questions people are stuck on (the railing page is the template). Check Google autocomplete for "gta 6 how to…" and "gta 6 where…" every day, and write a short page for any stuck-point you can verify.

## Keeping facts straight

Every guide ends with a **Sources** list. House rule: a claim goes in plainly only when two independent sources agree. A single-source claim names its source in the text ("PowerPyx reports…"), and conflicting claims are marked as disputed or left out.

## Ads

Ad slots are already placed on the home, map list, checklist, live log and mid-guide. While `showAdPlaceholders` is `true` they show as dashed boxes. Once your ad network is approved, paste its script into `headHtml`, set the flag to `false`, and either let auto-ads place ads or put ad unit code inside the `.ad-slot` divs in `build.py`.
