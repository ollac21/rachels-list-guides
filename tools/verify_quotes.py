#!/usr/bin/env python3
"""Check that every research quote really appears on the page it cites.

Walks a research JSON, finds every dict that has both "quote" and "source_url"
(or "url"), fetches the page with curl-like headers, strips tags and compares the
quote with whitespace and curly quotes normalised. Prints OK / MISSING per quote.
Usage: python3 -I tools/verify_quotes.py .cache/research/houston.json
"""
import json, re, sys, html, urllib.request, subprocess, hashlib, os

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache", "pages")


def norm(s):
    s = html.unescape(s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def page_text(url):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".txt")
    if os.path.exists(f):
        return open(f, encoding="utf-8").read()
    raw = None
    if url.lower().split("?")[0].endswith(".pdf"):
        p = subprocess.run(["curl", "-sL", "-A", UA, "-m", "90", "--retry", "2", url, "-o", f + ".pdf"])
        t = subprocess.run(["pdftotext", "-layout", f + ".pdf", "-"], capture_output=True, text=True)
        text = t.stdout
    else:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode("utf-8", "replace")
        except Exception:  # some sites stall Python's client but answer curl
            raw = subprocess.run(["curl", "-sL", "-m", "60", "--retry", "1", "-A", UA, url], capture_output=True).stdout.decode("utf-8", "replace")
        raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
        # keep JSON-LD text out, keep everything else visible
        text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = norm(text)
    if text:  # never cache an empty page (a failed download must be retried)
        open(f, "w", encoding="utf-8").write(text)
    return text


def walk(o, out):
    if isinstance(o, dict):
        q = o.get("quote")
        u = o.get("source_url") or o.get("url")
        if isinstance(q, str) and q and u:
            out.append((q, u, o))
        for v in o.values():
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)


def main():
    bad = 0
    for path in sys.argv[1:]:
        data = json.load(open(path))
        items = []
        walk(data, items)
        for q, u, o in items:
            try:
                t = page_text(u)
            except Exception as e:
                print("FETCHFAIL", u, str(e)[:60]); bad += 1; continue
            if norm(q) in t:
                print("OK      ", u[:80], "|", q[:60])
            else:
                print("MISSING ", u[:80], "|", q[:80]); bad += 1
    print("problems:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
