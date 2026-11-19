"""Exercise the built explorer at a project subpath in Chromium."""
from functools import partial
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.get_by_text("0.692 ± 0.022", exact=True).wait_for()
                assert page.locator("#plot .dot").count() >= 3
                assert page.locator("#plot").get_by_text("Not reported").count() >= 2
                page.locator("#metric").select_option("1")
                page.get_by_text("Earth radii", exact=True).wait_for()
                page.locator("#search").fill("doesnotexist-example")
                page.get_by_text("No matching planet", exact=True).wait_for()
                page.locator("#search").fill("TRAPPIST-1 e")
                page.locator("#metric").select_option("0")
                page.get_by_text("0.692 ± 0.022", exact=True).wait_for()
                page.locator("details summary").click()
                page.locator("#ranking button").first.click()
                page.locator("#plot .dot").first.wait_for()
                page.locator("details summary").click()
                page.locator("#search").fill("TRAPPIST-1 e")
                page.get_by_text("0.692 ± 0.022", exact=True).wait_for()
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: project subpath, source records, filters and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
