#! /usr/bin/env python3
import glob, os, sys
import unittest

sys.path.append('..')

from libexport import Parser, SourceException, versionString

TESTDATA_DIR = "../../testdata"


class TestLibExport(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.versions = {}
    with open(os.path.join(TESTDATA_DIR, "versionString.txt")) as f:
      for line in f:
        name, value = line.split(" ", 1)
        cls.versions[name] = value.strip()

    p = Parser()
    cls.all_data = p.parse(
      glob.glob(os.path.join(TESTDATA_DIR, "Demo*.bp"))
    )
    
  def test_testCoverage(self):
    for cl, data in self.all_data.items():
      if not data.is_enum:
        self.assertTrue(cl in self.versions, f"{cl} not in versionString.txt")

  def test_versionString(self):
    for cl, expected in self.versions.items():
      data = self.all_data[cl]
      vs = versionString(data, self.all_data, {}, {}, set())
      self.assertEqual(expected, vs)

  def test_intermediate_representation(self):
    for cl, data in self.all_data.items():
        self.assertNotEqual(data.fields[0][1], '', f"{cl} fields have empty leading data: {data.fields}")
        self.assertNotEqual(data.fields[-1][1], '', f"{cl} fields have empty trailing data: {data.fields}")
        for inner, inner_data in data.inner.items():
            self.assertNotEqual(inner_data.fields[0][1], '', f"{cl}.{inner} fields have empty leading data: {inner_data.fields}")
            self.assertNotEqual(inner_data.fields[-1][1], '', f"{cl}.{inner} fields have empty trailing data: {inner_data.fields}")

  def test_negatives(self):
    path = os.path.join(TESTDATA_DIR, "Negative*.bp")
    for filepath in glob.glob(path):
      print("...", filepath)
      with self.subTest(filename=filepath):
        p = Parser()
        annotations = {}
        with self.assertRaises(SourceException) as cm:
          data = p.parse([filepath], annotations=annotations)
        self.assertEqual(annotations['@what'], cm.exception.what)
      

if __name__ == '__main__':
    unittest.main()
