"""frontend_v4.py = frontend_v3.py (untouched, imported) plus the Hex-N page THE FOUR MODELS (/hexn/models, nano/hexn_tab_v3.py, nano/hexn_models_v1.py): pick items from the four Hex-N models, get the build sheet,
run the Python models from the page (12 Nov 2026; Alan 08:56). Every other page is served by frontend_v3's handler unchanged. Run with: python3 nano/frontend_v4.py [port]   then http://localhost:7421/hexn/models"""
import http.server
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import frontend_v3 as F3  # noqa: E402
import hexn_tab_v3 as T3  # noqa: E402
import hexn_models_v1 as M  # noqa: E402


class FrontendHandler(F3.FrontendHandler):
    models = None

    def do_GET(self):
        if self.path == "/hexn/models":
            self._html_response(T3.page_hexn_models())
        elif self.path == "/hexn":
            self._html_response(T3.page_hexn_overview())
        else:
            F3.FrontendHandler.do_GET(self)

    def do_POST(self):
        if self.path == "/hexn/models":
            f = self._read_form_body(); self._html_response(T3.page_hexn_models(self.models.sheet(f), f))
        elif self.path == "/hexn/models/run":
            f = self._read_form_body(); self._html_response(T3.page_hexn_models(None, f, self.models.run(f)))
        else:
            F3.FrontendHandler.do_POST(self)


def serve(port: int = 7421, open_browser: bool = False) -> http.server.HTTPServer:
    FrontendHandler.controller = F3.FrontendController()
    FrontendHandler.hexn = F3.hexn_tab_v2.HexnController()
    FrontendHandler.composer = F3.composer_page_v1.ComposerController()
    FrontendHandler.models = M.ModelsController()
    server = http.server.HTTPServer(("localhost", port), FrontendHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if open_browser:
        webbrowser.open(f"http://localhost:{port}/hexn/models")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7421
    server = serve(port, open_browser=True)
    print(f"Imago UniCell front end (with the Hex-N models page) serving at http://localhost:{port}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
