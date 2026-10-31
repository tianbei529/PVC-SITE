#!/usr/bin/env python3
"""Build script for Tianbei website.
Reads content/*.yaml + templates, generates dist/ for Netlify publish.
"""
import html
import os
import re
import shutil


ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")


def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s


def mini_yaml(path):
    """Minimal YAML parser for the simple config files used by this site:
    nested dicts, lists of dicts, flat lists, scalar values."""
    with open(path, encoding="utf-8") as f:
        lines = [(len(l) - len(l.lstrip(" ")), l.strip())
                 for l in f if l.strip() and not l.strip().startswith("#")]

    def parse_block(i, indent):
        # decide list vs dict by first line
        if lines[i][1].startswith("- "):
            arr = []
            while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                first = lines[i][1][2:].strip()
                if ":" in first and not first.endswith(":"):
                    # list of dicts starting inline "- key: val"
                    d = {}
                    k, v = first.split(":", 1)
                    d[k.strip()] = _scalar(v) if v.strip() else None
                    i += 1
                    while i < len(lines) and lines[i][0] > indent and not lines[i][1].startswith("- "):
                        k2, v2 = lines[i][1].split(":", 1)
                        d[k2.strip()] = _scalar(v2) if v2.strip() else None
                        i += 1
                    arr.append(d)
                else:
                    arr.append(_scalar(first))
                    i += 1
            return arr, i
        else:
            d = {}
            while i < len(lines) and lines[i][0] == indent:
                line = lines[i][1]
                if ":" not in line:
                    i += 1
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v:
                    d[k] = _scalar(v)
                    i += 1
                else:
                    # nested block
                    if i + 1 < len(lines) and lines[i + 1][0] > indent:
                        d[k], i = parse_block(i + 1, lines[i + 1][0])
                    else:
                        d[k] = None
                        i += 1
            return d, i

    val, _ = parse_block(0, lines[0][0])
    return val


def esc(s):
    return html.escape(str(s), quote=False)


def txt(s):
    """Escape text for HTML body: only bare ampersands are escaped, so typographic
    entities (if any) survive while "&" never breaks validation."""
    return str(s).replace("&", "&amp;")


def wa_quote(name):
    """URL-encoded pre-filled WhatsApp message for a product name."""
    return html.escape(
        "Hi Anna, please send me the price and datasheet for " + name + ".",
        quote=True,
    ).replace(" ", "%20").replace("&amp;", "%26")


def build_products(products, wa_number):
    card_tpl = """      <article class="p-card reveal">
        <div class="p-visual">
          <img src="{image}" alt="{alt}" loading="lazy" style="width:100%;height:100%;object-fit:cover">
        </div>
        <div class="p-body">
          <h3 class="p-name">{name}</h3>
          <p class="p-desc">
            {desc}
          </p>
          <dl class="p-specs">
{specs}
          </dl>
          <div class="p-actions">
            <a href="{page}" class="p-link">{link_text}</a>
            <a href="https://wa.me/{wa}?text=Hi%20Anna%2C%20please%20send%20me%20the%20price%20for%20{prod_enc}." target="_blank" rel="noopener" class="wa-link">Get price on WhatsApp</a>
          </div>
        </div>
      </article>"""

    swatch_tpl = """      <article class="p-card reveal">
        <div class="p-visual" style="background:linear-gradient(160deg,#e9eef5,#d5dde8)">
          <div style="display:flex;gap:8px;align-items:flex-end">
            <div style="width:34px;height:88px;border-radius:4px;background:linear-gradient(160deg,#ffffff,#e8ecf1);box-shadow:0 12px 20px -8px rgba(15,20,25,.3)"></div>
            <div style="width:34px;height:104px;border-radius:4px;background:linear-gradient(160deg,#1f242b,#0d1117);box-shadow:0 12px 20px -8px rgba(15,20,25,.35)"></div>
            <div style="width:34px;height:72px;border-radius:4px;background:linear-gradient(160deg,#f59e0b,#d97706);box-shadow:0 12px 20px -8px rgba(15,20,25,.3)"></div>
            <div style="width:34px;height:96px;border-radius:4px;background:linear-gradient(160deg,#0b6bcb,#0752a0);box-shadow:0 12px 20px -8px rgba(15,20,25,.3)"></div>
          </div>
        </div>
        <div class="p-body">
          <h3 class="p-name">{name}</h3>
          <p class="p-desc">
            {desc}
          </p>
          <dl class="p-specs">
{specs}
          </dl>
          <div class="p-actions">
            <a href="{page}" class="p-link">{link_text}</a>
            <a href="https://wa.me/{wa}?text=Hi%20Anna%2C%20please%20send%20me%20the%20price%20for%20{prod_enc}." target="_blank" rel="noopener" class="wa-link">Get price on WhatsApp</a>
          </div>
        </div>
      </article>"""

    out = []
    for p in sorted(products, key=lambda x: int(x.get("weight", 99))):
        specs = "\n".join(
            '            <div class="p-spec"><dt>{}</dt><dd>{}</dd></div>'.format(
                esc(s["label"]), esc(s["value"])
            )
            for s in p.get("specs", [])
        )
        prod_enc = html.escape(p["name"], quote=True).replace(" ", "%20").replace("/", "%2F").replace("&amp;", "%26")
        tpl = swatch_tpl if p.get("visual") == "swatch" else card_tpl
        out.append(tpl.format(
            image=esc(p.get("image") or ""),
            alt=esc(p.get("image_alt") or p["name"]),
            name=esc(p["name"]),
            desc=esc(p.get("description", "")),
            specs=specs,
            link_text=esc(p.get("link_text", "Request datasheet →")),
            page=esc(p.get("page") or "index.html#products"),
            wa=wa_number,
            prod_enc=prod_enc,
        ))
    return "\n\n".join(out)


# --------------------------------------------------------------------------
# product detail pages
# --------------------------------------------------------------------------

PVC_TABLE = """            <table>
              <caption class="sr-only">PVC foam board specifications by thickness</caption>
              <thead>
                <tr>
                  <th scope="col">Thickness</th>
                  <th scope="col">Density (g/cm&sup3;)</th>
                  <th scope="col">Size (mm)</th>
                  <th scope="col">Weight (kg/sheet)</th>
                  <th scope="col">Surface</th>
                  <th scope="col">Typical use</th>
                </tr>
              </thead>
              <tbody>
                <tr><td class="mono">1.8 &ndash; 2 mm</td><td class="mono">0.50 &ndash; 0.75</td><td class="mono">1220 &times; 2440</td><td class="mono">5.4 &ndash; 7.5</td><td>Glossy</td><td>Indoor signage, POP display</td></tr>
                <tr><td class="mono">3 &ndash; 5 mm</td><td class="mono">0.45 &ndash; 0.70</td><td class="mono">1220 &times; 2440</td><td class="mono">8.0 &ndash; 15.0</td><td>Glossy / matte</td><td>UV printing, exhibition boards</td></tr>
                <tr><td class="mono">8 &ndash; 12 mm</td><td class="mono">0.40 &ndash; 0.65</td><td class="mono">1220 &times; 2440</td><td class="mono">19 &ndash; 39</td><td>Matte</td><td>Cabinet doors, furniture panels</td></tr>
                <tr><td class="mono">15 &ndash; 20 mm</td><td class="mono">0.30 &ndash; 0.60</td><td class="mono">1220 &times; 2440</td><td class="mono">30 &ndash; 60</td><td>Matte</td><td>Wet-area cabinets, partitions</td></tr>
              </tbody>
            </table>"""

ACRYLIC_TABLE = """            <table>
              <caption class="sr-only">Acrylic sheet specifications by thickness</caption>
              <thead>
                <tr>
                  <th scope="col">Thickness</th>
                  <th scope="col">Type</th>
                  <th scope="col">Size (mm)</th>
                  <th scope="col">Weight (kg/sheet)</th>
                  <th scope="col">Light transmission</th>
                  <th scope="col">Typical use</th>
                </tr>
              </thead>
              <tbody>
                <tr><td class="mono">1.8 &ndash; 2 mm</td><td>Cast / extruded</td><td class="mono">1220 &times; 2440</td><td class="mono">6.4 &ndash; 7.1</td><td>up to 92%</td><td>Light-box faces, posters</td></tr>
                <tr><td class="mono">3 &ndash; 5 mm</td><td>Cast / extruded</td><td class="mono">1220 &times; 2440</td><td class="mono">10.6 &ndash; 17.7</td><td>up to 92%</td><td>Signage, display stands, screens</td></tr>
                <tr><td class="mono">8 &ndash; 12 mm</td><td>Cast</td><td class="mono">1220 &times; 2440</td><td class="mono">28.3 &ndash; 42.5</td><td>up to 92%</td><td>Machine guards, furniture fronts</td></tr>
                <tr><td class="mono">15 &ndash; 20 mm</td><td>Cast</td><td class="mono">1220 &times; 2440</td><td class="mono">53.1 &ndash; 70.8</td><td>up to 92%</td><td>Bathroom panels, heavy glazing</td></tr>
              </tbody>
            </table>"""

APP_ICONS = [
    # signage
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>',
    # furniture
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 20V9l9-6 9 6v11"/><path d="M9 20v-6h6v6"/></svg>',
    # construction
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-4h6v4"/></svg>',
    # industrial
    '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>',
]


def _features(page):
    out = []
    for i in range(1, 5):
        t = page.get("feature_%d_t" % i)
        d = page.get("feature_%d_d" % i)
        if not t:
            continue
        out.append(
            '      <div class="feature-card">\n'
            '        <span class="fc-n">0%d</span>\n'
            '        <h3>%s</h3>\n'
            '        <p>%s</p>\n'
            '      </div>' % (i, txt(t), txt(d or ""))
        )
    return "\n".join(out)


def _applications(page):
    out = []
    for i in range(1, 5):
        t = page.get("app_%d_t" % i)
        d = page.get("app_%d_d" % i)
        if not t:
            continue
        out.append(
            '      <div class="app-card">\n'
            '        <div class="app-icon">%s</div>\n'
            '        <h3>%s</h3>\n'
            '        <p>%s</p>\n'
            '      </div>' % (APP_ICONS[(i - 1) % 4], txt(t), txt(d or ""))
        )
    return "\n".join(out)


def _related(page, wa_number):
    out = []
    for i in range(1, 4):
        n = page.get("rel_%d_name" % i)
        d = page.get("rel_%d_desc" % i)
        img = page.get("rel_%d_img" % i)
        if not n:
            continue
        out.append(
            '      <article class="rel-card">\n'
            '        <figure><img src="%s" alt="%s" loading="lazy"></figure>\n'
            '        <div class="rel-card-body">\n'
            '          <h3>%s</h3>\n'
            '          <p>%s</p>\n'
            '          <a href="https://wa.me/%s?text=Hi%%20Anna%%2C%%20please%%20send%%20me%%20the%%20price%%20for%%20%s." target="_blank" rel="noopener" class="wa-link" style="margin-top:16px">Ask for price on WhatsApp</a>\n'
            '        </div>\n'
            '      </article>' % (
                esc(img or ""), txt(n), txt(n), esc(d or ""), wa_number, wa_quote(n)
            )
        )
    return "\n".join(out)


def _faq_html(page):
    out = []
    for i in range(1, 4):
        q = page.get("faq_%d_q" % i)
        a = page.get("faq_%d_a" % i)
        if not q:
            continue
        out.append(
            '      <div class="faq-item">\n'
            '        <button class="faq-q" aria-expanded="false">%s</button>\n'
            '        <div class="faq-a"><p>%s</p></div>\n'
            '      </div>' % (txt(q), esc(a or ""))
        )
    return "\n".join(out)


def load_pages():
    page_dir = os.path.join(ROOT, "content", "pages")
    if not os.path.isdir(page_dir):
        return []
    return [mini_yaml(os.path.join(page_dir, f))
            for f in sorted(os.listdir(page_dir)) if f.endswith(".yaml")]


def build_product_pages(site, products, tpl):
    pages = load_pages()

    built = []
    start = 0
    for page in pages:
        url = page["url"]
        names = [n.strip() for n in page.get("series_names", "").split("|") if n.strip()]
        # 主站产品卡按 series_names 顺序匹配，筛选出属于本页的卡片
        all_sorted = sorted(products, key=lambda x: int(x.get("weight", 99)))
        group = all_sorted[start:start + len(names)]
        start += len(names)

        wa_text = html.escape(
            "Hi Anna, I'm interested in %s. Please send me your best price." % page["link_label"],
            quote=False).replace(" ", "%20").replace("'", "%27")

        addr = "<br>".join([site["address_en_1"], site["address_en_2"], site["address_en_3"]])

        if url.startswith("pvc"):
            table, ld_material, low, high, sku = PVC_TABLE, "Polyvinyl chloride (PVC) foam", "0.60", "3.90", "TB-PVC-FB"
        else:
            table, ld_material, low, high, sku = ACRYLIC_TABLE, "Polymethyl methacrylate (PMMA)", "2.20", "9.80", "TB-ACR-SH"

        reps = {
            "{{URL}}": esc(url),
            "{{META_TITLE}}": esc(page["meta_title"]),
            "{{META_DESCRIPTION}}": esc(page["meta_description"]),
            "{{META_KEYWORDS}}": esc(page.get("meta_keywords", "")),
            "{{LD_NAME}}": esc(page["link_label"] + " - Tianbei"),
            "{{LD_DESCRIPTION}}": esc(page["meta_description"]),
            "{{LD_MATERIAL}}": ld_material,
            "{{LD_LOW}}": low,
            "{{LD_HIGH}}": high,
            "{{SKU}}": sku,
            "{{HERO_IMAGE}}": esc(page["hero_image"]),
            "{{HERO_ALT}}": esc(page["hero_alt"]),
            "{{HERO_CHIP}}": esc(page["hero_chip"]),
            "{{HERO_BADGE}}": esc(page["hero_badge"]),
            "{{HERO_H1}}": esc(page["hero_h1"]),
            "{{HERO_SUB}}": txt(page["hero_sub"]),
            "{{HERO_LEDE}}": esc(page["hero_lede"]),
            "{{LINK_LABEL}}": esc(page["link_label"]),
            "{{INTRO_EYEBROW}}": esc(page["intro_eyebrow"]),
            "{{INTRO_H2}}": esc(page["intro_h2"]),
            "{{INTRO_P1}}": esc(page["intro_p1"]),
            "{{INTRO_P2}}": esc(page["intro_p2"]),
            "{{TABLE_H2}}": txt(page["table_h2"]),
            "{{TABLE_NOTE}}": esc(page["table_note"]),
            "{{REL_H2}}": esc(page["rel_h2"]),
            "{{FAQ_1_Q}}": esc(page["faq_1_q"]),
            "{{FAQ_1_A}}": esc(page["faq_1_a"]),
            "{{FAQ_2_Q}}": esc(page["faq_2_q"]),
            "{{FAQ_2_A}}": esc(page["faq_2_a"]),
            "{{FAQ_3_Q}}": esc(page["faq_3_q"]),
            "{{FAQ_3_A}}": esc(page["faq_3_a"]),
            "{{FEATURES}}": _features(page),
            "{{APPLICATIONS}}": _applications(page),
            "{{RELATED}}": _related(page, site["whatsapp_number"]),
            "{{FAQ_HTML}}": _faq_html(page),
            "{{TABLE}}": table,
            "{{CARDS}}": build_products(group, site["whatsapp_number"]),
            "{{WA_NUMBER}}": site["whatsapp_number"],
            "{{WA_TEXT}}": wa_text,
            "{{WHATSAPP_DISPLAY}}": esc(site["whatsapp_display"]),
            "{{PHONE_DISPLAY}}": esc(site.get("phone_display", site["whatsapp_display"])),
            "{{CONTACT_NAME}}": esc(site["whatsapp_name"]),
            "{{EMAIL}}": esc(site["email"]),
            "{{ADDRESS}}": addr,
        }
        htmlout = tpl
        for k, v in reps.items():
            htmlout = htmlout.replace(k, v)
        left = re.findall(r"\{\{[A-Z0-9_]+\}\}", htmlout)
        assert not left, "unreplaced markers in %s: %s" % (url, left)
        built.append((url, htmlout))
    return built


def write_sitemap(product_urls, today):
    urls = [("https://www.tianbeiplastic.com/", "1.0")]
    urls += [("https://www.tianbeiplastic.com/" + u, "0.9") for u in product_urls]
    urls += [
        ("https://www.tianbeiplastic.com/#products", "0.8"),
        ("https://www.tianbeiplastic.com/#applications", "0.8"),
        ("https://www.tianbeiplastic.com/#factory", "0.8"),
        ("https://www.tianbeiplastic.com/#faq", "0.7"),
        ("https://www.tianbeiplastic.com/#contact", "0.8"),
    ]
    items = [
        "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n    <priority>%s</priority>\n  </url>" % (u, today, p)
        for u, p in urls
    ]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(items) + "\n</urlset>\n")
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)


def main():
    import datetime
    today = datetime.date.today().isoformat()

    site = mini_yaml(os.path.join(ROOT, "content", "site.yaml"))
    prod_dir = os.path.join(ROOT, "content", "products")
    products = [mini_yaml(os.path.join(prod_dir, f))
                for f in sorted(os.listdir(prod_dir)) if f.endswith(".yaml")]

    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(ROOT, "template-product.html"), encoding="utf-8") as f:
        prod_tpl = f.read()

    # inject product cards
    cards_pvc = build_products([p for p in products if int(p["weight"]) <= 3], site["whatsapp_number"])
    cards_acr = build_products([p for p in products if int(p["weight"]) > 3], site["whatsapp_number"])
    assert "{{CARDS_PVC}}" in page and "{{CARDS_ACRYLIC}}" in page, "markers missing in template"
    page = page.replace("{{CARDS_PVC}}", cards_pvc)
    page = page.replace("{{CARDS_ACRYLIC}}", cards_acr)

    # site settings replacement (plain values, applied globally)
    page = page.replace("8615893110948", site["whatsapp_number"])
    page = page.replace("+86 158 9311 0948", site["whatsapp_display"])
    page = page.replace("anna@tianbeiplastic.com", site["email"])

    product_pages = build_product_pages(site, products, prod_tpl)

    # assemble dist
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    # collect referenced media (all html) to keep dist lean
    used = set()
    all_html = page + "".join(h for _, h in product_pages)
    for m in re.findall(r'images/[\w./-]+\.(?:jpg|jpeg|png|webp|mp4)', all_html):
        used.add(os.path.basename(m))

    for item in ["assets", "admin"]:
        src = os.path.join(ROOT, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(DIST, item))

    img_src = os.path.join(ROOT, "images")
    img_dst = os.path.join(DIST, "images")
    os.makedirs(img_dst, exist_ok=True)
    for f in sorted(used):
        fp = os.path.join(img_src, f)
        if os.path.exists(fp):
            shutil.copy2(fp, img_dst)
        else:
            print("WARNING missing image:", f)
    if os.path.exists(os.path.join(ROOT, "robots.txt")):
        shutil.copy2(os.path.join(ROOT, "robots.txt"), DIST)

    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)

    for url, htmlout in product_pages:
        with open(os.path.join(DIST, url), "w", encoding="utf-8") as f:
            f.write(htmlout)

    write_sitemap([u for u, _ in product_pages], today)

    print("build ok:", sorted(os.listdir(DIST)))


if __name__ == "__main__":
    main()
