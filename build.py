#!/usr/bin/env python3
"""Rachel's List Guides: build the static site from content/*.json.

    python3 build.py            write docs/ (pages, sitemap, robots, llms.txt, IndexNow key file)
    python3 build.py --check    build, then run every check that blocks a deploy
    python3 build.py --check --no-links   same, without the (slow) outside-link sweep
    python3 build.py --ping     tell Bing/IndexNow which pages changed (run ONLY once the domain is live)

Standard library only. Content lives in content/<name>.json (one per page) and content/_site.json.
Files starting with "_" are data, not pages (_site.json, _finds.json, _images.json, _courthouse_dresses.json).
The page plan and the ONLY rules are in CONVERSION-PLAN.md (section 4): every page starts with the answer, 4-6 real
photos with prices, the size or style chips and the button; photos load straight from the seller's or venue's server.
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

# ----------------------------------------------------------------------------- the button
# page type -> (the button, the small header link, the phone bar)
LABELS = {
    "courthouse": ("Show me dresses in my size", "Dresses in my size", "Show me dresses in my size"),
    "dresses": ("Show me gowns in my size", "Gowns in my size", "Show me gowns in my size"),
    "home": ("Find my dress &amp; venue for less", "Find my dress &amp; venue", "Find my dress &amp; venue for less"),
    "packages": ("Find my dress &amp; flowers for less", "Find my dress &amp; flowers", "Find my dress &amp; flowers for less"),
    "cost": ("Find my dress &amp; venue for less", "Find my dress &amp; venue", "Find my dress &amp; venue for less"),
}
DEFAULT_LABELS = ("Find my venue for less", "Find my venue", "Find my venue for less")
# page type -> (what she taps first, the button text after she has tapped; {s} = her size or style)
PICKED = {"courthouse": ("size", "Show me dresses in size {s}"), "dresses": ("size", "Show me gowns in size {s}"),
          "home": ("style", "Find my {s} dress &amp; venue for less")}
CATCH = "Free to start &middot; in your browser, no download &middot; no affiliate links: we earn nothing from these sellers"
FINE = "Free &middot; 90 seconds &middot; no card"
BOARD_HEAD = {
    "courthouse": "Want more like these, in <em>your</em> size?",
    "venues": "Still looking? Rachel finds your venue, dress &amp; decor <em>for less</em>",
    "hub": "Still looking? Rachel finds your venue, dress &amp; decor <em>for less</em>",
    "packages": "Still comparing? Rachel finds your dress &amp; flowers <em>for less</em>",
    "dresses": "Not your size? Rachel shows you <em>gowns in your size</em>, every week",
    "home": "Tell us your style. Rachel's List finds the dress, flowers and venue <em>for less</em>",
    "trust": "Tell Rachel your style. She finds the dress, flowers and venue <em>for less</em>",
}
END_LINE = {
    "courthouse": "I search Poshmark and Etsy every week for the looks you tap. Free to start.",
    "dresses": "Tell Rachel's List your size and the shapes you love. It checks Poshmark and Etsy every week. Free to start.",
}
END_LINE_DEFAULT = "Rachel's List searches Poshmark, Etsy and venues every week for the looks you tap. Free to start."
BOARD_CAP = "Finds on a Dream Board in the app (screen recording): the price now, the seller's original price struck through."
BANDS = [("2-4", "2&ndash;4"), ("6-8", "6&ndash;8"), ("10-12", "10&ndash;12"), ("14+", "14+")]
STYLES = [("boho-garden", "Boho"), ("classic-elegant", "Classic"), ("modern-minimal", "Modern"),
          ("rustic-barn", "Rustic"), ("beach", "Beach"), ("vintage", "Vintage")]
MAX_PHOTO_BYTES = 1_000_000  # a venue's own photo above this is not loaded (it would slow the first screen): its text card is shown

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
    if page.get("labels"):  # a page may name its own (button, header link, phone bar), e.g. a calculator
        return tuple(page["labels"])
    if page["type"] == "venues":
        city = CITY_NAMES.get(city_key(page), "")
        return ("Find my {} venue for less".format(city), "Find my venue", "Find my {} venue for less".format(city))
    return LABELS.get(page["type"], DEFAULT_LABELS)


def picked_for(page):
    return PICKED.get(page["type"])


def ico(name):
    return '<svg class="ico" aria-hidden="true"><use href="#{}"/></svg>'.format(name)


STRIPS = {}  # page path -> (cards in the first-screen row, cards with a real photo)


# ----------------------------------------------------------------------------- photos (each loaded from its own server, linked to its listing)
_IMAGES = None


def images():
    global _IMAGES
    if _IMAGES is None:
        f = ROOT / "content" / "_images.json"
        _IMAGES = load_json(f) if f.exists() else {}
    return _IMAGES


_SKIPS = None


def skips():
    global _SKIPS
    if _SKIPS is None:
        f = ROOT / "content" / "_image_skips.json"
        _SKIPS = load_json(f) if f.exists() else {}
    return _SKIPS


def photo_for(url):
    """(src, full-size fallback) for an item's own photo, or (None, None): the page then shows the item's text card.
    content/_image_skips.json lists the pictures looked at and left out (a logo, a stock picture, one that does not load)."""
    if url in skips():
        return None, None
    r = images().get(url)
    if not r or not r.get("src"):
        return None, None
    src = r["src"]
    if "cloudfront.net/posts/" in src and "/l_" in src:  # Poshmark's own medium size, same server: a gown card needs 300 px, not 900
        return src.replace("/l_", "/m_", 1), src
    if (r.get("bytes") or 0) > MAX_PHOTO_BYTES:
        return None, None
    return src, None


def img_tag(url, alt, w, h, eager=False):
    src, full = photo_for(url)
    if not src:
        return ""
    return ('<img src="{}" width="{}" height="{}" alt="{}" referrerpolicy="no-referrer" decoding="async"{}{} onerror="rlImg(this)">').format(
        esc(src), w, h, esc(alt), "" if eager else ' loading="lazy"', ' data-alt="{}"'.format(esc(full)) if full else "")


def has_photo(url):
    return photo_for(url)[0] is not None


def ph_card(url, price, name, sub="", attrs="", eager=False, cta="strip", line=""):
    """A small square photo card: the item's own photo, its price on it, its name and one line under it; a tap opens the listing."""
    img = img_tag(url, name, 200, 200, eager)
    return ('<a class="ph{noimg}" href="{url}" target="_blank" rel="noopener" data-cta="{cta}" data-item{attrs}>'
            '<span class="ph-img">{img}<span class="ph-t">{name}</span><span class="ph-p">{price}</span></span>'
            '<span class="ph-c"><b>{line}</b><span>{sub}</span></span></a>').format(
        noimg="" if img else " noimg", url=esc(url), cta=cta, attrs=attrs, img=img, name=esc(name), price=price, sub=esc(sub), line=esc(line or name))


def strip_wrap(cards, label, groups="", none="No find in that size this week. The button sets your size: Rachel watches for yours every Tuesday.", ndef=None):
    ndef = len(cards) if ndef is None else ndef
    return ('<div class="swrap"><p class="strip-h">{}</p><div class="pstrip{}" data-strip data-groups="{}">{}</div>'
            '<p class="fnone">{}</p></div>').format(label, " c4" if ndef == 4 else "", groups, "".join(cards), none)


# ----------------------------------------------------------------------------- the button blocks
def cta_html(page, app, pos):
    lab = labels_for(page)[0]
    pk = picked_for(page)
    tpl = ' data-pick="{}" data-base="{}" data-tpl="{}"'.format(pk[0], lab, pk[1]) if pk else ""
    catch = '<p class="catch">{}</p>'.format(CATCH) if pos == "first" else ""
    return '<div class="cta"{}><a class="rl-btn" href="{}" data-cta="{}" data-app{}><span class="lbl">{}</span></a><p class="fine">{}</p>{}</div>'.format(
        ' id="first-cta"' if pos == "first" else "", app, pos, tpl, lab, FINE, catch)


def btn_row(page, app, pos, root="../"):
    """After the 6th item of a list: the app in action (the real board, three steps) and the button."""
    return '<div class="gfull">{}</div>'.format(board_block(page, app, root, pos))


def pick_chips(kind):
    """The small first tap before the ask: her dress size, her style, her guest count or her budget. It sets &size= / &style= / &guests= / &budget= on every button."""
    opts, label, group = {
        "size": (BANDS, "Tap your size", "size"), "style": (STYLES, "Tap your style", "style"),
        "guests": ([("10", "10+"), ("20", "20+"), ("50", "50+")], "Guests", "fits"),
        "budget": ([("500", "Under $500"), ("1000", "Under $1k"), ("2500", "Under $2.5k")], "Budget", "budget")}[kind]
    b = "".join('<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(v, t) for v, t in opts)
    line = '<p class="pickline" data-noun="{}" hidden></p>'.format("dresses" if kind == "size" else "") if kind == "size" else ""
    return '<div class="fchips pick{}" data-group="{}" data-toggle><span class="lbl">{}</span>{}</div>{}'.format(" wrap" if kind == "style" else "", group, label, b, line)


def packages_gap(page):
    """What the providers' own lists leave out, counted from their `includes` text."""
    cards = [c for c in page.get("cards", []) if c["city"] != "las-vegas"]
    inc = [(c.get("includes") or "").lower() for c in cards]
    n = len(cards)
    dress = sum(1 for t in inc if "dress" in t or "gown" in t)
    flowers = sum(1 for t in inc if any(k in t for k in ("bouquet", "floral", "flower")))
    lead = "None of these lists a dress" if dress == 0 else "Only {} of {} list a dress".format(dress, n)
    return "{} and {} of {} leave flowers out".format(lead, n - flowers, n)


def packages_head(page):
    """The bridge for the packages page, from what the providers' own lists say they include."""
    return packages_gap(page).replace("None of these lists", "No package here lists") + ". Rachel's List finds both <em>for less</em>"


def board_block(page, app, root, pos="board"):
    """The app in action: the real Dream Board (screen recording, unblurred), 3 steps, the button."""
    head = packages_head(page) if page["type"] == "packages" else page.get("board_head") or BOARD_HEAD.get(page["type"], BOARD_HEAD["home"])
    return fill(template("board.html"), heading=head, root=root, cta=cta_html(page, app, pos), cap=BOARD_CAP)


def end_block(page, app, root):
    return fill(template("endblock.html"), root=root, line=page.get("end_line") or END_LINE.get(page["type"], END_LINE_DEFAULT), cta=cta_html(page, app, "end"))


# ----------------------------------------------------------------------------- the answer (first screen)
def answer_wrap(inner):
    return '<div class="answer" id="answer"><!--answer-->{}<!--/answer--></div>'.format(inner)


def whole_day(page):
    """The courthouse fees plus the cheapest dress and the bouquet we found: one real number for a whole courthouse day (each part from its own page)."""
    cd = load_cdresses().get("dresses", [])
    ff = ROOT / "research" / "flow-finds.json"
    bq = (load_json(ff)["cities"].get(city_key(page), {}) or {}).get("bouquet") if ff.exists() else None
    if not cd or not bq:
        return ""
    dress = min(d["price"] for d in cd)
    return '<p class="a-sub">Dresses here run {} to {}. With the cheapest ({}) and a {} bouquet: about <b>{}</b> in all.</p>'.format(
        money(dress), money(max(d["price"] for d in cd)), money(dress), esc(bq["price_display"]), money(page["fee_total"] + dress + bq["amount"]))


def answer_courthouse(page):
    city = page["card_title"]
    year = page["last_checked"][:4]
    return answer_wrap(
        '<p class="a-lead">A courthouse wedding in {city} costs <b class="a-big">${fee:,}</b> in {year}'
        '<span class="a-parts">{parts}{extra}</span></p>{day}'
        '<p class="a-meta">{pin}<span>{where} &middot; {when}</span></p>'.format(
            city=esc(city), fee=page["fee_total"], year=year, parts=esc(page["fee_parts"]), pin=ico("i-pin"), day=whole_day(page),
            extra=esc(" · " + page["fee_extra"]) if page.get("fee_extra") else "",
            where=esc(page["where"]), when=esc(page.get("when_short") or page["when"])))


def venue_stats(page):
    vs = page["venues"]
    flat = [v for v in vs if not v.get("per_person")]
    ten = [v for v in flat if (v.get("max_guests") or 0) >= 10]
    return vs, flat, ten


def answer_venues(page):
    vs, flat, ten = venue_stats(page)
    city = CITY_NAMES.get(city_key(page), "")
    prices = [v["amount"] for v in flat]
    lo, hi = min(prices), max(prices)
    year = page["last_checked"][:4]
    out = ('<p class="a-lead"><b class="a-big">{n}</b> small venues in {city} print their price in {year}: <b>{lo}</b> to <b>{hi}</b>, the middle <b>{mid}</b></p>').format(
        n=len(vs), city=esc(city), year=year, lo=money(lo), hi=money(hi), mid=money(statistics.median(prices)))
    bits = ["{} of {} are under $1,000.".format(sum(1 for p in prices if p < 1000), len(prices))]
    if ten:
        v = min(ten, key=lambda x: x["amount"])
        bits.append('For 10+ guests the cheapest is <b>{}</b> (<a href="{}" rel="noopener" target="_blank">{}</a>).'.format(money(v["amount"]), esc(v["url"]), esc(v["name"])))
    two = [x for x in flat if 0 < (x.get("max_guests") or 0) <= 2]
    if two:
        bits.append("{} is for two people.".format(money(min(x["amount"] for x in two))))
    return answer_wrap(out + '<p class="a-sub">{}</p>'.format(" ".join(bits)))


def micro_pick(venues):
    """The cheapest room for 10 or more guests, preferring a small room (at most 60 guests): the hub's 'micro' pick."""
    flat = [v for v in venues if not v.get("per_person") and (v.get("max_guests") or 0) >= 10]
    small = [v for v in flat if v["max_guests"] <= 60]
    pool = small or flat
    return min(pool, key=lambda v: v["amount"]) if pool else None


def answer_hub(page, pages):
    best = None
    for c in CITY_ORDER:
        p = next((x for x in pages.values() if x["type"] == "venues" and city_key(x) == c), None)
        pick = micro_pick(p["venues"]) if p else None
        if pick:
            best = pick["amount"] if best is None else min(best, pick["amount"])
    year = page["last_checked"][:4]
    allp = sorted(v["amount"] for p in pages.values() if p["type"] == "venues" for v in p["venues"] if not v.get("per_person"))
    lo = min(allp)
    return answer_wrap('<p class="a-lead">A venue for 10 or more guests starts at <b class="a-big">{best}</b> in {year}; the middle price in our five cities is <b>{mid}</b>.</p>'
                       '<p class="a-sub">{u} of {n} priced venues are under $1,000 and {f} are $5,000 or less. The {lo} one is a chapel for two.</p>'.format(
        best=money(best), mid=money(statistics.median(allp)), year=year, n=len(allp), u=sum(1 for a in allp if a < 1000), f=sum(1 for a in allp if a <= 5000), lo=money(lo)))


def answer_packages(page, pages=None):
    cards = page["cards"]
    main = [c for c in cards if c["city"] != "las-vegas"]
    vegas = [c for c in cards if c["city"] == "las-vegas"]
    amts = sorted(c["amount"] for c in main)
    year = page["last_checked"][:4]
    out = ('<p class="a-lead"><b class="a-big">{n}</b> elopement and micro wedding packages in our five cities print their price in {year}: <b>{lo}</b> to <b>{hi}</b>; {u} are under $1,000</p>').format(
        n=len(main), year=year, lo=money(amts[0]), hi=money(amts[-1]), u=sum(1 for a in amts if a < 1000))
    vg = " Two Las Vegas chapels start at {}.".format(money(min(c["amount"] for c in vegas))) if vegas else ""
    out += '<p class="a-sub">Middle price <b>{}</b>.{} {} packages in all.</p>'.format(money(statistics.median(amts)), vg, len(cards))
    return answer_wrap(out)


def answer_dresses(page):
    g = page["gowns"]
    sizes = [int(re.search(r"\d+", str(x["size"])).group()) for x in g if re.search(r"\d+", str(x["size"]))]
    year = page["last_checked"][:4]
    return answer_wrap('<p class="a-lead"><b class="a-big">{n}</b> secondhand designer wedding gowns, {lo} to {hi}, on Poshmark in {year}: sizes {a} to {b}.</p>'
                       '<p class="a-sub">Each re-opened {d}, still for sale at this price. &ldquo;orig.&rdquo; = the seller\'s original price.</p>'.format(
        n=len(g), lo=money(min(x["price"] for x in g)), hi=money(max(x["price"] for x in g)), year=year, a=min(sizes), b=max(sizes), d=fmt_short(page["last_checked"])))


def answer_generic(page):
    ah = re.sub(r'<p class="sub">.*?</p>', "", page["answer_html"], flags=re.S)
    ah = re.sub(r'<p class="hook">.*?</p>', "", ah, flags=re.S)
    return answer_wrap(ah)


def day_totals(pages):
    out = []
    cd = load_cdresses().get("dresses", [])
    ff = ROOT / "research" / "flow-finds.json"
    fc = load_json(ff)["cities"] if ff.exists() else {}
    for p in pages.values():
        if p["type"] == "courthouse" and cd:
            bq = (fc.get(city_key(p)) or {}).get("bouquet")
            if bq:
                out.append(p["fee_total"] + min(d["price"] for d in cd) + bq["amount"])
    return out


def answer_home(page, pages):
    year = page["last_checked"][:4]
    court = [p["fee_total"] for p in pages.values() if p["type"] == "courthouse"]
    flat = [v["amount"] for p in pages.values() if p["type"] == "venues" for v in p["venues"] if not v.get("per_person")]
    gowns = [g["price"] for p in pages.values() if p["type"] == "dresses" for g in p["gowns"]]
    n = len([p for p in pages.values() if p["path"] not in ("", "/") and p["type"] not in ("trust", "calculator")])
    days = day_totals(pages)
    whole = "A whole courthouse day, dress and bouquet included: about <b>{} to {}</b>. ".format(money(min(days)), money(max(days))) if days else ""
    return answer_wrap('<p class="a-lead">Real wedding prices in {y}, each from its own source page:</p>'
                       '<ul class="a-stats3"><li><b>${a:,}&ndash;${b:,}</b><span>courthouse fees</span></li><li><b>from {v}</b><span>a small venue</span></li><li><b>from {g}</b><span>a designer gown</span></li></ul>'
                       '<p class="a-sub">{w}{n} free guides, dated {d}. <a href="@how-we-check/">How we check</a>.</p>'.format(
        y=year, a=min(court), b=max(court), v=money(min(flat)), g=money(min(gowns)), n=n, d=fmt_short(page["last_checked"]) + ", " + year, w=whole))


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
    if t == "home":
        return answer_home(page, pages)
    return answer_generic(page)


# ----------------------------------------------------------------------------- the items (one record per thing with a photo, a price and a link)
def band_of_size(size):
    m = re.search(r"\d+", str(size))
    if not m:
        return ""
    n = int(m.group())
    return "2-4" if n <= 5 else "6-8" if n <= 9 else "10-12" if n <= 13 else "14+"


def gown_name(g):
    if g.get("model"):
        return "{} · {}".format(g["brand"], g["model"])
    return g["title"] if g["title"].lower().startswith(g["brand"].lower()) else "{}: {}".format(g["brand"], g["title"])


def gown_item(g):
    size = str(g["size"]).replace("US ", "")
    return {"url": g["url"], "price": g["price"], "old": g.get("old_price"), "brand": g["brand"], "model": g.get("model") or g["title"],
            "name": "{} {}".format(g["brand"], g.get("model") or "").strip(), "size": size, "band": band_of_size(size), "kind": "gown"}


def cd_item(d):
    name = d["name"] if d["style"].lower() in d["name"].lower() else "{} {}".format(d["name"], d["style"])
    return {"url": d["url"], "price": d["price"], "old": d.get("old_price"), "brand": d["name"], "model": d["style"], "name": name,
            "size": str(d["size"]), "band": d["band"], "kind": "dress"}


def venue_item(v):
    pp = bool(v.get("per_person"))
    mx = int(v.get("max_guests") or 0)
    return {"url": v["url"], "price": v["amount"], "pp": pp, "name": v["name"], "max": mx, "kind": "venue", "area": v.get("area", ""),
            "sub": ("Couple only" if 0 < mx <= 2 else "Up to {} guests".format(mx)) if mx else (v.get("guests") or "")}


def card_item(c, hub_fit=None):
    mx = int((hub_fit or {}).get(c["name"]) or 0)
    city = CITY_NAMES.get(c["city"], "Las Vegas" if c["city"] == "las-vegas" else "")
    fit = ("couple only" if 0 < mx <= 2 else "up to {} guests".format(mx)) if mx else ""
    return {"url": c["url"], "price": c["amount"], "pp": False, "name": c["name"], "max": mx, "kind": "card", "city": c["city"],
            "sub": "{} · {}".format(city, fit) if fit else city}


def price_txt(it):
    return money(it["price"]) + (" pp" if it.get("pp") else "")


def strip_card(it, attrs="", eager=False):
    if it["kind"] in ("gown", "dress"):
        sub = "Size {}".format(it["size"]) + (" · orig. {}".format(money(it["old"])) if it.get("old") else "")
        if it.get("tag"):
            sub = it["tag"]
        return ph_card(it["url"], money(it["price"]), it["name"], sub, ' data-band="{}"{}'.format(it["band"], attrs), eager, line=it["brand"])
    sub = it.get("tag") or it.get("sub", "")
    return ph_card(it["url"], price_txt(it), it["name"], sub, ' data-max="{}" data-amt="{}"{}'.format(it.get("max", 0), 999999 if it.get("pp") else int(it["price"]), attrs), eager)


def pick_strip(items, n=6, floor=4):
    """The cheapest items that have a photo (no photo shown twice), then the cheapest others as text cards, so the row has at least `floor` cards."""
    chosen, seen = [], set()
    for it in sorted(items, key=lambda x: x["price"]):
        src = photo_for(it["url"])[0]
        if not src or src in seen:
            continue
        seen.add(src)
        chosen.append(it)
        if len(chosen) == n:
            return chosen
    for it in sorted(items, key=lambda x: x["price"]):
        if len(chosen) >= max(floor, min(n, len(chosen))) and len(chosen) >= floor:
            break
        if it not in chosen:
            chosen.append(it)
    return chosen


def band_defaults(items, rot=0, n=6):
    """The first screen with no size chosen: one find per size band (the pick rotates by page), then the cheapest of the rest."""
    by = {}
    for it in sorted(items, key=lambda x: x["price"]):
        by.setdefault(it["band"], []).append(it)
    pick = []
    for b, _ in BANDS:
        v = [x for x in by.get(b, []) if has_photo(x["url"])] or by.get(b, [])
        if v:
            pick.append(v[rot % len(v)])
    rest = [x for x in sorted(items, key=lambda x: x["price"]) if x not in pick and has_photo(x["url"])]
    pick += rest[:max(0, n - len(pick))]
    return pick[:n]


# ----------------------------------------------------------------------------- the first screen
def courthouse_items(page):
    cd = load_cdresses()
    return [cd_item(d) for d in cd.get("dresses", [])], cd


def first_screen(page, site, pages, app, root):
    t = page["type"]
    head = ['<p class="rl-eyebrow">{}</p>'.format(esc(page["eyebrow"])), "<h1>{}</h1>".format(h1_html(page)), render_answer(page, pages)]
    attrs_def = lambda it, pk: " data-def" if it in pk else ""
    if t in ("courthouse", "dresses"):
        if t == "courthouse":
            items, cd = courthouse_items(page)
            rot = CITY_ORDER.index(city_key(page)) if city_key(page) in CITY_ORDER else 0
            label = "Courthouse dresses &middot; tap to open"
        else:
            items = [gown_item(g) for g in page["gowns"]]
            rot, label = 0, "Real gowns, still for sale &middot; tap to open"
        pk = band_defaults(items, rot) if t == "courthouse" else pick_strip(items, 6, 6)
        cards = [strip_card(it, " data-def" if it in pk else "", eager=it in pk) for it in sorted(items, key=lambda x: (x not in pk, pk.index(x) if x in pk else 0, x["price"]))]
        strip = strip_wrap(cards, label, "size")
        chips = pick_chips("size")
    else:
        if t == "venues":
            items = [venue_item(v) for v in page["venues"]]
        elif t == "packages":
            items = [card_item(c) for c in page["cards"] if c["city"] != "las-vegas"]
        elif t == "hub":
            items = hub_items(page, pages)
        else:  # home: a dress, a gown, venues, a package
            items = home_items(pages)
        pk = hub_strip(items) if t == "hub" else (items if t == "home" else pick_strip(items, 6, 4))
        rest = [x for x in sorted(items, key=lambda x: (not has_photo(x["url"]), x["price"])) if x not in pk] if t != "home" else []
        cards = [strip_card(it, " data-def", eager=True) for it in pk] + [strip_card(it, "", eager=False) for it in rest]
        label = {"venues": "Cheapest venues that show a photo", "hub": "10+ guest rooms with a photo, by city", "packages": "Cheapest packages that show a photo",
                 "home": "Real finds this week"}.get(t, "Real finds")
        groups = {"venues": "fits", "hub": "fits", "packages": "budget"}.get(t, "")
        strip = strip_wrap(cards, label, groups, none="Nothing with a photo matches that. The list below has every one.", ndef=len(pk))
        chips = pick_chips({"venues": "guests", "hub": "guests", "packages": "budget"}.get(t, "style"))
    STRIPS[page["path"]] = (len(pk), sum(1 for it in pk if has_photo(it["url"])))
    bridge = '<p class="bridge">{}. Rachel&rsquo;s List finds both <em>for less</em>.</p>'.format(packages_gap(page)) if t == "packages" else ""
    return "\n".join(head + [strip, checked_line(page), chips, bridge, cta_html(page, app, "first")])


def hub_items(page, pages):
    """Every venue on the five city pages (the hub shows the best of each city, the photos come from all of them)."""
    out = []
    for c in CITY_ORDER:
        vp = next((x for x in pages.values() if x["type"] == "venues" and city_key(x) == c), None)
        for v in (vp["venues"] if vp else []):
            if v.get("per_person"):
                continue
            it = venue_item(v)
            it["city"] = c
            it["sub"] = "{} · {}".format(CITY_NAMES[c], it["sub"].lower() if it["sub"] else "")
            out.append(it)
    return out


def hub_strip(items):
    """Rooms for 10 or more guests only (the answer says so): the cheapest with a photo first, one per city where it can, then text cards."""
    room = [x for x in items if 10 <= (x.get("max") or 0) <= 60]
    out, seen = [], set()
    for c in CITY_ORDER:
        for it in sorted((x for x in room if x["city"] == c), key=lambda x: x["price"]):
            src = photo_for(it["url"])[0]
            if src and src not in seen:
                seen.add(src)
                out.append(it)
                break
    for it in pick_strip(room, 6, 4):
        if it not in out and len(out) < 6:
            out.append(it)
    return sorted(out, key=lambda x: x["price"])[:6]


def home_items(pages):
    out = []
    g5 = next((p for p in pages.values() if p["path"] == "wedding-dresses-under-500"), None)
    if g5:
        gs = sorted(g5["gowns"], key=lambda g: g["price"])
        out += [dict(gown_item(g), tag="Gown · Poshmark") for g in gs if has_photo(g["url"])][:2]
    cds = [d for d in load_cdresses().get("dresses", []) if has_photo(d["url"]) and "mini" in d["style"] and d["price"] <= 100]
    if cds:
        out.append(dict(cd_item(sorted(cds, key=lambda d: d["price"])[0]), tag="Dress · Poshmark"))
    for path, city in (("small-wedding-venues-houston", "Houston"), ("small-wedding-venues-dallas", "Dallas")):
        p = pages.get(path)
        if p:
            v = [venue_item(x) for x in p["venues"] if has_photo(x["url"]) and not x.get("per_person")]
            if v:
                out.append(dict(sorted(v, key=lambda x: x["price"])[0], tag="Venue · " + city))
    pk = pages.get("elopement-packages")
    if pk:
        c = [card_item(x) for x in pk["cards"] if x["city"] != "las-vegas" and has_photo(x["url"])]
        if c:
            it = sorted(c, key=lambda x: x["price"])[0]
            out.append(dict(it, tag="Package · " + it["sub"]))
    return sorted(out, key=lambda x: x["price"])


# ----------------------------------------------------------------------------- courthouse
def render_steps(page):
    items = []
    for i, s in enumerate(page["steps5"], 1):
        fee = '<span class="sfee">{}{}</span>'.format(esc(s["fee"]), '<small>{}</small>'.format(esc(s["fee_note"])) if s.get("fee_note") else "") if s.get("fee") else "<span></span>"
        items.append('<li><span class="sn">{}</span><div class="sb"><b>{}</b><span>{}</span></div>{}</li>'.format(i, esc(s["title"]), esc(s["text"]), fee))
    note = ' <i>({})</i>'.format(esc(page["where_note"])) if page.get("where_note") else ""
    wh = ('<ul class="a-rows wh"><li>{}<span><b>Where</b>{}{}</span></li><li>{}<span><b>When</b>{}</span></li></ul>'.format(
        ico("i-pin"), esc(page["where"]), note, ico("i-cal"), esc(page["when"])))
    return '<section><h2>Do it in <em>{} steps</em></h2>{}<ol class="steps5">{}</ol>{}</section>'.format(len(items), wh, "".join(items), sources_details(page))


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


def dress_card(it, attrs=""):
    """A dress or gown for the grid: its photo, the price, the seller's original, the size; a tap opens the listing."""
    img = img_tag(it["url"], "{}, {}".format(it["name"], money(it["price"])), 240, 300)
    was = '<s><span class="vh">seller\'s original </span>{}</s>'.format(money(it["old"])) if it.get("old") else ""
    return ('<a class="dcard{noimg}" data-item data-band="{band}"{attrs} href="{url}" rel="noopener" target="_blank" data-cta="dress">'
            '<span class="d-img">{img}<span class="d-t">{name}</span></span>'
            '<span class="d-price"><span class="price">{price}</span>{was}</span>'
            '<span class="d-name">{brand}</span><span class="d-meta">Size {size} &middot; {model}</span></a>').format(
        noimg="" if img else " noimg", band=esc(it["band"]), attrs=attrs, url=esc(it["url"]), img=img, name=esc(it["name"]), price=money(it["price"]), was=was,
        brand=esc(it["brand"]), size=esc(it["size"]), model=esc(it["model"]))


def grid_with_button(cards, btn, after=6):
    return "".join(cards[:after]) + btn + "".join(cards[after:])


def clean_item(text):
    """The short name of a bouquet or menu, before any colon, bracket or sentence end (the research notes after it stay in research/)."""
    t = re.split(r"\s*[:(]| Standard| Shop at|\. ", text or "", maxsplit=1)[0].strip()
    return t[:60]


def find_row(icon, title, sub, price, url, small=""):
    img = img_tag(url, title, 64, 64)
    lead = '<span class="fimg">{}</span>'.format(img) if img else ico(icon)
    return ('<li><a class="frow{}" href="{}" rel="noopener" target="_blank" data-cta="find">{}<span><b>{}</b><span class="fm">{}</span></span>'
            '<span class="fp">{}{}</span></a></li>').format(" has-img" if img else "", esc(url), lead, esc(title), esc(sub), small, esc(price))


def grid_cards(items, pk, more_after=None):
    """The list below the first-screen row: cards in price order; the ones already in the row stay out of the way until she picks a size."""
    pkurls = {p["url"] for p in pk}
    rest = [it for it in sorted(items, key=lambda x: (not has_photo(x["url"]), x["price"])) if it["url"] not in pkurls]
    cards = [dress_card(it, " data-more" if (more_after is not None and i >= more_after) else "") for i, it in enumerate(rest)]
    skip = [dress_card(it, " data-skipdef") for it in sorted(items, key=lambda x: x["price"]) if it["url"] in pkurls]
    return cards, skip, len(items)


def render_courthouse_grid(page, app):
    items, cd = courthouse_items(page)
    rot = CITY_ORDER.index(city_key(page)) if city_key(page) in CITY_ORDER else 0
    cards, skip, n = grid_cards(items, band_defaults(items, rot), more_after=6)
    dd = fmt_short(cd["date_read"]) if cd.get("date_read") else "Oct 28"
    lead = "Short, midi and simple white dresses, each re-opened on {} and still for sale. Tap your size above, or open any one.".format(dd)
    return ('<section><h2>{head}</h2><p class="sec-lead">{lead}</p><div class="fwrap" data-groups="size"><p class="fstate" hidden></p>'
            '<div class="dgrid">{body}</div><button type="button" class="fc showmore" data-more-btn>Show all {n} dresses</button>'
            '<p class="fnone">No dress in that size this week. The button sets your size: Rachel watches for yours every Tuesday.</p></div>'
            '<p class="srcnote">Dresses are Poshmark listings; each photo and price links to the seller\'s own page.</p></section>').format(
        head=page["look_heading"].replace("look,", "<em>look</em>,") if page.get("look_heading") else "Your courthouse look, for less",
        lead=lead, body=grid_with_button(cards, btn_row(page, app, "mid", root_of(page["path"]))) + "".join(skip), n=n)


def render_courthouse_finds(page):
    city = city_key(page)
    rows = []
    fl = (load_json(ROOT / "research" / "flow-finds.json")["cities"] if (ROOT / "research" / "flow-finds.json").exists() else {}).get(city, {})
    bq = fl.get("bouquet")
    if bq:
        rows.append(find_row("i-flowers", "A bridal bouquet", "{}: {}".format(bq["name"].split(" (")[0], clean_item(bq["item"])), bq["price_display"], bq["url"]))
    lu = fl.get("lunch")
    if lu:
        rows.append(find_row("i-dinner", "Lunch after, in a private room", lu["name"].split(" (")[0], lu["price_display"].replace(" per person", ""), lu["url"], '<small class="from">per person </small>'))
    ph = load_finds().get(city, {}).get("photographer")
    if ph and (ph.get("hours") or 9) <= 1 and ph["amount"] <= 500:
        rows.append(find_row("i-photo", "Courthouse photos", "{}: {}".format(ph["name"], ph["package"]), money(ph["amount"]), ph["url"], '<small class="from">from </small>' if ph.get("from") else ""))
    if not rows:
        return ""
    return '<section><h2>The rest of the day, <em>for less</em></h2><ul class="finds">{}</ul><p class="srcnote">Each price is from the shop\'s or restaurant\'s own page, read {}.</p></section>'.format("".join(rows), fmt_short(page["last_checked"]))


def render_tips(page):
    lis = "".join("<li><b>{}</b>{}</li>".format(esc(t["h"]), esc(t["t"])) for t in page.get("tips", []))
    return '<section><h2>Make the day feel like a <em>wedding</em></h2><ul class="tipl">{}</ul></section>'.format(lis) if lis else ""


# ----------------------------------------------------------------------------- venues, packages, hub
_THUMBS = set()


def thumb(url, name, seen):
    """The card's photo, once per page: a second package from the same venue shows no repeat of it."""
    src = photo_for(url)[0]
    if not src or src in seen:
        return ""
    seen.add(src)
    return img_tag(url, name, 120, 120)


def venue_card(v, seen=None):
    pp = v.get("per_person")
    unit = "per person" if pp else ""
    mx = int(v.get("max_guests") or 0)
    fits = '<span class="v-fits">{}</span>'.format("Couple only" if 0 < mx <= 2 else "Up to {} guests".format(mx)) if mx else ""
    inc = '<p class="v-inc">{}</p>'.format(esc(v["includes"])) if v.get("includes") else ""
    img = thumb(v["url"], v["name"], seen if seen is not None else set())
    thumb_html = '<a class="v-ph" href="{}" rel="noopener" target="_blank" data-cta="venue" tabindex="-1" aria-hidden="true">{}</a>'.format(esc(v["url"]), img) if img else ""
    return ('<article class="vcard{cls}" data-item data-max="{mx}" data-amt="{amt}">{thumb}<div class="v-body"><div class="v-top">'
            '<h3 class="v-name">{fits}<a href="{url}" rel="noopener" target="_blank" data-cta="venue">{name}</a><span class="v-area">{area}</span></h3>'
            '<div class="v-price">{price}<small>{unit}</small></div></div>'
            '<p class="v-for">{guests} &middot; {pf}</p>{inc}'
            '<p class="v-src"><a href="{url}" rel="noopener" target="_blank" data-cta="venue">Venue\'s own page</a> &middot; read {date}</p></div></article>').format(
        cls=" has-ph" if img else "", thumb=thumb_html, mx=mx, amt=999999 if pp else int(v["amount"]), url=esc(v["url"]), name=esc(v["name"]), area=esc(v.get("area", "")), fits=fits,
        price=money(v["amount"]), unit=esc(unit), guests=esc(v["guests"]), pf=esc(v["price_for"]), inc=inc, date=fmt_short(v["date_read"]))


def venue_chips():
    def grp(name, label, opts):
        b = ['<button type="button" class="fc" data-v="all" aria-pressed="true">Any</button>']
        b += ['<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(v, t) for v, t in opts]
        return '<div class="fchips" data-group="{}"><span class="lbl">{}</span>{}</div>'.format(name, label, "".join(b))
    return (grp("fits", "Guests", [("10", "10+"), ("20", "20+"), ("50", "50+")]) +
            grp("budget", "Budget", [("1000", "Under $1k"), ("3000", "Under $3k")]))


def render_venues_list(page, app):
    seen = set()
    cards = [venue_card(v, seen) for v in page["venues"]]
    return ('<section><h2>{head}</h2><p class="sec-lead">{intro}</p>'
            '<div class="fwrap" data-groups="fits budget">{chips}<div class="vlist">{body}</div><p class="fnone">No venue matches both filters. Choose &ldquo;Any&rdquo; on one of them.</p></div>'
            '{note}</section>').format(note=('<p class="srcnote">{}</p>'.format(esc(page["facts_note"])) if page.get("facts_note") else ""),
        head=page.get("facts_heading") or "Venues with a <em>printed price</em>, cheapest first", intro=page.get("facts_intro", ""),
        chips=venue_chips(), body=grid_with_button(cards, btn_row(page, app, "mid", root_of(page["path"]))))


def render_payless(page):
    if not page.get("pay_less"):
        return ""
    lis = "".join("<li><b>{}</b>{}</li>".format(esc(t["h"]), t["t"]) for t in page["pay_less"])
    return '<section><h2>{}</h2><ul class="tipl">{}</ul></section>'.format(page.get("pay_less_heading", "How to pay <em>less</em> for a small venue"), lis)


def render_cards_section(page, app, pages=None):
    """Hub and packages: a city chooser, then every card cheapest first, the button after the 6th."""
    cards = page.get("cards", [])
    fit = {v["name"]: v.get("max_guests") for p in pages.values() if p["type"] == "venues" for v in p["venues"]} if (page["type"] == "hub" and pages) else {}
    cities = [c for c in CITY_ORDER + ["las-vegas"] if any(x["city"] == c for x in cards)]
    chips = ['<button type="button" class="fc" data-v="all" aria-pressed="true">All cities</button>']
    chips += ['<button type="button" class="fc" data-v="{}" aria-pressed="false">{}</button>'.format(c, CITY_NAMES[c]) for c in cities]
    out, seen = [], set()
    for c in cards:
        det = '<p class="v-for">{}</p>'.format(esc(c["detail"])) if c.get("detail") else ""
        flags = ""
        if page["type"] == "packages":
            inc_l = (c.get("includes") or "").lower()
            fl = [("Officiant", ("officiant", "minister")), ("Photos", ("photo",)), ("License", ("license",)), ("Flowers", ("bouquet", "floral", "flower"))]
            named = [n for n, ks in fl if any(k in inc_l for k in ks)]
            flags = '<ul class="flags">{}</ul>'.format("".join('<li class="y">&#10003; {}</li>'.format(n) for n in named)) if named else ""
        mx = fit.get(c["name"]) or 0
        tag = '<span class="v-fits">{}</span>'.format("Destination: Las Vegas") if c["city"] == "las-vegas" else (
            '<span class="v-fits">{}</span>'.format(esc(CITY_NAMES.get(c["city"], ""))) if page["type"] == "packages" and c["city"] else (
                '<span class="v-fits">{} &middot; {}</span>'.format(esc(CITY_NAMES.get(c["city"], "")), "couple only" if 0 < mx <= 2 else "up to {} guests".format(mx)) if mx else ""))
        inc = '<p class="v-inc">Includes: {}</p>'.format(esc(c["includes"])) if c.get("includes") else ""
        img = thumb(c["url"], c["name"], seen)
        thumb_html = '<a class="v-ph" href="{}" rel="noopener" target="_blank" data-cta="venue" tabindex="-1" aria-hidden="true">{}</a>'.format(esc(c["url"]), img) if img else ""
        out.append(('<article class="vcard{cls}" data-item data-city="{city}" data-max="{mx}" data-amt="{amt}">{thumb}<div class="v-body"><div class="v-top"><h3 class="v-name">{tag}<a href="{url}" rel="noopener" target="_blank" data-cta="venue">{name}</a>'
                    '<span class="v-area">{sub}</span></h3><div class="v-price">{price}</div></div>{flags}{inc}{det}'
                    '<p class="v-src"><a href="{url}" rel="noopener" target="_blank" data-cta="venue">Their own page</a> &middot; read {date}</p></div></article>').format(
            cls=" has-ph" if img else "", thumb=thumb_html, city=esc(c["city"]), mx=mx, amt=int(c["amount"]), url=esc(c["url"]), name=esc(c["name"]), sub=esc(c.get("sub", "")), price=esc(c["price_display"]), det=det, inc=inc,
            tag=tag, flags=flags, date=fmt_short(c["date_read"])))
    links = ""
    if page["type"] == "hub":
        for c in CITY_ORDER:
            vp = next((x for x in (pages or {}).values() if x["type"] == "venues" and city_key(x) == c), None)
            if vp:
                links += '<a class="citylink" data-for="{c}" href="@{path}/" hidden>See all {n} {name} venues &rarr;</a>'.format(c=c, path=vp["path"], n=len(vp["venues"]), name=CITY_NAMES[c])
    return ('<section><h2>{head}</h2><p class="sec-lead">{intro}</p><div class="fwrap" data-groups="city"><div class="fchips" data-group="city"><span class="lbl">City</span>{chips}</div>{links}'
            '{legend}<div class="vlist">{body}</div><p class="fnone">Nothing listed for this city yet.</p></div></section>').format(
        legend='<p class="srcnote legend">&#10003; = named on the provider\'s own page; what is not ticked is not named there</p>' if page["type"] == "packages" else "",
        head=page.get("facts_heading", "Prices, cheapest first"), intro=page.get("facts_intro", ""), chips="".join(chips), links=links,
        body=grid_with_button(out, btn_row(page, app, "mid", root_of(page["path"]))))


# ----------------------------------------------------------------------------- dresses
def render_gowns(page, app):
    items = [gown_item(g) for g in page["gowns"]]
    cards, skip, n = grid_cards(items, pick_strip(items, 6, 6))
    other = '<p class="srcnote">{} Other price band: <a href="@{}/">{}</a>.</p>'.format(esc(page.get("facts_intro", "")), *(("wedding-dresses-under-1000", "gowns from $501 to $1,000") if "500" in page["path"] else ("wedding-dresses-under-500", "gowns at $500 or less")))
    return ('<section class="gowns-sec"><h2>{head}</h2><div class="fwrap" data-groups="size"><p class="fstate" hidden></p><div class="dgrid big">{body}</div>'
            '<p class="fnone">No gown in that size this week. The button sets your size: Rachel watches for yours every Tuesday.</p></div>{other}</section>').format(
        head=page.get("facts_heading") or "This week's <em>gowns</em>", body=grid_with_button(cards, btn_row(page, app, "mid", root_of(page["path"]))) + "".join(skip), other=other)


def render_safe(page):
    if page["type"] != "dresses":
        return ""
    return ('<section><h2>Buying secondhand <em>safely</em></h2><ul class="tipl">'
            '<li><b>Measure first</b>Take your bust, waist and hips, and compare them with the measurements in the listing photos. If a size tag has no measurements, ask the seller.</li>'
            '<li><b>Know the return rule</b>Poshmark says it gives a full refund if an item never ships or does not match the listing description; otherwise all sales are final. You have 72 hours after delivery to open a return case with photos, so inspect the dress before you accept the order '
            '(<a href="https://poshmark.com/posh_protect" rel="noopener">Posh Protect</a>, read Oct 28, 2026).</li>'
            '<li><b>Ask before you buy</b>Message the seller for more photos, the fabric, the brand label and tags, and any flaws. A clear answer is a good sign.</li>'
            '<li><b>Plan for a seamstress</b>Get a quote from a local seamstress before you buy: a hem or a bustle is often priced separately from the dress.</li></ul></section>')


# ----------------------------------------------------------------------------- faq, related, home
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
    return '<section class="menu" id="menu"><h2>Pick your <em>guide</em></h2><div class="hgrid">{}</div></section>'.format("".join(out))


def render_trust_table(page):
    t = page.get("table")
    if not t:
        return ""
    head = "".join('<th scope="col">{}</th>'.format(esc(h)) for h in t["headers"])
    rows = "".join('<tr><th scope="row">{}</th><td>{}</td><td class="src">{}</td></tr>'.format(r["th"], r["td"], r["src"]) for r in t["rows"])
    note = '<p class="note">{}</p>'.format(page["facts_note"]) if page.get("facts_note") else ""
    return '<section><h2>{}</h2><table class="tbl"><thead><tr>{}</tr></thead><tbody>{}</tbody></table>{}</section>'.format(page.get("facts_heading", ""), head, rows, note)


# ----------------------------------------------------------------------------- calculators (shared: one page type, one render function)
# A calculator page: "type": "calculator", "medium": "calculator", "calc_template": "calc-<name>.html", "calc_data": "<name>",
# optional "labels" (button, header link, phone bar), "board_head", "end_line".
# render_calculator fills templates/<calc_template> with {{data}} (JSON for the page's own inline script = page["calc"] + what
# CALC_DATA[<name>] returns), {{root}}, {{cta}} (the first button, id="first-cta": the template places it under its result),
# {{board}} (the Dream Board block) and every string CALC_DATA returns under "html" (static result, tables, finds).
# Each calculator keeps its own JS inside its template; no "{{" may appear in that JS (fill() and --check both read it).
def calc_intro(pages):
    names = [p["h1"][0].lower() + p["h1"][1:] for p in sorted(pages.values(), key=lambda x: x.get("order", 0)) if p["type"] == "calculator"]
    return "Free calculators: {}. ".format(", ".join(names)) if names else ""


def render_calculator(page, pages, finds, app="", root="../"):
    got = dict(CALC_DATA[page["calc_data"]](page, pages, finds))
    parts = got.pop("html", {})
    blob = dict(page.get("calc", {}))
    blob.update(got)
    data = json.dumps(blob, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return fill(template(page["calc_template"]), data=data, root=root, cta=cta_html(page, app, "first"),
                board=board_block(page, app, root), **parts)


def cents(x):
    """Whole dollars, half up (the page's JS rounds the same way: Math.floor(x + 0.5))."""
    return "${:,}".format(int(x + 0.5))


def plural(n, one, many):
    return "{:,} {}".format(n, one if n == 1 else many)


def alcohol_calc(inp, d):
    """The alcohol calculator's formula. Its JS twin (rlAlcCalc in templates/calc-alcohol.html) must give the same result."""
    try:
        g, h = int(float(inp.get("guests"))), int(float(inp.get("hours")))
    except (TypeError, ValueError):
        return None
    if g <= 0 or h <= 0:
        return None
    capped = []
    if g > d["max_guests"]:
        g = d["max_guests"]
        capped.append("guests")
    if h > d["max_hours"]:
        h = d["max_hours"]
        capped.append("hours")
    pace = d["pace_heavy"] if inp.get("pace") == 2 else d["pace_average"]
    drinks = g * h * pace
    sp = d["split_bw"] if inp.get("bar") == "bw" else d["split_full"]
    share = lambda pct: (drinks * pct + 50) // 100  # servings of one kind, rounded half up, in whole numbers
    up = lambda a, b: -(-a // b)
    rows = []

    def add(key, name, served, s1, s2, buy, b1, b2, price):
        rows.append({"key": key, "name": name, "served": plural(served, s1, s2), "buy": plural(buy, b1, b2), "n": buy, "unit": b2 if buy != 1 else b1,
                     "cost": buy * price if isinstance(price, (int, float)) else None})
    w = share(sp["wine"])
    add("wine", "Wine", w, "glass", "glasses", up(w, d["wine_glasses"]), "bottle", "bottles", inp.get("p_wine"))
    if sp.get("liquor"):
        lq = share(sp["liquor"])
        add("liquor", "Liquor", lq, "pour", "pours", up(lq, d["liquor_pours"]), "bottle", "bottles", inp.get("p_liquor"))
    b = share(sp["beer"])
    add("beer", "Beer", b, "can", "cans", up(b, d["beer_case"]), "case of 24", "cases of 24", inp.get("p_beer"))
    if inp.get("toast"):
        add("sparkling", "Sparkling (toast)", g, "flute", "flutes", up(g, d["sparkling_flutes"]), "bottle", "bottles", inp.get("p_spark"))
    priced = [r for r in rows if r["cost"] is not None]
    return {"guests": g, "hours": h, "pace": pace, "bar": "bw" if inp.get("bar") == "bw" else "full", "toast": bool(inp.get("toast")),
            "drinks": drinks, "rows": rows, "total": sum(r["cost"] for r in priced), "priced": [r["key"] for r in priced],
            "missing": [r["key"] for r in rows if r["cost"] is None], "capped": capped,
            "avg": {"wine": inp.get("p_wine") == d["wine_price"], "beer": inp.get("p_beer") == d["beer_price"]}}


def join_and(words):
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def alcohol_html(r, d):
    """The result block. Its JS twin (rlAlcHtml) writes the same string, so the page reads the same before and after the script runs."""
    cap = "For {} &middot; {} &middot; {} &middot; {}".format(plural(r["guests"], "guest", "guests"), plural(r["hours"], "hour", "hours"),
                                                             "full bar" if r["bar"] == "full" else "beer and wine", plural(r["pace"], "drink an hour", "drinks an hour"))
    if r["capped"]:
        cap += " (capped at {})".format(join_and([plural(d["max_guests"], "guest", "guests") if c == "guests" else plural(d["max_hours"], "hour", "hours") for c in r["capped"]]))
    head = " &middot; ".join("<b>{:,}</b> {} of {}".format(x["n"], x["unit"].replace(" of 24", ""), x["key"]) for x in r["rows"])
    body = "".join('<tr><th scope="row">{}</th><td>{}</td><td>{}</td><td{}>{}</td></tr>'.format(
        x["name"], x["served"], x["buy"], "" if x["cost"] is not None else ' class="calc-na"', cents(x["cost"]) if x["cost"] is not None else "add a price") for x in r["rows"])
    if r["priced"]:
        what = join_and(r["priced"])
        cost = "{}: <b>{}</b>".format(what[0].upper() + what[1:], cents(r["total"]))
        avg = [k for k in r["priced"] if r["avg"].get(k)]
        yours = [k for k in r["priced"] if k not in avg]
        if avg and not yours:
            cost += ", at US average store prices (BLS, {}).".format(d["price_month"])
        elif avg:
            cost += ": {} at US average store prices (BLS, {}), {} at your price.".format(join_and(avg), d["price_month"], join_and(yours))
        else:
            cost += ", at your prices."
    else:
        cost = "Type prices under Change prices for a cost."
    if r["missing"] and r["priced"]:
        cost += " Add a price for {} under Change prices for the full total.".format(join_and(r["missing"]))
    foot = '<tr><th scope="row">Total</th><td>{}</td><td></td><td>{}</td></tr>'.format(plural(r["drinks"], "drink", "drinks"), cents(r["total"]) if r["priced"] else "")
    return ('<p class="calc-cap">{}</p><p class="calc-head">{}</p><table class="calc-out"><thead><tr><th scope="col">Drink</th><th scope="col">Served</th>'
            '<th scope="col">Buy</th><th scope="col">Cost</th></tr></thead><tbody>{}</tbody><tfoot>{}</tfoot></table><p class="calc-cost">{}</p>').format(cap, head, body, foot, cost)


def calc_data_alcohol(page, pages, finds):
    d = {s["key"]: s.get("amount", s.get("value")) for s in page["sources"]}
    d.update({k: v for k, v in page.get("calc", {}).items()})
    ex = dict(d["example"], p_wine=d["wine_price"], p_beer=d["beer_price"])
    res = alcohol_calc(ex, d)
    bw = alcohol_calc(dict(ex, bar="bw"), d)
    toast = alcohol_calc(dict(ex, toast=True), d)
    liquor_n = next(x["n"] for x in res["rows"] if x["key"] == "liquor")
    even = (bw["total"] - res["total"]) / liquor_n  # the liquor price per bottle where beer and wine only costs the same as the full bar
    w_bw = next(x for x in bw["rows"] if x["key"] == "wine")
    b_bw = next(x for x in bw["rows"] if x["key"] == "beer")
    sp = next(x for x in toast["rows"] if x["key"] == "sparkling")
    less = ('<li><b>Beer and wine only.</b> No liquor to buy: for {g} guests and {h} hours, {wb} of wine and {bb} of beer, about {c} at {m} average prices. '
            'That is cheaper than the full bar when your liquor costs more than about {e} a bottle.</li>'
            '<li><b>A shorter bar.</b> Each hour less is one drink less per guest: {g} fewer drinks for {g} guests.</li>'
            '<li><b>A toast only if you want one.</b> It adds {sp} for {g} guests ({f} flutes a bottle).</li>').format(
        g=ex["guests"], h=ex["hours"], wb=w_bw["buy"], bb=b_bw["buy"].replace(" of 24", ""), c=cents(bw["total"]), m=d["price_month"],
        e=cents(even), sp=sp["buy"], f=d["sparkling_flutes"])
    rows = []
    for s in page["sources"]:
        note = '<br><span class="note">{}</span>'.format(esc(s["note"])) if s.get("note") else ""
        rows.append('<tr><th scope="row">{}<br><b class="calc-used">{}</b></th><td>&ldquo;{}&rdquo;{}</td><td class="src"><a href="{}" rel="noopener">{}</a><br>read {}</td></tr>'.format(
            esc(s["what"]), esc(s["shown"]), esc(s["quote"]), note, esc(s["source_url"]), esc(s["source_name"]), fmt_short(s["date_read"])))
    srcs = '<table class="tbl"><thead><tr><th scope="col">What we use</th><th scope="col">The page says</th><th scope="col">Source</th></tr></thead><tbody>{}</tbody></table>'.format("".join(rows))
    fr = []
    gowns = sorted((g for p in pages.values() if p["type"] == "dresses" for g in p["gowns"] if g.get("price")), key=lambda g: g["price"])
    dates = []
    if gowns:
        g = gowns[0]
        dates.append(g["date_read"])
        fr.append(find_row("i-dress", "A designer wedding gown", "{}, size {}, on Poshmark{}".format(g["brand"], g["size"], ", seller's original {}".format(money(g["old_price"])) if g.get("old_price") else ""),
                           money(g["price"]), g["url"]))
    fl = sorted((dict(v["florist"], city=c) for c, v in finds.items() if v.get("florist", {}).get("amount")), key=lambda x: x["amount"])
    if fl:
        f = fl[0]
        dates.append(f["date_read"])
        fr.append(find_row("i-flowers", "A bridal bouquet", "{}, {}: {}".format(f["name"], CITY_NAMES.get(f["city"], f["city"]), clean_item(f["item"])), money(f["amount"]), f["url"]))
    ph = sorted((dict(v["photographer"], city=c) for c, v in finds.items() if v.get("photographer", {}).get("amount")), key=lambda x: x["amount"])
    if ph:
        x = ph[0]
        dates.append(x["date_read"])
        fr.append(find_row("i-photo", "Wedding photos", "{}, {}: {}".format(x["name"], CITY_NAMES.get(x["city"], x["city"]), x["package"]), money(x["amount"]), x["url"],
                           '<small class="from">from </small>' if x.get("from") else ""))
    finds_html = ""
    if fr:
        finds_html = ('<section class="calc-finds"><h2>The rest of your list, <em>for less</em></h2><ul class="finds">{}</ul>'
                      '<p class="srcnote">The cheapest of each on our guides, from the seller&rsquo;s or shop&rsquo;s own page, read {}.</p></section>').format("".join(fr), fmt_short(max(dates)))
    return {"wine_price": d["wine_price"], "beer_price": d["beer_price"],
            **{s["key"]: s.get("amount", s.get("value")) for s in page["sources"]},
            "html": {"static_result": alcohol_html(res, d), "less": less, "sources": srcs, "finds": finds_html,
                     "wine_price": "{:.2f}".format(d["wine_price"]), "beer_price": "{:.2f}".format(d["beer_price"]),
                     "price_month": d["price_month"], "max_guests": d["max_guests"], "max_hours": d["max_hours"]}}


CALC_DATA = {"alcohol": calc_data_alcohol}


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
    if page["type"] == "calculator":
        blocks.append({"@context": "https://schema.org", "@type": "WebApplication", "name": h1, "url": url,
                       "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
                       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}})
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


def checked_line(page):
    src = ' &middot; <a href="#sources">official sources</a>' if page["type"] == "courthouse" else (
        ' &middot; <a href="@how-we-check/">no one pays to be listed</a>' if page["type"] in ("venues", "hub", "packages", "dresses", "home", "calculator") else "")
    orig = ""
    return '<p class="checked">Last checked: <time datetime="{}">{}</time>{}{}</p>'.format(page["last_checked"], fmt_date(page["last_checked"]), src, orig)


def render_page(page, site, pages, finds):
    root = root_of(page["path"])
    app = esc(app_link(site, page))
    t = page["type"]
    if t in ("trust", "calculator"):  # no photos to show: the answer, then the table (trust) or the tool (calculator)
        head = ['<p class="rl-eyebrow">{}</p>'.format(esc(page["eyebrow"])), "<h1>{}</h1>".format(h1_html(page)), checked_line(page), render_answer(page, pages)]
        if t == "trust":  # a calculator's template places its own first button ({{cta}}), right under its result
            head.append(cta_html(page, app, "first"))
    else:
        head = [first_screen(page, site, pages, app, root)]
    board = board_block(page, app, root)
    end = end_block(page, app, root)
    if t == "home":
        mid = [render_home_menu(page, pages), board]
        tail = []
    elif t == "courthouse":
        mid = [render_steps(page), render_courthouse_grid(page, app), render_courthouse_finds(page), render_tips(page)]
        tail = [render_faq(page), end, render_related(page, pages)]
    elif t == "venues":
        mid = [render_venues_list(page, app), render_payless(page)]
        tail = [render_faq(page), end, render_related(page, pages)]
    elif t in ("hub", "packages"):
        mid = [render_cards_section(page, app, pages), render_payless(page)]
        tail = [render_faq(page), end, render_related(page, pages)]
    elif t == "dresses":
        mid = [render_gowns(page, app), render_safe(page)]
        tail = [render_faq(page), end, render_related(page, pages)]
    elif t == "calculator":
        mid = [render_calculator(page, pages, finds, app, root)]
        tail = [render_faq(page), end, render_related(page, pages)]
    else:  # trust
        mid = [render_trust_table(page)]
        tail = [render_faq(page), board, render_related(page, pages)]
    body = "\n".join(head + mid + tail)
    return finish_page(page, site, pages, internal(body, root), root, app)


def finish_page(page, site, pages, body, root, app):
    ld = "\n".join('<script type="application/ld+json">{}</script>'.format(
        json.dumps(b, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")) for b in jsonld_blocks(page, site, pages))
    lab = labels_for(page)
    pk = picked_for(page)
    stp = ' data-pick="{}" data-base="{}" data-tpl="{}"'.format(pk[0], lab[2], pk[1]) if pk else ""
    sticky = '<a href="{}" data-cta="sticky" data-app{}><span class="lbl">{}</span><small>Free</small></a>'.format(app, stp, lab[2])
    hd = {"courthouse": "Dresses in size {s}", "dresses": "Gowns in size {s}"}.get(page["type"])
    hdp = ' data-pick="size" data-base="{}" data-tpl="{}"'.format(lab[1], hd) if hd else ""
    html_ = fill(template("base.html"),
                 title=esc(page["title"]), description=esc(page["description"]),
                 canonical=page_url(site, page["path"]), base_url=site["base_url"], root=root,
                 last_checked=page["last_checked"], jsonld=ld, posthog_key=site["posthog_key"],
                 posthog_host=site["posthog_host"], app_url=app, body=body,
                 slug=page["path"].strip("/") or "home", medium=page["medium"],
                 main_class=" home" if page["type"] == "home" else "", body_class=("is-home " if page["type"] == "home" else "") + "t-" + page["type"],
                 stickyhtml=sticky,
                 hdlink='<a class="hd-link" href="{}" data-cta="header" data-app{}><span class="lbl">{}</span> &rarr;</a>'.format(app, hdp, lab[1]))
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
             + calc_intro(pages) +
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
        if 'id="first-cta"' not in h:
            problems.append("{}: no button on the first screen".format(w))
        if re.search(r"\$9\.92|billed yearly|\$24/month|/month|per month", re.sub(r"(?is)<script\b.*?</script>", "", h)):
            problems.append("{}: a subscription price is on the page (the pages show only 'Free to start')".format(w))
        if p["type"] not in ("trust", "calculator") and STRIPS.get(p["path"], (0, 0))[1] < 4:
            warnings.append("{}: only {} real photos in the first-screen row (wanted 4 to 6)".format(w, STRIPS.get(p["path"], (0, 0))[1]))
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
                if re.match(r"https://rachelslist\.co(/|$)", url) or status == 429:  # the app's own domain is not ours to fix here; 429 = the site answered and asked us to slow down
                    warnings.append(msg)
                else:
                    problems.append(msg)
    print("pages: {}  outside links: {}".format(len(pages), len(outside)))
    if warnings:
        for wmsg in warnings:
            print("WARNING (not blocking):", wmsg[:200])
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
