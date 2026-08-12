"""Arctic manufacturer site extraction (Shopware PDP)."""

from __future__ import annotations

SAMSUNG_GET_IMAGES_JS = r"""
() => {
    return Array.from(document.querySelectorAll(
        '.pdd-header-gallery__item img'
    ))
        .map(img =>
             img.getAttribute('data-desktop-src') ||
             img.getAttribute('data-src') ||
             img.getAttribute('srcset')?.split(/\s+/)[0] ||
             img.src
            )
        .filter(Boolean)
        .map(src => src.startsWith('//') ? 'https:' + src : src)
        .filter((v, i, arr) => arr.indexOf(v) === i);
}
"""

SAMSUNG_GET_SPECS_JS = r"""
() => {
    let output = 'Specifications:\n';

    // =========================
    // TYPE 1: product-spec (accordion)
    // =========================
    const sections1 = document.querySelectorAll('[class*="product-spec__item"]');

    if (sections1.length) {
        sections1.forEach(section => {
            const titleEl = section.querySelector('[class*="product-spec__title"] button');
            if (titleEl) {
                output += `\n　${titleEl.textContent.trim().toUpperCase()}\n`;
            }

            section.querySelectorAll('[class*="product-spec__content-item"]').forEach(li => {
                const key = li.querySelector('[class*="content-item-title"]');
                const val = li.querySelector('[class*="content-item-desc"]');

                if (key && val) {
                    const cleanVal = val.textContent.trim().replace(/\s*\n\s*/g, ', ');
                    output += `　　${key.textContent.trim()}: ${cleanVal}\n`;
                } else if (val) {
                    const cleanVal = val.textContent.trim().replace(/\s*\n\s*/g, ', ');
                    output += `　　${cleanVal}\n`;
                }
            });
        });

        return output.trim();
    }

    // =========================
    // TYPE 2: spec-highlight (NEW layout)
    // =========================
    const sections2 = document.querySelectorAll('.spec-highlight__detail');

    if (sections2.length) {
        sections2.forEach(section => {
            const titleEl = section.querySelector('.spec-highlight__title');
            if (titleEl) {
                output += `\n　${titleEl.textContent.trim().toUpperCase()}\n`;
            }

            section.querySelectorAll('.spec-highlight__item').forEach(li => {
                const key = li.querySelector('.spec-highlight__title');
                const val = li.querySelector('.spec-highlight__value');

                if (key && val) {
                    output += `　　${key.textContent.trim()}: ${val.textContent.trim()}\n`;
                } else if (val) {
                    // handles cases like OS / Sensors (no key)
                    output += `　　${val.textContent.trim()}\n`;
                }
            });
        });

        return output.trim();
    }

    return '⚠️ No specs found';
}
"""

SAMSUNG_GET_DESCRIPTION_JS = """
() => {
    return ""
}
"""