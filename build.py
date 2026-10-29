#!/usr/bin/env python3
"""Build script for Tianbei website.
Reads content/*.yaml + template.html, generates dist/ for Netlify publish.
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
                    item_indent = indent + 2
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
            <a href="#contact" class="p-link">{link_text}</a>
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
            <a href="#contact" class="p-link">{link_text}</a>
            <a href="https://wa.me/{wa}?text=Hi%20Anna%2C%20please%20send%20me%20the%20price%20for%20{prod_enc}." target="_blank" rel="noopener" class="wa-link">Get price on WhatsApp</a>
          </div>
        </div>
      </article>"""

    out = []
    for p in sorted(products, key=lambda x: x.get("weight", 99)):
        specs = "\n".join(
            '            <div class="p-spec"><dt>{}</dt><dd>{}</dd></div>'.format(
                esc(s["label"]), esc(s["value"])
            )
            for s in p.get("specs", [])
        )
        prod_enc = html.escape(p["name"], quote=True).replace(" ", "%20").replace("/", "%2F")
        tpl = swatch_tpl if p.get("visual") == "swatch" else card_tpl
        out.append(tpl.format(
            image=esc(p.get("image") or ""),
            alt=esc(p.get("image_alt") or p["name"]),
            name=esc(p["name"]),
            desc=esc(p.get("description", "")),
            specs=specs,
            link_text=esc(p.get("link_text", "Request datasheet →")),
            wa=wa_number,
            prod_enc=prod_enc,
        ))
    return "\n\n".join(out)


def main():
    site = mini_yaml(os.path.join(ROOT, "content", "site.yaml"))
    prod_dir = os.path.join(ROOT, "content", "products")
    products = [mini_yaml(os.path.join(prod_dir, f))
                for f in sorted(os.listdir(prod_dir)) if f.endswith(".yaml")]

    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        page = f.read()

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

    # assemble dist
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    # collect referenced media (template + content yaml) to keep dist lean
    used = set()
    for m in re.findall(r'images/[\w./-]+\.(?:jpg|jpeg|png|webp|mp4)', page):
        used.add(os.path.basename(m))
    for p in products:
        if p.get("image"):
            used.add(os.path.basename(p["image"]))

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
    for f in ["sitemap.xml", "robots.txt"]:
        if os.path.exists(os.path.join(ROOT, f)):
            shutil.copy2(os.path.join(ROOT, f), DIST)

    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)

    print("build ok:", sorted(os.listdir(DIST)))


if __name__ == "__main__":
    main()
