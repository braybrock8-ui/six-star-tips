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

## Adding map markers fast

1. Open http://localhost:8080/map/?edit=1
2. Click the spot. A ready-made marker is copied to your clipboard.
3. Paste it into `data/markers.json`, then fill in `id` (unique, lowercase-with-dashes), `category`, `title` and `desc`.

Marker fields: `id`, `category` (one of the ids in `data/map.json`), `title`, `pos` ([x, y] pixels on the map image), `region`, `desc`, `verified` (true once you've seen it in-game), `credit` (who found it).

Every marker gets a shareable link: `/map/#m=<id>`.

## Swapping in a real map

Put the image in `static/images/`, then update `image`, `width` and `height` in `data/map.json` to match its pixel size. Remove `placeholder`. Marker positions are in image pixels, so re-place them with edit mode.

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

## Keeping facts straight

Every guide ends with a **Sources** list. House rule: a claim goes in plainly only when two independent sources agree. A single-source claim names its source in the text ("PowerPyx reports…"), and conflicting claims are marked as disputed or left out.

## Ads

Ad slots are already placed on the home, map list, checklist, live log and mid-guide. While `showAdPlaceholders` is `true` they show as dashed boxes. Once your ad network is approved, paste its script into `headHtml`, set the flag to `false`, and either let auto-ads place ads or put ad unit code inside the `.ad-slot` divs in `build.py`.
