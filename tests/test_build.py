import json
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import ROOT, build, metadata


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / "web", self.root / "web")
        shutil.copyfile(ROOT / "tool.json", self.root / "tool.json")
        shutil.copyfile(ROOT / "README.md", self.root / "README.md")

    def edit(self, **changes):
        tool = json.loads((self.root / "tool.json").read_text())
        tool.update(changes)
        (self.root / "tool.json").write_text(json.dumps(tool))

    def test_build_is_scoped_to_web_and_escapes_metadata(self):
        (self.root / "private.txt").write_text("must not publish")
        self.edit(title='<img src=x onerror="bad()">')
        build(self.root)
        page = (self.root / "dist/index.html").read_text()
        self.assertIn('&lt;img', page)
        self.assertNotIn('<img', page)
        self.assertNotIn('{{', page)
        self.assertIn('href="./style.css"', page)
        self.assertFalse((self.root / "dist/private.txt").exists())
        self.assertTrue((self.root / "dist/.nojekyll").exists())

    def test_permanent_records_are_reachable_from_browse_and_match_the_sitemap(self):
        build(self.root)
        site = self.root / "dist"
        base = "https://coolcode.ca/planetpapers/"
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [el.text for el in ET.parse(site / "sitemap.xml").findall("s:url/s:loc", namespace)]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertTrue(all(url.startswith(base+"records/") for url in locations))
        expected = {url[len(base):] for url in locations} - {""}
        catalogue = json.loads((site / "data/catalogue.json").read_text())
        profiles = {"records/planets/"+slug+"/" for slug in catalogue["profiles"].values()}
        self.assertEqual(profiles, {p for p in expected if p.startswith("records/planets/")})
        self.assertLess(len(profiles), len(catalogue["names"]))
        seen, queue = set(), ["records/"]
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            seen.add(path)
            body = (site / path / "index.html").read_text()
            self.assertIn(f'<link rel="canonical" href="{base}{path}">', body)
            if path in profiles:
                continue  # All profiles must also be discoverable through the thematic directories.
            for relative in re.findall(r'<a href="([^"]+)"', body):
                url = urlsplit(urljoin(base+path, relative))
                if url.hostname == 'coolcode.ca' and url.path.startswith('/planetpapers/records/'):
                    queue.append(url.path[len('/planetpapers/'):])
        self.assertEqual(seen, expected)
        sample = (site / "records/planets/trappist-1-e/index.html").read_text()
        self.assertIn('0.692 ± 0.022 Earth masses', sample)
        self.assertIn('Gillon et al. 2017', sample)
        self.assertIn('Agol et al. 2021', sample)
        self.assertIn('metric=radius', sample)
        self.assertIn('Other planets in the same papers', sample)

    def test_url_matches_tool_id(self):
        self.edit(url="/different/")
        with self.assertRaises(ValueError): metadata(self.root)

    def test_requires_a_source_sentence_and_a_guide_note(self):
        (self.root / "README.md").write_text("# A tool")
        with self.assertRaisesRegex(ValueError, "README note"):
            metadata(self.root)
        self.edit(data_info={"mode": "local", "detail": ""})
        with self.assertRaisesRegex(ValueError, "homepage card"):
            metadata(self.root)

    def test_browser_access_is_explicit(self):
        self.edit(access="install")
        with self.assertRaisesRegex(ValueError, "immediately usable"):
            metadata(self.root)

    def test_failed_build_keeps_existing_output(self):
        build(self.root)
        existing = (self.root / "dist/index.html").read_bytes()
        self.edit(source="javascript:bad()")
        with self.assertRaises(ValueError): build(self.root)
        self.assertEqual((self.root / "dist/index.html").read_bytes(), existing)


if __name__ == "__main__": unittest.main()
