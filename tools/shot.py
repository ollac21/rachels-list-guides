#!/usr/bin/env python3
"""Phone-width screenshot of a built page through headless Chrome.
Headless Chrome will not open a window narrower than ~500 px, so the page is shown in a 390 px iframe.
Usage: python3 -I tools/shot.py <path-on-site e.g. wedding-dresses-under-500/> <out.png> [height]
Needs a local server on :8777 serving docs/  (cd docs && python3 -m http.server 8777)."""
import subprocess, sys, tempfile, os
path, out = sys.argv[1], sys.argv[2]
h = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
d = tempfile.mkdtemp()
f = os.path.join(d, "frame.html")
open(f, "w").write('<!doctype html><body style="margin:0;background:#888"><iframe src="http://localhost:8777/%s" width="390" height="%d" style="border:0;display:block;margin:0"></iframe></body>' % (path, h))
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--window-size=500,%d" % h, "--virtual-time-budget=8000", "--screenshot=" + out, "file://" + f],
               stderr=subprocess.DEVNULL, timeout=90)
subprocess.run(["sips", "-c", str(h), "390", "--cropOffset", "0", "0", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(out)
