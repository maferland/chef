#!/usr/bin/env bash
# fetch-flyers.sh — screenshot grocery flyer pages for Claude vision parsing
#
# Usage:
#   fetch-flyers.sh [store1,store2,...]   comma-separated stores (default: all)
#
# Output:
#   ~/.claude/chef/flyer-cache/{Store}-{YYYY-MM-DD}.png

set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CACHE_DIR="$HOME/.claude/chef/flyer-cache"
DATE=$(date +%Y-%m-%d)
REQUESTED="${1:-all}"

store_url() {
    case "$1" in
        Metro)    echo "https://www.metro.ca/fr/circulaire" ;;
        IGA)      echo "https://www.iga.net/fr/circulaire" ;;
        Maxi)     echo "https://www.maxi.ca/fr/circulaire" ;;
        Provigo)  echo "https://www.provigo.ca/fr/circulaire" ;;
        "Super C") echo "https://www.superc.ca/fr/circulaire" ;;
        SAQ)      echo "https://www.saq.com/fr/promotions-et-nouveautes" ;;
        *)        echo "" ;;
    esac
}

ALL_STORES="Metro IGA Maxi Provigo Super C SAQ"

if [ "$REQUESTED" = "all" ]; then
    STORES="$ALL_STORES"
else
    STORES=$(echo "$REQUESTED" | tr ',' ' ')
fi

if [ ! -f "$CHROME" ]; then
    echo "Error: Chrome not found at $CHROME"
    exit 1
fi

mkdir -p "$CACHE_DIR"

FETCHED=0
FAILED=0

for STORE in $STORES; do
    URL=$(store_url "$STORE")

    if [ -z "$URL" ]; then
        echo "⚠️  Unknown store: $STORE — skipping"
        continue
    fi

    OUTPUT="${CACHE_DIR}/${STORE}-${DATE}.png"
    echo "Fetching $STORE..."

    "$CHROME" \
        --headless=new \
        --no-sandbox \
        --disable-gpu \
        --screenshot="$OUTPUT" \
        --window-size=1400,3000 \
        --hide-scrollbars \
        "$URL" 2>/dev/null || true

    if [ -f "$OUTPUT" ] && [ -s "$OUTPUT" ]; then
        SIZE=$(wc -c < "$OUTPUT")
        echo "  ✓ $OUTPUT (${SIZE} bytes)"
        FETCHED=$((FETCHED + 1))
    else
        echo "  ✗ Failed: $STORE"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "Done. $FETCHED screenshot(s) saved to $CACHE_DIR/"
[ "$FAILED" -gt 0 ] && echo "$FAILED store(s) failed."
