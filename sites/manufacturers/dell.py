"""Dell manufacturer site extraction."""

DELL_GET_IMAGES_JS = """
() => Array.from(document.querySelectorAll('.gallery-modal figure[data-full-img]'))
    .map(fig => {
        let url = fig.getAttribute('data-full-img');
        return url ? (url.startsWith('//') ? 'https:' + url : url) : null;
    })
    .filter(Boolean)
"""

DELL_GET_SPECS_JS = """
() => {
    let output = 'Specifications:\\n';
    const dell_ui1 = document.querySelectorAll('.specs.list-unstyled li');
    const dell_ui2 = document.querySelectorAll('.spec__main');
    if (dell_ui1.length > 0) {
        dell_ui1.forEach(item => {
            const key = item.querySelector('div')?.textContent?.trim();
            let valueEl = item.querySelector('p');
            let value = '';
            if (valueEl) {
                value = valueEl.innerHTML
                    .replace(/<br\\s*\\/?>/gi, '; ')
                    .replace(/\\s*;\\s*$/, '')
                    .replace(/\\s+/g, ' ')
                    .trim();
            }
            if (key && value) {
                output += `　　${key.replace(/^\\w/, c => c)}: ${value}\\n`;
            }
        });
    } else if (dell_ui2.length > 0) {
        dell_ui2.forEach(section => {
            section.querySelectorAll('.spec__main_wrapper').forEach(wrapper => {
                const mainTitle = wrapper.querySelector('.spec__child__heading')?.textContent?.trim() || 'General';
                output += `　${mainTitle}\\n`;
                wrapper.querySelectorAll('.spec__child .spec__item').forEach(item => {
                    const key = item.querySelector('.spec__item__title')?.textContent?.trim();
                    if (!key) return;
                    let valNode = item.cloneNode(true);
                    valNode.querySelector('.spec__item__title')?.remove();
                    let value = valNode.textContent
                        .split(/\\r?\\n/)
                        .map(v => v.trim())
                        .filter(Boolean)
                        .join(' , ');
                    if (value) output += `　　${key}: ${value}\\n`;
                });
                output += '\\n';
            });
        });
    }
    return output.replace(/^Model:\\s*/im, '').trim();
}
"""


def scrape_dell_product(page) -> dict:
    images = page.evaluate(DELL_GET_IMAGES_JS) or []
    specs_text = page.evaluate(DELL_GET_SPECS_JS) or ""
    title = ""
    try:
        title = page.title() or ""
    except Exception:
        pass
    return {
        "source": "manufacturer",
        "brand": "dell",
        "title": title,
        "images": images,
        "specs_text": specs_text,
        "specs": _parse_specs_text(specs_text),
    }


def _parse_specs_text(text: str) -> dict:
    """Parse indented specs text into {group: {key: val}}."""
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
