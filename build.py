#!/usr/bin/env python3
"""Rachel's List Guides: build the static site from content/*.json.

    python3 build.py            write docs/ (pages, sitemap, robots, llms.txt, IndexNow key file)
    python3 build.py --check    build, then run every check that blocks a deploy
    python3 build.py --check --no-links   same, without the (slow) outside-link sweep
    python3 build.py --ping     tell Bing/IndexNow which pages changed (run ONLY once the domain is live)

Standard library only. Content lives in content/<name>.json (one per page) and content/_site.json.
Files starting with "_" are data, not pages (_site.json, _finds.json).
"""
import datetime
import html
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
AI_BOTS = ["Googlebot", "Bingbot", "OAI-SearchBot", "GPTBot", "ChatGPT-User", "ClaudeBot",
           "PerplexityBot", "Google-Extended"]
SAVE_HEADING = "Make it feel like a wedding, for less"


# ----------------------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def money(n):
    n = float(n)
    return "${:,.0f}".format(n) if n == int(n) else "${:,.2f}".format(n)


def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "{} {}, {}".format(d.strftime("%b"), d.day, d.year)


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def fill(tpl, **kw):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(kw[m.group(1)]) if m.group(1) in kw else m.group(0), tpl)


def template(name):
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_site():
    return load_json(ROOT / "content" / "_site.json")


def load_pages():
    pages = {}
    for f in sorted((ROOT / "content").glob("*.json")):
        if f.name.startswith("_"):
            continue
        p = load_json(f)
        p["_file"] = f.name
        pages[p["path"]] = p
    return pages


def load_finds():
    f = ROOT / "content" / "_finds.json"
    return load_json(f) if f.exists() else {}


def page_url(site, path):
    return site["base_url"] + ("/" if path in ("", "/") else "/" + path.strip("/") + "/")


def root_of(path):
    return "./" if path in ("", "/") else "../"


def internal(htm, root):
    """href="@x/" in content means a page of this site; make it relative to the page."""
    return htm.replace('href="@', 'href="' + root)


def app_link(site, page):
    slug = page["path"].strip("/") or "home"
    return "{}?utm_source=guides&utm_medium={}&utm_campaign={}".format(
        site["app_url"], page["medium"], slug)


# ----------------------------------------------------------------------------- finds ("ideas")
def src_line(name, date_iso):
    return "{} &middot; read {}".format(esc(name), fmt_date(date_iso))


def resolve_idea(spec, pages, finds):
    """Turn {"ref": "..."} into a displayable find (None if its source is missing)."""
    kind, _, rest = spec["ref"].partition(":")
    out = None
    if kind == "gown":
        pg, idx = rest.rsplit(":", 1)
        gl = pages[pg]["gowns"]
        if idx.startswith("brand="):  # follow the weekly refresh: first gown of that brand, else the biggest gap
            g = next((x for x in gl if x["brand"] == idx[6:]), gl[0])
        else:
            g = gl[int(idx)]
        out = dict(label="The dress", name="{}: {}".format(g["brand"], g["title"]), url=g["url"],
                   amount=g["price"], source_url=g["url"], date_read=g["date_read"],
                   meta="Seller's original {} &middot; size {} &middot; {}".format(
                       money(g["old_price"]), esc(g["size"]), src_line("Poshmark listing", g["date_read"])))
    elif kind == "find":
        city, _, what = rest.partition(".")
        f = (finds.get(city) or {}).get(what)
        if not f:
            return None
        if what == "photographer":
            out = dict(label="The photos", name="{}: {}".format(f["name"], f["package"]), url=f["url"],
                       amount=f["amount"], source_url=f["url"], date_read=f["date_read"],
                       meta="{}{}".format(esc(f.get("includes", "")) + " &middot; " if f.get("includes") else "",
                                          src_line("their own site", f["date_read"])))
        else:
            out = dict(label="The flowers", name="{}: {}".format(f["name"], f["item"]), url=f["url"],
                       amount=f["amount"], source_url=f["url"], date_read=f["date_read"],
                       meta=src_line("their own site", f["date_read"]))
    elif kind == "venue":
        pg, _, rule = rest.partition(":")
        vs = [v for v in pages[pg].get("venues", []) if v.get("max_guests", 0) >= 10]
        if not vs:
            return None
        v = min(vs, key=lambda x: x["amount"])
        out = dict(label="A room for dinner for 10", name=v["name"], url=v["url"], amount=v["amount"],
                   source_url=v["url"], date_read=v["date_read"],
                   meta="{} &middot; {} &middot; {}".format(esc(v["guests"]), esc(v["price_for"]),
                                                            src_line("their own page", v["date_read"])))
    elif kind == "fact":
        pg, key = rest.split(":")
        f = next((x for x in pages[pg]["facts"] if x["key"] == key), None)
        if not f:
            return None
        out = dict(label="Make it legal", name=f["label"] + " (" + pages[pg]["office"] + ")", url=f["source_url"],
                   amount=f.get("amount"), source_url=f["source_url"], date_read=f["date_read"],
                   meta=src_line(f["source_name"], f["date_read"]))
    if out is None:
        return None
    if spec.get("label"):
        out["label"] = spec["label"]
    out["price_display"] = money(out["amount"]) if out.get("amount") is not None else ""
    out["kind"] = kind
    return out


def render_ideas(page, pages, finds):
    ideas = []
    for s in page.get("ideas", []):
        try:
            i = resolve_idea(s, pages, finds)
        except (KeyError, IndexError, ValueError):  # its source page is not built yet
            i = None
        if i:
            ideas.append(i)
    page["_resolved_ideas"] = ideas
    if not ideas:
        return ""
    cards = "\n".join(fill(template("idea.html"), label=esc(i["label"]), url=esc(i["url"]), name=esc(i["name"]),
                           price_display=esc(i["price_display"]), meta=i["meta"]) for i in ideas)
    lead = page.get("ideas_lead") or "One real find in each category, each from its own page and dated. Prices change; check the page before you buy."
    return ('<section><h2>{}</h2><p class="lead">{}</p><div class="ideas">\n{}\n</div>{}</section>'
            .format(SAVE_HEADING.replace("less", "<em>less</em>"), lead, cards, render_allin(page, ideas)))


def render_allin(page, ideas):
    if page["type"] != "courthouse":
        return ""
    fees = [f for f in page.get("facts", []) if f.get("allin") and f.get("amount") is not None]
    priced = [i for i in ideas if i.get("amount") is not None]
    if not fees and not priced:
        return ""
    rows, total = [], 0.0
    for f in fees:
        rows.append('<tr><th scope="row">{}</th><td><span class="price">{}</span></td></tr>'.format(
            esc(f["label"]), money(f["amount"])))
        total += f["amount"]
    for i in priced:
        rows.append('<tr><th scope="row">{}</th><td><span class="price">{}</span><span class="was">{}</span></td></tr>'.format(
            esc(i["label"]), money(i["amount"]), esc(strip_tags(i["name"]))))
        total += i["amount"]
    rows.append('<tr class="total"><th scope="row">All in</th><td><span class="price">{}</span></td></tr>'.format(money(total)))
    page["_allin_total"] = total
    return ('<h3 style="margin-top:28px">Your courthouse wedding, all in</h3>'
            '<table class="tbl allin"><tbody>{}</tbody></table>'
            '<p class="note">Official fees plus one real find per category from the cards above. It is a sum of dated listings, not a quote: '
            'prices change.</p>').format("".join(rows))


# ----------------------------------------------------------------------------- tables
def table(headers, rows):
    head = "".join("<th scope=\"col\">{}</th>".format(esc(h)) for h in headers)
    return '<table class="tbl"><thead><tr>{}</tr></thead><tbody>\n{}\n</tbody></table>'.format(head, "\n".join(rows))


def facts_table(page):
    rows = []
    for f in page["facts"]:
        if f.get("amount") is not None:
            detail = '<span class="price">{}</span>'.format(esc(f["display"]))
        else:
            detail = "<strong>{}</strong>".format(esc(f["display"]))
        rows.append(
            '<tr><th scope="row">{}</th><td>{}<q class="quote">{}</q></td><td class="src"><a href="{}" rel="noopener">{}</a><br>Read {}</td></tr>'
            .format(esc(f["label"]), detail, esc(f["quote"]), esc(f["source_url"]), esc(f["source_name"]), fmt_date(f["date_read"])))
    return table(["What", "The official page says", "Source"], rows)


def venues_table(page):
    rows = []
    for v in page["venues"]:
        inc = '<span class="was">Includes: {}</span>'.format(esc(v["includes"])) if v.get("includes") else ""
        rows.append(
            '<tr><th scope="row"><a href="{}" rel="noopener">{}</a><small>{}</small></th>'
            '<td><span class="price">{}</span><span class="was">{} &middot; {}</span>{}<q class="quote">{}</q></td>'
            '<td class="src">Venue\'s own page<br>Read {}</td></tr>'.format(
                esc(v["url"]), esc(v["name"]), esc(v.get("area", "")), esc(v["price_display"]), esc(v["guests"]),
                esc(v["price_for"]), inc, esc(v["quote"]), fmt_date(v["date_read"])))
    return table(["Venue", "Price on its own page", "Source"], rows)


def gowns_rows(page, start=0, stop=None):
    rows = []
    for g in page["gowns"][start:stop]:
        rows.append(
            '<tr><th scope="row"><a href="{}" rel="noopener">{}</a><small>{} &middot; {}</small></th>'
            '<td><span class="price">{}</span><span class="was">Seller\'s original {}</span></td>'
            '<td class="src">Poshmark listing<br>Read {}</td></tr>'.format(
                esc(g["url"]), esc(g["title"]), esc(g["brand"]), esc(g["size"]), money(g["price"]),
                money(g["old_price"]), fmt_date(g["date_read"])))
    return rows


def generic_table(page):
    t = page["table"]
    rows = []
    for r in t["rows"]:
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td class="src">{}</td></tr>'.format(r["th"], r["td"], r["src"]))
    return table(t["headers"], rows)


def render_facts(page, site, pages):
    t = page["type"]
    root = root_of(page["path"])
    head = "<h2>{}</h2>".format(page["facts_heading"]) if page.get("facts_heading") else ""
    intro = '<p class="lead">{}</p>'.format(page["facts_intro"]) if page.get("facts_intro") else ""
    note = '<p class="note">{}</p>'.format(page["facts_note"]) if page.get("facts_note") else ""
    if t == "courthouse":
        steps = ""
        if page.get("steps"):
            steps = "<h3>The steps</h3><ol>{}</ol>".format("".join("<li>{}</li>".format(esc(s)) for s in page["steps"]))
        return "<section>{}{}{}{}{}</section>".format(head, intro, facts_table(page), note, steps)
    if t == "venues":
        return "<section>{}{}{}{}</section>".format(head, intro, venues_table(page), note)
    if t == "dresses":
        rows = gowns_rows(page)
        first, rest = rows[:5], rows[5:]
        mid = fill(template("cta.html"), promise=page.get("cta_mid", "Not your size or style? Tap the dresses you love; Rachel watches Poshmark and Etsy for your size every week."),
                   app_url=esc(app_link(site, page)), position="after-5")
        body = table(["Gown", "Price now", "Source"], first)
        if rest:
            body += mid + table(["Gown", "Price now", "Source"], rest)
        else:
            body += mid
        return "<section>{}{}{}{}</section>".format(head, intro, body, note)
    if t in ("hub", "packages", "home", "trust"):
        tbl = generic_table(page) if page.get("table") else ""
        return "<section>{}{}{}{}</section>".format(head, intro, tbl, note)
    return ""


def render_dress_bridge(page, site, pages, finds):
    """Venue pages, the hub and packages: 'Venue sorted? The dress is next', 3 real gowns, then the button."""
    if page["type"] not in ("venues", "hub", "packages") or not page.get("show_dress_bridge", True):
        return ""
    d = pages.get("wedding-dresses-under-500")
    if not d or not d.get("gowns"):
        return ""
    rows = gowns_rows(d, 0, 3)
    return ('<section><h2>Venue sorted? The <em>dress</em> is next</h2>'
            '<p class="lead">Three secondhand designer gowns at $500 or less, each re-opened on {} before it went on this page. '
            '<a href="@wedding-dresses-under-500/">See all of them</a>.</p>{}{}</section>').format(
        fmt_date(d["last_checked"]), table(["Gown", "Price now", "Source"], rows),
        fill(template("cta.html"), promise="Venue sorted? Rachel finds the rest for less, every week.",
             app_url=esc(app_link(site, page)), position="dress-bridge"))


def render_faq(page):
    items = "".join(fill(template("faq_item.html"), q=esc(f["q"]), a=f["a"]) for f in page["faq"])
    return '<section class="faq"><h2>Questions people <em>ask</em></h2>{}</section>'.format(items)


def render_related(page, pages):
    links = page.get("related") or []
    items = []
    for r in links:
        tgt = pages.get(r["path"])
        if not tgt:
            continue
        items.append('<li><a href="@{}">{}<span>{}</span></a></li>'.format(
            r["path"] + "/" if r["path"] else "", esc(r["label"]), esc(r.get("note", tgt.get("oneliner", "")))))
    if not items:
        return ""
    return '<section class="related"><h2>More <em>guides</em></h2><ul>{}</ul></section>'.format("".join(items))


def render_home_index(page, pages):
    groups = [("courthouse", "Courthouse weddings"), ("venues", "Small and micro wedding venues"),
              ("hub", "Compare cities"), ("packages", "Elopement packages"), ("dresses", "Wedding dresses"), ("trust", "Trust")]
    out = []
    for t, label in groups:
        ps = [p for p in pages.values() if p["type"] == t and p["path"] not in ("", "/")]
        if not ps:
            continue
        lis = "".join('<li><a href="@{}/">{}<span>{}</span></a></li>'.format(
            p["path"], esc(p["h1"]), esc(p.get("oneliner", ""))) for p in sorted(ps, key=lambda x: x.get("order", 0)))
        out.append('<section class="related"><h2>{}</h2><ul>{}</ul></section>'.format(label, lis))
    return "".join(out)


# ----------------------------------------------------------------------------- structured data
def jsonld_blocks(page, site, pages):
    url = page_url(site, page["path"])
    h1 = page["h1"]
    blocks = [{
        "@context": "https://schema.org", "@type": "Article", "headline": h1[:110],
        "description": page["description"], "dateModified": page["last_checked"],
        "datePublished": page.get("first_published", page["last_checked"]),
        "author": {"@type": "Organization", "name": "Rachel's List", "url": "https://rachelslist.co/"},
        "publisher": {"@type": "Organization", "name": "Rachel's List", "url": "https://rachelslist.co/",
                      "logo": {"@type": "ImageObject", "url": site["base_url"] + "/rachel-avatar-400.jpg"}},
        "mainEntityOfPage": url, "image": site["base_url"] + "/rachel-avatar-400.jpg", "inLanguage": "en-US"}]
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Rachel's List Guides", "item": site["base_url"] + "/"}]
    if page["path"] not in ("", "/"):
        crumbs.append({"@type": "ListItem", "position": 2, "name": h1, "item": url})
    blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs})
    blocks.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": strip_tags(f["a"])}}
        for f in page["faq"]]})
    items = []
    if page["type"] == "venues":
        items = [(v["name"], v["url"]) for v in page["venues"]]
    elif page["type"] == "dresses":
        items = [("{}: {}".format(g["brand"], g["title"]), g["url"]) for g in page["gowns"]]
    elif page["type"] in ("hub", "packages") and page.get("items"):
        items = [(i["name"], i["url"]) for i in page["items"]]
    if items:
        blocks.append({"@context": "https://schema.org", "@type": "ItemList", "name": h1,
                       "numberOfItems": len(items),
                       "itemListElement": [{"@type": "ListItem", "position": n + 1, "name": nm, "url": u}
                                           for n, (nm, u) in enumerate(items)]})
    return blocks


# ----------------------------------------------------------------------------- page
def h1_html(page):
    h = esc(page["h1"])
    em = page.get("h1_em")
    if em and esc(em) in h:
        h = h.replace(esc(em), "<em>{}</em>".format(esc(em)), 1)
    return h


def render_page(page, site, pages, finds):
    root = root_of(page["path"])
    app = esc(app_link(site, page))
    crumbs = '<nav class="crumbs" aria-label="Breadcrumb"><a href="@">Guides</a>{}</nav>'.format(
        "" if page["path"] in ("", "/") else " &rsaquo; " + esc(page["h1"]))
    checked = '<p class="checked">Last checked: <time datetime="{}">{}</time>. {}</p>'.format(
        page["last_checked"], fmt_date(page["last_checked"]), esc(page.get("refresh_note", "")))
    answer = '<div class="answer" id="answer">{}</div>'.format(page["answer_html"])
    facts = render_facts(page, site, pages)
    ideas = render_ideas(page, pages, finds)
    bridge = render_dress_bridge(page, site, pages, finds)
    card = fill(template("rachel_card.html"), root=root, app_url=app)
    body = "\n".join([
        crumbs,
        '<p class="rl-eyebrow">{}</p>'.format(esc(page["eyebrow"])),
        "<h1>{}</h1>".format(h1_html(page)),
        checked, answer, facts, bridge, ideas, card, render_faq(page), render_related(page, pages),
        render_home_index(page, pages) if page["type"] == "home" else "",
        '<p class="trust">Every price on this page links to the page it came from and shows the day we read it. '
        'No affiliate links: we earn nothing from these sellers or venues. <a href="@how-we-check/">How we check</a>.</p>',
    ])
    body = internal(body, root)
    ld = "\n".join('<script type="application/ld+json">{}</script>'.format(
        json.dumps(b, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")) for b in jsonld_blocks(page, site, pages))
    return fill(template("base.html"),
                title=esc(page["title"]), description=esc(page["description"]),
                canonical=page_url(site, page["path"]), base_url=site["base_url"], root=root,
                last_checked=page["last_checked"], jsonld=ld, posthog_key=site["posthog_key"],
                posthog_host=site["posthog_host"], app_url=app, body=body,
                slug=page["path"].strip("/") or "home", medium=page["medium"])


# ----------------------------------------------------------------------------- site files
def write_site_files(site, pages):
    urls = []
    for p in sorted(pages.values(), key=lambda x: (x["path"] not in ("", "/"), x["path"])):
        urls.append("<url><loc>{}</loc><lastmod>{}</lastmod></url>".format(page_url(site, p["path"]), p["last_checked"]))
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{}\n</urlset>\n'.format("\n".join(urls)),
        encoding="utf-8")
    robots = ["User-agent: *", "Allow: /", ""]
    for b in AI_BOTS:
        robots += ["User-agent: " + b, "Allow: /", ""]
    robots.append("Sitemap: {}/sitemap.xml".format(site["base_url"]))
    (DOCS / "robots.txt").write_text("\n".join(robots) + "\n", encoding="utf-8")
    lines = ["# Rachel's List Guides", "",
             "> Real wedding prices, each one checked on the official or seller's own page and dated. "
             "Courthouse fees, small and micro wedding venues, elopement packages and secondhand designer wedding dresses in Houston, Chicago, New York, Dallas and Los Angeles. "
             "No affiliate links. Built by Rachel's List (https://rachelslist.co).", "", "## Pages", ""]
    for p in sorted(pages.values(), key=lambda x: (x["path"] not in ("", "/"), x.get("order", 0), x["path"])):
        lines.append("- [{}]({}): {} (checked {})".format(p["h1"], page_url(site, p["path"]), p["oneliner"], fmt_date(p["last_checked"])))
    (DOCS / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DOCS / "{}.txt".format(site["indexnow_key"])).write_text(site["indexnow_key"], encoding="utf-8")
    if not os.environ.get("NO_CNAME"):  # NO_CNAME=1 lets the github.io address serve the site before DNS is set
        (DOCS / "CNAME").write_text(site["domain"] + "\n", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copyfile(ROOT / "site.css", DOCS / "site.css")


def build():
    site, pages, finds = load_site(), load_pages(), load_finds()
    DOCS.mkdir(exist_ok=True)
    keep = {"rachel-avatar-400.jpg"}
    for child in DOCS.iterdir():  # clear stale pages, keep the brand image
        if child.name in keep:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for p in pages.values():
        out = DOCS / "index.html" if p["path"] in ("", "/") else DOCS / p["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(p, site, pages, finds), encoding="utf-8")
    write_site_files(site, pages)
    print("built {} pages into docs/".format(len(pages)))
    return site, pages, finds


# ----------------------------------------------------------------------------- checks
MONEY_KEYS = ("amount", "price_display", "price", "old_price")


def walk_prices(obj, where, problems):
    if isinstance(obj, dict):
        if any(k in obj and obj[k] not in (None, "") for k in MONEY_KEYS):
            src = obj.get("source_url") or obj.get("url")
            if not src or not obj.get("date_read"):
                problems.append("{}: a price without source and date: {}".format(where, json.dumps(obj, ensure_ascii=False)[:90]))
        for v in obj.values():
            walk_prices(v, where, problems)
    elif isinstance(obj, list):
        for v in obj:
            walk_prices(v, where, problems)


def check_link(url):
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status < 400:
                    return url, True, r.status
        except urllib.error.HTTPError as e:
            if method == "GET":
                return url, False, e.code
        except Exception as e:  # DNS, timeout, TLS
            if method == "GET":
                return url, False, str(e)[:60]
    return url, False, "?"


def check(do_links=True):
    site, pages, finds = build()
    problems = []
    outside = {}
    for p in pages.values():
        w = p["path"] or "home"
        walk_prices(p, w, problems)
        walk_prices(finds, "_finds", problems)
        if len(p["title"]) > 60:
            problems.append("{}: title is {} characters (max 60)".format(w, len(p["title"])))
        if len(p["description"]) > 155:
            problems.append("{}: description is {} characters (max 155)".format(w, len(p["description"])))
        if not re.search(r"\d", p["description"]):
            problems.append("{}: description has no number".format(w))
        if len(p["faq"]) != 5:
            problems.append("{}: FAQ has {} questions (need 5)".format(w, len(p["faq"])))
        words = strip_tags(p["answer_html"]).split()
        first50 = " ".join(words[:50])
        if not re.search(r"\d", first50) or str(datetime.date.fromisoformat(p["last_checked"]).year) not in first50:
            problems.append("{}: the first 50 words need a number and the year".format(w))
        if re.search(r"ultimate guide", json.dumps(p), re.I):
            problems.append("{}: 'ultimate guide' is banned".format(w))
        out = DOCS / "index.html" if p["path"] in ("", "/") else DOCS / p["path"].strip("/") / "index.html"
        h = out.read_text(encoding="utf-8")
        size = len(h.encode("utf-8"))
        if size > 80 * 1024:
            problems.append("{}: page is {:.1f} KB (max 80)".format(w, size / 1024))
        n_btn = len(re.findall(r'class="rl-btn"', h))
        if not 1 <= n_btn <= 3:
            problems.append("{}: {} buttons (need 1 to 3)".format(w, n_btn))
        if "utm_campaign=" + (p["path"].strip("/") or "home") not in h or "utm_medium=" + p["medium"] not in h:
            problems.append("{}: the button link lacks its utm tags".format(w))
        if "Last checked:" not in h:
            problems.append("{}: no visible 'Last checked'".format(w))
        if len(re.findall(r"<h1[ >]", h)) != 1:
            problems.append("{}: needs exactly one h1".format(w))
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            try:
                d = json.loads(blk)
                assert d.get("@type")
            except Exception as e:
                problems.append("{}: structured data does not parse ({})".format(w, e))
        kinds = set(re.findall(r'"@type":"(Article|BreadcrumbList|FAQPage|ItemList)"', h))
        need = {"Article", "BreadcrumbList", "FAQPage"} | ({"ItemList"} if p["type"] in ("venues", "dresses") else set())
        if not need <= kinds:
            problems.append("{}: structured data missing {}".format(w, sorted(need - kinds)))
        for href in re.findall(r'href="([^"]+)"', h):
            if "affiliate" in href.lower():
                problems.append("{}: the word affiliate in a link: {}".format(w, href))
            if href.startswith("http"):
                host = re.sub(r"^https?://([^/]+).*$", r"\1", href)
                if host not in ("guides.rachelslist.co", "fonts.googleapis.com", "fonts.gstatic.com"):
                    outside.setdefault(html.unescape(href), []).append(w)
            elif href.startswith(("../", "./")) and not href.startswith(("../site.css", "./site.css")):
                tgt = (out.parent / href).resolve()
                tgt = tgt / "index.html" if tgt.is_dir() or not tgt.suffix else tgt
                if not tgt.exists():
                    problems.append("{}: internal link goes nowhere: {}".format(w, href))
        for m in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>([^<]*)</a>', h):
            if "affiliate" in m[1].lower():
                problems.append("{}: the word affiliate in link text: {}".format(w, m[1]))
    sm = (DOCS / "sitemap.xml").read_text()
    for p in pages.values():
        if page_url(site, p["path"]) not in sm:
            problems.append("{}: missing from sitemap".format(p["path"]))
    if do_links:
        urls = sorted(outside)
        print("checking {} outside links ...".format(len(urls)), flush=True)
        with ThreadPoolExecutor(max_workers=12) as ex:
            for url, ok, status in ex.map(check_link, urls):
                if not ok:
                    problems.append("link does not answer ({}): {}  [on {}]".format(status, url, ", ".join(sorted(set(outside[url]))[:2])))
    print("pages: {}  outside links: {}".format(len(pages), len(outside)))
    if problems:
        print("CHECK FAILED: {} problem(s)".format(len(problems)))
        for pr in problems:
            print(" -", pr)
        return 1
    print("CHECK OK: prices have sources and dates, titles <= 60, descriptions <= 155, structured data parses, every page has its button, no affiliate links{}".format(
        ", all outside links answer" if do_links else " (outside links not swept)"))
    return 0


# ----------------------------------------------------------------------------- ping
def ping():
    """IndexNow: tell Bing (and the other IndexNow engines) which URLs changed. Run only when the domain is live."""
    site, pages = load_site(), load_pages()
    body = json.dumps({"host": site["domain"], "key": site["indexnow_key"],
                       "keyLocation": "{}/{}.txt".format(site["base_url"], site["indexnow_key"]),
                       "urlList": [page_url(site, p["path"]) for p in pages.values()]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("IndexNow answered", r.status)
    except urllib.error.HTTPError as e:
        print("IndexNow answered", e.code, e.read()[:200])
        return 1
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--ping" in a:
        sys.exit(ping())
    if "--check" in a:
        sys.exit(check(do_links="--no-links" not in a))
    build()
