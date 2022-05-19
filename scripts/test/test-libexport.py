#! /usr/bin/env python3
import os, sys
import unittest

sys.path.append('..')

from libexport import Parser, versionString

TESTDATA_DIR = "../../testdata"

class TestStringMethods(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.versions = {}
    with open(os.path.join(TESTDATA_DIR, "versionString.txt")) as f:
      for line in f:
        bp, _ = line.split("+", 1)
        cls.versions[bp] = line.strip()
        
    p = Parser()
    cls.all_data = p.parse([os.path.join(TESTDATA_DIR, "Demo.bp")])
    
  def test_testCoverage(self):
    for cl, data in self.all_data.items():
      if not data.is_enum:
        self.assertTrue(cl in self.versions[cl], f"{cl} not in versionString.txt")

  def test_versionString(self):
      for cl, expected in self.versions.items():
        data = self.all_data[cl]
        vs = versionString(data, self.all_data, {}, {}, set())
        self.assertEqual(expected, vs)

if __name__ == '__main__':
    unittest.main()
