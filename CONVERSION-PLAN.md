# What a page needs to convert: checklist, our pages against it, the target page (2026-10-28)

Evidence: `GUIDES-CONVERSION.md` (60 findings with sources), plus the patterns of pages that convert: deal and shopping pages (Wirecutter, NerdWallet, Slickdeals: a photo, a price and a button on every item) and quiz funnels.

## 1. The checklist
| # | A converting page has | Evidence |
|---|---|---|
| 1 | The answer AND the button on the first screen | 57 % of viewing time is above the fold, 74 % in the first two screens (NN/g). The 100 px just above the fold get 102 % more views. Users read about 20 % of a page (NN/g). |
| 2 | Real product photos, on every item | Baymard: shoppers judge products by their images first. A real product hero + 3 steps: +71.6 % (Felix + Iris). Forms with images complete 120 % more often (Typeform). |
| 3 | The button named after what she gets, in "my" | "Get my…" vs "Get your…": +90 % (Unbounce). "Find gym" vs "Get membership": +68 %. Personalized CTAs: +202 % (HubSpot). |
| 4 | A small first tap before the ask (her size, her style) | A micro-commitment before the ask: 5.64 % vs 3.07 % (Wisepops). Quiz funnels: 24 % engage (ConvertFlow). |
| 5 | The offer inside the content, not a banner | An inline offer 2.0 % vs a banner 0.10 % (NextAfter). In-text CTAs produced up to 93 % of leads vs 6 % for end banners (HubSpot). |
| 6 | A bar that stays at the bottom on phones | Sticky mobile CTA: +8 % to +25 % (Conversion Sciences); +13 % on mobile (NextAfter). |
| 7 | "Free", and no friction on the page | "Free" turns choices: 27 % → 69 % (Ariely). "No account needed": +45 % buyers (UIE). Reassurance: +17 % (GoodUI). |
| 8 | The click continues the same thing | A page-matched offer (content upgrade): 0.54 % → 4.82 % (Backlinko). |
| 9 | Fast | A 31 % faster first screen: +8 % sales (web.dev). |
| 10 | Real proof of the product | Showing the actual product, not an illustration (Felix + Iris). |

## 2. Our pages against it
| # | Today | Status |
|---|---|---|
| 1 | The first screen = a stock photo + the answer. The button comes after the steps or tips. | FAIL |
| 2 | Finds are text cards with no photo. | FAIL |
| 3 | The button is page-matched ("Show me courthouse dresses in my size"). | PASS |
| 4 | Size chips exist, but low on the page. | PARTIAL |
| 5 | One block after the content. | PARTIAL |
| 6 | A phone bar exists. | PASS |
| 7 | A subscription price line beside the button reads as a trap (all 3 reviewers). | FAIL |
| 8 | The app opens on a generic style quiz, not on what she chose. | FAIL (app side) |
| 9 | Fast static pages. | PASS |
| 10 | The board is blurred, with AI notes. | FAIL |

## 3. The target page (every type)
1. **First screen:**
   - H1 and a one-line answer ("Courthouse wedding in Chicago: $70, Tue–Fri, no appointment").
   - Right under it, a row of 4–6 REAL item photos with prices: the page's own items (dresses, venues, packages, bouquets). A tap on a photo opens the listing.
   - The size or style chips ("Your size: 2–4 · 6–8 · 10–12 · 14+").
   - The button "Show me dresses in my size" (it carries `&size=`), with "Free · 90 seconds · no card" under it.
2. **Then the full list:** a grid of real photos, price, the seller's original price, size. A button inside the list after 6 items.
3. **The app in action:** the real board with real finds, no blur, plus 3 steps. Then the button.
4. **Then the facts for Google and ChatGPT:** steps, fees, tips, FAQ, related guides.
5. **The phone bar** appears after the first screen.
6. **No price on the page,** only "Free to start". The app shows the price after her finds.

## 4. Rules for the iteration agent (the ONLY rules)
- **Honesty:**
  - real prices from real pages, re-checked; no invented numbers, reviews or customers;
  - facts carry a source link (a small link, not repeated on every row).
- **Photos:** use the listing's or venue's own image URL straight from their server (never re-hosted), linked to the listing. Footer: "Photos belong to their sellers; ask us to remove one."
- **Basics:** keep SEO basics (title, answer in the first lines, FAQ, structured data, sitemap) and the utm tags on every button.
- **Everything else is open:** the number of buttons, their position, the wording ("save", "%", "was $X"), the order of blocks, the photos.

### Rules REMOVED (they lowered conversion)
- "never a seller's or venue's photo"
- "the board blurred" and "AI-made notes in the body"
- "at most 3 buttons" and "the ask only after the help" (FLOW-SPEC principle 1)
- "the price line next to the button"
- "dress pages must not say save, %, retail, discount" (removed from `build.py --check`)
- "sources and 'read <date>' on every row"
- "80 KB page cap" (now 200 KB; photos load from the sellers)
