# Diagnosis: micro-wedding-venues (the hub across five cities)

Read on a phone as she who searched "micro wedding venues" (12,100 a month) or "small wedding venues" (9,900): early in planning, no city chosen, wants to know what a small wedding venue costs and where. The page as it was live before the rebuild (git 4eb9dbf, 10,096 px tall); screenshots in `review/old/old-hub-*.png`.

| # | Block, in page order | What she sees | What is wrong | The fix |
|---|---|---|---|---|
| 1 | Header | A black pill, "Find my dress & flowers" | Ask before help | A small text link |
| 2 | Hero | A couple kissing, about 250 px | Mood picture; costs a quarter of the first screen | A room photo, short |
| 3 | Eyebrow | "HOUSTON · CHICAGO · NEW YORK · DALLAS · LOS ANGELES" in capitals | It is a list of cities in a label, not a way to pick one | Turn it into the city chooser |
| 4 | Answer box | "the lowest micro or small wedding venue price we verified is $197 (The Courthouse Wedding Chapel, Houston). By city: Houston from $197, Chicago from $400, ..." | The best sentence on the page (the five city floors) is run into a paragraph; the lead number is a 2-person chapel | The five floors as five chips with the price on each; "tap your city" |
| 5 | In-text link, "Which look is yours?" strip, a gown | Asks, AI-made pictures, a size-10 gown | Three asks before one venue | Remove |
| 6 | "The three cheapest venues in each city" (15 rows) | A long single list: name, city link, price, guests, "+ Their exact words", link, date | She cannot find her city without scrolling past the others; the rows repeat the same boilerplate | City chooser filters the list; cards with price, guests and one link |
| 7 | "Venue sorted? The dress is next" and "Make it feel like a wedding" (four finds) | Ball gowns, a burgundy bouquet from Houston, a license fee | Finds that do not fit; she has no city | One button block after the fourth card |
| 8 | Dream Board block, Rachel card, third button | As on the other pages | Jargon, a statistic, "$12,690", AI-made, a third ask | One clean block; one end block |
| 9 | FAQ | 5 answers ("What would be considered a micro wedding?", "Is 100 guests a micro wedding?") | Good | Keep |
| 10 | More guides | Six cards | Good | Keep, with the numbers |
| 11 | Missing | A reason to pick a city page | The hub is a doorway: it should send her to her city page fast | Each city chip links to its city page ("all Houston venues") as well as filtering |
