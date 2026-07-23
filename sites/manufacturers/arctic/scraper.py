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
    return Array.from(urls).sort((a, b) => {
        const ga = parseInt(a.match(/_g(\\d+)/)?.[1] ?? "999", 10);
        const gb = parseInt(b.match(/_g(\\d+)/)?.[1] ?? "999", 10);
        return ga - gb;
    });
}
"""

ARCTIC_GET_SPECS_JS = r"""
() => {
    let output = 'Specifications:\n';

    const blocks = document.querySelectorAll('.collapse-item');
    if (!blocks.length) return '⚠️ No specs found';

    blocks.forEach(block => {
        const titleEl = block.querySelector('.collapse-headline span');
        const title = titleEl?.textContent.trim();

        if (title) {
            output += `　${title}\n`;
        }

        // CASE 1: table style (technical-data)
        const tables = block.querySelectorAll('.technical-data .table');
        tables.forEach(row => {
            const cols = row.querySelectorAll('.spalte');
            if (cols.length >= 2) {
                const key = cols[0].textContent.trim();
                const val = cols[1].textContent.trim().replace(/\s+/g, ' ');
                output += `　　${key}: ${val}\n`;
            }
        });

        // CASE 2: UL list (Packaging)
        const listItems = block.querySelectorAll('ul li');
        listItems.forEach(li => {
            const text = li.textContent.trim().replace(/\s+/g, ' ');
            if (text) output += `　　${text}\n`;
        });

        // CASE 3: paragraph info (Manufacturer / EAN / UPC)
        const paragraphs = block.querySelectorAll('.technical-data p');
        paragraphs.forEach(p => {
            const text = p.textContent.trim().replace(/\s+/g, ' ');
            if (text) output += `　　${text}\n`;
        });

        output += '\n';
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
