#!/bin/sh
# Phone (390) screens + full page, desktop (1440) screens, and the sideways-overflow check at 320 / 430.
# Usage: tools/shoot_all.sh <slug> <outdir> <prefix>      (needs: cd docs && python3 -m http.server 8777)
slug="$1"; out="$2"; pre="$3"; url="http://localhost:8777/$slug"
D="$(cd "$(dirname "$0")" && pwd)"
perl -e 'alarm shift; exec @ARGV' 120 node "$D/cdp_shot.js" "$url" "$out" "$pre-390" --w 390
perl -e 'alarm shift; exec @ARGV' 120 node "$D/cdp_shot.js" "$url" "$out" "$pre-1440" --w 1440 --h 900 --screens 3 --tile 2400
for w in 320 430; do perl -e 'alarm shift; exec @ARGV' 120 node "$D/cdp_shot.js" "$url" /tmp/rl-ov "$pre-$w" --w $w --screens 0 --tile 99999 | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print('overflow',d['w'],d['overflow'],d['offenders'])"; done
