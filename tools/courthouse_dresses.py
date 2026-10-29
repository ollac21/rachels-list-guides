#!/usr/bin/env python3
"""Courthouse dresses: short, midi, slip or simple white dresses under $250, from the app's weekly finds file.

Source: gs://rachels-list-app-pool/pool/latest.json (the `finds` list). The picks below were chosen by reading the
titles (US, a Poshmark listing, price at most $250, white / ivory / cream, short, midi, slip or simple) and spread over four
size bands (each pick was also looked at: a simple white or ivory short, midi or sheath dress that suits a courthouse) so a bride can filter to hers. Every pick is RE-OPENED on Poshmark: it must still be available at the
same price, or it is dropped and printed. A listing with no printed original price shows no "was".
Run:  python3 -I tools/courthouse_dresses.py <pool.json>   -> content/_courthouse_dresses.json
"""
import datetime, json, sys, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from dresses import reopen  # noqa: E402

# pool id -> (size band, short name, one-phrase style read from the title)
PICKS = [
    ("553d473b6adf4c35", "2-4", "Two Sisters", "lace mini"),
    ("4255c2e22c409dcd", "2-4", "Few Moda", "top and skirt set"),
    ("6f341754d445e495", "2-4", "White satin mini", "satin mini"),
    ("ca75182260e0f8f5", "2-4", "Tadashi Shoji", "beaded lace cocktail"),
    ("8ca2dcd52e7d0148", "6-8", "Eliza J", "lace dress"),
    ("07930663af342bfc", "6-8", "Rachel Allan", "fit-and-flare mini"),
    ("795ef496f2cf40be", "6-8", "Angel Biba", "crochet handkerchief hem"),
    ("089c100b836ece7d", "6-8", "Reformation", "cream tie-strap maxi"),
    ("95aa7abfd8282ab4", "10-12", "The Limited", "sleeveless dress"),
    ("6b779d8b4a9b928d", "10-12", "Marina", "long-sleeve gown"),
    ("afcb293a6d7e6b67", "10-12", "Jenny Yoo", "one-shoulder gown"),
    ("c48fe95a5748504d", "10-12", "White maxi dress", "maxi"),
    ("ad7547ca9213fa41", "14+", "Merry's", "satin off-the-shoulder"),
    ("b161c22da1d1e4a0", "14+", "Azazie", "satin mini"),
    ("f2ddf004c892dd93", "14+", "David's Bridal", "lace midi"),
    ("5383ac670c49511b", "14+", "Adrianna Papell", "sheath"),
    ("367af18c872d8ed3", "14+", "Jessica London", "lace tea-length"),
]


def main():
    pool = json.load(open(sys.argv[1]))
    by_id = {x["id"]: x for x in pool["finds"]}
    today = datetime.date.today().isoformat()
    out, dropped = [], []
    for pid, band, name, style in PICKS:
        x = by_id.get(pid)
        if not x:
            dropped.append({"id": pid, "why": "not in the pool"})
            continue
        try:
            live = reopen(x["url"])
        except Exception as e:  # a listing we cannot open is not shown
            live = {"available": False, "state": "error:%s" % e, "price": None, "original": None}
        ok = live["available"] and live["price"] == float(x["price"]) and x["country"] in ("US", "US+CA") and x["price"] <= 250
        print(("KEEP " if ok else "DROP "), band, x["price"], x.get("old_price"), x["size"], name, live["state"], live["price"], live["original"], flush=True)
        if not ok:
            dropped.append({"id": pid, "name": name, "live": live})
            continue
        was = live["original"] if live["original"] and live["original"] > live["price"] else None
        out.append({"id": pid, "band": band, "name": name, "style": style, "size": x["size"].replace("US ", ""), "price": live["price"],
                    "old_price": was, "url": x["url"], "source": "Poshmark", "date_read": today})
        time.sleep(0.8)
    json.dump({"date_read": today, "pool_week": pool.get("week"), "dresses": out, "dropped": dropped},
              open(__file__.rsplit("/", 2)[0] + "/content/_courthouse_dresses.json", "w"), indent=1, ensure_ascii=False)
    print(len(out), "kept;", len(dropped), "dropped")


if __name__ == "__main__":
    main()
