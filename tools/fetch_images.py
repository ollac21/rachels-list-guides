#!/usr/bin/env python3
"""Find each item's own photo, so the pages can load it straight from the seller's or venue's server (never re-hosted).

    python3 -I tools/fetch_images.py [pool.json]        -> content/_images.json   (listing URL -> image URL)

- A dress or gown: the pool's `image_url` (gs://rachels-list-app-pool/pool/latest.json, `finds`, matched by listing URL),
  or, when the pool has none, the listing's own `og:image`.
- A venue, florist, photographer or package: its page's `og:image` (or `twitter:image`).
- Each image URL is opened once (status 200, an image content type); one that fails is left out and the page shows its text card.
Entries already in the file are kept unless --refresh is given."""
import concurrent.futures as cf, datetime, html, json, re, sys, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
OUT = ROOT / "content" / "_images.json"


def get(url, rng=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
    if rng:
        h["Range"] = rng
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers, r.read()


def og_image(page_url):
    try:
        st, hd, body = get(page_url, timeout=25)
    except Exception as e:
        return None, "page: %s" % str(e)[:60]
    t = body[:600000].decode("utf-8", "replace")
    for pat in (r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]*content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']',
                r'<meta[^>]+(?:property|name)=["\']twitter:image(?::src)?["\'][^>]*content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']twitter:image["\']'):
        m = re.search(pat, t, re.I)
        if m:
            u = urllib.parse.urljoin(page_url, html.unescape(m.group(1)).strip())
            if u.startswith("http"):
                return u, "ok"
    return None, "no og:image"


def works(img_url):
    """The image answers 200 with an image type; returns (ok, bytes or None)."""
    try:
        st, hd, body = get(img_url, rng="bytes=0-2047", timeout=20)
        ct = (hd.get("Content-Type") or "").lower()
        total = None
        cr = hd.get("Content-Range") or ""
        m = re.search(r"/(\d+)$", cr)
        if m:
            total = int(m.group(1))
        elif hd.get("Content-Length") and st == 200:
            total = int(hd["Content-Length"])
        return (ct.startswith("image/") or body[:3] == b"\xff\xd8\xff" or body[:4] == b"\x89PNG" or body[:4] == b"RIFF"), total
    except Exception:
        return False, None


def targets():
    """(listing url, kind) for every item the pages show with a photo."""
    t = {}
    for f in sorted((ROOT / "content").glob("*.json")):
        if f.name.startswith("_"):
            continue
        p = json.loads(f.read_text())
        for g in p.get("gowns", []):
            t[g["url"]] = "poshmark"
        for v in p.get("venues", []):
            t[v["url"]] = "page"
        for c in p.get("cards", []):
            t[c["url"]] = "page"
    for d in json.loads((ROOT / "content" / "_courthouse_dresses.json").read_text())["dresses"]:
        t[d["url"]] = "poshmark"
    finds = json.loads((ROOT / "content" / "_finds.json").read_text())
    for city in finds.values():
        for k in ("florist", "photographer", "bouquet", "lunch"):
            if city.get(k) and city[k].get("url"):
                t[city[k]["url"]] = "page"
    ff = ROOT / "research" / "flow-finds.json"
    if ff.exists():
        for city in json.loads(ff.read_text())["cities"].values():
            for k in ("bouquet", "lunch"):
                if city.get(k) and city[k].get("url") and not city[k]["url"].lower().split("?")[0].endswith(".pdf"):
                    t[city[k]["url"]] = "page"
    return t


def one(args):
    url, kind, pool_img = args
    src, how, note = None, None, ""
    if pool_img:
        src, how = pool_img, "pool"
    else:
        src, note = og_image(url)
        how = "og"
    if not src:
        return url, {"src": None, "how": how, "why": note, "checked": datetime.date.today().isoformat()}
    ok, size = works(src)
    if not ok and how == "pool":
        src2, note = og_image(url)
        if src2:
            ok2, size2 = works(src2)
            if ok2:
                return url, {"src": src2, "how": "og", "bytes": size2, "checked": datetime.date.today().isoformat()}
    return url, ({"src": src, "how": how, "bytes": size, "checked": datetime.date.today().isoformat()} if ok
                 else {"src": None, "how": how, "why": "image does not load", "tried": src, "checked": datetime.date.today().isoformat()})


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refresh = "--refresh" in sys.argv
    pool_by_url = {}
    if args:
        for x in json.load(open(args[0]))["finds"]:
            pool_by_url[x["url"]] = x.get("image_url")
    have = json.loads(OUT.read_text()) if OUT.exists() and not refresh else {}
    tg = targets()
    todo = [(u, k, pool_by_url.get(u)) for u, k in sorted(tg.items()) if u not in have or (have[u].get("src") is None and "429" in str(have[u].get("why", "")))]
    print("%d targets, %d to fetch" % (len(tg), len(todo)), flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for url, rec in ex.map(one, todo):
            have[url] = rec
            print(("OK   " if rec["src"] else "MISS "), (rec.get("bytes") or 0) // 1024, "KB", url[:70], rec.get("why", ""), flush=True)
    OUT.write_text(json.dumps(dict(sorted(have.items())), indent=1, ensure_ascii=False))
    print("%d with a photo, %d without" % (sum(1 for r in have.values() if r["src"]), sum(1 for r in have.values() if not r["src"])))


if __name__ == "__main__":
    main()
