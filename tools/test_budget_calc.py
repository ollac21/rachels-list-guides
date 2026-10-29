#!/usr/bin/env python3
"""The wedding budget calculator's math, checked in Python and in the page's own JS (through node).
Run after `python3 build.py`:  python3 tools/test_budget_calc.py
Checks: the split adds back to the budget exactly ($36,000, $15,000, $5,000 and a few odd ones); the JS split() in the built page
gives the same dollars row by row as the Python static table; the plan's hand-checked numbers; the gown counts; the static page."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

PAGE = json.loads((ROOT / "content" / "wedding-budget-calculator.json").read_text(encoding="utf-8"))
ITEMS = PAGE["calc"]["items"]
AVGS = [i["zola_avg"] for i in ITEMS]
KEYS = [i["key"] for i in ITEMS]
HTML = (ROOT / "docs" / "wedding-budget-calculator" / "index.html").read_text(encoding="utf-8")
fails = []


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


ok(sum(AVGS) == 46893, "the 15 Zola averages add up to $46,893 (got {:,})".format(sum(AVGS)))

# 1. Python: the split adds back exactly; every line but the last is within 50 cents of its exact share
BUDGETS = [36000, 15000, 5000, 10000, 1, 999, 123457, 10000000]
for b in BUDGETS:
    s = build.budget_split(b, AVGS)
    exact = [b * a / sum(AVGS) for a in AVGS]
    ok(sum(s) == b, "Python split of ${:,} adds up to ${:,}".format(b, sum(s)))
    ok(all(abs(x - e) <= 0.5 for x, e in zip(s[:-1], exact[:-1])) and abs(s[-1] - exact[-1]) <= 7.5,
       "Python split of ${:,}: lines 1-14 within $0.50, the last within $7.50 of exact (last off by ${:.2f})".format(b, s[-1] - exact[-1]))

# 2. The page's own JS split() (between /*split*/ markers) gives the same dollars, row by row
m = re.search(r"/\*split\*/(.*?)/\*/split\*/", HTML, re.S)
ok(bool(m), "the built page carries the JS split() between its markers")
if m:
    js = m.group(1) + "\nconsole.log(JSON.stringify({}.map(function(b){{return split(b,{})}})));".format(json.dumps(BUDGETS), json.dumps(AVGS))
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    res = json.loads(out.stdout) if out.returncode == 0 else None
    ok(res is not None, "node ran the page's split() ({})".format(out.stderr.strip()[:80] or "ok"))
    for b, r in zip(BUDGETS, res or []):
        ok(r == build.budget_split(b, AVGS) and sum(r) == b, "JS split of ${:,} = Python split, adds up to ${:,}".format(b, sum(r)))


# 3. The plan's hand-checked numbers (per guest and food + drink use the same half-up rounding as the page)
def worked(b, g):
    a = dict(zip(KEYS, build.budget_split(b, AVGS)))
    return a, int(b / g + 0.5), int((a["catering"] + a["bar"]) / g + 0.5)


a, pg, fd = worked(36000, 145)
ok((a["venue"], a["dress"], pg, fd) == (6582, 1535, 248, 66), "$36,000 / 145 guests: venue $6,582, dress $1,535, $248 a guest, food + drink $66 a guest (got {}, {}, {}, {})".format(a["venue"], a["dress"], pg, fd))
a, pg, fd = worked(15000, 50)
ok((a["venue"], a["dress"], pg, fd) == (2742, 640, 300, 80), "$15,000 / 50 guests: venue $2,742, dress $640, $300 a guest, food + drink $80 a guest (got {}, {}, {}, {})".format(a["venue"], a["dress"], pg, fd))
a, _, _ = worked(10000, 50)
ok((a["venue"], a["catering"], a["dress"]) == (1828, 1477, 427), "$10,000 (FAQ 1): venue $1,828, catering $1,477, dress $427 (got {}, {}, {})".format(a["venue"], a["catering"], a["dress"]))

# 4. Gown counts from the dress pages (the data blob the JS reads)
blob = json.loads(re.search(r'<script type="application/json" id="b-data">(.*?)</script>', HTML, re.S).group(1))
gowns = [g[0] for g in blob["gowns"]]
ok(gowns == sorted(gowns) and len(gowns) == 30, "30 gown prices in the blob, cheapest first (got {})".format(len(gowns)))
ok(sum(1 for p in gowns if p <= 1535) == 30 and sum(1 for p in gowns if p <= 640) == 19, "gowns at or under the dress line: 30 at $1,535, 19 at $640")

# 5. The static page (no JS) shows the $36,000 split the answer quotes
ans = re.search(r"<!--answer-->(.*?)<!--/answer-->", HTML, re.S).group(1)
ok("$6,582" in ans and "$1,535" in ans and "$36,000" in ans, "the answer quotes $36,000, $6,582 and $1,535")
ok('data-amt="venue">$6,582<' in HTML and 'data-amt="dress">$1,535<' in HTML and 'id="b-total">$36,000<' in HTML, "the static table prints venue $6,582, dress $1,535, total $36,000")
ok("30 real gowns" in HTML and "Show me dresses under $1,535" in HTML, "the static dress line counts 30 gowns and the button reads 'Show me dresses under $1,535'")
ok("Per guest: <b>$248</b>" in HTML and "<b>$66</b>" in HTML, "the static per-guest line: $248, food and drink $66")
ok("{{" not in HTML, "no unfilled {{placeholder}}")

print("\n{} failed".format(len(fails)) if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
