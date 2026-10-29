# Courthouse pages: frozen at round 1 (owner's decision, 2026-10-28)

Rule: keep the version with the best sum of the three reviewers x four measures over rounds 1-4.

| Round | (a) engaged bride | (b) skeptical bride | (c) CRO professional | Sum |
|---|---|---|---|---|
| 1 | 9+6+8+4 = 27 | 9+6+6+4 = 25 | 8+7+8+4 = 27 | **79** |
| 2 | 8+5+7+5 = 25 | 8+6+5+3 = 22 | 8+7+7+4 = 26 | 73 |
| 3 | 8+6+7+4 = 25 | 9+7+6+4 = 26 | 8+6+8+4 = 26 | 77 |
| 4 | 8+6+8+5 = 27 | 8+6+6+4 = 24 | 8+7+8+4 = 27 | 78 |

Round 1 wins by one point over round 4 (79 against 78). The five courthouse pages are rebuilt as the round-1 version and frozen: do not iterate on them.

What "round 1" is: the first build of FLOW-SPEC (answer box, 5 numbered steps with fees, one collapsed sources list, "Your look for less" with four size-chip dress cards and a bouquet, the button block with the price line above the button, generic tips, FAQ, more guides, end block). It was never committed on its own, so it was rebuilt from the round-1 screenshots and page text: the rebuilt Chicago page text is identical to `review/flow-r1/chicago-text.txt` and its phone screenshots are pixel-identical to `review/flow-r1/chicago-390-*.png` (one 1/255 shade band aside), page height 5,676 px in both.

Where it lives now (so nothing else bleeds into it):
- `build.py`: the section "courthouse blocks" (`render_steps`, `sources_details`, `courthouse_dress_cards`, `render_look`, `render_tips`), `answer_courthouse`, `PRICE_LINE_C`, and the courthouse branches of `board_block`, `end_block`, `cta_html`, `render_page`, `finish_page`.
- `templates/board-c.html`, `templates/endblock-c.html`; the CSS block "courthouse pages: frozen at round 1" in `site.css` (scoped to `.t-courthouse`).
- `content/courthouse-wedding-*.json` (steps, tips, where, fees: the round-1 content), `content/_finds.json` (the round-1 bouquets: Flowers for Dreams $200, KVITKAFA $180, NYC Flower Pop $150, RainFlorist from $125, Hanamate $98), `content/_courthouse_dresses.json`.

The round-4 version (tips first with the finds inside the first tip, official phone numbers, a price in the phone bar, cheaper bouquets) is kept in git at commit `e775c96`, and its research (bouquets at $35-$140, a free photo spot per city, a Dallas lunch at $39 a person) in `research/flow-finds.json`, in case the owner wants to switch.

Known weaknesses of the frozen version, as the reviewers saw them: the price line above the button reads like a bill; the $15 certified copy sits next to the $60 and $10 fees in step 5; the "not shown" list is hidden in the collapsed sources; the tips are generic; no phone numbers.
