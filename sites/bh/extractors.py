"""B&H page extraction (ported from Tampermonkey helpers)."""

BH_GET_IMAGES_JS = """
() => {
    const urls = [];
    const preloaded = document.querySelector('div.bh-preloaded-data');
    if (!preloaded) return [];
    const priorities = [
        'images2500x2500', 'images2000x2000', 'images1500x1500',
        'images1000x1000', 'images500x500', 'images250x250',
        'images150x150', 'smallimages', 'thumbnails'
    ];
    try {
        const dataJson = JSON.parse(preloaded.getAttribute('data-data'));
        const dataStr = JSON.stringify(dataJson);
        const allMatches = dataStr.match(/https:\\/\\/static\\.bhphoto\\.com\\/images\\/[^"\\\\\\s]+\\.jpg/g) || [];
        const validMatches = allMatches.filter(url => {
            const fileMatch = url.match(/\\/([^\\/]+\\.jpg)$/);
            if (!fileMatch) return false;
            const fileName = fileMatch[1];
            return /^[0-9]+_[0-9]+\\.jpg$/.test(fileName) || /^[0-9]+_IMG_[0-9]+\\.jpg$/.test(fileName);
        });
        const imagesMap = {};
        validMatches.forEach(url => {
            const baseName = url.match(/\\/([^\\/]+\\.jpg)$/)[1];
            if (!imagesMap[baseName]) imagesMap[baseName] = [];
            imagesMap[baseName].push(url);
        });
        for (const urlsArr of Object.values(imagesMap)) {
            let selected = null;
            for (const size of priorities) {
                selected = urlsArr.find(u => u.includes('/' + size + '/'));
                if (selected) break;
            }
            if (!selected) selected = urlsArr[0];
            urls.push(selected);
        }
    } catch (err) {
        console.error('bh images:', err);
    }
    return urls;
}
"""

# Returns string[] — export adds bullets via YAML transform (no headings in JS).
BH_GET_FEATURES_JS = """
() => {
    const meta = document.querySelector('meta[name="description"]');
    if (!meta) return [];

    let content = meta.getAttribute('content') || '';
    if (!content) return [];

    const match = content.match(/featuring([\\s\\S]*?)\\.?\\s*Review/i);
    if (!match) return [];

    const featureText = match[1].trim();
    const parts = featureText
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

    const features = [];
    let i = 0;

    while (i < parts.length) {
        let part = parts[i];

        if (/Webcam/i.test(part)) {
            let audio = part;
            while (i + 1 < parts.length && !/Mics/i.test(parts[i])) {
                i++;
                audio += ', ' + parts[i];
                if (/Mics/i.test(parts[i])) break;
            }
            features.push(audio);
        } else {
            features.push(part);
        }

        i++;
    }

    return features;
}
"""

# Returns plain text with original paragraph newlines (no Feature & Design heading).
BH_GET_DESIGN_JS = """
() => {
    const container =
        document.querySelector('[data-selenium="overviewLongDescription"]') ||
        document.querySelector('[data-selenium="overviewDescription"]');
    if (!container) return '';

    const paragraphs = container.querySelectorAll('.js-injected-html p, p');
    const lines = [];
    paragraphs.forEach(p => {
        const text = (p.textContent || '').trim();
        if (text) lines.push(text);
    });

    if (lines.length) {
        return lines.join('\\n\\n');
    }

    return (container.innerText || '').trim();
}
"""

BH_GET_SPECS_JS = """
() => {
    let output = 'Specifications:\\n';
    const specContent = document.querySelector('div[class^="specsContent_"]');
    if (!specContent) return '';
    const groups = specContent.querySelectorAll('div[class^="group_"]');
    groups.forEach(group => {
        let title = '';
        const nameEl = group.querySelector('div[class^="name_"]');
        if (nameEl) {
            title = nameEl.textContent.trim();
        } else {
            const h2El = specContent.querySelector('div[class^="title_"] h2');
            if (h2El) title = h2El.textContent.trim();
        }
        if (!title) title = 'GENERAL';
        output += `　${title}\\n`;
        group.querySelectorAll('tr[data-selenium="specsItemGroupTableRow"]').forEach(row => {
            const key = row.querySelector('td[class^="label_"]')?.textContent?.trim();
            const val = row.querySelector('td[class^="value_"]')?.innerText?.trim().replace(/\\s*\\n\\s*/g, ', ');
            if (key && val) output += `　　${key}: ${val}\\n`;
        });
        output += '\\n';
    });
    return output.trim();
}
"""

BH_GET_PACKAGING_JS = """
() => {
    const names = document.querySelectorAll('[data-selenium="specsItemGroupName"]');
    for (const nameEl of names) {
        if (nameEl.textContent.trim() !== 'Packaging Info') continue;
        const group = nameEl.closest('div[class*="group_"]') || nameEl.parentElement;
        if (!group) continue;
        const table = group.querySelector('[data-selenium="specsItemGroupTable"]');
        if (!table) continue;
        const out = {};
        table.querySelectorAll('[data-selenium="specsItemGroupTableRow"]').forEach(row => {
            const key = row.querySelector('[data-selenium="specsItemGroupTableColumnLabel"]')
                ?.textContent?.trim();
            const val = row.querySelector('[data-selenium="specsItemGroupTableColumnValue"]')
                ?.innerText?.trim().replace(/\\s*\\n\\s*/g, ' ');
            if (key && val) out[key] = val;
        });
        return out;
    }
    return {};
}
"""
