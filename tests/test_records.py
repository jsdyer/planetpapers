from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from records import comparable, grouped, slugs, uncertainty


class RecordRules(unittest.TestCase):
    def test_three_dated_sources_must_report_distinct_point_estimates(self):
        refs = [['A','https://example.org/a'], ['B','https://example.org/b'], ['C','https://example.org/c']]
        rows = [[i, f'202{i}-01', 0, [1, None, None, 0]] for i in range(3)]
        def result():
            return comparable(grouped(rows, refs, 0), refs)
        self.assertIsNone(result())
        rows[2][3][0] = 2
        self.assertEqual([r[3][0] for r in result()], [1, 2])
        rows[2][3][3] = 1
        self.assertIsNone(result())
        rows[2][3][3] = None
        self.assertIsNone(result())
        rows[2][3][3] = 0
        rows[2][1] = ''
        self.assertIsNone(result())
        rows[2][1] = '2022'
        refs[2][1] = refs[1][1]
        self.assertIsNone(result())

    def test_new_punctuation_collision_preserves_existing_and_retired_names(self):
        original = slugs(['TRAPPIST-1 e', 'A B'])
        new = slugs(['A/B', 'TRAPPIST-1 e'], original)
        self.assertEqual(new['A B'], 'a-b')
        self.assertTrue(new['A/B'].startswith('a-b--'))
        self.assertEqual(new['TRAPPIST-1 e'], 'trappist-1-e')
        self.assertEqual(slugs(['A B','A/B'], new), new)

    def test_missing_and_asymmetric_uncertainty(self):
        self.assertEqual(uncertainty([1,None,None,0]), 'Unreported')
        self.assertEqual(uncertainty([1,None,-0.2,0]), '+? / −0.2')
        self.assertEqual(uncertainty([1,0.1,-0.2,0]), '+0.1 / −0.2')
