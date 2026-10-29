#!/usr/bin/env python3
"""Rachel's List Guides: build the static site from content/*.json.

    python3 build.py            write docs/ (pages, sitemap, robots, llms.txt, IndexNow key file)
    python3 build.py --check    build, then run every check that blocks a deploy
    python3 build.py --check --no-links   same, without the (slow) outside-link sweep
    python3 build.py --ping     tell Bing/IndexNow which pages changed (run ONLY once the domain is live)

Standard library only. Content lives in content/<name>.json (one per page) and content/_site.json.
Files starting with "_" are data, not pages (_site.json, _finds.json, _courthouse_dresses.json).
The page flow by page type is FLOW-SPEC.md.
"""
import datetime
import html
import json
import os
import re
import statistics
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
AI_BOTS = ["Googlebot", "Bingbot", "OAI-SearchBot", "GPTBot", "ChatGPT-User", "ClaudeBot",
           "PerplexityBot", "Google-Extended"]

# ----------------------------------------------------------------------------- the button (FLOW-SPEC: one first-person promise per page)
# page type -> (the button, the small header link, the phone bar)
LABELS = {
    "courthouse": ("Show me courthouse dresses in my size", "Find my dress", "Show me dresses in my size"),
    "dresses": ("Show me gowns in my size", "Gowns in my size", "Show me gowns in my size"),
}
DEFAULT_LABELS = ("Find my dress &amp; decor for less", "Find my dress &amp; decor", "Find my dress &amp; decor for less")
LABELS["home"] = ("Find cheaper dresses, flowers &amp; venues", "Try the free app", "Find cheaper dresses, flowers &amp; venues")
for _t in ("venues", "hub"):  # she is still choosing a place: the promise covers the venue too
    LABELS[_t] = ("Find my venue, dress &amp; decor for less", "Find my venue &amp; dress", "Find my venue, dress &amp; decor for less")
LABELS["packages"] = ("Find my dress &amp; flowers for less", "Find my dress &amp; flowers", "Find my dress &amp; flowers for less")
BOARD_HEAD = {
    "courthouse": "Want more like these, in <em>your</em> size?",
    "venues": "Still looking? Rachel finds your venue, dress &amp; decor <em>for less</em>",
    "hub": "Still looking? Rachel finds your venue, dress &amp; decor <em>for less</em>",
    "packages": "Still comparing? Rachel finds your venue, dress &amp; decor <em>for less</em>",
    "dresses": "Not your size? Rachel shows you <em>gowns in your size</em>, every week",
    "home": "Tell us your style. Rachel's List finds the dress, flowers and venue <em>for less</em>",
    "trust": "Tell Rachel your style. She finds the dress, flowers and venue <em>for less</em>",
}
END_LINE = {
    "courthouse": "I search Poshmark and Etsy every week for the looks you tap. Free to start.",
    "dresses": "Tell Rachel's List your size and the shapes you love. It checks Poshmark and Etsy every week.",
}
END_LINE_DEFAULT = "Rachel's List searches Poshmark, Etsy and venues every week for the looks you tap. Free to start."
PRICE_LINE = ('<p class="price-line"><b>Free: your board and your first finds. No card to start.</b>'
              '<span>After that, every new find each week: $9.92/month billed yearly ($119), or $24/month.</span></p>')
PRICE_LINE_CA = PRICE_LINE.replace("</p>", '<span>Canada: C$159/year or C$33/month.</span></p>')
PRICE_LINE_C = ('<p class="price-line"><b>Free:</b> your board and your first finds &middot; every new find each week: '
                '$9.92/month billed yearly ($119), or $24/month &middot; no card to start'
                '<span class="ca">Canada: C$159/year or C$33/month.</span></p>')
SAMPLE_CAP = "A sample board in the app."


# ----------------------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def money(n):
    n = float(n)
    return "${:,.0f}".format(n) if n == int(n) else "${:,.2f}".format(n)


def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "{} {}, {}".format(d.strftime("%b"), d.day, d.year)


def fmt_short(iso):
    d = datetime.date.fromisoformat(iso)
    return "{} {}".format(d.strftime("%b"), d.day)


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


def load_cdresses():
    f = ROOT / "content" / "_courthouse_dresses.json"
    return load_json(f) if f.exists() else {"dresses": []}


def page_url(site, path):
    return site["base_url"] + ("/" if path in ("", "/") else "/" + path.strip("/") + "/")


def root_of(path):
    return "./" if path in ("", "/") else "../"


def internal(htm, root):
    """href="@x/" in content means a page of this site; make it relative to the page."""
    return htm.replace('href="@', 'href="' + root)


def app_link(site, page):
    slug = page["path"].strip("/") or "home"
    return "{}?utm_source=guides&utm_medium={}&utm_campaign={}&from={}".format(
        site["app_url"], page["medium"], slug, page["type"])


CITY_NAMES = {"houston": "Houston", "chicago": "Chicago", "new-york": "New York", "dallas": "Dallas",
              "los-angeles": "Los Angeles", "las-vegas": "Las Vegas"}
CITY_ORDER = ["chicago", "new-york", "houston", "dallas", "los-angeles"]


def city_key(page):
    m = re.search(r"-(chicago|new-york|houston|dallas|los-angeles)$", page["path"])
    return m.group(1) if m else ""


def labels_for(page):
    return LABELS.get(page["type"], DEFAULT_LABELS)


def ico(name):
    return '<svg class="ico" aria-hidden="true"><use href="#{}"/></svg>'.format(name)


# ----------------------------------------------------------------------------- the button blocks
SIZED = {"dresses": "Show me gowns in size {s}"}


def cta_html(page, app, pos, fine=True):
    sized = ' data-base="{}" data-sized="{}"'.format(labels_for(page)[0], SIZED[page["type"]]) if page["type"] in SIZED else ""
    note = "About 90 seconds, in your browser. No download." if page["type"] == "courthouse" else "About 90 seconds, in your browser."
    return ('<div class="cta"><a class="rl-btn" href="{}" data-cta="{}"{}>{}</a>{}</div>'.format(
        app, pos, sized, labels_for(page)[0], '<p class="fine">{}</p>'.format(note) if fine else ""))


def mid_strip(page, app, pos):
    return ('<div class="mid-strip"><a class="rl-btn" href="{}" data-cta="{}">{}</a><p class="fine">Free to start, no card. After that, every new find each week: $9.92/month billed yearly ($119), or $24/month.</p></div>').format(
        app, pos, labels_for(page)[0])


def packages_head(page):
    """The bridge for the packages page, from what the providers' own lists say they include."""
    cards = [c for c in page.get("cards", []) if c["city"] != "las-vegas"]
    inc = [(c.get("includes") or "").lower() for c in cards]
    n = len(cards)
    dress = sum(1 for t in inc if "dress" in t or "gown" in t)
    flowers = sum(1 for t in inc if any(k in t for k in ("bouquet", "floral", "flower")))
    lead = "No package here lists a dress" if dress == 0 else "Only {} of {} packages list a dress".format(dress, n)
    return "{} and {} of {} leave flowers out. Rachel's List finds both <em>for less</em>".format(lead, n - flowers, n)


def board_block(page, app, root, pos):
    """The button block: the real board in a phone frame, 3 steps, the button, the price line, one fine-print line.
    The courthouse pages are frozen at round 1 (button block: price line above the button)."""
    if page["type"] == "courthouse":
        return fill(template("board-c.html"), heading=BOARD_HEAD["courthouse"], root=root, price=PRICE_LINE_C, cta=cta_html(page, app, pos), cap=SAMPLE_CAP)
    return fill(template("board.html"), heading=packages_head(page) if page["type"] == "packages" else BOARD_HEAD.get(page["type"], BOARD_HEAD["home"]), root=root, price=PRICE_LINE,
                cta=cta_html(page, app, pos, fine=False), cap=SAMPLE_CAP)


def end_block(page, app, root):
    if page["type"] == "courthouse":
        return fill(template("endblock-c.html"), root=root, line=END_LINE["courthouse"], price=PRICE_LINE_C, cta=cta_html(page, app, "end", fine=False))
    return fill(template("endblock.html"), root=root, line=END_LINE.get(page["type"], END_LINE_DEFAULT),
                price=PRICE_LINE_CA if page["type"] in ("home", "trust") else PRICE_LINE, cta=cta_html(page, app, "end", fine=False))


# ----------------------------------------------------------------------------- the answer (first screen)
def answer_wrap(inner):
    return '<div class="answer" id="answer"><!--answer-->{}<!--/answer--></div>'.format(inner)


def answer_courthouse(page):
    city = page["card_title"]
    year = page["last_checked"][:4]
    note = ' <i>({})</i>'.format(esc(page["where_note"])) if page.get("where_note") else ""
    return answer_wrap(
        '<p class="a-lead">A courthouse wedding in {city} costs <b class="a-big">${fee:,}</b> in {year}'
        '<span class="a-parts">{parts}</span></p>'
        '<ul class="a-rows"><li>{i1}<span><b>Where</b>{where}{note}</span></li><li>{i2}<span><b>When</b>{when}</span></li></ul>'.format(
            city=esc(city), fee=page["fee_total"], year=year, parts=esc(page["fee_parts"]), i1=ico("i-pin"), i2=ico("i-cal"),
            where=esc(page["where"]), note=note, when=esc(page["when"])))


def venue_stats(page):
    vs = page["venues"]
    flat = [v for v in vs if not v.get("per_person")]
    ten = [v for v in flat if (v.get("max_guests") or 0) >= 10]
    return vs, flat, ten


def answer_venues(page):
    vs, flat, ten = venue_stats(page)
    city = CITY_NAMES.get(city_key(page), "")
    lo, hi = min(v["amount"] for v in flat), max(v["amount"] for v in flat)
    year = page["last_checked"][:4]
    out = ('<p class="a-lead"><b class="a-big">{n}</b> small venues in {city} print their price in {year}: from <b>{lo}</b> to <b>{hi}</b></p>').format(
        n=len(vs), city=esc(city), year=year, lo=money(lo), hi=money(hi))
    rows, used = [], set()
    for t in (10, 20, 50):  # the cheapest room for 10, 20 and 50 guests; a venue is shown once
        fits = sorted((v for v in flat if (v.get("max_guests") or 0) >= t), key=lambda x: x["amount"])
        if fits and fits[0]["name"] not in used:  # the true cheapest for this size; a venue that is also the cheapest for a smaller size is shown once
            v = fits[0]
            used.add(v["name"])
            rows.append('<li><span class="as-p">{}</span><span class="as-t"><em>{}</em><b><a href="{}" rel="noopener" target="_blank">{}</a></b>'
                        '<span>{}</span></span></li>'.format(money(v["amount"]), ("Seats up to {}".format(v["max_guests"]) if v.get("max_guests") else "For {}+ guests".format(t)), esc(v["url"]), esc(v["name"]), esc(v["price_for"])))
    if rows:
        out += '<p class="a-sub">The cheapest room for each group size:</p><ul class="a-stats">{}</ul>'.format("".join(rows))
    return answer_wrap(out)


def micro_pick(venues):
    """The cheapest room for 10 or more guests, preferring a small room (at most 60 guests): the hub's 'micro' pick."""
    flat = [v for v in venues if not v.get("per_person") and (v.get("max_guests") or 0) >= 10]
    small = [v for v in flat if v["max_guests"] <= 60]
    pool = small or flat
    return min(pool, key=lambda v: v["amount"]) if pool else None


def answer_hub(page, pages):
    floors, best = [], None
    for c in CITY_ORDER:
        p = next((x for x in pages.values() if x["type"] == "venues" and city_key(x) == c), None)
        if not p:
            continue
        flat = [v for v in p["venues"] if not v.get("per_person")]
        pick = micro_pick(p["venues"])
        two = [v for v in flat if 0 < (v.get("max_guests") or 0) <= 2]
        if pick:
            best = pick["amount"] if best is None else min(best, pick["amount"])
        sub = "couple only from {}".format(money(min(v["amount"] for v in two))) if two else "{} venues listed".format(len(p["venues"]))
        floors.append('<li><a href="@{}/"><span>{}</span><b>{}</b><small>for 10+ guests</small><small>{}</small></a></li>'.format(
            p["path"], CITY_NAMES[c], "from " + money(pick["amount"]) if pick else "see the list", sub))
    year = page["last_checked"][:4]
    allp = sorted(v["amount"] for p in pages.values() if p["type"] == "venues" for v in p["venues"] if not v.get("per_person"))
    return answer_wrap('<p class="a-lead">A venue for 10 or more guests starts at <b class="a-big">{lo}</b> in {year}; the middle printed price in our five cities is <b>{mid}</b>. Tap your city:</p>'
                       '<ul class="a-floors">{f}</ul>'.format(lo=money(best), mid=money(statistics.median(allp)), year=year, f="".join(floors)))


def answer_packages(page, pages=None):
    cards = page["cards"]
    main = [c for c in cards if c["city"] != "las-vegas"]
    amts = sorted(c["amount"] for c in main)
    year = page["last_checked"][:4]
    out = ('<p class="a-lead"><b class="a-big">{n}</b> elopement and micro wedding packages in our five cities print their price in {year}: from <b>{lo}</b> to <b>{hi}</b>; {u} are under $1,000</p>').format(
        n=len(main), year=year, lo=money(amts[0]), hi=money(amts[-1]), u=sum(1 for a in amts if a < 1000))
    both = [c["amount"] for c in main if "photo" in (c.get("includes") or "").lower() and any(k in (c.get("includes") or "").lower() for k in ("officiant", "minister"))]
    if both:
        out += '<p class="a-sub">With an officiant and photos in the price: from {}.</p>'.format(money(min(both)))
    fees = [f["amount"] for p in (pages or {}).values() if p["type"] == "courthouse" for f in p["facts"] if f["key"] == "license_fee" and f.get("amount") is not None]
    if fees:
        out += '<p class="a-sub">The marriage license is extra unless a card says it is in the price: ${:,} to ${:,} by county (<a href="@courthouse-wedding-chicago/">courthouse guides</a>).</p>'.format(min(fees), max(fees))
    return answer_wrap(out)


def answer_dresses(page):
    g = page["gowns"]
    sizes = [int(re.search(r"\d+", str(x["size"])).group()) for x in g if re.search(r"\d+", str(x["size"]))]
    year = page["last_checked"][:4]
    return answer_wrap('<p class="a-lead"><b class="a-big">{n}</b> secondhand designer wedding gowns, {lo} to {hi}, on Poshmark in {year}: sizes {a} to {b}.</p>'
                       '<p class="a-sub">Each was re-opened on {d} and was still for sale at the price shown.</p>'.format(
        n=len(g), lo=money(min(x["price"] for x in g)), hi=money(max(x["price"] for x in g)), year=year, a=min(sizes), b=max(sizes), d=fmt_date(page["last_checked"])))


def answer_generic(page):
    ah = re.sub(r'<p class="sub">.*?</p>', "", page["answer_html"], flags=re.S)
    ah = re.sub(r'<p class="hook">.*?</p>', "", ah, flags=re.S)
    return answer_wrap(ah)


def render_answer(page, pages=None):
    t = page["type"]
    if t == "courthouse":
        return answer_courthouse(page)
    if t == "venues":
        return answer_venues(page)
    if t == "hub":
        return answer_hub(page, pages)
    if t == "packages":
        return answer_packages(page, pages)
    if t == "dresses":
        return answer_dresses(page)
    return answer_generic(page)


# ----------------------------------------------------------------------------- courthouse blocks
# FROZEN AT ROUND 1 (owner's decision: the best sum of the 3 reviewers x 4 measures over rounds 1-4: R1 79, R2 73, R3 77, R4 78).
# The round-4 version (tips first, finds inside the first tip, official phone numbers) is in git at e775c96.
def render_steps(page):
    items = []
    for i, s in enumerate(page["steps5"], 1):
        fee = '<span class="sfee">{}</span>'.format(esc(s["fee"])) if s.get("fee") else "<span></span>"
        items.append('<li><span class="sn">{}</span><div class="sb"><b>{}</b><span>{}</span></div>{}</li>'.format(i, esc(s["title"]), esc(s["text"]), fee))
    return '<section><h2>Do it in <em>{} steps</em></h2><ol class="steps5">{}</ol>{}</section>'.format(len(items), "".join(items), sources_details(page))


def sources_details(page):
    rows = []
    for f in page["facts"]:
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td class="src"><a href="{}" rel="noopener">{}</a><br>read {}</td></tr>'.format(
            esc(f["label"]), esc(f["display"]), esc(f["source_url"]), esc(f["source_name"]), fmt_short(f["date_read"])))
    t = '<table class="tbl"><thead><tr><th scope="col">What</th><th scope="col">The official page says</th><th scope="col">Source</th></tr></thead><tbody>{}</tbody></table>'.format("".join(rows))
    note = ""
    if page.get("facts_note_list"):
        note = '<p class="note">{}</p><ul class="note-list">{}</ul>'.format(
            esc(page.get("facts_note_head", "Not shown, because no official page states it:")), "".join("<li>{}</li>".format(esc(x)) for x in page["facts_note_list"]))
    return ('<details class="src" id="sources"><summary>Official sources: every fee and rule, each with its page and the day we read it</summary>{}{}</details>').format(t, note)


BANDS = [("2-4", "2&ndash;4"), ("6-8", "6&ndash;8"), ("10-12", "10&ndash;12"), ("14+", "14+")]


def band_of_size(size):
    m = re.search(r"\d+", str(size))
    if not m:
        return ""
    n = int(m.group())
    return "2-4" if n <= 5 else "6-8" if n <= 9 else "10-12" if n <= 13 else "14+"


def size_chips(label="Size"):
    chips = ['<button type="button" class="fc" data-v="all" aria-pressed="true">All</button>']
    chips += ['<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(k, v) for k, v in BANDS]
    return '<div class="fchips" data-group="band"><span class="lbl">{}</span>{}</div>'.format(label, "".join(chips))


def courthouse_dress_cards(page, cd):
    """One top pick per size band (the pick rotates by city, so the five pages differ); a size chip shows that band's finds."""
    dresses = cd.get("dresses", [])
    rot = CITY_ORDER.index(city_key(page)) if city_key(page) in CITY_ORDER else 0
    by_band = {}
    for d in dresses:
        by_band.setdefault(d["band"], []).append(d)
    top = {b: v[rot % len(v)]["id"] for b, v in by_band.items()}
    cards = []
    for d in dresses:
        was = '<s><span class="vh">seller\'s original </span>{}</s>'.format(money(d["old_price"])) if d.get("old_price") else ""
        cards.append(
            ('<a class="dcard" data-item data-band="{band}"{top} href="{url}" rel="noopener" data-cta="dress">'
             '<span class="d-price"><span class="price">{price}</span>{was}</span>'
             '<span class="d-name">{name}</span><span class="d-meta">Size {size} &middot; {style}</span></a>').format(
                band=esc(d["band"]), top=" data-top" if top.get(d["band"]) == d["id"] else "", url=esc(d["url"]),
                price=money(d["price"]), was=was, name=esc(d["name"]), size=esc(d["size"]), style=esc(d["style"])))
    return cards


def find_row(icon, title, sub, price, url, small=""):
    return ('<li><a class="frow" href="{}" rel="noopener" data-cta="find">{}<span><b>{}</b><span class="fm">{}</span></span>'
            '<span class="fp">{}{}</span></a></li>').format(esc(url), ico(icon), esc(title), esc(sub), small, esc(price))


def render_look(page, finds, cd):
    city = city_key(page)
    f = finds.get(city, {})
    rows = []
    fl = f.get("florist")
    if fl:
        rows.append(find_row("i-flowers", "A bridal bouquet", "{}: {}".format(fl["name"], fl["item"]), money(fl["amount"]), fl["url"],
                             '<small class="from">from </small>' if fl.get("from") else ""))
    ph = f.get("photographer")
    if ph and (ph.get("hours") or 9) <= 1 and ph["amount"] <= 500:  # FLOW-SPEC: a 1-hour courthouse session, or leave it out
        rows.append(find_row("i-photo", "Courthouse photos", "{}: {}".format(ph["name"], ph["package"]), money(ph["amount"]), ph["url"],
                             '<small class="from">from </small>' if ph.get("from") else ""))
    cards = courthouse_dress_cards(page, cd)
    dd = fmt_short(cd["date_read"]) if cd.get("date_read") else "Oct 28"
    lead = "Real finds, each re-opened on its own page on {} and still for sale. Tap your size.".format(dd)
    return ('<section><h2>{head}</h2><p class="sec-lead">{lead}</p>'
            '<div class="fwrap" data-topmode>{chips}<div class="dgrid">{cards}</div></div>'
            '<ul class="finds">{rows}</ul>'
            '<p class="srcnote">Dresses are Poshmark listings; every price links to the seller\'s own page. No affiliate links.</p></section>').format(
        head=page["look_heading"].replace("look,", "<em>look</em>,") if page.get("look_heading") else "Your courthouse look, for less",
        lead=lead, chips=size_chips(), cards="".join(cards), rows="".join(rows))


def render_tips(page):
    lis = "".join("<li><b>{}</b>{}</li>".format(esc(t["h"]), esc(t["t"])) for t in page.get("tips", []))
    return '<section><h2>Make the day feel like a <em>wedding</em></h2><ul class="tipl">{}</ul></section>'.format(lis) if lis else ""


# ----------------------------------------------------------------------------- venues, packages, hub
def venue_card(v):
    pp = v.get("per_person")
    unit = "per person" if pp else ""
    mx = int(v.get("max_guests") or 0)
    fits = '<span class="v-fits">{}</span>'.format("Couple only" if 0 < mx <= 2 else "Up to {} guests".format(mx)) if mx else ""
    inc = '<p class="v-inc">{}</p>'.format(esc(v["includes"])) if v.get("includes") else ""
    return ('<article class="vcard" data-item data-max="{mx}" data-amt="{amt}"><div class="v-top">'
            '<h3 class="v-name">{fits}<a href="{url}" rel="noopener" target="_blank">{name}</a><span class="v-area">{area}</span></h3>'
            '<div class="v-price">{price}<small>{unit}</small></div></div>'
            '<p class="v-for">{guests} &middot; {pf}</p>{inc}'
            '<p class="v-src"><a href="{url}" rel="noopener" target="_blank" data-cta="venue">Venue\'s own page</a> &middot; read {date}</p></article>').format(
        mx=mx, amt=999999 if pp else int(v["amount"]), url=esc(v["url"]), name=esc(v["name"]), area=esc(v.get("area", "")), fits=fits,
        price=money(v["amount"]), unit=esc(unit), guests=esc(v["guests"]), pf=esc(v["price_for"]), inc=inc, date=fmt_short(v["date_read"]))


def venue_chips():
    def grp(name, label, opts):
        b = ['<button type="button" class="fc" data-v="all" aria-pressed="true">Any</button>']
        b += ['<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(v, t) for v, t in opts]
        return '<div class="fchips" data-group="{}"><span class="lbl">{}</span>{}</div>'.format(name, label, "".join(b))
    return (grp("fits", "Guests", [("10", "10+"), ("20", "20+"), ("50", "50+")]) +
            grp("budget", "Budget", [("1000", "Under $1k"), ("3000", "Under $3k")]))


def interleave(cards, block, after):
    return "".join(cards[:after]) + block + "".join(cards[after:])


def render_venues_list(page, app, root, board=True):
    cards = [venue_card(v) for v in page["venues"]]
    return ('<section><h2>{head}</h2><p class="sec-lead">{intro}</p>'
            '<div class="fwrap">{chips}<div class="vlist">{body}</div><p class="fnone">No venue matches both filters. Choose &ldquo;Any&rdquo; on one of them.</p></div>'
            '{note}</section>').format(note=('<p class="srcnote">{}</p>'.format(esc(page["facts_note"])) if page.get("facts_note") else ""),
        head=page.get("facts_heading") or "Venues with a <em>printed price</em>, cheapest first", intro=page.get("facts_intro", ""),
        chips=venue_chips(), body="".join(cards)) + (board_block(page, app, root, "mid") if board else "")


def render_payless(page):
    if not page.get("pay_less"):
        return ""
    lis = "".join("<li><b>{}</b>{}</li>".format(esc(t["h"]), t["t"]) for t in page["pay_less"])
    return '<section><h2>{}</h2><ul class="tipl">{}</ul></section>'.format(page.get("pay_less_heading", "How to pay <em>less</em> for a small venue"), lis)


def render_cards_section(page, app, root, pages=None, board=True):
    """Hub and packages: a city chooser, then cards cheapest first, the button after the 4th."""
    cards = page.get("cards", [])
    if page["type"] == "hub" and pages:  # the room size, from the city pages (matched by the venue's own page address)
        fit = {v["name"]: v.get("max_guests") for p in pages.values() if p["type"] == "venues" for v in p["venues"]}
        top = set()
        for c in CITY_ORDER:
            vp = next((x for x in pages.values() if x["type"] == "venues" and city_key(x) == c), None)
            pick = micro_pick(vp["venues"]) if vp else None
            if pick:
                top.add(pick["name"])
    else:
        fit, top = {}, set()
    cities = [c for c in CITY_ORDER + ["las-vegas"] if any(x["city"] == c for x in cards)]
    chips = ['<button type="button" class="fc" data-v="all" aria-pressed="true">All cities</button>']
    chips += ['<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(c, CITY_NAMES[c]) for c in cities]
    out = []
    for c in cards:
        det = '<p class="v-for">{}</p>'.format(esc(c["detail"])) if c.get("detail") else ""
        flags = ""
        flags = ""
        if page["type"] == "packages":
            inc_l = (c.get("includes") or "").lower()
            fl = [("Officiant", ("officiant", "minister")), ("Photos", ("photo",)), ("License", ("license",)), ("Flowers", ("bouquet", "floral", "flower"))]
            flags = '<ul class="flags">{}</ul>'.format("".join('<li class="{}">{} {}</li>'.format("y" if any(k in inc_l for k in ks) else "n", "&#10003;" if any(k in inc_l for k in ks) else "&ndash;", n) for n, ks in fl))
        mx = fit.get(c["name"]) or 0
        tag = '<span class="v-fits">{}</span>'.format("Destination: Las Vegas") if c["city"] == "las-vegas" else (
            '<span class="v-fits">{}</span>'.format(esc(CITY_NAMES.get(c["city"], ""))) if page["type"] == "packages" and c["city"] else (
                '<span class="v-fits">{} &middot; {}</span>'.format(esc(CITY_NAMES.get(c["city"], "")), "couple only" if 0 < mx <= 2 else "up to {} guests".format(mx)) if mx else ""))
        more = "" if (page["type"] != "hub" or c["name"] in top) else " data-more"
        inc = '<p class="v-inc">Includes: {}</p>'.format(esc(c["includes"])) if c.get("includes") else ""
        out.append(('<article class="vcard" data-item data-city="{city}"{more}><div class="v-top"><h3 class="v-name">{tag}<a href="{url}" rel="noopener" target="_blank">{name}</a>'
                    '<span class="v-area">{sub}</span></h3><div class="v-price">{price}</div></div>{flags}{inc}{det}'
                    '<p class="v-src"><a href="{url}" rel="noopener" target="_blank" data-cta="venue">Their own page</a> &middot; read {date}</p></article>').format(
            city=esc(c["city"]), url=esc(c["url"]), name=esc(c["name"]), sub=esc(c.get("sub", "")), price=esc(c["price_display"]), det=det, inc=inc, tag=tag, more=more, flags=flags, date=fmt_short(c["date_read"])))
    links = ""
    if page["type"] == "hub":
        for c in CITY_ORDER:
            vp = next((x for x in (pages or {}).values() if x["type"] == "venues" and city_key(x) == c), None)
            if vp:
                links += '<a class="citylink" data-for="{c}" href="@{path}/" hidden>See all {n} {name} venues &rarr;</a>'.format(c=c, path=vp["path"], n=len(vp["venues"]), name=CITY_NAMES[c])
    btn = '<button type="button" class="fc showmore" data-more-btn>Show all {} (three per city)</button>'.format(len(cards)) if top else ""
    return ('<section><h2>{head}</h2><p class="sec-lead">{intro}</p><div class="fwrap" data-limit="{lim}"><div class="fchips" data-group="city"><span class="lbl">City</span>{chips}</div>{links}'
            '{legend}<div class="vlist">{body}</div>{btn}<p class="fnone">Nothing listed for this city yet.</p></div></section>').format(btn=btn, lim=1 if top else 0,
        legend='<p class="srcnote legend">&#10003; named on the provider\'s own page &middot; &ndash; not named there</p>' if page["type"] == "packages" else "",
        head=page.get("facts_heading", "Prices, cheapest first"), intro=page.get("facts_intro", ""), chips="".join(chips), links=links,
        body="".join(out)) + (board_block(page, app, root, "mid") if board else "")


# ----------------------------------------------------------------------------- dresses
def gown_name(g):
    if g.get("model"):
        return "{} · {}".format(g["brand"], g["model"])
    return g["title"] if g["title"].lower().startswith(g["brand"].lower()) else "{}: {}".format(g["brand"], g["title"])


def gown_card(g, more=False):
    size = str(g["size"]).replace("US ", "")
    return ('<a class="dcard" data-item data-band="{band}"{more} href="{url}" rel="noopener" target="_blank" data-cta="dress"><span class="d-price"><span class="price">{price}</span></span>'
            '<span class="d-orig">seller\'s original {old}</span><span class="d-name">{brand} &middot; {model}</span>'
            '<span class="d-meta">Size {size}</span><span class="d-go">View on Poshmark &nearr;</span></a>').format(
        band=band_of_size(size), more=" data-more" if more else "", url=esc(g["url"]), price=money(g["price"]), old=money(g["old_price"]),
        brand=esc(g["brand"]), model=esc(g.get("model") or g["title"]), size=esc(size))


def render_gowns(page, app, root):
    g = sorted(page["gowns"], key=lambda x: (x["price"], -x["old_price"]))
    cards = [gown_card(x) for x in g]
    body = "".join(cards)
    other = '<p class="srcnote">{} Other price band: <a href="@{}/">{}</a>.</p>'.format(esc(page.get("facts_intro", "")), *(("wedding-dresses-under-1000", "gowns from $501 to $1,000") if "500" in page["path"] else ("wedding-dresses-under-500", "gowns at $500 or less")))
    return ('<section class="gowns-sec"><div class="fwrap">{chips}<div class="dgrid big">{body}</div>'
            '<p class="fnone">No gown in that size this week. Rachel watches for yours every Tuesday: the button below sets your size.</p></div>{other}</section>').format(
        chips=size_chips("Size"), body=body, other=other) + board_block(page, app, root, "mid")


def render_safe(page):
    if page["type"] != "dresses":
        return ""
    return ('<section><h2>Buying secondhand <em>safely</em></h2><ul class="tipl">'
            '<li><b>Measure first</b>Take your bust, waist and hips, and compare them with the measurements in the listing photos. If a size tag has no measurements, ask the seller.</li>'
            '<li><b>Know the return rule</b>Poshmark says it gives a full refund if an item never ships or does not match the listing description; otherwise all sales are final. You have 72 hours after delivery to open a return case with photos, so inspect the dress before you accept the order '
            '(<a href="https://poshmark.com/posh_protect" rel="noopener">Posh Protect</a>, read Oct 28, 2026).</li>'
            '<li><b>Ask before you buy</b>Message the seller for more photos, the fabric, the brand label and tags, and any flaws. A clear answer is a good sign.</li>'
            '<li><b>Plan for a seamstress</b>Get a quote from a local seamstress before you buy: a hem or a bustle is often priced separately from the dress.</li></ul></section>')


# ----------------------------------------------------------------------------- faq, related, menu
def render_faq(page):
    items = "".join(fill(template("faq_item.html"), q=esc(f["q"]), a=f["a"]) for f in page["faq"])
    return '<section class="faq"><h2>Questions people <em>ask</em></h2>{}</section>'.format(items) if items else ""


def render_related(page, pages):
    links = page.get("related") or []
    items = []
    for r in links:
        tgt = pages.get(r["path"])
        if not tgt:
            continue
        note = r.get("note", tgt.get("oneliner", ""))
        if tgt["type"] == "courthouse" and page["type"] == "venues":
            note = "{} in fees. Steps and fees, from the official pages.".format("${:,}".format(tgt["fee_total"]))
        items.append('<li><a href="@{}">{}<span>{}</span></a></li>'.format(
            r["path"] + "/" if r["path"] else "", esc(r["label"]), esc(note)))
    if not items:
        return ""
    return '<section class="related"><h2>More <em>guides</em></h2><ul>{}</ul></section>'.format("".join(items))


def render_home_menu(page, pages):
    """Home: four cards, each with ONE answer line (numbers read from the pages) and the links into that part of the site, each link with its number."""
    by = lambda *t: sorted((p for p in pages.values() if p["type"] in t and p["path"] not in ("", "/")), key=lambda x: x.get("order", 0))
    court, venues, dress, pack = by("courthouse"), by("venues"), by("dresses"), by("packages")
    hub = by("hub")
    out = []

    def card(icon, title, href, line, links):
        lk = "".join('<a class="{}" href="@{}/">{}</a>'.format("hmore" if t == "Compare cities" else "", h, t) for h, t in links)
        return ('<article class="hcard"><h3>{}<a href="@{}/">{}</a></h3><p>{}</p><div class="hlinks">{}</div></article>').format(ico(icon), href, esc(title), esc(line), lk)

    if court:
        fees = [p["fee_total"] for p in court]
        out.append(card("i-courthouse", "Courthouse weddings", court[0]["path"], "${:,} to ${:,} in fees, license plus ceremony, from each clerk's own page.".format(min(fees), max(fees)),
                        [(p["path"], "{} <b>${:,}</b>".format(esc(p["card_title"]), p["fee_total"])) for p in court]))
    if venues:
        links = []
        for p in venues:
            flat = [v["amount"] for v in p["venues"] if not v.get("per_person")]
            links.append((p["path"], "{} <b>from {}</b>".format(esc(CITY_NAMES.get(city_key(p), p["card_title"])), money(min(flat)))))
        amts = [v["amount"] for p in venues for v in p["venues"] if not v.get("per_person")]
        micro = [micro_pick(p["venues"]) for p in venues]
        out.append(card("i-venue", "Small and micro venues", hub[0]["path"] if hub else venues[0]["path"],
                        "Only venues that print their own price: from ${:,} for a couple, ${:,} for 10 or more guests.".format(min(amts), min(m["amount"] for m in micro if m)),
                        links + ([(hub[0]["path"], "Compare cities")] if hub else [])))
    if dress:
        d5 = next((p for p in dress if "500" in p["path"]), dress[0])
        out.append(card("i-dress", "Wedding dresses", d5["path"], "{} secondhand designer gowns at $500 or less, from {}: resale listings, re-checked every week.".format(
            len(d5["gowns"]), money(min(g["price"] for g in d5["gowns"]))),
            [(p["path"], "{} <b>{} gowns</b>".format("Up to $500" if "500" in p["path"] else "$501 to $1,000", len(p["gowns"]))) for p in dress]))
    if pack:
        c = pack[0].get("cards", [])
        amt = [x["amount"] for x in c if x.get("city") != "las-vegas"]
        out.append(card("i-gift", "Elopement packages", pack[0]["path"], "{} packages from {} with the price on the provider's own page.".format(len(c), money(min(x["amount"] for x in c))) if amt else "Packages with the price on the provider's own page.",
                        [(pack[0]["path"], "All {} packages <b>from {}</b>".format(len(c), money(min(x["amount"] for x in c))))]))
    return '<section class="menu" id="menu"><div class="hgrid">{}</div></section>'.format("".join(out))


def render_chips(page):
    if not page.get("chips"):
        return ""
    return '<div class="chips">{}</div>'.format("".join(
        '<a class="chip" href="#{}">{}<b>{}</b></a>'.format(c["target"], esc(c["label"]), esc(c["value"])) for c in page["chips"]))


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


def render_trust_table(page):
    t = page.get("table")
    if not t:
        return ""
    head = "".join('<th scope="col">{}</th>'.format(esc(h)) for h in t["headers"])
    rows = "".join('<tr><th scope="row">{}</th><td>{}</td><td class="src">{}</td></tr>'.format(r["th"], r["td"], r["src"]) for r in t["rows"])
    note = '<p class="note">{}</p>'.format(page["facts_note"]) if page.get("facts_note") else ""
    return '<section><h2>{}</h2><table class="tbl"><thead><tr>{}</tr></thead><tbody>{}</tbody></table>{}</section>'.format(page.get("facts_heading", ""), head, rows, note)


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
    if page["faq"]:
        blocks.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": strip_tags(f["a"])}}
            for f in page["faq"]]})
    if page.get("steps5"):
        blocks.append({"@context": "https://schema.org", "@type": "HowTo", "name": "How to get married at the courthouse in {}".format(page.get("card_title", "")),
                       "totalTime": "P2D", "estimatedCost": {"@type": "MonetaryAmount", "currency": "USD", "value": str(page["fee_total"])},
                       "step": [{"@type": "HowToStep", "position": n + 1, "name": s["title"], "text": s["text"]} for n, s in enumerate(page["steps5"])]})
    items = []
    if page["type"] == "venues":
        items = [(v["name"], v["url"]) for v in page["venues"]]
    elif page["type"] == "dresses":
        items = [(gown_name(g).replace(" \u00b7 ", ": "), g["url"]) for g in page["gowns"]]
    elif page["type"] == "home":
        items = [(p["h1"], page_url(site, p["path"])) for p in sorted(pages.values(), key=lambda x: x.get("order", 0)) if p["path"] not in ("", "/")]
    elif page["type"] in ("hub", "packages") and page.get("cards"):
        items = [(i["name"], i["url"]) for i in page["cards"]]
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


HERO_BY_TYPE = {"home": "home", "trust": "home", "courthouse": "courthouse"}  # the list pages start with the answer, no photo


def render_hero(page, site, root):
    key = page.get("hero") or HERO_BY_TYPE.get(page["type"])
    im = (site.get("images") or {}).get(key)
    if not im:
        return ""
    return ('<!-- Hero photo: {credit}. Pexels License: free to use, no attribution required. -->'
            '<figure class="hero"><img src="{root}img/{file}" width="1000" height="600" alt="{alt}" fetchpriority="high" style="object-position:{pos}"></figure>').format(
        credit=im["credit"].replace("--", "-"), root=root, file=im["file"], alt=esc(im["alt"]), pos=im.get("pos", "50% 50%"))


def checked_line(page):
    src = ' &middot; <a href="#sources">official sources</a>' if page["type"] == "courthouse" else (
        ' &middot; <a href="@how-we-check/">no one pays to be listed</a>' if page["type"] in ("venues", "hub", "packages") else (
            ' &middot; <a href="@how-we-check/">we earn nothing from these sellers</a>' if page["type"] == "dresses" else ""))
    return '<p class="checked">Last checked: <time datetime="{}">{}</time>{}</p>'.format(page["last_checked"], fmt_date(page["last_checked"]), src)


def render_page(page, site, pages, finds):
    root = root_of(page["path"])
    app = esc(app_link(site, page))
    t = page["type"]
    cd = load_cdresses()
    head = [render_hero(page, site, root),
            '<p class="rl-eyebrow">{}</p>'.format(esc(page["eyebrow"])),
            "<h1>{}</h1>".format(h1_html(page)), checked_line(page), render_answer(page, pages)]
    trust = ('<p class="trust">Every price on this page links to the page it came from and shows the day we read it. '
             'No affiliate links: we earn nothing from these sellers or venues. <a href="@how-we-check/">How we check</a>.</p>')
    end = end_block(page, app, root)
    if t == "home":
        body = "\n".join([
            '<div class="home-top">{}<div class="home-copy">{}</div></div>'.format(
                render_hero(page, site, root),
                "\n".join(['<p class="rl-eyebrow">{}</p>'.format(esc(page["eyebrow"])), "<h1>{}</h1>".format(h1_html(page)),
                           checked_line(page), render_answer(page, pages), render_chips(page)])),
            render_home_menu(page, pages), board_block(page, app, root, "mid")])
        return finish_page(page, site, pages, internal(body, root), root, app)
    if t == "courthouse":
        mid = [render_steps(page), render_look(page, finds, cd), board_block(page, app, root, "mid"), render_tips(page)]
    elif t == "venues":
        mid = [render_venues_list(page, app, root, board=False), render_payless(page), board_block(page, app, root, "mid")]
    elif t in ("hub", "packages"):
        mid = [render_cards_section(page, app, root, pages, board=False), render_payless(page), board_block(page, app, root, "mid")]
    elif t == "dresses":
        mid = [render_gowns(page, app, root), render_safe(page)]
    else:  # trust
        mid = [render_trust_table(page)]
    tail = [render_faq(page), end, render_related(page, pages)]
    if t in ("venues", "hub", "packages"):  # the button block sits after the tips; a second block after the FAQ only repeated it
        tail = [render_faq(page), render_related(page, pages)]
    if t == "courthouse":  # frozen at round 1: the related list comes before the end block, then the trust line
        tail = [render_faq(page), render_related(page, pages), end, trust]
    if t == "trust":
        tail = [render_faq(page), board_block(page, app, root, "mid"), render_related(page, pages)]
    body = "\n".join(head + mid + tail)
    return finish_page(page, site, pages, internal(body, root), root, app)


def finish_page(page, site, pages, body, root, app):
    ld = "\n".join('<script type="application/ld+json">{}</script>'.format(
        json.dumps(b, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")) for b in jsonld_blocks(page, site, pages))
    lab = labels_for(page)
    if page["type"] == "courthouse":  # round 1: one line, label and "free"
        sticky = '<a href="{}" data-cta="sticky">{} &middot; free</a>'.format(app, lab[2])
    else:
        sticky = '<a href="{}" data-cta="sticky"><span>{}</span><small>Free &middot; no card &middot; then $9.92/month billed yearly</small></a>'.format(app, lab[2])
    html_ = fill(template("base.html"),
                 title=esc(page["title"]), description=esc(page["description"]),
                 canonical=page_url(site, page["path"]), base_url=site["base_url"], root=root,
                 last_checked=page["last_checked"], jsonld=ld, posthog_key=site["posthog_key"],
                 posthog_host=site["posthog_host"], app_url=app, body=body,
                 slug=page["path"].strip("/") or "home", medium=page["medium"],
                 main_class=" home" if page["type"] == "home" else "", body_class=("is-home " if page["type"] == "home" else "") + "t-" + page["type"],
                 btnhead=lab[1], btnsticky=lab[2], stickyhtml=sticky,
                 hdlink="" if page["type"] in ("venues", "hub", "packages") else '<a class="hd-link" href="{}" data-cta="header">{} &rarr;</a>'.format(app, lab[1]))
    return html_


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
    if (ROOT / "img").is_dir():
        shutil.copytree(ROOT / "img", DOCS / "img", dirs_exist_ok=True)
    (DOCS / "404.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Page not found: Rachel\'s List Guides</title><meta name="robots" content="noindex">'
        '<style>body{font-family:Georgia,serif;background:#FFFCF9;color:#231F20;margin:0;padding:48px 16px;text-align:center}'
        'a{color:#9C4A52}</style></head><body><h1>That page is not here.</h1>'
        '<p><a href="/">See all the guides</a></p></body></html>\n', encoding="utf-8")


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
            if e.code == 429:  # the site answered and asked us to slow down: the link is alive
                return url, True, e.code
            if method == "GET":
                return url, False, e.code
        except Exception as e:  # DNS, timeout, TLS
            if method == "GET":
                return url, False, str(e)[:60]
    return url, False, "?"


def check(do_links=True):
    site, pages, finds = build()
    problems, warnings = [], []
    outside = {}
    for p in pages.values():
        w = p["path"] or "home"
        walk_prices(p, w, problems)
        walk_prices(finds, "_finds", problems)
        walk_prices(load_cdresses(), "_courthouse_dresses", problems)
        if len(p["title"]) > 60:
            problems.append("{}: title is {} characters (max 60)".format(w, len(p["title"])))
        if len(p["description"]) > 155:
            problems.append("{}: description is {} characters (max 155)".format(w, len(p["description"])))
        if not re.search(r"\d", p["description"]):
            problems.append("{}: description has no number".format(w))
        if len(p["faq"]) != 5 and not (p["type"] == "home" and not p["faq"]):
            problems.append("{}: FAQ has {} questions (need 5)".format(w, len(p["faq"])))
        out = DOCS / "index.html" if p["path"] in ("", "/") else DOCS / p["path"].strip("/") / "index.html"
        h = out.read_text(encoding="utf-8")
        am = re.search(r"<!--answer-->(.*?)<!--/answer-->", h, re.S)
        words = strip_tags(am.group(1) if am else "").split()
        first50 = " ".join(words[:50])
        if not re.search(r"\d", first50) or str(datetime.date.fromisoformat(p["last_checked"]).year) not in first50:
            problems.append("{}: the first 50 words need a number and the year".format(w))
        if re.search(r"ultimate guide", json.dumps(p), re.I):
            problems.append("{}: 'ultimate guide' is banned".format(w))
        out = DOCS / "index.html" if p["path"] in ("", "/") else DOCS / p["path"].strip("/") / "index.html"
        h = out.read_text(encoding="utf-8")
        size = len(h.encode("utf-8"))
        if size > 200 * 1024:
            problems.append("{}: page is {:.1f} KB (max 200)".format(w, size / 1024))
        n_btn = len(re.findall(r'class="rl-btn"', h))
        if n_btn < 1:
            problems.append("{}: no button".format(w))
        if "utm_campaign=" + (p["path"].strip("/") or "home") not in h or "utm_medium=" + p["medium"] not in h:
            problems.append("{}: the button link lacks its utm tags".format(w))
        if re.search(r"\{(?!s\})[a-z_]+\}", re.sub(r"(?is)<(script|style)\b.*?</\1>", "", h)):
            problems.append("{}: an unfilled {{placeholder}} is left in the page".format(w))
        if "{{" in h:
            problems.append("{}: an unfilled {{{{placeholder}}}} is left in the page".format(w))
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
        need = {"Article", "BreadcrumbList"} | ({"FAQPage"} if p["faq"] else set()) | ({"ItemList"} if p["type"] in ("venues", "dresses", "hub", "packages", "home") else set())
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
                if ok:
                    continue
                msg = "link does not answer ({}): {}  [on {}]".format(status, url, ", ".join(sorted(set(outside[url]))[:2]))
                if re.match(r"https://rachelslist\.co(/|$)", url):  # the app's own domain is not ours to fix here
                    warnings.append(msg)
                else:
                    problems.append(msg)
    print("pages: {}  outside links: {}".format(len(pages), len(outside)))
    if warnings:
        print("WARNING (not blocking: the app's own domain): {} link(s) to rachelslist.co do not answer, e.g. {}".format(len(warnings), warnings[0][:160]))
    if problems:
        print("CHECK FAILED: {} problem(s)".format(len(problems)))
        for pr in problems:
            print(" -", pr)
        return 1
    print("CHECK OK: prices have sources and dates, titles <= 60, descriptions <= 155, structured data parses, every page has its button, no affiliate links{}".format(
        ", all outside links answer" + (" (app domain: see warning)" if warnings else "") if do_links else " (outside links not swept)"))
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
