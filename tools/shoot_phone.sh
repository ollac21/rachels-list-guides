#!/bin/sh
# Phone-only screens + tiles + page text, for reviewers.  Usage: tools/shoot_phone.sh <slug or ""> <outdir> <prefix>
D="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$2"
perl -e 'alarm shift; exec @ARGV' 120 node "$D/cdp_shot.js" "http://localhost:8777/$1" "$2" "$3" --w 390 --screens 4 --tile 1300 | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print(d['url'],'overflow' if d['overflow'] else 'ok',d['height'],len(d['tiles']),'tiles')"
python3 -I "$D/page_text.py" "$1" > "$2/$3-text.txt"
