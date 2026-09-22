# JA Assure AI Marketing Agent — User Guide

This guide is for anyone **operating** the product day to day — a marketer,
compliance reviewer, or sales/outreach lead — not for developers setting it
up. For installation, see [RUNBOOK.md](RUNBOOK.md). For API-level testing,
see [TESTING_GUIDE.md](TESTING_GUIDE.md).

Open the app at the address your team gave you (locally, this is usually
`http://localhost:5173`). There's no login screen in this version — anyone
with the link can use it, so treat the URL like you would any internal tool.

---

## 1. The Sidebar — What Each Screen Is For

| Screen | What you do here |
|---|---|
| **Overview** | Your dashboard — counts, pipeline health, quick links |
| **Content Studio** | Generate new marketing content and videos |
| **Review Center** | Approve, reject, or edit anything AI drafted before it goes anywhere |
| **Competitor Intel** | See what competitors are doing and how JA Assure can counter-position |
| **Lead Intelligence** | Find prospects, see their fit score, and manage outreach to them |
| **Publishing** | Actually send approved content to LinkedIn |
| **Closed-Loop Memory** | See what the AI has learned from your past rejections/edits |
| **Governance Analytics** | Compliance and pipeline health metrics |

A number badge on **Review Center** in the sidebar tells you how many items
are waiting for your decision right now.

---

## 2. Generating Content (Content Studio)

1. Pick a **brand** — Jade, DoctorShield, or Jaguar Transit. Each has its own
   tone and risk focus, so pick the one the content is actually for.
2. Pick a **platform** — LinkedIn, Instagram, X, a blog post, or a video/reel.
3. Pick a **language** — English plus four Southeast Asian languages.
4. Type your **topic/brief** in plain language — e.g. *"Announce updated
   medical indemnity coverage for aesthetic clinic surgeons in Singapore."*
5. Click **Generate**. You'll get either:
   - A set of **A/B copy variations** for a text post, or
   - A **video storyboard** if you picked video/reel — scenes, voiceover
     script, on-screen text, and (if rendering completes) an actual playable
     video with real visuals, narration, and captions.
6. Video takes longer than text — the AI needs to generate an image per
   scene, record narration, and assemble the file. A few scenes can take
   1–3 minutes, mostly depending on which image source is actually available
   (see [§8, "Reading the Badges"](#8-reading-the-badges-what-they-actually-mean)).
7. Whatever you generate lands automatically in the **Review Center** — it is
   never published or sent anywhere on its own.

**Launch Full Suite** generates the same brief across multiple platforms and
languages in one click, useful for a campaign that needs several formats at
once.

---

## 3. Reviewing Content (Review Center)

Every draft shows:
- The **compliance score** (0–100) and a pass/warning/blocked badge.
- Any **flagged violations**, in plain language, with a suggested fix if one
  exists.
- The **full drafted text** (or video preview, for video content).

Your options, per item:
- **Approve** — only available once compliance has passed. This is the only
  action that makes content eligible for publishing.
- **Reject & Learn** — pick a reason and add a note. This isn't just a
  delete: your note gets turned into a permanent lesson the AI will apply to
  future drafts on the same brand/topic. Check **Closed-Loop Memory**
  afterward to see it appear.
- **Edit** — change the text directly. An edited draft always goes back
  through compliance and back to "awaiting review" — it can never skip
  straight to approved, even if you're the one who just edited it.
- **AI Rewrite Fix** — asks the AI to automatically clean up a flagged draft
  (removing prohibited claims, adding a missing disclaimer). Always re-checks
  compliance afterward rather than trusting the rewrite blindly.
- **Regenerate** — throws the draft away and starts over, applying any
  lessons learned so far.
- **Audit Trail** — the full history of every decision made on this item,
  who made it, and what changed. Nothing here is ever deleted or overwritten.

**Nothing reaches Publishing or gets emailed to anyone until you click
Approve here.**

---

## 4. Publishing to LinkedIn

The **Publishing** screen shows two things:

1. **Approved & Ready to Publish** — a list of content that's cleared review
   and compliance and is just waiting for a dispatch click.
2. **Dispatch Record History** — every publish attempt ever made, real or
   simulated, with its outcome.

### Connecting your LinkedIn account
If you see **Connect LinkedIn** at the top, click it — you'll be taken to
LinkedIn's own login/consent screen. Approve access, and you'll be redirected
back with a confirmation. This only ever requests permission to post on
*your own* profile — never a company page, and never anything beyond posting.

### Publishing an item
Click **Publish to LinkedIn** next to any ready item. This is a real,
immediate post to your connected account. There's no "undo" for a real
LinkedIn post, so make sure you actually want it live before clicking.

### Reading a dispatch record
Each row is tagged **Real LinkedIn** or **Simulated Preview** — the two look
similar but are not the same thing: a simulated preview never contacts
LinkedIn at all (useful for rehearsing the workflow), while a real dispatch
is an actual post. The record shows the LinkedIn post ID (for real posts),
status, and any error if something went wrong — publishing never claims
success when it didn't happen.

### The background worker
There's a manual **Trigger Worker Pass** button that publishes everything
currently approved-and-ready in one batch. A fully automatic version of this
(polling on a timer with no button click) exists but is off by default and
is a backend configuration choice, not something toggled from this screen —
ask whoever manages your deployment if you want it enabled.

---

## 5. Leads & Outreach

### Finding leads
On **Lead Intelligence**, set your filters (brand, country, industry) and
click **Discover & Score Leads**. Depending on how the system is configured,
you'll get either:
- **Real businesses** (tagged `VERIFIED SOURCE`) — genuine companies with real
  addresses and, sometimes, a real discovered contact email, or
- **AI-suggested profiles** (tagged `AI-GENERATED PROSPECT`) or demo data —
  realistic but not verified real businesses, used when real lead-sourcing
  isn't configured.

Either way, every lead gets the same transparent **5-factor fit score**
(Industry Fit, Company Profile, Geo Relevance, Product Fit, Insurance Need) —
click a lead to expand it and see the real breakdown and the reasoning behind
each factor, not just the total number.

### Enriching a lead
Click **Enrich** and optionally paste the company's website — this attempts
to pull a genuine, verified description and contact email from that real
page. It never invents a phone number or email that isn't actually found.

### Generating and sending outreach
1. Expand a lead and click **Generate New Draft** — this writes a
   personalized email referencing the lead's real industry/location/company
   size, and runs it through compliance automatically.
2. Review the draft. If it needs changes, click **Edit**, fix the wording,
   and save — it goes back to "awaiting review" for a fresh look.
3. Click **Approve**.
4. Click **Send Email** — only enabled once approved, and only if the lead
   has a real email on file. If there's no real email, there is nothing to
   send to, and the button won't let you fake it.
5. The draft's status updates to **Sent** (with a real delivery confirmation)
   or **Send Failed** (with the real reason) — never a status that doesn't
   match what actually happened.

---

## 6. Competitor Intelligence

1. Enter a competitor's real URL and pick which of your brands it's relevant
   to, then click **Scrape & Analyze**. This performs a real, safe fetch of
   that page and extracts what it can (title, description, headings).
2. The **Competitor Change Digest** compares a competitor's two most recent
   snapshots and tells you exactly what changed — this is a factual
   comparison, not a guess. Run research on the same competitor again later
   (e.g. next week) to see genuine, dated differences appear.
3. Click **Snapshot History** on any competitor card to see every past
   research pass on file for them.

---

## 7. Closed-Loop Memory & Analytics

- **Closed-Loop Memory** lists every lesson the system has learned from your
  rejections and edits, which brand/category it applies to, and how many
  times it's been reinforced. You can deactivate a lesson if it's no longer
  relevant.
- **Governance Analytics** shows real pipeline health: how much content is
  pending/approved/rejected, compliance score distribution, and rejection
  reasons — all computed from your actual usage, never sample/placeholder
  numbers.

---

## 8. Reading the Badges — What They Actually Mean

This product is built to never claim more than what actually happened. Learn
these labels once and you'll always know exactly what you're looking at:

| Badge / Label | Meaning |
|---|---|
| **Visual source: Gemini / Hugging Face / Stable Diffusion 1.5 — Local GPU** | A real AI model actually generated this image |
| **Visual source: Branded fallback — AI provider unavailable** | No AI provider was available for this scene; a clean placeholder card was used instead — never presented as AI-made |
| **VERIFIED SOURCE** | Real, independently-confirmed data (a real scraped page, a real Google-Places business) |
| **AI-GENERATED PROSPECT** | A plausible profile invented by the AI, not a confirmed real business |
| **DEMO DATA** | Built-in sample data, shown when no real or AI source was available |
| **Real LinkedIn** vs **Simulated Preview** (Publishing screen) | Whether a dispatch record represents an actual post or a rehearsal that never contacted LinkedIn |
| **Sent** vs **Send Failed** vs **Draft** (Outreach) | Whether an email was actually delivered, actually failed (with a real reason), or hasn't been sent yet |
| **Compliance: Passed / Flagged / Failed** | The actual outcome of the 12-rule compliance check, never assumed |

If you ever see something that looks like it's overclaiming — e.g. a
"published" status for something you don't believe actually posted — treat
that as a bug and report it; it should never happen by design.

---

## 9. Common Questions

**Q: I clicked Generate and nothing compliance-flagged appeared. Is that a
bug?**
No — clean content simply shows a passing score and no violations. Not every
draft needs a fix.

**Q: Why does video generation sometimes take much longer than other times?**
It depends on which image provider is actually available at that moment. A
cloud provider (Gemini/Hugging Face) is fast when it has quota; if it's
unavailable, the system falls to a local GPU model, which is slower per
image, or a fallback card, which is instant. This is visible per scene once
generation finishes.

**Q: I approved something and it disappeared from Review Center — where did
it go?**
That's expected — approved items move to the **Publishing** screen (or, for
outreach, they're still visible on the **Leads** screen under that lead's
outreach history, now in "approved" status).

**Q: Can I un-send an email or un-publish a LinkedIn post?**
No — both are real, external actions once triggered. There's no undo inside
this product for either; you'd need to delete the post on LinkedIn directly
or follow up separately for an email.

**Q: A lead has no email — can I add one myself?**
Only through enrichment (pasting a real website to discover one) or having
an administrator add a verified one directly — the product deliberately
never lets you type in an unverified email and have it treated as confirmed
contact data.
