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
                page.get_by_role("link", name="Read the permanent comparison for TRAPPIST-1 e").click()
                page.get_by_role("heading", name="TRAPPIST-1 e measurements").wait_for()
                assert page.get_by_role("table").count() >= 2
                assert page.get_by_role("link", name="Agol et al. 2021").first.get_attribute("href").startswith("https://")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile-planet.png"), full_page=True)
                page.get_by_role("link", name="View the radius chart").click()
                assert page.locator("#metric").input_value() == "1"
                assert page.locator("#planet").input_value() == "TRAPPIST-1 e"
                assert "metric=radius" in page.url
                page.reload()
                page.get_by_text("Earth radii", exact=True).wait_for()
                page.locator("#search").fill("55 Cnc e")
                page.locator("#metric").select_option("2")
                page.get_by_role("heading", name="55 Cnc e · Orbital period").wait_for()
                assert "metric=orbital-period" in page.url
                page.get_by_role("link", name="Browse published measurements by planet").click()
                page.get_by_role("link", name="Orbital period", exact=True).click()
                page.get_by_role("navigation", name="Result pages").get_by_role("link", name="2", exact=True).click()
                page.locator(".planet-list li a").first.click()
                assert page.url.endswith("#orbital-period")
                assert page.get_by_role("heading", name="Orbital period in days").count() == 1
                assert not errors, errors
                browser.close()
            print("Browser checks passed: project subpath, source records, filters and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
