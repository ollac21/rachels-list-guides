#!/usr/bin/env python3
"""Bootstrap content/<page>.json from the researched inputs.

Inputs  : .cache/dresses.json (tools/dresses.py), .cache/research/<city>.json (hand research, quotes verified
          by tools/verify_quotes.py), content/_finds.json
Outputs : content/<page>.json  (these files are the source of truth afterwards: the PR tab edits them directly;
          running this script again overwrites them)
Run     : python3 -I tools/make_content.py
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
CACHE = ROOT / ".cache"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_io as _rio  # noqa: E402
TODAY = _rio.latest_date()


def money(n):
    n = float(n)
    return "${:,.0f}".format(n) if n == int(n) else "${:,.2f}".format(n)


def fdate(iso):
    d = datetime.date.fromisoformat(iso)
    return "{} {}, {}".format(d.strftime("%b"), d.day, d.year)


def save(name, obj):
    obj.setdefault("last_checked", TODAY)
    obj.setdefault("first_published", TODAY)
    (CONTENT / (name + ".json")).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote content/{}.json".format(name))


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


# ----------------------------------------------------------------------------- dresses
def dress_pages():
    d = json.loads((ROOT / "research" / "dresses.json").read_text())
    specs = [
        ("wedding-dresses-under-500", "under500", 500, "Designer Wedding Dresses Under $500 (This Week)",
         "Designer Wedding Dresses Under $500", "Under $500", 13),
        ("wedding-dresses-under-1000", "under1000", 1000, "Designer Wedding Dresses Under $1,000 (This Week)",
         "Designer Wedding Dresses Under $1,000", "Under $1,000", 14),
    ]
    import re as _re
    gn = json.loads((CONTENT / "_gown_names.json").read_text())
    for path, band, cap, title, h1, em, order in specs:
        gowns = d[band]
        for _g in gowns:
            _m = _re.search(r"([0-9a-f]{24})$", _g["url"])
            _n = gn.get(_m.group(1)) if _m else None
            if _n:
                _g["brand"], _g["model"] = _n["brand"], _n["model"]
        if not gowns:
            continue
        n = len(gowns)
        cheapest = min(gowns, key=lambda g: g["price"])
        big = max(gowns, key=lambda g: g["old_price"] - g["price"])
        lo = "$500 or less" if cap == 500 else "$1,000 or less"
        band_txt = "$500 or less" if cap == 500 else "more than $500 and up to $1,000"
        other = "wedding-dresses-under-1000" if cap == 500 else "wedding-dresses-under-500"
        answer = (
            "<p>As of {date}, we found <strong class=\"big\">{n}</strong> secondhand designer wedding gowns listed at {lo} on Poshmark, "
            "from <strong>{lowp}</strong> ({lowb}, seller's original {lowo}) to <strong>{hip}</strong>. "
            "The biggest gap: a {bigb} gown at {bigp}, seller's original {bigo}.</p>"
            "<p class=\"sub\">Each listing was re-opened on {date} and was still available at the price shown.</p>"
        ).format(date=fdate(TODAY), n=n, lo=band_txt if cap == 1000 else lo, lowp=money(cheapest["price"]),
                 lowb=cheapest["brand"], lowo=money(cheapest["old_price"]), hip=money(max(g["price"] for g in gowns)),
                 bigb=big["brand"], bigp=money(big["price"]), bigo=money(big["old_price"]))
        oneliner = ("{n} secondhand designer wedding gowns at {band} on Poshmark, from {lo} to {hi}; "
                    "each re-opened {date}.").format(n=n, band=band_txt, lo=money(cheapest["price"]),
                                                    hi=money(max(g["price"] for g in gowns)), date=fdate(TODAY))
        faq = [
            {"q": "Where can I buy a designer wedding dress for under ${}?".format("500" if cap == 500 else "1,000"),
             "a": "Secondhand marketplaces such as Poshmark list designer gowns from individual sellers. On {date} we found {n} listed at {lo}, "
                  "starting at {lowp} for a {lowb} gown (seller's original {lowo}).".format(
                      date=fdate(TODAY), n=n, lo=band_txt, lowp=money(cheapest["price"]), lowb=cheapest["brand"],
                      lowo=money(cheapest["old_price"]))},
            {"q": "Is it safe to buy a wedding dress secondhand?",
             "a": "Each listing states its own condition, so read the notes and the seller's photos before you buy. "
                  "We re-open every listing on {date} and drop any that is sold or has changed price.".format(date=fdate(TODAY))},
            {"q": "How do I know a secondhand wedding dress will fit?",
             "a": "Sizes on this page are exactly what each seller lists, and bridal sizing often differs from street sizing. "
                  "Compare the seller's measurements with yours, and tap the dresses you love in Rachel's List so she can watch Poshmark and Etsy for your size every week."},
            {"q": "What does \"seller's original\" mean?",
             "a": "It is the original price the seller typed into the listing, shown exactly as printed. "
                  "We cannot check what a gown cost new, so we show it only as the seller's original price."},
            {"q": "How often is this list updated?",
             "a": "Every Tuesday. We re-open each gown, drop the ones that are sold or repriced, and change the date at the top. "
                  "The list you see was last checked on {date}.".format(date=fdate(TODAY))},
        ]
        page = {
            "path": path, "type": "dresses", "medium": "dresses", "order": order,
            "title": title,
            "description": "{n} secondhand designer wedding gowns at {lo}, each re-opened {d}. Price now, seller's original, size and link.".format(
                n=n, lo=band_txt.replace("more than $500 and up to $1,000", "$501 to $1,000"), d=fdate(TODAY)),
            "h1": h1.replace("Designer Wedding Dresses Under", "Designer wedding dresses under"), "h1_em": em.lower().replace("under", "under"),
            "eyebrow": "Poshmark gowns \u00b7 weekly",
            "refresh_note": "Refreshed weekly, on Tuesdays.",
            "answer_html": answer, "oneliner": oneliner,
            "card_title": em, "card_line": "{} gowns, from {}".format(n, money(cheapest["price"])),
            "facts_heading": "This week's <em>gowns</em>",
            "facts_intro": "Source: Poshmark listings, each re-opened on {} and still available at the price shown. Tap a gown to open its listing. Biggest gap between price now and seller's original first; shipping and tax are not included.".format(fdate(TODAY)),
            "gowns": gowns,
            "ideas": [
                {"ref": "find:houston.florist"}, {"ref": "find:new-york.photographer"},
                {"ref": "venue:small-wedding-venues-houston:cheapest10"},
                {"ref": "fact:courthouse-wedding-houston:license_fee"},
            ],
            "ideas_lead": "A dress is one line of the budget. Here is one real find in each of the other categories, each from its own page and dated.",
            "faq": faq,
            "related": [{"path": other, "label": "Designer wedding dresses " + ("$501 to $1,000" if cap == 500 else "$500 or less"),
                         "note": "The other price band, re-opened the same day."},
                        {"path": "small-wedding-venues-houston", "label": "Small and micro wedding venues in Houston"},
                        {"path": "courthouse-wedding-houston", "label": "Courthouse wedding in Houston"},
                        {"path": "how-we-check", "label": "How we check every price"}],
        }
        save(path, page)


# ----------------------------------------------------------------------------- trust
def trust_page():
    faq = [
        {"q": "Where do your numbers come from?",
         "a": "Courthouse fees come from the county or city clerk's own web page and are quoted word for word. Venue and photographer prices come from their own websites. Dress prices come from the Poshmark listing, re-opened on the day shown."},
        {"q": "Do you earn money from the venues, sellers or links on these pages?",
         "a": "No. There are no affiliate links, and we earn nothing from any seller or venue listed. The only button on a page leads to Rachel's List, our own free app."},
        {"q": "What happens when a price changes?",
         "a": "Every row shows the day we read it. Dress pages are re-checked every Tuesday, venue pages monthly, and courthouse pages every three months. A price we can no longer confirm is removed, not guessed."},
        {"q": "Why is a fee or a price missing from a page?",
         "a": "If we cannot find a number on the official or seller's own page, we leave it out and say so. We do not use averages, estimates or prices copied from directories."},
        {"q": "How do I report a wrong price?",
         "a": "Check the source link on the row and tell us through <a href=\"https://rachelslist.co/\" rel=\"noopener\">rachelslist.co</a>. If the source says something different, we correct the page and the date."},
    ]
    table = {"headers": ["Page type", "Where the number comes from", "How often"], "rows": [
        {"th": "Courthouse pages", "td": "The county or city clerk's own web page. The sentence is copied word for word and shown on the row, with its link and the day we read it.", "src": "Every 3 months"},
        {"th": "Venue pages", "td": "The venue's own website. We show the price and guest count in the venue's words, what is included, a link and the day we read it. Directories and social posts are only leads, never sources.", "src": "Monthly"},
        {"th": "Dress pages", "td": "The week's secondhand listings on Poshmark. Each listing is re-opened: it must still be available at the price shown. Sold or repriced ones are dropped.", "src": "Every Tuesday"},
        {"th": "Photographers, florists", "td": "The photographer's or florist's own page, with the package or item named as they name it.", "src": "Monthly"},
    ]}
    answer = ("<p>Every price on Rachel's List Guides links to the page it came from and shows the day we read it ({d}). "
              "Government fees are quoted from the official page, venue prices from the venue's own site, and dress prices from a Poshmark listing re-opened that day. "
              "There are <strong>no affiliate links</strong>.</p>").format(d=fdate(TODAY))
    save("how-we-check", {
        "path": "how-we-check", "type": "trust", "medium": "hub", "order": 16,
        "title": "How We Check Every Price: Rachel's List",
        "description": "Our rules for the 16 guides: official pages quoted word for word, venues' own prices, dated rows, no affiliate links. Checked Oct 28, 2026.",
        "h1": "How we check every price", "h1_em": "check",
        "eyebrow": "Sources &middot; dates &middot; no affiliate links".replace("&middot;", "·"),
        "refresh_note": "Rules reviewed with every refresh.",
        "answer_html": answer,
        "oneliner": "Official pages quoted word for word, venues' own prices, dated rows, no affiliate links.",
        "facts_heading": "Where each number <em>comes from</em>", "table": table,
        "facts_note": "We leave out any number we cannot find on the right kind of page. A missing number is better than a guessed one.",
        "ideas": [], "faq": faq,
        "related": [{"path": "", "label": "All the guides"}],
    })


# ----------------------------------------------------------------------------- research -> pages
CITY_TITLES = {  # exactly the title tags of the spec
    "courthouse": {"chicago": "Courthouse Wedding in Chicago: Real Cost & Steps (2026)",
                   "new-york": "Courthouse Wedding in NYC: Real Cost & Steps (2026)",
                   "houston": "Courthouse Wedding in Houston: Real Cost & Steps (2026)",
                   "dallas": "Courthouse Wedding in Dallas: Real Cost & Steps (2026)",
                   "los-angeles": "Courthouse Wedding in Los Angeles: Real Cost (2026)"},
    "venues": {"houston": "Small & Micro Wedding Venues in Houston, With Prices",
               "chicago": "Small & Micro Wedding Venues in Chicago, With Prices",
               "new-york": "Small & Micro Wedding Venues in NYC, With Prices",
               "dallas": "Small & Micro Wedding Venues in Dallas, With Prices",
               "los-angeles": "Small & Micro Wedding Venues in LA, With Prices"},
}
ORDER = {"courthouse": {"chicago": 1, "new-york": 2, "houston": 3, "dallas": 4, "los-angeles": 5},
         "venues": {"houston": 6, "chicago": 7, "new-york": 8, "dallas": 9, "los-angeles": 10}}
SHORT = {"houston": "Houston", "chicago": "Chicago", "new-york": "New York", "dallas": "Dallas", "los-angeles": "Los Angeles"}
OFFICE_SHORT = {"houston": "Harris County Clerk", "chicago": "Cook County Clerk", "new-york": "NYC City Clerk",
                "dallas": "Dallas County Clerk", "los-angeles": "LA County Registrar-Recorder/County Clerk"}


def research(city):
    sys.path.insert(0, str(ROOT / "tools"))
    import research_io
    return research_io.load(city)


def faqs_for(key):
    sys.path.insert(0, str(ROOT / "tools"))
    import faqs  # tools/faqs.py: hand-written, per page
    return faqs.get(key)


FIND_DISPLAY = {
    ("houston", "photographer"): dict(name="Brit Fine Photography", package="micro wedding coverage, 5 hours", includes="5 hours of shooting, split as you wish", **{"from": True}),
    ("houston", "florist"): dict(name="KVITKAFA", item="Burgundy bridal bouquet (pre-order)"),
    ("chicago", "photographer"): dict(name="The Adri Photo Co.", package="courthouse and small-ceremony coverage, 2 hours", includes="a full edited gallery", **{"from": True}),
    ("chicago", "florist"): dict(name="Flowers for Dreams", item="bridal bouquet, white and cream (self-service shop)"),
    ("new-york", "photographer"): dict(name="Erica Morris Photography", package="City Hall ceremony plus a 30-minute shoot", includes="50+ edited images"),
    ("new-york", "florist"): dict(name="NYC Flower Pop", item="elopement bouquet, 8 to 10 inch, seasonal (pickup)"),
    ("los-angeles", "photographer"): dict(name="Golden Vibes Photo", package="courthouse weddings, 1 hour, 10 guests or fewer", includes="50+ images", **{"from": True}),
    ("los-angeles", "florist"): dict(name="Hanamate Floral Design", item="bridal bouquet, customizable"),
    ("dallas", "photographer"): dict(name="Shelly Voss Photography", package="courthouse ceremony coverage, 1-hour minimum ($400 an hour)", includes=""),
}


def finds_file():
    out = {}
    for slug, _ in CITIES:
        r = research(slug)
        if not r:
            continue
        out[slug] = {}
        for k in ("photographer", "florist"):
            v = r.get(k)
            if v and v.get("amount") is not None and v.get("url"):
                out[slug][k] = {x: v[x] for x in v if x != "quote"}
                out[slug][k]["quote"] = v.get("quote", "")
                out[slug][k].update({a: b for a, b in FIND_DISPLAY.get((slug, k), {}).items()})
    (CONTENT / "_finds.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote content/_finds.json:", {k: sorted(v) for k, v in out.items()})


DOMAIN_NAME = {"cookcountyclerkil.gov": "Cook County Clerk", "cookcountycourtil.gov": "Circuit Court of Cook County",
               "cookcountycourt.org": "Circuit Court of Cook County", "portal.311.nyc.gov": "NYC311 (City of New York)",
               "cclerk.hctx.net": "Harris County Clerk", "dallascounty.org": "Dallas County Clerk",
               "lavote.gov": "LA County Registrar-Recorder/County Clerk", "www.lavote.gov": "LA County Registrar-Recorder/County Clerk"}
ANSWER_CREDIT = {  # (who issues the license, who performs the ceremony, a short note)
    "houston": ("Harris County Clerk", "Justice of the Peace, Precinct 1", ", cash only; other Harris County courts set their own fees"),
    "dallas": ("Dallas County Clerk", "Justice of the Peace court 2-2", " by appointment, cash only; other Dallas County courts charge $60 to $150"),
    "chicago": ("Cook County Clerk", "Circuit Court of Cook County", ", an administrative fee"),
    "new-york": ("NYC City Clerk", "City Clerk's office, any borough", ""),
    "los-angeles": ("LA County Registrar-Recorder/County Clerk", "county office, prepaid", ""),
}
CREDIT = {"houston": "license: Harris County Clerk; ceremony: Harris County Justice of the Peace, Precinct 1",
          "dallas": "license: Dallas County Clerk; ceremony: Dallas County Justice of the Peace court 2-2","chicago": "license: Cook County Clerk; ceremony: Circuit Court of Cook County",
          "new-york": "NYC City Clerk, from the City's NYC311 pages"}


def source_name(url, fallback):
    from urllib.parse import urlparse
    u = urlparse(url)
    host = u.netloc.lower()
    if host == "jp.hctx.net":
        return "Harris County Justice of the Peace, Pct. 1"
    if host.endswith("dallascounty.org") and "/jpcourts/" in u.path:
        return "Dallas County Justice of the Peace court"
    for k, v in DOMAIN_NAME.items():
        if host == k or host.endswith("." + k):
            return v
    return fallback


def courthouse_page(slug, name):
    r = research(slug)
    if not r or not r.get("courthouse") or not r["courthouse"].get("facts"):
        return
    c = r["courthouse"]
    office = OFFICE_SHORT[slug]
    credit = CREDIT.get(slug, office)
    facts = []
    for f in c["facts"]:
        x = dict(f)
        x["source_name"] = source_name(x["source_url"], OFFICE_SHORT[slug])
        if x["key"] in ("license_fee", "ceremony_fee") and x.get("amount") is not None:
            x["allin"] = True
        facts.append(x)
    lic = next((f for f in facts if f["key"] == "license_fee"), None)
    cer = next((f for f in facts if f["key"] == "ceremony_fee"), None)
    if lic and cer and cer.get("amount") is not None:
        total = lic["amount"] + cer["amount"]
        lc, cc, note = ANSWER_CREDIT[slug]
        lead = ("a courthouse wedding in {n} costs <strong class=\"big\">{t}</strong> in official fees: <strong>{l}</strong> for the marriage license ({lc}) "
                "and <strong>{c}</strong> for the civil ceremony ({cc}).").format(n=name, t=money(total), l=money(lic["amount"]), c=money(cer["amount"]), lc=lc, cc=cc + note)
        one_fee = "{} in fees: license {} + ceremony {}".format(money(total), money(lic["amount"]), money(cer["amount"]))
        card_line = "{} in fees".format(money(total))
    elif lic:
        lead = ("a courthouse wedding in {n} starts with a <strong>{l}</strong> marriage license ({o}). "
                "The official pages we read list no separate civil-ceremony fee.").format(n=name, l=lic["display"], o=office)
        one_fee = "license {}".format(lic["display"])
        card_line = "{} marriage license".format(money(lic["amount"]))
    else:
        return
    answer = ("<p>As of {d}, {lead}</p><p class=\"hook\"><a href=\"#allin\">A full courthouse day with a dress, flowers, photos and a dinner room: about {{{{allin}}}} all in</a></p>"
              "<p class=\"sub\">Every figure below is the official page's own wording, with its link and the day we read it.</p>").format(d=fdate(TODAY), lead=lead)
    left = [x.strip().rstrip(".") for x in (c.get("left_out") or []) if x.strip()]
    sys.path.insert(0, str(ROOT / "tools"))
    import display as _d
    left = _d.LEFT_OUT.get(slug, left)
    faq = faqs_for("courthouse-wedding-" + slug)
    if not faq:
        print("no FAQ yet for", slug); return
    path = "courthouse-wedding-" + slug
    desc = "Courthouse wedding in {n}: {fee}, per the official pages. Wait, ID and booking steps. Checked {d}.".format(n=name, fee=one_fee, d=fdate(TODAY))
    if len(desc) > 155:
        desc = "Courthouse wedding in {n}: {fee}, per the official pages. Checked {d}.".format(n=name, fee=one_fee, d=fdate(TODAY))
    page = {
        "path": path, "type": "courthouse", "medium": "courthouse", "order": ORDER["courthouse"][slug],
        "title": CITY_TITLES["courthouse"][slug],
        "description": desc,
        "h1": "Courthouse wedding in " + name, "h1_em": name,
        "eyebrow": "{} \u00b7 {}".format(name, OFFICE_SHORT[slug].split("/")[0]),
        "refresh_note": "Courthouse pages are re-checked every 3 months.",
        "answer_html": answer,
        "oneliner": "{} ({}), checked {}.".format(one_fee[0].upper() + one_fee[1:], OFFICE_SHORT[slug], fdate(TODAY)),
        "card_title": name, "card_line": card_line,
        "office": office,
        "facts_heading": "The fees and the <em>steps</em>, from the official pages",
        "facts_intro": "Copied word for word from {}. Each row links to the page it came from.".format(office),
        "facts": facts, "steps": c.get("steps", []), "facts_note_list": left,
        "facts_note_head": "Not shown, because no official page states it:",
        "ideas": [{"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:{}.florist".format(slug)}]
                 + ([{"ref": "find:{}.photographer".format(slug)}] if (r.get("photographer") or {}).get("hours", 9) <= 2 else [])
                 + [{"ref": "venue:small-wedding-venues-{}:cheapest10".format(slug)}],
        "ideas_lead": "The license is the legal part. Here is one real find in each category couples still buy for a courthouse day, each from its own page and dated.",
        "faq": faq,
        "related": [{"path": "small-wedding-venues-" + slug, "label": "Small and micro wedding venues in " + name,
                     "note": "Want a dinner or a small party after the courthouse? Prices from the venues' own sites."},
                    {"path": "wedding-dresses-under-500", "label": "Designer wedding dresses, $500 or less"},
                    {"path": "elopement-packages", "label": "Elopement and micro wedding packages"},
                    {"path": "how-we-check", "label": "How we check every price"}],
    }
    save(path, page)


def venue_page(slug, name):
    r = research(slug)
    if not r or not r.get("venues"):
        return
    vs = sorted(r["venues"], key=lambda v: (bool(v.get("per_person")), v["amount"]))
    for v in vs:
        v.pop("curl_verifiable", None)
    totals = [v for v in vs if not v.get("per_person")]
    lo, hi = totals[0], totals[-1]
    faq = faqs_for("small-wedding-venues-" + slug)
    if not faq:
        print("no FAQ yet for venues", slug); return
    ten = [v for v in totals if v.get("max_guests", 0) >= 10]
    if ten:
        answer = ("<p>As of {d}, small wedding venues in {c} start at <strong class=\"big\">{lp}</strong> for just the two of you and <strong>{tp}</strong> for venues that seat 10 or more ({tn}, {tf}). "
                  "The {n} venues we verified go up to {hp}.</p>"
                  "<p class=\"sub\">Each price and guest count is quoted from the venue's own website and shows the day we read it.</p>").format(
            d=fdate(TODAY), c=name, tp=ten[0]["price_display"], tn=e(ten[0]["name"]), tf=e(ten[0]["price_for"].split(" (")[0]), lp=lo["price_display"], n=len(vs), hp=hi["price_display"])
    else:
        answer = ("<p>As of {d}, {n} small and micro wedding venues in {c} print their own prices, from <strong>{lp}</strong> ({ln}) to <strong>{hp}</strong> ({hn}).</p>"
                  "<p class=\"sub\">Each price and guest count is quoted from the venue's own website and shows the day we read it.</p>").format(
            d=fdate(TODAY), n=len(vs), c=name, lp=lo["price_display"], ln=e(lo["name"]), hp=hi["price_display"], hn=e(hi["name"]))
    path = "small-wedding-venues-" + slug
    page = {
        "path": path, "type": "venues", "medium": "venues", "order": ORDER["venues"][slug],
        "title": CITY_TITLES["venues"][slug],
        "description": "{n} small and micro wedding venues in {c}, {lp} to {hp}, each price from the venue's own site. Checked {d}.".format(
            n=len(vs), c=name, lp=money(lo["amount"]), hp=money(hi["amount"]), d=fdate(TODAY)),
        "h1": "Small & micro wedding venues in " + name, "h1_em": name,
        "eyebrow": "{} \u00b7 venue prices".format(name),
        "refresh_note": "Venue pages are re-checked monthly.",
        "answer_html": answer,
        "oneliner": "{} venues with printed prices, {} to {} (checked {}).".format(len(vs), lo["price_display"], hi["price_display"], fdate(TODAY)),
        "card_title": name, "card_line": "{} venues, {} to {}".format(len(vs), lo["price_display"], hi["price_display"]),
        "facts_heading": "Venues with a <em>printed price</em>, cheapest first",
        "facts_intro": "Only venues that print a number for a small, micro, weekday or elopement booking on their own website. Directories and social posts were leads, never sources.",
        "facts_note": "A price is for the package the venue names, on the day we read it. Ask the venue about dates, taxes and fees.",
        "venues": vs,
        "ideas": [{"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:{}.florist".format(slug)},
                  {"ref": "find:{}.photographer".format(slug)}, {"ref": "fact:courthouse-wedding-{}:license_fee".format(slug)}],
        "ideas_lead": "A venue is one line of the budget. One real find in each of the other categories, each from its own page and dated.",
        "faq": faq,
        "related": [{"path": "courthouse-wedding-" + slug, "label": "Courthouse wedding in " + name,
                     "note": "The official fees and steps, if you want the legal part cheap."},
                    {"path": "micro-wedding-venues", "label": "Micro wedding venues: real prices by city"},
                    {"path": "elopement-packages", "label": "Elopement and micro wedding packages"},
                    {"path": "wedding-dresses-under-500", "label": "Designer wedding dresses, $500 or less"}],
    }
    save(path, page)


def e(x):
    import html as _h
    return _h.escape(str(x), quote=True)


def hub_pages():
    venues = []
    for slug, name in CITIES:
        pg = read_page("small-wedding-venues-" + slug)
        if not pg:
            continue
        for v in sorted((x for x in pg["venues"] if not x.get("per_person")), key=lambda x: x["amount"])[:3]:
            venues.append((slug, name, v))
    if len(venues) < 6:
        return
    faq = faqs_for("micro-wedding-venues")
    if faq:
        by_city = {}
        for slug, name, v in venues:
            by_city.setdefault(name, v)
        cheapest = min(venues, key=lambda t: t[2]["amount"])
        bits = ", ".join("{} from {}".format(n, v["price_display"]) for n, v in by_city.items())
        answer = ("<p>As of {d}, the lowest micro or small wedding venue price we verified is <strong>{p}</strong> ({vn}, {c}). "
                  "By city: {bits}. Every price comes from the venue's own website.</p>").format(
            d=fdate(TODAY), p=cheapest[2]["price_display"], vn=e(cheapest[2]["name"]).replace("&amp;amp;", "&amp;"), c=cheapest[1], bits=bits)
        rows, items = [], []
        for slug, name, v in venues:
            rows.append({
                "th": '<a href="{}" rel="noopener">{}</a><small><a href="@small-wedding-venues-{}/">{}</a></small>'.format(e(v["url"]), e(v["name"]), slug, name),
                "td": '<span class="price">{}</span><span class="was">{} &middot; {}</span><details class="words"><summary>Their exact words</summary><q class="quote">{}</q></details>'.format(
                    e(v["price_display"]), e(v["guests"]), e(v["price_for"]), e(v["quote"])),
                "src": '<a href="{}" rel="noopener">Venue\'s own page</a><br>Read {}'.format(e(v["url"]), fdate(v["date_read"])),
                "amount": v["amount"], "source_url": v["url"], "date_read": v["date_read"]})
            items.append({"name": "{} ({})".format(v["name"], name), "url": v["url"]})
        page = {
            "path": "micro-wedding-venues", "type": "hub", "medium": "hub", "order": 11,
            "title": "Micro Wedding Venues: Real Prices by City (2026)",
            "description": "Micro and small wedding venue prices in 5 US cities, from {} to {}, each quoted from the venue's own site. Checked {}.".format(
                cheapest[2]["price_display"], max(v["price_display"] for _, _, v in venues if v["amount"] == max(x["amount"] for _, _, x in venues)), fdate(TODAY)),
            "h1": "Micro wedding venues: real prices by city", "h1_em": "real prices",
            "eyebrow": "Houston \u00b7 Chicago \u00b7 New York \u00b7 Dallas \u00b7 Los Angeles",
            "refresh_note": "Refreshed monthly.",
            "answer_html": answer,
            "oneliner": "Lowest verified micro wedding venue price {} ({}); three cheapest venues in each of five cities.".format(cheapest[2]["price_display"], cheapest[1]),
            "card_title": "Compare the five cities", "card_line": "Lowest verified price {} ({})".format(cheapest[2]["price_display"], cheapest[1]),
            "facts_heading": "The three cheapest venues in <em>each city</em>",
            "facts_intro": "From each city's venue page, where every venue has its own price, guest count and quote. Open a city for the full list.",
            "table": {"headers": ["Venue", "Price on its own page", "Source"], "rows": rows},
            "items": items,
            "ideas": [{"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:houston.florist"},
                      {"ref": "find:new-york.photographer"}, {"ref": "fact:courthouse-wedding-houston:license_fee"}],
            "ideas_lead": "Whichever city you pick, the rest of the day can cost less too. One real find in each other category, each from its own page and dated.",
            "faq": faq,
            "related": [{"path": "small-wedding-venues-" + s2, "label": "Small and micro wedding venues in " + n2} for s2, n2 in CITIES]
                       + [{"path": "elopement-packages", "label": "Elopement and micro wedding packages"}],
        }
        # rows with amount need source+date at the row level for the price check
        save("micro-wedding-venues", page)
    # packages
    f = ROOT / "research" / "packages.json"
    if not f.exists():
        return
    d = json.loads(f.read_text())
    sys.path.insert(0, str(ROOT / "tools"))
    import display as _d
    pk = []
    for x in d["packages"]:
        x = dict(x)
        for (prov, key), patch in _d.PACKAGES.items():
            nm, _, pl = key.partition("|")
            if x.get("provider") == prov and x["name"].replace("\u201c", '"').replace("\u201d", '"').startswith(nm) and (not pl or pl in (x.get("place") or "")):
                x.update(patch)
                break
        x["price_display"] = money(x["amount"])
        pk.append(x)
    pk.sort(key=lambda x: (bool(x.get("destination")), x["amount"]))
    faq = faqs_for("elopement-packages")
    if not pk or not faq:
        return
    rows, items = [], []
    for x in pk:
        rows.append({
            "th": '<a href="{}" rel="noopener">{}</a><small>{} &middot; {}</small>'.format(e(x["url"]), e(x["name"]), e(x.get("provider") or ""), e(x.get("place") or "")),
            "td": '<span class="price">{}</span><span class="was">{}</span>{}<details class="words"><summary>Their exact words</summary><q class="quote">{}</q></details>'.format(
                e(x["price_display"]), e(x.get("guests") or ""),
                '<span class="was">Includes: {}</span>'.format(e(x["includes"])) if x.get("includes") else "", e(x["quote"])),
            "src": '<a href="{}" rel="noopener">Provider\'s own page</a><br>Read {}'.format(e(x["url"]), fdate(x["date_read"])),
            "amount": x["amount"], "source_url": x["url"], "date_read": x["date_read"]})
        items.append({"name": "{} ({})".format(x["name"], x.get("provider", "")), "url": x["url"]})
    city_pk = [x for x in pk if not x.get("destination")]
    dest = [x for x in pk if x.get("destination")]
    lo, hi = min(city_pk, key=lambda x: x["amount"]), max(city_pk, key=lambda x: x["amount"])
    dest_txt = " Two Las Vegas chapels start lower, from {}.".format(money(min(x["amount"] for x in dest))) if dest else ""
    answer = ("<p>As of {d}, elopement and micro wedding packages in our five cities that print their price run from <strong class=\"big\">{lp}</strong> "
              "({ln}, {lpl}) to <strong>{hp}</strong> ({hn}, {hpl}).{dest} We list {n}, each quoted from the provider's own page.</p>").format(
        d=fdate(TODAY), lp=lo["price_display"], ln=e(lo["name"]), lpl=e(lo.get("place") or ""), hp=hi["price_display"], hn=e(hi["name"]),
        hpl=e(hi.get("place") or ""), dest=dest_txt, n=len(pk))
    save("elopement-packages", {
        "path": "elopement-packages", "type": "packages", "medium": "packages", "order": 12,
        "title": "Elopement & Micro Wedding Packages, Real Prices",
        "description": "{} elopement and micro wedding packages, {} to {}, with what each includes, quoted from the providers' own pages. Checked {}.".format(
            len(pk), money(min(x["amount"] for x in pk)), money(hi["amount"]), fdate(TODAY)),
        "h1": "Elopement & micro wedding packages", "h1_em": "packages",
        "eyebrow": "All-in packages \u00b7 prices from the providers' own pages",
        "refresh_note": "Refreshed monthly.",
        "answer_html": answer,
        "oneliner": "{} packages with printed prices, {} to {} (checked {}).".format(len(pk), lo["price_display"], hi["price_display"], fdate(TODAY)),
        "card_title": "{} packages".format(len(pk)), "card_line": "{} to {}, each from the provider's own page".format(money(lo["amount"]), money(hi["amount"])),
        "facts_heading": "Packages with a <em>printed price</em>, cheapest first",
        "facts_intro": "Only packages whose provider prints the price on its own website. Read what each includes: officiant, photographer, flowers and permits differ.",
        "table": {"headers": ["Package", "Price on its own page", "Source"], "rows": rows},
        "items": items,
        "ideas": [{"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:houston.florist"},
                  {"ref": "find:new-york.photographer"}, {"ref": "fact:courthouse-wedding-houston:license_fee"}],
        "ideas_lead": "A package covers some pieces. One real find in each other category, each from its own page and dated.",
        "faq": faq,
        "related": [{"path": "micro-wedding-venues", "label": "Micro wedding venues: real prices by city"},
                    {"path": "courthouse-wedding-houston", "label": "Courthouse wedding in Houston"},
                    {"path": "wedding-dresses-under-500", "label": "Designer wedding dresses, $500 or less"}],
    })


def read_page(name):
    f = CONTENT / (name + ".json")
    return json.loads(f.read_text()) if f.exists() else None


CITIES = [("houston", "Houston"), ("chicago", "Chicago"), ("new-york", "New York"), ("dallas", "Dallas"), ("los-angeles", "Los Angeles")]


def home_page():
    d5 = read_page("wedding-dresses-under-500")
    n_c = len([1 for sl, _ in CITIES if read_page("courthouse-wedding-" + sl)])
    lics = []
    for slug, name in CITIES:
        c = read_page("courthouse-wedding-" + slug)
        if c:
            lic = next((f for f in c["facts"] if f["key"] == "license_fee"), None)
            if lic and lic.get("amount") is not None:
                lics.append((lic["amount"], name))
    answer = ("<p>Courthouse fees, small venues, designer dresses and elopement packages for 5 US cities, "
              "each from the official or seller's page and dated ({d}). Rachel's List is the free app that finds cheaper dresses, flowers and venues for your style.</p>").format(d=fdate(TODAY))
    page = {
        "path": "", "type": "home", "medium": "hub", "order": 0,
        "title": "Real Wedding Prices, Checked: Rachel's List Guides",
        "description": "Courthouse fees, small wedding venues and designer gowns with real prices, each checked on its source page. Last checked {}.".format(fdate(TODAY)),
        "h1": "Real wedding prices, checked", "h1_em": "checked",
        "eyebrow": "Rachel's List Guides",
        "refresh_note": "Pages refresh weekly, monthly or every 3 months; each shows its own date.",
        "answer_html": answer,
        "oneliner": "Real wedding prices for five US cities, each checked on its source page and dated {}.".format(fdate(TODAY)),
        "ideas": [], "faq": [], "related": [],
        "board_ideas": [{"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:houston.florist"},
                        {"ref": "find:new-york.photographer"}, {"ref": "venue:small-wedding-venues-houston:cheapest10"}],
    }
    fees = []
    for slug, name in CITIES:
        c = read_page("courthouse-wedding-" + slug)
        if c:
            tot = sum(f["amount"] for f in c["facts"] if f.get("allin") and f.get("amount") is not None)
            if tot:
                fees.append(tot)
    ten = []
    for slug, name in CITIES:
        v = read_page("small-wedding-venues-" + slug)
        if v:
            ten += [x["amount"] for x in v["venues"] if x.get("max_guests", 0) >= 10 and not x.get("per_person")]
    chips = []
    if fees:
        chips.append({"target": "courthouse", "label": "Courthouse fees from", "value": money(min(fees))})
    if ten:
        chips.append({"target": "venues", "label": "Venues seating 10+ from", "value": money(min(ten))})
    if d5:
        chips.append({"target": "dresses", "label": "Dresses from", "value": money(min(g["price"] for g in d5["gowns"]))})
    pkj = ROOT / "research" / "packages.json"
    if pkj.exists():
        chips.append({"target": "packages", "label": "Packages from", "value": money(min(x["amount"] for x in json.loads(pkj.read_text())["packages"] if "Las Vegas" not in (x.get("place") or "")))})
    page["chips"] = chips
    save("home", page)


if __name__ == "__main__":
    CONTENT.mkdir(exist_ok=True)
    dress_pages()
    trust_page()
    finds_file()
    for _slug, _name in CITIES:
        courthouse_page(_slug, _name)
        venue_page(_slug, _name)
    hub_pages()
    home_page()
