#!/bin/sh
# One representative page per page type: phone (390) screens + full page, desktop (1440) screens, the page text, the sideways-overflow check.
# Usage: tools/shoot_conv.sh <round> [type ...]      types: courthouse venues hub packages dresses home   (needs: cd docs && python3 -m http.server 8777)
D="$(cd "$(dirname "$0")/.." && pwd)"; R="$1"; shift
[ $# -eq 0 ] && set -- courthouse venues hub packages dresses home
for T in "$@"; do
  case $T in
    courthouse) S=courthouse-wedding-chicago/; P=chi;;
    venues) S=small-wedding-venues-houston/; P=hou;;
    hub) S=micro-wedding-venues/; P=hub;;
    packages) S=elopement-packages/; P=pkg;;
    dresses) S=wedding-dresses-under-500/; P=dre;;
    home) S=""; P=home;;
  esac
  O="$D/review/conv-$T-r$R"; mkdir -p "$O"
  (cd "$D" && sh tools/shoot_all.sh "$S" "review/conv-$T-r$R" $P >/dev/null 2>&1; python3 -I tools/page_text.py "$S" > "review/conv-$T-r$R/$P-text.txt")
  echo "$T: $O"
done
