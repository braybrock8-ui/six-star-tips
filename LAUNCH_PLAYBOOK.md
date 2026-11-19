# Launch playbook

The site is the easy part. Winning comes down to being **fast, accurate and findable** in the first 72 hours, then still being useful in week two when the big outlets have caught up.

Target launch: **Nov 19, 2026**. Check that date is still current before you plan around it.

---

## The strategy in one paragraph

Don't try to be the wiki. The big wikis and IGN will own "GTA 6 walkthrough." Own the **narrow, urgent questions people ask in the first 48 hours**: where's X, what do I do first, fastest early money, which settings. Be the page that answers each one in 10 seconds, on a fast mobile page, with a shareable map link. Answers that are fast, specific and linkable get posted in Reddit and Discord threads, and that's your first traffic before Google ranks you.

---

## T-8 to T-1 days (now until launch)

**Day 1–2: get it online**
- [ ] Pick a name and domain. **Keep "GTA", "Rockstar" and "Grand Theft Auto" out of the domain.** Take-Two enforces trademarks hard. Using "GTA 6" in page titles to describe what the page is about is normal; using it in your brand isn't. `dayoneatlas.com`-style names are safer.
- [ ] Put the domain in `data/site.json` → `url`.
- [ ] Deploy to Netlify (free): connect the repo, and `netlify.toml` already sets the build. Or run `python build.py` and drag the `dist/` folder onto app.netlify.com/drop.
- [ ] Turn on Netlify Forms (Site → Forms) so `/submit/` works. Set up email notifications for new submissions.
- [ ] Add the site to **Google Search Console** and submit `/sitemap.xml`. Do this now: indexing takes days.
- [ ] Add the site to **Bing Webmaster Tools** too (it also feeds DuckDuckGo and some AI search).

**Day 2–4: money plumbing**
- [ ] **Apply to Google AdSense now.** Approval can take days to weeks, and a site with a few real pages has a better shot. Once approved, put the script in `site.json` → `headHtml` and set `showAdPlaceholders` to `false`.
- [ ] Set up the tip jar: create a Ko-fi, PayPal.me, Cash App, Venmo or Buy Me a Coffee account and put your handle (just the name, not the full link) under `tipJar` in `data/site.json`. The `/tip/` page shows a button for each handle you fill in.
- [ ] Join the Amazon Associates program for controller, headset and SSD affiliate links in the settings guide. Keep the affiliate note in the footer.
- [ ] Later: once you have sustained traffic, apply to higher-paying ad networks (Ezoic has low minimums; Raptive and Mediavine need much more traffic).
- [ ] Add privacy-friendly analytics (Plausible, Umami or Cloudflare Web Analytics) to `headHtml`. You need to see which pages are taking off.

**Day 4–7: prep**
- [ ] Write a "pre-launch" page people search for now. Examples: release time by region, preload size and time, editions compared. These can earn traffic *before* launch.
- [ ] Prepare the posts you'll share on launch day so you're not writing them while racing.
- [ ] Find the main communities: the big GTA subreddits, GTA Discord servers, and X accounts that post finds. **Read each one's self-promotion rules.** Most ban bare links but allow helpful answers that include one.
- [ ] Practise the launch-day loop: add a marker with `/map/?edit=1`, add an update, push, and confirm it's live in under 5 minutes.

---

## Launch day: the loop

You can't map everything, so pick **two pages to win** and update them all day. Best bets: the **interactive map** (collectibles + money spots) and **what to do first**.

**Every 1–2 hours:**
1. **Gather** finds from your own play, `/submit/` submissions, Reddit "new" sorted threads, and Discord.
2. **Verify** before publishing. Accuracy is your edge over spam sites. Mark anything you haven't seen yourself `verified: false`.
3. **Add** markers with `/map/?edit=1` (click the map → JSON is copied → paste into `data/markers.json`).
4. **Log** it in `data/updates.json`. The Live log shows people the site is current.
5. **Fill** the `> [!TBD]` blocks in guides as answers come in. Delete the callout once it's answered and change `status: prelaunch` to `status: live`.
6. **Push.** Netlify rebuilds in about 30 seconds.
7. **Share** one specific, useful link where people are asking: "Here's where the X is: [map link to that exact marker]". Every map marker has its own `#m=` link.

**Rules for sharing that don't get you banned:**
- Answer the question in the comment itself, then add the link. Never post just a link.
- Credit players who found things. People share pages that credit them.
- Never repost other sites' screenshots or text. Use your own captures or credited submissions.

---

## T+2 to T+7

- [ ] Check Search Console daily. When a query starts showing impressions, write or expand the page that answers it.
- [ ] Split big topics into their own pages once they get traffic, e.g. one page per collectible type. Each new page is another way to be found.
- [ ] Replace the placeholder map with a real map image you have rights to use (your own stitched screenshots, or a community map with permission). Update `width`/`height` in `data/map.json`, then re-place markers.
- [ ] Start short-form video: 20-second "where to find X" clips that point to the map. These carry well past launch week.

## T+7 to T+30

- [ ] Cover the slower-burn topics: 100% completion, trophies/achievements, best cars, hidden easter eggs.
- [ ] If there's an online mode, it's a whole second launch. Plan it like this one.
- [ ] Build an email list ("get notified when we map new X") so you own a channel that isn't Google or Reddit.

---

## Pages worth having by day 3

Ranked roughly by how many people will search them in launch week:

1. What to do first / beginner tips
2. How to make money fast
3. Interactive map (collectibles, secrets)
4. Best settings (performance vs quality)
5. How long to beat / number of missions
6. Best cars and where to find them
7. Cheats (if the game has them)
8. Each collectible type's full list
9. Easter eggs and secrets
10. Safehouses and properties

## What not to do

- Don't publish rumors as facts. One wrong "confirmed" item can wreck the trust your page needs to get shared.
- Don't use Rockstar's logo, key art or trailer frames as your branding.
- Don't sell or promote mods, money glitches that break the terms of service, or account services.
- Don't buy traffic or post-spam. Reddit bans spread fast and domains get blocklisted.
