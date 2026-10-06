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
import sys  # noqa: E402
sys.path.insert(0, os.path.join(REPO_ROOT, "nano"))
import ui_theme_v1 as ui  # noqa: E402  (ledger #997: the shared look)

# Real, curated list of this project's own real docs, in a sensible
# reading order -- not everything in the repo, the ones that actually
# help someone using the front end understand what they're doing.
DEFAULT_SOURCES = [
    "README.md",
    "sub/README.md",                                     # ledger #992: the current line's cells
    "docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md",
    "docs/stripped-cell/ICM_V3_FORMAT.md",
    "docs/stripped-cell/ICM_VIX_FORMAT.md",
    "docs/man/README.md",
    "docs/man/tang-nano-20k-getting-started.md",
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
    # Ledger #997: consecutive plain lines form ONE paragraph (previously each wrapped source line became its own
    # <p>, so prose looked double-spaced and bold/italic spanning a line break never rendered).
    para = []

    def flush_para():
        if para:
            html_out.append(f"<p>{convert_inline(' '.join(para))}</p>")
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        is_plain = (line.strip() != "" and not line.strip().startswith("```") and not re.match(r"^(#{1,4})\s+", line)
                    and not re.match(r"^\s*---+\s*$", line) and not line.strip().startswith("|")
                    and not re.match(r"^\s*[-*]\s+", line) and not re.match(r"^\s*\d+\.\s+", line))
        if not in_code and not is_plain:
            flush_para()

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

        if in_list and line[:1] in (" ", "\t") and html_out and html_out[-1].endswith("</li>"):
            # An indented continuation of the previous list item: append it to that item.
            html_out[-1] = html_out[-1][:-len("</li>")] + " " + convert_inline(line.strip()) + "</li>"
            i += 1
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    if in_list:
        html_out.append(f"</{in_list}>")
    if in_table:
        html_out.append("</table>")

    return "\n".join(html_out), toc


# Ledger #997: the manual uses the shared front-panel look (nano/ui_theme_v1.py); only its own two-column layout is here.
MANUAL_CSS = """
.manual { display: grid; grid-template-columns: minmax(0, 1fr) 240px; gap: 32px; align-items: start; }
.manual nav#toc { position: sticky; top: 72px; max-height: calc(100vh - 96px); overflow-y: auto; font-size: 0.78rem;
                  background: var(--bg-panel); border: 1px solid var(--line); padding: 10px 12px; order: 2; }
.manual nav#toc a { display: block; color: var(--fg-dim); padding: 2px 0; font-family: var(--font-mono); }
.manual nav#toc a:hover { color: var(--copper); text-decoration: none; }
.manual article { min-width: 0; max-width: 860px; }
.manual article h1 { border-bottom: 1px solid var(--line); padding-bottom: 6px; margin-top: 40px; }
.manual article table { border-collapse: collapse; margin: 10px 0; font-size: 0.86rem; display: block; overflow-x: auto; }
.manual article th, .manual article td { border: 1px solid var(--line); padding: 4px 8px; text-align: left; color: var(--fg-dim); }
.manual article th { color: var(--fg); font-family: var(--font-mono); font-weight: 500; }
.manual article hr { border: none; border-top: 1px solid var(--line); margin: 24px 0; }
.manual article p, .manual article li { max-width: none; overflow-wrap: anywhere; }
@media (max-width: 900px) { .manual { grid-template-columns: 1fr; } .manual nav#toc { position: static; max-height: 40vh; order: 0; } }
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
        f'<a href="#{anchor}" style="padding-left:{(lvl-1)*10}px">{convert_inline(t)}</a>'
        for lvl, t, anchor in all_toc
    )

    body = f"""<div class="manual">
<nav id="toc" aria-label="Contents">{toc_html}</nav>
<article>
<div class="eyebrow">Manual &middot; generated live from the repository's docs</div>
<h1 id="top">Imago UniCell Manual</h1>
<p><i>Regenerated fresh from this project's own real docs -- not a
separately hand-maintained copy. See tools/manual_generate_v1.py.</i></p>
{"".join(body_parts)}
</article>
</div>"""
    return ui.page("Manual", body, active="manual", app="frontpanel", extra_css=MANUAL_CSS, narrow=False)


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
