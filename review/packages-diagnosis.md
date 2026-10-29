# Diagnosis: elopement-packages

Read on a phone as she who searched "elopement packages" or "micro wedding packages": a couple who wants one price for the day (ceremony, maybe photos and flowers) and has not chosen a city. The page as it was live before the rebuild (git 4eb9dbf, 10,216 px tall); screenshots in `review/old/old-packages-*.png`.

| # | Block, in page order | What she sees | What is wrong | The fix |
|---|---|---|---|---|
| 1 | Header | A black pill, "Find the rest of my day" | Ask before help; vague words | A small text link |
| 2 | Hero | A couple in a forest, about 250 px | Fits the search; costs a quarter of the screen | Keep it short |
| 3 | Eyebrow | "ALL-IN PACKAGES · PRICES FROM THE PROVIDERS' OWN PAGES" in capitals, two lines | Noise | Short: "Packages · prices from the provider's page" |
| 4 | Answer box | "run from $350 (The Little Glass Chapel: Quick "I Do", Missouri City / Stafford (Houston area)) to $4,775 (Tiny Wedding Collective: all-inclusive micro wedding, Chicago). Two Las Vegas chapels start lower, from $159. We list 16..." | The longest first sentence on the site, with two venue names in parentheses; she cannot find "what do I get for $1,000" | Count and range first; the two Las Vegas chapels as a short second line |
| 5 | In-text link and "Which look is yours? Tap one" strip + a gown example | "Find the rest of my day", barn, beach, a Maggie Sottero gown | Two asks, an AI-made strip and a gown, before the first package | Remove |
| 6 | List heading and intro | "Packages with a printed price, cheapest first. Only packages whose provider prints the price... Read what each includes" | Good idea (read what each includes), buried in a paragraph | Show what is included on the card itself |
| 7 | 16 package rows | Name, provider and city, price, guest count, "Includes: ...", "+ Their exact words", link, "read Oct 28" | No way to pick her city; the list mixes Houston, Chicago, New York, Dallas, Los Angeles and Las Vegas in price order; "guest count not stated" on the cheapest | A city chooser (chips) on top; cards with price, guests, what is included, one link |
| 8 | "Venue sorted? The dress is next" with 3 gowns | Three ball gowns | Intent mismatch (a $4,775 package is not a ball-gown wedding), wrong sizes | One button block |
| 9 | "Make it feel like a wedding, for less" (four finds) | A dress, flowers, a venue, a license fee | Finds that do not fit: she has just chosen a package that includes some of these | Remove |
| 10 | Dream Board block, Rachel card, third button | Same as the other pages | Jargon, AI-made, a statistic, "$12,690" | Same fix as the other pages |
| 11 | FAQ | 5 answers ("Does eloping make you legally married?", "Is $5,000 enough for a wedding?") | The legal answer is the most useful thing on the page and it sits at the bottom | Keep the five; the legal one stays first |
| 12 | Missing | What to check before you book a package | Missing content she wants: what is NOT included (license, officiant, photos, flowers), travel fees | A "What a package usually leaves out" block, phrased as questions to ask |
