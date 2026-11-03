import unittest
from pathlib import Path
from scripts.build_site import market_filename

class BuildBoundaryTests(unittest.TestCase):
 def test_repository_symbols_are_single_safe_files(self):
  for symbol in ['org/repo','../../unexpected','NVDA.US','000001.SH','研究/示例']:
   name=market_filename(symbol)
   self.assertEqual(Path(name).name,name)
   self.assertNotIn('/',name)
   self.assertTrue(name.endswith('.json'))
 def test_symbol_identity_does_not_collapse(self):
  symbols=['org/repo','org_repo','ORG/repo','000001.SH','000001.SZ']
  self.assertEqual(len({market_filename(s) for s in symbols}),len(symbols))

if __name__=='__main__':unittest.main()
