#!/usr/bin/env python3
"""Tiny markdown -> HTML converter for blog posts (headings, paragraphs,
bullet/numbered lists, tables, bold, links, images). No external deps."""

import html as _html
import re


def _inline(s):
    s = _html.escape(s, quote=False)
    # bold **text**
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    # links [text](url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def md_to_html(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)

    def flush_table(rows):
        # rows: list of cell-lists; row[0] is header
        if not rows:
            return
        h = ['<div class="table-wrap"><div class="table-scroll"><table><thead><tr>']
        h += ["<th>%s</th>" % _inline(c) for c in rows[0]]
        h.append("</tr></thead><tbody>")
        for r in rows[1:]:
            h.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
        h.append("</tbody></table></div></div>")
        out.append("".join(h))

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = _inline(m.group(2))
            tag = {1: "h2", 2: "h2", 3: "h3", 4: "h3"}[level]
            out.append("<%s>%s</%s>" % (tag, text, tag))
            i += 1
            continue

        # table
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            rows = []
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows.append(header)
            i += 2  # skip separator
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            flush_table(rows)
            continue

        # bullet list
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append("<li>%s</li>" % _inline(re.sub(r"^[-*]\s+", "", lines[i].strip())))
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # numbered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append("<li>%s</li>" % _inline(re.sub(r"^\d+\.\s+", "", lines[i].strip())))
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # blockquote
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % _inline(" ".join(buf)))
            continue

        # image alone on a line
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if m:
            out.append('<figure><img src="%s" alt="%s" loading="lazy"></figure>'
                       % (_html.escape(m.group(2), quote=True), _html.escape(m.group(1), quote=True)))
            i += 1
            continue

        # paragraph (accumulate until blank / special)
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#{1,4}\s|[-*]\s|\d+\.\s|\||>)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % _inline(" ".join(buf)))

    return "\n".join(out)
