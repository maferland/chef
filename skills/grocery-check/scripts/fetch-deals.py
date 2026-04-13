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

import re, sys
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

            // Extract all prices from the tile
            const prices = [...tile.textContent.matchAll(/(\\d+[,]\\d+)\\s*\\$/g)]
                .map(m => parseFloat(m[1].replace(',', '.')));
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
            let card = label.parentElement;
            for (let i = 0; i < 8; i++) {
                if (!card) break;
                if (card.querySelectorAll('a[href*="/fr/produits/"]').length > 0) break;
                card = card.parentElement;
            }
            if (!card) return;
            const nameEl = card.querySelector('[class*="cursor-pointer"], a[href*="/fr/produits/"]');
            if (!nameEl) return;
            const name = nameEl.textContent.trim();
            const prices = [...card.textContent.matchAll(/(\\d+[,]\\d+)\\s*\\$/g)].map(
                m => parseFloat(m[1].replace(',','.'))
            );
            if (prices.length < 2) return;
            const sale = Math.min(...prices.slice(0, 2));
            const was = Math.max(...prices.slice(0, 2));
            const disc = Math.round((1 - sale/was)*100);
            results.push({
                name: name.substring(0, 65),
                sale: sale.toFixed(2).replace('.', ',') + ' $',
                reg: was.toFixed(2).replace('.', ',') + ' $',
                disc: disc
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


def extract_maxi_js(page):
    """Extract Maxi deals using sale/was labels."""
    deals = page.evaluate('''() => {
        const results = [];
        const cards = Array.from(document.querySelectorAll('li, article, [data-testid]'));
        const seen = new Set();
        cards.forEach(card => {
            const saleEl = Array.from(card.querySelectorAll('*')).find(
                el => el.childNodes.length === 1 && el.textContent.trim() === 'sale'
            );
            const wasEl = Array.from(card.querySelectorAll('*')).find(
                el => el.childNodes.length === 1 && el.textContent.trim() === 'was'
            );
            if (!saleEl || !wasEl) return;
            // Price is sibling text node
            const salePrice = saleEl.nextSibling?.textContent?.trim() ||
                              saleEl.parentElement?.querySelector('text')?.textContent;
            const wasPrice = wasEl.nextSibling?.textContent?.trim();
            const nameEl = card.querySelector('h3, h2, [class*="title"]');
            if (!nameEl || !salePrice || !wasPrice) return;
            const name = nameEl.textContent.trim();
            if (seen.has(name)) return;
            seen.add(name);
            const sv = parseFloat(salePrice.replace('$','').trim());
            const wv = parseFloat(wasPrice.replace('$','').trim());
            const disc = Math.round((1-sv/wv)*100);
            results.push({ name: name.substring(0,65), sale: salePrice, reg: wasPrice, disc });
        });
        return results;
    }''')

    seen = set()
    filtered = []
    for item in deals:
        if item['name'] in seen: continue
        seen.add(item['name'])
        filtered.append(item)
    return sorted(filtered, key=lambda x: -x['disc'])


def dismiss_dialogs(page):
    for text in ['Accept All', 'Tout accepter', 'Oui', 'Sauter', 'Fermer', 'Close Tour']:
        try:
            page.get_by_role('button', name=text).click(timeout=1500)
            page.wait_for_timeout(400)
        except:
            pass


def scrape_store(page, name, config):
    print(f'\n  {name}...')
    stype = config['type']
    page.goto(config['url'], wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)
    dismiss_dialogs(page)

    if stype == 'iga':
        try:
            page.locator('#tab-1').click(timeout=2000)
            page.wait_for_timeout(2000)
            dismiss_dialogs(page)
        except:
            pass

    if stype == 'maxi':
        page.wait_for_timeout(2000)
        dismiss_dialogs(page)

    if stype in ('metro', 'superc'):
        page.wait_for_timeout(2000)
        return paginate_and_extract(page, config['url'], stype)
    elif stype == 'iga':
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
