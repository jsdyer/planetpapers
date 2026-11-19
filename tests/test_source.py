from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from refresh import improvement, relative_width


class SourceTests(unittest.TestCase):
    def test_limits_and_ambiguous_endpoints_excluded(self):
        self.assertIsNone(relative_width([1, 0.1, -0.1, 1]))
        self.assertIsNone(relative_width([1, None, -0.1, 0]))
        rows = [[1,"2015",0,[1,.2,-.2,0]], [2,"2021",0,[1,.05,-.05,0]]]
        self.assertEqual(improvement(rows,0),4)
        self.assertIsNone(improvement(rows+[ [3,"2021",0,[1,.1,-.1,0]] ],0))

    def test_snapshot_counts_and_links(self):
        folder = ROOT / "web/data"
        info = json.loads((folder/"index.json").read_text())
        catalogue = json.loads(gzip.decompress((folder/"catalogue.json.gz").read_bytes()))
        counts = Counter()
        for path in folder.glob("solutions-*.json.gz"):
            shard = int(path.name.split("-")[1].split(".")[0])
            for name, rows in json.loads(gzip.decompress(path.read_bytes())).items():
                self.assertEqual(catalogue["names"][name], shard)
                counts[name] += len(rows)
                self.assertTrue(all(catalogue["references"][row[0]][1].startswith(("http://","https://")) for row in rows))
        self.assertGreaterEqual(counts["TRAPPIST-1 e"],3)
        self.assertEqual(sum(counts.values()),info["count"])
        self.assertEqual(len(counts),info["planets"])
