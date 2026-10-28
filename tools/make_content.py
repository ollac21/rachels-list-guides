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
TODAY = "2026-10-28"


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
    d = json.loads((CACHE / "dresses.json").read_text())
    specs = [
        ("wedding-dresses-under-500", "under500", 500, "Designer Wedding Dresses Under $500 (This Week)",
         "Designer Wedding Dresses Under $500", "Under $500", 13),
        ("wedding-dresses-under-1000", "under1000", 1000, "Designer Wedding Dresses Under $1,000 (This Week)",
         "Designer Wedding Dresses Under $1,000", "Under $1,000", 14),
    ]
    for path, band, cap, title, h1, em, order in specs:
        gowns = d[band]
        if not gowns:
            continue
        n = len(gowns)
        cheapest = min(gowns, key=lambda g: g["price"])
        big = max(gowns, key=lambda g: g["old_price"] - g["price"])
        lo = "$500 or less" if cap == 500 else "$1,000 or less"
        band_txt = "$500 or less" if cap == 500 else "more than $500 and up to $1,000"
        other = "wedding-dresses-under-1000" if cap == 500 else "wedding-dresses-under-500"
        answer = (
            "<p>As of {date}, we found <strong>{n} secondhand designer wedding gowns</strong> listed at {lo} on Poshmark, "
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
                  "We cannot check what a gown cost new, so we never call it a retail price."},
            {"q": "How often is this list updated?",
             "a": "Every Tuesday. We re-open each gown, drop the ones that are sold or repriced, and change the date at the top. "
                  "The list you see was last checked on {date}.".format(date=fdate(TODAY))},
        ]
        page = {
            "path": path, "type": "dresses", "medium": "dresses", "order": order,
            "title": title,
            "description": "{n} secondhand designer wedding gowns at {lo}, each re-opened {d}. Price now, seller's original, size and link.".format(
                n=n, lo=band_txt.replace("more than $500 and up to $1,000", "$501 to $1,000"), d=fdate(TODAY)),
            "h1": h1, "h1_em": em,
            "eyebrow": "Secondhand designer gowns &middot; Poshmark &middot; updated every Tuesday".replace("&middot;", "·"),
            "refresh_note": "Refreshed every Tuesday.",
            "answer_html": answer, "oneliner": oneliner,
            "facts_heading": "This week's <em>gowns</em>",
            "facts_intro": "Biggest gap between price now and seller's original first. Prices are the listing prices on the day we read them; shipping and tax are not included.",
            "gowns": gowns,
            "ideas": [
                {"ref": "find:houston.florist"}, {"ref": "find:houston.photographer"},
                {"ref": "venue:small-wedding-venues-houston:cheapest10"},
                {"ref": "fact:courthouse-wedding-houston:license_fee"},
            ],
            "ideas_lead": "A dress is one line of the budget. Here is one real find in each of the other categories, from Houston, each from its own page and dated.",
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


def read_page(name):
    f = CONTENT / (name + ".json")
    return json.loads(f.read_text()) if f.exists() else None


CITIES = [("houston", "Houston"), ("chicago", "Chicago"), ("new-york", "New York"), ("dallas", "Dallas"), ("los-angeles", "Los Angeles")]


def home_page():
    rows, facts_lines = [], []
    lics = []
    cheapest = []
    for slug, name in CITIES:
        c = read_page("courthouse-wedding-" + slug)
        v = read_page("small-wedding-venues-" + slug)
        parts_td, parts_src = [], []
        if c:
            lic = next((f for f in c["facts"] if f["key"] == "license_fee"), None)
            cer = next((f for f in c["facts"] if f["key"] == "ceremony_fee"), None)
            if lic:
                lics.append((lic["amount"], name))
                parts_td.append('Marriage license <strong>{}</strong>'.format(lic["display"]))
            if cer:
                parts_td.append('courthouse ceremony <strong>{}</strong>'.format(cer["display"]))
            parts_src.append('<a href="@courthouse-wedding-{}/">Courthouse page</a>'.format(slug))
        if v and v.get("venues"):
            vv = min(v["venues"], key=lambda x: x["amount"])
            cheapest.append((vv["amount"], vv["name"], name))
            parts_td.append('cheapest small-venue price we verified <strong>{}</strong> ({})'.format(vv["price_display"], vv["name"].replace("&", "&amp;")))
            parts_src.append('<a href="@small-wedding-venues-{}/">Venue page</a>'.format(slug))
        if parts_td:
            rows.append({"th": '<a href="@courthouse-wedding-{0}/">{1}</a>'.format(slug, name) if c else name,
                         "td": "; ".join(parts_td) + ".", "src": "<br>".join(parts_src)})
    d5 = read_page("wedding-dresses-under-500")
    bits = []
    if lics:
        lo, hi = min(lics), max(lics)
        bits.append("a marriage license costs from <strong>{}</strong> in {} to <strong>{}</strong> in {}".format(money(lo[0]), lo[1], money(hi[0]), hi[1]))
    if cheapest:
        c0 = min(cheapest)
        bits.append("the cheapest small-venue price we verified is <strong>{}</strong> ({}, {})".format(money(c0[0]), c0[1].replace("&", "&amp;"), c0[2]))
    if d5:
        bits.append("{} secondhand designer gowns are <strong>$500 or less</strong>".format(len(d5["gowns"])))
    answer = "<p>As of {d}: {b}. Every number links to the page it came from and shows the day we read it.</p>".format(
        d=fdate(TODAY), b="; ".join(bits))
    one = "Real wedding prices for five US cities, each checked on its source page and dated {}.".format(fdate(TODAY))
    page = {
        "path": "", "type": "home", "medium": "hub", "order": 0,
        "title": "Real Wedding Prices, Checked: Rachel's List Guides",
        "description": "Courthouse fees, small wedding venues and designer gowns with real prices, each checked on its source page. Last checked {}.".format(fdate(TODAY)),
        "h1": "Real wedding prices, checked", "h1_em": "checked",
        "eyebrow": "Rachel's List Guides",
        "refresh_note": "Pages refresh weekly, monthly or every 3 months; each shows its own date.",
        "answer_html": answer, "oneliner": one,
        "facts_heading": "Five cities, <em>at a glance</em>",
        "facts_intro": "The official license fee and the cheapest small-venue price we could verify on a venue's own site. Open a city for every row, quote and date.",
        "table": {"headers": ["City", "What we found", "Pages"], "rows": rows} if rows else None,
        "ideas": [
            {"ref": "gown:wedding-dresses-under-500:brand=BHLDN"}, {"ref": "find:houston.florist"},
            {"ref": "find:houston.photographer"}, {"ref": "venue:small-wedding-venues-houston:cheapest10"},
        ],
        "ideas_lead": "Whatever the venue, the rest of the day can cost less too. One real find in each category, from its own page and dated.",
        "faq": [
            {"q": "How much does a small wedding cost?",
             "a": "It depends on the city and the venue, so we do not quote an average. Open a city page to see the actual fees and the small-venue prices we verified on venues' own websites."},
            {"q": "Are courthouse weddings cheaper than a venue?",
             "a": "The official fees are listed on each courthouse page with the county's own wording. Compare them with the venue prices on the same city's venue page: both show the day we read them."},
            {"q": "Can I really find a designer wedding dress for under $500?",
             "a": "Yes: we re-open secondhand designer listings every Tuesday and show only the ones still available. See the dress pages for this week's gowns and their sellers' original prices."},
            {"q": "Who writes these guides?",
             "a": "Rachel's List, a free wedding-planning app that finds dresses, decor and venues for less. We earn nothing from the venues, sellers or photographers listed."},
            {"q": "How do you check a price?",
             "a": "Official pages are quoted word for word, venue prices come from the venue's own site, and dress listings are re-opened before they appear. <a href=\"@how-we-check/\">Read how we check</a>."},
        ],
        "related": [],
    }
    save("home", page)


if __name__ == "__main__":
    CONTENT.mkdir(exist_ok=True)
    dress_pages()
    trust_page()
    home_page()
