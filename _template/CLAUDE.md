# CLAUDE.md — Micro-Tool Hub build standard

This file is the throughput engine. It tells Claude Code exactly how to clone
`reference-tool-template.html` into a new, ranking-ready tool so every tool
meets the same bar without re-deciding anything. Read it before creating any
tool. The reference file is the source of truth for structure and house style;
this file is the rules.

---

## 0. The one-line strategy

Build many small, genuinely useful, **zero-support-surface** web tools on **one
hub domain**, rank them on Google, monetize with display ads + affiliate.
Winners are unpredictable, so the game is **throughput + a ruthless kill-gate**,
not picking one hit. Low revenue per tool is the moat: it is too thin to attract
focused competitors, so it does not get taken.

Honest expectation: organic traffic ramps over 6–12 months; first months are
near-zero; ~1,000,000 KRW/month needs **8–15 ranking tools** and is a 12–18
month cumulative game. This path optimizes *minimal ongoing intervention*, not
speed or ceiling.

---

## 1. Architecture (do not re-litigate per tool)

- **One hub domain**, many tool pages at `/{tool-slug}/`. Cumulative topical
  authority; internal links pass value between tools; one deploy.
- **Dependency-free static HTML/CSS/vanilla-JS per tool.** No framework. Reason:
  frameworks rot (breaking upgrades = maintenance = violates the whole point).
  Static files run untouched for years and score top Core Web Vitals.
- **Host:** any static host with a free tier (Cloudflare Pages / Netlify /
  Vercel). Deploy = push to git. (Deploy from your own machine; this sandbox
  cannot reach those hosts.)
- **Tight topical theme.** All tools should share a vertical (e.g. personal
  finance, or health metrics, or a trade niche). A themed hub outranks a random
  grab-bag because Google rewards topical depth. Pick the theme ONCE (see §6).

---

## 2. Tool-selection filter — a candidate must pass ALL four

1. **Zero support surface.** No login, no accounts, no payments, no writing to
   anyone's data, no storing user input server-side. Anonymous visitor → uses
   tool → leaves. If it could generate a support email, reject it.
2. **Real search demand.** People actively google this calculation/conversion/
   lookup. Prefer phrases with steady volume and clear intent ("X calculator",
   "convert X to Y", "how much X"). If nobody searches it, it cannot rank into
   traffic.
3. **Monetizable intent.** The topic must be one where ads/affiliate actually
   pay: finance, loans, tax, insurance, real estate, health, B2B/SaaS-adjacent.
   Trivial converters (cm↔inch) get traffic but ~zero RPM. Money follows the
   topic, not the pageview.
4. **Buildable in days as pure client-side logic.** If the math needs a backend,
   a paid API, or live data feeds, reject (that adds cost + maintenance).

If a candidate fails any one, drop it. Do not "make it work" by adding accounts
or a backend — that re-introduces exactly the support/maintenance surface this
whole path exists to avoid.

---

## 3. Per-tool build checklist (clone the reference, then verify every line)

Structure / SEO
- [ ] `<title>` ≤60 chars, leads with the exact search phrase.
- [ ] `<meta description>` ≤155 chars, promises the answer.
- [ ] `<link canonical>` = this tool's final URL.
- [ ] OG + Twitter tags updated.
- [ ] JSON-LD updated: `WebApplication` name/url; `BreadcrumbList`; `FAQPage`
      Q&A. **The visible FAQ text must match the FAQPage JSON-LD word-for-word**
      or you lose the rich result.
- [ ] One `<h1>` containing the primary phrase; `<h2>`s for sections.

Content (a bare tool ranks poorly — it needs real words)
- [ ] "How it works" section, plain-language, ~80–150 words.
- [ ] A concrete worked example.
- [ ] 2–4 FAQ items answering real "people also ask" questions.
- [ ] Copy is genuinely helpful and original (not filler). Thin/auto-spun text
      risks AdSense rejection and Google suppression — this is why the tool
      must be *useful*, not a keyword shell.

Tool UX
- [ ] Recalculates live on input (no submit button).
- [ ] Sensible default values pre-filled so the readout is populated on load.
- [ ] Mobile layout verified (single column ≤560px), keyboard focus visible.

Monetization slots (leave as placeholders until §5 conditions are met)
- [ ] Ad slot present but empty until AdSense approved.
- [ ] Affiliate block present but empty until a relevant, **disclosed** partner
      exists.

Instrumentation
- [ ] Analytics snippet present (shared across site).
- [ ] Page will appear in Google Search Console (domain verified once).
- [ ] Added to `sitemap.xml` and linked from the hub index + 2–3 related tools.

House style
- [ ] Shared CSS untouched (consistency = throughput). Only the tool's inputs,
      math, copy, and schema change between tools.

---

## 4. The kill-gate (this is what keeps the portfolio hands-off)

For every tool, **6–8 weeks after Google has indexed it**, check Search Console:

- **Kill** if it has effectively no impressions (search isn't showing it → no
  demand or hopeless competition). Remove it or leave it dormant; do not invest
  more. No emotion.
- **Keep & lightly reinforce** if it's getting impressions but few clicks
  (improve title/description/content once).
- **Double down** if it's getting clicks: add 2–3 closely related tools to
  compound the topical cluster.

Rule: a tool earns further attention only by showing traffic signal. This
prevents a graveyard of half-maintained pages and keeps per-tool maintenance
near zero. Track one row per tool: slug, publish date, week-6 impressions,
week-6 clicks, verdict.

---

## 5. Monetization sequencing (don't front-load)

1. **First**, publish 15–25 useful tools + core pages (About, Privacy, Contact).
   AdSense will not approve a thin, empty site.
2. **Then** apply for AdSense; once approved, drop the ad unit into the shared
   ad slot (one change propagates via the shared include).
3. **Affiliate usually out-earns display ads on tool pages** — a finance tool
   next to a relevant, disclosed account/offer link converts far better than a
   banner. Add affiliate blocks only where they're genuinely relevant, always
   with disclosure.
4. Never click your own ads, never buy traffic to ad pages — invalid-traffic =
   AdSense ban. Traffic must be organic.

---

## 6. Cadence & portfolio math

- **Pick the hub theme once** (one monetizable vertical). All early tools live
  inside it for topical authority.
- **Ship 1 tool every ~1–2 weeks.** Claude Code clones the reference; your time
  goes to the selection filter, the original copy, and QA — not boilerplate.
- **Portfolio to ~1,000,000 KRW/month (rough):** if a ranking finance-ish tool
  averages on the order of tens of thousands of KRW/month, you need ~8–15
  *ranking* tools; since most won't rank, plan to publish ~25–40 to get there.
  This is the honest shape: wide funnel, kill-gate, compound the winners.

---

## 7. Claude Code workflow (how to actually mass-produce)

For each new tool, instruct Claude Code roughly:

> "Clone `reference-tool-template.html` to `/{slug}/index.html` for a
> **{tool name}**. Replace: title, meta description, canonical, OG/Twitter,
> all three JSON-LD blocks, breadcrumb, h1, lede, the input fields, the `calc()`
> function with {the math}, the how-it-works + worked-example + FAQ copy (FAQ
> must match the FAQPage JSON-LD), and the related-tools links. Keep the shared
> CSS and house style byte-for-byte identical. Then run the §3 checklist and
> report any item you couldn't satisfy."

Then: add the page to `sitemap.xml`, link it from the index and 2–3 siblings,
commit, deploy. Log it in the kill-gate tracker with today's date.

---

## 8. What NOT to do (guardrails)

- No accounts, payments, backends, paid APIs, or live-data dependencies.
- No thin auto-generated keyword pages — tools must be genuinely useful.
- No unique per-tool visual identity — reuse the house style (consistency is
  throughput; bespoke design per tool kills the model).
- No skipping the kill-gate — the discipline is the product.
- No self-clicks / bought traffic — that ends the AdSense account.
