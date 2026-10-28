#!/usr/bin/env python3
"""Write GUIDES-CONVERSION.md from research/conversion/*.json (every quote verified by tools/verify_quotes.py).
The 'what we do with it' column is our decision for each finding."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [("placement-shown", "PLACEMENT / SHOWN"), ("quiz-wording", "QUIZ / WORDING"), ("friction-intent-motive", "FRICTION / INTENT / MOTIVE")]

DO = {
 "placement-shown": {
  0: "The answer and the first button share the first screen; the header button is always visible.",
  1: "Answer, hero and first button all sit in the top 40% of the page.",
  2: "On a phone the first button's bottom edge is measured at 844 px or less on every content page (checked in the screenshots).",
  3: "Contradicts the NN/g numbers (different pages, different measure), so the offer is repeated lower down (mid-page and end), not only above the fold.",
  4: "The answer is short and comes first; nothing sits before it except one hero photo.",
  5: "Answer in about 50 words; the offer is a short block, not a long text.",
  6: "A slim bottom button on phones only: appears after a short scroll, hides while an inline button is on screen.",
  7: "The bottom bar is phones-only (720 px and below): none on tablet or desktop, where it lost 11% and 5%.",
  8: "No sidebar: the offer lives in the content flow.",
  9: "The offer is a content card with the real board, never styled as a banner or ad; no banners on the site.",
  10: "No slide-in and no pop-up (the spec forbids pop-ups). A possible later test; no change now.",
  11: "Video is not assumed to help: ours is small, below the first screen, lazy-loaded, with a still poster. We compare it with poster-only if the data allows.",
  12: "Supports showing the real product next to the button: the real board sits beside Rachel's card.",
  13: "Same direction (vendor case, 2011): an embedded explainer beside the offer.",
  14: "Caution kept: a still image beat a video once, so the poster is a full still of the board and the loop never blocks anything.",
  15: "Closest match: the real thing + three plain steps + a button named for the action. This is the new Dream Board block.",
  16: "Media stays small and lazy so it cannot slow the first screen (it is below it).",
  17: "WebM and MP4, never GIF: ours are 255 KB and 187 KB plus a 49 KB poster.",
  18: "Context only: people who reach a video CTA click it; we cannot measure this here.",
 },
 "quiz-wording": {
  0: "A quiz is engaged by about a quarter of visitors on a quiz page; ours is not a quiz on our page, it is one tap that opens the app's own quiz.",
  1: "A quiz embedded in an existing page did not beat a dedicated quiz page, so the on-page step is ONE tap (a style), not a mini-quiz.",
  2: "Starters mostly finish (65%), so the page's job is the first tap; the app's quiz is short.",
  3: "Weak vendor story: context only.",
  4: "Multi-step beats one long form: the app's quiz is already multi-step; the on-page tap passes the first answer in with &style=.",
  5: "Same: multi-step beat single-step in one test.",
  6: "Click-then-form equalled a plain form in 10 tests, so we expect no magic and we measure.",
  7: "The strongest match for the style strip: a first small preference click before anything else (5.64% vs 3.07%, 1.8 million sessions; popups, vendor data).",
  8: "Image answers: the strip uses photos (the app's own AI-made style pictures, labelled Example styles). Weak evidence; measured.",
  9: "Context: a head start feels like progress; the strip is the head start.",
  10: "Foot-in-the-door: a small first yes can lead to a bigger one (secondhand). A hypothesis to measure, not a promise.",
  11: "Calibration: in the 1983 meta-analysis about half of the groups had no or a negative effect, so we log both clicks and compare.",
  12: "First person: the button says 'my'.",
  13: "Never 'your' on the button (it lost 24.95%).",
  14: "Name what you get: the button and the reason line name the outcome ('Dream Board', dress, flowers, dinner spot).",
  15: "Tie the offer to the visitor's situation: each page's reason line names what she just read.",
  16: "Page-matched offer text: courthouse pages talk about the courthouse day, dress pages about her size.",
  17: "No default 'Submit' wording anywhere.",
  18: "'Free' is in the button and under it: Free · 90 seconds · no card (academic evidence on prices, not buttons).",
 },
 "friction-intent-motive": {
  0: "Trust cues matter most where money changes hands; our app is free, so the line stays short.",
  1: "A plain 'no account needed' next to the action helped a shop; ours: 'Free · 90 seconds · no card' under every button.",
  2: "Say the time: '90 seconds' sits under every button and in the bottom bar (a shorter stated length means more people start).",
  3: "Reassurance next to the action: kept; weak evidence; measured.",
  4: "Same: weak evidence, measured.",
  5: "Calibration: most UI tests do not win (169 of about 650), so we log events and compare instead of assuming.",
  6: "'Free' in the button and the line under it.",
  7: "In-text link: a link inside the answer box (and a text link after each facts table), not only buttons (HubSpot: in-text CTA produced up to 93% of a post's leads, end-of-post banners about 6%).",
  8: "Page-matched offer (the reason line names what she just read).",
  9: "A page-specific offer ('your board for a Chicago courthouse day') in place of a generic one.",
  10: "Same as placement: first screen.",
  11: "The Dream Board block cites it: 77% of couples use Pinterest for wedding inspiration (source linked).",
  12: "Context: 51% of Gen Z and 45% of Millennials point to their Pinterest board as the planning tool they find most essential.",
  13: "The reason to want a board, in one line with the source linked: 60% of couples say fitting the budget to online inspiration is their biggest planning stress.",
  14: "Context (48% raised or shifted their budget for something they saw online): not used in copy.",
  15: "Context: 32% of couples are searching resale platforms for wedding attire.",
  16: "Context: couples pick vintage because it feels unique (71%), cost 28%: copy talks about finds, not only discounts.",
  17: "Context for venue pages: 37% of couples contact more vendors than planned to find budget-fit options.",
  18: "Context: 13 vendors on average.",
  19: "Context: nearly 90% set the budget before researching costs: our pages show real costs early.",
  20: "Weak (self-selected poll, Australia): not used.",
  21: "Context: 7 billion wedding searches, 16.7 billion saves on Pinterest.",
 },
}

QUESTIONS = '''## The three questions, answered from the evidence

**1. Why would she want a board?** Couples plan from pictures (77% use Pinterest for wedding inspiration; Zola 2026) and the hard part is the budget (60% say matching their budget to online inspiration is their number-one planning stress; 48% raised or shifted their budget for something they saw online; Zola 2026). Resale is already on their mind (32% search resale platforms for attire, 71% consider thrifted or pre-owned; Zola x Poshmark 2026). So the reason line on every page is tied to what she just read and to the budget: "You just saw what the courthouse costs. Rachel finds your dress, flowers and dinner spot for less, every week." (HubSpot: CTAs matched to the visitor convert better, vendor figure +202%; Backlinko: a page-specific offer, +785% before/after.)

**2. Where does she click?** In the first screen, in the text and at the end: the answer and a button share the first screen (NN/g: 57% of viewing time above the fold, 74% in the first two screenfuls); an in-text link inside the answer (HubSpot: in-text CTA up to 93% of a post's leads vs about 6% for end-of-post banners; NextAfter: an inline offer 2.0% vs 0.10% for a banner, n=242,062); the offer repeated mid-page and at the end; a slim bottom bar on phones only (NextAfter: +13.1% mobile, -5% desktop, -11% tablet, n=143,839; Conversion Rate Experts: +8% to +25%).

**3. How do we present it?** Show the real thing: the actual Dream Board (looping, small, lazy) with three plain steps and a button named for the action (MarketingExperiments, Felix + Iris: +71.62% at 95% confidence when the hero showed the actual kit with three steps; bundled changes). One first tap on the page: six example styles, a micro-commitment that opens the app with the style chosen (Wisepops: first small preference click 5.64% vs 3.07%, 1.8 million sessions; caution: a quiz embedded in a page did not beat a dedicated quiz page, ConvertFlow 10.45% vs 11.28%). First-person, free, outcome-named wording (ContentVerve: "my" +90%, "your" -24.95%).
'''

def md(s):
    return str(s).replace("|", "\\|").replace("\n", " ")

def main():
    out = ["# GUIDES-CONVERSION.md: the evidence behind the step from a guide page into the app", "",
           "Researched 2026-10-28 by three Sonnet researchers; every quote below was re-fetched and found on its page by `tools/verify_quotes.py` (`research/conversion/*.json` holds the full quote, context and caveat of each entry). **A claim with no source is marked \"no evidence\".** Most conversion numbers come from the vendor's own write-up; the caveat column in the JSON says which. Only NN/g, Google web.dev, the Ariely paper and the Freedman and Fraser / Nunes and Dreze studies are independent, and the last two were read secondhand.",
           "", QUESTIONS, "## Findings", ""]
    no_ev = []
    for fn, title in FILES:
        d = json.loads((ROOT / "research" / "conversion" / (fn + ".json")).read_text())
        out += ["### " + title, "", "| Topic | Finding | Source | Number | What we do with it |", "|---|---|---|---|---|"]
        for i, f in enumerate(d["findings"]):
            do = DO[fn].get(i, "Context only.")
            out.append("| {} | {} | [{}]({}) | {} | {} |".format(f["topic"], md(f["finding"]), md(f["source_name"]), f["source_url"], md(f["number"]), md(do)))
        out.append("")
        no_ev += ["{}: {}".format(title, x) for x in d.get("no_evidence", [])]
    out += ["## No evidence found (so no number is claimed)", ""] + ["- " + md(x) for x in no_ev] + [""]
    out += ["## What we measure (PostHog, cookieless)", "",
            "- `$pageview` per guide; `guide_cta_click` with `position` = header, top, text, card, sticky, after-6, closing, or style; `guide_style_click` with `style`.",
            "- Compare click-through by position and by page type; compare the style strip's taps against button clicks; poster-only vs looping video can be compared by switching `data-autoplay` off.",
            "- Calibration: GoodUI counts only 169 significant winners in about 650 published UI tests, so none of the choices above is treated as proven for our pages until our own numbers say so.", ""]
    (ROOT / "GUIDES-CONVERSION.md").write_text("\n".join(out), encoding="utf-8")
    print("wrote GUIDES-CONVERSION.md", len("\n".join(out)), "chars")

if __name__ == "__main__":
    main()
