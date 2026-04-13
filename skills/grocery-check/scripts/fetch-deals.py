#!/usr/bin/env -S uv run
# /// script
# dependencies = ["playwright"]
# ///
"""
fetch-deals.py — Scrape grocery flyer deals and write deals.md

Usage:
  uv run scripts/fetch-deals.py [Metro,IGA,Maxi,"Super C"]

Writes to ~/.claude/chef/flyer-cache/deals.md
Cache expires next Wednesday (Quebec flyer cycle Thu–Wed).
"""

import re, sys, json
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

CACHE_DIR = Path.home() / '.claude' / 'chef' / 'flyer-cache'
CACHE_FILE = CACHE_DIR / 'deals.md'

STORES = {
    'Metro': {
        'url': 'https://www.metro.ca/fr/epicerie-en-ligne/circulaire?sortOrder=relevance&filter=%3Arelevance%3Aoption%3Asuggestion-for-you',
        'type': 'metro',
    },
    'Super C': {
        'url': 'https://www.superc.ca/fr/epicerie-en-ligne/circulaire?sortOrder=relevance&filter=%3Arelevance%3Aoption%3Asuggestion-for-you',
        'type': 'superc',
    },
    'IGA': {
        'url': 'https://www.iga.net/fr/circulaire?view=list',
        'type': 'iga',
    },
    'Maxi': {
        'url': 'https://www.maxi.ca/fr/deals/flyer',
        'type': 'maxi',
    },
}

SKIP_KW = ['détergent','shampoo','savon','litière','couche','nettoyant',
           'lave-vaisselle','mouchoir','antisudorifique']
MAX_DISC = 85  # discard apparent discounts > 85% (bottle deposits, data artifacts)


def next_wednesday():
    today = datetime.now()
    days = (2 - today.weekday()) % 7
    if days == 0: days = 7
    return (today + timedelta(days=days)).replace(hour=23, minute=59, second=59)


def get_pagination_urls(page, base_url):
    """Find all paginated page URLs (Metro/Super C use /circulaire-page-N pattern)."""
    pages = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('.ppn--element[href]'))
            .map(a => a.getAttribute('href'))
            .filter(h => h && !h.includes('void') && h.includes('circulaire-page'));
    }''')
    # Get max page number
    nums = []
    for url in pages:
        m = re.search(r'circulaire-page-(\d+)', url)
        if m: nums.append(int(m.group(1)))
    if not nums:
        return []
    max_page = max(nums)
    # Build all page URLs
    base = base_url.rstrip('/')
    return [f'{base.replace("/circulaire", "/circulaire-page-{i}")}' if 'circulaire-page' not in base
            else base.replace(re.search(r'circulaire-page-\d+', base).group(), f'circulaire-page-{i}')
            for i in range(2, max_page + 1)]


def paginate_and_extract(page, base_url, store_type, max_pages=None):
    """Navigate through all paginated pages and accumulate deals."""
    # Determine max page from pagination
    max_page = page.evaluate('''() => {
        const links = Array.from(document.querySelectorAll('.ppn--element[href]'));
        const nums = links.map(a => {
            const m = a.getAttribute('href').match(/circulaire-page-(\d+)/);
            return m ? parseInt(m[1]) : 0;
        });
        return nums.length ? Math.max(...nums) : 1;
    }''')
    print(f'    {max_page} pages total')

    # Build page URLs: replace /circulaire? with /circulaire-page-N?
    all_deals = extract_metro_superc_js(page, store_type)
    print(f'    Page 1: {len(all_deals)} deals')

    pages_to_fetch = range(2, max_page + 1)
    if max_pages:
        pages_to_fetch = range(2, min(max_page + 1, max_pages + 1))

    for n in pages_to_fetch:
        # Replace /circulaire in base_url with /circulaire-page-N
        full_url = base_url.replace('/circulaire?', f'/circulaire-page-{n}?')
        page.goto(full_url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(1500)
        new_deals = extract_metro_superc_js(page, store_type)
        existing_names = {d['name'] for d in all_deals}
        fresh = [d for d in new_deals if d['name'] not in existing_names]
        all_deals.extend(fresh)
        print(f'    Page {n}/{max_page}: +{len(fresh)} (total {len(all_deals)})', end='\r')

    print(f'\n    Done: {len(all_deals)} deals across {max_page} pages')
    return sorted(all_deals, key=lambda x: -x['disc'])


def extract_metro_superc_js(page, store_type):
    """Extract deals using .default-product-tile class (Metro/Super C shared platform)."""
    tile_class = 'default-product-tile' if store_type == 'metro' else 'default-product-tile'
    deals = page.evaluate(f'''() => {{
        const results = [];
        const tiles = Array.from(document.querySelectorAll('.{tile_class}'));
        tiles.forEach(tile => {{
            // Get product name: named link (not "Promo" image link)
            const links = tile.querySelectorAll('a[href*="/allees/"]');
            let name = '';
            links.forEach(l => {{
                const t = l.textContent.trim();
                if (t && t.length > 5 && !t.startsWith('Promo') && !t.startsWith('Ajouter')) {{
                    name = t;
                }}
            }});
            if (!name) return;

            // Extract all prices from the tile, filtering out deposits (< $1.00)
            const prices = [...tile.textContent.matchAll(/(\\d+[,]\\d+)\\s*\\$/g)]
                .map(m => parseFloat(m[1].replace(',', '.')))
                .filter(p => p >= 1.0);  // exclude bottle deposits ($0.10-$0.30)
            if (prices.length < 2) return;

            const reg = Math.max(prices[0], prices[1]);
            const sale = Math.min(prices[0], prices[1]);
            if (reg === sale) return;

            const disc = Math.round((1 - sale / reg) * 100);
            results.push({{
                name: name.replace(/\\s+/g, ' ').trim().substring(0, 65),
                sale: sale.toFixed(2).replace('.', ',') + ' $',
                reg: reg.toFixed(2).replace('.', ',') + ' $',
                disc: disc
            }});
        }});
        return results;
    }}''')

    seen = set()
    filtered = []
    for item in deals:
        name = item['name'].strip()
        if name in seen: continue
        if any(k in name.lower() for k in SKIP_KW): continue
        if item['disc'] > MAX_DISC: continue  # filter bottle deposit artifacts
        seen.add(name)
        item['name'] = name
        filtered.append(item)

    return sorted(filtered, key=lambda x: -x['disc'])


def extract_iga_js(page):
    """Extract IGA deals: ÉCONOMISEZ items (real discounts) + Scene+ offers."""
    discounts = page.evaluate('''() => {
        const results = [];
        // Find all ÉCONOMISEZ labels
        const labels = Array.from(document.querySelectorAll('*')).filter(
            el => el.childNodes.length === 1 &&
                  el.childNodes[0].nodeType === 3 &&
                  el.textContent.trim() === 'ÉCONOMISEZ'
        );
        labels.forEach(label => {
            let card = label;
            for (let i = 0; i < 8; i++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.textContent.length > 50 && card.textContent.length < 600) break;
            }
            // Normalize non-breaking spaces, extract prices >= $1
            const text = card.textContent.replace(/\xa0/g, ' ');
            const prices = [...text.matchAll(/(\\d+[,]\\d+)\\s*\\$/g)]
                .map(m => parseFloat(m[1].replace(',','.')))
                .filter(p => p >= 1.0);
            if (prices.length < 2) return;
            const sale = Math.min(prices[0], prices[1]);
            const was = Math.max(prices[0], prices[1]);
            if (sale >= was) return;
            // Product name: strip price+label prefix, take the trailing product text
            // Pattern: "SALE $WAS $ÉCONOMISEZ SAVINGS $SIZE NAMEBrand Product Name SIZE"
            let name = text
                .replace(/\\d+[,\\.]+\\d+\\s*\\$/g, '')  // remove prices
                .replace(/ÉCONOMISEZ/g, '')
                .replace(/\\(.*?\\)/g, '')  // remove parenthetical unit prices
                .replace(/[A-Z]+\\s*G\\s*\\(.*?\\)/g, '')  // remove "340 G (...)"
                .replace(/Ajouter[^A-Z]*/g, '')
                .replace(/favoris|panier|liste/gi, '')
                .replace(/\\s+/g, ' ')
                .trim();
            // Take the last meaningful segment (product name tends to be at the end)
            const parts = name.split(/(?=[A-Z][a-z])/);
            name = parts.slice(-1)[0]?.trim() || name.substring(0, 65);
            if (!name || name.length < 5) return;
            const disc = Math.round((1 - sale/was)*100);
            if (disc <= 0 || disc > 85) return;
            results.push({
                name: name.substring(0, 65),
                sale: sale.toFixed(2).replace('.', ',') + ' $',
                reg: was.toFixed(2).replace('.', ',') + ' $',
                disc
            });
        });
        return results;
    }''')

    scene_plus = page.evaluate('''() => {
        const results = [];
        // Find items with +TPS +TVQ (Scene+ loyalty items)
        const taxEls = Array.from(document.querySelectorAll('*')).filter(
            el => el.textContent.trim() === '+TPS +TVQ'
        );
        taxEls.forEach(el => {
            let card = el.parentElement;
            for (let i = 0; i < 6; i++) {
                if (!card) break;
                if (card.querySelectorAll('[class*="cursor-pointer"]').length > 0) break;
                card = card.parentElement;
            }
            if (!card) return;
            const nameEl = card.querySelector('[class*="cursor-pointer"]');
            if (!nameEl) return;
            const name = nameEl.textContent.trim();
            const prices = [...card.textContent.matchAll(/(\\d+[,]\\d+)\\s*\\$/g)].map(m => m[0].trim());
            const ptsMatch = card.textContent.match(/(\\d+)\\s*PTS/);
            if (!prices[0]) return;
            results.push({
                name: name.substring(0, 65),
                price: prices[0],
                pts: ptsMatch ? ptsMatch[1] : '?'
            });
        });
        return results.slice(0, 20);
    }''')

    seen = set()
    d_filtered = []
    for item in discounts:
        if item['name'] in seen: continue
        seen.add(item['name'])
        d_filtered.append(item)

    seen2 = set()
    s_filtered = []
    for item in scene_plus:
        if item['name'] in seen2: continue
        seen2.add(item['name'])
        s_filtered.append(item)

    return sorted(d_filtered, key=lambda x: -x['disc']), s_filtered


def extract_maxi_via_api(page, request_body, request_headers):
    """Paginate through Maxi's flyersPage POST API to get all flyer deals."""
    deals = []
    seen = set()
    page_num = 1
    from_idx = 1
    page_size = 48

    # Use all original headers — the PCExpress API requires the full auth context
    api_headers = request_headers

    while True:
        body = dict(request_body)
        body['listingInfo'] = dict(body.get('listingInfo', {}))
        body['listingInfo']['pagination'] = {'from': from_idx}
        body['listingInfo']['includeFiltersInResponse'] = (page_num == 1)

        # Do extraction in JS — pass headers and body as args to avoid f-string escaping issues
        page_result = page.evaluate('''async ({hdrs, bdy, maxDisc}) => {
            const r = await fetch('https://api.pcexpress.ca/pcx-bff/api/v2/flyersPage', {
                method: 'POST', headers: hdrs, body: JSON.stringify(bdy)
            });
            const data = await r.json();
            try {
                const tiles = data.layout.sections.productListingSection.components[0].data.productGrid.productTiles;
                const pagination = data.layout.sections.productListingSection.components[0].data.productGrid.pagination;
                const deals = tiles
                    .filter(t => t.pricing && t.pricing.wasPrice)
                    .map(t => {
                        const brand = t.brand || '';
                        const name = brand ? brand + ' ' + t.title : t.title;
                        const sv = parseFloat(t.pricing.price);
                        const wv = parseFloat(String(t.pricing.wasPrice).replace(',', '.').replace(/[\\s\\xa0\\$]/g, ''));
                        const disc = Math.round((1 - sv/wv)*100);
                        return { name: name.substring(0, 65), sale: '$' + sv.toFixed(2), reg: '$' + wv.toFixed(2), disc };
                    })
                    .filter(d => d.disc > 0 && d.disc <= maxDisc);
                return { deals, hasMore: pagination ? !!pagination.hasMore : false };
            } catch(e) {
                return { deals: [], hasMore: false, error: e.message };
            }
        }''', {'hdrs': api_headers, 'bdy': body, 'maxDisc': MAX_DISC})

        new_items = 0
        for item in page_result.get('deals', []):
            if item['name'] not in seen:
                seen.add(item['name'])
                deals.append(item)
                new_items += 1

        print(f'    Page {page_num}: +{new_items} deals (total {len(deals)})', end='\r')

        if not page_result.get('hasMore'):
            break

        from_idx += page_size
        page_num += 1

    print(f'\n    Done: {len(deals)} deals across {page_num} pages')
    return sorted(deals, key=lambda x: -x['disc'])


def dismiss_dialogs(page):
    for text in ['Accept All', 'Tout accepter', 'Tout Accepter', 'Oui', 'Sauter', 'Fermer', 'Close Tour', 'Skip Tour']:
        try:
            page.get_by_role('button', name=text).click(timeout=1500)
            page.wait_for_timeout(400)
        except:
            pass


def scrape_store(page, name, config):
    print(f'\n  {name}...')
    stype = config['type']

    # Maxi: set up API listener BEFORE navigation so we capture the flyersPage POST
    if stype == 'maxi':
        maxi_req = {'body': None, 'headers': None}
        def capture_maxi(request):
            if 'flyersPage' in request.url and request.method == 'POST':
                try:
                    maxi_req['body'] = request.post_data_json
                    maxi_req['headers'] = dict(request.headers)
                except: pass
        page.on('request', capture_maxi)

    page.goto(config['url'], wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)
    dismiss_dialogs(page)

    if stype == 'iga':
        # URL already has ?view=list which selects grid tab — no click needed
        page.wait_for_timeout(2000)
        dismiss_dialogs(page)

    if stype == 'maxi':
        page.wait_for_timeout(2000)
        dismiss_dialogs(page)

    if stype in ('metro', 'superc'):
        page.wait_for_timeout(2000)
        return paginate_and_extract(page, config['url'], stype)
    elif stype == 'maxi':
        page.wait_for_timeout(2000)  # wait for flyersPage POST to fire after store confirmation
        if maxi_req['body']:
            store_id = maxi_req['body'].get('fulfillmentInfo', {}).get('storeId', '?')
            print(f'    Using POST API (store {store_id})')
            return extract_maxi_via_api(page, maxi_req['body'], maxi_req['headers'])
        else:
            print('    flyersPage POST not captured')
            return []
    elif stype == 'iga':
        # Verify products loaded before starting click loop
        initial = page.evaluate("() => document.querySelectorAll(\"a[href*='/fr/produits/']\").length")
        if initial == 0:
            print(f'    IGA: no products loaded, retrying grid tab...')
            try:
                page.locator('#tab-1').click(timeout=3000)
                page.wait_for_timeout(3000)
            except: pass
        # Scroll to bottom first, then click "Charger plus" via JS until it disappears
        clicks = 0
        while clicks < 60:
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1000)
            clicked = page.evaluate('''() => {
                const btn = Array.from(document.querySelectorAll("button"))
                    .find(b => b.textContent.trim() === "Charger plus");
                if (btn) { btn.click(); return true; }
                return false;
            }''')
            if not clicked:
                break
            page.wait_for_timeout(1500)
            clicks += 1
            count = page.evaluate("() => document.querySelectorAll(\"a[href*='/fr/produits/']\").length")
            print(f'    Load more {clicks}: {count} products', end='\r')
        print(f'\n    Done: {clicks} loads')
        return extract_iga_js(page)
    elif stype == 'maxi':
        return extract_maxi_js(page)
    return []


def write_deals(results, expires):
    today = datetime.now()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        f.write(f'---\nfetched_at: {today.strftime("%Y-%m-%dT%H:%M:%S")}\nexpires_at: {expires.strftime("%Y-%m-%dT%H:%M:%S")}\n---\n\n')
        for store, (stype, data) in results.items():
            f.write(f'## {store}\n')
            if stype in ('metro', 'superc', 'maxi'):
                for item in data:
                    d = item['disc']
                    flag = '**' if d >= 35 else ''
                    f.write(f'- {flag}{item["name"]} — {item["sale"]}{"  ↓"+str(d)+"%" if d else ""} (was {item["reg"]}){flag}\n')
            elif stype == 'iga':
                discounts, scene = data
                for item in discounts:
                    d = item['disc']
                    f.write(f'- **{item["name"]} — {item["sale"]}  ↓{d}% (was {item["reg"]})**\n')
                if scene:
                    f.write('\n### IGA Scene+ Bonus Offers\n')
                    for item in scene:
                        f.write(f'- {item["name"]} — {item["price"]} (+{item["pts"]} pts)\n')
            elif stype == 'error':
                f.write(f'- Error: {data}\n')
            f.write('\n')


def main():
    stores_arg = sys.argv[1] if len(sys.argv) > 1 else 'Metro,Super C,IGA,Maxi'
    requested = [s.strip() for s in stores_arg.split(',')]
    expires = next_wednesday()
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1400, 'height': 900}
        ).new_page()

        for store_name in requested:
            if store_name not in STORES:
                print(f'  Unknown store: {store_name}')
                continue
            try:
                data = scrape_store(page, store_name, STORES[store_name])
                stype = STORES[store_name]['type']
                results[store_name] = (stype, data)
                count = len(data[0]) if isinstance(data, tuple) else len(data)
                print(f'    → {count} deals')
            except Exception as e:
                print(f'    Error: {e}')
                results[store_name] = ('error', str(e))

        browser.close()

    write_deals(results, expires)
    print(f'\nDone → {CACHE_FILE}')
    print(f'Expires: {expires.strftime("%a Apr %d")}')


if __name__ == '__main__':
    main()
