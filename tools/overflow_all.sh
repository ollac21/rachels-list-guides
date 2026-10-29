#!/bin/sh
# Sideways-scroll check on every page at 320 / 390 / 430 px.  Needs: cd docs && python3 -m http.server 8777
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D/../docs"
bad=0
for p in $(find . -name index.html | sed 's#^\./##; s#index.html$##' | sort); do
  for w in 320 390 430; do
    r=$(perl -e 'alarm shift; exec @ARGV' 60 node "$D/cdp_shot.js" "http://localhost:8777/$p" /tmp/rl-ov x --w $w --noshots | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print('BAD' if d['overflow'] else 'ok', d['scrollWidth'], d['offenders'][:3])")
    case "$r" in BAD*) echo "$p $w $r"; bad=1;; esac
  done
done
[ $bad = 0 ] && echo "no sideways scroll on any page at 320 / 390 / 430"
