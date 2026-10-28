#!/usr/bin/env python3
"""The visible text of a built page, one block per line (for reviewers).  Usage: python3 -I tools/page_text.py <slug or ''>"""
import html, re, sys
from pathlib import Path
slug = sys.argv[1].strip("/") if len(sys.argv) > 1 else ""
p = Path(__file__).resolve().parent.parent / "docs" / slug / "index.html"
h = p.read_text(encoding="utf-8")
h = re.sub(r"(?is)<(script|style|svg|head)\b.*?</\1>", " ", h)
h = re.sub(r"(?i)</?(p|div|li|h[1-6]|section|article|tr|ul|ol|header|footer|aside|figure|details|summary|button|a)\b[^>]*>", "\n", h)
h = re.sub(r"<[^>]+>", "", h)
for line in html.unescape(h).splitlines():
    line = re.sub(r"\s+", " ", line).strip()
    if line:
        print(line)
