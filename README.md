# Rachel's List Guides

Source of https://guides.rachelslist.co, published by GitHub Pages from `main /docs`.
The spec is `marketing/GUIDES-SPEC.md` in the Rachel's List engine repo.

- `content/<page>.json`: one file per page (facts with source URL and date read, FAQ, bridge finds). `content/_site.json` holds the domain, the app link and the IndexNow key.
- `templates/`, `site.css`, `build.py` (standard library only) write `docs/`.
- `python3 build.py` builds. `python3 build.py --check` builds and runs the checks that block a deploy (add `--no-links` to skip the outside-link sweep). `python3 build.py --ping` sends IndexNow once the domain is live.
- `tools/` holds the research helpers: `dresses.py` (weekly gowns, each listing re-opened), `verify_quotes.py` (every quote must appear on the page it cites), `make_content.py` (first draft of the content files from the research; after that the content files are edited directly), `shot.py` (phone screenshots).
- Refresh: dress pages every Tuesday; venue pages and the hub monthly; courthouse pages every 3 months.
- No affiliate links, no seller or venue photos.
