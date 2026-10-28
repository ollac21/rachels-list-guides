#!/usr/bin/env python3
"""Pick and re-open the week's secondhand designer wedding gowns.

Source: the app's weekly finds file (gs://rachels-list-app-pool/pool/latest.json).
Rules (GUIDES-SPEC): category wedding_dress, country US, a printed old price,
a bridal brand named in the title, biggest gap first. Every listing is then
RE-OPENED on Poshmark: it must still be available and the price must match.
Run:  python3 -I tools/dresses.py pool.json   -> content/_dresses.json
"""
import json, re, sys, time, urllib.request, datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# A brand counts only when it is a bridal label named in the listing title.
BRANDS = [
    ("Maggie Sottero", r"maggie sottero"), ("Martina Liana", r"martina liana"),
    ("Hayley Paige", r"hayley paige"), ("Demetrios", r"demetrios"),
    ("Calla Blanche", r"calla blanche"), ("Mikaella", r"mikaella"),
    ("Pronovias", r"pronovias"), ("Vera Wang", r"vera wang"),
    ("Sophia Tolli", r"sophia tolli"), ("DaVinci Bridal", r"davinci bridal"),
    ("Madi Lane", r"madi lane"), ("Oleg Cassini", r"oleg cassini"),
    ("Noel and Jean by Katie May", r"noel and jean by katie may"),
    ("Justin Alexander", r"justin alexander"), ("Jenny Yoo", r"jenny (by jenny )?yoo"),
    ("Casablanca Bridal", r"casablanca bridal"), ("David's Bridal", r"david[’']?s bridal|david bridal"),
    ("Galina Signature", r"galina"), ("BHLDN", r"bhldn|bhdln"),
    ("Tadashi Shoji", r"tadashi shoji"), ("Nadine Merabi", r"nadine merabi"),
    ("Amur", r"\bamur\b"), ("Azazie", r"azazie"), ("Mori Lee", r"mori lee"),
    ("Alfred Angelo", r"alfred angelo"), ("Rivini", r"rita vinieris"),
    ("Nox Anabel", r"nox anabel"), ("Ronald Joyce", r"ronald joyce"),
    ("Adrianna Papell", r"adrianna papell"), ("Birdy Grey", r"birdy"),
]


def brand_of(title):
    t = title.lower()
    for name, rx in BRANDS:
        if re.search(rx, t):
            return name
    return None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def reopen(url):
    """Return dict(available, price, original) read from the live listing."""
    html = fetch(url)
    avail = re.search(r'"availability":"(available|sold_out|not_for_sale|[a-z_]+)"', html)
    price = re.search(r'"price_amount":\{"val":"([\d.]+)"', html)
    orig = re.search(r'"original_price_amount":\{"val":"([\d.]+)"', html)
    return {
        "available": bool(avail and avail.group(1) == "available"),
        "state": avail.group(1) if avail else None,
        "price": float(price.group(1)) if price else None,
        "original": float(orig.group(1)) if orig else None,
    }


def main():
    pool = json.load(open(sys.argv[1]))
    today = datetime.date.today().isoformat()
    cands = []
    seen = set()
    for x in pool["finds"]:
        if x.get("category") != "wedding_dress" or x.get("country") != "US":
            continue
        if not x.get("old_price") or x["old_price"] <= x["price"] or x["price"] > 1000:
            continue
        b = brand_of(x["title"])
        if not b or x["url"] in seen:
            continue
        seen.add(x["url"])
        x["brand_name"] = b
        cands.append(x)
    cands.sort(key=lambda x: -(x["old_price"] - x["price"]))
    out = {"under500": [], "under1000": [], "dropped": [], "date_read": today}
    for x in cands:
        band = "under500" if x["price"] <= 500 else "under1000"
        if len(out[band]) >= 20:
            continue
        live = None
        for attempt in range(3):
            try:
                live = reopen(x["url"])
                break
            except Exception as e:  # network trouble is not a reason to keep a listing
                live = {"available": False, "state": "error:%s" % e, "price": None, "original": None}
                time.sleep(2)
        ok = live["available"] and live["price"] == float(x["price"]) \
            and live["original"] == float(x["old_price"])
        print(("KEEP " if ok else "DROP "), band, x["price"], x["old_price"], x["brand_name"], live["state"], live["price"], live["original"], flush=True)
        rec = {k: x[k] for k in ("title", "url", "price", "old_price", "size")}
        rec["brand"] = x["brand_name"]
        rec["date_read"] = today
        if ok:
            out[band].append(rec)
        else:
            rec["live"] = live
            out["dropped"].append(rec)
        time.sleep(0.8)
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print(len(out["under500"]), "under500;", len(out["under1000"]), "under1000;", len(out["dropped"]), "dropped")


if __name__ == "__main__":
    main()
