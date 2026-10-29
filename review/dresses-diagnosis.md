# Diagnosis: the two dress pages (model: wedding-dresses-under-500)

Read on a phone as she who searched "wedding dresses under 500": a bride with a budget and a size, shopping. The page as it was live before the rebuild (git 4eb9dbf, 6,815 px tall); screenshots in `review/old/old-dresses-500-*.png`.

| # | Block, in page order | What she sees | What is wrong | The fix |
|---|---|---|---|---|
| 1 | Header | A black pill, "Find my gown for less" | Ask before help; the pill outweighs the wordmark | A small text link |
| 2 | Hero | A bride with a hanging gown, about 250 px | Fine (it fits the search), but it pushes the answer down | Keep it short |
| 3 | Answer box | "we found 20 secondhand designer wedding gowns listed at $500 or less on Poshmark, from $65 (David's Bridal, seller's original $600) to $500. The biggest gap: a Hayley Paige gown at $500, seller's original $2,400." | The count and the range are there. "The biggest gap" is a sales line (what she wants is her size) | Keep the count and the range; add "size 2 to 18" so she sees at once it may fit |
| 4 | In-text link | "Not your size or style? Find my gown for less" | First ask inside the answer, before one gown is shown | Remove; the first button follows the first six gowns |
| 5 | "Which gown shape do you love? Tap one" strip | Lace A-line, satin slip, off-shoulder ballgown, "EXAMPLE PICTURES, AI-MADE" | Distrust cue (AI-made); pictures of gowns that are not the ones listed; a second ask | Remove |
| 6 | "This week's gowns" heading + 4-line paragraph | "Source: Poshmark listings, each re-opened on ... Biggest gap between price now and seller's original first; shipping and tax are not included." | Inside baseball before the first gown | One short line; sorting is by price |
| 7 | 20 gown cards in 2 columns | Brand label, model, price, "seller's original", size, "See photos on Poshmark ->" (about 330 px each) | No way to find her size: sizes run 2 to 18 and the order is by "biggest gap". Each card has 5 lines. The first three cards are US 6, US 10, US 10 | Size chips (2-4, 6-8, 10-12, 14+) that filter the grid; cards of 3 lines: price and original, brand and model, size and link |
| 8 | Button after the 6th card | "Find my gown for less", "Free · 90 seconds · no card" | Right place, weak words: "for less" is not about her | "Not your size? Show me gowns in my size every week" with the price line |
| 9 | "Show the other 8 gowns" | A button | Fine | Keep |
| 10 | "Make it feel like a wedding, for less": flowers $180 (burgundy, Houston), photos $500 (New York), a venue $380, a license $81 (Harris County) | Four finds from four different cities | Intent mismatch: she is buying a dress, and these are Houston and New York items for people who are not her | Remove from the dress pages |
| 11 | Dream Board block | Heading, 3 steps, "What it takes", a statistic, a looping phone clip with a blurred collage and "$12,690 saved", "AI-made", "more finds unlock with a paid plan" | Jargon, a number that is not hers, distrust cues, vague price | One clean button block: image in a phone frame, 3 plain steps, the price line, one button |
| 12 | Rachel card + button | A third ask | Repetition | One end block |
| 13 | FAQ | 5 answers | Good (safety, fit, "seller's original") | Keep |
| 14 | Missing | Nothing on buying secondhand safely | Missing content she wants: measuring, the return rule, alterations | A short "Buying secondhand safely" block; the return rule is quoted from Poshmark's own Posh Protect page |
