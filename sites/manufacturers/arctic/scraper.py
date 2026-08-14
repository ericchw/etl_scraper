"""Arctic manufacturer site extraction (Shopware PDP)."""

from __future__ import annotations

ARCTIC_GET_IMAGES_JS = r"""
() => {
    const urls = new Set();

    const add = (url) => {
        if (!url || url.startsWith('data:')) return;
        if (url.startsWith('//')) url = 'https:' + url;
        if (!/\/media\//.test(url)) return;
        urls.add(url.split('?')[0]);
    };

    document.querySelectorAll(
        '.gallery-slider-image[data-src], .gallery-slider-image[src]'
    ).forEach(img => {
        add(img.getAttribute('data-src') || img.src);
    });

    document.querySelectorAll('.gallery-slider-image.magnifier-image').forEach(img => {
        add(img.getAttribute('data-src') || img.src);
    });

    return Array.from(urls).sort((a, b) => {
        const getOrder = (url) => {
            const filename = url.split('/').pop();
    
            // _icon first
            if (/_icon\./i.test(filename)) return 0;
    
            // dimensions last
            if (/dimensions/i.test(filename)) return 999;
    
            // _00, _01, _02, _03, _04...
            const normal = filename.match(/_(\d+)(?:_[^.]+)?\.[^.]+$/);
            if (normal) return 10 + parseInt(normal[1], 10);
    
            // _g03 after normal images
            const g = filename.match(/_g(\d+)/i);
            if (g) return 100 + parseInt(g[1], 10);
    
            return 500;
        };
    
        return getOrder(a) - getOrder(b);
    });
}
"""

ARCTIC_GET_SPECS_JS = r"""
() => {
    let output = 'Specifications:\n';

    const blocks = document.querySelectorAll('.collapse-item');

    if (!blocks.length) {
        return '⚠️ No specs found';
    }

    // =========================================================
    // CLEAN TEXT
    // =========================================================

    const cleanText = text =>
    text
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/:$/, '')
    .replace(/[*_`]/g, '')
    .replace(/®/g, '')
    .replace(/^Compatibillity$/im, 'Compatibility')
    .replace(/^Cable Lenght$/im, 'Cable Length');


    // =========================================================
    // CLEAN VALUE
    // =========================================================

    const cleanValue = el => {

        const clone = el.cloneNode(true);

        // Preserve line breaks
        clone.querySelectorAll('br').forEach(br => {
            br.replaceWith('; ');
        });

        // Preserve superscript
        clone.querySelectorAll('sup').forEach(sup => {
            const value = sup.textContent.trim();

            sup.replaceWith(
                value ? `^${value}` : ''
            );
        });

        return clone.textContent
            .trim()
            .replace(/\s+/g, ' ')
            .replace(/[*_`]/g, '')
            .replace(/®/g, '');
    };


    // =========================================================
    // SECTION HEADING DETECTION
    // =========================================================

    const isSectionHeading = el => {

        if (el.tagName !== 'DIV') {
            return false;
        }

        // Don't treat a container containing a table
        // as a heading.
        if (el.querySelector('table, .table')) {
            return false;
        }

        const text = el.textContent.trim();

        if (!text) {
            return false;
        }

        const style = el.getAttribute('style') || '';

        const isOldHeading =
              /color\s*:\s*white/i.test(style);

        const isBoldHeading =
              /font-weight\s*:\s*(bold|[6-9]00)/i.test(style);

        return isOldHeading || isBoldHeading;
    };


    // =========================================================
    // PROCESS EACH COLLAPSE BLOCK
    // =========================================================

    blocks.forEach(block => {

        const title =
              block
        .querySelector('.collapse-headline span')
        ?.textContent
        .trim() || '';


        const technicalData =
              block.querySelector('.technical-data');


        // =====================================================
        // SPECIFICATIONS
        // =====================================================

        if (
            technicalData &&
            title !== 'Manufacturer Info'
        ) {

            // Section title
            if (
                title &&
                title !== 'Specifications'
            ) {
                output += `  ${title}\n`;
            }


            // -----------------------------------------------
            // Specification storage
            // -----------------------------------------------

            const rootSpecs = new Map();
            const sectionSpecs = new Map();

            let currentSection = '';
            let previousKey = '';


            // -----------------------------------------------
            // Add specification
            // -----------------------------------------------

            const addSpec = (key, value) => {

                if (!key || !value) {
                    return;
                }

                let targetMap;

                if (currentSection) {

                    if (!sectionSpecs.has(currentSection)) {
                        sectionSpecs.set(
                            currentSection,
                            new Map()
                        );
                    }

                    targetMap =
                        sectionSpecs.get(currentSection);

                } else {

                    targetMap = rootSpecs;
                }


                let outputKey = key;


                // Old layout special case:
                //
                // Bearing
                // Current | Voltage
                //
                // becomes:
                //
                // Bearing Current | Voltage

                if (
                    key === 'Current | Voltage' &&
                    previousKey
                ) {
                    outputKey =
                        `${previousKey} ${key}`;
                }


                if (!targetMap.has(outputKey)) {
                    targetMap.set(outputKey, []);
                }


                const values =
                      targetMap.get(outputKey);


                // Avoid duplicate values
                if (!values.includes(value)) {
                    values.push(value);
                }


                previousKey = key;
            };


            // =================================================
            // WALK TECHNICAL DATA
            // =================================================

            const elements =
                  technicalData.querySelectorAll('*');


            elements.forEach(el => {

                // ---------------------------------------------
                // SECTION HEADING
                // ---------------------------------------------

                if (isSectionHeading(el)) {

                    const section =
                          cleanText(el.textContent);

                    if (section) {

                        currentSection = section;

                        if (
                            !sectionSpecs.has(
                                currentSection
                            )
                        ) {
                            sectionSpecs.set(
                                currentSection,
                                new Map()
                            );
                        }

                        previousKey = '';
                    }

                    return;
                }


                // =============================================
                // OLD LAYOUT
                //
                // .table
                //   .spalte
                //   .spalte
                // =============================================

                if (
                    el.classList &&
                    el.classList.contains('table')
                ) {

                    const cols =
                          el.querySelectorAll('.spalte');


                    if (cols.length >= 2) {

                        const key =
                              cleanText(
                                  cols[0].textContent
                              );

                        const value =
                              cleanValue(cols[1]);


                        if (key) {

                            addSpec(
                                key,
                                value
                            );

                        } else if (
                            value &&
                            previousKey
                        ) {

                            let targetMap;

                            if (currentSection) {

                                if (
                                    !sectionSpecs.has(
                                        currentSection
                                    )
                                ) {
                                    sectionSpecs.set(
                                        currentSection,
                                        new Map()
                                    );
                                }

                                targetMap =
                                    sectionSpecs.get(
                                    currentSection
                                );

                            } else {

                                targetMap =
                                    rootSpecs;
                            }


                            if (
                                !targetMap.has(
                                    previousKey
                                )
                            ) {
                                targetMap.set(
                                    previousKey,
                                    []
                                );
                            }


                            const values =
                                  targetMap.get(
                                      previousKey
                                  );


                            if (!values.includes(value)) {
                                values.push(value);
                            }
                        }
                    }

                    return;
                }


                // =============================================
                // NEW LAYOUT
                //
                // <table>
                //   <tr>
                //     <td>Density</td>
                //     <td>2.50 g/cm³</td>
                //   </tr>
                // </table>
                // =============================================

                if (el.tagName === 'TABLE') {

                    let rows =
                        el.querySelectorAll(
                            ':scope > tbody > tr'
                        );


                    // Tables without <tbody>
                    if (!rows.length) {
                        rows =
                            el.querySelectorAll(
                            ':scope > tr'
                        );
                    }


                    // Final fallback
                    if (!rows.length) {
                        rows =
                            el.querySelectorAll('tr');
                    }


                    rows.forEach(row => {

                        const cells =
                              row.querySelectorAll('td');


                        if (cells.length < 2) {
                            return;
                        }


                        const key =
                              cleanText(
                                  cells[0].textContent
                              );


                        const value =
                              cleanValue(cells[1]);


                        if (key) {

                            addSpec(
                                key,
                                value
                            );

                        } else if (
                            value &&
                            previousKey
                        ) {

                            let targetMap;

                            if (currentSection) {

                                if (
                                    !sectionSpecs.has(
                                        currentSection
                                    )
                                ) {
                                    sectionSpecs.set(
                                        currentSection,
                                        new Map()
                                    );
                                }

                                targetMap =
                                    sectionSpecs.get(
                                    currentSection
                                );

                            } else {

                                targetMap =
                                    rootSpecs;
                            }


                            if (
                                !targetMap.has(
                                    previousKey
                                )
                            ) {
                                targetMap.set(
                                    previousKey,
                                    []
                                );
                            }


                            const values =
                                  targetMap.get(
                                      previousKey
                                  );


                            if (!values.includes(value)) {
                                values.push(value);
                            }
                        }
                    });


                    return;
                }
            });


            // =================================================
            // OUTPUT ROOT SPECS
            // =================================================

            rootSpecs.forEach((values, key) => {

                if (!values.length) {
                    return;
                }

                output +=
                    `    ${key}: ${values.join('; ')}\n`;
            });


            // =================================================
            // OUTPUT NESTED SECTIONS
            // =================================================

            sectionSpecs.forEach((specs, section) => {

                if (!specs.size) {
                    return;
                }

                output +=
                    `  ${section}\n`;


                specs.forEach((values, key) => {

                    if (!values.length) {
                        return;
                    }

                    output +=
                        `    ${key}: ${values.join('; ')}\n`;
                });


                output += '\n';
            });


            // Blank line before next collapse block
            output += '\n';
        }


        // =====================================================
        // PACKAGING
        // =====================================================

        const items =
              block.querySelectorAll('ul li');


        if (items.length) {

            if (title) {
                output += `  ${title}\n`;
            }


            items.forEach(li => {

                const text =
                      li.textContent
                .trim()
                .replace(/\s+/g, ' ');


                if (text) {
                    output +=
                        `    ${text}\n`;
                }
            });


            output += '\n';
        }


        // =====================================================
        // MANUFACTURER INFO
        // =====================================================

        let manufacturer =
            block.querySelectorAll(
                '.manufacturer-data p'
            );


        // Fallback for older layouts
        if (
            !manufacturer.length &&
            title === 'Manufacturer Info'
        ) {
            manufacturer =
                block.querySelectorAll(
                '.technical-data p'
            );
        }


        if (manufacturer.length) {

            output += `  ${title}\n`;


            manufacturer.forEach(p => {

                const clone =
                      p.cloneNode(true);


                const label =
                      clone
                .querySelector('b')
                ?.textContent
                .trim();


                clone
                    .querySelector('b')
                    ?.remove();


                // Preserve readable spacing around <br>
                clone
                    .querySelectorAll('br')
                    .forEach(br => {
                    br.replaceWith(' ');
                });


                const value =
                      clone.textContent
                .trim()
                .replace(/\s+/g, ' ')
                .replace(/^[:\-\s]+/, '');


                const cleanLabel =
                      label
                ? cleanText(label)
                : '';


                if (
                    cleanLabel &&
                    value
                ) {

                    output +=
                        `    ${cleanLabel}: ${value}\n`;

                } else if (value) {

                    output +=
                        `    ${value}\n`;
                }
            });


            output += '\n';
        }
    });


    // =========================================================
    // FINAL CLEANUP
    // =========================================================

    return output
        .trim()
        .replace(/\n{3,}/g, '\n\n');
}
"""

ARCTIC_GET_FEATURES_JS = r"""
() => {
    const features = [];
    const seen = new Set();

    const excludedHeadings = new Set([
        'awards',
        'brauchst du hilfe oder eine produktberatung?',
        '3d model'
    ]);

    const addFeature = (heading) => {
        if (!heading) {
            return;
        }

        let text = heading.textContent.trim().replace(/\s+/g, ' ');

        if (!text) {
            return;
        }

        const normalized = text.toLowerCase();

        if (excludedHeadings.has(normalized)) {
            return;
        }

        // Keep the expected output name.
        if (normalized === 'automated two-plane balancing') {
            text = 'Automated Balancing';
        }

        const key = text.toLowerCase();

        if (!seen.has(key)) {
            seen.add(key);
            features.push(text);
        }
    };

    // ------------------------------------------------------------
    // Previous page layout
    // ------------------------------------------------------------
    const oldBlocks = document.querySelectorAll(
        'div.product-detail-description-block-wrap > div.product-detail-description-block'
    );

    oldBlocks.forEach(block => {
        const h3 = block.querySelector('h3');
        addFeature(h3);
    });

    // ------------------------------------------------------------
    // New page layout
    // ------------------------------------------------------------
    const newBlocks = document.querySelectorAll(
        '.senza-custom-fields .senza-content-wrap'
    );

    newBlocks.forEach(block => {
        // Some sections have desktop + mobile versions containing
        // the same <h3>, so the Set above prevents duplicates.
        const headings = block.querySelectorAll('h3');

        headings.forEach(h3 => {
            addFeature(h3);
        });
    });

    return features;
}
"""

ARCTIC_GET_DESCRIPTION_JS = r"""
() => {
    const excluded = new Set([
        'Do you need help or product advice?',
        'Brauchst du Hilfe oder eine Produktberatung?',
        'Online Dictionary',
        'Choose variant'
    ]);

    const seen = new Set();
    const parts = [];

    document.querySelectorAll(
        '.cms-element-text h3, .product-detail-description h3, h3'
    ).forEach(h3 => {
        const title = h3.textContent.trim();

        if (!title || excluded.has(title)) {
            return;
        }

        let body = '';
        let el = h3.nextElementSibling;

        while (el && !/^H[1-4]$/.test(el.tagName)) {
            if (el.tagName === 'P') {
                const text = el.textContent.trim();

                if (text) {
                    body += (body ? '\n' : '') + text;
                }
            }

            el = el.nextElementSibling;
        }

        if (!body) {
            return;
        }

        const key = `${title}\n${body}`;

        // Prevent identical desktop/mobile sections
        if (seen.has(key)) {
            return;
        }

        seen.add(key);
        parts.push(key);
    });

    return parts.join('\n\n');
}
"""


# def _parse_specs_text(text: str) -> dict:
#     specs = {}
#
#     current_group = "General Specifications"
#     specs[current_group] = {}
#
#     previous_key = ""
#
#     for line in (text or "").splitlines():
#
#         if not line.strip():
#             continue
#
#         if line.strip().startswith("Specifications") or line.strip().startswith("⚠️"):
#             continue
#
#         stripped = line.strip()
#
#         # Count indentation level
#         indent = len(line) - len(line.lstrip(" "))
#
#         # Level 0: top-level sections
#         # Packaging, Manufacturer Info
#         if indent == 0 and ":" not in stripped:
#             current_group = stripped
#
#             # Avoid duplicate empty groups
#             if current_group not in specs:
#                 specs[current_group] = {}
#
#             previous_key = ""
#             continue
#
#
#         # Level 2: subgroup
#         # Example:
#         #   Radiator
#         #     Material: Aluminium
#         if indent == 2 and ":" not in stripped:
#             current_group = stripped
#
#             if current_group not in specs:
#                 specs[current_group] = {}
#
#             previous_key = ""
#             continue
#
#
#         # Level 2 or 4 key/value
#         if ":" in stripped:
#
#             key, _, val = stripped.partition(":")
#             key = key.strip()
#             val = val.strip()
#
#             block = specs.setdefault(current_group, {})
#
#             # Merge Current | Voltage
#             if key == "Current | Voltage" and previous_key:
#                 key = f"{previous_key} {key}"
#
#             # Avoid duplicate keys
#             unique_key = key
#             counter = 2
#
#             while unique_key in block:
#                 unique_key = f"{key} #{counter}"
#                 counter += 1
#
#             block[unique_key] = val
#
#             previous_key = key
#
#     return specs
def _parse_specs_text(text: str) -> dict:
    specs = {}

    # Stack of (indent, dictionary, group_name)
    stack = [(-1, specs, None)]

    previous_key = ""

    for line in (text or "").splitlines():
        if not line.strip():
            continue

        stripped = line.strip()

        if stripped.startswith("Specifications") or stripped.startswith("⚠️"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        # ---------------------------------------------------------
        # Heading / group
        # ---------------------------------------------------------
        if ":" not in stripped:
            # Find the parent dictionary based on indentation
            while stack and indent <= stack[-1][0]:
                stack.pop()

            parent = stack[-1][1]

            group = stripped
            parent[group] = {}

            # This group becomes the current nesting level
            stack.append((indent, parent[group], group))

            previous_key = ""
            continue

        # ---------------------------------------------------------
        # Key / value
        # ---------------------------------------------------------
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()

        # Find the dictionary this key belongs to
        while stack and indent <= stack[-1][0]:
            stack.pop()

        block = stack[-1][1]

        # Merge "Current | Voltage" with previous key
        if key == "Current | Voltage" and previous_key:
            key = f"{previous_key} {key}"

        # Avoid duplicate keys
        unique_key = key
        counter = 2

        while unique_key in block:
            unique_key = f"{key} #{counter}"
            counter += 1

        block[unique_key] = val

        previous_key = key

    return specs

def scrape_arctic_product(page) -> dict:
    images = page.evaluate(ARCTIC_GET_IMAGES_JS) or []
    specs_text = page.evaluate(ARCTIC_GET_SPECS_JS) or ""
    features = page.evaluate(ARCTIC_GET_FEATURES_JS) or []
    description = page.evaluate(ARCTIC_GET_DESCRIPTION_JS) or ""

    title = ""

    el = (
            page.query_selector("h1")
            or page.query_selector('div[class*="product-detail-name"]')
    )

    if el:
        title = el.inner_text().strip()

    subtitle_el = (
            page.query_selector(".product-detail-name ~ p")
            or page.query_selector(".product-detail-name-subtitle")
            or page.query_selector('div[class*="product-detail-description-text"] p')
    )

    subtitle = subtitle_el.inner_text().strip() if subtitle_el else ""

    if subtitle and title:
        title = f"{title} - {subtitle}"

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


if __name__ == "__main__":
    #     specs_text = "Specifications:\n\nGeneral Specifications\n  TIM: MX-6 (0.8 g)\n  Warranty: 6 Years\n  Operating Ambient Temperature: 0—40 °C\n  Pump: 800–2800 rpm (PWM controlled)\n  Pump Current | Voltage: 0.35 A | 12 V DC\n  Cold Plate: Copper, Micro Skived Fins\n  Tube Length: 450 mm\n  Tube Diameter: Outer: 12.4 mm Inner: 6.0 mm\n  Weight: 1665 g\n  Compatibility\n    Intel: LGA1851, LGA1700\n    AMD: AM5, AM4\n    PI | NNPI: 330 | 238\n\n  Radiator\n    Material: Aluminium\n    Dimensions: 277 (L) x 120 (W) x 38 (H) mm\n\n  VRM Module\n    VRM Fan: 400–2500 rpm (PWM-controlled)\n    VRM Fan Current | Voltage: 0.05 A | 12 V DC\n    LEDs: 12x A-RGB Gen2 LEDs\n    LEDs Current | Voltage: 0.40 A | 5 V DC\n\n  Radiator Fan\n    General: 2x P12 Pro A-RGB\n    Speed: 600–3000 rpm\n    Airflow: 77 cfm | 131 m³/h3/h\n    Static Pressure: 6.9 mmH2O\n    Bearing: Fluid Dynamic Bearing\n    Bearing Current | Voltage: 0.33 A | 12 V DC\n    Connector: 4-Pin Fan Plug\n\n  RGB\n    LEDs: 12x A-RGB LEDs\n    LEDs Current | Voltage: 0.40 A | 5 V DC\n    Connector: 3-Pin A-RGB Plug + 3-Pin Socket\n\nPackaging\n  Width: 171 mm\n  Height: 142 mm\n  Length: 294 mm\n  Weight: 2.055 kg\n\n\nManufacturer Info\nManufacturer Info\n  Manufacturer: ARCTIC (HK) Ltd., Unit 3001-07, The Octagon, 6 Sha Tsui Road, Tsuen Wan NT, Hong Kong, hk@arctic.de\n  EU Representative: ARCTIC GmbH, Bevenroder Str. 149, 38108 Braunschweig, Germany, info@arctic.de, +49 531 60945294\n  EAN: 4895265000232\n  UPC: 840033402910"
    #     import json
    #     print(json.dumps(_parse_specs_text(specs_text), indent=4))
    pass