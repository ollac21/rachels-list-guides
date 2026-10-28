#!/usr/bin/env python3
"""Read the MAIN listing out of a Poshmark page (the first record around "price_amount"), for hand-picking finds.
Usage: python3 -I tools/posh_probe.py <listing-url> ...   (prints title, size, price, original, availability, colors, length words)"""
import json, re, sys, time, urllib.request, html as H

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def probe(url):
    h = fetch(url)
    i = h.find('"price_amount"')
    seg = h[max(0, i - 6000):i + 900]
    title = re.search(r'<title>(?:[^|]*\|)\s*(?:[^|]*\|)\s*([^|]*)\|', h)
    av = re.search(r'"availability":"([a-z_]+)"', h)
    price = re.search(r'"price_amount":\{"val":"([\d.]+)"', h)
    orig = re.search(r'"original_price_amount":\{"val":"([\d.]+)"', h)
    size = re.search(r'"size":"([^"]*)"', seg[seg.find('"price_amount"'):])
    brand = re.search(r'"brand":"([^"]*)"', seg[seg.find('"price_amount"'):])
    cols = re.findall(r'"colors":\[\{"name":"([^"]+)"', seg)
    desc = re.search(r'"description":"(.*?)","price_amount"', seg, re.S)
    d = json.loads('"' + desc.group(1) + '"') if desc else ""
    ln = re.findall(r'(?i)(?:length|hem|tea[- ]length|mini|midi|maxi|knee|floor)[^.\n]{0,40}', d)
    return {"url": url, "title": H.unescape(title.group(1).strip()) if title else None, "available": av.group(1) if av else None,
            "price": float(price.group(1)) if price else None, "original": float(orig.group(1)) if orig else None,
            "size": size.group(1) if size else None, "brand": brand.group(1) if brand else None, "colors": cols[:2], "length_words": ln[:3], "desc": d[:260].replace("\n", " ")}


if __name__ == "__main__":
    for u in sys.argv[1:]:
        try:
            print(json.dumps(probe(u), ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"url": u, "error": str(e)}))
        time.sleep(0.8)
