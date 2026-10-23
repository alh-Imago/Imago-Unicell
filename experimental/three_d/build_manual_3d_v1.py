#!/usr/bin/env python3
"""experimental/three_d/build_manual_3d_v1.py -- bake the 3D kit's documents into ONE self-contained page, experimental/three_d/manual3d.html (ledger #1314).

Separate from docs/build_manual.py on purpose: the 3D kit has its own manual and is not part of the main one. Sources, in order: MANUAL_3D.md (the manual), ICM_3D_FORMAT.md (the file-format
specification), CELL_AUDIT_6_FACE.md (what each cell type needs for six faces). No runtime fetch, works from a double-click. Re-run after editing any of them, and commit the .html.

    python3 experimental/three_d/build_manual_3d_v1.py
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "docs"))
sys.path.insert(0, os.path.join(REPO, "nano"))
import build_manual as bm  # noqa: E402  (only its markdown renderer is used)
import ui_theme_v1 as ui  # noqa: E402

OUT = os.path.join(HERE, "manual3d.html")
SECTIONS = [("manual", "Manual", "MANUAL_3D.md"), ("icm3d", "ICM-3D v2 specification", "ICM_3D_FORMAT.md"), ("audit", "Cell audit: six faces", "CELL_AUDIT_6_FACE.md")]
CSS = """
.m3 { display: grid; grid-template-columns: 250px 1fr; gap: 28px; align-items: start; }
.m3 nav.toc { position: sticky; top: 64px; max-height: calc(100vh - 80px); overflow-y: auto; font-size: 14px; padding-right: 6px; }
.m3 nav.toc h4 { margin: 14px 0 4px; font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--fg-dim); }
.m3 nav.toc a { display: block; padding: 2px 0; color: var(--fg-dim); text-decoration: none; overflow-wrap: anywhere; }
.m3 nav.toc a:hover, .m3 nav.toc a.cur { color: var(--copper); }
.m3 nav.toc a.sub { padding-left: 12px; font-size: 13px; }
.m3 article { min-width: 0; max-width: var(--measure); }
.m3 article section { margin-bottom: 56px; padding-top: 8px; }
.m3 article table { border-collapse: collapse; display: block; overflow-x: auto; max-width: 100%; margin: 10px 0; }
.m3 article th, .m3 article td { border: 1px solid var(--line); padding: 5px 9px; text-align: left; vertical-align: top; font-size: 14px; }
.m3 article th { background: var(--bg-panel); }
.m3 article pre { background: var(--bg-input); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; overflow-x: auto; font-size: 13px; }
.m3 article code { font-family: var(--font-mono); font-size: .92em; }
.m3 article blockquote { border-left: 3px solid var(--copper); margin: 12px 0; padding: 4px 14px; color: var(--fg-dim); background: var(--bg-panel); }
@media (max-width: 860px) { .m3 { grid-template-columns: 1fr; } .m3 nav.toc { position: static; max-height: none; } }
"""


def slug(s, used):
    base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", s).lower()).strip("-") or "s"
    n, out = 1, base
    while out in used:
        n += 1
        out = "%s-%d" % (base, n)
    used.add(out)
    return out


def build():
    toc, body, used = [], [], set()
    for sid, title, fname in SECTIONS:
        with open(os.path.join(HERE, fname), encoding="utf-8") as f:
            h = bm.render_markdown(f.read())
        toc.append('<h4>%s</h4>' % html.escape(title))

        def fix(m):
            level, attrs, inner = m.group(1), m.group(2), m.group(3)
            if level in ("1", "2", "3") and "id=" not in attrs:
                i = slug(inner, used)
                if level in ("1", "2"):
                    toc.append('<a href="#%s"%s>%s</a>' % (i, ' class="sub"' if level == "2" else "", re.sub(r"<[^>]+>", "", inner)))
                return '<h%s id="%s"%s>%s</h%s>' % (level, i, attrs, inner, level)
            return m.group(0)
        h = re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", fix, h, flags=re.S)
        body.append('<section id="sec-%s">%s</section>' % (sid, h))
    page = ('<!doctype html><html lang="en"><head>%s</head><body>'
            '<header class="site"><div class="site-nav"><div class="brand"><span class="dot">&#9670;</span>IMAGO UNICELL <small>3D kit &middot; manual</small></div>'
            '<nav class="links"><a href="/">Composer</a></nav></div></header>'
            '<main><div class="wrap"><div class="m3"><nav class="toc" aria-label="contents">%s</nav><article>%s</article></div></div></main>'
            '<footer class="site"><div class="wrap"><span>Exploration only: no 3D hardware, no 3D RTL</span><span>separate from the main UniCell manual</span></div></footer></body></html>'
            % (ui.head("3D Kit manual", CSS), "".join(toc), "".join(body)))
    # the composer's "/" link only makes sense when served by it; opened as a file it points nowhere, which is harmless
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    return OUT, len(page)


if __name__ == "__main__":
    out, n = build()
    print("wrote %s (%d KB)" % (out, n // 1024))
