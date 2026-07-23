"""Arctic manufacturer site extraction (Shopware PDP)."""

from __future__ import annotations

ARCTIC_GET_IMAGES_JS = """
() => {
    const urls = new Set();
    const add = (url) => {
        if (!url || url.startsWith('data:')) return;
        if (url.startsWith('//')) url = 'https:' + url;
        if (!/\\/media\\//.test(url)) return;
        urls.add(url.split('?')[0]);
    };
    document.querySelectorAll('.gallery-slider-image[data-src], .gallery-slider-image[src]').forEach(img => {
        add(img.getAttribute('data-src') || img.src);
    });
    document.querySelectorAll('.gallery-slider-image.magnifier-image').forEach(img => {
        add(img.getAttribute('data-src') || img.src);
    });
     /*
     return Array.from(urls).sort((a, b) => {
        const ma = a.match(/_g(\\d+)/);
        const mb = b.match(/_g(\\d+)/);
    
        const ga = ma ? parseInt(ma[1], 10) : 999;
        const gb = mb ? parseInt(mb[1], 10) : 999;
    
        if (ga !== gb) return ga - gb;
    
        // Same g number (e.g. g00 vs g00_eha_award)
        return a.localeCompare(b);
    });
    */
    return Array.from(urls).sort((a, b) => {
        const ga = parseInt(a.match(/_g(\\d+)/)?.[1] ?? "999", 10);
        const gb = parseInt(b.match(/_g(\\d+)/)?.[1] ?? "999", 10);
    
        return ga - gb;
    });
    
}
"""

ARCTIC_GET_SPECS_JS = """
() => {
    let output = 'Specifications:\\n';
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        let group = 'General Specifications';
        const heading = table.closest('section, .cms-element-text, .product-detail-tabs')
            ?.querySelector('h2, h3, h4');
        if (heading) group = heading.textContent.trim();
        output += `　${group}\\n`;
        table.querySelectorAll('tr').forEach(row => {
            const cells = row.querySelectorAll('th, td');
            if (cells.length >= 2) {
                const key = cells[0].textContent.trim();
                const val = cells[1].textContent.trim();
                if (key && val) output += `　　${key}: ${val}\\n`;
            } else if (cells.length === 1) {
                const text = cells[0].textContent.trim();
                const match = text.match(/^([^:]+):\\s*(.+)$/);
                if (match) output += `　　${match[1].trim()}: ${match[2].trim()}\\n`;
            }
        });
    });
    const packaging = document.querySelector('.product-detail-packaging, [class*="packaging"]');
    if (packaging) {
        output += '　Packaging\\n';
        packaging.querySelectorAll('li, p').forEach(el => {
            const text = el.textContent.trim();
            const match = text.match(/^([^:]+):\\s*(.+)$/);
            if (match) output += `　　${match[1].trim()}: ${match[2].trim()}\\n`;
        });
    }
    document.querySelectorAll('ul li').forEach(li => {
        const text = li.textContent.trim();
        if (/^(Width|Height|Length|Weight|EAN|UPC):\\s*/i.test(text)) {
            const match = text.match(/^([^:]+):\\s*(.+)$/);
            if (match) output += `　　${match[1].trim()}: ${match[2].trim()}\\n`;
        }
    });
    return output.trim();
}
"""

ARCTIC_GET_FEATURES_JS = """
() => {
    const features = [];

    const desc = document.querySelector(
        '#senza-content > div > div > div:nth-child(2) > div.product-detail-description-text.text-right'
    );

    if (desc) {
        desc.querySelectorAll('p').forEach(p => {
            const text = p.textContent.trim();
            if (text) features.push(text);
        });
    }

    return features;
}
"""

ARCTIC_GET_DESCRIPTION_JS = """
() => {
    const parts = [];
    document.querySelectorAll('.cms-element-text h3, .product-detail-description h3, h3').forEach(h3 => {
        const title = h3.textContent.trim();
        if (!title || title === 'Choose variant') return;
        let body = '';
        let el = h3.nextElementSibling;
        while (el && !/^H[1-4]$/.test(el.tagName)) {
            if (el.tagName === 'P') body += (body ? '\\n' : '') + el.textContent.trim();
            el = el.nextElementSibling;
        }
        if (body) parts.push(`${title}\\n${body}`);
    });
    return parts.join('\\n\\n');
}
"""


def _parse_specs_text(text: str) -> dict:
    specs: dict = {}
    current_group = "General"
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Specifications"):
            continue
        if line.startswith("　　") and ":" in stripped:
            key, _, val = stripped.partition(":")
            block = specs.setdefault(current_group, {})
            block[key.strip()] = val.strip()
        elif line.startswith("　") and not line.startswith("　　"):
            current_group = stripped
            specs.setdefault(current_group, {})
    return specs


def scrape_arctic_product(page) -> dict:
    images = page.evaluate(ARCTIC_GET_IMAGES_JS) or []
    specs_text = page.evaluate(ARCTIC_GET_SPECS_JS) or ""
    features = page.evaluate(ARCTIC_GET_FEATURES_JS) or []
    description = page.evaluate(ARCTIC_GET_DESCRIPTION_JS) or ""

    title = ""
    el = page.query_selector("h1")
    if el:
        title = el.inner_text().strip()

    subtitle_el = page.query_selector(".product-detail-name ~ p, .product-detail-name-subtitle")
    subtitle = subtitle_el.inner_text().strip() if subtitle_el else ""
    if subtitle and title:
        title = f"{title} — {subtitle}"

    return {
        "source": "manufacturer",
        "brand": "arctic",
        "title": title,
        "description": description,
        "features": features if isinstance(features, list) else [],
        "images": images,
        "specs_text": specs_text,
        "specs": _parse_specs_text(specs_text),
    }
