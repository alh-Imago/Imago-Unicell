"""hexn_tab_v3.py = hexn_tab_v2.py (untouched, imported) plus THE FOUR MODELS page (/hexn/models): pick items from the four Hex-N models, set a few options, get the build sheet (the exact commands in order, with the
result on record), and run the Python models from the page (12 Nov 2026; Alan 08:56). The work is done by nano/hexn_models_v1.py. Importing this module adds 'The four models' to the Hex-N sub-menu of every Hex-N page
(a change in memory only; hexn_tab_v2.py run on its own is as before)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hexn_tab_v2 as T2  # noqa: E402
import hexn_models_v1 as M  # noqa: E402
import ui_theme_v1 as ui  # noqa: E402

if not any(k == "models" for k, _, _ in T2.SUBTABS):
    T2.SUBTABS.insert(1, ("models", "The four models", "/hexn/models"))
_e = T2._e

CSS = """fieldset.model { border: 1px solid var(--line); margin: 14px 0; padding: 10px 14px; max-width: var(--measure); } fieldset.model legend { font-weight: 600; padding: 0 6px; }
fieldset.model label.pick { display: block; margin: 5px 0; } fieldset.model label.pick input { width: auto; margin-right: 8px; } .tag { font-family: var(--font-mono); font-size: 0.74rem; color: var(--fg-faint); margin-left: 6px; }
.opts label { display: inline-block; margin: 4px 14px 4px 0; } .opts input, .opts select { width: auto; } .sheet h2 { margin-top: 1.2em; } .sheet pre { white-space: pre-wrap; word-break: break-word; }
form.runnow { display: inline; } pre.out { max-height: 60vh; overflow: auto; white-space: pre; }"""


def page_hexn_overview():
    extra = '<p><b>New:</b> <a href="/hexn/models">The four models</a> &mdash; pick what you want from the four Hex-N models (layered, detector and speech chain, neural bus network, upper logic), get the build sheet, and run the Python models from the page.</p>'
    return T2.page_hexn_overview().replace("<h1>Hex-N</h1>", "<h1>Hex-N</h1>" + extra, 1)


def _checked(f, name, default=False):
    return " checked" if (f.get(name) if f else default) else ""


def _form(f):
    f = f or {}
    out = []
    for m in M.MODELS:
        rows = "".join('<label class="pick"><input type="checkbox" name="pick_%s"%s>%s<span class="tag">[%s]</span></label>' % (i["key"], _checked(f, "pick_" + i["key"]), _e(i["label"]), _e(i["tag"]))
                       for i in M.ITEMS if i["model"] == m["n"])
        out.append('<fieldset class="model"><legend>Model %d: %s</legend><p>%s<br><span class="tag" style="margin-left:0">%s &middot; base document: <code>%s</code></span></p>%s</fieldset>'
                   % (m["n"], _e(m["name"]), _e(m["what"]), _e(m["state"]), _e(m["doc"]), rows))
    arr = "".join('<label><input type="checkbox" name="arr_%s"%s> %s</label>' % (a, _checked(f, "arr_" + a, a in ("hex7_off2_mix", "hex6")), a) for a in M.ARRAYS)
    sel = lambda name, items, cur: '<select name="%s">%s</select>' % (name, "".join('<option value="%s"%s>%s</option>' % (_e(k), " selected" if k == cur else "", _e(v)) for k, v in items))
    opts = """<fieldset class="model opts"><legend>Options (used by the items that need them)</legend>
<label>Seeds for the Python models (1 to 5; the recorded figures used 5) <input name="seeds" size="2" value="%s"></label>
<label>Games per match (Model 1) <input name="games" size="4" value="%s"></label><br>
<label>Pattern arrays in the base (card builds):</label> %s<br>
<label>Speech test after the build %s</label><br>
<label>Bus network shape %s</label> <label>version %s</label><br>
<label>Build folder on the big disk <input name="out" size="42" value="%s"></label><br>
<label>Speech data folder (shd_train.h5, shd_test.h5) <input name="data" size="30" value="%s"></label></fieldset>""" % (
        _e(f.get("seeds", "1")), _e(f.get("games", "20")), arr,
        sel("speech_test", (("full", "the whole test set (1,079 recordings)"), ("kitram", "the kit's 300 from the on-chip event memory"), ("kit", "the kit's 300 sent command by command")), f.get("speech_test", "full")),
        sel("shape", list(M.SHAPES.items()), f.get("shape", "8:8:48:3")), sel("netv", [(v, v) for v in M.NETV], f.get("netv", "v5")),
        _e(f.get("out", "/media/alan/InternalHDD/hexn_builds")), _e(f.get("data", "~/shd")))
    return '<form class="tool" method="post" action="/hexn/models">%s%s<button type="submit" class="primary">Make the build sheet</button></form>' % ("".join(out), opts)


def _hidden(f, key):
    keep = ("seeds", "games", "out", "data", "shape", "netv", "speech_test") + tuple("arr_" + a for a in M.ARRAYS)
    return '<input type="hidden" name="key" value="%s">' % _e(key) + "".join('<input type="hidden" name="%s" value="%s">' % (k, _e(f[k])) for k in keep if f.get(k))


def _sheet(res, f):
    if not res["ok"]:
        return T2._err(res)
    parts = ['<div class="result ok sheet"><b>Build sheet</b> for %d item(s). Card builds are not started from this page and nothing is sent to a card; the commands are for the terminal, in this order.' % len(res["items"])]
    for it in res["items"]:
        run = ('<form class="runnow" method="post" action="/hexn/models/run">%s<button type="submit">Run it now</button></form> <span class="tag">the page waits until it has finished</span>' % _hidden(f, it["key"])) if it["runnable"] else ""
        parts.append("<h2>Model %d: %s <span class=\"tag\">[%s]</span></h2><pre>%s</pre>%s<p>%s</p>%s" % (
            it["model"], _e(it["label"]), _e(it["tag"]), _e("\n".join(it["commands"])), run, _e(it["expect"] or ""), "".join("<p>%s</p>" % _e(n) for n in it["notes"])))
    return "".join(parts) + "</div>"


def page_hexn_models(result=None, fields=None, run_result=None):
    r = ""
    if run_result is not None:
        r = T2._err(run_result) if not run_result["ok"] else '<div class="result %s"><b>%s</b><br><code>%s</code> (exit %d)<pre class="out">%s</pre></div>' % (
            "ok" if run_result["code"] == 0 else "err", _e(run_result["label"]), _e(run_result["command"]), run_result["code"], _e(run_result["output"]))
    elif result is not None:
        r = _sheet(result, fields or {})
    return ui.page("Hex-N: the four models", T2._sub("models") + """<h1>The four models</h1>
<p>Tick what you want from the four Hex-N models and press the button. You get a <b>build sheet</b>: the exact commands, in order, for each item, with the result that is on record for that choice.
The Python models can also be run from this page. <b>Card builds are never started here</b> (they need the openXC7 shell and take minutes to an hour), and nothing is sent to a card.
The words in square brackets say where each item has been shown to work. The figures quoted are copied from the base documents in <code>docs/hex-n/</code>.</p>
%s<style>%s</style>%s""" % (r, CSS, _form(fields)), active="hexn")
