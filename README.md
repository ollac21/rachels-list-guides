# Rachel's List Guides

Source of https://guides.rachelslist.co, published by GitHub Pages from `main /docs`.
The spec is `marketing/GUIDES-SPEC.md` in the Rachel's List engine repo.

- `content/<page>.json`: one file per page (facts with source URL and date read, FAQ, bridge finds). `content/_site.json` holds the domain, the app link, the hero-photo credits and the IndexNow key. `content/_finds.json` holds the photographer and florist finds. `content/_paa.json` records the People-also-ask questions the FAQs follow.
- `templates/`, `site.css`, `build.py` (standard library only) write `docs/` (and copy `img/`).
- `python3 build.py` builds. `python3 build.py --check` builds and runs the checks that block a deploy (add `--no-links` to skip the outside-link sweep; `NO_CNAME=1` skips writing `docs/CNAME`). `python3 build.py --ping` sends IndexNow once the domain is live.
- `research/*.json`: what was read by hand on each source page (the quote, the URL, the day read). `python3 -I tools/verify_quotes.py research/<file>.json` re-fetches every cited page and checks the quote is on it.
- `tools/`: `dresses.py` (weekly gowns from the app's finds file; every listing is re-opened and must still be available at the same price), `make_content.py` (first draft of the content files from the research; pages are stamped with the latest `date_read`; after that the content files may be edited directly), `faqs.py`, `display.py` and `research_io.py` (the editorial layer: short names, drops), `shot.py` (phone screenshots).
- Refresh: dress pages every Tuesday (`dresses.py`, then `make_content.py`); venue pages and the hub monthly; courthouse pages every 3 months.
- No affiliate links, no seller or venue photos. The one hero photo per page is licensed stock (Pexels License), credited in an HTML comment above it and in `content/_site.json`.
- `GUIDES-CONVERSION.md`: the evidence (finding, source link, number, what we do) behind the step from a guide page into the app; `research/conversion/*.json` holds each verified quote. `tools/make_conversion_doc.py` rebuilds it.
- `img/dream-board.mp4|webm|-poster.jpg`: the looping real Dream Board (cut from the app recording; sellers' photos blurred); `img/style-*.jpg`, `img/dress-*.jpg`: the app's own AI-made style and gown-shape pictures for the tap-a-look strip.
- `review/round-N/` and `review/final/` hold the phone (390 px) and desktop (1440 px) screenshots of the design rounds.
