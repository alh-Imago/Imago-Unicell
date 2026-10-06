"""
ui_theme_v1.py -- one look for every local browser tool (ledger #997).

Before this, each tool styled itself: the front panel (`frontend_v1.py`)
was plain light, the workbench (`workbench_v1.py`) dark Courier with
cyan, and the live manual (`tools/manual_generate_v1.py`) light with a
fixed contents box. Alan: "make the look consistent across all the
pages, it was sort of hashed together". This module holds the one
stylesheet and the one header/footer they all use, in the design
language of the public site (`gh-pages`): a dark board-green background
with a faint grid, copper/gold accents, and IBM Plex Mono / Sans
(loaded from Google Fonts when online, falling back to system fonts
offline).

Only presentation lives here. No page logic, form field, element id or
endpoint is defined in this module, so restyling cannot change what a
tool does.

The front panel and the workbench are two separate local servers (ports
7421 and 7420 by default). The shared navigation links across them by
absolute URL; the ports are the constants below.
"""

FRONTPANEL_PORT = 7421
WORKBENCH_PORT = 7420
FRONTPANEL_URL = f"http://localhost:{FRONTPANEL_PORT}"
WORKBENCH_URL = f"http://localhost:{WORKBENCH_PORT}"

FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
    '&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">'
)

THEME_CSS = """
:root {
  --bg: #0e130f; --bg-panel: #161d18; --bg-panel-2: #1c241d; --bg-input: #0b100c;
  --line: #2a352c; --line-soft: #1f2921;
  --fg: #e9ede6; --fg-dim: #9aab98; --fg-faint: #627262;
  --copper: #c17f45; --copper-dim: #8a5c30; --gold: #d9b46a;
  --ok: #7fae7a; --ok-bg: #18241a; --warn: #c1a145; --warn-bg: #241f15; --err: #d0786a; --err-bg: #2a1a17;
  --in: #7fa6d0;
  --font-mono: 'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
  --font-sans: 'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, sans-serif;
  --measure: 760px; --wide: 1180px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  background-image: linear-gradient(var(--line-soft) 1px, transparent 1px),
                    linear-gradient(90deg, var(--line-soft) 1px, transparent 1px);
  background-size: 28px 28px; background-position: -1px -1px;
  font-family: var(--font-sans); font-size: 15px; line-height: 1.6; -webkit-font-smoothing: antialiased;
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; scroll-behavior: auto !important; } }
a { color: var(--copper); text-decoration: none; }
a:hover { color: var(--gold); text-decoration: underline; }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--gold); outline-offset: 2px;
}
h1, h2, h3 { font-family: var(--font-mono); font-weight: 600; letter-spacing: -0.01em; color: var(--fg); margin: 0 0 0.5em; }
h1 { font-size: 1.7rem; line-height: 1.2; }
h2 { font-size: 1.15rem; margin-top: 2em; }
h3 { font-size: 0.95rem; color: var(--copper); }
p, li { color: var(--fg-dim); }
p { max-width: var(--measure); margin: 0 0 1em; }
b, strong { color: var(--fg); }
code, .mono, pre, kbd { font-family: var(--font-mono); }
code { font-size: 0.88em; color: var(--gold); overflow-wrap: anywhere; }
pre code { overflow-wrap: normal; }
pre { background: var(--bg-input); border: 1px solid var(--line); padding: 12px 14px; overflow-x: auto;
      font-size: 0.82rem; color: var(--fg-dim); white-space: pre; }
pre code { color: inherit; }

/* header / nav / footer */
header.site { border-bottom: 1px solid var(--line); position: sticky; top: 0; z-index: 20;
              background: rgba(14,19,15,0.94); backdrop-filter: blur(6px); }
.site-nav { max-width: var(--wide); margin: 0 auto; padding: 12px 24px; display: flex; align-items: center;
            justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.brand { font-family: var(--font-mono); font-weight: 600; color: var(--fg); display: flex; align-items: baseline; gap: 8px; }
.brand .dot { color: var(--copper); }
.brand small { color: var(--fg-faint); font-weight: 400; font-size: 0.75rem; }
nav.links { display: flex; gap: 18px; flex-wrap: wrap; align-items: center; }
nav.links a { color: var(--fg-dim); font-family: var(--font-mono); font-size: 0.82rem; letter-spacing: 0.02em; }
nav.links a:hover { color: var(--copper); text-decoration: none; }
nav.links a.active { color: var(--fg); border-bottom: 1px solid var(--copper); }
nav.links .sep { width: 1px; height: 14px; background: var(--line); }
.menu-toggle { display: none; }
@media (max-width: 700px) {
  nav.links { display: none; width: 100%; flex-direction: column; align-items: flex-start; gap: 6px; }
  nav.links.open { display: flex; }
  nav.links .sep { display: none; }
  .menu-toggle { display: inline-flex; background: none; border: 1px solid var(--line); color: var(--fg);
                 font-family: var(--font-mono); padding: 5px 10px; cursor: pointer; margin: 0; }
}
main { padding: 32px 0 48px; }
.wrap { max-width: var(--wide); margin: 0 auto; padding: 0 24px; }
.wrap.narrow { max-width: calc(var(--measure) + 48px); }
footer.site { border-top: 1px solid var(--line); padding: 18px 0 28px; color: var(--fg-faint);
              font-family: var(--font-mono); font-size: 0.75rem; }
footer.site .wrap { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.eyebrow { font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
           color: var(--fg-faint); display: flex; align-items: center; gap: 0.6em; margin-bottom: 0.7em; }
.eyebrow::before { content: ""; width: 7px; height: 7px; background: var(--copper); transform: rotate(45deg); }
.help { float: right; font-size: 1.1rem; text-decoration: none; color: var(--fg-faint); }
.help:hover { color: var(--gold); text-decoration: none; }

/* panels, notes, results */
.panel { background: var(--bg-panel); border: 1px solid var(--line); padding: 16px 18px; margin-bottom: 14px; }
.panel h3 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
.note, .real, .placeholder { border: 1px solid var(--line); border-left: 3px solid var(--fg-faint);
        background: var(--bg-panel); padding: 10px 14px; margin: 14px 0; color: var(--fg-dim); max-width: var(--measure); }
.real, .note.ok { border-left-color: var(--ok); }
.placeholder, .note.warn { border-left-color: var(--warn); background: var(--warn-bg); }
.result { margin: 18px 0; padding: 12px 14px; border: 1px solid var(--line); max-width: var(--measure); }
.result.ok { border-left: 3px solid var(--ok); background: var(--ok-bg); }
.result.err { border-left: 3px solid var(--err); background: var(--err-bg); }
.result h2 { margin-top: 0.8em; }
.muted { color: var(--fg-faint); font-size: 0.85em; }
.status { color: var(--in); font-size: 0.85em; }
.error-text { color: var(--err); }
.hint-text { color: var(--warn); }

/* tables */
table.fields { width: 100%; max-width: var(--measure); border-collapse: collapse; font-size: 0.86rem; margin: 8px 0 18px; }
table.fields th { text-align: left; font-family: var(--font-mono); font-weight: 500; color: var(--fg-faint);
                  font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--line); padding: 6px 8px; }
table.fields td { border-bottom: 1px solid var(--line-soft); padding: 6px 8px; color: var(--fg-dim); vertical-align: top; }
table.fields td:first-child { color: var(--fg); white-space: nowrap; }
@media (max-width: 700px) { table.fields { display: block; overflow-x: auto; } table.fields td:first-child { white-space: normal; } }

/* forms */
form.tool { max-width: var(--measure); }
label { display: block; margin-top: 12px; font-size: 0.85rem; color: var(--fg-dim); }
label.inline { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; }
input, select, textarea {
  font: inherit; font-size: 0.88rem; color: var(--fg); background: var(--bg-input);
  border: 1px solid var(--line); padding: 6px 8px; border-radius: 0;
}
form.tool input:not([type=checkbox]):not([type=radio]), form.tool select, form.tool textarea { width: 100%; margin-top: 3px; display: block; }
textarea { font-family: var(--font-mono); font-size: 0.82rem; }
input[type=checkbox], input[type=radio] { accent-color: var(--copper); width: auto; }
input:focus, select:focus, textarea:focus { border-color: var(--copper-dim); outline: none; }
button, .btn {
  font-family: var(--font-mono); font-size: 0.82rem; color: var(--fg); background: transparent;
  border: 1px solid var(--copper-dim); padding: 7px 14px; margin: 6px 6px 6px 0; cursor: pointer; display: inline-block;
}
button:hover, .btn:hover { border-color: var(--gold); color: var(--gold); background: var(--bg-panel-2); text-decoration: none; }
button.primary { border-color: var(--copper); background: rgba(193,127,69,0.12); }
button.danger { border-color: #6a3a30; }
button.danger:hover { border-color: var(--err); color: var(--err); }
form.tool button[type=submit] { margin-top: 20px; }
"""

_MENU_JS = """<script>
document.addEventListener('DOMContentLoaded', function () {
  var t = document.querySelector('.menu-toggle'), l = document.querySelector('nav.links');
  if (t && l) t.addEventListener('click', function () {
    l.classList.toggle('open'); t.setAttribute('aria-expanded', l.classList.contains('open') ? 'true' : 'false');
  });
});
</script>"""

# (key, label, path, which server serves it)
NAV_ITEMS = [
    ("start", "Start", "/", "frontpanel"),
    ("man", "1. Card / MAN", "/man", "frontpanel"),
    ("cells", "2. Create cells", "/cells", "frontpanel"),
    ("walker", "3. Walker", "/walker", "frontpanel"),
    ("menu", "4. Other tools", "/menu", "frontpanel"),
    (None, None, None, None),
    ("workbench", "Workbench", "/", "workbench"),
    ("manual", "Manual", "/manual", "frontpanel"),
]


def _href(path: str, server: str, app: str) -> str:
    if server == app:
        return path
    return (FRONTPANEL_URL if server == "frontpanel" else WORKBENCH_URL) + path


def header(active: str = "", app: str = "frontpanel") -> str:
    """The shared site header. `app` is the server rendering the page, so links to the other server are absolute."""
    links = []
    for key, label, path, server in NAV_ITEMS:
        if key is None:
            links.append('<span class="sep" aria-hidden="true"></span>')
            continue
        cls = ' class="active"' if key == active else ""
        cur = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{_href(path, server, app)}"{cls}{cur}>{label}</a>')
    return (
        '<header class="site"><div class="site-nav">'
        '<div class="brand"><span class="dot">&#9670;</span>IMAGO UNICELL <small>front panel</small></div>'
        '<button class="menu-toggle" aria-expanded="false" aria-label="Toggle navigation">MENU</button>'
        f'<nav class="links">{"".join(links)}</nav>'
        '</div></header>'
    )


def footer() -> str:
    return (
        '<footer class="site"><div class="wrap">'
        f'<span>FRONT PANEL {FRONTPANEL_URL.split("//")[1]} &middot; WORKBENCH {WORKBENCH_URL.split("//")[1]}</span>'
        '<span>every action here also has a command-line equivalent</span>'
        '</div></footer>'
    )


def head(title: str, extra_css: str = "") -> str:
    return (
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{title} — Imago UniCell</title>{FONTS_LINK}'
        f'<style>{THEME_CSS}{extra_css}</style>'
    )


def page(title: str, body: str, active: str = "", app: str = "frontpanel", extra_css: str = "", narrow: bool = True) -> str:
    """A complete themed page: head, shared header, the page body inside the content column, shared footer."""
    wrap = "wrap narrow" if narrow else "wrap"
    return (
        f'<!doctype html><html lang="en"><head>{head(title, extra_css)}</head><body>'
        f'{header(active, app)}<main><div class="{wrap}">{body}</div></main>{footer()}{_MENU_JS}</body></html>'
    )
