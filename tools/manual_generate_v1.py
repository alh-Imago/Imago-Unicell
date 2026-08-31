#!/usr/bin/env python3
"""
manual_generate_v1.py — points.md #558: Alan's own real idea, "one
button reuse of something built" -- rather than writing NEW help
content that could drift from the real docs, this tool concatenates
this project's own EXISTING, real markdown documentation into one
browsable HTML manual, regenerated fresh from the current repo state
every time it's asked for, never hand-maintained as a separate copy.

REAL, DELIBERATE SCOPE: no external dependency. Every other real tool
this project has built (`shape_extract_v1.py`, `project_assemble_v1.py`,
`frontend_v1.py`, `man_generate_v1.py`) is stdlib-only -- this matches
that discipline rather than adding a `markdown` package requirement
just for this. A real, minimal, regex-driven line-based converter,
the same general approach `shape_extract_v1.py` already established
for a different language (Verilog instead of Markdown). Handles the
real subset of Markdown syntax this project's own docs actually use:
headers, bold/italic, inline code, fenced code blocks, links, lists,
tables, horizontal rules, blockquotes. NOT a full CommonMark
implementation -- a real, working converter for THIS project's own
real content, not a general-purpose one.

Every `#`/`##`/`###` header gets a real, stable, slugified anchor ID,
so any other real tool (the frontend's own "Help" links, `#557`) can
link straight to a specific section rather than the top of a whole
document.
"""

import argparse
import html
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Real, curated list of this project's own real docs, in a sensible
# reading order -- not everything in the repo, the ones that actually
# help someone using the front end understand what they're doing.
DEFAULT_SOURCES = [
    "README.md",
    "docs/man/README.md",
    "docs/shapes/README.md",
    "tools/README.md",
    "docs/stripped-cell/SUPER_CELL_INTERNALS.md",
    "docs/stripped-cell/UNICELL_S_DSL_MANUAL.md",
]


def slugify(text):
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "section"


def convert_inline(line):
    """Real, minimal inline conversion -- bold, italic, inline code,
    links. Order matters: code first, so markup INSIDE a code span
    isn't itself converted."""
    # Inline code: `...`
    parts = re.split(r"(`[^`]+`)", line)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        p = html.escape(part)
        # Links: [text](url)
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', p)
        # Bold: **text**
        p = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", p)
        # Italic: *text* (after bold, so ** isn't eaten by *)
        p = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", p)
        out.append(p)
    return "".join(out)


def convert_markdown(text, doc_id):
    lines = text.split("\n")
    html_out = []
    toc = []
    in_code = False
    in_list = None  # 'ul' or 'ol' or None
    in_table = False
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if not in_code:
                html_out.append("<pre><code>")
                in_code = True
            else:
                html_out.append("</code></pre>")
                in_code = False
            i += 1
            continue
        if in_code:
            html_out.append(html.escape(line))
            i += 1
            continue

        header_match = re.match(r"^(#{1,4})\s+(.*)", line)
        if header_match:
            if in_list:
                html_out.append(f"</{in_list}>")
                in_list = None
            level = len(header_match.group(1))
            text_content = header_match.group(2).strip()
            anchor = f"{doc_id}-{slugify(text_content)}"
            html_out.append(f'<h{level} id="{anchor}">{convert_inline(text_content)}</h{level}>')
            toc.append((level, text_content, anchor))
            i += 1
            continue

        if re.match(r"^\s*---+\s*$", line) and line.strip() != "":
            html_out.append("<hr>")
            i += 1
            continue

        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            if not in_table:
                html_out.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            html_out.append("<tr>" + "".join(f"<th>{convert_inline(c)}</th>" for c in cells) + "</tr>")
            i += 2  # skip the separator row
            continue
        if in_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            html_out.append("<tr>" + "".join(f"<td>{convert_inline(c)}</td>" for c in cells) + "</tr>")
            i += 1
            continue
        if in_table and not line.strip().startswith("|"):
            html_out.append("</table>")
            in_table = False

        list_match = re.match(r"^\s*[-*]\s+(.*)", line)
        num_match = re.match(r"^\s*\d+\.\s+(.*)", line)
        if list_match:
            if in_list != "ul":
                if in_list:
                    html_out.append(f"</{in_list}>")
                html_out.append("<ul>")
                in_list = "ul"
            html_out.append(f"<li>{convert_inline(list_match.group(1))}</li>")
            i += 1
            continue
        if num_match:
            if in_list != "ol":
                if in_list:
                    html_out.append(f"</{in_list}>")
                html_out.append("<ol>")
                in_list = "ol"
            html_out.append(f"<li>{convert_inline(num_match.group(1))}</li>")
            i += 1
            continue
        if in_list and line.strip() == "":
            html_out.append(f"</{in_list}>")
            in_list = None

        if line.strip() == "":
            i += 1
            continue

        html_out.append(f"<p>{convert_inline(line)}</p>")
        i += 1

    if in_list:
        html_out.append(f"</{in_list}>")
    if in_table:
        html_out.append("</table>")

    return "\n".join(html_out), toc


MANUAL_CSS = """
<style>
body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #222; line-height: 1.6; }
nav#toc { position: fixed; top: 20px; right: 20px; width: 220px; font-size: 0.8em; max-height: 90vh; overflow-y: auto; background: #fafafa; padding: 10px; border: 1px solid #ddd; }
nav#toc a { display: block; text-decoration: none; color: #444; padding: 2px 0; }
main { margin-right: 250px; }
code { background: #f0f0f0; padding: 1px 4px; }
pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
table { border-collapse: collapse; margin: 10px 0; }
th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; }
hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
h1 { border-bottom: 2px solid #333; padding-bottom: 6px; margin-top: 40px; }
</style>
"""


def generate_manual(source_paths):
    body_parts = []
    all_toc = []
    for idx, rel_path in enumerate(source_paths):
        abs_path = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(abs_path):
            continue
        with open(abs_path) as f:
            text = f.read()
        doc_id = f"doc{idx}"
        body_html, toc = convert_markdown(text, doc_id)
        body_parts.append(f'<section data-source="{rel_path}">\n{body_html}\n</section>')
        all_toc.extend(toc)

    toc_html = "\n".join(
        f'<a href="#{anchor}" style="margin-left:{(lvl-1)*10}px">{convert_inline(t)}</a>'
        for lvl, t, anchor in all_toc
    )

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Imago UniCell Manual</title>{MANUAL_CSS}</head>
<body>
<nav id="toc">{toc_html}</nav>
<main>
<h1 id="top">Imago UniCell Manual</h1>
<p><i>Regenerated fresh from this project's own real docs -- not a
separately hand-maintained copy. See tools/manual_generate_v1.py.</i></p>
{"".join(body_parts)}
</main>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", default=None, help="Write to a file instead of stdout")
    ap.add_argument("--sources", nargs="*", default=None, help="Override the default doc list")
    args = ap.parse_args()

    out = generate_manual(args.sources or DEFAULT_SOURCES)
    if args.output:
        with open(args.output, "w") as f:
            f.write(out)
        print(f"Wrote {args.output}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
